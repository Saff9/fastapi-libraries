---
title: "Lesson 02: Annotated and Metadata"
aliases:
 - Annotated and Metadata
 - 02-Annotated-and-Metadata
 - PEP 593
tags:
 - typing
 - annotated
 - pep-593
 - canonical
 - fastapi-primitive
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "45–60 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[01-typing/11-typing-vs-runtime]]"
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
first_taught_in: "01-typing/02-Annotated-and-Metadata"
---

# Lesson 02: Annotated and Metadata

*The single primitive FastAPI introspects on every request — `Annotated[T, metadata]` (PEP 593) — and the `include_extras=True` flag the entire dependency-injection system hinges on.*

**You're at the very beginning of Section 01's most important lesson.**

If there is one lesson in this entire vault to read twice, this is it. Every `Annotated[int, Depends(get_db)]` you write in a FastAPI route is a `typing.Annotated` (PEP 593). FastAPI calls `typing.get_type_hints(route_handler, include_extras=True)` on every request-handling function — and the `include_extras=True` part is what makes FastAPI's entire dependency-injection system possible. Without `Annotated`, FastAPI pre-0.85 had to wrap dependencies in a separate `Depends(...)` argument, which broke the type signature for static checkers. With `Annotated`, the type stays `int`, the metadata rides along, and both FastAPI and mypy can read the same signature. Take your time. Type every example. **This is how you learn.**

#typing #annotated #canonical #fastapi-primitive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct** `Annotated[T, *metadata]` annotations with one or more metadata items and explain what Python stores in `__metadata__`.
2. **Explain** why `Annotated[int, "meta"]` and `int` are different objects at runtime but `get_type_hints(f, include_extras=False)` returns `int` (the metadata is stripped by default).
3. **Recover** metadata using `get_type_hints(..., include_extras=True)`, `get_origin`, `get_args`, and the `.__metadata__` attribute.
4. **Reproduce** the exact introspection pattern FastAPI uses to read a route signature: walk `get_type_hints(..., include_extras=True)`, look for `Annotated`, peel off metadata, dispatch dependencies.
5. **Defend** the choice of `Annotated[T, Depends(...)]` over the legacy `Depends(...)` wrapper argument — and explain why FastAPI 0.85+ migrated.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — you must be comfortable with `list[int]`, `X | Y`, and `get_type_hints(f)` returning a `dict[str, type]`.
- **About 45–60 minutes of focused time.**

**The most common gap: not knowing `get_type_hints` has an `include_extras` flag.**

Most engineers have called `get_type_hints(f)` at least once. Few know it takes a keyword argument `include_extras=False` by default, and that the *only* way to recover `Annotated` metadata is to pass `include_extras=True`. FastAPI calls it with `True` on every single request. If you do not know the flag exists, you cannot reproduce what FastAPI does — and reproducing what FastAPI does is the entire point of this course.

## The Problem

Here is the problem this lesson solves. You are writing a FastAPI route that takes a `project_id` query parameter. The route needs three pieces of information per parameter:

1. The **type** — `int` — so OpenAPI generation, validation, and serialisation all work.
2. The **default** — `Query(default=1)` — what to use when the client omits the parameter.
3. The **validation rule** — `gt=0` — the project_id must be positive.

Pre-PEP-593 FastAPI (versions before 0.85) wrote this as two separate arguments:

```python
def list_tickets(
    project_id: int = Depends(Query(default=1, gt=0)),
) -> list[int]:
    ...
```

That works at runtime but the type signature lies. mypy sees `project_id: int = Depends(Query(...))` — the default value is a `Depends` object, not an `int`. Static checkers complained. IDEs could not autocomplete the int methods. Documentation generators rendered the default as a Depends instance. The fix — PEP 593, available since Python 3.9 — is `Annotated`:

```python
def list_tickets(
    project_id: Annotated[int, Query(default=1, gt=0)],
) -> list[int]:
    ...
```

Now the type is `int`. The metadata (`Query(default=1, gt=0)`) rides along, invisible to mypy and the IDE, visible to anyone who calls `get_type_hints(..., include_extras=True)`. FastAPI 0.85+ migrated to this form, and modern FastAPI docs recommend `Annotated` for every route.

## The Code

```python
# boardly/annotated_metadata.py
"""boardly — Annotated (PEP 593), the primitive FastAPI introspects on every request."""
from typing import Annotated, get_type_hints, get_origin, get_args

# A "dependency" — in real FastAPI this returns a database session.
def get_db() -> str:
    return "db-session"

# A marker class — works like FastAPI's Query/Depends/Header.
class Query:
    def __init__(self, default=None, *, gt=None):
        self.default = default
        self.gt = gt
    def __repr__(self):
        return f"Query(default={self.default!r}, gt={self.gt})"

# A FastAPI-style route using Annotated.
def list_tickets(
    project_id: Annotated[int, Query(gt=0)],
    db: Annotated[str, "db_dependency"],
) -> list[int]:
    return [1, 2, 3]

if __name__ == "__main__":
    # Default get_type_hints STRIPS metadata — Annotated[int, ...] becomes int.
    stripped = get_type_hints(list_tickets)
    print("default (stripped):", stripped)

    # include_extras=True preserves the metadata.
    preserved = get_type_hints(list_tickets, include_extras=True)
    print("include_extras=True:", preserved)

    # Drill into one annotation.
    ann = preserved["project_id"]
    print("  type:", type(ann).__name__)
    print("  __metadata__:", ann.__metadata__)
    print("  get_origin:", get_origin(ann))
    print("  get_args:", get_args(ann))

    # The first arg of get_args is the underlying type — recovered by FastAPI.
    assert get_args(ann)[0] is int
    print("  get_args[0] is int:", get_args(ann)[0] is int)

    # The stripped form is *identical* to the underlying type.
    assert stripped["project_id"] is int
    print("  stripped is int:", stripped["project_id"] is int)

    # Multiple metadata items are kept as a tuple in __metadata__.
    def f(x: Annotated[int, "first", "second", "third"]) -> None: ...
    extras = get_type_hints(f, include_extras=True)
    print("  multi-meta __metadata__:", extras["x"].__metadata__)
```

## Line-by-Line Deep Dive

### Lines 1–4: Module header and imports

```python
# boardly/annotated_metadata.py
"""boardly — Annotated (PEP 593), the primitive FastAPI introspects on every request."""
from typing import Annotated, get_type_hints, get_origin, get_args
```

We import four names from `typing`: `Annotated` (the constructor), `get_type_hints` (the introspector), `get_origin` and `get_args` (the two helpers that decompose a generic alias). `Annotated` was added in Python 3.9 (PEP 593). If you are on 3.8 you can polyfill it via `typing_extensions.Annotated`, but 3.12 — this vault's target — has it natively. The four names are the *complete* surface a framework needs to read PEP 593 metadata; everything else is sugar.

**Why does `Annotated` live in `typing` and not `types`?**

`types` is the module for "things that exist at runtime and have a type". `typing` is the module for "things that describe types". PEP 593 chose `typing` because `Annotated` is fundamentally a type-annotation construct — its primary consumer is static checkers, with runtime introspection as a secondary use. CPython implements it as `typing._AnnotatedAlias`, a private class, constructed by `Annotated.__class_getitem__`.

### Lines 6–8: The dependency callable

```python
# A "dependency" — in real FastAPI this returns a database session.
def get_db() -> str:
    return "db-session"
```

In real FastAPI, `get_db` would return a SQLAlchemy session, a Pydantic settings object, or anything else you want injected per-request. Here it returns a string for the demo. The point is that `get_db` is a *callable* — FastAPI calls it (or its cached result) when the route runs. We do not call it in this file — we attach it as metadata and let FastAPI's machinery call it later. The signature `() -> str` is what FastAPI uses to type the injected value.

**Why attach the callable as metadata instead of as a default value?**

Two reasons. (1) Defaults are part of the parameter's signature and visible to mypy — `project_id: int = Depends(get_db)` would make mypy think `project_id`'s default is a `Depends` instance, which is a type error. (2) Defaults are evaluated once at function-definition time; if `get_db` is a factory, that is fine, but if you want a fresh per-request evaluation (the normal FastAPI case), the framework needs to know to call it on every request — which means storing it as metadata, not as a default. `Annotated` lets you store the dependency *separately* from the default, so mypy sees a clean `int` and FastAPI sees both the `int` type and the dependency.

### Lines 10–16: The `Query` marker class

```python
# A marker class — works like FastAPI's Query/Depends/Header.
class Query:
    def __init__(self, default=None, *, gt=None):
        self.default = default
        self.gt = gt
    def __repr__(self):
        return f"Query(default={self.default!r}, gt={self.gt})"
```

This is a minimal stand-in for `fastapi.Query`. The real `Query` class is more elaborate (it carries title, description, examples, deprecated, alias, regex, min/max length, etc.) but the *principle* is identical: it is a plain class whose instances are attached as `Annotated` metadata. The `__repr__` matters because the metadata is printed by `get_type_hints(..., include_extras=True)`, and a useless `<Query object at 0x...>` is unreadable. Always give marker classes a `__repr__`.

**Why is `gt` a keyword-only argument (`*, gt=None`)?**

So that the call site reads `Query(default=1, gt=0)` — the keyword makes the meaning obvious. If `gt` were positional, you would see `Query(1, 0)` in the codebase and have to count positions to know which is the default and which is the constraint. FastAPI's real `Query` is keyword-only for the same reason. This is a small design choice, but it is the difference between a marker API that reads like English and one that reads like noise.

### Lines 18–22: The route signature

```python
# A FastAPI-style route using Annotated.
def list_tickets(
    project_id: Annotated[int, Query(gt=0)],
    db: Annotated[str, "db_dependency"],
) -> list[int]:
    return [1, 2, 3]
```

This is the heart of the lesson. `project_id: Annotated[int, Query(gt=0)]` says: "the parameter is an `int`; attached to it, ride a `Query(gt=0)` instance." The `int` is what mypy sees; the `Query(gt=0)` is what FastAPI sees. The two never collide because `Annotated` separates them. The `db: Annotated[str, "db_dependency"]` line shows that metadata can be any object — here, a plain string. In real FastAPI you would use `Depends(get_db)`, but a string makes the demo minimal: anything you put in the second-onwards position of `Annotated[...]` is metadata.

**Why is metadata a tuple and not a single object?**

Because PEP 593 explicitly allows multiple pieces of metadata to compose. `Annotated[int, Query(gt=0), Depends(get_db), "docstring"]` is legal — all three items are stored in `__metadata__` as a tuple. This composes: FastAPI's `Depends` reads only the `Depends` items; Pydantic's `Field` reads only the `Field` items; a documentation generator reads only the strings. Multiple frameworks can attach to the same parameter without stepping on each other. That composability is the *real* win of PEP 593 — not just "one metadata slot", but "an ordered tuple of metadata slots".

**What if I put the same kind of metadata twice — `Annotated[int, Query(gt=0), Query(lt=100)]`?**

`__metadata__` will be `(Query(gt=0), Query(lt=100))` — two `Query` instances. The framework decides what to do with that. FastAPI raises an error ("multiple Query annotations"); Pydantic merges them. There is no rule at the language level; it is a per-framework decision. If you are designing a framework, document your merge rule explicitly.

### Lines 24–27: Default `get_type_hints` strips metadata

```python
if __name__ == "__main__":
    # Default get_type_hints STRIPS metadata — Annotated[int, ...] becomes int.
    stripped = get_type_hints(list_tickets)
    print("default (stripped):", stripped)
```

The default call `get_type_hints(list_tickets)` returns `{'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[int]}` — the metadata is gone. This is the *backward-compatibility default* — code written before PEP 593 expected `int` from `Annotated[int, ...]`, and the default preserves that behaviour. The default is correct for 99% of code: type-checkers, documentation tools, and most introspection frameworks want the *underlying type*, not the metadata. The 1% that want the metadata are frameworks like FastAPI and Pydantic — and they pass `include_extras=True`.

**Why is the default `False` and not `True`?**

Backward compatibility. `get_type_hints` was added in Python 3.5 (PEP 484). PEP 593 (`Annotated`) was added in 3.9. Between 3.5 and 3.9, every caller of `get_type_hints` expected it to return *types*. If 3.9 had flipped the default to `True`, every existing caller would have started receiving `Annotated[int, ...]` objects where they expected `int` — silent breakage. The Python core team chose to keep the default `False` and require frameworks to opt in. This is a master-class in API evolution: do not break existing callers, even when you have a better default.

### Lines 29–32: `include_extras=True` preserves metadata

```python
    # include_extras=True preserves the metadata.
    preserved = get_type_hints(list_tickets, include_extras=True)
    print("include_extras=True:", preserved)
```

`preserved` now contains `{'project_id': typing.Annotated[int, Query(default=None, gt=0)], 'db': typing.Annotated[str, 'db_dependency'], 'return': list[int]}`. The `Annotated[...]` objects survive. This is the line FastAPI executes on every request — internally it is something close to:

```python
hints = get_type_hints(route_handler, include_extras=True)
for name, hint in hints.items():
    if get_origin(hint) is Annotated or hasattr(hint, "__metadata__"):
        # Peel off metadata items, dispatch dependencies, validation, etc.
        ...
```

The exact FastAPI implementation is in `fastapi/dependencies/utils.py` (function `get_dependant`), and it does exactly this walk. We will reproduce a minimal version of it in the exercises.

### Lines 34–42: Drilling into one annotation

```python
    # Drill into one annotation.
    ann = preserved["project_id"]
    print("  type:", type(ann).__name__)
    print("  __metadata__:", ann.__metadata__)
    print("  get_origin:", get_origin(ann))
    print("  get_args:", get_args(ann))
```

Four introspection primitives on the same `Annotated` object:

- `type(ann).__name__` is `_AnnotatedAlias` — the internal class. You will rarely use this directly; `get_origin` is the public way.
- `ann.__metadata__` is `(Query(default=None, gt=0),)` — the tuple of metadata items, in the order you wrote them. This is the *public* attribute for accessing metadata.
- `get_origin(ann)` is `typing.Annotated` — the marker class. Comparing `get_origin(ann) is typing.Annotated` is the canonical way to detect an `Annotated` form (or `hasattr(ann, '__metadata__')`).
- `get_args(ann)` is `(<class 'int'>, Query(default=None, gt=0))` — the underlying type *plus* the metadata items, flattened. `get_args(ann)[0]` is the underlying type.

**Why are there two ways to get the metadata — `__metadata__` and `get_args`?**

They return different shapes. `__metadata__` is *just* the metadata: `(Query(...),)`. `get_args` is *everything*: `(int, Query(...))`. Use `__metadata__` when you only want the metadata (the framework's view); use `get_args` when you want the underlying type as well (the type-checker's view). The two coexist because they serve different consumers: frameworks want `__metadata__`, type tools want `get_args`. Pick the one that matches what you are doing.

### Lines 44–47: The underlying type is recoverable

```python
    # The first arg of get_args is the underlying type — recovered by FastAPI.
    assert get_args(ann)[0] is int
    print("  get_args[0] is int:", get_args(ann)[0] is int)

    # The stripped form is *identical* to the underlying type.
    assert stripped["project_id"] is int
    print("  stripped is int:", stripped["project_id"] is int)
```

Two assertions. First: `get_args(ann)[0] is int` — the first element of `get_args` is the underlying type, recovered by reference. Second: `stripped["project_id"] is int` — the result of `get_type_hints(..., include_extras=False)` is *the same `int` object*. These are the same `int`. So if you have an `Annotated[int, ...]` form, you can recover the underlying type in three ways:

1. `get_args(ann)[0]` — direct index.
2. `get_type_hints(f)["x"]` — re-run with the default flag, get the underlying type.
3. `typing.get_type_hints(f, include_extras=True)["x"].__origin__` — the private attribute (less stable, prefer `get_args`).

FastAPI uses form (1). Pydantic uses a variant that calls `get_args` and walks recursively, because Pydantic needs to handle `Annotated[list[int], Field(min_items=1)]` — the underlying type is itself a generic, and Pydantic needs to recurse into it.

### Lines 49–52: Multiple metadata items

```python
    # Multiple metadata items are kept as a tuple in __metadata__.
    def f(x: Annotated[int, "first", "second", "third"]) -> None: ...
    extras = get_type_hints(f, include_extras=True)
    print("  multi-meta __metadata__:", extras["x"].__metadata__)
```

The `Annotated[int, "first", "second", "third"]` form puts three strings into `__metadata__`. The output `('first', 'second', 'third')` shows they are stored as a tuple, in the order written. This is what makes PEP 593 composable: you can attach `Field(...)`, `Depends(...)`, and a docstring string to the same parameter, and each framework reads only what it understands.

**Why is metadata a tuple and not a list?**

Immutability. Type annotations are constructed at function-definition time and should not be mutated afterwards. A tuple enforces that. If you have ever tried to monkey-patch a function's `__annotations__` at runtime (some test frameworks do), you have discovered that the metadata tuple is frozen — you cannot append to it in place, only construct a new `Annotated` object.

## Execution Trace

```bash
$ python boardly/annotated_metadata.py
default (stripped): {'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[int]}
include_extras=True: {'project_id': typing.Annotated[int, Query(default=None, gt=0)], 'db': typing.Annotated[str, 'db_dependency'], 'return': list[int]}
  type: _AnnotatedAlias
  __metadata__: (Query(default=None, gt=0),)
  get_origin: <class 'typing.Annotated'>
  get_args: (<class 'int'>, Query(default=None, gt=0))
  get_args[0] is int: True
  stripped is int: True
  multi-meta __metadata__: ('first', 'second', 'third')
```

The two lines that matter are the `default (stripped)` line — `int`, no metadata — and the `include_extras=True` line — `Annotated[int, Query(...)]`, metadata preserved. The `get_args[0] is int` and `stripped is int` lines prove they are the same `int`. The `multi-meta __metadata__` line shows the tuple-of-strings form.

## Common Mistakes

### Mistake 1: Calling `get_type_hints` without `include_extras=True` and wondering where the metadata went

```python
hints = get_type_hints(my_route)  # ← no include_extras
for name, hint in hints.items():
    if hasattr(hint, "__metadata__"):  # ← never True; metadata was stripped
        process(hint.__metadata__)
```

**Symptom:** The `if hasattr(hint, "__metadata__")` branch never fires. The framework silently does nothing — no dependencies injected, no validation applied.
**Why:** The default of `include_extras` is `False`. The metadata is stripped before you see it. `hasattr` returns `False` because the resulting object is plain `int`, not `_AnnotatedAlias`.
**Fix:**

```python
hints = get_type_hints(my_route, include_extras=True)
```

This is the single most common mistake when writing a FastAPI-like framework. The mistake is invisible at runtime — no error, just missing behaviour.

### Mistake 2: Putting metadata in the wrong position

```python
def f(x: Annotated[Query(gt=0), int]) -> None: ...  # ← wrong order
```

**Symptom:** FastAPI sees the underlying type as `Query(gt=0)` (a `Query` instance), not as `int`, and tries to validate the parameter as a `Query` — which fails or treats it as a body.
**Why:** `Annotated` is positional: the *first* argument is the underlying type; everything else is metadata. Swapping the order makes the metadata the type.
**Fix:**

```python
def f(x: Annotated[int, Query(gt=0)]) -> None: ...
```

If you are not sure, the rule is: the first argument is the type mypy sees; the rest is the metadata frameworks read. Run `get_args(ann)` and confirm `args[0]` is the type you expect.

### Mistake 3: Using a mutable default as metadata

```python
def f(x: Annotated[int, Query(default=[])]) -> None: ...
```

**Symptom:** Two concurrent requests share the same list default — mutation in one request affects the next. This is the classic "mutable default argument" bug, dressed up in `Annotated` clothing.
**Why:** `Annotated` is constructed at function-definition time. The `Query(default=[])` instance is created *once*, shared across every call. Any mutation persists.
**Fix:** Use a sentinel (`Query(default=None)`) and create the list inside the function, or use `Query(default_factory=list)` — the pattern Pydantic's `Field` uses. The boardly `Query` class above does not support `default_factory`; the real FastAPI `Query` does, and you should use it for any mutable default.

## Engineering Trade-Offs

**Decision:** Use `Annotated[T, metadata]` for every FastAPI route parameter, every Pydantic field, and any framework that needs metadata attached to a type.
**Both sides:** The legacy form (`T = Depends(...)`) works at runtime and is shorter to write. It breaks mypy and IDE tooling because the default value is a non-`T` object. The `Annotated` form is two more characters and one import, but mypy and IDEs see the correct type.
**Commitment:** boardly uses `Annotated` everywhere. There is no file in the boardly codebase that uses the legacy `T = Depends(...)` form. This is the FastAPI recommendation since 0.85 and it is non-negotiable for any new code.

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/annotated_metadata.py` and run it. Compare your output to the Execution Trace. `Verify: python boardly/annotated_metadata.py`
2. **Exercise 2 — Build a minimal FastAPI-like dispatcher.** Write a function `dispatch(route)` that takes a route function, calls `get_type_hints(route, include_extras=True)`, and for each parameter prints "param X has type Y and metadata Z". Run it on `list_tickets`. `Verify: python -c "from boardly.annotated_metadata import dispatch, list_tickets; dispatch(list_tickets)"`
3. **Exercise 3 — Compose two metadata items.** Add a `Depends` marker class and rewrite `db: Annotated[str, Depends(get_db)]` so that `__metadata__` contains both a `Depends` instance and the string `"db_dependency"` (`Annotated[str, Depends(get_db), "db_dependency"]`). Print `__metadata__` and confirm it has two items. `Verify: python -c "from boardly.annotated_metadata import list_tickets; from typing import get_type_hints; h = get_type_hints(list_tickets, include_extras=True); print(h['db'].__metadata__)"`
4. **Exercise 4 — Detect Annotated without `get_origin`.** Write a function `is_annotated(hint) -> bool` that returns `True` if `hint` is an `Annotated` form, using only `hasattr`. Use it to filter `get_type_hints(list_tickets, include_extras=True).values()`. `Verify: python -c "from boardly.annotated_metadata import is_annotated, list_tickets; from typing import get_type_hints; print([k for k,v in get_type_hints(list_tickets, include_extras=True).items() if is_annotated(v)])"`
5. **Exercise 5 — Build a `Field` marker.** Implement a `Field` marker class with `gt`, `lt`, `min_length`, `max_length`. Use it in `Annotated[str, Field(min_length=1, max_length=100)]`. Write a `validate(name, value, hint)` function that reads the `Field` from the hint's `__metadata__` and validates `value`. `Verify: python -c "from boardly.annotated_metadata import validate, Field; from typing import Annotated; h = Annotated[str, Field(min_length=1, max_length=3)]; print(validate('name', 'ab', h)); print(validate('name', 'abcd', h))"`

## Verification

```bash
$ python boardly/annotated_metadata.py
default (stripped): {'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[int]}
include_extras=True: {'project_id': typing.Annotated[int, Query(default=None, gt=0)], 'db': typing.Annotated[str, 'db_dependency'], 'return': list[int]}
  type: _AnnotatedAlias
  __metadata__: (Query(default=None, gt=0),)
  get_origin: <class 'typing.Annotated'>
  get_args: (<class 'int'>, Query(default=None, gt=0))
  get_args[0] is int: True
  stripped is int: True
  multi-meta __metadata__: ('first', 'second', 'third')
```

If the output matches, you have successfully reproduced the four-primitive introspection FastAPI uses to read every route. The `include_extras=True` line is the lesson in one screenshot.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — you learned `list[int]`, `X | Y`, and `get_type_hints(f)`. This lesson extends `get_type_hints` with the `include_extras` flag, the one FastAPI depends on.

## What's Next

[[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T")`, bounds, constraints, and `class Stack(Generic[T])`. `Annotated` taught you how to attach metadata to a *concrete* type. `TypeVar` teaches you how to write *parameterised* types — a function that works on `list[int]` or `list[str]` depending on what the caller passes. Three things to look for in lesson 03:

- The difference between `TypeVar("T")` (unbounded — any type) and `TypeVar("T", bound=int)` (must be `int` or a subclass) and `TypeVar("T", str, bytes)` (must be one of these — a *constraint*).
- Why `Generic[T]` is the marker class that makes a class subscriptable.
- How FastAPI uses `TypeVar` in `Depends`'s own signature to type the dependency's return value back to the caller.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.Annotated — CPython reference** — https://docs.python.org/3/library/typing.html#typing.Annotated — accessed 2026-10-23 — the canonical API documentation for `Annotated`, `get_type_hints(include_extras=True)`, `get_origin`, `get_args`, and `__metadata__`.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the PEP that introduced `Annotated` in 3.9. Read the "Resolving Type Annotations" section — it explicitly mentions `include_extras` and explains why the default is `False`.
- **PEP 484 — Type Hints (the `get_type_hints` function)** — https://peps.python.org/pep-0484/ — accessed 2026-10-23 — the original type-hints PEP, where `get_type_hints` was defined and the `include_extras` flag was later added by PEP 593.
- **FastAPI source — `fastapi/dependencies/utils.py`** — https://github.com/tiangolo/fastapi/blob/master/fastapi/dependencies/utils.py — accessed 2026-10-23 — the production implementation of the dependency walk we reproduce in Exercise 2.

## What We Learned

- `Annotated[T, *metadata]` (PEP 593, 3.9+) attaches metadata to a type without changing the type's identity for static checkers.
- `get_type_hints(f)` (default) *strips* metadata and returns the underlying type — backward compatible with pre-PEP-593 code.
- `get_type_hints(f, include_extras=True)` preserves the metadata; this is the call FastAPI makes on every route.
- `ann.__metadata__` is the tuple of metadata items; `get_args(ann)[0]` is the underlying type; `get_origin(ann) is typing.Annotated` is the canonical detection test.
- Multiple metadata items compose: `Annotated[int, Field(...), Depends(...), "doc"]` stores all three in `__metadata__`.
- The legacy `T = Depends(...)` form lies to mypy because the default is a non-`T` object; the `Annotated[T, Depends(...)]` form tells the truth.
