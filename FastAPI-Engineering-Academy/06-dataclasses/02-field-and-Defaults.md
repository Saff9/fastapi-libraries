---
title: "Lesson 02: field() and Defaults"
aliases:
 - dataclass field
 - default_factory
 - field and Defaults
tags:
 - dataclasses
 - canonical
status: complete
course_level: beginner
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
 - "[[06-dataclasses/08-KW_ONLY-and-InitVar]]"
first_taught_in: "06-dataclasses/02-field-and-Defaults"
---

# Lesson 02: field() and Defaults

*Why `tags: list[str] = []` is forbidden in `boardly`'s `Ticket`, what `field(default_factory=list)` does instead, and how the `metadata` dict is the bridge to FastAPI's `Field`.*

**You're at the very beginning of Section 06, second lesson in.**

You finished lesson 01 and you can write a `@dataclass` with confidence. The moment you add the second model — `Ticket` with a `tags: list[str]` field — you hit the wall every student hits: `ValueError: mutable default <class 'list'> for field tags is not allowed: use default_factory`. The error is the friendly version. The unfriendly version, before `@dataclass` existed, was a silent bug where every `Ticket` instance shared one `tags` list and a `.append()` on one mutated every other. `field()` is the standard-library fix — and it is also the bridge to Pydantic's `Field()` and FastAPI's `Field()`, because the API surface is deliberately identical. This lesson walks `field()` in full so the rest of the section can refer to it without re-explaining.

#dataclasses #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `field(default_factory=...)`** to give a field a fresh mutable default per instance.
2. **Explain the mutable-default trap** — why `[]` and `{}` are forbidden, what mechanism `@dataclass` uses to catch them, and what would happen if it did not.
3. **Control each `field()` knob** — `default`, `default_factory`, `init`, `repr`, `compare`, `hash`, `metadata`, `kw_only` — and name the runtime effect of each.
4. **Use the `metadata` dict** to carry per-field configuration that frameworks (FastAPI, Pydantic, your ORM) read at introspection time.
5. **Map `dataclasses.field` to `pydantic.Field`** — name the parameters they share, the ones Pydantic adds, and the design reason for the parallel surface.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. You need to know how the decorator reads `__annotations__` and generates `__init__`.
- **`Annotated`** — [[01-typing/02-Annotated-and-Metadata]] is recommended. The `metadata` dict on `field()` and the `Annotated[T, metadata]` typing construct solve the same problem at different layers; seeing both side by side is the fastest way to internalise either.
- **About 35–50 minutes of focused time.**

**The most common gap: the mutable-default trap.**

Students arrive at `field()` believing it is just a default-value shortcut. It is not — `field()` is the only legal way to put a *mutable* default on a field, and the `default_factory` parameter exists precisely because mutable defaults are a footgun. The trap predates `@dataclass`: `def f(x=[]):` and `class C: x = []` both share one list across all callers/instances. `@dataclass` is the rare standard-library feature that *refuses to let you* repeat the trap; lesson 01's Mistake 2 was the preview.

## The Problem

You add the `Ticket` model to `boardly`. A ticket has a `title`, an `assignee_id`, and a list of `tags`. The natural first attempt is:

```python
@dataclass
class Ticket:
    id: int
    title: str
    assignee_id: int
    tags: list[str] = []
```

This raises `ValueError` at import time — `@dataclass` refuses to generate the class. The error message tells you to `use default_factory`, which is the fix, but it does not tell you *why* the trap is dangerous enough to justify an import-time hard refusal. Here is the why: before `@dataclass`, the equivalent class would have written `self.tags = []` in `__init__` — but only if the user remembered to write it. The mutable-default version above, if `@dataclass` accepted it, would put *one* list object on the class, shared by every `Ticket` instance, so `Ticket(id=1).tags.append("bug")` would mutate `Ticket(id=2).tags`. That is exactly the bug the standard library is supposed to prevent — and `field(default_factory=list)` is the prevention.

## The Code

```python
# boardly/models/ticket.py
"""boardly Ticket model — field() and defaults."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: list[str] = field(default_factory=list)
    watchers: set[int] = field(default_factory=set, repr=False)
    priority: int = field(default=3, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict, metadata={"json_key": "meta"})


if __name__ == "__main__":
    t1 = Ticket(id=1, title="Fix login bug", assignee_id=42)
    t1.tags.append("urgent")
    t1.watchers.add(42)

    t2 = Ticket(id=2, title="Ship MVP", assignee_id=99)
    print("t1.tags:", t1.tags)
    print("t2.tags:", t2.tags)
    print("t1 == t2 modified:", t1 == Ticket(id=1, title="Fix login bug", assignee_id=42, tags=["urgent"], watchers={42}))
    print("repr:", repr(t1))
    print("fields:", [f.name for f in __import__("dataclasses").fields(t1)])
    print("priority field metadata:", Ticket.__dataclass_fields__["priority"].metadata)
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports

```python
# boardly/models/ticket.py
"""boardly Ticket model — field() and defaults."""
from dataclasses import dataclass, field
from typing import Any
```

`field` is imported from `dataclasses` alongside `dataclass`. The full signature is `def field(*, default=MISSING, default_factory=MISSING, init=True, repr=True, hash=None, compare=True, metadata=None, kw_only=MISSING): ...`. Every parameter is keyword-only (note the leading `*` in the signature — there is no positional-only marker `/`). The keyword-only rule is for the same reason as `@dataclass`: future arguments can be appended without breaking callers. `MISSING` is a sentinel: it is *not* `None`, because `None` is a legitimate default value (`archived: Optional[bool] = None`). `MISSING` means "no default at all — required field". The first parameter `default` is keyword-only too — you must write `field(default=3)`, not `field(3)`.

### Lines 8–15: The Ticket fields

```python
@dataclass
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: list[str] = field(default_factory=list)
    watchers: set[int] = field(default_factory=set, repr=False)
    priority: int = field(default=3, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict, metadata={"json_key": "meta"})
```

The first three fields use the *plain default* form: `assignee_id: int = 0` is a plain class attribute that `@dataclass` reads from `__dict__`. This works because `0` is immutable — `int`, `str`, `bool`, `tuple`, `frozenset`, `None` are all safe. The next four use `field()`. `tags` and `watchers` use `default_factory` because `list` and `set` are mutable. `priority` uses `default=3` — equivalent to `priority: int = 3` but explicit; we add `compare=False` so two `Ticket`s with the same `id`/`title`/`assignee_id`/`tags`/`watchers` compare equal even if their `priority` differs. `metadata` uses both `default_factory=dict` and `metadata={"json_key": "meta"}` — the inner `metadata` dict is the per-field configuration bag a framework can read.

**Why does `field()` separate `default` and `default_factory`?**

Because `default` must be the value itself, and `default_factory` must be a *callable* that returns a fresh value each call. If `field(default=[])` were allowed, `@dataclass` would still have the shared-list bug. If `field(default_factory=[])` were allowed, `@dataclass` would call `[]()` at construction time — and `[]()` is a `TypeError` because lists are not callable. The two parameters are different shapes on purpose: `default` takes the value, `default_factory` takes a zero-argument callable that builds the value. The factory is called once per `__init__` call, so every instance gets its own list.

### Lines 16–24: The sanity check

```python
if __name__ == "__main__":
    t1 = Ticket(id=1, title="Fix login bug", assignee_id=42)
    t1.tags.append("urgent")
    t1.watchers.add(42)

    t2 = Ticket(id=2, title="Ship MVP", assignee_id=99)
    print("t1.tags:", t1.tags)
    print("t2.tags:", t2.tags)
```

`t1.tags.append("urgent")` mutates `t1.tags` only. Because `tags` uses `default_factory=list`, the `__init__` for `t1` called `list()` (i.e., `[]`) and assigned the new list to `self.tags`. The `__init__` for `t2` called `list()` again — a *different* list — and assigned it to `t2.tags`. The two lists are independent. `print(t2.tags)` shows `[]`, proving the isolation.

**Why does `@dataclass` reject `tags: list[str] = []` at import time but `tags: list[str] = field(default_factory=list)` works?**

Because `@dataclass` has an explicit check at field-construction time: it walks the field's default value, and if the value is one of `list`, `dict`, `set`, `bytearray`, or any class whose `__hash__` is `None` (i.e., mutable), it raises `ValueError`. The check is in `_HAS_DEFAULT_FACTORY`-adjacent logic in `Lib/dataclasses.py`. The reason for the hard refusal — rather than a warning — is that the bug is silent, slow, and expensive to debug in production. A `Warning` would not be enough; engineers ignore `Warning`s. The hard `ValueError` at import time forces the fix at the moment of authoring, which is the cheapest moment to fix it.

### Lines 25–26: The equality comparison

```python
    print("t1 == t2 modified:", t1 == Ticket(id=1, title="Fix login bug", assignee_id=42, tags=["urgent"], watchers={42}))
```

This constructs a fresh `Ticket` with all fields explicit — including `tags=["urgent"]` and `watchers={42}` — and compares it to `t1`. The `==` operator calls the generated `__eq__`, which compares the fields marked `compare=True` (default for every field except `priority`, where we set `compare=False`). The `priority` field is excluded from the comparison tuple, so the two instances compare equal even though `t1.priority` (3, the default) and the new instance's `priority` (also 3, the default) — wait, they are the same here. Construct a second instance with `priority=99` and the comparison still returns `True`, because `compare=False` excluded `priority` from the tuple entirely.

**Why would you set `compare=False` on a field?**

Two reasons. First, when a field is genuinely not part of identity — a cache, a timestamp, a transient flag. Second, when the field is unhashable and you want to keep the rest of the instance hashable (when combined with `frozen=True`, see lesson 03). `compare=False` also implies `hash=False` for that field — `@dataclass` uses the `compare` setting as the source of truth for the `__hash__` field set unless you override `hash` explicitly.

### Lines 27–28: `repr=False` and the field introspection

```python
    print("repr:", repr(t1))
    print("fields:", [f.name for f in __import__("dataclasses").fields(t1)])
```

`repr(t1)` calls the generated `__repr__`, which builds a string from every field where `repr=True`. We set `watchers` to `repr=False`, so the output omits the `watchers={42}` field. The `fields(t1)` call returns a tuple of `Field` objects — one per field — and the list comprehension extracts the names. `fields()` is the introspection API; Pydantic's introspection of `@dataclass`-based models (via `pydantic.dataclasses.dataclass`) walks this same `Field` tuple.

### Lines 29–30: Reading the metadata back

```python
    print("priority field metadata:", Ticket.__dataclass_fields__["priority"].metadata)
```

`Ticket.__dataclass_fields__` is a dict mapping field name → `Field` object that `@dataclass` stores on the class at decoration time. The `metadata` attribute is a `types.MappingProxyType` — a read-only view of the dict you passed in. A framework reads it via `f.metadata.get("json_key")` to find per-field configuration. This is the bridge to FastAPI's `Field()` and Pydantic's `Field()` — both use the same pattern, just with extra parameters.

**Why is `metadata` a read-only `MappingProxyType` rather than the raw dict?**

Because if it were the raw dict, a framework could mutate it accidentally and corrupt the field configuration for every other framework reading the same model. The `MappingProxyType` is a defensive copy at the API surface: it lets frameworks read but not mutate. The pattern recurs across the standard library (`os.environ` is a `MappingProxyType`-shaped object; `types.MappingProxyType` is the underlying type); it is the safe way to expose an internal dict to callers you do not trust.

## Execution Trace

```bash
$ python boardly/models/ticket.py
t1.tags: ['urgent']
t2.tags: []
t1 == t2 modified: True
repr: Ticket(id=1, title='Fix login bug', assignee_id=42, tags=['urgent'], priority=3, metadata={})
fields: ['id', 'title', 'assignee_id', 'tags', 'watchers', 'priority', 'metadata']
priority field metadata: {}
```

Note four things. First, `t2.tags` is `[]` — the lists are independent. Second, the comparison returns `True` because `priority` was excluded from the comparison tuple. Third, the `repr` omits `watchers` because of `repr=False`. Fourth, `priority`'s metadata is `{}` — we did not set any metadata on `priority`, only on the `metadata` field — and the empty dict is the `MappingProxyType` default.

## Common Mistakes

### Mistake 1: Using `default_factory` with a non-callable

```python
@dataclass
class Ticket:
    tags: list[str] = field(default_factory=[])
```

**Symptom:** `TypeError: 'list' object is not callable` at the first `Ticket(...)` call.
**Why:** `default_factory` must be a zero-argument callable. `[]` is a list literal, not a callable. `@dataclass` evaluates `factory()` at `__init__` time — `[]()` is a `TypeError`.
**Fix:** `field(default_factory=list)` — `list` *is* callable and returns a fresh `[]`.

### Mistake 2: Setting `default` and `default_factory` together

```python
@dataclass
class Ticket:
    tags: list[str] = field(default=[], default_factory=list)
```

**Symptom:** `ValueError: cannot specify both default and default_factory`.
**Why:** The two parameters are mutually exclusive — a field has either a single value or a factory that builds one. `@dataclass` enforces this at decoration time.
**Fix:** Pick one. For mutable types, use `default_factory`. For immutable types, `default=` is fine.

### Mistake 3: Mutable default passed in via `default`

```python
@dataclass
class Ticket:
    extras: dict = field(default={})
```

**Symptom:** `ValueError: mutable default <class 'dict'> for field extras is not allowed: use default_factory`.
**Why:** `@dataclass` runs the same mutable-default check on `field(default=...)` that it runs on plain `extras: dict = {}`. The check fires regardless of whether you used the bare form or `field(default=...)`.
**Fix:** `field(default_factory=dict)`.

## Engineering Trade-Offs

**Decision:** Use `field(default_factory=...)` for every mutable default. Use plain `= value` only for immutable defaults. Use `compare=False` for cache/transient fields. Use `repr=False` only when the field's repr is noisy (large lists, secret values).
**Both sides:** The alternative to `default_factory` is to use `None` as the default and convert in `__post_init__`: `tags: list[str] | None = None` then `def __post_init__(self): self.tags = self.tags or []`. This works but is noisier and loses the type-checker's guarantee that `tags` is always a list. The `default_factory` form is shorter, type-correct, and the one every modern codebase uses.
**Commitment:** In `boardly`, mutable defaults use `field(default_factory=...)` exclusively — never `None`-then-coerce, never bare mutable literal. The convention is enforced by code review.

## Exercises

1. **Exercise 1 — Add `comments`.** Add `comments: list[str] = field(default_factory=list)` to `Ticket`. Verify `t1.comments.append("hi")` does not affect `t2.comments`. `Verify: python boardly/models/ticket.py`
2. **Exercise 2 — `compare=False` on `metadata`.** Set `compare=False` on the `metadata` field. Construct two `Ticket`s with identical fields except different `metadata` contents; verify they still compare equal. `Verify: python boardly/models/ticket.py`
3. **Exercise 3 — Custom factory.** Change `tags` to `field(default_factory=lambda: ["new"])`. Verify `t1.tags` is `['new']` on construction. `Verify: python boardly/models/ticket.py`
4. **Exercise 4 — Read `__dataclass_fields__`.** Iterate `Ticket.__dataclass_fields__.items()` and print `name, default, default_factory, repr, compare, metadata` for each field. Explain why `default_factory` is `MISSING` for `id`. `Verify: python boardly/models/ticket.py`
5. **Exercise 5 — Pydantic parallel.** Install pydantic if available and write the equivalent `class TicketModel(BaseModel): tags: list[str] = Field(default_factory=list)`. Note the identical parameter name. (If pydantic is unavailable, read its source: `pydantic/fields.py`.) `Verify: python -c "import pydantic; print(pydantic.Field.__doc__[:200])"`

## Verification

```bash
$ python boardly/models/ticket.py
t1.tags: ['urgent']
t2.tags: []
t1 == t2 modified: True
repr: Ticket(id=1, title='Fix login bug', assignee_id=42, tags=['urgent'], priority=3, metadata={})
fields: ['id', 'title', 'assignee_id', 'tags', 'watchers', 'priority', 'metadata']
priority field metadata: {}
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — `@dataclass` reads `__annotations__`; this lesson builds on that to show how `field()` augments each annotation.

## What's Next

[[06-dataclasses/03-Frozen-and-Immutability]] — `@dataclass(frozen=True)`, the generated `__hash__`, why frozen implies hashable, and `FrozenInstanceError`. The `compare`/`hash` settings from this lesson become the foundation for the frozen `__hash__` generation in lesson 03. Three things to take with you:

- `field(default_factory=callable)` is the only legal way to give a field a mutable default.
- `compare=False` removes a field from both `__eq__` and `__hash__`; `repr=False` removes it from `__repr__`; `init=False` removes it from `__init__` (we did not cover it here — covered in lesson 08 alongside `InitVar`).
- `metadata={...}` is the per-field configuration bag — the bridge to FastAPI and Pydantic.

## Sources

- **`dataclasses.field` — API reference** — https://docs.python.org/3/library/dataclasses.html#dataclasses.field — accessed 2026-10-23 — the canonical reference for every `field()` parameter.
- **`dataclasses.fields` — introspection helper** — https://docs.python.org/3/library/dataclasses.html#dataclasses.fields — accessed 2026-10-23 — the function FastAPI and Pydantic use to read a dataclass's fields.
- **PEP 557 — Data Classes: field()** — https://peps.python.org/pep-0557/#class-variables — accessed 2026-10-23 — the section that justifies the mutable-default hard refusal.
- **Pydantic Field() — API** — https://docs.pydantic.dev/latest/concepts/fields/ — accessed 2026-10-23 — the parallel API surface; `default_factory` is parameter-identical.

## What We Learned

- You can use `field(default_factory=...)` to give a field a fresh mutable default per instance.
- You can explain the mutable-default trap and the import-time `ValueError` `@dataclass` raises to prevent it.
- You can control every `field()` knob — `default`, `default_factory`, `init`, `repr`, `compare`, `hash`, `metadata`, `kw_only`.
- You can use the `metadata` dict to carry per-field configuration a framework can introspect.
- You can map `dataclasses.field` to `pydantic.Field` and name the parameters they share.
