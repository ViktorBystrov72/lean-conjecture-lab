"""Regenerate one or more numerical batches in a separate output directory."""

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
PIN = 'c5775bae40085f67f4c30f8916b0d6e998c304ab'
NEIGHBORS = {
    17: 'dfa1358efc0881aa376ace0e85a914472891fccb1b533a867ab9ba3fa8cee2db',
    19: 'f72ffb931d0237a2f5a4579329d58d9f2a90482debc4feb2cd31482a157a6fd9',
    20: '5a075ef10a4c74d6ee3c079860895546fd9880d959954aaf6870d9fd8df9c52d',
    21: 'd877c28157a9346295cc48746471d6663a99559941a49918106bd6270c905762',
    22: '0d310b7d60f1647479efb188ffa64442752dd984bb56eedfe512de69ea857c71',
}
BATCHES = ('a', 'b', 'c', 'd', 'e', 'grid', 'neighbors')


def fetch_neighbors(dest):
    dest.mkdir()
    for n, expected in NEIGHBORS.items():
        name = f'n-{n:03d}.yaml'
        url = f'https://raw.githubusercontent.com/jlevy/squares/{PIN}/packing/witnesses/known-best/{name}'
        with urlopen(url, timeout=45) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'SHA-256 mismatch for {name}')
        (dest/name).write_bytes(data)


def mira_seed(work):
    layouts = ROOT.parent/'layouts'
    path = layouts/'mira-six-tilt-exact.json'
    if not path.exists():
        path = work/'mira-six-tilt-exact.json'
        subprocess.run([sys.executable, layouts/'fetch_mira.py', '--output', path], check=True)
    data = json.loads(path.read_text())
    root = math.sqrt(7)

    def value(pair):
        a, b = map(Fraction, pair)
        return float(a) + float(b)*root

    squares = [[value(f['x']), value(f['y']), math.atan(value(f['s'])/value(f['c']))]
               for f in data['frames']]
    dest = work/'mira-six-tilt.json'
    dest.write_text(json.dumps({'side': (7+root)/2, 'squares': squares}))
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='a new output directory')
    parser.add_argument('--batch', nargs='+', choices=BATCHES, default=BATCHES)
    args = parser.parse_args()
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PACK18_RUN=str(work), OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    flags = ['-dynamiclib'] if platform.system() == 'Darwin' else ['-shared', '-fPIC']
    subprocess.run([env.get('CXX','c++'), '-std=c++17', '-O3', *flags, ROOT/'packing.cpp',
                    '-o', work/'packing.dylib'], check=True)
    historical = ROOT/'seeds'/'hamalainen.json'
    other = [ROOT/'seeds'/name for name in
             ('gustafson-fig7.json', 'cantrell-fig7.json', 'gensane-ryckelynck-fig7.json')]

    for batch in args.batch:
        if batch == 'neighbors':
            fetch_neighbors(work/'neighbor-inputs')
            command = [ROOT/'neighboring.py']
        elif batch == 'grid':
            command = [ROOT/'grid_starts.py']
        else:
            rng, starts = {'a': (181527,350), 'b': (181528,350),
                           'c': (181601,6000), 'd': (181602,6000), 'e': (181701,6000)}[batch]
            command = [ROOT/'search.py', '--rng', str(rng), '--starts', str(starts),
                       '--output', f'batch-{batch}']
            if batch in ('c','d','e'):
                command.append('--extended')
            if batch == 'e':
                command.extend(other)
            else:
                seeds = [historical, mira_seed(work)]
                command.extend(reversed(seeds) if batch in ('b','d') else seeds)
        subprocess.run([sys.executable, *command], cwd=work, env=env, check=True)


if __name__ == '__main__':
    main()
