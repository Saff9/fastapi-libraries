"""tee: fork the iterator; zip_longest: zip with fillvalue for unequal lengths."""
from __future__ import annotations

import itertools
import tracemalloc
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: int
    name: str


@dataclass(frozen=True)
class Ticket:
    id: int
    project_id: int
    title: str
    status: str       # "todo" | "in_progress" | "done" | "blocked"


# --- Fixture: 5 projects, 3 owners, 6 tickets ---
projects = [
    Project(1, "Search"),
    Project(2, "Auth"),
    Project(3, "Docs"),
    Project(4, "Export"),
    Project(5, "Billing"),
]
owners = ["alice", "bob", "carol"]   # 3 named owners — 2 projects will be "unassigned"
UNASSIGNED = "unassigned"


def ticket_rows():
    """Pretend this is a CSV-reader generator: one-shot, lazy, single-pass."""
    rows = [
        Ticket(101, 1, "Search 500 on /q", "in_progress"),
        Ticket(102, 1, "Add synonyms", "todo"),
        Ticket(103, 2, "OAuth callback loops", "blocked"),
        Ticket(104, 3, "Docs typo", "done"),
        Ticket(105, 4, "Export to CSV", "todo"),
        Ticket(106, 5, "Stripe webhook 500", "blocked"),
    ]
    for row in rows:
        yield row


def tee_demo() -> None:
    """tee(iterable, n=2): split a single-pass iterator into two independent forks."""
    # The basic fork
    rows_for_metrics, rows_for_persist = itertools.tee(ticket_rows(), 2)

    # Metrics consumer: count tickets by status
    by_status: dict[str, int] = {}
    for t in rows_for_metrics:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    print("metrics — tickets by status:", by_status)

    # Persistence consumer: log each ticket id (would insert into DB in production)
    persisted_ids = [t.id for t in rows_for_persist]
    print(f"persist — {len(persisted_ids)} rows: {persisted_ids}")

    # The "tee is not free" memory demo with islice
    print()
    print("memory-growth demo: tee with islice and a 50,000-gap fork")
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    def gen():
        for i in range(100_000):
            yield i

    fast, slow = itertools.tee(gen(), 2)
    # Advance 'fast' 50,000 ahead of 'slow' — tee must buffer 50,000 items
    list(itertools.islice(fast, 50_000))
    # 'slow' has not advanced at all — the buffer holds 50,000 ints
    print(f"  slow's next value after fast advanced 50,000: {next(slow)}")
    print(f"  (the buffer holds the 50,000 ints slow hasn't read yet)")

    snapshot_after = tracemalloc.take_snapshot()
    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    top = stats[0]
    print(f"  top allocation delta: {top.size_diff // 1024} KiB at {top.traceback}")


def zip_longest_demo() -> None:
    """zip_longest(*iterables, fillvalue=None): zip with fillvalue for unequal lengths."""
    # The bug: zip silently truncates to the shortest (3 pairs, 2 projects dropped)
    truncated = list(zip(projects, owners))
    print(f"zip(projects, owners) -> {len(truncated)} pairs (silently drops 2 projects)")

    # The fix: zip_longest pads to the longest with fillvalue
    padded = list(itertools.zip_longest(projects, owners, fillvalue=UNASSIGNED))
    print(f"zip_longest(projects, owners, fillvalue={UNASSIGNED!r}) -> {len(padded)} pairs:")
    for project, owner in padded:
        print(f"  P{project.id} {project.name:8} -> {owner}")

    # The default fillvalue=None is silent — looks like real data
    default_padded = list(itertools.zip_longest(projects, owners))
    print()
    print(f"zip_longest(projects, owners) (default fillvalue=None) -> last 2 pairs:")
    for project, owner in default_padded[-2:]:
        print(f"  P{project.id} {project.name:8} -> {owner!r}   (None — was that intentional?)")

    # Three-way zip_longest: projects + owners + status, all unequal lengths
    statuses = ["active", "active", "archived"]   # only 3 statuses; 2 missing
    tri = list(itertools.zip_longest(projects, owners, statuses, fillvalue="unknown"))
    print()
    print("zip_longest(projects, owners, statuses, fillvalue='unknown'):")
    for project, owner, status in tri:
        print(f"  P{project.id} {project.name:8} | owner={owner:10} | status={status}")


def main() -> None:
    print("=== tee: fork the single-pass iterator ===")
    tee_demo()
    print()
    print("=== zip_longest: zip unequal-length iterables ===")
    zip_longest_demo()


if __name__ == "__main__":
    main()
