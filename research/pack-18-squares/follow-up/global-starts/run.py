"""Fresh starts for joint deformation of 18 squares in a soft parallelogram."""
import argparse
from collections import Counter
import ctypes
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = Path(os.environ.get("PACK18_STUDY", HERE.parent.parent))
sys.path[:0] = [str(STUDY/"search-history"),str(STUDY/"follow-up"/"patch")]
import search
import exact

BUILD = Path(os.environ["PACK18_RUN"])
lib = ctypes.CDLL(str(BUILD / "chamber.dylib"))
lib.relax.argtypes = [search.PTR, search.PTR, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
lib.relax.restype = ctypes.c_double
lib.energy_and_force.argtypes = [search.PTR,search.PTR,ctypes.c_double,ctypes.c_double,ctypes.c_double,search.PTR]
lib.energy_and_force.restype = ctypes.c_double
FAMILIES = ("maximin", "grain-boundary", "stripes", "shells")


def maximin(rng, n, taken):
    result = list(taken)
    for _ in range(n):
        targets = rng.uniform(-2.1,2.1,(32,2))
        if result:
            distance = ((targets[:,None,:] - np.array(result)[None,:,:])**2).sum(2).min(1)
            choice = np.argmax(distance*rng.uniform(.8,1.15,32))
        else:
            choice = 0
        result.append(targets[choice])
    return np.array(result)


def seed_layout(rng, family):
    a = rng.uniform(-math.pi/4,math.pi/4,18)
    if family == "maximin":
        xy = maximin(rng,18,[])
    elif family == "grain-boundary":
        normal = rng.normal(size=2)
        normal /= np.linalg.norm(normal)
        offset = rng.uniform(-.65,.65)
        cols, angles = [], []
        for side in (-1,1):
            theta = rng.uniform(-.72,.72)
            c,s = math.cos(theta),math.sin(theta)
            field = np.array([(i,j) for i in range(-4,5) for j in range(-4,5)],dtype=float)
            field = (field+rng.uniform(-.5,.5,2))@np.array([[c,s],[-s,c]])*rng.uniform(.87,1.08)
            choose = (np.max(np.abs(field),1)<2.17) & (side*(field@normal-offset)>=-.06)
            cols.extend(field[choose]);angles.extend([theta]*np.sum(choose))
        if len(cols) < 18:
            xy=maximin(rng,18-len(cols),cols)
            a[:len(cols)]=angles
        else:
            keep=rng.choice(len(cols),size=18,replace=False)
            xy=np.array(cols)[keep];a=np.array(angles)[keep]
        xy += rng.normal(0,.105,xy.shape); a += rng.normal(0,.17,len(xy))
    elif family=="stripes":
        rows=int(rng.integers(3,7)); sizes=np.full(rows,2)
        for _ in range(18-2*rows):
            sizes[rng.choice(np.flatnonzero(sizes<7))] += 1
        ys=np.linspace(-2.0,2.0,rows)
        cols=[]; angles=[]
        for y,n in zip(ys,sizes):
            phase=rng.uniform(-.5,.5)
            slope=rng.uniform(-.27,.27)
            tilt=rng.uniform(-.65,.65)
            for x in np.linspace(-2.,2.,n)+phase:
                cols.append((x,y+slope*x));angles.append(tilt+rng.normal(0,.13))
        xy=np.array(cols)+rng.normal(0,.1,(18,2)); a=np.array(angles)
    else:
        inner=int(rng.integers(4,9))
        xy=[]
        for size, r in ((inner,rng.uniform(.8,1.35)),(18-inner,rng.uniform(2.,2.4))):
            phase=rng.uniform(0,2*math.pi)
            for t in phase+np.linspace(0.,2*math.pi,size,endpoint=False):
                point=np.array([math.cos(t),math.sin(t)])
                point *= r/(np.abs(point).max()**rng.uniform(0.,.9))
                xy.append(point+rng.normal(0,.13,2))
        xy=np.array(xy)
    return np.column_stack([xy,a]).copy()


def fingerprint(q):
    # Canonicalize unlabeled position and direction modulo the eight box symmetries.
    old=q.copy(); options=[]
    for flip in (1,-1):
        xy=old[:,:2].copy(); xy[:,1]*=flip; a=flip*old[:,2]
        for _ in range(4):
            four=np.column_stack([xy,np.cos(4*a),np.sin(4*a)])
            vals=np.rint(1e8*four).astype('<i8')
            options.append(vals[np.lexsort(vals.T[::-1])].tobytes())
            xy=np.column_stack([-xy[:,1],xy[:,0]]); a=a+math.pi/2
    return hashlib.sha256(min(options)).hexdigest()[:24]


def transform(q, prev, nxt):
    # Co-move the centres with the chamber, bringing each tile's own angle along
    # with the image of its first edge under the same linear map.
    w,h,k=prev; W,H,K=nxt
    sx,sy=W/w,H/h
    factor=K*sy-k*sx
    x=q[:,0].copy(); y=q[:,1].copy()
    q[:,0]=sx*x+factor*y; q[:,1]=sy*y
    c,s=np.cos(q[:,2]),np.sin(q[:,2])
    q[:,2]=np.arctan2(sy*s,sx*c+factor*s)


def relax(q, radii, chamber, steps):
    lib.relax(search.ptr(q), search.ptr(np.ascontiguousarray(radii)),
              *chamber, steps)


def round_layout(q):
    x=np.r_[q.ravel(),4.9]
    for weight, steps in ((3.0,90),(25.,125),(250.,115),(1800.,80)):
        search._lib.polish(search.ptr(x), weight, 0, steps)
    best=search.feasible_rescale(x)
    if best[-1]<4.91 or x[-1]<search.S+.018:
        polished=search.slsqp(x,0)
        out=search.feasible_rescale(polished)
        if out[-1]<best[-1]:
            best=out
    return best


def run_trial(rng,q):
    radii=np.full(18,.5)
    phases=rng.uniform(0,2*math.pi,18)
    aspect=rng.uniform(-.18,.18); shear=rng.uniform(-.29,.29)
    def chamber(side, elliptic, shear):
        return side*math.exp(elliptic), side*math.exp(-elliptic), shear
    cur=chamber(5.35,0,0)
    # A deliberately asynchronous inflation sequence. Every tile attains size one.
    for j in range(9):
        t=j/8
        nxt=chamber(5.35-.51*t,aspect*math.sin(math.pi*t),shear*math.sin(2*math.pi*t))
        transform(q,cur,nxt);cur=nxt
        r=.5*(.6+.4*t+.15*t*(1-t)*np.cos(phases+2*math.pi*t))
        relax(q,r,nxt,85)
    best=round_layout(q)
    for j in range(2):
        # Frustrate pre-existing contacts by changing both outer wall angles
        # and aspect ratio, then restore the true square chamber.
        amp=rng.uniform(.15,.53)*rng.choice([-1.,1.])
        elliptic=rng.uniform(-.24,.24)
        pump=rng.uniform(.08,.32)
        q[:,:2]+=rng.normal(0,.10,(18,2));q[:,2]+=rng.normal(0,.14,18)
        for i in range(1,9):
            t=i/8
            crush=math.sin(math.pi*t)
            nxt=chamber(4.84-pump*crush,elliptic*crush,amp*math.sin(2*math.pi*t))
            transform(q,cur,nxt);cur=nxt
            r=radii*(1+.14*crush*np.cos(phases+2*math.pi*t+j))
            relax(q,r,nxt,80)
        candidate=round_layout(q)
        if candidate[-1]<best[-1]:
            best=candidate
    return best


def derivative_test():
    rng=np.random.default_rng(82915)
    x=np.column_stack([rng.uniform(-2.6,2.6,(18,2)),rng.uniform(-.73,.73,18)]).ravel()
    rad=rng.uniform(.32,.55,18)
    d=np.zeros(54)
    def calc(x,d):
        return lib.energy_and_force(search.ptr(x),search.ptr(rad),4.63,4.94,.32,search.ptr(d))
    calc(x,d)
    errors=[]; buff=np.empty(54)
    for k in range(54):
        u=x.copy();u[k]+=1e-6
        v=x.copy();v[k]-=1e-6
        approx=(calc(u,buff)-calc(v,buff))/2e-6
        errors.append(abs(approx+d[k]))
    if max(errors)>1e-7: raise ValueError(max(errors))
    return max(errors)


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    best=None;counts=Counter();closest={};rawmin=100
    gtest=derivative_test()
    with (out/"runs.csv").open("w",buffering=1) as f:
        wr=csv.writer(f);wr.writerow(["seed","family","initial_d4_sha","floating_side","rational_side_approx"])
        for seed in range(args.seed,args.seed+args.count):
            family=FAMILIES[seed%4];rng=np.random.default_rng(seed)
            q=seed_layout(rng,family)
            fp=fingerprint(q)
            x=run_trial(rng,q)
            pos=search.doc(x)["squares"]
            side,tiles=exact.repair(pos)
            counts[family]+=1
            if best is None or side<best:
                exact.verify(side,tiles)
                best=side
                (out/"best-rational.json").write_text(json.dumps({"side":str(side),"squares":[[str(x),str(y),str(t)] for x,y,t in tiles]},indent=2)+"\n")
                (out/"best-numerical.json").write_text(json.dumps({"seed":seed,"family":family,"side":float(x[-1]),"squares":pos},indent=2)+"\n")
            if family not in closest or closest[family]>side:
                closest[family]=side
            rawmin=min(rawmin,float(x[-1]))
            wr.writerow([seed,family,fp,format(x[-1],'.17g'),format(float(side),'.17g')])
            if exact.below(side):
                exact.verify(side,tiles)
                print("VERIFIED STRICT IMPROVEMENT",seed,side,flush=True);break
    report={"seed":args.seed,"requested":args.count,"counts":dict(counts),
            "gradient_control_max_abs_error":gtest,"floating_min":rawmin,
            "best_rational":str(best),"by_family":{k:str(v) for k,v in closest.items()},
            "below_target":exact.below(best),"runs_sha256":hashlib.sha256((out/'runs.csv').read_bytes()).hexdigest()}
    (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(args.seed,dict(counts),float(best),exact.below(best),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,required=True)
    parser.add_argument("--count",type=int,required=True)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args())
