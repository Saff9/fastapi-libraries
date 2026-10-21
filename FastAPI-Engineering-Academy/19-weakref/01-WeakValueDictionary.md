---
title: "Lesson 01: WeakValueDictionary"
aliases:
 - WeakValueDictionary
 - WeakKeyDictionary
 - weakref dict
tags:
 - weakref
 - weakvaluedictionary
 - caching
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[02-functools/01-lru_cache-and-Caching]]"
related_lessons:
 - "[[02-functools/06-cached_property]]"
 - "[[19-weakref/02-WeakSet-and-finalize]]"
first_taught_in: "19-weakref/01-WeakValueDictionary"
---

# Lesson 01: `WeakValueDictionary`

*The standard-library dict that forgets its values the moment no one else remembers them — and the primitive behind every per-name cache in `boardly` that must not keep large objects alive forever.*

**You're at the very beginning of Section 19.**

`weakref.WeakValueDictionary()` looks like a `dict`. It walks like a `dict`. It even talks like a `dict` — `d["k"] = v`, `d.get("k")`, `len(d)`, `"k" in d`. The one thing it does not do is *keep its values alive*. The entries in a `WeakValueDictionary` are stored by weak reference; when the last strong reference to a value dies elsewhere in the program, the entry disappears from the dict as if you had called `del d["k"]` yourself. That single behavioural difference is what makes the type the right primitive for a per-`project_id` cache of recently-loaded `Project` objects — a cache that should never be the reason a 5 KB project stays in memory after the request that loaded it has returned. By the end of this lesson you will know exactly when `WeakValueDictionary` beats `lru_cache` (and when it doesn't), why `KeyError` is the *correct* failure mode after a value dies, and how its sibling `WeakKeyDictionary` turns the contract on its head. Take your time. Type every example. **This is how you learn.**

#weakref #weakvaluedictionary #caching #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `WeakValueDictionary`** and explain that the *values* (not the keys) are held by weak reference.
2. **Predict the auto-removal** behaviour — entry disappears when the last strong reference to the value goes out of scope, with no `del` on the dict itself.
3. **Distinguish the three access paths** on a dead entry — `d.get(k)` returns `None`, `k in d` returns `False`, and `d[k]` raises `KeyError`.
4. **Use `WeakKeyDictionary`** for the opposite contract (keys held weakly, values held strongly), and name the use case — a per-object side table that must not extend the object's lifetime.
5. **Choose between `WeakValueDictionary` and `@lru_cache`** for a per-argument cache, and articulate why the cache shape decides the answer.

## Prerequisites

Before starting, you need:

- **`@lru_cache` basics** — [[02-functools/01-lru_cache-and-Caching]]. The whole reason `WeakValueDictionary` exists is that `@lru_cache` retains its values forever; you must have seen that retention before this lesson's "weak alternative" lands.
- **`@cached_property`** — [[02-functools/06-cached_property]]. The instance-level lazy-cache pattern is the closest *strong-reference* analogue to what `WeakValueDictionary` does at the module level.
- **About 25–35 minutes of focused time.**

**The most common gap: thinking a `WeakValueDictionary` is just a memory-saving `lru_cache`.**

Students reach for `WeakValueDictionary` when they want "a cache that uses less memory". That's not what it does. `WeakValueDictionary` does not free memory that the rest of your program is still using — the entry only disappears once *no other code* holds a reference to the value. If your function that loaded the `Project` returned it to a caller that is still using it, the cache entry survives. The memory saving only shows up when the cache is the *last* holder of a value, which is the case for "per-name cache of recently-seen objects whose callers finish quickly". `lru_cache`, by contrast, evicts on a count regardless of who holds the value — that is a different contract.

## The Problem

You ship `boardly/projects/cache.py`. Every endpoint that touches a `Project` loads it from Postgres — an 80 ms `SELECT` plus a 200 ms JSON-unpack into a `Project` dataclass. One request can load the same `Project` twice (once for permission checks, once for the response body). Two requests in the same second can load the same `Project` four times. You want a cache.

`@lru_cache(maxsize=128)` on the loader is the obvious first reach — and it works. It pins the 128 most-recently-loaded `Project` objects in the cache forever (or until the LRU evicts them). Each `Project` is ~5 KB once its metadata dict is unpacked. 128 entries × 5 KB = 640 KB resident, all the time. That is *fine* for a small deployment, but it is wrong in principle: the cache, not the request that needed the data, is the reason the `Project` is still in memory. If you scale to 5000 distinct projects over a day, the cache holds 128 of them forever even though no current request is touching them.

`WeakValueDictionary` is the contractually-correct answer. You store the `Project` by `project_id` in the dict; the request that loaded it also holds a strong reference in a local variable. While the request is in flight, the dict returns that same instance. The moment the request returns and its local variable goes out of scope, *the only remaining reference to the `Project` is the weak one inside the dict*. CPython's garbage collector reaps the `Project`; the dict's entry disappears as a side-effect. The cache cost is bounded by "projects currently in-flight", not "projects recently seen", which is the right shape for a request-scoped cache.

## The Code

```python
# boardly/weakref_cache_demo.py
"""boardly ProjectCache — a WeakValueDictionary of recently-loaded projects."""
from __future__ import annotations

import gc
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    owner: str


class ProjectCache:
    """Per-id cache of recently-loaded Project objects.

    The cache does NOT keep projects alive — when the last strong
    reference to a Project goes out of scope, the cache entry
    disappears with it.
    """

    def __init__(self) -> None:
        self._by_id: weakref.WeakValueDictionary[str, Project] = (
            weakref.WeakValueDictionary()
        )

    def put(self, project: Project) -> None:
        self._by_id[project.id] = project

    def get(self, project_id: str) -> Project | None:
        # WeakValueDictionary.get() returns None if the entry has been
        # auto-removed; [] raises KeyError. We use .get() for the soft
        # lookup that a cache needs.
        return self._by_id.get(project_id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, project_id: str) -> bool:
        return project_id in self._by_id


class ProjectSideTable:
    """Per-Project metadata, keyed by the Project itself (weakly).

    The key is held weakly: when the Project dies, the side-table
    entry disappears with it. The side table never keeps a Project
    alive.
    """

    def __init__(self) -> None:
        self._meta: weakref.WeakKeyDictionary[Project, dict[str, str]] = (
            weakref.WeakKeyDictionary()
        )

    def set(self, project: Project, meta: dict[str, str]) -> None:
        self._meta[project] = meta

    def get(self, project: Project) -> dict[str, str] | None:
        return self._meta.get(project)


def main() -> None:
    cache = ProjectCache()
    side = ProjectSideTable()

    p = Project(id="p_001", name="Auth Rewrite", owner="rahul")
    cache.put(p)
    side.set(p, {"last_seen": "2026-10-23", "open_tickets": 3})

    print(f"cache has p_001: {'p_001' in cache}")
    print(f"cache len: {len(cache)}")
    print(f"cache.get('p_001') -> {cache.get('p_001')!r}")

    # Drop the only strong reference. The cache entry vanishes with it.
    del p
    gc.collect()
    print()
    print("after del p + gc.collect():")
    print(f"  cache has p_001: {'p_001' in cache}")
    print(f"  cache len: {len(cache)}")
    print(f"  cache.get('p_001') -> {cache.get('p_001')!r}")

    # KeyError on direct access — entry has been removed.
    try:
        _ = cache._by_id["p_001"]
    except KeyError as exc:
        print(f"  cache._by_id['p_001'] raised KeyError: {exc!r}")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the `Project` model

```python
# boardly/weakref_cache_demo.py
"""boardly ProjectCache — a WeakValueDictionary of recently-loaded projects."""
from __future__ import annotations

import gc
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    owner: str
```

`weakref` is the star. `gc` is imported for one reason: when we `del p` later, we want to force garbage collection immediately so the cache's auto-removal is observable in the same `print()` block. In a production worker you don't call `gc.collect()` — CPython's reference-counting collector reaps the `Project` the instant the refcount hits zero, which is usually the moment the request returns; `gc.collect()` here just makes the demo deterministic.

`Project` is `@dataclass(frozen=True)` for one reason specific to this lesson: `WeakKeyDictionary` requires its *keys* to be hashable, and the default `@dataclass` (with `eq=True`) sets `__hash__ = None`. `frozen=True` restores `__hash__` as `hash((id, name, owner))`. The `WeakValueDictionary` does not need `Project` to be hashable — its keys are plain strings — but we use one `Project` class for both halves of the lesson, so we make it hashable up front.

**Why `frozen=True` and not just `eq=False`?** `eq=False` would also restore `__hash__` (it would inherit `object.__hash__`, the identity hash), but identity hashing breaks the side-table semantics — two `Project(id="p_001", ...)` instances constructed at different times would have different hashes and land in different buckets. `frozen=True` gives us *value* hashing, which is what the side table actually wants.

### Lines 12–24: `ProjectCache` — the `WeakValueDictionary`

```python
class ProjectCache:
    """Per-id cache of recently-loaded Project objects.

    The cache does NOT keep projects alive — when the last strong
    reference to a Project goes out of scope, the cache entry
    disappears with it.
    """

    def __init__(self) -> None:
        self._by_id: weakref.WeakValueDictionary[str, Project] = (
            weakref.WeakValueDictionary()
        )

    def put(self, project: Project) -> None:
        self._by_id[project.id] = project
```

`weakref.WeakValueDictionary()` constructs the dict. The type parameters `[str, Project]` are the 3.9+ generic-syntax form — they are *static* hints for the type checker, not enforced at runtime. Internally the type stores entries as `{key: weakref.ref(value)}`; when you do `self._by_id[project.id] = project`, the dict calls `weakref.ref(project)` and stores the *ref* in the underlying `dict`, not the `Project` itself. The `Project`'s refcount therefore does *not* go up — the dict holds zero strong references to it.

The mechanism that auto-removes the entry is a callback. When the dict stores `weakref.ref(value)`, it actually stores `weakref.ref(value, self._remove)` — a callback that fires when the referent dies. The callback receives the dead `weakref.ref` object, looks it up in a reverse map (`ref -> key`), and `del`s the entry from the underlying `dict`. This is why `WeakValueDictionary.__setitem__` is slower than `dict.__setitem__` — it has to register the callback and update the reverse map. The slowdown is small (a few hundred nanoseconds per insert) and is the price of automatic eviction.

**Why not just hold a `dict[str, weakref.ref[Project]]` and call `ref()` on every access?** You *could* — that is essentially what `WeakValueDictionary` is, except it adds the callback-driven auto-removal. Without the callback, dead entries would accumulate forever in the dict (the `weakref.ref` objects themselves don't die — they hold zero references to the referent and just return `None` when called). The auto-removal is what keeps the dict bounded by live values, not by "values ever inserted". The stdlib class exists because the callback bookkeeping is fiddly and easy to get wrong.

### Lines 26–33: The lookup paths

```python
    def get(self, project_id: str) -> Project | None:
        # WeakValueDictionary.get() returns None if the entry has been
        # auto-removed; [] raises KeyError. We use .get() for the soft
        # lookup that a cache needs.
        return self._by_id.get(project_id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, project_id: str) -> bool:
        return project_id in self._by_id
```

Three access paths, three behaviours. `cache.get(project_id)` is the soft lookup — returns `None` if the entry is gone. `"p_001" in cache` is the membership test — returns `False`. `cache._by_id["p_001"]` (direct access) is the hard lookup — raises `KeyError('p_001')`. The three paths agree on the *fact* ("the entry is gone") but disagree on the *signal* (`None`, `False`, or `KeyError`). The soft `.get()` is the right shape for a cache: callers want "give me the value if you have it, otherwise let me know there isn't one" without a `try`/`except`. The hard `[]` is the right shape for "I assert this entry exists; if it doesn't, that's a bug".

**Why `__contains__` returns `False` instead of raising `KeyError`?** Because `__contains__` is a predicate — it answers yes/no questions, not assertions. The same is true of `dict.__contains__`: `"missing" in d` returns `False`, it does not raise. `WeakValueDictionary` mirrors this contract exactly. The `KeyError` is reserved for the `__getitem__` path, where the caller is making a demand, not asking a question.

### Lines 36–50: `ProjectSideTable` — the `WeakKeyDictionary`

```python
class ProjectSideTable:
    """Per-Project metadata, keyed by the Project itself (weakly).

    The key is held weakly: when the Project dies, the side-table
    entry disappears with it. The side table never keeps a Project
    alive.
    """

    def __init__(self) -> None:
        self._meta: weakref.WeakKeyDictionary[Project, dict[str, str]] = (
            weakref.WeakKeyDictionary()
        )

    def set(self, project: Project, meta: dict[str, str]) -> None:
        self._meta[project] = meta

    def get(self, project: Project) -> dict[str, str] | None:
        return self._meta.get(project)
```

`weakref.WeakKeyDictionary()` flips the contract: the *keys* are held weakly, the *values* strongly. When the `Project` dies, the entry (the `{project: meta}` pair) disappears. The side table never keeps a `Project` alive — which is exactly what you want for a side table, because the whole point of a side table is "extra data attached to an object whose lifetime is owned elsewhere".

The mechanism is the same as `WeakValueDictionary` — callbacks on `weakref.ref` objects — but the bookkeeping is reversed: the underlying `dict` is `{weakref.ref(key): value}`, and the callback removes the `(ref, value)` pair when the referent of `ref` dies. The type parameters `[Project, dict[str, str]]` are the 3.9+ generic form.

**Why a `WeakKeyDictionary` and not `Project.__dict__`?** Because the side data is *not part of the model* — it's transient per-request metadata (`last_seen`, `open_tickets` count) that you don't want on the dataclass itself. Adding fields to `Project` to hold this state would force every `Project` to carry the side data, even when it's not relevant; the side table lets you attach the data only to projects that need it, and only for as long as they live. This is the same shape as `cached_property` (see [[02-functools/06-cached_property]]) but for *cross-cutting* state rather than per-instance lazy state.

### Lines 53–70: The demo

```python
def main() -> None:
    cache = ProjectCache()
    side = ProjectSideTable()

    p = Project(id="p_001", name="Auth Rewrite", owner="rahul")
    cache.put(p)
    side.set(p, {"last_seen": "2026-10-23", "open_tickets": 3})

    print(f"cache has p_001: {'p_001' in cache}")
    print(f"cache len: {len(cache)}")
    print(f"cache.get('p_001') -> {cache.get('p_001')!r}")

    # Drop the only strong reference. The cache entry vanishes with it.
    del p
    gc.collect()
    print()
    print("after del p + gc.collect():")
    print(f"  cache has p_001: {'p_001' in cache}")
    print(f"  cache len: {len(cache)}")
    print(f"  cache.get('p_001') -> {cache.get('p_001')!r}")

    # KeyError on direct access — entry has been removed.
    try:
        _ = cache._by_id["p_001"]
    except KeyError as exc:
        print(f"  cache._by_id['p_001'] raised KeyError: {exc!r}")
```

The local variable `p` is the *only* strong reference to the `Project`. `cache.put(p)` stored a `weakref.ref` to it inside `self._by_id`, and `side.set(p, ...)` stored a `weakref.ref` to it inside `self._meta`. The refcount of the `Project` is exactly 1 (the local `p`).

The first three `print`s confirm the cache sees the entry: `'p_001' in cache` is `True`, `len(cache)` is `1`, `cache.get('p_001')` returns the `Project` instance.

`del p` drops the refcount from 1 to 0. CPython's reference-counting collector immediately reaps the `Project` — *before* `del p` even returns, in fact. The reap fires the weakref callbacks registered by the `WeakValueDictionary` and `WeakKeyDictionary`; each callback removes its entry from its underlying dict. `gc.collect()` is technically redundant here (refcount-driven collection already happened) but it documents the intent and protects against implementations where the callback runs on the GC pass instead of the refcount hit.

The second three `print`s confirm the cache no longer sees the entry: `'p_001' in cache` is `False`, `len(cache)` is `0`, `cache.get('p_001')` returns `None`. The `try`/`except` shows that direct access raises `KeyError('p_001')` — the same exception `dict["missing"]` would raise.

**Why does the entry disappear rather than return `None` from `[]`?** Because the auto-removal callback ran when the value died. If the entry stayed in the dict, every subsequent `cache["p_001"]` would either return `None` (which would silently break `for p in cache.values():` iteration) or raise some new "weakref-dead" exception. The stdlib designers chose the cleanest contract: the entry is gone, so the dict behaves exactly like a `dict` after `del d[k]` — `[]` raises `KeyError`, `.get()` returns `None`, `in` returns `False`. The student who knows `dict` semantics already knows `WeakValueDictionary`'s semantics for dead entries.

## Execution Trace

```bash
$ uv run python boardly/weakref_cache_demo.py
cache has p_001: True
cache len: 1
cache.get('p_001') -> Project(id='p_001', name='Auth Rewrite', owner='rahul')

after del p + gc.collect():
  cache has p_001: False
  cache len: 0
  cache.get('p_001') -> None
  cache._by_id['p_001'] raised KeyError: KeyError('p_001')
```

The first three lines confirm the cache holds the entry while `p` is alive. The second block confirms the entry has vanished after `del p` plus `gc.collect()`. The `KeyError` is the same exception `dict["missing"]` raises — `WeakValueDictionary` is *behaving like a dict whose entry has been deleted*, not like a dict whose value went stale.

## Common Mistakes

### Mistake 1: Storing a value the cache never holds weakly

```python
import weakref

class Project: ...

cache = weakref.WeakValueDictionary()
cache["p_001"] = Project(id="p_001")  # ← no strong reference kept
print("p_001" in cache)  # False — entry already gone
```

**Symptom:** `len(cache) == 0` immediately after the `put`, even though no one has explicitly removed the entry.

**Why:** The right-hand side of `cache["p_001"] = Project(...)` constructs a temporary `Project`. The assignment stores a `weakref.ref` to it. After the assignment statement finishes, the temporary's refcount drops to zero (no local variable holds it). The `Project` is reaped on the spot, the weakref callback fires, and the entry is removed. The cache never held the value long enough to be useful.

**Fix:** Hold a strong reference somewhere — typically in a local variable in the calling function, or in a caller-owned registry. The cache's job is to share existing instances, not to be the sole owner. If you genuinely need the cache to own the lifetime, use a plain `dict` or `lru_cache`, not `WeakValueDictionary`.

### Mistake 2: Treating `cache[key]` as a safe lookup

```python
def get_project(project_id: str) -> Project:
    return cache[project_id]  # ← KeyError the moment the value dies
```

**Symptom:** Intermittent `KeyError` in production for keys you "just put in".

**Why:** `WeakValueDictionary.__getitem__` raises `KeyError` whenever the entry is gone — and the entry can be gone *between two consecutive statements* if the value's last strong reference died in the first statement. A `WeakValueDictionary` is not a `dict` whose entries live until you delete them; it's a `dict` whose entries live until the value's last strong reference dies, which can be any time.

**Fix:** Use `.get()` for the soft lookup and re-load on `None`:

```python
def get_project(project_id: str) -> Project:
    cached = cache.get(project_id)
    if cached is not None:
        return cached
    fresh = load_from_db(project_id)
    cache[project_id] = fresh
    return fresh
```

This is the canonical `WeakValueDictionary` access pattern: read-with-fallback. The fallback reloads the value and re-inserts it; while the caller holds the returned `fresh`, the entry stays alive.

### Mistake 3: Putting an unhashable value into a `WeakKeyDictionary`

```python
from dataclasses import dataclass

@dataclass              # ← eq=True default → __hash__ = None
class Project:
    id: str

side = weakref.WeakKeyDictionary()
side[Project(id="p_001")] = {}  # TypeError: unhashable type: 'Project'
```

**Symptom:** `TypeError: unhashable type: 'Project'` on the first insert into a `WeakKeyDictionary`.

**Why:** `WeakKeyDictionary` uses the *key* as the underlying `dict`'s key (wrapped in a `weakref.ref`), so the key must be hashable. The default `@dataclass` (with `eq=True`) sets `__hash__ = None`, making instances unhashable. The same problem affects `set` and `frozenset` membership.

**Fix:** Make the model hashable — `@dataclass(frozen=True)` (the recommended form) restores `__hash__` as a value-hash over the fields. Alternatively, `@dataclass(eq=False)` inherits `object.__hash__` (identity-hash), which works but means two `Project(id="p_001")` instances are different keys — usually wrong for a side table.

## Engineering Trade-Offs

**Decision:** Use `WeakValueDictionary` for per-key caches of short-lived objects whose lifetime is owned by their callers, and `WeakKeyDictionary` for per-object side tables that must not extend the object's lifetime.

**Both sides:** The alternative is `@lru_cache(maxsize=N)`, which retains N entries on a count basis. `lru_cache` wins when the values are immutable, the function is pure, and you can predict the working set size; the cache will hold N entries forever, but N is bounded. `WeakValueDictionary` wins when the values are mutable, the loader has side effects (database read), or the working set size is unpredictable — the cache holds "currently live" entries, which scales with concurrency, not with history.

**Commitment:** `boardly` uses `WeakValueDictionary` for `ProjectCache`, `UserCache`, and `TicketCache` — three per-id caches of recently-loaded domain objects. The caches are populated by the request loaders, and the entries disappear when the request returns. `@lru_cache` is reserved for the *pure* resolvers (slug → id, role → permission list) where the value is small and immutable; the LRU's bounded retention is the right shape for those.

**Why not just `WeakValueDictionary` everywhere?** Because the auto-removal makes the cache *unusable* for memoising pure functions. Consider a slug → id resolver: the value (`"p_001"`) is a short string with no strong reference held anywhere after the resolver returns — so a `WeakValueDictionary` cache would evict every entry the moment it was inserted. `lru_cache` keeps the entry by holding a strong reference inside the wrapper, which is the behaviour the resolver needs. The two primitives are not interchangeable; they solve different retention problems.

## Exercises

1. **Exercise 1 — Verify the auto-removal.** Add a `print(f"cache len before del: {len(cache)}")` line just before `del p`. Run the file and confirm the cache holds 1 entry before `del` and 0 after. `Verify: uv run python boardly/weakref_cache_demo.py`

2. **Exercise 2 — Reproduce Mistake 1.** Add `cache["p_extra"] = Project(id="p_extra", name="Extra", owner="x")` to `main()`. Print `len(cache)` immediately after. Confirm it's still 1 — the temporary `Project` was reaped before the entry could be useful. `Verify: uv run python boardly/weakref_cache_demo.py`

3. **Exercise 3 — Hold a strong reference.** Add `projects = [Project(id=f"p_{i:03d}", name=f"P{i}", owner="x") for i in range(5)]` and insert all five into the cache. Print `len(cache)` — it should be 5. Then `del projects` and `gc.collect()`; `len(cache)` should be 0. `Verify: uv run python boardly/weakref_cache_demo.py`

4. **Exercise 4 — Add a `WeakKeyDictionary` access pattern.** Extend `ProjectSideTable` with a `__len__` and `__contains__`. Confirm the side table also auto-removes when `p` dies, the same way the value-dict did. `Verify: uv run python boardly/weakref_cache_demo.py`

5. **Exercise 5 — Compare with `lru_cache`.** Add an `@lru_cache(maxsize=128)`-decorated `load_project(project_id: str) -> Project` that returns `Project(id=project_id, name=project_id.title(), owner="x")`. Call it 10 times across 5 distinct ids. Print `cache_info()` and note `currsize=5` — the entries are pinned forever (or until LRU evicts), regardless of caller references. `Verify: uv run python boardly/weakref_cache_demo.py`

## Verification

```bash
$ uv run python boardly/weakref_cache_demo.py
cache has p_001: True
cache len: 1
cache.get('p_001') -> Project(id='p_001', name='Auth Rewrite', owner='rahul')

after del p + gc.collect():
  cache has p_001: False
  cache len: 0
  cache.get('p_001') -> None
  cache._by_id['p_001'] raised KeyError: KeyError('p_001')
```

## Previously Learned Here

- [[02-functools/01-lru_cache-and-Caching]] — `@lru_cache` is the strong-reference analogue of `WeakValueDictionary`. The two are constantly compared; this lesson is the "weak" sibling.
- [[02-functools/06-cached_property]] — `cached_property` is the *instance-level* strong-reference cache. `WeakValueDictionary` is the *module-level* weak-reference cache. The two are siblings with different scopes.

## What's Next

[[19-weakref/02-WeakSet-and-finalize]] — the other half of `weakref`: `WeakSet` (a set of weak references — the right shape for an event-bus subscriber list that should not keep subscribers alive) and `weakref.finalize` (the modern replacement for `__del__` — register a callback to run when an object is GC'd, with none of `__del__`'s resurrection or interpreter-shutdown traps). Three things to take with you:

- `WeakValueDictionary` holds values weakly; `WeakKeyDictionary` holds keys weakly — pick the one whose *lifetime you want to follow*.
- `cache.get(k)` is the soft lookup; `cache[k]` is the hard lookup; choose based on whether a missing entry is a bug or a reload trigger.
- The cache auto-removes the entry on the value's death — `KeyError` after death is the *correct* behaviour, not a bug.

## Sources

- **`weakref` — Weak references** — https://docs.python.org/3/library/weakref.html — accessed 2026-10-23 — the canonical CPython reference, including the `WeakValueDictionary` and `WeakKeyDictionary` semantics, the callback mechanism, and the `KeyError`-on-access contract.
- **PEP 205 — Weak References** — https://peps.python.org/pep-0205/ — accessed 2026-10-23 — the original PEP that introduced `weakref`; the "Applications" section is still the clearest list of the use cases this lesson teaches.
- **CPython `weakref.py` source** — https://github.com/python/cpython/blob/3.12/Lib/weakref.py — accessed 2026-10-23 — the `_remove` callback in `WeakValueDictionary` is the single best-documented example of weakref-callback-driven auto-removal in the stdlib.

## What We Learned

- You can construct a `WeakValueDictionary` and explain that *values* (not keys) are held by weak reference.
- You can predict the auto-removal behaviour — the entry disappears when the value's last strong reference dies, with no `del` on the dict.
- You can distinguish the three access paths — `.get()` returns `None`, `in` returns `False`, `[]` raises `KeyError` — and choose the right one for the lookup you mean.
- You can use `WeakKeyDictionary` for the opposite contract and name its use case — per-object side tables that must not extend the object's lifetime.
- You can choose between `WeakValueDictionary` (caller-owned lifetime) and `@lru_cache` (cache-owned lifetime) based on whether the value is mutable, side-effecting, or pure.
