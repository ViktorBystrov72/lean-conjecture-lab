"""Independent directed-interval test of the six two-face leaves in orbit 137."""
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
import argparse
import gzip
import hashlib
import json


SCALE = 10**12
MICRO = SCALE // 10**6
CAP = 4822876 * MICRO
MASK = 0x1ffbcf
OWNERS = [i for i in range(21) if MASK >> i & 1]
FLIP_Y = (True, True, False, False, True, False)
FIRST_ROWS = ((7,), (2, 7))         # vertical probe, horizontal probe
SECOND_ROWS = ((13, 16), (20, 16)) # in the opposite corner frame
MIDDLE = (9, 14)
ACTIVE = set(FIRST_ROWS[0]+FIRST_ROWS[1]+SECOND_ROWS[0]+SECOND_ROWS[1]+MIDDLE)
# Each path branches on the owner's x, y or original 128-bin orientation.
# Even operators select the lower side, odd operators the upper side.
PATHS = (
    ((12,1,2909031),),
    ((12,0,2909031),(9,4,64)),
    ((12,0,2909031),(9,5,64),(13,1,2900673)),
    ((12,0,2909031),(9,5,64),(13,0,2900673),(11,5,64)),
    ((12,0,2909031),(9,5,64),(13,0,2900673),(11,4,64),(19,2,1902202)),
    ((12,0,2909031),(9,5,64),(13,0,2900673),(11,4,64),(19,3,1902202)),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int

    def __add__(self, other):
        return Interval(self.lo+other.lo,self.hi+other.hi)

    def __neg__(self):
        return Interval(-self.hi,-self.lo)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        values = (self.lo*other.lo,self.lo*other.hi,self.hi*other.lo,self.hi*other.hi)
        return Interval(min(values)//SCALE, -((-max(values))//SCALE))

    def over(self, other):
        require(other.lo > 0, "denominator interval not positive")
        reciprocal = Interval(SCALE**2//other.hi, -((-SCALE**2)//other.lo))
        return self * reciprocal

    def largest_abs(self):
        return max(abs(self.lo),abs(self.hi))

    @staticmethod
    def enclose(intervals):
        return Interval(min(i.lo for i in intervals),max(i.hi for i in intervals))


def rat(n,d):
    require(d>0,"rational denominator")
    return Interval((n*SCALE)//d,-((-n*SCALE)//d))


HALF = rat(1,2)
ONE = rat(1,1)
CAP_I = Interval(CAP,CAP)


def dot(a,b):
    return a[0]*b[0]+a[1]*b[1]


def sub(a,b):
    return (a[0]-b[0],a[1]-b[1])


def invert(p):
    return (CAP_I-p[0],CAP_I-p[1])


def cover(paths):
    """Check each internal split has both branches, without requiring disjoint boundaries."""
    require(len(paths) > 0, "empty cover")
    if not paths[0]:
        require(paths == [()], "leaf is duplicated or occurs next to descendants")
        return 1
    j,op,value=paths[0][0]
    require(j in OWNERS and 0<=op<6, "invalid cut")
    require(0 < value < (128 if op>=4 else 4822876), "invalid threshold")
    axis=op//2
    require(all(row and (row[0][0],row[0][1]//2,row[0][2])==(j,axis,value) for row in paths),
            "paths do not share the same geometric split")
    return sum(cover([row[1:] for row in paths if row[0][1]%2==b]) for b in (0,1))


def owner_map(symmetry):
    swap, rx, ry = symmetry
    pts=sorted({(a,b) for x,y in ((390,390),(617,617),(797,359),(1000,716),(1000,1000))
                for i,j in ((x,y),(y,x)) for a in (i,2000-i) for b in (j,2000-j)})
    require(len(pts)==21, "rack")
    reflected={}
    for i,(x,y) in enumerate(pts):
        if swap: x,y=y,x
        reflected[i]=pts.index((2000-x if rx else x,2000-y if ry else y))
    return reflected


def label_reflection():
    reflected=owner_map((0,0,1))
    require(set(reflected[i] for i in OWNERS)==set(OWNERS), "wrong class symmetry")
    return reflected


@lru_cache(None)
def frame_at(k,d):
    den=d*d+k*k
    return (rat(d*d-k*k,den),rat(2*d*k,den))


@dataclass(frozen=True)
class Pose:
    center: tuple
    frame: tuple
    tangent: Interval


def poses(records, symmetry, active):
    """Read [band numerator, denominator, xmin, xmax, ymin, ymax] in micro-units."""
    mapping=owner_map(symmetry)
    sw,rx,ry=symmetry
    tiles={}
    require(all(0<=j<21 for j,_ in records) and {mapping[j] for j, _ in records} == active, "stored endpoint owners")
    for owner,rows in records:
        require(mapping[owner] in active and mapping[owner] not in tiles and rows,"unknown, duplicate or empty owner")
        states=[]
        for k,d,x,X,y,Y in rows:
            require(0<=k<d<=8192 and 0<=x<=X<=4822876 and 0<=y<=Y<=4822876,"invalid pose box")
            first,last=frame_at(k,d),frame_at(k+1,d)
            ti=Interval(rat(k,d).lo,rat(k+1,d).hi)
            if sw: x,X,y,Y=y,Y,x,X
            if rx: x,X=4822876-X,4822876-x
            if ry: y,Y=4822876-Y,4822876-y
            if sw ^ rx ^ ry:
                # A reflected first-quadrant orientation maps to pi/2-theta
                # modulo quarter turns, reversing the endpoint order.
                first,last=(last[1],last[0]),(first[1],first[0])
                ti=Interval(rat(d-k-1,d+k+1).lo,rat(d-k,d+k).hi)
            u=(Interval(last[0].lo,first[0].hi),Interval(first[1].lo,last[1].hi))
            states.append(Pose((Interval(x*MICRO,X*MICRO),Interval(y*MICRO,Y*MICRO)),u,ti))
        tiles[mapping[owner]]=states
    return tiles


def row_profile(states, opposite):
    vertical=[]; horizontal=[]; tips=[]; x_orders=[]; y_orders=[]
    for st in states:
        x,y = invert(st.center) if opposite else st.center
        c,s = st.frame
        # The horizontal-facing edge must be unique in the entire band.
        if c.lo <= 3*SCALE//4:
            c,s = s,-c
        require(c.lo>3*SCALE//4,"no uniform near-horizontal edge")
        tr=s.largest_abs()
        # A vertical probe through this central strip crosses both faces
        # normal to J u. The analogous horizontal probe crosses both u faces.
        slack=(c.lo-tr)//2
        vertical.append((x.hi-slack,x.lo+slack))
        horizontal.append((y.hi-slack,y.lo+slack))
        center_error=rat(tr,2*c.lo).hi
        y_orders.append(Interval(y.lo-center_error,y.hi+center_error))
        x_orders.append(Interval(x.lo-center_error,x.hi+center_error))
        tips.append((x+(c-s)*HALF,y+(c+s)*HALF))
    return {
        "vertical":(max(z[0] for z in vertical),min(z[1] for z in vertical)),
        "horizontal":(max(z[0] for z in horizontal),min(z[1] for z in horizontal)),
        "y_order":Interval.enclose(y_orders),"x_order":Interval.enclose(x_orders),
        "tip":tuple(Interval.enclose([p[k] for p in tips]) for k in (0,1)),
    }


def corner(tiles, rows, opposite, ratio):
    vertical,horizontal=rows
    common=vertical[-1]
    require(common==horizontal[-1],"two different terminal corners")
    require(len(set(vertical))==len(vertical) and len(set(horizontal))==len(horizontal),"repeated row member")
    prof={i:row_profile(tiles[i],opposite) for i in set(vertical+horizontal)}
    ix=(max(prof[i]["vertical"][0] for i in vertical), min(prof[i]["vertical"][1] for i in vertical))
    iy=(max(prof[i]["horizontal"][0] for i in horizontal),min(prof[i]["horizontal"][1] for i in horizontal))
    require(all(prof[i]["y_order"].hi<prof[common]["y_order"].lo for i in vertical[:-1]),"vertical order")
    require(all(prof[i]["x_order"].hi<prof[common]["x_order"].lo for i in horizontal[:-1]),"horizontal order")
    p,q=prof[common]["tip"]
    # For every admissible slope b/a, choose probes x=p-lambda and
    # y=q-(b/a)*lambda. The strict inner interval keeps both lines inside.
    low=max(0,p.hi-ix[1],rat(q.hi-iy[1],ratio.lo).hi)
    high=min(p.lo-ix[0],rat(q.lo-iy[0],ratio.hi).lo)
    require(low<high,"no coupled wall probes")
    return (p,q),high-low


def first_face(states, corner_box, left):
    # The physical corner belongs to a different tile. It cannot be in
    # the open middle square. Eliminate the back and the two transverse faces.
    for st in states:
        direction=st.frame
        perp=(-direction[1],direction[0])
        diff=sub(st.center,corner_box) if left else sub(corner_box,st.center)
        f=dot(direction,diff);v=dot(perp,diff)
        require(f.lo>=HALF.lo or (f.lo> -HALF.lo and v.largest_abs()<HALF.lo),
                "cannot certify terminal corner on forward side")


def guarded_leaf(records,symmetry,first_rows,second_rows,middle):
    f,g=middle
    A=set(first_rows[0]+first_rows[1]);B=set(second_rows[0]+second_rows[1])
    require(f!=g and not A.intersection(B) and not (A | B).intersection(middle), "repeated physical owner")
    counts=(len(first_rows[0])+len(second_rows[0]),len(first_rows[1])+len(second_rows[1]))
    require(sorted(counts)==[3,4],"wrong total wall chords")
    tiles=poses(records,symmetry,A | B | set(middle))
    a,b=tiles[f],tiles[g]
    all_mid=a+b
    require(all(min(st.frame[0].lo,st.frame[1].lo)>0 for st in all_mid),"middle cone")
    ratios=[st.frame[1].over(st.frame[0]) for st in all_mid]
    cone=Interval.enclose(ratios)
    P,gap1=corner(tiles,first_rows,False,cone)
    inverse_Q,gap2=corner(tiles,second_rows,True,cone)
    Q=invert(inverse_Q)
    first_face(a,P,True);first_face(b,Q,False)
    for A in a:
        u=A.frame;U=(-u[1],u[0])
        left=dot(U,sub(A.center,P))
        for B in b:
            v=B.frame;V=(-v[1],v[0])
            right=dot(V,sub(Q,B.center))
            delta=sub(B.center,A.center)
            # The half-sum of the projected tile widths is at least one on
            # either tile's own axes. Rule out all but the forward u or v.
            require(max(dot(U,delta).largest_abs(),dot(V,delta).largest_abs())<SCALE,
                    "a transverse separating axis is still possible")
            require(min(dot(u,delta).lo,dot(v,delta).lo)>-SCALE,"reverse axis is possible")
            lo=(Interval(A.tangent.lo,A.tangent.lo)-Interval(B.tangent.hi,B.tangent.hi)).over(
                ONE + Interval(A.tangent.lo,A.tangent.lo)*Interval(B.tangent.hi,B.tangent.hi))
            hi=(Interval(A.tangent.hi,A.tangent.hi)-Interval(B.tangent.lo,B.tangent.lo)).over(
                ONE + Interval(A.tangent.hi,A.tangent.hi)*Interval(B.tangent.lo,B.tangent.lo))
            # (tan(alpha/2)-tan(beta/2))/(1+tan(alpha/2)tan(beta/2))
            # is increasing in the first argument, decreasing in the second.
            if hi.hi>0:
                require(min(HALF.lo+right.lo,HALF.lo-left.hi)>=hi.hi,"positive transverse guard")
            if lo.lo<0:
                require(min(HALF.lo-right.hi,HALF.lo+left.lo)>= -lo.lo,"negative transverse guard")
    return {"first_middle_bands":len(a),"second_middle_bands":len(b),"band_pairs":len(a)*len(b),
            "first_probe_gap_units":gap1,"second_probe_gap_units":gap2}


def verify_leaf(records,flip):
    return guarded_leaf(records,(0,0,int(flip)),FIRST_ROWS,SECOND_ROWS,MIDDLE)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rectangles",type=Path,nargs="?",default=Path(__file__).with_name("rectangles.json.gz"))
    ap.add_argument("--record",type=Path,help="write a receipt instead of comparing the archived one")
    args=ap.parse_args()
    require(cover(list(PATHS))==6,"cover leaf count")
    ids=FIRST_ROWS[0]+FIRST_ROWS[1]+SECOND_ROWS[0]+SECOND_ROWS[1]
    require(len(set(MIDDLE))==2 and not set(ids).intersection(MIDDLE) and
            not set(FIRST_ROWS[0]+FIRST_ROWS[1]).intersection(SECOND_ROWS[0]+SECOND_ROWS[1]),
            "tile roles overlap")
    require((len(FIRST_ROWS[0])+len(SECOND_ROWS[0]),len(FIRST_ROWS[1])+len(SECOND_ROWS[1]))==(3,4),
            "unexpected wall counts")
    raw=gzip.decompress(args.rectangles.read_bytes())
    data=json.loads(raw)
    require(len(data)==6,"wrong number of enclosures")
    rows=[]
    rejected=0
    for i,(record,flip) in enumerate(zip(data,FLIP_Y)):
        result=verify_leaf(record,flip)
        rows.append(dict(leaf=i,reflected=flip,**result))
        # A full-box uncertainty on the terminal or a middle centre
        # must not pass the corresponding geometric obligation.
        for target, field in ((MIDDLE[0],"centre"),(FIRST_ROWS[0][-1],"centre"),(MIDDLE[1],"angle")):
            mutated=[]
            for owner, states in record:
                mapped=label_reflection()[owner] if flip else owner
                if mapped==target:
                    if field=="centre":
                        states=[[k,d,0,4822876,0,4822876] for k,d,*_ in states]
                    else:
                        states=[[0,1,*state[2:]] for state in states]
                mutated.append([owner,states])
            try:
                verify_leaf(mutated,flip)
            except ValueError:
                rejected+=1
            else:
                raise ValueError("Accepted an intentionally undetermined guard")
    for i in range(6):
        try:
            cover([path for j,path in enumerate(PATHS) if i!=j])
        except ValueError:
            rejected+=1
        else:
            raise ValueError("An incomplete branch cover passed")
    receipt={"case":137,"mask":format(MASK,"x"),"enclosure_payload_sha256":hashlib.sha256(raw).hexdigest(),
             "interval_scale":SCALE,"terminal_angle_pairs":sum(x["band_pairs"] for x in rows),
             "outward_interval_guards_passed":len(rows),"negative_controls_rejected":rejected,"leaves":rows}
    if args.record:
        args.record.write_text(json.dumps(receipt,indent=2)+"\n")
    else:
        stored=json.loads(Path(__file__).with_name("receipt.json").read_text())
        require(stored==receipt,"receipt mismatch")
    print(f'Checked {len(rows)} terminal guards and {receipt["terminal_angle_pairs"]} middle-angle pairs.')
    print(f'Rejected {rejected} damaged leaf or covering inputs.')


if __name__=="__main__":
    main()
