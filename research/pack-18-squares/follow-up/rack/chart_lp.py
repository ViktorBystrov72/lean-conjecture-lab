"""Refine rack assignments in fixed-angle, signed-axis translation charts."""
import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np
from scipy.optimize import linprog, linear_sum_assignment, minimize
import rack_search as rs

n=18
ii,jj=np.triu_indices(n,k=1)
dx=np.array([0,1]); eye=np.eye(37)
def orient(theta):
    c=np.cos(theta);s=np.sin(theta)
    u=np.stack([c,s],axis=-1);v=np.stack([-s,c],axis=-1)
    return np.stack([u,v,-u,-v],axis=1)

def d4(x,k):
    a,b=x[:-1].reshape(18,3).copy(),x[-1]
    if k//4:
        a[:,0]*=-1
        a[:,2]=np.pi-a[:,2]
    for _ in range(k%4):
        a[:,:2]=a[:,[1,0]]*[-1,1]
        a[:,2]+=np.pi/2
    a[:,2]=(a[:,2]+np.pi/4)%(np.pi/2)-np.pi/4
    return np.r_[a.ravel(),b]

def ownership(x,home,rng,noise):
    p=x[:-1].reshape(n,3); ax=orient(p[:,2])[:,:2,:]
    dif=home[:,None,:]-p[None,:,:2]
    dist=np.abs(np.einsum('mij,ikj->mik',dif,ax)).max(axis=2)
    # The violations have greater priority than variations in the slack. Rare
    # alternate matchings explore assignments unavailable from a nearest match.
    cost=dist+5*np.maximum(dist-.5,0.)+rng.normal(0,noise,dist.shape)
    _,o=linear_sum_assignment(cost)
    return np.r_[p[o].ravel(),x[-1]]

def translation_lp(x,home,holes,rng,noise,margin):
    p=x[:-1].reshape(n,3)
    ax=orient(p[:,2]);u=ax[:,0,:]
    qty=37
    # Permanently fixed mark coordinates: all centers and the small container
    # are relative to the center of the common test box of side U.
    pairaxes=np.concatenate([ax[ii,:,:], ax[jj,:,:]],axis=1)
    delta=p[jj,:2]-p[ii,:2]
    d=np.einsum('akb,ab->ak',pairaxes,delta)
    pick=(d+rng.uniform(-noise,noise,d.shape)).argmax(axis=1)
    normal=pairaxes[np.arange(ii.size),pick,:]
    cross=abs(u[ii,0]*u[jj,1]-u[ii,1]*u[jj,0])
    dot=abs((u[ii]*u[jj]).sum(axis=1))
    rad=(1+cross+dot)*.5
    pairs=np.zeros((ii.size,qty))
    for k in (0,1):
        pairs[np.arange(ii.size),2*ii+k]=normal[:,k]
        pairs[np.arange(ii.size),2*jj+k]=-normal[:,k]
    # Support constraints against each wall.
    wall=np.zeros((n,2,2,qty))
    for i in range(n):
        for k in (0,1):wall[i,k,0,2*i+k]=1;wall[i,k,1,2*i+k]=-1
    wall[:,:,:,-1]=-.5
    hw=(abs(u[:,0])+abs(u[:,1]))*.5
    # Include owner and compare its four supports with one signed support per hole.
    own=np.zeros((n,4,qty))
    for i in range(n): own[i,:,2*i:2*i+2]=-ax[i]
    ob=.5-margin-np.einsum('ikj,ij->ik',ax,home)
    dif=holes[None,:,:]-p[:,None,:2]
    dh=np.einsum('ihj,ikj->ihk',dif,ax)
    which=(dh+rng.uniform(-noise,noise,dh.shape)).argmax(axis=2)
    hvec=ax[np.arange(n)[:,None],which]
    near=np.zeros((n,3,4,qty))
    for i in range(n):near[i,:,:,2*i:2*i+2]=hvec[i,:,None,:]-ax[i,None,:,:]
    nb=np.einsum('ihj,hj->ih',hvec,holes)[:,:,None]-np.einsum('ikj,ij->ik',ax,home)[:,None,:]-margin
    mat=np.vstack([pairs,wall.reshape(-1,qty),own.reshape(-1,qty),near.reshape(-1,qty)])
    right=np.concatenate([-rad,np.repeat(-hw,4),ob.ravel(),nb.ravel()])
    r=linprog(eye[-1],A_ub=mat,b_ub=right,bounds=[(None,None)]*(qty-1)+[(4.2,5.7)],
              method='highs',options={'primal_feasibility_tolerance':1e-10,'dual_feasibility_tolerance':1e-10})
    if not r.success:return None
    cand=x.copy()
    cand[:-1].reshape(n,3)[:,:2]=r.x[:-1].reshape(n,2);cand[-1]=r.x[-1]
    return cand

def assigned_guards(y,home,holes,jacobian=False,margin=1e-8):
    a=y[:-1].reshape(n,3);ax=orient(a[:,2]);dax=ax[:,:,[1,0]]*[-1,1]
    dv=home-a[:,:2];dhome=np.einsum('ij,ikj->ik',dv,ax)
    diff=holes[None,:,:]-a[:,None,:2]
    dh=np.einsum('ihj,ikj->ihk',diff,ax)
    k=dh.argmax(axis=-1);hv=ax[np.arange(n)[:,None],k]
    vh=dh.max(axis=-1)
    if not jacobian: return np.concatenate([(.5-margin-dhome).ravel(),(vh[:,:,None]-dhome[:,None,:]-margin).ravel()])
    dj=np.einsum('ij,ikj->ik',dv,dax)
    hj=np.einsum('ihj,ihj->ih',diff,dax[np.arange(n)[:,None],k])
    aa=np.zeros((n,4,55));bb=np.zeros((n,3,4,55))
    for i in range(n):
        aa[i,:,3*i:3*i+2]=ax[i]
        aa[i,:,3*i+2]=-dj[i]
        bb[i,:,:,3*i:3*i+2]=ax[i,None,:,:]-hv[i,:,None,:]
        bb[i,:,:,3*i+2]=hj[i,:,None]-dj[i,None,:]
    return np.vstack([aa.reshape(-1,55),bb.reshape(-1,55)])

def polish_guarded(x,home,holes,locked,margin):
    active=np.flatnonzero(rs.prior.gaps(x)<.38)
    markeractive=np.flatnonzero(assigned_guards(x,home,holes,margin=margin)<.22)
    def value(y):
        return np.r_[rs.prior.gaps(y)[active],assigned_guards(y,home,holes,margin=margin)[markeractive]]
    def jac(y):
        return np.vstack([rs.prior.gaps(y,True)[active],assigned_guards(y,home,holes,True,margin=margin)[markeractive]])
    bounds=[(None,None)]*55
    for i in locked:bounds[3*i+2]=(x[3*i+2],x[3*i+2])
    obj=np.r_[np.zeros(54),1]
    r=minimize(lambda y:y[-1],x,jac=lambda _:obj,bounds=bounds,method='SLSQP',
               constraints=[{'type':'ineq','fun':value,'jac':jac}],options={'maxiter':100,'ftol':8e-13})
    violation=min(rs.prior.gaps(r.x).min(),assigned_guards(r.x,home,holes,margin=margin).min())
    if violation < -1e-7:return x
    return r.x

def raw_doc(x):
    a=x[:-1].reshape(18,3).copy(); a[:,:2]+=rs.U/2
    return {'side':float(x[-1]),'test_box':rs.U,'squares':a.tolist()}

def run(args):
    rng=np.random.default_rng(args.seed)
    out=args.out;out.mkdir(exist_ok=True)
    mask=rs.canonical_masks[args.orbit]
    idx=[i for i in range(21) if mask>>i&1]+[i for i in range(21) if not mask>>i&1]
    rk=np.ascontiguousarray(rs.grid[idx].reshape(-1)); home,holes=rs.U*rs.grid[idx[:18]],rs.U*rs.grid[idx[18:]]
    initial=[(p.stem,rs.prior.load(p)) for p in args.starts]
    best=np.inf;ownbest=np.inf;success=0;extra=0;archive=[];start=time.monotonic();apparent=0
    with (out/'rounds.csv').open('w',buffering=1) as f:
        log=csv.writer(f);log.writerow(['index','base','D4','stage','raw_L','min_gap','min_owner_guard','repaired_L','repaired_orbit'])
        for k in range(args.count):
            name,x=initial[(k//8)%len(initial)] if k<8*len(initial) or not archive or rng.random()<.43 else ('archive',archive[rng.integers(len(archive))][1])
            action=k%8 if k<8*len(initial) else rng.integers(8)
            x=ownership(d4(x,int(action)),home,rng,rng.choice([0,.02,.06,.11]) if k>=8*len(initial) else 0)
            nn=rng.choice([0.,.003,.013,.047,.11,.25]) if k>=8*len(initial) else 0
            margin=1e-8 if k%2 else 0
            y=translation_lp(x,home,holes,rng,nn,margin)
            if y is None:
                # This chart may be infeasible; get a different angle and center
                # configuration with mark terms active and try again without chart noise.
                if k%3!=0:continue
                x=rs.perturb(x,rng)
                rs.place_marks(rk,3.,5.,.001)
                for w in (4.,45.,560.):rs.pol(x,w,120)
                y=translation_lp(x,home,holes,rng,0,margin)
                if y is None:continue
            success+=1
            bestchart=y.copy()
            for trial in range(2):
                # First follow the chart, then allow all angles in a nonlinear solve.
                locked=[] if trial else np.flatnonzero(abs(np.sin(2*y[:-1].reshape(n,3)[:,2]))<1e-8)
                if trial>0 and k%5:continue
                q=polish_guarded(y,home,holes,locked,margin)
                if q[-1]<=bestchart[-1] and min(rs.prior.gaps(q).min(),assigned_guards(q,home,holes,margin=margin).min())>=-1e-8:
                    bestchart=q
            raw=bestchart.copy(); x=rs.prior.feasible_rescale(raw);tag=rs.midpoint_mark_orbit(x)
            log.writerow((k,name,action,'assigned',raw[-1],rs.prior.gaps(raw).min(),assigned_guards(raw,home,holes,margin=margin).min(),x[-1],tag))
            if raw[-1]<rs.H:apparent+=1
            if raw[-1] < ownbest:
                ownbest=raw[-1];rs.prior.atomic_write(out/'best-assigned-raw.json',raw_doc(raw))
                rs.prior.atomic_write(out/'best-assigned.json',rs.layout(x))
            if tag==args.orbit and x[-1]<5.05 and not any(abs(v-x[-1])<.00025 for v,_ in archive):
                archive.append((x[-1],x.copy()));archive.sort(key=lambda z:z[0]);archive=archive[:28]
            rs.place_marks(rk,0.,0.,0.)
            y=rs.prior.slsqp(raw,0)
            yr=rs.prior.feasible_rescale(y)
            if yr[-1]<x[-1]:x=yr;raw=y
            extra+=1
            log.writerow((k,name,action,'released',raw[-1],rs.prior.gaps(raw).min(),assigned_guards(raw,home,holes,margin=margin).min(),x[-1],rs.midpoint_mark_orbit(x)))
            if x[-1] < best:
                best=x[-1];rs.prior.atomic_write(out/'best.json',rs.layout(x))
            if best < rs.H-2e-12:
                print('POSSIBLE IMPROVEMENT',out,k,best,flush=True);break
            if (k+1)%100==0: print(out.name,k+1,'LP feasible',success,'raw',ownbest,'repaired',best,flush=True)
    rs.prior.atomic_write(out/'summary.json',dict(orbit=args.orbit,seed=args.seed,chart_attempts=k+1,feasible_charts=success,
       nonlinear_and_released=extra,best_repaired=best if np.isfinite(best) else None,
       best_assigned_raw=ownbest if np.isfinite(ownbest) else None,raw_assigned_below_record=apparent,
       seconds=time.monotonic()-start))
    print(out,'done',success,ownbest,best,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--orbit',type=int,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--count',type=int,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('starts',nargs='+',type=Path);run(p.parse_args())
