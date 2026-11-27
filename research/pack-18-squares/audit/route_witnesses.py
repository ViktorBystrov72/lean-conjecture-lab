"""Route physical exact poses through terminal coordinate and angle restrictions."""
from rack_check import U, F, classify, exact_source, geometry, marks, masks
from itertools import product
from pathlib import Path
import argparse, json
import os

REPLAY = Path(os.environ["PACK18_REPLAY"])

def canonical_images(tiles):
    for swap,rx,ry in product((False,True),repeat=3):
        posed=[]
        for x,y,c,s in tiles:
            if swap: x,y,c,s=y,x,s,c
            if rx: x,c=U-x,-c
            if ry: y,s=U-y,-s
            posed.append((x,y,c,s))
        ds=[]
        for x,y,c,s in posed:
            distances=[max(abs((u-x)*c+(v-y)*s),abs((v-y)*c-(u-x)*s)) for u,v in marks]
            lo=min(distances)
            assert lo<F(1,2)
            ds.append([i for i,d in enumerate(distances) if d==lo])
        for owners in product(*ds):
            assert len(set(owners))==18
            used=sum(1<<i for i in owners)
            if used in masks:
                yield (int(swap),int(rx),int(ry)),masks.index(used),dict(zip(owners,posed))


def angle_bins(c,s,bands=128):
    result=set()
    for _ in range(4):
        if c>=0 and s>=0:
            for k in range(bands):
                if k*(1+c)<=bands*s<=(k+1)*(1+c):result.add(k)
        c,s=-s,c
    if not result:raise ValueError("angle outside all charts")
    return result


def allowed(pose,path,bins):
    # Coordinates use 1e-6 units. The angle cuts select integer band indices,
    # rather than independent comparisons to the endpoints.
    live={}
    for tile,k,v in zip(path[::3],path[1::3],path[2::3]):
        x,y,c,s=pose[tile]
        if k<4:
            z=(x,y)[k//2]*1000000
            if k%2==0 and z>v or k%2==1 and z<v:return False
        else:
            a=live.setdefault(tile,bins[tile].copy())
            a.intersection_update(i for i in range(128) if (i<v if k==4 else i>=v))
            if not a:return False
    return True


def load_groups():
    here=REPLAY
    base=json.loads((here/'n18-482-base.json').read_text())
    mask53=json.loads((here/'full-endpoint-mask-cases.json').read_text())
    g={137:[],82:[],53:[],55:[],92:[],115:[]}
    for r,(path,_,_) in enumerate(base[format(masks[137],'x')][1]):
        g[137].append((str(r),path,'faces'))
    for orbit_id in [82,92,115]:
        residual=json.loads((here/f'residual-{orbit_id}-cases.json').read_text())
        for r,(prefix,leaves) in enumerate(residual):
            for s,(path,_,action) in enumerate(leaves):
                g[orbit_id].append((f'{r}.{s}',prefix+path,action[0] if isinstance(action[0],str) else action[-1]))
    mask55=json.loads((here/'second-endpoint-mask-cases.json').read_text())
    for r,(lo,hi,leaves) in enumerate(mask55):
        prefix=([9,1,lo] if lo is not None else [])+([9,0,hi] if hi is not None else [])
        for s,(path,_,action) in enumerate(leaves):
            g[55].append((f'{r}.{s}',prefix+path,action[0] if isinstance(action[0],str) else action[-1]))
    for r,(lo,hi,leaves) in enumerate(mask53):
        prefix=[]
        if lo is not None:
            prefix+=[5,3,lo,15,1,lo,5,0,4822876-lo,15,2,4822876-lo]
        if hi is not None:prefix+=[5,2,hi]
        for s,(path,_,action) in enumerate(leaves):
            g[53].append((f'{r}.{s}',prefix+path,action[0] if isinstance(action[0],str) else action[-1]))
    return g


def routes(tiles,groups):
    out=[]
    for sym,case,pose in canonical_images(tiles):
        if case not in groups:
            out.append((sym,case,None,'outside-audited-tables'))
            continue
        bins={i:angle_bins(c,s) for i,(_,_,c,s) in pose.items()}
        for leaf,path,action in groups[case]:
            if allowed(pose,path,bins):out.append((sym,case,leaf,action))
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('sources',nargs='+',type=Path)
    groups=load_groups()
    print('terminal table sizes', {k:len(v) for k,v in groups.items()})
    for p in parser.parse_args().sources:
        side,tiles=exact_source(p)
        geometry(tiles,side)
        print(p.name,routes(tiles,groups),flush=True)
