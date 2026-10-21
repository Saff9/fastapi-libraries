---
title: "Lesson 01: signature and Parameter"
aliases:
 - inspect.signature
 - inspect.Parameter
 - Signature object
tags:
 - inspect
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[10-inspect/02-get_type_hints]]"
 - "[[10-inspect/04-Parameter-kinds]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
first_taught_in: "10-inspect/01-signature-and-Parameter"
---

# Lesson 01: signature and Parameter

*How `boardly`'s `inspect.signature(get_ticket)` turns the function `def get_ticket(id: int, status: str = "open") -> dict:` into data you can walk, iterate, and bind — the same call FastAPI makes on every route you write.*

**You're at the very beginning of Section 10.**

You have written `def get_ticket(id: int, status: str = "open") -> dict:` and you know what each piece means. You have not seen what Python does when it stores that signature as *data*. This lesson shows you: `inspect.signature` returns a `Signature` object, the `Signature` has a `.parameters` mappingproxy (a read-only view over an `OrderedDict`) of `Parameter` objects, each `Parameter` has a `.kind` and a `.default` and an `.annotation`. By the end of the lesson, you can read a function's signature the way FastAPI does. Take your time. Type every example. **This is how you learn.**

#inspect #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `inspect.signature`** — pass a callable, get back a `Signature`, and read its `repr`.
2. **Walk `sig.parameters`** — iterate the `mappingproxy` view of `Parameter` objects, read each `.name`, `.kind`, `.default`, `.annotation`.
3. **Name the five `Parameter.kind` values** — `POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD` — and explain what each means.
4. **Identify `Parameter.empty`** — explain that the sentinel `inspect.Parameter.empty` means "no default" or "no annotation", distinct from `None`.
5. **Read `sig.return_annotation`** — explain how the return type is stored on the `Signature`, not on a `Parameter`.

## Prerequisites

Before starting, you need:

- **Type hints basics** — `def f(x: int) -> bool:` should be familiar. See [[01-typing/01-Type-Hints-Basics]] for the canonical introduction.
- **About 30–40 minutes of focused time.**

**The most common gap: confusing the `Parameter.empty` sentinel with `None`.** `Parameter.empty` is a class-level sentinel that means "no value provided" — for default, for annotation. `None` is a real default value (e.g., `status: Optional[str] = None`). The two compare unequal, and mistaking one for the other causes the most common bug in this section: "does this parameter have a default?" is checked via `param.default is not Parameter.empty`, not `param.default is not None`.

## The Problem

Here is the bug. `boardly` had this helper:

```python
# boardly/di.py — the bad old days
def get_ticket(id: int, status: str = "open"):
    ...

# Somewhere else — trying to figure out which params the function takes
import inspect
src = inspect.getsource(get_ticket)
# Now we have to parse Python source to find the params. Yuck.
```

The "parse the source" approach is what every naive dependency-injection framework did before `inspect.signature` existed. It is brittle, slow, and wrong on the edge cases (decorators, `functools.partial`, `*args`/`**kwargs`, defaults that are not literals). PEP 362 (Python 3.3) introduced `inspect.signature` precisely to give Python a *first-class* way to read a callable's parameter list as data.

The bug that motivates `inspect.signature` is "I need to know what arguments a function takes, and I refuse to parse Python source to find out." FastAPI hits that bug on every route you write — it has to know which parameters are path params, which are query params, which are dependencies, and which are body. The solution is `inspect.signature`.

## The Code

```python
# boardly/di_signature.py
"""Demonstrates inspect.signature and the Parameter object."""
import inspect


def get_ticket(id: int, status: str = "open", *tags, user, **extra) -> dict:
    """A boardly function with all five parameter kinds."""
    return {"id": id, "status": status, "tags": tags, "user": user, "extra": extra}


# 1. The Signature object
sig = inspect.signature(get_ticket)
print("sig:", sig)                       # (id: int, status: str = 'open', *tags, user, **extra) -> dict
print("type:", type(sig).__name__)      # Signature
print("return_annotation:", sig.return_annotation)   # <class 'dict'>

# 2. The parameters — a mappingproxy view of OrderedDict
print("\n--- sig.parameters ---")
for name, param in sig.parameters.items():
    print(f"  {name}: kind={param.kind.name}, default={param.default!r}, annotation={param.annotation!r}")

# 3. The five Parameter.kind values
print("\n--- all Parameter.kind values ---")
for kind in (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.KEYWORD_ONLY,
    inspect.Parameter.VAR_KEYWORD,
):
    print(f"  {kind.name} = {kind.value}")

# 4. The empty sentinel — distinct from None
print("\n--- the empty sentinel ---")
print("Parameter.empty:", repr(inspect.Parameter.empty))   # <class 'inspect._empty'>
print("Signature.empty:", repr(inspect.Signature.empty))   # <class 'inspect._empty'>
print("Parameter.empty is None:", inspect.Parameter.empty is None)   # False
print("Parameter.empty is Signature.empty:", inspect.Parameter.empty is inspect.Signature.empty)   # True

# 5. Checking "has a default?"
def has_default(param: inspect.Parameter) -> bool:
    return param.default is not inspect.Parameter.empty

id_param = sig.parameters["id"]
status_param = sig.parameters["status"]
print(f"\nid has default?     {has_default(id_param)}")      # False
print(f"status has default? {has_default(status_param)}")   # True
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 6–7: The function under inspection

```python
def get_ticket(id: int, status: str = "open", *tags, user, **extra) -> dict:
    """A boardly function with all five parameter kinds."""
    return {"id": id, "status": status, "tags": tags, "user": user, "extra": extra}
```

This function is deliberately a maximal example — it has all five `Parameter.kind` values in one signature:

- `id: int` — `POSITIONAL_OR_KEYWORD`. Can be passed by position or by keyword.
- `status: str = "open"` — `POSITIONAL_OR_KEYWORD` with a default. Same kind, but `param.default` is `"open"`, not `Parameter.empty`.
- `*tags` — `VAR_POSITIONAL`. Collects extra positional arguments into a tuple.
- `user` — `KEYWORD_ONLY`. After `*tags`, every parameter must be passed by keyword.
- `**extra` — `VAR_KEYWORD`. Collects extra keyword arguments into a dict.

The return annotation `-> dict` is stored on the `Signature` object (as `sig.return_annotation`), not on a `Parameter`. That is because the return type is a property of the function, not of any one parameter. There is no `POSITIONAL_ONLY` parameter in this example — `POSITIONAL_ONLY` parameters come from C-extension builtins and from functions defined with the `/` separator (e.g., `def f(a, /, b)`).

### Lines 11–13: The `Signature` object

```python
sig = inspect.signature(get_ticket)
print("sig:", sig)                       # (id: int, status: str = 'open', *tags, user, **extra) -> dict
print("type:", type(sig).__name__)      # Signature
print("return_annotation:", sig.return_annotation)   # <class 'dict'>
```

`inspect.signature(get_ticket)` calls `get_ticket.__signature__` if it exists, otherwise builds a `Signature` from the function's `__code__` and `__defaults__`/`__kwdefaults__`. Most Python callables — functions, lambdas, methods, classes, `functools.partial` objects — produce a `Signature` via the second path. A callable that defines a custom `__signature__` property (rare; usually decorated wrappers) controls what `inspect.signature` returns.

The `repr` of a `Signature` is the source-code form: `(id: int, status: str = 'open', *tags, user, **extra) -> dict`. That readable `repr` is one of the small things that makes `inspect.signature` worth using — you can print the signature of any callable and get back the same shape you wrote in source. (Try this with a `functools.partial` — the `repr` shows the bound arguments.)

`sig.return_annotation` is `dict` — the return type annotation. It is `inspect.Signature.empty` if the function has no return annotation. Note the placement: it lives on `Signature`, not on `Parameter`. There is one return type per function; there are many parameters.

**Why is `return_annotation` not a `Parameter`?** Because a `Parameter` is "an input to the function." The return type is not an input. Storing it on `Signature` keeps the data model clean: each `Parameter` describes one input, the `Signature` describes the function as a whole (inputs + return + the call signature). When you iterate `sig.parameters.values()`, you do not want a phantom "return" parameter in the list.

### Lines 16–19: `sig.parameters` is a `mappingproxy`

```python
print("\n--- sig.parameters ---")
for name, param in sig.parameters.items():
    print(f"  {name}: kind={param.kind.name}, default={param.default!r}, annotation={param.annotation!r}")
```

`sig.parameters` is a `mappingproxy` (read-only view over an `OrderedDict`) of `Parameter` objects, keyed by parameter name. The order matches the source-code order — `id`, `status`, `tags`, `user`, `extra`. That order matters: it is the order in which `POSITIONAL_OR_KEYWORD` and `VAR_POSITIONAL` parameters are bound by `Signature.bind` (lesson 05). The `mappingproxy` makes the parameters read-only: you can iterate them and look up by key, but you cannot `sig.parameters["x"] = ...` (that raises `TypeError`). Lesson 04 covers the mappingproxy mechanics in full.

Each `Parameter` has four attributes you read in this lesson:
- `.name` — the parameter name as a string (`"id"`, `"status"`, etc.).
- `.kind` — one of the five `Parameter.kind` enum values.
- `.default` — the default value, or `Parameter.empty` if there is no default.
- `.annotation` — the type annotation, or `Parameter.empty` if there is no annotation.

**Tip — `sig.parameters` is the dictionary you will iterate most**

`for name, param in sig.parameters.items():` is the most common line of `inspect` code. FastAPI's `get_dependant` (the function that builds the dependency tree) starts with exactly that loop. Every DI framework, every command-line argument parser, every "call this function with auto-discovered args" tool walks `sig.parameters`. Memorise this loop.

### Lines 22–30: The five `Parameter.kind` values

```python
for kind in (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.KEYWORD_ONLY,
    inspect.Parameter.VAR_KEYWORD,
):
    print(f"  {kind.name} = {kind.value}")
```

The five `kind` values form an enum (`inspect._ParameterKind`). Their integer values are 0–4, in declaration order:

| kind | value | meaning | example |
|------|-------|---------|---------|
| `POSITIONAL_ONLY` | 0 | can only be passed by position | `def f(a, /): ...` (the `/` separator) |
| `POSITIONAL_OR_KEYWORD` | 1 | can be passed by position or by keyword | `def f(a): ...` (the default) |
| `VAR_POSITIONAL` | 2 | collects extra positional args into a tuple | `def f(*args): ...` |
| `KEYWORD_ONLY` | 3 | can only be passed by keyword | `def f(*, a): ...` or `def f(*args, a): ...` |
| `VAR_KEYWORD` | 4 | collects extra keyword args into a dict | `def f(**kwargs): ...` |

**Note — Lesson 04 covers the five kinds in depth**

This lesson introduces the five; lesson 04 walks each one's rules in depth, with the ordering constraints (`POSITIONAL_ONLY` must come before `POSITIONAL_OR_KEYWORD`, which must come before `VAR_POSITIONAL`, etc.) and the `bind()` behaviour each kind enforces. For now, the takeaway is: every parameter has exactly one of these five kinds, and the kind determines how the parameter is bound at call time.

### Lines 33–37: The `Parameter.empty` sentinel

```python
print("Parameter.empty:", repr(inspect.Parameter.empty))   # <class 'inspect._empty'>
print("Signature.empty:", repr(inspect.Signature.empty))   # <class 'inspect._empty'>
print("Parameter.empty is None:", inspect.Parameter.empty is None)   # False
print("Parameter.empty is Signature.empty:", inspect.Parameter.empty is inspect.Signature.empty)   # True
```

`inspect.Parameter.empty` is a sentinel. Its `repr` is `<class 'inspect._empty'>` — it is actually a class (the private `_empty` class), used as a singleton sentinel. The same class is aliased as `inspect.Signature.empty` (used for missing return annotations), so `Parameter.empty is Signature.empty` is `True` — they are the same sentinel.

The sentinel exists because `None` is a valid default value. `def f(x=None)` has `param.default == None` — that is a real default, not a missing one. If `inspect` used `None` for "no default", you could not distinguish `def f(x=None)` from `def f(x)`. The sentinel makes the distinction crisp: `param.default is Parameter.empty` means "no default"; `param.default is None` means "default is `None`".

The same applies to `.annotation`. `def f(x: int)` has `param.annotation == int`. `def f(x)` has `param.annotation is Parameter.empty`. `def f(x: None)` would have `param.annotation == NoneType` (which is a real annotation, weird as it is). The sentinel distinguishes "no annotation" from "annotation is `None`".

**Warning — Check with `is`, not `==`**

```python
param.default is inspect.Parameter.empty   # correct
param.default == inspect.Parameter.empty  # also True for the sentinel, but use `is` for clarity
```

The `is` check is idiomatic; it makes the sentinel-comparison intent visible. Some codebases use `==`, which works for `Parameter.empty` (because the sentinel class defines `__eq__` as identity) but loses the visual cue that you are checking a sentinel, not a value.

### Lines 39–46: The `has_default` helper

```python
def has_default(param: inspect.Parameter) -> bool:
    return param.default is not inspect.Parameter.empty

id_param = sig.parameters["id"]
status_param = sig.parameters["status"]
print(f"\nid has default?     {has_default(id_param)}")      # False
print(f"status has default? {has_default(status_param)}")   # True
```

This helper is the canonical "does this parameter have a default?" check. It is the single most useful `inspect` idiom — FastAPI uses it (in spirit) to decide whether a query parameter is required (`param.default is Parameter.empty` → required) or optional (has a default → optional). You will write this check dozens of times if you build anything that introspects callables.

The output for `get_ticket`'s parameters:
- `id` has no default (`param.default is Parameter.empty` → `True`)
- `status` has a default (`param.default == "open"` → `True`)
- `tags` (`VAR_POSITIONAL`) has no default in the usual sense — its `.default` is `Parameter.empty`, but it accepts zero arguments (an empty tuple).
- `user` (`KEYWORD_ONLY`) has no default — `param.default is Parameter.empty`, so it is a *required* keyword argument. Calling `get_ticket(1, "open")` without `user=...` raises `TypeError`.
- `extra` (`VAR_KEYWORD`) has no default in the usual sense — `.default` is `Parameter.empty`, but it accepts zero keyword arguments (an empty dict).

**Why does `*args`/`**kwargs` have `.default = Parameter.empty`?** Because they are not "optional" in the keyword-argument sense — they are *variadic*. The presence of `*args` means "any number of positional args, including zero"; the `.default` sentinel means "this parameter does not have a single default value; it has a tuple/dict of values." The check `param.default is not Parameter.empty` returns `False` for `*args`/`**kwargs`, which is correct — they do not have a default value in the same sense as `status = "open"`.

## Execution Trace

```bash
$ python boardly/di_signature.py
sig: (id: int, status: str = 'open', *tags, user, **extra) -> dict
type: Signature
return_annotation: <class 'dict'>

--- sig.parameters ---
  id: kind=POSITIONAL_OR_KEYWORD, default=<class 'inspect._empty'>, annotation=<class 'int'>
  status: kind=POSITIONAL_OR_KEYWORD, default='open', annotation=<class 'str'>
  tags: kind=VAR_POSITIONAL, default=<class 'inspect._empty'>, annotation=<class 'inspect._empty'>
  user: kind=KEYWORD_ONLY, default=<class 'inspect._empty'>, annotation=<class 'inspect._empty'>
  extra: kind=VAR_KEYWORD, default=<class 'inspect._empty'>, annotation=<class 'inspect._empty'>

--- all Parameter.kind values ---
  POSITIONAL_ONLY = 0
  POSITIONAL_OR_KEYWORD = 1
  VAR_POSITIONAL = 2
  KEYWORD_ONLY = 3
  VAR_KEYWORD = 4

--- the empty sentinel ---
Parameter.empty: <class 'inspect._empty'>
Signature.empty: <class 'inspect._empty'>
Parameter.empty is None: False
Parameter.empty is Signature.empty: True

id has default?     False
status has default? True
```

## Common Mistakes

### Mistake 1: Confusing `Parameter.empty` with `None`

```python
def f(x=None): ...
sig = inspect.signature(f)
param = sig.parameters["x"]
if param.default is None:    # WRONG — this is True for f(x=None) AND for f(x) (if you used None as sentinel)
    print("no default")
```

**Symptom:** The check `param.default is None` returns `True` for `f(x=None)`, but you wanted to detect "no default provided" — and `f(x=None)` *does* have a default (which happens to be `None`).
**Why:** `None` is a valid default value. `Parameter.empty` is the sentinel for "no default". They are different.
**Fix:** Use `param.default is inspect.Parameter.empty`. That returns `True` only when there is genuinely no default. `param.default is None` returns `True` only when the default is literally `None`.

### Mistake 2: Reading `param.annotation` and assuming it is a type

```python
def f(x: "int"):    # string annotation, common with `from __future__ import annotations`
    ...
sig = inspect.signature(f)
annotation = sig.parameters["x"].annotation   # the string "int", NOT the class int
```

**Symptom:** `issubclass(annotation, int)` raises `TypeError` because `annotation` is the string `"int"`, not the class `int`.
**Why:** `inspect.signature` does not resolve string annotations. It returns whatever is in `__annotations__` — which, under `from __future__ import annotations` (PEP 563), is the string form of the annotation.
**Fix:** Use `typing.get_type_hints(call)` (lesson 02) to resolve the strings. `get_type_hints` evaluates forward references using the function's `__globals__` and returns real classes.

### Mistake 3: Iterating `sig.parameters` and expecting the return type

```python
for name, param in sig.parameters.items():
    if param.annotation is dict:    # never True
        handle_return(param)
```

**Symptom:** The loop never finds the return type, because the return type is not in `sig.parameters`.
**Why:** The return annotation lives on the `Signature` object as `sig.return_annotation`, not on a `Parameter`. `sig.parameters` is keyed by parameter name; there is no "return" key.
**Fix:** Read `sig.return_annotation` directly, outside the parameter loop.

## Engineering Trade-Offs

**Decision:** Use `inspect.signature` for every "I need to know what arguments a callable takes" problem. Do not parse source. Do not read `__code__` directly.
**Both sides:** The alternative is `inspect.getfullargspec` (the older API, predates `signature`). `getfullargspec` returns a tuple of `(args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations)`. It is faster than `signature` and lighter, but the tuple-indexed access is brittle and the API does not handle all the edge cases (positional-only parameters, `functools.partial` unwrapping). `signature` is the modern API; `getfullargspec` is for legacy code.
**Commitment:** `boardly` uses `inspect.signature` everywhere. The `getfullargspec` API is mentioned in this lesson for context but not used.

## Exercises

1. **Exercise 1 — Inspect a boardly function.** Define `def create_ticket(title: str, priority: int = 1): ...` and call `inspect.signature` on it. Print the parameters. `Verify: python -c "import inspect; def f(t: str, p: int = 1): ...; sig=inspect.signature(f); print(list(sig.parameters))"`
2. **Exercise 2 — All five kinds.** Write a function with all five parameter kinds and confirm `sig.parameters` lists them in the order `POSITIONAL_ONLY` → `POSITIONAL_OR_KEYWORD` → `VAR_POSITIONAL` → `KEYWORD_ONLY` → `VAR_KEYWORD`. `Verify: python -c "import inspect; exec('def f(a, /, b, *c, d, **e): pass'); sig=inspect.signature(f); print([p.kind.name for p in sig.parameters.values()])"`
3. **Exercise 3 — The sentinel check.** Write `has_default(param)` and test it on `def f(x, y=2): ...` — confirm `x` returns `False` and `y` returns `True`. `Verify: python -c "import inspect; from boardly.di_signature import has_default; def f(x, y=2): ...; sig=inspect.signature(f); print(has_default(sig.parameters['x']), has_default(sig.parameters['y']))"`
4. **Exercise 4 — Return annotation.** Define `def f() -> int: return 1` and confirm `sig.return_annotation is int`. Try with no return annotation and confirm `sig.return_annotation is inspect.Signature.empty`. `Verify: python -c "import inspect; def f() -> int: return 1; sig=inspect.signature(f); print(sig.return_annotation)"`
5. **Exercise 5 — Build a parameter list printer.** Write a function `print_signature(callable)` that prints each parameter's name, kind, default, and annotation in a formatted table. Test it on a 5-parameter function. `Verify: python -c "from boardly.di_signature import print_signature; print_signature(lambda a, b=1, *c, d, **e: None)"`

## Verification

```bash
$ python boardly/di_signature.py | head -1
sig: (id: int, status: str = 'open', *tags, user, **extra) -> dict
$ python boardly/di_signature.py | rg 'POSITIONAL_ONLY'
  POSITIONAL_ONLY = 0
$ python -c "import inspect; print(inspect.Parameter.empty is inspect.Signature.empty)"
True
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — type annotations, the `def f(x: int):` syntax that `inspect.signature` reads.

## What's Next

[[10-inspect/02-get_type_hints]] — You can now read the parameter *shape* via `inspect.signature`. The next lesson shows you how to read the parameter *annotations* via `typing.get_type_hints` — which resolves string forms (the `from __future__ import annotations` interaction) and, with `include_extras=True`, keeps `Annotated` metadata. That metadata is what FastAPI reads to find `Depends(...)` markers in your route signatures.

- **Lesson 02** — `get_type_hints`, `include_extras=True`, the `Annotated` read path.
- **Lesson 04** — The five `Parameter.kind` values in depth.
- **Lesson 06** — How FastAPI combines `signature` + `get_type_hints` to build the dependency tree.

## Sources

- **Python `inspect` module documentation — `inspect.signature`** — https://docs.python.org/3/library/inspect.html#inspect.signature — accessed 2026-10-23 — the canonical reference for the `Signature` class and the `signature()` factory.
- **Python `inspect` module documentation — `inspect.Parameter`** — https://docs.python.org/3/library/inspect.html#inspect.Parameter — accessed 2026-10-23 — the canonical reference for the `Parameter` class, its `.kind` enum, and the `empty` sentinel.
- **PEP 362 — Function Signature Object** — https://peps.python.org/pep-0362/ — accessed 2026-10-23 — the PEP that introduced `inspect.signature` in Python 3.3. Read it for the "stop parsing source" motivation and the original `Parameter.kind` design.

## What We Learned

- You can now call `inspect.signature(callable)` and read the `Signature` object it returns.
- You can now walk `sig.parameters` (a `mappingproxy` view over an `OrderedDict`) and read each `Parameter`'s `.name`, `.kind`, `.default`, `.annotation`.
- You can now name the five `Parameter.kind` values and explain what each one means.
- You can now check "does this parameter have a default?" with `param.default is not inspect.Parameter.empty` (the sentinel, not `None`).
- You can now read `sig.return_annotation` and know it lives on the `Signature`, not on a `Parameter`.
