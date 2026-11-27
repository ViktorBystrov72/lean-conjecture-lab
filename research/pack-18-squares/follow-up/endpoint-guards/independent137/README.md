# Full-side endpoint certificate for rack class 137

A packing in class **137** of the 21-mark rack requires a square of side at least $H=(7+\sqrt7)/2$. The enclosure uses the full rack box $U=4.822876$. The six complementary cut paths cover the entire occupied mask **0x1ffbcf**. Smaller containers can be translated concentrically into the rack box. The final wall inequalities use the true container side $L$ so they give the exact bound $L\ge H$ for this class.

| Leaf | Angular bands | Propagation rounds | Middle-tile band pairs |
| ---: | ---: | ---: | ---: |
| 0 | 128 | 38 | 361 |
| 1 | 512 | 20 | 1,296 |
| 2 | 128 | 30 | 484 |
| 3 | 128 | 65 | 575 |
| 4 | 128 | 65 | 272 |
| 5 | 128 | 65 | 528 |
| **Total** | | | **3,516** |

The reconstruction uses independent [integer geometry](../../terminal-crosscheck/README.md) and independently implemented [two-face guards](../README.md). Mira Cult supplied the rack, the case partition, the role assignments, and the mathematical endpoint strategy. The archived inputs consist of proposed points of guaranteed tile interiors. Before using any point the geometry checker tests it against every defining halfplane. The live continuous centre regions are recomputed for every orientation band, starting from the four walls of the full rack box. At the last round the geometry program still has nonempty regions. The guard step converts each verified polygon to a rectangle, rounds its four coordinates outwards and tests the wall probes, face choices and signed transverse inequalities on all remaining middle-tile band pairs. The algebraic implication is formalized in [Lean](../../../../../ConjectureLab/PackingEndpoint.lean).

## Reproduction

Use Python 3.10 or later and a C++17 compiler supporting 128-bit integer arithmetic. The six point traces are local and compressed. No source geometry, pose boxes or preset guard decisions need to be downloaded.

~~~sh
python3 replay.py --sanitize
~~~

The script checks coverage, decompresses and hashes each [certificate](certificates/), and compiles the integer verifier with its output-only rectangle option. After that verifier finishes checking its trace, the script independently evaluates the guard and compares the measured band counts and both positive probe gaps with the [receipt](receipt.json).
