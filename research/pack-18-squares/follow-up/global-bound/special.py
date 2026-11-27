"""Try continuous exclusion at a smaller true side across all six endpoint classes.

This is a search for empty regions, including regions labelled 'faces' or
'chord' by the producer. It does not assume that a proposed geometric
endpoint guard has already been verified.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"empty-cover"))
from cover import case_masks, options
sys.path.insert(0,str(HERE.parent.parent/"audit"))
UNIT, TEST = 10**9, 4822876000


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    parser.add_argument("--tables",type=Path,required=True)
    parser.add_argument("--side",type=Fraction,default=Fraction(24,5))
    parser.add_argument("--schedule",default="24:30,40:45,64:65")
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--cases",default="53,55,82,92,115,137")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    side=args.side*UNIT
    if not UNIT<=side<=TEST or side.denominator!=1 or (TEST-int(side))%2:
        parser.error("Invalid side")
    if args.workers<1:parser.error("Expected positive worker count")
    os.environ["PACK18_REPLAY"]=str(args.tables.resolve())
    from route_witnesses import load_groups
    masks=case_masks()
    selected=set(map(int,args.cases.split(',')))
    groups=load_groups()
    tasks=[(case,leaf,tuple(path),action) for case,items in sorted(groups.items()) if case in selected
           for leaf,path,action in items]
    if not selected<=set(groups) or not tasks: parser.error("Unknown or empty class list")
    completed={}
    receipts=[]
    exe=str(args.exe.resolve())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for band,limit in (map(int,stage.split(':')) for stage in args.schedule.split(',')):
            pending=[task for task in tasks if task[:2] not in completed]
            if not pending:break
            def evaluate(task):
                case,leaf,flat,action=task
                cuts=list(zip(flat[::3],flat[1::3],flat[2::3]))
                argv=[exe,*options(cuts,128),"--side",str(int(side)),format(masks[case],"x"),str(band),str(limit)]
                r=subprocess.run(argv,check=True,capture_output=True,text=True)
                result=r.stdout.strip().splitlines()[-1]
                if not (re.fullmatch(r"EXCLUDED (empty owner \d+|guaranteed overlap \d+ \d+) round \d+",result)
                        or result in ("INCONCLUSIVE budget","INCONCLUSIVE fixed point")):
                    raise RuntimeError(result)
                return case,leaf,{"published_action":action,"case":case,"leaf":leaf,"bands":band,"rounds":limit,
                                  "verdict":result}
            for i,(case,leaf,receipt) in enumerate(pool.map(evaluate,pending)):
                receipts.append(receipt)
                if receipt["verdict"].startswith("EXCLUDED "):completed[case,leaf]=receipt
                if (i+1)%25==0: print(f"{band}: {i+1}/{len(pending)} processed",flush=True)
            by_case={case:{"excluded":sum(k[0]==case for k in completed),
                           "total":len(groups[case])} for case in sorted(selected)}
            data={"side":str(args.side),"table_ref":"78bec6aacebf304d942a9225e16c2f18165778ff",
                  "by_case":by_case,"total_excluded":len(completed),"total_regions":len(tasks),
                  "unresolved":[[c,l] for c,l,_,_ in tasks if (c,l) not in completed],"runs":receipts}
            scratch=args.output.with_suffix(".tmp")
            scratch.write_text(json.dumps(data,indent=2)+"\n")
            scratch.replace(args.output)
            print(f"{band}: {len(completed)} of {len(tasks)} regions closed; {by_case}",flush=True)


if __name__=="__main__":
    main()
