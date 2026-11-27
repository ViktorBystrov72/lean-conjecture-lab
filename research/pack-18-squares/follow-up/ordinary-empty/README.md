# Completing the 181 ordinary rack classes

At the outer test side $U=4.822876$, we independently exclude all physical placements of 18 interior-disjoint unit squares in the last **45 ordinary rack classes**. Each class fixes the three unassigned marks on the published 21-point rack up to square symmetry. An assigned mark must belong to its unit tile and minimize its distance to the tile's centre in that tile's own square frame, with ties allowed. The centres and rotations of the tiles are free. [Rack geometry](../terminal-crosscheck/) · [Pinned public case table](https://github.com/Mira-Cult/math/blob/78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/unit-square-packing-18/replay/n18-482-base.json)

Earlier computational certificates excluded **136** whole classes. The remaining 45 classes divide into **91** terminal regions. We used the original definitions of these regions, generated new point suggestions from bare rack and wall constraints, and verified every region geometrically with an integer-only checker. Of the 91 exclusions, 80 used 128 angular bands, seven used 320, and four used 384. The previous 136 and the new 45 exhaust the **181** classes proposed empty at $U$. Together with the independently checked rack reduction, this confines every packing at $U$ to one of the six exceptional classes, numbered 53, 55, 82, 92, 115 and 137. Within those classes, proving the sharp side bound still depends on the treatment of the surviving regions. [Previous 136 classes](../empty-cover/) · [Exceptional empty regions](../endpoint-empty/) · [Exceptional partitions](../endpoint-cover/)

## Independent replay

From this directory, run the following with Python 3 and a C++17 compiler supporting signed 128-bit integers.

~~~sh
python3 replay.py --sanitize --workers 2
~~~

The driver reads the single pinned public JSON partition table and rejects a wrong SHA-256. Pass `--table /path/to/n18-482-base.json` to replay offline. It reconstructs all rack masks, checks that the two closed children cover each partition split, and subtracts the 136 previously credited masks to obtain the roster for this run. It verifies the 91 leaf IDs and their compressed traces against the actual cuts in the table, then rebuilds the integer geometry kernel to rerun all exclusions. Earlier certificates are replayable through their own drivers. [Replay](replay.py) · [Trace archive](points.xz) · [Parameters and hashes](receipt.json) · [Partition checker](../empty-cover/cover.py)

A coordinate cutoff is an exact threshold in millionths. For an angle cutoff $v/B_{\rm source}$ we convert its numerator to the solver's cutoff scale of 128 with the integer factor $128/B_{\rm source}$. The independent solver encloses continuous rotations by closed rational half-angle bands. Its resolution can be chosen separately from the source cutoff scale. Optional `--regenerate` discovers fresh guaranteed-point suggestions and sends them to the same integer-only checker. Every accepted point must satisfy the defining integer halfplanes before it can constrain another tile. A region closes when a required tile has no surviving placement.
