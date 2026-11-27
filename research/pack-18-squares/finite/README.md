# Exact maximum for 7,140 prescribed unit-square placements

**Exactly 17 of the placements in [poses.txt](poses.txt) fit together.** The container is the square $[0,4.8228756]^2$. Tile positions and rotations must be chosen from the 7,140 rows of that file. Allowing poses elsewhere in the container gives a different optimization problem.

## Coordinates

Each row contains five integers `x y a b c`. Put $D=10^7$. The square has centre $(x/D,y/D)$ and unit edge directions $(a/c,b/c)$ and $(-b/c,a/c)$. Boundary contact is allowed. This file defines the finite problem exactly.

The pool was assembled from historical 18-square layouts, positions transplanted from packings of 17 and 19 squares, wall- and centre-anchored positions, rational rotations, symmetries of the container and recombinations of $x$ and $y$ coordinates of axis-aligned tiles. [Historical survey](https://www.combinatorics.org/files/Surveys/ds7/ds7v5-2009/ds7-2009.html) · [Packing witnesses](https://github.com/jlevy/squares/tree/main/packing/witnesses/known-best)

## Why the check proves the maximum

The lower bound is [witness-17.txt](witness-17.txt). The verifier checks membership of 17 distinct poses, all four vertices of each square against the walls, and separation of all 136 pairs.

For the upper bound, every pose is a Boolean variable. For a pair of squares, disjoint interiors are equivalent to weak separation of projections on at least one edge normal of either square. The encoder compares these projections with integers, clearing positive denominators. If the open circumdisks are disjoint the pair can be skipped. Each remaining pair with overlapping interiors contributes a clause forbidding simultaneous selection.

The encoder groups the poses by 21 marks. It checks from the coordinates that every pose has a mark **strictly** in its interior and assigns the first such mark as its owner. Two distinct selected poses must have different owners. For each owner an auxiliary Boolean variable implies that at least one pose in that group was selected. Every four owners are required to have at least one true auxiliary variable. Thus at least 18 of the 21 groups must contribute selected poses. Conversely any compatible set of at least 18 poses satisfies the formula by setting its occupied groups true. The marker construction is borrowed from prior work and checked here only on the finite pool. [Marker source](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/proof.md)

CaDiCaL refutes the resulting formula. A separate [checker](rup_check.cpp) validates the positive-hint LRAT trace. For every added clause it assumes the negations of its literals, follows the specified unit implications to a contradiction, and finally checks the derivation of the empty clause.

## Replay

Use Python 3, a C++17 compiler and CaDiCaL 2.1.2 (distributed with the pinned Lean toolchain). From the repository root:

```sh
lake env python3 research/pack-18-squares/finite/replay.py
```

Alternatively pass `--cadical /path/to/cadical`. Set `CXX` to select a compiler. The command validates the stored inputs, reconstructs the CNF, generates a fresh text proof, and independently checks it. All generated files live in a temporary directory and are removed on exit. Allow about 1.5 GB of temporary disk space.

| Artifact or result | Reference |
| --- | --- |
| Exact pool SHA-256 | `42cc2a46f6285288f3ba12dbb0079e28851d61fabcebf5c3f77e703edc9a5d57` |
| 17-pose witness SHA-256 | `05ab7d4b52be4f27822f1161e3341a765f92c72bdeeb7a666b9cac5f8a38578d` |
| Generated CNF SHA-256 | `8bd60d42eae3fa84f97441d03f6d96d514c88ea0337a5156ac30e35b81973739` |
| Formula | 7,161 variables, 6,377,604 clauses |
| Reference text LRAT SHA-256 | `58fdc29d6ac7ca9c163fbc1aa1eaba497088652fb3bb5a4577203049d87bd42a` |
| Reference trace | 309,021 additions, ending with the empty clause |

A different valid proof trace establishes the same result. The replay checks the CNF hash and the proof itself.
