---
title: "Lesson 02: WeakSet and finalize"
aliases:
 - WeakSet
 - weakref.finalize
 - finalize
 - __del__ replacement
tags:
 - weakref
 - weakset
 - finalize
 - cleanup
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[19-weakref/01-WeakValueDictionary]]"
related_lessons:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[19-weakref/03-When-weakrefs-save-memory]]"
---

# Lesson 02: `WeakSet` and `finalize`

*The two `weakref` primitives that have nothing to do with caches — `WeakSet` for subscriber lists that should die when their owners do, and `weakref.finalize` for the modern, reliable replacement for `__del__`.*

**You're at the very beginning of Section 19, second lesson in.**

You have met `WeakValueDictionary` and `WeakKeyDictionary` — both are *mappings* with one weak side. The `weakref` module has two more primitives that don't fit the mapping shape at all. `WeakSet` is a `set` whose elements are held by weak reference — the right shape for an event-bus subscriber list where the bus must not keep subscribers alive after their owning request finishes. `weakref.finalize(obj, callback, *args)` is the modern replacement for `__del__` — you register a callback to run when `obj` is garbage-collected, and CPython guarantees the callback runs even during interpreter shutdown if `obj` is still alive. The two together cover the non-cache half of `weakref`: "I have a collection of things I don't want to own" and "I have a thing I want to clean up after, but I can't trust `__del__`". By the end of this lesson you will know exactly when to reach for `WeakSet` over a plain `set`, why `finalize` is *strictly better* than `__del__` in 3.12, and the one trap that has bitten every team that adopted `finalize` first. Take your time. Type every example. **This is how you learn.**

#weakref #weakset #finalize #cleanup

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `WeakSet`** and explain that auto-removal happens when an element's last strong reference dies.
2. **Snapshot-iterate a `WeakSet` safely** — explain why `list(self._listeners)` is required before iteration.
3. **Register `weakref.finalize(obj, callback, *args, **kwargs)`** and articulate the four-method surface: `.alive`, `.atexit`, `.detach()`, `.peek()`.
4. **Explain why `finalize` replaces `__del__`** — no resurrection, no GC-order issues, callback runs during interpreter shutdown if `atexit=True`.
5. **Diagnose the `finalize` closure trap** — closures that capture `obj` silently prevent collection; the rule is "never pass the object itself, pass its data".

## Prerequisites

Before starting, you need:

- **`WeakValueDictionary`** — [[19-weakref/01-WeakValueDictionary]]. The auto-removal mechanism is the same in `WeakSet` (weakref callbacks); having seen it once makes the second pass easier.
- **`__del__` and the GC interaction** — you should have written at least one `__del__` method and been bitten by one of its traps (a `__del__` that raises, a `__del__` that resurrects, or a `__del__` that didn't run at shutdown). If you have not, the lesson will still work but the "why finalize" motivation lands harder if you have.
- **About 25–35 minutes of focused time.**

**The most common gap: thinking `__del__` and `finalize` are interchangeable.**

They are not. `__del__` is a method *on the class*; it has access to `self` and can resurrect the object by storing `self` somewhere. `finalize` is a *separate object* that holds a weak reference to `obj` and runs a callback when `obj` dies; the callback receives *arguments you choose*, never `obj` itself. `__del__`'s access to `self` is precisely what makes it dangerous — a `__del__` that calls `self.save()` can resurrect a half-dead object and confuse the GC. `finalize` cannot resurrect because the callback never sees `obj`. If you take one thing from this lesson: prefer `finalize` for every "run X when Y dies" use case, and reserve `__del__` for debugging.

## The Problem

You ship `boardly/events/bus.py` — an in-process event bus. Endpoints subscribe to ticket-change events; the bus publishes when a ticket is updated. The naive implementation uses a plain `set` of listeners:

```python
class TicketBus:
    def __init__(self):
        self._listeners: set[TicketChangeListener] = set()
    def subscribe(self, l):
        self._listeners.add(l)
    def publish(self, ticket_id):
        for l in self._listeners:
            l.on_change(ticket_id)
```

The bus is a process-singleton. Listeners are per-request — each endpoint subscribes one, processes the request, returns. The bus *never* removes anyone. Every long-running worker now has a memory leak: every listener ever subscribed is still in `self._listeners`, holding the request context, the user, the database session, the works. The bus is the largest object in the worker's heap, and it's full of dead listeners.

`WeakSet` is the one-line fix: change `set` to `weakref.WeakSet`, and the auto-removal kicks in. When the request that subscribed the listener returns, its local reference dies, the listener's refcount hits zero, the `WeakSet`'s weakref callback fires, and the entry is removed from the underlying `set`. The bus is bounded by *currently-subscribed* listeners, not by *ever-subscribed* listeners.

The second problem is `boardly/db/pool.py`. You have a `Connection` class that wraps a database session. When a `Connection` is forgotten (the caller never calls `.close()`), you want it returned to the idle pool. The classic solution is `__del__`:

```python
class Connection:
    def __del__(self):
        self._return_to_pool()
```

This breaks in three ways. (1) `__del__` runs in the GC's "object teardown" phase — if `self._return_to_pool` raises, the exception is silently swallowed and the pool is corrupted. (2) `__del__` can *resurrect* `self` by storing `self` in a global, which the GC then has to handle specially. (3) `__del__` is *not* guaranteed to run at interpreter shutdown if the object is still alive — CPython historically skips `__del__` for objects still alive at exit in certain orders, and even when it runs, the order is unspecified. `weakref.finalize` fixes all three: the callback runs in a clean context, it cannot resurrect `obj` (it never sees `obj`), and CPython's `atexit` flag (default `True`) guarantees the callback runs at interpreter exit *in reverse order of registration*.

## The Code

```python
# boardly/weakref_bus_demo.py
"""boardly TicketBus (WeakSet of subscribers) + ConnectionPool (finalize)."""
from __future__ import annotations

import gc
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: str
    name: str


class TicketChangeListener:
    """A subscriber that wants a callback when a ticket changes."""
    def __init__(self, name: str) -> None:
        self.name = name

    def on_change(self, ticket_id: str) -> None:
        print(f"  [{self.name}] ticket {ticket_id} changed")


class TicketBus:
    """In-process event bus. Subscribers are held weakly — when a
    listener dies (its owning request finishes), the bus forgets it
    automatically."""

    def __init__(self) -> None:
        self._listeners: weakref.WeakSet[TicketChangeListener] = (
            weakref.WeakSet()
        )

    def subscribe(self, listener: TicketChangeListener) -> None:
        self._listeners.add(listener)

    def publish(self, ticket_id: str) -> None:
        # Snapshot via sorted list — WeakSet's own __iter__ skips dead
        # refs but raises RuntimeError if .discard() is called mid-loop.
        # The sorted snapshot holds strong refs to every listener for
        # the duration of publish, so neither can happen, and the
        # alphabetical order makes the Execution Trace reproducible.
        for listener in sorted(self._listeners, key=lambda l: l.name):
            listener.on_change(ticket_id)

    def __len__(self) -> int:
        return len(self._listeners)


# --- finalize: the modern replacement for __del__ ---

class Connection:
    """A fake DB connection that needs to be returned to a pool."""
    _next_id = 0

    def __init__(self) -> None:
        Connection._next_id += 1
        self.id = Connection._next_id
        print(f"  Connection {self.id} opened")

    def close(self) -> None:
        print(f"  Connection {self.id} closed (returned to pool)")


def _return_to_pool(conn_id: int) -> None:
    """Module-level cleanup callback. weakref.finalize calls this when
    the Connection is GC'd. No reference to the Connection is passed in
    — by the time this runs, the object is already gone."""
    print(f"  finalize fired for Connection {conn_id}: returning to pool")


class ConnectionPool:
    """Wraps each Connection with a weakref.finalize so that forgetting
    to call .close() still releases the resource back to the pool."""

    def __init__(self) -> None:
        self._idle: list[Connection] = []

    def acquire(self) -> Connection:
        conn = Connection()
        # Register cleanup. We pass the *id* (an int), not conn —
        # finalize must NOT hold a strong reference to conn, or
        # conn never dies.
        weakref.finalize(conn, _return_to_pool, conn.id)
        return conn


def main() -> None:
    print("=== WeakSet of subscribers ===")
    bus = TicketBus()
    l1 = TicketChangeListener("worker-1")
    l2 = TicketChangeListener("worker-2")
    bus.subscribe(l1)
    bus.subscribe(l2)
    print(f"  bus has {len(bus)} listeners")
    bus.publish("t_100")

    # worker-1's request finishes; its listener goes out of scope.
    del l1
    gc.collect()
    print(f"  after del l1 + gc.collect(): bus has {len(bus)} listeners")
    bus.publish("t_101")  # only worker-2 receives

    print()
    print("=== weakref.finalize for cleanup ===")
    pool = ConnectionPool()
    conn = pool.acquire()
    print(f"  got Connection {conn.id}; forgetting to call .close()...")
    del conn
    gc.collect()
    print("  (cleanup above fired via weakref.finalize, not __del__)")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–10: Imports and the `Project` model

```python
# boardly/weakref_bus_demo.py
"""boardly TicketBus (WeakSet of subscribers) + ConnectionPool (finalize)."""
from __future__ import annotations

import gc
import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: str
    name: str
```

`weakref` for `WeakSet` and `finalize`. `gc` for forced collection in the demo. `dataclass(frozen=True)` for `Project` — kept here because the second half of the lesson (the connection pool) is a parallel to the lesson-01 cache story, and a `Project` model is what the rest of `boardly` uses; even though `Project` is unused in this particular demo's `main()`, the import mirrors the project template so students copy-pasting into a real `boardly` module don't have to add it.

**Why is `Project` declared but never used in `main()`?** For lesson continuity. The previous lesson built a `ProjectCache`; the next lesson (memory) uses `Project` heavily. Keeping `Project` in this file means a student can clone this file as the starting point for a `boardly/events/bus.py` module and the model is already there. In a real module you would remove the unused import; in a lesson it documents the cross-section continuity.

### Lines 13–19: The listener class

```python
class TicketChangeListener:
    """A subscriber that wants a callback when a ticket changes."""
    def __init__(self, name: str) -> None:
        self.name = name

    def on_change(self, ticket_id: str) -> None:
        print(f"  [{self.name}] ticket {ticket_id} changed")
```

`TicketChangeListener` is the per-request subscriber. Each endpoint constructs one, subscribes it, processes the request, returns. The class is intentionally not a dataclass — listeners carry mutable state (a request context, an HTTP session) and don't benefit from the dataclass-generated `__init__`/`__repr__`/`__eq__`. The `name` attribute is the only thing the lesson needs for the deterministic `sorted()` call in `publish()`.

### Lines 22–36: The `WeakSet`-backed bus

```python
class TicketBus:
    """In-process event bus. Subscribers are held weakly — when a
    listener dies (its owning request finishes), the bus forgets it
    automatically."""

    def __init__(self) -> None:
        self._listeners: weakref.WeakSet[TicketChangeListener] = (
            weakref.WeakSet()
        )

    def subscribe(self, listener: TicketChangeListener) -> None:
        self._listeners.add(listener)
```

`weakref.WeakSet()` constructs the set. The type parameter `[TicketChangeListener]` is the 3.9+ generic form. Internally the type stores elements as `{weakref.ref(element): True}` in an underlying `set` (the `weakref.ref` is the actual set element, hashable by identity). When you `.add(listener)`, the `WeakSet` calls `weakref.ref(listener, self._remove)` — registering the same kind of callback that `WeakValueDictionary` uses, so that when `listener` dies, the entry is removed from the underlying `set`.

The API is the `set` API: `.add()`, `.discard()`, `.remove()`, `.pop()`, `.clear()`, `len()`, `in`, iteration, and the set-algebra operations (`.union()`, `.intersection()`, etc., which return plain `set`s, not `WeakSet`s — the weak semantics don't compose). If you know `set`, you know `WeakSet`; the only behavioural difference is the auto-removal.

**Why `WeakSet` and not `WeakValueDictionary` keyed by `id(listener)`?** Because the listener is the *thing you're storing*, not the key for some other value. A `WeakSet` says "I have a collection of things I don't own"; a `WeakValueDictionary` says "I have a map from keys to values I don't own". The bus is the first shape. Using a dict for it would force an arbitrary key (`id(listener)` or `name`) and would invite bugs where two listeners with the same key clobber each other. The set is the right abstraction.

### Lines 38–44: Safe iteration

```python
    def publish(self, ticket_id: str) -> None:
        # Snapshot via sorted list — WeakSet's own __iter__ skips dead
        # refs but raises RuntimeError if .discard() is called mid-loop.
        # The sorted snapshot holds strong refs to every listener for
        # the duration of publish, so neither can happen, and the
        # alphabetical order makes the Execution Trace reproducible.
        for listener in sorted(self._listeners, key=lambda l: l.name):
            listener.on_change(ticket_id)
```

`sorted(self._listeners, key=...)` builds a `list` snapshot of the live listeners and sorts it. Three reasons. First, deterministic delivery order — the lesson's Execution Trace is reproducible across runs (a bare `WeakSet` iterates its underlying `set`, whose order is hash-based and unspecified). Second, snapshot semantics: `WeakSet.__iter__` does *not* snapshot — it iterates `self.data` (a `set` of `weakref.ref` objects) directly. CPython 3.12's iterator skips dead refs (the iterator yields `itemref()` only when non-`None`) and defers GC-driven removals to `_pending_removals` until iteration ends, so an unvisited listener that dies mid-iteration is silently skipped — not visited, not raised. Explicit `.discard()` or `.remove()` calls *do* modify `self.data` immediately, and that raises `RuntimeError: Set changed size during iteration`. The `sorted()` snapshot sidesteps both: the strong-reference `list` keeps every listener alive for the duration of the publish (so GC cannot kill one mid-iteration), and the iteration is over the snapshot rather than the live `WeakSet`, so explicit `.discard()` calls inside `on_change` modify the underlying set without breaking the snapshot. Third, the strong-reference snapshot is the contract a subscriber expects: every listener stays alive at least until its `on_change` returns, even if the only other strong reference to it has already gone out of scope.

**Why sort by name and not by insertion order?** Because `WeakSet` does not preserve insertion order — its underlying container is a `set`, not a `dict`, and `set` iteration order is hash-based and unspecified. If you need insertion-order delivery, use a `dict[weakref.ref, None]`-shaped structure manually, or use a `list` of `weakref.ref` objects with periodic compaction. For an event bus, alphabetical-by-name is usually fine; for a strict "subscribers in registration order" requirement, don't use `WeakSet`.

### Lines 50–65: `Connection` and the module-level callback

```python
class Connection:
    """A fake DB connection that needs to be returned to a pool."""
    _next_id = 0

    def __init__(self) -> None:
        Connection._next_id += 1
        self.id = Connection._next_id
        print(f"  Connection {self.id} opened")

    def close(self) -> None:
        print(f"  Connection {self.id} closed (returned to pool)")


def _return_to_pool(conn_id: int) -> None:
    """Module-level cleanup callback. weakref.finalize calls this when
    the Connection is GC'd. No reference to the Connection is passed in
    — by the time this runs, the object is already gone."""
    print(f"  finalize fired for Connection {conn_id}: returning to pool")
```

`Connection` is the resource that needs cleanup. The class-level `_next_id` is a counter for the demo's reproducible output; each `Connection` gets a unique integer `id`. Note that `Connection` does *not* define `__del__` — the cleanup is registered externally, by the pool, using `weakref.finalize`. This is the key design decision: the cleanup is *separable* from the class.

`_return_to_pool` is a module-level function — *not* a method on `Connection`, *not* a closure. It takes the `conn_id` (an int) as its only argument. The `weakref.finalize` machinery will call `_return_to_pool(conn.id)` when the `Connection` dies. The callback never receives the `Connection` itself — by the time the callback fires, the `Connection` is already gone (its memory is about to be freed; the callback fires in the weakref's teardown, which runs *during* the GC of the referent).

**Why a module-level function and not a method or closure?** Two reasons. (1) A method on `Connection` would have to be `static` or receive `self` — and receiving `self` would resurrect the object (the callback would hold `self`), which is the entire bug `finalize` is meant to prevent. (2) A closure like `lambda: return_to_pool(conn)` would *close over `conn`*, holding a strong reference that prevents `conn` from ever dying. The module-level function takes only the *data* you need at cleanup time — here, `conn_id` — never the object itself. This rule ("pass data, not the object") is the single most common `finalize` bug; see Mistake 3.

### Lines 68–80: The pool with `finalize`

```python
class ConnectionPool:
    """Wraps each Connection with a weakref.finalize so that forgetting
    to call .close() still releases the resource back to the pool."""

    def __init__(self) -> None:
        self._idle: list[Connection] = []

    def acquire(self) -> Connection:
        conn = Connection()
        # Register cleanup. We pass the *id* (an int), not conn —
        # finalize must NOT hold a strong reference to conn, or
        # conn never dies.
        weakref.finalize(conn, _return_to_pool, conn.id)
        return conn
```

`weakref.finalize(conn, _return_to_pool, conn.id)` is the registration call. Its signature is `finalize(obj, func, /, *args, **kwargs)` — the `/` means `obj` and `func` are positional-only (you cannot call `finalize(obj=conn, func=...)` — they must be the first two positional args). When `conn` is GC'd, CPython invokes `_return_to_pool(conn.id)` — that is, `_return_to_pool(*args, **kwargs)` with the args you passed at registration. The return value of `_return_to_pool` is ignored.

The return value of `weakref.finalize(...)` is a `weakref.finalize` *object* (the lower-case `finalize` is the class; the call returns an instance). You usually don't store it — the registration is fire-and-forget. But the object has four useful methods and attributes, which the lesson will walk through in the next block.

**Why does `acquire()` not store the `finalize` object?** Because we don't need to manage it — the registration is fire-and-forget. If you needed to *cancel* cleanup (e.g., when an explicit `.close()` is called and you don't want the callback to also fire), you'd store the `finalize` object on the `Connection` instance and call `.detach()` in `close()`. For this lesson's "leak the connection and let finalize clean up" pattern, the registration alone is enough.

### Lines 84–103: The demo

```python
def main() -> None:
    print("=== WeakSet of subscribers ===")
    bus = TicketBus()
    l1 = TicketChangeListener("worker-1")
    l2 = TicketChangeListener("worker-2")
    bus.subscribe(l1)
    bus.subscribe(l2)
    print(f"  bus has {len(bus)} listeners")
    bus.publish("t_100")

    # worker-1's request finishes; its listener goes out of scope.
    del l1
    gc.collect()
    print(f"  after del l1 + gc.collect(): bus has {len(bus)} listeners")
    bus.publish("t_101")  # only worker-2 receives

    print()
    print("=== weakref.finalize for cleanup ===")
    pool = ConnectionPool()
    conn = pool.acquire()
    print(f"  got Connection {conn.id}; forgetting to call .close()...")
    del conn
    gc.collect()
    print("  (cleanup above fired via weakref.finalize, not __del__)")
```

The first half is the `WeakSet` demo: subscribe two listeners, confirm the bus has 2, publish (both receive), delete one, confirm the bus now has 1, publish again (only the survivor receives). The auto-removal is observable in `len(bus)` going from 2 to 1 without an explicit `bus.discard(l1)`.

The second half is the `finalize` demo: acquire a `Connection`, then `del conn` without calling `.close()`. The `_return_to_pool` callback fires during the `gc.collect()`. The cleanup is the same as if you had called `.close()` — except no one called it; the GC did. The output line `(cleanup above fired via weakref.finalize, not __del__)` documents the cause for the student reading the trace.

**Why `gc.collect()` after `del conn`?** For determinism. The `Connection`'s refcount hits zero the moment `del conn` runs (the local `conn` was the only strong reference), so the weakref callback fires *before* `del conn` returns — `gc.collect()` is technically redundant. We call it explicitly so the demo's output is reproducible even on implementations where the callback fires on the next GC pass (PyPy, alternative runtimes). In production code, do not call `gc.collect()` — let refcounting do its job.

## Execution Trace

```bash
$ uv run python boardly/weakref_bus_demo.py
=== WeakSet of subscribers ===
  bus has 2 listeners
  [worker-1] ticket t_100 changed
  [worker-2] ticket t_100 changed
  after del l1 + gc.collect(): bus has 1 listeners
  [worker-2] ticket t_101 changed

=== weakref.finalize for cleanup ===
  Connection 1 opened
  got Connection 1; forgetting to call .close()...
  finalize fired for Connection 1: returning to pool
  (cleanup above fired via weakref.finalize, not __del__)
```

The first block shows the bus receiving both listeners for `t_100` (delivered in alphabetical order thanks to the `sorted()` snapshot), then only `worker-2` for `t_101` after `worker-1` was deleted. The second block shows `Connection 1` opened, then `finalize fired for Connection 1` — the cleanup ran without anyone calling `.close()`.

## Common Mistakes

### Mistake 1: Iterating a `WeakSet` without a snapshot

```python
class TicketBus:
    def __init__(self):
        self._listeners = weakref.WeakSet()
    def publish(self, ticket_id):
        for listener in self._listeners:           # ← no snapshot
            listener.on_change(ticket_id)          # ← may drop other refs
```

**Symptom:** Intermittent `RuntimeError: Set changed size during iteration`, or subscribers silently skipped, in long-running workers under GC pressure.

**Why:** `WeakSet.__iter__` iterates the underlying `set` of `weakref.ref` objects directly — it does *not* snapshot. CPython 3.12's iterator skips dead refs (it yields `itemref()` only when non-`None`) and defers GC-driven removal to `_pending_removals` until iteration ends, so an unvisited listener that dies mid-iteration is silently skipped — not visited, not raised. Explicit `.discard()` or `.remove()` calls *do* modify `self.data` immediately, and that raises `RuntimeError: Set changed size during iteration`. A listener's `on_change` can trigger GC (drops the last reference to another listener) or call `.discard()` itself, and either path produces a silent skip or a loud `RuntimeError` — neither of which is what a publish loop wants.

**Fix:** Take an explicit snapshot — `for listener in list(self._listeners):`. If you need deterministic delivery order, `sorted(list(self._listeners), key=...)` does both jobs in one call.

### Mistake 2: Using `__del__` instead of `finalize`

```python
class Connection:
    def __del__(self):
        self._pool.return_to_pool(self)  # ← resurrects self
```

**Symptom:** The connection is *never* GC'd — `__del__` stored `self` in the pool, which counts as a strong reference, which keeps `self` alive, which keeps `__del__` from ever being called again. (Or: `__del__` runs but raises, the exception is swallowed, the pool is corrupted, the worker silently leaks connections.)

**Why:** `__del__` receives `self`, so any operation that stores `self` anywhere — including in a pool — is a resurrection. The GC must re-detect the resurrection and treat the object as live, which is expensive and error-prone. Worse, `__del__` exceptions are silently swallowed by CPython (since 3.8 the exception is printed to stderr but the program continues), so a buggy `__del__` corrupts state without raising.

**Fix:** Use `weakref.finalize`. Register the cleanup externally, pass *data* (the connection id, the pool reference) — never `self`. The callback fires when `self` is gone, with the data you passed; it cannot resurrect because it never sees `self`.

### Mistake 3: Closures that capture `obj`

```python
def acquire(self):
    conn = Connection()
    weakref.finalize(conn, lambda: self._return_to_pool(conn))  # ← captures conn!
    return conn
```

**Symptom:** `conn` is never GC'd; the `finalize` callback never fires. The pool appears to leak connections in production.

**Why:** The `lambda` closes over `conn` (it references `conn` inside its body). The `weakref.finalize` object holds the `lambda` as its callback. The `lambda` holds `conn`. So `finalize` holds `conn` strongly — the only weak reference is the one inside the finalize machinery, and as long as the finalize object exists, the lambda exists, and `conn` exists. The cycle: `finalize` → `lambda` → `conn` → `finalize` (via the weakref). CPython's cycle detector eventually breaks this, but only on a full GC pass, not on the refcount hit — which means cleanup is delayed arbitrarily and may not fire at all if the program exits first.

**Fix:** Pass *data*, not the object. `weakref.finalize(conn, self._return_to_pool, conn.id)` — the callback receives `conn.id` (an int, copied by value), not `conn`. The callback cannot close over `conn` because `conn` never appears in the callback's body.

## Engineering Trade-Offs

**Decision:** Use `WeakSet` for "I have a collection of things I don't own" (subscriber lists, observer registries, plugin registries). Use `weakref.finalize` for "I want a callback to run when an object dies" (resource cleanup, leak detection, teardown).

**Both sides:** The alternatives are a plain `set` (holds listeners forever — memory leak) and `__del__` (resurrection-prone, exception-swallowing, shutdown-unreliable). The `WeakSet`/`finalize` pair trades a small constant-factor cost (callback registration on insert, snapshot iteration) for the correctness properties — auto-removal on death, no resurrection, atexit-guaranteed cleanup. For long-running processes, the trade is overwhelmingly worth it; for short-lived scripts, a plain `set` and `__del__` are fine because the whole process exits before the leak matters.

**Commitment:** `boardly` uses `WeakSet` for `TicketBus` (subscriber list), `WebSocketHub` (live socket list), and `PluginRegistry` (loaded plugin list). `weakref.finalize` is used by `ConnectionPool` (return connections on GC), `TemporaryFile` (delete file on GC), and `LeakDetector` (log when an expected-short-lived object survives a configurable threshold). `__del__` is *forbidden* in the `boardly` style guide — every "cleanup on death" use case uses `finalize` instead.

**Why not always `__del__` for simple cases?** Because `__del__`'s failure modes are *silent*. A `__del__` that raises prints to stderr and continues; a `__del__` that resurrects confuses the GC and may re-trigger; a `__del__` that runs at shutdown may find the module's globals already torn down (`sys.path` empty, imported modules `None`). `finalize` avoids all three by construction — the callback runs in a clean context, it cannot see the object, and the `atexit=True` flag guarantees ordered shutdown. The simplicity of `__del__` is a trap; the verbosity of `finalize` is the price of correctness.

## Exercises

1. **Exercise 1 — Verify auto-removal.** Add a third listener `l3 = TicketChangeListener("worker-3")`, subscribe it, then `del l3` and `gc.collect()`. Confirm `len(bus)` drops back to 2. `Verify: uv run python boardly/weakref_bus_demo.py`

2. **Exercise 2 — Use `finalize.detach()`.** Acquire a `Connection`, then call `finalizer = weakref.finalize(conn, _return_to_pool, conn.id)` and store the return value. Call `finalizer.detach()` immediately — this deactivates the finalizer. `del conn` should *not* fire the callback. Print `finalizer.alive` before and after `detach()` to confirm. `Verify: uv run python boardly/weakref_bus_demo.py`

3. **Exercise 3 — Demonstrate the `atexit` flag.** Set `fin = weakref.finalize(conn, _return_to_pool, conn.id)`; set `fin.atexit = False`. Now `del conn` still fires the callback at GC, but if `conn` were still alive at process exit, the callback would *not* run. Print `fin.atexit` to confirm the flag is settable. `Verify: uv run python boardly/weakref_bus_demo.py`

4. **Exercise 4 — Reproduce Mistake 3.** Change `weakref.finalize(conn, _return_to_pool, conn.id)` to `weakref.finalize(conn, lambda: _return_to_pool(conn.id))` — the lambda closes over `conn`. Confirm that `del conn; gc.collect()` does *not* fire the callback immediately, and that `gc.collect()` may take a second pass (cycle GC) to break the cycle. `Verify: uv run python boardly/weakref_bus_demo.py`

5. **Exercise 5 — Replace `__del__` with `finalize`.** Write a `TempFile` class with `__del__` that calls `os.unlink(self.path)`. Demonstrate one of the `__del__` traps (resurrection via storing `self` in a global, or silent exception swallowing). Then replace `__del__` with `weakref.finalize(self, os.unlink, self.path)` registered in `__init__` (carefully — see Mistake 3) and confirm the cleanup is reliable. `Verify: uv run python boardly/weakref_bus_demo.py`

## Verification

```bash
$ uv run python boardly/weakref_bus_demo.py
=== WeakSet of subscribers ===
  bus has 2 listeners
  [worker-1] ticket t_100 changed
  [worker-2] ticket t_100 changed
  after del l1 + gc.collect(): bus has 1 listeners
  [worker-2] ticket t_101 changed

=== weakref.finalize for cleanup ===
  Connection 1 opened
  got Connection 1; forgetting to call .close()...
  finalize fired for Connection 1: returning to pool
  (cleanup above fired via weakref.finalize, not __del__)
```

## Previously Learned Here

- [[19-weakref/01-WeakValueDictionary]] — the same auto-removal mechanism (weakref callbacks) underlies `WeakSet`. The callback bookkeeping is the same; the container is a `set` instead of a `dict`.
- [[03-contextlib/01-contextmanager]] — `contextmanager` is the *deterministic* cleanup primitive (`with` block exits, cleanup runs). `finalize` is the *fallback* primitive (object is GC'd, cleanup runs if it didn't already). The two are complementary — `contextmanager` for the happy path, `finalize` for the leak path.

## What's Next

[[19-weakref/03-When-weakrefs-save-memory]] — the decision lesson. When do `WeakValueDictionary`, `WeakSet`, and `finalize` actually save memory in production, and when are they pure indirection? The lesson walks a long-running worker that holds a `WeakValueDictionary` of recently-loaded projects, compares the cache's memory profile with `lru_cache`'s, and commits the rule: weakrefs win when you have a long-lived mapping of short-lived objects, lose when you have the opposite. Three things to take with you:

- `WeakSet` is the right shape for "collection of things I don't own" — `WeakValueDictionary` is the right shape for "map of values I don't own".
- `weakref.finalize` is the modern `__del__` — pass *data*, not the object, or you'll silently prevent collection.
- The `atexit=True` flag (default) guarantees the callback runs at interpreter shutdown, in reverse order of registration.

## Sources

- **`weakref` — Weak references** — https://docs.python.org/3/library/weakref.html — accessed 2026-10-23 — the canonical reference, including the `WeakSet` API surface and the `finalize` class's `.atexit`, `.alive`, `.detach()`, `.peek()` methods.
- **`weakref.finalize`** — https://docs.python.org/3/library/weakref.html#weakref.finalize — accessed 2026-10-23 — the class docstring is the best one-paragraph explanation of why `finalize` replaces `__del__`; the atexit guarantee and the "no reference to obj" contract are both documented here.
- **PEP 205 — Weak References** — https://peps.python.org/pep-0205/ — accessed 2026-10-23 — the original PEP; the "Cyclic garbage collection" section explains why weakref callbacks cannot resurrect the referent.
- **Python 3.13 what's new — `weakref`** — https://docs.python.org/3.13/whatsnew/3.13.html — accessed 2026-10-23 — version-gated note: Python 3.13 added `__copy__` and `__reduce__` to `weakref.ref`, making weak references picklable. On 3.12 (this vault's runtime), these are absent — you cannot pickle a bare `weakref.ref` on 3.12.

## What We Learned

- You can construct a `WeakSet` and explain that auto-removal happens when an element's last strong reference dies.
- You can snapshot-iterate a `WeakSet` safely with `list(self._listeners)` (or `sorted(...)`) before the loop.
- You can register `weakref.finalize(obj, callback, *args, **kwargs)` and explain the four-method surface: `.alive`, `.atexit`, `.detach()`, `.peek()`.
- You can explain why `finalize` replaces `__del__` — no resurrection, no GC-order issues, atexit-guaranteed cleanup.
- You can diagnose the `finalize` closure trap — closures that capture `obj` silently prevent collection; the rule is "pass data, not the object".
