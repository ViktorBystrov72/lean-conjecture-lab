import argparse
import concurrent.futures
import itertools
import json
import re
import subprocess
from pathlib import Path


def actions(x,y):
    for flip in (False,True):
        a,b=(y,x) if flip else (x,y)
        for _ in range(4):
            yield a,b
            a,b=2000-b,a


def labels():
    return sorted({point for centre in [(390,390),(617,617),(797,359),(1000,716),(1000,1000)] for point in actions(*centre)})


def case_masks():
    pts=labels()
    G=[tuple(pts.index(list(actions(*p))[k]) for p in pts) for k in range(8)]
    full=(1<<21)-1
    canonical={min(tuple(sorted(g[i] for i in t)) for g in G) for t in itertools.combinations(range(21),3)}
    return sorted(full-sum(1<<i for i in t) for t in canonical)


def run(exe, case, mask, bands, rounds, side):
    process=subprocess.run([str(exe),'--side',str(side),format(mask,'x'),str(bands),str(rounds)],check=True,capture_output=True,text=True)
    verdict=process.stdout.splitlines()[-1]
    if re.fullmatch(r'EXCLUDED (empty owner [0-9]+|guaranteed overlap [0-9]+ [0-9]+) round [0-9]+',verdict):
        status='excluded'
    elif verdict in ('INCONCLUSIVE fixed point','INCONCLUSIVE budget'):
        status='inconclusive'
    else:
        raise RuntimeError(verdict)
    return dict(case=case,mask=format(mask,'x'),bands=bands,max_rounds=rounds,side_nanounits=side,status=status,end=verdict)


def main():
    parser=argparse.ArgumentParser(description='Run independent continuous-angle relaxations for selected orbits.')
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--cases',default='all')
    parser.add_argument('--side',type=int,default=4822876000,help='centred box side in nanounits')
    parser.add_argument('--bands',type=int,default=16)
    parser.add_argument('--rounds',type=int,default=12)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--output',type=Path,required=True)
    opts=parser.parse_args()
    ms=case_masks()
    if len(ms)!=187:raise ValueError('incorrect orbit count')
    cases=range(187) if opts.cases=='all' else [int(x) for x in opts.cases.split(',')]
    exe=opts.exe.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=opts.workers) as pool:
        futures=[pool.submit(run,exe,i,ms[i],opts.bands,opts.rounds,opts.side) for i in cases]
        outcomes=[f.result() for f in futures]
    print('Excluded',sum(x['status']=='excluded' for x in outcomes),'out of',len(outcomes))
    print('Inconclusive',[x['case'] for x in outcomes if x['status']=='inconclusive'])
    opts.output.write_text(json.dumps(outcomes,indent=2)+'\n')


if __name__=='__main__':main()
