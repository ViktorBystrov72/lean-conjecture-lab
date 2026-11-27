"""Fixed-orientation searches for a physical pose assigned to an empty case/leaf.

Pairwise half-planes are chosen only from axes valid at the starting witness.
Their intersection is an inner approximation to all permissible moves. The LP
is solely a proposal mechanism; novel leaves are independently checked with
rational poses, exact SAT and the exact rack classifier.
"""
from collections import Counter
from itertools import combinations, product
from pathlib import Path
import json, math
import argparse

import numpy as np
from scipy.optimize import linprog

from rack_check import U,F,marks,masks,grid,SCALE,mask,orbit,MIXED,geometry,classify,exact_source
from route_witnesses import routes,canonical_images,load_groups,angle_bins


def approx(x):
    return float(x.a)+float(x.b)*math.sqrt(7) if hasattr(x,'a') else float(x)


def rationalize(centers,frames):
    out=[]
    for (x,y),(c,s) in zip(centers,frames):
        if c<-.5:c,s=-c,-s
        t=F(str(round(s/(1+c),14)))
        out.append((F(str(round(x,13))),F(str(round(y,13))),(1-t*t)/(1+t*t),2*t/(1+t*t)))
    return out


def normal_choices(centers,frames):
    choices=[]
    for i,j in combinations(range(18),2):
        choices_ij=[]
        for k in (i,j):
            c,s=frames[k]
            for v in ([c,s],[-s,c]):
                a=np.array(v)
                delta=centers[j]-centers[i]
                if a@delta<0:a=-a
                support=sum((abs(a[0]*c1+a[1]*s1)+abs(-a[0]*s1+a[1]*c1))/2
                            for c1,s1 in (frames[i],frames[j]))
                gap=float(a@delta-support)
                if gap>=-1e-8 and not any(np.linalg.norm(a-b)<1e-8 for _,b,_ in choices_ij):
                    choices_ij.append((gap,a,support))
        choices_ij.sort(key=lambda item:-item[0])
        assert choices_ij
        choices.append((i,j,choices_ij))
    return choices


def packet(pose,frames,normal_sets,branch,rng):
    A=[];b=[];slack=2e-9
    for i,j,alternatives in normal_sets:
        _,v,h=alternatives[0 if branch==0 else rng.integers(len(alternatives))]
        row=np.zeros(36)
        row[2*i:2*i+2]=v
        row[2*j:2*j+2]=-v
        A.append(row);b.append(-h-slack)
    bounds=[]
    for c,s in frames:
        half=(abs(c)+abs(s))/2
        bounds.extend([(half+slack,float(U)-half-slack)]*2)
    return np.array(A),np.array(b),bounds


def candidates(lp,objective,extra=None):
    A,b,bounds=lp
    if extra:
        A=np.vstack((A,np.array([a for a,_ in extra])))
        b=np.r_[b,np.array([v for _,v in extra])]
    ans=linprog(objective,A_ub=A,b_ub=b,bounds=bounds,method='highs',
        options={'primal_feasibility_tolerance':1e-10,'dual_feasibility_tolerance':1e-10})
    return ans.x.reshape(18,2) if ans.success else None


def target(path,ids,bins):
    cons=[]
    chosen={}
    for j,t,v in zip(path[::3],path[1::3],path[2::3]):
        if t>=4:
            r=chosen.setdefault(j,bins[j].copy())
            r.intersection_update(i for i in range(128) if (i<v if t==4 else i>=v))
            if not r:return None
        else:
            a=np.zeros(36);idx=2*ids.index(j)+t//2
            sign=1 if t%2==0 else -1
            a[idx]=sign
            cons.append((a,sign*v/1e6))
    return cons


real_marks=np.array(marks,dtype=float)
def signs(positions,frames):
    dx=real_marks[None,:,:]-positions[:,None,:]
    c=frames[:,0,None];s=frames[:,1,None]
    d=np.maximum(abs(dx[:,:,0]*c+dx[:,:,1]*s),abs(dx[:,:,1]*c-dx[:,:,0]*s))
    owner=np.argmin(d,axis=1)
    if len(set(owner))!=18: return None,None,True
    owner=tuple(map(int,owner))
    nearest_two=np.partition(d,1,axis=1)[:,:2]
    tie=bool(np.any(abs(nearest_two[:,0]-nearest_two[:,1])<1e-9))
    return orbit[tuple(sorted(set(range(21))-set(owner)))],owner,tie


def float_charts(owners,frames,groupdata):
    result=[]
    for sw,rx,ry in product((False,True),repeat=3):
        ids=[];axes=[]
        for old,(c,s) in zip(owners,frames):
            x,y=grid[old]
            if sw: x,y,c,s=y,x,s,c
            if rx: x,c=SCALE-x,-c
            if ry: y,s=SCALE-y,-s
            ids.append(grid.index((x,y)));axes.append((c,s))
        used=sum(1<<i for i in ids)
        if used not in masks:continue
        case=masks.index(used)
        if case not in groupdata:continue
        bins={i:angle_bins(c,s) for i,(c,s) in zip(ids,axes)}
        paths=[];bounds=[]
        for leaf,path,action in groupdata[case]:
            constraints=target(path,ids,bins)
            if constraints is None:continue
            low=np.full(36,-np.inf);high=np.full(36,np.inf)
            for a,v in constraints:
                i=int(np.flatnonzero(a)[0])
                if a[i]>0: high[i]=min(high[i],v)
                else: low[i]=max(low[i],-v)
            paths.append((case,leaf,action));bounds.append([low,high])
        if paths:result.append(((sw,rx,ry),paths,np.array(bounds)))
    return result


def run(source,branches,n_random):
    data=json.loads(source.read_text())
    exact=([tuple(map(F,t)) for t in data['tiles']]
           if 'tiles' in data else exact_source(source)[1])
    geometry(exact,U)
    groupdata=load_groups()
    rng=np.random.default_rng(237701)
    report={'source':source.name,'branches_per_chart':branches,'random_directions':n_random}
    targeted=Counter();sampled=Counter();seen=set()
    examples={}; visited=Counter()
    canonical=list(canonical_images(exact))
    for sym,case,pose in canonical:
        ids=list(pose)
        frames=np.array([[approx(c),approx(s)] for _,_,c,s in pose.values()])
        positions=np.array([[approx(x),approx(y)] for x,y,_,_ in pose.values()])
        bins={k:angle_bins(q[2],q[3]) for k,q in pose.items()}
        normals=normal_choices(positions,frames)
        chart_cache={}
        # Numeric proposals are cheap. Every new case and every LP-feasible
        # attempt at a nominally empty target is checked exactly.
        def tally(pts,tag,force=False):
            if pts is None:return
            case_float,owners,tie=signs(pts,frames)
            sampled[(tag,case_float)]+=1
            if owners not in chart_cache:
                chart_cache[owners]=float_charts(owners,frames,groupdata) if owners is not None else []
            approx_routes=[]
            for (sw,rx,ry),paths,b in chart_cache[owners]:
                z=(pts[:,::-1] if sw else pts).copy()
                if rx:z[:,0]=float(U)-z[:,0]
                if ry:z[:,1]=float(U)-z[:,1]
                z=z.ravel()
                active=np.flatnonzero(((b[:,0,:]<=z+1e-10)&(z-1e-10<=b[:,1,:])).all(axis=1))
                approx_routes.extend(paths[i] for i in active)
            for item in approx_routes:visited[item]+=1
            signature=tuple(sorted(set(approx_routes)))
            if signature in seen and not force and not tie and signature and all(x[-1]!='empty' for x in signature) and case_float in MIXED:return
            tiles=rationalize(pts,frames)
            try: geometry(tiles,U)
            except ValueError:
                sampled[('failed-rationalization',case_float)]+=1
                return
            expected,ties=classify(tiles)
            route=routes(tiles,groupdata)
            e={'case':sorted(set(expected.values())),'routes':route,'ties':ties}
            if (case_float not in MIXED or any(v[-1]=='empty' for v in route)
                    or not route):
                failure=e
                failure['tiles']=[[str(z) for z in q] for q in tiles]
                path=Path('candidate-'+source.stem+'.json');path.write_text(json.dumps(failure))
                raise RuntimeError(('candidate needs investigation',path))
            seen.add(signature);examples[str(e)]=e
            for _,orbit_id,leaf,action in route:
                suffix=f'{orbit_id}-{leaf}'
                saved=Path('representatives')/(source.stem+'-'+suffix+'.json')
                if not saved.exists():
                    saved.parent.mkdir(exist_ok=True)
                    sdata={'side':str(U),'tiles':[[str(z) for z in q] for q in tiles],'source':source.name,'route':e}
                    saved.write_text(json.dumps(sdata,indent=1)+'\n')
        for branch in range(branches):
            lp=packet(positions,frames,normals,branch,rng)
            anchor=candidates(lp,np.zeros(36))
            if 'tiles' not in data:
                h=(7+math.sqrt(7))/2
                anchor=positions*(1+2e-8)+(float(U)-h)/4
            for leaf,path,action in groupdata[case]:
                if action!='empty':continue
                key=(case,leaf)
                cons=target(path,ids,bins)
                if cons is None:
                    targeted[(*key,'angles-exclude')]+=1
                    continue
                pts=candidates(lp,rng.uniform(-1,1,36),cons)
                status='LP-feasible' if pts is not None else 'LP-infeasible'
                targeted[(*key,status)]+=1
                tally(pts,'target',True)
            for _ in range(n_random):
                direction=rng.normal(size=36)
                pts=candidates(lp,direction)
                tally(pts,'random')
                if pts is not None and anchor is not None:
                    fraction=rng.uniform()
                    tally((1-fraction)*anchor+fraction*pts,'interpolation')
    report['canonical_images']=len(canonical)
    report['targets']={','.join(map(str,k)):v for k,v in targeted.items()}
    report['sampled']={','.join(map(str,k)):v for k,v in sampled.items()}
    report['exact_examples']=list(examples.values())
    report['visits']={','.join(map(str,k)):v for k,v in visited.items()}
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--branches',type=int,default=12)
    parser.add_argument('--random-directions',type=int,default=25)
    parser.add_argument('sources',nargs='+',type=Path)
    args=parser.parse_args()
    for src in args.sources:
        result=run(src,args.branches,args.random_directions)
        Path(src.stem+'-free.json').write_text(json.dumps(result,indent=2)+'\n')
        print(src.name,'charts',result['canonical_images'],'sampled',result['sampled'],
              'targets',dict(Counter({status:sum(v for k,v in result['targets'].items() if k.endswith(','+status))
                                 for status in ('angles-exclude','LP-infeasible','LP-feasible')})), flush=True)
