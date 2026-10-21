---
title: "Lesson 04: Semaphore and Condition"
aliases:
 - asyncio.Semaphore
 - asyncio.Condition
 - bounded concurrency
 - DB pool pattern
tags:
 - asyncio
 - python-stdlib
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]]"
related_lessons:
 - "[[21-asyncio-primitives/02-Lock-and-Event]]"
 - "[[21-asyncio-primitives/05-to_thread-and-run-in-executor]]"
first_taught_in: "21-asyncio-primitives/04-Semaphore-and-Condition"
---

# Lesson 04: `Semaphore` and `Condition`

*`asyncio.Semaphore(value=N)` for capacity control — limit to N concurrent DB connections, no matter how many tasks want in — and `asyncio.Condition` for the wait/notify pattern.*

**You're at the very beginning of Section 21, four lessons in.**

You can run N tasks concurrently. You can co-ordinate them with a `Lock` and an `Event`. You can wire up a producer-consumer pipeline with a `Queue`. The remaining primitives are `Semaphore` and `Condition` — `Semaphore` for "I have N slots and want to limit concurrent access to N" (the bounded-concurrency pattern, the DB pool of 10 connections), and `Condition` for the wait/notify pattern (one task waits, another notifies one or all). Both have `threading` siblings with the same names; both behave differently enough that you must reach for the asyncio version in async code. By the end of this lesson you will know both, plus the trap that `Semaphore(1)` is *not* a substitute for `Lock` (release-without-acquire is silently wrong on a Semaphore and loudly wrong on a Lock). Take your time. Type every example. **This is how you learn.**

#asyncio #semaphore #condition

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `asyncio.Semaphore(value=N)` for capacity control** — `async with sem:` limits concurrent access to N; the (N+1)th task blocks until one of the first N releases.
2. **Implement the bounded-concurrency pattern** — a `DbPool` with N connections, where `async with sem:` enforces the cap regardless of how many tasks call `pool.query(...)`.
3. **State why `Semaphore(1)` is *not* a substitute for `Lock`** — `Semaphore` allows release-without-acquire (silently increments the counter); `Lock` raises `RuntimeError` on the same call.
4. **Use `asyncio.Condition` for wait/notify** — `async with cond: await cond.wait()` blocks; `cond.notify(n=1)` wakes one waiter; `cond.notify_all()` wakes every waiter.
5. **Contrast `asyncio.Condition` with `threading.Condition`** — the asyncio version is awaitable and lives on the loop; the threading version blocks the thread.

## Prerequisites

Before starting, you need:

- **`asyncio.Lock` and `asyncio.Event`** — [[21-asyncio-primitives/02-Lock-and-Event]]. `Semaphore` is a generalisation of `Lock` (capacity 1) and `Condition` is `Event` + `Lock` combined. Both make sense only after you understand the simpler primitives.
- **`asyncio.Queue`** — [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]]. The Queue pattern (producer-consumer) is the alternative to the bounded-concurrency Semaphore pattern; knowing when each wins is the senior question.
- **About 30–40 minutes of focused time.**

**The most common gap: confusing `Semaphore` and `Lock`.**

A `Semaphore(1)` looks like a `Lock` — it has `acquire`/`release`, `async with sem:` works the same way. The difference is the semantics: a `Lock` is *exclusive* (the holder must be the one to release; release-without-acquire is an error), a `Semaphore` is *counting* (any task can release at any time; release-without-acquire just increments the counter, no error). The trap: you write `Semaphore(1)` thinking it's a `Lock`, ship it, and a buggy caller that releases twice makes the "lock" suddenly allow two concurrent holders — and you have a race condition that is impossible to reproduce in development because the buggy caller only fires in production under a specific load pattern. The fix is to use `Lock` when you mean exclusion; use `Semaphore` when you mean capacity (a pool of N, where any task can return a slot to the pool).

## The Problem

Here is the bounded-concurrency bug, in its native habitat.

```python
# boardly/db/pool.py — the unbounded version
class DbPool:
    async def query(self, slug):
        return await fetch_project(slug)        # ← no concurrency limit

async def handler():
    pool = DbPool()
    # 100 concurrent queries — all hit the DB at the same instant.
    # The DB allows 10 connections; the 11th gets "pool exhausted".
    await asyncio.gather(*[pool.query(s) for s in slugs])
```

100 concurrent `pool.query` calls all run at the same instant. The downstream DB has 10 connection slots. The 11th caller gets a "pool exhausted" error from the DB; the 12th gets the same; and so on. The DB has effectively become a serialisation point — not because the work is slow, but because the connection limit is enforced downstream and you are not enforcing it upstream.

The fix is `asyncio.Semaphore(value=10)`: `async with sem:` limits concurrent access to 10. The first 10 callers acquire immediately; the 11th blocks until one of the first 10 releases. The downstream DB sees at most 10 concurrent connections, no "pool exhausted" errors, and the 11th caller proceeds as soon as a slot frees up. This is the canonical bounded-concurrency pattern.

The other pattern this lesson covers is `Condition`: one task waits for a state change, another task makes the change and notifies. The boardly use is a small in-process event log where a producer publishes updates and consumers block on `await cond.wait()` until a producer calls `cond.notify_all()`. The `Event` would work for one-shot signals; the `Condition` wins for repeated state changes because the producer can `notify_all()` repeatedly and each call wakes the current waiters.

## The Code

```python
# boardly/asyncio_semaphore_condition_demo.py
"""asyncio.Semaphore and asyncio.Condition on boardly.

Semaphore = capacity control. The boardly use: a pool of N DB connections;
every outbound query acquires one slot via `async with sem:` so we never
exceed the limit. Condition = the wait/notify pattern: a producer publishes
new data and notifies one or all waiters.

Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class Project:
    slug: str


# --- Pattern A: Semaphore for bounded concurrency (DB pool) ---
class DbPool:
    """A bounded pool of N connections; Semaphore enforces the cap."""

    def __init__(self, capacity: int) -> None:
        self._sem = asyncio.Semaphore(value=capacity)
        self._active = 0
        self._peak = 0

    async def query(self, slug: str) -> Project:
        async with self._sem:               # acquire a slot (blocks if all in use)
            self._active += 1
            self._peak = max(self._peak, self._active)
            await asyncio.sleep(0.02)        # simulate DB round-trip
            self._active -= 1
            return Project(slug=slug)

    @property
    def peak(self) -> int:
        return self._peak


async def bounded_concurrency_demo() -> None:
    print("=== Semaphore bounds concurrent DB queries ===")
    pool = DbPool(capacity=3)                # only 3 connections
    # 10 concurrent queries — without the Semaphore, all 10 would hit the DB
    # at the same instant. With it, only 3 are active at any moment.
    tasks = [asyncio.create_task(pool.query(f"p{i}")) for i in range(10)]
    results = await asyncio.gather(*tasks)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")
    print(f"  peak concurrency: {pool.peak} (capped at 3)")


# --- Pattern B: Semaphore(value=1) is NOT a Lock (semantics differ) ---
async def semaphore_vs_lock_demo() -> None:
    print("\n=== Semaphore(1) is NOT a Lock (release-without-acquire) ===")
    sem = asyncio.Semaphore(value=1)
    # Lock would raise RuntimeError("release unlocked lock"); Semaphore just
    # increments its internal counter. So Semaphore(1) lets a buggy caller
    # 'release' without acquiring — and a second task can then acquire it
    # concurrently with the first.
    sem.release()                          # release without acquire
    async with sem:                        # acquires (counter goes 2 -> 1)
        print("  inside sem: counter would be 1 (should be 0 for a Lock)")
    # Use asyncio.Lock when you need mutual-exclusion semantics. Use a
    # Semaphore when you mean capacity (e.g. a pool of N connections).


# --- Pattern C: Condition — notify_one / notify_all / wait ---
async def condition_demo() -> None:
    print("\n=== Condition: notify_one / notify_all / wait ===")
    cond = asyncio.Condition()
    state: dict[str, str] = {"status": "init"}

    async def waiter(name: str) -> None:
        async with cond:                    # MUST hold the lock to wait
            await cond.wait()               # releases the lock while waiting
            print(f"  {name} woke up; status={state['status']!r}")

    async def producer() -> None:
        await asyncio.sleep(0.01)            # let waiters queue first
        async with cond:
            state["status"] = "ready"
            cond.notify_all()                # wake every waiter
            print("  producer: notify_all() sent")

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(3)]
    await producer()
    await asyncio.gather(*waiters)


# --- Pattern D: notify_one wakes exactly one waiter ---
async def notify_one_demo() -> None:
    print("\n=== notify_one wakes exactly one waiter ===")
    cond = asyncio.Condition()
    woke: list[str] = []

    async def waiter(name: str) -> None:
        async with cond:
            await cond.wait()
            woke.append(name)

    async def producer(n: int) -> None:
        await asyncio.sleep(0.01)
        async with cond:
            for _ in range(n):
                cond.notify(1)               # wake one waiter at a time

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(4)]
    await producer(2)                        # only 2 of the 4 will be woken
    await asyncio.sleep(0.01)
    print(f"  woke: {woke} (notify_one called twice; 2 waiters left blocked)")
    for w in waiters:
        if not w.done():
            w.cancel()
            try:
                await w
            except asyncio.CancelledError:
                pass


async def main() -> None:
    await bounded_concurrency_demo()
    await semaphore_vs_lock_demo()
    await condition_demo()
    await notify_one_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–13: Imports and the `Project` model

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class Project:
    slug: str
```

`asyncio` brings `Semaphore` and `Condition`. The `Project` model is minimal here — `slug` is the only field we need to track which project a query returned.

### Lines 16–34: Pattern A — the `DbPool` with a `Semaphore`

```python
class DbPool:
    """A bounded pool of N connections; Semaphore enforces the cap."""

    def __init__(self, capacity: int) -> None:
        self._sem = asyncio.Semaphore(value=capacity)
        self._active = 0
        self._peak = 0

    async def query(self, slug: str) -> Project:
        async with self._sem:               # acquire a slot (blocks if all in use)
            self._active += 1
            self._peak = max(self._peak, self._active)
            await asyncio.sleep(0.02)        # simulate DB round-trip
            self._active -= 1
            return Project(slug=slug)

    @property
    def peak(self) -> int:
        return self._peak
```

`asyncio.Semaphore(value=capacity)` creates the semaphore with an internal counter set to `capacity`. Each `async with sem:` decrements the counter on entry (or blocks if the counter is 0) and increments it on exit. So with `capacity=3`, the first three `query` calls proceed immediately; the fourth blocks until one of the first three exits the `async with` block.

The `_active`/`_peak` bookkeeping is here to make the demo observable — the trace shows the peak concurrency hit 3, not 10. In production you would not keep these counters; you would use metrics (Prometheus, etc.).

**Why `Semaphore(value=capacity)` and not a `Queue(maxsize=capacity)`?** Because the Semaphore pattern says "I have N slots; whoever wants one grabs it, runs, releases it" — the workers are stateless and interchangeable. The Queue pattern says "I have a queue of work items; whoever is free grabs the next item" — the work items are stateful and ordered. The Semaphore is right when the bottleneck is downstream capacity (a DB pool of N); the Queue is right when the bottleneck is item-level ordering (a job queue with dependencies). For the boardly DB pool, the Semaphore is the right choice — every query is independent, and we only care about not exceeding the connection limit.

### Lines 37–44: Pattern A — the bounded-concurrency demo

```python
async def bounded_concurrency_demo() -> None:
    print("=== Semaphore bounds concurrent DB queries ===")
    pool = DbPool(capacity=3)                # only 3 connections
    # 10 concurrent queries — without the Semaphore, all 10 would hit the DB
    # at the same instant. With it, only 3 are active at any moment.
    tasks = [asyncio.create_task(pool.query(f"p{i}")) for i in range(10)]
    results = await asyncio.gather(*tasks)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")
    print(f"  peak concurrency: {pool.peak} (capped at 3)")
```

10 `create_task` calls schedule 10 concurrent `pool.query` calls. Without the Semaphore, all 10 would start at the same instant and the DB would see 10 concurrent connections (and reject the 11th). With the Semaphore, only 3 run at any moment — the first 3 proceed, the next 7 queue, and as each of the first 3 finishes, the next waiter acquires the slot. The `pool.peak` ends up at 3, the cap.

The total wall-clock time: 10 queries at 20ms each, 3 concurrent, so ~4 batches of 3 ≈ 80ms (plus overhead). Without the Semaphore, the same 10 queries would run in ~20ms — much faster, but the DB would have rejected 7 of them. The Semaphore trades wall-clock time for downstream protection.

**Why is the Semaphore FIFO fair?** For the same reason `asyncio.Lock` is FIFO fair (3.10+): the asyncio primitives guarantee no starvation. A steady stream of callers cannot starve one unlucky task — the waiters are queued in arrival order. (The 3.10+ fairness guarantee from [[21-asyncio-primitives/02-Lock-and-Event]] applies to `Semaphore` too.)

### Lines 47–55: Pattern B — `Semaphore(1)` is NOT a `Lock`

```python
async def semaphore_vs_lock_demo() -> None:
    print("\n=== Semaphore(1) is NOT a Lock (release-without-acquire) ===")
    sem = asyncio.Semaphore(value=1)
    # Lock would raise RuntimeError("release unlocked lock"); Semaphore just
    # increments its internal counter. So Semaphore(1) lets a buggy caller
    # 'release' without acquiring — and a second task can then acquire it
    # concurrently with the first.
    sem.release()                          # release without acquire
    async with sem:                        # acquires (counter goes 2 -> 1)
        print("  inside sem: counter would be 1 (should be 0 for a Lock)")
    # Use asyncio.Lock when you need mutual-exclusion semantics. Use a
    # Semaphore when you mean capacity (e.g. a pool of N connections).
```

The demo creates a `Semaphore(1)` — the value is 1, which superficially matches a `Lock` (one holder at a time). It then calls `sem.release()` *without acquiring first*. On a `Lock`, this would raise `RuntimeError("release unlocked lock")`; on a `Semaphore`, it silently increments the counter to 2. The next `async with sem:` acquires (counter goes 2 -> 1) — and now there are "two slots" in a Semaphore that was supposed to have one.

This is the trap. A buggy caller (or a bug in your own code) that releases a `Semaphore(1)` twice will silently allow two concurrent holders — exactly the failure mode you were trying to prevent by using the primitive. A `Lock` would have raised; the `Semaphore` stays silent.

**Why does `Semaphore` allow release-without-acquire?** Because the Semaphore's mental model is "a pool of N tokens" — you acquire a token to use a resource, you return the token when done. The pool does not care who returned the token; it just increments the counter. A real-world pool (a connection pool, a parking lot, a checkout queue at the grocery store) does not enforce "you must be the one who took this token to return it" — anyone can drop a token back in. The `Lock`'s mental model is different: "I hold the lock; only I can release it" — like a bathroom stall, the lock is exclusive to the holder. The two models are not interchangeable, even when N=1.

### Lines 58–76: Pattern C — `Condition` with `notify_all`

```python
async def condition_demo() -> None:
    print("\n=== Condition: notify_one / notify_all / wait ===")
    cond = asyncio.Condition()
    state: dict[str, str] = {"status": "init"}

    async def waiter(name: str) -> None:
        async with cond:                    # MUST hold the lock to wait
            await cond.wait()               # releases the lock while waiting
            print(f"  {name} woke up; status={state['status']!r}")

    async def producer() -> None:
        await asyncio.sleep(0.01)            # let waiters queue first
        async with cond:
            state["status"] = "ready"
            cond.notify_all()                # wake every waiter
            print("  producer: notify_all() sent")

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(3)]
    await producer()
    await asyncio.gather(*waiters)
```

`asyncio.Condition()` creates the condition variable. It wraps a `Lock` internally (you can pass a custom `lock` argument, but it must be an asyncio `Lock`). The pattern is:

1. **The waiter** acquires the lock (`async with cond:`), then calls `await cond.wait()`. The `wait()` *releases the lock* while it blocks, so other tasks can acquire it (to call `notify`); when `wait()` is woken by a notify, it *re-acquires the lock* before returning. The waiter is holding the lock the entire time — except during the `wait()` itself.
2. **The producer** acquires the lock, mutates the shared state, calls `cond.notify_all()` (or `notify(n=1)`), then releases the lock. The notify wakes the waiters; they re-acquire the lock one at a time (FIFO fair), read the new state, and proceed.

The `await asyncio.sleep(0.01)` in the producer is the yield that lets the waiters reach `await cond.wait()` before the producer calls `notify_all()`. Without it, the producer would notify before anyone was waiting, and the notify would wake nobody.

**Why must the waiter hold the lock to call `wait()`?** Because the wait/notify protocol requires atomicity between "check the state" and "wait". Without the lock, you would have a race: the waiter checks the state, sees "init", decides to wait — and in the gap between check and wait, the producer mutates the state to "ready" and notifies (which wakes nobody, because the waiter hasn't started waiting yet). The waiter then blocks forever on `wait()`, missing the notify. The lock makes "check state, decide to wait, register as waiter" atomic — the producer cannot notify between the check and the registration because the producer cannot acquire the lock to call notify. This is the classic condition-variable protocol, identical in `threading.Condition` and `asyncio.Condition`.

### Lines 79–99: Pattern D — `notify(n=1)` wakes exactly one waiter

```python
async def notify_one_demo() -> None:
    print("\n=== notify_one wakes exactly one waiter ===")
    cond = asyncio.Condition()
    woke: list[str] = []

    async def waiter(name: str) -> None:
        async with cond:
            await cond.wait()
            woke.append(name)

    async def producer(n: int) -> None:
        await asyncio.sleep(0.01)
        async with cond:
            for _ in range(n):
                cond.notify(1)               # wake one waiter at a time

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(4)]
    await producer(2)                        # only 2 of the 4 will be woken
    await asyncio.sleep(0.01)
    print(f"  woke: {woke} (notify_one called twice; 2 waiters left blocked)")
    for w in waiters:
        if not w.done():
            w.cancel()
            try:
                await w
            except asyncio.CancelledError:
                pass
```

`cond.notify(1)` wakes exactly one waiter (the default; you can write `notify()` without args). `cond.notify_all()` wakes every waiter. The choice is "wake one, let the others stay blocked" vs "wake everyone, let them compete for the lock".

The demo creates 4 waiters, calls `notify(1)` twice — so 2 waiters wake up and 2 stay blocked. The trace shows `woke: ['w0', 'w1']` — the first two in queue order (FIFO fair, same as `Lock` and `Semaphore`). The remaining 2 are cancelled by the cleanup loop at the end (`for w in waiters: if not w.done(): w.cancel()`).

**Why `notify(n=1)` instead of `notify_all()`?** When one notify is enough — e.g. "I added one item to a queue, wake one consumer to process it". `notify_all()` would wake every consumer; only one would find the item, the others would re-check the state, see nothing, and re-wait. Wasted wakeups. `notify(1)` is the right choice for "one item, one consumer". For "state changed, anyone interested should re-check", `notify_all()` is the right choice — you do not know which waiter cares about the change, so wake all.

### Lines 102–107: `main` and the entrypoint

```python
async def main() -> None:
    await bounded_concurrency_demo()
    await semaphore_vs_lock_demo()
    await condition_demo()
    await notify_one_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

Four demos run sequentially. The `DbPool` and `Condition` instances are fresh per demo.

## Execution Trace

```bash
$ uv run python boardly/asyncio_semaphore_condition_demo.py
=== Semaphore bounds concurrent DB queries ===
  10 projects: ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9']
  peak concurrency: 3 (capped at 3)

=== Semaphore(1) is NOT a Lock (release-without-acquire) ===
  inside sem: counter would be 1 (should be 0 for a Lock)

=== Condition: notify_one / notify_all / wait ===
  producer: notify_all() sent
  w0 woke up; status='ready'
  w1 woke up; status='ready'
  w2 woke up; status='ready'

=== notify_one wakes exactly one waiter ===
  woke: ['w0', 'w1'] (notify_one called twice; 2 waiters left blocked)
```

Demo A shows the peak concurrency capped at 3 — the bound is enforced. Demo B shows the `Semaphore(1)` silently accepting a release-without-acquire (no `RuntimeError`). Demo C shows `notify_all()` waking all three waiters in queue order. Demo D shows `notify(1)` waking exactly two waiters, leaving two blocked (then cancelled).

## Common Mistakes

### Mistake 1: Using `Semaphore(1)` as a `Lock`

```python
sem = asyncio.Semaphore(1)

async def get(slug):
    async with sem:
        ...
        sem.release()  # ← bug: double-release; now the "lock" allows 2 holders
```

**Symptom:** Concurrency appears correct in tests; in production under specific load patterns, a buggy caller releases twice, the counter becomes 2, and two tasks end up in the "critical section" simultaneously — a race condition that is impossible to reproduce in development.

**Why:** `Semaphore` allows release-without-acquire silently; the counter just goes up.

**Fix:** Use `asyncio.Lock` when you mean exclusion. Use `Semaphore` only when you mean capacity (a pool of N, where any task can return a slot).

### Mistake 2: Calling `cond.wait()` without holding the lock

```python
cond = asyncio.Condition()

async def waiter():
    await cond.wait()       # ← RuntimeError: no lock held
```

**Symptom:** `RuntimeError: cannot wait on un-acquired lock` raised on the `wait()` call.

**Why:** The condition-variable protocol requires the lock to be held during `wait()` (so the wait/notify is atomic). The `wait()` releases the lock while it blocks, but you must hold it before calling `wait()`.

**Fix:** Acquire the lock first:

```python
async def waiter():
    async with cond:
        await cond.wait()
```

### Mistake 3: Notifying before any waiter is queued

```python
async def producer():
    async with cond:
        state["x"] = "ready"
        cond.notify_all()       # ← no waiters yet; notify is a no-op

async def waiter():
    async with cond:
        await cond.wait()       # ← blocks forever
```

**Symptom:** The waiter hangs forever — the notify fired before it started waiting, so it missed the wake-up.

**Why:** `notify` is not a flag — it is a one-shot signal. It wakes *currently-blocked* waiters only; it does not queue for future waiters.

**Fix:** Either ensure the waiters start first (e.g. `await asyncio.sleep(0)` to yield before notifying), or use `asyncio.Event` for a state-based signal (`set()` is sticky — future `wait()` calls return immediately).

## Engineering Trade-Offs

**Decision:** Use `Semaphore(value=N)` for bounded concurrency (a pool of N downstream resources). Use `Condition` for the wait/notify pattern with repeated state changes. Use `Lock` (not `Semaphore(1)`) when you mean exclusion.

**Both sides:** The alternative to a Semaphore for bounded concurrency is a `Queue` (covered in [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]]): each "slot" is a token in the queue; acquire is `await q.get()`; release is `await q.put(token)`. The Queue pattern is more verbose but observable (you can `q.qsize()` and see the queue depth). The Semaphore pattern is more direct (one line `async with sem:`) but opaque (no introspection on the counter). For a downstream connection pool, the Semaphore is the right choice — the slots are interchangeable and the bottleneck is downstream capacity. For a job queue, the Queue is the right choice — the jobs are distinct items, and you want backpressure.

The alternative to `Condition` is `Event` ([[21-asyncio-primitives/02-Lock-and-Event]]). `Event` is simpler — `set()` is sticky, every `wait()` returns immediately if already set. `Condition` is more powerful — `notify()` is one-shot, you can wake one or all, and the wait/notify is atomic under the lock. For one-shot "ready" signals, `Event` wins; for repeated state changes (a producer publishes, consumers wait, producer publishes again), `Condition` wins.

**Commitment:** `boardly` uses `asyncio.Semaphore(value=10)` for the outbound HTTP client pool — at most 10 concurrent requests to a downstream service, regardless of how many tasks want to call. `asyncio.Condition()` is used in two places: the in-process event log (a producer publishes, N consumers wait) and the "shutdown requested" pattern (a `Condition` is `notify_all()`-ed on shutdown; tasks blocked on `await cond.wait()` for shutdown wake up and exit). `Lock` (not `Semaphore(1)`) is used everywhere exclusion is the intent — the cache, the counter, the rate-limiter.

**Why not use `asyncio.Semaphore` for the rate-limiter?** Because the rate-limiter is a time-based pattern (N requests per second), not a concurrency pattern (N concurrent at a time). A `Semaphore` limits concurrency, not rate. For rate-limiting, you need a token bucket (a `Lock`-guarded counter that resets on a timer); the `Semaphore` is the wrong abstraction.

## Exercises

1. **Exercise 1 — Increase `capacity`.** Change `DbPool(capacity=3)` to `DbPool(capacity=10)`. Re-run. Confirm the peak concurrency is now 10 (all 10 queries run concurrently). `Verify: uv run python boardly/asyncio_semaphore_condition_demo.py`

2. **Exercise 2 — Verify `Semaphore(1)` release-without-acquire.** In `semaphore_vs_lock_demo`, replace the `Semaphore` with a `Lock` and call `lock.release()` without acquiring. Confirm `RuntimeError: cannot release un-acquired lock` is raised. `Verify: uv run python boardly/asyncio_semaphore_condition_demo.py`

3. **Exercise 3 — Time the bounded vs unbounded.** Replace `async with self._sem:` in `DbPool.query` with a bare `await asyncio.sleep(0.02)` (no Semaphore). Time the 10-query gather. Confirm the unbounded version is ~3× faster but would hit the downstream connection limit. `Verify: uv run python boardly/asyncio_semaphore_condition_demo.py`

4. **Exercise 4 — Use `Event` instead of `Condition`.** Refactor `condition_demo` to use `asyncio.Event`. Confirm the same observable behaviour. Note the `Event.set()` is sticky — a second waiter that starts after `set()` returns immediately. `Verify: uv run python boardly/asyncio_semaphore_condition_demo.py`

5. **Exercise 5 — Build a token-bucket rate-limiter.** Write a `RateLimiter(rate_per_second: int)` that uses a `Lock`-guarded counter and an asyncio timer to refill tokens. Confirm that N concurrent calls to `await rl.acquire()` block when the bucket is empty. `Verify: uv run python boardly/asyncio_semaphore_condition_demo.py`

## Verification

```bash
$ uv run python boardly/asyncio_semaphore_condition_demo.py
=== Semaphore bounds concurrent DB queries ===
  10 projects: ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9']
  peak concurrency: 3 (capped at 3)

=== Semaphore(1) is NOT a Lock (release-without-acquire) ===
  inside sem: counter would be 1 (should be 0 for a Lock)

=== Condition: notify_one / notify_all / wait ===
  producer: notify_all() sent
  w0 woke up; status='ready'
  w1 woke up; status='ready'
  w2 woke up; status='ready'

=== notify_one wakes exactly one waiter ===
  woke: ['w0', 'w1'] (notify_one called twice; 2 waiters left blocked)
```

## Previously Learned Here

- [[21-asyncio-primitives/02-Lock-and-Event]] — `Lock` and `Event` are the simpler siblings. `Semaphore` is a generalisation of `Lock` (capacity 1 is superficially equivalent — but the semantics differ, see Pattern B). `Condition` is `Event` + `Lock` combined, with the wait/notify protocol under the lock.
- [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] — `Queue` is the alternative to `Semaphore` for bounded concurrency. The Queue pattern is item-based (jobs); the Semaphore pattern is slot-based (downstream capacity).

## What's Next

[[21-asyncio-primitives/05-to_thread-and-run-in-executor]] — `asyncio.to_thread(func, *args, **kwargs)` (3.9+) is the canonical way to call blocking sync code from async — `requests.get`, `time.sleep`, file I/O on a slow disk. `loop.run_in_executor(executor, func, *args)` is the lower-level form. And the rule: don't call `requests.get` in async — use `to_thread` (offload to a thread) or `httpx.AsyncClient` (use a real async HTTP client). The default `ThreadPoolExecutor` has `max_workers = min(32, os.cpu_count() + 4)` since 3.8 — version-gated because the formula is a 3.8 commitment.

- `asyncio.to_thread` — the canonical 3.9+ form.
- `loop.run_in_executor` — the lower-level form.
- The "don't call `requests.get` in async" rule.
- The default `ThreadPoolExecutor` and the `min(32, os.cpu_count() + 4)` formula.

## Sources

- **`asyncio` — Synchronization Primitives: Semaphores** — https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Semaphore — accessed 2026-10-23 — the canonical reference for `Semaphore`, including the FIFO fairness guarantee (3.10+) and the `value` parameter.
- **`asyncio` — Synchronization Primitives: Conditions** — https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Condition — accessed 2026-10-23 — the canonical reference for `Condition`, including the lock-holding requirement for `wait()` and the `notify(n=1)` / `notify_all()` semantics.
- **`asyncio` — Synchronization Primitives: Locks** — https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Lock — accessed 2026-10-23 — the `Lock` reference, for the "release unlocked lock raises `RuntimeError`" rule that distinguishes `Lock` from `Semaphore(1)`.

## What We Learned

- You can use `asyncio.Semaphore(value=N)` for capacity control via `async with sem:`.
- You can implement the bounded-concurrency pattern (a DB pool of N connections).
- You can state why `Semaphore(1)` is *not* a `Lock` (release-without-acquire silently increments; `Lock` raises `RuntimeError`).
- You can use `asyncio.Condition` for the wait/notify pattern, holding the lock while calling `wait()`.
- You can choose between `notify(n=1)` and `notify_all()` and explain when each wins.
- You can contrast `asyncio.Condition` with `threading.Condition` (awaitable, lives on the loop).
