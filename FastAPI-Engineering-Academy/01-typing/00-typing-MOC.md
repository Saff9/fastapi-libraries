---
title: "typing — Section Map of Content"
aliases:
 - typing MOC
 - 01-typing MOC
tags:
 - typing
 - moc
 - foundation
status: complete
course_level: beginner
difficulty: beginner
estimated_time: "5–8 hours across 11 lessons"
prerequisites: []
---

# typing — Section Map of Content

*The module FastAPI introspects on every single request — and the foundation half the other sections rest on.*

**You're at the very beginning of Section 01.**

`typing` is the most important module in this vault. When you write `def get_ticket(id: int) -> Ticket: ...` in a FastAPI route, FastAPI does not just *read* the signature — it calls `typing.get_type_hints(func, include_extras=True)` to recover every `Annotated[...]` you attached, then dispatches a dependency, validates the body, and serialises the response based on what it finds. Half of FastAPI is `typing` plus `inspect`. Master this section and the rest of the course reads like English.

#typing #moc #foundation

## Why this section exists

Every modern Python backend — FastAPI, Pydantic, SQLAlchemy 2.0, Starlette, msgspec, beanie — leans on `typing` for one of three jobs: introspection (FastAPI reading your route signature), validation (Pydantic constructing a model from `Annotated[int, Field(gt=0)]`), and ergonomic data shape (TypedDict for JSON envelopes, Protocol for plug-in points). If you have ever written `Annotated[int, Depends(get_db)]` and not known exactly what `Annotated` does — or what `inspect` call FastAPI makes to read it — this section is for you. If you have ever had a `from __future__ import annotations` file silently break a Pydantic model, this section is for you. You are in good company. Every senior backend engineer was once exactly here.

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[01-typing/01-Type-Hints-Basics]] | `list[int]`, `dict[str, X]`, `X | Y` (PEP 604), `Optional[X]` vs `X | None`, and the `tuple[int, str]` vs `tuple[int, ...]` distinction. |
| 02 | [[01-typing/02-Annotated-and-Metadata]] | `Annotated[T, ...metadata]` (PEP 593) is the primitive FastAPI introspects via `get_type_hints(..., include_extras=True)` — the most important lesson in the vault. |
| 03 | [[01-typing/03-TypeVar-and-Generics]] | `TypeVar("T")`, bounds, constraints, and `class Stack(Generic[T])` for parameterised classes that stay type-correct. |
| 04 | [[01-typing/04-ParamSpec-and-TypeVarTuple]] | `ParamSpec("P")` for typed decorators, `TypeVarTuple("Ts")` for variadic generics, and `Concatenate` (Python 3.10+). |
| 05 | [[01-typing/05-Protocol-Structural-Typing]] | `Protocol` (PEP 544) for duck typing with a static checker, `@runtime_checkable` and what it cannot check. |
| 06 | [[01-typing/06-Callable-and-Callable-Annotations]] | `Callable[[int, str], None]`, `Callable[..., T]`, the 3.12 `Callable[int, str]` shorthand, and `collections.abc.Callable` vs `typing.Callable`. |
| 07 | [[01-typing/07-TypedDict]] | `TypedDict` (PEP 589) for typed dicts the JSON body parses into, with `total=False`, `Required`/`NotRequired`, and `ReadOnly` (3.13+, version-gated). |
| 08 | [[01-typing/08-Literal-and-TypeGuard]] | `Literal["active", "archived"]` (PEP 586), `LiteralString` (3.11+), `TypeGuard` (3.10+), and `TypeIs` (3.13+, version-gated). |
| 09 | [[01-typing/09-Overload]] | `@overload` for multiple signatures with one runtime implementation, and why mypy needs the stubs. |
| 10 | [[01-typing/10-Future-Annotations]] | `from __future__ import annotations` (PEP 563) stringifies annotations; PEP 649 (deferred evaluation, default in 3.14) and when string annotations break FastAPI/Pydantic. |
| 11 | [[01-typing/11-typing-vs-runtime]] | What evaluates at runtime vs what is stored as strings: `get_type_hints()` vs `__annotations__`, `ForwardRef`, and the `include_extras` flag FastAPI depends on. |

## Mindmap

```mermaid
mindmap
  root((typing))
    Construction
      PEP 604 union<br/>int | str
      Builtin generics<br/>list[int] dict[str, X]
      tuple forms<br/>tuple[int, str] vs tuple[int, ...]
    Metadata
      Annotated (PEP 593)
        FastAPI Depends
        Pydantic Field
        get_type_hints include_extras
    Generics
      TypeVar
        bound
        constraints
      Generic[T]
      ParamSpec (3.10+)
      TypeVarTuple (3.11+)
      Concatenate (3.10+)
    Shapes
      Protocol (structural)
      TypedDict (PEP 589)
      Callable
      Literal (PEP 586)
    Type narrowing
      TypeGuard (3.10+)
      TypeIs (3.13+ version-gated)
    Signatures
      overload
      from __future__ import annotations
      get_type_hints vs __annotations__
```

## Reading order

Read the lessons in numbered order. The first three — Basics, `Annotated`, `TypeVar` — are the prerequisites for everything afterwards. `Protocol` and `TypedDict` are independent of each other but both build on the generics vocabulary from lesson 03. `10-Future-Annotations` and `11-typing-vs-runtime` are deliberately last because they explain *what Python does internally* with all the constructs above — and that is the layer FastAPI lives at.

If you only have time for three lessons, read 01, 02, and 11. Those three are enough to understand what FastAPI does on every request.

## Prerequisites

None. This is the foundation. The only thing we assume is that you can read a Python function signature and that you have written `def f(x: int) -> str:` at least once. If you have never seen a type hint before, lesson 01 starts from `list[int]` and `dict[str, int]` — nothing earlier is required.

## What you will be able to do by the end

- Read a FastAPI route signature and predict exactly which `typing` calls FastAPI will make.
- Write `Annotated[T, metadata]` confidently and know whether the metadata will survive a `get_type_hints` call.
- Choose between `Protocol`, `TypedDict`, `Callable`, and `dataclass` for a given JSON shape and defend the choice.
- Explain why `from __future__ import annotations` breaks some Pydantic models and not others.
- Read `typing` source in CPython and not get lost.

## What's next

Once you finish lesson 11, you have the typing vocabulary the rest of the course assumes. [[02-functools/00-functools-MOC]] picks up with `lru_cache`, `wraps`, `partial`, and `singledispatch` — and lesson 04 of that section (`singledispatch`) leans directly on `ParamSpec` and `Callable` from this section. Open [[01-typing/01-Type-Hints-Basics]] to begin.

**Welcome to typing. We'll see you at the end.**

## Sources

- **typing — Module API reference** — https://docs.python.org/3/library/typing.html — accessed 2026-10-23 — the canonical CPython reference for every construct in this section.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the `Annotated` PEP, the foundation FastAPI is built on.
