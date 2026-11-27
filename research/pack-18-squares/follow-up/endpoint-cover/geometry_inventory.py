"""Match full-side geometry receipts to the 193 exceptional terminal records.

This reports certificate inventory. Replay the geometry certificates and the
cover proof before using the resulting counts in a lower-bound argument.
"""
import argparse
import json
from pathlib import Path
import re

import verify as cover

HERE = Path(__file__).resolve().parent
CASES = (53, 55, 82, 92, 115, 137)
SIDE = 4_822_876_000


def need(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def source_inventory(directory):
    tables = cover.inputs(directory)
    masks, _ = cover.inventory(tables['stabs18-endpoint-window.json'])
    raw = {}
    omitted = set()
    for case in CASES:
        mask = masks[case]
        owners = {i for i in range(21) if mask >> i & 1}
        roots = cover.normalized_roots(case, tables, mask, owners)
        for i, (_, leaves) in enumerate(roots):
            for j, (_, _, action) in enumerate(leaves):
                raw[case, f'{i}.{j}'] = cover.kind(action)
        omitted.update((case, leaf) for leaf in cover.OMIT.get(case, set()))
    need(len(raw) == 193 and len(omitted) == 8 and omitted <= raw.keys(),
         "unexpected full or reduced cover")
    return masks, raw, raw.keys() - omitted


def empty_verdict(record, mask):
    return isinstance(record, str) and re.fullmatch(
        rf'EXCLUDED mask {mask} index (?:[0-9]|1[0-7]) round [0-9]+ [AB]', record)


def two_face_guard(record):
    keys = ('first_middle_bands', 'second_middle_bands', 'band_pairs',
            'first_probe_gap_units', 'second_probe_gap_units')
    return (isinstance(record, dict) and all(type(record.get(k)) is int and record[k] > 0 for k in keys)
            and record['band_pairs'] == record['first_middle_bands'] * record['second_middle_bands'])


def gather(base, masks, raw, required):
    accepted = set()

    def add(case, leaf, allowed_cases, allowed_labels):
        key = (case, leaf)
        need(type(case) is int and case in allowed_cases and raw.get(key) in allowed_labels,
             f"unexpected case, leaf or source action: {case}:{leaf}")
        need(key not in accepted, f"duplicate certificate: {case}:{leaf}")
        accepted.add(key)

    empty = read(base / 'endpoint-empty/receipt.json')
    need(empty['pin'] == cover.PIN and empty['side_nano'] == SIDE, "wrong empty-certificate side or pin")
    empty_keys = {key for key, label in raw.items() if label == 'empty'}
    for row in empty['leaves']:
        case, leaf = row['case'], row['leaf']
        add(case, leaf, CASES, {'empty'})
        need(row['required'] is ((case, leaf) in required), "wrong required flag on empty certificate")
        need(empty_verdict(row['proof']['verdict'], masks[case]), "empty verdict names wrong mask or outcome")
    need(accepted == empty_keys and len(accepted) == 89, "incomplete empty receipt")

    residual = read(base / 'endpoint-guards/independent-residual/receipt.json')
    for row in residual:
        case, leaf = row['case'], row['leaf']
        add(case, leaf, (82, 92, 115), {'faces'})
        result = row['result']
        need(empty_verdict(result, masks[case]) or two_face_guard(result),
             f"malformed two-face decision for {case}:{leaf}")
    need(len(residual) == 20, "incomplete residual receipt")

    fork = read(base / 'endpoint-guards/independent137/receipt.json')
    need(fork['mask'] == format(masks[137], 'x') and fork['side_nano'] == SIDE, "wrong case-137 mask or side")
    for row in fork['leaves']:
        need(row.get('case', 137) == 137 and type(row['leaf']) is int and two_face_guard(row['guard']),
             "malformed case-137 guard")
        add(137, f"{row['leaf']}.0", (137,), {'faces'})
    need(len(fork['leaves']) == 6, "incomplete case-137 receipt")

    for case in (53, 55):
        file = base / f'row-guards/independent{case}/receipt.json'
        if not file.exists():
            continue
        data = read(file)
        need(data['case'] == case, "single-probe receipt belongs to a different class")
        for row in data['leaves']:
            need(row.get('case', case) == case and row['result'] in ('empty', 'guard'),
                 "incorrect single-probe case or result")
            add(case, row['leaf'], (case,), {'chord', 'faces'})
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='directory containing the seven pinned source tables')
    parser.add_argument('--require-complete', action='store_true',
                        help='exit with status 1 when any required exceptional leaf is missing')
    args = parser.parse_args()
    masks, raw, required = source_inventory(args.source)
    accepted = gather(HERE.parent, masks, raw, required)
    print("Receipt inventory only. Replay the geometry certificates and cover proof to establish the bounds.")
    print("Case  Raw matched/total  Raw missing  Required matched/total  Required missing  Coverage")
    for case in (*CASES, None):
        full = {k for k in raw if case is None or k[0] == case}
        kept = required & full
        status = "complete" if kept <= accepted else "partial"
        print(f"{str(case or 'All'):>4}  {len(full & accepted):3}/{len(full):<3}            "
              f"{len(full - accepted):3}          {len(kept & accepted):3}/{len(kept):<3}                 "
              f"{len(kept - accepted):3}       {status}")
    return int(args.require_complete and bool(required - accepted))


if __name__ == '__main__':
    raise SystemExit(main())
