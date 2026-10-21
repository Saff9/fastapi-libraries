---
title: "Lesson 08: KW_ONLY and InitVar"
aliases:
 - KW_ONLY sentinel
 - InitVar
 - post_init lifecycle
tags:
 - dataclasses
 - init
 - lifecycle
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
 - "[[06-dataclasses/05-Inheritance]]"
related_lessons:
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
 - "[[06-dataclasses/06-asdict-astuple-replace]]"
---

# Lesson 08: KW_ONLY and InitVar

*The `KW_ONLY` sentinel (3.10+) that splits a `boardly` `Ticket`'s positional and keyword fields, `InitVar[T]` for init-only fields passed to `__post_init__`, and the full `__post_init__` lifecycle that connects them.*

**You're at the very beginning of Section 06, eighth and final lesson in.**

You finish the section here. The last two pieces of the `@dataclass` API surface are `KW_ONLY` — the sentinel value that, when assigned to a field name, marks every field after it as keyword-only — and `InitVar[T]` — the type annotation that marks a field as init-only, passed to `__post_init__` but never stored on the instance. The two together unlock the `__post_init__` lifecycle: a `Ticket` whose `__init__` takes a `raw_tags: InitVar[str]` (a comma-separated string from the database) and whose `__post_init__` parses it into the `tags: tuple[str, ...]` field stored on the instance. This lesson walks the sentinel, the `InitVar`, and the lifecycle, and closes the section.

#dataclasses #init #lifecycle

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use the `KW_ONLY` sentinel** (Python 3.10+) to split a class's fields into a positional prefix and a keyword-only suffix.
2. **Use `InitVar[T]`** to declare an init-only field — passed to `__init__`, passed to `__post_init__`, never stored on the instance.
3. **Write `__post_init__`** that receives `InitVar` values as positional arguments in declaration order.
4. **Reason about the `__post_init__` lifecycle** — when it runs, what it sees, the `object.__setattr__` escape for frozen classes.
5. **Combine `KW_ONLY`, `InitVar`, and `__post_init__`** in a `Ticket`-from-DB-row pattern that parses raw input on construction.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. The `__init__` generation is what `KW_ONLY` modifies.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. The `kw_only` parameter on `field()` is the per-field version of the sentinel.
- **`kw_only=True` at the class level** — [[06-dataclasses/05-Inheritance]]. Lesson 05's class-level knob is the broad form; this lesson's sentinel is the fine form.
- **`frozen=True`** — [[06-dataclasses/03-Frozen-and-Immutability]]. The `__post_init__` lifecycle interacts with frozen classes through `object.__setattr__`.
- **About 30–45 minutes of focused time.**

**The most common gap: `InitVar` fields don't appear on the instance.**

Students declare `raw_tags: InitVar[str] = ""` on a `Ticket`, call `Ticket(id=1, raw_tags="urgent,bug")`, then try `t.raw_tags` and get the class-level default value (`""` or `None`) — not an instance attribute. The `InitVar` annotation tells `@dataclass` "this field is for `__init__` and `__post_init__` only — do not assign it to `self`". The field is not in `__slots__`, not in the instance's `__dict__`, not in `asdict(t)`'s output, not in `astuple(t)`'s output, not in `replace(t, ...)`'s parameters. The class-level default value remains in `Ticket.__dict__` (a side-effect of the `AnnAssign` form), so `hasattr(t, "raw_tags")` is `True` — but reading `t.raw_tags` returns the class attribute, not an instance attribute. The robust check for "is this an instance attribute?" is `'raw_tags' in __slots__` (slotted) or `'raw_tags' in t.__dict__` (non-slotted), both returning `False`. The lesson walks this fact and the use case (parsing raw input) that motivates it.

## The Problem

You have a `boardly` database row that comes back from `SELECT * FROM tickets` as a `tuple` — `(id, title, assignee_id, raw_tags)` where `raw_tags` is a comma-separated string `"urgent,bug"`. You want to construct a `Ticket` from the row, with `Ticket.tags` as a `tuple[str, ...]` (parsed). The natural attempt:

```python
@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    title: str
    assignee_id: int
    tags: tuple[str, ...] = ()
```

You would have to parse the row before constructing — `Ticket(id=row[0], title=row[1], assignee_id=row[2], tags=tuple(row[3].split(",")) if row[3] else ())`. The parsing is at every call site, duplicated, error-prone. The cleaner pattern is to pass the raw row to `__init__` and let `__post_init__` parse — but `raw_tags` should not be a field on the instance (it's the un-parsed source, redundant with `tags`). `InitVar[T]` is the answer: declare `raw_tags: InitVar[str] = ""` on the class, and `__post_init__(self, raw_tags: str)` receives it as a positional argument, parses it, and uses `object.__setattr__` to set `self.tags`. The `raw_tags` value never lands on the instance.

## The Code

```python
# boardly/models/ticket_initvar.py
"""boardly — KW_ONLY, InitVar, and the __post_init__ lifecycle."""
from dataclasses import InitVar, dataclass, field, KW_ONLY


@dataclass(frozen=True, slots=True)
class Ticket:
    id: int                  # positional
    title: str               # positional
    _: KW_ONLY               # everything after this is keyword-only
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
    raw_tags: InitVar[str | None] = None

    def __post_init__(self, raw_tags: str | None) -> None:
        if raw_tags is not None:
            object.__setattr__(self, "tags", tuple(raw_tags.split(",")))


# A row from SELECT * FROM tickets.
row = (1, "Fix login", 42, "urgent,bug")


if __name__ == "__main__":
    t = Ticket(row[0], row[1], assignee_id=row[2], raw_tags=row[3])
    print("ticket:", t)
    print("'raw_tags' in __slots__:", 'raw_tags' in Ticket.__slots__)
    print("tags:", t.tags)

    t2 = Ticket(id=2, title="Ship MVP", assignee_id=99, tags=("feature",))
    print("ticket2:", t2)

    # Positional call — only id and title can be positional.
    try:
        Ticket(1, "X", 42, ("urgent",))  # TypeError: extra positional arg
    except TypeError as exc:
        print("positional blocked:", exc)
```

## Line-by-Line Deep Dive

### Lines 1–4: Imports

```python
# boardly/models/ticket_initvar.py
"""boardly — KW_ONLY, InitVar, and the __post_init__ lifecycle."""
from dataclasses import InitVar, dataclass, field, KW_ONLY
```

`KW_ONLY` is a sentinel value (Python 3.10+) — it is a single instance of `_kw_only` (a private marker class). `InitVar` is a class — used as `InitVar[T]` which returns a `_InitVar[T]` generic alias. `field` is the per-field configurator from lesson 02. Both `KW_ONLY` and `InitVar` are 3.10+-stable — they were added in 3.10 alongside `slots=True` and the `kw_only` parameter on `field()`.

**Why is `KW_ONLY` a sentinel rather than a decorator parameter?**

Because the sentinel form lets you split a class's fields at any point in the declaration order — `id` and `title` are positional, `KW_ONLY` splits here, `assignee_id` and `tags` are keyword-only. The decorator-level `kw_only=True` (lesson 05) makes *every* field keyword-only — the sentinel lets you mix positional and keyword in one class. The sentinel form is strictly more expressive; the decorator form is the shortcut for the common case (every field keyword-only). The two are equivalent for the all-keyword-only case.

### Lines 6–14: The Ticket class with `KW_ONLY` and `InitVar`

```python
@dataclass(frozen=True, slots=True)
class Ticket:
    id: int                  # positional
    title: str               # positional
    _: KW_ONLY               # everything after this is keyword-only
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
    raw_tags: InitVar[str | None] = None
```

The `_` field is assigned `KW_ONLY` — the sentinel. The name `_` is a convention (it could be anything — `_kw_only`, `__`, etc.); the value `KW_ONLY` is what `@dataclass` looks for. The decorator walks the class body; when it encounters a field whose value is the `KW_ONLY` sentinel, it does *not* add it to the field list, and it sets a flag "all subsequent fields are keyword-only". The generated `__init__` signature is:

```python
def __init__(self, id: int, title: str, *, assignee_id: int = 0, tags: tuple[str, ...] = (), raw_tags: str | None = None):
    ...
```

The `*` separator appears between `title` and `assignee_id`. Positional construction allows only `id` and `title` — `Ticket(1, "X")` works; `Ticket(1, "X", 42)` raises `TypeError`. `raw_tags: InitVar[str | None] = None` is the init-only field. `@dataclass` recognises the `InitVar` annotation and marks the field as init-only — it adds it to the `__init__` parameters but does *not* add it to the instance attributes (no `self.raw_tags = ...` line in the generated `__init__`), does *not* add it to `__slots__` (slots), and passes it to `__post_init__` as a positional argument.

**Why does `InitVar` not store the field on the instance?**

Because the field is *init-only* — it exists to pass information to `__post_init__`, not to be part of the instance's persistent state. In the `Ticket`-from-row pattern, `raw_tags` is the comma-separated string from the database; the *parsed* `tags` tuple is what the instance needs to keep. Storing both would be redundant — `raw_tags` would be derivable from `tags` (with `",".join(tags)`), and the redundancy would invite inconsistency (`t.raw_tags != ",".join(t.tags)` if one was changed). `InitVar` lets you accept the raw input, parse it in `__post_init__`, and store only the parsed form on the instance. The instance is smaller (one fewer field) and self-consistent.

### Lines 16–18: The `__post_init__` method

```python
    def __post_init__(self, raw_tags: str | None) -> None:
        if raw_tags is not None:
            object.__setattr__(self, "tags", tuple(raw_tags.split(",")))
```

`__post_init__` is called by the generated `__init__` *after* every regular field has been set. The signature receives every `InitVar` field as a positional argument, in declaration order. Here, `raw_tags` is the only `InitVar`, so `__post_init__(self, raw_tags)` is the signature. If there were two `InitVar`s (`raw_tags` and `raw_assignee`), the signature would be `__post_init__(self, raw_tags, raw_assignee)` — order matters.

The body checks `raw_tags is not None` and, if so, parses it — `tuple(raw_tags.split(","))` — and assigns to `self.tags`. The `object.__setattr__` is the frozen-class escape hatch. Without it, `self.tags = ...` would raise `FrozenInstanceError` (lesson 03). The `object.__setattr__` bypasses the frozen `__setattr__` override and sets the attribute directly. This is the documented escape hatch for initialising derived fields on a frozen class — it is the only safe way to mutate a frozen instance, and it should only be used inside `__post_init__`.

**Why does `__post_init__` run after regular field assignment?**

Because the regular fields must exist before `__post_init__` can read or modify them. The generated `__init__` is, in effect:

```python
def __init__(self, id, title, *, assignee_id=0, tags=(), raw_tags=None):
    self.id = id
    self.title = title
    self.assignee_id = assignee_id
    self.tags = tags
    self.__post_init__(raw_tags)
```

The `self.tags = tags` runs first (using `object.__setattr__` internally for frozen classes), then `__post_init__(raw_tags)` runs and may overwrite `self.tags` with the parsed version. The pattern is "default-then-override" — the default value (`()`) is set, then `__post_init__` may replace it. This is why `replace(t, ...)` (lesson 06) re-runs `__post_init__` — the new instance gets the default, then `__post_init__` overrides based on the (possibly new) `InitVar` values.

### Lines 20–22: The database row and the construction

```python
# A row from SELECT * FROM tickets.
row = (1, "Fix login", 42, "urgent,bug")


if __name__ == "__main__":
    t = Ticket(row[0], row[1], assignee_id=row[2], raw_tags=row[3])
    print("ticket:", t)
    print("'raw_tags' in __slots__:", 'raw_tags' in Ticket.__slots__)
    print("tags:", t.tags)
```

`Ticket(row[0], row[1], assignee_id=row[2], raw_tags=row[3])` constructs the `Ticket` from the row. `row[0]` and `row[1]` are the positional `id` and `title`; `assignee_id` and `raw_tags` are keyword-only because of the `KW_ONLY` sentinel. The construction `Ticket(*row[:3], raw_tags=row[3])` would fail with `TypeError: Ticket.__init__() takes 3 positional arguments but 5 were given` — `row[:3]` unpacks three elements as positional, but the `__init__` accepts only `id` and `title` positionally after the `*` separator. The correct construction passes only the first two elements positionally and the rest by name.

The `print("ticket:", t)` produces `Ticket(id=1, title='Fix login', assignee_id=42, tags=('urgent', 'bug'))`. Note that `raw_tags` does *not* appear in the `__repr__` — it is not a regular field. The `'raw_tags' in __slots__` check is `False` — the init-only field is not in the instance's slot set. The `t.tags` is `('urgent', 'bug')` — parsed from `raw_tags` by `__post_init__`.

**Note — `hasattr(t, "raw_tags")` returns `True`, but `raw_tags` is not an instance attribute.**

The class body has `raw_tags: InitVar[str | None] = None` — this is an *annotated assignment* (`AnnAssign`), and Python stores the result `None` as a *class attribute* (in `Ticket.__dict__['raw_tags']`). `@dataclass`'s `InitVar` recognition prevents `raw_tags` from being added to `__slots__` or to the instance `__dict__`, but it does *not* remove the class-attribute `None` that was assigned at class-body time. So `hasattr(t, "raw_tags")` walks `instance -> class -> ...` and finds the class attribute — returning `True` (the value is `None`). The robust check for "is this an instance attribute?" is `'raw_tags' in __slots__` (slotted classes) or `'raw_tags' in t.__dict__` (non-slotted). Both return `False` for an `InitVar` field.

**Why is the `raw_tags` not on the instance even though `__init__` received it?**

Because `@dataclass`'s generated `__init__` does *not* have a `self.raw_tags = raw_tags` line for `InitVar` fields. The `raw_tags` parameter is passed to `__post_init__` only; the instance never stores it. The `__slots__` (with slots=True) does not include `raw_tags`. The `__dict__` (without slots) does not include `raw_tags`. The `asdict(t)` does not include `raw_tags`. The `astuple(t)` does not include `raw_tags`. The `replace(t, ...)` does not accept `raw_tags` as a keyword (it accepts only the regular fields). The `InitVar` is *truly* init-only — it exists for the duration of `__init__` and `__post_init__`, then is gone. The class-level `raw_tags = None` value remains in `Ticket.__dict__` (a Python side-effect of the annotated assignment form), but the *instance* has no `raw_tags` storage — checking `'raw_tags' in __slots__` (slotted) or `'raw_tags' in t.__dict__` (non-slotted) confirms the absence.

### Lines 24–26: The non-raw construction

```python
    t2 = Ticket(id=2, title="Ship MVP", assignee_id=99, tags=("feature",))
    print("ticket2:", t2)
```

`Ticket(id=2, title="Ship MVP", assignee_id=99, tags=("feature",))` constructs a `Ticket` with the parsed tags directly. `raw_tags` defaults to `None`, so `__post_init__` does not modify `self.tags` — it stays as `("feature",)`. This is the "constructed from already-parsed data" path; the `raw_tags` path is for "constructed from raw DB row" use case. Both paths produce a valid `Ticket` with `tags` as a tuple.

### Lines 28–32: The positional block

```python
    # Positional call — only id and title can be positional.
    try:
        Ticket(1, "X", 42, ("urgent",))  # TypeError: extra positional arg
    except TypeError as exc:
        print("positional blocked:", exc)
```

`Ticket(1, "X", 42, ("urgent",))` attempts 4 positional arguments. The `__init__` signature allows only 2 positional (`id`, `title`). The `*` separator after `title` enforces keyword-only for everything after. The call raises `TypeError: Ticket.__init__() takes 3 positional arguments but 5 were given` (or similar message — the exact count depends on whether `self` is counted). The `except TypeError` block prints the message.

**Why does the `TypeError` message say "5 were given" when only 4 args are passed?**

Because Python counts `self` as one of the arguments. `Ticket(1, "X", 42, ("urgent",))` is `Ticket.__init__(t, 1, "X", 42, ("urgent",))` — 5 arguments including `self`. The `__init__` signature takes `self, id, title, *` — 3 positional. The `TypeError` reports "5 were given" (the actual count including `self`) vs "3 positional" (the signature count including `self`).

## Execution Trace

```bash
$ python boardly/models/ticket_initvar.py
ticket: Ticket(id=1, title='Fix login', assignee_id=42, tags=('urgent', 'bug'))
'raw_tags' in __slots__: False
tags: ('urgent', 'bug')
ticket2: Ticket(id=2, title='Ship MVP', assignee_id=99, tags=('feature',))
positional blocked: Ticket.__init__() takes 3 positional arguments but 5 were given
```

The `Ticket` constructed from the row has `tags=('urgent', 'bug')` — parsed by `__post_init__`. The `raw_tags` field is not in the instance's `__slots__` — confirmed by the `'raw_tags' in __slots__` check returning `False`. (See the Note above: `hasattr(t, "raw_tags")` returns `True` because of the class-level fallback, but the instance storage is empty.) The `t2` constructed directly has `tags=('feature',)`. The positional block raises `TypeError`.

## Common Mistakes

### Mistake 1: Accessing an `InitVar` field on the instance

```python
@dataclass(slots=True)
class Ticket:
    id: int
    raw_tags: InitVar[str] = ""

t = Ticket(id=1, raw_tags="urgent,bug")
print(t.raw_tags)  # prints "" — the class-attribute default, NOT the instance value
print('raw_tags' in Ticket.__slots__)  # False
print('raw_tags' in t.__dict__ if hasattr(t, '__dict__') else False)  # False
```

**Symptom:** `t.raw_tags` returns the class-attribute default (e.g., `""`), not the value passed to `__init__`. The class attribute is a Python side-effect of the `AnnAssign` form — `raw_tags: InitVar[str] = ""` stores `""` in `Ticket.__dict__`.
**Why:** `InitVar` fields are not stored on the instance — `__init__` does not have a `self.raw_tags = raw_tags` line. `hasattr(t, "raw_tags")` is `True` (class attribute fallback), but the instance has neither a slot nor a `__dict__` entry for it.
**Fix:** Store the parsed form on a regular field, or pass `raw_tags` through `__post_init__` to a regular field, or accept that `raw_tags` is gone after `__post_init__` returns.

### Mistake 2: Forgetting the `object.__setattr__` in a frozen `__post_init__`

```python
@dataclass(frozen=True)
class Ticket:
    id: int
    tags: tuple[str, ...] = ()
    raw_tags: InitVar[str | None] = None

    def __post_init__(self, raw_tags):
        if raw_tags:
            self.tags = tuple(raw_tags.split(","))  # FrozenInstanceError
```

**Symptom:** `FrozenInstanceError: cannot assign to field 'tags'`.
**Why:** The frozen `__setattr__` override blocks every assignment, including the one in `__post_init__`. The regular `__init__` uses `object.__setattr__` internally (the generated code); `__post_init__` is user code and must use the escape explicitly.
**Fix:** `object.__setattr__(self, "tags", tuple(raw_tags.split(",")))`.

### Mistake 3: Wrong `__post_init__` signature

```python
    def __post_init__(self):  # missing the InitVar parameter
        ...
```

**Symptom:** `TypeError: __post_init__() takes 1 positional argument but 2 were given`.
**Why:** The generated `__init__` calls `self.__post_init__(raw_tags)` — one positional arg. If your `__post_init__` does not declare the parameter, the call fails.
**Fix:** `def __post_init__(self, raw_tags: str | None) -> None:` — match the `InitVar` declaration order. Multiple `InitVar`s come in declaration order.

## Engineering Trade-Offs

**Decision:** Use `KW_ONLY` to split positional convenience from keyword-only configuration on classes that have both. Use `InitVar` for raw input that should be parsed in `__post_init__` and not stored. Use `__post_init__` for derived-field computation, normalisation, and (carefully) lightweight validation.
**Both sides:** The alternative to `KW_ONLY` is the class-level `kw_only=True` from lesson 05 — simpler but loses the positional convenience. The alternative to `InitVar` is to parse the raw input at the call site before construction — simpler but duplicates the parsing logic. The alternative to `__post_init__` is a `classmethod` `from_row` factory — explicit but more boilerplate.
**Commitment:** In `boardly`, the `Ticket`-from-DB-row pattern uses `InitVar` + `__post_init__` exclusively. The convention is enforced in the model template. `KW_ONLY` is used on classes with mixed positional/keyword ergonomic needs — `Project` (positional `id` for primary-key use, keyword `name`/`owner_id` for clarity).

## Exercises

1. **Exercise 1 — Multiple `InitVar`s.** Add `raw_assignee: InitVar[str | None] = None` to `Ticket` and parse it in `__post_init__` (e.g., `int(raw_assignee)`). Update the `__post_init__` signature to take both `InitVar`s in declaration order. `Verify: python boardly/models/ticket_initvar.py`
2. **Exercise 2 — `replace` and `InitVar`.** Use `replace(t, tags=("new",))` and verify the result. Then try `replace(t, raw_tags="new,raw")` — confirm `TypeError` (InitVar is not in `replace`). `Verify: python boardly/models/ticket_initvar.py`
3. **Exercise 3 — `asdict` and `InitVar`.** Run `asdict(t)` and verify `raw_tags` is not in the result — `InitVar` is excluded from the helpers. `Verify: python boardly/models/ticket_initvar.py`
4. **Exercise 4 — `KW_ONLY` placement.** Move the `_` (KW_ONLY) field to after `assignee_id`, making `id`, `title`, `assignee_id` positional and `tags` keyword-only. Read the generated `inspect.signature(Ticket.__init__)`. `Verify: python boardly/models/ticket_initvar.py`
5. **Exercise 5 — `__post_init__` for validation.** Add a check in `__post_init__` that raises `ValueError` if `self.title` is empty. Verify `Ticket(id=1, title="")` raises. Explain why this is lightweight validation, not full Pydantic-style validation. `Verify: python boardly/models/ticket_initvar.py`

## Verification

```bash
$ python boardly/models/ticket_initvar.py
ticket: Ticket(id=1, title='Fix login', assignee_id=42, tags=('urgent', 'bug'))
'raw_tags' in __slots__: False
tags: ('urgent', 'bug')
ticket2: Ticket(id=2, title='Ship MVP', assignee_id=99, tags=('feature',))
positional blocked: Ticket.__init__() takes 3 positional arguments but 5 were given
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — `__init__` is the function `__post_init__` extends.
- [[06-dataclasses/02-field-and-Defaults]] — `field()`'s `kw_only` parameter is the per-field form of the `KW_ONLY` sentinel.
- [[06-dataclasses/03-Frozen-and-Immutability]] — `object.__setattr__` is the escape hatch for frozen `__post_init__`.
- [[06-dataclasses/05-Inheritance]] — the class-level `kw_only=True` is the broad form; the `KW_ONLY` sentinel is the fine form.
- [[06-dataclasses/06-asdict-astuple-replace]] — `InitVar` fields are excluded from `asdict`, `astuple`, and `replace`.

## What's Next

You have finished Section 06. The next section is [[07-itertools/00-itertools-MOC]] — `chain`, `groupby`, `islice`, `starmap`, `product`, `combinations`. But if you came to this section from a FastAPI project, the natural next stop is back to [[01-typing/02-Annotated-and-Metadata]] — the parallel between `dataclasses.field(metadata=...)` and `Annotated[T, metadata]` is the bridge the section was building toward. The dataclass `metadata` dict and the `Annotated` metadata tuple solve the same problem at different layers; seeing both side by side is the senior insight. Three things to take with you:

- `KW_ONLY` splits a class's fields into positional prefix and keyword-only suffix; `kw_only=True` on `field()` is the per-field version.
- `InitVar[T]` declares an init-only field — passed to `__post_init__`, not stored on the instance.
- `__post_init__` runs after regular field assignment; `object.__setattr__` is the frozen escape hatch.

## Sources

- **`dataclasses.KW_ONLY`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.KW_ONLY — accessed 2026-10-23 — the canonical reference for the sentinel, added in 3.10.
- **`dataclasses.InitVar`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.InitVar — accessed 2026-10-23 — the canonical reference for init-only fields.
- **`dataclasses` — `__post_init__`** — https://docs.python.org/3/library/dataclasses.html#post-init — accessed 2026-10-23 — the lifecycle documentation, including the `InitVar` parameter passing order.
- **PEP 557 — Data Classes: InitVar** — https://peps.python.org/pep-0557/#init-only-variables — accessed 2026-10-23 — the rationale for `InitVar`.

## What We Learned

- You can use the `KW_ONLY` sentinel (3.10+) to split a class's fields into positional prefix and keyword-only suffix.
- You can use `InitVar[T]` to declare an init-only field — passed to `__init__`, passed to `__post_init__`, never stored on the instance.
- You can write `__post_init__` that receives `InitVar` values as positional arguments in declaration order.
- You can reason about the `__post_init__` lifecycle — when it runs, what it sees, the `object.__setattr__` escape for frozen classes.
- You can combine `KW_ONLY`, `InitVar`, and `__post_init__` in a `Ticket`-from-DB-row pattern that parses raw input on construction.
