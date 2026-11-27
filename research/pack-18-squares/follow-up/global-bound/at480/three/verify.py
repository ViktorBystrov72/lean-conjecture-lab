"""Verify three split orbit exclusions directly in the centred box of side 4.80."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
EMPTY = HERE.parents[2]/"empty-cover"
sys.path.insert(0,str(EMPTY))
from build import build
from cover import controls, options, read

CASES = (22, 54, 132)
PIN = "78bec6aacebf304d942a9225e16c2f18165778ff"
SOURCE_PATH = "notes/geometry/unit-square-packing-18/replay/n18-482-base.json"
SIDE_NANO = 4_800_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group()
    location.add_argument("--source",type=Path,help="Git clone containing the pinned commit")
    location.add_argument("--table",type=Path,help="local pinned n18-482-base.json")
    parser.add_argument("--exe",type=Path,help="prebuilt kernel with --endpoint-supports")
    parser.add_argument("--jobs",type=int,default=2)
    parser.add_argument("--output",type=Path,help="write a fresh receipt")
    args = parser.parse_args()
    if not 1 <= args.jobs <= 16:
        parser.error("--jobs must be between 1 and 16")
    with TemporaryDirectory(prefix="three-orbits-480-") as scratch:
        work = Path(scratch)
        table_path = args.table
        if args.source is not None:
            table_path = work/"table.json"
            raw = subprocess.check_output(["git","-C",args.source,"show",f"{PIN}:{SOURCE_PATH}"])
            table_path.write_bytes(raw)
        controls()
        table = read(table_path)
        old = json.loads((EMPTY/"receipt.json").read_text())
        recipes = {g["case"]:g for g in old["completed_orbits"] if g["case"] in CASES}
        if sorted(recipes) != list(CASES):
            raise ValueError("Missing complete input orbits")
        if args.exe:
            exe = args.exe.resolve()
        else:
            exe = work/"geometry"
            build(exe,endpoints=True)
        jobs = []
        for case in CASES:
            mask,den,paths = table[case]
            root = recipes[case]
            if int(root["mask"],16) != mask or sorted(r["leaf"] for r in root["leaves"]) != list(range(len(paths))):
                raise ValueError(f"Bad orbit recipe for {case}")
            for row in root["leaves"]:
                leaf = row["leaf"]
                if row["kernel"] != "endpoints":
                    raise ValueError("Unexpected kernel variant")
                op = options(paths[leaf],den)
                # The angle extension reads its options first. The base
                # kernel then reads --side and the positional half-spaces.
                split = op.index("--cut") if "--cut" in op else len(op)
                cmd=[str(exe),*op[:split],"--side",str(SIDE_NANO),*op[split:],
                     format(mask,"x"),str(row["bands"]),str(row["rounds"])]
                jobs.append((case,mask,row,cmd))
        def verify(job):
            case,mask,row,cmd=job
            output=subprocess.check_output(cmd,text=True).splitlines()[-1]
            m=re.fullmatch(r"EXCLUDED (empty owner [0-9]+|guaranteed overlap [0-9]+ [0-9]+) round ([0-9]+)",output)
            if not m or int(m[2]) >= row["rounds"]:
                raise ValueError((case,row["leaf"],output))
            owners=list(map(int,re.findall(r"[0-9]+",m[1])))
            if len(owners)!=len(set(owners)) or any(i>=21 or not mask>>i&1 for i in owners):
                raise ValueError("Invalid terminal owner(s)")
            return {"case":case,"leaf":row["leaf"],"mask":format(mask,"x"),"bands":row["bands"],
                    "rounds":row["rounds"],"verdict":output}
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results=list(pool.map(verify,jobs))
    receipt={"side":"24/5","rack_side":"1205719/250000","side_nanounits":SIDE_NANO,
             "kernel":"independent, including direct endpoint supports","cases":list(CASES),
             "table_commit":PIN,"table_sha256":"d6fa37860cde0d0e8f8ddedc25508f478fe30112be16e79697cb9ab59c54f086",
             "leaves":results}
    if args.output:
        args.output.write_text(json.dumps(receipt,indent=2)+"\n")
    else:
        old=json.loads((HERE/"receipt.json").read_text())
        if {k:v for k,v in old.items() if k!="leaves"}!={k:v for k,v in receipt.items() if k!="leaves"}:
            raise ValueError("Receipt scope mismatch")
        # A different valid contradiction at the same leaf is acceptable.
        if [[r[k] for k in ("case","leaf","mask","bands","rounds")] for r in old["leaves"]] != [
                [r[k] for k in ("case","leaf","mask","bands","rounds")] for r in results]:
            raise ValueError("Recipe changed")
    print(f"All {len(results)} leaves in orbits 22, 54 and 132 are excluded directly at L=24/5.")


if __name__=="__main__":
    main()
