"""Recompute the geometric exclusions credited to the six exceptional masks."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'endpoint-cover'))
import verify as cover
sys.path.insert(0, str(HERE.parent / 'row-guards' / 'independent480'))
import build as centred

# Two leaves use 1,280 rational angle bands. The proof kernel already constructs
# frames for general B. Raise only its CLI input limit for this replay.
centred.PARSE = centred.only(centred.PARSE, 'bandCount>768', 'bandCount>1280')

SIDE = 4_822_876_000
CASES = (53, 55, 82, 92, 115, 137)


def inventory(directory):
    tables = cover.inputs(directory)
    masks, _ = cover.inventory(tables['stabs18-endpoint-window.json'])
    result = {}
    for case in CASES:
        mask = masks[case]
        owners = {k for k in range(21) if mask & (1 << k)}
        for i, (prefix, table) in enumerate(cover.normalized_roots(case, tables, mask, owners)):
            for j, (tail, _, tag) in enumerate(table):
                if cover.kind(tag) == 'empty':
                    leaf = f'{i}.{j}'
                    result[(case, leaf)] = (mask, prefix + tail, leaf not in cover.OMIT.get(case, set()))
    if len(result) != 89 or sum(required for _, _, required in result.values()) != 83:
        raise ValueError('Unexpected endpoint inventory')
    return result


def checked(kernel, proposer, work, region, proof, traces):
    case, leaf, mask, cuts = region
    offset, size = proof['offset'], proof['bytes']
    body = traces[offset:offset + size]
    if len(body) != size or hashlib.sha256(body).hexdigest() != proof['sha256']:
        raise ValueError(f'Invalid point trace for {case}:{leaf}')
    path = work / f'points-{case}-{leaf}'
    path.write_bytes(body)
    command = [kernel, format(mask, 'x'), str(proof['bands']), str(proof['rounds']),
               'verify', path, str(SIDE), *map(str, cuts)]
    output = subprocess.run(command, check=True, text=True, capture_output=True)
    verdict = output.stdout.splitlines()[-1]
    parsed = re.fullmatch(rf'EXCLUDED mask {mask} index (\d+) round (\d+) [AB]', verdict)
    if verdict != proof['verdict'] or not parsed or not (0 <= int(parsed[1]) < 18
                                                          and 0 <= int(parsed[2]) < proof['rounds']):
        raise ValueError(f'{case}:{leaf} failed: {verdict}')
    if proposer:
        path = work / f'fresh-{case}-{leaf}'
        fresh = [format(mask, 'x'), str(proof['bands']), str(proof['rounds']),
                 'generate', path, str(SIDE), *map(str, cuts)]
        made = subprocess.run([proposer, *fresh], check=True, text=True, capture_output=True)
        fresh[3] = 'verify'
        tested = subprocess.run([kernel, *fresh], check=True, text=True, capture_output=True)
        if tested.stdout.splitlines()[-1] != made.stdout.splitlines()[-1]:
            raise ValueError('Regenerated point trace failed independent replay')
    return (case, leaf)


def positive_control(kernel, work):
    control = HERE.parent / 'terminal-crosscheck' / 'control.py'
    witness = HERE.parent / 'rack' / 'saved' / 'closest-rational.json'
    hints, bands, snapshots = (work / name for name in ('control-hints', 'control-bands', 'snapshots'))
    rounds = 3
    hints.write_text(''.join(f'{step} {owner} 0\n' for step in range(rounds) for owner in range(18)))
    command = [sys.executable, control, witness, '--bands', '1280', '--rounds', str(rounds)]
    subprocess.run([*command, '--output', bands], check=True)
    env = dict(os.environ, RACK_CONTROL_BANDS=str(bands), RACK_CONTROL_TRACE=str(snapshots))
    run = subprocess.run([kernel, '1efbef', '1280', str(rounds), 'verify', hints, str(SIDE)],
                         env=env, text=True, capture_output=True)
    if run.returncode != 1 or run.stdout.splitlines()[-1] != 'UNDECIDED':
        raise ValueError('The rational control packing was excluded')
    subprocess.run([*command, '--trace', snapshots], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='offline path to the pinned upstream replay directory')
    parser.add_argument('--kernel', type=Path, help='prebuilt compatible integer-only binary allowing 1,280 bands')
    parser.add_argument('--sanitize', action='store_true', help='enable undefined-behavior checks at compilation')
    parser.add_argument('--regenerate', action='store_true', help='also generate fresh hints for every credited leaf')
    parser.add_argument('--control', action='store_true', help='also trace an exact layout using 1,280 bands')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('Use between 1 and 8 workers')
    expected = inventory(args.source)
    receipt = json.loads((HERE / 'receipt.json').read_bytes())
    traces = lzma.decompress((HERE / 'points.xz').read_bytes())
    if receipt['side_nano'] != SIDE or receipt['pin'] != cover.PIN:
        raise ValueError('Invalid source or frame')
    done = set()
    offset = 0
    jobs = []
    for row in receipt['leaves']:
        key = (row['case'], row['leaf'])
        if key in done or key not in expected:
            raise ValueError(f'Duplicate or unknown endpoint leaf {key}')
        done.add(key)
        mask, cuts, required = expected[key]
        if row['required'] != required:
            raise ValueError(f'Incorrect subcover flag {key}')
        if 'proof' in row:
            proof = row['proof']
            if proof['offset'] != offset or proof['bytes'] < 0:
                raise ValueError('Invalid trace offset')
            offset += proof['bytes']
            jobs.append(((*key, mask, cuts), proof))
    if done != set(expected) or len(jobs) != len(expected) or offset != len(traces):
        raise ValueError('Incomplete inventory or unexpected trace bytes')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        kernel = args.kernel.resolve() if args.kernel else work / 'integer'
        if not args.kernel:
            centred.build(kernel, sanitize=args.sanitize)
        proposer = work / 'proposer' if args.regenerate else None
        if proposer:
            centred.build(proposer, proposer=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            verified = list(pool.map(lambda job: checked(kernel, proposer, work, *job, traces), jobs))
        if args.control:
            positive_control(kernel, work)
    required = sum(expected[key][2] for key in verified)
    print(f'{len(verified)}/89 physical exclusions, {required}/83 required by the reduced cover.')
    print('Credited leaves by class:', dict(sorted(Counter(c for c, _ in verified).items())))


if __name__ == '__main__':
    main()
