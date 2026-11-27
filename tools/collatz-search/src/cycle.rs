use anyhow::{Result, ensure};
use num_bigint::BigUint;
use num_rational::Ratio;
use num_traits::{One, Zero};
use serde::Serialize;

use crate::descent::shortcut_big;

#[derive(Debug, Serialize)]
pub struct Cycle {
    minimum: String,
    shortcut_steps: usize,
    parity_word: String,
}

fn candidate(word: &[u8], floor: &BigUint) -> Option<Cycle> {
    let mut multiplier = BigUint::one();
    let mut b = BigUint::zero();
    let mut divisor = BigUint::one();
    for &bit in word {
        if bit == b'1' {
            multiplier *= 3u32;
            b = 3u32 * b + &divisor;
        }
        divisor <<= 1u32;
    }
    if divisor <= multiplier {
        return None;
    }
    let denominator = divisor - multiplier;
    if &b % &denominator != BigUint::ZERO {
        return None;
    }
    let n = b / denominator;
    if &n < floor {
        return None;
    }
    let mut x = n.clone();
    for (i, &bit) in word.iter().enumerate() {
        if x.bit(0) != (bit == b'1') {
            return None;
        }
        shortcut_big(&mut x);
        if x < n || (x == n && i + 1 < word.len()) {
            return None;
        }
    }
    (x == n).then(|| Cycle {
        minimum: n.to_string(),
        shortcut_steps: word.len(),
        parity_word: String::from_utf8(word.to_vec()).expect("binary word"),
    })
}

#[derive(Debug, Serialize)]
pub struct Words {
    length: usize,
    prefix: String,
    from_offset: String,
    to_offset_exclusive: String,
    minima_at_least: String,
    cycles: Vec<Cycle>,
}

pub fn words(length: usize, prefix: &str, offset: u128, count: u64, min: u128) -> Result<Words> {
    ensure!(
        (1..=4096).contains(&length),
        "word length must be in 1..=4096"
    );
    ensure!(
        prefix.len() <= length && prefix.bytes().all(|c| matches!(c, b'0' | b'1')),
        "prefix must be a binary string of at most length {length}"
    );
    let free = length - prefix.len();
    ensure!(
        free <= 127,
        "supply a longer prefix so at most 127 bits remain"
    );
    ensure!(
        count > 0 && min > 0,
        "count and lower bound must be positive"
    );
    let end = offset.checked_add(u128::from(count));
    ensure!(
        end.is_some_and(|end| end <= (1 << free)),
        "offset/count extend beyond the suffix space"
    );
    let end = end.expect("validated above");
    let mut word = prefix.as_bytes().to_vec();
    word.resize(length, b'0');
    let floor = BigUint::from(min);
    let mut cycles = Vec::new();
    for index in offset..end {
        for (bit, digit) in word[prefix.len()..].iter_mut().rev().enumerate() {
            *digit = b'0' + ((index >> bit) & 1) as u8;
        }
        if let Some(cycle) = candidate(&word, &floor) {
            cycles.push(cycle);
        }
    }
    Ok(Words {
        length,
        prefix: prefix.to_owned(),
        from_offset: offset.to_string(),
        to_offset_exclusive: end.to_string(),
        minima_at_least: min.to_string(),
        cycles,
    })
}

type Fraction = Ratio<BigUint>;

// log(x) = 2 * (t + t^3/3 + ...), t = (x-1)/(x+1).
// Bounding the unused denominators by the first unused denominator
// reduces the remainder to a geometric series with ratio t^2.
fn log_bounds(inverse_t: u32) -> (Fraction, Fraction) {
    let t2 = Fraction::new(1u32.into(), (inverse_t * inverse_t).into());
    let mut twice_power = Fraction::new(2u32.into(), inverse_t.into());
    let mut low = Fraction::zero();
    for j in 0..96u32 {
        low += &twice_power / BigUint::from(2 * j + 1);
        twice_power *= &t2;
    }
    let high = &low + twice_power / BigUint::from(193u32) / (Fraction::one() - t2);
    (low, high)
}

// Sum floor((a*i+b)/m) for 0 <= i < n using Euclidean division.
fn floor_sum(mut n: BigUint, mut m: BigUint, mut a: BigUint, mut b: BigUint) -> BigUint {
    let mut result = BigUint::zero();
    while !n.is_zero() {
        if a >= m {
            result += &n * (&n - 1u32) * (&a / &m) / 2u32;
            a %= &m;
        }
        if b >= m {
            result += &n * (&b / &m);
            b %= &m;
        }
        let y = &a * &n + &b;
        if y < m {
            break;
        }
        n = &y / &m;
        b = y % &m;
        std::mem::swap(&mut m, &mut a);
    }
    result
}

struct Band {
    low: Fraction,
    high: Fraction,
}

impl Band {
    fn new(min: u128) -> Self {
        let (ln2_low, ln2_high) = log_bounds(3);
        let (ln3_low, ln3_high) = log_bounds(2);
        // k/r = log2(3) + mean(log2(1+1/(3x))) over odd cycle terms.
        // Since ln(2) > 2/3 and ln(1+t) <= t, the mean is < 1/(2*min).
        Self {
            low: ln3_low / &ln2_high,
            high: ln3_high / ln2_low + Fraction::new(1u32.into(), BigUint::from(min) * 2u32),
        }
    }

    fn count(&self, from: u128, to: u128) -> BigUint {
        let count = BigUint::from(to - from);
        let r = BigUint::from(from);
        let hi = floor_sum(
            count.clone(),
            self.high.denom().clone(),
            self.high.numer().clone(),
            self.high.numer() * &r,
        );
        let below_lo = floor_sum(
            count,
            self.low.denom().clone(),
            self.low.numer().clone(),
            self.low.numer() * r - 1u32,
        );
        hi - below_lo
    }

    fn list(&self, from: u128, to: u128, limit: usize, pairs: &mut Vec<Pair>) {
        if pairs.len() == limit || self.count(from, to).is_zero() {
            return;
        }
        if to - from > 1 {
            let mid = from + (to - from) / 2;
            self.list(from, mid, limit, pairs);
            self.list(mid, to, limit, pairs);
            return;
        }
        let r = BigUint::from(from);
        let mut k = (self.low.numer() * &r - 1u32) / self.low.denom() + 1u32;
        let k_max = (self.high.numer() * r) / self.high.denom();
        while k <= k_max && pairs.len() < limit {
            pairs.push(Pair {
                odd_steps: from.to_string(),
                shortcut_steps: k.to_string(),
            });
            k += 1u32;
        }
    }
}

#[derive(Debug, Serialize)]
struct Pair {
    odd_steps: String,
    shortcut_steps: String,
}

#[derive(Debug, Serialize)]
pub struct Screen {
    odd_from: String,
    odd_to_exclusive: String,
    minima_at_least: String,
    possible_pairs: String,
    listed_pairs: Vec<Pair>,
}

pub fn screen(min: u128, from: u128, to: u128, list: usize) -> Result<Screen> {
    ensure!(
        min > 0 && from > 0 && from < to,
        "need positive minimum and 1 <= odd-from < odd-to"
    );
    ensure!(list <= 10_000, "list at most 10000 pairs per report");
    let band = Band::new(min);
    let possible_pairs = band.count(from, to);
    let mut listed_pairs = Vec::new();
    band.list(from, to, list, &mut listed_pairs);
    Ok(Screen {
        odd_from: from.to_string(),
        odd_to_exclusive: to.to_string(),
        minima_at_least: min.to_string(),
        possible_pairs: possible_pairs.to_string(),
        listed_pairs,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn offset_partition_and_trivial_cycle() {
        let a = words(2, "1", 0, 1, 1).unwrap();
        assert_eq!(a.cycles.len(), 1);
        assert_eq!(a.cycles[0].minimum, "1");
        assert!(words(2, "1", 1, 1, 1).unwrap().cycles.is_empty());
        assert!(words(4, "1010", 0, 1, 1).unwrap().cycles.is_empty());
        assert!(words(2, "1", 0, 1, 2).unwrap().cycles.is_empty());
    }

    #[test]
    fn floor_sum_matches_direct_count() {
        let band = Band::new(17);
        for (from, to) in [(1, 20), (19, 125), (822, 1025)] {
            let direct: BigUint = (from..to)
                .map(|r: u128| {
                    band.high.numer() * r / band.high.denom()
                        - (band.low.numer() * r - 1u32) / band.low.denom()
                })
                .sum();
            assert_eq!(band.count(from, to), direct);
        }
        let result = screen(1, 1, 2, 1).unwrap();
        assert_eq!(result.listed_pairs[0].shortcut_steps, "2");
    }
}
