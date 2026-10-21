---
title: "Lesson 03: When weakrefs save memory"
aliases:
 - weakref decision rule
 - weakref memory
 - when to use weakrefs
tags:
 - weakref
 - memory
 - decision
 - lru_cache
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[19-weakref/01-WeakValueDictionary]]"
 - "[[19-weakref/02-WeakSet-and-finalize]]"
related_lessons:
 - "[[02-functools/01-lru_cache-and-Caching]]"
 - "[[02-functools/06-cached_property]]"
---

# Lesson 03: When weakrefs save memory

*The decision rule — long-lived mapping of short-lived objects wins, short-lived mapping of long-lived objects loses, and the four cases where weakrefs are forbidden by CPython itself.*

**You're at the very beginning of Section 19, third lesson in — the closer.**

You have seen the three primitives — `WeakValueDictionary`, `WeakKeyDictionary`, `WeakSet`, and `finalize`. The natural question is *when do these actually save memory?* The answer is a single decision rule that fits in one sentence: weakrefs save memory when a long-lived data structure holds objects whose lifetime is owned elsewhere. Inverting the rule tells you when they don't: when a short-lived data structure holds long-lived objects, weakrefs add indirection and save nothing. And there is a third, surprising class — CPython *forbids* weakrefs on `int`, `str`, `tuple`, `list`, `dict`, and `set` (no `__weakref__` slot), so the question is sometimes not "should I?" but "can I?". By the end of this lesson you will have the decision rule committed to print, a runnable demo showing the *wrong* shape (`lru_cache` pinning 50 entries that no one is using) against the *right* shape (`WeakValueDictionary` auto-expiring them), and the slotted-class gotcha that breaks weakrefs on the dataclass you most want to use them on. Take your time. Type every example. **This is how you learn.**

#weakref #memory #decision #lru_cache

## Learning Objectives

By the end of this lesson you will be able to:

1. **State the decision rule** — weakrefs save memory when a long-lived mapping holds short-lived objects; they cost memory when the opposite is true.
2. **Demonstrate the win** — a `WorkerCache` (`WeakValueDictionary`) that auto-expires entries after every request returns, versus `@lru_cache` which pins them forever.
3. **Diagnose the "weakrefs don't help" case** — a pure-function resolver where the value has no other holder, so the `WeakValueDictionary` is empty after every call.
4. **Recognise CPython's forbidden-types list** — `int`, `str`, `tuple`, `list`, `dict`, `set` cannot be weakly referenced; objects with `__slots__` and no `__weakref__` slot also can't.
5. **Fix the slotted-dataclass trap** — `@dataclass(slots=True, weakref_slot=True)` (3.12+) adds `__weakref__` to the generated slots so weakrefs work.

## Prerequisites

Before starting, you need:

- **`WeakValueDictionary`** — [[19-weakref/01-WeakValueDictionary]]. The decision rule is "use `WeakValueDictionary` *when* the cache shape is right"; you must know the API before this lesson's "is it right?" lands.
- **`@lru_cache`** — [[02-functools/01-lru_cache-and-Caching]]. The wrong-shape case in this lesson is "use `lru_cache` where a `WeakValueDictionary` would be better"; you need to know `lru_cache`'s retention contract to see the difference.
- **`@cached_property`** — [[02-functools/06-cached_property]]. The instance-level lazy cache is the third primitive in the comparison; the lesson's commitment table places all three side by side.
- **`@dataclass(slots=True)`** — [[06-dataclasses/04-Slots-and-Performance]]. The slotted-dataclass gotcha is the same shape as the cached_property-slots trap, and the fix is the 3.12 `weakref_slot=True` knob.
- **About 20–30 minutes of focused time.**

**The most common gap: applying weakrefs where they cannot help.**

Students reach for `WeakValueDictionary` after a memory-leak post-mortem says "the cache is pinning 50,000 entries". Sometimes the cache is the cause and `WeakValueDictionary` fixes it. Sometimes the cache is the cause *but the values are immutable short strings* — and `WeakValueDictionary` cannot hold `str` weakly, because CPython does not put a `__weakref__` slot on `str`. The student tries the swap, gets `TypeError`, and concludes "weakrefs are broken". The rule this lesson commits to print is the one that prevents the misunderstanding: weakrefs save memory when the value (a) is weakreferenceable, (b) is held elsewhere by its callers, and (c) those callers' lifetimes are short relative to the cache's. Miss any of the three and the weakref is dead weight.

## The Problem

You ship a long-running `boardly` worker — a background task processor that handles ticket events. Each event causes the worker to load a `Project` (an 80 ms DB call plus 200 ms JSON unpack into a 5 KB dataclass), use it for ~50 ms, and then return. The worker processes 1000 events per minute across 50 distinct `project_id`s. Over an hour, that's 60,000 events.

You put `@lru_cache(maxsize=128)` on the loader. The cache now holds 50 entries forever — 50 × 5 KB = 250 KB resident. That is *fine* in absolute terms; the worker has 256 MB. But it is *wrong in principle*: the 50 entries are pinned even when no event is currently processing. The cache is the largest single contributor to the worker's resident set, and 95% of the time, none of the entries are in use.

You swap to `WeakValueDictionary`. Now the cache holds an entry only while a caller — the event handler — holds a strong reference. The handler loads the project, uses it, returns; the local variable dies; the cache entry dies with it. The cache cost is bounded by *currently in-flight* events, not by *distinct projects seen*. With 4 concurrent handlers, the cache holds at most 4 entries × 5 KB = 20 KB at peak. The 250 KB → 20 KB saving is the *theoretical* maximum; the practical saving is the *principle*: the cache is no longer the reason a `Project` stays in memory.

The inversion: if you swap the shape — a *short-lived* cache of *long-lived* values — `WeakValueDictionary` saves nothing and costs a little. Consider a one-shot script that loads 50,000 `Project`s, indexes them by id in a `WeakValueDictionary`, and writes them to a file. The script holds strong references to all 50,000 in the list it iterates; the `WeakValueDictionary` adds a weakref per entry (about 80 bytes) on top of the strong-reference storage, *and* the script's total memory is unchanged because the strong references are still there. `WeakValueDictionary` saved zero bytes and added 4 MB of weakref overhead. The decision rule is what prevents that mistake.

## The Code

```python
# boardly/worker_cache_demo.py
"""boardly WorkerCache — WeakValueDictionary that auto-expires per request."""
from __future__ import annotations

import functools
import gc
import sys
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A boardly project — 100 fields, ~5 KB once metadata is loaded."""
    id: str
    name: str
    metadata: dict[str, str]  # imagine 100 keys


def fake_load(project_id: str) -> Project:
    """Pretend to load from the database."""
    return Project(
        id=project_id,
        name=project_id.title(),
        metadata={f"key_{i}": f"val_{i}" for i in range(100)},
    )


class WorkerCache:
    """A long-running worker's per-id project cache.

    Holds projects weakly: while the request that loaded them still
    references the Project, the cache returns the same instance; once
    the request finishes and the only strong reference goes away, the
    cache entry auto-expires. Memory cost is bounded by *currently
    in-flight requests*, not by *total distinct projects ever seen*.
    """

    def __init__(self) -> None:
        self._cache: weakref.WeakValueDictionary[str, Project] = (
            weakref.WeakValueDictionary()
        )

    def get_or_load(self, project_id: str) -> Project:
        cached = self._cache.get(project_id)
        if cached is not None:
            return cached
        fresh = fake_load(project_id)
        self._cache[project_id] = fresh
        return fresh

    def __len__(self) -> int:
        return len(self._cache)


def process_request(worker: WorkerCache, project_id: str) -> int:
    """Simulate one request that loads a project, uses it, returns."""
    p = worker.get_or_load(project_id)
    return sys.getsizeof(p)  # tiny; the *referenced* dict is the payload


def main() -> None:
    print("=== WorkerCache with WeakValueDictionary ===")
    worker = WorkerCache()

    # Simulate 1000 distinct requests across 50 distinct project_ids.
    for i in range(1000):
        project_id = f"p_{i % 50:04d}"
        process_request(worker, project_id)

    gc.collect()
    print(f"  cache len after 1000 requests across 50 ids: {len(worker)}")
    # All requests have returned; no strong refs to any Project survive.
    # The cache should be empty.

    print()
    print("=== comparison: lru_cache would pin all 50 forever ===")
    @functools.lru_cache(maxsize=128)
    def cached_load(project_id: str) -> Project:
        return fake_load(project_id)

    for i in range(1000):
        project_id = f"p_{i % 50:04d}"
        cached_load(project_id)

    print(f"  lru_cache info: {cached_load.cache_info()}")
    print(f"  lru_cache holds {cached_load.cache_info().currsize} entries "
          f"after 1000 requests across 50 ids — they live until cache_clear()")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–11: The model and the loader

```python
# boardly/worker_cache_demo.py
"""boardly WorkerCache — WeakValueDictionary that auto-expires per request."""
from __future__ import annotations

import functools
import gc
import sys
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A boardly project — 100 fields, ~5 KB once metadata is loaded."""
    id: str
    name: str
    metadata: dict[str, str]  # imagine 100 keys
```

`weakref` for `WeakValueDictionary`. `functools` for the comparison half — the `lru_cache` decorator on the second loader. `gc` for forced collection in the demo. `sys` for `sys.getsizeof`. `Project` is `frozen=True` because (a) it's a value type, (b) it might be used as a `WeakKeyDictionary` key elsewhere, and (c) frozen dataclasses are the canonical `boardly` model shape (see [[06-dataclasses/03-Frozen-and-Immutability]]).

The `metadata` field carries a 100-key dict — that is the payload that makes a `Project` worth ~5 KB. Without it, the `Project` would be ~200 bytes (the dataclass instance + 3 small fields), and weakref overhead would dominate the value. The 100-key dict is the *expensive* part — the part you want to expire when the request finishes.

### Lines 14–22: The fake loader

```python
def fake_load(project_id: str) -> Project:
    """Pretend to load from the database."""
    return Project(
        id=project_id,
        name=project_id.title(),
        metadata={f"key_{i}": f"val_{i}" for i in range(100)},
    )
```

`fake_load` is the stand-in for an 80 ms DB call plus a 200 ms JSON unpack. It constructs a fresh `Project` with a 100-key metadata dict. The fresh `Project` is returned to its caller; the caller decides whether to store it (in a local variable, in a list, in a cache). The loader itself does not retain the value — that's the loader's contract with the rest of the program, and it's what makes the `WeakValueDictionary` shape work.

**Why is the loader's "no retain" contract load-bearing?** Because the `WeakValueDictionary` shape requires the *caller* to own the lifetime. If the loader itself cached strongly (e.g., it stored each `Project` in a module-level `dict` for "easy access later"), the `WeakValueDictionary` would be useless — the strong references in the loader's own cache would keep every `Project` alive forever, defeating the auto-expiry. The loader must be "load, return, forget"; the cache must be "remember weakly"; the caller must be "use, return, drop". All three contracts together produce the memory win. Break any one and the win collapses.

### Lines 25–46: The `WorkerCache`

```python
class WorkerCache:
    """A long-running worker's per-id project cache.

    Holds projects weakly: while the request that loaded them still
    references the Project, the cache returns the same instance; once
    the request finishes and the only strong reference goes away, the
    cache entry auto-expires. Memory cost is bounded by *currently
    in-flight requests*, not by *total distinct projects ever seen*.
    """

    def __init__(self) -> None:
        self._cache: weakref.WeakValueDictionary[str, Project] = (
            weakref.WeakValueDictionary()
        )

    def get_or_load(self, project_id: str) -> Project:
        cached = self._cache.get(project_id)
        if cached is not None:
            return cached
        fresh = fake_load(project_id)
        self._cache[project_id] = fresh
        return fresh

    def __len__(self) -> int:
        return len(self._cache)
```

`get_or_load` is the canonical read-with-fallback pattern from [[19-weakref/01-WeakValueDictionary]]. The soft `.get()` returns `None` on a dead entry; the fallback reloads, re-inserts, and returns. The returned `Project` is held strongly by the caller's local variable — so the cache entry is alive at least until the caller drops the local.

The `__len__` is for observability — the demo prints `len(worker)` after 1000 simulated requests to show the cache is empty. In production you would expose this as a metric (`boardly_worker_cache_size`) so you can see the cache's high-water mark under load; the high-water mark should track the worker's concurrency, not its history.

**Why is the high-water mark "concurrency" the right shape?** Because the entries that survive at any moment are exactly the entries being used by *currently in-flight* requests. If the worker has 4 concurrent handlers, at most 4 `Project`s are in flight at any instant, so at most 4 entries are alive in the cache. The cache's memory footprint scales with the worker's concurrency — which is what you designed for — not with the number of distinct projects the worker has *ever* seen, which is unbounded. This is the "long-lived mapping of short-lived objects" case — the case where weakrefs win.

### Lines 49–54: The simulated request

```python
def process_request(worker: WorkerCache, project_id: str) -> int:
    """Simulate one request that loads a project, uses it, returns."""
    p = worker.get_or_load(project_id)
    return sys.getsizeof(p)  # tiny; the *referenced* dict is the payload
```

`process_request` is the per-event shape: load the `Project` into a local `p`, do work with it (here, just `sys.getsizeof`), return. The local `p` is the only strong reference; when the function returns, `p`'s refcount hits zero, the `Project` is reaped, the cache entry dies. The `sys.getsizeof` return value is meaningless for the lesson — it's there to make the function "do something" with `p` so the optimizer (if any) doesn't elide the load.

**Why `sys.getsizeof(p)` and not just `pass`?** Because a no-op `pass` would let an aggressive interpreter elide the local-variable binding entirely (some runtimes do this in escape analysis), which would mean `p` is never really bound and the cache's `fresh = fake_load(...)` line is the last strong reference — meaning the entry dies the moment `get_or_load` returns. `sys.getsizeof(p)` is a real use of `p` that prevents the elision. In CPython 3.12 the elision doesn't happen anyway (CPython doesn't do escape analysis), but the principle stands: a benchmark should *use* the value it loads.

### Lines 57–87: The demo and the comparison

```python
def main() -> None:
    print("=== WorkerCache with WeakValueDictionary ===")
    worker = WorkerCache()

    # Simulate 1000 distinct requests across 50 distinct project_ids.
    for i in range(1000):
        project_id = f"p_{i % 50:04d}"
        process_request(worker, project_id)

    gc.collect()
    print(f"  cache len after 1000 requests across 50 ids: {len(worker)}")
    # All requests have returned; no strong refs to any Project survive.
    # The cache should be empty.

    print()
    print("=== comparison: lru_cache would pin all 50 forever ===")
    @functools.lru_cache(maxsize=128)
    def cached_load(project_id: str) -> Project:
        return fake_load(project_id)

    for i in range(1000):
        project_id = f"p_{i % 50:04d}"
        cached_load(project_id)

    print(f"  lru_cache info: {cached_load.cache_info()}")
    print(f"  lru_cache holds {cached_load.cache_info().currsize} entries "
          f"after 1000 requests across 50 ids — they live until cache_clear()")
```

The first half runs 1000 simulated requests across 50 distinct `project_id`s through the `WorkerCache`. Each request loads, uses, returns; the cache entry for that `project_id` dies when the request returns. After `gc.collect()`, `len(worker)` is 0 — the cache holds nothing, because no request is in flight. The 50 distinct `project_id`s were loaded ~20 times each; the cache served hits *within* a request (if a request asked for the same id twice in one handler) but never *across* requests (because each request finished and dropped its reference).

The second half runs the same 1000 requests through an `@lru_cache(maxsize=128)`-decorated `cached_load`. After the run, `cache_info()` reports `currsize=50` — all 50 distinct `project_id`s are pinned forever (or until LRU evicts them, which it won't, because 50 < 128). The cache's memory footprint is `50 × ~5 KB = 250 KB`, *all the time*, even when no request is in flight. That's the wrong shape for this workload.

**Why is `lru_cache` "wrong" here and not just "suboptimal"?** Because the contract is mismatched. `lru_cache`'s contract is "I retain values so callers don't recompute them"; that contract is right when the values are *pure* (no side effects) and *cheap to evict* (small enough that 128 of them is fine). The `Project` value is neither: it has a side effect (DB call, log line), and it's expensive enough that 128 of them is 640 KB. The `WeakValueDictionary` contract is "I share values while their owners are using them"; that contract fits the workload — the worker always has at most a handful of `Project`s in flight at once. The right primitive for the right shape.

## Execution Trace

```bash
$ uv run python boardly/worker_cache_demo.py
=== WorkerCache with WeakValueDictionary ===
  cache len after 1000 requests across 50 ids: 0

=== comparison: lru_cache would pin all 50 forever ===
  lru_cache info: CacheInfo(hits=950, misses=50, maxsize=128, currsize=50)
  lru_cache holds 50 entries after 1000 requests across 50 ids — they live until cache_clear()
```

The `WorkerCache` shows `len == 0` after 1000 requests — every entry expired with the request that loaded it. The `lru_cache` shows `currsize=50` — every distinct `project_id` is pinned, even though no caller is currently using any of them. The two caching strategies made the same number of DB calls (50 distinct misses each); the difference is *resident memory after the requests finish*, not request count.

## Common Mistakes

### Mistake 1: Using `WeakValueDictionary` where `lru_cache` is right

```python
import weakref

@weakref.WeakValueDictionary()  # ← doesn't decorate, doesn't memoize
def slug_to_id(slug: str) -> str:
    return _db_lookup(slug)  # returns a 5-char string

result = slug_to_id("auth")  # ← string returned, no one holds it
# cache is empty immediately after — string had no strong holder
```

**Symptom:** `WeakValueDictionary` cache hit rate is zero; every call is a miss; the cache appears useless.

**Why:** The return value (a `str`) has no strong reference held by any caller after the resolver returns — `slug_to_id("auth")` returns `"p_001"`, the caller uses it as an argument somewhere, the local variable in `slug_to_id` is gone, the cache's weakref callback fires, the entry is removed before the next call. The cache never has a hit.

**Fix:** Use `@lru_cache(maxsize=N)` for pure resolvers whose values are immutable and small. `lru_cache` holds the value *strongly* in the wrapper's underlying dict, which is exactly what a pure resolver needs — the cache is the sole owner, and that's fine for a 5-char string. The `WeakValueDictionary` shape only works when the value is held *elsewhere*; pure resolvers don't have a "elsewhere".

### Mistake 2: Trying to weakref a `str`, `int`, `tuple`, `list`, or `dict`

```python
import weakref

cache = weakref.WeakValueDictionary()
cache["greeting"] = "hello"  # ← str is not weakreferenceable
# TypeError: cannot create weak reference to 'str' object
```

**Symptom:** `TypeError: cannot create weak reference to 'str' object` (or `'int'`, `'tuple'`, `'list'`, `'dict'`, `'set'`) on the first insert.

**Why:** CPython's built-in `int`, `str`, `tuple`, `list`, `dict`, and `set` types do not declare `__weakref__` in their instance layout — there is no slot for the weakref list on these objects. This is an optimisation: these types are allocated in vast numbers, and the 8 bytes for `__weakref__` would multiply across every string and int in the program. The cost is that you cannot weakref them. Subclassing opts in: `class MyStr(str): pass` *does* get `__weakref__`, at the cost of one extra allocation per instance.

**Fix:** Wrap the primitive in a class — either a `@dataclass` (which gets `__weakref__` by default) or a manual subclass. For a per-name cache of *strings*, the right primitive is `lru_cache` (which holds them strongly); for a per-name cache of *objects that contain strings*, the right primitive is `WeakValueDictionary` on the wrapping object, not on the string.

### Mistake 3: Slotted dataclass without `weakref_slot=True`

```python
from dataclasses import dataclass
import weakref

@dataclass(slots=True)               # ← no __weakref__ slot generated
class Project:
    id: str

p = Project(id="p_001")
weakref.ref(p)  # ← TypeError: cannot create weak reference to 'Project' object
```

**Symptom:** `TypeError: cannot create weak reference to 'Project' object` on the first `weakref.ref(p)` or `WeakValueDictionary[id] = p` call.

**Why:** `@dataclass(slots=True)` generates `__slots__` from the field annotations — and *only* from the field annotations. The generated `__slots__` does not include `"__weakref__"`, so instances of the slotted dataclass have no slot for the weakref list. The class cannot be weakly referenced. This is the same trap that breaks `cached_property` on slotted classes (see [[02-functools/06-cached_property]] and [[06-dataclasses/04-Slots-and-Performance]]).

**Fix:** On Python 3.12+, use `@dataclass(slots=True, weakref_slot=True)`. The `weakref_slot=True` parameter (added in **Python 3.12**) tells the slot generator to add `"__weakref__"` to the generated `__slots__` tuple, so instances are weakreferenceable. On Python 3.11 and earlier, you must declare `__slots__` manually: `__slots__ = ("id", "__weakref__")`.

**Note — `weakref_slot=True` requires Python 3.12+.**

The `weakref_slot` parameter was added to `dataclasses.dataclass` in Python 3.12 (via [gh-86447](https://github.com/python/cpython/issues/86447)). On Python 3.11 and earlier, you cannot combine `slots=True` with automatic weakref support — you must declare `__slots__` manually, including `"__weakref__"` in the tuple.

### Mistake 4: Holding the value somewhere "for convenience"

```python
class WorkerCache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()
        self._all_projects: list[Project] = []   # ← strong reference!

    def get_or_load(self, project_id: str) -> Project:
        cached = self._cache.get(project_id)
        if cached is not None:
            return cached
        fresh = fake_load(project_id)
        self._cache[project_id] = fresh
        self._all_projects.append(fresh)        # ← defeats the whole cache
        return fresh
```

**Symptom:** `WeakValueDictionary` cache never expires — `len(cache)` grows forever, mirroring `len(self._all_projects)`.

**Why:** The `_all_projects` list holds a strong reference to every `Project` ever loaded. The weakref in the cache is therefore *never* the last reference — the list always has one. The cache's auto-removal callback never fires because the value never dies. The whole `WeakValueDictionary` is dead weight.

**Fix:** Remove the `_all_projects` list. If you genuinely need a "list of all projects ever loaded" (e.g., for an audit log), accept that you cannot use a `WeakValueDictionary` — the strong-reference list defeats it. Use a plain `dict` and accept the memory cost, or use a `WeakSet` for "things I might want to inspect but don't want to keep alive" (which has the same problem if you also keep the strong list). The decision rule is binary: either the value's lifetime is owned *outside* the cache (use weakref), or it's owned *by* the cache (use strong). There is no "both".

## Engineering Trade-Offs

**Decision:** Use `WeakValueDictionary` for long-lived mappings of short-lived objects whose lifetime is owned by their callers. Use `@lru_cache` for short-lived mappings of immutable values whose lifetime is owned by the cache. Use `@cached_property` for per-instance lazy attributes whose lifetime is owned by the instance.

**Both sides:** The decision rule is "who owns the lifetime?". `WeakValueDictionary` says "not me" — the cache is a *sharing* structure, not a *retention* structure; the value lives as long as its caller needs it, no longer. `lru_cache` says "me" — the cache is the retention structure; the value lives until the LRU evicts it. `cached_property` says "the instance" — the value lives as long as the instance does. Pick the primitive whose ownership model matches your workload. Mismatches produce the symptoms above — `WeakValueDictionary` with no hits (no caller holds the value), `lru_cache` with too much memory (cache retains values no caller needs), `cached_property` with a slotted-class `TypeError` (no instance `__dict__` to store the cache in).

**Commitment:** `boardly` uses the three primitives as follows. `WeakValueDictionary` for `ProjectCache`, `UserCache`, `TicketCache` — per-id caches of recently-loaded domain objects in long-running workers. `@lru_cache` for `slug_to_id`, `role_to_permissions`, `feature_flag_to_state` — pure resolvers whose values are immutable and small. `@cached_property` for `Project.metadata`, `User.permissions`, `Ticket.derived_status` — per-instance lazy attributes on classes with `__dict__`. The three together cover the entire cache surface of the application, and the decision rule for picking one is committed in the project's style guide.

**Why not use `WeakValueDictionary` everywhere, just to be safe?** Because the cost of using the wrong primitive is real. `WeakValueDictionary` on a pure resolver produces a cache with zero hits (every call is a miss because the value has no caller-held reference). `WeakValueDictionary` on a value that's also held strongly elsewhere is dead weight (the weakref is never the last reference). `WeakValueDictionary` on a `str` value doesn't even construct — it raises `TypeError` on the first insert. The "safe" choice is *not* safe; it's a foot-gun. The right primitive for the right shape, every time.

## Exercises

1. **Exercise 1 — Confirm the auto-expiry.** Add a `print(f"mid-run len: {len(worker)}")` inside the `for i in range(1000)` loop, after every 100th iteration. Observe `len` is 1 (the just-loaded `Project`'s entry) — every other entry has expired because its request returned. `Verify: uv run python boardly/worker_cache_demo.py`

2. **Exercise 2 — Demonstrate the forbidden-types trap.** Replace `Project` with `str` in the `WeakValueDictionary` — change `fake_load` to return `project_id.upper()` and the cache type to `WeakValueDictionary[str, str]`. Confirm `TypeError: cannot create weak reference to 'str' object`. Then wrap the string in a `@dataclass(frozen=True)` class `SlugRef(value: str)` and confirm the cache works. `Verify: uv run python boardly/worker_cache_demo.py`

3. **Exercise 3 — Reproduce the slotted-dataclass trap.** Change `Project` to `@dataclass(frozen=True, slots=True)` (no `weakref_slot`). Confirm `weakref.ref(Project(id="x"))` raises `TypeError`. Then add `weakref_slot=True` (Python 3.12+) and confirm `weakref.ref` works. `Verify: uv run python boardly/worker_cache_demo.py`

4. **Exercise 4 — Invert the shape.** Write a *short-lived* cache that holds *long-lived* values: load all 50 `Project`s into a list once, then look them up in a `WeakValueDictionary` whose values are the list's elements. Confirm `len(cache)` stays at 50 forever (the list holds them). The `WeakValueDictionary` saved zero bytes — the strong list is the actual owner. `Verify: uv run python boardly/worker_cache_demo.py`

5. **Exercise 5 — Add a high-water-mark metric.** Add `self._high_water = 0` to `WorkerCache.__init__`, and `self._high_water = max(self._high_water, len(self._cache))` after each `get_or_load`. Print `self._high_water` at the end. Confirm the high-water mark tracks the worker's effective concurrency (1, in this single-threaded demo). Bonus: bump the demo to use 4 threads and confirm the high-water mark is 4. `Verify: uv run python boardly/worker_cache_demo.py`

## Verification

```bash
$ uv run python boardly/worker_cache_demo.py
=== WorkerCache with WeakValueDictionary ===
  cache len after 1000 requests across 50 ids: 0

=== comparison: lru_cache would pin all 50 forever ===
  lru_cache info: CacheInfo(hits=950, misses=50, maxsize=128, currsize=50)
  lru_cache holds 50 entries after 1000 requests across 50 ids — they live until cache_clear()
```

## Previously Learned Here

- [[19-weakref/01-WeakValueDictionary]] — the API this lesson's `WorkerCache` is built on; the soft `.get()` lookup is the canonical read-with-fallback pattern.
- [[19-weakref/02-WeakSet-and-finalize]] — `WeakSet` for "collection of things I don't own" is the same decision rule in a different shape; `finalize` is for "cleanup on death", a separate axis.
- [[02-functools/01-lru_cache-and-Caching]] — the *strong-reference* cache this lesson compares against; the cache-owned-lifetime alternative.
- [[02-functools/06-cached_property]] — the *instance-level* strong-reference cache; the instance-owned-lifetime alternative. The slotted-class `TypeError` in Mistake 3 is the same trap as cached_property on slotted classes.
- [[06-dataclasses/04-Slots-and-Performance]] — the `weakref_slot=True` fix is the 3.12 knob that adds `__weakref__` to the generated `__slots__`, parallel to the `__dict__` slot fix from this lesson.

## What's Next

You have reached the end of Section 19. The three lessons — `WeakValueDictionary`, `WeakSet`/`finalize`, and this decision rule — together cover the entire surface of `weakref` that a `boardly` engineer uses in production. The next natural step depends on your direction:

- If you are continuing through the standard library: [[20-warnings/00-warnings-MOC]] is the next section. `warnings` is small, focused, and the right place to land after the "lifetime and cleanup" territory of `weakref`.
- If you came here from a FastAPI dependency-cache question: return to [[02-functools/01-lru_cache-and-Caching]] and re-read the `Depends` parallel — the FastAPI dependency cache is an `lru_cache`-shaped idea (cache-owned lifetime) and the contrast with `WeakValueDictionary` (caller-owned lifetime) is the cleanest way to internalise the decision rule.
- If you came here from a memory-leak post-mortem: re-read the Common Mistakes section of this lesson, then audit your own code for the four shapes — pure-resolver (`lru_cache`), per-id (`WeakValueDictionary`), per-instance (`cached_property`), per-collection (`WeakSet`). Mismatches are the leak.

## Sources

- **`weakref` — Weak references** — https://docs.python.org/3/library/weakref.html — accessed 2026-10-23 — the canonical reference; the "Weak Reference Objects" and "WeakSet" sections together document every primitive this lesson's decision rule applies to.
- **PEP 205 — Weak References** — https://peps.python.org/pep-0205/ — accessed 2026-10-23 — the original PEP; the "Applications" section is the canonical list of use cases this lesson commits to a single rule.
- **Python Data Model — `__slots__`** — https://docs.python.org/3/reference/datamodel.html#slots — accessed 2026-10-23 — explains why `__slots__` without `__weakref__` forbids weak references, and why the built-in `int`/`str`/`tuple`/`list`/`dict`/`set` types don't have `__weakref__` slots.
- **`dataclasses` — `weakref_slot` parameter** — https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass.params — accessed 2026-10-23 — the 3.12 knob that adds `__weakref__` to the generated `__slots__`; the fix for the slotted-dataclass trap.
- **CPython `gh-86447` — Add `weakref_slot` to `@dataclass`** — https://github.com/python/cpython/issues/86447 — accessed 2026-10-23 — the issue that added the `weakref_slot=True` parameter in Python 3.12.

## What We Learned

- You can state the decision rule — weakrefs save memory when a long-lived mapping holds short-lived objects; they cost memory when the opposite is true.
- You can demonstrate the win — `WorkerCache` (`WeakValueDictionary`) auto-expires entries after every request returns, while `@lru_cache` pins them forever.
- You can diagnose the "weakrefs don't help" case — a pure-function resolver where the value has no other holder, so the `WeakValueDictionary` is empty after every call.
- You recognise CPython's forbidden-types list — `int`, `str`, `tuple`, `list`, `dict`, `set` cannot be weakly referenced; objects with `__slots__` and no `__weakref__` slot also can't.
- You can fix the slotted-dataclass trap — `@dataclass(slots=True, weakref_slot=True)` (3.12+) adds `__weakref__` to the generated slots so weakrefs work.
