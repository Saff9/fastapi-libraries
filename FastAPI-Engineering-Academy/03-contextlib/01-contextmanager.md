---
title: "Lesson 01: contextmanager"
aliases:
 - contextlib.contextmanager
 - @contextmanager
tags:
 - contextlib
 - contextmanager
 - context-managers
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[02-functools/02-wraps-and-Decorators]]"
related_lessons:
 - "[[03-contextlib/02-asynccontextmanager]]"
 - "[[03-contextlib/07-contextmanager-decorator-internals]]"
first_taught_in: "03-contextlib/01-contextmanager"
---

# Lesson 01: `@contextmanager`

*The decorator that turns a generator into a context manager — every `with` block you'll write in production starts here, and so does FastAPI's `Depends` async-generator shape.*

**You're at the very beginning of Section 03.**

`contextlib.contextmanager` is the decorator that lets you write a context manager as a generator function instead of a class with `__enter__` and `__exit__`. It's smaller, it reads top-to-bottom (setup, `yield`, teardown), and it's the shape FastAPI's `Depends` async generators copy. By the end of this lesson you will know the `try`/`yield`/`finally` pattern, the exception-rethrow behaviour (an exception in the `with` body is thrown *into* the generator at the `yield` point), and the precise trade-off between `@contextmanager` and a class with `__enter__`/`__exit__`. Take your time. Type every example. **This is how you learn.**

#contextlib #contextmanager #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@contextlib.contextmanager`** to a generator that yields exactly once, turning it into a context manager.
2. **Use the `try`/`yield`/`finally` pattern** to guarantee teardown runs even if the body raises.
3. **Explain the exception-rethrow behaviour** — an exception in the `with` body is thrown into the generator at the `yield` point; if the generator doesn't catch it, it propagates.
4. **State the "yield exactly once" requirement** — a context-manager generator must yield exactly once; multiple yields raise `RuntimeError`.
5. **Choose between `@contextmanager` and a class with `__enter__`/`__exit__`** — when each form wins.

## Prerequisites

Before starting, you need:

- **Generators and `yield`** — `def gen(): yield 1` should feel normal. If not, write three small generators and `for`-loop them before this lesson.
- **The `with` block protocol** — `with x as y: ...` calls `x.__enter__()` to get `y`, runs the body, then calls `x.__exit__(*exc_info)`.
- **About 30–40 minutes of focused time.**

**The most common gap: thinking the `yield` is the only thing `@contextmanager` does.**

The `yield` is *where the body runs*. Everything before `yield` is `__enter__`. Everything after `yield` (in the `finally`) is `__exit__`. The exception-rethrow behaviour is the subtle part: an exception raised in the `with` body is thrown into the generator at the `yield` point, where the `try`/`finally` catches it. If you `yield` outside a `try`, the exception propagates without teardown — a resource leak.

## The Problem

You ship `boardly/db/session.py` with a `db_session()` context manager. Callers use it as `with db_session() as s: s.query(...)`. You have two options: write it as a class with `__enter__`/`__exit__`, or as a generator with `@contextmanager`.

The class form is verbose:

```python
class DbSession:
    def __init__(self, name):
        self.name = name
        self.session = None
    def __enter__(self):
        self.session = open_session(self.name)
        return self.session
    def __exit__(self, *exc):
        if self.session:
            close_session(self.session)
```

Ten lines for a one-concept idea: open, use, close. The `@contextmanager` form is six lines:

```python
@contextlib.contextmanager
def db_session(name):
    session = open_session(name)
    try:
        yield session
    finally:
        close_session(session)
```

The trade-off: the class form is more flexible (it can hold state, define `__exit__` with conditional logic, support multiple `with` uses); the `@contextmanager` form is more readable (the setup and teardown live next to each other, in execution order). For 90% of context managers, the `@contextmanager` form wins.

## The Code

```python
# boardly/contextmanager_demo.py
"""Demonstrate contextlib.contextmanager — turn a generator into a context manager."""
from __future__ import annotations

import contextlib
from typing import Any, Iterator


# --- Fake DB session ---
class FakeSession:
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.open = False
    def __enter__(self) -> "FakeSession":
        self.open = True
        print(f"  [session] opening {self.name}")
        return self
    def __exit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [session] closing {self.name}")
    def query(self, slug: str) -> dict[str, str]:
        return {"id": f"p_{slug}", "name": slug.title()}


# --- @contextmanager form ---
@contextlib.contextmanager
def db_session(name: str = "default") -> Iterator[FakeSession]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    session = FakeSession(name)
    session.__enter__()  # delegate to FakeSession's __enter__
    try:
        yield session
    finally:
        session.__exit__(None, None, None)  # delegate to FakeSession's __exit__


# --- Class-based form, for comparison ---
class DbSessionManager:
    """The class-based equivalent of db_session above."""
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.session: FakeSession | None = None
    def __enter__(self) -> FakeSession:
        self.session = FakeSession(self.name)
        return self.session.__enter__()
    def __exit__(self, *exc: Any) -> None:
        if self.session is not None:
            self.session.__exit__(*exc)


def normal_use() -> None:
    print("=== normal use ===")
    with db_session("boardly-prod") as session:
        print(f"  query: {session.query('auth')}")


def exception_in_body() -> None:
    print("\n=== exception in body — session still closes ===")
    try:
        with db_session("boardly-prod") as session:
            print(f"  before raise: session.open = {session.open}")
            raise ValueError("something broke mid-query")
    except ValueError as e:
        print(f"  caught: {e}")


def class_based_form() -> None:
    print("\n=== class-based form ===")
    with DbSessionManager("boardly-test") as session:
        print(f"  query: {session.query('billing')}")


def main() -> None:
    normal_use()
    exception_in_body()
    class_based_form()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports

```python
# boardly/contextmanager_demo.py
"""Demonstrate contextlib.contextmanager — turn a generator into a context manager."""
from __future__ import annotations

import contextlib
from typing import Any, Iterator
```

`contextlib.contextmanager` is the star. `Any` is for the `*exc: Any` parameter on `__exit__` (a tuple of `(exc_type, exc_value, traceback)` or `(None, None, None)`). `Iterator` is the return type of a generator function — `@contextmanager` requires the wrapped function to be a generator that returns `Iterator[T]`, where `T` is the yielded value's type.

### Lines 11–21: A fake DB session

```python
# --- Fake DB session ---
class FakeSession:
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.open = False
    def __enter__(self) -> "FakeSession":
        self.open = True
        print(f"  [session] opening {self.name}")
        return self
    def __exit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [session] closing {self.name}")
    def query(self, slug: str) -> dict[str, str]:
        return {"id": f"p_{slug}", "name": slug.title()}
```

`FakeSession` is a stand-in for an actual database session. It's also itself a context manager (`__enter__`/`__exit__` defined) — this lets us delegate from `db_session` to `FakeSession.__enter__`/`__exit__`, which is the canonical pattern when you have a class that already implements the protocol and you want to wrap it in a `@contextmanager` for ergonomics. The `self.open` flag is for the demo — it lets us inspect whether the session is open.

`__exit__(self, *exc: Any)` accepts the three exception-info arguments (or three `None`s for normal exit). Returning `None` (or `False`) from `__exit__` tells Python "don't suppress the exception" — let it propagate. Returning `True` would suppress the exception. Here we return `None` implicitly, which is the same as `False` for suppression semantics.

### Lines 24–31: The `@contextmanager` form

```python
# --- @contextmanager form ---
@contextlib.contextmanager
def db_session(name: str = "default") -> Iterator[FakeSession]:
    """Open a session, yield it, close it on exit — even if the body raises."""
    session = FakeSession(name)
    session.__enter__()  # delegate to FakeSession's __enter__
    try:
        yield session
    finally:
        session.__exit__(None, None, None)  # delegate to FakeSession's __exit__
```

`@contextlib.contextmanager` wraps `db_session` (a generator function — it has a `yield`) so that calling `db_session(...)` returns a `_GeneratorContextManager` object instead of a generator. That object implements `__enter__` and `__exit__`:

- `__enter__` calls `next(self.gen)` — advances the generator to the `yield`, returns the yielded value (`session`).
- `__exit__` calls `self.gen.throw(*exc)` if `exc` is set, or `next(self.gen)` (expecting `StopIteration`) otherwise. If the generator catches the exception via `try`/`except`, the `__exit__` returns whatever the generator returns (or `None`/`False`, propagating the exception).

Lines 26-27 are the `__enter__` body — they run before the `yield`. Line 28's `yield session` is the *handoff point* — the body of the `with` block runs here. Lines 29-30's `finally` runs as part of `__exit__` — whether the body raised or returned normally, the `finally` always runs and `session.__exit__` is called.

The `try`/`yield`/`finally` pattern is *the* idiom for `@contextmanager`. Without the `try`/`finally`, an exception in the `with` body would propagate from the `yield` point and the `session.__exit__(...)` line would never run — a resource leak. The `try`/`finally` guarantees teardown.

**Why delegate to `FakeSession.__enter__` and `__exit__`?** Because `FakeSession` already implements the protocol. We could have written `session.open = True; print(...)` directly in `db_session`, but that duplicates `FakeSession`'s logic. Delegating keeps the logic in one place — `FakeSession` — and `db_session` just orchestrates.

### Lines 34–45: The class-based form, for comparison

```python
# --- Class-based form, for comparison ---
class DbSessionManager:
    """The class-based equivalent of db_session above."""
    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.session: FakeSession | None = None
    def __enter__(self) -> FakeSession:
        self.session = FakeSession(self.name)
        return self.session.__enter__()
    def __exit__(self, *exc: Any) -> None:
        if self.session is not None:
            self.session.__exit__(*exc)
```

`DbSessionManager` is the class-based equivalent. Same behaviour: open on `__enter__`, close on `__exit__`. The differences:

1. **State lives on the instance** — `self.session` holds the session between `__enter__` and `__exit__`. In the `@contextmanager` form, `session` is a local variable in the generator's frame, captured by the generator's closure.
2. **`__exit__` receives the real `exc_info`** — the class form gets the actual `(exc_type, exc_value, traceback)` triple; the `@contextmanager` form has to manually pass `(None, None, None)` because it's not yet inside the exception-handling path. (Internally, `@contextmanager`'s `__exit__` calls `gen.throw(*exc)` to inject the exception into the generator at the `yield` — which is why `try`/`except` inside the generator works.)
3. **The class form is more verbose** — 12 lines vs 8 lines for the `@contextmanager` form. For this simple case, `@contextmanager` wins.

**When does the class form win?** Three cases: (a) when the context manager needs to hold multiple pieces of state between `__enter__` and `__exit__` (the generator's closure handles this, but it's harder to inspect); (b) when the context manager is reused across multiple `with` blocks (the generator form creates a new generator each call, but the class form can be designed for reuse with a counter); (c) when you want a public API that exposes the manager's state (the class form has discoverable attributes, the generator form has only its closure).

### Lines 48–52: Normal use

```python
def normal_use() -> None:
    print("=== normal use ===")
    with db_session("boardly-prod") as session:
        print(f"  query: {session.query('auth')}")
```

The `with db_session("boardly-prod") as session:` line:
1. Calls `db_session("boardly-prod")` — returns a `_GeneratorContextManager` instance.
2. Calls `.__enter__()` on it — runs the generator up to the `yield`, returns the `session`.
3. Binds `session` to that value.
4. Runs the body: `print(f"  query: {session.query('auth')}")`.
5. Calls `.__exit__(None, None, None)` (no exception) — runs the `finally` block, which calls `session.__exit__(None, None, None)`.

The output: `[session] opening boardly-prod`, the query result, `[session] closing boardly-prod`.

### Lines 55–63: Exception in the body

```python
def exception_in_body() -> None:
    print("\n=== exception in body — session still closes ===")
    try:
        with db_session("boardly-prod") as session:
            print(f"  before raise: session.open = {session.open}")
            raise ValueError("something broke mid-query")
    except ValueError as e:
        print(f"  caught: {e}")
```

The `raise ValueError(...)` in the body:
1. The exception propagates from the body to `__exit__`.
2. `__exit__` is called with `(ValueError, <the exception instance>, <traceback>)`.
3. `@contextmanager`'s `__exit__` calls `gen.throw(ValueError, ...)` — this injects the exception *into the generator at the `yield` point*.
4. The generator's `try`/`finally` catches it (the `try` doesn't have an `except`, so it propagates, but the `finally` runs first).
5. The `finally` runs `session.__exit__(None, None, None)` — wait, but the `*exc` here is `(None, None, None)`, not the actual exception. That's because we hardcoded it.

This is the subtle bug in this demo: we delegate to `session.__exit__(None, None, None)`, which means `FakeSession` doesn't see the exception. In a real `DbSession` class, you'd want `__exit__` to receive the exception info so it can decide whether to commit or rollback. To do that with `@contextmanager`, you need to catch the exception in the `try`/`except` and pass it to `session.__exit__(*sys.exc_info())`:

```python
@contextlib.contextmanager
def db_session(name="default"):
    session = FakeSession(name)
    session.__enter__()
    try:
        yield session
    except BaseException as exc:
        session.__exit__(*sys.exc_info())
        raise  # re-raise after handling
    else:
        session.__exit__(None, None, None)
```

The simpler `try`/`yield`/`finally` form is correct for the common case where the cleanup doesn't need to know about the exception (e.g. closing a file, releasing a lock). For database sessions where you want rollback-on-exception, use the `try`/`except` form.

### Lines 66–70: The class-based form

```python
def class_based_form() -> None:
    print("\n=== class-based form ===")
    with DbSessionManager("boardly-test") as session:
        print(f"  query: {session.query('billing')}")
```

The class form produces the same observable behaviour: open, query, close. The internal mechanism differs (instance state vs closure), but the user-visible contract is identical.

## Execution Trace

```bash
$ uv run python boardly/contextmanager_demo.py
=== normal use ===
  [session] opening boardly-prod
  query: {'id': 'p_auth', 'name': 'Auth'}
  [session] closing boardly-prod

=== exception in body — session still closes ===
  [session] opening boardly-prod
  before raise: session.open = True
  [session] closing boardly-prod
  caught: something broke mid-query

=== class-based form ===
  [session] opening boardly-test
  query: {'id': 'p_billing', 'name': 'Billing'}
  [session] closing boardly-test
```

The first block shows the normal flow: open, query, close. The second block shows the exception flow: open, the body prints the open state, the body raises, the session still closes (proving the `finally` runs), then the exception is caught by the outer `try`. The third block shows the class form producing the same observable behaviour.

## Common Mistakes

### Mistake 1: Forgetting the `try`/`finally` around `yield`

```python
@contextlib.contextmanager
def db_session(name):
    session = open_session(name)
    yield session              # ← no try/finally!
    close_session(session)     # ← never runs if body raises
```

**Symptom:** A resource leak — the session is never closed when the `with` body raises. Tests pass (because tests rarely raise in the body), production has a connection-pool exhaustion incident.

**Why:** An exception in the body is thrown into the generator at the `yield` point. Without `try`/`finally`, the exception propagates immediately and the code after `yield` never runs.

**Fix:** Wrap the `yield` in `try`/`finally`:

```python
@contextlib.contextmanager
def db_session(name):
    session = open_session(name)
    try:
        yield session
    finally:
        close_session(session)
```

### Mistake 2: Yielding more than once

```python
@contextlib.contextmanager
def two_yields():
    print("setup")
    yield 1
    print("middle")
    yield 2  # ← RuntimeError
```

**Symptom:** `RuntimeError: generator didn't stop` (or `RuntimeError: generator didn't yield`) on the second `with` body call.

**Why:** `@contextmanager` requires the generator to yield *exactly once*. The `__enter__` advances the generator to the first `yield`; the `__exit__` advances it to `StopIteration`. A second `yield` breaks the protocol.

**Fix:** Refactor to yield a tuple or a small namespace if you need to expose multiple values:

```python
@contextlib.contextmanager
def two_values():
    print("setup")
    yield (1, 2)
    print("teardown")
```

### Mistake 3: Suppressing exceptions unintentionally

```python
@contextlib.contextmanager
def suppress_all():
    try:
        yield
    except Exception:
        pass  # ← swallows every exception, including programming errors
```

**Symptom:** Bugs in the `with` body silently fail — `TypeError`, `AttributeError`, `KeyError` are all swallowed.

**Why:** Catching `Exception` and `pass`-ing it inside a context manager suppresses the exception permanently — `__exit__` returns `None`, but the generator has already absorbed the exception via the `except`.

**Fix:** Use `contextlib.suppress(SpecificException)` (see [[03-contextlib/04-suppress]]) for the narrow case. For broad cleanup, re-raise after the cleanup:

```python
@contextlib.contextmanager
def cleanup_only():
    try:
        yield
    finally:
        cleanup()  # runs always, doesn't suppress
```

## Engineering Trade-Offs

**Decision:** Use `@contextmanager` for resource-lifecycle context managers where the setup and teardown are tightly coupled and simple. Use a class with `__enter__`/`__exit__` when the manager needs to hold multiple state pieces, support reuse, or expose a public API.

**Both sides:** The class form is more flexible — it can be subclassed, it can hold state that's inspectable, it can implement additional methods. The `@contextmanager` form is more readable — the setup and teardown live in execution order in one function. The class form wins for production-grade context managers (e.g. `httpx.Client`, `sqlalchemy.Session`); the `@contextmanager` form wins for one-off helpers (e.g. `with db_session("prod") as s: ...`).

**Commitment:** `boardly` uses `@contextmanager` for all the in-app context managers — `db_session`, `audit_context`, `tenant_context`. The class form is reserved for context managers that are part of a public API and need stable attributes (e.g. `boardly.db.Session` is a class; `boardly.db.session_scope()` is a `@contextmanager` wrapper around it). The rule: `@contextmanager` for internal use, class for public APIs.

**Why not just always use the class form?** Because the `try`/`yield`/`finally` form is *visibly* correct — the setup and teardown are next to each other in the source, in execution order. The class form has `__enter__` at the top and `__exit__` at the bottom, separated by other methods; the reader has to mentally pair them. For 90% of context managers, the readability win is decisive.

## Exercises

1. **Exercise 1 — Verify the cleanup.** Add a `print("after yield")` *inside* the `try` block but *after* `yield session`. Confirm it never runs (because `yield` doesn't return — the generator is suspended at the yield). `Verify: uv run python boardly/contextmanager_demo.py`

2. **Exercise 2 — Inspect the returned object.** After `cm = db_session("test")`, print `type(cm)`. Confirm it's `_GeneratorContextManager` (or similar — the internal name). Print `cm.gen` to confirm it's a generator object. `Verify: uv run python -c "import boardly.contextmanager_demo as m; cm = m.db_session('x'); print(type(cm), cm.gen)"`

3. **Exercise 3 — Two yields.** Add a second `yield` to `db_session` and confirm it raises `RuntimeError` when used in a `with` block. `Verify: uv run python -c "..."`

4. **Exercise 4 — Catch the exception in the generator.** Modify `db_session` to `try`/`except Exception:` around the `yield`, log the exception, and re-raise. Verify the log fires and the exception still propagates. `Verify: uv run python boardly/contextmanager_demo.py`

5. **Exercise 5 — Write a `timed()` context manager.** Use `@contextmanager` to write a `timed(label)` context manager that prints the elapsed time on exit. Use `time.perf_counter()` before `yield` and in the `finally`. `Verify: uv run python -c "from boardly.contextmanager_demo import timed; import time
with timed('sleep'):
    time.sleep(0.1)"`

## Verification

```bash
$ uv run python boardly/contextmanager_demo.py
=== normal use ===
  [session] opening boardly-prod
  query: {'id': 'p_auth', 'name': 'Auth'}
  [session] closing boardly-prod

=== exception in body — session still closes ===
  [session] opening boardly-prod
  before raise: session.open = True
  [session] closing boardly-prod
  caught: something broke mid-query

=== class-based form ===
  [session] opening boardly-test
  query: {'id': 'p_billing', 'name': 'Billing'}
  [session] closing boardly-test
```

## Previously Learned Here

- [[02-functools/02-wraps-and-Decorators]] — `@wraps` preserves identity when you wrap a function; `@contextmanager` synthesises a class when you wrap a generator. Both are decorator-driven identity transformations.

## What's Next

[[03-contextlib/02-asynccontextmanager]] — the async sibling. `@asynccontextmanager` turns an async generator into an async context manager, and it's the shape FastAPI's `Depends` async-generator dependencies use. The `async with` interaction is the bridge between this lesson and every async DB session you'll write in production.

- `@asynccontextmanager` — the async form.
- `async yield` — the suspension point.
- The FastAPI `Depends` async-generator parallel — the exact shape FastAPI dependencies use.

## Sources

- **`contextlib.contextmanager`** — https://docs.python.org/3.12/library/contextlib.html#contextlib.contextmanager — accessed 2026-10-23 — the canonical reference, including the "yield exactly once" requirement and the exception-rethrow behaviour.
- **`contextlib._GeneratorContextManager`** — https://github.com/python/cpython/blob/3.12/Lib/contextlib.py — accessed 2026-23 — the CPython source for the synthesised `__enter__`/`__exit__`. Read this in [[03-contextlib/07-contextmanager-decorator-internals]].
- **PEP 343 — The `with` statement** — https://peps.python.org/pep-0343/ — accessed 2026-10-23 — the original PEP that added the `with` protocol.

## What We Learned

- You can apply `@contextlib.contextmanager` to a single-yield generator and get a context manager.
- You can use `try`/`yield`/`finally` to guarantee teardown runs.
- You can explain the exception-rethrow behaviour — exceptions are thrown into the generator at the `yield` point.
- You know the "yield exactly once" requirement and the `RuntimeError` on violation.
- You can choose between `@contextmanager` and a class with `__enter__`/`__exit__` based on the use case.
