---
title: "Lesson 04: product, combinations, permutations"
aliases:
 - itertools.product
 - itertools.combinations
 - itertools.permutations
 - itertools.combinations_with_replacement
tags:
 - itertools
 - combinatorics
 - product
 - combinations
 - permutations
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[07-itertools/01-chain-and-islice]]"
 - "[[07-itertools/03-starmap-and-accumulate]]"
related_lessons:
 - "[[07-itertools/03-starmap-and-accumulate]]"
 - "[[18-operator/01-itemgetter-attrgetter]]"
 - "[[04-collections/03-deque]]"
---

# Lesson 04: `product`, `combinations`, `permutations`

*The four combinatorial primitives — `product(*iterables, repeat=1)` is the Cartesian product, `combinations(iterable, r)` is the no-repetition subsets, `permutations(iterable, r=None)` is the all-orderings enumeration, `combinations_with_replacement(iterable, r)` is the multiset subsets — and the math that warns you `len(list(product(alphabet, repeat=6)))` is 308,915,776 and materialising it would take ~25 GB of RAM.*

**You're at the very beginning of Section 07, Lesson 04.**

`itertools.product`, `combinations`, `permutations`, and `combinations_with_replacement` are the four primitives that turn a small input into a very large output. Each yields tuples lazily, one at a time, O(1) in memory — until you call `list(...)` on the result, at which point the entire enumeration materialises into RAM and the O(1) becomes O(N). The senior-engineer stance is to *iterate*, not *materialise*. `for pwd in product(alphabet, repeat=6):` walks 309 million passwords one at a time, never holding more than one in memory; `list(product(alphabet, repeat=6))` would hold all 309 million at once and burn ~25 GB of RAM. By the end of this lesson you will know the four primitives, the `repeat=` and `r=` parameters, the `math.comb` / `math.perm` formulas that tell you the size before you start, and the combinatorial-explosion warning that every senior engineer carries in their head. Take your time. Type every example. **This is how you learn.**

#itertools #combinatorics #product #combinations #permutations

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `itertools.product(*iterables, repeat=1)`** to enumerate the Cartesian product of N iterables — and use `repeat=` for "the same iterable N times."
2. **Apply `itertools.combinations(iterable, r)`** to enumerate r-length subsets without repetition, in lexicographic order.
3. **Apply `itertools.permutations(iterable, r=None)`** to enumerate r-length orderings (where `AB` and `BA` are different); default `r=len(iterable)` for all orderings.
4. **Apply `itertools.combinations_with_replacement(iterable, r)`** to enumerate r-length multisets (where `AA` is allowed and order does not matter).
5. **Predict the size** of any enumeration with `math.comb` and `math.perm` *before* materialising, and articulate why iterating is O(1) memory while `list(...)` is O(N).

## Prerequisites

Before starting, you need:

- **The iterator/iterable distinction** — every `itertools` function returns a one-shot iterator. See [[05-collections-abc/04-Iterator-vs-Iterable]] and [[07-itertools/01-chain-and-islice]].
- **High-school combinatorics** — `C(n, r) = n! / (r! * (n-r)!)` and `P(n, r) = n! / (n-r)!`. The lesson re-derives these via `math.comb` and `math.perm`.
- **About 20–30 minutes of focused time.**

**The most common gap: materialising instead of iterating.**

Students reach for `list(product(range(50), repeat=5))` to "see" what `product` produces — and the laptop freezes because the enumeration is 318 million tuples. The mental shift this lesson teaches is the same shift [[07-itertools/01-chain-and-islice]] taught for `islice`: the iterator yields one item at a time, and the consumer's choice to `list()` or `for ... in ...` is the difference between O(N) and O(1) memory. For combinatorial primitives, the cost of `list(...)` is not just `N` — it is `N * tuple_size`, which for a 6-tuple of strings is ~80 bytes per tuple. The 80 bytes becomes 25 GB at 309 million tuples. The senior move is to iterate, break early when you find what you want, and never `list(...)` a combinatorial primitive without first computing the size.

## The Problem

You ship `boardly/api/assignments.py` — an endpoint that enumerates candidate `(user, project, status)` assignments for a planning view. The first version reads naturally:

```python
from itertools import product

def candidate_assignments(users, projects, statuses):
    return list(product(users, projects, statuses))
```

Three problems. First, the call materialises every tuple into a list — for 10 users, 10 projects, 4 statuses, that's 400 tuples (~32 KB, fine). For 50 users, 50 projects, 5 statuses, that's 12,500 tuples (~1 MB, fine). For 1,000 users, 1,000 projects, 10 statuses, that's 10 million tuples (~800 MB, your endpoint times out). Second, the endpoint iterates the list once and returns the first 100 candidates — so 9,999,900 tuples are materialised and discarded. Third, the code never computes the size before starting, so there is no guard against the "10,000-user company hits the endpoint" scenario.

`itertools.product` is correct; the bug is the `list(...)` call. The fix is to iterate the product directly — `for assignment in product(users, projects, statuses):` — and break early. For the brute-force search use case (`password_brute_force_demo` below), the early break means the iterator walks a few hundred tuples and stops, never holding the full enumeration. For the pagination use case, `islice(product(...), 100)` (see [[07-itertools/01-chain-and-islice]]) yields the first 100 and stops. The lesson also shows `math.comb` and `math.perm` as the size-prediction primitives that gate the call — if `math.comb(N, r) > 1_000_000`, refuse to materialise.

## The Code

```python
# boardly/itertools_product_demo.py
"""Demonstrate product, combinations, permutations, combinations_with_replacement."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class User:
    id: UUID
    name: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    status: str   # "planning" | "active" | "archived"


# A small fixture: 3 users, 2 statuses, 3 projects
users = [
    User(uuid4(), "Ana"),
    User(uuid4(), "Bo"),
    User(uuid4(), "Cai"),
]
statuses = ["planning", "active"]
projects = [
    Project(uuid4(), "Auth Rewrite", "planning"),
    Project(uuid4(), "Search v2", "active"),
    Project(uuid4(), "Onboarding", "planning"),
]


def product_cartesian() -> None:
    """product(*iterables, repeat=1) — the Cartesian product."""
    # One iterable, repeated: product("AB", repeat=2) -> AA, AB, BA, BB
    pairs = list(itertools.product("AB", repeat=2))
    print(f"product('AB', repeat=2) -> {pairs}")

    # Two iterables: product(users, statuses) -> every (user, status) pair
    assignments = list(itertools.product(users, statuses))
    print(f"product(users, statuses) — {len(assignments)} (user, status) pairs:")
    for u, s in assignments:
        print(f"  {u.name} x {s}")

    # Three iterables: product(users, projects, statuses) -> 3*3*2 = 18 triples
    triples = list(itertools.product(users[:2], projects[:2], statuses))
    print(f"product(users[:2], projects[:2], statuses) — {len(triples)} triples (2*2*2)")


def combinations_subsets() -> None:
    """combinations(iterable, r) — r-length subsets, no repetition, lex order."""
    # All pairs of reviewers from 3 users
    review_pairs = list(itertools.combinations(users, 2))
    print(f"combinations(users, 2) — {len(review_pairs)} review pairs:")
    for pair in review_pairs:
        print(f"  {pair[0].name} + {pair[1].name}")

    # 3-of-5 from "ABCDE"
    triples = list(itertools.combinations("ABCDE", 3))
    print(f"combinations('ABCDE', 3) -> {triples}")
    print(f"  (len = C(5, 3) = {math.comb(5, 3)})")


def permutations_orderings() -> None:
    """permutations(iterable, r=None) — r-length orderings; default r=len(iterable)."""
    # Default r = len(iterable): all orderings of "ABC"
    all_orders = list(itertools.permutations("ABC"))
    print(f"permutations('ABC') -> {all_orders}")
    print(f"  (len = 3! = {math.factorial(3)})")

    # r=2: orderings of length 2 (AB != BA, so 6 not 3)
    pairs = list(itertools.permutations("ABC", 2))
    print(f"permutations('ABC', 2) -> {pairs}")
    print(f"  (len = P(3, 2) = {math.perm(3, 2)})")

    # Assignment orderings: 3 tickets, 3 engineers, all 1-to-1 assignments
    assignments = list(itertools.permutations(users, 3))
    print(f"permutations(users, 3) — {len(assignments)} 1-to-1 assignment orderings")
    for assign in assignments:
        print(f"  {[u.name for u in assign]}")


def combinations_with_replacement_demo() -> None:
    """combinations_with_replacement(iterable, r) — subsets with repetition allowed."""
    # Multisets of size 2 from "AB" -> AA, AB, BB (not BA — order doesn't matter)
    multisets = list(itertools.combinations_with_replacement("AB", 2))
    print(f"combinations_with_replacement('AB', 2) -> {multisets}")
    print(f"  (len = C(2+2-1, 2) = {math.comb(3, 2)})")

    # Pick 2 snacks from {apple, banana, cherry} with replacement
    snacks = list(itertools.combinations_with_replacement("ABC", 2))
    print(f"combinations_with_replacement('ABC', 2) -> {snacks}")


def combinatorial_explosion_warning() -> None:
    """Show the math — these grow fast."""
    # product with repeat — password-style enumeration
    n_chars = 26
    n_length = 6
    product_size = n_chars ** n_length
    print(f"product(alphabet, repeat={n_length}) = {n_chars}^{n_length} = {product_size:,} passwords")
    print(f"  (real password crackers: 95^8 = {95**8:,} for 8-char printable ASCII)")

    # combinations — lottery ticket
    n = 50
    r = 5
    comb_size = math.comb(n, r)
    print(f"combinations(range({n}), {r}) = C({n}, {r}) = {comb_size:,} tickets")

    # permutations — race finish order
    n = 8
    r = 3
    perm_size = math.perm(n, r)
    print(f"permutations(range({n}), {r}) = P({n}, {r}) = {perm_size:,} podiums")

    # combinations_with_replacement — dice rolls
    n = 6
    r = 3
    cwr_size = math.comb(n + r - 1, r)
    print(f"combinations_with_replacement(range({n}), {r}) = C({n+r-1}, {r}) = {cwr_size:,} dice outcomes")

    # Memory cost of materialising: each tuple is ~80 bytes
    bytes_estimate = product_size * 80
    print(f"\nMaterialising product(alphabet, repeat=6) as a list would take ~{bytes_estimate / 1_000_000_000:.1f} GB of RAM")
    print(f"Iterating one-by-one via `for pwd in product(...)` takes O(1) memory")


def password_brute_force_demo() -> None:
    """A realistic demo: enumerate 3-char 'abc' passwords."""
    charset = "abc"
    found = None
    target = "cab"
    for pwd in itertools.product(charset, repeat=3):
        candidate = "".join(pwd)
        if candidate == target:
            found = candidate
            break  # early exit — don't enumerate the rest
    print(f"brute-force 'abc' x 3 looking for {target!r}: found {found!r}")
    print(f"  (max space = {3**3} = 27 candidates; early break = O(1) memory)")


def main() -> None:
    print("=== product: Cartesian ===")
    product_cartesian()
    print()
    print("=== combinations: subsets, no repetition ===")
    combinations_subsets()
    print()
    print("=== permutations: all orderings ===")
    permutations_orderings()
    print()
    print("=== combinations_with_replacement: subsets with repetition ===")
    combinations_with_replacement_demo()
    print()
    print("=== combinatorial explosion ===")
    combinatorial_explosion_warning()
    print()
    print("=== password brute-force demo ===")
    password_brute_force_demo()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/itertools_product_demo.py
"""Demonstrate product, combinations, permutations, combinations_with_replacement."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from uuid import UUID, uuid4
```

`itertools` is the star. `math` provides `math.comb(n, r)` and `math.perm(n, r)` — the size-prediction functions added in Python 3.8. These let the lesson compute `C(50, 5) = 2,118,760` *before* calling `combinations(range(50), 5)`, which is the senior-engineer move: predict the size, refuse to materialise if it is too large. `dataclass` and `UUID`/`uuid4` keep the demo offline.

### Lines 12–22: The boardly models

```python
@dataclass(frozen=True)
class User:
    id: UUID
    name: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    status: str   # "planning" | "active" | "archived"
```

Two frozen dataclasses from the `boardly/models.py` contract. Frozen makes the instances hashable — important for `permutations`, because the demo iterates `User` instances and joins their names; the `User` instances are not used as dict keys here, but the frozen contract keeps the demo aligned with [[18-operator/01-itemgetter-attrgetter]] for continuity.

### Lines 25–35: The fixture

```python
# A small fixture: 3 users, 2 statuses, 3 projects
users = [
    User(uuid4(), "Ana"),
    User(uuid4(), "Bo"),
    User(uuid4(), "Cai"),
]
statuses = ["planning", "active"]
projects = [
    Project(uuid4(), "Auth Rewrite", "planning"),
    Project(uuid4(), "Search v2", "active"),
    Project(uuid4(), "Onboarding", "planning"),
]
```

Three users (`Ana`, `Bo`, `Cai`), two statuses (`planning`, `active`), three projects. The fixture is at module scope so every helper sees the same data. The numbers are deliberately small so the demo runs instantly — `product(users, statuses)` is 6 pairs, `combinations(users, 2)` is 3 pairs, `permutations(users, 3)` is 6 orderings. The lesson deliberately runs the *small* case to show the shape; the combinatorial-explosion section later in the lesson scales up to show the math.

### Lines 38–49: `product` — Cartesian product

```python
def product_cartesian() -> None:
    """product(*iterables, repeat=1) — the Cartesian product."""
    # One iterable, repeated: product("AB", repeat=2) -> AA, AB, BA, BB
    pairs = list(itertools.product("AB", repeat=2))
    print(f"product('AB', repeat=2) -> {pairs}")

    # Two iterables: product(users, statuses) -> every (user, status) pair
    assignments = list(itertools.product(users, statuses))
    print(f"product(users, statuses) — {len(assignments)} (user, status) pairs:")
    for u, s in assignments:
        print(f"  {u.name} x {s}")

    # Three iterables: product(users, projects, statuses) -> 3*3*2 = 18 triples
    triples = list(itertools.product(users[:2], projects[:2], statuses))
    print(f"product(users[:2], projects[:2], statuses) — {len(triples)} triples (2*2*2)")
```

`itertools.product(*iterables, repeat=1)` is the Cartesian product. Internally — see `Modules/itertoolsmodule.c` — `product` maintains a pool of N input iterables, a current index tuple, and yields the combination at each step. The output is a tuple of length N (the number of iterables), and the total count is `len(iter1) * len(iter2) * ... * len(iterN)`. The `repeat=K` keyword is sugar for "the same iterable K times" — `product("AB", repeat=2)` is equivalent to `product("AB", "AB")` and yields `AA, AB, BA, BB` (4 tuples).

The first call `product("AB", repeat=2)` shows the `repeat=` keyword — the canonical password-enumeration pattern. The second call `product(users, statuses)` shows the multi-iterable form — every `(user, status)` pair, 6 tuples. The third call `product(users[:2], projects[:2], statuses)` shows the three-iterable form — 2*2*2 = 8 triples. Each form is the same primitive; the difference is the input shape.

**Why does `product` exist when nested `for` loops do the same?** Three reasons. First, `product` is a single iterator you can pass to other `itertools` primitives — `islice(product(...), 100)`, `starmap(func, product(...))`, `chain(product(a, b), product(c, d))`. Nested `for` loops are syntax, not values; you cannot pass a `for` loop as an argument. Second, `product` is C-implemented and faster than the equivalent Python `for` loop — the inner loop runs in C, not in Python bytecode. Third, the `repeat=` keyword handles the "same iterable N times" case without repeating the argument N times in the call — `product("AB", repeat=8)` is one argument; `product("AB", "AB", "AB", "AB", "AB", "AB", "AB", "AB")` is eight, and is harder to read.

**Why is the output order `AA, AB, BA, BB` and not `AA, BA, AB, BB`?** Because the *last* input index varies fastest. `product("AB", "AB")` walks the second iterable for each fixed value of the first: `(A, A), (A, B), (B, A), (B, B)`. This is the standard "odometer" order — the rightmost wheel turns fastest. The same order appears in nested `for` loops: `for a in "AB": for b in "AB": print(a, b)` produces the same sequence. The order is the lex order on tuples, which matches what `sorted` would do.

### Lines 52–63: `combinations` — r-length subsets, no repetition

```python
def combinations_subsets() -> None:
    """combinations(iterable, r) — r-length subsets, no repetition, lex order."""
    # All pairs of reviewers from 3 users
    review_pairs = list(itertools.combinations(users, 2))
    print(f"combinations(users, 2) — {len(review_pairs)} review pairs:")
    for pair in review_pairs:
        print(f"  {pair[0].name} + {pair[1].name}")

    # 3-of-5 from "ABCDE"
    triples = list(itertools.combinations("ABCDE", 3))
    print(f"combinations('ABCDE', 3) -> {triples}")
    print(f"  (len = C(5, 3) = {math.comb(5, 3)})")
```

`itertools.combinations(iterable, r)` enumerates the r-length subsets of `iterable` without repetition, in lexicographic order. Internally, `combinations` maintains a pool of indices into the input, and at each step it advances the rightmost index that can advance without colliding with a higher index. The output is a tuple of length r; the total count is `C(n, r) = n! / (r! * (n-r)!)`, computed by `math.comb(n, r)` (Python 3.8+).

The first call `combinations(users, 2)` shows the boardly reviewer-pair use case: from 3 users, you get 3 review pairs — `(Ana, Bo), (Ana, Cai), (Bo, Cai)`. Note that `(Bo, Ana)` is *not* in the output — combinations treats `(A, B)` and `(B, A)` as the same subset, and yields only one. The order within each tuple is the input order (Ana before Bo before Cai), not alphabetical.

The second call `combinations("ABCDE", 3)` shows the lex order: `(A, B, C), (A, B, D), (A, B, E), (A, C, D), ...`. The first index varies slowest; the last index varies fastest; each index always exceeds the previous (no repetition). The total is `C(5, 3) = 10` — verified with `math.comb(5, 3)`.

**Why does `combinations` not yield `(B, A)` as a separate pair?** Because combinations models *sets*, not *sequences*. The mathematical concept of "choose 2 from {A, B, C}" is a set of 2-element subsets: `{A, B}, {A, C}, {B, C}` — three subsets, not six. `(A, B)` and `(B, A)` are the same subset. If you want both orderings (i.e. "A is the primary reviewer, B is the secondary" vs. "B is the primary, A is the secondary"), use `permutations(users, 2)` instead, which yields 6 pairs: `(A, B), (A, C), (B, A), (B, C), (C, A), (C, B)`. The choice between `combinations` and `permutations` is the choice between unordered subsets and ordered sequences.

### Lines 66–83: `permutations` — r-length orderings

```python
def permutations_orderings() -> None:
    """permutations(iterable, r=None) — r-length orderings; default r=len(iterable)."""
    # Default r = len(iterable): all orderings of "ABC"
    all_orders = list(itertools.permutations("ABC"))
    print(f"permutations('ABC') -> {all_orders}")
    print(f"  (len = 3! = {math.factorial(3)})")

    # r=2: orderings of length 2 (AB != BA, so 6 not 3)
    pairs = list(itertools.permutations("ABC", 2))
    print(f"permutations('ABC', 2) -> {pairs}")
    print(f"  (len = P(3, 2) = {math.perm(3, 2)})")

    # Assignment orderings: 3 tickets, 3 engineers, all 1-to-1 assignments
    assignments = list(itertools.permutations(users, 3))
    print(f"permutations(users, 3) — {len(assignments)} 1-to-1 assignment orderings")
    for assign in assignments:
        print(f"  {[u.name for u in assign]}")
```

`itertools.permutations(iterable, r=None)` enumerates the r-length orderings of `iterable`. The default `r=None` means `r = len(iterable)` — all orderings of the entire iterable, total `n!`. With `r` specified, the total is `P(n, r) = n! / (n-r)!`, computed by `math.perm(n, r)` (Python 3.8+). The crucial difference from `combinations`: `(A, B)` and `(B, A)` are *different* permutations and both are in the output.

The first call `permutations("ABC")` (no `r`) yields 6 tuples — all orderings of the 3-element input. The second call `permutations("ABC", 2)` yields 6 tuples of length 2 — every ordered pair. Note that `P(3, 2) = 6` and `C(3, 2) = 3` — `permutations` yields twice as many because each combination has two orderings. The third call `permutations(users, 3)` shows the boardly assignment use case: 3 tickets, 3 engineers, all 1-to-1 assignments — 6 orderings, each a different (ticket-1 engineer, ticket-2 engineer, ticket-3 engineer) assignment.

**Why is `permutations` of `range(50)` with default `r` a 50! enumeration?** Because the default `r=None` means `r = len(iterable)`, and `P(50, 50) = 50!` which is approximately `3 * 10^64`. Calling `list(permutations(range(50)))` would attempt to materialise `3 * 10^64` tuples — the universe will end before the call returns. The lesson's `combinatorial_explosion_warning` section computes `P(8, 3) = 336` (manageable) but the lesson deliberately does not call `permutations(range(50))` because no machine can hold the result.

### Lines 86–96: `combinations_with_replacement` — multisets

```python
def combinations_with_replacement_demo() -> None:
    """combinations_with_replacement(iterable, r) — subsets with repetition allowed."""
    # Multisets of size 2 from "AB" -> AA, AB, BB (not BA — order doesn't matter)
    multisets = list(itertools.combinations_with_replacement("AB", 2))
    print(f"combinations_with_replacement('AB', 2) -> {multisets}")
    print(f"  (len = C(2+2-1, 2) = {math.comb(3, 2)})")

    # Pick 2 snacks from {apple, banana, cherry} with replacement
    snacks = list(itertools.combinations_with_replacement("ABC", 2))
    print(f"combinations_with_replacement('ABC', 2) -> {snacks}")
```

`itertools.combinations_with_replacement(iterable, r)` (Python 3.1+) enumerates the r-length *multisets* of `iterable` — subsets where the same element can appear more than once, and order does not matter. The total is `C(n+r-1, r)` — the standard "stars and bars" formula. For `("AB", 2)`, the multisets are `(A, A), (A, B), (B, B)` — three tuples (note that `(B, A)` is *not* in the output, because as a multiset it equals `(A, B)`).

The boardly use case is "pick 2 snacks from the snack drawer with replacement" — you can pick the same snack twice. For `("ABC", 2)`, the multisets are `(A, A), (A, B), (A, C), (B, B), (B, C), (C, C)` — six tuples, verified by `C(3+2-1, 2) = C(4, 2) = 6`.

**Why is `combinations_with_replacement` rarely used?** Because most real-world "subset" questions are about *without replacement* — you cannot pick the same lottery number twice, the same reviewer twice, the same project twice. The *with-replacement* case appears in probability (dice rolls, coin flips, sampling with replacement) and in the "stars and bars" combinatorial identity. The primitive exists for completeness — and because the implementation is a one-line variation of `combinations` — but you will reach for it maybe twice in a career. Knowing it exists is enough.

### Lines 99–124: The combinatorial-explosion warning

```python
def combinatorial_explosion_warning() -> None:
    """Show the math — these grow fast."""
    # product with repeat — password-style enumeration
    n_chars = 26
    n_length = 6
    product_size = n_chars ** n_length
    print(f"product(alphabet, repeat={n_length}) = {n_chars}^{n_length} = {product_size:,} passwords")
    print(f"  (real password crackers: 95^8 = {95**8:,} for 8-char printable ASCII)")

    # combinations — lottery ticket
    n = 50
    r = 5
    comb_size = math.comb(n, r)
    print(f"combinations(range({n}), {r}) = C({n}, {r}) = {comb_size:,} tickets")

    # permutations — race finish order
    n = 8
    r = 3
    perm_size = math.perm(n, r)
    print(f"permutations(range({n}), {r}) = P({n}, {r}) = {perm_size:,} podiums")

    # combinations_with_replacement — dice rolls
    n = 6
    r = 3
    cwr_size = math.comb(n + r - 1, r)
    print(f"combinations_with_replacement(range({n}), {r}) = C({n+r-1}, {r}) = {cwr_size:,} dice outcomes")

    # Memory cost of materialising: each tuple is ~80 bytes
    bytes_estimate = product_size * 80
    print(f"\nMaterialising product(alphabet, repeat=6) as a list would take ~{bytes_estimate / 1_000_000_000:.1f} GB of RAM")
    print(f"Iterating one-by-one via `for pwd in product(...)` takes O(1) memory")
```

The warning. The four primitives all grow combinatorially — the size of the output is exponential in the input. The math:

- `product(alphabet, repeat=6) = 26^6 = 308,915,776` passwords — the lowercase-alphabet 6-character password space.
- `product(printable_ascii, repeat=8) = 95^8 = 6,634,204,312,890,625` — the 8-character ASCII password space, ~6.6 * 10^15. At 1 billion passwords per second, this takes 76 days to brute-force.
- `combinations(range(50), 5) = C(50, 5) = 2,118,760` — the 5-of-50 lottery ticket space.
- `permutations(range(8), 3) = P(8, 3) = 336` — the 8-runner, 3-podium race outcomes.
- `combinations_with_replacement(range(6), 3) = C(6+3-1, 3) = C(8, 3) = 56` — the 3-dice-roll multisets.

The crucial line at the bottom: materialising `product(alphabet, repeat=6)` as a list would take ~24.7 GB of RAM (each tuple is ~80 bytes; 308,915,776 * 80 / 1,000,000,000 ≈ 24.7 GB). The list call would either OOM-kill the process or swap to disk and take hours. Iterating via `for pwd in product(...)` is O(1) in memory — the iterator yields one tuple at a time and the previous tuple is garbage-collected before the next is created.

**Why is the senior-engineer move to compute the size *before* the call?** Because the size tells you whether `list(...)` is safe. `math.comb(N, r)` and `math.perm(N, r)` are O(1) calls — they compute the size without enumerating. If the size is < 100,000 (a few MB), `list(...)` is safe. If the size is > 1,000,000, you must iterate. If the size is > 1,000,000,000, you must iterate *and* have an early-exit condition (because even iterating 10^9 items takes minutes). The lesson's `password_brute_force_demo` shows the early-exit pattern: `for pwd in product(...): if match: break`.

**Why does Python not refuse to materialise large enumerations?** Because there is no "large" threshold that is right for every use case — 10 million tuples is fine on a server with 16 GB RAM, fatal on a Raspberry Pi. The contract is "you call `list(...)` if you accept the memory cost; you iterate if you don't." The standard library does not second-guess the caller. The senior-engineer move is to compute the size first, decide based on the size, and never call `list(...)` blindly.

### Lines 127–138: The brute-force password demo

```python
def password_brute_force_demo() -> None:
    """A realistic demo: enumerate 3-char 'abc' passwords."""
    charset = "abc"
    found = None
    target = "cab"
    for pwd in itertools.product(charset, repeat=3):
        candidate = "".join(pwd)
        if candidate == target:
            found = candidate
            break  # early exit — don't enumerate the rest
    print(f"brute-force 'abc' x 3 looking for {target!r}: found {found!r}")
    print(f"  (max space = {3**3} = 27 candidates; early break = O(1) memory)")
```

The realistic pattern. The lesson enumerates `product("abc", repeat=3)` — 27 candidates — looking for `"cab"`. The `for pwd in product(...):` loop walks the enumeration one tuple at a time; the `if candidate == target: break` exits early when the match is found. The `break` is the senior move — without it, the loop would walk all 27 candidates even after the match. With the break, the loop walks 6 candidates (the order is `aaa, aab, aac, aba, ..., cab` — `"cab"` is the 6th), finds the match, and exits.

The crucial detail: even though the *total* enumeration is 27 candidates, the *memory* used is O(1) — one tuple at a time. If the lesson scaled to `product("abc", repeat=20)` (3^20 = 3.5 billion candidates), the `for pwd in product(...)` loop would still be O(1) in memory — the iterator yields one tuple at a time, the previous is garbage-collected, and only one tuple is alive at any moment. The early-exit means the loop stops at the match, even if the match is the 1,000th candidate out of 3.5 billion.

**Warning — `"".join(pwd)` materialises the candidate string per iteration.** The `pwd` tuple is `('c', 'a', 'b')`; `"".join(pwd)` is `"cab"`. The `join` call allocates a fresh 3-char string per iteration, which is then compared to `target` and discarded. For a 27-candidate enumeration this is fine; for a 309-million-candidate enumeration (the lowercase-alphabet 6-char case), this would allocate 309 million strings — fine in steady state (each is garbage-collected), but it does mean the loop is not literally free. For a production brute-forcer, you would compare tuples directly (`if pwd == ('c', 'a', 'b'): ...`) to skip the `join` allocation. The demo uses `join` because the candidate is more readable as a string than as a tuple.

## Execution Trace

```bash
$ uv run python boardly/itertools_product_demo.py
=== product: Cartesian ===
product('AB', repeat=2) -> [('A', 'A'), ('A', 'B'), ('B', 'A'), ('B', 'B')]
product(users, statuses) — 6 (user, status) pairs:
  Ana x planning
  Ana x active
  Bo x planning
  Bo x active
  Cai x planning
  Cai x active
product(users[:2], projects[:2], statuses) — 8 triples (2*2*2)

=== combinations: subsets, no repetition ===
combinations(users, 2) — 3 review pairs:
  Ana + Bo
  Ana + Cai
  Bo + Cai
combinations('ABCDE', 3) -> [('A', 'B', 'C'), ('A', 'B', 'D'), ('A', 'B', 'E'), ('A', 'C', 'D'), ('A', 'C', 'E'), ('A', 'D', 'E'), ('B', 'C', 'D'), ('B', 'C', 'E'), ('B', 'D', 'E'), ('C', 'D', 'E')]
  (len = C(5, 3) = 10)

=== permutations: all orderings ===
permutations('ABC') -> [('A', 'B', 'C'), ('A', 'C', 'B'), ('B', 'A', 'C'), ('B', 'C', 'A'), ('C', 'A', 'B'), ('C', 'B', 'A')]
  (len = 3! = 6)
permutations('ABC', 2) -> [('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B')]
  (len = P(3, 2) = 6)
permutations(users, 3) — 6 1-to-1 assignment orderings
  ['Ana', 'Bo', 'Cai']
  ['Ana', 'Cai', 'Bo']
  ['Bo', 'Ana', 'Cai']
  ['Bo', 'Cai', 'Ana']
  ['Cai', 'Ana', 'Bo']
  ['Cai', 'Bo', 'Ana']

=== combinations_with_replacement: subsets with repetition ===
combinations_with_replacement('AB', 2) -> [('A', 'A'), ('A', 'B'), ('B', 'B')]
  (len = C(2+2-1, 2) = 3)
combinations_with_replacement('ABC', 2) -> [('A', 'A'), ('A', 'B'), ('A', 'C'), ('B', 'B'), ('B', 'C'), ('C', 'C')]

=== combinatorial explosion ===
product(alphabet, repeat=6) = 26^6 = 308,915,776 passwords
  (real password crackers: 95^8 = 6,634,204,312,890,625 for 8-char printable ASCII)
combinations(range(50), 5) = C(50, 5) = 2,118,760 tickets
permutations(range(8), 3) = P(8, 3) = 336 podiums
combinations_with_replacement(range(6), 3) = C(8, 3) = 56 dice outcomes

Materialising product(alphabet, repeat=6) as a list would take ~24.7 GB of RAM
Iterating one-by-one via `for pwd in product(...)` takes O(1) memory

=== password brute-force demo ===
brute-force 'abc' x 3 looking for 'cab': found 'cab'
  (max space = 27 = 27 candidates; early break = O(1) memory)
```

The first block shows the three forms of `product`: the `repeat=` keyword (4 tuples for `product("AB", repeat=2)`), the two-iterable form (6 pairs for `product(users, statuses)`), and the three-iterable form (8 triples for `product(users[:2], projects[:2], statuses)`). Each form yields the same kind of object — a tuple of length N where N is the number of input iterables.

The second block shows `combinations`: 3 review pairs from 3 users (`C(3, 2) = 3`), and 10 triples from 5 letters (`C(5, 3) = 10`). The lex order is visible — the first index varies slowest, the last index varies fastest, and each index always exceeds the previous.

The third block shows `permutations`: 6 orderings of "ABC" (3!), 6 ordered pairs from "ABC" (P(3, 2) = 6), and 6 1-to-1 assignments of 3 users to 3 tickets (3! = 6). Note that `permutations("ABC", 2)` and `permutations("ABC")` happen to have the same count (6), but for different reasons — the former is `P(3, 2) = 6` and the latter is `3! = 6`. They are different enumerations.

The fourth block shows `combinations_with_replacement`: 3 multisets from "AB" (`C(3, 2) = 3`), and 6 multisets from "ABC" (`C(4, 2) = 6`). The order within each tuple is non-decreasing (the same element can repeat but never decrease), and `(B, A)` is not in the output (it equals `(A, B)` as a multiset).

The fifth block shows the combinatorial-explosion math. 26^6 = 308,915,776 lowercase-alphabet 6-char passwords. 95^8 = 6.6 * 10^15 ASCII 8-char passwords. C(50, 5) = 2,118,760 lottery tickets. P(8, 3) = 336 race podiums. C(8, 3) = 56 dice-roll multisets. Materialising the lowercase-6-char password enumeration as a list would take ~24.7 GB of RAM; iterating via `for pwd in product(...)` takes O(1).

The sixth block shows the brute-force pattern: `for pwd in product("abc", repeat=3): if candidate == target: break`. The loop walks 6 candidates (the 6th is `"cab"`) and exits. Max space is 27 candidates (the full enumeration), but the early break means only 6 are actually visited and only 1 tuple is alive at any moment.

## Common Mistakes

### Mistake 1: Calling `list(permutations(range(50)))` and locking up the laptop

```python
# Wrong — 50! is 3 * 10^64, no machine can hold it
all_perms = list(itertools.permutations(range(50)))
```

**Symptom:** The process hangs, consumes all available RAM, and the OS eventually OOM-kills it (or the user force-quits).

**Why:** `permutations(range(50))` with default `r` is `P(50, 50) = 50! = 3.04 * 10^64`. Materialising this as a list is physically impossible — there are not enough atoms in the universe to represent that many tuples. The iterator yields them one at a time correctly, but the `list(...)` call tries to hold them all at once.

**Fix:** Compute the size first with `math.perm(50, 50)` (or `math.factorial(50)`). If the size is over 1 million, never call `list(...)`. Iterate with `for perm in permutations(...):` and break early when you find what you need. If you genuinely need a finite subset, use `islice(permutations(...), 100)` (see [[07-itertools/01-chain-and-islice]]).

### Mistake 2: Confusing `combinations` and `permutations`

```python
# Wrong — using combinations when you wanted ordered pairs
pairs = list(itertools.combinations("ABC", 2))
# pairs == [('A','B'), ('A','C'), ('B','C')]  — 3 pairs, no (B,A)
# If you wanted (B, A) too — i.e. "A is primary, B is secondary"
# — you needed permutations, not combinations.
```

**Symptom:** The output is missing half the tuples you expected. `combinations("ABC", 2)` yields 3 pairs; `permutations("ABC", 2)` yields 6.

**Why:** `combinations` models *unordered subsets* (where `(A, B) == (B, A)`); `permutations` models *ordered sequences* (where `(A, B) != (B, A)`). The choice depends on whether the order of elements in each tuple is significant for your use case.

**Fix:** Decide whether order matters. If `(A, B)` and `(B, A)` are equivalent for your use case (reviewer pairs, lottery tickets), use `combinations`. If they are different (primary/secondary reviewer, race positions), use `permutations`.

### Mistake 3: Forgetting `repeat=` in `product`

```python
# Wrong — without repeat, this is product of one iterable, which yields
# 1-tuples, not 2-tuples
pairs = list(itertools.product("AB"))  # [('A',), ('B',)]  — 1-tuples!
# Right:
pairs = list(itertools.product("AB", repeat=2))  # [('A','A'), ('A','B'), ...]  — 2-tuples
```

**Symptom:** The output has 1-tuples instead of N-tuples, and the count is `len(iterable)` instead of `len(iterable) ** N`.

**Why:** `product("AB")` is the Cartesian product of *one* iterable with itself zero times — it yields each element as a 1-tuple, total `len("AB") = 2` tuples. `product("AB", repeat=2)` is the product of `"AB"` with itself twice — total `2 ** 2 = 4` tuples, each of length 2. The `repeat=` keyword is the only way to express "the same iterable N times" with one argument.

**Fix:** Always pass `repeat=N` when you want the N-fold Cartesian product of one iterable with itself. If you forget, the output is silently the 1-tuple form — no error, just the wrong shape.

## Engineering Trade-Offs

**Decision:** Use `product` for Cartesian enumeration (cross-team × cross-status matrices, password brute-force), `combinations` for unordered subsets (reviewer pairs, lottery tickets), `permutations` for ordered sequences (race podiums, 1-to-1 assignments), and `combinations_with_replacement` for multisets (sampling with replacement, dice rolls). Iterate, do not materialise, unless `math.comb`/`math.perm` confirms the size is small.

**Both sides:** The alternative to iterating is materialising with `list(...)`, which wins when (a) the size is small (verified by `math.comb`/`math.perm` first), (b) you need random access or multiple passes, or (c) the downstream code expects a list (e.g. `len(list(...))` for the count). Materialising wins for the small case; iterating wins for the large case. The senior move is to compute the size first and choose based on the size, not on a default.

**Commitment:** `boardly/api/assignments.py` uses `islice(product(users, projects, statuses), 100)` to enumerate the first 100 candidate assignments for the planning view — never `list(product(...))`. The project's lint config flags `list(product(...))`, `list(combinations(...))`, and `list(permutations(...))` with a `Bench` warning suggesting `math.comb`/`math.perm` size check + `islice` as the rewrite. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to this rule as the project's "don't materialise a combinatorial enumeration without a size check" stance.

**Why not just always iterate?** Because for the small case (e.g. `product("AB", "CD")` is 4 tuples), `list(...)` is clearer and the downstream code (a `for` loop, a `len()` call, a `sorted()` call) often expects a list. The `Bench` lint warning is a *warning*, not an error — it surfaces the size-check question without blocking the small case. The senior move is to make the size check explicit (`assert math.comb(N, r) < 1_000_000`) before the `list(...)` call, so the lint warning is resolved by the assertion.

## Exercises

1. **Exercise 1 — Enumerate 4-character "01" binary strings.** Use `product("01", repeat=4)` and print all 16 binary strings. Verify the count is 16 and the lex order starts with `0000` and ends with `1111`. `Verify: uv run python boardly/itertools_product_demo.py`

2. **Exercise 2 — All 3-of-5 review committees.** Use `combinations(users + [User(uuid4(), "Dee"), User(uuid4(), "Eve")], 3)` to enumerate 3-person review committees from 5 users. Verify the count is `C(5, 3) = 10`. `Verify: uv run python boardly/itertools_product_demo.py`

3. **Exercise 3 — Podium outcomes for an 8-runner race.** Use `permutations(range(8), 3)` and `math.perm(8, 3)` to enumerate the 336 gold-silver-bronze outcomes. Print only the first 10 (use `islice`), and verify the count via `math.perm`. `Verify: uv run python boardly/itertools_product_demo.py`

4. **Exercise 4 — Predict, then enumerate, the 4-dice multisets.** Compute `math.comb(6+4-1, 4)` (the stars-and-bars count for 4 dice from 6 faces). Then enumerate with `combinations_with_replacement(range(1, 7), 4)` and verify the count matches. `Verify: uv run python boardly/itertools_product_demo.py`

5. **Exercise 5 — Implement an early-exit brute-forcer with `islice`.** Use `product("abcde", repeat=4)` (625 candidates) and `islice(..., 50)` to enumerate only the first 50 candidates without materialising the full 625. Print the 50th candidate. Verify the total `len(list(islice(...)))` is exactly 50. `Verify: uv run python boardly/itertools_product_demo.py`

## Verification

```bash
$ uv run python boardly/itertools_product_demo.py
=== product: Cartesian ===
product('AB', repeat=2) -> [('A', 'A'), ('A', 'B'), ('B', 'A'), ('B', 'B')]
product(users, statuses) — 6 (user, status) pairs:
  Ana x planning
  Ana x active
  Bo x planning
  Bo x active
  Cai x planning
  Cai x active
product(users[:2], projects[:2], statuses) — 8 triples (2*2*2)

=== combinations: subsets, no repetition ===
combinations(users, 2) — 3 review pairs:
  Ana + Bo
  Ana + Cai
  Bo + Cai
combinations('ABCDE', 3) -> [('A', 'B', 'C'), ('A', 'B', 'D'), ('A', 'B', 'E'), ('A', 'C', 'D'), ('A', 'C', 'E'), ('A', 'D', 'E'), ('B', 'C', 'D'), ('B', 'C', 'E'), ('B', 'D', 'E'), ('C', 'D', 'E')]
  (len = C(5, 3) = 10)

=== permutations: all orderings ===
permutations('ABC') -> [('A', 'B', 'C'), ('A', 'C', 'B'), ('B', 'A', 'C'), ('B', 'C', 'A'), ('C', 'A', 'B'), ('C', 'B', 'A')]
  (len = 3! = 6)
permutations('ABC', 2) -> [('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B')]
  (len = P(3, 2) = 6)
permutations(users, 3) — 6 1-to-1 assignment orderings
  ['Ana', 'Bo', 'Cai']
  ['Ana', 'Cai', 'Bo']
  ['Bo', 'Ana', 'Cai']
  ['Bo', 'Cai', 'Ana']
  ['Cai', 'Ana', 'Bo']
  ['Cai', 'Bo', 'Ana']

=== combinations_with_replacement: subsets with repetition ===
combinations_with_replacement('AB', 2) -> [('A', 'A'), ('A', 'B'), ('B', 'B')]
  (len = C(2+2-1, 2) = 3)
combinations_with_replacement('ABC', 2) -> [('A', 'A'), ('A', 'B'), ('A', 'C'), ('B', 'B'), ('B', 'C'), ('C', 'C')]

=== combinatorial explosion ===
product(alphabet, repeat=6) = 26^6 = 308,915,776 passwords
  (real password crackers: 95^8 = 6,634,204,312,890,625 for 8-char printable ASCII)
combinations(range(50), 5) = C(50, 5) = 2,118,760 tickets
permutations(range(8), 3) = P(8, 3) = 336 podiums
combinations_with_replacement(range(6), 3) = C(8, 3) = 56 dice outcomes

Materialising product(alphabet, repeat=6) as a list would take ~24.7 GB of RAM
Iterating one-by-one via `for pwd in product(...)` takes O(1) memory

=== password brute-force demo ===
brute-force 'abc' x 3 looking for 'cab': found 'cab'
  (max space = 27 = 27 candidates; early break = O(1) memory)
```

## Previously Learned Here

- [[07-itertools/01-chain-and-islice]] — the one-shot-iterator mental model. `product`/`combinations`/`permutations` are all one-shot iterators; `list(...)` materialises, `for ... in ...` iterates.
- [[07-itertools/03-starmap-and-accumulate]] — the pipeline-composition pattern. `product(users, statuses)` is often the upstream of `starmap(assign_func, ...)` when each `(user, status)` pair is passed to a two-arg assignment function.

## What's Next

[[07-itertools/05-cycle-repeat-count]] — `product` and friends are the *finite* combinatorial primitives; the next lesson shows you the *infinite* iterators. `itertools.cycle(iterable)` cycles through an iterable forever (good for round-robin distribution), `itertools.repeat(obj, times=None)` yields `obj` N times (or forever), and `itertools.count(start=0, step=1)` yields an arithmetic sequence forever. The lesson shows `zip(count(1), items)` for enumeration and why `cycle` is dangerous without a `takewhile` or `islice` bound.

- `cycle(iterable)` — infinite repetition of a finite iterable.
- `repeat(obj, times=None)` — `obj` yielded N times (or forever if `times=None`).
- `count(start=0, step=1)` — infinite arithmetic sequence, the streaming alternative to `range(...)` without a stop.

## Sources

- **`itertools.product`** — https://docs.python.org/3/library/itertools.html#itertools.product — accessed 2026-10-23 — the canonical reference for the Cartesian product, including the `repeat=` keyword and the "odometer" output order.
- **`itertools.combinations`** — https://docs.python.org/3/library/itertools.html#itertools.combinations — accessed 2026-10-23 — the canonical reference for r-length subsets, no repetition, in lex order.
- **`itertools.permutations`** — https://docs.python.org/3/library/itertools.html#itertools.permutations — accessed 2026-10-23 — the canonical reference for r-length orderings, with the default `r=None` meaning `r=len(iterable)`.
- **`itertools.combinations_with_replacement`** — https://docs.python.org/3/library/itertools.html#itertools.combinations_with_replacement — accessed 2026-10-23 — the canonical reference for r-length multisets, added in Python 3.1.
- **`math.comb` and `math.perm`** — https://docs.python.org/3/library/math.html#math.comb — accessed 2026-10-23 — the size-prediction functions added in Python 3.8, which let you compute `C(n, r)` and `P(n, r)` without enumerating.

## What We Learned

- You can apply `itertools.product(*iterables, repeat=1)` to enumerate the Cartesian product of N iterables — and use `repeat=` for "the same iterable N times."
- You can apply `itertools.combinations(iterable, r)` to enumerate r-length subsets without repetition, in lexicographic order.
- You can apply `itertools.permutations(iterable, r=None)` to enumerate r-length orderings (where `AB` and `BA` are different); default `r=len(iterable)` for all orderings.
- You can apply `itertools.combinations_with_replacement(iterable, r)` to enumerate r-length multisets (where `AA` is allowed and order does not matter).
- You can predict the size of any enumeration with `math.comb` and `math.perm` *before* materialising, and articulate why iterating is O(1) memory while `list(...)` is O(N).
