use anyhow::{Context, Result, bail, ensure};
use fs2::FileExt;
use serde::{Deserialize, Serialize, de::DeserializeOwned};
use serde_json::json;
use std::fs::{self, File, OpenOptions};
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};

use crate::cycle;
use crate::descent::{MAX_BLOCK_BITS, MAX_PENDING, MAX_SIEVE_BITS};
use crate::scan::{Backend, Scan};
use crate::trace::{Outcome, trace};

const FORMAT: u32 = 1;

#[derive(Deserialize, Serialize)]
pub struct Config {
    format: u32,
    known_below: String,
    first_exp: u32,
    last_exp: u32,
    block_bits: u32,
    sieve_bits: u32,
    steps: u32,
}

#[derive(Default, Deserialize, Serialize)]
struct Progress {
    next: String,
    completed_blocks: u128,
    pending: Vec<Pending>,
    cycle: Option<serde_json::Value>,
}

#[derive(Deserialize, Serialize)]
struct Pending {
    n: String,
    tried: u64,
}

pub struct State {
    root: PathBuf,
    config: Config,
    known: u128,
}

impl State {
    pub fn init(
        root: &Path,
        known: u128,
        first: u32,
        last: u32,
        block_bits: u32,
        sieve_bits: u32,
        steps: u32,
    ) -> Result<()> {
        ensure!(known >= 2, "known prefix must end at 2 or higher");
        ensure!(
            1 <= first && first <= last && last <= 126,
            "need 1 <= first-exp <= last-exp <= 126"
        );
        ensure!(
            block_bits <= MAX_BLOCK_BITS && sieve_bits <= MAX_SIEVE_BITS && steps > 0,
            "invalid block, sieve or step budget"
        );
        fs::create_dir_all(root)?;
        let _lock = try_lock(&root.join("init.lock"))?
            .context("another process is initializing this state")?;
        let path = root.join("config.json");
        ensure!(
            !path.exists(),
            "state already initialized: {}",
            root.display()
        );
        write_json(
            &path,
            &Config {
                format: FORMAT,
                known_below: known.to_string(),
                first_exp: first,
                last_exp: last,
                block_bits,
                sieve_bits,
                steps,
            },
        )
    }

    pub fn open(root: &Path) -> Result<Self> {
        let config: Config = read_json(&root.join("config.json"))?
            .context("run init on this state directory first")?;
        ensure!(
            config.format == FORMAT,
            "this binary cannot read state format {}",
            config.format
        );
        ensure!(
            1 <= config.first_exp && config.first_exp <= config.last_exp && config.last_exp <= 126,
            "invalid lane configuration"
        );
        ensure!(
            config.block_bits <= MAX_BLOCK_BITS
                && config.sieve_bits <= MAX_SIEVE_BITS
                && config.steps > 0,
            "invalid block, sieve or step budget"
        );
        let known = config.known_below.parse::<u128>()?;
        ensure!(known >= 2, "known prefix must end at 2 or higher");
        Ok(Self {
            root: root.to_owned(),
            config,
            known,
        })
    }

    fn lane(&self, exp: u32) -> Lane {
        let end = 1u128 << (exp + 1);
        Lane {
            path: self.root.join(format!("lane-{exp}")),
            exp,
            start: (1u128 << exp).max(self.known).min(end),
            end,
        }
    }

    fn claim(
        &self,
        requested: Option<u32>,
        ready: impl Fn(&Lane, &Progress) -> Result<bool>,
    ) -> Result<Option<(Lane, Progress, File)>> {
        let first = requested.unwrap_or(self.config.first_exp);
        let last = requested.unwrap_or(self.config.last_exp);
        ensure!(
            first >= self.config.first_exp && last <= self.config.last_exp,
            "lane outside configured exponents"
        );
        for exp in first..=last {
            let lane = self.lane(exp);
            fs::create_dir_all(&lane.path)?;
            if let Some(lock) = try_lock(&lane.path.join("worker.lock"))? {
                let progress = lane.progress()?;
                if ready(&lane, &progress)? {
                    return Ok(Some((lane, progress, lock)));
                }
            }
        }
        Ok(None)
    }

    pub fn work(
        &self,
        requested: Option<u32>,
        blocks: u64,
        backend: Backend,
        threads: usize,
        worker: &str,
    ) -> Result<()> {
        ensure!(blocks > 0, "block count must be positive");
        let Some((lane, mut progress, _lock)) = self.claim(requested, |lane, progress| {
            Ok(progress.cycle.is_none() && progress.next.parse::<u128>()? < lane.end)
        })?
        else {
            return print_json(&json!({"status": "no_claimable_lane"}));
        };
        let _device_lock = if matches!(backend, Backend::Metal) {
            Some(
                try_lock(&self.root.join("metal.lock"))?
                    .context("a Metal worker is already active in this state")?,
            )
        } else {
            None
        };
        let scan = Scan::new(backend, threads, self.config.sieve_bits, self.config.steps)?;
        for _ in 0..blocks {
            let start: u128 = progress.next.parse()?;
            if start == lane.end {
                break;
            }
            let stop = start
                .saturating_add(1 << self.config.block_bits)
                .min(lane.end);
            let _lease = lane.note_active(worker, backend.label(), start, stop)?;
            let (result, seconds) = scan.block(start, stop, self.config.steps)?;
            ensure!(
                progress.pending.len() + result.unresolved.len() <= MAX_PENDING,
                "pending queue is full; use trace-work before scanning more blocks"
            );
            progress
                .pending
                .extend(result.unresolved.iter().map(|n| Pending {
                    n: n.clone(),
                    tried: u64::from(self.config.steps),
                }));
            progress.next = stop.to_string();
            progress.completed_blocks += 1;
            lane.save(&progress)?;
            print_json(&json!({
                "worker": worker, "lane": lane.exp, "backend": backend.label(),
                "seconds": seconds, "block": result,
                "pending_total": progress.pending.len(),
                "lane_descended_below": progress.limit()
            }))?;
        }
        Ok(())
    }

    pub fn trace_work(
        &self,
        requested: Option<u32>,
        steps: u64,
        limit: usize,
        worker: &str,
    ) -> Result<()> {
        ensure!(
            steps > 0 && limit > 0,
            "step and candidate limits must be positive"
        );
        let Some((lane, mut progress, _lock)) = self.claim(requested, |_, p| {
            Ok(p.cycle.is_none() && p.pending.iter().any(|pending| pending.tried < steps))
        })?
        else {
            return print_json(&json!({"status": "no_claimable_candidates", "step_budget": steps}));
        };
        for _ in 0..limit {
            let Some(index) = progress.pending.iter().position(|p| p.tried < steps) else {
                break;
            };
            let n = progress.pending[index].n.parse::<u128>()?;
            let _lease = lane.note_active(worker, "trace", n, n + 1)?;
            let result = trace(&progress.pending[index].n, steps, false)?;
            match result.outcome {
                Outcome::ReachesOne | Outcome::Descended => {
                    progress.pending.remove(index);
                }
                Outcome::StepLimit => progress.pending[index].tried = steps,
                Outcome::Cycle => {
                    progress.cycle = Some(serde_json::to_value(&result)?);
                }
            }
            lane.save(&progress)?;
            print_json(
                &json!({"worker": worker, "lane": lane.exp, "trace": result, "pending_total": progress.pending.len()}),
            )?;
            if progress.cycle.is_some() {
                break;
            }
        }
        Ok(())
    }

    pub fn status(&self) -> Result<()> {
        let mut frontier = self.known;
        let mut lanes = Vec::new();
        for exp in self.config.first_exp..=self.config.last_exp {
            let lane = self.lane(exp);
            let p = lane.progress()?;
            let covered = p.limit().parse::<u128>()?;
            if frontier >= lane.start && frontier < lane.end {
                frontier = frontier.max(covered);
            }
            let note = lane.path.join("active.json");
            let active =
                if lane.path.is_dir() && try_lock(&lane.path.join("worker.lock"))?.is_none() {
                    read_json::<serde_json::Value>(&note)?
                        .or_else(|| Some(json!({"status": "claiming"})))
                } else {
                    None
                };
            lanes.push(json!({
                "lane": exp, "search_from": lane.start.to_string(),
                "to_exclusive": lane.end.to_string(), "next_to_scan": p.next,
                "lane_descended_below": p.limit(), "completed_blocks": p.completed_blocks.to_string(),
                "pending": p.pending.len(),
                "earliest_unresolved": p.pending.first(), "cycle": p.cycle,
                "active": active
            }));
        }
        let (cycle_screens, cycle_claims) = reports(&self.root.join("cycles"))?;
        let (parity_batches, parity_claims) = reports(&self.root.join("words"))?;
        print_json(&json!({
            "config": self.config, "verified_below_given_base": frontier.to_string(),
            "lanes": lanes, "cycle_screens": cycle_screens, "cycle_claims": cycle_claims,
            "parity_batches": parity_batches, "parity_claims": parity_claims
        }))
    }

    pub fn cycle_work(&self, exp: u32, list: usize) -> Result<()> {
        ensure!(exp <= 126, "odd-count exponent must be at most 126");
        let directory = self.root.join("cycles");
        fs::create_dir_all(&directory)?;
        let _lock = try_lock(&directory.join(format!("{exp}.lock")))?
            .context("this odd-count lane is already claimed")?;
        let path = directory.join(format!("{exp}.json"));
        ensure!(
            !path.exists(),
            "this odd-count lane already has a report: {}",
            path.display()
        );
        let report = cycle::screen(self.known, 1 << exp, 1 << (exp + 1), list)?;
        write_json(&path, &report)?;
        print_json(&report)
    }

    pub fn word_work(&self, length: u32, prefix_bits: u32, shard: u128) -> Result<()> {
        ensure!(
            (1..=127).contains(&length) && prefix_bits <= length,
            "need 1 <= length <= 127 and prefix-bits <= length"
        );
        let suffix_bits = length - prefix_bits;
        ensure!(
            suffix_bits <= 20 && shard < (1 << prefix_bits),
            "need at most 20 bits per batch and shard < 2^prefix-bits"
        );
        let directory = self.root.join("words").join(length.to_string());
        let batches = directory.join("batches");
        fs::create_dir_all(&batches)?;
        {
            let layout = open_lock_file(&directory.join("layout.lock"))?;
            FileExt::lock_exclusive(&layout)?;
            let path = directory.join("prefix-bits.json");
            if let Some(existing) = read_json::<u32>(&path)? {
                ensure!(
                    existing == prefix_bits,
                    "this state uses {existing} prefix bits for length {length}"
                );
            } else {
                write_json(&path, &prefix_bits)?;
            }
        }
        let _lock = try_lock(&batches.join(format!("{shard}.lock")))?
            .context("this parity shard is already claimed")?;
        let path = batches.join(format!("{shard}.json"));
        ensure!(
            !path.exists(),
            "this parity shard already has a report: {}",
            path.display()
        );
        let prefix = if prefix_bits == 0 {
            String::new()
        } else {
            format!("{shard:0width$b}", width = prefix_bits as usize)
        };
        let report = cycle::words(length as usize, &prefix, 0, 1 << suffix_bits, self.known)?;
        write_json(&path, &report)?;
        print_json(&report)
    }
}

fn reports(path: &Path) -> Result<(Vec<PathBuf>, Vec<PathBuf>)> {
    let mut paths = Vec::new();
    let mut claims = Vec::new();
    if path.is_dir() {
        for entry in fs::read_dir(path)? {
            let path = entry?.path();
            if path.is_dir() {
                let (lower_paths, lower_claims) = reports(&path)?;
                paths.extend(lower_paths);
                claims.extend(lower_claims);
            } else if path.extension().is_some_and(|ext| ext == "json")
                && path
                    .file_name()
                    .is_some_and(|name| name != "prefix-bits.json")
            {
                paths.push(path);
            } else if path.extension().is_some_and(|ext| ext == "lock")
                && path.file_stem().is_some_and(|name| name != "layout")
                && try_lock(&path)?.is_none()
            {
                claims.push(path);
            }
        }
        paths.sort_unstable();
        claims.sort_unstable();
    }
    Ok((paths, claims))
}

impl Progress {
    fn limit(&self) -> &str {
        self.pending.first().map_or(&self.next, |first| &first.n)
    }
}

struct Lane {
    path: PathBuf,
    exp: u32,
    start: u128,
    end: u128,
}

impl Lane {
    fn progress(&self) -> Result<Progress> {
        let p: Progress =
            read_json(&self.path.join("progress.json"))?.unwrap_or_else(|| Progress {
                next: self.start.to_string(),
                ..Progress::default()
            });
        let next = p.next.parse::<u128>()?;
        ensure!(
            self.start <= next && next <= self.end,
            "corrupt cursor in lane {}",
            self.exp
        );
        let mut prev = None;
        for item in &p.pending {
            let n = item.n.parse::<u128>()?;
            ensure!(
                n >= self.start && n < next && prev.is_none_or(|last| last < n),
                "corrupt pending queue in lane {}",
                self.exp
            );
            prev = Some(n);
        }
        Ok(p)
    }

    fn save(&self, progress: &Progress) -> Result<()> {
        write_json(&self.path.join("progress.json"), progress)
    }

    fn note_active(&self, worker: &str, mode: &str, start: u128, stop: u128) -> Result<Lease> {
        let path = self.path.join("active.json");
        write_json(
            &path,
            &json!({
                "worker": worker, "pid": std::process::id(), "mode": mode,
                "from": start.to_string(), "to_exclusive": stop.to_string()
            }),
        )?;
        Ok(Lease(path))
    }
}

struct Lease(PathBuf);

impl Drop for Lease {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn try_lock(path: &Path) -> Result<Option<File>> {
    let file = open_lock_file(path)?;
    match FileExt::try_lock_exclusive(&file) {
        Ok(()) => Ok(Some(file)),
        Err(e) if e.kind() == ErrorKind::WouldBlock => Ok(None),
        Err(e) => Err(e).with_context(|| format!("cannot lock {}", path.display())),
    }
}

fn open_lock_file(path: &Path) -> Result<File> {
    Ok(OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(path)?)
}

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<Option<T>> {
    match File::open(path) {
        Ok(file) => serde_json::from_reader(std::io::BufReader::new(file))
            .with_context(|| format!("cannot read {}", path.display()))
            .map(Some),
        Err(e) if e.kind() == ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e.into()),
    }
}

fn write_json<T: Serialize>(path: &Path, data: &T) -> Result<()> {
    let temp = path.with_extension("tmp");
    let mut file = File::create(&temp)?;
    serde_json::to_writer(&mut file, data)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    fs::rename(temp, path)?;
    let Some(parent) = path.parent() else {
        bail!("state file has no parent directory");
    };
    File::open(parent)?.sync_all()?;
    Ok(())
}

pub fn print_json<T: Serialize>(data: &T) -> Result<()> {
    let mut out = std::io::stdout().lock();
    serde_json::to_writer(&mut out, data)?;
    out.write_all(b"\n")?;
    Ok(())
}
