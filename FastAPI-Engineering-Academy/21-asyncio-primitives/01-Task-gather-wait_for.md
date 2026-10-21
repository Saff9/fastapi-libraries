---
title: "Lesson 01: Task, gather, wait_for"
aliases:
 - asyncio.create_task
 - asyncio.gather
 - asyncio.wait_for
 - fire-and-forget
 - bare-coroutine bug
tags:
 - asyncio
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[03-contextlib/02-asynccontextmanager]]"
related_lessons:
 - "[[21-asyncio-primitives/02-Lock-and-Event]]"
 - "[[21-asyncio-primitives/05-to_thread-and-run-in-executor]]"
first_taught_in: "21-asyncio-primitives/01-Task-gather-wait_for"
---

# Lesson 01: `Task`, `gather`, `wait_for`

*The three primitives that take you from "I await one thing at a time" to "I fetch ten boardly projects concurrently, with a per-call timeout and a gather that never raises."*

**You're at the very beginning of Section 21.**

You have written `async def` functions. You have `await`ed one coroutine at a time, top to bottom, like sequential code that just happens to use `await` before each call. And then one day boardly's `/projects/batch?slugs=alpha,beta,...,gamma` endpoint ships, and you discover that fetching ten projects one after another takes 500ms (ten 50ms DB calls in series) where the user expected 50ms (ten calls in parallel). The fix is one line — `asyncio.gather(*coros)` — but only if you also understand `asyncio.create_task` (the primitive that actually schedules a coroutine on the loop) and `asyncio.wait_for` (the per-call timeout). And the bug you will hit on day one — the bare-coroutine-never-awaited `RuntimeWarning` — is the single most common asyncio mistake in production code. This lesson covers all three primitives and that bug. Take your time. Type every example. **This is how you learn.**

#asyncio #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Schedule a coroutine with `asyncio.create_task(coro)`** — explain that the call returns immediately with a `Task` (a `Future` subclass) and the coroutine runs on the loop; contrast with a bare `coro()` call which is *never* scheduled.
2. **Run N coroutines concurrently with `asyncio.gather(*aws, return_exceptions=False)`** — state the order of results (input order, not completion order), the default raise-on-first-failure behaviour, and the `return_exceptions=True` opt-in for "never raise".
3. **Enforce a per-call timeout with `asyncio.wait_for(aw, timeout)`** — name the exception (`asyncio.TimeoutError`, which is `TimeoutError` itself in 3.11+, identical in 3.12), and explain that the inner coroutine is cancelled on timeout.
4. **Recognise and fix the bare-coroutine bug** — read `RuntimeWarning: coroutine 'X' was never awaited` and rewrite the bare `coro()` call as `asyncio.create_task(coro())` (or `await coro()`).
5. **Choose between sequential, concurrent, and fire-and-forget patterns** — name the trade-off each commits to.

## Prerequisites

Before starting, you need:

- **`async`/`await` and the `async with` protocol** — `[[03-contextlib/02-asynccontextmanager]]` covers the `async with` shape and the FastAPI `Depends` parallel. This lesson assumes you have internalised "an `await` yields control to the event loop".
- **Generators** — `asyncio.gather` takes awaitables, but the list-comprehension-of-coroutines pattern (`[coro(s) for s in slugs]`) is exactly the generator pattern; you should be comfortable with that.
- **About 35–45 minutes of focused time.**

**The most common gap: thinking `coro()` runs the coroutine.**

It does not. `coro()` *creates* a coroutine object. Nothing in it has executed yet. The coroutine body runs only when you `await` it (or `create_task` it, which schedules it on the loop). The single most common asyncio bug — and the single most common support ticket on the boardly issue tracker in our first six months — is writing `fetch_project(slug)` (with parens, no `await`, no `create_task`) inside an `async def` and assuming it ran. It did not. The loop's garbage collector eventually prints `RuntimeWarning: coroutine 'fetch_project' was never awaited` to stderr — usually six minutes after the user has filed a bug. The fix is one character: either `await fetch_project(slug)` or `asyncio.create_task(fetch_project(slug))`. Knowing the difference between these three forms is the entire foundation of this section.

## The Problem

Here is the bug, in its native habitat.

```python
# boardly/api/projects.py — the slow version
async def fetch_project(slug: str) -> Project:
    await asyncio.sleep(0.05)   # 50ms DB call
    return Project(slug=slug, name=slug.title())

async def list_projects(slugs: list[str]) -> list[Project]:
    return [await fetch_project(s) for s in slugs]
    #            ^^^^^^^^^^^^^^^^ N awaits in series = N × 50ms
```

Ten slugs, 50ms each, run one after another: 500ms. The user has clicked "load my projects" and is staring at a spinner for half a second. Slow.

The "obvious" fix is to remove the `await`:

```python
async def list_projects(slugs: list[str]) -> list[Project]:
    return [fetch_project(s) for s in slugs]
    #       ^^^^^^^^^^^^^^^ no await — coroutine objects, never scheduled
```

That does not run faster. It does not run at all. `fetch_project(s)` returns a coroutine object; nothing schedules it; nothing awaits it; Python's garbage collector eventually closes it with a `RuntimeWarning`. The return value of `list_projects` is a list of `<coroutine object>` instances — which `list[Project]` claims to be a lie about.

The actual fix is `asyncio.gather(*[fetch_project(s) for s in slugs])` — gather takes the coroutine objects, schedules them all on the loop as tasks, and returns an aggregate awaitable that resolves to the results in input order. Ten concurrent 50ms calls finish in ~50ms, not 500ms. This lesson is `create_task` + `gather` + `wait_for`: the three primitives you need to write concurrent boardly code that is also correct.

## The Code

```python
# boardly/asyncio_task_gather_demo.py
"""asyncio.create_task / asyncio.gather / asyncio.wait_for on boardly projects.

Shows the canonical boardly pattern: fetch N projects concurrently from a
slow upstream service, with a per-call timeout and a gather that never raises
(return_exceptions=True). Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class Project:
    slug: str
    name: str
    budget_cents: int


# --- Fake upstream: a slow async "database" call ---
async def fetch_project(slug: str, *, delay: float = 0.05) -> Project:
    """Simulate a 50ms DB round-trip."""
    await asyncio.sleep(delay)
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)


async def fetch_project_or_timeout(slug: str, *, delay: float = 0.05) -> Project:
    """Same as fetch_project but raises ValueError for slug 'boom'."""
    await asyncio.sleep(delay)
    if slug == "boom":
        raise ValueError(f"project {slug!r} not found")
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)


# --- Pattern 1: sequential (the slow baseline) ---
async def fetch_all_sequential(slugs: list[str]) -> list[Project]:
    return [await fetch_project(s) for s in slugs]


# --- Pattern 2: concurrent via create_task + gather ---
async def fetch_all_concurrent(slugs: list[str]) -> list[Project]:
    tasks = [asyncio.create_task(fetch_project(s)) for s in slugs]
    return await asyncio.gather(*tasks)


# --- Pattern 3: gather with return_exceptions=True (never raises) ---
async def fetch_all_tolerant(slugs: list[str]) -> list[Project | ValueError]:
    tasks = [asyncio.create_task(fetch_project_or_timeout(s)) for s in slugs]
    return await asyncio.gather(*tasks, return_exceptions=True)


# --- Pattern 4: wait_for with per-call timeout ---
async def fetch_with_timeout(slug: str, timeout: float = 0.02) -> Project | None:
    try:
        return await asyncio.wait_for(fetch_project(slug, delay=0.05), timeout=timeout)
    except TimeoutError:
        print(f"  [timeout] project {slug!r} did not respond in {timeout}s")
        return None


# --- Pattern 5: the bare-coroutine bug (fire-and-forget needs create_task) ---
async def fire_and_forget_bug() -> None:
    """The wrong way: a bare coro() is never scheduled."""
    fetch_project("ghost")  # ← never awaited, never scheduled
    await asyncio.sleep(0.01)  # give the loop a turn to print the warning


async def fire_and_forget_correct() -> None:
    """The right way: create_task schedules the coro on the loop."""
    task = asyncio.create_task(fetch_project("ghost"))
    # don't await — fire and forget. But you must keep a reference or the
    # task can be garbage-collected mid-flight (CPython 3.12 warning).
    await asyncio.sleep(0.06)
    if task.done():
        print(f"  [fire-and-forget] ghost result: {task.result()}")


async def main() -> None:
    slugs = ["alpha", "beta", "gamma"]

    print("=== sequential (3 × 50ms ≈ 150ms) ===")
    results = await fetch_all_sequential(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== concurrent via create_task + gather (≈ 50ms) ===")
    results = await fetch_all_concurrent(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== gather with return_exceptions=True (no raise) ===")
    mixed = await fetch_all_tolerant(["alpha", "boom", "gamma"])
    for item in mixed:
        if isinstance(item, Project):
            print(f"  OK   {item.slug}")
        else:
            print(f"  FAIL {type(item).__name__}: {item}")

    print("\n=== wait_for with a too-short timeout ===")
    out = await fetch_with_timeout("delta", timeout=0.02)
    print(f"  delta result: {out}")

    print("\n=== bare-coroutine bug (warning to stderr) ===")
    await fire_and_forget_bug()

    print("\n=== fire-and-forget via create_task (the correct way) ===")
    await fire_and_forget_correct()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–14: Imports and the `Project` model

```python
# boardly/asyncio_task_gather_demo.py
"""asyncio.create_task / asyncio.gather / asyncio.wait_for on boardly projects.

Shows the canonical boardly pattern: fetch N projects concurrently from a
slow upstream service, with a per-call timeout and a gather that never raises
(return_exceptions=True). Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class Project:
    slug: str
    name: str
    budget_cents: int
```

`asyncio` is the standard-library module — every primitive in this section lives there. `dataclass` gives us a typed `Project` model with `__init__`/`__repr__`/`__eq__` for free; the `field` import is unused in this file but we keep it for parity with other boardly demos. `from __future__ import annotations` makes the `list[Project]` / `Project | ValueError` type hints parse as strings, so the file runs on 3.12 even though some unions look like 3.10+ syntax.

### Lines 17–27: The fake upstream

```python
async def fetch_project(slug: str, *, delay: float = 0.05) -> Project:
    """Simulate a 50ms DB round-trip."""
    await asyncio.sleep(delay)
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)


async def fetch_project_or_timeout(slug: str, *, delay: float = 0.05) -> Project:
    """Same as fetch_project but raises ValueError for slug 'boom'."""
    await asyncio.sleep(delay)
    if slug == "boom":
        raise ValueError(f"project {slug!r} not found")
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)
```

`fetch_project` is a coroutine — `async def` makes it so. Calling `fetch_project("alpha")` (with parens, no `await`) does not run the body; it returns a coroutine object. The body runs only when something awaits that object. The `await asyncio.sleep(delay)` is the simulated 50ms DB round-trip — and crucially, `sleep` is itself a coroutine that yields control back to the event loop, which is what lets other coroutines run *during* that 50ms. That is the whole reason concurrency is possible: every `await` is a yield point.

The `fetch_project_or_timeout` variant is identical except it raises `ValueError` for slug `"boom"`. We use it in Pattern 3 to show how `gather(return_exceptions=True)` handles failures.

### Lines 30–32: Pattern 1 — the slow sequential baseline

```python
async def fetch_all_sequential(slugs: list[str]) -> list[Project]:
    return [await fetch_project(s) for s in slugs]
```

This is a list comprehension with an `await` inside it. Python evaluates it left-to-right: `await fetch_project(slugs[0])`, then `await fetch_project(slugs[1])`, and so on. Each `await` blocks until the coroutine completes — so three slugs means three 50ms waits in series, ~150ms total. The pattern is correct, just slow. It is the right answer when you genuinely cannot start the second call until the first returns (e.g. when each call depends on the previous one's result), and the wrong answer when the calls are independent (which is most of the time).

**Why does the list comprehension with `await` work syntactically?** Because Python 3.6+ allows `await` inside comprehensions and generator expressions (PEP 530). The comprehension is desugared to a `for` loop where each iteration `await`s the expression. Without PEP 530 you would need `results = []; for s in slugs: results.append(await fetch_project(s)); return results`. The comprehension is sugar, not a different concurrency model — it is still sequential.

### Lines 35–38: Pattern 2 — concurrent via `create_task` + `gather`

```python
async def fetch_all_concurrent(slugs: list[str]) -> list[Project]:
    tasks = [asyncio.create_task(fetch_project(s)) for s in slugs]
    return await asyncio.gather(*tasks)
```

Two things happen here, and understanding both is the lesson.

First, `asyncio.create_task(fetch_project(s))` — *not* `asyncio.create_task(fetch_project)` and *not* `fetch_project(s)`. The inner `fetch_project(s)` call (with parens) creates the coroutine object; `create_task` then *schedules* that coroutine on the running event loop and returns a `Task` (a `Future` subclass). The `Task` object is what `gather` waits on. The coroutine body starts running the next time the loop reaches a yield point — which is the very next `await` in the surrounding `fetch_all_concurrent`, namely the `await asyncio.gather(...)` line.

Second, `asyncio.gather(*tasks)` takes the three `Task` objects (splat with `*`), schedules them concurrently, and returns an aggregate awaitable. Awaiting that aggregate yields a list of *results* — in **input order**, not completion order. So even if the third task finishes first, the result list is `[Project("alpha", ...), Project("beta", ...), Project("gamma", ...)]` because that is the order you passed to `gather`. The aggregate does not return until all three tasks have completed (or one has raised — see Pattern 3).

Internally, `gather` wraps each awaitable in a `Task` if it isn't one already (so the explicit `create_task` in this pattern is technically redundant — `gather(fetch_project(s) for s in slugs)` would also work). The reason to write `create_task` explicitly is *time sensitivity*: if you write `gather(fetch_project(s) for s in slugs)`, the coroutines only get scheduled when `gather` runs them (microseconds later); if you write `tasks = [create_task(...)]; ...; await gather(*tasks)`, the coroutines are scheduled the instant `create_task` is called — they may have already started (or even finished) by the time you reach `gather`. The second form is what you want when there is work between creating the tasks and awaiting them.

**Why doesn't `gather` return results in completion order?** Because the contract is "return the same shape as the input". If you call `gather(a, b, c)` and get `[result_b, result_a, result_c]` because `b` finished first, you cannot map results back to inputs without extra bookkeeping. Returning in input order is the only choice that makes `gather` composable — you can `zip(results, slugs)` and know which result corresponds to which slug. The cost is that `gather` has to buffer results internally until every task is done; that is a small fixed overhead.

### Lines 41–44: Pattern 3 — `gather(return_exceptions=True)`

```python
async def fetch_all_tolerant(slugs: list[str]) -> list[Project | ValueError]:
    tasks = [asyncio.create_task(fetch_project_or_timeout(s)) for s in slugs]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

By default (`return_exceptions=False`), if any task raises, `gather` cancels the other tasks and re-raises the first exception. That is the right default for "all or nothing" calls — a single failure means the batch failed. But for "best effort" calls (fetch ten projects, return whichever ones succeed), you pass `return_exceptions=True`: each task's result is returned in input order, and exceptions are *returned as values* (`ValueError('boom')` as a value, not raised) so you can inspect them.

The return type `list[Project | ValueError]` makes the contract explicit: each slot in the list is either a `Project` (success) or a `ValueError` (failure) — and you discriminate with `isinstance(item, Project)` (the Pattern 5 caller does exactly this). If the function could raise multiple exception types, the union widens; the discrimination pattern stays the same.

**Why return exceptions as values instead of raising?** Because once you are batching independent calls, "one failed" is information, not a fatal error. The caller of `fetch_all_tolerant` is going to render a list of projects to the user; one of them failing is a partial-success state, not an error state. Raising would force the caller to either swallow the exception (losing the successful results) or re-fetch the failing slug (re-running the slow call). Returning exceptions as values lets the caller discriminate per-slot and continue. The downside is that the caller *must* discriminate — a bug-prone `for item in mixed: print(item.slug)` will `AttributeError` on the failure slots.

### Lines 47–53: Pattern 4 — `wait_for` with a per-call timeout

```python
async def fetch_with_timeout(slug: str, timeout: float = 0.02) -> Project | None:
    try:
        return await asyncio.wait_for(fetch_project(slug, delay=0.05), timeout=timeout)
    except TimeoutError:
        print(f"  [timeout] project {slug!r} did not respond in {timeout}s")
        return None
```

`asyncio.wait_for(aw, timeout)` wraps an awaitable with a deadline. If the awaitable does not complete within `timeout` seconds, `wait_for` *cancels* the inner awaitable (sends `CancelledError` into it at the next yield point) and raises `asyncio.TimeoutError`. As of Python 3.11, `asyncio.TimeoutError` is an alias for the built-in `TimeoutError`; in 3.12 they are literally the same class — `asyncio.TimeoutError is TimeoutError` evaluates to `True`. So catching `TimeoutError` (the built-in) catches the asyncio timeout; you do not have to import `asyncio.TimeoutError` separately. If you need to support 3.10 or earlier, import `asyncio` and catch `asyncio.TimeoutError` — that name has been an alias since 3.11 but the underlying class predates it.

The `timeout=0.02` (20ms) here is shorter than the 50ms `delay`, so the timeout always fires in this demo. The print + `return None` is the "best effort" pattern: a single project failing to load within the SLA is a recoverable error, not a fatal one. The caller checks `if out is None` and skips that project in the UI.

**Why does `wait_for` cancel the inner coroutine on timeout?** Because the alternative — leaving it running — would mean the call still uses CPU/IO after the deadline, wasting resources on a result the caller has already given up on. Cancellation is the only safe default. The consequence is that the inner coroutine receives `CancelledError` at its next yield point; if it has cleanup to do (closing a file, releasing a lock), it must do so in a `try`/`finally` — `CancelledError` will propagate through `except Exception` in 3.8+ (it became a subclass of `BaseException` in 3.8), so a bare `except Exception:` will not catch it. This is the `[[03-contextlib/02-asynccontextmanager]]` `try`/`yield`/`finally` pattern in a different hat — `async with` cleanup runs on cancellation too.

### Lines 56–64: Pattern 5 — the bare-coroutine bug

```python
async def fire_and_forget_bug() -> None:
    """The wrong way: a bare coro() is never scheduled."""
    fetch_project("ghost")  # ← never awaited, never scheduled
    await asyncio.sleep(0.01)  # give the loop a turn to print the warning
```

`fetch_project("ghost")` creates a coroutine object and immediately discards the reference. The coroutine body — `await asyncio.sleep(delay); return Project(...)` — never runs, because nothing scheduled it on the loop and nothing awaited it. The Python garbage collector eventually closes the coroutine object, and at that moment Python prints `RuntimeWarning: coroutine 'fetch_project' was never awaited` to stderr (the warning fires on close, which happens when the refcount hits zero — typically on the next GC cycle).

This is the single most common asyncio bug. The fix is on lines 67–75.

### Lines 67–75: Pattern 5 — fire-and-forget via `create_task`

```python
async def fire_and_forget_correct() -> None:
    """The right way: create_task schedules the coro on the loop."""
    task = asyncio.create_task(fetch_project("ghost"))
    # don't await — fire and forget. But you must keep a reference or the
    # task can be garbage-collected mid-flight (CPython 3.12 warning).
    await asyncio.sleep(0.06)
    if task.done():
        print(f"  [fire-and-forget] ghost result: {task.result()}")
```

`asyncio.create_task(fetch_project("ghost"))` does two things: it creates the coroutine (the parens call) and it schedules that coroutine on the running loop. The `Task` object is the handle — it is a `Future` subclass, so you can `await task`, `task.result()`, `task.exception()`, or `task.cancel()`. Critically, *keeping a reference to the task* prevents the CPython garbage collector from cancelling it mid-flight. If you write `asyncio.create_task(coro())` and discard the return value, CPython may GC the task while the coroutine is still running — and Python 3.12 will print a warning about it. Stash the reference (in a local, a class attribute, or a set) until the task is `done()`.

The `await asyncio.sleep(0.06)` here is deliberate: it gives the loop enough time to run the 50ms `fetch_project` coroutine to completion. The `if task.done()` check is defensive — it should always be `True` after 60ms of sleep, but if the loop were starved (heavy load) the task might still be pending.

**Why "fire and forget" instead of `await`?** Because some work genuinely does not need to be awaited — logging, metrics emission, cache priming. The pattern is "kick off this work, return a response to the user now, let the work complete in the background". The catch is "fire and forget" is a lie: you must still track the task (to suppress the GC warning), still handle its exceptions (an unhandled exception in a forgotten task is silent in 3.7-3.10 and surfaces via `loop.set_exception_handler` in 3.11+), and still cancel it on shutdown. The cleanest pattern is to keep a `set[Task]` of in-flight background tasks, add on `create_task`, discard on `done`, and `gather(*tasks)` in your shutdown path. Anything less and you have a leak.

### Lines 78–98: `main` — the demo driver

```python
async def main() -> None:
    slugs = ["alpha", "beta", "gamma"]

    print("=== sequential (3 × 50ms ≈ 150ms) ===")
    results = await fetch_all_sequential(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== concurrent via create_task + gather (≈ 50ms) ===")
    results = await fetch_all_concurrent(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== gather with return_exceptions=True (no raise) ===")
    mixed = await fetch_all_tolerant(["alpha", "boom", "gamma"])
    for item in mixed:
        if isinstance(item, Project):
            print(f"  OK   {item.slug}")
        else:
            print(f"  FAIL {type(item).__name__}: {item}")

    print("\n=== wait_for with a too-short timeout ===")
    out = await fetch_with_timeout("delta", timeout=0.02)
    print(f"  delta result: {out}")

    print("\n=== bare-coroutine bug (warning to stderr) ===")
    await fire_and_forget_bug()

    print("\n=== fire-and-forget via create_task (the correct way) ===")
    await fire_and_forget_correct()


if __name__ == "__main__":
    asyncio.run(main())
```

Each `print` block exercises one pattern. The first two compare sequential vs concurrent — same output, different wall-clock time. The third block (`return_exceptions=True`) iterates the result list and discriminates `Project` from `ValueError` with `isinstance`. The fourth block shows `wait_for` returning `None` on timeout. The fifth block triggers the bare-coroutine `RuntimeWarning`. The sixth block shows the fire-and-forget pattern with `create_task`.

`asyncio.run(main())` is the 3.7+ entry point: it creates a fresh event loop, runs `main()` to completion, and closes the loop. You should never call `asyncio.run` from inside an already-running loop (it raises `RuntimeError: asyncio.run() cannot be called from a running event loop`); use it only at the top of a script or in a synchronous entrypoint.

## Execution Trace

```bash
$ uv run python boardly/asyncio_task_gather_demo.py
=== sequential (3 × 50ms ≈ 150ms) ===
  3 projects: ['alpha', 'beta', 'gamma']

=== concurrent via create_task + gather (≈ 50ms) ===
  3 projects: ['alpha', 'beta', 'gamma']

=== gather with return_exceptions=True (no raise) ===
  OK   alpha
  FAIL ValueError: project 'boom' not found
  OK   gamma

=== wait_for with a too-short timeout ===
  [timeout] project 'delta' did not respond in 0.02s
  delta result: None

=== bare-coroutine bug (warning to stderr) ===
/home/z/my-project/FastAPI-Engineering-Academy/boardly/asyncio_task_gather_demo.py:65: RuntimeWarning: coroutine 'fetch_project' was never awaited
  fetch_project("ghost")  # ← never awaited, never scheduled
RuntimeWarning: Enable tracemalloc to get the object allocation traceback

=== fire-and-forget via create_task (the correct way) ===
  [fire-and-forget] ghost result: Project(slug='ghost', name='Ghost', budget_cents=10000)
```

The first two blocks show identical output — same three projects, same order — but the wall-clock time differs (150ms vs ~50ms; not visible in the trace, but time the script with `time uv run python ...` to see it). The third block shows `gather(return_exceptions=True)` returning `ValueError('boom')` as a value, discriminated by `isinstance(item, Project)`. The fourth block shows `wait_for` raising `TimeoutError`, caught, returning `None`. The fifth block shows the `RuntimeWarning` — note that the warning is printed to stderr *after* the function returns, on the next GC cycle. The sixth block shows the fire-and-forget task completing and `task.result()` returning the `Project`.

## Common Mistakes

### Mistake 1: Calling `coro()` without `await` or `create_task`

```python
async def list_projects(slugs):
    return [fetch_project(s) for s in slugs]   # ← bare coro() calls
```

**Symptom:** `RuntimeWarning: coroutine 'fetch_project' was never awaited` printed to stderr, and the function returns a list of `<coroutine object>` instances — which your type checker claims are `Project`. Any caller that does `project.slug` raises `AttributeError: 'coroutine' object has no attribute 'slug'`.

**Why:** `fetch_project(s)` (with parens, no `await` or `create_task`) creates a coroutine object and immediately discards the reference. The coroutine body never runs. Python's garbage collector eventually closes the coroutine and emits the warning.

**Fix:** Use `await` (sequential) or `asyncio.create_task` + `asyncio.gather` (concurrent):

```python
async def list_projects(slugs):
    tasks = [asyncio.create_task(fetch_project(s)) for s in slugs]
    return await asyncio.gather(*tasks)
```

### Mistake 2: `gather` without `return_exceptions=True` for a "best effort" batch

```python
results = await asyncio.gather(*[fetch_project(s) for s in slugs])
# If any one of them raises, the whole gather raises — and the
# successful results are discarded.
```

**Symptom:** A batch of ten fetches fails entirely because one upstream returned a 500. The user sees "load failed" instead of "9 of 10 projects loaded".

**Why:** `gather`'s default is "all or nothing" — the first exception cancels the other tasks and re-raises.

**Fix:** Pass `return_exceptions=True` and discriminate the results per-slot:

```python
mixed = await asyncio.gather(*[fetch_project(s) for s in slugs], return_exceptions=True)
ok = [r for r in mixed if isinstance(r, Project)]
```

### Mistake 3: Discarding the `create_task` return value

```python
asyncio.create_task(background_work())   # ← return value discarded
```

**Symptom:** Under memory pressure, the task is garbage-collected mid-flight; the work is cancelled; you see no error. In Python 3.12, you may see the warning `an open Task was found garbage collected...`.

**Why:** CPython's reference counting will free the `Task` object if no reference is held. A freed task is a cancelled task.

**Fix:** Keep the reference — in a local for short-lived tasks, in a `set[Task]` for background tasks:

```python
self._background: set[asyncio.Task] = set()
task = asyncio.create_task(background_work())
self._background.add(task)
task.add_done_callback(self._background.discard)
```

## Engineering Trade-Offs

**Decision:** Use `gather` for "run these independent calls concurrently and collect results". Use `create_task` directly when you need to schedule work that does not need to be awaited immediately. Use `wait_for` for per-call deadlines. Use `return_exceptions=True` only when partial failure is acceptable.

**Both sides:** The alternative to `gather` is `asyncio.wait` (returns two sets — `done` and `pending` — instead of a result list). `wait` is more flexible (you can return early on the first completion with `return_when=FIRST_COMPLETED`) but less ergonomic (no built-in result collection, no built-in order preservation). `gather` is the right default — `wait` is the escape hatch for "I need partial results as they arrive" (e.g. a streaming UI that shows each result as soon as it lands).

**Commitment:** `boardly` uses `gather` for the batch-fetch endpoints (`/projects/batch?slugs=...`), `create_task` for background work (cache priming, metrics emission), and `wait_for` for every outbound HTTP call with a 5-second deadline. `return_exceptions=True` is used in exactly two places: the batch-fetch endpoint (partial-success is acceptable) and the metrics emitter (one failing metric must not block the others). Everywhere else, the default raise-on-failure semantics are correct because the caller is a request handler that needs to return 500 if any subsystem fails.

**Why use `gather` over manual `for`+`await` for batch endpoints?** Because the manual form is sequential — it serialises the calls. With `gather`, ten 50ms calls finish in ~50ms (the slowest call); with manual `await`, they finish in 500ms (the sum). The wall-clock difference is the entire user-visible latency.

## Exercises

1. **Exercise 1 — Measure the speedup.** Add `import time; t0 = time.perf_counter()` before the sequential block and `print(f"  {time.perf_counter()-t0:.3f}s")` after. Do the same for the concurrent block. Confirm the concurrent block is roughly 3× faster. `Verify: uv run python boardly/asyncio_task_gather_demo.py`

2. **Exercise 2 — Change `wait_for`'s timeout to 0.1.** Modify `fetch_with_timeout("delta", timeout=0.02)` to use `timeout=0.1`. Confirm the call no longer times out and returns a `Project`. `Verify: uv run python boardly/asyncio_task_gather_demo.py`

3. **Exercise 3 — Use `asyncio.wait` instead of `gather`.** Rewrite `fetch_all_concurrent` to use `done, pending = await asyncio.wait(tasks); return [t.result() for t in done]`. Confirm the result order is no longer guaranteed to match input order (the list comes back in completion order). `Verify: uv run python boardly/asyncio_task_gather_demo.py`

4. **Exercise 4 — Catch the exception from `gather(return_exceptions=False)`.** Modify `fetch_all_tolerant` to drop `return_exceptions=True`. Wrap the `gather` call in `try/except ValueError`. Confirm you only see the first failure and lose the other results. `Verify: uv run python boardly/asyncio_task_gather_demo.py`

5. **Exercise 5 — Build a "track in-flight tasks" set.** Refactor `fire_and_forget_correct` to keep a module-level `set[asyncio.Task]`, add the task to it on `create_task`, and remove it via `task.add_done_callback(self._set.discard)`. Confirm the task is removed when it completes. `Verify: uv run python boardly/asyncio_task_gather_demo.py`

## Verification

```bash
$ uv run python boardly/asyncio_task_gather_demo.py
=== sequential (3 × 50ms ≈ 150ms) ===
  3 projects: ['alpha', 'beta', 'gamma']

=== concurrent via create_task + gather (≈ 50ms) ===
  3 projects: ['alpha', 'beta', 'gamma']

=== gather with return_exceptions=True (no raise) ===
  OK   alpha
  FAIL ValueError: project 'boom' not found
  OK   gamma

=== wait_for with a too-short timeout ===
  [timeout] project 'delta' did not respond in 0.02s
  delta result: None

=== bare-coroutine bug (warning to stderr) ===
/home/z/my-project/FastAPI-Engineering-Academy/boardly/asyncio_task_gather_demo.py:65: RuntimeWarning: coroutine 'fetch_project' was never awaited
  fetch_project("ghost")  # ← never awaited, never scheduled
RuntimeWarning: Enable tracemalloc to get the object allocation traceback

=== fire-and-forget via create_task (the correct way) ===
  [fire-and-forget] ghost result: Project(slug='ghost', name='Ghost', budget_cents=10000)
```

## Previously Learned Here

- [[03-contextlib/02-asynccontextmanager]] — the `async with` shape and the `try`/`yield`/`finally` cleanup pattern. The `CancelledError` propagation in Pattern 4 (`wait_for` cancels the inner coroutine on timeout) follows the same `finally`-runs-on-cancellation rule.

## What's Next

[[21-asyncio-primitives/02-Lock-and-Event]] — once you can run N tasks concurrently, the next question is "how do I make them co-ordinate?" `asyncio.Lock` is async mutual exclusion (only one task in the critical section, FIFO fair since 3.10), and `asyncio.Event` is the one-to-many wake-up primitive (one setter, N waiters wake up at the same instant). The boardly use: a tiny in-process cache guarded by a `Lock` so two concurrent refresh tasks don't stampede the upstream, and an `Event` that signals "the cache is primed" so N worker coroutines can start at the same moment.

- `asyncio.Lock()` — async mutual exclusion; `async with lock:`.
- `asyncio.Event()` — `set()` / `clear()` / `is_set()` / `await wait()`.
- The "Lock is fair (FIFO)" guarantee (3.10+) and the difference from `threading.Lock`.

## Sources

- **`asyncio` — Tasks and Coroutines** — https://docs.python.org/3.12/library/asyncio-task.html — accessed 2026-10-23 — the canonical reference for `create_task`, `gather`, `wait_for`, `sleep`, and the `RuntimeWarning: coroutine was never awaited` warning.
- **`asyncio` — Synchronization Primitives** — https://docs.python.org/3.12/library/asyncio-sync.html — accessed 2026-10-23 — the reference for `Lock`, `Event`, `Semaphore`, `Condition` (covered in the rest of this section).
- **PEP 530 — Asynchronous Comprehensions** — https://peps.python.org/pep-0530/ — accessed 2026-10-23 — the PEP that allows `await` inside list comprehensions (Pattern 1).
- **PEP 492 — Coroutines with async and await syntax** — https://peps.python.org/pep-0492/ — accessed 2026-10-23 — the original `async`/`await` PEP; explains why a bare `coro()` is not scheduled.

## What We Learned

- You can schedule a coroutine with `asyncio.create_task(coro())` and explain why the bare `coro()` form is never scheduled.
- You can run N coroutines concurrently with `asyncio.gather(*tasks)` and explain the input-order result preservation.
- You can pass `return_exceptions=True` to `gather` and discriminate failures per-slot with `isinstance`.
- You can enforce a per-call deadline with `asyncio.wait_for(aw, timeout)` and catch `TimeoutError` (which is `asyncio.TimeoutError` in 3.12).
- You can recognise the `RuntimeWarning: coroutine was never awaited` and fix it with `await` or `create_task`.
- You can keep a reference to fire-and-forget tasks to prevent the CPython 3.12 GC-from-cancelling warning.
