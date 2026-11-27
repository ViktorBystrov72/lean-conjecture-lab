# Independent endpoint guards for the four double-probe orbits

**Result.** The directed interval checks here accept every nonempty leaf in the published case tables for orbits 82, 92, 115 and 137. These 26 leaves use two perpendicular wall probes and two independently oriented separating faces. The checks derive the side bound from the supplied outer pose enclosures. Separate full-side replays now compute the enclosures in all four classes. [Three residual classes](independent-residual/) · [Class 137](independent137/) · [The 38 empty leaves and the other exceptional empty regions](../endpoint-empty/)

| Orbit | Nonempty leaves checked | Pairs of middle-tile angular bands | Empty leaves outside this guard |
| ---: | ---: | ---: | ---: |
| 82 | 6 | 15,340 | 14 |
| 92 | 9 | 22,597 | 10 |
| 115 | 5 | 8,747 | 14 |
| 137 | 6 | 19,095 | 0 |
| **Total** | **26** | **65,779** | **38** |

The mathematical argument, initial mark grid, cut paths, role assignments and source enclosure algorithm come from Mira Cult. This package independently implements the implications from the enclosures to the endpoint hypotheses. It uses signed integer interval arithmetic at scale $10^{12}$, rounding every multiplication and division outwards. The archived inputs keep only centre bounds and angular intervals for tiles the endpoint argument actually uses. [Original argument](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/proof.md) · [Guard checker](check_guards.py) · [Orbit-137 receipt](receipt.json) · [Residual-orbit receipt](residual-receipt.json)

At the full test side **4.822876**, a second replay now independently rebuilds every enclosure for the six leaves of orbit 137 and proves its exact lower bound $L\ge H$. [Full-side class-137 certificate](independent137/README.md)

At the smaller side **4.80**, a separate replay closes all 64 leaves of these four classes using the independent geometry program for every enclosure. [Independent result at 4.80](side480.md)

## Inputs and coverage

For orbit 137 the initial mask is **0x1ffbcf**. The six leaves are the six siblings or descendants of successive splits on owners 12, 9, 13, 11 and 19. The coverage check requires both children at every internal split. A coordinate threshold may belong to both branches. The angle thresholds use the original 128-bin input coordinate. The subsequent worker refinement yields polygons over a finer grid, reaching 896 bands in these 137 inputs. Leaves 0, 1 and 4 use a vertical reflection of the whole configuration before assigning rows. The raw geometry parser checks every vertex count, integer scale and owner label. Bounds used by the guard come from the axis-aligned extrema of each polygon separately.

For the other orbits, the residual driver uses the actual concatenation of the root path and its additional cuts. It verifies the SHA-256 of each source table, then selects all leaves except those marked *empty*. Each selected action has four row lists and two different middle owners. It applies the action’s coordinate exchange and reflections to the centres, owner labels and angle endpoints. Reflection of an orientation replaces $\theta$ with $\pi/2-\theta$ modulo a quarter turn. The separate cover study checks the residual root symmetries and the coverage of the leaf paths. [Cover study](../endpoint-cover/README.md) · [Residual driver](residual_replay.py)

## Wall supports and the two faces

1. In a wall tile’s frame write its unique near-horizontal unit side as $(c,s)$ with $c>3/4$. A vertical line with horizontal distance from the centre less than $(c-|s|)/2$ crosses opposite faces. Its chord length is $1/c\ge1$. The midpoint height differs from the tile-centre height by at most $|s|/(2c)$. The bounds are recomputed separately on each live angle interval. Swapping horizontal and vertical gives the other chord. The same upper-right vertex serves as the endpoint of both probes.
2. At the terminal vertex $(p,q)$ choose probe coordinates $\xi=p-\lambda$ and $\eta=q-(b/a)\lambda$ for a middle normal $(a,b)$ with positive components. The checker constructs an interval of $\lambda$ strictly inside all required probe ranges and checks that the designated terminal chord lies above each preceding vertical chord and to the right of each preceding horizontal chord. The positive lower bound on the length of this interval is in the receipt. Row counts use disjoint interiors along each line, with allowances for a common terminal tile across the two directions.
3. If the true lower walls are $x_0,y_0$, the two bounds are $q\ge y_0+v+(p-\xi)s/c$ and $p\ge x_0+h-(q-\eta)s/c$. Multiplying by $b$ and $a$ cancels the slope error. At the opposite corner apply the same argument after a half turn. Translating the true walls inside the test box has no effect on their differences. The sum of the horizontal/vertical counts is 4/3 or 3/4. In orbit 137 it is 4/3, giving the allowance $(L-4)a+(L-3)b$.
4. For the first middle square with centre $F$ and forward normal $u$, the interval for $u\cdot(F-P)$ is either at least $1/2$, or greater than $-1/2$ while the transverse coordinate is strictly between $-1/2$ and $1/2$. A corner of the other tile cannot lie in the open middle square, since arbitrarily close points are in its own interior. It follows that $u\cdot(F-P)\ge1/2$. The same argument at the far end gives $v\cdot(Q-G)\ge1/2$ for the second middle tile.
5. A separating axis of two squares exists along an edge normal of either tile. The projected half-width sum on such an axis is at least 1. The checks first exclude transverse axes and reverse directions, leaving at least one of the forward middle normals. They then check the signed transverse guard for both possible normal choices. The signed half-angle threshold is $(t-T)/(1+tT)$ in the two stored half-angle parameters. This function increases in $t$ and decreases in $T$, so we can use its endpoint extrema. Both signs are checked if the interval spans zero.
6. The resulting projection is at least two. The two possible wall-count orders give the same Euclidean bound by swapping the normal coordinates. Area already forces $L>4$ for eighteen unit squares. Cauchy–Schwarz and the resulting quadratic inequality give $L\ge(7+\sqrt7)/2$. [Two-face Lean theorem](../../../../ConjectureLab/PackingEndpoint.lean) · [Wall, face selection and half-angle lemmas](WallProbes.lean)

## Replay

From this directory, Python 3.10 or later suffices for the offline guard checks:

~~~sh
python3 check_guards.py
python3 residual_replay.py
~~~

For orbit 137 the controls delete each of the six leaves in turn, widen a middle or terminal centre to the entire box, or allow the middle angle to fill the whole quadrant. All 24 deliberately damaged inputs must be refused.

To regenerate the exterior boxes, the following commands fetch the pinned public sources into temporary storage using the same hash-checked source retriever as the physical audit. They compile and run the original geometry worker, extract the centre extrema, and then use **our** endpoint checker. A C++17 compiler is required. An existing source clone can be supplied with **--source**. The signed-interval tests themselves do not import the producer’s guard code.

~~~sh
work=$(mktemp -d)
python3 enclosures.py --output "$work/class137.json.gz"
python3 check_guards.py "$work/class137.json.gz"
python3 residual_replay.py --regenerate --boxes "$work/residual.json.gz"
~~~

The commands above reproduce the original enclosures. For class 137 the independent replay linked above constructs tighter outer polygons from the four walls and proves all six implications directly. The other special orbits, 53 and 55, use different single-probe roles and are outside this package.
