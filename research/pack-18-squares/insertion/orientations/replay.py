"""Re-run the unrestricted-angle numerical search from the thirteen layout seeds."""

import argparse
import concurrent.futures
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
HISTORY = HERE.parent.parent / "search-history"
CASES = {
    "setA": (180621, [0, 2, 4, 74, 93, 122, 126], False),
    "setB": (180622, [1, 3, 5, 75, 94, 127], False),
    "thaw126": (180624, [126], True),
    "thaw127": (180625, [127], True),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--jobs", choices=(1, 2), type=int, default=1)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(
        os.environ,
        PACK18_RUN=str(out),
        PYTHONDONTWRITEBYTECODE="1",
        OPENBLAS_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    flags = ["-dynamiclib"] if platform.system() == "Darwin" else ["-shared", "-fPIC"]
    for cpp in (HISTORY / "packing.cpp", HERE / "rounded.cpp"):
        subprocess.run(
            [
                env.get("CXX", "c++"),
                "-O3",
                "-std=c++17",
                *flags,
                str(cpp),
                "-o",
                str(out / (cpp.stem + ".dylib")),
            ],
            check=True,
        )

    def run(name):
        seed, layouts, thaw = CASES[name]
        hard = 1 if args.smoke else 480 if thaw else 240
        other = 1 if args.smoke else 16
        command = [
            sys.executable,
            str(HERE / "search_orientations.py"),
            "--batch",
            name,
            "--seed",
            str(seed),
            "--layouts",
            *map(str, layouts),
            "--hard",
            str(hard),
            "--other",
            str(other),
        ]
        if thaw:
            command.append("--thaw")
        with (out / (name + ".log")).open("w") as log:
            subprocess.run(
                command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, check=True
            )
        print(name, "complete", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        list(executor.map(run, CASES))


if __name__ == "__main__":
    main()
