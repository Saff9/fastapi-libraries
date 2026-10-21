---
title: "Lesson 02: Lock and Event"
aliases:
 - asyncio.Lock
 - asyncio.Event
 - async mutual exclusion
 - FIFO fairness
tags:
 - asyncio
 - python-stdlib
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[21-asyncio-primitives/01-Task-gather-wait_for]]"
related_lessons:
 - "[[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]]"
 - "[[21-asyncio-primitives/04-Semaphore-and-Condition]]"
first_taught_in: "21-asyncio-primitives/02-Lock-and-Event"
---

# Lesson 02: `Lock` and `Event`

*`asyncio.Lock` for async mutual exclusion (only one task in the critical section; FIFO fair since 3.10) and `asyncio.Event` for one-to-many wake-ups — the two primitives that let concurrent tasks co-ordinate without a shared memory model.*

**You're at the very beginning of Section 21, two lessons in.**

You can run N tasks concurrently now. The next problem is "what happens when two of them touch the same thing at the same time?" In boardly: a tiny in-process cache that two concurrent refresh tasks can both miss, both decide to call the DB, and stampede the upstream. The fix is `asyncio.Lock` — async mutual exclusion, only one task in the critical section at a time, FIFO fair since 3.10. And the next problem after that is "how do I make N tasks wait for a single signal, then wake them all at the same instant?" — `asyncio.Event`, the broadcast primitive. By the end of this lesson you will know both, plus the difference from `threading.Lock` (the asyncio Lock is *not reentrant* — re-acquiring from the same task deadlocks — and is awaitable, not blocking). Take your time. Type every example. **This is how you learn.**

#asyncio #lock #event

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `asyncio.Lock` for async mutual exclusion** — `async with lock:` acquires/releases; only one task is inside the block at a time.
2. **State the FIFO fairness guarantee** — since 3.10, `asyncio.Lock` wakes waiters in the order they queued; no starvation.
3. **Explain the "not reentrant" rule** — re-acquiring the lock from a task that already holds it deadlocks (unlike `threading.RLock`).
4. **Use `asyncio.Event` for one-to-many wake-ups** — `.set()` / `.clear()` / `.is_set()` / `await wait()`.
5. **Contrast `asyncio.Lock` with `threading.Lock`** — the asyncio Lock is awaitable (yields control while waiting) and lives on the event loop; `threading.Lock` is blocking and must not be used in async code.

## Prerequisites

Before starting, you need:

- **`asyncio.create_task` and `asyncio.gather`** — [[21-asyncio-primitives/01-Task-gather-wait_for]] covers the primitives that let you have N concurrent tasks in the first place. Without that, you have no concurrency to co-ordinate.
- **The `async with` protocol** — [[03-contextlib/02-asynccontextmanager]]. `async with lock:` calls `await lock.__aenter__()` on entry and `await lock.__aexit__(*exc_info)` on exit; the same protocol as `@asynccontextmanager`-decorated functions.
- **About 30–40 minutes of focused time.**

**The most common gap: using `threading.Lock` in async code.**

You have written `threading.Lock` for years. You reach for it in async code, write `with lock:`, and your code *appears* to work — until production, when a slow blocking call inside the `with` block freezes the entire event loop, because `threading.Lock.acquire` is a blocking call that does not yield control. The asyncio Lock is the *only* correct lock inside `async def`. The two are not interchangeable. The asyncio Lock's `acquire` is a coroutine — `await lock.acquire()` yields to the loop while it waits, so other tasks can run. `threading.Lock.acquire()` blocks the calling thread, which in async code means the entire loop is frozen.

## The Problem

Here is the stampede bug, in its native habitat.

```python
# boardly/cache/projects.py — the stampede version
class ProjectCache:
    def __init__(self):
        self._cache = {}

    async def get(self, slug: str) -> Project:
        if slug not in self._cache:               # check
            self._cache[slug] = await fetch_project(slug)  # populate
        return self._cache[slug]

async def handler():
    cache = ProjectCache()
    # 5 concurrent calls for the SAME slug — all miss the cache,
    # all call the DB, the upstream sees 5 calls instead of 1.
    await asyncio.gather(*[cache.get("alpha") for _ in range(5)])
```

Five concurrent tasks call `cache.get("alpha")` at the same instant. Each one checks the cache (cache miss — they all run before the first has finished populating), each one calls the DB, and you have a 5× stampede. The upstream sees 5 calls instead of 1.

The textbook fix is "double-checked locking": check the cache *again* after acquiring a lock, so the first task populates and the other 4 see the cached value. The lock has to be `asyncio.Lock` — `threading.Lock` would freeze the loop. And the lock has to be FIFO fair (which asyncio.Lock has been since 3.10), so a steady stream of callers cannot starve one unlucky task.

The Event solves a different problem: signalling. You want N worker tasks to wait for "the cache is primed" and start at the same instant. A `bool` flag does not work (the workers would busy-poll); a `Lock` does not work (only one waiter is woken on release); an `Event` is the right tool — `await event.wait()` blocks the task (without blocking the loop) until `event.set()` is called, and *every* waiter is woken on `set()`.

## The Code

```python
# boardly/asyncio_lock_event_demo.py
"""asyncio.Lock and asyncio.Event on boardly.

Lock = async mutual exclusion (only one task in the critical section).
Event = one-to-many signal (one setter, N waiters wake up at the same time).

The boardly use: a tiny in-process cache guarded by a Lock so two concurrent
refresh tasks don't stampede the upstream; an Event that signals "the cache
is primed" so N worker coroutines can start at the same instant.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class Project:
    slug: str
    name: str


# --- The shared state we protect ---
class ProjectCache:
    """Tiny in-process cache. The Lock serialises refresh."""

    def __init__(self) -> None:
        self._cache: dict[str, Project] = {}
        self._lock = asyncio.Lock()           # async mutual exclusion
        self._primed = asyncio.Event()        # "cache is ready" signal
        self._refresh_calls = 0

    async def _refresh(self, slug: str) -> Project:
        # Simulate a 30ms DB round-trip.
        await asyncio.sleep(0.03)
        self._refresh_calls += 1
        return Project(slug=slug, name=slug.title())

    async def get(self, slug: str) -> Project:
        async with self._lock:               # FIFO fair; only one task in here
            if slug not in self._cache:      # double-checked pattern
                self._cache[slug] = await self._refresh(slug)
            return self._cache[slug]

    async def prime_initial_set(self, slugs: list[str]) -> None:
        async with self._lock:
            for slug in slugs:
                self._cache[slug] = await self._refresh(slug)
        self._primed.set()                   # wake every waiter at once

    async def wait_until_ready(self) -> None:
        await self._primed.wait()            # blocks this task only

    @property
    def refresh_calls(self) -> int:
        return self._refresh_calls


# --- Demo A: the Lock prevents a stampede ---
async def stampede_demo() -> None:
    print("=== Lock prevents a stampede ===")
    cache = ProjectCache()

    # 5 concurrent gets for the SAME slug — without the lock, all 5 would
    # miss the cache and hit the DB 5 times. With the Lock, the first task
    # populates the cache; the other 4 wait and read the cached value.
    tasks = [asyncio.create_task(cache.get("alpha")) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print(f"  results: {[r.name for r in results]}")
    print(f"  upstream calls: {cache.refresh_calls} (expected 1)")


# --- Demo B: the Event wakes N waiters at the same instant ---
async def event_demo() -> None:
    print("\n=== Event wakes N waiters at once ===")
    cache = ProjectCache()

    async def worker(name: str) -> str:
        await cache.wait_until_ready()       # every worker blocks here
        proj = await cache.get(name)
        return f"{name} -> {proj.name}"

    workers = [asyncio.create_task(worker(s)) for s in ("alpha", "beta", "gamma")]
    # Give the workers a turn to start and block on the Event.
    await asyncio.sleep(0.01)
    print("  priming cache...")
    await cache.prime_initial_set(["alpha", "beta", "gamma"])
    results = await asyncio.gather(*workers)
    print(f"  results: {results}")


# --- Demo C: Lock is FIFO fair (3.10+ guarantee) ---
async def fifo_demo() -> None:
    print("\n=== Lock is FIFO fair (3.10+) ===")
    lock = asyncio.Lock()
    order: list[str] = []

    async def worker(name: str) -> None:
        async with lock:
            order.append(name)
            await asyncio.sleep(0.001)      # yield so others queue up

    # Acquire the lock first, so the workers queue in creation order.
    async with lock:
        tasks = [asyncio.create_task(worker(f"w{i}")) for i in range(5)]
        await asyncio.sleep(0.01)            # let them all queue
    await asyncio.gather(*tasks)
    print(f"  acquisition order: {order}  (expected ['w0','w1','w2','w3','w4'])")


# --- Demo D: NOT reentrant — re-acquire from the same task deadlocks ---
async def reentrancy_demo() -> None:
    print("\n=== asyncio.Lock is NOT reentrant (deadlock if you try) ===")
    lock = asyncio.Lock()

    async def inner() -> None:
        async with lock:                    # ← second acquire from the same task
            print("  this never prints")

    # Cancel after a short delay so the demo doesn't hang forever.
    task = asyncio.create_task(_hold_and_call_inner(lock, inner))
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
    except TimeoutError:
        task.cancel()
        print("  cancelled — would deadlock forever without the timeout")


async def _hold_and_call_inner(lock: asyncio.Lock, inner: Callable[[], Awaitable[None]]) -> None:
    async with lock:
        await inner()                       # tries to re-acquire


async def main() -> None:
    await stampede_demo()
    await event_demo()
    await reentrancy_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–17: Imports and the `Project` model

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class Project:
    slug: str
    name: str
```

`asyncio` brings `Lock` and `Event` (both imported from the `asyncio` namespace). `Callable` and `Awaitable` from `typing` are used in `_hold_and_call_inner`'s signature — `Callable[[], Awaitable[None]]` reads as "a callable taking no args that returns an awaitable yielding `None`", which is exactly the shape of an `async def inner() -> None` function.

### Lines 20–48: The `ProjectCache` with a `Lock` and an `Event`

```python
class ProjectCache:
    """Tiny in-process cache. The Lock serialises refresh."""

    def __init__(self) -> None:
        self._cache: dict[str, Project] = {}
        self._lock = asyncio.Lock()           # async mutual exclusion
        self._primed = asyncio.Event()        # "cache is ready" signal
        self._refresh_calls = 0

    async def _refresh(self, slug: str) -> Project:
        # Simulate a 30ms DB round-trip.
        await asyncio.sleep(0.03)
        self._refresh_calls += 1
        return Project(slug=slug, name=slug.title())

    async def get(self, slug: str) -> Project:
        async with self._lock:               # FIFO fair; only one task in here
            if slug not in self._cache:      # double-checked pattern
                self._cache[slug] = await self._refresh(slug)
            return self._cache[slug]

    async def prime_initial_set(self, slugs: list[str]) -> None:
        async with self._lock:
            for slug in slugs:
                self._cache[slug] = await self._refresh(slug)
        self._primed.set()                   # wake every waiter at once

    async def wait_until_ready(self) -> None:
        await self._primed.wait()            # blocks this task only

    @property
    def refresh_calls(self) -> int:
        return self._refresh_calls
```

`asyncio.Lock()` creates the lock. There is no constructor argument — unlike `threading.Lock`, there is no "reentrant" variant; if you need reentrancy you have `asyncio.RLock` (added in 3.13; on 3.12 you have to write the reentrancy yourself with a per-task counter, or restructure so reentrancy is not needed).

`asyncio.Event()` creates the event. The internal state is a single `bool` (`False` initially). `event.set()` flips it to `True` and wakes every current waiter; `event.clear()` flips it back to `False`; `event.is_set()` reads it; `await event.wait()` blocks the calling task until the flag is `True` (returns immediately if it is already `True`).

The `get` method is the textbook double-checked locking pattern: acquire the lock, *re-check* the cache inside the critical section (because the cache state may have changed since the outside check), populate if still missing, return. Without the inner re-check, the second-through-fifth callers would all miss the cache (because they all ran the outside check before the first had populated) and all hit the DB. With the inner re-check, only the first caller populates; the rest see the cached value and return it without a DB call.

`prime_initial_set` populates the cache for an initial set of slugs and then signals `_primed.set()` to wake every worker that is blocked on `wait_until_ready`. Note that `_primed.set()` is called *outside* the `async with self._lock` block — the lock is released first, so the woken workers can immediately acquire it to read their slugs.

### Lines 51–60: Demo A — the stampede test

```python
async def stampede_demo() -> None:
    print("=== Lock prevents a stampede ===")
    cache = ProjectCache()

    # 5 concurrent gets for the SAME slug — without the lock, all 5 would
    # miss the cache and hit the DB 5 times. With the Lock, the first task
    # populates the cache; the other 4 wait and read the cached value.
    tasks = [asyncio.create_task(cache.get("alpha")) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print(f"  results: {[r.name for r in results]}")
    print(f"  upstream calls: {cache.refresh_calls} (expected 1)")
```

Five `create_task` calls schedule five concurrent `cache.get("alpha")` invocations. The first to acquire the lock populates the cache (one DB call); the other four queue on the lock, then re-check the cache, see the value, return it (no DB call). The `refresh_calls` counter is 1, not 5 — the proof that the stampede was prevented.

**Why `asyncio.create_task(cache.get("alpha"))` instead of `asyncio.gather(*[cache.get("alpha") for _ in range(5)])`?** Because `gather` would schedule the coroutines as part of the gather call, which is fine, but the explicit `create_task` form lets the coroutines start running *before* the `await gather` line — they enter the lock and queue immediately. With `gather(*[cache.get(...) for ...])`, the coroutines are scheduled only when `gather` runs them. In this demo the difference is microseconds and the result is the same; in real code where you want the coroutines to start running while you do other work between scheduling and gathering, the `create_task` form is the right choice.

### Lines 63–76: Demo B — the Event broadcast

```python
async def event_demo() -> None:
    print("\n=== Event wakes N waiters at once ===")
    cache = ProjectCache()

    async def worker(name: str) -> str:
        await cache.wait_until_ready()       # every worker blocks here
        proj = await cache.get(name)
        return f"{name} -> {proj.name}"

    workers = [asyncio.create_task(worker(s)) for s in ("alpha", "beta", "gamma")]
    # Give the workers a turn to start and block on the Event.
    await asyncio.sleep(0.01)
    print("  priming cache...")
    await cache.prime_initial_set(["alpha", "beta", "gamma"])
    results = await asyncio.gather(*workers)
    print(f"  results: {results}")
```

Three worker tasks are created and each immediately blocks on `await cache.wait_until_ready()` — which is `await self._primed.wait()`. The `await asyncio.sleep(0.01)` after creating the workers is a yield point that gives the loop time to schedule the workers and let them reach the `wait()` call. (Without that yield, `prime_initial_set` could run before the workers had started — and `set()` would have nothing to wake.)

`prime_initial_set` populates the cache, releases the lock, then calls `_primed.set()`. The `set()` flips the internal flag and wakes every task currently blocked on `wait()` — all three workers wake at the same instant, each proceeds to `cache.get(name)`, each acquires the lock in turn (FIFO fair), reads the cached value (no DB call), and returns.

**Why an Event and not a `bool` flag?** A `bool` flag would require busy-polling — `while not self._ready: await asyncio.sleep(0.01)` — which is both wasteful (the loop runs every 10ms even when nothing changes) and racy (if `set()` happens between the `while` check and the next iteration, the worker would miss it). `Event.wait()` is implemented as a `Future` under the hood — `wait()` registers the task as a waiter on the future, and `set()` resolves the future, waking every registered waiter. No polling, no race.

### Lines 79–91: Demo C — FIFO fairness

```python
async def fifo_demo() -> None:
    print("\n=== Lock is FIFO fair (3.10+) ===")
    lock = asyncio.Lock()
    order: list[str] = []

    async def worker(name: str) -> None:
        async with lock:
            order.append(name)
            await asyncio.sleep(0.001)      # yield so others queue up

    # Acquire the lock first, so the workers queue in creation order.
    async with lock:
        tasks = [asyncio.create_task(worker(f"w{i}")) for i in range(5)]
        await asyncio.sleep(0.01)            # let them all queue
    await asyncio.gather(*tasks)
    print(f"  acquisition order: {order}  (expected ['w0','w1','w2','w3','w4'])")
```

This demo proves the FIFO guarantee. The outer code acquires the lock, then creates five worker tasks (each of which tries to acquire the lock, finds it held, and queues), then sleeps 10ms to let them all queue, then releases the lock (by exiting the `async with`). The first worker to acquire the lock appends its name; the second-through-fifth queue in the order they reached the `async with lock` line — which, because `create_task` schedules in order, is `w0, w1, w2, w3, w4`.

The `order` list ends up `['w0','w1','w2','w3','w4']` — exactly creation order. Before 3.10 this was *not* guaranteed (a `Lock` could wake waiters in any order, including random); since 3.10 the asyncio lock is FIFO, no starvation.

**Why is FIFO fairness a guarantee and not just "current behaviour"?** Because pre-3.10 asyncio had starvation bugs in production — a steady stream of callers could keep one unlucky task waiting indefinitely, because the lock would always grant to whichever task the loop happened to run next. PEP 537 (and the 3.10 release notes) committed asyncio to FIFO fairness for `Lock`, `Semaphore`, and `Event`. The guarantee matters for backpressure: a queue with FIFO-fair locks cannot starve the head of the queue.

### Lines 94–106: Demo D — `asyncio.Lock` is NOT reentrant

```python
async def reentrancy_demo() -> None:
    print("\n=== asyncio.Lock is NOT reentrant (deadlock if you try) ===")
    lock = asyncio.Lock()

    async def inner() -> None:
        async with lock:                    # ← second acquire from the same task
            print("  this never prints")

    # Cancel after a short delay so the demo doesn't hang forever.
    task = asyncio.create_task(_hold_and_call_inner(lock, inner))
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
    except TimeoutError:
        task.cancel()
        print("  cancelled — would deadlock forever without the timeout")


async def _hold_and_call_inner(lock: asyncio.Lock, inner: Callable[[], Awaitable[None]]) -> None:
    async with lock:
        await inner()                       # tries to re-acquire
```

`_hold_and_call_inner` acquires the lock, then calls `await inner()`. `inner` tries to acquire the same lock — but the lock is already held by the same task. `asyncio.Lock` does not track "which task holds me"; it only tracks "am I held". So the second `async with lock` blocks forever waiting for the first to release — which can't happen because the first is blocked in `inner`. Classic deadlock.

The `asyncio.wait_for(asyncio.shield(task), timeout=0.2)` is the safety: after 200ms with no progress, the timeout fires and `task.cancel()` aborts the deadlock. Without the timeout the demo would hang forever. (`asyncio.shield` prevents the outer `wait_for` cancellation from propagating into `task` before we manually cancel it — a subtle 3.8+ pattern for "cancel only after this deadline".)

**Why is the asyncio Lock not reentrant?** Because reentrancy requires tracking the holder, and tracking the holder requires either a thread identity (which doesn't exist for asyncio tasks, which can hop threads) or an asyncio task identity (which adds bookkeeping and gets complicated under `asyncio.shield` and `run_in_executor`). The asyncio designers chose simplicity: no reentrancy, no `RLock` (until 3.13 added `asyncio.RLock`). If you genuinely need reentrancy in 3.12, restructure the code so the inner function takes the already-locked data as an argument (`async def _inner_with_data(self, data)`) instead of acquiring the lock itself. That is also the more testable design.

### Lines 109–112: `main` and the entrypoint

```python
async def main() -> None:
    await stampede_demo()
    await event_demo()
    await reentrancy_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

Three demos run sequentially inside the same loop. `asyncio.run` creates the loop, runs `main`, and closes the loop on exit. The `asyncio.Lock` and `asyncio.Event` instances are created inside their demos — fresh state per demo, no shared state between them.

## Execution Trace

```bash
$ uv run python boardly/asyncio_lock_event_demo.py
=== Lock prevents a stampede ===
  results: ['Alpha', 'Alpha', 'Alpha', 'Alpha', 'Alpha']
  upstream calls: 1 (expected 1)

=== Event wakes N waiters at once ===
  priming cache...
  results: ['alpha -> Alpha', 'beta -> Beta', 'gamma -> Gamma']

=== Lock is FIFO fair (3.10+) ===
  acquisition order: ['w0', 'w1', 'w2', 'w3', 'w4']  (expected ['w0','w1','w2','w3','w4'])

=== asyncio.Lock is NOT reentrant (deadlock if you try) ===
  cancelled — would deadlock forever without the timeout
```

Demo A shows the stampede prevented — 5 callers, 1 upstream call. Demo B shows the Event broadcast — three workers wake on `set()` and read the cache. Demo C shows the FIFO order matches creation order. Demo D shows the reentrancy deadlock — cancelled by the timeout safety, otherwise would hang forever.

## Common Mistakes

### Mistake 1: Using `threading.Lock` in async code

```python
import threading
lock = threading.Lock()

async def get(slug):
    with lock:                          # ← blocking acquire
        ...
```

**Symptom:** The event loop freezes for the duration of every `with lock:` block — including any `await` inside it. Under load, requests start timing out and the server appears hung.

**Why:** `threading.Lock.acquire()` blocks the calling *thread* (the event loop's thread). While it blocks, no other coroutine can run — the entire loop is frozen. The asyncio Lock's `acquire` is a coroutine that yields control, so other tasks can run while one waits.

**Fix:** Use `asyncio.Lock` and `async with`:

```python
lock = asyncio.Lock()

async def get(slug):
    async with lock:
        ...
```

### Mistake 2: Forgetting the inner re-check in double-checked locking

```python
async def get(self, slug):
    if slug in self._cache:        # outside check
        return self._cache[slug]
    async with self._lock:
        # BUG: no re-check — every waiter populates the cache
        self._cache[slug] = await self._refresh(slug)
        return self._cache[slug]
```

**Symptom:** The stampede is not prevented — five concurrent calls all miss the outside check, all queue on the lock, all populate the cache in turn (each overwriting the previous), and you see 5 upstream calls instead of 1.

**Why:** The outside check ran before the lock was acquired; the state may have changed by the time the lock is held. The whole point of acquiring the lock is to re-check under exclusion.

**Fix:** Re-check inside the critical section:

```python
async def get(self, slug):
    async with self._lock:
        if slug not in self._cache:
            self._cache[slug] = await self._refresh(slug)
        return self._cache[slug]
```

### Mistake 3: Re-acquiring the same `asyncio.Lock` from the same task

```python
lock = asyncio.Lock()

async def outer():
    async with lock:
        await inner()              # tries to re-acquire

async def inner():
    async with lock:               # ← deadlock
        ...
```

**Symptom:** The task hangs forever — no exception, no progress, no log line. You discover it in production when a request times out.

**Why:** `asyncio.Lock` is not reentrant. The second `acquire` waits for the first to release, which can't happen because the first is blocked in `inner`. Classic deadlock.

**Fix:** Restructure so `inner` doesn't need to acquire the lock — pass the already-locked data as an argument:

```python
async def outer():
    async with lock:
        data = self._cache[...]
        await inner(data)          # no lock needed

async def inner(data):
    ...
```

## Engineering Trade-Offs

**Decision:** Use `asyncio.Lock` for short critical sections where only one task should be inside at a time. Use `asyncio.Event` for one-to-many broadcast signals. Use double-checked locking when the value being guarded is expensive to compute and the cache hit rate is high.

**Both sides:** The alternative to a Lock is a single-writer task that owns the state and accepts commands via an `asyncio.Queue` (covered in the next lesson). The Queue pattern is more scalable (no lock contention, the writer can batch) but more verbose (every operation is a queue round-trip). For a tiny hot-path cache, the Lock wins — the overhead is microseconds and the code is direct. For a high-throughput shared mutable state (a boardly background job queue with thousands of items per second), the Queue pattern wins.

**Commitment:** `boardly` uses `asyncio.Lock` for the in-process `ProjectCache` (the demo in this lesson), the connection-count counter in the DB pool (lesson 04), and the per-tenant rate-limiter token bucket. `asyncio.Event` is used in two places: the "cache primed" signal in `ProjectCache`, and the "shutdown requested" signal in the worker pool — workers `await shutdown_event.wait()` to exit cleanly. For the high-throughput background job queue, `boardly` uses `asyncio.Queue` (next lesson) — no Lock, no shared mutable state, one writer.

**Why not always use `asyncio.Event` instead of `asyncio.Lock`?** Because they solve different problems. An Event is "broadcast" — one setter, N waiters, no exclusion. A Lock is "exclusion" — only one task in the critical section. Using an Event for exclusion would require every waiter to acquire a Lock after the Event fires, which is just Lock + Event glued together — more complex and slower than using a Lock alone. Use the right primitive for the right problem.

## Exercises

1. **Exercise 1 — Remove the inner re-check.** In `ProjectCache.get`, delete the `if slug not in self._cache:` line inside the `async with self._lock:` block. Re-run the stampede demo. Confirm `refresh_calls` is now 5, not 1. `Verify: uv run python boardly/asyncio_lock_event_demo.py`

2. **Exercise 2 — Add a `clear()` call.** After `prime_initial_set`, add `cache._primed.clear()` and re-run. Confirm the workers do not re-wake (because the Event was already consumed) — `clear()` only affects future `wait()` callers. `Verify: uv run python boardly/asyncio_lock_event_demo.py`

3. **Exercise 3 — Measure lock contention.** Replace the 30ms DB call with a 0ms call (`await asyncio.sleep(0)`) and increase the concurrency to 1000. Time the `gather`. Confirm the FIFO queue serialises the work and the wall time scales linearly. `Verify: uv run python boardly/asyncio_lock_event_demo.py`

4. **Exercise 4 — Replace the Lock with a Queue.** Refactor `ProjectCache` so the cache lives inside a single-writer task and `get` sends a `(slug, future)` pair on a queue. Confirm the result is the same but the cache no longer needs a Lock. `Verify: uv run python boardly/asyncio_lock_event_demo.py`

5. **Exercise 5 — Add a per-slug Lock.** Instead of one Lock for the whole cache, use a `dict[str, asyncio.Lock]` (one lock per slug). Confirm that concurrent gets for *different* slugs no longer serialise. `Verify: uv run python boardly/asyncio_lock_event_demo.py`

## Verification

```bash
$ uv run python boardly/asyncio_lock_event_demo.py
=== Lock prevents a stampede ===
  results: ['Alpha', 'Alpha', 'Alpha', 'Alpha', 'Alpha']
  upstream calls: 1 (expected 1)

=== Event wakes N waiters at once ===
  priming cache...
  results: ['alpha -> Alpha', 'beta -> Beta', 'gamma -> Gamma']

=== Lock is FIFO fair (3.10+) ===
  acquisition order: ['w0', 'w1', 'w2', 'w3', 'w4']  (expected ['w0','w1','w2','w3','w4'])

=== asyncio.Lock is NOT reentrant (deadlock if you try) ===
  cancelled — would deadlock forever without the timeout
```

## Previously Learned Here

- [[21-asyncio-primitives/01-Task-gather-wait_for]] — `create_task` and `gather` are how you get the N concurrent tasks that this lesson's Lock co-ordinates. Without concurrency you do not need a Lock.
- [[03-contextlib/02-asynccontextmanager]] — the `async with` protocol that `asyncio.Lock` uses. `async with lock:` is `await lock.__aenter__()` / `await lock.__aexit__(*exc_info)`, identical to `async with` on an `@asynccontextmanager`-wrapped function.

## What's Next

[[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] — the producer-consumer pattern. `asyncio.Queue(maxsize=N)` is a bounded async channel between producer and consumer tasks; `await q.put(item)` blocks when full (backpressure), `await q.get()` blocks when empty, `q.task_done()` decrements the unfinished-tasks counter, `await q.join()` waits for the counter to hit zero. And the 3.13+ `q.shutdown()` method, which immediately closes the queue and makes pending `get()` raise `QueueShutDown` — version-gated because the 3.12 runtime does not have it.

- `asyncio.Queue(maxsize=0)` — bounded vs unbounded.
- `put` / `get` / `put_nowait` / `get_nowait` / `join` / `task_done`.
- The producer-consumer pattern with one sentinel per consumer.
- The 3.13+ `Queue.shutdown()` and `QueueShutDown` exception.

## Sources

- **`asyncio` — Synchronization Primitives** — https://docs.python.org/3.12/library/asyncio-sync.html — accessed 2026-10-23 — the canonical reference for `Lock`, `Event`, `Semaphore`, `Condition`, and the FIFO fairness guarantee (3.10+).
- **`asyncio` — Synchronization Primitives: Locks** — https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Lock — accessed 2026-10-23 — the `Lock` reference, including the "not a `threading.Lock`" note and the no-reentrancy rule.
- **`asyncio` — Synchronization Primitives: Events** — https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Event — accessed 2026-10-23 — the `Event` reference, including `set`/`clear`/`is_set`/`wait`.
- **PEP 537 — new asyncio synchronization primitives** — https://peps.python.org/pep-0537/ — accessed 2026-10-23 — historical context for the 3.10 FIFO fairness guarantee.

## What We Learned

- You can use `asyncio.Lock` for async mutual exclusion via `async with lock:`.
- You can state the FIFO fairness guarantee (3.10+) and explain why it matters for backpressure.
- You can explain the "not reentrant" rule and the deadlock trap it sets.
- You can use `asyncio.Event` for one-to-many broadcast via `set`/`clear`/`wait`.
- You can contrast `asyncio.Lock` with `threading.Lock` — the asyncio Lock is awaitable and lives on the loop, the threading Lock blocks the thread.
- You can implement double-checked locking to prevent the cache stampede.
