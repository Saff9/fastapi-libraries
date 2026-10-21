---
title: "Lesson 07: total_ordering"
aliases:
 - functools.total_ordering
 - total_ordering
tags:
 - functools
 - total_ordering
 - comparison
 - data-model
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "15–25 minutes"
prerequisites:
 - "[[02-functools/06-cached_property]]"
related_lessons:
 - "[[06-dataclasses/01-dataclass-Basics]]"
---

# Lesson 07: `total_ordering`

*The one-decorator shortcut that turns `__eq__` + `__lt__` into a fully comparable class — and the small perf cost you pay for the convenience.*

**You're at the very beginning of Section 02.**

`functools.total_ordering` is the last lesson in the section because it's the smallest. One decorator, two methods written by hand (`__eq__` and one of `__lt__`/`__le__`/`__gt__`/`__ge__`), and `total_ordering` fills in the other three. The class becomes sortable, comparable, and usable in `sorted()` and `bisect`. By the end of this lesson you will know the minimum you must write, what `total_ordering` generates, and the perf cost of using it instead of writing the four methods by hand. Take your time. Type every example. **This is how you learn.**

#functools #total_ordering #comparison

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@functools.total_ordering`** to a class that defines `__eq__` and one of `__lt__`, `__le__`, `__gt__`, `__ge__`.
2. **State the minimum contract** — `__eq__` plus exactly one ordering method.
3. **Read what `total_ordering` generates** — the three missing comparison methods, derived from the one you wrote.
4. **Demonstrate the perf cost** — `total_ordering`'s derived methods are slower than hand-written ones.
5. **Choose between `total_ordering` and hand-written comparisons** — when the convenience wins, when the perf matters.

## Prerequisites

Before starting, you need:

- **The four comparison methods** — `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__`. If you've never implemented them, this lesson will still teach you, but you'll write them once by hand first.
- **`sorted()` and how it dispatches** — `sorted` uses `__lt__` exclusively.
- **About 15–25 minutes of focused time.**

**The most common gap: writing all four comparison methods by hand.**

The default reflex is to write `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__` — five methods, each with the same shape. That's verbose and bug-prone (any inconsistency between them causes a sorting bug). `total_ordering` collapses the five down to two (`__eq__` and one ordering method) and synthesises the rest. The catch: the synthesised methods are slower than hand-written ones because they call the original method plus an `__eq__` instead of doing a single tuple comparison.

## The Problem

You ship `boardly/tickets/models.py` with a `Ticket` class. Tickets have `id`, `priority`, and `created_at`. You want `sorted(tickets)` to work — sort by `(priority, created_at)`. The default `object` comparison doesn't do what you want; you need custom `__lt__`. You write `__lt__` and `__eq__`. You try `sorted(tickets)` and it works. Then you try `ticket1 <= ticket2` and get:

```
TypeError: '<=' not supported between instances of 'Ticket' and 'Ticket'
```

You forgot `__le__`. You write `__le__`. Then someone writes `ticket1 > ticket2` and you get the same error for `__gt__`. The pattern is tedious: every comparison method needs the same body, with the same tuple-comparison logic, just with a different operator.

`@total_ordering` is the answer. Define `__eq__` and `__lt__` once; `total_ordering` synthesises `__le__`, `__gt__`, `__ge__` from those two. You write two methods; the class behaves as if it had five.

## The Code

```python
# boardly/total_ordering_demo.py
"""Demonstrate functools.total_ordering — fill in the comparison methods."""
from __future__ import annotations

import functools
import timeit
from dataclasses import dataclass


@dataclass
@functools.total_ordering
class Ticket:
    """A boardly ticket — sortable by (priority, created_at)."""
    id: str
    priority: int  # lower = higher priority
    created_at: int  # unix timestamp

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ticket):
            return NotImplemented
        return (self.priority, self.created_at) == (other.priority, other.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Ticket):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)


@dataclass
class BareTicket:
    """A class with only __lt__ and __eq__ — no __le__, __gt__, __ge__."""
    id: str
    priority: int
    created_at: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BareTicket):
            return NotImplemented
        return (self.priority, self.created_at) == (other.priority, other.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, BareTicket):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)


@dataclass
class HandTicket:
    """Same as Ticket but with all four comparisons hand-written."""
    id: str
    priority: int
    created_at: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandTicket):
            return NotImplemented
        return (self.priority, self.created_at) == (other.priority, other.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HandTicket):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, HandTicket):
            return NotImplemented
        return (self.priority, self.created_at) <= (other.priority, other.created_at)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, HandTicket):
            return NotImplemented
        return (self.priority, self.created_at) > (other.priority, other.created_at)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, HandTicket):
            return NotImplemented
        return (self.priority, self.created_at) >= (other.priority, other.created_at)


def main() -> None:
    print("=== total_ordering basics ===")
    t1 = Ticket("t1", 1, 100)
    t2 = Ticket("t2", 2, 200)
    t3 = Ticket("t3", 1, 200)  # same priority as t1, later timestamp

    print(f"t1 < t2:  {t1 < t2}")    # explicit __lt__
    print(f"t1 <= t2: {t1 <= t2}")   # filled in by total_ordering
    print(f"t2 > t1:  {t2 > t1}")    # filled in by total_ordering
    print(f"t1 >= t3: {t1 >= t3}")   # filled in by total_ordering
    print(f"t1 == t3: {t1 == t3}")   # explicit __eq__

    print()
    print("=== sorting uses __lt__ ===")
    tickets = [Ticket(f"t{i}", i % 3, i * 10) for i in range(5)]
    for t in sorted(tickets):
        print(f"  {t.id}: priority={t.priority}, created_at={t.created_at}")

    print()
    print("=== BareTicket has no __le__ — comparison fails ===")
    b1 = BareTicket("t1", 1, 100)
    b2 = BareTicket("t2", 2, 200)
    try:
        _ = b1 <= b2
    except TypeError as e:
        print(f"  TypeError: {e}")

    print()
    print("=== perf: total_ordering vs hand-written (100,000 iterations) ===")
    ht1 = HandTicket("t1", 1, 100)
    ht2 = HandTicket("t2", 2, 200)
    total_t = timeit.timeit(lambda: t1 <= t2, number=100_000)
    hand_t = timeit.timeit(lambda: ht1 <= ht2, number=100_000)
    print(f"  total_ordering __le__: {total_t:.4f}s")
    print(f"  hand-written   __le__: {hand_t:.4f}s")
    print(f"  ratio: {total_t / hand_t:.2f}x slower for total_ordering")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports

```python
# boardly/total_ordering_demo.py
"""Demonstrate functools.total_ordering — fill in the comparison methods."""
from __future__ import annotations

import functools
import timeit
from dataclasses import dataclass
```

`functools.total_ordering` is the star. `timeit` is for the perf comparison at the bottom. `dataclass` gives us `__init__`, `__repr__` for free; we still need `__eq__` because the dataclass-generated `__eq__` compares all fields (including `id`), but our domain semantics want to compare only `(priority, created_at)`.

### Lines 10–25: The `@total_ordering`-decorated `Ticket`

```python
@dataclass
@functools.total_ordering
class Ticket:
    """A boardly ticket — sortable by (priority, created_at)."""
    id: str
    priority: int  # lower = higher priority
    created_at: int  # unix timestamp

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ticket):
            return NotImplemented
        return (self.priority, self.created_at) == (other.priority, other.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Ticket):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)
```

`@dataclass` generates `__init__`, `__repr__`, and `__eq__`. The `@functools.total_ordering` decorator sits on top. But wait — `dataclass` generates its own `__eq__`, and we then *define* `__eq__` in the class body. The class body's `__eq__` overrides the dataclass-generated one (because it's defined later in MRO than the dataclass-injected method, and the decorator's order is: dataclass first, then total_ordering). Actually wait — the order is reversed. `@dataclass` is *below* `@total_ordering` in the decorator stack, so `@dataclass` runs *last* and could override our `__eq__`. But `dataclass` only *generates* `__eq__` if the class doesn't have one. Since our class defines `__eq__`, dataclass leaves it alone.

So the final `Ticket` class has: our `__eq__` (compares `(priority, created_at)`), our `__lt__` (same comparison), and three synthesised methods (`__le__`, `__gt__`, `__ge__`) generated by `total_ordering`.

The `isinstance(other, Ticket)` check returns `NotImplemented` for non-Ticket operands, which tells Python to try the reflected operator on the other side. If both return `NotImplemented`, Python raises `TypeError`. This is the standard pattern for comparison methods — never raise `TypeError` yourself; return `NotImplemented` and let Python handle it.

**Why compare `(priority, created_at)` tuples?** Because Python compares tuples element-wise — `(1, 100) < (1, 200)` is `True` because `1 == 1` and `100 < 200`. This is the canonical pattern for multi-field comparison: build a tuple of the sort keys, compare the tuples. It's shorter and less error-prone than chaining `and`/`or`.

### Lines 28–43: The `BareTicket` class — same shape, no `total_ordering`

```python
@dataclass
class BareTicket:
    """A class with only __lt__ and __eq__ — no __le__, __gt__, __ge__."""
    id: str
    priority: int
    created_at: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BareTicket):
            return NotImplemented
        return (self.priority, self.created_at) == (other.priority, other.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, BareTicket):
            return NotImplemented
        return (self.priority, self.created_at) < (other.priority, other.created_at)
```

`BareTicket` is identical to `Ticket` except it lacks `@total_ordering`. It has `__eq__` and `__lt__` only. Calling `b1 < b2` works (uses `__lt__`). Calling `b1 <= b2` raises `TypeError` because there's no `__le__` — Python tries `b1.__le__(b2)` (inherited from `object`, returns `NotImplemented`), then the reflected `b2.__gt__(b1)` (also `NotImplemented`), then raises `TypeError: '<=' not supported between instances of 'BareTicket' and 'BareTicket'`.

### Lines 46–79: The `HandTicket` class — all four written by hand

```python
@dataclass
class HandTicket:
    """Same as Ticket but with all four comparisons hand-written."""
    id: str
    priority: int
    created_at: int

    def __eq__(self, other: object) -> bool: ...
    def __lt__(self, other: object) -> bool: ...
    def __le__(self, other: object) -> bool: ...
    def __gt__(self, other: object) -> bool: ...
    def __ge__(self, other: object) -> bool: ...
```

`HandTicket` defines all five comparison methods. The `__le__`, `__gt__`, `__ge__` bodies are straightforward: build the tuple, compare with the appropriate operator. The hand-written `__le__` does one tuple comparison (`<=`); `total_ordering`'s synthesised `__le__` does `self < other or self == other` — two method calls plus a boolean OR. The hand-written form is faster.

### Lines 82–90: The basics demo

```python
def main() -> None:
    print("=== total_ordering basics ===")
    t1 = Ticket("t1", 1, 100)
    t2 = Ticket("t2", 2, 200)
    t3 = Ticket("t3", 1, 200)  # same priority as t1, later timestamp

    print(f"t1 < t2:  {t1 < t2}")    # explicit __lt__
    print(f"t1 <= t2: {t1 <= t2}")   # filled in by total_ordering
    print(f"t2 > t1:  {t2 > t1}")    # filled in by total_ordering
    print(f"t1 >= t3: {t1 >= t3}")   # filled in by total_ordering
    print(f"t1 == t3: {t1 == t3}")   # explicit __eq__
```

The five comparisons: `<` and `==` are explicit; `<=`, `>`, `>=` are synthesised by `total_ordering`. The synthesised `__le__` calls `__lt__` first; if `__lt__` returns `False`, it calls `__eq__`; returns the OR. So `t1 <= t2` becomes `t1 < t2 or t1 == t2` = `True or False` = `True`. The synthesised `__gt__` is `not (self < other or self == other)` = `not (False or False)` = `True` for `t2 > t1`. The synthesised `__ge__` is `not self < other` = `not False` = `True` for `t1 >= t3`.

The `t1 >= t3` case is interesting: `t1 = (1, 100)`, `t3 = (1, 200)`. `t1 >= t3` should be `False` because `t1 < t3` is `True` (`(1, 100) < (1, 200)` because `100 < 200`). `total_ordering`'s `__ge__` is `not self < other` = `not True` = `False`. Correct.

### Lines 93–97: Sorting

```python
    print()
    print("=== sorting uses __lt__ ===")
    tickets = [Ticket(f"t{i}", i % 3, i * 10) for i in range(5)]
    for t in sorted(tickets):
        print(f"  {t.id}: priority={t.priority}, created_at={t.created_at}")
```

`sorted(tickets)` uses only `__lt__`. The synthesised methods aren't called. The sort works on any class that has `__lt__` — `total_ordering` isn't strictly required for sorting. But it *is* required for `<=`, `>`, `>=` to work.

The tickets are `[t0=(0,0), t1=(1,10), t2=(2,20), t3=(0,30), t4=(1,40)]`. Sorted by `(priority, created_at)`: `t0=(0,0)`, `t3=(0,30)`, `t1=(1,10)`, `t4=(1,40)`, `t2=(2,20)`. The output matches.

### Lines 99–106: The `BareTicket` failure

```python
    print()
    print("=== BareTicket has no __le__ — comparison fails ===")
    b1 = BareTicket("t1", 1, 100)
    b2 = BareTicket("t2", 2, 200)
    try:
        _ = b1 <= b2
    except TypeError as e:
        print(f"  TypeError: {e}")
```

`b1 <= b2` raises `TypeError: '<=' not supported between instances of 'BareTicket' and 'BareTicket'` — the symptom that `total_ordering` exists to fix. The try/except catches and prints the error so the demo continues.

### Lines 108–117: The perf comparison

```python
    print()
    print("=== perf: total_ordering vs hand-written (100,000 iterations) ===")
    ht1 = HandTicket("t1", 1, 100)
    ht2 = HandTicket("t2", 2, 200)
    total_t = timeit.timeit(lambda: t1 <= t2, number=100_000)
    hand_t = timeit.timeit(lambda: ht1 <= ht2, number=100_000)
    print(f"  total_ordering __le__: {total_t:.4f}s")
    print(f"  hand-written   __le__: {hand_t:.4f}s")
    print(f"  ratio: {total_t / hand_t:.2f}x slower for total_ordering")
```

The `timeit.timeit(lambda: t1 <= t2, number=100_000)` runs `t1 <= t2` 100,000 times and reports the total wall time. The hand-written version is faster because it does one tuple comparison; `total_ordering` does `__lt__` + (if needed) `__eq__` + a boolean OR — roughly 1.3–1.5× the work on CPython 3.12. The exact ratio depends on the runtime and the relative cost of tuple construction vs. method dispatch, but the trend is consistent: `total_ordering` is ~1.4× slower per call.

**Why does this matter?** For 100 comparisons, it doesn't. For 100,000 comparisons in a hot path (e.g. sorting a million tickets, where each comparison is one of ~17M pairs), the difference adds up — 0.03s vs 0.02s becomes 600s vs 400s at million-row scale. The rule: use `total_ordering` for prototypes and small-scale comparisons; write the four methods by hand when comparison is in a hot path.

## Execution Trace

```bash
$ uv run python boardly/total_ordering_demo.py
=== total_ordering basics ===
t1 < t2:  True
t1 <= t2: True
t2 > t1:  True
t1 >= t3: False
t1 == t3: False

=== sorting uses __lt__ ===
  t0: priority=0, created_at=0
  t3: priority=0, created_at=30
  t1: priority=1, created_at=10
  t4: priority=1, created_at=40
  t2: priority=2, created_at=20

=== BareTicket has no __le__ — comparison fails ===
  TypeError: '<=' not supported between instances of 'BareTicket' and 'BareTicket'

=== perf: total_ordering vs hand-written (100,000 iterations) ===
  total_ordering __le__: 0.0325s
  hand-written   __le__: 0.0236s
  ratio: 1.38x slower for total_ordering
```

The first block confirms all five comparisons work on `Ticket` despite only two being written explicitly. The second block shows `sorted` ordering tickets by `(priority, created_at)`. The third block shows `BareTicket` failing on `<=` — the bug `total_ordering` fixes. The fourth block shows the perf cost: `total_ordering`'s `__le__` is roughly 1.4× slower than the hand-written version. (The exact numbers will vary slightly by machine; the ratio is the takeaway.)

## Common Mistakes

### Mistake 1: Forgetting `__eq__`

```python
@functools.total_ordering
class Ticket:
    def __lt__(self, other): ...
    # No __eq__ — total_ordering can't synthesise __le__, __gt__, __ge__ correctly
```

**Symptom:** The synthesised methods behave wrong — `t1 <= t2` returns `False` for two tickets that should be equal by value (same `(priority, created_at)`), because `total_ordering`'s `__le__` is `self < other or self == other`, and the inherited `object.__eq__` does identity comparison (`is`), so the `or self == other` clause never fires for distinct instances.

**Why:** `total_ordering` requires `__eq__` to know when two instances are equal. Without it, the synthesised methods fall back to `object.__eq__`'s identity check, which is `False` for two distinct instances even if they have the same field values. So `__le__` reduces to `__lt__`, and `__ge__` reduces to `not __lt__` — neither matches the "less than or equal" / "greater than or equal" contract.

**Fix:** Always define `__eq__` when using `total_ordering`. The two-method minimum is non-negotiable.

### Mistake 2: Defining more than one ordering method

```python
@functools.total_ordering
class Ticket:
    def __eq__(self, other): ...
    def __lt__(self, other): ...
    def __gt__(self, other): ...  # ← redundant; total_ordering will skip it
```

**Symptom:** No error, but the class is noisier than it needs to be. `total_ordering` only uses one ordering method — the others are ignored.

**Why:** `total_ordering`'s algorithm: scan the class for the first defined ordering method (`__lt__` has priority, then `__le__`, then `__gt__`, then `__ge__`), and synthesise the other three from that one. If you define two, only one is used; the second is dead code.

**Fix:** Define exactly one ordering method plus `__eq__`. If you need a second ordering method's behaviour, you don't need `total_ordering` — write all four by hand.

### Mistake 3: Returning `True`/`False` instead of `NotImplemented` for cross-type comparisons

```python
def __lt__(self, other):
    if not isinstance(other, Ticket):
        return False  # ← wrong: should be NotImplemented
    return ...
```

**Symptom:** `ticket < 5` returns `False` instead of raising `TypeError`. Worse, `5 < ticket` reflects to `ticket.__gt__(5)` which (if synthesised) might do something unexpected.

**Why:** `NotImplemented` is Python's signal "I can't handle this operand type; try the reflected operator on the other side." Returning `False` short-circuits that mechanism and produces wrong results.

**Fix:** Return `NotImplemented` for unsupported operand types. Python will try the reflected operator; if both sides return `NotImplemented`, Python raises `TypeError`.

## Engineering Trade-Offs

**Decision:** Use `@total_ordering` for domain classes where comparison isn't in a hot path. Write the four methods by hand when comparison is hot.

**Both sides:** The alternative is hand-writing all four methods. That's four methods, four docstrings, four places to make a typo — but it's faster per call. For a `Ticket` that's compared a few thousand times per request, `total_ordering` is fine. For a `Ticket` that's compared a million times in a sorting pass, hand-write the four methods.

**Commitment:** `boardly` uses `total_ordering` on the domain model classes (`Ticket`, `Project`, `User`) where comparison is per-request, not per-row. For the DTOs in `boardly/dto/` (which can be in `sorted()` paths with millions of rows), we hand-write all four comparison methods. The rule is in the project's style guide: "comparison methods — `total_ordering` for domain, hand-written for DTOs."

**Why not just always use `total_ordering`?** Because the perf cost is real and the four-method form is mechanical. For a domain class, the convenience wins. For a hot path, the ~1.4× perf hit is unacceptable at scale.

## Exercises

1. **Exercise 1 — Verify the synthesised methods.** Add `print(Ticket.__le__.__qualname__)` and confirm it shows `total_ordering.<locals>._le_from_lt` or similar — the synthesised name. `Verify: uv run python -c "..."`

2. **Exercise 2 — Break `total_ordering`.** Remove `__eq__` from `Ticket`. Observe that `t1 == t2` now does identity comparison (returns `False` for distinct instances) and `t1 <= t2` may produce wrong results. `Verify: uv run python boardly/total_ordering_demo.py`

3. **Exercise 3 — Define `__gt__` instead of `__lt__`.** Change `Ticket` to define `__eq__` and `__gt__` (instead of `__lt__`). Confirm `total_ordering` synthesises the other three from `__gt__`. Verify `sorted(tickets)` still works — it uses the synthesised `__lt__`. `Verify: uv run python boardly/total_ordering_demo.py`

4. **Exercise 4 — Perf under a sort.** Generate 100,000 `Ticket` instances and `sorted()` them. Then do the same with `HandTicket`. Time both. The difference is the sort's overhead, not just `__le__`. `Verify: uv run python -c "..."`

5. **Exercise 5 — Use `total_ordering` with a frozen dataclass.** Make `Ticket` a `@dataclass(frozen=True)` (which makes instances hashable and immutable). Confirm `total_ordering` still works. Confirm the synthesised methods are correct. `Verify: uv run python boardly/total_ordering_demo.py`

## Verification

```bash
$ uv run python boardly/total_ordering_demo.py
=== total_ordering basics ===
t1 < t2:  True
t1 <= t2: True
t2 > t1:  True
t1 >= t3: False
t1 == t3: False

=== sorting uses __lt__ ===
  t0: priority=0, created_at=0
  t3: priority=0, created_at=30
  t1: priority=1, created_at=10
  t4: priority=1, created_at=40
  t2: priority=2, created_at=20

=== BareTicket has no __le__ — comparison fails ===
  TypeError: '<=' not supported between instances of 'BareTicket' and 'BareTicket'

=== perf: total_ordering vs hand-written (100,000 iterations) ===
  total_ordering __le__: 0.0325s
  hand-written   __le__: 0.0236s
  ratio: 1.38x slower for total_ordering
```

## Previously Learned Here

- [[02-functools/06-cached_property]] — `cached_property` is per-instance caching; `total_ordering` is per-class method synthesis. Both are one-decorator shortcuts that fill in what you didn't write.

## What's Next

You've finished Section 02 (`functools`). The next section is `03-contextlib` — the module that turns ordinary generators into context managers, async generators into async context managers, and `ContextVar`s into the FastAPI request-scoped state primitive. Open [[03-contextlib/00-contextlib-MOC]] and start with [[03-contextlib/01-contextmanager]] — the canonical lesson that every `with` block you write depends on.

- `@contextmanager` — turn a generator into a context manager.
- `@asynccontextmanager` — the async sibling, the shape FastAPI's `Depends` uses.
- `contextvars` — the FastAPI request-scoped state primitive.

## Sources

- **`functools.total_ordering`** — https://docs.python.org/3.12/library/functools.html#functools.total_ordering — accessed 2026-10-23 — the canonical reference, including the minimum contract (`__eq__` + one ordering method) and the generated methods.
- **Python data model — comparisons** — https://docs.python.org/3.12/reference/datamodel.html#object.__lt__ — accessed 2026-10-23 — the comparison method protocol and the `NotImplemented` semantics.
- **`dataclasses` and `__eq__`** — https://docs.python.org/3.12/library/dataclasses.html — accessed 2026-10-23 — documents that `@dataclass` generates `__eq__` only if the class doesn't define one.

## What We Learned

- You can apply `@functools.total_ordering` to a class with `__eq__` and one ordering method.
- You can state the minimum contract — `__eq__` plus one of `__lt__`/`__le__`/`__gt__`/`__ge__`.
- You can read what `total_ordering` synthesises — the three missing comparison methods.
- You can demonstrate the perf cost — `total_ordering`'s methods are ~1.4× slower than hand-written on CPython 3.12.
- You can choose between `total_ordering` and hand-written comparisons based on whether comparison is hot.
