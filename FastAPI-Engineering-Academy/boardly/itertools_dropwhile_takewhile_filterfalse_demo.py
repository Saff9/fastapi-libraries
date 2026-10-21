"""The three predicate filters: dropwhile, takewhile, filterfalse."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    status: str       # "system_boot" | "todo" | "in_progress" | "done" | "blocked"
    priority: int     # 1 (low) .. 5 (urgent)


WATCH = {"blocked", "in_progress"}     # statuses that page the on-call


# --- Fixture: a creation-time-ordered stream ---
# Rows 1-3 are "system_boot" warm-up rows; then real tickets; then
# a stray "system_boot" row mid-stream (a deploy restart) — the gotcha.
stream = [
    Ticket(uuid4(), "[boot] pipeline ready", "system_boot", 0),
    Ticket(uuid4(), "[boot] db pool warmed", "system_boot", 0),
    Ticket(uuid4(), "[boot] scheduler started", "system_boot", 0),
    Ticket(uuid4(), "Search returns 500", "todo", 5),
    Ticket(uuid4(), "Auth fails on macOS", "todo", 3),
    Ticket(uuid4(), "Export to CSV", "in_progress", 2),
    Ticket(uuid4(), "Docs typo", "done", 1),
    Ticket(uuid4(), "[boot] redeploy at noon", "system_boot", 0),  # stray mid-stream
    Ticket(uuid4(), "Reopen: search bug", "todo", 4),               # reopened ticket
    Ticket(uuid4(), "Synonym expansion slow", "blocked", 2),
]


def dropwhile_demo() -> None:
    """dropwhile(predicate, iterable): drop prefix while True, then yield all rest."""
    # Per-element demo: dropwhile(<5, [1,4,6,3,8]) — note 3 survives
    nums = [1, 4, 6, 3, 8]
    result = list(itertools.dropwhile(lambda x: x < 5, nums))
    print(f"dropwhile(<5, {nums}) -> {result}   # note 3 is yielded even though <5")

    # Boardly: skip leading system_boot rows, yield the rest (including the stray)
    real_stream = itertools.dropwhile(lambda t: t.status == "system_boot", stream)
    print("dropwhile(system_boot, stream) — first 4 titles after the prefix:")
    for t in itertools.islice(real_stream, 4):
        print(f"  [{t.status:12}] {t.title}")


def takewhile_demo() -> None:
    """takewhile(predicate, iterable): yield while True, then STOP at first False."""
    # Per-element demo: takewhile(<5, [1,4,6,3,8]) — note 3 is NOT yielded
    nums = [1, 4, 6, 3, 8]
    result = list(itertools.takewhile(lambda x: x < 5, nums))
    print(f"takewhile(<5, {nums}) -> {result}   # note 3 is NOT yielded (stop at 6)")

    # Boardly: take leading "todo" tickets, stop at first non-todo.
    # The boot prefix (rows 1-3) is dropped first so the leading todos are
    # at the head of the stream takewhile walks.
    stream_after_boot = stream[3:]
    leading_todos = itertools.takewhile(lambda t: t.status == "todo", stream_after_boot)
    print("takewhile(status == 'todo', stream_after_boot) — leading todos only:")
    for t in leading_todos:
        print(f"  [{t.status:12}] {t.title}")
    print("  (stops at first non-todo; the later 'Reopen: search bug' todo is NOT reached)")


def filterfalse_demo() -> None:
    """filterfalse(predicate, iterable): yield where predicate is False (complement of filter)."""
    # Per-element demo: filterfalse(even, [1,2,3,4,5]) — the odds
    nums = [1, 2, 3, 4, 5]
    result = list(itertools.filterfalse(lambda x: x % 2 == 0, nums))
    print(f"filterfalse(even, {nums}) -> {result}   # the odds (complement of filter)")

    # filterfalse(None, ...) — yields falsy elements
    mixed = [0, 1, 2, None, 3, "", "x", [], [1]]
    falsies = list(itertools.filterfalse(None, mixed))
    print(f"filterfalse(None, {mixed!r}) -> {falsies!r}   # the falsy elements")

    # Boardly: tickets NOT in the WATCH set — the "don't page me" view
    not_watched = itertools.filterfalse(lambda t: t.status in WATCH, stream)
    print("filterfalse(status in WATCH, stream) — tickets NOT watched:")
    for t in not_watched:
        print(f"  [{t.status:12}] {t.title}")


def main() -> None:
    print("=== dropwhile: drop prefix while True, then yield the rest ===")
    dropwhile_demo()
    print()
    print("=== takewhile: yield while True, then STOP at first False ===")
    takewhile_demo()
    print()
    print("=== filterfalse: yield where predicate is False (complement of filter) ===")
    filterfalse_demo()


if __name__ == "__main__":
    main()
