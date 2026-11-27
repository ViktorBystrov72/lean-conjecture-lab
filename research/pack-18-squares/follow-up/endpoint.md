# What remains to establish the exact optimum

Let $H=(7+\sqrt7)/2$. A placement at $H$ is already known. An independent proof of optimality must still exclude **every** placement with actual side $L<H$. The global exclusion at $L=24/5$ removes all sides up to and including 4.80. Numerical searches and exclusions of isolated arrangements cannot establish the remaining universal claim. [Unrestricted bound](global-bound/at480/) · [Feasibility problem](../unrestricted/)

One possible route uses the case structure of Mira Cult’s proposed proof:

- The test container is slightly larger than the record, $U=4.822876>H$. A verified 21-point rack and its eight square symmetries reduce the problem to 187 cases. In the proposed proof, 181 whole cases, covered by 235 terminal regions, are empty even at $U$. Each exclusion must be independently justified, either class by class or with an argument covering many at once. The ordinary-class calculations below now supply these exclusions.
- Cases 53, 55, 82, 92, 115 and 137 are exceptional. The submitted proof subdivides them into $114+15+20+19+19+6=193$ regions. In each region it suffices to establish emptiness or a lower bound on the *actual* side $L$. A region containing a known packing at $H$ must remain feasible at the test side. Any use of reflections or subdivisions must cover both sides, including boundary contacts.
- These exceptional six differ from the six empty cases sampled inconclusively by the previous external auditor (2, 56, 80, 86, 91, 93). Independent programs here have supplied closing computations for that entire sample. This strengthens the evidence for those cases without certifying the whole theorem. [Sample review and current scope](terminal-audit/)

At $U=4.822876$ the three series of computations exclude all 181 ordinary classes. Of the six exceptional classes, the whole of 55, 82, 92, 115 and 137 is excluded for $L<H$. A hypothetical improvement must therefore lie in class 53. In class 53 all 43 leaves labelled empty are independently excluded; progress on its 71 remaining leaves is tracked by the geometry inventory. The rack, split thresholds and the geometric strategy are due to Mira Cult. [All ordinary classes](ordinary-empty/) · [Exceptional empty leaves](endpoint-empty/) · [Class 55](row-guards/independent55/) · [Classes 82, 92 and 115](endpoint-guards/independent-residual/) · [Class 137](endpoint-guards/independent137/) · [Inventory](endpoint-cover/geometry_inventory.py)

The proposed geometric guards reduce the surviving configurations to
$$
2\le \sqrt{(L-3)^2+(L-4)^2}
$$
in the remaining range $24/5<L<H$. Squaring gives $2L^2-14L+21\ge0$. The lower root $(7-\sqrt7)/2$ is below four, so the inequality forces $L\ge H$. The key obligation is to derive the geometric premise for every live branch. Rearranging the quadratic is the final operation. [Proposed guard argument](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/proof.md)

Proving the side optimal would still leave the geometry of the equality cases to investigate. Several different arrangements attain the same side. Mira Cult explicitly excludes classification of all optimal arrangements from its claim. [Stated scope](https://github.com/Mira-Cult/math/tree/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18)

## Reproduce the full-side calculations

Use Python 3.10 or newer and a C++17 compiler supporting 128-bit integers. From this directory, **python3 verify_endpoint.py --ordinary-only** checks the historical construction by exact arithmetic, checks that the rack covers every one-tile pose, and runs the component verifiers for all 181 ordinary classes. The argument **--source /path/to/upstream/notes/geometry/unit-square-packing-18/replay** selects an offline copy of the seven pinned JSON tables.

The full command **python3 verify_endpoint.py** also runs the exceptional partition and geometry checks and requires every essential leaf to have a certificate. A partial inventory cannot pass that last test. To see the exceptional leaf counts alone, use **python3 endpoint-cover/geometry_inventory.py**. [Composite verifier](verify_endpoint.py)
