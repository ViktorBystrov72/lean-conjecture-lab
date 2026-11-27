"""Replay the ordinary cases and the available endpoint certificates at the full rack side."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'endpoint-cover'))
sys.path.insert(0, str(HERE / 'terminal-audit'))
sys.path.insert(0, str(HERE.parent / 'audit'))
import verify as cover
import sweep
from rack_check import Quadratic, exact_source, geometry


def read(path):
    return json.loads(path.read_bytes())


def run(script, *args):
    subprocess.run([sys.executable, HERE / script, *map(str, args)], check=True)


def baseline(source, tmp, workers):
    core = tmp / 'audit'
    subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O3', '-ftrapv',
                    HERE / 'terminal-audit/case_audit.cpp', '-o', core], check=True)
    sample_result = tmp / 'sample.json'
    run('terminal-audit/replay.py', '--exe', core, '--workers', workers, '--output', sample_result)
    past = read(HERE / 'terminal-audit/sweep-receipt.json')
    adaptive = read(HERE / 'terminal-audit/adaptive-receipt.json')
    masks = sweep.case_masks()
    coarse = past['coarse']
    sample = set(read(sample_result)['sample_excluded'])
    if sample != set(past['sample']):
        raise ValueError('Mismatch between sample proof and roster')
    plan = {i: (coarse['bands'], coarse['rounds']) for i in coarse['excluded_cases']}
    for row in adaptive['results']:
        if row['status'] == 'excluded':
            i = row['case']
            if row['side_nanounits'] != 4_822_876_000 or int(row['mask'], 16) != masks[i]:
                raise ValueError('Wrong square or unused marks')
            plan[i] = (row['bands'], row['max_rounds'])
    def recompute(item):
        i, (bands, rounds) = item
        verdict = sweep.run(core, i, masks[i], bands, rounds, 4_822_876_000)
        if verdict['status'] != 'excluded':
            raise ValueError(f'Inconclusive computation in ordinary case {i}')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(recompute, plan.items()))
    prior = set(plan) | sample
    predicted = set(coarse['excluded_cases']) | sample | set(adaptive['newly_excluded'])
    if prior != predicted or len(prior) != 118:
        raise ValueError('Inconsistent roster for the first 118 cases')

    table = source / 'n18-482-base.json'
    cores = [tmp / 'angles', tmp / 'supports']
    run('empty-cover/build.py', cores[0])
    run('empty-cover/build.py', cores[1], '--endpoint-supports')
    run('empty-cover/cover.py', '--table', table)
    run('empty-cover/replay.py', '--core', cores[0], '--endpoints', cores[1],
        '--table', table, '--workers', workers)
    more = {r['case'] for r in read(HERE / 'empty-cover/receipt.json')['completed_orbits']}
    if more & prior or len(prior | more) != 136:
        raise ValueError('Expected 136 distinct ordinary cases')

    run('ordinary-empty/replay.py', '--table', table, '--workers', workers)
    more_cases = {r['case'] for r in read(HERE / 'ordinary-empty/receipt.json')['leaves']}
    exceptional = {53, 55, 82, 92, 115, 137}
    if (prior | more) & more_cases or prior | more | more_cases != set(range(187)) - exceptional:
        raise ValueError('Missing ordinary case or repeated proof domain')
    print('All 181 ordinary classes excluded at side 4.822876.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='local pinned upstream replay directory')
    parser.add_argument('--workers', type=int, default=3, choices=range(1, 9))
    parser.add_argument('--ordinary-only', action='store_true', help='stop after the 181 ordinary classes')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        source = args.source.resolve() if args.source else tmp / 'tables'
        if args.source is None:
            source.mkdir()
            for name in cover.FILES:
                with urlopen(f'{cover.SOURCE}/{name}', timeout=30) as response:
                    (source / name).write_bytes(response.read())
        cover.inputs(source)
        side, tiles = exact_source(HERE.parent / 'layouts/hamalainen-exact.json')
        if side != Quadratic(Fraction(7, 2), Fraction(1, 2)):
            raise ValueError('Unexpected side in the construction')
        geometry(tiles, side)
        print('Verified the exact 18-square construction at (7 + sqrt(7))/2.', flush=True)
        baseline(source, tmp, args.workers)
        if args.ordinary_only:
            return
        run('endpoint-cover/verify.py', '--data', source)
        run('endpoint-empty/replay.py', '--source', source, '--workers', args.workers)
        run('endpoint-guards/independent137/replay.py')
        run('endpoint-guards/independent-residual/replay.py', '--jobs', args.workers)
        for case in (55, 53):
            run('row-guards/independent_rows.py', case, '--source', source, '--workers', args.workers)
        run('endpoint-cover/geometry_inventory.py', '--source', source, '--require-complete')
        print('All 187 classes preclude a packing below the exact construction side.', flush=True)


if __name__ == '__main__':
    main()
