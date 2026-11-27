"""Recheck independent geometric exclusions at the outer container side."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import lzma
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
FOLLOW = HERE.parent
sys.path.insert(0, str(FOLLOW / 'empty-cover'))
import cover

spec = importlib.util.spec_from_file_location('endpoint_points', FOLLOW / 'endpoint-empty' / 'replay.py')
points = importlib.util.module_from_spec(spec)
spec.loader.exec_module(points)


def inventory(table_file):
    cover.controls()
    table = cover.read(table_file)
    audit = FOLLOW / 'terminal-audit'
    baseline = json.loads((audit / 'sweep-receipt.json').read_bytes())
    adaptive = json.loads((audit / 'adaptive-receipt.json').read_bytes())
    other = json.loads((FOLLOW / 'empty-cover' / 'receipt.json').read_bytes())
    previous = (set(baseline['coarse']['excluded_cases']) | set(baseline['sample'])
                | set(adaptive['newly_excluded']) | {r['case'] for r in other['completed_orbits']})
    remaining = set(table) - previous
    if (len(previous) != 136 or len(remaining) != 45 or previous - set(table)
            or remaining != set(other['remaining_empty_orbits'])):
        raise ValueError('Ordinary mask inventories do not match')
    regions = {}
    for case in sorted(remaining):
        mask, scale, paths = table[case]
        if 128 % scale:
            raise ValueError('Incompatible source angle scale')
        for i, path in enumerate(paths):
            cuts = []
            for owner, op, v in path:
                cuts.extend((owner, op, v * (128 // scale) if op >= 4 else v))
            regions[(case, i)] = (mask, cuts)
    if len(regions) != 91:
        raise ValueError('Unexpected leaf count')
    return regions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', type=Path, help='offline pinned n18-482-base.json')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--kernel', type=Path, help='compatible prebuilt integer-only verifier')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--regenerate', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('Use 1 to 8 workers')
    regions = inventory(args.table)
    receipt = json.loads((HERE / 'receipt.json').read_bytes())
    traces = lzma.decompress((HERE / 'points.xz').read_bytes())
    if receipt['side_nano'] != points.SIDE or receipt['pin'] != points.cover.PIN:
        raise ValueError('Wrong test frame or pinned source')
    seen = set()
    jobs = []
    offset = 0
    for row in receipt['leaves']:
        key = (row['case'], row['leaf'])
        if key in seen or key not in regions:
            raise ValueError(f'Unknown or duplicate ordinary leaf {key}')
        seen.add(key)
        proof = row['proof']
        if proof['offset'] != offset or proof['bytes'] < 0:
            raise ValueError('Invalid trace extent')
        offset += proof['bytes']
        mask, cuts = regions[key]
        jobs.append(((*key, mask, cuts), proof))
    if seen != set(regions) or offset != len(traces):
        raise ValueError('A required leaf or trace is missing')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        kernel = args.kernel.resolve() if args.kernel else work / 'integer'
        if not args.kernel:
            points.centred.build(kernel, sanitize=args.sanitize)
        proposer = work / 'proposer' if args.regenerate else None
        if proposer:
            points.centred.build(proposer, proposer=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            checked = set(pool.map(lambda j: points.checked(kernel, proposer, work, *j, traces), jobs))
    if checked != set(regions):
        raise ValueError('Mismatch after geometric replay')
    print(f'Excluded {len(checked)} terminal regions for all {len({c for c, _ in checked})} remaining ordinary masks.')
    print('Together with the previous 136 complete masks: 181/181 ordinary classes.')


if __name__ == '__main__':
    main()
