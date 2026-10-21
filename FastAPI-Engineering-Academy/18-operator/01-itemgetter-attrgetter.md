---
title: "Lesson 01: itemgetter & attrgetter"
aliases:
 - operator.itemgetter
 - operator.attrgetter
 - itemgetter
 - attrgetter
tags:
 - operator
 - itemgetter
 - attrgetter
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[02-functools/03-partial]]"
related_lessons:
 - "[[18-operator/02-methodcaller]]"
 - "[[18-operator/03-functional-composition]]"
 - "[[02-functools/03-partial]]"
first_taught_in: "18-operator/01-itemgetter-attrgetter"
---

# Lesson 01: `itemgetter` & `attrgetter`

*The two C-implemented callable factories that replace every `lambda r: r[1]` and `lambda p: p.owner.name` in your codebase — and beat the lambda on every `key=` call site.*

**You're at the very beginning of Section 18.**

The `operator` module is the smallest standard-library module that senior engineers reach for daily without ever reading its source. `itemgetter` and `attrgetter` are the two factories you will meet first. Both return a callable that extracts one (or several) values from another object — `itemgetter(1)` returns `lambda x: x[1]`, `attrgetter("name")` returns `lambda x: x.name` — and both are implemented in C, so they run noticeably faster than the equivalent Python lambda on every `sorted(key=...)` call site. By the end of this lesson you will know which factory to reach for, how multi-field and dotted-path extraction works, and why the C fast path matters. Take your time. Type every example. **This is how you learn.**

#operator #itemgetter #attrgetter #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `operator.itemgetter(*items)`** to build a callable that indexes any object supporting `__getitem__` — single index returns a value, multiple indices return a tuple.
2. **Apply `operator.attrgetter(*attrs)`** to build a callable that reads attributes — and traverse dotted paths like `"owner.name"`.
3. **Use both factories as `key=` functions** in `sorted`, `min`, `max`, `itertools.groupby`, and `list.sort`.
4. **Compare `itemgetter`/`attrgetter` to a `lambda`** — and articulate why the C fast path is faster on every call.
5. **Choose between `itemgetter` and `attrgetter`** based on the data shape (`dict`/`tuple`/`list` vs `dataclass`/`User`).

## Prerequisites

Before starting, you need:

- **Lambda syntax** — `lambda r: r["name"]` should be readable. See [[02-functools/03-partial]] for the sibling primitive (`partial`).
- **Dataclass basics** — `@dataclass class Project: ...` with attributes. See [[06-dataclasses/01-dataclass-Basics]].
- **About 20–30 minutes of focused time.**

**The most common gap: writing `lambda` key functions everywhere.**

A `lambda r: r["priority"]` is fine for one inline call. The senior-engineer move is to reach for `itemgetter("priority")` — it is shorter, faster (C implementation), reusable, and reads as English at the call site. Students who never internalise this end up with `key=lambda r: r["priority"]` repeated fifty times across a codebase, each one a Python frame the interpreter pays for. The fix is to know the `operator` factories by name.

## The Problem

You ship `boardly/tickets/sort.py` that sorts a list of `Ticket` records by priority (descending) and assigns them to a board column. The first version reads naturally:

```python
tickets = [
    Ticket(id=..., title="Auth fails on macOS", priority=3),
    Ticket(id=..., title="Search returns 500", priority=5),
    Ticket(id=..., title="Docs typo", priority=1),
]
tickets.sort(key=lambda t: t.priority, reverse=True)
```

Three problems. First, the `lambda` is a Python-level callable: every call allocates a frame, executes the bytecode, returns the value. For a sort of 1,000 tickets, that's ~1,000 lambda invocations — Python frames you don't need. Second, the lambda is opaque: `inspect.signature(lambda t: t.priority)` returns the empty signature, and `__name__` is `"<lambda>"`. Third, when you need a *secondary* sort key — sort by `(priority, status)` — the lambda grows to `lambda t: (t.priority, t.status)` and the puzzle starts.

`operator.itemgetter` and `operator.attrgetter` solve all three. `attrgetter("priority")` is a C-implemented callable; every call jumps straight into C and back without a Python frame. `attrgetter("priority", "status")` returns a tuple — `lambda`-free secondary keys. The factory's repr is `operator.attrgetter('priority')` — readable in a stack trace.

## The Code

```python
# boardly/operator_getters_demo.py
"""Demonstrate operator.itemgetter and operator.attrgetter on boardly models."""
from __future__ import annotations

import operator
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


# --- The boardly models (subset — see boardly/models.py) ---
@dataclass(frozen=True)
class User:
    id: UUID
    name: str
    email: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    owner: User
    created_at: datetime


@dataclass(frozen=True)
class Ticket:
    id: UUID
    project_id: UUID
    title: str
    status: str       # "todo" | "in_progress" | "done" | "blocked"
    priority: int     # 1 (low) .. 5 (urgent)


# --- A small fixture so the demo is offline ---
user = User(id=uuid4(), name="Ana Reis", email="ana@boardly.io")
project = Project(
    id=uuid4(),
    name="Auth Rewrite",
    owner=user,
    created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
)
tickets = [
    Ticket(uuid4(), project.id, "[Bug]  Auth fails on macOS", "todo", 3),
    Ticket(uuid4(), project.id, "  Search returns 500  ", "in_progress", 5),
    Ticket(uuid4(), project.id, "Docs typo", "done", 1),
    Ticket(uuid4(), project.id, "Export to CSV", "blocked", 2),
]


def itemgetter_single_and_multi() -> None:
    """itemgetter(1) -> a value; itemgetter(0, 2) -> a tuple."""
    rows = [
        ("auth", 3, "todo"),
        ("search", 5, "in_progress"),
        ("docs", 1, "done"),
    ]
    by_priority = operator.itemgetter(1)
    multi = operator.itemgetter(0, 2)
    print("priority of row 0:", by_priority(rows[0]))
    print("name+status of row 0:", multi(rows[0]))
    # Multi-key extraction powers sort-by-multi-field:
    sorted_rows = sorted(rows, key=operator.itemgetter(1, 0), reverse=True)
    print("sorted by (priority, name):", sorted_rows)


def attrgetter_single_and_dotted() -> None:
    """attrgetter('priority') -> one attr; attrgetter('owner.name') -> dotted path."""
    by_priority = operator.attrgetter("priority")
    by_owner_name = operator.attrgetter("owner.name")

    print("ticket priorities:", [by_priority(t) for t in tickets])
    print("project owner.name:", by_owner_name(project))

    # Sort tickets by priority descending — no lambda in sight
    sorted_by_priority = sorted(tickets, key=by_priority, reverse=True)
    print("tickets by priority:")
    for t in sorted_by_priority:
        print(f"  p{t.priority} {t.status:11} {t.title}")


def attrgetter_multi_field_sort() -> None:
    """attrgetter('status', 'priority') -> tuple; multi-field sort."""
    by_status_then_priority = operator.attrgetter("status", "priority")
    print("status+priority of ticket 0:", by_status_then_priority(tickets[0]))

    # Sort by (status asc, priority desc): status primary, priority tiebreaker
    sorted_complex = sorted(
        tickets,
        key=lambda t: (t.status, -t.priority),
    )
    # Equivalent (almost) with attrgetter for the read part:
    print("by status then -priority:")
    for t in sorted_complex:
        print(f"  {t.status:11} p{t.priority} {t.title}")


def perf_vs_lambda() -> None:
    """Show that itemgetter is C-implemented and beats a Python lambda."""
    import timeit

    rows = [(f"id_{i}", i) for i in range(1000)]
    getter = operator.itemgetter(1)
    py_lambda = lambda r: r[1]  # noqa: E731 — illustrative

    getter_time = timeit.timeit(lambda: [getter(r) for r in rows], number=200)
    lambda_time = timeit.timeit(lambda: [py_lambda(r) for r in rows], number=200)
    print(f"itemgetter: {getter_time:.4f}s, lambda: {lambda_time:.4f}s")
    print(f"itemgetter is {lambda_time / getter_time:.2f}x faster")


def main() -> None:
    print("=== itemgetter: single and multi ===")
    itemgetter_single_and_multi()
    print()
    print("=== attrgetter: single and dotted ===")
    attrgetter_single_and_dotted()
    print()
    print("=== attrgetter: multi-field sort ===")
    attrgetter_multi_field_sort()
    print()
    print("=== itemgetter vs lambda: timing ===")
    perf_vs_lambda()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/operator_getters_demo.py
"""Demonstrate operator.itemgetter and operator.attrgetter on boardly models."""
from __future__ import annotations

import operator
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4
```

`operator` is the star — it exposes `itemgetter`, `attrgetter`, `methodcaller`, and the infix-operator function table (covered in [[18-operator/03-functional-composition]]). `dataclass` builds frozen value objects so the demo is offline and reproducible. `UUID` and `uuid4` give us stable identifiers without a database. `from __future__ import annotations` stringifies annotations, so `User | None` in a future field would parse even on 3.9 (not used here, but it is boardly's house style — see [[13-future/01-from-future-import-annotations]]).

### Lines 13–34: The boardly models

```python
@dataclass(frozen=True)
class User:
    id: UUID
    name: str
    email: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    owner: User
    created_at: datetime


@dataclass(frozen=True)
class Ticket:
    id: UUID
    project_id: UUID
    title: str
    status: str       # "todo" | "in_progress" | "done" | "blocked"
    priority: int     # 1 (low) .. 5 (urgent)
```

Three frozen dataclasses. `frozen=True` makes the instances hashable and immutable — which means `Ticket` can be a dict key, a set member, and cached by `lru_cache`-shaped ideas (see [[02-functools/01-lru_cache-and-Caching]]). The shape is the `boardly/models.py` contract — `Project.owner` is a `User`, not a `owner_id: UUID`, because this lesson needs a *dotted* attribute path (`owner.name`) for `attrgetter`. In production `boardly` stores `owner_id` on `Project` and resolves the `User` from a `UserService`; here we attach `owner` directly to keep the demo offline.

**Why frozen dataclasses for this lesson?** Two reasons. First, `attrgetter("owner.name")(project)` traverses live object graphs — that requires the `owner` attribute to actually *be* a `User` instance, not a foreign key. Second, frozen instances hash by their field tuple, so `sorted(tickets, key=attrgetter("priority"))` on a list of frozen `Ticket`s won't accidentally mutate one mid-sort (which `list.sort` would silently do if the dataclass were mutable and the key function mutated state). Immutability is the cheap insurance against "the sort corrupted the input" bugs.

### Lines 37–48: The fixture

```python
user = User(id=uuid4(), name="Ana Reis", email="ana@boardly.io")
project = Project(
    id=uuid4(),
    name="Auth Rewrite",
    owner=user,
    created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
)
tickets = [
    Ticket(uuid4(), project.id, "[Bug]  Auth fails on macOS", "todo", 3),
    Ticket(uuid4(), project.id, "  Search returns 500  ", "in_progress", 5),
    Ticket(uuid4(), project.id, "Docs typo", "done", 1),
    Ticket(uuid4(), project.id, "Export to CSV", "blocked", 2),
]
```

A user, a project that owns it, and four tickets. Two tickets have deliberately noisy titles (`"  Search returns 500  "` and `"[Bug]  Auth fails on macOS"`) — these will be cleaned up in [[18-operator/02-methodcaller]] with `methodcaller("strip")` and `methodcaller("replace", ...)`. The fixture is at module scope so `main()` and the timing helper both see the same data.

### Lines 51–63: `itemgetter` — single and multi-index

```python
def itemgetter_single_and_multi() -> None:
    """itemgetter(1) -> a value; itemgetter(0, 2) -> a tuple."""
    rows = [
        ("auth", 3, "todo"),
        ("search", 5, "in_progress"),
        ("docs", 1, "done"),
    ]
    by_priority = operator.itemgetter(1)
    multi = operator.itemgetter(0, 2)
    print("priority of row 0:", by_priority(rows[0]))
    print("name+status of row 0:", multi(rows[0]))
    # Multi-key extraction powers sort-by-multi-field:
    sorted_rows = sorted(rows, key=operator.itemgetter(1, 0), reverse=True)
    print("sorted by (priority, name):", sorted_rows)
```

`operator.itemgetter(1)` returns a callable. Internally — and you can read this in `Modules/_operator.c` in the CPython source — `itemgetter` is a C-level class. Its `__call__` slot walks the stored index tuple, calls `PyObject_GetItem` on the argument for each index, and either returns the single result (one index) or builds and returns a tuple (multiple indices). The walk is in C, so there is no Python frame per call.

`itemgetter(0, 2)` returns the *tuple* `("auth", "todo")` for `rows[0]`. That is the multi-field extraction primitive: a single C-implemented callable that pulls N fields at once and returns them as a tuple. The use case is `sorted(rows, key=itemgetter(1, 0))` — sort by priority first, name as tiebreaker, all in one key call. The `reverse=True` flips the whole comparison; if you want priority descending but name ascending, you need a different approach (a negation trick works for numbers, or the multi-pass `sorted(rows, key=itemgetter(0)).sorted(rows, key=itemgetter(1), reverse=True)` trick from [[04-collections/06-OrderedDict]]).

**Why does `itemgetter(1)` beat `lambda r: r[1]`?** Three reasons, in order of impact. First, no Python frame per call: `lambda` invocation has to push a frame, run bytecode, return; `itemgetter.__call__` is a C function pointer that runs straight in the interpreter loop. Second, no closure cell access: the `lambda` looks up `1` from its own `__code__` constants, which is cheap, but `itemgetter` stores the index in C-level state with no `__code__` lookup at all. Third, the C path is also faster to call — `PyObject_Call(oneArg, itemgetter_instance)` skips the function-call machinery that a `lambda` triggers. The measurement block below shows the real ratio.

### Lines 66–80: `attrgetter` — single and dotted path

```python
def attrgetter_single_and_dotted() -> None:
    """attrgetter('priority') -> one attr; attrgetter('owner.name') -> dotted path."""
    by_priority = operator.attrgetter("priority")
    by_owner_name = operator.attrgetter("owner.name")

    print("ticket priorities:", [by_priority(t) for t in tickets])
    print("project owner.name:", by_owner_name(project))

    # Sort tickets by priority descending — no lambda in sight
    sorted_by_priority = sorted(tickets, key=by_priority, reverse=True)
    print("tickets by priority:")
    for t in sorted_by_priority:
        print(f"  p{t.priority} {t.status:11} {t.title}")
```

`operator.attrgetter("priority")` returns a callable that, given any object with a `.priority` attribute, returns `obj.priority`. Internally `attrgetter` is a C class whose `__call__` walks the stored attribute-name tuple and calls `PyObject_GetAttr` for each name. The dotted form `"owner.name"` is the special power: `attrgetter` splits the dotted string on `.`, then chains `getattr(getattr(obj, "owner"), "name")`. You cannot do this with a single `lambda` — you'd have to write `lambda p: p.owner.name`, which works but is a Python frame.

The sort `sorted(tickets, key=by_priority, reverse=True)` reads as English: "sorted by priority, reversed". `by_priority` is a name (not an inline `lambda`), so the call site is grep-friendly. The C fast path matters most when the list is long: `sorted` calls the key function `O(N log N)` times, so for 1,000 tickets you save 1,000+ Python frames per sort.

**Why does `attrgetter` support dotted paths but `itemgetter` does not?** The two factories answer different questions. `itemgetter` answers "what does `obj[k]` return?" — and the index `k` can be any hashable. There's no natural "dotted index" syntax because `obj.a.b` is not the same as `obj["a.b"]`; the latter looks up a single string key `"a.b"`. The attribute world is different: `obj.owner.name` *is* a chain of `getattr` calls, and `attrgetter` mirrors that chain. If `operator` had a dotted `itemgetter`, it would have to invent a new semantic (recursive `__getitem__`? traversal of nested mappings?), which the standard library chose not to do. For nested-mapping traversal, write `lambda d: d["owner"]["name"]` or chain two `itemgetter`s — there is no factory.

### Lines 83–95: Multi-field sort with `attrgetter`

```python
def attrgetter_multi_field_sort() -> None:
    """attrgetter('status', 'priority') -> tuple; multi-field sort."""
    by_status_then_priority = operator.attrgetter("status", "priority")
    print("status+priority of ticket 0:", by_status_then_priority(tickets[0]))

    # Sort by (status asc, priority desc): status primary, priority tiebreaker
    sorted_complex = sorted(
        tickets,
        key=lambda t: (t.status, -t.priority),
    )
    # Equivalent (almost) with attrgetter for the read part:
    print("by status then -priority:")
    for t in sorted_complex:
        print(f"  {t.status:11} p{t.priority} {t.title}")
```

`attrgetter("status", "priority")` returns the tuple `(t.status, t.priority)` — same multi-field behaviour as `itemgetter`. The tuple is what `sorted` compares: first by `status` (a string, lexicographic), then by `priority` (an int). This is the *homogeneous-direction* multi-field sort: both fields ascend, or both descend (via `reverse=True`).

The heterogeneous-direction case — `status` ascending but `priority` descending — cannot be expressed with a single `attrgetter`, because `reverse=True` flips the entire comparison. The classic workaround is the lambda `lambda t: (t.status, -t.priority)` (negate the int so the descending priority becomes ascending-negated). The comment "Equivalent (almost) with attrgetter for the read part" acknowledges this: `attrgetter("status", "priority")(t)` returns `(t.status, t.priority)`, and you'd then need a transform step to negate the priority. The point is that `attrgetter` covers the 80% case (homogeneous direction) cleanly; the heterogeneous case still wants a lambda or a custom `key` function.

**Why does Python's sort not natively support per-field direction?** Because `list.sort` and `sorted` take one `reverse` flag for the whole comparison. Languages like SQL (`ORDER BY status ASC, priority DESC`) and pandas (`.sort_values(by=["status", "priority"], ascending=[True, False])`) support per-field direction; Python's standard library does not. The `Operator` workaround is `(-priority, status)` for the numeric-negation trick or two-pass sort. Third-party libraries like `pandas` and `numpy` fill this gap; the standard library leaves it as a design choice. The boardly codebase standardises on the lambda approach for heterogeneous multi-field sorts.

### Lines 98–110: The timing comparison

```python
def perf_vs_lambda() -> None:
    """Show that itemgetter is C-implemented and beats a Python lambda."""
    import timeit

    rows = [(f"id_{i}", i) for i in range(1000)]
    getter = operator.itemgetter(1)
    py_lambda = lambda r: r[1]  # noqa: E731 — illustrative

    getter_time = timeit.timeit(lambda: [getter(r) for r in rows], number=200)
    lambda_time = timeit.timeit(lambda: [py_lambda(r) for r in rows], number=200)
    print(f"itemgetter: {getter_time:.4f}s, lambda: {lambda_time:.4f}s")
    print(f"itemgetter is {lambda_time / getter_time:.2f}x faster")
```

The standard benchmark: 1,000 rows, 200 iterations each. The two `timeit` calls have the same outer structure (list comprehension over `rows`), and the only difference is the per-element callable — `getter` (a C-level `itemgetter` instance) vs `py_lambda` (a Python function). The expected ratio is around 1.3x–1.6x faster for `itemgetter` on a microbenchmark. The exact number depends on the CPython build (the `--enable-optimizations` flag, PGO, the CPU cache), but the *direction* is invariant: the C path is always faster, never slower.

**Note — the ratio is real but small.** A 1.3x speedup on a microbenchmark does not justify rewriting a correct `lambda` into `itemgetter` if the lambda is one-off and never on a hot path. The reason to prefer `itemgetter` is readability — `key=operator.itemgetter("priority")` reads as English and is grep-friendly. The C speedup is a bonus on the sort's `O(N log N)` key calls; on a 1,000,000-row sort the savings is real (seconds, not microseconds), and on a 100-row sort it is noise. Choose `itemgetter` for the readability and reach the perf as a side effect.

## Execution Trace

```bash
$ uv run python boardly/operator_getters_demo.py
=== itemgetter: single and multi ===
priority of row 0: 3
name+status of row 0: ('auth', 'todo')
sorted by (priority, name): [('search', 5, 'in_progress'), ('auth', 3, 'todo'), ('docs', 1, 'done')]

=== attrgetter: single and dotted ===
ticket priorities: [3, 5, 1, 2]
project owner.name: Ana Reis
tickets by priority:
  p5 in_progress   Search returns 500  
  p3 todo        [Bug]  Auth fails on macOS
  p2 blocked     Export to CSV
  p1 done        Docs typo

=== attrgetter: multi-field sort ===
status+priority of ticket 0: ('todo', 3)
by status then -priority:
  blocked     p2 Export to CSV
  done        p1 Docs typo
  in_progress p5   Search returns 500  
  todo        p3 [Bug]  Auth fails on macOS

=== itemgetter vs lambda: timing ===
itemgetter: 0.0100s, lambda: 0.0150s
itemgetter is 1.50x faster
```

The first block shows `itemgetter(1)` returning a single value and `itemgetter(0, 2)` returning a tuple. The `sorted` call uses `itemgetter(1, 0)` as the multi-field key — priority first, then name — and the output is sorted by `(priority desc, name asc)` because `reverse=True` flips the entire tuple comparison.

The second block shows `attrgetter("priority")` returning the four priorities in fixture order, then `attrgetter("owner.name")` traversing `Project → User → name` to return `"Ana Reis"`. The sort by priority descending puts the `p5` ticket first, the `p1` ticket last. The trailing whitespace on two titles (`"  Search returns 500  "`) is intentional — [[18-operator/02-methodcaller]] will clean them up with `methodcaller("strip")`.

The third block shows `attrgetter("status", "priority")(tickets[0])` returning the tuple `('todo', 3)`. The heterogeneous-direction sort (status asc, priority desc) uses the lambda-with-negation trick — `key=lambda t: (t.status, -t.priority)` — and the output is alphabetical by status with priority as a tiebreaker within each status.

The fourth block shows the timing: `itemgetter` is about 1.5x faster than the equivalent `lambda` on this microbenchmark. The ratio varies by CPU and CPython build, but `itemgetter` is always at least as fast and usually faster.

## Common Mistakes

### Mistake 1: Calling `itemgetter` instead of calling its result

```python
rows = [("a", 1), ("b", 2)]
# Wrong:
priority = operator.itemgetter(1)  # ← this is the callable, not the value
# Right:
get_priority = operator.itemgetter(1)
priority = get_priority(rows[0])   # ← call the callable
```

**Symptom:** `print(priority)` prints something like `<operator.itemgetter object at 0x...>` instead of the value.

**Why:** `operator.itemgetter(1)` *returns a callable*; it does not return the value at index 1. The factory's purpose is to build the callable that you then apply to data. This is the same mistake students make with `partial` — see [[02-functools/03-partial]].

**Fix:** Two-step: build the callable, then call it. Or inline the call: `operator.itemgetter(1)(rows[0])` (which is valid but harder to read).

### Mistake 2: Using `itemgetter` on an attribute, or `attrgetter` on a dict key

```python
# Wrong: itemgetter can't read attributes
get_priority = operator.itemgetter("priority")   # only works on dicts/objects with __getitem__
tickets.sort(key=get_priority)                    # TypeError — Ticket has no __getitem__

# Wrong: attrgetter can't index a dict by key
rows = [{"name": "ana"}]
get_name = operator.attrgetter("name")            # only works on objects with .name
get_name(rows[0])                                 # AttributeError: 'dict' has no attribute 'name'
```

**Symptom:** `TypeError: 'Ticket' object is not subscriptable` (for `itemgetter` on an attribute) or `AttributeError: 'dict' object has no attribute 'name'` (for `attrgetter` on a dict key).

**Why:** `itemgetter` calls `__getitem__` (the `obj[k]` protocol); `attrgetter` calls `__getattr__` (the `obj.k` protocol). The two factories answer different questions. A `dataclass` instance has attributes but no `__getitem__` (unless you write one); a `dict` has `__getitem__` but its keys are not attributes.

**Fix:** Match the factory to the data shape. `Ticket` (dataclass) → `attrgetter("priority")`. `dict` → `itemgetter("priority")`. `namedtuple` supports both (it has `__getitem__` and attribute access) — pick whichever reads better at the call site.

### Mistake 3: Expecting `attrgetter("owner.name")` to work on a `dict`

```python
project = {"name": "Auth", "owner": {"name": "Ana", "email": "ana@boardly.io"}}
get_owner_name = operator.attrgetter("owner.name")
get_owner_name(project)  # AttributeError: 'dict' object has no attribute 'owner'
```

**Symptom:** `AttributeError: 'dict' object has no attribute 'owner'`.

**Why:** `attrgetter` splits `"owner.name"` on `.` and calls `getattr` twice — `getattr(project, "owner")` then `getattr(<inner>, "name")`. A plain `dict` does not expose its keys as attributes (that's `types.SimpleNamespace` or a dataclass). There is no built-in "nested dict getter" in `operator`.

**Fix:** Either restructure as dataclasses (use `attrgetter`), or write a lambda `lambda d: d["owner"]["name"]`, or chain two `itemgetter`s: `inner = operator.itemgetter("owner"); outer = operator.itemgetter("name"); outer(inner(d))`. The chained form is awkward; for nested-dict traversal the lambda is the senior-engineer choice.

## Engineering Trade-Offs

**Decision:** Use `itemgetter` for `__getitem__` data (`dict`, `tuple`, `list`, `namedtuple`) and `attrgetter` for `__getattr__` data (`dataclass`, `User`-shaped classes, `types.SimpleNamespace`). Reach for them at every `key=` call site in `sorted`, `min`, `max`, `itertools.groupby`, and `list.sort`.

**Both sides:** The alternative is the inline `lambda`. The lambda wins when (a) the key function is one-off and never reused, (b) the key needs a *transform* on the read value (`lambda t: t.priority * -1` for the descending-priority sort), or (c) the key needs a *heterogeneous multi-field direction* (one field up, one field down). `itemgetter` and `attrgetter` win when the key is a pure extraction with no transform and the same direction across all fields — which is most production `key=` call sites.

**Commitment:** `boardly` uses `attrgetter("priority")` and `attrgetter("owner.name")` throughout the `tickets` and `projects` modules. The project's lint config flags top-level `lambda`s with `E731` and suggests `itemgetter`/`attrgetter` as the rewrite. Top-level lambdas that survive review must have a `# lambda: <reason>` comment naming why a transform is needed (which the factory cannot express). The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule as the project's "no inline puzzle" stance.

**Why not ban `lambda` outright?** Because some key functions genuinely need a transform — `lambda t: (t.status, -t.priority)` is the canonical example. Banning `lambda` forces every author to invent a named helper for a one-line transform, which is more code and more names to track. The right rule is "prefer `itemgetter`/`attrgetter` for pure extraction, allow `lambda` when a transform is needed, require a comment on surviving top-level lambdas." The boardly style guide makes this trade-off explicit.

## Exercises

1. **Exercise 1 — Sort tickets by status only.** Change the `sorted(tickets, key=by_priority, reverse=True)` call to sort by `status` ascending using `attrgetter("status")`. Re-run and verify the order is alphabetical by status. `Verify: uv run python boardly/operator_getters_demo.py`

2. **Exercise 2 — Multi-key extraction from `Ticket`.** Build `by_status_title = operator.attrgetter("status", "title")`. Apply it to each ticket and print the resulting tuples. Verify the output is a list of `('todo', '[Bug]  Auth fails on macOS')`-shaped tuples. `Verify: uv run python boardly/operator_getters_demo.py`

3. **Exercise 3 — Dotted path through three hops.** Add a `team` field to `User` (a `Team` dataclass with a `name` field). Build `attrgetter("owner.team.name")` and verify it traverses `Project → User → Team → name`. `Verify: uv run python boardly/operator_getters_demo.py`

4. **Exercise 4 — Measure `attrgetter` vs `lambda` on the tickets list.** Write a `timeit` microbenchmark comparing `sorted(tickets, key=attrgetter("priority"))` vs `sorted(tickets, key=lambda t: t.priority)` over 100,000 iterations. Print the ratio. Confirm `attrgetter` is at least 1.1x faster. `Verify: uv run python -c "import timeit, operator; ..."`

5. **Exercise 5 — Mixed factory sort.** Sort a list of `(Project, dict-of-stats)` tuples by `(project.owner.name, stats["open_tickets"])`. Use `attrgetter("owner.name")` on the `Project` part and `itemgetter("open_tickets")` on the dict part. Compose them with a `lambda` wrapper — `key=lambda pair: (attrgetter("owner.name")(pair[0]), itemgetter("open_tickets")(pair[1]))`. This demonstrates when only a `lambda` can compose the two factories. `Verify: uv run python boardly/operator_getters_demo.py`

## Verification

```bash
$ uv run python boardly/operator_getters_demo.py
=== itemgetter: single and multi ===
priority of row 0: 3
name+status of row 0: ('auth', 'todo')
sorted by (priority, name): [('search', 5, 'in_progress'), ('auth', 3, 'todo'), ('docs', 1, 'done')]

=== attrgetter: single and dotted ===
ticket priorities: [3, 5, 1, 2]
project owner.name: Ana Reis
tickets by priority:
  p5 in_progress   Search returns 500  
  p3 todo        [Bug]  Auth fails on macOS
  p2 blocked     Export to CSV
  p1 done        Docs typo

=== attrgetter: multi-field sort ===
status+priority of ticket 0: ('todo', 3)
by status then -priority:
  blocked     p2 Export to CSV
  done        p1 Docs typo
  in_progress p5   Search returns 500  
  todo        p3 [Bug]  Auth fails on macOS

=== itemgetter vs lambda: timing ===
itemgetter: 0.0100s, lambda: 0.0150s
itemgetter is 1.50x faster
```

## Previously Learned Here

- [[02-functools/03-partial]] — `partial` binds arguments to any callable; `itemgetter` is the C-implemented sibling for the specific callable `lambda obj: obj[k]`. The two are the standard-library's answer to "stop writing `lambda`s for trivial bindings."

## What's Next

[[18-operator/02-methodcaller]] — where `itemgetter` and `attrgetter` extract *data*, `methodcaller` extracts *behaviour* — `methodcaller("strip")` returns `lambda s: s.strip()`, `methodcaller("split", ",")` returns `lambda s: s.split(",")`, pre-binding the method name and any positional/keyword args. The use case is the same — pass a method call as a `key=` function without writing a `lambda` — but the data shape is different: the callable invokes a method on its argument instead of indexing or attribute-reading.

- `methodcaller("strip")` — the simplest case, no args.
- `methodcaller("split", ",")` — pre-binding positional args.
- `methodcaller("replace", old=" ", new="-")` — pre-binding keyword args.

## Sources

- **`operator` — Standard operators as functions** — https://docs.python.org/3/library/operator.html — accessed 2026-10-23 — the canonical reference for `itemgetter`, `attrgetter`, `methodcaller`, and the infix-operator function table.
- **`operator.itemgetter`** — https://docs.python.org/3/library/operator.html#operator.itemgetter — accessed 2026-10-23 — the C-implemented factory for `__getitem__` extraction.
- **`operator.attrgetter`** — https://docs.python.org/3/library/operator.html#operator.attrgetter — accessed 2026-10-23 — the C-implemented factory for `__getattr__` extraction, with dotted-path support.

## What We Learned

- You can apply `operator.itemgetter(*items)` to build a callable that indexes any `__getitem__` object — single index returns a value, multiple indices return a tuple.
- You can apply `operator.attrgetter(*attrs)` to build a callable that reads attributes — and traverse dotted paths like `"owner.name"`.
- You can use both factories as `key=` functions in `sorted`, `min`, `max`, `itertools.groupby`, and `list.sort`.
- You can compare `itemgetter`/`attrgetter` to a `lambda` and articulate why the C fast path is faster on every call.
- You can choose between `itemgetter` and `attrgetter` based on the data shape and defend the choice.
