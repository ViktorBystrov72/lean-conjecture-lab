// For each middle band retain the four signed endpoint directions at both ends.
struct EndpointSupports {
  vector<Pt> n;
  vector<vector<int>> ids;
  vector<vector<I>> own, other;

  EndpointSupports(const vector<Band>& bands) : ids(bands.size()) {
    map<Pt,int> index;
    for(size_t k=0;k<bands.size();++k) {
      for(auto endpoint : {bands[k].lo,bands[k].hi}) {
        for(auto axis : axes(endpoint)) {
          Pt v=unit_normal(axis);
          auto [it,fresh]=index.emplace(v,int(index.size()));
          if(fresh)n.push_back(v);
          ids[k].push_back(it->second);
        }
      }
    }
    own.assign(bands.size(),vector<I>(n.size()));
    other=own;
    for(size_t l=0;l<bands.size();++l) for(size_t id=0;id<n.size();++id) {
      Pt v=n[id];const auto &r=bands[l];
      auto along=[&](Dir q){return llabs(v.x*q.a+v.y*q.b);};
      auto across=[&](Dir q){return llabs(v.y*q.a-v.x*q.b);};
      own[l][id]=down((W)D*max(along(r.mid),across(r.mid)),2*r.mid.q);
      auto support=[&](Dir q){return down((W)D*(along(q)+across(q)),2*q.q);};
      other[l][id]=min(support(r.lo),support(r.hi));
    }
  }
};

vector<vector<vector<HP>>> endpoint_forbidden(const EndpointSupports& e,
    const vector<vector<Poly>>& c,const vector<int>& owners) {
  const int B=int(e.ids.size()),nn=int(e.n.size());
  const W inf=(W)1<<100;
  vector<vector<vector<HP>>> result(21,vector<vector<HP>>(B));
  for(int j:owners) {
    vector<vector<W>> lowCentre(B,vector<W>(nn));
    for(int l=0;l<B;++l) if(!c[j][l].empty()) {
      for(int id=0;id<nn;++id)lowCentre[l][id]=low(c[j][l],e.n[id]);
    }
    for(int k=0;k<B;++k) {
      vector<W> rhs(nn,inf);
      for(int l=0;l<B;++l) if(!c[j][l].empty()) {
        for(int id:e.ids[k]) {
          I h=e.own[k][id]+(k==l?e.own[k][id]:e.other[l][id]);
          rhs[id]=min(rhs[id],lowCentre[l][id]+h);
        }
        for(int id:e.ids[l]) {
          I h=e.own[l][id]+(k==l?e.own[l][id]:e.other[k][id]);
          rhs[id]=min(rhs[id],lowCentre[l][id]+h);
        }
      }
      for(int id=0;id<nn;++id)if(rhs[id]!=inf)result[j][k].push_back({e.n[id].x,e.n[id].y,rhs[id]});
    }
  }
  return result;
}
