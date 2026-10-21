---
title: "re — Section Map of Content"
aliases:
 - re MOC
 - 22-re MOC
tags:
 - re
 - moc
 - foundation
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "2.5–4 hours across 4 lessons"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
---

# re — Section Map of Content

*The `compile`, `match`, `fullmatch`, `search`, `findall`, `finditer`, `sub`, `subn`, and named-group API — the regular-expression engine every FastAPI `Path` validation, every email-format check, every slug-pattern matcher, and every ticket-id parser leans on.*

**You're at the very beginning of Section 22.**

`re` is the standard library's regular-expression engine. A regex is a small domain-specific language for describing string patterns; the `re` module parses a pattern string into a finite-state machine, runs that machine against an input string, and either returns a `Match` object (success) or `None` (failure). The four operations on a compiled `Pattern` — `match` (anchored at the start), `fullmatch` (anchored at both ends), `search` (anywhere), and `sub` (replace) — are the foundation of every wire-format validator in `boardly`: slugs (`r"^[a-z0-9-]+$"`), ticket ids (`r"^TKT-[a-f0-9]{8,12}$"`), UUIDs (`r"^[0-9a-f]{8}-...$"`), and ISO dates (`r"^\d{4}-\d{2}-\d{2}$"`). When the pattern's grammar is genuinely regular — no nesting, no recursion, no comments — a regex is the right tool. When the grammar is context-free (HTML, email, JSON, HTTP headers), a regex is the wrong tool; the section's lesson 04 names the two anti-patterns and points you at the right parsers.

This section gives you the API surface (lessons 01–03: compile, match, fullmatch, search, findall, finditer, sub, subn, expand, named groups) and the use case (lesson 04: Pydantic `Field(pattern=...)`, `field_validator`, the HTML/email anti-patterns, and the catastrophic-backtracking ReDoS trap with its four defences — remove the nesting, atomic groups `(?>...)`, possessive quantifiers `*+`/`++`/`?+`, and the `signal`-based timeout). By the end you will know why every slug validator in a boardly API uses `pattern.fullmatch(value)` (not `re.match`), why every `re.sub` template uses `\g<name>` backrefs (not `\1`), and why every pattern that runs on attacker-controlled input uses atomic groups.

#re #moc #foundation

## Why this section exists

Every senior backend engineer writes a regex at least once a week. You write `re.match(r"^\d+$", year_string)` and it works, and you write `re.match(r"\d+", age_string)` and it accepts `"abc123"` because `match` is not anchored at both ends, and the bug ships to production. You write `re.sub(r"(\d+)", r"\1\2", text)` and the `\12` becomes an octal escape, silently corrupting your output. You write `Field(pattern=r"^[^@]+@[^@]+\.[a-z]{2,}$")` for an email field and it rejects `"alice+tag@example.name"` (legal) while accepting `"a@b.cc"` (almost certainly wrong). You write `re.compile(r"(a+)+$")` on a user-controlled field and a single malicious request hangs your worker for sixty seconds — and the attacker repeats the request and hangs every worker you have. The section walks all four bugs and the discipline that prevents each.

The discipline is two rules. *Use `re.fullmatch` for validation* (lesson 01) — the whole value must match, not just a prefix. *Use `\g<name>` for backrefs* (lesson 03) — the `<...>` delimiters make the group reference self-terminating, so a following digit literal cannot be parsed as an octal escape. *Use `pydantic.EmailStr` for email* (lesson 04) — RFC 5322 is recursive, regex is regular, the two do not match. *Use atomic groups on attacker-controlled input* (lesson 04) — `(?>...)` and `*+`/`++`/`?+` (Python 3.11+) make the inner match non-backtracking, which removes the catastrophic-backtracking surface entirely.

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[22-re/01-compile-and-match]] | `re.compile(r"...", re.ASCII)` returns a `re.Pattern` (3.7+, `re.Pattern[str]` is 3.9+) that you bind at module scope and reuse; `re.match` is anchored at the *start* of the string only; `re.fullmatch` (3.4+) is anchored at *both* ends; the `re.Match` object exposes `.group(0)` (whole match), `.group("name")` (named group), `.groups()`, `.groupdict()`, `.span()`, `.start()`, `.end()`, `.string`, `.re`; the `re.ASCII` flag makes `\w`/`\d`/`\s` ASCII-only (right for slugs and identifiers). |
| 02 | [[22-re/02-search-findall-finditer]] | `re.search` returns the *first* match anywhere (not anchored); `re.findall` returns `list[str]` for 0 or 1 group and `list[tuple[str, ...]]` for 2+ groups; `re.finditer` (3.7+) returns a lazy iterator of `Match` objects (memory-efficient for multi-MB logs); `re.Scanner` is the undocumented tokeniser class (use a real parser for production code); the difference between `findall` (text-only) and `finditer` (full `Match` with `.span()`). |
| 03 | [[22-re/03-sub-and-named-groups]] | `re.sub(pattern, repl, string, count=0, flags=0)` with `repl` a string (with `\1`/`\g<name>` backrefs) or a callable (called per `Match`, returns the replacement); `\g<name>` is the unambiguous form (because `\1` followed by a digit becomes an octal escape); `re.subn` returns `(new_string, num_substitutions)`; `(?P<name>...)` is Python's only named-group syntax (the .NET `(?<name>...)` form raises `re.error`); `Match.expand(template)` applies the same template syntax as `re.sub`'s string `repl`, on a single `Match`. |
| 04 | [[22-re/04-re-in-validation]] | `Field(pattern=r"^...$")` is the declarative Pydantic form (Pydantic uses `re.fullmatch` internally, and emits the `pattern` keyword into OpenAPI); `field_validator` with `re.fullmatch` is the procedural form (normalise-and-validate in one pass); the HTML anti-pattern (`html.parser`, not regex); the email anti-pattern (`pydantic.EmailStr`, not regex — RFC 5322 is recursive); the ReDoS catastrophic-backtracking trap (`(a+)+` family) and the four defences — remove the nesting, atomic groups `(?>...)` (3.11+), possessive quantifiers `*+`/`++`/`?+` (3.11+), and the `signal`-based timeout (Unix only). |

## Mindmap

```mermaid
mindmap
  root((re))
    Construction
      re.compile pattern flags
      re.Pattern 3.7+
      re.Pattern[str] 3.9+
      re.ASCII flag
      re.LOCALE flag avoided
    Single match
      re.match anchored start
      re.fullmatch 3.4+ both ends
      re.search first anywhere
      returns Match or None
    Multi match
      re.findall list[str] or list[tuple]
      re.finditer 3.7+ lazy iterator
      re.Scanner undocumented
      finditer yields Match
      findall yields text
    Match object
      group 0 / group N / group name
      groups tuple
      groupdict name to value
      span start end
      string input
      re pattern
      expand template
    Substitution
      re.sub pattern repl string
      repl string with backrefs
      repl callable per match
      re.subn returns count
      backrefs g name not 1
    Named groups
      (?P<name>...) Python only
      (?<name>...) .NET NOT supported
      group name access
      groupdict named captures
    Validation
      Field pattern declarative
      field_validator procedural
      re.fullmatch rule
      EmailStr not regex
      html.parser not regex
      atomic groups 3.11+
      possessive quantifiers 3.11+
      ReDoS catastrophic
      signal alarm timeout
    Cross-links
      09-enum 05-Enum-in-APIs
      06-dataclasses 07-dataclass-vs-pydantic-vs-typeddict
      01-typing 02-Annotated
      25-Reference-Library Engineering-Decision-Log
```

## Reading order

Read the lessons in numbered order. Lesson 01 is the canonical foundation — the compiled `Pattern`, `match` vs `fullmatch`, the `Match` accessors. Every later lesson assumes you have internalised "`fullmatch` for validation, `match` only when you want the prefix". Lesson 02 (search, findall, finditer) builds on lesson 01 — the multi-match operations return either text or `Match` objects depending on which API you call. Lesson 03 (sub and named groups) builds on lesson 02 — `sub` finds every match the same way `finditer` does, but with a replacement side-effect. Lesson 04 (re in validation) builds on all three — the Pydantic integration uses `fullmatch` internally, and the ReDoS defences are the application of the API-surface knowledge to a real security trap.

If you only have time for one lesson, read lesson 01. It is enough to stop shipping the `match`-vs-`fullmatch` bug and the `re.ASCII`-on-slug gap; the rest of the section is refinement.

If you have time for two, read 01 and 04 — you will know the validation discipline even if you skip the multi-match and substitution machinery (which you can pick up later when a streaming-log use case forces the question).

If you have time for three, read 01, 02, and 04 — you will have the validation discipline plus the streaming pattern, which is what most production code uses day-to-day.

## Concepts first-taught in this section

These concepts have their canonical lesson in `22-re/`:

- **`re.compile`, `re.Pattern`, `re.Match`, `re.match`, `re.fullmatch`** → [[22-re/01-compile-and-match]] — the canonical lesson for the compiled-`Pattern` form, the three single-match operations, the `Match` accessors, and the `re.ASCII` flag.
- **`re` in Pydantic / FastAPI validation; ReDoS defences** → [[22-re/04-re-in-validation]] — the canonical lesson for the API-boundary use case, the HTML/email anti-patterns, and the catastrophic-backtracking trap with its four defences.

## Prerequisites

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. Lesson 04 writes `re.Pattern[str]` and `re.Match[str]` annotations (Python 3.9+ subscripts); you need to read those as "a `Pattern` that operates on `str` inputs".
- **A typed model to validate** — [[06-dataclasses/01-dataclass-Basics]]. The boardly `Project` and `Ticket` dataclasses carry `slug: str` and `ticket_id: str` fields; the `@dataclass` decorator generates the surrounding machinery.
- **Pydantic `BaseModel`** — [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] is recommended before lesson 04, because `Field(pattern=...)` and `field_validator` are Pydantic's field-validation API and the lesson assumes familiarity with the decorator stack.
- **`Annotated` metadata** — [[01-typing/02-Annotated-and-Metadata]] is recommended before lesson 04, because `Annotated[str, Field(pattern=...)]` is the v2-idiomatic form for attaching a regex constraint to a type.
- **Enum in APIs** — [[09-enum/05-Enum-in-APIs]] is the natural cross-link; `StrEnum` and `re` are the two standard-library ways to constrain a string field in an API.

## What you will be able to do by the end

- Compile a pattern once at module scope with `re.compile(r"...", re.ASCII)` and explain why the bound methods on the `Pattern` object skip the module-internal cache lookup on every call.
- Distinguish `re.match` (anchored at the start) from `re.fullmatch` (3.4+, anchored at both ends) and predict which one rejects trailing junk.
- Read a `Match` object's `.group(0)`, `.group("name")`, `.groups()`, `.groupdict()`, `.span()`, `.start()`, `.end()`, `.string`, and `.re` accessors.
- Predict `re.findall`'s return type from the pattern's group count (zero groups → `list[str]` of full matches, one group → `list[str]` of group-1 captures, two+ groups → `list[tuple]`).
- Use `re.finditer` (3.7+) to stream `Match` objects lazily through a generator function, keeping the working set at one `Match` regardless of input size.
- Write `re.sub` with `\g<name>` backrefs (the unambiguous form) and callable `repl` for per-match logic, and explain why `\1` is risky (octal-escape ambiguity when followed by a digit).
- Use `(?P<name>...)` named groups and explain that Python does *not* support the .NET `(?<name>...)` form (which raises `re.error`).
- Pick between `Field(pattern=r"^...$")` (declarative, schema-exposed) and `field_validator` with `re.fullmatch` (procedural, normalise-and-validate) based on the field's constraint shape.
- State the HTML anti-pattern ("never parse HTML with regex — use `html.parser`") and the email anti-pattern ("never validate email with regex — use `pydantic.EmailStr`").
- Recognise the catastrophic-backtracking family (`(a+)+`, nested quantifiers that overlap) and apply the four defences — remove the nesting, atomic groups `(?>...)` (Python 3.11+), possessive quantifiers `*+`/`++`/`?+` (Python 3.11+), and the `signal`-based timeout (Unix only).

## What's next

When you finish this section, the natural next stops are [[25-Reference-Library/Engineering-Decision-Log]] (the cross-cutting trade-offs from this section, indexed by topic) and (later in the curriculum) the `string` module's `Template` class — the static-template form that complements `re.sub` for non-regex substitution. For the FastAPI arc, the most relevant cross-link is [[09-enum/05-Enum-in-APIs]] — `StrEnum` and `re` are the two standard-library ways to constrain a string field in an API, and the enum lesson walks the side that this section does not. Open [[22-re/01-compile-and-match]] to begin.

**Welcome to re. We'll see you at the end.**

## Sources

- **`re` — Regular expression operations** — https://docs.python.org/3/library/re.html — accessed 2026-10-23 — the canonical CPython reference for `re.compile`, `re.Pattern`, `re.Match`, the four match operations, `re.sub`/`re.subn`, named groups, and every flag (`re.ASCII`, `re.IGNORECASE`, `re.MULTILINE`, `re.DOTALL`, `re.VERBOSE`, `re.LOCALE`).
- **`re` — Atomic groups and possessive quantifiers** — https://docs.python.org/3/library/re.html#atomic-groups — accessed 2026-10-23 — the syntax and semantics of `(?>...)` and `*+`/`++`/`?+`, added in Python 3.11 to prevent catastrophic backtracking.
- **Pydantic v2 — `Field` constraints** — https://docs.pydantic.dev/2.12/concepts/fields/ — accessed 2026-10-23 — the `Field(pattern=...)` declarative validator; how Pydantic uses `re.fullmatch` internally and emits the `pattern` keyword into OpenAPI.
- **Pydantic v2 — `EmailStr`** — https://docs.pydantic.dev/2.12/concepts/types/#emailstr — accessed 2026-10-23 — the email type that delegates to the `email-validator` package; the right alternative to a regex email pattern.
- **OWASP — Regular expression Denial of Service (ReDoS)** — https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS — accessed 2026-10-23 — the canonical description of the catastrophic-backtracking attack, including the `(a+)+` family of evil patterns.
