"""Export outer centre rectangles for class 137 from the pinned geometry worker."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from check_guards import MASK, OWNERS, PATHS, FLIP_Y, ACTIVE, cover, require, label_reflection


HERE=Path(__file__).resolve().parent
STUDY=HERE.parents[1]


def extract(raw, owners_expected=OWNERS):
    lines=raw.decode("ascii").splitlines()
    require(len(lines)==2 and lines[1].startswith("OPEN"),"geometry response is not an open family")
    numbers=iter(lines[0].split())
    require(next(numbers)=="POSE2" and int(next(numbers))==18,"geometry header")
    bands=int(next(numbers))
    angles=[(int(next(numbers)),int(next(numbers))) for _ in range(bands)]
    require(4<=bands<=1024 and angles==sorted(set(angles)) and len({d for _,d in angles})==1,
            "invalid band grid")
    owners=[]
    for _ in range(18):
        owner=int(next(numbers))
        records=[]
        for k,d in angles:
            count=int(next(numbers))
            require(0<=k<d<=8192 and 0<=count<=2000,"vertex or band limits")
            verts=[(int(next(numbers)),int(next(numbers))) for _ in range(count)]
            if verts:
                xs,ys=zip(*verts)
                records.append([k,d,min(xs),max(xs),min(ys),max(ys)])
        require(records,"empty owner")
        owners.append([owner,records])
    require(next(numbers,None) is None and [i for i,_ in owners]==owners_expected,"owner ordering or trailing input")
    return owners


def store(path, records):
    # Export only the boxes required by the endpoint argument, after the
    # strict full-table parser has validated the geometry response.
    remap=label_reflection()
    compact=[[[j,rows] for j,rows in record if (remap[j] if flip else j) in ACTIVE]
             for record,flip in zip(records,FLIP_Y,strict=True)]
    payload=json.dumps(compact,separators=(",",":")).encode()
    path.write_bytes(gzip.compress(payload,mtime=0))
    return hashlib.sha256(payload).hexdigest()


def pinned_files(source,work):
    # This project helper only fetches and hash-checks the pinned source,
    # and extracts its archive into temporary storage.
    spec=importlib.util.spec_from_file_location("audit_fetch",STUDY/"audit/replay.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.source_files(source,work)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,help="an existing clone with Mira's pinned revision")
    parser.add_argument("--raw",type=Path,help="read six existing leaf-N.txt worker responses")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--jobs",type=int,choices=(1,2,3),default=2)
    args=parser.parse_args()
    if args.raw:
        records=[extract((args.raw/f"leaf-{j}.txt").read_bytes()) for j in range(6)]
    else:
        with tempfile.TemporaryDirectory(prefix="pack18-leaves-") as tmp:
            work=Path(tmp)
            source=pinned_files(args.source,work)
            table=json.loads((source/"n18-482-base.json").read_text())[format(MASK,"x")]
            require(table[0]==128 and len(table[1])==6,"incorrect primary table")
            paths=[tuple(zip(r[0][::3],r[0][1::3],r[0][2::3],strict=True)) for r in table[1]]
            require(tuple(paths)==PATHS and cover(paths)==6,"changed source paths")
            worker=work/"worker"
            worker.mkdir()
            build=("import sys,json; from pathlib import Path; from inhabited_endpoint import worker,certified_init; "
                   "d=Path(sys.argv[1]); worker(d); "
                   "certified_init(json.loads(Path('stabs18-endpoint-window.json').read_text()),128,d/'i')")
            subprocess.run([sys.executable,"-c",build,str(worker)],cwd=source,check=True)
            def get(path):
                cuts=[v for triple in path for v in triple]
                data=" ".join(map(str,[220,8,896,130,18,*OWNERS,*cuts]))+"\n"
                out=subprocess.check_output([worker/"geometry",worker/"i"],input=data.encode())
                return extract(out)
            with ThreadPoolExecutor(args.jobs) as pool:
                records=list(pool.map(get,paths))
    print(store(args.output,records))


if __name__=="__main__":
    main()
