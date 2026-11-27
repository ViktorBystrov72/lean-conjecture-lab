"""One asymmetric perturbation for each near-balanced 5-by-5 occupancy mask."""
import argparse
import csv
import itertools
import math
import time
from pathlib import Path
import numpy as np
import search

def orbit(mask):
    x=mask
    images=[]
    for flip in range(2):
        u=x if not flip else tuple((4-i,j) for i,j in x)
        for _ in range(4):
            images.append(tuple(sorted(u)))
            u=tuple((j,4-i) for i,j in u)
    return images

def masks():
    # 7 vacant cells; every row/column contains 1, 2 or 3 vacancies.
    rows_by_size={k:list(itertools.combinations(range(5),k)) for k in (1,2,3)}
    visited=set()
    for row_sizes in itertools.product((1,2,3), repeat=5):
        if sum(row_sizes)!=7:continue
        for rows in itertools.product(*(rows_by_size[k] for k in row_sizes)):
            cells=tuple((i,j) for i,row in enumerate(rows) for j in row)
            if cells in visited: continue
            columns=[sum(j in row for row in rows) for j in range(5)]
            if min(columns)<1 or max(columns)>3: continue
            visited.update(orbit(cells));yield cells

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rng',type=int,default=180519)
    parser.add_argument('--part',type=int,default=0)
    parser.add_argument('--parts',type=int,default=1)
    parser.add_argument('--output',default='batch-grid')
    args=parser.parse_args()
    out=search.ROOT/args.output;out.mkdir(exist_ok=True)
    best=float('inf'); best_i=-1; nrun=0; close=0
    start=time.perf_counter()
    with (out/'runs.csv').open('w',buffering=1) as f:
        rows=csv.writer(f);rows.writerow(['index','removed','locked','repaired_side'])
        for i,missing in enumerate(masks()):
            if i%args.parts!=args.part:continue
            rng=np.random.default_rng(np.random.SeedSequence([args.rng,i]))
            coords=np.array([(i,j) for i in range(5) for j in range(5) if (i,j) not in missing]) - 2.
            angle=rng.normal(0,.18,18)
            fix=(rng.random(18)<rng.uniform(.05,.65))
            angle[fix]=0.
            # Motivate non-parallel starts before relaxation of load-bearing chains.
            coords+=rng.normal(0,.12,coords.shape)
            x=np.r_[np.column_stack([coords,angle]).ravel(),5.]
            locked=sum(1<<k for k in np.flatnonzero(fix))
            for weight,budget in [(1.25,105),(10,120),(75,115),(600,90)]:
                search._lib.polish(search.ptr(x),weight,int(locked),budget)
            candidate=search.feasible_rescale(x)
            if candidate[-1]<search.S+.05:
                polished=search.feasible_rescale(search.slsqp(x,locked))
                if polished[-1]<candidate[-1]:candidate=polished
            nrun+=1;close+=int(candidate[-1]<search.S+.01)
            rows.writerow([i,' '.join(str(5*a+b) for a,b in missing),int(locked).bit_count(),format(candidate[-1],'.15f')])
            if candidate[-1]<best:
                best=float(candidate[-1]); best_i=i;search.atomic_write(out/'best.json',search.doc(candidate))
            if candidate[-1]<search.S-1e-10:
                print('CANDIDATE',best,best_i,flush=True);break
            if nrun%1000==0:print(nrun,best,round(time.perf_counter()-start,1),flush=True)
    report=dict(rng=args.rng,starts=nrun,best=best,best_index=best_i,within_0_01=close,seconds=time.perf_counter()-start)
    search.atomic_write(out/'summary.json',report);print(report,flush=True)

if __name__=='__main__':main()
