// The first 18 marks are proposed distinct owners. The last 3 are holes.
thread_local std::array<double, 108> box;
thread_local double box_penalty=0;
struct MarkTerm {double value,x,y,angle,side;};
thread_local std::array<Axis,21> assigned;
thread_local double owner_strength=0, margin=0, nearest_strength=0;
MarkTerm mark_distance(const Vec& x, int i, int mark, double c, double s) {
    Axis m=assigned[mark];
    const double dx=m.x*x[d-1]-x[3*i], dy=m.y*x[d-1]-x[3*i+1];
    const double p=c*dx+s*dy,q=-s*dx+c*dy;
    const bool main=std::abs(p)>=std::abs(q);
    const double ax=main?c:-s, ay=main?s:c;
    const double sg=sign(main?p:q);
    return {std::abs(main?p:q),-sg*ax,-sg*ay,sg*(main?q:-p),sg*(ax*m.x+ay*m.y)};
}
void accumulate(Vec& g, int i, const MarkTerm& q, double w) {
    g[3*i]+=w*q.x; g[3*i+1]+=w*q.y; g[3*i+2]+=w*q.angle; g[d-1]+=w*q.side;
}

void apply_fields(const Vec& x, double weight, Vec& grad, double& cost) {
    if(box_penalty>0) for(int i=0;i<54;i++) {
        const double lo=box[2*i],hi=box[2*i+1],mid=.5*(lo+hi);
        const double val=i%3==2?mid+std::remainder(x[i]-mid,1.570796326794896619):x[i];
        const double residual=val<lo?val-lo:(val>hi?val-hi:0.);
        cost+=weight*box_penalty*residual*residual;
        grad[i]+=2*weight*box_penalty*residual;
    }
    if(owner_strength>0 || nearest_strength>0) for(int i=0;i<n;i++) {
        const double c=std::cos(x[3*i+2]), s=std::sin(x[3*i+2]);
        MarkTerm home=mark_distance(x,i,i,c,s);
        double z=home.value-.5+margin;
        if(z>0 && owner_strength>0){
            cost+=weight*owner_strength*z*z;
            accumulate(grad,i,home,2*weight*owner_strength*z);
        }
        if(nearest_strength>0) for(int h=n;h<21;h++){
            MarkTerm away=mark_distance(x,i,h,c,s);
            z=home.value-away.value+margin;
            if(z>0) {
                cost+=weight*nearest_strength*z*z;
                const double coeff=2*weight*nearest_strength*z;
                accumulate(grad,i,home,coeff);accumulate(grad,i,away,-coeff);
            }
        }
    }
}
