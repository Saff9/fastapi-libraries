---
title: "Lesson 01: Counter"
aliases:
 - collections.Counter
 - Counter
tags:
 - collections
 - counter
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[04-collections/02-defaultdict]]"
 - "[[04-collections/06-OrderedDict]]"
first_taught_in: "04-collections/01-Counter"
---

# Lesson 01: Counter

*`collections.Counter` — the dict subclass that turns "count how many times each ticket status appears" from a six-line `defaultdict` loop into one line, and then gives you `.most_common(n)` for free.*

**You're at the very beginning of Section 04.**

`Counter` is the gentlest possible introduction to `collections`. It is a `dict` subclass with a counting-shaped default and four arithmetic operators. Once you have read this lesson you will see why the entire module is shaped the way it is — small, focused, doing exactly one thing — and you will be ready for `defaultdict`, `deque`, and the rest of the section.

Take your time. Type every example. **This is how you learn.**

#collections #counter #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `Counter`** from any iterable of hashable items, and explain what Python does internally for each input shape.
2. **Use `.most_common(n)`** to pull the top-N entries — and explain why it uses `heapq.nlargest` internally rather than a full sort.
3. **Combine counters with `+`, `-`, `&`, `|`** and predict the result of each operator without running it.
4. **Choose between `Counter` and `defaultdict(int)`** for a given counting problem, and defend the choice.

## Prerequisites

Before starting, you need:

- **Basic `dict` literacy** — you have written `{k: v for k, v in items}` and you know what `dict.get(k, default)` does.
- **About 20 minutes of focused time.**

**The most common gap: forgetting that `Counter` is a `dict` subclass.**

Students who hit `Counter` cold tend to memorise "it's a thing for counting" and never see that every `dict` method (`keys`, `values`, `items`, `__getitem__`, `__setitem__`, `update`) works on a `Counter` exactly the same way. That makes the API feel twice as large as it is. Read this lesson with `dict` in the back of your mind.

## The Problem

Here is the bug. `boardly` exposes a dashboard endpoint that returns the count of tickets in each status. The first implementation everyone writes looks like this:

```python
def ticket_status_counts(tickets: list[Ticket]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tickets:
        if t.status not in counts:
            counts[t.status] = 0
        counts[t.status] += 1
    return counts
```

This is correct. It is also six lines that you will write a thousand times in your career. The bug is not in this code — the bug is in what happens next. The product team asks for "the top three statuses by ticket count" and you write:

```python
sorted_counts = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
top_three = sorted_counts[:3]
```

Now you have eight lines for something that should be one. Worse: a junior engineer on your team writes the same eight lines next sprint, slightly differently, and a reviewer has to argue about whether `reverse=True` belongs on the `sorted` call or the slice. Multiply by every dashboard endpoint, every metrics endpoint, every "group-and-rank" task.

`collections.Counter` exists to make that whole class of problem one line. It is a `dict` subclass, so it composes with everything you already know — but its `__missing__` returns `0`, its constructor accepts any iterable, and it ships `.most_common(n)` and four arithmetic operators.

## The Code

```python
# boardly/metrics.py
"""Ticket-status counting with collections.Counter."""
from collections import Counter
from boardly.models import Ticket


def status_counts(tickets: list[Ticket]) -> Counter:
    """Return a Counter of status -> ticket count."""
    return Counter(t.status for t in tickets)


def top_n_statuses(tickets: list[Ticket], n: int = 3) -> list[tuple[str, int]]:
    """Return the top-n statuses by ticket count, descending."""
    return status_counts(tickets).most_common(n)


def merge_sprint_counts(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Combine two sprints' tickets; overlapping statuses add."""
    return Counter(t.status for t in sprint_a) + Counter(t.status for t in sprint_b)


def shared_statuses(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Statuses present in BOTH sprints, min count."""
    return Counter(t.status for t in sprint_a) & Counter(t.status for t in sprint_b)


def expand_to_repeated_statuses(tickets: list[Ticket]) -> list[str]:
    """Yield each status once per ticket with that status."""
    c = status_counts(tickets)
    return list(c.elements())


if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    proj = uuid4()
    sample = [
        Ticket(uuid4(), proj, "write docs",   None,    "todo",        2),
        Ticket(uuid4(), proj, "fix login",    uuid4(), "in_progress", 4),
        Ticket(uuid4(), proj, "ship release", uuid4(), "in_progress", 5),
        Ticket(uuid4(), proj, "triage",       None,    "todo",        1),
        Ticket(uuid4(), proj, "done item",    uuid4(), "done",        2),
    ]
    print("counts:", status_counts(sample))
    print("top 2:", top_n_statuses(sample, 2))
    print("elements:", expand_to_repeated_statuses(sample))
```

## Line-by-Line Deep Dive

### Lines 1–4: Imports and module docstring

```python
# boardly/metrics.py
"""Ticket-status counting with collections.Counter."""
from collections import Counter
from boardly.models import Ticket
```

`from collections import Counter` is the canonical import path. `Counter` lives at the top of the `collections` module, not under `collections.abc` — that is the first thing to get straight, because `collections.abc` (Section 05) is a different module entirely.

The docstring is the only documentation many of your coworkers will read. Be specific about what the module does and which `collections` class it leans on.

### Lines 7–10: `status_counts` — the constructor that accepts an iterable

```python
def status_counts(tickets: list[Ticket]) -> Counter:
    """Return a Counter of status -> ticket count."""
    return Counter(t.status for t in tickets)
```

`Counter(t.status for t in tickets)` — the constructor accepts any iterable, including a generator expression. Internally `Counter.__init__` does roughly `self.update(iterable)` where `update` walks the iterable and increments `self[item]` for each item. The increment path goes through `__getitem__`, which (because `Counter` overrides `__missing__` to return `0`) creates the key on first touch with value `0 + 1 = 1`.

**Why does the constructor accept a dict too?** If you pass `Counter({"todo": 3, "done": 5})`, the constructor reads counts from the dict's values directly. This is the bridge from "I already have a dict" to "now I want `.most_common`" — and it is the cheapest way to convert a hand-built count dict to a Counter.

### Lines 13–16: `.most_common(n)` — the killer method

```python
def top_n_statuses(tickets: list[Ticket], n: int = 3) -> list[tuple[str, int]]:
    """Return the top-n statuses by ticket count, descending."""
    return status_counts(tickets).most_common(n)
```

`.most_common(n)` returns a list of `(key, count)` tuples, sorted descending by count. Calling `.most_common()` with no argument returns *all* items in descending count order — equivalent to `sorted(c.items(), key=lambda kv: kv[1], reverse=True)`.

Internally, for `n < len(self)`, `most_common` uses `heapq.nlargest(n, self.items(), key=_itemgetter(1))` — an O(N log n) algorithm rather than an O(N log N) full sort. For a boardly project with 50,000 tickets across 5 statuses that is unmeasurable; for a system with millions of distinct keys it is the difference between a 200 ms endpoint and a 50 ms one.

**Why return a list of tuples and not a list of keys?** Because the count is the second half of the answer. If you only want the keys: `[k for k, _ in c.most_common(n)]`. The tuple shape keeps the count visible, which is what dashboards want.

### Lines 19–22: `+` — arithmetic that adds counts

```python
def merge_sprint_counts(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Combine two sprints' tickets; overlapping statuses add."""
    return Counter(t.status for t in sprint_a) + Counter(t.status for t in sprint_b)
```

`Counter.__add__` walks the keys of both counters and produces `c1[k] + c2[k]` for each key, dropping any key whose result is `<= 0` (which can happen with `-` but never with `+`). The result is a fresh `Counter` — neither operand is mutated.

`+` is the natural choice for "combine two metrics windows". If sprint A had `{"todo": 4, "in_progress": 2}` and sprint B had `{"todo": 1, "done": 3}`, the sum is `{"todo": 5, "in_progress": 2, "done": 3}`. That is the dashboard's "this quarter so far" number.

### Lines 25–28: `&` — intersection keeps the min

```python
def shared_statuses(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Statuses present in BOTH sprints, min count."""
    return Counter(t.status for t in sprint_a) & Counter(t.status for t in sprint_b)
```

`&` is intersection: `min(c1[k], c2[k])` for each key in either counter, dropping keys absent from one side (because `min(x, 0)` would be `0`, and `0` counts are dropped). The mirror operator `|` is union: `max(c1[k], c2[k])` for each key.

**Why `&` returns min and `|` returns max:** `Counter` mimics multisets. Multiset intersection keeps the smaller multiplicity ("how many of this item are in BOTH bags?"), multiset union keeps the larger ("how many are in either bag, counting duplicates only once"). Once you internalise that, `&` and `|` stop feeling arbitrary.

### Lines 31–35: `.elements()` — the round-trip back to an iterable

```python
def expand_to_repeated_statuses(tickets: list[Ticket]) -> list[str]:
    """Yield each status once per ticket with that status."""
    c = status_counts(tickets)
    return list(c.elements())
```

`.elements()` yields each key repeated `count` times, in insertion order. If `c == {"todo": 2, "done": 1}`, then `list(c.elements()) == ["todo", "todo", "done"]`. This is the inverse of the constructor: `Counter(c.elements()) == c` (modulo order and zero-count keys, which `elements()` skips).

**Why does `.elements()` exist?** Because once you have a Counter, the question "now sample from it" comes up constantly — random sampling, weighted choice, rebuilding the underlying list of items. Without `.elements()` you would write `itertools.chain.from_iterable([k]*v for k, v in c.items())`, which is exactly what `elements` does internally.

### Lines 38–52: The `__main__` smoke test

```python
if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    proj = uuid4()
    sample = [
        Ticket(uuid4(), proj, "write docs",   None,    "todo",        2),
        Ticket(uuid4(), proj, "fix login",    uuid4(), "in_progress", 4),
        Ticket(uuid4(), proj, "ship release", uuid4(), "in_progress", 5),
        Ticket(uuid4(), proj, "triage",       None,    "todo",        1),
        Ticket(uuid4(), proj, "done item",    uuid4(), "done",        2),
    ]
    print("counts:", status_counts(sample))
    print("top 2:", top_n_statuses(sample, 2))
    print("elements:", expand_to_repeated_statuses(sample))
```

A `__main__` smoke test that constructs real `Ticket` instances is worth a thousand words of explanation. The column-aligned literals make the status column easy to scan. The expected output is recorded in the Execution Trace below — type the file in and confirm you get the same numbers.

## Execution Trace

```bash
$ uv run python boardly/metrics.py
counts: Counter({'todo': 2, 'in_progress': 2, 'done': 1})
top 2: [('todo', 2), ('in_progress', 2)]
elements: ['todo', 'todo', 'in_progress', 'in_progress', 'done']
```

Note that `Counter`'s `__repr__` shows items in *insertion order* (the order keys were first seen), not descending count order. `todo` was seen first, so it appears first in the repr — even though `todo` and `in_progress` have the same count. `.most_common(n)`, by contrast, returns items sorted by descending count, with ties broken by insertion order; that is why `top 2` starts with `todo` (first inserted among the tied pair). `Counter` does not override `__str__` separately, so `print(c)` produces the same output as `__repr__`.

## Common Mistakes

### Mistake 1: Treating `Counter` as a `set` and expecting missing keys to raise

```python
c = Counter(["todo", "todo", "done"])
blocked = c["blocked"]   # student expects KeyError
```

**Symptom:** `blocked` is `0`, not a `KeyError`. The student expected `Counter` to behave like `dict` (where missing keys raise).

**Why:** `Counter.__missing__` is overridden to return `0`. This is the whole point of the class — counting without the bookkeeping of `defaultdict(int)` — but it is also a sharp edge. If you need to distinguish "absent" from "zero", use `k in c` or `c.get(k, None)`.

**Fix:** Either accept the `0` (most of the time, this is the right answer for a counter) or use `c.get("blocked") is None` if you genuinely need the absence signal.

### Mistake 2: Using `-` to subtract counts and getting surprised by negative keys disappearing

```python
a = Counter(x=5)
b = Counter(x=8)
result = a - b   # student expects Counter({'x': -3})
```

**Symptom:** `result` is `Counter()` — empty. The student expected a negative count.

**Why:** `Counter.__sub__` keeps only positive results; any key whose difference is `0` or negative is dropped. This matches the multiset intuition (you cannot have a negative number of items in a bag) but it breaks the "Counter is just a dict" mental model.

**Fix:** If you need signed differences, drop to plain dict arithmetic:

```python
result = {k: a[k] - b[k] for k in a | b}
```

### Mistake 3: Calling `.most_common()` and slicing the result yourself

```python
c = Counter(...)
top_three = c.most_common()[:3]   # full sort, then slice
```

**Symptom:** The endpoint is slower than the equivalent `c.most_common(3)` on a large Counter.

**Why:** `most_common()` with no argument does a full O(N log N) sort. `most_common(n)` uses `heapq.nlargest` which is O(N log n). For a Counter with a million distinct keys and `n=3`, the difference is roughly 20×.

**Fix:** Always pass `n` when you only need the top few: `c.most_common(3)`.

## Engineering Trade-Offs

**Decision:** Use `Counter` for any "count hashable things, then maybe rank" task.

**Both sides:** The alternative is `defaultdict(int)` (next lesson). `defaultdict(int)` wins when (a) you need to mutate counts in place during the loop and the `Counter.update` shape does not fit, (b) you need negative counts and the auto-drop behaviour of `Counter` subtraction is wrong, or (c) you want the type signature to read `defaultdict[int]` so downstream code does not call `.most_common` on it. `Counter` wins everywhere else — it has `.most_common`, `.elements`, arithmetic, and `.total()` (3.10+) for free.

**Commitment:** `boardly/metrics.py` uses `Counter` for all read-only counting tasks. When a function needs to mutate counts during the loop (for example, "decrement the open-ticket count when a ticket moves to done"), it uses `defaultdict(int)` and the next lesson explains why.

## Exercises

1. **Exercise 1 — Print the full ranking.** Modify the `__main__` block to print the full ranking of statuses by count (not just top 2). `Verify: uv run python -c "from boardly.metrics import status_counts, top_n_statuses; from boardly.models import Ticket; from uuid import uuid4; ts=[Ticket(uuid4(),uuid4(),'t',None,'todo',1),Ticket(uuid4(),uuid4(),'t',None,'todo',1),Ticket(uuid4(),uuid4(),'t',None,'done',1)]; print(status_counts(ts).most_common())"`
2. **Exercise 2 — Add `.total()`.** Use `c.total()` (added in Python 3.10) to print the total number of tickets counted. `Verify: uv run python -c "from collections import Counter; c=Counter(a=2,b=3); print(c.total())"`
3. **Exercise 3 — Subtract two sprints.** Write `def diff(sprint_a, sprint_b)` that uses `-` to return a Counter of "statuses in A but not fully covered by B". `Verify: uv run python -c "from collections import Counter; a=Counter(x=5); b=Counter(x=2); print(a-b)"`
4. **Exercise 4 — Union vs intersection.** Write a small script that constructs two Counters and prints both `a | b` and `a & b` so you can see the max/min behaviour. `Verify: uv run python -c "from collections import Counter; a=Counter(x=2,y=1); b=Counter(x=5,z=3); print(a|b, a&b)"`
5. **Exercise 5 — Add a `top_assignees` function.** Add `def top_assignees(tickets, n=3)` to `boardly/metrics.py` that uses `Counter` over `t.assignee_id`. Decide what to do with `None` assignees — skip them or count them. `Verify: uv run python -c "import boardly.metrics as m; print(hasattr(m,'top_assignees'))"`

## Verification

```bash
$ uv run python boardly/metrics.py
counts: Counter({'todo': 2, 'in_progress': 2, 'done': 1})
top 2: [('todo', 2), ('in_progress', 2)]
elements: ['todo', 'todo', 'in_progress', 'in_progress', 'done']
```

## Previously Learned Here

- [[04-collections/00-collections-MOC]] — the section map, the `boardly` models, the path through the seven lessons.

## What's Next

[[04-collections/02-defaultdict]] — `defaultdict` is `Counter`'s older, more general sibling. Where `Counter`'s default is "zero", `defaultdict`'s default is "whatever `default_factory` returns" — and the most common factory is `list`, which turns "group tickets by assignee" into one line. We will dig into the `__missing__` protocol that both classes share, the `setdefault` it replaces, and the `None`-factory gotcha that has bitten every Python developer once.

## Sources

- **Python `collections.Counter` documentation** — https://docs.python.org/3/library/collections.html#collections.Counter — accessed 2026-10-23 — the canonical reference for `Counter`, `.most_common`, `.elements`, `.total`, and the four arithmetic operators.
- **CPython `Counter` source** — https://github.com/python/cpython/blob/3.12/Lib/collections/__init__.py#L574 — accessed 2026-10-23 — the actual implementation, 240 lines, well worth reading once.

## What We Learned

- You can construct a `Counter` from any iterable of hashable items, including a generator.
- `Counter.__missing__` returns `0`, which is why missing keys do not raise and why `c[k] += 1` "just works".
- `.most_common(n)` uses `heapq.nlargest` for the small-`n` case, giving O(N log n) instead of O(N log N).
- `+` adds counts, `-` subtracts (and drops non-positive), `&` keeps the min, `|` keeps the max — all four return fresh `Counter` objects.
- `.elements()` is the round-trip back to a flat iterable, skipping zero-count keys.
