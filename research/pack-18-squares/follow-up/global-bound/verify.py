"""Replay one unrestricted lower bound, including rack coverage and all 187 orbits."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from sweep import TEST, UNIT, marks_and_masks

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent/"terminal-audit/case_audit.cpp"


def verdict(exe, side, index, mask, entry):
    bands = entry["bands"]
    rounds = entry["round_limit"]
    if (entry["case"] != index or int(entry["mask"],16) != mask or
        not 4 <= bands <= 128 or not 1 <= rounds <= 150):
        raise ValueError(f"Invalid coverage instruction at {index}")
    result = subprocess.run([str(exe),"--side",str(side),format(mask,"x"),str(bands),str(rounds)],
                            capture_output=True, text=True, check=True)
    last = result.stdout.strip().splitlines()[-1]
    match = re.fullmatch(r"EXCLUDED (empty owner (\d+)|guaranteed overlap (\d+) (\d+)) round (\d+)", last)
    if not match:
        raise ValueError(f"Case {index}: {last}")
    owners = list(map(int,filter(None,match.groups()[1:4])))
    if (len(set(owners)) != len(owners) or
        any(not (0 <= i < 21 and mask & (1 << i)) for i in owners) or
        not 0 <= int(match.group(5)) < rounds):
        raise ValueError(f"Invalid closing event for case {index}: {last}")
    return last


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate",type=Path,default=HERE/"cases.json")
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--rack-bands",type=int,default=512)
    parser.add_argument("--receipt",type=Path)
    args = parser.parse_args()
    if args.workers < 1 or not 128 <= args.rack_bands <= 1024:
        parser.error("invalid worker count or rack resolution")
    request = json.loads(args.certificate.read_text())
    side = Fraction(request["side"])*UNIT
    if side.denominator != 1 or not UNIT <= side < TEST or (TEST-int(side))%2:
        raise ValueError("The requested side cannot be represented exactly")
    masks = marks_and_masks()
    entries = request["runs"]
    if len(entries) != len(masks) or len(masks)!=187:
        raise ValueError("Incomplete case cover")
    source_bytes = SOURCE.read_bytes()
    with TemporaryDirectory(prefix="square-bound-") as tmp:
        exe = Path(tmp)/"check"
        copy = Path(tmp)/"case_audit.cpp"
        copy.write_bytes(source_bytes)
        subprocess.run([os.environ.get("CXX","c++"),"-O2","-std=c++17",str(copy),"-o",str(exe)],check=True)
        rack = subprocess.check_output([str(exe),"--rack",str(args.rack_bands)],text=True).strip()
        if not re.fullmatch(r"RACK COVERED [1-9]\d* leaves [1-9]\d* nodes, max depth \d+",rack):
            raise ValueError(f"Rack check did not conclude: {rack}")
        print(rack,flush=True)
        def solve(index):
            return verdict(exe,int(side),index,masks[index],entries[index])
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            conclusions = list(pool.map(solve,range(len(masks))))
    report = {"side":request["side"],"square_count":18,"rack":rack,
              "hole_triples":1330,"symmetry_classes":len(conclusions),
              "angles_by_case_count":dict(sorted(Counter(e["bands"] for e in entries).items())),
              "source_sha256":sha256(source_bytes).hexdigest(),
              "case_settings_sha256":sha256(args.certificate.read_bytes()).hexdigest(),
              "conclusions_sha256":sha256(("\n".join(conclusions)+"\n").encode()).hexdigest()}
    print(f"All {len(conclusions)} orbits excluded at side {request['side']}.")
    if args.receipt: args.receipt.write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    main()
