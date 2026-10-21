---
title: "Lesson 05: reduce"
aliases:
 - functools.reduce
 - reduce
tags:
 - functools
 - reduce
 - functional-programming
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "15–25 minutes"
prerequisites:
 - "[[02-functools/04-singledispatch]]"
related_lessons:
 - "[[18-operator/01-itemgetter-attrgetter]]"
 - "[[18-operator/03-functional-composition]]"
---

# Lesson 05: `reduce`

*The standard-library left-fold that Guido himself wanted out of the builtins — and the three rare cases where you actually want it.*

**You're at the very beginning of Section 02.**

`functools.reduce` is the only function in the standard library that has an *opinion* attached to it. Guido van Rossum, in his famous 2005 essay "The fate of `reduce()` in Python 3000," wrote that he disliked it and wanted it gone — it ended up exiled to `functools` rather than removed outright. The opinion is: don't use `reduce` when a built-in (`sum`, `max`, `min`, `any`, `all`) does the job. The exception: there are three genuine cases where `reduce` is the right tool — composition of an unknown-length callable pipeline, deep-merge of an unknown-length dict sequence, and chained application of a binary operator with no built-in equivalent. By the end of this lesson you will know the rule, the exceptions, and why Guido was right. Take your time. Type every example. **This is how you learn.**

#functools #reduce #functional-programming

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `functools.reduce(fun, iterable, initial)`** as a left-fold over an iterable.
2. **Recite the "don't use `reduce`" rule** — every built-in (`sum`, `max`, `min`, `any`, `all`, `str.join`, `dict.update`) beats `reduce` when there's a built-in for the operation.
3. **Name the three cases `reduce` genuinely wins** — function composition, deep-merge of dicts, chained binary operators with no built-in.
4. **Compare `reduce` to an explicit loop** — both compute the same value; the loop is more readable; `reduce` is more composable.
5. **Read the accumulator threading** — explain how the `initial` value seeds the fold and how the binary function is called left-to-right.

## Prerequisites

Before starting, you need:

- **List comprehensions and `for` loops** — `for n in nums: total *= n` should feel natural.
- **Lambda syntax** — `lambda x, y: x + y` should be readable.
- **About 15–25 minutes of focused time.**

**The most common gap: reaching for `reduce` because it feels clever.**

`reduce` looks elegant on paper — one call, one accumulator, one binary function. In production code it reads as a puzzle: the reader has to mentally simulate the fold to know what's computed. A loop with an explicit `total = 1; for n in nums: total *= n` reads in seconds. The rule: when there's a built-in (`sum`, `max`, `min`), use it. When there's a loop, use the loop. When neither exists and the operation is genuinely a left-fold, use `reduce` — but document why.

## The Problem

You ship `boardly/config/loader.py` that merges three dicts: `defaults`, `env_overrides`, and `runtime_overrides`. The merge order matters — later dicts win — and the merge is *deep* (nested dicts merge recursively). A loop is fine:

```python
merged = {}
for d in [defaults, env_overrides, runtime_overrides]:
    merged = deep_merge(merged, d)
```

But what if the list is dynamic? What if `boardly` adds a fourth source tomorrow — say, `cli_overrides`? You'd write the same loop, and that's fine. But if the operation is "compose a list of N decorators" or "fold a list of validators," the loop form accumulates an explicit `acc` variable that's only there to be threaded through — there's no other use for it. That's the case where `reduce` reads cleaner: it makes the accumulator implicit, freeing the reader from tracking a variable that's never inspected.

## The Code

```python
# boardly/reduce_demo.py
"""Demonstrate functools.reduce — and why you usually shouldn't use it."""
from __future__ import annotations

import functools
import operator
from typing import Any, Callable


def sum_demo() -> None:
    """reduce(operator.add, ...) is the long way to spell sum()."""
    total = functools.reduce(operator.add, [1, 2, 3, 4], 0)
    total_sum = sum([1, 2, 3, 4])
    print(f"reduce: {total}, sum: {total_sum}")
    # reduce: 10, sum: 10 — built-in wins


def product_demo() -> None:
    """No built-in product(), so reduce+operator.mul is acceptable."""
    product = functools.reduce(operator.mul, [1, 2, 3, 4, 5], 1)
    # The loop form, for comparison:
    prod_loop = 1
    for n in [1, 2, 3, 4, 5]:
        prod_loop *= n
    print(f"product: {product} == loop: {prod_loop}")
    # product: 120 == loop: 120


def pipeline(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose left-to-right: pipeline(f, g, h)(x) = h(g(f(x))).

    The case reduce genuinely wins: an unknown-length composition of callables
    is awkward to write as a loop without an explicit accumulator variable.
    """
    return functools.reduce(
        lambda f, g: lambda x: g(f(x)),
        funcs,
        lambda x: x,  # identity — the initial accumulator
    )


def compose_demo() -> None:
    def double(x: int) -> int: return x * 2
    def add_one(x: int) -> int: return x + 1
    def to_str(x: int) -> str: return f"result={x}"

    p = pipeline(double, add_one, to_str)
    print(p(5))  # double(5)=10, add_one(10)=11, to_str(11)="result=11"


def deep_merge(a: dict, b: dict) -> dict:
    """Recursively merge b into a; b's values win on conflict."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def merge_demo() -> None:
    defaults = {"db": {"host": "localhost", "port": 5432}, "log": "info"}
    env_overrides = {"db": {"port": 9999}, "log": "debug"}
    runtime_overrides = {"db": {"host": "db.boardly.io"}}

    merged = functools.reduce(
        deep_merge, [defaults, env_overrides, runtime_overrides]
    )
    print(merged)
    # {'db': {'host': 'db.boardly.io', 'port': 9999}, 'log': 'debug'}


def never_use_reduce_for_max() -> None:
    """A function that exists only to warn you off."""
    worst = functools.reduce(max, [1, 5, 3])  # 5 — but max() is built-in
    best = max([1, 5, 3])                     # 5 — built-in wins
    print(f"worst: {worst}, best: {best}")


def main() -> None:
    sum_demo()
    product_demo()
    compose_demo()
    merge_demo()
    never_use_reduce_for_max()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports

```python
# boardly/reduce_demo.py
"""Demonstrate functools.reduce — and why you usually shouldn't use it."""
from __future__ import annotations

import functools
import operator
from typing import Any, Callable
```

`functools.reduce` is the star. `operator.add` and `operator.mul` are the C-implemented binary functions we pass to `reduce` — `operator.add(a, b)` is `a + b`, but callable as a function (which `reduce` requires). `Any` and `Callable` are typing-only.

### Lines 11–16: The boring case — sum

```python
def sum_demo() -> None:
    """reduce(operator.add, ...) is the long way to spell sum()."""
    total = functools.reduce(operator.add, [1, 2, 3, 4], 0)
    total_sum = sum([1, 2, 3, 4])
    print(f"reduce: {total}, sum: {total_sum}")
    # reduce: 10, sum: 10 — built-in wins
```

`functools.reduce(operator.add, [1, 2, 3, 4], 0)` threads the accumulator left-to-right: `acc = 0`, then `acc = operator.add(acc, 1) = 1`, then `acc = operator.add(acc, 2) = 3`, then `acc = 6`, then `acc = 10`. The `0` is the *initial* — the seed value that primes the accumulator before the first element. Without it, `reduce` would use the first element as the initial (and skip the first iteration), which is a frequent source of off-by-one bugs.

`sum([1, 2, 3, 4])` returns the same `10`, with three advantages: it's a single call, it's faster (implemented in C, with a tight loop), and it reads in English. This is the canonical "don't use `reduce`" case — every time you reach for `reduce(operator.add, ...)`, use `sum()` instead.

### Lines 19–26: The product case — no built-in, but a loop is also fine

```python
def product_demo() -> None:
    """No built-in product(), so reduce+operator.mul is acceptable."""
    product = functools.reduce(operator.mul, [1, 2, 3, 4, 5], 1)
    # The loop form, for comparison:
    prod_loop = 1
    for n in [1, 2, 3, 4, 5]:
        prod_loop *= n
    print(f"product: {product} == loop: {prod_loop}")
    # product: 120 == loop: 120
```

There's no `product()` built-in (PEP 450 rejected it; `math.prod` exists since 3.8 but only for iterables of numbers). `reduce(operator.mul, ..., 1)` is the classic. The `1` is the multiplicative identity, just as `0` is the additive identity in the sum case.

The loop form `prod_loop = 1; for n in nums: prod_loop *= n` computes the same value and reads in seconds. The lesson's opinion: use `math.prod` if you're on 3.8+ and have numbers; otherwise use the loop. `reduce(operator.mul, ...)` is acceptable but less readable than the loop — only choose it if you're passing the operation around as a value (e.g. configurable).

### Lines 29–37: The case reduce genuinely wins — function composition

```python
def pipeline(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose left-to-right: pipeline(f, g, h)(x) = h(g(f(x))).

    The case reduce genuinely wins: an unknown-length composition of callables
    is awkward to write as a loop without an explicit accumulator variable.
    """
    return functools.reduce(
        lambda f, g: lambda x: g(f(x)),
        funcs,
        lambda x: x,  # identity — the initial accumulator
    )
```

This is the case `reduce` genuinely wins. The function composes an arbitrary number of callables left-to-right: `pipeline(f, g, h)(x) = h(g(f(x)))`. The lambda `lambda f, g: lambda x: g(f(x))` takes two functions and returns a new function that threads them — apply `f` first, then `g`. `reduce` threads this binary operation across the entire `funcs` list, with `lambda x: x` (the identity function) as the seed.

The walk-through for `pipeline(double, add_one, to_str)`:
- `acc = lambda x: x` (identity)
- `next = double` → `acc = lambda x: double(identity(x))` ≈ `double`
- `next = add_one` → `acc = lambda x: add_one(double(x))`
- `next = to_str` → `acc = lambda x: to_str(add_one(double(x)))`

So `acc(5) = to_str(add_one(double(5))) = to_str(add_one(10)) = to_str(11) = "result=11"`. The closures capture correctly because each step's `f` and `g` are fresh parameters in the lambda's local scope, not shared mutable state.

**Why does `reduce` win here?** Because the loop form requires an explicit `acc` variable that's only threaded, never inspected:

```python
def pipeline_loop(*funcs):
    def composed(x):
        acc = x
        for f in funcs:
            acc = f(acc)
        return acc
    return composed
```

The loop is just as correct, but it forces the reader to track `acc` as a local variable in `composed`'s body. `reduce` makes `acc` implicit. For *pure composition* of unknown-length callable sequences, `reduce` is the cleaner read.

### Lines 40–43: The compose demo

```python
def compose_demo() -> None:
    def double(x: int) -> int: return x * 2
    def add_one(x: int) -> int: return x + 1
    def to_str(x: int) -> str: return f"result={x}"

    p = pipeline(double, add_one, to_str)
    print(p(5))  # double(5)=10, add_one(10)=11, to_str(11)="result=11"
```

Three nested `def`s, then `pipeline` composes them. Calling `p(5)` walks `5` through `double → add_one → to_str` and returns `"result=11"`. The composition is left-to-right: `double` runs first.

### Lines 46–54: The deep-merge function

```python
def deep_merge(a: dict, b: dict) -> dict:
    """Recursively merge b into a; b's values win on conflict."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
```

`deep_merge` is a binary operation: it takes two dicts, returns a merged dict. The merge is recursive — if both dicts have the same key with dict values, those inner dicts are merged. If a key is in `b` but not `a`, or if either value isn't a dict, `b`'s value wins. This is the canonical config-merge semantics: defaults < env < runtime < CLI.

`deep_merge` is itself a perfect candidate for `reduce` because it's an *associative binary operation with no built-in equivalent*. `functools.reduce(deep_merge, [d1, d2, d3])` folds the list of dicts into one merged dict, threading the accumulator through.

### Lines 57–65: The merge demo

```python
def merge_demo() -> None:
    defaults = {"db": {"host": "localhost", "port": 5432}, "log": "info"}
    env_overrides = {"db": {"port": 9999}, "log": "debug"}
    runtime_overrides = {"db": {"host": "db.boardly.io"}}

    merged = functools.reduce(
        deep_merge, [defaults, env_overrides, runtime_overrides]
    )
    print(merged)
    # {'db': {'host': 'db.boardly.io', 'port': 9999}, 'log': 'debug'}
```

The three dicts fold into one: `defaults` provides the seed structure (`db.host`, `db.port`, `log`), `env_overrides` updates `db.port` and `log`, `runtime_overrides` updates `db.host`. The merged dict reflects all three sources, with later sources winning. The `db` inner dict is recursively merged — `defaults`'s `{"host": "localhost", "port": 5432}` gets `port` overridden by `env_overrides` and `host` overridden by `runtime_overrides`, giving `{"host": "db.boardly.io", "port": 9999}`.

**Why is this the case `reduce` wins?** The loop form is:

```python
merged = {}
for d in [defaults, env_overrides, runtime_overrides]:
    merged = deep_merge(merged, d)
```

That's almost as readable — and for *three* sources, the loop wins. The case `reduce` wins is when the list of dicts is *dynamic* — `boardly/config/loader.py` might load N config sources from a plugin system, and the loader doesn't know N at authoring time. `reduce(deep_merge, sources)` handles any N uniformly; the loop form needs an explicit `merged = {}` initialization that's slightly noisier.

### Lines 68–73: The "never use reduce for max" demo

```python
def never_use_reduce_for_max() -> None:
    """A function that exists only to warn you off."""
    worst = functools.reduce(max, [1, 5, 3])  # 5 — but max() is built-in
    best = max([1, 5, 3])                     # 5 — built-in wins
    print(f"worst: {worst}, best: {best}")
```

The lesson's warning shot. `functools.reduce(max, [1, 5, 3])` computes `max(max(max(?, 1), 5), 3)` — but wait, there's no initial, so the first element `1` is the seed. So `acc = 1`, then `acc = max(1, 5) = 5`, then `acc = max(5, 3) = 5`. Returns `5`. The built-in `max([1, 5, 3])` returns `5` with one call, no threading, no thinking. Every time you write `reduce(max, ...)`, replace it with `max(...)`. Same for `min`, `any`, `all`, `str.join`.

## Execution Trace

```bash
$ uv run python boardly/reduce_demo.py
reduce: 10, sum: 10
product: 120 == loop: 120
result=11
{'db': {'host': 'db.boardly.io', 'port': 9999}, 'log': 'debug'}
worst: 5, best: 5
```

The first line confirms `reduce(add)` matches `sum()` — use `sum`. The second line confirms `reduce(mul)` matches the explicit loop — pick either, prefer the loop for clarity. The third line shows the composition working — `pipeline(double, add_one, to_str)(5)` returns `"result=11"`. The fourth line shows the deep-merge result. The fifth line shows that `reduce(max)` and `max()` produce the same value — but `max()` is the right tool.

## Common Mistakes

### Mistake 1: Using `reduce` when a built-in exists

```python
total = functools.reduce(operator.add, nums, 0)  # ← don't
# Use:
total = sum(nums)
```

**Symptom:** Reviewer asks "why not just `sum()`?" on the pull request.

**Why:** `sum` is a built-in that's faster, clearer, and the standard idiom. `reduce(operator.add, ...)` is a puzzle.

**Fix:** Use the built-in. Same for `max`, `min`, `any`, `all`, `str.join`, `dict.update`, `list.extend`.

### Mistake 2: Forgetting the `initial` argument

```python
functools.reduce(operator.add, [])  # ← raises TypeError
# Use:
functools.reduce(operator.add, [], 0)  # ← returns 0 (the identity)
```

**Symptom:** `TypeError: reduce() of empty iterable with no initial value` when the iterable is empty.

**Why:** Without an `initial`, `reduce` uses the first element as the seed — and an empty iterable has no first element. With an `initial`, `reduce` returns the `initial` unchanged for an empty iterable.

**Fix:** Always pass `initial` when the iterable might be empty. The idiom: `reduce(op, iterable, identity_value)`.

### Mistake 3: Late-binding closures in the composition lambda

```python
funcs = [double, add_one, to_str]
composed = functools.reduce(
    lambda f, g: lambda x: f(g(x)),  # ← late-binding: captures `f` and `g` by reference
    funcs,
    lambda x: x,
)
```

**Symptom:** The composition seems to apply only the *last* function multiple times, instead of all of them in sequence.

**Why:** In a regular `for` loop with `lambda`, late-binding bites — the closure captures `f` and `g` as names, and they end up bound to the last iteration's values. *But in `reduce`*, each step calls the outer lambda *immediately* with fresh parameters, so each inner lambda captures the correct `f` and `g` for that step. The `reduce` form actually avoids the late-binding bug.

**Fix:** This isn't actually a mistake in `reduce` — it's the *one* place the composition idiom works correctly without `functools.partial` or default-argument binding. Just be aware that the same idiom in a `for` loop *would* bite.

## Engineering Trade-Offs

**Decision:** Use `reduce` only when the operation is genuinely a left-fold *and* there's no built-in *and* the iterable length is unknown at authoring time. Otherwise use a built-in or an explicit loop.

**Both sides:** The alternative is always the explicit loop. The loop is more readable, debuggable (you can `print(acc)` inside the loop), and flexible (you can add side effects, early-exit, or branching). `reduce` is shorter and composable — you can pass `deep_merge` as a value to a higher-order function. For `boardly/config/loader.py`, the loader accepts a list of *sources* (callables returning dicts) and merges them — `reduce(deep_merge, sources)` is the natural fit. For a one-off merge of three dicts, the loop is fine.

**Commitment:** `boardly` uses `reduce` in three places: `pipeline` (the callable composition in `boardly/utils/compose.py`), `deep_merge` (the config-source merge in `boardly/config/loader.py`), and the rare case of an unknown-length validator chain (`boardly/validation/chain.py`). Every `reduce` call has a docstring naming why `reduce` was chosen over the loop. The project's lint config flags `reduce` with a comment-required rule — you must write `# reduce: <reason>` next to every `reduce` call.

**Why not ban `reduce` outright?** Because the three cases where it wins are real. Banning it forces authors to write the explicit `acc` variable, which is more code and harder to refactor. The right rule is "require a comment explaining why `reduce` was chosen" — not "ban it."

## Exercises

1. **Exercise 1 — Replace `reduce` with built-ins.** Find the three "wrong" uses of `reduce` in the file: `sum_demo` (use `sum`), `product_demo` (use `math.prod` if on 3.8+), `never_use_reduce_for_max` (use `max`). Replace each and verify identical output. `Verify: uv run python boardly/reduce_demo.py`

2. **Exercise 2 — Trace the accumulator.** Add a `print(f"acc={acc}")` inside a custom binary function passed to `reduce`. Confirm the accumulator threads correctly: `acc=0`, then `acc=1`, then `acc=3`, then `acc=6`, then `acc=10`. `Verify: uv run python -c "import functools, operator; fun = lambda a, b: (print(f'acc={a}, next={b}'), a + b)[1]; functools.reduce(fun, [1,2,3,4], 0)"`

3. **Exercise 3 — Compose with four functions.** Extend `compose_demo` to compose four functions (`double`, `add_one`, `to_str`, `upper = lambda s: s.upper()`). Verify the output is `"RESULT=11"`. `Verify: uv run python boardly/reduce_demo.py`

4. **Exercise 4 — Deep-merge with a fourth source.** Add `cli_overrides = {"db": {"port": 5433}, "log": "warning"}` to `merge_demo`. Use `reduce(deep_merge, [defaults, env_overrides, runtime_overrides, cli_overrides])`. Verify the merged dict has `db.port=5433` and `log="warning"`. `Verify: uv run python boardly/reduce_demo.py`

5. **Exercise 5 — Use `reduce` for a chain of validators.** Write a `validate_chain(validators, value)` that threads `value` through each validator. Each validator returns the (possibly transformed) value or raises `ValidationError`. Use `reduce`. Compare with the loop form and articulate when each wins. `Verify: uv run python boardly/reduce_demo.py`

## Verification

```bash
$ uv run python boardly/reduce_demo.py
reduce: 10, sum: 10
product: 120 == loop: 120
result=11
{'db': {'host': 'db.boardly.io', 'port': 9999}, 'log': 'debug'}
worst: 5, best: 5
```

## Previously Learned Here

- [[02-functools/04-singledispatch]] — `singledispatch` dispatches by type; `reduce` folds by binary operation. The two are different specialization axes — type and value-accumulation.

## What's Next

[[02-functools/06-cached_property]] — `cached_property` is `lru_cache`'s instance-level sibling. Where `lru_cache` caches a *function's* result by argument tuple, `cached_property` caches a *method's* result by instance. Together they cover the two main cache shapes — argument-keyed and instance-keyed.

- `@cached_property` — the per-instance cache.
- The threading lock (3.12 implementation).
- `cached_property` vs `lru_cache` vs the slotted-class bug.

## Sources

- **`functools.reduce`** — https://docs.python.org/3.12/library/functools.html#functools.reduce — accessed 2026-10-23 — the canonical reference for the left-fold API.
- **"The fate of `reduce()` in Python 3000"** — https://www.artima.com/weblogs/viewpost.jsp?thread=98196 — accessed 2026-10-23 — Guido van Rossum's 2005 essay explaining why `reduce` left the builtins.
- **`math.prod` (3.8+)** — https://docs.python.org/3.12/library/math.html#math.prod — accessed 2026-10-23 — the 3.8+ built-in for product-of-iterable, the right tool when `reduce(operator.mul, ...)` would be the alternative.

## What We Learned

- You can apply `functools.reduce(fun, iterable, initial)` as a left-fold.
- You can recite the "don't use `reduce`" rule — every built-in beats it.
- You can name the three cases `reduce` wins — composition, deep-merge, chained binary ops.
- You can compare `reduce` to an explicit loop and articulate when each is more readable.
- You can read the accumulator threading and explain why `initial` matters for empty iterables.
