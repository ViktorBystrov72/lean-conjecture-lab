"""Replay the four double-probe special classes at side 4.80 using our own enclosures."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from check_guards import FLIP_Y, FIRST_ROWS, SECOND_ROWS, MIDDLE, owner_map, guarded_leaf


HERE=Path(__file__).resolve().parent
CASES=(82,92,115,137)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def leaves(source):
    geometry=module("packing_endpoint_cover", HERE.parent/"endpoint-cover/verify.py")
    data=geometry.inputs(source)
    masks,actions=geometry.inventory(data["stabs18-endpoint-window.json"])
    private=json.loads((HERE.parent/"endpoint-cover/private-points.json").read_text())
    out={}
    for case in CASES:
        mask=masks[case]
        owners={i for i in range(21) if mask>>i&1}
        geometry.roots_check(case,data,mask,owners,actions,private[str(case)])
        roots=geometry.normalized_roots(case,data,mask,owners)
        for i,(path,subs) in enumerate(roots):
            for j,(suffix,_,action) in enumerate(subs):
                cuts=path+suffix
                label=str(i) if case==137 else f"{i}.{j}"
                if case==137:
                    roles=((0,0,int(FLIP_Y[i])),FIRST_ROWS,SECOND_ROWS,MIDDLE)
                elif action==["empty"]:
                    roles=None
                else:
                    sym,ids,how=action
                    if how!="faces" or len(ids)!=6:raise ValueError("Unexpected nonempty residual action")
                    roles=(tuple(sym),(tuple(ids[0]),tuple(ids[1])),(tuple(ids[2]),tuple(ids[3])),tuple(ids[4:]))
                out[case,label]=(mask,list(zip(cuts[::3],cuts[1::3],cuts[2::3],strict=True)),roles)
    if Counter(case for case,_ in out)!={82:20,92:19,115:19,137:6}:
        raise ValueError("Incorrect terminal inventory")
    return out


def pose_boxes(path,mask,B):
    owners={i:[] for i in range(21) if mask>>i&1}
    seen=set()
    with path.open() as f:
        for line in f:
            i,k,n,*coords=map(int,line.split())
            if i not in owners or (i,k) in seen or not 0<=k<B or n<0 or len(coords)!=2*n:
                raise ValueError("Malformed outer polygon")
            seen.add((i,k))
            if n:
                x,y=coords[::2],coords[1::2]
                # The outer geometry uses nanounits. Round each lower/upper
                # coordinate outward to the microunits expected by the guard.
                owners[i].append([k,B,min(x)//1000,-((-max(x))//1000),
                                  min(y)//1000,-((-max(y))//1000)])
    if len(seen)!=18*B or not all(owners.values()):
        raise ValueError("Incomplete outer-polygon inventory")
    return owners


def run_case(exe,directory,row,leaf):
    mask,cuts,roles=leaf
    case,name,B,rounds=row["case"],row["leaf"],row["bands"],row["rounds"]
    if int(row["mask"],16)!=mask or not 4<=B<=128 or not 1<=rounds<=256:
        raise ValueError("Bad terminal recipe")
    angle=[]
    coords=[]
    for i,kind,value in cuts:
        sense=("le","ge")[kind%2]
        if kind>=4:
            angle.extend(["--angle",str(i),sense,str(value),"128"])
        else:
            coords.extend(["--cut",str(i),"xy"[kind//2]+"-"+sense,str(1000*value)])
    cmd=[str(exe),*angle,"--side","4800000000",*coords,format(mask,"x"),str(B)]
    path=directory/f"{case}-{name}.pol"
    proc=subprocess.run([*cmd,str(rounds),str(path)],check=True,capture_output=True,text=True)
    lines=proc.stdout.splitlines()
    verdict=lines[-1]
    if re.fullmatch(r"EXCLUDED (?:empty owner [0-9]+|guaranteed overlap [0-9]+ [0-9]+) round [0-9]+",verdict):
        return "geometry"
    if row["method"]!="guard" or roles is None:
        raise ValueError((case,name,verdict))
    if verdict=="INCONCLUSIVE fixed point" and not path.is_file():
        # The unmodified program only emits a dump on budget exhaustion.
        # The preceding, possibly looser, enclosure is also sufficient if
        # the guard succeeds on it.
        r=int(lines[-2].split()[0])
        if r>0:
            subprocess.run([*cmd,str(r),str(path)],check=True,stdout=subprocess.DEVNULL)
    if not path.is_file():raise ValueError((case,name,"no polygons"))
    boxes=pose_boxes(path,mask,B)
    sym,first,second,middle=roles
    relabel=owner_map(sym)
    required=set(first[0]+first[1]+second[0]+second[1]+middle)
    active=[[i,states] for i,states in boxes.items() if relabel[i] in required]
    guarded_leaf(active,sym,first,second,middle)
    return "guard"


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--table-dir",type=Path,help="local directory of pinned case JSONs")
    ap.add_argument("--exe",type=Path,help="prebuilt empty-cover kernel with --endpoint-supports")
    ap.add_argument("--jobs",type=int,default=2)
    ap.add_argument("--case",type=int,choices=CASES)
    args=ap.parse_args()
    if args.jobs<1:ap.error("--jobs must be positive")
    table=leaves(args.table_dir)
    receipt=json.loads((HERE/"side480.json").read_text())
    side=Fraction(receipt["side"])
    if side != Fraction(24,5) or side <= 4 or (side-3)**2+(side-4)**2 >= 4:
        raise ValueError("A successful two-probe guard would not contradict the trial side")
    recipes=receipt["leaves"]
    keys=[(row["case"],row["leaf"]) for row in recipes]
    if len(keys)!=len(set(keys)) or set(keys)!=set(table):
        raise ValueError("Receipt does not cover all 64 terminals")
    with TemporaryDirectory(prefix="pack18-four-classes-") as scratch:
        work=Path(scratch)
        if args.exe:
            exe=args.exe.resolve()
        else:
            exe=work/"geometry"
            module("packing_angle_build",HERE.parent/"empty-cover/build.py").build(exe,endpoints=True)
        def verify(row):
            return (row["case"],run_case(exe,work,row,table[row["case"],row["leaf"]]))
        chosen=[r for r in recipes if args.case is None or args.case==r["case"]]
        with ThreadPoolExecutor(args.jobs) as pool:
            counts=Counter(pool.map(verify,chosen))
        for c in CASES:
            if args.case is None or args.case==c:
                print(f"Case {c}: {counts[c,'geometry']} direct contradictions, {counts[c,'guard']} valid lower-bound guards.")
        print(f"Checked {sum(counts.values())} of {len(table)} terminals at side 4.80.")


if __name__=="__main__":
    main()
