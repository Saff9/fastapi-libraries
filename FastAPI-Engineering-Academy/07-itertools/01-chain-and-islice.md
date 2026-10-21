---
title: "Lesson 01: chain & islice"
aliases:
 - itertools.chain
 - itertools.islice
 - chain.from_iterable
tags:
 - itertools
 - chain
 - islice
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[05-collections-abc/04-Iterator-vs-Iterable]]"
 - "[[04-collections/03-deque]]"
related_lessons:
 - "[[07-itertools/02-groupby]]"
 - "[[07-itertools/03-starmap-and-accumulate]]"
 - "[[04-collections/03-deque]]"
first_taught_in: "07-itertools/01-chain-and-islice"
---

# Lesson 01: `chain` & `islice`

*The two lazy-iterator primitives that let `boardly` page through a million-row ticket stream without materialising a single slice — `chain(*iterables)` flattens, `islice(iterable, start, stop, step)` slices, and both stay O(1) in memory.*

**You're at the very beginning of Section 07.**

`itertools` is the standard-library module that senior engineers reach for whenever a `for` loop has to walk a stream too big to fit in memory, or a slice too wide to copy. The two primitives you will meet first are `chain` and `islice`. `chain("AB", "CD")` yields `A, B, C, D` without first concatenating the inputs into one big list. `islice(stream, 0, 10, 2)` yields every other element of the first ten — without first slicing `stream[:10]` into a fresh list. Both are C-accelerated, both are one-shot iterators, and both teach the lesson the rest of `itertools` keeps repeating: *don't materialise what you can stream*. By the end of this lesson you will know how to flatten a list-of-iterables lazily, how to slice an infinite generator without crashing, and why `islice` refuses negative indices. Take your time. Type every example. **This is how you learn.**

#itertools #chain #islice #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.chain(*iterables)`** to concatenate two or more iterables into a single lazy stream — without first building a combined list.
2. **Apply `itertools.chain.from_iterable(iterables)`** to flatten a single iterable-of-iterables one level deep — the fast path when the inputs come from a generator.
3. **Apply `itertools.islice(iterable, stop)` and `islice(iterable, start, stop, step=1)`** to slice any iterator lazily — and articulate why negative indices are forbidden.
4. **Measure the memory win** of `islice(stream, n)` over `list(stream)[:n]` on a million-row stream.
5. **Choose between `islice` and `collections.deque(..., maxlen=n)`** based on whether you want a *prefix* or a *sliding window* of the stream.

## Prerequisites

Before starting, you need:

- **The iterator/iterable distinction** — an `iterable` produces a fresh `iterator` on each `iter()` call; an `iterator` is one-shot. See [[05-collections-abc/04-Iterator-vs-Iterable]] for the canonical explanation.
- **`collections.deque` with `maxlen`** — the sliding-window primitive that `islice` cannot replace. See [[04-collections/03-deque]].
- **About 20–30 minutes of focused time.**

**The most common gap: treating an iterator like a list.**

Students who haven't internalised the iterator/iterable distinction reach for `list(stream)[:10]` to peek at the first ten items. That materialises the entire stream into a list just to throw away everything past index ten — a memory cost that is harmless on a hundred-row stream and fatal on a million-row stream. `islice(stream, 10)` is the senior-engineer move: yield the first ten, then stop, never build the list. The mental shift this lesson teaches is to *trust laziness* — let the iterator produce only what you ask for.

## The Problem

You ship `boardly/api/tickets_feed.py` — a paginated endpoint that streams `Ticket` rows out of the database, joins them with the parent `Project` name, and returns the first 50 rows to the client. The first version reads naturally:

```python
def feed_v1(project_ids: list[UUID]) -> list[dict]:
    rows: list[dict] = []
    for pid in project_ids:
        for t in db.tickets_for(pid):
            rows.append({"id": t.id, "title": t.title, "project": pid})
    return rows[:50]
```

Three problems. First, you build `rows` for every ticket in every project before you slice `[:50]`. If two projects each have 10,000 tickets, you materialise 20,000 dicts to return 50. Second, the slice `rows[:50]` builds yet another list of 50 dicts — you pay the construction cost twice. Third, the code only works because `db.tickets_for(pid)` returns a list. The day you swap it for a generator (to stream from the DB cursor), `rows[:50]` still forces a full materialisation — the laziness is lost at the slice step.

`itertools.chain` and `itertools.islice` solve all three. `chain(*[db.tickets_for(pid) for pid in project_ids])` yields one lazy stream across all projects without concatenating. `islice(stream, 50)` yields the first fifty tickets and stops — the database cursor is closed after the fiftieth row, not after the last row of the last project. Memory cost goes from O(total tickets) to O(50). The endpoint streams the database instead of loading it.

## The Code

```python
# boardly/itertools_chain_islice_demo.py
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


def chain_two_iterables() -> None:
    """chain(*iterables) concatenates without building a combined list."""
    stream = itertools.chain(tickets_a, tickets_b)
    print("chain(tickets_a, tickets_b) — first 2 titles:")
    for t in itertools.islice(stream, 2):
        print(f"  {t.title}")
    # The remaining tickets are still in the stream, untouched:
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

    # Compare with chain(*pages): both work, but *pages unpacks the list
    # eagerly; from_iterable accepts any iterable, including a generator.
    stream2 = itertools.chain.from_iterable(
        tickets_for(p) for p in projects
    )
    print("from_iterable(generator) — works where chain(*gen) would explode:")
    for t in stream2:
        print(f"  {t.title}")


def tickets_for(project: Project) -> list[Ticket]:
    """Trivial dispatcher — pretend this hits the DB cursor per project."""
    return tickets_a if project.id == proj_a.id else tickets_b


def islice_prefix_and_step() -> None:
    """islice(iterable, stop) and islice(iter, start, stop, step) — lazy slice."""
    stream = itertools.chain(tickets_a, tickets_b)
    # First three only — never builds a list of all six just to slice [:3]
    first_three = list(itertools.islice(stream, 3))
    print("islice(stream, 3) ->", [t.title for t in first_three])

    # The remaining stream still has three tickets
    rest = list(stream)
    print("rest of stream ->", [t.title for t in rest])

    # Step form: every other element from a 10-element range
    every_other = list(itertools.islice(range(10), 0, 10, 2))
    print("islice(range(10), 0, 10, 2) ->", every_other)


def islice_rejects_negative_indices() -> None:
    """Negative start/stop/step raise ValueError — the gotcha."""
    try:
        list(itertools.islice(range(10), -1))
    except ValueError as e:
        print("islice(range(10), -1) ->", e)

    # Sliding window of the last N items — use deque(maxlen=N), not islice
    stream = (f"row-{i}" for i in range(10))
    last_three = deque(stream, maxlen=3)
    print("last 3 via deque(maxlen=3) ->", list(last_three))


def memory_win_vs_list_slice() -> None:
    """islice(stream, 50) vs list(stream)[:50] — same result, different cost."""
    def big_stream(n: int):
        for i in range(n):
            yield {"id": i, "title": f"ticket-{i}"}

    # The islice path: yield exactly 3 items, stop, never build the rest
    head = list(itertools.islice(big_stream(1_000_000), 3))
    print("islice(big_stream(1_000_000), 3) ->", [h["title"] for h in head])

    # The list-slice path: build a million-item list to keep three
    # Don't actually run it — would burn ~80 MB of RAM. The point is
    # that list(big_stream(N))[:k] allocates the full N regardless of k.
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
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/itertools_chain_islice_demo.py
"""Demonstrate chain, chain.from_iterable, and islice on boardly streams."""
from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass
from uuid import UUID, uuid4
```

`itertools` is the star — it exposes `chain`, `chain.from_iterable`, `islice`, and the rest of the lazy-iterator algebra covered across the section. `collections.deque` is the sliding-window primitive that `islice` cannot be — the lesson's closing comparison uses it. `dataclass` builds frozen value objects so the demo is offline and reproducible, and `UUID`/`uuid4` give us stable identifiers without a database. `from __future__ import annotations` stringifies annotations — boardly house style, see [[13-future/01-from-future-import-annotations]].

### Lines 13–28: The boardly models

```python
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
```

Two frozen dataclasses. `frozen=True` makes the instances hashable and immutable — meaning a `Ticket` can be a set member, a dict key, and (crucially for `itertools.groupby` in [[07-itertools/02-groupby]]) survives being a key in a `groupby` without being mutated mid-iteration. The shape matches the `boardly/models.py` contract from [[18-operator/01-itemgetter-attrgetter]]: same `Ticket` with `id`, `project_id`, `title`, `status`; same `Project` with `id`, `name`. Continuity across the section is the design — the same models reappear so you can focus on the new primitive.

### Lines 31–51: The fixture

```python
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
```

Two projects, three tickets each. `ticket_batches()` returns the two ticket lists wrapped in an outer list — the shape `db.fetch_pages()` would return if it batched a cursor. The fixture is at module scope so `main()` and every helper see the same data. The two `tickets_a` / `tickets_b` lists are deliberately *separate* iterables because `chain` is about joining separate iterables — the demo needs at least two streams to chain.

### Lines 60–72: `chain(*iterables)` — concatenation without a combined list

```python
def chain_two_iterables() -> None:
    """chain(*iterables) concatenates without building a combined list."""
    stream = itertools.chain(tickets_a, tickets_b)
    print("chain(tickets_a, tickets_b) — first 2 titles:")
    for t in itertools.islice(stream, 2):
        print(f"  {t.title}")
    # The remaining tickets are still in the stream, untouched:
    print("rest of the stream:")
    for t in stream:
        print(f"  {t.title}")
```

`itertools.chain(tickets_a, tickets_b)` returns a single iterator. Internally — you can read this in `Modules/itertoolsmodule.c` in the CPython source — `chain` stores the tuple of input iterables in C-level state and walks them in order: it pulls from `tickets_a` until `StopIteration`, then moves to `tickets_b`. There is no concatenation step. `tickets_a + tickets_b` would build a fresh list of six `Ticket` objects (allocating, copying, paying the cost); `chain` yields from each input in place, with O(1) overhead per yielded item.

The `islice(stream, 2)` call yields the first two tickets, then stops — without consuming the rest. The subsequent `for t in stream` loop picks up where `islice` left off: tickets 3, 4, 5, 6. This is the senior-engineer pattern: *peek at the prefix, then resume*. `list(stream)` would force-consume the rest into a list and lose the laziness.

**Why does `chain` exist when `a + b` works for lists?** Three reasons. First, `a + b` requires both inputs to be concrete sequences — it allocates a fresh list and copies every element. `chain` works on any iterables, including one-shot generators and infinite streams. Second, `chain` is O(1) in memory: it stores only the *iterators* over the inputs, not the elements themselves; `a + b` is O(len(a) + len(b)) in memory. Third, `chain` is composable — `chain(chain(a, b), c)` builds a single lazy stream that walks `a`, then `b`, then `c`; the equivalent `a + b + c` allocates two intermediate lists before producing the final one. On a hundred-row stream the difference is invisible; on a million-row stream it is the difference between 8 MB and 8 GB.

### Lines 75–95: `chain.from_iterable` — the fast path for a list-of-iterables

```python
def chain_from_iterable_flattens_one_level() -> None:
    """chain.from_iterable(iterable_of_iterables) is the fast path."""
    pages = ticket_batches()
    stream = itertools.chain.from_iterable(pages)
    print("from_iterable(pages) — all ticket titles, flattened:")
    for t in stream:
        print(f"  {t.title}")

    # Compare with chain(*pages): both work, but *pages unpacks the list
    # eagerly; from_iterable accepts any iterable, including a generator.
    stream2 = itertools.chain.from_iterable(
        tickets_for(p) for p in projects
    )
    print("from_iterable(generator) — works where chain(*gen) would explode:")
    for t in stream2:
        print(f"  {t.title}")
```

`chain.from_iterable(pages)` is the class-method form: it takes a *single* iterable-of-iterables and flattens it one level deep. `pages` is `[[t1, t2, t3], [t4, t5, t6]]`; the result yields `t1, t2, t3, t4, t5, t6`. The crucial difference from `chain(*pages)` is that `*pages` unpacks the list eagerly at call time — Python has to materialise the entire `pages` list (or generator) before `chain` even starts. `from_iterable` accepts the outer iterable lazily; if the outer iterable is itself a generator that yields ten million sub-iterables, `from_iterable` walks them one at a time without ever holding all ten million in memory.

The `stream2` example is the case where `from_iterable` is the only choice. `tickets_for(p) for p in projects` is a generator expression — you cannot `*`-unpack a generator into `chain(*gen)` because unpacking consumes the entire generator into a tuple first. `from_iterable(gen)` accepts the generator as-is and lazily yields the next sub-iterable only after the previous one is exhausted.

**Why does `from_iterable` exist as a class method, not a separate function?** Historical and ergonomic. The `itertools` module was originally a recipe collection (see the `itertools` recipes at the end of the docs page); `chain.from_iterable` was added later as the "real" flatten-one-level primitive, and the CPython maintainers chose to attach it to `chain` as a class method to avoid polluting the module namespace with a second name (`flatten` would have been the obvious name, but `flatmap` and `flatten` had competing meanings in other languages). The class-method form also reads well at the call site: `chain.from_iterable(...)` makes the "this is the chain fast path" intent obvious.

### Lines 105–119: `islice` — prefix and step

```python
def islice_prefix_and_step() -> None:
    """islice(iterable, stop) and islice(iter, start, stop, step) — lazy slice."""
    stream = itertools.chain(tickets_a, tickets_b)
    # First three only — never builds a list of all six just to slice [:3]
    first_three = list(itertools.islice(stream, 3))
    print("islice(stream, 3) ->", [t.title for t in first_three])

    # The remaining stream still has three tickets
    rest = list(stream)
    print("rest of stream ->", [t.title for t in rest])

    # Step form: every other element from a 10-element range
    every_other = list(itertools.islice(range(10), 0, 10, 2))
    print("islice(range(10), 0, 10, 2) ->", every_other)
```

`islice` has two call shapes. `islice(iterable, stop)` yields the first `stop` items and then raises `StopIteration` — equivalent to `iterable[:stop]` for a list, but it works on any iterable. `islice(iterable, start, stop, step=1)` yields items `[start, start+step, start+2*step, ...)` up to (but not including) `stop` — equivalent to `iterable[start:stop:step]`. Internally `islice` walks the underlying iterator item-by-item, counting the index, and yields only the items whose index falls in the requested slice. The items before `start` are *discarded* (pulled and dropped), so the underlying iterator advances past them — `islice` cannot rewind.

The crucial behaviour shown here: after `islice(stream, 3)` consumes the first three tickets, the underlying `stream` is now positioned at the fourth ticket. The subsequent `list(stream)` collects tickets 4, 5, 6 — not 1, 2, 3 again. `islice` does not return a fresh iterator over the original stream; it operates *on* the iterator you pass in. This is the laziness win: peek at the prefix, then keep streaming. The list-slice equivalent `list(stream)[:3]` would materialise all six, slice, and discard the last three — losing the streaming property entirely.

The step form `islice(range(10), 0, 10, 2)` yields `0, 2, 4, 6, 8`. Internally `islice` pulls `0`, yields; pulls `1`, discards; pulls `2`, yields; and so on. There is no way to "skip" elements without pulling them — the underlying iterator's `__next__` is the only way to advance.

### Lines 122–134: `islice` rejects negative indices — the gotcha

```python
def islice_rejects_negative_indices() -> None:
    """Negative start/stop/step raise ValueError — the gotcha."""
    try:
        list(itertools.islice(range(10), -1))
    except ValueError as e:
        print("islice(range(10), -1) ->", e)

    # Sliding window of the last N items — use deque(maxlen=N), not islice
    stream = (f"row-{i}" for i in range(10))
    last_three = deque(stream, maxlen=3)
    print("last 3 via deque(maxlen=3) ->", list(last_three))
```

`islice(range(10), -1)` raises `ValueError: Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.` This is the gotcha: `islice` looks like a slice, behaves like a slice for non-negative arguments, and breaks the moment you reach for a negative index. The reason is structural: `islice` walks the iterator forward only. `iterable[-1]` on a list means "the last element"; to compute "the last element" of a forward-only iterator, you have to consume the entire iterator and remember the last one — `islice` refuses to silently do that work, because it would defeat the laziness contract.

**Why not just raise IndexError or return an empty iterator?** Because returning an empty iterator would silently hide the bug — you'd write `islice(stream, -3)` expecting the last three items, get an empty result, and ship a feature that does nothing. Raising `ValueError` at call time forces you to confront the question: do you actually want a *prefix* (use `islice(stream, n)`) or a *suffix* (use `deque(stream, maxlen=n)`)? These are different operations with different memory costs: the prefix is O(n) in memory (you hold the prefix), the suffix is O(n) in memory (you hold the last n via a `deque` of size `n`), but the suffix requires consuming the entire stream — which `islice` refuses to do silently.

The `deque(stream, maxlen=3)` pattern is the standard-library answer to "the last N items of a stream". The `deque` keeps a circular buffer of size `maxlen`; every `append` after the third evicts the oldest entry. By the time the stream is exhausted, the `deque` holds exactly the last three items — `list(deque)` gives you them in order. This is the sliding-window primitive; see [[04-collections/03-deque]] for the canonical treatment.

### Lines 137–148: The memory win

```python
def memory_win_vs_list_slice() -> None:
    """islice(stream, 50) vs list(stream)[:50] — same result, different cost."""
    def big_stream(n: int):
        for i in range(n):
            yield {"id": i, "title": f"ticket-{i}"}

    # The islice path: yield exactly 3 items, stop, never build the rest
    head = list(itertools.islice(big_stream(1_000_000), 3))
    print("islice(big_stream(1_000_000), 3) ->", [h["title"] for h in head])

    # The list-slice path: build a million-item list to keep three
    # Don't actually run it — would burn ~80 MB of RAM. The point is
    # that list(big_stream(N))[:k] allocates the full N regardless of k.
    print("list(big_stream(1_000_000))[:3] would allocate 1,000,000 dicts")
```

`big_stream(1_000_000)` is a generator that would yield a million dicts if consumed. `islice(big_stream(1_000_000), 3)` consumes exactly three dicts — the generator function's frame is paused at `yield` after the third item, and the rest of the million are never built. Memory cost: O(3). `list(big_stream(1_000_000))[:3]` would materialise a million dicts (~80 MB at 80 bytes per dict), then slice to a fresh list of three, then discard the million. Memory cost: O(1,000,000). Same result, four orders of magnitude difference in RAM.

The print statement at the bottom deliberately does *not* run the list-slice form — running it would burn 80 MB of RAM on a demo machine for no pedagogical gain. The comment is the lesson: `list(stream)[:k]` allocates the full N regardless of k, so the cost is bounded by the stream length, not by the slice length. `islice(stream, k)` is bounded by k. The principle generalises: *if you only need a prefix of a stream, never materialise the stream first*.

## Execution Trace

```bash
$ uv run python boardly/itertools_chain_islice_demo.py
=== chain: two iterables ===
chain(tickets_a, tickets_b) — first 2 titles:
  Login fails on Safari
  OAuth callback loops
rest of the stream:
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI

=== chain.from_iterable: flatten one level ===
from_iterable(pages) — all ticket titles, flattened:
  Login fails on Safari
  OAuth callback loops
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI
from_iterable(generator) — works where chain(*gen) would explode:
  Login fails on Safari
  OAuth callback loops
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI

=== islice: prefix and step ===
islice(stream, 3) -> ['Login fails on Safari', 'OAuth callback loops', 'Docs typo in /login']
rest of stream -> ['Index out of range on /search', 'Synonym expansion slow', 'Add filter UI']
islice(range(10), 0, 10, 2) -> [0, 2, 4, 6, 8]

=== islice: rejects negative indices ===
islice(range(10), -1) -> Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.
last 3 via deque(maxlen=3) -> ['row-7', 'row-8', 'row-9']

=== memory win: islice vs list-slice ===
islice(big_stream(1_000_000), 3) -> ['ticket-0', 'ticket-1', 'ticket-2']
list(big_stream(1_000_000))[:3] would allocate 1,000,000 dicts
```

The first block shows `chain(tickets_a, tickets_b)` yielding the six tickets in order. The `islice(stream, 2)` peeks at the first two; the subsequent `for t in stream` resumes from ticket 3 — the laziness is preserved across the two consumption phases.

The second block shows `from_iterable` flattening both a concrete list-of-lists and a generator-of-lists. The two paths produce identical output because `from_iterable` is agnostic to the outer iterable's type.

The third block shows `islice` in both call shapes: the prefix form `islice(stream, 3)` and the step form `islice(range(10), 0, 10, 2)`. The `rest` printout confirms the underlying stream advances past the items `islice` consumed.

The fourth block shows `islice` rejecting negative indices and `deque(stream, maxlen=3)` as the correct primitive for the last-three-items use case. The `deque` output is the last three items in order, exactly what a hypothetical `stream[-3:]` would have returned if `islice` supported it.

The fifth block confirms the memory win: `islice(big_stream(1_000_000), 3)` runs instantly and yields three items; the list-slice form would allocate a million dicts.

## Common Mistakes

### Mistake 1: Treating `chain` like `+` and unpacking a generator

```python
def bad() -> None:
    gen = (tickets_for(p) for p in projects)   # generator of lists
    stream = itertools.chain(*gen)             # ← unpacks the generator eagerly
```

**Symptom:** `TypeError: 'int' object is not iterable` if the generator yields non-iterables (e.g. ints instead of sub-lists); or (worse, when every yielded value *is* iterable) silently consumes the entire generator into a tuple before `chain` even starts.

**Why:** `chain(*gen)` triggers Python's unpacking protocol — `*gen` is sugar for `tuple(gen)`, which materialises every item the generator yields before `chain` is called. For two projects this is harmless. For ten thousand projects (each fetched lazily from a database) it would force ten thousand DB queries up front, defeating the streaming property. If any yielded value is not itself an iterable, the `chain(...)` call raises `TypeError` on the first `iter(item)` inside `chain` — the error message points at the *item* (`'int' object is not iterable`), not at `chain` itself, which can mislead a student who expects the error to point at the `*gen` unpacking.

**Fix:** Use `chain.from_iterable(gen)` — it accepts the generator as the single outer iterable and walks it lazily, fetching the next sub-iterable only after the previous one is exhausted.

### Mistake 2: Expecting `islice` to support negative indices

```python
# Wrong: tries to take the "last three" items of a stream
last_three = list(itertools.islice(stream, -3))  # ← ValueError
```

**Symptom:** `ValueError: Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.`

**Why:** `islice` walks the iterator forward only. Computing "the last three items" requires consuming the entire iterator and remembering the last three — `islice` refuses to do this silently because it would defeat the laziness contract. The same applies to negative `start` and `step`.

**Fix:** Use `collections.deque(stream, maxlen=3)`. The `deque` keeps a circular buffer of size `maxlen`; every `append` after the third evicts the oldest entry. By the time the stream is exhausted, the `deque` holds exactly the last three items. See [[04-collections/03-deque]] for the canonical treatment.

### Mistake 3: Forgetting `chain` returns a one-shot iterator

```python
stream = itertools.chain(tickets_a, tickets_b)
print(list(stream))   # [t1, t2, t3, t4, t5, t6]
print(list(stream))   # []  ← empty, the iterator is exhausted
```

**Symptom:** The second `list(stream)` returns `[]` — the first call consumed the entire chain.

**Why:** `chain` returns an `itertools.chain` *object*, which is an *iterator*, not an *iterable*. The iterator/iterable distinction (see [[05-collections-abc/04-Iterator-vs-Iterable]]) is that an iterable produces a fresh iterator on each `iter()` call; an iterator is one-shot — once exhausted, subsequent `__next__` calls raise `StopIteration`. All `itertools` functions return one-shot iterators.

**Fix:** If you need to walk the stream twice, either (a) materialise it once into a list with `list(stream)` and walk the list multiple times, or (b) reconstruct the chain from the original inputs each time. The right choice depends on whether the inputs are themselves reproducible (lists) or one-shot (generators); for one-shot inputs you must materialise once.

## Engineering Trade-Offs

**Decision:** Use `chain(*iterables)` to concatenate two or more concrete iterables, `chain.from_iterable(outer)` to flatten a list-of-iterables or a generator-of-iterables, and `islice(iterable, ...)` to slice any iterator lazily. Reach for `deque(stream, maxlen=n)` when you want a sliding window of the last N items.

**Both sides:** The alternative to `chain` is `a + b` (for sequences) or a list-comprehension flatten `[x for sub in outer for x in sub]`. Both win when (a) the inputs are already concrete lists and (b) the result will be used multiple times — `a + b` returns a list that supports `len()`, indexing, and repeated iteration, where `chain` returns a one-shot iterator. The alternative to `islice` is `list(stream)[:n]`, which wins when (a) the stream is short, (b) you actually need the full list downstream, and (c) you need negative-index slicing. `chain` and `islice` win when the stream is large, one-shot, or infinite, and when you want O(1) memory.

**Commitment:** `boardly` uses `chain.from_iterable(db.fetch_pages(pid) for pid in project_ids)` to stream tickets across paginated project IDs without materialising per-page lists, and `islice(stream, 50)` to implement the `?limit=50` query parameter on the ticket feed. The project's lint config flags `list(stream)[:k]` with a `Bench` warning suggesting `islice(stream, k)` as the rewrite. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule as the project's "don't materialise what you can stream" stance.

**Why not ban list-slicing altogether?** Because slicing a concrete list is O(k) in memory for the slice and O(1) in memory for the original — there is no leak. The danger is *only* when slicing the result of a materialisation step, `list(generator)[:k]`, where the materialisation cost dominates. The right rule is "if the input is already a list, slice freely; if the input is a generator or cursor, use `islice`." The boardly style guide makes this trade-off explicit.

## Exercises

1. **Exercise 1 — Change the islice prefix to step form.** Modify `islice_prefix_and_step()` to call `islice(stream, 0, 6, 2)` instead of `islice(stream, 3)`. Re-run and verify the output is the first, third, and fifth ticket titles. `Verify: uv run python boardly/itertools_chain_islice_demo.py`

2. **Exercise 2 — Flatten a list of three lists with `from_iterable`.** Add a third project `proj_c` with three tickets, add `tickets_c` to the fixture, and chain all three via `chain.from_iterable([tickets_a, tickets_b, tickets_c])`. Verify the output has nine tickets. `Verify: uv run python boardly/itertools_chain_islice_demo.py`

3. **Exercise 3 — Implement `last_n_via_deque`.** Write a helper `def last_n(stream, n): return list(deque(stream, maxlen=n))` and use it to get the last two ticket titles of `chain(tickets_a, tickets_b)`. Verify it returns `['Synonym expansion slow', 'Add filter UI']`. `Verify: uv run python boardly/itertools_chain_islice_demo.py`

4. **Exercise 4 — Stream a 100k-element range with `islice`.** Build `big = (i for i in range(100_000))`, take the first ten with `islice`, then verify the rest of the stream still has 99,990 items. Print the count of remaining items without materialising them all at once (hint: `sum(1 for _ in big)`). `Verify: uv run python boardly/itertools_chain_islice_demo.py`

5. **Exercise 5 — Implement an infinite-stream paginated feed.** Write `def infinite_ticket_stream(): ...` that yields `Ticket` objects forever (use `itertools.count` for the ID). Use `islice(infinite_ticket_stream(), 25)` to fetch the first page of 25 results. Add a `?page=N` parameter that returns items `(N-1)*25 : N*25` via two `islice` calls — first to skip `(N-1)*25`, then to take 25. Confirm the page-2 feed starts at ID 25. `Verify: uv run python boardly/itertools_chain_islice_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_chain_islice_demo.py
=== chain: two iterables ===
chain(tickets_a, tickets_b) — first 2 titles:
  Login fails on Safari
  OAuth callback loops
rest of the stream:
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI

=== chain.from_iterable: flatten one level ===
from_iterable(pages) — all ticket titles, flattened:
  Login fails on Safari
  OAuth callback loops
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI
from_iterable(generator) — works where chain(*gen) would explode:
  Login fails on Safari
  OAuth callback loops
  Docs typo in /login
  Index out of range on /search
  Synonym expansion slow
  Add filter UI

=== islice: prefix and step ===
islice(stream, 3) -> ['Login fails on Safari', 'OAuth callback loops', 'Docs typo in /login']
rest of stream -> ['Index out of range on /search', 'Synonym expansion slow', 'Add filter UI']
islice(range(10), 0, 10, 2) -> [0, 2, 4, 6, 8]

=== islice: rejects negative indices ===
islice(range(10), -1) -> Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.
last 3 via deque(maxlen=3) -> ['row-7', 'row-8', 'row-9']

=== memory win: islice vs list-slice ===
islice(big_stream(1_000_000), 3) -> ['ticket-0', 'ticket-1', 'ticket-2']
list(big_stream(1_000_000))[:3] would allocate 1,000,000 dicts
```

## Previously Learned Here

- [[05-collections-abc/04-Iterator-vs-Iterable]] — the iterator/iterable distinction is the foundation every `itertools` primitive stands on; if `chain` returns an iterator (not an iterable), it is one-shot, and that is why `list(stream)` twice yields `[]` the second time.

## What's Next

[[07-itertools/02-groupby]] — `chain` and `islice` are the warm-up; `groupby` is the first `itertools` primitive with a *gotcha* that has caused real production bugs. `groupby(iterable, key=fn)` groups adjacent equal-key elements — if your input is unsorted, you get multiple groups with the same key and a silent bug. The fix is `sorted(data, key=fn)` before `groupby`, and the lesson walks the bug, the fix, and the `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]` pattern in detail.

- `groupby(iterable, key=None)` — consecutive-equal-key grouping.
- The "sort first" precondition — the bug every student hits.
- The shared-iterator trap — each group's iterator must be consumed before advancing to the next group.

## Sources

- **`itertools` — Functions creating iterators for efficient looping** — https://docs.python.org/3/library/itertools.html — accessed 2026-10-23 — the canonical reference for `chain`, `chain.from_iterable`, `islice`, and the rest of the lazy-iterator algebra.
- **`itertools.chain`** — https://docs.python.org/3/library/itertools.html#itertools.chain — accessed 2026-10-23 — the C-implemented concatenation primitive, including `chain.from_iterable` and the lazy-walk semantics.
- **`itertools.islice`** — https://docs.python.org/3/library/itertools.html#itertools.islice — accessed 2026-10-23 — the lazy-slice primitive, with the explicit "negative indices not allowed" note that the docs surface in two lines.
- **`collections.deque`** — https://docs.python.org/3/library/collections.html#collections.deque — accessed 2026-10-23 — the sliding-window primitive that `islice` cannot be, with the `maxlen` argument that turns the deque into a fixed-size circular buffer.

## What We Learned

- You can apply `itertools.chain(*iterables)` to concatenate two or more iterables into a single lazy stream without building a combined list.
- You can apply `itertools.chain.from_iterable(outer)` to flatten a list-of-iterables or a generator-of-iterables one level deep — the fast path when the outer source is itself a generator.
- You can apply `itertools.islice(iterable, stop)` and `islice(iterable, start, stop, step=1)` to slice any iterator lazily, and articulate why negative indices raise `ValueError`.
- You can measure the memory win of `islice(stream, n)` over `list(stream)[:n]` on a million-row stream — O(n) vs O(N).
- You can choose between `islice` (prefix) and `deque(stream, maxlen=n)` (sliding window of last N) and defend the choice.
