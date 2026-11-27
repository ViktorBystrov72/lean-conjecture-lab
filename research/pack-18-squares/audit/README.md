# Targeted physical controls on the proposed lower-bound proof

Mira Cult reports a computer-assisted proof of the exact 18-square optimum. We looked for a specific failure mode: could a feasible packing in the rational test box of side $U=4.822876$ be sent to a branch declared empty, or be removed by the geometric enclosures of a retained branch? All tested historical configurations survived. These tests leave the unrestricted lower-bound claim undecided. [Pinned source and proof](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18) · [Prior independent review](https://github.com/jlevy/squares/issues/1050#issuecomment-7059935258)

## Exact results

We independently assigned tiles to their nearest strictly interior marks in the rotated maximum norm and enumerated the 187 symmetry classes of triples of unused marks. We then evaluated the published terminal restrictions on each possible canonical reflection of each physical packing, with all closed angular bands compatible with the tile orientations.

| Layout | Orbit | Reached leaf or leaves | Action |
| --- | ---: | --- | --- |
| Hämäläinen | 53 | 28.8 | chord |
| Gustafson | 82 | 9.1 | faces |
| Cantrell | 137 | 2, 0 | faces |
| Gensane–Ryckelynck | 53 | 0.0 | chord |
| Mira six-tilt | 53 | 0.0 | chord |

The kernel test obtains convex pose polygons and angle bands from the pinned external geometry worker. An independent exact test checks the historical coordinates and rational translated witnesses against these polygons. All 18 tile positions survived in each of the eight tested witness/symmetry/leaf combinations. For the Gustafson and Cantrell historical placements, the four extreme translations of the entire assembly in the box suffice to check every rigid translation on three applicable routes. [Historical routes](receipts/exact-routes.txt) · [Kernel controls](receipts/kernel-check.json) · [All rigid translations](receipts/rigid-slides.json) · [Source layout provenance](../layouts/README.md)

The fixed-orientation LP screen first tried 7,680 extremal points and 7,680 interpolations from the historical layouts. One numerical proposal failed exact rationalization. Among 6,528 attempts to reach specified empty leaves, fixed angles excluded 264, and the selected LP models reported the other 6,264 infeasible. Further searches from three rational controls in orbits 92 and 115 made 2,000 LP proposals and 2,000 interpolations. Of 540 targeted checks, fixed angles excluded 450 and the restricted LPs reported 90 infeasible. These counts include repeated charts. The LP screens do not prove emptiness of a continuous terminal region. [First screen](receipts/search-free.log) · [Second screen](receipts/search-alternative.log) · [Three rational controls](controls/)

## Replay

The exact classification uses Python 3.10+, Git and tar. From this directory:

```sh
python3 replay.py
python3 replay.py --kernel
```

The runner fetches the pinned Git commit into temporary storage, verifies the replay tree ID `6c2f791f184e059e78e71a24bcb13fc32e0dd377`, and exports the corresponding source. With `--kernel`, it also invokes the original Python preparation scripts and a C++17 compiler named `g++`, then rechecks the saved JSON receipts for the eight sample routes and the three all-translation controls. If the Mira layout has not been materialized, the runner obtains it from the same pinned archive. To use an existing Git clone with that commit instead of accessing GitHub, add `--source /path/to/clone`. Generated kernel code, binaries and polygon caches stay in temporary storage.

The optional `--search` flag repeats the floating LP screens. It requires NumPy and SciPy from [the numerical requirements](../search-history/requirements.txt). The search logs are historical observations and floating proposals may vary with the platform. Keep Python assertions enabled throughout the replay.
