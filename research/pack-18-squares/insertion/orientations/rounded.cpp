// Positional and angular gradient of an overlap penalty for disk-to-square homotopy.
#include <algorithm>
#include <array>
#include <cmath>
namespace {
double sign(double z) { return (z > 0) - (z < 0); }
struct Rot {
    double x, y;
};
} // namespace
extern "C" double energy(const double *q, double fraction, double side, double *grad) {
    std::fill(grad, grad + 54, 0.0);
    std::array<Rot, 18> angle;
    double result = 0;
    for (int i = 0; i < 18; i++) {
        double c = std::cos(q[3 * i + 2]), s = std::sin(q[3 * i + 2]);
        angle[i] = {c, s};
        const double half = .5 * (1 + fraction * (std::abs(c) + std::abs(s) - 1));
        const double dh = .5 * fraction * (-sign(c) * s + sign(s) * c);
        for (int k = 0; k < 2; k++) {
            double pos = q[3 * i + k], g = std::abs(pos) + half - side / 2;
            if (g > 0) {
                result += g * g;
                grad[3 * i + k] += 2 * g * sign(pos);
                grad[3 * i + 2] += 2 * g * dh;
            }
        }
        for (int j = 0; j < i; j++) {
            double dx = q[3 * j] - q[3 * i], dy = q[3 * j + 1] - q[3 * i + 1];
            if (std::abs(dx) > 1.415 || std::abs(dy) > 1.415)
                continue;
            double cs = c * angle[j].x + s * angle[j].y, sn = c * angle[j].y - s * angle[j].x;
            double support = 1 + .5 * fraction * (std::abs(cs) + std::abs(sn) - 1);
            double change = .5 * fraction * (-sign(cs) * sn + sign(sn) * cs);
            double best = -10, gx = 0, gy = 0, ga = 0, gb = 0;
            for (int owner : {i, j}) {
                const Rot r = angle[owner];
                for (auto n : {r, Rot{-r.y, r.x}}) {
                    double raw = dx * n.x + dy * n.y, sg = sign(raw);
                    double g = std::abs(raw) - support;
                    if (g > best) {
                        best = g;
                        gx = sg * n.x;
                        gy = sg * n.y;
                        double turn = sg * (-dx * n.y + dy * n.x);
                        ga = change + (owner == i ? turn : 0);
                        gb = -change + (owner == j ? turn : 0);
                    }
                }
            }
            double distance = std::hypot(dx, dy);
            if (distance > 1e-8 && fraction < 1) {
                double nx = dx / distance, ny = dy / distance;
                double ii = c * nx + s * ny, it = c * ny - s * nx;
                double jj = angle[j].x * nx + angle[j].y * ny,
                       jt = angle[j].x * ny - angle[j].y * nx;
                double di = -sign(ii) * it + sign(it) * ii, dj = -sign(jj) * jt + sign(jt) * jj;
                double g =
                    distance - 1 +
                    .5 * fraction * (2 - std::abs(ii) - std::abs(it) - std::abs(jj) - std::abs(jt));
                if (g > best) {
                    best = g;
                    double k = .5 * fraction * (di + dj) / distance;
                    gx = nx + k * ny;
                    gy = ny - k * nx;
                    ga = .5 * fraction * di;
                    gb = .5 * fraction * dj;
                }
            }
            if (best < 0) {
                result += best * best;
                double k = 2 * best;
                grad[3 * i] -= k * gx;
                grad[3 * i + 1] -= k * gy;
                grad[3 * i + 2] += k * ga;
                grad[3 * j] += k * gx;
                grad[3 * j + 1] += k * gy;
                grad[3 * j + 2] += k * gb;
            }
        }
    }
    return result;
}
