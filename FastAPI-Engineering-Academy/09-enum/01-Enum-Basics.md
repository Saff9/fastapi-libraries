---
title: "Lesson 01: Enum Basics"
aliases:
 - Enum
 - enum.Enum
 - Enum basics
tags:
 - enum
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "30–40 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[09-enum/02-IntEnum-and-StrEnum]]"
 - "[[09-enum/04-auto-and-value]]"
first_taught_in: "09-enum/01-Enum-Basics"
---

# Lesson 01: Enum Basics

*How `boardly` replaced a buggy `TICKET_OPEN = 1` integer constant with `class TicketStatus(Enum): OPEN = 1` and stopped confusing itself about which integer meant what.*

**You're at the very beginning of Section 09.**

You have written `STATUS_OPEN = 1` somewhere in your code. You have also written `STATUS_OPEN = "open"` somewhere else. Both files imported the same constant, and they got two different values, and a comparison silently returned `False` and the bug took two hours to find. We are going to fix that, permanently, with the `enum` module. Take your time. Type every example. **This is how you learn.**

#enum #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare an `Enum`** — write `class TicketStatus(Enum): OPEN = 1` and read the three things Python does at class-creation time.
2. **Look up members three ways** — by attribute (`TicketStatus.OPEN`), by name (`TicketStatus["OPEN"]`), and by value (`TicketStatus(1)`), and explain when each one raises.
3. **Read `__members__`** — iterate an enum, build a lookup table, and explain why `__members__` is a `dict`-like, not a `list`.
4. **Reason about identity** — explain why `TicketStatus.OPEN is TicketStatus(1)` returns `True`, and why that guarantee matters for `match`/`is`/caching.
5. **Name the metaclass** — identify `enum.EnumType` (Python 3.12+) as the metaclass that turns your `class` body into enum members.

## Prerequisites

Before starting, you need:

- **Comfort reading a Python class** — if `class C: pass` followed by `c = C()` makes sense, you are ready. See [[01-typing/01-Type-Hints-Basics]] for the surrounding type-system context.
- **About 30–40 minutes of focused time.**

**The most common gap: confusing "a member" with "a value".** Students arrive thinking `TicketStatus.OPEN` is `1`. It is not. It is a `TicketStatus` instance whose `.value` is `1`. Holding that distinction is the whole point of this lesson.

## The Problem

Here is the bug that motivates the entire `enum` module. Read it slowly.

```python
# boardly/constants.py — the bad old days
STATUS_OPEN    = 1
STATUS_IN_PRG  = 2
STATUS_BLOCKED = 3
STATUS_DONE    = 4

PRIORITY_LOW   = 1
PRIORITY_MED   = 2
PRIORITY_HIGH = 3
```

Two unrelated concepts (`STATUS_*` and `PRIORITY_*`) share the integer `1`. The first time you write `if ticket.status == ticket.priority:` — comparing two completely different things — Python returns `True` and you ship a bug. The integers have no concept of *which kind of constant they are*; they are just `int`.

Worse, there is no enumeration. `STATUS_OPEN = 1` does not know about `STATUS_IN_PRG = 2`. You cannot iterate "all the statuses". You cannot raise a clear error when someone passes `status=99`. You cannot print `"open"` from `1` without writing your own reverse map. Every team writes that reverse map. Every team eventually ships a bug where the reverse map gets out of sync with the constants.

`enum.Enum` fixes all five of those problems in one class statement. Let me show you.

## The Code

```python
# boardly/enums.py
"""boardly's canonical ticket-status enum."""
from enum import Enum

class TicketStatus(Enum):
    OPEN    = 1
    IN_PRG  = 2
    BLOCKED = 3
    DONE    = 4

# 1. Attribute access — by name
print(TicketStatus.OPEN)             # TicketStatus.OPEN
print(TicketStatus.OPEN.name)        # OPEN
print(TicketStatus.OPEN.value)       # 1

# 2. Subscript access — by member name (string lookup, 3.11+ ergonomic form)
print(TicketStatus["OPEN"])          # TicketStatus.OPEN

# 3. Call lookup — by value (raises ValueError on miss)
print(TicketStatus(1))               # TicketStatus.OPEN

# 4. __members__ — the dict-like that lets you iterate
for name, member in TicketStatus.__members__.items():
    print(f"{name:8} = {member.value}")
# OPEN     = 1
# IN_PRG   = 2
# BLOCKED  = 3
# DONE     = 4

# 5. Identity — members are singletons
print(TicketStatus.OPEN is TicketStatus.OPEN)   # True
print(TicketStatus.OPEN is TicketStatus(1))     # True
print(TicketStatus.OPEN == 1)                  # False — different type

# 6. The metaclass (Python 3.12+)
print(type(TicketStatus))           # <class 'enum.EnumType'>
print(type(TicketStatus.OPEN))      # <enum 'TicketStatus'>
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–6: Declaring the enum

```python
from enum import Enum

class TicketStatus(Enum):
    OPEN    = 1
    IN_PRG  = 2
    BLOCKED = 3
    DONE    = 4
```

The `from enum import Enum` line pulls the base class. `Enum` is the parent of every other enum flavour in this section — `IntEnum`, `StrEnum`, `Flag` all inherit from it (transitively or directly).

The `class TicketStatus(Enum):` line triggers a metaclass. The metaclass is `enum.EnumType` (called `EnumMeta` before Python 3.12). At class-creation time — not at instance time — that metaclass walks the class body, finds every name bound to a value, and turns it into an *enum member*: a singleton instance of `TicketStatus` itself. By the time the `class` statement finishes, `TicketStatus.OPEN` is not the integer `1` — it is a `TicketStatus` instance whose `.value` attribute is `1` and whose `.name` attribute is the string `"OPEN"`.

**Why does Python do this at class-creation time, not lazily?** Two reasons. First, identity: by the time any other code runs, `TicketStatus.OPEN` must already be the same object every time you ask for it. Lazy creation would break `is`. Second, validation: the metaclass can immediately check for duplicate values and raise `ValueError` at class-creation, before you ship the bug to production. That is why a typo in your enum body crashes on import, not three weeks later.

**Note — EnumType vs EnumMeta (the 3.12 rename)**

Before Python 3.12, the metaclass was named `EnumMeta`. The 3.12 release renamed it to `EnumType` to match the convention that a metaclass shares its class's name (`type` for `object`, `EnumType` for `Enum`). `enum.EnumMeta` remains as an alias — old code still imports it. New code imports `enum.EnumType`. See PEP 435 for the original `EnumMeta` design.

### Lines 8–11: Attribute access and `.name`/`.value`

```python
print(TicketStatus.OPEN)             # TicketStatus.OPEN
print(TicketStatus.OPEN.name)        # OPEN
print(TicketStatus.OPEN.value)       # 1
```

`TicketStatus.OPEN` is attribute access on the class — the metaclass's `__getattr__` returns the pre-built member. The `repr` of a member is `TicketStatus.OPEN`, which is the class name and the member name separated by a dot. That readable `repr` is one of the small things that makes `Enum` worth using over bare integers — your tracebacks now say `TicketStatus.OPEN` instead of `1`.

`.name` is the string `"OPEN"`. `.value` is whatever you assigned — here the integer `1`, but it can be any hashable: a string, a tuple, a ` frozenset`. (Tuple values are how `Color` enums handle multi-component values like RGB triples.) Both attributes are read-only; assigning `TicketStatus.OPEN.value = 5` raises `AttributeError`.

**Warning — Don't confuse `.value` with the member itself**

```python
TicketStatus.OPEN == 1     # False!
TicketStatus.OPEN.value == 1   # True
```

The member is *not* its value. That is the whole point: the member has a *type* (`TicketStatus`), and only members of `TicketStatus` can compare equal to other members of `TicketStatus`. The next lesson introduces `IntEnum`, which *does* compare equal to its integer value — and you will see why that is a deliberate exception, not the default.

### Lines 13–14: Subscript access by name

```python
print(TicketStatus["OPEN"])          # TicketStatus.OPEN
```

`TicketStatus["OPEN"]` is the name-based lookup — the metaclass's `__getitem__` walks `__members__` and returns the member whose `.name` matches. This form is essential when the name lives in a variable (`name = "OPEN"; TicketStatus[name]`), or when you are deserialising from JSON that stored the name string.

`TicketStatus["OPEN"]` raises `KeyError` if the name does not exist. (Before Python 3.11, this `__getitem__` access was the canonical form; the `Enum["X"]` ergonomic shortcut has been there since 3.4, but it was reaffirmed and surfaced in the 3.11 enum rewrites.)

**Why KeyError and not AttributeError?** Because subscript access is dict-shaped — the lookup goes through `__members__`, which is a `dict`-like. The error type matches the access form: attribute access raises `AttributeError`, subscript access raises `KeyError`, value lookup raises `ValueError`. Three access forms, three exception types, one consistent story.

### Lines 16–17: Value lookup by call

```python
print(TicketStatus(1))               # TicketStatus.OPEN
```

`TicketStatus(1)` is the value-based lookup — the metaclass's `__call__` walks `__members__` looking for a member whose `.value == 1`. This is the form you reach for when deserialising from a database integer column, an environment-variable integer, or a Pydantic `int` field that you want to coerce into the enum.

`TicketStatus(99)` raises `ValueError: 99 is not a valid TicketStatus`. That `ValueError` is the second half of the enum contract — your API now refuses unknown values at the boundary, instead of silently storing `99` and wondering why nothing renders.

**Tip — Value lookup is O(n), name lookup is O(1)**

Internally, the metaclass builds `_value2member_map_` (value → member) and `_member_map_` (name → member) at class-creation time. Both are plain dicts. So both lookups are O(1) — the O(n) wording above is about the implementation walking the map, but the lookup itself is a dict access. The performance worry people have about enums is largely a myth on CPython 3.11+; the `_member_map_` is a real dict.

### Lines 19–22: `__members__` is the dict-like

```python
for name, member in TicketStatus.__members__.items():
    print(f"{name:8} = {member.value}")
```

`TicketStatus.__members__` is the canonical dict-like that maps each member's name (string) to the member object itself. It is a `mappingproxy` (defined in the `types` module as `MappingProxyType`) — a read-only view over an `OrderedDict`. You can read it, iterate it, and pass it to `dict()` to get a real dict, but you cannot mutate it. That immutability is the third part of the singleton contract: no code can sneak `TicketStatus.__members__["NEW"] = ...` and inject a fake member at runtime.

The iteration order of `__members__` matches the order in which you wrote the members in the class body. (CPython has guaranteed dict ordering since 3.7, and `__members__` is built by walking the class namespace in source order.) That is why your `for` loop above prints `OPEN`, `IN_PRG`, `BLOCKED`, `DONE` — exactly the order in the source.

**Why is `__members__` exposed publicly but `_member_map_` is underscore-private?** Because `__members__` is the *stable* API: it has been there since 3.4 and its semantics have not changed. The underscore-private maps (`_member_map_`, `_value2member_map_`, `_member_names`) are the implementation's internal cache, and they have changed shape across Python versions. Use `__members__` in your code; reach for the underscore-private ones only when you are debugging CPython itself.

### Lines 24–26: The singleton identity guarantee

```python
print(TicketStatus.OPEN is TicketStatus.OPEN)   # True
print(TicketStatus.OPEN is TicketStatus(1))     # True
print(TicketStatus.OPEN == 1)                  # False — different type
```

`TicketStatus.OPEN is TicketStatus.OPEN` is `True` because the metaclass builds exactly one `TicketStatus` instance for the value `1`, at class-creation time, and every subsequent access — attribute, name lookup, value lookup — returns the *same object*. There is no second construction. `is` is pointer-equality, and the pointer never changes.

`TicketStatus.OPEN is TicketStatus(1)` is `True` for the same reason: `TicketStatus(1)` looks up the value `1` in `_value2member_map_` and returns the same singleton. Identity across lookup forms is what lets you use `match`/`is` safely:

```python
match ticket.status:
    case TicketStatus.OPEN:    ...
    case TicketStatus.BLOCKED: ...
```

`TicketStatus.OPEN == 1` is `False` because the member and the integer are different types. `Enum.__eq__` returns `NotImplemented` when the other side is not an enum member of the same class — and Python falls back to identity comparison, which is `False`. This is the *feature*, not a bug: the whole point is that a `TicketStatus` and a `Priority` cannot be confused, even if their integer values happen to match.

### Lines 28–30: The metaclass

```python
print(type(TicketStatus))           # <class 'enum.EnumType'>
print(type(TicketStatus.OPEN))      # <enum 'TicketStatus'>
```

`type(TicketStatus)` is `enum.EnumType`. That is the metaclass — the class that builds classes. `EnumType` is what runs when Python sees `class TicketStatus(Enum):` — it intercepts the class-body namespace, finds the assignments, and turns each into a singleton member.

`type(TicketStatus.OPEN)` is the `TicketStatus` class itself (its `repr` is `<enum 'TicketStatus'>`). That is the standard metaclass behaviour: instances of a class built by `EnumType` are members of the enum, and their `type()` is the enum class.

**Why does the metaclass matter to me?** Because every surprising enum behaviour — the singleton guarantee, the `__members__` immutability, the duplicate-value detection, the `auto()` value generation in lesson 04, the boundary handling in lesson 03 — is implemented in `EnumType.__new__`. When something behaves unexpectedly, the answer is in the metaclass. You do not need to read CPython source to use enums, but knowing that *a* metaclass is in play reframes "weird" as "designed".

## Execution Trace

```bash
$ python boardly/enums.py
TicketStatus.OPEN
OPEN
1
TicketStatus.OPEN
TicketStatus.OPEN
OPEN     = 1
IN_PRG   = 2
BLOCKED  = 3
DONE     = 4
True
True
False
<class 'enum.EnumType'>
<enum 'TicketStatus'>
```

## Common Mistakes

### Mistake 1: Confusing value lookup with name lookup

```python
TicketStatus("OPEN")   # ValueError: 'OPEN' is not a valid TicketStatus
```

**Symptom:** `ValueError` from a deserialisation call you swore worked yesterday.
**Why:** `TicketStatus(...)` is *value* lookup, not name lookup. The string `"OPEN"` is not in `_value2member_map_` — only the integer `1` is. Students reach for the call form because they think "I have a string, so I look it up" — but the call form looks up by `.value`, not by `.name`.
**Fix:** Use `TicketStatus["OPEN"]` for name lookup; reserve `TicketStatus(value)` for the value form. If you are not sure which one to use, ask: "Did I write `OPEN = 1` or `OPEN = "open"`?" — the right-hand side is the value.

### Mistake 2: Trying to mutate a member

```python
TicketStatus.OPEN.value = 99   # AttributeError: can't set attribute
```

**Symptom:** `AttributeError` on what looks like a normal attribute assignment.
**Why:** Enum members are immutable singletons. `.name` and `.value` are read-only descriptors — assigning to them raises. The immutability is the contract: if members could change, identity (`is`) could not be guaranteed.
**Fix:** Add a new member to the enum body and re-deploy. Never mutate an existing member at runtime — even if you find the CPython escape hatch that lets you, the next deployment will revert it.

### Mistake 3: Comparing across enum classes

```python
class Priority(Enum):
    LOW = 1

TicketStatus.OPEN == Priority.LOW   # False
```

**Symptom:** Two enums that "should" be equal return `False` and your `if ticket.status == some_priority:` branch never runs.
**Why:** `Enum.__eq__` returns `NotImplemented` unless both sides are members of the *same* enum class. Python falls back to identity, which is `False`. This is the feature: the enum refuses to silently equate two unrelated concepts that happen to share a value.
**Fix:** Stop comparing them. If you genuinely need cross-enum comparison, compare `.value` to `.value` *explicitly* — and add a comment explaining why.

## Engineering Trade-Offs

**Decision:** Use `Enum` for every closed set of named constants — statuses, roles, kinds, types.
**Both sides:** The alternative is module-level constants (`STATUS_OPEN = 1`). Constants are simpler at first reading — no metaclass, no `__members__`, just `int`s — and they survive every Python version without import concerns. But constants have no type, no enumeration, no identity, no duplicate detection, and no reverse map. You pay for the simplicity with the same five bugs the section opened with.
**Commitment:** `boardly` uses `Enum` (specifically `StrEnum`, lesson 02) for every closed constant set that appears in an API contract. Bare integer constants are reserved for internal-only constants that never cross a serialisation boundary.

## Exercises

1. **Exercise 1 — Add a member.** Add `CANCELLED = 5` to `TicketStatus` in `boardly/enums.py`. Re-run the script. Observe that `__members__` iteration now includes `CANCELLED`. `Verify: python boardly/enums.py | rg CANCELLED`
2. **Exercise 2 — Reverse value lookup.** Write a function `status_from_int(value: int) -> TicketStatus` that returns the member or raises `ValueError` with a custom message. Use the call form, do not reinvent `_value2member_map_`. `Verify: python -c "from boardly.enums import TicketStatus, status_from_int; print(status_from_int(1))"`
3. **Exercise 3 — Iterate names only.** Modify the `__members__` loop to print only names (not values). Use `TicketStatus.__members__.keys()` instead of `.items()`. `Verify: python boardly/enums.py | rg '^OPEN$'`
4. **Exercise 4 — Identity test in a loop.** Write a loop that calls `TicketStatus(1)` ten thousand times and asserts every result `is` the same object. Time it. Confirm O(1). `Verify: python -c "from boardly.enums import TicketStatus; t=TicketStatus(1); assert all(TicketStatus(1) is t for _ in range(10000)); print('ok')"`
5. **Exercise 5 — The duplicate-value trap.** Add a second member `OPEN_AGAIN = 1` to `TicketStatus`. Run the script. Read the warning. Explain (in a comment) what an *alias* is and why `enum.unique` (lesson 04) refuses it. `Verify: python boardly/enums.py | rg 'as the alias' || echo 'no alias detected'`

## Verification

```bash
$ python boardly/enums.py
TicketStatus.OPEN
OPEN
1
TicketStatus.OPEN
TicketStatus.OPEN
OPEN     = 1
IN_PRG   = 2
BLOCKED  = 3
DONE     = 4
True
True
False
<class 'enum.EnumType'>
<enum 'TicketStatus'>
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — type annotations and the basic class syntax that this lesson builds on.
- [[04-collections/06-OrderedDict]] — `OrderedDict` and `dict`-like objects; `__members__` is one.

## What's Next

[[09-enum/02-IntEnum-and-StrEnum]] — Now that you can declare an `Enum`, we ask the obvious question: "what if I need this enum to *be* an integer, or *be* a string, so I can pass it where an `int` or `str` is expected?" The answer is `IntEnum` and `StrEnum` — and the answer comes with a 3.11 surprise about what `str(MyStrEnum.X)` returns.

- **Lesson 02** — `IntEnum`, `StrEnum`, the `str()` behaviour fix.
- **Lesson 04** — `auto()` and the `@unique` decorator that closes the alias loophole.
- **Lesson 05** — How FastAPI reads `TicketStatus` from a `response_model`.

## Sources

- **Python `enum` module documentation** — https://docs.python.org/3/library/enum.html — accessed 2026-10-23 — the source-of-truth reference for `Enum`, `__members__`, name/value lookup, and the `EnumType` metaclass.
- **PEP 435 — Adding an Enum type to the Python standard library** — https://peps.python.org/pep-0435/ — accessed 2026-10-23 — the original 3.4 PEP. Read it for the singleton rationale and the `_value2member_map_` design.
- **PEP 663 — Deprecation of enum aliases and str-enum mixins** — https://peps.python.org/pep-0663/ — accessed 2026-10-23 — context for why name lookup was made first-class in 3.11 and why aliases are now flagged by default.

## What We Learned

- You can now declare `class X(Enum): ...` and explain what the metaclass does at class-creation time.
- You can look up a member three ways (attribute, name, value) and you know which exception each form raises.
- You can iterate `__members__` and explain why it is dict-like and immutable.
- You can reason about the singleton identity guarantee (`X.A is X.A is X(value_of_A)`).
- You can identify `enum.EnumType` (3.12+) as the metaclass and know it was called `EnumMeta` before 3.12.
