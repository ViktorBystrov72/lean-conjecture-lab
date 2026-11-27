"""Independent D4/orbit and exact nearest-mark checker for Mira Cult's rack.

The only input taken from the remote proof is its JSON rack specification plus
the six potentially inhabited orbit indices listed in its public report.
"""
import argparse
from dataclasses import dataclass
from fractions import Fraction as F
from functools import total_ordering
from itertools import combinations, product
import json
from pathlib import Path

U = F(4822876, 1000000)
SCALE = 2000
GENERATORS = ((390,390),(617,617),(797,359),(1000,716),(1000,1000))
MIXED = {53,55,82,92,115,137}


@total_ordering
@dataclass(frozen=True)
class Quadratic:
    """An element a+b*sqrt(7)."""
    a: F
    b: F = F(0)

    @classmethod
    def of(cls, value):
        if isinstance(value, cls):
            return value
        return cls(F(value))

    def __add__(self, other):
        z = self.of(other)
        return Quadratic(self.a+z.a, self.b+z.b)

    __radd__ = __add__

    def __neg__(self):
        return Quadratic(-self.a,-self.b)

    def __sub__(self, other):
        return self + (-self.of(other))

    def __rsub__(self, other):
        return self.of(other) - self

    def __mul__(self, other):
        z = self.of(other)
        return Quadratic(self.a*z.a+7*self.b*z.b, self.a*z.b+self.b*z.a)

    __rmul__ = __mul__

    def __truediv__(self, scalar):
        return Quadratic(self.a/scalar,self.b/scalar)

    def sign(self):
        def s(v):
            return (v>0)-(v<0)
        if self.a==0: return s(self.b)
        if self.b==0 or s(self.b)==s(self.a): return s(self.a)
        return s(self.a)*s(self.a*self.a-7*self.b*self.b)

    def __eq__(self,other):
        try:
            z=self.of(other)
        except (TypeError, ValueError):
            return False
        return self.a==z.a and self.b==z.b

    def __lt__(self,other):
        return (self-other).sign()<0

    def __abs__(self):
        return -self if self.sign()<0 else self


def actions(x,y):
    return ((x,y),(SCALE-y,x),(SCALE-x,SCALE-y),(y,SCALE-x),
            (SCALE-x,y),(x,SCALE-y),(y,x),(SCALE-y,SCALE-x))


grid=sorted({p for x,y in GENERATORS for p in actions(x,y)})
assert len(grid)==21
marks=[(U*x/SCALE,U*y/SCALE) for x,y in grid]
d4=[tuple(grid.index(actions(x,y)[k]) for x,y in grid) for k in range(8)]


def canonical_missing(missing):
    return min(tuple(sorted(f[i] for i in missing)) for f in d4)


def mask(triple):
    return sum(1<<i for i in range(21) if i not in triple)


all_holes=list(combinations(range(21),3))
masks=sorted({mask(canonical_missing(t)) for t in all_holes})
assert len(all_holes)==1330 and len(masks)==187
orbit={t:masks.index(mask(canonical_missing(t))) for t in all_holes}


def classify(tiles):
    if len(tiles)!=18: raise ValueError("18 squares expected")
    owners=[]
    ties=0
    for x,y,c,s in tiles:
        distances=[max(abs((u-x)*c+(v-y)*s),abs((v-y)*c-(u-x)*s)) for u,v in marks]
        least=min(distances)
        if not least<F(1,2):raise ValueError("missing strict hit")
        nearest=tuple(i for i,d in enumerate(distances) if d==least)
        ties+=len(nearest)>1
        owners.append(nearest)
    results={}
    for selected in product(*owners):
        if len(set(selected))!=18:raise ValueError("shared owner")
        missing=tuple(i for i in range(21) if i not in selected)
        results[missing]=orbit[missing]
    return results,ties


def geometry(tiles,side):
    if len(tiles)!=18: raise ValueError("18 squares expected")
    for x,y,c,s in tiles:
        if c*c+s*s!=1: raise ValueError("nonunit orientation")
        w=(abs(c)+abs(s))/2
        if not (w<=x<=side-w and w<=y<=side-w):raise ValueError("wall contact violation")
    for (x,y,c,s),(X,Y,C,S) in combinations(tiles,2):
        for a,b in [(c,s),(-s,c),(C,S),(-S,C)]:
            lhs=2*abs(a*(X-x)+b*(Y-y))
            rhs=abs(a*c+b*s)+abs(-a*s+b*c)+abs(a*C+b*S)+abs(-a*S+b*C)
            if lhs>=rhs: break
        else: raise ValueError("overlapping squares")


def exact_source(path):
    data=json.loads(path.read_text())
    def q(ab):
        return Quadratic(*map(F,ab))
    if 'frames' in data:
        return q(data['side']),[tuple(q(frame[k]) for k in ['x','y','c','s']) for frame in data['frames']]
    if 'centers' in data:
        c=Quadratic(F(1,4),F(1,4))
        s=Quadratic(F(-1,4),F(1,4))
        return q(data['side']),[(q(x),q(y),c if tilt else Quadratic(F(1)),s if tilt else Quadratic(F(0))) for _,tilt,x,y in data['centers']]
    raise ValueError('unrecognized format')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',nargs='+',type=Path)
    for p in parser.parse_args().source:
        side,tiles=exact_source(p)
        geometry(tiles,side)
        assert side<=U
        assignments,ties=classify(tiles)
        print(p.name,'OK',assignments,'tied tiles',ties)
