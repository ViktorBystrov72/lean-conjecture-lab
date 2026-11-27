# Physical exclusions for all 89 empty endpoint regions

At the rational test side $U=4.822876$, no packing of 18 interior-disjoint unit squares satisfies the nearest-mark assignments and region cuts of any of the 89 leaves labelled **empty** in the six exceptional classes of Mira Cult's proposed proof. We generated new point certificates for each leaf and replayed each certificate with an independent integer geometry implementation. The initial polygons, enclosure updates, point traces and emptiness decisions are all computed locally. The published data supply the rack and the definitions of the regions. [Pinned case data](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay) · [Integer geometry argument](../terminal-crosscheck/) · [Verifier](replay.py)

| Mask class | Empty leaves checked | Required by the reduced cover |
| --- | ---: | ---: |
| 53 | 43 | 43 |
| 55 | 8 | 8 |
| 82 | 14 | 10 |
| 92 | 10 | 8 |
| 115 | 14 | 14 |
| 137 | 0 | 0 |
| Total | **89** | **83** |

The [independent covering calculation](../endpoint-cover/) reduces the full table of 193 exceptional leaves to 185 using square symmetries and cut contradictions. In that cover, four empty leaves of class 82 have conflicting cuts, and two empty leaves of class 92 are redundant under reflection. The six original leaves were each checked directly in the geometry run, including both reflected cases. The other **102** leaves in the reduced cover require a geometric lower-bound argument for their surviving poses. This package establishes only the 83 empty leaves of that cover. The ordinary mask classes form a separate set of proof obligations.

## How to replay

From this directory, use Python 3 and a C++17 compiler supporting signed 128-bit integers.

~~~sh
python3 replay.py --workers 2
~~~

By default the driver fetches seven small position-and-angle tables pinned by commit and SHA-256. For offline use, pass `--source /path/to/upstream/notes/geometry/unit-square-packing-18/replay`. It reconstructs all six mask IDs and the original paths for every empty leaf, builds the integer verifier, decompresses the point traces and rechecks each verdict. Use `--sanitize` to enable undefined-behavior checks at compilation, or `--regenerate` to generate and check a second set of point suggestions. With `--control`, the upper-resolution verifier runs on a known valid rational packing in the uncut class 53. At 1,280 bands it preserved all 18 physical poses through the three-round trace of 990 owner snapshots. [Trace archive](points.xz) · [Per-leaf parameters and hashes](receipt.json)

Centres may vary continuously and orientations range over closed angle bands. A centre cut uses its exact rational threshold. An angle cut retains any band touching the cutoff, including boundary contact. For each centre polygon and band, the verifier checks every proposed guaranteed point against all its defining integer halfplanes. It credits a leaf only when some required tile has no surviving pose. The archived runs use 64, 128, 256, 384, 768 or 1,280 angular bands. The two 1,280-band cases are 53:25.5 and 53:26.5. They use the same rational frame construction as the other cases, with a higher command-line input limit. [Angle cut implementation](../row-guards/independent480/build.py) · [Geometry kernel](../terminal-crosscheck/exact.cpp)
