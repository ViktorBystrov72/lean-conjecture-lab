"""Reconstruct the six endpoint enclosures for mask 0x1ffbcf at the full rack side."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import check_guards as guards


def endpoint_records(path, bands, flip):
    by_owner = {owner: {} for owner in guards.OWNERS}
    for line in path.read_text().splitlines():
        owner, k, b, x, X, y, Y = map(int, line.split())
        if (owner not in by_owner or b != bands or not 0 <= k < b or
                k in by_owner[owner] or not 0 <= x <= X <= 2411438000 or
                not 0 <= y <= Y <= 2411438000):
            raise ValueError("invalid rectangle in geometry output")
        # One guard microunit is 500 geometry lattice units. Include both extrema.
        by_owner[owner][k] = [k, b, x // 500, -(-X // 500), y // 500, -(-Y // 500)]
    mapping = guards.owner_map((0, 0, int(flip)))
    return [(owner, list(rows.values())) for owner, rows in by_owner.items()
            if mapping[owner] in guards.ACTIVE]


def replay(checker, tmp):
    receipt = json.loads((HERE / 'receipt.json').read_text())
    leaves = receipt['leaves']
    indices = [row['leaf'] for row in leaves]
    if (receipt['mask'] != hex(guards.MASK)[2:] or receipt['side_nano'] != 4822876000 or
            indices != list(range(6)) or len(guards.PATHS) != 6 or
            guards.cover(list(guards.PATHS)) != 6):
        raise ValueError("incomplete class 137 cover or unexpected rack")
    total = 0
    for row in leaves:
        index = row['leaf']
        trace = gzip.decompress((HERE / 'certificates' / f'{index}.txt.gz').read_bytes())
        if hashlib.sha256(trace).hexdigest() != row['sha256']:
            raise ValueError(f"incorrect trace for leaf {index}")
        points = tmp / 'points.txt'
        points.write_bytes(trace)
        boxes = tmp / f'leaf-{index}.txt'
        cuts = [str(v) for cut in guards.PATHS[index] for v in cut]
        cmd = [checker, receipt['mask'], str(row['bands']), str(row['rounds']), 'verify',
               points, str(receipt['side_nano']), *cuts]
        run = subprocess.run(cmd, env={**os.environ, 'PACK18_OUTER_BOXES': str(boxes)},
                             capture_output=True, text=True)
        if run.returncode != 1 or run.stdout.splitlines()[-1:] != ['UNDECIDED']:
            raise ValueError(f"unexpected geometry outcome for leaf {index}: "
                             f"{run.stdout[-250:]} {run.stderr[-250:]}")
        flip = guards.FLIP_Y[index]
        computed = guards.verify_leaf(endpoint_records(boxes, row['bands'], flip), flip)
        if computed != row['guard']:
            raise ValueError(f"guard diagnostics differ on leaf {index}: {computed}")
        total += computed['band_pairs']
        print(f"Leaf {index}: {computed['band_pairs']} middle-angle pairs accepted.", flush=True)
    print(f"All six leaves of class 137 accepted ({total} pairs).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sanitize', action='store_true', help='enable undefined behavior checks')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as work:
        tmp = Path(work)
        checker = tmp / 'checker'
        build = HERE.parents[1] / 'row-guards' / 'independent480' / 'build.py'
        subprocess.run([sys.executable, build, checker, '--export-boxes',
                        *(['--sanitize'] if args.sanitize else [])], check=True)
        replay(checker, tmp)
