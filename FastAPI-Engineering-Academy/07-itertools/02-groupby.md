---
title: "Lesson 02: groupby"
aliases:
 - itertools.groupby
 - groupby
tags:
 - itertools
 - groupby
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[18-operator/01-itemgetter-attrgetter]]"
related_lessons:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[07-itertools/03-starmap-and-accumulate]]"
 - "[[18-operator/01-itemgetter-attrgetter]]"
---

# Lesson 02: `groupby`

*The `itertools` primitive that has caused more silent bugs than every other `itertools` function combined — `groupby(iterable, key=fn)` groups **consecutive** equal-key elements, and if you forget to sort first, you get six "todo" groups instead of one.*

**You're at the very beginning of Section 07, Lesson 02.**

`itertools.groupby` is the only `itertools` primitive that has a *precondition* the docs surface in one sentence and every senior engineer has burnt a deploy on. The precondition is this: `groupby` walks the input left-to-right and starts a new group every time the key changes. If your input is unsorted, the same key appears in multiple disjoint runs and you get one group per run — not one group per key. The fix is one `sorted(data, key=fn)` call before the `groupby`, but the bug is invisible because `groupby` runs without error and returns *something*. It just returns the wrong something. By the end of this lesson you will know the bug, the fix, the canonical `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]` pattern, and the second gotcha — the shared-iterator trap. Take your time. Type every example. **This is how you learn.**

#itertools #groupby

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.groupby(iterable, key=None)`** to group consecutive equal-key elements of any iterable.
2. **Diagnose the unsorted-input bug** — multiple groups with the same key — and fix it by sorting the input by key first.
3. **Write the canonical pattern** `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]` from memory.
4. **Explain the shared-iterator trap** — each group's iterator must be consumed before advancing to the next group — and avoid it by materialising each group with `list(g)` immediately.
5. **Choose between `groupby` and `collections.defaultdict`** based on whether the input is already sorted by key.

## Prerequisites

Before starting, you need:

- **`operator.attrgetter`** — the senior-engineer `key=` function for dataclass attributes. See [[18-operator/01-itemgetter-attrgetter]].
- **`chain` and `islice`** — the warm-up `itertools` primitives, for the one-shot-iterator mental model. See [[07-itertools/01-chain-and-islice]].
- **About 20–30 minutes of focused time.**

**The most common gap: not sorting before `groupby`.**

Students reach for `groupby` after SQL `GROUP BY` and pandas `.groupby()`, both of which *sort for you*. SQL `GROUP BY status` collects every row with the same status into one group, regardless of the row order in the underlying table. pandas `.groupby("status")` does the same. `itertools.groupby` does *not* — it is a much cheaper primitive that scans the input once and starts a new group only when the key changes. The precondition is the caller's job, not the function's. Students who skip reading the docs ship a feature that produces six "todo" groups, write a unit test that happens to feed sorted input, and the bug survives to production. The fix is one line — `sorted(data, key=fn)` before `groupby` — and the lesson makes it automatic.

## The Problem

You ship `boardly/api/tickets_by_status.py` — an endpoint that returns `{status: [ticket_titles]}` for a board view. The first version reads naturally:

```python
from itertools import groupby
from operator import attrgetter

def group_by_status(tickets: list[Ticket]) -> dict[str, list[str]]:
    by_status = attrgetter("status")
    return {
        status: [t.title for t in group]
        for status, group in groupby(tickets, key=by_status)
    }
```

You write a unit test with three tickets — one `todo`, one `in_progress`, one `done` — and the endpoint returns the right shape. You ship. Two days later a teammate asks why the board shows three separate "todo" columns when there are clearly four todo tickets. You dig in and find the production input is:

```python
tickets = [
    Ticket(..., status="todo"),
    Ticket(..., status="in_progress"),
    Ticket(..., status="done"),
    Ticket(..., status="todo"),       # ← not adjacent to the first "todo"
    Ticket(..., status="blocked"),
    Ticket(..., status="todo"),       # ← not adjacent to either of the others
]
```

`groupby` walks left-to-right. The first `todo` starts group 1; `in_progress` starts group 2; `done` starts group 3; the second `todo` (key changed from `done` to `todo`) starts group 4; `blocked` starts group 5; the third `todo` starts group 6. The dict-comprehension overwrites group 1 with group 4 with group 6, so the final dict has `{todo: [last todo only], in_progress: [...], done: [...], blocked: [...]}` — three "todo" tickets are silently lost.

`itertools.groupby` is correct; the bug is the precondition. The fix is `sorted(tickets, key=by_status)` before `groupby` — then all `todo` tickets are adjacent, `groupby` collapses them into one group, and the dict-comprehension sees one "todo" key with three titles. The lesson walks the bug, the fix, and the canonical one-liner pattern.

## The Code

```python
# boardly/itertools_groupby_demo.py
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
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/itertools_groupby_demo.py
"""Demonstrate itertools.groupby: the bug, the fix, and the shared-iterator trap."""
from __future__ import annotations

import itertools
import operator
from dataclasses import dataclass
from uuid import UUID, uuid4
```

`itertools` is the star — `groupby` is the only function we use today, but the imports line stays consistent with [[07-itertools/01-chain-and-islice]]. `operator.attrgetter` is the senior-engineer `key=` function — `attrgetter("status")` is the C-implemented callable equivalent of `lambda t: t.status` (see [[18-operator/01-itemgetter-attrgetter]]). `dataclass` builds frozen value objects so the demo is offline. `UUID` and `uuid4` give us stable identifiers without a database. `from __future__ import annotations` is boardly house style.

### Lines 12–16: The `Ticket` model

```python
@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    status: str   # "todo" | "in_progress" | "done" | "blocked"
```

A frozen dataclass. The `status` field is a plain string — in production `boardly` uses a `StrEnum` (see [[09-enum/02-IntEnum-and-StrEnum]]), but for this lesson a string keeps the demo dependency-free. `frozen=True` makes the instance hashable, which matters for `groupby` only indirectly: the key function is `attrgetter("status")`, which extracts the `status` *string* (already hashable), so the `Ticket` itself does not need to be hashable. Frozen is here for continuity with the rest of `boardly`.

### Lines 19–27: The interleaved fixture

```python
# Interleaved statuses — the canonical buggy fixture
tickets = [
    Ticket(uuid4(), "Login fails on Safari", "todo"),
    Ticket(uuid4(), "OAuth callback loops", "in_progress"),
    Ticket(uuid4(), "Docs typo in /login", "done"),
    Ticket(uuid4(), "Index out of range on /search", "todo"),
    Ticket(uuid4(), "Synonym expansion slow", "blocked"),
    Ticket(uuid4(), "Add filter UI", "todo"),
]
```

Six tickets, four distinct statuses. The `status` values are deliberately interleaved: `todo`, `in_progress`, `done`, `todo`, `blocked`, `todo`. The "todo" status appears at indices 0, 3, and 5 — none adjacent. This is the canonical buggy fixture: a real production feed where the upstream source emits rows in arbitrary order. The fixture is at module scope so every helper sees the same data.

**Why interleave by hand instead of shuffling?** Because the bug is *visible* in the interleaving. A randomised fixture would reproduce the bug, but the student reading the demo would have to mentally unroll the shuffle to see why group 4 exists. The hand-crafted interleaving makes the bug readable: "the key changed from `done` to `todo` between index 2 and index 3, so a new group started." In production the interleaving is whatever order the DB cursor returns; in the lesson it is deliberate.

### Lines 30–37: The unsorted-input bug

```python
def groupby_unsorted_bug() -> None:
    """groupby groups CONSECUTIVE equal-key items — unsorted input is the bug."""
    by_status = operator.attrgetter("status")
    groups = itertools.groupby(tickets, key=by_status)
    result = [(k, [t.title for t in g]) for k, g in groups]
    print("groupby(tickets, key=status) — UNSORTED input:")
    for status, titles in result:
        print(f"  {status!r}: {titles}")
    print(f"  -> {len(result)} groups instead of 4 — bug!")
```

`itertools.groupby(tickets, key=attrgetter("status"))` returns an iterator of `(key, group_iterator)` pairs. Internally — you can read this in `Modules/itertoolsmodule.c` in the CPython source — `groupby` walks the underlying iterator in a single forward pass. It peeks at the first element, computes the key, and starts yielding items from the first group. Every `__next__` call on the group iterator pulls the next item from the underlying iterator; if the key matches, the item is yielded; if the key has changed, the group iterator raises `StopIteration` *and the underlying item is buffered for the next group*. The next call to `next(groups)` then peeks at that buffered item, computes its key, and starts a new group.

The crucial detail: `groupby` does not remember past groups. If the key changes from `todo` to `in_progress` and then back to `todo`, the second `todo` run starts a *new* group — there is no look-back to merge it with the first `todo` group. The precondition for "one group per key" is that all items with the same key are *consecutive* in the input, which is exactly what `sorted(data, key=fn)` guarantees.

The list comprehension `[(k, [t.title for t in g]) for k, g in groups]` materialises each group's titles into a list. The result has *six* groups: `todo`, `in_progress`, `done`, `todo`, `blocked`, `todo` — three of them with key `"todo"`. The student expected four (one per distinct status). The print line calls out the bug: "6 groups instead of 4 — bug!"

**Why doesn't `groupby` just sort for you?** Two reasons. First, sorting is O(N log N) and `groupby` is O(N) — the docs and the CPython maintainers chose to keep `groupby` cheap and push the sort cost to the caller, who often has a pre-sorted input (DB cursor with `ORDER BY`, time-series data already in chronological order). Second, the consecutive-grouping semantics is *useful in its own right*: it answers "what are the contiguous runs of equal-key items in this stream?" — which is exactly what you want for log-line analysis, run-length encoding, and detecting state transitions. If `groupby` silently sorted, those use cases would break. The contract is "I group consecutive equal-key items; you sort if you want one-group-per-key." Knowing the contract is the senior-engineer move.

### Lines 40–49: The sorted-input fix

```python
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
```

One line added: `sorted_tickets = sorted(tickets, key=by_status)`. `sorted` is the stable sort (see [[18-operator/01-itemgetter-attrgetter]] for the `key=` convention) — it returns a fresh list, sorted by `status` ascending, with the original ticket order preserved within each status (so the `todo` group has tickets in fixture order: `Login fails on Safari`, `Index out of range on /search`, `Add filter UI`).

`groupby` on the sorted input now sees: `blocked, blocked, ...` (one ticket), `done, done, ...` (one), `in_progress, in_progress, ...` (one), `todo, todo, todo` (three). The consecutive-equal-key precondition is satisfied, and `groupby` produces four groups — one per distinct status. The fix is one line; the bug is the absence of that line.

**Why call `attrgetter("status")` twice — once in `sorted` and once in `groupby`?** Because `sorted` and `groupby` are independent functions with independent `key=` parameters; there is no shared "sort key" state. The senior-engineer move is to bind the callable to a name (`by_status = attrgetter("status")`) and reuse the name at both call sites — which is what the lesson does. The C-level `attrgetter` instance is the same object both times (no allocation cost beyond the first call), and the call site reads as English: "sorted by status, then grouped by status". If the two `key=` functions diverged (`sorted` by one key, `groupby` by another), you would have a real bug — the lesson's naming convention makes the divergence visible at a glance.

### Lines 52–63: The canonical one-liner pattern

```python
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
```

The pattern: `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]`. Read it inside-out: `sorted(data, key=fn)` returns a list sorted by `fn`; `groupby(sorted_list, key=fn)` returns an iterator of `(key, group_iterator)` pairs; the list comprehension walks the pairs and materialises each `group_iterator` into a list with `list(g)`. The result is a `list[tuple[key, list[item]]]` — a fully materialised structure you can iterate, index, or pass downstream.

The `list(g)` call inside the comprehension is *not* cosmetic. Each `group_iterator` is a view onto a shared underlying iterator (see the next block); if you don't materialise it before the comprehension advances to the next `(k, g)` pair, the shared iterator moves past your group's items and the next `list(g)` call returns an empty list. `list(g)` materialises *now*, before the next iteration, and the pattern works.

**Why `list(g)` and not `tuple(g)`?** Mostly convention. `list` is the default materialisation in Python idioms ("list out the items"), and downstream code often wants to append or extend. `tuple(g)` is fine if you want immutability, and `set(g)` is fine if you want uniqueness. The choice is downstream — the lesson uses `list` because that is the most common materialisation in `boardly`'s API layer (returning lists of ticket titles to the client).

### Lines 66–84: The shared-iterator trap

```python
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
```

The second gotcha. `groupby` returns an iterator of `(key, group_iterator)` pairs, but the *group iterators* share a single underlying iterator over the input. When you call `next(groups)` to advance to the second group, `groupby` peeks at the next underlying item to find the second group's key — which means the underlying iterator has moved past the first group's items. If you have not yet materialised `first_group` (e.g. via `list(first_group)`), it is now too late: `list(first_group)` returns an empty list because the shared underlying iterator is positioned at the start of the second group's items.

The demo: `first_key, first_group = next(groups)` gets the `"blocked"` key (the first status in sorted order) and a `first_group` iterator that would yield the one blocked ticket. `second_key, second_group = next(groups)` gets `"done"` and a `second_group` iterator — and silently poisons `first_group`. `list(first_group)` then returns `[]` because the underlying iterator is now positioned at the first `done` ticket. The `"blocked"` ticket is lost forever from `first_group`'s perspective.

**Why is the iterator shared instead of being forked per group?** Because `groupby` is designed to be a single-pass streaming primitive. If every group had its own independent iterator, `groupby` would have to buffer every item from every group until the consumer chose to walk them — O(N) in memory and identical in cost to `defaultdict(list)`. The shared-iterator design keeps `groupby` at O(1) memory regardless of group count. The cost is the contract: the caller must consume each group's iterator before advancing to the next. The `list(g)` call inside the canonical pattern is what enforces the contract — it materialises each group eagerly, so the shared iterator is consumed in order.

**Warning — Materialise or advance, not both.** If you have an unconsumed `group_iterator` and you advance the outer `groups` iterator, the `group_iterator` is silently invalidated. Either `list(g)` it immediately, or pass it to a function that fully consumes it before the outer `next(groups)` call. There is no "save the group iterator and consume it later" — by then the underlying stream is gone.

### Lines 87–98: Counting per group

```python
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
```

The board-view use case: a status badge that shows `todo (3)`. `sum(1 for _ in g)` consumes the group iterator and counts items without materialising them — `sum` walks the generator expression `1 for _ in g`, which pulls each item from `g`, discards the item, and yields `1` per pull. The result is the count of items in the group.

This pattern is the senior-engineer choice when you want a count, not the items: `sum(1 for _ in g)` is O(1) in memory (it never holds the group's items) and O(k) in time (it walks the group once). `len(list(g))` would materialise the group into a list first, paying O(k) memory just to throw the list away. The generator expression keeps the laziness.

**Why not `collections.Counter(t.status for t in tickets)`?** That is also a valid choice — and is the right one when the input is unsorted and you want a count per key without paying the sort. `Counter` is O(N) in time and O(distinct keys) in memory, with no sort precondition. `groupby` + `sum(1 for _ in g)` is O(N log N) in time (because of the sort) and O(distinct keys) in memory. The `groupby` approach wins when (a) you also want the items per group (not just the count), or (b) the input is already sorted by key (so the sort is free). `Counter` wins when you only want counts on unsorted input. The boardly board-view uses `Counter` for the count badge and `groupby` for the expand-to-list endpoint, because the count badge is called ten times more often and `Counter` is cheaper per call.

## Execution Trace

```bash
$ uv run python boardly/itertools_groupby_demo.py
=== groupby: the unsorted bug ===
groupby(tickets, key=status) — UNSORTED input:
  'todo': ['Login fails on Safari']
  'in_progress': ['OAuth callback loops']
  'done': ['Docs typo in /login']
  'todo': ['Index out of range on /search']
  'blocked': ['Synonym expansion slow']
  'todo': ['Add filter UI']
  -> 6 groups instead of 4 — bug!

=== groupby: the sorted fix ===
groupby(sorted(tickets, key=status), key=status) — SORTED input:
  'blocked': ['Synonym expansion slow']
  'done': ['Docs typo in /login']
  'in_progress': ['OAuth callback loops']
  'todo': ['Login fails on Safari', 'Index out of range on /search', 'Add filter UI']
  -> 4 groups, one per status — fixed!

=== groupby: the canonical pattern ===
The canonical [(k, list(g)) for k, g in groupby(sorted(...), key=...)] pattern:
  'blocked': 1 tickets
  'done': 1 tickets
  'in_progress': 1 tickets
  'todo': 3 tickets

=== groupby: the shared-iterator trap ===
first_key='blocked' (first_group NOT consumed)
second_key='done'
list(first_group) AFTER advancing -> 0 items (should be 1 — got 0!)
second_group titles: ['Docs typo in /login']

=== groupby: count per group ===
counts per status: {'blocked': 1, 'done': 1, 'in_progress': 1, 'todo': 3}
```

The first block shows the bug: six groups, three of them with key `"todo"`. The `groupby` walked the unsorted input and started a new group every time the status changed. The student expected one group per distinct status (four); the actual is one group per contiguous run (six).

The second block shows the fix: one `sorted(tickets, key=by_status)` call before `groupby` collapses the six runs into four groups — one per distinct status. The `"todo"` group now has all three todo tickets in fixture order (`Login fails on Safari`, `Index out of range on /search`, `Add filter UI`).

The third block shows the canonical one-liner pattern producing a list of `(status, count)` pairs. The pattern reads inside-out: `sorted`, then `groupby`, then a list comprehension that materialises each `group_iterator` with `list(g)`.

The fourth block shows the shared-iterator trap. After `next(groups)` returns the first group (blocked) and `next(groups)` returns the second group (done), `list(first_group)` returns `[]` because the underlying iterator has advanced into the second group's items. The blocked ticket is lost. `second_group` still works because it was the most recently returned and the underlying iterator is positioned at its first item.

The fifth block shows the count-per-group aggregator. The dict has one entry per distinct status with the count of tickets. The `sum(1 for _ in g)` pattern keeps memory O(1) per group — no list materialised.

## Common Mistakes

### Mistake 1: Forgetting to sort before `groupby`

```python
# Wrong: unsorted input → multiple groups with the same key
groups = itertools.groupby(tickets, key=attrgetter("status"))
result = [(k, list(g)) for k, g in groups]
# result has 6 groups, three with key="todo" — silently wrong
```

**Symptom:** The output has more groups than distinct keys, or a downstream dict-comprehension `{k: list(g) for k, g in groupby(...)}` silently overwrites earlier groups with later ones (because the same key appears multiple times).

**Why:** `groupby` groups *consecutive* equal-key elements. If your input is unsorted, the same key appears in multiple disjoint runs and you get one group per run — not one group per key. SQL `GROUP BY` and pandas `.groupby()` sort for you; `itertools.groupby` does not.

**Fix:** Add `sorted(data, key=fn)` before `groupby`: `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]`. This is the canonical pattern. Use it from memory.

### Mistake 2: Not consuming a group iterator before advancing

```python
groups = itertools.groupby(sorted_tickets, key=by_status)
first_key, first_group = next(groups)
second_key, second_group = next(groups)   # ← first_group now poisoned
# ...
list(first_group)   # ← returns [] — the underlying iterator is past first_group's items
```

**Symptom:** A group iterator that should have items returns an empty list when materialised later.

**Why:** All group iterators from one `groupby` call share a single underlying iterator. When you call `next(groups)` to advance to the second group, `groupby` peeks at the next underlying item to find the second group's key — which means the underlying iterator has moved past the first group's items. If you have not yet materialised `first_group`, it is too late.

**Fix:** Materialise each group with `list(g)` *before* the outer iterator advances. The canonical pattern `[(k, list(g)) for k, g in groupby(...)]` enforces this: the list comprehension materialises `g` inside the comprehension body, before the next iteration step.

### Mistake 3: Using `groupby` when you only want counts

```python
# Wrong (works, but pays an unnecessary sort)
counts = {k: sum(1 for _ in g) for k, g in groupby(sorted(data, key=fn), key=fn)}

# Right — no sort needed
from collections import Counter
counts = Counter(item.status for item in data)
```

**Symptom:** The code works, but `timeit` shows it is slower than the equivalent `Counter` call — by a factor of log N, the sort cost.

**Why:** `groupby` requires a sort, which is O(N log N). If you only want counts per key (not the items per key), `collections.Counter` is O(N) with no sort precondition. The `groupby` approach wins when you want the *items per group* (so the items are materialised anyway) or when the input is already sorted by key. For pure counts on unsorted input, `Counter` is the senior choice.

**Fix:** Use `Counter` for counts on unsorted input. Reserve `groupby` for "I want the items per key, sorted by key, and I will materialise the groups."

## Engineering Trade-Offs

**Decision:** Use `itertools.groupby(sorted(data, key=fn), key=fn)` when you want the items per key, the input is or can be sorted by key, and you will materialise the groups. Use `collections.defaultdict(list)` when the input is unsorted and you do not want to pay the sort cost. Use `collections.Counter` when you want only the count per key.

**Both sides:** The alternative to `groupby` is `defaultdict(list)`: `groups = defaultdict(list); for t in tickets: groups[t.status].append(t)`. This is O(N) in time and O(N) in memory (it holds every item), with no sort precondition. It wins when (a) the input is unsorted, (b) you want a dict not a list of pairs, and (c) you have enough memory to hold all items at once. `groupby` wins when (a) the input is already sorted (so the sort is free), (b) you want a streaming one-pass primitive that does not hold the items, or (c) you specifically want the *consecutive-run* semantics (log-line analysis, run-length encoding).

**Commitment:** `boardly/api/tickets_by_status.py` uses `[(k, list(g)) for k, g in groupby(sorted(tickets, key=attrgetter("status")), key=attrgetter("status"))]` because the DB cursor returns tickets in an order the endpoint cannot rely on, the endpoint needs the items per status (not just counts), and the result is consumed downstream as a list. The boardly lint config flags a bare `groupby(...)` (without a `sorted(...)` wrapping) with a `Maybe` warning suggesting the canonical pattern. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule as the project's "don't ship the silent groupby bug" stance.

**Why not just sort the SQL with `ORDER BY status` and skip the Python sort?** Because the senior-engineer stance is defense-in-depth: the endpoint should produce correct output regardless of the cursor order, in case someone reorders the SQL for a different reason (e.g. `ORDER BY created_at DESC` for a different view) and forgets to update the `groupby` call. Sorting in Python costs O(N log N) on a list of typically 50–500 tickets per project — negligible. The `Maybe` lint warning makes the contract visible at the call site.

## Exercises

1. **Exercise 1 — Group by `status` descending.** Change the `sorted_tickets` call in `groupby_sorted_fix()` to sort status descending (`sorted(tickets, key=by_status, reverse=True)`). Re-run and verify the groups appear in reverse alphabetical order (`todo`, `in_progress`, `done`, `blocked`). `Verify: uv run python boardly/itertools_groupby_demo.py`

2. **Exercise 2 — Materialise each group with `tuple(g)` instead of `list(g)`.** Modify `the_canonical_pattern()` to build `(k, tuple(g))` pairs. Verify the second element of each pair is a tuple, not a list. `Verify: uv run python boardly/itertools_groupby_demo.py`

3. **Exercise 3 — Implement a run-length encoder.** Write `def rle(s: str) -> list[tuple[str, int]]:` that uses `groupby` to return run-length-encoded pairs — `rle("aaabbc")` should return `[('a', 3), ('b', 2), ('c', 1)]`. Note: no `sorted` here, because RLE is *about* the consecutive runs. Verify with `rle("aaabbc")` and `rle("ababab")` (which has 6 runs of length 1, not 2 groups). `Verify: uv run python boardly/itertools_groupby_demo.py`

4. **Exercise 4 — Replace `groupby` with `defaultdict(list)` for the count use case.** Rewrite `count_per_group()` using `collections.defaultdict(int)` (or `collections.Counter`). Verify the dict is identical, then `timeit` both implementations on a list of 10,000 tickets with 4 distinct statuses. Report the speedup. `Verify: uv run python boardly/itertools_groupby_demo.py`

5. **Exercise 5 — Build a `group_by_month` aggregator.** Add a `created_at: datetime` field to the `Ticket` model, populate the fixture with tickets across two months, and write a `group_by_month(tickets)` function that uses `groupby(sorted(tickets, key=lambda t: t.created_at.replace(day=1)), key=lambda t: t.created_at.replace(day=1))` to bucket tickets by calendar month. Print one group per month. `Verify: uv run python boardly/itertools_groupby_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_groupby_demo.py
=== groupby: the unsorted bug ===
groupby(tickets, key=status) — UNSORTED input:
  'todo': ['Login fails on Safari']
  'in_progress': ['OAuth callback loops']
  'done': ['Docs typo in /login']
  'todo': ['Index out of range on /search']
  'blocked': ['Synonym expansion slow']
  'todo': ['Add filter UI']
  -> 6 groups instead of 4 — bug!

=== groupby: the sorted fix ===
groupby(sorted(tickets, key=status), key=status) — SORTED input:
  'blocked': ['Synonym expansion slow']
  'done': ['Docs typo in /login']
  'in_progress': ['OAuth callback loops']
  'todo': ['Login fails on Safari', 'Index out of range on /search', 'Add filter UI']
  -> 4 groups, one per status — fixed!

=== groupby: the canonical pattern ===
The canonical [(k, list(g)) for k, g in groupby(sorted(...), key=...)] pattern:
  'blocked': 1 tickets
  'done': 1 tickets
  'in_progress': 1 tickets
  'todo': 3 tickets

=== groupby: the shared-iterator trap ===
first_key='blocked' (first_group NOT consumed)
second_key='done'
list(first_group) AFTER advancing -> 0 items (should be 1 — got 0!)
second_group titles: ['Docs typo in /login']

=== groupby: count per group ===
counts per status: {'blocked': 1, 'done': 1, 'in_progress': 1, 'todo': 3}
```

## Previously Learned Here

- [[07-itertools/01-chain-and-islice]] — `chain` and `islice` taught the one-shot-iterator mental model. `groupby` is the first `itertools` primitive where that model bites: the shared group iterator is one-shot, and the order of consumption matters.

## What's Next

[[07-itertools/03-starmap-and-accumulate]] — `groupby` showed you the *group* primitive; the next lesson shows you the *map* and *fold* primitives. `itertools.starmap(func, iterable)` unpacks each tuple into positional args (`func(*t)` instead of `func(t)`), and `itertools.accumulate(iterable, func, initial=...)` is the streaming fold — running sum, running max, factorial via `operator.mul`. The `initial=` keyword (3.8+) is the second `itertools` gotcha: it changes the output length.

- `starmap(func, [(a, b), (c, d)])` — unpacks tuples into positional args.
- `accumulate([1, 2, 3], operator.add)` — running sum, lazy.
- `accumulate(range(1, 6), operator.mul, initial=1)` — factorial, with the leading `1` from `initial`.

## Sources

- **`itertools.groupby`** — https://docs.python.org/3/library/itertools.html#itertools.groupby — accessed 2026-10-23 — the canonical reference, including the one-line "generally, the iterable needs to already be sorted on the same key function" note that the docs surface and every senior engineer has burnt a deploy on.
- **`itertools` — Functions creating iterators for efficient looping** — https://docs.python.org/3/library/itertools.html — accessed 2026-10-23 — the parent module reference, with the recipes section that ends the docs page and the canonical `grouper` recipe.
- **`collections.defaultdict`** — https://docs.python.org/3/library/collections.html#collections.defaultdict — accessed 2026-10-23 — the alternative grouping primitive that does not require a sort precondition, useful for unsorted inputs.
- **`collections.Counter`** — https://docs.python.org/3/library/collections.html#collections.Counter — accessed 2026-10-23 — the count-per-key primitive that beats `groupby` + `sum(1 for _ in g)` when you only want counts.

## What We Learned

- You can apply `itertools.groupby(iterable, key=None)` to group consecutive equal-key elements of any iterable.
- You can diagnose the unsorted-input bug — multiple groups with the same key — and fix it with one `sorted(data, key=fn)` call before `groupby`.
- You can write the canonical `[(k, list(g)) for k, g in groupby(sorted(data, key=fn), key=fn)]` pattern from memory.
- You can explain the shared-iterator trap — each group's iterator must be consumed before advancing — and avoid it by materialising each group with `list(g)` immediately.
- You can choose between `groupby` (sorted input, want items per key), `defaultdict(list)` (unsorted input, want items per key), and `Counter` (want counts per key only) and defend the choice.
