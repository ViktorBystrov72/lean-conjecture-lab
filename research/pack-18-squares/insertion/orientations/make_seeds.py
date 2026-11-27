"""Derive all clipped Voronoi vertices admitting an extra inscribed disk."""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from free_angles import clip
from free_tile import HALF, LENGTH
from scan import read_rows


def holes(sites):
    candidates = set()
    high = LENGTH - HALF
    for i, (a, b) in enumerate(sites):
        cell = [(HALF, HALF), (high, HALF), (high, high), (HALF, high)]
        for j, (x, y) in enumerate(sites):
            if j != i:
                cell = clip(cell, 2 * (x - a), 2 * (y - b), x * x + y * y - a * a - b * b)
        for x, y in cell:
            if (x - a) ** 2 + (y - b) ** 2 >= 1:
                candidates.add((x, y))
    return [[str(x), str(y)] for x, y in sorted(candidates)]


def build():
    pool_file = HERE.parent.parent / "finite" / "poses.txt"
    samples = json.loads((HERE.parent / "sample-indices.json").read_text())
    if hashlib.sha256(pool_file.read_bytes()).hexdigest() != samples["pool_sha256"]:
        raise ValueError("Pool digest mismatch")
    pool = read_rows(pool_file)
    rows = []
    for i, select in enumerate(samples["layouts"]):
        poses = [pool[j] for j in select]
        points = [(Fraction(x, 10**7), Fraction(y, 10**7)) for x, y, *_ in poses]
        candidates = holes(points)
        if candidates:
            rows.append(dict(layout=i, fixed=poses, holes=candidates))
    return dict(side=str(LENGTH), layouts=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="write the regenerated JSON instead of checking the supplied seeds",
    )
    opt = parser.parse_args()
    content = json.dumps(build(), separators=(",", ":")) + "\n"
    if opt.output:
        opt.output.write_text(content)
    elif (HERE / "seeds.json").read_text() != content:
        raise ValueError("Seed coordinates differ from the recomputed values")
    print("Surviving layouts:", len(json.loads(content)["layouts"]))
