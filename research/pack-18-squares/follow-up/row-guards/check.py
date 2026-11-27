"""Rational implication checks for the single-probe row and bridge certificates.

Consumes outer centre boxes and closed angular intervals. The checks are
conditional on the supplied boxes containing every physical pose in a leaf.
"""
from argparse import ArgumentParser
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
from pathlib import Path
import json
import zlib

U=F(4822876,1000000)
HALF=F(1,2)


def sum_i(a,b):return a[0]+b[0],a[1]+b[1]
def neg(a):return -a[1],-a[0]
def diff(a,b):return sum_i(a,neg(b))
def mul(a,b):
    values=[x*y for x in a for y in b]
    return min(values),max(values)
def magnitude(a):return max(abs(a[0]),abs(a[1]))
def dot(a,b):return a[0]*b[0]+a[1]*b[1]
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def minus(a,b):return a[0]-b[0],a[1]-b[1]
def J(u):return -u[1],u[0]
def interval_dot(a,b):return sum_i(mul(a[0],b[0]),mul(a[1],b[1]))
def corners(p):return product(p[0],p[1])
def gap(p,q):return diff(p[0],q[0]),diff(p[1],q[1])
def span(vecs):
    xs,ys=zip(*vecs)
    return ((min(xs),max(xs)),(min(ys),max(ys)))
def halves(a):return a[0]/2,a[1]/2
def dir_at(k,d):return F(d*d-k*k,d*d+k*k),F(2*k*d,d*d+k*k)
def ratio_box(v):return v[1][0]/v[0][1],v[1][1]/v[0][0]


def transform(row,g):
    p,lo,hi=row
    swap,sx,sy=g
    q=[p[swap],p[1-swap]]
    for k,flip in enumerate((sx,sy)):
        if flip:q[k]=(U-q[k][1],U-q[k][0])
    if swap^sx^sy:lo,hi=(hi[1],hi[0]),(lo[1],lo[0])
    return tuple(q),lo,hi


def read_row(row,sym):
    k,d,x,X,y,Y=row
    if not (all(type(n) is int for n in row) and 0<=k<d<=8192 and x<=X and y<=Y):
        raise ValueError("invalid band or position interval")
    return transform((((F(x,10**6),F(X,10**6)),(F(y,10**6),F(Y,10**6))),
                      dir_at(k,d),dir_at(k+1,d)),sym)


def wall_tiles(rows):
    result=[]
    for p,lo,hi in rows:
        if min(lo[0],hi[0])<min(lo[1],hi[1]):
            lo,hi=(lo[1],-lo[0]),(hi[1],-hi[0])
        c,s=span([lo,hi])
        if c[0]<=magnitude(s):raise ValueError("wall frame not near horizontal")
        reach=(c[0]-magnitude(s))/2
        probe=(p[0][1]-reach,p[0][0]+reach)
        tip=(sum_i(p[0],halves(diff(c,s))),sum_i(p[1],halves(sum_i(c,s))))
        # At a valid probe x, the chord midpoint has y-coordinate
        # centre_y + (x-centre_x)*s/c, with |x-centre_x| <= 1/2.
        shift=magnitude(s)/(2*c[0])
        levels=(p[1][0]-shift,p[1][1]+shift)
        result.append((probe,tip,levels,c,s))
    return result


def outer_tip(wall):
    return span([z for _,p,_,_,_ in wall for z in corners(p)])


def check_stack(walls,ratio):
    r,R=ratio
    if r<=0 or r>R:raise ValueError("nonpositive direction")
    terminal=walls[-1]
    bottom=min(z[2][0] for z in terminal)
    if any(high>=bottom for wall in walls[:-1] for _,_,(_,high),_,_ in wall):
        raise ValueError("wall row order")
    left=max(z[0][0] for wall in walls for z in wall)
    right=min(z[0][1] for wall in walls for z in wall)
    # Choose one vertical line that both crosses every tile from edge to
    # opposite edge and pays for the tilt of the terminal corner.
    for _,tip,_,c,s in terminal:
        if s[1]>0:
            right=min(right,tip[0][0]-s[1]/((1+c[0])*r))
        if s[0]<0:
            left=max(left,tip[0][1]-c[0]*(1+s[0]/(1+c[0]))/R)
    if not left<right:raise ValueError("no common probe")


def chord(rows,P,Q):
    pp,qq=list(corners(P)),list(corners(Q))
    for centre,lo,hi in rows:
        zz=list(corners(centre))
        # For each endpoint pair use its own displacement on both sides.
        # With fixed normal and determinant sign the difference is
        # affine separately in p, q and z.
        tests=[]
        for p,q in product(pp,qq):
            d=minus(q,p)
            bound=2*max(abs(cross(d,minus(p,z))) for z in zz)
            tests.append((d,bound))
        before,after=gap(P,centre),gap(Q,centre)
        for _ in range(4):
            # For positive endpoint lower bounds the intermediate unit vector
            # is a positive combination of the endpoints with weight sum >= 1.
            normals=[(c+sign*(-s),s+sign*c) for c,s in (lo,hi) for sign in (-1,1)]
            if all(dot(d,n)>bound for d,bound in tests for n in normals):
                u=span([lo,hi])
                if interval_dot(before,u)[1]<HALF and interval_dot(after,u)[0]>-HALF:break
            lo,hi=J(lo),J(hi)
        else:raise ValueError("segment not certified through two faces")


def native(rows,corner,first):
    result=[]
    for pos,lo,hi in rows:
        u=span([lo,hi]);v=(neg(u[1]),u[0])
        if min(u[0][0],u[1][0])<=0:raise ValueError("native normal outside positive cone")
        d=gap(pos,corner) if first else gap(corner,pos)
        forward=interval_dot(u,d)[0];lateral=interval_dot(v,d)
        if forward<HALF and not (forward>-HALF and magnitude(lateral)<HALF):
            raise ValueError("terminal corner could be behind its cross face")
        tlo=lo[1]/(1+lo[0]);thi=hi[1]/(1+hi[0])
        result.append((pos,u,v,lateral,tlo,thi))
    return result


def facing(left,right):
    for f,u,ju,arm_f,t,T in left:
        for g,v,jv,arm_g,s,S in right:
            d=gap(g,f)
            if magnitude(interval_dot(ju,d))>=1 or magnitude(interval_dot(jv,d))>=1:
                raise ValueError("transverse separation possible")
            if min(interval_dot(u,d)[0],interval_dot(v,d)[0])<=-1:
                raise ValueError("reverse separation possible")
            lo=(t-S)/(1+t*S);hi=(T-s)/(1+T*s)
            if hi>0 and min(HALF+arm_g[0],HALF-arm_f[1])<hi:
                raise ValueError("positive relative angle guard")
            if lo<0 and min(HALF-arm_g[1],HALF+arm_f[0])< -lo:
                raise ValueError("negative relative angle guard")


def check(entry):
    if len(entry['sym'])!=3 or any(x not in (0,1) for x in entry['sym']):raise ValueError("invalid symmetry")
    if len(entry['roles'])!=7 or len(set(entry['roles']))!=7:raise ValueError("role collision")
    if len(entry['rows'])!=7:raise ValueError("missing pose rows")
    raw=[[read_row(z,entry['sym']) for z in rows] for rows in entry['rows']]
    if not all(raw):raise ValueError("empty required owner")
    bottom=[wall_tiles(z) for z in raw[:3]]
    top=[wall_tiles([transform(r,(1,1,1)) for r in z]) for z in raw[3:5]]
    P=outer_tip(bottom[-1]);tip=outer_tip(top[-1])
    Q=tuple((U-k[1],U-k[0]) for k in (tip[1],tip[0]))
    if entry['kind']=='chord':
        delta=gap(Q,P)
        if min(delta[0][0],delta[1][0])<=0:raise ValueError("uncertain chord direction")
        ratio=ratio_box(delta)
        for tile in raw[5:7]:chord(tile,P,Q)
    elif entry['kind']=='faces':
        left=native(raw[5],P,True);right=native(raw[6],Q,False)
        all_ratios=[ratio_box(z[1]) for z in left+right]
        ratio=min(z[0] for z in all_ratios),max(z[1] for z in all_ratios)
        facing(left,right)
    else:raise ValueError("unknown terminal kind")
    check_stack(bottom,ratio)
    check_stack(top,(1/ratio[1],1/ratio[0]))


def controls(data):
    rejected=0
    for kind in ("chord","faces"):
        source=next(x for x in data if x["kind"]==kind)
        for mutation in ("repeat-owner","wide-wall","displaced-middle","bad-angle"):
            example=json.loads(json.dumps(source))
            if mutation=="repeat-owner":example["roles"][1]=example["roles"][0]
            elif mutation=="wide-wall":
                for r in example["rows"][2]:r[2:]=[0,4822876,0,4822876]
            elif mutation=="displaced-middle":
                for r in example["rows"][5]:r[2:]=[20000000,20000000,20000000,20000000]
            else:example["rows"][5][0][0]= -1
            try:check(example)
            except ValueError:rejected+=1
            else:raise ValueError("Accepted corrupted "+kind+" geometry: "+mutation)
    return rejected


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("enclosures",type=Path,nargs="?",default=Path(__file__).with_name("outer-boxes.zlib"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--regenerated",action="store_true",
                        help="use freshly regenerated bounds, allowing different enclosure widths")
    args=parser.parse_args()
    raw=zlib.decompress(args.enclosures.read_bytes())
    if not args.regenerated and sha256(raw).hexdigest()!="de8e3ae4cb397094c689bcb62df633f60e0521094915317c8a2f460e66a00f20":
        raise ValueError("Saved outer bounds differ from their reference digest")
    data=json.loads(raw)
    if len(data)!=78 or len({(x["case"],x["leaf"]) for x in data})!=78:raise ValueError("Incomplete or duplicate input")
    accepted=Counter();failed=[]
    for item in data:
        try:check(item)
        except ValueError as error:failed.append([item['case'],item['leaf'],str(error)])
        else:accepted[item['case'],item['kind']]+=1
    mutations=controls(data)
    print(dict(accepted));print("Inconclusive:",failed,"; corrupted inputs rejected:",mutations)
    if args.receipt:
        args.receipt.write_text(json.dumps({"outer_data_sha256":sha256(raw).hexdigest(),
            "accepted":{f"{k[0]}-{k[1]}":v for k,v in sorted(accepted.items())},
            "inconclusive":failed,"corrupted_inputs_rejected":mutations},indent=2)+"\n")
    if failed:raise SystemExit(1)


if __name__=="__main__":
    main()
