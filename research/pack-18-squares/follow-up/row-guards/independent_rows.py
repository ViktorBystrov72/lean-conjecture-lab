"""Reconstruct continuous pose bounds for the single-probe endpoint cases."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import check as guards

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'endpoint-cover'))
import verify as cover

SIDE = 4_822_876_000


def jobs(case, source):
    tables = cover.inputs(source)
    masks, perms = cover.inventory(tables['stabs18-endpoint-window.json'])
    mask = masks[case]
    owners = {i for i in range(21) if mask >> i & 1}
    result = {}
    for i, (prefix, leaves) in enumerate(cover.normalized_roots(case, tables, mask, owners)):
        for j, (cuts, _, rule) in enumerate(leaves):
            kind = cover.kind(rule)
            if kind == 'empty':
                continue
            sym = tuple(rule[0])
            roles = [2, 0, 1, 18, 13, 5, 11] if case == 53 else rule[1]
            sources = [perms[sym].index(owner) for owner in roles]
            if len(set(sources)) != 7 or not set(sources) <= owners:
                raise ValueError('Invalid seven-tile assignment')
            result[f'{i}.{j}'] = dict(mask=mask, cuts=prefix + cuts, kind=kind,
                                      sym=sym, roles=roles, sources=sources, perms=perms)
    if len(result) != {53: 71, 55: 7}[case]:
        raise ValueError('Incomplete source guard inventory')
    return result


def select_guard(job, sym=None, kind=None):
    """Choose seven witnesses after a square symmetry, preserving the original cuts."""
    sym = job['sym'] if sym is None else tuple(sym)
    kind = job['kind'] if kind is None else kind
    if sym not in job['perms'] or kind not in ('faces', 'chord'):
        raise ValueError('Invalid square symmetry or guard type')
    sources = [job['perms'][sym].index(owner) for owner in job['roles']]
    if len(set(sources)) != 7 or not all(job['mask'] >> i & 1 for i in sources):
        raise ValueError('A selected witness is absent from this mask')
    return dict(job, sym=sym, kind=kind, sources=sources)


def check_boxes(path, job, bands):
    by_owner = {i: {} for i in range(21) if job['mask'] >> i & 1}
    for line in path.read_text().splitlines():
        owner, k, b, x, X, y, Y = map(int, line.split())
        if (owner not in by_owner or k in by_owner[owner] or b != bands
                or not 0 <= k < b or not 0 <= x <= X <= SIDE // 2
                or not 0 <= y <= Y <= SIDE // 2):
            raise ValueError('Invalid outer box')
        by_owner[owner][k] = [k, b, x // 500, -(-X // 500), y // 500, -(-Y // 500)]
    if not all(by_owner.values()):
        raise ValueError('Missing owner in the geometry export')
    rows = [list(by_owner[j].values()) for j in job['sources']]
    guards.check(dict(sym=job['sym'], roles=job['roles'], kind=job['kind'], rows=rows))


def run_leaf(kernel, job, bands, rounds, trace, boxfile, mode='verify'):
    # Remove any earlier output. A failed export must never replay stale bounds.
    Path(boxfile).unlink(missing_ok=True)
    mask = job['mask']
    argv = [kernel, f'{mask:x}', str(bands), str(rounds), mode, trace, str(SIDE),
            *map(str, job['cuts'])]
    run = subprocess.run(argv, env={**os.environ, 'PACK18_OUTER_BOXES': str(boxfile)},
                         text=True, capture_output=True)
    last = run.stdout.splitlines()[-1:] or ['']
    if run.returncode == 0 and re.fullmatch(rf'EXCLUDED mask {mask} index \d+ round \d+ [AB]', last[0]):
        return 'empty'
    if run.returncode != 1 or last != ['UNDECIDED']:
        raise ValueError(f'Unexpected geometry outcome {run.returncode}: {last} {run.stderr}')
    check_boxes(boxfile, job, bands)
    return 'guard'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=int, choices=[53, 55])
    parser.add_argument('--source', type=Path, help='local directory with pinned upstream JSON')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--workers', type=int, default=3, choices=range(1, 9))
    args = parser.parse_args()
    folder = HERE / f'independent{args.case}'
    receipt = json.loads((folder / 'receipt.json').read_text())
    expected = jobs(args.case, args.source)
    leaves = receipt['leaves']
    names = [r['leaf'] for r in leaves]
    if (receipt['case'] != args.case or not names or len(set(names)) != len(names)
            or not set(names) <= set(expected)):
        raise ValueError('Wrong case or duplicate/unknown leaf')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        kernel = work / 'verify'
        subprocess.run([sys.executable, HERE / 'independent480/build.py', kernel, '--export-boxes',
                        *(['--extended-bands'] if args.case == 53 else []),
                        *(['--sanitize'] if args.sanitize else [])], check=True)
        def replay(row):
            name = row['leaf']
            directory = work / name
            directory.mkdir()
            trace = gzip.decompress((folder / 'certificates' / f'{name}.txt.gz').read_bytes())
            if sha256(trace).hexdigest() != row['sha256']:
                raise ValueError(f'Wrong trace for {name}')
            points = directory / 'points'
            points.write_bytes(trace)
            job = select_guard(expected[name], row.get('sym'), row.get('kind'))
            verdict = run_leaf(kernel, job, row['bands'], row['rounds'], points,
                               directory / 'boxes')
            if verdict != row['result']:
                raise ValueError(f'Wrong outcome for {name}: {verdict}')
            return verdict
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            counts = Counter(pool.map(replay, leaves))
    print(f'Case {args.case}: {len(names)}/{len(expected)} guard leaves verified. {dict(counts)}')


if __name__ == '__main__':
    main()
