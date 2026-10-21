---
title: "Lesson 02: asynccontextmanager"
aliases:
 - contextlib.asynccontextmanager
 - @asynccontextmanager
tags:
 - contextlib
 - asynccontextmanager
 - async
 - canonical
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "25–35 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
related_lessons:
 - "[[03-contextlib/05-contextvars]]"
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
first_taught_in: "03-contextlib/02-asynccontextmanager"
---

# Lesson 02: `@asynccontextmanager`

*The async sibling of `@contextmanager` — and the exact shape FastAPI's `Depends` async-generator dependencies use under the hood.*

**You're at the very beginning of Section 03.**

`contextlib.asynccontextmanager` (3.7+) is the async sibling of `@contextmanager`. It wraps an async generator in an `__aenter__`/`__aexit__` pair, lets you write `async with` blocks for async resources, and — the production-grade payoff — is the exact shape FastAPI uses for `yield`-based dependencies. When you write `async def get_db() -> AsyncIterator[Session]: yield session` and wire it into FastAPI via `Depends(get_db)`, Starlette internally does the equivalent of `async with asynccontextmanager(get_db)() as session:`. By the end of this lesson you will know the `async yield` shape, the `async with` interaction, and the precise FastAPI `Depends` parallel — including the manual teardown Starlette does on the async generator. Take your time. Type every example. **This is how you learn.**

#contextlib #asynccontextmanager #async #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@contextlib.asynccontextmanager`** to an async generator that yields exactly once, turning it into an async context manager.
2. **Use the `async with` interaction** — `__aenter__` returns the yielded value, `__aexit__` runs the `finally`.
3. **State the exception-rethrow behaviour** — exceptions in the `async with` body are thrown into the async generator at the `yield` point via `athrow`.
4. **Explain the FastAPI `Depends` async-generator parallel** — FastAPI dependencies use the same shape, and Starlette manages the lifecycle manually via `__anext__`/`athrow`.
5. **Choose between `@asynccontextmanager` and a class with `__aenter__`/`__aexit__`** — when each form wins for async resources.

## Prerequisites

Before starting, you need:

- **`async`/`await` and async generators** — `async def gen(): yield 1` should feel normal. If not, write a small async generator and `async for` over it before this lesson.
- **The `async with` protocol** — `async with x as y: ...` calls `await x.__aenter__()` to get `y`, runs the body, then calls `await x.__aexit__(*exc_info)`.
- **[[03-contextlib/01-contextmanager]] — the sync sibling** — the `@contextmanager` lesson. This lesson assumes you have read it.
- **About 25–35 minutes of focused time.**

**The most common gap: thinking `@asynccontextmanager` and `@contextmanager` are interchangeable.**

They're not. `@contextmanager` wraps a sync generator; `@asynccontextmanager` wraps an *async* generator. Using `@contextmanager` on an async function does nothing useful (the `yield` happens at the sync level, not the async level — the wrapped object is a sync context manager, not an async one). The two decorators target different protocols: `__enter__`/`__exit__` (sync) vs `__aenter__`/`__aexit__` (async).

## The Problem

You ship `boardly/db/session.py` with an async DB session. Callers use `async with db_session() as s: await s.query(...)` — they need the `await` inside the `with` for the actual database call. You have two options: write it as a class with `__aenter__`/`__aexit__`, or as an async generator with `@asynccontextmanager`. The class form is verbose (12 lines); the `@asynccontextmanager` form is 8 lines and reads top-to-bottom.

The bigger reason to learn `@asynccontextmanager`: FastAPI dependencies. When you write:

```python
async def get_db() -> AsyncIterator[Session]:
    async with engine.connect() as conn:
        yield conn

@app.get("/projects/{slug}")
async def get_project(slug: str, db: Session = Depends(get_db)):
    return await db.query(...)
```

The `get_db` function is *not* decorated with `@asynccontextmanager` — but Starlette internally wraps it as if it were, then drives the async generator's `__anext__`/`athrow` to enter and exit the dependency. Knowing the `@asynccontextmanager` shape is knowing how FastAPI manages your dependencies' lifecycles.

## The Code

```python
# boardly/asynccontextmanager_demo.py
"""Demonstrate contextlib.asynccontextmanager and the FastAPI Depends parallel."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any, AsyncIterator


# --- Fake async DB session ---
class FakeAsyncSession:
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.open = False
    async def __aenter__(self) -> "FakeAsyncSession":
        self.open = True
        print(f"  [session] opening {self.name}")
        return self
    async def __aexit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [session] closing {self.name}")
    async def query(self, slug: str) -> dict[str, str]:
        await asyncio.sleep(0.01)  # simulated async DB call
        return {"id": f"p_{slug}", "name": slug.title()}


# --- @asynccontextmanager form ---
@contextlib.asynccontextmanager
async def db_session(name: str = "default") -> AsyncIterator[FakeAsyncSession]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    session = FakeAsyncSession(name)
    await session.__aenter__()  # delegate to FakeAsyncSession's __aenter__
    try:
        yield session
    finally:
        await session.__aexit__(None, None, None)


# --- FastAPI Depends parallel: the async-generator shape ---
async def get_db() -> AsyncIterator[FakeAsyncSession]:
    """The FastAPI Depends shape: an async generator that yields exactly once."""
    session = FakeAsyncSession("boardly-fastapi")
    await session.__aenter__()
    try:
        yield session
    finally:
        await session.__aexit__(None, None, None)


async def normal_use() -> None:
    print("=== normal use ===")
    async with db_session("boardly-prod") as session:
        result = await session.query("auth")
        print(f"  query: {result}")


async def exception_in_body() -> None:
    print("\n=== exception in body — session still closes ===")
    try:
        async with db_session("boardly-prod") as session:
            print(f"  before raise: session.open = {session.open}")
            raise ValueError("something broke mid-query")
    except ValueError as e:
        print(f"  caught: {e}")


async def fastapi_depends_parallel() -> None:
    """Demonstrate the FastAPI Depends shape — manual lifecycle drive."""
    print("\n=== FastAPI Depends parallel (manual lifecycle) ===")
    gen = get_db()
    # __aenter__ equivalent: advance the generator to the yield
    session = await gen.__anext__()
    try:
        result = await session.query("billing")
        print(f"  query: {result}")
    finally:
        # __aexit__ equivalent: advance again, expect StopAsyncIteration
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass  # this is the expected end-of-generator signal


async def main() -> None:
    await normal_use()
    await exception_in_body()
    await fastapi_depends_parallel()


if __name__ == "__main__":
    asyncio.run(main())
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports

```python
# boardly/asynccontextmanager_demo.py
"""Demonstrate contextlib.asynccontextmanager and the FastAPI Depends parallel."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any, AsyncIterator
```

`asyncio` is for `asyncio.run(main())` and `asyncio.sleep`. `contextlib.asynccontextmanager` is the star — it's 3.7+ (added the same year as `async def` itself in 3.5 became widely deployed). `AsyncIterator` is the return type of an async generator function — `@asynccontextmanager` requires the wrapped function to be an async generator returning `AsyncIterator[T]`.

### Lines 11–22: A fake async session

```python
class FakeAsyncSession:
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.open = False
    async def __aenter__(self) -> "FakeAsyncSession":
        self.open = True
        print(f"  [session] opening {self.name}")
        return self
    async def __aexit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [session] closing {self.name}")
    async def query(self, slug: str) -> dict[str, str]:
        await asyncio.sleep(0.01)  # simulated async DB call
        return {"id": f"p_{slug}", "name": slug.title()}
```

`FakeAsyncSession` is an async context manager — it defines `__aenter__`/`__aexit__` as *async* methods (with `async def`). The `await` inside `__aenter__` (here just `asyncio.sleep`) models the async setup; in production this would be `await engine.connect()`. The `await asyncio.sleep(0.01)` inside `query` models an async DB round-trip — 10ms simulated latency.

### Lines 25–33: The `@asynccontextmanager` form

```python
@contextlib.asynccontextmanager
async def db_session(name: str = "default") -> AsyncIterator[FakeAsyncSession]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    session = FakeAsyncSession(name)
    await session.__aenter__()  # delegate to FakeAsyncSession's __aenter__
    try:
        yield session
    finally:
        await session.__aexit__(None, None, None)
```

`@contextlib.asynccontextmanager` wraps `db_session` (an async generator — it has `yield` and is `async def`) so that calling `db_session(...)` returns an `_AsyncGeneratorContextManager` object. That object implements `__aenter__` and `__aexit__`:

- `__aenter__` calls `await self.gen.__anext__()` — advances the async generator to the `yield`, returns the yielded value (`session`).
- `__aexit__` calls `await self.gen.athrow(*exc)` if `exc` is set, or `await self.gen.__anext__()` (expecting `StopAsyncIteration`) otherwise. The exception-handling semantics are identical to the sync `@contextmanager` form.

The `try`/`yield`/`finally` pattern is the same as in the sync lesson. The only differences: `await` prefixes every async operation, and the generator is `async def` instead of `def`.

**Why `await session.__aenter__()` instead of `session.__enter__()`?** Because `FakeAsyncSession` is an *async* context manager — it implements `__aenter__`/`__aexit__`, not `__enter__`/`__exit__`. The `await` is required because `__aenter__` is an async method that returns a coroutine. Mixing the two protocols is a common bug: calling `session.__enter__()` on an async session would return a coroutine that's never awaited.

### Lines 36–43: The FastAPI `Depends` parallel

```python
async def get_db() -> AsyncIterator[FakeAsyncSession]:
    """The FastAPI Depends shape: an async generator that yields exactly once."""
    session = FakeAsyncSession("boardly-fastapi")
    await session.__aenter__()
    try:
        yield session
    finally:
        await session.__aexit__(None, None, None)
```

`get_db` is *not* decorated with `@asynccontextmanager` — it's a plain async generator. But the shape is identical to `db_session` minus the decorator. This is the FastAPI `Depends` shape: an async generator that yields exactly once, with the `try`/`finally` cleanup.

When you write:

```python
async def get_project(slug: str, db: Session = Depends(get_db)):
    return await db.query(...)
```

FastAPI's `Depends` system resolves the dependency by:

1. Calling `get_db()` to create the async generator.
2. Calling `await gen.__anext__()` to advance to the `yield` — this is the "enter" phase.
3. Passing the yielded `session` to the route handler.
4. After the route handler returns, calling `await gen.athrow(...)` if the route raised, or `await gen.__anext__()` (expecting `StopAsyncIteration`) otherwise — this is the "exit" phase, which runs the `finally`.

So `get_db` is internally treated as if it were wrapped in `@asynccontextmanager` and used in `async with`. The benefit of writing it as a plain async generator (without `@asynccontextmanager`) is that FastAPI can drive the lifecycle itself — including cleanup that happens after the route response is sent, in a background task. With `@asynccontextmanager`, the lifecycle is bounded by the `async with` block.

### Lines 46–51: Normal use

```python
async def normal_use() -> None:
    print("=== normal use ===")
    async with db_session("boardly-prod") as session:
        result = await session.query("auth")
        print(f"  query: {result}")
```

The `async with db_session("boardly-prod") as session:` line:
1. Calls `db_session("boardly-prod")` — returns an `_AsyncGeneratorContextManager` instance.
2. Calls `await .__aenter__()` on it — advances the async generator to the `yield`, returns the `session`.
3. Binds `session` to that value.
4. Runs the body, including `await session.query("auth")`.
5. Calls `await .__aexit__(None, None, None)` (no exception) — runs the `finally` block, which awaits `session.__aexit__(None, None, None)`.

The `async` is required on `with` because `__aenter__` is async — the `with` block must `await` it. Using `with` instead of `async with` would call the sync `__enter__` (which doesn't exist on `_AsyncGeneratorContextManager`) and raise `AttributeError`.

### Lines 54–63: Exception in the body

```python
async def exception_in_body() -> None:
    print("\n=== exception in body — session still closes ===")
    try:
        async with db_session("boardly-prod") as session:
            print(f"  before raise: session.open = {session.open}")
            raise ValueError("something broke mid-query")
    except ValueError as e:
        print(f"  caught: {e}")
```

The `raise ValueError(...)` in the body:
1. The exception propagates from the body to `__aexit__`.
2. `__aexit__` is called with `(ValueError, <the exception instance>, <traceback>)`.
3. `@asynccontextmanager`'s `__aexit__` calls `await gen.athrow(ValueError, ...)` — this injects the exception *into the async generator at the `yield` point*.
4. The generator's `try`/`finally` catches it (the `try` doesn't have an `except`, so it propagates, but the `finally` runs first).
5. The `finally` runs `await session.__aexit__(None, None, None)` — closes the session.
6. The exception continues propagating out of `db_session`, caught by the outer `try`.

Same semantics as the sync form. The `try`/`yield`/`finally` pattern guarantees teardown.

### Lines 66–78: The FastAPI `Depends` manual-drive demo

```python
async def fastapi_depends_parallel() -> None:
    """Demonstrate the FastAPI Depends shape — manual lifecycle drive."""
    print("\n=== FastAPI Depends parallel (manual lifecycle) ===")
    gen = get_db()
    # __aenter__ equivalent: advance the generator to the yield
    session = await gen.__anext__()
    try:
        result = await session.query("billing")
        print(f"  query: {result}")
    finally:
        # __aexit__ equivalent: advance again, expect StopAsyncIteration
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass  # this is the expected end-of-generator signal
```

This is what FastAPI does internally to a `Depends`-wrapped async generator:

1. `gen = get_db()` — creates the async generator object (no code runs yet).
2. `session = await gen.__anext__()` — advances the generator to the `yield`. This runs everything up to the `yield`: `FakeAsyncSession("boardly-fastapi")`, `await session.__aenter__()`, and the entry into `try`. The `yield` returns the `session`.
3. Body runs: `await session.query("billing")`.
4. `try`/`finally`: cleanup runs.
5. `await gen.__anext__()` — advances the generator past the `yield`, into the `finally` block. `await session.__aexit__(None, None, None)` runs (closing the session). The generator returns (no more `yield`s), so `__anext__` raises `StopAsyncIteration`.
6. `except StopAsyncIteration: pass` — the expected end-of-generator signal.

This manual-drive pattern is what Starlette's `solve_generator` does. If the route raised, Starlette would call `await gen.athrow(*exc_info)` instead of `await gen.__anext__()` — that throws the exception into the generator at the `yield` point, where the `try`/`finally` catches it.

### Lines 81–83: Run the demo

```python
async def main() -> None:
    await normal_use()
    await exception_in_body()
    await fastapi_depends_parallel()


if __name__ == "__main__":
    asyncio.run(main())
```

`asyncio.run(main())` is the 3.7+ entry point for running an async top-level function. It creates an event loop, runs `main()` to completion, then closes the loop. The three demos run sequentially inside the same loop.

## Execution Trace

```bash
$ uv run python boardly/asynccontextmanager_demo.py
=== normal use ===
  [session] opening boardly-prod
  query: {'id': 'p_auth', 'name': 'Auth'}
  [session] closing boardly-prod

=== exception in body — session still closes ===
  [session] opening boardly-prod
  before raise: session.open = True
  [session] closing boardly-prod
  caught: something broke mid-query

=== FastAPI Depends parallel (manual lifecycle) ===
  [session] opening boardly-fastapi
  query: {'id': 'p_billing', 'name': 'Billing'}
  [session] closing boardly-fastapi
```

The first block shows the normal flow: open, query, close. The second block shows the exception flow: open, body prints the open state, body raises, session still closes (proving the `finally` runs), exception is caught. The third block shows the manual-drive of `get_db()` — the same observable behaviour as the `@asynccontextmanager` form, because under the hood the lifecycle management is identical.

## Common Mistakes

### Mistake 1: Using `@contextmanager` on an async function

```python
@contextlib.contextmanager  # ← wrong decorator for async
async def db_session():
    yield session
```

**Symptom:** The decorator returns a sync context manager, and `async with db_session() as s:` raises `AttributeError: __aenter__` (because the sync form has `__enter__`, not `__aenter__`).

**Why:** `@contextmanager` wraps a sync generator. An async function with `yield` is an async generator; `@contextmanager` doesn't know how to handle it.

**Fix:** Use `@contextlib.asynccontextmanager` for async generators.

### Mistake 2: Forgetting `await` on the `__aenter__`/`__aexit__` calls

```python
@contextlib.asynccontextmanager
async def db_session(name):
    session = FakeAsyncSession(name)
    session.__aenter__()  # ← missing await
    try:
        yield session
    finally:
        session.__aexit__(None, None, None)  # ← missing await
```

**Symptom:** `RuntimeWarning: coroutine 'FakeAsyncSession.__aenter__ was never awaited`. The session appears to never open (because the coroutine that opens it is never run).

**Why:** `__aenter__` and `__aexit__` on an async context manager are coroutines. Calling them without `await` creates a coroutine object that's never awaited, so the actual setup/teardown never runs.

**Fix:** Add `await` to every `__aenter__` and `__aexit__` call.

### Mistake 3: Suppressing exceptions inside the async generator's `finally`

```python
@contextlib.asynccontextmanager
async def db_session(name):
    session = FakeAsyncSession(name)
    await session.__aenter__()
    try:
        yield session
    except Exception:
        await session.__aexit__(None, None, None)
        return  # ← swallows the exception!
    await session.__aexit__(None, None, None)
```

**Symptom:** Bugs in the `async with` body silently fail — `KeyError`, `TypeError`, etc. are all swallowed.

**Why:** The `except` catches the exception, the `return` swallows it (no `raise`), and `__aexit__` sees no exception to propagate.

**Fix:** Re-raise after the cleanup:

```python
except Exception:
    await session.__aexit__(*sys.exc_info())
    raise
```

Or use `try`/`finally` (no `except`) — the `finally` always runs, and the exception propagates naturally.

## Engineering Trade-Offs

**Decision:** Use `@asynccontextmanager` for async resource-lifecycle context managers — DB sessions, HTTP clients, locks, file handles. Use plain async generators (without the decorator) when you want FastAPI's `Depends` to drive the lifecycle.

**Both sides:** The alternative is a class with `__aenter__`/`__aexit__`. The class form is more flexible (can hold state, support reuse) and more verbose. The `@asynccontextmanager` form is more readable (top-to-bottom flow) and matches the FastAPI `Depends` shape. For 90% of async context managers, `@asynccontextmanager` wins. For complex async resource managers that need public attributes (e.g. `boardly.db.AsyncSession` with `session.is_active`), the class form wins.

**Commitment:** `boardly` uses `@asynccontextmanager` for the internal `db_session` helper and the in-app `audit_context` and `tenant_context` helpers. The public `AsyncSession` class is a full class with `__aenter__`/`__aexit__` because it needs to expose attributes like `is_active` and `in_transaction`. The FastAPI dependencies (`get_db`, `get_redis`) are plain async generators (no decorator) so FastAPI's `Depends` system drives the lifecycle.

**Why not always use `@asynccontextmanager` for FastAPI dependencies?** Because FastAPI doesn't use the decorator — it drives the async generator manually via `__anext__`/`athrow`. Adding `@asynccontextmanager` would change the returned object from a generator to a `_AsyncGeneratorContextManager`, and FastAPI's `solve_generator` only knows how to drive generators. (You can use `@asynccontextmanager` inside a FastAPI dependency if you wrap it in an `async with`, but the dependency function itself must be a plain async generator.)

## Exercises

1. **Exercise 1 — Replace the manual drive with `aclosing`.** Use `from contextlib import aclosing; async with aclosing(get_db()) as gen: session = await gen.__anext__()`. Confirm the same output. `aclosing` ensures the generator is closed even if an exception escapes. `Verify: uv run python boardly/asynccontextmanager_demo.py`

2. **Exercise 2 — Drive with `athrow`.** After the body, call `await gen.athrow(ValueError, ValueError("test"))` instead of `await gen.__anext__()`. Confirm the `finally` runs and the exception propagates. `Verify: uv run python boardly/asynccontextmanager_demo.py`

3. **Exercise 3 — Time the manual drive vs `async with`.** Use `asyncio.run` and `time.perf_counter` to compare `async with db_session():` vs the manual drive. The manual drive should be marginally faster (no decorator overhead) but the difference is tiny. `Verify: uv run python -c "..."`

4. **Exercise 4 — Write a `timed_async()` context manager.** Use `@asynccontextmanager` to write a `timed_async(label)` that prints elapsed time on exit. Use `time.perf_counter()` before `yield` and in the `finally`. `Verify: uv run python -c "import asyncio; from boardly.asynccontextmanager_demo import timed_async; ..."`

5. **Exercise 5 — Wire `get_db` into a fake FastAPI dependency.** Define a `Depends(get_db)`-shaped call: write a `fake_solve_dependency(gen)` that returns the yielded value and registers a cleanup callback. Use it to manage `get_db`'s lifecycle. Verify cleanup runs after the body. `Verify: uv run python boardly/asynccontextmanager_demo.py`

## Verification

```bash
$ uv run python boardly/asynccontextmanager_demo.py
=== normal use ===
  [session] opening boardly-prod
  query: {'id': 'p_auth', 'name': 'Auth'}
  [session] closing boardly-prod

=== exception in body — session still closes ===
  [session] opening boardly-prod
  before raise: session.open = True
  [session] closing boardly-prod
  caught: something broke mid-query

=== FastAPI Depends parallel (manual lifecycle) ===
  [session] opening boardly-fastapi
  query: {'id': 'p_billing', 'name': 'Billing'}
  [session] closing boardly-fastapi
```

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — the sync sibling. `@asynccontextmanager` mirrors `@contextmanager` exactly, except for the async/await keywords.

## What's Next

[[03-contextlib/03-ExitStack-and-AsyncExitStack]] — `ExitStack` lets you manage a *dynamic* list of context managers, where the number isn't known at authoring time. `AsyncExitStack` is the async sibling. Both let you push cleanup callbacks dynamically, which is what FastAPI's `Depends` system does internally for nested dependencies.

- `ExitStack()`, `enter_context()`, `push()`, `callback()` — the dynamic stack.
- `AsyncExitStack` — the async sibling.
- The resource-cleanup order (LIFO).

## Sources

- **`contextlib.asynccontextmanager`** — https://docs.python.org/3.12/library/contextlib.html#contextlib.asynccontextmanager — accessed 2026-10-23 — the canonical reference, added in 3.7.
- **Starlette dependency resolution** — https://www.starlette.io/dependencies/ — accessed 2026-10-23 — the FastAPI dependency system that drives async generators as if they were `@asynccontextmanager`-wrapped.
- **PEP 492 — Coroutines with async and await syntax** — https://peps.python.org/pep-0492/ — accessed 2026-10-23 — the PEP that added `async with` and `__aenter__`/`__aexit__`.

## What We Learned

- You can apply `@contextlib.asynccontextmanager` to an async generator and get an async context manager.
- You can use the `async with` interaction — `__aenter__` returns the yielded value, `__aexit__` runs the `finally`.
- You can explain the exception-rethrow behaviour — `athrow` injects exceptions into the async generator at the `yield` point.
- You can articulate the FastAPI `Depends` async-generator parallel — plain async generators driven manually via `__anext__`/`athrow`.
- You can choose between `@asynccontextmanager` and a class with `__aenter__`/`__aexit__` for async resources.
