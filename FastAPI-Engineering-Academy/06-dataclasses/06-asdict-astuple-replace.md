---
title: "Lesson 06: asdict, astuple, replace"
aliases:
 - dataclasses.asdict
 - dataclasses.astuple
 - dataclasses.replace
 - asdict deep-copy gotcha
tags:
 - dataclasses
 - helpers
 - immutability
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–40 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
related_lessons:
 - "[[06-dataclasses/08-KW_ONLY-and-InitVar]]"
 - "[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]"
---

# Lesson 06: asdict, astuple, replace

*The three helper functions every `boardly` service uses — `asdict` (deep, recurses into nested dataclasses), `astuple` (positional, same shape), and `replace` (returns a new instance with one field changed, the standard way to "update" a frozen `Ticket`).*

**You're at the very beginning of Section 06, sixth lesson in.**

You have frozen `Ticket`s in `boardly`. To "update" one — change the assignee — you cannot mutate it (`FrozenInstanceError`). You need a *new* `Ticket` with one field changed. `dataclasses.replace(obj, field=value)` is the standard-library function for exactly this. It returns a new instance, copies every unchanged field by reference, and overrides the ones you specify. This lesson also walks `asdict(obj)` — the function FastAPI uses to serialise a dataclass response body to a dict before JSON-encoding it — and `astuple(obj)`, the positional sibling. All three are subtle: `asdict` is *deep* (it recurses into nested dataclasses, dicts, lists, tuples), and the deep recursion is a perf footgun if you do not know it is happening. `replace` does *not* call `__init__` directly — it uses `__init__` but bypasses some `__post_init__` paths. This lesson walks every piece.

#dataclasses #helpers

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `asdict(obj)`** to convert a dataclass instance to a (deep) `dict`, and explain what "deep" means.
2. **Use `astuple(obj)`** to convert to a positional tuple, and name when it beats `asdict`.
3. **Use `replace(obj, field=value)`** to derive a new frozen instance with one or more fields changed.
4. **Reason about the `asdict` deep-copy gotcha** — why a nested `list` field is *copied* on every `asdict` call, and what that costs.
5. **Map `replace` to the immutable-update pattern** — the same shape as `dict |= other` and `tuple.replace` (3.13+).

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. The helpers operate on `is_dataclass(obj)`-true instances.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. `asdict`'s recursion uses the field metadata to decide what to recurse into.
- **`frozen=True`** — [[06-dataclasses/03-Frozen-and-Immutability]]. `replace` is the immutable "update" path for frozen dataclasses.
- **About 25–40 minutes of focused time.**

**The most common gap: the `asdict` deep-copy gotcha.**

Students call `asdict(ticket)` expecting a shallow `dict` of the ticket's fields. They get one — but the nested `tags` list is a *copy*, not a reference to the original. If `ticket.tags` is large (1000 items), `asdict(ticket)` allocates a fresh 1000-item list on every call. In a hot path (say, a FastAPI route that calls `asdict` to serialise a response body 1000 times per second), the allocation is significant. The fix is to use `dataclasses.asdict(obj, *, dict_factory=dict)` with a `dict_factory` that does not copy nested — but the default *does* copy. The lesson walks the source so you can predict the cost.

## The Problem

You have a frozen `Ticket`:

```python
@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    assignee_id: int
    tags: tuple[str, ...] = ()
```

You need three operations in `boardly`:

1. **Serialise** the `Ticket` to a `dict` for a JSON response body.
2. **Compare** two `Ticket`s by their field tuple (faster than `__eq__` for some operations — e.g., sorting).
3. **Update** the `assignee_id` — but `frozen=True` forbids mutation.

The standard library provides `asdict`, `astuple`, and `replace` for exactly these three. They look trivial but each has a gotcha: `asdict` deep-copies; `astuple` is positional (loses field names); `replace` does not call the full `__init__` path (so `__post_init__` may not run as expected). This lesson walks each function's source-of-truth behaviour.

## The Code

```python
# boardly/services/ticket_helpers.py
"""boardly — asdict, astuple, replace on a frozen Ticket."""
from dataclasses import asdict, astuple, dataclass, field, replace


@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Board:
    id: int
    tickets: tuple[Ticket, ...] = ()


if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42, tags=("urgent", "bug"))

    d = asdict(t)
    print("asdict:", d)
    print("tags is same list?", d["tags"] is t.tags)  # False — deep copy

    tpl = astuple(t)
    print("astuple:", tpl)

    t2 = replace(t, assignee_id=99)
    print("replaced:", t2)
    print("t unchanged:", t)

    b = Board(id=1, tickets=(t, t2))
    bd = asdict(b)
    print("nested asdict:", bd)
    print("nested ticket is dict?", isinstance(bd["tickets"][0], dict))  # True — recursion
```

## Line-by-Line Deep Dive

### Lines 1–10: Imports and the frozen Ticket

```python
# boardly/services/ticket_helpers.py
"""boardly — asdict, astuple, replace on a frozen Ticket."""
from dataclasses import asdict, astuple, dataclass, field, replace


@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
```

The class is the lesson 03 frozen form, with `tags` as a `tuple` for deep immutability. The helpers `asdict`, `astuple`, `replace` are imported from `dataclasses`. The `field` import is for completeness — this lesson does not use it directly, but every `field()`-aware helper in the module follows the same field metadata. The class is frozen; `replace` is the immutable-update path.

### Lines 12–14: The nested Board class

```python
@dataclass(frozen=True)
class Board:
    id: int
    tickets: tuple[Ticket, ...] = ()
```

`Board` has a `tickets: tuple[Ticket, ...]` field — a tuple of `Ticket`s. The `asdict` recursion will descend into each `Ticket` in the tuple and convert them to dicts. This is the "deep" property: `asdict` does not stop at the top-level fields — it walks every dataclass instance, every `dict` value, every `list`/`tuple`/`set` element, recursively.

**Why does `asdict` recurse rather than being shallow?**

Because the use case is JSON serialisation, and a JSON object cannot contain a Python `Ticket` instance — it must contain a `dict`. If `asdict(board)` returned `{"id": 1, "tickets": (<Ticket id=1 ...>, <Ticket id=2 ...>)}`, the resulting dict would still contain `Ticket` instances, which `json.dumps` cannot serialise. The deep recursion is the only way to produce a fully-JSON-serialisable `dict` from a dataclass tree in one call. The cost — copying every nested list/tuple — is the price. FastAPI's `_prepare_response_content` walks this same path.

### Lines 16–20: The `asdict` deep-copy demonstration

```python
if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42, tags=("urgent", "bug"))

    d = asdict(t)
    print("asdict:", d)
    print("tags is same list?", d["tags"] is t.tags)  # False — deep copy
```

`asdict(t)` produces `{"id": 1, "title": "Fix login", "assignee_id": 42, "tags": ("urgent", "bug")}`. The `tags` field is *copied* — `d["tags"] is t.tags` is `False`. The copy is a new tuple containing the same string elements (strings are immutable, so the element sharing is fine). For a `list` field, the copy would be a new list with the same elements — same sharing for the elements. The `is` check is the demonstration; the cost matters when the field is large.

**Why does `asdict` copy rather than reuse the reference?**

Because if it reused the reference, mutating `d["tags"]` would mutate the original `Ticket`'s `tags` — and `Ticket` is frozen, so the original would appear to violate its freeze. The copy is the standard-library's defence: the result of `asdict` is *yours* to mutate, with no coupling back to the source. The cost is one allocation per nested mutable container. For immutable containers (`tuple`, `frozenset`, `str`), the copy is still made — the source code is not smart enough to skip immutables — but the per-element copy is cheap because the elements are shared.

### Lines 22–23: The `astuple` call

```python
    tpl = astuple(t)
    print("astuple:", tpl)
```

`astuple(t)` produces `(1, "Fix login", 42, ("urgent", "bug"))` — a positional tuple, in declaration order. The tuple has the same shape as `asdict`'s values but without the field names. `astuple` is useful for: (a) sorting a list of dataclass instances by their field tuple (faster than `__lt__` when ordering is needed; the `operator.itemgetter` pattern), (b) `*tpl` unpacking into another constructor — `Ticket2(*astuple(t))` if `Ticket2` has the same field order. `astuple` is also deep — it recurses into nested dataclasses, converting them to tuples too.

**Why would `astuple` beat `asdict`?**

Two cases. First, when you need a *sorted* view of a list of tickets — `sorted(tickets, key=astuple)` is faster than `sorted(tickets, key=lambda t: (t.id, t.title, ...))` because the field-tuple key is built once per instance and reused by `sorted`. Second, when you need to pass the field values to a function that expects positional args — `operator.itemgetter`-shaped use. `asdict` loses the field names by design (it returns a dict), so neither is universally better; the choice depends on what the caller wants.

### Lines 25–27: The `replace` immutable update

```python
    t2 = replace(t, assignee_id=99)
    print("replaced:", t2)
    print("t unchanged:", t)
```

`replace(t, assignee_id=99)` returns a *new* `Ticket` instance with `assignee_id=99` and every other field copied from `t` by reference. The original `t` is unchanged — `frozen=True` would have made mutation impossible anyway. The new instance has the same `tags` tuple (same reference — tuples are immutable so sharing is safe), the same `title` string (same reference — strings are immutable), and the new `assignee_id=99`. The `replace` implementation is: `cls(**{**asdict(obj), **changes})` — wait, that's wrong. The actual implementation uses `__init__` directly: it builds a kwargs dict from the existing field values plus the changes, then calls `cls(**kwargs)`. The `__init__` call runs (so any `__post_init__` runs too — see Mistake 1).

**Why does `replace` call `__init__` rather than just mutating the instance?**

Because the instance is frozen — there is no way to mutate it without `object.__setattr__`. The cleanest path is to construct a new instance. The `__init__` call also re-runs `__post_init__` if present (lesson 08), which is correct — the new instance should be in the same valid state as if it had been constructed from scratch. The only behaviour to be aware of is that `__post_init__` runs again — if your `__post_init__` does work that should only happen once (e.g., timestamp the creation), `replace` will re-timestamp. The fix is to use `InitVar` (lesson 08) to pass the original `created_at` through.

### Lines 29–32: The nested `asdict` demonstration

```python
    b = Board(id=1, tickets=(t, t2))
    bd = asdict(b)
    print("nested asdict:", bd)
    print("nested ticket is dict?", isinstance(bd["tickets"][0], dict))  # True — recursion
```

`asdict(b)` produces `{"id": 1, "tickets": ({"id": 1, "title": "Fix login", "assignee_id": 42, "tags": ("urgent", "bug")}, {"id": 1, "title": "Fix login", "assignee_id": 99, "tags": ("urgent", "bug")})}`. Each `Ticket` in the `tickets` tuple has been converted to a `dict`. The `isinstance(bd["tickets"][0], dict)` check confirms the recursion. This is the deep property in action — the `Board`'s `tickets` field is a tuple of `Ticket`s, and `asdict` walked into each one.

**Note — `asdict` preserves container type for tuples.**

The `asdict` source in `Lib/dataclasses.py` does `type(obj)(_asdict_inner(v, dict_factory) for v in obj)` for `list` and `tuple` fields — it calls `type(obj)` to rebuild the container. A `tuple[Ticket, ...]` field produces a `tuple` of `dict`s; a `list[Ticket]` field would produce a `list` of `dict`s. The output is *not* uniformly `list` — the original container type is preserved. This matters when the downstream code (e.g., a JSON encoder) treats `tuple` and `list` differently (`json.dumps` serialises both as JSON arrays, but other tools may distinguish).

**Why does the recursion happen for nested dataclasses but not for arbitrary objects?**

Because `asdict` checks `is_dataclass(obj)` (or `isinstance(obj, dict)` or `isinstance(obj, (list, tuple)))` at each level. If the check passes, it recurses; otherwise it returns the value unchanged. So a `Ticket` field that is a `datetime.datetime` instance is returned as-is (datetime is not a dataclass, not a dict, not a list/tuple) — `asdict` does not know how to serialise it; the caller is responsible. FastAPI's response model handles this by running the `asdict` result through `json.dumps` with a `default=` handler that knows about `datetime`. The lesson is: `asdict` is *not* a JSON encoder — it is a `dict` converter; JSON encoding is a separate step.

## Execution Trace

```bash
$ python boardly/services/ticket_helpers.py
asdict: {'id': 1, 'title': 'Fix login', 'assignee_id': 42, 'tags': ('urgent', 'bug')}
tags is same list? False
astuple: (1, 'Fix login', 42, ('urgent', 'bug'))
replaced: Ticket(id=1, title='Fix login', assignee_id=99, tags=('urgent', 'bug'))
t unchanged: Ticket(id=1, title='Fix login', assignee_id=42, tags=('urgent', 'bug'))
nested asdict: {'id': 1, 'tickets': ({'id': 1, 'title': 'Fix login', 'assignee_id': 42, 'tags': ('urgent', 'bug')}, {'id': 1, 'title': 'Fix login', 'assignee_id': 99, 'tags': ('urgent', 'bug')})}
nested ticket is dict? True
```

The `asdict` result has a *different* `tags` tuple from the original (the `is` check is `False`). The `astuple` result is the positional form. The `replace` produces a new instance with `assignee_id=99`; the original is unchanged. The nested `asdict` recursed into the `tickets` tuple and converted each `Ticket` to a dict — note that the outer `(...)` is still a `tuple`, not a `list` (`asdict` preserves the container type).

## Common Mistakes

### Mistake 1: `replace` runs `__post_init__` again

```python
@dataclass(frozen=True)
class Ticket:
    id: int
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        object.__setattr__(self, "created_at", self.created_at.replace(microsecond=0))

t = Ticket(id=1)
t2 = replace(t, id=2)
# t2.created_at is now a NEW timestamp, not t's timestamp
```

**Symptom:** `t2.created_at != t.created_at` — the timestamp is fresh, not copied.
**Why:** `replace` calls `__init__`, which calls `__post_init__`. The `__post_init__` runs the `default_factory` first (so `created_at` is set to a fresh `datetime.now()`), then the body of `__post_init__` truncates microseconds. The result is a new timestamp.
**Fix:** Pass `created_at` explicitly to `replace`: `replace(t, id=2, created_at=t.created_at)`. Or use an `InitVar` (lesson 08) to signal "do not re-stamp".

### Mistake 2: Using `asdict` in a hot path

```python
def serialize(t: Ticket) -> dict:
    return asdict(t)  # allocates a new tags tuple every call
```

**Symptom:** Profile shows `asdict` as the top allocator, despite the `Ticket` being small.
**Why:** `asdict` deep-copies every nested mutable field. For a `Ticket` with `tags=("urgent", "bug")`, the copy is cheap. For a `Board` with 1000 `Ticket`s, every `asdict(board)` allocates 1000 dicts and 1000 tuples.
**Fix:** If the data is immutable (frozen + `tuple`/`frozenset`/`str` fields), use a custom shallow serialiser that does not copy: `dict(cls.__dict__)` for the top level. Or use `msgspec`/`pydantic` for serialisation. Or cache the `asdict` result if the instance never changes.

### Mistake 3: Expecting `astuple` to preserve field names

```python
@dataclass
class Ticket:
    id: int
    title: str
    description: str = ""

t = Ticket(id=1, title="X", description="Y")
id, title, *_ = astuple(t)  # works
{f.name: v for f, v in zip(dataclasses.fields(t), astuple(t))}  # roundtrip
```

**Symptom:** No bug — but students reach for `astuple` when they want a dict, then rebuild the dict.
**Why:** `astuple` is positional; it does not preserve names. If you need names, use `asdict`.
**Fix:** Use `asdict(t)` if you need names; use `astuple(t)` only for positional use.

## Engineering Trade-Offs

**Decision:** Use `replace` for every immutable "update" of a frozen dataclass. Use `asdict` only at the serialisation boundary (FastAPI response body). Use `astuple` only for sort keys and positional interop.
**Both sides:** The alternative to `replace` is `dataclasses.replace`-by-hand: `Ticket(id=t.id, title=t.title, assignee_id=99, tags=t.tags)`. This works but requires you to know every field, every default, every factory. `replace` does the bookkeeping for you. The alternative to `asdict` is `cls.__dict__` (shallow) — but `__dict__` does not include inherited fields and does not recurse. The alternative to `astuple` is `operator.itemgetter`-shaped use with explicit field access.
**Commitment:** In `boardly`, the service layer uses `replace` for every domain-model update. The FastAPI routes use `asdict` once, at the response-serialisation boundary, and cache the result for large immutable responses. `astuple` is reserved for sort keys in the analytics module.

## Exercises

1. **Exercise 1 — `is` check.** Run the file. Verify `d["tags"] is t.tags` is `False`. Explain why the copy is made even though `tuple` is immutable. `Verify: python boardly/services/ticket_helpers.py`
2. **Exercise 2 — `replace` multiple fields.** Use `replace(t, assignee_id=99, title="New title")` and verify both fields are updated in the result. `Verify: python boardly/services/ticket_helpers.py`
3. **Exercise 3 — `asdict` with `dict_factory`.** Call `asdict(t, dict_factory=type("Ordered", (), {"__call__": lambda self, items: dict(items)})())` — or simpler, `asdict(t, dict_factory=sorted)` to test the parameter. (Note: `dict_factory` takes an iterable of `(key, value)` pairs.) `Verify: python boardly/services/ticket_helpers.py`
4. **Exercise 4 — `astuple` for sort.** Build a list of 5 `Ticket`s with various `assignee_id`s. Sort by `astuple` and verify the order. `Verify: python boardly/services/ticket_helpers.py`
5. **Exercise 5 — Nested `replace`.** Use `replace(b, tickets=replace(b.tickets[0], assignee_id=99))` — wait, tuples are immutable. Use `replace(b, tickets=b.tickets[0:1] + (replace(b.tickets[1], assignee_id=99),))` to update one element of the nested tuple. `Verify: python boardly/services/ticket_helpers.py`

## Verification

```bash
$ python boardly/services/ticket_helpers.py
asdict: {'id': 1, 'title': 'Fix login', 'assignee_id': 42, 'tags': ('urgent', 'bug')}
tags is same list? False
astuple: (1, 'Fix login', 42, ('urgent', 'bug'))
replaced: Ticket(id=1, title='Fix login', assignee_id=99, tags=('urgent', 'bug'))
t unchanged: Ticket(id=1, title='Fix login', assignee_id=42, tags=('urgent', 'bug'))
nested asdict: {'id': 1, 'tickets': ({'id': 1, 'title': 'Fix login', 'assignee_id': 42, 'tags': ('urgent', 'bug')}, {'id': 1, 'title': 'Fix login', 'assignee_id': 99, 'tags': ('urgent', 'bug')})}
nested ticket is dict? True
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — `__init__` is what `replace` calls.
- [[06-dataclasses/02-field-and-Defaults]] — `field()` metadata is what `asdict` walks.
- [[06-dataclasses/03-Frozen-and-Immutability]] — `replace` is the immutable-update path for frozen classes.

## What's Next

[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — the senior decision: `@dataclass` (no validation, fastest), Pydantic `BaseModel` (validation, slower), `TypedDict` (type-only, no runtime). The three are siblings; this lesson's `asdict`/`astuple`/`replace` helpers reappear in Pydantic as `model_dump()`/`model_dump_json()`/`model_copy()`. Three things to take with you:

- `asdict(obj)` is *deep* — it recurses into nested dataclasses, dicts, lists, tuples.
- `astuple(obj)` is positional; use it for sort keys and positional interop.
- `replace(obj, field=value)` calls `__init__`, so `__post_init__` runs again — pass `InitVar`s explicitly if you need to preserve state.

## Sources

- **`dataclasses.asdict`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict — accessed 2026-10-23 — the canonical reference, including the `dict_factory` parameter and the deep-copy behaviour.
- **`dataclasses.astuple`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.astuple — accessed 2026-10-23 — the positional sibling.
- **`dataclasses.replace`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.replace — accessed 2026-10-23 — the immutable-update function; the docstring is the canonical specification.
- **`dataclasses.fields` / `is_dataclass`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.fields — accessed 2026-10-23 — the introspection helpers FastAPI uses to walk a dataclass response model.

## What We Learned

- You can use `asdict(obj)` to convert a dataclass instance to a deep `dict`, and explain why the deep copy is made.
- You can use `astuple(obj)` for sort keys and positional interop, and name when it beats `asdict`.
- You can use `replace(obj, field=value)` to derive a new frozen instance with fields changed.
- You can reason about the `asdict` deep-copy gotcha — every nested mutable container is copied on every call.
- You can map `replace` to the immutable-update pattern and explain why `__post_init__` runs again.
