# Review of the 4.80 exclusion

The proof covers the 18-square packing problem with arbitrary real centres and rotations at side $24/5$. The two geometric programs use the same 21 points in the rack of side 4.822876. They centre the smaller container in this rack. Their coordinate units are respectively one billionth and one five-hundred-millionth of a unit. Both implementations apply the same physical wall inset, 0.011438. The eight symmetries about the common centre preserve the walls and permute the marks.

The inventory checker reconstructs all 1,330 unused triples. It explicitly removes each complete symmetry orbit and orders the resulting 187 occupied masks. Every representative occurs once in the execution plan. The 153 direct cases and 27 integer traces exclude whole representatives. For each split case the review checks that its cuts recursively cover both sides of each geometric threshold. The six leaves belonging to cases 22, 54 and 132 have their own tests at 4.80. Case 0 has eight leaves, and cases 53 and 55 each use one unrestricted run. Case 137 has six leaves. Independent enclosures directly exclude two, and give sufficient bounds for the opposite-wall probes in the other four. Opposite-wall offsets cancel, so the probe bound applies to the actual side 4.80. The rational inequality $(4.8-3)^2+(4.8-4)^2=3.88<4$ contradicts the necessary probe bound.

The review also replayed the rack cover, all seven split or exceptional cases, three direct full orbits and four additional integer traces. One control used the known 18-square packing at side 4.822876. All 18 exact poses survived every checked snapshot. An inventory with a missing case, a substituted representative, a changed wall side or a corrupted trace hash was rejected. The full combined run is recorded separately in the [producer's receipt](../at480/receipt.json). The [review receipt](receipt.json) lists the smaller execution set used here.

These checks support the computer-assisted conclusion that $s(18)>4.80$. Compactness gives a minimum because the centres and orientations stay in a compact parameter space and containment and pairwise interior disjointness are closed conditions. The proof uses the published rack and split data. Any first-proof claim must account for the existing claim of optimality at $(7+\sqrt7)/2$. The full exclusion uses C++ and Python. [Earlier claim and audit](https://github.com/jlevy/squares/issues/1050)

Run the inventory check from this directory. It requires Python 3 and fetches the pinned split data. To use a local copy, pass `--table /path/to/n18-482-base.json`.

```sh
python3 inventory.py
```
