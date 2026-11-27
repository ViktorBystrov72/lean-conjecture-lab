extern "C" {
void set_leaf(const double* b, double strength) {
    std::copy(b,b+108,box.begin()); box_penalty=strength;
}
void set_rack(const double* ordered_marks,double w,double nearest,double inset) {
    for(int i=0;i<21;i++) assigned[i]={ordered_marks[2*i],ordered_marks[2*i+1]};
    owner_strength=w;nearest_strength=nearest;margin=inset;
}
}
