from dataclasses import dataclass
from fractions import Fraction as F
from math import sqrt

@dataclass(frozen=True)
class Q:
    a: F=F(0)
    b: F=F(0)
    def __neg__(self):return Q(-self.a,-self.b)
    def __add__(self,v):return Q(self.a+v.a,self.b+v.b)
    def __sub__(self,v):return self+-v
    def __mul__(self,v):return Q(self.a*v.a+7*self.b*v.b,self.a*v.b+self.b*v.a)
    def __truediv__(self,v):
        n=v.a*v.a-7*v.b*v.b
        z=self*Q(v.a,-v.b)
        return Q(z.a/n,z.b/n)
    def sig(self):
        sg=lambda v: int(v>0)-int(v<0)
        if self.a*self.b>=0:return sg(self.a) or sg(self.b)
        return sg(self.a)*sg(self.a*self.a-7*self.b*self.b)
    def __abs__(self):return self if self.sig()>=0 else -self
    def __float__(self):return float(self.a)+sqrt(7)*float(self.b)
    def pair(self):return [str(self.a),str(self.b)]
def q(a=0,b=0):return Q(F(a),F(b))
O=q();I=q(1);half=q('1/2');H=q('7/2','1/2')

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]
