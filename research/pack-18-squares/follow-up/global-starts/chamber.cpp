// Overlap forces for polydisperse squares in a cyclically sheared chamber.
#include <algorithm>
#include <array>
#include <cmath>

namespace {
constexpr int count = 18;
constexpr int dim = 3*count;
using Vec = std::array<double, dim>;
double sign(double x) { return (x > 0) - (x < 0); }

double forces(const double* q, const double* radius, double width, double height,
              double shear, Vec& force) {
    std::array<double,count> c{}, s{};
    force.fill(0);
    double energy = 0;
    const double wallnorm = std::sqrt(1+shear*shear);
    for (int i=0; i<count; ++i) {
        const int k=3*i;
        c[i] = std::cos(q[k+2]);
        s[i] = std::sin(q[k+2]);
        for (int wall=0; wall<2; ++wall) {
            const double nx=wall==0 ? 1/wallnorm : 0;
            const double ny=wall==0 ? -shear/wallnorm : 1;
            const double bound=wall==0 ? width/(2*wallnorm) : height/2;
            const double projection=q[k]*nx+q[k+1]*ny;
            const double u=nx*c[i]+ny*s[i], v=-nx*s[i]+ny*c[i];
            const double pen=std::abs(projection)+radius[i]*(std::abs(u)+std::abs(v))-bound;
            if (pen<=0) continue;
            energy+=pen*pen/2;
            force[k]-=pen*sign(projection)*nx;
            force[k+1]-=pen*sign(projection)*ny;
            force[k+2]-=pen*radius[i]*(sign(u)*v-sign(v)*u);
        }
        for (int j=0; j<i; ++j) {
            const int h=3*j;
            const double x=q[h]-q[k], y=q[h+1]-q[k+1];
            const double cutoff=1.414213562373096*(radius[i]+radius[j]);
            if (std::abs(x)>cutoff || std::abs(y)>cutoff) continue;
            const double cc=c[i]*c[j]+s[i]*s[j], ss=c[i]*s[j]-s[i]*c[j];
            const double m=std::abs(cc)+std::abs(ss), dm=-sign(cc)*ss+sign(ss)*cc;
            double best=1e10, bx=0,by=0,bi=0,bj=0;
            for (int owner : {i,j}) {
                const double other=owner==i ? radius[j] : radius[i];
                for (int perp=0; perp<2; ++perp) {
                    const double nx=perp ? -s[owner] : c[owner], ny=perp ? c[owner] : s[owner];
                    const double projection=x*nx+y*ny, sg=sign(projection);
                    const double pen=radius[owner]+other*m-std::abs(projection);
                    if (pen>=best) continue;
                    best=pen; bx=sg*nx; by=sg*ny;
                    const double rot=sg*(-x*ny+y*nx);
                    bi=-other*dm-(owner==i ? rot : 0);
                    bj=other*dm-(owner==j ? rot : 0);
                }
            }
            if (best<=0) continue;
            energy+=best*best/2;
            force[k]-=best*bx;force[k+1]-=best*by;force[k+2]-=best*bi;
            force[h]+=best*bx;force[h+1]+=best*by;force[h+2]-=best*bj;
        }
    }
    return energy;
}
}

extern "C" double relax(double* q, const double* r, double w, double h,
                        double shear, int steps) {
    Vec v{}, f{};
    double dt=.055, mix=.18, energy=0;
    int good=0;
    for (int n=0; n<steps; ++n) {
        energy=forces(q,r,w,h,shear,f);
        if (energy<1e-15) break;
        double power=0, v2=0, f2=0;
        for (int k=0; k<dim; ++k) {
            v[k]+=dt*f[k];
            power+=v[k]*f[k];v2+=v[k]*v[k];f2+=f[k]*f[k];
        }
        if (power<0) {
            v.fill(0);dt=std::max(.006,.55*dt);good=0;mix=.18;
        } else {
            if (++good>6) {dt=std::min(.23,dt*1.06);mix*=.99;}
            const double scale=std::sqrt(v2/std::max(f2,1e-300));
            for (int k=0;k<dim;++k) v[k]=(1-mix)*v[k]+mix*scale*f[k];
        }
        for (int k=0;k<dim;++k) q[k]+=std::clamp(dt*v[k],-.11,.11);
    }
    return energy;
}
extern "C" double energy_and_force(const double* q,const double* r,double w,
                                    double h,double shear,double* f) {
    Vec tmp;
    const double e=forces(q,r,w,h,shear,tmp);
    std::copy(tmp.begin(),tmp.end(),f);
    return e;
}
