# Reorienting the thirteen disk-hole survivors

At enclosing side 4.8228756, thirteen of the 128 sampled 17-tile centre sets pass the necessary empty-disk test. We inserted a trial eighteenth centre at their clipped Voronoi vertices and numerically reoptimized all 18 angles. We then released every centre, including the original seventeen, and minimized the enclosing side. We found no packing below $H=(7+\sqrt7)/2$.

## Starting points and results

The [seed file](seeds.json) gives all 13 layouts and their 37 starting vertices (counted separately for each layout). Each vertex lies in the possible centre container and has exact squared distance at least one from every existing centre. The largest-hole and square-core tests retain boundary contacts. Passing the disk test provides a numerical starting point, not a proof that a square fits. [Exact seed reconstruction](make_seeds.py) · [Parent orientation-independent test](../free_angles.py)

| Starts | Initial centre sets | Search |
| ---: | --- | --- |
| 176 | 11 layouts, 16 trials each | Rotate with the original centres pinned, then release all centres and angles |
| 480 | Layouts 126 and 127, 240 trials each | Same continuation, using both surviving vertices of each centre set |
| 960 | Layouts 126 and 127, 480 further trials each | Temporarily expand the box, rotate and perturb 5–9 tiles near the inserted centre, then recompress |

The initial angular objective gradually interpolates between disks and squares, using pairwise projections and a quadratic overlap penalty. At the square endpoint it evaluates the four separating edge-normal directions. The inserted centre can translate throughout. Each unconstrained refinement ends with a true unit-square separating-axis optimization. We converted each of the 1,616 resulting configurations to an exactly feasible rational packing by dilating the centres and recentering its bounding box. The exact lengths are upper bounds on the unrestricted optimum. A positive pinned penalty is a search diagnostic and does not prove infeasibility.

Across all trials, the best exactly verified side was $4.82287591725075946289\ldots$, larger than $H$ by $2.61718464167644\ldots\times10^{-7}$. That trial started from layout 003. The best side reached from layout 126 was about 4.826261049, and from layout 127 about 4.822876349. Centre coordinates in these final witnesses are free to differ from the 17 starting centres. [Rational witness](best-rational.json) · [Search output before repair](best-source.json) · [Results by batch and layout](summary.json)

## Reproduction

From this directory, Python's standard library suffices to verify the exact seeds and the contained, nonoverlapping rational squares in the saved winner:

```sh
python3 make_seeds.py
python3 ../../follow-up/patch/exact.py best-rational.json
```

The numerical replay also needs a C++17 compiler and the versions of NumPy and SciPy in [search-history/requirements.txt](../../search-history/requirements.txt).

```sh
python3 replay.py /tmp/packing-hole-orientations --jobs 2
```

Choose a new output directory. The original four search batches were repeated from the packaged code. The four complete per-attempt CSVs and all four batch winners matched byte for byte. Their SHA-256 digests are in the summary. Numerical trajectories on other platforms may vary.
