# Endpoint guards for cases 53 and 55

An independently written checker accepts the geometric implications in all 78 terminals labelled with a guard in these two case tables. For case 53 it accepts 42 chord guards and 29 separating-face guards. For case 55 it accepts four chord guards and three separating-face guards. The result is conditional on the outer pose enclosures covering all real poses in their leaves. The data are derived from the **producer's** geometry worker. This test neither proves the enclosures correct nor decides the 51 leaves marked empty in these two classes. [Pinned source](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18)

## Wall rows

In local coordinates whose origin is the true bottom-left wall corner, take the near-horizontal direction $(c,s)$ of a row tile, with $c>0$, and centre $(x,y)$. A vertical line at $\xi$ crosses the opposite faces parallel to $(c,s)$ when $|\xi-x|<(c-|s|)/2$. Its chord has length $1/c\ge1$ and midpoint ordinate $y+(\xi-x)s/c$. In particular the midpoint differs from $y$ by at most $|s|/(2c)$. We require a common probe interval and place each earlier midpoint strictly below the terminal midpoint across all possible poses. The chord interiors do not overlap. If there are $p$ tiles in the row and $P$ is the upper-right corner of the terminal tile, then
$$
P_y\ge p+(P_x-\xi)s/c,\qquad P_x\ge c+\max(0,-s).
$$
These formulas are relative to the actual walls. Probe-to-corner differences may be computed in test-box coordinates.

For a unit direction $(a,b)$ with $b/a\in[r,R]$ and $r>0$, the probe must imply $aP_x+bP_y\ge a+pb$. When $s>0$, it suffices to have $P_x-\xi\ge s/((1+c)r)$. When $s<0$, it suffices to have $P_x-\xi\le c(1-|s|/(1+c))/R$. They follow by substituting the preceding inequalities and $1-c=s^2/(1+c)$. A zero tilt costs nothing. We bound the expressions separately in each angular band, keeping a common interval for the probe across every band of every row tile. Apply the same argument to the two-tile row in coordinates reflected and interchanged from the opposite true walls. The three- and two-tile bounds yield
$$
(a,b)\cdot(Q-P)\le (L-3)a+(L-4)b
$$
for the relevant terminal corners and actual container side $L$.

## Two ways of obtaining the matching lower support

For a **chord terminal** let $D=Q-P$, and let $z$ be a middle tile centre. Some signed tile axis $u$ must satisfy
$$
D\cdot u > |D\cdot Ju|+2|\det(D,P-z)|,
$$
where $Ju$ is a quarter turn of $u$. This implies that the full line through $P,Q$ meets the relative interiors of both opposite faces perpendicular to $u$. The inequality follows by checking the transverse coordinate at each of the two face intersections. The determinant is affine separately in $P,Q,z$, so its absolute maximum over their boxes occurs at corners. For the left-hand lower bound we test each endpoint of the angular arc, both signs in $u\pm Ju$, and all corner pairs. A positive bound for both angular endpoints persists throughout their short arc, since a unit arc vector is a positive combination of its endpoints with coefficient sum at least one.

We also verify $(P-z)\cdot u<1/2$ and $(Q-z)\cdot u>-1/2$. The two terminal corners belong to different tiles from the two middle tiles, so they cannot lie in either middle tile’s interior in a legal packing. The segment must therefore traverse the whole chord. Each of the two traversed chords has length at least one and their interiors are disjoint. For $(a,b)=D/|D|$ this gives $(a,b)\cdot D\ge2$.

For a **faces terminal** the separating-axis test eliminates the transverse axes and reverse directions for the two middle tiles. If the two forward unit normals are $u,v$, their scalar product is $c>0$. Write $s=u\cdot Jv$, with $c^2+s^2=1$. We enclose the projections from $P$ and to $Q$ on the two native frames. The forward gaps are at least $1/2$, either directly or because a smaller gap in the tested interval would put a different tile’s corner strictly inside a middle tile. For a forward separation along $u$ the centre gap in that direction is at least $(1+c+|s|)/2$. The signed transverse inequality checked by the program supplies the missing $1-c=s^2/(1+c)$ in the combined projection. The case of separation along $v$ exchanges the two frames and reverses the transverse sign. The half-angle parameter difference divided by one plus the parameter product gives the signed value $s/(1+c)$. [Precise real hypotheses and Lean proof](../../../../ConjectureLab/PackingEndpoint.lean)

In either case a positive unit direction pays a projection of at least two. The wall bound and Cauchy–Schwarz give $(L-3)^2+(L-4)^2\ge4$. With $L>4$ this implies $L\ge(7+\sqrt7)/2$.

## Verification and regeneration

From this directory, Python 3 rechecks all 78 implications from the saved rational input with **python3 check.py**. It validates the decompressed input digest and refuses eight deliberate mutations covering repeated owners, invalid angles, widened wall bounds, and displaced middle tiles. [Checker](check.py) · [Exact receipt](receipt.json)

The object **outer-boxes.zlib** contains compressed centre bounds in millionths and half-angle band indices for the seven selected owners. To rebuild those bounds from the pinned upstream code, run **python3 regenerate.py** with a C++17 compiler and network access or provide **--source /path/to/upstream-clone**. The source geometry supplies the pose enclosures. Our code reads those as input and computes the guard conclusions independently. [Extractor](inputs.py) · [Original proof and scope](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/proof.md)
