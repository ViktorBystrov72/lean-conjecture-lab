# First continuous search for an 18-square improvement

We ran 29,407 numerical starts in a square whose side was allowed to shrink. The 18 tiles could translate and rotate. None of the seven batch winners became a strict improvement after rational reconstruction. The smallest certified side exceeded the Hämäläinen side by approximately $3.62285533\times 10^{-15}$. This experiment samples the continuous problem. Its finite list of initial conditions does not exhaust possible packings.

| Initialization | Batches | Starts |
| --- | --- | ---: |
| Historical layouts, perturbations and adaptive basin hopping | a–e | 18,700 |
| 5-by-5 grid with an asymmetric perturbation for each of 5,497 symmetry representatives | grid | 5,497 |
| Add or remove tiles in published packings of 17, 19, 20, 21 and 22 squares | neighbors | 5,210 |

[Overall counts](summary.json) · [Batch winners and individual summaries](batches/) · [Best numerical finalist](batches/batch-e/best.json) · [Exact comparisons](exact-results.txt)

## Recheck the saved results

From this directory, Python 3 can check the seven outputs without network access or third-party packages.

```sh
python3 exact_rescale.py batches/*/best.json
```

The checker rounds angles to rational half-angle tangents, computes a sufficient dilation of the centres using the four possible separating axes for each pair, then verifies all walls and pair separations using rational corner coordinates. The rational packing retained for the best of the seven is also checked in [Lean](../Trial.lean).

## Repeat the numerical experiment

Create a virtual environment with Python 3.13, install the [pinned dependencies](requirements.txt) and run from this directory:

```sh
python -m pip install -r requirements.txt
python replay_search.py /tmp/pack18-history-run
```

The output directory must be new. For a single batch add, for example, `--batch e`. All seven batches run with the archived seeds and schedules. Compiling the optimizer requires a C++17 compiler. The runner stores the shared library, logs and generated candidates in the requested directory. Floating results may vary with the platform and numerical libraries.

Four historical starting layouts are archived in [seeds](seeds/). Mira Cult's six-tilt floating point seed is calculated from the pinned external coordinates fetched by [the layout loader](../layouts/fetch_mira.py). Neighboring witness YAMLs are fetched only for batch `neighbors` at revision `c5775bae40085f67f4c30f8916b0d6e998c304ab`, with SHA-256 verification before parsing. [Historical survey, Figure 7](https://erich-friedman.github.io/papers/squares/squares.html#figure7) · [Neighboring layouts](https://github.com/jlevy/squares/tree/c5775bae40085f67f4c30f8916b0d6e998c304ab/packing/witnesses/known-best) · [Mira Cult’s coordinates](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/six-tilt18.json)
