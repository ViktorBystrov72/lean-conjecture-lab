# Four special classes at side 4.80 using independent pose enclosures

For each of the four double-probe classes, every leaf is excluded at the **true container side $L=24/5$**. The rack stays in its original box of side $U=4.822876$. We centre the true container inside it. All outer centre polygons for this experiment come from our independent geometry program. Mira Cult’s tables supply candidate cuts, row roles and symmetries. Its geometry kernel, final enclosures and verdicts are not used in this replay.

| Orbit | Direct continuous-geometry contradiction | Two-probe guard | Total leaves |
| ---: | ---: | ---: | ---: |
| 82 | 20 | 0 | 20 |
| 92 | 16 | 3 | 19 |
| 115 | 19 | 0 | 19 |
| 137 | 2 | 4 | 6 |
| **Total** | **57** | **7** | **64** |

The seven guards are 92:0.0, 92:4.0, 92:4.2 and 137:0, 137:3, 137:4, 137:5. Each certifies the conditional inequality $L\ge(7+\sqrt7)/2$, contradicting $L=24/5$. Equivalently, the required squared projection allowance is at least 4 while $(L-3)^2+(L-4)^2=97/25<4$. All leaves except 137:1 ran at 64 angular bands with a cap of 35 rounds. The 96-band pass on 137:1 found intersecting guaranteed interiors for owners 1 and 3 at zero-based round 16.

The replay rechecks the complete root/leaf coverage for the four cases, including the reflected root comparisons in orbits 82 and 92. The geometry kernel interprets angular cuts as closed physical half-intervals. Coordinate cuts stay in the original rack frame. A guard run reads the output centre polygons at each live angle separately and rounds their coordinate bounds outward from nanounits to microunits. Each wall probe is measured against the actual walls of the smaller container, so the wall translation cancels. [Geometric checker](../empty-cover/README.md) · [Endpoint argument](README.md) · [Complete 64-leaf receipt](side480.json)

From this directory with Python 3.10+ and a C++17 compiler:

~~~sh
python3 side480.py --jobs 2
~~~

Use `--table-dir /path/to/pinned/replay` for offline inputs or `--case 137` to select one orbit. By default the script builds our independent kernel with direct endpoint supports. With a prebuilt binary, pass `--exe /path/to/kernel`. Each terminal is recomputed, and the program accepts only an actual geometric contradiction or a successful guard on that case’s freshly regenerated polygon dump. The receipt records the exclusion method and the first run’s exact interval diagnostics. This four-orbit result must be combined with other independent proofs to conclude a bound on unrestricted packings.
