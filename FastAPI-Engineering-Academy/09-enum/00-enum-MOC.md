---
title: "enum: Section Map of Content"
aliases:
 - enum MOC
 - Section 09 Map of Content
tags:
 - enum
 - moc
 - section-index
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "180–240 minutes"
---

# enum: Section Map of Content

*The standard-library module that gives Python named, singleton, type-safe constants — the same module FastAPI leans on to serialise every status field, every role flag, every priority label in your API.*

**You're at the very beginning of Section 09.**

This section teaches the `enum` module — `enum.Enum`, `enum.IntEnum`, `enum.StrEnum` (new in Python 3.11), `enum.Flag`, `enum.IntFlag`, `enum.auto()`, and the `@enum.unique` decorator — by building `boardly`'s `TicketStatus`, `MemberRole`, and `PermFlag` enums from scratch. By the end you will know exactly what FastAPI does when it sees `status: TicketStatus` on a `response_model`, and you will be able to write your own enum classes that don't lie in production.

#enum #section-moc

## What's in this section

Five lessons, one growing application, three canonical concepts. Read them in order — each lesson assumes the previous one.

| # | Lesson | What it teaches | Time |
|---|--------|------------------|------|
| 01 | [[09-enum/01-Enum-Basics]] | `class Color(Enum): RED = 1`, member access (`Color.RED`), name lookup (`Color["RED"]`), value lookup (`Color(1)`), the `__members__` dict, the singleton identity guarantee (`Color.RED is Color.RED`), the `enum.EnumType` metaclass (3.12+). | 30–40 min |
| 02 | [[09-enum/02-IntEnum-and-StrEnum]] | `IntEnum` (`int` + `Enum`), `StrEnum` (3.11+, `str` + `Enum`), why `str(StrEnum.X)` returns `"X"` not `"StrEnum.X"` — the 3.11 fix that killed the str-mixin pattern. | 35–45 min |
| 03 | [[09-enum/03-Flag-and-IntFlag]] | `Flag` and `IntFlag` for bit-flags, the `|`/`&`/`^`/`~` operators, `auto()` with `enum.RESTART`/`enum.CONST`, the 3.11 boundary modes `KEEP`/`DROP`/`CONFORM`/`EJECT`. | 35–45 min |
| 04 | [[09-enum/04-auto-and-value]] | `auto()`, the `_generate_next_value_` hook, custom value generators, the `@unique` decorator. | 30–40 min |
| 05 | [[09-enum/05-Enum-in-APIs]] | **The FastAPI connection.** How FastAPI serialises `Enum` fields, how `StrEnum` shapes the OpenAPI schema, the `response_model` with `Enum`, and the `Literal[...]` alternative. | 40–55 min |

**Total estimated time:** 3–4 hours of focused reading and typing.

## The canonical concepts registered here

Three lessons in this section are the canonical introduction for concepts registered in [[00-Start-Here/Concept-Registry]]:

- **Enum** — canonical lesson: [[09-enum/01-Enum-Basics]] (`first_taught_in: "09-enum/01-Enum-Basics"`). The base `enum.Enum` class, member identity, value/name lookup. Every other enum concept builds on this one.
- **IntEnum / StrEnum** — canonical lesson: [[09-enum/02-IntEnum-and-StrEnum]] (`first_taught_in: "09-enum/02-IntEnum-and-StrEnum"`). The two mixins you reach for when you need an enum that behaves like a primitive. `StrEnum` in particular is what FastAPI wants for serialised status fields.
- **Enum in APIs (FastAPI integration)** — canonical lesson: [[09-enum/05-Enum-in-APIs]] (`first_taught_in: "09-enum/05-Enum-in-APIs"`). The serialisation contract, the OpenAPI `enum` keyword, and the `Literal` alternative.

If you only have time for three lessons, do those three.

## The boardly code that threads through

Every lesson in this section writes to the same `boardly/enums.py` module. By the end of the section, that file contains:

```python
# boardly/enums.py
"""boardly's canonical enum module."""
from enum import Enum, IntEnum, StrEnum, IntFlag, auto, unique, CONFORM, KEEP

class TicketStatus(StrEnum):       # lesson 02 + 05
    OPEN    = "open"
    IN_PRG  = "in_progress"
    BLOCKED = "blocked"
    DONE    = "done"

class Priority(IntEnum):            # lesson 02
    LOW  = 1
    MED  = 2
    HIGH = 3

class PermFlag(IntFlag, boundary=CONFORM):   # lesson 03
    READ   = auto()
    WRITE  = auto()
    DELETE = auto()
    ADMIN  = 0b1111

class MemberRole(StrEnum):          # lesson 02 + 05
    OWNER  = "owner"
    MEMBER = "member"
    VIEWER = "viewer"
```

You will see these definitions evolve lesson by lesson. By lesson 05, they are wired into `boardly`'s FastAPI routes and rendered in the OpenAPI schema.

## Prerequisites

Before starting Section 09, you should be comfortable with:

- **Classes and metaclasses basics** — knowing that `type(SomeClass)` is its metaclass. See [[01-typing/01-Type-Hints-Basics]] for the surrounding context of Python's type system. (If you can read `class C: pass` and explain what `type(C)` returns, you are ready.)
- **`dict` and `OrderedDict`** — `Enum.__members__` is a `dict`-like object. See [[04-collections/06-OrderedDict]] (and the sibling [[04-collections/05-ChainMap]] lesson) if you need a refresher.
- **Reading type hints** — annotations like `status: TicketStatus` should be familiar. See [[01-typing/01-Type-Hints-Basics]].

**The most common gap: confusing member access with value lookup.** Students arrive thinking `Color.RED` and `Color(1)` are two ways of writing the same thing. They are not — one looks up by name, the other by value, and they behave differently when the lookup misses. Lesson 01 spends a full block on the difference.

## How this section fits the course

This section is the foundation for:

- [[10-inspect/06-How-FastAPI-uses-inspect]] — FastAPI's dependency resolver reads your `Enum` subclass from each `Annotated[TicketStatus, ...]` annotation. Lesson 05 shows the upstream side; the inspect section shows the read-side.
- [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — Pydantic's `BaseModel` uses `StrEnum` natively; a `@dataclass` field with an `Enum` annotation does not auto-serialise. Lesson 05 is the upstream read.

## What's next

Open [[09-enum/01-Enum-Basics]] and start typing. We will build `boardly`'s `TicketStatus` from a raw `class` with bare integers — watch the bug — and then rewrite it as an `Enum`. By the end of lesson 01 you will have the singleton guarantee and the three lookup forms in your fingers.

- **Lesson 01** — `Enum`, members, `__members__`, identity.
- **Lesson 02** — `IntEnum`, `StrEnum`, the `str()` behaviour fix.
- **Lesson 05** — How FastAPI reads your `Enum` on every request.

**Welcome to the enum section. Pull up a chair.**

## Sources

- **Python `enum` module documentation** — https://docs.python.org/3/library/enum.html — accessed 2026-10-23 — the source-of-truth API reference for `Enum`, `IntEnum`, `StrEnum`, `Flag`, `IntFlag`, `auto`, `unique`, and the 3.11+ boundary modes.
- **PEP 435 — Adding an Enum type to the Python standard library** — https://peps.python.org/pep-0435/ — accessed 2026-10-23 — the original PEP that introduced `enum` in Python 3.4. Read it for the design rationale (why members are singletons, why value lookup exists).
- **PEP 663 — Deprecation of enum aliases and str-enum mixins** — https://peps.python.org/pep-0663/ — accessed 2026-10-23 — the PEP that motivated `StrEnum` in 3.11 and fixed the `str(OldStrEnum.X)` surprise. Lesson 02 leans on this.
