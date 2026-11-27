"""Exercise the unrestricted formula on exact contacts, overlaps and record layouts."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as F
import json
from pathlib import Path

from query import problem, run, smt


def exact(q):
    a,b=map(F,q)
    return f"(+ {smt(a)} (* {smt(b)} root7))"


def signs(q):
    a,b=map(F,q)
    if not b or a*b >= 0:
        v=a or b
    else:
        v=a*(a*a-7*b*b)
    return (v>0)-(v<0)


def pinned(data, *, displaced=False):
    poses=[]
    for index,pose in enumerate(data["frames"]):
        c,s=pose["c"],pose["s"]
        # Select a first-quadrant representative of this same square.
        for _ in range(4):
            if signs(c)>=0 and signs(s)>=0:
                break
            c,s=[-F(z) for z in s],c
        x=list(map(F,pose["x"]));y=pose["y"]
        poses.append((c,s,x,y))
    # An approximate ordering is only a convenience for writing the input.
    # Z3 checks the actual ordering in the query.
    with localcontext() as ctx:
        ctx.prec=50
        def sine(p):
            a,b=map(F,p[1])
            return Decimal(a.numerator)/Decimal(a.denominator) + Decimal(7).sqrt()*Decimal(b.numerator)/Decimal(b.denominator)
        poses.sort(key=sine)
    if displaced:
        c,s,_,_=poses[1]
        poses[1]=(c,s,poses[0][2],poses[0][3])
    out=["(declare-const root7 Real)","(assert (and (> root7 0) (= (* root7 root7) 7)))",
         "(assert (= L (/ (+ 7 root7) 2)))"]
    for i,(c,s,x,y) in enumerate(poses):
        for var,pair in (("c",c),("s",s),("x",x),("y",y)):
            out.append(f"(assert (= {var}{i} {exact(pair)}))")
    return "\n".join(out)+"\n"


def grid(p,eps=F(0),side=2,frame=(1,0)):
    out=f"(assert (= L {smt(side)}))\n"
    for i,(x,y) in enumerate(p):
        for var,v in (("c",frame[0]),("s",frame[1]),("x",x-(eps if i==1 else 0)),("y",y)):
            out+=f"(assert (= {var}{i} {smt(v)}))\n"
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--solver",required=True)
    ap.add_argument("--seconds",type=int,default=15)
    args=ap.parse_args()
    touch=[(F(1,2),F(1,2)),(F(3,2),F(1,2))]
    rotated=[(1,1),(F(9,4),1)]
    unit=(F(3,5),F(4,5))
    cases=[("one-tile boundary",problem(1,strict_target=False)+"(assert (= L 1))\n","sat"),
           ("one-tile too small",problem(1,strict_target=False)+"(assert (< L 1))\n","unsat"),
           ("two-tile boundary",problem(2,strict_target=False)+grid(touch),"sat"),
           ("overlap by 10^-12",problem(2,strict_target=False)+grid(touch,F(1,10**12)),"unsat"),
           ("tilted side contact, centres more than one apart",
            problem(2,strict_target=False)+grid(rotated,side=4,frame=unit),"sat"),
           ("tilted overlap by 10^-12, disjoint inscribed disks",
            problem(2,strict_target=False)+grid(rotated,F(1,10**12),side=4,frame=unit),"unsat"),
           ("tilted tile protrudes through the bottom wall",
            problem(1,strict_target=False)+grid([(1,F(7,10)-F(1,10**12))],side=3,frame=unit),"unsat")]
    directory=Path(__file__).resolve().parent.parent/"layouts"
    for name in ("hamalainen","gustafson","cantrell","gensane-ryckelynck"):
        data=json.loads((directory/(name+"-exact.json")).read_text())
        cases.append((name+" at the record side",problem(strict_target=False)+pinned(data),"sat"))
    cases.append(("record equality is not a strict improvement",problem()+pinned(data),"unsat"))
    cases.append(("coincident centres",problem(strict_target=False)+pinned(data,displaced=True),"unsat"))
    for label,text,expected in cases:
        verdict,detail=run(args.solver,text,args.seconds,180321)
        if verdict!=expected:raise ValueError((label,expected,verdict,detail[:500]))
        print(f"{label}: {verdict}",flush=True)


if __name__=="__main__":
    main()
