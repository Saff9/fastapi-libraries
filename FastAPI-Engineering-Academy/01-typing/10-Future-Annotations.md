---
title: "Lesson 10: Future Annotations"
aliases:
 - Future Annotations
 - 10-Future-Annotations
 - PEP 563
 - from __future__ import annotations
tags:
 - typing
 - future-annotations
 - pep-563
 - pep-649
 - canonical
 - fastapi-primitive
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/09-Overload]]"
related_lessons:
 - "[[01-typing/11-typing-vs-runtime]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[13-future/00-future-MOC]]"
first_taught_in: "01-typing/10-Future-Annotations"
---

# Lesson 10: Future Annotations

*`from __future__ import annotations` (PEP 563) — every annotation in the file becomes a string at runtime, and `get_type_hints` resolves them lazily. The break that hits FastAPI and Pydantic codebases.*

**You're at the very beginning of Section 01's most subtle lesson.**

You write `def get_ticket(id: int) -> Ticket: ...` and expect `Ticket` to be a real class object in `get_ticket.__annotations__["return"]`. It is — unless the file has `from __future__ import annotations` at the top. With that import, every annotation in the file is stored as a *string* (`"Ticket"` instead of `Ticket`), and `get_type_hints` resolves the strings at call time. PEP 563 introduced this in 3.7 as the future default; PEP 649 (deferred evaluation) replaces it in 3.14. This lesson is canonical because FastAPI and Pydantic v1 break *subtly* under PEP 563 — strings instead of types — and you must know exactly when and why. Take your time. Type every example. **This is how you learn.**

#typing #future-annotations #canonical #fastapi-primitive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Explain** what `from __future__ import annotations` does — every annotation in the file is stored as a string in `__annotations__`.
2. **Use** `get_type_hints` to resolve the strings back to real types — and explain the failure modes (forward refs not in scope, NameError).
3. **Predict** when PEP 563 breaks a framework: when the framework calls `__annotations__` directly (instead of `get_type_hints`), or when it expects real types in `__annotations__`.
4. **Use** `ForwardRef` and understand its role in `get_type_hints`'s internals.
5. **Version-gate** PEP 649 (deferred evaluation, default in 3.14) and explain why it replaces PEP 563.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — `get_type_hints`, `__annotations__`.
- **[[01-typing/02-Annotated-and-Metadata]]** — `include_extras=True` — the flag PEP 563 strings must be paired with.
- **About 40–55 minutes of focused time.**

**The most common gap: assuming `from __future__ import annotations` is purely cosmetic.**

Students arrive having seen the import at the top of many files and assume it is a "use new syntax" import (like `from __future__ import generator_stop`). It is not. It changes the *runtime representation* of every annotation in the file. `def f(x: int) -> None:` without the future import produces `f.__annotations__ == {"x": int, "return": NoneType}` — real type objects. With the future import, the same line produces `f.__annotations__ == {"x": "int", "return": "None"}` — strings. Frameworks that read `__annotations__` directly (instead of calling `get_type_hints`) silently receive strings, which they often cannot handle. This is the source of countless "FastAPI silently does not validate" bugs.

## The Problem

Here is the bug this lesson prevents. boardly has a file with `from __future__ import annotations` at the top:

```python
from __future__ import annotations
from typing import Annotated

class TicketCreate:
    title: Annotated[str, "min_length=1"]
    status: Annotated[str, "default=open"]

# Some custom framework:
def validate(obj):
    hints = obj.__annotations__   # ← reads __annotations__ directly!
    for name, hint in hints.items():
        if hasattr(hint, "__metadata__"):  # ← never True; hint is a string!
            apply_validation(obj, name, hint.__metadata__)
```

The framework reads `__annotations__` directly instead of calling `get_type_hints(include_extras=True)`. Under PEP 563, `hints` is `{"title": "Annotated[str, 'min_length=1']", "status": "Annotated[str, 'default=open']"}` — strings. `hasattr(string, "__metadata__")` is `False`. The validation silently does nothing — no error, no validation applied. The endpoint accepts `{"title": ""}` without complaint.

This is the trap. The fix is to use `get_type_hints(obj, include_extras=True)` — which resolves the strings back to real types and recovers the `Annotated` metadata. FastAPI and Pydantic v2 do this correctly. Pydantic v1 and many custom frameworks historically did not — and broke under `from __future__ import annotations`. The lesson is: never read `__annotations__` directly when you want real types; always use `get_type_hints`.

## The Code

```python
# boardly/future_annotations.py
"""boardly — from __future__ import annotations (PEP 563): annotations become strings."""
from __future__ import annotations   # ← THIS LINE — every annotation below becomes a string.

from typing import get_type_hints, Annotated, ForwardRef

class Ticket:
    # Forward references work even before the class is fully defined.
    def clone(self) -> Ticket:        # ← 'Ticket' is a string under PEP 563; no NameError.
        return Ticket()

    def related(self) -> list[Ticket]:  # ← 'list[Ticket]' is a string too.
        return []

def get_ticket(id: int) -> Ticket:
    return Ticket()

# Annotations are stored as STRINGS in __annotations__.
print("Ticket.__annotations__:", Ticket.__annotations__)
print("get_ticket.__annotations__:", get_ticket.__annotations__)

# get_type_hints resolves the strings back to real types using the module globals.
print("Ticket get_type_hints:", get_type_hints(Ticket.clone))
print("get_ticket get_type_hints:", get_type_hints(get_ticket))

# --- The Pydantic / FastAPI break ---
# When annotations are strings, frameworks that call get_type_hints need:
#   (a) The referenced names to be in scope (globals + locals).
#   (b) include_extras=True to preserve Annotated metadata.
def route(p: Annotated[int, "meta"]) -> None: ...
print("route __annotations__ (string!):", route.__annotations__)
print("route get_type_hints default:", get_type_hints(route))
print("route get_type_hints include_extras:", get_type_hints(route, include_extras=True))

# --- ForwardRef: the object get_type_hints constructs internally ---
fr = ForwardRef("int")
print("ForwardRef:", fr, "arg:", fr.__forward_arg__)
```

## Line-by-Line Deep Dive

### Lines 1–6: The future import and the impact

```python
# boardly/future_annotations.py
"""boardly — from __future__ import annotations (PEP 563): annotations become strings."""
from __future__ import annotations   # ← THIS LINE — every annotation below becomes a string.

from typing import get_type_hints, Annotated, ForwardRef
```

`from __future__ import annotations` (PEP 563, available since 3.7) is a *module-level* import that changes how annotations are stored. Without it, Python evaluates each annotation expression at function-definition time and stores the resulting object. With it, Python stores the *source code text* of the annotation as a string — no evaluation. `def f(x: int) -> Ticket:` produces `f.__annotations__ == {"x": "int", "return": "Ticket"}` — note the quotes around the names; they are strings.

The import *must* be at the top of the file (after the docstring, before any other imports) — `__future__` imports are special and Python checks for them early. The behaviour change applies to *every* annotation in the file — function params, return types, variable annotations, class-level annotations, `TypedDict` fields, `dataclass` fields, all of them.

**Why was PEP 563 introduced?**

Three reasons. (1) **Performance**: evaluating complex type expressions at import time has measurable cost. PEP 563 makes import faster. (2) **Forward references**: with PEP 563, you can write `def f() -> Ticket: ...` even when `Ticket` is defined *after* `f` — no NameError, because the annotation is a string and not evaluated at definition time. (3) **Forward compatibility**: PEP 563 was meant to be the *default* in a future Python (originally 3.10, then deferred to 3.13/3.14). It was the future — and then PEP 649 came along with a better future (lesson 11 covers this).

### Lines 8–15: Forward references "just work"

```python
class Ticket:
    # Forward references work even before the class is fully defined.
    def clone(self) -> Ticket:        # ← 'Ticket' is a string under PEP 563; no NameError.
        return Ticket()

    def related(self) -> list[Ticket]:  # ← 'list[Ticket]' is a string too.
        return []
```

Inside `class Ticket`, the method `clone` returns `Ticket` — a forward reference, because `Ticket` is not yet fully defined when `clone` runs at class-definition time. *Without* PEP 563, this would raise `NameError: name 'Ticket' is not defined` at class-definition time — you would have to write `def clone(self) -> "Ticket":` (with quotes) to delay evaluation. *With* PEP 563, every annotation is already a string — the forward reference is automatic, no quotes needed.

This is the *ergonomic* win of PEP 563: forward references become invisible. You can write `def f() -> User: ...` and define `User` later in the same file — Python never tries to evaluate `User` at function-definition time.

**Why does this work without quotes?**

Because Python never evaluates the annotation. The annotation is stored as the *source text* — the string `"Ticket"`. When `get_type_hints` later needs the real type, it calls `eval("Ticket", module_globals, locals)` — and by that time `Ticket` is in scope (the class has finished defining). The lazy evaluation is what makes forward references invisible.

### Lines 17–18: A module-level function

```python
def get_ticket(id: int) -> Ticket:
    return Ticket()
```

A simple function. Under PEP 563, `get_ticket.__annotations__` is `{"id": "int", "return": "Ticket"}` — strings. The body `return Ticket()` works fine — the body is *not* affected by PEP 563; only the annotations are. PEP 563 is purely about type annotations, not about runtime code.

### Lines 20–21: Annotations are stored as strings

```python
# Annotations are stored as STRINGS in __annotations__.
print("Ticket.__annotations__:", Ticket.__annotations__)
print("get_ticket.__annotations__:", get_ticket.__annotations__)
```

`Ticket.__annotations__` will be `{}` (no class-level annotations on `Ticket`) and `get_ticket.__annotations__` will be `{"id": "int", "return": "Ticket"}` — strings, not type objects. This is the smoking gun: a direct read of `__annotations__` returns strings under PEP 563. Any framework that does `obj.__annotations__["x"]` and expects a type is broken.

Note that `Ticket.clone`'s annotations are also strings — but you do not see them in `Ticket.__annotations__` because that is the *class* annotation dict. The method's annotations are in `Ticket.clone.__annotations__`.

### Lines 23–25: `get_type_hints` resolves the strings

```python
# get_type_hints resolves the strings back to real types using the module globals.
print("Ticket get_type_hints:", get_type_hints(Ticket.clone))
print("get_ticket get_type_hints:", get_type_hints(get_ticket))
```

`get_type_hints(Ticket.clone)` will be `{"return": <class 'Ticket'>}` — the string `"Ticket"` has been resolved to the real `Ticket` class via `eval("Ticket", module_globals, locals)`. `get_type_hints(get_ticket)` will be `{"id": <class 'int'>, "return": <class 'Ticket'>}` — same resolution. `get_type_hints` is the bridge from PEP 563's string storage to real types.

The resolution uses `eval` against the function's module globals — so any name referenced in an annotation must be importable or defined at module scope. If you reference `Ticket` and the file does not define or import `Ticket`, `get_type_hints` raises `NameError`. The forward-reference benefit is *only* within the same module's scope.

**Why does `get_type_hints` use `eval`?**

Because PEP 563 stores annotations as strings, and the only way to convert a string back to a type is to evaluate it. `eval` against the module's globals plus `None` locals (for class scope) is the canonical way. `get_type_hints` calls `eval(annotation_string, globalns, localns)` for each annotation, then recursively unwraps `Annotated`, `ForwardRef`, and other lazy forms. This is why `get_type_hints` is *not free* — it does an eval per annotation, which is why some frameworks cache the result.

### Lines 27–33: The `Annotated` + `include_extras` interaction

```python
# --- The Pydantic / FastAPI break ---
# When annotations are strings, frameworks that call get_type_hints need:
#   (a) The referenced names to be in scope (globals + locals).
#   (b) include_extras=True to preserve Annotated metadata.
def route(p: Annotated[int, "meta"]) -> None: ...
print("route __annotations__ (string!):", route.__annotations__)
print("route get_type_hints default:", get_type_hints(route))
print("route get_type_hints include_extras:", get_type_hints(route, include_extras=True))
```

`route.__annotations__` will be `{"p": "Annotated[int, 'meta']", "return": "None"}` — strings, including the whole `Annotated[int, 'meta']` form as one string. `route get_type_hints default` (without `include_extras`) will be `{"p": <class 'int'>, "return": <class 'NoneType'>}` — the metadata is stripped, the underlying type is recovered. `route get_type_hints include_extras` will be `{"p": typing.Annotated[int, 'meta'], "return": <class 'NoneType'>}` — the metadata is preserved.

This is the FastAPI dependency. FastAPI calls `get_type_hints(route, include_extras=True)` — if it did not pass `include_extras`, the `Depends(...)` metadata would be stripped and dependencies would silently not be injected. Under PEP 563, this works *only* because FastAPI passes `include_extras=True`. The combination of PEP 563 + `include_extras=False` (the default) is what produces the empty-metadata break we saw in lesson 02.

**Why does PEP 563 store the *whole* `Annotated[...]` as one string?**

Because PEP 563 stores the *source text* of the annotation. The annotation `Annotated[int, "meta"]` is one syntactic expression; its source text is `"Annotated[int, 'meta']"` (a string containing the source). `get_type_hints(include_extras=True)` evaluates the string with `eval` — producing a real `Annotated[int, "meta"]` object — then unwraps it as we saw in lesson 02. The lazy evaluation is *one eval per annotation*, not one per metadata item — so the metadata survives.

### Lines 35–37: `ForwardRef` — the internal type

```python
# --- ForwardRef: the object get_type_hints constructs internally ---
fr = ForwardRef("int")
print("ForwardRef:", fr, "arg:", fr.__forward_arg__)
```

`ForwardRef("int")` constructs a `typing.ForwardRef` object — a "not yet resolved" reference to a type by name. `ForwardRef` has `__forward_arg__` (the string it wraps) and an `_evaluate(globalns, localns)` method that does the actual `eval`. `get_type_hints` uses `ForwardRef` internally when it cannot immediately resolve a string — e.g., a forward reference to a class that has not finished defining.

You rarely construct `ForwardRef` directly — `get_type_hints` does it for you. But knowing it exists is useful when you are debugging a "string that should be a type" issue: the type might be a `ForwardRef` that has not been `_evaluate`d yet. Calling `get_type_hints` resolves all `ForwardRef`s eagerly.

**Why does `ForwardRef` exist as a separate class?**

Because some forward references cannot be resolved at the moment the annotation is encountered — e.g., inside a class body where the class itself is not yet defined. `ForwardRef` is a *placeholder* that can be resolved later when the necessary names are in scope. `get_type_hints` walks the annotation tree, finds `ForwardRef`s, and `_evaluate`s each one. Without `ForwardRef`, the only option would be to `eval` eagerly — which fails for forward references. `ForwardRef` is the lazy-evaluation primitive at the type level.

## Execution Trace

```bash
$ python boardly/future_annotations.py
Ticket.__annotations__: {}
get_ticket.__annotations__: {'id': 'int', 'return': 'Ticket'}
Ticket get_type_hints: {'return': <class '__main__.Ticket'>}
get_ticket get_type_hints: {'id': <class 'int'>, 'return': <class '__main__.Ticket'>}
route __annotations__ (string!): {'p': "Annotated[int, 'meta']", 'return': 'None'}
route get_type_hints default: {'p': <class 'int'>, 'return': <class 'NoneType'>}
route get_type_hints include_extras: {'p': typing.Annotated[int, 'meta'], 'return': <class 'NoneType'>}
ForwardRef: ForwardRef('int') arg: int
```

Three things to verify. First, `get_ticket.__annotations__` shows `{'id': 'int', 'return': 'Ticket'}` — strings, not type objects. Second, `get_ticket get_type_hints` shows `{'id': <class 'int'>, 'return': <class '__main__.Ticket'>}` — `get_type_hints` resolved the strings. Third, the `route` lines show the `Annotated` form stored as one string and resolved to the underlying `int` (default) or the full `Annotated[int, 'meta']` (with `include_extras=True`).

## Common Mistakes

### Mistake 1: Reading `__annotations__` directly and expecting real types

```python
def f(x: int) -> Ticket: ...
hints = f.__annotations__   # ← under PEP 563: {'x': 'int', 'return': 'Ticket'}
for name, t in hints.items():
    if hasattr(t, "__metadata__"):  # ← never True; t is a string
        ...
```

**Symptom:** The `hasattr` branch never fires. Validation, dependency injection, or whatever metadata-driven logic you wrote silently does nothing.
**Why:** Under PEP 563, `__annotations__` stores *strings*, not types. The string `"Annotated[int, 'meta']"` does not have a `__metadata__` attribute. Only the *resolved* `Annotated[int, "meta"]` object does.
**Fix:** Use `get_type_hints(f, include_extras=True)` — it evaluates the strings and returns real type objects, including `Annotated` forms with their metadata. Never read `__annotations__` directly when you want real types.

### Mistake 2: Forward reference that is not in module scope

```python
# boardly/bad_forward.py
from __future__ import annotations

def f(x: "NotDefinedYet") -> None: ...
# NotDefinedYet is never defined in this module.

get_type_hints(f)  # ← NameError
```

**Symptom:** `NameError: name 'NotDefinedYet' is not defined` at `get_type_hints` time — usually when a framework tries to introspect your route.
**Why:** PEP 563 stores the annotation as `"NotDefinedYet"` and `get_type_hints` evaluates it against the module's globals. If the name is not in globals, `eval` raises `NameError`. Forward references work *only* when the name eventually exists in module scope at `get_type_hints` time.
**Fix:** Either define the name (import it, define it at the top of the file), or pass `localns`/`globalns` to `get_type_hints` with the missing names. For class-level forward references inside a class body, the class scope is *not* in `get_type_hints`'s localns — `get_type_hints` uses the *module* globals, not the class body's locals. This is a subtle Python rule (class scope is invisible to nested functions and to `eval`).

### Mistake 3: Assuming PEP 563 is the future

```python
from __future__ import annotations   # ← thinking this is the future default
```

**Symptom:** No runtime issue today, but you might be writing code that breaks in 3.14.
**Why:** PEP 649 (deferred evaluation, default in 3.14) replaces PEP 563. Under PEP 649, annotations are not strings — they are `typing.Form` objects that evaluate lazily on access. `__annotations__` under PEP 649 returns a special mapping that evaluates on `__getitem__`. Code that depends on the *string* form (PEP 563) will break — strings become `Form` objects. Code that uses `get_type_hints` will work unchanged.
**Fix:** Use `get_type_hints(include_extras=True)` for everything that needs real types. Do not depend on the *string* representation of `__annotations__`. If you absolutely need a string, use `typing.get_type_hints(...).__getitem__` and string-format the result — do not assume `__annotations__` is a string dict.

## Engineering Trade-Offs

**Decision:** Use `from __future__ import annotations` in every boardly file; never read `__annotations__` directly; always use `get_type_hints(include_extras=True)`.
**Both sides:** The future import makes forward references automatic and import time faster — but stores annotations as strings, which breaks frameworks that read `__annotations__` directly. The alternative (no future import) stores real types in `__annotations__` but requires explicit string-quotes for forward references and is slower at import time.
**Commitment:** boardly uses `from __future__ import annotations` everywhere. We require all framework integration code to call `get_type_hints(..., include_extras=True)` (FastAPI and Pydantic v2 do this correctly; Pydantic v1 historically did not). The future import is a small performance win at import time and a large ergonomic win for forward references — the trade-off (frameworks must use `get_type_hints`) is one we control by picking well-maintained dependencies.

**Python 3.14+: PEP 649 (Deferred Evaluation of Annotations)**
PEP 649 replaces PEP 563 as the default in Python 3.14. Under PEP 649, annotations are not stored as strings — they are stored as `typing.Form` objects (PEP 749) that *evaluate lazily* on access. The `__annotations__` attribute returns a special mapping whose `__getitem__` evaluates the annotation the first time it is accessed. The result: forward references still work (no eager evaluation), but `__annotations__[name]` returns a real type, not a string. PEP 563 (string storage) is *deprecated* in 3.14 and scheduled for removal in a later version. Code that uses `get_type_hints` works unchanged under PEP 649; code that reads `__annotations__` directly and expects strings will break.

PEP 649 is **not the default in 3.12 or 3.13**. The 3.12 runtime still uses PEP 563 (when the future import is present) or eager evaluation (when it is not). For 3.14+ codebases, the future import becomes a no-op (PEP 649 is the default and behaves similarly). We cover PEP 649 in detail in section `13-future`.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/future_annotations.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/future_annotations.py`
2. **Exercise 2 — Remove the future import and re-run.** Delete the `from __future__ import annotations` line and run the file. Confirm that `get_ticket.__annotations__` now stores real types (not strings). Note that `Ticket.clone` might break with `NameError` if `Ticket` is referenced before it is fully defined. `Verify: python boardly/future_annotations.py`
3. **Exercise 3 — Demonstrate the break.** Write a function `validate(obj)` that reads `obj.__annotations__` directly and tries to call `hasattr(t, "__metadata__")`. Run it on `route` with and without the future import. Confirm the metadata is invisible under PEP 563. `Verify: python -c "from boardly.future_annotations import route; print(route.__annotations__['p'])"`
4. **Exercise 4 — Construct a `ForwardRef`.** Use `ForwardRef("Ticket")` and call `fr._evaluate(globals(), locals(), frozenset())` (3.12 signature) to resolve it. Confirm the result is the `Ticket` class. `Verify: python -c "from typing import ForwardRef; from boardly.future_annotations import Ticket; fr = ForwardRef('Ticket'); print(fr._evaluate(globals(), locals(), frozenset()))"`
5. **Exercise 5 — Write a PEP 649-style accessor.** Write a function `get_hints(obj) -> dict` that calls `get_type_hints(obj, include_extras=True)` and caches the result on `obj.__dict__`. This mimics what PEP 649's lazy evaluation will do for free. Compare it to `obj.__annotations__`. `Verify: python -c "from boardly.future_annotations import get_hints, route; print(get_hints(route))"`

## Verification

```bash
$ python boardly/future_annotations.py
Ticket.__annotations__: {}
get_ticket.__annotations__: {'id': 'int', 'return': 'Ticket'}
Ticket get_type_hints: {'return': <class '__main__.Ticket'>}
get_ticket get_type_hints: {'id': <class 'int'>, 'return': <class '__main__.Ticket'>}
route __annotations__ (string!): {'p': "Annotated[int, 'meta']", 'return': 'None'}
route get_type_hints default: {'p': <class 'int'>, 'return': <class 'NoneType'>}
route get_type_hints include_extras: {'p': typing.Annotated[int, 'meta'], 'return': <class 'NoneType'>}
ForwardRef: ForwardRef('int') arg: int
```

If `get_ticket.__annotations__` shows strings (`{'id': 'int', 'return': 'Ticket'}`) and `get_ticket get_type_hints` shows real types, you have demonstrated the PEP 563 string-storage behaviour. If `route get_type_hints include_extras` shows `typing.Annotated[int, 'meta']`, you have demonstrated the `include_extras` interplay with PEP 563.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `get_type_hints(f)`. Lesson 10 shows what `get_type_hints` actually does internally when PEP 563 is in effect.
- [[01-typing/02-Annotated-and-Metadata]] — `include_extras=True`. Lesson 10 shows why PEP 563 makes `include_extras=True` *mandatory* for any framework that wants `Annotated` metadata.

## What's Next

[[01-typing/11-typing-vs-runtime]] — the final typing lesson. You have seen `__annotations__`, `get_type_hints`, `include_extras`, `ForwardRef`, and the PEP 563/649 distinction. Lesson 11 ties it all together with the precise model of "what evaluates at runtime vs what is stored as strings", and the `include_extras` flag that FastAPI depends on. Three things to look for in lesson 11:

- The full mental model of `__annotations__` vs `get_type_hints` — when each is right.
- How FastAPI's request-handler pipeline uses `get_type_hints` end-to-end.
- The `ForwardRef._evaluate` signature and what it needs to succeed.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.get_type_hints — CPython reference** — https://docs.python.org/3/library/typing.html#typing.get_type_hints — accessed 2026-10-23 — the canonical API for resolving string annotations to real types, including `include_extras` and the `globalns`/`localns` parameters.
- **typing.ForwardRef — CPython reference** — https://docs.python.org/3/library/typing.html#typing.ForwardRef — accessed 2026-10-23 — the canonical API for the internal "not yet resolved" type.
- **PEP 563 — Postponed Evaluation of Annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the PEP that introduced `from __future__ import annotations` in 3.7. Read the "Implementation" section for the string-storage rule.
- **PEP 649 — Deferred Evaluation of Annotations** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the PEP that replaces PEP 563 as the default in 3.14 (version-gated; not in 3.12).
- **PEP 749 — Implementing PEP 649** — https://peps.python.org/pep-0749/ — accessed 2026-10-23 — the implementation PEP for PEP 649 (3.14+).

## What We Learned

- `from __future__ import annotations` (PEP 563, 3.7+) stores every annotation in the file as a string in `__annotations__` — no eager evaluation.
- Forward references "just work" under PEP 563 because the annotation is a string; `get_type_hints` resolves it lazily via `eval`.
- `get_type_hints(f)` evaluates the strings back to real types — the bridge from PEP 563's lazy form to runtime type objects.
- `get_type_hints(f, include_extras=True)` is *mandatory* under PEP 563 for any framework that wants `Annotated` metadata — the default `include_extras=False` strips it.
- `ForwardRef("name")` is the internal class `get_type_hints` uses when an annotation references a name not yet defined; `_evaluate(globalns, localns)` resolves it.
- Reading `__annotations__` directly is broken under PEP 563 — you get strings, not types. Always use `get_type_hints`.
- PEP 649 (deferred evaluation, default in 3.14) replaces PEP 563 — annotations become `Form` objects that evaluate on access, not strings. Code using `get_type_hints` works unchanged; code reading `__annotations__` directly for strings will break.
