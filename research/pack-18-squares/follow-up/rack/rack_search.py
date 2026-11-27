"""Counterexample search from a D4 orbit of 18 assigned interior marks.
Centers, angles, and container size move continuously. No known-layout seeds.
"""
import argparse
import csv
import ctypes
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "search-history"))
import search as prior

H = (7 + math.sqrt(7)) / 2
U = 4.822876
LIB = ctypes.CDLL(str(Path(os.environ["PACK18_RUN"]) / "packing.dylib"))
LIB.polish.argtypes = [prior.PTR, ctypes.c_double, ctypes.c_uint, ctypes.c_int]
LIB.set_rack.argtypes = [prior.PTR, ctypes.c_double, ctypes.c_double, ctypes.c_double]

def transforms(x, y):
    return ((x,y),(2000-y,x),(2000-x,2000-y),(y,2000-x),
            (2000-x,y),(x,2000-y),(y,x),(2000-y,2000-x))

marks = sorted({a for p in [(390,390),(617,617),(797,359),(1000,716),(1000,1000)]
                for a in transforms(*p)})
sym = [[marks.index(transforms(*p)[k]) for p in marks] for k in range(8)]
bits = (1 << 21) - 1
def canonical(holes):
    return min(tuple(sorted(g[i] for i in holes)) for g in sym)
triples = list(itertools.combinations(range(21), 3))
canonical_masks = sorted({bits - sum(1 << i for i in canonical(t)) for t in triples})
def orbit(holes):
    return canonical_masks.index(bits - sum(1 << i for i in canonical(holes)))
grid = (np.asarray(marks)/2000.0 - .5)
MIXED = (53,55,82,92,115,137)

def midpoint_mark_orbit(x):
    xy=x[:-1].reshape(18,3)
    ax=xy[:,2]; c=np.cos(ax)[:,None]; s=np.sin(ax)[:,None]
    dx=grid[None,:,0]*x[-1]-xy[:,None,0]
    dy=grid[None,:,1]*x[-1]-xy[:,None,1]
    dist=np.maximum(abs(c*dx+s*dy), abs(c*dy-s*dx))
    owner=dist.argmin(axis=1)
    n_unique=len(set(owner))
    if n_unique<18: return -1
    holes=tuple(sorted(set(range(21))-set(owner)))
    return orbit(holes) if dist[np.arange(18),owner].max() < .5 else -1

def layout(x):
    return prior.doc(x)

def pol(x, weight, budget, locked=0):
    return LIB.polish(prior.ptr(x), weight, locked, budget)

def place_marks(rk, owner, close, margin):
    LIB.set_rack(prior.ptr(rk),owner,close,margin)

def random_pose(rk, rng):
    L=rng.uniform(4.65,5.45)
    xs=rk[:18]*L+rng.normal(0,rng.uniform(.09,.4),size=(18,2))
    direction=rng.choice((-1.,1.))
    style=int(rng.integers(5))
    if style==0: theta=rng.uniform(-.78,.78,18)
    if style==1: theta=rng.choice([0.,.424031,-.424031,math.pi/4],size=18)
    if style==2: theta=np.ones(18)*direction*rng.uniform(.15,.57) +rng.normal(0,.09,18)
    if style==3: theta=np.zeros(18);theta[rng.random(18)<.32]=direction*rng.uniform(.16,.6)
    if style==4: theta=rng.choice((-.5,.5),size=18)+rng.normal(0,.3,18)
    return np.r_[np.column_stack((xs,theta)).reshape(-1),L]

def perturb(x,rng):
    x=x.copy(); p=x[:-1].reshape(18,3)
    style=int(rng.integers(6))
    if style==0:
        p[:,:2] += rng.normal(0,.15,(18,2));p[:,2]+=rng.normal(0,.3,18)
    if style==1:
        i=int(rng.integers(18)); g=np.linalg.norm(p[:,:2]-p[i,:2],axis=1)<rng.uniform(.7,2)
        p[g,:2]+=rng.normal(0,.2,(g.sum(),2));p[g,2]+=rng.normal(0,.46,g.sum())
    if style==2:
        for i in rng.choice(18,size=rng.integers(3,10),replace=False):
            p[i,2]+=rng.uniform(-.75,.75);p[i,:2]+=rng.uniform(-.22,.22,2)
    if style==3:
        i=int(rng.integers(18));d=p[:,:2]-p[i,:2];g=np.linalg.norm(d,axis=1)<rng.uniform(1.3,2.6)
        a=rng.uniform(-.45,.45);c,s=math.cos(a),math.sin(a)
        p[g,:2]=p[i,:2]+d[g]@np.array([[c,s],[-s,c]]);p[g,2]+=a
    if style==4:
        p[:,2]*=-1;p[:,:2]+=rng.normal(0,rng.uniform(.01,.14),(18,2))
    if style==5:
        v=np.array([np.cos(a:=rng.uniform(0,2*np.pi)),np.sin(a)]);g=(p[:,:2]@v)>rng.uniform(-1,1)
        p[g,:2]+=rng.uniform(-.45,.45,2);p[g,2]+=rng.uniform(-.44,.44)
    return x

def run(orbit_id,seed,count,out,external):
    rng=np.random.default_rng(seed)
    mask=canonical_masks[orbit_id]
    order=[i for i in range(21) if mask>>i&1]+[i for i in range(21) if not mask>>i&1]
    rk=np.ascontiguousarray(grid[order].reshape(-1))
    marks2=rk.reshape(21,2)
    initial=[]
    for path in external:
        pos=prior.load(path);xy=pos[:-1].reshape(18,3)
        diff=marks2[:18,None,:]*pos[-1]-xy[None,:,:2]
        ii,jj=linear_sum_assignment(np.sum(diff**2,axis=2))
        initial.append(np.r_[xy[jj].ravel(),pos[-1]])
    pool=[]; best_pred=math.inf; best=math.inf; best_home=math.inf
    out.mkdir(parents=True,exist_ok=True)
    start=time.monotonic(); homes=0; buckets={}
    with (out/'rounds.csv').open('w',buffering=1) as f:
        wr=csv.writer(f)
        wr.writerow(('index','start','assigned','tag_before_release','repaired_before_release','tag_after_release','repaired_after_release','raw_side','min_raw_gap','slsqp'))
        for i in range(count):
            if initial and rng.random()<.25:
                x=perturb(initial[rng.integers(len(initial))],rng);mode='orbit-transfer'
            elif not pool or rng.random()<.36:
                x=random_pose(marks2,rng); mode='fresh'
            else:
                pos=pool[int(rng.integers(len(pool)))][1]
                x=perturb(pos,rng);mode='adaptive'
            # An initial owner buffer helps avoid dropping prescribed mark assignments.
            w=rng.choice([.25,1.,3.]); nearest=rng.choice([.30,1.5,5.])
            for pw,nw,m,physical,budget in [(w,nearest,.025,2.,110),(w,nearest,.010,18.,140),
                                             (w,nearest,.001,120.,160),(w*1.5,nearest,.0005,900.,160)]:
                place_marks(rk,pw,nw,m);pol(x,physical,budget)
            held=prior.feasible_rescale(x)
            held_tag=midpoint_mark_orbit(held); held_side=held[-1]
            if held_tag==orbit_id and held_side<best_home:
                best_home=held_side;prior.atomic_write(out/'best-assigned.json',layout(held))
            homes+=int(held_tag==orbit_id)
            # Archive diverse owner-conditioned basins; retain by repaired value with an
            # explicit penalty when the nearest-marker orbit has changed.
            score=held_side+(.12 if held_tag!=orbit_id else 0)
            if not any(abs(score-z)<.0015 for z,_ in pool):
                pool.append((score,x.copy()));pool.sort(key=lambda z:z[0]);pool=pool[:36]
            # Remove all mark terms before the final physical search.
            place_marks(rk,0.,0.,0.)
            pol(x,75.,90);pol(x,1200.,95);pol(x,14000.,80)
            rough=prior.feasible_rescale(x)
            precise=rough; polished=False
            if rough[-1]<H+.009 or (rough[-1]<H+.055 and i%29==0) or (i%401==0):
                # An unrestricted cleanup and a boundary-axis cleanup are independent.
                precise=prior.feasible_rescale(prior.slsqp(x,0))
                q=x.copy(); p=q[:-1].reshape(18,3);p[:,2]=(p[:,2]+np.pi/4)%(np.pi/2)-np.pi/4
                near=abs(p[:,2])<.018
                p[near,2]=0
                alt=prior.feasible_rescale(prior.slsqp(q,sum(1<<int(k) for k in np.flatnonzero(near))))
                precise=min((precise,alt,rough),key=lambda y:y[-1]);polished=True
            final_tag=midpoint_mark_orbit(precise);buckets[final_tag]=buckets.get(final_tag,0)+1
            raw_gap=float(prior.gaps(x).min())
            wr.writerow((i,mode,orbit_id,held_tag,'%.16f'%held_side,final_tag,'%.16f'%precise[-1],
                         '%.16f'%x[-1], '%.8g'%raw_gap,int(polished)))
            if precise[-1]<best:
                best=precise[-1];prior.atomic_write(out/'best.json',layout(precise))
            if x[-1]<best_pred:
                best_pred=float(x[-1]);prior.atomic_write(out/'raw-best.json',layout(x))
            if best<H-2e-12:
                print('COUNTEREXAMPLE CANDIDATE',out,i,best,flush=True);break
            if (i+1)%500==0:print(out.name,i+1,'best',best,'assigned',best_home,flush=True)
    prior.atomic_write(out/'summary.json',dict(assigned_orbit=orbit_id,seed=seed,attempted=i+1,
      matched_pre_release=homes,best_assigned=best_home if np.isfinite(best_home) else None,
      best_after_release=best,raw_minimum=best_pred,end_orbits=buckets,elapsed_seconds=time.monotonic()-start,
      external_seeds=[str(p) for p in external]))
    print(out.name,'done',i+1,best,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--orbit',type=int,required=True);ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--count',type=int,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--external',type=Path,nargs='*',default=[])
    a=ap.parse_args();run(a.orbit,a.seed,a.count,a.out,a.external)
