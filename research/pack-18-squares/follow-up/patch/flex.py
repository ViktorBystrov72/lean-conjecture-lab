"""Search for second-order inward flexes of exact square-packing realizations.

The LP results propose paths. Only the independent rational geometry test
can certify that an actual finite displacement beats the containing side.
"""

import argparse
import csv
import json
import math
import sys

import numpy as np
from scipy.optimize import linprog
from scipy.linalg import null_space

from run import ROOT, STUDY, TARGET, search, exact

sys.path.insert(0, str(STUDY))
import contact_stress as stress


def layout_path(layout):
    path = STUDY / "layouts" / (layout + "-exact.json")
    return path if path.exists() else ROOT / (layout + "-exact.json")


def setup(layout):
    data = json.loads(layout_path(layout).read_text())
    field_side, tiles = stress.get_geometry(data)
    labels, rows = stress.constraints(field_side, tiles)
    A = np.array([[float(x) for x in r[:-1]] for r in rows])
    fixed = []
    for i in range(len(labels)):
        res = linprog(-A[i], A_ub=-A, b_ub=np.zeros(len(A)), bounds=(-1, 1), method="highs")
        if res.success and res.fun > -1e-8:
            fixed.append(i)
    space = null_space(A[fixed], rcond=1e-9)
    # A basis for the equalities improves conditioning and removes degeneracy.
    reduced = A @ space
    pin = np.eye(54) @ space
    inequality = np.vstack((-reduced, pin, -pin))
    rhs = np.r_[np.zeros(len(A)), np.ones(108)]
    q = []
    for f in data["frames"]:
        x, y, c, s = [float(stress.field(f[key])) for key in ("x", "y", "c", "s")]
        q.extend([x - TARGET / 2, y - TARGET / 2, math.atan2(s, c)])
    return np.array(q + [TARGET]), space, inequality, rhs, len(fixed)


def first_order(base, space, ineq, rhs, rng):
    obj = rng.standard_normal(54)
    if rng.random() < 0.55:
        obj[2:54:3] *= 6
    a = ineq.copy()
    b = rhs.copy()
    for _ in range(6):
        res = linprog(-(obj @ space), A_ub=a, b_ub=b, bounds=(None, None), method="highs")
        if not res.success:
            return None
        v = np.r_[space @ res.x, 0.0]
        if np.max(abs(v)) < 0.025:
            return None
        h = 3e-5
        xv = base + h * v
        g = search.gaps(xv)
        bad = np.flatnonzero(g < -h * 0.001)
        if not len(bad):
            return v
        j = search.gaps(xv, True)[bad, :-1] @ space
        a = np.vstack((a, -j))
        b = np.r_[b, np.zeros(len(bad))]
    return None


def quadratic_patch(base, v, active, h, limit):
    # Include all contacts, also the initially nonbinding ones when they come
    # close at this step. A velocity straight into a face is thereby rejected.
    xh = base + h * v
    g = search.gaps(xh)
    ids = np.union1d(active, np.flatnonzero(g < 0.005))
    J = search.gaps(xh, True)[ids]
    slack = g[ids] / (h * h)
    c = np.zeros(55)
    c[-1] = 1.0
    result = linprog(
        c, A_ub=-J, b_ub=slack, bounds=[(-limit, limit)] * 54 + [(-5, 5)], method="highs"
    )
    if not result.success:
        return np.zeros(55), None
    ds = result.x[-1]
    # Choose the smallest correction in sup norm at the predicted compression.
    B = np.zeros((len(ids) + 108, 56))
    B[: len(ids), :55] = -J
    B[len(ids) : len(ids) + 54, :54] = np.eye(54)
    B[len(ids) + 54 :, :54] = -np.eye(54)
    B[len(ids) :, -1] = -1
    c2 = np.zeros(56)
    c2[-1] = 1.0
    smooth = linprog(
        c2,
        A_ub=B,
        b_ub=np.r_[slack, np.zeros(108)],
        bounds=[(-limit, limit)] * 54 + [(ds, min(5, ds + 2e-9)), (0, limit)],
        method="highs",
    )
    return (smooth.x[:55] if smooth.success else result.x), ds


def pose_document(x):
    p = x[:-1].reshape(18, 3).copy()
    p[:, :2] += x[-1] / 2
    return dict(side=float(x[-1]), squares=p.tolist())


def run(layouts, args):
    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.seed)
    total = []
    best = None
    with (out / "trials.csv").open("w") as csvf:
        wr = csv.writer(csvf)
        wr.writerow(
            [
                "layout",
                "index",
                "h",
                "quadratic_prediction",
                "raw_exact_min_side",
                "released_exact_side",
            ]
        )
        for name in layouts:
            base, space, ineq, rhs, tight = setup(name)
            init_active = np.flatnonzero(search.gaps(base) < 2e-8)
            accepted = 0
            valid_lps = 0
            predictions = 0
            exact_checks = 0
            strongest = 0.0
            prev = []
            for i in range(args.per_layout):
                v = first_order(base, space, ineq, rhs, rng)
                if v is None:
                    continue
                if prev and rng.random() < 0.6:
                    mix = rng.uniform(0.1, 0.85)
                    v = (1 - mix) * v + mix * prev[rng.integers(len(prev))]
                if len(prev) < 90:
                    prev.append(v)
                else:
                    prev[rng.integers(len(prev))] = v
                accepted += 1
                h = rng.choice([0.0003, 0.001, 0.003, 0.015, 0.04, 0.10])
                accel, ds = quadratic_patch(base, v, init_active, h, rng.choice([1.5, 5.0, 20.0]))
                if ds is not None:
                    valid_lps += 1
                    strongest = min(strongest, ds)
                    predictions += int(ds < -1e-7)
                raw_min = None
                for dt in (h, h / 4, min(0.4, 4 * h)):
                    trial = base + v * dt + accel * (dt * dt)
                    pos = pose_document(trial)
                    side, plac = exact.repair(pos["squares"])
                    exact_checks += 1
                    if raw_min is None or side < raw_min:
                        raw_min = side
                    if best is None or side < best:
                        exact.verify(side, plac)
                        best = side
                        store(out, pos, side, plac, name, i, float(dt), "taylor")
                    if exact.below(side):
                        raise SystemExit("EXACT IMPROVEMENT")
                # Advance far enough to perturb the contact pattern, then
                # release all tiles and carry out unrestricted area optimization.
                dt = rng.uniform(0.05, 0.45)
                jump = base + dt * v + min(dt, 0.17) ** 2 * accel
                for weight, nsteps in ((8.0, 100), (100.0, 150), (1700.0, 110)):
                    search._lib.polish(search.ptr(jump), weight, 0, nsteps)
                polished = search.slsqp(jump, 0)
                pos = pose_document(polished)
                side, plac = exact.repair(pos["squares"])
                exact_checks += 1
                wr.writerow([name, i, float(h), ds, float(raw_min), float(side)])
                if best is None or side < best:
                    exact.verify(side, plac)
                    best = side
                    store(out, pos, side, plac, name, i, float(dt), "release")
                if exact.below(side):
                    raise SystemExit("EXACT IMPROVEMENT")
                if (i + 1) % 60 == 0:
                    csvf.flush()
            total.append(
                dict(
                    layout=name,
                    attempts=args.per_layout,
                    first_order_paths=accepted,
                    forced_rows_numerical=tight,
                    tangent_hull_dimension_numerical=space.shape[1],
                    traced_accelerations=valid_lps,
                    predicted_below_minus_1e_neg7=predictions,
                    min_predicted_side_acceleration=float(strongest),
                    exact_sides_compared=exact_checks,
                )
            )
            print(json.dumps(total[-1]), flush=True)
    report = dict(
        seed=args.seed, layouts=total, best_rational=str(best), strict_improvement=exact.below(best)
    )
    search.atomic_write(out / "summary.json", report)


def store(out, pos, side, placed, name, i, dt, kind):
    search.atomic_write(out / "best.json", pos)
    search.atomic_write(
        out / "best-rational.json",
        dict(
            side=str(side),
            squares=[[str(v) for v in row] for row in placed],
            source=name,
            index=i,
            displacement=dt,
            method=kind,
            below=exact.below(side),
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--layouts", nargs="+", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--per-layout", type=int, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    run(args.layouts, args)
