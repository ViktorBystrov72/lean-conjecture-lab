# The classical Collatz conjecture

**Status on 27 November 2026: open.** The iXBT Live article of 6 June 2026 asks whether every positive integer eventually reaches 1 under the ordinary Collatz map. I found no accepted proof or counterexample. A peer-reviewed paper published on 24 November still describes the problem as open. [iXBT article](https://www.ixbt.com/live/science/mem-kotoryy-paralizoval-universitety-pochemu-prostaya-zadacha-3x1-uzhe-vek-kradet-vremya-u-luchshih-umov-planety.html) · [Elsenhans, §1](https://doi.org/10.1007/s40993-026-00811-5)

## The exact question

For a positive integer $n$, put $C(n)=n/2$ if $n$ is even and $C(n)=3n+1$ if $n$ is odd. Write $C^0(n)=n$ and $C^{k+1}(n)=C(C^k(n))$. The claim is

$$
\forall n\in\mathbb Z_{>0}\quad \exists k\in\mathbb Z_{\ge 0}\quad C^k(n)=1.
$$

After the first visit to 1 the orbit repeats $1,4,2,1$. A counterexample would either enter a different cycle or tend to infinity. In fact, an orbit that never repeats can visit each member of any finite interval at most once, so it eventually stays above every fixed bound. [Tao, Conjecture 1.1](https://arxiv.org/html/1909.03562v7#S1.Thmtheorem1)

Some sources use $T(n)=n/2$ on even inputs and $T(n)=(3n+1)/2$ on odd inputs. An odd positive input produces an even $3n+1\ge4$. One shortcut step then traverses exactly two ordinary steps, and the omitted intermediate value cannot be 1. Expanding each shortcut step, or deleting each such intermediate value, preserves the visit to 1 in both directions. Even a convention requiring $k\ge1$ gives the same question at the starting value 1, since $T^2(1)=C^3(1)=1$. The number of steps does depend on the convention. [Erdős Problem 1135](https://www.erdosproblems.com/1135) · [Local Lean equivalence](../../ConjectureLab/Collatz.lean#L59-L65)

## How far the computation reaches

Each upper endpoint below is **exclusive**. Showing that every new start $n>1$ reaches a positive value smaller than $n$ suffices: strong induction then supplies the rest of the trajectory to 1.

**The project's contiguous prefix reaches $1\le n<H=2\,392\,518\,189\,264\,310\,108\,160$, conditional on Barina's project results.** The table records exactly which range each result adds to the preceding ones.

| Evidence | Newly covered range | Exclusive contiguous endpoint | Verification |
| --- | --- | --- | --- |
| David Barina, milestone reached 15 January 2025, published 2 May 2025 | $[1,2^{71})$ | $2^{71}=2\,361\,183\,241\,434\,822\,606\,848$ | Peer-reviewed computational result. The endpoint itself reaches 1 by 71 halvings. [Project log](https://pcbarina.fit.vut.cz/) · [Paper, Sections 2 and 6](https://doi.org/10.1007/s11227-025-07337-0) |
| Barina's live project, 27 November 2026 at 14:42:02 +0100 | $[2^{71},B)$ | $B=2\,175\,982\,616\cdot2^{40}=2\,392\,518\,188\,130\,438\,742\,016$ | The project reports all earlier work units verified. Unit 2,175,982,616 was the first with incomplete status. [Live project](https://pcbarina.fit.vut.cz/) |
| M3 Pro, 27 November 2026, Metal | $[B,F)$ | $F=B+2^{40}=2\,392\,518\,189\,229\,950\,369\,792$ | All $2^{40}$ starts descended. The block took 56.513 s of scan time. CPU and Metal also agreed on a $2^{34}$-start interval inside this block. [Replay and timings](../../tools/collatz-search/README.md#apple-m3-pro-control-runs) |
| M3 Pro, 27 November 2026, Metal and CPU | $[F,G)$ | $G=F+2^{34}=2\,392\,518\,189\,247\,130\,238\,976$ | Four Metal checkpoints and a full CPU replay agreed. All 17,179,869,184 starts descended. Scan times were 1.008 s on Metal and 5.014 s on the CPU. [Replay and timings](../../tools/collatz-search/README.md#apple-m3-pro-control-runs) |
| M5 Max, 28 November 2026, Metal and CPU | $[G,H)$ | $H=G+2^{34}=2\,392\,518\,189\,264\,310\,108\,160$ | Both runs verified all 17,179,869,184 starts in four blocks. [Paired run and timings](#m5-max-lane-71-comparison) |

John Fairfax-Ball reported 7,936 consecutive batches on 14 October 2026 covering $[B,E)$, where $E=B+79\,852\,170=2\,392\,518\,188\,130\,518\,594\,186$. We replayed this interval using exact integers. Even starts halve immediately. For $n\equiv1\pmod4$ in this interval, two shortcut steps reach $(3n+1)/4<n$. The other 19,963,042 starts all descended, with a maximum of 360 shortcut steps to first descent. [Fixed run report](https://github.com/jfairfaxball-348/CEML/blob/d88d8fb8bfd88e92a348891f80d5723479bb68f5/docs/RUN1_PROGRESS.md#L8004-L8008) · [Batch table](https://john-fairfaxball-research.vercel.app/collatz) · [Independent replay](verify_frontier.py)

On 27 November 2026 an additional Python run verified $[E,2\,392\,518\,188\,130\,652\,811\,914)$, a block of $2^{27}$ starts. It took 43.99 seconds on an Apple M3 Pro with one Python 3.9.6 process. A control run of $2^{23}$ starts beginning at $2^{71}$ took 2.77 seconds. Both runs contributed checks within the prefix in the table. [Verifier](verify_frontier.py)

Checking a huge individual input answers a different question about the computation. Andreas-Stephan Elsenhans reports a successful run for a number with **20 billion decimal digits** in §4.6. The paper gives no exhaustive verification of the intervening integers. [Research in Number Theory, 24 November 2026](https://doi.org/10.1007/s40993-026-00811-5)

## M5 Max lane 71 comparison

On 28 November 2026, we ran the four-block pilot on an Apple M5 Max with 18 CPU cores and 40 GPU cores, macOS 26.6.2, and Rust 1.100.1. Metal ran first with four host threads. The CPU replay used 18 Rayon threads. Each run started with a fresh state at $G$ and used the same exclusive target $H$, $2^{32}$ starts per block, a 24-bit sieve, and a limit of 10,000 shortcut steps. [Source revision](https://github.com/ViktorBystrov72/lean-conjecture-lab/commit/f06f8b30e366269df074c5196ce6a4208be72ea7) · [Replay commands](../../tools/collatz-search/README.md#run-a-pilot-with-an-explicit-stop)

Before the pilot, both backends passed the control on `[2392518188130518594186, 2392518188131592336010)` with an 18-bit sieve. Each sieved 1,043,042,304 starts, checked 30,699,520 orbits, and returned an empty unresolved list. The control scans took 0.034704792 s on Metal and 0.140093500 s on the CPU.

| From | To, exclusive | Metal scan (s) | CPU scan (s) |
| ---: | ---: | ---: | ---: |
| `2392518189247130238976` | `2392518189251425206272` | 0.063276333 | 0.414930083 |
| `2392518189251425206272` | `2392518189255720173568` | 0.063727166 | 0.412685583 |
| `2392518189255720173568` | `2392518189260015140864` | 0.063432209 | 0.408971375 |
| `2392518189260015140864` | `2392518189264310108160` | 0.061554875 | 0.408146875 |
| **Total scan** | | **0.251990583** | **1.644733916** |
| **Elapsed `work` command** | | **0.394893084** | **1.726106125** |

The scan totals sum the per-block times in the saved journals. The elapsed `work` times also include process startup, sieve construction, backend setup, and checkpoint writes. For this pair of runs, Metal delivered **6.53× the CPU scan throughput** and **4.37× the throughput across the full command**.

Each block sieved 4,221,602,560 starts and checked 73,364,736 orbits on both backends. Every block returned `unresolved: []` and `exact_replays: 0`. The saved coverage in each state reports the same gap-free interval `[2392518189247130238976, 2392518189264310108160)` and the same conditional contiguous endpoint `2392518189264310108160`.

## What is known for infinitely many starts

| Result | Quantifiers and conclusion |
| --- | --- |
| Riho Terras (1976) | The set of starts whose orbit eventually falls below the starting value has natural density one. An exceptional set of density zero is compatible with this theorem. [Original paper](https://doi.org/10.4064/aa-30-3-241-252) |
| Ilia Krasikov and Jeffrey Lagarias (2002 preprint) | For all sufficiently large $x$, at least $x^{0.84}$ integers below $x$ have 1 in their forward orbit. The bound in iXBT is a **count**. Dividing by $x$ gives a lower bound of order $x^{-0.16}$ for the proportion. [Authors' paper](https://arxiv.org/abs/math/0205002) |
| Terence Tao (2019 preprint, 2022 journal article) | For **each** function $f(n)\to+\infty$, the set of starts for which $\min_{k\ge0} C^k(n)<f(n)$ has **logarithmic density one**. This means the sum of $1/n$ over exceptional $n\le X$, divided by $\log X$, tends to zero. The article's example of a fixed threshold of 1000 falls outside the hypothesis. Tao explicitly discusses the fixed-bound question in Remark 1.4. [Theorem 1.3 and Remark 1.4, corrected v7 of 16 July 2026](https://arxiv.org/html/1909.03562v7#S1.Thmtheorem3) · [Journal article](https://doi.org/10.1017/fmp.2022.8) |

Lech Mazur's 6 September 2026 manuscript reports that a positive lower natural density of starts reaches 1 within $10.46\log n$ ordinary steps. Its release records a Lean build and lists publication review as pending. Kenny Lau's October preprint gives an explicit lower bound for that proportion and links a formalization. Positive lower density permits infinitely many exceptions. These are partial results with different conclusions from Tao's. The external builds are reported by their projects. [Mazur, v2.1](https://www.proofatlas.ai/formalizations/positive-density-log-time-collatz/) · [Lau, v2](https://hexagonmath.org/2610.00249v2) · [Lau's code at a fixed revision](https://github.com/AxiomMath/CollatzPositiveDensity/tree/c2e1f71e5ac8f54292d633cda70d23853c4e2c42)

## What happened to recent claims

- **Proposed proof, revised.** Toshiharu Kawasaki's arXiv v1 (28 February 2025) claimed a proof by a fixed-point theorem. In v2 (7 March), the author changed the title and concluded §3 by identifying cases where the fixed-point hypotheses fail. The preprint remains on arXiv in its revised form. [Original abstract](https://arxiv.org/abs/2502.20642v1) · [Revised argument, §3](https://arxiv.org/html/2502.20642v2#S3)
- **Proposed proof, withdrawn by its author.** Joel Cruz Cabrera's July 2026 claim relied on checking twelve odd representatives modulo 24. The author withdrew it in September. One can see the obstruction directly: 1 and 25 are congruent modulo 24, but the odd parts of $3\cdot1+1=4$ and $3\cdot25+1=76$ are 1 and 19, which differ modulo 24. [Author's withdrawal](https://github.com/joelcanary/collatz-kodama-observable/blob/b77664dec222ff422667cf69344aac5ec1a988a9/docs/withdrawn-claims.md)
- **AI-assisted disproof, invalidated.** On 25 July 2026 Ramana Kumar published a purported Lean proof that some positive orbit never reaches 1, without giving a specific start. On 28 July Kiran Gopinathan reduced the argument to a proof of False. Lean's developers confirmed a kernel bug, fixed it and published a postmortem on 1 August. This establishes why the proposed disproof fails. [Original claim](https://github.com/xrchz/CollatzLean/blob/a79357462a33d2a6babd4cf6c8d8bcd25425d653/README.md) · [Lean developer's postmortem](https://leodemoura.github.io/blog/2026-8-1-postmortem-for-kernel-soundness-bug-14576/)
- **November index entry.** The aiXiv problem index marked the conjecture “claimed resolved”. The cited 16 November preprint by Justin Bondurant-David concerns the minimum attained by almost all **prime** starts, with a growing threshold and a weighted density on the primes. Its abstract makes this scope explicit. [Index entry](https://aixiv.online/problems/collatz-conjecture) · [Author's preprint](https://doi.org/10.5281/zenodo.24286158)

## What Lean checks

Google DeepMind's Formal Conjectures records the ordinary step and the full universal assertion in the declaration **CollatzConjecture.collatz_conjecture**. At revision **ea8e3e198ded6fc73efb7f5653b74b28ac4ae1a8**, the declaration is tagged *research open* and its body is **sorry**, a placeholder accepted by Lean. That revision pins Lean 4.33.1. [Exact declaration and body](https://github.com/google-deepmind/formal-conjectures/blob/ea8e3e198ded6fc73efb7f5653b74b28ac4ae1a8/FormalConjectures/Wikipedia/CollatzConjecture.lean#L43-L54) · [Upstream toolchain](https://github.com/google-deepmind/formal-conjectures/blob/ea8e3e198ded6fc73efb7f5653b74b28ac4ae1a8/lean-toolchain)

The local module uses only Lean's standard library and the repository's pinned Lean 4.36.0. It defines the open statement as a **Prop**. Its two public theorems establish the equivalence of the two reachability predicates for every start and verify the article's example of 27. With the start at step 0, the first visit to 1 is at step 111, and the maximum through that visit is 9,232, attained at step 77. Lean’s axiom audit lists only the standard `propext`, `Classical.choice` and `Quot.sound` for the equivalence. The calculation for 27 has no axiom dependencies. [Local statement and proofs](../../ConjectureLab/Collatz.lean) · [Local toolchain](../../lean-toolchain)

To repeat the standalone Lean check and the finite interval replay, run from the repository root:

~~~sh
lean -DwarningAsError=true ConjectureLab/Collatz.lean
python3 results/collatz-3x-plus-1/verify_frontier.py
python3 results/collatz-3x-plus-1/verify_frontier.py --start 2392518188130518594186 --count 134217728
~~~

The project build and compiled-module check also pass with the pinned toolchain:

~~~sh
lake build
lake env leanchecker ConjectureLab.Collatz
~~~
