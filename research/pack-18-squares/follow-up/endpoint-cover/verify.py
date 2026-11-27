"""Independently check coverage of the six endpoint classes from JSON alone."""
import argparse
from collections import Counter
from fractions import Fraction as Q
from functools import lru_cache
from hashlib import sha256
from itertools import combinations, combinations_with_replacement, product
import json
from pathlib import Path
from urllib.request import urlopen

PIN = "78bec6aacebf304d942a9225e16c2f18165778ff"
SOURCE = f"https://raw.githubusercontent.com/Mira-Cult/math/{PIN}/notes/geometry/unit-square-packing-18/replay"
FILES = {
    "stabs18-endpoint-window.json": "78a24ce2869910ef86824cdab5e3fa00811e1b78594ba6e2a16dd75cdf7b8d45",
    "n18-482-base.json": "d6fa37860cde0d0e8f8ddedc25508f478fe30112be16e79697cb9ab59c54f086",
    "full-endpoint-mask-cases.json": "15c97c04853fdd5a851c17d1929dd866ebe9bf12519c0a07dc461db1d6796d3d",
    "second-endpoint-mask-cases.json": "95e012935bffde956d0be815cc41c2ca70075a562c69820e6c1f0b4261dc7e44",
    "residual-82-cases.json": "c1657ecc5aae295b415fdff0b4875436f770439c6d9336050f8d37acbef0e05f",
    "residual-92-cases.json": "a63c93ebda866877314e0703a25363480254ae53dd88b8d217e557d290f42ec0",
    "residual-115-cases.json": "91a6687e4b48f52a9892b036646b65250e0f52d3da006002cab1070c90041188",
}
M = 4_822_876             # lengths in millionths of a unit
BANDS = 128
IDENTITY = (0, 0, 0)
KINDS = ("empty", "wall", "chord", "faces")
# Each name is root.leaf, both zero based. These removals are simultaneous.
OMIT = {82: {"7.0","8.0","10.0","11.0"}, 92: {"2.1","2.3","4.1"}, 137: {"3.0"}}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def inputs(directory):
    result = {}
    for name, digest in FILES.items():
        if directory:
            raw = (directory/name).read_bytes()
        else:
            with urlopen(f"{SOURCE}/{name}", timeout=30) as response:
                raw = response.read()
        require(sha256(raw).hexdigest() == digest, f"Wrong pinned data: {name}")
        result[name] = json.loads(raw)
    return result


def move(p, g, scale):
    swap, fx, fy = g
    x,y = p[::-1] if swap else p
    return (scale-x if fx else x, scale-y if fy else y)


def inventory(config):
    require(Q(config["cap"])*10**6 == M, "Unexpected test box")
    scale = config["scale"]
    group = list(product((0,1), repeat=3))
    marks = sorted({move(p,g,scale) for p in config["orbits"] for g in group})
    require(len(marks) == config["marks"] == 21, "Invalid rack")
    perms = {g: tuple(marks.index(move(p,g,scale)) for p in marks) for g in group}
    triples = list(combinations(range(21),3))
    reps = {min(tuple(sorted(u[i] for i in t)) for u in perms.values()) for t in triples}
    masks = sorted((1<<21)-1-sum(1<<i for i in triple) for triple in reps)
    require(len(triples)==1330 and len(masks)==187, "Invalid orbit enumeration")
    return masks,perms


def ranges(key, physical):
    if key[1] == 2:
        return (Q(0),Q(1)) if physical else (0,BANDS-1)
    return Q(0),Q(M)


def box(path, owners, physical=False):
    """Intersect cuts on common integer band indices BEFORE projecting to t."""
    require(len(path)%3==0, "Invalid cut sequence")
    result = {}
    for i,op,n in zip(path[::3],path[1::3],path[2::3]):
        require(i in owners and op in range(6) and type(n) is int, "Bad cut")
        key = (i,op//2)
        lo,hi = result.get(key,ranges(key,False))
        if op >= 4:
            require(0<n<BANDS, "Invalid angular threshold")
        else:
            require(0<=n<=M, "Invalid centre threshold")
        if op%2:
            lo = max(lo,n)
        else:
            hi = min(hi,n-1 if op==4 else n)
        if lo>hi:
            return None
        result[key] = (lo,hi)
    if physical:
        for key,(lo,hi) in list(result.items()):
            if key[1]==2:
                result[key] = (Q(lo,BANDS),Q(hi+1,BANDS))
    return {k:v for k,v in result.items() if v!=ranges(k,physical)}


def mirror_angle(t):
    return (1-t)/(1+t)


def pullback(b,g,perms):
    """Preimage under the symmetry of the physical centres and square frames."""
    if b is None:
        return None
    inv = {j:i for i,j in enumerate(perms[g])}
    swap,fx,fy = g
    out = {}
    for (j,axis),(lo,hi) in b.items():
        if axis==2:
            if swap^fx^fy:
                lo,hi = mirror_angle(hi),mirror_angle(lo)
            out[inv[j],2] = (lo,hi)
        else:
            if (fx,fy)[axis]:
                lo,hi = M-hi,M-lo
            out[inv[j],axis^swap] = (lo,hi)
    return out


def intersection(a,b):
    if a is None or b is None:
        return None
    out = dict(a)
    for k,(lo,hi) in b.items():
        l,r = out.get(k,ranges(k,True))
        l,r = max(l,lo),min(r,hi)
        if l>r:
            return None
        out[k] = (l,r)
    return out


def contained(inner,outer):
    if inner is None:
        return True
    if outer is None:
        return False
    return all(lo<=inner.get(k,ranges(k,True))[0] and
               inner.get(k,ranges(k,True))[1]<=hi for k,(lo,hi) in outer.items())


def population(mask):
    return bin(mask).count("1")


def coverage(boxes,physical):
    """An exact covering decision; return an uncovered partial point if one exists.

    Every real comparison is constant on open intervals between successive
    distinct endpoints. Singleton endpoints are additional atoms. A discrete
    angle dimension ranges over all integer band indices.
    """
    boxes=[b for b in boxes if b is not None]
    if not boxes:
        return {},0
    dims=sorted({key for b in boxes for key in b})
    free=[]
    options=[]
    for key in dims:
        default=ranges(key,physical)
        intervals=[b.get(key,default) for b in boxes]
        free.append(sum(1<<i for i,v in enumerate(intervals) if v==default))
        if not physical and key[1]==2:
            atoms=range(BANDS)
        else:
            ends=sorted({*default,*(e for it in intervals for e in it)})
            atoms=ends+[(a+b)*Q(1,2) for a,b in zip(ends,ends[1:])]
        seen={}
        for v in atoms:
            keep=sum(1<<i for i,(lo,hi) in enumerate(intervals) if lo<=v<=hi)
            seen.setdefault(keep,v)
        options.append(seen)

    @lru_cache(None)
    def walk(unused, mask):
        if not mask:
            return ()
        whole=mask
        rest=[i for i in range(len(dims)) if unused & (1<<i)]
        for i in rest:
            whole &= free[i]
        if whole:
            return None
        # Ignore current-axis atoms with identical remaining boxes.
        choices={}
        for i in rest:
            by_child={}
            for permitted,v in options[i].items():
                child=mask&permitted
                if not child:
                    return ((dims[i],v),)
                by_child.setdefault(child,v)
            choices[i]=by_child
        i=min(rest,key=lambda i:(max(population(m) for m in choices[i]),
                                 len(choices[i]),i))
        for child,v in sorted(choices[i].items(),key=lambda p:population(p[0])):
            bad=walk(unused^(1<<i),child)
            if bad is not None:
                return ((dims[i],v),)+bad
        return None

    missing=walk((1<<len(dims))-1,(1<<len(boxes))-1)
    return (None if missing is None else dict(missing)),walk.cache_info().currsize


def normalized_roots(case,data,mask,owners):
    """Decode the regions actually sent to the finite terminal tests."""
    if case in (53,55):
        source=("full-endpoint-mask-cases.json" if case==53 else "second-endpoint-mask-cases.json")
        roots=[]
        for lo,hi,leaves in data[source]:
            cuts=[]
            if case==53:
                if lo is not None:
                    cuts.extend([5,3,lo,15,1,lo,5,0,M-lo,15,2,M-lo])
                if hi is not None:
                    cuts.extend([5,2,hi])
            else:
                if lo is not None:
                    cuts.extend([9,1,lo])
                if hi is not None:
                    cuts.extend([9,0,hi])
            roots.append((cuts,leaves))
        return roots
    if case==137:
        bands,root=data["n18-482-base.json"][format(mask,"x")]
        require(bands==BANDS,"wrong angle grid")
        # The six checks and their 'faces' labels are explicit in the source
        # driver, rather than in a separate residual JSON.
        return [(path,[([],None,["faces"])]) for path,_,_ in root]
    return data[f"residual-{case}-cases.json"]


def kind(status):
    tag=status[0] if len(status)==1 else status[-1]
    require(tag in KINDS,"Unknown terminal label")
    return tag


def private_points(case,roots,owners,stabs,perms,points):
    """Check private assignments by transforming the point FORWARD and reading
    the raw cut sequence. This does not call box(), pullback() or coverage().
    """
    paths={f"{i}.{j}":head+tail for i,(head,table) in enumerate(roots)
           for j,(tail,_,_) in enumerate(table)}
    require(set(points)==set(paths)-OMIT.get(case,set()),"Private witness labels do not match the subcover")

    def satisfies(path,pose):
        candidates={}
        for i,op,n in zip(path[::3],path[1::3],path[2::3]):
            if op<4:
                z=pose[i][op//2]
                if (op%2==0 and z>n) or (op%2 and z<n):
                    return False
            else:
                scaled=BANDS*pose[i][2]
                # k <= scaled <= k+1, including both adjacent bands at a tie.
                low,high=candidates.get(i,(max(0,-((-scaled.numerator)//scaled.denominator)-1),
                                          min(BANDS-1,scaled.numerator//scaled.denominator)))
                if op==4:
                    high=min(high,n-1)
                else:
                    low=max(low,n)
                if low>high:
                    return False
                candidates[i]=(low,high)
        return True

    for label,changes in points.items():
        values={i:[Q(M,2),Q(M,2),Q(2,5)] for i in owners}
        seen=set()
        for i,axis,frac in changes:
            require(i in owners and axis in range(3) and (i,axis) not in seen,"Bad private point axis")
            seen.add((i,axis))
            number=Q(frac)
            require(0<number<1 if axis==2 else 500000<number<M-500000,
                    "Private coordinate outside the open wall inset or open angle chart")
            values[i][axis]=number
        hits=set()
        for g in stabs:
            pose={perms[g][i]:(*move((x,y),g,M),mirror_angle(t) if g[0]^g[1]^g[2] else t)
                  for i,(x,y,t) in values.items()}
            hits.update(name for name,path in paths.items() if satisfies(path,pose))
        require(hits=={label},f"Invalid mandatory leaf witness {case}:{label}: {hits}")
    return len(points)


def roots_check(case,data,mask,owners,perms,points):
    roots=normalized_roots(case,data,mask,owners)
    stabs=[g for g,p in perms.items() if {p[i] for i in owners}==owners]
    physical=[box(path,owners,True) for path,_ in roots]
    quotient=[pullback(b,g,perms) for g in stabs for b in physical]
    missing,nodes=coverage(quotient,True)
    require(missing is None, f"Class {case}: uncovered physical root assignment {missing}")
    leaves=Counter()
    child_nodes=0
    for index,(_,table) in enumerate(roots):
        branches=[box(p,owners,False) for p,_,_ in table]
        gap,n=coverage(branches,False)
        require(gap is None,f"Class {case}, root {index}: uncovered subregion {gap}")
        leaves.update(kind(act) for _,_,act in table)
        child_nodes+=n

    details={}
    empty_roots=[i for i,b in enumerate(physical) if b is None]
    empty_leaves=[f"{i}.{j}" for i,(head,table) in enumerate(roots)
                  for j,(suffix,_,_) in enumerate(table) if box(head+suffix,owners,False) is None]
    details["empty_by_cuts_roots"]=empty_roots
    details["empty_by_cuts_leaves"]=empty_leaves
    all_boxes=[]
    kept_boxes=[]
    kept_kinds=Counter()
    for i,(head,table) in enumerate(roots):
        for j,(tail,_,action) in enumerate(table):
            name=f"{i}.{j}"
            physical_leaf=box(head+tail,owners,True)
            lifted=[pullback(physical_leaf,g,perms) for g in stabs]
            all_boxes.extend(lifted)
            if name not in OMIT.get(case,set()):
                kept_boxes.extend(lifted)
                kept_kinds[kind(action)]+=1
    for label,regions in [("full",all_boxes),("reduced",kept_boxes)]:
        hole,n=coverage(regions,True)
        require(hole is None,f"Class {case}: {label} full-leaf cover leaves a gap {hole}")
        details[f"{label}_leaf_states"]=n
    details["removed"]=sorted(OMIT.get(case,set()))
    details["retained_actions"]=dict(sorted(kept_kinds.items()))
    details["necessary_even_among_all_originals"]=private_points(case,roots,owners,stabs,perms,points)
    if case==137:
        refl=(0,0,1)
        require(refl in stabs and contained(physical[3],pullback(physical[1],refl,perms)),
                "137:3 not inside the reflection of 137:1")
    if case==92:
        require(perms[(0,0,1)][10]==10 and Q(181,128)**2<2,
                "92 centre-angle cutoff does not lie below sqrt(2)-1")
    if case in (82,92):
        # Check the exact reflected subregions without using any integer
        # outward-rounding recipe or the source's helper for mirroring.
        bands,table=data["n18-482-base.json"][format(mask,"x")]
        require(bands==BANDS,"unexpected base grid")
        base=[box(p,owners,True) for p,_,_ in table]
        require(coverage(base,True)[0] is None,"base does not cover its mask")
        coupled,g=([0,4,5],(1,0,0)) if case==82 else ([1,2],(0,0,1))
        require(g in stabs and all(perms[g][perms[g][j]]==j for j in owners),"invalid involution")
        exact=[(str(i),b) for i,b in enumerate(base) if i not in coupled]
        for i,j in combinations_with_replacement(coupled,2):
            exact.append((f"{i}x{j}",intersection(base[i],pullback(base[j],g,perms))))
        # Check the data's corresponding root, including the possibility of a
        # genuinely inconsistent exact pair. In case 82 four of these pairs and
        # their four enlarged root rows are already empty by their own cuts.
        require(len(exact)==len(physical),"wrong number of reflected roots")
        matches={}
        for idx,((label,cell),enclosure) in enumerate(zip(exact,physical)):
            require(contained(cell,enclosure),f"Uncovered reflected base pair {case}:{label}")
            matches[label]={"stored_root":idx,"exact_pair_empty":cell is None,
                            "stored_root_empty":enclosure is None}
        details["exact_root_enclosures"]=matches
    return {"mask":hex(mask),"roots":len(roots),"leaves":dict(sorted(leaves.items())),
            "count":sum(leaves.values()),"symmetries":[list(g) for g in stabs],
            "root_states":nodes,"child_states":child_nodes,**details}


def controls():
    key=(2,2)
    impossible=[2,4,64,2,5,64]
    require(box(impossible,{2},True) is None,"contradictory same-band interval survived")
    choices=[box([2,4,64],{2}),box([2,5,64],{2})]
    require(coverage(choices,False)[0] is None,"complementary index cuts lost coverage")
    require(coverage(choices[:1],False)[0] is not None,"missing upper angular branch accepted")
    # At the reflecting boundary a half-angle 1/2 maps to 1/3, not to 1/2.
    require(mirror_angle(Q(1,2))==Q(1,3) and mirror_angle(Q(1,3))==Q(1,2),"reflection")
    require(Q(42,128)<Q(1,3)<Q(43,128),"reflected grid boundary")
    # Singleton atoms must be retained when a domain itself is a point.
    require(coverage([{key:(Q(0),Q(0))},{key:(Q(1),Q(1))}],True)[0] is not None,
            "a gap between closed singleton intervals was missed")


def mutation_tests(data,masks,perms):
    case=82
    mask=masks[case]
    owners={i for i in range(21) if mask&(1<<i)}
    raw=normalized_roots(case,data,mask,owners)
    roots=[box(path,owners,True) for path,_ in raw]
    stabs=[g for g,p in perms.items() if {p[i] for i in owners}==owners]
    def expand(bs):
        return [pullback(b,g,perms) for g in stabs for b in bs]
    def witness(bs):
        hole,_=coverage(bs,True)
        require(hole is not None,"Mutation was falsely accepted")
        complete={k:hole.get(k,Q(0)) for b in bs if b is not None for k in b}
        require(not any(all(a<=complete[k]<=z for k,(a,z) in b.items())
                        for b in bs if b is not None),"Invalid mutation witness")
        return {f"{i}.{'xyt'[a]}":str(v) for (i,a),v in sorted(hole.items())}
    no_symmetry=witness(roots)
    bad=list(roots)
    bad[12]=dict(roots[12])
    require(bad[12][10,2]==(Q(42,128),Q(64,128)),"Unexpected angle on root 12")
    bad[12][10,2]=(Q(60,128),Q(64,128))
    wrong_reflection=witness(expand(bad))
    # Removing one of the two complementary coordinate cuts of a real
    # descendant table must fail even if all remaining regions are tested.
    table=raw[0][1]
    require(len(table)==2,"Unexpected control table")
    child_gap,_=coverage([box(table[0][0],owners,False)],False)
    require(child_gap is not None,"Dropped child was falsely accepted")
    return {"82_identity_only_uncovered":no_symmetry,
            "82_narrowed_reflected_angle_uncovered":wrong_reflection,
            "82_missing_descendant_detected":True}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data",type=Path,help="local pinned replay directory containing only the requested JSON data")
    ap.add_argument("--output",type=Path)
    ap.add_argument("--private-points",type=Path,default=Path(__file__).with_name("private-points.json"))
    args=ap.parse_args()
    data=inputs(args.data)
    masks,perms=inventory(data["stabs18-endpoint-window.json"])
    controls()
    points=json.loads(args.private_points.read_bytes())
    report={}
    for case in (53,55,82,92,115,137):
        mask=masks[case]
        owners={i for i in range(21) if mask&(1<<i)}
        res=roots_check(case,data,mask,owners,perms,points[str(case)])
        report[case]=res
        print(case,res["roots"],res["count"],res["leaves"],flush=True)
    all_kinds=Counter()
    retained=Counter()
    for row in report.values():
        all_kinds.update(row["leaves"])
        retained.update(row["retained_actions"])
    require(sum(all_kinds.values())==193,"wrong terminal count")
    require(retained=={"empty":83,"chord":46,"faces":56},"unexpected reduced cover")
    out={"pin":PIN,"cases":report,"total_actions":dict(sorted(all_kinds.items())),
         "controls":mutation_tests(data,masks,perms),
         "total_terminals":sum(all_kinds.values()),"retained_actions":dict(sorted(retained.items())),
         "retained_terminals":sum(retained.values())}
    if args.output:
        args.output.write_text(json.dumps(out,indent=2)+"\n")
    print("Every physical root covered up to the mask's true stabilizer; all 193 descendants accounted for.")
    print("Minimum cut-only subcover: 185 leaves, with one private rational point per mandatory record.")


if __name__=="__main__":
    main()
