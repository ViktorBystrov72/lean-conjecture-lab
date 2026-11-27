struct FP {
    long double x, y;
};
Poly suggest_points(const std::vector<H> &hs) {
    std::vector<FP> p = {
        {0, 0}, {(long double)U, 0}, {(long double)U, (long double)U}, {0, (long double)U}};
    // Float arithmetic ONLY proposes points. A lost point weakens a deduction.
    for (auto h : hs) {
        if (p.empty() || p.size() > 512)
            return {};
        std::vector<FP> q;
        FP a = p.back();
        auto eval = [&](FP p) { return h.a * p.x + h.b * p.y - h.k; };
        auto s = eval(a);
        for (auto b : p) {
            auto t = eval(b);
            if (t >= 0)
                q.push_back(b);
            if ((s > 0 && t < 0) || (t > 0 && s < 0)) {
                auto z = s / (s - t);
                q.push_back({a.x + z * (b.x - a.x), a.y + z * (b.y - a.y)});
            }
            a = b;
            s = t;
        }
        p.swap(q);
    }
    if (p.empty())
        return {};
    FP c{};
    for (auto q : p) {
        c.x += q.x;
        c.y += q.y;
    }
    c.x /= p.size();
    c.y /= p.size();
    p.push_back(c);
    Poly out;
    for (auto q : p) {
        bool found = false;
        for (double a : {1., .9999999, .99999, .999, .95, .75, .5, 0.}) {
            long double x = c.x + (q.x - c.x) * a, y = c.y + (q.y - c.y) * a;
            if (!std::isfinite(x) || !std::isfinite(y) || x < -10 || y < -10 || x > U + 10 || y > U + 10)
                continue;
            P t{(I)std::llround(x), (I)std::llround(y)};
            for (int dx = -1; dx <= 1 && !found; ++dx)
                for (int dy = -1; dy <= 1 && !found; ++dy) {
                    P z{t.x + dx, t.y + dy};
                    if (z.x < 0 || z.y < 0 || z.x > U || z.y > U)
                        continue;
                    bool ok = std::all_of(hs.begin(), hs.end(), [&](H h) { return value(h, z) >= 0; });
                    if (ok) {
                        out.push_back(z);
                        found = true;
                    }
                }
            if (found)
                break;
        }
    }
    return hull(out);
}
// Optional discovery path. The portable proof only needs integer verification.
struct CandidateTrace {
    std::unique_ptr<CoreTrace> reader;
    std::ofstream output;
    CandidateTrace(const std::string &mode, const char *path) {
        if (mode == "verify")
            reader = std::make_unique<CoreTrace>(path);
        else if (mode == "generate") {
            output.open(path);
            if (!output)
                throw std::runtime_error("cannot write certificate");
        } else
            throw std::runtime_error("expected generate or verify");
    }
    Poly points(int round, int owner, const std::vector<H> &planes) {
        if (reader)
            return reader->points(round, owner, planes);
        Poly p = suggest_points(planes);
        for (auto v : p)
            for (auto h : planes)
                if (value(h, v) < 0)
                    throw std::runtime_error("infeasible suggested point");
        output << round << " " << owner << " " << p.size();
        for (auto v : p)
            output << " " << v.x << " " << v.y;
        output << "\n";
        return p;
    }
    void finish() {
        if (reader)
            reader->finish();
    }
};
