---
title: "Lesson 06: OrderedDict"
aliases:
 - collections.OrderedDict
 - OrderedDict
 - move_to_end
tags:
 - collections
 - ordereddict
 - lru
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[04-collections/05-ChainMap]]"
related_lessons:
 - "[[02-functools/01-lru_cache-and-Caching]]"
 - "[[04-collections/03-deque]]"
first_taught_in: "04-collections/06-OrderedDict"
---

# Lesson 06: OrderedDict

*`collections.OrderedDict` — the dict subclass that *still ships* even though `dict` has been insertion-ordered since Python 3.7. It earns its keep with `move_to_end(key)` and `popitem(last=True)`, with order-sensitive equality, and as the backbone of `functools.lru_cache`'s eviction loop.*

**You're at the very beginning of Section 04 — Lesson 06.**

A question every senior engineer gets asked once: "If `dict` is ordered now, why does `OrderedDict` exist?" The answer is three things: `move_to_end`, `popitem(last=...)`, and equality semantics. By the end of this lesson you will be the person who can answer that question in a code review without checking the docs.

Take your time. Type every example. **This is how you learn.**

#collections #ordereddict #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct an `OrderedDict`** and predict its iteration order without running the code.
2. **Use `move_to_end(key, last=True)` and `popitem(last=True)`** — the two API calls `dict` does not have.
3. **Explain why `OrderedDict` still exists** despite `dict` being ordered since 3.7.
4. **Implement a tiny LRU cache** on top of `OrderedDict`, mirroring how `functools.lru_cache` works internally.

## Prerequisites

Before starting, you need:

- **[[04-collections/05-ChainMap]]** — comfort with the `collections` mapping family.
- **About 25 minutes of focused time.**

**The most common gap: not knowing `dict` was *unordered* before 3.7.**

If you started writing Python in 3.7 or later, you have never seen a `dict` whose iteration order was *not* the insertion order. Before 3.7, `dict` iterated in an implementation-defined order that depended on hash values and insertion history; `OrderedDict` was the only way to get a predictable iteration order. That historical context is the only way the question "why does this still exist?" makes sense — so read the Note below.

## The Problem

Here is the bug. `boardly` wants a small in-memory LRU (Least-Recently-Used) cache of resolved user permissions, keyed by user ID. The cache holds 1,000 entries; on the 1,001st, the oldest-touched entry is evicted.

```python
cache: dict[UUID, Permissions] = {}

def get_or_resolve(user_id: UUID) -> Permissions:
    if user_id in cache:
        # move to "most recently used" — requires re-insertion
        value = cache.pop(user_id)
        cache[user_id] = value
        return value
    value = resolve_from_db(user_id)
    cache[user_id] = value
    if len(cache) > 1000:
        # evict the oldest entry — but which one is "oldest"?
        oldest = next(iter(cache))   # the first-inserted (because dict is ordered)
        del cache[oldest]
    return value
```

This is correct *because* `dict` is ordered since 3.7. But it has two bugs the second a junior engineer inherits it:

1. `next(iter(cache))` is the *first-inserted*, not the *least-recently-used*. The pop-and-re-insert pattern moves an entry to the end (most-recently-used), so the first key is indeed the LRU candidate — but only if every read path does the pop-and-re-insert dance. The pattern is fragile.
2. There is no API to move an existing key to the end without pop-and-reinsert. Every "touch" is two dict operations.

`OrderedDict.move_to_end(key)` is one operation, in-place, that does the move without pop-and-reinsert. `OrderedDict.popitem(last=False)` is one operation that pops the oldest entry. Both are atomic from the caller's perspective.

## The Code

```python
# boardly/lru.py
"""Tiny LRU cache on top of collections.OrderedDict."""
from collections import OrderedDict
from typing import Callable, Generic, TypeVar
from uuid import UUID

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """A fixed-capacity LRU cache built on OrderedDict.

    OrderedDict's move_to_end(last=True) and popitem(last=False) are the
    only two operations an LRU needs. Both are O(1).
    """

    def __init__(self, capacity: int, loader: Callable[[K], V]) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._loader = loader
        # OrderedDict preserves insertion order; we maintain "MRU at the end".
        self._store: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V:
        if key in self._store:
            # Cache hit — move to the MRU end (one operation, in place).
            self._store.move_to_end(key, last=True)
            return self._store[key]
        # Cache miss — load, store, evict if over capacity.
        value = self._loader(key)
        self._store[key] = value
        if len(self._store) > self._capacity:
            # Pop the LRU entry (the first-inserted / least-recently-moved).
            self._store.popitem(last=False)
        return value

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store


if __name__ == "__main__":
    def load_user(uid: UUID) -> str:
        return f"perms_for_{uid}"

    cache: LRUCache[UUID, str] = LRUCache(capacity=3, loader=load_user)
    u1, u2, u3, u4 = UUID("00000000-0000-0000-0000-000000000001"), \
                     UUID("00000000-0000-0000-0000-000000000002"), \
                     UUID("00000000-0000-0000-0000-000000000003"), \
                     UUID("00000000-0000-0000-0000-000000000004")

    cache.get(u1); cache.get(u2); cache.get(u3)
    print(f"after 3 gets: len={len(cache)}")
    cache.get(u1)  # touch u1 -> it should now be MRU; u2 is LRU
    cache.get(u4)  # miss; u2 should be evicted
    print(f"after touch + new miss: len={len(cache)}")
    print(f"u1 in cache: {u1 in cache}")
    print(f"u2 in cache: {u2 in cache}")  # should be False — evicted

    print("\n--- order-sensitive equality demo ---")
    a = OrderedDict([("x", 1), ("y", 2)])
    b = OrderedDict([("y", 2), ("x", 1)])
    c = {"x": 1, "y": 2}
    d = {"y": 2, "x": 1}
    print(f"a == b (OrderedDict, different order): {a == b}")  # False
    print(f"c == d (dict, different order): {c == d}")          # True
    print(f"a == c (OrderedDict vs dict, same order): {a == c}")  # True
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports

```python
# boardly/lru.py
"""Tiny LRU cache on top of collections.OrderedDict."""
from collections import OrderedDict
from typing import Callable, Generic, TypeVar
from uuid import UUID
```

`from collections import OrderedDict` — note the capitalisation. `OrderedDict` is one of several *capitalised* classes in `collections` (alongside `Counter`, `ChainMap`, `UserDict`, `UserList`, `UserString`). The lowercase trio (`defaultdict`, `deque`, `namedtuple`) are either factory functions or drop-in replacements for builtins; the capitalised ones are regular classes that carry their own identity and exist as named types in the module.

### Lines 16–24: Construction

```python
class LRUCache(Generic[K, V]):
    """A fixed-capacity LRU cache built on OrderedDict.

    OrderedDict's move_to_end(last=True) and popitem(last=False) are the
    only two operations an LRU needs. Both are O(1).
    """

    def __init__(self, capacity: int, loader: Callable[[K], V]) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._loader = loader
        # OrderedDict preserves insertion order; we maintain "MRU at the end".
        self._store: OrderedDict[K, V] = OrderedDict()
```

`self._store = OrderedDict()` constructs an empty ordered dict. The constructor accepts an iterable of pairs or a mapping: `OrderedDict([("x", 1), ("y", 2)])` and `OrderedDict({"x": 1, "y": 2})` both work. The iteration order is the construction order.

`OrderedDict` is a subclass of `dict`. Every `dict` method works on it. The additions over `dict` are exactly two: `move_to_end(key, last=True)` and `popitem(last=True)`. Those two methods are why `OrderedDict` exists.

### Lines 31–37: Cache hit — `move_to_end`

```python
    def get(self, key: K) -> V:
        if key in self._store:
            # Cache hit — move to the MRU end (one operation, in place).
            self._store.move_to_end(key, last=True)
            return self._store[key]
```

`self._store.move_to_end(key, last=True)` moves `key` from its current position to the *rightmost* (last) end of the iteration order. `last=False` would move it to the *leftmost* (first) end. The operation is O(1) — it relinks two pointers in the underlying doubly-linked list of keys.

**Why is this O(1) on a dict subclass?** Because `OrderedDict`'s underlying storage is *not just a hash table* — it is a hash table *plus* a doubly-linked list of `(key, value)` nodes. The hash table maps `key -> node`; the linked list maintains the order. `move_to_end` does hash-lookup the node, unlink it from its current position, and relink at the chosen end — three pointer ops, all O(1).

A plain `dict` does *not* have this linked list. The only way to "move to the end" is `del d[k]; d[k] = v`, which is two hash operations — faster than nothing, but slower than `move_to_end`'s single relink on a long-lived dict (the relink does not invalidate the hash slot).

### Lines 38–43: Cache miss — `popitem(last=False)` evicts the LRU

```python
        # Cache miss — load, store, evict if over capacity.
        value = self._loader(key)
        self._store[key] = value
        if len(self._store) > self._capacity:
            # Pop the LRU entry (the first-inserted / least-recently-moved).
            self._store.popitem(last=False)
        return value
```

`self._store.popitem(last=False)` removes and returns the *leftmost* (first) item. `last=True` (the default) removes the *rightmost* (last) item. This is the API `dict.popitem` does not have — `dict.popitem()` (added in 3.7 for parity) is `last=True` only and accepts no argument.

The `last=False` form is what makes LRU eviction one operation. Without it, you would `next(iter(d))` and `del` — two operations, with a subtle gotcha (the iteration must not be racing another thread). `OrderedDict.popitem(last=False)` is one atomic C-level call.

### Lines 53–62: The smoke test — touch, miss, evict

```python
    cache: LRUCache[UUID, str] = LRUCache(capacity=3, loader=load_user)
    u1, u2, u3, u4 = UUID("00000000-0000-0000-0000-000000000001"), \
                     UUID("00000000-0000-0000-0000-000000000002"), \
                     UUID("00000000-0000-0000-0000-000000000003"), \
                     UUID("00000000-0000-0000-0000-000000000004")

    cache.get(u1); cache.get(u2); cache.get(u3)
    print(f"after 3 gets: len={len(cache)}")
    cache.get(u1)  # touch u1 -> it should now be MRU; u2 is LRU
    cache.get(u4)  # miss; u2 should be evicted
    print(f"after touch + new miss: len={len(cache)}")
    print(f"u1 in cache: {u1 in cache}")
    print(f"u2 in cache: {u2 in cache}")  # should be False — evicted
```

After three gets, the cache holds `u1`, `u2`, `u3` with `u1` LRU and `u3` MRU. The `cache.get(u1)` is a hit — it moves `u1` to the MRU end, so the order is now `u2, u3, u1`. The next miss (`u4`) inserts `u4` at the MRU end (`u2, u3, u1, u4`) and evicts the LRU entry (`u2`) — leaving `u3, u1, u4`.

`u1 in cache` is `True`; `u2 in cache` is `False`. That is the LRU invariant.

### Lines 64–72: The order-sensitive equality demo — the third reason `OrderedDict` exists

```python
    print("\n--- order-sensitive equality demo ---")
    a = OrderedDict([("x", 1), ("y", 2)])
    b = OrderedDict([("y", 2), ("x", 1)])
    c = {"x": 1, "y": 2}
    d = {"y": 2, "x": 1}
    print(f"a == b (OrderedDict, different order): {a == b}")  # False
    print(f"c == d (dict, different order): {c == d}")          # True
    print(f"a == c (OrderedDict vs dict, same order): {a == c}")  # True
```

`a == b` is `False` even though both contain `{"x": 1, "y": 2}` — because `OrderedDict.__eq__` is order-sensitive. `c == d` is `True` because plain `dict.__eq__` is not.

`a == c` is `True` — `OrderedDict` and `dict` are comparable; the order matches, so they are equal. `OrderedDict.__eq__` falls back to plain `dict` comparison when the other side is not an `OrderedDict`.

**Why does order-sensitive equality matter?** Two cases:

1. **Snapshot tests.** If you assert `cache == OrderedDict([("a", 1), ("b", 2)])` and the cache happens to have the same keys in a different order, you want the test to *fail* — the order is the thing being tested. With plain `dict`, the test would pass.
2. **Diff detection.** When you serialise an `OrderedDict` to JSON or YAML and reload it, the order matters for reproducibility. A round-trip through `OrderedDict` preserves order; through `dict` (since 3.7) it also preserves order, but `==` would not flag a reorder introduced by a buggy serializer.

## Execution Trace

```bash
$ uv run python boardly/lru.py
after 3 gets: len=3
after touch + new miss: len=3
u1 in cache: True
u2 in cache: False

--- order-sensitive equality demo ---
a == b (OrderedDict, different order): False
c == d (dict, different order): True
a == c (OrderedDict vs dict, same order): True
```

## Common Mistakes

### Mistake 1: Using `OrderedDict` because "dict is unordered"

```python
from collections import OrderedDict
config = OrderedDict()
config["db_url"] = "..."
config["log_level"] = "..."
# student uses OrderedDict "so iteration order is preserved"
```

**Symptom:** No bug — but the import and the class are dead weight. The code works identically with a plain `dict` because `dict` has been insertion-ordered since Python 3.7.

**Why:** `OrderedDict`'s original raison d'être was ordering. That use case is gone. Today you reach for it only when you need `move_to_end`, `popitem(last=...)`, or order-sensitive equality.

**Fix:** Use `dict`. If a reviewer pushes back, point at the Python 3.7 changelog (the "dict keeps insertion order" line was in the 3.6 changelog as an implementation detail, and 3.7 made it a language guarantee).

### Mistake 2: Calling `dict.popitem()` and expecting to pass `last=False`

```python
d = {"a": 1, "b": 2}
oldest = d.popitem(last=False)   # student expects this to work
```

**Symptom:** `TypeError: dict.popitem() takes no keyword arguments`.

**Why:** `dict.popitem()` (added in 3.7 for parity) only pops the *last* item and accepts no argument. The `last=` parameter exists on `OrderedDict.popitem` only. The `dict` version is a thin compatibility shim, not a full `OrderedDict`-equivalent.

**Fix:** Use `OrderedDict` if you need to pop the first item. Use `dict` and `next(iter(d))` if you only need to *read* the first key without popping.

### Mistake 3: Expecting `OrderedDict` to be faster than `dict`

```python
d = OrderedDict(...)
for i in range(1_000_000):
    d[i] = i
# student expects OrderedDict to be faster than dict because "more specialised"
```

**Symptom:** `OrderedDict` is roughly 2× *slower* than `dict` for the same operations — more memory per entry (the linked-list nodes) and more pointer-chasing per insert.

**Why:** `OrderedDict`'s extra storage is the doubly-linked list of `(key, value)` nodes. That list is what makes `move_to_end` and `popitem(last=False)` O(1), but it adds per-entry cost. For "I just need a dict", `dict` is faster.

**Fix:** Use `OrderedDict` only when you need its API. For everything else, `dict`.

## Engineering Trade-Offs

**Decision:** Use `OrderedDict` when you need `move_to_end`, `popitem(last=False)`, or order-sensitive equality. Use `dict` for everything else.

**Both sides:**

`OrderedDict` wins on:

1. `move_to_end` — there is no plain-`dict` equivalent that is one operation.
2. `popitem(last=False)` — same.
3. Order-sensitive equality — for snapshot tests and diff detection.
4. As the backbone of LRU caches — which is exactly what `functools.lru_cache` uses internally.

`dict` wins on:

1. Speed — fewer pointer-chasing operations per insert.
2. Memory — no per-entry linked-list nodes.
3. JSON-friendliness — `json.dumps(d)` works on a plain `dict`; on an `OrderedDict` it also works (because `OrderedDict` is a `dict` subclass) but the order is preserved without you having to think about it.
4. Builtin — no import.

**Commitment:** `boardly/lru.py` uses `OrderedDict` for the LRU cache (the canonical use). `boardly/config.py` uses `dict` for the layer dicts inside the `ChainMap` (ordering is not the concern there; layering is). The rule: "Need `move_to_end` or first-item pop? `OrderedDict`. Otherwise `dict`."

## Exercises

1. **Exercise 1 — Confirm `move_to_end` mutates order.** Build `OrderedDict([("a",1),("b",2),("c",3)])`, call `.move_to_end("a")`, and print `list(d.keys())`. `Verify: uv run python -c "from collections import OrderedDict; d=OrderedDict([('a',1),('b',2),('c',3)]); d.move_to_end('a'); print(list(d.keys()))"`
2. **Exercise 2 — `move_to_end(last=False)` goes to the front.** Build the same dict, call `.move_to_end("c", last=False)`, confirm `c` is now first. `Verify: uv run python -c "from collections import OrderedDict; d=OrderedDict([('a',1),('b',2),('c',3)]); d.move_to_end('c', last=False); print(list(d.keys()))"`
3. **Exercise 3 — `popitem(last=False)`.** Confirm `OrderedDict([("a",1),("b",2)]).popitem(last=False)` returns `("a", 1)`. `Verify: uv run python -c "from collections import OrderedDict; print(OrderedDict([('a',1),('b',2)]).popitem(last=False))"`
4. **Exercise 4 — Order-sensitive equality.** Confirm `OrderedDict([("a",1),("b",2)]) != OrderedDict([("b",2),("a",1)])` but `{("a",1),("b",2)} == {("b",2),("a",1)}` is not the comparison — use dicts. `Verify: uv run python -c "from collections import OrderedDict; print(OrderedDict([('a',1),('b',2)])==OrderedDict([('b',2),('a',1)]), {'a':1,'b':2}=={'b':2,'a':1})"`
5. **Exercise 5 — Build an MRU cache.** Modify `LRUCache` to evict the *most*-recently-used entry on overflow (an MRU cache). The change is one keyword: `popitem(last=True)`. Confirm the test trace changes. `Verify: uv run python -c "from boardly.lru import LRUCache; from uuid import UUID; c=LRUCache(2, lambda k: f'v_{k}'); u1=UUID('00000000-0000-0000-0000-000000000001'); u2=UUID('00000000-0000-0000-0000-000000000002'); u3=UUID('00000000-0000-0000-0000-000000000003'); c.get(u1); c.get(u2); c.get(u3); print(u1 in c, u2 in c, u3 in c)"`

## Verification

```bash
$ uv run python boardly/lru.py
after 3 gets: len=3
after touch + new miss: len=3
u1 in cache: True
u2 in cache: False

--- order-sensitive equality demo ---
a == b (OrderedDict, different order): False
c == d (dict, different order): True
a == c (OrderedDict vs dict, same order): True
```

## Previously Learned Here

- [[04-collections/05-ChainMap]] — `ChainMap` stores layer references; `OrderedDict` stores ordered entries with a linked list. Both are views over structure, not snapshots.
- [[04-collections/01-Counter]] — `Counter` is also a `dict` subclass with custom behaviour; this lesson continues that pattern.

## What's Next

[[04-collections/07-UserDict-UserList-UserString]] — the last stop in Section 04. `UserDict` is the *safe* way to subclass `dict`. It looks redundant — `class MyDict(dict): ...` works — until you override `__setitem__` and discover that `dict.update` does not call it. `UserDict` solves that by holding the real storage in a `.data` attribute and routing every method through it. The lesson closes the section with the reason the `collections` module has these wrapper classes at all.

## Sources

- **Python `collections.OrderedDict` documentation** — https://docs.python.org/3/library/collections.html#collections.OrderedDict — accessed 2026-10-23 — the canonical reference for `move_to_end`, `popitem(last=...)`, and the equality semantics.
- **Python 3.7 What's New — `dict` insertion order** — https://docs.python.org/3/whatsnew/3.7.html — accessed 2026-10-23 — the changelog entry that made `dict` insertion-ordered as a language guarantee (was a CPython implementation detail in 3.6).
- **`functools.lru_cache` source** — https://github.com/python/cpython/blob/3.12/Lib/functools.py#L540 — accessed 2026-10-23 — uses `OrderedDict` for the underlying cache storage; the `move_to_end` and `popitem(last=False)` calls are the eviction loop.

## What We Learned

- `OrderedDict` still exists in 3.12 because `move_to_end(key, last=True)` and `popitem(last=False)` are not on `dict`.
- Internally `OrderedDict` is a hash table plus a doubly-linked list of `(key, value)` nodes — the linked list is what makes `move_to_end` O(1).
- `OrderedDict.__eq__` is order-sensitive: two `OrderedDict`s with the same items in different order are *not* equal.
- `OrderedDict` vs `dict` comparison falls back to plain `dict.__eq__` (order-insensitive) — useful when you need the order-sensitive form for tests but plain comparison for cross-type code.
- `functools.lru_cache` is built on `OrderedDict`; the eviction loop is exactly the `move_to_end` / `popitem(last=False)` pair this lesson walks.
