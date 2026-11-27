# The unrestricted 18-square decision problem

Can 18 independently translated and rotated closed unit squares with disjoint interiors fit in an axis-aligned square of side $L<(7+\sqrt7)/2$? An exact witness answers yes. An independently checkable proof that the following real constraints are inconsistent would answer no, and would give a matching lower bound to Hämäläinen's construction. The initial solver run reached its time limit. Its status was **unknown**.

## Constraints on all tiles

The variables are $L$ and the centres $(x_i,y_i)$ and directions $u_i=(c_i,s_i)$ of all 18 tiles. Set $v_i=(-s_i,c_i)$. By quarter-turn symmetry each tile has a representative with $c_i,s_i\ge0$ and $c_i^2+s_i^2=1$. Relabel the tiles so that $s_i$ is nondecreasing. These conventions cover every real packing, including tiles with equal orientations.

The horizontal and vertical half-extents of tile $i$ are both $(c_i+s_i)/2$. Wall containment is therefore exactly
$$
(c_i+s_i)/2\le x_i,y_i\le L-(c_i+s_i)/2.
$$

For $i<j$ put $d=(x_j-x_i,y_j-y_i)$ and
$$
b=1+c_i c_j+s_i s_j+c_i s_j-s_i c_j .
$$
Nonoverlap requires at least one of the four directions $a\in\{u_i,v_i,u_j,v_j\}$ to satisfy $2|d\cdot a|\ge b$. All these inequalities are inclusive so a shared edge or vertex is allowed.

To see necessity and sufficiency, the centre differences that produce an interior overlap are precisely the interior of the Minkowski sum of the two origin-centred squares (each square is centrally symmetric). That sum is a polygon whose edges are parallel to the generating sides. Its facet normals therefore belong to the four directions above, up to sign. Its support along any of them is half the sum of the projection widths. The relative angle is between zero and a quarter turn, by the ordering of the tiles, so that sum is exactly $b$.

Finally $L>0$ and either $2L-7<0$ or $(2L-7)^2<7$. The generator also supplies the redundant area constraint $L^2\ge18$ and the lower bound of one on pairwise centre distances from the inscribed disks. The formulation uses 73 real variables and all 153 pairs. It assigns no tile a particular position, starting template or direction.

## Why a genuine improvement would have a rational witness

Suppose a real packing fits at some $L<H$, and write $\delta=H-L>0$. For any positive integer $m$, dilate the whole packing and box by $\lambda=1+4/m$. Each dilated tile has side $\lambda$. Temporarily replace it by a unit tile of the same orientation at its dilated centre. This leaves clearance $2/m$ to each side of its own dilated tile.

Round each dilated centre to the nearest multiple of $1/m$ in both coordinates. Write its angle as $\theta=2\arctan t$ with $0\le t\le1$ and round $t$ to the nearest multiple of $1/m$. This gives an exactly rational unit frame
$$
\left(\frac{1-t^2}{1+t^2},\frac{2t}{1+t^2}\right)
$$
using the rounded $t$. The change of angle is at most $1/m$ radians, as $|(2\arctan t)'|\le2$. Translation moves a point by at most $\sqrt2/(2m)$, and rotating about the centre moves a point in the unit square by at most another $\sqrt2/(2m)$. Their sum is strictly below $2/m$, so the closed rounded tile lies inside its own dilated tile. The rounded packing fits in a box of rational side $\lceil m\lambda L\rceil/m\le L+(4L+1)/m$. Since $H<5$, any $m>21/\delta$ suffices to stay strictly below $H$.

This elementary rounding argument explains why rational certificates suffice for finding a strict improvement even if the original construction uses irrational coordinates. Any individual grid or finite pool still has a limited resolution. This argument and the reduction above are written mathematical arguments. The solver run supplies no proof of infeasibility.

## Replay

The generator uses the Python standard library. For the reference run we used the Z3 executable from the z3-solver 5.4.1 distribution. From this directory:

~~~sh
python3 controls.py --solver /path/to/z3
python3 query.py --output unrestricted.smt2
python3 query.py --solver /path/to/z3 --seconds 75 --seed 180321
~~~

The controls accept the four supplied historical layouts at exact equality in $\mathbb Q(\sqrt7)$, reject equality as a strict improvement, accept boundary contact and reject a $10^{-12}$ overlap. [Generator](query.py) · [Controls](controls.py) · [Unrestricted run](global-run.json)
