"""Demonstrate itertools.groupby: the bug, the fix, and the shared-iterator trap."""
from __future__ import annotations

import itertools
import operator
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    status: str   # "todo" | "in_progress" | "done" | "blocked"


# Interleaved statuses — the canonical buggy fixture
tickets = [
    Ticket(uuid4(), "Login fails on Safari", "todo"),
    Ticket(uuid4(), "OAuth callback loops", "in_progress"),
    Ticket(uuid4(), "Docs typo in /login", "done"),
    Ticket(uuid4(), "Index out of range on /search", "todo"),
    Ticket(uuid4(), "Synonym expansion slow", "blocked"),
    Ticket(uuid4(), "Add filter UI", "todo"),
]


def groupby_unsorted_bug() -> None:
    """groupby groups CONSECUTIVE equal-key items — unsorted input is the bug."""
    by_status = operator.attrgetter("status")
    groups = itertools.groupby(tickets, key=by_status)
    result = [(k, [t.title for t in g]) for k, g in groups]
    print("groupby(tickets, key=status) — UNSORTED input:")
    for status, titles in result:
        print(f"  {status!r}: {titles}")
    print(f"  -> {len(result)} groups instead of 4 — bug!")


def groupby_sorted_fix() -> None:
    """Sort by key first — then groupby collapses to one group per key."""
    by_status = operator.attrgetter("status")
    sorted_tickets = sorted(tickets, key=by_status)
    groups = itertools.groupby(sorted_tickets, key=by_status)
    result = [(k, [t.title for t in g]) for k, g in groups]
    print("groupby(sorted(tickets, key=status), key=status) — SORTED input:")
    for status, titles in result:
        print(f"  {status!r}: {titles}")
    print(f"  -> {len(result)} groups, one per status — fixed!")


def the_canonical_pattern() -> None:
    """The one-liner every senior engineer reaches for."""
    by_status = operator.attrgetter("status")
    by_status_groups = [
        (k, list(g))
        for k, g in itertools.groupby(
            sorted(tickets, key=by_status),
            key=by_status,
        )
    ]
    print("The canonical [(k, list(g)) for k, g in groupby(sorted(...), key=...)] pattern:")
    for status, group in by_status_groups:
        print(f"  {status!r}: {len(group)} tickets")


def shared_iterator_trap() -> None:
    """Each group iterator must be consumed before advancing to the next."""
    by_status = operator.attrgetter("status")
    sorted_tickets = sorted(tickets, key=by_status)
    groups = itertools.groupby(sorted_tickets, key=by_status)

    # Take the first group's key, then immediately jump to the second group
    # WITHOUT consuming the first group's iterator:
    first_key, first_group = next(groups)
    second_key, second_group = next(groups)   # ← first_group's iterator is now poisoned
    print(f"first_key={first_key!r} (first_group NOT consumed)")
    print(f"second_key={second_key!r}")
    # Now try to consume first_group — the shared underlying iterator has
    # advanced past the first group's items, so first_group yields nothing:
    leftover = list(first_group)
    print(f"list(first_group) AFTER advancing -> {len(leftover)} items (should be 1 — got 0!)")
    # And second_group is fine — until you advance to the third group
    sg_titles = [t.title for t in second_group]
    print(f"second_group titles: {sg_titles}")


def count_per_group() -> None:
    """The common aggregator: count tickets per status."""
    by_status = operator.attrgetter("status")
    counts = {
        k: sum(1 for _ in g)
        for k, g in itertools.groupby(
            sorted(tickets, key=by_status),
            key=by_status,
        )
    }
    print("counts per status:", counts)


def main() -> None:
    print("=== groupby: the unsorted bug ===")
    groupby_unsorted_bug()
    print()
    print("=== groupby: the sorted fix ===")
    groupby_sorted_fix()
    print()
    print("=== groupby: the canonical pattern ===")
    the_canonical_pattern()
    print()
    print("=== groupby: the shared-iterator trap ===")
    shared_iterator_trap()
    print()
    print("=== groupby: count per group ===")
    count_per_group()


if __name__ == "__main__":
    main()
