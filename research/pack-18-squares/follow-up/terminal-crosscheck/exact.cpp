// Independent integer outer-hull propagation for prescribed rack masks.
// Units are 1/D. Centre polygons are rounded OUT at every edge crossing.
// All candidate guaranteed tile points are checked exactly before use.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
using I = int64_t;
using W = __int128_t;
constexpr I D = 500000000, U = 2411438000;
I narrow(W v) {
    if (v < -W(6900000000000000000LL) || v > W(6900000000000000000LL))
        std::abort();
    return I(v);
}
W mul(W a, W b) {
    W c = 0;
    if (__builtin_mul_overflow(a, b, &c))
        std::abort();
    return c;
}
I floorq(W a, W b) {
    if (b <= 0)
        std::abort();
    return narrow(a / b - (a < 0 && a % b));
}
I ceilq(W a, W b) { return -floorq(-a, b); }
struct P {
    I x, y;
    bool operator<(P b) const { return std::tie(x, y) < std::tie(b.x, b.y); }
    bool operator==(P b) const { return x == b.x && y == b.y; }
};
using Poly = std::vector<P>;
struct N {
    I x, y, d;
};
struct H {
    I a, b, k;
};
I dot(I a, I b, P p) { return narrow(W(a) * p.x + W(b) * p.y); }
I dot(N n, P p) { return dot(n.x, n.y, p); }
W value(H h, P p) { return W(dot(h.a, h.b, p)) - h.k; }
W cross(P a, P b, P c) { return W(b.x - a.x) * (c.y - a.y) - W(b.y - a.y) * (c.x - a.x); }
Poly hull(Poly v) {
    if (v.size() > 100000) {
        std::cerr << "polygon resource limit" << std::endl;
        std::abort();
    }
    std::sort(v.begin(), v.end());
    v.erase(std::unique(v.begin(), v.end()), v.end());
    if (v.size() <= 2)
        return v;
    Poly h(2 * v.size());
    int k = 0;
    for (auto p : v) {
        while (k >= 2 && cross(h[k - 2], h[k - 1], p) <= 0)
            --k;
        h[k++] = p;
    }
    int lo = k + 1;
    for (int i = int(v.size()) - 2; i >= 0; --i) {
        auto p = v[i];
        while (k >= lo && cross(h[k - 2], h[k - 1], p) <= 0)
            --k;
        h[k++] = p;
    }
    h.resize(k - 1);
    return h;
}
void around(Poly &q, P a, P b, W num, W den) {
    if (num < 0 || num > den || den <= 0)
        std::abort();
    W x = W(a.x) * den + num * (b.x - a.x), y = W(a.y) * den + num * (b.y - a.y);
    I xl = floorq(x, den), yl = floorq(y, den), xh = ceilq(x, den), yh = ceilq(y, den);
    q.push_back({xl, yl});
    q.push_back({xl, yh});
    q.push_back({xh, yl});
    q.push_back({xh, yh});
}
// Intersect an outer polygon with one closed halfplane, rounding crossing
// coordinates out to the enclosing grid cell before taking a convex hull.
void half(Poly &p, H h) {
    if (p.empty())
        return;
    Poly q;
    auto a = p.back();
    auto s = value(h, a);
    bool all = true;
    for (auto b : p) {
        auto t = value(h, b);
        if (t >= 0)
            q.push_back(b);
        else
            all = false;
        if ((s > 0 && t < 0) || (t > 0 && s < 0)) {
            if (s < 0)
                around(q, a, b, -s, t - s);
            else
                around(q, b, a, -t, s - t);
        }
        a = b;
        s = t;
    }
    if (!all)
        p = hull(std::move(q));
}
// Keep an outer hull of P intersected with a UNION of closed halfplanes.
// On each mixed edge the first crossing out of the convex forbidden set
// is retained. An edge between retained vertices is covered by their hull.
void any(Poly &p, const std::vector<H> &hs) {
    if (p.empty())
        return;
    std::vector<bool> yes(p.size());
    unsigned n = 0;
    for (size_t i = 0; i < p.size(); ++i) {
        for (auto h : hs) {
            if (value(h, p[i]) >= 0) {
                yes[i] = true;
                break;
            }
        }
        n += yes[i];
    }
    if (n == p.size())
        return;
    if (!n) {
        p.clear();
        return;
    }
    Poly q;
    for (size_t i = 0; i < p.size(); ++i) {
        size_t j = (i + 1) % p.size();
        if (yes[i])
            q.push_back(p[i]);
        if (yes[i] == yes[j])
            continue;
        P a = yes[i] ? p[j] : p[i], b = yes[i] ? p[i] : p[j];
        W bestn = 1, bestd = 1;
        for (auto h : hs) {
            auto t = value(h, b);
            if (t < 0)
                continue;
            auto s = value(h, a);
            if (s >= 0)
                std::abort();
            W nu = -s, de = t - s;
            if (mul(nu, bestd) < mul(bestn, de)) {
                bestn = nu;
                bestd = de;
            }
        }
        around(q, a, b, bestn, bestd);
    }
    p = hull(std::move(q));
}
using Fr = std::array<N, 4>;
Fr frame(int a, int b) {
    I x = I(b) * b - I(a) * a, y = 2 * I(a) * b, d = I(a) * a + I(b) * b;
    I g = std::gcd(std::gcd(x, y), d);
    x /= g;
    y /= g;
    d /= g;
    return {N{x, y, d}, N{-y, x, d}, N{-x, -y, d}, N{y, -x, d}};
}
I minp(const Poly &p, N n) {
    if (p.empty())
        std::abort();
    I m = dot(n, p[0]);
    for (auto q : p)
        m = std::min(m, dot(n, q));
    return m;
}
I maxp(const Poly &p, N n) {
    N f{-n.x, -n.y, n.d};
    return -minp(p, f);
}
W proj(N n, N f) {
    W a = W(n.x) * f.x + W(n.y) * f.y, b = W(n.x) * f.y - W(n.y) * f.x;
    return (a >= 0 ? a : -a) + (b >= 0 ? b : -b);
}
// The point lists are untrusted suggestions. A false inner approximation
// could invalidate a proof, so every proposed vertex is tested against every
// proven halfplane before the contraction uses it.
struct CoreTrace {
    std::ifstream read;
    explicit CoreTrace(const std::string &path) : read(path) {
        if (!read)
            throw std::runtime_error("cannot open core certificate");
    }
    Poly points(int step, int owner, const std::vector<H> &halfplanes) {
        int r, id, count;
        if (!(read >> r >> id >> count) || r != step || id != owner || count < 0 || count > 2048)
            throw std::runtime_error("invalid core certificate record");
        Poly points;
        for (int k = 0; k < count; ++k) {
            P p;
            if (!(read >> p.x >> p.y) || p.x < 0 || p.x > U || p.y < 0 || p.y > U)
                throw std::runtime_error("invalid proposed grid point");
            for (auto h : halfplanes)
                if (value(h, p) < 0)
                    throw std::runtime_error("core point fails defining halfplane");
            points.push_back(p);
        }
        return points;
    }
    void finish() {
        std::string extra;
        if (read >> extra)
            throw std::runtime_error("unused certificate records");
    }
};
int run(int argc, char **argv) {
    if (argc != 4)
        return 2;
    CoreTrace trace(argv[3]);
    int cas = std::stoi(argv[1]), B = 128, rounds = std::stoi(argv[2]);
    if (rounds < 1 || rounds > 1000)
        return 2;
    int drop[3];
    if (cas == 93) {
        drop[0] = 2;
        drop[1] = 5;
        drop[2] = 14;
    } else if (cas == 56) {
        drop[0] = 0;
        drop[1] = 9;
        drop[2] = 16;
    } else if (cas == 53) {
        drop[0] = 4;
        drop[1] = 10;
        drop[2] = 16;
    } else
        return 2;
    int digits[21][2] = {
        {359, 797},   {359, 1203}, {390, 390},   {390, 1610},  {617, 617},   {617, 1383}, {716, 1000},
        {797, 359},   {797, 1641}, {1000, 716},  {1000, 1000}, {1000, 1284}, {1203, 359}, {1203, 1641},
        {1284, 1000}, {1383, 617}, {1383, 1383}, {1610, 390},  {1610, 1610}, {1641, 797}, {1641, 1203}};
    std::vector<P> marks, all;
    for (int i = 0; i < 21; ++i) {
        P p{digits[i][0] * (U / 2000), digits[i][1] * (U / 2000)};
        all.push_back(p);
        if (i != drop[0] && i != drop[1] && i != drop[2])
            marks.push_back(p);
    }
    if (U % 2000)
        std::abort();
    std::vector<Fr> mid, ends;
    for (int k = 0; k < B; ++k)
        mid.push_back(frame(2 * k + 1, 2 * B));
    for (int k = 0; k <= B; ++k)
        ends.push_back(frame(k, B));
    auto inner = [&](I d) { return floorq(W(d) * D * B, 2 * (B + 1)); };
    auto outer = [&](I d) { return ceilq(W(d) * D * (B + 1), 2 * B); };
    auto ownd = [&](I d) { return floorq(W(d) * D * (2 * I(B) * B - 1), 4 * I(B) * B); };
    auto self = [&](I d) { return floorq(W(d) * D * (2 * I(B) * B - 1), 2 * I(B) * B); };
    // Endpoint bounds for a separating axis; see the endpoint lemma in the note.
    std::vector<std::vector<I>> supp(B + 1, std::vector<I>(B));
    for (int k = 0; k <= B; ++k)
        for (int l = 0; l < B; ++l) {
            N n = ends[k][0], a = ends[l][0], b = ends[l + 1][0];
            supp[k][l] = ownd(n.d) + std::min(floorq(W(D) * proj(n, a), 2 * a.d),
                                              floorq(W(D) * proj(n, b), 2 * b.d));
        }
    std::vector<std::vector<Poly>> state(18, std::vector<Poly>(B));
    for (int i = 0; i < 18; ++i)
        for (int k = 0; k < B; ++k) {
            auto &p = state[i][k];
            I w = std::min(floorq(W(D) * (ends[k][0].x + ends[k][0].y), 2 * ends[k][0].d),
                           floorq(W(D) * (ends[k + 1][0].x + ends[k + 1][0].y), 2 * ends[k + 1][0].d));
            p = {{w, w}, {U - w, w}, {U - w, U - w}, {w, U - w}};
            for (auto n : mid[k])
                half(p, {n.x, n.y, dot(n, marks[i]) - outer(n.d)});
        }
    std::vector<Poly> cores;
    for (auto p : marks)
        cores.push_back({p});
    std::array<int, 18> watch{};
    std::ofstream observer;
    if (const char *file = std::getenv("RACK_CONTROL_BANDS")) {
        std::ifstream bands(file);
        for (auto &b : watch)
            if (!(bands >> b) || b < 0 || b >= B)
                throw std::runtime_error("invalid control band");
        const char *path = std::getenv("RACK_CONTROL_TRACE");
        if (!path)
            throw std::runtime_error("missing control output");
        observer.open(path);
        if (!observer)
            throw std::runtime_error("bad control output");
    }
    auto emitWatch = [&](int step, int j) {
        if (!observer.is_open())
            return;
        for (int i = 0; i < 18; i++) {
            const Poly &q = state[i][watch[i]];
            observer << step << " " << j << " " << i << " " << watch[i] << " " << q.size();
            for (auto p : q)
                observer << " " << p.x << " " << p.y;
            observer << " " << cores[i].size();
            for (auto p : cores[i])
                observer << " " << p.x << " " << p.y;
            observer << "\n";
        }
    };
    emitWatch(-1, -1);
    for (int step = 0; step < rounds; ++step) {
        for (int j = 0; j < 18; ++j) {
            // The owned mark must be nearest in the actual square frame.
            for (int k = 0; k < B; ++k) {
                auto &p = state[j][k];
                if (p.empty())
                    continue;
                for (auto y : all) {
                    auto x = marks[j];
                    if (y == x)
                        continue;
                    for (int z = 0; z < 4; ++z) {
                        std::vector<H> hs;
                        for (int e : {k, k + 1}) {
                            N b = ends[e][z];
                            for (auto a : ends[e])
                                hs.push_back({a.x - b.x, a.y - b.y, dot(a, y) - dot(b, x)});
                        }
                        any(p, hs);
                        if (p.empty())
                            break;
                    }
                    if (p.empty())
                        break;
                }
                if (!p.empty())
                    for (int i = 0; i < 18; ++i)
                        if (i != j) {
                            std::vector<H> hs;
                            for (auto n : mid[k])
                                hs.push_back({n.x, n.y, dot(n, marks[i]) + inner(n.d)});
                            any(p, hs);
                        }
            }
            std::vector<int> active;
            for (int l = 0; l < B; ++l)
                if (!state[j][l].empty())
                    active.push_back(l);
            if (active.empty()) {
                trace.finish();
                std::cout << "EXCLUDED case " << cas << " index " << j << " round " << step << " A\n";
                return 0;
            }
            // Points in all of these halfplanes belong to every remaining
            // pose of owner j. The trace can propose any subset of them.
            std::vector<H> planes;
            for (int l : active)
                for (auto n : mid[l])
                    planes.push_back({-n.x, -n.y, -minp(state[j][l], n) - inner(n.d)});
            auto inc = trace.points(step, j, planes);
            inc.insert(inc.end(), cores[j].begin(), cores[j].end());
            cores[j] = hull(inc);
            for (int k = 0; k < B; ++k) {
                auto &p = state[j][k];
                for (auto n : mid[k])
                    half(p, {n.x, n.y, maxp(cores[j], n) - outer(n.d)});
                // The outward facet normals of the Minkowski sum of the
                // certified core and a midpoint square come from these two polygons.
                std::vector<N> ns(mid[k].begin(), mid[k].end());
                for (size_t s = 0; s < cores[j].size(); ++s) {
                    auto v = cores[j][s], z = cores[j][(s + 1) % cores[j].size()];
                    I a = z.y - v.y, b = v.x - z.x, g = std::gcd(a, b);
                    if (g)
                        ns.push_back({a / g, b / g, 0});
                }
                std::vector<H> out;
                for (auto n : ns) {
                    auto f = mid[k][0];
                    out.push_back(
                        {n.x, n.y,
                         maxp(cores[j], n) + floorq(W(D) * B * proj(n, f), W(2) * (B + 1) * f.d)});
                }
                for (int i = 0; i < 18; ++i)
                    if (i != j)
                        any(state[i][k], out);
            }
            active.clear();
            for (int l = 0; l < B; ++l)
                if (!state[j][l].empty())
                    active.push_back(l);
            if (active.empty()) {
                trace.finish();
                std::cout << "EXCLUDED case " << cas << " index " << j << " round " << step << " B\n";
                return 0;
            }
            // Across the other owner's surviving angle bands, retain every
            // centre which may separate along an endpoint of either tile's band.
            using S = std::array<I, 4>;
            std::vector<std::vector<S>> sup(B, std::vector<S>(B + 1));
            for (int l : active)
                for (int e = 0; e <= B; ++e)
                    for (int z = 0; z < 4; ++z)
                        sup[l][e][z] = minp(state[j][l], ends[e][z]);
            for (int k = 0; k < B; ++k) {
                std::vector<H> hs;
                for (int e : {k, k + 1})
                    for (int z = 0; z < 4; ++z) {
                        N n = ends[e][z];
                        I least = INT64_MAX;
                        for (int l : active)
                            least = std::min(least, sup[l][e][z] + (k == l ? self(n.d) : supp[e][l]));
                        hs.push_back({n.x, n.y, least});
                    }
                for (int l : active)
                    for (int e : {l, l + 1})
                        for (int z = 0; z < 4; ++z) {
                            N n = ends[e][z];
                            hs.push_back({n.x, n.y, sup[l][e][z] + (k == l ? self(n.d) : supp[e][k])});
                        }
                for (int i = 0; i < 18; ++i)
                    if (i != j)
                        any(state[i][k], hs);
            }
            emitWatch(step, j);
        }
        int count = 0;
        for (auto &rows : state)
            for (auto &p : rows)
                count += !p.empty();
        std::cout << "round " << step << " active " << count << std::endl;
    }
    trace.finish();
    std::cout << "UNDECIDED\n";
    return 1;
}

int main(int argc, char **argv) {
    try {
        return run(argc, argv);
    } catch (const std::exception &e) {
        std::cerr << "INVALID: " << e.what() << "\n";
        return 2;
    }
}
