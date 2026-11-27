"""Optional second decision: ask Z3 QF_LRA about all lifted full leaves at once."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import z3
import verify


def inspect(case,groups,check_minimal):
    boxes=[b for _,bs in groups for b in bs if b is not None]
    keys={key for b in boxes for key in b}
    variables={k:z3.Real(f"p{k[0]}_{k[1]}") for k in keys}
    def scalar(x):
        x=Q(x)
        return z3.RealVal(f"{x.numerator}/{x.denominator}")
    slv=z3.SolverFor("QF_LRA")
    slv.set(timeout=30000)
    for key,v in variables.items():
        low,high=verify.ranges(key,True)
        slv.add(v>=scalar(low),v<=scalar(high))
    flags={name:z3.Bool(f"keep_{name}") for name,_ in groups}
    for name,lifted in groups:
        for b in lifted:
            if b is None:
                continue
            outside=[]
            for key,(lo,hi) in b.items():
                v=variables[key]
                outside.extend((v<scalar(lo),v>scalar(hi)))
            slv.add(z3.Implies(flags[name],z3.Or(outside)))
    stay=sorted(flags.keys()-verify.OMIT.get(case,set()))
    def test(active):
        return slv.check(*(flags[n] for n in active))
    for active in (list(flags),stay):
        result=test(active)
        if result!=z3.unsat:
            raise ValueError(f"Direct test: {case} {result}, "
                             f"{slv.model() if result==z3.sat else slv.reason_unknown()}")
    points={}
    if check_minimal:
        def covered_names(point):
            return {n for n,bs in groups if any(b is not None and
                    all(lo<=point[k]<=hi for k,(lo,hi) in b.items()) for b in bs)}
        for key,v in variables.items():
            # Locate a private point within the ordinary centre wall inset,
            # avoiding the two chart representations of an axis-aligned tile.
            if key[1]==2: slv.add(v>0,v<1)
            else: slv.add(v>500000,v<verify.M-500000)
        for name in stay:
            result=test([n for n in flags if n!=name])
            if result!=z3.sat:
                raise ValueError(f"Missing private box point for {case}:{name}")
            model=slv.model()
            point={k:model.eval(v,model_completion=True).as_fraction() for k,v in variables.items()}
            if covered_names(point)!={name}:
                raise ValueError("Solver model did not pass rational validation")
            for key in sorted(point):
                old=point[key]
                point[key]=Q(2,5) if key[1]==2 else Q(verify.M,2)
                if covered_names(point)!={name}:
                    point[key]=old
            points[name]=[[i,a,str(val)] for (i,a),val in sorted(point.items())
                          if val!=(Q(2,5) if a==2 else Q(verify.M,2))]
    return len(boxes),len(stay),points


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data",type=Path)
    ap.add_argument("--irredundant",action="store_true",
                    help="also find a point covered only by each required original leaf orbit")
    ap.add_argument("--private-output",type=Path,
                    help="generate a new set of private rational points for independent checking")
    opt=ap.parse_args()
    data=verify.inputs(opt.data)
    masks,perms=verify.inventory(data["stabs18-endpoint-window.json"])
    points={}
    for case in (53,55,82,92,115,137):
        mask=masks[case];owners={i for i in range(21) if mask&(1<<i)}
        stabs=[g for g,perm in perms.items() if {perm[i] for i in owners}==owners]
        groups=[(f"{ri}.{j}",[verify.pullback(verify.box(head+sub,owners,True),g,perms) for g in stabs])
                for ri,(head,table) in enumerate(verify.normalized_roots(case,data,mask,owners))
                for j,(sub,_,_) in enumerate(table)]
        count,kept,points[case]=inspect(case,groups,opt.irredundant or bool(opt.private_output))
        message=f"case {case}: UNSAT outside {count} nonempty lifted boxes and outside {kept} retained leaf orbits"
        if opt.irredundant or opt.private_output:
            message+=", each retained leaf necessary even with all other originals"
        print(message,flush=True)
    if opt.private_output:
        opt.private_output.write_text("{\n"+",\n".join(
            f'  "{case}": {{\n' + ",\n".join(
                f'    "{name}": '+json.dumps(values,separators=(",",":")) for name,values in table.items())
            +"\n  }" for case,table in points.items())+"\n}\n")
