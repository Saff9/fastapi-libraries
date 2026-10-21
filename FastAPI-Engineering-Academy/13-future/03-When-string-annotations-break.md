---
title: "Lesson 03: When string annotations break"
aliases:
 - NameError on get_type_hints
 - localns globalns
 - FastAPI Annotated resolution
 - local types in annotations
tags:
 - __future__
 - typing
 - failure-modes
 - debugging
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[13-future/01-from-future-import-annotations]]"
 - "[[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
related_lessons:
 - "[[10-inspect/00-inspect-MOC]]"
---

# Lesson 03: When string annotations break

*The four failure modes of PEP 563's string-storage design — `NameError` on `get_type_hints()` when a name is out of scope, the `localns`/`globalns` workaround, the FastAPI `Annotated[int, Depends(...)]` resolution path, and the "no local types in annotations" rule that has bitten every team that uses `from __future__ import annotations` seriously.*

**You're at the very beginning of Section 13, third and final lesson in.**

You finished lessons 01 and 02. You know what `from __future__ import annotations` does, you know the PEP saga, you know PEP 649 is the proper fix. You are running on 3.12 and you are paying PEP 563's cost — the string-storage behaviour. This lesson is the failure-mode deep dive. Four failure modes, four `boardly` symptoms, four fixes. The lesson closes the section by showing you *why* each failure happens at the bytecode level and *how* PEP 649 (3.14) fixes it. By the end, you will be able to diagnose a `NameError` from `get_type_hints()` in under a minute — and you will know to upgrade to 3.14 as the strategic fix.

#__future__ #typing #failure-modes

## Learning Objectives

By the end of this lesson you will be able to:

1. **Diagnose the `NameError` from `get_type_hints()`** — read the traceback, find the missing name, find the scope it should be in, apply the `localns`/`globalns` workaround.
2. **Explain the "no local types in annotations" rule** — why classes defined inside functions cannot be referenced in annotations, and the two valid workarounds.
3. **Trace the FastAPI `Annotated[int, Depends(...)]` resolution path** — why `Depends` must be importable from `func.__globals__`, and how `from __future__ import annotations` interacts.
4. **Reason about the `include_extras=True` requirement** — why `Annotated` metadata is stripped without the flag, and why FastAPI always passes it.
5. **Predict the 3.14 fix path** — which of the four failures PEP 649 eliminates, which it mitigates, which it leaves alone.

## Prerequisites

Before starting, you need:

- **PEP 563 mechanism** — [[13-future/01-from-future-import-annotations]]. The string-storage behaviour is the direct cause of every failure mode here.
- **PEP 649 vs 563** — [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]]. The 3.14 fix is the resolution to several of the failures.
- **`Annotated`** — [[01-typing/02-Annotated-and-Metadata]]. The `Annotated[int, metadata]` primitive and its `include_extras` resolution behaviour.
- **About 30–45 minutes of focused time.**

**The most common gap: "no local types in annotations".**

Students define a class inside a function (a common pattern for test fixtures, factory functions, schema generation) and use it as an annotation in the same function. With `from __future__ import annotations`, the file imports without error — the annotation is stored as a string. The first call to `get_type_hints(func)` raises `NameError` — the local class is not in `func.__globals__`. The fix is to either (a) move the class to module level, or (b) pass `localns={"LocalClass": LocalClass}` to `get_type_hints()`. The rule "no local types in annotations" is the lesson's central commit — and it is the rule PEP 649 (3.14) lifts.

## The Problem

You have a `boardly` route that takes a `Ticket` body. The route depends on a `get_db` session:

```python
from __future__ import annotations
from typing import Annotated
from fastapi import Depends, FastAPI

app = FastAPI()

def get_db():
    ...

@app.post("/tickets")
def create_ticket(ticket: Ticket, db: Annotated[Session, Depends(get_db)]):
    ...
```

This works on 3.12 because `Depends` and `get_db` are in `create_ticket.__globals__` — the module's globals. But if you move `get_db` inside a factory function:

```python
def make_app():
    def get_db():
        ...

    @app.post("/tickets")
    def create_ticket(ticket: Ticket, db: Annotated[Session, Depends(get_db)]):
        ...

    return app
```

— the route's annotation string `"Annotated[Session, Depends(get_db)]"` cannot be resolved: `get_db` is not in `create_ticket.__globals__` (it is a local in `make_app`'s frame). `get_type_hints(create_ticket)` raises `NameError: name 'get_db' is not defined`. This is the central failure mode of PEP 563, and lesson 03 walks it through four variants.

## The Code

```python
# boardly/typing_demo/annotation_failures.py
"""The four failure modes of PEP 563 string annotations."""
from __future__ import annotations

from typing import Annotated, get_type_hints


# A minimal Depends stub — stands in for `from fastapi import Depends`.
# Defined at module level so `get_type_hints` can find it during `eval()`.
class Depends:
    def __init__(self, target):
        self.target = target


# (A) Forward ref to a module-level name — works.
class ModuleTicket:
    id: int
    title: str


def get_module_ticket(id: int) -> ModuleTicket:
    ...


# (B) Local type defined in a function — fails at get_type_hints().
def make_local():
    class LocalTicket:
        id: int
        title: str

    def get_local_ticket(id: int) -> LocalTicket:
        ...

    return get_local_ticket


# (C) Depends inside a factory — fails at get_type_hints().
# `get_db` is local to `make_depends_factory`; route.__globals__ (the module's
# globals) does not include `get_db`. The `eval()` of `"Annotated[str, Depends(get_db)]"`
# raises NameError.
def make_depends_factory():
    def get_db() -> str:
        return "session"

    def route(db: Annotated[str, Depends(get_db)]) -> None:
        ...

    return route


# (D) Annotated metadata stripped by default — works but loses metadata.
def plain_route(x: Annotated[int, "meta"]) -> None:
    ...


if __name__ == "__main__":
    # (A) Module-level forward ref — resolves.
    print("(A) module hints:", get_type_hints(get_module_ticket))

    # (B) Local type — NameError.
    try:
        local_fn = make_local()
        get_type_hints(local_fn)
    except NameError as exc:
        print("(B) NameError:", exc)

    # (C) Factory-local Depends — NameError.
    try:
        route_fn = make_depends_factory()
        get_type_hints(route_fn)
    except NameError as exc:
        print("(C) NameError:", exc)

    # (D) Annotated metadata stripped by default.
    print("(D) default hints:", get_type_hints(plain_route))
    print("(D) include_extras hints:", get_type_hints(plain_route, include_extras=True))
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports and the future statement

```python
# boardly/typing_demo/annotation_failures.py
"""The four failure modes of PEP 563 string annotations."""
from __future__ import annotations

from typing import Annotated, get_type_hints
```

The future import is the trigger for every failure mode in this lesson — without it, the annotations would be eagerly evaluated at function-definition time and the local-type / factory-local `Depends` failures would appear at import (as `NameError` from the function definition) rather than at `get_type_hints()` call time. The future import *delays* the failure from import time to call time — which is better (the module imports) but harder to debug (the failure appears only when the framework resolves the annotations).

**Why does the future import delay rather than eliminate the failure?**

Because PEP 563 stores the annotation as a string at compile time, without resolving the names. The resolution happens later, when `get_type_hints()` (or any caller of `eval`) evaluates the string. The names are still missing at that point — the failure is the same, just deferred. PEP 649 (3.14) eliminates the failure by capturing the original scope at definition time and evaluating against it — the local names are visible. The "delayed failure" is a property of PEP 563, not a fix.

### Lines 7–15: Module-level forward ref

```python
# (A) Forward ref to a module-level name — works.
class ModuleTicket:
    id: int
    title: str


def get_module_ticket(id: int) -> ModuleTicket:
    ...
```

`get_module_ticket`'s return annotation is `ModuleTicket`. With the future import, the annotation is stored as the string `"ModuleTicket"`. `get_type_hints(get_module_ticket)` resolves the string against `get_module_ticket.__globals__` — which is the module's globals, which includes `ModuleTicket` (defined above). The resolution succeeds. This is the *normal* case — module-level names resolve without issue because they are in the module's globals, which is the resolution scope.

**Why does the module-level case always work?**

Because `func.__globals__` is a reference to the module's `__dict__`, which contains every name defined at module level (classes, functions, imports). The `eval` of `"ModuleTicket"` against the module's globals finds the class. The case fails only when the annotation refers to a name *not* in the module's globals — a local in a function, a name imported inside a function, a name from a different scope.

### Lines 17–25: Local type in a function

```python
# (B) Local type defined in a function — fails at get_type_hints().
def make_local():
    class LocalTicket:
        id: int
        title: str

    def get_local_ticket(id: int) -> LocalTicket:
        ...

    return get_local_ticket
```

`LocalTicket` is defined inside `make_local`'s body. It is a *local* name in `make_local`'s frame, not a global. The function `get_local_ticket` is also defined inside `make_local`. Its return annotation is `LocalTicket`, stored as the string `"LocalTicket"` (under PEP 563). When `get_type_hints(get_local_ticket)` is called *after* `make_local` returns, the resolution does `eval("LocalTicket", get_local_ticket.__globals__, None)`. `get_local_ticket.__globals__` is the *module's* globals — it does not include `LocalTicket` (which was a local in `make_local`). The `eval` raises `NameError`.

**Why does `func.__globals__` not include `LocalTicket`?**

Because `func.__globals__` is set at function-creation time to the module's `__dict__`. Local names from enclosing functions are *not* in `__globals__` — they are in the enclosing function's frame, captured as a closure cell if `func` references them. But `__annotations__` strings are not closures — they are plain strings. The resolution uses `__globals__` (module scope) plus an optional `localns` argument; without `localns`, only module globals are visible. The closure cells of `func` are *not* consulted — `get_type_hints` does not know which cells correspond to which annotation strings. This is the fundamental limit of PEP 563: it cannot capture the enclosing scope at definition time.

### Lines 27–35: Factory-local `Depends`

```python
# (C) Depends inside a factory — fails at get_type_hints().
# `get_db` is local to `make_depends_factory`; route.__globals__ (the module's
# globals) does not include `get_db`. The `eval()` of `"Annotated[str, Depends(get_db)]"`
# raises NameError.
def make_depends_factory():
    def get_db() -> str:
        return "session"

    def route(db: Annotated[str, Depends(get_db)]) -> None:
        ...

    return route
```

This is the `boardly` FastAPI failure mode. `get_db` is defined inside `make_depends_factory`. The `route` function's annotation is `Annotated[str, Depends(get_db)]` — a *real* `Depends(get_db)` call wrapped in `Annotated`. Under PEP 563 (the future import), the entire `Annotated[str, Depends(get_db)]` annotation is stored as the string `'Annotated[str, Depends(get_db)]'`. When `get_type_hints(route)` runs, it `eval`s this string against `route.__globals__` (the module's globals). `Depends` is found (it was imported at module level), but `get_db` is *not* found — it is a local in `make_depends_factory`, not in the module's globals. The `eval` raises `NameError: name 'get_db' is not defined`.

The fix is `localns={"get_db": get_db}` — pass the local name explicitly:

```python
get_type_hints(route, include_extras=True, localns={"get_db": get_db})
```

FastAPI does *not* do this automatically — FastAPI assumes the `Depends` targets are module-level (which is the convention). Factory patterns that move `Depends` targets into local scope break FastAPI under PEP 563. The fix is to define `get_db` at module level.

**Note — the lesson's earlier draft used `Annotated[str, "Depends(get_db)"]` (string metadata).**

That form *does not fail* with `NameError`. The metadata `'Depends(get_db)'` is a *string literal* preserved verbatim — `get_type_hints()` does not `eval` the metadata string, only the bare `Annotated[str, ...]` wrapper expression. The failure requires `Depends(get_db)` (without quotes), which the future import stringifies as part of the annotation string and `get_type_hints()` evaluates at resolution time. This is the canonical FastAPI pattern (`Annotated[str, Depends(get_db)]`), and it is the one the lesson walks.

**Why does FastAPI not pass `localns` automatically?**

Because FastAPI does not have access to the closure cells of `route` — only `route.__globals__`. The closure cells are accessible via `route.__closure__`, but mapping cell contents to annotation string names is not generally possible (a cell can be referenced by multiple names; a name can be shadowed). The robust path is "module-level definitions only" — the convention FastAPI documents.

### Lines 37–40: Annotated metadata stripping

```python
# (D) Annotated metadata stripped by default — works but loses metadata.
def plain_route(x: Annotated[int, "meta"]) -> None:
    ...
```

`plain_route`'s parameter `x` is annotated `Annotated[int, "meta"]`. Under PEP 563, the annotation is stored as the string `'Annotated[int, "meta"]'`. `get_type_hints(plain_route)` (without `include_extras`) returns `{"x": int}` — the `Annotated` wrapper is stripped, the metadata `"meta"` is gone. `get_type_hints(plain_route, include_extras=True)` returns `{"x": Annotated[int, "meta"]}` — the metadata is preserved.

The stripping is a backwards-compatibility behaviour: before `Annotated` existed (PEP 593, Python 3.9), `__annotations__` values were bare types. When `Annotated` was introduced, `get_type_hints()` was updated to strip the metadata by default, so old code that expected bare types kept working. The `include_extras=True` flag (added in 3.9) is the opt-in to preserve metadata — required for FastAPI and Pydantic, which use the metadata for dependency injection and validation rules.

**Why does FastAPI always pass `include_extras=True`?**

Because FastAPI's dependency-injection system reads the metadata to find `Depends(...)` markers. Without `include_extras`, the markers would be stripped and FastAPI would see bare `int`/`str` types — no dependencies would be injected. The `include_extras=True` is mandatory for FastAPI's resolution path. Pydantic uses it for the same reason — `Field(...)` validators live in the metadata.

### Lines 42–58: The sanity check

```python
if __name__ == "__main__":
    # (A) Module-level forward ref — resolves.
    print("(A) module hints:", get_type_hints(get_module_ticket))

    # (B) Local type — NameError.
    try:
        local_fn = make_local()
        get_type_hints(local_fn)
    except NameError as exc:
        print("(B) NameError:", exc)

    # (C) Factory-local Depends — NameError.
    try:
        route_fn = make_depends_factory()
        get_type_hints(route_fn)
    except NameError as exc:
        print("(C) NameError:", exc)

    # (D) Annotated metadata stripped by default.
    print("(D) default hints:", get_type_hints(plain_route))
    print("(D) include_extras hints:", get_type_hints(plain_route, include_extras=True))
```

The (A) case resolves to `{"id": int, "return": ModuleTicket}`. The (B) case raises `NameError: name 'LocalTicket' is not defined`. The (C) case raises `NameError: name 'get_db' is not defined`. The (D) case shows the bare `int` (default) and the `Annotated[int, 'meta']` (with `include_extras`).

**Why is the (D) failure silent rather than a `NameError`?**

Because the failure is not a name-resolution failure — it is a *metadata-loss* failure. The `eval` of `'Annotated[int, "meta"]'` succeeds (both `Annotated` and `int` are in the module globals, and `"meta"` is a literal). The result is an `Annotated[int, "meta"]` object. But then `get_type_hints`'s default behaviour *strips* the `Annotated` wrapper and returns the bare `int`. The metadata is silently gone. This is the most insidious of the four failures because no exception is raised — the metadata just disappears, and the caller's downstream logic (FastAPI's `Depends` injection) silently does not fire.

## Execution Trace

```bash
$ python boardly/typing_demo/annotation_failures.py
(A) module hints: {'id': <class 'int'>, 'return': <class '__main__.ModuleTicket'>}
(B) NameError: name 'LocalTicket' is not defined
(C) NameError: name 'get_db' is not defined
(D) default hints: {'x': <class 'int'>, 'return': <class 'NoneType'>}
(D) include_extras hints: {'x': typing.Annotated[int, 'meta'], 'return': <class 'NoneType'>}
```

The (A) case resolves cleanly — the `return` key shows `ModuleTicket` resolved from the module's globals. (B) and (C) raise `NameError` — `LocalTicket` and `get_db` are local names not in `func.__globals__`. (D) shows the stripping — `int` (default) vs `Annotated[int, 'meta']` (with `include_extras`). The `return: NoneType` entry in (D) comes from `plain_route`'s explicit `-> None` annotation.

## Common Mistakes

### Mistake 1: Local types in annotations

```python
from __future__ import annotations

def make():
    class LocalTicket: ...
    def route(id: int) -> LocalTicket: ...
    return route

route = make()
get_type_hints(route)  # NameError: name 'LocalTicket' is not defined
```

**Symptom:** `NameError` from `get_type_hints()`.
**Why:** `LocalTicket` is a local in `make`'s frame; `route.__globals__` (the module globals) does not include it.
**Fix:** Move `LocalTicket` to module level, or pass `localns={"LocalTicket": LocalTicket}` to `get_type_hints()`. PEP 649 (3.14) eliminates this failure by capturing the original scope.

### Mistake 2: `Depends` target in a factory

```python
from __future__ import annotations
from typing import Annotated
from fastapi import Depends

def make_app():
    def get_db(): ...
    @app.post("/x")
    def route(db: Annotated[str, Depends(get_db)]): ...
    return app
```

**Symptom:** FastAPI raises `NameError: name 'get_db' is not defined` at request time, when it calls `get_type_hints(route, include_extras=True)`.
**Why:** `get_db` is a local in `make_app`; `route.__globals__` does not include it.
**Fix:** Define `get_db` at module level. Or (rare) pass `localns` manually — but FastAPI does not expose this hook.

### Mistake 3: Forgetting `include_extras=True`

```python
hints = get_type_hints(route)  # default
# hints["db"] is `str`, not `Annotated[str, Depends(get_db)]`
```

**Symptom:** FastAPI dependency injection does not fire — the `db` parameter is treated as a plain query parameter.
**Why:** `get_type_hints()` without `include_extras=True` strips `Annotated` metadata.
**Fix:** Always pass `include_extras=True` when resolving annotations for dependency injection or validation. (FastAPI does this internally; the mistake is in user code that calls `get_type_hints` directly.)

## Engineering Trade-Offs

**Decision:** In `boardly`, every name referenced in an annotation must be importable from the module's globals (or passed via `localns` explicitly). `Depends` targets are module-level. Local types are not used in annotations. `get_type_hints(obj, include_extras=True)` is the only call form.
**Both sides:** The alternative is to wrap every factory in a closure-aware resolution layer — pass `localns` derived from `func.__closure__`. This works in principle but is fragile (cells do not have stable names) and not supported by FastAPI. The clean path is "module-level names only" — the convention the Python community has converged on.
**Commitment:** In `boardly`, the lint rule `boardly-module-level-annotations` flags any annotation that references a name not in the module's globals. The convention is enforced. When `boardly` upgrades to 3.14, the rule will be relaxed — PEP 649 lifts the restriction.

## Exercises

1. **Exercise 1 — Reproduce the (B) failure.** Run the file. Confirm the `NameError` from `get_type_hints(local_fn)`. Read the traceback and find the failing name. `Verify: python boardly/typing_demo/annotation_failures.py`
2. **Exercise 2 — `localns` workaround.** Modify the (B) case to pass `localns={"LocalTicket": LocalTicket}` to `get_type_hints()`. (You will need to expose `LocalTicket` from `make_local`.) Verify the resolution succeeds. `Verify: python boardly/typing_demo/annotation_failures.py`
3. **Exercise 3 — `include_extras` flag.** Run the (D) case. Confirm `get_type_hints(plain_route)` returns `int` and `get_type_hints(plain_route, include_extras=True)` returns `Annotated[int, 'meta']`. `Verify: python boardly/typing_demo/annotation_failures.py`
4. **Exercise 4 — Module-level `Depends`.** Move `get_db` to module level in the (C) case. Verify `get_type_hints(route_fn, include_extras=True)` resolves. `Verify: python boardly/typing_demo/annotation_failures.py`
5. **Exercise 5 — Predict the 3.14 behaviour.** For each of the four failure modes, predict whether PEP 649 (3.14) eliminates, mitigates, or leaves the failure. (Hint: PEP 649 evaluates in the original scope, so local types and factory-local `Depends` resolve; `include_extras` is still required for `Annotated` metadata preservation.) `Verify: open https://peps.python.org/pep-0649/ in a browser`

## Verification

```bash
$ python boardly/typing_demo/annotation_failures.py
(A) module hints: {'id': <class 'int'>, 'return': <class '__main__.ModuleTicket'>}
(B) NameError: name 'LocalTicket' is not defined
(C) NameError: name 'get_db' is not defined
(D) default hints: {'x': <class 'int'>, 'return': <class 'NoneType'>}
(D) include_extras hints: {'x': typing.Annotated[int, 'meta'], 'return': <class 'NoneType'>}
```

## Previously Learned Here

- [[13-future/01-from-future-import-annotations]] — the string-storage behaviour that causes every failure in this lesson.
- [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] — the 3.14 fix path; PEP 649 eliminates failures (B) and (C) by capturing the original scope.
- [[01-typing/02-Annotated-and-Metadata]] — the `Annotated` primitive and the `include_extras` flag.

## What's Next

You have finished Section 13. The next section is [[14-importlib/00-importlib-MOC]] — `import_module`, `resources`, `metadata`, `reload`. But if you came here from a FastAPI debugging session, the natural next stop is [[10-inspect/00-inspect-MOC]] — `inspect.signature` is what FastAPI calls to read a route's parameters, and the `inspect` + `get_type_hints` combination is the second half of the FastAPI resolution path. Three things to take with you:

- PEP 563's string-storage causes four failure modes: `NameError` on local types, `NameError` on factory-local `Depends`, `Annotated` metadata stripping, and the silent metadata-loss (no exception, just metadata gone).
- The `localns`/`globalns` workaround exists but is fragile; the robust path is "module-level names only".
- PEP 649 (3.14) eliminates the local-type and factory-local `Depends` failures by capturing the original scope; the `include_extras` requirement stays.

## Sources

- **`typing.get_type_hints`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical reference, including the `globalns`/`localns`/`include_extras` parameters.
- **`typing.ForwardRef`** — https://docs.python.org/3/library/typing.html#typing.ForwardRef — accessed 2026-10-23 — the internal class that wraps and resolves annotation strings; the `_evaluate` method is the failure point.
- **PEP 563 — Postponed evaluation of annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the "Resolving Type Hints at Runtime" section documents the `get_type_hints` path.
- **PEP 649 — Deferred evaluation of annotations** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the 3.14 fix path; the "Behavioral differences" section compares to PEP 563.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the `Annotated` PEP; the `include_extras` rationale.
- **FastAPI — Dependencies with `Annotated`** — https://fastapi.tiangolo.com/python-types/ — accessed 2026-10-23 — the FastAPI pattern that depends on `include_extras=True`.

## What We Learned

- You can diagnose the `NameError` from `get_type_hints()` — read the traceback, find the missing name, apply the `localns`/`globalns` workaround.
- You can explain the "no local types in annotations" rule and the two valid workarounds.
- You can trace the FastAPI `Annotated[int, Depends(...)]` resolution path — why `Depends` must be importable from `func.__globals__`.
- You can reason about the `include_extras=True` requirement and why FastAPI always passes it.
- You can predict the 3.14 fix path — which of the four failures PEP 649 eliminates, which it leaves alone.
