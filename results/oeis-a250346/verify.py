"""Verify the finite certificate for OEIS A250346 using integer arithmetic."""

import argparse
from collections import Counter
from itertools import product
from pathlib import Path


def direct_count(length, state):
    """Enumerate the literal arrays, including any values already used."""
    prior = dict(enumerate(state, start=1))
    choices = [range(i, i + 4) for i in range(1, length + 1)]
    return sum(
        all(times + prior.get(value, 0) <= 2 for value, times in Counter(array).items())
        for array in product(*choices)
    )


def successors(state):
    for offset in range(4):
        loads = [*state, 0]
        if loads[offset] < 2:
            loads[offset] += 1
            yield tuple(loads[1:])


def read_b_file(path):
    terms = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        data = line.partition("#")[0].strip()
        if not data:
            continue
        try:
            index, value = map(int, data.split())
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: expected an index and a value") from error
        if index < 0 or index in terms:
            raise ValueError(f"{path}:{line_number}: invalid or duplicate index {index}")
        terms[index] = value
    if not terms:
        raise ValueError(f"{path}: no terms")
    return terms


def verify(terms):
    states = list(product(range(3), range(3), range(2)))
    edges = {state: tuple(successors(state)) for state in states}
    rows = [{state: 1 for state in states}]
    for _ in range(max(8, max(terms, default=0))):
        previous = rows[-1]
        rows.append({state: sum(previous[t] for t in edges[state]) for state in states})

    empty = (0, 0, 0)
    for state in states:
        for n in range(9 if state == empty else 7):
            if direct_count(n, state) != rows[n][state]:
                raise ValueError(f"Enumeration disagrees at n={n}, state={state}")
        a0, _, a2, a3, _, a5, a6 = (row[state] for row in rows[:7])
        if a6 + 2 * a3 + 5 * a2 != 4 * a5 + a0:
            raise ValueError(f"Recurrence certificate failed at state={state}")

    print("Direct enumeration agrees through n=6 in all 18 states and n=8 in the empty state.")
    print("The order-six recurrence certificate holds in all 18 states.")
    for index, value in terms.items():
        if rows[index][empty] != value:
            raise ValueError(f"b-file disagrees at n={index}: computed {rows[index][empty]}, read {value}")
    if terms:
        print(f"All {len(terms)} b-file terms agree (indices {min(terms)} to {max(terms)}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-file", type=Path, help="also compare with a local OEIS b-file")
    args = parser.parse_args()
    verify(read_b_file(args.b_file) if args.b_file else {})
