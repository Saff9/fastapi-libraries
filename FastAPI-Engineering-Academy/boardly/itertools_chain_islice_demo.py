"""Demonstrate chain, chain.from_iterable, and islice on boardly streams."""
from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass
from uuid import UUID, uuid4


# --- The boardly models (subset — see boardly/models.py) ---
@dataclass(frozen=True)
class Project:
    id: UUID
    name: str


@dataclass(frozen=True)
class Ticket:
    id: UUID
    project_id: UUID
    title: str
    status: str   # "open" | "in_progress" | "blocked" | "done"


# --- A small offline fixture: two projects, three tickets each ---
proj_a = Project(uuid4(), "Auth Rewrite")
proj_b = Project(uuid4(), "Search v2")
projects = [proj_a, proj_b]

tickets_a = [
    Ticket(uuid4(), proj_a.id, "Login fails on Safari", "open"),
    Ticket(uuid4(), proj_a.id, "OAuth callback loops", "in_progress"),
    Ticket(uuid4(), proj_a.id, "Docs typo in /login", "done"),
]
tickets_b = [
    Ticket(uuid4(), proj_b.id, "Index out of range on /search", "open"),
    Ticket(uuid4(), proj_b.id, "Synonym expansion slow", "blocked"),
    Ticket(uuid4(), proj_b.id, "Add filter UI", "open"),
]


def ticket_batches() -> list[list[Ticket]]:
    """Pretend each inner list is a page fetched from the DB cursor."""
    return [tickets_a, tickets_b]


def tickets_for(project: Project) -> list[Ticket]:
    """Trivial dispatcher — pretend this hits the DB cursor per project."""
    return tickets_a if project.id == proj_a.id else tickets_b


def chain_two_iterables() -> None:
    """chain(*iterables) concatenates without building a combined list."""
    stream = itertools.chain(tickets_a, tickets_b)
    print("chain(tickets_a, tickets_b) — first 2 titles:")
    for t in itertools.islice(stream, 2):
        print(f"  {t.title}")
    print("rest of the stream:")
    for t in stream:
        print(f"  {t.title}")


def chain_from_iterable_flattens_one_level() -> None:
    """chain.from_iterable(iterable_of_iterables) is the fast path."""
    pages = ticket_batches()
    stream = itertools.chain.from_iterable(pages)
    print("from_iterable(pages) — all ticket titles, flattened:")
    for t in stream:
        print(f"  {t.title}")

    stream2 = itertools.chain.from_iterable(
        tickets_for(p) for p in projects
    )
    print("from_iterable(generator) — works where chain(*gen) would explode:")
    for t in stream2:
        print(f"  {t.title}")


def islice_prefix_and_step() -> None:
    """islice(iterable, stop) and islice(iter, start, stop, step) — lazy slice."""
    stream = itertools.chain(tickets_a, tickets_b)
    first_three = list(itertools.islice(stream, 3))
    print("islice(stream, 3) ->", [t.title for t in first_three])

    rest = list(stream)
    print("rest of stream ->", [t.title for t in rest])

    every_other = list(itertools.islice(range(10), 0, 10, 2))
    print("islice(range(10), 0, 10, 2) ->", every_other)


def islice_rejects_negative_indices() -> None:
    """Negative start/stop/step raise ValueError — the gotcha."""
    try:
        list(itertools.islice(range(10), -1))
    except ValueError as e:
        print("islice(range(10), -1) ->", e)

    stream = (f"row-{i}" for i in range(10))
    last_three = deque(stream, maxlen=3)
    print("last 3 via deque(maxlen=3) ->", list(last_three))


def memory_win_vs_list_slice() -> None:
    """islice(stream, 50) vs list(stream)[:50] — same result, different cost."""
    def big_stream(n: int):
        for i in range(n):
            yield {"id": i, "title": f"ticket-{i}"}

    head = list(itertools.islice(big_stream(1_000_000), 3))
    print("islice(big_stream(1_000_000), 3) ->", [h["title"] for h in head])
    print("list(big_stream(1_000_000))[:3] would allocate 1,000,000 dicts")


def main() -> None:
    print("=== chain: two iterables ===")
    chain_two_iterables()
    print()
    print("=== chain.from_iterable: flatten one level ===")
    chain_from_iterable_flattens_one_level()
    print()
    print("=== islice: prefix and step ===")
    islice_prefix_and_step()
    print()
    print("=== islice: rejects negative indices ===")
    islice_rejects_negative_indices()
    print()
    print("=== memory win: islice vs list-slice ===")
    memory_win_vs_list_slice()


if __name__ == "__main__":
    main()
