---
title: "Lesson 07: @contextmanager internals"
aliases:
 - contextmanager decorator internals
 - _GeneratorContextManager
 - @contextmanager internals
tags:
 - contextlib
 - contextmanager
 - internals
 - context-managers
 - senior-deep-dive
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "35–50 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/02-asynccontextmanager]]"
 - "[[03-contextlib/04-suppress]]"
 - "[[03-contextlib/06-redirect_stdout-stderr]]"
related_lessons:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/02-asynccontextmanager]]"
 - "[[03-contextlib/05-contextvars]]"
---

# Lesson 07: `@contextmanager` internals

*The senior deep-dive — how `@contextmanager` actually works: the generator wrapper, `_GeneratorContextManager`, the `__enter__`/`__exit__` it synthesises, the one-yield rule (it raises `RuntimeError` if the generator doesn't yield exactly once), and the exception-rethrow via `gen.throw()`. With a minimal re-implementation of the whole decorator in ~30 lines.*

**You're at the very beginning of Section 03's senior deep-dive.**

You have used `@contextmanager` a hundred times — `try`/`yield`/`finally`, the body runs at the `yield`, the teardown runs in the `finally`. This lesson is *what Python does to make that work*. The decorator returns a `_GeneratorContextManager` instance — a class that synthesises `__enter__` (call `next(gen)`, get the yielded value), `__exit__` (if the body raised, throw the exception *into* the generator at the `yield` point via `gen.throw(exc)`; if not, advance the generator and expect `StopIteration`). The one-yield rule is a *runtime check*, not a syntactic one: the generator must `yield` exactly once, and the wrapper raises `RuntimeError` if it doesn't. By the end of this lesson you will be able to re-implement `@contextmanager` from scratch, and read CPython's `Lib/contextlib.py` without getting lost. Take your time. Type every example. **This is how you learn.**

#contextlib #contextmanager #internals #senior-deep-dive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Explain** the three-piece architecture: `@contextmanager` (the decorator factory) → `_GeneratorContextManager` (the class) → an instance (the context manager itself).
2. **Re-implement** `@contextmanager` in ~30 lines of Python — including the one-yield check and the exception-rethrow via `gen.throw()`.
3. **State** the one-yield rule: a generator that yields zero times raises `RuntimeError("generator didn't yield")` at `__enter__`; a generator that yields twice raises `RuntimeError("generator didn't stop")` at `__exit__`; a non-generator function (no `yield` syntactically) raises `TypeError` at `__enter__`.
4. **Trace** the exception-rethrow path: an exception in the `with` body is thrown into the generator at the `yield` point via `gen.throw(exc_value)`; if the generator catches it and returns normally, `__exit__` returns `True` (suppress); if the generator doesn't catch it, the exception propagates; if the generator raises a *different* exception, the new one propagates.
5. **Read** the `_GeneratorContextManager` MRO and explain why `@contextmanager`-decorated functions can also be used as decorators (the `ContextDecorator` mixin in the real CPython class).

## Prerequisites

Before starting, you need:

- **[[03-contextlib/01-contextmanager]]** — the canonical lesson. You should be comfortable with `try`/`yield`/`finally` and the exception-rethrow behaviour at the user level. This lesson is the *implementation* of that behaviour.
- **[[03-contextlib/02-asynccontextmanager]]** — the async sibling; same shape with `agen` instead of `gen`.
- **Generators and `yield`** — including `next(gen)`, `StopIteration`, and `gen.throw(exc)`.
- **About 35–50 minutes of focused time.**

**The most common gap: assuming `@contextmanager` is "magic".**

It is not magic. It is a decorator factory that returns a class that wraps your generator function. When you call the wrapped function, the class instance is created with `gen = func(*args, **kwargs)` — *not* yet iterated. The `__enter__` calls `next(gen)` once (advancing to the `yield`); `__exit__` either calls `gen.throw(exc)` (if the body raised) or `next(gen)` again (if it didn't, expecting `StopIteration`). That is the entire mechanism. Once you see it, the "one yield" rule, the exception-rethrow, the `try`/`finally`-runs-on-exit — all become obvious consequences of the underlying generator protocol.

## The Problem

You ship `boardly/db/session.py` with `@contextmanager`. A junior engineer asks: "When the body raises, how does the `finally` block in the generator run? The function returned a generator object — the body's exception is in the *caller's* stack, not the generator's. How does the `finally` see it?"

The answer is: `@contextmanager`'s `__exit__` *throws* the exception into the generator at the `yield` point, using `gen.throw(exc_value)`. The generator resumes from the `yield` with the exception active; if the generator wraps the `yield` in `try`/`finally`, the `finally` runs; if the generator catches the exception, the context manager *suppresses* it (returns `True` from `__exit__`); if not, the exception re-propagates out of the `with` block.

This is the senior view. The lesson ends with you being able to write `@contextmanager` from scratch — which is the only real test of "do you understand it".

## The Code

```python
# boardly/contextmanager_internals.py
"""A minimal re-implementation of contextlib.contextmanager to expose the protocol."""
from __future__ import annotations

from contextlib import AbstractContextManager
from functools import wraps
from typing import Any, Callable, Iterator


class MyContextManager(AbstractContextManager):
    """Minimal @contextmanager reimplementation.

    The real CPython class is _GeneratorContextManager (~60 lines) and also
    inherits from ContextDecorator (so @contextmanager-decorated functions can
    themselves be used as decorators). This minimal version focuses on the
    core __enter__/__exit__ protocol and the one-yield check.
    """

    def __init__(self, func: Callable[..., Iterator[Any]], args, kwargs) -> None:
        self.gen = func(*args, **kwargs)   # NOT yet iterated — a generator object.
        self.func, self.args, self.kwargs = func, args, kwargs

    def __enter__(self) -> Any:
        # Advance the generator to its first (and only) yield.
        try:
            return next(self.gen)
        except StopIteration:
            # Generator returned without yielding — the "didn't yield" rule.
            raise RuntimeError("generator didn't yield")

    def __exit__(self, exc_type, exc_value, tb) -> bool:
        if exc_type is None:
            # Body exited cleanly — advance the generator, expect StopIteration.
            try:
                next(self.gen)
            except StopIteration:
                return False   # clean exit, propagate nothing
            # Generator yielded a second time — the "didn't stop" rule.
            raise RuntimeError("generator didn't stop")
        else:
            # Body raised — throw the exception into the generator at the yield.
            try:
                self.gen.throw(exc_value)   # 3.12 single-arg form
            except StopIteration:
                # Generator finished normally — suppress the original exception.
                return True
            except BaseException as new_exc:
                # Generator raised (or re-raised) — propagate the new one.
                if new_exc is exc_value:
                    return False   # same exception, propagate
                raise               # different exception, propagate new
            else:
                # Generator yielded a second time — bug.
                raise RuntimeError("generator didn't stop")


def my_contextmanager(func: Callable[..., Iterator[Any]]) -> Callable[..., MyContextManager]:
    @wraps(func)
    def helper(*args, **kwargs) -> MyContextManager:
        return MyContextManager(func, args, kwargs)
    return helper


# --- Demonstration ---
@my_contextmanager
def db_session(name: str) -> Iterator[str]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    print(f"  [enter] opening {name}")
    try:
        yield f"session-{name}"
    finally:
        print(f"  [exit] closing {name}")


if __name__ == "__main__":
    # 1. Normal path: __enter__ = next(gen); __exit__ = next(gen) → StopIteration.
    print("--- normal path ---")
    with db_session("default") as s:
        print(f"  body got {s}")
    print("after with")

    # 2. Exception path: body raises, generator catches → __exit__ returns True.
    print("\n--- exception caught in generator ---")
    @my_contextmanager
    def cm_catches() -> Iterator[str]:
        print("  [enter]")
        try:
            yield "value"
        except ValueError as e:
            print(f"  generator caught {type(e).__name__}: {e}")
            # swallowed
        finally:
            print("  [exit]")

    with cm_catches() as v:
        print(f"  body got {v}")
        raise ValueError("boom")
    print("after with — exception was suppressed")

    # 3. Exception path: body raises, generator doesn't catch → propagate.
    print("\n--- exception not caught in generator ---")
    @my_contextmanager
    def cm_no_catch() -> Iterator[str]:
        print("  [enter]")
        yield "value"
        print("  [after yield — unreachable if body raised]")

    try:
        with cm_no_catch() as v:
            print(f"  body got {v}")
            raise ValueError("boom")
    except ValueError as e:
        print(f"caught outside: {e}")

    # 4. One-yield rule: zero yields → RuntimeError at __enter__.
    print("\n--- zero-yield rule ---")
    @my_contextmanager
    def bad_zero() -> Iterator[int]:
        if False:
            yield 1   # syntactically a generator, but never yields at runtime

    try:
        with bad_zero() as v:
            print(f"  body got {v}")
    except RuntimeError as e:
        print(f"RuntimeError: {e}")

    # 5. One-yield rule: two yields → RuntimeError at __exit__.
    print("\n--- two-yield rule ---")
    @my_contextmanager
    def bad_two() -> Iterator[int]:
        yield 1
        yield 2

    try:
        with bad_two() as v:
            print(f"  body got {v}")
    except RuntimeError as e:
        print(f"RuntimeError: {e}")

    # 6. The instance IS a context manager (subclass of AbstractContextManager).
    print("\n--- instance is a context manager ---")
    inst = db_session("x")
    print(f"  type: {type(inst).__name__}")
    print(f"  isinstance(AbstractContextManager): {isinstance(inst, AbstractContextManager)}")
```

## Line-by-Line Deep Dive

### Lines 1–6: Module header and imports

```python
# boardly/contextmanager_internals.py
"""A minimal re-implementation of contextlib.contextmanager to expose the protocol."""
from __future__ import annotations

from contextlib import AbstractContextManager
from functools import wraps
from typing import Any, Callable, Iterator
```

We import `AbstractContextManager` (the base class that defines `__enter__`/`__exit__` as abstract-no-op), `functools.wraps` (to preserve the wrapped function's metadata), and the typing names. The `from __future__ import annotations` is here for consistency with the boardly codebase; it does not affect behaviour. Notably, we do *not* import `ContextDecorator` — the real CPython `_GeneratorContextManager` does, but for our minimal re-implementation the focus is the `__enter__`/`__exit__` protocol.

**Why inherit from `AbstractContextManager`?**

Because the context-manager protocol is a *duck-typed* protocol — any class with `__enter__` and `__exit__` is a context manager, regardless of base class. But inheriting from `AbstractContextManager` registers the class with `contextlib`'s introspection machinery (so `isinstance(obj, AbstractContextManager)` returns `True`) and provides a default `__enter__` that returns `self` (overridden by `_GeneratorContextManager` to return the yielded value). For a real context manager, inheriting is the recommended path; for a *re-implementation* that demonstrates the protocol, it makes the `isinstance` check work.

### Lines 14–19: `MyContextManager.__init__` — store the generator object

```python
    def __init__(self, func: Callable[..., Iterator[Any]], args, kwargs) -> None:
        self.gen = func(*args, **kwargs)   # NOT yet iterated — a generator object.
        self.func, self.args, self.kwargs = func, args, kwargs
```

The `__init__` calls `func(*args, **kwargs)` — but does *not* iterate the result. Calling a generator function returns a *generator object* in a suspended state — the function body has not run yet, no `print` has fired, no `yield` has executed. The generator is a *recipe* for execution, not the execution itself. The first `next(gen)` call (in `__enter__`) is what starts the body running, up to the first `yield`.

Storing `self.func, self.args, self.kwargs` is the CPython pattern — it allows `_recreate_cm` (a method on the real class) to construct a fresh instance for re-entry, used when the context manager is used as a decorator on multiple functions. We do not implement `_recreate_cm` here; we keep the storage to make the shape match.

**Why is the generator not iterated in `__init__`?**

Because the body of the generator (everything before the `yield`) is the *setup* code that should run when `__enter__` is called — not when the context manager is *constructed*. Consider `with db_session("x") as s:` — the `__init__` runs first (creating the `MyContextManager` instance, storing the generator), then `__enter__` runs (advancing the generator, executing the setup, returning the yielded value). If `__init__` ran the generator, the setup would run *before* the `with` block entered — which would break the resource lifecycle (the session would be open before the `with` started managing it). The separation is essential.

### Lines 21–27: `__enter__` — `next(gen)` and the didn't-yield check

```python
    def __enter__(self) -> Any:
        # Advance the generator to its first (and only) yield.
        try:
            return next(self.gen)
        except StopIteration:
            # Generator returned without yielding — the "didn't yield" rule.
            raise RuntimeError("generator didn't yield")
```

`__enter__` calls `next(self.gen)` — this advances the generator from its initial suspended state to the first `yield`, executing all the setup code before that `yield`. The yielded value is returned to the `with ... as v:` `v`. If the generator finished without yielding (e.g., `if False: yield 1` — syntactically a generator, but the `yield` is never reached), `next` raises `StopIteration`, which we catch and re-raise as `RuntimeError("generator didn't yield")`. This is the *zero-yield* case of the one-yield rule.

**Why raise `RuntimeError` instead of letting `StopIteration` propagate?**

Because `StopIteration` is a *normal* generator-completion signal — it would be silently swallowed by some `for` loops and would be confusing to debug ("my context manager exited with no value, why?"). `RuntimeError` is loud, points at the actual problem (the generator didn't yield), and matches the CPython error message exactly. The error message is the contract — search for `"generator didn't yield"` in CPython's `contextlib.py` and you will find the exact same string.

**Danger — The non-generator function case raises `TypeError`, not `RuntimeError`.**

If you decorate a function with *no* `yield` (so it is a regular function, not a generator), `func(*args, **kwargs)` returns `None` (or whatever the function returns), not a generator object. `next(None)` raises `TypeError: 'NoneType' object is not an iterator` — at `__enter__`, before the one-yield check fires. CPython's real `_GeneratorContextManager.__enter__` adds a `_is_generator(func)` check at class-construction time and refuses to wrap non-generator functions — raising `TypeError` early, with a clearer message. Our minimal version skips that check; the error is still loud, just less informative. The rule is: `@contextmanager` requires a function with `yield` somewhere in its body.

### Lines 29–48: `__exit__` — the two branches (clean vs exception)

```python
    def __exit__(self, exc_type, exc_value, tb) -> bool:
        if exc_type is None:
            # Body exited cleanly — advance the generator, expect StopIteration.
            try:
                next(self.gen)
            except StopIteration:
                return False   # clean exit, propagate nothing
            # Generator yielded a second time — the "didn't stop" rule.
            raise RuntimeError("generator didn't stop")
        else:
            # Body raised — throw the exception into the generator at the yield.
            try:
                self.gen.throw(exc_value)   # 3.12 single-arg form
            except StopIteration:
                # Generator finished normally — suppress the original exception.
                return True
            except BaseException as new_exc:
                # Generator raised (or re-raised) — propagate the new one.
                if new_exc is exc_value:
                    return False   # same exception, propagate
                raise               # different exception, propagate new
            else:
                # Generator yielded a second time — bug.
                raise RuntimeError("generator didn't stop")
```

This is the heart of the protocol — 20 lines that contain the entire `@contextmanager` semantics. Two branches:

**Branch 1: `exc_type is None` (body exited cleanly).** The body finished without raising. We call `next(self.gen)` again — the generator resumes from the `yield` and runs the rest of its body (the `finally` block, the teardown). If the generator finishes (raises `StopIteration`), we return `False` — meaning "no exception to suppress, exit the `with` normally". If the generator *yields a second time*, that is a bug — we raise `RuntimeError("generator didn't stop")`. This is the *two-yield* case of the one-yield rule.

**Branch 2: `exc_type is not None` (body raised).** The body raised an exception. We call `self.gen.throw(exc_value)` — this resumes the generator from the `yield` *with the exception active at the yield point*. If the generator wraps the `yield` in `try`/`except`, it can catch the exception; if it does and the generator finishes normally (`StopIteration`), we return `True` — meaning "suppress the original exception". If the generator does not catch (or re-raises the same exception), the exception propagates out of `gen.throw`, and we propagate it (return `False` for the same exception, `raise` for a different one). If the generator *yields a second time* (shouldn't happen but the protocol handles it), `RuntimeError("generator didn't stop")`.

**Why `gen.throw(exc_value)` and not `gen.throw(exc_type, exc_value, tb)`?**

The 3-arg form was the only signature until Python 3.12, which deprecated it in favour of the 1-arg form `gen.throw(exc_value)` (PEP 654-ish cleanup; the 3-arg form goes away in 3.14). The 1-arg form is the modern, non-deprecated API. Our re-implementation uses the 1-arg form; the real CPython `contextlib.py` (3.12) still uses the 3-arg form internally for compatibility, with a deprecation warning suppressed. When 3.14 lands, the 1-arg form will be the only one.

### Lines 51–55: The decorator factory

```python
def my_contextmanager(func: Callable[..., Iterator[Any]]) -> Callable[..., MyContextManager]:
    @wraps(func)
    def helper(*args, **kwargs) -> MyContextManager:
        return MyContextManager(func, args, kwargs)
    return helper
```

`my_contextmanager(func)` is the decorator factory — it takes a generator function `func` and returns a wrapper `helper`. When you call `helper(*args, **kwargs)` (i.e., when you call the decorated function), it constructs and returns a `MyContextManager(func, args, kwargs)` instance — *without* iterating the generator. The `@wraps(func)` preserves `func`'s `__name__`, `__doc__`, `__wrapped__`, so the decorated function still introspects as the original (important for `inspect.signature`, which FastAPI uses on every route).

The asymmetry is critical: `@contextmanager`-decorated `db_session` is *not* the generator function — it is a factory that returns a context manager. Calling `db_session("x")` returns a `MyContextManager` instance, *not* a generator. The `with` block then drives the instance's `__enter__`/`__exit__`, which drive the underlying generator. The decorator pattern hides the underlying generator from the caller; the caller sees a function that "returns a context manager".

### Lines 60–66: The demonstration generator

```python
@my_contextmanager
def db_session(name: str) -> Iterator[str]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    print(f"  [enter] opening {name}")
    try:
        yield f"session-{name}"
    finally:
        print(f"  [exit] closing {name}")
```

The shape you have used a hundred times. Setup before `yield` (`print("[enter] opening ...")`); `yield` the value the `with ... as v:` `v` receives (`f"session-{name}"`); teardown in the `finally` (`print("[exit] closing ...")`). The `try`/`yield`/`finally` pattern guarantees the teardown runs whether the body raised or not — because `gen.throw` re-enters the generator *inside the try block*, so the `finally` fires.

**Why does `try`/`yield`/`finally` guarantee teardown?**

Because `gen.throw(exc_value)` resumes the generator *at the yield point*, which is *inside* the `try`. The exception is active at that point; Python's exception-handling walks up the generator's stack, finds the `try`/`finally`, runs the `finally` block (the teardown), and then propagates the exception (or, if the `try` had an `except` that caught it, swallows it). The `try`/`yield`/`finally` shape is what makes `@contextmanager` safe for resource cleanup — without the `try`, the `yield` is at the top level of the generator, and an exception thrown into the generator bypasses any cleanup code below it. This is the *first* rule in [[03-contextlib/01-contextmanager]] and the reason every example wraps `yield` in `try`/`finally`.

### Lines 69–76: Normal path — `__enter__` runs setup, `__exit__` runs teardown

```python
if __name__ == "__main__":
    # 1. Normal path: __enter__ = next(gen); __exit__ = next(gen) → StopIteration.
    print("--- normal path ---")
    with db_session("default") as s:
        print(f"  body got {s}")
    print("after with")
```

The execution flow:

1. `db_session("default")` → calls `helper("default")` → constructs `MyContextManager(func=db_session, args=("default",), kwargs={})` → `__init__` calls `func(*args, **kwargs)` → returns a generator object (suspended, body not run yet).
2. `with ... as s:` → `__enter__` → `next(self.gen)` → generator resumes, runs `print("[enter] opening default")`, then `yield f"session-default"` → the `yield` returns `"session-default"` to `__enter__` → `__enter__` returns it → bound to `s`.
3. `print(f"  body got {s}")` → the with-body executes.
4. `__exit__(None, None, None)` → `next(self.gen)` → generator resumes after the `yield`, enters the `finally`, runs `print("[exit] closing default")`, returns (raises `StopIteration`) → `__exit__` catches `StopIteration`, returns `False` → with-block exits normally.

**Why is the teardown code at the `yield`?**

Because the generator's `yield` *is* the `with`-body suspension point. Everything before `yield` is `__enter__`; everything after is `__exit__`. The `try`/`finally` shape lets the after-`yield` code run even when an exception is thrown in — which is the entire reason `@contextmanager` exists.

### Lines 78–94: Exception caught in the generator → `__exit__` returns `True`

```python
    # 2. Exception path: body raises, generator catches → __exit__ returns True.
    print("\n--- exception caught in generator ---")
    @my_contextmanager
    def cm_catches() -> Iterator[str]:
        print("  [enter]")
        try:
            yield "value"
        except ValueError as e:
            print(f"  generator caught {type(e).__name__}: {e}")
            # swallowed
        finally:
            print("  [exit]")

    with cm_catches() as v:
        print(f"  body got {v}")
        raise ValueError("boom")
    print("after with — exception was suppressed")
```

Execution flow:

1. `__enter__` → `next(gen)` → runs `print("[enter]")` → `yield "value"` → `__enter__` returns `"value"` → `v = "value"`.
2. `print("  body got value")` → `raise ValueError("boom")`.
3. `__exit__(ValueError, ValueError("boom"), tb)` → `gen.throw(ValueError("boom"))` → generator resumes at the `yield` *with the exception active*. The `try` catches it; `print("  generator caught ValueError: boom")` runs; the `except` body completes (no `raise`); the `finally` runs (`print("  [exit]")`); the generator returns normally → `gen.throw` raises `StopIteration` → `__exit__` catches `StopIteration`, returns `True` → original exception suppressed.
4. `print("after with — exception was suppressed")` runs.

This is the *swallow* path — the `with` body raised, the generator caught the exception, the `__exit__` returned `True` (the context-manager-protocol signal for "suppress"). Compare to `contextlib.suppress` (Lesson 04): `suppress` is a class whose `__exit__` does the `isinstance` check and returns `True` for listed types. Here, the generator's `try`/`except` does the same job, with arbitrary user logic. The two mechanisms are dual: `suppress` is the class-form for "swallow a closed set of types", `@contextmanager` with `try`/`except` is the generator-form for "swallow with custom logic".

### Lines 96–111: Exception not caught → re-propagates

```python
    # 3. Exception path: body raises, generator doesn't catch → propagate.
    print("\n--- exception not caught in generator ---")
    @my_contextmanager
    def cm_no_catch() -> Iterator[str]:
        print("  [enter]")
        yield "value"
        print("  [after yield — unreachable if body raised]")

    try:
        with cm_no_catch() as v:
            print(f"  body got {v}")
            raise ValueError("boom")
    except ValueError as e:
        print(f"caught outside: {e}")
```

Execution flow:

1. `__enter__` → `next(gen)` → `print("  [enter]")` → `yield "value"` → returns `"value"`.
2. `print("  body got value")` → `raise ValueError("boom")`.
3. `__exit__(ValueError, ...)` → `gen.throw(ValueError("boom"))` → generator resumes at the `yield` with the exception active. There is no `try` around the `yield`, so the exception propagates *out of the generator* → `gen.throw` raises `ValueError("boom")` (the *same* exception object — `is exc_value` is `True`). The `except BaseException as new_exc:` catches it, sees `new_exc is exc_value`, returns `False` → with-block re-raises the original `ValueError`.
4. `except ValueError as e:` outside catches it → `print("caught outside: boom")`.

**Why does `gen.throw` re-raise the *same* exception object when the generator doesn't catch?**

Because that is the generator protocol: `gen.throw(exc)` resumes the generator with `exc` active; if the generator does not catch it, the exception propagates *out of* `gen.throw` — the same exception object, same traceback chain. The `new_exc is exc_value` identity check is what distinguishes "the generator re-raised the original" (propagate, return `False`) from "the generator raised a *different* exception" (propagate the new one, `raise`). The distinction matters for traceback clarity: if the generator raises its own exception (e.g., re-raises after logging), that is a *different* exception and should propagate as the new one.

### Lines 113–124: The one-yield rule — zero yields

```python
    # 4. One-yield rule: zero yields → RuntimeError at __enter__.
    print("\n--- zero-yield rule ---")
    @my_contextmanager
    def bad_zero() -> Iterator[int]:
        if False:
            yield 1   # syntactically a generator, but never yields at runtime

    try:
        with bad_zero() as v:
            print(f"  body got {v}")
    except RuntimeError as e:
        print(f"RuntimeError: {e}")
```

`bad_zero` is syntactically a generator (the `yield` keyword makes it so), but the `yield` is never reached at runtime — the body returns immediately. Calling `bad_zero()` returns a generator object; `__enter__` calls `next(gen)`; the generator runs `if False:` (no-op), returns — raising `StopIteration`. `__enter__` catches `StopIteration`, re-raises as `RuntimeError("generator didn't yield")`.

This is the *zero-yield* check: the generator must yield *at least* once at runtime. The check is at `__enter__`, not at decoration time — because the generator's control flow is data-dependent (`if some_condition: yield`), and the check can only fire when the generator is actually iterated.

### Lines 126–137: The one-yield rule — two yields

```python
    # 5. One-yield rule: two yields → RuntimeError at __exit__.
    print("\n--- two-yield rule ---")
    @my_contextmanager
    def bad_two() -> Iterator[int]:
        yield 1
        yield 2

    try:
        with bad_two() as v:
            print(f"  body got {v}")
    except RuntimeError as e:
        print(f"RuntimeError: {e}")
```

`bad_two` yields twice. `__enter__` calls `next(gen)` — the generator runs, yields `1`, suspends. The with-body executes (`print(f"  body got 1")`). `__exit__(None, None, None)` calls `next(gen)` again — the generator resumes, runs the second `yield 2`. Because `next` returned a value (not `StopIteration`), the generator yielded a *second time* — the one-yield rule is violated. `__exit__` raises `RuntimeError("generator didn't stop")`.

**Why check at `__exit__` and not at `__enter__`?**

Because `__enter__` only calls `next` once — it cannot predict whether the generator will yield a second time later. The two-yield check has to happen when the with-body exits and the generator is asked to advance. The check is: "if I `next` the generator after the with-body, and it *yields* (instead of `StopIteration`), that's a bug." This is the *didn't-stop* half of the one-yield rule, complementing the *didn't-yield* half at `__enter__`.

### Lines 139–144: Instance is a context manager

```python
    # 6. The instance IS a context manager (subclass of AbstractContextManager).
    print("\n--- instance is a context manager ---")
    inst = db_session("x")
    print(f"  type: {type(inst).__name__}")
    print(f"  isinstance(AbstractContextManager): {isinstance(inst, AbstractContextManager)}")
```

The output confirms `inst` is a `MyContextManager` instance and `isinstance(inst, AbstractContextManager)` is `True` — the class is registered with the context-manager ABC. The real CPython class is `_GeneratorContextManager` (the leading underscore marks it as "private to contextlib"), inheriting from `_GeneratorContextManagerBase`, `AbstractContextManager`, `ABC`, `ContextDecorator`, and `object` — in that MRO order. The `ContextDecorator` mixin is what lets `@contextmanager`-decorated functions be used as decorators *themselves* (e.g., `@db_session("x")` on another function) — a feature we do not implement in the minimal version.

**Tip — `@contextmanager` instances work as decorators too.**

CPython's `_GeneratorContextManager` inherits from `ContextDecorator`, which provides a `__call__` method that wraps another function: `with self: return func(*args, **kwargs)`. This is why `@contextmanager def my_cm(): ...` then `@my_cm()` on another function works — the instance is a decorator. Our minimal `MyContextManager` does not have this mixin, so its instances cannot be used as decorators — but the core `__enter__`/`__exit__` protocol is identical to CPython's. Adding `ContextDecorator` to the MRO is a one-line change.

## Execution Trace

```bash
$ python boardly/contextmanager_internals.py
--- normal path ---
  [enter] opening default
  body got session-default
  [exit] closing default
after with

--- exception caught in generator ---
  [enter]
  body got value
  generator caught ValueError: boom
  [exit]
after with — exception was suppressed

--- exception not caught in generator ---
  [enter]
  body got value
caught outside: boom

--- zero-yield rule ---
RuntimeError: generator didn't yield

--- two-yield rule ---
  body got 1
RuntimeError: generator didn't stop

--- instance is a context manager ---
  type: MyContextManager
  isinstance(AbstractContextManager): True
```

The six blocks prove the six properties: normal flow, swallow path, re-raise path, zero-yield check, two-yield check, and the `AbstractContextManager` registration. The exact error messages (`generator didn't yield`, `generator didn't stop`) match CPython's `contextlib.py` character-for-character — confirming our re-implementation is faithful.

## Common Mistakes

### Mistake 1: Yielding more than once

```python
@contextmanager
def two_phase():
    setup_phase1()
    yield state1
    setup_phase2()
    yield state2   # ← bug: second yield
    teardown()
```

**Symptom:** `RuntimeError: generator didn't stop` at `__exit__`.
**Why:** The one-yield rule. `__exit__` advances the generator after the body; if it yields again instead of `StopIteration`-ing, the rule is violated. `@contextmanager` models a single enter/exit boundary, not a multi-phase state machine.
**Fix:** Use two separate context managers, or use `ExitStack` to compose them. If you genuinely need multi-phase, write a class with `__enter__`/`__exit__` and explicit phase methods.

### Mistake 2: Forgetting the `try`/`finally` around `yield`

```python
@contextmanager
def leaky():
    resource = open_resource()
    yield resource   # ← no try/finally
    close_resource(resource)
```

**Symptom:** If the with-body raises, `close_resource` never runs — the resource leaks.
**Why:** `gen.throw(exc)` resumes the generator at the `yield` *with the exception active*. Without a `try` around the `yield`, the exception propagates out of the generator immediately — the code after `yield` never runs.
**Fix:**

```python
@contextmanager
def safe():
    resource = open_resource()
    try:
        yield resource
    finally:
        close_resource(resource)
```

The `try`/`finally` is the *only* way to guarantee teardown. This is the first rule of [[03-contextlib/01-contextmanager]] and the most common bug in `@contextmanager` code.

### Mistake 3: Re-raising a different exception from the generator

```python
@contextmanager
def cm():
    try:
        yield
    except ValueError:
        raise RuntimeError("transformed")   # ← different exception
```

**Symptom:** The with-body raises `ValueError`, the generator catches and raises `RuntimeError("transformed")` — the *new* exception propagates out of the `with` block, not the original. Callers `except ValueError` do not catch it.
**Why:** `__exit__`'s `except BaseException as new_exc:` checks `new_exc is exc_value`; if they differ, it `raise`s the new one. This is intentional — the generator's exception *replaces* the body's, which is sometimes desired (transform an exception type) and sometimes a bug (lose the original context).
**Fix:** If you want to *transform* the exception, raise the new one — and document it. If you want to *augment* (preserve context), use `raise X from original` so the chain is kept. If you want to *suppress*, do nothing (do not raise). Be explicit about which of the three you intend.

## Engineering Trade-Offs

**Decision:** Use `@contextmanager` for the 90% case (open/yield/close); use a class with `__enter__`/`__exit__` for the 10% case (multiple methods on the context manager, state held across calls, complex `__exit__` logic that needs custom exception handling).
**Both sides:** The class form is more flexible — you can add `__aenter__`/`__aexit__`, hold state, support re-entry, define methods on the manager itself. The `@contextmanager` form is more readable — the setup, body, and teardown live next to each other in execution order, and the resource lifecycle is obvious from the function's shape. The generator form is the FastAPI `Depends` async-generator shape — `async def get_db(): session = open(); try: yield session; finally: session.close()` — and the entire Starlette dependency system is built on `@asynccontextmanager`. The class form is what `contextlib.suppress`, `contextlib.redirect_stdout`, and `contextlib.ExitStack` are — they need the class form because their `__exit__` is structural (a closed-set check, a swap-restore, a stack-pop).
**Commitment:** boardly uses `@contextmanager` for every "open/yield/close" resource (DB session, file, lock, transaction). The class form is used only for `SwallowErrors` (the test helper from [[03-contextlib/06-redirect_stdout-stderr]]) and for custom multi-method managers. There is no case in boardly where a class-form context manager could have been a `@contextmanager` and was not.

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/contextmanager_internals.py` and run it. Compare your output to the Execution Trace — the error messages `generator didn't yield` and `generator didn't stop` must match CPython's character-for-character. `Verify: python boardly/contextmanager_internals.py`
2. **Exercise 2 — Confirm the error messages match CPython.** Use the *real* `contextlib.contextmanager` on `bad_zero` (with `if False: yield 1`) and `bad_two` (with two yields). Confirm the same `RuntimeError` messages fire. `Verify: python -c "import contextlib; \n@contextlib.contextmanager \ndef bad_zero(): \n  if False: yield 1 \ntry: \n  with bad_zero(): pass \nexcept RuntimeError as e: print('zero:', e) \n@contextlib.contextmanager \ndef bad_two(): \n  yield 1 \n  yield 2 \ntry: \n  with bad_two(): pass \nexcept RuntimeError as e: print('two:', e)"`
3. **Exercise 3 — Add `ContextDecorator` support.** Make `MyContextManager` inherit from `contextlib.ContextDecorator` as well as `AbstractContextManager`. Verify that `@db_session("x")` on another function works (the wrapper enters and exits the context manager around the call). `Verify: python -c "from boardly.contextmanager_internals import my_contextmanager, MyContextManager, db_session; \n@db_session('x') \ndef f(): print('inside f'); return 'f-result' \nprint('f returned:', f())"`
4. **Exercise 4 — Transform an exception in the generator.** Write a `@contextmanager def cm()` that catches `ValueError` and raises `RuntimeError("transformed")` from it. Use the `with cm(): raise ValueError("orig")` pattern and confirm `RuntimeError` propagates (not `ValueError`). Walk through the `__exit__` path that handles this — the `new_exc is not exc_value` branch. `Verify: python -c "from boardly.contextmanager_internals import my_contextmanager; \n@my_contextmanager \ndef cm(): \n  try: yield \n  except ValueError: raise RuntimeError('transformed') \ntry: \n  with cm(): raise ValueError('orig') \nexcept RuntimeError as e: print('caught:', e)"`
5. **Exercise 5 — Implement `asynccontextmanager` minimally.** Mirror the structure for the async case: `__aenter__` does `await self.agen.__anext__()`, `__aexit__` does `await self.agen.athrow(exc_value)` (or `await self.agen.__anext__()` if no exception). The one-yield rule applies identically. Write a 30-line `my_asynccontextmanager` and test it on an `async def get_db()` that `yield`s a session. This is the shape FastAPI's `Depends` uses internally. `Verify: python -c "import asyncio; from boardly.contextmanager_internals import my_asynccontextmanager; \n@my_asynccontextmanager \nasync def get_db(): \n  print('opening'); try: yield 'sess'; finally: print('closing') \nasync def main(): \n  async with get_db() as s: print('got', s) \nasyncio.run(main())"`

## Verification

```bash
$ python boardly/contextmanager_internals.py
--- normal path ---
  [enter] opening default
  body got session-default
  [exit] closing default
after with

--- exception caught in generator ---
  [enter]
  body got value
  generator caught ValueError: boom
  [exit]
after with — exception was suppressed

--- exception not caught in generator ---
  [enter]
  body got value
caught outside: boom

--- zero-yield rule ---
RuntimeError: generator didn't yield

--- two-yield rule ---
  body got 1
RuntimeError: generator didn't stop

--- instance is a context manager ---
  type: MyContextManager
  isinstance(AbstractContextManager): True
```

If the output matches, you have re-implemented `@contextmanager` from scratch — the same `__enter__`/`__exit__` protocol, the same one-yield checks, the same exception-rethrow via `gen.throw`. The two `RuntimeError` messages match CPython's exactly.

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — the user-facing lesson: `try`/`yield`/`finally`, the exception-rethrow behaviour. This lesson is the *implementation* of that behaviour.
- [[03-contextlib/02-asynccontextmanager]] — the async sibling, same architecture with `agen.__anext__`/`athrow`. Exercise 5 walks the parallel reimplementation.
- [[03-contextlib/04-suppress]] — `suppress` is the *class-form* counterpart: a class with a five-line `__exit__` doing `isinstance` checks. This lesson's `MyContextManager` is the *generator-form* counterpart.

## What's Next

You have finished Section 03 (`contextlib`). The next section, [[04-collections/00-collections-MOC]], is the natural sibling — `Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`. The `ChainMap` ↔ `Context` comparison (read-falls-through, write-goes-to-first) is the bridge: `ChainMap` is the *dict* version of what `contextvars.Context` is for the *value* version. Three things to look for in the next section:

- Why `defaultdict` is the right tool for "accumulate into a dict" (and how it relates to `ContextVar` defaults — the factory question).
- The `deque(maxlen=N)` rolling-window pattern that FastAPI uses for in-memory rate-limiters.
- `ChainMap` as the layering primitive for config-overrides — and the parallel to `contextvars.copy_context()`.

Take your time. Type every example. **This is how you learn.**

## Sources

- **`contextlib.contextmanager` — CPython reference** — https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager — accessed 2026-10-23 — the canonical API documentation, including the one-yield rule and the exception-rethrow semantics.
- **PEP 343 — The "with" statement** — https://peps.python.org/pep-0343/ — accessed 2026-10-23 — the context-manager protocol; `__exit__` returning truthy suppresses.
- **PEP 492 — Coroutines with async and await syntax** — https://peps.python.org/pep-0492/ — accessed 2026-10-23 — the `async with` protocol and `__aenter__`/`__aexit__`; `asynccontextmanager` follows.
- **CPython source — `Lib/contextlib.py`** — https://github.com/python/cpython/blob/3.12/Lib/contextlib.py — accessed 2026-10-23 — the real `_GeneratorContextManager` implementation; the one-yield check, the `gen.throw` call, and the `_recreate_cm` machinery. Read it after this lesson — every line will make sense.
- **CPython source — `Lib/contextlib.py` (`ContextDecorator`)** — https://github.com/python/cpython/blob/3.12/Lib/contextlib.py — accessed 2026-10-23 — the mixin that lets `@contextmanager` instances be used as decorators.

## What We Learned

- `@contextmanager` is a decorator factory that returns a class — `_GeneratorContextManager` in CPython, `MyContextManager` in our re-implementation — that wraps a generator function and synthesises `__enter__` and `__exit__`.
- `__enter__` calls `next(gen)` and returns the yielded value; if the generator finishes without yielding, it raises `RuntimeError("generator didn't yield")`.
- `__exit__` has two branches: clean exit (advance the generator, expect `StopIteration`; if it yields, `RuntimeError("generator didn't stop")`), exception (call `gen.throw(exc_value)`; if the generator finishes, suppress; if it re-raises the same exception, propagate; if it raises a different one, propagate the new).
- The one-yield rule is a *runtime* check, enforced at `__enter__` (zero-yield case) and `__exit__` (two-yield case). The error messages `generator didn't yield` and `generator didn't stop` match CPython exactly.
- The `try`/`yield`/`finally` pattern is what makes `@contextmanager` safe for resource cleanup — `gen.throw` resumes the generator *inside* the `try`, so the `finally` runs even on exception.
- The `gen.throw(exc_value)` call (single-arg, 3.12+ form) is the exception-rethrow mechanism; the 3-arg `(type, exc, tb)` form is deprecated in 3.12 and removed in 3.14.
- CPython's `_GeneratorContextManager` inherits from `ContextDecorator`, so `@contextmanager`-decorated functions can also be used as decorators on other functions. Our minimal version omits this mixin but the protocol is identical.
