---
title: "Lesson 02: IntEnum and StrEnum"
aliases:
 - IntEnum
 - StrEnum
 - str enum
tags:
 - enum
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[09-enum/01-Enum-Basics]]"
related_lessons:
 - "[[09-enum/01-Enum-Basics]]"
 - "[[09-enum/05-Enum-in-APIs]]"
first_taught_in: "09-enum/02-IntEnum-and-StrEnum"
---

# Lesson 02: IntEnum and StrEnum

*How `boardly` learned that `class TicketStatus(str, Enum): OPEN = "open"` printed `TicketStatus.OPEN` when you called `str()`, how that broke the JSON serialiser, and how Python 3.11's `StrEnum` fixed it for good.*

**You're at the very beginning of Section 09 — two lessons in.**

In the last lesson you learned that `TicketStatus.OPEN == 1` returns `False`. That was a feature: an `Enum` is not its value. Today you will meet the two exceptions to that rule — `IntEnum` (which *is* an `int`) and `StrEnum` (which *is* a `str`) — and the 3.11 surprise that made the second one necessary. Take your time. Type every example. **This is how you learn.**

#enum #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare `IntEnum`** — write `class Priority(IntEnum): LOW = 1` and explain why `Priority.LOW == 1` returns `True` while the base `Enum` returned `False`.
2. **Declare `StrEnum`** — write `class TicketStatus(StrEnum): OPEN = "open"` (Python 3.11+) and explain why `str(TicketStatus.OPEN)` returns `"open"` instead of `"TicketStatus.OPEN"`.
3. **Identify the str-mixin trap** — write the pre-3.11 `class TicketStatus(str, Enum): OPEN = "open"` pattern, observe `str()` returns `"TicketStatus.OPEN"`, and explain why this broke JSON serialisers and motivated PEP 663.
4. **Name the metaclass** — explain that `enum.EnumType` is the metaclass for `IntEnum` and `StrEnum` too, and that the str/int behaviour is implemented by class mixins, not by separate metaclasses.
5. **Choose between the three** — given a use case (API serialisation, bit-flags, internal constants), pick `Enum`, `IntEnum`, or `StrEnum` and justify the choice.

## Prerequisites

Before starting, you need:

- **Lesson 01 of this section** — [[09-enum/01-Enum-Basics]] — you need the singleton guarantee and the three lookup forms in your fingers before this lesson makes sense.
- **About 35–45 minutes of focused time.**

**The most common gap: assuming `str(MyEnum.X)` returns `MyEnum.X.value`.** Students arrive expecting "of course `str()` gives me the string I assigned". For base `Enum`, it does not — it gives you the `repr`-shaped `"MyEnum.X"`. For `StrEnum` (3.11+) it does give you the value. For the old `str, Enum` mixin pattern it gave you `"MyEnum.X"` — and that surprise is what motivated PEP 663 and the introduction of `StrEnum` in 3.11.

## The Problem

Here is the production bug. `boardly` ships this enum, used in a FastAPI `response_model`:

```python
# boardly/enums.py — pre-3.11 code that "worked" until it didn't
from enum import Enum

class TicketStatus(str, Enum):     # the old str-mixin pattern
    OPEN = "open"
    DONE = "done"
```

A FastAPI route returns `{"status": TicketStatus.OPEN}`. The Pydantic serialiser, seeing that `TicketStatus.OPEN` is a `str` (because the mixin makes it a `str`), calls `str(TicketStatus.OPEN)` to get the JSON value. Pre-3.11, that returns the string `"TicketStatus.OPEN"`. The JSON response ships `{"status": "TicketStatus.OPEN"}` — not `"open"`. Every client breaks.

The bug is not in FastAPI, and not in Pydantic, and not in your code. The bug is that `str(TicketStatus.OPEN)` does not return `TicketStatus.OPEN.value` for the `str, Enum` mixin. It returns the `Enum.__str__` output, which is `"TicketStatus.OPEN"` — the class-qualified name. That surprise is what PEP 663 (Python 3.11) addressed by introducing `StrEnum`, whose `__str__` returns the underlying string value.

`IntEnum` has the same architectural shape — it is `int + Enum`, and `int(IntEnum.X)` returns the integer — but it never had the same surprise because nobody expected `str()` on an `IntEnum` to give anything specific. The surprise was always about the string side.

## The Code

```python
# boardly/enums.py
"""boardly's canonical enums — IntEnum and StrEnum flavours."""
from enum import Enum, IntEnum, StrEnum, EnumType

# 1. IntEnum — int + Enum
class Priority(IntEnum):
    LOW  = 1
    MED  = 2
    HIGH = 3

print(Priority.LOW)                  # 1   (IntEnum.__str__ inherits from int)
print(Priority.LOW == 1)             # True  (IntEnum behaves as int)
print(isinstance(Priority.LOW, int)) # True
print(int(Priority.LOW))             # 1
print([1, 2, 3].count(Priority.LOW)) # 1   — works in int contexts

# 2. StrEnum — str + Enum (3.11+)
class TicketStatus(StrEnum):
    OPEN    = "open"
    IN_PRG  = "in_progress"
    BLOCKED = "blocked"
    DONE    = "done"

print(TicketStatus.OPEN)             # open   (StrEnum.__str__ returns the value)
print(str(TicketStatus.OPEN))        # open   <- the 3.11 fix
print(TicketStatus.OPEN == "open")   # True
print(isinstance(TicketStatus.OPEN, str))  # True
print("{}".format(TicketStatus.OPEN))# open

# 3. The OLD str-mixin pattern — pre-3.11 code
class OldTicketStatus(str, Enum):
    OPEN = "open"

print(str(OldTicketStatus.OPEN))     # OldTicketStatus.OPEN  <- the bug
print(OldTicketStatus.OPEN == "open")# True  (it's still a str, but str() lies)

# 4. The metaclass is shared — StrEnum and IntEnum both use EnumType
print(type(TicketStatus))            # <class 'enum.EnumType'>
print(type(Priority))               # <class 'enum.EnumType'>
print(type(OldTicketStatus))         # <class 'enum.EnumType'>
print(Priority.__mro__)              # (<enum 'Priority'>, <enum 'IntEnum'>, <class 'int'>, <enum 'ReprEnum'>, <enum 'Enum'>, <class 'object'>)
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 5–8: Declaring `IntEnum`

```python
class Priority(IntEnum):
    LOW  = 1
    MED  = 2
    HIGH = 3
```

`IntEnum` is a subclass of both `int` and `Enum` — see the MRO printout at the end of the script: `(<enum 'Priority'>, <enum 'IntEnum'>, <class 'int'>, <enum 'ReprEnum'>, <enum 'Enum'>, <class 'object'>)`. (Python 3.12 inserts `ReprEnum` between `int` and `Enum` to centralise the `__repr__` behaviour that `IntEnum` and `StrEnum` share.) That dual inheritance is the entire point: every `Priority` member is *also* an `int`, which means it compares equal to integers, can be passed anywhere an `int` is expected, and serialises to JSON as its integer value without any custom encoder.

The metaclass is still `EnumType` — `IntEnum` does not have its own metaclass. The "behaves like an int" behaviour comes from the `int` in the MRO, not from a special metaclass. `EnumType.__new__` calls `int.__new__` when it sees `int` in the bases, so each member is *constructed* as an `int` from the ground up. That is why `int(Priority.LOW)` is `1` without any `__int__` override.

**Why does `IntEnum` exist as a separate class at all?** Three reasons. First, the MRO order matters: `IntEnum` puts `int` *before* `Enum` so that `__str__` and `__format__` come from `int` (returning the value), not from `Enum` (returning the qualified name). Second, `IntEnum` members are *interoperable* — `Priority.LOW == 1` is `True`, and two `IntEnum`s from different classes with the same value compare equal. Third, `IntEnum` is the ancestor of `IntFlag` (lesson 03), and the bit-flag operations need integer arithmetic.

**Danger — `IntEnum` is the loophole in the type-safety contract**

```python
class Priority(IntEnum): LOW = 1
class Status(IntEnum):   OPEN = 1
Priority.LOW == Status.OPEN   # True — different enums, same value
```

That equality is *by design* for `IntEnum` — it is the price of being an `int`. If you need strict type isolation (where `Priority.LOW == Status.OPEN` returns `False`), use plain `Enum` instead. The boardly rule: `IntEnum` is for integers that cross serialisation boundaries (DB columns, JSON, environment variables); plain `Enum` is for closed-set constants that should never be confused with anything else.

### Lines 10–15: `IntEnum` behaves as `int`

```python
print(Priority.LOW)                  # 1   (IntEnum.__str__ inherits from int)
print(Priority.LOW == 1)             # True  (IntEnum behaves as int)
print(isinstance(Priority.LOW, int)) # True
print(int(Priority.LOW))             # 1
print([1, 2, 3].count(Priority.LOW)) # 1   — works in int contexts
```

`Priority.LOW == 1` returns `True` because `IntEnum.__eq__` falls through to `int.__eq__` — the member really is an `int` underneath, and integer equality is value-based. (Plain `Enum` returns `NotImplemented` for `member == int`, which falls back to identity and gives `False`. The `IntEnum` mixin reverses that — the `int` MRO wins.)

`isinstance(Priority.LOW, int)` is `True` because the member's type hierarchy goes through `int`. `int(Priority.LOW)` returns `1` via `int.__int__`, which is inherited unchanged. The last line — `[1, 2, 3].count(Priority.LOW)` returns `1` — is the proof that the member behaves as an `int` in third-party code that has no idea what an `Enum` is. That is the value of `IntEnum`: legacy interfaces that take `int` accept your enum without adaptation.

**Tip — Use `IntEnum` when the value is the contract**

When the wire format is an integer (a database column, a JSON number, an HTTP status code), reach for `IntEnum`. When the wire format is a string, reach for `StrEnum`. When there is no wire format — internal constants only — reach for plain `Enum` and enjoy the strict type isolation. The choice is not aesthetic; it is dictated by the serialisation surface.

### Lines 17–24: `StrEnum` — the 3.11 fix

```python
class TicketStatus(StrEnum):
    OPEN    = "open"
    IN_PRG  = "in_progress"
    BLOCKED = "blocked"
    DONE    = "done"

print(TicketStatus.OPEN)             # open   (StrEnum.__str__ returns the value)
print(str(TicketStatus.OPEN))        # open   <- the 3.11 fix
print(TicketStatus.OPEN == "open")   # True
print(isinstance(TicketStatus.OPEN, str))  # True
print("{}".format(TicketStatus.OPEN))# open
```

`StrEnum` (Python 3.11+) inherits from `str` *and* `ReprEnum` (the 3.12 class that centralises the `<ClassName.MEMBER: VALUE>` repr for both `IntEnum` and `StrEnum`). The critical difference from the pre-3.11 `str, Enum` mixin is the *resolution* of `__str__`:

- `class Old(str, Enum):` — MRO is `Old → str → Enum → object`. You might expect `__str__` to resolve to `str.__str__`, but the `EnumType` metaclass sets `__str__ = Enum.__str__` on the class at creation time, so `str(Old.OPEN)` returns `"Old.OPEN"` (the qualified name).
- `class S(StrEnum):` — `StrEnum` itself is declared as `class StrEnum(str, ReprEnum):` (no explicit `__str__`). The `EnumType` metaclass, seeing a `str` mixin, sets `__str__ = str.__str__` on the class. So `str(S.OPEN)` returns `"open"` (the value).

That metaclass `__str__` setting is the whole fix. By routing `__str__` to the underlying primitive's `__str__`, every serialiser that calls `str()` — Pydantic, `json.dumps`, `f"{x}"`, `logger.info("%s", x)` — gets `"open"` instead of `"TicketStatus.OPEN"`. The 3.11 PEP 663 motivation was specifically this serialisation surprise.

`str(TicketStatus.OPEN)` returns `"open"`. `TicketStatus.OPEN == "open"` returns `True` (via `str.__eq__`). `isinstance(TicketStatus.OPEN, str)` returns `True`. The member is a `str` through and through — the metaclass-set `__str__ = str.__str__` is what changes the `str(member)` output from the base `str, Enum` pattern's qualified name to the value.

**Why does `StrEnum` exist as a separate class instead of just fixing `str, Enum`?** Because the maintainers could not change the behaviour of `str, Enum` without breaking everyone's existing code. Millions of lines of Python use `class X(str, Enum):` and depend on `str(X.Y)` returning `"X.Y"`. PEP 663 proposed deprecating that behaviour; community pushback killed the deprecation. The compromise was a new class — `StrEnum` — with the *new* behaviour, leaving the old `str, Enum` pattern untouched. You should use `StrEnum` for all new code. Reserve `str, Enum` for the corner of your codebase that genuinely needs the old behaviour (and add a comment explaining why).

**Warning — `StrEnum` requires Python 3.11+**

If your project supports 3.10 or earlier, `StrEnum` is not in `enum`. Either bump the minimum to 3.11, or `pip install typing_extensions` and use `typing_extensions.StrEnum` (a backport for 3.7–3.10). The boardly project targets 3.12, so this is not a concern.

### Lines 26–31: The old str-mixin pattern — the bug

```python
class OldTicketStatus(str, Enum):
    OPEN = "open"

print(str(OldTicketStatus.OPEN))     # OldTicketStatus.OPEN  <- the bug
print(OldTicketStatus.OPEN == "open")# True  (it's still a str, but str() lies)
```

The pre-3.11 way to make a string enum was the `str, Enum` mixin pattern. It works — `OldTicketStatus.OPEN` is a `str` and compares equal to `"open"` — but `str()` lies. The MRO is `(<enum 'OldTicketStatus'>, <class 'str'>, <class 'Enum'>, <class 'object'>`, so you would expect `str.__str__` (which returns the value) to win. It does not. The `EnumType` metaclass sets `__str__ = Enum.__str__` on the class at creation time, overriding what MRO resolution would pick. `Enum.__str__` returns the qualified name `"OldTicketStatus.OPEN"`, and the `str` methods below `Enum` in the MRO never get a chance to run.

The two-line comparison above is the entire 3.11 motivation in miniature:

- `OldTicketStatus.OPEN == "open"` is `True` (the member *is* `"open"`).
- `str(OldTicketStatus.OPEN)` returns `"OldTicketStatus.OPEN"` (the *string* of the member is its class-qualified name).

A JSON serialiser that does `str(x)` to get the JSON value gets the wrong answer. A logger that does `"%s" % x` gets the wrong answer. An f-string `"{}".format(x)` gets the wrong answer. Every code path that touches the string representation breaks, and the breakage is silent — no exception, just a wrong value in production.

**Bug — `str()` is the serialiser's interface, and `str, Enum` lies through it**

```python
import json
json.dumps({"status": OldTicketStatus.OPEN})
# '{"status": "OldTicketStatus.OPEN"}'   <- the bug, serialised to clients
```

That is the bug. `StrEnum` fixes it by overriding `__str__` to return the value. There is no fix for the old `str, Enum` pattern short of overriding `__str__` yourself — and if you are going to override it, you may as well use `StrEnum`.

### Lines 33–37: The metaclass is shared

```python
print(type(TicketStatus))            # <class 'enum.EnumType'>
print(type(Priority))               # <class 'enum.EnumType'>
print(type(OldTicketStatus))         # <class 'enum.EnumType'>
print(Priority.__mro__)              # (<enum 'Priority'>, <enum 'IntEnum'>, <class 'int'>, <enum 'ReprEnum'>, <enum 'Enum'>, <class 'object'>)
```

All three classes — `TicketStatus`, `Priority`, `OldTicketStatus` — have the *same* metaclass: `enum.EnumType` (called `EnumMeta` before Python 3.12). The mixin behaviour (int-ness, str-ness) comes from the MRO, not from a separate metaclass. `EnumType` is generic — it walks any class body, finds the assignments, builds singletons, and lets the normal Python MRO resolution do the rest.

The `__mro__` printout for `Priority` shows the order: the enum class itself, then `IntEnum`, then `int`, then `ReprEnum` (3.12+), then `Enum`, then `object`. That ordering is what makes `__str__`, `__eq__`, `__int__` come from `int` rather than from `Enum`. For `StrEnum`, the order is `StrEnum → str → ReprEnum → Enum → object`, and the explicit `StrEnum.__str__` override (which calls `self._value_`) is what wins over both `str.__str__` and `Enum.__str__`.

**Why does this matter to me?** Because when you debug a "weird" enum behaviour, the first place to look is the MRO, not the metaclass. `StrEnum` is not magic — it is `str, Enum` with one method override. `IntEnum` is not magic — it is `int, Enum`. The whole section's "surprises" reduce to two questions: "what is in the MRO?" and "which `__str__`/`__eq__`/`__int__` does that MRO resolve?"

## Execution Trace

```bash
$ python boardly/enums.py
1
True
True
1
1
open
open
True
True
open
OldTicketStatus.OPEN
True
<class 'enum.EnumType'>
<class 'enum.EnumType'>
<class 'enum.EnumType'>
(<enum 'Priority'>, <enum 'IntEnum'>, <class 'int'>, <enum 'ReprEnum'>, <enum 'Enum'>, <class 'object'>)
```

## Common Mistakes

### Mistake 1: Using `str, Enum` instead of `StrEnum` in new code

```python
class TicketStatus(str, Enum):    # the old pattern — don't
    OPEN = "open"

# JSON response ships "TicketStatus.OPEN", clients break
```

**Symptom:** JSON responses contain the class-qualified name `"TicketStatus.OPEN"` instead of the value `"open"`. Clients receive a string they did not expect.
**Why:** The `str, Enum` mixin pattern's MRO puts `Enum` before `str`, so `Enum.__str__` wins and returns the qualified name. `StrEnum` (3.11+) overrides `__str__` to return `self._value_`, which is the value you assigned.
**Fix:** Use `class TicketStatus(StrEnum): OPEN = "open"` for all new code. If you are stuck on 3.10 or earlier, install `typing_extensions` and use `typing_extensions.StrEnum`, or override `__str__` manually:

```python
class TicketStatus(str, Enum):
    OPEN = "open"
    def __str__(self):
        return str(self._value_)
```

### Mistake 2: Treating `IntEnum` like base `Enum` for type isolation

```python
class Priority(IntEnum): LOW = 1
class Status(IntEnum):   OPEN = 1

if ticket.priority == ticket.status:   # True — both are int 1
    promote(ticket)                    # wrong branch, ships bug
```

**Symptom:** Two unrelated `IntEnum` classes compare equal, your conditional takes the wrong branch, and the bug only shows up when the values happen to collide.
**Why:** `IntEnum.__eq__` falls through to `int.__eq__`, which is value-based. Two `IntEnum`s from different classes with the same integer value compare `True`. This is the price of being an `int`.
**Fix:** If you need strict type isolation, use plain `Enum` instead of `IntEnum`. Or compare by identity (`ticket.priority is ticket.status` — always `False` for different classes), or add an explicit `type(x) is type(y)` guard.

### Mistake 3: Subclassing an instantiated `Enum`

```python
class SubPriority(Priority):   # ValueError at class-creation
    URGENT = 4
```

**Symptom:** `TypeError: <enum 'SubPriority'> cannot be subclassed` or a `ValueError` at import time.
**Why:** Once an `Enum` has members, you cannot subclass it to add more — the metaclass refuses. This is a deliberate restriction to preserve the singleton contract: if subclasses could add members, every existing member would need to know which subclass it belonged to.
**Fix:** Either add the member to the original `Priority` class, or define a new separate enum and use a `Union` type at the call site (`Priority | SubPriority`).

## Engineering Trade-Offs

**Decision:** Use `StrEnum` for every closed-set string constant in an API contract; `IntEnum` for integer-wire constants (DB columns, status codes); plain `Enum` for internal-only constants that benefit from type isolation.
**Both sides:** Plain `Enum` is the strictest — no accidental equality, no `str()` surprises, no serialisation concerns. `StrEnum`/`IntEnum` trade strictness for wire-compatibility: the member is also a `str`/`int`, which means it serialises without a custom encoder but also compares equal to unrelated integers/strings. The trade-off is real and you make it every time you pick a base class.
**Commitment:** `boardly` uses `StrEnum` for every API-facing string enum (status, role, kind) and `IntEnum` only for integers that come from legacy DB schemas. New internal constants are plain `Enum`. The rule is documented in `boardly/enums.py` as a module-level docstring.

## Exercises

1. **Exercise 1 — Verify the str() fix.** Add a `print(json.dumps({"status": TicketStatus.OPEN}))` line at the bottom of `boardly/enums.py`. Confirm the output is `{"status": "open"}`. `Verify: python boardly/enums.py | tail -1`
2. **Exercise 2 — MRO inspection.** Print `TicketStatus.__mro__` and `OldTicketStatus.__mro__`. Confirm both have `str` before `Enum`, but `StrEnum`'s explicit `__str__` wins. `Verify: python -c "from boardly.enums import TicketStatus; print(TicketStatus.__mro__)"`
3. **Exercise 3 — IntEnum arithmetic.** Show that `Priority.LOW + Priority.MED == 3` returns `True` (because both are `int`). Add a comment explaining why this is sometimes a footgun. `Verify: python -c "from boardly.enums import Priority; assert Priority.LOW + Priority.MED == 3; print('ok')"`
4. **Exercise 4 — The 3.10 fallback.** Write a try/except that imports `StrEnum` from `enum` on 3.11+ and from `typing_extensions` on older Python. Confirm it works on 3.12. `Verify: python -c "from boardly.enums import TicketStatus; import sys; print(sys.version_info[:2], TicketStatus.__mro__[0].__name__)"`
5. **Exercise 5 — Custom `__str__` on plain Enum.** Define `class Color(Enum): RED=1` and override `__str__` to return `self._value_`. Compare with `StrEnum` — what is missing? (Hint: `Color.RED == "red"` is still `False`.) `Verify: python -c "from enum import Enum; class C(Enum):\n R=1\n def __str__(self): return str(self._value_)\nprint(str(C.R))"`

## Verification

```bash
$ python boardly/enums.py | head -1
Priority.LOW
$ python boardly/enums.py | rg '^open$'
open
$ python -c "from boardly.enums import TicketStatus; print(str(TicketStatus.OPEN))"
open
```

## Previously Learned Here

- [[09-enum/01-Enum-Basics]] — base `Enum`, the singleton guarantee, the three lookup forms. This lesson assumes you can declare `class X(Enum): ...` and read `__members__`.

## What's Next

[[09-enum/03-Flag-and-IntFlag]] — Now you have `IntEnum` for single integers and `StrEnum` for single strings. The next lesson covers *combinations*: `Flag` and `IntFlag` for bit-flags, where `PERM_READ | PERM_WRITE` is a real value (not a list), and the 3.11 boundary modes (`KEEP`, `DROP`, `CONFORM`, `EJECT`) decide what happens when bits fall outside the defined set.

- **Lesson 03** — `Flag`, `IntFlag`, bitwise operators, boundary modes.
- **Lesson 04** — `auto()` and the `@unique` decorator that closes the alias loophole from lesson 01.
- **Lesson 05** — How FastAPI reads `StrEnum` from a `response_model` and renders it in the OpenAPI schema.

## Sources

- **Python `enum` module documentation — `StrEnum`** — https://docs.python.org/3/library/enum.html#enum.StrEnum — accessed 2026-10-23 — the canonical reference for `StrEnum` and the `__str__` override that fixes the str-mixin surprise.
- **PEP 663 — Deprecation of enum aliases and str-enum mixins** — https://peps.python.org/pep-0663/ — accessed 2026-10-23 — the PEP that proposed deprecating the `str, Enum` pattern and introduced `StrEnum`. Read it for the production-bug motivation.
- **Python `enum` module documentation — `IntEnum`** — https://docs.python.org/3/library/enum.html#enum.IntEnum — accessed 2026-10-23 — the canonical reference for `IntEnum` and its `int` mixin semantics.

## What We Learned

- You can now declare `IntEnum` and explain why `Priority.LOW == 1` is `True` (the `int` MRO wins).
- You can now declare `StrEnum` (3.11+) and explain why `str(TicketStatus.OPEN)` returns `"open"` (the explicit `__str__` override).
- You can now identify the str-mixin trap and explain why it motivated PEP 663 and the `StrEnum` introduction.
- You can now read the MRO of any enum and predict which `__str__`/`__eq__`/`__int__` will win.
- You can now choose between `Enum`, `IntEnum`, and `StrEnum` based on the wire-format contract.
