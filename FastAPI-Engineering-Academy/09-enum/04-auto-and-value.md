---
title: "Lesson 04: auto and value"
aliases:
 - enum auto
 - _generate_next_value_
 - enum unique
 - enum verify
tags:
 - enum
 - python-stdlib
 - auto
 - unique
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[09-enum/01-Enum-Basics]]"
 - "[[09-enum/02-IntEnum-and-StrEnum]]"
 - "[[09-enum/03-Flag-and-IntFlag]]"
related_lessons:
 - "[[09-enum/05-Enum-in-APIs]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
---

# Lesson 04: auto and value

*How `boardly`'s `TicketStatus` stopped hard-coding `OPEN = 1, IN_PRG = 2` and let `auto()` do the bookkeeping — and how the `@unique` decorator closed the alias loophole that caused a two-day outage when two members got the same value.*

**You're at the very beginning of Section 09 — four lessons in.**

You have copy-pasted `OPEN = 1, IN_PRG = 2, BLOCKED = 3` into five different enum classes. You have also got the numbers wrong twice — `DONE = 4` and `CANCELLED = 4` collided, and the bug only surfaced in production three weeks later. `auto()` lets you stop bookkeeping. `@unique` makes the bookkeeping you did do refuse to lie. Take your time. Type every example. **This is how you learn.**

#enum #auto

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `auto()`** — write `OPEN = auto()` and explain what default value the metaclass assigns (consecutive integers for `Enum`/`IntEnum`, powers of 2 for `Flag`).
2. **Override `_generate_next_value_`** — write a custom hook that returns the member's name lowercased, or `count * 10`, or whatever your wire format demands.
3. **Use the `@unique` decorator** — apply it to an enum and explain why a duplicate value raises `ValueError` at class-creation time, not at runtime.
4. **Use the `@verify` decorator (3.11+)** — apply `@verify(UNIQUE)`, `@verify(CONTINUOUS)`, `@verify(NAMED_FLAGS)` and explain when each check is worth the import.
5. **Identify an alias** — explain that without `@unique`, the second of two duplicate-value members becomes an alias for the first, with the same identity.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[09-enum/01-Enum-Basics]] — the singleton guarantee and `__members__` (aliases live there).
- **Lesson 03** — [[09-enum/03-Flag-and-IntFlag]] — the difference between `auto()` for `Enum` (consecutive integers) and `auto()` for `Flag` (powers of 2).
- **About 30–40 minutes of focused time.**

**The most common gap: assuming `auto()` always produces consecutive integers.** It does for `Enum` and `IntEnum`. It produces powers of 2 for `Flag` and `IntFlag`. And — most importantly — it produces *whatever your custom `_generate_next_value_` returns*. The default is overridden by the class.

## The Problem

Here is the bug. `boardly` had this enum in production:

```python
class TicketStatus(StrEnum):
    OPEN    = "open"
    IN_PRG  = "in_progress"
    BLOCKED = "blocked"
    DONE    = "done"
    CLOSED  = "done"   # typo — the junior dev meant "closed"
```

`CLOSED` has the same value as `DONE`. Without `@unique`, this is not an error — it is an *alias*. `TicketStatus.CLOSED is TicketStatus.DONE` is `True`. The API route `if status == TicketStatus.CLOSED:` works for both `DONE` and `CLOSED`, which is technically fine but semantically wrong: a closed ticket and a done ticket are different things in the product. The bug is silent — until a UI engineer queries `TicketStatus.__members__` to populate a dropdown and `CLOSED` is missing from the iteration because aliases are skipped, and they file a bug.

`@unique` would have caught this at class-creation time, at import, before the bug shipped. `auto()` would have avoided it by never asking the junior dev to type the values. The two features together — `auto()` for the values, `@unique` for the safety net — are how you stop typing values into an enum entirely.

## The Code

```python
# boardly/enum_auto_demo.py
"""Demonstrates auto(), _generate_next_value_, @unique, and @verify."""
from enum import Enum, IntEnum, StrEnum, Flag, auto, unique, verify, UNIQUE, CONTINUOUS

# 1. auto() default — consecutive integers for Enum and IntEnum
class Color(Enum):
    RED   = auto()
    GREEN = auto()
    BLUE  = auto()

class Priority(IntEnum):
    LOW  = auto()
    MED  = auto()
    HIGH = auto()

print("--- plain Enum auto ---")
for c in Color:    print(f"  {c.name}: {c.value}")
print("--- IntEnum auto ---")
for p in Priority: print(f"  {p.name}: {p.value}")

# 2. Custom _generate_next_value_ — name lowercased (boardly's wire format)
class TicketStatus(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    OPEN   = auto()
    IN_PRG = auto()
    BLOCKED = auto()
    DONE   = auto()

print("--- TicketStatus auto (lowercased name) ---")
for s in TicketStatus: print(f"  {s.name}: {s.value!r}")

# 3. Static-method override — count * 10
class Code(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count * 10   # 0, 10, 20, ...

    A = auto()
    B = auto()
    C = auto()

print("--- Code auto (count * 10) ---")
for c in Code: print(f"  {c.name}: {c.value}")

# 4. The @unique decorator — refuses aliases at class-creation
try:
    @unique
    class BadStatus(StrEnum):
        OPEN   = "open"
        CLOSED = "open"   # duplicate value
except ValueError as e:
    print("--- @unique caught the duplicate ---")
    print(f"  ValueError: {e}")

# 5. WITHOUT @unique — duplicates become aliases
class WithAlias(StrEnum):
    OPEN   = "open"
    CLOSED = "open"

print("--- without @unique (alias) ---")
print(f"  OPEN is CLOSED: {WithAlias.OPEN is WithAlias.CLOSED}")   # True
print(f"  __members__ keys: {list(WithAlias.__members__)}")        # both
print(f"  list(WithAlias): {[m.name for m in WithAlias]}")         # only OPEN
print(f"  WithAlias('open'): {WithAlias('open')}")                  # open (StrEnum.__str__ returns the value)

# 6. The @verify decorator (3.11+) — multiple checks
@verify(UNIQUE, CONTINUOUS)
class GoodCodes(IntEnum):
    A = 1
    B = 2
    C = 3

print("--- @verify(UNIQUE, CONTINUOUS) passed ---")
for g in GoodCodes: print(f"  {g.name}: {g.value}")

try:
    @verify(CONTINUOUS)
    class Skipper(IntEnum):
        A = 1
        B = 3   # skips 2
except ValueError as e:
    print("--- @verify(CONTINUOUS) caught the skip ---")
    print(f"  ValueError: {e}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 5–17: `auto()` defaults

```python
class Color(Enum):
    RED   = auto()
    GREEN = auto()
    BLUE  = auto()

class Priority(IntEnum):
    LOW  = auto()
    MED  = auto()
    HIGH = auto()
```

`auto()` is a sentinel value. When the metaclass walks the class body and sees `RED = auto()`, it does not assign a literal "auto" — it calls the *class's* `_generate_next_value_` method, passing the member's name (`"RED"`), the `start` value (always `1` for plain `Enum`), the current `count` (how many members have been processed before this one), and the `last_values` list (so you can do increment-with-memory).

The default `_generate_next_value_` on `Enum` is, roughly:

```python
@staticmethod
def _generate_next_value_(name, start, count, last_values):
    return count + start
```

So for `Color.RED` (the first member), `count = 0` and the value is `0 + 1 = 1`. For `Color.GREEN`, `count = 1` and the value is `2`. For `Color.BLUE`, `count = 2` and the value is `3`. Consecutive integers starting at `start` (which is `1` for `Enum`).

For `Flag` (lesson 03), the default is overridden to `1 << count` — powers of 2. For `StrEnum`, the default is the same as `Enum` (consecutive integers), but you almost always want to override it to return `name.lower()` so the string value matches the wire format you actually want.

**Why does `auto()` exist?** Because bookkeeping is wrong 5% of the time. Typing `OPEN = 1, IN_PRG = 2, BLOCKED = 3, DONE = 4, CANCELLED = 4` (typo) is the bug that motivated `auto()`. With `auto()`, you write the *names* — the only thing that has semantic meaning — and let the metaclass pick values. The values are not part of your domain knowledge; they are just unique keys.

**Tip — `auto()` is opt-in, not all-or-nothing**

You can mix `auto()` and explicit values:

```python
class TicketStatus(StrEnum):
    OPEN    = "open"
    IN_PRG  = auto()   # uses _generate_next_value_
    BLOCKED = auto()
    DONE    = "done"
```

The metaclass calls `_generate_next_value_` for the `auto()` members and uses the explicit value for the others. Mix judiciously — a half-mixed enum is harder to read than a fully-consistent one.

### Lines 25–32: Custom `_generate_next_value_`

```python
class TicketStatus(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    OPEN   = auto()
    IN_PRG = auto()
    BLOCKED = auto()
    DONE   = auto()
```

The custom `_generate_next_value_` is a method (or static method) defined *inside the class body*. The metaclass looks for it before walking the assignments. When it sees `OPEN = auto()`, it calls `TicketStatus._generate_next_value_("OPEN", 1, 0, [])` and the return value `"open"` becomes `OPEN.value`.

The four arguments are:
- `name` — the member's name as a string (`"OPEN"`). Useful when you want the value to derive from the name.
- `start` — the starting value (always `1` for `Enum`). Useful for `Flag`-style "start at 1" semantics, but rarely needed.
- `count` — how many members have been generated before this one (starts at `0`). Useful for consecutive values or for `1 << count`.
- `last_values` — a list of every value the hook has returned so far, in order. Useful for "increment the max" patterns.

The `name.lower()` override is the canonical `StrEnum` pattern. It means you never type the string value — you write `OPEN = auto()` and the wire value becomes `"open"`, automatically. The typos that motivated `auto()` in the first place ("CLOSED = 'done'") are impossible because the value is derived from the name, not typed.

**Warning — `_generate_next_value_` runs at class-creation, not lazily**

The hook is called once per `auto()` member, *at the moment the class statement is executed*. The result is baked into the member's `.value` and never recomputed. If you change the hook later, the values do not change unless the class is re-imported. There is no lazy lookup at access time.

### Lines 38–47: Static-method override — `count * 10`

```python
class Code(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count * 10   # 0, 10, 20, ...

    A = auto()
    B = auto()
    C = auto()
```

The hook can also be a `@staticmethod`. The difference is mostly stylistic — a static method does not receive the class as the first argument, but the metaclass calls it the same way. The `count * 10` pattern is the classic "reserve space between values" technique: `A=0, B=10, C=20`, leaving room for `A1=1, A2=2` if you need to insert new members later.

**Why `count * 10` instead of `count + 1`?** Because the values are stored in a database column. If you ever need to insert a new member between two existing ones (a rare but real requirement when the enum represents an ordered scale), the `count + 1` scheme forces you to renumber every existing row. The `count * 10` scheme gives you nine free slots between each pair of members. It is the same logic that motivates the "give every test a multiplier of 10" trick in classroom grading.

### Lines 49–56: The `@unique` decorator

```python
try:
    @unique
    class BadStatus(StrEnum):
        OPEN   = "open"
        CLOSED = "open"   # duplicate value
except ValueError as e:
    print("--- @unique caught the duplicate ---")
    print(f"  ValueError: {e}")
```

`@unique` is a class decorator. It runs *after* the metaclass has built the class and *before* the class is bound to its name. It walks `__members__` and checks for duplicate values; if it finds any, it raises `ValueError: duplicate values found in <enum 'BadStatus'>: CLOSED -> OPEN`. The error message names the duplicate (CLOSED) and the original it points to (OPEN).

The `ValueError` is raised at *import time*, not at access time. The bug — `CLOSED = "open"` when you meant `CLOSED = "closed"` — is caught the moment the module is imported, not three weeks later when a UI engineer notices `CLOSED` is missing from the dropdown.

**Note — `@unique` is a *check*, not a *transform***

`@unique` does not rename or renumber anything. It just raises if there are duplicates. If you want to deduplicate, fix the source — do not rely on the decorator to fix it for you.

### Lines 58–66: Without `@unique` — aliases

```python
class WithAlias(StrEnum):
    OPEN   = "open"
    CLOSED = "open"

print("--- without @unique (alias) ---")
print(f"  OPEN is CLOSED: {WithAlias.OPEN is WithAlias.CLOSED}")   # True
print(f"  __members__ keys: {list(WithAlias.__members__)}")        # both
print(f"  list(WithAlias): {[m.name for m in WithAlias]}")         # only OPEN
print(f"  WithAlias('open'): {WithAlias('open')}")                  # open (StrEnum.__str__ returns the value)
```

Without `@unique`, the second of two duplicate-value members becomes an *alias* for the first. `WithAlias.CLOSED is WithAlias.OPEN` is `True` — they are the same object. The metaclass does not create a new singleton for `CLOSED`; it just binds `CLOSED` to the existing `OPEN` singleton.

`__members__` keys include both names (`['OPEN', 'CLOSED']`) because aliases are listed. But `list(WithAlias)` (which iterates via `__iter__`) yields only the *canonical* members — `['OPEN']`. `CLOSED` is skipped because iteration does not yield aliases. That is the gotcha: `__members__.keys()` includes aliases; `for m in cls` does not.

`WithAlias("open")` returns `WithAlias.OPEN` — the first member with that value. The alias is never returned by value lookup.

**Bug — Aliases cause silent iteration drops**

```python
for status in WithAlias:
    build_dropdown_option(status)
# dropdown only shows "OPEN" — CLOSED is missing
```

The UI engineer expected `CLOSED` to appear in the dropdown. It does not, because iteration skips aliases. The fix: either remove the alias (use `@unique` to catch the typo at import), or use `__members__.values()` if you really want to iterate every name including aliases.

### Lines 71–82: The `@verify` decorator (3.11+)

```python
@verify(UNIQUE, CONTINUOUS)
class GoodCodes(IntEnum):
    A = 1
    B = 2
    C = 3
```

`@verify` (Python 3.11+) is the generalised form of `@unique`. It takes one or more `EnumCheck` values — `UNIQUE`, `CONTINUOUS`, `NAMED_FLAGS` — and runs each check. `@verify(UNIQUE)` is equivalent to `@unique`. `@verify(UNIQUE, CONTINUOUS)` runs both checks.

`CONTINUOUS` checks that integer values are contiguous (no skips). It only makes sense for `IntEnum` and `IntFlag` — `StrEnum` values are strings, so "contiguous" is meaningless. Use `CONTINUOUS` when your integer values are stored in a DB column and you want every integer from `min` to `max` to map to a member — a skip means a value the DB could store that has no enum member, which is a data-integrity bug.

`NAMED_FLAGS` checks that every flag combination has a defined name. Use it for `Flag`/`IntFlag` classes where you want every combination of bits to decode to a named member — without it, `Flag.R | Flag.W` is a "combined flag" with no `.name` of its own (it gets a synthesised `"R|W"` string instead of a true name).

**Why `@verify` instead of `@unique`?** Because `@unique` only checks one thing. `@verify` lets you stack checks. For a `boardly` enum that backs a DB column and needs every combination named, you write `@verify(UNIQUE, CONTINUOUS, NAMED_FLAGS)` and you get all three guarantees at import time.

## Execution Trace

```bash
$ python boardly/enum_auto_demo.py
--- plain Enum auto ---
  RED: 1
  GREEN: 2
  BLUE: 3
--- IntEnum auto ---
  LOW: 1
  MED: 2
  HIGH: 3
--- TicketStatus auto (lowercased name) ---
  OPEN: 'open'
  IN_PRG: 'in_prg'
  BLOCKED: 'blocked'
  DONE: 'done'
--- Code auto (count * 10) ---
  A: 0
  B: 10
  C: 20
--- @unique caught the duplicate ---
  ValueError: duplicate values found in <enum 'BadStatus'>: CLOSED -> OPEN
--- without @unique (alias) ---
  OPEN is CLOSED: True
  __members__ keys: ['OPEN', 'CLOSED']
  list(WithAlias): ['OPEN']
  WithAlias('open'): open
--- @verify(UNIQUE, CONTINUOUS) passed ---
  A: 1
  B: 2
  C: 3
--- @verify(CONTINUOUS) caught the skip ---
  ValueError: invalid enum 'Skipper': missing values 2
```

## Common Mistakes

### Mistake 1: Defining `_generate_next_value_` after the members

```python
class Bad(Enum):
    A = auto()
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()
```

**Symptom:** The hook is never called; `Bad.A.value` is `1` (the default), not `"a"`.
**Why:** The metaclass reads the class body in order. By the time it sees `A = auto()`, the hook has not been defined yet. The metaclass falls back to `Enum._generate_next_value_` (the default, returning `count + start`).
**Fix:** Define the hook *before* the first `auto()` call. Convention: put it at the top of the class body, before any members.

### Mistake 2: Forgetting `@unique` on a wire-serialised enum

```python
class TicketStatus(StrEnum):    # no @unique
    OPEN = "open"
    DONE = "done"
    CLOSED = "done"   # typo
```

**Symptom:** Production silent-bug — `CLOSED` is an alias for `DONE`, iteration skips `CLOSED`, the dropdown UI shows three statuses instead of four.
**Why:** Without `@unique`, duplicate values become aliases. The class does not raise; the bug ships.
**Fix:** Always use `@unique` (or `@verify(UNIQUE, ...)`) on enums that cross a serialisation boundary. The decorator costs nothing at runtime and catches the typo at import.

### Mistake 3: Assuming `auto()` produces consecutive integers on `Flag`

```python
class Perm(Flag):
    R = auto()    # value 1
    W = auto()    # value 2 — same bit-set as R|W, but you wanted bit 1
    X = auto()    # value 3 — out of range for bit-flags
```

**Symptom:** Bit-flag operations produce nonsense — `R | W == 3`, but `R & W == 0` only because bit 1 and bit 2 are different bits. The intent was three separate bits, but the values are 1, 2, 3 (one bit, two bits, two bits). `Perm.X` has value 3, which means "bits 0 and 1 set" — the same as `Perm.R | Perm.W`.
**Why:** The default `_generate_next_value_` for `Flag` is `1 << count` (powers of 2), not `count + 1`. But — and this is the bug — students sometimes override it back to `count + 1`, breaking the bit-flag semantics.
**Fix:** Trust the default for `Flag`. Do not override `_generate_next_value_` unless you understand bit arithmetic. If you need consecutive integers, you do not want a `Flag` — you want an `IntEnum`.

## Engineering Trade-Offs

**Decision:** Use `auto()` for the values; use `@unique` (or `@verify(UNIQUE, CONTINUOUS)` for DB-backed enums) as the safety net; override `_generate_next_value_` only when the wire format derives from the name (the `StrEnum` `name.lower()` pattern).
**Both sides:** The alternative is explicit values (`OPEN = 1, IN_PRG = 2`). Explicit values are easier to read at first glance — you see the integer you will get — but they are the source of the duplicate-value bug. `auto()` shifts the cognitive load from "type the right number" to "trust the hook to do the right thing", which is the right trade for any enum with more than three members.
**Commitment:** `boardly` uses `auto()` with the `_generate_next_value_` returning `name.lower()` for every `StrEnum`. `@unique` is mandatory on every wire-serialised enum; `@verify(UNIQUE, CONTINUOUS)` is mandatory on every `IntEnum` that backs a DB column. The convention is documented in `boardly/enums.py`.

## Exercises

1. **Exercise 1 — Verify auto defaults.** Define `class C(Enum): A=auto(); B=auto()` and confirm `C.A.value == 1` and `C.B.value == 2`. `Verify: python -c "from enum import Enum, auto; class C(Enum):\n A=auto()\n B=auto()\nprint(C.A.value, C.B.value)"`
2. **Exercise 2 — Override `_generate_next_value_`.** Add the `name.lower()` hook to a `StrEnum` and confirm `OPEN.value == "open"` without you typing the string. `Verify: python -c "from enum import StrEnum, auto; class S(StrEnum):\n def _generate_next_value_(n,s,c,l):\n  return n.lower()\n A=auto()\nprint(S.A.value)"`
3. **Exercise 3 — Trigger `@unique`.** Try to declare `@unique class Bad(StrEnum): A='x'; B='x'` and confirm the `ValueError` is raised. `Verify: python -c "from enum import StrEnum, unique; \n@unique\nclass B(StrEnum):\n A='x'\n B='x'" 2>&1 | tail -1`
4. **Exercise 4 — Stack `@verify` checks.** Write `@verify(UNIQUE, CONTINUOUS)` on a 4-member `IntEnum` with values 1, 2, 4, 5 (skipping 3). Confirm the `ValueError` mentions the missing 3. `Verify: python -c "from enum import IntEnum, verify, CONTINUOUS; \n@verify(CONTINUOUS)\nclass C(IntEnum):\n A=1\n B=2\n C=4\n D=5" 2>&1 | tail -1`
5. **Exercise 5 — Build a custom generator that reserves space.** Write `_generate_next_value_` that returns `count * 100` (so values are 0, 100, 200, ...). Define a 5-member enum this way. Document in a comment why you would want this for a DB-backed scale. `Verify: python -c "from enum import Enum, auto; class S(Enum):\n @staticmethod\n def _gnv(n,s,c,l):\n  return c*100\n A=auto();B=auto();C=auto();D=auto();E=auto()\nprint([m.value for m in S])"`

## Verification

```bash
$ python boardly/enum_auto_demo.py | head -3
--- plain Enum auto ---
  RED: 1
  GREEN: 2
$ python boardly/enum_auto_demo.py | rg 'duplicate'
  ValueError: duplicate values found in <enum 'BadStatus'>: CLOSED -> OPEN
$ python -c "from boardly.enum_auto_demo import TicketStatus; print(TicketStatus.OPEN.value)"
open
```

## Previously Learned Here

- [[09-enum/01-Enum-Basics]] — the singleton guarantee; aliases share identity with their canonical member.
- [[09-enum/02-IntEnum-and-StrEnum]] — `StrEnum`'s wire-format requirements, which `auto()` with `_generate_next_value_` solves neatly.
- [[09-enum/03-Flag-and-IntFlag]] — `auto()` for `Flag` produces powers of 2 by default; do not override unless you understand bit arithmetic.

## What's Next

[[09-enum/05-Enum-in-APIs]] — Now you have `StrEnum` with `auto()`-generated `name.lower()` values, `@unique` to catch the typos, and `@verify(UNIQUE, CONTINUOUS)` for DB-backed enums. The last lesson in this section shows you what FastAPI does when it sees a `StrEnum` on a `response_model` — how it serialises, how it builds the OpenAPI `enum` keyword, and what the `Literal[...]` alternative looks like.

- **Lesson 05** — FastAPI + `StrEnum`: the serialisation contract, the OpenAPI schema, `Literal` vs `Enum`.
- **Section 10 — `inspect`** — How FastAPI reads your `StrEnum` from the `Annotated[TicketStatus, ...]` annotation in the dependency signature.

## Sources

- **Python `enum` module documentation — `auto`** — https://docs.python.org/3/library/enum.html#enum.auto — accessed 2026-10-23 — the canonical reference for `auto()` and the `_generate_next_value_` hook signature.
- **Python `enum` module documentation — `unique` and `verify`** — https://docs.python.org/3/library/enum.html#enum.unique — accessed 2026-10-23 — the canonical reference for the `@unique` decorator and the 3.11+ `@verify` generalisation.
- **PEP 435 — `auto()` and `unique`** — https://peps.python.org/pep-0435/#using-automatic-values — accessed 2026-10-23 — the original motivation for `auto()` (avoid the bookkeeping bug) and `unique` (catch the duplicate-value bug at import).

## What We Learned

- You can now use `auto()` and explain what default value the metaclass assigns for each parent class.
- You can now write a custom `_generate_next_value_` hook that derives values from names, counts, or previous values.
- You can now apply `@unique` and explain why aliases are the failure mode it prevents.
- You can now stack `@verify(UNIQUE, CONTINUOUS, NAMED_FLAGS)` checks for stricter guarantees on DB-backed enums.
- You can now identify an alias at runtime — `OPEN is CLOSED` returns `True`, iteration skips aliases, value lookup returns the canonical member.
