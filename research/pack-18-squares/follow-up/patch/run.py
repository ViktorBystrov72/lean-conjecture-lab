"""Cavity removal, constrained reinsertion, grouped rotations and global relaxation."""

import argparse
import csv
import ctypes
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
ROOT = Path(os.environ["PACK18_RUN"])
PREVIOUS = STUDY / "search-history"
sys.path.insert(0, str(PREVIOUS))
import search
import exact

patch = ctypes.CDLL(str(ROOT / "patch.dylib")).patch_repack
patch.argtypes = [search.PTR, ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_double]
patch.restype = ctypes.c_uint
splice = ctypes.CDLL(str(ROOT / "patch.dylib")).patch_splice
splice.argtypes = [
    search.PTR,
    search.PTR,
    ctypes.c_uint64,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_double,
]
splice.restype = ctypes.c_uint
TARGET = (7 + math.sqrt(7)) / 2


def grouped_polish(x):
    """Optimize common rotations within nearly parallel clusters as smooth variables."""
    raw = x[:-1].reshape(18, 3)
    angles = (raw[:, 2] + np.pi / 4) % (np.pi / 2) - np.pi / 4
    distinct = []
    assignment = np.zeros(18, dtype=int)
    for i in np.argsort(abs(angles)):
        a = angles[i]
        if abs(a) < 0.012:
            assignment[i] = -1
            continue
        nearest = min(range(len(distinct)), key=lambda k: abs(a - distinct[k]), default=None)
        if nearest is None or abs(a - distinct[nearest]) > 0.025:
            nearest = len(distinct)
            distinct.append(a)
        assignment[i] = nearest

    z = np.r_[raw[:, :2].ravel(), distinct, x[-1]]
    # This affine parameterization also supplies the exact chain rule.
    matrix = np.zeros((55, len(z)))
    for i, group in enumerate(assignment):
        matrix[3 * i, 2 * i] = 1
        matrix[3 * i + 1, 2 * i + 1] = 1
        if group >= 0:
            matrix[3 * i + 2, 36 + group] = 1
    matrix[-1, -1] = 1
    active = np.flatnonzero(search.gaps(matrix @ z) < 0.55)
    jac_obj = matrix[-1]
    result = minimize(
        lambda v: v[-1],
        z,
        jac=lambda v: jac_obj,
        method="SLSQP",
        constraints={
            "type": "ineq",
            "fun": lambda v: search.gaps(matrix @ v)[active],
            "jac": lambda v: search.gaps(matrix @ v, True)[active] @ matrix,
        },
        options={"maxiter": 70, "ftol": 1e-12},
    )
    return matrix @ result.x


def fingerprint(x):
    gaps = search.gaps(x)
    wall_count = (gaps[:36].reshape(18, 2) < 0.012).sum(axis=1)
    pair_count = np.zeros(18, dtype=np.int32)
    k = 36
    for i in range(1, 18):
        for j in range(i):
            if gaps[k] < 0.012:
                pair_count[i] += 1
                pair_count[j] += 1
            k += 1
    bins = np.minimum(
        8, np.rint(abs((x[2:54:3] + np.pi / 4) % (np.pi / 2) - np.pi / 4) / 0.10).astype(int)
    )
    return tuple(sorted(zip(wall_count.tolist(), pair_count.tolist(), bins.tolist())))


def run(args):
    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    seed_files = sorted(
        [*(PREVIOUS / "seeds").glob("*.json"), ROOT / "mira-six-tilt.json"], key=lambda p: p.name
    )
    seeds = [search.load(path) for path in seed_files]
    rng = np.random.default_rng(args.seed)
    archive = {}
    current = seeds[0]
    best = None
    best_exact = None
    near_count = 0
    began = time.perf_counter()
    grouped_calls = 0
    local_polish_calls = 0
    counts_by_size = {}
    subtargets = (TARGET - 5e-7, TARGET - 0.002, TARGET - 0.012, TARGET - 0.045)
    with (out / "runs.csv").open("w") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "index",
                "source",
                "key",
                "patch_size",
                "patch_mode",
                "tile_mask",
                "target_side",
                "angle_locks",
                "raw_penalty_side",
                "repaired_side",
                "grouped_check",
            ]
        )
        for idx in range(args.iterations):
            choose = rng.random()
            if idx < 5 or choose < 0.20:
                src = "reference"
                base = seeds[idx % 5 if idx < 5 else rng.integers(len(seeds))]
            elif choose < 0.66 and archive:
                src = "archive"
                candidates = list(archive.values())
                shortlist = [candidates[rng.integers(len(candidates))] for _ in range(4)]
                base = min(shortlist, key=lambda y: y[-1] + rng.exponential(0.028))
            else:
                src = "walk"
                base = current
            x = base.copy()
            key = int(rng.integers(0, 2**63 - 1, dtype=np.int64))
            size = int(rng.integers(4, 10))
            mode = int(rng.integers(4))
            target = subtargets[rng.integers(len(subtargets))]
            if args.splice:
                if archive and rng.random() < 0.6:
                    donor = list(archive.values())[rng.integers(len(archive))]
                else:
                    donor = seeds[rng.integers(len(seeds))]
                free = int(splice(search.ptr(x), search.ptr(donor), key, size, mode, target))
            else:
                free = int(patch(search.ptr(x), key, size, mode, target))
            angles = x[2:54:3]
            angles[:] = (angles + np.pi / 4) % (np.pi / 2) - np.pi / 4
            keep = rng.random()
            locked = 0
            for j in range(18):
                if not ((free >> j) & 1) and abs(angles[j]) < 0.015 and rng.random() < keep:
                    angles[j] = 0
                    locked |= 1 << j
            for weight, steps in ((2, 100), (22, 170), (220, 140), (2500, 140)):
                search._lib.polish(search.ptr(x), weight, locked, steps)
            value = search.feasible_rescale(x)
            grouped = 0
            if value[-1] < TARGET + 0.025 or (idx % 24 == 0 and value[-1] < 4.97):
                q = search.slsqp(x, locked)
                local_polish_calls += 1
                qq = search.feasible_rescale(q)
                if qq[-1] < value[-1]:
                    value = qq
                if idx % 3 == 0 or qq[-1] < TARGET + 1e-5:
                    grouped = 1
                    grouped_calls += 1
                    gg = search.feasible_rescale(grouped_polish(value))
                    if gg[-1] < value[-1]:
                        value = gg
            val = float(value[-1])
            counts_by_size[size] = counts_by_size.get(size, 0) + 1
            writer.writerow(
                [
                    idx,
                    src,
                    key,
                    size,
                    mode,
                    free,
                    repr(target),
                    locked.bit_count(),
                    format(x[-1], ".16g"),
                    format(val, ".16g"),
                    grouped,
                ]
            )
            if best is None or val < best[-1]:
                best = value.copy()
                search.atomic_write(out / "best.json", search.doc(best))
                search.atomic_write(
                    out / "best_provenance.json",
                    dict(index=idx, seed=args.seed, key=key, side=val, method=mode, patch=size),
                )
            if args.screen and val < TARGET + 1e-9:
                near_count += 1
                pos = search.doc(value)
                for lim in (10**8, 10**13):
                    side, placed = exact.repair(pos["squares"], slope_limit=lim)
                    if best_exact is None or side < best_exact:
                        exact.verify(side, placed)
                        best_exact = side
                        info = dict(
                            side=str(side),
                            squares=[[str(v) for v in tile] for tile in placed],
                            seed=args.seed,
                            index=idx,
                            slope_limit=lim,
                            below=exact.below(side),
                        )
                        search.atomic_write(out / "best-rational.json", info)
                        search.atomic_write(out / "best-exact-source.json", pos)
                        if exact.below(side):
                            print("EXACT IMPROVEMENT", idx, str(side), flush=True)
                            return info
            if val < TARGET - 2e-13:
                search.atomic_write(out / f"possible-{idx}.json", search.doc(value))
                print("POSSIBLE STRICT IMPROVEMENT", idx, val, flush=True)
            if val < 5.01:
                profile = fingerprint(value)
                if profile not in archive or archive[profile][-1] > val:
                    archive[profile] = value.copy()
                if len(archive) > 330:
                    # Preserve some nonrecord minima; they may lead to new contact patterns.
                    keys = list(archive)
                    del archive[keys[rng.integers(len(keys))]]
                if val < current[-1] + rng.exponential(0.035):
                    current = value.copy()
            elif rng.random() < 0.12:
                current = seeds[rng.integers(len(seeds))]
            if (idx + 1) % 100 == 0:
                fh.flush()
                print(idx + 1, format(best[-1], ".16g"), "profiles", len(archive), flush=True)
    summary = dict(
        seed=args.seed,
        starts=args.iterations,
        best=float(best[-1]),
        target=TARGET,
        archive_size=len(archive),
        counts_by_size=counts_by_size,
        grouped_polishes=grouped_calls,
        individual_angle_polishes=local_polish_calls,
        seconds=time.perf_counter() - began,
        seed_files=[p.name for p in seed_files],
        splice=args.splice,
        near_candidates_screened=near_count,
        best_rational_side=str(best_exact),
    )
    search.atomic_write(out / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--splice", action="store_true")
    parser.add_argument("--screen", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args)), flush=True)
