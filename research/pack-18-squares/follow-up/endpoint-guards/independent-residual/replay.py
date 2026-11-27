"""Independent reconstruction of the 20 'faces' branches in residual classes 82, 92 and 115."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from check_guards import guarded_leaf, owner_map
from residual_replay import jobs, TABLES


def pose_records(path, mask, bands, symmetry, roles):
    rows = {i: {} for i in range(21) if mask >> i & 1}
    for line in path.read_text().splitlines():
        owner, k, b, x, X, y, Y = map(int, line.split())
        if (owner not in rows or b != bands or not 0 <= k < b or k in rows[owner] or
                not 0 <= x <= X <= 2411438000 or not 0 <= y <= Y <= 2411438000):
            raise ValueError("invalid rectangle in verifier output")
        # Exterior rounding from the two-nanounit lattice to guard microunits.
        rows[owner][k] = [k, b, x // 500, -(-X // 500), y // 500, -(-Y // 500)]
    av, ah, bv, bh, f, g = roles
    active = set(av + ah + bv + bh + [f, g])
    perm = owner_map(symmetry)
    return [(owner, list(states.values())) for owner, states in rows.items() if perm[owner] in active]


def replay(checker, directory, row, job):
    case, i, j, cuts, _, symmetry, roles = job
    mask = TABLES[case][0]
    name = f'{case}-{i}.{j}'
    trace = gzip.decompress((HERE / 'certificates' / f'{name}.txt.gz').read_bytes())
    if hashlib.sha256(trace).hexdigest() != row['trace_sha256']:
        raise ValueError(f"invalid certificate for {name}")
    points = directory / (name + '.txt')
    points.write_bytes(trace)
    boxes = directory / (name + '.boxes')
    cmd = [checker, format(mask, 'x'), str(row['bands']), str(row['rounds']),
           'verify', points, '4822876000', *map(str, cuts)]
    run = subprocess.run(cmd, capture_output=True, text=True,
                         env={**os.environ, 'PACK18_OUTER_BOXES': str(boxes)})
    verdict = run.stdout.splitlines()[-1:] or ['']
    if (run.returncode == 0 and
            re.fullmatch(rf'EXCLUDED mask {mask} index (?:[0-9]|1[0-7]) round [0-9]+ [AB]', verdict[0])):
        result = verdict[0]
    elif run.returncode == 1 and verdict == ['UNDECIDED']:
        av, ah, bv, bh, f, g = roles
        records = pose_records(boxes, mask, row['bands'], symmetry, roles)
        result = guarded_leaf(records, symmetry, (tuple(av), tuple(ah)), (tuple(bv), tuple(bh)), (f, g))
    else:
        raise ValueError(f"unexpected geometry outcome for {name}: {verdict}, {run.stderr[-250:]}")
    if result != row['result']:
        raise ValueError(f"certificate diagnostics differ on {name}: {result}")
    return case, result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    # jobs reads the three pinned tables, checks their hashes and inventories,
    # and reconstructs the complete physical cut path and roles of each branch.
    branches = {(job[0], f'{job[1]}.{job[2]}'): job for job in jobs(HERE / 'tables')}
    recipe = json.loads((HERE / 'receipt.json').read_text())
    keys = [(r['case'], r['leaf']) for r in recipe]
    if len(keys) != len(set(keys)) or set(keys) != set(branches):
        raise ValueError("incomplete or duplicated set of residual face branches")
    with TemporaryDirectory() as work:
        tmp = Path(work)
        checker = tmp / 'checker'
        build = HERE.parents[1] / 'row-guards' / 'independent480' / 'build.py'
        subprocess.run([sys.executable, build, checker, '--export-boxes',
                        *(['--sanitize'] if args.sanitize else [])], check=True)
        with ThreadPoolExecutor(args.jobs) as pool:
            results = list(pool.map(lambda row: replay(checker, tmp, row, branches[row['case'], row['leaf']]), recipe))
    for case in TABLES:
        chosen = [r for c, r in results if c == case]
        num_empty = sum(isinstance(r, str) for r in chosen)
        num_pairs = sum(r['band_pairs'] for r in chosen if isinstance(r, dict))
        print(f"Case {case}: {num_empty} direct exclusions, {len(chosen) - num_empty} two-face bounds, "
              f"{num_pairs} band pairs.")


if __name__ == '__main__':
    main()
