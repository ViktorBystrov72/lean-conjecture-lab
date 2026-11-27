"""Verify the centred 4.80 exclusions for masks 0, 53 and 55 from stored integer hints."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from build import build

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'endpoint-cover'))
from verify import box,coverage
sys.path.insert(0,str(HERE.parents[1]/'terminal-audit'))
from sweep import case_masks

EXPECTED={0:8,53:1,55:1}
SIDE=4800000000


def manifest():
    data=json.loads((HERE/'receipt.json').read_bytes())
    masks=case_masks()
    rows=data['runs']
    if len(masks)!=187 or data['side_nano']!=SIDE or data['closed_masks']!=list(EXPECTED):
        raise ValueError('Invalid mask inventory or test context')
    for case,n in EXPECTED.items():
        selected=[r for r in rows if r['case']==case]
        if len(selected)!=n or len({r['leaf'] for r in selected})!=n:
            raise ValueError(f'Incorrect case table for {case}')
        owners={i for i in range(21) if masks[case]&(1<<i)}
        regions=[]
        for r in selected:
            if r['mask']!=format(masks[case],'x') or r['bands']!=128:
                raise ValueError('Wrong mask or band count')
            if case!=0 and r['cuts']:
                raise ValueError('Expected an unrestricted whole mask')
            regions.append(box(r['cuts'],owners,True))
        if coverage(regions,True)[0] is not None:
            raise ValueError(f'Terminal domains leave part of case {case} uncovered')
    if len(rows)!=sum(EXPECTED.values()):raise ValueError('Unexpected case')
    return rows


def check_one(executable,row):
    path=HERE/'certificates'/row['certificate']
    if path.name!=row['certificate'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
        raise ValueError('Invalid or changed core point trace')
    n=int(row['mask'],16)
    cmd=[executable,row['mask'],str(row['bands']),str(row['rounds']),'verify',path,str(SIDE),*map(str,row['cuts'])]
    result=subprocess.run(cmd,text=True,capture_output=True,check=True)
    last=result.stdout.splitlines()[-1]
    m=re.fullmatch(rf'EXCLUDED mask {n} index (\d+) round (\d+) [AB]',last)
    if not m or not 0<=int(m[1])<18 or not 0<=int(m[2])<row['rounds'] or last!=row['verdict']:
        raise ValueError((row['case'],row['leaf'],last))
    return f"{row['case']}:{row['leaf']} {last}"


def physical_control(kernel,work):
    study=HERE.parents[1]
    origin=study/'terminal-crosscheck'
    witness=study/'rack/saved/closest-rational.json'
    bands=work/'bands';trace=work/'observations'
    subprocess.run([sys.executable,origin/'control.py',witness,'--output',bands],check=True)
    import os
    env=dict(os.environ,RACK_CONTROL_BANDS=str(bands),RACK_CONTROL_TRACE=str(trace))
    proc=subprocess.run([kernel,'1efbef','128','10','verify',origin/'certificates/control-53.txt',
                         '4822876000'],env=env,capture_output=True,text=True)
    if proc.returncode!=1 or proc.stdout.splitlines()[-1]!='UNDECIDED':raise ValueError('Positive control failed')
    subprocess.run([sys.executable,origin/'control.py',witness,'--rounds','10','--trace',trace],check=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel',type=Path,help='optional prebuilt integer verifier made by build.py')
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--sanitize',action='store_true')
    p.add_argument('--control',action='store_true',help='also audit a real case-53 packing at the outer side')
    args=p.parse_args()
    if not 1<=args.workers<=8:p.error('workers must be between 1 and 8')
    rows=manifest()
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)
        if args.kernel:
            exe=args.kernel.resolve()
        else:
            exe=work/'integer-verifier'
            build(exe,sanitize=args.sanitize)
        with ThreadPoolExecutor(max_workers=args.workers) as workers:
            for line in workers.map(lambda r:check_one(exe,r),rows):
                print(line,flush=True)
        if args.control:physical_control(exe,work)
    print("Excluded every pose in cases 0, 53 and 55 at centred side 24/5.",flush=True)


if __name__=='__main__':main()
