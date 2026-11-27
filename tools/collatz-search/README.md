# Collatz experiments on Apple Silicon

## Instructions for the M5 Max worker

> Run a bounded Collatz pilot on the M5 Max. Use the same local state directory as the other workers. The pilot starts at 2392518189247130238976 and ends at 2392518189264310108160, exclusive. Read `status` before starting. After each completed batch, run `coverage --save` with the same state directory and use `history` for timings. Stop scheduling scans when `goal.reached` is true or `counterexample` contains a cycle witness. If `goal.scanned` is true and `goal.reached` is false, follow the unresolved starts with `trace-work` and regenerate the table. At completion, record the exact verified interval and contiguous endpoint in the research report.

In BB, run the ERNIE agent in an environment on the M5 Max. The model tunnel carries inference requests. Shell commands run on the machine selected for the environment, so check the execution host with `sysctl -n machdep.cpu.brand_string` before starting a benchmark.

The 2025 paper established convergence for starts strictly below $2^{71}$. The project currently uses $G=2\,392\,518\,189\,247\,130\,238\,976$ as its next unchecked start, conditional on the base documented in the research report. Both $G$ and the M5 pilot target lie in lane 71, $[2^{71},2^{72})$. Lane 72 begins at $2^{72}$ and can be scanned independently. A lane 72 result advances the global prefix only after the intervening starts in lane 71 are covered. The $2^{40}$ in the timing section counts the starts in a benchmark block whose absolute starting value is listed beside it. [Published 2025 result](https://doi.org/10.1007/s11227-025-07337-0) · [How the project frontier reached G](../../results/collatz-3x-plus-1/README.md#how-far-the-computation-reaches)

Clone the research branch on the M5 Max. Build with [Rust 1.90 or newer](https://rustup.rs/) and the macOS Command Line Tools. Cargo pins the dependencies in `Cargo.lock`. The Metal backend compiles its shader through the installed Metal runtime.

~~~sh
git clone --single-branch --branch research/collatz-metal-workers https://github.com/ViktorBystrov72/lean-conjecture-lab.git
cd lean-conjecture-lab/tools/collatz-search
cargo build --release --locked
cargo test --release --locked -- --include-ignored
~~~

Run this first check on the M5 Max. Both backends should produce an empty `unresolved` list and identical interval and sieve counts. `seconds` measures the block after setup.

~~~sh
bin=./target/release/collatz-search
from=2392518188130518594186
to=2392518188131592336010
"$bin" verify --from "$from" --to "$to" --backend cpu
"$bin" verify --from "$from" --to "$to" --backend metal --threads 4
~~~

## Run a pilot with an explicit stop

This pilot covers four blocks of size $2^{32}$ immediately after the M3 Pro verification. Initialize the state once. Reuse the same absolute state path from each BB thread on the M5 Max.

~~~sh
bin="$PWD/target/release/collatz-search"
state="$PWD/run-state/m5-pilot"
"$bin" init --state "$state" --known-below 2392518189247130238976 \
  --target-below 2392518189264310108160 --first-exp 71 --last-exp 71 \
  --block-bits 32 --sieve-bits 24
"$bin" work --state "$state" --lane 71 --worker m5-pilot --backend metal --threads 4 --blocks 4
"$bin" status --state "$state"
"$bin" history --state "$state" --limit 10
"$bin" coverage --state "$state" --save
~~~

The last scan block is clipped at the exclusive target. `goal.scanned` marks a completed scan up to that point, while `goal.reached` requires every earlier start to have a descent certificate or a successful exact trace. A recorded cycle witness stops workers before they begin their next block, trace, or cycle assignment. Individual cycle assignments otherwise finish at their own bounded limit.

For a longer batch, use a persistent terminal in the ERNIE thread on the M5 Max. Run the following in place of the foreground `work` command. While the terminal runs, read `status` and `history` from a separate shell to answer questions in the thread.

~~~sh
bb terminal create --thread "$BB_THREAD_ID" --title "Collatz pilot" -- \
  "$bin" work --state "$state" --lane 71 --worker m5-pilot --backend metal --threads 4 --blocks 4
~~~

For an existing state, rebuild the workers and wait for active scans and traces to finish before running `set-target --state "$state" --target-below NUMBER`. It preserves all completed checkpoints. An older worker binary lacks the new goal and journal support.

## Record verified intervals

`coverage --state "$state" --save` writes `coverage.md` atomically under the report lock. The table is generated from the saved checkpoints. It shows the gap-free descent interval within each lane, the scanned interval, the first unresolved start, and the contiguous convergence prefix given the configured base. Save it after a scan or trace batch. Use the journal for the backend and elapsed time and the preflight check for the host chip.

When the contiguous prefix advances, add the newly covered half-open interval, its exclusive endpoint, the run date, the backend, and the evidence to the [research report's coverage table](../../results/collatz-3x-plus-1/README.md#how-far-the-computation-reaches). Preserve the 2025 published row as the starting point for the evidence chain. Report work beyond a gap in the lane table until the gap is closed.

## Shared scan and long-orbit jobs

Set the **same absolute path on the same local filesystem** in every worker terminal. Initialize once. The example below resumes at $G$ using the evidence chain in the research report. Omitting `--known-below` starts an independent replay at the exclusive $2^{71}$ bound from the 2025 paper. [Barina, §6 and Table 10](https://doi.org/10.1007/s11227-025-07337-0) · [Project evidence chain](../../results/collatz-3x-plus-1/README.md#how-far-the-computation-reaches)

~~~sh
state="$PWD/run-state/m5"
"$bin" init --state "$state" --known-below 2392518189247130238976 \
  --first-exp 71 --last-exp 73 --block-bits 32 --sieve-bits 24
~~~

Run these in separate terminals after setting `bin` and `state` in each of them. Set a larger `--last-exp` when initializing if more workers need their own exponent lanes.

| Worker | Assigned starts | Command |
| --- | --- | --- |
| `metal-71` | $[G,2^{72})$ | `"$bin" work --state "$state" --lane 71 --worker metal-71 --backend metal --threads 4 --blocks 4` |
| `cpu-72` | $[2^{72},2^{73})$ | `"$bin" work --state "$state" --lane 72 --worker cpu-72 --backend cpu --threads 6 --blocks 4` |
| `cpu-73` | $[2^{73},2^{74})$ | `"$bin" work --state "$state" --lane 73 --worker cpu-73 --backend cpu --threads 6 --blocks 4` |

Omit `--lane` to claim the first available lane with unscanned blocks. Each `work` invocation runs at most `--blocks` blocks and saves a checkpoint after each one. Repeating the command continues at `next_to_scan`. A stopped process releases its advisory locks and leaves any interrupted block available for retry. A worker holds an exclusive lease for its lane. The shared state also admits one Metal worker at a time. Use the same state directory for all processes and keep the files on the Mac's local disk.

~~~sh
"$bin" status --state "$state"
~~~

`active` shows the owner and current interval for each busy lane. `lane_descended_below` marks the contiguous checked portion **within that lane**. `verified_below_given_base` advances only across an unbroken prefix with every earlier lane and candidate resolved. A result in lane 72 can therefore be useful even while the global prefix is still in lane 71.

Each lane writes its completed scan and trace events under `lane-N/journal/` while holding its exclusive worker lock. The records include the worker, bounds or start, completion time and outcome. `history --state "$state" --lane 71 --limit 10` reads the saved events after a process exits. The newest event is also in the atomic checkpoint, so it remains visible if a process stops before archiving that event. Cycle-screen and parity jobs keep their own locked reports, listed in `status`.

Workers doing long-orbit analysis pick up the existing backlog. `trace-work` can run in several lanes at once and retries only candidates whose previous budget was smaller.

~~~sh
"$bin" trace-work --state "$state" --lane 71 --worker trace-71 --steps 1000000 --limit 8
"$bin" trace-work --state "$state" --lane 72 --worker trace-72 --steps 1000000 --limit 8
"$bin" trace --start 27 --steps 1000 --until-one
~~~

A trace uses arbitrary-precision integers and Brent's cycle detection. `descended` discharges the strict-descent check for that start. `cycle` reports an exact repeated value in `last` and its positive `period`. Re-iterate from that value for the given period with exact arithmetic to confirm the witness. `step_limit` retains the candidate. A proof of escape would require an infinite argument, for example an invariant that guarantees successively higher checkpoints on that specific orbit.

## Parallel cycle experiments

Cycle searches are most naturally partitioned by word length, parity prefix, or odd-step count. Blocks of starting integers are useful for following orbits, while a search over parity words may generate candidates from any numerical range.

Run these arithmetic screens in separate terminals. Lane 37 screens odd-step counts in $[2^{37},2^{38})$ and lane 38 covers the next interval. Results are saved under `cycles/` inside the state directory. `status` exposes active claims and finished reports.

~~~sh
"$bin" cycle-work --state "$state" --odd-exp 37 --list 20
"$bin" cycle-work --state "$state" --odd-exp 38 --list 20
~~~

For a cycle with minimum $m\ge L$, length $k$ in shortcut steps and $r$ odd steps, multiplying the ratios of successive values gives

$$
\log_2 3 < \frac{k}{r} \le \log_2 3 + \frac{1}{3L\ln 2}
< \log_2 3 + \frac1{2L}.
$$

The program encloses $\log_2 3$ by rational series bounds and uses a Euclidean floor sum. It can rule out intervals of odd counts without enumerating the counts or constructing the corresponding parity words. Each pair still listed is only a necessary arithmetic possibility. `possible_pairs` counts all pairs in the assigned interval, including pairs beyond the `--list` limit. [Cycle bounds and background](https://doi.org/10.1007/s11227-025-07337-0)

For bounded parity experiments, a fixed `--prefix-bits` layout reserves disjoint batches for a given length. These small commands demonstrate the partition. In this example shards 0 and 1 cover words beginning with `0000` and `0001`.

~~~sh
"$bin" word-work --state "$state" --length 12 --prefix-bits 4 --shard 0
"$bin" word-work --state "$state" --length 12 --prefix-bits 4 --shard 1
"$bin" cycle-words --length 2 --prefix 1 --offset 0 --count 1 --min 1
~~~

For each word, the code forms $T^k(n)=(3^r n+b)/2^k$. It tests the unique possible positive integer $n=b/(2^k-3^r)$, verifies the full word, and accepts only a primitive cycle represented by its minimum. The last command recovers the trivial shortcut cycle $1\to2\to1$. Use `cycle-screen` to decide which lengths are worth investigating before enumerating words. The parity batches are bounded experiments far below the scale of the published lower bounds for a nontrivial cycle. [Math and current status](../../results/collatz-3x-plus-1/README.md) · [Barina, Section 6](https://doi.org/10.1007/s11227-025-07337-0)

## What the scan verifies

The verifier uses the shortcut map $T$ with $(3n+1)/2$ on odd inputs. Each skipped intermediate value is even, so the visit to 1 is preserved. The sieve fixes the low $s$ bits. For the first $k\le s$ steps, changing the high bits preserves the parity word, and the difference $T^k(n)-n$ is affine. A class is discarded only when this difference is negative at its first permitted representative and decreases as the starting value grows. All other starts are iterated. The Rust CPU path batches consecutive divisions by two and switches to arbitrary precision on overflow. Metal uses two 64-bit limbs, with exact CPU replay on overflow or a step limit. Each result accounts for exactly the requested interval. [Barina's sieve and distributed verification](https://doi.org/10.1007/s11227-025-07337-0) · [Shortcut equivalence in Lean](../../ConjectureLab/Collatz.lean)

The sieve is periodic in the low bits, so the same proof also excludes those classes from the backlog of possible least counterexamples. A strict descent at every start extends a previously verified prefix by strong induction. A range can be scanned independently of the base, while extending the prefix requires checking the gap to that range.

Each exponent lane is an assignment that can contain billions of blocks. An entire octave starting at $2^{71}$ has $2^{31}$ blocks of size $2^{40}$, which would take about 340 years at five seconds per block on one device. Measure this implementation on the M5 Max and run a small number of blocks per worker at first. Further sieve improvements and distributed computation change the throughput. [Barina's throughput](https://pcbarina.fit.vut.cz/) · [Angeltveit's larger-scale sieve](https://arxiv.org/abs/2602.10466)

## Apple M3 Pro control runs

All timings below exclude sieve construction and program startup. The runs used a 24-bit sieve and a budget of 10,000 shortcut steps.

| Starts | From | Metal | CPU with 12 threads | Unresolved |
| ---: | ---: | ---: | ---: | ---: |
| $2^{34}$ | 2392518188130652811914 | 0.985 s | 5.624 s | 0 on both |
| $2^{40}$ | 2392518188130438742016 | 56.513 s | | 0 on Metal |
| $2^{34}$ | 2392518189229950369792 | 1.008 s across four blocks | 5.014 s | 0 on both |

The full-block run excluded 1,080,730,255,360 starts by the sieve and iterated 18,781,372,416 starts. No lane required exact CPU replay in that run. The Mac executing these controls was an M3 Pro. Measure throughput on the M5 Max using the commands above.

~~~sh
"$bin" verify --from 2392518188130438742016 --to 2392518189229950369792 \
  --backend metal --sieve-bits 24 --threads 4
~~~

To replay the $2^{34}$ starts just above that work unit, use the following interval with either backend.

~~~sh
"$bin" verify --from 2392518189229950369792 --to 2392518189247130238976 \
  --backend cpu --sieve-bits 24 --threads 12
~~~
