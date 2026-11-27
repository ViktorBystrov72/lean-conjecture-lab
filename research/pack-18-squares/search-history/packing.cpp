#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>

namespace {
constexpr int n = 18, d = 3*n+1;
using Vec = std::array<double,d>;
inline double sign(double v) {return (v>0)-(v<0);}
inline double dot(const Vec& x, const Vec& y) {
    double sum=0;
    for (int i=0;i<d;i++) sum+=x[i]*y[i];
    return sum;
}
struct Axis {double x, y;};
struct Constraint {
    double gap;
    int a, b;
    double x, y, da, db;
};
constexpr int m = 2*n+n*(n-1)/2;
void geometry(const double* x, Constraint* cons) {
    const double l=x[d-1];
    std::array<Axis,n> u;
    int p=0;
    for(int i=0;i<n;i++) {
        double c=std::cos(x[3*i+2]), s=std::sin(x[3*i+2]);
        u[i]={c,s};
        const double h=.5*(std::abs(c)+std::abs(s));
        const double dh=.5*(-sign(c)*s+sign(s)*c);
        for(int k=0;k<2;k++) {
            const double coord=x[3*i+k];
            cons[p++]={l*.5-std::abs(coord)-h,i,-1,k==0?-sign(coord):0,k==1?-sign(coord):0,-dh,0};
        }
    }
    for(int i=0;i<n;i++) for(int j=0;j<i;j++) {
        const double dx=x[3*j]-x[3*i], dy=x[3*j+1]-x[3*i+1];
        const double c=u[i].x*u[j].x+u[i].y*u[j].y;
        const double s=u[i].x*u[j].y-u[i].y*u[j].x;
        const double h=.5*(1+std::abs(c)+std::abs(s));
        const double dh=.5*(-sign(c)*s+sign(s)*c);
        Axis best{};
        double magnitude=-1, projected=0;
        int owner=0;
        for (int a : {i,j}) {
            const Axis v=u[a];
            for (const Axis w : {v,Axis{-v.y,v.x}}) {
                double z=dx*w.x+dy*w.y;
                if(std::abs(z)>magnitude) {
                    best=w; owner=a; projected=z; magnitude=std::abs(z);
                }
            }
        }
        double axisDerivative=sign(projected)*(dy*best.x-dx*best.y);
        cons[p++]={magnitude-h,i,j,-sign(projected)*best.x,-sign(projected)*best.y,
                   dh+(owner==i?axisDerivative:0),-dh+(owner==j?axisDerivative:0)};
    }
}
double cost(const Vec& x,double weight,unsigned fixed, Vec& grad) {
    std::array<Constraint,m> cons; geometry(x.data(),cons.data());
    grad.fill(0); grad[d-1]=1;
    double cost=x[d-1];
    for(const auto& g:cons) {
        if(g.gap>=0) continue;
        cost+=weight*g.gap*g.gap;
        double s=2*weight*g.gap;
        grad[3*g.a]+=s*g.x; grad[3*g.a+1]+=s*g.y;
        grad[3*g.a+2]+=s*g.da;
        if(g.b==-1) grad[d-1]+=.5*s;
        else {
            grad[3*g.b]-=s*g.x; grad[3*g.b+1]-=s*g.y;
            grad[3*g.b+2]+=s*g.db;
        }
    }
    for(int i=0;i<n;i++) if(fixed&(1u<<i)) grad[3*i+2]=0;
    return cost;
}
}
extern "C" {
int polish(double* position,double weight,unsigned fixed,int budget) {
    // L-BFGS with a monotone Armijo line search on the piecewise smooth penalty.
    constexpr int mem=7;
    std::array<Vec,mem> ss,ys;
    std::array<double,mem> rho{},alpha{};
    int head=0, count=0, steps=0;
    Vec x, grad, p, trial, newg;
    std::memcpy(x.data(),position,d*sizeof(double));
    double f=cost(x,weight,fixed,grad);
    for (;steps<budget;steps++) {
        p=grad;
        for(int h=0;h<count;h++) {
            int j=(head-1-h+mem)%mem;
            alpha[j]=rho[j]*dot(ss[j],p);
            for(int k=0;k<d;k++) p[k]-=alpha[j]*ys[j][k];
        }
        int recent=(head+mem-1)%mem;
        double scaling=count?1./(rho[recent]*dot(ys[recent],ys[recent])):.5/weight;
        for(double &v:p) v*=scaling;
        for(int h=count;h>0;h--) {
            int j=(head-h+mem)%mem;
            double beta=rho[j]*dot(ys[j],p);
            for(int k=0;k<d;k++) p[k]+=(alpha[j]-beta)*ss[j][k];
        }
        double descent=dot(p,grad);
        if(!(descent>1e-19)) break;
        double step=1, newf=f;
        int lines=0;
        for(;lines<25;lines++) {
            for(int k=0;k<d;k++) trial[k]=x[k]-step*p[k];
            newf=cost(trial,weight,fixed,newg);
            if(newf<=f-1e-4*step*descent) break;
            step*=.5;
        }
        if(lines==25 || f-newf<1e-15*(1+std::abs(f))) {
            if(count>0 && lines==25){count=0;head=0;continue;}
            break;
        }
        Vec s,y;
        for(int k=0;k<d;k++){s[k]=trial[k]-x[k];y[k]=newg[k]-grad[k];}
        double sy=dot(s,y);
        if(sy>1e-14*std::sqrt(dot(s,s)*dot(y,y))) {
            ss[head]=s;ys[head]=y;rho[head]=1/sy;
            head=(head+1)%mem;count=std::min(mem,count+1);
        }
        x=trial;grad=newg;f=newf;
    }
    std::memcpy(position,x.data(),d*sizeof(double));return steps;
}
void constraints(const double* x,double* gaps,double* jac) {
    std::array<Constraint,m> cons; geometry(x,cons.data());
    if(jac) std::fill(jac,jac+m*d,0.);
    for(int p=0;p<m;p++) {
        const auto& g=cons[p];
        gaps[p]=g.gap;
        if(!jac) continue;
        double* row=jac+p*d;
        row[3*g.a]=g.x;row[3*g.a+1]=g.y;row[3*g.a+2]=g.da;
        if(g.b==-1) row[d-1]=.5;
        else {row[3*g.b]=-g.x;row[3*g.b+1]=-g.y;row[3*g.b+2]=g.db;}
    }
}
}
