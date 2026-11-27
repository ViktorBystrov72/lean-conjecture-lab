# Independent review and replay at side 19/4

The global exclusion at side **4.75** passed this agent review. A separately compiled copy of the [geometric kernel](../../terminal-audit/case_audit.cpp) excluded every occupied-mark class. The orbit enumeration and rack-cover program here were implemented separately. This is an independent build and replay of the same class-exclusion implementation, together with mathematical inspection of its geometric rules. It is an AI review. It does not establish optimality at $(7+\sqrt7)/2$.

## Why the smaller container gives a global bound

Translate the enclosing square of side $L=19/4$ so that its centre coincides with that of the rational rack box of side $U=4.822876$. The walls then lie at $(U-L)/2$ and $(U+L)/2$ on both axes. Any packing fitting a smaller square also fits this square. The concentric region is invariant under all eight symmetries of the rack. Reflections preserve the class of unit squares with unrestricted orientations.

The 21-mark covering ensures that every tile has a mark in its concentric contraction of side $1-10^{-5}$. Choosing a nearest mark in that tile’s rotated maximum norm preserves this strict margin. The 18 assigned marks are distinct because the interiors are disjoint. Ties may be resolved arbitrarily. We partitioned the 1,330 possible triples of unassigned marks into 187 disjoint orbits and checked the multiplicity of each. Each use of a symmetry transports the whole packing. The continuous program keeps all positions and orientations consistent with each assigned representative.

Exclusion of every orbit proves there is no packing at side $19/4$. It also gives $s(18)>19/4$ for the infimum convention. A sequence of packings with sides tending to the infimum has a convergent subsequence of all bounded centres and all unit frames. Wall containment and the finite disjunction of non-strict separating-axis inequalities for each pair are closed conditions. Hence the infimum is attained.

## Checks

- The independent rack program bounded the sine and cosine on each rational half-angle interval by their separate endpoint ranges. For every centre rectangle it checked that one mark lies strictly inside the contracted tile for the entire rectangle and interval. A 257-slab run covered 203,063 leaves in 405,869 nodes (maximum depth 20). [Interval rack checker](rack_interval.cpp)
- The exclusion program was compiled with LLVM Clang 23.1.1 from the Lean 4.36 distribution, using the system C++ library. With a 75-round cap, the 25-band run excluded 146 orbits, the 42-band run excluded 40 more, and the 64-band run closed case 22. The sum of the excluded orbit multiplicities was 1,330. [Machine-readable receipt](receipt.json)
- The mathematical inspection checked the inset walls, outward lattice rounding of outer centre polygons, inward orientation cores (including the 16-lattice-unit rounding allowance), strict nearest-owner cuts, universal partner-core pruning and growth of closed hulls contained in true open tile interiors. Intersections used for outer clipping are rounded to their four surrounding integer grid points. Floating point proposes inner points, which must satisfy every required integer half-plane. These details keep admissible boundary contacts.
- For additional controls, 902 admissible centre/angle memberships from three legal rational packings in classes 53, 82 and 137 survived initialization and ten propagation rounds. With a nonzero inset at side 4.822875700, 224 memberships from eight symmetry images survived a further check. Sanitized builds also reproduced the case-80 exclusions at 32 and 64 bands.

## Replay

A C++17 compiler supporting signed 128-bit integers and Python 3 are required. From this directory:

~~~sh
python3 replay.py --verify-receipt
python3 replay.py --jobs 2
~~~

The first command checks orbit coverage and the recorded verdict format. The second recompiles both programs and reruns every exclusion. Set the environment variable **CXX** to select a compiler. To inspect a single orbit first, use **--case 22**. Different valid band-level closures can yield the same final coverage.
