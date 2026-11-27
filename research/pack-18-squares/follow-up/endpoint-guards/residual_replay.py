"""Independent two-probe / two-face checks in the nonempty residual leaves."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from check_guards import guarded_leaf, owner_map, require
from enclosures import extract, pinned_files


HERE=Path(__file__).resolve().parent
TABLES={
    82: (0x1fb7ef,"c1657ecc5aae295b415fdff0b4875436f770439c6d9336050f8d37acbef0e05f"),
    92: (0x1fbfcf,"a63c93ebda866877314e0703a25363480254ae53dd88b8d217e557d290f42ec0"),
    115: (0x1ff3ef,"91a6687e4b48f52a9892b036646b65250e0f52d3da006002cab1070c90041188"),
}
EXPECTED={82:6,92:9,115:5}


def jobs(source):
    out=[]
    for case,(mask,digest) in TABLES.items():
        raw=(source/f"residual-{case}-cases.json").read_bytes()
        require(hashlib.sha256(raw).hexdigest()==digest,"unexpected case data")
        for i,(root,leaves) in enumerate(json.loads(raw)):
            for j,(cut,params,act) in enumerate(leaves):
                if act==["empty"]:
                    continue
                symmetry,roles,kind=act
                require(kind=="faces" and len(roles)==6,"unexpected endpoint type")
                out.append((case,i,j,root+cut,params,symmetry,roles))
    require(dict(Counter(j[0] for j in out))==EXPECTED,"incomplete selection of nonempty leaves")
    return out


def regenerate(source, raw_dir, directory, concurrency):
    if raw_dir is None:
        worker=directory/"worker"
        worker.mkdir()
        build=("import sys,json; from pathlib import Path; from inhabited_endpoint import worker,certified_init; "
               "d=Path(sys.argv[1]); worker(d); "
               "certified_init(json.loads(Path('stabs18-endpoint-window.json').read_text()),128,d/'i')")
        subprocess.run([sys.executable,"-c",build,str(worker)],cwd=source,check=True)
    def one(job):
        case,i,j,cut,params,sym,roles=job
        owners=[k for k in range(21) if TABLES[case][0]>>k&1]
        require(len(owners)==18,"invalid mask")
        if raw_dir is None:
            req=" ".join(map(str,[*params,18,*owners,*cut]))+"\n"
            raw=subprocess.check_output([worker/"geometry",worker/"i"],input=req.encode())
        else:
            raw=(raw_dir/f"case{case}-{i}.{j}.txt").read_bytes()
        rows=extract(raw,owners)
        remap=owner_map(sym)
        wanted=set(roles[0]+roles[1]+roles[2]+roles[3]+roles[4:])
        compact=[[owner,boxes] for owner,boxes in rows if remap[owner] in wanted]
        return [case,i,j,sym,roles,compact]
    with ThreadPoolExecutor(concurrency) as pool:
        return list(pool.map(one,jobs(source)))


def verify(records):
    output=[]
    seen=set()
    for case,i,j,sym,roles,rows in records:
        require(case in EXPECTED and (case,i,j) not in seen,"unrecognized or duplicate case")
        require(set(sym)<={0,1} and len(sym)==3,"bad symmetry")
        seen.add((case,i,j))
        av,ah,bv,bh,f,g=roles
        result=guarded_leaf(rows,sym,(tuple(av),tuple(ah)),(tuple(bv),tuple(bh)),(f,g))
        output.append(dict(case=case,leaf=f"{i}.{j}",symmetry=sym,**result))
    require(dict(Counter(v["case"] for v in output))==EXPECTED,"incorrect number of checked cases")
    return output


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,help="existing Git clone at the pin for regeneration")
    ap.add_argument("--raw",type=Path,help="reuse original geometry output, with pinned case rules")
    ap.add_argument("--regenerate",action="store_true",help="regenerate boxes from the upstream kernel")
    ap.add_argument("--boxes",type=Path,default=HERE/"residual-rectangles.json.gz")
    ap.add_argument("--record",type=Path)
    ap.add_argument("--jobs",type=int,choices=(1,2,3),default=2)
    args=ap.parse_args()
    if args.regenerate or args.raw:
        require(__debug__,"source expects Python assertions enabled")
        with TemporaryDirectory(prefix="pack18-residual-guards-") as tmp:
            folder=Path(tmp)
            src=pinned_files(args.source,folder)
            rows=regenerate(src,args.raw,folder,args.jobs)
            blob=json.dumps(rows,separators=(",",":")).encode()
            args.boxes.write_bytes(gzip.compress(blob,mtime=0))
    else:
        blob=gzip.decompress(args.boxes.read_bytes())
        rows=json.loads(blob)
    results=verify(rows)
    out={"enclosure_payload_sha256":hashlib.sha256(blob).hexdigest(),
         "geometry":"Producer outer enclosures; separately computed directed-interval endpoint rules.",
         "lower_bound_guards":len(results),"middle_angle_pairs":sum(z["band_pairs"] for z in results),
         "leaves":results}
    if args.record:args.record.write_text(json.dumps(out,indent=2)+"\n")
    else:require(json.loads((HERE/"residual-receipt.json").read_text())==out,"residual receipt mismatch")
    for case in EXPECTED:
        selected=[r for r in results if r["case"]==case]
        print(f"Case {case}: {len(selected)} two-face leaves, {sum(x['band_pairs'] for x in selected)} band pairs.")


if __name__=="__main__":
    main()
