"""Verify the full 187-orbit exclusion in the centred square of side 24/5."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import zlib

HERE=Path(__file__).resolve().parent
FOLLOW=HERE.parent.parent
SIDE=4800000000


def import_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(cmd):
    return subprocess.check_output(list(map(str,cmd)),text=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,help="local upstream Git repository containing the pinned case data")
    ap.add_argument("--workers",type=int,default=3)
    ap.add_argument("--receipt",type=Path)
    args=ap.parse_args()
    if args.workers<1 or not __debug__:ap.error("Positive worker count and enabled assertions required")
    manifest=json.loads((HERE/"manifest.json").read_text())
    if manifest['side']!='24/5' or manifest['wall_side_nano']!=SIDE or manifest['rack_side_nano']!=4822876000:
        raise ValueError("Wrong square or rack")
    orbit=import_file("case_masks_independent",FOLLOW/"terminal-audit/sweep.py")
    masks=orbit.case_masks()
    direct=manifest["direct"]; certified=manifest["certified"]
    cases=[v["case"] for v in direct+certified]+manifest["three"]+manifest["special"]+manifest["guard"]
    if len(cases)!=187 or set(cases)!=set(range(187)) or len(masks)!=187:
        raise ValueError("Incomplete or overlapping coverage plan")
    if [manifest[k] for k in ("three","special","guard")]!=[[22,54,132],[0,53,55],[137]]:
        raise ValueError("Unexpected delegated domains")
    for row in direct+certified:
        if masks[row["case"]]!=int(row["mask"],16):raise ValueError("Wrong symmetry representative")
    packets=json.loads(zlib.decompress((HERE/"points.zlib").read_bytes()))
    if set(packets)!=set(str(r["case"]) for r in certified):raise ValueError("Wrong trace inventory")
    upstream=import_file("pinned_external_table",FOLLOW.parent/"audit/replay.py")
    with TemporaryDirectory(prefix="verify-480-") as tmp:
        work=Path(tmp)
        tables=upstream.source_files(args.source.resolve() if args.source else None,work)
        core=work/"core"; alternate=work/"alternate"; angular=work/"angular"
        subprocess.run([os.environ.get("CXX","c++"),"-std=c++17","-O3",
                        FOLLOW/"terminal-audit/case_audit.cpp","-o",core], check=True)
        subprocess.run([sys.executable,FOLLOW/"row-guards/independent480/build.py",alternate],check=True)
        subprocess.run([sys.executable,FOLLOW/"empty-cover/build.py",angular,"--endpoint-supports"],check=True)
        rack=run([core,"--rack",512]).strip()
        if not re.fullmatch(r"RACK COVERED [1-9]\d* leaves [1-9]\d* nodes, max depth \d+",rack):
            raise ValueError("Coverage of all tile poses was not confirmed")
        print(rack,flush=True)

        def primary(row):
            b,r=row["bands"],row["round_limit"]
            verdict=run([core,"--side",SIDE,row["mask"],b,r]).strip().splitlines()[-1]
            if not re.fullmatch(r"EXCLUDED (empty owner \d+|guaranteed overlap \d+ \d+) round \d+",verdict):
                raise ValueError((row["case"],verdict))
            return verdict
        def secondary(row):
            i=row["case"];data=packets[str(i)].encode()
            if sha256(data).hexdigest()!=row["trace_sha256"]:raise ValueError(("Wrong hints",i))
            path=work/f"trace-{i}.txt";path.write_bytes(data)
            verdict=run([alternate,row["mask"],row["bands"],row["rounds"],"verify",path,SIDE]).strip().splitlines()[-1]
            if verdict!=row["verdict"] or not verdict.startswith(f"EXCLUDED mask {masks[i]} "):
                raise ValueError((i,verdict))
            return verdict
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            first=list(pool.map(primary,direct))
            print(f"Independent geometry excluded {len(first)} full orbits.",flush=True)
            second=list(pool.map(secondary,certified))
            print(f"Checked integer traces for {len(second)} additional full orbits.",flush=True)
        a=run([sys.executable,HERE/"three/verify.py","--table",tables/"n18-482-base.json"])
        b=run([sys.executable,FOLLOW/"row-guards/independent480/replay.py","--kernel",alternate])
        c=run([sys.executable,FOLLOW/"endpoint-guards/side480.py","--case",137,"--table-dir",tables,
               "--exe",angular,"--jobs",args.workers])
        print(a.strip(),b.strip(),c.strip(),sep="\n",flush=True)
    report={"side":"24/5","rack":rack,"raw_unused_triples":1330,"classes_excluded":len(cases),
            "direct":len(first),"integer_traces":len(second),"remaining_routes":{k:manifest[k] for k in ("three","special","guard")},
            "manifest_sha256":sha256((HERE/"manifest.json").read_bytes()).hexdigest(),
            "certificates_sha256":sha256((HERE/"points.zlib").read_bytes()).hexdigest()}
    print("All 187 symmetry classes excluded at side 24/5.")
    if args.receipt:args.receipt.write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    main()
