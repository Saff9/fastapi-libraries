---
title: "inspect: Section Map of Content"
aliases:
 - inspect MOC
 - Section 10 Map of Content
tags:
 - inspect
 - moc
 - section-index
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "180–240 minutes"
---

# inspect: Section Map of Content

This is the module FastAPI uses to read your dependency signatures.

*The standard-library module that turns a Python function into data — `Signature`, `Parameter`, `BoundArguments` — the same module FastAPI leans on to read every `Annotated[int, Depends(get_db)]` you write, decide whether your route is sync or async, and figure out which dependencies to inject before each request.*

**You're at the very beginning of Section 10.**

This section teaches the `inspect` module — `inspect.signature`, `inspect.Parameter` (and its five `kind` values), `inspect.BoundArguments` (via `Signature.bind`), `typing.get_type_hints` (the partner call FastAPI makes alongside `inspect.signature` to read `Annotated` metadata), and `inspect.iscoroutinefunction` (the call FastAPI uses to decide sync-vs-async routing) — by re-implementing FastAPI's dependency resolution in miniature. By the end you will know exactly what FastAPI does when it sees `Annotated[int, Depends(get_db)]` in your route signature, and you will be able to write your own DI framework with the same primitives.

#inspect #section-moc

## What's in this section

Seven lessons, one growing application, three canonical concepts. Read them in order — each lesson assumes the previous one.

| # | Lesson | What it teaches | Time |
|---|--------|------------------|------|
| 01 | [[10-inspect/01-signature-and-Parameter]] | `inspect.signature(fun)`, the `Signature` object, `Parameter` (`.kind`, `.name`, `.default`, `.annotation`), the five `Parameter.kind` values (`POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD`), the `Parameter.empty` sentinel. | 30–40 min |
| 02 | [[10-inspect/02-get_type_hints]] | `typing.get_type_hints(obj, globalns, localns, include_extras=False)`, why it lives in `typing` and not `inspect`, the `from __future__ import annotations` interaction, `include_extras=True` (the call FastAPI uses to keep `Annotated` metadata). | 35–45 min |
| 03 | [[10-inspect/03-iscoroutinefunction]] | `inspect.iscoroutinefunction(fun)`, the difference between a true coroutine and a marked one, `inspect.ismarkedcoroutinefunction` (Python 3.13+ — version-gated), why FastAPI uses this to decide sync-vs-async routing. | 25–35 min |
| 04 | [[10-inspect/04-Parameter-kinds]] | The five `Parameter.kind` values deep-dive, how `inspect.signature` orders them in `sig.parameters`, the rules each kind enforces on `Signature.bind()`. | 30–40 min |
| 05 | [[10-inspect/05-BoundArguments-and-bind]] | `sig.bind(*args, **kwargs)`, `BoundArguments` (`.arguments`, `.args`, `.kwargs`), `sig.bind_partial()`, `apply_defaults()`, how FastAPI calls `bind` to figure out which dependencies to inject. | 35–45 min |
| 06 | [[10-inspect/06-How-FastAPI-uses-inspect]] | **The senior deep-dive.** The actual call chain: `inspect.signature(route.endpoint)` → `typing.get_type_hints(..., include_extras=True)` → for each `Annotated[T, Depends(...)]` param, resolve the dependency sub-tree. A minimal re-implementation of FastAPI's dependency resolution. | 50–65 min |

**Total estimated time:** 3–4 hours of focused reading and typing.

## The canonical concepts registered here

Three lessons in this section are the canonical introduction for concepts registered in [[00-Start-Here/Concept-Registry]]:

- **`inspect.signature` and `Parameter`** — canonical lesson: [[10-inspect/01-signature-and-Parameter]] (`first_taught_in: "10-inspect/01-signature-and-Parameter"`). The two classes that turn a callable into data.
- **`typing.get_type_hints` with `include_extras=True`** — canonical lesson: [[10-inspect/02-get_type_hints]] (`first_taught_in: "10-inspect/02-get_type_hints"`). The call that resolves string annotations and keeps `Annotated` metadata — the read path FastAPI uses.
- **How FastAPI uses `inspect` (the dependency-resolution chain)** — canonical lesson: [[10-inspect/06-How-FastAPI-uses-inspect]] (`first_taught_in: "10-inspect/06-How-FastAPI-uses-inspect"`). The senior deep-dive that ties the section together.

If you only have time for three lessons, do those three.

## The boardly code that threads through

Every lesson in this section writes to the same `boardly/di.py` module — a tiny re-implementation of FastAPI's dependency injection. By the end of the section, that file contains:

```python
# boardly/di.py — a 50-line re-implementation of FastAPI's DI
import inspect
from typing import Annotated, get_type_hints, get_origin, get_args, Any, Callable

class Depends:
    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency

def get_dependant(call: Callable[..., Any]) -> dict:
    """Inspect a callable's signature and return its dependency tree."""
    signature = inspect.signature(call, eval_str=True)
    hints = get_type_hints(call, include_extras=True)
    deps = []
    for name, param in signature.parameters.items():
        annotation = hints.get(name, param.annotation)
        if get_origin(annotation) is Annotated:
            for arg in get_args(annotation)[1:]:
                if isinstance(arg, Depends):
                    deps.append((name, arg.dependency))
    return {"call": call, "deps": deps}

def call_with_deps(call, deps_resolved):
    sig = inspect.signature(call)
    bound = sig.bind(**deps_resolved)
    bound.apply_defaults()
    return call(*bound.args, **bound.kwargs)
```

You will see this evolve lesson by lesson. By lesson 06, it resolves a real `boardly` route's dependency tree, mimicking FastAPI's behaviour for `Annotated[Session, Depends(get_session)]`.

## Prerequisites

Before starting Section 10, you should be comfortable with:

- **Type hints and `Annotated`** — `Annotated[int, "metadata"]` should be familiar. See [[01-typing/02-Annotated-and-Metadata]] for the canonical introduction. (This is the most important prerequisite — half of this section is about how FastAPI reads `Annotated` metadata.)
- **`from __future__ import annotations`** — basic familiarity with PEP 563 and string annotations. See [[13-future/01-from-future-import-annotations]] for the canonical deep-dive. (Lesson 02 spends a block on the interaction between string annotations and `get_type_hints`.)
- **Decorators and `functools.wraps`** — basic familiarity. Lesson 06's `inspect.unwrap` walks `functools.wraps`-decorated functions to find the original signature.

**The most common gap: confusing `inspect.signature` with `typing.get_type_hints`.** Students arrive thinking one is enough. They are not — `signature` reads the parameter *shape* (name, kind, default); `get_type_hints` reads the *annotations* (and resolves string forms, and keeps `Annotated` metadata when `include_extras=True`). FastAPI calls both, in sequence, to build the complete picture. Lesson 06 shows the actual call chain.

## How this section fits the course

This section is the *read side* of the FastAPI dependency-injection contract. The *write side* lives in:

- [[09-enum/05-Enum-in-APIs]] — how FastAPI reads `StrEnum` from a `response_model`. Lesson 06 of this section is the read-side partner: how FastAPI reads `StrEnum` from a *parameter* annotation.
- [[01-typing/02-Annotated-and-Metadata]] — the canonical introduction to `Annotated`. Lesson 02 of this section is the `inspect`-side partner: how `get_type_hints(..., include_extras=True)` reads that `Annotated` metadata back.

## What's next

Open [[10-inspect/01-signature-and-Parameter]] and start typing. We will inspect a `boardly` function with `inspect.signature`, walk its `Parameter` objects, and learn the five `kind` values that decide which arguments go where.

- **Lesson 01** — `signature`, `Parameter`, the five `kind` values.
- **Lesson 02** — `get_type_hints` with `include_extras=True` (the FastAPI read path for `Annotated`).
- **Lesson 06** — The senior deep-dive: the full dependency-resolution call chain, with a working re-implementation.

**Welcome to the inspect section. Pull up a chair.**

## Sources

- **Python `inspect` module documentation** — https://docs.python.org/3/library/inspect.html — accessed 2026-10-23 — the source-of-truth API reference for `signature`, `Parameter`, `BoundArguments`, `iscoroutinefunction`, and the `Parameter.kind` enum.
- **Python `typing` module documentation — `get_type_hints`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical reference for the function that resolves string annotations and reads `Annotated` metadata. (It lives in `typing`, not `inspect` — lesson 02 explains the why.)
- **PEP 649 — Deferred evaluation of annotations** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the PEP that motivated `inspect.get_annotations` (PEP 649 was deferred from 3.10 and is targeted for 3.14). Lesson 02 notes the 3.14 connection.
