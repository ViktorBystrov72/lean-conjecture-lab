// Replay the positive-hint (reverse unit propagation) part of text LRAT.
// Each added clause must follow from the still-live clauses in the DIMACS input
// and trace. Deriving the empty clause establishes unsatisfiability.
#include <charconv>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Clause = std::vector<int>;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

class Tokens {
public:
    explicit Tokens(const std::string& line)
        : pos(line.data()), end(line.data() + line.size()) {}

    bool done() {
        skip_space();
        return pos == end;
    }

    bool deletion() {
        skip_space();
        if (pos == end || *pos != 'd') return false;
        ++pos;
        return true;
    }

    int integer() {
        skip_space();
        int value;
        auto result = std::from_chars(pos, end, value);
        require(result.ec == std::errc(), "expected an integer");
        pos = result.ptr;
        return value;
    }

private:
    const char* pos;
    const char* end;

    void skip_space() {
        while (pos != end && std::isspace(static_cast<unsigned char>(*pos))) ++pos;
    }
};

Clause read_literals(Tokens& input, int variables) {
    Clause clause;
    for (int lit; (lit = input.integer()) != 0;) {
        require(lit >= -variables && lit <= variables, "variable outside DIMACS range");
        clause.push_back(lit);
    }
    return clause;
}

void replay(std::istream& formula, std::istream& proof) {
    std::string line;
    int variables = 0, original = 0;
    std::vector<Clause> clauses(1); // Clause IDs start at 1.
    while (std::getline(formula, line)) {
        if (line.empty() || line[0] == 'c') continue;
        if (line[0] == 'p') {
            require(variables == 0, "duplicate DIMACS header");
            std::istringstream header(line);
            std::string marker, format;
            header >> marker >> format >> variables >> original;
            require(header && marker == "p" && format == "cnf" &&
                    variables > 0 && original > 0, "bad DIMACS header");
            clauses.reserve(static_cast<size_t>(original) + 1);
            continue;
        }
        require(variables > 0, "missing DIMACS header");
        Tokens input(line);
        clauses.push_back(read_literals(input, variables));
        require(input.done(), "trailing clause tokens");
    }
    require(formula.eof() && variables > 0 && clauses.size() == static_cast<size_t>(original) + 1,
            "incomplete DIMACS input");

    std::vector<bool> live(clauses.size(), true);
    live[0] = false;
    // Stamps avoid clearing a full assignment between clauses.
    std::vector<int> stamp(variables + 1, 0), value(variables + 1);
    int additions = 0;
    bool empty_proved = false;
    while (std::getline(proof, line)) {
        if (line.empty()) continue;
        Tokens input(line);
        int id = input.integer();
        if (input.deletion()) {
            for (int hint; (hint = input.integer()) != 0;) {
                require(hint > 0 && static_cast<size_t>(hint) < clauses.size(), "bad deletion");
                live[hint] = false;
            }
            require(input.done(), "trailing deletion tokens");
            continue;
        }
        require(id > 0 && static_cast<size_t>(id) >= clauses.size(), "clause ID reused");
        Clause candidate = read_literals(input, variables);
        bool contradiction = false;
        auto assign = [&](int literal) {
            int var = std::abs(literal);
            int truth = literal > 0 ? 1 : -1;
            if (stamp[var] == id && value[var] != truth) {
                contradiction = true;
            } else {
                stamp[var] = id;
                value[var] = truth;
            }
        };
        for (int literal : candidate) assign(-literal);

        for (int hint; (hint = input.integer()) != 0;) {
            require(hint > 0 && static_cast<size_t>(hint) < clauses.size() && live[hint],
                    "unsupported or unavailable hint");
            if (contradiction) continue;
            bool satisfied = false;
            int unknown = 0, unit = 0;
            for (int literal : clauses[hint]) {
                int var = std::abs(literal);
                if (stamp[var] != id) {
                    ++unknown;
                    unit = literal;
                } else if ((literal > 0 ? 1 : -1) == value[var]) {
                    satisfied = true;
                    break;
                }
            }
            require(!satisfied && unknown <= 1, "hint was neither false nor unit");
            if (unknown == 0) contradiction = true;
            else assign(unit);
        }
        require(input.done() && contradiction, "no RUP contradiction");
        ++additions;
        if (candidate.empty()) empty_proved = true;
        clauses.resize(static_cast<size_t>(id) + 1);
        live.resize(clauses.size(), false);
        clauses[id] = std::move(candidate);
        live[id] = true;
    }
    require(proof.eof() && empty_proved, "empty clause never proved");
    std::cout << "Verified UNSAT: " << variables << " variables, " << original
              << " original clauses, " << additions << " RUP additions.\n";
}

int main(int argc, char** argv) {
    try {
        require(argc == 3, "usage: rup_check formula.cnf proof.lrat");
        std::ifstream formula(argv[1]), proof(argv[2]);
        require(formula.good() && proof.good(), "could not open input");
        replay(formula, proof);
    } catch (const std::exception& error) {
        std::cerr << "Rejected: " << error.what() << '\n';
        return 1;
    }
}
