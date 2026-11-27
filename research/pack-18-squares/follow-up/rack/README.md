# Rack-conditioned search for 18 unit squares

We searched for an enclosing side strictly smaller than $H=(7+\sqrt7)/2$. No verified improvement was found. Of 582 archived finalists, seven initially reported sides below $H$. After repair with rational arithmetic the best side was $4.8228756555322974767711711663\ldots$, exceeding $H$ by approximately $2.18152036\times10^{-15}$. Lean checks the validity of that specific packing and the strict sign of the difference. [Exact receipt](saved/exact-summary.json) · [Rational placement](saved/closest-rational.json) · [Lean proofs](RackTrial.lean)

## What we tried

The 21 marks of Mira Cult's proposed lower-bound certificate were used to generate candidate arrangements. Three unoccupied marks determine one of 187 symmetry classes. We assigned the 18 other marks to tiles. A penalty on the distance from each tile centre in its own coordinate axes guided its assigned mark into the tile. Another penalty favoured it over the three unassigned marks. All centres and angles were variable. The physical optimization at the end of each run discarded the mark constraints. [Original geometry](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18) · [Previous search](../../search-history/README.md)

| Search | Attempts | Scope |
| --- | ---: | --- |
| Rack-conditioned starts | 19,344 | 15,000 in the six surviving classes, 24 in each of the 181 other classes |
| Starts from marginal pose enclosures | 1,400 | 200 per surviving terminal of class 55 |
| Fixed-angle linear-program proposals | 3,400 | 939 feasible charts polished nonlinearly and then released |

The first two rows account for **20,744 numerical starts**. The LP proposals are counted separately. The rack-conditioned starts comprised 6,866 random starts, 11,586 adaptive perturbations and 892 rematchings from transferred layouts. Of 7,800 starts directed at class 55 in this stage, 4,845 retained that class after preliminary repair and before release. For layouts larger than the test box this diagnostic uses marks scaled with the enclosing side. It does not establish membership in a proof branch at $H$. [Run counts](saved/run-summary.json)

The seven terminal enclosures served solely for initialization and temporary guidance. Their smallest repaired member retaining normalized class 55 in this batch needed side $4.8245652664\ldots$. Fixed-angle LP charts impose signed separating axes, wall inequalities, mark inclusion and missing-mark comparisons. The unrestricted refinement can subsequently change angles and separation patterns. None of these search counts exhausts continuous placements.

One raw penalty output reported $4.822825638977719$. After eliminating the intersections and enforcing the wall constraints exactly it required $4.822900193809047\ldots$, roughly $0.00002454$ above $H$. The final comparison uses exact rational arithmetic. [Archived inputs for all 582 rechecks](saved/finalists.json.gz) · [Exact checker](../../search-history/exact_rescale.py)

## Verification and reproduction

The following command rechecks every archived finalist and compares the best exact coordinates and summary with the saved receipts. Only the Python standard library is required.

~~~sh
python3 verify_results.py
~~~

From the repository root, build the packing checker and check the best result.

~~~sh
lake build ConjectureLab.SquarePacking
lake env lean -DwarningAsError=true research/pack-18-squares/follow-up/rack/RackTrial.lean
~~~

For a numerical run, use Python 3.13, a C++17 compiler, the [search dependencies](../../search-history/requirements.txt), and a new output directory. Run these commands from this directory. The smoke test builds the search library and exercises both the rack and LP workflows offline.

~~~sh
python3 replay.py /tmp/pack18-rack-smoke --smoke
python3 replay.py /tmp/pack18-rack-full
~~~

A full run obtains the pinned external case data through the [earlier audit's source loader](../../audit/replay.py), builds the published kernel in the new run directory and regenerates the seven enclosures. To use an existing Mira Cult Git clone containing commit 78bec6aacebf304d942a9225e16c2f18165778ff, add the option --source followed by its path. The six-tilt numerical seed is derived from that same pinned data. The other four transferred seeds come from the [earlier search](../../search-history/seeds/). No external proof source is bundled here. [Runner, budgets and RNG seeds](replay.py) · [Native objective extensions](rack_terms.inc)

Floating-point trajectories and numbers of feasible LP charts can vary between solver and compiler versions. The archived rational replays are deterministic and do not require the external kernel. This experiment neither determines the unrestricted optimum nor independently verifies the claimed global proof.
