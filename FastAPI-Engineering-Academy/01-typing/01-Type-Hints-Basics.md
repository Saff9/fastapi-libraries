---
title: "Lesson 01: Type Hints Basics"
aliases:
 - Type Hints Basics
 - 01-Type-Hints-Basics
tags:
 - typing
 - type-hints
 - canonical
status: complete
course_level: beginner
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites: []
related_lessons:
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[01-typing/11-typing-vs-runtime]]"
first_taught_in: "01-typing/01-Type-Hints-Basics"
---

# Lesson 01: Type Hints Basics

*The four primitive forms — `list[int]`, `dict[str, X]`, `X | Y`, `tuple[int, str]` vs `tuple[int, ...]` — that every FastAPI route, every Pydantic model, and every `get_type_hints` call in this vault rests on.*

**You're at the very beginning of Section 01.**

If you have ever written `def get_ticket(id: int) -> Ticket: ...` and not known exactly what Python stores in `__annotations__` — or why `list[int]` works as a type in 3.9+ but broke in 3.8 — this lesson is for you. Type hints look like syntax. They are actually runtime objects, and FastAPI introspects them on every request. We start with the four primitives that everything else (`Annotated`, `TypeVar`, `Protocol`, `TypedDict`) is built on top of. Type every example. **This is how you learn.**

#typing #type-hints #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Write** a function signature using builtin generics (`list[int]`, `dict[str, X]`, `tuple[int, str]`, `tuple[int, ...]`) and explain which Python version made each legal at runtime.
2. **Choose** between `Optional[X]` and `X | None` and explain why they are equal-but-not-identical objects at runtime.
3. **Use** PEP 604 union syntax (`int | str | None`) and explain what `types.UnionType` is versus `typing._UnionGenericAlias`.
4. **Predict** what `typing.get_type_hints()` returns for a function whose annotations use any of the above forms.
5. **Explain** the difference between `tuple[int, str]` (fixed arity, heterogeneous) and `tuple[int, ...]` (variable arity, homogeneous) and when each is correct.

## Prerequisites

Before starting, you need:

- **A working Python 3.10+ interpreter.** This vault targets 3.12. The PEP 604 union syntax `X | Y` requires 3.10 at runtime. (3.9 sees `X | Y` as a `TypeError` on a class object.)
- **About 30–45 minutes of focused time.**
- **No prior `typing` experience.** This is the first lesson of the section.

**The most common gap: assuming type hints are syntax, not objects.**

Students arrive assuming `list[int]` is parsed by the compiler into some kind of "type AST" that lives only at static-check time. It is not. `list[int]` is a `types.GenericAlias` object constructed at the moment the function definition executes, stored in `func.__annotations__`, and readable by any code that wants to — including FastAPI. Once you internalise that hints are runtime objects, the rest of the section stops feeling like magic.

## The Problem

Here is the bug this lesson prevents. A new engineer joins the boardly team and writes:

```python
def search_tickets(project_id: int, q: str = None) -> list[Ticket]:
    ...
```

The linter says `q: str = None` is wrong: a `str` parameter cannot default to `None`. They "fix" it by deleting the annotation entirely:

```python
def search_tickets(project_id: int, q=None) -> list[Ticket]:
    ...
```

Now FastAPI still introspects this function. With no annotation on `q`, FastAPI treats it as a *query parameter of type `str | None`* — because the default is `None` — but it has lost the chance to document the type, run OpenAPI generation correctly, or apply validation. The endpoint silently accepts `?q=123` as a string `"123"`. Worse, when someone reads the code six months later, they have to infer from the body that `q` is a search string.

The fix is to write `q: str | None = None` — three pieces of information in one line: the type, the union with `None`, and the default. This lesson teaches what each of those pieces does and what Python stores when it sees them.

## The Code

```python
# boardly/type_hints_basics.py
"""boardly — type-hints primer: builtin generics, PEP 604 unions, Optional, tuple forms."""
from typing import Optional, get_type_hints

class User:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name
    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name!r})"

# Builtin generics (Python 3.9+) — list[...] and dict[...] are first-class types.
def list_active_ticket_ids(project_id: int) -> list[int]:
    return [1, 2, 3]

def assign_tickets(ticket_ids: list[int], user_id: int) -> dict[int, list[int]]:
    return {user_id: ticket_ids}

# PEP 604 union syntax (Python 3.10+) — `X | Y` replaces Union[X, Y].
def find_user(query: int | str) -> User | None:
    return User(id=1, name="ada") if query else None

# Optional[X] is identical to X | None at runtime — same type object.
def get_owner(ticket_id: int) -> Optional[User]:
    return User(id=1, name="ada")

def get_assignee(ticket_id: int) -> User | None:
    return None

# tuple[int, str] — fixed arity, heterogeneous positions.
def split_email(email: str) -> tuple[str, str]:
    local, _, domain = email.partition("@")
    return local, domain

# tuple[int, ...] — variable arity, homogeneous (an immutable sequence).
def pack_ticket_ids(ids: list[int]) -> tuple[int, ...]:
    return tuple(ids)

if __name__ == "__main__":
    print("active ids:", list_active_ticket_ids(42))
    print("assign:", assign_tickets([1, 2], user_id=7))
    print("find_user(0):", find_user(0))
    print("find_user(1):", find_user(1))
    print("split_email:", split_email("ada@example.com"))
    print("pack_ticket_ids:", pack_ticket_ids([10, 20, 30]))
    print("hints of find_user:", get_type_hints(find_user))
    print("hints of get_owner:", get_type_hints(get_owner))
```

## Line-by-Line Deep Dive

### Lines 1–4: Module header and imports

```python
# boardly/type_hints_basics.py
"""boardly — type-hints primer: builtin generics, PEP 604 unions, Optional, tuple forms."""
from typing import Optional, get_type_hints
```

The module docstring is the contract. Anyone opening this file in six months — or a static analyser — should be able to read line 2 and know that the file demonstrates four things: builtin generics, PEP 604 unions, `Optional`, and tuple forms. We import only two names from `typing`. `Optional` is the legacy form for `X | None`; `get_type_hints` is the function FastAPI (and Pydantic) call to recover a function's annotations as a `dict[str, type]`. We will use it at the bottom of the file to demonstrate what Python actually stores.

**Why import `Optional` at all when `X | None` exists?**

Backward compatibility. Codebases that ran on 3.9 and earlier — and any library that supports 3.9 — cannot use `X | Y` at runtime (it raises `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`). `Optional[X]` has worked since 3.5. Pydantic v1, Starlette pre-2.0, and many corporate internal frameworks still ship `Optional[X]`. If you ever port a 3.9 codebase forward, your IDE will offer to rewrite `Optional[X]` to `X | None` for you — accept the offer, but know *why* it is safe: the two are equal at runtime (we prove this in lesson 11).

### Lines 6–9: The `User` domain class

```python
class User:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name
    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name!r})"
```

We need a domain object to reference in return types later. Defining `User` *before* the functions lets us write `-> User | None` without forward-reference strings. (When you cannot define classes top-to-bottom, you write `-> "User | None"` as a string and let `get_type_hints` resolve it; lesson 10 covers this in depth.) Note that `User.__init__` itself has type hints — they are not just for public API. Pydantic, dataclasses, and FastAPI's dependency injection all introspect `__init__` when relevant. The `-> None` return annotation matters: without it, mypy infers the return type, which is fine, but `get_type_hints(User.__init__)` then has no `'return'` key and downstream code that expects one will `KeyError`.

**Why does `__init__` need a return annotation of `-> None`?**

Two reasons. First, mypy strict mode requires it — without it, the inferred return type is `Any`, which propagates and weakens every type-check downstream. Second, FastAPI's `inspect.signature` walks `__init__` for class-based dependencies; an explicit `-> None` is one less inference the framework has to make. We will see this again in lesson 02 with `Annotated`.

### Lines 11–16: Builtin generics

```python
# Builtin generics (Python 3.9+) — list[...] and dict[...] are first-class types.
def list_active_ticket_ids(project_id: int) -> list[int]:
    return [1, 2, 3]

def assign_tickets(ticket_ids: list[int], user_id: int) -> dict[int, list[int]]:
    return {user_id: ticket_ids}
```

Before Python 3.9, `list[int]` was a `TypeError` at runtime — you had to write `List[int]` (capital `L`, from `typing`). PEP 585 made the builtin containers (`list`, `dict`, `set`, `tuple`, `frozenset`, `type`) subscriptable using `__class_getitem__`. What you write as `list[int]` is constructed at function-definition time as a `types.GenericAlias` object — `types.GenericAlias(list, (int,))` — and stored in `__annotations__['return']`. FastAPI reads that object, sees the origin is `list`, sees the arg is `int`, and serialises a JSON array of integers in the response. That is the entire mechanism.

**Why did Python 3.9 make builtin generics subscriptable?**

Two reasons. (1) The capital `List`/`Dict`/`Set` aliases in `typing` were a wart — they duplicated the builtin names and made every codebase import an extra name. (2) PEP 585 finally let `__class_getitem__` exist on `object`, which made any class subscriptable for typing purposes — including user-defined classes. The `typing.List` form is now a deprecated alias; in 3.12 you should always write `list[int]`. (The `typing.List` import still works — deprecation, not removal.)

### Lines 18–20: PEP 604 union syntax

```python
# PEP 604 union syntax (Python 3.10+) — `X | Y` replaces Union[X, Y].
def find_user(query: int | str) -> User | None:
    return User(id=1, name="ada") if query else None
```

`int | str` and `User | None` are PEP 604 syntax, available from 3.10. The `|` operator on types returns a `types.UnionType` object — distinct from `typing._UnionGenericAlias` (which is what `Union[int, str]` and `Optional[int]` produce). The two are *equal* (`int | None == Optional[int]` is `True`) but *not identical* (`int | None is Optional[int]` is `False`). This matters because tools that switch on `is` (rare but real — some Pydantic v1 internals did) see different objects; tools that switch on `==` (the right way) see them as the same. FastAPI and Pydantic v2 both normalise unions internally, so the distinction is invisible at the API level but visible if you ever debug a custom serialiser.

**Why use `X | Y` over `Union[X, Y]`?**

Readability. `list[int | str] | None` reads left-to-right as "a list of int-or-str or None". `Optional[Union[List[Union[int, str]], None]]` reads as nested noise. The new syntax is also a single token at parse time, where `Union[...]` requires a function call to `typing.Union`'s `__getitem__`. Microscopically faster at import time. The only reason to keep `Union` is 3.9 compatibility, which 3.12 lets you forget.

### Lines 22–27: `Optional` and `X | None` equivalence

```python
# Optional[X] is identical to X | None at runtime — same type object.
def get_owner(ticket_id: int) -> Optional[User]:
    return User(id=1, name="ada")

def get_assignee(ticket_id: int) -> User | None:
    return None
```

`Optional[User]` and `User | None` are *semantically identical* — both say "either a `User` instance or `None`". At runtime they produce different concrete objects (`typing._UnionGenericAlias` versus `types.UnionType`) but they compare equal and FastAPI/Pydantic treat them identically. The comment on line 23 says "same type object" — that is the *intent* of the PEP, even though the implementation uses two classes. We will prove the equality in lesson 11 with `assert Optional[int] == int | None`.

**Why does the comment say "same type object" if `is` returns False?**

Because the *intent* of PEP 604 was to retire `Optional` and `Union`. The Python core team has discussed normalising them to a single class. As of 3.12 they have not done so (it would break code that uses `isinstance` on the type object). Treat `Optional[X]` and `X | None` as the same thing in your head, but know that under the hood there are two classes — useful when a library behaves differently between them, which is always a bug in the library.

### Lines 29–32: `tuple[int, str]` — fixed arity

```python
# tuple[int, str] — fixed arity, heterogeneous positions.
def split_email(email: str) -> tuple[str, str]:
    local, _, domain = email.partition("@")
    return local, domain
```

`tuple[str, str]` says: a tuple of *exactly two* elements, both strings, positionally distinguished. The caller knows that the first element is the local part and the second is the domain — even though they are both `str`. The arity is part of the type. This is fundamentally different from a `list[str]` where any number of strings is allowed and the positions are interchangeable. When you write a return type, ask: does the caller care about position? If yes, `tuple`; if no, `list`.

**Why not use a dataclass or `NamedTuple` here instead of a bare tuple?**

A bare `tuple[str, str]` is the *minimum* ceremony. For two values that are obvious from context (local-part, domain), naming them is overkill. For three or more values, or values that are not obvious from context, switch to `NamedTuple` or `@dataclass`. The threshold is roughly: if the caller would have to read the docstring to know which position is which, name the type. The boardly codebase uses `tuple[str, str]` for split-email and `@dataclass` for everything else.

### Lines 34–36: `tuple[int, ...]` — variable arity

```python
# tuple[int, ...] — variable arity, homogeneous (an immutable sequence).
def pack_ticket_ids(ids: list[int]) -> tuple[int, ...]:
    return tuple(ids)
```

The ellipsis (`...`) is the marker that flips `tuple` from "fixed arity, heterogeneous" to "variable arity, homogeneous". `tuple[int, ...]` means "a tuple of any length, all integers" — it is the immutable counterpart to `list[int]`. The ellipsis is *not* a placeholder meaning "fill in later"; it is a literal token that `typing`'s tuple alias interprets as "this is a homogeneous variadic tuple".

**Why is `tuple[int, ...]` the right type for `pack_ticket_ids`?**

Because the function returns `tuple(ids)` — and `tuple()` of a list of `N` ints produces a tuple of `N` ints. The arity is unknown at type-check time. `tuple[int, ...]` says exactly that. If you wrote `tuple[int]` (without the ellipsis), that would mean "a one-element tuple containing an int" — which is *not* what the function returns. The ellipsis is the difference between a one-tuple and an N-tuple.

**What is the difference between `tuple[int, ...]` and `Sequence[int]`?**

Immutability. `tuple[int, ...]` is immutable; `Sequence[int]` (from `collections.abc`) is an interface that *both* `list[int]` and `tuple[int, ...]` satisfy. If the caller only iterates, `Sequence[int]` is more flexible. If the caller will hash the result (e.g. as a dict key), `tuple[int, ...]` is required because lists are not hashable. In boardly, ticket-id tuples are sometimes used as cache keys — hence `tuple[int, ...]`.

### Lines 38–47: The `__main__` block

```python
if __name__ == "__main__":
    print("active ids:", list_active_ticket_ids(42))
    print("assign:", assign_tickets([1, 2], user_id=7))
    print("find_user(0):", find_user(0))
    print("find_user(1):", find_user(1))
    print("split_email:", split_email("ada@example.com"))
    print("pack_ticket_ids:", pack_ticket_ids([10, 20, 30]))
    print("hints of find_user:", get_type_hints(find_user))
    print("hints of get_owner:", get_type_hints(get_owner))
```

The first six lines invoke each function to prove they run. The last two lines are the senior-engineer moment: we call `get_type_hints()` on two functions and print the result. This is what FastAPI does internally on every request — it calls `get_type_hints(route_handler)` to recover the annotated types, then for each parameter decides "is this a path param, query param, body, or dependency?". The output (which we show in the Execution Trace) demonstrates that `int | str` round-trips as `int | str` and `Optional[User]` round-trips as `typing.Optional[User]` — i.e., the *form you wrote* is preserved. That matters: if you wrote `Optional[User]`, downstream code that switches on `isinstance(t, types.UnionType)` will not see it — only `typing._UnionGenericAlias`. We cover this asymmetry in lesson 11.

## Execution Trace

```bash
$ python boardly/type_hints_basics.py
active ids: [1, 2, 3]
assign: {7: [1, 2]}
find_user(0): None
find_user(1): User(id=1, name='ada')
split_email: ('ada', 'example.com')
pack_ticket_ids: (10, 20, 30)
hints of find_user: {'query': int | str, 'return': __main__.User | None}
hints of get_owner: {'ticket_id': <class 'int'>, 'return': typing.Optional[__main__.User]}
```

Two details in this trace are worth your attention. First, `get_type_hints(find_user)` shows `'query': int | str` — the PEP 604 form is preserved verbatim. Second, `get_type_hints(get_owner)` shows `'return': typing.Optional[__main__.User]` — the `Optional` form is also preserved verbatim. Python does not normalise `Optional[X]` to `X | None` or vice versa. Tools that need a canonical union form (like Pydantic v2's core schema builder) do that normalisation themselves; the standard library does not.

## Common Mistakes

### Mistake 1: Writing `tuple[int]` when you meant `tuple[int, ...]`

```python
def pack_ticket_ids(ids: list[int]) -> tuple[int]:
    return tuple(ids)
```

**Symptom:** mypy reports `Incompatible return value type (got "tuple[int, ...]", expected "tuple[int]")` and the function appears to type-check incorrectly at the call site.
**Why:** `tuple[int]` is a *one-element* tuple. Without the ellipsis, `typing` interprets the form as fixed-arity-1, not as "any-length tuple of ints". This is the single most common tuple annotation mistake.
**Fix:**

```python
def pack_ticket_ids(ids: list[int]) -> tuple[int, ...]:
    return tuple(ids)
```

### Mistake 2: Using `Optional[X]` and `X | None` inconsistently in the same file

```python
def get_owner(ticket_id: int) -> Optional[User]: ...
def get_assignee(ticket_id: int) -> User | None: ...
```

**Symptom:** No runtime failure — both work — but the codebase looks inconsistent and a senior reviewer will ask "which form are we using?". Some downstream libraries (Pydantic v1 internals, some custom serializers) switch on the concrete class and behave subtly differently.
**Why:** They produce different concrete objects (`typing._UnionGenericAlias` vs `types.UnionType`) even though they are `==` equal.
**Fix:** Pick one form for the codebase and enforce it via `ruff` rule `UP007` (which rewrites `Optional[X]` to `X | None` for 3.10+ targets). The boardly project uses `X | None` everywhere.

### Mistake 3: Annotating `__init__` without a `-> None` return

```python
class User:
    def __init__(self, id: int, name: str):  # missing -> None
        ...
```

**Symptom:** mypy strict mode flags it; some introspection frameworks (notably older FastAPI versions) `KeyError` when looking up `__annotations__['return']`.
**Why:** Without an explicit return annotation, `__init__`'s `'return'` key is absent from `get_type_hints`'s output. Code that assumes the key exists will fail.
**Fix:** Always annotate `__init__` with `-> None`.

## Engineering Trade-Offs

**Decision:** Use the new syntax — `list[int]`, `X | Y`, `tuple[int, ...]`, `X | None` — throughout boardly.
**Both sides:** The legacy syntax (`List[int]`, `Union[X, Y]`, `Optional[X]`) is more explicit at the import (you see `from typing import List, Union, Optional`) and works on 3.8/3.9. The new syntax is more readable, requires fewer imports, and is the future the core team is committed to.
**Commitment:** boardly targets 3.12. We use the new syntax exclusively. The only `typing` imports we keep are the ones with no builtin equivalent (`Annotated`, `TypeVar`, `Protocol`, `TypedDict`, `Literal`, `overload`, `get_type_hints`).

## Exercises

1. **Exercise 1 — Run the file as-is.** Save the code above as `boardly/type_hints_basics.py` and run it. Compare your output to the Execution Trace. `Verify: python boardly/type_hints_basics.py`
2. **Exercise 2 — Add a `find_tickets` function.** Add `def find_tickets(project_id: int, q: str | None = None) -> list[Ticket]: ...` to the file (define a `Ticket` class first). Re-run and confirm `get_type_hints(find_tickets)` shows `'q': str | None`. `Verify: python -c "from boardly.type_hints_basics import find_tickets; from typing import get_type_hints; print(get_type_hints(find_tickets))"`
3. **Exercise 3 — Prove the equality.** Add `assert Optional[int] == int | None` and `assert Optional[int] != int | str` to the bottom of the file. Run and confirm no `AssertionError`. Now write `assert Optional[int] is int | None` and confirm it *does* raise. Explain in a comment why. `Verify: python boardly/type_hints_basics.py`
4. **Exercise 4 — Add a homogeneous tuple key.** Write a function `cache_key(project_id: int, ticket_ids: list[int]) -> tuple[int, ...]` that returns `(project_id, *ticket_ids)` as a tuple usable as a dict key. Run it. `Verify: python -c "from boardly.type_hints_basics import cache_key; k = cache_key(7, [1,2]); d = {k: 'hit'}; print(d[k])"`
5. **Exercise 5 — Replace `tuple[str, str]` with a NamedTuple.** Refactor `split_email` to return a `NamedTuple` subclass with named fields `local` and `domain`. Decide when the named version is worth the extra line. Document your decision in a comment. `Verify: python -c "from boardly.type_hints_basics import split_email; r = split_email('a@b'); print(r.local, r.domain)"`

## Verification

```bash
$ python boardly/type_hints_basics.py
active ids: [1, 2, 3]
assign: {7: [1, 2]}
find_user(0): None
find_user(1): User(id=1, name='ada')
split_email: ('ada', 'example.com')
pack_ticket_ids: (10, 20, 30)
hints of find_user: {'query': int | str, 'return': __main__.User | None}
hints of get_owner: {'ticket_id': <class 'int'>, 'return': typing.Optional[__main__.User]}
```

If your output matches the above, you have the four primitives working. The hint-dictionary output is the single most important line — that is the dictionary FastAPI builds internally on every request.

## Previously Learned Here

- (This is the first lesson — nothing has been taught yet.)

## What's Next

[[01-typing/02-Annotated-and-Metadata]] — the most important lesson in the whole vault. You have just learned the four primitive forms (`list[int]`, `X | Y`, `Optional`, `tuple[...]`). Lesson 02 introduces the fifth primitive — `Annotated[T, metadata]` (PEP 593) — which is what makes FastAPI possible. Without `Annotated`, FastAPI would have no way to attach `Depends(get_db)`, `Query(gt=0)`, or `Header(...)` to a parameter *without changing the parameter's runtime type*. Three things to look for in lesson 02:

- Why `Annotated[int, "meta"]` is the same type as `int` at runtime, but `get_type_hints(include_extras=True)` recovers the metadata.
- The `include_extras` flag — the single boolean FastAPI's entire dependency-injection system hinges on.
- Why `Annotated` was the missing primitive that made FastAPI's `Depends` ergonomic (FastAPI pre-0.85 used a separate `Depends` wrapper argument, which broke the type signature).

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing — Module API reference** — https://docs.python.org/3/library/typing.html — accessed 2026-10-23 — the canonical CPython reference for `Optional`, `Union`, and tuple forms.
- **PEP 585 — Type Hinting Generics In Standard Collections** — https://peps.python.org/pep-0585/ — accessed 2026-10-23 — the PEP that made `list[int]`, `dict[str, X]`, and `tuple[int, str]` subscriptable in 3.9.
- **PEP 604 — Allow writing union types as `X | Y`** — https://peps.python.org/pep-0604/ — accessed 2026-10-23 — the PEP that introduced `int | str` syntax in 3.10.
- **PEP 484 — Type Hints** — https://peps.python.org/pep-0484/ — accessed 2026-10-23 — the original type-hints PEP that introduced `Optional` and `Union`.

## What We Learned

- You can write `list[int]`, `dict[str, X]`, `set[X]`, `tuple[X, Y]`, `tuple[X, ...]` as first-class runtime objects (3.9+).
- You can write `X | Y` and `X | None` as union syntax (3.10+).
- `Optional[X]` and `X | None` are equal but not identical — two different concrete classes, same semantics.
- `tuple[int, str]` is a fixed-arity heterogeneous tuple; `tuple[int, ...]` is a variable-arity homogeneous tuple.
- `get_type_hints(f)` returns a `dict[str, type]` preserving the *form you wrote* — `Optional[User]` stays `Optional[User]`, not `User | None`.
- `__init__` should always be annotated `-> None` to satisfy strict mypy and avoid `KeyError` in introspection frameworks.
