"""Independent dual verification by signed support functions of the squares."""
import json
from pathlib import Path
from field import Q,q,I,O,half,dot

source=Path(__file__).resolve().parent
stress_dir=source.parent
def vadd(a,b):return tuple(x+y for x,y in zip(a,b))
def minus(a,b):return tuple(x-y for x,y in zip(a,b))
def times(k,a):return tuple(k*x for x in a)
def zero():return (O,O)
def rot(u):return (-u[1],u[0])
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def zmin(a,b):return a if (b-a).sig()>=0 else b
def zmax(a,b):return a if (a-b).sig()>=0 else b
def sign(k):return q(k.sig())

def stress_balance(record,stress):
    side=q(*record['side'])
    tiles={f['id']:((q(*f['x']),q(*f['y'])),(q(*f['c']),q(*f['s']))) for f in record['frames']}
    if len(tiles)!=18:raise ValueError('incorrect layout')
    forces={i:zero() for i in tiles};couples={i:O for i in tiles};edge=O
    def apply(i,p,F,w):
        forces[i]=vadd(forces[i],times(w,F))
        couples[i]+=w*cross(minus(p,tiles[i][0]),F)
    for key,weight in stress.items():
        w=q(*weight)
        if w.sig()<0:raise ValueError('negative stress')
        fields=key.split(':')
        if fields[0]!='face':
            tag=fields[0];i,k=map(int,fields[1].split('.'))
            u=tiles[i][1];v=rot(u)
            su=(1,-1,-1,1)[k];sv=(1,1,-1,-1)[k]
            p=vadd(tiles[i][0],times(half,vadd(times(q(su),u),times(q(sv),v))))
            a=int(tag[-1]);N=[O,O]
            N[a]=I if tag.startswith('min') else -I
            if p[a]!=(O if tag.startswith('min') else side):raise ValueError('selected wall is not in contact')
            apply(i,p,N,w)
            if tag.startswith('max'):edge+=w
            continue
        _,iteg,jstr,end=fields
        i,k=map(int,iteg.split('.'));j=int(jstr);end=int(end)
        c,u=tiles[i];d,U=tiles[j];v=rot(u);V=rot(U)
        n=[v,times(-I,u),times(-I,v),u][k]
        t=rot(n)
        face_center=vadd(c,times(half,n))
        normal_dist=dot(minus(d,face_center),n) - half*(abs(dot(n,U))+abs(dot(n,V)))
        if normal_dist!=O:raise ValueError('second square is not supported by the chosen face line')
        dpos=d;span=O
        for axis in (U,V):
            h=dot(n,axis)
            if h==O:span+=half*abs(dot(t,axis))
            else:dpos=minus(dpos,times(half*sign(h),axis))
        mid=dot(minus(dpos,face_center),t)
        lo=zmax(-half,mid-span);hi=zmin(half,mid+span)
        if (hi-lo).sig()<0 or (hi==lo and abs(lo)==half):raise ValueError('no regular contact')
        if end==1 and lo==hi:raise ValueError('duplicate point')
        e=lo if end==0 else hi
        p=vadd(face_center,times(e,t))
        apply(i,p,times(-I,n),w);apply(j,p,n,w)
    if any(v!=zero() for v in forces.values()) or any(z!=O for z in couples.values()) or edge!=I:
        raise ValueError('unbalanced')
    return sum(q(*v).sig()>0 for v in stress.values())
for name,stressname in [('hamalainen','hamalainen'),('gustafson','gustafson'),('cantrell','cantrell'),('gensane-ryckelynck','gensane-ryckelynck'),('mira-six-tilt','six-tilt')]:
    record=json.loads((source/(name+'-exact.json')).read_text())
    stress=json.loads((stress_dir/(stressname+'-stress.json')).read_text())
    print(name,stress_balance(record,stress),'exact nonzero stresses')
    for mutate in ('double','negative','delete','zero'):
        wrong=dict(stress)
        k=next(k for k,v in stress.items() if q(*v).sig()>0)
        if mutate=='delete':del wrong[k]
        elif mutate=='double':wrong[k]=(q(2)*q(*wrong[k])).pair()
        elif mutate=='negative':wrong[k]=(-q(*wrong[k])).pair()
        elif mutate=='zero':wrong={k:O.pair() for k in wrong}
        try:stress_balance(record,wrong)
        except ValueError:pass
        else:raise ValueError('mutation accepted '+name+' '+mutate)
print('All 20 altered certificates rejected.')
