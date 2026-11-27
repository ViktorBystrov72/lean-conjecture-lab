"""Optimize contact charts derived only from the best freshly compressed layouts."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog, minimize

import run

I, J = np.triu_indices(18, k=1)
PAIRS=np.arange(len(I))
ROWS, TAIL = 72, len(I)
WALL=np.zeros((ROWS,37))
for i in range(18):
    for k in range(2):
        for s in range(2):
            WALL[4*i+2*k+s,2*i+k]=2*s-1
            WALL[4*i+2*k+s,-1]=-.5


def contacts(q,rng,noise):
    theta=q[:,2]; u=np.c_[np.cos(theta),np.sin(theta)]
    v=np.c_[-u[:,1],u[:,0]]
    choices=np.stack([u[I],v[I],u[J],v[J]],axis=1)
    dp=q[J,:2]-q[I,:2]
    products=np.einsum('ijk,ik->ij',choices,dp)
    direction=np.argmax(abs(products)+rng.uniform(0,noise,products.shape),axis=1)
    owner=np.where(direction<2,I,J);cross=(direction%2)!=0
    sign=np.where(products[PAIRS,direction]>=0,1,-1)
    return owner,cross,sign


class Chart:
    def __init__(self,chart):
        self.owner,self.cross,self.sign=chart
        self.calls=0
        self.c=np.r_[np.zeros(36),1.]
        self.A=np.zeros((ROWS+TAIL,37))
        self.A[:ROWS]=WALL

    def evaluate(self,theta):
        self.calls+=1
        c,s=np.cos(theta),np.sin(theta)
        extent=.5*(abs(c)+abs(s))
        dext=.5*(-np.sign(c)*s+np.sign(s)*c)
        delta=theta[J]-theta[I];dc,ds=np.cos(delta),np.sin(delta)
        support=.5*(1+abs(dc)+abs(ds))
        dh=.5*(-np.sign(dc)*ds+np.sign(ds)*dc)
        a=self.sign*np.where(self.cross,-s[self.owner],c[self.owner])
        b=self.sign*np.where(self.cross, c[self.owner],s[self.owner])
        n=ROWS+PAIRS
        self.A[n,2*I]= a;self.A[n,2*I+1]= b
        self.A[n,2*J]=-a;self.A[n,2*J+1]=-b
        result=linprog(self.c,A_ub=self.A,b_ub=np.r_[-np.repeat(extent,4),-support],
                       bounds=[(None,None)]*36+[(0,None)],method="highs",
                       options={"primal_feasibility_tolerance":1e-9,"dual_feasibility_tolerance":1e-9})
        if not result.success:
            return 20.,np.zeros(18),None
        xy=result.x[:36].reshape(18,2)
        dp=xy[J]-xy[I]
        dual=result.ineqlin.marginals[ROWS:]
        g=-result.ineqlin.marginals[:ROWS].reshape(18,4).sum(1)*dext
        np.add.at(g,I,dual*dh);np.add.at(g,J,-dual*dh)
        np.add.at(g,self.owner,dual*(a*dp[:,1]-b*dp[:,0]))
        return float(result.fun),g,xy


def optimize(q,rng,start,jitter,group):
    q=q.copy();q[:,2]=np.remainder(q[:,2]+np.pi/4,np.pi/2)-np.pi/4
    solver=Chart(contacts(q,rng,jitter))
    theta=q[:,2].copy()
    if group:
        classes=[];labels=[]
        for i in np.argsort(theta):
            if not classes or abs(theta[i]-theta[classes[-1][0]])>group:
                classes.append([i])
            else: classes[-1].append(i)
        for ids in classes:
            labels.append(ids)
            theta[ids]=theta[ids].mean()
    else:
        labels=[[i] for i in range(18)]
    t=np.array([theta[ids[0]] for ids in labels])
    if start:
        t+=rng.normal(0,start,len(t))
    best=[float("inf"),None]
    def loss(ts):
        for u,ids in zip(ts,labels): theta[ids]=u
        side,grad,xy=solver.evaluate(theta)
        if xy is not None and side<best[0]:
            best[:]=side,np.column_stack([xy,theta.copy()])
        return side,np.array([grad[ids].sum() for ids in labels])
    # The value is piecewise smooth. Keep every best feasible iterate, including
    # when the line search terminates at a nondifferentiable angle alignment.
    minimize(loss,t,jac=True,method='L-BFGS-B',bounds=[(a-.22,a+.22) for a in t],
             options={'maxiter':45,'ftol':1e-14,'gtol':2e-10,'maxls':15})
    return best[0],best[1],solver.calls


def stage(base,seed):
    rng=np.random.default_rng(500_000+seed)
    raw=base[-1];best=base.copy();calls=0
    for group,start,noise in ((.012,0.,0.),(.00001,0.,.00001),(0.,0.,0.),
                              (.025,.033,.045),(0.,.014,.04),(.04,.07,.08)):
        side,q,number=optimize(best[:-1].reshape(18,3),rng,start,noise,group)
        calls+=number;raw=min(raw,side)
        if q is None:continue
        feasible=run.search.feasible_rescale(np.r_[q.ravel(),side])
        if feasible[-1]<best[-1]: best=feasible
        q=run.search.slsqp(np.r_[q.ravel(),side],0)
        feasible=run.search.feasible_rescale(q)
        if feasible[-1]<best[-1]:best=feasible
    return best,raw,calls


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batches',nargs='+',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--part',type=int,default=0);p.add_argument('--parts',type=int,default=1)
    p.add_argument('--cutoff',type=float,default=4.86)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    roots=sorted(int(r['seed']) for b in args.batches for r in csv.DictReader((b/'runs.csv').open())
                 if float(r["rational_side_approx"])<args.cutoff)
    selected=roots[args.part::args.parts]
    best=None;nominal=100;total=0;prebelow=0
    with (args.output/'runs.csv').open('w',buffering=1) as out:
        log=csv.writer(out);log.writerow(['seed','raw_lp_min','lp_calls','rational_side'])
        for seed in selected:
            rng=np.random.default_rng(seed)
            q=run.seed_layout(rng,run.FAMILIES[seed%4])
            x=run.run_trial(rng,q)
            repaired,raw,calls=stage(x,seed)
            total+=calls;nominal=min(nominal,raw);prebelow+=int(run.exact.below(Fraction.from_float(raw)))
            poses=run.search.doc(repaired)['squares']
            trials=[run.exact.repair(poses,slope_limit=lim) for lim in (10**8,10**12)]
            side,tiles=min(trials,key=lambda pair:pair[0])
            log.writerow([seed,format(raw,'.17g'),calls,str(side)])
            if best is None or side<best:
                run.exact.verify(side,tiles);best=side
                (args.output/'best-rational.json').write_text(json.dumps({'side':str(side),'squares':[[str(a),str(b),str(c)] for a,b,c in tiles]},indent=2)+'\n')
                (args.output/'best-numerical.json').write_text(json.dumps({'seed':seed,'family':run.FAMILIES[seed%4], 'side':float(repaired[-1]),'squares':poses},indent=2)+'\n')
            if run.exact.below(side):
                print('STRICTLY BELOW RECORD',seed,side,flush=True);break
    summary={'starts':len(selected),'lp_calls':total,'minimum_nominal':nominal,'nominal_below':prebelow,'best_rational':str(best),
             'runs_sha256':hashlib.sha256((args.output/'runs.csv').read_bytes()).hexdigest()}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary,flush=True)
if __name__=='__main__':main()
