# The minimum side for eighteen unit squares

With arbitrary real centres and rotations, and with boundary contacts allowed, the smallest enclosing square for 18 unit squares has side
$$
s(18)=H=\frac{7+\sqrt7}{2}=4.822875655532295\ldots.
$$
Pekka Hämäläinen constructed a packing at this side in 1980. On November 20, 2026, Mira Cult posted a computer-assisted proof of optimality. The verification here uses Mira Cult's rack, case division and endpoint geometry. Separately written programs regenerate enclosures from the walls and rack and check the necessary geometric implications. Lean checks several of the underlying real inequalities. The full verification runs in C++ and Python. [Historical construction](https://erich-friedman.github.io/papers/squares/squares.html#figure7) · [Original optimality claim](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18) · [Prior external audit](https://github.com/jlevy/squares/issues/1050#issuecomment-7059935258)

## How the lower bound covers every packing

1. Suppose a packing existed in a square of side $L<H$. Area gives $L\ge\sqrt{18}>4$. Centre the container within the test box of side $U=4.822876>H$. The four true walls can move relative to the fixed marks when $L$ changes.
2. The verified 21-point rack has a mark strictly inside every unit square anywhere in the test box, in any orientation. Assign each tile a nearest mark in its own axis coordinates. Disjoint tile interiors force 18 distinct assignments. The three unused marks give 1,330 triples. The eight symmetries of the test square reduce these to 187 classes. Coordinates and angles still vary continuously in every class. [Rack verification](terminal-audit/)
3. Integer geometry excludes 181 entire classes even inside the larger box. Starting with the possible locations of each centre in each closed angular interval, the programs keep outer polygons for centres and inner polygons guaranteed to lie within the tile. Rounding enlarges the outer bounds. When no possible position remains for a required tile, or two guaranteed interiors overlap, the case is impossible. The final 45 classes have 91 checked terminal regions. [First 118 classes](terminal-audit/) · [Next 18](empty-cover/) · [Last 45](ordinary-empty/)
4. The other six classes split into 193 regions. The partition checker verifies their union up to symmetries, including boundary contacts. All 193 have independent geometry certificates, including the eight regions redundant for coverage. For 89 of them a direct contradiction agrees with the original empty label. The other 104 are accounted for below. [Partition](endpoint-cover/) · [89 emptiness proofs](endpoint-empty/)

| Class | Empty-labelled regions | Other regions | Independent proof for the other regions |
| ---: | ---: | ---: | --- |
| 53 | 43 | 71 | [Single-probe rows and bridge inequalities](row-guards/independent53/) |
| 55 | 8 | 7 | [Six guard proofs and one direct exclusion](row-guards/independent55/) |
| 82 | 14 | 6 | [Two-face guards and direct exclusions](endpoint-guards/independent-residual/) |
| 92 | 10 | 9 | [Two-face guards and direct exclusions](endpoint-guards/independent-residual/) |
| 115 | 14 | 5 | [Two-face guards and direct exclusions](endpoint-guards/independent-residual/) |
| 137 | 0 | 6 | [Double-probe two-face guards](endpoint-guards/independent137/) |
| **Total** | **89** | **104** | **193 regions accounted for** |

In every exceptional region that survives the direct exclusions, wall rows and the two intervening tiles force a positive unit direction $(a,b)$ with $2\le (L-3)a+(L-4)b$. Here $L$ is the side between the true walls. Cauchy–Schwarz gives $(L-3)^2+(L-4)^2\ge4$. Since $L>4$, the quadratic inequality implies $L\ge(7+\sqrt7)/2$, contradicting the assumed improvement. The upper bound is checked separately using exact quadratic-field coordinates for all 18 tiles and all 153 tile pairs. This proves the value of the minimum. Classifying all arrangements that attain it is a separate question. [Wall and bridge arguments](row-guards/) · [Lean lemmas](../../../ConjectureLab/PackingEndpoint.lean) · [Coordinates of the historical construction](../layouts/hamalainen-exact.json)

## Reproduction

From this directory run the following with Python 3.10 or later and a C++17 compiler supporting signed 128-bit integers.

~~~sh
python3 verify_endpoint.py --workers 3
~~~

For offline use add **--source /path/to/upstream/notes/geometry/unit-square-packing-18/replay**. The input consists of seven JSON tables checked against the pinned source digests. All point traces and independent geometry programs are local. The verifier starts with the exact packing, tests the rack, runs each ordinary and exceptional certificate, and compares the leaf identities against the partition. **--ordinary-only** stops after all 181 ordinary classes. For a quick inventory after geometry replay, run **python3 endpoint-cover/geometry_inventory.py --require-complete**. [Composite verifier](verify_endpoint.py) · [Recorded run](endpoint-replay.txt)

From the repository root, **lake build**, **lake env leanchecker ConjectureLab.PackingEndpoint**, and **lake env lean research/pack-18-squares/follow-up/endpoint-guards/WallProbes.lean** check the formal part. The translation from continuous packings to the geometric enclosures, and the geometry certificate computations themselves, are outside Lean. The work was reviewed by AI agents and has not received external mathematical peer review.
