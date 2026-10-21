---
title: "Lesson 02: Sequence, Mapping, Set mixins"
aliases:
 - collections.abc mixins
 - Sequence ABC
 - Mapping ABC
tags:
 - collections-abc
 - sequence
 - mapping
 - set
 - mixins
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[05-collections-abc/01-The-ABC-Hierarchy]]"
related_lessons:
 - "[[04-collections/07-UserDict-UserList-UserString]]"
 - "[[05-collections-abc/03-Hashable-and-Frozen]]"
---

# Lesson 02: Sequence, Mapping, Set mixins

*The mixin methods each ABC provides. Inherit from `Sequence`, implement `__getitem__` and `__len__`, and you get `__contains__`, `__iter__`, `__reversed__`, `index`, and `count` for free. Inherit from `Mapping`, implement `__getitem__`, `__iter__`, `__len__`, and you get `keys`, `values`, `items`, `get`, `__eq__`, `__ne__` for free. The mixins are why ABCs are worth importing.*

**You're at the very beginning of Section 05 — Lesson 02.**

The hierarchy from Lesson 01 is the map; this lesson is the engine. ABCs are not just `isinstance` markers — they are *mixin providers*. Inherit from the right ABC and you get five to ten methods for free. This lesson walks a custom `Sequence` subclass from zero to full conformance, then shows the equivalent for `Mapping` and `Set`.

Take your time. Type every example. **This is how you learn.**

#collections-abc #sequence #mapping #set #mixins

## Learning Objectives

By the end of this lesson you will be able to:

1. **List the abstract methods** each of `Sequence`, `Mapping`, `Set` requires you to implement.
2. **List the mixin methods** each provides in return.
3. **Build a custom `Sequence`** in 30 lines that inherits `__contains__`, `__iter__`, `__reversed__`, `index`, `count` from the ABC.
4. **Explain the difference between `Sequence` and `MutableSequence`** — which abstract methods each adds.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/01-The-ABC-Hierarchy]]** — the hierarchy map this lesson's engine lives in.
- **About 30 minutes of focused time.**

**The most common gap: forgetting the mixin methods exist.**

Students inherit from `Sequence`, implement `__getitem__` and `__len__`, then write `__contains__` by hand — duplicating the ABC's mixin. Or they reach for `itertools` for `__iter__` not realising the ABC already provides it. Read this lesson with "what do I get for free?" front of mind.

## The Problem

Here is the bug. `boardly` wants a `TicketList` — a read-only view over a list of tickets that supports indexing, length, iteration, `in`-checks, `index()`, and `count()`. The first implementation everyone writes:

```python
class TicketList:
    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __getitem__(self, i: int) -> Ticket:
        return self._tickets[i]

    def __len__(self) -> int:
        return len(self._tickets)

    def __contains__(self, t: object) -> bool:
        return t in self._tickets

    def __iter__(self):
        return iter(self._tickets)

    def __reversed__(self):
        return reversed(self._tickets)

    def index(self, t: object) -> int:
        return self._tickets.index(t)

    def count(self, t: object) -> int:
        return self._tickets.count(t)
```

That is *seven* hand-written methods to get a "list-like" view. Each is correct; each is boilerplate. Multiply by every wrapper class in the codebase — `ProjectList`, `AuditListView`, `UserListView` — and you have hundreds of lines of identical boilerplate.

Inherit from `Sequence` and four of those seven become mixins. The implementation drops to:

```python
from collections.abc import Sequence

class TicketList(Sequence):
    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __getitem__(self, i):
        return self._tickets[i]

    def __len__(self):
        return len(self._tickets)
```

Three methods. The other four come from `Sequence`'s mixins.

## The Code

```python
# boardly/sequence_views.py
"""Custom Sequence, Mapping, and Set subclasses to demo ABC mixins."""
from collections.abc import Sequence, Mapping, Set
from typing import Iterator
from boardly.models import Ticket


class TicketList(Sequence):
    """A read-only sequence view over a list of tickets.

    Sequence requires __getitem__ and __len__. It provides __contains__,
    __iter__, __reversed__, index, and count as mixins.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __getitem__(self, index):
        return self._tickets[index]

    def __len__(self):
        return len(self._tickets)

    def __repr__(self):
        return f"TicketList({self._tickets!r})"


class FrozenConfig(Mapping):
    """A read-only mapping view over a config dict.

    Mapping requires __getitem__, __iter__, __len__. It provides __contains__,
    keys, values, items, get, __eq__, __ne__ as mixins.
    """

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class RoleSet(Set):
    """A read-only set view over a list of role strings.

    Set requires __contains__ and __iter__ and __len__. It provides the set
    operators __le__, __lt__, __gt__, __ge__, __and__, __or__, __sub__, __xor__,
    and isdisjoint as mixins.
    """

    def __init__(self, roles: list[str]) -> None:
        # Materialise into a real set for O(1) lookup; the view is read-only.
        self._roles = set(roles)

    def __contains__(self, role: object) -> bool:
        return role in self._roles

    def __iter__(self) -> Iterator[str]:
        return iter(self._roles)

    def __len__(self) -> int:
        return len(self._roles)


if __name__ == "__main__":
    from uuid import uuid4

    print("--- TicketList: Sequence mixins ---")
    ts = TicketList([
        Ticket(uuid4(), uuid4(), "t1", None, "open", 1),
        Ticket(uuid4(), uuid4(), "t2", None, "open", 2),
        Ticket(uuid4(), uuid4(), "t3", None, "done", 3),
    ])

    print(f"len: {len(ts)}")
    print(f"ts[0].title: {ts[0].title}")
    print(f"ts[-1].title: {ts[-1].title}")   # negative index works
    t0 = ts[0]
    print(f"t0 in ts: {t0 in ts}")             # __contains__ mixin
    print(f"[t.title for t in ts]: {[t.title for t in ts]}")   # __iter__ mixin
    print(f"[t.title for t in reversed(ts)]: {[t.title for t in reversed(ts)]}")  # __reversed__ mixin
    print(f"ts.index(t0): {ts.index(t0)}")     # index mixin
    print(f"ts.count(t0): {ts.count(t0)}")     # count mixin

    print("\n--- FrozenConfig: Mapping mixins ---")
    cfg = FrozenConfig({"db_url": "x", "log_level": "INFO", "max_tickets": 1000})
    print(f"len: {len(cfg)}")
    print(f"cfg['db_url']: {cfg['db_url']}")
    print(f"'db_url' in cfg: {'db_url' in cfg}")            # __contains__ mixin
    print(f"keys: {list(cfg.keys())}")                     # keys mixin
    print(f"values: {list(cfg.values())}")                 # values mixin
    print(f"items: {list(cfg.items())}")                   # items mixin
    print(f"cfg.get('missing', 'default'): {cfg.get('missing', 'default')}")  # get mixin
    print(f"cfg == FrozenConfig(cfg._data): {cfg == FrozenConfig(cfg._data)}")  # __eq__ mixin

    print("\n--- RoleSet: Set mixins ---")
    rs = RoleSet(["admin", "editor", "viewer"])
    rs2 = RoleSet(["admin", "viewer"])
    print(f"'admin' in rs: {'admin' in rs}")
    print(f"rs <= rs2: {rs <= rs2}")           # subset
    print(f"rs2 <= rs: {rs2 <= rs}")
    print(f"rs - rs2: {set(rs - rs2)}")        # set difference
    print(f"rs & rs2: {set(rs & rs2)}")        # intersection
    print(f"rs | RoleSet(['x']): {set(rs | RoleSet(['x']))}")  # union
    print(f"rs ^ rs2: {set(rs ^ rs2)}")        # symmetric difference
    print(f"rs.isdisjoint(RoleSet(['z'])): {rs.isdisjoint(RoleSet(['z']))}")
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports

```python
# boardly/sequence_views.py
"""Custom Sequence, Mapping, and Set subclasses to demo ABC mixins."""
from collections.abc import Sequence, Mapping, Set
from typing import Iterator
from boardly.models import Ticket
```

`from collections.abc import Sequence, Mapping, Set` — these are the three immutable-tier ABCs we will subclass. The mutable counterparts (`MutableSequence`, `MutableMapping`, `MutableSet`) are the topic of a later lesson and add their own abstract methods.

### Lines 9–26: `TicketList` — the `Sequence` subclass

```python
class TicketList(Sequence):
    """A read-only sequence view over a list of tickets.

    Sequence requires __getitem__ and __len__. It provides __contains__,
    __iter__, __reversed__, index, and count as mixins.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __getitem__(self, index):
        return self._tickets[index]

    def __len__(self):
        return len(self._tickets)

    def __repr__(self):
        return f"TicketList({self._tickets!r})"
```

`class TicketList(Sequence):` — inherit from `Sequence`. The ABC's metaclass (`ABCMeta`) will refuse instantiation if any of the abstract methods (`__getitem__`, `__len__`) are not implemented on the subclass. That is the *contract* part of an ABC: abstract methods must be defined on the concrete subclass or `TypeError` at instantiation time.

`__getitem__(self, index)` — the abstract method. Note that `index` can be a plain `int` *or* a slice — the mixin methods (`__contains__`, `__iter__`, `__reversed__`) work by calling `__getitem__` with integer indices. The mixin implementation of `__iter__` is roughly:

```python
def __iter__(self):
    i = 0
    while i < len(self):
        yield self[i]
        i += 1
```

— which calls `__getitem__` with `i` (an int). Your `__getitem__` does not have to support slices for the mixins to work — but it should, because external callers will pass slices.

`__len__` — the other abstract method. Used by the `__contains__` mixin (which scans `0..len-1` calling `__getitem__`) and by `reversed()`'s default protocol.

**What does `Sequence` provide as mixins?**

| Method | How the mixin implements it |
|---|---|
| `__contains__` | Calls `__getitem__(0..len-1)` until match or `IndexError`. |
| `__iter__` | `for i in range(len(self)): yield self[i]`. |
| `__reversed__` | Same as `__iter__` but backwards from `len-1`. |
| `index(value, start=0, stop=len)` | Linear scan; raises `ValueError` if not found. |
| `count(value)` | Linear scan; counts occurrences. |

Five mixins for the price of two abstract methods. That is the value of `collections.abc`.

### Lines 30–48: `FrozenConfig` — the `Mapping` subclass

```python
class FrozenConfig(Mapping):
    """A read-only mapping view over a config dict.

    Mapping requires __getitem__, __iter__, __len__. It provides __contains__,
    keys, values, items, get, __eq__, __ne__ as mixins.
    """

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)
```

`class FrozenConfig(Mapping):` — inherit from `Mapping`. Three abstract methods: `__getitem__`, `__iter__`, `__len__`. Implement those three and you get:

| Method | How the mixin implements it |
|---|---|
| `__contains__` | `try: self[key]; except KeyError: return False; return True` — uses `__getitem__`, not `__iter__`. |
| `keys()` | Returns a `KeysView(self)`. |
| `values()` | Returns a `ValuesView(self)`. |
| `items()` | Returns an `ItemsView(self)`. |
| `get(key, default=None)` | `try: return self[key]; except KeyError: return default`. |
| `__eq__` | Iterates keys; checks length and per-key equality via `__getitem__`. |
| `__ne__` | `not self == other`. |

Seven mixins for the price of three abstract methods.

**Why does `Mapping` require `__iter__` but not `__contains__`?** Because `__contains__` can be derived from `__getitem__` (try/except `KeyError`), and that derivation is *faster* than iterating every key. The ABC picks the *minimum* set of abstract methods such that all other operations can be derived as mixins. `__getitem__` is a better foundation than `__iter__` for `__contains__` because the hash table already gives O(1) lookup — walking every key to check membership would throw away that speed.

### Lines 52–69: `RoleSet` — the `Set` subclass

```python
class RoleSet(Set):
    """A read-only set view over a list of role strings.

    Set requires __contains__ and __iter__ and __len__. It provides the set
    operators __le__, __lt__, __gt__, __ge__, __and__, __or__, __sub__, __xor__,
    and isdisjoint as mixins.
    """

    def __init__(self, roles: list[str]) -> None:
        # Materialise into a real set for O(1) lookup; the view is read-only.
        self._roles = set(roles)

    def __contains__(self, role: object) -> bool:
        return role in self._roles

    def __iter__(self) -> Iterator[str]:
        return iter(self._roles)

    def __len__(self) -> int:
        return len(self._roles)
```

`class RoleSet(Set):` — inherit from `Set`. Three abstract methods: `__contains__`, `__iter__`, `__len__`. Implement those and you get:

| Method | How the mixin implements it |
|---|---|
| `__le__` (subset) | `all(e in other for e in self)`. |
| `__lt__` (proper subset) | `self <= other and self != other`. |
| `__gt__`, `__ge__` | Symmetric. |
| `__and__` (intersection) | `for e in self if e in other`. |
| `__or__` (union) | Iterates both; yields each once. |
| `__sub__` (difference) | `for e in self if e not in other`. |
| `__xor__` (symmetric difference) | `(self - other) | (other - self)`. |
| `isdisjoint(other)` | `all(e not in other for e in self)`. |

Eight mixins for the price of three abstract methods.

### Lines 73–91: `TicketList` in action

```python
if __name__ == "__main__":
    from uuid import uuid4

    print("--- TicketList: Sequence mixins ---")
    ts = TicketList([
        Ticket(uuid4(), uuid4(), "t1", None, "open", 1),
        Ticket(uuid4(), uuid4(), "t2", None, "open", 2),
        Ticket(uuid4(), uuid4(), "t3", None, "done", 3),
    ])

    print(f"len: {len(ts)}")
    print(f"ts[0].title: {ts[0].title}")
    print(f"ts[-1].title: {ts[-1].title}")   # negative index works
    t0 = ts[0]
    print(f"t0 in ts: {t0 in ts}")             # __contains__ mixin
    print(f"[t.title for t in ts]: {[t.title for t in ts]}")   # __iter__ mixin
    print(f"[t.title for t in reversed(ts)]: {[t.title for t in reversed(ts)]}")  # __reversed__ mixin
    print(f"ts.index(t0): {ts.index(t0)}")     # index mixin
    print(f"ts.count(t0): {ts.count(t0)}")     # count mixin
```

Each line is a mixin demo. `t0 in ts` calls `Sequence.__contains__(t0)`, which iterates `__getitem__(0), __getitem__(1), ...` until it finds `t0` or hits `IndexError`. `reversed(ts)` calls `Sequence.__reversed__`, which iterates from `len-1` to `0`.

### Lines 93–106: `FrozenConfig` in action

```python
    print("\n--- FrozenConfig: Mapping mixins ---")
    cfg = FrozenConfig({"db_url": "x", "log_level": "INFO", "max_tickets": 1000})
    print(f"len: {len(cfg)}")
    print(f"cfg['db_url']: {cfg['db_url']}")
    print(f"'db_url' in cfg: {'db_url' in cfg}")            # __contains__ mixin
    print(f"keys: {list(cfg.keys())}")                     # keys mixin
    print(f"values: {list(cfg.values())}")                 # values mixin
    print(f"items: {list(cfg.items())}")                   # items mixin
    print(f"cfg.get('missing', 'default'): {cfg.get('missing', 'default')}")  # get mixin
    print(f"cfg == FrozenConfig(cfg._data): {cfg == FrozenConfig(cfg._data)}")  # __eq__ mixin
```

`cfg.keys()` returns a `KeysView` — the same `KeysView` ABC from Lesson 01. It is a *live* view: if you mutate `cfg._data` (which `FrozenConfig` does not allow, but `MutableMapping` subclasses do), `cfg.keys()` reflects the change.

### Lines 108–117: `RoleSet` in action

```python
    print("\n--- RoleSet: Set mixins ---")
    rs = RoleSet(["admin", "editor", "viewer"])
    rs2 = RoleSet(["admin", "viewer"])
    print(f"'admin' in rs: {'admin' in rs}")
    print(f"rs <= rs2: {rs <= rs2}")           # subset
    print(f"rs2 <= rs: {rs2 <= rs}")
    print(f"rs - rs2: {set(rs - rs2)}")        # set difference
    print(f"rs & rs2: {set(rs & rs2)}")        # intersection
    print(f"rs | RoleSet(['x']): {set(rs | RoleSet(['x']))}")  # union
    print(f"rs ^ rs2: {set(rs ^ rs2)}")        # symmetric difference
    print(f"rs.isdisjoint(RoleSet(['z'])): {rs.isdisjoint(RoleSet(['z']))}")
```

`rs - rs2` calls `Set.__sub__(rs2)`, which iterates `rs` and yields elements not in `rs2`. The result is a fresh `RoleSet`-shaped object — actually, the mixin returns a `set`-shaped object because `Set._from_iterable` defaults to constructing `set(...)`. To return your own subclass, override `_from_iterable`.

## Execution Trace

```bash
$ uv run python boardly/sequence_views.py
--- TicketList: Sequence mixins ---
len: 3
ts[0].title: t1
ts[-1].title: t3
t0 in ts: True
[t.title for t in ts]: ['t1', 't2', 't3']
[t.title for t in reversed(ts)]: ['t3', 't2', 't1']
ts.index(t0): 0
ts.count(t0): 1

--- FrozenConfig: Mapping mixins ---
len: 3
cfg['db_url']: x
'db_url' in cfg: True
keys: ['db_url', 'log_level', 'max_tickets']
values: ['x', 'INFO', 1000]
items: [('db_url', 'x'), ('log_level', 'INFO'), ('max_tickets', 1000)]
cfg.get('missing', 'default'): default
cfg == FrozenConfig(cfg._data): True

--- RoleSet: Set mixins ---
'admin' in rs: True
rs <= rs2: False
rs2 <= rs: True
rs - rs2: {'editor'}
rs & rs2: {'admin', 'viewer'}
rs | RoleSet(['x']): {'editor', 'admin', 'viewer', 'x'}
rs ^ rs2: {'editor'}
rs.isdisjoint(RoleSet(['z'])): True
```

(The order of items inside `set` reprs is `hash()`-dependent — `PYTHONHASHSEED` randomises it across runs — so your `rs & rs2` line may show `{'viewer', 'admin'}` instead. The contents are what matters; the set holds the same elements regardless of repr order.)

## Common Mistakes

### Mistake 1: Forgetting to implement an abstract method

```python
class MySeq(Sequence):
    def __getitem__(self, i): return ...
    # forgot __len__
```

**Symptom:** `TypeError: Can't instantiate abstract class MySeq with abstract method __len__` at construction time.

**Why:** `ABCMeta.__new__` walks the class's `__abstractmethods__` set; if it is non-empty, the class is "abstract" and cannot be instantiated. The set is computed from the abstract methods declared via `@abstractmethod` on the base classes (including `Sequence`, which has `__getitem__` and `__len__` decorated).

**Fix:** Implement every abstract method on the subclass. The docs list them per ABC.

### Mistake 2: Overriding a mixin with a slower hand-rolled version

```python
class MySeq(Sequence):
    def __getitem__(self, i): return self._items[i]
    def __len__(self): return len(self._items)
    def __contains__(self, x):           # override
        for item in self._items:
            if item == x: return True
        return False
```

**Symptom:** The code works, but the hand-rolled `__contains__` is the same as the mixin — pure duplication.

**Why:** The `Sequence.__contains__` mixin does exactly this scan. Overriding it adds no behaviour; it adds a maintenance burden.

**Fix:** Delete the override. Use the mixin. If you have a faster algorithm (e.g., binary search on a sorted sequence), *then* override — and document why.

### Mistake 3: Calling `__contains__` on a `Sequence` with no `__len__`

```python
class Bad(Sequence):
    def __getitem__(self, i): return [1, 2, 3][i]
    # forgot __len__ — but Python still constructs? No: TypeError at __init__
```

**Symptom:** `TypeError: Can't instantiate abstract class Bad with abstract method __len__`.

**Why:** Both `__getitem__` and `__len__` are abstract on `Sequence`. Missing either blocks construction.

**Fix:** Implement both. If you really have a "sequence without length" (rare — `range` always has `len`), inherit from `Collection` (which requires `__len__`, `__iter__`, `__contains__`) and implement those three instead.

## Engineering Trade-Offs

**Decision:** Inherit from `Sequence` / `Mapping` / `Set` for read-only custom collections; inherit from the `Mutable*` counterparts only when you need write semantics.

**Both sides:**

Inherit from the immutable ABC when:

1. You want a read-only view (the wrapper class refuses `__setitem__`).
2. The mutable mixins (`MutableSequence.__setitem__`, `__delitem__`, `insert`, `append`, `extend`, `pop`, `remove`, `__iadd__`) are not part of your class's contract.
3. You want `isinstance(x, Sequence)` to return `True` for type-guard code.

Inherit from the `Mutable*` ABC when:

1. Your class is genuinely mutable and you want the write-side mixins.
2. You want `isinstance(x, MutableSequence)` to return `True` (which implies `Sequence` too — `MutableSequence` extends `Sequence`).

**Commitment:** `boardly/sequence_views.py` uses the immutable-tier ABCs (`Sequence`, `Mapping`, `Set`) for read-only views. For mutable wrappers, `boardly` uses `UserDict` / `UserList` (Section 04 Lesson 07) because the `Mutable*` ABCs do not provide a default storage attribute; you would have to write `__setitem__`, `__delitem__`, `insert`, `append`, `extend`, `pop`, `remove` yourself. `UserDict` / `UserList` give you a `data` attribute and route everything for free.

## Exercises

1. **Exercise 1 — Verify the abstract-method contract.** Try `Sequence()` directly and confirm `TypeError`. `Verify: uv run python -c "from collections.abc import Sequence\ntry:\n  Sequence()\nexcept TypeError as e:\n  print('TypeError:', e)"`
2. **Exercise 2 — A custom `Sequence` with `__contains__` overridden.** Override `__contains__` on a `Sequence` subclass to use `set` membership for O(1) check. Confirm the override fires. `Verify: uv run python -c "from collections.abc import Sequence\nclass S(Sequence):\n  def __init__(self, items): self._items=set(items); self._list=list(items)\n  def __getitem__(self, i): return self._list[i]\n  def __len__(self): return len(self._list)\n  def __contains__(self, x): return x in self._items\ns=S([1,2,3]); print(2 in s, 5 in s)"`
3. **Exercise 3 — A `Mapping` with custom `get`.** Override `get` on a `Mapping` subclass to log accesses. `Verify: uv run python -c "from collections.abc import Mapping\nclass M(Mapping):\n  def __init__(self, d): self._d=d\n  def __getitem__(self, k): return self._d[k]\n  def __iter__(self): return iter(self._d)\n  def __len__(self): return len(self._d)\n  def get(self, k, default=None):\n    print(f'get({k})'); return self._d.get(k, default)\nm=M({'a':1}); m.get('a'); m.get('z', 0)"`
4. **Exercise 4 — A `Set` with custom `_from_iterable`.** Override `_from_iterable` to return your subclass instead of plain `set`. `Verify: uv run python -c "from collections.abc import Set\nclass S(Set):\n  def __init__(self, items=()): self._s=set(items)\n  def __contains__(self, x): return x in self._s\n  def __iter__(self): return iter(self._s)\n  def __len__(self): return len(self._s)\n  @classmethod\n  def _from_iterable(cls, it):\n    return cls(it)\ns=S([1,2]); r=S([2,3]); print(type(s & r).__name__)"`
5. **Exercise 5 — A `MutableMapping` that auto-saves.** Subclass `MutableMapping`, implement the five abstract methods, and override `__setitem__` to call a `save()` callback. `Verify: uv run python -c "from collections.abc import MutableMapping\nclass M(MutableMapping):\n  def __init__(self, d, save): self._d=dict(d); self._save=save\n  def __getitem__(self, k): return self._d[k]\n  def __setitem__(self, k, v): self._d[k]=v; self._save()\n  def __delitem__(self, k): del self._d[k]; self._save()\n  def __iter__(self): return iter(self._d)\n  def __len__(self): return len(self._d)\ncalls=[0]\ndef save(): calls[0]+=1\nm=M({}, save); m['x']=1; print('save calls:', calls[0])"`

## Verification

```bash
$ uv run python boardly/sequence_views.py
--- TicketList: Sequence mixins ---
len: 3
ts[0].title: t1
ts[-1].title: t3
t0 in ts: True
[t.title for t in ts]: ['t1', 't2', 't3']
[t.title for t in reversed(ts)]: ['t3', 't2', 't1']
ts.index(t0): 0
ts.count(t0): 1

--- FrozenConfig: Mapping mixins ---
len: 3
cfg['db_url']: x
'db_url' in cfg: True
keys: ['db_url', 'log_level', 'max_tickets']
values: ['x', 'INFO', 1000]
items: [('db_url', 'x'), ('log_level', 'INFO'), ('max_tickets', 1000)]
cfg.get('missing', 'default'): default
cfg == FrozenConfig(cfg._data): True

--- RoleSet: Set mixins ---
'admin' in rs: True
rs <= rs2: False
rs2 <= rs: True
rs - rs2: {'editor'}
rs & rs2: {'admin', 'viewer'}
rs | RoleSet(['x']): {'admin', 'editor', 'viewer', 'x'}
rs ^ rs2: {'editor'}
rs.isdisjoint(RoleSet(['z'])): True
```

## Previously Learned Here

- [[05-collections-abc/01-The-ABC-Hierarchy]] — the tree this lesson's mixins live in.
- [[04-collections/07-UserDict-UserList-UserString]] — `UserDict` / `UserList` provide an alternative path to mutable custom containers, with a `.data` attribute.

## What's Next

[[05-collections-abc/03-Hashable-and-Frozen]] — the `Hashable` ABC and the immutability contract. A hashable object must be immutable (or behave immutable for as long as it lives in a dict key). We will see why mutable objects are unhashable, what `__hash__` actually does, and why `@dataclass(frozen=True)` flips a mutable class into a hashable one.

## Sources

- **Python `collections.abc` mixin methods table** — https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes — accessed 2026-10-23 — the table that lists, for each ABC, the abstract methods and the mixin methods.
- **PEP 3119 — Abstract Base Class mixins** — https://peps.python.org/pep-3119/#abstract-base-classes-and-mixins — accessed 2026-10-23 — the design rationale for the mixin-method pattern.
- **CPython `_collections_abc.py` source** — https://github.com/python/cpython/blob/3.12/Lib/_collections_abc.py — accessed 2026-10-23 — the actual mixin implementations, all in Python; reading them is the fastest way to understand the pattern.

## What We Learned

- `Sequence` requires `__getitem__` and `__len__`; provides `__contains__`, `__iter__`, `__reversed__`, `index`, `count` as mixins.
- `Mapping` requires `__getitem__`, `__iter__`, `__len__`; provides `__contains__`, `keys`, `values`, `items`, `get`, `__eq__`, `__ne__` as mixins.
- `Set` requires `__contains__`, `__iter__`, `__len__`; provides the set operators (`__le__`, `__lt__`, `__and__`, `__or__`, `__sub__`, `__xor__`, `isdisjoint`) as mixins.
- `MutableSequence` / `MutableMapping` / `MutableSet` add the write-side abstract methods (`__setitem__`, `__delitem__`, `insert`, `append`, `extend`, `pop`, `remove`).
- `ABCMeta` blocks instantiation of a subclass that has not implemented all abstract methods; `TypeError` at construction time.
- Override a mixin only when you have a *faster* algorithm than the default — never for behaviour parity.
