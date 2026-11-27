"""Reproduce the independent orbit inventory, interval rack and 19/4 kernel replay."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "terminal-audit" / "case_audit.cpp"
SCHEDULE = (25, 42, 64)
ROUND_CAP = 75


def orbits():
    def images(x, y):
        return ((x, y), (2000-x, y), (x, 2000-y), (2000-x, 2000-y),
                (y, x), (2000-y, x), (y, 2000-x), (2000-y, 2000-x))

    generators = ((390, 390), (617, 617), (797, 359), (1000, 716), (1000, 1000))
    points = sorted({q for p in generators for q in images(*p)})
    if len(points) != 21:
        raise ValueError("Unexpected mark count")
    actions = [[points.index(images(*p)[g]) for p in points] for g in range(8)]
    remaining = set(combinations(range(21), 3))
    cases = []
    while remaining:
        triple = next(iter(remaining))
        orbit = {tuple(sorted(g[i] for i in triple)) for g in actions}
        if not orbit <= remaining:
            raise ValueError("Invalid orbit partition")
        remaining.difference_update(orbit)
        rep = min(orbit)
        mask = sum(1 << i for i in range(21) if i not in rep)
        cases.append((mask, len(orbit)))
    if len(cases) != 187 or sum(n for _, n in cases) != 1330:
        raise ValueError("Incomplete orbit inventory")
    return sorted(cases)


def check_reason(reason, mask):
    match = re.fullmatch(r"(empty owner [0-9]+|guaranteed overlap [0-9]+ [0-9]+) round ([0-9]+)", reason)
    if not match or int(match[2]) >= ROUND_CAP:
        raise ValueError(f"Invalid exclusion: {reason}")
    labels = list(map(int, re.findall(r"[0-9]+", match[1])))
    if len(set(labels)) != len(labels) or not all(0 <= i < 21 and (mask >> i) & 1 for i in labels):
        raise ValueError("Exclusion cites an absent or repeated owner")


def check_receipt(receipt, cases):
    rows = receipt["full_187_closures_in_order__mask_weight_band_verdict"]
    if len(rows) != len(cases):
        raise ValueError("Incorrect number of recorded closures")
    for (mask, size), (hex_mask, weight, bands, verdict) in zip(cases, rows):
        if (int(hex_mask, 16), weight) != (mask, size) or bands not in SCHEDULE:
            raise ValueError("Mismatch between receipt and independent orbit list")
        check_reason(verdict, mask)
    counts = {str(k): v for k, v in Counter(r[2] for r in rows).items()}
    if counts != receipt["first_exclusions_by_band"]:
        raise ValueError("Band count mismatch")
    print("Recorded closures account for all 187 orbits and 1,330 raw triples.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--verify-receipt", action="store_true", help="check the inventory only")
    parser.add_argument("--case", type=int, help="replay only this zero-based case")
    opts = parser.parse_args()
    if opts.jobs < 1 or opts.case is not None and not 0 <= opts.case < 187:
        parser.error("invalid job count or case number")
    receipt = json.loads((HERE / "receipt.json").read_text())
    cases = orbits()
    check_receipt(receipt, cases)
    if opts.verify_receipt:
        return
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    print("Geometric kernel SHA-256:", digest, flush=True)
    if digest != receipt["kernel_sha256"]:
        print("The current geometric kernel differs from the source used for the receipt.", flush=True)
    with TemporaryDirectory(prefix="pack18-review-") as tmp:
        out = Path(tmp)
        cc = shlex.split(os.environ.get("CXX", "c++"))
        for source, binary in ((SOURCE, "geometry"), (HERE / "rack_interval.cpp", "rack")):
            subprocess.run([*cc, "-std=c++17", "-O3", "-ffp-contract=off", str(source), "-o", str(out / binary)], check=True)
        rack = subprocess.run([out / "rack", "257"], check=True, text=True, capture_output=True)
        if not rack.stdout.startswith("Strict rack covering"):
            raise ValueError("Rack coverage was not verified")
        print(rack.stdout.strip(), flush=True)

        pending = list(range(187)) if opts.case is None else [opts.case]
        closed = set()
        for bands in SCHEDULE:
            def run(case):
                mask = cases[case][0]
                proc = subprocess.run([out / "geometry", "--side", "4750000000", format(mask, "x"),
                                       str(bands), str(ROUND_CAP)], check=True, capture_output=True, text=True)
                last = proc.stdout.splitlines()[-1]
                if last.startswith("EXCLUDED "):
                    check_reason(last[len("EXCLUDED "):], mask)
                    return case
                if last not in ("INCONCLUSIVE budget", "INCONCLUSIVE fixed point"):
                    raise ValueError(f"Unknown output {last}")
                return None
            with ThreadPoolExecutor(max_workers=opts.jobs) as executor:
                at_band = {i for i in executor.map(run, pending) if i is not None}
            closed.update(at_band)
            pending = [i for i in pending if i not in at_band]
            print(f"B={bands}: {len(at_band)} closed, {len(pending)} remaining.", flush=True)
            if not pending:
                break
        if pending:
            raise SystemExit(f"Inconclusive: {pending}")
        weight = sum(cases[i][1] for i in closed)
        print(f"Closed {len(closed)} orbits representing {weight} omitted-mark triples.", flush=True)


if __name__ == "__main__":
    main()
