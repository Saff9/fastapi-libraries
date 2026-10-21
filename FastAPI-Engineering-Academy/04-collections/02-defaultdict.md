---
title: "Lesson 02: defaultdict"
aliases:
 - collections.defaultdict
 - defaultdict
tags:
 - collections
 - defaultdict
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[04-collections/01-Counter]]"
related_lessons:
 - "[[04-collections/03-deque]]"
 - "[[04-collections/06-OrderedDict]]"
first_taught_in: "04-collections/02-defaultdict"
---

# Lesson 02: defaultdict

*`collections.defaultdict` — the `dict` subclass that lets you write `groups[t.assignee_id].append(t)` without the `if assignee_id not in groups` guard, by calling a `default_factory` on every missing key.*

**You're at the very beginning of Section 04 — Lesson 02.**

`defaultdict` is `Counter`'s more general sibling. Where `Counter`'s default is the integer zero, `defaultdict`'s default is "whatever `default_factory` returns". The factory is almost always `list`, `set`, or `int`, but it can be any zero-argument callable — a `lambda`, a class, a `functools.partial`. This lesson walks the protocol, the gotchas, and the decision between `defaultdict` and `dict.setdefault`.

Take your time. Type every example. **This is how you learn.**

#collections #defaultdict #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `defaultdict`** with the right `default_factory` for a given problem (`list`, `set`, `int`, custom).
2. **Explain the `__missing__` protocol** — what Python does internally when you read a missing key, and how `defaultdict` and `Counter` both lean on it.
3. **Choose between `defaultdict` and `dict.setdefault`** for a given mutation pattern, and name the one case where `setdefault` wins.
4. **Spot the `None`-factory gotcha** before it bites you.

## Prerequisites

Before starting, you need:

- **[[04-collections/01-Counter]]** — `Counter` is also a `dict` subclass that overrides `__missing__`; reading it first makes this lesson's protocol section a recap instead of a cold start.
- **About 25 minutes of focused time.**

**The most common gap: not realising `defaultdict` only calls the factory on `__getitem__`, not on `__contains__` or `.get()`.**

Students hit `defaultdict(list)`, see it create lists for missing keys, and assume the factory fires for every access. It does not. `d.get(missing_key)` returns `None` (no factory call); `missing_key in d` returns `False` (no factory call); only `d[missing_key]` fires the factory. If you do not internalise that, you will write a bug that mutates state in what you thought was a read path.

## The Problem

Here is the bug. `boardly` has a dashboard that shows tickets grouped by assignee. The first implementation everyone writes:

```python
def group_by_assignee(tickets: list[Ticket]) -> dict[UUID, list[Ticket]]:
    groups: dict[UUID, list[Ticket]] = {}
    for t in tickets:
        if t.assignee_id is None:
            continue
        if t.assignee_id not in groups:
            groups[t.assignee_id] = []
        groups[t.assignee_id].append(t)
    return groups
```

Six lines of which three are bookkeeping. Multiply by every endpoint that groups anything — tickets by project, projects by owner, audit events by user. The bookkeeping is the same every time and the bug surface is the same every time: the `if k not in groups` guard is the line a junior engineer forgets, getting a `KeyError` on the next line.

`defaultdict(list)` exists to delete the guard. With it, the function becomes:

```python
def group_by_assignee(tickets: list[Ticket]) -> dict[UUID, list[Ticket]]:
    groups: defaultdict[UUID, list[Ticket]] = defaultdict(list)
    for t in tickets:
        if t.assignee_id is not None:
            groups[t.assignee_id].append(t)
    return groups
```

Four lines, zero bookkeeping, zero `KeyError` surface.

## The Code

```python
# boardly/grouping.py
"""Group tickets by various keys using collections.defaultdict."""
from collections import defaultdict
from uuid import UUID
from boardly.models import Ticket


def group_by_assignee(tickets: list[Ticket]) -> defaultdict[UUID, list[Ticket]]:
    """Map assignee_id -> list of tickets assigned to that user."""
    groups: defaultdict[UUID, list[Ticket]] = defaultdict(list)
    for t in tickets:
        if t.assignee_id is not None:
            groups[t.assignee_id].append(t)
    return groups


def unique_statuses_per_project(tickets: list[Ticket]) -> defaultdict[UUID, set[str]]:
    """Map project_id -> set of statuses seen on that project's tickets."""
    groups: defaultdict[UUID, set[str]] = defaultdict(set)
    for t in tickets:
        groups[t.project_id].add(t.status)
    return groups


def count_tickets_per_project(tickets: list[Ticket]) -> defaultdict[UUID, int]:
    """Map project_id -> number of tickets. Same shape as Counter, mutable."""
    groups: defaultdict[UUID, int] = defaultdict(int)
    for t in tickets:
        groups[t.project_id] += 1
    return groups


def first_ticket_per_status(tickets: list[Ticket]) -> defaultdict[str, Ticket | None]:
    """Map status -> first ticket seen with that status (or None if none yet).

    Uses a custom factory: a closure over a mutable cell.
    """
    seen: dict[str, bool] = {}

    def _first_or_none() -> Ticket | None:
        return None  # placeholder; the loop overwrites immediately

    groups: defaultdict[str, Ticket | None] = defaultdict(_first_or_none)
    for t in tickets:
        groups[t.status] = t   # always overwrites; the factory only fires on first read of a NEW key
    return groups


if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    p1, p2 = uuid4(), uuid4()
    u1, u2 = uuid4(), uuid4()
    sample = [
        Ticket(uuid4(), p1, "t1", u1, "todo", 2),
        Ticket(uuid4(), p1, "t2", u2, "in_progress", 3),
        Ticket(uuid4(), p2, "t3", u1, "todo", 4),
        Ticket(uuid4(), p2, "t4", u1, "done", 1),
    ]
    by_assignee = group_by_assignee(sample)
    print("by_assignee:", {k: len(v) for k, v in by_assignee.items()})
    print("statuses per project:", {str(k): sorted(v) for k, v in unique_statuses_per_project(sample).items()})
    print("counts per project:", dict(count_tickets_per_project(sample)))
```

## Line-by-Line Deep Dive

### Lines 1–4: Imports

```python
# boardly/grouping.py
"""Group tickets by various keys using collections.defaultdict."""
from collections import defaultdict
from uuid import UUID
from boardly.models import Ticket
```

`from collections import defaultdict`. Same top-level location as `Counter`. The class name is lowercased (it is one of three lowercased classes in `collections`, the other two being `deque` and `OrderedDict` — the lowercase is a hint that they are usually used as drop-in replacements for `dict`/`list` literals).

### Lines 7–13: `defaultdict(list)` — the canonical use case

```python
def group_by_assignee(tickets: list[Ticket]) -> defaultdict[UUID, list[Ticket]]:
    """Map assignee_id -> list of tickets assigned to that user."""
    groups: defaultdict[UUID, list[Ticket]] = defaultdict(list)
    for t in tickets:
        if t.assignee_id is not None:
            groups[t.assignee_id].append(t)
    return groups
```

`defaultdict(list)` — the argument is `list`, the *type itself*, not an instance. `default_factory` is a callable that takes zero arguments; `list()` constructs an empty list. Calling `defaultdict(list)` stores `list` as the factory; every missing-key access calls `list()` to materialise the default.

`groups[t.assignee_id].append(t)` — Python evaluates this as:

1. `groups[t.assignee_id]` — `dict.__getitem__` looks for `t.assignee_id`. It is absent.
2. `dict.__getitem__` calls `groups.__missing__(t.assignee_id)` (the `defaultdict` override).
3. `__missing__` calls `self.default_factory()` — that is `list()` — which returns `[]`.
4. `__missing__` stores `self[key] = []` and returns `[]`.
5. The `[]` list now has `.append(t)` called on it.

**Why store the default in the dict?** So that the *next* access of the same key does not fire the factory again — and so that `for k, v in groups.items()` reflects all the keys you have ever touched. If `__missing__` returned the default without storing it, you would create-and-discard on every read, and `groups.items()` would be empty until you wrote. Storing is the right call.

### Lines 17–22: `defaultdict(set)` — when order does not matter and duplicates should collapse

```python
def unique_statuses_per_project(tickets: list[Ticket]) -> defaultdict[UUID, set[str]]:
    """Map project_id -> set of statuses seen on that project's tickets."""
    groups: defaultdict[UUID, set[str]] = defaultdict(set)
    for t in tickets:
        groups[t.project_id].add(t.status)
    return groups
```

`defaultdict(set)` is the "group, but dedupe" shape. `set()` is the factory; `.add()` is the write. The result is `dict[UUID, set[str]]` — a dict whose values are sets. If two tickets on the same project have status `"todo"`, the set has `"todo"` once.

**Why not use `Counter` here?** Because we want a set, not a count. `Counter` answers "how many of each"; `defaultdict(set)` answers "which distinct values appeared".

### Lines 26–31: `defaultdict(int)` — the `Counter`-equivalent that is mutable and signed

```python
def count_tickets_per_project(tickets: list[Ticket]) -> defaultdict[UUID, int]:
    """Map project_id -> number of tickets. Same shape as Counter, mutable."""
    groups: defaultdict[UUID, int] = defaultdict(int)
    for t in tickets:
        groups[t.project_id] += 1
    return groups
```

`defaultdict(int)` and `Counter` are nearly the same shape for "count things" — both fire `int()` on a missing key, both yield zero. The difference is in the *extras*: `Counter` ships `.most_common`, `.elements`, `+`/`-`/`&`/`|`; `defaultdict(int)` ships nothing extra.

Use `Counter` when you will *read ranked counts* (`.most_common`). Use `defaultdict(int)` when you will *mutate counts in a non-trivial way* — decrementing on ticket-close, capping at a max, writing signed deltas. `Counter`'s `-` operator drops negative counts, which is wrong for "decrement a running count" code.

### Lines 35–46: A custom factory — the closure-over-a-cell pattern

```python
def first_ticket_per_status(tickets: list[Ticket]) -> defaultdict[str, Ticket | None]:
    """Map status -> first ticket seen with that status (or None if none yet).

    Uses a custom factory: a closure over a mutable cell.
    """
    seen: dict[str, bool] = {}

    def _first_or_none() -> Ticket | None:
        return None  # placeholder; the loop overwrites immediately

    groups: defaultdict[str, Ticket | None] = defaultdict(_first_or_none)
    for t in tickets:
        groups[t.status] = t   # always overwrites; the factory only fires on first read of a NEW key
    return groups
```

`defaultdict(_first_or_none)` — any zero-argument callable works. The factory here is `_first_or_none`, a closure that returns `None`. The body of the function is a placeholder; in practice the loop always writes a real `Ticket` before anyone reads. The factory exists to provide a sensible default if someone reads a key the loop never wrote.

**Why show this pattern?** Because the next step is a stateful factory — one that increments an internal counter, or one that returns a thread-local default. Reading this pattern once means the production version (a factory that consults a `contextvars.ContextVar`) is no surprise.

### Lines 49–63: The `__main__` smoke test

```python
if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    p1, p2 = uuid4(), uuid4()
    u1, u2 = uuid4(), uuid4()
    sample = [
        Ticket(uuid4(), p1, "t1", u1, "todo", 2),
        Ticket(uuid4(), p1, "t2", u2, "in_progress", 3),
        Ticket(uuid4(), p2, "t3", u1, "todo", 4),
        Ticket(uuid4(), p2, "t4", u1, "done", 1),
    ]
    by_assignee = group_by_assignee(sample)
    print("by_assignee:", {k: len(v) for k, v in by_assignee.items()})
    print("statuses per project:", {str(k): sorted(v) for k, v in unique_statuses_per_project(sample).items()})
    print("counts per project:", dict(count_tickets_per_project(sample)))
```

The smoke test exercises all three factories (`list`, `set`, `int`) plus the closure factory. The expected output is in the Execution Trace below.

## Execution Trace

```bash
$ uv run python boardly/grouping.py
by_assignee: {UUID('...'): 3, UUID('...'): 1}
statuses per project: {'...': ['in_progress', 'todo'], '...': ['done', 'todo']}
counts per project: {UUID('...'): 2, UUID('...'): 2}
```

The UUIDs print with `UUID('...')` prefix because the default `__repr__` of `UUID` includes the type name. The set's items print sorted because we wrap the print in `sorted(v)`.

## Common Mistakes

### Mistake 1: The `None`-factory gotcha

```python
d = defaultdict()   # no factory
d["missing"]         # student expects []
```

**Symptom:** `KeyError: 'missing'` raised inside `defaultdict.__missing__`.

**Why:** When `defaultdict` is constructed without an argument, `default_factory` is `None`. `__missing__` checks `if self.default_factory is None: raise KeyError(key)` and only calls the factory otherwise. So a no-arg `defaultdict()` is just a `dict` with extra steps.

**Fix:** Always pass a factory. If you want a real no-default dict, use `dict`. If you want a `defaultdict` whose default is "absent", that is a contradiction — `defaultdict` only makes sense with a factory.

### Mistake 2: Calling `.get(missing)` and being surprised by `None`

```python
d = defaultdict(list)
result = d.get("never_seen")   # student expects []
```

**Symptom:** `result` is `None`, not `[]`. The student expected the factory to fire.

**Why:** `defaultdict.__missing__` only fires from `__getitem__` (`d[k]`). `dict.get` calls `__getitem__` inside a `try/except KeyError` and returns the `None` default on `KeyError`. Because `__missing__` would have created the key, the only way for `get` to see a `KeyError` is when `default_factory` is `None` — and in that case `get` returns its own `default` argument (which is `None` by default).

**Fix:** Use `d["never_seen"]` if you want the factory to fire. Use `d.get("never_seen", [])` if you want a default without mutating the dict.

### Mistake 3: `setdefault` with a mutable default that gets built every iteration

```python
groups = {}
for t in tickets:
    groups.setdefault(t.assignee_id, []).append(t)
```

**Symptom:** No bug — but the code is slower than `defaultdict(list)` for large inputs and the line is longer.

**Why:** `dict.setdefault(k, default)` evaluates `default` *before* deciding whether to use it. Every iteration constructs a fresh `[]`, then throws it away if the key already exists. For `list` the cost is tiny; for `set()` or a `list`-of-lists it is measurable on big inputs. `defaultdict(list)` constructs the default once per *new* key, never per *iteration*.

**Fix:** Use `defaultdict(list)` for the "group items" pattern. Reserve `setdefault` for the case where you need the default only on the *first* write to a key (see Trade-Offs).

## Engineering Trade-Offs

**Decision:** Use `defaultdict` for the group/mutate pattern; use `dict.setdefault` only when the default is expensive to build and you want it built at most once.

**Both sides:** `defaultdict` is shorter, faster, and reads better in the group pattern. `setdefault` wins in one specific case: when the default is expensive to construct (say, a large nested structure or a database lookup result) and you want it constructed only on the first write — but you also want the dict to behave like a plain `dict` outside that one call. In that case `setdefault` keeps the default evaluation lazy and explicit.

There is a third option: `try/except KeyError`. It is the fastest *if* the key is usually present (because exceptions are cheap when they do not fire). For the group pattern, where most keys are absent at first and present later, `defaultdict` beats `try/except`.

**Commitment:** `boardly/grouping.py` uses `defaultdict` for all group patterns. When a single function needs a one-off default on one key, it uses `try/except KeyError` inline — `setdefault` is reserved for the rare "expensive default, want lazy construction, want plain `dict`" case, which has not yet appeared in the codebase.

## Exercises

1. **Exercise 1 — Add `group_by_project`.** Write `def group_by_project(tickets: list[Ticket]) -> defaultdict[UUID, list[Ticket]]` mirroring `group_by_assignee`. `Verify: uv run python -c "import boardly.grouping as g; print(hasattr(g,'group_by_project'))"`
2. **Exercise 2 — Trigger the `None`-factory gotcha.** Construct a `defaultdict()` with no argument and access a missing key. Confirm you get a `KeyError`. `Verify: uv run python -c "from collections import defaultdict; d=defaultdict(); \ntry:\n  d['x']\nexcept KeyError as e:\n  print('KeyError:', e)"`
3. **Exercise 3 — Compare `setdefault` vs `defaultdict` timing.** Build a list of 100,000 random UUIDs and group them with both approaches. Time both with `timeit`. `Verify: uv run python -c "from collections import defaultdict; from uuid import uuid4; import timeit; data=[uuid4() for _ in range(100_000)]; s='''\\nfrom collections import defaultdict\\ndata=[uuid4() for _ in range(100_000)]\\ng=defaultdict(list)\\nfor x in data: g[x].append(x)\\n'''; print(timeit.timeit(s, number=5))"`
4. **Exercise 4 — A `defaultdict` with a `lambda: 0`.** Confirm that `defaultdict(lambda: 0)` behaves identically to `defaultdict(int)` for counting. `Verify: uv run python -c "from collections import defaultdict; d=defaultdict(lambda:0); d['x']+=1; print(d)"`
5. **Exercise 5 — A stateful factory.** Write a `defaultdict` whose factory returns an incrementing integer (the first missing key gets `0`, the second missing key gets `1`, etc.). Hint: closure over a list with one int. `Verify: uv run python -c "from collections import defaultdict; cell=[0]; d=defaultdict(lambda: cell[0] or (cell.__setitem__(0, cell[0]+1) or cell[0])); print(d['a'], d['b'], d['a'])"`

## Verification

```bash
$ uv run python boardly/grouping.py
by_assignee: {UUID('...'): 3, UUID('...'): 1}
statuses per project: {'...': ['in_progress', 'todo'], '...': ['done', 'todo']}
counts per project: {UUID('...'): 2, UUID('...'): 2}
```

## Previously Learned Here

- [[04-collections/01-Counter]] — `Counter` is also a `dict` subclass that overrides `__missing__`. This lesson generalises that protocol to any factory.
- [[04-collections/00-collections-MOC]] — the section map and the `boardly` models.

## What's Next

[[04-collections/03-deque]] — leave dict-land and enter sequence-land. `deque` is the `collections` class for double-ended queues: O(1) `appendleft` and `popleft`, an optional `maxlen` that turns it into a fixed-size ring buffer, and a `rotate()` method that is the cheapest way to "shift everything by N". It is the class FastAPI itself uses for its middleware stack. We will see why, and when `deque` beats `list`.

## Sources

- **Python `collections.defaultdict` documentation** — https://docs.python.org/3/library/collections.html#collections.defaultdict — accessed 2026-10-23 — the canonical reference for `default_factory`, the `__missing__` protocol, and the `None`-factory behaviour.
- **CPython `defaultdict` source** — https://github.com/python/cpython/blob/3.12/Lib/collections/__init__.py#L923 — accessed 2026-10-23 — the actual implementation, written in Python, around 80 lines.
- **What's New in Python 2.5 — `defaultdict`** — https://docs.python.org/2/whatsnew/2.5.html#pep-3106-making-dict-a-mapping — accessed 2026-10-23 — historical context for `defaultdict`'s addition and the `setdefault` pain it replaced (the CPython team adopted Raymond Hettinger's recipe; no dedicated PEP).

## What We Learned

- `defaultdict(default_factory)` stores the factory and calls it inside `__missing__` on every read of a missing key.
- The factory is called per *new key*, not per *access* — `__missing__` stores the default back into the dict before returning.
- `.get()` does NOT fire the factory; only `__getitem__` (`d[k]`) does.
- `defaultdict(int)` is `Counter` without the extras — use it for mutable signed counts.
- `defaultdict(list)` is the canonical "group items" pattern and replaces the `if k not in d` guard.
