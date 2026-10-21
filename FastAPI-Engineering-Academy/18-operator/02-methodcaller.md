---
title: "Lesson 02: methodcaller"
aliases:
 - operator.methodcaller
 - methodcaller
tags:
 - operator
 - methodcaller
 - functional-programming
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "15–25 minutes"
prerequisites:
 - "[[18-operator/01-itemgetter-attrgetter]]"
related_lessons:
 - "[[18-operator/01-itemgetter-attrgetter]]"
 - "[[18-operator/03-functional-composition]]"
 - "[[02-functools/03-partial]]"
---

# Lesson 02: `methodcaller`

*The third `operator` factory — pre-binds a method name and its arguments into a C-level callable so you can sort by `.strip()` or `map()` with `.split(",")` without writing a single `lambda`.*

**You're at the very beginning of Section 18.**

`operator.methodcaller` is the factory that closes the trio. Where `itemgetter` extracts by index and `attrgetter` extracts by attribute name, `methodcaller` *invokes* — `methodcaller("strip")` returns `lambda s: s.strip()`, `methodcaller("split", ",")` returns `lambda s: s.split(",")`, and `methodcaller("replace", " ", "-")` returns `lambda s: s.replace(" ", "-")`. The factory stores the method name and the pre-bound positional and keyword arguments; calling the returned object on `obj` invokes `obj.method_name(*args, **kwargs)` in C. By the end of this lesson you will know the three forms, the two real use cases (sort-by-method-result and `map`-with-method), and the one trap (`str.replace` is positional-only). Take your time. Type every example. **This is how you learn.**

#operator #methodcaller #functional-programming

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `operator.methodcaller(name, *args, **kwargs)`** to build a callable that invokes `name` on its argument with the pre-bound arguments.
2. **Distinguish `methodcaller` from `attrgetter`** — `attrgetter` reads; `methodcaller` calls.
3. **Sort by a method result** — `sorted(strings, key=methodcaller("strip"))` — without writing a `lambda`.
4. **Pre-bind positional and keyword arguments** — `methodcaller("split", sep=",")` for keyword arguments, `methodcaller("replace", " ", "-")` for positional.
5. **Call a dunder method** — `methodcaller("__len__")(s)` is `s.__len__()` — and articulate why this is rarely the right call.

## Prerequisites

Before starting, you need:

- **`itemgetter` and `attrgetter`** — the first lesson of this section. See [[18-operator/01-itemgetter-attrgetter]].
- **Method invocation** — `s.strip()`, `s.split(",")` should feel natural.
- **About 15–25 minutes of focused time.**

**The most common gap: writing `lambda s: s.strip()` when a `methodcaller` is the right tool.**

A `lambda` that does nothing but call a method is a puzzle: `lambda s: s.strip()` is six tokens for "call `.strip()`". `methodcaller("strip")` is three tokens for the same semantics, plus the C fast path, plus a readable repr (`operator.methodcaller('strip')`). Students who never internalise this end up writing `lambda s: s.strip().lower()` everywhere — fine in moderation, but the moment the lambda's body is *one* method call, `methodcaller` is the senior-engineer move. The fix is the same as in lesson 01: know the factory by name.

## The Problem

You ship `boardly/tickets/import.py` that ingests CSV rows from a marketing team's spreadsheet. The titles arrive with leading/trailing whitespace (`"  Search returns 500  "`) and the tag column arrives as a comma-separated string (`"auth,billing,search"`). The first version reads naturally:

```python
def clean_title(s: str) -> str:
    return s.strip()

def parse_tags(s: str) -> list[str]:
    return s.split(",")

cleaned = [clean_title(t.title) for t in tickets]
tagged = [parse_tags(t.tags) for t in tickets]
```

Three problems. First, `clean_title` and `parse_tags` are one-line wrappers around a single method call — they exist only because `lambda` is linted away with `E731` at module scope. Second, the wrappers add names to the module's namespace that a future reader has to track down. Third, when you need to sort the CSV rows by the cleaned title, you write `sorted(tickets, key=lambda t: t.title.strip())` — and the `lambda` is back inline, exactly where the linter complained.

`methodcaller` solves all three. `methodcaller("strip")` is a C-implemented callable that does exactly `lambda s: s.strip()` — no wrapper, no lambda, no puzzle. The use case is `sorted(tickets, key=methodcaller("strip"))` for the sort-by-method-result pattern, and `map(methodcaller("split", ","), csv_lines)` for the apply-method-to-iterable pattern. The factory is the third leg of the `operator` tripod; once you know all three, you have a name for every trivial callable.

## The Code

```python
# boardly/operator_methodcaller_demo.py
"""Demonstrate operator.methodcaller on boardly ticket imports."""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from uuid import UUID, uuid4


# --- The boardly Ticket (subset — see boardly/models.py) ---
@dataclass
class Ticket:
    id: UUID
    title: str           # raw title — may have leading/trailing whitespace
    tags_csv: str        # comma-separated tag list, e.g. "auth,billing,search"
    priority: int        # 1 (low) .. 5 (urgent)


# --- Fixture: import data with noisy whitespace and CSV tags ---
tickets = [
    Ticket(uuid4(), "  Search returns 500  ", "auth,billing", 5),
    Ticket(uuid4(), "[Bug]  Auth fails on macOS", "auth,macos", 3),
    Ticket(uuid4(), "Docs typo", "docs", 1),
    Ticket(uuid4(), "  Export to CSV  ", "export,billing", 2),
]


def strip_demo() -> None:
    """methodcaller('strip') returns a callable that strips its argument."""
    strip = operator.methodcaller("strip")
    print(f"raw:        {tickets[0].title!r}")
    print(f"stripped:   {strip(tickets[0].title)!r}")

    # Sort by the stripped title — no lambda in sight
    by_clean_title = sorted(tickets, key=lambda t: strip(t.title))
    print("sorted by stripped title:")
    for t in by_clean_title:
        print(f"  {strip(t.title)!r}")

    # Sort the bare strings by their stripped form, preserving original strings
    titles = [t.title for t in tickets]
    sorted_titles = sorted(titles, key=strip)
    print("bare titles sorted by strip():", sorted_titles)


def split_with_positional_args() -> None:
    """methodcaller('split', ',') pre-binds the positional arg."""
    split_comma = operator.methodcaller("split", ",")
    print(f"tags[0] raw:    {tickets[0].tags_csv!r}")
    print(f"tags[0] split:  {split_comma(tickets[0].tags_csv)}")

    # Apply to a list of CSV strings with map()
    csv_lines = [t.tags_csv for t in tickets]
    parsed = list(map(split_comma, csv_lines))
    print("all tag lists:", parsed)


def replace_with_positional_args() -> None:
    """str.replace is positional-only — pass args positionally."""
    replace_space_dash = operator.methodcaller("replace", " ", "-")
    title = "[Bug]  Auth fails on macOS"
    print(f"replaced: {replace_space_dash(title)!r}")

    # The sort-by-method-result pattern: sort by the slugified title
    by_slug = sorted(tickets, key=lambda t: replace_space_dash(t.title))
    print("sorted by slugified title:")
    for t in by_slug:
        print(f"  {replace_space_dash(t.title)!r}")


def keyword_args_demo() -> None:
    """methodcaller accepts keyword args for methods that take them."""
    # str.split accepts sep= and maxsplit= as keyword args (it's in the signature,
    # even though the docs mark it positional-or-keyword).
    split_first_only = operator.methodcaller("split", sep=",", maxsplit=1)
    print(f"first split: {split_first_only(tickets[0].tags_csv)}")

    # list.sort(key=...) accepts key as a keyword
    nums = [[3, 1, 2], [9, 0, 5], [4, 4, 4]]
    sort_by_max = operator.methodcaller("sort")
    # Note: list.sort returns None — methodcaller returns whatever the method returns
    for n in nums:
        sort_by_max(n)
    print(f"in-place sorted: {nums}")


def dunder_call_demo() -> None:
    """methodcaller can call a dunder — but it's almost never the right move."""
    len_caller = operator.methodcaller("__len__")
    print(f"len of title: {len_caller(tickets[0].title)}")

    # The normal way is just len(); the dunder form is rarely clearer.
    print(f"len (builtin): {len(tickets[0].title)}")

    # The one valid case: passing a len() callable as a value into a higher-order
    # function that expects a 1-arg callable. Use builtins.len instead.
    import builtins
    lens = list(map(builtins.len, [t.title for t in tickets]))
    print(f"all lengths: {lens}")


def main() -> None:
    print("=== methodcaller('strip') ===")
    strip_demo()
    print()
    print("=== methodcaller('split', ',') ===")
    split_with_positional_args()
    print()
    print("=== methodcaller('replace', ' ', '-') ===")
    replace_with_positional_args()
    print()
    print("=== keyword args ===")
    keyword_args_demo()
    print()
    print("=== dunder methods ===")
    dunder_call_demo()


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/operator_methodcaller_demo.py
"""Demonstrate operator.methodcaller on boardly ticket imports."""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from uuid import UUID, uuid4
```

`operator` is the star. `dataclass` builds a mutable `Ticket` (the import shape — tickets arrive as mutable rows and may be transformed during import). `UUID` and `uuid4` give stable identifiers. `field` is imported for forward compatibility — the demo doesn't use it but production boardly uses `field(default_factory=list)` for the `tags: list[str]` field on `Ticket`. `from __future__ import annotations` is boardly's house style — see [[13-future/01-from-future-import-annotations]].

### Lines 13–18: The boardly `Ticket`

```python
@dataclass
class Ticket:
    id: UUID
    title: str           # raw title — may have leading/trailing whitespace
    tags_csv: str        # comma-separated tag list, e.g. "auth,billing,search"
    priority: int        # 1 (low) .. 5 (urgent)
```

A mutable dataclass (no `frozen=True`). The `title` field is raw — the marketing team's spreadsheet exports titles with leading/trailing whitespace, and the import pipeline is responsible for cleaning them. The `tags_csv` field is a string of comma-separated tags — the import pipeline parses them into a list. The `priority` field is a 1–5 int. The shape is intentionally raw: this lesson is about transforming raw imported data, and `methodcaller` is the tool for that transformation when the transformation is a single method call.

**Why not parse `tags_csv` into `tags: list[str]` in `__post_init__`?** Two reasons. First, the import pipeline may want to *preserve* the raw CSV form for an audit log — `tags_csv` is the source of truth, `tags` is a derived view. Second, the pipeline may want to *lazily* parse (only when needed) — `tags_csv` is parseable on demand via `methodcaller("split", ",")`. The boardly codebase stores the raw form on the import row and parses in a separate `parsed_tags` property — see [[06-dataclasses/02-field-and-Defaults]] for the `__post_init__` pattern that *would* eagerly parse.

### Lines 21–26: The fixture

```python
tickets = [
    Ticket(uuid4(), "  Search returns 500  ", "auth,billing", 5),
    Ticket(uuid4(), "[Bug]  Auth fails on macOS", "auth,macos", 3),
    Ticket(uuid4(), "Docs typo", "docs", 1),
    Ticket(uuid4(), "  Export to CSV  ", "export,billing", 2),
]
```

Four tickets with intentionally noisy data: `"  Search returns 500  "` has both leading and trailing whitespace; `"  Export to CSV  "` has the same shape; `"[Bug]  Auth fails on macOS"` has double spaces inside (which `strip` does not touch — that's the `replace` case). The `tags_csv` field is comma-separated strings of varying length. The fixture is the same shape as lesson 01's fixture so the student sees continuity — boardly's models are stable across the section.

### Lines 29–43: `methodcaller("strip")` — the no-argument case

```python
def strip_demo() -> None:
    """methodcaller('strip') returns a callable that strips its argument."""
    strip = operator.methodcaller("strip")
    print(f"raw:        {tickets[0].title!r}")
    print(f"stripped:   {strip(tickets[0].title)!r}")

    # Sort by the stripped title — no lambda in sight
    by_clean_title = sorted(tickets, key=lambda t: strip(t.title))
    print("sorted by stripped title:")
    for t in by_clean_title:
        print(f"  {strip(t.title)!r}")

    # Sort the bare strings by their stripped form, preserving original strings
    titles = [t.title for t in tickets]
    sorted_titles = sorted(titles, key=strip)
    print("bare titles sorted by strip():", sorted_titles)
```

`operator.methodcaller("strip")` returns a C-implemented callable. Its `__call__` slot — readable in `Modules/_operator.c` in the CPython source — looks up `getattr(obj, "strip")` (which is the bound method `str.strip`) and then calls it with no arguments. The result is `obj.strip()`. There is no Python frame per call; the entire invocation is C-level.

`strip(tickets[0].title)` returns `"Search returns 500"` — the leading `"  "` and trailing `"  "` removed. The `!r` format in the f-string is the senior-engineer move: it prints with repr so the whitespace is visible (`"  Search returns 500  "` with quotes vs. `Search returns 500` without). When debugging string cleaning, *always* use `!r` — without it, leading/trailing whitespace is invisible and you waste 30 minutes on a "bug" that's actually just your print hiding the problem.

The bare-string sort `sorted(titles, key=strip)` is the cleanest case: `strip` is a `methodcaller` instance, `sorted` calls it once per element, and the elements are sorted by their stripped form *without modifying them*. The original `titles` list is unchanged; the `sorted_titles` list contains the original strings ordered by their stripped form. This is the "sort by a method result" pattern that `methodcaller` exists for.

The first `sorted(tickets, key=lambda t: strip(t.title))` is slightly different — here we have to extract `t.title` first (using a `lambda`), then apply `strip`. This is the case where `methodcaller` cannot do the whole job alone: you need to extract a field *and* then call a method on it. The composition `lambda t: strip(t.title)` is the readable form. A pure-`operator` composition would be `lambda t: strip(operator.attrgetter("title")(t))` — which is correct but harder to read. The senior-engineer move: reach for `lambda` when composition is needed; reach for `methodcaller` when the operation is a single method call.

**Why does `sorted` not modify the elements?** Because `key=` returns a *sort key* — the comparison value — not a replacement. `sorted(["  Banana  ", "apple"], key=strip)` returns `["  Banana  ", "apple"]` (the originals), sorted as if each were stripped. If you want the *stripped* values, write `[strip(s) for s in sorted(strings, key=strip)]` — the comprehension modifies; the sort does not.

### Lines 46–56: `methodcaller("split", ",")` — pre-binding positional args

```python
def split_with_positional_args() -> None:
    """methodcaller('split', ',') pre-binds the positional arg."""
    split_comma = operator.methodcaller("split", ",")
    print(f"tags[0] raw:    {tickets[0].tags_csv!r}")
    print(f"tags[0] split:  {split_comma(tickets[0].tags_csv)}")

    # Apply to a list of CSV strings with map()
    csv_lines = [t.tags_csv for t in tickets]
    parsed = list(map(split_comma, csv_lines))
    print("all tag lists:", parsed)
```

`operator.methodcaller("split", ",")` stores both the method name `"split"` and the positional argument `","`. When called on `tickets[0].tags_csv` (which is `"auth,billing"`), it invokes `"auth,billing".split(",")` — returning `["auth", "billing"]`. The factory pre-binds the argument, so the returned callable is a 1-argument function (takes the string, returns the list).

The `map(split_comma, csv_lines)` pattern is the apply-method-to-iterable use case. `map` expects a 1-argument callable; `methodcaller("split", ",")` is exactly that. The result is `[['auth', 'billing'], ['auth', 'macos'], ['docs'], ['export', 'billing']]`. The alternative is a list comprehension `[s.split(",") for s in csv_lines]` — equally readable, equally fast. The senior-engineer move: use `map(methodcaller(...), ...)` when the operation is a single method call and you want to emphasise the functional style; use the comprehension when the operation is a more complex expression.

**Why does `methodcaller` pre-bind `","` instead of taking it as a second call argument?** Because the whole point of `methodcaller` is to produce a 1-argument callable for `key=` and `map`. If `methodcaller("split")` did not pre-bind `","`, calling `split_comma("auth,billing")` would have no separator to use. The pre-binding is what makes `methodcaller` composable with `sorted(key=...)` and `map(...)` — both of which call their callable with exactly one argument. The pre-binding is the same idea as `functools.partial` — see [[02-functools/03-partial]] — but specialised to "call a method by name on the argument".

### Lines 59–70: `methodcaller("replace", " ", "-")` — positional args, `str` methods

```python
def replace_with_positional_args() -> None:
    """str.replace is positional-only — pass args positionally."""
    replace_space_dash = operator.methodcaller("replace", " ", "-")
    title = "[Bug]  Auth fails on macOS"
    print(f"replaced: {replace_space_dash(title)!r}")

    # The sort-by-method-result pattern: sort by the slugified title
    by_slug = sorted(tickets, key=lambda t: replace_space_dash(t.title))
    print("sorted by slugified title:")
    for t in by_slug:
        print(f"  {replace_space_dash(t.title)!r}")
```

`operator.methodcaller("replace", " ", "-")` stores `name="replace"`, `args=(" ", "-")`. When called on a string, it invokes `s.replace(" ", "-")` — replacing all spaces with dashes. The double-space in `"[Bug]  Auth fails on macOS"` becomes `"[Bug]--Auth-fails-on-macOS"`.

**Danger — `str.replace` is positional-only.** Calling `s.replace(old=" ", new="-")` raises `TypeError: replace() takes no keyword arguments`. The CPython `str.replace` implementation marks the parameters as positional-only (the `/` in the signature `str.replace(self, old, new, count=-1, /)`). So `methodcaller("replace", old=" ", new="-")` — passing the arguments as keywords — also fails at call time, with the same `TypeError`. The correct form is `methodcaller("replace", " ", "-")` (positional). This is the most common trap with `methodcaller`: you assume methods take keyword arguments the way you'd call them in Python, but a substantial fraction of C-level built-in methods are positional-only. The fix is to test the method in isolation first — call `s.replace(old=" ", new="-")` in a REPL — and if it fails, use positional args in `methodcaller`.

### Lines 73–85: Keyword arguments

```python
def keyword_args_demo() -> None:
    """methodcaller accepts keyword args for methods that take them."""
    # str.split accepts sep= and maxsplit= as keyword args (it's in the signature,
    # even though the docs mark it positional-or-keyword).
    split_first_only = operator.methodcaller("split", sep=",", maxsplit=1)
    print(f"first split: {split_first_only(tickets[0].tags_csv)}")

    # list.sort(key=...) accepts key as a keyword
    nums = [[3, 1, 2], [9, 0, 5], [4, 4, 4]]
    sort_by_max = operator.methodcaller("sort")
    # Note: list.sort returns None — methodcaller returns whatever the method returns
    for n in nums:
        sort_by_max(n)
    print(f"in-place sorted: {nums}")
```

`operator.methodcaller("split", sep=",", maxsplit=1)` shows the keyword-argument path. `str.split` *does* accept `sep` and `maxsplit` as keyword arguments (its signature is `str.split(self, /, sep=None, maxsplit=-1)` — the `self` is positional-only, but `sep` and `maxsplit` are positional-or-keyword). So this form works: calling `split_first_only("auth,billing,search")` returns `["auth", "billing,search"]` — the first comma splits, the rest stays as one string because of `maxsplit=1`.

`methodcaller("sort")` on a `list` invokes `list.sort()` — which sorts the list *in place* and returns `None`. The demo loops over each `nums` sublist and sorts it in place. The `print(f"in-place sorted: {nums}")` shows `[[1, 2, 3], [0, 5, 9], [4, 4, 4]]` — the sublists are mutated, the outer list is not. The trap: `methodcaller` returns whatever the method returns, so `result = methodcaller("sort")(my_list)` gives you `None`, not the sorted list. This is the same trap as `list.sort` itself — Python's `list.sort` returns `None` to signal "this was an in-place operation, don't chain me" — and `methodcaller` faithfully passes that `None` through.

**Why does `list.sort` return `None`?** Because returning `self` would invite the bug `my_list = my_list.sort().append(4)` — a chain that looks like it modifies `my_list` but actually creates a `None.append` error. By returning `None`, CPython forces you to write the in-place call as a statement (`my_list.sort()`), not as an expression. `methodcaller("sort")` preserves this contract: the call returns `None`, the list is mutated in place. The senior-engineer move: don't write `result = methodcaller("sort")(my_list)`; write `methodcaller("sort")(my_list)` as a statement, then access `my_list` for the sorted result.

### Lines 88–100: Dunder methods

```python
def dunder_call_demo() -> None:
    """methodcaller can call a dunder — but it's almost never the right move."""
    len_caller = operator.methodcaller("__len__")
    print(f"len of title: {len_caller(tickets[0].title)}")

    # The normal way is just len(); the dunder form is rarely clearer.
    print(f"len (builtin): {len(tickets[0].title)}")

    # The one valid case: passing a len() callable as a value into a higher-order
    # function that expects a 1-arg callable. Use builtins.len instead.
    import builtins
    lens = list(map(builtins.len, [t.title for t in tickets]))
    print(f"all lengths: {lens}")
```

`operator.methodcaller("__len__")` calls `obj.__len__()` — the dunder that `len(obj)` invokes. So `len_caller(tickets[0].title)` is equivalent to `len(tickets[0].title)`. Both work; the dunder form is rarely the right call because the builtin `len()` is shorter, reads in English, and handles the type-protocol details (e.g. `__length_hint__` fallback for generators).

The "one valid case" for `methodcaller("__len__")` is when you need a 1-argument callable that returns the length of its argument — e.g. as a `key=` function in a sort. But even there, `builtins.len` (the function form, not the syntax form) is the cleaner choice: `sorted(items, key=len)` works because `len` is a function that takes one argument. The senior-engineer move: use the builtin when it exists; reserve `methodcaller("__len__")` and friends for cases where no builtin covers the operation and you genuinely want the dunder call as a value.

**Why mention dunder methods at all if they're rarely the right call?** Two reasons. First, completeness — `methodcaller` *does* call any method by name, and dunders are methods. Second, the **Bug** factor: a student who tries `methodcaller("__len__")` and discovers it works may start writing `methodcaller("__add__", other)` instead of `operator.add`. That's a bug — `operator.add(a, b)` is the senior-engineer form, covered in [[18-operator/03-functional-composition]]. The rule: use `methodcaller` for *public* method calls (`.strip`, `.split`, `.replace`, `.sort`); use the named `operator` functions (`operator.add`, `operator.mul`) for operator-semantic calls.

## Execution Trace

```bash
$ uv run python boardly/operator_methodcaller_demo.py
=== methodcaller('strip') ===
raw:        '  Search returns 500  '
stripped:   'Search returns 500'
sorted by stripped title:
  'Docs typo'
  'Export to CSV'
  'Search returns 500'
  '[Bug]  Auth fails on macOS'
bare titles sorted by strip(): ['Docs typo', '  Export to CSV  ', '  Search returns 500  ', '[Bug]  Auth fails on macOS']

=== methodcaller('split', ',') ===
tags[0] raw:    'auth,billing'
tags[0] split:  ['auth', 'billing']
all tag lists: [['auth', 'billing'], ['auth', 'macos'], ['docs'], ['export', 'billing']]

=== methodcaller('replace', ' ', '-') ===
replaced: '[Bug]--Auth-fails-on-macOS'
sorted by slugified title:
  '--Export-to-CSV--'
  '--Search-returns-500--'
  'Docs-typo'
  '[Bug]--Auth-fails-on-macOS'

=== keyword args ===
first split: ['auth', 'billing']
in-place sorted: [[1, 2, 3], [0, 5, 9], [4, 4, 4]]

=== dunder methods ===
len of title: 22
len (builtin): 22
all lengths: [22, 26, 9, 17]
```

The first block shows `methodcaller("strip")` returning `"Search returns 500"` from `"  Search returns 500  "`. The sort by stripped title produces the four titles in alphabetical order of their stripped forms — `Docs typo` (D, ASCII 68) comes first, then `Export to CSV` (E, 69), then `Search returns 500` (S, 83), then `[Bug]  Auth fails on macOS` (`[` is ASCII 91, which sorts after uppercase letters). The bare-string sort produces the same order, but the elements are the *original* strings (with whitespace preserved), not the stripped forms — `key=` is a projection, not a transformation.

The second block shows `methodcaller("split", ",")` parsing `"auth,billing"` into `["auth", "billing"]`. The `map` over the four CSV strings produces the four tag lists. Note the list-of-lists shape — the import pipeline would normally flatten or assign these to a `tags: list[str]` field on a parsed `Ticket`.

The third block shows `methodcaller("replace", " ", "-")` slugifying titles. The double space in `"[Bug]  Auth fails on macOS"` becomes `"[Bug]--Auth-fails-on-macOS"`. The leading/trailing whitespace in `"  Export to CSV  "` and `"  Search returns 500  "` becomes `--` on both ends — `replace` touches *all* spaces, not just interior ones (which is why `strip` and `replace` are often composed: `strip` first to remove leading/trailing, then `replace` for the interior). The sort by slugified title is alphabetical by the slug form: strings starting with `-` (ASCII 45) sort before strings starting with `D` (ASCII 68) or `[` (ASCII 91).

The fourth block shows `methodcaller("split", sep=",", maxsplit=1)` returning `["auth", "billing"]` — the input `"auth,billing"` has only one comma, so `maxsplit=1` is enough to split it fully. If the input had multiple commas (e.g. `"a,b,c"`), the result would be `["a", "b,c"]` — only the first comma splits. The `list.sort` example shows the in-place mutation: the three sublists are sorted, the outer list is unchanged, and the method returns `None` (so we don't capture a return value).

The fifth block shows `methodcaller("__len__")` returning `22` for the title's length — the same as `len(title)`. The `map(builtins.len, ...)` shows the cleaner form: `len` is a function, so it works directly with `map` and `key=` without needing a `methodcaller`.

## Common Mistakes

### Mistake 1: Passing keyword arguments to a positional-only method

```python
# Wrong:
replace_space = operator.methodcaller("replace", old=" ", new="-")
replace_space("a b c")  # TypeError: replace() takes no keyword arguments
```

**Symptom:** `TypeError: replace() takes no keyword arguments` when the methodcaller is called.

**Why:** `str.replace` is positional-only — its parameters are not exposed as keywords. `methodcaller` stores the keyword args you pass and forwards them as `**kwargs` to the method call, so the method receives `old=` and `new=` and rejects them.

**Fix:** Pass the arguments positionally: `operator.methodcaller("replace", " ", "-")`. The rule: test the method in isolation (`"a b c".replace(old=" ", new="-")`) before wiring it into `methodcaller`. If the isolated call fails with `takes no keyword arguments`, use positional args in `methodcaller`.

### Mistake 2: Expecting the sort to modify the elements

```python
titles = ["  Banana  ", "apple", " Cherry "]
sorted_titles = sorted(titles, key=operator.methodcaller("strip"))
# Student expects: ["Banana", "Cherry", "apple"] (stripped)
# Actual:          ["  Banana  ", " Cherry ", "apple"] (originals, sorted by stripped)
```

**Symptom:** The sorted list still has the leading/trailing whitespace — the student is confused why `strip` didn't "stick".

**Why:** `key=` is a *projection* — `sorted` calls it to get a comparison value, then compares the originals. The stripped form is used only for comparison; the elements in the output are the *original* strings, not the stripped ones. This is the same behaviour as every other `key=` function in Python's sort.

**Fix:** Compose `strip` and `sorted` explicitly: `sorted_titles = [s.strip() for s in sorted(titles, key=strip)]` — sort by the stripped form (preserving originals), then strip each in a comprehension. The two-step is the only way to *both* sort by a method result *and* return the transformed values.

### Mistake 3: Trying to chain methods with one `methodcaller`

```python
# Wrong:
slug = operator.methodcaller("strip.lower")  # ← this is one method name "strip.lower"
slug("  Hello  ")  # AttributeError: 'str' object has no attribute 'strip.lower'

# Student expected:
slug("  Hello  ")  # → "hello"
```

**Symptom:** `AttributeError: 'str' object has no attribute 'strip.lower'` (or whatever method-name string you passed).

**Why:** `methodcaller` takes the method name as a single string. It does not split on `.` — unlike `attrgetter` which *does* support dotted attribute paths. There is no method-naming syntax for "call `.strip().lower()`"; `methodcaller` calls *one* method.

**Fix:** Compose two `methodcaller`s, or use a `lambda`:
```python
strip_then_lower = lambda s: s.strip().lower()  # the readable composition
# Or compose explicitly:
strip = operator.methodcaller("strip")
lower = operator.methodcaller("lower")
result = lower(strip("  Hello  "))   # "hello"
```
For two-step chains, the `lambda` is the senior-engineer choice. `methodcaller` shines for *single* method calls; for chains, the `lambda` is shorter and reads more naturally. The boardly style guide explicitly allows the `lambda` form for two-method chains.

## Engineering Trade-Offs

**Decision:** Use `methodcaller` for single-method calls — `.strip()`, `.split(",")`, `.replace(" ", "-")`, `.sort()` — at every `key=` site and in every `map`/`filter` that calls exactly one method. Use a `lambda` for two-method chains (`.strip().lower()`) and for field-then-method compositions (`lambda t: t.title.strip()`).

**Both sides:** The alternative is the inline `lambda`. The `lambda` wins when (a) the operation is a composition of two or more methods, (b) the operation needs a field extraction before the method call (`lambda t: t.title.strip()`), or (c) the operation needs an inline transform on the method result (`lambda s: len(s.strip())`). `methodcaller` wins when the operation is exactly one method call with zero or more pre-bound arguments — which is most "clean this string" / "split this string" / "sort by this method" call sites.

**Commitment:** `boardly` uses `methodcaller("strip")` in `tickets/import.py` to clean titles, `methodcaller("split", ",")` to parse tag CSVs, and `methodcaller("replace", " ", "-")` to slugify. The project's lint config flags `lambda s: s.strip()`-shaped lambdas with `E731` and suggests `methodcaller("strip")` as the rewrite. The boardly style guide (see [[25-Reference-Library/Engineering-Decision-Log]]) commits to "single-method callables go through `methodcaller`".

**Why use `methodcaller` when a `def` is two more lines?** Two reasons. First, the `def` adds a name to the module namespace that a future reader has to track down — `clean_title` is just `s.strip()` wrapped in a function, and the indirection costs more than it pays. Second, the `def` form does not compose with `map`/`key=` naturally — `map(clean_title, strings)` is fine but `sorted(strings, key=clean_title)` requires the function to take exactly one argument and be reusable, which a one-off `def` may not be. `methodcaller` is the inline-form callable that doesn't add names.

## Exercises

1. **Exercise 1 — Use `methodcaller("lower")` to sort.** Add `sorted(titles, key=operator.methodcaller("lower"))` to `strip_demo`. Verify the sort is now case-insensitive (uppercase before lowercase no longer matters — `'Docs'` and `'docs'` sort together). `Verify: uv run python boardly/operator_methodcaller_demo.py`

2. **Exercise 2 — Parse tags with `maxsplit=2`.** Change `split_comma` to `methodcaller("split", ",", 2)` (positional `maxsplit=2`). Apply to `"auth,billing,search,deploy"`. Verify the result is `["auth", "billing", "search,deploy"]` — first two commas split, the rest stays. `Verify: uv run python boardly/operator_methodcaller_demo.py`

3. **Exercise 3 — Slugify with `strip` + `replace`.** Compose `strip = methodcaller("strip")` and `replace = methodcaller("replace", " ", "-")`. Apply both to `"  Hello World  "`. Verify the result is `"Hello-World"`. `Verify: uv run python boardly/operator_methodcaller_demo.py`

4. **Exercise 4 — Sort tickets by tag count.** Use `sorted(tickets, key=lambda t: len(methodcaller("split", ",")(t.tags_csv)))`. Verify the tickets are ordered by number of tags (single-tag tickets first, multi-tag tickets last). `Verify: uv run python boardly/operator_methodcaller_demo.py`

5. **Exercise 5 — Method-by-name dynamic dispatch.** Write a function `apply_method(name, *args, obj)` that returns `methodcaller(name, *args)(obj)`. Use it to dispatch between `"strip"`, `"lower"`, and `"upper"` based on a config string. This is the rare dynamic-dispatch case where `methodcaller` is genuinely useful — when the method name comes from configuration, not from source code. `Verify: uv run python boardly/operator_methodcaller_demo.py`

## Verification

```bash
$ uv run python boardly/operator_methodcaller_demo.py
=== methodcaller('strip') ===
raw:        '  Search returns 500  '
stripped:   'Search returns 500'
sorted by stripped title:
  'Docs typo'
  'Export to CSV'
  'Search returns 500'
  '[Bug]  Auth fails on macOS'
bare titles sorted by strip(): ['Docs typo', '  Export to CSV  ', '  Search returns 500  ', '[Bug]  Auth fails on macOS']

=== methodcaller('split', ',') ===
tags[0] raw:    'auth,billing'
tags[0] split:  ['auth', 'billing']
all tag lists: [['auth', 'billing'], ['auth', 'macos'], ['docs'], ['export', 'billing']]

=== methodcaller('replace', ' ', '-') ===
replaced: '[Bug]--Auth-fails-on-macOS'
sorted by slugified title:
  '--Export-to-CSV--'
  '--Search-returns-500--'
  'Docs-typo'
  '[Bug]--Auth-fails-on-macOS'

=== keyword args ===
first split: ['auth', 'billing']
in-place sorted: [[1, 2, 3], [0, 5, 9], [4, 4, 4]]

=== dunder methods ===
len of title: 22
len (builtin): 22
all lengths: [22, 26, 9, 17]
```

## Previously Learned Here

- [[18-operator/01-itemgetter-attrgetter]] — `itemgetter` and `attrgetter` *extract* (by index or attribute); `methodcaller` *invokes* (by method name). The three factories form the `operator` tripod — every trivial callable has a name now.

## What's Next

[[18-operator/03-functional-composition]] — the third leg of the section. Where the first two lessons covered the *factories* (`itemgetter`, `attrgetter`, `methodcaller`), the third lesson covers the *infix-operator function table* — `operator.add`, `operator.mul`, `operator.and_`, `operator.or_`, `operator.contains`, `operator.truth`, `operator.not_` — and the `reduce(operator.add, nums)` pattern that ties them to `functools`. The opinion is the same as `reduce`'s: prefer the built-in (`sum`, `any`, `all`) when one exists; reach for `operator` when the operation is genuinely a value passed to a higher-order function.

- The arithmetic table (`add`, `sub`, `mul`, `truediv`, `floordiv`, `mod`, `pow`).
- The bitwise table (`and_`, `or_`, `xor`, `invert`, `lshift`, `rshift`).
- `operator.contains(a, b)` == `b in a` and `operator.truth`/`not_`.
- `reduce(operator.add, nums)` — and why `sum(nums)` usually wins.

## Sources

- **`operator.methodcaller`** — https://docs.python.org/3/library/operator.html#operator.methodcaller — accessed 2026-10-23 — the canonical reference for the third factory, with the `*args, **kwargs` signature.
- **`operator` — Standard operators as functions** — https://docs.python.org/3/library/operator.html — accessed 2026-10-23 — the section's root reference; the `methodcaller` entry sits alongside `itemgetter` and `attrgetter`.
- **`str.replace` (positional-only)** — https://docs.python.org/3/library/stdtypes.html#str.replace — accessed 2026-10-23 — the signature `str.replace(old, new, count=-1, /)` documents the positional-only `/` that breaks keyword-form `methodcaller` calls.

## What We Learned

- You can apply `operator.methodcaller(name, *args, **kwargs)` to build a callable that invokes `name` on its argument.
- You can distinguish `methodcaller` from `attrgetter` — `attrgetter` reads, `methodcaller` calls.
- You can sort by a method result — `sorted(strings, key=methodcaller("strip"))` — without a `lambda`.
- You can pre-bind positional and keyword arguments — `methodcaller("split", sep=",")` and `methodcaller("replace", " ", "-")`.
- You can call a dunder — `methodcaller("__len__")(s)` — and you know why the builtin (`len`) is almost always the cleaner form.
