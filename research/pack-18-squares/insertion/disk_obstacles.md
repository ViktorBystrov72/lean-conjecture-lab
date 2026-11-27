# Continuous insertion with all rotations free

At enclosing side $4.8228756$, none of the 128 listed 17-centre samples can be completed by an eighteenth unit square, even if every existing centre moves independently by up to $1/8192$ along each coordinate and **all 18 angles are unrestricted**. The centre of the eighteenth square may be any real point. For 127 samples the same exclusion holds at the larger displacement $1/512$. The restriction is the set of allowed initial centre neighbourhoods. [Sample indices](sample-indices.json) · [Exact receipt](disk_obstacles_receipt.json)

## Geometry

Let $m$ be the coordinate drift allowance. Each obstacle centre stays within Euclidean distance $d=3m/2$ of its sample point, since $\sqrt2\le3/2$. Its open unit square contains the open disk of radius $1/2-d$ in every position about its sample point. Thus whenever every legal new centre lies at distance strictly less than $1-d$ from some sample point, insertion is impossible at every orientation. An exact maximum-distance test over clipped Voronoi cells proves this for 115 samples at $m=1/512$. [Voronoi calculation](free_angles.py)

The 13 remaining cases use a stronger shape. We parameterize a tile's orientation by $t=\tan(\theta/2)\in[0,1]$, which covers a full quarter turn. Its unit basis is rational at rational $t$. A parameter interval $[a,b]$ has angular distance at most $b-a$ from the midpoint orientation, since $|d\theta/dt|\le2$. The support multiplier of an axis-aligned square at angular offset $\delta$ is $|\cos\delta|+|\sin\delta|\le1+|\delta|$. Consequently an obstacle of any orientation in the interval and any allowed shift contains the square about its *sample* centre in the midpoint orientation of side $(1-2d)/(1+b-a)$. The free tile's analogous midpoint core has side $1/(1+b-a)$ about its actual centre.

For each old tile, discard an angle interval if even the maximum wall clearance at drift $m$ is too small, or if its midpoint core must overlap a neighbouring obstacle disk. At zero drift, touching walls and pairs of unit-separated centres can also force a tile's axes. The positive-drift final argument uses no such pins. Every surviving angle band contributes an upper support multiplier for each chosen reference frame. We bound that multiplier by its midpoint value plus $b-a$, since $|\cos\delta|+|\sin\delta|$ is 1-Lipschitz. Calling the maximum upper bound $K$, every possible configuration contains the reference-oriented square of side $(1-2d)/K$ about the sample centre. For a horizontal reference, the wall-clearance bound can further reduce $K$.

Finally, subdivide the free tile's centre coordinates and its half-angle tangent. Each closed box is clipped against the walls using the minimum axial extent over its angle interval. A box is excluded if any obstacle overlaps the free tile throughout it. For a disk test, if $U,V$ bound the absolute coordinates of an obstacle centre in the free tile's midpoint frame and $h$ is the free core's half-side, the squared distance from the obstacle centre to this core is at most
$$\max(0,U-h)^2+\max(0,V-h)^2.$$
A strict comparison with $(1/2-d)^2$ rejects the box. For a square core we check strict overlap on all four candidate separating axes. All comparisons are rational. A shape on a boundary is allowed, including edge and vertex contacts. Remaining intervals are subdivided. The replay requires zero pending intervals for a successful exclusion.

## Replay

From the repository root:

~~~sh
python3 research/pack-18-squares/insertion/disk_obstacles_replay.py
~~~

The Python standard library suffices. The runner reconstructs the samples from the hashed pool and index file, verifies their initial unit frames and compatibility, recomputes all 128 exclusions, and compares the result with the saved receipt. The controls check a genuine physical insertion with free space, a tight touching grid, a strictly overlapping pair, a rotated wall tangent and an occupied unit container. A surviving disk/core relaxation by itself does not give a square packing. [Search implementation](disk_obstacles.py) · [Replay and controls](disk_obstacles_replay.py)
