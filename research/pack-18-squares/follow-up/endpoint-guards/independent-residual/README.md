# The 20 residual two-face branches at the full rack side

At the enclosure side $U=4.822876$, every branch labelled **faces** in classes 82, 92 and 115 of the 21-mark rack requires a container of side at least $H=(7+\sqrt7)/2$, or is already impossible throughout the test box. All eighteen tiles may move and rotate continuously. The reconstruction starts from the four original walls for every branch and uses independently verified exterior regions.

| Class | Face branches | Directly impossible at $U$ | Two-face bound $L\ge H$ | Middle-angle pairs checked |
| ---: | ---: | ---: | ---: | ---: |
| 82 | 6 | 3 | 3 | 5,627 |
| 92 | 9 | 1 | 8 | 1,292 |
| 115 | 5 | 3 | 2 | 448 |
| **Total** | **20** | **7** | **13** | **7,367** |

The source partitions contribute a further **38** leaves labelled *empty* in these classes. Their proofs are separate. The [certificate for class 137](../independent137/README.md) covers the six remaining *faces* branches, bringing the total to all 26 in these four classes.

## Reproduction

From this directory with Python 3.10+ and a C++17 compiler supporting checked 128-bit integers:

~~~sh
python3 replay.py --sanitize --jobs 3
~~~

The [checker](replay.py) uses the three [pinned case tables](tables/) to select and enumerate every faces branch. It recovers the actual mask, the full sequence of coordinate and orientation cuts, the symmetries and the wall and middle tile roles. It decompresses and hashes the [suggested interior points](certificates/), then rebuilds the [independent verifier](../../row-guards/independent480/build.py) and checks the points against all contributing halfplanes. Seven runs lose all admissible positions of a required tile. For each of the thirteen remaining runs, the verifier exports rectangles circumscribing its final polygons for all live angular bands. Their extrema are rounded outwards to the microunits used by the [directed-interval tests](../check_guards.py). The two probe gaps, middle-angle counts and the direct exclusion diagnostics are recorded in the [receipt](receipt.json).

The rack, suggested cuts, role assignments and two-face argument are due to Mira Cult. The input tables are from its pinned [source](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay). All exterior pose regions in this replay come from local integer geometry. The algebraic endpoint implication has a [Lean proof](../../../../../ConjectureLab/PackingEndpoint.lean).
