---
title: "operator — Section Map of Content"
aliases:
 - operator MOC
 - 18-operator MOC
tags:
 - operator
 - moc
status: complete
course_level: intermediate
difficulty: intermediate
---

# Section 18: `operator` — Map of Content

*The `itemgetter`, `attrgetter`, `methodcaller` trio plus the infix-operator function table — the functional-programming primitives that turn `sorted(rows, key=lambda r: r[1])` into `sorted(rows, key=itemgetter(1))` and `OPS["+"](2, 3)` into a real dispatch table.*

**You're at the very beginning of Section 18.**

`operator` is the standard-library module that gives a name to every infix. `+` is `operator.add` (callable as a function), `in` is `operator.contains`, `getattr(obj, "name")` is `operator.attrgetter("name")(obj)`. The point is not to replace the syntax — `a + b` is always clearer than `operator.add(a, b)` — but to make the operator *passable as a value* to `reduce`, `partial`, `map`, `filter`, and dispatch tables. By the end of this section you will know the three factories (`itemgetter`, `attrgetter`, `methodcaller`), the three operator tables (arithmetic, bitwise, logical/container), and the opinion that `sum()` beats `reduce(operator.add, ...)` every single time.

#operator #moc

## Lessons in this section

| # | Lesson | What you learn | Tags |
|---|--------|----------------|------|
| 01 | [[18-operator/01-itemgetter-attrgetter]] | `itemgetter(1)` returns `lambda x: x[1]`, `itemgetter(0, 2)` returns a multi-index tuple extractor, `attrgetter("name")` returns `lambda x: x.name`, `attrgetter("owner.name")` walks dotted attributes, and the C-accelerated fast path that beats a Python `lambda` on every `key=` call site. | `canonical` |
| 02 | [[18-operator/02-methodcaller]] | `methodcaller("strip")` returns `lambda s: s.strip()`, `methodcaller("split", ",")` pre-binds the positional arg, `methodcaller("replace", " ", "-")` for the positional-only `str.replace` case, and the sort-by-method-result pattern without a `lambda`. | |
| 03 | [[18-operator/03-functional-composition]] | The arithmetic table (`add`, `sub`, `mul`, `truediv`, `floordiv`, `mod`, `pow`), the bitwise table (`and_`, `or_`, `xor`, `invert`, `lshift`, `rshift`), `operator.truth`/`not_`/`contains`, the `reduce(operator.add, nums)` pattern, and the opinion that a list comprehension usually beats `reduce(operator.add, ...)`. | |

## Mindmap

```mermaid
mindmap
  root((operator))
    Factories
      itemgetter
        single index
        multi-index tuple
        C fast path
      attrgetter
        single attr
        dotted path<br/>owner.name
        C fast path
      methodcaller
        no args<br/>strip
        positional args<br/>split ","
        keyword args<br/>split sep=","
        dunder trap<br/>__len__
    Infix tables
      Arithmetic
        add sub mul
        truediv floordiv
        mod pow
      Bitwise
        and_ or_ xor
        invert (unary)
        lshift rshift
      Comparison
        lt le eq ne
        ge gt
        is_ is_not
      Logical
        truth
        not_
      Container
        contains(a, b)<br/>== b in a
        countOf indexOf
        length_hint
      In-place
        iadd isub
        imul itruediv
        iand ior ixor
    Composition
      functools.partial
        partial(contains, WATCH)
      functools.reduce
        reduce(add, nums)
        opinion: use sum()
      Dispatch tables
        OPS["+"] = operator.add
```

## Suggested reading order

1. [[18-operator/01-itemgetter-attrgetter]] — the canonical lesson. Every later lesson assumes you have read it. The two factories (`itemgetter`, `attrgetter`) are the C-implemented siblings of the trivial `lambda`s that production code reaches for at every `key=` call site.
2. [[18-operator/02-methodcaller]] — the third factory. Reads immediately after `attrgetter` because the two share the "callable factory that returns a 1-arg extractor" shape. The lesson's pivot is "where `attrgetter` reads, `methodcaller` calls".
3. [[18-operator/03-functional-composition]] — the infix-operator function table and the `reduce` composition. Reads last because it cross-links to [[02-functools/05-reduce]] for the canonical reduce opinion — read the reduce lesson in parallel if you haven't already.

If you only have time for one lesson, read lesson 01 — `itemgetter` and `attrgetter` cover 80% of the production use of `operator`. If you have time for two, add lesson 03 — the operator table is the second-most-used surface, and the opinion ("`sum` beats `reduce(operator.add, ...)`") is the lesson's whole point.

## Concepts first-taught in this section

These concepts have their canonical lesson in `18-operator/`:

- **`operator.itemgetter`** → [[18-operator/01-itemgetter-attrgetter]] — the canonical lesson for the `__getitem__` extraction factory.
- **`operator.attrgetter`** → [[18-operator/01-itemgetter-attrgetter]] — the canonical lesson for the `__getattr__` extraction factory with dotted-path support.
- **`operator.methodcaller`** → [[18-operator/02-methodcaller]] — the canonical lesson for the "call a method by name" factory.
- **The `operator` infix function table** → [[18-operator/03-functional-composition]] — the canonical lesson for `operator.add`/`mul`/`and_`/`or_`/`contains` and the `reduce` composition.

## Cross-link: `functools.partial`

The `operator` factories and the `functools.partial` curry-pattern are the two halves of point-free style in Python. `partial` fixes function arguments; `operator` provides the function-from-syntax primitive. The two compose: `partial(operator.contains, WATCH)` is a 1-argument predicate built from the `operator` table and the `partial` currier. The boardly codebase uses this composition in `boardly/tickets/filters.py` — see [[02-functools/03-partial]] for the canonical `partial` lesson and the side-by-side comparison with `itemgetter`.

## What you will be able to do by the end

- Reach for `itemgetter`/`attrgetter` at every `key=` call site — and never write `lambda r: r[1]` again.
- Use `methodcaller` for any single-method-callable (`.strip`, `.split(",")`, `.replace(" ", "-")`) at every `key=` and `map` site.
- Read the `operator` infix function table — `add`, `mul`, `and_`, `or_`, `contains`, `truth`, `not_` — and reach for the function form only when the operation is genuinely a value.
- Articulate the "`sum` beats `reduce(operator.add, ...)`" opinion and the three rare cases where `reduce` survives.
- Compose `operator` with `functools.partial` to build predicate factories (`partial(operator.contains, WATCH)`) — the two modules are designed to work together.

## What's next

When you finish this section, [[19-weakref/00-weakref-MOC]] is the natural next stop — `weakref.finalize(obj, operator.attrgetter("close"), resource)` is the canonical composition of `operator` (provides the callable) with `weakref` (provides the lifecycle hook). Or, if you'd rather see the operator+itertools composition, [[07-itertools/00-itertools-MOC]] (still being written) will cover `starmap(operator.add, pairs)` and `accumulate(iterable, operator.mul)`.

## Sources

- **`operator` — Standard operators as functions** — https://docs.python.org/3/library/operator.html — accessed 2026-10-23 — the canonical reference for every API used in this section.
