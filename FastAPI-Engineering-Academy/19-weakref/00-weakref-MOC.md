---
title: "weakref — Section Map of Content"
aliases:
 - weakref MOC
 - 19-weakref MOC
tags:
 - weakref
 - moc
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "70–100 minutes across 3 lessons"
prerequisites:
 - "[[02-functools/01-lru_cache-and-Caching]]"
 - "[[02-functools/06-cached_property]]"
---

# weakref — Section Map of Content

*The standard-library module that lets a long-lived data structure reference an object without keeping it alive — `WeakValueDictionary` for per-id caches that auto-expire, `WeakSet` for subscriber lists that die with their owners, and `weakref.finalize` for the modern, reliable replacement for `__del__`.*

**You're at the very beginning of Section 19.**

`weakref` is the smallest module in this vault that has the largest design impact per line of code. You can build an entire request-scoped caching layer for `boardly` in three primitives — `WeakValueDictionary`, `WeakSet`, and `weakref.finalize` — and the result is a worker whose resident memory tracks its *concurrency*, not its *history*. The three lessons in this section walk each primitive in isolation and then commit the decision rule for when to use one versus the alternatives (`lru_cache`, `cached_property`, `__del__`). By the end you will know exactly which primitive to reach for and — more importantly — when *not* to reach for one, because the value is not weakreferenceable or the lifetime is wrong.

#weakref #moc

## Why this section exists

Every senior backend engineer eventually ships a long-running worker that holds a cache. The cache is the largest object in the worker's heap, and it grows monotonically with the number of *distinct items ever seen*. After a day of traffic, the cache holds 50,000 entries; 49,995 of them are not in active use. The worker has a memory leak in *principle* even though no individual line of code is buggy.

`weakref` is the standard-library answer to that leak. The four primitives — `WeakValueDictionary`, `WeakKeyDictionary`, `WeakSet`, and `weakref.finalize` — together cover the two axes of "I don't want to be the reason this object stays alive": *mapping* (per-id caches, per-object side tables) and *collection* (subscriber lists, plugin registries) and *cleanup* (return resource on GC). The decision rule that picks the right primitive for the right shape is the closer of this section — the single most useful sentence in the whole vault: weakrefs save memory when a long-lived mapping holds short-lived objects whose lifetime is owned by their callers. The rest is bookkeeping.

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[19-weakref/01-WeakValueDictionary]] | `WeakValueDictionary()` holds values by weak reference (entry disappears when the value is GC'd elsewhere), the three access paths (`.get()` → `None`, `in` → `False`, `[]` → `KeyError`), the per-id-cache use case, and the `WeakKeyDictionary` companion (keys held weakly for per-object side tables). |
| 02 | [[19-weakref/02-WeakSet-and-finalize]] | `WeakSet()` for "a collection of things I don't own" (subscriber lists, plugin registries), `weakref.finalize(obj, callback, *args, **kwargs)` as the modern `__del__` replacement (no resurrection, no GC-order issues, atexit-guaranteed cleanup), and the closure trap (closures that capture `obj` silently prevent collection). |
| 03 | [[19-weakref/03-When-weakrefs-save-memory]] | The decision rule — weakrefs win when a long-lived mapping holds short-lived objects, lose when the opposite; the CPython forbidden-types list (`int`/`str`/`tuple`/`list`/`dict`/`set` cannot be weakref'd); and the `@dataclass(slots=True, weakref_slot=True)` (3.12+) fix for slotted models. |

## Mindmap

```mermaid
mindmap
  root((weakref))
    WeakValueDictionary
      Values held weakly
      Entry dies with value
      .get returns None
      in returns False
      [] raises KeyError
      Read-with-fallback pattern
      ProjectCache use case
    WeakKeyDictionary
      Keys held weakly
      Entry dies with key
      Per-object side tables
      Requires hashable key
      frozen=True dataclass
    WeakSet
      Elements held weakly
      set API surface
      No insertion order
      Snapshot-iterate before loop
      Subscriber list use case
    finalize
      finalize(obj, func, args)
      atexit=True default
      .alive .atexit
      .detach .peek
      Replaces __del__
      No resurrection
      Pass data not obj
    Decision rule
      Long-lived mapping short-lived values
      Caller owns lifetime
      Pure resolver use lru_cache
      Instance-level use cached_property
    Forbidden types
      int str tuple list dict set
      No __weakref__ slot
      Subclass to opt in
    Slotted dataclass
      slots=True forbids weakref
      weakref_slot=True 3.12+
      Manual __slots__ fallback
```

## Reading order

Read the lessons in numbered order. Lesson 01 is the canonical lesson — every later lesson assumes you have seen the `WeakValueDictionary` API and the auto-removal semantics. Lesson 02 (`WeakSet`/`finalize`) is structurally parallel — `WeakSet` is the same auto-removal mechanism in a `set` shape, and `finalize` is the modern cleanup primitive that has nothing to do with caching but everything to do with the same "I don't want to be the reason this stays alive" principle. Lesson 03 is the closer — the decision rule that ties the primitives to `lru_cache` and `cached_property`, plus the forbidden-types and slotted-dataclass traps that you will hit the day after reading lessons 01–02.

If you only have time for one lesson, read 01 — it's the canonical. If you have time for two, read 01 and 03 — the API and the decision rule together cover 80% of what a `boardly` engineer uses. Lesson 02 is the cleanup half; read it when you're about to write a `__del__` method (don't) or a subscriber list (use `WeakSet`).

## Concepts first-taught in this section

These concepts have their canonical lesson in `19-weakref/`:

- **`weakref.WeakValueDictionary`** → [[19-weakref/01-WeakValueDictionary]] — the canonical lesson for the weak-value mapping.
- **`weakref.WeakKeyDictionary`** → [[19-weakref/01-WeakValueDictionary]] — the canonical lesson (covered alongside the value-dict in the same lesson because the API is parallel).
- **`weakref.WeakSet`** → [[19-weakref/02-WeakSet-and-finalize]] — the canonical lesson for the weak-element set.
- **`weakref.finalize`** → [[19-weakref/02-WeakSet-and-finalize]] — the canonical lesson for the modern `__del__` replacement.
- **When to use `weakref` vs `lru_cache` vs `cached_property`** → [[19-weakref/03-When-weakrefs-save-memory]] — the canonical decision lesson.

## Prerequisites

- **`@lru_cache`** — [[02-functools/01-lru_cache-and-Caching]]. The strong-reference cache that `WeakValueDictionary` is the weak alternative to. You need to have seen `lru_cache`'s retention contract (cache-owned lifetime) before this section's caller-owned lifetime lands.
- **`@cached_property`** — [[02-functools/06-cached_property]]. The instance-level strong-reference cache. The slotted-class `TypeError` in [[19-weakref/03-When-weakrefs-save-memory]] is the same trap as `cached_property` on slotted classes — the two parallels are clearer if you have seen the cached_property version first.
- **`@dataclass(slots=True)`** — [[06-dataclasses/04-Slots-and-Performance]]. The `weakref_slot=True` fix is the 3.12 knob that adds `__weakref__` to the generated `__slots__`; you need to know what `__slots__` is and why it forbids `__dict__`/`__weakref__` before the fix makes sense.

## Cross-links

- [[02-functools/01-lru_cache-and-Caching]] — the strong-reference analogue of `WeakValueDictionary`. Lesson 03's decision rule commits to print which to pick when.
- [[02-functools/06-cached_property]] — the instance-level strong-reference cache. The cached_property-slots trap is the precedent for the weakref-slots trap; the same fix shape (`__dict__` slot vs `__weakref__` slot) recurs.
- [[03-contextlib/01-contextmanager]] — `contextmanager` is the *deterministic* cleanup primitive; `weakref.finalize` is the *fallback* cleanup primitive. The two are complementary — `contextmanager` for the happy path, `finalize` for the leak path.
- [[06-dataclasses/04-Slots-and-Performance]] — the `__slots__` lesson; the `weakref_slot=True` fix lives in the same family.

## What you will be able to do by the end

- Construct a `WeakValueDictionary`-backed per-id cache and predict when each entry auto-expires.
- Use the three access paths (`.get()` / `in` / `[]`) correctly — soft lookup, membership test, hard lookup — and explain why each has a different failure signal.
- Pick between `WeakValueDictionary`, `@lru_cache`, and `@cached_property` based on the lifetime-ownership model of the workload.
- Build a `WeakSet`-backed event bus whose subscriber list never outlives the requests that subscribed.
- Replace every `__del__` method with `weakref.finalize`, and articulate why (no resurrection, no exception-swallowing, atexit-guaranteed cleanup).
- Diagnose the four `weakref` traps — temp-value `put`, `KeyError`-on-access, unhashable key, closure-that-captures-`obj` — without searching.

## What's next

When you finish this section, [[20-warnings/00-warnings-MOC]] is the natural next stop if you are continuing through the standard library. `warnings` is small and orthogonal — `weakref` is about *lifetime*, `warnings` is about *attention* — and the contrast makes both clearer. If you came here from a FastAPI dependency-cache question, return to [[02-functools/01-lru_cache-and-Caching]] and re-read the FastAPI `Depends` parallel — the dependency cache is an `lru_cache`-shaped idea (cache-owned lifetime) and the contrast with `WeakValueDictionary` (caller-owned lifetime) is the cleanest way to internalise the decision rule from Lesson 03.

**Welcome to `weakref`. We'll see you at the end.**

## Sources

- **`weakref` — Weak references** — https://docs.python.org/3/library/weakref.html — accessed 2026-10-23 — the canonical CPython reference for every API used in this section: `WeakValueDictionary`, `WeakKeyDictionary`, `WeakSet`, `finalize`, `ref`, `proxy`.
- **PEP 205 — Weak References** — https://peps.python.org/pep-0205/ — accessed 2026-10-23 — the original PEP that introduced `weakref`; the "Applications" section is the canonical list of use cases this section's decision rule distils.
