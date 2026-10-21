"""The three infinite iterators: cycle, repeat, count."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str


# --- Fixture ---
engineers = ["alice", "bob", "carol"]            # on-call rotation
ticket_ids = [f"T-{n}" for n in range(1, 8)]     # 7 incoming tickets
default_owner = "unassigned"
projects = ["Search", "Auth", "Docs", "Export"]   # 4 active projects


def cycle_round_robin() -> None:
    """cycle(iterable): loop the iterable forever."""
    # Bounded form: islice(cycle(...), n)
    assignments = list(itertools.islice(itertools.cycle(engineers), len(ticket_ids)))
    print("round-robin assignments:")
    for tid, who in zip(ticket_ids, assignments):
        print(f"  {tid} -> {who}")

    # Unbounded form: for x in cycle(...) with an explicit break
    print("first 5 with explicit break:")
    for n, who in enumerate(itertools.cycle(engineers)):
        if n >= 5:
            break
        print(f"  {n}: {who}")


def repeat_as_map_filler() -> None:
    """repeat(elem, times=None): repeat elem N times (or forever if times is None)."""
    print(f"repeat(2, 3)      = {list(itertools.repeat(2, 3))}")
    print(f"repeat('x', 0)    = {list(itertools.repeat('x', 0))}")
    print(f"islice(repeat(2), 4) = {list(itertools.islice(itertools.repeat(2), 4))}")

    # The map filler pattern: zip two iterables, one finite, one infinite-constant
    pairs = list(map(lambda tid, owner: (tid, owner), ticket_ids, itertools.repeat(default_owner)))
    print("audit pairs (ticket_id, default_owner):")
    for tid, owner in pairs:
        print(f"  ({tid}, {owner})")

    # The real win: map(pow, range(5), repeat(2)) — pow's 2nd arg stays constant
    squares = list(map(pow, range(5), itertools.repeat(2)))
    print(f"map(pow, range(5), repeat(2)) = {squares}")


def count_for_enumeration() -> None:
    """count(start=0, step=1): infinite arithmetic sequence."""
    print(f"islice(count(10), 5)       = {list(itertools.islice(itertools.count(10), 5))}")
    print(f"islice(count(10, -1), 5)   = {list(itertools.islice(itertools.count(10, -1), 5))}")
    print(f"islice(count(0, 2), 5)     = {list(itertools.islice(itertools.count(0, 2), 5))}")

    # 1-indexed enumeration: zip(count(1), data)
    print("1-indexed projects (zip(count(1), projects)):")
    for n, name in zip(itertools.count(1), projects):
        print(f"  {n}. {name}")

    # The composability win: islice the zip to take rows 2..3
    print("enumerated projects, rows 2-3 only (islice(zip(count(1), projects), 1, 3)):")
    for n, name in itertools.islice(zip(itertools.count(1), projects), 1, 3):
        print(f"  {n}. {name}")


def main() -> None:
    print("=== cycle (round-robin assignment) ===")
    cycle_round_robin()
    print()
    print("=== repeat (map filler) ===")
    repeat_as_map_filler()
    print()
    print("=== count (1-indexed enumeration) ===")
    count_for_enumeration()


if __name__ == "__main__":
    main()
