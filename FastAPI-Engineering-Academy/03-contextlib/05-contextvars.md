---
title: "Lesson 05: contextvars"
aliases:
 - contextvars
 - ContextVar
 - contextvars.Context
 - PEP 567
tags:
 - contextlib
 - contextvars
 - pep-567
 - fastapi-primitive
 - canonical
 - context-managers
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "45–60 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
related_lessons:
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
 - "[[03-contextlib/04-suppress]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/11-typing-vs-runtime]]"
first_taught_in: "03-contextlib/05-contextvars"
---

# Lesson 05: `contextvars`

*THE FastAPI request-scoped state primitive (PEP 567). `ContextVar("name")`, `.get()/.set()`, the `Token` returned by `.set()` for `.reset(token)`, the copy-on-create semantics for asyncio tasks — and why a DB session per request is a `ContextVar`, not a global.*

**You're at the very beginning of Section 03's most important lesson.**

If there is one lesson in this section to read twice, this is it. `contextvars.ContextVar` is the primitive that lets a FastAPI middleware say `request_id_var.set(uuid4())` once, and every handler — synchronous or `async`, in any dependency, at any depth of the call stack — see that same `request_id_var.get()` without a single argument threaded through. It is how Starlette and FastAPI store the per-request state that `Depends` reads, how `structlog` correlates log lines per request, how SQLAlchemy 2.0's async session is scoped. The mechanism is PEP 567, added in Python 3.7, and it is *not* thread-local storage — it is the asyncio-aware successor. By the end of this lesson you will know the `ContextVar` lifecycle, the `Token` reset contract, the copy-on-create semantics that makes asyncio safe, and the exact middleware pattern FastAPI uses. Take your time. Type every example. **This is how you learn.**

#contextlib #contextvars #canonical #fastapi-primitive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct** `ContextVar("name", default=...)` and explain why the default is the *factory-less* baseline — there is no `default_factory` (unlike `dataclasses.field`).
2. **Use** `.get()`, `.set(value)` (returns a `Token`), and `.reset(token)` to manage a per-context value safely, including the LIFO reset rule.
3. **Explain** the `Token` object — its `.var` and `.old_value` attributes, and the `<Token.MISSING>` sentinel that marks "the var was at its default".
4. **Reproduce** the copy-on-create semantics for asyncio tasks: a `ContextVar` set in a parent task is visible in child tasks created afterwards, but a `.set()` in a child does *not* leak back.
5. **Apply** the FastAPI middleware pattern — `request_id_var.set(uuid4())` in middleware, `request_id_var.get()` in any handler — and explain why this is the per-request DB session primitive.

## Prerequisites

Before starting, you need:

- **[[03-contextlib/01-contextmanager]]** — `ContextVar` is *not* a context manager itself, but the `set`/`reset` pattern and the `token_reset` helper are. Read lesson 01 first.
- **[[03-contextlib/03-ExitStack-and-AsyncExitStack]]** — FastAPI uses an `AsyncExitStack` to manage per-request dependencies; the `ContextVar` set in middleware is one half of that lifecycle.
- **[[01-typing/02-Annotated-and-Metadata]]** — the `Annotated[T, Depends(...)]` form is what FastAPI uses to inject the per-request state this lesson sets up. The two halves meet.
- **About 45–60 minutes of focused time.**

**The most common gap: reaching for `threading.local` when the code is async.**

`threading.local` is per-thread state — and in asyncio, all coroutines on the same event loop share *one* thread. If you store the DB session in `threading.local`, every concurrently-running request overwrites the previous one's session — silently, no error, the wrong data is read from the wrong session. `ContextVar` is the fix: it is per-context, and asyncio copies the context on task creation, so each task sees its own copy. If you have ever reached for `threading.local` in an async codebase and seen "ghost data" in tests, this lesson is the cure.

## The Problem

You ship `boardly/middleware/request_id.py`. The requirement is:

1. In middleware, generate a `request_id` per incoming HTTP request (`uuid4()`).
2. In every route handler, every dependency, every log call, the `request_id` is visible — without threading it through every function signature.
3. Two concurrently-running requests must *not* see each other's `request_id`.

The naive approach is a global:

```python
_current_request_id: str | None = None

def set_request_id(rid: str) -> None:
    global _current_request_id
    _current_request_id = rid

def get_request_id() -> str | None:
    return _current_request_id
```

This works for a single-threaded test. It fails the moment two requests overlap — request A sets the id to `"aaa"`, request B sets it to `"bbb"`, request A's handler now logs `"bbb"`. The global is shared; concurrent requests clobber each other.

The `threading.local` approach looks like it fixes this:

```python
import threading
_local = threading.local()

def set_request_id(rid: str) -> None:
    _local.rid = rid

def get_request_id() -> str | None:
    return getattr(_local, "rid", None)
```

This works for synchronous code where each request runs on its own thread (e.g., a Flask Gunicorn worker). It *fails* for async code where multiple coroutines share one event loop thread — the `threading.local` storage is per-thread, so two `async` handlers running concurrently see the *same* slot. The fix is `ContextVar`, which is per-context, not per-thread:

```python
import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id")

def set_request_id(rid: str) -> contextvars.Token[str]:
    return request_id_var.set(rid)

def get_request_id() -> str:
    return request_id_var.get()
```

`ContextVar` is the asyncio-aware successor to `threading.local` (PEP 567). This lesson walks the full lifecycle.

## The Code

```python
# boardly/contextvars_demo.py
"""contextvars.ContextVar — the FastAPI per-request state primitive (PEP 567)."""
from __future__ import annotations

import asyncio
import contextvars
from uuid import uuid4

# --- The request-scoped primitive ---
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request"
)

db_session_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "db_session", default=None
)


# --- The FastAPI middleware pattern (synchronous shape) ---
def middleware(handler, request_id: str):
    """Set the request_id in middleware; reset on the way out."""
    token = request_id_var.set(request_id)
    try:
        return handler()
    finally:
        request_id_var.reset(token)


def list_tickets_handler() -> dict[str, str]:
    """Route handler — reads the request_id set by middleware, no args threaded."""
    return {"request_id": request_id_var.get(), "tickets": [1, 2, 3]}


# --- The copy-on-create semantics for asyncio tasks ---
async def child(task_name: str) -> None:
    print(f"  child {task_name} sees request_id: {request_id_var.get()}")
    new_token = request_id_var.set(f"set-by-{task_name}")
    print(f"  child {task_name} after set: {request_id_var.get()}")
    # No reset — set does not leak back to parent anyway.
    return new_token


async def main_async() -> None:
    request_id_var.set("parent-value")
    print(f"parent before gather: {request_id_var.get()}")
    await asyncio.gather(child("A"), child("B"))
    print(f"parent after gather: {request_id_var.get()}")


if __name__ == "__main__":
    # 1. Basic get/set/reset.
    print("--- Token lifecycle ---")
    print("default:", request_id_var.get())
    token = request_id_var.set("req-abc")
    print("after set:", request_id_var.get())
    print("token type:", type(token).__name__)
    print("token.var.name:", token.var.name)
    print("token.old_value:", token.old_value)
    request_id_var.reset(token)
    print("after reset:", request_id_var.get())

    # 2. Middleware pattern.
    print("\n--- Middleware pattern ---")
    result = middleware(list_tickets_handler, str(uuid4()))
    print("handler result:", result)
    print("after middleware exited:", request_id_var.get())

    # 3. Asyncio copy-on-create.
    print("\n--- asyncio copy-on-create ---")
    asyncio.run(main_async())

    # 4. No default → LookupError.
    print("\n--- no default → LookupError ---")
    no_default = contextvars.ContextVar("no_default")
    try:
        no_default.get()
    except LookupError as e:
        print("LookupError:", e)
    print("get(default-arg):", no_default.get("fallback"))
```

## Line-by-Line Deep Dive

### Lines 1–10: Module header and the request-scoped primitive

```python
# boardly/contextvars_demo.py
"""contextvars.ContextVar — the FastAPI per-request state primitive (PEP 567)."""
from __future__ import annotations

import asyncio
import contextvars
from uuid import uuid4

# --- The request-scoped primitive ---
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request"
)
```

`contextvars.ContextVar("request_id", default="no-request")` constructs the context variable. The first argument is a *name* — a human-readable string used in `repr`, error messages, and the `Token.var.name` attribute. The name is *not* the variable's identity (the Python object is); it is a debug label. The `default` argument is the value returned by `.get()` when the var has not been `.set()` in the current context. Without a default, `.get()` raises `LookupError`.

The module-level binding `request_id_var` is the *single* context variable object. Every call to `.set()` or `.get()` — in any task, any coroutine, any thread — operates on the *same* `ContextVar` object; what differs is the per-context *value* stored against it. That distinction — one shared `ContextVar` object, many per-context values — is the heart of PEP 567.

**Why is there no `default_factory` (unlike `dataclasses.field`)?**

Because `ContextVar`'s default is meant to be a simple, immutable fallback — typically a string or `None`. If the default were a mutable factory (e.g., `default_factory=list`), each `.get()` from a fresh context would have to call the factory, and you would have to choose whether the result is cached (so a second `.get()` returns the same list) or fresh (every `.get()` returns a new list). PEP 567 sidesteps the question: the default is a value, not a factory. If you want a fresh mutable per context, `set` it explicitly in middleware (e.g., `db_session_var.set(Session())`) — that is the FastAPI pattern, and the right pattern.

### Lines 12–14: A second `ContextVar` — DB session per request

```python
db_session_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "db_session", default=None
)
```

The DB session is the canonical "second" `ContextVar` in a FastAPI app — set in a dependency (`get_db`) when the request begins, reset (or closed) when the request ends. The type is `str | None` here for the demo (a real app uses `Session | None`); the `default=None` lets any code that reads `db_session_var.get()` before the dependency runs get `None` instead of a `LookupError`. This is the *safe* default pattern: pick `None` so that uninitialised reads are predictable.

**Why is the DB session a `ContextVar` and not a function argument?**

Two reasons. (1) The session has to be visible at *many* layers — the route handler, the service layer, the repository layer, the SQLAlchemy `before_flush` hook — without threading it through every signature. `ContextVar` is the language-level "ambient state" primitive; it lets you write `db_session_var.get()` anywhere. (2) The session has to be per-request, not per-process. `ContextVar` with the asyncio copy-on-create semantics (covered below) gives you per-request isolation for free; a global would not. Cross-link to [[01-typing/02-Annotated-and-Metadata]]: FastAPI's `Depends(get_db)` reads the session from the `ContextVar` *inside* `get_db`, then injects the value into the route handler as a normal argument — so the route signature stays clean (`db: Session = Depends(get_db)` or `db: Annotated[Session, Depends(get_db)]`), and the ambient read happens once inside `get_db`.

### Lines 17–23: The FastAPI middleware pattern (synchronous shape)

```python
# --- The FastAPI middleware pattern (synchronous shape) ---
def middleware(handler, request_id: str):
    """Set the request_id in middleware; reset on the way out."""
    token = request_id_var.set(request_id)
    try:
        return handler()
    finally:
        request_id_var.reset(token)
```

This is the FastAPI middleware pattern, distilled. Three steps:

1. `request_id_var.set(request_id)` — sets the value in the *current* context and returns a `Token`. The `Token` is your receipt — it captures "what the value was before this set" so you can restore it later.
2. `handler()` — the route runs. Inside the handler (and any function it calls, any `await` it makes), `request_id_var.get()` returns the value you just set, with zero arguments threaded.
3. `request_id_var.reset(token)` — restores the var to its previous value. The `finally` guarantees this runs even if `handler()` raises.

**Why `reset(token)` instead of `set(original_value)`?**

Because `reset(token)` is the only way to restore the *exact* prior state, including the case where the var was never set in the first place. `set(original_value)` would push a new `Token` onto the stack — leaving the var in a state where `token.old_value` says `"no-request"` even after the middleware has exited. `reset(token)` *pops* the stack, restoring the var to whatever it was before the corresponding `set`. The LIFO rule — tokens must be reset in reverse order of their `set` — is what makes `ContextVar` compose across nested middleware. Violate it and Python raises `ValueError` ("Token was not created by the current context").

**Danger — Forgetting to `reset(token)` leaks context across requests.**

If the `finally` is missing or skipped, the value set in middleware survives into the *next* request handled on the same context (in async code, the next task that reuses the context). The symptom is "ghost request_id" — request A's id appears in request B's logs, two minutes apart, on different endpoints. Always pair `set` with `reset` in a `try`/`finally`, or use `contextvars.copy_context()` for snapshot semantics instead.

### Lines 25–28: The handler — `request_id_var.get()` with no arguments

```python
def list_tickets_handler() -> dict[str, str]:
    """Route handler — reads the request_id set by middleware, no args threaded."""
    return {"request_id": request_id_var.get(), "tickets": [1, 2, 3]}
```

The handler is just a function — no `request_id` parameter. It calls `request_id_var.get()` and receives the value set by middleware. This is the entire point of `ContextVar`: ambient state, readable anywhere, scoped per-request. Compare to the alternative — `def list_tickets_handler(request_id: str): ...` — which forces every caller to thread the id through, every test to set up a fake id, every intermediate function to accept and forward it. `ContextVar` eliminates that.

**Why is this safe under concurrency?**

Because of the copy-on-create semantics, walked below. In an asyncio app, each task gets its own *copy* of the context when the task is created. So request A's `set("aaa")` lives in request A's context; request B's `set("bbb")` lives in request B's context; the two never collide. In a multi-threaded sync app, the same holds — each thread has its own context (the default context is created when the thread starts, and threads do not share contexts). The isolation is structural, not convention-al.

### Lines 31–37: Copy-on-create for asyncio tasks — child reads, child writes do not leak

```python
# --- The copy-on-create semantics for asyncio tasks ---
async def child(task_name: str) -> None:
    print(f"  child {task_name} sees request_id: {request_id_var.get()}")
    new_token = request_id_var.set(f"set-by-{task_name}")
    print(f"  child {task_name} after set: {request_id_var.get()}")
    # No reset — set does not leak back to parent anyway.
    return new_token
```

`child("A")` is a coroutine scheduled via `asyncio.gather`. When asyncio creates the task, it copies the *parent's* context — at the moment of task creation — into a new context for the child. The child sees the parent's `request_id_var` value (the `set("parent-value")` in `main_async`), because that was in the parent's context at the time the task was created.

The child then does `request_id_var.set("set-by-A")`. This *modifies the child's copy* of the context — not the parent's, not sibling B's. The print confirms: the child sees its own new value. When the child returns and the parent resumes, the parent's `request_id_var.get()` is *still* `"parent-value"` — the child's mutation did not leak back.

**Why copy-on-create and not share-by-reference?**

Because the alternative — sharing one context across tasks — would re-introduce the global-mutation bug. If request A's task and request B's task shared a context, request A's `set` would clobber request B's value mid-flight. PEP 567's choice is: copy at task creation, so each task gets a private snapshot it can mutate freely. The cost is one dict copy per task — negligible compared to the IO work each task is doing. The benefit is correct concurrent isolation for free.

**Tip — `asyncio.create_task` copies; `asyncio.run_coroutine_threadsafe` does not.**

`asyncio.create_task(coro)` copies the current context at task-creation time — this is the standard path. `asyncio.run_coroutine_threadsafe(coro, loop)` schedules the coroutine on a *different* loop's thread, and the context copy happens on the destination loop's thread — which may not have the parent's context. If you need cross-thread context propagation, you must `copy_context()` manually and `ctx.run(...)` your coroutine. This is rare in FastAPI (which is single-loop) but common in test harnesses.

### Lines 39–44: `main_async` — gather two children, parent value unchanged

```python
async def main_async() -> None:
    request_id_var.set("parent-value")
    print(f"parent before gather: {request_id_var.get()}")
    await asyncio.gather(child("A"), child("B"))
    print(f"parent after gather: {request_id_var.get()}")
```

`main_async` sets the var to `"parent-value"`, schedules two children via `gather`, then prints the value again. The two children run concurrently (well, interleaved — asyncio is single-threaded). Each child reads `"parent-value"` (the parent's value at the time the task was created), sets its own value, and returns. The parent's value is *unchanged* after the gather — proving the copy-on-create semantics. This is the property that makes `ContextVar` safe for per-request state in an asyncio app: every task sees the value set by the *parent* (the request's middleware), and no task can mutate another's view.

### Lines 46–62: The `__main__` block — Token lifecycle, middleware, asyncio, LookupError

```python
if __name__ == "__main__":
    # 1. Basic get/set/reset.
    print("--- Token lifecycle ---")
    print("default:", request_id_var.get())
    token = request_id_var.set("req-abc")
    print("after set:", request_id_var.get())
    print("token type:", type(token).__name__)
    print("token.var.name:", token.var.name)
    print("token.old_value:", token.old_value)
    request_id_var.reset(token)
    print("after reset:", request_id_var.get())
```

The `Token` object has two attributes worth knowing: `.var` (the `ContextVar` the token was created against — useful when juggling multiple vars) and `.old_value` (the value the var held *before* this `set`). On the first `set` against a var that was at its default, `old_value` is the sentinel `<Token.MISSING>` — a "no previous value" marker, *not* the default. (`Token.MISSING` exists so you can distinguish "the var was at its default of `None`" from "the var had never been set" — the default is a real value, the sentinel means "unset".) After `reset(token)`, the var is back at its default `"no-request"`. The LIFO rule: if you have two tokens `t1` then `t2`, you must `reset(t2)` before `reset(t1)`. Violate it and `ValueError` fires.

### Lines 64–67: The middleware pattern in action

```python
    # 2. Middleware pattern.
    print("\n--- Middleware pattern ---")
    result = middleware(list_tickets_handler, str(uuid4()))
    print("handler result:", result)
    print("after middleware exited:", request_id_var.get())
```

`middleware(list_tickets_handler, str(uuid4()))` runs the middleware around the handler. Inside the handler, `request_id_var.get()` returns the uuid set by middleware — confirmed by `result["request_id"]` being that uuid. After the middleware returns, `request_id_var.get()` is back to `"no-request"` — the `finally: reset(token)` did its job. This is the FastAPI contract, distilled to four lines of middleware.

### Lines 69–72: Asyncio copy-on-create in action

```python
    # 3. Asyncio copy-on-create.
    print("\n--- asyncio copy-on-create ---")
    asyncio.run(main_async())
```

`asyncio.run(main_async())` runs the coroutine, which sets the var, gathers two children, and confirms the parent value is unchanged after. The output proves the isolation property — see the Execution Trace.

### Lines 74–81: `LookupError` when there is no default

```python
    # 4. No default → LookupError.
    print("\n--- no default → LookupError ---")
    no_default = contextvars.ContextVar("no_default")
    try:
        no_default.get()
    except LookupError as e:
        print("LookupError:", e)
    print("get(default-arg):", no_default.get("fallback"))
```

`no_default = contextvars.ContextVar("no_default")` — no `default=` argument. Calling `no_default.get()` raises `LookupError` (a subclass of `KeyError`/`IndexError`'s parent). The error message includes the var's name — useful for debugging. The `no_default.get("fallback")` form accepts an inline default, returning `"fallback"` if the var is unset. This is the `dict.get(k, default)` parallel.

**Why `LookupError` and not `AttributeError` or a custom `ContextVarError`?**

`LookupError` is the standard library's "key-not-found" parent class — `KeyError` and `IndexError` both inherit from it. PEP 567 chose it so that `except LookupError:` catches both `ContextVar`-unset and dict/list-not-found cases, which is the common "look up a value that might be missing" pattern. A custom exception would force callers to add a new `except` clause. `LookupError` is the right level of abstraction.

## Execution Trace

```bash
$ python boardly/contextvars_demo.py
--- Token lifecycle ---
default: no-request
after set: req-abc
token type: Token
token.var.name: request_id
token.old_value: <Token.MISSING>
after reset: no-request

--- Middleware pattern ---
handler result: {'request_id': '...', 'tickets': [1, 2, 3]}
after middleware exited: no-request

--- asyncio copy-on-create ---
parent before gather: parent-value
  child A sees request_id: parent-value
  child A after set: set-by-A
  child B sees request_id: parent-value
  child B after set: set-by-B
parent after gather: parent-value

--- no default → LookupError ---
LookupError: <ContextVar name='no_default' at 0x...>
get(default-arg): fallback
```

(Where `...` is a freshly-generated uuid4 and `0x...` is a hex address — both vary per run.) The four blocks each prove a property: the `Token` lifecycle (default → set → reset → default), the middleware pattern (set in middleware, read in handler, reset on exit), the asyncio copy-on-create (children see parent's value, parent's value is unchanged after children mutate their copies), and the `LookupError` path when no default is supplied.

## Common Mistakes

### Mistake 1: Forgetting `reset(token)` — context leaks across requests

```python
def middleware(handler, rid):
    request_id_var.set(rid)   # ← token discarded
    return handler()         # ← no reset
```

**Symptom:** Request A's `request_id` is still visible when request B's handler runs (if both share a context — common in async test runners). The logs show A's id in B's entries.
**Why:** `ContextVar.set` mutates the *current* context. Without `reset`, the mutation survives the middleware exit. The next handler on the same context inherits the value.
**Fix:**

```python
def middleware(handler, rid):
    token = request_id_var.set(rid)
    try:
        return handler()
    finally:
        request_id_var.reset(token)
```

Or use `contextvars.copy_context()` and `ctx.run(...)` to run the handler in a fresh context that is discarded on exit. The `try`/`finally`+`reset` shape is the FastAPI/Starlette pattern.

### Mistake 2: Treating `ContextVar` like a global — sharing across threads in sync code

```python
request_id_var = contextvars.ContextVar("request_id")   # module level
# Worker thread 1: request_id_var.set("aaa")
# Worker thread 2: request_id_var.set("bbb")
# Both threads read request_id_var.get() and expect different values.
```

**Symptom:** Worker thread 1 sees `"bbb"` after thread 2 set it — the values appear to share.
**Why:** `ContextVar` *is* per-context, but the default context for a *new thread* is empty. If you `set` in one thread and `get` in another without first `set`-ing in that other thread, the second thread gets the default (or `LookupError`). Threads do not share contexts — but threads do share the `ContextVar` object itself, and without per-thread `set`, every thread sees the same default.
**Fix:** `set` the var at the start of each thread's work (e.g., in the request handler entry), or use a `threading.local`-shaped wrapper that initialises on thread start. In async code, the issue does not arise because the event loop's context is copied per task. The general rule: each context that wants a non-default value must `set` it explicitly.

### Mistake 3: Using `threading.local` in async code

```python
import threading
_local = threading.local()
_local.session = Session()   # set in dependency
# async handler reads _local.session
```

**Symptom:** Two concurrent async requests share the same session. Request A's commit flushes request B's pending changes; data corruption or `InvalidRequestError` ("object is already in another session").
**Why:** All coroutines on the same event loop share one thread. `threading.local` is per-thread, so all coroutines see the same slot. The session set by request A is *the* session, overwritten by request B.
**Fix:** Use `contextvars.ContextVar` instead. The copy-on-create semantics give each task its own value. This is the canonical migration from `threading.local` to `ContextVar` — and it is the migration Starlette, FastAPI, SQLAlchemy 2.0, and structlog all made between 2018 and 2022.

## Engineering Trade-Offs

**Decision:** Use `contextvars.ContextVar` for per-request ambient state in async code (and in sync code that might go async). Reserve `threading.local` for code that is *synchronous-only* and never shares a thread with concurrent work (e.g., a CLI tool that does not need cross-coroutine isolation).
**Both sides:** `threading.local` is simpler to reason about in pure sync code — one slot per thread, full stop. It does not require thinking about contexts or tasks. The cost is that it silently breaks the moment async creeps in: tests pass, production corrupts. `ContextVar` is the asyncio-correct primitive — it works in sync and async, with copy-on-create semantics that scale to thousands of concurrent tasks without crosstalk. The cost is one extra concept (the `Context` and the copy-on-create rule) to learn.
**Commitment:** boardly uses `ContextVar` for every per-request primitive — `request_id_var`, `db_session_var`, `tenant_id_var`, `correlation_id_var`. There is no `threading.local` in the boardly codebase. The Starlette/FastAPI middleware contract is `set` in middleware, `reset` in `finally`, `get` anywhere — and we follow it precisely.

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/contextvars_demo.py` and run it. Compare your output to the Execution Trace — the `parent after gather: parent-value` line is the proof of copy-on-create. `Verify: python boardly/contextvars_demo.py`
2. **Exercise 2 — LIFO violation raises `ValueError`.** Call `t1 = request_id_var.set("a")` then `t2 = request_id_var.set("b")` then `request_id_var.reset(t1)` (out of order). Catch the `ValueError`. Restore with `reset(t2)` then `reset(t1)`. `Verify: python -c "import contextvars; from boardly.contextvars_demo import request_id_var; t1 = request_id_var.set('a'); t2 = request_id_var.set('b'); \ntry: request_id_var.reset(t1) \nexcept ValueError as e: print('caught:', e); request_id_var.reset(t2); request_id_var.reset(t1); print('reset ok')"` — if the shell quoting bites you, write a small script.
3. **Exercise 3 — `copy_context()` snapshot.** Use `contextvars.copy_context()` to take a snapshot of the current context, mutate the var, then `ctx.run(some_fn)` that reads the var. Confirm the snapshot sees the *old* value, and the mutation is invisible to the snapshot. `Verify: python -c "import contextvars; from boardly.contextvars_demo import request_id_var; request_id_var.set('orig'); ctx = contextvars.copy_context(); request_id_var.set('mutated'); print(ctx.get(request_id_var))"`
4. **Exercise 4 — Build a `request_scope` context manager.** Write `@contextmanager def request_scope(rid): token = request_id_var.set(rid); try: yield; finally: request_id_var.reset(token)`. Use it as `with request_scope("rid-1"): print(request_id_var.get())`. Confirm the var is reset on exit. `Verify: python -c "from boardly.contextvars_demo import request_scope, request_id_var; \nwith request_scope('rid-1'): print(request_id_var.get()) \nprint(request_id_var.get())"`
5. **Exercise 5 — `Depends`-shaped dependency that reads the `ContextVar`.** Write `def get_db_session() -> str: return db_session_var.get()` and a route `def list_tickets(db: Annotated[str, Depends(get_db_session)]): ...`. Set `db_session_var` to a value in a `with request_scope(...)` block, call the route via a fake dispatcher, and confirm the handler receives the var's value. Cross-link to [[01-typing/02-Annotated-and-Metadata]] for the `Annotated[T, Depends(...)]` form. `Verify: python -c "from boardly.contextvars_demo import db_session_var, request_scope, get_db_session, list_tickets; \nfrom typing import Annotated \nwith request_scope('sess-1'): \n  print(list_tickets())"` — wire `list_tickets` to call `get_db_session()` internally.

## Verification

```bash
$ python boardly/contextvars_demo.py
--- Token lifecycle ---
default: no-request
after set: req-abc
token type: Token
token.var.name: request_id
token.old_value: <Token.MISSING>
after reset: no-request

--- Middleware pattern ---
handler result: {'request_id': '...', 'tickets': [1, 2, 3]}
after middleware exited: no-request

--- asyncio copy-on-create ---
parent before gather: parent-value
  child A sees request_id: parent-value
  child A after set: set-by-A
  child B sees request_id: parent-value
  child B after set: set-by-B
parent after gather: parent-value

--- no default → LookupError ---
LookupError: <ContextVar name='no_default' at 0x...>
get(default-arg): fallback
```

(Where `...` is a per-run uuid and `0x...` is a per-run hex address.) The four blocks prove the four properties. If the `parent after gather: parent-value` line shows anything other than `parent-value`, copy-on-create is broken — and that would mean CPython itself is broken.

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — `@contextmanager` and the `try`/`yield`/`finally` pattern. This lesson uses the same `try`/`finally` shape, but for `set`/`reset` instead of `yield`/`close`. Exercise 4 turns the pattern into a `@contextmanager`.
- [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — FastAPI uses an `AsyncExitStack` to manage per-request dependencies; the `ContextVar` set in middleware is the state half of that lifecycle, and the `AsyncExitStack` is the cleanup half.

## What's Next

[[03-contextlib/06-redirect_stdout-stderr]] — the testing utilities. `ContextVar` is request-scoped state; `redirect_stdout` and `redirect_stderr` are *output-capture* scope — narrower, for tests and CLI tools. Three things to look for in lesson 06:

- The `io.StringIO` capture pattern: redirect stdout into a `StringIO`, run the code, read the buffer.
- The `ExitStack` + `redirect_stdout` + `redirect_stderr` combo for capturing both at once.
- When to use `contextlib.redirect_stdout` vs `unittest.mock.patch("sys.stdout", ...)` — and why `redirect_stdout` is safer for test code.

Take your time. Type every example. **This is how you learn.**

## Sources

- **`contextvars` — Context Variables** — https://docs.python.org/3/library/contextvars.html — accessed 2026-10-23 — the canonical CPython reference for `ContextVar`, `Token`, `Context`, and `copy_context()`.
- **PEP 567 — Context Variables** — https://peps.python.org/pep-0567/ — accessed 2026-10-23 — the PEP that introduced `ContextVar` in 3.7, including the copy-on-create semantics for asyncio and the rationale for replacing `threading.local`.
- **PEP 567 — asyncio integration** — https://peps.python.org/pep-0567/#context-and-asyncio — accessed 2026-10-23 — the section that specifies `asyncio.Task` copies the context at creation time.
- **Starlette source — `BaseHTTPMiddleware`** — https://github.com/encode/starlette/blob/master/starlette/middleware/base.py — accessed 2026-10-23 — the production middleware that uses `contextvars.copy_context()` to isolate per-request state in async apps.
- **CPython source — `Lib/contextvars.py` and `Modules/_contextvarsmodule.c`** — https://github.com/python/cpython/blob/3.12/Modules/_contextvars.c — accessed 2026-10-23 — the C-level implementation of `ContextVar`, `Token`, and the copy-on-create snapshot.

## What We Learned

- `contextvars.ContextVar("name", default=...)` is the per-context state primitive — one shared object, many per-context values. `default` is a value, not a factory.
- `.get()` returns the current context's value or the default; raises `LookupError` if no default and unset. `.get(fallback)` accepts an inline default.
- `.set(value)` returns a `Token` (with `.var` and `.old_value` attributes; `old_value` is `<Token.MISSING>` on the first set against a default). `.reset(token)` pops back to the prior state, LIFO order enforced.
- `copy_context()` snapshots the current context; `ctx.run(callable)` runs in the snapshot; mutations inside `ctx.run` do not leak back to the caller.
- asyncio's `Task` copies the context at task-creation time — children see the parent's value at that moment; child `set`s do not leak back to the parent or to siblings.
- The FastAPI middleware pattern: `token = var.set(rid)` in middleware, `var.get()` in any handler, `var.reset(token)` in a `finally` block — the per-request DB session primitive.
- `threading.local` is *not* safe in async code — `ContextVar` is the asyncio-aware successor, and the migration Starlette, FastAPI, SQLAlchemy 2.0, and structlog all made.
