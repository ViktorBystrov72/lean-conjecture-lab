"""Prove that at most 17 members of poses.txt fit together in the container."""

import argparse
import hashlib
import os
from itertools import combinations
from math import comb
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import NamedTuple


ROOT = Path(__file__).resolve().parent
SCALE = 10_000_000
SIDE = 48_228_756  # The container side is SIDE / SCALE.
MARK_SCALE = 48_228_760
POOL_SHA256 = "42cc2a46f6285288f3ba12dbb0079e28851d61fabcebf5c3f77e703edc9a5d57"
WITNESS_SHA256 = "05ab7d4b52be4f27822f1161e3341a765f92c72bdeeb7a666b9cac5f8a38578d"
CNF_SHA256 = "8bd60d42eae3fa84f97441d03f6d96d514c88ea0337a5156ac30e35b81973739"


class Pose(NamedTuple):
    x: int
    y: int
    a: int
    b: int
    c: int

    def axes(self):
        return ((self.a, self.b), (-self.b, self.a))

    def vertices(self):
        """Numerators with common denominator 2*SCALE*c."""
        return [(2*self.c*self.x + SCALE*(s*self.a - t*self.b),
                 2*self.c*self.y + SCALE*(s*self.b + t*self.a))
                for s in (-1, 1) for t in (-1, 1)]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_poses(path, expected_length, expected_hash):
    if digest(path) != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {path}")
    poses = [Pose(*map(int, line.split())) for line in path.read_text().splitlines()]
    if len(poses) != expected_length or len(set(poses)) != expected_length:
        raise ValueError(f"Expected {expected_length} distinct placements in {path}")
    for p in poses:
        if p.c <= 0 or p.a*p.a + p.b*p.b != p.c*p.c:
            raise ValueError(f"Non-unit frame: {p}")
        if any(not 0 <= z <= 2*p.c*SIDE for vertex in p.vertices() for z in vertex):
            raise ValueError(f"Wall crossing: {p}")
    return poses


def project(vertices, axis):
    a, b = axis
    values = [a*x + b*y for x, y in vertices]
    return min(values), max(values)


def verify_witness(poses, witness):
    if not set(witness) <= set(poses):
        raise ValueError("Witness outside the pool")
    for p, q in combinations(witness, 2):
        for axis in p.axes() + q.axes():
            p_lo, p_hi = project(p.vertices(), axis)
            q_lo, q_hi = project(q.vertices(), axis)
            if p_hi*q.c <= q_lo*p.c or q_hi*p.c <= p_lo*q.c:
                break
        else:
            raise ValueError(f"Overlapping witness squares: {p}, {q}")
    print("Verified 17 placements and all 136 pair separations.", flush=True)


def mark_groups(poses):
    # Points in units of 1/(2000*SCALE), listed in lexicographic order.
    marks = set()
    for a, b in [(390, 390), (617, 617), (797, 359), (1000, 716), (1000, 1000)]:
        for x, y in [(a, b), (b, a)]:
            for xx in (x, 2000-x):
                for yy in (y, 2000-y):
                    marks.add((xx*MARK_SCALE, yy*MARK_SCALE))
    marks = sorted(marks)
    groups = [[] for _ in marks]
    for i, p in enumerate(poses, 1):
        for k, (x, y) in enumerate(marks):
            dx, dy = x - 2000*p.x, y - 2000*p.y
            if max(abs(dx*p.a + dy*p.b), abs(-dx*p.b + dy*p.a)) < 1000*SCALE*p.c:
                groups[k].append(i)
                break
        else:
            raise ValueError(f"Pose {i} has no strictly interior mark")
    return groups


def encode(poses, dest):
    groups = mark_groups(poses)
    polygons = [p.vertices() for p in poses]
    axes = [p.axes() for p in poses]
    projections = {axis: [project(poly, axis) for poly in polygons]
                   for axis in {a for pair in axes for a in pair}}
    n = len(poses)
    g = len(groups)
    # Write clashes to disk while counting them for the DIMACS header.
    with tempfile.TemporaryFile("w+", dir=dest.parent) as clashes:
        count = 0
        for i, j in combinations(range(n), 2):
            p, q = poses[i], poses[j]
            if (p.x-q.x)**2 + (p.y-q.y)**2 >= 2*SCALE*SCALE:
                continue  # Disjoint open circumdisks imply disjoint interiors.
            for axis in axes[i] + axes[j]:
                p_lo, p_hi = projections[axis][i]
                q_lo, q_hi = projections[axis][j]
                if p_hi*q.c <= q_lo*p.c or q_hi*p.c <= p_lo*q.c:
                    break
            else:
                clashes.write(f"-{i+1} -{j+1} 0\n")
                count += 1
        four = g - 18 + 1
        clauses = count + g + comb(g, four)
        with dest.open("w", newline="\n") as out:
            out.write(f"p cnf {n+g} {clauses}\n")
            clashes.seek(0)
            shutil.copyfileobj(clashes, out)
            for k, group in enumerate(groups, 1):
                out.write(" ".join(map(str, [-(n+k), *group, 0])) + "\n")
            for selected in combinations(range(n+1, n+g+1), four):
                out.write(" ".join(map(str, selected)) + " 0\n")
    if digest(dest) != CNF_SHA256:
        raise ValueError("Regenerated CNF SHA-256 mismatch")
    print(f"Verified CNF with {n+g} variables and {clauses} clauses.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cadical", default="cadical", help="path to the CaDiCaL executable")
    args = parser.parse_args()
    poses = load_poses(ROOT/"poses.txt", 7140, POOL_SHA256)
    witness = load_poses(ROOT/"witness-17.txt", 17, WITNESS_SHA256)
    verify_witness(poses, witness)
    with tempfile.TemporaryDirectory(prefix="finite-packing-") as temp:
        work = Path(temp)
        cnf, proof, checker = work/"pool.cnf", work/"proof.lrat", work/"rup_check"
        subprocess.run([os.environ.get("CXX", "c++"), "-std=c++17", "-O3",
                        ROOT/"rup_check.cpp", "-o", checker], check=True)
        encode(poses, cnf)
        result = subprocess.run([args.cadical, "--lrat=1", "--no-binary", "-q", cnf, proof])
        if result.returncode != 20:
            raise RuntimeError(f"Expected CaDiCaL UNSAT (20), got {result.returncode}")
        subprocess.run([checker, cnf, proof], check=True)
        print(f"Generated proof SHA-256: {digest(proof)}")


if __name__ == "__main__":
    main()
