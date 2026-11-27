"""Replay the exhaustive centred-wall lower-bound experiment with the case auditor."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path
import re
import subprocess

UNIT = 10**9
TEST = 4822876000


def marks_and_masks():
    def orbit(p):
        x,y = p
        for a,b in ((x,y),(y,x)):
            for _ in range(4):
                yield (a,b)
                a,b = 2000-b,a
    marks=sorted({z for p in [(390,390),(617,617),(797,359),(1000,716),(1000,1000)] for z in orbit(p)})
    actions=[{i:marks.index(tuple(orbit(p))[k]) for i,p in enumerate(marks)} for k in range(8)]
    holes=list(combinations(range(len(marks)),3))
    canonical={min(tuple(sorted(g[i] for i in h)) for g in actions) for h in holes}
    if len(marks)!=21 or len(holes)!=1330 or len(canonical)!=187:
        raise ValueError("Unexpected rack or symmetry count")
    return sorted(((1<<21)-1) ^ sum(1<<i for i in h) for h in canonical)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    parser.add_argument("--side",type=Fraction,required=True)
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--schedule", default="16:20,32:35,48:60,64:70,96:90")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--only",help="test only these mask indices (diagnostics only)")
    args=parser.parse_args()
    side=args.side*UNIT
    if side.denominator!=1 or not UNIT<=side<TEST or (TEST-int(side))%2:
        parser.error("Side must fit on the centred nanounit grid")
    bands=[tuple(map(int,x.split(":"))) for x in args.schedule.split(",")]
    if any(len(x)!=2 or not 4<=x[0]<=128 or x[1]<1 for x in bands) or args.workers<1:
        parser.error("Invalid schedule")
    masks=marks_and_masks()
    pending=list(range(len(masks))) if args.only is None else sorted(set(map(int,args.only.split(','))))
    if any(i<0 or i>=len(masks) for i in pending):parser.error("Unknown mask")
    certs={}
    calls=[]
    executable=str(args.exe.resolve())
    def store():
        data={"side":str(args.side),"rack_side":"1205719/250000","mask_count":len(masks),
              "schedule":args.schedule,"excluded":len(certs),"inconclusive_or_untested":len(masks)-len(certs),
              "all_excluded":len(certs)==len(masks),"runs":calls}
        tmp=args.output.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,indent=2)+"\n")
        tmp.replace(args.output)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for b,steps in bands:
            if not pending:break
            def test(i):
                proc=subprocess.run([executable,"--side",str(int(side)),format(masks[i],"x"),str(b),str(steps)],
                                    text=True,capture_output=True,check=True)
                verdict=proc.stdout.strip().splitlines()[-1]
                if re.fullmatch(r'EXCLUDED (empty owner \d+|guaranteed overlap \d+ \d+) round \d+',verdict):
                    status="excluded"
                elif verdict.startswith("INCONCLUSIVE "):
                    status="inconclusive"
                else:raise RuntimeError(verdict)
                return i,{"case":i,"mask":format(masks[i],"x"),"bands":b,"round_limit":steps,"verdict":verdict},status
            next_cases=[]
            for i,receipt,status in pool.map(test,pending):
                calls.append(receipt)
                if status=="excluded":certs[i]=receipt
                else:next_cases.append(i)
            pending=next_cases
            store()
            print(f"{args.side}, {b} bands: {len(certs)}/187 excluded, {len(pending)} pending in this selection",flush=True)
    store()


if __name__=="__main__":
    main()
