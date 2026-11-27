"""Exact checks of archived or regenerated candidates, using only the Python standard library."""
import argparse
import gzip
import json
import sys
import tempfile
from decimal import Decimal, localcontext
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'search-history'))
from exact_rescale import repair

def dec(q):return Decimal(q.numerator)/Decimal(q.denominator)
NAMES={'best.json','best-assigned.json','best-assigned-raw.json','raw-best.json'}

def summary(inputs):
    best=None;raw_min=None;n=lower=na=0
    with localcontext() as ctx:
        ctx.prec=65
        H=(7+Decimal(7).sqrt())/2
        for key,path in inputs:
            obj=json.loads(path.read_text());raw=Decimal(str(obj['side']))
            side,centers,ts=repair(path)
            if 2*side<=7 or (2*side-7)**2<7: lower+=1
            n+=1
            row=[key,str(raw),str(dec(side)),str(dec(side)-H),str(2*side<=7 or (2*side-7)**2<7)]
            if raw<H:
                na+=1
                if raw_min is None or raw<Decimal(raw_min[1]):raw_min=row
            if best is None or side<best[0]:best=(side,centers,ts,row)
    side,centers,ts,best_row=best
    return dict(rechecks=n,nominal_below=na,strict_improvements=lower,best=best_row,strongest_apparent=raw_min),dict(source=best_row[0],side=str(side),squares=[[str(x),str(y),str(t)] for (x,y),t in zip(centers,ts)])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,help='use the finalist files from a new run instead of checking the saved receipt')
    a=p.parse_args()
    if a.run:
        paths=sorted(p for p in a.run.rglob('*.json') if p.name in NAMES and p.parent!=a.run)
        report,witness=summary((str(p.relative_to(a.run)),p) for p in paths)
        (a.run/'exact-summary.json').write_text(json.dumps(report,indent=2)+'\n')
        (a.run/'closest-rational.json').write_text(json.dumps(witness,indent=2)+'\n')
    else:
        contents=json.loads(gzip.decompress((HERE/'saved'/'finalists.json.gz').read_bytes()))
        with tempfile.TemporaryDirectory(prefix='rack-exact-') as td:
            def items():
                target=Path(td)/'candidate.json'
                for key,obj in sorted(contents.items()):
                    target.write_text(json.dumps(obj));yield key,target
            report,witness=summary(items())
        if report!=json.loads((HERE/'saved'/'exact-summary.json').read_text()) or witness!=json.loads((HERE/'saved'/'closest-rational.json').read_text()):
            raise ValueError('Exact replay differs from saved receipt')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
