"""Search 18 squares by shrinking ghosts within 19- and 21-square donors."""
import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import sys
import time
from urllib.request import urlopen

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
PIN = "c5775bae40085f67f4c30f8916b0d6e998c304ab"
INPUTS = {19: "f72ffb931d0237a2f5a4579329d58d9f2a90482debc4feb2cd31482a157a6fd9",
          21: "d877c28157a9346295cc48746471d6663a99559941a49918106bd6270c905762"}
TARGET = (7 + math.sqrt(7))/2


def donor(n, source):
    name=f"n-{n:03d}.yaml"
    if source:
        raw=(source/name).read_bytes()
    else:
        url=f"https://raw.githubusercontent.com/jlevy/squares/{PIN}/packing/witnesses/known-best/{name}"
        with urlopen(url,timeout=45) as response:
            raw=response.read()
    if hashlib.sha256(raw).hexdigest()!=INPUTS[n]:
        raise ValueError(f"unrecognized coordinates for {name}")
    data=yaml.safe_load(raw)["witness"]
    def number(s):return float(Fraction(str(s)))
    side=number(data["side"])
    positions=[]
    for tile in data["squares"]:
        if "center" in tile:
            x,y=map(number,tile["center"])
            theta=math.radians(number(tile["angle"]))
        else:
            points=np.array([[number(k) for k in row] for row in tile["corners"]])
            x,y=points.mean(axis=0); dx,dy=points[1]-points[0]
            theta=math.atan2(dy,dx)
        positions.append([x-side/2,y-side/2,math.remainder(theta,math.pi/2)])
    return np.array(positions),side


def symmetries(poses):
    """Induced permutations under D4 at numerical tolerance 1e-8 (report only)."""
    result=[]
    for turn in range(4):
        for sign in (1,-1):
            perm=[]
            for x,y,a in poses:
                y*=sign;a*=sign
                for _ in range(turn):
                    x,y=-y,x
                hits=[i for i,(X,Y,b) in enumerate(poses)
                      if math.hypot(x-X,y-Y)<1e-8 and abs(math.remainder(a-b,math.pi/2))<1e-8]
                if len(hits)!=1:break
                perm.append(hits[0])
            if len(perm)==len(poses):
                t=tuple(perm)
                if t not in result:result.append(t)
    return result


def gradient_control(lib,search):
    rng=np.random.default_rng(1401999)
    for n in (19,21):
        x=np.r_[np.column_stack([rng.uniform(-2,2,(n,2)),rng.uniform(-.7,.7,n)]).ravel(),4.1]
        sides=rng.uniform(.15,1,n)
        g=np.empty_like(x); direction=rng.normal(size=x.shape)
        def energy(p,dest):
            return lib.ghost_energy(search.ptr(p),search.ptr(dest),n,search.ptr(sides),7.)
        f=energy(x,g)
        h=1e-7; aux=np.empty_like(x)
        observed=(energy(x+h*direction,aux)-energy(x-h*direction,aux))/(2*h)
        predicted=float(direction@g)
        if abs(observed-predicted)>1e-6*(1+abs(predicted)):
            raise ValueError((n,f,predicted,observed))


def solve_one(donor_poses,side,ids,rng,mode,lib,search):
    n=len(donor_poses)
    pos=donor_poses.copy()
    # A donor appears only as an initial position. The ghosts also move.
    strength=rng.choice((.008,.025,.06,.12,.22))
    pos[:,:2]+=rng.normal(0.,strength,(n,2))
    pos[:,2]+=rng.normal(0.,strength*.7,n)
    x=np.r_[pos.ravel(), side]
    all_ids=np.arange(n)
    ghost=np.array(ids);survivors=np.delete(all_ids,ghost)
    exponents=np.ones(len(ghost))
    if len(ghost)==3 and mode!=0:
        exponents=np.array((.55,1.,1.85));rng.shuffle(exponents)
    if mode==2:
        schedule=(1,.82,.64,.39,.26,.62,.43,.22,.08)
    elif mode==3:
        schedule=(1,.84,.72,.58,.44,.31,.16,.045)
    else:
        schedule=(1,.86,.68,.49,.31,.16,.05)
    for k,f in enumerate(schedule):
        sides=np.ones(n)
        sides[ghost]=f**exponents
        if k==2 or (k==5 and mode>=2):
            # Rearrange adjacent squares into newly freed space with a
            # localized deformation, then re-optimize the entire donor.
            q=x[:-1].reshape(n,3)
            for j in ghost:
                rel=q[:,:2]-q[j,:2]
                taper=np.exp(-np.sum(rel*rel,axis=1)/1.85)
                phi=rng.uniform(-.23,.23)*taper
                q[:,:2]+=np.column_stack([-rel[:,1]*phi, rel[:,0]*phi])
                q[:,2]+=phi*.55
                q[j,:2]+=rng.normal(0,.18,2)
            q[:,:2]+=rng.normal(0,.018,(n,2))
        w=4+12*k/len(schedule)
        lib.relax_ghosts(search.ptr(x),n,search.ptr(sides),w,95)
    s=np.r_[x[:-1].reshape(n,3)[survivors].ravel(),x[-1]]
    # External final stage has no ghosts and no locked angles.
    for weight,budget in ((2.5,175),(18,140),(120,120),(900,115)):
        search._lib.polish(search.ptr(s),weight,0,budget)
    if search.feasible_rescale(s)[-1] < TARGET+.075:
        proposed=search.slsqp(s,0)
        if search.feasible_rescale(proposed)[-1] <= search.feasible_rescale(s)[-1]:
            s=proposed
    return s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--donor",type=int,required=True,choices=(19,21))
    parser.add_argument("--study",type=Path,default=HERE.parents[1])
    parser.add_argument("--library-dir",type=Path,required=True)
    parser.add_argument("--inputs",type=Path,help="optional pinned donor YAML directory")
    parser.add_argument("--variants",type=int)
    parser.add_argument("--limit-masks",type=int)
    parser.add_argument("--seed",type=int,default=19002118)
    args=parser.parse_args()
    study=args.study.resolve();n=args.donor; names=[study/"search-history",study/"follow-up/patch"]
    sys.path[:0]=[str(v) for v in names]
    os.environ["PACK18_RUN"]=str(args.library_dir.resolve())
    import search
    import exact
    ptr=search.PTR
    lib=ctypes.CDLL(str((args.library_dir/"ghost.dylib").resolve()))
    lib.ghost_energy.argtypes=[ptr,ptr,ctypes.c_int,ptr,ctypes.c_double]
    lib.ghost_energy.restype=ctypes.c_double
    lib.relax_ghosts.argtypes=[ptr,ctypes.c_int,ptr,ctypes.c_double,ctypes.c_int]
    lib.relax_ghosts.restype=None
    gradient_control(lib,search)
    poses,side=donor(n,args.inputs)
    masks=list(combinations(range(n),n-18))
    if args.limit_masks is not None: masks=masks[:args.limit_masks]
    variants=args.variants if args.variants is not None else (48 if n==19 else 2)
    if variants<=0 or not masks:raise ValueError("non-empty campaign required")
    args.output.mkdir(parents=True,exist_ok=False)
    out=args.output
    groups=symmetries(poses); classes={min(tuple(sorted(g[i] for i in ids)) for g in groups) for ids in masks}
    best=None; earliest=None; raw_hits=0; above_gap=0; close=0; start=time.monotonic()
    with (out/"runs.csv").open("w",buffering=1) as f:
        writer=csv.writer(f);writer.writerow(("mask","variant","mode","side_raw","min_gap","verified_side"))
        for j,ids in enumerate(masks):
            for rep in range(variants):
                rng=np.random.default_rng(np.random.SeedSequence((args.seed,n,j,rep)))
                mode=(j+rep)%4
                v=solve_one(poses,side,ids,rng,mode,lib,search)
                data=search.doc(v);raw=float(v[-1]);gap=float(min(search.gaps(v)))
                records=[exact.repair(data["squares"],digits=17,slope_limit=den) for den in (10**8,10**12)]
                cert=min(records,key=lambda row:row[0])
                length,tiles=cert
                writer.writerow(("/".join(str(i+1) for i in ids),rep,mode,format(raw,".17g"),format(gap,".17g"),
                                 format(float(length),".17g")))
                raw_hits+=int(raw<TARGET)
                above_gap+=int(gap < -1e-9)
                close+=int(float(length)<TARGET+1e-7)
                if best is None or length<best:
                    exact.verify(length,tiles)
                    best=length;earliest=(j,rep,mode)
                    (out/"best-source.json").write_text(json.dumps(data,indent=2)+"\n")
                    (out/"best-rational.json").write_text(json.dumps({"side":str(length),"squares":[list(map(str,q)) for q in tiles]},indent=2)+"\n")
                    if exact.below(length):
                        raise SystemExit(f"STRICT VERIFIED IMPROVEMENT {length} in {out}")
            if (j+1)%100==0:print(n,j+1,"masks",float(best),flush=True)
    import decimal
    with decimal.localcontext() as ctx:
        ctx.prec=65; D=decimal.Decimal
        dec=D(best.numerator)/D(best.denominator);diff=dec-(7+D(7).sqrt())/2
    summary=dict(donor=n,donor_sha256=INPUTS[n],seed=args.seed, masks=len(masks), observed_donor_D4=len(groups),
                 masks_mod_observed_D4=len(classes),schedules_per_mask=variants,starts=len(masks)*variants,
                 nominal_below=raw_hits,final_min_gap_below_minus_1e_9=above_gap,within_1e_7=close,
                 best_exact=str(best),best_decimal=str(dec),difference_from_H=str(diff),
                 best_mask=[i+1 for i in masks[earliest[0]]],best_variant=earliest[1],best_mode=earliest[2],
                 seconds=round(time.monotonic()-start,3))
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
