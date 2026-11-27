"""Replay the all-angle, movable-centre insertion obstruction on 128 archived samples."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from disk_obstacles import fit, overlap, run, sqdist
from free_angles import can_exclude, largest_hole
from free_tile import HALF, LENGTH, basis, separated

HERE = Path(__file__).resolve().parent
WIDE = F(1,512)
NARROW = F(1,8192)


def controls():
    unit=(F(1),F(0));other=(F(3,5),F(4,5))
    # Equality is permitted at both a disk-square and a square-square contact.
    assert sqdist(F(0),F(0),unit,F(1),F(0),HALF) == F(1,4)
    assert not overlap(0,0,unit,1,1,0,unit,1)
    assert overlap(0,0,unit,1,F(999999,1000000),0,unit,1)
    assert fit(F(7,10),F(7,10),other,F(7,5))
    assert not fit(F(7,10),F(7,10),other,F(7,5)-F(1,10000))
    # True insertion into a spacious container, tested against the original
    # squares after the search. All initial centres here force axis-parallel tiles.
    centres=[(x+HALF,y+HALF) for x in range(6) for y in range(3)][:-1]
    found=run(centres,F(6),use_pins=True,node_limit=5000,depth_limit=24)
    assert found['status']=='relaxation_witness'
    x,y,t=map(F,(found['x'],found['y'],found['t']))
    assert fit(x,y,basis(t),F(6))
    assert all(separated((x,y,basis(t)),(X,Y,unit)) for X,Y in centres)
    # A single occupied 1x1 box cannot admit a second unit square.
    assert run([(HALF,HALF)],F(1))['status']=='excluded'
    # Only an exactly axis-aligned mobile tile can fit the touching corner
    # of the 2x2 grid. The witness might not be a midpoint; pruning must
    # not certify exclusion even though there is no positive clearance.
    corner=[(HALF,HALF),(HALF,3*HALF),(3*HALF,HALF)]
    assert all(separated((3*HALF,3*HALF,unit),(X,Y,unit)) for X,Y in corner)
    assert run(corner,F(2),depth_limit=12)['status']!='excluded'
    return dict(spacious='physical witness found',touching='allowed',overlap='detected',
                occupied_unit_box='excluded',tight_grid='feasible tangent retained')


def records():
    data=json.loads((HERE/'sample-indices.json').read_text())
    path=HERE.parent/'finite/poses.txt'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=data['pool_sha256']:
        raise ValueError('The source pool has changed')
    pool=[tuple(map(int,line.split())) for line in path.read_text().splitlines()]
    jobs=[]
    for i,indices in enumerate(data['layouts']):
        if len(indices)!=17 or len(set(indices))!=17 or not all(0<=k<len(pool) for k in indices):
            raise ValueError('Bad 17-tile sample')
        tiles=[]
        for k in indices:
            x,y,a,b,d=pool[k]
            if d<=0 or a*a+b*b!=d*d: raise ValueError('Invalid original frame')
            t=(F(x,10**7),F(y,10**7),(F(a,d),F(b,d)))
            if not fit(*t,LENGTH) or not all(separated(t,r) for r in tiles):
                raise ValueError('The original sample does not pack')
            tiles.append(t)
        jobs.append((i,tiles))
    if len(jobs)!=128:raise ValueError('Expected exactly 128 source layouts')
    return jobs


def check(job):
    i,tiles=job
    c=[(x,y) for x,y,_ in tiles];refs=[u for _,_,u in tiles]
    r2,_=largest_hole(c,LENGTH)
    if can_exclude(r2,WIDE):
        return dict(layout=i,method='voronoi',drift=str(WIDE),radius_squared=str(r2))
    for drift,bins in [(WIDE,64),(NARROW,128)]:
        result=run(c,LENGTH,bins=bins,drift=drift,references=refs)
        if result['status']=='excluded':
            return dict(layout=i,method='angular_core',drift=str(drift),bins=bins,
                        nodes=result['nodes'],depth=result['maximum_depth'],pending=result['pending'])
    raise ValueError(f'Did not close layout {i}: {result}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='write a new receipt instead of comparing it')
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args()
    if args.workers<1 or not __debug__:raise ValueError('Positive worker count and enabled assertions required')
    checks=controls()
    with ProcessPoolExecutor(max_workers=args.workers) as workers:
        rows=list(workers.map(check,records()))
    receipt=dict(side=str(LENGTH),layouts=len(rows),all_centres_per_coordinate_drift=str(NARROW),
                 orientations='unrestricted for all 18 tiles',controls=checks,
                 methods=dict(Counter(x['method'] for x in rows)),drifts=dict(Counter(x['drift'] for x in rows)),
                 sample_indices_sha256=hashlib.sha256((HERE/'sample-indices.json').read_bytes()).hexdigest(),
                 exact_voronoi_radii_sha256=hashlib.sha256(json.dumps([[x['layout'],x['radius_squared']] for x in rows if 'radius_squared' in x],separators=(',',':')).encode()).hexdigest(),
                 branch_and_bound=[x for x in rows if x['method']=='angular_core'])
    if args.output:
        args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    elif json.loads((HERE/'disk_obstacles_receipt.json').read_text())!=receipt:
        raise ValueError('The reproduced certificate differs from the saved receipt')
    print(f"{len(rows)}/128 excluded with all angles free and independent coordinate drift {NARROW}.")
    print(f"{receipt['drifts'][str(WIDE)]}/128 excluded with drift {WIDE}.")
    print('Controls:',checks)

if __name__=='__main__':main()
