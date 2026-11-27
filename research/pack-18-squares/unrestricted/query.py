"""Build the real, unrestricted feasibility question for n congruent squares.

All constraints are rational polynomial inequalities. A numerical candidate,
partial assignment or list of preferred positions is unnecessary.
"""
import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


def smt(value):
    q = Fraction(value)
    if q < 0:
        return f"(- {smt(-q)})"
    return str(q.numerator) if q.denominator == 1 else f"(/ {q.numerator} {q.denominator})"


def problem(n=18, *, strict_target=True):
    if n < 1:
        raise ValueError("positive number of squares required")
    lines = ["(set-logic QF_NRA)", "(declare-const L Real)", "(assert (> L 0))"]
    if strict_target:
        lines.extend(["(define-fun h () Real (- (* 2 L) 7))",
                      "(assert (or (< h 0) (< (* h h) 7)))"])
    lines.append(f"(assert (>= (* L L) {n}))")
    for i in range(n):
        for coord in ("x","y","c","s"):
            lines.append(f"(declare-const {coord}{i} Real)")
        c,s = f"c{i}",f"s{i}"
        lines.append(f"(assert (and (>= {c} 0) (>= {s} 0) (= (+ (* {c} {c}) (* {s} {s})) 1)))")
        if i:
            lines.append(f"(assert (<= s{i-1} {s}))")
        for axis in ("x","y"):
            z=f"{axis}{i}"
            lines.append(f"(assert (and (>= (* 2 {z}) (+ {c} {s})) "
                         f"(<= (+ (* 2 {z}) {c} {s}) (* 2 L))))")
    for i in range(n):
        for j in range(i+1,n):
            # All angles lie in the first quadrant and are sorted. Therefore
            # cos(theta_j-theta_i) and sin(theta_j-theta_i) are nonnegative.
            d=f"{i}_{j}"
            dx, dy, extent = f"dx{d}", f"dy{d}", f"b{d}"
            lines.extend([f"(define-fun {dx} () Real (- x{j} x{i}))",
                          f"(define-fun {dy} () Real (- y{j} y{i}))",
                          f"(define-fun {extent} () Real (+ 1 (* c{i} c{j}) (* s{i} s{j}) "
                          f"(* c{i} s{j}) (- (* s{i} c{j}))))"])
            clauses=[]
            for k in (i,j):
                for tag,pr in (("a",f"(+ (* {dx} c{k}) (* {dy} s{k}))"),
                               ("b",f"(- (* {dy} c{k}) (* {dx} s{k}))")):
                    axis=f"p{d}_{k}{tag}"
                    lines.append(f"(define-fun {axis} () Real (* 2 {pr}))")
                    clauses.extend([f"(>= {axis} {extent})",f"(<= {axis} (- {extent}))"])
            lines.append("(assert (or "+" ".join(clauses)+"))")
            # Redundant, valid because each tile contains an open disk of radius 1/2.
            lines.append(f"(assert (>= (+ (* {dx} {dx}) (* {dy} {dy})) 1))")
    return "\n".join(lines)+"\n"


def run(exe, text, budget, seed):
    setup=f"(set-option :timeout {budget*1000})\n(set-option :random-seed {seed})\n"
    query=setup+text+"(check-sat)\n(get-info :reason-unknown)\n(get-info :all-statistics)\n"
    # Request a model only after a positive response, in the same solver process.
    with subprocess.Popen([exe, "-in", "-smt2"],text=True,stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT) as child:
        child.stdin.write(query)
        child.stdin.flush()
        verdict=child.stdout.readline().strip()
        rest=child.communicate(("(get-model)\n" if verdict=="sat" else "")+"(exit)\n")[0]
        if verdict not in ("sat","unsat","unknown") or child.returncode:
            raise RuntimeError(verdict+"\n"+rest)
    return verdict,rest.strip()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",type=Path,help="write SMT-LIB, including check-sat")
    ap.add_argument("--solver",help="also run this z3 executable on the unrestricted query")
    ap.add_argument("--seconds",type=int,default=60)
    ap.add_argument("--seed",type=int,default=180321)
    ap.add_argument("--receipt",type=Path)
    args=ap.parse_args()
    if args.seconds<1: ap.error("seconds must be positive")
    text=problem()
    if args.output: args.output.write_text(text+"(check-sat)\n")
    if args.solver:
        verdict,detail=run(args.solver,text,args.seconds,args.seed)
        print(verdict);print(detail)
        if args.receipt:
            version=subprocess.check_output([args.solver,"--version"],text=True).strip()
            args.receipt.write_text(json.dumps({"solver":version,"seed":args.seed,"seconds":args.seconds,
                                                "verdict":verdict,"detail":detail},indent=2)+"\n")
    elif not args.output:
        print(text+"(check-sat)")


if __name__=="__main__":
    main()
