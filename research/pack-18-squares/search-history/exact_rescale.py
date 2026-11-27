"""Repair and verify a floating search candidate with exact rational geometry."""
import argparse
import itertools
import json
import math
from fractions import Fraction as Q
from pathlib import Path

def dot(a, b):
    return a[0]*b[0]+a[1]*b[1]

def axes(t):
    u=((1-t*t)/(1+t*t),2*t/(1+t*t))
    return u,(-u[1],u[0])

def corners(center, uv):
    u,v=uv
    return [tuple(center[k]+(a*u[k]+b*v[k])/2 for k in (0,1))
            for a,b in itertools.product((-1,1),repeat=2)]

def repair(path):
    given=json.loads(path.read_text(),parse_float=str)['squares']
    assert len(given)==18
    centers=[(Q(str(x)),Q(str(y))) for x,y,_ in given]
    # Floating trigonometry only selects a rational parameter; verification
    # subsequently uses the exact guaranteed unit rotation which it defines.
    ts=[Q(str(math.tan(float(theta)/2))) for _,_,theta in given]
    bases=list(map(axes,ts));factors=[]
    for i,j in itertools.combinations(range(18),2):
        d=tuple(a-b for a,b in zip(centers[i],centers[j]))
        thresholds=[]
        for v in (*bases[i],*bases[j]):
            projected=abs(dot(v,d))
            if projected:
                radii=sum(abs(dot(v,w)) for w in (*bases[i],*bases[j]))/2
                thresholds.append(radii/projected)
        if not thresholds:raise ValueError('coincident centers')
        factors.append(min(thresholds))
    scale=max(factors)
    centers=[(scale*x,scale*y) for x,y in centers]
    polygons=[corners(c,b) for c,b in zip(centers,bases)]
    extent=[(min(v[k] for p in polygons for v in p),max(v[k] for p in polygons for v in p)) for k in (0,1)]
    side=max(hi-lo for lo,hi in extent)
    centers=[(x-extent[0][0],y-extent[1][0]) for x,y in centers]
    polygons=[corners(c,b) for c,b in zip(centers,bases)]
    for p in polygons:
        if any(not 0<=a<=side for v in p for a in v): raise ValueError('outside')
    for i,j in itertools.combinations(range(18),2):
        for v in (*bases[i],*bases[j]):
            a=[dot(v,c) for c in polygons[i]]
            b=[dot(v,c) for c in polygons[j]]
            if max(a)<=min(b) or max(b)<=min(a):break
        else:raise ValueError('overlap')
    return side,centers,ts

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('seeds',nargs='+',type=Path)
    p.add_argument('--save',type=Path)
    a=p.parse_args()
    best=None
    for path in a.seeds:
        side,centers,ts=repair(path)
        comparison=(2*side-7)**2-7
        below=2*side<=7 or comparison<0
        print(path, 'side',format(float(side),'.17g'),'strictly below target?',below,
              'algebraic comparison',format(float(comparison),'.9e'))
        if best is None or side<best[0]:best=side,centers,ts,path
    if a.save:
        side,centers,ts,path=best
        a.save.write_text(json.dumps(dict(source=str(path),side=str(side),
                squares=[[str(x),str(y),str(t)] for (x,y),t in zip(centers,ts)]),indent=2)+'\n')
