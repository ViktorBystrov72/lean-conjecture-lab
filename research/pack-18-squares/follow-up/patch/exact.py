"""Fast exact rational repair and side comparison for numerical witnesses."""

from fractions import Fraction
from itertools import combinations
import math


def repair(positions, digits=17, slope_limit=10**10):
    D = 10**digits
    centers = []
    frames = []
    slopes = []
    for x, y, angle in positions:
        centers.append((round(Fraction(str(x)) * D), round(Fraction(str(y)) * D)))
        angle = math.remainder(angle, math.pi / 2)
        t = Fraction(str(math.tan(angle / 2))).limit_denominator(slope_limit)
        p, q = t.numerator, t.denominator
        frames.append((q * q - p * p, 2 * p * q, q * q + p * p))
        slopes.append(t)
    # Compare every possible separating-axis requirement with integer products.
    # All four axes of a pair have the same sum of tile support radii.
    num, den = 0, 1
    for i, j in combinations(range(len(centers)), 2):
        a, b, r = frames[i]
        c, d, s = frames[j]
        dx = centers[i][0] - centers[j][0]
        dy = centers[i][1] - centers[j][1]
        m = max(
            abs(dx * a + dy * b) * s,
            abs(dy * a - dx * b) * s,
            abs(dx * c + dy * d) * r,
            abs(dy * c - dx * d) * r,
        )
        if not m:
            raise ValueError("duplicate centres")
        demand = (r * s + abs(a * c + b * d) + abs(a * d - b * c)) * D
        if demand * den > num * 2 * m:
            num, den = demand, 2 * m
    scale = Fraction(num, den)
    repaired = [(scale * Fraction(x, D), scale * Fraction(y, D)) for x, y in centers]
    radius = [Fraction(abs(a) + abs(b), 2 * r) for a, b, r in frames]
    lo = [min(p[k] - v for p, v in zip(repaired, radius)) for k in (0, 1)]
    hi = [max(p[k] + v for p, v in zip(repaired, radius)) for k in (0, 1)]
    side = max(hi[k] - lo[k] for k in (0, 1))
    output = [(x - lo[0], y - lo[1], t) for (x, y), t in zip(repaired, slopes)]
    return side, output


def below(side):
    lhs = 2 * side - 7
    return lhs < 0 or lhs * lhs < 7


def verify(side, tiles):
    """Independent check by all polygon corners and direct interval projection."""
    if side <= 0 or len(tiles) != 18:
        raise ValueError("expected a positive side and exactly 18 squares")
    polygons = []
    normals = []
    for x, y, t in tiles:
        c = (1 - t * t) / (1 + t * t)
        s = 2 * t / (1 + t * t)
        assert c * c + s * s == 1
        vertices = tuple(
            (x + (h * c - k * s) / 2, y + (h * s + k * c) / 2)
            for h, k in ((1, 1), (-1, 1), (-1, -1), (1, -1))
        )
        if not all(0 <= u <= side and 0 <= v <= side for u, v in vertices):
            raise ValueError("wall violation")
        polygons.append(vertices)
        normals.append(((c, s), (-s, c)))
    for i, j in combinations(range(len(tiles)), 2):
        for a, b in normals[i] + normals[j]:
            vals1 = [a * x + b * y for x, y in polygons[i]]
            vals2 = [a * x + b * y for x, y in polygons[j]]
            if max(vals1) <= min(vals2) or max(vals2) <= min(vals1):
                break
        else:
            raise ValueError(f"overlap {i} {j}")


if __name__ == "__main__":
    import argparse
    import json
    from decimal import Decimal, localcontext
    from pathlib import Path

    p = argparse.ArgumentParser(
        description="Verify a saved rational placement and compare with H exactly."
    )
    p.add_argument("candidate", type=Path, nargs="+")
    for path in p.parse_args().candidate:
        doc = json.loads(path.read_text())
        side = Fraction(doc["side"])
        verify(side, [tuple(map(Fraction, tile)) for tile in doc["squares"]])
        with localcontext() as ctx:
            ctx.prec = 60
            decimal = Decimal(side.numerator) / Decimal(side.denominator)
            delta = decimal - (7 + Decimal(7).sqrt()) / 2
            print(path, "side", str(decimal), "delta", str(delta), "below", below(side))
