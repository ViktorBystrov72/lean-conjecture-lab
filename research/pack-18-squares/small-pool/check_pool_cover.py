"""Verify a finite-pool packing bound with integer arithmetic.

Usage: python3 check_pool_cover.py pool-0.txt clique-pool-0-cover.json
A pool row is x y a b c. Its centre is (x,y)/10^7 and its edge is (a,b)/c.
A clique is a set of poses whose interiors intersect pairwise. Any packing can
use at most one pose from it. The certificate gives integer clique weights.
"""
from argparse import ArgumentParser
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

SCALE = 10_000_000
CONTAINER = 48_228_756

def polygon(row):
    x, y, a, b, c = row
    if c <= 0 or a*a + b*b != c*c:
        raise ValueError("Invalid unit direction")
    # Vertex coordinates in units of 1/(2*c*SCALE), counterclockwise.
    vertices = tuple((2*c*x + SCALE*(s*a - t*b), 2*c*y + SCALE*(s*b + t*a))
                     for s,t in ((-1,-1),(1,-1),(1,1),(-1,1)))
    if not all(0 <= z <= 2*c*CONTAINER for v in vertices for z in v):
        raise ValueError("A square crosses the container")
    return vertices, 2*c

def outside_some_edge(first, second):
    p, den = first
    q, other = second
    for k, (x, y) in enumerate(p):
        xx, yy = p[(k+1) % 4]
        dx, dy = xx - x, yy - y
        if all(dx*(qy*den-y*other) <= dy*(qx*den-x*other) for qx,qy in q):
            return True
    return False

def check(pool, certificate):
    rows = [tuple(map(int,ln.split())) for ln in pool.splitlines()]
    d = certificate
    if len(set(rows)) != len(rows) or len(rows) != d['columns'] or sha256(pool).hexdigest() != d['sha256']:
        raise ValueError("Pool identity mismatch")
    shapes = [polygon(row) for row in rows]
    if d['den'] <= 0 or not isinstance(d['den'],int):
        raise ValueError("Invalid coverage denominator")

    @lru_cache(None)
    def disjoint(i,j):
        return outside_some_edge(shapes[i],shapes[j]) or outside_some_edge(shapes[j],shapes[i])
    def indices(values):
        if any(type(v) is not int or v < 0 or v >= len(rows) for v in values) or len(set(values)) != len(values):
            raise ValueError("Invalid or repeated index")
        return sorted(values)

    used = indices(d['compatible'])
    if not all(disjoint(i,j) for i,j in combinations(used,2)):
        raise ValueError("The proposed packing contains intersecting interiors")
    coverage = [0]*len(rows)
    total = 0
    for item in d['cover']:
        vs = indices(item['indices'])
        w = item['w']
        if type(w) is not int or w <= 0:
            raise ValueError("Invalid clique weight")
        if any(disjoint(i,j) for i,j in combinations(vs,2)):
            raise ValueError("A claimed clique contains a compatible pair")
        for v in vs:
            coverage[v] += w
        total += w
    if min(coverage) < d['den']:
        raise ValueError("A pose is missing coverage")
    bound = Fraction(total, d['den'])
    if len(used) != bound.numerator // bound.denominator:
        raise ValueError("Packing and upper bound do not meet")
    return len(used), len(rows), len(d['cover']), bound

if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('pool', type=Path)
    parser.add_argument('certificate', type=Path)
    args = parser.parse_args()
    size, n, m, bound = check(args.pool.read_bytes(), json.loads(args.certificate.read_bytes()))
    print(f"Exact maximum {size} over {n} poses; {m} verified cliques give upper bound {bound}.")
