// Independent continuous-centre relaxation for occupied-mark cases of the
// 18-square problem. Coordinates use 10^-9 units. Floating point only proposes
// new hull vertices.
#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <string>
#include <vector>
#include <string_view>
#include <utility>
using namespace std;
using I = int64_t;
using W = __int128_t;
constexpr I D = 1000000000LL, U = 4822876000LL;
struct Pt {
  I x, y;
  bool operator<(const Pt &q) const { return x == q.x ? y < q.y : x < q.x; }
  bool operator==(const Pt &q) const { return x == q.x && y == q.y; }
};
using Poly = vector<Pt>;
struct HP {
  I x, y;
  W k;
};
struct Dir {
  I a, b, q;
};

W wide(I a, I b, Pt p) { return (W)a * p.x + (W)b * p.y; }
W area(Pt a, Pt b, Pt c) {
  return (W)(b.x - a.x) * (c.y - a.y) - (W)(b.y - a.y) * (c.x - a.x);
}
Poly hull(Poly p) {
  sort(p.begin(), p.end());
  p.erase(unique(p.begin(), p.end()), p.end());
  if (p.size() < 3)
    return p;
  Poly a, b;
  for (auto x : p) {
    while (a.size() >= 2 && area(a[a.size() - 2], a.back(), x) <= 0)
      a.pop_back();
    a.push_back(x);
  }
  reverse(p.begin(), p.end());
  for (auto x : p) {
    while (b.size() >= 2 && area(b[b.size() - 2], b.back(), x) <= 0)
      b.pop_back();
    b.push_back(x);
  }
  a.pop_back();
  b.pop_back();
  a.insert(a.end(), b.begin(), b.end());
  return a;
}
Dir direction(I a, I b) { return {b * b - a * a, 2 * a * b, b * b + a * a}; }
vector<Pt> marks() {
  vector<Pt> a;
  for (auto [x, y] : vector<Pt>{
           {390, 390}, {617, 617}, {797, 359}, {1000, 716}, {1000, 1000}}) {
    for (int s = 0; s < 4; s++) {
      a.push_back({x * (U / 2000), y * (U / 2000)});
      a.push_back({y * (U / 2000), x * (U / 2000)});
      I z = x;
      x = 2000 - y;
      y = z;
    }
  }
  sort(a.begin(), a.end());
  a.erase(unique(a.begin(), a.end()), a.end());
  return a;
}
bool in(Pt g, const vector<HP> &h) {
  for (auto v : h)
    if (wide(v.x, v.y, g) > v.k)
      return false;
  return true;
}
struct DD {
  double x, y;
};
Poly inner_points(const vector<HP> &hp) {
  vector<DD> p = {
      {0, 0}, {(double)U, 0}, {(double)U, (double)U}, {0, (double)U}};
  for (auto v : hp) {
    if (p.empty())
      return {};
    vector<DD> out;
    auto eval = [&](DD g) {
      return (double)v.x * g.x + (double)v.y * g.y - (double)v.k;
    };
    DD prev = p.back();
    double a = eval(prev);
    for (auto x : p) {
      double b = eval(x);
      if ((a < 0 && b > 0) || (a > 0 && b < 0)) {
        double t = a / (a - b);
        out.push_back(
            {prev.x + t * (x.x - prev.x), prev.y + t * (x.y - prev.y)});
      }
      if (b <= 0)
        out.push_back(x);
      a = b;
      prev = x;
    }
    p = std::move(out);
  }
  if (p.empty())
    return {};
  DD c{};
  for (auto x : p) {
    c.x += x.x;
    c.y += x.y;
  }
  c.x /= p.size();
  c.y /= p.size();
  Poly good;
  for (auto v : p) {
    for (double e : {0., 1e-8, 1e-6, 1e-4, .01, .1, 1.}) {
      DD f{v.x + (c.x - v.x) * e, v.y + (c.y - v.y) * e};
      if (!isfinite(f.x) || !isfinite(f.y) || f.x < -5 || f.y < -5 ||
          f.x > U + 5 || f.y > U + 5)
        continue;
      Pt q{llround(f.x), llround(f.y)};
      if (q.x >= 0 && q.x <= U && q.y >= 0 && q.y <= U && in(q, hp)) {
        good.push_back(q);
        break;
      }
    }
  }
  return good;
}
struct Band {
  Dir mid, lo, hi;
  Poly core;
  vector<Pt> normal;
  vector<int> ids;
  I wall, outer_dot;
};
I down(W n, W d) {
  if (d < 0) {
    n = -n;
    d = -d;
  }
  return (I)(n / d - (n < 0 && n % d != 0));
}
I up(W n, W d) { return -down(-n, d); }
W low(const Poly &p, Pt n) {
  W w = wide(n.x, n.y, p[0]);
  for (auto z : p)
    w = min(w, wide(n.x, n.y, z));
  return w;
}
W high(const Poly &p, Pt n) {
  W w = wide(n.x, n.y, p[0]);
  for (auto z : p)
    w = max(w, wide(n.x, n.y, z));
  return w;
}
Poly clip_grid(const Poly &p, HP hp) {
  if (p.empty())
    return {};
  Poly z;
  Pt prev = p.back();
  W fp = wide(hp.x, hp.y, prev) - hp.k;
  for (auto next : p) {
    W fn = wide(hp.x, hp.y, next) - hp.k;
    if ((fp < 0 && fn > 0) || (fp > 0 && fn < 0)) {
      W den = fp - fn;
      W nx = (W)prev.x * den + fp * (next.x - prev.x),
        ny = (W)prev.y * den + fp * (next.y - prev.y);
      I x = down(nx, den), X = up(nx, den), y = down(ny, den), Y = up(ny, den);
      for (auto u : {x, X})
        for (auto v : {y, Y})
          z.push_back({u, v});
    }
    if (fn <= 0)
      z.push_back(next);
    prev = next;
    fp = fn;
  }
  return hull(z);
}
Poly minus_region(const Poly &p, const vector<HP> &forbidden) {
  if (p.empty() || forbidden.empty())
    return p;
  vector<HP> active;
  for (auto n : forbidden) {
    auto v = Pt{n.x, n.y};
    if (low(p, v) >= n.k)
      return p;
    if (high(p, v) >= n.k)
      active.push_back(n);
  }
  if (active.empty())
    return {};
  Poly all;
  for (auto n : active) {
    Poly out = clip_grid(p, {-n.x, -n.y, -n.k});
    all.insert(all.end(), out.begin(), out.end());
  }
  return hull(all);
}
Pt unit_normal(Pt a) {
  I s = std::gcd(llabs(a.x), llabs(a.y));
  return {a.x / s, a.y / s};
}
vector<Pt> normals_of(const Poly &p) {
  vector<Pt> ns;
  if (p.size() < 2)
    return ns;
  for (size_t j = 0; j < p.size(); j++) {
    auto a = p[j], b = p[(j + 1) % p.size()];
    ns.push_back(unit_normal({b.y - a.y, a.x - b.x}));
  }
  return ns;
}
vector<Pt> axes(Dir x) {
  return {{x.a, x.b}, {-x.b, x.a}, {-x.a, -x.b}, {x.b, -x.a}};
}
Band band(int k, int B) {
  Dir m = direction(2 * k + 1, 2 * B), lo = direction(k, B),
      hi = direction(k + 1, B);
  W gn = 0, gd = 1;
  for (auto a : {lo, hi}) {
    I n = llabs(a.a * m.a + a.b * m.b) + llabs(a.b * m.a - a.a * m.b),
      d = a.q * m.q;
    if ((W)n * gd > gn * d) {
      gn = n;
      gd = d;
    }
  }
  I h = down((D / 2 - 16) * gd, gn), R = D / 2 - 16;
  Poly core;
  for (auto A : {-1, 1})
    for (auto b : {-1, 1})
      core.push_back({down((W)h * (A * m.a - b * m.b), m.q),
                      down((W)h * (A * m.b + b * m.a), m.q)});
  // Coordinate floors move a vertex by less than sqrt(2) lattice units.
  // The 16-unit margin covers this. Add its negative for central symmetry.
  for (auto n : axes(m))
    core.push_back({down((W)R * n.x, m.q), down((W)R * n.y, m.q)});
  Poly cp = core;
  for (auto v : cp)
    core.push_back({-v.x, -v.y});
  core = hull(core);
  auto p = lo;
  if ((hi.a + hi.b) * lo.q < (lo.a + lo.b) * hi.q)
    p = hi;
  I wall = down((W)D * (p.a + p.b), 2 * p.q);
  return {m,
          lo,
          hi,
          core,
          normals_of(core),
          {},
          wall,
          up((W)(D / 2) * m.q * gn, gd)};
}
Poly initial(const Band &r, const vector<Pt> &M, int j, const Poly &seed,
             I inset) {
  I e = r.wall + inset;
  Poly p = {{e, e}, {U - e, e}, {U - e, U - e}, {e, U - e}};
  for (auto n : axes(r.mid))
    p = clip_grid(p, {n.x, n.y, low(seed, n) + r.outer_dot});
  // At every theta, the assigned mark must minimize max absolute axis
  // projection. Forbid uniformly strict comparisons witnessed by one owner
  // face, tested at both endpoints.
  for (int jj = 0; jj < (int)M.size() && !p.empty(); jj++) {
    if (j == jj)
      continue;
    auto z = M[jj], m = M[j];
    if (llabs(z.x - m.x) > 2 * D || llabs(z.y - m.y) > 2 * D)
      continue;
    for (int f = 0; f < 4 && !p.empty(); f++) {
      vector<HP> fs;
      bool skip = false;
      for (auto endpoint : {r.lo, r.hi}) {
        auto dirs = axes(endpoint);
        auto o = dirs[f];
        for (auto a : dirs) {
          Pt n{o.x - a.x, o.y - a.y};
          W h = wide(o.x, o.y, m) - wide(a.x, a.y, z);
          if (n.x == 0 && n.y == 0) {
            if (h <= 0)
              skip = true;
            continue;
          }
          fs.push_back({n.x, n.y, h});
        }
      }
      if (!skip)
        p = minus_region(p, fs);
    }
  }
  return p;
}
struct Box {
  I x0, x1, y0, y1;
  int depth;
};
int check_rack(int B) {
  if (B < 128 || B > 1024)
    return 2;
  auto pts = marks();
  if (pts.size() != 21)
    return 3;
  long long tested = 0, covered = 0;
  int maxDepth = 0;
  for (int k = 0; k < B; k++) {
    auto r = band(k, B);
    auto u = r.mid;
    I inHalf = down((W)(D - D / 100000) * B, 2 * (B + 1)) - 1;
    vector<Box> work = {{r.wall, U - r.wall, r.wall, U - r.wall, 0}};
    while (!work.empty()) {
      auto b = work.back();
      work.pop_back();
      tested++;
      maxDepth = max(maxDepth, b.depth);
      bool hit = false;
      for (auto m : pts) {
        bool inside = true;
        for (auto x : {b.x0, b.x1})
          for (auto y : {b.y0, b.y1}) {
            I p = x - m.x, q = y - m.y;
            if (max(llabs(p * u.a + q * u.b), llabs(q * u.a - p * u.b)) >
                inHalf * u.q)
              inside = false;
          }
        if (inside) {
          hit = true;
          break;
        }
      }
      if (hit) {
        covered++;
        continue;
      }
      if (b.depth >= 45) {
        cout << "INCONCLUSIVE rack at angle " << k << " depth " << b.depth
             << endl;
        return 2;
      }
      if (b.x1 - b.x0 >= b.y1 - b.y0) {
        auto m = (b.x0 + b.x1) / 2;
        work.push_back({b.x0, m, b.y0, b.y1, b.depth + 1});
        work.push_back({m, b.x1, b.y0, b.y1, b.depth + 1});
      } else {
        auto m = (b.y0 + b.y1) / 2;
        work.push_back({b.x0, b.x1, b.y0, m, b.depth + 1});
        work.push_back({b.x0, b.x1, m, b.y1, b.depth + 1});
      }
    }
  }
  cout << "RACK COVERED " << covered << " leaves " << tested
       << " nodes, max depth " << maxDepth << endl;
  return 0;
}

bool parse(const char *input, int base, I &v) {
  std::string_view s(input);
  auto parsed = std::from_chars(s.begin(), s.end(), v, base);
  return !s.empty() && parsed.ec == std::errc{} && parsed.ptr == s.end();
}
int main(int argc, char **argv) {
  std::vector<std::pair<int, HP>> cuts;
  I inset = 0;
  while (argc > 1) {
    std::string option = argv[1];
    if (option == "--side") {
      I side;
      if (argc < 3 || !parse(argv[2], 10, side) || side < D || side > U ||
          (U - side) % 2)
        return 2;
      inset = (U - side) / 2;
      argc -= 2;
      argv += 2;
    } else if (option == "--cut") {
      I i, value;
      if (argc < 5 || !parse(argv[2], 10, i) || i < 0 || i >= 21 ||
          !parse(argv[4], 10, value) || value < 0 || value > U)
        return 2;
      std::string cmp = argv[3];
      HP hp{0, 0, value};
      if (cmp == "x-le")
        hp.x = 1;
      else if (cmp == "y-le")
        hp.y = 1;
      else if (cmp == "x-ge") {
        hp.x = -1;
        hp.k = -value;
      } else if (cmp == "y-ge") {
        hp.y = -1;
        hp.k = -value;
      } else
        return 2;
      cuts.emplace_back((int)i, hp);
      argc -= 4;
      argv += 4;
    } else
      break;
  }
  if (argc == 3 && string(argv[1]) == "--rack") {
    I b;
    if (!parse(argv[2], 10, b) || b < 128 || b > 1024)
      return 2;
    return check_rack(int(b));
  }
  if (argc < 3 || argc > 5)
    return 1;
  I rawMask, b, r = 90;
  if (!parse(argv[1], 16, rawMask) || rawMask < 0 || rawMask >= (1 << 21) ||
      !parse(argv[2], 10, b) || b < 4 || b > 128 ||
      (argc > 3 && !parse(argv[3], 10, r)) || r < 1 || r > 256)
    return 2;
  unsigned mask = unsigned(rawMask);
  int B = int(b), maxr = int(r);
  if (__builtin_popcount(mask) != 18)
    return 2;
  for (auto &cut : cuts)
    if (!(mask >> cut.first & 1))
      return 2;
  auto M = marks();
  vector<int> own;
  for (int i = 0; i < 21; i++)
    if (mask >> i & 1)
      own.push_back(i);
  vector<Band> bins;
  vector<Pt> nn;
  map<Pt, int> idx;
  for (int k = 0; k < B; k++) {
    bins.push_back(band(k, B));
    auto &b = bins.back();
    for (auto n : b.normal) {
      auto [it, added] = idx.emplace(n, idx.size());
      if (added)
        nn.push_back(n);
      b.ids.push_back(it->second);
    }
  }
  int nN = nn.size();
  vector<vector<W>> sup(B, vector<W>(nN));
  for (int k = 0; k < B; k++)
    for (int d = 0; d < nN; d++)
      sup[k][d] = high(bins[k].core, nn[d]);
  // H[j] is known to lie strictly in tile j. In contrast, c[j][k]
  // encloses all possible centres of tile j in angle band k.
  vector<Poly> H(21);
  vector<vector<Poly>> c(21, vector<Poly>(B));
  for (int j : own) {
    auto z = M[j];
    I rad = D / 1000000;
    H[j] = hull({{z.x + rad, z.y},
                 {z.x - rad, z.y},
                 {z.x, z.y + rad},
                 {z.x, z.y - rad}});
    for (int k = 0; k < B; k++)
      c[j][k] = initial(bins[k], M, j, H[j], inset);
  }
  for (const auto &cut : cuts)
    for (auto &domain : c[cut.first])
      domain = clip_grid(domain, cut.second);
  W inf = (W)1 << 100;
  for (int r = 0; r < maxr; r++) {
    // F[j][k] is a forbidden region for a candidate in band k. A
    // point in its interior intersects a partner core for every live
    // band and centre of tile j. Integer dot products decide all cuts.
    vector<vector<vector<HP>>> F(21, vector<vector<HP>>(B));
    for (int j : own) {
      // S takes the lower support across all live partner bands.
      // T takes it only over bands where that direction is a facet.
      vector<W> S(nN, inf), T(nN, inf);
      for (int l = 0; l < B; l++) {
        auto &p = c[j][l];
        if (p.empty())
          continue;
        vector<W> step(nN);
        for (int z = 0; z < nN; z++) {
          step[z] = low(p, nn[z]) + sup[l][z];
          S[z] = min(S[z], step[z]);
        }
        for (int z : bins[l].ids)
          T[z] = min(T[z], step[z]);
      }
      for (int k = 0; k < B; k++) {
        auto R = T;
        for (int id : bins[k].ids)
          R[id] = S[id];
        for (int z = 0; z < nN; z++)
          if (R[z] != inf)
            F[j][k].push_back({nn[z].x, nn[z].y, R[z] + sup[k][z]});
      }
    }
    bool change = false;
    long long vertices = 0;
    int alive = 0;
    auto nextH = H;
    for (int j : own) {
      vector<HP> common;
      for (int k = 0; k < B; k++) {
        auto &p = c[j][k];
        if (p.empty())
          continue;
        auto old = p;
        auto &row = bins[k];
        for (auto n : axes(row.mid)) {
          HP z{n.x, n.y, low(H[j], n) + row.outer_dot};
          if (high(p, n) > z.k)
            p = clip_grid(p, z);
          if (p.empty())
            break;
        }
        for (int jj : own)
          if (jj != j && !p.empty() && llabs(M[j].x - M[jj].x) < 3 * D &&
              llabs(M[j].y - M[jj].y) < 3 * D) {
            vector<HP> G;
            auto hN = normals_of(H[jj]);
            for (int a : row.ids)
              G.push_back({nn[a].x, nn[a].y, high(H[jj], nn[a]) + sup[k][a]});
            for (auto n : hN)
              G.push_back({n.x, n.y, high(H[jj], n) + high(row.core, n)});
            p = minus_region(p, G);
            if (!p.empty())
              p = minus_region(p, F[jj][k]);
          }
        if (p != old)
          change = true;
        if (p.empty())
          continue;
        for (int id : row.ids) {
          auto n = nn[id];
          common.push_back({n.x, n.y, low(p, n) + sup[k][id]});
        }
        vertices += p.size();
        alive++;
      }
      if (common.empty()) {
        cout << "EXCLUDED empty owner " << j << " round " << r << endl;
        return 0;
      }
      auto added = inner_points(common);
      for (auto z : added)
        nextH[j].push_back(z);
      nextH[j] = hull(nextH[j]);
      if (nextH[j] != H[j])
        change = true;
    }
    H = std::move(nextH);
    cout << r << " alive " << alive << " vertices " << vertices << endl;
    for (int i : own)
      for (int j : own)
        if (i < j) {
          if (H[i].size() < 3 || H[j].size() < 3)
            continue;
          bool sep = false;
          for (auto ph : {&H[i], &H[j]}) {
            auto &other = ph == &H[i] ? H[j] : H[i];
            for (auto n : normals_of(*ph))
              if (low(other, n) > high(*ph, n)) {
                sep = true;
                break;
              }
            if (sep)
              break;
          }
          if (!sep) {
            cout << "EXCLUDED guaranteed overlap " << i << " " << j << " round "
                 << r << endl;
            return 0;
          }
        }
    if (!change) {
      cout << "INCONCLUSIVE fixed point" << endl;
      return 0;
    }
  }
  if (argc == 5) {
    std::ofstream out(argv[4]);
    if (!out)
      return 2;
    for (int i : own)
      for (int k = 0; k < B; k++) {
        out << i << " " << k << " " << c[i][k].size();
        for (auto p : c[i][k])
          out << " " << p.x << " " << p.y;
        out << "\n";
      }
  }
  cout << "INCONCLUSIVE budget" << endl;
}
