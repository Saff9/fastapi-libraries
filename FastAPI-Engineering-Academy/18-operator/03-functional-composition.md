---
title: "Lesson 03: Functional composition with operator"
aliases:
 - operator functional composition
 - operator.add
 - operator.mul
 - operator.contains
 - operator.truth
tags:
 - operator
 - functional-programming
 - reduce
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[18-operator/01-itemgetter-attrgetter]]"
 - "[[18-operator/02-methodcaller]]"
 - "[[02-functools/05-reduce]]"
related_lessons:
 - "[[18-operator/01-itemgetter-attrgetter]]"
 - "[[18-operator/02-methodcaller]]"
 - "[[02-functools/05-reduce]]"
 - "[[02-functools/03-partial]]"
---

# Lesson 03: Functional composition with `operator`

*The infix-operator function table — `operator.add(a, b)` is `a + b`, callable as a function, composable with `reduce` — and the opinion that a list comprehension usually beats `reduce(operator.add, ...)`, every single time.*

**You're at the very beginning of Section 18.**

The `operator` module is the standard library's "name every infix" table. `+` becomes `operator.add`, `*` becomes `operator.mul`, `&` becomes `operator.and_`, `in` becomes `operator.contains`. The point is not to replace the syntax — `a + b` is always clearer than `operator.add(a, b)` — but to make the operator *passable as a value*. `reduce(operator.add, nums)` threads `+` across a list; `filter(partial(operator.contains, allowed_set), items)` threads `in` across a stream. By the end of this lesson you will know the three operator tables (arithmetic, bitwise, logical/container), the `reduce(operator.add, ...)` pattern, and the opinion that a list comprehension almost always wins. Take your time. Type every example. **This is how you learn.**

#operator #functional-programming #reduce

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply the arithmetic table** — `operator.add`/`sub`/`mul`/`truediv`/`floordiv`/`mod`/`pow` as binary callables.
2. **Apply the bitwise table** — `operator.and_`/`or_`/`xor`/`invert` (unary `~`) plus `lshift`/`rshift`.
3. **Apply the logical/container callables** — `operator.truth`, `operator.not_`, `operator.contains(a, b)` == `b in a`.
4. **Compose `reduce(operator.add, nums)`** — and articulate why `sum(nums)` is the senior-engineer form.
5. **Articulate the "list comprehension beats `reduce(operator.add, ...)`" opinion** — and the three rare cases where `reduce` still wins.

## Prerequisites

Before starting, you need:

- **`itemgetter`/`attrgetter`/`methodcaller`** — the three factories from the first two lessons of this section.
- **`functools.reduce`** — see [[02-functools/05-reduce]] for the canonical lesson on the left-fold and the "don't use `reduce`" opinion.
- **About 20–30 minutes of focused time.**

**The most common gap: reaching for `reduce(operator.add, nums)` because it looks functional.**

`reduce(operator.add, nums, 0)` is the textbook example of point-free style: it threads `+` across a list of numbers and returns the sum. It is also the canonical "don't write this" example — `sum(nums)` is shorter, faster (C-implemented), and reads in English. The student who internalises `operator` without internalising the reduce opinion ends up writing functional-looking code that's slower and harder to read than the loop form. The fix: learn the operator table, learn the reduce opinion in the same lesson, and reach for `operator` as a *value* (passed to `reduce`, `partial`, `map`) only when there's no built-in.

## The Problem

You ship `boardly/tickets/metrics.py` that computes aggregates over the day's tickets: total priority weight, product of weight multipliers, the union of status flags (as a bitmap), and the count of tickets whose status is in a watch set. The first version reads naturally:

```python
total_priority = sum(t.priority for t in tickets)
weights_product = 1
for w in weights:
    weights_product *= w
status_bitmap = 0
for s in status_flags:
    status_bitmap |= s
watched = [t for t in tickets if t.status in WATCH]
```

This is correct, readable, and the senior-engineer form for *most* of these operations. The case where `operator` becomes useful is when you need to *pass the operation as a value* — `apply_op(op, a, b)` where `op` is `+` or `*` or `&` selected at runtime. Without `operator`, you'd write a dispatch table `{"+": lambda a, b: a + b, "*": lambda a, b: a * b}`; with `operator`, the table is `{"+": operator.add, "*": operator.mul}` — no lambdas, no puzzle.

The case where `reduce(operator.add, nums)` becomes tempting — but loses — is the "fold a list of numbers with `+`" pattern. The temptation: `reduce(operator.add, nums)` looks functional and elegant. The reality: `sum(nums)` is shorter, faster, and standard. This lesson covers both: when `operator` is the right tool (passing `+` as a value), and when `reduce(operator.add, ...)` is the wrong tool (use `sum`).

## The Code

```python
# boardly/operator_composition_demo.py
"""Demonstrate the operator infix-function table and reduce composition."""
from __future__ import annotations

import functools
import operator
from dataclasses import dataclass
from uuid import UUID, uuid4


# --- The boardly Ticket (subset) ---
@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    status: str       # "todo" | "in_progress" | "done" | "blocked"
    priority: int     # 1 (low) .. 5 (urgent)
    weight: float     # multiplier for SLA


# --- Status flags as bit positions (a small enum-shape without enum) ---
STATUS_FLAGS: dict[str, int] = {
    "todo":        0b0001,
    "in_progress": 0b0010,
    "done":        0b0100,
    "blocked":     0b1000,
}
WATCH = {"blocked", "in_progress"}  # statuses that page the on-call


# --- Fixture ---
tickets = [
    Ticket(uuid4(), "Search returns 500", "in_progress", 5, 1.5),
    Ticket(uuid4(), "Auth fails on macOS", "todo", 3, 1.0),
    Ticket(uuid4(), "Docs typo", "done", 1, 0.5),
    Ticket(uuid4(), "Export to CSV", "blocked", 2, 1.0),
]
weights = [t.weight for t in tickets]


def arithmetic_table() -> None:
    """operator.add/sub/mul/truediv/floordiv/mod/pow as binary callables."""
    print("add(2, 3)     =", operator.add(2, 3))
    print("sub(5, 2)     =", operator.sub(5, 2))
    print("mul(2, 3)     =", operator.mul(2, 3))
    print("truediv(7, 2) =", operator.truediv(7, 2))
    print("floordiv(7, 2)=", operator.floordiv(7, 2))
    print("mod(7, 3)     =", operator.mod(7, 3))
    print("pow(2, 3)     =", operator.pow(2, 3))

    # The dispatch-table use case: op as a value
    OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
    print("apply_op('+', 2, 3) =", OPS["+"](2, 3))
    print("apply_op('*', 2, 3) =", OPS["*"](2, 3))


def bitwise_table() -> None:
    """operator.and_/or_/xor/invert/lshift/rshift for status bitmaps."""
    blocked = STATUS_FLAGS["blocked"]   # 0b1000
    in_prog = STATUS_FLAGS["in_progress"]  # 0b0010
    print(f"and_({blocked:b}, {in_prog:b}) = {operator.and_(blocked, in_prog):b} (intersection)")
    print(f"or_({blocked:b}, {in_prog:b})  = {operator.or_(blocked, in_prog):b} (union)")
    print(f"xor({blocked:b}, {in_prog:b})  = {operator.xor(blocked, in_prog):b} (symmetric diff)")
    print(f"invert({blocked:b})       = {operator.invert(blocked):04b} (bitwise NOT)")
    print(f"lshift(0b0001, 3)   = {operator.lshift(0b0001, 3):b}")
    print(f"rshift(0b1000, 2)   = {operator.rshift(0b1000, 2):b}")

    # Union of all status flags across the day's tickets
    flags = [STATUS_FLAGS[t.status] for t in tickets]
    bitmap = functools.reduce(operator.or_, flags, 0)
    print(f"union of all ticket statuses: {bitmap:04b}")
    print(f"is 'done' present? {bool(bitmap & STATUS_FLAGS['done'])}")


def logical_and_container() -> None:
    """operator.truth, operator.not_, operator.contains."""
    print(f"truth([1, 2])  = {operator.truth([1, 2])}   (non-empty list is truthy)")
    print(f"truth([])      = {operator.truth([])}   (empty list is falsy)")
    print(f"not_([1, 2])   = {operator.not_([1, 2])}  (negation of truthy)")
    print(f"not_([])       = {operator.not_([])}  (negation of falsy)")
    print(f"contains([1,2,3], 2) = {operator.contains([1, 2, 3], 2)}  (2 in [1,2,3])")

    # The use case: filter tickets by status-in-WATCH
    watched = [t for t in tickets if operator.contains(WATCH, t.status)]
    print(f"watched tickets: {[t.title for t in watched]}")

    # The partial-application form: contains(WATCH, ...) → a 1-arg predicate
    is_watched = functools.partial(operator.contains, WATCH)
    watched2 = [t for t in tickets if is_watched(t.status)]
    print(f"watched (partial): {[t.title for t in watched2]}")


def reduce_vs_sum_opinion() -> None:
    """The opinion: sum() beats reduce(operator.add, ...), every time."""
    priorities = [t.priority for t in tickets]

    # Wrong-but-tempting: reduce(operator.add, priorities)
    via_reduce = functools.reduce(operator.add, priorities, 0)
    # Right: sum(priorities)
    via_sum = sum(priorities)
    print(f"reduce(add, priorities): {via_reduce}")
    print(f"sum(priorities):         {via_sum}")
    print(f"equal? {via_reduce == via_sum}")

    # The list-comprehension-beats-reduce opinion, made concrete:
    # `sum(t.priority for t in tickets)` is one expression; reduce needs three imports
    # (functools, operator), a function call (reduce), a binary op (operator.add),
    # and an initial value (0). sum() is shorter, faster, and standard.

    # The product case: no built-in, so reduce(operator.mul, ...) is acceptable
    via_reduce_mul = functools.reduce(operator.mul, weights, 1.0)
    # Or math.prod on 3.8+
    import math
    via_math_prod = math.prod(weights)
    print(f"reduce(mul, weights): {via_reduce_mul}")
    print(f"math.prod(weights):   {via_math_prod}")


def list_comp_beats_reduce_opinion() -> None:
    """The opinion: a list comprehension usually beats reduce(operator.add, ...)."""
    # The pattern that tempts students:
    #   reduce(operator.add, [t.title + "\n" for t in tickets])
    # The senior-engineer form:
    titles_block = "".join(t.title + "\n" for t in tickets)
    print("titles joined:")
    print(titles_block)

    # Why join() wins: it's a single C call that knows the buffer size up front;
    # reduce(operator.add, strs) does N intermediate string allocations (quadratic
    # in the worst case). The list-comprehension-feeds-join pattern is the standard.

    # The 3-case rule from functools/05-reduce:
    # 1. Function composition (unknown-length callable chain) — reduce wins.
    # 2. Deep-merge of N dicts — reduce wins when N is dynamic.
    # 3. Chained binary op with no built-in — reduce wins.
    # Anything else: sum(), math.prod(), str.join(), or an explicit loop.


def main() -> None:
    print("=== arithmetic table ===")
    arithmetic_table()
    print()
    print("=== bitwise table ===")
    bitwise_table()
    print()
    print("=== logical & container ===")
    logical_and_container()
    print()
    print("=== reduce vs sum: the opinion ===")
    reduce_vs_sum_opinion()
    print()
    print("=== list comp beats reduce ===")
    list_comp_beats_reduce_opinion()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/operator_composition_demo.py
"""Demonstrate the operator infix-function table and reduce composition."""
from __future__ import annotations

import functools
import operator
from dataclasses import dataclass
from uuid import UUID, uuid4
```

`functools` is here for `reduce` — the lesson cross-links [[02-functools/05-reduce]]. `operator` is the star. `dataclass` and `UUID` build the `Ticket` shape. `math` is imported inside `reduce_vs_sum_opinion` because `math.prod` is the right alternative to `reduce(operator.mul, ...)`. `from __future__ import annotations` is boardly's house style.

### Lines 13–19: The boardly `Ticket` (subset)

```python
@dataclass(frozen=True)
class Ticket:
    id: UUID
    title: str
    status: str       # "todo" | "in_progress" | "done" | "blocked"
    priority: int     # 1 (low) .. 5 (urgent)
    weight: float     # multiplier for SLA
```

A frozen `Ticket` with five fields. The `weight` field is new — it's a multiplier the SLA calculator uses to scale each ticket's priority (`effective_priority = priority * weight`). This lesson uses `weight` to demonstrate `operator.mul` and `math.prod`. The other fields (`status`, `priority`) are the same as lessons 01 and 02.

### Lines 22–35: Status flags and watch set

```python
# --- Status flags as bit positions (a small enum-shape without enum) ---
STATUS_FLAGS: dict[str, int] = {
    "todo":        0b0001,
    "in_progress": 0b0010,
    "done":        0b0100,
    "blocked":     0b1000,
}
WATCH = {"blocked", "in_progress"}  # statuses that page the on-call


# --- Fixture ---
tickets = [
    Ticket(uuid4(), "Search returns 500", "in_progress", 5, 1.5),
    Ticket(uuid4(), "Auth fails on macOS", "todo", 3, 1.0),
    Ticket(uuid4(), "Docs typo", "done", 1, 0.5),
    Ticket(uuid4(), "Export to CSV", "blocked", 2, 1.0),
]
weights = [t.weight for t in tickets]
```

`STATUS_FLAGS` maps each status string to a 4-bit position. This is the "enum without `enum`" pattern — fine for a small fixed set, though production boardly would use `IntFlag` from [[09-enum/03-Flag-and-IntFlag]]. The dict shape lets us look up the bit position by status name; the bitwise operations compose the bits.

`WATCH` is a set of statuses that page the on-call. The set membership test `t.status in WATCH` is the canonical filter — `operator.contains(WATCH, t.status)` is the function-form equivalent. The fixture has four tickets, two of which (in_progress, blocked) are in `WATCH`.

`weights = [t.weight for t in tickets]` pre-extracts the weight list. This is the standard "build the input list once" pattern — the list comprehension is the senior-engineer form for materialising a list from an iterable of objects. The same list comprehension feeds both `reduce(operator.mul, weights)` and `math.prod(weights)` in the next demo.

### Lines 38–51: The arithmetic table

```python
def arithmetic_table() -> None:
    """operator.add/sub/mul/truediv/floordiv/mod/pow as binary callables."""
    print("add(2, 3)     =", operator.add(2, 3))
    print("sub(5, 2)     =", operator.sub(5, 2))
    print("mul(2, 3)     =", operator.mul(2, 3))
    print("truediv(7, 2) =", operator.truediv(7, 2))
    print("floordiv(7, 2)=", operator.floordiv(7, 2))
    print("mod(7, 3)     =", operator.mod(7, 3))
    print("pow(2, 3)     =", operator.pow(2, 3))

    # The dispatch-table use case: op as a value
    OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
    print("apply_op('+', 2, 3) =", OPS["+"](2, 3))
    print("apply_op('*', 2, 3) =", OPS["*"](2, 3))
```

The arithmetic table is `operator.add(a, b)` == `a + b`, `operator.sub(a, b)` == `a - b`, and so on. Each function is a thin C-level wrapper around the corresponding dunder call: `operator.add(a, b)` is essentially `a.__add__(b)`, with the addition of `__radd__` fallback if `a` doesn't know how to add `b` (the same protocol Python uses for `a + b`).

The seven arithmetic functions:
- `add(a, b)` — `a + b`
- `sub(a, b)` — `a - b`
- `mul(a, b)` — `a * b`
- `truediv(a, b)` — `a / b` (always float, the 3.0+ true division)
- `floordiv(a, b)` — `a // b` (floor division)
- `mod(a, b)` — `a % b` (modulo)
- `pow(a, b)` — `a ** b` (exponentiation)

**Note — `truediv` vs `floordiv`.** The naming reflects Python 2/3 history. In Python 2, `/` was floor division for ints (`5 / 2 == 2`); Python 3 split this into `/` (true division, returns float) and `//` (floor division). The `operator` module named them `truediv` and `floordiv` to be explicit. There is no `operator.div` — that name was removed in Python 3 (it referred to the Python 2 `/` behaviour, which no longer exists).

The dispatch-table use case is the real reason the arithmetic table exists. `OPS = {"+": operator.add, ...}` is a dict that maps a *configurable* operator string to the corresponding callable. When a CLI flag or config file specifies "combine these metrics with `+`", you look up `OPS["+"]` and call it. Without `operator`, you'd write `OPS = {"+": lambda a, b: a + b, ...}` — lambdas that have no introspection, no `__name__`, no composability with `partial` and `reduce`. With `operator`, the table is grep-friendly and the callables are first-class.

**Why not just use `eval`?** Because `eval` is the security hole that ended careers. `eval("2 + 3")` works but `eval(user_input)` is arbitrary code execution. The dispatch-table pattern `OPS[user_op](a, b)` is a *whitelist*: only the four operators in `OPS` are reachable. The senior-engineer rule: never `eval` user input; always use a dispatch table that exposes only the operations you intend.

### Lines 54–66: The bitwise table

```python
def bitwise_table() -> None:
    """operator.and_/or_/xor/invert/lshift/rshift for status bitmaps."""
    blocked = STATUS_FLAGS["blocked"]   # 0b1000
    in_prog = STATUS_FLAGS["in_progress"]  # 0b0010
    print(f"and_({blocked:b}, {in_prog:b}) = {operator.and_(blocked, in_prog):b} (intersection)")
    print(f"or_({blocked:b}, {in_prog:b})  = {operator.or_(blocked, in_prog):b} (union)")
    print(f"xor({blocked:b}, {in_prog:b})  = {operator.xor(blocked, in_prog):b} (symmetric diff)")
    print(f"invert({blocked:b})       = {operator.invert(blocked):04b} (bitwise NOT)")
    print(f"lshift(0b0001, 3)   = {operator.lshift(0b0001, 3):b}")
    print(f"rshift(0b1000, 2)   = {operator.rshift(0b1000, 2):b}")

    # Union of all status flags across the day's tickets
    flags = [STATUS_FLAGS[t.status] for t in tickets]
    bitmap = functools.reduce(operator.or_, flags, 0)
    print(f"union of all ticket statuses: {bitmap:04b}")
    print(f"is 'done' present? {bool(bitmap & STATUS_FLAGS['done'])}")
```

The bitwise table mirrors the arithmetic table: `operator.and_(a, b)` == `a & b`, `operator.or_(a, b)` == `a | b`, `operator.xor(a, b)` == `a ^ b`, `operator.invert(a)` == `~a` (unary), `operator.lshift(a, b)` == `a << b`, `operator.rshift(a, b)` == `a >> b`. The trailing underscore (`and_`, `or_`, `not_`) is because `and`, `or`, `not` are Python keywords and cannot be used as attribute names without it.

**Why the trailing underscore?** Because `operator.and` would be a syntax error — `and` is a keyword, so the lexer would reject `operator.and` before the parser ever saw it. The trailing underscore (`and_`, `or_`, `not_`, `is_`) is the standard Python convention for "this name would be a keyword, so we append `_`". You'll see the same pattern in `pip._internal.utils.logging` and other stdlib modules where a name collides with a keyword.

The status-bitmap use case is real: boardly stores a per-day bitmap of which statuses appeared. `reduce(operator.or_, flags, 0)` threads `|` across the list, producing the union — `0b1111` for the fixture, because every status is present: `in_progress` (0b0010), `todo` (0b0001), `done` (0b0100), and `blocked` (0b1000). The output line `union of all ticket statuses: 1111` shows exactly that — all four bits set.

**Why use a bitmap at all?** For O(1) membership tests across a fixed set. `bitmap & STATUS_FLAGS["done"]` returns nonzero if "done" was present, zero otherwise. The bitmap shape lets you compose "what statuses were seen yesterday AND today" with `yesterday_bitmap & today_bitmap` (intersection) in a single instruction. For a fixed small set, the bitmap is faster than a set-of-strings and serialises as a single int. For a large or dynamic set, use a `frozenset` instead.

### Lines 69–84: Logical and container callables

```python
def logical_and_container() -> None:
    """operator.truth, operator.not_, operator.contains."""
    print(f"truth([1, 2])  = {operator.truth([1, 2])}   (non-empty list is truthy)")
    print(f"truth([])      = {operator.truth([])}   (empty list is falsy)")
    print(f"not_([1, 2])   = {operator.not_([1, 2])}  (negation of truthy)")
    print(f"not_([])       = {operator.not_([])}  (negation of falsy)")
    print(f"contains([1,2,3], 2) = {operator.contains([1, 2, 3], 2)}  (2 in [1,2,3])")

    # The use case: filter tickets by status-in-WATCH
    watched = [t for t in tickets if operator.contains(WATCH, t.status)]
    print(f"watched tickets: {[t.title for t in watched]}")

    # The partial-application form: contains(WATCH, ...) → a 1-arg predicate
    is_watched = functools.partial(operator.contains, WATCH)
    watched2 = [t for t in tickets if is_watched(t.status)]
    print(f"watched (partial): {[t.title for t in watched2]}")
```

Four callables here:
- `operator.truth(obj)` — returns `True` if `obj` is truthy, `False` otherwise. Equivalent to `bool(obj)`. The function exists because the `operator` module is "name every operator", and `bool(obj)` is the operator form of `obj`'s truth value.
- `operator.not_(obj)` — returns `not obj`. Unary.
- `operator.contains(a, b)` — returns `b in a`. The operands follow the dunder convention: `a.__contains__(b)` is what's called, so `contains(container, item)` mirrors `__contains__(item)`. This is *not* the same order as the `in` syntax — `"todo" in statuses` reads left-to-right as "is `todo` in `statuses`?", while `operator.contains(statuses, "todo")` reads as "does `statuses` contain `todo`?". The result is identical; the argument order differs because the function form mirrors the dunder, while the syntax form reads naturally.

The use case `[t for t in tickets if operator.contains(WATCH, t.status)]` filters tickets whose status is in `WATCH`. This is the function-form of `t.status in WATCH`. The two forms produce the same result; the syntax form (`t.status in WATCH`) is the senior-engineer choice in a comprehension — the function form (`operator.contains(WATCH, t.status)`) is only worth reaching for when you need the operation as a value.

**Why mention `operator.truth` and `operator.not_` if `bool()` and `not obj` are shorter?** Same reason as the arithmetic table: passing the operation as a value. `map(operator.not_, list_of_bools)` flips each element; `filter(operator.truth, items)` keeps the truthy ones (the same as `filter(None, items)`, but more explicit). These are the rare cases where the function form reads cleaner than the syntax form.

The `partial(operator.contains, WATCH)` form is the genuinely useful composition. `operator.contains` is a 2-argument function; `partial(operator.contains, WATCH)` pre-binds the first argument, producing a 1-argument predicate `is_watched(item)` that returns `item in WATCH`. This is the partial-application pattern from [[02-functools/03-partial]] composed with the `operator` table — the two modules are designed to work together. The result: `is_watched` is a reusable predicate that can be passed to `filter`, used in `sorted(key=...)`, or stored in a registry.

**Note — `operator.in_` does not exist in Python 3.12.** Older documentation and some textbooks reference `operator.in_(a, b)` as the "reverse-argument-order" form of `operator.contains(a, b)`, where `in_(a, b)` would mean `a in b`. In CPython 3.12, that function is not exposed — `dir(operator)` shows `contains` but no `in_`. The only "containment test" callable is `operator.contains(a, b)` == `b in a`. If you see `operator.in_` in older code, the call should be rewritten as `operator.contains(b, a)` (note the swapped operand order). The senior-engineer move: standardise on `operator.contains` and ignore any reference to `in_`.

### Lines 87–104: `reduce` vs `sum` — the opinion

```python
def reduce_vs_sum_opinion() -> None:
    """The opinion: sum() beats reduce(operator.add, ...), every time."""
    priorities = [t.priority for t in tickets]

    # Wrong-but-tempting: reduce(operator.add, priorities)
    via_reduce = functools.reduce(operator.add, priorities, 0)
    # Right: sum(priorities)
    via_sum = sum(priorities)
    print(f"reduce(add, priorities): {via_reduce}")
    print(f"sum(priorities):         {via_sum}")
    print(f"equal? {via_reduce == via_sum}")

    # The list-comprehension-beats-reduce opinion, made concrete:
    # `sum(t.priority for t in tickets)` is one expression; reduce needs three imports
    # (functools, operator), a function call (reduce), a binary op (operator.add),
    # and an initial value (0). sum() is shorter, faster, and standard.

    # The product case: no built-in, so reduce(operator.mul, ...) is acceptable
    via_reduce_mul = functools.reduce(operator.mul, weights, 1.0)
    # Or math.prod on 3.8+
    import math
    via_math_prod = math.prod(weights)
    print(f"reduce(mul, weights): {via_reduce_mul}")
    print(f"math.prod(weights):   {via_math_prod}")
```

The opinion, made concrete. `functools.reduce(operator.add, priorities, 0)` threads `+` across the priorities list, with `0` as the seed. The result is the sum. `sum(priorities)` produces the same result, with three advantages: (a) it's a single call, no imports beyond `sum` (which is a builtin), (b) it's faster — `sum` is a C function with a tight loop, while `reduce` calls `operator.add` N times through Python function-call machinery, (c) it reads in English. The lesson's opinion: every time you write `reduce(operator.add, ...)`, replace it with `sum()`.

The product case is more nuanced. There's no `product()` builtin, so `reduce(operator.mul, weights, 1.0)` is the textbook form. *But* `math.prod` (added in Python 3.8) is the senior-engineer form — it's a C function, faster, and reads in English. The lesson's opinion: on 3.8+, use `math.prod`; on older Python (which boardly doesn't support — see [[13-future/01-from-future-import-annotations]] for the version policy), `reduce(operator.mul, ...)` is the fallback.

**Why does `sum()` beat `reduce(operator.add, ...)`?** Three reasons, in order of impact. First, performance: `sum` is a C-level builtin that loops in C, while `reduce(operator.add, ...)` calls `operator.add` (a Python callable) N times — each call has Python function-call overhead. For 1,000 numbers the difference is microseconds; for 1,000,000 it's seconds. Second, readability: `sum(nums)` reads as "sum the numbers"; `reduce(operator.add, nums, 0)` reads as "fold add across nums starting at 0" — the latter requires the reader to know `reduce` and to mentally simulate the fold. Third, standardisation: `sum` is the idiom every Python engineer knows; `reduce(operator.add, ...)` is the idiom that signals "I'm being clever" — and cleverness is the bug. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to "always `sum`, never `reduce(add)`".

**Why does `math.prod` beat `reduce(operator.mul, ...)`?** The same three reasons. `math.prod` is C-level, reads in English, and is the standard idiom on 3.8+. The case where `reduce(operator.mul, ...)` survives is when the weights are *objects* with a custom `__mul__` (e.g. a `Weight` dataclass that returns a `WeightedTotal`), not plain numbers — `math.prod` only works on numeric iterables. For custom `__mul__`, the loop `total = 1.0; for w in weights: total *= w` is the senior-engineer form, not `reduce(operator.mul, ...)`.

### Lines 107–124: The "list comp beats reduce" opinion

```python
def list_comp_beats_reduce_opinion() -> None:
    """The opinion: a list comprehension usually beats reduce(operator.add, ...)."""
    # The pattern that tempts students:
    #   reduce(operator.add, [t.title + "\n" for t in tickets])
    # The senior-engineer form:
    titles_block = "".join(t.title + "\n" for t in tickets)
    print("titles joined:")
    print(titles_block)

    # Why join() wins: it's a single C call that knows the buffer size up front;
    # reduce(operator.add, strs) does N intermediate string allocations (quadratic
    # in the worst case). The list-comprehension-feeds-join pattern is the standard.

    # The 3-case rule from functools/05-reduce:
    # 1. Function composition (unknown-length callable chain) — reduce wins.
    # 2. Deep-merge of N dicts — reduce wins when N is dynamic.
    # 3. Chained binary op with no built-in — reduce wins.
    # Anything else: sum(), math.prod(), str.join(), or an explicit loop.
```

The string-join case is the textbook "don't use `reduce(operator.add, ...)`" example. `reduce(operator.add, [t.title + "\n" for t in tickets])` produces the same string as `"".join(t.title + "\n" for t in tickets)` — but `reduce` is *quadratic* in the worst case (every intermediate concatenation allocates a new string and copies the prefix), while `str.join` is *linear* (it pre-computes the total length, allocates once, and copies each piece into place).

The lesson's opinion, restated: a list comprehension (or generator) feeding a builtin (`sum`, `math.prod`, `str.join`, `dict.update`) almost always beats `reduce(operator.add, ...)`. The 3-case rule from [[02-functools/05-reduce]] is: (1) function composition, (2) deep-merge of dynamic-length dicts, (3) chained binary op with no builtin — these are the only cases where `reduce` survives. Everything else: builtin or loop.

**Why does `str.join` beat `reduce(operator.add, strs)`?** Because string concatenation via `+` is O(n²) for n strings — each `a + b` allocates a new string and copies both. `str.join` is O(n) — it pre-computes the total length with one pass over the iterable, allocates the buffer once, then copies each piece into place. For 1,000 strings of 100 bytes each, `join` is ~100ms; `reduce(add, strs)` is ~10s (100x slower). This is the most common "reduce is wrong" bug in production Python code — and the fix is always `str.join`.

**Why does the lesson include `reduce` at all if it almost always loses?** Because the operator table exists, the `reduce` composition is the textbook example, and the lesson's job is to teach the operator table *and* the opinion. The student who learns `operator` without the opinion writes `reduce(operator.add, nums)` in production; the student who learns both writes `sum(nums)`. The opinion is the lesson — the operator table is the vocabulary.

## Execution Trace

```bash
$ uv run python boardly/operator_composition_demo.py
=== arithmetic table ===
add(2, 3)     = 5
sub(5, 2)     = 3
mul(2, 3)     = 6
truediv(7, 2) = 3.5
floordiv(7, 2)= 3
mod(7, 3)     = 1
pow(2, 3)     = 8
apply_op('+', 2, 3) = 5
apply_op('*', 2, 3) = 6

=== bitwise table ===
and_(1000, 10) = 0 (intersection)
or_(1000, 10)  = 1010 (union)
xor(1000, 10)  = 1010 (symmetric diff)
invert(1000)       = -1001 (bitwise NOT)
lshift(0b0001, 3)   = 1000
rshift(0b1000, 2)   = 10
union of all ticket statuses: 1111
is 'done' present? True

=== logical & container ===
truth([1, 2])  = True   (non-empty list is truthy)
truth([])      = False   (empty list is falsy)
not_([1, 2])   = False  (negation of truthy)
not_([])       = True  (negation of falsy)
contains([1,2,3], 2) = True  (2 in [1,2,3])
watched tickets: ['Search returns 500', 'Export to CSV']
watched (partial): ['Search returns 500', 'Export to CSV']

=== reduce vs sum: the opinion ===
reduce(add, priorities): 11
sum(priorities):         11
equal? True
reduce(mul, weights): 0.75
math.prod(weights):   0.75

=== list comp beats reduce ===
titles joined:
Search returns 500
Auth fails on macOS
Docs typo
Export to CSV
```

The first block shows the seven arithmetic functions and the dispatch-table use case. Each function returns the expected value (`add(2, 3) = 5`, etc.) and the dispatch table lookups (`OPS["+"](2, 3)` and `OPS["*"](2, 3)`) produce the same results as the direct calls.

The second block shows the bitwise operations. `and_(0b1000, 0b0010) = 0` because the two bits don't overlap (intersection is empty); `or_(0b1000, 0b0010) = 0b1010` because the union combines both bits; `xor(0b1000, 0b0010) = 0b1010` (same as `or_` here because the inputs don't overlap). `invert(0b1000)` returns `-1001` — the signed representation of `~0b1000`, which is `-9` in two's complement (the `:04b` format shows the negative bits). `lshift(0b0001, 3)` returns `0b1000`; `rshift(0b1000, 2)` returns `0b10`. The union of all four ticket statuses is `0b1111` — every status is present. `bool(0b1111 & 0b0100)` is `True` because "done" (0b0100) is in the bitmap.

The third block shows the logical and container callables. `operator.truth([1, 2])` is `True`; `operator.truth([])` is `False`. `operator.not_([1, 2])` is `False` (the negation of truthy); `operator.not_([])` is `True` (the negation of falsy). `operator.contains([1,2,3], 2)` is `True` because `2 in [1, 2, 3]`. The two filter forms (`operator.contains(WATCH, t.status)` and `is_watched(t.status)` via `partial`) produce the same list of watched tickets: the `in_progress` and `blocked` ones.

The fourth block shows the reduce-vs-sum opinion in action. `reduce(operator.add, priorities)` and `sum(priorities)` both produce `11` — the same value, with `sum` shorter, faster, and standard. `reduce(operator.mul, weights)` and `math.prod(weights)` both produce `0.75` — the same value, with `math.prod` shorter and faster on 3.8+.

The fifth block shows the string-join pattern producing the joined titles. The list-comprehension-feeds-`join` form is the senior-engineer pattern; `reduce(operator.add, ...)` would produce the same string but be O(n²) for large inputs.

## Common Mistakes

### Mistake 1: Using `reduce(operator.add, ...)` when `sum()` exists

```python
import functools, operator
total = functools.reduce(operator.add, nums, 0)  # ← don't
# Use:
total = sum(nums)
```

**Symptom:** Reviewer asks "why not just `sum()`?" on the pull request.

**Why:** `sum` is the standard idiom, faster (C-level), and reads in English. `reduce(operator.add, ...)` is the textbook example that students remember — but the lesson's whole point is "don't write this in production."

**Fix:** Use the builtin. Same for `math.prod` (3.8+) over `reduce(operator.mul, ...)`, `str.join` over `reduce(operator.add, strs)`, `max` over `reduce(max, ...)`, `any`/`all` over `reduce(operator.or_, ...)`/`reduce(operator.and_, ...)`.

### Mistake 2: Confusing `operator.contains(a, b)` with `a in b`

```python
# Wrong reading:
result = operator.contains([1, 2, 3], 5)
# Student reads as: "is [1,2,3] in 5?" → expects False (TypeError?)
# Actual:           "does [1,2,3] contain 5?" → returns False (no error)

# The reverse-order trap:
operator.contains("todo", statuses)  # ← calls "todo".__contains__(statuses)
                                       #     which is "statuses" in "todo" — the wrong direction
```

**Symptom:** The function returns `False` for an input that "should be `True`", or raises `TypeError` for a nonsensical argument.

**Why:** `operator.contains(a, b)` calls `a.__contains__(b)`, which is `b in a` — the same as the syntax form. The argument order is `contains(container, item)`, not `contains(item, container)`. The trap is that the *syntax* form (`item in container`) reads naturally left-to-right as "is item in container", but the *function* form mirrors the dunder, which puts the container first.

**Fix:** Read `operator.contains(a, b)` as "does `a` contain `b`?" — same order as `a.__contains__(b)`. If you find yourself confused, switch to the syntax form (`b in a`) which is unambiguous. The function form is only worth using when you need the operation as a value (e.g. via `partial`).

### Mistake 3: Using `operator.add` instead of `+` for performance

```python
# Misguided "optimisation":
result = operator.add(big_list, [4])  # ← student thinks this is faster than big_list + [4]
# Actual: it's the same call (operator.add just calls __add__), with extra function-call overhead
```

**Symptom:** No bug — but no speedup either. The student has rewritten a clear `a + b` into a less-clear `operator.add(a, b)` for no benefit.

**Why:** `operator.add` is a thin C wrapper around the `__add__` dunder call. Calling `operator.add(a, b)` has the same cost as `a + b` *plus* the cost of looking up the `operator.add` attribute and calling it as a function. The wrapper exists for *passing the operation as a value*, not for inlining in arithmetic.

**Fix:** Use the syntax form (`a + b`) for inline arithmetic. Reserve `operator.add` for the dispatch-table and `reduce` cases — when the operation is genuinely a value being passed around. The C-level operator *syntax* is always at least as fast as the function form; the function form exists for composability, not performance.

## Engineering Trade-Offs

**Decision:** Use `operator.<name>` only when the operation is genuinely a value — passed to `reduce`, `partial`, `map`, `filter`, or stored in a dispatch table. For inline arithmetic, use the syntax form (`a + b`, `a & b`, `b in a`). And in every `reduce(operator.add, ...)` call site, replace with `sum()` (or `math.prod`, `str.join`, etc.).

**Both sides:** The alternative is the lambda dispatch table — `OPS = {"+": lambda a, b: a + b, ...}`. The lambda table works but loses introspection (each value is a `<lambda>`) and loses composability with `partial` (`partial(lambda a, b: a + b, 2)` produces a partial-of-a-lambda, not a partial-of-`operator.add` which has a name and a C-level `__call__`). The `operator` table wins on introspection and composability; the lambda table wins only when the operation is a custom expression (e.g. `lambda a, b: a + b + 1`).

**Commitment:** `boardly` uses `operator.add`/`sub`/`mul`/`truediv`/`and_`/`or_`/`contains` in three places: (1) the SLA calculator's `apply_op(op_name, a, b)` dispatch table (`boardly/sla/calculator.py`), (2) the status-bitmap union via `reduce(operator.or_, flags, 0)` (`boardly/tetrics/daily.py`), and (3) the `partial(operator.contains, WATCH)` predicate factory (`boardly/tickets/filters.py`). Every `reduce(operator.add, ...)` is replaced by `sum()`; every `reduce(operator.mul, ...)` is replaced by `math.prod()`; every `reduce(operator.add, strs)` is replaced by `str.join()`. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule.

**Why use `operator` at all if `+` is always clearer?** Because the operation sometimes needs to be a *value*. The SLA calculator reads its operator from a config file — `op_name = config["combine_mode"]` — and dispatches via `OPS[op_name]`. The dispatch table needs `operator.add` (a value), not `+` (syntax). The status-bitmap union threads `|` across an unknown-length list — `reduce(operator.or_, flags, 0)` is the natural fit because `|` as a value is `operator.or_`. The `partial(operator.contains, WATCH)` factory needs `contains` as a value to pre-bind. These are the three real cases where `operator` is the right tool; everything else uses the syntax form.

## Exercises

1. **Exercise 1 — Replace `reduce(operator.add, ...)` with `sum()`.** Find the `via_reduce = functools.reduce(operator.add, priorities, 0)` line. Replace it with `via_reduce = sum(priorities)`. Verify the output is unchanged. `Verify: uv run python boardly/operator_composition_demo.py`

2. **Exercise 2 — Replace `reduce(operator.mul, ...)` with `math.prod()`.** Find the `via_reduce_mul = functools.reduce(operator.mul, weights, 1.0)` line. Replace it with `via_reduce_mul = math.prod(weights)` (the `import math` is already in the function). Verify the output is unchanged. `Verify: uv run python boardly/operator_composition_demo.py`

3. **Exercise 3 — Build a subtraction dispatch table.** Extend the `OPS` dict in `arithmetic_table` to include `"//": operator.floordiv, "%": operator.mod, "**": operator.pow`. Test each with `OPS["//"](7, 2)` and verify the outputs match `7 // 2 == 3`, `7 % 2 == 1`, `7 ** 2 == 49`. `Verify: uv run python boardly/operator_composition_demo.py`

4. **Exercise 4 — Add `operator.xor` to the status-bitmap demo.** Compute the symmetric difference between the day's bitmap and a "yesterday" bitmap. Use `operator.xor(today_bitmap, yesterday_bitmap)` to find the statuses that changed. Verify that adding a new status today produces the correct diff. `Verify: uv run python boardly/operator_composition_demo.py`

5. **Exercise 5 — The full predicate factory.** Build a `make_filter(allowed_set)` function that returns `functools.partial(operator.contains, allowed_set)`. Use it to build three predicates (`is_watched`, `is_closed`, `is_actionable`) from three sets. Filter the tickets list with each and verify the results. This exercise demonstrates the composition of `operator` + `partial` — the two modules are designed to work together. `Verify: uv run python boardly/operator_composition_demo.py`

## Verification

```bash
$ uv run python boardly/operator_composition_demo.py
=== arithmetic table ===
add(2, 3)     = 5
sub(5, 2)     = 3
mul(2, 3)     = 6
truediv(7, 2) = 3.5
floordiv(7, 2)= 3
mod(7, 3)     = 1
pow(2, 3)     = 8
apply_op('+', 2, 3) = 5
apply_op('*', 2, 3) = 6

=== bitwise table ===
and_(1000, 10) = 0 (intersection)
or_(1000, 10)  = 1010 (union)
xor(1000, 10)  = 1010 (symmetric diff)
invert(1000)       = -1001 (bitwise NOT)
lshift(0b0001, 3)   = 1000
rshift(0b1000, 2)   = 10
union of all ticket statuses: 1111
is 'done' present? True

=== logical & container ===
truth([1, 2])  = True   (non-empty list is truthy)
truth([])      = False   (empty list is falsy)
not_([1, 2])   = False  (negation of truthy)
not_([])       = True  (negation of falsy)
contains([1,2,3], 2) = True  (2 in [1,2,3])
watched tickets: ['Search returns 500', 'Export to CSV']
watched (partial): ['Search returns 500', 'Export to CSV']

=== reduce vs sum: the opinion ===
reduce(add, priorities): 11
sum(priorities):         11
equal? True
reduce(mul, weights): 0.75
math.prod(weights):   0.75

=== list comp beats reduce ===
titles joined:
Search returns 500
Auth fails on macOS
Docs typo
Export to CSV
```

## Previously Learned Here

- [[02-functools/05-reduce]] — `reduce` is the left-fold; `operator.add` is the canonical binary op passed to it. The two lessons are paired: this one teaches the operator table and the "use `sum` instead" opinion; the reduce lesson teaches the three rare cases where `reduce` genuinely wins.
- [[02-functools/03-partial]] — `partial(operator.contains, WATCH)` is the composition pattern that makes the predicate factory work. `operator` provides the binary callable; `partial` pre-binds the first argument.

## What's Next

You've finished Section 18. The natural next step is [[19-weakref/00-weakref-MOC]] — `weakref` is the standard-library module for "hold a reference without preventing garbage collection", and it pairs with `operator.attrgetter` for the "weakly-referenced callback" pattern (`weakref.finalize(obj, operator.attrgetter("close"), resource)`). Or, if you'd rather see the operator+functools composition in a wider context, jump to [[07-itertools/00-itertools-MOC]] (still being written) where `starmap(operator.add, pairs)` is the natural composition.

- `weakref.finalize` + `operator.attrgetter` — the "weakly-close-on-GC" pattern.
- `itertools.starmap` + `operator.add` — the "thread `+` across pairs" composition (still being written).
- The boardly `apply_op` dispatch table — production use of the operator table.

## Sources

- **`operator` — Standard operators as functions** — https://docs.python.org/3/library/operator.html — accessed 2026-10-23 — the canonical reference for the arithmetic, bitwise, comparison, logical, and container function tables.
- **`operator.contains`** — https://docs.python.org/3/library/operator.html#operator.contains — accessed 2026-10-23 — the canonical "containment test" callable. Note: no `operator.in_` is exposed in CPython 3.12, despite older documentation references.
- **`functools.reduce`** — https://docs.python.org/3/library/functools.html#functools.reduce — accessed 2026-10-23 — the canonical left-fold API, paired with this lesson's `operator` table.
- **`math.prod` (3.8+)** — https://docs.python.org/3/library/math.html#math.prod — accessed 2026-10-23 — the 3.8+ builtin for product-of-iterable, the senior-engineer alternative to `reduce(operator.mul, ...)`.
- **`str.join`** — https://docs.python.org/3/library/stdtypes.html#str.join — accessed 2026-10-23 — the linear-time string-join that beats `reduce(operator.add, strs)` (which is quadratic).

## What We Learned

- You can apply the arithmetic table — `operator.add`/`sub`/`mul`/`truediv`/`floordiv`/`mod`/`pow` as binary callables.
- You can apply the bitwise table — `operator.and_`/`or_`/`xor`/`invert` plus `lshift`/`rshift`.
- You can apply the logical/container callables — `operator.truth`, `operator.not_`, `operator.contains(a, b)` == `b in a`.
- You can compose `reduce(operator.add, nums)` — and articulate why `sum(nums)` is the senior-engineer form.
- You can articulate the "list comprehension beats `reduce(operator.add, ...)`" opinion and the three rare cases where `reduce` survives.
