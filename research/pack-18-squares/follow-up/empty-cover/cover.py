"""Independently check that the published 235 empty leaves cover their 181 orbits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'terminal-audit'))
from sweep import case_masks

URL=('https://raw.githubusercontent.com/Mira-Cult/math/'
     '78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/'
     'unit-square-packing-18/replay/n18-482-base.json')
DIGEST='d6fa37860cde0d0e8f8ddedc25508f478fe30112be16e79697cb9ab59c54f086'
MIXED={53,55,82,92,115,137}


def unique(pairs):
    ans={}
    for k,v in pairs:
        if k in ans:raise ValueError('Repeated case key')
        ans[k]=v
    return ans


def tree(paths):
    """A leaf is terminal or has two complementary children on one variable."""
    if not paths:raise ValueError('Missing half-space')
    if any(not path for path in paths):
        if len(paths)!=1:raise ValueError('Duplicate or nonterminal leaf')
        return
    owner,d,v=paths[0][0]
    dim=d//2
    halves=[[],[]]
    for path in paths:
        i,e,w=path[0]
        if (i,e//2,w)!=(owner,dim,v):raise ValueError('Incompatible split')
        halves[e%2].append(path[1:])
    for half in halves:tree(half)


def read(path=None):
    if path:
        raw=path.read_bytes()
    else:
        with urlopen(URL,timeout=30) as response:raw=response.read()
    if hashlib.sha256(raw).hexdigest()!=DIGEST:raise ValueError('Certificate data digest differs')
    data=json.loads(raw,object_pairs_hook=unique)
    masks=case_masks()
    if len(masks)!=187 or set(data)!={format(m,'x') for m in masks}:raise ValueError('Orbit correspondence')
    out={}
    for i,m in enumerate(masks):
        if i in MIXED:continue
        B,leaves=data[format(m,'x')]
        if B not in (32,64,128):raise ValueError('Invalid source angle scale')
        paths=[]
        for flattened,_,_ in leaves:
            if len(flattened)%3:raise ValueError('Incomplete split')
            cut=[]
            for i0,d,v in zip(flattened[::3],flattened[1::3],flattened[2::3]):
                if (any(type(a)!=int for a in (i0,d,v)) or i0<0 or i0>=21 or not m>>i0&1 or
                    d not in range(6) or not (0<v<B if d>=4 else 0<=v<=4822876)):
                    raise ValueError('Invalid cut')
                cut.append((i0,d,v))
            paths.append(cut)
        tree(paths)
        out[i]=(m,B,paths)
    if len(out)!=181 or sum(len(g[2]) for g in out.values())!=235:
        raise ValueError('Unexpected cover sizes')
    return out


def options(path, B):
    angles=[]; coords=[]
    for i,d,v in path:
        sense=('le','ge')[d%2]
        if d>=4:
            angles.extend(['--angle',str(i),sense,str(v),str(B)])
        else:
            coords.extend(['--cut',str(i),'xy'[d//2]+'-'+sense,str(1000*v)])
    return angles+coords


def controls():
    good=[[(1,4,22)],[(1,5,22),(2,0,400)],[(1,5,22),(2,1,400)]]
    tree(good)
    for negative in (good[:-1],good+[good[0]], [good[0],[(1,5,23)]]):
        try:tree(negative)
        except ValueError:continue
        raise ValueError('Invalid partition accepted')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table',type=Path)
    a=parser.parse_args()
    controls()
    states=read(a.table)
    angle=sum(any(d>=4 for path in paths for _,d,_ in path) for _,_,paths in states.values())
    print(f'Validated 181 complete orbit partitions and 235 terminals. {angle} orbits use angular cuts.')
