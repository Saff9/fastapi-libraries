"""Demonstrate itertools.starmap and itertools.accumulate on boardly streams."""
from __future__ import annotations

import itertools
import operator
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    hours: int        # logged hours
    rate: Decimal     # billing rate per hour (USD)


# A small fixture — (hours, rate) pairs to compute revenue per ticket
tickets = [
    Ticket(uuid4(), "Login fails on Safari", 5, Decimal("120.00")),
    Ticket(uuid4(), "OAuth callback loops", 3, Decimal("150.00")),
    Ticket(uuid4(), "Docs typo in /login", 1, Decimal("90.00")),
    Ticket(uuid4(), "Search index slow", 8, Decimal("200.00")),
]


def starmap_unpacks_tuples() -> None:
    """starmap(func, iterable) calls func(*t) for each tuple t."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    print("starmap(lambda h, r: h * r, [(hours, rate), ...]):")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")
    print("vs. map() which would pass the tuple as one positional arg:")
    # map(lambda pair: pair[0] * pair[1], pairs)  — works but unpacks by hand
    revenues_map = map(lambda pair: pair[0] * pair[1], pairs)
    print("  map version:", [str(r) for r in revenues_map])


def starmap_with_named_callable() -> None:
    """Pair starmap with a named function for cleaner call sites."""
    def revenue(hours: int, rate: Decimal) -> Decimal:
        return hours * rate

    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = list(itertools.starmap(revenue, pairs))
    print("starmap(revenue, pairs) — named function, no lambda:")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")


def accumulate_running_sum() -> None:
    """accumulate(iterable, func=operator.add) — the running aggregate."""
    hours_stream = [t.hours for t in tickets]
    running = list(itertools.accumulate(hours_stream))
    print("accumulate(hours_stream) — default operator.add (running sum):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: {r} hours total")


def accumulate_running_max() -> None:
    """accumulate(iterable, func=max) — the running maximum."""
    hours_stream = [t.hours for t in tickets]
    running_max = list(itertools.accumulate(hours_stream, max))
    print("accumulate(hours_stream, max) — running maximum hours so far:")
    for t, r in zip(tickets, running_max):
        print(f"  after {t.title:30s}: max so far = {r}")


def accumulate_factorial() -> None:
    """accumulate(range(1, n+1), operator.mul) — the lazy factorial."""
    n = 5
    factorials = list(itertools.accumulate(range(1, n + 1), operator.mul))
    print(f"accumulate(range(1, {n+1}), operator.mul) — first {n} factorials:")
    print(f"  {factorials}  # 1!, 2!, 3!, 4!, 5!")


def accumulate_initial_keyword() -> None:
    """accumulate(..., initial=X) — 3.8+ — prepends X to the output."""
    # Without initial: output has N items, one per input item
    no_initial = list(itertools.accumulate([1, 2, 3], operator.add))
    print(f"accumulate([1,2,3], add)             -> {no_initial}  (3 items)")

    # With initial=10: output has N+1 items, the first being initial
    with_initial = list(itertools.accumulate([1, 2, 3], operator.add, initial=10))
    print(f"accumulate([1,2,3], add, initial=10) -> {with_initial}  (4 items)")

    # Factorial with initial=1 — the convention from mathematics
    factorials = list(itertools.accumulate(range(1, 6), operator.mul, initial=1))
    print(f"accumulate(range(1,6), mul, initial=1) -> {factorials}  (6 items, leading 1)")


def running_revenue() -> None:
    """A realistic boardly pipeline: per-ticket revenue -> running total."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    running = itertools.accumulate(revenues, operator.add, initial=Decimal("0"))
    print("starmap -> accumulate pipeline (running revenue, initial=0):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: ${r} total")
    # Note: zip stops at the shortest input, so the leading 0 is paired
    # with the first ticket. Print the raw list to see all 5 items.
    print(f"  raw running list (length 5): {list(itertools.accumulate(itertools.starmap(lambda h, r: h * r, pairs), operator.add, initial=Decimal('0')))}")


def main() -> None:
    print("=== starmap: unpacks tuples into positional args ===")
    starmap_unpacks_tuples()
    print()
    print("=== starmap with a named callable ===")
    starmap_with_named_callable()
    print()
    print("=== accumulate: running sum (default) ===")
    accumulate_running_sum()
    print()
    print("=== accumulate: running max ===")
    accumulate_running_max()
    print()
    print("=== accumulate: factorial ===")
    accumulate_factorial()
    print()
    print("=== accumulate: the initial= keyword (3.8+) ===")
    accumulate_initial_keyword()
    print()
    print("=== boardly pipeline: starmap -> accumulate ===")
    running_revenue()


if __name__ == "__main__":
    main()
