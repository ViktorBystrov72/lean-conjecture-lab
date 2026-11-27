# Input layouts for the contact tests

Each `*-exact.json` gives a unit-square placement in the square of side `(7 + sqrt(7))/2`. A scalar pair `[a,b]` denotes `a + b sqrt(7)`. The centre is `(x,y)`, the first side direction is `(c,s)` and the other is `(-s,c)`. Boundary contacts are allowed. The diagram reconstructions fix representatives of free tile positions and angles.

| Layout | Input provenance |
| --- | --- |
| Hämäläinen (1980) | [Published decimal witness](https://github.com/jlevy/squares/blob/c5775bae40085f67f4c30f8916b0d6e998c304ab/packing/witnesses/known-best/n-018.yaml), lifted to the quadratic field and checked against the geometric constraints. |
| Gustafson (1981), Cantrell (2002), Gensane and Ryckelynck (2004) | Reconstructions from [Figure 7 of Friedman's survey](https://erich-friedman.github.io/papers/squares/squares.html#figure7). The free orientations of two Cantrell tiles use the rational frame (91/109, 60/109). |
| Mira Cult (2026) | Run `python3 fetch_mira.py` to retrieve and hash-check the [pinned coordinate table](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/six-tilt18.json). For offline use, supply `--input /path/to/six-tilt18.json`. |

After materializing the fifth input, run `python3 independent_stress_review.py` to replay the five equilibrium certificates and twenty negative controls. The main [contact verifier](../contact_stress.py) also checks containment and all pairwise separations in the original layouts.
