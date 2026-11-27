"""Replay the follow-up experiment into a new directory."""

import argparse
import concurrent.futures
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
HISTORY = HERE.parent.parent / "search-history"
sys.path.insert(0, str(HISTORY))
from replay_search import mira_seed

RUNS = {
    "batch1-screen": ("run.py", 1809471, 2400, ()),
    "batch2-screen": ("run.py", 7120718, 2400, ()),
    "splice-a": ("run.py", 8140554, 4200, ("--splice",)),
    "splice-b": ("run.py", 8140555, 4200, ("--splice",)),
    "flex-a": ("flex.py", 493818, 320, ("gustafson", "cantrell", "mira-six-tilt")),
    "flex-b": ("flex.py", 493819, 320, ("hamalainen", "gensane-ryckelynck")),
    "curvature-a": ("curvature.py", 260714, 200, ("gustafson", "cantrell", "mira-six-tilt")),
    "curvature-b": ("curvature.py", 260715, 200, ("hamalainen", "gensane-ryckelynck")),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--batches", choices=RUNS, nargs="+", default=list(RUNS))
    p.add_argument("--jobs", type=int, choices=(1, 2), default=1)
    p.add_argument("--smoke", action="store_true", help="two starts per batch or layout")
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(
        os.environ,
        PACK18_RUN=str(out),
        OPENBLAS_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
        OMP_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    flags = ["-dynamiclib"] if platform.system() == "Darwin" else ["-shared", "-fPIC"]
    for cpp in (HERE / "patch.cpp", HISTORY / "packing.cpp"):
        subprocess.run(
            [
                env.get("CXX", "c++"),
                "-std=c++17",
                "-O3",
                *flags,
                str(cpp),
                "-o",
                str(out / (cpp.stem + ".dylib")),
            ],
            check=True,
        )
    mira_seed(out)

    def execute(name):
        script, seed, count, extra = RUNS[name]
        n = 2 if args.smoke else count
        cmd = [sys.executable, str(HERE / script), "--out", name, "--seed", str(seed)]
        if script == "run.py":
            cmd.extend(["--iterations", str(n), "--screen", *extra])
        else:
            cmd.extend(["--per-layout", str(n), "--layouts", *extra])
        with (out / (name + ".log")).open("w") as log:
            subprocess.run(cmd, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        print(name, "complete", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as workers:
        list(workers.map(execute, args.batches))


if __name__ == "__main__":
    main()
