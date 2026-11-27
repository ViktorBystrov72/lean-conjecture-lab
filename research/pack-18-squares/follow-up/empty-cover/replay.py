"""Recompute each proved leaf and prove the combined whole-orbit count."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess

from cover import HERE, MIXED, controls, options, read


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core',type=Path,required=True,help='angular checker built without endpoint extension')
    p.add_argument('--endpoints',type=Path,required=True,help='checker built with --endpoint-supports')
    p.add_argument('--table',type=Path,help='offline copy of pinned n18-482-base.json')
    p.add_argument('--workers',type=int,default=2)
    args=p.parse_args()
    if not 1<=args.workers<=16:p.error('Expected 1 to 16 workers')
    controls()
    table=read(args.table)
    receipt=json.loads((HERE/'receipt.json').read_text())
    parent=HERE.parent/'terminal-audit'
    base=json.loads((parent/'sweep-receipt.json').read_text()); follow=json.loads((parent/'adaptive-receipt.json').read_text())
    prior=set(base['coarse']['excluded_cases'])|set(base['sample'])|set(follow['newly_excluded'])
    if len(prior)!=118 or prior&MIXED:raise RuntimeError('Unexpected prior coverage')
    commands=[];fresh=set()
    for group in receipt['completed_orbits']:
        i=group['case'];mask,b,paths=table[i]
        if i in prior or i in fresh:raise RuntimeError('Repeated case')
        fresh.add(i)
        rows=group['leaves']
        if sorted(r['leaf'] for r in rows)!=list(range(len(paths))):raise RuntimeError('Missing a leaf')
        for row in rows:
            kernel={'core':args.core,'endpoints':args.endpoints}[row['kernel']].resolve()
            op=options(paths[row['leaf']],b)
            commands.append([str(kernel),*op,format(mask,'x'),str(row['bands']),str(row['rounds'])])
    if receipt['independent_total']!=len(prior|fresh) or set(receipt['remaining_empty_orbits'])!=set(table)-(prior|fresh):
        raise RuntimeError('Aggregate coverage mismatch')
    def run(cmd):
        output=subprocess.run(cmd,text=True,capture_output=True,check=True).stdout.splitlines()[-1]
        if not re.fullmatch(r'EXCLUDED (?:empty owner \d+|guaranteed overlap \d+ \d+) round \d+',output):
            raise RuntimeError((cmd,output))
    with ThreadPoolExecutor(args.workers) as ex:list(ex.map(run,commands))
    print(f'Replayed {len(commands)} leaves for {len(fresh)} additional complete orbits; cumulative {len(prior|fresh)}/187.')

if __name__=='__main__':main()
