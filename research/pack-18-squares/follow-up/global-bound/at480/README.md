# An unrestricted exclusion at side 4.80

**Theorem (computer-assisted).** No 18 unit squares with pairwise disjoint interiors fit in a square of side $24/5$. The centres and orientations are arbitrary real numbers. The known packing at $H=(7+\sqrt7)/2$ gives the other end of the interval. Our conclusion is
$$
4.80<s(18)\le H=4.822875655532295\ldots .
$$

The strict lower bound uses attainment of the minimum: from a sequence of feasible sides tending to the infimum, pass to a convergent subsequence of the finitely many centres and unit frames. The wall inequalities and nonoverlap persist under this limit. Thus ruling out a packing at $24/5$ rules out equality as well. The Squares Project's register listed a verified lower bound of 4.705 when this work was done. Mira Cult previously claimed the stronger equality $s(18)=H$. Our independent computation of this weaker bound is not a claim of publication priority for the inequality. [Case register](https://squaremath.org/cases/18.html) · [Prior optimality claim](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18)

## Exhaustion

Given a hypothetical packing, centre its true square of side $24/5$ inside the test square of side $U=4.822876$. Both share all eight square symmetries. The verifier first checks that every real unit-square pose in the larger test square contains a mark strictly inside a concentric contraction. Assign each tile a nearest mark in its own frame. The 18 assigned marks are distinct. The three unused marks give 1,330 triples and 187 symmetry classes. Each computation below retains the exact true-wall inset while using marks in the coordinates of the larger test square.

| Cases | Count | Reason the class cannot contain a packing |
| --- | ---: | --- |
| Unsplit continuous-centre exclusions | 153 | Outward enclosures, inward tile cores, a vanished pose domain or a mandatory overlap. |
| Unsplit integer-trace exclusions | 27 | An independently written checker validates every proposed core point before using it. Includes direct exclusions of 82, 92 and 115. |
| 22, 54, 132 | 3 | The two complementary leaves in each class close by direct geometric contradiction. |
| 0, 53, 55 | 3 | Integer traces close all eight leaves of 0 and each entire uncut class 53 and 55. |
| 137 | 1 | Two leaves close directly. In the other four, independently computed outer pose polygons plus a wall-and-separating-face argument force $(L-3)^2+(L-4)^2\ge4$. At $L=24/5$ the left-hand side is $97/25<4$. |

The manifest lists each class exactly once. The replay regenerates its mask from the 21 marks, checks the indicated computation, and reaches all 187 conclusions. A separate pass also excluded all 64 terminal regions of 82, 92, 115 and 137, including the branches not needed by the shorter composite proof. [Manifest](manifest.json) · [Root traces and replay](verify.py) · [Three partitioned cases](three/) · [Cases 0, 53 and 55](../../row-guards/independent480/) · [64-terminal verification](../../endpoint-guards/side480.md)

## Independence and replay

The 21-point rack, the published source case tables and some split choices come from Mira Cult. The decisive pose enclosures used here and the geometric contradictions are computed by separately written programs. The seven-role or double-probe implications elsewhere in this research branch sometimes use the producer’s pose enclosures. This composite proof uses our own enclosures for the guard in case 137. It does not call a producer program to decide a case. This is a computer-assisted proof with AI review and a separate verification of the aggregation. It has not been formalized end to end in Lean or peer-reviewed by humans. [Independent aggregation review](../at480-review/) · [Main receipt](receipt.json)

Use Python 3.10 or newer, Git, and a C++17 compiler supporting 128-bit integers. From this directory run:

~~~sh
python3 verify.py --workers 3
~~~

To avoid network access, add the option **--source /path/to/Mira-Cult-math-clone** with commit 78bec6aacebf304d942a9225e16c2f18165778ff present. The pinned Git tree supplies the case data. The independent programs build in a temporary directory. Floating-point proposals in the first kernel can vary across platforms. Only exactly checked points and conservative geometric tests justify eliminations.
