"""Directed search in surviving marginal pose enclosures of orbit 55."""
import argparse
import ctypes
import csv
import json
import math
from pathlib import Path
import time
import numpy as np
import rack_search as rs
from chart_lp import polish_guarded

rs.LIB.set_leaf.argtypes=[rs.prior.PTR,ctypes.c_double]
def tighten(points,rng):
    # Average several hull vertices: a point in the convex enclosure, with sampling
    # biased alternately towards extreme or central permissible tile centers.
    if len(points)<=2 or rng.random()<.28:
        return points[rng.integers(len(points))]
    r=rng.dirichlet(np.full(len(points),rng.choice([.1,.5,2.])))
    return r@points

def prep(raw):
    result=[]
    for owner, bands in sorted(raw):
        states=[]
        for (k,d), vertices in bands:
            points=np.array(vertices)*1e-6-rs.U/2
            lo,hi=2*math.atan(k/d),2*math.atan((k+1)/d)
            states.append((lo,hi,points,points.min(axis=0),points.max(axis=0)))
        result.append(states)
    return result

def draw(pre,rng,choice):
    x=np.empty(55);x[-1]=rs.H
    limits=np.zeros((54,2))
    for i,states in enumerate(pre):
        if choice==0:
            pos=rng.integers(len(states))
        else:
            likely=np.array([((s[0]+s[1])*0.5+np.pi/4)%(np.pi/2)-np.pi/4 for s in states])
            targets=([0,.424031] if choice==1 else
                     [0,-.424031] if choice==2 else
                     [0,.424031,-.424031,np.pi/4] if choice==3 else
                     [0,rng.uniform(-.75,.75)])
            dist=np.min(abs(likely[:,None]-targets),axis=1)
            scale=rng.choice([.009,.035,.09])
            weights=np.exp(-dist/scale);weights/=weights.sum()
            pos=rng.choice(len(states),p=weights)
        lo,hi,points,mn,mx=states[pos]
        theta=rng.uniform(lo,hi)
        for t in (0,math.pi/2,.4240310394907405,math.pi/2-.4240310394907405,math.pi/4):
            if lo-1e-13<=t<=hi+1e-13 and rng.random()<.8:
                theta=t;break
        x[3*i:3*i+2]=tighten(points,rng);x[3*i+2]=theta
        limits[3*i:3*i+2,:]=np.stack((mn,mx),axis=1)
        limits[3*i+2,:]=(lo,hi)
    return x,limits

def run(args):
    data=json.loads(Path('leaf55.json').read_text())
    data=[(r['name'],prep(r['cells'])) for r in data if r['cells']]
    mask=rs.canonical_masks[55]
    idx=[i for i in range(21) if mask>>i&1]+[i for i in range(21) if not mask>>i&1]
    rk=np.ascontiguousarray(rs.grid[idx].ravel());home,holes=rs.U*rs.grid[idx[:18]],rs.U*rs.grid[idx[18:]]
    rng=np.random.default_rng(args.rng);out=args.out;out.mkdir(exist_ok=True)
    start=time.monotonic();overall=100.;own=100.;ag=100.;globalraw=100.; bins={}
    with (out/'rounds.csv').open('w',buffering=1) as f:
        log=csv.writer(f)
        log.writerow(('i','leaf','angle_bias','assigned_raw','min_assigned_gap','assigned_L','assigned_orbit','released_raw','min_released_gap','released_L','released_orbit'))
        for i in range(args.count):
            leaf,pre=data[i%len(data)]; style=int(rng.integers(5))
            x,box=draw(pre,rng,style);box=np.ascontiguousarray(box.ravel())
            for pw,bw,nw,eps,capacity in [(2.,2.,1.5,.001,95),(20.,1.2,2,.0001,110),
                                             (100.,.05,2,.000002,130),(800.,0.,2,.00000001,145)]:
                rs.LIB.set_leaf(rs.prior.ptr(box),bw);rs.place_marks(rk,2.,nw,eps)
                rs.pol(x,pw,capacity)
            ass=x.copy(); initial=rs.prior.feasible_rescale(ass)
            if initial[-1]<rs.H+.025 and i%4==0:
                hold=np.flatnonzero(abs(np.sin(2*ass[:-1].reshape(18,3)[:,2]))<1e-7)
                ass=polish_guarded(ass,home,holes,hold,1.0e-10)
            fixed=rs.prior.feasible_rescale(ass);tag=rs.midpoint_mark_orbit(fixed)
            if tag==55 and fixed[-1]<own:
                own=fixed[-1];rs.prior.atomic_write(out/'best-assigned.json',rs.layout(fixed))
            if ag>ass[-1]:
                ag=ass[-1];rs.prior.atomic_write(out/'best-assigned-raw.json',rs.layout(ass))
            rs.place_marks(rk,0.,0.,0.)
            for w in [140.,1600.,17000.]:rs.pol(x,w,110)
            rr=rs.prior.feasible_rescale(x)
            if rr[-1] < rs.H+.011 or i%79==0:
                z=rs.prior.slsqp(x,0);zz=rs.prior.feasible_rescale(z)
                if zz[-1] < rr[-1]: x,rr=z,zz
            if globalraw>x[-1]:
                globalraw=x[-1];rs.prior.atomic_write(out/'raw-best.json',rs.layout(x))
            if rr[-1]<overall:
                overall=rr[-1];rs.prior.atomic_write(out/'best.json',rs.layout(rr))
            if overall<rs.H-2e-12:
                print('COUNTEREXAMPLE CANDIDATE',i,overall,flush=True);break
            rtag=rs.midpoint_mark_orbit(rr); bins[tag]=bins.get(tag,0)+1
            log.writerow([i,leaf,style,ass[-1],rs.prior.gaps(ass).min(),fixed[-1],tag,x[-1],rs.prior.gaps(x).min(),rr[-1],rtag])
            if (i+1)%300==0: print(i+1,own,overall,flush=True)
    rs.prior.atomic_write(out/'summary.json',dict(seed=args.rng,leaf_starts=i+1,side_assigned_55=own,side_free=overall,assigned_orbits=bins,seconds=time.monotonic()-start))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,required=True)
    parser.add_argument('--rng',type=int,required=True);parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args())
