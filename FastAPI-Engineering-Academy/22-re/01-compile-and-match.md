---
title: "Lesson 01: compile & match — Pattern, Match, fullmatch"
aliases:
 - re.compile
 - re.Pattern
 - re.Match
 - re.fullmatch
 - match vs fullmatch
tags:
 - re
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[22-re/02-search-findall-finditer]]"
 - "[[22-re/03-sub-and-named-groups]]"
 - "[[22-re/04-re-in-validation]]"
first_taught_in: "22-re/01-compile-and-match"
---

# Lesson 01: compile & match — Pattern, Match, fullmatch

*Why `boardly`'s `slug` and `ticket_id` validators compile the pattern once at module load, call `pattern.fullmatch(value)` at the boundary, and read the named group out of the `Match` object — and the one-line mistake that lets `"TKT-deadbeef00 extra"` past a `re.match`.*

**You're at the very beginning of Section 22.**

You have written `re.match(r"\d+", text)` in a route handler and seen it work, and seen it work on the wrong input, and moved on without knowing why. You have written the same pattern as a string literal ten times in the same file and not noticed. You have hit `AttributeError: 'NoneType' object has no attribute 'group'` and patched it with `if m is not None:` without knowing that the pattern is the problem, not the calling code. This section is the standard-library `re` module — and `re` is what every FastAPI `Path` regex constraint, every slug validator, and every UUID-format check actually runs. Lesson 01 is the foundation: the `Pattern` object, the three matching operations that return one, and the `Match` object you read your captures out of. Take your time. Type every example. **This is how you learn.**

#re #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Compile a pattern once at module scope** — write `SLUG_RE = re.compile(r"...")`, explain why this skips the module-internal pattern cache on every call, and read the type annotation `re.Pattern[str]` (Python 3.9+) at the boundary.
2. **Distinguish `match` from `fullmatch`** — explain that `re.match` anchors only at the *start* of the string while `re.fullmatch` (3.4+) anchors at *both* ends, and predict which one rejects trailing junk.
3. **Read a `Match` object** — call `.group(0)`, `.group("name")`, `.groups()`, `.groupdict()`, `.span()`, `.start()`, `.end()`, and explain what `.string` and `.re` give you.
4. **Use the `re.ASCII` flag** — explain why the `re.ASCII` flag forces `\w` to mean `[a-zA-Z0-9_]` instead of every Unicode word character, and when that matters for a slug validator.
5. **State the rule** that the rest of the section depends on: validate strings with `pattern.fullmatch(value)`, not `re.match(pattern, value)`, and never let `m.group(...)` run without a `None` check.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. This lesson's compiled patterns are annotated `re.Pattern[str]`; you need to read that as "a `Pattern` that operates on `str` inputs".
- **A typed model to validate** — [[06-dataclasses/01-dataclass-Basics]]. The boardly `Project` dataclass carries `slug: str`; that field is the running example.
- **About 35–50 minutes of focused time.**

**The most common gap: thinking `re.match` and `re.fullmatch` are interchangeable.**

They are not. `re.match` anchors only at the start; `re.fullmatch` anchors at both ends. A student who writes `re.match(r"\d{4}", year_string)` to validate a four-digit year will accept `"2026abc"` because `match` is happy with the prefix `"2026"`. The right call is `re.fullmatch(r"\d{4}", year_string)` — or, equivalently, `re.match(r"^\d{4}$", year_string)`. The whole lesson turns on this single distinction. Get it right once and the rest of the section follows.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/validation/ticket_validator.py — the bad old days
import re

def parse_ticket_id(text: str) -> str:
    m = re.match(r"TKT-[a-f0-9]{8,12}", text)
    return m.group(0)                # AttributeError if m is None
```

Two bugs in three lines:

1. **`re.match` accepts trailing junk.** `parse_ticket_id("TKT-deadbeef00 EXTRA STUFF")` returns `"TKT-deadbeef00"`. The `re.match` operation anchors only at the start of the string; it does not require the match to reach the end. The pattern matched the prefix, the rest of the string is silently ignored, and the function returns the prefix as if it were the whole input. A client that submitted an attacker-crafted string with a valid-looking prefix and an SQL-injection payload in the trailing portion sails through the validator.
2. **`m.group(0)` raises `AttributeError` on a non-match.** When the pattern does not match at all (say the input is `"BAD-ticket"`), `re.match` returns `None`. The next line calls `None.group(0)` and raises `AttributeError: 'NoneType' object has no attribute 'group'`. The error message does not mention the pattern, the input, or the validator; the operator who reads it has to grep for the line number to know which validator blew up.

The fix is two-fold: use `re.fullmatch` so the whole string must match, and check the `Match` (or `None`) return before calling `.group(...)`. The compiled-`Pattern` form is the same fix and one more — it compiles the regex once at module load instead of on every call. That is what this lesson teaches.

## The Code

```python
# boardly/validation/compile_and_match.py
"""The compiled `Pattern` object, `match` vs `fullmatch`, and the `Match` accessors."""
import re
from dataclasses import dataclass


# 1. Compile once — reuse forever. The compiled Pattern is immutable; the module
#    caches the last ~512 compiled patterns internally, but explicit compile
#    skips the cache lookup on every call and tells your reader where the
#    pattern lives.
SLUG_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", re.ASCII)
TICKET_ID_RE = re.compile(r"TKT-(?P<seq>[a-f0-9]{8,12})")          # no ^...$ here


# 2. The boardly model that holds a slug
@dataclass
class Project:
    name: str
    slug: str


def validate_project(name: str, slug: str) -> Project:
    # 3. fullmatch() — anchored at BOTH ends. The whole string must be a slug.
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid slug: {slug!r} (must match the slug grammar)")
    return Project(name=name, slug=slug)


# 4. match vs fullmatch — the real difference
def parse_ticket_id(text: str) -> str:
    # match anchors at the START only. If the pattern lacks $, trailing junk is
    # silently accepted by match() but rejected by fullmatch().
    if TICKET_ID_RE.match(text) is None:
        raise ValueError(f"not a ticket id: {text!r}")
    # The second check uses fullmatch — the whole string must be the id.
    if TICKET_ID_RE.fullmatch(text) is None:
        raise ValueError(f"trailing junk on ticket id: {text!r}")
    return TICKET_ID_RE.match(text).group("seq")


# 5. The Match object — every accessor you'll actually use
def inspect_match() -> None:
    m = TICKET_ID_RE.match("TKT-deadbeef00")
    print("group(0):    ", m.group(0))           # the full match
    print("group('seq'):", m.group("seq"))        # named group by name
    print("groups():    ", m.groups())            # tuple of all groups
    print("groupdict(): ", m.groupdict())         # {name: value}
    print("span(0):     ", m.span(0))             # (start, end) tuple
    print("start(0):    ", m.start(0))            # 0
    print("end(0):      ", m.end(0))              # 14
    print("m.string:    ", m.string)             # the whole input string
    print("m.re:        ", m.re)                  # the compiled Pattern object


# 6. The two kinds of error message
if __name__ == "__main__":
    print("good project:", validate_project("Boardly", "boardly-2026"))
    try:
        validate_project("Boardly", "BAD Slug!")
    except ValueError as e:
        print("bad project:", e)

    print()
    print("ticket seq:", parse_ticket_id("TKT-deadbeef00"))
    try:
        parse_ticket_id("TKT-deadbeef00 extra")        # trailing junk
    except ValueError as e:
        print("trailing junk:", e)

    print()
    inspect_match()
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–8: The two compiled patterns

```python
import re
from dataclasses import dataclass


# 1. Compile once — reuse forever. The compiled Pattern is immutable; the module
#    caches the last ~512 compiled patterns internally, but explicit compile
#    skips the cache lookup on every call and tells your reader where the
#    pattern lives.
SLUG_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", re.ASCII)
TICKET_ID_RE = re.compile(r"TKT-(?P<seq>[a-f0-9]{8,12})")          # no ^...$ here
```

`re.compile(pattern, flags=0)` parses the pattern string into a compiled `re.Pattern` object once. The `Pattern` is immutable: it holds the parsed finite-state machine, the flag bits, the group count, and a `groupindex` dict mapping named groups to their group numbers. You can call `.match`, `.search`, `.fullmatch`, `.findall`, `.finditer`, `.sub`, `.subn`, `.split`, and `.scanner` on it — all the top-level `re.*` functions exist as bound methods on a compiled `Pattern`. The bound methods do *not* re-parse the pattern; they go straight to the engine.

The two patterns sit at module scope on purpose. They are constructed once when the module is first imported; every subsequent function call reuses the same `Pattern` object. The `re` module maintains an internal cache of the last ~512 compiled patterns (the `_cache` dict in `re/__init__.py`), so calling `re.match(r"...", s)` repeatedly is *not* as slow as parsing the regex every time — but the cache lookup has a cost (a dict hash, a tuple key including the flags), and explicit `re.compile` skips it. More important than the speed is the readability: a module-level `SLUG_RE` tells the reader "this is the slug pattern" once, instead of scattering the literal through every function.

The `re.ASCII` flag on `SLUG_RE` forces the `\w`, `\d`, `\s`, `\W`, `\D`, `\S` character classes inside the pattern to mean their ASCII-only forms (`[a-zA-Z0-9_]`, `[0-9]`, `[ \t\n\r\f\v]`, and complements) instead of their Unicode forms. The slug pattern here does not use any of those classes — it spells `[a-z0-9-]` explicitly — but the flag is the rule you write on a slug pattern regardless: it documents that "slugs are ASCII" and protects you against a future edit that introduces `\w` and silently admits `"héllo-wörld"` because `\w` in default (Unicode) mode matches letters with diacritics.

The `TICKET_ID_RE` pattern uses `(?P<seq>...)` — a *named group*. The name `seq` lets the calling code read `m.group("seq")` instead of `m.group(1)`, which is the difference between code that documents itself and code that requires you to count parentheses. Lesson 03 walks named groups in depth; this lesson only needs `m.group("seq")` to work.

**Why does the comment say `# no ^...$ here`?** Because the contrast with `SLUG_RE` matters. `SLUG_RE` has no `^` or `$` either, and it works because we call `.fullmatch` on it — `fullmatch` implicitly anchors both ends. `TICKET_ID_RE` has no `^`/`$` on purpose so that `.match` and `.fullmatch` give *different* answers on the same input and the lesson can show the distinction. In production validators you write one of two forms: either `re.compile(r"^...$")` and use `.match`, or `re.compile(r"...")` and use `.fullmatch`. The two are equivalent in result; the `.fullmatch` form is the modern idiom (3.4+) and is what boardly commits to.

**Warning — `re.match` is anchored at the start, not at both ends.**

This is the single most-repeated bug in the section. `re.match(r"TKT-[a-f0-9]{8,12}", "TKT-deadbeef00 trailing junk")` returns a `Match`, not `None`. The match starts at position 0, ends at the last matched character, and the trailing junk is silently ignored. If you want "the whole string is exactly this", use `re.fullmatch` or add explicit `^...$` anchors. Every slug/UUID/ticket-id validator in `boardly` uses `re.fullmatch` precisely so this bug cannot land.

### Lines 10–15: The boardly `Project` dataclass

```python
# 2. The boardly model that holds a slug
@dataclass
class Project:
    name: str
    slug: str
```

The `@dataclass` decorator generates `__init__`, `__repr__`, `__eq__`, and (because no fields are mutable) `__hash__` from the two annotated fields. The `slug: str` annotation tells the type checker and FastAPI (lesson 04) that this field holds a string. The dataclass itself performs no validation — `Project(name="x", slug="anything")` constructs successfully. Validation lives in `validate_project`, which is the function that actually calls `SLUG_RE.fullmatch(slug)`. The split between the model (data shape) and the validator (data correctness) is the FastAPI/Pydantic pattern; lesson 04 shows how Pydantic collapses the two into one with `field_validator` and `Field(pattern=...)`.

### Lines 17–21: `fullmatch` — the right call for "the whole string is exactly this"

```python
def validate_project(name: str, slug: str) -> Project:
    # 3. fullmatch() — anchored at BOTH ends. The whole string must be a slug.
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid slug: {slug!r} (must match the slug grammar)")
    return Project(name=name, slug=slug)
```

`SLUG_RE.fullmatch(slug)` returns a `Match` object if the entire `slug` matches the pattern, or `None` if any prefix or suffix fails. The `not` operator treats the `Match` as truthy (any non-`None` object is truthy in Python) and `None` as falsy, so `not <Match>` is `False` on a match and `True` on a non-match. The error message includes the *invalid value* (`{slug!r}`) so the operator can see what was rejected — this is the difference between a 422 the client can fix and a 422 the client has to email you about.

`re.fullmatch` was added in Python 3.4 (PEP-style minor release, not a PEP — it is a `bpo-6211` fix). On earlier Pythons you write `re.match(r"^...$", s)` and get the same behaviour; on 3.4+ you write `re.fullmatch(r"...", s)` and get clearer intent. The two are equivalent in result, but `.fullmatch` reads as "the whole string must match" and `.match` with anchors reads as "the start must match, and also the start must be at the start, and also the end must be at the end". Use the clearer form.

**Why does the validator return the `Project` instead of the slug?** Because the function's contract is "give me a valid `Project`", not "give me a valid slug". The slug is an *input*; the `Project` is the *output*. Returning the slug would force the caller to construct the `Project` separately, doubling the work. Returning the `Project` lets the caller write `p = validate_project(name, slug)` and get back a typed, validated object in one call. Lesson 04 collapses this further: Pydantic's `BaseModel` does the validation *during* construction, so `Project(name=..., slug=...)` itself raises on a bad slug and no separate validator function is needed.

### Lines 23–31: `match` vs `fullmatch` — the contrast

```python
# 4. match vs fullmatch — the real difference
def parse_ticket_id(text: str) -> str:
    # match anchors at the START only. If the pattern lacks $, trailing junk is
    # silently accepted by match() but rejected by fullmatch().
    if TICKET_ID_RE.match(text) is None:
        raise ValueError(f"not a ticket id: {text!r}")
    # The second check uses fullmatch — the whole string must be the id.
    if TICKET_ID_RE.fullmatch(text) is None:
        raise ValueError(f"trailing junk on ticket id: {text!r}")
    return TICKET_ID_RE.match(text).group("seq")
```

This function is deliberately redundant. It calls `TICKET_ID_RE.match(text)` *and* `TICKET_ID_RE.fullmatch(text)` on the same input, with the same pattern, to show the student exactly which inputs they accept differently. The pattern is `r"TKT-(?P<seq>[a-f0-9]{8,12})"` — no `^`, no `$`. So:

- On `"TKT-deadbeef00"`: `match` returns a `Match` from position 0 to 14 (the whole string). `fullmatch` returns the same `Match`. Both pass; the function returns `"deadbeef00"`.
- On `"TKT-deadbeef00 extra"`: `match` returns a `Match` from position 0 to 14 (stops at the space). `fullmatch` returns `None` because the trailing ` extra` is not consumed by the pattern. The first check passes (`match` is not `None`); the second check fails (`fullmatch` is `None`); the function raises `"trailing junk on ticket id"`.
- On `"BAD-ticket"`: `match` returns `None` because the start of the string is `BAD`, not `TKT`. The first check fails; the function raises `"not a ticket id"`.

The third call — `TICKET_ID_RE.match(text).group("seq")` — re-runs `match` because by the time we reach it we know both checks passed, so we know a `Match` exists. In production code you would cache the `Match` once:

```python
m = TICKET_ID_RE.fullmatch(text)
if m is None:
    raise ValueError(...)
return m.group("seq")
```

The lesson writes the two-check form to make the `match` vs `fullmatch` contrast visible. The production form is the cached `fullmatch` and the `m.group("seq")` once.

**Why does the comment say "if the pattern lacks `$`"?** Because if the pattern *had* a `$` — say `r"TKT-[a-f0-9]{8,12}$"` — then `match` and `fullmatch` would behave the same way: the `$` anchor already forces the match to reach the end of the string (modulo `re.MULTILINE`, where `$` matches at any `\n`). The lesson removes the `$` so the student can see the difference the hard way. In production, you choose one form: either write `^...$` and use `.match`, or write the pattern bare and use `.fullmatch`. Both work. Mixing them is what produces surprises.

### Lines 33–43: The `Match` object — every accessor you will actually use

```python
# 5. The Match object — every accessor you'll actually use
def inspect_match() -> None:
    m = TICKET_ID_RE.match("TKT-deadbeef00")
    print("group(0):    ", m.group(0))           # the full match
    print("group('seq'):", m.group("seq"))        # named group by name
    print("groups():    ", m.groups())            # tuple of all groups
    print("groupdict(): ", m.groupdict())         # {name: value}
    print("span(0):     ", m.span(0))             # (start, end) tuple
    print("start(0):    ", m.start(0))            # 0
    print("end(0):      ", m.end(0))              # 14
    print("m.string:    ", m.string)             # the whole input string
    print("m.re:        ", m.re)                  # the compiled Pattern object
```

`TICKET_ID_RE.match("TKT-deadbeef00")` returns a `re.Match` object — a small, immutable record of "where the match was, what each group captured, and the original input and pattern". The accessors:

- **`m.group(0)`** — the whole match (`"TKT-deadbeef00"`). Group `0` is the entire match; group `1` is the first parenthesised group, `2` the second, etc. `m.group()` with no argument returns the same as `m.group(0)`.
- **`m.group("seq")`** — the named-group capture (`"deadbeef00"`). You can also pass `1` here because `seq` is the first (and only) group; the name is just an alias for the number. Lesson 03 walks the `(?P<name>...)` syntax in detail.
- **`m.groups()`** — a tuple of all the captures, in order (`("deadbeef00",)`). Group `0` is excluded; only the parenthesised captures appear. If a group did not participate in the match (an optional `(...)?` that did not fire), it appears as `None`.
- **`m.groupdict()`** — a dict mapping every *named* group to its capture (`{"seq": "deadbeef00"}`). Unnamed groups do not appear here; that is why `groupdict()` is empty for a pattern with no named groups.
- **`m.span(0)`** — a `(start, end)` tuple of the whole match's positions in `m.string`. `m.span(1)` would give the `seq` group's span, `m.span("seq")` the same. All positions are character offsets; on a `str` input they are code-point offsets.
- **`m.start(0)`** / **`m.end(0)`** — the individual halves of `m.span(0)`. `m.start(0)` is `0` here because the match anchored at the start; `m.end(0)` is `14`, the index *after* the last matched character.
- **`m.string`** — the original input string the match was performed against. Useful when you are passing `Match` objects around between functions and need to recover the source text.
- **`m.re`** — the compiled `Pattern` object that produced this `Match`. Lets you read `m.re.pattern` (the source string) or `m.re.flags` (the integer flag bits) from a `Match` alone.

The `Match` object is *not* a `tuple` and is *not* a `dict`. It is its own small class, defined in `re._compile`'s internal `Match` type. It does not support iteration directly (so `for g in m:` is a `TypeError`); if you want all captures as a sequence, call `m.groups()` explicitly.

**Why does `m.group(0)` exist when `m.group("seq")` is the named capture?** Because `0` is the whole match, not "the first group". The whole match is the text the engine consumed — the literal `TKT-` plus the digits — and it is the capture you want when you need "the matched substring" rather than "the part inside the parentheses". Many students reach for `m.group(1)` expecting the whole match and are surprised to get only the inner part. `0` is the whole match; `1` is the first capture. Get this distinction right once and the rest of the API follows.

### Lines 45–54: The two error paths

```python
# 6. The two kinds of error message
if __name__ == "__main__":
    print("good project:", validate_project("Boardly", "boardly-2026"))
    try:
        validate_project("Boardly", "BAD Slug!")
    except ValueError as e:
        print("bad project:", e)

    print()
    print("ticket seq:", parse_ticket_id("TKT-deadbeef00"))
    try:
        parse_ticket_id("TKT-deadbeef00 extra")        # trailing junk
    except ValueError as e:
        print("trailing junk:", e)

    print()
    inspect_match()
```

The `if __name__ == "__main__":` guard is the Python idiom for "run this block only when the file is executed directly, not when it is imported". `boardly/validation/compile_and_match.py` is intended to be a runnable demo as well as a module the rest of the package imports (for `SLUG_RE` and `TICKET_ID_RE`); the guard keeps the demo runs from happening on every import.

The four `print(...)` / `try ... except` blocks each demonstrate one path through the validator: a good slug, a bad slug, a good ticket id, a ticket id with trailing junk. The bad-path `try`/`except ValueError` swallows the exception and prints the message, so the script does not crash and the student sees the actual error string the validator produces. In production you would let the `ValueError` propagate to FastAPI/Pydantic, which converts it to an HTTP 422 with a structured body — that is lesson 04.

## Execution Trace

```bash
$ uv run python boardly/validation/compile_and_match.py
good project: Project(name='Boardly', slug='boardly-2026')
bad project: invalid slug: 'BAD Slug!' (must match the slug grammar)

ticket seq: deadbeef00
trailing junk: trailing junk on ticket id: 'TKT-deadbeef00 extra'

group(0):     TKT-deadbeef00
group('seq'): deadbeef00
groups():     ('deadbeef00',)
groupdict():  {'seq': 'deadbeef00'}
span(0):      (0, 14)
start(0):     0
end(0):       14
m.string:     TKT-deadbeef00
m.re:         re.compile('TKT-(?P<seq>[a-f0-9]{8,12})')
```

## Common Mistakes

### Mistake 1: `m.group(...)` on a non-match

```python
m = re.match(r"^\d+$", "abc")       # m is None
digits = m.group(0)                  # AttributeError: 'NoneType' has no 'group'
```

**Symptom:** `AttributeError: 'NoneType' object has no attribute 'group'` from a validator that called `re.match` on a non-matching input. The stack trace points at the `.group(...)` line, not at the regex — the operator has to grep to find the validator.
**Why:** `re.match`, `re.fullmatch`, and `re.search` all return `None` when the pattern does not match. They do *not* raise. The contract is "a `Match` or `None`", and the caller is responsible for checking. Calling `.group(...)` on `None` is the bug; the validator should have branched on `m is None`.
**Fix:** Cache the match and check it first:

```python
m = re.match(r"^\d+$", "abc")
if m is None:
    raise ValueError("not all digits")
digits = m.group(0)
```

Or use the truthy trick: `if not (m := re.match(r"^\d+$", text)): raise ...`.

### Mistake 2: Using `re.match` when you meant `re.fullmatch`

```python
def validate_slug(slug: str) -> str:
    if not re.match(r"[a-z0-9-]+", slug):
        raise ValueError("bad slug")
    return slug

validate_slug("boardly-2026<script>")   # returns the slug, with trailing junk
```

**Symptom:** The validator accepts strings that begin with a valid prefix and continue with anything else. The trailing `<script>` is silently dropped by `re.match` because it anchored only at the start; the rest of the string is ignored.
**Why:** `re.match` anchors at position 0 but does *not* require the match to reach the end of the string. Without an explicit `$` (or the `re.fullmatch` call), trailing junk is accepted. The validator's `if not re.match(...)` returns `False` (because a `Match` was returned), the function returns the slug, and the caller has a value that did not actually pass the validator's intent.
**Fix:** Use `re.fullmatch` (3.4+):

```python
def validate_slug(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError("bad slug")
    return slug
```

Or add explicit `^...$` anchors to the pattern and keep `re.match`. Both work; `fullmatch` is the modern idiom.

### Mistake 3: Forgetting the `re.ASCII` flag on a slug

```python
SLUG_RE = re.compile(r"[\w-]+")            # default is Unicode
SLUG_RE.fullmatch("héllo-wörld")            # returns a Match!
```

**Symptom:** The slug validator accepts non-ASCII characters that you did not intend to allow. The validator passes `"héllo-wörld"` because `\w` in Python 3 defaults to "Unicode word character", which includes letters with diacritics, Cyrillic, Han, etc.
**Why:** In Python 3, the default for `\w` is `re.UNICODE` (the implicit flag). `\w` matches any character that has the Unicode `Alphabetic` or `Decimal_Number` property, plus underscore — that is far wider than the ASCII `[a-zA-Z0-9_]` the slug grammar intends. Slugs are ASCII by convention; the validator must opt into ASCII explicitly.
**Fix:** Add `re.ASCII` (alias `re.A`):

```python
SLUG_RE = re.compile(r"[\w-]+", re.ASCII)
SLUG_RE.fullmatch("héllo-wörld")            # None — rejected
```

`re.ASCII` makes `\w` mean `[a-zA-Z0-9_]` and `\d` mean `[0-9]`. Use it for every pattern that operates on wire-format identifiers (slugs, ticket ids, UUID strings, ISO dates).

### Mistake 4: Calling `re.match` repeatedly with the same pattern literal

```python
def validate(slug: str) -> bool:
    return re.match(r"^[a-z0-9-]+$", slug) is not None     # parses every call (cached, but still)
```

**Symptom:** No bug visible — but the function pays a cache-lookup cost on every call, and the pattern literal is duplicated if it appears in another function.
**Why:** `re.match(r"...", s)` parses the pattern lazily, then checks the module-level `_cache` dict for a previously compiled `Pattern`. The cache key is `(pattern, flags)`, and the lookup is O(1), but the lookup is still work — and the literal is still code duplication if it appears in multiple places.
**Fix:** Compile once at module scope:

```python
SLUG_RE = re.compile(r"^[a-z0-9-]+$")

def validate(slug: str) -> bool:
    return SLUG_RE.match(slug) is not None
```

The compiled `Pattern` is constructed once at import; every call to `validate` reuses it. The speed gain is modest (cache lookup vs bound-method call), but the readability gain — "the slug pattern lives at line N of this module" — is real.

## Engineering Trade-Offs

**Decision:** `boardly` validates every wire-format string with a module-level `re.compile(...)` followed by `pattern.fullmatch(value)`, and reads captures out via `m.group("name")`.
**Both sides:** The alternative is `pydantic.Field(pattern=r"...", ...)` on a `BaseModel` field, which lets Pydantic do the regex check at the boundary without you writing a `field_validator`. That is shorter and gives you the OpenAPI `pattern` keyword for free; lesson 04 shows it. The trade-off: `Field(pattern=...)` only gives you a boolean accept/reject — you cannot transform the input (lowercasing a slug, extracting a sub-group, normalising whitespace) inside the regex check. The hand-written `field_validator` with `re.fullmatch` lets you transform and validate in one pass. For a slug that needs no transformation, `Field(pattern=...)` is shorter. For a ticket-id parser that needs the `seq` group extracted, the compiled pattern and `.group("seq")` is the right tool.
**Commitment:** `boardly` uses `re.compile` at module scope and `pattern.fullmatch` in `field_validator`s for every validator that needs to *extract* a group (ticket-id parsing, UUID segment parsing). For pure accept/reject validation (slug format, hex colour, ISO date), `Field(pattern=...)` is the preferred form and is covered in lesson 04.

## Exercises

1. **Exercise 1 — Tighten the slug pattern.** The current `SLUG_RE` accepts a one-character slug (`"a"`), which is too permissive for a real product. Change the minimum length to 3 characters (so `"abc"` is accepted, `"ab"` is rejected). Re-run and confirm `"ab"` is now rejected. `Verify: uv run python -c "from boardly.validation.compile_and_match import SLUG_RE; assert SLUG_RE.fullmatch('abc'); assert SLUG_RE.fullmatch('ab') is None"`
2. **Exercise 2 — Add a UUID validator.** Add a third compiled pattern `UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.ASCII)` and a `parse_uuid(text: str) -> str` function that uses `fullmatch`. Confirm `"deadbeef-dead-dead-dead-deadbeefdead"` is accepted and `"deadbeef-dead-dead-dead-deadbeefdead extra"` is rejected. `Verify: uv run python -c "from boardly.validation.compile_and_match import parse_uuid; assert parse_uuid('deadbeef-dead-dead-dead-deadbeefdead'); import pytest; pytest.raises(ValueError, parse_uuid, 'bad')"`
3. **Exercise 3 — Compare `match` and `fullmatch` directly.** Write a function `compare(text: str) -> tuple[bool, bool]` that returns `(TICKET_ID_RE.match(text) is not None, TICKET_ID_RE.fullmatch(text) is not None)`. Confirm that `compare("TKT-abc12345")` returns `(True, True)`, `compare("TKT-abc12345 extra")` returns `(True, False)`, and `compare("BAD")` returns `(False, False)`. `Verify: uv run python -c "from boardly.validation.compile_and_match import compare; assert compare('TKT-abc12345') == (True, True); assert compare('TKT-abc12345 extra') == (True, False); assert compare('BAD') == (False, False)"`
4. **Exercise 4 — Read `m.re.pattern`.** The `Match` object exposes `.re`, which is the compiled `Pattern`. Write a function `pattern_string(m: re.Match) -> str` that returns the pattern's source string by reading `m.re.pattern`. Confirm it returns `"TKT-(?P<seq>[a-f0-9]{8,12})"` for a `TICKET_ID_RE.match(...)`. `Verify: uv run python -c "from boardly.validation.compile_and_match import TICKET_ID_RE, pattern_string; m = TICKET_ID_RE.match('TKT-deadbeef00'); assert pattern_string(m) == 'TKT-(?P<seq>[a-f0-9]{8,12})'"`
5. **Exercise 5 — Compile with `re.VERBOSE`.** Rewrite `SLUG_RE` using `re.VERBOSE` (alias `re.X`), which lets you put whitespace and comments inside the pattern. The verbose form should match the same set of strings as the compact form. Confirm `SLUG_RE.fullmatch("boardly-2026")` still returns a `Match`. `Verify: uv run python -c "from boardly.validation.compile_and_match import SLUG_RE; assert SLUG_RE.fullmatch('boardly-2026') is not None"`

## Verification

```bash
$ uv run python boardly/validation/compile_and_match.py
good project: Project(name='Boardly', slug='boardly-2026')
bad project: invalid slug: 'BAD Slug!' (must match the slug grammar)

ticket seq: deadbeef00
trailing junk: trailing junk on ticket id: 'TKT-deadbeef00 extra'

group(0):     TKT-deadbeef00
group('seq'): deadbeef00
groups():     ('deadbeef00',)
groupdict():  {'seq': 'deadbeef00'}
span(0):      (0, 14)
start(0):     0
end(0):       14
m.string:     TKT-deadbeef00
m.re:         re.compile('TKT-(?P<seq>[a-f0-9]{8,12})')
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — the `re.Pattern[str]` and `re.Match[str]` type annotations this lesson writes in the docstrings (Python 3.9+ subscripts).
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` decorator that generates `__init__`/`__repr__`/`__eq__` for the `Project` model this lesson validates.
- [[09-enum/05-Enum-in-APIs]] — the FastAPI enum integration; `StrEnum` and `re.fullmatch` are the two standard-library ways to constrain a string field, and that lesson explains when each is appropriate.

## What's Next

[[22-re/02-search-findall-finditer]] — Lesson 01 covers the *single-match* operations (`match`, `fullmatch`). The next lesson covers the *multi-match* family: `re.search` (the first match anywhere in the string, not anchored at the start), `re.findall` (a list of every match's full text, or every group-1 capture, or a list of tuples — depending on how many groups the pattern has), and `re.finditer` (3.7+, a lazy iterator of `Match` objects that lets you stream a multi-gigabyte log file without materialising a list of matches). Lesson 02 also covers the rarely-used `re.Scanner` class and the difference between `findall` returning strings (when you have 0 or 1 groups) and `finditer` always returning `Match` objects (which give you `.group()`, `.span()`, `.groupdict()`, etc.).

- **Lesson 02** — `re.search`, `re.findall`, `re.finditer`, the `re.Scanner` class.
- **Lesson 03** — `re.sub`, `re.subn`, the `(?P<name>...)` named-group syntax in depth, callable replacements.
- **Lesson 04** — `re` inside Pydantic `field_validator`s and FastAPI `Field(pattern=...)`; the ReDoS catastrophic-backtracking trap.

## Sources

- **Python `re` module documentation** — https://docs.python.org/3/library/re.html — accessed 2026-10-23 — the source-of-truth reference for `re.compile`, `re.Pattern`, `re.Match`, `re.match`, `re.fullmatch`, and every flag.
- **Python `re` "Match Objects" reference** — https://docs.python.org/3/library/re.html#match-objects — accessed 2026-10-23 — the `.group`, `.groups`, `.groupdict`, `.span`, `.start`, `.end`, `.string`, `.re` accessors documented in one place.
- **Python `re` "Regular Expression Objects" reference** — https://docs.python.org/3/library/re.html#regular-expression-objects — accessed 2026-10-23 — the `.match`, `.fullmatch`, `.search`, `.findall`, `.finditer`, `.sub`, `.subn`, `.split`, `.scanner`, `.pattern`, `.flags`, `.groups`, `.groupindex` methods and attributes of a compiled `Pattern`.

## What We Learned

- You can now compile a pattern once at module scope with `re.compile(r"...", re.ASCII)` and explain why the bound methods on the `Pattern` object skip the cache lookup on every call.
- You can distinguish `re.match` (anchored at the start) from `re.fullmatch` (3.4+, anchored at both ends) and predict which one rejects trailing junk.
- You can read a `Match` object's `.group(0)`, `.group("name")`, `.groups()`, `.groupdict()`, `.span(0)`, `.start(0)`, `.end(0)`, `.string`, and `.re` accessors.
- You can defend the choice of `re.ASCII` over the default Unicode mode for slug and identifier patterns, and explain the `\w` semantics difference.
- You can name the rule the rest of the section depends on: validate wire-format strings with `pattern.fullmatch(value)`, never with `re.match(pattern, value)` alone, and never let `m.group(...)` run without a `None` check.
