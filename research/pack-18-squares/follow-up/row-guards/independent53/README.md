# Full-window checks for class 53

Any 18-square packing in occupied-mask class 53 requires a container of side at least $H=(7+\sqrt7)/2$. At the full rack side $U=4.822876$, all 71 regions originally assigned a geometric endpoint argument now pass a guard using independently computed pose enclosures. The final 71 certificates use 36 chord arguments and 35 separating-face arguments. Each conclusion applies to the true container side $L$, so it excludes every $L<H$ in that region. The other 43 regions of this same class have separate integer emptiness certificates. These 114 regions cover class 53 up to its square symmetries. [Guard receipts](receipt.json) · [43 empty regions](../../endpoint-empty/) · [Domain coverage](../../endpoint-cover/)

The integer geometry starts each tile at every angle and continuous centre allowed by the four outer walls, its assigned mark and the listed cuts. Each [point trace](certificates/) proposes inner-core witnesses. The geometry checker accepts each point only after testing the exact halfplanes, then exports outward centre bounds for every surviving angular band. The seven-tile argument applies to these regenerated enclosures. Some records select a different chord, separating face or symmetry of the square from the one indicated by the original author. Their prescribed cuts are identical. The verifier recomputes the seven distinct mark preimages and evaluates the row and middle-square conditions in the selected coordinates. The true container width enters through its opposite walls. [Geometry and algebra of the guards](../README.md)

Run from this directory with Python 3.10 or later and a C++17 compiler supporting 128-bit integers.

~~~sh
python3 ../independent_rows.py 53 --sanitize
~~~

The default obtains seven public case tables from the pinned source revision and checks their SHA-256 digests. For an offline verification, append `--source /path/to/notes/geometry/unit-square-packing-18/replay`. The local certificates contain only integer point suggestions. [Source partition and proposed endpoint argument](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18)
