---
title: "Lesson 03: Queue and Queue.shutdown"
aliases:
 - asyncio.Queue
 - asyncio.Queue.shutdown
 - asyncio.QueueShutDown
 - producer-consumer pattern
tags:
 - asyncio
 - python-stdlib
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[21-asyncio-primitives/02-Lock-and-Event]]"
related_lessons:
 - "[[21-asyncio-primitives/04-Semaphore-and-Condition]]"
 - "[[04-collections/03-deque]]"
first_taught_in: "21-asyncio-primitives/03-Queue-and-Queue-Shutdown"
---

# Lesson 03: `Queue` and `Queue.shutdown`

*`asyncio.Queue` is the producer-consumer channel — bounded by `maxsize` (backpressure when full), drained by `await join()` (waits for `task_done()` on every item), and immediately closed by `shutdown()` in 3.13+.*

**You're at the very beginning of Section 21, three lessons in.**

You can run N tasks concurrently, and you can co-ordinate them with a `Lock` and an `Event`. The next pattern is the producer-consumer pipeline: a producer task pushes items onto a queue, N consumer tasks pull items off, and the queue handles the backpressure and the join semantics for you. This is the right answer when you have one producer and many workers (the `boardly` background job queue), when the producer is faster than the consumers (the queue absorbs the burst), or when the consumers are slower than the producer (the `maxsize` bound stops the producer from running away with memory). By the end of this lesson you will know `asyncio.Queue(maxsize=N)`, the `put`/`get`/`put_nowait`/`get_nowait` quartet, the `task_done`/`join` pair (and the bug if you forget a `task_done`), and the 3.13+ `shutdown` method that closes a queue immediately — version-gated because the 3.12 runtime you are running does not have it. Take your time. Type every example. **This is how you learn.**

#asyncio #queue

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a bounded `asyncio.Queue(maxsize=N)`** — state that `maxsize=0` (the default) is unbounded, and `maxsize=N` blocks `put` when the queue is full (backpressure).
2. **Use the `put`/`get`/`put_nowait`/`get_nowait` quartet** — `await put(item)` blocks when full; `await get()` blocks when empty; the `*_nowait` variants raise `QueueFull` / `QueueEmpty` instead of blocking.
3. **Use `task_done()` and `await join()`** — `join` waits for the unfinished-tasks counter to hit zero; every `get` must be matched by a `task_done` or `join` hangs forever.
4. **Implement the producer-consumer pattern** — one sentinel per consumer, `join` then `gather`, no `cancel` needed.
5. **State the 3.13+ `Queue.shutdown()` semantics** — immediately closes the queue; pending `get()` raises `QueueShutDown`; `put()` raises `QueueShutDown`. Version-gated; not in 3.12.

## Prerequisites

Before starting, you need:

- **`asyncio.create_task` and `asyncio.gather`** — [[21-asyncio-primitives/01-Task-gather-wait_for]]. The producer and consumers are tasks; `gather` collects their results.
- **`asyncio.Lock` and `asyncio.Event`** — [[21-asyncio-primitives/02-Lock-and-Event]]. The `Queue` supersedes both for producer-consumer pipelines; you should know what they are *not* the right tool for.
- **`collections.deque`** — [[04-collections/03-deque]]. The `Queue` uses a `deque` internally; understanding the underlying data structure makes the API obvious.
- **About 35–45 minutes of focused time.**

**The most common gap: forgetting `task_done()` after `get()`.**

The `await q.join()` call waits for the queue's unfinished-tasks counter to reach zero. Every `await q.get()` increments that counter; every `q.task_done()` decrements it. If you `get` an item and forget to call `task_done`, the counter never reaches zero, and `join` hangs forever. This is the most common queue bug, and it is silent in development (the test passes because nothing calls `join`) and fatal in production (the shutdown path calls `join` and the process hangs on SIGTERM). The fix is mechanical: every `await q.get()` site must call `q.task_done()` in a `try`/`finally` — or, in modern Python (3.13+), you can use `q.shutdown()` to break the `join` instead.

## The Problem

Here is the producer-consumer pipeline, in its native habitat.

```python
# boardly/jobs/queue.py — the queue version
async def producer(q, tickets):
    for ticket in tickets:
        await q.put(ticket)         # blocks if the queue is full
    await q.put(None)               # sentinel: "no more work"
    # BUG: only one sentinel, but there are 4 consumers — 3 of them hang forever

async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break                   # ← this consumer exits; the others never see None
        await process(item)
        q.task_done()               # ← only called for non-sentinel items
```

The single sentinel works for one consumer. With multiple consumers, the first consumer to see the sentinel exits; the others block forever on `await q.get()` because there are no more items and no more sentinels. The fix is "one sentinel per consumer": the producer pushes N `None` sentinels for N consumers, each consumer sees exactly one and exits. Then `await q.join()` waits for every `task_done()` to land (one per item + one per sentinel), and `await asyncio.gather(*consumers)` returns their processed counts.

The other failure mode is the `task_done()`-less `get`:

```python
async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            q.task_done()           # matched
            break
        await process(item)
        # BUG: forgot q.task_done() — the join hangs forever
```

The `task_done()` after `process` is what decrements the counter; without it, `join` hangs. Both bugs are silent in development and loud in production. This lesson shows the correct pattern, the sentinel-per-consumer rule, and the 3.13+ `shutdown()` escape hatch.

## The Code

```python
# boardly/asyncio_queue_demo.py
"""asyncio.Queue on boardly: the producer-consumer pattern, with join/task_done,
maxsize backpressure, and the *_nowait variants. The 3.13+ Queue.shutdown()
method is version-gated inline (it does not exist on the 3.12 runtime).
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass


@dataclass
class Ticket:
    id: int
    title: str


# --- Pattern A: bounded producer-consumer with maxsize backpressure ---
async def producer(q: asyncio.Queue[Ticket | None], n: int, n_consumers: int) -> None:
    for i in range(n):
        ticket = Ticket(id=i, title=f"ticket-{i}")
        await q.put(ticket)              # blocks if the queue is full
        print(f"  [producer] put {ticket.id}")
    # One sentinel per consumer: when a consumer sees None, it exits.
    for _ in range(n_consumers):
        await q.put(None)
    print("  [producer] done")


async def consumer(q: asyncio.Queue[Ticket | None], name: str) -> int:
    processed = 0
    while True:
        ticket = await q.get()
        if ticket is None:              # sentinel -> exit
            q.task_done()
            break
        print(f"  [consumer {name}] got {ticket.id} ({ticket.title})")
        await asyncio.sleep(0.005)      # simulate work
        q.task_done()                   # decrement the unfinished counter
        processed += 1
    return processed


async def producer_consumer_demo() -> None:
    print("=== bounded producer-consumer (maxsize=3, 2 consumers) ===")
    q: asyncio.Queue[Ticket | None] = asyncio.Queue(maxsize=3)
    prod = asyncio.create_task(producer(q, 6, n_consumers=2))
    cons1 = asyncio.create_task(consumer(q, "A"))
    cons2 = asyncio.create_task(consumer(q, "B"))
    await prod
    await q.join()                     # waits for every task_done() to land
    # Both consumers see their sentinel and exit on their own — no cancel needed.
    results = await asyncio.gather(cons1, cons2)
    print(f"  processed: A={results[0]}, B={results[1]}")


# --- Pattern B: the *_nowait variants (raise instead of block) ---
async def nowait_demo() -> None:
    print("\n=== put_nowait / get_nowait ===")
    q: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
    q.put_nowait(1)                    # ok, queue had room
    try:
        q.put_nowait(2)                # queue full -> QueueFull
    except asyncio.QueueFull as e:
        print(f"  put_nowait raised: {type(e).__name__}")
    print(f"  get_nowait -> {q.get_nowait()}")   # ok, queue had an item
    try:
        q.get_nowait()                 # queue empty -> QueueEmpty
    except asyncio.QueueEmpty as e:
        print(f"  get_nowait raised: {type(e).__name__}")


# --- Pattern C: q.join() needs every get() to be matched by a task_done() ---
async def join_without_task_done_demo() -> None:
    print("\n=== join() waits for task_done() (and the bug if you forget) ===")
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.put_nowait(2)
    _ = q.get_nowait()                  # forgot to call task_done()
    q.task_done()                       # only matched one get()
    try:
        await asyncio.wait_for(q.join(), timeout=0.1)
    except TimeoutError:
        print("  join() timed out — one task_done() missing")


# --- Pattern D: 3.13+ Queue.shutdown() (version-gated; not in 3.12) ---
async def shutdown_demo() -> None:
    print("\n=== Queue.shutdown() — Python 3.13+, version-gated ===")
    if sys.version_info < (3, 13):
        print(f"  running Python {sys.version_info[:3]} -> shutdown() not available")
        print("  (3.13+: q.shutdown() closes the queue immediately;")
        print("   pending get() raises QueueShutDown; put() raises QueueShutDown)")
        return
    # On 3.13+ this branch runs:
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.shutdown()                       # 3.13+: immediately close the queue
    try:
        await q.get()                  # already-empty + shut down
    except asyncio.QueueShutDown as e:
        print(f"  get() raised: {type(e).__name__}")


async def main() -> None:
    await producer_consumer_demo()
    await nowait_demo()
    await join_without_task_done_demo()
    await shutdown_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–15: Imports and the `Ticket` model

```python
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass


@dataclass
class Ticket:
    id: int
    title: str
```

`asyncio` brings `Queue`, `QueueFull`, `QueueEmpty`. `sys` is for `sys.version_info` in the 3.13+ version gate. `Ticket` is the work item — a `dataclass` with an `id` and a `title`. In the real `boardly`, this would be a `Ticket` from the boardly domain model (a support ticket, a build job, a webhook delivery).

### Lines 18–24: Pattern A — the producer

```python
async def producer(q: asyncio.Queue[Ticket | None], n: int, n_consumers: int) -> None:
    for i in range(n):
        ticket = Ticket(id=i, title=f"ticket-{i}")
        await q.put(ticket)              # blocks if the queue is full
        print(f"  [producer] put {ticket.id}")
    # One sentinel per consumer: when a consumer sees None, it exits.
    for _ in range(n_consumers):
        await q.put(None)
    print("  [producer] done")
```

The producer takes the queue, the number of items to produce, and the number of consumers (so it knows how many sentinels to push). `await q.put(ticket)` blocks if the queue is at capacity — this is backpressure, the producer cannot outrun the consumers. Each put increments the unfinished-tasks counter.

After all the real tickets are pushed, the producer pushes `n_consumers` sentinels (`None`). The sentinel-per-consumer rule: each consumer sees exactly one sentinel and exits cleanly. (If you pushed one sentinel for two consumers, the first to see it would exit; the second would hang forever on `await q.get()`.)

**Why `None` as the sentinel?** Because it is unambiguously not a `Ticket`. The type annotation `Queue[Ticket | None]` makes the contract explicit: every item in the queue is either a `Ticket` or a `None` shutdown signal. You could use a sentinel object (`_SHUTDOWN = object()`) for the same effect with stricter typing — `Queue[Ticket | _Sentinel]` — but `None` is idiomatic and the discrimination is `if ticket is None:`.

### Lines 27–37: Pattern A — the consumer

```python
async def consumer(q: asyncio.Queue[Ticket | None], name: str) -> int:
    processed = 0
    while True:
        ticket = await q.get()
        if ticket is None:              # sentinel -> exit
            q.task_done()
            break
        print(f"  [consumer {name}] got {ticket.id} ({ticket.title})")
        await asyncio.sleep(0.005)      # simulate work
        q.task_done()                   # decrement the unfinished counter
        processed += 1
    return processed
```

The consumer pulls items in an infinite loop. For each non-sentinel item: simulate work, then `q.task_done()` to decrement the unfinished counter. For the sentinel: `q.task_done()` (matched), `break` out of the loop, return the processed count.

The two `task_done()` calls — one for the sentinel, one for each real item — are what make `await q.join()` return. Forgetting either is the classic queue bug.

**Why call `task_done()` even for the sentinel?** Because the sentinel was pushed via `await q.put(None)`, which incremented the unfinished counter. The counter must be decremented for every `put`, including the sentinel — otherwise `join` hangs. The rule is mechanical: every `get` site calls `task_done`, no exceptions, in a `try`/`finally` if there is any chance of an exception escaping.

### Lines 40–48: Pattern A — the demo driver

```python
async def producer_consumer_demo() -> None:
    print("=== bounded producer-consumer (maxsize=3, 2 consumers) ===")
    q: asyncio.Queue[Ticket | None] = asyncio.Queue(maxsize=3)
    prod = asyncio.create_task(producer(q, 6, n_consumers=2))
    cons1 = asyncio.create_task(consumer(q, "A"))
    cons2 = asyncio.create_task(consumer(q, "B"))
    await prod
    await q.join()                     # waits for every task_done() to land
    # Both consumers see their sentinel and exit on their own — no cancel needed.
    results = await asyncio.gather(cons1, cons2)
    print(f"  processed: A={results[0]}, B={results[1]}")
```

`asyncio.Queue(maxsize=3)` is a bounded queue — at most 3 items in flight. The producer and two consumers are scheduled via `create_task`. After the producer finishes (`await prod`), the demo waits for `q.join()` — which blocks until every `put` has been matched by a `task_done`. Once `join` returns, both consumers have seen their sentinel and exited (the `break` in the consumer loop). The `gather(cons1, cons2)` returns their processed counts.

`maxsize=3` is what causes the producer's `await q.put(ticket)` calls to occasionally block — the trace shows the producer pushing items 0, 1, 2 then waiting until a consumer pulls one before pushing item 3. That backpressure is the whole point of a bounded queue: the producer cannot run away with memory.

**Why `await prod` before `await q.join()`?** Because the producer needs to finish pushing all items (including sentinels) before the counter can reach zero. If you called `join` before the producer finished, the counter would never hit zero (because the producer hadn't yet pushed all the sentinels). The order is: producer finishes -> `join` waits for consumers to drain -> consumers exit on their sentinels -> `gather` collects their results.

### Lines 51–64: Pattern B — the `*_nowait` variants

```python
async def nowait_demo() -> None:
    print("\n=== put_nowait / get_nowait ===")
    q: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
    q.put_nowait(1)                    # ok, queue had room
    try:
        q.put_nowait(2)                # queue full -> QueueFull
    except asyncio.QueueFull as e:
        print(f"  put_nowait raised: {type(e).__name__}")
    print(f"  get_nowait -> {q.get_nowait()}")   # ok, queue had an item
    try:
        q.get_nowait()                 # queue empty -> QueueEmpty
    except asyncio.QueueEmpty as e:
        print(f"  get_nowait raised: {type(e).__name__}")
```

`put_nowait` and `get_nowait` are the non-blocking variants — they raise `QueueFull` / `QueueEmpty` instead of yielding control. They are useful when you want to "try once and move on": a metrics emitter that should not block the request path on a full queue, a webhook fanout that drops on overflow. They are *not* awaitable — they are sync methods that succeed immediately or raise.

**Why use `*_nowait` at all?** Because sometimes blocking is wrong. A request handler that emits a webhook should not block the response on the webhook queue being full — it should drop and log. `put_nowait` lets you make that explicit:

```python
try:
    q.put_nowait(webhook)
except asyncio.QueueFull:
    log.warning("webhook queue full; dropping")
```

The blocking `await q.put(webhook)` is the wrong choice here — it would block the response until a consumer drained the queue, which could be seconds. The trade-off is the drop is visible (a lost webhook); for the metrics emitter that is the right trade-off, for the audit log it is not.

### Lines 67–78: Pattern C — the `join`-hangs-without-`task_done` bug

```python
async def join_without_task_done_demo() -> None:
    print("\n=== join() waits for task_done() (and the bug if you forget) ===")
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.put_nowait(2)
    _ = q.get_nowait()                  # forgot to call task_done()
    q.task_done()                       # only matched one get()
    try:
        await asyncio.wait_for(q.join(), timeout=0.1)
    except TimeoutError:
        print("  join() timed out — one task_done() missing")
```

The queue has 2 items. The demo `get`s both via `get_nowait` (counter at 2). It calls `task_done()` once (counter at 1). Then `await q.join()` waits for the counter to hit 0 — which never happens, because the second `task_done()` is missing. The `wait_for` with a 100ms timeout is the safety: the demo would hang forever without it.

This is the bug. In production, the symptom is `asyncio.run` hanging on shutdown — the worker that forgot `task_done()` is the cause, and the only clue is that `SIGTERM` does nothing.

**Why does `join` not just time out on its own?** Because `join` has no timeout argument — its contract is "wait until counter is zero, however long that takes". The expectation is that you, the caller, know the work is finite. If you are not sure, wrap `join` in `wait_for` (as this demo does) so you at least get a `TimeoutError` instead of a hang. The 3.13+ `shutdown()` (next pattern) is the better escape hatch — it forces the queue closed.

### Lines 81–94: Pattern D — the 3.13+ `shutdown` (version-gated)

```python
async def shutdown_demo() -> None:
    print("\n=== Queue.shutdown() — Python 3.13+, version-gated ===")
    if sys.version_info < (3, 13):
        print(f"  running Python {sys.version_info[:3]} -> shutdown() not available")
        print("  (3.13+: q.shutdown() closes the queue immediately;")
        print("   pending get() raises QueueShutDown; put() raises QueueShutDown)")
        return
    # On 3.13+ this branch runs:
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.shutdown()                       # 3.13+: immediately close the queue
    try:
        await q.get()                  # already-empty + shut down
    except asyncio.QueueShutDown as e:
        print(f"  get() raised: {type(e).__name__}")
```

`asyncio.Queue.shutdown()` was added in **Python 3.13** — the 3.12 runtime you are running does not have it (you can verify: `hasattr(asyncio.Queue, "shutdown")` returns `False` on 3.12). The `sys.version_info < (3, 13)` gate is the version-gate; on 3.12 the demo prints the explanation and returns. On 3.13+ it would actually run the `shutdown()` call.

The semantics: `shutdown()` immediately closes the queue. Pending `get()` calls raise `QueueShutDown`; `put()` calls raise `QueueShutDown`. Items still in the queue are abandoned (you can read them via `get_nowait()` *after* `shutdown()` — they are not lost, but they will not be delivered to waiters). The typical use is the shutdown path: call `shutdown()` to break every `await q.get()` and `await q.join()`, then exit.

**Why was `shutdown()` added in 3.13?** Because before 3.13, the only ways to break a blocked `get()` or `join()` were (a) cancel the task that was blocked (which propagates `CancelledError` and complicates cleanup) or (b) push a sentinel through the queue (which requires the queue to not be full, and requires every consumer to know about the sentinel). `shutdown()` is the clean, queue-level primitive: "no more items, ever, everyone waiting should wake up with `QueueShutDown`". On 3.12, the sentinel-per-consumer pattern is the equivalent — `shutdown()` is a 3.13 convenience, not a 3.12 necessity.

### Lines 97–104: `main` and the entrypoint

```python
async def main() -> None:
    await producer_consumer_demo()
    await nowait_demo()
    await join_without_task_done_demo()
    await shutdown_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

Four demos run sequentially. The producer-consumer demo creates its own queue and tasks; the `nowait` demo creates a fresh queue; the `join`-bug demo creates a fresh queue with a `wait_for` safety; the `shutdown` demo version-gates on 3.13+.

## Execution Trace

```bash
$ uv run python boardly/asyncio_queue_demo.py
=== bounded producer-consumer (maxsize=3, 2 consumers) ===
  [producer] put 0
  [producer] put 1
  [producer] put 2
  [consumer A] got 0 (ticket-0)
  [consumer B] got 1 (ticket-1)
  [producer] put 3
  [producer] put 4
  [consumer A] got 2 (ticket-2)
  [consumer B] got 3 (ticket-3)
  [producer] put 5
  [consumer A] got 4 (ticket-4)
  [consumer B] got 5 (ticket-5)
  [producer] done
  processed: A=3, B=3

=== put_nowait / get_nowait ===
  put_nowait raised: QueueFull
  get_nowait -> 1
  get_nowait raised: QueueEmpty

=== join() waits for task_done() (and the bug if you forget) ===
  join() timed out — one task_done() missing

=== Queue.shutdown() — Python 3.13+, version-gated ===
  running Python (3, 12, 15) -> shutdown() not available
  (3.13+: q.shutdown() closes the queue immediately;
   pending get() raises QueueShutDown; put() raises QueueShutDown)
```

Demo A shows the bounded producer-consumer running cleanly — the producer pushes 0, 1, 2 (fills the queue), then waits until consumer A pulls 0 (the queue has room), then pushes 3, and so on. The two consumers split the 6 tickets 3-3. Demo B shows the `QueueFull` and `QueueEmpty` raises from the non-blocking variants. Demo C shows the `task_done`-missing bug — `join` hangs until the 100ms `wait_for` safety fires. Demo D shows the version-gate: on 3.12 the `shutdown` branch is skipped with an explanation; on 3.13+ it would run.

## Common Mistakes

### Mistake 1: One sentinel for multiple consumers

```python
async def producer(q, n):
    for i in range(n):
        await q.put(Ticket(i))
    await q.put(None)              # one sentinel
```

**Symptom:** With two consumers, the first to see the sentinel exits; the second hangs forever on `await q.get()`. The shutdown path hangs.

**Why:** The sentinel is consumed by exactly one consumer. The other consumer never sees it and blocks forever.

**Fix:** Push one sentinel per consumer:

```python
async def producer(q, n, n_consumers):
    for i in range(n):
        await q.put(Ticket(i))
    for _ in range(n_consumers):
        await q.put(None)
```

### Mistake 2: Forgetting `task_done()` after `get()`

```python
async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break
        await process(item)
        # BUG: no task_done() — join hangs forever
```

**Symptom:** `await q.join()` hangs. The shutdown path hangs. `SIGTERM` does nothing.

**Why:** The unfinished-tasks counter never reaches zero. `join` waits forever.

**Fix:** Call `task_done()` for every `get`, including the sentinel. Use `try`/`finally` if `process` can raise:

```python
async def consumer(q):
    while True:
        item = await q.get()
        try:
            if item is None:
                break
            await process(item)
        finally:
            q.task_done()
```

### Mistake 3: Using `Queue` for inter-task signalling instead of `Event`

```python
q = asyncio.Queue()
await q.put("ready")           # signal
await q.get()                  # wait
```

**Symptom:** The code works, but only one waiter can be woken per signal — additional waiters block forever. The queue accumulates items if the signal rate exceeds the consume rate.

**Why:** A queue is point-to-point — one producer, one consumer per item. The "one signal, many waiters" case is a broadcast, which is `Event`'s job.

**Fix:** Use `asyncio.Event` for one-to-many wake-ups ([[21-asyncio-primitives/02-Lock-and-Event]]):

```python
ev = asyncio.Event()
ev.set()                       # wake every waiter
await ev.wait()                # block until set
```

## Engineering Trade-Offs

**Decision:** Use `asyncio.Queue` for producer-consumer pipelines with one producer and N consumers. Use `maxsize=N` when the producer is faster than the consumers (backpressure). Use the sentinel-per-consumer pattern for shutdown. Use the `*_nowait` variants when blocking is wrong. On 3.13+, use `shutdown()` for the "break every blocked `get`/`join`" path.

**Both sides:** The alternative is shared mutable state guarded by a `Lock` ([[21-asyncio-primitives/02-Lock-and-Event]]). The Lock pattern is simpler for a small N (one cache, one counter); the Queue pattern scales better for high throughput (no lock contention, the consumer owns the state). The Queue pattern is also more debuggable: the queue depth is observable (`q.qsize()`), the items in flight are countable (`q._unfinished_tasks` is internal but accessible), and the shutdown is clean (`shutdown()` or sentinel).

**Commitment:** `boardly` uses `asyncio.Queue(maxsize=100)` for the background job queue — bounded to absorb bursts but not run away with memory. The producer is the request handler that pushes webhook deliveries; the consumers are N worker tasks (N = `min(10, cpu_count * 5)`). Shutdown is the sentinel-per-consumer pattern (3.12 runtime) — the producer pushes N `None` sentinels before exiting. When the project upgrades to 3.13+, the shutdown path will switch to `q.shutdown()` for the simpler `QueueShutDown` semantics. The `*_nowait` variants are used in the metrics emitter (drop on full) and the audit log (raise on full, surface the failure).

**Why use `maxsize=100` and not `maxsize=0` (unbounded)?** Because an unbounded queue under a burst load can grow until the process runs out of memory and gets OOM-killed. A bounded queue with `maxsize=100` absorbs a normal burst (100 items queued) and applies backpressure on the producer when the burst exceeds that — the producer blocks, which is the right behaviour for a request handler (it returns a 503 instead of OOMing the process). The trade-off is the producer can be blocked; the alternative is dropping, which loses work.

## Exercises

1. **Exercise 1 — Remove the sentinel-per-consumer.** In `producer`, push only one sentinel regardless of `n_consumers`. Re-run with 2 consumers. Confirm the demo hangs (cancel with Ctrl-C). `Verify: uv run python boardly/asyncio_queue_demo.py`

2. **Exercise 2 — Forget `task_done()`.** In `consumer`, remove the `q.task_done()` call after `process`. Re-run. Confirm `join` hangs and the `wait_for` safety (there isn't one in the producer-consumer demo — add one to see the timeout). `Verify: uv run python boardly/asyncio_queue_demo.py`

3. **Exercise 3 — Increase `maxsize`.** Change `maxsize=3` to `maxsize=10` and re-run. Confirm the producer no longer blocks (all 6 items fit immediately). `Verify: uv run python boardly/asyncio_queue_demo.py`

4. **Exercise 4 — Use `put_nowait` with drop-on-full.** Replace `await q.put(ticket)` with `try: q.put_nowait(ticket); except asyncio.QueueFull: log.warning(...)`. Confirm the producer no longer blocks; confirm some items are dropped under load. `Verify: uv run python boardly/asyncio_queue_demo.py`

5. **Exercise 5 — Build a multi-priority queue.** Use two queues (`high_q` and `low_q`) and a consumer that drains `high_q` first (with `get_nowait` to check both). Confirm high-priority items are processed before low-priority ones when both queues have items. `Verify: uv run python boardly/asyncio_queue_demo.py`

## Verification

```bash
$ uv run python boardly/asyncio_queue_demo.py
=== bounded producer-consumer (maxsize=3, 2 consumers) ===
  [producer] put 0
  [producer] put 1
  [producer] put 2
  [consumer A] got 0 (ticket-0)
  [consumer B] got 1 (ticket-1)
  [producer] put 3
  [producer] put 4
  [consumer A] got 2 (ticket-2)
  [consumer B] got 3 (ticket-3)
  [producer] put 5
  [consumer A] got 4 (ticket-4)
  [consumer B] got 5 (ticket-5)
  [producer] done
  processed: A=3, B=3

=== put_nowait / get_nowait ===
  put_nowait raised: QueueFull
  get_nowait -> 1
  get_nowait raised: QueueEmpty

=== join() waits for task_done() (and the bug if you forget) ===
  join() timed out — one task_done() missing

=== Queue.shutdown() — Python 3.13+, version-gated ===
  running Python (3, 12, 15) -> shutdown() not available
  (3.13+: q.shutdown() closes the queue immediately;
   pending get() raises QueueShutDown; put() raises QueueShutDown)
```

## Previously Learned Here

- [[21-asyncio-primitives/02-Lock-and-Event]] — `Lock` and `Event` are the wrong tool for producer-consumer pipelines. A `Lock` would serialise the work (no concurrency); an `Event` would broadcast a signal (no item passing). `Queue` is the right tool for "one producer, N consumers, items in flight".
- [[04-collections/03-deque]] — `asyncio.Queue` uses a `deque` internally; the bounded-vs-unbounded behaviour is implemented on top of the deque's O(1) append/popleft.

## What's Next

[[21-asyncio-primitives/04-Semaphore-and-Condition]] — `Semaphore` for bounded concurrency (a pool of N connections; `async with sem:` limits concurrent access to N) and `Condition` for the wait-notify pattern (one task waits, another notifies one or all). The `Semaphore` is what you reach for when the bottleneck is the downstream capacity (a DB pool of 10) rather than the queue depth. And the difference from `threading.Condition` mirrors the difference from `threading.Lock` — the asyncio `Condition` is awaitable and lives on the loop.

- `asyncio.Semaphore(value=N)` — capacity control; `async with sem:`.
- `asyncio.Condition()` — `notify(n=1)` / `notify_all()` / `await wait()`.
- The bounded-concurrency pattern (DB pool of N connections).
- Why `Semaphore(1)` is *not* a substitute for `Lock` (release-without-acquire).

## Sources

- **`asyncio` — Queues** — https://docs.python.org/3.12/library/asyncio-queue.html — accessed 2026-10-23 — the canonical reference for `Queue`, `put`/`get`/`put_nowait`/`get_nowait`, `task_done`, `join`, `QueueFull`, `QueueEmpty`.
- **`asyncio` — Queues: `Queue.shutdown`** — https://docs.python.org/3.13/library/asyncio-queue.html#asyncio.Queue.shutdown — accessed 2026-10-23 — the 3.13+ reference for `shutdown()` and `QueueShutDown`; the version-gate source.
- **`collections.deque`** — https://docs.python.org/3.12/library/collections.html#collections.deque — accessed 2026-10-23 — the underlying data structure; O(1) append/popleft.

## What We Learned

- You can construct a bounded `asyncio.Queue(maxsize=N)` and explain that `maxsize=0` is unbounded.
- You can use `put`/`get`/`put_nowait`/`get_nowait` and explain when each is appropriate.
- You can explain the `task_done`/`join` pair and the bug if a `task_done` is missing.
- You can implement the producer-consumer pattern with one sentinel per consumer.
- You can state the 3.13+ `Queue.shutdown()` semantics and version-gate it correctly on the 3.12 runtime.
- You can choose between `Queue`, `Lock`, and `Event` for a given co-ordination problem.
