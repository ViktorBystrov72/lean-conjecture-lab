"""Build both kernels and reproduce the four vacancy search batches."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys


HERE=Path(__file__).resolve().parent
STUDY=HERE.parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--inputs",type=Path,help="offline directory with the two pinned YAML files")
    parser.add_argument("--quick",action="store_true",help="smoke test each kind on two masks and two relays")
    args=parser.parse_args()
    root=args.output.resolve()
    root.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,OPENBLAS_NUM_THREADS="1",VECLIB_MAXIMUM_THREADS="1")
    flags=["-dynamiclib"] if platform.system()=="Darwin" else ["-shared","-fPIC"]
    def run(argv):subprocess.run(argv,env=env,check=True)
    for src,name in [(STUDY/"search-history"/"packing.cpp","packing"),(HERE/"ghost.cpp","ghost")]:
        run([env.get("CXX","c++"),"-std=c++17","-O3",*flags,src,"-o",root/(name+".dylib")])
    for n,k in [(19,1),(21,3)]:
        path=root/f"donor-{n}"
        cmd=[sys.executable,HERE/"run.py",path,"--donor",str(n),"--library-dir",root]
        if args.inputs:cmd+=["--inputs",args.inputs.resolve()]
        if args.quick:cmd+=["--limit-masks","2","--variants","1"]
        run(cmd)
        relay=root/f"relay-{n}"
        run([sys.executable,HERE/"relay.py",relay,"--source",path/"best-source.json",
             "--extra",str(k),"--library-dir",root,"--starts","2" if args.quick else "1500"])
        run([sys.executable,STUDY/"follow-up"/"patch"/"exact.py",path/"best-rational.json",relay/"best-rational.json"])
    if not args.quick:
        for line in (HERE/"hashes.txt").read_text().splitlines():
            expected,file=line.split()
            actual=hashlib.sha256((root/file).read_bytes()).hexdigest()
            print(("match" if actual==expected else "platform-dependent difference"), file,
                  actual if actual!=expected else "")

if __name__=="__main__":
    main()
