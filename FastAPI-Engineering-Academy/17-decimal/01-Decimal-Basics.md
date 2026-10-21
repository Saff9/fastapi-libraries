---
title: "Lesson 01: Decimal Basics"
aliases:
 - Decimal
 - decimal.Decimal
 - Decimal basics
 - never float for money
tags:
 - decimal
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[17-decimal/02-Context-and-precision]]"
 - "[[17-decimal/03-Decimal-in-APIs]]"
first_taught_in: "17-decimal/01-Decimal-Basics"
---

# Lesson 01: Decimal Basics

*Why `boardly`'s `Project.budget` is `Decimal("1000.00")` and never `1000.0` — and the one-line bug that costs real money if you forget.*

**You're at the very beginning of Section 17.**

You have written `price = 0.1 + 0.2` and printed it and seen `0.30000000000000004` and learned to live with it. You have written `round(x, 2)` and seen `0.3` come back, and felt clever, and shipped it. And then one day a customer's invoice total comes out one cent wrong, and the finance team files a ticket, and you discover that "just round it" hides a whole class of bugs that compound across a thousand line items. This lesson shows you the standard-library fix: the `decimal.Decimal` type. It is exact where `float` is approximate, it preserves the digits you typed, and it is the only type you should ever use for money. Take your time. Type every example. **This is how you learn.**

#decimal #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `Decimal` correctly** — write `Decimal("0.10")` and explain why the string argument matters, while `Decimal(0.1)` captures the float's exact binary value and looks like `0.1000000000000000055511151231257827021181583404541015625`.
2. **Read the exactness guarantee** — explain why `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` is `True` while `0.1 + 0.2 == 0.3` is `False`, and what that means for billing arithmetic.
3. **Do arithmetic on `Decimal`** — `+`, `-`, `*`, `/` all return `Decimal`, with the rules you would expect from a hand-written ledger.
4. **Inspect a `Decimal`** with `.as_tuple()` — read the `sign`, `digits`, and `exponent` triple and reconstruct the value from it.
5. **State the rule** that the rest of the section depends on: never accept `float` for money. Always parse the string. Always store the `Decimal`.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. The boardly model uses `budget: Decimal`, and you need to be comfortable reading an annotation as a contract.
- **A typed model to attach the field to** — [[06-dataclasses/01-dataclass-Basics]]. This lesson writes `budget: Decimal` on a `Project` dataclass; the dataclass lesson is where the surrounding `field()` machinery lives.
- **About 30–45 minutes of focused time.**

**The most common gap: treating `Decimal` as a "more precise `float`".**

It is not. `Decimal` is a different *kind* of number — a base-10 number, with the digits you typed — not a base-2 approximation. The single biggest mistake students make in this section is writing `Decimal(0.1)` and being *surprised* that the precision bug is still there. It is still there because the bug was already in the `float` literal `0.1` before the `Decimal` constructor ever ran. `Decimal` does not rescue a `float`; it captures it. The fix is to never let the `float` exist in the first place. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/billing/bad_totals.py — the bad old days
def line_total(price: float, qty: int) -> float:
    return price * qty

def invoice_total(lines: list[tuple[float, int]]) -> float:
    return sum(line_total(p, q) for p, q in lines)

lines = [(0.10, 3), (0.20, 1), (0.30, 2)]
print(round(invoice_total(lines), 2))   # 1.1 ? maybe
```

`0.10` is not `0.10` in Python. It is the closest base-2 `float` to `0.10`, which is `0.1000000000000000055511151231257827021181583404541015625`. Multiply that by 3, add it to a similarly imprecise `0.20` and `0.30`, and the trailing digits you do not see are accumulating under the visible total. Round to two decimal places and sometimes the answer is right, sometimes it is one cent short, sometimes one cent over. The result depends on which intermediate imprecisions happened to cancel. You cannot reproduce the bug by adding it to a test, because the bug is non-deterministic across the float arithmetic the standard library performs internally.

This is not a Python problem. It is a base-2-float problem. Every language that uses IEEE 754 binary floats has the same bug. JavaScript has it. Go has it. Java `double` has it. The fix is the same in every language: do not use binary floats for money. Use a base-10 type. In Python, that type is `decimal.Decimal`.

The `decimal` module is the standard-library answer to "I need a number that behaves like the numbers on a calculator". `Decimal("0.1") + Decimal("0.2")` is `Decimal("0.3")` exactly, because every digit you typed is preserved exactly the way you typed it. There is no binary approximation step. There is no "closest representable value". There is just the decimal you wrote.

## The Code

```python
# boardly/billing/decimal_basics.py
"""The decimal type, the string-constructor rule, and the exactness guarantee."""
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class Project:
    name: str
    budget: Decimal                       # always Decimal, never float


# 1. The bug: passing a float captures the binary imprecision
print("Decimal(0.1) ->", Decimal(0.1))    # 0.1000000000000000055511151231257827021181583404541015625

# 2. The rule: always pass a string
print('Decimal("0.1") ->', Decimal("0.1"))   # 0.1

# 3. The exactness guarantee
float_total = 0.1 + 0.2
decimal_total = Decimal("0.1") + Decimal("0.2")
print("float 0.1 + 0.2 == 0.3:    ", float_total == 0.3)          # False
print("Decimal 0.1 + 0.2 == 0.3:  ", decimal_total == Decimal("0.3"))  # True

# 4. The boardly use: budget arithmetic
p = Project(name="alpha", budget=Decimal("1000.00"))
spent = Decimal("12.34")
remaining = p.budget - spent
print(f"{p.name} remaining: {remaining}")                        # 987.66
print("exact equality: ", remaining == Decimal("987.66"))         # True

# 5. Multiplication and division stay exact (within context precision)
unit_price = Decimal("9.99")
three = Decimal(unit_price) * Decimal(3)
print("9.99 * 3 ==", three)                                          # 29.97

# 6. Inspection: as_tuple reveals the digits
print("Decimal('1.00').as_tuple():", Decimal("1.00").as_tuple())   # DecimalTuple(sign=0, digits=(1, 0, 0), exponent=-2)

# 7. The forbidden pattern in billing
def bad_invoice_total(lines: list[tuple[float, int]]) -> float:
    return sum(p * q for p, q in lines)        # float * int -> float; bug

def good_invoice_total(lines: list[tuple[Decimal, int]]) -> Decimal:
    return sum(p * q for p, q in lines)       # Decimal * int -> Decimal; exact

lines_f = [(0.10, 3), (0.20, 1), (0.30, 2)]
lines_d = [(Decimal("0.10"), 3), (Decimal("0.20"), 1), (Decimal("0.30"), 2)]
print("float total raw:", bad_invoice_total(lines_f))            # 1.1 (looks clean; the underlying float is 1.1000000000000001)
print("Decimal total raw:", good_invoice_total(lines_d))        # 1.10 (exact; preserves the two-decimal-places scale)
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–10: The dataclass with a `Decimal` field

```python
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class Project:
    name: str
    budget: Decimal                       # always Decimal, never float
```

The `from decimal import Decimal` line is the only import you need for this lesson. The `decimal` module exports `Decimal` (the type), `Context` (the precision/rounding rules — lesson 02), `getcontext`/`localcontext` (the context accessors — lesson 02), and a set of rounding-mode constants and signal classes (also lesson 02). For construction and arithmetic, `Decimal` is everything.

The `@dataclass` decorator generates `__init__`, `__repr__`, `__eq__`, and `__hash__` (where appropriate) from the two annotated fields. The `budget: Decimal` annotation tells `@dataclass` (and your type checker, and FastAPI in lesson 03) that this field holds a `Decimal` instance. There is no default — `Project(name="alpha")` will raise `TypeError`. If you need a default budget, you write `budget: Decimal = Decimal("0.00")` (the literal default is fine because `Decimal` is immutable — see [[06-dataclasses/02-field-and-Defaults]] for why `[]` would not be).

**Why a `Decimal` literal default is safe where a `list` literal default is not:** `Decimal` is immutable — every operation returns a *new* `Decimal`; the existing one never changes. So two `Project` instances sharing the *same* `Decimal("0.00")` default is harmless: neither can mutate it. A `list` default, by contrast, is shared by reference and any mutation in one instance leaks into the next. The dataclass machinery forbids `budget: list = []` precisely for this reason; it does not forbid `budget: Decimal = Decimal("0.00")` because there is no mutation to leak. This is the same rule that makes `int`, `str`, `tuple`, and `frozenset` safe as defaults.

### Lines 12–17: The float-construction bug

```python
print("Decimal(0.1) ->", Decimal(0.1))    # 0.1000000000000000055511151231257827021181583404541015625
print('Decimal("0.1") ->', Decimal("0.1"))   # 0.1
```

The two lines look identical at a glance. They are not. The first line passes a `float` literal `0.1`. Before the `Decimal` constructor runs, Python has already parsed `0.1` into the IEEE 754 binary64 value closest to one-tenth — which is, in decimal, the long monster number you see in the comment. `Decimal(0.1)` calls `Decimal.from_float(0.1)` internally, which *captures* the float's exact value, all fifty-five digits of it. The bug you were trying to escape has already happened, and `Decimal` faithfully reproduces it.

The second line passes the string `"0.1"`. `Decimal.__new__` parses the string digit-by-digit, base-10, and builds a `Decimal` whose digits are exactly `1` and whose exponent is `-1`. No float was ever constructed. No imprecision was ever introduced. The result prints `0.1` because that is what you typed.

**Why does `Decimal(0.1)` not "round" to a clean `0.1`?** Because that would lie. The float `0.1` is *not* one-tenth — it is the binary number `0.0001100110011...` repeating, and its exact decimal value is the long string above. `Decimal` is a *number type*; its contract is to represent the value you gave it exactly. If you give it a binary float, it represents that binary float exactly, including its imprecision. The fix is to give it the decimal you actually meant — as a string — so the binary float is never constructed. There is no rescue at the `Decimal` layer for a `float` you already created; the rescue is upstream, in the literal you write.

**Danger — `Decimal(0.1)` is the section's silent bug**

The line compiles. It runs. It returns a `Decimal`. The `repr` even looks plausible if you do not look closely — it starts with `0.1`. It is not until you do the arithmetic that the trailing digits compound into a wrong total. Always construct from a string. Lint for `Decimal(<float>)` in code review. The trap is real and recurring.

### Lines 19–23: The exactness guarantee

```python
float_total = 0.1 + 0.2
decimal_total = Decimal("0.1") + Decimal("0.2")
print("float 0.1 + 0.2 == 0.3:    ", float_total == 0.3)          # False
print("Decimal 0.1 + 0.2 == 0.3:  ", decimal_total == Decimal("0.3"))  # True
```

`0.1 + 0.2` in Python returns `0.30000000000000004`. That is the IEEE 754 sum of the closest-binary-float-to-0.1 and the closest-binary-float-to-0.2, both of which are slightly above their decimal names, and the sum lands slightly above `0.3`. `0.3 == 0.3` is comparing two *different* binary floats — the left one is the sum (slightly above), the right one is the closest-binary-float-to-0.3 (slightly below). They are not the same bit pattern, so Python returns `False`.

`Decimal("0.1") + Decimal("0.2")` returns `Decimal("0.3")` exactly. Internally, the `decimal` module performs base-10 long addition on the digits — no approximation, no "closest representable value", no rounding step. The `==` comparison is digit-by-digit equality, and `Decimal("0.3") == Decimal("0.3")` is `True`. That is the exactness guarantee, and it is the single sentence that justifies the entire `decimal` module's existence.

**Why is this not the default for all Python numbers?** Because base-2 floats are roughly 100× faster than base-10 decimals — the CPU has dedicated silicon for IEEE 754 arithmetic, and `Decimal` is software-emulated (with C speedups in CPython 3.11+, but still software). For physics simulations, geometry, machine learning, anything where you would round to a tolerance anyway, `float` is right. For money, where one-cent errors compound over thousands of transactions and where the law requires the digits you typed, `Decimal` is right. The two types exist for two different notions of "number"; using the wrong one is the bug.

### Lines 25–29: The boardly budget arithmetic

```python
p = Project(name="alpha", budget=Decimal("1000.00"))
spent = Decimal("12.34")
remaining = p.budget - spent
print(f"{p.name} remaining: {remaining}")                        # 987.66
print("exact equality: ", remaining == Decimal("987.66"))         # True
```

`p.budget - spent` is `Decimal.__sub__`. The `__sub__` method computes the base-10 difference: `1000.00` minus `12.34` is `987.66`, with the two decimal places preserved. The result is `Decimal("987.66")` — exactly. Compare with `Decimal("987.66")` and you get `True`. There is no `round(..., 2)` call. There is no `abs(diff) < 0.01` tolerance check. The number you typed is the number you got back.

The string `f"{p.name} remaining: {remaining}"` formats the `Decimal` via `str()`, which returns `"987.66"` — the digits you would write by hand. Compare with `f"{1000.0 - 12.34}"` (the float version), which returns `"987.66"` *for this specific case* (the imprecision happens to round away at print time), but would have returned `"987.6600000000001"` for slightly different inputs. The `Decimal` version is reliably clean; the `float` version is reliably unreliable.

**Why does `Decimal` preserve the trailing zeros (`1000.00` has two decimal places, not one)?** Because the digit count is part of the value. `Decimal("1000.00")` and `Decimal("1000")` are mathematically equal (`==` returns `True`), but they are *different* `Decimal` instances: the first has `exponent=-2` and the second has `exponent=0`. The trailing-zero preservation is what lets you print a budget with exactly two decimal places, a tax rate with exactly four, and a unit price with exactly six — without storing the precision separately. The number carries its own scale.

### Lines 31–34: Multiplication stays exact within context precision

```python
unit_price = Decimal("9.99")
three = Decimal(unit_price) * Decimal(3)
print("9.99 * 3 ==", three)                                          # 29.97
```

`Decimal("9.99") * Decimal(3)` — note that `Decimal(3)` accepts an `int` without any precision loss, because integers are exact in Python (no binary approximation). The `*` returns `Decimal("29.97")`, exactly the value you would compute by hand.

The "within context precision" caveat matters: by default, the active context has `prec=28`, meaning the result is rounded to 28 significant digits if it would exceed that. `9.99 * 3 = 29.97` is well under 28 digits, so it is exact. `Decimal("1") / Decimal("3")` would return `Decimal("0.3333333333333333333333333333")` — 28 threes, because the context precision forces the rounding. Lesson 02 walks the precision and rounding model in detail.

**Why is `Decimal(3)` safe but `Decimal(0.1)` not?** Because `3` is an `int`, and integers in Python are arbitrary-precision exact values — there is no binary approximation step. `0.1` is a `float` literal, and the literal *is* the approximation step. The rule "always pass a string" is shorthand for the more precise rule "never pass a `float`"; passing an `int` is fine because `int`s are exact. The string rule is simpler to teach and to lint for, so we keep it.

### Lines 36–37: `as_tuple()` — the digit-level inspection

```python
print("Decimal("1.00").as_tuple():", Decimal("1.00").as_tuple())   # DecimalTuple(sign=0, digits=(1, 0, 0), exponent=-2)
```

`Decimal("1.00").as_tuple()` returns a `DecimalTuple` — a named tuple with three fields: `sign` (0 for positive, 1 for negative), `digits` (a tuple of the significant digits, here `(1, 0, 0)`), and `exponent` (the power of ten to multiply the digits by, here `-2`). To reconstruct the value: `sign=0` means positive; `digits=(1, 0, 0)` represents the integer `100`; `exponent=-2` means "divide by `10**2 = 100`"; so the value is `100 / 100 = 1.00`.

This is the internal representation of a `Decimal` — a sign, a tuple of digits, and an exponent. There is no binary mantissa; there is no IEEE 754 layout. The digits are exactly the digits you typed, in the order you typed them. When you need to know whether a `Decimal` has a particular number of decimal places — say, to validate a price has exactly two — `as_tuple()` is how you read it: `len(d.as_tuple().digits) + d.as_tuple().exponent` gives the number of digits after the decimal point.

**Why is `as_tuple` a named tuple and not a plain tuple?** Because named tuples support both attribute access (`t.sign`) and positional access (`t[0]`), and the `decimal` module chose to give you both. The class is `decimal.DecimalTuple`, and it behaves like any other `NamedTuple` — you can unpack it (`sign, digits, exponent = d.as_tuple()`), iterate it, or use the attribute names. Lesson 02 uses it for one of its exercises.

### Lines 39–46: The forbidden pattern, side by side

```python
def bad_invoice_total(lines: list[tuple[float, int]]) -> float:
    return sum(p * q for p, q in lines)        # float * int -> float; bug

def good_invoice_total(lines: list[tuple[Decimal, int]]) -> Decimal:
    return sum(p * q for p, q in lines)       # Decimal * int -> Decimal; exact

lines_f = [(0.10, 3), (0.20, 1), (0.30, 2)]
lines_d = [(Decimal("0.10"), 3), (Decimal("0.20"), 1), (Decimal("0.30"), 2)]
print("float total raw:", bad_invoice_total(lines_f))            # 1.1 (looks clean; the underlying float is 1.1000000000000001)
print("Decimal total raw:", good_invoice_total(lines_d))        # 1.10 (exact; preserves the two-decimal-places scale)
```

The two functions are line-for-line identical except for the type annotations. The `float` version prints `1.1` — *looks* clean, but the underlying float is the closest binary value to one-and-one-tenth, which is `1.100000000000000088817841970012523233890533447265625` (slightly *above* `1.1`). Python's `str(float)` returns the shortest decimal that round-trips to the same float — so it shows `1.1` and hides the trailing imprecision. The bug is real, just *hidden by the repr*. Compare with the `Decimal` version: it prints `1.10` — two decimal places, exactly, with the trailing zero preserved (the float version cannot preserve a trailing zero because the closest binary float to `1.10` is the same closest binary float to `1.1`). Run `Decimal.from_float(1.1) == Decimal("1.10")` and you get `False` — that is the bug, surfaced.

The `Decimal` version returns `Decimal("1.10")`. Two decimal places, exactly. The arithmetic inside `sum` is base-10 long addition: `0.10 * 3 = 0.30`, plus `0.20 * 1 = 0.20`, plus `0.30 * 2 = 0.60`, total `1.10`. No floating-point error. No rounding. No surprise. The function reads like the math you would do on paper, and it returns the value you would get on paper.

**Why does the float version look clean even though it is wrong?** Because each individual `float` literal `0.10`, `0.20`, `0.30` is *slightly above* its decimal name (the closest binary float to `0.10` is `0.1000000000000000055...`, which is greater than `0.10`). The multiplication `0.10 * 3` in float arithmetic rounds to the nearest representable value, which happens to be `0.30000000000000004` — slightly above. The sum then compounds the rounding errors: `0.30000000000000004 + 0.2 + 0.6` = `1.1` in the closest-binary-float sense, which *also* happens to be slightly above `1.1`. Python's `str(float)` shows the shortest round-trip form `1.1` because the closest binary float to `1.1` is the value we just computed. So the *print* looks clean, but `Decimal.from_float(1.1) != Decimal("1.10")` exposes the underlying drift. The exact direction of the drift is non-deterministic across inputs; what is deterministic is that the drift exists. `Decimal` eliminates the drift at the source.

## Execution Trace

```bash
$ uv run python boardly/billing/decimal_basics.py
Decimal(0.1) -> 0.1000000000000000055511151231257827021181583404541015625
Decimal("0.1") -> 0.1
float 0.1 + 0.2 == 0.3:     False
Decimal 0.1 + 0.2 == 0.3:   True
alpha remaining: 987.66
exact equality:  True
9.99 * 3 == 29.97
Decimal('1.00').as_tuple(): DecimalTuple(sign=0, digits=(1, 0, 0), exponent=-2)
float total raw: 1.1
Decimal total raw: 1.10
```

## Common Mistakes

### Mistake 1: Passing a float to `Decimal`

```python
budget = Decimal(0.1)            # 0.1000000000000000055511151231257827021181583404541015625
```

**Symptom:** A `Decimal` that looks like `0.1` until you do arithmetic with it, at which point it behaves like `0.1000000000000000055...` and totals are off by tiny fractions of a cent that compound into real money over thousands of transactions.
**Why:** `Decimal(0.1)` calls `Decimal.from_float(0.1)`, which faithfully reproduces the binary float's exact decimal value. The bug is in the `0.1` literal, not in `Decimal` — by the time the constructor runs, the imprecision is already locked in.
**Fix:** Always pass a string: `Decimal("0.1")`. If your data started life as a float (from a JSON request, a CSV import, an external API), convert via `Decimal(str(value))` *only* at the boundary — and prefer reading the raw string directly from the request so the float never exists. Lesson 03 covers the boundary pattern in detail.

### Mistake 2: Mixing `Decimal` and `float` in arithmetic

```python
total = Decimal("9.99") * 1.5      # TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
```

**Symptom:** `TypeError` on what looks like a perfectly reasonable multiplication.
**Why:** `Decimal` and `float` use different arithmetic; Python refuses to silently convert one to the other (it would re-introduce the imprecision the `Decimal` was protecting against). The mixed-type operation raises instead of guessing.
**Fix:** Convert the float to `Decimal` explicitly — but via the string path: `Decimal("9.99") * Decimal("1.5")`. If the `1.5` came from a calculation that genuinely was a float (a measurement, a ratio), ask whether it should be a `Decimal` from the start. Most of the time the answer is yes — if the result will be used in money arithmetic, every input to that arithmetic should be `Decimal`.

### Mistake 3: Comparing `Decimal` and `float` with `==`

```python
Decimal("0.1") == 0.1     # False
```

**Symptom:** A comparison that "obviously should be true" returns `False`, and your `if total == expected:` branch does not run.
**Why:** `Decimal.__eq__` refuses to silently coerce a `float` for comparison (same reasoning as for arithmetic) — but it *does* return `False` instead of raising, because the comparison is well-defined: a `Decimal` and a `float` are different types and a `Decimal` is never equal to a non-`Decimal` of any kind (with the exception of `int`, which is exact). The comparison is silently wrong, not loudly wrong.
**Fix:** Compare `Decimal` to `Decimal`. If the right-hand side is a literal, make it `Decimal("0.1")`. If it is a variable, you have a type problem upstream — the variable should have been a `Decimal` from the start.

### Mistake 4: Forgetting that `round()` returns a `float`

```python
total = round(Decimal("9.999"), 2)   # 10.00  (a float, not a Decimal!)
type(total)                            # <class 'float'>
```

**Symptom:** You rounded a `Decimal` to two decimal places, and the result is a `float` again — reintroducing the imprecision you just eliminated.
**Why:** The built-in `round()` calls `__round__` if the type defines it, but for `Decimal` it returns a `Decimal` in Python 3 (the rule was clarified in 3.11). However, calling `round(decimal_value, n)` *without* a second argument returns an `int`; calling `round(float_value, n)` returns a `float`. The behaviour is fragile and version-dependent. Use `Decimal.quantize()` (lesson 02) for currency-scale rounding instead.
**Fix:** `Decimal("9.999").quantize(Decimal("0.01"))` returns `Decimal("10.00")` — exactly two decimal places, still a `Decimal`. Lesson 02 walks `quantize` in detail.

## Engineering Trade-Offs

**Decision:** Use `Decimal` for every money value in `boardly`. Never `float`. Always construct from a string.
**Both sides:** The alternative is `float` (faster, simpler, native JSON) or `int`-cents (integer arithmetic, no `Decimal` overhead at all). `float` loses to `Decimal` on the exactness requirement — a billing system that occasionally produces wrong totals is broken. `int`-cents is genuinely viable for systems where every amount is a whole-cent multiple: store `$1.23` as `123`, do integer math, divide by 100 only at the boundary. It is faster than `Decimal`, it round-trips cleanly through JSON as a plain number, and it has no precision trap. The trade-off: `int`-cents cannot represent `$0.001` (per-API-call prices, tax rates to four places, gas prices to nine places) without rescaling, and every display conversion has to know the scale. `Decimal` carries its own scale (`as_tuple().exponent`), which is a feature `int`-cents pays for with extra code.
**Commitment:** `boardly` uses `Decimal` for `Project.budget`, `Ticket.price`, and every other money field. `Project.budget: Decimal = Decimal("0.00")` is the default. The `int`-cents alternative is documented in lesson 03 for systems that need the speed; we use `Decimal` because the team is small and the scale-tracking buys us more than the speed costs us.

## Exercises

1. **Exercise 1 — Add a third line item.** Add `(Decimal("0.40"), 5)` to `lines_d` and re-run. Confirm the total is `3.00` exactly. `Verify: uv run python boardly/billing/decimal_basics.py | rg 'Decimal total raw:'`
2. **Exercise 2 — Reproduce the float bug.** Add a `print(0.1 + 0.2)` line at the top of the script. Confirm the output is `0.30000000000000004`. Then add `print(Decimal("0.1") + Decimal("0.2"))`. Confirm it is `0.3`. `Verify: uv run python boardly/billing/decimal_basics.py | rg '^0\.3'`
3. **Exercise 3 — `as_tuple` deep dive.** Write a function `decimal_places(d: Decimal) -> int` that returns the number of digits after the decimal point, using `d.as_tuple()`. It should return `2` for `Decimal("1.00")`, `0` for `Decimal("100")`, `4` for `Decimal("0.0001")`. Handle negative exponents only. `Verify: uv run python -c "from boardly.billing.decimal_basics import decimal_places; from decimal import Decimal; assert decimal_places(Decimal('1.00'))==2 and decimal_places(Decimal('100'))==0 and decimal_places(Decimal('0.0001'))==4"`
4. **Exercise 4 — Compare `int`-cents to `Decimal`.** Add a third function `cents_total(lines: list[tuple[int, int]]) -> int` that takes line items as integer cents (`[(10, 3), (20, 1), (30, 2)]`) and returns the integer total. Confirm it returns `100` and the display value is `Decimal(cents_total(...)) / Decimal(100) == Decimal("1.00")`. `Verify: uv run python -c "from boardly.billing.decimal_basics import cents_total; from decimal import Decimal; assert Decimal(cents_total([(10,3),(20,1),(30,2)]))/Decimal(100)==Decimal('1.00')"`
5. **Exercise 5 — Lint for `Decimal(<float>)`.** Write a small AST-walking function that scans a Python file's source for `Decimal(...)` calls where the argument is a float literal (a number with a `.` in it) and prints a warning. Run it on `decimal_basics.py`. You should see *zero* warnings because the file uses strings. Insert a deliberate `Decimal(0.1)` and confirm the linter catches it. `Verify: uv run python -c "import boardly.billing.decimal_basics as m; import inspect; src=inspect.getsource(m); print('linted ok' if '0.1)' not in src or 'Decimal(0.1)' not in src else 'found bug')"`

## Verification

```bash
$ uv run python boardly/billing/decimal_basics.py
Decimal(0.1) -> 0.1000000000000000055511151231257827021181583404541015625
Decimal("0.1") -> 0.1
float 0.1 + 0.2 == 0.3:     False
Decimal 0.1 + 0.2 == 0.3:   True
alpha remaining: 987.66
exact equality:  True
9.99 * 3 == 29.97
Decimal('1.00').as_tuple(): DecimalTuple(sign=0, digits=(1, 0, 0), exponent=-2)
float total raw: 1.1
Decimal total raw: 1.10
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — the annotation syntax `budget: Decimal` that this lesson writes on the dataclass field.
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` decorator that generates `__init__`/`__repr__`/`__eq__` for the `Project` model this lesson uses as its running example.
- [[04-collections/04-namedtuple]] — `as_tuple()` returns a `DecimalTuple`, which is a `NamedTuple`; that lesson covers named-tuple semantics.

## What's Next

[[17-decimal/02-Context-and-precision]] — Now that you can construct a `Decimal` correctly and do exact arithmetic, we need to talk about what happens when the result has more digits than you want. `Decimal("1") / Decimal("3")` is not `0.333...` forever — the `decimal` module rounds it to the active context's precision (28 significant digits by default). That rounding follows a *mode* (banker's rounding by default, half-up on request), and the choice of mode is the difference between a finance-compliant total and a rounding bug. Lesson 02 walks `getcontext()`, `localcontext()`, the rounding modes, and the signal classes (`InvalidOperation`, `Overflow`, `FloatOperation`) that turn silent imprecision into loud errors when you want them to.

- **Lesson 02** — `Context`, `localcontext()`, rounding modes, `quantize()`.
- **Lesson 03** — `Decimal` in a Pydantic model and a FastAPI route; the never-accept-float-from-JSON rule.

## Sources

- **Python `decimal` module documentation** — https://docs.python.org/3/library/decimal.html — accessed 2026-10-23 — the source-of-truth reference for `Decimal`, `as_tuple`, `from_float`, and the exactness guarantee.
- **IBM General Decimal Arithmetic Specification** — http://speleotrove.com/decimal/decarith.html — accessed 2026-10-23 — the IBM specification the `decimal` module implements; the base-10 arithmetic rules and the rounding-mode definitions.
- **PEP 3141 — A Type Hierarchy for Numbers** — https://peps.python.org/pep-3141/ — accessed 2026-10-23 — where `Decimal` sits in Python's number ABC hierarchy (`numbers.Number`); context for `__eq__` returning `False` against `float`.

## What We Learned

- You can now construct a `Decimal` correctly: `Decimal("0.10")` from a string, never `Decimal(0.1)` from a float.
- You can explain why `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` is `True` while the float version is `False` — base-10 vs base-2 arithmetic.
- You can read `as_tuple()` and reconstruct a `Decimal`'s value from its `sign`, `digits`, and `exponent` triple.
- You can name the rule the rest of the section depends on: never accept `float` for money; parse the string at the boundary; store the `Decimal`.
- You can defend the choice of `Decimal` over `int`-cents, naming the trade-off (scale tracking vs speed) and the situation where each wins.
