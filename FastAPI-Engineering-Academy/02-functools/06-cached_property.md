---
title: "Lesson 06: cached_property"
aliases:
 - functools.cached_property
 - cached_property
tags:
 - functools
 - cached_property
 - caching
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[02-functools/01-lru_cache-and-Caching]]"
related_lessons:
 - "[[02-functools/05-reduce]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
first_taught_in: "02-functools/06-cached_property"
---

# Lesson 06: `cached_property`

*The instance-level sibling of `lru_cache` — cache one expensive computation per object, in one line, with no bookkeeping.*

**You're at the very beginning of Section 02.**

`functools.cached_property` is the decorator you reach for when you have an expensive computation that lives on an instance and depends only on instance state. It is not the same as `@property` (which recomputes every access) and not the same as `@lru_cache` (which keys on the argument tuple, not the instance). It is a third tool, with its own contract, its own gotchas, and its own failure mode on slotted classes. By the end of this lesson you will know the line between `cached_property` and `lru_cache`, why `cached_property` on a slotted class raises `TypeError`, and — the surprise of the lesson — that the 3.12 implementation has *no* threading lock, contrary to what every blog post written before 3.12 says. Take your time. Type every example. **This is how you learn.**

#functools #cached_property #caching

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@functools.cached_property`** to a zero-argument method on a class, and explain the per-instance caching.
2. **Explain the 3.12 implementation** — no threading lock, the GIL provides atomicity for the dict store, the race condition is bounded.
3. **State the difference between `cached_property` and `lru_cache`** — instance-keyed vs argument-keyed.
4. **Demonstrate the slotted-class `TypeError`** — `cached_property` stores in `instance.__dict__`, and a slotted class has no `__dict__`.
5. **Choose between `cached_property`, `@property`, and `lru_cache`** — the three cache shapes for instance-level work.

## Prerequisites

Before starting, you need:

- **`@property`** — the basic descriptor that turns a method into a "computed attribute." `@cached_property` extends it.
- **`__slots__`** — what they are, what they save (no per-instance `__dict__`), and the constraints they impose.
- **About 25–35 minutes of focused time.**

**The most common gap: confusing `cached_property` with `lru_cache`.**

Students reach for `lru_cache` on a method, get a memory leak (the cache holds `self` forever), and then hear about `cached_property` but use it on a function that takes arguments — which doesn't work because `cached_property` only decorates zero-argument methods. The line: `cached_property` is for zero-argument instance methods; `lru_cache` is for argument-keyed functions.

## The Problem

You ship `boardly/projects/models.py` with a `Project` class. Each `Project` has an `id`, a `name`, and an expensive `metadata` field that joins three database tables and takes ~80ms to compute. You decorate `metadata` with `@property` so callers write `project.metadata` (not `project.metadata()`), but `@property` recomputes on every access — calling it twice in the same request burns 160ms. You need a cache, but the cache must be *per instance* (different projects have different metadata) and *lazy* (only computed when first read, not at `__init__`).

`@functools.cached_property` is the answer. It's a descriptor that, on first access, computes the value and stores it in `instance.__dict__[name]`. Subsequent accesses hit the instance dict directly, bypassing the descriptor entirely (because instance `__dict__` shadows non-data descriptors). The cache is per-instance, lazy, and free — three lines of code (the decorator plus the function body).

## The Code

```python
# boardly/cached_property_demo.py
"""Demonstrate functools.cached_property — per-instance lazy cache."""
from __future__ import annotations

import functools
import threading
import time


class Project:
    """A boardly project with a lazily-computed expensive field."""
    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        """Lazily fetched; cached on the instance after first access."""
        print(f"  computing metadata for {self.id}...")
        time.sleep(0.05)  # simulated DB round-trip
        return {"id": self.id, "name": self.id.title(), "owner": "rahul"}


# --- Slotted class: cached_property BREAKS here ---
class SlottedProject:
    __slots__ = ("id",)  # NO __dict__ — cached_property cannot store the result

    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        return {"id": self.id}


class CountedProject:
    """Demonstrates the 3.12 race: no lock means N threads compute N times."""
    counter = 0  # class-level counter

    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        CountedProject.counter += 1
        time.sleep(0.05)
        return {"id": self.id, "computed_by": threading.current_thread().name}


def thread_race_demo() -> None:
    """3.12 cached_property has NO lock — N racing threads compute N times."""
    CountedProject.counter = 0
    p = CountedProject("auth")
    barrier = threading.Barrier(3)

    def worker() -> None:
        barrier.wait()
        _ = p.metadata

    threads = [threading.Thread(target=worker, name=f"T{i}") for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  function called {CountedProject.counter} times by 3 racing threads")
    print(f"  cached value: {p.metadata}")


def lru_cache_vs_cached_property() -> None:
    """lru_cache keys on args; cached_property keys on the instance."""

    @functools.lru_cache(maxsize=128)
    def fetch(slug: str) -> str:
        print(f"  lru_cache miss for {slug}")
        return slug.upper()

    print("  lru_cache (keyed on the slug argument):")
    fetch("auth")
    fetch("auth")  # cached hit
    fetch("billing")  # miss

    print("  cached_property (keyed on the instance):")
    p1 = Project("auth")
    _ = p1.metadata  # miss
    _ = p1.metadata  # cached hit, second access
    p2 = Project("auth")  # different instance — different cache entry
    _ = p2.metadata  # miss


def main() -> None:
    print("=== cached_property basic ===")
    p = Project("auth")
    print(f"first access:   {p.metadata}")
    print(f"second access:  {p.metadata}")  # no recompute

    print()
    print("=== 3.12 thread race (no lock in 3.12) ===")
    thread_race_demo()

    print()
    print("=== lru_cache vs cached_property ===")
    lru_cache_vs_cached_property()

    print()
    print("=== the slotted-class bug ===")
    try:
        sp = SlottedProject("auth")
        _ = sp.metadata
    except TypeError as e:
        print(f"  TypeError: {e}")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports

```python
# boardly/cached_property_demo.py
"""Demonstrate functools.cached_property — per-instance lazy cache."""
from __future__ import annotations

import functools
import threading
import time
```

`functools.cached_property` is the star. `threading` is for the race-condition demo. `time` is for the simulated database latency. No `typing` imports needed — annotations are made lazy by `from __future__ import annotations`.

### Lines 11–19: The basic `cached_property`

```python
class Project:
    """A boardly project with a lazily-computed expensive field."""
    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        """Lazily fetched; cached on the instance after first access."""
        print(f"  computing metadata for {self.id}...")
        time.sleep(0.05)  # simulated DB round-trip
        return {"id": self.id, "name": self.id.title(), "owner": "rahul"}
```

`@functools.cached_property` wraps `metadata` into a non-data descriptor (it only defines `__get__`, not `__set__` or `__delete__`). On first access via `p.metadata`, the descriptor's `__get__` is invoked: it computes `self.func(p)` (which runs the body), stores the result in `p.__dict__["metadata"]`, and returns it. On *subsequent* access via `p.metadata`, Python's attribute lookup finds `"metadata"` in `p.__dict__` *first* (instance dict shadows non-data descriptors), and returns that — the descriptor's `__get__` is never called again. The result: the function body runs exactly once per instance.

**Why does the instance dict shadow the descriptor?** Because `cached_property` is a *non-data descriptor* (defines only `__get__`). Python's attribute lookup order is: data descriptor on the class → instance `__dict__` → non-data descriptor on the class → class `__dict__`. Since `cached_property` is non-data, the instance `__dict__` (populated on first access) wins on every subsequent access. This is the trick that makes `cached_property` essentially free after the first call — there's no descriptor invocation overhead.

### Lines 22–29: The slotted-class trap

```python
# --- Slotted class: cached_property BREAKS here ---
class SlottedProject:
    __slots__ = ("id",)  # NO __dict__ — cached_property cannot store the result

    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        return {"id": self.id}
```

`SlottedProject` declares `__slots__ = ("id",)`. This means instances of `SlottedProject` have no `__dict__` — they have only the named slot `id`. The memory saving is real (a few hundred bytes per instance), but the constraint is real too: you can't set arbitrary attributes, and `cached_property` has nowhere to store its result. The decoration itself doesn't fail (the decorator doesn't check for `__dict__`); the failure happens at first access, when `cached_property.__get__` tries `instance.__dict__` and raises `AttributeError`, which the descriptor catches and re-raises as `TypeError`.

The error message, in Python 3.12, is exactly:

```
TypeError: No '__dict__' attribute on 'SlottedProject' instance to cache 'metadata' property.
```

The fix is one of:

1. **Add `"__dict__"` to `__slots__`** — `__slots__ = ("id", "__dict__")`. Restores `__dict__` access, but loses some of the memory saving.
2. **Don't use `cached_property`** — write a manual cache in a slot. `self._metadata_cache = None` in `__init__`, then check in the method.
3. **Use `lru_cache`** — but only if you accept the `self`-in-cache memory leak.

### Lines 32–43: The race-condition demonstrator

```python
class CountedProject:
    """Demonstrates the 3.12 race: no lock means N threads compute N times."""
    counter = 0  # class-level counter

    def __init__(self, project_id: str) -> None:
        self.id = project_id

    @functools.cached_property
    def metadata(self) -> dict[str, str]:
        CountedProject.counter += 1
        time.sleep(0.05)
        return {"id": self.id, "computed_by": threading.current_thread().name}
```

`CountedProject` exists to demonstrate the 3.12 race. The class-level `counter` is incremented every time the function body runs. If three threads all access `p.metadata` simultaneously (using a `Barrier` to start them in lock-step), the counter tells us how many times the body ran.

The expected output is `function called 3 times by 3 racing threads` — three threads, three computations. This is the 3.12 behaviour: `cached_property` has no internal lock, so multiple threads can each see a cache miss and each run the function body. Only one's result gets stored in `__dict__["metadata"]`; the other two computations are wasted, but they're not a correctness bug — the cached value is one of the computed values, which is fine for idempotent computations.

**Why no lock in 3.12?** The Python 3.12 release removed the `RLock` that 3.8-3.11 had on `cached_property`. The reasoning: the GIL already makes the `instance.__dict__[name] = val` store atomic (single bytecode op), so the only race is "compute N times" — which is wasteful but not incorrect for idempotent computations. The lock was a perf cost (RLock acquisition per access path) that was deemed not worth the safety on free-threaded builds. For genuinely expensive idempotent computations, the fix is `@lru_cache` (which has its own lock) or a manual `RLock`-protected cache.

### Lines 46–60: The race demo

```python
def thread_race_demo() -> None:
    """3.12 cached_property has NO lock — N racing threads compute N times."""
    CountedProject.counter = 0
    p = CountedProject("auth")
    barrier = threading.Barrier(3)

    def worker() -> None:
        barrier.wait()
        _ = p.metadata

    threads = [threading.Thread(target=worker, name=f"T{i}") for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  function called {CountedProject.counter} times by 3 racing threads")
    print(f"  cached value: {p.metadata}")
```

A `threading.Barrier(3)` synchronises three threads at the same instant. Each thread calls `p.metadata`. Without a lock, all three see a cache miss, all three call the function body, and `CountedProject.counter` ends at 3. The cached value (`p.metadata` after all three threads finish) is whatever the *last* thread to store wrote — usually one of the three's return value.

This is *not* a correctness bug for idempotent computations (the cached value is one of the valid computed values), but it is a *wasted-work* bug for expensive ones. If the computation is a 1-second database call, three racing threads burn 3 seconds instead of 1.

### Lines 63–82: `lru_cache` vs `cached_property`

```python
def lru_cache_vs_cached_property() -> None:
    """lru_cache keys on args; cached_property keys on the instance."""

    @functools.lru_cache(maxsize=128)
    def fetch(slug: str) -> str:
        print(f"  lru_cache miss for {slug}")
        return slug.upper()

    print("  lru_cache (keyed on the slug argument):")
    fetch("auth")
    fetch("auth")  # cached hit
    fetch("billing")  # miss

    print("  cached_property (keyed on the instance):")
    p1 = Project("auth")
    _ = p1.metadata  # miss
    _ = p1.metadata  # cached hit, second access
    p2 = Project("auth")  # different instance — different cache entry
    _ = p2.metadata  # miss
```

`lru_cache` keys on the *argument tuple* — `fetch("auth")` and `fetch("auth")` both hit the same cache entry because the key `("auth",)` is identical. `cached_property` keys on the *instance* — `p1.metadata` and `p2.metadata` are different cache entries because `p1` and `p2` are different objects, even though they have the same `id="auth"`.

The line:

- Use `lru_cache` when the cache key is the *arguments* — slug → metadata, user_id → display_name.
- Use `cached_property` when the cache key is the *instance* — a `Project` whose metadata is computed from its `id`, where different instances of `Project` with the same `id` should re-compute (they're conceptually different objects, even if they represent the same row).

The slotted-class trap doesn't apply to `lru_cache` — `lru_cache` stores in the wrapper, not on the instance, so it works on any class. The trade-off: `lru_cache` on a method holds `self` forever (memory leak), as covered in [[02-functools/01-lru_cache-and-Caching]].

### Lines 84–95: The `main` routine

```python
def main() -> None:
    print("=== cached_property basic ===")
    p = Project("auth")
    print(f"first access:   {p.metadata}")
    print(f"second access:  {p.metadata}")  # no recompute

    print()
    print("=== 3.12 thread race (no lock in 3.12) ===")
    thread_race_demo()

    print()
    print("=== lru_cache vs cached_property ===")
    lru_cache_vs_cached_property()

    print()
    print("=== the slotted-class bug ===")
    try:
        sp = SlottedProject("auth")
        _ = sp.metadata
    except TypeError as e:
        print(f"  TypeError: {e}")
```

The four demos in order: basic caching (compute once, reuse forever), the 3.12 thread race (N threads compute N times), the `lru_cache` vs `cached_property` key-axis difference, and the slotted-class `TypeError`. The try/except catches the `TypeError` to make the demo print the error rather than crash.

## Execution Trace

```bash
$ uv run python boardly/cached_property_demo.py
=== cached_property basic ===
  computing metadata for auth...
first access:   {'id': 'auth', 'name': 'Auth', 'owner': 'rahul'}
second access:  {'id': 'auth', 'name': 'Auth', 'owner': 'rahul'}

=== 3.12 thread race (no lock in 3.12) ===
  function called 3 times by 3 racing threads
  cached value: {'id': 'auth', 'computed_by': 'T0'}

=== lru_cache vs cached_property ===
  lru_cache (keyed on the slug argument):
  lru_cache miss for auth
  lru_cache miss for billing
  cached_property (keyed on the instance):
  computing metadata for auth...
  computing metadata for auth...

=== the slotted-class bug ===
  TypeError: No '__dict__' attribute on 'SlottedProject' instance to cache 'metadata' property.
```

The first block shows `metadata` is computed once and cached — the second access prints no `"computing"` line, proving the cache hit. The second block shows the race: 3 threads, 3 computations, one cached value. The third block shows `lru_cache` misses once per *unique argument* (`"auth"` cached, second call hits; `"billing"` is a new miss) while `cached_property` misses once per *instance* (two `Project` instances with `id="auth"` both compute, because they're different objects). The fourth block shows the `TypeError` on a slotted class.

## Common Mistakes

### Mistake 1: Decorating a method that takes arguments

```python
class Project:
    @functools.cached_property
    def fetch(self, slug: str) -> dict: ...  # ← won't work
```

**Symptom:** `TypeError: fetch() missing 1 required positional argument: 'slug'` when you access `project.fetch`.

**Why:** `cached_property` only works on zero-argument methods. The descriptor's `__get__` calls `self.func(instance)` — no arguments. A method with `slug` needs an argument.

**Fix:** Use `@lru_cache` instead, but be aware of the `self`-in-cache memory leak. Or restructure: extract the per-instance logic into a zero-arg method and the per-argument logic into a free function.

### Mistake 2: Using `cached_property` on a slotted class without `__dict__`

```python
class Project:
    __slots__ = ("id",)  # no __dict__
    @functools.cached_property
    def metadata(self) -> dict: ...
```

**Symptom:** `TypeError: No '__dict__' attribute on 'Project' instance to cache 'metadata' property.` on first access.

**Why:** `cached_property` stores the result in `instance.__dict__[name]`. A slotted class without `__dict__` in slots has no `__dict__`.

**Fix:** Add `"__dict__"` to `__slots__` (`__slots__ = ("id", "__dict__")`), or use `lru_cache` instead (which stores on the wrapper, not the instance), or write a manual cache in a slot.

### Mistake 3: Assuming `cached_property` is thread-safe in 3.12

```python
# Pre-3.12 cached_property had a per-instance RLock; 3.12 removed it.
# Race: N threads can compute N times before any store wins.
```

**Symptom:** Performance regression in a multi-threaded workload — the cached computation runs once per racing thread instead of once total.

**Why:** The 3.12 implementation removed the `RLock`. The GIL ensures the store is atomic, but doesn't prevent multiple threads from computing before any store wins. For idempotent computations this is correct but wasteful; for non-idempotent (e.g. incrementing a counter) it's a correctness bug.

**Fix:** If thread-safety matters, use `@lru_cache` (which has its own lock) or write a manual `RLock`-protected cache:

```python
class Project:
    def __init__(self, project_id):
        self.id = project_id
        self._metadata_lock = threading.RLock()
        self._metadata = None

    @property
    def metadata(self):
        if self._metadata is None:
            with self._metadata_lock:
                if self._metadata is None:  # double-check
                    self._metadata = self._compute_metadata()
        return self._metadata
```

## Engineering Trade-Offs

**Decision:** Use `@functools.cached_property` for zero-argument, instance-keyed, lazy, idempotent computations on classes that have `__dict__` (the default).

**Both sides:** The alternatives are `@property` (recomputes every access — fine for cheap computations, bad for expensive ones), `@lru_cache` on a method (memory leak via `self` retention), and a manual cache (verbose but fully controlled). `cached_property` wins for the common case because it's one line, lazy, and free after first access. It loses on slotted classes, on methods with arguments, and on non-idempotent or non-thread-safe computations.

**Commitment:** `boardly` uses `cached_property` for every "expensive computed instance attribute" — `Project.metadata`, `User.permissions`, `Ticket.derived_status`. We use `@property` for cheap computations (just a dict lookup). We use `@lru_cache` for argument-keyed lookups (slug → id). We never use `cached_property` on slotted classes — slots are reserved for the small data classes in `boardly/dto/`, and those don't have cached fields.

**Why not just always use `lru_cache`?** Because `lru_cache` on a method holds `self` in the cache forever, which is a memory leak in any long-running process. `cached_property` is per-instance, dies with the instance, and never retains anything past the instance's lifetime.

## Exercises

1. **Exercise 1 — Verify the cache.** Add a `print()` statement at the top of `metadata` and call `p.metadata` three times in a row. Confirm the print fires exactly once. `Verify: uv run python boardly/cached_property_demo.py`

2. **Exercise 2 — Add a `__dict__` slot.** Modify `SlottedProject` to `__slots__ = ("id", "__dict__")` and confirm `_ = sp.metadata` now works without raising. Print the cached value. `Verify: uv run python boardly/cached_property_demo.py`

3. **Exercise 3 — Demonstrate the race with one thread.** Set the `Barrier(3)` to `Barrier(1)` and the threads list to a single thread. Confirm `function called 1 times` — single-threaded access doesn't race. Then bump back to 3 and confirm `function called 3 times`. `Verify: uv run python boardly/cached_property_demo.py`

4. **Exercise 4 — Compare `lru_cache` on a method.** Add `@functools.lru_cache` to a method on `Project` and demonstrate the `self`-in-cache retention by calling `import gc; gc.collect()` and checking the instance survives (because the cache holds it). Use `weakref.ref` to detect this. `Verify: uv run python -c "..."`

5. **Exercise 5 — Write a thread-safe cached_property.** Replace `cached_property` on `Project.metadata` with a manual `RLock`-protected cache. Verify the race demo returns `function called 1 times` for 3 threads. `Verify: uv run python boardly/cached_property_demo.py`

## Verification

```bash
$ uv run python boardly/cached_property_demo.py
=== cached_property basic ===
  computing metadata for auth...
first access:   {'id': 'auth', 'name': 'Auth', 'owner': 'rahul'}
second access:  {'id': 'auth', 'name': 'Auth', 'owner': 'rahul'}

=== 3.12 thread race (no lock in 3.12) ===
  function called 3 times by 3 racing threads
  cached value: {'id': 'auth', 'computed_by': 'T0'}

=== lru_cache vs cached_property ===
  lru_cache (keyed on the slug argument):
  lru_cache miss for auth
  lru_cache miss for billing
  cached_property (keyed on the instance):
  computing metadata for auth...
  computing metadata for auth...

=== the slotted-class bug ===
  TypeError: No '__dict__' attribute on 'SlottedProject' instance to cache 'metadata' property.
```

## Previously Learned Here

- [[02-functools/01-lru_cache-and-Caching]] — `lru_cache` is the function-level, argument-keyed cache; `cached_property` is the instance-level, zero-arg cache. The two are siblings with different shapes.
- [[02-functools/05-reduce]] — neither `reduce` nor `cached_property` is the default tool; both are specialised for their niche.

## What's Next

[[02-functools/07-total_ordering]] — the last lesson in the section. `total_ordering` is a one-decorator shortcut that fills in the missing comparison methods (`__lt__`, `__le__`, `__gt__`, `__ge__`) from a `__eq__` and one ordering method. It's small, opinionated, and the right way to make a `Ticket` sortable in one line.

- `@total_ordering` — fill in the comparison methods.
- The `__lt__` + `__eq__` minimum.
- The performance cost of the generated methods.

## Sources

- **`functools.cached_property`** — https://docs.python.org/3.12/library/functools.html#functools.cached_property — accessed 2026-10-23 — the canonical reference, including the note about thread-safety and the slotted-class requirement.
- **Python 3.12 changelog — `functools.cached_property`** — https://docs.python.org/3.12/whatsnew/3.12.html — accessed 2026-10-23 — documents the removal of the per-instance `RLock` in 3.12 and the rationale.
- **Descriptor How-To** — https://docs.python.org/3.12/howto/descriptor.html — accessed 2026-10-23 — explains why instance `__dict__` shadows non-data descriptors, the mechanism `cached_property` relies on.

## What We Learned

- You can apply `@functools.cached_property` to a zero-argument instance method for per-instance caching.
- You can explain the 3.12 implementation — no threading lock, the GIL provides atomicity, the race is bounded.
- You can state the difference between `cached_property` (instance-keyed) and `lru_cache` (argument-keyed).
- You can demonstrate the slotted-class `TypeError` and fix it by adding `"__dict__"` to `__slots__`.
- You can choose between `cached_property`, `@property`, and `lru_cache` based on the cache shape you need.
