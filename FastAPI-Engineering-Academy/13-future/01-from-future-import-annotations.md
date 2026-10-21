---
title: "Lesson 01: from __future__ import annotations"
aliases:
 - PEP 563
 - future annotations
 - ForwardRef
 - get_type_hints
tags:
 - __future__
 - typing
 - canonical
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/11-typing-vs-runtime]]"
related_lessons:
 - "[[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]]"
 - "[[13-future/03-When-string-annotations-break]]"
first_taught_in: "13-future/01-from-future-import-annotations"
---

# Lesson 01: from __future__ import annotations

*What `from __future__ import annotations` (PEP 563) actually does at the bytecode level, why `__annotations__` becomes a `dict[str, str]` instead of `dict[str, type]`, why FastAPI and Pydantic must call `typing.get_type_hints()` to resolve them, and the `ForwardRef` mechanism that does the resolving.*

**You're at the very beginning of Section 13.**

You have typed `from __future__ import annotations` at the top of a file a hundred times. You may not know that this single line changes the Python bytecode for every annotation in the module: the annotation expressions are no longer evaluated at class/function definition time, and `__annotations__` is no longer a `dict[str, type]` — it becomes a `dict[str, str]` (or, with PEP 649 in 3.14, a callable that produces the resolved dict on demand). FastAPI, Pydantic, `dataclasses`, mypy, and every other framework that introspects annotations must call `typing.get_type_hints(obj)` to resolve the strings back into types. The resolution can fail with `NameError` if a name is not in scope. This lesson walks the mechanism in detail: the bytecode change, the stringification, the `ForwardRef` object, and the `get_type_hints()` resolution path.

#__future__ #typing #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Explain what `from __future__ import annotations` does at the bytecode level** — annotations are stored as strings, not evaluated.
2. **Read `__annotations__`** and predict whether you will get types or strings — depending on the `__future__` import and the Python version.
3. **Explain why FastAPI calls `typing.get_type_hints(func, include_extras=True)`** on every route signature — and what would break if it just read `__annotations__`.
4. **Trace the `ForwardRef` resolution mechanism** — the string is wrapped in a `ForwardRef`, then `eval`'d against `func.__globals__` at call time.
5. **Predict the `NameError` failure mode** — when a forward-referenced name is not in `func.__globals__`, the resolution raises `NameError`.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. `__annotations__` is the dict Python populates from your hints.
- **`get_type_hints` vs `__annotations__`** — [[01-typing/11-typing-vs-runtime]]. The two APIs and why they differ.
- **About 30–45 minutes of focused time.**

**The most common gap: `__annotations__` is not the same as `get_type_hints()`.**

Students read `func.__annotations__` and assume the values are types. They are — *unless* `from __future__ import annotations` is in scope, in which case the values are strings. The two APIs (`__annotations__` and `get_type_hints()`) differ on this axis: `__annotations__` is whatever the function actually stored; `get_type_hints()` resolves strings to types. FastAPI uses `get_type_hints()`. Pydantic uses `get_type_hints()`. `dataclasses` uses `__annotations__` (which is why `@dataclass` works fine with strings — it does not need to resolve them at runtime). The asymmetry is the foundation of the failure modes in lesson 03.

## The Problem

You write a `boardly` route:

```python
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI()


class Ticket:
    id: int
    title: str


@app.get("/tickets/{id}")
def get_ticket(id: int) -> Ticket:
    return Ticket(id=id, title="x")
```

The route's return type is `Ticket`. But `Ticket` is defined *after* the route's signature — wait, no, in the file above, `Ticket` is defined before `get_ticket`. The forward-reference problem appears when `Ticket` is defined *after* `get_ticket`:

```python
from __future__ import annotations

@app.get("/tickets/{id}")
def get_ticket(id: int) -> Ticket:
    return Ticket(id=id, title="x")

class Ticket:
    id: int
    title: str
```

Without `from __future__ import annotations`, this file fails at module-import time with `NameError: name 'Ticket' is not defined` — the annotation `-> Ticket` is evaluated eagerly, and `Ticket` does not exist yet. With `from __future__ import annotations`, the file imports successfully — the annotation `-> Ticket` is stored as the string `"Ticket"` and not evaluated. FastAPI, at request time, calls `get_type_hints(get_ticket)` which resolves `"Ticket"` against `get_ticket.__globals__`, finds the `Ticket` class (now defined), and proceeds. This is the canonical use case for the import.

## The Code

```python
# boardly/typing_demo/future_annotations.py
"""Demonstrate the bytecode-level effect of `from __future__ import annotations`."""
from __future__ import annotations

from typing import get_type_hints


class Project:
    id: int
    name: str = "untitled"
    archived: bool = False


def get_ticket(id: int) -> Ticket:
    return Ticket(id=id, title="x")


class Ticket:
    id: int
    title: str


if __name__ == "__main__":
    print("Project.__annotations__:", Project.__annotations__)
    print("get_ticket.__annotations__:", get_ticket.__annotations__)

    print("\nresolved via get_type_hints:")
    print("  Project hints:", get_type_hints(Project))
    print("  get_ticket hints:", get_type_hints(get_ticket))
```

## Line-by-Line Deep Dive

### Lines 1–6: The `__future__` import and module header

```python
# boardly/typing_demo/future_annotations.py
"""Demonstrate the bytecode-level effect of `from __future__ import annotations`."""
from __future__ import annotations

from typing import get_type_hints
```

`from __future__ import annotations` is a *future statement* — a directive to the compiler that changes the bytecode generation for the rest of the module. Future statements must appear at the top of the file (after the docstring and before any other code). The compiler flag `CO_FUTURE_ANNOTATIONS` is set on the module's code object. When this flag is set, the compiler stores *every* annotation expression as a string in `__annotations__`, rather than evaluating the expression and storing the resulting type object.

The mechanism is in the compiler's `AST` → bytecode pass: the `Annotation` AST node, normally translated to `LOAD_NAME` + `STORE_ANNOTATION`, is instead translated to `LOAD_CONST` (the string form of the annotation expression) + `STORE_ANNOTATION`. The annotation expression is *reconstructed* from the AST as a string — `int` becomes `"int"`, `"Ticket"` becomes `"'Ticket'"` (wait — the inner string is preserved as `Ticket`), `list[int]` becomes `"list[int]"`, `Annotated[int, Field(gt=0)]` becomes `"Annotated[int, Field(gt=0)]"`. The reconstruction is the source-code form, not the `repr()` of the evaluated type.

**Why does `from __future__ import annotations` not just call `repr()` on the type?**

Because the type has not been evaluated yet — the compiler is working at AST time, before the `LOAD_NAME` calls that would resolve `int` and `Ticket` to their type objects. The string form is reconstructed from the AST *source code*, not from a type object's `repr()`. The difference matters for `Annotated[int, Field(gt=0)]`: the string form preserves the `Field(gt=0)` expression verbatim, whereas `repr(Annotated[int, Field(gt=0)])` would produce `typing.Annotated[int, Field(gt=0)]` (with the `typing.` prefix and the `Field(...)` repr'd). The string form is what `get_type_hints()` needs to re-evaluate the expression at call time, with the `Field` name in scope.

### Lines 8–12: The `Project` class

```python
class Project:
    id: int
    name: str = "untitled"
    archived: bool = False
```

`Project`'s class body declares three fields with annotations. With `from __future__ import annotations`, the compiler stores `Project.__annotations__ = {"id": "int", "name": "str", "archived": "bool"}` — note the values are *strings*, not the `int` and `str` types. The class attributes (`name = "untitled"`, `archived = False`) are still evaluated normally — only the annotations are stringified.

**Why are only annotations stringified, not regular assignments?**

Because future statements only affect the compiler's `Annotation` AST node, not the `Assign` node. `name = "untitled"` is an `Assign` — it runs at class-body time and produces the class attribute `Project.name = "untitled"`. `name: str = "untitled"` is an `AnnAssign` (annotated assignment) — the compiler splits it into two parts: the value `"untitled"` (evaluated and assigned normally) and the annotation `str` (stringified and stored in `__annotations__`). The asymmetry is why you can still use class attributes as defaults — the *value* is live, the *annotation* is a string.

### Lines 14–17: Forward references

```python
def get_ticket(id: int) -> Ticket:
    return Ticket(id=id, title="x")


class Ticket:
    id: int
    title: str
```

`get_ticket`'s return annotation is `Ticket` (no quotes) — a *forward reference*, because `Ticket` is defined *after* `get_ticket` in the module. Without `from __future__ import annotations`, this file would fail at module-import time with `NameError: name 'Ticket' is not defined` — the annotation `-> Ticket` would be evaluated eagerly, and `Ticket` does not exist yet. With `from __future__ import annotations`, the `-> Ticket` annotation is stored as the string `"Ticket"` in `get_ticket.__annotations__["return"]`. FastAPI, at request time, calls `get_type_hints(get_ticket)` which resolves `"Ticket"` against `get_ticket.__globals__`, finds the `Ticket` class (now defined), and proceeds. The future import unifies the explicit-string form (`-> "Ticket"`) and the bare form (`-> Ticket`) — both end up as the string `"Ticket"` after resolution. The bare form is the modern idiom; the explicit-string form was the only forward-reference option before 3.7.

**Why does `from __future__ import annotations` let you drop the quotes on forward references?**

Because the future import makes *every* annotation a string at the source level — the annotation is already going to be a string in `__annotations__`, so wrapping it in quotes is redundant. The future import is the "all annotations are forward references" mode. Note that the *stored* form differs by call site: `-> Ticket` (no quotes) becomes the string `"Ticket"`; `-> "Ticket"` (with quotes) becomes the string `"'Ticket'"` (with the inner quotes preserved, because the future import reconstructs the source expression verbatim). At resolution time, `get_type_hints()` `eval`s both forms against the appropriate scope and gets the same `Ticket` class — the inner quotes make no semantic difference at runtime. The bare form is preferred because it is shorter and is the form PEP 649 (3.14) preserves as the default behaviour.

### Lines 19–23: Inspecting `__annotations__`

```python
if __name__ == "__main__":
    print("Project.__annotations__:", Project.__annotations__)
    print("get_ticket.__annotations__:", get_ticket.__annotations__)
```

`Project.__annotations__` is `{"id": "int", "name": "str", "archived": "bool"}` — strings. `get_ticket.__annotations__` is `{"id": "int", "return": "Ticket"}` — strings. The `id` key holds the parameter annotation; the `return` key holds the return annotation (which is the string `"Ticket"` because we wrote `-> Ticket` without quotes — the future import reconstructs the source expression as a string).

**Why does `get_ticket.__annotations__` have a `"return"` key but not all parameters?**

Because `__annotations__` only contains *annotated* parameters. `id: int` is annotated, so `id` is in the dict. An un-annotated parameter (e.g., `def f(x, y: int)`) only has `y` in `__annotations__`, not `x`. The `"return"` key is added when the return annotation is present. `inspect.signature()` is the API that returns *every* parameter (annotated or not) — it is what FastAPI uses to read the full signature, then `get_type_hints()` is called separately to resolve the annotations.

### Lines 25–28: Resolution via `get_type_hints`

```python
    print("\nresolved via get_type_hints:")
    print("  Project hints:", get_type_hints(Project))
    print("  get_ticket hints:", get_type_hints(get_ticket))
```

`get_type_hints(Project)` returns `{"id": int, "name": str, "archived": bool}` — actual type objects. `get_type_hints(get_ticket)` returns `{"return": Ticket, "id": int}` — `Ticket` is the class, `int` is the type. The function resolved every string against the appropriate scope: for a class, against the class's module globals; for a function, against the function's `__globals__`. The resolution uses `ForwardRef` internally — for each annotation string, `typing` constructs a `ForwardRef(string)` and then evaluates it via `eval(string, globalns, localns)`. The result is the type object.

**Why does FastAPI call `get_type_hints(func, include_extras=True)` and not just `func.__annotations__`?**

Three reasons. First, `__annotations__` is strings (with the future import) — FastAPI needs types. Second, `__annotations__` does not include un-annotated parameters; `inspect.signature()` does. Third, `__annotations__` does not preserve `Annotated[T, metadata]` metadata — by default, `get_type_hints()` strips the metadata and returns `T` (the bare type). The `include_extras=True` flag preserves the metadata, which is what FastAPI needs to find the `Depends(...)`, `Field(...)`, `Body(...)` markers in `Annotated[int, Depends(get_db)]`. Without `include_extras=True`, FastAPI would see `int` and not find the `Depends` — the dependency would not be injected. This is why the FastAPI source always calls `get_type_hints(func, include_extras=True)`.

### The `ForwardRef` mechanism (deep dive)

When `get_type_hints()` walks `__annotations__`, for each string it constructs a `ForwardRef`:

```python
ref = typing.ForwardRef("Ticket")
```

Then it calls `ref._evaluate(globalns, localns, frozenset())` — which internally does:

```python
code = compile("Ticket", "<string>", "eval")
return eval(code, globalns, localns)
```

The `globalns` is `func.__globals__` for functions, the module's `__dict__` for classes. The `localns` is whatever was passed to `get_type_hints()` (typically `None`, which means `globalns` is used). The `eval` resolves the string `"Ticket"` to the type object `Ticket` *at call time* — which is why the forward reference works: by the time `get_type_hints()` is called (at request time, for FastAPI), `Ticket` is in the module's globals.

**Why does `ForwardRef` use `eval` rather than a custom parser?**

Because the annotation can be *any* Python expression — `list[int]`, `Annotated[int, Field(gt=0)]`, `Callable[[int, str], None]`, `"Ticket" | None` (PEP 604 union). Writing a custom parser for all of these would duplicate the Python grammar. `eval` reuses the language's parser and evaluates the expression in the appropriate scope. The cost is one `compile` per annotation per call — significant at high throughput but cached in some paths (Pydantic caches the resolved hints at class-creation time; FastAPI's `get_type_hints` call is per-route-resolution, not per-request, because of `lru_cache`).

## Execution Trace

```bash
$ python boardly/typing_demo/future_annotations.py
Project.__annotations__: {'id': 'int', 'name': 'str', 'archived': 'bool'}
get_ticket.__annotations__: {'id': 'int', 'return': 'Ticket'}

resolved via get_type_hints:
  Project hints: {'id': <class 'int'>, 'name': <class 'str'>, 'archived': <class 'bool'>}
  get_ticket hints: {'id': <class 'int'>, 'return': <class '__main__.Ticket'>}
```

The `__annotations__` values are strings (`'int'`, `'str'`, `'bool'`, `'Ticket'`). The `get_type_hints` values are types (`int`, `str`, `bool`, `Ticket`). The `Ticket` class is shown as `<class '__main__.Ticket'>` — fully resolved from the string `"Ticket"` against `get_ticket.__globals__`. The `__annotations__` dict order follows source order — parameter annotation (`id`) first, then the `return` key.

## Common Mistakes

### Mistake 1: Reading `__annotations__` and assuming types

```python
from __future__ import annotations

def f(x: int) -> str: ...

print(f.__annotations__["return"])  # 'str', not the str type
print(f.__annotations__["return"] is str)  # False
```

**Symptom:** Code that uses `f.__annotations__["return"]` as a type (e.g., `isinstance(value, f.__annotations__["return"])`) raises `TypeError: isinstance() arg 2 must be a type ...`.
**Why:** `__annotations__` values are strings under the future import, not types.
**Fix:** Use `get_type_hints(f)["return"]` to get the resolved type.

### Mistake 2: Forward reference to a name not in scope at `get_type_hints()` time

```python
from __future__ import annotations

def f(x: "LocalType") -> None: ...

def make():
    class LocalType: ...
    return f

f_resolved = make()
get_type_hints(f_resolved)  # NameError: name 'LocalType' is not defined
```

**Symptom:** `NameError: name 'LocalType' is not defined` from `get_type_hints()`.
**Why:** `f.__globals__` does not include `LocalType` (which was defined inside `make`). The string `"LocalType"` cannot be resolved at `eval` time.
**Fix:** Define `LocalType` at module level, or pass `localns={"LocalType": LocalType}` to `get_type_hints()`. Lesson 03 walks this in detail.

### Mistake 3: Expecting `Annotated[T, metadata]` to be preserved in `__annotations__`

```python
from __future__ import annotations
from typing import Annotated

def f(x: Annotated[int, "meta"]) -> None: ...

print(f.__annotations__)  # {'x': 'Annotated[int, "meta"]'}
print(get_type_hints(f))  # {'x': int}  -- metadata STRIPPED
print(get_type_hints(f, include_extras=True))  # {'x': Annotated[int, 'meta']}  -- preserved
```

**Symptom:** `get_type_hints(f)` returns `int` (the bare type), not `Annotated[int, "meta"]` — the metadata is gone.
**Why:** `get_type_hints()` *by default* strips `Annotated` wrappers and returns the bare type. The `include_extras=True` flag is required to preserve the metadata.
**Fix:** Always pass `include_extras=True` when you need the metadata (FastAPI, Pydantic, attrs all do this).

## Engineering Trade-Offs

**Decision:** Add `from __future__ import annotations` at the top of every `boardly` module that uses type hints. Use `get_type_hints(obj, include_extras=True)` whenever resolving annotations at runtime.
**Both sides:** The alternative is to omit the import and use explicit `"ForwardRef"` strings — but this is noisier (every forward ref needs quotes), does not unify the forward-ref and bare-annotation forms, and does not enable the 3.14 deferred-evaluation migration path. The future import is the modern default.
**Commitment:** In `boardly`, every module that defines types or functions with annotations starts with `from __future__ import annotations`. The convention is enforced by a lint rule. In 3.14, when PEP 649 becomes the default, the import becomes a no-op — but keeping it does no harm and provides the 3.12/3.13 forward-compat path.

## Exercises

1. **Exercise 1 — Compare with and without the import.** Comment out `from __future__ import annotations` and re-run. Observe the `NameError` from the forward reference. Explain why. `Verify: python boardly/typing_demo/future_annotations.py`
2. **Exercise 2 — `Annotated` metadata.** Add `from typing import Annotated` and a function `def f(x: Annotated[int, "meta"]) -> None:`. Run `get_type_hints(f)` and `get_type_hints(f, include_extras=True)`. Observe the difference. `Verify: python boardly/typing_demo/future_annotations.py`
3. **Exercise 3 — `ForwardRef` directly.** Construct `from typing import ForwardRef; ref = ForwardRef("int"); print(ref._evaluate(globals(), locals(), frozenset()))` — manually resolve the string. `Verify: python -c "from typing import ForwardRef; print(ForwardRef('int')._evaluate(globals(), locals(), frozenset()))"`
4. **Exercise 4 — Local-type failure.** Define a local class inside a function and use it as an annotation. Call `get_type_hints()` and observe the `NameError`. `Verify: python boardly/typing_demo/future_annotations.py`
5. **Exercise 5 — `localns` workaround.** Pass `localns={"LocalType": LocalType}` to `get_type_hints()` and verify the local-type annotation resolves. `Verify: python boardly/typing_demo/future_annotations.py`

## Verification

```bash
$ python boardly/typing_demo/future_annotations.py
Project.__annotations__: {'id': 'int', 'name': 'str', 'archived': 'bool'}
get_ticket.__annotations__: {'id': 'int', 'return': 'Ticket'}

resolved via get_type_hints:
  Project hints: {'id': <class 'int'>, 'name': <class 'str'>, 'archived': <class 'bool'>}
  get_ticket hints: {'id': <class 'int'>, 'return': <class '__main__.Ticket'>}
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `__annotations__` is the dict Python populates from your hints; this lesson shows what changes when the future import is in scope.
- [[01-typing/11-typing-vs-runtime]] — `get_type_hints()` vs `__annotations__` — the two APIs that diverge under the future import.

## What's Next

[[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] — the saga. PEP 563 was the 3.7 opt-in that was supposed to become the 3.10 default; the default was deferred indefinitely because of the failure modes this lesson previews. PEP 649 is the proper fix — deferred evaluation via `__annotate__`, default in 3.14. PEP 749 is the 3.14 implementation refinement. Three things to take with you:

- `from __future__ import annotations` stores every annotation as a string in `__annotations__`.
- `get_type_hints(obj, include_extras=True)` is what FastAPI/Pydantic call to resolve them — and `include_extras` is required to preserve `Annotated` metadata.
- The resolution uses `ForwardRef._evaluate()` which calls `eval()` against `obj.__globals__` — a `NameError` is the failure mode if a name is not in scope.

## Sources

- **`__future__.annotations`** — https://docs.python.org/3/library/__future__.html — accessed 2026-10-23 — the canonical reference for the future statement.
- **`typing.get_type_hints`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the resolution function FastAPI calls on every route.
- **`typing.ForwardRef`** — https://docs.python.org/3/library/typing.html#typing.ForwardRef — accessed 2026-10-23 — the internal class that wraps and resolves annotation strings.
- **PEP 563 — Postponed evaluation of annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the PEP that introduced the future import, with the implementation rationale.

## What We Learned

- You can explain what `from __future__ import annotations` does at the bytecode level — annotations are stored as strings, not evaluated.
- You can read `__annotations__` and predict whether you will get types or strings.
- You can explain why FastAPI calls `typing.get_type_hints(func, include_extras=True)` on every route signature.
- You can trace the `ForwardRef` resolution mechanism — the string is wrapped, then `eval`'d against `func.__globals__`.
- You can predict the `NameError` failure mode — when a forward-referenced name is not in `func.__globals__`.
