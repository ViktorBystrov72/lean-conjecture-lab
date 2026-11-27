// Smooth each change of the optional tiles' sides by minimizing a soft
// contact energy. Each centre, tile angle and the container side is free.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>

namespace {
constexpr int max_dim = 3*21+1;
using Vector = std::array<double, max_dim>;
double sign(double x) { return (x>0)-(x<0); }
double dot(const Vector& a, const Vector& b, int dim) {
    double v=0;
    for (int k=0; k<dim; ++k) v += a[k]*b[k];
    return v;
}
double energy(const double* x, double* g, int n, const double* length, double weight) {
    const int last = 3*n;
    std::fill(g,g+last+1,0.);
    double objective=x[last];
    g[last]=1.;
    double cs[21], ss[21];
    for(int i=0;i<n;++i) {
        cs[i]=std::cos(x[3*i+2]); ss[i]=std::sin(x[3*i+2]);
        const double half=.5*length[i];
        const double reach=half*(std::abs(cs[i])+std::abs(ss[i]));
        const double dh=half*(-sign(cs[i])*ss[i]+sign(ss[i])*cs[i]);
        for(int k=0;k<2;++k) {
            const double v=x[3*i+k];
            const double overlap=std::abs(v)+reach-.5*x[last];
            if(overlap<=0) continue;
            const double scale=2*weight*overlap;
            objective+=weight*overlap*overlap;
            g[3*i+k]+=scale*sign(v);
            g[3*i+2]+=scale*dh;
            g[last]-=.5*scale;
        }
        for(int j=0;j<i;++j) {
            double dx=x[3*j]-x[3*i], dy=x[3*j+1]-x[3*i+1];
            if (std::max(std::abs(dx),std::abs(dy))>.708*(length[i]+length[j])) continue;
            double c=cs[i]*cs[j]+ss[i]*ss[j];
            double s=cs[i]*ss[j]-ss[i]*cs[j];
            double sum=std::abs(c)+std::abs(s);
            double best=-1e100, normal_x=0,normal_y=0,projection=0, other_half=0;
            int owner=-1;
            for(int who : {i,j}) {
                const double other=.5*(who==i?length[j]:length[i]);
                const double radius=.5*length[who]+other*sum;
                for(int direction=0;direction<2;++direction) {
                    const double nx=direction?-ss[who]:cs[who];
                    const double ny=direction?cs[who]:ss[who];
                    const double z=dx*nx+dy*ny;
                    const double gap=std::abs(z)-radius;
                    if(gap>best) { best=gap;normal_x=nx;normal_y=ny;owner=who;projection=z;other_half=other; }
                }
            }
            if(best>=0) continue;
            const double gp=2*weight*best;
            const double fx=sign(projection)*normal_x, fy=sign(projection)*normal_y;
            const double turn=sign(projection)*(dy*normal_x-dx*normal_y);
            const double ds=other_half*(-sign(c)*s+sign(s)*c);
            objective+=weight*best*best;
            g[3*i]-=gp*fx;g[3*i+1]-=gp*fy;
            g[3*j]+=gp*fx;g[3*j+1]+=gp*fy;
            g[3*i+2]+=gp*(ds+(owner==i?turn:0));
            g[3*j+2]+=gp*(-ds+(owner==j?turn:0));
        }
    }
    return objective;
}
}

extern "C" double ghost_energy(const double* pos, double* g, int n,
                               const double* sides, double weight) {
    return energy(pos,g,n,sides,weight);
}

extern "C" void relax_ghosts(double* pos, int n, const double* sides, double weight, int budget) {
    constexpr int history=6;
    const int dim=3*n+1;
    Vector x{},g{},step{},trial{},g1{};
    std::copy(pos,pos+dim,x.begin());
    double f=energy(x.data(),g.data(),n,sides,weight);
    Vector dx[history],dg[history];
    double inv[history]{},alpha[history]{};
    int head=0, size=0;
    for(int iter=0;iter<budget;++iter) {
        step=g;
        for(int h=0;h<size;++h) {
            const int k=(head-1-h+history)%history;
            alpha[k]=inv[k]*dot(dx[k],step,dim);
            for(int j=0;j<dim;++j) step[j]-=alpha[k]*dg[k][j];
        }
        double scale=.5/weight;
        if(size) {int k=(head-1+history)%history;scale=1/(inv[k]*dot(dg[k],dg[k],dim));}
        for(int j=0;j<dim;++j) step[j]*=scale;
        for(int h=size;h>0;--h) {
            const int k=(head-h+history)%history;
            const double b=alpha[k]-inv[k]*dot(dg[k],step,dim);
            for(int j=0;j<dim;++j) step[j]+=b*dx[k][j];
        }
        const double descent=dot(step,g,dim);
        if(!(descent>1e-19)) break;
        double t=1, f1=f;
        int line=0;
        for(;line<23;++line,t*=.5) {
            for(int j=0;j<dim;++j) trial[j]=x[j]-t*step[j];
            f1=energy(trial.data(),g1.data(),n,sides,weight);
            if(f1<=f-1e-4*t*descent)break;
        }
        if(line==23) {
            if(size) {size=0;head=0;continue;}
            break;
        }
        if(f-f1<5e-15*(1+std::abs(f))) break;
        Vector s{},y{};
        for(int j=0;j<dim;++j) {s[j]=trial[j]-x[j];y[j]=g1[j]-g[j];}
        double sy=dot(s,y,dim);
        if(sy>1e-14*std::sqrt(dot(s,s,dim)*dot(y,y,dim))) {
            dx[head]=s;dg[head]=y;inv[head]=1/sy;
            head=(head+1)%history;size=std::min(size+1,history);
        }
        x=trial;g=g1;f=f1;
    }
    std::copy(x.begin(),x.begin()+dim,pos);
}
