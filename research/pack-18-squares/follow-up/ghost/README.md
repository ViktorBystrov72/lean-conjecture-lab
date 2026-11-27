# Eighteen squares from 19- and 21-square donors

We searched for an 18-square packing with enclosing side strictly below $H=(7+\sqrt7)/2$. Both the 19-square donor and the 21-square donor were used at their published sizes as starting configurations. All centres and angles of the final eighteen tiles were free. No certified improvement was found.

## Disappearing tiles

In the first stage, each selected donor tile shrinks through a sequence of positive side lengths. Centre positions, orientations and the container side relax jointly while those tiles are still present. Trials use simultaneous shrinkage, different exponents for different tiles, or a partial reinflation to alter contacts. We then remove the small tiles, retain the eighteen surviving unit tiles, and optimize the unrestricted 18-tile objective. This differs from immediately deleting the selected tiles.

In the second stage we take each donor campaign’s best 18-square output. We insert small prospective replacement tiles while one or three existing tiles shrink. During the exchange each replacement pair has sides $\sin\phi$ and $\cos\phi$, keeping the sum of their areas one. The final optimization discards the departing tiles and releases all remaining centres and angles.

| Start and operation | New trajectories | Distinct labelled choices of departing tiles | Best certified side minus $H$ |
| --- | ---: | ---: | ---: |
| 19-square donor, shrink one | 912 | All 19 singletons, 48 trajectories each | $+2.8575870\cdot10^{-5}$ |
| 21-square donor, shrink three | 2,660 | All 1,330 triples, two trajectories each | $+4.9054733\cdot10^{-3}$ |
| 18 from the best 19-square trial, exchange one | 1,500 | 18 singletons | $+1.4338995\cdot10^{-15}$ |
| 18 from the best 21-square trial, exchange three | 1,500 | 521 triples | $+2.4628667\cdot10^{-12}$ |

The 6,572 trajectories include 3,572 from the original two donor layouts. Counts are per trajectory, irrespective of how many internal continuation steps it takes. Testing the eight symmetries of each numerical donor at tolerance $10^{-8}$ groups the original labelled choices into 11 and 1,330 classes, respectively. The choices and symmetry counts describe these two starting layouts only.

## Verification

The finalist had rational enclosing side $634588902043723/131578947368421$. For each trajectory we replaced the tile angles by rational half-angle tangents in two precisions, scaled the centre separations sufficiently to make its unit squares feasible, and compared the resulting rational sides exactly. The final winners were independently checked by corner containment and by testing separation for every pair. Lean verifies containment and disjoint interiors of the best witness, and that its exact side is strictly greater than $H$. [Best coordinates](best-rational.json) · [Lean witness](Trial.lean) · [Batch summaries](summary.json)

In 758 trials the floating objective gave a nominal side below $H$. The exact reconstruction did not validate an improvement in any of them. For example, a penalty optimum in the 21-square campaign gave a nominal side of 4.35343 with a negative constraint residual of about −0.11175. The repaired packing took side 5.01484. Search outcomes do not bound packings outside these trajectories.

## Replay

Use a C++17 compiler, Python and the pinned [numerical dependencies](../../search-history/requirements.txt). From this directory:

~~~sh
python3 replay.py /path/to/new-output
~~~

The runner builds both local libraries, fetches the two [pinned donor layouts](https://github.com/jlevy/squares/tree/c5775bae40085f67f4c30f8916b0d6e998c304ab/packing/witnesses/known-best) with SHA-256 checks, runs the four campaigns, and checks their four rational winners. To use an existing directory containing the pinned files, add `--inputs /path/to/witnesses`. The `--quick` option performs a short functional check. The full-precision hash comparison covers the per-start CSVs and final coordinate files. Floating optimization paths can vary between platforms. Each ghost-kernel launch also compares directional derivatives against central finite differences.

The saved rational result and the Lean theorems can be verified without repeating numerical optimization. From the repository root:

~~~sh
python3 research/pack-18-squares/follow-up/patch/exact.py research/pack-18-squares/follow-up/ghost/best-rational.json
lake env lean -DwarningAsError=true research/pack-18-squares/follow-up/ghost/Trial.lean
~~~
