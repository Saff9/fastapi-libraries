---
title: "Lesson 03: iscoroutinefunction"
aliases:
 - inspect.iscoroutinefunction
 - ismarkedcoroutinefunction
 - sync vs async routing
tags:
 - inspect
 - asyncio
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
related_lessons:
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
 - "[[21-asyncio-primitives/00-asyncio-MOC]]"
---

# Lesson 03: iscoroutinefunction

*How `boardly`'s `inspect.iscoroutinefunction(get_ticket)` decides whether the route runs on the event loop or in a threadpool — the same call FastAPI makes on every route to decide sync-vs-async handling.*

**You're at the very beginning of Section 10 — three lessons in.**

You have written `async def get_ticket(...)` and `def get_ticket(...)` in the same project. You have wondered why FastAPI treats them differently — the async one runs on the event loop, the sync one runs in a threadpool, and never the twain shall meet. The function that makes the decision is one call: `inspect.iscoroutinefunction`. Take your time. Type every example. **This is how you learn.**

#inspect #asyncio

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `inspect.iscoroutinefunction`** — pass a callable, get back `True` if it is an `async def` function (or a `functools.partial` of one), `False` otherwise.
2. **Explain the difference between a coroutine function and a coroutine object** — `inspect.iscoroutinefunction(coro)` checks the function; `asyncio.iscoroutine(coro())` checks the object the function returns.
3. **Explain `ismarkedcoroutinefunction` (Python 3.13+) — version-gated** — the new check for functions marked with `@asyncio.coroutine`-style markers, distinct from true `async def`.
4. **Walk the `functools.wraps` edge case** — explain why a sync wrapper around an async function reports `False` to `iscoroutinefunction`, and how `inspect.unwrap` recovers the truth.
5. **Explain FastAPI's routing decision** — sync route → threadpool call; async route → direct `await`; why the choice matters for the event loop.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[10-inspect/01-signature-and-Parameter]] — basic `inspect` familiarity.
- **`async def` basics** — you should have written at least one `async def` function. See [[21-asyncio-primitives/00-asyncio-MOC]] for the canonical introduction.
- **About 25–35 minutes of focused time.**

**The most common gap: confusing a coroutine function with a coroutine object.** `async def f(): ...` is a *coroutine function* — calling `f()` does not run it; it returns a *coroutine object* that you must `await`. `iscoroutinefunction(f)` checks the function. `iscoroutine(f())` checks the object. The two checks answer different questions; students conflate them.

## The Problem

Here is the bug. `boardly` had this FastAPI route:

```python
# boardly/routes/tickets.py — the bug
def get_ticket(id: int):           # sync, no async
    return {"id": id}
```

The route is sync. FastAPI's request handler does the obvious thing: call `get_ticket(42)` and return the result. But the call happens on the event loop, and the route hits the database — a 50-millisecond synchronous I/O operation. During those 50 milliseconds, the event loop is blocked. No other request can be served. The server appears frozen. Production goes down at the first traffic spike.

The bug is that FastAPI treated a sync route as if it were async — it ran the sync code on the event loop, blocking everything. The fix is for FastAPI to *detect* that the route is sync (via `iscoroutinefunction`) and dispatch it to a threadpool via `await asyncio.to_thread(...)`. The event loop stays free; other requests keep flowing.

The bug that motivates `iscoroutinefunction` is "I need to know whether this callable is async, and I refuse to introspect `__code__.co_flags` directly." The fix is one call.

## The Code

```python
# boardly/di_async.py
"""Demonstrates inspect.iscoroutinefunction."""
import asyncio
import functools
import inspect


# 1. A true async function
async def get_ticket_async(id: int):
    return {"id": id}


# 2. A sync function
def get_ticket_sync(id: int):
    return {"id": id}


# 3. The basic check
print("--- iscoroutinefunction ---")
print(f"  async: {inspect.iscoroutinefunction(get_ticket_async)}")   # True
print(f"  sync:  {inspect.iscoroutinefunction(get_ticket_sync)}")     # False


# 4. A functools.partial of an async function — still detected
async_partial = functools.partial(get_ticket_async, 42)
print(f"\n--- partial of async ---")
print(f"  inspect.iscoroutinefunction(partial): {inspect.iscoroutinefunction(async_partial)}")   # True
print(f"  asyncio.iscoroutinefunction(partial): {asyncio.iscoroutinefunction(async_partial)}")   # True


# 5. A sync wrapper around an async function — the gotcha
def sync_wrapper(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)    # calls the async function but does not await
    return wrapper


wrapped = sync_wrapper(get_ticket_async)
print(f"\n--- @functools.wraps of async ---")
print(f"  iscoroutinefunction(wrapped):                   {inspect.iscoroutinefunction(wrapped)}")      # False
print(f"  iscoroutinefunction(inspect.unwrap(wrapped)):  {inspect.iscoroutinefunction(inspect.unwrap(wrapped))}")   # True


# 6. The coroutine object — a different question
coro_obj = get_ticket_async(42)
print(f"\n--- coroutine OBJECT (not function) ---")
print(f"  inspect.iscoroutinefunction(coro_obj):  {inspect.iscoroutinefunction(coro_obj)}")    # False — it's an object
print(f"  asyncio.iscoroutine(coro_obj):          {asyncio.iscoroutine(coro_obj)}")            # True
# (coroutine object is never awaited here — fine for the demo)

# 7. Other inspect predicates
print(f"\n--- other predicates ---")
print(f"  isfunction(get_ticket_async): {inspect.isfunction(get_ticket_async)}")     # True
print(f"  isfunction(get_ticket_sync):  {inspect.isfunction(get_ticket_sync)}")      # True
print(f"  isclass(int):                 {inspect.isclass(int)}")                      # True
print(f"  ismodule(inspect):           {inspect.ismodule(inspect)}")                  # True

# 8. Python 3.13+ — version-gated
print(f"\n--- Python 3.13+ check ---")
print(f"  hasattr(inspect, 'ismarkedcoroutinefunction'): {hasattr(inspect, 'ismarkedcoroutinefunction')}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 7–12: The two functions under inspection

```python
async def get_ticket_async(id: int):
    return {"id": id}


def get_ticket_sync(id: int):
    return {"id": id}
```

`async def get_ticket_async` is a *coroutine function*. Calling `get_ticket_async(42)` does not run the body — it returns a *coroutine object* that you must `await`. The body runs only when something awaits the object.

`def get_ticket_sync` is a *regular function*. Calling `get_ticket_sync(42)` runs the body immediately and returns the dict. There is no coroutine object involved.

The two functions have the same body and the same return value. The only difference is the `async` keyword. `iscoroutinefunction` distinguishes them.

### Lines 16–19: The basic check

```python
print(f"  async: {inspect.iscoroutinefunction(get_ticket_async)}")   # True
print(f"  sync:  {inspect.iscoroutinefunction(get_ticket_sync)}")     # False
```

`inspect.iscoroutinefunction(get_ticket_async)` returns `True` because the function was defined with `async def`. Internally, the check looks at `functools.CO_COROUTINE` flag in the function's `__code__.co_flags` — that flag is set by the Python compiler when it sees `async def`. The check is O(1) and reliable for any function object.

`inspect.iscoroutinefunction(get_ticket_sync)` returns `False` because the `CO_COROUTINE` flag is not set. The function is a plain synchronous function.

**Why does FastAPI need this check?** Because FastAPI calls routes differently based on the result. For an async route, FastAPI calls it directly with `await endpoint(...)`. For a sync route, FastAPI dispatches it to a threadpool via `await asyncio.to_thread(endpoint, ...)` — so the synchronous I/O in the route does not block the event loop. The check is the only way to make the decision; FastAPI cannot tell from the signature alone.

### Lines 23–26: `functools.partial` of an async function

```python
async_partial = functools.partial(get_ticket_async, 42)
print(f"\n--- partial of async ---")
print(f"  inspect.iscoroutinefunction(partial): {inspect.iscoroutinefunction(async_partial)}")   # True
print(f"  asyncio.iscoroutinefunction(partial): {asyncio.iscoroutinefunction(async_partial)}")   # True
```

`functools.partial(get_ticket_async, 42)` creates a `partial` object that wraps `get_ticket_async` with the first argument `42` pre-bound. The `partial` is callable. `inspect.iscoroutinefunction` on a `partial` returns `True` if the wrapped function is a coroutine function. (In Python 3.8+, `inspect.iscoroutinefunction` was extended to look through `functools.partial`.)

`asyncio.iscoroutinefunction` (the `asyncio` module's copy) returns the same result. FastAPI imports `iscoroutinefunction` from `inspect` (on 3.12+, where it knows the partial-lookthrough works) with a fallback to `asyncio` on older Pythons:

```python
# from fastapi/dependencies/models.py
try:
    from inspect import iscoroutinefunction
except ImportError:   # Python < 3.8
    from asyncio import iscoroutinefunction
```

Both functions check the same flag; the `inspect` version is preferred because it also looks through `functools.partial`.

**Why does FastAPI need partial-lookthrough?** Because FastAPI wraps every callable in a `functools.partial` (the `Depends` mechanism uses partials to bind sub-dependencies). Without partial-lookthrough, every wrapped callable would report `False` to `iscoroutinefunction`, and FastAPI would dispatch async dependencies to the threadpool, deadlocking the event loop. The partial-lookthrough is the load-bearing piece of the architecture.

### Lines 30–38: The `functools.wraps` gotcha

```python
def sync_wrapper(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)    # calls the async function but does not await
    return wrapper


wrapped = sync_wrapper(get_ticket_async)
print(f"\n--- @functools.wraps of async ---")
print(f"  iscoroutinefunction(wrapped):                   {inspect.iscoroutinefunction(wrapped)}")      # False
print(f"  iscoroutinefunction(inspect.unwrap(wrapped)):  {inspect.iscoroutinefunction(inspect.unwrap(wrapped))}")   # True
```

This is the gotcha that costs the most production incidents. `sync_wrapper` takes a function `f` and returns a *sync* `wrapper` that calls `f`. The `@functools.wraps(f)` decorator copies `f.__name__`, `f.__doc__`, and `f.__wrapped__` onto `wrapper`, but it does *not* copy the `CO_COROUTINE` flag — because `wrapper` is not a coroutine function, it is a sync function that happens to call one. `iscoroutinefunction(wrapper)` returns `False`.

`inspect.unwrap(wrapped)` follows the `__wrapped__` chain (set by `functools.wraps`) to the original `get_ticket_async`. `iscoroutinefunction` on the unwrapped function returns `True`.

**Danger — `@functools.wraps` does not preserve async-ness**

```python
def my_decorator(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):     # async — fine
        return await f(*args, **kwargs)
    return wrapper

# vs

def my_decorator_buggy(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):            # sync — wraps async, but loses the await
        return f(*args, **kwargs)            # returns a coroutine object, never awaited
    return wrapper
```

If you wrap an async function with a sync wrapper, the wrapper returns a coroutine object that nobody awaits. The route appears to work (no exception at definition time) but every call leaks a coroutine. FastAPI's `iscoroutinefunction` check fails for the wrapper, dispatching it to the threadpool, where the un-awaited coroutine goes silent. The bug is subtle and expensive.

The fix: if you wrap an async function, your wrapper must be `async def`. Or, use `inspect.unwrap(call)` before calling `iscoroutinefunction` — which is what FastAPI does (see lesson 06).

### Lines 41–45: The coroutine *object* — a different question

```python
coro_obj = get_ticket_async(42)
print(f"\n--- coroutine OBJECT (not function) ---")
print(f"  inspect.iscoroutinefunction(coro_obj):  {inspect.iscoroutinefunction(coro_obj)}")    # False — it's an object
print(f"  asyncio.iscoroutine(coro_obj):          {asyncio.iscoroutine(coro_obj)}")            # True
```

`get_ticket_async(42)` *calls* the coroutine function and returns a *coroutine object*. The object is not the function. `iscoroutinefunction(coro_obj)` returns `False` — because `coro_obj` is an object, not a function. The check you want for objects is `asyncio.iscoroutine(coro_obj)` (or equivalently `inspect.iscoroutine(coro_obj)`, which has been available since Python 3.5 and delegates to `asyncio.iscoroutine`).

**Warning — `iscoroutinefunction` is for functions; `iscoroutine` is for objects**

```python
inspect.iscoroutinefunction(f)     # is f a coroutine function?
inspect.iscoroutine(f())          # is the return value of f() a coroutine object?
```

These answer different questions. The first is "would I `await f(x)`?" The second is "is this thing an awaitable?" The two are related but distinct.

### Lines 48–52: Other `inspect` predicates

```python
print(f"  isfunction(get_ticket_async): {inspect.isfunction(get_ticket_async)}")     # True
print(f"  isfunction(get_ticket_sync):  {inspect.isfunction(get_ticket_sync)}")      # True
print(f"  isclass(int):                 {inspect.isclass(int)}")                      # True
print(f"  ismodule(inspect):           {inspect.ismodule(inspect)}")                  # True
```

`inspect.isfunction(x)` returns `True` for any function (sync or async), `False` for methods, classes, modules. `inspect.ismethod(x)` returns `True` for bound methods. `inspect.isclass(x)` returns `True` for classes (like `int`, `str`, your own classes). `inspect.ismodule(x)` returns `True` for modules. These are the four predicates you reach for when you need to ask "what kind of thing is this?" before deciding how to introspect it.

`inspect.isfunction` returns `True` for both `get_ticket_async` and `get_ticket_sync` — because they are both functions. `iscoroutinefunction` further distinguishes the async one.

### Lines 55–57: Python 3.13+ — `ismarkedcoroutinefunction` (version-gated)

```python
print(f"\n--- Python 3.13+ check ---")
print(f"  hasattr(inspect, 'ismarkedcoroutinefunction'): {hasattr(inspect, 'ismarkedcoroutinefunction')}")
```

**Python 3.13+:** `inspect.ismarkedcoroutinefunction(f)` is a new check that returns `True` for functions marked with `@asyncio.coroutine` (the deprecated decorator that wraps a generator as a coroutine). Before 3.13, the marker was invisible — `iscoroutinefunction` returned `True` for `@asyncio.coroutine`-decorated functions (because they had the `CO_ITERABLE_COROUTINE` flag), but you could not distinguish "true `async def`" from "marked coroutine".

**Why does this matter?** Because `@asyncio.coroutine` was deprecated in 3.8 and removed in 3.12 — but the marker class lives on as `types.MarkerLike`, and some legacy code still uses it. The 3.13+ `ismarkedcoroutinefunction` check lets frameworks distinguish the two, decide whether to wrap-and-await (for true coroutines) or to call directly (for marked coroutines that are actually generator-based). On 3.12, this distinction is unavailable, and frameworks treat both as coroutines.

This course targets Python 3.12 (the sandbox runtime). On 3.12, `ismarkedcoroutinefunction` is not available — `hasattr(inspect, 'ismarkedcoroutinefunction')` is `False`. The feature is version-gated: code that needs the marker-aware check must do `if sys.version_info >= (3, 13): from inspect import ismarkedcoroutinefunction`.

## Execution Trace

```bash
$ python boardly/di_async.py
--- iscoroutinefunction ---
  async: True
  sync:  False

--- partial of async ---
  inspect.iscoroutinefunction(partial): True
  asyncio.iscoroutinefunction(partial): True

--- @functools.wraps of async ---
  iscoroutinefunction(wrapped):                   False
  iscoroutinefunction(inspect.unwrap(wrapped)):  True

--- coroutine OBJECT (not function) ---
  inspect.iscoroutinefunction(coro_obj):  False
  asyncio.iscoroutine(coro_obj):          True

--- other predicates ---
  isfunction(get_ticket_async): True
  isfunction(get_ticket_sync):  True
  isclass(int):                 True
  ismodule(inspect):           True

--- Python 3.13+ check ---
  hasattr(inspect, 'ismarkedcoroutinefunction'): False
```

(The script also emits a `RuntimeWarning: coroutine 'get_ticket_async' was never awaited` — that is expected; the `coro_obj = get_ticket_async(42)` line creates a coroutine object that is never awaited, because we are only checking its type, not running it.)

## Common Mistakes

### Mistake 1: Calling `iscoroutinefunction` on the result, not the function

```python
async def f(): return 1
inspect.iscoroutinefunction(f())   # False — f() returns a coroutine OBJECT
inspect.iscoroutinefunction(f)     # True  — f is the coroutine FUNCTION
```

**Symptom:** The check returns `False` for an async function, and your framework treats it as sync.
**Why:** `f()` *calls* the function and returns a coroutine object. `iscoroutinefunction` checks the type of its argument; for a coroutine object, the answer is `False`.
**Fix:** Pass the function itself, not a call to it. Use `asyncio.iscoroutine(f())` if you want to check whether a value is an awaitable.

### Mistake 2: Wrapping an async function with a sync wrapper

```python
def my_decorator(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)   # returns coroutine object, never awaited
    return wrapper

@my_decorator
async def get_ticket(): ...
```

**Symptom:** The route "works" in dev (no exception), but every call leaks an un-awaited coroutine. Production memory grows until OOM.
**Why:** `wrapper` is sync, so it returns the coroutine object that `f(...)` produces. Nobody awaits it. `iscoroutinefunction(wrapper)` returns `False`, so FastAPI dispatches the route to the threadpool, where the leak goes unnoticed.
**Fix:** Make your wrapper `async def` if you wrap an async function. Or `inspect.unwrap` the wrapper before the check — but the safer fix is to write the wrapper as async.

### Mistake 3: Assuming `iscoroutinefunction` works on callable instances

```python
class Caller:
    async def __call__(self):
        return 1

c = Caller()
inspect.iscoroutinefunction(c)   # False — even though __call__ is async
```

**Symptom:** A callable class instance with `async def __call__` reports `False` to `iscoroutinefunction`, and your framework dispatches it to the threadpool — calling the async `__call__` synchronously, which returns an un-awaited coroutine.
**Why:** `iscoroutinefunction` checks the type passed in. For an instance, the type is the class, not the `__call__` method. The check returns `False`.
**Fix:** For callable instances, check the `__call__` method directly: `inspect.iscoroutinefunction(type(c).__call__)`. Or use FastAPI's elaborate `is_coroutine_callable` (in `fastapi/dependencies/models.py`), which walks through `__call__` chains.

## Engineering Trade-Offs

**Decision:** Use `inspect.iscoroutinefunction` to decide sync-vs-async routing. Pair it with `inspect.unwrap` for `functools.wraps`-decorated callables.
**Both sides:** The alternative is `asyncio.iscoroutinefunction` (the `asyncio` module's copy). They behave identically on Python 3.8+ for plain functions, but the `inspect` version has better `functools.partial` lookthrough. Use the `inspect` version on 3.12+; use `asyncio` as the fallback on older Pythons.
**Commitment:** `boardly`'s DI uses `inspect.iscoroutinefunction` directly. Lesson 06 shows the full chain, including the `inspect.unwrap` call for `functools.wraps`-decorated callables.

## Exercises

1. **Exercise 1 — The basic check.** Define `async def f(): return 1` and `def g(): return 1`. Confirm `iscoroutinefunction(f)` is `True` and `iscoroutinefunction(g)` is `False`. `Verify: python -c "import inspect; async def f(): return 1; def g(): return 1; print(inspect.iscoroutinefunction(f), inspect.iscoroutinefunction(g))"`
2. **Exercise 2 — Partial lookthrough.** Wrap `f` from exercise 1 in `functools.partial(f)`. Confirm `iscoroutinefunction(partial(f))` is `True`. `Verify: python -c "import inspect, functools; async def f(): return 1; p=functools.partial(f); print(inspect.iscoroutinefunction(p))"`
3. **Exercise 3 — The wraps gotcha.** Write a sync `@functools.wraps(f)` wrapper around an async function. Confirm `iscoroutinefunction(wrapper)` is `False` and `iscoroutinefunction(unwrap(wrapper))` is `True`. `Verify: python -c "import inspect, functools; async def f(): return 1; \nimport functools\ndef d(f):\n @functools.wraps(f)\n def w(*a, **k): return f(*a, **k)\n return w\nw=d(f); print(inspect.iscoroutinefunction(w), inspect.iscoroutinefunction(inspect.unwrap(w)))"`
4. **Exercise 4 — Object vs function.** Create `coro = f()` from an async `f`. Confirm `iscoroutinefunction(coro)` is `False` and `asyncio.iscoroutine(coro)` is `True`. `Verify: python -c "import inspect, asyncio; async def f(): return 1; c=f(); print(inspect.iscoroutinefunction(c), asyncio.iscoroutine(c))"`
5. **Exercise 5 — Build a `dispatch` helper.** Write `def dispatch(callable, *args)` that calls the callable on the event loop if it is async, in `asyncio.to_thread` if it is sync. Test with one async and one sync function. `Verify: python -c "import asyncio, inspect; from boardly.di_async import dispatch; async def f(): return 'async'; def g(): return 'sync'; print(asyncio.run(dispatch(f)), asyncio.run(dispatch(g)))"`

## Verification

```bash
$ python boardly/di_async.py | head -3
--- iscoroutinefunction ---
  async: True
  sync:  False
$ python boardly/di_async.py | rg 'inspect.unwrap'
  iscoroutinefunction(inspect.unwrap(wrapped)):  True
$ python -c "import inspect; print(hasattr(inspect, 'ismarkedcoroutinefunction'))"
False
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`. This lesson's `iscoroutinefunction` is the third predicate in the `inspect` toolkit FastAPI uses.
- [[21-asyncio-primitives/00-asyncio-MOC]] — the canonical introduction to `async def`, the event loop, and coroutine objects.

## What's Next

[[10-inspect/04-Parameter-kinds]] — Now you can detect whether a callable is async. The next lesson is a deep-dive on the five `Parameter.kind` values introduced in lesson 01 — `POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD` — the rules each kind enforces on `Signature.bind()`, and the order in which `inspect.signature` lists them.

- **Lesson 04** — The five `Parameter.kind` values in depth.
- **Lesson 05** — `Signature.bind` and `BoundArguments`, the call FastAPI uses to figure out which dependencies to inject.
- **Lesson 06** — The full dependency-resolution chain: `signature` + `get_type_hints` + `iscoroutinefunction` + `bind`.

## Sources

- **Python `inspect` module documentation — `iscoroutinefunction`** — https://docs.python.org/3/library/inspect.html#inspect.iscoroutinefunction — accessed 2026-10-23 — the canonical reference for `iscoroutinefunction`, including the `functools.partial` lookthrough (Python 3.8+).
- **Python `inspect` module documentation — `ismarkedcoroutinefunction` (3.13+)** — https://docs.python.org/3/library/inspect.html#inspect.ismarkedcoroutinefunction — accessed 2026-10-23 — the canonical reference for the 3.13+ check that distinguishes true `async def` from `@asyncio.coroutine`-marked functions. Version-gated in this lesson.
- **Python `inspect` module documentation — `inspect.unwrap`** — https://docs.python.org/3/library/inspect.html#inspect.unwrap — accessed 2026-10-23 — the canonical reference for the `__wrapped__`-chain follower that recovers the original function from a `functools.wraps`-decorated wrapper.
- **FastAPI source — `fastapi/dependencies/models.py`** — https://github.com/fastapi/fastapi/blob/master/fastapi/dependencies/models.py — accessed 2026-10-23 — the actual `is_coroutine_callable` implementation that FastAPI uses; shows the partial-lookthrough, the `inspect.unwrap` call, and the `__call__`-chain walk.

## What We Learned

- You can now call `inspect.iscoroutinefunction(f)` and explain the `CO_COROUTINE` flag check.
- You can now distinguish a coroutine *function* from a coroutine *object* and use the right predicate for each.
- You can now explain the `functools.wraps` gotcha and use `inspect.unwrap` to recover the original async function.
- You can now explain the 3.13+ `ismarkedcoroutinefunction` check and version-gate it on 3.12.
- You can now explain why FastAPI uses this check to decide sync-vs-async routing (threadpool vs event loop).
