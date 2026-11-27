// Continuous large-neighborhood repacking at a prescribed container side.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

namespace {
constexpr int N = 18;
constexpr double pi = 3.14159265358979323846;
using RNG = std::mt19937_64;
double uni(RNG &rng) { return std::generate_canonical<double, 53>(rng); }
double sym(RNG &rng) { return 2 * uni(rng) - 1; }
double sign(double x) { return (x > 0) - (x < 0); }
struct Pose {
    double x, y, a, c, s;
};
Pose make(double x, double y, double a) { return {x, y, a, std::cos(a), std::sin(a)}; }
using Layout = std::array<Pose, N>;

// Returns penetration; a positive value indicates that the squares overlap.
double depth(const Pose &a, const Pose &b, double ra, double rb) {
    const double x = b.x - a.x, y = b.y - a.y;
    const double cs = a.c * b.c + a.s * b.s, sn = a.c * b.s - a.s * b.c;
    const double orient = std::abs(cs) + std::abs(sn);
    const double p = std::max(std::abs(x * a.c + y * a.s), std::abs(-x * a.s + y * a.c));
    const double q = std::max(std::abs(x * b.c + y * b.s), std::abs(-x * b.s + y * b.c));
    return std::min(ra + rb * orient - p, rb + ra * orient - q);
}

std::vector<int> remove_patch(const Layout &layout, int size, int mode, RNG &rng) {
    const auto &a = layout[rng() % N];
    const auto &b = layout[rng() % N];
    double alpha = 2 * pi * uni(rng), c = std::cos(alpha), s = std::sin(alpha);
    const double stretch = .28 + uni(rng) * .72;
    std::array<double, N> score{};
    for (int i = 0; i < N; i++) {
        double x = layout[i].x - a.x, y = layout[i].y - a.y;
        double u = c * x + s * y, v = -s * x + c * y;
        double d = stretch * stretch * u * u + v * v;
        if (mode == 1) { // Two cavities rather than a single connected patch.
            double dx = layout[i].x - b.x, dy = layout[i].y - b.y;
            d = std::min(x * x + y * y, dx * dx + dy * dy);
        } else if (mode == 2) { // A strip across the full width.
            d = v * v + .025 * u * u;
        } else if (mode == 3) { // A deliberately disconnected set of holes.
            d = uni(rng) * 8;
        }
        score[i] = d + .35 * uni(rng);
    }
    std::vector<int> ids(N);
    std::iota(ids.begin(), ids.end(), 0);
    std::sort(ids.begin(), ids.end(), [&](int i, int j) { return score[i] < score[j]; });
    ids.resize(size);
    std::shuffle(ids.begin(), ids.end(), rng);
    return ids;
}

void repopulate(Layout &q, const std::vector<int> &patch, double side, RNG &rng) {
    Layout original = q, best = q;
    unsigned mask = 0;
    for (int i : patch)
        mask |= 1u << i;
    double bestEnergy = 1e100;
    // Independent multi-start constructive refill, retaining the best complete cavity.
    for (int round = 0; round < 4; round++) {
        unsigned vacant = mask;
        q = original;
        double energy = 0;
        for (int i : patch) {
            double bestMerit = 1e100;
            Pose pick{};
            for (int trial = 0; trial < 130; trial++) {
                int home = patch[rng() % patch.size()];
                double angle = sym(rng) * pi / 4;
                if (trial % 4 == 0)
                    angle = original[home].a + .22 * sym(rng);
                if (trial % 9 == 0)
                    angle = 0;
                Pose z = make(0, 0, angle);
                double edge = side / 2 - (std::abs(z.c) + std::abs(z.s)) / 2;
                if (trial % 3) {
                    z.x = original[home].x + .91 * sym(rng);
                    z.y = original[home].y + .91 * sym(rng);
                } else {
                    z.x = edge * sym(rng);
                    z.y = edge * sym(rng);
                }
                z.x = std::clamp(z.x, -edge, edge);
                z.y = std::clamp(z.y, -edge, edge);
                double clash = 0;
                for (int j = 0; j < N; j++)
                    if (!(vacant & (1u << j))) {
                        if (std::abs(z.x - q[j].x) > 1.42 || std::abs(z.y - q[j].y) > 1.42)
                            continue;
                        double d = depth(z, q[j], .5, .5);
                        if (d > 0)
                            clash += d * d;
                    }
                const double merit = clash + .003 * uni(rng);
                if (merit < bestMerit) {
                    bestMerit = merit;
                    pick = z;
                }
            }
            q[i] = pick;
            vacant ^= 1u << i;
            energy += bestMerit;
        }
        if (energy < bestEnergy) {
            bestEnergy = energy;
            best = q;
        }
    }
    q = best;
}

void relax(Layout &q, unsigned free, double side, double radius, int steps) {
    // Anchored iterations at fixed container size. Removed tiles grow back to
    // full size, allowing them to move through temporarily narrower passages.
    std::array<std::array<double, 3>, N> velocity{};
    for (int iter = 0; iter < steps; iter++) {
        std::array<std::array<double, 3>, N> f{};
        double energy = 0;
        for (int i = 0; i < N; i++) {
            bool mi = free & (1u << i);
            const auto &a = q[i];
            double ri = mi ? radius : .5;
            if (mi) {
                double h = ri * (std::abs(a.c) + std::abs(a.s));
                double dh = ri * (-sign(a.c) * a.s + sign(a.s) * a.c);
                for (int k = 0; k < 2; k++) {
                    double x = k == 0 ? a.x : a.y, g = std::abs(x) + h - side / 2;
                    if (g > 0) {
                        f[i][k] -= g * sign(x);
                        f[i][2] -= g * dh;
                        energy += g * g;
                    }
                }
            }
            for (int j = 0; j < i; j++) {
                bool mj = free & (1u << j);
                if (!(mi || mj))
                    continue;
                const auto &b = q[j];
                double dx = b.x - a.x, dy = b.y - a.y;
                if (std::abs(dx) > 1.42 || std::abs(dy) > 1.42)
                    continue;
                double ca = a.c * b.c + a.s * b.s, sa = a.c * b.s - a.s * b.c;
                double phi = std::abs(ca) + std::abs(sa), dphi = -sign(ca) * sa + sign(sa) * ca;
                double rj = mj ? radius : .5, pen = 2., wx = 0., wy = 0., dd = 0.;
                bool ownerI = false;
                for (int owner = 0; owner < 2; owner++) {
                    const auto &v = owner == 0 ? a : b;
                    for (int k = 0; k < 2; k++) {
                        double nx = k == 0 ? v.c : -v.s, ny = k == 0 ? v.s : v.c,
                               p = dx * nx + dy * ny;
                        double g =
                            owner == 0 ? ri + rj * phi - std::abs(p) : rj + ri * phi - std::abs(p);
                        if (g < pen) {
                            pen = g;
                            wx = sign(p) * nx;
                            wy = sign(p) * ny;
                            dd = sign(p) * (-dx * ny + dy * nx);
                            ownerI = owner == 0;
                        }
                    }
                }
                if (pen <= 0)
                    continue;
                const double angular = (ownerI ? rj : ri) * dphi;
                if (mi) {
                    f[i][0] -= pen * wx;
                    f[i][1] -= pen * wy;
                    f[i][2] += pen * (angular + (ownerI ? dd : 0));
                }
                if (mj) {
                    f[j][0] += pen * wx;
                    f[j][1] += pen * wy;
                    f[j][2] += pen * (-angular + (ownerI ? 0 : dd));
                }
                energy += pen * pen;
            }
        }
        if (energy < 1e-14)
            break;
        double step = .26 * (1. - .60 * iter / steps);
        for (int i = 0; i < N; i++)
            if (free & (1u << i)) {
                for (int k = 0; k < 3; k++)
                    velocity[i][k] = .48 * velocity[i][k] + f[i][k];
                auto &a = q[i];
                a = make(a.x + step * velocity[i][0], a.y + step * velocity[i][1],
                         a.a + .75 * step * velocity[i][2]);
            }
    }
}
} // namespace

extern "C" unsigned patch_repack(double *x, uint64_t key, int size, int mode, double side) {
    RNG rng(key);
    Layout q;
    for (int i = 0; i < N; i++)
        q[i] = make(x[3 * i], x[3 * i + 1], x[3 * i + 2]);
    auto ids = remove_patch(q, size, mode, rng);
    repopulate(q, ids, side, rng);
    unsigned mask = 0;
    for (int i : ids)
        mask |= 1u << i;
    relax(q, mask, side, .39, 55);
    relax(q, mask, side, .445, 70);
    relax(q, mask, side, .48, 80);
    relax(q, mask, side, .5, 100);
    for (int i = 0; i < N; i++) {
        x[3 * i] = q[i].x;
        x[3 * i + 1] = q[i].y;
        x[3 * i + 2] = q[i].a;
    }
    x[54] = side;
    return mask;
}

extern "C" unsigned patch_splice(double *x, const double *donor, uint64_t key, int size, int mode,
                                 double side) {
    RNG rng(key);
    Layout q, best, d;
    for (int i = 0; i < N; i++) {
        q[i] = make(x[3 * i], x[3 * i + 1], x[3 * i + 2]);
        d[i] = make(donor[3 * i], donor[3 * i + 1], donor[3 * i + 2]);
    }
    const auto ids = remove_patch(q, size, mode, rng);
    unsigned mask = 0;
    for (int i : ids)
        mask |= 1u << i;
    double bestScore = 1e100;
    // Pose the donor as a whole before selecting the noninterfering tiles.
    // One common reflection, rotation and translation preserves the internal
    // feasibility of every donor subset; its obstacles are the retained tiles
    // of an entirely different configuration.
    for (int it = 0; it < 96; it++) {
        double angle = (rng() % 4) * pi / 2 + .45 * sym(rng);
        if (it % 6 == 0)
            angle = (rng() % 4) * pi / 2;
        double c = std::cos(angle), s = std::sin(angle);
        int reflect = (rng() & 1) ? 1 : -1;
        double ox = .75 * sym(rng), oy = .75 * sym(rng);
        if (it % 6 == 0) {
            ox = .07 * sym(rng);
            oy = .07 * sym(rng);
        }
        if (it % 3 == 1) {
            const auto &selected = q[ids[rng() % ids.size()]];
            const auto &start = d[rng() % N];
            ox = selected.x - c * start.x + s * reflect * start.y + .12 * sym(rng);
            oy = selected.y - s * start.x - c * reflect * start.y + .12 * sym(rng);
        }
        Layout moved{};
        std::array<int, N> order;
        std::iota(order.begin(), order.end(), 0);
        std::array<double, N> cost{};
        for (int i = 0; i < N; i++) {
            const auto &v = d[i];
            auto &z = moved[i];
            z = make(ox + c * v.x - s * reflect * v.y, oy + s * v.x + c * reflect * v.y,
                     reflect * v.a + angle);
            double h = (std::abs(z.c) + std::abs(z.s)) / 2;
            double gx = std::max(std::abs(z.x) + h - side / 2, 0.);
            double gy = std::max(std::abs(z.y) + h - side / 2, 0.);
            double clash = gx * gx + gy * gy;
            for (int j = 0; j < N; j++)
                if (!(mask & (1u << j))) {
                    if (std::abs(z.x - q[j].x) > 1.42 || std::abs(z.y - q[j].y) > 1.42)
                        continue;
                    double g = std::max(depth(z, q[j], .5, .5), 0.);
                    clash += g * g;
                }
            cost[i] = clash + .006 * uni(rng);
        }
        std::partial_sort(order.begin(), order.begin() + size, order.end(),
                          [&](int a, int b) { return cost[a] < cost[b]; });
        double score = 0., change = 0.;
        for (int i = 0; i < size; i++) {
            int h = order[i];
            score += cost[h];
            double near = 10.;
            for (int j : ids) {
                double dx = moved[h].x - q[j].x, dy = moved[h].y - q[j].y;
                double da = std::remainder(moved[h].a - q[j].a, pi / 2);
                near = std::min(near, dx * dx + dy * dy + .25 * da * da);
            }
            change = std::max(change, near);
        }
        // A near-identical donor would make this an inessential relabeling.
        if (change < .03)
            score += 1;
        if (score < bestScore) {
            bestScore = score;
            best = q;
            for (int i = 0; i < size; i++)
                best[ids[i]] = moved[order[i]];
        }
    }
    q = best;
    relax(q, mask, side, .405, 45);
    relax(q, mask, side, .47, 70);
    relax(q, mask, side, .5, 95);
    for (int i = 0; i < N; i++) {
        x[3 * i] = q[i].x;
        x[3 * i + 1] = q[i].y;
        x[3 * i + 2] = q[i].a;
    }
    x[54] = side;
    return mask;
}
