---
title: "Lesson 03: starmap & accumulate"
aliases:
 - itertools.starmap
 - itertools.accumulate
tags:
 - itertools
 - starmap
 - accumulate
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[07-itertools/02-groupby]]"
 - "[[18-operator/03-functional-composition]]"
 - "[[17-decimal/01-Decimal-Basics]]"
related_lessons:
 - "[[07-itertools/02-groupby]]"
 - "[[07-itertools/04-product-combinations-permutations]]"
 - "[[18-operator/03-functional-composition]]"
 - "[[02-functools/05-reduce]]"
---

# Lesson 03: `starmap` & `accumulate`

*The two `itertools` primitives that turn a stream of tuples into a stream of results — `starmap(func, iterable)` unpacks each tuple into positional args (`func(*t)` instead of `func(t)`), and `accumulate(iterable, func)` is the streaming fold that `functools.reduce` would be if it yielded every intermediate value.*

**You're at the very beginning of Section 07, Lesson 03.**

`itertools.starmap` and `itertools.accumulate` are the two primitives you reach for the moment a boardly pipeline stops being "map one function over one stream" and starts being "thread a function across a stream, yielding every intermediate value". `starmap` answers "I have a list of `(hours, rate)` pairs and I want `hours * rate` for each" — `map(lambda pair: pair[0] * pair[1], pairs)` works but you have to unpack the tuple by hand, and `starmap(lambda h, r: h * r, pairs)` does the unpacking for you. `accumulate` answers "I want a running total" — `sum(numbers)` gives you the final total, but `accumulate(numbers)` yields every prefix sum lazily, which is what a board view needs to draw a cumulative-burn-down chart. By the end of this lesson you will know the difference between `map` and `starmap`, the three forms of `accumulate`, and the `initial=` keyword that changes the output length. Take your time. Type every example. **This is how you learn.**

#itertools #starmap #accumulate

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.starmap(func, iterable)`** to call `func(*t)` for each tuple `t` in the iterable — and articulate the difference from `map(func, iterable)` which calls `func(t)`.
2. **Apply `itertools.accumulate(iterable, func=operator.add)`** to yield the running aggregate — running sum by default, running max via `max`, running product via `operator.mul`.
3. **Apply the `initial=` keyword (Python 3.8+)** to prepend a starting value to the accumulate output — and articulate why it changes the output length from N to N+1.
4. **Compute a running factorial** via `accumulate(range(1, n+1), operator.mul)` and the equivalent with `initial=1`.
5. **Compose `starmap` and `accumulate`** into a single pipeline that computes per-ticket revenue and the running total — without materialising the intermediate list.

## Prerequisites

Before starting, you need:

- **`operator.add` and `operator.mul`** — the named-callable forms of `+` and `*` that `accumulate` consumes as its `func` argument. See [[18-operator/03-functional-composition]].
- **`functools.reduce`** — the non-streaming fold; `accumulate` is its streaming cousin. See [[02-functools/05-reduce]].
- **`Decimal` basics** — `Decimal("120.00")` for money, never `Decimal(120.00)`. See [[17-decimal/01-Decimal-Basics]].
- **About 20–30 minutes of focused time.**

**The most common gap: reaching for `sum` when you need every intermediate value.**

Students who haven't seen `accumulate` reach for `sum(numbers)` to compute a running total. `sum` is great for the final total — `sum([1, 2, 3]) == 6`. But a board view that draws a cumulative-burn-down chart needs `[1, 3, 6]` — every prefix sum, in order. The hand-rolled version is `running = []; total = 0; for n in numbers: total += n; running.append(total)` — five lines for what `list(accumulate(numbers))` does in one. The mental shift is to know that `accumulate` exists and yields every intermediate value of the fold. Once you internalise it, the running-total pattern stops being boilerplate.

## The Problem

You ship `boardly/api/revenue.py` — an endpoint that returns per-ticket revenue and the running project total. The first version reads naturally:

```python
def revenue_v1(tickets: list[Ticket]) -> dict:
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = [h * r for h, r in pairs]            # ← unpack by hand
    running = []
    total = Decimal("0")
    for rev in revenues:
        total += rev
        running.append(total)                        # ← five lines for "running total"
    return {
        "per_ticket": [{"title": t.title, "revenue": rev} for t, rev in zip(tickets, revenues)],
        "running_total": running,
    }
```

Three problems. First, the list comprehension `[h * r for h, r in pairs]` unpacks each tuple into `h` and `r` by hand — the comprehension works, but it hides the intent ("apply a function to each pair"). Second, the `running` boilerplate is five lines for what `accumulate(revenues, operator.add, initial=Decimal("0"))` does in one — and the boilerplate is exactly where bugs sneak in (off-by-one on the initial value, wrong starting total, mutation of `total` across calls). Third, the code materialises `revenues` into a list before walking it for the running total — the streaming property is lost.

`itertools.starmap` and `itertools.accumulate` solve all three. `starmap(lambda h, r: h * r, pairs)` applies the function to each pair without manual unpacking. `accumulate(revenues, operator.add, initial=Decimal("0"))` yields the running total lazily, with the initial value in the output. Compose them — `accumulate(starmap(...), operator.add, initial=Decimal("0"))` — and the entire pipeline is one lazy stream, no intermediate list. Memory cost goes from O(N) to O(1).

## The Code

```python
# boardly/itertools_starmap_accumulate_demo.py
"""Demonstrate itertools.starmap and itertools.accumulate on boardly streams."""
from __future__ import annotations

import itertools
import operator
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    hours: int        # logged hours
    rate: Decimal     # billing rate per hour (USD)


# A small fixture — (hours, rate) pairs to compute revenue per ticket
tickets = [
    Ticket(uuid4(), "Login fails on Safari", 5, Decimal("120.00")),
    Ticket(uuid4(), "OAuth callback loops", 3, Decimal("150.00")),
    Ticket(uuid4(), "Docs typo in /login", 1, Decimal("90.00")),
    Ticket(uuid4(), "Search index slow", 8, Decimal("200.00")),
]


def starmap_unpacks_tuples() -> None:
    """starmap(func, iterable) calls func(*t) for each tuple t."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    print("starmap(lambda h, r: h * r, [(hours, rate), ...]):")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")
    print("vs. map() which would pass the tuple as one positional arg:")
    # map(lambda pair: pair[0] * pair[1], pairs)  — works but unpacks by hand
    revenues_map = map(lambda pair: pair[0] * pair[1], pairs)
    print("  map version:", [str(r) for r in revenues_map])


def starmap_with_named_callable() -> None:
    """Pair starmap with a named function for cleaner call sites."""
    def revenue(hours: int, rate: Decimal) -> Decimal:
        return hours * rate

    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = list(itertools.starmap(revenue, pairs))
    print("starmap(revenue, pairs) — named function, no lambda:")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")


def accumulate_running_sum() -> None:
    """accumulate(iterable, func=operator.add) — the running aggregate."""
    hours_stream = [t.hours for t in tickets]
    running = list(itertools.accumulate(hours_stream))
    print("accumulate(hours_stream) — default operator.add (running sum):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: {r} hours total")


def accumulate_running_max() -> None:
    """accumulate(iterable, func=max) — the running maximum."""
    hours_stream = [t.hours for t in tickets]
    running_max = list(itertools.accumulate(hours_stream, max))
    print("accumulate(hours_stream, max) — running maximum hours so far:")
    for t, r in zip(tickets, running_max):
        print(f"  after {t.title:30s}: max so far = {r}")


def accumulate_factorial() -> None:
    """accumulate(range(1, n+1), operator.mul) — the lazy factorial."""
    n = 5
    factorials = list(itertools.accumulate(range(1, n + 1), operator.mul))
    print(f"accumulate(range(1, {n+1}), operator.mul) — first {n} factorials:")
    print(f"  {factorials}  # 1!, 2!, 3!, 4!, 5!")


def accumulate_initial_keyword() -> None:
    """accumulate(..., initial=X) — 3.8+ — prepends X to the output."""
    # Without initial: output has N items, one per input item
    no_initial = list(itertools.accumulate([1, 2, 3], operator.add))
    print(f"accumulate([1,2,3], add)             -> {no_initial}  (3 items)")

    # With initial=10: output has N+1 items, the first being initial
    with_initial = list(itertools.accumulate([1, 2, 3], operator.add, initial=10))
    print(f"accumulate([1,2,3], add, initial=10) -> {with_initial}  (4 items)")

    # Factorial with initial=1 — the convention from mathematics
    factorials = list(itertools.accumulate(range(1, 6), operator.mul, initial=1))
    print(f"accumulate(range(1,6), mul, initial=1) -> {factorials}  (6 items, leading 1)")


def running_revenue() -> None:
    """A realistic boardly pipeline: per-ticket revenue -> running total."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    running = itertools.accumulate(revenues, operator.add, initial=Decimal("0"))
    print("starmap -> accumulate pipeline (running revenue, initial=0):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: ${r} total")
    # Note: zip stops at the shortest input, so the leading 0 is paired
    # with the first ticket. Print the raw list to see all 5 items.
    raw = list(itertools.accumulate(
        itertools.starmap(lambda h, r: h * r, pairs),
        operator.add,
        initial=Decimal("0"),
    ))
    print(f"  raw running list (length 5): {raw}")


def main() -> None:
    print("=== starmap: unpacks tuples into positional args ===")
    starmap_unpacks_tuples()
    print()
    print("=== starmap with a named callable ===")
    starmap_with_named_callable()
    print()
    print("=== accumulate: running sum (default) ===")
    accumulate_running_sum()
    print()
    print("=== accumulate: running max ===")
    accumulate_running_max()
    print()
    print("=== accumulate: factorial ===")
    accumulate_factorial()
    print()
    print("=== accumulate: the initial= keyword (3.8+) ===")
    accumulate_initial_keyword()
    print()
    print("=== boardly pipeline: starmap -> accumulate ===")
    running_revenue()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/itertools_starmap_accumulate_demo.py
"""Demonstrate itertools.starmap and itertools.accumulate on boardly streams."""
from __future__ import annotations

import itertools
import operator
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4
```

`itertools` is the star. `operator` provides `operator.add` and `operator.mul` — the named-callable forms of `+` and `*` that `accumulate` consumes (see [[18-operator/03-functional-composition]]). `Decimal` is the money type — never `float` for billing, see [[17-decimal/01-Decimal-Basics]]. `dataclass` and `UUID`/`uuid4` keep the demo offline. `from __future__ import annotations` is boardly house style.

### Lines 12–17: The `Ticket` model

```python
@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    hours: int        # logged hours
    rate: Decimal     # billing rate per hour (USD)
```

A frozen dataclass with two financial fields: `hours: int` and `rate: Decimal`. The `rate` is `Decimal` not `float` because money must not be a binary float — `Decimal("120.00") * 5 == Decimal("600.00")` is exact, `120.00 * 5 == 600.0` is approximate (see [[17-decimal/01-Decimal-Basics]]). The lesson computes `hours * rate` per ticket — `int * Decimal == Decimal`, so the multiplication is exact.

### Lines 20–26: The fixture

```python
# A small fixture — (hours, rate) pairs to compute revenue per ticket
tickets = [
    Ticket(uuid4(), "Login fails on Safari", 5, Decimal("120.00")),
    Ticket(uuid4(), "OAuth callback loops", 3, Decimal("150.00")),
    Ticket(uuid4(), "Docs typo in /login", 1, Decimal("90.00")),
    Ticket(uuid4(), "Search index slow", 8, Decimal("200.00")),
]
```

Four tickets with `(hours, rate)` pairs: 5×120 = $600, 3×150 = $450, 1×90 = $90, 8×200 = $1600. Total = $2740. The fixture is at module scope so every helper sees the same data. The rates are deliberately heterogeneous ($90 to $200) to make the `accumulate(max)` demonstration visible.

### Lines 29–40: `starmap` unpacks tuples into positional args

```python
def starmap_unpacks_tuples() -> None:
    """starmap(func, iterable) calls func(*t) for each tuple t."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    print("starmap(lambda h, r: h * r, [(hours, rate), ...]):")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")
    print("vs. map() which would pass the tuple as one positional arg:")
    # map(lambda pair: pair[0] * pair[1], pairs)  — works but unpacks by hand
    revenues_map = map(lambda pair: pair[0] * pair[1], pairs)
    print("  map version:", [str(r) for r in revenues_map])
```

`itertools.starmap(func, iterable)` calls `func(*t)` for each tuple `t` in the iterable. Internally — see `Modules/itertoolsmodule.c` — `starmap.__next__` pulls a tuple from the underlying iterator, calls `PyObject_CallFunctionObjArgs(func, t[0], t[1], ..., NULL)` (which is the C-level equivalent of `func(*t)`), and yields the result. The crucial difference from `map` is the unpacking: `map(func, [(1, 2), (3, 4)])` calls `func((1, 2))` — one positional argument, the tuple. `starmap(func, [(1, 2), (3, 4)])` calls `func(1, 2)` — two positional arguments, the unpacked tuple.

The demo prints both versions side by side. The `starmap` version uses `lambda h, r: h * r` — two parameters, matching the unpacked tuple. The `map` version uses `lambda pair: pair[0] * pair[1]` — one parameter (the tuple), with manual `[0]` and `[1]` indexing inside the body. The `starmap` version is the senior choice because the lambda's signature *documents* the shape of the input: two values, named `h` and `r`. The `map` version's signature says "I take a pair" and the body says how to crack it open — less documentation, more puzzle.

**Why is it called `starmap`?** Because the star in `f(*args)` is the unpacking operator in Python syntax. `starmap(f, [(1, 2), (3, 4)])` is read as "star-map f over the iterable" — i.e. apply the star-unpacking to each item before calling f. The name predates the formalisation of `*args` syntax in PEP 3132 (Python 3.0), but the meaning is the same: `f(*t)` per tuple.

**Why not just use a list comprehension `[h * r for h, r in pairs]`?** You absolutely can — and for one-off transformations the comprehension is the senior choice (see [[18-operator/03-functional-composition]] for the equivalent argument against `reduce`). The comprehension wins when (a) the transform is one line, (b) you don't need to reuse the function, and (c) the input is concrete. `starmap` wins when (a) the transform is a named function you want to reuse, (b) the input is a generator or cursor that you want to stream, or (c) the transform composes into a larger pipeline (the `starmap -> accumulate` pattern below). The lesson uses both — the comprehension in the fixture build, `starmap` in the pipeline composition.

### Lines 43–53: `starmap` with a named callable

```python
def starmap_with_named_callable() -> None:
    """Pair starmap with a named function for cleaner call sites."""
    def revenue(hours: int, rate: Decimal) -> Decimal:
        return hours * rate

    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = list(itertools.starmap(revenue, pairs))
    print("starmap(revenue, pairs) — named function, no lambda:")
    for t, rev in zip(tickets, revenues):
        print(f"  {t.title:30s} -> ${rev}")
```

The same call as before, but with a named function `revenue(hours, rate)` instead of a lambda. The call site `starmap(revenue, pairs)` reads as English: "star-map the revenue function over pairs." The function's signature `revenue(hours: int, rate: Decimal) -> Decimal` documents the input shape — two args, `int` and `Decimal`, returning `Decimal`. The lambda version `lambda h, r: h * r` documents nothing about types (lambdas cannot have annotations in 3.12, 3.13, or 3.14 — there is no accepted PEP that lifts this restriction; `lambda h: int: h` is a `SyntaxError`). For a one-off transform, the lambda is fine; for a reusable transform, the named function is the senior choice.

**Why doesn't `starmap` just accept `*args`-shape functions natively?** Because `starmap` cannot know how many positional args your function takes without inspecting it. The `*t` unpacking is the universal contract: if your function takes two args, you pass two-element tuples; if it takes three, three-element tuples. Mismatch — say, a three-element tuple and a two-arg function — raises `TypeError: <lambda>() takes 2 positional arguments but 3 were given` at the first call. There is no auto-truncation or auto-padding. This is the contract `starmap` enforces.

### Lines 56–63: `accumulate` — running sum (default)

```python
def accumulate_running_sum() -> None:
    """accumulate(iterable, func=operator.add) — the running aggregate."""
    hours_stream = [t.hours for t in tickets]
    running = list(itertools.accumulate(hours_stream))
    print("accumulate(hours_stream) — default operator.add (running sum):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: {r} hours total")
```

`itertools.accumulate(iterable, func=operator.add)` is the running aggregate. Internally — see `Modules/itertoolsmodule.c` — `accumulate.__next__` maintains an internal "current" value (initially `iterable[0]`), pulls the next item, calls `func(current, next)` to compute the new current, yields the new current. The output has the same length as the input — every intermediate value is emitted.

The default `func=operator.add` makes `accumulate` the running sum: `accumulate([5, 3, 1, 8])` yields `5, 8, 9, 17`. The demo pairs each ticket title with the running total, printing "5 hours total", "8 hours total", "9 hours total", "17 hours total" — the burn-down chart shape. Without `accumulate`, you would write `running = []; total = 0; for h in hours: total += h; running.append(total)` — five lines for what `list(accumulate(hours))` does in one.

**Why does the default `func` default to `operator.add` and not `None`?** Because the running sum is the overwhelmingly most common use case — running totals in dashboards, cumulative counts in metrics, burn-down charts. Defaulting to `operator.add` lets the caller write `accumulate(stream)` for the common case and `accumulate(stream, func)` for the uncommon case. The 3.8 changelog (bpo-3567) added this default — before 3.8, you had to write `accumulate(stream, operator.add)` explicitly. The default removed a line of import boilerplate.

### Lines 66–73: `accumulate` — running max

```python
def accumulate_running_max() -> None:
    """accumulate(iterable, func=max) — the running maximum."""
    hours_stream = [t.hours for t in tickets]
    running_max = list(itertools.accumulate(hours_stream, max))
    print("accumulate(hours_stream, max) — running maximum hours so far:")
    for t, r in zip(tickets, running_max):
        print(f"  after {t.title:30s}: max so far = {r}")
```

`accumulate(stream, max)` is the running maximum. The `max` builtin is a two-argument function when called as `max(a, b)` — it returns the larger of the two. `accumulate` calls `max(current, next)` at each step: `max(5, 3) == 5`, `max(5, 1) == 5`, `max(5, 8) == 8`. The output is `5, 5, 5, 8` — the maximum-seen-so-far at each step. The demo prints "max so far = 5", "max so far = 5", "max so far = 5", "max so far = 8". Any two-argument function works as `func`: `min` for the running minimum, `operator.mul` for the running product, a custom lambda for the running concatenation.

**Why does `accumulate` accept any two-arg function instead of only `+`?** Because the generalisation is free — `accumulate(stream, func)` is `reduce(func, stream[:i+1])` for every i, and `reduce` accepts any two-arg function. Specialising on `+` would have made the running-sum use case one character shorter and every other use case (running product, running max, running min, running concat) impossible. The generalisation is the senior-engineer move: one primitive, many use cases, no need for separate `running_max`/`running_min`/`running_product` functions.

### Lines 76–82: `accumulate` — factorial

```python
def accumulate_factorial() -> None:
    """accumulate(range(1, n+1), operator.mul) — the lazy factorial."""
    n = 5
    factorials = list(itertools.accumulate(range(1, n + 1), operator.mul))
    print(f"accumulate(range(1, {n+1}), operator.mul) — first {n} factorials:")
    print(f"  {factorials}  # 1!, 2!, 3!, 4!, 5!")
```

`accumulate(range(1, 6), operator.mul)` yields `1, 2, 6, 24, 120` — the first five factorials. The trick: `range(1, 6)` is `1, 2, 3, 4, 5`; `accumulate` with `operator.mul` does `1, 1*2=2, 2*3=6, 6*4=24, 24*5=120`. The first output `1` is both `1!` and the seed of the multiplication — the algorithm starts from the first input value, so `1` from `range(1, 6)` is the seed.

This is the canonical "lazy factorial" pattern. `math.factorial(5)` gives you `120` (one value); `list(accumulate(range(1, 6), operator.mul))` gives you `[1, 2, 6, 24, 120]` (every intermediate factorial). If you want the first 100 factorials without recomputing from scratch, `accumulate` is the answer — each factorial is one multiplication away from the previous, not 99 multiplications from scratch.

**Why `range(1, n+1)` and not `range(n+1)`?** Because `range(0, n+1)` starts with 0, and `0 * anything == 0` — the running product would be `0, 0, 0, 0, 0` because the seed is 0. The first element of the input is the seed (without `initial=`), so the seed must be 1 (the multiplicative identity) for the factorial pattern. Starting at `range(1, n+1)` is the idiomatic fix. The next block shows the alternative: `initial=1` lets you start at `range(1, n+1)` *with* a leading 1, which is the convention from mathematics.

### Lines 85–96: The `initial=` keyword (Python 3.8+)

```python
def accumulate_initial_keyword() -> None:
    """accumulate(..., initial=X) — 3.8+ — prepends X to the output."""
    # Without initial: output has N items, one per input item
    no_initial = list(itertools.accumulate([1, 2, 3], operator.add))
    print(f"accumulate([1,2,3], add)             -> {no_initial}  (3 items)")

    # With initial=10: output has N+1 items, the first being initial
    with_initial = list(itertools.accumulate([1, 2, 3], operator.add, initial=10))
    print(f"accumulate([1,2,3], add, initial=10) -> {with_initial}  (4 items)")

    # Factorial with initial=1 — the convention from mathematics
    factorials = list(itertools.accumulate(range(1, 6), operator.mul, initial=1))
    print(f"accumulate(range(1,6), mul, initial=1) -> {factorials}  (6 items, leading 1)")
```

The `initial=` keyword (Python 3.8+, bpo-3567) prepends a starting value to the accumulate output. Without `initial`, `accumulate([1, 2, 3], operator.add)` yields `1, 3, 6` (three items — one per input). With `initial=10`, the same call yields `10, 11, 13, 16` (four items — `initial` is the first, then `initial + 1 = 11`, then `11 + 2 = 13`, then `13 + 3 = 16`). The output length changes from N to N+1.

**Why does `initial=` change the output length?** Because `initial` is emitted as the first value of the output, before any input item is consumed. Internally, `accumulate.__next__` with `initial` set yields `initial` on the first call, then sets `current = initial` and proceeds as normal: `current = func(current, next)`, yield `current`. Without `initial`, the first call yields `iterable[0]` (no `func` call) and sets `current = iterable[0]`. The `initial` form is `func(initial, iterable[0]), func(that, iterable[1]), ...` — every output value is the result of a `func` call. The non-initial form is `iterable[0], func(iterable[0], iterable[1]), ...` — the first output is a passthrough.

The factorial-with-initial pattern `accumulate(range(1, 6), operator.mul, initial=1)` yields `1, 1, 2, 6, 24, 120` — six items. The first `1` is `initial`; the second `1` is `initial * 1 = 1`; then `1 * 2 = 2`, `2 * 3 = 6`, `6 * 4 = 24`, `24 * 5 = 120`. The leading `1` is the convention from mathematics — `0! == 1` by definition, and the factorial sequence is `1, 1, 2, 6, 24, 120, ...` with two leading ones. Without `initial`, `accumulate(range(1, 6), operator.mul)` yields `1, 2, 6, 24, 120` — five items, missing the leading `0!`.

**Why was `initial=` added in 3.8 and not earlier?** Because before 3.8, callers who wanted a leading seed had to use `itertools.chain([initial], accumulate(iterable, func))` — three function calls and a list literal. The `initial=` keyword collapsed this to one argument. The 3.8 changelog framed it as "make the empty-iterable case useful" — `list(accumulate([]))` is `[]` without `initial` (nothing to seed), but `list(accumulate([], initial=10))` is `[10]` (the seed alone). The `initial=` form is the one that always yields at least one item, which makes it the safer choice for downstream code that assumes a non-empty result.

### Lines 99–112: The `starmap` → `accumulate` pipeline

```python
def running_revenue() -> None:
    """A realistic boardly pipeline: per-ticket revenue -> running total."""
    pairs = [(t.hours, t.rate) for t in tickets]
    revenues = itertools.starmap(lambda h, r: h * r, pairs)
    running = itertools.accumulate(revenues, operator.add, initial=Decimal("0"))
    print("starmap -> accumulate pipeline (running revenue, initial=0):")
    for t, r in zip(tickets, running):
        print(f"  after {t.title:30s}: ${r} total")
    # Note: zip stops at the shortest input, so the leading 0 is paired
    # with the first ticket. Print the raw list to see all 5 items.
    raw = list(itertools.accumulate(
        itertools.starmap(lambda h, r: h * r, pairs),
        operator.add,
        initial=Decimal("0"),
    ))
    print(f"  raw running list (length 5): {raw}")
```

The realistic boardly pipeline. `pairs = [(t.hours, t.rate) for t in tickets]` builds a list of two-element tuples. `starmap(lambda h, r: h * r, pairs)` yields the per-ticket revenue — `Decimal("600.00"), Decimal("450.00"), Decimal("90.00"), Decimal("1600.00")` — without materialising them. `accumulate(revenues, operator.add, initial=Decimal("0"))` yields the running revenue — `Decimal("0"), Decimal("600.00"), Decimal("1050.00"), Decimal("1140.00"), Decimal("2740.00")` — five items because of `initial=`. The pipeline is one lazy stream; the only list materialised is the final one in the print call.

The crucial gotcha exposed in the `zip(tickets, running)` loop: `zip` stops at the shortest input. `tickets` has four items; `running` has five (because of `initial=`). `zip` truncates to four pairs, and the pairs are `(tickets[0], running[0]), (tickets[1], running[1]), ...` — i.e. the first ticket is paired with the *initial* value `Decimal("0")`, not with its own revenue. The output reads "after Login fails on Safari: $0 total" — which is wrong if the student expected the running total *after* the first ticket.

**Why does the `zip` truncation expose the off-by-one?** Because `accumulate(..., initial=X)` shifts the output by one position. Without `initial`, `accumulate(revenues)` yields four items aligned with `tickets` — the first item is the first revenue, the second is the sum of the first two revenues, etc. With `initial=0`, `accumulate(revenues, initial=0)` yields five items — the first is `0` (before any revenue), the second is `0 + first_revenue`, etc. To pair the *running total after ticket i* with `tickets[i]`, you need to either drop the first `running` item or shift the `tickets` list. The lesson's `raw` print shows the full five-item list so the student can see the leading 0 and reason about the alignment.

**Why not just use `initial=Decimal("0")` and accept the leading 0?** Because the leading 0 is semantically "the running total before any ticket was processed" — useful for the *pre-state* of the chart (the burn-down starts at zero, not at the first ticket's revenue). The endpoint contract is "running_total[0] == 0 (before any revenue), running_total[i+1] == running_total[i] + revenue[i]" — and `initial=0` is what makes that contract work. The `zip` off-by-one is a presentation issue, not a correctness issue; the raw list is correct.

## Execution Trace

```bash
$ uv run python boardly/itertools_starmap_accumulate_demo.py
=== starmap: unpacks tuples into positional args ===
starmap(lambda h, r: h * r, [(hours, rate), ...]):
  Login fails on Safari          -> $600.00
  OAuth callback loops           -> $450.00
  Docs typo in /login            -> $90.00
  Search index slow              -> $1600.00
vs. map() which would pass the tuple as one positional arg:
  map version: ['600.00', '450.00', '90.00', '1600.00']

=== starmap with a named callable ===
starmap(revenue, pairs) — named function, no lambda:
  Login fails on Safari          -> $600.00
  OAuth callback loops           -> $450.00
  Docs typo in /login            -> $90.00
  Search index slow              -> $1600.00

=== accumulate: running sum (default) ===
accumulate(hours_stream) — default operator.add (running sum):
  after Login fails on Safari         : 5 hours total
  after OAuth callback loops          : 8 hours total
  after Docs typo in /login           : 9 hours total
  after Search index slow             : 17 hours total

=== accumulate: running max ===
accumulate(hours_stream, max) — running maximum hours so far:
  after Login fails on Safari         : max so far = 5
  after OAuth callback loops          : max so far = 5
  after Docs typo in /login           : max so far = 5
  after Search index slow             : max so far = 8

=== accumulate: factorial ===
accumulate(range(1, 6), operator.mul) — first 5 factorials:
  [1, 2, 6, 24, 120]  # 1!, 2!, 3!, 4!, 5!

=== accumulate: the initial= keyword (3.8+) ===
accumulate([1,2,3], add)             -> [1, 3, 6]  (3 items)
accumulate([1,2,3], add, initial=10) -> [10, 11, 13, 16]  (4 items)
accumulate(range(1,6), mul, initial=1) -> [1, 1, 2, 6, 24, 120]  (6 items, leading 1)

=== boardly pipeline: starmap -> accumulate ===
starmap -> accumulate pipeline (running revenue, initial=0):
  after Login fails on Safari         : $0 total
  after OAuth callback loops          : $600.00 total
  after Docs typo in /login           : $1050.00 total
  after Search index slow             : $1140.00 total
  raw running list (length 5): [Decimal('0'), Decimal('600.00'), Decimal('1050.00'), Decimal('1140.00'), Decimal('2740.00')]
```

The first block shows `starmap` calling `lambda h, r: h * r` per pair, producing per-ticket revenue. The `map` version produces the same numbers but via a one-arg lambda that manually unpacks the tuple — same result, less self-documenting.

The second block shows `starmap(revenue, pairs)` with a named function — identical output, but the call site reads as English and the function signature documents the input shape.

The third block shows `accumulate(hours_stream)` with the default `operator.add` — the running sum. Each line prints the running total after the corresponding ticket.

The fourth block shows `accumulate(hours_stream, max)` — the running maximum. The `max so far` value stays at 5 through the first three tickets (none of them exceed 5), then jumps to 8 when the fourth ticket arrives.

The fifth block shows the lazy factorial: `accumulate(range(1, 6), operator.mul)` yields `[1, 2, 6, 24, 120]` — `1!` through `5!` in one call.

The sixth block shows the `initial=` keyword. Without it, `accumulate([1, 2, 3], add)` yields three items `[1, 3, 6]`. With `initial=10`, it yields four items `[10, 11, 13, 16]` — the leading `10` is the initial value. With `initial=1` on the factorial pattern, it yields six items `[1, 1, 2, 6, 24, 120]` — the convention from mathematics.

The seventh block shows the full pipeline. The `zip` loop prints `"$0 total"` after the first ticket because `zip(tickets, running)` truncates to four pairs and the first pair is `(tickets[0], running[0])` where `running[0]` is the initial value `Decimal("0")`. The raw list at the bottom shows the full five-item output: `[0, 600, 1050, 1140, 2740]` — the running total before and after each ticket.

## Common Mistakes

### Mistake 1: Using `map` when you want `starmap`

```python
pairs = [(5, Decimal("120.00")), (3, Decimal("150.00"))]
# Wrong: map passes the tuple as one positional arg
revenues = map(lambda h, r: h * r, pairs)   # TypeError: <lambda>() missing 1 required positional argument: 'r'
```

**Symptom:** `TypeError: <lambda>() missing 1 required positional argument: 'r'` at the first iteration.

**Why:** `map(func, iterable)` calls `func(item)` per item — one positional arg, the whole tuple. A two-arg lambda `lambda h, r: h * r` expects two args, but `map` passes one (the tuple), so Python raises `TypeError` on the missing second arg.

**Fix:** Use `starmap(func, iterable)` which calls `func(*item)` per item — the tuple is unpacked into positional args. Or rewrite the lambda to take one arg: `map(lambda pair: pair[0] * pair[1], pairs)` — works but loses the self-documenting signature.

### Mistake 2: Forgetting that `initial=` changes the output length

```python
# Wrong: zip pairs the leading initial with the first input — off by one
revenues = [10, 20, 30]
running = list(accumulate(revenues, operator.add, initial=0))
# running == [0, 10, 30, 60] — length 4, but revenues has length 3
pairs = list(zip(revenues, running))
# pairs == [(10, 0), (20, 10), (30, 30)] — shifted by one!
```

**Symptom:** The first `(revenue, running_total)` pair has the running total *before* the revenue was added, not after. The chart's first data point is at zero, not at the first revenue.

**Why:** `accumulate(iterable, func, initial=X)` prepends `X` to the output. The output length goes from N to N+1. Zipping the N-length input with the N+1-length output truncates to N pairs, and the alignment is shifted by one — the first input is paired with the leading initial.

**Fix:** Either drop the first item of `running` (`running[1:]`) before zipping, or shift the input (`zip([None] + revenues, running)`). Or use `initial=` only when you actually want the leading-seed semantics — for the simple "running total per item" use case, `accumulate(revenues)` (without `initial`) gives N items aligned with the input.

### Mistake 3: Computing the same factorial list twice

```python
# Wrong — recomputes from scratch each time
def factorial(n: int) -> int:
    return math.factorial(n)

# Right — compute once, materialise, reuse
from itertools import accumulate
import operator
factorials = list(accumulate(range(1, 101), operator.mul, initial=1))
def factorial(i: int) -> int:
    return factorials[i]   # O(1) lookup
```

**Symptom:** A loop calling `factorial(50)` ten thousand times is slow — each call does 50 multiplications from scratch.

**Why:** `math.factorial(n)` recomputes the entire product every time. If you call it in a hot loop, you pay O(n) per call. `accumulate` computes every factorial from 1 to N once, in O(N) total — then each lookup is O(1) via list indexing.

**Fix:** Materialise the factorial list with `accumulate(range(1, N+1), operator.mul, initial=1)` once at module load, then index it. This is the classic dynamic-programming move — trade O(N) space for O(1) lookup.

## Engineering Trade-Offs

**Decision:** Use `starmap` when you have a stream of tuples and a multi-arg function; use `accumulate` when you want the running aggregate of a stream. Reach for `initial=` when you need the leading seed (mathematical convention, "before any input" state, guaranteed non-empty result). Compose `starmap` → `accumulate` when the pipeline is "per-item transform, then running aggregate."

**Both sides:** The alternatives to `starmap` are (a) the list comprehension `[func(*t) for t in iterable]` (wins for one-off transforms on concrete lists — more Pythonic, no import), and (b) a manual `for` loop (wins when the transform has side effects or accumulates state). The alternative to `accumulate` is `functools.reduce` (see [[02-functools/05-reduce]]) — `reduce` yields the final value, `accumulate` yields every intermediate value. `reduce` wins when you want the final total; `accumulate` wins when you want the running total.

**Commitment:** `boardly/api/revenue.py` uses `accumulate(starmap(lambda h, r: h * r, pairs), operator.add, initial=Decimal("0"))` to build the running-revenue stream. The project's lint config flags a manual `running = []; total = 0; for ...` pattern with a `Bench` warning suggesting `list(accumulate(...))` as the rewrite. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule as the project's "don't hand-roll a fold" stance.

**Why not just use a `for` loop?** Because the `for` loop is five lines for what `accumulate` does in one, and the boilerplate is where bugs sneak in — the `total = 0` initialisation, the `total += x` step, the `running.append(total)` order. `accumulate(revenues, initial=Decimal("0"))` encodes all three of those decisions in one call. The `for` loop is appropriate when the body has logic `accumulate` cannot express (filtering, side effects, branching); the `accumulate` call is appropriate when the body is "apply `func` to running and next." Most running-aggregate code is the latter, and `accumulate` is the senior-engineer move.

## Exercises

1. **Exercise 1 — Switch `accumulate` from `add` to `mul`.** Modify `accumulate_running_sum()` to call `accumulate(hours_stream, operator.mul)` and re-run. Verify the output is `[5, 15, 15, 120]` — the running product. `Verify: uv run python boardly/itertools_starmap_accumulate_demo.py`

2. **Exercise 2 — Pair `starmap` with `operator.mul`.** Rewrite `starmap_unpacks_tuples()` to use `starmap(operator.mul, pairs)` instead of a lambda. Verify the output is identical (hint: `operator.mul(a, b) == a * b`). `Verify: uv run python boardly/itertools_starmap_accumulate_demo.py`

3. **Exercise 3 — Compute a running concatenation.** Use `accumulate(words, lambda a, b: a + b)` on `["board", "ly", "rules"]` to build a running string concatenation. Verify the output is `['board', 'boardly', 'boardlyrules']`. Note: this is O(N²) in total work because each `+` copies the running string — fine for small inputs, pathological for large ones. `Verify: uv run python boardly/itertools_starmap_accumulate_demo.py`

4. **Exercise 4 — Implement a running average.** Use `accumulate` to compute the running sum, then `enumerate` (or `zip` with `range(1, N+1)`) to divide each running sum by its position index. Print the running average of `hours_stream`. Verify the output is `[5.0, 4.0, 3.0, 4.25]`. `Verify: uv run python boardly/itertools_starmap_accumulate_demo.py`

5. **Exercise 5 — Build a `burn_down_chart` pipeline.** Compose `starmap` (per-ticket revenue) → `accumulate` (running total) → `map` (subtract from `Decimal("5000.00")` budget) to produce a list of "remaining budget" values. Print the chart. The output should start at $5000 and end at $2260 (5000 − 2740). `Verify: uv run python boardly/itertools_starmap_accumulate_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_starmap_accumulate_demo.py
=== starmap: unpacks tuples into positional args ===
starmap(lambda h, r: h * r, [(hours, rate), ...]):
  Login fails on Safari          -> $600.00
  OAuth callback loops           -> $450.00
  Docs typo in /login            -> $90.00
  Search index slow              -> $1600.00
vs. map() which would pass the tuple as one positional arg:
  map version: ['600.00', '450.00', '90.00', '1600.00']

=== starmap with a named callable ===
starmap(revenue, pairs) — named function, no lambda:
  Login fails on Safari          -> $600.00
  OAuth callback loops           -> $450.00
  Docs typo in /login            -> $90.00
  Search index slow              -> $1600.00

=== accumulate: running sum (default) ===
accumulate(hours_stream) — default operator.add (running sum):
  after Login fails on Safari         : 5 hours total
  after OAuth callback loops          : 8 hours total
  after Docs typo in /login           : 9 hours total
  after Search index slow             : 17 hours total

=== accumulate: running max ===
accumulate(hours_stream, max) — running maximum hours so far:
  after Login fails on Safari         : max so far = 5
  after OAuth callback loops          : max so far = 5
  after Docs typo in /login           : max so far = 5
  after Search index slow             : max so far = 8

=== accumulate: factorial ===
accumulate(range(1, 6), operator.mul) — first 5 factorials:
  [1, 2, 6, 24, 120]  # 1!, 2!, 3!, 4!, 5!

=== accumulate: the initial= keyword (3.8+) ===
accumulate([1,2,3], add)             -> [1, 3, 6]  (3 items)
accumulate([1,2,3], add, initial=10) -> [10, 11, 13, 16]  (4 items)
accumulate(range(1,6), mul, initial=1) -> [1, 1, 2, 6, 24, 120]  (6 items, leading 1)

=== boardly pipeline: starmap -> accumulate ===
starmap -> accumulate pipeline (running revenue, initial=0):
  after Login fails on Safari         : $0 total
  after OAuth callback loops          : $600.00 total
  after Docs typo in /login           : $1050.00 total
  after Search index slow             : $1140.00 total
  raw running list (length 5): [Decimal('0'), Decimal('600.00'), Decimal('1050.00'), Decimal('1140.00'), Decimal('2740.00')]
```

## Previously Learned Here

- [[07-itertools/01-chain-and-islice]] — the one-shot-iterator mental model. `starmap` and `accumulate` both return one-shot iterators; the lesson uses `list(...)` to materialise every example.
- [[07-itertools/02-groupby]] — the precondition-then-iterate pattern. `accumulate` has its own precondition (the `func` must accept two args of compatible types), and the lesson surfaces it via the running-max demo.

## What's Next

[[07-itertools/04-product-combinations-permutations]] — `starmap` and `accumulate` showed you the *unary* and *binary* iterator primitives; the next lesson shows you the *n-ary* combinatorial primitives. `itertools.product(*iterables, repeat=1)` is the Cartesian product, `combinations(iterable, r)` is the no-repetition subsets, and `permutations(iterable, r)` is the all-orderings enumeration. The lesson shows `product("AB", repeat=3)` for password-style enumeration and the combinatorial-explosion warning — `len(list(product("ABCDEF", repeat=6)))` is 46,656 and `len(list(combinations(range(50), 5)))` is over two million.

- `product(*iterables, repeat=1)` — Cartesian product, with `repeat=` for "the same iterable N times."
- `combinations(iterable, r)` — r-length subsets, no repetition, in lexicographic order.
- `permutations(iterable, r=None)` — r-length orderings; default `r=len(iterable)`.

## Sources

- **`itertools.starmap`** — https://docs.python.org/3/library/itertools.html#itertools.starmap — accessed 2026-10-23 — the canonical reference for the tuple-unpacking map, including the one-line "equivalent to `func(*a, *b)`" note that the docs surface.
- **`itertools.accumulate`** — https://docs.python.org/3/library/itertools.html#itertools.accumulate — accessed 2026-10-23 — the canonical reference, including the `func` parameter, the `initial=` keyword (3.8+), and the default `operator.add` behaviour.
- **`operator.add` and `operator.mul`** — https://docs.python.org/3/library/operator.html#operator.add — accessed 2026-10-23 — the named-callable forms of `+` and `*` that `accumulate` consumes as its `func` argument.
- **`functools.reduce`** — https://docs.python.org/3/library/functools.html#functools.reduce — accessed 2026-10-23 — the non-streaming fold cousin; useful for comparing "I want the final value" (reduce) vs "I want every intermediate value" (accumulate).

## What We Learned

- You can apply `itertools.starmap(func, iterable)` to call `func(*t)` for each tuple `t` — and articulate the difference from `map(func, iterable)` which calls `func(t)`.
- You can apply `itertools.accumulate(iterable, func=operator.add)` to yield the running aggregate — running sum by default, running max via `max`, running product via `operator.mul`.
- You can apply the `initial=` keyword (Python 3.8+) to prepend a starting value to the accumulate output — and articulate why it changes the output length from N to N+1.
- You can compute a running factorial via `accumulate(range(1, n+1), operator.mul)` and the equivalent with `initial=1`.
- You can compose `starmap` and `accumulate` into a single pipeline that computes per-ticket revenue and the running total without materialising the intermediate list.
