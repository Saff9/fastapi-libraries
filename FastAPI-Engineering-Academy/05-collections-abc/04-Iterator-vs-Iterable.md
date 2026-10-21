---
title: "Lesson 04: Iterator vs Iterable"
aliases:
 - collections.abc.Iterator
 - collections.abc.Iterable
 - iter builtin
 - StopIteration
tags:
 - collections-abc
 - iterator
 - iterable
 - stop-iteration
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[05-collections-abc/03-Hashable-and-Frozen]]"
related_lessons:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[05-collections-abc/05-Custom-ABCs]]"
---

# Lesson 04: Iterator vs Iterable

*`Iterable.__iter__` vs `Iterator.__next__`. The `iter()` builtin, the StopIteration protocol, why `for x in obj` calls `iter(obj)` first, and the "iterator is exhausted" gotcha that bites every developer the first time they try to loop a generator twice.*

**You're at the very beginning of Section 05 — Lesson 04.**

The `Iterable` → `Iterator` → `Generator` subtree from Lesson 01 is the protocol behind every `for` loop in Python. This lesson walks the protocol from the inside — what `for x in obj:` actually does, what `iter()` is for, and the gotcha that has bitten every Python developer at least once.

Take your time. Type every example. **This is how you learn.**

#collections-abc #iterator #iterable

## Learning Objectives

By the end of this lesson you will be able to:

1. **Explain the `__iter__` / `__next__` / `StopIteration` protocol** in three sentences.
2. **Implement a custom `Iterator`** with `__next__` and `__iter__` returning `self`.
3. **Implement a custom `Iterable`** whose `__iter__` returns a fresh `Iterator` each call.
4. **Spot the "iterator is exhausted" bug** in code before it bites.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/03-Hashable-and-Frozen]]** — comfort with the ABC contract pattern.
- **About 30 minutes of focused time.**

**The most common gap: not realising a generator can be iterated once.**

A generator expression `(x for x in [1, 2, 3])` is an `Iterator`. Iterators are *single-use*: once `__next__` raises `StopIteration`, the iterator is exhausted — every subsequent `__next__` also raises, and every `for` loop iterates zero items. Students who treat the generator as a list (`for x in gen: ...; for x in gen: ...`) get a surprise: the second loop does nothing. Read this lesson with "iterators are single-use" front of mind.

## The Problem

Here is the bug. `boardly` has a generator that yields filtered tickets:

```python
def open_tickets(tickets):
    return (t for t in tickets if t.status == "open")
```

Someone calls it and tries to iterate twice:

```python
gen = open_tickets(all_tickets)
print("count of open:", sum(1 for _ in gen))
print("titles of open:", [t.title for t in gen])
```

The first `sum` consumes the generator. The second list comprehension iterates *zero items* — the generator is exhausted. The output is `count of open: N` and `titles of open: []`. The bug is that `gen` is an `Iterator`, not a `Sequence`. Iterators are single-use.

The fix is one of three:

1. **Materialise** the generator into a list: `gen = list(open_tickets(...))`. Now it is a `Sequence`; iteration is repeatable. Cost: memory.
2. **Call `open_tickets` twice** — get a fresh generator each time. Cost: the source is iterated twice.
3. **Make `open_tickets` a `Sequence`-returning function** — return a list comprehension `[t for t in tickets if ...]` instead of a generator expression. Cost: memory, but the contract is now "I am iterable multiple times".

Which fix is right depends on the use case — but the bug is the same in all three: the student did not realise a generator is single-use.

## The Code

```python
# boardly/iteration.py
"""The Iterable/Iterator protocol: __iter__, __next__, StopIteration, and the
'exhausted iterator' gotcha."""
from collections.abc import Iterable, Iterator
from typing import Any
from boardly.models import Ticket


class TicketBatch(Iterable[Ticket]):
    """A custom Iterable: returns a fresh Iterator each time __iter__ is called.

    Iterable requires __iter__. The contract: __iter__ MUST return a fresh
    Iterator each call. Reusing the same Iterator across calls is the
    'exhausted after first loop' bug.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __iter__(self) -> Iterator[Ticket]:
        # Each call to __iter__ must return a fresh Iterator.
        return iter(self._tickets)


class ReverseTicketIterator(Iterator[Ticket]):
    """A custom Iterator: walks the tickets in reverse.

    Iterator requires __next__ AND __iter__ (which returns self).
    The contract: __next__ either returns the next value or raises
    StopIteration. Once StopIteration has been raised, every subsequent
    __next__ MUST also raise StopIteration (the 'exhausted' state).
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets
        self._index = len(tickets)   # start past the end; decrement before yield

    def __iter__(self) -> Iterator[Ticket]:
        # Iterator's __iter__ returns self — that is what makes an Iterator
        # iterable (and what makes the 'for x in iterator' loop work).
        return self

    def __next__(self) -> Ticket:
        if self._index <= 0:
            # The exhausted state: raise StopIteration forever.
            raise StopIteration
        self._index -= 1
        return self._tickets[self._index]


class Range10:
    """A minimal Iterable demonstrating the protocol in 15 lines."""

    def __iter__(self):
        # A generator function: calling it returns a fresh generator.
        for i in range(10):
            yield i


if __name__ == "__main__":
    from uuid import uuid4

    print("--- iter() builtin: for x in obj -> iter(obj) -> next() loop ---")
    r = Range10()
    total = 0
    for x in r:                # for calls iter(r) -> generator; then next() until StopIteration
        total += x
    print(f"sum of 0..9: {total}")
    # for x in r: print(x)    # Range10's __iter__ returns a fresh generator — repeatable

    print("\n--- TicketBatch: Iterable that returns a fresh iterator each call ---")
    ts = [Ticket(uuid4(), uuid4(), f"t{i}", None, "open", i) for i in range(3)]
    batch = TicketBatch(ts)
    print(f"first iteration: {[t.title for t in batch]}")
    print(f"second iteration: {[t.title for t in batch]}   (works: fresh iterator)")

    print("\n--- ReverseTicketIterator: a custom Iterator ---")
    rti = ReverseTicketIterator(ts)
    print(f"isinstance(rti, Iterator): {isinstance(rti, Iterator)}")
    print(f"isinstance(rti, Iterable): {isinstance(rti, Iterable)}")
    print(f"first loop: {[t.title for t in rti]}")
    print(f"second loop: {[t.title for t in rti]}   (BUG: zero items — iterator exhausted)")

    print("\n--- the iter() + next() protocol, inlined ---")
    gen = (i for i in range(3))
    it = iter(gen)        # iter() returns the iterator (gen already is one)
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration (iterator exhausted)")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration again (once exhausted, always exhausted)")
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports

```python
# boardly/iteration.py
"""The Iterable/Iterator protocol: __iter__, __next__, StopIteration, and the
'exhausted iterator' gotcha."""
from collections.abc import Iterable, Iterator
from typing import Any
from boardly.models import Ticket
```

`from collections.abc import Iterable, Iterator` — both ABCs. `Iterable` is the *protocol* — anything with `__iter__` that returns an `Iterator`. `Iterator` is the *producer* — anything with `__next__` that returns values until `StopIteration`.

### Lines 10–21: `TicketBatch` — the `Iterable` contract

```python
class TicketBatch(Iterable[Ticket]):
    """A custom Iterable: returns a fresh Iterator each time __iter__ is called.

    Iterable requires __iter__. The contract: __iter__ MUST return a fresh
    Iterator each call. Reusing the same Iterator across calls is the
    'exhausted after first loop' bug.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __iter__(self) -> Iterator[Ticket]:
        # Each call to __iter__ must return a fresh Iterator.
        return iter(self._tickets)
```

`class TicketBatch(Iterable[Ticket]):` — inherit from `Iterable`. The ABC's one abstract method is `__iter__`. Implement it.

`return iter(self._tickets)` — `iter()` is the builtin that returns an iterator over an iterable. For a `list`, `iter(self._tickets)` returns a `list_iterator` — a fresh one each call. Each `for` loop on `batch` calls `__iter__` once, gets a fresh `list_iterator`, and iterates that. The result: `batch` is repeatable.

**Why must `__iter__` return a *fresh* iterator?** Because the contract of `Iterable` is "I can be iterated, possibly multiple times". If `__iter__` returned the same iterator every call, the second call would return an already-exhausted iterator, and the second `for` loop would yield zero items. That is the bug — and it is why `Iterable.__iter__` returning `self` is a sign that the class is actually an `Iterator`, not an `Iterable`.

### Lines 25–47: `ReverseTicketIterator` — the `Iterator` contract

```python
class ReverseTicketIterator(Iterator[Ticket]):
    """A custom Iterator: walks the tickets in reverse.

    Iterator requires __next__ AND __iter__ (which returns self).
    The contract: __next__ either returns the next value or raises
    StopIteration. Once StopIteration has been raised, every subsequent
    __next__ MUST also raise StopIteration (the 'exhausted' state).
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets
        self._index = len(tickets)   # start past the end; decrement before yield

    def __iter__(self) -> Iterator[Ticket]:
        # Iterator's __iter__ returns self — that is what makes an Iterator
        # iterable (and what makes the 'for x in iterator' loop work).
        return self

    def __next__(self) -> Ticket:
        if self._index <= 0:
            # The exhausted state: raise StopIteration forever.
            raise StopIteration
        self._index -= 1
        return self._tickets[self._index]
```

`class ReverseTicketIterator(Iterator[Ticket]):` — inherit from `Iterator`. The ABC's two abstract methods are `__next__` and `__iter__`. (Why does `Iterator` require `__iter__`? Because an `Iterator` is also an `Iterable` — `Iterator` extends `Iterable`. The `__iter__` on an `Iterator` returns `self`, signalling "I am my own iterator".)

`def __iter__(self) -> Iterator[Ticket]: return self` — the canonical `Iterator.__iter__` body. Returns `self`. This is what makes `for x in rti` work — `for` calls `iter(rti)`, which returns `rti` itself, then calls `next(rti)` until `StopIteration`.

`def __next__(self):` — the producer. Either returns the next `Ticket` or raises `StopIteration`. Once `StopIteration` has been raised, every subsequent `__next__` must also raise — the iterator is exhausted.

The `if self._index <= 0: raise StopIteration` line is the *exhaustion check*. We use `<=` (rather than `==`) because we want to be robust against a manual `next()` call that hits the boundary twice.

### Lines 50–56: `Range10` — the generator-function shortcut

```python
class Range10:
    """A minimal Iterable demonstrating the protocol in 15 lines."""

    def __iter__(self):
        # A generator function: calling it returns a fresh generator.
        for i in range(10):
            yield i
```

`def __iter__(self): for i in range(10): yield i` — a *generator function*. The `yield` keyword turns the function into a generator: calling `__iter__` does not execute the body; it returns a fresh generator object that, when iterated, runs the body, yielding each `i`. Each call to `__iter__` returns a fresh generator.

**Why is this the standard pattern?** Because the manual `Iterator` subclass (the `ReverseTicketIterator` above) is verbose. Generator functions give you the same protocol in a fraction of the code. Every time you write `yield` instead of `return`, you are using the Iterator protocol via the generator shortcut.

### Lines 60–66: The smoke test for `Range10`

```python
    print("--- iter() builtin: for x in obj -> iter(obj) -> next() loop ---")
    r = Range10()
    total = 0
    for x in r:                # for calls iter(r) -> generator; then next() until StopIteration
        total += x
    print(f"sum of 0..9: {total}")
```

The `for x in r` loop expands to roughly:

```python
_iter = iter(r)         # calls r.__iter__() -> generator
while True:
    try:
        x = next(_iter)  # calls _iter.__next__()
    except StopIteration:
        break
    total += x
```

That is the entire protocol. `for x in obj` is sugar for `iter(obj)` + `next()` loop + `StopIteration` handling.

### Lines 68–72: `TicketBatch` is repeatable

```python
    print("\n--- TicketBatch: Iterable that returns a fresh iterator each call ---")
    ts = [Ticket(uuid4(), uuid4(), f"t{i}", None, "open", i) for i in range(3)]
    batch = TicketBatch(ts)
    print(f"first iteration: {[t.title for t in batch]}")
    print(f"second iteration: {[t.title for t in batch]}   (works: fresh iterator)")
```

The two list comprehensions both iterate `batch`. The first calls `__iter__` once, gets a fresh iterator, and yields all three. The second calls `__iter__` again, gets *another* fresh iterator, and yields all three again. That is the contract of `Iterable`.

### Lines 74–78: `ReverseTicketIterator` is single-use

```python
    print("\n--- ReverseTicketIterator: a custom Iterator ---")
    rti = ReverseTicketIterator(ts)
    print(f"isinstance(rti, Iterator): {isinstance(rti, Iterator)}")
    print(f"isinstance(rti, Iterable): {isinstance(rti, Iterable)}")
    print(f"first loop: {[t.title for t in rti]}")
    print(f"second loop: {[t.title for t in rti]}   (BUG: zero items — iterator exhausted)")
```

`isinstance(rti, Iterator)` is `True`; `isinstance(rti, Iterable)` is also `True` (because `Iterator` extends `Iterable`). The first `for` loop iterates all three. The second `for` loop iterates zero — the iterator was exhausted after the first loop.

This is the bug. The fix is to make `rti` an `Iterable` (not an `Iterator`) by giving it an `__iter__` that returns a fresh `ReverseTicketIterator`:

```python
class ReverseTicketIterable:
    def __init__(self, tickets): self._tickets = tickets
    def __iter__(self): return ReverseTicketIterator(self._tickets)
```

Now each `for` loop calls `__iter__` which constructs a fresh `ReverseTicketIterator`. The first iteration does not exhaust the second.

### Lines 80–90: `iter()` + `next()` inlined

```python
    print("\n--- the iter() + next() protocol, inlined ---")
    gen = (i for i in range(3))
    it = iter(gen)        # iter() returns the iterator (gen already is one)
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration (iterator exhausted)")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration again (once exhausted, always exhausted)")
```

`gen = (i for i in range(3))` — a generator expression. `gen` is already an `Iterator` (it is its own iterator). `iter(gen)` returns `gen` itself (because `Iterator.__iter__` returns `self`).

The three `next(it)` calls yield `0`, `1`, `2`. The fourth `next(it)` raises `StopIteration`. The fifth `next(it)` raises `StopIteration` *again* — the exhaustion is permanent.

## Execution Trace

```bash
$ uv run python boardly/iteration.py
--- iter() builtin: for x in obj -> iter(obj) -> next() loop ---
sum of 0..9: 45

--- TicketBatch: Iterable that returns a fresh iterator each call ---
first iteration: ['t0', 't1', 't2']
second iteration: ['t0', 't1', 't2']   (works: fresh iterator)

--- ReverseTicketIterator: a custom Iterator ---
isinstance(rti, Iterator): True
isinstance(rti, Iterable): True
first loop: ['t2', 't1', 't0']
second loop: []   (BUG: zero items — iterator exhausted)

--- the iter() + next() protocol, inlined ---
next(it): 0
next(it): 1
next(it): 2
next(it): StopIteration (iterator exhausted)
next(it): StopIteration again (once exhausted, always exhausted)
```

## Common Mistakes

### Mistake 1: Treating a generator as a list

```python
gen = (x for x in [1, 2, 3])
print(sum(gen))   # 6
print(sum(gen))   # student expects 6
```

**Symptom:** The second `sum(gen)` returns `0` — the generator was exhausted by the first call.

**Why:** A generator is an `Iterator`. `Iterator` is single-use; the second `sum` iterates zero items.

**Fix:** Materialise the generator into a list: `gen = list(x for x in [1, 2, 3])`. Now `gen` is a `Sequence`; iteration is repeatable.

### Mistake 2: Implementing `__iter__` to return `self` on an `Iterable`

```python
class BadIterable:
    def __init__(self): self._index = 0
    def __iter__(self): return self
    def __next__(self):
        self._index += 1
        if self._index > 3: raise StopIteration
        return self._index
```

**Symptom:** The class is an `Iterator`, not an `Iterable`. The second `for` loop yields zero items.

**Why:** `__iter__` returning `self` is the `Iterator` contract — it makes the class single-use. The class is mis-named `BadIterable` but it is actually an `Iterator`.

**Fix:** Either rename the class to `BadIterator` (and accept that it is single-use) or change `__iter__` to return a *fresh* iterator: `def __iter__(self): return BadIterator(...)` where `BadIterator` is the inner class with `__next__`.

### Mistake 3: Forgetting `__next__` should raise `StopIteration` (not return a sentinel)

```python
class BadIter:
    def __next__(self):
        return self._next_value_or_None_if_done()
```

**Symptom:** The `for` loop never terminates (or terminates after a `None` is yielded, depending on the caller).

**Why:** The protocol requires raising `StopIteration` to signal "no more items". Returning `None` is not the same — `None` is a valid item, not a sentinel.

**Fix:** Use `raise StopIteration` when there are no more items. Use a generator function (`yield`) which handles this automatically — the generator's `return` raises `StopIteration`.

## Engineering Trade-Offs

**Decision:** Use generator functions (`yield`) for 99% of custom iterables. Use `Iterator` subclasses only when you need stateful iteration that does not fit the generator model.

**Both sides:**

Generator functions win on:

1. Conciseness — three lines for an iterator vs 15.
2. `StopIteration` handling — the language does it for you.
3. Composability — `yield from` lets you delegate to sub-generators.

`Iterator` subclasses win on:

1. Stateful iteration where you need methods like `reset()` or `peek()`.
2. Performance-critical loops where the generator's per-yield overhead matters (rare).
3. Implementing custom `__next__` that does not fit the generator model (e.g., reading from a socket where the protocol is message-by-message).

**Commitment:** `boardly/iteration.py` uses `yield` for `Range10` (the canonical Iterable pattern) and a full `Iterator` subclass for `ReverseTicketIterator` (the demonstration of the protocol). In production, `boardly` uses generator functions everywhere — the `Iterator` subclass is for teaching. The rule: "If you can write it with `yield`, write it with `yield`."

## Exercises

1. **Exercise 1 — Verify the iterator-exhaustion bug.** Construct a generator expression `(i for i in range(3))`, iterate it once via `sum`, then again. Confirm the second returns `0`. `Verify: uv run python -c "g=(i for i in range(3)); print(sum(g), sum(g))"`
2. **Exercise 2 — `iter()` returns the iterator.** Confirm `iter([1,2,3])` is a `list_iterator` and `iter(it) is it` (the same object). `Verify: uv run python -c "it=iter([1,2,3]); print(type(it).__name__, iter(it) is it)"`
3. **Exercise 3 — `for` calls `iter()` once.** Build a class with `__iter__` that prints, and confirm `for x in obj: pass` calls `__iter__` exactly once. `Verify: uv run python -c "class C:\n  def __iter__(self):\n    print('iter called'); return iter([1,2,3])\nfor x in C(): pass"`
4. **Exercise 4 — A repeatable `ReverseIterable`.** Build a class whose `__iter__` returns a fresh reverse iterator each call. Confirm two `for` loops both yield. `Verify: uv run python -c "class RevIter:\n  def __init__(self, items): self._items=list(items); self._i=len(items)\n  def __iter__(self): return self\n  def __next__(self):\n    if self._i <= 0: raise StopIteration\n    self._i -= 1; return self._items[self._i]\nclass Rev:\n  def __init__(self, items): self._items=items\n  def __iter__(self): return RevIter(self._items)\nr=Rev([1,2,3]); print(list(r), list(r))"`
5. **Exercise 5 — A `take(n, iterable)` generator.** Write a generator function that yields the first `n` items from any iterable, then stops. `Verify: uv run python -c "def take(n, it):\n  for i, x in enumerate(it):\n    if i >= n: return\n    yield x\nprint(list(take(3, range(10))))"`

## Verification

```bash
$ uv run python boardly/iteration.py
--- iter() builtin: for x in obj -> iter(obj) -> next() loop ---
sum of 0..9: 45

--- TicketBatch: Iterable that returns a fresh iterator each call ---
first iteration: ['t0', 't1', 't2']
second iteration: ['t0', 't1', 't2']   (works: fresh iterator)

--- ReverseTicketIterator: a custom Iterator ---
isinstance(rti, Iterator): True
isinstance(rti, Iterable): True
first loop: ['t2', 't1', 't0']
second loop: []   (BUG: zero items — iterator exhausted)

--- the iter() + next() protocol, inlined ---
next(it): 0
next(it): 1
next(it): 2
next(it): StopIteration (iterator exhausted)
next(it): StopIteration again (once exhausted, always exhausted)
```

## Previously Learned Here

- [[05-collections-abc/03-Hashable-and-Frozen]] — the contract pattern; this lesson is another contract (single-use iteration).
- [[05-collections-abc/01-The-ABC-Hierarchy]] — `Iterable` and `Iterator` were two of the five root ABCs.

## What's Next

[[05-collections-abc/05-Custom-ABCs]] — defining your own ABC. `ABCMeta` as the metaclass, `@abstractmethod` for the contract, `register()` for virtual subclasses (the way `collections.abc.Iterable` "claims" any class with `__iter__`), and the `__subclasshook__` pattern that powers the structural `isinstance` checks. This is the lesson that explains how the entire `collections.abc` module is built.

## Sources

- **Python `collections.abc.Iterator` and `Iterable` documentation** — https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator — accessed 2026-10-23 — the two ABCs and their abstract methods.
- **Python data model: `__iter__` and `__next__`** — https://docs.python.org/3/reference/datamodel.html#object.__iter__ — accessed 2026-10-23 — the language-level protocol.
- **PEP 234 — Iterators** — https://peps.python.org/pep-0234/ — accessed 2026-10-23 — the original iterator protocol PEP; the design rationale for `__iter__` / `__next__` / `StopIteration`.
- **The `iter()` builtin documentation** — https://docs.python.org/3/library/functions.html#iter — accessed 2026-10-23 — the two forms of `iter()` (one-arg and two-arg sentinel).

## What We Learned

- `Iterable.__iter__` returns a fresh `Iterator` each call; `Iterator.__next__` returns values until `StopIteration`.
- `Iterator.__iter__` returns `self` — that is what makes `for x in iterator` work.
- `for x in obj` expands to `iter(obj)` + `next()` loop + `StopIteration` handling.
- An `Iterator` is single-use: once `StopIteration` has been raised, every subsequent `__next__` must also raise.
- A generator function (`yield`) is the standard pattern for custom iterables — `StopIteration` handling is automatic.
- The "iterator is exhausted" bug is what bites everyone the first time they loop a generator twice.
