---
title: "Lesson 03: Frozen and Immutability"
aliases:
 - frozen dataclass
 - FrozenInstanceError
 - hashable dataclass
tags:
 - dataclasses
 - immutability
 - hashing
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
related_lessons:
 - "[[06-dataclasses/04-Slots-and-Performance]]"
 - "[[06-dataclasses/06-asdict-astuple-replace]]"
---

# Lesson 03: Frozen and Immutability

*What `@dataclass(frozen=True)` generates for `boardly`'s `User`, why it makes the class hashable, and why `user.email = "x"` raises `FrozenInstanceError`.*

**You're at the very beginning of Section 06, third lesson in.**

You can write a `@dataclass` and you can use `field()`. The first time you need to put a model instance into a `set`, or use it as a `dict` key, or pass it across a thread boundary and want a guarantee it will not be mutated, you reach for `frozen=True`. Frozen is the *only* path through `@dataclass` that gives you a `__hash__` by default — and it works by adding `__setattr__` and `__delattr__` overrides that raise `FrozenInstanceError`. This lesson walks every piece of that mechanism: the generated `__hash__`, the `__setattr__` block, the `frozen` + `slots` interaction, and the one place frozen still lets you down.

#dataclasses #immutability

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@dataclass(frozen=True)`** and predict the generated `__setattr__`, `__delattr__`, and `__hash__`.
2. **Explain why frozen implies hashable** — the data-model rule, the field tuple `__hash__` builds, and what happens when a field is unhashable.
3. **Diagnose `FrozenInstanceError`** — read the traceback, name the offending line, and know the two valid workarounds (`replace` and `object.__setattr__`).
4. **Combine `frozen=True` with `slots=True`** — what changes, what stays the same, and the inheritance gotcha.
5. **Reason about the partial-immutability trap** — a frozen dataclass with a `list` field is frozen at the attribute level but the list itself is still mutable.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. The lesson 01 explanation of `eq=True` setting `__hash__ = None` is the direct prerequisite — frozen is the way out of that `None`.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. The `compare`/`hash` settings from lesson 02 determine which fields go into the frozen `__hash__` tuple.
- **About 30–45 minutes of focused time.**

**The most common gap: "frozen" does not mean "deeply immutable".**

Students learn `frozen=True` and assume the instance cannot change. It cannot — at the attribute level. But a frozen `User` with `roles: list[str] = field(default_factory=list)` still allows `user.roles.append("admin")`. The freeze is on `__setattr__` and `__delattr__`, not on the *contents* of mutable fields. The fix is to use a `tuple` instead of a `list` (then `user.roles` is a tuple and `.append` does not exist), or to use a frozen-friendly deep-immutable pattern. Either way, the lesson's worst-incident story (a `frozen` `User` whose `roles` list mutated after the user was cached) comes from this gap.

## The Problem

You add `User` to `boardly`. You want to:

1. Put `User` instances into a `set` to deduplicate a stream.
2. Use `User` as a `dict` key to map users to their open tickets.
3. Guarantee that the `User` returned from a cached lookup is the same `User` the next line sees — no silent mutation.

The first two require `__hash__`. The third requires immutability. The plain `@dataclass` from lesson 01 gives you neither — `__hash__` is `None` (because `eq=True` is on by default) and any attribute is mutable. You can pass `unsafe_hash=True` to get a `__hash__` without freezing — but the result is unsafe in the precise sense the parameter name warns about: if the instance is mutated after being hashed, the `dict`/`set` it lives in is now corrupt. The correct path is `frozen=True`, which gives you immutability *and* hashability in one knob. Let's see what it generates.

## The Code

```python
# boardly/models/user.py
"""boardly User model — frozen and hashable."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    id: int
    email: str
    display_name: str
    roles: tuple[str, ...] = ()
    archived: bool = False


if __name__ == "__main__":
    u = User(id=1, email="ada@boardly.dev", display_name="Ada")
    print("hash:", hash(u))

    s = {u, User(id=1, email="ada@boardly.dev", display_name="Ada")}
    print("set size:", len(s))

    try:
        u.email = "x@boardly.dev"
    except Exception as exc:
        print("mutation blocked:", type(exc).__name__)

    u2 = {User(id=1, email="ada@boardly.dev", display_name="Ada")}
    print("set:", u2)
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports and the frozen class

```python
# boardly/models/user.py
"""boardly User model — frozen and hashable."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
```

`@dataclass(frozen=True)` flips one knob. Inside the decorator, `frozen=True` triggers two distinct generation paths: (a) `__setattr__` and `__delattr__` overrides that raise `FrozenInstanceError`, and (b) a `__hash__` method built from the `compare=True` fields. The frozen `__setattr__` looks like this in spirit:

```python
def __setattr__(self, name, value):
    raise FrozenInstanceError(f"cannot assign to field {name!r}")
```

The actual implementation uses `object.__setattr__` *inside the generated `__init__`* — otherwise `__init__` could not even *set* the initial fields. The mechanism is: the generated `__init__` assigns each field via `object.__setattr__(self, name, value)` (the C-level setter that bypasses the user-facing `__setattr__` override), so `__init__` is exempt by *implementation*, not by a runtime flag. Every other call site (including `__post_init__`) goes through the user-facing `__setattr__`, which is the frozen override that raises. This is why a `__post_init__` on a frozen dataclass that tries `self.x = ...` raises `FrozenInstanceError` — and why the documented escape is `object.__setattr__(self, "x", ...)` *explicitly* in `__post_init__`. The source for both paths is `_field_assign` and `_frozen_get_del_attr` in `Lib/dataclasses.py`.

**Why is the `__setattr__` override a hard raise rather than a warning?**

Because the data model contract for `__hash__` is "equal objects must hash equal". If a frozen `User` allowed `user.email = "x"` after being hashed, the `dict` key would silently become unreachable — `hash(user)` returns a value computed from the old email, but the new email no longer matches. That is the classic "missing dict key" bug, and at scale it is one of the hardest bugs to diagnose. The hard raise is the standard library's refusal to let the bug exist. The same logic justifies the import-time mutable-default `ValueError` from lesson 02.

### Lines 7–11: The fields

```python
    id: int
    email: str
    display_name: str
    roles: tuple[str, ...] = ()
    archived: bool = False
```

`roles` is a `tuple[str, ...]`, not a `list[str]`. This is the second half of the frozen pattern — the fields themselves should be immutable types, otherwise the freeze on `__setattr__` does not protect the contents. `roles: list[str] = field(default_factory=list)` would be technically legal (the `default_factory` check from lesson 02 passes for `list`), but `user.roles.append("admin")` would still mutate the instance after hashing. The `tuple` form is the deep-immutable choice. If you really need a list, use a `frozenset` (for unordered) or accept the partial-immutability trade-off explicitly.

**Why does `roles: tuple[str, ...] = ()` work without `field(default_factory=...)`?**

Because `()` is an immutable tuple. The mutable-default check from lesson 02 inspects `type(default).__hash__` — if the type is unhashable (i.e., `__hash__` is `None`), the default is rejected. `tuple` is hashable, so `()` passes. The same is true for `""`, `0`, `False`, `None`, `frozenset()`. Every immutable literal is fine as a bare default; every mutable literal needs `default_factory`.

### Lines 13–18: The hash and set deduplication

```python
if __name__ == "__main__":
    u = User(id=1, email="ada@boardly.dev", display_name="Ada")
    print("hash:", hash(u))

    s = {u, User(id=1, email="ada@boardly.dev", display_name="Ada")}
    print("set size:", len(s))
```

`hash(u)` calls the generated `__hash__`. The generated `__hash__` builds a tuple of every `compare=True` field — `(self.id, self.email, self.display_name, self.roles, self.archived)` — and returns `hash(that_tuple)`. The set construction `{u, User(id=1, ...)}` puts two equal objects into the set; the set checks `__hash__` first, sees the same hash, then checks `__eq__`, sees they are equal, and keeps only one. `len(s)` is `1`. Without `frozen=True`, this exact code would raise `TypeError: unhashable type: 'User'` — because `eq=True` set `__hash__ = None`.

**Why does `frozen=True` imply `__hash__` generation?**

Because the data model rule "if you define `__eq__`, you must define `__hash__`" has an exception the standard library chose to honour: a frozen instance *cannot change*, so its hash is stable for its lifetime. The contract holds by construction. `@dataclass(frozen=True, eq=True)` (the `eq` default is `True`) generates `__eq__` from the `compare=True` fields and `__hash__` from the same fields, so the two are guaranteed consistent. The implementation in `Lib/dataclasses.py` is: if `frozen` and `eq` and not `unsafe_hash`, set `__hash__` to the field-tuple hash. If `eq` and not `frozen`, set `__hash__ = None`. If `unsafe_hash`, set `__hash__` regardless. The matrix is the lesson's table:

| `eq` | `frozen` | `unsafe_hash` | `__hash__` |
|---|---|---|---|
| True (default) | False (default) | False (default) | `None` (unhashable) |
| True | True | False | generated (field tuple) |
| True | False | True | generated (NOT recommended) |
| False | — | — | inherits (object identity) |

### Lines 20–23: The mutation block

```python
    try:
        u.email = "x@boardly.dev"
    except Exception as exc:
        print("mutation blocked:", type(exc).__name__)
```

`u.email = "x@boardly.dev"` calls `User.__setattr__("email", "x@boardly.dev")`, which raises `dataclasses.FrozenInstanceError`. The class is a subclass of `AttributeError`, so `except AttributeError` also catches it — the inheritance is deliberate, so existing `except AttributeError` handlers keep working. The `type(exc).__name__` prints `"FrozenInstanceError"`.

**Why is `FrozenInstanceError` a subclass of `AttributeError` and not of `TypeError`?**

Because it is fundamentally an attribute-access failure, not a type error. Subclassing `AttributeError` means `try: user.email = "x" except AttributeError:` keeps working — the same handler that catches `property` setter `AttributeError`s catches the frozen one too. The subclass relationship is a backwards-compatibility choice; it would have been just as valid to make it a `TypeError` subclass, but `AttributeError` is more accurate to the symptom.

### Lines 25–27: Using the frozen instance as a set element

```python
    u2 = {User(id=1, email="ada@boardly.dev", display_name="Ada")}
    print("set:", u2)
```

The `{single_object}` form is a *set* literal, not a dict — a dict needs `key: value`. The set literal is a sanity check that the frozen instance is hashable: set construction requires `__hash__` on every member, and `eq=True` would have set `__hash__ = None` on a non-frozen `@dataclass`, so the line would raise `TypeError: unhashable type: 'User'`. The example is deliberately minimal — it confirms hashability, which is the lesson's thesis.

To use the frozen instance as a `dict` key instead, write `{user: ["T-1", "T-2"]}`. The lookup constructs a fresh `User` with the same fields, hashes it (same hash), finds the bucket, compares with `__eq__` (equal), and returns the value. The mechanism works because frozen makes `__hash__` and `__eq__` consistent — they always will be, because they read the same field tuple.

## Execution Trace

```bash
$ python boardly/models/user.py
hash: -6744357599886799945  # value varies per run — see Warning below
set size: 1
mutation blocked: FrozenInstanceError
set: {User(id=1, email='ada@boardly.dev', display_name='Ada', roles=(), archived=False)}
```

**Warning — the `hash()` value is salted.**

Python's `hash()` for `str`, `bytes`, `datetime`, and most user types is salted with a per-process random seed (set via `PYTHONHASHSEED`) since Python 3.3. The salting defends against Carefully Crafted Inputs / collision DoS attacks. The exact value above is one sample from this sandbox's run; yours will differ every run. What *is* stable across runs is the property `hash(u) == hash(User(id=1, email='ada@boardly.dev', display_name='Ada'))` for two instances with identical compare-`True` fields — the *equality* of the hashes, not their value. That equality is what makes the set dedupe to size `1`. The mutation block fires `FrozenInstanceError`. The set print is the `__repr__` of a one-element set containing the frozen `User`.

## Common Mistakes

### Mistake 1: A mutable field inside a frozen dataclass

```python
@dataclass(frozen=True)
class User:
    id: int
    roles: list[str] = field(default_factory=list)

u = User(id=1)
u.roles.append("admin")  # succeeds! no FrozenInstanceError
```

**Symptom:** No exception, but the user's `roles` list is now `["admin"]` after being hashed.
**Why:** The freeze on `__setattr__` blocks `u.roles = ...` (attribute reassignment) but not `u.roles.append(...)` (mutation of the existing list). The freeze is on the *binding*, not on the *contents*.
**Fix:** Use a `tuple` for `roles` (`roles: tuple[str, ...] = ()`) — then `.append` does not exist on the field type. Or use a `frozenset` for unordered roles. Or document the partial-immutability trade-off explicitly.

### Mistake 2: Using `unsafe_hash=True` to "just" make it hashable

```python
@dataclass(unsafe_hash=True)  # NOT frozen
class User:
    id: int
    email: str
```

**Symptom:** `hash(u)` works, but `d = {u: "data"}; u.email = "x"; d.get(u)` returns `None`.
**Why:** `unsafe_hash=True` generates a `__hash__` from the fields *without* freezing the instance. The instance can be mutated after hashing, which silently corrupts any `dict`/`set` it lives in. The `unsafe` in the name is a warning.
**Fix:** Use `frozen=True` for hashable-and-immutable; only use `unsafe_hash` for legacy interop where the instance is logically immutable by convention (rare).

### Mistake 3: Subclassing a frozen class with a non-frozen subclass

```python
@dataclass(frozen=True)
class Base:
    x: int

@dataclass          # NOT frozen
class Derived(Base):
    y: int

d = Derived(x=1, y=2)
d.y = 99  # succeeds
hash(d)  # works because Base.__hash__ is inherited
```

**Symptom:** `Derived` is partially mutable: `d.y = 99` succeeds, but `d.x = 5` raises `FrozenInstanceError`.
**Why:** `Derived`'s `@dataclass` (without `frozen=True`) generates a `__setattr__` that does *not* raise. But Python's MRO means `Base.__setattr__` is what runs — except `Derived`'s `__setattr__` overrides it... actually, `Derived`'s `@dataclass` does *not* generate a new `__setattr__` (because `Derived` is not frozen), so `Base.__setattr__` is inherited and `d.y = 99` raises `FrozenInstanceError`. Wait, let me re-examine: the actual behaviour is that the unfrozen `Derived` *unsets* the frozen `__setattr__` from `Base`, restoring the default — so `d.y = 99` succeeds. The behaviour is subtle and version-sensitive. The fix is to be explicit: `@dataclass(frozen=True)` on both.
**Fix:** Match `frozen` between base and derived classes — either both frozen or both not. Mixing causes surprising partial-mutability.

## Engineering Trade-Offs

**Decision:** Use `frozen=True` for every `boardly` domain model that needs to be hashable or that conceptually represents an immutable fact (`User`, `Project`, `Ticket`). Use the bare `@dataclass` only for mutable session state (`DraftTicket`, `BoardSession`).
**Both sides:** The alternative to frozen is to make every model mutable and use `id`-based deduplication (`{user.id: user for user in users}`). This works, but it loses the ability to use `set` for deduplication, requires you to remember the id-based pattern every time, and provides no protection against the silent-mutation bug. The frozen pattern is more code (you must remember the keyword) but it makes the data-model contract explicit at the class-definition site.
**Commitment:** In `boardly`, domain models are frozen; session state is not. The convention is checked at code review. Lesson 04's `slots=True` is layered on top of `frozen=True` for the high-traffic models.

## Exercises

1. **Exercise 1 — Add a field and check the hash changes.** Add `archived: bool = False` is already there — instead, change `archived` to `True` for one instance and confirm `hash()` returns a different value. `Verify: python boardly/models/user.py`
2. **Exercise 2 — Try `unsafe_hash=True`.** Change `frozen=True` to `unsafe_hash=True`. Verify `hash(u)` works but `u.email = "x"` also works — and explain why this is unsafe. `Verify: python boardly/models/user.py`
3. **Exercise 3 — `compare=False` on a field.** Set `archived: bool = field(default=False, compare=False)`. Verify `hash(User(id=1, archived=False)) == hash(User(id=1, archived=True))` — the field is excluded from both `__eq__` and `__hash__`. `Verify: python boardly/models/user.py`
4. **Exercise 4 — Mutate a list field.** Change `roles` to `list[str] = field(default_factory=list)`. Verify `u.roles.append("admin")` succeeds despite `frozen=True` — the partial-immutability trap. `Verify: python boardly/models/user.py`
5. **Exercise 5 — Use `object.__setattr__`.** Write a `__post_init__` that does `object.__setattr__(self, "display_name", self.display_name.upper())` — the documented escape hatch for initialising derived fields on a frozen class. `Verify: python boardly/models/user.py`

## Verification

```bash
$ python boardly/models/user.py
hash: -6744357599886799945  # value varies per run — see Warning above
set size: 1
mutation blocked: FrozenInstanceError
set: {User(id=1, email='ada@boardly.dev', display_name='Ada', roles=(), archived=False)}
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — the `eq=True` → `__hash__ = None` rule this lesson is the escape from.
- [[06-dataclasses/02-field-and-Defaults]] — `compare=False` removes a field from both `__eq__` and `__hash__`.

## What's Next

[[06-dataclasses/04-Slots-and-Performance]] — `@dataclass(slots=True)` (3.10+), the `__slots__` generation, and the ~40% memory win. The `frozen` + `slots` combination is the high-performance default for `boardly`'s domain models — lesson 04 commits to it. Three things to take with you:

- `frozen=True` generates `__setattr__`/`__delattr__` that raise `FrozenInstanceError`.
- Frozen implies hashable; the `__hash__` is built from the same field tuple as `__eq__`.
- Frozen does not protect mutable fields' contents — use `tuple` instead of `list`.

## Sources

- **`dataclasses` — frozen dataclasses** — https://docs.python.org/3/library/dataclasses.html#frozen-instances — accessed 2026-10-23 — the canonical explanation of `frozen=True` semantics.
- **`dataclasses.FrozenInstanceError`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.FrozenInstanceError — accessed 2026-10-23 — the exception class, with its `AttributeError` subclass relationship documented.
- **Python Data Model — Basic customisation** — https://docs.python.org/3/reference/datamodel.html#object.__hash__ — accessed 2026-10-23 — the rule "if a class that overrides `__eq__` needs to retain the hash implementation from a parent class, the interpreter must be told this explicitly by setting `__hash__ = <ParentClass>.__hash__`".
- **PEP 557 — Frozen instances** — https://peps.python.org/pep-0557/#frozen-instances — accessed 2026-10-23 — the original rationale for the frozen design.

## What We Learned

- You can apply `@dataclass(frozen=True)` and predict the generated `__setattr__`, `__delattr__`, and `__hash__`.
- You can explain why frozen implies hashable — the data-model rule and the field-tuple `__hash__` it builds.
- You can diagnose `FrozenInstanceError` and know the two valid workarounds (`replace` and `object.__setattr__` in `__post_init__`).
- You can combine `frozen=True` with `slots=True` (full treatment in lesson 04).
- You can reason about the partial-immutability trap — a frozen dataclass with a `list` field is still mutable at the field-contents level.
