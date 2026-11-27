"""Replay the six full orbits sampled independently in issue 1050."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
from sweep import case_masks, labels

# Closed complementary splits from the public base table. Their geometry is
# re-evaluated here; no output of the producer's refuter is consulted.
RUNS={
    2: (None,[(96,20)]),
    56: (None,[(96,20)]),
    80: (None,[(32,15)]),
    86: ((11,'y',3128620000),[(96,35),(128,40)]),
    91: ((10,'x',2394491000),[(96,35),(96,35)]),
    93: (None,[(128,40)]),
}
SAMPLES={
    2: ((359,797),(716,1000),(1641,1203)),
    56: ((359,797),(1000,716),(1383,1383)),
    80: ((359,797),(390,390),(1383,617)),
    86: ((359,797),(1000,1000),(1284,1000)),
    91: ((359,797),(716,1000),(1284,1000)),
    93: ((390,390),(617,1383),(1284,1000)),
}

def evaluate(job):
    case, mask, options, bands, budget, path = job
    cmd=[str(path),*options,format(mask,'x'),str(bands),str(budget)]
    proc=subprocess.run(cmd,capture_output=True,check=True,text=True)
    final=proc.stdout.splitlines()[-1]
    if not final.startswith('EXCLUDED '):
        raise RuntimeError(f"Unclosed subcase {case} {options}: {final}")
    return dict(case=case,mask=format(mask,'x'),options=options,bands=bands,budget=budget,verdict=final)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    path=args.exe.resolve()
    masks=case_masks(); pts=labels(); jobs=[]
    if len(masks)!=187 or len(pts)!=21:raise ValueError('Wrong rack or case count')
    # One additional covering certificate must hold before calling these
    # assignments classes of unit-square packings in the test box.
    cover=subprocess.check_output([str(path),'--rack','512'],text=True).strip()
    if not cover.startswith('RACK COVERED '):raise ValueError('Unverified rack')
    for i,(cut,plans) in RUNS.items():
        mask=masks[i]
        if tuple(p for j,p in enumerate(pts) if not mask>>j&1)!=SAMPLES[i]:
            raise ValueError('Case numbering does not match published sample')
        if cut is None:
            opts=[[]]
        else:
            owner, axis, point=cut
            opts=[['--cut',str(owner),axis+'-'+sign,str(point)] for sign in ('le','ge')]
        if len(opts)!=len(plans):raise ValueError('A split half is missing')
        for options,(bands,budget) in zip(opts,plans):
            jobs.append((i,mask,options,bands,budget,path))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        report=list(pool.map(evaluate,jobs))
    receipt={'test_side':'4822876/1000000','rack':cover,'sample_excluded':sorted(RUNS),'subcases':report}
    text=json.dumps(receipt,indent=2)
    print(text)
    if args.output:args.output.write_text(text+'\n')
if __name__=='__main__':main()
