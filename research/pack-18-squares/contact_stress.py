"""Look for an exact first-order obstruction at a specified Q(sqrt(7)) layout.

The original six-tilt18.json format gives centres as [rational, rational]
field coefficients. Only the LP support search uses floating point.
"""

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from math import sqrt
from pathlib import Path


@dataclass(frozen=True)
class Q:
    a: Fraction = Fraction(0)
    b: Fraction = Fraction(0)

    def __add__(self, x):
        if not isinstance(x, Q):
            x = Q(x)
        return Q(self.a+x.a, self.b+x.b)

    __radd__ = __add__

    def __neg__(self):
        return Q(-self.a, -self.b)

    def __sub__(self, x):
        return self + (-x)

    def __mul__(self, x):
        if not isinstance(x, Q):
            x = Q(x)
        return Q(self.a*x.a + 7*self.b*x.b, self.a*x.b + self.b*x.a)

    __rmul__ = __mul__

    def __truediv__(self, x):
        if not isinstance(x, Q):
            x = Q(x)
        norm = x.a*x.a - 7*x.b*x.b
        if not norm:
            raise ZeroDivisionError
        return self * Q(Fraction(x.a, norm), Fraction(-x.b, norm))

    def sign(self):
        if not self.b or self.a*self.b >= 0:
            v = self.a if self.a else self.b
        else:
            v = (self.a*self.a - 7*self.b*self.b) * self.a
        return (v > 0) - (v < 0)

    def __lt__(self, x):
        return (self-x).sign() < 0

    def __float__(self):
        return float(self.a) + sqrt(7)*float(self.b)

    def json(self):
        return [str(self.a), str(self.b)]


Z, U = Q(), Q(1)


def dot(p, q):
    return p[0]*q[0] + p[1]*q[1]


def add(p, q):
    return (p[0]+q[0], p[1]+q[1])


def scale(f, p):
    return (f*p[0], f*p[1])


def turn(p):
    return (-p[1], p[0])


def field(pair):
    return Q(Fraction(pair[0]), Fraction(pair[1]))


def get_geometry(data):
    side = field(data["side"])
    if "frames" in data:
        frames = [(v["id"], (field(v["x"]), field(v["y"])), (field(v["c"]), field(v["s"])))
                  for v in data["frames"]]
    else:
        frames = []
        for label, tilt, x, y in data["centers"]:
            if tilt not in (0, 1):
                raise ValueError("Unknown frame")
            axis = (Q(1, 1)/4, Q(-1, 1)/4) if tilt else (U, Z)
            frames.append((label, (field(x), field(y)), axis))
    if len({label for label, _, _ in frames}) != len(frames):
        raise ValueError("Tile labels must be distinct")
    tiles = []
    for label, center, u in frames:
        if dot(u, u) != U:
            raise ValueError(f"Non-unit frame at tile {label}")
        v = turn(u)
        vertices = [add(center, scale(Q(Fraction(1, 2)), add(scale(a, u), scale(b, v))))
                    for a, b in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        if any(coord < Z or side < coord for vertex in vertices for coord in vertex):
            raise ValueError(f"Wall violation at tile {label}")
        tiles.append((label, center, vertices))
    for i, (label, _, vs) in enumerate(tiles):
        for label2, _, ws in tiles[i+1:]:
            normals = [turn(add(q[(k+1) % 4], scale(-1, q[k]))) for q in (vs, ws) for k in range(2)]
            for normal in normals:
                aa = [dot(normal, p) for p in vs]
                bb = [dot(normal, p) for p in ws]
                if not min(bb) < max(aa) or not min(aa) < max(bb):
                    break
            else:
                raise ValueError(f"Overlap between tiles {label} and {label2}")
    return side, tiles


def constraints(side, tiles):
    dim = 3*len(tiles) + 1
    labels, rows = [], []

    def row():
        return [Z] * dim

    def push(tag, values):
        labels.append(tag)
        rows.append(values)

    def add_velocity(values, i, p, n):
        center = tiles[i][1]
        angular = dot(n, turn(add(p, scale(-1, center))))
        for k, coefficient in enumerate((*n, angular)):
            values[3*i+k] = values[3*i+k] + coefficient

    for i, (tag, _, vertices) in enumerate(tiles):
        for k, p in enumerate(vertices):
            for axis, n in enumerate(((U, Z), (Z, U))):
                if p[axis] == Z:
                    a = row()
                    add_velocity(a, i, p, n)
                    push(f"min{axis}:{tag}.{k}", a)
                if p[axis] == side:
                    a = row()
                    add_velocity(a, i, p, scale(-1, n))
                    a[-1] = U
                    push(f"max{axis}:{tag}.{k}", a)

    # A vertex in the open part of the other tile's face has a unique
    # separating normal. Positive-length shared faces also constrain each
    # endpoint by continuity from their relative interior. Corner-only
    # contacts with two possible separating axes are deliberately omitted.
    for i, (itag, _, vv) in enumerate(tiles):
        for k, p in enumerate(vv):
            q = vv[(k+1) % 4]
            tangent = add(q, scale(-1, p))
            n = scale(-1, turn(tangent))
            for j, (jtag, _, other) in enumerate(tiles):
                if i == j:
                    continue
                gaps = [dot(n, add(v, scale(-1, p))) for v in other]
                if min(gaps) != Z:
                    continue
                along = [dot(tangent, add(v, scale(-1, p))) for v, gap in zip(other, gaps) if gap == Z]
                lo, hi = max(Z, min(along)), min(U, max(along))
                if hi < lo or (lo == hi and not Z < lo < U):
                    continue
                for part, t in enumerate(dict.fromkeys((lo, hi))):
                    v = add(p, scale(t, tangent))
                    a = row()
                    add_velocity(a, i, v, scale(-1, n))
                    add_velocity(a, j, v, n)
                    push(f"face:{itag}.{k}:{jtag}:{part}", a)
    return labels, rows


def solve_exact(rows, selected):
    # The selected indices are a proposed sparse dual basis. Solve A^T y
    # = e_side in the quadratic field and then verify it in every column.
    m = len(selected)
    dim = len(rows[0])
    equations = [[rows[i][k] for i in selected] + [U if k == dim-1 else Z] for k in range(dim)]
    pivots = []
    for col in range(m):
        pivot = next((j for j in range(len(pivots), dim) if equations[j][col] != Z), None)
        if pivot is None:
            continue
        rank = len(pivots)
        equations[rank], equations[pivot] = equations[pivot], equations[rank]
        v = equations[rank][col]
        equations[rank] = [x/v for x in equations[rank]]
        for j in range(dim):
            if j != rank and equations[j][col] != Z:
                f = equations[j][col]
                equations[j] = [x - f*y for x, y in zip(equations[j], equations[rank])]
        pivots.append(col)
    weights = [Z]*m
    for j, col in enumerate(pivots):
        weights[col] = equations[j][-1]
    if any(y < Z for y in weights) or any(
        sum((y*rows[i][k] for y, i in zip(weights, selected)), Z) != (U if k == dim-1 else Z)
        for k in range(dim)
    ):
        raise ValueError("The proposed dual basis failed exact verification")
    return weights


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--write", type=Path)
    parser.add_argument("--check", type=Path, help="verify a saved stress without SciPy")
    args = parser.parse_args()
    side, tiles = get_geometry(json.loads(args.layout.read_text()))
    if len(tiles) != 18 or side != Q(Fraction(7, 2), Fraction(1, 2)):
        raise ValueError("Expected a record-side 18-tile layout")
    labels, rows = constraints(side, tiles)
    if args.check:
        stress = json.loads(args.check.read_text())
        selected = [labels.index(k) for k in stress]
        weights = [field(v) for v in stress.values()]
        if any(w < Z for w in weights) or any(
            sum((w*rows[i][k] for i, w in zip(selected, weights)), Z) != (U if k == len(rows[0])-1 else Z)
            for k in range(len(rows[0]))
        ):
            raise ValueError("Invalid stress")
    else:
        import numpy as np
        from scipy.optimize import linprog
        a = np.array([[float(x) for x in row] for row in rows])
        rhs = np.zeros(a.shape[1])
        rhs[-1] = 1
        result = linprog(np.ones(len(rows)), A_eq=a.T, b_eq=rhs, bounds=(0, None), method="highs")
        if not result.success:
            raise ValueError(result.message)
        selected = [i for i, x in enumerate(result.x) if x > 1e-9]
        weights = solve_exact(rows, selected)
    if args.write:
        args.write.write_text(json.dumps({labels[i]: y.json() for i, y in zip(selected, weights)}, indent=2) + "\n")
    print(f"Verified {len(selected)} nonnegative contact weights across {len(rows[0])} velocity coordinates.")


if __name__ == "__main__":
    main()
