---
title: "contextlib — Map of Content"
aliases:
 - contextlib MOC
 - Section 03 MOC
tags:
 - contextlib
 - moc
status: complete
course_level: intermediate
---

# Section 03: `contextlib`

*The standard-library module that turns generators into context managers, async generators into async context managers, and `ContextVar`s into the FastAPI request-scoped state primitive. Every `with` block you write lives here.*

**You're at the very beginning of Section 03.**

`contextlib` is the bridge between `functools` and FastAPI. Where `functools` gives you function-level primitives, `contextlib` gives you resource-lifecycle primitives — the `with` block you write to open a database session, the `async with` you write to acquire a lock, the `ContextVar` FastAPI sets in middleware and reads in your dependency. By the end of this section you will know how `@contextmanager` actually works under the hood (a generator that yields exactly once, wrapped in a `__enter__`/`__exit__` synthesised pair), how `ExitStack` lets you manage dynamic lists of resources, and why a DB session per request is a `ContextVar` and not a global. Take your time. Type every example. **This is how you learn.**

#contextlib #moc

## Lessons in this section

| # | Lesson | What you learn | Tags |
|---|--------|----------------|------|
| 01 | [[03-contextlib/01-contextmanager]] | `@contextmanager`, the `try`/`yield`/`finally` pattern, the exception-rethrow behaviour, `contextmanager` vs a class with `__enter__`/`__exit__`. | `canonical` |
| 02 | [[03-contextlib/02-asynccontextmanager]] | `@asynccontextmanager`, `async yield`, the `async with` interaction, the FastAPI `Depends` async-generator parallel. | `canonical` |
| 03 | [[03-contextlib/03-ExitStack-and-AsyncExitStack]] | `ExitStack()`, `enter_context()`, `push()`, `callback()`, dynamic context management, the resource-cleanup order. | |
| 04 | [[03-contextlib/04-suppress]] | `with suppress(KeyError): ...`, the `None`-return behaviour, when `suppress` beats a bare `try`/`except`/`pass`. | |
| 05 | [[03-contextlib/05-contextvars]] | **THE FastAPI request-scoped primitive** (PEP 567). `ContextVar`, `.get()/.set()`, the copy-on-create semantics for asyncio tasks, why a DB session per request is a `ContextVar`. | `canonical` |
| 06 | [[03-contextlib/06-redirect_stdout-stderr]] | `redirect_stdout`, `redirect_stderr`, `redirect_stdin`, testing with captured output. | |
| 07 | [[03-contextlib/07-contextmanager-decorator-internals]] | How `@contextmanager` works: the generator wrapper, `_GeneratorContextManager`, the `__enter__`/`__exit__` it synthesises. Senior deep-dive. | |

## Suggested reading order

1. [[03-contextlib/01-contextmanager]] — the canonical lesson. Every other lesson in this section assumes you have read this.
2. [[03-contextlib/02-asynccontextmanager]] — the async sibling, and the shape FastAPI's `Depends` async-generator dependencies use.
3. [[03-contextlib/05-contextvars]] — THE FastAPI request-scoped primitive. Read this third because it depends on the `@contextmanager` lesson for the `token_reset` pattern.
4. [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — the dynamic-resource manager. Pay attention to the cleanup order.
5. [[03-contextlib/04-suppress]] — short, opinionated, and the right tool for a common case.
6. [[03-contextlib/06-redirect_stdout-stderr]] — testing utilities you'll reach for in test code.
7. [[03-contextlib/07-contextmanager-decorator-internals]] — the senior deep-dive on how `@contextmanager` synthesises the protocol. Close the section here.

## Concepts first-taught in this section

These concepts have their canonical lesson in `03-contextlib/`:

- **`contextlib.contextmanager`** → [[03-contextlib/01-contextmanager]] — the canonical lesson.
- **`contextlib.asynccontextmanager`** → [[03-contextlib/02-asynccontextmanager]] — the canonical lesson.
- **`contextvars.ContextVar`** → [[03-contextlib/05-contextvars]] — the canonical lesson for the FastAPI request-scoped state primitive.

## What's next

When you finish this section, [[04-collections/00-collections-MOC]] is the natural next stop. The `collections` module (`Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`) shares `contextlib`'s composability ethos — each tool is small, focused, and combines cleanly with the others. The `ChainMap` ↔ `Context` comparison is the bridge.

## Sources

- **`contextlib` — Utilities for with-statement contexts** — https://docs.python.org/3.12/library/contextlib.html — accessed 2026-10-23 — the canonical reference for every API used in this section.
- **`contextvars` — Context Variables** — https://docs.python.org/3.12/library/contextvars.html — accessed 2026-10-23 — PEP 567, the request-scoped state primitive.
- **PEP 567 — Context Variables** — https://peps.python.org/pep-0567/ — accessed 2026-10-23 — the PEP that introduced `ContextVar` in 3.7.
