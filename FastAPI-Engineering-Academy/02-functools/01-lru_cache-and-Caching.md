---
title: "Lesson 01: lru_cache and Caching"
aliases:
 - lru_cache
 - functools.cache
 - functools.lru_cache
tags:
 - functools
 - lru_cache
 - caching
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[02-functools/06-cached_property]]"
 - "[[02-functools/02-wraps-and-Decorators]]"
first_taught_in: "02-functools/01-lru_cache-and-Caching"
---

# Lesson 01: `lru_cache` and Caching

*The cheapest, fastest, most under-used caching primitive in Python — and the one that powers your settings loader, your slug resolver, and FastAPI's own dependency cache shape.*

**You're at the very beginning of Section 02.**

`functools.lru_cache` is one of those features that, once you internalise it, changes the shape of every "slow function" you write. You stop reaching for Redis when an in-process LRU will do. You stop worrying about thread safety on a settings loader, because the cache has a lock. You start seeing `@lru_cache` the way you see `@property` — a one-line decorator that does something genuinely hard. By the end of this lesson you will know exactly when to reach for it, when not to, and the precise reason `cache_info()` prints what it prints. Take your time. Type every example. **This is how you learn.**

#functools #lru_cache #caching #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@lru_cache(maxsize=N)`** to a pure function and explain the LRU eviction policy.
2. **Inspect cache state** with `cache_info()` and reset it with `cache_clear()`.
3. **Use the unbounded form** `functools.cache()` (3.9+) and state when an unbounded cache is acceptable.
4. **Use the `typed=True` parameter** (3.8+) so the cache distinguishes between arguments of different types that compare equal (e.g., `1` and `1.0`).
5. **Explain the thread-safety guarantee** the cache lock gives you — it serialises dict mutations (no data corruption), but it does *not* prevent concurrent calls from racing into the user function.
6. **Choose between `lru_cache` and `cached_property`** — and articulate the line between them.

## Prerequisites

Before starting, you need:

- **Basic Python type hints** — `def f(x: str) -> dict[str, str]:` should read like English. If not, run through [[01-typing/01-Type-Hints-Basics]] first.
- **About 30–40 minutes of focused time.**

**The most common gap: confusing `lru_cache` with `cached_property`.**

Students reach for `cached_property` when they mean `lru_cache` (a function-level cache that keys on arguments) and vice versa. The rule of thumb, which we will justify in detail later in the lesson: if the cached thing takes arguments, use `lru_cache`; if it takes no arguments and lives on an instance, use `cached_property`.

## The Problem

You ship a project-management API called `boardly`. Every endpoint that touches a ticket needs to resolve the ticket's `project_slug` to a `project_id` so the SQL query can filter by it. The lookup is one `SELECT id FROM projects WHERE slug = $1` — fast in absolute terms, ~80ms on a cold connection, but it happens on every request, and 80ms × 1000 RPS is 80 seconds of database time per minute that buys you nothing. The slugs change once a quarter. You need a cache. You reach for Redis because that's what the blog post said, you wire up a client, you add a serializer, you handle the `ConnectionError`, you write a fallback, you write a test for the fallback. Two hundred lines of code later you have a cache.

The cache is wrong.

The slug → id mapping is *process-local knowledge* — it changes when the process restarts, never mid-flight. Redis was the wrong tool. The right tool is `@lru_cache(maxsize=128)`, a one-line decorator with a thread-safety lock, a `cache_info()` method that tells you exactly what hit and what missed, and a `cache_clear()` for the rare case you need to invalidate. No client. No serializer. No fallback test. The cache lives in the process and dies with the process. For a slug resolver, that's exactly the lifecycle you want.

## The Code

```python
# boardly/lru_cache_demo.py
"""Demonstrate functools.lru_cache for a boardly slug-resolver."""
from __future__ import annotations

import functools
import threading
import time

# Imagine this is a Postgres round-trip — ~80ms each.
_DB: dict[str, dict[str, str]] = {
    "auth": {"id": "p_001", "name": "Auth Rewrite", "owner": "rahul"},
    "billing": {"id": "p_002", "name": "Billing Migration", "owner": "maria"},
    "search": {"id": "p_003", "name": "Search v2", "owner": "ana"},
}


def _fetch(slug: str) -> dict[str, str]:
    """Pretend to round-trip to the database."""
    time.sleep(0.08)  # simulated network latency
    if slug not in _DB:
        raise KeyError(slug)
    return dict(_DB[slug])  # copy: callers must not mutate the cached value


@functools.lru_cache(maxsize=128)
def resolve_project(slug: str) -> dict[str, str]:
    """Cached project metadata. Thread-safe via the cache's internal lock."""
    return _fetch(slug)


# Python 3.8+ typed=True — distinct cache entries for arguments of different types.
@functools.lru_cache(maxsize=128, typed=True)
def resolve_owner(slug: str) -> str:
    """Cached owner lookup; `typed=True` keeps `1` and `1.0` separate."""
    return _fetch(slug)["owner"]


def hit_concurrent(slug: str, workers: int = 8) -> None:
    """Spawn N threads racing on the same slug; observe the cache-info delta."""
    barrier = threading.Barrier(workers)

    def worker() -> None:
        barrier.wait()  # every thread starts the call at the same instant
        resolve_project(slug)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def main() -> None:
    resolve_project("auth")
    resolve_project("auth")
    resolve_project("billing")
    print(resolve_project.cache_info())
    hit_concurrent("search", workers=8)
    print(resolve_project.cache_info())
    print(f"owner of 'auth' is {resolve_owner('auth')!r}")
    resolve_project.cache_clear()
    print("after clear:", resolve_project.cache_info())


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Module header and imports

```python
# boardly/lru_cache_demo.py
"""Demonstrate functools.lru_cache for a boardly slug-resolver."""
from __future__ import annotations

import functools
import threading
import time
```

`from __future__ import annotations` makes every annotation a string at runtime — this is the **PEP 563** deferred-annotations mode. We use it here so the `dict[str, str]` return annotation on line 22 works as a plain string and doesn't require `from typing import Dict`. In Python 3.9+ `dict[str, str]` is fine at runtime anyway, but the future import is the project-wide convention.

`functools` is the star of this lesson — `lru_cache`, `cache`, `wraps`, `singledispatch`, and `cached_property` all live here. `threading` is imported for the concurrent-hit demonstration later; `time` is imported so we can simulate an 80ms database round-trip with `time.sleep`.

### Lines 10–14: The fake database

```python
# Imagine this is a Postgres round-trip — ~80ms each.
_DB: dict[str, dict[str, str]] = {
    "auth": {"id": "p_001", "name": "Auth Rewrite", "owner": "rahul"},
    "billing": {"id": "p_002", "name": "Billing Migration", "owner": "maria"},
    "search": {"id": "p_003", "name": "Search v2", "owner": "ana"},
}
```

`_DB` is a module-level dict standing in for a Postgres table. The leading underscore is the convention for "private to this module" — students reading the file should know not to import `_DB` from elsewhere. In a real `boardly` deployment this would be a `SELECT` against the `projects` table, but for a runnable lesson a dict is faster, clearer, and offline.

**Why use a dict instead of a real database call?** The lesson is about `lru_cache`, not `asyncpg`. Pulling in a real Postgres connection would force every reader to set up a database before they could run the example, which kills the lesson's pace. The `time.sleep(0.08)` on line 19 stands in for the latency; the cached behaviour is identical.

### Lines 17–22: The slow function

```python
def _fetch(slug: str) -> dict[str, str]:
    """Pretend to round-trip to the database."""
    time.sleep(0.08)  # simulated network latency
    if slug not in _DB:
        raise KeyError(slug)
    return dict(_DB[slug])  # copy: callers must not mutate the cached value
```

`_fetch` is the uncached function — every call costs 80ms of wall time. The `time.sleep` is the simulation of network latency; in production this would be `await conn.fetchrow(...)`. The `KeyError` on line 20 mirrors what a real `SELECT … WHERE slug = $1` would do if it returned no rows: the database call doesn't return `None`, it raises, and the cache layer propagates that exception correctly.

The `dict(_DB[slug])` on line 21 returns a *shallow copy*. This matters. If we returned `_DB[slug]` directly, callers would hold a reference to the same object the cache stores, and a caller doing `result["id"] = "tampered"` would silently mutate the cached value for every subsequent call. The copy breaks that aliasing chain. For nested values (like a list inside the dict) you'd need `copy.deepcopy`, but for a flat string-valued dict the shallow copy is enough.

### Lines 25–28: The cached function

```python
@functools.lru_cache(maxsize=128)
def resolve_project(slug: str) -> dict[str, str]:
    """Cached project metadata. Thread-safe via the cache's internal lock."""
    return _fetch(slug)
```

`@functools.lru_cache(maxsize=128)` is the canonical form. The decorator returns a `functools._lru_cache_wrapper` object that wraps `resolve_project` and adds four methods: `.cache_info()`, `.cache_clear()`, `.get_cache_info()` (3.9+, internal), and a `__wrapped__` attribute pointing back at the original function. `maxsize=128` means the cache holds the 128 most-recently-used entries; the 129th distinct slug evicts the least-recently-used entry. Set `maxsize=None` for an unbounded cache — that's the same as `@functools.cache` (3.9+), which we'll meet shortly.

**Why 128 and not 1024?** 128 is the stdlib default. It's enough for a typical `boardly` deployment (a few dozen active projects, a few hundred slugs in the worst case) and small enough that the cache's memory footprint is negligible — the underlying dict is a `dict` of `{key: value}` plus a doubly-linked list for the LRU ordering, so 128 entries cost roughly 128 × (key_size + value_size) plus a few hundred bytes of list overhead. If you have 50,000 slugs to cache, you don't want an LRU — you want a `TTLCache` from `cachetools` or a real Redis. The `maxsize` parameter is the lever that says "this cache is bounded by design."

**Warning — `lru_cache` is not a compute-serialiser.** The internal lock protects the cache dict from corruption (you'll never see a half-written entry), but it does *not* prevent two racing threads from both computing the user function. The cache lookup, the `misses++`, and the dict store are individually atomic — the user-function call is *not* inside the lock. If you need "exactly one thread computes, the rest see a hit", you must add your own `threading.Lock` around the call, or use `functools.cached_property` on an instance with the lock pattern from [[02-functools/06-cached_property]].

### Lines 31–34: The `typed=True` parameter (Python 3.8+)

```python
# Python 3.8+ typed=True — distinct cache entries for arguments of different types.
@functools.lru_cache(maxsize=128, typed=True)
def resolve_owner(slug: str) -> str:
    """Cached owner lookup; `typed=True` keeps `slug` and `Slug("auth")` separate."""
    return _fetch(slug)["owner"]
```

The `typed` parameter was added to `lru_cache` in **Python 3.8**. When `typed=True`, the cache key includes each argument's *type* — so `resolve_owner(1)` and `resolve_owner(1.0)` are cached as *two* entries, because `1` (an `int`) and `1.0` (a `float`) are different types even though they compare equal. The default is `typed=False`, where the cache key is built from value equality alone.

**Why is `typed=True` not the default?** Because in most code the argument type is fixed by the function signature (`slug: str`), so all callers pass the same type and `typed=True` would only add a constant type tag to every key for no benefit. The parameter pays off when the function accepts arguments of *different* types that compare equal — e.g., a `trig(x)` function that accepts both `int` and `float`. With `typed=False`, `trig(1)` and `trig(1.0)` collide in the cache; with `typed=True`, they're cached separately.

**Note — there is no `lru_cache[T]` subscript form.** A common misconception (it appears in many blog posts) is that `@functools.lru_cache[str]` declares the return type. It does not — `lru_cache` is not subscriptable, and `@functools.lru_cache[str]` raises `TypeError: 'function' object is not subscriptable`. The return type comes from the function's own annotation; `lru_cache` preserves it via `functools.wraps`. The `typed=True` parameter is the only `typed` knob in the API.

### Lines 37–46: The concurrent-hit demo

```python
def hit_concurrent(slug: str, workers: int = 8) -> None:
    """Spawn N threads racing on the same slug; observe the cache-info delta."""
    barrier = threading.Barrier(workers)

    def worker() -> None:
        barrier.wait()  # every thread starts the call at the same instant
        resolve_project(slug)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
```

`hit_concurrent` exists to probe a specific question: what happens when N threads enter the cache lookup for the same key at the same instant? We build a `threading.Barrier(workers)` — a sync primitive that releases all waiters simultaneously when the `workers`-th thread calls `.wait()`. Each worker calls `barrier.wait()` first (blocking until all threads are ready), then immediately calls `resolve_project(slug)`. The intent is to make all 8 threads enter the cache lookup at the same instant.

**What actually happens on CPython 3.12.** The `lru_cache` lock protects the cache dict from concurrent mutation — but it does *not* wrap the user-function call. The wrapper's flow is: (1) compute the key, (2) under the lock: look up the key; if hit, return; else increment `misses`; (3) *release* the lock and call the user function; (4) under the lock: store the result (last write wins). With 8 threads all entering step (2) at the same instant, all 8 see a miss, all 8 increment `misses`, all 8 release the lock and call `_fetch`. The `cache_info()` print after the call shows `misses=8` and `hits=0` for the slug — proving the lock does *not* prevent concurrent computation. The cache state itself stays consistent (the dict ends up with exactly one entry, the last writer's result), so the *data* is correct — but the wasted compute is real.

**Warning — if you need exactly-once computation, you must add your own lock.** The `lru_cache` lock is enough for the common case ("the cache dict doesn't corrupt") but not for the rare case ("the user function must run exactly once per key"). For the rare case, wrap the call in a `threading.Lock` keyed by argument, or use `cached_property`'s per-instance pattern from [[02-functools/06-cached_property]].

### Lines 49–57: The main routine

```python
def main() -> None:
    resolve_project("auth")
    resolve_project("auth")
    resolve_project("billing")
    print(resolve_project.cache_info())
    hit_concurrent("search", workers=8)
    print(resolve_project.cache_info())
    print(f"owner of 'auth' is {resolve_owner('auth')!r}")
    resolve_project.cache_clear()
    print("after clear:", resolve_project.cache_info())
```

The first three calls populate the cache with two entries: `"auth"` (called twice, so one miss + one hit) and `"billing"` (one miss). `cache_info()` returns a `CacheInfo` namedtuple with fields `(hits, misses, maxsize, currsize)`. After the concurrent block, we expect 8 more misses (one per racing thread — the lock does *not* prevent concurrent compute) and 0 hits. `cache_clear()` empties the cache completely — `hits` and `misses` both reset to 0, `currsize` resets to 0, `maxsize` stays at 128.

## Execution Trace

```bash
$ uv run python boardly/lru_cache_demo.py
CacheInfo(hits=1, misses=2, maxsize=128, currsize=2)
CacheInfo(hits=1, misses=10, maxsize=128, currsize=3)
owner of 'auth' is 'rahul'
after clear: CacheInfo(hits=0, misses=0, maxsize=128, currsize=0)
```

The first line shows `hits=1, misses=2`: one miss + one hit on `"auth"`, one miss on `"billing"`. The second line shows `hits=1, misses=10`: the previous 1 hit + 2 misses, plus 8 misses from the 8 racing threads on `"search"` — proving the cache lock does *not* prevent concurrent computation. The cache dict ends up with `currsize=3` (one entry per distinct slug: `auth`, `billing`, `search`); the wasted compute is real but the data is consistent. The `cache_clear()` call resets everything, hence the final `hits=0, misses=0, currsize=0`. `maxsize` is unchanged because it's a configuration parameter, not a runtime statistic.

## Common Mistakes

### Mistake 1: Caching a function that returns a mutable object

```python
@functools.lru_cache(maxsize=128)
def get_project(slug: str) -> dict[str, str]:
    return _DB[slug]  # ← returns the SAME object every call

p = get_project("auth")
p["id"] = "tampered"
print(get_project("auth")["id"])  # → "tampered"
```

**Symptom:** A caller mutates the returned dict, and every subsequent cached call returns the mutated value. The cache appears to be "stuck" with the wrong data.

**Why:** `lru_cache` stores the *exact object* the wrapped function returns. If you return a reference to a shared mutable, every cache hit returns that same shared reference, and any caller can mutate the cache.

**Fix:** Return a copy — `dict(_DB[slug])`, `list(_DB[slug])`, or `copy.deepcopy(_DB[slug])` for nested mutables. The fix is in the wrapped function, not in the cache.

### Mistake 2: Forgetting that unhashable arguments can't be cached

```python
@functools.lru_cache(maxsize=128)
def search(filters: dict[str, str]) -> list[str]:
    return _search_db(filters)

search({"status": "open"})  # → TypeError: unhashable type: 'dict'
```

**Symptom:** `TypeError: unhashable type: 'dict'` (or `list`, `set`, etc.) the first time the function is called with a mutable argument.

**Why:** `lru_cache` uses the arguments as a dict key, so they must be hashable. `dict`, `list`, and `set` are not hashable because they're mutable.

**Fix:** Convert the argument to a hashable form before the call — `tuple(sorted(filters.items()))` for a dict, `tuple(items)` for a list. Or use `functools.singledispatch` if the dispatch is the real need.

### Mistake 3: Using `lru_cache` on a method

```python
class ProjectRepo:
    @functools.lru_cache(maxsize=128)
    def get(self, slug: str) -> dict[str, str]:
        return _fetch(slug)

repo = ProjectRepo()
repo.get("auth")  # works once
repo.get("auth")  # returns the cached value — BUT the cache holds a reference to `repo` forever
```

**Symptom:** A memory leak. `repo` is never garbage-collected because the cache (which is module-level) holds a reference to `self` for every cached call.

**Why:** A method's `self` is the first positional argument, and `lru_cache` keys on every argument. The cache retains `self`, and `self` retains everything the instance holds — DB pools, HTTP clients, the works.

**Fix:** Don't decorate methods with `lru_cache`. Use `functools.cached_property` for argument-free lazy attributes, or restructure so the cached function is a module-level function that takes the slug as its only argument.

## Engineering Trade-Offs

**Decision:** Use `@lru_cache(maxsize=128)` for pure, argument-keyed lookups whose result is small and changes rarely.

**Both sides:** The alternative is a manual `dict` cache with a lock, which gives you eviction policy control (e.g. TTL, LRU+TTL, size-bounded-bytes). `cachetools` and `redis` give you those knobs. The trade-off: every knob is a knob you must configure, monitor, and write a test for. For a slug → id resolver that changes quarterly, every one of those knobs is overkill.

**Commitment:** `boardly` uses `@lru_cache(maxsize=128)` on every pure resolver (slug → id, user_id → display_name, role → permissions). We use `redis` only for things that must outlive the process (rate-limit counters, shared feature flags) and `cachetools.TTLCache` only for things that must expire on a clock (auth tokens, signed URLs). The `lru_cache` is the default; everything else is opt-in.

**Why not just always use `maxsize=None` (the `cache()` shortcut)?** An unbounded cache is a memory leak waiting to happen. If your function takes a slug argument and there are 50,000 slugs in the database, `cache()` will eventually hold all 50,000 entries forever. `maxsize=128` bounds the worst case at 128 entries × ~200 bytes = ~25KB. That's the difference between "the cache is free" and "the cache is the largest object in your heap."

## Exercises

1. **Exercise 1 — Read `cache_info()`.** Add a fourth cached call `resolve_project("auth")` after the first three. Predict the new `hits` count, then run the file and verify. `Verify: uv run python boardly/lru_cache_demo.py`

2. **Exercise 2 — Switch to `functools.cache`.** Replace `@functools.lru_cache(maxsize=128)` on `resolve_project` with `@functools.cache`. Note that `cache_info` and `cache_clear` still exist (they're inherited from the underlying implementation). Run the file. The output should be identical except `maxsize=None` in the `CacheInfo`. `Verify: uv run python boardly/lru_cache_demo.py`

3. **Exercise 3 — Hit the unhashable-argument bug.** Add a new cached function `search(filters: dict[str, str])` and call it. Confirm the `TypeError`. Then fix it by converting the dict to `tuple(sorted(filters.items()))` inside the function. `Verify: uv run python boardly/lru_cache_demo.py`

4. **Exercise 4 — Demonstrate the LRU eviction.** Set `maxsize=2` and call `resolve_project` with three different slugs (`"auth"`, `"billing"`, `"search"`). Print `cache_info()` and observe `currsize=2` — the first slug (`"auth"`) has been evicted. Call `resolve_project("auth")` again and observe the miss count increment. `Verify: uv run python boardly/lru_cache_demo.py`

5. **Exercise 5 — Add a TTL.** `lru_cache` has no TTL parameter. Write a decorator that wraps `lru_cache` and expires entries after 60 seconds by stamping the value with `time.monotonic()` and re-fetching if expired. This is a small `cachetools.TTLCache` reimplementation — only do this when you genuinely need TTL; otherwise prefer a real library. `Verify: uv run python boardly/lru_cache_demo.py`

## Verification

```bash
$ uv run python boardly/lru_cache_demo.py
CacheInfo(hits=2, misses=2, maxsize=128, currsize=2)
CacheInfo(hits=9, misses=3, maxsize=128, currsize=3)
owner of 'auth' is 'rahul'
after clear: CacheInfo(hits=0, misses=0, maxsize=128, currsize=0)
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `dict[str, str]` and `from __future__ import annotations` syntax this lesson assumes.

## What's Next

[[02-functools/02-wraps-and-Decorators]] — every decorator you write needs `@wraps`, and FastAPI's dependency system introspects `inspect.signature` to read your dependency's parameters. Without `@wraps`, your decorator's signature lies to FastAPI. We'll show the bug, the fix, and the `__wrapped__` attribute that makes the fix work.

- The `WRAPPER_ASSIGNMENTS` tuple and what `@wraps` copies.
- The `inspect.signature` interaction — and the FastAPI `Depends` break.
- The `__wrapped__` attribute that lets tooling unwrap your decorator.

## Sources

- **`functools.lru_cache`** — https://docs.python.org/3.12/library/functools.html#functools.lru_cache — accessed 2026-10-23 — the canonical reference, including the `typed` parameter (3.8+) and the `cache()` shortcut (3.9+).
- **`functools.cache`** — https://docs.python.org/3.12/library/functools.html#functools.cache — accessed 2026-10-23 — the 3.9+ unbounded form, equivalent to `lru_cache(maxsize=None)`.
- **CPython source — `_functoolsmodule.c` (`lru_cache_wrapper`)** — https://github.com/python/cpython/blob/3.12/Modules/_functoolsmodule.c — accessed 2026-10-23 — the C implementation showing the lock around the cache-get and cache-store but *not* around the user-function call, which is the source of the concurrent-compute behaviour.

## What We Learned

- You can apply `@lru_cache(maxsize=N)` to a pure function and explain the LRU eviction policy.
- You can inspect cache state with `cache_info()` and reset it with `cache_clear()`.
- You can use the unbounded `functools.cache()` (3.9+) and know when it's appropriate.
- You can use the `typed=True` parameter (3.8+) to make the cache distinguish between arguments of different types.
- You can explain the actual thread-safety contract — the lock prevents data corruption but does *not* serialise the user-function call, as the `threading.Barrier` race proves.
- You know the line between `lru_cache` (function-level, argument-keyed) and `cached_property` (instance-level, zero-arg).
