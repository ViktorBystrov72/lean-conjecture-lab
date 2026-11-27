"""Exact insertion when all 17 fixed-centre unit squares may rotate freely.

A fixed centre always carries an open disk of radius 1/2. Some squares have a
forced orientation because their inscribed disks touch a wall or one another.
Box search over the last tile uses only exact Fraction comparisons.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from free_tile import LENGTH, HALF, axes, basis, check_fixed, radius


def sqdist(x, y, u, X, Y, a, hx=0, hy=0):
    """Upper bound for point-to-square distance squared anywhere in a centre box.

    (x,y) is the midpoint, (hx,hy) its halfwidths, u a unit direction, a
    the inner square's half-side. With zero box widths this is exact.
    """
    c, s = u
    dx, dy = x-X, y-Y
    du = abs(c*dx+s*dy)+abs(c)*hx+abs(s)*hy
    dv = abs(-s*dx+c*dy)+abs(s)*hx+abs(c)*hy
    return max(du-a, 0)**2 + max(dv-a, 0)**2


def pins(centres, side):
    fixed = {}
    for i, (x,y) in enumerate(centres):
        if min(x,y,side-x,side-y) == HALF:
            fixed[i]=(F(1),F(0))
        for j, (X,Y) in enumerate(centres[:i]):
            a,b=x-X,y-Y
            if a*a+b*b==1:
                fixed[i]=fixed[j]=(a,b)
    return fixed


def fit(x,y,u,side):
    h=(abs(u[0])+abs(u[1]))/2
    return h<=x<=side-h and h<=y<=side-h


def overlap(x,y,u,size,X,Y,v,other_size):
    return all(abs(a*(x-X)+b*(y-Y)) < size*radius((a,b),u)+other_size*radius((a,b),v)
               for a,b in axes(u,v))


def angular_cores(centres, side, forced, bins, references, drift):
    """Eliminate impossible orientation bands of each unpinned fixed-centre tile.
    All retained angles contain each returned core square at the tile's centre.
    """
    # A 2D displacement bounded per coordinate by drift has Euclidean norm
    # at most sqrt(2)*drift <= 3*drift/2. All guaranteed shapes below
    # are centred at the recorded initial centre, also when drift > 0.
    shift=3*drift/2
    disk=HALF-shift
    width=1-2*shift
    possible={}
    sizes={}
    cores={i:[(v,F(1))] for i,v in forced.items()}
    if not bins: return cores,possible,sizes
    for i,(x,y) in enumerate(centres):
        if i in forced:continue
        remaining=[]
        for k in range(bins):
            lo,hi=F(k,bins),F(k+1,bins)
            wall=min(sum(basis(lo)),sum(basis(hi)))/2
            if min(x,y,side-x,side-y)+drift<wall:continue
            u=basis((lo+hi)/2);inner=width/(1+hi-lo)
            for j,(X,Y) in enumerate(centres):
                if j==i:continue
                if sqdist(x,y,u,X,Y,inner/2)<disk*disk:break
                if j in forced and overlap(x,y,u,inner,X,Y,forced[j],1):break
            else:remaining.append(u)
        if not remaining:raise ValueError('A known feasible fixed-centre tile lost every angle')
        possible[i]=len(remaining)
        choices=list(dict.fromkeys([(F(1),F(0)),references[i]]))
        cs=[]
        for ref in choices:
            # cos(delta)+sin(delta) with absolute values is 1-Lipschitz as
            # a function of delta, also across its quarter-turn junctions.
            K=max(2*radius(ref,u)+F(1,bins) for u in remaining)
            if ref==(F(1),F(0)):
                # The true maximum axis extent cannot exceed the available
                # distance from the shifted centre to every wall.
                K=min(K,2*(min(x,y,side-x,side-y)+drift))
            cs.append((ref,width/K))
        cores[i]=cs
        sizes[i]=[str(q) for _,q in cs]
    return cores,possible,sizes


def run(centres, side, *, use_pins=True, bins=0, references=None, drift=F(0), node_limit=30000, depth_limit=64):
    forced=pins(centres,side) if use_pins and drift==0 else {}
    disk=HALF-3*drift/2
    cores, angles_left, core_sizes = angular_cores(centres,side,forced,bins,references,drift)
    @lru_cache(maxsize=4096)
    def fdata(lo,hi):
        u=basis((lo+hi)/2)
        # theta=2atan(t), so every angle differs from the midpoint frame
        # by at most hi-lo radians. Rotating a square scales its axial
        # extent by at most 1+|delta|. The shrunk midpoint square is inside.
        size=1/(1+hi-lo)
        wall=min(sum(basis(lo)),sum(basis(hi)))/2
        bands={}
        for i,options in cores.items():
            X,Y=centres[i]
            bands[i]=[[(a,b,a*X+b*Y,size*radius((a,b),u)+scale*radius((a,b),v))
                       for a,b in axes(u,v)] for v,scale in options]
        return u,size,wall,bands

    stack=[(HALF,side-HALF,HALF,side-HALF,F(0),F(1),0)]
    tally=Counter();left=0
    while stack and tally['nodes']<node_limit:
        x0,x1,y0,y1,t0,t1,depth=stack.pop()
        tally['nodes']+=1;tally['maximum_depth']=max(tally['maximum_depth'],depth)
        u,size,wall,bands=fdata(t0,t1)
        x0,x1=max(x0,wall),min(x1,side-wall)
        y0,y1=max(y0,wall),min(y1,side-wall)
        if x0>x1 or y0>y1:tally['walls']+=1;continue
        x,hx=(x0+x1)/2,(x1-x0)/2
        y,hy=(y0+y1)/2,(y1-y0)/2
        occupied=False;middle=True
        # The order is a heuristic and does not enter a pruning predicate.
        order=sorted(range(len(centres)),key=lambda i: (float(centres[i][0])-float(x))**2+(float(centres[i][1])-float(y))**2)
        for i in order:
            X,Y=centres[i]
            if (abs(x-X)+hx)**2+(abs(y-Y)+hy)**2 < (HALF+disk)**2:
                occupied=True;tally['disks']+=1;break
            if sqdist(x,y,u,X,Y,size/2,hx,hy)<disk*disk:
                occupied=True;tally['square_disk']+=1;break
            if i in cores and any(all(abs(a*x+b*y-z)+abs(a)*hx+abs(b)*hy<reach for a,b,z,reach in row) for row in bands[i]):
                occupied=True;tally['forced_square' if i in forced else 'angular_core']+=1;break
            if middle and (sqdist(x,y,u,X,Y,HALF)<disk*disk or
                           any(overlap(x,y,u,1,X,Y,v,scale) for v,scale in cores.get(i,[]))):
                middle=False
        if occupied:continue
        if middle and fit(x,y,u,side):
            return dict(status='relaxation_witness',x=str(x),y=str(y),t=str((t0+t1)/2),
                        forced=len(forced),angles_left=angles_left,core_sizes=core_sizes,**tally)
        if depth>=depth_limit:left+=1;continue
        widths=(x1-x0,y1-y0,t1-t0)
        k=max(range(3),key=widths.__getitem__)
        bounds=[x0,x1,y0,y1,t0,t1]
        m=(bounds[2*k]+bounds[2*k+1])/2
        l,r=bounds.copy(),bounds.copy();l[2*k+1]=m;r[2*k]=m
        stack.extend([(*r,depth+1),(*l,depth+1)])
    pending=left+len(stack)
    return dict(status='inconclusive' if pending else 'excluded',pending=pending,forced=len(forced),angles_left=angles_left,core_sizes=core_sizes,**tally)


def one(task):
    name,fixed,side,mode,limit,depth,bins,drift=task
    res=run([(x,y) for x,y,_ in fixed],side,use_pins=mode!='disks',bins=bins if mode=='bands' else 0,
            references=[v for _,_,v in fixed],drift=drift,node_limit=limit,depth_limit=depth)
    return dict(file=name,mode=mode,**res)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path,help='directory produced by scan.py')
    ap.add_argument('--angles',type=Path,help='free_angles.py receipt; restricts to its unclosed cases')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--mode',choices=['disks','pins','both','bands'],default='both')
    ap.add_argument('--drift',type=F,default=F(0),help='per-coordinate motion allowed for each obstacle centre')
    ap.add_argument('--bins',type=int,default=64)
    ap.add_argument('--names',nargs='+',help='explicit subset of layout file names')
    ap.add_argument('--limit',type=int,default=30000)
    ap.add_argument('--depth',type=int,default=64)
    ap.add_argument('--workers',type=int,default=2)
    a=ap.parse_args()
    if a.limit<1 or not 0<=a.depth<=300 or a.workers<1:ap.error('invalid limits')
    files=sorted(a.directory.glob('layout-*.txt'))
    if a.angles:
        screen=json.loads(a.angles.read_text())
        if F(screen['side'])!=LENGTH:raise ValueError('Wrong container size')
        wanted={row['file'] for row in screen['results'] if not row['excluded']}
        files=[f for f in files if f.name in wanted]
        if len(files)!=len(wanted):raise ValueError('Missing input files')
    if a.names:files=[f for f in files if f.name in a.names]
    if not 0<=a.drift<F(1,4):raise ValueError('Expected drift in [0,1/4)')
    if a.bins<1:raise ValueError("A positive number of angle bands is required")
    if not files:raise ValueError('No selected layouts')
    jobs=[]
    digests={}
    for f in files:
        fixed=check_fixed(f,LENGTH)
        digests[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
        for mode in (('disks','pins') if a.mode=='both' else (a.mode,)):
            jobs.append((f.name,fixed,LENGTH,mode,a.limit,a.depth,a.bins,a.drift))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        results=[]
        for item in pool.map(one,jobs):
            print(item['file'],item['mode'],item['status'],item['nodes'],flush=True)
            results.append(item)
    a.output.write_text(json.dumps(dict(side=str(LENGTH),limit=a.limit,depth=a.depth,bins=a.bins,drift=str(a.drift),inputs=digests,results=results),indent=2)+'\n')
if __name__=='__main__':main()
