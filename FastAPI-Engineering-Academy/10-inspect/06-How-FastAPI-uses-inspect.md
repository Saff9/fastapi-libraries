---
title: "Lesson 06: How FastAPI uses inspect"
aliases:
 - FastAPI dependency resolution
 - inspect.signature in FastAPI
 - get_type_hints include_extras in FastAPI
 - Annotated Depends resolution
 - solve_dependencies
 - call_with_dependencies
tags:
 - inspect
 - typing
 - fastapi-internals
 - dependency-injection
 - canonical
 - python-stdlib
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "50–65 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[10-inspect/02-get_type_hints]]"
 - "[[10-inspect/03-iscoroutinefunction]]"
 - "[[10-inspect/04-Parameter-kinds]]"
 - "[[10-inspect/05-BoundArguments-and-bind]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
related_lessons:
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[10-inspect/02-get_type_hints]]"
 - "[[10-inspect/05-BoundArguments-and-bind]]"
first_taught_in: "10-inspect/06-How-FastAPI-uses-inspect"
---

# Lesson 06: How FastAPI uses inspect

*How `boardly`'s 50-line `solve_dependencies`/`call_with_dependencies` re-implements FastAPI's actual call chain — `inspect.signature(route.endpoint)` → `typing.get_type_hints(..., include_extras=True)` → for each `Annotated[T, Depends(...)]` parameter, recurse into the dependency sub-tree — and arrives at the same resolved-kwargs shape FastAPI hands to your route.*

**You're at the very beginning of Section 10 — the capstone.**

You have spent five lessons assembling the parts: `inspect.signature` reads parameter shape, `typing.get_type_hints(..., include_extras=True)` reads resolved annotations with `Annotated` metadata intact, `iscoroutinefunction` decides sync-vs-async dispatch, the five `Parameter.kind` values drive `bind`'s routing, and `BoundArguments.arguments` is the writable dict where you inject resolved dependencies. Today you put them together. By the end of this lesson, you will have a 50-line re-implementation of FastAPI's dependency resolution that produces the exact kwargs FastAPI hands to your `Annotated[Session, Depends(get_session)]` route. This is the lesson the section was built for. Take your time. **This is how you learn.**

#inspect #typing #fastapi-internals #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **State FastAPI's call chain from memory** — `inspect.signature(route.endpoint)` → `typing.get_type_hints(..., include_extras=True)` → walk `sig.parameters` → for each `Annotated[T, Depends(...)]` parameter, recurse into the dependency sub-tree → `bind_partial` + `apply_defaults` + `f(*bound.args, **bound.kwargs)`.
2. **Implement a `Depends` marker** — a small class that holds a dependency callable, placed in the metadata slot of `Annotated[T, Depends(...)]`.
3. **Implement `solve_dependencies(call, request)`** — walk the signature, route request-data params first, fall back to `Annotated[T, Depends(...)]` resolution, recurse into sub-trees.
4. **Implement `call_with_dependencies(call, resolved)`** — `bind_partial(resolved)`, `apply_defaults`, splat `bound.args`/`bound.kwargs`.
5. **Explain why `include_extras=True` is non-negotiable** — without it, `Annotated[T, Depends(...)]` is stripped to `T` and the dependency marker is gone; FastAPI cannot find the `Depends` without it.
6. **Explain the recursion** — a dependency itself has a signature, which itself may contain `Annotated[T, Depends(...)]` parameters, so `solve_dependencies` is called recursively until a sub-dependency has no further dependencies.

## Prerequisites

Before starting, you need:

- **Lessons 01–05 of this section** — `signature`, `Parameter`, `get_type_hints`, `iscoroutinefunction`, the five kinds, `BoundArguments`, `bind`, `bind_partial`, `apply_defaults`. This lesson uses every one of them.
- **`Annotated` basics** — [[01-typing/02-Annotated-and-Metadata]] for the metadata slot semantics.
- **About 50–65 minutes of focused time.**

**The most common gap: thinking FastAPI's DI is magic.** It is not. FastAPI's dependency resolution is `inspect.signature` + `get_type_hints(include_extras=True)` + a recursive walk that matches `Annotated[T, Depends(...)]` metadata. That is the whole machine. Once you see the 50-line re-implementation, the magic evaporates and what is left is a pattern you can replicate, extend, or replace.

## The Problem

Here is the bug. `boardly` had this route:

```python
# boardly/routes/tickets.py — the route as written
from typing import Annotated
from boardly.deps import Depends, get_db_session, get_current_user

def create_ticket(
    title: str,
    session: Annotated[str, Depends(get_db_session)],
    user: Annotated[str, Depends(get_current_user)],
    priority: int = 1,
) -> dict:
    return {"title": title, "session": session, "user": user, "priority": priority}
```

The route declares two dependencies (`session`, `user`) via `Annotated[T, Depends(...)]` markers, plus a request-data parameter (`title`) and a defaulted parameter (`priority`). The handler code that *calls* `create_ticket` has to:

1. Read the signature of `create_ticket`.
2. Resolve every annotation to its real form (handling `from __future__ import annotations` if present).
3. For each parameter, decide whether the value comes from (a) the request, (b) a `Depends(...)` marker, or (c) the function's default.
4. For (b), recursively do the same to the dependency callable, since it may itself have `Depends` markers.
5. Build the final kwargs, bind them to the signature, apply defaults, call.

That is exactly what FastAPI does, in that order, on every request to every route. The route function never knows it happened — it just receives `title`, `session`, `user`, `priority` as ordinary parameters. The "magic" is `inspect` + `typing` + recursion.

The bug that motivates this lesson is "I want to know exactly what FastAPI does when it sees `Annotated[str, Depends(get_db_session)]`." The fix is to write it yourself, in 50 lines, and confirm it produces the same kwargs FastAPI does.

## The Code

```python
# boardly/di.py
"""A 50-line re-implementation of FastAPI's dependency resolution via inspect."""
import inspect
from typing import Annotated, Any, Callable, get_type_hints, get_origin, get_args


# 1. The Depends marker — placed in Annotated metadata: Annotated[T, Depends(dep)]
class Depends:
    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency

    def __repr__(self) -> str:
        return f"Depends({self.dependency.__name__})"


# 2. solve_dependencies — walk the signature, route request data, recurse on Depends
def solve_dependencies(
    call: Callable[..., Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    """Return the resolved kwargs for `call`: request data + recursively-resolved Depends values."""
    signature = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)   # keeps Annotated metadata
    resolved: dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name in request:
            resolved[name] = request[name]              # request data wins
            continue
        hint = hints.get(name, param.annotation)         # resolved annotation
        if get_origin(hint) is Annotated:                # Annotated[T, ...]?
            for meta in get_args(hint)[1:]:              # [1:] skips the underlying type
                if isinstance(meta, Depends):
                    # Recursively solve the sub-dependency, then call it.
                    sub_resolved = solve_dependencies(meta.dependency, {})
                    resolved[name] = call_with_dependencies(meta.dependency, sub_resolved)
                    break
    return resolved


# 3. call_with_dependencies — bind, apply defaults, call
def call_with_dependencies(
    call: Callable[..., Any],
    resolved: dict[str, Any],
) -> Any:
    """Bind `resolved` against `call`, apply defaults, call."""
    signature = inspect.signature(call)
    bound = signature.bind_partial(**resolved)
    bound.apply_defaults()
    return call(*bound.args, **bound.kwargs)


# 4. boardly dependencies under inspection — a 3-level sub-tree
def get_settings() -> dict:
    return {"db_url": "sqlite:///boardly.db"}

def get_db_session(
    settings: Annotated[dict, Depends(get_settings)],
) -> str:
    return f"session:{settings['db_url']}"

def get_current_user() -> str:
    return "alice"

def create_ticket(
    title: str,
    session: Annotated[str, Depends(get_db_session)],
    user: Annotated[str, Depends(get_current_user)],
    priority: int = 1,
) -> dict:
    return {"title": title, "session": session, "user": user, "priority": priority}


# 5. Run the chain — FastAPI in miniature
if __name__ == "__main__":
    request_data = {"title": "API broken"}
    print("--- solve_dependencies(create_ticket, {'title': 'API broken'}) ---")
    resolved = solve_dependencies(create_ticket, request_data)
    print(f"  resolved: {resolved}")

    print("\n--- call_with_dependencies(create_ticket, resolved) ---")
    result = call_with_dependencies(create_ticket, resolved)
    print(f"  result:   {result}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 5–11: The `Depends` marker

```python
class Depends:
    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency

    def __repr__(self) -> str:
        return f"Depends({self.dependency.__name__})"
```

`Depends` is a tiny marker class. It holds a single callable (`dependency`) and prints nicely. The class has no behaviour beyond storing the dependency — no `__call__`, no special method. It is a *tag* placed in the `Annotated` metadata slot, not a callable itself.

In real FastAPI, `Depends` is more sophisticated (it supports `use_cache=True` for singleton resolution, it can take a yield-generator for resource cleanup, etc.), but the core shape is identical: a marker that says "this parameter is resolved by calling this other callable."

**Why a class and not a function returning a marker?** Because `Depends(get_db_session)` is *not* calling `get_db_session` — it is storing a reference to it. A function-style marker (`def Depends(d): return _Marker(d)`) is functionally identical; FastAPI chose a class because the `__init__` is self-documenting and the marker carries attributes. The class shape also lets FastAPI extend the marker later (`Depends(get_db, use_cache=True)`) without breaking callers.

**Why `__name__` in the `__repr__`?** For debugging. When the dep tree prints in a stack trace, you see `Depends(get_db_session)`, not `Depends(<function 0x7f...>)`. The route registration log depends on this.

### Lines 14–32: `solve_dependencies` — the recursive walk

```python
def solve_dependencies(
    call: Callable[..., Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    """Return the resolved kwargs for `call`: request data + recursively-resolved Depends values."""
    signature = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)   # keeps Annotated metadata
    resolved: dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name in request:
            resolved[name] = request[name]              # request data wins
            continue
        hint = hints.get(name, param.annotation)         # resolved annotation
        if get_origin(hint) is Annotated:                # Annotated[T, ...]?
            for meta in get_args(hint)[1:]:              # [1:] skips the underlying type
                if isinstance(meta, Depends):
                    # Recursively solve the sub-dependency, then call it.
                    sub_resolved = solve_dependencies(meta.dependency, {})
                    resolved[name] = call_with_dependencies(meta.dependency, sub_resolved)
                    break
    return resolved
```

This is the heart of FastAPI's DI. Walk it line by line:

- **Line `signature = inspect.signature(call)`** — read the parameter shape (lesson 01). Returns the `Signature` whose `.parameters` we walk next.
- **Line `hints = get_type_hints(call, include_extras=True)`** — resolve annotations (lesson 02). Crucially, `include_extras=True` keeps `Annotated[T, ...]` intact; without it, the `Depends` marker would be stripped to `T` and we could not find it.
- **Line `for name, param in signature.parameters.items():`** — iterate parameters in source order (lesson 04's order-preserving mappingproxy). Order matters because `bind_partial` will partition them by kind.
- **Line `if name in request: resolved[name] = request[name]; continue`** — request data wins. If the URL query string supplied `title=...`, we use that; we do not look for a `Depends` marker on `title`. This is FastAPI's "request data has priority" rule.
- **Line `hint = hints.get(name, param.annotation)`** — the resolved annotation for this parameter. Fall back to `param.annotation` if `get_type_hints` did not return the parameter (rare — happens only for parameters without annotations).
- **Line `if get_origin(hint) is Annotated:`** — the metadata-detection check (lesson 02). `get_origin(Annotated[int, "x"])` returns `Annotated`; `get_origin(int)` returns `None`. So this `is` check filters to only the `Annotated`-wrapped parameters.
- **Line `for meta in get_args(hint)[1:]:`** — walk the metadata. `get_args(Annotated[int, "x", Depends(...)])` returns `(int, "x", Depends(...))`. The `[1:]` skips the underlying type at index 0, leaving the metadata list — exactly what we scan for markers.
- **Line `if isinstance(meta, Depends):`** — find a `Depends` marker. There can be other metadata (e.g., `Annotated[int, Field(gt=0), Depends(get_int)]`); we look only for `Depends`.
- **Line `sub_resolved = solve_dependencies(meta.dependency, {})`** — **the recursion**. The sub-dependency (`get_db_session`) itself has a signature that may contain `Depends` markers. We call `solve_dependencies` recursively with an empty request dict (dependencies start with no request data — they are pure function-of-deps). This recursion terminates when a sub-dependency has no `Depends` markers; the loop body is skipped, and `solve_dependencies` returns an empty (or partial) dict.
- **Line `resolved[name] = call_with_dependencies(meta.dependency, sub_resolved)`** — actually call the sub-dependency, with its own resolved deps. The result is what we assign to `resolved[name]`.
- **Line `break`** — stop scanning metadata once we found a `Depends` (assume one marker per parameter; matches FastAPI's behaviour).

**Why `get_type_hints(..., include_extras=True)` and not `param.annotation`?** Because `param.annotation` is the raw form from `__annotations__`, which (under `from __future__ import annotations`) is the *string* `"Annotated[str, Depends(get_db_session)]"`. `get_type_hints` evaluates that string in the function's `__globals__` and returns the real `Annotated` object. Without `include_extras=True`, `get_type_hints` would strip `Annotated` to `str` — and `get_origin(str) is Annotated` is `False`, so the entire `if` block would be skipped and dependencies would never be found. This is the single most common bug in naive DI implementations.

**Why the recursion uses an empty request dict?** Because request data is per-endpoint. A sub-dependency like `get_db_session` does not have a request of its own — the request belongs to `create_ticket`. Sub-dependencies are pure function-of-deps. (In real FastAPI, sub-dependencies *can* declare `Request`-typed parameters to access the live request, but that is a separate annotation-driven mechanism, not part of the basic `Annotated[T, Depends(...)]` recursion.)

**Why `break` after the first `Depends`?** Because FastAPI's contract is one `Depends` per parameter. Multiple `Depends` markers on the same parameter would be ambiguous — which one resolves the value? FastAPI raises a validation error at route registration if it sees two. Our re-implementation silently picks the first; the `break` makes that choice visible.

### Lines 35–42: `call_with_dependencies` — bind, defaults, call

```python
def call_with_dependencies(
    call: Callable[..., Any],
    resolved: dict[str, Any],
) -> Any:
    """Bind `resolved` against `call`, apply defaults, call."""
    signature = inspect.signature(call)
    bound = signature.bind_partial(**resolved)
    bound.apply_defaults()
    return call(*bound.args, **bound.kwargs)
```

This is lesson 05's flow in three lines:

- **`bind_partial(**resolved)`** — bind the resolved kwargs leniently. `bind_partial` (not `bind`) because some defaulted parameters may be absent from `resolved` (e.g., `priority` was not in the request, not a `Depends`). `bind` would raise on the missing required-looking param; `bind_partial` lets `apply_defaults` fill it in.
- **`apply_defaults()`** — fill in the function's defaults: `priority=1` (explicit default), plus implicit `()`/`{}` for any variadic params.
- **`call(*bound.args, **bound.kwargs)`** — splat and call. The `args`/`kwargs` partition is recomputed from `.arguments` by the `Signature`'s kind-aware logic (lesson 04), so `POSITIONAL_ONLY`, `KEYWORD_ONLY`, `VAR_POSITIONAL`, `VAR_KEYWORD` all route correctly.

**Why is `call_with_dependencies` separate from `solve_dependencies`?** Because FastAPI separates them too: `get_dependant(route)` builds the dep tree once at registration time; the request handler walks the tree and calls each dep in order, then calls the endpoint. Our `solve_dependencies` walks the tree *and* calls each sub-dep as it goes (a simplification — real FastAPI precomputes the tree); the separation makes the structure visible. The recursion in `solve_dependencies` calls `call_with_dependencies` for each sub-dep; the top-level caller invokes `call_with_dependencies` once for the endpoint.

**Why not collapse them into one function?** Readability. The two-step structure mirrors the mental model: "first figure out what to call, then call it." A single function would entangle the recursion with the bind+call logic and obscure the boundary. The trade-off is a few extra lines of indirection; the win is a clear separation that survives refactoring.

### Lines 45–63: The `boardly` dependency tree under inspection

```python
def get_settings() -> dict:
    return {"db_url": "sqlite:///boardly.db"}

def get_db_session(
    settings: Annotated[dict, Depends(get_settings)],
) -> str:
    return f"session:{settings['db_url']}"

def get_current_user() -> str:
    return "alice"

def create_ticket(
    title: str,
    session: Annotated[str, Depends(get_db_session)],
    user: Annotated[str, Depends(get_current_user)],
    priority: int = 1,
) -> dict:
    return {"title": title, "session": session, "user": user, "priority": priority}
```

This is a deliberately three-level dependency tree:

- `create_ticket` (the endpoint) depends on `get_db_session` and `get_current_user`.
- `get_db_session` (a sub-dependency) depends on `get_settings`.
- `get_current_user` and `get_settings` are leaf dependencies — no further `Depends` markers.

The endpoint also has:

- `title: str` — a request-data parameter (no `Depends`). FastAPI would source this from the request body or query string; we source it from the `request` dict.
- `priority: int = 1` — a defaulted parameter. Not in `request`, not a `Depends`. `solve_dependencies` skips it; `apply_defaults` fills it in.

The recursion trace for `solve_dependencies(create_ticket, {"title": "API broken"})` is:

1. Walk `create_ticket`'s parameters.
2. `title` is in `request` → `resolved["title"] = "API broken"`.
3. `session` has `Annotated[str, Depends(get_db_session)]` → recurse into `get_db_session`:
   1. Walk `get_db_session`'s parameters.
   2. `settings` has `Annotated[dict, Depends(get_settings)]` → recurse into `get_settings`:
      1. `get_settings` has no parameters → `solve_dependencies` returns `{}`.
      2. `call_with_dependencies(get_settings, {})` → returns `{"db_url": "sqlite:///boardly.db"}`.
      3. `resolved["settings"] = {"db_url": "sqlite:///boardly.db"}`.
   3. `call_with_dependencies(get_db_session, {"settings": {...}})` → returns `"session:sqlite:///boardly.db"`.
   4. `resolved["session"] = "session:sqlite:///boardly.db"`.
4. `user` has `Annotated[str, Depends(get_current_user)]` → recurse into `get_current_user`:
   1. `get_current_user` has no parameters → `solve_dependencies` returns `{}`.
   2. `call_with_dependencies(get_current_user, {})` → returns `"alice"`.
   3. `resolved["user"] = "alice"`.
5. `priority` is not in `request`, has no `Annotated` annotation → skipped.
6. Return `resolved = {"title": "API broken", "session": "...", "user": "alice"}`.

The top-level `call_with_dependencies(create_ticket, resolved)` then `bind_partial`s, `apply_defaults` (fills `priority=1`), and calls.

### Lines 66–73: The run

```python
if __name__ == "__main__":
    request_data = {"title": "API broken"}
    print("--- solve_dependencies(create_ticket, {'title': 'API broken'}) ---")
    resolved = solve_dependencies(create_ticket, request_data)
    print(f"  resolved: {resolved}")

    print("\n--- call_with_dependencies(create_ticket, resolved) ---")
    result = call_with_dependencies(create_ticket, resolved)
    print(f"  result:   {result}")
```

This is the entry point. The `request_data` simulates what FastAPI would extract from the HTTP request — in this case, a body parameter `title`. In real FastAPI, the request dict would also contain path params, query params, cookies, headers — each filtered to match the parameter names declared on `create_ticket`.

The output (see Execution Trace) shows `resolved` containing the three resolved values, and `result` containing the function's return value with `priority=1` filled in by `apply_defaults`.

## Execution Trace

```bash
$ python boardly/di.py
--- solve_dependencies(create_ticket, {'title': 'API broken'}) ---
  resolved: {'title': 'API broken', 'session': 'session:sqlite:///boardly.db', 'user': 'alice'}

--- call_with_dependencies(create_ticket, resolved) ---
  result:   {'title': 'API broken', 'session': 'session:sqlite:///boardly.db', 'user': 'alice', 'priority': 1}
```

Three observations from the trace:

1. `resolved` has exactly three entries: `title` (request), `session` (sub-tree recursion through `get_db_session` → `get_settings`), `user` (leaf dependency). `priority` is *not* in `resolved` — `solve_dependencies` skipped it because it has no request data and no `Depends` marker.
2. `result` has four entries: the three from `resolved` plus `priority=1`, filled in by `apply_defaults` in `call_with_dependencies`. The function received a complete, validated argument set.
3. The sub-tree recursion worked: `session` is `"session:sqlite:///boardly.db"`, which is the result of calling `get_db_session` with its own dependency (`settings`) resolved. The recursion went two levels deep (`create_ticket` → `get_db_session` → `get_settings`).

## Common Mistakes

### Mistake 1: Forgetting `include_extras=True`

```python
hints = get_type_hints(call)   # default include_extras=False — strips Annotated!
hint = hints.get("session")    # just <class 'str'>, the Annotated wrapper is gone
get_origin(hint) is Annotated  # False
```

**Symptom:** `solve_dependencies` returns an empty dict (or only request-data entries). Dependencies are silently never resolved.
**Why:** `get_type_hints` defaults to `include_extras=False`, which strips `Annotated[T, ...]` to `T` for backward compatibility. Without the `Annotated` wrapper, `get_origin(hint)` is `None`, not `Annotated`, so the `if` block is skipped. The `Depends` marker is gone — there is no way to find it.
**Fix:** Always pass `include_extras=True` when you need to read `Annotated` metadata. This is the single most common bug in naive DI implementations. FastAPI's source uses `get_type_hints(call, include_extras=True)` everywhere it reads dependency metadata.

### Mistake 2: Reading `param.annotation` instead of `hints[name]`

```python
for name, param in signature.parameters.items():
    hint = param.annotation    # the RAW form, may be a string under PEP 563
    if get_origin(hint) is Annotated:   # always False if hint is a string
        ...
```

**Symptom:** Under `from __future__ import annotations`, the `Annotated` block is never entered. Dependencies are silently not resolved.
**Why:** `param.annotation` is whatever is in `__annotations__`. Under PEP 563 (`from __future__ import annotations`), every annotation is stored as a string. So `param.annotation` is the string `"Annotated[str, Depends(get_db_session)]"`, not the `Annotated` object. `get_origin(str)` is `None`, so the `if` is `False`. Lesson 02 covers this in depth.
**Fix:** Use `hints = get_type_hints(call, include_extras=True); hint = hints.get(name, param.annotation)`. `get_type_hints` evaluates the strings in the function's `__globals__` and returns the real `Annotated` object.

### Mistake 3: Mutating the dep cache mid-recursion

```python
def solve_dependencies(call, request, cache=None):
    if cache is None:
        cache = {}
    if call in cache:
        return cache[call]
    ...
    cache[call] = resolved    # write before recursion completes
    for name, ... in ...:
        sub = solve_dependencies(meta.dependency, {}, cache=cache)   # recursion sees the partial cache
```

**Symptom:** Subtle wrong values in dependency results when two sub-dependencies share a common ancestor. The cache returns a partially-built resolved dict instead of the final one.
**Why:** Writing to the cache *before* the recursion completes means a recursive call can observe a half-built entry. FastAPI's real cache writes *after* the recursion returns. The pattern is "compute, then cache" — never "cache, then compute."
**Fix:** Compute `resolved` fully, *then* write to the cache. The pattern:

```python
def solve_dependencies(call, request, cache=None):
    if cache is None:
        cache = {}
    if call in cache:
        return cache[call]
    resolved = {}   # compute fully
    for name, param in ...:
        ...
    cache[call] = resolved   # write *after* the loop, not inside it
    return resolved
```

This lesson's re-implementation omits the cache for simplicity (each dependency is resolved fresh on every call — `use_cache=False` semantics in FastAPI). Adding a cache is exercise 5.

## Engineering Trade-Offs

**Decision:** Re-implement FastAPI's DI as a 50-line `solve_dependencies` + `call_with_dependencies` pair, using `inspect.signature` + `get_type_hints(..., include_extras=True)` + recursion. Do not depend on FastAPI for the dependency-resolution core.
**Both sides:** The alternative is to depend on FastAPI's `fastapi.dependencies.utils.get_dependant` directly. That gives you FastAPI's exact behaviour (caching, `yield`-generator cleanup, `Request`/`Response` injection, sync-vs-async dispatch) for free. The trade-off is a heavyweight dependency: `fastapi` pulls in `pydantic`, `starlette`, `anyio`, and a few thousand lines of code paths you do not need for a CLI tool or library. For `boardly`'s teaching scope — showing *how* the DI works — the 50-line re-implementation wins. For a production service that already runs FastAPI, use FastAPI's `get_dependant` directly.
**Commitment:** `boardly` ships the 50-line `boardly/di.py` shown here. It is enough to resolve `Annotated[T, Depends(...)]` sub-trees of arbitrary depth, with request-data priority and default filling. The lesson explicitly *does not* implement: (a) dependency caching (exercise 5), (b) `yield`-generator cleanup (a `contextlib` concern), (c) sync-vs-async dispatch (lesson 03 covers the `iscoroutinefunction` check; the integration is left to the student). Each gap is a deliberate simplification that maps to a FastAPI feature the student now has the tools to understand.

## Exercises

1. **Exercise 1 — Run the example.** Save the code block as `boardly/di.py` and run it. Confirm the output matches the Execution Trace exactly. Modify `request_data` to include `priority=5` and confirm the result's `priority` is `5` (request data overrides the function's default). `Verify: python boardly/di.py`
2. **Exercise 2 — Drop `include_extras`.** Change `get_type_hints(call, include_extras=True)` to `get_type_hints(call)` (the default). Re-run. Confirm `resolved` no longer contains `session` or `user` — the `Annotated` metadata was stripped. Restore `include_extras=True`. `Verify: python -c "import boardly.di as d; d.solve_dependencies(d.create_ticket, {'title':'x'})"`
3. **Exercise 3 — Add a `Request` parameter.** Extend `create_ticket` to take `request: Annotated[dict, Depends(get_request)]` where `get_request()` returns a fake request object. Confirm `solve_dependencies` resolves it. (Hint: you need to register `get_request` and add it as a `Depends`.) `Verify: python -c "import boardly.di as d; print(d.call_with_dependencies(d.create_ticket, d.solve_dependencies(d.create_ticket, {'title':'x'})))"`
4. **Exercise 4 — Sync-vs-async dispatch.** Add `import inspect; print(inspect.iscoroutinefunction(create_ticket))` and confirm it is `False`. Convert `create_ticket` to `async def` and confirm it becomes `True`. Discuss (in a comment) where in `call_with_dependencies` you would branch on this to `await` the call. `Verify: python -c "import inspect; async def f(): pass; print(inspect.iscoroutinefunction(f))"`
5. **Exercise 5 — Add a dependency cache.** Extend `solve_dependencies` to accept a `cache: dict | None = None` argument. After computing `resolved` for a given `call`, write `cache[call] = resolved`. Before computing, check `if call in cache: return cache[call]`. Test with a `boardly` route where two parameters share the same `Depends(get_settings)` — confirm `get_settings` is called once, not twice. `Verify: python -c "import boardly.di as d; cache={}; d.solve_dependencies(d.create_ticket, {'title':'x'}, cache=cache); print('cache size:', len(cache))"`

## Verification

```bash
$ python boardly/di.py | head -4
--- solve_dependencies(create_ticket, {'title': 'API broken'}) ---
  resolved: {'title': 'API broken', 'session': 'session:sqlite:///boardly.db', 'user': 'alice'}

--- call_with_dependencies(create_ticket, resolved) ---
$ python -c "import boardly.di as d; r=d.solve_dependencies(d.create_ticket, {'title':'x'}); print(sorted(r.keys()))"
['session', 'title', 'user']
$ python -c "from typing import Annotated, get_type_hints, get_origin; def f(x: Annotated[int,'m']): pass; h=get_type_hints(f, include_extras=True)['x']; print(get_origin(h) is Annotated)"
True
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`. This lesson's `solve_dependencies` opens with `signature = inspect.signature(call)` — the call from lesson 01.
- [[10-inspect/02-get_type_hints]] — `get_type_hints(..., include_extras=True)`, the `Annotated` read path. This lesson's `hints = get_type_hints(call, include_extras=True)` is the call from lesson 02.
- [[10-inspect/03-iscoroutinefunction]] — `iscoroutinefunction` for sync-vs-async dispatch. Exercise 4 integrates the lesson 03 check.
- [[10-inspect/04-Parameter-kinds]] — the five `Parameter.kind` values that drive `bind`'s arg routing. The `call_with_dependencies` function relies on kind-aware bind to partition `args`/`kwargs`.
- [[10-inspect/05-BoundArguments-and-bind]] — `bind_partial`, `apply_defaults`, `bound.arguments` mutation. This lesson's `call_with_dependencies` is exactly the section 7 of lesson 05.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated[T, metadata]` itself, without which `Depends` markers have no home.

## What's Next

You have completed Section 10. The inspect section ends here. The next section you should walk depends on your track:

- **Async track** — [[21-asyncio-primitives/00-asyncio-MOC]] — you saw `iscoroutinefunction` decide sync-vs-async in lesson 03; now learn what the event loop actually does when FastAPI hands it a coroutine.
- **Pydantic track** — [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — FastAPI uses Pydantic to validate request bodies before they reach your route. This lesson's `request` dict is a stand-in; the real FastAPI flow extracts request data via Pydantic models.
- **FastAPI internals track** — re-read this lesson with the Starlette `Request` docs (https://www.starlette.io/requests/) open alongside. The `request` dict in `solve_dependencies` is what FastAPI's `Request` object supplies in production.

Three things to do before moving on:

- Re-run `python boardly/di.py` and confirm the output matches the Execution Trace.
- Modify `request_data` to omit `title` — confirm `solve_dependencies` returns `{}` for `title` and `call_with_dependencies` raises `TypeError` (because `title` is required and has no default).
- Add a fourth `Depends` parameter to `create_ticket` and trace the recursion by hand on paper before running it. Confirm your trace matches the actual recursion.

Take your time. **This is how you learn.**

## Sources

- **Python `inspect` module documentation** — https://docs.python.org/3/library/inspect.html — accessed 2026-10-23 — the source-of-truth API reference for `signature`, `Parameter`, `BoundArguments`, `bind`, `bind_partial`, `apply_defaults`, and `iscoroutinefunction`. Every call in this lesson's 50-line re-implementation is documented here.
- **Python `typing` module documentation — `get_type_hints`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical reference for the `include_extras` flag and the `"return"` key convention. The flag is the single most important parameter in this lesson's chain.
- **Python `typing` module documentation — `Annotated`, `get_origin`, `get_args`** — https://docs.python.org/3/library/typing.html#typing.Annotated — accessed 2026-10-23 — the metadata-slot semantics that make `Annotated[T, Depends(...)]` work. `get_origin`/`get_args` are the read path for the metadata.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the PEP that introduced `Annotated`. Read the "Use Cases" section for the dependency-injection motivation that FastAPI implements.
- **PEP 362 — Function Signature Object** — https://peps.python.org/pep-0362/ — accessed 2026-10-23 — the PEP that introduced `inspect.signature` and `BoundArguments` in Python 3.3. The "BoundArguments" section documents the `.arguments`-as-source-of-truth design that this lesson's `call_with_dependencies` relies on.

## What We Learned

- You can now state FastAPI's call chain from memory: `inspect.signature(route.endpoint)` → `get_type_hints(..., include_extras=True)` → walk parameters → for each `Annotated[T, Depends(...)]`, recurse into the sub-tree → `bind_partial` + `apply_defaults` + `f(*bound.args, **bound.kwargs)`.
- You can now implement a `Depends` marker class and place it in `Annotated` metadata slots.
- You can now implement `solve_dependencies(call, request)` that walks the signature, prioritises request data, and recursively resolves `Depends` sub-trees.
- You can now implement `call_with_dependencies(call, resolved)` that does `bind_partial` → `apply_defaults` → call, using `bound.args`/`bound.kwargs` to splat into the function.
- You can now explain why `include_extras=True` is non-negotiable — without it, `Annotated` is stripped and `Depends` markers are invisible.
- You can now explain the recursion — sub-dependencies themselves have signatures that may contain `Depends` markers, so `solve_dependencies` is called recursively until a sub-dependency has no further dependencies.
