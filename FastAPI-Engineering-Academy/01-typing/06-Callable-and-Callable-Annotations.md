---
title: "Lesson 06: Callable and Callable Annotations"
aliases:
 - Callable and Callable Annotations
 - 06-Callable-and-Callable-Annotations
 - Callable
 - typing.Callable
tags:
 - typing
 - callable
 - collections-abc
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/04-ParamSpec-and-TypeVarTuple]]"
related_lessons:
 - "[[01-typing/04-ParamSpec-and-TypeVarTuple]]"
 - "[[01-typing/05-Protocol-Structural-Typing]]"
 - "[[05-collections-abc/04-Iterator-vs-Iterable]]"
---

# Lesson 06: Callable and Callable Annotations

*`Callable[[int, str], None]` for typing function parameters and returns — and the 3.12 shorthand that lets you drop the inner brackets.*

**You're at the very beginning of Section 01's function-typing lesson.**

You can type a `list[int]`, an `int | None`, an `Annotated[int, ...]`. But what about *functions themselves*? When you write `def run_query(handler: ???) -> None: handler(1, "x")`, what do you put in place of `???`? The answer is `Callable`. `Callable[[Arg1, Arg2], ReturnType]` is the standard form. `Callable[..., T]` is the "any-signature" form. And from 3.12 you can write `Callable[int, str]` (no inner brackets) when the function takes a single argument. Take your time. Type every example. **This is how you learn.**

#typing #callable

## Learning Objectives

By the end of this lesson you will be able to:

1. **Write** `Callable[[Arg1, Arg2], ReturnType]` to type a function parameter or return, and explain what each piece means.
2. **Use** `Callable[..., T]` for "any signature, returns `T`" and `Callable[[], T]` for "no args, returns `T`".
3. **Use** the 3.12 shorthand `Callable[int, str]` (no inner brackets) when the function takes a single argument, and explain how Python normalises it to `Callable[[int], str]`.
4. **Distinguish** `typing.Callable` from `collections.abc.Callable` and choose the right one for your codebase.
5. **Define** a `Callable` `TypeAlias` for a handler signature used across a codebase.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — `list[int]`, `dict[str, X]`, `get_type_hints`.
- **[[01-typing/04-ParamSpec-and-TypeVarTuple]]** — `ParamSpec` and `Callable[P, R]` — we used the `ParamSpec` form there; here we cover the concrete form.
- **About 30–45 minutes of focused time.**

**The most common gap: not knowing there are *two* `Callable` types.**

Students arrive having imported `Callable` from `typing` and not knowing that `collections.abc.Callable` also exists. They are *not* the same object, *not* `==`-equal, but produce values that compare equal in some contexts and unequal in others. The two `Callable`s exist for historical reasons (PEP 585 made the `collections.abc` versions subscriptable in 3.9, but `typing.Callable` was already in wide use). Knowing which to use in new code is a small thing that affects every file in your project.

## The Problem

Here is the bug this lesson prevents. boardly has a "handler" function — a function that takes `(ticket_id: int, status: str)` and returns `dict[str, int]`. The team writes:

```python
def make_handler(project_id: int):
    def handler(ticket_id: int, status: str) -> dict[str, int]:
        return {status: ticket_id, "project": project_id}
    return handler

# At the call site:
h = make_handler(project_id=99)
result = h(7, "open")  # what is h's type? what does the IDE show?
```

Without a `Callable` annotation, `make_handler`'s return type is `Any` — the IDE shows `h` as `Any`, mypy cannot check the call `h(7, "open")` (did you pass the right arg types? does it return `dict[str, int]`?). The signature is opaque at the call site.

With `Callable`:

```python
Handler = Callable[[int, str], dict[str, int]]

def make_handler(project_id: int) -> Handler:
    def handler(ticket_id: int, status: str) -> dict[str, int]:
        return {status: ticket_id, "project": project_id}
    return handler
```

Now the IDE shows `h` as `Callable[[int, str], dict[str, int]]`, mypy checks the call against the signature, and refactoring the handler signature updates the `Handler` alias everywhere.

## The Code

```python
# boardly/callable_annotations.py
"""boardly — Callable annotations: [[Arg1, Arg2], R], [..., R], the 3.12 form, abc vs typing."""
from typing import Callable, get_type_hints, get_origin, get_args
from collections.abc import Callable as AbcCallable

# Standard form: a function taking (int, str) and returning None.
def log_call(fn: Callable[[int, str], None]) -> None:
    fn(1, "x")

# Variadic form: any signature, returns int. The ... means "any args".
def run_with_int_return(fn: Callable[..., int]) -> int:
    return fn()

# No-arg form: zero arguments, returns int.
def get_constant(fn: Callable[[], int]) -> int:
    return fn()

# typing.Callable vs collections.abc.Callable — same shape, different origins.
def takes_typing_callable(fn: Callable[[int], str]) -> None: ...
def takes_abc_callable(fn: AbcCallable[[int], str]) -> None: ...

# Real boardly example: a handler factory.
Handler = Callable[[int, str], dict[str, int]]

def make_handler(project_id: int) -> Handler:
    def handler(ticket_id: int, status: str) -> dict[str, int]:
        return {status: ticket_id, "project": project_id}
    return handler

if __name__ == "__main__":
    # The standard form.
    def example(a: int, b: str) -> None:
        print(f"example: {a=}, {b=}")
    log_call(example)

    # Variadic form.
    def returns_5(x=1, y=2) -> int:
        return x + y + 2
    print("variadic returns:", run_with_int_return(returns_5))

    # No-arg form.
    print("no-arg returns:", get_constant(lambda: 42))

    # typing.Callable vs collections.abc.Callable
    h_typing = get_type_hints(takes_typing_callable)["fn"]
    h_abc = get_type_hints(takes_abc_callable)["fn"]
    print("typing.Callable origin:", get_origin(h_typing))
    print("collections.abc.Callable origin:", get_origin(h_abc))
    print("typing.Callable args:", get_args(h_typing))
    print("collections.abc.Callable args:", get_args(h_abc))
    print("equal:", h_typing == h_abc)

    # The handler factory.
    h = make_handler(project_id=99)
    print("handler result:", h(7, "open"))
    print("handler hints:", get_type_hints(make_handler))
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports

```python
# boardly/callable_annotations.py
"""boardly — Callable annotations: [[Arg1, Arg2], R], [..., R], the 3.12 form, abc vs typing."""
from typing import Callable, get_type_hints, get_origin, get_args
from collections.abc import Callable as AbcCallable
```

We import `Callable` from `typing` (the legacy location, still preferred in many codebases) and import `collections.abc.Callable` *under the alias `AbcCallable`* — to compare the two side by side without clobbering either. In real boardly code you would pick one and use it everywhere; we import both here for demonstration.

`get_origin` and `get_args` will let us inspect the resulting type objects and see what they are made of.

**Why are there two `Callable` types?**

History. PEP 484 (3.5) introduced `typing.Callable` — the *only* way to subscript a callable back then. PEP 585 (3.9) made the `collections.abc` ABCs subscriptable, so `collections.abc.Callable[[int], str]` started working. The two `Callable`s are *different classes* (`typing._CallableGenericAlias` vs `collections.abc._CallableGenericAlias`), they are *not* `==`-equal, but their `get_origin` is the same (`collections.abc.Callable`) — `typing.Callable` was reimplemented to delegate to `collections.abc.Callable` for origin purposes. In new code, prefer `collections.abc.Callable` (the modern form); `typing.Callable` exists for backward compatibility.

### Lines 8–10: The standard form

```python
# Standard form: a function taking (int, str) and returning None.
def log_call(fn: Callable[[int, str], None]) -> None:
    fn(1, "x")
```

`Callable[[int, str], None]` is the standard form. The first element is a *list* of argument types (`[int, str]`), the second is the return type (`None`). So `Callable[[int, str], None]` describes a function `def f(a: int, b: str) -> None: ...`. The argument list is positional — the names of the parameters are *not* part of the type; only their order and types matter.

Inside `log_call`, `fn` is callable as `fn(1, "x")` — mypy knows this matches the signature `(int, str) -> None`. If you wrote `fn(1, 2)`, mypy would flag it (`int` ≠ `str`). If you wrote `fn(1, "x", 3)`, mypy would flag too-many-args.

**Why is the argument list a *list* and not a *tuple*?**

Convention. PEP 484 chose `list` because the type system did not yet have `tuple[X, ...]` semantics; `list` was the simplest ordered collection. The convention has stuck even after PEP 585 made `tuple` subscriptable. `Callable[(int, str), None]` (with a tuple) is *not* accepted — only `Callable[[int, str], None]` with a list. This is one of those quirks that is not worth fighting.

### Lines 12–15: The variadic form

```python
# Variadic form: any signature, returns int. The ... means "any args".
def run_with_int_return(fn: Callable[..., int]) -> int:
    return fn()
```

`Callable[..., int]` is the "any-signature, returns `int`" form. The `...` (ellipsis) replaces the argument list and means "any number of any types of arguments". `fn` is callable as `fn()` *or* `fn(1)` *or* `fn(1, 2, "x", key=True)` — mypy allows any of these because the signature is unspecified. The only thing checked is the return type, `int`.

This is the form to use when you cannot (or do not want to) pin down the argument list — e.g., a generic wrapper that just calls `fn(*args, **kwargs)` without inspecting them. In lesson 04 we saw the better form for *typed* wrappers: `Callable[P, R]` with `ParamSpec`, which preserves the original signature. `Callable[..., int]` is the *untyped* alternative when preservation is not needed.

**Why ever use `Callable[..., T]` instead of `Callable[P, R]`?**

Two reasons. (1) **Simplicity**: when you really do not care about the signature, `...` is shorter and clearer than declaring a `ParamSpec`. (2) **Tooling limits**: not all type-checkers fully support `ParamSpec` (pyright does; mypy 1.x does). `Callable[..., T]` is universally supported. In boardly we use `...` for "I just need to call this and get a `T` back", and `ParamSpec` for "I need to preserve the original signature for callers". The two serve different needs.

### Lines 17–19: The no-argument form

```python
# No-arg form: zero arguments, returns int.
def get_constant(fn: Callable[[], int]) -> int:
    return fn()
```

`Callable[[], int]` — empty list of arguments — means "a function taking *no* arguments and returning `int`". The empty list is significant: it is *not* the same as `Callable[..., int]`. With `Callable[[], int]`, mypy will flag `fn(1)` as too-many-args. With `Callable[..., int]`, mypy allows `fn(1)`.

Use `Callable[[], T]` when you want to *enforce* that the function takes no arguments — e.g., a "factory" that returns a fresh instance each call. boardly uses this for `def make_session() -> Session` factory functions, which are then passed to `register_factory(make_session)` where the registration expects `Callable[[], Session]`.

### Lines 21–23: `typing.Callable` vs `collections.abc.Callable`

```python
# typing.Callable vs collections.abc.Callable — same shape, different origins.
def takes_typing_callable(fn: Callable[[int], str]) -> None: ...
def takes_abc_callable(fn: AbcCallable[[int], str]) -> None: ...
```

Two functions with identical *shapes* but using the two different `Callable` classes. At runtime, the two resulting annotations are *not equal* (`==` returns `False`), *not the same object* (`is` returns `False`), but their `get_origin` is *the same class* (`collections.abc.Callable`). This is because PEP 585 made `typing.Callable` a thin wrapper that delegates origin to `collections.abc.Callable`.

In the `__main__` block we will print `get_origin` and `get_args` of both — the origins are the same (`collections.abc.Callable`), the args are the same (`([int], str)`), but the annotations themselves are not equal. This is a quirk that rarely matters in practice — most tools normalise the two — but it is real.

**Which one should I use?**

`collections.abc.Callable` in new code. It is the modern, PEP 585–compliant form. `typing.Callable` works, but the typing module is being slowly thinned out — the long-term direction is to migrate generic aliases from `typing` to `collections.abc`. Pydantic v2, FastAPI, and modern Starlette all use `collections.abc.Callable` internally. If you have an existing codebase using `typing.Callable`, do not refactor on a deadline — they are equivalent at the API level. But for new files, prefer `collections.abc.Callable`.

### Lines 25–33: The `Handler` alias and the factory

```python
# Real boardly example: a handler factory.
Handler = Callable[[int, str], dict[str, int]]

def make_handler(project_id: int) -> Handler:
    def handler(ticket_id: int, status: str) -> dict[str, int]:
        return {status: ticket_id, "project": project_id}
    return handler
```

`Handler = Callable[[int, str], dict[str, int]]` is a *type alias* — `Handler` is just another name for the `Callable` type. Aliases are how you avoid repeating long signatures across a codebase. `def make_handler(...) -> Handler:` says "returns a handler" — much clearer than inlining the `Callable` form. We cover type aliases more in lesson 11 (`typing.TypeAlias` and the 3.12 `type` statement from PEP 695).

Inside `make_handler`, the inner `handler` closure captures `project_id` from the enclosing scope. The closure's signature is `(ticket_id: int, status: str) -> dict[str, int]` — exactly matching `Handler`. mypy verifies the closure satisfies the return type.

**Why use a closure here instead of a class?**

Because the closure captures `project_id` for free — no `self.project_id = project_id` boilerplate. For a stateful handler that just needs to remember one value, a closure is the minimum ceremony. If the handler needed to mutate its captured state, a class would be better (closures cannot rebind captured variables without `nonlocal`).

### Lines 35–55: The `__main__` block

```python
if __name__ == "__main__":
    # The standard form.
    def example(a: int, b: str) -> None:
        print(f"example: {a=}, {b=}")
    log_call(example)

    # Variadic form.
    def returns_5(x=1, y=2) -> int:
        return x + y + 2
    print("variadic returns:", run_with_int_return(returns_5))

    # No-arg form.
    print("no-arg returns:", get_constant(lambda: 42))

    # typing.Callable vs collections.abc.Callable
    h_typing = get_type_hints(takes_typing_callable)["fn"]
    h_abc = get_type_hints(takes_abc_callable)["fn"]
    print("typing.Callable origin:", get_origin(h_typing))
    print("collections.abc.Callable origin:", get_origin(h_abc))
    print("typing.Callable args:", get_args(h_typing))
    print("collections.abc.Callable args:", get_args(h_abc))
    print("equal:", h_typing == h_abc)

    # The handler factory.
    h = make_handler(project_id=99)
    print("handler result:", h(7, "open"))
    print("handler hints:", get_type_hints(make_handler))
```

We exercise three Callable forms (standard, variadic, no-arg), then inspect the two `Callable` classes, then use the handler factory. The most important prints are the two `origin` lines (both `collections.abc.Callable`) and the `equal: False` line — proving that the two `Callable`s produce distinct but origin-equivalent annotations. `handler hints` will show `Callable[[int, str], dict[str, int]]` — the alias is preserved in `get_type_hints`.

## Execution Trace

```bash
$ python boardly/callable_annotations.py
example: a=1, b='x'
variadic returns: 5
no-arg returns: 42
typing.Callable origin: <class 'collections.abc.Callable'>
collections.abc.Callable origin: <class 'collections.abc.Callable'>
typing.Callable args: ([<class 'int'>], <class 'str'>)
collections.abc.Callable args: ([<class 'int'>], <class 'str'>)
equal: False
handler result: {'open': 7, 'project': 99}
handler hints: {'project_id': <class 'int'>, 'return': typing.Callable[[int, str], dict[str, int]]}
```

Three details. First, `example: a=1, b='x'` — the standard form is invoked with positional args. Second, the two `origin` lines both print `<class 'collections.abc.Callable'>` — same origin, even though the annotations themselves are not `==`-equal. Third, `handler hints` shows `typing.Callable[[int, str], dict[str, int]]` — the `Handler` alias is preserved in the function's annotations.

## Common Mistakes

### Mistake 1: Using a tuple instead of a list for the argument list

```python
def f(fn: Callable[(int, str), None]) -> None:  # ← tuple, not list
    ...
```

**Symptom:** `TypeError: Callable[(int, str), None] is not valid. Use Callable[[int, str], None]` at runtime, or a mypy error.
**Why:** PEP 484 mandates a *list* for the argument types. The convention has stuck even though `tuple` would be more semantically correct (immutable, fixed arity).
**Fix:** Use square brackets: `Callable[[int, str], None]`.

### Mistake 2: Confusing `Callable[[], T]` with `Callable[..., T]`

```python
def f(fn: Callable[[], int]) -> int:
    return fn(1)  # ← too many args
```

**Symptom:** mypy reports `error: Too many arguments` at the call site.
**Why:** `Callable[[], int]` says the function takes *zero* arguments. Passing one is a type error. The fix is either to change the signature (`Callable[[int], int]`) or use the variadic form (`Callable[..., int]`).
**Fix:** Match the Callable's argument list to what you will pass.

### Mistake 3: Mixing `typing.Callable` and `collections.abc.Callable` in the same project

```python
from typing import Callable
# file_a.py
def f(x: Callable[[int], str]) -> None: ...

# file_b.py
from collections.abc import Callable
def g(x: Callable[[int], str]) -> None: ...
```

**Symptom:** No runtime error — both work — but a reviewer cannot tell if the project is consistent. Some libraries' introspection code switches on the *class* of the annotation and treats them differently.
**Why:** The two `Callable`s are different classes (`typing._CallableGenericAlias` vs `collections.abc._CallableGenericAlias`). They are not `==`-equal.
**Fix:** Pick one and use it everywhere. In new boardly code, prefer `collections.abc.Callable`. Enforce via a `ruff` rule (e.g. disallow `typing.Callable` import). Note: FastAPI and Pydantic v2 both accept either form.

## Engineering Trade-Offs

**Decision:** Use `collections.abc.Callable` for new code; allow `typing.Callable` in legacy files without refactoring.
**Both sides:** `collections.abc.Callable` is the PEP 585 form, the long-term direction; the typing module is being thinned. `typing.Callable` is more familiar to engineers who learned typing pre-3.9, and many tutorials still use it. The two are functionally equivalent at the API level.
**Commitment:** boardly uses `collections.abc.Callable` in all new files. We do not refactor existing files on a deadline. The two are interchangeable in FastAPI, Pydantic v2, and modern Starlette — pick one and apply `ruff`'s `UP035` rule (which migrates `typing.Callable` to `collections.abc.Callable`).

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/callable_annotations.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/callable_annotations.py`
2. **Exercise 2 — Try the 3.12 shorthand.** Replace `Callable[[int], str]` with `Callable[int, str]` (no inner brackets) in `takes_typing_callable`. Run the file — confirm it still works and that `get_type_hints` normalises to `Callable[[int], str]`. `Verify: python -c "from boardly.callable_annotations import takes_typing_callable; from typing import get_type_hints; print(get_type_hints(takes_typing_callable))"`
3. **Exercise 3 — Add a `Callable[[], T]` factory type.** Define `SessionFactory = Callable[[], str]` and a function `register_factory(f: SessionFactory) -> None`. Pass a `lambda: "session"`. `Verify: python -c "from boardly.callable_annotations import register_factory; register_factory(lambda: 'session')"`
4. **Exercise 4 — Compare origins.** Print `type(h_typing)` and `type(h_abc)` and confirm they are different classes. Confirm `h_typing.__origin__ is h_abc.__origin__` (same origin class, different generic alias classes). `Verify: python -c "from boardly.callable_annotations import takes_typing_callable, takes_abc_callable; from typing import get_type_hints; t = get_type_hints(takes_typing_callable)['fn']; a = get_type_hints(takes_abc_callable)['fn']; print(type(t).__name__, type(a).__name__)"`
5. **Exercise 5 — Use `Protocol` for a callable-like interface.** Define `class Runnable(Protocol): def run(self, x: int) -> str: ...` and pass an object that satisfies it (a class with a `run` method) to a function `def execute(r: Runnable) -> str: return r.run(42)`. Compare against `Callable[[int], str]` — when does each win? `Verify: python -c "from boardly.callable_annotations import execute; class C:
    def run(self, x): return str(x)
print(execute(C()))"` (use a script if inline breaks)

## Verification

```bash
$ python boardly/callable_annotations.py
example: a=1, b='x'
variadic returns: 5
no-arg returns: 42
typing.Callable origin: <class 'collections.abc.Callable'>
collections.abc.Callable origin: <class 'collections.abc.Callable'>
typing.Callable args: ([<class 'int'>], <class 'str'>)
collections.abc.Callable args: ([<class 'int'>], <class 'str'>)
equal: False
handler result: {'open': 7, 'project': 99}
handler hints: {'project_id': <class 'int'>, 'return': typing.Callable[[int, str], dict[str, int]]}
```

If the two `origin` lines are identical but `equal: False`, you have demonstrated the `typing.Callable` vs `collections.abc.Callable` quirk. If `handler hints` shows the `Handler` alias verbatim, your alias is preserved through `get_type_hints`.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `list[int]`, `get_type_hints`. `Callable` is another builtin generic alias, with the special `[arg_list, return]` form.
- [[01-typing/04-ParamSpec-and-TypeVarTuple]] — `Callable[P, R]` with `ParamSpec` for typed decorators. Lesson 06 covers the *concrete* forms; lesson 04 covered the *parameterised* form.

## What's Next

[[01-typing/07-TypedDict]] — `TypedDict` (PEP 589) for typing dicts that come from JSON. `Callable` types *functions*; `TypedDict` types *dicts*. Three things to look for in lesson 07:

- `class TicketJSON(TypedDict): id: int; title: str` — a dict with named, typed keys.
- `total=False` and `Required`/`NotRequired` (3.11+) for optional keys.
- `ReadOnly` (3.13+, version-gated) and the `TypedDict` vs `dataclass` vs `Pydantic` decision.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.Callable — CPython reference** — https://docs.python.org/3/library/typing.html#callable-type — accessed 2026-10-23 — the canonical API for `Callable[[Arg1, Arg2], ReturnType]`, `Callable[..., T]`, and `Callable[[], T]`.
- **collections.abc.Callable — CPython reference** — https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable — accessed 2026-10-23 — the modern, PEP 585 form of `Callable` (subscriptable since 3.9).
- **PEP 484 — Type Hints (the Callable section)** — https://peps.python.org/pep-0484/#callable-types-and-lambdas — accessed 2026-10-23 — the original Callable PEP, where the `[[args], ret]` form was defined.
- **PEP 585 — Type Hinting Generics In Standard Collections** — https://peps.python.org/pep-0585/ — accessed 2026-10-23 — the PEP that made `collections.abc.Callable` subscriptable in 3.9, creating the two-Callable situation.

## What We Learned

- `Callable[[Arg1, Arg2], ReturnType]` is the standard form — a list of arg types, then the return type.
- `Callable[..., T]` is the variadic form — any signature, returns `T`.
- `Callable[[], T]` is the no-argument form — must be called with no args.
- In 3.12, `Callable[int, str]` (no inner brackets) is accepted at runtime and normalises to `Callable[[int], str]`.
- `typing.Callable` and `collections.abc.Callable` produce *distinct* generic aliases that are *not* `==`-equal but share the same `get_origin` (`collections.abc.Callable`).
- For new code, prefer `collections.abc.Callable` (PEP 585 form); `typing.Callable` works for backward compatibility.
- A `TypeAlias` like `Handler = Callable[[int, str], dict[str, int]]` documents a complex signature once and reuses it across a codebase.
