---
title: "Lesson 05: to_thread and run_in_executor"
aliases:
 - asyncio.to_thread
 - loop.run_in_executor
 - blocking-in-async
 - ThreadPoolExecutor default
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
 - "[[21-asyncio-primitives/02-Lock-and-Event]]"
 - "[[23-logging/04-Uvicorn-logging-integration]]"
first_taught_in: "21-asyncio-primitives/05-to_thread-and-run-in-executor"
---

# Lesson 05: `to_thread` and `run_in_executor`

*`asyncio.to_thread(func, *args, **kwargs)` (3.9+) is the canonical way to call blocking sync code from async — `requests.get`, `time.sleep`, file I/O on a slow disk. `loop.run_in_executor(executor, func, *args)` is the lower-level form. The rule: don't call `requests.get` in async — use `to_thread` or `httpx.AsyncClient`.*

**You're at the very beginning of Section 21, five lessons in.**

You can run N coroutines concurrently. You can co-ordinate them with `Lock`, `Event`, `Queue`, `Semaphore`, `Condition`. But every primitive so far has been *cooperative* — every `await` yields control, every coroutine is well-behaved. The real world is full of blocking sync code that does not know about the event loop: `requests.get(...)` blocks the calling thread for 200ms; `time.sleep(5)` blocks for 5 seconds; `sqlite3.connect(...)` blocks on a slow disk. If you call any of these from a coroutine *without wrapping*, the event loop freezes for the duration — every other coroutine stops, every request times out, the server appears hung. The fix is `asyncio.to_thread` (3.9+): wrap the blocking call so it runs in a worker thread while the loop keeps going. By the end of this lesson you will know `to_thread`, the lower-level `loop.run_in_executor`, the "don't call `requests.get` in async" rule, and the default `ThreadPoolExecutor` formula (`max_workers = min(32, os.cpu_count() + 4)` since 3.8). Take your time. Type every example. **This is how you learn.**

#asyncio #to_thread #run_in_executor

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `asyncio.to_thread(func, *args, **kwargs)`** — the 3.9+ canonical way to call a sync function in a worker thread from async code.
2. **Use `loop.run_in_executor(executor, func, *args)`** — the lower-level form; `executor=None` uses the default `ThreadPoolExecutor`.
3. **State the "don't call `requests.get` in async" rule** — either use `to_thread(requests.get, url)` (offload to a thread) or use `httpx.AsyncClient` (a real async HTTP client).
4. **State the default `ThreadPoolExecutor` formula** — `max_workers = min(32, os.cpu_count() + 4)` since 3.8; explain why it caps at 32.
5. **Choose between `to_thread` and `run_in_executor`** — `to_thread` for the common case; `run_in_executor` for custom executors (a process pool for CPU work, a fixed thread pool for I/O).

## Prerequisites

Before starting, you need:

- **`asyncio.create_task` and `asyncio.gather`** — [[21-asyncio-primitives/01-Task-gather-wait_for]]. `to_thread` returns a coroutine you can `gather` with other coroutines — concurrent blocking calls become concurrent worker threads.
- **The `async with` protocol** — [[03-contextlib/02-asynccontextmanager]]. The `ThreadPoolExecutor` is a sync context manager (`with ThreadPoolExecutor() as ex:`); the asyncio side (`await loop.run_in_executor(...)`) returns a coroutine.
- **About 30–40 minutes of focused time.**

**The most common gap: calling `requests.get` directly in an async function.**

You have written `requests.get(url)` for years. You move to FastAPI, write `async def handler(): r = requests.get(url)`, and your code *appears* to work — until production, when a slow upstream (a 2-second response) freezes the entire event loop for 2 seconds. Every other request times out. The CPU is idle, the network is idle, the disk is idle — the loop is just blocked waiting for `requests.get` to return. The fix is one of two: `await asyncio.to_thread(requests.get, url)` (offload to a thread; the loop keeps going) or `async with httpx.AsyncClient() as c: r = await c.get(url)` (use a real async HTTP client). The first is the migration path; the second is the long-term answer. Mixing `requests.get` directly into async code is *never* the right answer.

## The Problem

Here is the freezing bug, in its native habitat.

```python
# boardly/api/projects.py — the frozen version
import requests

async def fetch_project(slug: str) -> Project:
    r = requests.get(f"https://upstream/projects/{slug}")  # ← blocks the loop
    return Project(**r.json())
```

`requests.get` is a sync function. Calling it from an `async def` does not make it async — it just blocks the event loop's thread for the duration of the HTTP round-trip. A 200ms call freezes the loop for 200ms; a 2-second call freezes it for 2 seconds. Every other coroutine stops, every other request times out, the server appears hung.

The fix is `asyncio.to_thread` (3.9+):

```python
async def fetch_project(slug: str) -> Project:
    r = await asyncio.to_thread(requests.get, f"https://upstream/projects/{slug}")
    return Project(**r.json())
```

`to_thread` runs `requests.get(url)` in a worker thread from the default `ThreadPoolExecutor`. The `await` yields control to the loop while the worker thread blocks — so other coroutines keep running. When the worker thread finishes, the result is delivered to the awaiting coroutine. The blocking call is still blocking — it just blocks a worker thread instead of the loop's thread.

The deeper fix is to use an async HTTP client (`httpx.AsyncClient`); this lesson covers `to_thread` because it is the right migration path for legacy code and the right answer for one-off blocking calls (a sync database driver you have not yet migrated, a `subprocess.run` you cannot avoid). For the long-term, `httpx.AsyncClient` is the answer; this lesson shows both.

## The Code

```python
# boardly/asyncio_to_thread_demo.py
"""asyncio.to_thread and loop.run_in_executor on boardly.

to_thread (3.9+) is the canonical way to call blocking sync code from an
async function. run_in_executor is the lower-level form. The boardly use:
a sync `requests.get` call to an old internal service that we must call
until it's migrated — wrapped in to_thread so it doesn't block the loop.

Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class Project:
    slug: str
    name: str


# --- A blocking sync function. NOT async. This is the kind of code that
# would freeze the event loop if you called it directly from a coroutine. ---
def blocking_fetch_project(slug: str, *, latency: float = 0.05) -> Project:
    """Pretend this is `requests.get(...).json()` — a blocking call."""
    time.sleep(latency)            # sync sleep — blocks the calling thread
    return Project(slug=slug, name=slug.title())


# --- Pattern A: the wrong way — call blocking code directly from async ---
async def wrong_way() -> None:
    """Blocking call in an async function freezes the whole event loop."""
    print("  [wrong_way] start blocking call (loop is frozen)")
    result = blocking_fetch_project("alpha")    # blocks the entire loop
    print(f"  [wrong_way] {result.slug}")


# --- Pattern B: the right way — asyncio.to_thread (3.9+) ---
async def to_thread_way(slug: str) -> Project:
    """Run the blocking function in a worker thread; the loop keeps going."""
    # asyncio.to_thread(func, *args, **kwargs) — Python 3.9+.
    # Returns a coroutine. Awaiting it runs func(*args, **kwargs) in a thread
    # from the default ThreadPoolExecutor and returns its result.
    return await asyncio.to_thread(blocking_fetch_project, slug)


# --- Pattern C: the lower-level form — loop.run_in_executor ---
async def run_in_executor_way(slug: str) -> Project:
    """The lower-level form: explicit loop + executor + func + args."""
    loop = asyncio.get_running_loop()
    # executor=None -> default ThreadPoolExecutor
    # (max_workers = min(32, os.cpu_count() + 4) since 3.8).
    return await loop.run_in_executor(None, blocking_fetch_project, slug)


async def run_in_executor_custom_way(slug: str) -> Project:
    """A custom ThreadPoolExecutor with a fixed max_workers."""
    loop = asyncio.get_running_loop()
    # max_workers = min(32, os.cpu_count() + 4) is the default; you can override.
    with ThreadPoolExecutor(max_workers=2) as ex:
        return await loop.run_in_executor(ex, blocking_fetch_project, slug)


# --- Pattern D: concurrent to_thread calls keep the loop responsive ---
async def concurrent_to_thread_demo() -> None:
    print("=== concurrent to_thread (loop stays responsive) ===")
    # 3 blocking calls in parallel — each runs in its own worker thread.
    # The asyncio.sleep(0.001) coroutine co-operates with them, proving the
    # loop is not frozen.
    async def heartbeat() -> None:
        for i in range(15):
            print(f"    heartbeat tick {i}")
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    results = await asyncio.gather(
        to_thread_way("alpha"),
        to_thread_way("beta"),
        to_thread_way("gamma"),
    )
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    print(f"  results: {[p.slug for p in results]}")


# --- Pattern E: the rule — don't call requests.get in async; use httpx or to_thread ---
async def requests_rule_demo() -> None:
    print("\n=== the rule: don't call requests.get in async ===")
    # Demonstrate the principle with urllib (which is in the stdlib) instead
    # of requests, so the demo runs without an external dependency.
    # The WRONG way:
    #     import requests
    #     r = requests.get("https://example.com/projects/alpha")  # blocks the loop
    # The RIGHT way #1 (offload to a thread):
    #     r = await asyncio.to_thread(requests.get, url)
    # The RIGHT way #2 (use an async HTTP client):
    #     async with httpx.AsyncClient() as c:
    #         r = await c.get(url)

    def sync_get(url: str) -> int:
        # urllib.request.urlopen is blocking — same family as requests.get.
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status

    status = await asyncio.to_thread(sync_get, "https://example.com")
    print(f"  sync_get via to_thread -> {status}")
    print(f"  default ThreadPoolExecutor max_workers = min(32, os.cpu_count() + 4) = {min(32, os.cpu_count() + 4)}")


async def main() -> None:
    print("=== WRONG way: blocking call in async (loop frozen) ===")
    await wrong_way()

    await concurrent_to_thread_demo()
    await requests_rule_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–17: Imports and the `Project` model

```python
from __future__ import annotations

import asyncio
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class Project:
    slug: str
    name: str
```

`asyncio` brings `to_thread` (3.9+) and `get_running_loop`. `os` is for `os.cpu_count()` in the default-executor printout. `time` is for `time.sleep` — the *blocking* sleep we want to wrap. `urllib.request` is the stdlib HTTP client (we use it instead of `requests` so the demo runs without an external dependency). `ThreadPoolExecutor` from `concurrent.futures` is the executor class for the lower-level `run_in_executor` form.

### Lines 20–24: The blocking sync function

```python
def blocking_fetch_project(slug: str, *, latency: float = 0.05) -> Project:
    """Pretend this is `requests.get(...).json()` — a blocking call."""
    time.sleep(latency)            # sync sleep — blocks the calling thread
    return Project(slug=slug, name=slug.title())
```

This is a regular sync function — `def`, not `async def`. It calls `time.sleep(latency)` (NOT `await asyncio.sleep(latency)`), which blocks the calling thread for `latency` seconds. If you call this from a coroutine *without wrapping*, the event loop's thread is the calling thread, and the loop is frozen for the duration. This is the shape of every blocking sync call you will ever meet: `requests.get`, `time.sleep`, `sqlite3.connect`, `subprocess.run`, file I/O on a slow disk.

**Why does `time.sleep` freeze the loop?** Because `time.sleep` is a kernel-level syscall — `nanosleep` on Linux — that suspends the calling *thread* for the specified duration. The asyncio event loop runs on a single thread; if that thread is suspended, no coroutine can run. `await asyncio.sleep(d)`, by contrast, is *not* a syscall — it is a coroutine that schedules a callback on the loop after `d` seconds and immediately yields control back to the loop. The loop keeps running other coroutines during the wait; when the timer fires, the loop resumes the sleeping coroutine. The two `sleep`s look similar but are mechanically different — one blocks the thread, the other cooperates with the loop.

### Lines 27–31: Pattern A — the wrong way

```python
async def wrong_way() -> None:
    """Blocking call in an async function freezes the whole event loop."""
    print("  [wrong_way] start blocking call (loop is frozen)")
    result = blocking_fetch_project("alpha")    # blocks the entire loop
    print(f"  [wrong_way] {result.slug}")
```

`blocking_fetch_project("alpha")` is a direct sync call inside an `async def`. The `async def` does not magically make the call async — it just means the function *could* `await` something; here it does not. The call runs to completion on the loop's thread, blocking the loop for 50ms. Every other coroutine (including the heartbeat we will see in Pattern D) is starved during that 50ms.

This is the bug. The fix is Pattern B.

### Lines 34–39: Pattern B — `asyncio.to_thread`

```python
async def to_thread_way(slug: str) -> Project:
    """Run the blocking function in a worker thread; the loop keeps going."""
    # asyncio.to_thread(func, *args, **kwargs) — Python 3.9+.
    # Returns a coroutine. Awaiting it runs func(*args, **kwargs) in a thread
    # from the default ThreadPoolExecutor and returns its result.
    return await asyncio.to_thread(blocking_fetch_project, slug)
```

`asyncio.to_thread(func, *args, **kwargs)` (Python 3.9+) is the canonical wrapper. It takes a sync function and its arguments, schedules `func(*args, **kwargs)` to run in a worker thread from the default `ThreadPoolExecutor`, and returns a coroutine. Awaiting that coroutine yields control to the loop while the worker thread runs the function; when the function returns, the result is delivered to the awaiting coroutine.

The signature `asyncio.to_thread(func, /, *args, **kwargs)` (note the `/` — `func` is positional-only) means you cannot pass `func` as a keyword argument. The intended call shape is `await asyncio.to_thread(my_function, arg1, arg2, kw=val)`.

**Why is `to_thread` the canonical form?** Because before 3.9, the only way to do this was `loop.run_in_executor(None, func, *args)` — three things to remember (the loop, the executor, the func). `to_thread` is one thing: the function and its arguments. The lower-level form is still there (Pattern C) for the cases where you need a custom executor; `to_thread` is the everyday form. The implementation is literally `loop.run_in_executor(None, functools.partial(func, *args, **kwargs))` — `to_thread` is sugar over `run_in_executor`.

### Lines 42–47: Pattern C — the lower-level `loop.run_in_executor`

```python
async def run_in_executor_way(slug: str) -> Project:
    """The lower-level form: explicit loop + executor + func + args."""
    loop = asyncio.get_running_loop()
    # executor=None -> default ThreadPoolExecutor
    # (max_workers = min(32, os.cpu_count() + 4) since 3.8).
    return await loop.run_in_executor(None, blocking_fetch_project, slug)
```

`loop.run_in_executor(executor, func, *args)` is the lower-level form. `executor=None` uses the default `ThreadPoolExecutor`; you can pass a custom executor (Pattern D) for a fixed `max_workers` or a `ProcessPoolExecutor` for CPU work. `func` must be a callable (not a partial — `run_in_executor` does not accept `**kwargs`; if you need them, use `functools.partial(func, **kwargs)`).

The signature asymmetry is the key reason `to_thread` exists: `run_in_executor` takes `*args` only (no `**kwargs`), so passing keyword arguments to the wrapped function requires a `partial`. `to_thread` accepts `**kwargs` directly. The everyday call is `to_thread`; the escape hatch is `run_in_executor`.

### Lines 50–54: Pattern C — a custom `ThreadPoolExecutor`

```python
async def run_in_executor_custom_way(slug: str) -> Project:
    """A custom ThreadPoolExecutor with a fixed max_workers."""
    loop = asyncio.get_running_loop()
    # max_workers = min(32, os.cpu_count() + 4) is the default; you can override.
    with ThreadPoolExecutor(max_workers=2) as ex:
        return await loop.run_in_executor(ex, blocking_fetch_project, slug)
```

A custom `ThreadPoolExecutor(max_workers=2)` lets you bound the worker thread count. The default executor (used by `executor=None` in `run_in_executor` and by `to_thread`) has `max_workers = min(32, os.cpu_count() + 4)` since 3.8 — see Pattern E for the formula. A custom executor with `max_workers=2` is the right choice when you want to limit concurrency to a downstream (e.g. at most 2 concurrent calls to a legacy service that has its own connection limit).

The `with ThreadPoolExecutor() as ex:` block is the sync context manager — on `__exit__`, it calls `ex.shutdown(wait=True)`, which waits for every submitted task to complete. If you create the executor inline (as here), the `with` block keeps it alive for the duration of the `run_in_executor` call. If you create the executor at module level (the more common pattern), you keep it as a module-level global and submit work to it for the lifetime of the process.

### Lines 57–76: Pattern D — concurrent `to_thread` keeps the loop responsive

```python
async def concurrent_to_thread_demo() -> None:
    print("=== concurrent to_thread (loop stays responsive) ===")
    # 3 blocking calls in parallel — each runs in its own worker thread.
    # The asyncio.sleep(0.001) coroutine co-operates with them, proving the
    # loop is not frozen.
    async def heartbeat() -> None:
        for i in range(15):
            print(f"    heartbeat tick {i}")
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    results = await asyncio.gather(
        to_thread_way("alpha"),
        to_thread_way("beta"),
        to_thread_way("gamma"),
    )
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    print(f"  results: {[p.slug for p in results]}")
```

This is the proof that `to_thread` keeps the loop responsive. Three `to_thread_way` calls (each runs a 50ms blocking function in a worker thread) are scheduled concurrently via `asyncio.gather`. A heartbeat coroutine runs alongside them, printing `heartbeat tick 0` through `heartbeat tick 4` (about 5 ticks in the 50ms the gather takes). The heartbeat's `await asyncio.sleep(0.01)` yields control to the loop, which can run other coroutines — including the ones waiting for the `to_thread` results.

If the three calls had been made directly (Pattern A, the wrong way), the loop would have been frozen for 150ms total (3 × 50ms), and no heartbeat tick would have printed during that window. The trace shows the heartbeat ticking *during* the gather — proof the loop is alive.

**Why does the heartbeat stop at tick 4?** Because the three `to_thread` calls take ~50ms total (each runs in a separate worker thread, concurrently). At 10ms per heartbeat tick, that is about 5 ticks. The `hb.cancel()` after `gather` returns cancels the heartbeat (which is mid-sleep); the `try/except asyncio.CancelledError` handles the cancellation cleanly.

### Lines 79–96: Pattern E — the rule, and the default executor

```python
async def requests_rule_demo() -> None:
    print("\n=== the rule: don't call requests.get in async ===")
    # Demonstrate the principle with urllib (which is in the stdlib) instead
    # of requests, so the demo runs without an external dependency.
    # The WRONG way:
    #     import requests
    #     r = requests.get("https://example.com/projects/alpha")  # blocks the loop
    # The RIGHT way #1 (offload to a thread):
    #     r = await asyncio.to_thread(requests.get, url)
    # The RIGHT way #2 (use an async HTTP client):
    #     async with httpx.AsyncClient() as c:
    #         r = await c.get(url)

    def sync_get(url: str) -> int:
        # urllib.request.urlopen is blocking — same family as requests.get.
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status

    status = await asyncio.to_thread(sync_get, "https://example.com")
    print(f"  sync_get via to_thread -> {status}")
    print(f"  default ThreadPoolExecutor max_workers = min(32, os.cpu_count() + 4) = {min(32, os.cpu_count() + 4)}")
```

The rule: **don't call `requests.get` in async**. Use `to_thread` (offload to a thread) or `httpx.AsyncClient` (use a real async HTTP client). The demo uses `urllib.request.urlopen` (stdlib, no external dependency) to make the point — it is the same family of blocking sync HTTP call as `requests.get`.

The two paths:

1. **`to_thread` offload** — `r = await asyncio.to_thread(requests.get, url)`. The blocking call runs in a worker thread; the loop keeps going. The downside: you consume a worker thread per concurrent call, and the default executor caps at `min(32, os.cpu_count() + 4)` — see the formula below.
2. **`httpx.AsyncClient`** — `async with httpx.AsyncClient() as c: r = await c.get(url)`. The async HTTP client uses non-blocking I/O internally; no worker thread consumed; the loop handles thousands of concurrent calls without the thread cap.

The right answer for the long term is `httpx.AsyncClient` (or `aiohttp`, or any other async HTTP client). The right answer for migration (you have `requests` everywhere, you cannot rewrite it all at once) is `to_thread`. Mixing `requests.get` directly into async code is *never* the right answer — it freezes the loop.

The default `ThreadPoolExecutor` formula: `max_workers = min(32, os.cpu_count() + 4)` since 3.8. The `+ 4` is "a few extra threads for I/O overlap"; the `min(32, ...)` caps at 32 to prevent thread explosion on big machines (a 64-core box gets 32 worker threads, not 68). On a 2-core sandbox (this demo's runtime), the formula evaluates to `min(32, 2 + 4) = 6`. On a 16-core production box, it would be `min(32, 16 + 4) = 20`. On a 64-core box, `min(32, 64 + 4) = 32`.

**Why does the formula cap at 32?** Because threads are not free — each thread costs ~8MB of stack space on Linux default, plus kernel scheduling overhead. 32 threads is ~256MB of stack — manageable. 68 threads would be ~544MB — significant, and the GIL means more threads do not buy more CPU. The cap is a heuristic for "I/O overlap on a typical server"; for CPU work you should use a `ProcessPoolExecutor` instead, which is not bound by the GIL but is bounded by `os.cpu_count()`.

### Lines 99–105: `main` and the entrypoint

```python
async def main() -> None:
    print("=== WRONG way: blocking call in async (loop frozen) ===")
    await wrong_way()

    await concurrent_to_thread_demo()
    await requests_rule_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

Three demos: the wrong way (to show the bug), the concurrent `to_thread` (to show the fix and the heartbeat proof), and the `requests` rule with the default-executor formula printout.

## Execution Trace

```bash
$ uv run python boardly/asyncio_to_thread_demo.py
=== WRONG way: blocking call in async (loop frozen) ===
  [wrong_way] start blocking call (loop is frozen)
  [wrong_way] alpha
=== concurrent to_thread (loop stays responsive) ===
    heartbeat tick 0
    heartbeat tick 1
    heartbeat tick 2
    heartbeat tick 3
    heartbeat tick 4
  results: ['alpha', 'beta', 'gamma']

=== the rule: don't call requests.get in async ===
  sync_get via to_thread -> 200
  default ThreadPoolExecutor max_workers = min(32, os.cpu_count() + 4) = 6
```

The first block shows the wrong way — the loop is frozen, no heartbeat can run (no heartbeat is scheduled here; the wrong-way demo just shows the blocking call). The second block shows the concurrent `to_thread` — five heartbeat ticks print during the 50ms gather, proving the loop is alive. The third block shows the `urllib` call wrapped in `to_thread` returning a 200 status, and the default-executor formula evaluating to 6 on this 2-core sandbox.

## Common Mistakes

### Mistake 1: Calling `requests.get` directly in an async function

```python
import requests

async def handler(url):
    r = requests.get(url)            # ← blocks the loop
    return r.json()
```

**Symptom:** Under load, requests start timing out; the CPU is idle, the network is idle, the disk is idle — the loop is just blocked. The server appears hung. P99 latency spikes; the SLO is breached.

**Why:** `requests.get` is a sync function. Calling it from `async def` does not make it async — it blocks the loop's thread for the duration of the HTTP call. Every other coroutine stops.

**Fix:** Use `to_thread` or `httpx.AsyncClient`:

```python
# Option 1: offload to a thread (the migration path)
r = await asyncio.to_thread(requests.get, url)

# Option 2: use an async HTTP client (the long-term answer)
async with httpx.AsyncClient() as c:
    r = await c.get(url)
```

### Mistake 2: Using `to_thread` for CPU-bound work

```python
def sha256_of_large_file(path):
    # CPU-bound: hashes 1GB of data
    ...

result = await asyncio.to_thread(sha256_of_large_file, path)  # ← GIL blocks
```

**Symptom:** The loop is *still* frozen during the call — even though `to_thread` is running it in a worker thread. The heartbeat stops.

**Why:** The Python Global Interpreter Lock (GIL) serialises Python bytecode across threads. A CPU-bound function holds the GIL for its entire run; the loop's thread cannot run other coroutines. `to_thread` helps for I/O-bound blocking calls (which release the GIL during the syscall); it does *not* help for CPU-bound Python code (which holds the GIL).

**Fix:** Use a `ProcessPoolExecutor` for CPU-bound work:

```python
from concurrent.futures import ProcessPoolExecutor

loop = asyncio.get_running_loop()
with ProcessPoolExecutor() as ex:
    result = await loop.run_in_executor(ex, sha256_of_large_file, path)
```

Each process has its own GIL; CPU work runs in parallel.

### Mistake 3: Letting the `ThreadPoolExecutor` shut down while tasks are pending

```python
async def handler():
    with ThreadPoolExecutor(max_workers=2) as ex:
        # Submit 10 tasks; only 2 can run concurrently; the rest queue.
        tasks = [loop.run_in_executor(ex, slow_call, i) for i in range(10)]
        results = await asyncio.gather(*tasks)
    # ← `with` exits, `ex.shutdown(wait=True)` runs, waits for the remaining 8 tasks.
```

**Symptom:** The `with` block hangs on `__exit__` until every queued task finishes — which could be many seconds.

**Why:** `ThreadPoolExecutor.__exit__` calls `shutdown(wait=True)` — it waits for every submitted task to complete before returning. If you submitted 10 tasks to a 2-worker pool, the `with` exit blocks for the duration of the remaining 8 tasks.

**Fix:** Create the executor at module level (not inside the function), and let it live for the process lifetime:

```python
# Module level
EXECUTOR = ThreadPoolExecutor(max_workers=2)

async def handler():
    tasks = [loop.run_in_executor(EXECUTOR, slow_call, i) for i in range(10)]
    return await asyncio.gather(*tasks)
```

The module-level executor is shut down on process exit; the function does not block on `__exit__`.

## Engineering Trade-Offs

**Decision:** Use `asyncio.to_thread` for one-off blocking calls (legacy sync code, sync database drivers, `subprocess.run`). Use `loop.run_in_executor` with a custom `ThreadPoolExecutor` for bounded concurrency to a downstream. Use a `ProcessPoolExecutor` for CPU-bound work. Use a real async client (`httpx.AsyncClient`) for the long-term HTTP path.

**Both sides:** The alternative to `to_thread` is to rewrite the sync code as async. The rewrite is the right answer when the sync code is yours and the async version is available (`sqlite3` → `aiosqlite`; `requests` → `httpx`). The `to_thread` wrapper is the right answer when the sync code is not yours (a vendored library, a stdlib module with no async equivalent) or when the rewrite is too expensive (a 10,000-line sync codebase you cannot migrate in a sprint). The trade-off is worker-thread consumption vs rewrite cost — `to_thread` is a debt, not a free pass.

**Commitment:** `boardly` uses `asyncio.to_thread` for two legacy sync calls — the old internal `requests`-based project service (waiting to be migrated to `httpx`) and a vendored sync billing SDK (no async equivalent). For the long-term HTTP path, `boardly` uses `httpx.AsyncClient` (a single client per process, shared across requests). For the CPU-bound SHA-256 of large audit logs, `boardly` uses a `ProcessPoolExecutor` with `max_workers=4` (bounded to leave CPU for the loop). The default `ThreadPoolExecutor` (from `to_thread`) is used for short-lived calls only; for sustained concurrency, a custom executor with a known `max_workers` is the right choice.

**Why use `to_thread` for the legacy sync code and not rewrite it?** Because the rewrite is a project, not a refactor. The `requests`-based project service has 2,000 lines of business logic around the HTTP calls — retry policies, response shaping, error mapping. Rewriting it to `httpx.AsyncClient` means rewriting all of that, testing it, and shipping it — a sprint of work for one migration. `to_thread(requests.get, url)` is a one-line wrapper that unblocks the loop today; the rewrite can happen on the next sprint. The trade-off is worker-thread consumption (the default executor caps at 6 on this sandbox, 20 on a 16-core box) — which is enough for boardly's current request rate but will need to scale before the rewrite.

## Exercises

1. **Exercise 1 — Measure the frozen loop.** In `wrong_way`, add a heartbeat coroutine that prints "tick" every 10ms during the call. Run and confirm no ticks print during the 50ms blocking call. `Verify: uv run python boardly/asyncio_to_thread_demo.py`

2. **Exercise 2 — Time `to_thread` vs `run_in_executor`.** Use `time.perf_counter` to compare `to_thread_way` and `run_in_executor_way` for the same call. Confirm they take the same wall time (the implementation is the same — `to_thread` is sugar). `Verify: uv run python boardly/asyncio_to_thread_demo.py`

3. **Exercise 3 — Verify the default executor cap.** Submit 100 concurrent `to_thread` calls (each `time.sleep(0.05)`). Time the gather. Confirm it takes ~17 batches of 6 (the default `max_workers` on this sandbox) ≈ 850ms. `Verify: uv run python boardly/asyncio_to_thread_demo.py`

4. **Exercise 4 — Use a `ProcessPoolExecutor` for CPU work.** Replace `time.sleep` with `sum(i*i for i in range(10**7))` (CPU-bound). Confirm `to_thread` does NOT keep the loop responsive (GIL held). Switch to `ProcessPoolExecutor` and confirm the loop is responsive again. `Verify: uv run python boardly/asyncio_to_thread_demo.py`

5. **Exercise 5 — Migrate `sync_get` to `httpx.AsyncClient`.** Install `httpx` (`uv add httpx`), replace the `to_thread(sync_get, url)` call with `async with httpx.AsyncClient() as c: r = await c.get(url)`. Confirm the same 200 status with no worker thread consumed. `Verify: uv run python boardly/asyncio_to_thread_demo.py`

## Verification

```bash
$ uv run python boardly/asyncio_to_thread_demo.py
=== WRONG way: blocking call in async (loop frozen) ===
  [wrong_way] start blocking call (loop is frozen)
  [wrong_way] alpha
=== concurrent to_thread (loop stays responsive) ===
    heartbeat tick 0
    heartbeat tick 1
    heartbeat tick 2
    heartbeat tick 3
    heartbeat tick 4
  results: ['alpha', 'beta', 'gamma']

=== the rule: don't call requests.get in async ===
  sync_get via to_thread -> 200
  default ThreadPoolExecutor max_workers = min(32, os.cpu_count() + 4) = 6
```

## Previously Learned Here

- [[21-asyncio-primitives/01-Task-gather-wait_for]] — `create_task` and `gather` are how you turn multiple `to_thread` calls into concurrent worker threads. The `gather(*[to_thread_way(s) for s in slugs])` pattern is the bridge between the two lessons.
- [[03-contextlib/02-asynccontextmanager]] — the `async with` protocol that `httpx.AsyncClient` uses. The long-term answer to "don't call `requests.get` in async" is an `async with httpx.AsyncClient() as c:` block — `__aenter__` opens the client, `__aexit__` closes it, the `await c.get(...)` calls in between use the async I/O the client owns.

## What's Next

This is the last lesson in the `21-asyncio-primitives` section. The five lessons together cover the concurrency toolkit FastAPI's event loop is built on: `create_task`/`gather`/`wait_for` (lesson 01), `Lock`/`Event` (lesson 02), `Queue` (lesson 03), `Semaphore`/`Condition` (lesson 04), and `to_thread`/`run_in_executor` (this lesson).

The natural next sections are:

- **[[23-logging/04-Uvicorn-logging-integration]]** — how FastAPI's logging integrates with Uvicorn's process model. The asyncio event loop is per-process; the logging integration has to know about thread/loop boundaries.
- **[[25-Reference-Library/Engineering-Decision-Log]]** — the canonical place where boardly records "we use `to_thread` for the legacy `requests` calls; we will migrate to `httpx.AsyncClient` in the next sprint". The Decision Log is the long-term memory of the project's engineering commitments.

## Sources

- **`asyncio` — `to_thread`** — https://docs.python.org/3.12/library/asyncio-task.html#asyncio.to_thread — accessed 2026-10-23 — the canonical reference, added in 3.9. Documents the `func, /, *args, **kwargs` signature and the default-executor behaviour.
- **`asyncio` — `loop.run_in_executor`** — https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.run_in_executor — accessed 2026-10-23 — the lower-level form, with `executor=None` using the default executor.
- **`concurrent.futures.ThreadPoolExecutor`** — https://docs.python.org/3.12/library/concurrent.futures.html#threadpoolexecutor — accessed 2026-10-23 — the executor class; documents the `max_workers = min(32, os.cpu_count() + 4)` default formula (since 3.8) and the `shutdown(wait=True)` behaviour on `__exit__`.
- **`httpx` — Async support** — https://www.python-httpx.org/async/ — accessed 2026-10-23 — the long-term async HTTP client. The right answer for new code; the migration target for legacy `requests` code.

## What We Learned

- You can use `asyncio.to_thread(func, *args, **kwargs)` to call blocking sync code from async without freezing the loop.
- You can use `loop.run_in_executor(executor, func, *args)` for the lower-level form, with `executor=None` for the default or a custom `ThreadPoolExecutor` for bounded concurrency.
- You can state the "don't call `requests.get` in async" rule and name both fixes (`to_thread` for migration, `httpx.AsyncClient` for the long term).
- You can state the default `ThreadPoolExecutor` formula (`min(32, os.cpu_count() + 4)` since 3.8) and explain the 32 cap.
- You can distinguish I/O-bound blocking (releases the GIL — `to_thread` works) from CPU-bound work (holds the GIL — needs `ProcessPoolExecutor`).
- You can choose between `to_thread` and `run_in_executor` and explain when each wins.
