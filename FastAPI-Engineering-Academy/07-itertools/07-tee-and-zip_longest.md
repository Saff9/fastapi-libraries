---
title: "Lesson 07: tee & zip_longest — fork the iterator, zip the unequal"
aliases:
 - itertools tee
 - itertools zip_longest
 - fork the iterator
tags:
 - itertools
 - tee
 - zip_longest
 - streaming
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[07-itertools/05-cycle-repeat-count]]"
 - "[[07-itertools/06-dropwhile-takewhile-filterfalse]]"
 - "[[04-collections/03-deque]]"
related_lessons:
 - "[[07-itertools/06-dropwhile-takewhile-filterfalse]]"
 - "[[07-itertools/05-cycle-repeat-count]]"
 - "[[04-collections/03-deque]]"
---

# Lesson 07: `tee` & `zip_longest` — fork the iterator, zip the unequal

*Two `itertools` functions for the cases the builtin `zip` cannot handle — `tee(iterable, n=2)` splits a single-pass iterator into n independent iterators (WARNING: tee caches the input; if one tee advances far ahead, memory grows), and `zip_longest(*iterables, fillvalue=None)` zips unequal-length iterables by filling the missing positions with a sentinel.*

**You're at the very beginning of Section 07.**

`zip` is the builtin everyone reaches for, and `zip` is right 90% of the time — it stops at the shortest iterable, no sentinel, no waste. The two cases `zip` cannot handle are this lesson: (1) you have a *single-pass iterator* (a generator, a database cursor, a stream socket) and you need *two independent consumers* — one to compute a summary, one to persist the rows — and (2) you have *unequal-length iterables* and you want to keep the missing positions explicit with a `fillvalue` instead of silently truncating. The first case is `itertools.tee`; the second is `itertools.zip_longest`. Both have a gotcha — `tee` is not free (the internal queue grows when one fork advances far ahead of another), and `zip_longest`'s `fillvalue=None` default is silent (a row of `None`s looks like real data). This lesson is the line-by-line tour of both, with the memory-cost demo that makes "tee is not free" land. Take your time. Type every example. **This is how you learn.**

#itertools #tee #zip_longest

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.tee(iterable, n=2)`** — split a single-pass iterator into n independent iterators that each see the full sequence.
2. **State the "tee is not free" rule** — `tee` caches the input; if one fork advances far ahead of another, the buffer of unconsumed elements grows linearly with the gap.
3. **Avoid the "don't reuse the original" trap** — after calling `tee`, the original iterable should not be used; doing so steals values from the shared upstream and silently corrupts the forks.
4. **Apply `itertools.zip_longest(*iterables, fillvalue=None)`** — zip unequal-length iterables, padding the shorter side(s) with `fillvalue` to the length of the longest.
5. **Distinguish `zip` from `zip_longest`** — `zip` truncates to the shortest (silent); `zip_longest` pads to the longest (explicit `fillvalue`). Choose based on whether missing data is a bug (`zip`) or expected (`zip_longest`).

## Prerequisites

Before starting, you need:

- **The iterator/iterable distinction** — [[05-collections-abc/04-Iterator-vs-Iterable]] (also a prerequisite of [[07-itertools/01-chain-and-islice]]). `tee` is the canonical example of the difference: a *list* can be iterated multiple times (each `for x in lst:` is fresh); a *generator* can be iterated once (each `for x in gen:` after the first is empty). `tee` is the bridge that lets you "iterate a generator twice" — at a memory cost.
- **`collections.deque`** — [[04-collections/03-deque]] covers the C-accelerated queue `tee`'s internal buffer is modelled on. The cross-link matters: `tee`'s buffer is essentially a queue of unconsumed items the lagging fork still needs to read, and the memory cost is the same kind of cost `deque` teaches.
- **The previous two `itertools` lessons** — [[07-itertools/05-cycle-repeat-count]] for the laziness model and [[07-itertools/06-dropwhile-takewhile-filterfalse]] for the predicate-filter context. This lesson assumes you have internalised "iterators are one-shot; materialising is the bug".
- **About 25–35 minutes of focused time.**

**The most common gap: assuming `tee` makes a "copy" of the iterable.**

It does not. `tee(iterable, n=2)` returns a tuple of two iterators that *share* a single underlying buffer; it does not materialise two independent copies of the data. The student who writes `a, b = tee(some_gen, 2); list(a); list(b)` and expects `list(b)` to "just work" with O(1) memory gets a surprise: the moment `a` is fully consumed, `tee`'s buffer has held the entire generator output, and `b` reads from that buffer (not from a fresh pass over the original generator). The mental shift this lesson teaches is that `tee` is a *buffered fan-out*, not a *copy* — and the buffer's size is determined by the *gap* between the most-advanced fork and the least-advanced fork, not by the total data size.

## The Problem

`boardly/tickets/forked_pipeline.py` has two real tasks the builtin `zip` cannot express:

1. **One stream, two consumers.** A `ticket_rows()` generator yields ticket dicts one at a time, parsed from a CSV file. The metrics aggregator wants to compute "tickets per project" and "blocked-tickets" totals; the persistence layer wants to insert every row into the database. The naive approach — `rows = list(ticket_rows())` — materialises the entire CSV into memory, which is fine for 1,000 rows and fatal for 1,000,000. `tee(ticket_rows(), 2)` gives both consumers a *lazy* view of the same stream — the metrics aggregator pulls from one fork, the persistence layer pulls from the other, and neither materialises more than a single row at a time (in the *balanced* case where both consumers run at the same rate).

2. **Zip projects with owners, unequal lengths.** The boardly fixture has 5 active projects and 3 named owners; the remaining 2 projects have `owner = "unassigned"` as a sentinel. `zip(projects, owners)` silently truncates to 3 pairs — the 2 unassigned projects are dropped, and the bug is invisible until someone notices the missing projects in the UI. `zip_longest(projects, owners, fillvalue="unassigned")` keeps all 5 projects and fills the missing 2 owner slots with `"unassigned"`, making the missing-data case explicit.

The first task needs `tee` because the input is a one-shot generator and the two consumers must see the same data without re-running the generator (which a generator doesn't support — `__next__` after `StopIteration` keeps raising). The second task needs `zip_longest` because `zip`'s "truncate to the shortest" semantics silently drop data when one side is shorter, and the bug is only visible after the fact. Both are real production failure modes; this lesson is the line-by-line tour.

## The Code

```python
# boardly/itertools_tee_zip_longest_demo.py
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
```

## Line-by-Line Deep Dive

### Lines 1–15: Imports and the boardly models

```python
# boardly/itertools_tee_zip_longest_demo.py
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
```

`itertools` is the star. `tracemalloc` is new — Python's standard-library memory profiler, used for the "tee is not free" demo to measure the buffer that grows when one fork advances far ahead of another. `dataclass` builds the frozen value objects. `from __future__ import annotations` is boardly house style.

The `Project` and `Ticket` models are *simplified* versions of the section's running shape — the IDs are plain `int` instead of `UUID` so the lesson's output is short and readable (no 36-character UUIDs in every print line). The field shapes match the rest of the section: `Project` has `id` and `name`; `Ticket` has `id`, `project_id`, `title`, `status`. Continuity with [[07-itertools/01-chain-and-islice]] and [[07-itertools/06-dropwhile-takewhile-filterfalse]] is preserved at the field level.

**Why `tracemalloc` instead of `sys.getsizeof`?** Because `sys.getsizeof` measures one object in isolation, and `tee`'s buffer is a C-level internal queue that doesn't expose its size through `getsizeof` of the `_tee_dataobject`. `tracemalloc` measures *all* Python-allocator allocations between two snapshots, which captures the buffer's growth as Python-level allocations (each buffered item is a Python object — an `int`, a `tuple`, a `dict` — that `tracemalloc` sees). The trade-off: `tracemalloc` is more invasive (it adds ~5% overhead while running) and reports noisy stats (it captures *every* allocation, not just the one you care about), but it's the only standard-library tool that can measure `tee`'s buffer growth directly.

### Lines 18–35: The fixture — 5 projects, 3 owners, a 6-row ticket generator

```python
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
```

Two fixtures, deliberately unequal. `projects` has 5 entries; `owners` has 3 — the `zip` bug is that the 2 extra projects get silently dropped, and the `zip_longest` fix is that they get the `"unassigned"` sentinel. The numbers are chosen to make the divergence visible: 5 vs 3 leaves exactly 2 padded rows in the `zip_longest` output, which is enough to see the pattern but not so many that the output scrolls off the screen.

`ticket_rows()` is a generator function — the `yield` keyword makes it a generator, not a function that returns a list. The body materialises a `rows` list internally (for the demo's reproducibility) and yields each row one at a time. In production, the body would be `for row in csv.reader(f): yield parse_ticket(row)` — the same single-pass shape, but reading from a file instead of a fixture list. The single-pass contract is what makes `tee` necessary: a generator can be iterated *once*, so two consumers cannot both call `for row in ticket_rows():` and expect to see the rows.

**Why a generator instead of just returning the list?** Because the lesson is about *single-pass iterators*, and a list is *not* single-pass — a list can be iterated as many times as you want, each `for x in lst:` produces a fresh iterator. If the fixture were `rows = [Ticket(...), ...]`, the demo would have no need for `tee` — both consumers could just iterate `rows` directly. The generator is the lesson's point: `tee` exists to give single-pass iterables the multi-pass behaviour that lists have natively. Without a single-pass input, `tee` has no reason to exist.

### Lines 38–62: `tee` — fork the iterator, two independent consumers

```python
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
```

`itertools.tee(iterable, n=2)` returns a tuple of n independent iterators, each of which produces the same sequence of elements as the original `iterable`. The two forks here — `rows_for_metrics` and `rows_for_persist` — both yield all 6 tickets, in order. The metrics consumer walks its fork and computes `by_status` (a `dict[str, int]` counting tickets per status); the persistence consumer walks its fork and collects the ticket IDs.

Internally, `tee` creates a single shared buffer (a linked-list of arrays in CPython's `itertoolsmodule.c`, conceptually a queue) and an "index" per fork. The original `iterable` is consumed lazily — only when a fork needs the next item that's not yet in the buffer. When a fork reads an item, it advances its index; the buffer holds every item from the *most-advanced* fork's position down to the *least-advanced* fork's position. The buffer's size is the *gap* between the forks, not the total data size.

In this demo, the two consumers run *sequentially* — the metrics consumer fully drains `rows_for_metrics` before the persistence consumer starts `rows_for_persist`. That means `tee`'s buffer grows to hold all 6 tickets while the metrics consumer runs, then shrinks back to 0 as the persistence consumer catches up. For 6 items, the buffer peaks at 6 — invisible. For 6 million items, the buffer peaks at 6 million — and the whole point of using a generator (don't materialise) is defeated. The senior-engineer move is to run the two consumers *concurrently* — typically via `asyncio` or `threading` — so neither fork gets more than a few items ahead of the other. (The concurrency lesson is out of scope for this section; the rule is "tee is balanced, or tee is memory-broken".)

**Why `tee` over `list(ticket_rows())`?** Because the list materialises the entire generator into memory — defeating the entire purpose of using a generator. `tee` is the lazy form: each fork pulls from the original generator on demand, and the buffer holds only the *gap* between the most- and least-advanced forks. In the balanced case (both consumers run at the same rate), the gap is 1 — `tee`'s buffer holds a single item at a time, and the total memory is O(1). The list form is O(n) regardless of consumption rate. `tee` wins when the consumers are balanced and the data is large; the list form wins when the data is small or when the consumers cannot be balanced.

**Why `tee` over re-running `ticket_rows()` twice?** Because `ticket_rows()` is a generator function — calling it again produces a *fresh* generator that re-does the work. For a fixture list inside the generator, that's fine (the work is trivial). For a real CSV reader, calling `ticket_rows()` twice re-opens the file and re-parses every row — doubling the I/O and the CPU cost. `tee` consumes the original generator *once*, buffering for the second consumer. The trade-off: `tee` trades memory (the buffer) for I/O/CPU (re-running the generator). For I/O-bound generators (file reads, network reads, DB cursors), `tee` wins; for CPU-bound generators (computing primes, parsing JSON), re-running may win — depends on which is more expensive per item.

### Lines 64–80: The "tee is not free" memory-growth demo

```python
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
```

This is the lesson's heart. `gen()` yields 100,000 integers. `tee(gen(), 2)` produces `fast` and `slow`. The line `list(itertools.islice(fast, 50_000))` consumes 50,000 items from `fast` only — `tee`'s buffer has to hold all 50,000 because `slow` hasn't read any of them. `next(slow)` then returns `0` (the first item), confirming that `slow`'s view is intact; the buffer still holds the 49,999 items `slow` hasn't read.

`tracemalloc` measures the buffer. `tracemalloc.start()` turns on tracing; `take_snapshot()` captures the current allocations; `compare_to(snapshot_before, "lineno")` returns a list of `(filename, line) -> (size, count, delta)` stats sorted by `size_diff` descending. `stats[0]` is the top allocation delta — typically ~1.5 MiB at the `list(islice(fast, 50_000))` line, which is the 50,000 `int` objects `tee` is buffering.

**Why 50,000 and not 100,000?** Because the demo needs to show that the buffer holds the *gap*, not the *total*. If we consumed `fast` all 100,000 items, `tee` would buffer 100,000 ints and the demo would conflate "total data size" with "gap". By consuming only 50,000 and leaving `slow` at 0, the buffer is exactly the 50,000-gap. The student who runs the demo and sees "~1.5 MiB at the islice line" understands that the buffer size is determined by the gap, not by the generator's total length. Doubling the gap (100,000 consumed, slow at 0) would double the buffer; halving the gap (25,000 consumed, slow at 0) would halve it. The rule: `tee`'s memory is O(gap), not O(total).

**Why is `tee` not free even when the input is "free"?** Because the buffer *is* the cost. The student who reads "tee lets you iterate a generator twice" concludes "tee is a free copy" — it's not. The "copy" is the buffer, and the buffer grows with the gap. The fix is to keep the forks *balanced*: if both consumers run at the same rate (e.g. via `asyncio.gather(consume_a(fork_a), consume_b(fork_b))`), the gap stays at 1 and `tee`'s memory is O(1). The lesson's commitment (in Engineering Trade-Offs below): `boardly` only uses `tee` when the consumers can be balanced; otherwise it falls back to `list(stream)` and accepts the O(n) memory cost — at least the cost is visible at the call site.

### Lines 83–87: The trap — `zip` silently truncates

```python
def zip_longest_demo() -> None:
    """zip_longest(*iterables, fillvalue=None): zip with fillvalue for unequal lengths."""
    # The bug: zip silently truncates to the shortest (3 pairs, 2 projects dropped)
    truncated = list(zip(projects, owners))
    print(f"zip(projects, owners) -> {len(truncated)} pairs (silently drops 2 projects)")
```

The bug demo: `zip(projects, owners)` zips the 5-project list with the 3-owner list, stopping at the shortest (3 pairs). The 2 extra projects (`Export`, `Billing`) are silently dropped — no error, no warning, just a 3-pair result instead of 5. The `print` line reports `3 pairs (silently drops 2 projects)`, making the bug visible; in production code, the bug is *invisible* because the truncation produces a valid-looking list. The student who runs the demo sees the truncation in the output and internalises "zip is silent on unequal lengths".

**Why does `zip` truncate instead of error?** Because `zip`'s contract is "yield while all iterables have items" — the moment any iterable is exhausted, `zip` stops. This is the *safe* default for the case where unequal lengths mean "the input was malformed and you should not pretend the missing data exists". For example, `zip(names, ages)` where the names list and ages list are *supposed* to be the same length: if they're not, you have a bug, and silently padding with `None` would hide the bug. `zip`'s truncation makes the bug visible — *if* you check the result length. The case for `zip_longest` is the case where missing data is *expected* (e.g. a sparse matrix, an optional second column), and you want to keep the missing positions explicit with a `fillvalue`.

### Lines 89–95: `zip_longest` — the fix with explicit `fillvalue`

```python
    # The fix: zip_longest pads to the longest with fillvalue
    padded = list(itertools.zip_longest(projects, owners, fillvalue=UNASSIGNED))
    print(f"zip_longest(projects, owners, fillvalue={UNASSIGNED!r}) -> {len(padded)} pairs:")
    for project, owner in padded:
        print(f"  P{project.id} {project.name:8} -> {owner}")
```

`itertools.zip_longest(*iterables, fillvalue=None)` zips the iterables, padding the shorter side(s) with `fillvalue` to the length of the *longest*. The result has 5 pairs — the first 3 have named owners (`alice`, `bob`, `carol`); the last 2 have the `UNASSIGNED` sentinel (`"unassigned"`). The `print` line reports `5 pairs`, and the loop prints each `(project, owner)` pair with the project ID, name, and owner. The 2 padded rows are explicit in the output: `P4 Export -> unassigned` and `P5 Billing -> unassigned`.

The `fillvalue` parameter is the lesson's key knob. The default is `None`, which is silent — a row of `None`s looks like real data (see the next block). The senior-engineer choice is to pass an explicit sentinel that *cannot* be confused with real data: a string like `"unassigned"` or `"MISSING"`, a sentinel object (`UNASSIGNED = object()`), or a domain-specific value (`0` for "no count", `""` for "no string"). The rule: never use the default `None` in production code unless you've explicitly reasoned about whether `None` is a valid data value.

**Why pass an explicit `fillvalue` instead of relying on the default `None`?** Three reasons. First, `None` is silent — a row of `(project, None)` looks identical to a row of `(project, some_owner)` in the output, and the bug "the owner is missing" is invisible. Second, `None` propagates — `(project, None).owner` raises `AttributeError` if anyone tries to access `.owner` on it; the bug surfaces as a downstream `AttributeError`, not at the `zip_longest` call site. Third, `None` is sometimes a valid data value (e.g. a project whose owner is genuinely `None` because the owner was deleted) — using `None` as the sentinel conflates "missing data" with "data that is None". An explicit sentinel like `"unassigned"` (or a sentinel object that *cannot* appear in the data) makes the missing-data case unambiguous.

### Lines 97–102: The default `fillvalue=None` is silent

```python
    # The default fillvalue=None is silent — looks like real data
    default_padded = list(itertools.zip_longest(projects, owners))
    print()
    print(f"zip_longest(projects, owners) (default fillvalue=None) -> last 2 pairs:")
    for project, owner in default_padded[-2:]:
        print(f"  P{project.id} {project.name:8} -> {owner!r}   (None — was that intentional?)")
```

The default demo: `zip_longest(projects, owners)` without a `fillvalue` uses the default `None`. The last 2 pairs are `(P4 Export, None)` and `(P5 Billing, None)` — the `None` is shown via `!r` so the student sees the literal `None` in the output. The comment `(None — was that intentional?)` calls out the silent-default trap: the student who reads this output has no way to know whether the `None` is "the project genuinely has no owner" or "the project's owner wasn't loaded yet" or "the data is broken".

This block is the lesson's warning. The student who writes `zip_longest(a, b)` without a `fillvalue` is silently opting into `None` as the sentinel — and `None` is the *worst* sentinel because it's a valid data value in most contexts. The senior-engineer rule: every `zip_longest` call site passes an explicit `fillvalue`. The default exists for backwards compatibility (the function was added in Python 2.6 with the default `None`), not because `None` is a good default.

### Lines 104–110: Three-way `zip_longest` with unequal lengths on every side

```python
    # Three-way zip_longest: projects + owners + status, all unequal lengths
    statuses = ["active", "active", "archived"]   # only 3 statuses; 2 missing
    tri = list(itertools.zip_longest(projects, owners, statuses, fillvalue="unknown"))
    print()
    print("zip_longest(projects, owners, statuses, fillvalue='unknown'):")
    for project, owner, status in tri:
        print(f"  P{project.id} {project.name:8} | owner={owner:10} | status={status}")
```

Three-way `zip_longest`: 5 projects, 3 owners, 3 statuses. The result is 5 triples; the last 2 have `(project, "unknown", "unknown")` because both `owners` and `statuses` are shorter than `projects`. The single `fillvalue="unknown"` is applied to *all* the missing positions — there's no per-side `fillvalue` in `zip_longest`'s API. If you need different fillvalues per side (e.g. `"unassigned"` for owners, `"inactive"` for statuses), you post-process: `[(p, o if o is not None else "unassigned", s if s is not None else "inactive") for p, o, s in itertools.zip_longest(projects, owners, statuses)]`. The lesson's commitment: use a single `fillvalue` when one sentinel fits all sides; post-process when it doesn't.

### Lines 113–118: `main` and the entry point

```python
def main() -> None:
    print("=== tee: fork the single-pass iterator ===")
    tee_demo()
    print()
    print("=== zip_longest: zip unequal-length iterables ===")
    zip_longest_demo()


if __name__ == "__main__":
    main()
```

Standard boardly entry point. The `tee_demo` runs first (with the memory-growth sub-demo), then `zip_longest_demo` runs. The blank line between sections makes the two demos visually distinct.

## Execution Trace

```bash
$ uv run python boardly/itertools_tee_zip_longest_demo.py
=== tee: fork the single-pass iterator ===
metrics — tickets by status: {'in_progress': 1, 'todo': 2, 'blocked': 2, 'done': 1}
persist — 6 rows: [101, 102, 103, 104, 105, 106]

memory-growth demo: tee with islice and a 50,000-gap fork
  slow's next value after fast advanced 50,000: 0
  (the buffer holds the 50,000 ints slow hasn't read yet)
  top allocation delta: 1554 KiB at <demo-file>:71
    list(itertools.islice(fast, 50_000))

=== zip_longest: zip unequal-length iterables ===
zip(projects, owners) -> 3 pairs (silently drops 2 projects)
zip_longest(projects, owners, fillvalue='unassigned') -> 5 pairs:
  P1 Search   -> alice
  P2 Auth     -> bob
  P3 Docs     -> carol
  P4 Export   -> unassigned
  P5 Billing  -> unassigned

zip_longest(projects, owners) (default fillvalue=None) -> last 2 pairs:
  P4 Export   -> None   (None — was that intentional?)
  P5 Billing  -> None   (None — was that intentional?)

zip_longest(projects, owners, statuses, fillvalue='unknown'):
  P1 Search   | owner=alice      | status=active
  P2 Auth     | owner=bob        | status=active
  P3 Docs     | owner=carol      | status=archived
  P4 Export   | owner=unknown    | status=unknown
  P5 Billing  | owner=unknown    | status=unknown
```

The first block shows `tee` forking the generator. The metrics consumer sees all 6 tickets and counts them by status: `in_progress: 1, todo: 2, blocked: 2, done: 1` (sum = 6). The persistence consumer sees all 6 tickets and collects their IDs: `[101, 102, 103, 104, 105, 106]`. The two forks are *independent* — neither consumer's iteration affected the other's view. The memory-growth sub-demo shows `slow`'s next value is `0` after `fast` advanced 50,000 — confirming `slow`'s view is intact — and `tracemalloc` reports ~1.5 MiB of allocations at the `islice` line, which is the 50,000 `int` objects `tee` is buffering for `slow`.

The second block shows `zip` vs `zip_longest`. `zip(projects, owners)` produces 3 pairs and silently drops the 2 extra projects; `zip_longest(projects, owners, fillvalue='unassigned')` produces 5 pairs, padding the last 2 with the explicit `"unassigned"` sentinel. The default-`fillvalue=None` demo shows the silent trap: the last 2 pairs have `None` as the owner, and the comment `(None — was that intentional?)` calls out the ambiguity. The three-way `zip_longest` produces 5 triples, with the last 2 having `"unknown"` for both owner and status.

The `tracemalloc` output line will vary slightly across runs (the exact KiB and the `<string>:N` line number depend on the Python build and the snapshot internals) — the *order of magnitude* (1,000–2,000 KiB, i.e. ~1.5 MiB) is the stable signal. The lesson's commitment is that the student sees the buffer growth, not that they see an exact KiB value.

## Common Mistakes

### Mistake 1: Reusing the original iterable after `tee`

```python
import itertools
src = iter([10, 20, 30, 40])
p, q = itertools.tee(src, 2)
print(next(p))   # 10  — p pulls from the shared upstream
print(next(src)) # 20  — STEALS 20 from the shared upstream
print(next(q))   # 10  — q sees the buffered 10
print(next(q))   # 30  — 20 was stolen by src; tee gives q the next buffered value (30)
```

**Symptom:** One fork yields values out of order, or skips values, or yields `StopIteration` earlier than expected. The bug is invisible until you compare the two forks' outputs side by side.

**Why:** `tee` wraps the original iterable in a shared buffer. When you call `next(p)`, `tee` either pulls from the buffer (if `p` is behind) or pulls from the original iterable and pushes the value into the buffer (if `p` is the most-advanced fork). Calling `next(src)` directly pulls from the original iterable *without* pushing into the buffer — the value is "stolen" from the forks' shared upstream. The forks then see a gap where the stolen value should have been, and the bug surfaces as missing or out-of-order values.

**Fix:** Once you've called `tee(iterable, n)`, *do not use* `iterable` again. The contract is: `tee` owns the iterable from the moment you call it; the n returned forks are the only legitimate consumers. If you need to iterate the original iterable, do it *before* calling `tee`. The CPython documentation is explicit: "Once a `tee()` has been started, the original iterable should not be used anywhere else; otherwise, the iterable could get advanced without the tee objects being informed."

### Mistake 2: `tee` with one fork fully drained before the other starts (memory blow-up)

```python
import itertools
def big_gen():
    for i in range(10_000_000):
        yield i
a, b = itertools.tee(big_gen(), 2)
# Drain 'a' fully before 'b' starts — tee buffers all 10,000,000 ints
list(a)                    # 10M ints buffered
first_from_b = next(b)     # 0 — but the 10M-int buffer is still live
```

**Symptom:** Memory usage spikes to ~400 MiB (10M ints × ~28 bytes each plus list overhead) while the first consumer drains its fork, then stays high until the second consumer catches up. The whole point of using a generator (don't materialise) is defeated.

**Why:** `tee`'s buffer holds every item between the most-advanced fork and the least-advanced fork. If `a` is fully drained (advanced 10M) and `b` hasn't started (advanced 0), the buffer holds 10M items. The buffer *is* the materialisation you were trying to avoid.

**Fix:** Run the two consumers *concurrently* — via `asyncio.gather(consume_a(a), consume_b(b))`, `threading.Thread(target=consume_a, args=(a,)).start()`, or `concurrent.futures`. The buffer's gap stays at 1 if both consumers run at the same rate. If concurrency is impossible (e.g. one consumer *must* finish before the other starts), `tee` is the wrong tool — use `list(stream)` and accept the O(n) memory cost explicitly, or restructure the pipeline so a single consumer does both jobs in one pass.

### Mistake 3: `zip_longest` with the default `fillvalue=None`

```python
import itertools
# Bug: default fillvalue=None is silent — looks like real data
result = list(itertools.zip_longest([1, 2, 3], [10, 20]))
# result == [(1, 10), (2, 20), (3, None)]   # None is invisible in production logs
# Downstream: sum(r[1] for r in result) raises TypeError (None + int)
```

**Symptom:** The padded rows have `None` where you expected a real value; downstream code that assumes a non-`None` value (e.g. `r[1] + 1`, `r.owner.name`) raises `TypeError` or `AttributeError` at runtime.

**Why:** `zip_longest`'s default `fillvalue=None` was chosen for backwards compatibility with Python 2.6, when the function was added. `None` is a *valid data value* in most contexts (e.g. a nullable owner field), so using it as the "missing data" sentinel conflates "data is missing" with "data is None". The bug surfaces downstream — the `zip_longest` call site looks fine, the consumer blows up.

**Fix:** Always pass an explicit `fillvalue` that *cannot* appear in the real data. For string fields: `"unassigned"`, `"unknown"`, `"MISSING"`. For numeric fields: a sentinel like `-1` (if non-negative is the contract) or `float('nan')` (if NaN-checking is in place). For objects: a sentinel `MISSING = object()` that has identity-equality only. The rule: the `fillvalue` should be distinguishable from real data by *type* or by *value*, not by convention.

## Engineering Trade-Offs

**Decision:** Use `tee` only when the input is a single-pass iterator and the consumers can be kept *balanced* (gap = O(1)); otherwise use `list(stream)` and accept the O(n) memory cost. Use `zip_longest` with an *explicit* `fillvalue` whenever the input iterables may have unequal lengths and the missing positions are expected (not a bug); use `zip` when unequal lengths are a bug to surface.

**Both sides:** The alternative to `tee` is `list(stream)` — materialise once, iterate twice. `list` wins when the data is small (the materialisation is cheap), when the consumers must run sequentially (one fully drains before the other starts — `tee`'s buffer would balloon), or when the input is already a sequence (you can iterate it twice for free). `tee` wins when the data is large (materialisation is expensive), the consumers can be balanced (the buffer stays small), and the input is single-pass (a list would defeat the laziness). The alternative to `zip_longest` is `zip` — truncate to the shortest. `zip` wins when unequal lengths are a bug (the truncation surfaces the bug, *if* you check the length); `zip_longest` wins when unequal lengths are expected and the missing positions need an explicit sentinel.

**Commitment:** `boardly` uses `tee` in `boardly/tickets/forked_pipeline.py` for the two-consumer metrics-and-persist fork (the call site is `rows_for_metrics, rows_for_persist = tee(ticket_rows(), 2)`, paired with an `asyncio.gather` that runs both consumers concurrently to keep the gap at O(1)). `boardly` uses `zip_longest` in `boardly/projects/owner_assignments.py` for the project-owner join (the call site is `zip_longest(projects, owners, fillvalue=UNASSIGNED)`, with `UNASSIGNED = "unassigned"` as a module-level sentinel). The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to: (1) `tee` only with concurrent consumers, (2) `zip_longest` always with an explicit `fillvalue`, (3) the original iterable never used after `tee`. The hand-written fork-the-list form (`rows = list(stream); for_a = iter(rows); for_b = iter(rows)`) is explicitly banned for streams larger than 1,000 rows.

**Why ban the hand-written fork-the-list form?** Because the form silently defeats the laziness of the generator. The student who writes `rows = list(stream); consume_a(iter(rows)); consume_b(iter(rows))` has materialised the entire stream into a list — the `iter(rows)` calls produce fresh iterators over the *list*, not over the original stream. For a 1,000-row stream, fine. For a 1,000,000-row stream, the list is 8 MB+ of memory that didn't need to exist. `tee(stream, 2)` *with balanced consumers* keeps the memory at O(1); `list(stream)` is O(n) regardless. The senior-engineer rule: if the stream is large and the consumers are concurrent, `tee` wins; if the stream is small or the consumers are sequential, `list` wins — and the choice should be explicit at the call site, not hidden behind a "just iterate twice" idiom.

## Exercises

1. **Exercise 1 — Increase the gap.** In the memory-growth demo, change `list(itertools.islice(fast, 50_000))` to `list(itertools.islice(fast, 100_000))` and re-run. Verify the top allocation delta roughly doubles (to ~3,000 KiB). Then change it to `25_000` and verify it halves. This exercise demonstrates that the buffer size is O(gap), not O(total). `Verify: uv run python boardly/itertools_tee_zip_longest_demo.py`

2. **Exercise 2 — Replace `tee` with `list`.** Rewrite the basic fork as `rows = list(ticket_rows())` and iterate `rows` twice (once for metrics, once for persistence). Verify the output is identical. Then articulate: `list(stream)` materialises the entire stream up front (O(n) memory, always); `tee(stream, 2)` with sequential consumers materialises on demand but the buffer still grows to O(n) because the first consumer drains fully before the second starts. The two forms have the *same* memory profile in the sequential case; `tee` only wins in the concurrent case. `Verify: uv run python boardly/itertools_tee_zip_longest_demo.py`

3. **Exercise 3 — Demonstrate the "don't reuse the original" trap.** Add a small script that calls `src = iter([10, 20, 30, 40]); p, q = tee(src, 2); print(next(p)); print(next(src)); print(next(q)); print(next(q))`. Predict the output before running. Verify that `q` yields `10, 30, 40` (skipping `20`, which `src` stole). This exercise makes the trap visible in the output. `Verify: uv run python boardly/itertools_tee_zip_longest_demo.py`

4. **Exercise 4 — Replace `zip_longest` with `zip` and surface the bug.** Rewrite `padded = list(itertools.zip_longest(projects, owners, fillvalue=UNASSIGNED))` as `padded = list(zip(projects, owners))`. Verify the output drops the last 2 projects — and that no error is raised. Then articulate: the silent truncation is the bug; the explicit `zip_longest` with a sentinel is the fix. `Verify: uv run python boardly/itertools_tee_zip_longest_demo.py`

5. **Exercise 5 — Per-side fillvalues.** Build a `zip_with_per_side_fillvalues(iterables, fillvalues)` helper that wraps `zip_longest` and post-processes the result to apply a different `fillvalue` per side. Use it to zip `projects` (fillvalue=`None` because all 5 are present), `owners` (fillvalue=`"unassigned"`), and `statuses` (fillvalue=`"inactive"`). Verify the last 2 rows have `(P4 Export, unassigned, inactive)` and `(P5 Billing, unassigned, inactive)`. This exercise demonstrates the composition of `zip_longest` with a post-processing step — the standard pattern when one sentinel doesn't fit all sides. `Verify: uv run python boardly/itertools_tee_zip_longest_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_tee_zip_longest_demo.py
=== tee: fork the single-pass iterator ===
metrics — tickets by status: {'in_progress': 1, 'todo': 2, 'blocked': 2, 'done': 1}
persist — 6 rows: [101, 102, 103, 104, 105, 106]

memory-growth demo: tee with islice and a 50,000-gap fork
  slow's next value after fast advanced 50,000: 0
  (the buffer holds the 50,000 ints slow hasn't read yet)
  top allocation delta: 1554 KiB at <demo-file>:71
    list(itertools.islice(fast, 50_000))

=== zip_longest: zip unequal-length iterables ===
zip(projects, owners) -> 3 pairs (silently drops 2 projects)
zip_longest(projects, owners, fillvalue='unassigned') -> 5 pairs:
  P1 Search   -> alice
  P2 Auth     -> bob
  P3 Docs     -> carol
  P4 Export   -> unassigned
  P5 Billing  -> unassigned

zip_longest(projects, owners) (default fillvalue=None) -> last 2 pairs:
  P4 Export   -> None   (None — was that intentional?)
  P5 Billing  -> None   (None — was that intentional?)

zip_longest(projects, owners, statuses, fillvalue='unknown'):
  P1 Search   | owner=alice      | status=active
  P2 Auth     | owner=bob        | status=active
  P3 Docs     | owner=carol      | status=archived
  P4 Export   | owner=unknown    | status=unknown
  P5 Billing  | owner=unknown    | status=unknown
```

Note: the exact `tracemalloc` line number and KiB value will vary across Python builds and snapshot internals — the stable signal is the order of magnitude (~1,000–2,000 KiB, i.e. ~1.5 MiB) at the `list(islice(fast, 50_000))` line. The student should see the buffer growth, not a specific KiB value.

## Previously Learned Here

- [[07-itertools/05-cycle-repeat-count]] — the three infinite iterators. The laziness model from that lesson is the foundation for this one's "tee is not free" memory demo: `cycle`/`repeat`/`count` are infinite, and `tee`'s buffer would grow without bound if one fork advanced and the other never caught up.
- [[07-itertools/06-dropwhile-takewhile-filterfalse]] — the predicate filters. The `zip_longest` demo's fixture reuses the same `Ticket` shape and `WATCH`-set-style sentinel pattern from that lesson.
- [[04-collections/03-deque]] — `deque` is the C-accelerated queue that `tee`'s internal buffer is modelled on. The cross-link matters: `tee`'s buffer is essentially a queue of unconsumed items, and the memory cost is the same kind of cost `deque` teaches.

## What's Next

You've reached the end of the seven-lesson `itertools` spine. The natural next step is [[08-pathlib/00-pathlib-MOC]] — `pathlib` is the standard-library module for filesystem paths as objects, and it pairs with `itertools.chain.from_iterable` for the "walk a directory tree lazily" pattern (`chain.from_iterable(p.glob("*.py") for p in path.rglob("src"))`).

- `pathlib.Path` — the filesystem-path-as-object that replaces `os.path.join` and `os.path.exists`.
- `chain.from_iterable` + `Path.rglob` — the lazy directory-walk composition across the `pathlib` section.
- The boardly `forked_pipeline` pattern — production use of `tee` with concurrent consumers.

## Sources

- **`itertools` — Functions creating iterators for efficient looping** — https://docs.python.org/3/library/itertools.html — accessed 2026-10-23 — the canonical reference for `tee`, `zip_longest`, and the rest of the `itertools` family.
- **`itertools.tee`** — https://docs.python.org/3/library/itertools.html#itertools.tee — accessed 2026-10-23 — the fork-the-iterator function; documents the "once tee has been started, the original iterable should not be used elsewhere" rule and the memory-cost warning.
- **`itertools.zip_longest`** — https://docs.python.org/3/library/itertools.html#itertools.zip_longest — accessed 2026-10-23 — the unequal-length zip; documents the `fillvalue` parameter and the default `None` behaviour.
- **`zip`** — https://docs.python.org/3/library/functions.html#zip — accessed 2026-10-23 — the builtin that truncates to the shortest; the contrast case for `zip_longest`.
- **`tracemalloc`** — https://docs.python.org/3/library/tracemalloc.html — accessed 2026-10-23 — the standard-library memory profiler used in the "tee is not free" demo to measure the buffer growth.

## What We Learned

- You can apply `itertools.tee(iterable, n=2)` — split a single-pass iterator into n independent forks that each see the full sequence.
- You can state the "tee is not free" rule — `tee` caches the input; the buffer's size is O(gap between forks), not O(total data).
- You can avoid the "don't reuse the original" trap — after `tee`, the original iterable must not be used; doing so steals values from the shared upstream.
- You can apply `itertools.zip_longest(*iterables, fillvalue=None)` — zip unequal-length iterables, padding to the longest with `fillvalue`.
- You can distinguish `zip` (truncate to shortest, silent) from `zip_longest` (pad to longest, explicit `fillvalue`) and choose based on whether missing data is a bug or expected.
