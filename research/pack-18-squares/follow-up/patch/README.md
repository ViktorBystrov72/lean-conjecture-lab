# Continuous cavity and contact searches for 18 unit squares

We searched for a square of side strictly smaller than $H=(7+\sqrt7)/2$ containing 18 disjoint-interior unit squares. The experiment made 15,800 new numerical starts or local path attempts with freely varying tile centres and orientations. All retained exact witnesses have enclosing side greater than $H$.

| Search | Attempts | What varied |
| --- | ---: | --- |
| Cavity reinsertion | 4,800 | Remove 4–9 tiles from a connected cavity, two cavities, a strip, or scattered holes. Refill with newly sampled continuous poses. |
| Donor recombination | 8,400 | Transform a different configuration by a common rotation, translation and possible reflection. Select 4–9 donor tiles that best fit among the surviving tiles in the recipient. |
| Perturbed-pose Taylor search | 1,600 | Generate motions in the contact-velocity cone with zero initial side derivative. Optimize second-order corrections with constraints linearized at finite displacements. |
| Material-contact curvature search | 1,000 | Track points of wall and tile contacts as the tiles turn. Use their quadratic motion to propose paths, then evaluate the actual displaced squares. |

## Best witness

The smallest exactly certified side from these runs is

$$
\frac{5523738281607369412151538109163}{1145320484319581724530881381256}
=4.8228756555322959656054854399702\ldots .
$$

This exceeds $H$ by about $6.70355\cdot 10^{-16}$. The sign is decided before rounding by comparing $(2L-7)^2$ with 7, with $2L-7>0$. The [rational witness](best-rational.json) gives the centre and half-angle tangent for each of the 18 squares. The [numerical precursor](best-source.json) records the floating-point positions and angles. Lean also proves both that this concrete placement fits and that its side is strictly greater than the target. [Lean witness](Trial.lean)

For the cavity and donor experiments, the outside tiles were held fixed while the inserted tiles grew from smaller squares to unit size inside the chosen region. The search then released the centres of all tiles and optimized the enclosing side. The angle updates included both individual rotations and nearly parallel groups rotating together. Of 13,200 trials, 1,699 finalists had a floating repaired side within $10^{-9}$ above the target and were converted to rational poses with each of two denominator limits.

Both local-path searches start from the five historical realizations in [the first study](../../README.md). They use the contact inequalities to obtain numerical velocity proposals at $L'=0$. For the finite-displacement model, 1,075 of 1,094 feasible correction LPs predicted a side-reduction coefficient below $-10^{-7}$. Comparing the actual geometry at finite steps rejected those apparent gains. In the material-contact model, none of the 1,000 correction LPs produced that numerical signal. Across both path searches we compared 10,400 finite placements by exact arithmetic, including a relaxed continuation for every direction. These LP experiments do not establish second-order rigidity. A change of supporting edge can invalidate a local Taylor prediction.

## Reproduce

The exact audit requires only the Python standard library. It reconstructs the four vertices of each unit square, checks the container walls and tests all 153 pairs by direct projections.

```sh
python3 exact.py best-rational.json
```

From the repository root, replay the Lean proof with `lake build ConjectureLab.SquarePacking` followed by `lake env lean -DwarningAsError=true research/pack-18-squares/follow-up/patch/Trial.lean`.

The numerical search uses a C++17 compiler and the NumPy/SciPy environment in [search-history/requirements.txt](../../search-history/requirements.txt). With those installed, run from this directory:

```sh
python3 replay.py /tmp/packing-18-patch-replay --jobs 2
```

The output directory must be new. To check the build and two starts per batch or starting geometry, append `--smoke`. Use `--batches` to select individual batches. The script builds both native kernels, loads the four archived historical seeds and reconstructs the fifth with the [pinned six-tilt source loader](../../layouts/fetch_mira.py). Fetching the fifth seed requires network access on a fresh checkout.

[summary.json](summary.json) records each seed, sample count and best rational side. The first two batches were replayed to enable screening of every near-target finalist. Their per-start numerical CSVs matched the initial runs, so those replays are counted once. All eight packaged batches were replayed in fresh output directories. Every per-attempt CSV and the eight best rational witnesses matched the originals byte for byte. Their SHA-256 digests are recorded in the summary. Floating paths can depend on the compiler and numerical libraries. The stored rational witness is directly verifiable across platforms.
