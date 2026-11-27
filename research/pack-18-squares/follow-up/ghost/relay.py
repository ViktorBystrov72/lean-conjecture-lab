"""Exchange one or three tiles by area-preserving vacancy continuation."""

import argparse
import csv
import ctypes
from decimal import Decimal, localcontext
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

from run import HERE, TARGET, gradient_control


def initial_sites(q, keep, old, rng, side, direction):
    new=[]
    for j in old:
        # Candidate sites are scored against the retained tiles, not against
        # the departing tiles, so future ghosts may invade an occupied hole.
        targets=np.vstack([rng.uniform(-side/2+.55,side/2-.55,(100,2)),
                           q[j,:2]+rng.normal(0,.65,(100,2))])
        if direction:
            targets=np.vstack((targets,q[old,:2].mean(axis=0)+rng.normal(0,.7,(180,2))))
        targets=np.clip(targets,-side/2+.51,side/2-.51)
        initial=np.vstack([q[keep,:2], *[np.array([v[:2]]) for v in new]])
        clearance=np.min(np.sum((initial[None,:,:]-targets[:,None,:])**2,axis=2),axis=1)
        order=np.argsort(-clearance)
        index=order[min(len(order)-1,int(rng.exponential(4.)))]
        new.append([*targets[index],rng.uniform(-.78,.78)])
    return np.asarray(new)


def trial(seed, k, rng, mode, lib, search):
    p=np.asarray(seed["squares"],dtype=float).copy()
    side=seed["side"];p[:,:2]-=side/2
    anchor=rng.integers(18)
    if mode%2:
        scores=np.linalg.norm(p[:,:2]-p[anchor,:2],axis=1)+rng.normal(0,.4,18)
        old=np.argsort(scores)[:k]
    else:old=rng.choice(18,k,replace=False)
    new=np.arange(18,18+k)
    keep=np.array([i for i in range(18) if i not in old])
    sites=initial_sites(p,keep,old,rng,side,mode//2)
    q=np.vstack((p,sites))
    q[:18,:2]+=rng.normal(0,rng.uniform(0,.05),(18,2))
    q[:18,2]+=rng.normal(0,rng.uniform(.01,.12),18)
    x=np.r_[q.ravel(),side]
    if mode in (0,1):
        steps=(.03,.15,.3,.48,.65,.8,.93,.985)
    else:
        steps=(.04,.22,.39,.56,.70,.41,.56,.79,.94,.985)
    exponent=rng.uniform(.5,1.9,k)
    for i,t in enumerate(steps):
        phi=t**exponent*(math.pi/2)
        sizes=np.ones(18+k)
        sizes[old]=np.cos(phi);sizes[new]=np.sin(phi)
        lib.relax_ghosts(search.ptr(x),18+k,search.ptr(sizes),4+10*i/len(steps),100)
    v=np.r_[x[:-1].reshape(18+k,3)[np.r_[keep,new]].ravel(),x[-1]]
    # Independent rotations are released throughout the final unit-size stages.
    for weight,iterations in ((1.8,120),(12.,120),(90.,120),(1000.,125)):
        search._lib.polish(search.ptr(v),weight,0,iterations)
    if search.feasible_rescale(v)[-1]<TARGET+.018:
        z=search.slsqp(v,0)
        if search.feasible_rescale(z)[-1]<=search.feasible_rescale(v)[-1]:v=z
        # Recover flat contacts near the nonsmooth absolute-value cusp.
        # Every snapped angle is freed again before evaluating the trial.
        z=v.copy();angles=z[:-1].reshape(18,3)[:,2]
        angles[:]=(angles+np.pi/4)%(np.pi/2)-np.pi/4
        lock=np.abs(angles)<.014
        angles[lock]=0.
        fixed=sum(1<<int(a) for a in np.flatnonzero(lock))
        for w in (50.,1000.,100000.):
            search._lib.polish(search.ptr(z),w,fixed,110)
        z=search.slsqp(z,fixed)
        free=search.slsqp(z,0)
        if search.feasible_rescale(free)[-1]<=search.feasible_rescale(v)[-1]:v=free
    return v, tuple(sorted(int(i)+1 for i in old))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--study",type=Path,default=HERE.parents[1])
    parser.add_argument("--library-dir",type=Path,required=True)
    parser.add_argument("--starts",type=int,default=1500)
    parser.add_argument("--extra",type=int,choices=(1,3),required=True)
    args=parser.parse_args()
    study=args.study.resolve()
    sys.path[:0]=[str(study/"search-history"),str(study/"follow-up/patch")]
    os.environ["PACK18_RUN"]=str(args.library_dir.resolve())
    import search
    import exact
    ptr=search.PTR
    lib=ctypes.CDLL(str((args.library_dir/"ghost.dylib").resolve()))
    lib.relax_ghosts.argtypes=[ptr,ctypes.c_int,ptr,ctypes.c_double,ctypes.c_int]
    lib.relax_ghosts.restype=None
    seed=json.loads(args.source.read_text())
    args.output.mkdir(parents=True,exist_ok=False);best=None;best_num=-1
    masks=set();raw_hits=0;near=0
    with (args.output/"runs.csv").open("w") as log:
        writer=csv.writer(log);writer.writerow(("index","removed","raw","min_gap","repaired_side"))
        for i in range(args.starts):
            rng=np.random.default_rng(np.random.SeedSequence((182117,args.extra,i)))
            x,mask=trial(seed,args.extra,rng,i%4,lib,search)
            data=search.doc(x)
            cert=min((exact.repair(data["squares"],digits=17,slope_limit=d) for d in (10**8,10**12)),key=lambda row:row[0])
            side,tiles=cert
            writer.writerow([i,"/".join(map(str,mask)),format(float(x[-1]),".17g"),format(float(min(search.gaps(x))),".17g"),format(float(side),".17g")])
            masks.add(mask);raw_hits+=int(float(x[-1])<TARGET);near+=int(float(side)<TARGET+1e-7)
            if best is None or side<best:
                best=side;best_num=i
                exact.verify(side,tiles)
                (args.output/"best-rational.json").write_text(json.dumps({"side":str(side),"squares":[list(map(str,row)) for row in tiles]},indent=2)+"\n")
                (args.output/"best-source.json").write_text(json.dumps(data,indent=2)+"\n")
                if exact.below(side):raise SystemExit(f"STRICT VERIFIED IMPROVEMENT {side}")
    with localcontext() as ctx:
        ctx.prec=65
        number=Decimal(best.numerator)/Decimal(best.denominator);diff=number-(7+Decimal(7).sqrt())/2
    result=dict(extra=args.extra,seed=182117,starts=args.starts,distinct_departing_masks=len(masks),
                input_sha256=__import__('hashlib').sha256(args.source.read_bytes()).hexdigest(),best_index=best_num,
                nominal_below=raw_hits,within_1e_7=near,best_exact=str(best),best_decimal=str(number),difference_from_H=str(diff))
    print(result,flush=True)
    (args.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    main()
