# Independent checks of the published empty-orbit cover

At test side $U=4.822876$, the checked-in base study independently excluded 118 of the 187 nearest-mark orbits. This follow-up adds **18 entire orbits**, bringing the total to **136**. Of the 181 orbits proposed empty at $U$, 45 still lack a whole-orbit exclusion in these runs. Six other orbits have a different role in the published proof: a surviving packing there must satisfy the sharp lower bound $L\ge(7+\sqrt7)/2$. These six are outside the present test. [Baseline study](../terminal-audit/) · [Adaptive results](receipt.json) · [Published case groups](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay)

## Which outcomes count

For every orbit the original input supplies proposed centre and angle splits. We import these numerical thresholds and check their logical coverage. We disregard every original computation budget, leaf verdict and generated kernel.

The independent partition check reconstructs all 187 masks, validates the marking indices, coordinates and angles on each path, and verifies that each internal node splits one owner, coordinate and threshold into opposite children. Each child represents a **closed** half-space, so their union contains the split boundary. A node cannot both declare a leaf and have descendants. All 181 claimed-empty orbits pass, with exactly 235 terminal paths. Three of these orbits use angle cuts. Passing this structural test establishes that sufficient exclusions at all given leaves would cover the orbit. It establishes no geometric impossibility by itself. The ten producer-side computation overrides mentioned in its driver concern unsplit roots and leave the partitions unchanged. [Pinned base data](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/n18-482-base.json) · [Partition checker](cover.py)

At the 24 credited leaves, our lattice geometry reached either an empty outer centre set for a required tile or intersecting guaranteed interiors of two tiles. Fourteen of the newly excluded orbits close without subdivisions. Complete checks of orbits 22, 54, 132 and 133 contribute the other ten leaves. Some additional individual leaves closed in partially checked orbits. No such orbit was added to the total. The receipt records 68 completed computational attempts, including inconclusive runs and selected refinements.

## Closed orientations

The old checker already handles centre restrictions. The build script verifies the SHA-256 of that source and adds an angle cut on $t=\tan(\theta/2)$ per named tile. To keep $t\le v/N$, a checker with $B$ bands drops band $k$ only when $kN>Bv$. For $t\ge v/N$ it drops the band only when $(k+1)N<Bv$. At equality the entire touching band is retained. The program then runs the ordinary outer-enclosure updates. As a positive control, constrain an axis-aligned owner to $t\le0$ in four actual algebraic packings. In each run all 18 physical centres survived in angle bands containing their true orientations, while all disallowed bands for the selected owner were removed. [Source extension](build.py) · [Boundary controls](boundary-controls.json)

## Optional direct endpoint supports

We independently implemented the signed endpoint-axis principle described in the published proof. This optional rule strengthens intersection tests between uncertain rotated squares. The essential non-overlap test uses the four signed face normals of **both** squares. For a candidate in angle band $k$, fix one of its unit normals $n$ and let $e_0,e_1$ be that normal at the band endpoints. We can write $n=\alpha e_0+\beta e_1$ with $\alpha,\beta\ge0$. Their sum need not equal one.

For a unit tile of side $D$ in lattice units, put $v_k$ equal to the unit normal at the middle frame, in the same signed direction. At each endpoint $e$ the candidate's own support contribution is $D(e\cdot v_k)/2$. After weighting by $\alpha,\beta$ its sum is $D(n\cdot v_k)/2\le D/2$. The code obtains $e\cdot v_k$ from the largest absolute projection onto the middle axes. Each endpoint is within $\pi/4$ of its matching middle normal.

For a partner in another band $\ell$, bound its support at $e$ below by the smaller support at the two partner orientations delimiting $\ell$. Grid endpoint directions meet no absolute-value kink in a band interior. On each such interval the support is a nonnegative concave sinusoid and its minimum is attained at an endpoint. For each fixed true partner orientation, its support is linear in the candidate normal throughout the intervening cone, since $k$ and $\ell$ have disjoint interiors. This allows combining the two endpoint lower bounds with the same nonnegative weights. For $k=\ell$, use the candidate’s own contribution twice. Its weighted sum is at most $D$, which is bounded by the sum of the two true supports via the two inscribed disks.

We impose these sufficient conditions for the normals of both tiles and all live partner bands and centres. Each endpoint inequality uses the minimum centre projection over the partner's outer centre polygon. Strict satisfaction rules out every separating direction for every admissible pair of poses. The integer implementation rounds each nonnegative support allowance down and removes only the strict interior. Thus rounding or an imprecise centre enclosure can weaken the proof. Neither can generate a contradiction by closing a boundary contact. Results at uncut roots are replayable with the angle extension alone where recorded. [Independent support implementation](endpoint_supports.inc) · [Base enclosure argument](../terminal-audit/README.md#geometry-and-soundness)

## Reproduce

Use Python 3 and a C++17 compiler supporting signed 128-bit integers. The only external input is the pinned 12 KiB JSON table. Supply **--table** with the local file for offline runs. A network fetch verifies the same SHA-256.

~~~sh
work=$(mktemp -d)
python3 build.py "$work/core"
python3 build.py --endpoint-supports "$work/endpoints"
python3 cover.py
python3 controls.py --exe "$work/endpoints"
python3 replay.py --core "$work/core" --endpoints "$work/endpoints" --workers 2
~~~

This replay verifies structural coverage of all 181 empty-orbit partitions and independently recomputes all 24 credited geometric leaves. It checks the new complete-orbit set against the earlier receipts and rejects a missing leaf or a duplicated claim. The two count levels correspond to different statements: 235 leaves checked for coverage, 24 leaves rechecked for geometric impossibility in this follow-up.
