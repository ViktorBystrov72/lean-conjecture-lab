use anyhow::{Result, ensure};
use num_bigint::BigUint;
use rayon::prelude::*;
use serde::Serialize;

pub const MAX_BLOCK_BITS: u32 = 40;
pub const MAX_SIEVE_BITS: u32 = 24;
pub const MAX_PENDING: usize = 65_536;

pub fn shortcut_big(value: &mut BigUint) {
    if value.bit(0) {
        *value += (&*value >> 1u32) + 1u32;
    } else {
        *value >>= 1u32;
    }
}

pub fn descends(start: u128, mut steps: u32) -> bool {
    let mut value = start;
    while steps > 0 {
        if value & 1 != 0 {
            if let Some(next) = value.checked_add((value >> 1) + 1) {
                value = next;
                steps -= 1;
            } else {
                let mut large = BigUint::from(value);
                let target = BigUint::from(start);
                for _ in 0..steps {
                    shortcut_big(&mut large);
                    if large < target {
                        return true;
                    }
                }
                return false;
            }
        } else {
            let shift = value.trailing_zeros().min(steps);
            value >>= shift;
            steps -= shift;
        }
        if value < start {
            return true;
        }
    }
    false
}

pub struct Sieve {
    bits: u32,
    survivors: Vec<u32>,
}

impl Sieve {
    pub fn new(bits: u32) -> Result<Self> {
        ensure!(
            bits <= MAX_SIEVE_BITS,
            "sieve bits must be at most {MAX_SIEVE_BITS}"
        );
        let period = 1 << bits;
        let survivors = (0..period)
            .into_par_iter()
            .filter(|&residue| !has_uniform_descent(period, residue, bits))
            .collect::<Vec<_>>();
        // GPU dispatch and partial-window counts both depend on residue order.
        let mut survivors = survivors;
        survivors.sort_unstable();
        Ok(Self { bits, survivors })
    }

    pub fn window(&self, start: u128, stop: u128) -> Result<Window<'_>> {
        ensure!(start >= 2 && stop > start, "need 2 <= start < stop");
        ensure!(
            stop - start <= 1 << MAX_BLOCK_BITS,
            "split this range into blocks of at most 2^{MAX_BLOCK_BITS}"
        );
        let (bits, residues) = if start >= 1 << self.bits {
            (self.bits, self.survivors.as_slice())
        } else {
            // Below the first full period the sieve's descent guarantee does not apply.
            (0, [0].as_slice())
        };
        let period = 1u64 << bits;
        let base = start & !(u128::from(period) - 1);
        Ok(Window {
            base,
            lo: (start - base) as u64,
            hi: (stop - base) as u64,
            bits,
            residues,
        })
    }
}

fn has_uniform_descent(period: u32, residue: u32, bits: u32) -> bool {
    let start = u64::from(period) + u64::from(residue);
    let mut value = start;
    let mut multiplier = 1;
    for depth in 1..=bits {
        if value & 1 == 0 {
            value >>= 1;
        } else {
            value += (value >> 1) + 1;
            multiplier *= 3;
        }
        // On this residue class the first depth branches are fixed. The difference
        // T^depth(n) - n decreases with n when 3^r < 2^depth.
        if multiplier < 1u64 << depth && value < start {
            return true;
        }
    }
    false
}

#[derive(Clone, Copy)]
pub struct Window<'a> {
    pub base: u128,
    pub lo: u64,
    pub hi: u64,
    pub bits: u32,
    pub residues: &'a [u32],
}

impl Window<'_> {
    fn count_before(&self, offset: u64) -> u64 {
        let remainder = offset & ((1 << self.bits) - 1);
        (offset >> self.bits) * self.residues.len() as u64
            + self.residues.partition_point(|&r| u64::from(r) < remainder) as u64
    }

    pub fn candidates(&self) -> u64 {
        self.count_before(self.hi) - self.count_before(self.lo)
    }

    pub fn slots(&self) -> std::ops::Range<u64> {
        self.count_before(self.lo)..self.count_before(self.hi)
    }

    pub fn at(&self, index: u64) -> u128 {
        let len = self.residues.len() as u64;
        let offset =
            ((index / len) << self.bits) + u64::from(self.residues[(index % len) as usize]);
        self.base + u128::from(offset)
    }

    pub fn scan_cpu(&self, steps: u32) -> Result<Vec<u128>> {
        self.slots()
            .into_par_iter()
            .try_fold(Vec::new, |mut pending, index| {
                let n = self.at(index);
                if !descends(n, steps) {
                    push_pending(&mut pending, n)?;
                }
                Ok(pending)
            })
            .try_reduce(Vec::new, |mut left, mut right| {
                ensure!(left.len() + right.len() <= MAX_PENDING, "{PENDING_LIMIT}");
                left.append(&mut right);
                Ok(left)
            })
    }
}

const PENDING_LIMIT: &str =
    "too many unresolved starts; increase the step budget or use smaller blocks";

pub fn push_pending(pending: &mut Vec<u128>, n: u128) -> Result<()> {
    ensure!(pending.len() < MAX_PENDING, "{PENDING_LIMIT}");
    pending.push(n);
    Ok(())
}

#[derive(Debug, Serialize)]
pub struct Block {
    pub from: String,
    pub to_exclusive: String,
    pub sieved: u64,
    pub orbit_checks: u64,
    pub exact_replays: u64,
    pub unresolved: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    fn reference(start: u128, limit: u32) -> bool {
        let n = BigUint::from(start);
        let mut x = n.clone();
        for _ in 0..limit {
            x = if x.bit(0) {
                (3u32 * &x + 1u32) / 2u32
            } else {
                x / 2u32
            };
            if x < n {
                return true;
            }
        }
        false
    }

    #[test]
    fn partial_windows_and_sieve_certificates() {
        let sieve = Sieve::new(8).unwrap();
        for (lo, hi) in [
            (2, 320),
            (259, 778),
            (1021, 3075),
            (1 << 71, (1 << 71) + 1001),
        ] {
            let window = sieve.window(lo, hi).unwrap();
            let candidates: BTreeSet<_> = window.slots().map(|i| window.at(i)).collect();
            assert_eq!(candidates.len() as u64, window.candidates());
            assert!(candidates.iter().all(|&n| n >= lo && n < hi));
            for n in lo..hi {
                if !candidates.contains(&n) {
                    assert!(reference(n, 8), "sieved {n}");
                }
            }
        }
    }

    #[test]
    fn shortcut_agrees_with_bigints_at_overflow_and_step_limits() {
        for n in [27, 1 << 71, (1 << 71) + 123, u128::MAX - 22, u128::MAX] {
            for limit in [1, 2, 3, 5, 100, 1_000] {
                assert_eq!(descends(n, limit), reference(n, limit), "{n} after {limit}");
            }
        }
    }
}
