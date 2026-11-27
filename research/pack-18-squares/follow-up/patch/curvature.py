"""Physical contact Taylor jets, a separate search at the known configurations."""

import argparse
import csv
import json
import numpy as np
from scipy.optimize import linprog
from flex import ROOT, setup, layout_path, first_order, stress, search, exact, pose_document, store


def contact_probes(name):
    field_data = json.loads(layout_path(name).read_text())
    side, tiles = stress.get_geometry(field_data)
    labels, rows = stress.constraints(side, tiles)
    A = np.array([[float(x) for x in row] for row in rows])
    index = {a[0]: i for i, a in enumerate(tiles)}
    contacts = []
    for tag in labels:
        ptag, *data = tag.split(":")
        if ptag.startswith("min") or ptag.startswith("max"):
            tile, k = map(int, data[0].split("."))
            i = index[tile]
            center = tiles[i][1]
            p = tiles[i][2][k]
            n = [0.0, 0.0]
            n[int(ptag[-1])] = 1.0 if ptag.startswith("min") else -1.0
            contacts.append(
                (
                    i,
                    -1,
                    np.array([float(p[k] - center[k]) for k in (0, 1)]),
                    np.zeros(2),
                    np.array(n),
                )
            )
        else:
            tile, k = map(int, data[0].split("."))
            i = index[tile]
            j = index[int(data[1])]
            vertices = tiles[i][2]
            p = vertices[k]
            q = vertices[(k + 1) % 4]
            tangent = stress.add(q, stress.scale(-1, p))
            n = stress.scale(-1, stress.turn(tangent))
            other = tiles[j][2]
            along = [
                stress.dot(tangent, stress.add(z, stress.scale(-1, p)))
                for z in other
                if stress.dot(n, stress.add(z, stress.scale(-1, p))) == stress.Z
            ]
            lo, hi = max(stress.Z, min(along)), min(stress.U, max(along))
            fraction = (lo, hi)[int(data[2])]
            point = stress.add(p, stress.scale(fraction, tangent))
            ri = np.array([float(point[k] - tiles[i][1][k]) for k in (0, 1)])
            rj = np.array([float(point[k] - tiles[j][1][k]) for k in (0, 1)])
            contacts.append((i, j, ri, rj, np.array([float(z) for z in n])))
    return A, contacts


def curvature(v, contacts):
    out = []
    tiles = v[:-1].reshape(18, 3)
    for i, j, ri, rj, n in contacts:
        wi = tiles[i, 2]
        if j < 0:
            h = -0.5 * wi**2 * (n @ ri)
        else:
            wj = tiles[j, 2]
            Jn = np.array([-n[1], n[0]])
            relative = (
                tiles[j, :2]
                - tiles[i, :2]
                + wj * np.array([-rj[1], rj[0]])
                - wi * np.array([-ri[1], ri[0]])
            )
            h = 0.5 * (wi * wi * (n @ ri) - wj * wj * (n @ rj)) + wi * (Jn @ relative)
        out.append(h)
    return np.array(out)


def run(args):
    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.seed)
    summaries = []
    best = None
    with (out / "trials.csv").open("w") as fh:
        writer = csv.writer(fh)
        writer.writerow(["layout", "index", "active", "side_accel", "exact_value", "finite_polish"])
        for name in args.layouts:
            base, space, ineq, rhs, _ = setup(name)
            A, contacts = contact_probes(name)
            flexes = success = predictions = checks = 0
            opt_cost = None
            for step in range(args.per_layout):
                v = first_order(base, space, ineq, rhs, rng)
                if v is None:
                    continue
                flexes += 1
                live = A @ v < 4e-8
                c = curvature(v, contacts)
                obj = np.zeros(55)
                obj[-1] = 1
                rate = linprog(
                    obj,
                    A_ub=-A[live],
                    b_ub=c[live],
                    bounds=[(-25, 25)] * 54 + [(-5, 5)],
                    method="highs",
                )
                if not rate.success:
                    continue
                success += 1
                predictions += int(rate.fun < -1e-7)
                opt_cost = rate.fun if opt_cost is None else min(opt_cost, rate.fun)
                # Minimize the magnitude of the patch, retaining the LP side bound.
                M = np.zeros((sum(live) + 108, 56))
                M[: sum(live), :55] = -A[live]
                M[sum(live) : sum(live) + 54, :54] = np.eye(54)
                M[sum(live) + 54 :, :54] = -np.eye(54)
                M[sum(live) :, -1] = -1
                objective = np.zeros(56)
                objective[-1] = 1.0
                fit = linprog(
                    objective,
                    A_ub=M,
                    b_ub=np.r_[c[live], np.zeros(108)],
                    bounds=[(-25, 25)] * 54 + [(rate.fun, min(5, rate.fun + 1e-9)), (0, 25)],
                    method="highs",
                )
                a = fit.x[:55].copy() if fit.success else rate.x.copy()
                # convert side acceleration coefficients from [0,L]^2 coordinates
                # to the centred coordinate system used by the numerical packing
                a[:54:3] -= a[-1] / 2
                a[1:54:3] -= a[-1] / 2
                trial_best = None
                for dt in (0.001, 0.017, 0.105):
                    q = base + dt * v + dt * dt * a
                    pos = pose_document(q)
                    side, coords = exact.repair(pos["squares"])
                    checks += 1
                    if trial_best is None or side < trial_best:
                        trial_best = side
                    if best is None or side < best:
                        exact.verify(side, coords)
                        best = side
                        store(out, pos, side, coords, name, step, dt, "contact-jet")
                    if exact.below(side):
                        raise SystemExit("EXACT IMPROVEMENT")
                dt = rng.uniform(0.05, 0.37)
                q = base + dt * v + min(dt, 0.2) ** 2 * a
                for weight, nsteps in ((7.0, 100), (110.0, 120), (1600.0, 110)):
                    search._lib.polish(search.ptr(q), weight, 0, nsteps)
                pos = pose_document(search.slsqp(q, 0))
                side, coords = exact.repair(pos["squares"])
                checks += 1
                if best is None or side < best:
                    exact.verify(side, coords)
                    best = side
                    store(out, pos, side, coords, name, step, dt, "released-contact-jet")
                if exact.below(side):
                    raise SystemExit("EXACT IMPROVEMENT")
                writer.writerow(
                    [name, step, int(sum(live)), rate.fun, float(trial_best), float(side)]
                )
            summaries.append(
                dict(
                    layout=name,
                    attempts=args.per_layout,
                    first_order_flexes=flexes,
                    contact_lps_feasible=success,
                    inward_lp_predictions=predictions,
                    most_negative_predicted_coefficient=opt_cost,
                    exact_compared=checks,
                )
            )
            print(json.dumps(summaries[-1]), flush=True)
    search.atomic_write(
        out / "summary.json",
        dict(seed=args.seed, layouts=summaries, best=str(best), below=exact.below(best)),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--layouts", nargs="+", required=True)
    p.add_argument("--per-layout", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    run(p.parse_args())
