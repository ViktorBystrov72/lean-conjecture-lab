"""Test every global translation of the exact historical pose within the test box.

This proof covers all rigid translations at the given fixed tile positions
relative to each other. It does not quantify over arbitrary tile movements.
"""
import argparse,json
from itertools import product
from pathlib import Path
from rack_check import U,F,exact_source,geometry,marks
from route_witnesses import canonical_images,angle_bins,load_groups
from kernel_control import process_leaf,check_output,HERE


def translations(pose):
    limits=[((abs(c)+abs(s))/2-x,U-(abs(c)+abs(s))/2-x,
             (abs(c)+abs(s))/2-y,U-(abs(c)+abs(s))/2-y) for x,y,c,s in pose.values()]
    return [max(p[0] for p in limits),min(p[1] for p in limits),
            max(p[2] for p in limits),min(p[3] for p in limits)]


def points(r):
    return tuple(product((r[0],r[1]),(r[2],r[3])))


def stable_ownership(pose,r):
    for owner,(x,y,c,s) in pose.items():
        d=[max(abs((X-x)*c+(Y-y)*s),abs((Y-y)*c-(X-x)*s)) for X,Y in marks]
        delta=max(max(abs(dx*c+dy*s),abs(dy*c-dx*s)) for dx,dy in points(r))
        others=[z for i,z in enumerate(d) if i!=owner]
        if not (d[owner]+2*delta<min(others) and d[owner]+delta<F(1,2)):return False
    return True


def restrict(r,pose,path,bins):
    r=r.copy()
    live={}
    for i,k,v in zip(path[::3],path[1::3],path[2::3]):
        if k>=4:
            a=live.setdefault(i,bins[i].copy());a.intersection_update(j for j in range(128) if (j<v if k==4 else j>=v))
            if not a:return None
        else:
            axis=k//2
            val=F(v,1000000)-pose[i][axis]
            if k%2==0:r[axis*2+1]=min(r[axis*2+1],val)
            else:r[axis*2]=max(r[axis*2],val)
            if r[axis*2]>r[axis*2+1]:return None
    return r


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('sources',nargs='+',type=Path);ap.add_argument('--output',default='rigid-slides.json');args=ap.parse_args()
    groups=load_groups();reports=[]
    for fn in args.sources:
        side,tiles=exact_source(fn);geometry(tiles,side);assert side<=U
        full_coverage=False
        for g,case,pose in canonical_images(tiles):
            box=translations(pose)
            assert box[0]<=0<=box[1] and box[2]<=0<=box[3]
            assert stable_ownership(pose,box)
            bins={i:angle_bins(c,s) for i,(_,_,c,s) in pose.items()}
            for leaf,pat,act in groups[case]:
                part=restrict(box,pose,pat,bins)
                if part is None:continue
                assert act!='empty'
                process_leaf((fn.name,g,case,leaf,pose,pat))
                out=(HERE/'kernel-control'/f'{case}-{leaf}.out').read_text()
                checked=check_output(out,pose,points(part))
                assert checked.get('lost')==[],(fn.name,g,leaf,checked)
                full=(box==part)
                if full: full_coverage=True
                one={'file':fn.name,'sym':g,'case':case,'leaf':leaf,'action':act,'full_box':full,'all_18_centres_in_kernel_for_every_translation':True}
                reports.append(one);print(one,flush=True)
        assert full_coverage,(fn.name,"no single representative covers all translations")
    print('PASS',len(reports),'witness/symmetry/leaf combinations')
    Path(args.output).write_text(json.dumps(reports,indent=2)+'\n')
