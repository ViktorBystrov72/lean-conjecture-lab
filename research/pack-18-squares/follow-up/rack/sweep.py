"""Independent fresh starts in every other symmetry class of the 21 marks."""
import argparse
from pathlib import Path
from rack_search import MIXED, run

if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("shard",type=int);p.add_argument("shards",type=int)
    p.add_argument("--count",type=int,default=24);a=p.parse_args()
    base=Path("all-orbits");base.mkdir(exist_ok=True)
    for j in range(a.shard,187,a.shards):
        if j not in MIXED:
            run(j,1810097+97*j,a.count,base/f"orbit-{j:03d}",[])
