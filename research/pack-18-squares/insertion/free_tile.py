"""Exhaustively search the real centre and rotation of one additional unit square.

The fixed layout uses integer rows x y a b d, for centre (x,y)/10^7
and orthonormal frame (a,b)/d, (-b,a)/d. Only the order of testing the
obstacles uses floating point. No pruning decision uses floating point.
"""
import argparse
import json
from collections import Counter
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path

LENGTH = Q(48228756, 10**7)
HALF = Q(1, 2)


def basis(t):
    return ((1-t*t)/(1+t*t), 2*t/(1+t*t))


def radius(axis, direction):
    x, y = axis
    c, s = direction
    return (abs(x*c+y*s) + abs(y*c-x*s))/2


def axes(u, v):
    return (u, (-u[1], u[0]), v, (-v[1], v[0]))


def separated(a, b):
    x, y, u = a
    xx, yy, v = b
    return any(abs(i*(x-xx)+j*(y-yy)) >= radius((i,j),u)+radius((i,j),v)
               for i,j in axes(u,v))


def check_fixed(path, side):
    fixed = []
    for line in path.read_text().splitlines():
        x, y, a, b, d = map(int, line.split())
        if d <= 0 or a*a+b*b != d*d:
            raise ValueError("invalid unit frame")
        tile = (Q(x, 10**7), Q(y, 10**7), (Q(a,d),Q(b,d)))
        r = (abs(tile[2][0])+abs(tile[2][1]))/2
        if not all(r <= c <= side-r for c in tile[:2]):
            raise ValueError("wall violation")
        if not all(separated(tile, prev) for prev in fixed):
            raise ValueError("fixed tiles overlap")
        fixed.append(tile)
    if len(fixed) != 17:
        raise ValueError("expected 17 fixed tiles")
    return fixed


def search(fixed, side, limit, max_depth, motion):
    # Each of the first 17 centres may move by motion along EACH coordinate
    # and may rotate by motion radians. This concentric square in its old
    # frame is inside every permitted new tile. In the new axes the centre
    # displacement costs at most 2*motion on either coordinate, and a rotated
    # square's support grows by at most a factor 1 + motion.
    obstacle_core = (1 - 4*motion)/(1 + motion)
    @lru_cache(maxsize=2048)
    def bounds(t0, t1):
        u = basis((t0+t1)/2)
        # A core of this side in the middle orientation lies in the real
        # tile at every angle of the interval: |delta angle| <= t1-t0.
        inner = 1/(1+t1-t0)
        # cos(theta)+sin(theta) is concave on [0, pi/2].
        wall = min(sum(basis(t0)),sum(basis(t1)))/2
        rows = []
        for x,y,v in fixed:
            rows.append([(a,b,a*x+b*y,inner*radius((a,b),u)+obstacle_core*radius((a,b),v))
                         for a,b in axes(u,v)])
        return wall, rows

    tally = Counter()
    unresolved = []
    stack = [(HALF, side-HALF, HALF, side-HALF, Q(0), Q(1), 0)]
    while stack and tally["nodes"] < limit:
        x0,x1,y0,y1,t0,t1,depth = stack.pop()
        tally["nodes"] += 1
        tally["maximum_depth"] = max(tally["maximum_depth"], depth)
        wall, rows = bounds(t0,t1)
        x0,x1,y0,y1 = max(x0,wall),min(x1,side-wall),max(y0,wall),min(y1,side-wall)
        if x1<x0 or y1<y0:
            tally["wall"] += 1
            continue
        x,hx,y,hy = (x0+x1)/2,(x1-x0)/2,(y0+y1)/2,(y1-y0)/2
        order = sorted(range(len(fixed)),key=lambda k:(float(fixed[k][0])-float(x))**2+
                                                      (float(fixed[k][1])-float(y))**2)
        closed = False
        for k in order:
            if all(abs(a*x+b*y-base)+abs(a)*hx+abs(b)*hy < reach for a,b,base,reach in rows[k]):
                closed = True
                break
        if closed:
            tally["overlap"] += 1
            continue
        mid = (t0+t1)/2
        u = basis(mid)
        extent = sum(u)/2
        tile = (x,y,u)
        if all(extent <= c <= side-extent for c in (x,y)) and all(separated(tile,b) for b in fixed):
            return {"status":"found", "x":str(x), "y":str(y), "t":str(mid), **tally}
        if depth >= max_depth:
            unresolved.append([str(v) for v in (x0,x1,y0,y1,t0,t1)])
            continue
        widths = (x1-x0, y1-y0, t1-t0)
        index = max(range(3),key=widths.__getitem__)
        interval = [x0,x1,y0,y1,t0,t1]
        m = (interval[2*index]+interval[2*index+1])/2
        left = interval.copy()
        right = interval.copy()
        left[2*index+1] = m
        right[2*index] = m
        stack.extend([(*right,depth+1),(*left,depth+1)])
    pending = len(unresolved)+len(stack)
    return {"status":"inconclusive" if pending else "excluded", "pending":pending, **tally}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witness",type=Path)
    parser.add_argument("--side",type=Q,default=LENGTH)
    parser.add_argument("--motion",type=Q,default=Q(0),
                        help="centre motion per coordinate and angular motion in radians for each reference tile")
    parser.add_argument("--limit",type=int,default=100000)
    parser.add_argument("--depth",type=int,default=100)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.limit <= 0 or not 0 <= args.depth <= 300 or not 0 <= args.motion < Q(1,4):
        parser.error("expected positive budget, depth between 0 and 300 and motion in [0,1/4)")
    result = search(check_fixed(args.witness,args.side),args.side,args.limit,args.depth,args.motion)
    result.update(side=str(args.side),witness=args.witness.name,limit=args.limit,depth=args.depth,
                  motion=str(args.motion))
    record=json.dumps(result,indent=2)
    print(record)
    if args.output:
        args.output.write_text(record+"\n")


if __name__ == "__main__":
    main()
