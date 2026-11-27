"""Regenerate the input bounds using the pinned upstream geometry worker."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location("external_loader",HERE.parent.parent/"audit/replay.py")
audit=importlib.util.module_from_spec(loader)
loader.loader.exec_module(audit)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,help="local clone containing the pinned upstream revision")
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--save",type=Path,help="retain the regenerated compressed enclosure input")
    args=parser.parse_args()
    if not __debug__ or args.workers<1:
        parser.error("Run with assertions enabled and positive worker count")
    with TemporaryDirectory(prefix="pack18-rows-") as d:
        root=Path(d)
        tables=audit.source_files(args.source.resolve() if args.source else None,root)
        directory=root/"worker";directory.mkdir()
        setup=("import json,sys; from pathlib import Path; "
               "from inhabited_endpoint import worker,certified_init; "
               "d=Path(sys.argv[1]); worker(d); "
               "certified_init(json.loads(Path('stabs18-endpoint-window.json').read_text()),128,d/'init')")
        subprocess.run([sys.executable,"-c",setup,str(directory)],cwd=tables,check=True)
        out=args.save.resolve() if args.save else root/"outer.zlib"
        subprocess.run([sys.executable,HERE/"inputs.py",tables,directory/"geometry",directory/"init",
                        out,"--workers",str(args.workers)],check=True)
        subprocess.run([sys.executable,HERE/"check.py",out,"--regenerated"],check=True)


if __name__=="__main__":
    main()
