---
title: "collections: Section Map of Content"
aliases:
 - collections MOC
 - Section 04 MOC
tags:
 - collections
 - moc
status: complete
course_level: intermediate
difficulty: intermediate
---

# Section 04: collections — Map of Content

*The `collections` module — eight small, focused data-structure classes that turn twenty-line boilerplate into one line. FastAPI itself reaches for `deque` for middleware stacks, `defaultdict` for grouped routes, and `Counter` for metrics. This section walks each one with the `boardly` project-management API as the running example.*

**You're at the very beginning of Section 04.**

`collections` is the most under-taught module in the standard library. Engineers reach for it only when Stack Overflow tells them to, then forget what it gave them. By the end of this section you will reach for `Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`, `OrderedDict`, and `UserDict` deliberately — because you will know what each one is, what it costs, and what it replaces.

#collections #moc

## What's in this section

| Lesson | What you learn | Canonical? |
|---|---|---|
| [[04-collections/01-Counter]] | `Counter(iterable)`, `.most_common(n)`, `+`/`-`/`&`/`|` arithmetic, `.elements()`, the `Counter` vs `defaultdict(int)` decision | Yes |
| [[04-collections/02-defaultdict]] | `defaultdict(list)`, the `default_factory`, the `__missing__` protocol, when `defaultdict` beats `setdefault`, the `None`-factory gotcha | Yes |
| [[04-collections/03-deque]] | `deque(iterable, maxlen=N)`, O(1) `appendleft`/`popleft`, `rotate(n)`, `extendleft`, the GIL-free ring buffer, when `deque` beats `list` | Yes |
| [[04-collections/04-namedtuple]] | `namedtuple("X", ["a","b"])`, `_fields`, `_replace`, `_make`, the `typing.NamedTuple` alternative with type hints, the memory win vs a class | No |
| [[04-collections/05-ChainMap]] | `ChainMap(d1, d2)`, read-falls-through, write-goes-to-first, `new_child()`, config-layering | No |
| [[04-collections/06-OrderedDict]] | `OrderedDict`, `move_to_end()`, `popitem(last=True)`, why `OrderedDict` still exists when `dict` is ordered since 3.7 | Yes |
| [[04-collections/07-UserDict-UserList-UserString]] | `UserDict`/`UserList`/`UserString`, the `data` attribute, why you subclass these instead of `dict`/`list` (the `__setitem__` override trap) | No |

## How to read this section

Read [[04-collections/01-Counter]] first — it is the canonical lesson and the lightest of the eight. Then read in numbered order. The three canonical lessons (`Counter`, `defaultdict`, `deque`) are the spine — every other lesson assumes you have read them. By [[04-collections/07-UserDict-UserList-UserString]] you will see the `data` attribute trick that explains why `defaultdict` and `OrderedDict` are implemented the way they are.

If you only have time for three: read `Counter`, `defaultdict`, and `deque`. Those three cover 80% of the production use of `collections`.

## The running example: `boardly`

`boardly` is a small project-management API. It has three core models:

```python
# boardly/models.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

@dataclass
class User:
    id: UUID
    name: str
    email: str

@dataclass
class Project:
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

@dataclass
class Ticket:
    id: UUID
    project_id: UUID
    title: str
    assignee_id: UUID | None
    status: str   # "open" | "in_progress" | "blocked" | "done"
    priority: int # 1 (low) .. 5 (urgent)
```

Every lesson in this section builds on this same shape — counting tickets by status, grouping them by assignee, ring-buffering the last N audit events, layering config from env + file + defaults, and so on. By the end you will have a mental model where `collections` is the answer to a class of small, repeated problems.

## Section learning objectives

By the end of Section 04 you will be able to:

1. **Pick the right `collections` class** in under ten seconds — given a problem statement, name the class (or "neither") and justify it.
2. **Read `collections` source code** — the implementations are short (under 600 lines combined) and now legible to you.
3. **Avoid the four canonical `collections` bugs** — the `None`-factory gotcha, the `deque` index-is-O(n) trap, the `UserDict`-vs-`dict` subclassing trap, and the `OrderedDict`-equality semantics surprise.
4. **See where FastAPI itself uses these classes** — `deque` in the middleware stack, `defaultdict(list)` in route grouping, `ChainMap`-shaped config.

## What's next

Open [[04-collections/01-Counter]] — the lightest of the eight, and the canonical lesson for "count hashable things, then ask for the top N."

## Sources

- **Python `collections` module documentation** — https://docs.python.org/3/library/collections.html — accessed 2026-10-23 — the canonical reference for every class in this section.

## What we learned in this section

- You opened the MOC. **That is the first step.**
