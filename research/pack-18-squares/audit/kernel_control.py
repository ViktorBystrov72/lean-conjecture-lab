"""Test individual kernel leaves against externally supplied exact physical poses.

The foreign geometry executable provides polygons in angular bands as witness
data. All ownership checks and all tests of whether a real centre survives in
a polygon are independent of the foreign proof checker.
"""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
from subprocess import run
import argparse,json,os
from rack_check import F,geometry,exact_source,U
from route_witnesses import allowed,angle_bins,canonical_images,load_groups,REPLAY

HERE=Path(os.environ["PACK18_RUN"])
groups=load_groups()

def params(case,leaf):
    if case==137:return [220,8,896,130]
    i,j=map(int,leaf.split('.'))
    if case==53:
        rows=json.loads((REPLAY/'full-endpoint-mask-cases.json').read_text())
        return rows[i][2][j][1]
    if case==55:
        rows=json.loads((REPLAY/'second-endpoint-mask-cases.json').read_text())
        return rows[i][2][j][1]
    rows=json.loads((REPLAY/f'residual-{case}-cases.json').read_text())
    return rows[i][1][j][1]

def point_in_polygon(x,y,vertices):
    if not vertices:return False
    if not min(k for k,_ in vertices)<=x<=max(k for k,_ in vertices):return False
    if not min(l for _,l in vertices)<=y<=max(l for _,l in vertices):return False
    turns=[(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]) for a,b in zip(vertices,vertices[1:]+vertices[:1])]
    return all(t>=0 for t in turns) or all(t<=0 for t in turns)

def contains_angle(c,s,k,d):
    for _ in range(4):
        if c>=0 and s>=0 and k*(1+c)<=d*s<=(k+1)*(1+c): return True
        c,s=-s,c
    return False

def check_output(raw,physical,translations=((0,0),)):
    lines=raw.splitlines()
    if len(lines)!=2 or not lines[-1].startswith('OPEN'):
        raise ValueError('geometry worker did not return an open pose enclosure')
    vals=iter(lines[0].split())
    assert next(vals)=='POSE2'
    n,B=int(next(vals)),int(next(vals))
    assert n==18
    bands=[(int(next(vals)),int(next(vals))) for _ in range(B)]
    survivors={}
    for _ in range(n):
        owner=int(next(vals));x,y,c,s=physical[owner]
        kept=[]
        for k,d in bands:
            vertices=[(int(next(vals)),int(next(vals))) for _ in range(int(next(vals)))]
            if vertices and contains_angle(c,s,k,d) and all(
                point_in_polygon((x+dx)*1000000,(y+dy)*1000000,vertices)
                for dx,dy in translations
            ):kept.append([k,d])
        survivors[owner]=kept
    assert next(vals,None) is None and set(survivors)==set(physical)
    return {'survivors':survivors,'lost':[i for i,v in survivors.items() if not v],'angular_bands':B}

def process_leaf(task):
    filename,sym,case,leaf,pose,path=task
    request=' '.join(map(str,[*params(case,leaf),18,*sorted(pose),*path]))+'\n'
    cache=HERE/'kernel-control'/f'{case}-{leaf}.out'
    if cache.exists():
        raw=cache.read_text()
    else:
        result=run([HERE/'kernel-control/geometry',HERE/'kernel-control/i'],text=True,input=request,capture_output=True,check=True)
        raw=result.stdout
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w',dir=cache.parent,delete=False) as tf: tf.write(raw)
        Path(tf.name).replace(cache)
    output=check_output(raw,pose)
    report={'file':filename,'sym':sym,'case':case,'leaf':leaf,'path':path,**output}
    return report

def input_tiles(path):
    data=json.loads(path.read_text())
    if 'tiles' in data:return F(data['side']),[tuple(map(F,t)) for t in data['tiles']]
    return exact_source(path)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('sources',nargs='+',type=Path);ap.add_argument('--output',default='kernel-check.json');args=ap.parse_args()
    jobs=[]
    for fn in args.sources:
        side,tiles=input_tiles(fn);geometry(tiles,side);assert side<=U
        for sym,case,pose in canonical_images(tiles):
            bins={i:angle_bins(c,s) for i,(_,_,c,s) in pose.items()}
            for leaf,path,act in groups[case]:
                if allowed(pose,path,bins):jobs.append((fn.name,sym,case,leaf,pose,path))
    print('kernel requests',len(jobs),flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        results=[]
        for res in ex.map(process_leaf,jobs):
            results.append(res)
            print(res['file'],res['sym'],res['case'],res['leaf'],'lost',res.get('lost'),res.get('error',''),flush=True)
    Path(args.output).write_text(json.dumps(results,indent=2)+'\n')
