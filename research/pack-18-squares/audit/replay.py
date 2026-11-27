"""Replay our physical controls against a pinned copy of the external case data."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
PIN = "78bec6aacebf304d942a9225e16c2f18165778ff"
TREE = "6c2f791f184e059e78e71a24bcb13fc32e0dd377"
SUBDIR = "notes/geometry/unit-square-packing-18/replay"
URL = "https://github.com/Mira-Cult/math.git"
NAMES = ("gustafson", "cantrell", "gensane-ryckelynck", "hamalainen", "mira-six-tilt")
CONTROLS = ("cantrell-exact-115-8.0", "cantrell-exact-92-0.0", "cantrell-exact-92-1.0")


def source_files(repo, work):
    if repo is None:
        repo = work/"source.git"
        subprocess.run(["git", "init", "--bare", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin", URL], check=True)
        subprocess.run(["git", "-C", repo, "fetch", "--no-tags", "--filter=blob:none",
                        "--depth=1", "origin", PIN], check=True)
    value = subprocess.check_output(["git", "-C", repo, "rev-parse", f"{PIN}:{SUBDIR}"], text=True)
    if value.strip() != TREE:
        raise ValueError("External replay tree mismatch")
    archive = subprocess.check_output(["git", "-C", repo, "archive", PIN, "--", SUBDIR])
    subprocess.run(["tar", "-xf", "-", "-C", work], input=archive, check=True)
    return work/SUBDIR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="existing Git clone with the pinned commit")
    parser.add_argument("--kernel", action="store_true", help="build and query the published geometry worker")
    parser.add_argument("--search", action="store_true", help="repeat our optional fixed-axis LP screens")
    args = parser.parse_args()
    if not __debug__:
        raise ValueError("Enabled Python assertions are required")
    with tempfile.TemporaryDirectory(prefix="pack18-audit-") as temp:
        work = Path(temp)
        source = source_files(args.source, work)
        env = dict(os.environ, PACK18_REPLAY=str(source), PACK18_RUN=str(work),
                   OPENBLAS_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
        layouts = ROOT.parent/"layouts"
        poses = [layouts/f"{name}-exact.json" for name in NAMES]
        # Materialize the one external layout in temporary storage if needed.
        if not poses[-1].is_file():
            poses[-1] = work/poses[-1].name
            subprocess.run([sys.executable, layouts/"fetch_mira.py", "--input",
                            source/"six-tilt18.json", "--output", poses[-1]], check=True)
        rec = ROOT/"receipts"
        subprocess.run([sys.executable, ROOT/"rack_check.py", *poses], cwd=work, env=env, check=True)
        routes = subprocess.check_output([sys.executable, ROOT/"route_witnesses.py", *poses],
                                        text=True, cwd=work, env=env)
        if routes != (rec/"exact-routes.txt").read_text():
            raise ValueError("Historical route receipt mismatch")
        print(routes, end="", flush=True)
        alternatives = [ROOT/"controls"/(name+".json") for name in CONTROLS]
        if args.kernel:
            d = work/"kernel-control"
            d.mkdir()
            prepare = (
                "import json,sys; from pathlib import Path; "
                "from inhabited_endpoint import worker,certified_init; "
                "d=Path(sys.argv[1]); "
                "certified_init(json.loads(Path('stabs18-endpoint-window.json').read_text()),128,d/'i'); "
                "worker(d)"
            )
            subprocess.run([sys.executable, "-c", prepare, d], cwd=source, env=env, check=True)
            for script, output, inputs in [
                ("kernel_control.py", "kernel-check.json", [*poses[:2], *alternatives]),
                ("rigid_slides.py", "rigid-slides.json", poses[:2]),
            ]:
                subprocess.run([sys.executable, ROOT/script, "--output", output, *inputs],
                               cwd=work, env=env, check=True)
                if json.loads((work/output).read_text()) != json.loads((rec/output).read_text()):
                    raise ValueError(f"Exact kernel receipt mismatch: {output}")
        if args.search:
            for branches, inputs in [(12, poses), (10, alternatives)]:
                subprocess.run([sys.executable, ROOT/"search_free.py", "--branches", str(branches),
                                "--random-directions", "40", *inputs], cwd=work, env=env, check=True)


if __name__ == "__main__":
    main()
