"""Basin-hopping search for 18 unit squares; angles in radians."""
import argparse
import collections
import ctypes
import json
import math
import os
from pathlib import Path
import time
import numpy as np
from scipy.optimize import minimize

ROOT = Path(os.environ.get("PACK18_RUN", Path(__file__).resolve().parent))
S = (7 + math.sqrt(7)) / 2
_lib = ctypes.CDLL(str(ROOT / 'packing.dylib'))
PTR = ctypes.POINTER(ctypes.c_double)
_lib.polish.argtypes = [PTR, ctypes.c_double, ctypes.c_uint, ctypes.c_int]
_lib.constraints.argtypes = [PTR, PTR, PTR]
_lib.constraints.restype = None
def ptr(arr): return arr.ctypes.data_as(PTR)
def load(path):
    seed = json.loads(path.read_text())
    squares = np.array(seed['squares'], dtype=float)
    squares[:, :2] -= seed['side'] / 2
    return np.r_[squares.ravel(), seed['side']]
def doc(x):
    a = x[:-1].reshape(18,3).copy()
    a[:,:2] += x[-1]/2
    return {'side':float(x[-1]), 'squares':a.tolist()}
def gaps(x, derivatives=False):
    g = np.empty(189); jac = np.empty((189,55)) if derivatives else None
    _lib.constraints(ptr(x),ptr(g),ptr(jac) if derivatives else None)
    return jac if derivatives else g
def feasible_rescale(x):
    """Radially separate centers, recenter, then bound the enclosing box."""
    p=x[:-1].reshape(18,3).copy()
    a=p[:,2]; u=np.stack([np.cos(a),np.sin(a)],axis=1)
    z=u[:,[1,0]].copy(); z[:,0]*=-1
    ratio=1.
    for i in range(1,18):
        v=p[:i,:2]-p[i,:2]
        m=np.maximum.reduce((np.abs(v@u[i]),np.abs(v@z[i]),
                        np.abs(np.sum(u[:i]*v,axis=1)),np.abs(np.sum(z[:i]*v,axis=1))))
        r=.5*(1+np.abs(u[:i]@u[i])+np.abs(z[:i]@u[i]))
        ratio=max(ratio,float(np.max(r/np.maximum(m,1e-20))))
    p[:,:2]*=ratio*(1+1e-14)
    h=.5*(np.abs(u[:,0])+np.abs(u[:,1]))
    lo=(p[:,:2]-h[:,None]).min(axis=0); hi=(p[:,:2]+h[:,None]).max(axis=0)
    p[:,:2]-=(lo+hi)/2
    return np.r_[p.ravel(), max(hi-lo)+2e-14]
def slsqp(x, fixed):
    q=x.copy()
    b=[(None,None)]*55
    for i in range(18):
        if fixed&(1<<i): b[3*i+2]=(q[3*i+2],q[3*i+2])
    # Remote pairs get reintroduced if they become active.
    active=np.flatnonzero(gaps(q)<.7)
    c={'type':'ineq','fun':lambda y:gaps(y)[active], 'jac':lambda y:gaps(y,True)[active]}
    obj=np.r_[np.zeros(54),1.]
    result=minimize(lambda y:y[-1],q,jac=lambda y:obj,method='SLSQP',bounds=b,
                    constraints=c,options={'ftol':4e-12,'maxiter':80})
    if np.amin(gaps(result.x)) < -1e-6: return x
    return result.x
def jitter(base, rng, mode):
    x=base.copy(); q=x[:-1].reshape(18,3)
    if mode=='grid':
        grid=np.array([(i,j) for i in range(5) for j in range(5)],dtype=float)-2
        q[:,:2]=grid[rng.choice(25,18,replace=False)]+rng.normal(0,.15,(18,2))
        q[:,2]=rng.uniform(-.65,.65,18); x[-1]=5.4
    elif mode=='reinsert':
        # Remove a small cluster and refill by ranked random placements. The
        # lookahead uses full separating-axis gaps, allowing a new local topology.
        count=int(rng.integers(1,4))
        removed=rng.choice(18,count,replace=False)
        present=[i for i in range(18) if i not in removed]
        for i in removed:
            angle=rng.uniform(-np.pi/4,np.pi/4,700)
            angle[:200]=rng.choice([0.,.42403103949,-.42403103949,np.pi/4],200)
            va=np.stack([np.cos(angle),np.sin(angle)],axis=1)
            vb=np.stack([-np.sin(angle),np.cos(angle)],axis=1)
            maxpos=.5*x[-1]-.5*(abs(va[:,0])+abs(va[:,1]))
            xy=rng.uniform(-1,1,(len(angle),2))*maxpos[:,None]
            xy[::4,0]=np.sign(xy[::4,0])*maxpos[::4]
            xy[1::4,1]=np.sign(xy[1::4,1])*maxpos[1::4]
            others=q[present]; ca=np.cos(others[:,2]); sa=np.sin(others[:,2])
            dx=xy[:,0,None]-others[:,0];dy=xy[:,1,None]-others[:,1]
            projections=np.maximum.reduce([abs(dx*va[:,0,None]+dy*va[:,1,None]),
                        abs(dx*vb[:,0,None]+dy*vb[:,1,None]),
                        abs(dx*ca+dy*sa),abs(-dx*sa+dy*ca)])
            halfwidth=.5*(1+abs(va[:,0,None]*ca+va[:,1,None]*sa)+
                              abs(va[:,1,None]*ca-va[:,0,None]*sa))
            overlap=np.maximum(0,halfwidth-projections)
            order=np.argsort(np.sum(overlap**2,axis=1))
            j=order[min(int(rng.exponential(1.9)),len(order)-1)]
            q[i]=[xy[j,0],xy[j,1],angle[j]]
            present.append(i)
        q[:,:2]+=rng.normal(0,.05,(18,2))
    elif mode=='layer':
        a=rng.uniform(-np.pi/2,np.pi/2);u=np.array([np.cos(a),np.sin(a)])
        v=np.array([-u[1],u[0]])
        t=rng.uniform(-1,1); side=q[:,:2]@u>=t
        if rng.random()<.3:
            q[side,:2]-=2*(q[side,:2]@v)[:,None]*v
            q[side,2]=2*a-q[side,2]
        else:
            q[side,:2]+=rng.uniform(-1,1)*v+rng.uniform(-.2,.2)*u
            q[side,2]+=rng.uniform(-.32,.32)
    elif mode=='shuffle':
        count=int(rng.integers(2,5)); ids=rng.choice(18,count,replace=False)
        for i in ids:
            q[i,:2]=rng.uniform(-2,2,2)
            q[i,2]=rng.uniform(-.77,.77)
        q[:,:2]+=rng.normal(0,.11,(18,2))
    elif mode=='local':
        i=int(rng.integers(18)); d=np.linalg.norm(q[:,:2]-q[i,:2],axis=1)
        ids=d<rng.uniform(1.15,2.4)
        q[ids,:2]+=rng.normal(0,rng.uniform(.10,.48),(sum(ids),2))
        q[ids,2]+=rng.normal(0,rng.uniform(.08,.45),sum(ids))
    elif mode=='twist':
        origin=q[rng.integers(18),:2].copy()
        d=np.linalg.norm(q[:,:2]-origin,axis=1); ids=d<rng.uniform(1.25,2.35)
        a=rng.choice([-1.,1.])*rng.uniform(.12,.62)
        c=np.cos(a);s=np.sin(a)
        q[ids,:2]=(q[ids,:2]-origin)@np.array([[c,s],[-s,c]])+origin
        q[ids,2]+=a
    else:
        q[:,:2]+=rng.normal(0,rng.uniform(.015,.30),(18,2))
        q[:,2]+=rng.normal(0,rng.uniform(.015,.37),18)
    q[:,2]=(q[:,2]+np.pi/4)%(np.pi/2)-np.pi/4
    fraction = rng.choice([0.,.2,.55,.85,1.])
    lock=(rng.random(18)<fraction) & (np.abs(q[:,2])<.25)
    q[lock,2]=0.
    return x,sum(1<<i for i in np.flatnonzero(lock))
def atomic_write(path, value):
    pp=path.with_suffix('.tmp'); pp.write_text(json.dumps(value,indent=1));pp.replace(path)
def run(args):
    out=ROOT/args.output; out.mkdir(exist_ok=True)
    seeds=[load(Path(p)) for p in args.seeds]
    rng=np.random.default_rng(args.rng); pool=[]; current=seeds[0]
    track=collections.Counter(); best=100.; best_i=-1
    start=time.perf_counter()
    with (out/'runs.csv').open('w', buffering=1) as f:
        f.write('index,seed,perturbation,locked,penalty_side,repaired_side,slsqp\n')
        for i in range(args.starts):
            v=rng.random()
            if v<.40: base=seeds[rng.integers(len(seeds))]; source='published'
            elif pool and v<.7: base=pool[rng.integers(len(pool))][1]; source='archive'
            else: base=current; source='walk'
            if args.extended:
                mode=rng.choice(['grid','shuffle','local','twist','jitter','layer','reinsert'],
                                p=[.04,.08,.15,.17,.13,.23,.2])
            else:
                mode=rng.choice(['grid','shuffle','local','twist','jitter'],p=[.1,.16,.25,.24,.25])
            x,locked=jitter(base,rng,mode)
            for weight,budget in [(1.7,110),(12,120),(95,140),(1400,100)]:
                _lib.polish(ptr(x), weight, int(locked),budget)
            rough=feasible_rescale(x)
            improved=(rough[-1] < S+.08 if i%5==0 else rough[-1] < S+.014)
            if improved:
                q=slsqp(x, int(locked))
                exact=feasible_rescale(q)
                if exact[-1]>rough[-1]: exact=rough
            else: exact=rough
            val=exact[-1]
            f.write(f'{i},{source},{mode},{int(locked).bit_count()},{x[-1]:.12f},{val:.15f},{int(improved)}\n')
            if val < best:
                best=val;best_i=i
                atomic_write(out/'best.json',doc(exact))
            if val < S-1e-10:
                print(f'CANDIDATE {i} {val:.15f}',flush=True);break
            if val<5.02:
                # Keep distinct scores to prevent immediate collapse to one topology.
                if not any(abs(val-a)<.00028 for a,_ in pool):
                    pool.append((val,exact));pool.sort(key=lambda item:item[0]);pool=pool[:25]
                if val<current[-1]+rng.exponential(.015): current=exact
            track['within_1e-5']+=int(val < S+.00001)
            track['within_0.01']+=int(val < S+.01)
            if (i+1)%50==0:
                print(f'{i+1} starts, best {best:.12f}, {time.perf_counter()-start:.1f}s',flush=True)
    summary=dict(rng=args.rng,starts=i+1,best=best,best_index=best_i,
                 seconds=time.perf_counter()-start, counts=dict(track),seed_files=args.seeds)
    atomic_write(out/'summary.json',summary)
    print(json.dumps(summary),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rng',type=int,required=True)
    p.add_argument('--starts',type=int,default=200);p.add_argument('--output',required=True)
    p.add_argument('--extended',action='store_true');p.add_argument('seeds',nargs='+');run(p.parse_args())
