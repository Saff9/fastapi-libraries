---
title: "Lesson 03: ExitStack and AsyncExitStack"
aliases:
 - contextlib.ExitStack
 - contextlib.AsyncExitStack
 - ExitStack
tags:
 - contextlib
 - exitstack
 - resource-management
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "25–35 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/02-asynccontextmanager]]"
related_lessons:
 - "[[03-contextlib/05-contextvars]]"
---

# Lesson 03: `ExitStack` and `AsyncExitStack`

*The dynamic context-manager stack — when you don't know how many resources you'll need at authoring time, or when cleanup callbacks aren't a context manager at all.*

**You're at the very beginning of Section 03.**

`contextlib.ExitStack` is the answer to a question that doesn't come up often but, when it does, is hard to solve any other way: "I need to manage N context managers, where N is computed at runtime, and each one needs proper cleanup even if one of them fails." The plain `with A() as a, B() as b, C() as c:` form is fine for static N; `ExitStack` is for dynamic N. The async sibling, `AsyncExitStack`, is what `asyncio.gather` and FastAPI's dependency system use internally to manage multiple async context managers. By the end of this lesson you will know the `enter_context`, `push`, and `callback` APIs, the LIFO cleanup order, and the precise reason FastAPI's `Depends` uses an `AsyncExitStack` internally to manage all your dependencies. Take your time. Type every example. **This is how you learn.**

#contextlib #exitstack #resource-management

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `contextlib.ExitStack()`** as a dynamic context manager that collects other context managers.
2. **Use `enter_context(cm)`** to push a context manager onto the stack — its `__enter__` runs immediately, its `__exit__` runs on stack exit.
3. **Use `push(exit_callable)`** to register a raw `__exit__`-shaped callable as a cleanup.
4. **Use `callback(fn, *args, **kwargs)`** to register a plain function call as a cleanup — no exception arguments, just a deferred invocation.
5. **Explain the LIFO cleanup order** — last-registered runs first, exactly mirroring nested `with` blocks.
6. **Apply `AsyncExitStack` and `enter_async_context`** — the async sibling, with `await` on each call.

## Prerequisites

Before starting, you need:

- **Nested `with` blocks** — `with A() as a:\n  with B() as b: ...` should feel natural.
- **The `with A() as a, B() as b:` form** — multiple context managers in one `with`, comma-separated.
- **[[03-contextlib/01-contextmanager]] and [[03-contextlib/02-asynccontextmanager]]** — the canonical lessons on the underlying context-manager protocol.
- **About 25–35 minutes of focused time.**

**The most common gap: reaching for a static `with A() as a, B() as b, C() as c:` when N is dynamic.**

Students hard-code N context managers in a `with` and then hit the case where N comes from a list — and they reach for a manual `try`/`finally` chain that's 30 lines long. `ExitStack` is the right tool for that case, in three lines.

## The Problem

You ship `boardly/config/loader.py` that loads N config files, where N comes from a CLI argument or a directory listing. Each file is opened with `open(path)`, parsed with `json.load`, and contributes to the merged config. The closing of each file must happen on exit, even if a later file fails to parse. With static `with`:

```python
with open(a) as fa, open(b) as fb, open(c) as fc:
    ...  # only works for exactly 3 files
```

For dynamic N, you'd write a manual `try`/`finally`:

```python
files = []
try:
    for path in paths:
        f = open(path)
        files.append(f)
        # use f
finally:
    for f in reversed(files):
        f.close()
```

Verbose, error-prone (what if `open(path)` fails for path[5]? The cleanup loop only closes the successfully-opened files, which is correct, but easy to get wrong), and not idiomatic. `ExitStack` does it in three lines:

```python
with contextlib.ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
    # use files
```

If `open(p)` for `paths[5]` raises, the `ExitStack.__exit__` runs all the previously-entered contexts' `__exit__` methods (in LIFO order, so `paths[4]` first, then `paths[3]`, etc.) before re-raising. Correct, terse, idiomatic.

## The Code

```python
# boardly/exitstack_demo.py
"""Demonstrate contextlib.ExitStack and AsyncExitStack."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any


# --- Fake resources ---
class Resource:
    def __init__(self, name: str) -> None:
        self.name = name
        self.open = False
    def __enter__(self) -> "Resource":
        self.open = True
        print(f"  [open]  {self.name}")
        return self
    def __exit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [close] {self.name}")


class AsyncResource:
    def __init__(self, name: str) -> None:
        self.name = name
        self.open = False
    async def __aenter__(self) -> "AsyncResource":
        self.open = True
        print(f"  [a-open]  {self.name}")
        return self
    async def __aexit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [a-close] {self.name}")


def use_static_stack() -> None:
    """Static: hard-coded `with A() as a, B() as b:` — the classic form."""
    print("=== static with-stack ===")
    with Resource("config-1") as r1, Resource("config-2") as r2:
        print(f"  using {r1.name} and {r2.name}")


def use_exit_stack_static() -> None:
    """Same as above but with ExitStack — useful when N is known at authoring time."""
    print("\n=== ExitStack (static known count) ===")
    with contextlib.ExitStack() as stack:
        r1 = stack.enter_context(Resource("config-1"))
        r2 = stack.enter_context(Resource("config-2"))
        print(f"  using {r1.name} and {r2.name}")


def use_exit_stack_dynamic() -> None:
    """ExitStack's killer feature: dynamic N from a list."""
    print("\n=== ExitStack (dynamic count from list) ===")
    names = ["config-1", "config-2", "config-3"]
    with contextlib.ExitStack() as stack:
        resources = [stack.enter_context(Resource(n)) for n in names]
        print(f"  using {[r.name for r in resources]}")


def use_exit_stack_callbacks() -> None:
    """callback() — register a plain callable, no __exit__ needed."""
    print("\n=== ExitStack with callback() ===")
    with contextlib.ExitStack() as stack:
        stack.callback(print, "  [callback] cleanup #1 (last to run)")
        stack.callback(print, "  [callback] cleanup #2 (first to run)")
        print("  body: do work")


def use_exit_stack_push() -> None:
    """push() — register an __exit__-shaped callable directly."""
    print("\n=== ExitStack with push() ===")
    def custom_exit(exc_type, exc_value, tb):
        print(f"  [push-exit] exc_type={exc_type}")
        return False  # don't suppress

    with contextlib.ExitStack() as stack:
        stack.push(custom_exit)
        print("  body: do work")


def use_exit_stack_exception() -> None:
    """LIFO cleanup order when body raises — observe the order."""
    print("\n=== ExitStack LIFO cleanup on exception ===")
    try:
        with contextlib.ExitStack() as stack:
            stack.callback(print, "  [callback] cleanup #1 (registered first, runs last)")
            stack.callback(print, "  [callback] cleanup #2 (registered last, runs first)")
            r = stack.enter_context(Resource("config-1"))
            print(f"  body: using {r.name}")
            raise ValueError("mid-body error")
    except ValueError as e:
        print(f"  caught: {e}")


async def use_async_exit_stack() -> None:
    """AsyncExitStack: the async sibling — same API, await on each call."""
    print("\n=== AsyncExitStack ===")
    async with contextlib.AsyncExitStack() as stack:
        r1 = await stack.enter_async_context(AsyncResource("a-config-1"))
        r2 = await stack.enter_async_context(AsyncResource("a-config-2"))
        print(f"  using {r1.name} and {r2.name}")


def main() -> None:
    use_static_stack()
    use_exit_stack_static()
    use_exit_stack_dynamic()
    use_exit_stack_callbacks()
    use_exit_stack_push()
    use_exit_stack_exception()
    asyncio.run(use_async_exit_stack())


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports

```python
# boardly/exitstack_demo.py
"""Demonstrate contextlib.ExitStack and AsyncExitStack."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any
```

`contextlib.ExitStack` is the star; `contextlib.AsyncExitStack` is the async sibling. `asyncio` is for `asyncio.run` to drive the async demo. `Any` is for `*exc: Any` parameters.

### Lines 11–28: Fake sync and async resources

```python
class Resource:
    def __init__(self, name: str) -> None:
        self.name = name
        self.open = False
    def __enter__(self) -> "Resource":
        self.open = True
        print(f"  [open]  {self.name}")
        return self
    def __exit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [close] {self.name}")


class AsyncResource:
    def __init__(self, name: str) -> None:
        self.name = name
        self.open = False
    async def __aenter__(self) -> "AsyncResource":
        self.open = True
        print(f"  [a-open]  {self.name}")
        return self
    async def __aexit__(self, *exc: Any) -> None:
        self.open = False
        print(f"  [a-close] {self.name}")
```

`Resource` is a sync context manager; `AsyncResource` is its async sibling. Both print on enter and exit, so the LIFO cleanup order is visible in the output. The `self.open` flag is for inspection during the demo.

### Lines 31–35: The static `with` form

```python
def use_static_stack() -> None:
    """Static: hard-coded `with A() as a, B() as b:` — the classic form."""
    print("=== static with-stack ===")
    with Resource("config-1") as r1, Resource("config-2") as r2:
        print(f"  using {r1.name} and {r2.name}")
```

The comma-separated form `with A() as a, B() as b:` is equivalent to nested `with` blocks:

```python
with A() as a:
    with B() as b:
        ...
```

Both `A` and `B` are entered in order (A first, then B). On exit, `B`'s `__exit__` runs first, then `A`'s — LIFO order, mirroring nested blocks. This form is fine for static N; it's the right idiom when you know the count at authoring time.

### Lines 38–44: `ExitStack` with a static known count

```python
def use_exit_stack_static() -> None:
    """Same as above but with ExitStack — useful when N is known at authoring time."""
    print("\n=== ExitStack (static known count) ===")
    with contextlib.ExitStack() as stack:
        r1 = stack.enter_context(Resource("config-1"))
        r2 = stack.enter_context(Resource("config-2"))
        print(f"  using {r1.name} and {r2.name}")
```

`with contextlib.ExitStack() as stack:` creates an empty stack. `stack.enter_context(Resource("config-1"))` calls `Resource(...).__enter__()` immediately and registers the resource's `__exit__` to run when the stack exits. The function returns the value yielded by `__enter__` — the resource instance.

For static N, this is more verbose than the comma-separated `with`. The win comes in the next demo — dynamic N.

### Lines 47–53: `ExitStack` with dynamic N

```python
def use_exit_stack_dynamic() -> None:
    """ExitStack's killer feature: dynamic N from a list."""
    print("\n=== ExitStack (dynamic count from list) ===")
    names = ["config-1", "config-2", "config-3"]
    with contextlib.ExitStack() as stack:
        resources = [stack.enter_context(Resource(n)) for n in names]
        print(f"  using {[r.name for r in resources]}")
```

The list comprehension `[stack.enter_context(Resource(n)) for n in names]` enters each resource and collects the instances. The list `resources` holds all three; they're all closed (in LIFO order) on stack exit. If `Resource(n)` for `n="config-2"` raised, the stack would close `Resource("config-1")` first (LIFO), then re-raise.

This is the killer feature: N can be a runtime list, a directory listing, a config-driven list — any iterable. The `ExitStack` manages all the cleanups correctly without you writing a `try`/`finally` chain.

### Lines 56–62: `callback()` — plain function as cleanup

```python
def use_exit_stack_callbacks() -> None:
    """callback() — register a plain callable, no __exit__ needed."""
    print("\n=== ExitStack with callback() ===")
    with contextlib.ExitStack() as stack:
        stack.callback(print, "  [callback] cleanup #1 (last to run)")
        stack.callback(print, "  [callback] cleanup #2 (first to run)")
        print("  body: do work")
```

`stack.callback(fn, *args, **kwargs)` registers a deferred call: when the stack exits, `fn(*args, **kwargs)` is called. Unlike `push()`, the callback doesn't receive exception info — it's just a plain deferred function call. Useful for "do this on exit, regardless of what happened" — e.g. `stack.callback(log_message, "request done")` or `stack.callback(redis.expire, key, 3600)`.

The LIFO order is observable: callback #2 was registered last, so it runs first; callback #1 runs second. The body's `print` runs before either callback.

### Lines 65–74: `push()` — `__exit__`-shaped callable

```python
def use_exit_stack_push() -> None:
    """push() — register an __exit__-shaped callable directly."""
    print("\n=== ExitStack with push() ===")
    def custom_exit(exc_type, exc_value, tb):
        print(f"  [push-exit] exc_type={exc_type}")
        return False  # don't suppress

    with contextlib.ExitStack() as stack:
        stack.push(custom_exit)
        print("  body: do work")
```

`stack.push(callable)` registers a callable that will be called with the same arguments as `__exit__`: `(exc_type, exc_value, traceback)`. For normal exit, all three are `None`. For an exception, they're the actual exception info.

`custom_exit` prints the exception type and returns `False` — which means "don't suppress the exception". Returning `True` would suppress the exception, equivalent to a try/except that swallows. Most cleanup callbacks should return `False` (or `None`, which Python treats as `False` for suppression).

**Why use `push()` vs `callback()`?** Use `push()` when the cleanup needs to know whether an exception occurred (e.g. rollback on exception, commit otherwise). Use `callback()` when the cleanup is unconditional (e.g. close a file, log a message).

### Lines 77–87: LIFO cleanup on exception

```python
def use_exit_stack_exception() -> None:
    """LIFO cleanup order when body raises — observe the order."""
    print("\n=== ExitStack LIFO cleanup on exception ===")
    try:
        with contextlib.ExitStack() as stack:
            stack.callback(print, "  [callback] cleanup #1 (registered first, runs last)")
            stack.callback(print, "  [callback] cleanup #2 (registered last, runs first)")
            r = stack.enter_context(Resource("config-1"))
            print(f"  body: using {r.name}")
            raise ValueError("mid-body error")
    except ValueError as e:
        print(f"  caught: {e}")
```

The body raises `ValueError`. The `ExitStack.__exit__` runs, executing each cleanup in LIFO order:
1. `Resource.__exit__` (registered third via `enter_context`) — closes the resource.
2. `callback #2` (registered second).
3. `callback #1` (registered first).

Then the original `ValueError` propagates and is caught by the outer `try`.

The LIFO order is what makes `ExitStack` composable — it matches the cleanup order of nested `with` blocks, where the innermost block exits first. This means an `ExitStack` behaves identically to a hand-written nest of `with` statements, just with dynamic N.

### Lines 90–96: `AsyncExitStack` — the async sibling

```python
async def use_async_exit_stack() -> None:
    """AsyncExitStack: the async sibling — same API, await on each call."""
    print("\n=== AsyncExitStack ===")
    async with contextlib.AsyncExitStack() as stack:
        r1 = await stack.enter_async_context(AsyncResource("a-config-1"))
        r2 = await stack.enter_async_context(AsyncResource("a-config-2"))
        print(f"  using {r1.name} and {r2.name}")
```

`AsyncExitStack` is the async sibling: `async with` to create, `await stack.enter_async_context(...)` to push async context managers, `await stack.enter_async_context(...)` to enter sync context managers too (via `enter_context`, which is also available). The LIFO cleanup is identical; only the protocol differs (`__aexit__` instead of `__exit__`).

`AsyncExitStack` is what `asyncio.gather` uses internally to manage the lifecycles of multiple async tasks, and what FastAPI's `Depends` system uses to manage all your yield-based dependencies in a single request — every dependency's cleanup runs (in LIFO order) when the response is sent.

## Execution Trace

```bash
$ uv run python boardly/exitstack_demo.py
=== static with-stack ===
  [open]  config-1
  [open]  config-2
  using config-1 and config-2
  [close] config-2
  [close] config-1

=== ExitStack (static known count) ===
  [open]  config-1
  [open]  config-2
  using config-1 and config-2
  [close] config-2
  [close] config-1

=== ExitStack (dynamic count from list) ===
  [open]  config-1
  [open]  config-2
  [open]  config-3
  using ['config-1', 'config-2', 'config-3']
  [close] config-3
  [close] config-2
  [close] config-1

=== ExitStack with callback() ===
  body: do work
  [callback] cleanup #2 (first to run)
  [callback] cleanup #1 (last to run)

=== ExitStack with push() ===
  body: do work
  [push-exit] exc_type=None

=== ExitStack LIFO cleanup on exception ===
  [open]  config-1
  body: using config-1
  [close] config-1
  [callback] cleanup #2 (registered last, runs first)
  [callback] cleanup #1 (registered first, runs last)
  caught: mid-body error

=== AsyncExitStack ===
  [a-open]  a-config-1
  [a-open]  a-config-2
  using a-config-1 and a-config-2
  [a-close] a-config-2
  [a-close] a-config-1
```

The first three blocks show sync `Resource` cleanup in LIFO order — last-opened closes first. The fourth block shows `callback()` cleanups running in LIFO order (callback #2 first, callback #1 second). The fifth block shows `push()` receiving `None` for normal exit. The sixth block shows the LIFO cleanup on exception: `Resource.__exit__` first (registered last via `enter_context`), then callback #2, then callback #1. The seventh block shows the async sibling doing the same with `AsyncResource`.

## Common Mistakes

### Mistake 1: Confusing `callback` and `push` argument conventions

```python
def my_cleanup():
    print("done")

stack.callback(my_cleanup)  # correct: callback calls my_cleanup()
stack.push(my_cleanup)      # wrong: push expects (exc_type, exc_value, tb)
                            # my_cleanup() will raise TypeError on exit
```

**Symptom:** `TypeError: my_cleanup() takes 0 positional arguments but 3 were given` on stack exit when using `push`.

**Why:** `push` passes `(exc_type, exc_value, tb)` to the callable; `callback` passes no exception args (just the `*args, **kwargs` you supplied at registration).

**Fix:** Use `callback` for unconditional cleanups, `push` only when you need the exception info. If you must use `push` with a no-arg function, wrap it: `stack.push(lambda *exc: my_cleanup())`.

### Mistake 2: Forgetting that `enter_context` runs `__enter__` immediately

```python
with contextlib.ExitStack() as stack:
    resources = [stack.enter_context(Resource(n)) for n in huge_list]
    # ... but you wanted to break early if a condition failed
```

**Symptom:** All N resources are opened even if you'd have aborted after the first few — wasted setup.

**Why:** `enter_context` calls `__enter__` immediately and registers `__exit__`. There's no lazy "open on first use" mode. If you want conditional opening, build the list manually:

```python
with contextlib.ExitStack() as stack:
    resources = []
    for n in huge_list:
        if should_skip(n):
            break
        resources.append(stack.enter_context(Resource(n)))
```

**Fix:** Use a `for` loop with `break`/`continue` instead of a list comprehension when you need conditional entry.

### Mistake 3: Returning `True` from a `push` cleanup accidentally

```python
def cleanup(exc_type, exc_value, tb):
    print("cleanup ran")
    return True  # ← suppresses the exception!

with contextlib.ExitStack() as stack:
    stack.push(cleanup)
    raise ValueError("test")  # ← never propagates!
```

**Symptom:** Exceptions in the `with` body silently fail. The cleanup runs, the exception is gone, the outer `try` never sees it.

**Why:** Returning `True` from `__exit__` (or from a `push`-registered callable) tells Python "I handled the exception; don't propagate."

**Fix:** Return `False` (or `None`) from cleanup callbacks unless you genuinely want to suppress.

## Engineering Trade-Offs

**Decision:** Use `ExitStack` whenever the number of context managers is dynamic (computed at runtime). Use `AsyncExitStack` for the async equivalent. Use `callback()` for unconditional cleanups and `push()` for exception-aware cleanups.

**Both sides:** The alternative is a manual `try`/`finally` chain with a list of "things to clean up." That's verbose, error-prone (forget to close one in the `finally`), and not composable. `ExitStack` is the composable primitive — you can pass an `ExitStack` to a function that pushes more cleanups onto it.

**Commitment:** `boardly` uses `ExitStack` in `config/loader.py` to manage multiple config files, in `cli/commands.py` to manage multiple sub-command contexts, and in `db/session.py` to manage nested transaction scopes. The `AsyncExitStack` form is used in `api/middleware.py` to manage per-request dependency lifecycles (mirroring what FastAPI's `Depends` does internally). The rule: any time you're tempted to write `try: ... finally: for x in reversed(things): x.close()`, use an `ExitStack` instead.

**Why not just always use nested `with` blocks?** Because nested `with` requires static N. For dynamic N, the only alternatives are `ExitStack` (good) or a manual `try`/`finally` chain (bad). `ExitStack` is the right tool.

## Exercises

1. **Exercise 1 — Use `enter_context` with a real file.** Replace `Resource("config-1")` with `open("/etc/hostname")` (or any small text file). Verify the file is closed on stack exit by checking `f.closed` after the `with`. `Verify: uv run python -c "import contextlib; ..."`.

2. **Exercise 2 — Conditional entry.** Modify `use_exit_stack_dynamic` to skip resources where `n == "config-2"` using a `for` loop with `continue`. Verify only 2 resources are opened and closed. `Verify: uv run python boardly/exitstack_demo.py`

3. **Exercise 3 — Use `push` for conditional cleanup.** Write a `transaction(exit_type, exit_value, tb)` that prints "commit" if `exit_type is None` and "rollback" otherwise. Register it via `stack.push(transaction)`. Verify "rollback" prints when the body raises. `Verify: uv run python boardly/exitstack_demo.py`

4. **Exercise 4 — Mix sync and async in `AsyncExitStack`.** In `use_async_exit_stack`, also use `stack.enter_context(Resource("sync-in-async"))` to push a sync context manager. Verify it cleans up correctly in LIFO order with the async resources. `Verify: uv run python boardly/exitstack_demo.py`

5. **Exercise 5 — Use `ExitStack` as a function argument.** Write `add_more_cleanups(stack: ExitStack)` that pushes more callbacks onto the existing stack. Verify they all clean up correctly when the outer `with` exits. This demonstrates `ExitStack`'s composability — the stack is a first-class object. `Verify: uv run python boardly/exitstack_demo.py`

## Verification

```bash
$ uv run python boardly/exitstack_demo.py
=== static with-stack ===
  [open]  config-1
  [open]  config-2
  using config-1 and config-2
  [close] config-2
  [close] config-1

=== ExitStack (static known count) ===
  [open]  config-1
  [open]  config-2
  using config-1 and config-2
  [close] config-2
  [close] config-1

=== ExitStack (dynamic count from list) ===
  [open]  config-1
  [open]  config-2
  [open]  config-3
  using ['config-1', 'config-2', 'config-3']
  [close] config-3
  [close] config-2
  [close] config-1

=== ExitStack with callback() ===
  body: do work
  [callback] cleanup #2 (first to run)
  [callback] cleanup #1 (last to run)

=== ExitStack with push() ===
  body: do work
  [push-exit] exc_type=None

=== ExitStack LIFO cleanup on exception ===
  [open]  config-1
  body: using config-1
  [close] config-1
  [callback] cleanup #2 (registered last, runs first)
  [callback] cleanup #1 (registered first, runs last)
  caught: mid-body error

=== AsyncExitStack ===
  [a-open]  a-config-1
  [a-open]  a-config-2
  using a-config-1 and a-config-2
  [a-close] a-config-2
  [a-close] a-config-1
```

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — `@contextmanager` wraps one generator; `ExitStack` wraps N context managers dynamically.
- [[03-contextlib/02-asynccontextmanager]] — `@asynccontextmanager` wraps one async generator; `AsyncExitStack` wraps N async context managers dynamically.

## What's Next

[[03-contextlib/04-suppress]] — a short, opinionated lesson on `contextlib.suppress`. The lesson: use `with suppress(KeyError): ...` instead of `try: ... except KeyError: pass` — it's one line shorter and signals intent more clearly.

- `with suppress(ExceptionType):` — the one-line try/except/pass.
- The `None`-return behaviour on suppress.
- When `suppress` beats a bare `try`/`except`/`pass`.

## Sources

- **`contextlib.ExitStack`** — https://docs.python.org/3.12/library/contextlib.html#contextlib.ExitStack — accessed 2026-10-23 — the canonical reference for `enter_context`, `push`, `callback`, and the LIFO cleanup order.
- **`contextlib.AsyncExitStack`** — https://docs.python.org/3.12/library/contextlib.html#contextlib.AsyncExitStack — accessed 2026-10-23 — the async sibling (3.7+).
- **PEP 533 — Deterministic cleanup for iterators** — https://peps.python.org/pep-0533/ — accessed 2026-10-23 — the proposal that discussed extending context-manager semantics, related to `ExitStack`'s design.

## What We Learned

- You can apply `contextlib.ExitStack()` as a dynamic context manager for runtime-known N resources.
- You can use `enter_context(cm)`, `push(callable)`, and `callback(fn, *args)` to register cleanups.
- You can explain the LIFO cleanup order — last-registered runs first.
- You can apply `AsyncExitStack` with `await enter_async_context(...)` for async resources.
- You can articulate when `ExitStack` beats a manual `try`/`finally` chain — always, for dynamic N.
