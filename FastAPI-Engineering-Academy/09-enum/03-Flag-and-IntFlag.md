---
title: "Lesson 03: Flag and IntFlag"
aliases:
 - Flag
 - IntFlag
 - bit-flags enum
 - enum boundary
tags:
 - enum
 - python-stdlib
 - bit-flags
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[09-enum/01-Enum-Basics]]"
 - "[[09-enum/02-IntEnum-and-StrEnum]]"
related_lessons:
 - "[[09-enum/04-auto-and-value]]"
 - "[[09-enum/05-Enum-in-APIs]]"
---

# Lesson 03: Flag and IntFlag

*How `boardly`'s `PermFlag` bit-flags let one integer say "read + write" without an `int` slot per permission — and the 3.11 boundary modes that decide what happens when a value carries bits you didn't define.*

**You're at the very beginning of Section 09 — three lessons in.**

You have written `user.permissions = 0b0110` somewhere in your code. You have also written the comment `# bit 0 = read, bit 1 = write, bit 2 = delete, bit 3 = admin` next to it. Six months later, a junior developer reads `0b0110` and asks "what does that mean?" and you cannot remember either. `Flag` and `IntFlag` fix that — they give bit-flags *names*. Take your time. Type every example. **This is how you learn.**

#enum #bit-flags

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare a `Flag`** — write `class Perm(Flag): R = auto(); W = auto(); X = auto()` and explain why `auto()` produces powers of 2 by default.
2. **Use the bitwise operators** — combine members with `|`, intersect with `&`, toggle with `^`, invert with `~`, and explain why `Perm.R in (Perm.R | Perm.W)` returns `True`.
3. **Explain `Flag` vs `IntFlag`** — `Flag` members are not `int`s (no arithmetic, no equality with integers); `IntFlag` members are `int`s (arithmetic works, equality with integers works).
4. **Choose a boundary mode** — explain the four modes `STRICT`, `CONFORM`, `EJECT`, `KEEP`, and pick the right one for "the value came from outside and might carry bits I didn't define."
5. **Read a combined flag's repr** — `Perm.R | Perm.W`'s `repr` is `Perm.R|W`, and `Perm(0)` is the empty flag.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[09-enum/01-Enum-Basics]] — the singleton guarantee and the three lookup forms.
- **Lesson 02** — [[09-enum/02-IntEnum-and-StrEnum]] — the `int`/`str` mixin pattern; this lesson's `IntFlag` follows the same architectural shape.
- **About 35–45 minutes of focused time.**

**The most common gap: assuming `Flag` members are `int`s.** They are not — `Flag` (without `Int`) keeps its members as pure `Flag` instances, distinct from `int`. Only `IntFlag` members are integers. The distinction matters: `Flag` is type-safe; `IntFlag` is wire-compatible.

## The Problem

Here is the bug that motivates `Flag` and `IntFlag`. Read it slowly.

```python
# boardly/permissions.py — the bad old days
PERM_READ   = 0b0001
PERM_WRITE  = 0b0010
PERM_DELETE = 0b0100
PERM_ADMIN  = 0b1000

def can_do(user_perms, required):
    return bool(user_perms & required)
```

The bug is that `user_perms` is an `int` and `required` is an `int`. There is no type safety — `can_do(42, 7)` returns `True` for reasons unrelated to permissions. There is no enumeration of "which permissions exist?" — you have to read the module. There is no readable `repr` — `print(user_perms)` prints `7`, and you have to know that `7` means `READ | WRITE | DELETE`.

The deeper bug is the *out-of-range value*. Suppose a database stores `user_perms = 0b1111` (all four defined bits set) and you later add `PERM_SUPERADMIN = 0b10000`. The database has `0b1111`, which is fine. But suppose a buggy migration wrote `0b11111` (five bits). When you read that row, what should the enum do? Strip the unknown bit? Keep it as an `int`? Crash? Refuse? Each answer is correct for a different domain — and the 3.11 boundary modes exist precisely to let you choose.

## The Code

```python
# boardly/permissions.py
"""boardly's permission bit-flags."""
from enum import Flag, IntFlag, auto, STRICT, CONFORM, EJECT, KEEP

# 1. Flag — type-safe bit-flags (members are NOT ints)
class Perm(Flag):
    R = auto()
    W = auto()
    X = auto()

print(Perm.R)                         # Perm.R
print(Perm.R | Perm.W)                # Perm.R|W
print(type(Perm.R | Perm.W))          # <flag 'Perm'>
print(Perm.R in (Perm.R | Perm.W))    # True
print(Perm.R & Perm.W)                # Perm(0)   <- empty flag
print(bool(Perm.R & Perm.W))          # False
print(Perm(0))                        # Perm(0)
print(bool(Perm(0)))                  # False
print(~Perm.R)                        # Perm.W|X
print(Perm.R ^ Perm.W)               # Perm.R|W
print([m for m in Perm])             # [<Perm.R: 1>, <Perm.W: 2>, <Perm.X: 4>]
print(isinstance(Perm.R, int))       # False  <- Flag, not IntFlag

# 2. IntFlag — int-compatible bit-flags
class IPerm(IntFlag):
    R = 4
    W = 2
    X = 1

print(IPerm.R | IPerm.W)              # 6   <- str() inherits from int
print(repr(IPerm.R | IPerm.W))        # <IPerm.R|W: 6>
print(int(IPerm.R | IPerm.W))         # 6
print(IPerm.R | IPerm.W == 6)         # True
print(IPerm.R + 5)                    # 9   <- arithmetic works (it's an int)
print(isinstance(IPerm.R, int))       # True

# 3. The four boundary modes (3.11+)
class StrictP(IntFlag, boundary=STRICT):
    R = 1
    W = 2

try:
    StrictP(7)   # 0b111 — the third bit is undefined
except ValueError as e:
    print("STRICT raised:", e)

class ConformP(IntFlag, boundary=CONFORM):
    R = 1
    W = 2

print("CONFORM(7):", ConformP(7))                 # 3 — third bit dropped
print("CONFORM(7) repr:", repr(ConformP(7)))      # <ConformP.R|W: 3>
print("CONFORM(7).value:", ConformP(7).value)     # 3

class EjectP(IntFlag, boundary=EJECT):
    R = 1
    W = 2

r = EjectP(7)
print("EJECT(7):", r, "type:", type(r).__name__)   # 7, int — ejected

class KeepP(IntFlag, boundary=KEEP):
    R = 1
    W = 2

print("KEEP(7):", KeepP(7), "value:", KeepP(7).value)   # 7, 7
print("KEEP(7) repr:", repr(KeepP(7)))                  # <KeepP.R|W|4: 7>

print("Default Flag boundary:", Perm._boundary_)        # STRICT
print("Default IntFlag boundary:", IPerm._boundary_)    # KEEP
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 5–9: Declaring a `Flag`

```python
from enum import Flag, IntFlag, auto, STRICT, CONFORM, EJECT, KEEP

class Perm(Flag):
    R = auto()
    W = auto()
    X = auto()
```

`Flag` is the base class for type-safe bit-flags. Each member is a `Flag` instance — *not* an `int`. `auto()` for a `Flag` produces powers of 2 by default: the first member gets `1`, the second gets `2`, the third gets `4`, the fourth gets `8`. That is because `_generate_next_value_` (the hook `auto()` calls) on a `Flag`-derived class returns `1 << len(cls._members_in_order)` — powers of 2, not consecutive integers.

**Why powers of 2?** Because each bit is a yes/no answer. `R` is bit 0 (value 1), `W` is bit 1 (value 2), `X` is bit 2 (value 4). When you OR them together (`R | W = 3`), both bits are set. When you AND (`R & W = 0`), the empty flag is `0`. When you XOR (`R ^ W = 3`), each side's exclusive bit survives. These are exactly the operations you need for "set membership encoded as bits" — `Flag` is the class that gives you that, with named members instead of bare integers.

**Tip — `auto()` for `Flag` yields powers of 2; `auto()` for `Enum` yields consecutive integers**

The default `_generate_next_value_` is overridden on `Flag` to return `1 << len(...)`. The base `Enum` uses `len(...) + 1` (consecutive integers). So `auto()` means different things depending on the parent class. Lesson 04 covers `_generate_next_value_` in full; the takeaway here is: trust `auto()` to do the right thing for the parent class you chose.

### Lines 11–20: Bitwise operators and the empty flag

```python
print(Perm.R)                         # Perm.R
print(Perm.R | Perm.W)                # Perm.R|W
print(type(Perm.R | Perm.W))          # <flag 'Perm'>
print(Perm.R in (Perm.R | Perm.W))    # True
print(Perm.R & Perm.W)                # Perm(0)   <- empty flag
print(bool(Perm.R & Perm.W))          # False
print(Perm(0))                        # Perm(0)
print(bool(Perm(0)))                  # False
print(~Perm.R)                        # Perm.W|X
print(Perm.R ^ Perm.W)               # Perm.R|W
```

`Perm.R | Perm.W` returns a new `Perm` instance whose integer value is `3`. That new instance is *also* a singleton? — no. Combined flags are constructed on demand; they are not pre-built singletons. The `Flag` metaclass builds singletons only for the named members; combinations like `R | W` are constructed at the call site, but they compare equal to any other `Perm(3)` produced by the same call.

`Perm.R in (Perm.R | Perm.W)` is `True` because `Flag.__contains__` checks whether every bit of the left operand is set in the right operand's integer value. This is the idiomatic "does this permission set include R?" check.

`Perm.R & Perm.W` returns `Perm(0)` — the *empty flag*. The empty flag is the identity for `|` (`Perm(0) | Perm.R == Perm.R`) and the zero for `&`. The `str(Perm(0))` (and thus `print(Perm(0))`) is `Perm(0)`; the `repr(Perm(0))` is `<Perm: 0>`; and `bool(Perm(0))` is `False` — you can use it in `if` statements directly.

`~Perm.R` returns `Perm.W|X` (no spaces) — the *complement* of `R` within the defined bits. Note the qualifier: `~` operates only on defined bits. If you have a bit that is not defined in the class (say, `0b1000` in `StrictP(7)`), `~` on a defined member does not include it. That qualifier is what the boundary modes (lines 33+) negotiate.

`Perm.R ^ Perm.W` returns `Perm.R|W` (no spaces) — the *symmetric difference*. Each side's exclusive bit survives; common bits cancel.

**Why is `Perm(0)` not `None`?** Because `Perm(0)` is a real `Perm` instance — it just happens to have no bits set. Returning `None` for the empty flag would force every consumer to check `if x is None or x == 0`; returning `Perm(0)` lets you write `if x` (which is `False` for the empty flag, `True` for any non-empty flag). That single design choice is what makes bit-flag enums ergonomic.

### Lines 23–27: `Flag` vs `IntFlag`

```python
print([m for m in Perm])             # [Perm.R, Perm.W, Perm.X]
print(isinstance(Perm.R, int))       # False  <- Flag, not IntFlag
```

Iterating a `Flag` walks `__members__` and yields the named singletons — `Perm.R`, `Perm.W`, `Perm.X`. It does *not* yield `Perm(0)` (the empty flag) or `Perm(3)` (combined flags). Those are not members; they are constructed values.

`isinstance(Perm.R, int)` is `False`. That is the defining difference between `Flag` and `IntFlag`: `Flag` members are *not* integers, they are pure `Flag` instances. This means `Perm.R == 1` is `False`, `int(Perm.R)` is `TypeError`, and `[1, 2, 4].count(Perm.R)` is `0`. `Flag` is type-safe; the cost is that you cannot pass a `Flag` member where an `int` is expected without an explicit cast.

**Warning — `Flag` members do not coerce to `int`**

```python
int(Perm.R)   # TypeError: int() argument must be a string, a bytes-like object or a number, not 'Perm'
```

If you need the integer value, use `Perm.R.value` explicitly. If you need the member to behave as an integer everywhere, use `IntFlag` instead.

### Lines 29–36: `IntFlag` — int-compatible bit-flags

```python
class IPerm(IntFlag):
    R = 4
    W = 2
    X = 1

print(IPerm.R | IPerm.W)              # 6   <- str() inherits from int
print(repr(IPerm.R | IPerm.W))        # <IPerm.R|W: 6>
print(int(IPerm.R | IPerm.W))         # 6
print(IPerm.R | IPerm.W == 6)         # True
print(IPerm.R + 5)                    # 9   <- arithmetic works (it's an int)
print(isinstance(IPerm.R, int))       # True
```

`IntFlag` is `int + Flag`. Each member is *also* an `int`, which means it compares equal to integers, can be passed anywhere an `int` is expected, supports arithmetic operators, and serialises as its integer value without any custom encoder. The MRO is `(IPerm, IntFlag, int, ReprEnum, Flag, Enum, object)` — `int` is in the chain.

`print(IPerm.R | IPerm.W)` outputs `6` — not `IPerm.R|W`. The reason is that `IntFlag.__str__` inherits from `int`, so `str(IPerm.R | IPerm.W)` is `"6"`. The named-member form is the *`repr`*: `repr(IPerm.R | IPerm.W)` is `<IPerm.R|W: 6>`. Use `repr()` when you need a human-readable named output of an `IntFlag`; use `str()` (the default for `print`) when you need the wire value. `int(IPerm.R | IPerm.W)` is `6`, and `IPerm.R | IPerm.W == 6` is `True` because `int.__eq__` is value-based. `IPerm.R + 5` is `9` because `int.__add__` works — but note this returns a plain `int`, not an `IPerm` instance. Arithmetic on an `IntFlag` returns an `int` (Python's `int` arithmetic always returns `int`, never a subclass). The trade-off: arithmetic works, but the result is not an `IntFlag` anymore.

**Note — The default `_boundary_` differs for `Flag` vs `IntFlag`**

```python
print(Perm._boundary_)      # STRICT
print(IPerm._boundary_)     # KEEP
```

The default boundary on `Flag` is `STRICT` — out-of-range bits raise `ValueError`. The default on `IntFlag` is `KEEP` — out-of-range bits are kept as the integer value, because `IntFlag` members are passed through database columns and serialised to JSON, and the contract is "preserve the integer even if you do not understand it." `Flag` is type-safe (strict); `IntFlag` is wire-compat (lenient).

### Lines 38–63: The four boundary modes

```python
class StrictP(IntFlag, boundary=STRICT):
    R = 1
    W = 2

try:
    StrictP(7)   # 0b111 — the third bit is undefined
except ValueError as e:
    print("STRICT raised:", e)
```

`STRICT` is the strictest mode. The defined bits are `0b011` (`R | W`). The value `7` (`0b111`) has the third bit set, which is not defined in `StrictP`. `STRICT` raises `ValueError` with a message like `<flag 'StrictP'> invalid value 7 given 0b0 111 allowed 0b0 011`. Use `STRICT` when an out-of-range bit means a programming error — the database should never have written it, and you want to fail loudly on read.

```python
class ConformP(IntFlag, boundary=CONFORM):
    R = 1
    W = 2

print("CONFORM(7):", ConformP(7))                 # 3 — third bit dropped
print("CONFORM(7) repr:", repr(ConformP(7)))      # <ConformP.R|W: 3>
print("CONFORM(7).value:", ConformP(7).value)     # 3
```

`CONFORM` strips the out-of-range bits. `ConformP(7)` returns a `ConformP` member whose `.value == 3` — the third bit (value 4) is silently dropped. `str(ConformP(7))` is `"3"` (because `IntFlag.__str__` inherits from `int`); `repr(ConformP(7))` is `<ConformP.R|W: 3>` (the named-member form). Use `CONFORM` when you want "show me what I understand, ignore the rest" — for example, when reading a legacy database that may have bits you don't recognise yet, but you do not want to crash.

```python
class EjectP(IntFlag, boundary=EJECT):
    R = 1
    W = 2

r = EjectP(7)
print("EJECT(7):", r, "type:", type(r).__name__)   # 7, int — ejected
```

`EJECT` returns a plain `int` when out-of-range bits are present. `EjectP(7)` returns the integer `7` — not a `EjectP` instance. Use `EJECT` when out-of-range values should be treated as raw integers (e.g., passed through to a downstream system that does its own bit decoding). Note that `EJECT` is not the same as `KEEP`: `KEEP` returns an `IntFlag` instance with the full integer value; `EJECT` returns a plain `int`.

```python
class KeepP(IntFlag, boundary=KEEP):
    R = 1
    W = 2

print("KEEP(7):", KeepP(7), "value:", KeepP(7).value)   # 7, 7
print("KEEP(7) repr:", repr(KeepP(7)))                  # <KeepP.R|W|4: 7>
```

`KEEP` returns an `IntFlag` instance whose integer value preserves the out-of-range bits. `KeepP(7)` is a `KeepP` member with `.value == 7`. `str(KeepP(7))` is `"7"` (IntFlag inherits `__str__` from `int`); `repr(KeepP(7))` is `<KeepP.R|W|4: 7>` — the named bits plus the raw `4` for the out-of-range bit. The unknown bits are carried through transparently. This is the default for `IntFlag` because it is the most wire-compat: a database that stores `7` reads back as `7`, and writing it back preserves the value.

**Why four modes instead of one?** Because "what to do with out-of-range bits" is a domain question, not a language question. A banking system wants `STRICT` (fail loudly on read; out-of-range bits mean fraud or corruption). A logger wants `CONFORM` (best-effort decode, never crash on log lines). A migration tool wants `EJECT` (preserve the raw value for downstream code). A general-purpose library wants `KEEP` (preserves the value but lets the consumer reason about it as an enum). The four modes cover the four real engineering answers; the language cannot pick one for you.

**Danger — The default boundary can break production on a database schema change**

If your `IntFlag` uses the default `KEEP` (the default for `IntFlag`) and a database column has bits you don't define yet, reads will succeed but writes will store the *full* integer — including bits you don't model in your code. When a later developer adds a member for that bit, the data suddenly decodes as something it wasn't before. The fix: when you add a new member to an existing `IntFlag` that backs a database column, audit the column for already-set bits that will decode to the new member unexpectedly.

## Execution Trace

```bash
$ python boardly/permissions.py
Perm.R
Perm.R|W
<flag 'Perm'>
True
Perm(0)
False
Perm(0)
False
Perm.W|X
Perm.R|W
[<Perm.R: 1>, <Perm.W: 2>, <Perm.X: 4>]
False
6
<IPerm.R|W: 6>
6
True
9
True
STRICT raised: <flag 'StrictP'> invalid value 7
    given 0b0 111
  allowed 0b0 011
CONFORM(7): 3
CONFORM(7) repr: <ConformP.R|W: 3>
CONFORM(7).value: 3
EJECT(7): 7 type: int
KEEP(7): 7 value: 7
KEEP(7) repr: <KeepP.R|W|4: 7>
Default Flag boundary: strict
Default IntFlag boundary: keep
```

## Common Mistakes

### Mistake 1: Using `Flag` where you need `IntFlag`

```python
class Perm(Flag):        # not IntFlag
    R = 4
    W = 2

int(Perm.R | Perm.W)    # TypeError
```

**Symptom:** `TypeError: int() argument must be a string, a bytes-like object or a number, not 'Perm'` from a JSON serialiser or a database column write.
**Why:** `Flag` members are not `int`s. `int(x)` on a `Flag` member raises. You need to use `x.value` explicitly, or change the parent to `IntFlag`.
**Fix:** If the value crosses a serialisation boundary (database, JSON, HTTP), use `IntFlag`. If it is internal-only and you want type safety, use `Flag` and access `.value` explicitly.

### Mistake 2: Forgetting the default boundary is `STRICT` for `Flag`

```python
class StrictPerm(Flag):       # boundary defaults to STRICT
    R = auto()
    W = auto()

StrictPerm(7)   # ValueError — the third bit is undefined
```

**Symptom:** `ValueError` from a read of a value that has bits beyond the defined set.
**Why:** The default boundary for `Flag` is `STRICT`, which raises on any out-of-range bit. `IntFlag` defaults to `KEEP`, which is why this bug surfaces specifically when migrating from `IntFlag` to `Flag` for type safety.
**Fix:** Pick a boundary explicitly. `Flag` with `boundary=CONFORM` is the typical "I want type safety but I also want resilience to legacy data" choice. `Flag` with `boundary=STRICT` is "I want to know the moment my data is corrupt."

### Mistake 3: Treating `IntFlag` arithmetic results as `IntFlag` instances

```python
class P(IntFlag): R = 1; W = 2
result = P.R + P.W
isinstance(result, P)    # False — it's a plain int
```

**Symptom:** Code that expects the result of `+`/`-`/`*` on `IntFlag` members to be `IntFlag` instances fails. The result is a plain `int`.
**Why:** Python's `int.__add__` returns `int`, never a subclass. Arithmetic on `IntFlag` members goes through `int.__add__`, and the result is downgraded to `int`. The same is true for `IntEnum`.
**Fix:** Wrap the result: `P(result)`. Or avoid arithmetic on flag members entirely — flags are set-membership, not arithmetic.

## Engineering Trade-Offs

**Decision:** Use `IntFlag` for bit-flags that cross a serialisation boundary (database columns, JSON values, environment variables). Use `Flag` (with `boundary=CONFORM`) for internal-only bit-flags that benefit from type safety but must tolerate legacy data.
**Both sides:** `Flag` is type-safe (`isinstance(x, int)` is `False`); `IntFlag` is wire-compatible (it is an `int`). The trade-off is between "the type system catches mistakes" and "the wire format accepts the member without conversion." `Flag` is the safer default for new code; `IntFlag` is the only choice when the value has to live in an `int`-typed column.
**Commitment:** `boardly` uses `IntFlag` with `boundary=CONFORM` for the `PermFlag` column (stored as `int` in PostgreSQL, decoded to `PermFlag` on read, strict on writes but lenient on reads to tolerate legacy rows that predate the current member set).

## Exercises

1. **Exercise 1 — Add a permission.** Add `D = auto()` to `Perm`. Re-run. Confirm `Perm.R | Perm.D` works and `Perm.D.value` is `8`. `Verify: python -c "from boardly.permissions import Perm; print(Perm.D.value)"`
2. **Exercise 2 — Boundary test.** Construct an `IntFlag` with `boundary=STRICT` and a defined bit `1`. Try to read `7` (out-of-range). Confirm `ValueError`. Try the same with `boundary=KEEP`. Confirm the value survives. `Verify: python -c "from enum import IntFlag, KEEP; class P(IntFlag, boundary=KEEP):\n R=1\nprint(P(7).value)"`
3. **Exercise 3 — Empty flag semantics.** Write `if not (Perm.R & Perm.W): print("no overlap")`. Confirm the empty flag is falsy. `Verify: python -c "from boardly.permissions import Perm; print('no overlap' if not (Perm.R & Perm.W) else 'overlap')"`
4. **Exercise 4 — The complement gotcha.** Compute `~Perm.R` and print the result. Explain (in a comment) why the complement is `Perm.W|X`, not "all bits except R". `Verify: python -c "from boardly.permissions import Perm; print(~Perm.R)"`
5. **Exercise 5 — Boundary mode summary table.** Write a markdown table summarising the four modes: which raises, which strips, which ejects, which keeps. Commit it next to `boardly/permissions.py` as a comment block. `Verify: python -c "import boardly.permissions as p; print(p.__doc__ or 'no docstring')"`

## Verification

```bash
$ python boardly/permissions.py | head -1
Perm.R
$ python boardly/permissions.py | rg '^Default'
Default Flag boundary: strict
Default IntFlag boundary: keep
$ python -c "from boardly.permissions import Perm; print(Perm.R | Perm.W)"
Perm.R|W
```

## Previously Learned Here

- [[09-enum/01-Enum-Basics]] — the singleton guarantee, the three lookup forms. `Flag`'s members are singletons just like `Enum`'s; combined flags are constructed on demand.
- [[09-enum/02-IntEnum-and-StrEnum]] — the `int`/`str` mixin pattern. `IntFlag` is `int + Flag` — the same architectural shape as `IntEnum` is `int + Enum`.

## What's Next

[[09-enum/04-auto-and-value]] — You have now seen `auto()` three times: once for `Enum` (consecutive integers), once for `Flag` (powers of 2). Lesson 04 unpacks the `_generate_next_value_` hook that `auto()` calls, shows you how to write a custom value generator, and introduces the `@unique` decorator that closes the alias loophole from lesson 01.

- **Lesson 04** — `auto()`, `_generate_next_value_`, custom generators, `@unique`.
- **Lesson 05** — How FastAPI serialises `IntFlag` and `StrEnum` in `response_model`s, and why the boundary mode you pick matters for the OpenAPI schema.

## Sources

- **Python `enum` module documentation — `Flag` and `IntFlag`** — https://docs.python.org/3/library/enum.html#enum.Flag — accessed 2026-10-23 — the canonical reference for `Flag`, `IntFlag`, the bitwise operators, and the four boundary modes.
- **Python `enum` module documentation — `FlagBoundary`** — https://docs.python.org/3/library/enum.html#boundaries — accessed 2026-10-23 — the source-of-truth reference for `STRICT`, `CONFORM`, `EJECT`, `KEEP` and the default-boundary rules.
- **PEP 435 — Adding an Enum type to the Python standard library (Flag section)** — https://peps.python.org/pep-0435/#flag — accessed 2026-10-23 — the original 3.4 design. Read it for the "bit-flag with names" motivation and the `~` complement semantics.

## What We Learned

- You can now declare `class Perm(Flag):` and explain why `auto()` produces powers of 2.
- You can now combine members with `|`, `&`, `^`, `~`, and you know that the empty flag is `Perm(0)` and is falsy.
- You can now explain the difference between `Flag` (type-safe, not `int`) and `IntFlag` (wire-compatible, is `int`).
- You can now choose between the four boundary modes (`STRICT`, `CONFORM`, `EJECT`, `KEEP`) based on what your domain wants to do with out-of-range bits.
- You can now read a combined flag's `repr` (`Perm.R|W`) and reason about which bits are set.
