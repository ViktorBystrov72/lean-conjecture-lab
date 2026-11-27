# Lean Conjecture Lab

Proofs and counterexamples to published mathematical questions. Each entry links to the original statement, explains the argument, and identifies the theorem checked by Lean.

## Results

| Question | Result | Lean |
| --- | --- | --- |
| [OEIS A250346](https://oeis.org/A250346) · Arrays with bounded entries and multiplicity | [Proof of Hardin’s recurrence for every length and Barker’s generating function](results/oeis-a250346/) | ✅ [Recurrence](ConjectureLab/ShiftedArrays.lean) · [Generating function](ConjectureLab/ShiftedArraysSeries.lean) |

✅ means Lean checked the full statement in the result column. The result page credits the original authors and documents the scope of the literature search.

## Computer-assisted verification

[The minimum side for eighteen unit squares](research/pack-18-squares/) is $(7+\sqrt7)/2$. This branch records an independent computational verification of Mira Cult's optimality argument for Hämäläinen's construction. Geometry checkers cover all 187 classes. Lean checks supporting geometric and algebraic lemmas. [Proof and scope](research/pack-18-squares/follow-up/endpoint.md) · [Recorded replay](research/pack-18-squares/follow-up/endpoint-replay.txt)

## Verify

From a clone with [Elan](https://lean-lang.org/install/) and Python 3 installed, run the following commands. The repository pins Lean and Mathlib to version 4.36.0.

```sh
lake exe cache get Mathlib.Algebra.BigOperators.Fin Mathlib.Data.Fintype.BigOperators Mathlib.Tactic.FinCases Mathlib.RingTheory.PowerSeries.Basic Mathlib.Tactic.Ring Mathlib.Analysis.SpecialFunctions.Trigonometric.Bounds Mathlib.Tactic.FieldSimp Mathlib.Tactic.LinearCombination
lake build
lake env lean results/oeis-a250346/Audit.lean
lake env leanchecker ConjectureLab.ShiftedArrays
lake env leanchecker ConjectureLab.ShiftedArraysSeries
python3 results/oeis-a250346/verify.py
```

The Python check runs offline. To compare against the 210 published values, download the [OEIS table](https://oeis.org/A250346/b250346.txt) and pass its path to the script with `--b-file`.
