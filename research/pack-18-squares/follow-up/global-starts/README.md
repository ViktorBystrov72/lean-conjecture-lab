# Fresh-start compression in a sheared container

We looked for 18 unit squares fitting in a square of side less than $H=(7+\sqrt7)/2$. The method generated all starting centres and orientations from scratch. It used no published packing, rack assignment, fixed tile or finite list of final poses.

## Experiment

We ran 7,200 independent initial conditions in three disjoint seed ranges of 2,400 each, starting at 1828000, 1831000 and 1834000. The four generators contributed 1,800 starts apiece:

| Family | Initial arrangement |
| --- | --- |
| Maximin | Sequentially choose a point with large randomized distance to its nearest predecessor. |
| Grain boundary | Join independently rotated and shifted square lattices across a random line, then select and disturb eighteen poses. |
| Stripes | Randomly distribute the eighteen tiles over three to six differently slanted strips. |
| Shells | Populate two staggered rings with random phases and radial distortions. |

All 7,200 starting fingerprints differed after ignoring labels and testing the eight box symmetries, rounding the fingerprint coordinates to eight decimal places. The geometry used by the search kept full numerical precision.

Every tile had two translation coordinates and an independent angle throughout the physical search. Contact forces came from squared positive overlaps on separating axes and the four soft walls of a parallelogram. We grew the tiles asynchronously, varied the aspect ratio, and cyclically sheared the chamber. Two subsequent compression and release cycles changed the individual tile sizes out of phase and allowed cooperative motion before returning the tiles to unit size in a square chamber. FIRE relaxation was followed by an unrestricted square-container optimization after each cycle. A finite-difference control checked all 54 components of the new force law. [Force model](chamber.cpp) · [Seed generation, annealing and adjustment](run.py)

The best of the three physically relaxed snapshots at each independent start underwent exact rational repair. Thirteen resulting sides were below 4.824 and 71 below 4.86. The best among all fresh starts exceeded $H$ by about $2.9920\times 10^{-10}$.

## Contact-chart refinement

We refined each of those 71 finalists. On each trial chart, every pair of squares received a signed separating face normal from one of its two frames. For a given angle vector the constraints on the centres and enclosing side were linear. We minimized the side by linear programming, used dual multipliers to compute its angular derivative where defined, and ran bounded L-BFGS searches on perturbed charts. Some charts temporarily grouped nearly parallel directions. The final physical updates released every angle. The 38,053 LP evaluations are internal to the 71 refinements. [Implementation](charts.py)

The best rational result came from shell start **1831527**:

$$
L=\frac{1062145690125958532580690114243370876769}
        {220230784699492755782557199201114840218}
=4.82287565553229810731544167135\ldots .
$$

It is larger than $H$ by $2.8120646338\ldots\times10^{-15}$. Nineteen refinements reached a certified side within $10^{-8}$ above $H$. One nominal LP side equalled the machine approximation of $H$, which itself rounds below the mathematical value. Exact coordinates gave no strict improvement. Lean verified the feasibility of the best rational witness and the strict sign of the difference. The result applies to this witness. [Exact witness](best-rational.json) · [Lean proof](Trial.lean) · [Run summary with hashes](summary.json)

## Reproduce

The exact audit uses Python's standard library. From this directory:

~~~sh
python3 ../patch/exact.py best-rational.json
~~~

For a floating replay use a C++17 compiler and the versions of Python, NumPy and SciPy used by the [first numerical search](../../search-history/README.md). The output directory must be new.

~~~sh
python3 replay.py /tmp/packing-fresh-starts --jobs 2
~~~

From the project root, the Lean check is:

~~~sh
lake env lean -DwarningAsError=true research/pack-18-squares/follow-up/global-starts/Trial.lean
~~~

The replay uses the existing [square-container relaxation](../../search-history/packing.cpp) and [exact rational repair](../patch/exact.py). Chamber-force calculations and chart search are specific to this experiment. On our machine the packaged replay reproduced the six per-batch CSV files and the final rational witness byte for byte. Numerical trajectories can differ across platforms.
