"""Extract moment-independent pose enclosures for the seven-role guards in cases 53 and 55."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zlib


HERE=Path(__file__).resolve().parent
AUDIT=HERE.parent.parent/"audit"
sys.path.insert(0,str(AUDIT))
from rack_check import marks, masks


def instructions(raw):
    os.environ["PACK18_REPLAY"]=str(raw)
    from route_witnesses import load_groups
    routes=load_groups()
    jobs=[]
    for orbit,name in ((53,"full-endpoint-mask-cases.json"),(55,"second-endpoint-mask-cases.json")):
        recipes=json.loads((raw/name).read_text())
        routes_by_name={leaf:(path,action) for leaf,path,action in routes[orbit]}
        for r,(_,_,leaves) in enumerate(recipes):
            for l,(_,params,rule) in enumerate(leaves):
                if rule==["empty"]:continue
                leaf=f"{r}.{l}"; path,kind=routes_by_name[leaf]
                if kind!=rule[-1]: raise ValueError("Terminal action mismatch")
                roles=[2,0,1,18,13,5,11] if orbit==53 else rule[1]
                if len(set(roles))!=7:raise ValueError("Expected seven distinct roles")
                jobs.append((orbit,leaf,path,params,rule[0],roles,kind))
    if len(jobs)!=78:raise ValueError("Expected 78 chord or face leaves")
    return jobs


def boxes(raw):
    lines=raw.splitlines()
    if len(lines)!=2 or not lines[1].startswith("OPEN "):raise ValueError("Expected source pose enclosures")
    tokens=iter(lines[0].split())
    if next(tokens)!="POSE2":raise ValueError("Expected POSE2")
    n,b=int(next(tokens)),int(next(tokens))
    if n!=18 or not 1<=b<=8192:raise ValueError("Bad enclosure headers")
    bands=[(int(next(tokens)),int(next(tokens))) for _ in range(b)]
    if len(set(bands))!=b or any(not 0<=k<d<=8192 for k,d in bands):raise ValueError("Invalid band")
    owners={}
    for _ in range(n):
        j=int(next(tokens))
        if j in owners:raise ValueError("Duplicate owner")
        rows=[]
        for k,d in bands:
            count=int(next(tokens))
            if not 0<=count<=10000:raise ValueError("Invalid polygon size")
            points=[(int(next(tokens)),int(next(tokens))) for _ in range(count)]
            if points:
                xs,ys=zip(*points)
                rows.append([k,d,min(xs),max(xs),min(ys),max(ys)])
        if not rows:raise ValueError("Owner without possible pose")
        owners[j]=rows
    if next(tokens,None) is not None:raise ValueError("Trailing enclosure data")
    return owners


def sym_point(i,g):
    p=marks[i]
    sw,sx,sy=g
    U=F(4822876,1000000)
    q=(U-p[sw] if sx else p[sw], U-p[1-sw] if sy else p[1-sw])
    return marks.index(q)


def extract(job, exe, init):
    orbit,leaf,path,params,sym,roles,kind=job
    owners=[j for j in range(21) if masks[orbit]>>j&1]
    req=" ".join(map(str,[*params,len(owners),*owners,*path]))+"\n"
    raw=subprocess.run([exe,init],input=req,text=True,check=True,capture_output=True).stdout
    rows=boxes(raw)
    if set(rows)!=set(owners):raise ValueError("Owner mismatch")
    labels={sym_point(j,sym):j for j in owners}
    if not set(roles)<=set(labels):raise ValueError("Missing transformed owner")
    return {"case":orbit,"leaf":leaf,"kind":kind,"sym":sym,"roles":roles,
            "rows":[rows[labels[j]] for j in roles]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tables",type=Path)
    parser.add_argument("geometry",type=Path)
    parser.add_argument("init",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--workers",type=int,default=3)
    args=parser.parse_args()
    jobs=instructions(args.tables.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        def invoke(j):return extract(j,args.geometry.resolve(),args.init.resolve())
        for item in pool.map(invoke,jobs):
            results.append(item)
            if len(results)%10==0:print(f"Enclosures: {len(results)}/{len(jobs)}",flush=True)
    data=json.dumps(results,separators=(",",":")).encode()
    args.output.write_bytes(zlib.compress(data,9))
    print("Uncompressed receipt SHA-256:",sha256(data).hexdigest())


if __name__=="__main__":
    main()
