---
title: "Lesson 02: Context and Precision"
aliases:
 - decimal Context
 - decimal.getcontext
 - decimal.localcontext
 - decimal rounding modes
 - decimal quantize
tags:
 - decimal
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "40–55 minutes"
prerequisites:
 - "[[17-decimal/01-Decimal-Basics]]"
related_lessons:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[17-decimal/03-Decimal-in-APIs]]"
first_taught_in: "17-decimal/02-Context-and-precision"
---

# Lesson 02: Context and Precision

*Why `boardly`'s tax calculation rounds `1.005` to `1.00` (banker's rounding, the default) and how to switch to `1.01` (half-up, the rounding you learned in school) for a single scope without leaking the change into the rest of the process.*

**You're at the very beginning of Section 17 — two lessons in.**

You can construct a `Decimal` correctly. You can add two `Decimal`s and trust the result. But you cannot, yet, control *how many digits* the result has, or *which way* it rounds when the result lands exactly on a half. Those two questions are the entire second half of the `decimal` module — the `Context` object, its precision and rounding mode, and the `localcontext()` context manager that lets you change both for a single scope. This lesson walks them, plus the signal classes (`InvalidOperation`, `Overflow`, `FloatOperation`) that turn silent imprecision into loud errors. By the end you will know how to round a `Project.budget` to two decimal places *correctly* — using `quantize()`, not `round()`. Take your time. Type every example. **This is how you learn.**

#decimal #canonical #context

## Learning Objectives

By the end of this lesson you will be able to:

1. **Read the default context** — call `decimal.getcontext()` and explain what `.prec=28` and `.rounding=ROUND_HALF_EVEN` mean, and why the context is thread-local.
2. **Construct a custom `Context`** — `Context(prec=10, rounding=ROUND_HALF_UP)` and predict which arithmetic results change versus the default context.
3. **Use `localcontext()`** — write a `with localcontext() as ctx:` block, mutate `ctx.prec` inside, and confirm the change reverts on `__exit__`.
4. **Choose a rounding mode by name** — name all six commonly used modes (`ROUND_HALF_EVEN`, `ROUND_HALF_UP`, `ROUND_HALF_DOWN`, `ROUND_DOWN`, `ROUND_UP`, `ROUND_05UP`), and pick the right one for finance vs display vs tax.
5. **Use `Decimal.quantize()`** — round a `Decimal` to exactly two decimal places with `Decimal("1.005").quantize(Decimal("0.01"))`, and explain why this is the correct rounding API where `round()` is the wrong one.
6. **Read the signal classes** — identify `InvalidOperation`, `DivisionByZero`, `Overflow`, `Inexact`, `Rounded`, `FloatOperation`, and explain what each traps and what the default trap state is.

## Prerequisites

Before starting, you need:

- **The string-constructor rule** — [[17-decimal/01-Decimal-Basics]]. Everything in this lesson assumes you are constructing `Decimal`s from strings; if you are still passing floats, the precision bugs compound under the context rounding in ways you cannot reason about.
- **The context-manager protocol** — [[03-contextlib/01-contextmanager]]. `localcontext()` is a context manager; the lesson reads its `__enter__`/`__exit__` semantics without re-explaining them.
- **About 40–55 minutes of focused time.**

**The most common gap: thinking `prec` means "decimal places".**

It does not. `prec` is *significant digits*, not *digits after the decimal point*. `prec=28` does not mean "two decimal places" — it means "up to 28 significant digits in any number the context produces". A budget of `Decimal("1234.567890")` has 8 significant digits and fits easily under `prec=28`. A unit price of `Decimal("0.00000001")` has 1 significant digit and also fits. A `Decimal("1") / Decimal("3")` under `prec=28` produces `0.3333333333333333333333333333` — 28 threes, because that is 28 significant digits. The two-decimal-place rounding you need for currency is a *separate* operation called `quantize()`, which is the second half of this lesson. Holding that distinction is the whole point.

## The Problem

Here is the bug that motivates the entire `Context` machinery. Read it slowly.

```python
# boardly/billing/bad_rounding.py — the bad old days
from decimal import Decimal

def line_total(price: Decimal, qty: int) -> Decimal:
    return price * qty

# A line item: 9.995 dollars, qty 1
total = line_total(Decimal("9.995"), 1)
print(round(total, 2))   # 9.99 or 10.00? which?
```

You might expect `round(Decimal("9.995"), 2)` to return `Decimal("10.00")` — that is the "round half up" rule you learned in school. But the `decimal` module's default rounding is *banker's rounding* (round half to even): the half-way value `9.995` sits exactly between `9.99` and `10.00`; banker's rounding picks the candidate whose last digit is even. `9.99` ends in `9` (odd); `10.00` ends in `0` (even). So banker's rounding picks `10.00`. Half-up also picks `10.00`. For this particular input the two modes agree.

But for `1.005` they do not. `1.005` is half-way between `1.00` and `1.01`; `1.00` ends in `0` (even), `1.01` ends in `1` (odd). Banker's picks `1.00`; half-up picks `1.01`. One cent of difference per invoice, on a million invoices, is real money. And the law in most jurisdictions says consumer tax is rounded half-up — so banker's rounding is *wrong* for that use case, by statute.

That is the bug. The `round()` builtin and the `decimal` module default to banker's rounding, which is the *right* choice for some contexts (statistics — round-to-even avoids a long-run bias toward larger values) and the *wrong* choice for others (consumer tax in most jurisdictions — the law usually says half-up). The fix is to know which rounding mode the active `Context` is using, and to be able to change it. This lesson shows you how.

## The Code

```python
# boardly/billing/context_and_precision.py
"""Context, precision, rounding modes, quantize, and the signal classes."""
import decimal
from decimal import (
    Decimal, getcontext, localcontext, Context,
    ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_DOWN, ROUND_05UP,
    InvalidOperation, Overflow, FloatOperation,
)


# 1. The default context
ctx = getcontext()
print(f"default prec={ctx.prec}, rounding={ctx.rounding}")   # prec=28, rounding=ROUND_HALF_EVEN

# 2. A custom context
high_prec = Context(prec=10, rounding=ROUND_HALF_UP)
print(f"custom  prec={high_prec.prec}, rounding={high_prec.rounding}")

# 3. Precision affects division, not addition
print("default 1/3 =", Decimal("1") / Decimal("3"))             # 0.3333333333333333333333333333
with localcontext() as scoped:
    scoped.prec = 10
    print("scoped 1/3   =", Decimal("1") / Decimal("3"))       # 0.3333333333
print("after scope 1/3 =", Decimal("1") / Decimal("3"))       # 0.3333333333333333333333333333 again

# 4. Rounding modes: banker's (default) vs half-up vs down
half_way = Decimal("1.005")
print("quantize HALF_EVEN:", half_way.quantize(Decimal("0.01")))                          # 1.00
print("quantize HALF_UP:  ", half_way.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))   # 1.01
print("quantize DOWN:     ", half_way.quantize(Decimal("0.01"), rounding=ROUND_DOWN))      # 1.00

# 5. localcontext with a pre-built Context
scoped_ctx = Context(prec=6, rounding=ROUND_HALF_UP)
with localcontext(scoped_ctx) as ctx_in:
    print(f"inside: prec={getcontext().prec}, rounding={getcontext().rounding}")   # prec=6, HALF_UP
    print("inside 1/3 =", Decimal("1") / Decimal("3"))                              # 0.333333
print(f"after: prec={getcontext().prec}, rounding={getcontext().rounding}")       # prec=28, HALF_EVEN

# 6. The boardly tax calculation, scoped correctly
def tax_round(amount: Decimal) -> Decimal:
    """Round a tax amount to 2 decimal places, half-up (consumer-tax convention)."""
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        return amount.quantize(Decimal("0.01"))

print("tax 1.005 ->", tax_round(Decimal("1.005")))               # 1.01
print("tax 1.004 ->", tax_round(Decimal("1.004")))               # 1.00
print("tax 2.5   ->", tax_round(Decimal("2.5")))                  # 2.50

# 7. Signals and traps
print("default traps:", {k.__name__: v for k, v in getcontext().traps.items()})

# FloatOperation is not trapped by default — but you can trap it
with localcontext() as ctx:
    ctx.traps[FloatOperation] = True
    try:
        Decimal(0.1)                       # raises FloatOperation
    except FloatOperation as e:
        print("FloatOperation trapped:", e)   # [<class 'decimal.FloatOperation'>]

# Overflow IS trapped by default — product exponent exceeds Emax (999999)
try:
    Decimal("1e999999") * Decimal("1e999999")
except Overflow as e:
    print("Overflow trapped:", str(e)[:60])

# InvalidOperation IS trapped by default — sqrt of negative
try:
    Decimal("-1").sqrt()
except InvalidOperation as e:
    print("InvalidOperation trapped:", str(e)[:60])
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the default context

```python
import decimal
from decimal import (
    Decimal, getcontext, localcontext, Context,
    ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_DOWN, ROUND_05UP,
    InvalidOperation, Overflow, FloatOperation,
)
```

The `import decimal` line gives you the module namespace — useful for `decimal.Decimal` (the long form), `decimal.Context` (the constructor), and the `decimal.getcontext()` call. The `from decimal import ...` line pulls the names you will type most often. `Decimal` and `Context` are classes; `getcontext` and `localcontext` are functions; the `ROUND_*` constants are enum members of `decimal.Rounding`; `InvalidOperation`, `Overflow`, and `FloatOperation` are signal classes (subclasses of `decimal.DecimalException`).

The complete set of rounding modes is `ROUND_CEILING`, `ROUND_FLOOR`, `ROUND_UP`, `ROUND_DOWN`, `ROUND_HALF_EVEN`, `ROUND_HALF_DOWN`, `ROUND_HALF_UP`, and `ROUND_05UP` (eight total). The four imported above are the four you will see in 99% of production code; the other four are specialised.

**Why are rounding modes constants and not strings?** Because the `decimal` module wants the mode checked at the point of use. A typo `rounding="HALF_UP"` would silently produce wrong results if the mode were a string; `rounding="HALF_UP"` is a typo that the enum catches at import (or at call) time — `AttributeError: module 'decimal' has no attribute 'HALF_UP'`. The enum membership is the type-check; the string would not be.

### Lines 11–12: The default context

```python
ctx = getcontext()
print(f"default prec={ctx.prec}, rounding={ctx.rounding}")   # prec=28, rounding=ROUND_HALF_EVEN
```

`decimal.getcontext()` returns the *current thread's* default `Context`. The CPython implementation stores one context per thread (`threading.local`-backed) so that two threads doing money arithmetic do not stomp on each other's precision setting. If you `getcontext().prec = 10` in thread A, thread B's context is unaffected — and on a multi-threaded FastAPI server (or any `concurrent.futures.ThreadPoolExecutor`), that is the difference between correct billing and an intermittent precision bug.

The default `.prec=28` means "up to 28 significant digits in any result the context produces". The number 28 is the IBM General Decimal Arithmetic Specification's recommended default — large enough for any monetary or scientific calculation, small enough to fit comfortably in memory. The default `.rounding=ROUND_HALF_EVEN` is the "banker's rounding" mode: half-way values round to the nearest even last digit. That is the IEEE 754 default for binary floats too — `round()` in Python uses banker's rounding for the same reason. It is the *statistics* default; it is not the *consumer finance* default.

**Why is `ROUND_HALF_EVEN` the default and not `ROUND_HALF_UP`?** Because banker's rounding has zero bias over a large sample. If you round a million half-way values half-up, your totals drift systematically upward; if you round them half-down, they drift downward. Banker's rounding — half to even — alternates the direction based on the last digit, and the long-run bias is zero. That is the right choice for statistics and for IEEE 754 binary floats. It is *not* the right choice for consumer tax in most jurisdictions, which legally specifies half-up. The `decimal` module defaults to the statistical choice and lets you override for finance. Lesson 03 walks the Pydantic / FastAPI integration where this default-vs-override matters most.

### Lines 14–16: A custom Context

```python
high_prec = Context(prec=10, rounding=ROUND_HALF_UP)
print(f"custom  prec={high_prec.prec}, rounding={high_prec.rounding}")
```

`Context(prec=10, rounding=ROUND_HALF_UP)` constructs a `Context` instance without making it the active context. The `Context` is a plain object — you can hold a reference to it, pass it to functions, store it in a module-level constant. To *use* it, you pass it to `localcontext()` (next block) or you call methods on it directly (`high_prec.divide(Decimal("1"), Decimal("3"))`).

The most useful `Context` constructor arguments are `prec` (int, default 28), `rounding` (a `Rounding` member, default `ROUND_HALF_EVEN`), and `traps` (a dict mapping signal class to bool, default set in the module — `InvalidOperation`, `DivisionByZero`, `Overflow` trapped; everything else not). There is also `Emax` and `Emin` (the exponent bounds, default 999999 and -999999) and `capitals` (whether `E` or `e` is used in the string form — defaults to 1, capital `E`).

**Why build a `Context` and not just mutate `getcontext()`?** Because mutating the global thread-local context is a side effect with indefinite scope. If you write `getcontext().prec = 6` at the top of a function, every other function on the same thread — including library code you do not own — is now running at precision 6 until your function returns and you remember to set it back. Forgetting to restore is a real bug. The `Context` object plus `localcontext(ctx)` is the *scoped* form: the change applies for the duration of the `with` block, then reverts. That is the discipline the rest of this lesson enforces.

### Lines 18–24: `localcontext()` as a context manager

```python
print("default 1/3 =", Decimal("1") / Decimal("3"))             # 0.3333333333333333333333333333
with localcontext() as scoped:
    scoped.prec = 10
    print("scoped 1/3   =", Decimal("1") / Decimal("3"))       # 0.3333333333
print("after scope 1/3 =", Decimal("1") / Decimal("3"))       # 0.3333333333333333333333333333 again
```

`localcontext()` returns a context manager. The `with` statement calls `__enter__`, which copies the current thread-local context (a *copy* — not a reference) and installs the copy as the new active context. The block body mutates `scoped.prec` to `10`, and arithmetic inside the block uses the new precision. On `__exit__`, the previous context is restored — the `scoped` copy is discarded.

`Decimal("1") / Decimal("3")` outside the block uses `prec=28` and returns `0.3333333333333333333333333333` (28 threes). Inside the block, `prec=10` makes the same division return `0.3333333333` (10 threes). After the block, the active context is the original default again, and the division returns the 28-three version.

The copy-on-`__enter__` semantics matter. If `localcontext()` returned a reference to the live context, mutating it inside the block would mutate the global state, and the change would not revert on `__exit__`. The copy is what makes the scope safe — and it is also what makes `localcontext()` work correctly inside a `ThreadPoolExecutor` task without affecting sibling tasks.

**Why does addition not seem to be affected by `prec`?** Because addition only produces as many digits as the operands have — `Decimal("0.1") + Decimal("0.2")` produces `Decimal("0.3")`, which has 1 significant digit, well under any `prec`. The context precision is the *maximum* number of significant digits the result of an operation can have. Addition, subtraction, and multiplication of `Decimal`s whose result fits under `prec` are exact; division and roots, which can produce infinitely many digits, are rounded to `prec` digits. That is why the precision effect is visible on `1/3` and not on `0.1 + 0.2`.

### Lines 26–30: Rounding modes — banker's vs half-up vs down

```python
half_way = Decimal("1.005")
print("quantize HALF_EVEN:", half_way.quantize(Decimal("0.01")))                          # 1.00
print("quantize HALF_UP:  ", half_way.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))   # 1.01
print("quantize DOWN:     ", half_way.quantize(Decimal("0.01"), rounding=ROUND_DOWN))      # 1.00
```

`Decimal("1.005").quantize(Decimal("0.01"))` rounds the value `1.005` to two decimal places. The first argument — `Decimal("0.01")` — is the *quantum*: the granularity to round to. The exponent of the quantum (`-2`, because `0.01 = 1 * 10^-2`) is the number of decimal places the result will have. The result has the same exponent as the quantum — `Decimal("1.00")` (banker's, default) or `Decimal("1.01")` (half-up) — never more, never less.

The three lines show the same input rounded three different ways:

- `ROUND_HALF_EVEN` (banker's, the default): `1.005` is exactly half-way between `1.00` and `1.01`. The two candidates are `1.00` (last digit `0`, even) and `1.01` (last digit `1`, odd). Banker's picks the even one: `1.00`.
- `ROUND_HALF_UP`: the same half-way case rounds *away from zero*: `1.01`. This is the rule most people learned in school.
- `ROUND_DOWN`: rounds toward zero unconditionally: `1.00`. This is the rule for "truncate" — used for some accounting conventions and for display where you never want to over-state a value.

The `quantize()` method takes the rounding mode as a keyword argument *for that single call*; if omitted, it uses the active context's rounding mode. Lesson 03 will use this to round a tax amount half-up without changing the global context — the local override at the `quantize` call site.

**Why is `quantize()` the right API and `round()` the wrong one for currency?** Two reasons. First, `round(Decimal("1.005"), 2)` rounds to *significant digits* in some Python versions and to *decimal places* in others — the behaviour was clarified in Python 3.11 but is still fragile across versions. `quantize(Decimal("0.01"))` is unambiguous: the result has exactly the exponent of the quantum, period. Second, `quantize` raises `InvalidOperation` if the result would have more digits than the context precision allows — `Decimal("1e20").quantize(Decimal("0.01"))` raises because `100000000000000000000.00` has 23 significant digits and the default `prec=28` is fine, but the same call under `prec=6` would raise. That loud failure is what you want when the rounding you intended does not actually fit; `round()` silently truncates.

### Lines 32–36: `localcontext` with a pre-built `Context`

```python
scoped_ctx = Context(prec=6, rounding=ROUND_HALF_UP)
with localcontext(scoped_ctx) as ctx_in:
    print(f"inside: prec={getcontext().prec}, rounding={getcontext().rounding}")   # prec=6, HALF_UP
    print("inside 1/3 =", Decimal("1") / Decimal("3"))                              # 0.333333
print(f"after: prec={getcontext().prec}, rounding={getcontext().rounding}")       # prec=28, HALF_EVEN
```

`localcontext(ctx)` takes an optional `ctx` argument. If passed, the context manager installs that exact context for the duration of the block (after copying it, so mutations inside the block do not leak into the `scoped_ctx` object you are holding). If omitted, the manager copies the current thread-local context and lets you mutate the copy.

Inside the block, `getcontext()` returns the *installed* context — `scoped_ctx`'s values. `Decimal("1") / Decimal("3")` therefore uses `prec=6` and returns `0.333333` (six threes). After the block, `getcontext()` returns the original default again. The `ctx_in` variable inside the `with` block refers to the same installed context — mutating it inside the block affects arithmetic in the block but does not persist past `__exit__`.

The pattern is: build a `Context` once at module load (a module-level constant), then `with localcontext(MY_CONTEXT):` wherever you need that exact precision and rounding. The boardly `billing` module defines `TAX_CTX = Context(prec=10, rounding=ROUND_HALF_UP)` at module load and uses `with localcontext(TAX_CTX):` around every tax computation. The constant documents the choice; the `with` enforces the scope.

### Lines 38–44: The boardly tax-rounding function

```python
def tax_round(amount: Decimal) -> Decimal:
    """Round a tax amount to 2 decimal places, half-up (consumer-tax convention)."""
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        return amount.quantize(Decimal("0.01"))

print("tax 1.005 ->", tax_round(Decimal("1.005")))               # 1.01
print("tax 1.004 ->", tax_round(Decimal("1.004")))               # 1.00
print("tax 2.5   ->", tax_round(Decimal("2.5")))                  # 2.50
```

`tax_round` is the function the `boardly` `billing` module exposes for rounding line-item tax to two decimal places. It does three things in five lines:

1. `with localcontext() as ctx:` — open a scoped context, copying the current default. The variable `ctx` is the copy.
2. `ctx.rounding = ROUND_HALF_UP` — change the rounding mode on the copy. The default precision (28) is preserved; only the rounding mode is overridden.
3. `amount.quantize(Decimal("0.01"))` — round the value to two decimal places using the scoped rounding mode. Because the block's context is active, the `quantize` call picks up `ROUND_HALF_UP` without an explicit `rounding=` keyword argument.

The function is pure — it does not mutate any global state. The scoped context reverts on `__exit__`. The return value is a `Decimal` with `exponent=-2`, exactly two decimal places, rounded half-up. `tax_round(Decimal("1.005"))` returns `Decimal("1.01")`; `tax_round(Decimal("1.004"))` returns `Decimal("1.00")` (because `1.004` is *below* the half-way point, all rounding modes agree); `tax_round(Decimal("2.5"))` returns `Decimal("2.50")` (the `2.5` is rounded to two places by adding a trailing zero, which is exact).

**Why scope the context at all — why not pass `rounding=ROUND_HALF_UP` directly to `quantize()`?** Because for a single `quantize` call, the direct argument is shorter and equivalent. The scoped-context form wins when you have *multiple* operations that all need the same non-default rounding — for example, a function that computes three sub-totals, applies three tax rates, and sums them, all half-up. Putting the `with localcontext() as ctx: ctx.rounding = ROUND_HALF_UP` block around the whole function makes every operation in the body use the half-up rule, without repeating the keyword on every call. The two forms are not in conflict; they are different scopes of the same override.

### Lines 46–56: Signals and traps

```python
print("default traps:", {k.__name__: v for k, v in getcontext().traps.items()})

# FloatOperation is not trapped by default — but you can trap it
with localcontext() as ctx:
    ctx.traps[FloatOperation] = True
    try:
        Decimal(0.1)                       # raises FloatOperation
    except FloatOperation as e:
        print("FloatOperation trapped:", e)   # [<class 'decimal.FloatOperation'>]

# Overflow IS trapped by default — product exponent exceeds Emax (999999)
try:
    Decimal("1e999999") * Decimal("1e999999")
except Overflow as e:
    print("Overflow trapped:", str(e)[:60])

# InvalidOperation IS trapped by default — sqrt of negative
try:
    Decimal("-1").sqrt()
except InvalidOperation as e:
    print("InvalidOperation trapped:", str(e)[:60])
```

A `Context`'s `.traps` attribute is a dict mapping signal class to bool. If `traps[SIGNAL]` is `True`, that signal — when raised by an operation — becomes an exception. If `False`, the signal is recorded in the `Context`'s `.flags` (so you can inspect it after the fact) but no exception is raised. The default traps (printed by the first line) are: `InvalidOperation=True`, `FloatOperation=False`, `DivisionByZero=True`, `Overflow=True`, `Underflow=False`, `Subnormal=False`, `Inexact=False`, `Rounded=False`, `Clamped=False`.

`FloatOperation` is the signal you turn on to enforce the section's cardinal rule (never accept a `float`). With `ctx.traps[FloatOperation] = True`, the line `Decimal(0.1)` raises `FloatOperation` instead of silently producing the 55-digit monster. That is the loud-failure form of "always pass a string". The boardly `billing` module turns this trap on at import time so any `Decimal(float)` anywhere in the billing code is a loud error.

`Overflow` is trapped by default. The trigger is a result whose exponent exceeds the context's `Emax` (default `999999`). `Decimal("1e999999") * Decimal("1e999999")` produces a value whose exponent is `1,999,998` — well above `Emax` — so the context raises `Overflow`. The construction of `Decimal("1e999999")` itself is fine, because the exponent `999999` is exactly equal to `Emax` and is allowed at construction time; only the *product* exceeds the bound. A silently-overflowed `Decimal` would be a wildly wrong value with no warning, so this trap is on by default and you almost never turn it off.

`InvalidOperation` is trapped by default. `Decimal("-1").sqrt()` is invalid (no real square root of a negative number) and raises `InvalidOperation`. The same signal fires for `Decimal("abc")` (unparseable string), `Decimal("Infinity") - Decimal("Infinity")` (indeterminate), and `Decimal("0") / Decimal("0")`.

**Why are only three signals trapped by default?** Because the `decimal` module's philosophy is "be loud about errors you cannot recover from (invalid operation, division by zero, overflow) and be quiet about things that are normal (inexact results, rounded results)". An `Inexact` result is the *ordinary* outcome of `1 / 3`; raising on every inexact result would make `decimal` unusable. The trap is there if you want it (a "strict precision" mode where every rounding is a bug), but it is off by default. The three trapped signals are the ones where the result is meaningless or the math is undefined; those, the module refuses to silently produce.

## Execution Trace

```bash
$ uv run python boardly/billing/context_and_precision.py
default prec=28, rounding=ROUND_HALF_EVEN
custom  prec=10, rounding=ROUND_HALF_UP
default 1/3 = 0.3333333333333333333333333333
scoped 1/3   = 0.3333333333
after scope 1/3 = 0.3333333333333333333333333333
quantize HALF_EVEN: 1.00
quantize HALF_UP:   1.01
quantize DOWN:      1.00
inside: prec=6, rounding=ROUND_HALF_UP
inside 1/3 = 0.333333
after: prec=28, rounding=ROUND_HALF_EVEN
tax 1.005 -> 1.01
tax 1.004 -> 1.00
tax 2.5   -> 2.50
default traps: {'InvalidOperation': True, 'FloatOperation': False, 'DivisionByZero': True, 'Overflow': True, 'Underflow': False, 'Subnormal': False, 'Inexact': False, 'Rounded': False, 'Clamped': False}
FloatOperation trapped: [<class 'decimal.FloatOperation'>]
Overflow trapped: [<class 'decimal.Overflow'>]
InvalidOperation trapped: [<class 'decimal.InvalidOperation'>]
```

## Common Mistakes

### Mistake 1: Mutating `getcontext()` directly

```python
getcontext().prec = 6        # global mutation
total = Decimal("1") / Decimal("3")   # 0.333333
# ... 500 lines later ...
other = Decimal("1") / Decimal("7")   # also 0.142857 — only 6 digits!
```

**Symptom:** Precision errors appear in unrelated code paths because you forgot to set the global context back.
**Why:** `getcontext()` returns the thread-local default; mutating it is a side effect with no scope. The change persists until you (or some other code) explicitly reverts it. Every library function you call between the mutation and the revert runs at the wrong precision.
**Fix:** Use `with localcontext() as ctx: ctx.prec = 6` for any precision override. The scope is the `with` block; the global context is untouched. Never call `getcontext().prec = ...` in production code.

### Mistake 2: Confusing `prec` with "decimal places"

```python
with localcontext() as ctx:
    ctx.prec = 2
    print(Decimal("1234.5678"))     # 1234.5678 — NOT rounded to 2 decimal places!
```

**Symptom:** You set `prec=2` expecting two decimal places, but the `Decimal` prints with all four — and arithmetic is rounded to two *significant digits*, not two decimal places.
**Why:** `prec` is the maximum number of *significant digits* in the result of an arithmetic operation, not the number of digits after the decimal point. `Decimal("1234.5678")` already has 8 significant digits; merely constructing or printing it does not invoke the context's precision (only arithmetic does). To round to two decimal places, you call `quantize(Decimal("0.01"))`.
**Fix:** Use `Decimal("1234.5678").quantize(Decimal("0.01"))` for two-decimal-place rounding. Use `prec` only when you genuinely want significant-digit precision — typically for scientific or statistical work, not money.

### Mistake 3: Using `round()` instead of `quantize()`

```python
total = round(Decimal("9.999"), 2)        # returns Decimal('10.00') in 3.11+? fragile
type(total)                                 # <class 'decimal.Decimal'> since 3.11 — but not guaranteed across versions
```

**Symptom:** Code that worked yesterday suddenly returns a `float` after a Python upgrade, and the imprecision you eliminated is back.
**Why:** `round()`'s behaviour on `Decimal` was clarified in Python 3.11 to return a `Decimal`, but the rule is fragile and the `ndigits` argument behaviour is not the same as `quantize`. The `round()` builtin was designed for `float`; `Decimal` is a guest.
**Fix:** `total = Decimal("9.999").quantize(Decimal("0.01"))`. The `quantize` API is the `decimal`-native rounding API; it returns a `Decimal` with the exact exponent of the quantum, always, on every Python version since 3.2.

### Mistake 4: Forgetting that rounding mode applies to division too

```python
with localcontext() as ctx:
    ctx.rounding = ROUND_HALF_UP
    print(Decimal("1") / Decimal("8"))    # 0.125 — not affected; no half-way case
    print(Decimal("1") / Decimal("16"))   # 0.0625 — same
    print(Decimal("1") / Decimal("3"))    # 0.3333333333... — rounds per prec, not half-way
```

**Symptom:** You set `ROUND_HALF_UP` expecting all your division to round half-up, and it appears to make no difference.
**Why:** The rounding mode applies *only when a result needs rounding* — that is, when the exact result has more digits than the context precision allows and the truncated portion is exactly half of the next digit. `1/8 = 0.125` exactly (3 digits, under any `prec`); no rounding happens. `1/3` does need rounding (infinite digits), but the rounding is to 28 significant digits — far from any half-way case at the truncation point. The rounding mode shows up most clearly on `quantize()`, where you are explicitly creating a half-way case.
**Fix:** Test your rounding mode on `Decimal("1.005").quantize(Decimal("0.01"))` — that is the canonical half-way test case. If that returns `1.01`, your mode is `ROUND_HALF_UP`; if `1.00`, it is `ROUND_HALF_EVEN`.

## Engineering Trade-Offs

**Decision:** Use `localcontext()` for every scoped precision/rounding override. Never mutate `getcontext()`. Use `quantize()` for currency-scale rounding.
**Both sides:** The alternative is to set `getcontext().prec` and `getcontext().rounding` once at application startup and live with the global setting. That is shorter and faster (no context-manager overhead per operation), and for a small single-threaded script it is fine. The trade-off is scope safety: a global mutation is a side effect with no boundary, and on a multi-threaded server (FastAPI runs handlers on a thread pool by default) you cannot safely mutate the thread-local default from inside a request handler without risking that a sibling request sees the wrong precision.
**Commitment:** `boardly` uses `localcontext()` for every precision/rounding override, and a module-level `TAX_CTX = Context(prec=10, rounding=ROUND_HALF_UP)` constant for the tax computation path. The constant documents the choice; the `with localcontext(TAX_CTX):` block enforces the scope. `quantize(Decimal("0.01"))` is the only rounding API used in the `billing` module — `round()` is forbidden by lint.

## Exercises

1. **Exercise 1 — Change the global rounding.** Inside the `tax_round` function, replace `with localcontext() as ctx: ctx.rounding = ROUND_HALF_UP` with `ctx.rounding = ROUND_HALF_UP` passed directly to `quantize`. Re-run and confirm the output is identical. `Verify: uv run python boardly/billing/context_and_precision.py | rg '^tax 1\.005'`
2. **Exercise 2 — Verify `localcontext` reverts.** Add a print of `getcontext().prec` immediately *before* and *immediately after* the `with localcontext(scoped_ctx):` block. Confirm both print `28`. `Verify: uv run python boardly/billing/context_and_precision.py | rg 'prec=28'`
3. **Exercise 3 — All eight rounding modes.** Write a function that, given a `Decimal`, prints its `quantize(Decimal("0.01"))` result under each of the eight `ROUND_*` modes — `ROUND_CEILING`, `ROUND_FLOOR`, `ROUND_UP`, `ROUND_DOWN`, `ROUND_HALF_EVEN`, `ROUND_HALF_DOWN`, `ROUND_HALF_UP`, `ROUND_05UP`. Test on `Decimal("1.005")` and `Decimal("1.015")`. Document the differences. `Verify: uv run python -c "from boardly.billing.context_and_precision import all_modes; all_modes(Decimal('1.005'))"`
4. **Exercise 4 — FloatOperation trap.** At module load, install a context with `FloatOperation` trapped. Try to construct `Decimal(0.1)`. Confirm the exception is raised. Then construct `Decimal("0.1")` and confirm it succeeds. `Verify: uv run python -c "import boardly.billing.context_and_precision as m; m.enable_floatoperation_trap(); import decimal; print('ok' if m.try_float() else 'fail')"`
5. **Exercise 5 — Per-call vs scoped override.** Write two versions of a tax computation: one with `with localcontext() as ctx: ctx.rounding = ROUND_HALF_UP` and three `quantize` calls inside; one with three `quantize(..., rounding=ROUND_HALF_UP)` calls and no `with`. Measure them with `timeit`. Report which is faster and by how much. Hypothesise why. `Verify: uv run python -c "import timeit; print(timeit.timeit('f()', 'from boardly.billing.context_and_precision import tax_round_scoped as f', number=10000))"`

## Verification

```bash
$ uv run python boardly/billing/context_and_precision.py
default prec=28, rounding=ROUND_HALF_EVEN
custom  prec=10, rounding=ROUND_HALF_UP
default 1/3 = 0.3333333333333333333333333333
scoped 1/3   = 0.3333333333
after scope 1/3 = 0.3333333333333333333333333333
quantize HALF_EVEN: 1.00
quantize HALF_UP:   1.01
quantize DOWN:      1.00
inside: prec=6, rounding=ROUND_HALF_UP
inside 1/3 = 0.333333
after: prec=28, rounding=ROUND_HALF_EVEN
tax 1.005 -> 1.01
tax 1.004 -> 1.00
tax 2.5   -> 2.50
default traps: {'InvalidOperation': True, 'FloatOperation': False, 'DivisionByZero': True, 'Overflow': True, 'Underflow': False, 'Subnormal': False, 'Inexact': False, 'Rounded': False, 'Clamped': False}
FloatOperation trapped: [<class 'decimal.FloatOperation'>]
Overflow trapped: [<class 'decimal.Overflow'>]
InvalidOperation trapped: [<class 'decimal.InvalidOperation'>]
```

## Previously Learned Here

- [[17-decimal/01-Decimal-Basics]] — the `Decimal` type, the string-constructor rule, and `as_tuple()`. This lesson builds the context machinery on top of that foundation.
- [[03-contextlib/01-contextmanager]] — the `with` statement and the `__enter__`/`__exit__` protocol that `localcontext()` implements. The `decimal` module's `localcontext` is a textbook use of the protocol.

## What's Next

[[17-decimal/03-Decimal-in-APIs]] — You can construct a `Decimal`, you can scope precision and rounding. Now we need to talk to the outside world. A `Decimal` field in a Pydantic model serialises to a JSON string (`"1.00"`, not `1.0`). A FastAPI `response_model=Project` produces an OpenAPI schema that declares `budget` as a string. And the boundary — the moment the request body arrives as JSON — is where the "never accept float" rule has to be enforced, because Pydantic v2 *does* accept a JSON float for a `Decimal` field and silently captures its imprecision. Lesson 03 walks the full request→validate→compute→respond path with `boardly`'s `/projects` endpoint, plus the `int`-cents alternative for systems where the `Decimal` overhead is genuinely too high.

- **Lesson 03** — Pydantic `Decimal` fields, FastAPI `response_model`, the never-accept-float rule, the `int`-cents alternative.

## Sources

- **Python `decimal` module documentation** — https://docs.python.org/3/library/decimal.html — accessed 2026-10-23 — the source-of-truth reference for `Context`, `getcontext`, `localcontext`, `quantize`, the rounding modes, and the signal classes.
- **IBM General Decimal Arithmetic Specification** — http://speleotrove.com/decimal/decarith.html — accessed 2026-10-23 — the IBM specification the `decimal` module implements; the rounding-mode definitions and the trap/flag distinction.
- **Python `round()` documentation** — https://docs.python.org/3/library/functions.html#round — accessed 2026-10-23 — the rounding behaviour of the builtin `round()` and the banker's-rounding default that `quantize()` mirrors.

## What We Learned

- You can now call `getcontext()` and read `.prec` and `.rounding` and explain why the context is thread-local.
- You can construct a `Context(prec=N, rounding=MODE)` and install it for a scope with `with localcontext(ctx):`.
- You can name the six common rounding modes and pick the right one for finance (`ROUND_HALF_UP`) vs statistics (`ROUND_HALF_EVEN`) vs truncation (`ROUND_DOWN`).
- You can use `Decimal.quantize(Decimal("0.01"))` to round a value to two decimal places, and you can explain why `quantize` is the right API where `round()` is the wrong one.
- You can install the `FloatOperation` trap to make the section's cardinal rule ("never accept a `float`") a loud error rather than a silent bug.
