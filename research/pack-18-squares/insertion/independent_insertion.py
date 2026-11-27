"""Independently exclude a freely rotating eighteenth tile by planar arrangements.

Run from this directory with Python 3.9+:
    python3 independent_insertion.py ../finite/witness-17.txt
"""
import argparse
from fractions import Fraction as F
from itertools import combinations, product
from math import gcd, lcm
from pathlib import Path


def frame(t):
    return (1-t*t)/(1+t*t), 2*t/(1+t*t)


def square(offset, direction, half):
    x,y = offset
    c,s = direction
    return [(x+half*(i*c-j*s), y+half*(i*s+j*c)) for i,j in product((-1,1),repeat=2)]


def convex_hull(points):
    points = sorted(set(points))

    def turn(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def chain(order):
        result = []
        for v in order:
            while len(result) >= 2 and turn(result[-2], result[-1], v) <= 0:
                result.pop()
            result.append(v)
        return result

    return chain(points)[:-1] + chain(reversed(points))[:-1]


def line(a,b,c):
    """Integer coefficients for a*x + b*y + c >= 0, preserving orientation."""
    d = lcm(F(a).denominator, F(b).denominator, F(c).denominator)
    ia,ib,ic = int(a*d),int(b*d),int(c*d)
    norm = gcd(gcd(abs(ia),abs(ib)),abs(ic))
    return ia//norm,ib//norm,ic//norm


def facets(points):
    hull = convex_hull(points)
    result = []
    for (x,y),(u,v) in zip(hull, hull[1:]+hull[:1]):
        a,b = y-v,u-x
        result.append(line(a,b,-a*x-b*y))
    return result


def intersection(p,q):
    a,b,c = p
    d,e,f = q
    w = a*e-b*d
    if w == 0:
        return None
    x,y = b*f-c*e,c*d-a*f
    if w < 0:
        x,y,w = -x,-y,-w
    return x,y,w


def inside(point, polygon, strict):
    x,y,w = point
    for a,b,c in polygon:
        d = a*x+b*y+c*w
        if d < 0 or (d == 0 and strict):
            return False
    return True


def uncovered(obstacles, wall, side):
    """Return an uncovered arrangement vertex, or certify the entire box."""
    upper = side-wall
    if upper < wall:
        return None,0
    box = [line(1,0,-wall),line(0,1,-wall),line(-1,0,upper),line(0,-1,upper)]
    # Any uncovered point has at least one closed exterior half-plane for
    # each obstacle. Their intersection with the closed box is a nonempty
    # bounded polyhedron. Some vertex lies on two nonparallel input lines,
    # including when the polyhedron is a segment or a single point.
    lines = set(box)
    for polygon in obstacles:
        lines.update(polygon)
    tested = 0
    for a,b in combinations(sorted(lines),2):
        p = intersection(a,b)
        if p is not None and inside(p,box,False):
            tested += 1
            if not any(inside(p,polygon,True) for polygon in obstacles):
                return p,tested
    return None,tested


def load_tiles(path):
    result = []
    for record in path.read_text().splitlines():
        x,y,a,b,c = map(int,record.split())
        if c <= 0 or a*a+b*b != c*c:
            raise ValueError("Non-unit frame")
        result.append(((F(x,10**7),F(y,10**7)),(F(a,c),F(b,c))))
    if len(result) != 17:
        raise ValueError("Expected 17 reference positions")
    return result


def exclude(tiles,side,motion,max_bands):
    # For each true unit normal, the shift of an old centre costs at most
    # sqrt(2)*motion <= 3*motion/2. A core point costs at most
    # h*(|cos(delta)|+|sin(delta)|) <= h*(1+motion) under rotation.
    half = (1-3*motion)/(2*(1+motion))
    cores = [square(center,uv,half) for center,uv in tiles]
    work = [(F(0),F(1),1)]
    kept = tested = maximum = 0
    while work:
        lo,hi,n = work.pop()
        c0,s0 = frame(lo)
        c1,s1 = frame(hi)
        # Use the left-end orientation. sin(theta - theta0) is at most
        # sin(theta1 - theta0) on the quarter-turn. All quantities are exact.
        sin_delta = s1*c0-c1*s0
        free_core = square((0,0),(c0,s0),F(1,2)/(1+sin_delta))
        obstacles = []
        for core in cores:
            obstacles.append(facets([(x-u,y-v) for x,y in core for u,v in free_core]))
        # cos decreases and sin increases on [0,pi/2], so every admissible
        # centre has wall distance at least (cos(theta1)+sin(theta0))/2.
        witness,count = uncovered(obstacles,(c1+s0)/2,side)
        tested += count
        maximum = max(maximum,n)
        if witness is None:
            kept += 1
            continue
        if 2*n > max_bands:
            print("Inconclusive band",str(lo),str(hi),"uncovered relaxed point",witness)
            return False
        mid = (lo+hi)/2
        work.extend([(mid,hi,2*n),(lo,mid,2*n)])
    print(f"Excluded all angles: {kept} covered intervals, maximum denominator {maximum}, "
          f"{tested} in-box line intersections tested.")
    return True


def controls():
    big = facets([(-1,-1),(-1,2),(2,-1),(2,2)])
    adjacent = [facets([(x,y) for x in xs for y in (-1,2)]) for xs in ((-1,F(1,2)),(F(1,2),2))]
    # Both open obstacles exclude their common edge; a free point survives.
    if uncovered([big],F(0),F(1))[0] is not None or uncovered(adjacent,F(0),F(1))[0] is None:
        raise ValueError("Incorrect open-boundary handling")
    if uncovered([],F(1,2),F(1))[0] is None:
        raise ValueError("Degenerate singleton box lost")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout",type=Path)
    parser.add_argument("--side",type=F,default=F(97,20))
    parser.add_argument("--motion",type=F,default=F(1,32))
    parser.add_argument("--max-bands",type=int,default=1024)
    args = parser.parse_args()
    if args.side <= 0 or not 0 <= args.motion < F(1,3) or args.max_bands < 1:
        parser.error("invalid geometry or subdivision budget")
    controls()
    if not exclude(load_tiles(args.layout),args.side,args.motion,args.max_bands):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
