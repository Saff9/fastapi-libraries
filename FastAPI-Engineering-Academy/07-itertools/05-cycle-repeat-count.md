---
title: "Lesson 05: cycle, repeat, count — the three infinite iterators"
aliases:
 - itertools cycle
 - itertools repeat
 - itertools count
 - infinite iterators
tags:
 - itertools
 - infinite-iterators
 - streaming
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[05-collections-abc/04-Iterator-vs-Iterable]]"
 - "[[04-collections/03-deque]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[07-itertools/06-dropwhile-takewhile-filterfalse]]"
 - "[[07-itertools/07-tee-and-zip_longest]]"
 - "[[02-functools/03-partial]]"
---

# Lesson 05: `cycle`, `repeat`, `count` — the three infinite iterators

*The three `itertools` functions that never raise `StopIteration` on their own — `cycle` loops a finite iterable forever, `repeat` yields one element N times (or forever), `count` produces an arithmetic sequence that walks to infinity — and the `islice(..., n)` bound that makes each of them safe.*

**You're at the very beginning of Section 07.**

`itertools` is the algebra of lazy iterators. Most of the module — `chain`, `islice`, `groupby`, `starmap` — wraps a finite iterable and produces another finite iterable. Three functions break that pattern on purpose: `cycle`, `repeat`, and `count`. Each returns an iterator that has no natural end. If you `list(count())` you will hang the interpreter; if you `for x in cycle([1,2,3]): ...` without a `break` you will hang the interpreter. The skill this lesson teaches is *how to bound an infinite iterator* — the `islice(cycle(...), n)` pattern, the `map(func, data, repeat(const))` filler pattern, and the `zip(count(1), data)` enumeration idiom — so the three infinite iterators become the most useful laziness primitives in the standard library. Take your time. Type every example. **This is how you learn.**

#itertools #infinite-iterators #streaming

## Learning Objectives

By the end of this lesson you will be able to:

1. **Bound an infinite iterator with `islice`** — write `list(islice(cycle([1,2,3]), 7))` and predict `→ [1, 2, 3, 1, 2, 3, 1]` without running it.
2. **Use `for x in cycle(...)` with a break** — the only safe way to consume a `cycle` in a `for` loop, and the canonical "round-robin status" boardly pattern.
3. **Use `repeat` as a `map` filler** — write `map(func, varying, repeat(const))` and explain why `repeat(const)` is the trick that lets `map` accept a constant second argument without `partial`.
4. **Use `count` for 1-indexed enumeration** — write `zip(count(1), data)` and explain why it beats `enumerate(data, start=1)` for streams you need to slice, and when `enumerate` still wins.
5. **State the rule** that every infinite iterator in production code has a bound — `islice`, `takewhile`, `zip` with a finite iterable, or an explicit `break` — and that "I forgot the bound" is the second most common `itertools` production bug (after "I forgot `groupby` needs sorted input").

## Prerequisites

Before starting, you need:

- **`itertools.islice`** — the bound primitive. [[07-itertools/01-chain-and-islice]] is the canonical lesson: `islice(iterable, stop)` or `islice(iterable, start, stop, step)` slices an iterator without materialising it. This lesson uses `islice(cycle(...), n)` to bound infinite iterators.
- **`collections.deque`** — [[04-collections/03-deque]] covers the C-accelerated queue that `cycle`'s internal cache is conceptually modelled on. You don't need to read deque's internals to use `cycle`, but the cross-link matters: `cycle` caches every yielded item in an internal list-shaped pool so it can replay them on the next pass, and the memory cost (O(n) where n is the source length) is the same kind of "buffer holds the gap" cost `deque` teaches.
- **A typed model to attach the demo to** — [[06-dataclasses/01-dataclass-Basics]] for the `Project`/`Ticket` shape we reuse across the section.
- **About 25–35 minutes of focused time.**

**The most common gap: forgetting that `cycle`/`repeat`/`count` are infinite.**

The student runs `list(itertools.count())` in a REPL, watches the CPU spin to 100%, hits `Ctrl-C`, and learns the lesson the hard way. The three infinite iterators are *designed* to walk to infinity — that is their power, not a bug — but every call site must bound them. The fix is mechanical: every `cycle` call is followed by either `islice`, `zip` with a finite iterable, or a `for` loop with an explicit `break`; every `repeat(x)` (no `times=`) call is followed by `islice`, `zip`, or `map` with a finite second arg; every `count()` call is followed by `islice` or `zip`. If you see a bare `cycle`/`repeat`/`count` with no bound, it's a bug.

## The Problem

`boardly/rotations/scheduler.py` has three real tasks that loops cannot express cleanly:

1. **Round-robin ticket assignment.** Three engineers (Alice, Bob, Carol) are on-call this week. New tickets arrive in a stream; assign them round-robin. A naive `while True` loop with an index counter works, but the index bookkeeping is fragile (`idx = (idx + 1) % len(engineers)` on every iteration, easy to forget, easy to get wrong with off-by-ones). `cycle(engineers)` produces the assignment stream directly.

2. **Pad a list of ticket IDs with a constant owner.** The audit log needs `[(ticket_id, default_owner_id), ...]` for every ticket — a `map(lambda tid, owner=DEFAULT: (tid, owner), ticket_ids)` works but the `lambda` with `owner=` keyword closure is the kind of "I'm being clever" code that gets flagged in review. `map(lambda tid, owner: (tid, owner), ticket_ids, repeat(DEFAULT_OWNER))` is the textbook `map` + `repeat` filler form — no closure, no `partial`, no cleverness.

3. **1-indexed enumeration that you can slice.** `enumerate(tickets, start=1)` produces `[(1, t0), (2, t1), ...]` — fine for printing, but `enumerate` returns an iterator that you cannot pass `start`/`stop` to. `zip(count(1), tickets)` produces the same pairs and is composable with `islice` — `islice(zip(count(1), tickets), 5, 10)` gives you the 6th through 10th enumerated pairs, which `enumerate` cannot express.

The three tasks have the same shape: "produce an iterator that walks an unbounded sequence, but stop it the moment I tell it to stop". The three `itertools` infinite iterators are the three primitives that match that shape — and this lesson is the line-by-line tour.

## The Code

```python
# boardly/itertools_infinite_iterators_demo.py
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
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the `Ticket` model

```python
# boardly/itertools_infinite_iterators_demo.py
"""The three infinite iterators: cycle, repeat, count."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
```

`itertools` is the only import that matters for this lesson. `dataclass` and `UUID` build the `Ticket` shape we reuse across the `itertools` section — same shape as [[18-operator/03-functional-composition]] uses, so the student sees continuity. `from __future__ import annotations` is boardly's house style (see [[13-future/01-from-future-import-annotations]]); it delays annotation evaluation so `Ticket` can be referenced before it's defined and so type hints cost nothing at runtime.

The `Ticket` is the minimal frozen dataclass we need: an `id` and a `title`. We don't need `status`/`priority`/`weight` for this lesson — the three infinite iterators are about *sequences* and *constants*, not about per-ticket filtering. The next lesson ([[07-itertools/06-dropwhile-takewhile-filterfalse]]) will widen `Ticket` to include `status` so the predicate filters have something to filter on.

**Why not `from itertools import cycle, repeat, count`?** Because the qualified name `itertools.cycle` reads better at the call site — the student can see at a glance that the call is an `itertools` call, not a builtin. The boardly style guide commits to `import itertools` and qualified calls; the four-character saving from `from itertools import *` is not worth the loss of grep-ability.

### Lines 13–18: Fixture data

```python
# --- Fixture ---
engineers = ["alice", "bob", "carol"]            # on-call rotation
ticket_ids = [f"T-{n}" for n in range(1, 8)]     # 7 incoming tickets
default_owner = "unassigned"
projects = ["Search", "Auth", "Docs", "Export"]   # 4 active projects
```

Four fixture values, each chosen to make a different infinite iterator demo land cleanly. `engineers` has 3 names — the round-robin `cycle(engineers)` will produce `alice, bob, carol, alice, bob, carol, alice` when bounded at 7 (one more than a multiple of 3, so the rotation visibly wraps). `ticket_ids` has 7 entries — paired with `assignments` from `cycle`, every ticket gets an owner and the wrap is visible. `default_owner` is a single string used as the constant second arg in the `map` filler pattern. `projects` has 4 entries — paired with `count(1)`, the demo shows 1-indexed enumeration cleanly (1 through 4) and the `islice(zip(...), 1, 3)` row-slice demo takes rows 2 and 3.

The fixture is module-level so each `def demo()` function can read it without passing it as an argument. This is the same pattern [[18-operator/03-functional-composition]] uses for `tickets` — the lesson's job is to teach the iterator, not the test-harness plumbing.

### Lines 22–37: `cycle` — the round-robin assignment

```python
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
```

`itertools.cycle(iterable)` returns an iterator that yields each element of `iterable` in order, then starts again from the beginning, forever. `cycle([1, 2, 3])` yields `1, 2, 3, 1, 2, 3, 1, 2, 3, ...` — there is no natural end. The bounded form `islice(cycle(engineers), 7)` takes exactly the first 7 values: `['alice', 'bob', 'carol', 'alice', 'bob', 'carol', 'alice']`. The `list()` materialises them so we can `zip` them with `ticket_ids`.

Internally, `cycle` saves every item it yields into an internal cache (a list-shaped pool in CPython's `itertoolsmodule.c`). The first pass through `iterable` populates the cache as items are pulled; once the source is exhausted, `cycle` replays from the cache forever — the original `iterable` is read only once. The cache grows with each item yielded up to the source length, regardless of whether the source is a sequence (`list`, `tuple`, `str`) or a non-sequence iterator (`generator`, `map`, `filter`) — `cycle` does not special-case sequences for indexing. The memory cost is O(n), where n is the source length. The one escape hatch: if you bound the iteration with `islice(cycle([1,2,3]), 7)` and the bound is less than one full pass (3), only the bound-many items are cached; once the bound crosses a full pass, the cache holds the full source.

The unbounded form `for n, who in enumerate(itertools.cycle(engineers))` is the only safe way to consume a `cycle` in a `for` loop without `islice`. The `if n >= 5: break` is the bound. Without the `break`, this loop runs forever — exactly the failure mode the prerequisites warned about. The `enumerate` is here only to give us a counter for the break condition; it doesn't bound the `cycle` itself.

**Why `islice(cycle(...), n)` rather than `for x in cycle(...): ...; if condition: break`?** Because the `islice` form composes. `zip(ticket_ids, islice(cycle(engineers), len(ticket_ids)))` is one expression that produces the round-robin pairs directly — no loop, no counter, no break. The `for x in cycle(...): break` form is what you write when the bound depends on a runtime condition that isn't a simple count (e.g. "stop when the next ticket's status changes"). For pure count-based bounds, `islice` wins.

**Why is the `for x in cycle(...): break` form here at all if `islice` is better?** Because it teaches the rule: a bare `for x in cycle(...)` without a `break` is a hang, and the student who sees the `break` form once internalises that `cycle` is infinite. The rule, restated: every `cycle` call site must have a bound, and the bound is either `islice`, `zip` with a finite iterable, or an explicit `break` in a `for` loop.

### Lines 40–54: `repeat` — the `map` filler

```python
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
```

`itertools.repeat(elem, times=None)` returns an iterator that yields `elem` repeatedly. With `times=N`, it yields `elem` exactly `N` times and then raises `StopIteration`. With `times=None` (the default), it yields `elem` forever — same infinite contract as `cycle` and `count`. The first three prints show the three shapes: `repeat(2, 3)` → `[2, 2, 2]`, `repeat('x', 0)` → `[]` (zero repeats), `islice(repeat(2), 4)` → `[2, 2, 2, 2]` (the bound form for the infinite `repeat(2)`).

The `map` filler pattern is the killer feature of `repeat`. `map(func, iterable1, iterable2)` calls `func(a, b)` for each pair `(a, b)` drawn from the two iterables, stopping when the *shorter* iterable is exhausted. Pair a finite iterable (`ticket_ids`, 7 entries) with an infinite constant iterable (`repeat(default_owner)`, no end) and the finite iterable bounds the `map` — `map` produces exactly 7 pairs, one per ticket ID, with `default_owner` as the constant second arg. No `lambda` closure, no `partial`, no list comprehension with a captured constant — just `map` doing what `map` does, with `repeat` providing the constant.

The `map(pow, range(5), repeat(2))` line is the textbook example. `pow(x, 2)` is `x ** 2`. `range(5)` is `[0, 1, 2, 3, 4]`. `repeat(2)` is `[2, 2, 2, 2, 2, ...]`. `map` zips them: `pow(0, 2), pow(1, 2), pow(2, 2), pow(3, 2), pow(4, 2)` → `[0, 1, 4, 9, 16]`. The `range(5)` bounds the `map`; the `repeat(2)` provides the constant exponent. This is the form the CPython `itertools` documentation uses as the canonical `repeat` example, and it is the form every senior Python engineer recognises.

**Why `repeat` rather than `[default_owner] * len(ticket_ids)`?** Because the multiplication form materialises the entire list before `map` even starts — `[default_owner] * 7` allocates a 7-element list, then `map` reads it. `repeat(default_owner)` is a single C-level iterator object that yields the same string object seven times without ever materialising a list. For 7 items the difference is invisible; for 7 million items the list form allocates 7 million pointer slots and the `repeat` form allocates one iterator. The `repeat` form is the senior-engineer choice for "constant filler in a `map`/`zip`".

**Why `repeat` rather than `functools.partial`?** Because `partial` and `repeat` solve different problems. `partial(func, const)(varying_arg)` pre-binds the *first* argument of a function and returns a one-arg callable — useful when you have a function you want to call with one arg fixed. `repeat(const)` produces a stream that fills the *second* (or third, or Nth) positional argument of a `map` call — useful when you want to keep one of `map`'s multiple iterables constant. For `map(pow, range(5), repeat(2))`, `partial` would be `map(partial(pow, b=2), range(5))` — but `pow`'s second arg is positional, and `partial(pow, b=2)` raises `TypeError` because `pow` doesn't take a `b` keyword. `repeat` is the right tool; `partial` is the wrong tool. The two modules are *designed* to be complementary, not redundant.

### Lines 57–73: `count` — the 1-indexed enumeration

```python
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
```

`itertools.count(start=0, step=1)` returns an iterator that yields `start`, `start + step`, `start + 2*step`, ... forever. The first three prints show three arithmetic sequences: `count(10)` is `10, 11, 12, 13, 14, ...`; `count(10, -1)` is `10, 9, 8, 7, 6, ...` (a count-down); `count(0, 2)` is `0, 2, 4, 6, 8, ...` (the even naturals). All three are bounded with `islice(..., 5)` — without the bound, `list(count(10))` hangs the interpreter.

The 1-indexed enumeration pattern is `zip(count(1), data)`. `zip` stops when the *shorter* iterable is exhausted; `count(1)` is infinite, so `data` (finite) bounds the `zip`. The result is `[(1, 'Search'), (2, 'Auth'), (3, 'Docs'), (4, 'Export')]` — exactly what `enumerate(projects, start=1)` produces. The two forms are equivalent for plain enumeration.

The composability win is on the last block: `islice(zip(count(1), projects), 1, 3)`. This takes the enumerated pairs from index 1 (inclusive) to index 3 (exclusive) — i.e. pairs 2 and 3: `(2, 'Auth'), (3, 'Docs')`. You cannot express this with `enumerate` because `enumerate` returns a one-shot iterator and you cannot pass a `start`/`stop` to it. The `zip(count(1), data)` form *is* a sliceable iterator — `islice` composes on top of it. This is the senior-engineer reason to reach for `count` over `enumerate`: when you need to slice or skip or window the enumeration, `zip(count(1), data)` is composable and `enumerate(data, start=1)` is not.

**Why `zip(count(1), data)` rather than `enumerate(data, start=1)`?** Because `enumerate` is the right tool for plain enumeration — it's a builtin, it's a C-level fast path, and `enumerate(data, start=1)` is shorter and reads in English. The case for `count` is narrower: when you need to compose the enumeration with `islice` (skip the first N, take a window), `zip(count(1), data)` is composable and `enumerate` is not. For plain "give me a 1-indexed list with my items", use `enumerate`. For "give me the 6th through 10th items, 1-indexed", use `zip(count(1), data)` and `islice` it.

**Why `count(1)` and not `count(0)` for "1-indexed"?** Because `count(1)` produces `1, 2, 3, 4, ...` — the 1-indexed naturals. `count(0)` produces `0, 1, 2, 3, ...` — the 0-indexed naturals, which is what `enumerate(data)` (no `start`) produces by default. The `1` is the start argument; the choice is whether your human-readable display starts at 1 (the convention for ticket IDs, project numbers, line numbers) or 0 (the convention for code, list indices, log offsets).

### Lines 76–84: `main` and the entry point

```python
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
```

Standard boardly entry point: `main()` runs each demo in order, with blank lines between sections. The `if __name__ == "__main__":` guard means `import boardly.rotations.infinite_iterators_demo` doesn't execute the demos — only `uv run python boardly/itertools_infinite_iterators_demo.py` does. This is the same pattern every boardly demo file uses.

## Execution Trace

```bash
$ uv run python boardly/itertools_infinite_iterators_demo.py
=== cycle (round-robin assignment) ===
round-robin assignments:
  T-1 -> alice
  T-2 -> bob
  T-3 -> carol
  T-4 -> alice
  T-5 -> bob
  T-6 -> carol
  T-7 -> alice
first 5 with explicit break:
  0: alice
  1: bob
  2: carol
  3: alice
  4: bob

=== repeat (map filler) ===
repeat(2, 3)      = [2, 2, 2]
repeat('x', 0)    = []
islice(repeat(2), 4) = [2, 2, 2, 2]
audit pairs (ticket_id, default_owner):
  (T-1, unassigned)
  (T-2, unassigned)
  (T-3, unassigned)
  (T-4, unassigned)
  (T-5, unassigned)
  (T-6, unassigned)
  (T-7, unassigned)
map(pow, range(5), repeat(2)) = [0, 1, 4, 9, 16]

=== count (1-indexed enumeration) ===
islice(count(10), 5)       = [10, 11, 12, 13, 14]
islice(count(10, -1), 5)   = [10, 9, 8, 7, 6]
islice(count(0, 2), 5)     = [0, 2, 4, 6, 8]
1-indexed projects (zip(count(1), projects)):
  1. Search
  2. Auth
  3. Docs
  4. Export
enumerated projects, rows 2-3 only (islice(zip(count(1), projects), 1, 3)):
  2. Auth
  3. Docs
```

The first block shows `cycle` producing the round-robin assignments. The 7-ticket fixture wraps the 3-engineer rotation visibly: `alice, bob, carol, alice, bob, carol, alice` — the rotation repeats after every three and the seventh ticket lands on `alice` again, which is what `cycle` is supposed to do. The `for x in cycle(...): break` form on the second block produces the first 5 values `alice, bob, carol, alice, bob` — note the index counter starts at 0 because `enumerate` without `start=` defaults to 0.

The second block shows `repeat` in its three shapes and the two `map` filler uses. `repeat(2, 3) → [2, 2, 2]`; `repeat('x', 0) → []` (zero repeats, empty list); `islice(repeat(2), 4) → [2, 2, 2, 2]` (the bound form for the infinite `repeat(2)`). The audit pairs demo shows 7 pairs `(T-1, unassigned)` through `(T-7, unassigned)`, the constant `default_owner` filling the second slot of each tuple. The `map(pow, range(5), repeat(2))` demo produces the squares `[0, 1, 4, 9, 16]` — `pow(0,2)=0, pow(1,2)=1, pow(2,2)=4, pow(3,2)=9, pow(4,2)=16`.

The third block shows `count` in its three arithmetic shapes and the 1-indexed enumeration. `count(10)` walks up `10..14`; `count(10, -1)` walks down `10..6`; `count(0, 2)` walks the evens `0..8`. The `zip(count(1), projects)` enumeration produces `1. Search, 2. Auth, 3. Docs, 4. Export` — exactly what `enumerate(projects, start=1)` would. The `islice(zip(...), 1, 3)` row-slice produces only `2. Auth, 3. Docs` — the composability win over `enumerate`.

## Common Mistakes

### Mistake 1: `list(itertools.count())` — the bare infinite iterator

```python
import itertools
all_naturals = list(itertools.count())   # ← hangs forever
```

**Symptom:** CPU goes to 100% on one core; the REPL never returns; `Ctrl-C` is the only way out. Memory grows steadily as the list allocates more and more slots.

**Why:** `count()` is infinite by design. `list()` tries to materialise every element, which is impossible for an infinite iterator. The same bug applies to `list(itertools.cycle([1,2,3]))` and `list(itertools.repeat(2))` (with no `times` argument) — all three hang the interpreter.

**Fix:** Always bound the infinite iterator with `islice`, `zip` with a finite iterable, or `takewhile` (see [[07-itertools/06-dropwhile-takewhile-filterfalse]]). The three forms:
```python
list(itertools.islice(itertools.count(), 5))                 # [0, 1, 2, 3, 4]
list(zip(itertools.count(1), ["a", "b", "c"]))               # [(1, 'a'), (2, 'b'), (3, 'c')]
list(itertools.takewhile(lambda x: x < 5, itertools.count())) # [0, 1, 2, 3, 4]
```

### Mistake 2: `cycle` on a generator exhausts the source and silently replays

```python
import itertools
def gen():
    yield from ["a", "b", "c"]
c = itertools.cycle(gen())          # ← gen() is a one-shot generator
# cycle had to consume gen() into an internal cache to replay it.
# Now the original gen() is exhausted — there's no way to "reset" it.
```

**Symptom:** No bug visible to the user — `cycle` works correctly. The hidden cost is memory: `cycle` builds an internal cache that holds every element the source ever yielded, so the cache grows with the source length. For a 3-element source, invisible; for a 7-million-row database cursor, a 7-million-element cache.

**Why:** `cycle` has to be able to replay the source forever, and the source's `__next__` will raise `StopIteration` after one pass. CPython's `cycle` saves every item it yields into an internal list-shaped pool (the `saved` field of `cycleobject` in `itertoolsmodule.c`) and replays from the pool after the source is exhausted. This caching happens regardless of whether the source is a sequence (`list`, `tuple`, `str`) or a non-sequence iterator — `cycle` does not special-case sequences for indexing. The cache is the cost.

**Fix:** Bound the iteration with `islice` when you can — `islice(cycle(source), n)` with `n` less than one full pass means only `n` items are cached, not the whole source. If you genuinely need unbounded `cycle` over a large source, the cache will hold the full source; accept the memory cost explicitly (e.g. `source_list = list(stream); cycle(source_list)`) so the cost is visible at the call site instead of hidden inside `cycle`'s internal pool.

### Mistake 3: `map(func, data, repeat(const))` with the wrong arg count

```python
import itertools
def add_three(a, b, c):
    return a + b + c
# Wrong: only two iterables, but add_three takes three args
result = list(map(add_three, range(3), itertools.repeat(10)))
# TypeError: add_three() missing required argument: 'c'
```

**Symptom:** `TypeError: <func>() missing N required positional arguments` at the `map` call site.

**Why:** `map` calls `func` with one positional arg per iterable passed. Two iterables → two args; three iterables → three args. `repeat(const)` counts as one iterable, no matter how many times it yields. If `func` takes three positional args, you need three iterables — `map(func, data1, data2, repeat(const))`.

**Fix:** Match the arg count to the function signature. `add_three(a, b, c)` needs `map(add_three, data1, data2, itertools.repeat(const))` — three iterables, three positional args. The `repeat(const)` form fills the *last* argument; if you need to fill a *middle* argument, you need a different shape (a `lambda` closure or a `partial` with the const in the right slot — `partial` is awkward for middle args too, so the `lambda` is often the honest answer).

## Engineering Trade-Offs

**Decision:** Use `cycle`, `repeat`, `count` for the three infinite-iterator patterns, and bound each call site with `islice`, `zip` with a finite iterable, or an explicit `break` in a `for` loop. Prefer `enumerate(data, start=1)` for plain 1-indexed enumeration; reach for `zip(count(1), data)` only when you need to compose the enumeration with `islice`.

**Both sides:** The alternative to `cycle` is a hand-written `idx = (idx + 1) % len(items)` counter inside a `while` loop — works, but the index arithmetic is fragile (off-by-ones, modulo bugs, missing-reset-after-modification bugs). The alternative to `repeat` as a `map` filler is `[const] * len(data)` (materialises a list) or a `lambda` with a closure (looks clever, gets flagged in review). The alternative to `count` for enumeration is `enumerate` (a builtin, faster, no import — and the right choice for plain enumeration). The three `itertools` infinite iterators win when you need the lazy, composable, O(1)-memory form of the pattern; they lose to the builtin (`enumerate`) for the plain case.

**Commitment:** `boardly` uses `cycle` in `boardly/rotations/scheduler.py` for the round-robin ticket-assignment stream (the call site is `islice(cycle(engineers), len(ticket_ids))`, materialised into a list and zipped with the ticket IDs). `boardly` uses `repeat` in `boardly/audit/log_pairs.py` for the `(ticket_id, default_owner)` audit-log construction (the call site is `map(make_pair, ticket_ids, repeat(default_owner))`, no `lambda` closure). `boardly` uses `count` in `boardly/reports/paginated_enumeration.py` for the paginated 1-indexed enumeration (the call site is `islice(zip(count(1), items), page_start, page_end)` — the form `enumerate` cannot express). The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to these three patterns and explicitly bans bare `cycle`/`repeat`/`count` without a bound in any `for` loop or `list()` call.

**Why ban bare `cycle` in a `for` loop?** Because the bare form is the most common `itertools` hang. `for x in cycle([1, 2, 3]):` without a `break` runs forever — and unlike `while True:`, the `cycle` call obscures the infinite intent. A reviewer who reads `while True:` sees the infinite loop and asks "where's the break?"; the same reviewer who reads `for x in cycle(...):` may not immediately register that `cycle` is infinite. The style guide makes the bound mandatory so the intent is explicit at every call site.

## Exercises

1. **Exercise 1 — Change the `cycle` bound.** In `cycle_round_robin`, change `len(ticket_ids)` to `10` and re-run. Verify that the rotation wraps correctly and the last three assignments are `bob, carol, alice` (positions 8, 9, 10 in a 1-indexed count). `Verify: uv run python boardly/itertools_infinite_iterators_demo.py`

2. **Exercise 2 — Replace the `map` filler with a list comprehension.** Rewrite `pairs = list(map(lambda tid, owner: (tid, owner), ticket_ids, itertools.repeat(default_owner)))` as `pairs = [(tid, default_owner) for tid in ticket_ids]`. Verify the output is identical. Then articulate the trade-off: the comprehension is shorter and clearer for a constant second arg, but the `map + repeat` form is the composable pattern when the constant comes from an iterator you didn't construct yourself. `Verify: uv run python boardly/itertools_infinite_iterators_demo.py`

3. **Exercise 3 — `count` with a negative step.** Add a demo line that prints `islice(count(100, -7), 5)`. Predict the output before running. Verify it produces `[100, 93, 86, 79, 72]`. `Verify: uv run python boardly/itertools_infinite_iterators_demo.py`

4. **Exercise 4 — `enumerate` vs `zip(count(1), data)` benchmark.** Add a small benchmark that enumerates `range(1_000_000)` with both `enumerate(range(1_000_000), start=1)` and `zip(count(1), range(1_000_000))`, timing each with `time.perf_counter()`. Verify that `enumerate` is faster (it's a C-level builtin). Use this to articulate the rule: `enumerate` for plain enumeration, `zip(count(1), data)` for composable enumeration. `Verify: uv run python boardly/itertools_infinite_iterators_demo.py`

5. **Exercise 5 — The full rotation scheduler.** Extend `cycle_round_robin` to read `engineers` from a `boardly/rotations/on_call.yaml` file (use `yaml.safe_load`) and produce a `dict` mapping each ticket ID to its assigned engineer. The exercise demonstrates the production form: the cycle source comes from config, the bound comes from `len(ticket_ids)`, and the output is a real `dict` the rest of `boardly` can consume. `Verify: uv run python boardly/itertools_infinite_iterators_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_infinite_iterators_demo.py
=== cycle (round-robin assignment) ===
round-robin assignments:
  T-1 -> alice
  T-2 -> bob
  T-3 -> carol
  T-4 -> alice
  T-5 -> bob
  T-6 -> carol
  T-7 -> alice
first 5 with explicit break:
  0: alice
  1: bob
  2: carol
  3: alice
  4: bob

=== repeat (map filler) ===
repeat(2, 3)      = [2, 2, 2]
repeat('x', 0)    = []
islice(repeat(2), 4) = [2, 2, 2, 2]
audit pairs (ticket_id, default_owner):
  (T-1, unassigned)
  (T-2, unassigned)
  (T-3, unassigned)
  (T-4, unassigned)
  (T-5, unassigned)
  (T-6, unassigned)
  (T-7, unassigned)
map(pow, range(5), repeat(2)) = [0, 1, 4, 9, 16]

=== count (1-indexed enumeration) ===
islice(count(10), 5)       = [10, 11, 12, 13, 14]
islice(count(10, -1), 5)   = [10, 9, 8, 7, 6]
islice(count(0, 2), 5)     = [0, 2, 4, 6, 8]
1-indexed projects (zip(count(1), projects)):
  1. Search
  2. Auth
  3. Docs
  4. Export
enumerated projects, rows 2-3 only (islice(zip(count(1), projects), 1, 3)):
  2. Auth
  3. Docs
```

## Previously Learned Here

- [[07-itertools/01-chain-and-islice]] — `chain` and `islice` are the two lazy-iterator primitives this lesson builds on. `islice(cycle(...), n)` is the bound form that makes `cycle`/`repeat`/`count` safe; `islice(zip(count(1), data), start, stop)` is the composability win over `enumerate`.
- [[04-collections/03-deque]] — `deque` is the C-accelerated queue `cycle` uses internally to cache non-sequence iterables; the cross-link matters for the memory-cost discussion.
- [[18-operator/03-functional-composition]] — the `Ticket` dataclass shape and the dispatch-table pattern that pairs with `repeat` for the `map(func, data, repeat(const))` form.
- [[02-functools/03-partial]] — the other "make a callable take fewer args" tool. `repeat` fills a *positional arg of `map`*; `partial` pre-binds an *arg of a function*. The two are complementary, not redundant.

## What's Next

[[07-itertools/06-dropwhile-takewhile-filterfalse]] — the predicate filters. Where this lesson taught the three iterators that *don't stop on their own*, the next lesson teaches the three iterators that *stop based on a predicate*: `dropwhile` (drop the prefix while the predicate is True, then yield the rest without re-checking), `takewhile` (yield while the predicate is True, then STOP — even if later elements would match), and `filterfalse` (the complement of `filter` — yield elements where the predicate is False). The boundary semantics are the gotcha the next lesson is built around.

- `dropwhile(lambda x: x<5, [1,4,6,3,8])` → `[6, 3, 8]` — note `3` is yielded even though `< 5`.
- `takewhile(lambda x: x<5, [1,4,6,3,8])` → `[1, 4]` — stops at `6`, never resumes.
- `filterfalse(even, [1,2,3,4,5])` → `[1, 3, 5]` — the opposite of `filter`.

## Sources

- **`itertools` — Functions creating iterators for efficient looping** — https://docs.python.org/3/library/itertools.html — accessed 2026-10-23 — the canonical reference for `cycle`, `repeat`, `count`, and the rest of the `itertools` family.
- **`itertools.cycle`** — https://docs.python.org/3/library/itertools.html#itertools.cycle — accessed 2026-10-23 — the round-robin iterator; documents the internal save-the-iterable-as-a-tuple behaviour for non-sequence inputs.
- **`itertools.repeat`** — https://docs.python.org/3/library/itertools.html#itertools.repeat — accessed 2026-10-23 — the constant-stream iterator; documents the `times` argument and the `map(func, data, repeat(const))` example that is the canonical use.
- **`itertools.count`** — https://docs.python.org/3/library/itertools.html#itertools.count — accessed 2026-10-23 — the arithmetic-sequence iterator; documents the `start`/`step` arguments and the `zip(count(1), data)` enumeration idiom.
- **`enumerate`** — https://docs.python.org/3/library/functions.html#enumerate — accessed 2026-10-23 — the builtin alternative to `zip(count(1), data)`; the senior-engineer choice for plain enumeration.

## What We Learned

- You can bound an infinite iterator with `islice` — `list(islice(cycle([1,2,3]), 7))` produces `[1, 2, 3, 1, 2, 3, 1]` without hanging.
- You can use `for x in cycle(...)` with an explicit `break` — the only safe way to consume `cycle` in a `for` loop, and the canonical round-robin pattern.
- You can use `repeat` as a `map` filler — `map(func, data, repeat(const))` keeps one positional arg constant without a `lambda` closure or a `partial`.
- You can use `count` for 1-indexed enumeration — `zip(count(1), data)` is composable with `islice` in a way `enumerate(data, start=1)` is not.
- You can state the rule that every `cycle`/`repeat`/`count` call site has a bound — `islice`, `zip` with a finite iterable, or an explicit `break` — and that "I forgot the bound" is the second most common `itertools` production bug.
