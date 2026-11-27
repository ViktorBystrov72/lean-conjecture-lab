"""Replay the two independent exclusions and a physical non-exclusion control."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def run(args, *, code=0, env=None):
    result = subprocess.run(args, text=True, capture_output=True, env=env)
    if result.returncode != code:
        raise RuntimeError(f"{args[0]} exited {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitize", action="store_true", help="also enable the compiler's undefined-behaviour sanitizer")
    args = parser.parse_args()
    witness = HERE.parent/"rack/saved/closest-rational.json"
    with tempfile.TemporaryDirectory() as temp:
        d=Path(temp)
        binary=d/"check"
        flags=["-fsanitize=undefined","-fno-sanitize-recover=all"] if args.sanitize else []
        run([os.environ.get("CXX","c++"),"-O3","-std=c++17","-ftrapv",*flags,HERE/"exact.cpp","-o",binary])
        base=HERE/"certificates"
        for case,owner,step in [(56,13,4),(93,9,9)]:
            packet=base/f"case-{case}.txt"
            stdout=run([binary,str(case),"32",packet])
            if stdout.splitlines()[-1] != f"EXCLUDED case {case} index {owner} round {step} A":
                raise ValueError("The elementary exclusion did not replay")
            print(stdout.splitlines()[-1],hashlib.sha256(packet.read_bytes()).hexdigest(),flush=True)

        # This packing is strictly inside the rational test side and belongs
        # to a live class. Check both polygons after each single-owner update.
        bands=d/"bands"
        control=d/"control"
        run([sys.executable,HERE/"control.py",witness,"--output",bands])
        env=dict(os.environ,RACK_CONTROL_BANDS=str(bands),RACK_CONTROL_TRACE=str(control))
        result=run([binary,"53","10",base/"control-53.txt"],code=1,env=env)
        if result.splitlines()[-1]!="UNDECIDED":
            raise ValueError("A physical packing was excluded")
        print(run([sys.executable,HERE/"control.py",witness,"--trace",control,"--rounds","10"]).strip(),flush=True)

        # Corrupt one guaranteed point at the first nonempty record. Its
        # claimed owner cannot contain the lower-left corner of the corridor.
        lines=(base/"case-56.txt").read_text().splitlines()
        pos=next(i for i,line in enumerate(lines) if int(line.split()[2])>0)
        values=lines[pos].split()
        values[3:5]=["0","0"]
        lines[pos]=" ".join(values)
        corrupted=d/"corrupt"
        corrupted.write_text("\n".join(lines)+"\n")
        run([binary,"56","32",corrupted],code=2)
        print("Rejected a corrupted guaranteed-point certificate.")


if __name__=="__main__":
    main()
