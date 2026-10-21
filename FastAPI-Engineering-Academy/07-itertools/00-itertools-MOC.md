---
title: itertools — Map of Content
aliases:
 - itertools MOC
 - it MOC
tags:
 - moc
 - itertools
status: complete
---

# Section 07 — `itertools` — Map of Content

*The iterator-algebra module. Lazy, memory-efficient, one-pass streaming primitives that let you compose pipelines over huge (or infinite) inputs without materialising them.*

**You're at the very beginning of Section 07.**

`itertools` is the module that makes Python's "everything is an iterator" promise pay off. Every function here returns an iterator — one-shot, lazy, O(1) memory. You chain them to build pipelines: `islice(cycle(data), 100)` for a bounded round-robin; `groupby(sorted(rows, key=...), key=...)` for a streaming group-by; `chain.from_iterable(map(lambda r: r.items(), batches))` for a flat stream. The whole module is ~20 functions, none longer than 40 lines of C. Master them once and your loops get smaller, faster, and more honest.

#itertools #streaming #lazy

## Lessons

| # | Lesson | What you learn |
|---|---|---|
| 01 | [[07-itertools/01-chain-and-islice]] | `chain` (concatenate), `chain.from_iterable` (flatten), `islice` (lazy slice — no negatives). *Canonical.* |
| 02 | [[07-itertools/02-groupby]] | `groupby` groups CONSECUTIVE same-key elements — sort first or you get duplicate groups. |
| 03 | [[07-itertools/03-starmap-and-accumulate]] | `starmap(func, tuples)`, `accumulate` (running sum / max / product). |
| 04 | [[07-itertools/04-product-combinations-permutations]] | `product` (Cartesian), `combinations`, `permutations`. The combinatorial-explosion warning. |
| 05 | [[07-itertools/05-cycle-repeat-count]] | The three infinite iterators. `cycle`, `repeat` (the `map` filler), `count` (infinite arithmetic). |
| 06 | [[07-itertools/06-dropwhile-takewhile-filterfalse]] | `dropwhile` (drop the prefix), `takewhile` (take the prefix then STOP), `filterfalse` (anti-`filter`). |
| 07 | [[07-itertools/07-tee-and-zip_longest]] | `tee` (fork an iterator — memory cost), `zip_longest` (zip with fillvalue). |

## Reading order

Start with [[07-itertools/01-chain-and-islice]] (the lazy primitives) → [[07-itertools/02-groupby]] (the gotcha that catches every senior engineer once) → the rest in order. The lessons are self-contained; read any one standalone.

## Concepts first taught here

- **Streaming pipelines** (`chain` + `islice` + `groupby`) — taught in Lesson 01 and 02.
- **Infinite iterators** (`cycle`, `repeat`, `count`) — taught in Lesson 05.
- **The `tee` memory cost** — taught in Lesson 07.

## Prerequisites

- [[05-collections-abc/04-Iterator-vs-Iterable]] — the `__iter__` vs `__next__` distinction. `itertools` functions return iterators; you need to know what that means before reading.
- [[04-collections/03-deque]] — `deque(maxlen=N)` is the non-iterator sliding window that complements `islice`.

## What's next

[[08-pathlib/00-pathlib-MOC]] — file paths are the most common infinite iterator you'll walk. Or jump to [[18-operator/03-functional-composition]] for how `operator.add` plugs into `reduce` and `accumulate`.
