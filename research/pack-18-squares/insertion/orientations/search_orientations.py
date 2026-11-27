"""Hole-seeded rotation search with a fixed-centre phase and a free-centre phase."""

import argparse
import csv
import ctypes
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
sys.path.insert(0, str(STUDY / "search-history"))
sys.path.insert(0, str(STUDY / "follow-up" / "patch"))
import search
import exact

LIB = ctypes.CDLL(str(Path(os.environ["PACK18_RUN"]) / "rounded.dylib"))
energy = LIB.energy
energy.argtypes = [search.PTR, ctypes.c_double, ctypes.c_double, search.PTR]
energy.restype = ctypes.c_double
TARGET = (7 + math.sqrt(7)) / 2
MEANINGFUL_PENETRATION = 1e-10


def relax(q, pinned, side, anchor, rho, stages):
    original = q.copy()
    indices = np.arange(54)
    free = indices[(indices % 3 == 2) | (indices >= 51)] if pinned else indices
    last_energy = None
    for alpha, steps in stages:

        def obj(z):
            arr = original.copy()
            arr[free] = z
            gradient = np.empty(54)
            cost = energy(search.ptr(arr), alpha, side, search.ptr(gradient))
            if rho:
                difference = arr[:51].reshape(17, 3)[:, :2] - anchor
                cost += rho * np.sum(difference**2)
                gradient[:51].reshape(17, 3)[:, :2] += 2 * rho * difference
            return cost, gradient[free]

        result = minimize(
            obj,
            q[free],
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": steps, "gtol": 1e-10, "ftol": 1e-15, "maxls": 25},
        )
        q[free] = result.x
        last_energy = result.fun
    return q, float(last_energy)


def prepare(seed, canvas):
    tiles = np.array(
        [
            [x / 1e7 - canvas / 2, y / 1e7 - canvas / 2, math.atan2(b, a)]
            for x, y, a, b, _ in seed["fixed"]
        ]
    )
    holes = np.array(
        [
            [float(Fraction(x)) - canvas / 2, float(Fraction(y)) - canvas / 2]
            for x, y in seed["holes"]
        ]
    )
    return tiles, holes


def run(args):
    env = Path(os.environ["PACK18_RUN"])
    seed_data = json.loads((HERE / "seeds.json").read_text())
    side = float(Fraction(seed_data["side"]))
    out = env / args.batch
    out.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.seed)
    summaries = []
    best = None
    start = time.perf_counter()
    with (out / "trials.csv").open("w") as f:
        wr = csv.writer(f)
        wr.writerow(
            [
                "layout",
                "index",
                "hole",
                "mode",
                "pinned_loss",
                "pinned_gap",
                "after_release_side",
                "certified_side_float",
            ]
        )
        for entry in seed_data["layouts"]:
            name = entry["layout"]
            if name not in args.layouts:
                continue
            base, holes = prepare(entry, side)
            ref = base[:, :2]
            count = args.hard if name >= 126 else args.other
            pin_best = float("inf")
            near = 0
            per_min = None
            for i in range(count):
                hi = i % len(holes)
                p = np.vstack([base, [*holes[hi], rng.uniform(-np.pi / 4, np.pi / 4)]])
                mode = (i // len(holes)) % 5
                near_hole = np.linalg.norm(ref - holes[hi], axis=1) < 1.53
                if mode == 1:
                    p[:17, 2] += rng.normal(0, 0.065, 17)
                elif mode == 2:
                    p[:17, 2] = rng.uniform(-np.pi / 4, np.pi / 4, 17)
                elif mode == 3:
                    p[:17, 2][near_hole] += rng.uniform(-0.60, 0.60, sum(near_hole))
                elif mode == 4:
                    p[:17, 2] *= rng.choice([-1.0, 1.0], 17)
                    p[:17, 2] += rng.normal(0, 0.16, 17)
                if i >= len(holes):
                    p[17, :2] += rng.normal(0, rng.uniform(0, 0.065), 2)
                q, pin = relax(
                    p.ravel().copy(),
                    True,
                    side,
                    ref,
                    0,
                    ((0.18, 50), (0.52, 65), (0.84, 70), (1.0, 100)),
                )
                gap = search.gaps(np.r_[q, side]).min()
                pin_best = min(pin_best, pin)
                if gap >= -MEANINGFUL_PENETRATION:
                    # A floating fit at the smaller side deserves an immediate exact check.
                    doc = search.doc(np.r_[q, side])
                    cand, tiles = exact.repair(doc["squares"])
                    if exact.below(cand):
                        exact.verify(cand, tiles)
                        search.atomic_write(out / "possible-pinned.json", doc)
                        raise RuntimeError(f"EXACT PINNED IMPROVEMENT at layout {name}")
                # Drop all constraints on the centres in stages. No centre or
                # angle is held fixed in the final minimization and polish.
                if args.thaw:
                    # Give the jammed cluster temporary room to reorient,
                    # followed by gradual compression in a shrinking box.
                    padding = rng.uniform(0.18, 0.86)
                    q = q.reshape(18, 3).copy()
                    q[:, :2] *= (side + padding) / side
                    hole = q[-1, :2].copy()
                    ids = np.argsort(np.linalg.norm(q[:, :2] - hole, axis=1))[: rng.integers(5, 10)]
                    turn = rng.uniform(-0.58, 0.58)
                    c, s = math.cos(turn), math.sin(turn)
                    q[ids, :2] = (q[ids, :2] - hole) @ np.array([[c, s], [-s, c]]) + hole
                    q[ids, 2] += turn
                    q[ids, :2] += rng.normal(0, 0.12, (len(ids), 2))
                    q[ids, 2] += rng.normal(0, 0.14, len(ids))
                    q = q.ravel()
                    for remaining in (1.0, 0.55, 0.15, 0.0):
                        q, _ = relax(q, False, side + padding * remaining, ref, 0.0, ((1.0, 85),))
                else:
                    for rho in (0.12, 0.008, 0.0):
                        q, _ = relax(q, False, side, ref, rho, ((1.0, 70),))
                y = np.r_[q, side]
                for weight, steps in ((3.0, 90), (40.0, 100), (900.0, 130), (3500.0, 70)):
                    search._lib.polish(search.ptr(y), weight, 0, steps)
                y = search.slsqp(y, 0)
                doc = search.doc(y)
                cand, tiles = exact.repair(doc["squares"])
                near += int(float(cand) < TARGET + 1e-6)
                if per_min is None or cand < per_min:
                    per_min = cand
                if best is None or cand < best:
                    best = cand
                    exact.verify(best, tiles)
                    search.atomic_write(out / "best.json", doc)
                    search.atomic_write(
                        out / "best-rational.json",
                        dict(
                            side=str(best),
                            squares=[[str(v) for v in tile] for tile in tiles],
                            layout=name,
                            index=i,
                            hole=hi,
                            mode=mode,
                            below=exact.below(cand),
                        ),
                    )
                if exact.below(cand):
                    raise RuntimeError(f"EXACT FREE IMPROVEMENT at layout {name}")
                wr.writerow([name, i, hi, mode, pin, gap, y[-1], float(cand)])
            f.flush()
            row = dict(
                layout=name,
                starts=count,
                hole_vertices=len(holes),
                smallest_pinned_overlap_penalty=pin_best,
                best_certified=str(per_min),
                near_target=near,
            )
            summaries.append(row)
            print(json.dumps(row), flush=True)
    search.atomic_write(
        out / "summary.json",
        dict(
            seed=args.seed,
            side=seed_data["side"],
            thaw=args.thaw,
            results=summaries,
            best_certified=str(best),
            elapsed_seconds=time.perf_counter() - start,
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--layouts", type=int, nargs="+", required=True)
    p.add_argument("--batch", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--hard", type=int, default=240)
    p.add_argument("--other", type=int, default=16)
    p.add_argument(
        "--thaw", action="store_true", help="expand, deform the hole cluster, then recompress"
    )
    run(p.parse_args())
