---
title: "decimal — Section Map of Content"
aliases:
 - decimal MOC
 - 17-decimal MOC
tags:
 - decimal
 - moc
 - foundation
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "2–3 hours across 3 lessons"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
---

# decimal — Section Map of Content

*The `Decimal` type, the `Context` precision/rounding machinery, and the never-use-`float`-for-money rule — the standard-library answer to "why did my total come out as 0.30000000000000004".*

**You're at the very beginning of Section 17.**

`decimal` is the standard library's base-10 number type. Where `float` is a binary approximation of a decimal (so `0.1 + 0.2` is `0.30000000000000004`, not `0.3`), `Decimal("0.1") + Decimal("0.2")` is exactly `Decimal("0.3")` — every digit you typed is preserved, every arithmetic operation is base-10 long addition, every comparison is digit-by-digit equality. The module exists because money is base-10, the law is base-10, and binary floats cannot represent `0.10` exactly. If your code touches a dollar amount, a tax rate, a unit price, or an invoice total, you use `Decimal`; if you use `float`, you ship a billing bug that compounds across thousands of transactions before anyone notices.

This section gives you the type (lesson 01), the precision and rounding control (lesson 02), and the Pydantic/FastAPI integration with the never-accept-float rule at the boundary (lesson 03). By the end you will know why every money field in a boardly API model is `Decimal`, why the response is a JSON string, and why the request refuses a JSON number with a `422`.

#decimal #moc #foundation

## Why this section exists

Every senior backend engineer hits the float bug at least once. You write `price * qty` for a line item, the unit tests pass with round numbers, and somewhere between a hundred and a thousand transactions the total drifts by a cent — sometimes over, sometimes under, never the same direction twice. The fix is not `round(..., 2)` (that hides the bug, it does not fix it); the fix is `decimal.Decimal`. The whole module is one sentence: "use a base-10 number type for base-10 values, and stop pretending binary floats are good enough for money".

But the section does not stop there. The `decimal` module exposes a *Context* object that controls precision (significant digits, not decimal places) and rounding mode (banker's by default, half-up on request for consumer tax). The `localcontext()` context manager lets you scope a precision/rounding override to a single function — essential on a multi-threaded FastAPI server where you cannot safely mutate the global thread-local context. And the Pydantic v2 / FastAPI integration has a quiet trap: a `Decimal` field accepts both strings and JSON numbers by default, capturing the float's imprecision silently on the number path; the section's `field_validator(mode='before')` pattern is the discipline that makes the boundary loudly wrong instead of silently wrong.

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[17-decimal/01-Decimal-Basics]] | `Decimal("0.10")` (always pass a string, never `Decimal(0.1)` which captures the float's exact value), arithmetic (`+`/`-`/`*`/`/`), the exactness guarantee (`Decimal("1.00") + Decimal("0.01") == Decimal("1.01")`), `as_tuple()` for digit-level inspection, and the cardinal rule: never use `float` for money. |
| 02 | [[17-decimal/02-Context-and-precision]] | `getcontext()` and `.prec=28` (significant digits, not decimal places), `Context(prec=N, rounding=MODE)` for a custom context, `localcontext()` as the scoped context-manager form, the six rounding modes (`ROUND_HALF_EVEN` banker's default vs `ROUND_HALF_UP` consumer-tax), `quantize(Decimal("0.01"))` for currency-scale rounding, and the `Overflow`/`InvalidOperation`/`FloatOperation` signals. |
| 03 | [[17-decimal/03-Decimal-in-APIs]] | `Decimal` in a Pydantic model, `str(Decimal)` serialisation contract (`"1.00"` not `1.0`), the `response_model` schema (`anyOf: [number, string]` on the request, `string` on the response), the `@field_validator(mode='before')` that rejects `isinstance(value, float)` and turns the silent acceptance into a `422`, and the `int`-cents alternative. |

## Mindmap

```mermaid
mindmap
  root((decimal))
    Construction
      Decimal("0.10") string
      Decimal(0.1) float-bug
      Decimal(10) int OK
      as_tuple sign digits exponent
    Arithmetic
      + - * /
      Exact base-10
      Decimal Decimal
      Mixed types raise TypeError
    Context
      getcontext thread-local
      prec 28 significant digits
      rounding ROUND_HALF_EVEN default
      Context(prec, rounding) custom
      localcontext scoped
      traps dict
    Rounding
      quantize Decimal 0.01
      ROUND_HALF_EVEN banker's
      ROUND_HALF_UP consumer-tax
      ROUND_DOWN truncate
      ROUND_05UP tax tables
      per-call rounding= kwarg
    Signals
      InvalidOperation trapped
      Overflow trapped
      DivisionByZero trapped
      FloatOperation off default
      Inexact Rounded off default
    API integration
      Pydantic Decimal field
      str serialisation
      model_dump_json string
      jsonable_encoder
      Field max_digits decimal_places
      field_validator mode before
      reject float -> 422
      int-cents alternative
    Cross-links
      06-dataclasses 01-dataclass-Basics
      03-contextlib 01-contextmanager
      09-enum 05-Enum-in-APIs
      01-typing 02-Annotated
```

## Reading order

Read the lessons in numbered order. Lesson 01 is the canonical foundation — the string-constructor rule and the exactness guarantee. Every later lesson assumes you have internalised "always pass a string". Lesson 02 (Context and precision) builds on lesson 01 — the precision and rounding model only makes sense once you understand that `Decimal` is exact and the context controls *when* rounding happens. Lesson 03 (Decimal in APIs) builds on both — the Pydantic integration needs the type (lesson 01) and the scoped-override pattern (lesson 02) for the tax computation example.

If you only have time for one lesson, read lesson 01. It is enough to stop shipping the float bug; the context and API lessons are refinements.

If you have time for two, read 01 and 03 — you will know how to put a `Decimal` on the wire safely, even if you skip the precision and rounding machinery (which you can pick up later when a tax-rate calculation forces the question).

## Concepts first-taught in this section

These concepts have their canonical lesson in `17-decimal/`:

- **`Decimal`** → [[17-decimal/01-Decimal-Basics]] — the canonical lesson for the type, the string-constructor rule, and the never-float-for-money rule.
- **`decimal.Context` and `localcontext`** → [[17-decimal/02-Context-and-precision]] — the canonical lesson for the precision/rounding model and the scoped context manager.
- **`Decimal` in Pydantic / FastAPI** → [[17-decimal/03-Decimal-in-APIs]] — the canonical lesson for the API integration, the float-rejecting validator, and the `int`-cents alternative.

## Prerequisites

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. The `budget: Decimal` annotation on a dataclass or Pydantic model is the field-level contract; you need to be comfortable reading an annotation as a type.
- **A typed model** — [[06-dataclasses/01-dataclass-Basics]]. The section's running example is `boardly`'s `Project` model, and the `@dataclass` decorator is what generates the surrounding `__init__`/`__repr__`/`__eq__`. The Pydantic `BaseModel` (lesson 03) is the validation-bearing sibling of `@dataclass`; the two share the field-with-default pattern.
- **Annotated metadata** — [[01-typing/02-Annotated-and-Metadata]] is recommended before lesson 03, because `Annotated[Decimal, Field(max_digits=12, decimal_places=2)]` is the v2-idiomatic form for attaching constraints to the type.
- **The context-manager protocol** — [[03-contextlib/01-contextmanager]] is recommended before lesson 02, because `localcontext()` is a textbook use of `__enter__`/`__exit__` and the lesson reads the protocol without re-explaining it.

## What you will be able to do by the end

- Construct a `Decimal` correctly: `Decimal("0.10")` from a string, never `Decimal(0.1)` from a float, and explain *why* the difference matters.
- Explain why `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` is `True` while the float version is `False` — base-10 vs base-2 arithmetic.
- Read `as_tuple()` and reconstruct a `Decimal`'s value from its `sign`, `digits`, and `exponent`.
- Use `with localcontext() as ctx: ctx.prec = 10` to scope a precision override and confirm the change reverts on `__exit__`.
- Use `Decimal.quantize(Decimal("0.01"))` for currency-scale rounding, and explain why `quantize` is the right API where `round()` is the wrong one.
- Implement the "never accept float from JSON" rule with `@field_validator(mode='before')` and turn Pydantic's silent acceptance into a `422`.
- Read the OpenAPI schema FastAPI generates for a `Decimal` field and explain the difference between the request schema (`anyOf: [number, string]`) and the response schema (`string`).
- Defend the choice of `Decimal` over `int`-cents, naming the trade-off (scale tracking and fractional-cent support vs speed and JSON-nativeness).

## What's next

When you finish this section, the natural next stops are [[18-operator/00-operator-MOC]] (the `operator` module — `operator.add` and friends for functional-style money pipelines) and [[19-weakref/00-weakref-MOC]] (the `weakref` module — for caching `Decimal` computations without preventing garbage collection). For the FastAPI arc, the most relevant cross-link is [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` alternative to Pydantic's `BaseModel`, and the field-with-default pattern that both share. Open [[17-decimal/01-Decimal-Basics]] to begin.

**Welcome to decimal. We'll see you at the end.**

## Sources

- **`decimal` — Decimal fixed-point and floating-point arithmetic** — https://docs.python.org/3/library/decimal.html — accessed 2026-10-23 — the canonical CPython reference for `Decimal`, `Context`, `localcontext`, `quantize`, the rounding modes, and the signal classes.
- **IBM General Decimal Arithmetic Specification** — http://speleotrove.com/decimal/decarith.html — accessed 2026-10-23 — the IBM specification the `decimal` module implements; the base-10 arithmetic rules and the rounding-mode definitions.
- **Pydantic v2 — Types: `Decimal`** — https://docs.pydantic.dev/2.12/concepts/types/#decimal — accessed 2026-10-23 — Pydantic v2's `Decimal` field documentation, including the `max_digits`/`decimal_places` constraints and the default string serialisation.
