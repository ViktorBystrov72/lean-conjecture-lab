# Exact lower bound for all packings in class 55

Every packing in class 55 of the 21-mark rack requires a square of side at least $H=(7+\sqrt7)/2$. The [partition](../../endpoint-cover/) covers the whole class with 15 leaves. At the larger side $U=4.822876$, [integer geometry](../../endpoint-empty/) excludes all eight leaves labelled empty. The same geometry also excludes guard leaf 5.1. For the other six leaves our [single-probe calculation](../) establishes the exact endpoint inequality using our own outer bounds for centres and orientations. The central wall offset cancels when the opposite walls are combined, so the conclusion concerns the true side of the container.

| Leaves | Angular bands | Propagation rounds | Conclusion |
| --- | ---: | ---: | --- |
| 1.0, 3.0, 4.0 | 384 | 55 | Wall and middle-tile guard |
| 0.0, 1.1, 2.0 | 512 | 48 | Wall and middle-tile guard |
| 5.1 | 768 | 55 | Empty pose domain |

From the parent directory run the commands below. A C++17 compiler with 128-bit integers and Python 3.10 or later are required. Both commands accept an offline path to the pinned upstream replay data with **--source**. The source supplies the rack, roles and cuts. The local integer solver computes the outer polygons, rounds their boxes outwards, and tests every proposed inner point before using it.

~~~sh
python3 independent_rows.py 55 --sanitize
python3 ../endpoint-empty/replay.py
~~~

The remaining algebraic implications are formalized in [PackingEndpoint.lean](../../../../../ConjectureLab/PackingEndpoint.lean). The geometry computations run in C++ and Python. [Trace hashes and outcomes](receipt.json) · [Compressed point traces](certificates/)
