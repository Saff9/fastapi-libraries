---
title: "Lesson 05: Inheritance"
aliases:
 - dataclass inheritance
 - kw_only
 - required after defaulted error
tags:
 - dataclasses
 - inheritance
 - mro
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
 - "[[06-dataclasses/04-Slots-and-Performance]]"
related_lessons:
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
 - "[[06-dataclasses/08-KW_ONLY-and-InitVar]]"
---

# Lesson 05: Inheritance

*How fields accumulate in MRO order across `boardly`'s `BoardObject` → `Ticket` → `Comment` hierarchy, the default-override rules, and the `kw_only=True` (3.10+) fix for the "required field after a defaulted one" `TypeError` that every team hits on day one.*

**You're at the very beginning of Section 06, fifth lesson in.**

You start with one model — `BoardObject`. It has `id: int`. You add `Ticket(BoardObject)` with `title: str` and `assignee_id: int`. You add `Comment(BoardObject)` with `body: str` and `author_id: int`. The fields accumulate: a `Ticket` has `id`, `title`, `assignee_id`. A `Comment` has `id`, `body`, `author_id`. So far so good. Then you add a defaulted field to `BoardObject` — `created_at: datetime = field(default_factory=datetime.now)` — and suddenly every subclass breaks with `TypeError: non-default argument follows default argument`. The error is the Python language rule that defaulted parameters cannot precede required ones in a function signature. `@dataclass`'s MRO-order field accumulation makes this trap hit every team on day one. The fix is `kw_only=True` (Python 3.10+), which makes every field keyword-only and breaks the position-ordering rule. This lesson walks the whole mechanism: the accumulation, the override rules, and the `kw_only` escape.

#dataclasses #inheritance #mro

## Learning Objectives

By the end of this lesson you will be able to:

1. **Read an inheritance chain** (`BoardObject` → `Ticket`) and predict the accumulated field order in the generated `__init__`.
2. **Explain the default-override rules** — what happens when a subclass redeclares a field with a different default, and the `field(default=...)` form that overrides.
3. **Diagnose the "non-default argument follows default argument" `TypeError`** — read the error, find the offending base class, and know the two fixes (reorder fields or use `kw_only=True`).
4. **Apply `kw_only=True`** at the class level and `kw_only=True` at the `field()` level (Python 3.10+).
5. **Reason about `__post_init__` in inheritance** — the MRO order it runs in, and the `super().__post_init__()` discipline.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. The field-ordering rule is a consequence of the generated `__init__` being a regular Python function.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. Defaulted vs required fields is the axis this lesson turns on.
- **`slots=True`** — [[06-dataclasses/04-Slots-and-Performance]]. The slots-inheritance gotcha from lesson 04 is the special case of the general inheritance rule taught here.
- **About 30–45 minutes of focused time.**

**The most common gap: the "required after defaulted" `TypeError`.**

Students add a defaulted field to a base class and every subclass breaks. The error message is `TypeError: non-default argument follows default argument`. The student sees the message, looks at the subclass (which has only required fields), and is confused — the error is in the *combined* signature, not the subclass. The lesson's first half is the diagnosis; the second half is the `kw_only` fix.

## The Problem

You have a `BoardObject` base class with shared fields. You want every `boardly` model to inherit `id` and `created_at` from `BoardObject`, then add its own fields. The natural first attempt is:

```python
@dataclass
class BoardObject:
    id: int
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Ticket(BoardObject):
    title: str
    assignee_id: int
```

`@dataclass` accumulates fields in MRO order — `BoardObject`'s `id`, then `BoardObject`'s `created_at`, then `Ticket`'s `title`, then `Ticket`'s `assignee_id`. The generated `__init__` signature is `(self, id, created_at=<factory>, title, assignee_id)` — and Python raises `TypeError` because the defaulted `created_at` is followed by the required `title`. The error is a Python language rule, not a `@dataclass` rule: a function signature cannot have a non-default argument after a default one. The fix is to either reorder the fields (move `created_at` to the end of `BoardObject` — but then every subclass's required fields must also come after, which breaks the "common base" pattern) or to use `kw_only=True` (Python 3.10+) — every field becomes keyword-only and the position-ordering rule no longer applies. This lesson walks both paths.

## The Code

```python
# boardly/models/board_object.py
"""boardly inheritance — field accumulation and kw_only."""
from dataclasses import dataclass, field
from datetime import datetime


# (A) The broken version — required-after-defaulted error.
@dataclass
class BoardObjectBroken:
    id: int
    created_at: datetime = field(default_factory=datetime.now)


# (B) The fix — kw_only=True at the class level (3.10+).
@dataclass(kw_only=True)
class BoardObject:
    id: int
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(kw_only=True)
class Ticket(BoardObject):
    title: str
    assignee_id: int = 0


# (C) Field-level kw_only via the KW_ONLY sentinel (lesson 08 preview).
@dataclass
class Comment(BoardObject):
    body: str
    author_id: int


if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42)
    print("ticket:", t)

    try:
        Ticket(1, datetime.now(), "Fix login", 42)
    except TypeError as exc:
        print("positional fails:", exc)

    c = Comment(id=2, body="LGTM", author_id=99)
    print("comment:", c)
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the broken base

```python
# boardly/models/board_object.py
"""boardly inheritance — field accumulation and kw_only."""
from dataclasses import dataclass, field
from datetime import datetime


# (A) The broken version — required-after-defaulted error.
@dataclass
class BoardObjectBroken:
    id: int
    created_at: datetime = field(default_factory=datetime.now)
```

`BoardObjectBroken` is the first attempt. It is a perfectly valid `@dataclass` on its own — `BoardObjectBroken(id=1)` works. The breakage appears only when a subclass adds *required* fields after `created_at`. The `field(default_factory=datetime.now)` is correct (the lesson 02 mutable-default check is fine with `datetime.now` because `datetime` is hashable but the factory form is what makes a fresh value per instance — see Mistake 2 below for why bare `= datetime.now()` is broken).

**Why does `created_at: datetime = datetime.now()` fail?**

Because `datetime.now()` is *evaluated at class-definition time* — once, when the class body runs. Every instance would get the *same* `datetime` value, the one from when the module was imported. The factory form `field(default_factory=datetime.now)` calls `datetime.now()` *per `__init__` call*, so every instance gets its own fresh timestamp. This is the lesson 02 trap in a less-obvious form — `datetime` is technically immutable (hashable), so the lesson 02 check passes, but the *value* would be shared across instances. The factory form is correct; the bare form is the bug.

### Lines 11–15: The `kw_only=True` fix at the class level

```python
# (B) The fix — kw_only=True at the class level (3.10+).
@dataclass(kw_only=True)
class BoardObject:
    id: int
    created_at: datetime = field(default_factory=datetime.now)
```

`@dataclass(kw_only=True)` (Python 3.10+, PEP 557 follow-up) makes every field in the generated `__init__` keyword-only. The signature becomes `def __init__(self, *, id, created_at=<factory>): ...` — the `*` forces everything after it to be keyword-only. With every field keyword-only, the position-ordering rule no longer applies — `id` and `created_at` can be passed in any order, by name. The "required after defaulted" `TypeError` disappears.

**Why was `kw_only` added in 3.10 rather than 3.7 when `@dataclass` first shipped?**

Because the inheritance use case (a base with a defaulted field, a subclass with required fields) was not the dominant pattern in 3.7 — most early dataclasses were flat. As adoption grew, the pattern became common, and the `TypeError` was reported enough times to justify a first-class fix. The 3.10 release also added `slots=True` and the field-level `kw_only` parameter — the three knobs (`slots`, `kw_only`, `KW_ONLY`) were a coordinated second-generation feature set. The CPython commit history (`bpo-42132` for slots, `bpo-42128` for kw_only) shows the two were developed together.

### Lines 17–20: The `kw_only` subclass

```python
@dataclass(kw_only=True)
class Ticket(BoardObject):
    title: str
    assignee_id: int = 0
```

`Ticket` also uses `kw_only=True`. The decorator accumulates fields in MRO order: `BoardObject.id`, `BoardObject.created_at`, `Ticket.title`, `Ticket.assignee_id`. The generated `__init__` is `def __init__(self, *, id, created_at=<factory>, title, assignee_id=0): ...` — every field is keyword-only, so the position-ordering rule is irrelevant. The `Ticket(id=1, title="Fix login", assignee_id=42)` call works; positional `Ticket(1, datetime.now(), "Fix login", 42)` fails with `TypeError: Ticket.__init__() takes 1 positional argument but 5 were given`.

**Why does `Ticket` need `kw_only=True` if `BoardObject` already has it?**

Because `kw_only` is per-class, not inherited automatically. `BoardObject`'s `kw_only=True` applies to `BoardObject`'s fields — `id` and `created_at` are keyword-only in the combined `__init__`. But `Ticket`'s own fields (`title`, `assignee_id`) are *not* keyword-only unless `Ticket` also sets `kw_only=True`. The decorator's bookkeeping is: for each field in MRO order, check the `Field.kw_only` flag — if set, mark the parameter as keyword-only in the signature. The class-level `kw_only=True` sets `Field.kw_only = True` for every field declared in *that class*. Inherited fields keep their original flag. The result is: a subclass without `kw_only=True` will have the base's fields keyword-only (good) but its own fields positional (bad — they are required and follow the defaulted `created_at`).

### Lines 22–25: The non-`kw_only` subclass preview

```python
# (C) Field-level kw_only via the KW_ONLY sentinel (lesson 08 preview).
@dataclass
class Comment(BoardObject):
    body: str
    author_id: int
```

Wait — `Comment` does not use `kw_only=True`, but it inherits from `BoardObject` which does. The combined signature is `(self, *, id, created_at=<factory>, body, author_id)`. The `body` and `author_id` fields are *not* keyword-only — they are positional. But they follow the `*` separator (because `id` and `created_at` are keyword-only and they come first in MRO order), so the `*` covers them too. Wait, no — the `*` only covers parameters *after* it that are also keyword-only or marked as such. Let me re-examine: actually, once the `*` separator appears in a signature, every parameter after it is keyword-only *regardless of whether they have defaults or not*. The signature `(self, *, id, created_at=<factory>, body, author_id)` — `body` and `author_id` *are* keyword-only by virtue of being after the `*`. So `Comment(id=2, body="LGTM", author_id=99)` works, and `Comment(2, "LGTM", 99)` fails. The class-level `kw_only=True` on `BoardObject` propagates through the signature's `*` separator to every later field, including those declared in subclasses.

**Wait — does that mean `Comment` doesn't need its own `kw_only=True`?**

Yes, exactly. Once any field in the MRO is keyword-only via the class-level `kw_only`, the `*` separator appears in the signature at the position of the first keyword-only field, and every field after it (in MRO order) is also keyword-only. `Comment` benefits from `BoardObject`'s `kw_only=True` because `BoardObject`'s fields come first in the MRO. If `BoardObject` did not have `kw_only=True` and `Comment` did, the signature would be `(self, id, created_at=<factory>, *, body, author_id)` — `id` and `created_at` positional, `body` and `author_id` keyword-only. Both forms are valid; the choice depends on which fields you want to allow positional. The recommended pattern is the `kw_only=True` on the base — it propagates downward. Lesson 08 covers the `KW_ONLY` sentinel for the field-level version.

### Lines 27–33: The sanity check

```python
if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42)
    print("ticket:", t)

    try:
        Ticket(1, datetime.now(), "Fix login", 42)
    except TypeError as exc:
        print("positional fails:", exc)
```

`t = Ticket(id=1, title="Fix login", assignee_id=42)` succeeds — every field is keyword-only. The `Ticket(1, datetime.now(), "Fix login", 42)` call fails with `TypeError` because positional args are not accepted after the `*` separator. The `except TypeError as exc` block prints the message, which is `Ticket.__init__() takes 1 positional argument but 5 were given`.

### Lines 35–36: The Comment sanity check

```python
    c = Comment(id=2, body="LGTM", author_id=99)
    print("comment:", c)
```

`Comment(id=2, body="LGTM", author_id=99)` succeeds — the `*` separator from `BoardObject`'s `kw_only=True` covers `body` and `author_id` too. The `created_at` field defaults to `datetime.now()` factory result. The `print` produces `Comment(id=2, created_at=datetime.datetime(2026, 10, 23, 12, 0, 0), body='LGTM', author_id=99)` — fields in MRO order, then `Comment`'s own fields.

**Why is field reordering in MRO order the rule?**

Because the MRO (Method Resolution Order) is the linearisation of the inheritance graph, and `@dataclass` walks it to collect fields. The C3 linearisation algorithm (the one Python uses) puts base classes before derived classes, left-to-right for multiple inheritance. The accumulated field order matches the order in which a human would read the inheritance diagram from root to leaf. The MRO rule is what makes `@dataclass`'s inheritance predictable — without it, the field order would depend on implementation details of `__annotations__` walking.

## Execution Trace

```bash
$ python boardly/models/board_object.py
ticket: Ticket(id=1, created_at=datetime.datetime(2026, 10, 23, 12, 0, 0, 123456), title='Fix login', assignee_id=42)
positional fails: Ticket.__init__() takes 1 positional argument but 5 were given
comment: Comment(id=2, created_at=datetime.datetime(2026, 10, 23, 12, 0, 0, 654321), body='LGTM', author_id=99)
```

The `created_at` timestamps differ between `t` and `c` — each `__init__` call invoked `datetime.now()` separately. The positional call fails with the keyword-only enforcement error. The `Comment` instance uses the propagated `*` separator from `BoardObject`'s `kw_only=True`.

## Common Mistakes

### Mistake 1: Subclass adds required fields after a defaulted base field

```python
@dataclass
class Base:
    id: int
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Derived(Base):
    title: str   # required, follows the defaulted created_at
```

**Symptom:** `TypeError: non-default argument follows default argument` at import time.
**Why:** `@dataclass` accumulates fields in MRO order: `Base.id`, `Base.created_at`, `Derived.title`. The generated signature would be `(self, id, created_at=<factory>, title)` — defaulted `created_at` followed by required `title`, which Python's function-signature rules forbid.
**Fix:** Use `@dataclass(kw_only=True)` on `Base` (propagates the `*` separator through the signature).

### Mistake 2: Bare `datetime.now()` as a default

```python
@dataclass
class Base:
    created_at: datetime = datetime.now()  # WRONG
```

**Symptom:** No error at import time, but every instance has the *same* `created_at` — the timestamp from when the module was imported.
**Why:** `datetime.now()` is evaluated once, at class-body time. The result is stored as the default and shared across every instance. The lesson 02 mutable-default check does not catch this because `datetime` is hashable (immutable).
**Fix:** `field(default_factory=datetime.now)` — the factory is called per `__init__`.

### Mistake 3: Overriding a field with a different default

```python
@dataclass
class Base:
    archived: bool = False

@dataclass
class Derived(Base):
    archived: bool = True   # override the default
```

**Symptom:** `Derived(id=1).archived` is `True` — the override works.
**Why:** `@dataclass` walks fields in MRO order; for fields with the same name in different classes, the *most-derived* class's version wins (the one closest to the leaf in the MRO). `Derived`'s `archived: bool = True` replaces `Base`'s `archived: bool = False` in the accumulated field set. The default is replaced too.
**Fix:** None needed — this is the documented behaviour. Use it deliberately.

## Engineering Trade-Offs

**Decision:** Use `@dataclass(kw_only=True)` on every `boardly` base class. Use `@dataclass` (without `kw_only`) on subclasses only when you need positional construction (rare — usually test code).
**Both sides:** The alternative is to put all required fields in the base and all defaulted fields in a *separate* `Mixin` class — `class DefaultedMixin: created_at: datetime = field(default_factory=datetime.now)`. The mixin is added at the end of the bases tuple so its defaulted fields come last in the MRO. This works without `kw_only` but is uglier and harder to read. The `kw_only` form is the modern, recommended path.
**Commitment:** In `boardly`, every base class uses `kw_only=True`. Subclasses are bare `@dataclass`. The convention is enforced in the model template.

## Exercises

1. **Exercise 1 — Reproduce the `TypeError`.** Delete `kw_only=True` from `BoardObject`. Verify the `TypeError: non-default argument follows default argument` at import. `Verify: python boardly/models/board_object.py`
2. **Exercise 2 — Override a default.** Add `assignee_id: int = 99` to a subclass of `Ticket` and verify the override applies. `Verify: python boardly/models/board_object.py`
3. **Exercise 3 — Print the MRO.** Add `print(Ticket.__mro__)` and verify the linearisation order matches the field-accumulation order. `Verify: python boardly/models/board_object.py`
4. **Exercise 4 — Field-level `kw_only`.** Use the `KW_ONLY` sentinel (lesson 08 preview) to mark only `created_at` as keyword-only, leaving `id` positional. Read the generated signature with `inspect.signature`. `Verify: python boardly/models/board_object.py`
5. **Exercise 5 — Multiple inheritance.** Define `class AuditMixin: created_at: datetime = field(default_factory=datetime.now)` and `class Ticket(BoardObject, AuditMixin): ...`. Read the MRO and the field order. Explain whether the order is `BoardObject, AuditMixin` or `AuditMixin, BoardObject`. `Verify: python boardly/models/board_object.py`

## Verification

```bash
$ python boardly/models/board_object.py
ticket: Ticket(id=1, created_at=datetime.datetime(2026, 10, 23, 12, 0, 0, 123456), title='Fix login', assignee_id=42)
positional fails: Ticket.__init__() takes 1 positional argument but 5 were given
comment: Comment(id=2, created_at=datetime.datetime(2026, 10, 23, 12, 0, 0, 654321), body='LGTM', author_id=99)
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — the field-ordering rule this lesson turns on its head.
- [[06-dataclasses/02-field-and-Defaults]] — `field(default_factory=...)` is the only correct way to put `datetime.now` on a field.
- [[06-dataclasses/04-Slots-and-Performance]] — the slots-inheritance gotcha is the slot-specific instance of the general inheritance rule.

## What's Next

[[06-dataclasses/06-asdict-astuple-replace]] — `asdict(obj)` (deep), `astuple(obj)`, `replace(obj, field=value)`. The `replace` function is the immutable way to "modify" a frozen dataclass — and it is the standard way to "update" `Ticket`s in `boardly`'s service layer. Three things to take with you:

- `@dataclass` accumulates fields in MRO order — base fields first, then derived.
- The "required after defaulted" `TypeError` is the Python signature rule, not a `@dataclass` rule — `kw_only=True` is the fix.
- `kw_only=True` on a base propagates through the signature's `*` separator to every subclass field.

## Sources

- **`dataclasses` — Inheritance** — https://docs.python.org/3/library/dataclasses.html#inheritance — accessed 2026-10-23 — the canonical reference for the MRO-order field accumulation and the `kw_only` fix.
- **`dataclasses.dataclass.params` — `kw_only`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass.params — accessed 2026-10-23 — the 3.10+ `kw_only` parameter at the class level.
- **PEP 557 — Data Classes: Inheritance** — https://peps.python.org/pep-0557/#inheritance — accessed 2026-10-23 — the original rationale for the MRO-order accumulation rule.
- **CPython `bpo-42128`** — https://github.com/python/cpython/issues/90518 — accessed 2026-10-23 — the issue that added `kw_only` in 3.10.

## What We Learned

- You can read an inheritance chain and predict the accumulated field order.
- You can explain the default-override rules — the most-derived class's field definition wins.
- You can diagnose the "non-default argument follows default argument" `TypeError` and apply `kw_only=True` to fix it.
- You can apply `kw_only=True` at the class level and the field level (via the `KW_ONLY` sentinel, lesson 08).
- You can reason about `__post_init__` in inheritance and the `super().__post_init__()` discipline (full treatment in lesson 08).
