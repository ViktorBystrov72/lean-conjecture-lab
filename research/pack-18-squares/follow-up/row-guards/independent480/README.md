# Centred exclusions of three full rack classes at side 4.80

In the square of side $24/5$, placed concentrically in the rack box of side $U=4.822876$, the checker independently excludes the full rack classes **0, 53 and 55**. The 21 marks remain at their original rack coordinates. The test for a tile uses its true four inset walls. The 18 physical tiles may translate and rotate independently and may touch at their boundaries.

| Class | Mask | Exhaustive branches | Proof |
| ---: | --- | ---: | --- |
| 0 | ffbfe | 8 | The published coordinate/angle partition of this mask. Each complete branch loses an owner in every one of 128 angle bands. |
| 53 | 1efbef | 1 | Independent empty-domain proof on the entire mask, with no coordinate or angle cuts. The first excluded owner has index 8 in the sorted list of occupied marks, in round 9 (zero based). |
| 55 | 1efbfe | 1 | Independent empty-domain proof on the entire mask. The corresponding owner index is 13 and the round is 7. |

In particular, these last two whole-mask calculations cover all 114 and 15 published endpoint leaves of classes 53 and 55 at this smaller side. They do not use the published geometry kernel, any of its outer pose boxes, or its terminal guard verdicts. The 40-round budget sufficed for both full masks. At 128 bands and 34 rounds this whole-mask method was inconclusive on 82, 92, 115 and 137. This package proves nothing about those four classes, or about the entire space without the other mask components. [Point data](certificates/) · [Exact results and hashes](receipt.json)

## Changes to the verified enclosure algorithm

The [integer base checker](../../terminal-crosscheck/README.md) uses a lattice of step $1/500000000$. The extension has three changes to the geometric input.

1. A 21-bit occupied mask identifies the eighteen selected marks. They are indexed in increasing order in the same rack. The rack and its symmetries stay fixed.
2. When the actual container side is $L$, the initial wall inset for a tile centre gains $(U-L)/2$ in both coordinates from every wall. Thus only the initial centre rectangles change. For $L=4.80$, this extra inset is $0.011438$. Every placement in a square of side $L$ can first be translated to this centred copy. The centred copy shares all eight symmetries of the rack box.
3. Optional centre-cut thresholds are the source's coordinate values in millionths. The verifier multiplies by 500 and clips outwards on its own lattice. Angular thresholds are physical half-angle cuts at $v/128$. A band $[k/B,(k+1)/B]$ is discarded only if it is disjoint from the requested closed half-interval. Thus a band meeting a threshold at an endpoint is retained, even on the smaller computational mesh. A pair of complementary cuts covers the parent.

All other centre-domain, directed separation and inner-point rules are those of the [base invariants](../../terminal-crosscheck/README.md#invariant-and-rounding). The ten compact certificates store suggested grid points for the inner hulls. Each is validated against every contributing halfplane *before* use. The verifying binary contains integer code only. A separate optional builder enables a heuristic that proposes inner points from approximate polygon intersections; the saved files replay without it. [Scoped build changes](build.py) · [Optional point proposer](point_suggestions.inc)

## Replay

From this directory, with Python 3 and a C++17 compiler accepting checked 128-bit integer arithmetic:

~~~sh
python3 replay.py --sanitize --control
~~~

The runner independently rebuilds the 187 mask representatives and checks that the case-0 cuts cover its full coordinate and orientation product, including all boundaries. It checks the ten certificate hashes, compiles the verifier, then requires each recorded exclusion at the stated side from the bare domains. The optional physical control reuses the base solver’s ten-round trace at side $U$: the previously certified rational case-53 packing survives in all 3,258 owner snapshots, including 9,805 checked core vertices. The control is at $U$, since this same packing is too large for the new smaller side.

Other aggregation scripts can reuse a binary compiled by the same builder:

~~~sh
python3 build.py /tmp/pack18-verify
python3 replay.py --kernel /tmp/pack18-verify
/tmp/pack18-verify 1efbef 128 40 verify certificates/case-53.txt 4800000000
~~~

The CLI takes an occupied hex mask, number of bands, round budget, mode, trace path, and centred side in billionths. Additional triples are **owner, opcode, threshold** in the source's cut convention. Coordinate opcodes 0/1 and 2/3 are upper/lower bounds on $x$ and $y$; 4/5 are upper/lower bounds on the half-angle. For example, the first case-0 leaf keeps $x_7\ge1.901877$.

~~~sh
python3 build.py /tmp/pack18-proposer --proposer
/tmp/pack18-proposer ffbfe 128 45 generate /tmp/pack18-case0-0.pts 4800000000 7 1 1901877
/tmp/pack18-verify ffbfe 128 45 verify /tmp/pack18-case0-0.pts 4800000000 7 1 1901877
~~~

An exit code of 0 together with the final **EXCLUDED** line is a successful exclusion. A round limit without a contradiction returns code 1. The combination of mask identity, branch coverage and per-branch arithmetic is required before calling a complete class excluded. [Pinned case-0 cut data](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/n18-482-base.json)
