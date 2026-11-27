// Independent interval proof of the continuous mark covering.
// Interval products bound the two varying entries of the orientation separately.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <set>
#include <utility>
#include <vector>
using Z=std::int64_t;
using Big=__int128_t;
constexpr Z scale=1'000'000'000, side=4'822'876'000;
struct Rectangle{Z xl,xh,yl,yh;int depth;};
using Point=std::pair<Z,Z>;
int main(int argc,char** argv){
    if(argc!=2)return 2;
    int B=std::atoi(argv[1]);if(B<50||B>700)return 2;
    std::set<Point> marks;
    std::array<Point,5> start={Point{390,390},{617,617},{797,359},{1000,716},{1000,1000}};
    for(auto [a,b]:start) for(int swap=0;swap<2;swap++) {
        Z x=swap?b:a,y=swap?a:b;
        for(auto X:{x,2000-x}) for(auto Y:{y,2000-y}) marks.insert({X*(side/2000),Y*(side/2000)});
    }
    if(marks.size()!=21||side%2000!=0)return 2;
    Z nodes=0,leaves=0,depth=0;
    for(Z k=0;k<B;k++) {
        Z b=B;
        Z q0=b*b+k*k,q1=b*b+(k+1)*(k+1),den=q0*q1;
        // cos decreases and sin increases on the first quadrant.
        Z cmin=(b*b-(k+1)*(k+1))*q0,cmax=(b*b-k*k)*q1;
        Z smin=2*b*k*q1,smax=2*b*(k+1)*q0;
        Z wall=(Big(scale)*(cmin+smin))/(2*Big(den));
        std::vector<Rectangle> pending={{wall,side-wall,wall,side-wall,0}};
        Big half=Big(scale-scale/100000)*den;
        while(!pending.empty()) {
            Rectangle r=pending.back();pending.pop_back();nodes++;depth=std::max(depth,Z(r.depth));
            bool covered=false;
            for(auto [x,y]:marks) {
                Z xl=x-r.xh,xh=x-r.xl,yl=y-r.yh,yh=y-r.yl;
                auto lo=[](Z v,Z l,Z h)->Big{return Big(v)*(v<0?h:l);};
                auto hi=[](Z v,Z l,Z h)->Big{return Big(v)*(v>0?h:l);};
                Big uMin=lo(xl,cmin,cmax)+lo(yl,smin,smax);
                Big uMax=hi(xh,cmin,cmax)+hi(yh,smin,smax);
                Big vMin=lo(-xh,smin,smax)+lo(yl,cmin,cmax);
                Big vMax=hi(-xl,smin,smax)+hi(yh,cmin,cmax);
                if(-half<2*uMin&&2*uMax<half&&-half<2*vMin&&2*vMax<half){covered=true;break;}
            }
            if(covered){leaves++;continue;}
            if(r.depth>=52){std::cout<<"UNRESOLVED "<<k<<" "<<r.xl<<" "<<r.yl<<"\n";return 1;}
            if(r.xh-r.xl>=r.yh-r.yl){
                Z m=(r.xl+r.xh)/2;
                pending.push_back({r.xl,m,r.yl,r.yh,r.depth+1});pending.push_back({m,r.xh,r.yl,r.yh,r.depth+1});
            }else{
                Z m=(r.yl+r.yh)/2;
                pending.push_back({r.xl,r.xh,r.yl,m,r.depth+1});pending.push_back({r.xl,r.xh,m,r.yh,r.depth+1});
            }
        }
    }
    std::cout<<"Strict rack covering for all real centres and angles. "<<B<<" angular slabs, "<<nodes<<" nodes, "<<leaves<<" leaves, max depth "<<depth<<"\n";
}
