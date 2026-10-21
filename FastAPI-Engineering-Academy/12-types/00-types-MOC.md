---
title: "types — Section Map of Content"
aliases:
 - types MOC
 - 12-types MOC
tags:
 - types
 - moc
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "2–3 hours across 4 lessons"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/03-TypeVar-and-Generics]]"
---

# Section 12: `types` — Map of Content

*The grab-bag of runtime type objects that don't fit in `typing` — `NewType`, `SimpleNamespace`, `GenericAlias`, `FunctionType`, `ModuleType`, `MappingProxyType` — the types behind `list[int]`, `def f()`, `import sys`, and the read-only `signature.parameters` FastAPI walks on every request.*

**You're at the very beginning of Section 12.**

`types` is the standard-library home for the runtime type objects Python itself is built from. When you write `import math`, the resulting `math` is an *instance* of `types.ModuleType`. When you write `def f(): ...`, `f` is an instance of `types.FunctionType`. When you write `list[int]`, the result is an instance of `types.GenericAlias`. When you write `int | str` (3.10+), the result is an instance of `types.UnionType`. When `inspect.signature(f)` returns, its `.parameters` attribute is a `types.MappingProxyType` — a read-only view over a dict, and the reason no caller can mutate FastAPI's view of your signature. By the end of this section you will know the six runtime types behind the language constructs you write every day. Take your time. Type every example. **This is how you learn.**

#types #moc

## Why this section exists

Every modern Python backend — FastAPI, Pydantic, SQLAlchemy 2.0, Starlette, msgspec, beanie — eventually has to *introspect* its own code. FastAPI walks `inspect.signature(route).parameters` to know which arguments are path params, query params, dependencies, and body. Pydantic walks `__annotations__` (and `get_type_hints(..., include_extras=True)`) to know which fields a model has and what types they hold. SQLAlchemy walks `__table__` (built from a `@dataclass` or a declarative base) to know which columns to materialise. All of that introspection bottoms out in the runtime types this section covers: `MappingProxyType` for read-only views, `FunctionType` for "is this a real function or a builtin?", `GenericAlias`/`UnionType` for "what is this annotation's structure?". If you have ever wondered *what* `list[int]` evaluates to at runtime, or *why* you cannot mutate `sig.parameters`, this section is for you. You are in good company. Every senior backend engineer was once exactly here.

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[12-types/01-NewType]] | `UserId = NewType("UserId", int)` for nominal typing — mypy distinguishes `UserId` from `int`; runtime `UserId(5) is 5` is `True`; zero-cost, zero-validation, the static-only concept FastAPI pairs with `Annotated[UserId, Field(ge=0)]` for runtime-validated ids. |
| 02 | [[12-types/02-SimpleNamespace]] | `SimpleNamespace(host="0.0.0.0", port=8000)` for ad-hoc attribute bags — the `**dict` unpacking pattern, value-based `__eq__`, the silent typo trap, and the boundary that decides when `@dataclass` should win instead. |
| 03 | [[12-types/03-GenericAlias-and-UnionType]] | `types.GenericAlias` is the runtime type of `list[int]` (PEP 585, 3.9+); `types.UnionType` is the runtime type of `int | str` (PEP 604, 3.10+); `typing.get_origin`/`get_args` abstracts over both the builtin and `typing` forms; `list[int]` (`GenericAlias`) and `typing.List[int]` (`_GenericAlias`) are different runtime classes. |
| 04 | [[12-types/04-ModuleType-and-FunctionType]] | `types.ModuleType` (a module *is* an instance), `types.FunctionType` (user `def`/`lambda` — `LambdaType` is an alias), `types.BuiltinFunctionType` (C-builtins like `len`), `types.MethodType` (bound method on user class), `types.CodeType` (the `__code__` bytecode), `types.MappingProxyType` (read-only dict view — what `inspect.signature(f).parameters` is). |

## Mindmap

```mermaid
mindmap
  root((types))
    Static-only constructs
      NewType (in typing)
        nominal distinction
        runtime is identity
        zero-cost zero-validation
        Annotated pairs validator
    Attribute containers
      SimpleNamespace
        kwargs construction
        **dict unpacking
        value-based __eq__
        typo trap (silent new attr)
        loses to @dataclass for models
    Type-of-the-type
      GenericAlias
        type of list[int] (PEP 585)
        __origin__ __args__
        isinstance(x, GenericAlias)
      UnionType
        type of int | str (PEP 604)
        origin is types.UnionType
        None becomes NoneType
      typing helpers
        get_origin
        get_args
        abstraction over both forms
      Historical forms
        typing.List[int] is _GenericAlias
        typing.Union[int, str] is _UnionGenericAlias
        deprecated since 3.9
    Runtime language types
      ModuleType
        every import is an instance
        types.ModuleType(name) constructor
      FunctionType
        user def and lambda same class
        LambdaType is alias
        BuiltinFunctionType for len
        BuiltinMethodType is alias
      MethodType
        bound method on user class
        __func__ __self__
        fresh wrapper per access
      MethodWrapperType
        dunders like [].__init__
        ().__contains__
      CodeType
        function.__code__
        co_argcount co_varnames co_consts
      MappingProxyType
        read-only dict view
        writes raise TypeError
        reads reflect underlying dict
        sig.parameters IS one
```

## Suggested reading order

Read the lessons in numbered order. The first lesson (`NewType`) is the only one that lives in `typing` rather than `types` — but it is the canonical "static-only concept" framing that the rest of the section's runtime-types lessons cross-reference. `SimpleNamespace` is the runtime-class introduction to "types is the home for runtime type objects". `GenericAlias` and `UnionType` are the runtime types behind the annotations you have been writing since lesson 01 of `01-typing`. `ModuleType` and `FunctionType` close the section by exposing the runtime types behind `import` and `def`.

If you only have time for one lesson, read lesson 04 — `ModuleType`/`FunctionType`/`MappingProxyType` cover the three runtime types you will meet in every FastAPI/Pydantic introspection walk. If you have time for two, add lesson 03 — `GenericAlias`/`UnionType` is the runtime-type layer behind every annotation you write, and `get_origin`/`get_args` is the helper pair you will reach for in every introspection task.

## Concepts first-taught in this section

These concepts have their canonical lesson in `12-types/`:

- **`typing.NewType` and the "static-only concept" framing** → [[12-types/01-NewType]] — the canonical lesson for nominal-distinction zero-cost aliases (`UserId = NewType("UserId", int)`).
- **`types.SimpleNamespace` for ad-hoc attribute bags** → [[12-types/02-SimpleNamespace]] — the canonical lesson for the `**kwargs`-constructed mutable attribute container and its boundary with `@dataclass`.
- **`types.GenericAlias` and `types.UnionType` — the runtime types behind `list[int]` and `int | str`** → [[12-types/03-GenericAlias-and-UnionType]] — the canonical lesson for the type-of-the-type layer and the `typing.get_origin`/`get_args` helpers.
- **`types.ModuleType`, `types.FunctionType`, `types.MappingProxyType` — the runtime types behind `import`, `def`, and `inspect.signature`** → [[12-types/04-ModuleType-and-FunctionType]] — the canonical lesson for the language-construct runtime types and the read-only `mappingproxy` that protects `sig.parameters`.

## Cross-link: `01-typing/03-TypeVar-and-Generics`

The `types` section and the `typing` generics lesson are siblings — `typing` teaches you how to *use* `TypeVar`, `Generic`, `Annotated`, and the other static constructs; `types` teaches you what those constructs *are* at runtime. The two cross-link at three points:

- **`list[int]` is a `types.GenericAlias` instance** — `01-typing/03-TypeVar-and-Generics` teaches the parameter side (`class Stack(Generic[T])`); `12-types/03-GenericAlias-and-UnionType` teaches the runtime-type side (`type(list[int]).__name__ == "GenericAlias"`). The two are connected: `Stack[int]` and `list[int]` are both `GenericAlias` instances at runtime.
- **`NewType` is the static-only counterpart of `GenericAlias`/`UnionType`** — `12-types/01-NewType` introduces the "static-only concept" framing (mypy knows, runtime does not); `12-types/03-GenericAlias-and-UnionType` is the runtime-only counterpart (the annotation *evaluates* to a runtime object).
- **`inspect.signature(f).parameters` is the runtime view of `TypeVar`-parameterised signatures** — `01-typing/03-TypeVar-and-Generics` writes `def peek_top(stack: Stack[T]) -> T | None`; `12-types/04-ModuleType-and-FunctionType` walks the `sig.parameters` object that `inspect` produces from that signature — and reveals it is a `MappingProxyType`, the read-only contract that lets FastAPI trust its walk.

## What you will be able to do by the end

- Declare nominal-distinction ids with `NewType("UserId", int)` and articulate when it beats `int` (API contract clarity) and when it loses to `@dataclass` (when you need runtime validation, hashing, or methods).
- Reach for `SimpleNamespace` for ad-hoc attribute bags (test fixtures, config prototypes, JSON introspection of unknown shape) and reach for `@dataclass` for every persisted or serialised model — and defend the choice in code review.
- Introspect any annotation via `typing.get_origin`/`typing.get_args` — and write a recursive annotation-walker (`describe(annotation) -> str`) that renders the structure of `dict[str, list[int]]`, `int | str | None`, or any nested form.
- Distinguish the four runtime classes for "list-of-int": `types.GenericAlias` (`list[int]`), `typing._GenericAlias` (`typing.List[int]`), `types.UnionType` (`int | str`), `typing._UnionGenericAlias` (`typing.Union[int, str]`) — and know which to use (the builtin forms, always).
- Identify the runtime type of every common Python construct — `isinstance(math, types.ModuleType)`, `isinstance(f, types.FunctionType)`, `isinstance(t.close, types.MethodType)`, `isinstance(sig.parameters, types.MappingProxyType)` — and explain why `sig.parameters` is read-only.

## What's next

When you finish this section, [[13-future/00-future-MOC]] is the natural next stop — the `from __future__ import annotations` switch (PEP 563) stringifies every annotation at module-import time, which means `list[int]` is stored as the *string* `"list[int]"` rather than the `types.GenericAlias` object. Lesson [[13-future/03-When-string-annotations-break]] walks the failure modes that arise when this stringification crosses a runtime-introspection boundary like Pydantic or FastAPI's signature walk — and the section's "PEP 649 vs PEP 563" lesson walks the deferred-evaluation alternative that becomes the default in Python 3.14. Open [[12-types/01-NewType]] to begin.

**Welcome to `types`. We'll see you at the end.**

## Sources

- **types — Dynamic type creation and names for built-in types — CPython reference** — https://docs.python.org/3/library/types.html — accessed 2026-10-23 — the canonical reference for every runtime type covered in this section: `NewType`, `SimpleNamespace`, `GenericAlias`, `UnionType`, `ModuleType`, `FunctionType`, `MethodType`, `CodeType`, `MappingProxyType`.
- **PEP 585 — Type Hinting Generics In Standard Collections** — https://peps.python.org/pep-0585/ — accessed 2026-10-23 — the 3.9 PEP that made `list[int]` work and introduced `types.GenericAlias`.
- **PEP 604 — New Type Union** — https://peps.python.org/pep-0604/ — accessed 2026-10-23 — the 3.10 PEP that introduced `int | str` syntax and `types.UnionType`.
- **PEP 484 — Type Hints (the NewType section)** — https://peps.python.org/pep-0484/#newtype — accessed 2026-10-23 — the original PEP where `NewType` was introduced (3.5.3+) and the "static-only concept" rationale was articulated.
- **typing.get_origin / get_args — CPython reference** — https://docs.python.org/3/library/typing.html#typing.get_origin — accessed 2026-10-23 — the helper pair that abstracts over both the builtin and `typing` forms of generic aliases and unions, used in every annotation walk in this section.
