"""Search 18-square starts transplanted from known neighboring packing sizes."""
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import csv
import json
import time
import numpy as np
import yaml
import search

def read(n):
    obj=yaml.safe_load((search.ROOT/'neighbor-inputs'/f'n-{n:03d}.yaml').read_text())['witness']
    def scalar(v):return float(Fraction(str(v)))
    poses=[]
    for e in obj['squares']:
        if 'center' in e: x,y=map(scalar,e['center']);ang=np.radians(scalar(e['angle']))
        else:
            v=np.array([[scalar(s) for s in p] for p in e['corners']])
            x,y=v.mean(axis=0);dx,dy=v[1]-v[0];ang=np.arctan2(dy,dx)
        poses.append((x,y,ang))
    poses=np.array(poses);L=scalar(obj['side']);poses[:,:2]-=L/2
    return poses,L
def cases(rng):
    for n,repeats,limit in [(17,1200,1),(19,50,19),(20,4,190),(21,1,1100),(22,1,1200)]:
        a,L=read(n)
        if n==17: choices=[()]
        else:
            choices=list(combinations(range(n),n-18))
            rng.shuffle(choices);choices=choices[:limit]
        for drop in choices:
            take=np.array([i for i in range(n) if i not in drop])
            for _ in range(repeats):
                p=a[take].copy()
                if n==17:
                    extra=np.array([rng.uniform(-1.85,1.85),rng.uniform(-1.85,1.85),rng.uniform(-.78,.78)])
                    p=np.vstack([p,extra])
                yield n,drop,np.r_[p.ravel(),L]
def main():
    out=search.ROOT/'batch-neighbors';out.mkdir(exist_ok=True);rng=np.random.default_rng(180718)
    best=float('inf');besti=-1; starts=close=0;t=time.perf_counter();hist={}
    with (out/'runs.csv').open('w',buffering=1) as f:
        writer=csv.writer(f); writer.writerow(['n','deleted','repaired_side'])
        for i,(n,drop,x) in enumerate(cases(rng)):
            q=x[:-1].reshape(18,3)
            q[:,2]=(q[:,2]+np.pi/4)%(np.pi/2)-np.pi/4
            fix=(abs(q[:,2])<1e-6)&(rng.random(18)<rng.uniform(.07,.88))
            q[fix,2]=0
            # Escape grid or symmetry locks with local independent displacements.
            q[:,:2]+=rng.normal(0,rng.uniform(.02,.22),(18,2))
            q[~fix,2]+=rng.normal(0,rng.uniform(.02,.27),sum(~fix))
            locked=sum(1<<k for k in np.flatnonzero(fix))
            for w,steps in [(1.6,125),(12,130),(100,125),(1000,100)]:
                search._lib.polish(search.ptr(x),w,int(locked),steps)
            c=search.feasible_rescale(x)
            if c[-1]<search.S+.05:
                b=search.feasible_rescale(search.slsqp(x,locked))
                if c[-1]>b[-1]:c=b
            writer.writerow([n,' '.join(map(str,drop)),format(c[-1],'.15f')])
            starts+=1; close+=int(c[-1]<search.S+.01)
            hist[n]=min(float(c[-1]),hist.get(n,100.))
            if c[-1]<best:
                best=float(c[-1]); besti=i; search.atomic_write(out/'best.json',search.doc(c))
            if c[-1]<search.S-1e-10:print('CANDIDATE',i,n,best,flush=True);break
            if starts%1000==0:print(starts,best,time.perf_counter()-t,flush=True)
    report=dict(rng=180718,starts=starts,best=best,best_index=besti,by_size=hist,within_0_01=close,seconds=time.perf_counter()-t)
    search.atomic_write(out/'summary.json',report);print(report)
if __name__=='__main__':main()
