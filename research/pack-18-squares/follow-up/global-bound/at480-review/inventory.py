"""Second implementation of the orbit inventory, split coverage and receipt checks."""

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path
import re
from urllib.request import urlopen
import zlib


HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "at480"
FOLLOW = HERE.parents[1]
SIDE = 4_800_000_000
RACK = 4_822_876_000
TABLE = "n18-482-base.json"
TABLE_DIGEST = "d6fa37860cde0d0e8f8ddedc25508f478fe30112be16e79697cb9ab59c54f086"
PIN = "78bec6aacebf304d942a9225e16c2f18165778ff"
URL = f"https://raw.githubusercontent.com/Mira-Cult/math/{PIN}/notes/geometry/unit-square-packing-18/replay/{TABLE}"


def require(condition, label):
    if not condition:
        raise ValueError(label)


def decode(raw):
    def no_repeats(pairs):
        require(len(dict(pairs)) == len(pairs), "repeated JSON key")
        return dict(pairs)
    return json.loads(raw, object_pairs_hook=no_repeats)


def representatives():
    points = [(390,390), (617,617), (797,359), (1000,716), (1000,1000)]
    operations = list(product((False, True), repeat=3))
    def image(p, g):
        x, y = reversed(p) if g[0] else p
        return (2000 - x if g[1] else x, 2000 - y if g[2] else y)
    points = sorted({image(p,g) for p in points for g in operations})
    require(len(points) == 21, "rack cardinality")
    transforms = [[points.index(image(p,g)) for p in points] for g in operations]
    todo = set(combinations(range(len(points)), 3))
    require(len(todo) == 1330, "unused triples")
    masks = []
    while todo:
        triple = min(todo)
        orbit = {tuple(sorted(t[i] for i in triple)) for t in transforms}
        require(triple == min(orbit) and orbit <= todo, "orbit partition")
        masks.append(sum(1 << j for j in range(21) if j not in triple))
        todo -= orbit
    require(len(masks) == 187, "orbit cardinality")
    return sorted(masks)


def direct(row, mask, budget):
    m = re.fullmatch(r"EXCLUDED (empty owner (\d+)|guaranteed overlap (\d+) (\d+)) round (\d+)", row["verdict"])
    require(m and int(m[5]) < budget, "direct contradiction")
    owners = [int(i) for i in m.group(2,3,4) if i is not None]
    require(len(owners) == len(set(owners)) and all(i < 21 and mask >> i & 1 for i in owners), "geometric owner")


def trace(row, mask, blob, digest):
    require(sha256(blob).hexdigest() == digest, "trace digest")
    m = re.fullmatch(rf"EXCLUDED mask {mask} index (\d+) round (\d+) [AB]", row["verdict"])
    require(m and int(m[1]) < 18 and int(m[2]) < row["rounds"], "trace contradiction")


def split_tree(paths, mask):
    require(paths, "missing half")
    if any(not p for p in paths):
        require(paths == [[]], "duplicate or nonterminal leaf")
        return
    owner, kind, value = paths[0][:3]
    require(0 <= owner < 21 and mask >> owner & 1 and kind in range(6), "split target")
    require(0 < value < (128 if kind >= 4 else RACK // 1000), "split threshold")
    children = [[], []]
    for path in paths:
        require(len(path) % 3 == 0, "cut record")
        i, k, v = path[:3]
        require((i, k // 2, v) == (owner, kind // 2, value), "inconsistent children")
        children[k % 2].append(path[3:])
    for half in children:
        split_tree(half, mask)


def check(m, packets, masks, table):
    require((m["side"],m["wall_side_nano"],m["rack_side_nano"]) == ("24/5", SIDE, RACK), "scale")
    ids = [r["case"] for r in m["direct"] + m["certified"]] + m["three"] + m["special"] + m["guard"]
    require(sorted(ids) == list(range(187)), "coverage")
    require([len(m[k]) for k in ("direct","certified")] == [153,27], "routes")
    require((m["three"],m["special"],m["guard"]) == ([22,54,132],[0,53,55],[137]), "split groups")
    require(set(packets) == {str(r["case"]) for r in m["certified"]}, "trace inventory")
    for r in m["direct"] + m["certified"]:
        require(int(r["mask"],16) == masks[r["case"]], "canonical mask")
    for r in m["direct"]:
        direct(r, masks[r["case"]], r["round_limit"])
    for r in m["certified"]:
        require(r["side_nanounits"] == SIDE and r["status"] == "excluded", "trace scope")
        trace(r, masks[r["case"]], packets[str(r["case"])].encode(), r["trace_sha256"])

    three = decode((RUN / "three/receipt.json").read_bytes())
    special_dir = FOLLOW / "row-guards/independent480"
    special = decode((special_dir / "receipt.json").read_bytes())
    guards = decode((FOLLOW / "endpoint-guards/side480.json").read_bytes())
    require([d["side"] for d in [three,special,guards]] == ["24/5"]*3, "terminal side")
    require(three["side_nanounits"] == special["side_nano"] == SIDE, "terminal scale")
    require(three["cases"] == m["three"] and special["closed_masks"] == m["special"], "terminal ids")
    require(len(three["leaves"]) == 6 and len(special["runs"]) == 10, "extra leaves")
    for case in m["three"] + m["special"] + m["guard"]:
        mask = masks[case]
        if case in (53,55):
            paths = [[]]
        else:
            denominator, regions = table[format(mask,"x")]
            require(denominator == 128, "angle cut scale")
            paths = [row[0] for row in regions]
        split_tree(paths, mask)
        source = three["leaves"] if case in m["three"] else special["runs"] if case in m["special"] else guards["leaves"]
        rows = [r for r in source if r["case"] == case]
        leaves = [0 if r["leaf"] == "root" else int(r["leaf"]) for r in rows]
        require(sorted(leaves) == list(range(len(paths))), "terminal indices")
        for r,leaf in zip(rows,leaves):
            require(int(r["mask"],16) == mask, "terminal mask")
            if case in m["special"]:
                require(r["cuts"] == paths[leaf] and ((r["leaf"] == "root") == (case in (53,55))), "special cuts")
                trace(r, mask, (special_dir / "certificates" / r["certificate"]).read_bytes(), r["sha256"])
            elif case in m["three"] or r["method"] == "geometry":
                direct(r, mask, r["rounds"])
            else:
                a = r["interval_receipt"]
                require(r["method"] == "guard" and min(a.values()) > 0, "missing probe")
                require(a["band_pairs"] == a["first_middle_bands"]*a["second_middle_bands"], "missing band pair")
        if case == 137:
            require(Counter(r["method"] for r in rows) == {"geometry":2,"guard":4}, "guard inventory")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--table", type=Path, help="local copy of the pinned base table")
    args = ap.parse_args()
    raw = args.table.read_bytes() if args.table else urlopen(URL,timeout=30).read()
    require(sha256(raw).hexdigest() == TABLE_DIGEST, "base table digest")
    table = decode(raw)
    masks = representatives()
    manifest = decode((RUN / "manifest.json").read_bytes())
    packets = decode(zlib.decompress((RUN / "points.zlib").read_bytes()))
    check(manifest, packets, masks, table)
    mutations = [
        lambda m: m["direct"].pop(),
        lambda m: m["direct"][1].update(mask=m["direct"][0]["mask"]),
        lambda m: m.update(side="4.81"),
        lambda m: m["certified"][0].update(trace_sha256="0"*64),
    ]
    for change in mutations:
        broken = deepcopy(manifest)
        change(broken)
        try:
            check(broken, packets, masks, table)
        except ValueError:
            continue
        raise ValueError("negative control accepted")
    print("187 canonical orbits checked. All required split paths and trace hashes agree. Four negative controls rejected.")


if __name__ == "__main__":
    main()
