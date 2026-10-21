---
title: "Lesson 04: suppress"
aliases:
 - contextlib.suppress
 - suppress
 - with suppress(KeyError)
tags:
 - contextlib
 - suppress
 - exception-handling
 - context-managers
status: complete
course_level: beginner
difficulty: beginner
estimated_time: "15–25 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
related_lessons:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
 - "[[03-contextlib/07-contextmanager-decorator-internals]]"
---

# Lesson 04: `suppress`

*`with suppress(KeyError): ...` — the one-line context manager for "I expect this exception, ignore it and move on." Smaller than `try`/`except`/`pass`, scoped tighter, and impossible to swallow the wrong exception by accident.*

**You're at the very beginning of Section 03.**

`contextlib.suppress` is the shortest context manager in the standard library — five lines of Python in CPython's `contextlib.py` — and the one you will reach for more than any other. The job is simple: swallow a specific exception (or tuple of exceptions) raised inside the `with` block, and let everything else propagate. There is no `try`, no `except`, no `pass`, and — most importantly — no risk of swallowing an exception you did not mean to. By the end of this lesson you will know the `None`-return behaviour (the suppressed block evaluates to `None` if the exception fires), the multi-exception form, and exactly when `suppress` beats a bare `try`/`except`/`pass`. Take your time. Type every example. **This is how you learn.**

#contextlib #suppress #exception-handling

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply** `contextlib.suppress(*exceptions)` to swallow specific exception types raised inside a `with` block.
2. **Explain** the `None`-return behaviour — if the suppressed block raises, the surrounding expression evaluates to `None`; if it does not raise, the return value passes through untouched.
3. **Use** the multi-exception form `suppress(KeyError, ValueError, TypeError)` to swallow a closed set of exception types.
4. **Predict** what happens when a non-listed exception is raised: it propagates out of the `with` block as if there were no suppress at all.
5. **Decide** between `suppress` and a bare `try`/`except`/`pass` — and know the one rule that makes `suppress` the safer default.

## Prerequisites

Before starting, you need:

- **[[03-contextlib/01-contextmanager]]** — the canonical context-manager lesson. `suppress` is a context manager (it has `__enter__`/`__exit__`); you should be comfortable with the protocol.
- **About 15–25 minutes of focused time.**

**The most common gap: reaching for `try`/`except`/`pass` when `suppress` is shorter and safer.**

Students write `try: do_thing() except KeyError: pass` constantly. The pattern is so common it has a name — "the bare-except-and-pass antipattern". It works, but it has two failure modes `suppress` does not. First, the `except` clause can be widened accidentally (`except Exception:` instead of `except KeyError:`), swallowing bugs. Second, the `pass` body invites future engineers to add `print(...)` statements that grow into real logic, defeating the "ignore" intent. `suppress` is scoped — only the listed exceptions are swallowed, and there is no body to grow.

## The Problem

You ship `boardly/tickets/index.py`. A function looks up a ticket title by ID. The ticket might be missing — that is a normal case, not an error. The function should return `None` if the ID is not in the index. The obvious implementation:

```python
def get_title(ticket_id: int) -> str | None:
    try:
        return TICKETS[ticket_id]
    except KeyError:
        pass
    return None
```

This works, but it is five lines of ceremony for "return the title, or `None`". And the `except KeyError: pass` shape is fragile — a maintainer can later change `KeyError` to `Exception` "to be safe", and the function silently swallows `TypeError` (if `ticket_id` is unhashable), `AttributeError` (if `TICKETS` becomes `None`), and any other bug in `TICKETS[...]` access. `contextlib.suppress` fixes both problems:

```python
from contextlib import suppress

def get_title(ticket_id: int) -> str | None:
    with suppress(KeyError):
        return TICKETS[ticket_id]
    return None
```

Same behaviour, narrower scope, no body to grow. The `with suppress(KeyError):` line says exactly what it means: "I expect a `KeyError` here; ignore it; let everything else through."

## The Code

```python
# boardly/suppress_demo.py
"""contextlib.suppress — swallow a specific exception, let everything else through."""
from __future__ import annotations

from contextlib import suppress
from typing import Any

# A small ticket index — keyed by id.
TICKETS: dict[int, str] = {1: "first", 2: "second"}


def get_title(ticket_id: int) -> str | None:
    """Return the title, or None if the id is missing."""
    with suppress(KeyError):
        return TICKETS[ticket_id]   # raises KeyError if missing → suppressed
    return None                     # reached only when KeyError fired


def parse_int(value: Any) -> int | None:
    """Parse an int from arbitrary input; return None on failure."""
    with suppress(ValueError, TypeError):
        return int(value)
    return None


def failing_close() -> None:
    """Non-listed exception propagates — suppress is not a bare except."""
    with suppress(KeyError):
        raise ValueError("not in the suppress list")


if __name__ == "__main__":
    print("get_title(1):", get_title(1))
    print("get_title(99):", get_title(99))

    print("parse_int('42'):", parse_int("42"))
    print("parse_int('nope'):", parse_int("nope"))
    print("parse_int(None):", parse_int(None))
    print("parse_int(['x']):", parse_int(["x"]))

    try:
        failing_close()
    except ValueError as e:
        print("propagated ValueError:", e)
```

## Line-by-Line Deep Dive

### Lines 1–10: Module header and the ticket index

```python
# boardly/suppress_demo.py
"""contextlib.suppress — swallow a specific exception, let everything else through."""
from __future__ import annotations

from contextlib import suppress
from typing import Any

# A small ticket index — keyed by id.
TICKETS: dict[int, str] = {1: "first", 2: "second"}
```

We import `suppress` directly from `contextlib`. `suppress` is a class — its constructor takes one or more exception types and returns an instance that is also a context manager. The `from __future__ import annotations` is here for consistency with the rest of the boardly codebase; it does not affect `suppress`'s behaviour at all. The `TICKETS` dict is the data our lookups will hit; `99` is the missing key that triggers the suppression path.

**Why is `suppress` a class and not a `@contextmanager`-decorated function?**

Because its behaviour is purely structural: enter, do nothing; exit, return `True` if the exception is in the listed set (which suppresses it), else return `False` (which propagates). A class with `__enter__` returning `self` and `__exit__` doing the `isinstance` check is the smallest possible implementation — no generator, no `yield`, no teardown. CPython's `contextlib.suppress` is exactly that: a class inheriting from `AbstractContextManager`, with a five-line `__exit__`. The class form is faster (no generator overhead) and clearer to read; we walk its source in [[03-contextlib/07-contextmanager-decorator-internals]].

### Lines 12–16: `get_title` — the canonical `suppress` use case

```python
def get_title(ticket_id: int) -> str | None:
    """Return the title, or None if the id is missing."""
    with suppress(KeyError):
        return TICKETS[ticket_id]   # raises KeyError if missing → suppressed
    return None                     # reached only when KeyError fired
```

This is the heart of the lesson. The `with suppress(KeyError):` block attempts `TICKETS[ticket_id]`. If `ticket_id` is `1` or `2`, the lookup succeeds and the `return` statement returns the title — the `with` block exits normally, `suppress` does nothing. If `ticket_id` is `99`, `TICKETS[99]` raises `KeyError`; `suppress`'s `__exit__` is called with the `KeyError` instance; it sees the exception is in its suppressed set; it returns `True` — which tells Python to swallow the exception. Control falls out of the `with` block to `return None`.

The line `return None` is reached *only* when `KeyError` was raised and suppressed. If `TICKETS[ticket_id]` had succeeded, the `return` would have already exited the function. That is the `None`-return behaviour in action: the suppressed block evaluates to `None` for the caller.

**Why does the suppressed block return `None`?**

Because Python's `with` semantics are: if `__exit__` returns `True`, the exception is suppressed and control continues *after* the `with` block, as if the body had completed normally. The body's `return` statement was interrupted by the exception — the function never returned a value from the `with` body. So when control reaches the `return None` line below, that is the function's return value. There is no "restore the original return value" mechanism — once the exception fires, the body's work is abandoned. If you need a non-`None` fallback, you must provide it yourself (the `return None` here, or `return default` if you have one).

### Lines 18–22: `parse_int` — the multi-exception form

```python
def parse_int(value: Any) -> int | None:
    """Parse an int from arbitrary input; return None on failure."""
    with suppress(ValueError, TypeError):
        return int(value)
    return None
```

`int("not-a-number")` raises `ValueError`. `int(None)` raises `TypeError`. `int(["x"])` also raises `TypeError` (a list is not convertible). All three are legitimate "the input is not parseable" cases, and the function's contract is "return `None` on any parse failure". The multi-exception form `suppress(ValueError, TypeError)` lists both. This is the idiomatic shape: list exactly the exceptions you expect, no more.

**Why not `suppress(Exception)` to "catch everything"?**

Because that is the bare-except antipattern dressed up in `suppress` clothing. `suppress(Exception)` would swallow `KeyboardInterrupt` (no — actually `KeyboardInterrupt` inherits from `BaseException`, not `Exception`, so it would *not* be swallowed; but `SystemExit` is the same). What `suppress(Exception)` *does* swallow is every bug-shaped exception — `AttributeError` from a typo in the body, `NameError` from a missing import, `TypeError` from a function called with the wrong arguments. None of those are "the input is not parseable"; they are bugs in `parse_int` itself. Listing `ValueError, TypeError` is the closed set of "input is bad" exceptions; anything else is a bug, and bugs should propagate. Never widen `suppress` past the legitimate expected failures.

### Lines 24–27: Non-listed exceptions propagate

```python
def failing_close() -> None:
    """Non-listed exception propagates — suppress is not a bare except."""
    with suppress(KeyError):
        raise ValueError("not in the suppress list")
```

The `with suppress(KeyError):` block raises `ValueError`. `suppress`'s `__exit__` is called with the `ValueError` instance. It checks `isinstance(exc, KeyError)` — `False`. It returns `False`. Python re-raises the `ValueError` out of the `with` block, exactly as if there were no `suppress` at all. This is the safety property: `suppress` swallows *only* the types you list. A `MemoryError`, a `RecursionError`, an `AttributeError` from a typo in the body — all propagate. The "what if I accidentally swallow a bug" worry that haunts bare `except` clauses does not apply here, because the listed types are an explicit, closed set.

**Why does `__exit__` returning `False` re-raise?**

Because that is the context-manager protocol: `__exit__(exc_type, exc_value, traceback)` returns a truthy value to suppress, a falsy value to propagate. CPython's `contextlib.suppress.__exit__` is the simplest possible implementation — about 10 lines:

```python
def __exit__(self, exctype, excinst, exctb):
    if exctype is None:
        return                                   # clean exit — nothing to do
    if issubclass(exctype, self._exceptions):
        return True                              # exception in the listed set — suppress
    if issubclass(exctype, BaseExceptionGroup):   # 3.11+ — split a group
        match, rest = excinst.split(self._exceptions)
        if rest is None:
            return True
        raise rest
    return False                                 # not listed — propagate
```

(The `BaseExceptionGroup` branch is 3.11+ — added by PEP 654 alongside `ExceptionGroup`.) The protocol is what makes context managers composable: a `with` block inside another `with` block chains cleanly because each `__exit__` decides independently whether to swallow.

## Execution Trace

```bash
$ python boardly/suppress_demo.py
get_title(1): first
get_title(99): None
parse_int('42'): 42
parse_int('nope'): None
parse_int(None): None
parse_int(['x']): None
propagated ValueError: not in the suppress list
```

The two lines that matter are `get_title(99): None` (the suppressed `KeyError` returned `None` for the caller) and `propagated ValueError: not in the suppress list` (the `ValueError` was *not* in the suppressed set, so it propagated out and we caught it with the outer `try`/`except` in `__main__`).

## Common Mistakes

### Mistake 1: Treating `suppress` as a bare `except`

```python
with suppress(Exception):     # ← too broad
    result = parse_complex_payload(data)
return result                  # ← None if anything failed, even bugs
```

**Symptom:** `parse_complex_payload` has a typo — `data.get("title")` instead of `data["title"]`. The `AttributeError` is swallowed; `result` is `None`; the API silently returns empty results for every request.
**Why:** `suppress(Exception)` swallows every "normal" exception, including bugs. The closed set was meant to be `ValueError, TypeError` for "bad input"; widening it to `Exception` defeats the purpose.
**Fix:**

```python
with suppress(ValueError, TypeError):
    result = parse_complex_payload(data)
```

List only the expected failures. Bugs propagate. The rule is: if you cannot enumerate the expected exceptions, you do not yet understand the failure mode well enough to swallow it.

### Mistake 2: Expecting the suppressed block's return value to survive

```python
def get_title(ticket_id: int) -> str:
    with suppress(KeyError):
        return TICKETS[ticket_id]
    # ticket_id was missing — what does the function return?
```

**Symptom:** The function has no `return` after the `with` block. Python implicitly returns `None`, but the type hint says `str`. mypy catches it; at runtime, callers expecting a `str` get `None` and crash later with `AttributeError: 'NoneType' has no attribute 'lower'`.
**Why:** When the `KeyError` fires, the `return` statement is interrupted. The exception propagates to `suppress.__exit__`, which suppresses it. Control falls through to the next line — which is the end of the function. Python returns `None` by default.
**Fix:**

```python
def get_title(ticket_id: int) -> str | None:
    with suppress(KeyError):
        return TICKETS[ticket_id]
    return None   # ← explicit
```

Either widen the return type to `str | None` (preferred — the function *can* miss) or supply a non-`None` default (`return "unknown"`).

### Mistake 3: Using `suppress` for cleanup-style "ignore errors on close"

```python
with suppress(Exception):
    connection.close()   # ← swallows every close error, including bugs
```

**Symptom:** A bug in `connection.close` (e.g., a typo in an attribute access) is silently swallowed; the connection leaks; production slowly runs out of file descriptors.
**Why:** `suppress(Exception)` is the wrong tool for "ignore cleanup errors". The right tool is `suppress(OSError)` (the specific type `close` raises when the socket is already closed) — or, even better, log the error instead of swallowing it.
**Fix:**

```python
with suppress(OSError):   # ← only the expected "already closed" error
    connection.close()
```

List the specific exception type the close path is known to raise. If you do not know, do not suppress.

## Engineering Trade-Offs

**Decision:** Use `contextlib.suppress(*expected_exceptions)` for "this exception is a normal case" paths; use `try`/`except` only when you need to *do something* with the exception (log it, retry, fall back to a different strategy).
**Both sides:** A bare `try`/`except KeyError: pass` is functionally equivalent to `with suppress(KeyError):` — same bytecode shape, same observable behaviour. The `suppress` form wins on three axes: (1) it is shorter (one line vs three), (2) it has no body to grow (no `pass` that becomes `print(...)` that becomes `if condition: retry()`), (3) the listed exceptions are syntactically attached to the swallow site, so widening them requires editing the suppress line — whereas widening a bare `except` is invisible. The `try`/`except` form wins when you need the exception instance: `except KeyError as e: log(e)` — `suppress` discards the instance.
**Commitment:** boardly uses `suppress` for every "expected miss" path — `TICKETS[id]` lookups, optional config keys, `int()` parsing. There is no `try`/`except`/`pass` in the boardly codebase; every `except` clause either logs, retries, or re-raises a different exception. `suppress` is the only allowed shape for "do nothing on failure".

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/suppress_demo.py` and run it. Compare your output to the Execution Trace. `Verify: python boardly/suppress_demo.py`
2. **Exercise 2 — `del` with `suppress`.** `del d[key]` raises `KeyError` if `key` is missing. Wrap a `del` in `with suppress(KeyError):` so it is a no-op when the key is absent. Test on `TICKETS` with both `1` (present) and `99` (missing). `Verify: python -c "from contextlib import suppress; from boardly.suppress_demo import TICKETS; with suppress(KeyError): del TICKETS[99]; print('survived', TICKETS)"`
3. **Exercise 3 — Add `OverflowError` to `parse_int`.** `int("9" * 10000)` raises `ValueError` (too long) on 3.12. Try `10 ** 10000` (an int literal — no error) versus `int("1e9999")` (raises `ValueError`). List both `ValueError` and `OverflowError` in `suppress` for `parse_int`, and confirm both are swallowed. `Verify: python -c "from boardly.suppress_demo import parse_int; print(parse_int('1e9999'))"`
4. **Exercise 4 — Reproduce `suppress` as a class.** Write a `MySuppress` class with `__init__(self, *exceptions)`, `__enter__(self)`, and `__exit__(self, exc_type, exc, tb)` returning `issubclass(exc_type, self._exceptions)` (with the `None`-exc case handled). Confirm `with MySuppress(KeyError): {}['x']` runs without raising. `Verify: python -c "from boardly.my_suppress import MySuppress; with MySuppress(KeyError): {}['x']; print('ok')"`
5. **Exercise 5 — `suppress` does not work as a decorator.** Try `@contextlib.suppress(ValueError)` on a function. Confirm it raises `TypeError: 'suppress' object is not callable`. Explain why (suppress does not inherit from `ContextDecorator`, unlike `@contextmanager` instances). Write a `suppress_decorator(excs)` helper using `@contextmanager` that *does* work as a decorator. `Verify: python -c "from boardly.my_suppress import suppress_decorator; @suppress_decorator(ValueError) \ndef f(): raise ValueError('x') \nf(); print('survived')"`

## Verification

```bash
$ python boardly/suppress_demo.py
get_title(1): first
get_title(99): None
parse_int('42'): 42
parse_int('nope'): None
parse_int(None): None
parse_int(['x']): None
propagated ValueError: not in the suppress list
```

If the output matches, you have reproduced the four canonical `suppress` behaviours: hit (`first`), miss → `None`, multi-exception swallow (`parse_int` of bad input), and non-listed exception propagation.

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — `@contextmanager` and the `with` protocol. This lesson shows `suppress` as the *class-form* counterpart: a context manager that is too small to be a generator, just an `__enter__`/`__exit__` pair.

## What's Next

[[03-contextlib/05-contextvars]] — the FastAPI request-scoped primitive. `suppress` is a small, structural context manager; `ContextVar` is the *state* primitive — the thing FastAPI sets in middleware and reads in any handler, with copy-on-create semantics for asyncio tasks. Three things to look for in lesson 05:

- Why a per-request DB session is a `ContextVar`, not a global.
- The `Token` returned by `.set()` and what `.reset(token)` is for.
- The `copy_context()` snapshot mechanism and why asyncio tasks get a *copy* of the context, not a reference.

Take your time. Type every example. **This is how you learn.**

## Sources

- **`contextlib.suppress` — CPython reference** — https://docs.python.org/3/library/contextlib.html#contextlib.suppress — accessed 2026-10-23 — the canonical API documentation; the `__exit__` return-`True`-to-suppress semantics.
- **PEP 343 — The "with" statement** — https://peps.python.org/pep-0343/ — accessed 2026-10-23 — the context-manager protocol definition; `__exit__` returning truthy suppresses.
- **CPython source — `Lib/contextlib.py` (suppress)** — https://github.com/python/cpython/blob/3.12/Lib/contextlib.py — accessed 2026-10-23 — the five-line implementation of `suppress`; useful for the "it is a class, not a generator" point.

## What We Learned

- `with suppress(*exceptions):` swallows the listed exception types raised inside the `with` body and lets everything else propagate.
- If the suppressed block raises, the surrounding expression evaluates to `None` (or whatever value the code after the `with` block returns) — the body's `return` is interrupted.
- The multi-exception form `suppress(ValueError, TypeError)` lists a closed set; never widen past the legitimate expected failures.
- A non-listed exception propagates out of the `with` block — `suppress` is not a bare `except Exception`.
- `suppress` is a class (inheriting `AbstractContextManager`), not a `@contextmanager`-decorated generator — and it does *not* inherit from `ContextDecorator`, so it cannot be used as a decorator.
- Use `suppress` for "expected miss" paths; use `try`/`except` when you need the exception instance or want to do something with it (log, retry, fall back).
