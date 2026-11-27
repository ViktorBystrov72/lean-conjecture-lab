"""Check exact known square packings inside the centre enclosures.

For every owner, test the algebraic centre in every surviving angular band
that actually contains the square orientation, including either axis endpoint.
The continuous checker need only retain at least one representation.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sweep import labels


def sign_of_cross(a,b,p):
    return ((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))


def contains(poly,p):
    if not poly:
        return False
    if len(poly)==1:
        return p[0]==poly[0][0] and p[1]==poly[0][1]
    if len(poly)==2:
        a,b=poly
        return (sign_of_cross(a,b,p)==0 and
                min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and
                min(a[1],b[1])<=p[1]<=max(a[1],b[1]))
    return all(sign_of_cross(a,b,p)>=0 for a,b in zip(poly,poly[1:]+poly[:1]))


def verify(exe,layout,bands,rounds):
    from rack_check import exact_source, geometry, marks
    side, tiles=exact_source(layout)
    geometry(tiles,side)
    owners={}
    for x,y,c,s in tiles:
        distances=[max(abs((X-x)*c+(Y-y)*s),abs((Y-y)*c-(X-x)*s)) for X,Y in marks]
        least=min(distances)
        chosen=[i for i,d in enumerate(distances) if d==least]
        if len(chosen)!=1 or least>=1/2:
            raise ValueError("The physical control must have distinct, strict nearest marks")
        if chosen[0] in owners:
            raise ValueError("Shared assigned mark")
        owners[chosen[0]]=(x,y,c,s)
    mask=sum(1<<i for i in owners)
    with tempfile.TemporaryDirectory() as t:
        dump=Path(t)/"domains.txt"
        run=subprocess.run([str(exe),format(mask,"x"),str(bands),str(rounds),str(dump)],check=True,capture_output=True,text=True)
        if not run.stdout.splitlines()[-1].startswith("INCONCLUSIVE") or not dump.is_file():
            raise ValueError(run.stdout)
        received={}
        for line in dump.read_text().splitlines():
            i,k,n,*coords=map(int,line.split())
            if len(coords)!=2*n or (i,k) in received:raise ValueError("Malformed enclosure")
            received[i,k]=list(zip(coords[::2],coords[1::2]))
    if set(received)!={(i,k) for i in owners for k in range(bands)}:raise ValueError("Incomplete pose dump")
    for i,(x,y,c,s) in owners.items():
        matches=[]
        for _ in range(4):
            if c>=0 and s>=0:
                matches.extend(k for k in range(bands) if k*(1+c)<=bands*s<=(k+1)*(1+c))
            c,s=-s,c
        if not any(contains(received[i,k],(x*10**9,y*10**9)) for k in matches):
            raise ValueError(f"Lost square {i} in {layout.name}")
    return dict(layout=layout.name,mask=format(mask,'x'),bands=bands,rounds=rounds,survived=len(owners))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--layout-dir',type=Path,default=Path(__file__).resolve().parents[2]/'layouts')
    p.add_argument('--arithmetic-dir',type=Path,default=Path(__file__).resolve().parents[2]/'audit')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    sys.path.insert(0,str(args.arithmetic_dir.resolve()))
    from rack_check import grid
    if labels()!=grid:raise ValueError('Differing mark indexes')
    reports=[verify(args.exe.resolve(),args.layout_dir/name,32,12) for name in
             ('hamalainen-exact.json','gustafson-exact.json','cantrell-exact.json','gensane-ryckelynck-exact.json')]
    print(json.dumps(reports,indent=2))
    if args.output:args.output.write_text(json.dumps(reports,indent=2)+'\n')


if __name__=='__main__':main()
