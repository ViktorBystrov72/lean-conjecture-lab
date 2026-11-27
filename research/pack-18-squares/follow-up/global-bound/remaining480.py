"""Generate and independently replay finite inner-point traces for selected cases."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from sweep import marks_and_masks


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--cases",required=True)
    ap.add_argument("--workers",type=int,default=2)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--schedule",default="96:32,128:40")
    ap.add_argument("--side-nano",type=int,default=4800000000)
    args=ap.parse_args()
    ms=marks_and_masks()
    args.output.mkdir(parents=True,exist_ok=True)
    pending=sorted(set(map(int,args.cases.split(','))))
    if not pending or any(not 0<=i<len(ms) for i in pending):ap.error("Invalid orbit list")
    exe=args.exe.resolve()
    allrows=[]
    for b,r in (map(int,x.split(':')) for x in args.schedule.split(',')):
        if not pending:break
        def test(i):
            mask=format(ms[i],"x")
            trace=args.output/f"case-{i}-{b}.pts"
            params=[exe,mask,str(b),str(r)]
            result=subprocess.run([*params,'generate',trace,str(args.side_nano)],text=True,capture_output=True)
            last=result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if result.returncode==0 and last.startswith('EXCLUDED '):
                check=subprocess.run([*params,'verify',trace,str(args.side_nano)],check=True,capture_output=True,text=True)
                if check.stdout.strip().splitlines()[-1]!=last:raise ValueError("Replay mismatch")
                status="excluded"
            elif result.returncode==1 and last=="UNDECIDED":
                status="inconclusive"
            else:raise RuntimeError((i,result.returncode,last,result.stderr[-250:]))
            return {"case":i,"mask":mask,"side_nanounits":args.side_nano,"bands":b,"rounds":r,
                    "status":status,"verdict":last,"trace_sha256":sha256(trace.read_bytes()).hexdigest()}
        nxt=[]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(test,pending):
                allrows.append(row)
                if row['status']!='excluded':nxt.append(row['case'])
                print(row['case'],row['status'],b,flush=True)
                target=args.output/'summary.json'
                tmp=target.with_suffix('.tmp')
                tmp.write_text(json.dumps(allrows,indent=2)+'\n');tmp.replace(target)
        pending=nxt
    print("Inconclusive in this selection:",pending,flush=True)


if __name__=="__main__":
    main()
