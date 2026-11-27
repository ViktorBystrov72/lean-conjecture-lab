"""Replay three disjoint fresh-start batches, followed by their contact-chart refinements."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
SEEDS = (1828000, 1831000, 1834000)
TARGET_CUTOFF = "4.86"


def summarize(out):
    sys.path.insert(0,str(STUDY / "follow-up/patch"))
    import exact
    batches = [out / f"batch-{i}" for i in range(3)]
    stages = [out / f"refine-{i}" for i in range(3)]
    stats = [json.loads((p/"summary.json").read_text()) for p in batches+stages]
    records = []
    for name,path in zip(("initial","chart"),(batches,stages)):
        rows = []
        for folder in path:
            with (folder/"runs.csv").open() as fp:
                rows.extend(csv.DictReader(fp))
        records.append(rows)
    starts, charts = records
    if len(starts)!=len({r['initial_d4_sha'] for r in starts}):
        raise ValueError("Duplicate canonical starting fingerprint")
    if {int(r['seed']) for r in charts} != {int(r['seed']) for r in starts if float(r['rational_side_approx'])<float(TARGET_CUTOFF)}:
        raise ValueError("Chart selector was not covered exactly")
    rational=[]
    for path in batches+stages:
        doc=json.loads((path/"best-rational.json").read_text())
        side=Fraction(doc['side']);tiles=[tuple(map(Fraction,t)) for t in doc['squares']]
        exact.verify(side,tiles)
        rational.append((side,path))
    side,winning = min(rational,key=lambda pair:pair[0])
    with localcontext() as ctx:
        ctx.prec=60
        H=(7+Decimal(7).sqrt())/2
        L=Decimal(side.numerator)/Decimal(side.denominator)
        report={
            "fresh_starts":len(starts),
            "canonical_start_fingerprints":len({r['initial_d4_sha'] for r in starts}),
            "family_sizes":{k:sum(r['family']==k for r in starts) for k in sorted({r['family'] for r in starts})},
            "fresh_below_cutoffs":{str(k):sum(float(r['rational_side_approx'])<k for r in starts) for k in (4.824,4.835,4.86,4.9)},
            "chart_finalists":len(charts),"chart_lp_evaluations":sum(int(r['lp_calls']) for r in charts),
            "raw_lp_below_exact_target":sum(exact.below(Fraction.from_float(float(r['raw_lp_min']))) for r in charts),
            "chart_exact_improvements":sum(exact.below(Fraction(r['rational_side'])) for r in charts),
            "best_batch":winning.name,"best_seed":json.loads((winning/'best-numerical.json').read_text())['seed'],
            "best_rational_side":str(side),"best_side_decimal":str(L),"excess_decimal":str(L-H),
            "below_target":exact.below(side),
            "witness_sha256":hashlib.sha256((winning/'best-rational.json').read_bytes()).hexdigest(),
            "batches":{p.name:record for p,record in zip(batches+stages,stats)}
        }
    return report


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("output",type=Path,help="a new directory for generated binaries and results")
    args.add_argument("--jobs",type=int,choices=(1,2,3),default=2)
    options=args.parse_args()
    out=options.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    link="-dynamiclib" if platform.system()=="Darwin" else "-shared"
    cc=os.environ.get("CXX","c++")
    for source,name in ((HERE/"chamber.cpp","chamber"),(STUDY/"search-history/packing.cpp","packing")):
        subprocess.run([cc,"-O3","-std=c++17","-fPIC",link,str(source),"-o",str(out/(name+".dylib"))],check=True)
    env=dict(os.environ,PACK18_STUDY=str(STUDY),PACK18_RUN=str(out),OMP_NUM_THREADS="1",
             OPENBLAS_NUM_THREADS="1",VECLIB_MAXIMUM_THREADS="1")
    def execute(command):
        subprocess.run([sys.executable,*map(str,command)],check=True,env=env,cwd=out)
    batches=[out/f"batch-{i}" for i in range(3)]
    with ThreadPoolExecutor(max_workers=options.jobs) as threads:
        list(threads.map(execute,[(HERE/'run.py','--seed',s,'--count',2400,'--output',p)
                                  for s,p in zip(SEEDS,batches)]))
        list(threads.map(execute,[(HERE/'charts.py','--batches',*batches,'--cutoff',TARGET_CUTOFF,
                                  '--parts',3,'--part',i,'--output',out/f'refine-{i}') for i in range(3)]))
    report=summarize(out)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"{report['fresh_starts']} fresh starts; {report['chart_lp_evaluations']} chart LPs; "
          f"best side {report['best_side_decimal']}; below record {report['below_target']}")


if __name__=="__main__":
    main()
