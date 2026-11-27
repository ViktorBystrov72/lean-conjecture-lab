# A computer-assisted lower bound for unrestricted 18-square packing

**Claim.** Eighteen unit squares with disjoint interiors cannot fit in a square of side $19/4=4.75$. Each square is free to translate and rotate. Boundary contact is allowed. This excludes every side $L\le19/4$. It leaves a gap to the known feasible side $H=(7+\sqrt7)/2$.

This is an independent implementation of a lower-bound argument using Mira Cult’s published 21-point arrangement and nearest-mark framework. The Squares Project records a separately verified lower bound of 4.705. Mira Cult’s stronger claim of $H$ would imply the present result. We claim neither priority for the numerical inequality nor an independent proof of the exact optimum. [Case register](https://squaremath.org/cases/18.html) · [Mira Cult’s proof](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18)

## Why the computation is global

1. Put a hypothetical container of side $19/4$ concentrically inside the test square of side $U=4.822876$. This is just a translation of the packing. The distance from each true wall to the corresponding test wall is $(U-19/4)/2$.
2. The rack checker verifies that every possible unit square in the test square contains a rack point strictly inside its concentric contraction by $1-10^{-5}$. Each tile chooses a nearest rack point in its own coordinate norm. Ties may be resolved arbitrarily. Eighteen tiles with disjoint interiors choose eighteen distinct points, leaving three of the 21 points unused.
3. The verifier enumerates all $\binom{21}{3}=1330$ unused triples. Rotations and reflections preserving the test square also preserve the true container because it is concentric. They reduce the triples to 187 classes. The positions and angles of the tiles inside each class still range over the continuum.
4. For each class the geometry program starts with outer regions covering all permitted centres and orientation intervals. For the smaller container it moves the four initial wall constraints inward by the exact inset. It propagates guaranteed interior regions of neighbouring tiles and removes only impossible poses, with outward rounding on the remaining centre regions. A class closes if one required tile loses every pose or if the strict interiors of two required tiles must overlap. The implementation and the geometry of its relaxations are documented in the [case-audit package](../terminal-audit/).
5. Every class closed. Of the 187 recorded settings, 81 use 16 angle bands, 90 use 32 and 16 use 48. There are no fixed tile centres and no requirement that the tiles actually have one of the sampled directions. Each angle band covers a closed interval of directions. [Instructions for all 187 cases](cases.json)

If the notation $s(18)$ denotes the infimum over all feasible sides, the argument also gives $s(18)>19/4$. Indeed, a decreasing sequence of feasible sides tending to the infimum has a subsequence in which all 18 centres and unit frames converge. Containment and pairwise nonoverlap of interiors persist at the limit (the four-axis separation test is a finite disjunction of closed inequalities). The infimum is attained. For comparisons with the case register we quote the conservative bound $s(18)\ge 4.75$.

## Replay

The verification requires a C++17 compiler supporting 128-bit integers and Python 3.10 or later. From this directory run:

~~~sh
python3 verify.py --workers 3
~~~

It builds the independent checker in a temporary directory, verifies the rack for the full test square, regenerates the 187 classes, and checks a closing event for each class with the true wall inset. The saved cases select resources and supply no accepted verdict by themselves. Different compilers may propose different inner points. Every point used for an exclusion passes exact tests. Choose a compiler with the CXX environment variable. [Verifier](verify.py) · [Audit of the geometry kernel](../terminal-audit/)

The clean reference run closed all 187 cases. A separate replay compiled the same class-exclusion kernel using LLVM Clang 23 and a different angle schedule. It excluded 146 orbits at 25 bands, another 40 at 42 and the last at 64. The reviewer separately implemented the rack-cover test and the enumeration of unused triples. This is a computer-assisted bound reviewed by an AI agent. It has not been formalized end to end in Lean or refereed by a human. [Reference receipt](receipt.json) · [Review and reproduction](review/)

The search driver can try other rational sides on the centred nanounit grid. An interrupted run or a nonempty list of inconclusive classes yields no exclusion for the entire problem. [Search driver](sweep.py)
