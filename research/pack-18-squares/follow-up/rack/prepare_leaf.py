"""Export the seven live outer envelopes for orbit 55, solely as search proposals."""
import json
import os
from pathlib import Path
import sys
import subprocess

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(STUDY/'audit'))
from rack_check import masks
from kernel_control import groups, params


def main():
    work=Path(os.environ['PACK18_RUN'])
    source=Path(os.environ['PACK18_REPLAY'])
    kernel=work/'kernel-control'
    kernel.mkdir()
    prepare=(
        'import json,sys; from pathlib import Path; from inhabited_endpoint import worker,certified_init; '
        'd=Path(sys.argv[1]); certified_init(json.loads(Path("stabs18-endpoint-window.json").read_text()),128,d/"i"); worker(d)'
    )
    subprocess.run([sys.executable,'-c',prepare,kernel],cwd=source,check=True)
    owners=[i for i in range(21) if masks[55]>>i&1]
    out=[]
    for name,path,kind in groups[55]:
        if kind == 'empty': continue
        command=' '.join(map(str,[*params(55,name),18,*owners,*path]))+'\n'
        p=subprocess.run([kernel/'geometry',kernel/'i'],input=command,text=True,capture_output=True,check=True)
        lines=p.stdout.splitlines()
        if len(lines)!=2 or not lines[1].startswith('OPEN'): raise ValueError('Expected a live envelope')
        vals=iter(lines[0].split())
        if next(vals)!='POSE2':raise ValueError('Unknown envelope encoding')
        n,B=int(next(vals)),int(next(vals))
        pairs=[[int(next(vals)),int(next(vals))] for _ in range(B)]
        cells=[]
        for _ in range(n):
            owner=int(next(vals));bands=[]
            for band in pairs:
                verts=[[int(next(vals)),int(next(vals))] for _ in range(int(next(vals)))]
                if verts: bands.append([band,verts])
            cells.append([owner,bands])
        if n!=18 or next(vals,None) is not None: raise ValueError('Invalid enclosure')
        out.append(dict(name=name,kind=kind,cells=cells))
    (work/'leaf55.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
if __name__=='__main__':main()
