"""Exact orientation-independent hole test, using clipped Voronoi cells."""

import argparse
import json
from fractions import Fraction as Q
from pathlib import Path

from free_tile import HALF, LENGTH, check_fixed


def clip(poly, a, b, k):
    """Intersect a convex polygon with a*x+b*y <= k, retaining its boundary."""
    if not poly:
        return []
    out = []
    prev = poly[-1]
    gp = a*prev[0]+b*prev[1]-k
    for point in poly:
        g = a*point[0]+b*point[1]-k
        if gp*g < 0:
            t = gp/(gp-g)
            out.append(tuple(v+t*(w-v) for v,w in zip(prev,point)))
        if g <= 0:
            out.append(point)
        prev, gp = point, g
    return out


def largest_hole(centres, side):
    best = (-1, None)
    high = side-HALF
    for i, (cx,cy) in enumerate(centres):
        cell = [(HALF,HALF),(high,HALF),(high,high),(HALF,high)]
        for j,(x,y) in enumerate(centres):
            if j != i:
                cell = clip(cell,2*(x-cx),2*(y-cy),x*x+y*y-cx*cx-cy*cy)
        # Squared distance to site i is convex on its clipped Voronoi cell.
        for x,y in cell:
            d = (x-cx)**2+(y-cy)**2
            if d > best[0]:
                best = (d,(x,y))
    if best[1] is None:
        raise ValueError("empty centre domain")
    return best


def can_exclude(distance_squared, drift):
    # ||delta centre||_2 <= 3/2 * drift for coordinatewise L-infinity drift.
    allowed = 1 - Q(3,2)*drift
    return allowed > 0 and distance_squared < allowed*allowed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witnesses", type=Path,nargs='+')
    parser.add_argument("--side",type=Q,default=LENGTH)
    parser.add_argument("--drift",type=Q,default=Q(0))
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.drift < 0 or args.side < 1:
        parser.error("invalid search region")
    results = []
    for path in args.witnesses:
        sites = [(x,y) for x,y,_ in check_fixed(path,args.side)]
        distance, p = largest_hole(sites,args.side)
        results.append({"file":path.name,"distance_squared":str(distance),"point":list(map(str,p)),
                        "excluded":can_exclude(distance,args.drift)})
    report = {"side":str(args.side),"drift":str(args.drift),"layouts":len(results),
              "excluded":sum(line["excluded"] for line in results),"results":results}
    print(f"{report['excluded']} of {len(results)} layouts are excluded with all rotations free.")
    if args.output:
        args.output.write_text(json.dumps(report,indent=2)+"\n")
    else:
        print(json.dumps(results,indent=2))


if __name__ == "__main__":
    main()
