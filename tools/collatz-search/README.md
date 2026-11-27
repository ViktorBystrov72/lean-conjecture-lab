# Collatz experiments on Apple Silicon

## Instructions for the M5 Max worker

> Run bounded Collatz experiments on this Mac and share one local state directory with the other workers. Read its status before choosing a lane. Use the requested worker labels and return the exact half-open intervals, timings, and unresolved starts. For a cycle, return an exact witness and period. Report a step limit as an unresolved candidate and keep the stated base of the verified prefix.

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

## Shared scan and long-orbit jobs

Set the **same absolute path on the same local filesystem** in every worker terminal. Initialize once. The default `known_below` is the exclusive $2^{71}$ bound from the 2025 paper. To start at the later prefix documented by this repository, add `--known-below 2392518189229950369792` during initialization. That choice assumes the full-block Metal run and Barina's base below it. [Barina, §6 and Table 10](https://doi.org/10.1007/s11227-025-07337-0) · [Later prefix and its basis](../../results/collatz-3x-plus-1/README.md)

~~~sh
state="$PWD/run-state/m5"
"$bin" init --state "$state" --first-exp 71 --last-exp 73 --block-bits 32 --sieve-bits 24
~~~

Run these in separate terminals after setting `bin` and `state` in each of them. Set a larger `--last-exp` when initializing if more workers need their own exponent lanes.

| Worker | Assigned starts | Command |
| --- | --- | --- |
| `metal-71` | $[2^{71},2^{72})$ | `"$bin" work --state "$state" --lane 71 --worker metal-71 --backend metal --threads 4 --blocks 4` |
| `cpu-72` | $[2^{72},2^{73})$ | `"$bin" work --state "$state" --lane 72 --worker cpu-72 --backend cpu --threads 6 --blocks 4` |
| `cpu-73` | $[2^{73},2^{74})$ | `"$bin" work --state "$state" --lane 73 --worker cpu-73 --backend cpu --threads 6 --blocks 4` |

Omit `--lane` to claim the first available lane with unscanned blocks. Each `work` invocation runs at most `--blocks` blocks and saves a checkpoint after each one. Repeating the command continues at `next_to_scan`. A stopped process releases its advisory locks and leaves any interrupted block available for retry. A worker holds an exclusive lease for its lane. The shared state also admits one Metal worker at a time. Use the same state directory for all processes and keep the files on the Mac's local disk.

~~~sh
"$bin" status --state "$state"
~~~

`active` shows the owner and current interval for each busy lane. `lane_descended_below` marks the contiguous checked portion **within that lane**. `verified_below_given_base` advances only across an unbroken prefix with every earlier lane and candidate resolved. A result in lane 72 can therefore be useful even while the global prefix is still in lane 71.

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

The full-block run excluded 1,080,730,255,360 starts by the sieve and iterated 18,781,372,416 starts. No lane required exact CPU replay in that run. The Mac executing these controls was an M3 Pro. Measure throughput on the M5 Max using the commands above.

~~~sh
"$bin" verify --from 2392518188130438742016 --to 2392518189229950369792 \
  --backend metal --sieve-bits 24 --threads 4
~~~
