---
title: "Lesson 02: @wraps and Decorators"
aliases:
 - functools.wraps
 - WRAPPER_ASSIGNMENTS
 - __wrapped__
tags:
 - functools
 - wraps
 - decorators
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[02-functools/01-lru_cache-and-Caching]]"
related_lessons:
 - "[[02-functools/03-partial]]"
 - "[[10-inspect/01-signature-and-Parameter]]"
first_taught_in: "02-functools/02-wraps-and-Decorators"
---

# Lesson 02: `@wraps` and Decorators

*The one-line decorator that stops your decorator from lying — to `inspect.signature`, to FastAPI's dependency scanner, to `help()`, and to every type checker that reads your code.*

**You're at the very beginning of Section 02.**

Every Python engineer writes a decorator on day three of the job — `@timed`, `@retry`, `@cached`, `@audit_log` — and almost everyone forgets `@wraps` until a senior reviews the pull request and asks "why does `inspect.signature(my_function)` return `(*args, **kwargs)`?" That question is the lesson. By the end you will know the six attributes `@wraps` copies (`__module__`, `__name__`, `__qualname__`, `__doc__`, `__annotations__`, and `__type_params__` on 3.12+; on 3.8–3.11 the first five), the one attribute it sets (`__wrapped__`), and the FastAPI dependency break that happens when you skip it. Take your time. Type every example. **This is how you learn.**

#functools #wraps #decorators #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@functools.wraps(func)`** to every decorator's inner wrapper and explain what it copies.
2. **List `WRAPPER_ASSIGNMENTS`** from memory — the six attribute names `@wraps` copies from `func` to `wrapper` on Python 3.12+ (`__module__`, `__name__`, `__qualname__`, `__doc__`, `__annotations__`, `__type_params__`); the first five on 3.8–3.11.
3. **Explain `__wrapped__`** — the attribute `@wraps` sets so tooling can unwrap back to the original function.
4. **Demonstrate the `inspect.signature` interaction** — without `@wraps`, the signature reads as `(*args, **kwargs)`; with `@wraps`, it reads as the original function's.
5. **Explain the FastAPI `Depends` break** — `Depends` calls `inspect.signature` on your dependency; an unwrapped decorator returns the wrong signature and FastAPI injects the wrong arguments.

## Prerequisites

Before starting, you need:

- **Decorators as syntax** — `@timed def f(): ...` is `f = timed(f)`. If that's not yet obvious, this lesson will still teach you, but you'll write the decorator before you understand why.
- **About 25–35 minutes of focused time.**

**The most common gap: forgetting that a decorator returns a different function.**

A decorator replaces the original function with a new function. That new function has its own `__name__`, its own `__doc__`, its own signature. Without `@wraps`, the new function looks like `wrapper` to every piece of introspection tooling. With `@wraps`, the new function adopts the original's identity. The gap is small, but it's the difference between a decorator that works and a decorator that breaks FastAPI.

## The Problem

You ship a `@timed` decorator in `boardly/utils/timing.py`. The team loves it. Every endpoint gets `@timed`. Three weeks later you wire up FastAPI's `Depends(get_db)` inside a `@timed`-wrapped function, and FastAPI can't find the `db` argument. The error:

```
TypeError: wrapper() got an unexpected keyword argument 'db'
```

You stare at the function. It clearly takes `db: Session = Depends(get_db)`. You `print(inspect.signature(my_function))` and see `(*args: Any, **kwargs: Any) -> Any`. The signature is gone. FastAPI introspected your function, saw `*args, **kwargs`, decided there were no parameters to inject, and called your wrapper with no arguments at all. The decorator ate the signature.

The fix is one line: `@functools.wraps(func)` on the inner `wrapper`. That line copies the original function's `__name__`, `__qualname__`, `__doc__`, `__annotations__`, and `__module__` onto the wrapper, sets `__wrapped__` to point back at the original, and lets `inspect.signature` follow that pointer to recover the real signature. The bug disappears. The FastAPI dependency resolves. You move on.

## The Code

```python
# boardly/wraps_demo.py
"""Demonstrate why every decorator needs @functools.wraps."""
from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable

print("WRAPPER_ASSIGNMENTS =", functools.WRAPPER_ASSIGNMENTS)
# 3.12+: ('__module__', '__name__', '__qualname__', '__doc__', '__annotations__', '__type_params__')
# 3.8–3.11: the first five only — `__type_params__` was added by PEP 695 in 3.12.


def timed_broken(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator that FORGETS @wraps — the signature lies."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        time.sleep(0.01)
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  [timed] {func.__name__} took {elapsed:.2f} ms")
        return result
    return wrapper


def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Same decorator, this time with @wraps."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        time.sleep(0.01)
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  [timed] {func.__name__} took {elapsed:.2f} ms")
        return result
    return wrapper


@timed_broken
def fetch_project_broken(slug: str) -> dict[str, str]:
    """Return project metadata for a slug."""
    return {"id": f"p_{slug}", "name": slug.title()}


@timed
def fetch_project(slug: str) -> dict[str, str]:
    """Return project metadata for a slug."""
    return {"id": f"p_{slug}", "name": slug.title()}


def main() -> None:
    print("=== broken decorator (no @wraps) ===")
    print(f"name:      {fetch_project_broken.__name__}")
    print(f"doc:       {fetch_project_broken.__doc__}")
    print(f"signature: {inspect.signature(fetch_project_broken)}")

    print()
    print("=== fixed decorator (with @wraps) ===")
    print(f"name:      {fetch_project.__name__}")
    print(f"doc:       {fetch_project.__doc__}")
    print(f"signature: {inspect.signature(fetch_project)}")

    print()
    print("=== __wrapped__ lets tooling unwrap ===")
    print(f"wrapped:                 {fetch_project.__wrapped__}")
    print(f"signature of unwrapped:  {inspect.signature(fetch_project.__wrapped__)}")

    print()
    print("=== run the timed function ===")
    fetch_project("auth")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports

```python
# boardly/wraps_demo.py
"""Demonstrate why every decorator needs @functools.wraps."""
from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable
```

`functools` provides `wraps` and `WRAPPER_ASSIGNMENTS`. `inspect` is here because the whole point of the lesson is showing what `inspect.signature` reports — without `@wraps` it lies, with `@wraps` it tells the truth. `time` is for the artificial `time.sleep(0.01)` so the timed decorator has something measurable to print. `Any` and `Callable` are typing-only imports, made lazy by `from __future__ import annotations`.

### Lines 9–11: The constant `WRAPPER_ASSIGNMENTS`

```python
print("WRAPPER_ASSIGNMENTS =", functools.WRAPPER_ASSIGNMENTS)
# 3.12+: ('__module__', '__name__', '__qualname__', '__doc__', '__annotations__', '__type_params__')
# 3.8–3.11: the first five only — `__type_params__` was added by PEP 695 in 3.12.
```

`functools.WRAPPER_ASSIGNMENTS` is a tuple of attribute names that `@wraps` copies from the wrapped function to the wrapper. On **Python 3.12+** there are six: `__module__` (which module the function was defined in), `__name__` (the bare name, e.g. `fetch_project`), `__qualname__` (the qualified name, e.g. `main.<locals>.fetch_project` if nested), `__doc__` (the docstring), `__annotations__` (the type-hints dict), and `__type_params__` (the type-parameter tuple added by **PEP 695** in 3.12 — empty for a non-generic function like this one). On Python 3.8–3.11 the tuple has five elements (no `__type_params__`). These are the attributes that make a function *identify itself* to tooling.

**Python 3.12+:** the `__type_params__` attribute was added by PEP 695 to support the new generic-class and generic-function syntax (`def f[T](x: T) -> T: ...`). `WRAPPER_ASSIGNMENTS` grew to copy it too, so a `@wraps`-wrapped generic function keeps its type parameters. On 3.8–3.11, `WRAPPER_ASSIGNMENTS` has only the first five entries.

**Why these six and not, say, `__defaults__`?** The CPython maintainers chose these because they're the attributes that affect how the function *appears* in introspection — `help()`, `repr()`, `inspect.signature`. They deliberately left out `__defaults__`, `__kwdefaults__`, and `__code__` because copying those would actually change the wrapper's runtime behaviour, and the wrapper needs to keep its own runtime behaviour (it's the thing that does the timing). `@wraps` is a metadata copy, not a behaviour copy. (`__type_params__` is in the same "metadata, not behaviour" category — it tells `typing.get_type_hints` what `T` means, but it does not change the wrapper's call semantics.)

### Lines 14–22: The broken decorator

```python
def timed_broken(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator that FORGETS @wraps — the signature lies."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        time.sleep(0.01)
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  [timed] {func.__name__} took {elapsed:.2f} ms")
        return result
    return wrapper
```

`timed_broken` is the textbook decorator you wrote before someone told you about `@wraps`. It accepts `func`, defines an inner `wrapper` that does the timing, and returns `wrapper`. The original `func` is captured in the closure — so the wrapper can still call it — but the *identity* of the wrapper is `wrapper`, not `func`. When Python executes `@timed_broken def fetch_project_broken(...): ...`, the name `fetch_project_broken` is rebound to the inner `wrapper` function. The original `fetch_project_broken` is reachable only through the closure cell `func`.

The symptom appears the moment anyone introspects `fetch_project_broken`. `fetch_project_broken.__name__` is `wrapper`. `fetch_project_broken.__doc__` is `None` (the wrapper has no docstring). `inspect.signature(fetch_project_broken)` reads `wrapper`'s signature, which is `(*args: Any, **kwargs: Any) -> Any` — useless. FastAPI's dependency system calls `inspect.signature` and finds nothing to inject; the dependency never resolves.

**Why does the broken decorator still *run* correctly?** Because at runtime, Python dispatches on the function object, not its metadata. `wrapper(*args, **kwargs)` accepts everything and forwards to `func`, which does the real work. The decorator is functionally correct; it's only *introspectively* broken. That's what makes the bug so insidious — your tests pass, your manual curl works, and FastAPI's `Depends` still fails because `Depends` introspects before it dispatches.

### Lines 25–34: The fixed decorator

```python
def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Same decorator, this time with @wraps."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        time.sleep(0.01)
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  [timed] {func.__name__} took {elapsed:.2f} ms")
        return result
    return wrapper
```

The only difference from `timed_broken` is line 27: `@functools.wraps(func)` on the inner `wrapper`. That one line does three things at decoration time:

1. **Copies the six attributes** in `WRAPPER_ASSIGNMENTS` from `func` to `wrapper` — `wrapper.__name__` becomes `fetch_project`, `wrapper.__doc__` becomes `"Return project metadata for a slug."`, and so on.
2. **Sets `wrapper.__wrapped__ = func`** — a back-reference that lets `inspect.signature` (and `inspect.unwrap`) walk back to the original function.
3. **Updates `wrapper.__dict__`** with the contents of `func.__dict__` (line 60 of CPython's `functools.py`), so any custom attributes the original function had are preserved.

The result: `fetch_project.__name__` is now `fetch_project`, `inspect.signature(fetch_project)` returns `(slug: str) -> dict[str, str]`, and `help(fetch_project)` prints the right docstring. The wrapper is now indistinguishable from the original — except it still times.

### Lines 37–44: The decorated functions

```python
@timed_broken
def fetch_project_broken(slug: str) -> dict[str, str]:
    """Return project metadata for a slug."""
    return {"id": f"p_{slug}", "name": slug.title()}


@timed
def fetch_project(slug: str) -> dict[str, str]:
    """Return project metadata for a slug."""
    return {"id": f"p_{slug}", "name": slug.title()}
```

Both functions have an identical body and signature. The only difference is which decorator wraps them. The `slug: str` annotation and `dict[str, str]` return annotation live on `fetch_project.__annotations__` — and `@wraps` copies that dict onto the wrapper, which is why `inspect.signature` can reconstruct the type hints.

### Lines 47–58: The introspection demo

```python
def main() -> None:
    print("=== broken decorator (no @wraps) ===")
    print(f"name:      {fetch_project_broken.__name__}")
    print(f"doc:       {fetch_project_broken.__doc__}")
    print(f"signature: {inspect.signature(fetch_project_broken)}")

    print()
    print("=== fixed decorator (with @wraps) ===")
    print(f"name:      {fetch_project.__name__}")
    print(f"doc:       {fetch_project.__doc__}")
    print(f"signature: {inspect.signature(fetch_project)}")
```

The broken version reports `name='wrapper'`, `doc=None`, and `signature=(*args: Any, **kwargs: Any) -> Any`. The fixed version reports `name='fetch_project'`, `doc='Return project metadata for a slug.'`, and `signature=(slug: str) -> dict[str, str]`. That's the whole lesson in three print statements.

### Lines 60–63: The `__wrapped__` attribute

```python
    print()
    print("=== __wrapped__ lets tooling unwrap ===")
    print(f"wrapped:                 {fetch_project.__wrapped__}")
    print(f"signature of unwrapped:  {inspect.signature(fetch_project.__wrapped__)}")
```

`__wrapped__` is the attribute `@wraps` sets to point back at the original function. `inspect.signature` follows `__wrapped__` automatically (since Python 3.4) — that's why `inspect.signature(fetch_project)` returns the *original* signature, not the wrapper's `(*args, **kwargs)`. `inspect.unwrap(fetch_project)` walks the `__wrapped__` chain to its end; for a singly-decorated function, it returns the original. For a multiply-decorated function (`@cache @timed @retry`), it walks through all the wrappers to the bottom.

### Lines 65–68: Run the timed function

```python
    print()
    print("=== run the timed function ===")
    fetch_project("auth")
```

This proves the decorator actually still works — the timing prints, the return value is `{"id": "p_auth", "name": "Auth"}`. `@wraps` changed only the metadata; the runtime behaviour is unchanged.

## Execution Trace

```bash
$ uv run python boardly/wraps_demo.py
WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__', '__annotations__', '__type_params__')
=== broken decorator (no @wraps) ===
name:      wrapper
doc:       None
signature: (*args: 'Any', **kwargs: 'Any') -> 'Any'

=== fixed decorator (with @wraps) ===
name:      fetch_project
doc:       Return project metadata for a slug.
signature: (slug: 'str') -> 'dict[str, str]'

=== __wrapped__ lets tooling unwrap ===
wrapped:                 <function fetch_project at 0x7f...>
signature of unwrapped:  (slug: 'str') -> 'dict[str, str]'

=== run the timed function ===
  [timed] fetch_project took 10.08 ms
```

The broken section reports `wrapper` and `None` and `(*args, **kwargs)` — that's the bug. The fixed section reports `fetch_project`, the real docstring, and the real signature — that's `@wraps` doing its job. The `__wrapped__` line confirms the back-reference exists; `inspect.signature` of the unwrapped function returns the original signature. The final timing line proves the decorator still works at runtime. (The annotations appear quoted as `'str'`/`'Any'` because `from __future__ import annotations` turns every annotation into a string at runtime; `inspect.signature` shows the raw string form.)

## Common Mistakes

### Mistake 1: Forgetting `@wraps` on a decorator that wraps a FastAPI dependency

```python
def audit_log(func):
    def wrapper(*args, **kwargs):
        log_call(func.__name__, args, kwargs)
        return func(*args, **kwargs)
    return wrapper  # ← no @wraps

@audit_log
def get_db(session: Session = Depends(get_session)):
    return session

# FastAPI sees signature (*args, **kwargs) -> None
# FastAPI injects nothing
# RuntimeError: get_db() got an unexpected keyword argument 'session'
```

**Symptom:** FastAPI raises `TypeError: wrapper() got an unexpected keyword argument 'session'` even though your function clearly takes `session`.

**Why:** FastAPI's dependency system calls `inspect.signature` on your function to discover what to inject. Without `@wraps`, the signature reads `(*args, **kwargs)` — no parameters to inject, so FastAPI injects nothing, and the inner `wrapper` calls `func(*args, **kwargs)` with `args=()` and `kwargs={}`, which means the original `get_db` is called with no arguments and raises.

**Fix:** Add `@functools.wraps(func)` to the inner `wrapper`. The signature recovers, FastAPI sees `(session: Session = Depends(get_session))`, and the dependency resolves.

### Mistake 2: Using `functools.update_wrapper` directly instead of `@wraps`

```python
def timed(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    functools.update_wrapper(wrapper, func)  # ← works, but reads worse
    return wrapper
```

**Symptom:** The code works but reviewers ask "why not just use `@wraps`?"

**Why:** `@wraps(func)` is syntactic sugar for `functools.update_wrapper(wrapper, func)` called after the wrapper is defined. They're the same call. `@wraps` is the idiomatic form; `update_wrapper` is the underlying primitive, useful only when you can't use a decorator (e.g. you're constructing the wrapper dynamically).

**Fix:** Use `@wraps(func)` whenever you can. Reserve `update_wrapper` for metaprogramming.

### Mistake 3: Setting `__wrapped__` manually and expecting `inspect.signature` to follow

```python
def timed(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.__wrapped__ = func  # ← sets only __wrapped__
    return wrapper

inspect.signature(timed(f))  # → (*args, **kwargs) — still broken
```

**Symptom:** You set `__wrapped__` directly, but `inspect.signature` still reports the wrapper's signature.

**Why:** `inspect.signature` *does* follow `__wrapped__`, but only since Python 3.4 and only when `__wrapped__` is set. The mistake here isn't the omission — it's that you've only set one of the six attributes. `__name__`, `__doc__`, `__qualname__`, `__annotations__`, `__module__`, and `__type_params__` (3.12+) are still the wrapper's. `help()` prints the wrong docstring; type checkers may report the wrong annotations.

**Fix:** Use `@wraps(func)`, which sets `__wrapped__` *and* copies all six attributes in one call.

## Engineering Trade-Offs

**Decision:** Every decorator you write uses `@functools.wraps(func)` on the inner wrapper. No exceptions.

**Both sides:** The alternative is to write a class-based decorator with `__call__`, `__name__`, `__doc__`, and `__wrapped__` defined manually. That's more flexible (you can attach state to the decorator instance) but more verbose. For stateless decorators like `@timed` or `@audit_log`, the function-with-`@wraps` form is shorter and idiomatic. For stateful decorators like `@retry(max_attempts=3)`, the class form wins because the decorator instance can hold `attempts` state.

**Commitment:** `boardly` uses `@wraps` on every function decorator (the `timed`, `audit_log`, `cached`, `require_permission` family) and uses class-based decorators only when the decorator must hold state (`retry`, `circuit_breaker`). The rule is codified in the project's `pyproject.toml` ruff config: `D102` (missing docstring) is enforced even on wrapper functions, which forces authors to either write a docstring or use `@wraps` to inherit one.

**Why not enforce `@wraps` with a linter?** There's no built-in ruff rule for "decorator must use `@wraps`," but you can write a custom check or, more pragmatically, code-review for it. The pattern is so ingrained after the first six months that reviewers catch it on sight.

## Exercises

1. **Exercise 1 — Observe the bug.** Run the file as-is. Verify the broken version reports `name='wrapper'` and the fixed version reports `name='fetch_project'`. `Verify: uv run python boardly/wraps_demo.py`

2. **Exercise 2 — Add a second decorator.** Write `@audit_log(func)` that prints `calling <name>` before the call, and stack it with `@timed` on `fetch_project`. Verify `inspect.signature` still returns the original signature (because both decorators use `@wraps`, the `__wrapped__` chain is intact). `Verify: uv run python boardly/wraps_demo.py`

3. **Exercise 3 — Inspect `__dict__`.** Print `fetch_project.__dict__` and `fetch_project_broken.__dict__`. Note that the `@wraps`-version has the same `__dict__` as the original (empty), while the broken one has whatever attributes were assigned to `wrapper`. Attach `custom_attr = True` to `fetch_project` and confirm `fetch_project.__dict__["custom_attr"]` is `True` after decoration. `Verify: uv run python boardly/wraps_demo.py`

4. **Exercise 4 — Use `inspect.unwrap`.** Decorate `fetch_project` with three decorators (all using `@wraps`). Call `inspect.unwrap(fetch_project)` and confirm it returns the original unwrapped function. Print `inspect.signature` of the unwrapped function. `Verify: uv run python boardly/wraps_demo.py`

5. **Exercise 5 — Write a class-based decorator with `__wrapped__`.** Implement `Timed` as a class with `__init__`, `__call__`, and `__wrapped__`. Verify `inspect.signature` still recovers the original signature. Note the extra boilerplate and decide when this form pays off (hint: when the decorator must hold mutable state across calls). `Verify: uv run python boardly/wraps_demo.py`

## Verification

```bash
$ uv run python boardly/wraps_demo.py
WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__', '__annotations__', '__type_params__')
=== broken decorator (no @wraps) ===
name:      wrapper
doc:       None
signature: (*args: 'Any', **kwargs: 'Any') -> 'Any'

=== fixed decorator (with @wraps) ===
name:      fetch_project
doc:       Return project metadata for a slug.
signature: (slug: 'str') -> 'dict[str, str]'

=== __wrapped__ lets tooling unwrap ===
wrapped:                 <function fetch_project at 0x7f...>
signature of unwrapped:  (slug: 'str') -> 'dict[str, str]'

=== run the timed function ===
  [timed] fetch_project took 10.08 ms
```

## Previously Learned Here

- [[02-functools/01-lru_cache-and-Caching]] — `lru_cache` is itself a decorator that uses `@wraps` internally; you now know why `cache_info()` is reachable on the wrapped function but `inspect.signature` still returns the original function's signature.

## What's Next

[[02-functools/03-partial]] — `partial` is the companion to `@wraps`. Where `@wraps` preserves identity when you wrap a function, `partial` freezes arguments when you curry a function. Together they let you build decorators and dependencies that compose cleanly.

- `partial(fun, *args, **kwargs)` — currying without a lambda.
- `partialmethod` — `partial` for class methods.
- `partial` vs `operator.itemgetter` — when each wins.

## Sources

- **`functools.wraps`** — https://docs.python.org/3.12/library/functools.html#functools.wraps — accessed 2026-10-23 — the canonical reference, including `WRAPPER_ASSIGNMENTS` and `__wrapped__`.
- **`functools.update_wrapper`** — https://docs.python.org/3.12/library/functools.html#functools.update_wrapper — accessed 2026-10-23 — the underlying primitive `@wraps` calls.
- **`inspect.signature` and `__wrapped__`** — https://docs.python.org/3.12/library/inspect.html#inspect.signature — accessed 2026-10-23 — documents the `__wrapped__`-following behaviour that makes `inspect.signature` recover the original signature.

## What We Learned

- You can apply `@functools.wraps(func)` to every decorator's inner wrapper.
- You can list `WRAPPER_ASSIGNMENTS` — `__module__`, `__name__`, `__qualname__`, `__doc__`, `__annotations__`, `__type_params__` (the last one added by PEP 695 in 3.12; on 3.8–3.11 the tuple has only the first five).
- You can explain `__wrapped__` — the back-reference that lets `inspect.signature` recover the original signature.
- You can demonstrate the `inspect.signature` interaction and the FastAPI `Depends` break.
- You know when to use `@wraps` (function decorator) vs a class-based decorator (stateful decorator).
