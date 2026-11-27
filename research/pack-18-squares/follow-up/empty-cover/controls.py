"""Test the new angular cuts on exact feasible control placements."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'terminal-audit'),str(HERE.parents[1]/'audit')]
from controls import contains
from rack_check import exact_source,geometry,marks


def physical(exe,path):
    side,tiles=exact_source(path)
    geometry(tiles,side)
    assigned={}
    for x,y,c,s in tiles:
        ds=[max(abs((xx-x)*c+(yy-y)*s),abs((yy-y)*c-(xx-x)*s)) for xx,yy in marks]
        i=ds.index(min(ds)); assigned[i]=x,y,c,s
    if len(assigned)!=18:raise ValueError('Shared owner')
    mask=format(sum(1<<i for i in assigned),'x')
    i=next(i for i,(_,_,c,s) in assigned.items() if c==1 and s==0)
    with tempfile.TemporaryDirectory() as scratch:
        dump=Path(scratch)/'domains'
        # The chosen axis-aligned square has two representations t=0 and 1.
        # A cut t<=0 forces t=0. The last angular band must be eliminated.
        job=[str(exe),'--angle',str(i),'le','0','128',mask,'32','12',str(dump)]
        result=subprocess.run(job,check=True,capture_output=True,text=True)
        if not result.stdout.splitlines()[-1].startswith('INCONCLUSIVE'):raise ValueError('Control excluded')
        retained={}
        for l in dump.read_text().splitlines():
            j,k,n,*pairs=map(int,l.split())
            if len(pairs)!=2*n:raise ValueError('Invalid enclosure')
            retained[j,k]=list(zip(pairs[::2],pairs[1::2]))
    if any(retained[i,k] for k in range(1,32)):raise ValueError('Angle cut failed to remove an out-of-range band')
    for j,(x,y,c,s) in assigned.items():
        bands=set()
        for _ in range(4):
            if c>=0 and s>=0:
                bands.update(k for k in range(32) if k*(1+c)<=32*s<=(k+1)*(1+c))
            c,s=-s,c
        if j==i:bands&={0}
        if not any(contains(retained[j,k],(x*10**9,y*10**9)) for k in bands):
            raise ValueError('Lost a true pose on a closed angular split')
    return dict(layout=path.name,owner=i,mask=mask,actual_centres_retained=18)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--layout-dir',type=Path,default=HERE.parents[1]/'layouts')
    args=p.parse_args()
    print(json.dumps([physical(args.exe.resolve(),args.layout_dir/name) for name in
      ('hamalainen-exact.json','gustafson-exact.json','cantrell-exact.json','gensane-ryckelynck-exact.json')],indent=2))
