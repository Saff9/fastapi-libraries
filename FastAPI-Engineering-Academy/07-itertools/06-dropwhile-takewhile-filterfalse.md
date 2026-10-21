---
title: "Lesson 06: dropwhile, takewhile, filterfalse — the predicate filters"
aliases:
 - itertools dropwhile
 - itertools takewhile
 - itertools filterfalse
 - predicate filters
tags:
 - itertools
 - predicate-filters
 - streaming
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[07-itertools/05-cycle-repeat-count]]"
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[07-itertools/05-cycle-repeat-count]]"
 - "[[07-itertools/07-tee-and-zip_longest]]"
 - "[[18-operator/03-functional-composition]]"
---

# Lesson 06: `dropwhile`, `takewhile`, `filterfalse` — the predicate filters

*Three predicate-driven `itertools` functions, three different boundary semantics — `dropwhile` drops the *prefix once* and then yields *the rest* without re-checking (note `3` is yielded even though `<5`), `takewhile` yields *while* True and then *STOPS* at the first False even if later elements would match, and `filterfalse` is the *complement* of `filter` (yields where the predicate is False).*

**You're at the very beginning of Section 07.**

The last lesson taught the three infinite iterators — `cycle`, `repeat`, `count` — and the rule that every call site has a bound. This lesson teaches the three *predicate* filters: `dropwhile`, `takewhile`, `filterfalse`. Each takes a one-argument predicate function and an iterable; each applies the predicate to elements; each stops or yields based on a different boundary rule. The three boundary rules are the lesson — and the trap. `dropwhile(lambda x: x<5, [1,4,6,3,8])` yields `[6, 3, 8]` (the `3` survives because `dropwhile` does not re-check after the first False); `takewhile(lambda x: x<5, [1,4,6,3,8])` yields `[1, 4]` (the `3` does *not* survive, because `takewhile` stops at the first False); `filterfalse(even, [1,2,3,4,5])` yields `[1, 3, 5]` (the complement of `filter(even, ...)`). Three functions, three boundary rules, three production bugs if you mix them up. Take your time. Type every example. **This is how you learn.**

#itertools #predicate-filters #streaming

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.dropwhile(predicate, iterable)`** — drop the leading prefix while the predicate is True, then yield *everything that follows* without re-checking — including later elements that *would* satisfy the predicate.
2. **Apply `itertools.takewhile(predicate, iterable)`** — yield elements while the predicate is True, then *STOP* at the first False — even if later elements would match.
3. **Apply `itertools.filterfalse(predicate, iterable)`** — yield elements where `predicate(elem)` is `False` (the complement of `filter`); pass `None` as the predicate to yield falsy elements.
4. **Articulate the boundary asymmetry** between `dropwhile` and `takewhile` — `dropwhile` checks the predicate *until* the first False then never checks again; `takewhile` checks the predicate *until* the first False then never yields again. Same predicate, opposite stopping rules.
5. **State the "takewhile stops early" gotcha** — `takewhile(lambda x: x<5, [1,4,6,3,8])` yields `[1, 4]`, *not* `[1, 4, 3]`. The `3` would satisfy the predicate but is never reached, because `takewhile` stops at the first False and does not resume.

## Prerequisites

Before starting, you need:

- **The three infinite iterators** — [[07-itertools/05-cycle-repeat-count]] is the canonical previous lesson in this section; this lesson builds on the lazy-iterator mental model the infinite iterators taught.
- **`chain` & `islice`** — [[07-itertools/01-chain-and-islice]] for the broader `itertools` context, especially the laziness rule that *none* of these filters materialise their input.
- **A typed model with `status`** — [[06-dataclasses/01-dataclass-Basics]]. This lesson widens the `Ticket` from lesson 5 to include `status` and `priority`, so the predicates have something to filter on.
- **About 25–35 minutes of focused time.**

**The most common gap: confusing `dropwhile` with `filter(invert_predicate, ...)` and `takewhile` with `filter`.**

`dropwhile` and `takewhile` are *positional* filters — they care about where the predicate first fails, not about each element individually. `filter` and `filterfalse` are *per-element* filters — they check each element independently. The student who reads `dropwhile(lambda x: x<5, [1,4,6,3,8])` as "drop each element that is `<5`" gets `[6, 8]` (the per-element reading); the actual result is `[6, 3, 8]` (the positional reading — `3` survives because `dropwhile` already stopped checking after the first False). The same student who reads `takewhile(lambda x: x<5, [1,4,6,3,8])` as "take each element that is `<5`" gets `[1, 4, 3]` (the per-element reading); the actual result is `[1, 4]` (the positional reading — `3` is never reached). The mental shift this lesson teaches is the *boundary* reading: `dropwhile`/`takewhile` make one decision at one position, then commit to it forever.

## The Problem

`boardly/tickets/stream_filters.py` has three real tasks that positional and per-element filters express differently:

1. **Skip the boot log prefix.** The ticket-creation stream starts with N "warm-up" rows (status `"system_boot"`) emitted by the pipeline before any real ticket arrives. `dropwhile(lambda t: t.status == "system_boot", stream)` skips the leading boot rows and yields everything after, *including* any later boot-shaped rows that arrive mid-stream (rare, but real — a deploy restart emits a boot row in the middle of the day).

2. **Take the leading "open" tickets.** From a stream sorted by creation time, take every ticket while its status is `"todo"` — stop at the first non-`"todo"`. `takewhile(lambda t: t.status == "todo", stream)` yields the leading prefix of todo tickets and stops at the first `in_progress`/`done`. The gotcha: if a later `todo` ticket appears (e.g. one reopened), `takewhile` does not see it — the stop is final.

3. **Find the non-watched tickets.** `filterfalse(lambda t: t.status in WATCH, tickets)` yields the complement of `filter` — tickets whose status is *not* in the watch set. This is the "give me everything I'm not paging on" view, the opposite of the `filter` form the operator lesson used.

The three tasks have one shape in common: a predicate function decides what survives, but the *timing* of the decision differs. `dropwhile` decides once, at the start, and then yields the rest unconditionally. `takewhile` decides once, at the start, and then stops unconditionally. `filterfalse` decides per-element, every time. The lesson is the boundary semantics.

## The Code

```python
# boardly/itertools_dropwhile_takewhile_filterfalse_demo.py
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
```

## Line-by-Line Deep Dive

### Lines 1–14: Imports and the wider `Ticket` model

```python
# boardly/itertools_dropwhile_takewhile_filterfalse_demo.py
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
```

Same imports as lesson 5: `itertools` is the star, `dataclass` and `UUID` build the value object. The `Ticket` is wider than lesson 5's two-field model — it has `status` and `priority`, because the three predicate filters need something to filter on. The shape matches [[07-itertools/01-chain-and-islice]]'s `Ticket` exactly (same fields, same order, same comment style), so the student who has read the section in order sees continuity.

`frozen=True` matters here for the same reason it mattered in lesson 01: the tickets are fixture data that gets passed through `dropwhile`/`takewhile`/`filterfalse` iterators. Frozen instances cannot be mutated mid-iteration, so the predicate sees the same `status` every time it's called. If `Ticket` were mutable and a predicate had a side effect (it shouldn't, but accidents happen), the result of `takewhile` would be undefined. `frozen=True` is the contract that the predicate is pure.

### Lines 17–32: The fixture — a creation-time-ordered stream with a stray boot row

```python
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
```

`WATCH` is the same set [[18-operator/03-functional-composition]] uses — `{"blocked", "in_progress"}`. The fixture is a 10-ticket list ordered by creation time. The first three rows are `"system_boot"` warm-up rows; rows 4–7 are real tickets (two todos, one in_progress, one done); row 8 is a *stray* `"system_boot"` row mid-stream — the gotcha. Row 9 is a `"todo"` ticket *after* the first non-todo (a reopened ticket — `takewhile` will not see it); row 10 is a `"blocked"` ticket.

The stray boot row and the reopened ticket are the fixture's two traps. `dropwhile(lambda t: t.status == "system_boot", stream)` drops rows 1–3 and then yields *everything* — including row 8 (the stray boot row), because `dropwhile` doesn't re-check after the first False. `takewhile(lambda t: t.status == "todo", stream_after_boot)` (where `stream_after_boot = stream[3:]` skips the boot prefix) yields rows 4 and 5 (the leading todos) and stops at row 6 (the first non-todo); row 8's stray boot and row 9's reopened todo are *never reached*, because `takewhile` does not resume.

**Why include the stray boot row and the reopened ticket?** Because they're the production failure modes that distinguish positional filters from per-element filters. A real ticket stream has mid-stream boot rows (every deploy) and reopened tickets (every time a customer reports a regression). If the student runs `dropwhile` against a clean fixture and gets `[6, 8]` (the per-element reading) by accident — no, wait: `dropwhile` returns `[6, 3, 8]` regardless of fixture; the per-element reading is the *student's* mistaken prediction. The stray boot row and the reopened ticket are the rows where the positional and per-element readings diverge. Without those rows, the student can read the code either way and get the same answer; with those rows, only the positional reading is correct.

### Lines 35–43: `dropwhile` — drop the prefix once, then yield the rest

```python
def dropwhile_demo() -> None:
    """dropwhile(predicate, iterable): drop prefix while True, then yield all rest."""
    # Per-element demo: dropwhile(<5, [1,4,6,3,8]) — note 3 survives
    nums = [1, 4, 6, 3, 8]
    result = list(itertools.dropwhile(lambda x: x < 5, nums))
    print(f"dropwhile(<5, {nums}) -> {result}   # note 3 is yielded even though <5")
```

`itertools.dropwhile(predicate, iterable)` walks the iterable and calls `predicate(elem)` on each element in order. *While* the predicate returns `True`, the element is *dropped* (not yielded). The *first* element for which the predicate returns `False` is yielded, and every element after it is yielded *without re-checking the predicate*. Internally, `dropwhile` has two phases: a "drop" phase (call the predicate, skip if True) and a "pass" phase (yield everything without checking). The phase transition happens exactly once, at the first False.

`dropwhile(lambda x: x < 5, [1, 4, 6, 3, 8])` walks: `1` → predicate True → drop; `4` → predicate True → drop; `6` → predicate False → *transition to pass phase* → yield `6`; `3` → *pass phase, no check* → yield `3` (even though `3 < 5` is True); `8` → *pass phase* → yield `8`. The result is `[6, 3, 8]`. The `3` survives because `dropwhile` already committed to the pass phase.

**Why does `dropwhile` not re-check after the transition?** Because the contract is "drop the *prefix* while the predicate is True" — a prefix is a contiguous leading slice. Once the predicate fails at position `k`, the prefix is `[0..k-1]` and everything from `k` onward is the *rest*, regardless of whether later elements would individually satisfy the predicate. The per-element reading (drop *each* True element) is what `filter(lambda x: not pred(x), iterable)` does — `filterfalse` is the per-element complement, and `dropwhile` is the positional prefix-drop. The two functions solve different problems; the student who confuses them gets the wrong result.

### Lines 46–49: The boardly `dropwhile` — skip the boot prefix

```python
    # Boardly: skip leading system_boot rows, yield the rest (including the stray)
    real_stream = itertools.dropwhile(lambda t: t.status == "system_boot", stream)
    print("dropwhile(system_boot, stream) — first 4 titles after the prefix:")
    for t in itertools.islice(real_stream, 4):
        print(f"  [{t.status:12}] {t.title}")
```

The boardly use case: `dropwhile(lambda t: t.status == "system_boot", stream)` drops the first three rows (the boot prefix) and then yields the rest. `islice(real_stream, 4)` takes the first four yielded rows: row 4 (`Search returns 500`, todo), row 5 (`Auth fails on macOS`, todo), row 6 (`Export to CSV`, in_progress), row 7 (`Docs typo`, done). The stray boot row at position 8 is *not* in the first four — but if we extended the `islice` to `8`, we would see it yielded (because the pass phase doesn't re-check). The `islice(..., 4)` here is the bound — same pattern as lesson 5, applied to a `dropwhile` output stream.

The `islice` bound is the senior-engineer move because `dropwhile`'s output is itself a one-shot iterator — if you `list()` it, you materialise everything; if you `for t in real_stream:` without a bound, you iterate everything. `islice(real_stream, 4)` is the "peek at the first four, then stop" form, exactly the laziness lesson 01 taught.

**Why `dropwhile` over a `for` loop with a state flag?** Because the state-flag form is fragile. The hand-written equivalent is:
```python
seen_first_real = False
for t in stream:
    if not seen_first_real and t.status == "system_boot":
        continue
    seen_first_real = True
    yield t
```
This works, but the flag bookkeeping (`seen_first_real = False` initialiser, the `if not seen_first_real and ...` guard, the `seen_first_real = True` assignment) is three places to get wrong. `dropwhile(lambda t: t.status == "system_boot", stream)` is one expression with no flag. The CPython implementation is in `itertoolsmodule.c`'s `dropwhile_next` — a tiny state machine with two phases, exactly the flag form above, but in C and bug-free. The senior-engineer move: use the C-accelerated form, not the hand-written flag loop.

### Lines 53–63: `takewhile` — yield while True, then STOP at the first False

```python
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
```

`itertools.takewhile(predicate, iterable)` is the *mirror* of `dropwhile`'s prefix contract — but with a different stopping rule. *While* the predicate returns `True`, the element is *yielded*. The *first* element for which the predicate returns `False` is *not* yielded, and `takewhile` *stops* — it raises `StopIteration` on the next `__next__` call, never looking at any later elements. Internally, `takewhile` has one phase: call the predicate; if True, yield; if False, raise `StopIteration` *and never resume*.

`takewhile(lambda x: x < 5, [1, 4, 6, 3, 8])` walks: `1` → predicate True → yield `1`; `4` → predicate True → yield `4`; `6` → predicate False → *raise StopIteration*. The `3` and the `8` are *never seen*. The result is `[1, 4]`. The `3` (which would individually satisfy the predicate) is *not* yielded, because `takewhile` does not resume after the first False.

The boardly use case: `takewhile(lambda t: t.status == "todo", stream_after_boot)` yields the leading todos from the post-boot slice. `stream_after_boot = stream[3:]` skips the three boot rows so the first element `takewhile` sees is `Search returns 500` (todo). It walks: row 4 (`todo` → yield), row 5 (`todo` → yield), then row 6 (`in_progress` → False → *raise StopIteration*). Rows 7–10 are never seen — *including row 9*, the reopened `todo` ticket (`Reopen: search bug`). The output is two titles: `Search returns 500` and `Auth fails on macOS`. The reopened todo is invisible to `takewhile` because the predicate already returned False at row 6.

**Why does `takewhile` not resume after the first False?** Because the contract is "take the *prefix* while the predicate is True" — a contiguous leading slice, terminated by the first False. Once the predicate fails at position `k`, the prefix is `[0..k-1]` and the iterator is *done*; there is no second prefix to take. The student who expects `takewhile` to "find all the elements where the predicate is True" is reaching for `filter`, not `takewhile`. `filter(predicate, iterable)` is the per-element form — it checks every element and yields each one whose predicate returns True, regardless of position. `takewhile` is the positional form — it stops at the first False, period.

**Why is the "takewhile stops early" behaviour the gotcha?** Because it's invisible on a clean fixture. `takewhile(lambda x: x < 5, [1, 4, 3, 2])` yields `[1, 4, 3, 2]` — the predicate is True for every element, so the stop never triggers. The student concludes "`takewhile` takes each element that satisfies the predicate" and writes `takewhile(lambda x: x < 5, [1, 4, 6, 3, 8])` expecting `[1, 4, 3]`. The actual result is `[1, 4]`. The fixture in this lesson deliberately includes the `3` *after* the `6` to make the trap visible — the student who runs the demo sees the trap *in the output*, not just in the docstring.

### Lines 66–78: `filterfalse` — the complement of `filter`

```python
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
```

`itertools.filterfalse(predicate, iterable)` is the per-element complement of `filter`. Where `filter(predicate, iterable)` yields elements where `predicate(elem)` is `True`, `filterfalse` yields elements where `predicate(elem)` is `False`. The two cover the entire iterable with no overlap and no gaps: `list(filter(p, it)) + list(filterfalse(p, it)) == list(it)` (in some order). Internally, `filterfalse` is a thin wrapper around the same machinery `filter` uses — it just inverts the predicate's result.

`filterfalse(lambda x: x % 2 == 0, [1, 2, 3, 4, 5])` walks: `1` → `1 % 2 == 0` is `False` → `not False` is `True` → yield `1`; `2` → `2 % 2 == 0` is `True` → `not True` is `False` → skip; `3` → `False` → yield `3`; `4` → `True` → skip; `5` → `False` → yield `5`. The result is `[1, 3, 5]` — the odds. The complement of `filter(even, [1,2,3,4,5])` which yields `[2, 4]`.

**The `None` predicate form:** `filterfalse(None, iterable)` yields elements that are falsy — the complement of `filter(None, iterable)` which yields truthy elements. `filterfalse(None, [0, 1, 2, None, 3, "", "x", [], [1]])` yields `[0, None, "", []]` — the falsy ones. This is the form the docs call "the falsy elements of the iterable". The same `None` convention applies to `filter` (`filter(None, it)` yields the truthy elements) and is documented at `https://docs.python.org/3/library/functions.html#filter`.

The boardly use case: `filterfalse(lambda t: t.status in WATCH, stream)` yields tickets whose status is *not* in `WATCH` — the "don't page me on these" view, the complement of `filter(lambda t: t.status in WATCH, stream)` which is the watched view. Walking the fixture: rows 1–3 (`system_boot`, not in WATCH → yield), row 4 (`todo` → yield), row 5 (`todo` → yield), row 6 (`in_progress` → skip), row 7 (`done` → yield), row 8 (`system_boot` → yield), row 9 (`todo` → yield), row 10 (`blocked` → skip). The result is eight tickets — everything except the `in_progress` and `blocked` ones.

**Why `filterfalse` over `filter(lambda x: not pred(x), iterable)`?** Three reasons. First, the inversion is built into the C-level `filterfalse` — there's no extra `lambda` wrapper, no extra Python function call per element. `filterfalse(p, it)` is one C-level call per element; `filter(lambda x: not p(x), it)` is two (the lambda, then `not`, then `p`). For a million-row stream, that's a million extra function calls. Second, the name `filterfalse` reads as "filter where False" — the intent is explicit at the call site. `filter(lambda x: not p(x), it)` requires the reader to mentally invert the lambda to understand what's being kept. Third, the `None` predicate form (`filterfalse(None, it)` to get falsy elements) has no clean equivalent with `filter` — `filter(lambda x: not x, it)` works but reads as "keep elements where `not x` is True", which is more convoluted than "keep falsy elements".

### Lines 81–89: `main` and the entry point

```python
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
```

Same entry point pattern as lesson 5. Each demo prints a header, runs the per-element example, then runs the boardly example. The blank line between demos makes the three sections visually distinct in the terminal.

## Execution Trace

```bash
$ uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py
=== dropwhile: drop prefix while True, then yield the rest ===
dropwhile(<5, [1, 4, 6, 3, 8]) -> [6, 3, 8]   # note 3 is yielded even though <5
dropwhile(system_boot, stream) — first 4 titles after the prefix:
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  [in_progress ] Export to CSV
  [done        ] Docs typo

=== takewhile: yield while True, then STOP at first False ===
takewhile(<5, [1, 4, 6, 3, 8]) -> [1, 4]   # note 3 is NOT yielded (stop at 6)
takewhile(status == 'todo', stream_after_boot) — leading todos only:
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  (stops at first non-todo; the later 'Reopen: search bug' todo is NOT reached)

=== filterfalse: yield where predicate is False (complement of filter) ===
filterfalse(even, [1, 2, 3, 4, 5]) -> [1, 3, 5]   # the odds (complement of filter)
filterfalse(None, [0, 1, 2, None, 3, '', 'x', [], [1]]) -> [0, None, '', []]   # the falsy elements
filterfalse(status in WATCH, stream) — tickets NOT watched:
  [system_boot] [boot] pipeline ready
  [system_boot] [boot] db pool warmed
  [system_boot] [boot] scheduler started
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  [done        ] Docs typo
  [system_boot] [boot] redeploy at noon
  [todo        ] Reopen: search bug
```

The first block shows `dropwhile`'s positional contract: `dropwhile(<5, [1,4,6,3,8])` yields `[6, 3, 8]` — the `3` survives because `dropwhile` does not re-check after the first False (the transition from drop-phase to pass-phase happens at `6`). The boardly demo shows the leading three boot rows dropped, and the first four real tickets yielded: `Search returns 500` (todo), `Auth fails on macOS` (todo), `Export to CSV` (in_progress), `Docs typo` (done). The `islice(real_stream, 4)` bound stops before the stray boot row, but the stray would have been yielded if the bound were larger.

The second block shows `takewhile`'s positional contract: `takewhile(<5, [1,4,6,3,8])` yields `[1, 4]` — the `3` is *not* yielded because `takewhile` stops at `6` and never resumes. The boardly demo shows the leading two todos yielded, and the iteration stops at row 6 (`Export to CSV`, in_progress). The reopened `todo` ticket at row 9 is *never reached* — the explicit `print` line below the loop calls this out.

The third block shows `filterfalse`'s per-element contract: `filterfalse(even, [1,2,3,4,5])` yields `[1, 3, 5]` (the odds); `filterfalse(None, [...])` yields `[0, None, '', []]` (the falsy elements). The boardly demo yields every ticket whose status is *not* in `WATCH` — eight tickets, skipping the `in_progress` (`Export to CSV`) and `blocked` (`Synonym expansion slow`) rows. Note that the stray `system_boot` row at position 8 *is* yielded — `filterfalse` is per-element, not positional, so the stray boot row is treated like any other non-watched ticket.

## Common Mistakes

### Mistake 1: Reading `dropwhile` as "drop each True element"

```python
import itertools
# Wrong reading: "drop each element where x < 5"
result = list(itertools.dropwhile(lambda x: x < 5, [1, 4, 6, 3, 8]))
# Student expects: [6, 8]   (the elements where x >= 5)
# Actual:          [6, 3, 8]  (everything after the first False, including 3)
```

**Symptom:** The result has more elements than expected — specifically, it includes elements that *would* satisfy the predicate but appear after the first False.

**Why:** `dropwhile` is a *positional* filter, not a per-element filter. It drops a contiguous *prefix* of elements while the predicate is True, then yields *everything* that follows without re-checking. The per-element reading ("drop each True element") is what `filterfalse(predicate, iterable)` does.

**Fix:** If you want "drop each True element", use `filterfalse(predicate, iterable)`. If you want "drop the leading prefix until the first False, then yield the rest", use `dropwhile`. The two functions have different contracts; mixing them up is the most common `itertools` predicate-filter bug.

### Mistake 2: Reading `takewhile` as "take each True element" (the stops-early gotcha)

```python
import itertools
# Wrong reading: "take each element where x < 5"
result = list(itertools.takewhile(lambda x: x < 5, [1, 4, 6, 3, 8]))
# Student expects: [1, 4, 3]   (all elements where x < 5, in order)
# Actual:          [1, 4]       (stops at 6, never reaches 3)
```

**Symptom:** The result has *fewer* elements than expected — specifically, it omits elements that *would* satisfy the predicate but appear after the first False.

**Why:** `takewhile` is a *positional* filter. It yields a contiguous *prefix* while the predicate is True, then *stops* at the first False and never resumes. The per-element reading ("take each True element") is what `filter(predicate, iterable)` does. The two functions have different contracts.

**Fix:** If you want "take each True element", use `filter(predicate, iterable)` or a list comprehension `[x for x in iterable if pred(x)]`. If you want "take the leading prefix until the first False, then stop", use `takewhile`. The trap is invisible on a clean fixture (where the predicate is True for every element), so the test case *must* include a False-then-True sequence to surface the gotcha.

### Mistake 3: `filterfalse` with `None` to get truthy elements

```python
import itertools
# Wrong: filterfalse(None, ...) gives FALSY elements, not truthy
truthy = list(itertools.filterfalse(None, [0, 1, 2, None, 3]))
# Student expects: [1, 2, 3]   (the truthy elements)
# Actual:          [0, None]    (the FALSY elements — the complement of filter(None, ...))
```

**Symptom:** The result is the *opposite* of what the student expects — the elements they wanted to keep are missing, and the elements they wanted to drop are present.

**Why:** `filterfalse(None, iterable)` yields elements that are *falsy* — the complement of `filter(None, iterable)` which yields the truthy elements. The `None` predicate is interpreted as the identity function (`lambda x: x`), and `filterfalse` inverts the result. So `filterfalse(None, it)` is `filterfalse(lambda x: bool(x), it)` — keep elements where `bool(x)` is False.

**Fix:** For truthy elements, use `filter(None, iterable)` (no `itertools` import). For falsy elements, use `filterfalse(None, iterable)`. The mnemonic: `filter` keeps where True; `filterfalse` keeps where False. With `None` as the predicate, "where True" means "where the element itself is truthy" and "where False" means "where the element itself is falsy".

## Engineering Trade-Offs

**Decision:** Use `dropwhile` for "skip the leading prefix until a condition fails, then yield the rest", `takewhile` for "take the leading prefix until a condition fails, then stop", and `filterfalse` for "yield each element where the predicate is False". Never substitute one for another — the three contracts are different and the trap is silent on a clean fixture.

**Both sides:** The alternative to `dropwhile` and `takewhile` is a hand-written `for` loop with a state flag (the form shown in the `dropwhile` deep dive). The hand-written form works but is fragile — three places to get the flag bookkeeping wrong, three places a future maintainer can break the contract. The alternative to `filterfalse` is `filter(lambda x: not p(x), iterable)` — works, but adds a `lambda` wrapper and a Python-level `not` per element. The `itertools` forms are C-accelerated, named, and grep-friendly. The hand-written forms are slower, anonymous, and easy to mis-edit.

**Commitment:** `boardly` uses `dropwhile` in `boardly/tickets/stream_filters.py` for the boot-prefix skip (the call site is `dropwhile(lambda t: t.status == "system_boot", stream)`, paired with an `islice` bound). `boardly` uses `takewhile` in `boardly/tickets/leading_open.py` for the "leading open tickets" view (the call site is `takewhile(lambda t: t.status == "todo", stream)`, with an explicit comment that reopened tickets are out of scope). `boardly` uses `filterfalse` in `boardly/tickets/not_watched_view.py` for the complement-of-watch-list view (the call site is `filterfalse(lambda t: t.status in WATCH, stream)`). The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to these three patterns and explicitly bans the hand-written flag-loop equivalents.

**Why ban the hand-written flag loop?** Because the flag loop is the bug that ends incidents. The classic failure mode: a maintainer adds an early `continue` inside the loop body (e.g. to skip a malformed row), and the `seen_first_real = True` assignment is now conditional on the malformed-row check passing — the flag stays `False` forever, the prefix is never dropped, and the bug surfaces only when a malformed row appears in production. `dropwhile(lambda t: t.status == "system_boot", stream)` is one expression with no flag — the C-level state machine is bug-free because there's no user-modifiable flag to get wrong. The senior-engineer rule: if you can express the contract as a single `itertools` call, do; the hand-written loop is the fallback only when the contract is more complex than `itertools` supports.

## Exercises

1. **Exercise 1 — Add a second `dropwhile` bound.** In `dropwhile_demo`, change the `islice(real_stream, 4)` bound to `6` and re-run. Verify that the stray boot row (`[boot] redeploy at noon`) is yielded at position 5 — confirming that `dropwhile`'s pass phase does not re-check the predicate. `Verify: uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py`

2. **Exercise 2 — Replace `takewhile` with `filter`.** Rewrite `leading_todos = itertools.takewhile(lambda t: t.status == "todo", stream_after_boot)` as `leading_todos = filter(lambda t: t.status == "todo", stream_after_boot)`. Verify the output now includes *all* todo tickets in the post-boot slice — including the reopened one at row 9. Articulate the trade-off: `filter` is the per-element form (yields each matching ticket); `takewhile` is the positional form (yields the leading prefix only). `Verify: uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py`

3. **Exercise 3 — `filterfalse` vs `filter(not ...)`.** Replace `not_watched = itertools.filterfalse(lambda t: t.status in WATCH, stream)` with `not_watched = filter(lambda t: t.status not in WATCH, stream)`. Verify the output is identical. Then articulate: `filterfalse(p, it)` and `filter(lambda x: not p(x), it)` are semantically equivalent, but `filterfalse` is one C-level call per element while the `filter(lambda x: not p(x), ...)` form adds a `lambda` wrapper and a Python-level `not`. `Verify: uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py`

4. **Exercise 4 — Compose `takewhile` with `islice`.** Write a line that takes the leading three todos from the post-boot slice — `islice(takewhile(lambda t: t.status == "todo", stream_after_boot), 3)`. Verify the output is just the first two (`Search returns 500`, `Auth fails on macOS`) because `takewhile` stops at the third position (the first non-todo). This exercise demonstrates that `islice`'s bound on a `takewhile` output is a *maximum*, not a guaranteed length. `Verify: uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py`

5. **Exercise 5 — The streaming log analyser.** Build an `analyse_log(stream)` function that uses all three filters: (1) `dropwhile` to skip the boot prefix, (2) `takewhile` to take the first "incident window" (while `priority >= 3`), and (3) `filterfalse` to find the tickets in the window whose status is *not* in `WATCH`. The exercise demonstrates the three filters compose — each consumes the output of the previous. `Verify: uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_dropwhile_takewhile_filterfalse_demo.py
=== dropwhile: drop prefix while True, then yield the rest ===
dropwhile(<5, [1, 4, 6, 3, 8]) -> [6, 3, 8]   # note 3 is yielded even though <5
dropwhile(system_boot, stream) — first 4 titles after the prefix:
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  [in_progress ] Export to CSV
  [done        ] Docs typo

=== takewhile: yield while True, then STOP at first False ===
takewhile(<5, [1, 4, 6, 3, 8]) -> [1, 4]   # note 3 is NOT yielded (stop at 6)
takewhile(status == 'todo', stream_after_boot) — leading todos only:
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  (stops at first non-todo; the later 'Reopen: search bug' todo is NOT reached)

=== filterfalse: yield where predicate is False (complement of filter) ===
filterfalse(even, [1, 2, 3, 4, 5]) -> [1, 3, 5]   # the odds (complement of filter)
filterfalse(None, [0, 1, 2, None, 3, '', 'x', [], [1]]) -> [0, None, '', []]   # the falsy elements
filterfalse(status in WATCH, stream) — tickets NOT watched:
  [system_boot] [boot] pipeline ready
  [system_boot] [boot] db pool warmed
  [system_boot] [boot] scheduler started
  [todo        ] Search returns 500
  [todo        ] Auth fails on macOS
  [done        ] Docs typo
  [system_boot] [boot] redeploy at noon
  [todo        ] Reopen: search bug
```

## Previously Learned Here

- [[07-itertools/05-cycle-repeat-count]] — the three infinite iterators. This lesson builds on the laziness model the infinite iterators taught: every `dropwhile`/`takewhile`/`filterfalse` is a one-shot iterator that produces values on demand and never materialises its input.
- [[07-itertools/01-chain-and-islice]] — `chain` and `islice`. The `islice` bound on the `dropwhile` output stream (line 47) is the same `islice` bound from lesson 01, applied to a *filtered* stream rather than a *chained* stream.
- [[18-operator/03-functional-composition]] — the `WATCH` set and the `partial(operator.contains, WATCH)` predicate factory. The `filterfalse(lambda t: t.status in WATCH, stream)` form is the function-form alternative to `partial(operator.contains, WATCH)` — the two are interchangeable, and the lesson uses the `lambda` form for clarity.

## What's Next

[[07-itertools/07-tee-and-zip_longest]] — `tee` and `zip_longest`. Where this lesson taught the three predicate filters that *consume* a single iterator, the next lesson teaches the two `itertools` functions that *fork* a single iterator into multiple independent iterators (`tee`) and *zip* iterables of unequal lengths with a `fillvalue` (`zip_longest`). The "tee is not free" lesson — the internal queue that grows when one fork advances far ahead of another — is the memory-cost gotcha the next lesson is built around.

- `tee(iterable, n=2)` — split a single-pass iterator into n independent iterators; WARNING: the original iterable should not be used after `tee`.
- `zip_longest(*iterables, fillvalue=None)` — zip with a `fillvalue` for the missing positions; `zip_longest([1,2,3], [4,5], fillvalue=0)` → `(1,4),(2,5),(3,0)`.
- The memory-growth demo with `islice` showing the lagging fork's queue growing.

## Sources

- **`itertools` — Functions creating iterators for efficient looping** — https://docs.python.org/3/library/itertools.html — accessed 2026-10-23 — the canonical reference for `dropwhile`, `takewhile`, `filterfalse`, and the rest of the `itertools` family.
- **`itertools.dropwhile`** — https://docs.python.org/3/library/itertools.html#itertools.dropwhile — accessed 2026-10-23 — the prefix-drop iterator; documents the "drop while predicate is true, then yield the rest" contract that the per-element-reading student gets wrong.
- **`itertools.takewhile`** — https://docs.python.org/3/library/itertools.html#itertools.takewhile — accessed 2026-10-23 — the prefix-take iterator; documents the "yield while predicate is true, then stop" contract that the stops-early gotcha turns into a production bug.
- **`itertools.filterfalse`** — https://docs.python.org/3/library/itertools.html#itertools.filterfalse — accessed 2026-10-23 — the complement-of-`filter` iterator; documents the `None` predicate form (yield falsy elements).
- **`filter`** — https://docs.python.org/3/library/functions.html#filter — accessed 2026-10-23 — the builtin per-element filter; the canonical alternative to `takewhile` when you want all matching elements, not just the leading prefix.

## What We Learned

- You can apply `dropwhile(predicate, iterable)` — drop the leading prefix while the predicate is True, then yield *everything that follows* without re-checking (the `3` survives in `[1,4,6,3,8]`).
- You can apply `takewhile(predicate, iterable)` — yield while the predicate is True, then *STOP* at the first False, never resuming (the `3` is *not* yielded in `[1,4,6,3,8]`).
- You can apply `filterfalse(predicate, iterable)` — yield where `predicate(elem)` is False; `filterfalse(None, it)` yields the falsy elements.
- You can articulate the boundary asymmetry between `dropwhile` and `takewhile` — same predicate, opposite stopping rules.
- You can state the "takewhile stops early" gotcha — `takewhile` does not resume after the first False, so later elements that *would* satisfy the predicate are never seen.
