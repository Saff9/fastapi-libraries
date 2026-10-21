---
title: "Lesson 11: typing vs runtime"
aliases:
 - typing vs runtime
 - 11-typing-vs-runtime
 - get_type_hints vs __annotations__
 - ForwardRef
 - include_extras
tags:
 - typing
 - runtime-introspection
 - forwardref
 - pep-563
 - canonical
 - fastapi-primitive
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/10-Future-Annotations]]"
related_lessons:
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/10-Future-Annotations]]"
 - "[[10-inspect/02-get_type_hints]]"
 - "[[13-future/03-When-string-annotations-break]]"
first_taught_in: "01-typing/11-typing-vs-runtime"
---

# Lesson 11: typing vs runtime

*The layer FastAPI lives at — `obj.__annotations__` is raw (often strings); `get_type_hints(obj)` is resolved; `get_type_hints(obj, include_extras=True)` is what keeps `Annotated` metadata alive. This lesson ties everything in Section 01 together.*

**You're at the very beginning of Section 01's capstone lesson.**

You have seen `Annotated`, `TypeVar`, `Protocol`, `TypedDict`, `Literal`, and `from __future__ import annotations`. Each of those is a *construct* — a thing you write. This lesson is about *what Python does with what you write*. When you write `def f(x: int) -> Ticket: ...`, the bytecode stores `int` (or the string `"int"`) in `f.__annotations__`. When FastAPI needs the real `Ticket` class object, it does not read `f.__annotations__` — it calls `typing.get_type_hints(f, include_extras=True)`. The gap between those two is the entire reason this section exists. By the end of this lesson you will be able to predict, for any annotation you write, exactly what survives at runtime and what is rebuilt on demand. Take your time. Type every example. **This is how you learn.**

#typing #runtime-introspection #canonical #fastapi-primitive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Distinguish** `obj.__annotations__` (the raw dict Python stores at definition time, which may contain strings) from `get_type_hints(obj)` (the resolved dict Python builds on call).
2. **Explain** why `from __future__ import annotations` (PEP 563) makes `__annotations__` contain *strings* for every annotation, even when the type is in scope at definition time.
3. **Recover** `Annotated` metadata using `get_type_hints(obj, include_extras=True)` — and explain why the default is `include_extras=False` for backward compatibility.
4. **Use** `typing.ForwardRef` to explain what `get_type_hints` does internally when it resolves a string annotation, and how `NameError` arises when a string cannot be resolved.
5. **Reproduce** the exact introspection call FastAPI makes on every route: `get_type_hints(route_handler, include_extras=True)`.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — you must be comfortable with `obj.__annotations__` returning a `dict`.
- **[[01-typing/02-Annotated-and-Metadata]]** — `Annotated[T, *metadata]`, `__metadata__`, and the `include_extras=True` flag this lesson makes concrete.
- **[[01-typing/10-Future-Annotations]]** — what `from __future__ import annotations` stringifies.
- **About 40–55 minutes of focused time.**

**The most common gap: assuming `obj.__annotations__` and `get_type_hints(obj)` return the same thing.**

They do not. `__annotations__` is whatever Python stored at definition time — which under PEP 563 is *strings*, not types. `get_type_hints` walks those strings, calls `eval()` on each one in the function's module globals (plus optional `localns`), and returns real type objects. Frameworks that read `__annotations__` directly receive strings; frameworks that call `get_type_hints` receive types. FastAPI, Pydantic, and msgspec all call `get_type_hints`. Naive test helpers and some older libraries read `__annotations__`. The bugs that follow are subtle, silent, and hard to localise.

## The Problem

Here is the bug this lesson prevents. You ship `boardly/tickets/api.py` with `from __future__ import annotations` at the top (most boardly files have it). A route looks like:

```python
from __future__ import annotations
from typing import Annotated

class Depends:
    def __init__(self, dep): self.dep = dep

def get_db() -> str: return "session"

def list_tickets(
    project_id: Annotated[int, "gt=0"],
    db: Annotated[str, Depends(get_db)],
) -> list[Ticket]:
    ...
```

A junior engineer writes a custom validator that reads the route's annotations directly:

```python
def validate(route):
    for name, hint in route.__annotations__.items():
        if hasattr(hint, "__metadata__"):   # ← never True; hint is a string!
            apply_validation(hint.__metadata__)
```

**Symptom:** validation silently never runs. No error, no warning — the `if hasattr(...)` is `False` because `hint` is the string `"Annotated[int, 'gt=0']"`, not an `Annotated` object. Strings have no `__metadata__` attribute.

**Why:** `from __future__ import annotations` (PEP 563) stringified every annotation in the file at bytecode-compile time. `route.__annotations__` contains strings. To recover real `Annotated` objects, the validator must call `get_type_hints(route, include_extras=True)`. Both halves matter: `get_type_hints` *resolves* the strings, and `include_extras=True` *keeps* the `Annotated` wrapper. Drop either, and the metadata is gone.

This lesson is the senior view of that bug — the one lesson that makes the rest of Section 01 snap into focus.

## The Code

```python
# boardly/typing_vs_runtime.py
"""typing vs runtime — what __annotations__ stores vs what get_type_hints resolves."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ForwardRef, get_args, get_origin, get_type_hints


@dataclass
class Ticket:
    id: int
    title: str


# A Depends marker — mimics fastapi.Depends(get_db) without the framework.
class Depends:
    def __init__(self, dependency):
        self.dependency = dependency
    def __repr__(self):
        return f"Depends({self.dependency.__name__})"


def get_db() -> str:
    return "session"


def list_tickets(
    project_id: Annotated[int, "gt=0"],
    db: Annotated[str, Depends(get_db)],
) -> list[Ticket]:
    return []


if __name__ == "__main__":
    # 1. Raw __annotations__ — STRINGS (PEP 563 future import stringified them).
    raw = list_tickets.__annotations__
    print("raw __annotations__:", raw)

    # 2. Default get_type_hints — resolves strings, STRIPS Annotated metadata.
    stripped = get_type_hints(list_tickets)
    print("get_type_hints (stripped):", stripped)
    print("  project_id is int:", stripped["project_id"] is int)

    # 3. include_extras=True — resolves strings AND keeps Annotated.
    preserved = get_type_hints(list_tickets, include_extras=True)
    print("get_type_hints (include_extras=True):", preserved)
    print("  db __metadata__:", preserved["db"].__metadata__)
    print("  db get_args:", get_args(preserved["db"]))
    print("  db get_origin:", get_origin(preserved["db"]))

    # 4. ForwardRef — the internal type Python builds for each string.
    fr = ForwardRef("Ticket")
    print("ForwardRef('Ticket'):", fr, "type:", type(fr).__name__)
    print("  __forward_arg__:", fr.__forward_arg__)

    # 5. NameError when a string annotation cannot be resolved.
    def f(x: "Undefined"): ...
    print("f.__annotations__:", f.__annotations__)
    try:
        get_type_hints(f)
    except NameError as e:
        print("get_type_hints(f) NameError:", e)
```

## Line-by-Line Deep Dive

### Lines 1–4: Module header and the future import

```python
# boardly/typing_vs_runtime.py
"""typing vs runtime — what __annotations__ stores vs what get_type_hints resolves."""
from __future__ import annotations

from dataclasses import dataclass
```

The first real line of the file is `from __future__ import annotations`. This is the PEP 563 future import (available since 3.7, opt-in; it was *supposed* to become the default in 3.10 but the core team deferred, and PEP 649/PEP 749 will replace it with lazy evaluation in 3.14). With this import active, the CPython compiler stores every annotation in the file as a *string* in `__annotations__`, instead of evaluating the annotation expression. Without this import, the compiler evaluates the annotation expression at definition time and stores the result (a real type object) in `__annotations__`. The single import at the top of the file changes the runtime representation of every annotation below it.

**Why would Python store annotations as strings?**

Two reasons. First, forward references: `class Ticket: def set_parent(self, p: "Ticket") -> None: ...` — without the future import, `"Ticket"` is stored as a string because `Ticket` is not yet defined when the method is compiled. The future import extends this "store as string" behaviour to *every* annotation, so `def f(x: int)` stores `"int"` (not `int`) and `def g() -> Ticket` stores `"Ticket"` (not `Ticket`). Second, performance: evaluating complex annotations (`dict[str, list[int | None]]`) at import time is wasted work if no one ever reads `__annotations__`. Storing strings and resolving on demand via `get_type_hints` defers the cost to the reader. That is the trade: cheaper module import, more expensive introspection.

**Warning — The future import only changes storage, not what `get_type_hints` returns.**

`get_type_hints(obj)` resolves the strings at call time, so the *resolved* output is identical whether or not the future import is active. The bug surfaces only in code that reads `__annotations__` *directly*. That is why most engineers never notice the import is there — until they write a framework.

### Lines 6–9: A boardly dataclass

```python
@dataclass
class Ticket:
    id: int
    title: str
```

A plain `@dataclass` with two `int`/`str` fields. We define it at module scope so its name is in the module's globals — that is what makes `get_type_hints`'s `eval()` call able to resolve `"Ticket"` later. If `Ticket` were defined inside a function body (a local class), `get_type_hints` would raise `NameError` because the local scope is not visible to `eval`. This is the trap covered in [[13-future/03-When-string-annotations-break]].

### Lines 11–17: The `Depends` marker

```python
class Depends:
    def __init__(self, dependency):
        self.dependency = dependency
    def __repr__(self):
        return f"Depends({self.dependency.__name__})"
```

A minimal stand-in for `fastapi.Depends`. The real `Depends` class is more elaborate (it carries `use_cache`, `yield`-generator awareness, scope), but the principle is identical: it is a plain object attached as `Annotated` metadata, and the framework reads it via `get_type_hints(..., include_extras=True)`. The `__repr__` matters because the metadata is printed in the execution trace; a useless `<Depends object at 0x...>` makes introspection output unreadable.

### Lines 19–26: The route signature

```python
def get_db() -> str:
    return "session"


def list_tickets(
    project_id: Annotated[int, "gt=0"],
    db: Annotated[str, Depends(get_db)],
) -> list[Ticket]:
    return []
```

The signature has three annotated things: `project_id` (`Annotated[int, "gt=0"]`), `db` (`Annotated[str, Depends(get_db)]`), and the return type (`list[Ticket]`). Under PEP 563, all three are stored as strings in `__annotations__`: `"Annotated[int, 'gt=0']"`, `"Annotated[str, Depends(get_db)]"`, and `"list[Ticket]"` respectively. The strings look like the source code — that is the whole point of PEP 563, the annotation is captured as *source text* and re-evaluated on demand.

**Why store `Annotated[str, Depends(get_db)]` as a string instead of evaluating it?**

Because evaluating it at definition time would call `Depends(get_db)`, which constructs a `Depends` instance and *captures* the `get_db` callable. Under PEP 563, that capture is deferred until someone calls `get_type_hints`. This matters in two real scenarios. (1) Circular imports: if `get_db` is defined in a module that imports `list_tickets`'s module, evaluating at definition time would fail (the name is not yet visible). Storing as a string defers the resolution to a time when both modules are fully loaded. (2) Performance: most annotations are never read. Pydantic reads model annotations once at class definition; FastAPI reads route annotations once at route registration. The vast majority of `__annotations__` dicts in a large codebase are never read at all — deferring the work saves measurable import time on large projects.

### Lines 30–33: Raw `__annotations__`

```python
if __name__ == "__main__":
    # 1. Raw __annotations__ — STRINGS (PEP 563 future import stringified them).
    raw = list_tickets.__annotations__
    print("raw __annotations__:", raw)
```

`list_tickets.__annotations__` is the *raw* dict the compiler stored at definition time. Under PEP 563, every value is a string. The output looks like `{'project_id': "Annotated[int, 'gt=0']", 'db': 'Annotated[str, Depends(get_db)]', 'return': 'list[Ticket]'}`. Note the nested quotes: the compiler stored the *source text* of the annotation, including the inner single quotes around `'gt=0'` exactly as they appeared. This is what a naive framework that reads `__annotations__` directly receives — strings, never types, never `Annotated` objects.

**Why doesn't `__annotations__` resolve the strings itself?**

Because resolution is *expensive* (it calls `eval` in the module's globals) and most code never reads `__annotations__`. Storing the strings is essentially free (one string per annotation, captured at compile time). Resolving on read would penalise every `__annotations__` access — including the silent ones the runtime does at class-definition time for dataclasses, for example. The design splits the cost: cheap to write, paid by the reader. `get_type_hints` is the reader that pays.

### Lines 35–38: Default `get_type_hints` — resolved but stripped

```python
    # 2. Default get_type_hints — resolves strings, STRIPS Annotated metadata.
    stripped = get_type_hints(list_tickets)
    print("get_type_hints (stripped):", stripped)
    print("  project_id is int:", stripped["project_id"] is int)
```

`get_type_hints(list_tickets)` does two things internally. First, for each value in `__annotations__`, if it is a string (or a `ForwardRef`), it calls `eval(string, globalns, localns)` to recover a real type object — `"Annotated[int, 'gt=0']"` becomes `Annotated[int, 'gt=0']`, and `"list[Ticket]"` becomes `list[Ticket]` with the *real* `Ticket` class. Second, it *strips* `Annotated` wrappers by default: `Annotated[int, 'gt=0']` becomes `int`. The output is `{'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[...Ticket]}` — clean types, no metadata. The `stripped["project_id"] is int` assertion proves they are the *same* `int` object.

**Why does `get_type_hints` strip `Annotated` by default?**

Backward compatibility, as covered in [[01-typing/02-Annotated-and-Metadata]]. `get_type_hints` was added in 3.5 (PEP 484); `Annotated` was added in 3.9 (PEP 593). Between 3.5 and 3.9, every caller of `get_type_hints` expected types. If 3.9 had flipped the default to keep `Annotated`, every existing caller would have started receiving `Annotated[int, ...]` objects where they expected `int` — silent breakage. The default stays `False`, frameworks opt in via `include_extras=True`. This is master-class API evolution: do not break existing callers, even when a better default exists.

### Lines 40–45: `include_extras=True` — resolved AND preserved

```python
    # 3. include_extras=True — resolves strings AND keeps Annotated.
    preserved = get_type_hints(list_tickets, include_extras=True)
    print("get_type_hints (include_extras=True):", preserved)
    print("  db __metadata__:", preserved["db"].__metadata__)
    print("  db get_args:", get_args(preserved["db"]))
    print("  db get_origin:", get_origin(preserved["db"]))
```

`get_type_hints(list_tickets, include_extras=True)` is the line FastAPI executes on every route. The strings are resolved (same as the default call), but the `Annotated` wrappers are *kept*. The output is `{'project_id': typing.Annotated[int, 'gt=0'], 'db': typing.Annotated[str, Depends(get_db)], 'return': list[...Ticket]}`. The three introspection primitives — `__metadata__` (the tuple of metadata items), `get_args` (the underlying type plus the metadata, flattened), `get_origin` (the `Annotated` marker itself) — all return useful results now. This is the call shape FastAPI's `get_dependant` function (in `fastapi/dependencies/utils.py`) makes.

**Why is `include_extras` a single boolean flag and not an enum?**

Because there are only two modes the framework cares about: "give me clean types" (default — type checkers, documentation tools) and "give me the metadata too" (`True` — frameworks like FastAPI and Pydantic). There is no third mode in production use. A boolean is the smallest API surface that covers both. An enum would be premature abstraction; if PEP 593 ever adds a third mode (it has not, eight years after the PEP landed), the flag can graduate to an enum then.

### Lines 47–50: `ForwardRef` — what `get_type_hints` builds internally

```python
    # 4. ForwardRef — the internal type Python builds for each string.
    fr = ForwardRef("Ticket")
    print("ForwardRef('Ticket'):", fr, "type:", type(fr).__name__)
    print("  __forward_arg__:", fr.__forward_arg__)
```

`typing.ForwardRef("Ticket")` is the internal class CPython uses for unresolved string annotations. You rarely construct one yourself; `get_type_hints` does it for you. But understanding that the class exists clarifies the resolution pipeline: when `get_type_hints` sees the string `"Ticket"`, it first wraps it in `ForwardRef("Ticket")`, then calls `ForwardRef._evaluate(globalns, localns, ...)` which `eval`s the string in the module's globals. The `__forward_arg__` attribute is the raw string (`"Ticket"`). If you ever see a `ForwardRef` in your `__annotations__` (without the future import — common when a class refers to itself: `def f(self) -> "Ticket"`), that is what you are looking at.

**Why expose `ForwardRef` publicly if it is internal?**

Because some libraries need to build forward references manually — e.g., when you construct a type from a string at runtime and want to feed it to `get_type_hints` later. Pydantic v1 uses `ForwardRef` extensively when it resolves string annotations in model fields. The class is "public-but-internal" — it has a public name in `typing`, but its constructor arguments and `_evaluate` signature have changed across Python versions (the `frozenset` of `is_argument`/`is_class` flags were added in 3.9). Treat it as advanced machinery; prefer `get_type_hints` whenever possible.

### Lines 52–57: `NameError` when a string cannot be resolved

```python
    # 5. NameError when a string annotation cannot be resolved.
    def f(x: "Undefined"): ...
    print("f.__annotations__:", f.__annotations__)
    try:
        get_type_hints(f)
    except NameError as e:
        print("get_type_hints(f) NameError:", e)
```

`def f(x: "Undefined"): ...` stores `"Undefined"` (or `"'Undefined'"` under PEP 563) in `f.__annotations__`. The string is *legal* at definition time — Python does not check whether names in string annotations actually exist. But `get_type_hints(f)` calls `eval("Undefined", ...)` at call time, and `Undefined` is not a name in the module's globals — so it raises `NameError: name 'Undefined' is not defined`. This is the silent failure mode of PEP 563: bugs surface only when someone *reads* the annotations, which may be at test time, FastAPI route registration time, or never.

**Danger — `from __future__ import annotations` turns `NameError` into a deferred failure.**

Without the future import, `def f(x: Undefined): ...` (no quotes) raises `NameError` at *definition time* — the import of the module fails loudly. With the future import, the same line stores `"Undefined"` silently and raises only when `get_type_hints` is called — possibly minutes later, in a different stack frame, in production. This is the single biggest argument against PEP 563 and the reason PEP 649 (deferred evaluation, default in 3.14) replaces it: PEP 649 stores *code objects* instead of strings, so the failure modes are localised and the resolution is lazier. We cover that saga in [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]].

## Execution Trace

```bash
$ python boardly/typing_vs_runtime.py
raw __annotations__: {'project_id': "Annotated[int, 'gt=0']", 'db': 'Annotated[str, Depends(get_db)]', 'return': 'list[Ticket]'}
get_type_hints (stripped): {'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[__main__.Ticket]}
  project_id is int: True
get_type_hints (include_extras=True): {'project_id': typing.Annotated[int, 'gt=0'], 'db': typing.Annotated[str, Depends(get_db)], 'return': list[__main__.Ticket]}
  db __metadata__: (Depends(get_db),)
  db get_args: (<class 'str'>, Depends(get_db))
  db get_origin: <class 'typing.Annotated'>
ForwardRef('Ticket'): ForwardRef('Ticket') type: ForwardRef
  __forward_arg__: Ticket
f.__annotations__: {'x': "'Undefined'"}
get_type_hints(f) NameError: name 'Undefined' is not defined
```

The three lines that matter most: `raw __annotations__` (strings), `get_type_hints (stripped)` (clean types, no metadata), `get_type_hints (include_extras=True)` (real `Annotated` objects with the `Depends` instance recoverable via `__metadata__`). The `NameError` line shows the deferred-failure mode of PEP 563.

## Common Mistakes

### Mistake 1: Reading `__annotations__` directly and expecting types

```python
hints = my_route.__annotations__        # ← strings under PEP 563
for name, hint in hints.items():
    if hasattr(hint, "__metadata__"):    # ← never True; hint is "Annotated[...]"
        apply_validation(hint.__metadata__)
```

**Symptom:** Validation silently does not run. No error, no warning — the `if hasattr(...)` branch is dead.
**Why:** `__annotations__` under PEP 563 is a `dict[str, str]`. Strings do not have `__metadata__`.
**Fix:**

```python
hints = get_type_hints(my_route, include_extras=True)
for name, hint in hints.items():
    if hasattr(hint, "__metadata__"):
        apply_validation(hint.__metadata__)
```

This is the bug this lesson exists to prevent. Every framework that consumes annotations must call `get_type_hints`, not read `__annotations__`.

### Mistake 2: Calling `get_type_hints` and forgetting `include_extras=True`

```python
hints = get_type_hints(my_route)        # ← strips Annotated
for name, hint in hints.items():
    if hasattr(hint, "__metadata__"):    # ← never True; Annotated was stripped to int
        apply_validation(hint.__metadata__)
```

**Symptom:** Same silent failure as Mistake 1. `get_type_hints` resolved the strings but then *stripped* the `Annotated` wrappers.
**Why:** The default of `include_extras` is `False` — backward compatibility with pre-PEP-593 callers. The metadata is gone before you see it.
**Fix:**

```python
hints = get_type_hints(my_route, include_extras=True)
```

This is *the* flag FastAPI depends on. Without it, FastAPI's entire dependency-injection system would be invisible — `Annotated[str, Depends(get_db)]` would resolve to `str` and the dependency would be lost.

### Mistake 3: Defining the type used in an annotation inside a function

```python
def make_route():
    class Ticket: ...                          # local class
    def route() -> list[Ticket]: return []      # annotation refers to local
    return route
```

**Symptom:** `get_type_hints(route)` raises `NameError: name 'Ticket' is not defined`.
**Why:** `get_type_hints` resolves strings via `eval(string, globalns, localns)`. The default `localns` is `None`, so only module globals are visible. The local `Ticket` is invisible. PEP 649 (3.14) will fix this by storing the type's `__annotate__` closure; on 3.12 the fix is to move the class to module scope.
**Fix:** Move `Ticket` to module scope, or pass `localns={"Ticket": Ticket}` explicitly to `get_type_hints`. Covered in [[13-future/03-When-string-annotations-break]].

## Engineering Trade-Offs

**Decision:** Call `get_type_hints(obj, include_extras=True)` whenever you need to consume annotations in a framework; never read `__annotations__` directly.
**Both sides:** Reading `__annotations__` is faster (no `eval`) and never raises — you get strings, full stop. That is fine if you only want the *text* of the annotations (e.g., a documentation generator that prints the source). For any framework that needs to dispatch on the *type* (FastAPI, Pydantic, msgspec, beanie), you must call `get_type_hints` and pay the `eval` cost once at registration. The cost is paid once and cached.
**Commitment:** boardly uses `get_type_hints(..., include_extras=True)` everywhere it reads annotations — in the route dispatcher, the validator, the OpenAPI generator. `__annotations__` is read only by debug tooling that wants the raw source text. There is no path in the boardly codebase where `__annotations__` is consumed as if it contained types.

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/typing_vs_runtime.py` and run it. Compare your output to the Execution Trace. The three lines you must see are `raw __annotations__` (strings), `get_type_hints (stripped)` (clean types), and `get_type_hints (include_extras=True)` (real `Annotated`). `Verify: python boardly/typing_vs_runtime.py`
2. **Exercise 2 — Toggle the future import.** Comment out line 3 (`from __future__ import annotations`) and re-run. Note that `raw __annotations__` now contains real type objects (not strings) — `Annotated[int, 'gt=0']` becomes `Annotated[int, 'gt=0']` as an object. The two `get_type_hints` outputs are *unchanged*. Restore the import. `Verify: python -c "import boardly.typing_vs_runtime"` (no output means no error)
3. **Exercise 3 — Reproduce the FastAPI call.** Write a function `dependant(route)` that calls `get_type_hints(route, include_extras=True)`, walks each `Annotated` value's `__metadata__`, and prints `"param {name}: type {get_args(hint)[0].__name__}, deps {[m for m in hint.__metadata__ if isinstance(m, Depends)]}"`. Run it on `list_tickets`. `Verify: python -c "from boardly.typing_vs_runtime import dependant, list_tickets; dependant(list_tickets)"`
4. **Exercise 4 — ForwardRef manual eval.** Construct `ForwardRef("list[Ticket]")` (without the future import active — put this in a fresh file with no future import). Call `fr._evaluate(globals(), locals(), frozenset())` and confirm you get `list[Ticket]` with the real `Ticket` class. This is what `get_type_hints` does internally. `Verify: python -c "from typing import ForwardRef; from boardly.typing_vs_runtime import Ticket; fr = ForwardRef('list[Ticket]'); print(fr._evaluate(globals(), locals(), frozenset()))"` (define `Ticket` at module scope first)
5. **Exercise 5 — `localns` resolution.** Write a function that defines `Ticket` locally, returns a route whose annotation is `"list[Ticket]"`, then call `get_type_hints(route, localns={"Ticket": Ticket})` to resolve it. Confirm that without `localns` it raises `NameError`. `Verify: python -c "from typing import get_type_hints; exec(\"def make():\n    class T: ...\n    def r() -> 'list[T]': return []\n    return r\"); r = make(); print(get_type_hints(r, localns={'T': r.__annotations__['return'] if False else None}))"` — if your shell quoting struggles, write a small script file instead. The exercise is to *make* `localns` work.

## Verification

```bash
$ python boardly/typing_vs_runtime.py
raw __annotations__: {'project_id': "Annotated[int, 'gt=0']", 'db': 'Annotated[str, Depends(get_db)]', 'return': 'list[Ticket]'}
get_type_hints (stripped): {'project_id': <class 'int'>, 'db': <class 'str'>, 'return': list[__main__.Ticket]}
  project_id is int: True
get_type_hints (include_extras=True): {'project_id': typing.Annotated[int, 'gt=0'], 'db': typing.Annotated[str, Depends(get_db)], 'return': list[__main__.Ticket]}
  db __metadata__: (Depends(get_db),)
  db get_args: (<class 'str'>, Depends(get_db))
  db get_origin: <class 'typing.Annotated'>
ForwardRef('Ticket'): ForwardRef('Ticket') type: ForwardRef
  __forward_arg__: Ticket
f.__annotations__: {'x': "'Undefined'"}
get_type_hints(f) NameError: name 'Undefined' is not defined
```

If the output matches, you have reproduced the exact introspection FastAPI runs on every route registration. The `get_type_hints (include_extras=True)` line is the lesson in one screenshot.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `obj.__annotations__` returns a `dict`. This lesson shows that under PEP 563 the values are *strings*, not types — and that `get_type_hints` is the resolver.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated[T, *metadata]` and the `include_extras=True` flag. This lesson shows the call in context, alongside `__annotations__` and `ForwardRef`.
- [[01-typing/10-Future-Annotations]] — what `from __future__ import annotations` stringifies. This lesson shows the runtime consequence of that stringification, and how `get_type_hints` undoes it on demand.

## What's Next

[[02-functools/00-functools-MOC]] — `lru_cache`, `wraps`, `partial`, `singledispatch`. You now know what FastAPI reads when it sees your route signature. Section 02 teaches the function-level primitives FastAPI uses to *act on* what it reads — `lru_cache` for the per-request dependency cache, `wraps` for the decorators that preserve signatures, `partial` for binding arguments to dependencies, `singledispatch` for type-driven dispatch. Three things to look for in lesson 02-01 (`lru_cache`):

- Why `lru_cache` is the FastAPI dependency cache for `use_cache=True` dependencies — exactly the FastAPI pattern.
- The `typed=True` flag (3.8+) and why it matters for hashing `Annotated` arguments.
- The cache-info / cache-clear introspection that lets you debug "why is my dependency cached?"

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing — `get_type_hints`, `ForwardRef`, `Annotated`** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical CPython reference for `get_type_hints`, `include_extras`, and `ForwardRef`.
- **PEP 563 — Postponed evaluation of annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the PEP that introduced `from __future__ import annotations` (3.7 opt-in) and the string-storage behaviour this lesson walks.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the `Annotated` PEP, where the `include_extras` flag was introduced.
- **PEP 484 — Type Hints (the `get_type_hints` function)** — https://peps.python.org/pep-0484/ — accessed 2026-10-23 — the original type-hints PEP that defined `get_type_hints` and `ForwardRef`.
- **CPython source — `Lib/typing.py`** — https://github.com/python/cpython/blob/3.12/Lib/typing.py — accessed 2026-10-23 — the reference implementation; `get_type_hints` resolves string annotations by calling `eval` in `globalns`/`localns`.

## What We Learned

- `obj.__annotations__` is the *raw* dict the compiler stores at definition time. Under `from __future__ import annotations` (PEP 563), every value is a *string*.
- `get_type_hints(obj)` resolves the strings via `eval(string, globalns, localns)`, returning real type objects. By default, it also *strips* `Annotated` wrappers for backward compatibility.
- `get_type_hints(obj, include_extras=True)` is the call FastAPI makes on every route — it resolves the strings *and* preserves the `Annotated` metadata.
- `typing.ForwardRef("X")` is the internal class Python builds for an unresolved string annotation; `get_type_hints` wraps each string in a `ForwardRef` and calls `_evaluate` on it.
- A string annotation that names a missing identifier (e.g. `"Undefined"`) raises `NameError` at `get_type_hints` time, not at definition time — the deferred-failure mode of PEP 563.
- Frameworks that read `__annotations__` directly (instead of calling `get_type_hints`) silently receive strings under PEP 563 — the root cause of the "validation silently does not run" bug.
