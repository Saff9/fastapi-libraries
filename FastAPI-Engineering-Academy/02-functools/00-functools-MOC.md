---
title: "functools — Map of Content"
aliases:
 - functools MOC
 - Section 02 MOC
tags:
 - functools
 - moc
status: complete
course_level: intermediate
---

# Section 02: `functools`

*The standard-library module that turns ordinary functions into cached, dispatched, partially-applied, and orderable functions. FastAPI, Pydantic, and Starlette all live here for one reason or another — `lru_cache` for dependency caching, `wraps` for every decorator you write, `singledispatch` for type-driven dispatch, and `cached_property` for lazy attributes.*

**You're at the very beginning of Section 02.**

`functools` is the quietest module in the standard library. You use it every day — `@lru_cache` on a settings loader, `@wraps` on every decorator you ship, `functools.reduce` when someone reaches for it on a code review — and yet most engineers have never read its source. This section corrects that. By the end you will know which function to reach for, which to avoid, and the precise reason FastAPI's `Depends` cache is a `lru_cache`-shaped idea under a different name.

#functools #moc

## Lessons in this section

| # | Lesson | What you learn | Tags |
|---|--------|----------------|------|
| 01 | [[02-functools/01-lru_cache-and-Caching]] | `@lru_cache(maxsize=N)`, the 3.9+ `cache()` shortcut, `cache_info()`, `cache_clear()`, the thread-safety lock, the 3.9 typed form `@lru_cache[int]`. When `lru_cache` beats `cached_property`. | `canonical` |
| 02 | [[02-functools/02-wraps-and-Decorators]] | `@wraps(fun)`, `WRAPPER_ASSIGNMENTS`, `__wrapped__`, why every decorator needs `@wraps`, the `inspect.signature` interaction that breaks without it. | `canonical` |
| 03 | [[02-functools/03-partial]] | `partial(fun, *args, **kwargs)`, `partialmethod` for classes, when `partial` beats a lambda, `partial` vs `operator.itemgetter`. | |
| 04 | [[02-functools/04-singledispatch]] | `@singledispatch` + `@fun.register(Type)`, the MRO resolution, `@singledispatchmethod` (3.8+), the FastAPI `Depends` parallel. | |
| 05 | [[02-functools/05-reduce]] | `reduce(fun, iterable, initial)`, why `reduce` is discouraged in favour of a loop, the "never use `reduce`" opinion and the rare cases where it genuinely wins. | |
| 06 | [[02-functools/06-cached_property]] | `@cached_property`, the per-instance threading lock (3.12 implementation), `cached_property` vs `lru_cache` vs `functools.cached_property` on a slotted class — and the bug that breaks the last one. | |
| 07 | [[02-functools/07-total_ordering]] | `@total_ordering`, the `__lt__` + `__eq__` minimum, the generated methods, the perf cost. | |

## Suggested reading order

1. [[02-functools/01-lru_cache-and-Caching]] — the canonical lesson. Every later lesson assumes you have read this.
2. [[02-functools/02-wraps-and-Decorators]] — the second canonical. Without `@wraps`, your decorator's signature lies to `inspect.signature`, and FastAPI relies on that signature.
3. [[02-functools/06-cached_property]] — read immediately after `lru_cache`; the two are constantly compared and you must know the line between them.
4. [[02-functools/04-singledispatch]] — the FastAPI `Depends` parallel lives here.
5. [[02-functools/03-partial]] — the glue used by every decorator you'll write.
6. [[02-functools/05-reduce]] — short, opinionated, and the one lesson that tells you *not* to use the feature it teaches.
7. [[02-functools/07-total_ordering]] — close the section with the data-model helper you'll use on every `Project` and `Ticket` you sort.

## Concepts first-taught in this section

These concepts have their canonical lesson in `02-functools/`:

- **`functools.lru_cache`** → [[02-functools/01-lru_cache-and-Caching]] — the canonical lesson.
- **`functools.wraps`** → [[02-functools/02-wraps-and-Decorators]] — the canonical lesson.
- **`functools.singledispatch`** → [[02-functools/04-singledispatch]] — the canonical lesson for type-driven dispatch.
- **`functools.cached_property`** → [[02-functools/06-cached_property]] — the canonical lesson for per-instance lazy attributes.

## What's next

When you finish this section, [[03-contextlib/00-contextlib-MOC]] is the natural next stop. `functools` and `contextlib` share a common ancestor: both turn ordinary Python syntax (functions, generators, `with` blocks) into something reusable and composable. The `cached_property` ↔ `contextmanager` comparison is the single most useful bridge between the two.

## Sources

- **`functools` — Higher-order functions and operations on callable objects** — https://docs.python.org/3.12/library/functools.html — accessed 2026-10-23 — the canonical reference for every API used in this section.
