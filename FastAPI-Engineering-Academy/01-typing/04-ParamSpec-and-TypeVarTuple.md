---
title: "Lesson 04: ParamSpec and TypeVarTuple"
aliases:
 - ParamSpec and TypeVarTuple
 - 04-ParamSpec-and-TypeVarTuple
 - ParamSpec
 - TypeVarTuple
 - Concatenate
tags:
 - typing
 - paramspec
 - typevartuple
 - concatenate
 - variadic-generics
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[01-typing/06-Callable-and-Callable-Annotations]]"
related_lessons:
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[01-typing/06-Callable-and-Callable-Annotations]]"
 - "[[02-functools/02-wraps-and-Decorators]]"
---

# Lesson 04: ParamSpec and TypeVarTuple

*`ParamSpec("P")` parameterises over a whole signature — letting you write typed decorators that preserve the wrapped function's parameters. `TypeVarTuple("Ts")` parameterises over a variable number of types — letting you write variadic generics.*

**You're at the very beginning of Section 01's most advanced vocabulary.**

`TypeVar` (lesson 03) parameterises over a *single* type. But many real-world patterns need to parameterise over a *function's parameter list* — every typed decorator (`@functools.wraps`, `@app.route`, `@retry`, `@cache`) needs that to preserve the wrapped function's signature for callers. PEP 612 (Python 3.10) introduced `ParamSpec` for this. A second pattern needs to parameterise over *any number of types* — `tuple[*Ts]`, `class HeteroTuple[*Ts]`. PEP 646 (Python 3.11) introduced `TypeVarTuple` for this. The two together close the last gaps in the typing system, and both are used by FastAPI's internals (especially `ParamSpec` + `Concatenate` for `Depends`). Take your time. Type every example. **This is how you learn.**

#typing #paramspec #typevartuple #variadic-generics

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare** `ParamSpec("P")` and `TypeVarTuple("Ts")` and explain the difference from `TypeVar("T")`.
2. **Write** a typed decorator `def log_call(fn: Callable[P, R]) -> Callable[P, R]` that preserves the wrapped function's signature.
3. **Use** `P.args` and `P.kwargs` to forward arguments through a wrapper without losing their types.
4. **Use** `Concatenate[int, P]` to *prepend* a parameter to a `ParamSpec` — the pattern FastAPI uses to type dependency injection.
5. **Write** a variadic function `def first(*xs: *Ts) -> tuple[*Ts]` and a variadic class `class HeteroTuple(Generic[*Ts])`.

## Prerequisites

Before starting, you need:

- **[[01-typing/03-TypeVar-and-Generics]]** — `TypeVar("T")`, `class Stack(Generic[T])`, and `Callable` basics.
- **[[01-typing/06-Callable-and-Callable-Annotations]]** — the `Callable[[int, str], None]` form, since `ParamSpec` is used inside `Callable[...]`.
- **About 40–55 minutes of focused time.**

**The most common gap: not knowing `P.args` and `P.kwargs` exist.**

Students arrive having seen `*args, **kwargs` and expect `ParamSpec` to work the same way. It does *not*. A `ParamSpec` named `P` exposes *two* attributes — `P.args` (the positional parameters) and `P.kwargs` (the keyword-only parameters) — and you must use *both* in the wrapper signature: `def inner(*args: P.args, **kwargs: P.kwargs) -> R: ...`. Writing `*args: P` is a type error. This is the single most common `ParamSpec` mistake.

## The Problem

Here is the bug this lesson prevents. boardly has a logging decorator:

```python
import functools
def log_call(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} returned {result!r}")
        return result
    return inner

@log_call
def fetch_ticket(ticket_id: int, *, include_history: bool = False) -> dict:
    ...

# What is the signature of fetch_ticket after decoration?
# Without ParamSpec, mypy says: (*args: Any, **kwargs: Any) -> Any.
```

Without `ParamSpec`, the decorator's return type is `Callable[..., Any]` — every caller sees an untyped blob. The signature that `fetch_ticket` *originally* had — `ticket_id: int, include_history: bool = False, -> dict` — is gone. The IDE cannot autocomplete. Mypy cannot check the call site. Documentation generators emit garbage.

PEP 612's `ParamSpec` fixes this. With `ParamSpec`, the decorator preserves the original signature exactly:

```python
from typing import ParamSpec, TypeVar, Callable
P = ParamSpec("P")
R = TypeVar("R")
def log_call(fn: Callable[P, R]) -> Callable[P, R]: ...
```

Now `fetch_ticket`'s signature is preserved verbatim — mypy, IDE, and `inspect.signature` all see `(ticket_id: int, *, include_history: bool = False) -> dict`. That is the entire reason `ParamSpec` exists.

## The Code

```python
# boardly/paramspec_typevartuple.py
"""boardly — ParamSpec for typed decorators, TypeVarTuple for variadic generics."""
from typing import (
    ParamSpec, TypeVarTuple, TypeVar, Generic, Concatenate, Callable,
    get_type_hints, overload,
)
import functools

P = ParamSpec("P")  # A function's parameter list (a signature).
R = TypeVar("R")    # A single return type.
Ts = TypeVarTuple("Ts")  # A variable number of types.

# --- Typed decorator: log_call wraps any callable, preserving its signature. ---
def log_call(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} called")
        return result
    return inner

@log_call
def fetch_ticket(ticket_id: int, *, include_history: bool = False) -> dict:
    return {"id": ticket_id, "history": [] if not include_history else ["created"]}

# --- Concatenate: prepend a parameter to a ParamSpec ---
# A factory that "binds" a first arg into a callable of (int, *P.args, **P.kwargs).
def bind_project_id(fn: Callable[Concatenate[int, P], R], project_id: int) -> Callable[P, R]:
    @functools.wraps(fn)
    def bound(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(project_id, *args, **kwargs)
    return bound

def list_tickets(project_id: int, status: str = "open") -> list[int]:
    return [project_id, sum(ord(c) for c in status) % 1000]

bound_list = bind_project_id(list_tickets, project_id=42)
# bound_list now has signature (status: str = "open") -> list[int].

# --- Variadic generic: TypeVarTuple ---
def first(*xs: *Ts) -> tuple[*Ts]:
    """Return the input tuple unchanged (variadic in both input and output)."""
    return xs

# A variadic container, parameterised over any number of types.
class HeteroTuple(Generic[*Ts]):
    def __init__(self, *items: *Ts) -> None:
        self._items: tuple[*Ts] = items
    def __getitem__(self, i: int) -> object | None:
        try:
            return self._items[i]
        except IndexError:
            return None

if __name__ == "__main__":
    print("fetch_ticket:", fetch_ticket(1, include_history=True))
    print("bound_list:", bound_list(status="closed"))

    print("first ints:", first(1, 2, 3))
    print("first mixed:", first(1, "a", True, 3.14))

    ht = HeteroTuple(1, "a", True)
    print("HeteroTuple[0]:", ht[0])
    print("HeteroTuple[1]:", ht[1])

    # Inspect the ParamSpec and TypeVarTuple at runtime.
    print("P is:", P)
    print("Ts is:", Ts)
    print("fetch_ticket hints:", get_type_hints(fetch_ticket))
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the three TypeVars

```python
# boardly/paramspec_typevartuple.py
"""boardly — ParamSpec for typed decorators, TypeVarTuple for variadic generics."""
from typing import (
    ParamSpec, TypeVarTuple, TypeVar, Generic, Concatenate, Callable,
    get_type_hints, overload,
)
import functools

P = ParamSpec("P")  # A function's parameter list (a signature).
R = TypeVar("R")    # A single return type.
Ts = TypeVarTuple("Ts")  # A variable number of types.
```

Three parameter-spec symbols:

- `P = ParamSpec("P")` — a `ParamSpec` is like a `TypeVar` but stands for an *entire parameter list* (a signature). The string `"P"` is its name (same convention as `TypeVar`). When you write `Callable[P, R]`, the `P` is a *placeholder* for "whatever parameters the wrapped function takes".
- `R = TypeVar("R")` — an ordinary `TypeVar` for the return type. `ParamSpec` and `TypeVar` together are the canonical pair for typed decorators: `P` for the parameters, `R` for the return.
- `Ts = TypeVarTuple("Ts")` — a `TypeVarTuple` stands for a *variable number* of types (zero or more). Where `TypeVar` is one slot, `TypeVarTuple` is "fill in as many as the caller gives". The string `"Ts"` is its name; plural convention is `Ts` because it represents multiple types.

`ParamSpec` was added in Python 3.10 (PEP 612). `TypeVarTuple` was added in Python 3.11 (PEP 646). Both are available in 3.12. The `Concatenate` import we will use later is also 3.10+.

**Why are `ParamSpec` and `TypeVarTuple` separate things?**

Because they solve different problems. `ParamSpec` solves "I want to write a decorator that preserves the wrapped function's signature" — a *runtime*-signature problem. `TypeVarTuple` solves "I want to write a generic where the number of type parameters is itself variable" — a *static-typing* problem. They are complementary; both are needed for full generics. You can compose them: `Callable[Concatenate[int, P], tuple[*Ts]]` is a function whose first arg is `int`, whose middle args are `P`, and whose return is a tuple of `Ts` types.

### Lines 11–20: The typed decorator

```python
# --- Typed decorator: log_call wraps any callable, preserving its signature. ---
def log_call(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} called")
        return result
    return inner
```

The signature `def log_call(fn: Callable[P, R]) -> Callable[P, R]` is the entire point. `Callable[P, R]` means "any callable whose parameter list is `P` and whose return type is `R`". When the caller passes `fetch_ticket` — which has signature `(ticket_id: int, *, include_history: bool = False) -> dict` — mypy *infers* `P = (ticket_id: int, *, include_history: bool = False)` and `R = dict` for this particular call. The return type `Callable[P, R]` then expands to `Callable[(ticket_id: int, *, include_history: bool = False), dict]` — exactly the original signature. The signature is preserved.

The inner function uses `*args: P.args, **kwargs: P.kwargs` — the *two* attributes of `ParamSpec`. `P.args` is the tuple of positional parameter types; `P.kwargs` is the dict of keyword-only parameter types. Forwarding through `fn(*args, **kwargs)` is type-safe because `P` is the same on both sides.

`@functools.wraps(fn)` copies the `__name__`, `__doc__`, `__module__`, `__qualname__`, `__wrapped__`, and `__dict__` attributes from `fn` to `inner`. Without it, `inner.__name__` would be `"inner"` instead of `"fetch_ticket"` and `inspect.signature(fetch_ticket)` would not see the original signature. We cover `functools.wraps` in detail in the `02-functools` section.

**Why must I write both `P.args` *and* `P.kwargs`?**

Because `ParamSpec` represents the *whole* signature, which has both positional and keyword-only parts. `P.args` covers the positional parameters; `P.kwargs` covers the keyword-only ones. If you write only `*args: P.args`, mypy complains that you have lost the keyword-only parameters. The two together reconstruct the original parameter list — the *only* way to do that in a type-checker-friendly way.

### Lines 22–24: Using the decorator

```python
@log_call
def fetch_ticket(ticket_id: int, *, include_history: bool = False) -> dict:
    return {"id": ticket_id, "history": [] if not include_history else ["created"]}
```

`@log_call` wraps `fetch_ticket`. After decoration, `fetch_ticket` is the `inner` function — but mypy treats it as having the *original* signature `(ticket_id: int, *, include_history: bool = False) -> dict` thanks to `ParamSpec` inference. Callers can call `fetch_ticket(1, include_history=True)` and mypy checks the call exactly as if `log_call` had not been applied.

The `*` in the parameter list forces `include_history` to be keyword-only — so callers must write `fetch_ticket(1, include_history=True)`, not `fetch_ticket(1, True)`. This is good API design: keyword-only parameters self-document the call site. FastAPI's own route parameters use this pattern.

**Why does `@functools.wraps(fn)` matter for `ParamSpec`?**

Because at runtime, `inner` does not have `fetch_ticket`'s signature — `inner` has `(*args, **kwargs)`. `functools.wraps` copies `__wrapped__` so that `inspect.signature(inner)` *follows* `__wrapped__` and returns `fetch_ticket`'s original signature. Without `wraps`, `inspect.signature(fetch_ticket)` would show `(*args, **kwargs)` even though mypy sees the original — a confusing split between static and runtime views. `wraps` aligns them.

### Lines 26–34: `Concatenate` to prepend a parameter

```python
# --- Concatenate: prepend a parameter to a ParamSpec ---
# A factory that "binds" a first arg into a callable of (int, *P.args, **P.kwargs).
def bind_project_id(fn: Callable[Concatenate[int, P], R], project_id: int) -> Callable[P, R]:
    @functools.wraps(fn)
    def bound(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(project_id, *args, **kwargs)
    return bound
```

`Concatenate[int, P]` is the type that says "a parameter list starting with an `int` and then the parameters in `P`". So `fn: Callable[Concatenate[int, P], R]` is a callable whose first arg is `int` and whose remaining args are `P`. The wrapper returns `Callable[P, R]` — the *same* signature minus the first `int` parameter.

Inside `bound`, the call `fn(project_id, *args, **kwargs)` reconstructs the full call: the bound `project_id` plus the forwarded `args` and `kwargs`. The result is a function that "remembers" the `project_id` so the caller does not have to pass it.

**Why is `Concatenate` important for FastAPI?**

Because FastAPI's dependency injection uses `Concatenate` internally. When you write `def route(project_id: int, db: Session = Depends(get_db))`, FastAPI's `Depends` is implemented as a decorator that *prepends* the dependency's return value to the wrapped function's call. `Concatenate[Session, P]` is exactly the type signature of "the wrapped function takes a `Session` plus the user's other args". FastAPI uses this to type its own machinery. We see the same pattern in lesson 06's `Callable` discussion.

### Lines 36–41: Using `bind_project_id`

```python
def list_tickets(project_id: int, status: str = "open") -> list[int]:
    return [project_id, sum(ord(c) for c in status) % 1000]

bound_list = bind_project_id(list_tickets, project_id=42)
# bound_list now has signature (status: str = "open") -> list[int].
```

`list_tickets` has signature `(project_id: int, status: str = "open") -> list[int]`. We bind `project_id=42` into it. `bound_list` now has signature `(status: str = "open") -> list[int]` — mypy knows `project_id` is no longer a parameter; it is fixed to `42`. This is *partial application* with full type preservation.

The original `hash(status) % 1000` placeholder varied run-to-run because `hash()` is salted per Python process (PYTHONHASHSEED). We replaced it with `sum(ord(c) for c in status) % 1000`, which is a deterministic function of the string's characters. In production boardly this would be a database query; here we keep it pure and reproducible so the Execution Trace is stable across machines.

**Why does partial application need `Concatenate`?**

Because `functools.partial` *does* partial application but its return type is `functools.partial[R]` — a wrapper, not a `Callable`. mypy cannot see through `partial`'s return type to recover the original signature. `Concatenate` is the *type-level* way to say "I removed the first parameter" — the wrapper's type is `Callable[P, R]`, exactly what a caller expects.

### Lines 43–46: Variadic generics with `TypeVarTuple`

```python
# --- Variadic generic: TypeVarTuple ---
def first(*xs: *Ts) -> tuple[*Ts]:
    """Return the input tuple unchanged (variadic in both input and output)."""
    return xs
```

`*xs: *Ts` is the *unpacking* of `Ts` into the parameter list. The asterisk on `*Ts` is the type-level equivalent of `*args` — it says "Ts represents zero or more types, spread them out here". The return type `tuple[*Ts]` says "a tuple whose element types are the same Ts in the same order".

When the caller writes `first(1, "a", True)`, mypy infers `Ts = (int, str, bool)`. The input is `*xs: int, str, bool` (a 3-arg call); the return is `tuple[int, str, bool]`. The type-checker tracks the *arity* as well as the *types*. `first(1)` has `Ts = (int,)`, returns `tuple[int]`. `first()` has `Ts = ()`, returns `tuple[()]` (the empty tuple). This is *variadic* — the function adapts to the arity of the call.

**Why not just use `*xs: T` (a single TypeVar)?**

Because `T` is *one* type. `*xs: T` would say "every argument has the same type `T`" — so `first(1, 2, 3)` is fine (T=int) but `first(1, "a", True)` would be a type error (T cannot be int, str, and bool simultaneously). `*xs: *Ts` says "every argument can have a different type, captured in order". For a function that returns its arguments unchanged, `Ts` is what you want — the caller sees the exact types preserved in the return.

### Lines 48–55: A variadic class

```python
# A variadic container, parameterised over any number of types.
class HeteroTuple(Generic[*Ts]):
    def __init__(self, *items: *Ts) -> None:
        self._items: tuple[*Ts] = items
    def __getitem__(self, i: int) -> object | None:
        try:
            return self._items[i]
        except IndexError:
            return None
```

`class HeteroTuple(Generic[*Ts])` declares a class parameterised over a *variable* number of types. `HeteroTuple[int, str, bool]` is a 3-type instantiation; `HeteroTuple[int]` is a 1-type instantiation; `HeteroTuple[()]` (empty) is a 0-type instantiation. The `__init__` takes `*items: *Ts` — variadic in the constructor arguments, matching the class's type parameters.

The `__getitem__` returns `object | None` rather than something fancier because `tuple[*Ts][i]` — indexing a variadic tuple — is not well-typed in mypy without per-position tracking. The runtime works (you can index `self._items[i]`), but the static type is `object`. This is a known limitation of `TypeVarTuple` in 3.11/3.12: variadic element access loses per-position types. Pyright's experimental "variadic tuple arithmetic" can recover them; mypy as of 3.12 cannot.

**Why does `__getitem__` return `object | None` instead of a TypeVar?**

Because `Ts` is a *tuple* of types, not a single type. You cannot say "`Ts[i]`" in the type system — there is no way to index a `TypeVarTuple` to get the i-th element's type. The return type is therefore the *common supertype* of all element types, which is `object`. A `Protocol` with `__class_getitem__` tricks (we will see in lesson 05) can sometimes recover position types, but for plain `TypeVarTuple` you lose them on access. Variadic containers are most useful when you *iterate* or *unpack*, not when you *index*.

### Lines 57–73: The `__main__` block

```python
if __name__ == "__main__":
    print("fetch_ticket:", fetch_ticket(1, include_history=True))
    print("bound_list:", bound_list(status="closed"))

    print("first ints:", first(1, 2, 3))
    print("first mixed:", first(1, "a", True, 3.14))

    ht = HeteroTuple(1, "a", True)
    print("HeteroTuple[0]:", ht[0])
    print("HeteroTuple[1]:", ht[1])

    # Inspect the ParamSpec and TypeVarTuple at runtime.
    print("P is:", P)
    print("Ts is:", Ts)
    print("fetch_ticket hints:", get_type_hints(fetch_ticket))
```

We exercise the decorator, the partial application, and the variadic function/class. The last three `print` lines show: `P`'s repr is `~P` (the tilde prefix marks a ParamSpec); `Ts`'s repr is `Ts` (TypeVarTuples do not get the tilde); `get_type_hints(fetch_ticket)` returns the *original* signature's hints — `ticket_id: int`, `include_history: bool`, `return: dict` — proving the decorator preserved the signature at the type level.

The `fetch_ticket` hints are the smoking gun: even though `fetch_ticket` *is* the `inner` function (which has signature `(*args, **kwargs) -> R`), `get_type_hints` returns the *original* parameter hints — because `@functools.wraps(fn)` copied `__wrapped__` and `get_type_hints` follows `__wrapped__` when resolving the hints. This is the alignment we wanted.

## Execution Trace

```bash
$ python boardly/paramspec_typevartuple.py
fetch_ticket called
fetch_ticket: {'id': 1, 'history': ['created']}
bound_list: [42, 634]
first ints: (1, 2, 3)
first mixed: (1, 'a', True, 3.14)
HeteroTuple[0]: 1
HeteroTuple[1]: a
P is: ~P
Ts is: Ts
fetch_ticket hints: {'ticket_id': <class 'int'>, 'include_history': <class 'bool'>, 'return': <class 'dict'>}
```

Three things to verify. First, `fetch_ticket` is callable with the *original* parameter names — `fetch_ticket(1, include_history=True)` works because the signature is preserved. Second, `first(1, "a", True, 3.14)` returns a 4-tuple matching the 4 input types — variadic in the input arity. Third, `fetch_ticket hints` shows the original parameter names and types, not `(*args, **kwargs)`. That last line is the proof the decorator did its job.

## Common Mistakes

### Mistake 1: Writing `*args: P` instead of `*args: P.args, **kwargs: P.kwargs`

```python
def inner(*args: P, **kwargs: P) -> R:  # ← type error
    return fn(*args, **kwargs)
```

**Symptom:** mypy reports `error: ParamSpec "P" cannot be used in this context`.
**Why:** `ParamSpec` itself is not a type you can put on `*args` — it represents a whole signature. You must use the *two* attributes `P.args` (positional) and `P.kwargs` (keyword-only).
**Fix:**

```python
def inner(*args: P.args, **kwargs: P.kwargs) -> R:
    return fn(*args, **kwargs)
```

### Mistake 2: Forgetting `@functools.wraps` and breaking `inspect.signature`

```python
def log_call(fn: Callable[P, R]) -> Callable[P, R]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        ...
    return inner  # ← no @wraps
```

**Symptom:** mypy sees the correct signature (ParamSpec preserved statically) but `inspect.signature(fetch_ticket)` at runtime shows `(*args, **kwargs)`. Any framework that introspects at runtime (FastAPI!) now sees the wrong signature.
**Why:** `ParamSpec` is a *static* mechanism — it tells the type-checker the signature is preserved. At runtime, the inner function still has `(*args, **kwargs)` literally. `@functools.wraps(fn)` copies `__wrapped__` so `inspect.signature` *follows* the wrap chain and reports the original.
**Fix:** Always use `@functools.wraps(fn)` on the inner function of a decorator.

### Mistake 3: Subscripting `TypeVarTuple` without the asterisk

```python
class HeteroTuple(Generic[Ts]):  # ← missing *; TypeError
    ...
```

**Symptom:** `TypeError: Plain TypeVarTuple is not subscriptable` at class-definition time.
**Why:** `TypeVarTuple` represents a *variable number* of types; you must unpack it with `*` to use it as a type parameter. `Generic[Ts]` looks like you are passing a single TypeVarTuple, which makes no sense for `Generic`.
**Fix:**

```python
class HeteroTuple(Generic[*Ts]):
    ...
```

## Engineering Trade-Offs

**Decision:** Use `ParamSpec` for every typed decorator in boardly; use `TypeVarTuple` only where the arity genuinely varies (currently only the `first` utility and one shape-shifting container).
**Both sides:** `ParamSpec` adds one import and a tiny bit of indirection. The alternative — `Callable[..., Any]` — is shorter but loses all type information at the call site. `TypeVarTuple` adds real complexity (variadic types are subtle); the alternative — `tuple[Any, ...]` — is simpler but loses per-position types.
**Commitment:** boardly uses `ParamSpec` for every decorator that wraps a callable. We use `TypeVarTuple` only where the return type genuinely tracks the input arity (e.g., a function that returns its arguments unchanged). For most variadic uses, `tuple[Any, ...]` is fine; we do not use `TypeVarTuple` for `*args` forwarding, only for the rare case where the *return* type depends on the input arity.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/paramspec_typevartuple.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/paramspec_typevartuple.py`
2. **Exercise 2 — Add a retry decorator.** Write `def retry(fn: Callable[P, R]) -> Callable[P, R]` that retries the wrapped function up to 3 times on exception. Use it on a function that randomly fails. `Verify: python -c "from boardly.paramspec_typevartuple import retry; import random; @retry
def f(x: int) -> int: return x
print(f(1))"` (multiline; use a script if the inline form is awkward)
3. **Exercise 3 — Bind two parameters.** Extend `bind_project_id` to bind *two* arguments using `Concatenate[int, int, P]`. Call it `bind_two`. `Verify: python -c "from boardly.paramspec_typevartuple import bind_two; def f(a:int,b:int,c:int)->int: return a+b+c; b = bind_two(f, 1, 2); print(b(3))"`
4. **Exercise 4 — Variadic sum.** Write `def sum_all(*xs: *Ts) -> float` that returns `sum(xs)` as a float (all elements must be `int | float` — use a `Protocol` bound). Confirm `sum_all(1, 2, 3.5)` returns `6.5`. `Verify: python -c "from boardly.paramspec_typevartuple import sum_all; print(sum_all(1, 2, 3.5))"`
5. **Exercise 5 — Compose `ParamSpec` and `TypeVarTuple`.** Write `def apply_variadic(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R` that just forwards — then write a variadic variant `def apply_to_all(fn: Callable[[int], R], *xs: int) -> list[R]`. Decide where each pattern fits and document. `Verify: python -c "from boardly.paramspec_typevartuple import apply_to_all; print(apply_to_all(lambda x: x*2, 1, 2, 3))"`

## Verification

```bash
$ python boardly/paramspec_typevartuple.py
fetch_ticket called
fetch_ticket: {'id': 1, 'history': ['created']}
bound_list: [42, 634]
first ints: (1, 2, 3)
first mixed: (1, 'a', True, 3.14)
HeteroTuple[0]: 1
HeteroTuple[1]: a
P is: ~P
Ts is: Ts
fetch_ticket hints: {'ticket_id': <class 'int'>, 'include_history': <class 'bool'>, 'return': <class 'dict'>}
```

If `fetch_ticket hints` shows the original signature's hints — not `(*args, **kwargs)` — the decorator's signature preservation is verified end-to-end (static type preserved by `ParamSpec`, runtime signature preserved by `functools.wraps`).

## Previously Learned Here

- [[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T")` for one type. `ParamSpec` is the same idea but parameterises over a *signature*; `TypeVarTuple` parameterises over *multiple* types.
- [[01-typing/06-Callable-and-Callable-Annotations]] — `Callable[[int, str], None]`. `ParamSpec` is used *inside* `Callable[P, R]` and `Concatenate[...]` — without `Callable`, `ParamSpec` has no use.

## What's Next

[[01-typing/05-Protocol-Structural-Typing]] — `Protocol` for duck typing with a static type-checker. `TypeVar`'s `bound=X` lets you restrict a generic to `Shape` and its subclasses — but what if you do not have a class hierarchy, just a *shape* (a set of methods)? `Protocol` lets you write structural types: "anything with a `close()` method" can be a `Closable`, even if it does not inherit from anything. Three things to look for in lesson 05:

- `class Closable(Protocol): def close(self) -> None: ...` — defining a protocol.
- `@runtime_checkable` — what it does and what it *cannot* check (signatures, only names).
- When `Protocol` beats `ABC` (often) and when `ABC` beats `Protocol` (rarely).

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.ParamSpec — CPython reference** — https://docs.python.org/3/library/typing.html#typing.ParamSpec — accessed 2026-10-23 — the canonical API for `ParamSpec`, including `P.args`, `P.kwargs`, and `Concatenate`.
- **typing.TypeVarTuple — CPython reference** — https://docs.python.org/3/library/typing.html#typing.TypeVarTuple — accessed 2026-10-23 — the canonical API for `TypeVarTuple` and the `*Ts` unpacking syntax.
- **PEP 612 — Parameter Specification Variables** — https://peps.python.org/pep-0612/ — accessed 2026-10-23 — the PEP that introduced `ParamSpec` and `Concatenate` in 3.10.
- **PEP 646 — Variadic Generics** — https://peps.python.org/pep-0646/ — accessed 2026-10-23 — the PEP that introduced `TypeVarTuple` and `*Ts` unpacking in 3.11.

## What We Learned

- `ParamSpec("P")` parameterises over a function's *parameter list*; `P.args` and `P.kwargs` are the two attributes you must use in the wrapper signature.
- `Callable[P, R]` lets a typed decorator preserve the wrapped function's signature — `log_call(fn: Callable[P, R]) -> Callable[P, R]` is the canonical form.
- `Concatenate[int, P]` prepends a parameter to a `ParamSpec` — the type of "the wrapped function takes an `int` plus `P`". FastAPI uses this internally for `Depends`.
- `@functools.wraps(fn)` is mandatory for runtime signature preservation; `ParamSpec` is mandatory for static signature preservation. You need both.
- `TypeVarTuple("Ts")` parameterises over a *variable* number of types; `*Ts` unpacks it into a parameter list, return type, or class base.
- Variadic element access (`tuple[*Ts][i]`) loses per-position types in 3.12 mypy — variadic generics are best for iterate/unpack patterns, not for indexing.
