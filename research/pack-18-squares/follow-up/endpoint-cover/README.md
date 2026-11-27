# Do the six endpoint tables cover every pose?

**Yes, up to the geometric symmetries of the occupied rack.** We independently checked the domains of all 193 terminal records for the six exceptional classes in Mira Cult's proposed 18-square theorem. This is a statement about the completeness of the cuts. A terminal labelled **empty** still needs a proof of geometric emptiness, and a terminal labelled **chord** or **faces** still needs a valid lower-bound argument. Four of the empty labels follow directly from contradictory cuts. [Pinned source and terminal lists](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay) · [Independent checking code](verify.py) · [Exact receipt](receipt.json)

| Case | Root regions | Terminal records | Empty label | Chord label | Faces label |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 53 | 33 | 114 | 43 | 42 | 29 |
| 55 | 13 | 15 | 8 | 4 | 3 |
| 82 | 13 | 20 | 14 | 0 | 6 |
| 92 | 5 | 19 | 10 | 0 | 9 |
| 115 | 13 | 19 | 14 | 0 | 5 |
| 137 | 6 | 6 | 0 | 0 | 6 |
| **Total** | **83** | **193** | **89** | **46** | **58** |

## What counts as coverage

A state gives real coordinates and a square orientation for each of the 18 owners. The verifier works on the full product of coordinate and angle ranges, including assignments which fail the packing constraints. This proves coverage for the physical subset. Mark ownership is unchanged up to relabelling under an isometry of the test box. We use only isometries preserving the current set of occupied marks.

Centre coordinates are measured in millionths of a unit, from 0 to 4,822,876. Operations 0/1 are closed upper/lower cuts on $x$, and 2/3 are closed upper/lower cuts on $y$. For the orientation take a quarter-turn chart with $t=\tan(\theta/2)$ in $[0,1]$. Band $k$ is the **closed** interval $[k/128,(k+1)/128]$. Operation 4 at $v$ retains indices $k<v$; operation 5 retains $k\ge v$. At a boundary a physical orientation can have two band indices. We intersect all index restrictions on the *same* band first, then take the union of its surviving closed intervals. This prevents treating inconsistent requirements $k<v$ and $k\ge v$ as a physical singleton. At $t=0$ and $t=1$ the physical square orientation is identical. The verifier allows both chart endpoints. [Published centre cuts](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/split_variant.py) · [Published index cuts](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/angle_split_variant.py)

For each class we reconstructed the actual terminal paths from the seven pinned JSON data files and the stated cut conventions. The six **faces** actions of class 137 are given explicitly in the published driver. Its six paths come from the base JSON. For class 53 four centre-coordinate expressions are related by symmetry. The cut used for the lower edge $a$ of its slab is the conjunction $y_5,x_{15},M-x_5,M-y_{15}\ge a$, where $M=4{,}822{,}876$. Its upper edge $b$ requires $y_5\le b$. Thus the root test uses precisely those four lower inequalities and one upper inequality when their respective bounds exist. Equivalently, one may choose an isometric representative that makes $y_5$ the least of the four quantities. Class 55 uses ordinary slabs of $x_9$. For the three residual tables the prefix is already present in the JSON data. [Class 53 driver](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/verify_full_endpoint_mask.py) · [Class 137 driver](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/verify_fork_mask.py)

## Why the finite computation suffices

Each cut table describes a union of axis-aligned boxes. On a given real axis all box tests are constant between consecutive rational thresholds. We check each threshold itself and a rational midpoint in each open interval. For an integer band-index axis we check every index. Traversing the product of these one-dimensional atoms is exhaustive. The verifier merges branches with identical sets of surviving boxes and stops early if one surviving box contains the entire remaining product.

We first check the union of the physical root boxes under the rack stabilizer. Then, at each root, we check the union of its descendant predicates for all centres and all integer band indices. Once a physical root is chosen, choose any band index witnessing that root for each owner. The descendant check covers exactly those same choices, including a branch boundary. A second decision procedure uses rational linear arithmetic in Z3 and the full concatenated leaves directly. It asks for a point outside every terminal and every stabilizer image. All six queries were unsatisfiable. It shares the input decoding, while its coverage decision is independent of the atom traversal.

## Reflections in cases 82 and 92

The physical reflection of a square gives $\theta'=\pi/2-\theta$ modulo a quarter turn, hence $t'=(1-t)/(1+t)$. It acts on the labelled pose by the same owner permutation and coordinate isometry as on the rack. We transform **exact rational interval endpoints** by this involution. The checker does not import the source's rounded reflection routine.

For case 82 the reflection exchanges $x$ and $y$. Seven of the ten base regions are retained directly. When both members of a reflected pair land among the other three base regions (indices 0, 4 and 5), it is enough to take their six unordered pairs: applying the same involution exchanges the two entries. The checker verifies that each exact paired intersection lies in the corresponding recorded root, and separately that the union of all 13 roots and their true reflected images covers the full product. The threshold $64/128=1/2$ reflects to $1/3$, strictly between $42/128$ and $43/128$. The stored coarse cuts on the two sides overlap on that band. For case 92 the relevant reflection reverses $y$, and $68/128=17/32$ reflects to $15/49$, between $39/128$ and $40/128$. [Pair-by-pair mapping and mutations](receipt.json)

Four case-82 leaves are already empty in the coordinate/band domain. Indices below start at zero:

- **7.0** requires the index of owner 10 both to be at least 64 and to be below 43.
- **8.0** and **10.0** require $x_{12}\ge 2{,}909{,}783$ and $x_{12}\le 2{,}903{,}610$.
- **11.0** requires $y_1\le 2{,}903{,}610$ and $y_1\ge 2{,}909{,}783$.

No other terminal in these six tables has contradictory raw cuts. Some nonempty regions can nevertheless be omitted using symmetry.

## A minimum subcover of the published cut boxes

We found a subcover of **185 terminal records**. Four removals are the inconsistent roots in case 82. The other four have consistent cuts. They can be omitted *simultaneously* without changing coverage up to the actual rack stabilizer.

- **92:2.1, 92:2.3 and 92:4.1.** In the base-pair construction, roots 2 and 4 correspond respectively to the equal pairs (1,1) and (2,2). When both the pose and its reflection lie in the same original base region, either one may be used as the representative; both belong to the enlarged stored root. The reflection fixes the central mark with index 10. Choose the representative with $t_{10}\ge\sqrt2-1$, the fixed point of $t\mapsto(1-t)/(1+t)$. The three discarded leaves all require $t_{10}\le53/128<\sqrt2-1$; the last inequality follows from $181^2=32761<32768=2\cdot128^2$. The unequal base pair still has all its child tests, so it needs no such choice. These three removed records have respective labels **empty**, **empty**, **faces**.
- **137:3.0.** The preimage of leaf 1.0 under reflection in the horizontal centreline requires $x_{13}\le2{,}909{,}031$ and $t_{11}\ge1/3$. Every point in leaf 3.0 already satisfies $x_{13}\le2{,}900{,}673$ and $t_{11}\ge1/2$. Its reflected pose is therefore checked by 1.0. Both records have the label **faces**.

The remaining 185 labels are **83 empty, 46 chord and 56 faces**. The standard-library checker directly tests the union of the remaining complete leaf boxes under the stabilizer, in addition to its two-level check of the original cover.

**185 is the exact minimum for this box-cover question.** For each retained record, a [private rational assignment](private-points.json) lies in that record’s symmetry orbit and in no other original record of its class. Thus every subcover drawn from the 193 original records must include all 185 of them. The values in the private certificate use defaults $(x,y,t)=(M/2,M/2,2/5)$ for absent coordinates. Each supplied centre coordinate is strictly in the elementary wall inset $(500000,M-500000)$, and every angle lies strictly inside its quarter-turn chart. These are points in the ambient cut domain. They are not claimed to obey the ownership and pairwise-disjointness constraints, so geometric arguments could reduce the amount of work still further.

The private assignments were located with Z3 and then checked by the standard-library program without an SMT solver. It maps each rational point **forward** by every stabilizer element and evaluates the literal source cuts on one common angular-band index per tile, across every original leaf. This separate check uses neither the pulled-back boxes nor the coverage traversal. It demands that the set of matching source records be exactly the singleton printed for that witness.

## Reproduce

Run from this directory. Python's standard library suffices for the primary check. It only retrieves data files from the fixed Git revision, compares their SHA-256 hashes, and runs the local checker. For offline replay pass the upstream data directory with **--data**.

~~~sh
python3 verify.py --output /tmp/pack18-endpoint-cover.json
cmp receipt.json /tmp/pack18-endpoint-cover.json
~~~

The optional second check needs the Python Z3 binding (tested with version 5.4.1). The extra flag searches for private assignments against all the original records:

~~~sh
python3 direct_z3.py --irredundant
~~~

Controls reject an omitted descendant, omission of the stabilizer in case 82, and an inward perturbation of its reflected angle range. Concrete assignments outside the mutated covers are in the receipt. They certify a gap in the deliberately damaged cut tables and make no claim to be feasible packings.
