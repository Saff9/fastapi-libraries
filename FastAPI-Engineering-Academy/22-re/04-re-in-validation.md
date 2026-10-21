---
title: "Lesson 04: re in validation — Pydantic, ReDoS, and the anti-patterns"
aliases:
 - re in Pydantic
 - re in FastAPI
 - Field pattern
 - ReDoS
 - catastrophic backtracking
 - atomic groups
tags:
 - re
 - canonical
 - python-stdlib
 - fastapi
 - pydantic
 - security
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "45–60 minutes"
prerequisites:
 - "[[22-re/01-compile-and-match]]"
 - "[[22-re/02-search-findall-finditer]]"
 - "[[22-re/03-sub-and-named-groups]]"
 - "[[09-enum/05-Enum-in-APIs]]"
related_lessons:
 - "[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]"
first_taught_in: "22-re/04-re-in-validation"
---

# Lesson 04: re in validation — Pydantic, ReDoS, and the anti-patterns

*How `boardly`'s FastAPI routes use `Field(pattern=r"^[a-z0-9-]+$")` for declarative slug validation, how a `field_validator` with `re.fullmatch` normalises *and* validates in one pass, the "never parse HTML or email with regex" rule (use `html.parser` and `pydantic.EmailStr`), and the `(a+)+` ReDoS trap that took down Cloudflare in 2019.*

**You're at the very beginning of Section 22 — four lessons in. This is the canonical validation lesson.**

You have written `slug: str = Field(pattern=r"^[a-z0-9-]+$")` in a Pydantic model and seen the 422 come back, and seen it pass when the client sends `"boardly-2026"`. You have written a `field_validator` with `re.fullmatch` to lowercase an id and validate it in the same function. You have not seen what the regex engine does when an attacker submits `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaX"` to a pattern with nested quantifiers. This lesson ties the `re` API surface (lessons 01–03) to the FastAPI/Pydantic boundary, names the two anti-patterns (HTML parsing, email parsing), and walks the catastrophic-backtracking trap that turns a regex into a denial-of-service weapon. Take your time. Type every example. **This is how you learn.**

#re #canonical #fastapi #security

## Learning Objectives

By the end of this lesson you will be able to:

1. **Pick between `Field(pattern=...)` and `field_validator` with `re.fullmatch`** — explain when the declarative form wins (OpenAPI `pattern` keyword, no transformation), when the explicit form wins (normalise-and-validate, conditional logic, named-group extraction).
2. **State the HTML anti-pattern** — explain why parsing HTML with regex is the wrong tool (HTML is context-free, regex is regular) and what to use instead (`html.parser` stdlib, `lxml`, `BeautifulSoup`).
3. **State the email anti-pattern** — explain why RFC 5322 email addresses cannot be validated by a single regex (the grammar is recursive, comments are allowed) and what to use instead (`pydantic.EmailStr`, which delegates to the `email-validator` package).
4. **Spot and defuse ReDoS** — recognise the catastrophic-backtracking family (`(a+)+`, `(a|a)*`, nested quantifiers that overlap), and apply the four defences: remove the nesting, use atomic groups `(?>...)` (Python 3.11+), use possessive quantifiers `*+` / `++` / `?+` (Python 3.11+), and the `signal`-based timeout for last-resort protection.
5. **Pick the right `re.ASCII` / `re.LOCALE` flag** — explain that `re.ASCII` makes `\w` ASCII-only (right for slugs, ticket ids, ISO dates) and that `re.LOCALE` is almost never what you want (it is locale-dependent and the docs warn against it).

## Prerequisites

Before starting, you need:

- **Lessons 01–03 of this section** — [[22-re/01-compile-and-match]], [[22-re/02-search-findall-finditer]], [[22-re/03-sub-and-named-groups]]. This lesson assumes the `Pattern` object, the `Match` accessors, `findall` / `finditer`, `sub`, and named groups are second nature.
- **Enum in APIs** — [[09-enum/05-Enum-in-APIs]]. `StrEnum` and `re` are the two standard-library ways to constrain a string field in an API: `Enum` for "one of these literal values", `re` for "matches this pattern". Lesson 05 of the enum section walks the FastAPI integration; this lesson picks up where it leaves off.
- **Pydantic `BaseModel`** — [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]. The `Field(...)` constructor and `field_validator` decorator are Pydantic's field-validation API; that lesson compares the dataclass / Pydantic / TypedDict options.
- **About 45–60 minutes of focused time.**

**The most common gap: assuming `Field(pattern=...)` is enough for email validation.**

It is not. The RFC 5322 email grammar is recursive (comments in parentheses, quoted-pair backslash escapes, nested `@` after a `<>` route, etc.) and cannot be matched by a regular expression. A `Field(pattern=r"^[^@]+@[^@]+\.[a-z]{2,}$")` accepts obvious non-emails (`"a@b.cc"` looks fine but the domain may not resolve, the local-part may contain illegal characters, the TLD may not exist). The correct tool is `pydantic.EmailStr`, which delegates to the `email-validator` package, which parses the address with a real grammar and (optionally) checks the domain's MX records. The regex form is the anti-pattern that lets `"a@b.cc"` through and rejects `"alice+tag@example.name"` because the regex author forgot that `+` is a legal local-part character.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/api/users_route.py — the bad old days
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[a-z]{2,}$")
    html_bio: str = Field(pattern=r"^<p>.*</p>$")     # naive HTML check

@router.post("/users")
def create_user(payload: UserCreate):
    ...
```

Two bugs in two fields:

1. **The email pattern rejects legal addresses and accepts illegal ones.** `"alice+tag@example.name"` is rejected because `+` is not in the `[^@]` character class — but `+` is a legal local-part character used by Gmail and many mail systems for sub-addressing. Conversely, `"a@b.cc"` is accepted because the pattern's only check is "has an `@`, then a dot, then a 2-letter TLD" — it does not check the local-part length, the domain validity, or the TLD's actual existence. A typo (`"alice@exmaple.com"`) sails through.
2. **The HTML pattern is a security hole.** `^<p>.*</p>$` accepts `"<p>hello</p>"` and rejects everything else — but it also accepts `"<p><script>alert(1)</script></p>"` because `.*` matches the script tag. The pattern does not sanitise; it just confirms a wrapping tag exists. The student who writes this thinks they have "validated the HTML"; they have validated the *envelope*, not the *contents*.

The fix is the lesson: stop trying to parse email with regex (use `pydantic.EmailStr`), stop trying to parse HTML with regex (use `html.parser` or a real parser), and use regex only for the things it is good at — *format* validation (slugs, UUIDs, ticket ids, ISO dates) where the grammar is genuinely regular.

## The Code

```python
# boardly/api/re_in_validation.py
"""re in Pydantic / FastAPI validation: Field(pattern=...), field_validator,
   the HTML/email anti-pattern, and the ReDoS trap."""
import re
import signal
import time
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError


# 1. The declarative form: Field(pattern=...)
class SlugModel(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", min_length=3, max_length=64)


# 2. The explicit form: field_validator + re.fullmatch, with transform
class TicketModel(BaseModel):
    ticket_id: str

    @field_validator("ticket_id")
    @classmethod
    def normalise_and_validate(cls, v: str) -> str:
        # Normalise: uppercase -> lowercase, then validate.
        # The pattern itself is lowercase, so the normalisation happens FIRST.
        v = v.lower()
        if re.fullmatch(r"tkt-[a-f0-9]{8,12}", v, re.ASCII) is None:
            raise ValueError("ticket_id must match TKT-[a-f0-9]{8,12}")
        return v


# 3. The anti-pattern: do NOT parse HTML or email with regex
#    - HTML -> use html.parser (stdlib) or a real parser (lxml, BeautifulSoup)
#    - Email -> use pydantic.EmailStr (which uses email-validator)

class ContactModel(BaseModel):
    email: EmailStr                       # validated by email-validator, not regex


# 4. The ReDoS defence: atomic group (Python 3.11+)
HEX_GROUP_RE = re.compile(r"(?>[a-f0-9]{8,12})")     # atomic, no backtracking


def safe_match(pattern: str, string: str, seconds: int = 2) -> re.Match | None:
    """Signal-based timeout for regex — Unix only, breaks on Windows."""
    def _handler(signum, frame):
        raise TimeoutError(f"regex timed out after {seconds}s")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        return re.match(pattern, string)
    except TimeoutError:
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


if __name__ == "__main__":
    print("Field(pattern):")
    try:
        m = SlugModel(slug="boardly-2026")
        print("  good slug:", m.slug)
    except ValidationError as e:
        print("  good slug failed:", e)
    try:
        m = SlugModel(slug="BAD Slug!")
    except ValidationError as e:
        print("  bad slug:", e.errors()[0]["msg"])

    print()
    print("field_validator (normalise + validate):")
    try:
        m = TicketModel(ticket_id="TKT-ABCD1234")
        print("  uppercase input ->", m.ticket_id)
    except ValidationError as e:
        print("  failed:", e)
    try:
        m = TicketModel(ticket_id="BAD-1234")
    except ValidationError as e:
        print("  bad ticket_id:", e.errors()[0]["msg"])

    print()
    print("EmailStr (uses email-validator):")
    try:
        m = ContactModel(email="alice@example.com")
        print("  good email:", m.email)
    except ValidationError as e:
        print("  good email failed:", e)
    try:
        m = ContactModel(email="not-an-email")
    except ValidationError as e:
        print("  bad email rejected:", e.errors()[0]["msg"][:80])

    print()
    print("ReDoS defences on a^25+X (and a^30+X for the timeout):")
    start = time.perf_counter()
    re.match(r"(a+)+$", "a" * 25 + "X")
    print(f"  (a+)+$ (catastrophic): {time.perf_counter() - start:.3f}s")
    start = time.perf_counter()
    re.match(r"a+$", "a" * 25 + "X")
    print(f"  a+$ (no nesting): {time.perf_counter() - start:.6f}s")
    start = time.perf_counter()
    re.match(r"(?>a+)+$", "a" * 25 + "X")
    print(f"  (?>a+)+$ (atomic, 3.11+): {time.perf_counter() - start:.6f}s")
    start = time.perf_counter()
    re.match(r"(a++)+$", "a" * 25 + "X")
    print(f"  (a++)+$ (possessive, 3.11+): {time.perf_counter() - start:.6f}s")
    start = time.perf_counter()
    result = safe_match(r"(a+)+$", "a" * 30 + "X", seconds=1)
    print(f"  (a+)+$ with 1s timeout (a^30+X): {time.perf_counter() - start:.3f}s, result={result}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–16: Imports and the declarative `Field(pattern=...)`

```python
import re
import signal
import time
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError


# 1. The declarative form: Field(pattern=...)
class SlugModel(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", min_length=3, max_length=64)
```

`SlugModel.slug` is annotated `str` and given a `Field(...)` with three constraints: `pattern` (a regex the value must match), `min_length` (the value must be at least 3 characters), `max_length` (the value must be at most 64 characters). Pydantic applies the constraints at construction time — `SlugModel(slug="BAD Slug!")` raises `ValidationError` with the message `"String should match pattern '^[a-z0-9-]+$'"`. The error message is generated by Pydantic's standard error formatter; you do not have to write it.

The `pattern` argument is the most interesting one. It is a *regex* — Pydantic stores it as part of the field's metadata and uses it in two places: (a) at validation time, it calls `re.fullmatch(pattern, value)` (yes — `fullmatch`, not `match` — Pydantic gets this right) and rejects if the result is `None`; (b) at schema-generation time, it emits the regex into the OpenAPI schema as a `"pattern"` keyword. The OpenAPI `pattern` keyword is JSON Schema's regex constraint; clients that consume your OpenAPI document can validate their input *before* sending it to you, because the pattern is in the schema.

The `Annotated` import is unused in this demo but is the type-level alternative to `Field(...)` — `slug: Annotated[str, Field(pattern=r"^[a-z0-9-]+$")]` is the modern Pydantic form. The two are equivalent; `Annotated` keeps the type annotation as a `str` and moves the constraint to the metadata, which is what `Annotated` is for. The lesson uses `Field(...)` for brevity; the `Annotated` form is the production idiom.

**Why does Pydantic use `re.fullmatch` instead of `re.match`?** Because "the field value must match this pattern" means "the whole value must match", not "the value must start with a prefix that matches". `Field(pattern=r"\d+")` on `slug="123abc"` should reject, not accept — the whole value must be digits. Pydantic's choice of `fullmatch` is the right call; it removes the `match`-vs-`fullmatch` trap from the declarative API. Lesson 01's rule ("always use `fullmatch` for validation") is the same rule Pydantic follows internally.

### Lines 18–29: `field_validator` with normalise-and-validate

```python
# 2. The explicit form: field_validator + re.fullmatch, with transform
class TicketModel(BaseModel):
    ticket_id: str

    @field_validator("ticket_id")
    @classmethod
    def normalise_and_validate(cls, v: str) -> str:
        # Normalise: uppercase -> lowercase, then validate.
        # The pattern itself is lowercase, so the normalisation happens FIRST.
        v = v.lower()
        if re.fullmatch(r"tkt-[a-f0-9]{8,12}", v, re.ASCII) is None:
            raise ValueError("ticket_id must match TKT-[a-f0-9]{8,12}")
        return v
```

`field_validator("ticket_id")` is the Pydantic decorator that registers a class method as a per-field validator. The method receives the raw value `v` (the value the user submitted) and returns the value Pydantic should store. Returning a *different* value than the input is the *normalise* half: `v = v.lower()` lowercases the input, and the function returns the lowercased form. The stored value is `"tkt-abcd1234"` even when the user submitted `"TKT-ABCD1234"`.

The `re.fullmatch(r"tkt-[a-f0-9]{8,12}", v, re.ASCII)` is the *validate* half. The pattern is lowercase `tkt-` because the input has already been lowercased; if the pattern were uppercase, the lowercased input would never match. The `re.ASCII` flag forces the `[a-f0-9]` class to be ASCII-only — which is the rule for any wire-format identifier pattern, as lesson 01 covered. The error message is the string passed to `ValueError`; Pydantic catches the `ValueError`, formats it into the validation error list, and returns HTTP 422 with the message in the body.

`field_validator` and `Field(pattern=...)` are not interchangeable. `Field(pattern=...)` is declarative and produces an OpenAPI `pattern` keyword — clients see the constraint in the schema. `field_validator` is procedural and produces nothing in the schema (the schema generator does not introspect validator contents) — clients see only `{"type": "string"}` for `ticket_id`, and the regex constraint is hidden. The trade-off: declarative form for things you want the schema to expose (slug format, ISO date format); procedural form for things you want to keep internal (normalisation, conditional logic, named-group extraction). Lesson 03's `normalise_ticket_ids` is the callable-repl version of this same normalise-and-validate idea; `field_validator` is the Pydantic-bound version.

**Why normalise *before* validate, not after?** Because the validator sees the raw input — if the user submits `"TKT-ABCD1234"`, that is what `v` is. Normalising after validation would require the pattern to accept both cases (`[A-Fa-f0-9]`), and the stored value would be the original mixed case. Normalising first means the pattern only has to handle one case (`[a-f0-9]`), and the stored value is canonical. The trade-off: the error message has to refer to the canonical form ("must match TKT-...") even though the pattern is lowercase — the user sees the canonical form, not the lowercased form. That is a documentation effort, not a code effort.

### Lines 31–35: The HTML/email anti-pattern — use the right tools

```python
# 3. The anti-pattern: do NOT parse HTML or email with regex
#    - HTML -> use html.parser (stdlib) or a real parser (lxml, BeautifulSoup)
#    - Email -> use pydantic.EmailStr (which uses email-validator)

class ContactModel(BaseModel):
    email: EmailStr                       # validated by email-validator, not regex
```

`ContactModel.email` is annotated `EmailStr` — Pydantic's email type. `EmailStr` is not a regex under the hood; it delegates to the `email-validator` package (`pip install email-validator`), which parses the address with a real RFC 5322 grammar, optionally checks the domain's MX records, and rejects invalid addresses with a meaningful error. The validation is more thorough than any regex can be, and the error messages are written for humans ("The domain name `exmaple.com` does not exist").

The reason regex cannot validate email is that RFC 5322 is *recursive*. Comments in parentheses can appear in arbitrary positions. Quoted strings can contain otherwise-illegal characters. The `@` symbol can appear inside a quoted local-part. Sub-domains can be IPv6 literals (`user@[IPv6:2001:db8::1]`). The grammar is context-free (you need a stack to parse it), and regex is regular (no stack). The best-known "RFC 5322 regex" is several kilobytes long, takes a long time to compile, and still does not handle every edge case. The right tool is a parser; `email-validator` is that parser, and `EmailStr` is the Pydantic binding.

The same rule applies to HTML. `^<p>.*</p>$` looks like it validates "the value is a paragraph", but it accepts `<p><script>alert(1)</script></p>` because `.*` matches the script tag. The pattern checks the *envelope*, not the *contents*. The right tool is `html.parser` (stdlib) or `lxml` or `BeautifulSoup` — they parse the HTML into a DOM tree, where you can walk the tree and reject disallowed tags. Regex on HTML is the wrong layer of abstraction; the lesson's commitment is "never parse HTML or email with regex; use a parser".

**Danger — regex on HTML is a recurring security incident.**

The classic example is the 2019 Cloudflare outage, where a regex with catastrophic backtracking was triggered by a single character in a customer's HTTP request, and the worker threads tied up the entire CPU pool. The regex was meant to parse HTTP headers, not HTML, but the same pattern applies: a regex that *looks* like it validates structure is a regex that accepts structure it does not understand. The fix is to use a parser for any context-free grammar (HTML, XML, JSON, email, HTTP headers) and reserve regex for genuinely regular languages (slugs, UUIDs, ticket ids, ISO dates).

### Lines 37–39: The atomic-group defence (Python 3.11+)

```python
# 4. The ReDoS defence: atomic group (Python 3.11+)
HEX_GROUP_RE = re.compile(r"(?>[a-f0-9]{8,12})")     # atomic, no backtracking
```

`(?>...)` is an *atomic group*. It is a non-capturing group that, once it has matched, refuses to backtrack — the engine commits to the match and cannot give characters back. The atomic form was added to Python's `re` module in 3.11; before that, the stdlib did not support atomic groups, and the only way to get them was the third-party `regex` module. On 3.11+, `(?>...)` is part of the stdlib's `re` syntax and works in any `re.compile` call.

The point of an atomic group is to prevent catastrophic backtracking. A pattern like `(a+)+` has two nested quantifiers (`+` inside `+`), and on a near-miss input like `"aaaaaaX"`, the engine tries every partition of the `a`s between the two quantifiers before giving up — exponential work. The atomic group `(?>a+)+` makes the inner `a+` non-backtracking: once the inner `+` has consumed a run of `a`s, the engine commits to that run and the outer `+` cannot rearrange it. The result is linear-time matching on the same input that would have taken exponential time without the atomic group.

The closely-related defence is the *possessive quantifier* — `*+`, `++`, `?+`. `(a++)+$` is the possessive form of `(a+)+$`, where the inner `++` is a possessive quantifier (refuses to give characters back) equivalent to `(?>a+)`. Possessive quantifiers were also added in Python 3.11. They are syntactic sugar for atomic groups around the same subpattern; the two forms are equivalent in result. The lesson uses both forms in the demo to show they both defuse the trap.

**Why were atomic groups added in 3.11 and not earlier?** Because the stdlib `re` engine's backtracking algorithm did not have a "commit" operation before 3.11 — adding it required a non-trivial engine change. The third-party `regex` module has had atomic groups (and other advanced features like variable-length lookbehind) for years, but the stdlib was conservative. Python 3.11 added them as part of a series of `re` improvements (atomic groups, possessive quantifiers, and the V1 partial engine); the V1 full engine is still in `regex`-only. If you need features beyond what 3.11+ supports (atomic groups, possessive quantifiers, but not variable-length lookbehind or atomic backrefs), use the `regex` module.

### Lines 41–54: The `signal`-based timeout — the last-resort defence

```python
def safe_match(pattern: str, string: str, seconds: int = 2) -> re.Match | None:
    """Signal-based timeout for regex — Unix only, breaks on Windows."""
    def _handler(signum, frame):
        raise TimeoutError(f"regex timed out after {seconds}s")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        return re.match(pattern, string)
    except TimeoutError:
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
```

`safe_match` is the *last-resort* defence against ReDoS: wrap the regex call in a `signal.SIGALRM` timer. `signal.alarm(seconds)` schedules a `SIGALRM` to be delivered after `seconds` seconds; when the signal arrives, Python interrupts the running C code (the regex engine), calls the registered handler (`_handler`), which raises `TimeoutError`. The `try`/`except TimeoutError`/`finally` pattern catches the timeout and returns `None`, and the `finally` block cancels the alarm and restores the previous handler.

The trick is that `signal.SIGALRM` interrupts the C-level regex call. Python's `re` module does not poll for signals — the engine runs in a tight C loop and does not yield to the interpreter. `SIGALRM` is delivered by the OS to the process, the C-level signal handler runs, and the regex call is interrupted with a `TimeoutError`. This works for any long-running C call, not just regex.

**Warning — `signal.alarm` is Unix-only.**

`SIGALRM` does not exist on Windows; `signal.alarm` raises `AttributeError` there. For Windows, you need a thread-based timeout (run the regex in a worker thread, set a timeout on the join, abandon the thread if it overruns). The thread approach is uglier because the abandoned thread keeps running until the process exits — the regex engine does not have a cancellation token. For a cross-platform timeout, the cleanest answer is to run the regex in a subprocess and `kill` the subprocess on timeout — but that is heavyweight. The honest recommendation is: prefer atomic groups and possessive quantifiers (which prevent ReDoS at the pattern level), use `signal.alarm` as a backstop on Unix, and do not run user-supplied regex on Windows without a process boundary.

**Why does `safe_match` return `None` on timeout instead of raising?** Because the caller cannot distinguish "the pattern did not match" from "the pattern timed out" — both are "this string does not validate against this pattern". If the caller wants to log timeouts separately (which is good incident-response practice — a timeout is an attack signal), change the return type to `re.Match | None | Literal["timeout"]` or raise a custom exception that the caller can branch on. The demo returns `None` for brevity; production code should distinguish.

### Lines 56–86: The demo's main block — exercising every path

```python
if __name__ == "__main__":
    print("Field(pattern):")
    try:
        m = SlugModel(slug="boardly-2026")
        print("  good slug:", m.slug)
    except ValidationError as e:
        print("  good slug failed:", e)
    try:
        m = SlugModel(slug="BAD Slug!")
    except ValidationError as e:
        print("  bad slug:", e.errors()[0]["msg"])

    print()
    print("field_validator (normalise + validate):")
    try:
        m = TicketModel(ticket_id="TKT-ABCD1234")
        print("  uppercase input ->", m.ticket_id)
    except ValidationError as e:
        print("  failed:", e)
    try:
        m = TicketModel(ticket_id="BAD-1234")
    except ValidationError as e:
        print("  bad ticket_id:", e.errors()[0]["msg"])
    ...
```

The `if __name__ == "__main__":` guard runs the four test paths: a good slug, a bad slug, a normalised-good ticket_id, a bad ticket_id. Each `try`/`except ValidationError` swallows the exception and prints the error message, so the demo runs to completion instead of crashing on the first failure. The `e.errors()` method returns a list of error dicts; `[0]["msg"]` extracts the first error's human-readable message. In production, FastAPI's exception handler converts `ValidationError` to an HTTP 422 response automatically; you do not have to catch the exception in the route function.

The ReDoS demo at the end of the `__main__` block runs the catastrophic pattern and each defence, timing each call. The `time.perf_counter()` calls bracket the `re.match` calls; the difference is the wall-clock time the regex took. The output shows the catastrophic pattern taking ~2 seconds on `"a" * 25 + "X"` and the defences taking microseconds — a 4–5 orders-of-magnitude difference.

## Execution Trace

```bash
$ uv run python boardly/api/re_in_validation.py
Field(pattern):
  good slug: boardly-2026
  bad slug: String should match pattern '^[a-z0-9-]+$'

field_validator (normalise + validate):
  uppercase input -> tkt-abcd1234
  bad ticket_id: Value error, ticket_id must match TKT-[a-f0-9]{8,12}

EmailStr (uses email-validator):
  good email: alice@example.com
  bad email rejected: value is not a valid email address: An email address must have an @-sign.

ReDoS defences on a^25+X (and a^30+X for the timeout):
  (a+)+$ (catastrophic): 2.102s
  a+$ (no nesting): 0.000163s
  (?>a+)+$ (atomic, 3.11+): 0.000051s
  (a++)+$ (possessive, 3.11+): 0.000039s
  (a+)+$ with 1s timeout (a^30+X): 1.000s, result=None
```

## Common Mistakes

### Mistake 1: Using `Field(pattern=...)` for email

```python
class ContactModel(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[a-z]{2,}$")    # anti-pattern
```

**Symptom:** The validator rejects legal emails (`"alice+tag@example.name"`) and accepts illegal ones (`"a@b.cc"`, `"alice@exmaple.com"`). The error messages are unhelpful ("String should match pattern '...'") and do not tell the user what was wrong with their address.
**Why:** RFC 5322 email addresses are recursive (comments, quoted pairs, IPv6 domain literals, sub-addressing) and cannot be matched by a regular expression. The pattern's author simplified the grammar to a subset, which excludes legal addresses and includes illegal ones.
**Fix:** Use `pydantic.EmailStr`, which delegates to the `email-validator` package:

```python
from pydantic import EmailStr

class ContactModel(BaseModel):
    email: EmailStr                       # validated by email-validator, not regex
```

`EmailStr` parses the address with a real RFC 5322 grammar, optionally checks the domain's MX records, and rejects invalid addresses with a meaningful message ("The domain name `exmaple.com` does not exist"). It requires `pip install email-validator`; FastAPI does not ship it by default.

### Mistake 2: `re.match` instead of `re.fullmatch` in a `field_validator`

```python
@field_validator("slug")
@classmethod
def validate_slug(cls, v: str) -> str:
    if re.match(r"[a-z0-9-]+", v):           # match, not fullmatch
        return v
    raise ValueError("bad slug")
```

**Symptom:** The validator accepts `"boardly-2026<script>"` because `re.match` only anchors at the start and the trailing `<script>` is silently ignored. The stored value carries the script payload.
**Why:** `re.match` anchors only at the start. The pattern matches the prefix `"boardly-2026"`, the rest of the string is ignored, and `match` returns a `Match`. The validator's `if re.match(...): return v` returns the unsanitised value.
**Fix:** Use `re.fullmatch` (3.4+):

```python
@field_validator("slug")
@classmethod
def validate_slug(cls, v: str) -> str:
    if re.fullmatch(r"[a-z0-9-]+", v):       # fullmatch — whole string
        return v
    raise ValueError("bad slug")
```

Or, prefer `Field(pattern=...)` for declarative validation — Pydantic uses `fullmatch` internally, so the trap cannot land.

### Mistake 3: Nested quantifiers cause catastrophic backtracking

```python
EMAIL_RE = re.compile(r"^([a-zA-Z0-9._+]+)+@([a-zA-Z0-9.-]+)+\.([a-zA-Z]+)+$")
EMAIL_RE.fullmatch("a" * 30 + "!")          # ~60 seconds — ReDoS
```

**Symptom:** A single user-supplied string hangs the worker thread for a minute, blocking other requests. In production, an attacker can repeat the input and tie up every worker, causing a denial-of-service.
**Why:** The pattern has nested quantifiers (`([a-zA-Z0-9._+]+)+` — the inner `+` is wrapped in another `+`) that overlap (the inner `+` and outer `+` can both consume the same character). On a near-miss input (the `!` at the end cannot match), the engine tries every partition of the input between the two quantifiers before giving up — exponential work.
**Fix:** Apply one of four defences:
1. *Remove the nesting*: `^([a-zA-Z0-9._+]+)@([a-zA-Z0-9.-]+)\.([a-zA-Z]+)$` — one `+` per group, no overlap.
2. *Atomic group (3.11+)*: `^(?>[a-zA-Z0-9._+]+)@(?>[a-zA-Z0-9.-]+)\.(?>[a-zA-Z]+)$`.
3. *Possessive quantifier (3.11+)*: `^[a-zA-Z0-9._+]++@[a-zA-Z0-9.-]++\.[a-zA-Z]++$`.
4. *Signal-based timeout*: wrap the `re.match` call in a `signal.alarm` (Unix only) or subprocess boundary.

Or use the third-party `regex` module's V1 engine, which has more aggressive backtracking elimination. The stdlib `re` engine is the historical NFA backtracker; the `regex` module's V1 is the modernised engine. If your regex runs on attacker-controlled input, prefer atomic groups or `regex.V1`.

### Mistake 4: `re.LOCALE` on a slug

```python
SLUG_RE = re.compile(r"^[\w-]+$", re.LOCALE)      # locale-dependent!
```

**Symptom:** The slug validator accepts or rejects characters differently depending on the system locale (`LC_CTYPE`). The same input is valid on one server and invalid on another, with no change in the code.
**Why:** `re.LOCALE` makes `\w` match the locale's "word" characters — which depends on the runtime `LC_CTYPE` environment variable. A server in `C` locale treats `\w` as `[a-zA-Z0-9_]`; a server in `en_US.UTF-8` treats it as the Unicode word set; a server in `de_DE` may treat `\w` as including accented characters. The result is non-deterministic across deployments.
**Fix:** Use `re.ASCII` for the explicit "ASCII only" behaviour:

```python
SLUG_RE = re.compile(r"^[\w-]+$", re.ASCII)      # deterministic, ASCII only
```

Or spell the character class explicitly: `r"^[a-zA-Z0-9_-]+$"`. Both are deterministic across locales and deployments. The `re` documentation explicitly warns: "We strongly recommend that you use the `re.ASCII` flag rather than `re.LOCALE`".

## Engineering Trade-Offs

**Decision:** `boardly` uses `Field(pattern=r"^...$")` for declarative slug/UUID/ISO-date validation (the OpenAPI `pattern` keyword is a feature for clients), `field_validator` with `re.fullmatch` for normalise-and-validate cases (ticket-id lowercasing), `pydantic.EmailStr` for email, `html.parser` for any HTML the user submits, and atomic groups `(?>...)` (Python 3.11+) on every pattern that runs on attacker-controlled input.
**Both sides:** The alternative is `field_validator` for everything (more procedural, no OpenAPI pattern keyword, but uniform) or `Field(pattern=...)` for everything (declarative, schema-exposed, but no per-match transformation). The trade-off: declarative wins when the constraint is purely a pattern and clients benefit from seeing it in the schema; procedural wins when the constraint needs transformation or conditional logic. `boardly` splits the two based on whether the field's validation is "does it match this format" (declarative) or "transform and check" (procedural). For email and HTML, the right tools are not regex at all — `EmailStr` and `html.parser`.
**Commitment:** `boardly`'s `SlugModel.slug` uses `Field(pattern=...)` (declarative, schema-exposed). `TicketModel.ticket_id` uses `field_validator` with `re.fullmatch` (normalise-and-validate). `ContactModel.email` uses `EmailStr` (no regex). `BioModel.html_bio` uses a custom validator that calls `html.parser` and walks the DOM tree (no regex). ReDoS defences: every pattern in `boardly/validation/` that runs on request bodies uses atomic groups or possessive quantifiers where the pattern has nested quantifiers, and a `signal.alarm` backstop is wired into the request middleware for last-resort protection.

## Exercises

1. **Exercise 1 — Switch a `Field(pattern=...)` to `Annotated` form.** Convert `SlugModel.slug` from `slug: str = Field(pattern=...)` to `slug: Annotated[str, Field(pattern=...)]`. Confirm both forms produce the same OpenAPI schema and reject the same inputs. `Verify: uv run python -c "from boardly.api.re_in_validation import SlugModel; m = SlugModel(slug='boardly'); assert m.slug == 'boardly'"`
2. **Exercise 2 — Add a UUID validator with `Field(pattern=...)`.** Add a `uuid` field to `SlugModel` (or a new model) with `Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.ASCII)`. Confirm a valid UUID is accepted and `"not-a-uuid"` is rejected. `Verify: uv run python -c "from boardly.api.re_in_validation import UuidModel; import pytest; m = UuidModel(uuid='deadbeef-dead-dead-dead-deadbeefdead'); assert m.uuid.startswith('dead')"`
3. **Exercise 3 — Replace a regex email with `EmailStr`.** Find a `Field(pattern=r"^[^@]+@[^@]+$")` somewhere in a codebase (or write one in a scratch file) and convert it to `EmailStr`. Confirm the new form accepts `"alice+tag@example.name"` and rejects `"not-an-email"` with a meaningful message. `Verify: uv run python -c "from boardly.api.re_in_validation import ContactModel; m = ContactModel(email='alice+tag@example.name'); assert m.email == 'alice+tag@example.name'"`
4. **Exercise 4 — Defuse a ReDoS pattern.** Take the catastrophic pattern `(a+)+$` and apply each of the four defences from the lesson (remove nesting, atomic group, possessive quantifier, signal timeout). Time each on `a^25+X` and confirm all four finish in under 1ms except the signal-timeout which is bounded by the timeout. `Verify: uv run python -c "import re, time; start = time.perf_counter(); re.match(r'(?>a+)+\$', 'a' * 25 + 'X'); assert time.perf_counter() - start < 0.01"`
5. **Exercise 5 — Parse an HTML bio with `html.parser`.** Write a function `validate_bio(html: str) -> str` that uses `html.parser.HTMLParser` to walk the DOM tree, rejects if any `<script>` or `<iframe>` tag appears, and returns the input if it is clean. Confirm `<p>hello</p>` is accepted and `<p><script>alert(1)</script></p>` is rejected. `Verify: uv run python -c "from boardly.api.re_in_validation import validate_bio; assert validate_bio('<p>hello</p>') == '<p>hello</p>'; import pytest; pytest.raises(ValueError, validate_bio, '<p><script>x</script></p>')"`

## Verification

```bash
$ uv run python boardly/api/re_in_validation.py
Field(pattern):
  good slug: boardly-2026
  bad slug: String should match pattern '^[a-z0-9-]+$'

field_validator (normalise + validate):
  uppercase input -> tkt-abcd1234
  bad ticket_id: Value error, ticket_id must match TKT-[a-f0-9]{8,12}

EmailStr (uses email-validator):
  good email: alice@example.com
  bad email rejected: value is not a valid email address: An email address must have an @-sign.

ReDoS defences on a^25+X (and a^30+X for the timeout):
  (a+)+$ (catastrophic): 2.102s
  a+$ (no nesting): 0.000163s
  (?>a+)+$ (atomic, 3.11+): 0.000051s
  (a++)+$ (possessive, 3.11+): 0.000039s
  (a+)+$ with 1s timeout (a^30+X): 1.000s, result=None
```

## Previously Learned Here

- [[22-re/01-compile-and-match]] — the `Pattern` object, `match`/`fullmatch`, the `Match` accessors, the `re.ASCII` flag — the foundation this lesson builds on.
- [[22-re/02-search-findall-finditer]] — `findall`/`finditer`, the multi-match family — `Field(pattern=...)` uses `fullmatch` internally, but `field_validator`s sometimes need `findall`/`finditer` for multi-capture validation.
- [[22-re/03-sub-and-named-groups]] — `sub`, callable `repl`, named groups — the normalise-and-validate pattern in `field_validator` is the API-boundary version of lesson 03's `sub`-with-callable.
- [[09-enum/05-Enum-in-APIs]] — `StrEnum` and `re` are the two stdlib ways to constrain a string field in an API; that lesson covers the enum side, this lesson covers the regex side.
- [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — the dataclass / Pydantic / TypedDict comparison that frames where `Field(pattern=...)` and `field_validator` live.

## What's Next

You have reached the end of Section 22. The four lessons cover the `re` API surface (compile, match, fullmatch, search, findall, finditer, sub, subn, expand, named groups) and the use case (Pydantic validation, anti-patterns, ReDoS). The next step is the related topic in the standard library: [[25-Reference-Library/Engineering-Decision-Log]] collects the trade-offs you have learned across the section ("use `re.fullmatch` for validation, not `re.match`", "use `\g<name>` not `\1`", "use `EmailStr` not regex for email", "use atomic groups on attacker-controlled input"). The cross-link to [[09-enum/05-Enum-in-APIs]] ties the regex side of string validation to the enum side; together, the two sections cover the full surface of "constrain a string field in an API" in the standard library.

- **The decision log** — [[25-Reference-Library/Engineering-Decision-Log]] — the cross-cutting trade-offs from this section, indexed by topic.
- **The enum side** — [[09-enum/05-Enum-in-APIs]] — the alternative "one of these literal values" constraint, which complements the regex "matches this pattern" constraint.
- **The Pydantic field lesson** — [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — where `Field(pattern=...)` and `field_validator` fit in the broader model-validation toolkit.

## Sources

- **Python `re` module documentation** — https://docs.python.org/3/library/re.html — accessed 2026-10-23 — the source-of-truth reference for `re.fullmatch`, `re.ASCII`, `re.LOCALE`, atomic groups `(?>...)`, and possessive quantifiers `*+`/`++`/`?+` (Python 3.11+).
- **Python `re` "Atomic Groups and Possessive Quantifiers" reference** — https://docs.python.org/3/library/re.html#atomic-groups — accessed 2026-10-23 — the syntax and semantics of `(?>...)` and the possessive forms, added in 3.11 to prevent catastrophic backtracking.
- **Pydantic `Field` reference** — https://docs.pydantic.dev/2.12/concepts/fields/ — accessed 2026-10-23 — the `Field(pattern=...)` declarative validator and how Pydantic uses `re.fullmatch` internally.
- **Pydantic `EmailStr` reference** — https://docs.pydantic.dev/2.12/concepts/types/#emailstr — accessed 2026-10-23 — the email-validation type that delegates to the `email-validator` package; the right alternative to a regex email pattern.
- **`email-validator` PyPI page** — https://pypi.org/project/email-validator/ — accessed 2026-10-23 — the package `EmailStr` uses; the RFC 5322 grammar parser that replaces regex email validation.
- **OWASP ReDoS attack description** — https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS — accessed 2026-10-23 — the canonical description of the catastrophic-backtracking attack, including the `(a+)+` family of evil patterns.
- **Cloudflare 2019 outage post-mortem** — https://blog.cloudflare.com/cloudflare-incident-on-july-2-2019/ — accessed 2026-10-23 — a production incident caused by a regex with catastrophic backtracking; the real-world cost of the ReDoS trap.

## What We Learned

- You can now pick between `Field(pattern=r"^...$")` (declarative, schema-exposed) and `field_validator` with `re.fullmatch` (procedural, normalise-and-validate) based on whether the constraint is a pure format check or a transformation.
- You can state the HTML anti-pattern ("never parse HTML with regex — use `html.parser` or `lxml`") and the email anti-pattern ("never validate email with regex — use `pydantic.EmailStr`"), and explain *why* (HTML and email are context-free grammars, regex is regular).
- You can recognise the catastrophic-backtracking family of patterns (`(a+)+`, `(a|a)*`, nested quantifiers that overlap) and apply the four defences: remove the nesting, use atomic groups `(?>...)` (Python 3.11+), use possessive quantifiers `*+`/`++`/`?+` (Python 3.11+), and the `signal`-based timeout as a Unix-only backstop.
- You can pick `re.ASCII` (deterministic, ASCII-only `\w`/`\d`/`\s`, right for slugs and identifiers) over `re.LOCALE` (locale-dependent, the docs warn against it) for every wire-format pattern.
- You can name the rule the section depends on: regex is for *regular* languages (slugs, UUIDs, ticket ids, ISO dates); use a parser for context-free languages (HTML, email, JSON, HTTP headers).
