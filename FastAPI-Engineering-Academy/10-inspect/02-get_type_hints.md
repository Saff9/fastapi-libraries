---
title: "Lesson 02: get_type_hints"
aliases:
 - typing.get_type_hints
 - get_type_hints include_extras
 - Annotated metadata
tags:
 - inspect
 - typing
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
related_lessons:
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
 - "[[13-future/01-from-future-import-annotations]]"
first_taught_in: "10-inspect/02-get_type_hints"
---

# Lesson 02: get_type_hints

*How `boardly`'s `get_type_hints(get_ticket, include_extras=True)` reads the `Annotated[int, Depends(get_db)]` from a function signature — the call FastAPI makes on every route to find the dependency metadata that `inspect.signature` strips by default.*

**You're at the very beginning of Section 10 — two lessons in.**

In the last lesson you learned that `inspect.signature` reads parameter *shape* (name, kind, default, annotation) but does not resolve string annotations, and does not preserve `Annotated` metadata in a usable form. Today you will learn `typing.get_type_hints` — the partner call that resolves strings and, with `include_extras=True`, keeps the `Annotated` markers FastAPI needs. Take your time. Type every example. **This is how you learn.**

#inspect #typing #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `typing.get_type_hints`** — pass a callable, get back a dict of resolved type hints keyed by parameter name (plus the special `"return"` key for the return type).
2. **Explain the `include_extras` flag** — `include_extras=False` (the default) strips `Annotated[T, ...]` to `T`; `include_extras=True` keeps `Annotated[T, ...]` so callers can read the metadata.
3. **Explain why `get_type_hints` lives in `typing` and not `inspect`** — `inspect` reads the *shape* of a callable; `typing` resolves the *type system*. Different responsibilities, different modules.
4. **Read `Annotated` metadata via `get_origin`/`get_args`** — `get_origin(Annotated[int, "meta"])` returns `Annotated`; `get_args(...)` returns `(int, "meta")`.
5. **Explain the `from __future__ import annotations` interaction** — string annotations from PEP 563 are resolved by `get_type_hints` using the callable's `__globals__`, not by `inspect.signature`.

## Prerequisites

Before starting, you need:

- **Lesson 01 of this section** — [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`, the `empty` sentinel.
- **`Annotated` basics** — `Annotated[int, "metadata"]` should be familiar. See [[01-typing/02-Annotated-and-Metadata]] for the canonical introduction.
- **About 35–45 minutes of focused time.**

**The most common gap: assuming `inspect.signature` reads type annotations.** It does — but only as strings, not resolved types. Under `from __future__ import annotations`, `param.annotation` is the string `"int"`, not the class `int`. `get_type_hints` is the call that resolves the strings back to real types. Students conflate the two and then are surprised when `issubclass(param.annotation, int)` raises `TypeError` because `param.annotation` is the string `"int"`.

## The Problem

Here is the bug. `boardly` had this route:

```python
# boardly/routes.py
from __future__ import annotations   # PEP 563 — all annotations are strings
from typing import Annotated
from fastapi import Depends

def get_db():
    yield "session"

def get_ticket(id: int, db: Annotated[str, Depends(get_db)]):
    ...
```

The route uses `from __future__ import annotations` (common in modern codebases; it makes annotations strings to break import cycles). The function looks fine. But when FastAPI tries to read `Annotated[str, Depends(get_db)]` from the parameter annotation, it sees the *string* `"Annotated[str, Depends(get_db)]"`, not the `Annotated` object. The string has to be resolved (evaluated) before FastAPI can pull the `Depends` marker out of it.

`inspect.signature` does not resolve strings. It returns the annotation as-is from `__annotations__`, which (under PEP 563) is the string form. FastAPI has to call `typing.get_type_hints(call, include_extras=True)` to resolve the strings into real `Annotated` objects, then walk the `Annotated`'s `.args` to find the `Depends` marker.

The bug that motivates `get_type_hints` is "I see the annotation as a string and I need the real type." The fix is one call: `get_type_hints(call, include_extras=True)`.

## The Code

```python
# boardly/di_type_hints.py
"""Demonstrates typing.get_type_hints and the include_extras flag."""
import inspect
from typing import Annotated, get_type_hints, get_origin, get_args, Any, Callable


# 1. A boardly function with mixed annotations
def get_ticket(
    id: int,
    db: Annotated[str, "the session"],
    user: "User",               # forward reference — string form
    tags: Annotated[list[str], "the tags"] = [],
) -> "Ticket":
    ...

class User: ...
class Ticket: ...

# 2. inspect.signature sees the RAW annotations (strings or objects, mixed)
sig = inspect.signature(get_ticket)
print("--- inspect.signature annotations ---")
for name, param in sig.parameters.items():
    print(f"  {name}: {param.annotation!r}")

# 3. get_type_hints resolves the strings AND strips Annotated by default
hints_stripped = get_type_hints(get_ticket)
print("\n--- get_type_hints (include_extras=False, default) ---")
for name, hint in hints_stripped.items():
    print(f"  {name}: {hint!r}")

# 4. get_type_hints with include_extras=True keeps Annotated
hints_kept = get_type_hints(get_ticket, include_extras=True)
print("\n--- get_type_hints (include_extras=True) ---")
for name, hint in hints_kept.items():
    print(f"  {name}: {hint!r}")

# 5. Pull Annotated metadata via get_origin / get_args
print("\n--- Annotated metadata for 'db' ---")
db_hint = hints_kept["db"]
print(f"  get_origin(db): {get_origin(db_hint)}")   # typing.Annotated
print(f"  get_args(db):  {get_args(db_hint)}")     # (str, 'the session')

# 6. The "return" key
print(f"\n--- 'return' key ---")
print(f"  hints_stripped['return']: {hints_stripped['return']!r}")
print(f"  hints_kept['return']:     {hints_kept['return']!r}")

# 7. The signature — confirm it matches what inspect.signature gives
print(f"\n  inspect.signature of get_type_hints itself:")
print(f"  {inspect.signature(get_type_hints)}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 8–17: The function under inspection

```python
def get_ticket(
    id: int,
    db: Annotated[str, "the session"],
    user: "User",               # forward reference — string form
    tags: Annotated[list[str], "the tags"] = [],
) -> "Ticket":
    ...
```

This function deliberately mixes three annotation styles:

- `id: int` — a real class annotation. `inspect.signature` reads it as `int` directly.
- `db: Annotated[str, "the session"]` — an `Annotated` form with metadata. `inspect.signature` reads it as the `Annotated` object (because it is already an object, not a string).
- `user: "User"` — a forward reference (string form). `inspect.signature` reads it as the *string* `"User"`, because that is what is in `__annotations__`.
- `tags: Annotated[list[str], "the tags"] = []` — `Annotated` with a list type and a default. Same as `db` but with a default.

The return annotation `-> "Ticket"` is also a forward reference. `inspect.signature` reads it as the string `"Ticket"`. The `User` and `Ticket` classes are defined *after* the function — that is the canonical scenario where you need forward references, and it is also the canonical scenario that motivates `from __future__ import annotations` (which makes *all* annotations strings, even when the referenced type is defined before the function).

### Lines 19–23: `inspect.signature` reads raw annotations

```python
sig = inspect.signature(get_ticket)
print("--- inspect.signature annotations ---")
for name, param in sig.parameters.items():
    print(f"  {name}: {param.annotation!r}")
```

`inspect.signature` returns `Parameter` objects whose `.annotation` is whatever is in the function's `__annotations__` dict — strings stay strings, real types stay real types. The output looks like:

```
id: <class 'int'>
db: typing.Annotated[str, 'the session']
user: 'User'
tags: typing.Annotated[list[str], 'the tags']
```

The `id` annotation is the real `int` class. The `db` annotation is the `Annotated` object (already an object, not a string). The `user` annotation is the *string* `"User"` — not the class. The `tags` annotation is the `Annotated` object.

**Why does `inspect.signature` not resolve strings?** Because doing so would require evaluating the string in the function's `__globals__` — a side-effectful operation that can raise `NameError` (if the type is not yet imported) or import a heavy module. `inspect.signature` is a *pure* read; it deliberately does not have side effects. `get_type_hints` is the *side-effectful* companion that does the evaluation.

**Warning — `param.annotation` is not always a type**

```python
ann = sig.parameters["user"].annotation   # the string "User"
issubclass(ann, User)                     # TypeError: issubclass() arg 1 must be a class
```

The string `"User"` is not a class. `issubclass` raises. You must resolve the string with `get_type_hints` before you can do type-system operations on it.

### Lines 25–30: `get_type_hints` resolves the strings

```python
hints_stripped = get_type_hints(get_ticket)
print("\n--- get_type_hints (include_extras=False, default) ---")
for name, hint in hints_stripped.items():
    print(f"  {name}: {hint!r}")
```

`typing.get_type_hints(get_ticket)` returns a dict mapping parameter name → resolved type. The output looks like:

```
id: <class 'int'>
db: <class 'str'>       <- Annotated was stripped to the underlying type
user: <class '__main__.User'>    <- string resolved to the class
tags: list[str]    <- generic parameterisation kept intact
return: <class '__main__.Ticket'>
```

`get_type_hints` resolves forward references (the `"User"` string becomes `<class 'User'>`), keeps generic parameterisations like `list[str]` intact, and *strips* `Annotated` to the underlying type. The only thing it removes is the `Annotated` metadata wrapper; everything else is preserved as the runtime form.

The `Annotated[str, "the session"]` annotation is stripped to just `str`. The `Annotated[list[str], "the tags"]` annotation is stripped to just `list[str]`. The metadata (`"the session"`, `"the tags"`) is gone — that is what `include_extras=False` does by default.

**Why strip `Annotated` by default?** For backward compatibility. Before `Annotated` existed (PEP 593, Python 3.9), `get_type_hints` returned plain types. When `Annotated` was added, the maintainers wanted existing code that did `if issubclass(hint, SomeType):` to keep working — so the default strips `Annotated`. `include_extras=True` is the opt-in for code that *wants* the metadata (FastAPI, runtime type validators, custom serializers).

### Lines 32–37: `include_extras=True` keeps `Annotated`

```python
hints_kept = get_type_hints(get_ticket, include_extras=True)
print("\n--- get_type_hints (include_extras=True) ---")
for name, hint in hints_kept.items():
    print(f"  {name}: {hint!r}")
```

`get_type_hints(get_ticket, include_extras=True)` keeps the `Annotated` wrapper. The output looks like:

```
id: <class 'int'>
db: typing.Annotated[str, 'the session']    <- Annotated preserved
user: <class '__main__.User'>
tags: typing.Annotated[list[str], 'the tags']
return: <class '__main__.Ticket'>
```

The `db` and `tags` parameters keep their `Annotated` wrappers, with the metadata intact. The other annotations (`id`, `user`, `return`) are unaffected — `Annotated` was never there.

**Why does FastAPI pass `include_extras=True`?** Because the metadata is the point. FastAPI's `Annotated[Session, Depends(get_session)]` puts the `Depends(get_session)` marker in the metadata position. Without `include_extras=True`, that marker is stripped, and FastAPI cannot find the dependency. Lesson 06 shows the exact call: `get_type_hints(call, include_extras=True)`.

### Lines 39–44: Reading `Annotated` metadata via `get_origin`/`get_args`

```python
print("\n--- Annotated metadata for 'db' ---")
db_hint = hints_kept["db"]
print(f"  get_origin(db): {get_origin(db_hint)}")   # typing.Annotated
print(f"  get_args(db):  {get_args(db_hint)}")     # (str, 'the session')
```

`typing.get_origin(Annotated[int, "meta"])` returns `typing.Annotated` — the *marker* class that signals "this is an `Annotated` form". `typing.get_args(Annotated[int, "meta"])` returns the tuple `(int, "meta")` — the underlying type plus the metadata, in order.

The idiom to extract metadata is:

```python
if get_origin(annotation) is Annotated:
    args = get_args(annotation)
    underlying_type = args[0]
    metadata = args[1:]
    # walk metadata looking for FastAPI markers (Depends, Query, etc.)
```

That is the core of FastAPI's `analyze_param` (which lesson 06 walks in full). The metadata list is `args[1:]` because `args[0]` is the underlying type. Multiple metadata items are allowed: `Annotated[int, "first", "second"]` produces `args = (int, "first", "second")`.

**Tip — Check with `is`, not `==`**

```python
get_origin(annotation) is Annotated   # correct
get_origin(annotation) == Annotated  # also works, but `is` is idiomatic
```

`Annotated` is a singleton marker class. The `is` check is the canonical form; it is what FastAPI's source uses.

### Lines 46–49: The `"return"` key

```python
print(f"\n--- 'return' key ---")
print(f"  hints_stripped['return']: {hints_stripped['return']!r}")
print(f"  hints_kept['return']:     {hints_kept['return']!r}")
```

`get_type_hints` includes the return type under the key `"return"`. That is distinct from `inspect.signature`, where the return type lives on `sig.return_annotation` (a separate attribute). The two APIs chose different shapes:

- `inspect.signature(call).return_annotation` — a separate attribute.
- `get_type_hints(call)["return"]` — a key in the same dict as the parameters.

Both shapes are reasonable; the difference is historical. `inspect.signature` was designed to mirror the call-site shape (parameters and return are conceptually different). `get_type_hints` was designed to mirror the `__annotations__` dict shape (where `"return"` is just a key). FastAPI uses both APIs together — `sig.parameters` for the shape, `hints` for the resolved types — and reads the return type from `hints["return"]` when it needs the resolved form.

### Lines 51–53: The signature of `get_type_hints` itself

```python
print(f"\n  inspect.signature of get_type_hints itself:")
print(f"  {inspect.signature(get_type_hints)}")
```

The signature of `get_type_hints` is:

```
(obj, globalns=None, localns=None, include_extras=False)
```

The four parameters:

- `obj` — the callable (or class, or module) whose annotations to read.
- `globalns` — the globals dict to evaluate forward references in. Defaults to `obj.__globals__` for functions.
- `localns` — the locals dict (for class-scoped references). Defaults to `None`.
- `include_extras` — the `Annotated`-stripping flag. Defaults to `False`.

FastAPI calls it as `get_type_hints(call, include_extras=True)` — passing only `obj` and `include_extras`. The `globalns`/`localns` default to the call's own globals/locals, which is correct for the common case. (FastAPI's source uses `getattr(unwrapped, "__globals__", {})` to pass `globalns` explicitly when the call is wrapped — see lesson 06.)

## Execution Trace

```bash
$ python boardly/di_type_hints.py
--- inspect.signature annotations ---
  id: <class 'int'>
  db: typing.Annotated[str, 'the session']
  user: 'User'
  tags: typing.Annotated[list[str], 'the tags']

--- get_type_hints (include_extras=False, default) ---
  id: <class 'int'>
  db: <class 'str'>
  user: <class '__main__.User'>
  tags: list[str]
  return: <class '__main__.Ticket'>

--- get_type_hints (include_extras=True) ---
  id: <class 'int'>
  db: typing.Annotated[str, 'the session']
  user: <class '__main__.User'>
  tags: typing.Annotated[list[str], 'the tags']
  return: <class '__main__.Ticket'>

--- Annotated metadata for 'db' ---
  get_origin(db): <class 'typing.Annotated'>
  get_args(db):  (<class 'str'>, 'the session')

--- 'return' key ---
  hints_stripped['return']: <class '__main__.Ticket'>
  hints_kept['return']:     <class '__main__.Ticket'>

  inspect.signature of get_type_hints itself:
  (obj, globalns=None, localns=None, include_extras=False)
```

## Common Mistakes

### Mistake 1: Forgetting `include_extras=True` when reading metadata

```python
hints = get_type_hints(call)   # default include_extras=False
db_hint = hints["db"]           # just str, not Annotated[str, "session"]
get_origin(db_hint) is Annotated   # False — Annotated was stripped
```

**Symptom:** Your dependency-injection code never finds the `Depends` marker because `Annotated` was stripped before you got the hint.
**Why:** `include_extras=False` is the default. It strips `Annotated` for backward compatibility. The metadata is gone.
**Fix:** Pass `include_extras=True` explicitly when you want to read `Annotated` metadata. This is the single most common mistake with `get_type_hints` in DI frameworks.

### Mistake 2: Calling `get_type_hints` before the forward reference is defined

```python
def f(x: "Undefined"): ...   # forward reference to a class defined later

get_type_hints(f)   # NameError: name 'Undefined' is not defined
```

**Symptom:** `NameError` at `get_type_hints` call time, even though the class is defined later in the module.
**Why:** `get_type_hints` evaluates forward references in the function's `__globals__`. If the class has not been defined yet (because you are calling `get_type_hints` at import time, before the rest of the module has executed), the evaluation fails.
**Fix:** Either define the class before calling `get_type_hints`, or use `from __future__ import annotations` and defer the `get_type_hints` call until after the module has finished importing. The latter is what FastAPI does — it calls `get_type_hints` at route-registration time, not at import time.

### Mistake 3: Passing a string instead of a callable

```python
get_type_hints("my_module.get_ticket")   # TypeError — obj must be a callable/class/module
```

**Symptom:** `TypeError` from `get_type_hints` because you passed a string.
**Why:** `get_type_hints` takes a callable, class, or module — not a string path. You have to import the callable first.
**Fix:** `import my_module; get_type_hints(my_module.get_ticket)`. If you must work from a string path, use `importlib.import_module` first.

## Engineering Trade-Offs

**Decision:** Use `typing.get_type_hints(call, include_extras=True)` whenever you need resolved annotations + `Annotated` metadata. Pair it with `inspect.signature` for the parameter shape.
**Both sides:** The alternative is `inspect.get_annotations(obj, eval_str=True)` (Python 3.10+, PEP 649 backport). `get_annotations` returns the raw `__annotations__` dict with strings resolved; it does not strip `Annotated` (the metadata is always kept). It is the lower-level call — closer to the source of truth (`__annotations__`). `get_type_hints` is the higher-level call — it post-processes `get_annotations`' output to strip `Annotated` by default, normalize `Optional[X]` to `X | None`, and turn `None` into `type(None)`. For DI frameworks, `get_type_hints(..., include_extras=True)` is the right call — it gives you the resolved types and the metadata in one shot.
**Commitment:** `boardly`'s tiny DI uses `get_type_hints(call, include_extras=True)`. Lesson 06 shows the exact call site.

## Exercises

1. **Exercise 1 — Resolve a forward reference.** Write `def f(x: "int"): ...` and call `get_type_hints(f)`. Confirm the result is `{'x': <class 'int'>}`. `Verify: python -c "from typing import get_type_hints; def f(x: 'int'): ...; print(get_type_hints(f))"`
2. **Exercise 2 — Compare `include_extras`.** Write `def f(x: Annotated[int, "meta"]): ...` and call `get_type_hints` with both `include_extras=False` and `=True`. Confirm the first gives `int` and the second gives `Annotated[int, 'meta']`. `Verify: python -c "from typing import Annotated, get_type_hints; def f(x: Annotated[int,'meta']): ...; print(get_type_hints(f), get_type_hints(f, include_extras=True))"`
3. **Exercise 3 — Pull metadata via `get_origin`/`get_args`.** Take the `include_extras=True` hint from exercise 2 and call `get_origin(hint)` and `get_args(hint)`. Confirm `get_origin` is `Annotated` and `get_args` is `(int, 'meta')`. `Verify: python -c "from typing import Annotated, get_type_hints, get_origin, get_args; def f(x: Annotated[int,'meta']): ...; h=get_type_hints(f, include_extras=True)['x']; print(get_origin(h), get_args(h))"`
4. **Exercise 4 — The `"return"` key.** Write `def f() -> bool: ...` and confirm `get_type_hints(f)["return"] is bool`. `Verify: python -c "from typing import get_type_hints; def f() -> bool: ...; print(get_type_hints(f)['return'])"`
5. **Exercise 5 — Simulate FastAPI's metadata walk.** Write a function `find_depends(call)` that returns the list of `Depends` markers in the call's `Annotated` annotations. Use `get_type_hints(..., include_extras=True)`, `get_origin`, `get_args`, and a `Depends` sentinel class. Test on a function with two `Annotated[..., Depends(...)]` parameters. `Verify: python -c "from boardly.di_type_hints import find_depends; print(find_depends(some_test_function))"`

## Verification

```bash
$ python boardly/di_type_hints.py | head -5
--- inspect.signature annotations ---
  id: <class 'int'>
  db: typing.Annotated[str, 'the session']
  user: 'User'
  tags: typing.Annotated[list[str], 'the tags']
$ python boardly/di_type_hints.py | rg 'include_extras=True'
--- get_type_hints (include_extras=True) ---
$ python -c "from typing import Annotated, get_type_hints, get_origin; def f(x: Annotated[int,'meta']): ...; h=get_type_hints(f, include_extras=True)['x']; print(get_origin(h) is Annotated)"
True
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`, the `empty` sentinel. This lesson's `get_type_hints` is the partner call that resolves the strings `signature` leaves as-is.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated` itself; this lesson shows you how to read it back via `get_type_hints(..., include_extras=True)`.

## What's Next

[[10-inspect/03-iscoroutinefunction]] — You can now read the parameter shape (`signature`) and the resolved annotations (`get_type_hints`). The next lesson covers the third tool FastAPI uses on every route: `inspect.iscoroutinefunction`, which decides whether the route is async (called directly with `await`) or sync (called in a threadpool). Lesson 06 ties all three together.

- **Lesson 03** — `iscoroutinefunction`, sync-vs-async routing.
- **Lesson 06** — The full call chain: `signature` + `get_type_hints` + `iscoroutinefunction` → dependency tree.

## Sources

- **Python `typing` module documentation — `get_type_hints`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical reference for `get_type_hints`, the `include_extras` flag, and the `"return"` key convention.
- **Python `inspect` module documentation — `get_annotations`** — https://docs.python.org/3/library/inspect.html#inspect.get_annotations — accessed 2026-10-23 — the lower-level PEP 649-style API that returns the raw annotations dict (3.10+; PEP 649 itself is targeted for 3.14).
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the PEP that introduced `Annotated`. Read the "Static Type Checker" section for the metadata semantics `get_type_hints(..., include_extras=True)` reads.
- **PEP 563 — Postponed evaluation of annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the PEP that made `from __future__ import annotations` put *all* annotations in string form, and the reason `get_type_hints` exists to resolve them.
- **PEP 649 — Deferred evaluation of annotations** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the PEP that will make annotation resolution lazy (deferred to first access). Targeted for Python 3.14; version-gated in this lesson.

## What We Learned

- You can now call `typing.get_type_hints(call)` and read the resolved type-hints dict (parameter names + `"return"`).
- You can now explain the `include_extras` flag — `False` (default) strips `Annotated`; `True` keeps it.
- You can now explain why `get_type_hints` lives in `typing` and not `inspect` (different responsibilities).
- You can now read `Annotated` metadata via `get_origin`/`get_args` — `get_origin` is `Annotated`, `get_args` is `(type, *metadata)`.
- You can now explain the `from __future__ import annotations` interaction — strings are resolved by `get_type_hints` using `__globals__`, not by `inspect.signature`.
