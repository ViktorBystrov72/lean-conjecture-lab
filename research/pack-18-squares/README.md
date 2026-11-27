# Eighteen unit squares

**Research status, November 27, 2026.** We are looking for 18 unit squares with disjoint interiors that fit in an axis-aligned square of side strictly less than $H=(7+\sqrt7)/2$. Each tile may rotate independently and boundary contact is allowed. Our search has produced no such packing.

## Prior claim

Hämäläinen's 1980 construction attains $H$. On November 20, 2026, Mira Cult published a computer-assisted proof claiming the matching unrestricted lower bound. The Squares Project records an independent AI audit: it confirmed the construction, the covering by 21 marks, and the 187 symmetry classes. The author's implementation accepted all 428 terminal regions. The independent implementation was inconclusive on its six sampled terminals. The verdict was *partially verified, no gap found*. The project still records $4.705\le s(18)\le H$. This distinction matters for any priority claim. [Survey and historical layouts](https://erich-friedman.github.io/papers/squares/squares.html#figure7) · [Mira Cult's proof](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18) · [Independent audit](https://github.com/jlevy/squares/issues/1050#issuecomment-7059935258) · [Case register](https://squaremath.org/cases/18.html)

## Continuous search

We ran 29,407 local optimization starts. The runs comprise 18,700 starts seeded from several layouts and perturbation schemes, 5,497 symmetry representatives of a family of 5-by-5 grid masks, and 5,210 starts derived from published 17-, 19-, 20-, 21- and 22-square arrangements. Each run optimized the tile centres and angles. The finite list of grid masks seeds continuous optimization. It does not enumerate unrestricted packings. [Run counts](search-history/summary.json) · [Search and replay](search-history/README.md)

The best candidate after exact repair of the seven batch winners fits in a square with rational side

$$
L=\frac{48228756555323457}{10000000000000097}
=4.8228756555322989181061413367\ldots .
$$

It exceeds $H$ by $3.62285533345988\ldots\times10^{-15}$. The sign comes from an exact comparison. Lean checks that these particular 18 tiles fit, and that $H<L$. The two declarations are **feasible** and **largerThanTarget**. [Concrete positions and Lean proofs](Trial.lean) · [General checker and soundness theorem](../../ConjectureLab/SquarePacking.lean)

To repair a candidate, choose a rational approximation $t$ to each half-angle tangent and use the exact frame $((1-t^2)/(1+t^2),2t/(1+t^2))$. For each pair, compute how far apart its centres must be on each of the four possible separating axes. Choose the smallest sufficient dilation of the centres for that pair, then take the maximum of these dilations across all pairs. The bounding box of the repaired squares gives a certified enclosing side. This procedure calculates a side from the coordinates themselves and can reject a spurious improvement caused by floating-point arithmetic. [Standalone Python implementation](certify_candidate.py)

## Follow-up counterexample searches

The mark-conditioned search ran 20,744 continuous starts, covering all 187 symmetry classes as initial conditions. Seven archived candidates appeared to improve on $H$ before exact repair. The best valid finalist exceeded $H$ by approximately $2.18\times 10^{-15}$. [Methods, receipts and Lean check](follow-up/rack/)

Another 15,800 starts and contact-motion directions tested larger tile replacements, recombination and curved paths away from known configurations. The best certified finalist exceeded $H$ by approximately $6.70\times 10^{-16}$. Both searches have separate replayable Lean proofs for their selected finalists. [Methods and exact finalist](follow-up/patch/)

## Exhaustive search within a finite placement pool

We also fixed a smaller rational container of side **4.8228756**. A pool of 7,140 prescribed individual poses combined historical layouts, rotations and reflections of the container, positions from other square counts, additional rational orientations and recombinations of coordinates of axis-aligned tiles. We allowed the search to mix tiles from different layouts. Two poses were declared incompatible if their interiors overlapped, as determined by exact integer projections.

In this pool **the maximum is exactly 17**. There is a feasible set of 17 positions. On the full graph, an independently generated SAT encoding of the existence of 18 compatible poses produced a contradiction. Replaying the LRAT file checked all 309,021 added clauses and the final empty clause. The nested 596-, 1,932- and 2,948-pose pools were also exhausted. The upper bound of 17 applies only to the positions and orientations in these files. [Exact poses](finite/poses.txt) · [SAT encoding and replay](finite/README.md) · [17-tile witness](finite/witness-17.txt)

For the 596-pose pool there is a second, short upper bound. A list of 46 groups of mutually overlapping poses covers every pose with weight at least 45, and the sum of the group weights is 780. A packing can contain at most one pose from each group. Its size is therefore at most $780/45=52/3$, hence at most 17. A separate program verifies each group and the matching 17-pose construction directly from the coordinates. [Weighted cover](small-pool/clique-pool-0-cover.json) · [Geometric verifier](small-pool/check_pool_cover.py)

## Exact contact constraints at five layouts

At each of the five specific placements below we obtained a short certificate in $\mathbb Q(\sqrt7)$. If a feasible motion starts there and the centres, orientations and enclosing side have right derivatives, then its initial side derivative satisfies $L'(0)\ge0$. This is a first-order obstruction. A different initial packing or a path with zero initial side derivative falls outside its conclusion.

| Starting placement | Nonzero weights in the certificate |
| --- | ---: |
| Hämäläinen | 14 |
| Gustafson, reconstruction | 12 |
| Cantrell, reconstruction | 13 |
| Gensane–Ryckelynck, reconstruction | 14 |
| Mira Cult, six tilted squares | 26 |

The three reconstructions realize the contact patterns in Friedman's Figure 7. Free tile positions may differ from the drawings. We checked that every supplied frame is a unit frame and every initial placement is feasible in exact arithmetic. [Exact input layouts and their provenance](layouts/README.md)

For a contact point $p$ on a tile centred at $c_i$, its instantaneous velocity is $v_i+\omega_i J(p-c_i)$, where $J$ rotates by a quarter turn. At a wall its normal component must respect the wall motion. At a vertex touching the open face of another tile, the normal velocity of the vertex relative to the face must point out of the tile or be zero. At a shared edge of positive length, apply the same constraint along its relative interior, then at the endpoints by continuity. An isolated corner-to-corner contact can allow alternative normals and is omitted.

These constraints have the form $Aq\ge0$, where $q$ consists of 36 centre velocities, 18 angular velocities and the side velocity. The LP proposes a sparse set of rows. Exact elimination supplies weights $y\ge0$ and a verifier checks $A^\mathsf{T}y=e_{55}$ entry by entry. Thus $L'(0)=y^\mathsf{T}Aq\ge0$. An independently written checker reconstructed the contact points and verified all five certificates. [Stress verifier](contact_stress.py) · [Independent checker](layouts/independent_stress_review.py)

## Targeted attempt to falsify the prior claim

We tried to route actual packings to branches where the published case analysis rules out a packing. In an independent calculation over the quadratic field, the Gustafson reconstruction lands in case 82, the Cantrell reconstruction in 137 and the other three in 53. The Gustafson packing follows the retained leaf 9.1 in case 82. Two symmetric representatives of Cantrell's packing reach leaves 2 and 0 in case 137. All 18 exact centres and their angle rows survive the enclosing polygons produced by the original kernel on these three routes. We also checked every rigid translation of the two exact layouts within the rational test box. Further feasible moves reached cases 92 and 115. No tested packing was falsely excluded. This is a check of specific witnesses, not independent verification of the 428 terminal implications. [Targeted audit and reproduction](audit/README.md) · [Exact routes](audit/receipts/exact-routes.txt) · [Rigid-translation checks](audit/receipts/rigid-slides.json)

## Reproduce

From the research worktree with the pinned Lean toolchain on PATH:

~~~sh
lake build ConjectureLab.SquarePacking
lake env lean -DwarningAsError=true research/pack-18-squares/Trial.lean
lake env leanchecker ConjectureLab.SquarePacking
lake env python3 research/pack-18-squares/finite/replay.py
python3 research/pack-18-squares/certify_candidate.py research/pack-18-squares/search-history/batches/batch-e/best.json
python3 research/pack-18-squares/contact_stress.py research/pack-18-squares/layouts/gustafson-exact.json --check research/pack-18-squares/gustafson-stress.json
~~~

The Lean checker verifies individual rational witnesses over the real plane. The Python stress checker verifies the field arithmetic for the first-order argument. Neither checker asserts a global lower bound for arbitrary packings.
