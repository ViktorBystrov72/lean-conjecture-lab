mod cycle;
mod descent;
#[cfg(target_os = "macos")]
mod gpu;
mod jobs;
mod scan;
mod trace;

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

use jobs::{State, print_json};
use scan::{Backend, Scan};

// Starts below this bound have a published result in Barina (2025).
const PUBLISHED_BOUND: u128 = 1 << 71;

#[derive(Parser)]
#[command(
    version,
    about = "Bounded, exact computational experiments for the classical Collatz map"
)]
struct Args {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Check strict descent for one half-open interval, without a shared checkpoint.
    Verify {
        #[arg(long)]
        from: u128,
        #[arg(long)]
        to: u128,
        #[arg(long, value_enum, default_value = "cpu")]
        backend: Backend,
        /// Rayon thread count; zero uses its machine default.
        #[arg(long, default_value_t = 0)]
        threads: usize,
        #[arg(long, default_value_t = 18)]
        sieve_bits: u32,
        #[arg(long, default_value_t = 10_000)]
        steps: u32,
    },
    /// Initialize one shared state directory on a local disk.
    Init {
        #[arg(long)]
        state: PathBuf,
        #[arg(long, default_value_t = PUBLISHED_BOUND)]
        known_below: u128,
        #[arg(long, default_value_t = 71)]
        first_exp: u32,
        #[arg(long, default_value_t = 73)]
        last_exp: u32,
        #[arg(long, default_value_t = 32)]
        block_bits: u32,
        #[arg(long, default_value_t = 18)]
        sieve_bits: u32,
        #[arg(long, default_value_t = 10_000)]
        steps: u32,
        /// Exclusive target for the contiguous verified prefix.
        #[arg(long)]
        target_below: Option<u128>,
    },
    /// Claim a lane and scan bounded blocks, recording time and unresolved starts.
    Work {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        lane: Option<u32>,
        #[arg(long, default_value_t = 1)]
        blocks: u64,
        #[arg(long, value_enum, default_value = "cpu")]
        backend: Backend,
        #[arg(long, default_value_t = 0)]
        threads: usize,
        #[arg(long, default_value = "worker")]
        worker: String,
    },
    /// Show the conditional verified prefix, lane leases, and the candidate backlog.
    Status {
        #[arg(long)]
        state: PathBuf,
    },
    /// Set the exclusive goal in an existing state while scan and trace workers are idle.
    SetTarget {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        target_below: u128,
    },
    /// Read the latest durable scan and trace events, including completed jobs.
    History {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        lane: Option<u32>,
        #[arg(long, default_value_t = 10)]
        limit: usize,
    },
    /// Follow a single orbit using arbitrary-precision arithmetic and cycle detection.
    Trace {
        #[arg(long)]
        start: String,
        #[arg(long, default_value_t = 100_000)]
        steps: u64,
        /// Continue after the first strict descent.
        #[arg(long)]
        until_one: bool,
    },
    /// Claim a lane's unresolved starts and retry them with a higher step budget.
    TraceWork {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        lane: Option<u32>,
        #[arg(long, default_value_t = 100_000)]
        steps: u64,
        #[arg(long, default_value_t = 4)]
        limit: usize,
        #[arg(long, default_value = "tracer")]
        worker: String,
    },
    /// Check exact cycle candidates for a bounded batch of parity words.
    CycleWords {
        #[arg(long)]
        length: usize,
        #[arg(long, default_value = "")]
        prefix: String,
        #[arg(long, default_value_t = 0)]
        offset: u128,
        #[arg(long)]
        count: u64,
        #[arg(long, default_value_t = PUBLISHED_BOUND)]
        min: u128,
    },
    /// Count possible cycle length / odd count pairs using exact rational bounds.
    CycleScreen {
        #[arg(long, default_value_t = PUBLISHED_BOUND)]
        min: u128,
        #[arg(long)]
        odd_from: u128,
        #[arg(long)]
        odd_to: u128,
        #[arg(long, default_value_t = 20)]
        list: usize,
    },
    /// Reserve a shared interval of odd counts [2^odd-exp, 2^(odd-exp+1)).
    CycleWork {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        odd_exp: u32,
        #[arg(long, default_value_t = 20)]
        list: usize,
    },
    /// Claim one bounded parity shard in a shared, fixed-prefix layout.
    WordWork {
        #[arg(long)]
        state: PathBuf,
        #[arg(long)]
        length: u32,
        #[arg(long)]
        prefix_bits: u32,
        #[arg(long)]
        shard: u128,
    },
}

fn main() -> Result<()> {
    match Args::parse().command {
        Command::Verify {
            from,
            to,
            backend,
            threads,
            sieve_bits,
            steps,
        } => {
            let (block, seconds) =
                Scan::new(backend, threads, sieve_bits, steps)?.block(from, to, steps)?;
            print_json(
                &serde_json::json!({"backend": backend.label(), "step_budget": steps, "seconds": seconds, "block": block}),
            )
        }
        Command::Init {
            state,
            known_below,
            first_exp,
            last_exp,
            block_bits,
            sieve_bits,
            steps,
            target_below,
        } => {
            State::init(
                &state,
                known_below,
                first_exp..=last_exp,
                block_bits,
                sieve_bits,
                steps,
                target_below,
            )?;
            State::open(&state)?.status()
        }
        Command::Work {
            state,
            lane,
            blocks,
            backend,
            threads,
            worker,
        } => State::open(&state)?.work(lane, blocks, backend, threads, &worker),
        Command::Status { state } => State::open(&state)?.status(),
        Command::SetTarget {
            state,
            target_below,
        } => {
            let state = State::open(&state)?;
            state.set_target(target_below)?;
            state.status()
        }
        Command::History { state, lane, limit } => State::open(&state)?.history(lane, limit),
        Command::Trace {
            start,
            steps,
            until_one,
        } => print_json(&trace::trace(&start, steps, until_one)?),
        Command::TraceWork {
            state,
            lane,
            steps,
            limit,
            worker,
        } => State::open(&state)?.trace_work(lane, steps, limit, &worker),
        Command::CycleWords {
            length,
            prefix,
            offset,
            count,
            min,
        } => print_json(&cycle::words(length, &prefix, offset, count, min)?),
        Command::CycleScreen {
            min,
            odd_from,
            odd_to,
            list,
        } => print_json(&cycle::screen(min, odd_from, odd_to, list)?),
        Command::CycleWork {
            state,
            odd_exp,
            list,
        } => State::open(&state)?.cycle_work(odd_exp, list),
        Command::WordWork {
            state,
            length,
            prefix_bits,
            shard,
        } => State::open(&state)?.word_work(length, prefix_bits, shard),
    }
}
