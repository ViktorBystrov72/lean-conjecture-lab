# Independent integer exclusions for rack cases 56 and 93

Mira Cult's proposed proof of the unrestricted 18-square packing bound splits the problem into 187 symmetry classes of assignments of rack marks. A separately written reviewer tried six previously excluded classes with a different program and returned **UNDECIDED** on all six. We verify here the infeasibility of **two complete classes in that sample**, with independently written polygon propagation and small, checked certificates of guaranteed points. We used the public assignment and its geometric ideas. We did not use the producer's initial polygons, generated geometry kernel, case split paths, exit flags or replay programs. The overall optimality claim has additional obligations beyond these two classes. [Proposed proof](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/proof.md) · [External sample and outcomes](https://github.com/jlevy/squares/blob/c5775bae40085f67f4c30f8916b0d6e998c304ab/packing/resources/web/mira-cult-n18-1050-review-2026-11-20/out/refute-sample.json)

## Exact statement

Use the test square $[0,U]^2$, $U=4.822876$, and the public 21 marks. The coordinates before multiplying by $U/2000$ are all the square symmetries of $(390,390),(617,617),(797,359),(1000,716),(1000,1000)$. Each tile must contain its assigned mark and that mark must minimize the distance to its centre in the tile's own $\ell_\infty$ frame among the 21 marks. Ties are allowed. The 18 assigned marks are all distinct. Under these hypotheses there is no packing with disjoint tile interiors for either of the following choices of the three unassigned marks.

| Source case | Three unassigned marks in unscaled coordinates | First empty owner, zero-based in the sorted occupied list | Round, zero-based |
| --- | --- | ---: | ---: |
| 56 | (359,797), (1000,716), (1383,1383) | 13 | 4 |
| 93 | (390,390), (617,1383), (1284,1000) | 9 | 9 |

Both exclusions cover all real centres and orientations in their classes, with boundary contact allowed. They use the box side $U$, slightly larger than $(7+\sqrt7)/2$. The public covering lemma motivating the assignment is not an input to the checker and is not re-proved here.

## Invariant and rounding

For every owner $i$ and angular band $k$, a convex grid polygon $P_{ik}$ contains every possible centre in that band. A second convex grid polygon $K_i$ lies inside the closed tile for every possible placement of owner $i$. Its initial value is the singleton consisting of its rack mark. Grid coordinates are integral multiples of $1/500000000$, which represent the wall and all rack coordinates exactly.

We partition $t=\tan(\theta/2)$ on $[0,1]$ into $B=128$ equal, closed bands. Their unit frames are rational at the endpoints and midpoint, using $u(t)=((1-t^2)/(1+t^2),2t/(1+t^2))$ and its quarter turn. Relative to the middle orientation each true angle differs by at most $1/B$, since the derivative of $2\arctan(t)$ is at most two. The concentric midpoint square of half-side $h_- = 1/(2(1+1/B))$ is contained in the true square and the midpoint square of half-side $h_+=(1+1/B)/2$ contains it. This follows from $|\cos d|+|\sin d|\le 1+|d|$. Bounds on the centre from the walls use the minimum of $(\cos\theta+\sin\theta)/2$ at the two endpoints.

Each outer update clips a convex polygon by one closed halfplane or takes an outer hull of the part satisfying at least one halfplane from a list. The complement of this union is convex. For a disjunction, retain vertices satisfying at least one inequality. On an edge from a rejected vertex to a retained one, include the first crossing of a permitted halfplane. Edges with two retained endpoints are already in the retained hull, while a segment with two rejected endpoints is wholly in the convex complement. Equivalently, the clipped pieces for individual halfplanes have vertices at retained original vertices and at edge crossings, all covered by this hull. For every rational crossing, the four corners obtained by rounding each coordinate down or up are included before taking the hull. Every halfplane threshold used to exclude centres is rounded in the permissive direction.

### Nearest marks and guaranteed points

Fix the two marks $m_i,m_j$ and one signed frame axis $b$ of the true tile $i$. Assigning $m_i$ as nearest implies that some signed frame axis $a$ satisfies $b\cdot(c-m_i)\le a\cdot(c-m_j)$. For fixed choices, the difference between the right and left sides is linear in $(\cos\theta,\sin\theta)$. An intermediate unit orientation is a nonnegative linear combination of the endpoint orientations. Hence at least one endpoint must satisfy the same inequality. We apply the resulting disjunction over the two endpoints and four choices of $a$ for each $b$ and competing mark. Other occupied marks cannot lie strictly inside the tile's midpoint inner square.

A supplied point $z$ can be added to $K_j$ only if, for every surviving band and each of its four signed midpoint axes $n$,

$$
n\cdot z \le \min_{y\in P_{jk}} n\cdot y+h_- .
$$

Thus $z$ lies in every surviving physical tile by the inner-square bound. The trace files propose 105 points for case 56 and 330 for case 93. Every point is tested against every defining inequality before use. The verifier only adds checked points and uses convexity to take their hull. The candidate points were found using floating-point intersections during discovery. Replay does not perform floating-point operations.

The outer midpoint square about owner $j$ must contain $K_j$, which cuts its centre domains. For each other tile its open midpoint inner square cannot meet $K_j$: if a closed square meets the open interior of another, their interiors intersect. Centres strictly inside the Minkowski sum of $K_j$ and the symmetric inner square are therefore forbidden. The outward facet normals come from the two summands. Their support values add. For a singleton or segment the nonzero segment normals and square normals suffice.

### Pairwise separation with interval angles

Two squares with disjoint interiors have a separating axis that is a signed side normal of one of the squares. Fix angular bands $k,l$ for the two tiles and suppose the normal $n$ comes from tile $i$ in band $k$. Write $d=c_i-c_j$ with the sign chosen towards tile $i$. If the bands are different, their interiors are disjoint, so one corner vector $v$ of tile $j$ supports it throughout the band $k$, including at tied endpoints. Then $n\cdot(d-v)\ge1/2$. Write $n=\alpha e_0+\beta e_1$ using the signed endpoint directions of this axis, with $\alpha,\beta\ge0$. For endpoint angular distance $\Delta$, $\alpha+\beta\le1/\cos(\Delta/2)$. Since $\Delta/2\le1/B$, put $g=1-1/(2B^2)\le\cos(\Delta/2)$. At least one endpoint $e$ satisfies

$$
e\cdot d \ge g/2+\min_{\theta_j\in l} h_{\theta_j}(e),
\qquad h_{\theta}(e)=\tfrac12(|e\cdot u(\theta)|+|e\cdot Ju(\theta)|).
$$

The minimum is at an endpoint of band $l$: the signs in the support formula are constant in its interior for a grid-endpoint axis, and the positive support is concave there. For the same band use $n\cdot d\ge1$ from the two inscribed disks, so at least one endpoint has $e\cdot d\ge g$. The checker rounds the two terms in the first bound down separately. It uses the minimum of $e\cdot c_j$ over each surviving centre polygon to obtain a necessary halfplane for $c_i$. We retain the disjunction over endpoint choices, source tile and possible bands of $j$. The integer checker declares the class empty only when one of the 18 owners has no surviving band.

## Replay and controls

From this directory run:

~~~sh
python3 replay.py --sanitize
~~~

The program compiles the [integer verifier](exact.cpp), replays the two stored certificates, and verifies the exact rational [physical control layout](../rack/saved/closest-rational.json) at source case 53 after each update over ten rounds. It checks the true centre inside its surviving polygon at its actual angular band and each core vertex inside the real tile, in a total of 3,258 owner snapshots. It also rejects a mutated certificate with a proposed core point moved to the origin. C++17 with 128-bit integer support and Python 3 are required. The integrated arithmetic has explicit range and product guards. [Physical control checker](control.py) · [Core point data](certificates/)
