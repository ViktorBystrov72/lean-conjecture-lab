# Independent continuous-centre checks of the 21-mark reduction

Mira Cult proposed an unrestricted optimality proof for 18 unit squares. An outside audit independently verified the mark covering and symmetry reduction, but its continuous geometry program returned **UNDECIDED** on all six sample orbits (2, 56, 80, 86, 91, 93). These are a sample, not a list of six remaining leaves from an otherwise independently verified tree. The present C++ program is a separate implementation of continuous enclosures. It uses the same published rack, support-function propagation strategy and, where indicated, a suggested split, and does not execute the producer’s kernel or use its reported verdicts as premises. All six sampled orbits close independently. A coarse sweep of every orbit plus these targeted runs excludes 91 of 187. This does not prove the full 18-square optimum. [Published reduction](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18) · [Independent audit](https://github.com/jlevy/squares/blob/c5775bae40085f67f4c30f8916b0d6e998c304ab/docs/project/reviews/review-2026-11-20-mira-1050-n18.md) · [Its six samples](https://github.com/jlevy/squares/blob/c5775bae40085f67f4c30f8916b0d6e998c304ab/packing/resources/web/mira-cult-n18-1050-review-2026-11-20/out/refute-sample.json)

## What closed

| Orbit | Missing mark coordinates on the 2000-square | Continuous-centre certificate |
| --- | --- | --- |
| 2 | (359,797), (716,1000), (1641,1203) | 96 angle bands, empty owner 16 |
| 56 | (359,797), (1000,716), (1383,1383) | 96 bands, guaranteed interiors intersect for owners 4 and 12 |
| 80 | (359,797), (390,390), (1383,617) | 32 bands, empty owner 1 |
| 86 | (359,797), (1000,1000), (1284,1000) | Split owner 11 at $y=3.128620$. The low half closes with 96 bands, the high half with 128. |
| 91 | (359,797), (716,1000), (1284,1000) | Split owner 10 at $x=2.394491$. Both halves close with 96 bands. |
| 93 | (390,390), (617,1383), (1284,1000) | 128 bands, guaranteed interiors intersect for owners 10 and 15 |

The two thresholds appear in the producer's archived base table. Each pair of closed half-spaces includes its boundary and covers every centre. The intermediate domains, partner bounds, final contradictions, and global rack covering were recalculated here. The 512-band covering run used 783,262 boxes and certified 391,887 leaves. With 32 bands and 20 rounds per orbit, the full 187-case sweep excluded 86 cases including case 80. Adding the other five targeted cases gives 91 excluded and 96 unresolved by these transcripts, including all six orbits with retained equality branches. These counts refer to symmetry classes, not to individual terminal regions in the other implementation. [Sample replay](sample-receipt.json) · [Sweep receipt](sweep-receipt.json)

## Adaptive follow-up at the same side

A bounded work queue with three workers completed tests on 57 more distinct producer-empty orbits. We prioritized simple cases from the public base table, then used the independent kernel to evaluate each whole orbit. The runs added 27 exclusions to the original 91, for **118 independently excluded orbits out of 187 at side 4.822876**. The outstanding scope at this side consists of 63 producer-empty orbits and six mixed orbits. An inconclusive verdict contributes no exclusion. The exact case lists, parameters, output lines and kernel hash are in the [adaptive receipt](adaptive-receipt.json). To repeat a group, pass its `cases`, `bands` and `rounds` fields to `sweep.py`.

## Geometry and soundness

All integral lengths use one billion units per side of one tile. The reference box has side $U=4.822876>(7+\sqrt7)/2$. Place the 21 marks at the dihedral images of $(390,390),(617,617),(797,359),(1000,716),(1000,1000)$ on a square of side 2000, then scale them uniformly to $U$. The option **--side** centres a smaller container in the reference box while keeping this rack fixed.

1. **Independently check the covering.** Parameterize an orientation up to a quarter-turn by $t=\tan(\theta/2)\in[0,1]$. Its unit vector is $((1-t^2)/(1+t^2),2t/(1+t^2))$. In each of $B$ equal bands the orientation differs from the middle frame by at most $1/B$ radians. The free centre is in the initial wall rectangle since the minimum of $\cos\theta+\sin\theta$ is attained at an endpoint. Bisect that rectangle until its four corners belong to one square around a mark in the middle frame with half-side strictly less than $(1-10^{-5})/(2(1+1/B))$. Convexity covers each whole leaf. The rotational inflation factor is at most $1+1/B$. Thus every possible tile contains a mark in its concentric contraction by $1-10^{-5}$. The nearest mark in its own infinity norm has the same guarantee. Any tie can be resolved arbitrarily. Two disjoint-interior tiles cannot choose the same mark.
2. **Outer centre sets.** For each of 18 occupied marks $j$ keep one convex polygon $C_{j,k}$ for each angle band $k$. The wall bounds and the half-planes of a square enclosing the rotating tile in the middle frame give an initial outer enclosure. For each potential competitor mark and each signed owner axis $v$, remove centres where $v\cdot(m_j-c)$ exceeds *all four* signed projections of the competing mark displacement, at both band endpoints. Those strict inequalities persist throughout the band since each expression is homogeneous linear in $(\cos\theta,\sin\theta)$ and the intervening arc is in the positive cone of its endpoints. Removed centres violate the nearest-owner requirement.
3. **Inner tile sets.** The angle-band core $K_k$ is centrally symmetric. With $G$ the maximum of $\cos\delta+|\sin\delta|$ at the two angular endpoints relative to the middle frame, it includes a middle-frame square of half-side $(1/2-16\cdot10^{-9})/G$ after rounding its corners. The maximal angular deviation is below $\pi/4$, so the endpoint bound holds inside. Four additional axis points of length $1/2-16\cdot10^{-9}$ use the inscribed disk. Each integer coordinate floor moves a point by less than one lattice unit per coordinate. The 16-unit margin covers the resulting projection error. Negation and convex hull preserve inclusion in the true open tile. The owner’s initial guaranteed hull $H_j$ is a diamond with coordinate radius $10^{-6}$ about its mark.
4. **Propagation against all partner poses.** If the centre of a tile in band $k$ lies inside $H_j+K_k$ for another assigned tile, the two open tiles would overlap. We also use a band-aware exclusion without requiring their partner centre to be fixed. Let $h_k(n)=\max_{x\in K_k}n\cdot x$. For every live band $\ell$ of the partner, the intersection of $z+K_\ell+K_k$ over all $z\in C_{j,\ell}$ has inequalities
   $$
   n\cdot c\le\min_{z\in C_{j,\ell}} n\cdot z + h_\ell(n)+h_k(n)
   $$
   for every facet normal of either core. Intersect over live bands. A normal of $K_k$ takes its minimum over every band; each additional normal takes its minimum over the bands in which it is a facet. Removing the *interior* of this polygon is safe. The actual partner pose belongs to one live band and its true centre belongs to that outer polygon.
5. **Growing the guaranteed interior.** For a fixed $j,k$ the intersection of translated cores over its possible centres has support inequalities $n\cdot p\le\min_{z\in C_{j,k}}n\cdot z+h_k(n)$ for core facets $n$. Intersect over bands. A floating-point clipping step proposes lattice points, then **every** returned point is checked against **every** inequality by integer arithmetic. Add these verified points to $H_j$ and take their convex hull. Failure to find a point does not justify exclusion.
6. **Outward clipping and stopping.** For an intersection of an edge with a half-plane boundary, append all four combinations of coordinate floor/ceiling of the exact intersection before taking the hull. Removing the interior of a forbidden polygon is performed by clipping to the complement of each *open* facet and hulling the union. These operations may retain impossible poses. They preserve every possible pose, including contact and band endpoints. An exclusion occurs only when all centre domains of some owner are empty or two guaranteed inner hulls intersect. The remaining verdicts mean inconclusive.

Integer dot products and support bounds use signed 128-bit arithmetic where required. Initial centre vertices are in $[0,U]^2$. Flooring/ceiling an edge intersection stays within its integer endpoints’ coordinate bounding box. Proposed hull points are also required to be in $[0,U]^2$. Facet components are bounded by the box span, support offsets by a constant times its square, and products in rational clipping by a constant times its cube. At $U<5\cdot10^9$ lattice units these fit signed 128-bit arithmetic. The lower-order angular products and scaled normals fit signed 64-bit for the accepted band counts. The standard accelerated path does not use floating point to decide emptiness. Different floating proposals may change propagation speed.

## Reproduce

A C++17 compiler supporting signed 128-bit integers and Python 3 are required. From this directory:

~~~sh
c++ -O3 -std=c++17 case_audit.cpp -o /tmp/pack18-case-audit
/tmp/pack18-case-audit --rack 512
python3 replay.py --exe /tmp/pack18-case-audit
python3 controls.py --exe /tmp/pack18-case-audit
~~~

The controls read the four checked-in historical exact layouts, establish their containment and pairwise separation in $\mathbb Q(\sqrt7)$, assign actual nearest marks, and test all 18 actual centres against the output polygons in the true angular bands. Each of four configurations survived all twelve rounds with 32 bands. The sample partition is checked using **sweep.py**; its case masks must equal those produced by canonicalizing all 1,330 missing triples under the eight box symmetries. [Physical controls](physical-controls.json)

For a coarse sweep of all cases, run
~~~sh
python3 sweep.py --exe /tmp/pack18-case-audit --bands 32 --rounds 20 --output /tmp/pack18-sweep.json
~~~
A smaller box can be tested with **--side** in nanounits, e.g. **--side 4706000000**. The default side is 4822876000. An **EXCLUDED** verdict applies only to the requested mask, container and any explicitly supplied cuts. The cut command takes an owner index, a coordinate comparison (x-le, x-ge, y-le or y-ge), and a nanounit coordinate. A whole-case exclusion from such runs requires covering all possible values, including the split boundary.
