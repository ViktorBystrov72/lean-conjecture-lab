"""Try one completely free tile after sampling alternative exact 17-tile layouts."""

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
from random import Random

from free_tile import LENGTH, Q, check_fixed, search


def compatible(p, q):
    x, y, a, b, c = p
    X, Y, A, B, C = q
    dx, dy = x-X, y-Y
    support = 10**7 * (c*C + abs(a*A+b*B) + abs(a*B-b*A))
    return (2*C*max(abs(dx*a+dy*b), abs(dy*a-dx*b)) >= support or
            2*c*max(abs(dx*A+dy*B), abs(dy*A-dx*B)) >= support)


def read_rows(path):
    return [tuple(map(int, line.split())) for line in path.read_text().splitlines()]


def choices(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def generate(pool, reference, count, seed):
    rng = Random(seed)
    index = {pose: i for i, pose in enumerate(pool)}
    first = tuple(sorted(index[p] for p in reference))
    layouts = [first]
    keys = {first}
    all_poses = (1 << len(pool))-1

    @lru_cache(maxsize=None)
    def neighbors(i):
        bits = bytearray((len(pool)+7)//8)
        for j, pose in enumerate(pool):
            if compatible(pool[i], pose):
                bits[j//8] |= 1 << (j % 8)
        return int.from_bytes(bits, "little")

    current = first
    for trial in range(200*count):
        if len(layouts) >= count:
            break
        if trial % 25 == 0:
            current = rng.choice(layouts)
        k = rng.choice((2, 3, 4, 5, 6, 7))
        keep = rng.sample(current, 17-k)
        available = all_poses
        for i in keep:
            available &= neighbors(i)
        for _ in range(10):
            selection = list(keep)
            possible = available
            while len(selection) < 17 and possible:
                i = rng.choice(list(choices(possible)))
                selection.append(i)
                possible &= neighbors(i)
            if len(selection) != 17:
                continue
            proposed = tuple(sorted(selection))
            if proposed in keys or len(set(proposed).difference(current)) < 2:
                continue
            keys.add(proposed)
            layouts.append(proposed)
            current = proposed
            break
    return layouts


def run_one(task):
    path, budget, depth, motion = task
    result = search(check_fixed(path, LENGTH), LENGTH, budget, depth, motion)
    result["witness"] = path.name
    return result


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--seed", type=int, default=183271)
    parser.add_argument("--samples", type=Path, help="reuse a saved list of 17-pose index sets")
    parser.add_argument("--write-samples", type=Path, help="save the selected index sets")
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--depth", type=int, default=75)
    parser.add_argument("--motion", type=Q, default=Q(0))
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.count < 1 or args.workers < 1 or args.limit < 1 or args.depth < 0 or not 0 <= args.motion < Q(1,4):
        parser.error("invalid search budget or motion")
    pool_file = here.parent / "finite/poses.txt"
    pool = read_rows(pool_file)
    reference = read_rows(here.parent / "finite/witness-17.txt")
    pool_hash = hashlib.sha256(pool_file.read_bytes()).hexdigest()
    if args.samples:
        saved = json.loads(args.samples.read_text())
        if saved["pool_sha256"] != pool_hash:
            raise ValueError("Sample indices belong to a different pool")
        layouts = saved["layouts"]
        for row in layouts:
            if len(row) != 17 or len(set(row)) != 17 or any(type(i) is not int or not 0 <= i < len(pool) for i in row):
                raise ValueError("Bad 17-pose selection")
    else:
        layouts = generate(pool, reference, args.count, args.seed)
    if args.write_samples:
        args.write_samples.write_text(json.dumps({"pool_sha256":pool_hash,"layouts":layouts})+"\n")
    args.output.mkdir(parents=True, exist_ok=True)
    tasks = []
    for n, layout in enumerate(layouts):
        path = args.output / f"layout-{n:03d}.txt"
        path.write_text("".join(" ".join(map(str,pool[i]))+"\n" for i in layout))
        tasks.append((path, args.limit, args.depth, args.motion))
    counts = {}
    with ProcessPoolExecutor(max_workers=args.workers) as workers, (args.output / "results.jsonl").open("w") as out:
        for result in workers.map(run_one, tasks):
            status = result["status"]
            counts[status] = counts.get(status,0)+1
            out.write(json.dumps(result)+"\n")
            out.flush()
            if status == "found":
                print(result,flush=True)
    report = {"layouts":len(layouts),"side":str(LENGTH),"motion":str(args.motion),
              "limit_per_layout":args.limit,"depth":args.depth,"outcomes":counts,
              "pool_sha256":pool_hash}
    if not args.samples:
        report["seed"] = args.seed
    (args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
