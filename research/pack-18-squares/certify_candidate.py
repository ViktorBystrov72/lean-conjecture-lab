"""Turn numerical centres and angles into an exact packing of 18 unit squares.

Input JSON: {"squares": [[x, y, angle_in_radians], ...]}. A supplied side
length is ignored. Output can be checked using rational arithmetic alone.
"""

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations
from math import isfinite, pi, remainder, tan
from pathlib import Path


@dataclass(frozen=True)
class Tile:
    x: Fraction
    y: Fraction
    c: Fraction
    s: Fraction

    def axes(self):
        return ((self.c, self.s), (-self.s, self.c))

    def radius(self, axis):
        a, b = axis
        return (abs(a * self.c + b * self.s) + abs(-a * self.s + b * self.c)) / 2

    def extent(self):
        return (abs(self.c) + abs(self.s)) / 2


def rational_tile(row, digits):
    x, y, angle = row
    if not isfinite(float(angle)):
        raise ValueError("The angle must be finite")
    # Only the choice of the rational parameter uses floating point.
    # The resulting unit frame and all subsequent comparisons are exact.
    t = Fraction(round(tan(remainder(float(angle), pi / 2) / 2) * 10**digits), 10**digits)
    d = 1 + t*t
    return Tile(Fraction(x), Fraction(y), (1 - t*t) / d, 2*t / d)


def scale_for_pair(first, second):
    dx, dy = second.x - first.x, second.y - first.y
    ratios = []
    for axis in first.axes() + second.axes():
        gap = abs(dx * axis[0] + dy * axis[1])
        if gap:
            ratios.append((first.radius(axis) + second.radius(axis)) / gap)
    if not ratios:
        raise ValueError("Coincident centres cannot be separated by dilation")
    return min(ratios)


def enclose(tiles):
    scale = max(scale_for_pair(a, b) for a, b in combinations(tiles, 2))
    xmin = min(scale * t.x - t.extent() for t in tiles)
    ymin = min(scale * t.y - t.extent() for t in tiles)
    xmax = max(scale * t.x + t.extent() for t in tiles)
    ymax = max(scale * t.y + t.extent() for t in tiles)
    side = max(xmax - xmin, ymax - ymin)
    return side, [Tile(scale * t.x - xmin, scale * t.y - ymin, t.c, t.s) for t in tiles]


def verify(side, tiles):
    if len(tiles) != 18 or side <= 0:
        raise ValueError("Expected 18 tiles in a positive-side container")
    for i, t in enumerate(tiles):
        if t.c*t.c + t.s*t.s != 1:
            raise ValueError(f"Tile {i} has a non-unit frame")
        for ex, ey in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            x = t.x + (ex*t.c - ey*t.s) / 2
            y = t.y + (ex*t.s + ey*t.c) / 2
            if not (0 <= x <= side and 0 <= y <= side):
                raise ValueError(f"Tile {i} crosses a wall")
    for (i, a), (j, b) in combinations(enumerate(tiles), 2):
        if not any(abs((b.x - a.x)*u + (b.y - a.y)*v) >= a.radius((u, v)) + b.radius((u, v))
                   for u, v in a.axes() + b.axes()):
            raise ValueError(f"Tiles {i} and {j} overlap")


def strictly_below_record(side):
    h = 2 * side - 7
    return h < 0 or h*h < 7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--digits", type=int, default=15, choices=range(6, 17), metavar="6..16")
    parser.add_argument("--output", type=Path, help="save the exact rational placement")
    parser.add_argument("--verify", action="store_true", help="read an exact output without repair")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(), parse_float=Decimal)
    if args.verify:
        side = Fraction(data["side"])
        tiles = [Tile(*(Fraction(v) for v in row)) for row in data["frames"]]
    else:
        if len(data["squares"]) != 18:
            raise ValueError("Expected 18 numerical placements")
        side, tiles = enclose([rational_tile(row, args.digits) for row in data["squares"]])
    verify(side, tiles)
    with localcontext() as ctx:
        ctx.prec = 35
        length = Decimal(side.numerator) / Decimal(side.denominator)
        delta = length - (7 + Decimal(7).sqrt()) / 2
        print(f"Certified side (approx.) {length}; side minus record {delta:+.8E}")
    print("Strict improvement:", strictly_below_record(side))
    if args.output:
        frames = [[str(v) for v in (t.x, t.y, t.c, t.s)] for t in tiles]
        args.output.write_text(json.dumps({"side": str(side), "frames": frames}, indent=2) + "\n")


if __name__ == "__main__":
    main()
