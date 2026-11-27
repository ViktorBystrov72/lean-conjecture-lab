"""Check physical retention of an exact legal packing throughout the positive control."""
import argparse
import json
from fractions import Fraction as Q
from pathlib import Path

D=500_000_000
U=Q(4822876,10**6)
MISSING={(617,617),(1000,1000),(1383,1383)}

def dots(u,v):return u[0]*v[0]+u[1]*v[1]

def rack():
    result=set()
    for x,y in ((390,390),(617,617),(797,359),(1000,716),(1000,1000)):
        for _ in range(4):
            result.update(((x,y),(2000-x,y)))
            x,y=2000-y,x
    return sorted(result)

def load(path):
    data=json.loads(path.read_text())
    if not Q(data['side'])<=U:raise ValueError("witness lies above test box")
    tiles=[]
    for xx,yy,tt in data['squares']:
        x,y,t=map(Q,(xx,yy,tt))
        c,s=(1-t*t)/(1+t*t),2*t/(1+t*t)
        h=(abs(c)+abs(s))/2
        if c*c+s*s!=1 or not (h<=x<=U-h and h<=y<=U-h):raise ValueError("bad physical tile")
        for X,Y,C,S in tiles:
            sep=(1+abs(c*C+s*S)+abs(c*S-s*C))/2
            if max(abs((x-X)*a+(y-Y)*b) for a,b in ((c,s),(-s,c),(C,S),(-S,C)))<sep:
                raise ValueError("overlap in positive control")
        tiles.append((x,y,c,s))
    if len(tiles)!=18:raise ValueError("expected 18 tiles")
    return tiles


def canonical(tiles):
    marks=rack()
    for swap in (False,True):
        for rx in (False,True):
            for ry in (False,True):
                placed={}
                for x,y,c,s in tiles:
                    if swap:x,y,c,s=y,x,s,c
                    if rx:x,c=U-x,-c
                    if ry:y,s=U-y,-s
                    while not (c>0 and s>=0):
                        c,s=-s,c
                    distances=[]
                    for m in marks:
                        dx=x-U*m[0]/2000;dy=y-U*m[1]/2000
                        distances.append(max(abs(c*dx+s*dy),abs(-s*dx+c*dy)))
                    order=sorted(range(21),key=distances.__getitem__)
                    if distances[order[0]]>=Q(99999,200000) or distances[order[0]]==distances[order[1]]:
                        raise ValueError("ambiguous or insufficiently deep nearest mark")
                    m=marks[order[0]]
                    if m in placed:raise ValueError('duplicate occupied mark')
                    placed[m]=(x,y,c,s)
                if set(marks)-set(placed)==MISSING:return [placed[m] for m in marks if m in placed]
    raise ValueError("not in the control case 53")


def in_hull(x,y,pts):
    if not pts:return False
    if len(pts)<3:
        ax,ay=pts[0];bx,by=pts[-1]
        return min(ax,bx)<=x<=max(ax,bx) and min(ay,by)<=y<=max(ay,by) and (bx-ax)*(y-ay)==(by-ay)*(x-ax)
    return all((b[0]-a[0])*(y-a[1])>=(b[1]-a[1])*(x-a[0]) for a,b in zip(pts,pts[1:]+pts[:1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('witness',type=Path);p.add_argument('--bands',type=int,default=128)
    p.add_argument('--output',type=Path);p.add_argument('--trace',type=Path);p.add_argument('--rounds',type=int,default=10)
    args=p.parse_args()
    tiles=canonical(load(args.witness))
    bands=[int(args.bands*s/(1+c)) for _,_,c,s in tiles]
    if args.output:args.output.write_text(' '.join(map(str,bands))+'\n')
    if args.trace:
        vertices=rows=0
        with args.trace.open() as f:
            for step,who in [(-1,-1)]+[(k,j) for k in range(args.rounds) for j in range(18)]:
                for i,(x,y,c,s) in enumerate(tiles):
                    raw=list(map(int,f.readline().split()))
                    if len(raw)<6 or raw[:4]!=[step,who,i,bands[i]]:raise ValueError("bad trace ordering")
                    n=raw[4];end=5+2*n
                    poly=list(zip(raw[5:end:2],raw[6:end:2]))
                    if len(poly)!=n or not in_hull(x*D,y*D,poly):raise ValueError(("physical centre lost",step,who,i))
                    m=raw[end];core=list(zip(raw[end+1::2],raw[end+2::2]))
                    if len(raw)!=end+1+2*m:raise ValueError("bad core arity")
                    for X,Y in core:
                        dx=Q(X,D)-x;dy=Q(Y,D)-y
                        if max(abs(dx*c+dy*s),abs(-dx*s+dy*c))>Q(1,2):
                            raise ValueError(("unjustified core point",step,who,i))
                    vertices+=m;rows+=1
            if f.readline():raise ValueError("superfluous trace records")
        print(f"Preserved {len(tiles)} exact poses in all {rows} owner snapshots; {vertices} core vertices checked.")

if __name__=='__main__':main()
