"""Check strict descent over a consecutive interval of positive integers.

The default interval rechecks the Fairfax-Ball result published October 14, 2026.
Reaching 1 follows by strong induction given convergence below the chosen start.
Arithmetic uses Python's unbounded integers.
"""

from argparse import ArgumentParser

START = 2_175_982_616 * 2**40
COUNT = 79_852_170
STEP_LIMIT = 10_000


def steps_to_descent(n: int) -> int:
    """Count shortcut steps until the orbit first falls strictly below n."""
    x = n
    for steps in range(1, STEP_LIMIT + 1):
        if x % 2 == 0:
            x //= 2
        else:
            x = (3 * x + 1) // 2
        if x < n:
            return steps
    raise RuntimeError(f"No descent found in {STEP_LIMIT} shortcut steps for {n}")


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=START, help="first integer, inclusive")
    parser.add_argument("--count", type=int, default=COUNT, help="number of consecutive integers")
    args = parser.parse_args()
    if args.start < 2 or args.count < 1:
        parser.error("--start must be at least 2 and --count must be positive")
    start = args.start
    stop = start + args.count

    # Even n descend to n/2. For n = 1 (mod 4), n > 1, two shortcut
    # steps give (3n+1)/4 < n. Enumerate every remaining starting value.
    first = start + (3 - start) % 4
    tested = 0
    max_steps = 0
    record_start = 0
    for n in range(first, stop, 4):
        steps = steps_to_descent(n)
        tested += 1
        if steps > max_steps:
            max_steps, record_start = steps, n

    print(f"Strict descent verified on [{start}, {stop})")
    print(f"Starts covered: {args.count}, explicitly iterated: {tested}")
    if tested:
        print(f"Maximum first descent among iterated starts: {max_steps} shortcut steps at {record_start}")


if __name__ == "__main__":
    main()
