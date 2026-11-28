use anyhow::{Context, Result, bail, ensure};
use fs2::FileExt;
use serde::{Deserialize, Serialize, de::DeserializeOwned};
use serde_json::json;
use std::fmt::Write as _;
use std::fs::{self, File, OpenOptions};
use std::io::{ErrorKind, Write};
use std::ops::RangeInclusive;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::cycle;
use crate::descent::{Block, MAX_BLOCK_BITS, MAX_PENDING, MAX_SIEVE_BITS};
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
    #[serde(default)]
    last_event: Option<Event>,
}

#[derive(Deserialize, Serialize)]
struct Event {
    sequence: u64,
    lane: u32,
    completed_at_unix_ms: u64,
    stage: String,
    details: serde_json::Value,
}

#[derive(Deserialize, Serialize)]
struct Goal {
    target_below: String,
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
        exponents: RangeInclusive<u32>,
        block_bits: u32,
        sieve_bits: u32,
        steps: u32,
        target: Option<u128>,
    ) -> Result<()> {
        let (first, last) = exponents.into_inner();
        ensure!(known >= 2, "known prefix must end at 2 or higher");
        ensure!(
            1 <= first && first <= last && last <= 126,
            "need 1 <= first-exp <= last-exp <= 126"
        );
        ensure!(
            block_bits <= MAX_BLOCK_BITS && sieve_bits <= MAX_SIEVE_BITS && steps > 0,
            "invalid block, sieve or step budget"
        );
        if let Some(target) = target {
            validate_target(known, first, last, target)?;
        }
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
            &root.join("goal.json"),
            &target.map(|target| Goal {
                target_below: target.to_string(),
            }),
        )?;
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

    fn target(&self) -> Result<Option<u128>> {
        let goal = read_json::<Option<Goal>>(&self.root.join("goal.json"))?.flatten();
        goal.map(|goal| {
            let target = goal.target_below.parse()?;
            validate_target(
                self.known,
                self.config.first_exp,
                self.config.last_exp,
                target,
            )?;
            Ok(target)
        })
        .transpose()
    }

    pub fn set_target(&self, target: u128) -> Result<()> {
        validate_target(
            self.known,
            self.config.first_exp,
            self.config.last_exp,
            target,
        )?;
        let _lock = try_lock(&self.root.join("run.lock"))?
            .context("wait for active scan and trace workers to finish their current invocation before changing the target")?;
        write_json(
            &self.root.join("goal.json"),
            &Goal {
                target_below: target.to_string(),
            },
        )
    }

    fn lock_run(&self) -> Result<File> {
        let file = open_lock_file(&self.root.join("run.lock"))?;
        FileExt::lock_shared(&file)?;
        Ok(file)
    }

    fn frontier(&self) -> Result<u128> {
        let mut frontier = self.known;
        for exp in self.config.first_exp..=self.config.last_exp {
            let lane = self.lane(exp);
            if frontier >= lane.start && frontier < lane.end {
                frontier = lane.extend_prefix(frontier, lane.progress()?.limit().parse()?);
                if frontier < lane.end {
                    break;
                }
            }
        }
        Ok(frontier)
    }

    fn report_goal(&self, target: Option<u128>) -> Result<bool> {
        if let Some(target) = target {
            let frontier = self.frontier()?;
            if frontier >= target {
                print_json(&json!({
                    "status": "goal_reached", "target_below": target.to_string(),
                    "verified_below_given_base": frontier.to_string()
                }))?;
                return Ok(true);
            }
        }
        Ok(false)
    }

    fn counterexample(&self) -> Result<Option<serde_json::Value>> {
        read_json(&self.root.join("counterexample.json"))
    }

    fn record_cycle(&self, witness: serde_json::Value) -> Result<()> {
        let lock = open_lock_file(&self.root.join("counterexample.lock"))?;
        FileExt::lock_exclusive(&lock)?;
        let path = self.root.join("counterexample.json");
        if !path.exists() {
            write_json(&path, &witness)?;
        }
        Ok(())
    }

    fn report_cycle(&self) -> Result<bool> {
        if let Some(witness) = self.counterexample()? {
            print_json(&json!({"status": "cycle_witness", "counterexample": witness}))?;
            return Ok(true);
        }
        Ok(false)
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
                lane.archive_last_event(&progress)?;
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
        let _run = self.lock_run()?;
        let target = self.target()?;
        if self.report_cycle()? || self.report_goal(target)? {
            return Ok(());
        }
        let Some((lane, mut progress, _lock)) = self.claim(requested, |lane, progress| {
            Ok(progress.cycle.is_none()
                && progress.next.parse::<u128>()? < lane.end.min(target.unwrap_or(lane.end)))
        })?
        else {
            return print_json(&json!({"status": "no_claimable_lane"}));
        };
        let end = lane.end.min(target.unwrap_or(lane.end));
        let _device_lock = if matches!(backend, Backend::Metal) {
            Some(
                try_lock(&self.root.join("metal.lock"))?
                    .context("a Metal worker is already active in this state")?,
            )
        } else {
            None
        };
        let scan = Scan::new(backend, threads, self.config.sieve_bits, self.config.steps)?;
        let start: u128 = progress.next.parse()?;
        let block_size = 1u128 << self.config.block_bits;
        let initial_pending = progress.pending.len();
        let scan_blocks = |report: &mut dyn FnMut(u128, Block, f64) -> Result<()>| -> Result<()> {
            let mut start = start;
            let mut pending = initial_pending;
            for _ in 0..blocks {
                if self.counterexample()?.is_some() || start == end {
                    break;
                }
                let stop = start.saturating_add(block_size).min(end);
                let _lease = lane.note_active(worker, backend.label(), start, stop)?;
                let (result, seconds) = scan.block(start, stop, self.config.steps)?;
                pending += result.unresolved.len();
                ensure!(
                    pending <= MAX_PENDING,
                    "pending queue is full; use trace-work before scanning more blocks"
                );
                report(stop, result, seconds)?;
                start = stop;
            }
            Ok(())
        };
        let mut save_block = |stop: u128, result: Block, seconds: f64| {
            progress
                .pending
                .extend(result.unresolved.iter().map(|n| Pending {
                    n: n.clone(),
                    tried: u64::from(self.config.steps),
                }));
            progress.next = stop.to_string();
            progress.completed_blocks += 1;
            let details = json!({
                "worker": worker, "backend": backend.label(), "seconds": seconds,
                "from": result.from, "to_exclusive": result.to_exclusive,
                "orbit_checks": result.orbit_checks, "sieved": result.sieved,
                "exact_replays": result.exact_replays, "unresolved_count": result.unresolved.len(),
                "pending_total": progress.pending.len(), "lane_descended_below": progress.limit()
            });
            lane.checkpoint(&mut progress, "scan_finished", details)?;
            print_json(&json!({
                "worker": worker, "lane": lane.exp, "backend": backend.label(),
                "seconds": seconds, "block": result,
                "pending_total": progress.pending.len(),
                "lane_descended_below": progress.limit()
            }))
        };
        if matches!(backend, Backend::Cpu) && blocks > 1 && end - start > block_size {
            std::thread::scope(|scope| {
                // The writer saves one checkpoint while the scan computes the next block.
                let (send, receive) = std::sync::mpsc::sync_channel(0);
                let writer = std::thread::Builder::new().spawn_scoped(scope, move || {
                    receive
                        .into_iter()
                        .try_for_each(|(stop, result, seconds)| save_block(stop, result, seconds))
                })?;
                let scanned = scan_blocks(&mut |stop, result, seconds| {
                    send.send((stop, result, seconds))
                        .context("CPU checkpoint writer stopped")
                });
                drop(send);
                writer
                    .join()
                    .map_err(|_| anyhow::anyhow!("CPU checkpoint writer panicked"))??;
                scanned
            })?;
        } else {
            scan_blocks(&mut save_block)?;
        }
        if !self.report_cycle()? {
            self.report_goal(target)?;
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
        let _run = self.lock_run()?;
        let target = self.target()?;
        if self.report_cycle()? || self.report_goal(target)? {
            return Ok(());
        }
        let Some((lane, mut progress, _lock)) = self.claim(requested, |_, p| {
            Ok(p.cycle.is_none() && p.trace_candidate(steps, target)?.is_some())
        })?
        else {
            return print_json(&json!({"status": "no_claimable_candidates", "step_budget": steps}));
        };
        for _ in 0..limit {
            if self.report_cycle()? {
                return Ok(());
            }
            let Some(index) = progress.trace_candidate(steps, target)? else {
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
                    let witness = serde_json::to_value(&result)?;
                    self.record_cycle(
                        json!({"source": "trace_work", "lane": lane.exp, "witness": witness}),
                    )?;
                    progress.cycle = Some(witness);
                }
            }
            let details = json!({
                "worker": worker, "lane": lane.exp, "trace": result, "pending_total": progress.pending.len()
            });
            lane.checkpoint(&mut progress, "trace_finished", details.clone())?;
            print_json(&details)?;
            if progress.cycle.is_some() {
                self.report_cycle()?;
                return Ok(());
            }
        }
        if !self.report_cycle()? {
            self.report_goal(target)?;
        }
        Ok(())
    }

    pub fn status(&self) -> Result<()> {
        let target = self.target()?;
        let mut frontier = self.known;
        let mut scanned = self.known;
        let mut lanes = Vec::new();
        for exp in self.config.first_exp..=self.config.last_exp {
            let lane = self.lane(exp);
            let p = lane.progress()?;
            let covered = p.limit().parse::<u128>()?;
            frontier = lane.extend_prefix(frontier, covered);
            scanned = lane.extend_prefix(scanned, p.next.parse()?);
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
                "target_capped_end": lane.end.min(target.unwrap_or(lane.end)).max(lane.start).to_string(),
                "lane_descended_below": p.limit(), "completed_blocks": p.completed_blocks.to_string(),
                "pending": p.pending.len(),
                "earliest_unresolved": p.pending.first(), "cycle": p.cycle,
                "active": active, "last_event": p.last_event
            }));
        }
        let (cycle_screens, cycle_claims) = reports(&self.root.join("cycles"))?;
        let (parity_batches, parity_claims) = reports(&self.root.join("words"))?;
        let counterexample = self.counterexample()?;
        let goal = target.map(|target| json!({
            "target_below": target.to_string(), "scanned": scanned >= target, "reached": frontier >= target
        }));
        print_json(&json!({
            "config": self.config, "verified_below_given_base": frontier.to_string(),
            "goal": goal, "counterexample": counterexample,
            "scanned_below_given_base": scanned.to_string(),
            "lanes": lanes, "cycle_screens": cycle_screens, "cycle_claims": cycle_claims,
            "parity_batches": parity_batches, "parity_claims": parity_claims
        }))
    }

    pub fn history(&self, requested: Option<u32>, limit: usize) -> Result<()> {
        ensure!(
            (1..=1000).contains(&limit),
            "history limit must be in 1..=1000"
        );
        let first = requested.unwrap_or(self.config.first_exp);
        let last = requested.unwrap_or(self.config.last_exp);
        ensure!(
            first >= self.config.first_exp && last <= self.config.last_exp,
            "lane outside configured exponents"
        );
        let mut events = Vec::new();
        for exp in first..=last {
            let lane = self.lane(exp);
            let progress = lane.progress()?;
            if let Some(last_event) = progress.last_event {
                let from = last_event.sequence.saturating_sub(limit as u64 - 1).max(1);
                for sequence in from..last_event.sequence {
                    let event: Event =
                        read_json(&lane.event_path(sequence))?.with_context(|| {
                            format!("missing journal entry {sequence} for lane {exp}")
                        })?;
                    ensure!(
                        event.lane == exp && event.sequence == sequence,
                        "incorrect journal entry {sequence} for lane {exp}"
                    );
                    events.push(event);
                }
                // The checkpoint is authoritative if a crash interrupted the journal append.
                events.push(last_event);
            }
        }
        events.sort_unstable_by_key(|e| (e.completed_at_unix_ms, e.lane, e.sequence));
        print_json(&json!({"events": &events[events.len().saturating_sub(limit)..]}))
    }

    pub fn coverage(&self, save: bool) -> Result<()> {
        let _lock = if save {
            let lock = open_lock_file(&self.root.join("coverage.lock"))?;
            FileExt::lock_exclusive(&lock)?;
            Some(lock)
        } else {
            None
        };
        let mut table = String::from(
            "| Lane | Descent checked without gaps | Scanned | Unresolved starts | First unresolved | Completed blocks |\n\
             | ---: | --- | --- | ---: | --- | ---: |\n",
        );
        let mut frontier = self.known;
        for exp in self.config.first_exp..=self.config.last_exp {
            let lane = self.lane(exp);
            let p = lane.progress()?;
            frontier = lane.extend_prefix(frontier, p.limit().parse()?);
            let first_pending = p
                .pending
                .first()
                .map_or("—".to_owned(), |x| format!("`{}`", x.n));
            writeln!(
                table,
                "| {exp} | `[{}, {})` | `[{}, {})` | {} | {} | {} |",
                lane.start,
                p.limit(),
                lane.start,
                p.next,
                p.pending.len(),
                first_pending,
                p.completed_blocks,
            )?;
        }
        let report = format!(
            "# Collatz verification coverage\n\n\
             All upper endpoints are exclusive. The configured base is `[1, {})`.\n\n\
             **Contiguous convergence given the configured base** `[1, {frontier})`. \
             This run extends the base by {} starts.\n\n\
             Each lane shows descent checks from its start up to its first unresolved start \
             or its scan cursor. The first gap fixes the end of the contiguous prefix.\n\n\
             {table}",
            self.known,
            frontier - self.known,
        );
        if save {
            write_atomic(&self.root.join("coverage.md"), |file| {
                file.write_all(report.as_bytes())?;
                Ok(())
            })?;
        }
        std::io::stdout().lock().write_all(report.as_bytes())?;
        Ok(())
    }

    pub fn cycle_work(&self, exp: u32, list: usize) -> Result<()> {
        if self.report_cycle()? {
            return Ok(());
        }
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
        if self.report_cycle()? {
            return Ok(());
        }
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
        if let Some(witness) = report.cycles.first() {
            self.record_cycle(json!({"source": "word_work", "witness": witness}))?;
        }
        write_json(&path, &report)?;
        print_json(&report)
    }
}

fn validate_target(known: u128, first: u32, last: u32, target: u128) -> Result<()> {
    ensure!(target >= 2, "target must be at least 2");
    ensure!(
        target <= known || (known >= 1u128 << first && target <= 1u128 << (last + 1)),
        "target is outside the configured contiguous lanes or the base leaves an earlier gap"
    );
    Ok(())
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

    fn trace_candidate(&self, steps: u64, target: Option<u128>) -> Result<Option<usize>> {
        for (index, candidate) in self.pending.iter().enumerate() {
            if let Some(target) = target
                && candidate.n.parse::<u128>()? >= target
            {
                break;
            }
            if candidate.tried < steps {
                return Ok(Some(index));
            }
        }
        Ok(None)
    }
}

struct Lane {
    path: PathBuf,
    exp: u32,
    start: u128,
    end: u128,
}

impl Lane {
    fn extend_prefix(&self, prefix: u128, covered: u128) -> u128 {
        if (self.start..self.end).contains(&prefix) {
            prefix.max(covered)
        } else {
            prefix
        }
    }

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

    fn event_path(&self, sequence: u64) -> PathBuf {
        self.path
            .join("journal")
            .join(format!("{sequence:020}.json"))
    }

    fn archive_last_event(&self, progress: &Progress) -> Result<()> {
        if let Some(event) = &progress.last_event {
            let path = self.event_path(event.sequence);
            if !path.exists() {
                fs::create_dir_all(self.path.join("journal"))?;
                write_json(&path, event)?;
            }
        }
        Ok(())
    }

    fn checkpoint(
        &self,
        progress: &mut Progress,
        stage: &str,
        details: serde_json::Value,
    ) -> Result<()> {
        let previous = progress.last_event.as_ref().map_or(0, |e| e.sequence);
        progress.last_event = Some(Event {
            sequence: previous
                .checked_add(1)
                .context("journal sequence overflow")?,
            lane: self.exp,
            completed_at_unix_ms: now_ms(),
            stage: stage.to_owned(),
            details,
        });
        write_json(&self.path.join("progress.json"), progress)?;
        self.archive_last_event(progress)
    }

    fn note_active(&self, worker: &str, mode: &str, start: u128, stop: u128) -> Result<Lease> {
        let path = self.path.join("active.json");
        write_json(
            &path,
            &json!({
                "worker": worker, "pid": std::process::id(), "mode": mode,
                "started_at_unix_ms": now_ms(),
                "from": start.to_string(), "to_exclusive": stop.to_string()
            }),
        )?;
        Ok(Lease(path))
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
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
    write_atomic(path, |file| {
        serde_json::to_writer(&mut *file, data)?;
        file.write_all(b"\n")?;
        Ok(())
    })
}

fn write_atomic(path: &Path, write: impl FnOnce(&mut File) -> Result<()>) -> Result<()> {
    let temp = path.with_extension("tmp");
    let mut file = File::create(&temp)?;
    write(&mut file)?;
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
