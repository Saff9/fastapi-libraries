---
title: "Lesson 03: sub & named groups — the substitution family"
aliases:
 - re.sub
 - re.subn
 - re.expand
 - named groups
 - (?P<name>...)
 - callable repl
tags:
 - re
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[22-re/01-compile-and-match]]"
 - "[[22-re/02-search-findall-finditer]]"
related_lessons:
 - "[[22-re/04-re-in-validation]]"
 - "[[02-functools/03-partial]]"
---

# Lesson 03: sub & named groups — the substitution family

*How `boardly`'s date formatter turns `"2026-10-23"` into `"2026/10/23"` with `\g<year>` backrefs, how `sub` with a callable transforms each ticket id into a zero-padded canonical form, and the one-line mistake that converts `\1` into an octal escape and silently corrupts your substitution.*

**You're at the very beginning of Section 22 — three lessons in.**

Lessons 01 and 02 covered the *read-only* operations: `match`, `fullmatch`, `search`, `findall`, `finditer`. They extract information from a string; they do not modify it. This lesson covers the *write* operation: `re.sub` — substituting matches with a replacement. `re.sub` is what `boardly`'s audit-log formatter uses to turn ISO dates into slash dates, what the ticket-id normaliser uses to canonicalise uppercase and short ids, and what the URL rewriter uses to swap legacy paths. The lesson walks the three forms of `repl` — a string with `\1`/`\g<name>` backrefs, a callable that receives the `Match` per match, and `re.subn` which returns the count alongside the new string — plus the `(?P<name>...)` named-group syntax in depth. Take your time. Type every example. **This is how you learn.**

#re

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `re.sub` with a string replacement** — explain the `\1`, `\2`, ... positional backrefs and the `\g<name>` named backref form, and predict when `\1` produces an octal escape instead of a backref.
2. **Use `re.sub` with a callable replacement** — explain that the callable is called once per match with the `Match` object and returns the replacement string, and pick this form when the replacement needs per-match logic (lookups, conditionals, transformations).
3. **Read `re.subn`'s return** — explain the `(new_string, num_substitutions)` tuple and why you reach for `subn` when you need to know how many matches fired.
4. **Use `(?P<name>...)` named groups** — explain why `m.group("name")` is more readable than `m.group(1)` and why Python's named-group syntax is `(?P<name>...)` and *not* the .NET `(?<name>...)` form.
5. **Use `Match.expand(template)`** — explain that `expand` applies the same template syntax as `re.sub`'s string `repl`, but on a single `Match` (typically the one you got from `fullmatch`).

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[22-re/01-compile-and-match]]. The `Match` object and `m.group(...)` are this lesson's foundation; `sub`'s callable form passes a `Match` to your function.
- **Lesson 02** — [[22-re/02-search-findall-finditer]]. The compiled-`Pattern` form and the multi-match semantics are this lesson's substrate; `sub` finds every match in the string the same way `finditer` does.
- **A `lambda` or function** — the callable `repl` form passes a function. [[02-functools/03-partial]] covers the related `functools.partial` machinery if function-as-value is new.
- **About 35–50 minutes of focused time.**

**The most common gap: thinking `\1` and `\g<name>` are interchangeable.**

They are not — quite. `\1` is the positional backref ("the first capture group's text"), and `\g<name>` is the named backref. The two work in most cases. But `\1` is *also* the Python string escape for octal character codes (`\1` is the octal `001` character, `\12` is the ASCII newline, `\123` is the character with octal value 123). When the backref number is followed by a digit literal — say, `r"\12"` meaning "group 1 followed by literal `2`" — Python's parser sees `\12` and decodes it as octal. `\g<name>` is unambiguous because the `<...>` delimiters make the group reference self-terminating. The fix is to use `\g<name>` always, or `\g<1>` for positional — it costs nothing and removes a class of bugs.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/format/dates.py — the bad old days
import re

def to_slash(date: str) -> str:
    return re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\1/\2/\3", date)

def to_long_date(date: str) -> str:
    # The author wants "2026-10-23" -> "2026/10/23 (day 23 of month 10)".
    return re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\1/\2/\3 (day \3 of month \2)", date)
```

The first function works: `\1` is "the first group's text" (the year), `\2` the month, `\3` the day, and the result is `"2026/10/23"`. The second function *almost* works: the output is `"2026/10/23 (day 23 of month 10)"` — fine, because `\3` and `\2` happen to be followed by `)` and ` `, neither of which is a digit. But change the template to `r"\1/\2/\3 (day \32 of month \2)"` and the author expects `"2026/10/23 (day 232 of month 10)"`. What they get is `"2026/10/23 (day \x1a of month 10)"` — `\32` was decoded as octal `032`, which is ASCII `\x1a` (the SUB character). The bug is silent: the template parsed, the substitution ran, the output is just wrong.

The fix is `\g<3>2` — the `<...>` delimiters make the group reference self-terminating, and the `2` after the close angle bracket is a literal character. Lesson 03 walks the `\g<name>` form as the *default* and `\1` as the historical form you should recognise but not write.

## The Code

```python
# boardly/format/sub_and_named_groups.py
"""sub, subn, named groups, callable repl, expand — the substitution family."""
import re


# 1. A date string we want to reformat
ISO_DATE = "2026-10-23"


# 2. Pattern with named groups
DATE_RE = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")


# 3. sub with a string repl and \g<name> backrefs (the unambiguous form)
def iso_to_slash(date: str) -> str:
    return DATE_RE.sub(r"\g<year>/\g<month>/\g<day>", date)


# 4. sub with \1, \2 positional backrefs (less readable, ambiguity risk)
def iso_to_slash_positional(date: str) -> str:
    return DATE_RE.sub(r"\1/\2/\3", date)


# 5. sub with a callable repl — transform per match with real logic
def humanise_date(date: str) -> str:
    # The callable receives the Match; returns the replacement string.
    # Real per-match logic: convert "2026-10-23" into "Q4-2026 day 23".
    month_to_quarter = {
        "01": "Q1", "02": "Q1", "03": "Q1",
        "04": "Q2", "05": "Q2", "06": "Q2",
        "07": "Q3", "08": "Q3", "09": "Q3",
        "10": "Q4", "11": "Q4", "12": "Q4",
    }
    def repl(m: re.Match) -> str:
        quarter = month_to_quarter[m.group("month")]
        return f"{quarter}-{m.group('year')} day {m.group('day')}"
    return DATE_RE.sub(repl, date)


# 6. subn — returns (new_string, num_substitutions)
def count_and_replace(text: str, repl: str = "X") -> tuple[str, int]:
    return re.subn(r"\d+", repl, text)


# 7. expand() — apply a template to a single Match
def expand_demo() -> str:
    m = DATE_RE.fullmatch(ISO_DATE)
    # expand() applies the same \g<name> / \1 syntax as sub's repl string,
    # but on a single Match rather than across a whole string.
    return m.expand(r"year=\g<year>; month=\g<month>; day=\g<day>")


# 8. The .NET-style (?<name>...) — Python does NOT support this
def try_dotnet_named() -> None:
    try:
        re.compile(r"(?<year>\d{4})")
    except re.error as e:
        print(f"  (?<year>...) raised: {e}")


# 9. Multiple matches with callable repl — per-match normalisation
def normalise_ticket_ids(text: str) -> str:
    # Lowercase the ticket-id body and zero-pad to 12 hex chars after the prefix
    pat = re.compile(r"TKT-([A-Fa-f0-9]{6,12})")
    def repl(m: re.Match) -> str:
        body = m.group(1).lower().rjust(12, "0")  # pad with leading zeros
        return f"TKT-{body}"
    return pat.sub(repl, text)


if __name__ == "__main__":
    print("string repl with \\g<name>:", iso_to_slash(ISO_DATE))
    print("string repl with \\1 \\2 \\3:", iso_to_slash_positional(ISO_DATE))
    print("callable repl (quarter+year+day):", humanise_date(ISO_DATE))
    print()
    print("subn on 'a1 b22 c333':", count_and_replace("a1 b22 c333"))
    print("subn on 'a1 b22 c333', repl='#':", count_and_replace("a1 b22 c333", "#"))
    print()
    print("expand() demo:", expand_demo())
    print()
    print("Trying .NET (?<name>...) syntax:")
    try_dotnet_named()
    print()
    print("normalise_ticket_ids:")
    print(" ", normalise_ticket_ids("alice TKT-AB12CD and bob TKT-ef012345"))
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–7: The pattern with named groups

```python
import re


# 1. A date string we want to reformat
ISO_DATE = "2026-10-23"


# 2. Pattern with named groups
DATE_RE = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
```

The pattern `r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"` has three named groups: `year`, `month`, `day`. The `(?P<name>...)` syntax is Python's *only* named-group syntax. The .NET-style `(?<name>...)` form is *not* supported — block 8 of the demo proves this with a `re.error` — and the PCRE-style `(?P<name>...)` is what every Python regex uses. The `P` is historical: it stands for "Python-specific extension" in the original PCRE syntax, and `(?P...)` is the prefix Python reserved for its extensions.

A named group is also a numbered group. `(?P<year>\d{4})` is group 1, `(?P<month>\d{2})` is group 2, `(?P<day>\d{2})` is group 3. The name is an *alias* for the number — `m.group("year")` and `m.group(1)` return the same value. Both work in `re.sub`'s replacement template (`\g<year>` and `\g<1>` are equivalent) and in `m.group(...)`. The named form is more readable; the numbered form is the historical fallback when you cannot name a group (an inline pattern, a dynamically generated pattern).

**Why is the `P` in `(?P<name>...)`?** Because the original regex syntax (Perl/PCRE) reserved `(?<...)` and `(?(...)...)` and `(?P<name>...)` for Python-specific extensions. The `P` is the marker that tells the regex engine "this is a Python extension". Other languages adopted the same form to be Python-compatible — JavaScript's `(?<name>...)` is newer (ES2018) and uses the .NET form, so cross-language portability of patterns between Python and JavaScript requires writing numbered groups. Python has not added the `(?<name>...)` form because (a) it would be a backwards-incompatible parser change for any pattern that already uses `(?P<name>...)`, and (b) the existing form works fine.

### Lines 9–12: `sub` with a string `repl` and `\g<name>` backrefs

```python
# 3. sub with a string repl and \g<name> backrefs (the unambiguous form)
def iso_to_slash(date: str) -> str:
    return DATE_RE.sub(r"\g<year>/\g<month>/\g<day>", date)
```

`DATE_RE.sub(repl, date)` scans `date` for every match of the pattern and replaces each one with `repl`. When `repl` is a string, the engine interprets backrefs in it: `\g<year>` is "insert the year group's text", `\g<month>` the month, `\g<day>` the day. The `<...>` delimiters make the group reference self-terminating — there is no way for the next character in the template to be confused with the group name. The result is `"2026/10/23"`.

`\g<name>` is the *unambiguous* form. The alternative is `\1` (positional, group 1), which is shorter but ambiguous when followed by a digit. `\g<1>` works too — you can use the unambiguous form for positional backrefs as well as named ones. The lesson commits to `\g<name>` everywhere; `\1` is shown for context but not recommended.

`re.sub(pattern, repl, string, count=0, flags=0)` is the full signature. `count=0` means "replace all matches" (zero is the sentinel for "no limit"); `count=1` replaces only the first match; `count=3` the first three. `flags=0` is the default flags; passing `re.IGNORECASE` here applies case-insensitive matching for the *pattern* (not the `repl`).

**Why does `sub` accept a string *or* a callable for `repl`?** Because the two forms cover different use cases. A string `repl` is a *template* — every match produces the same replacement, with backrefs for the matched text. A callable `repl` is a *function* — every match produces a replacement computed from the `Match`, with full access to `m.group(...)`, conditionals, lookups, anything. The string form is faster (the engine parses the template once and applies it; the callable form has a Python function call per match). The callable form is more expressive (the replacement can do anything). The boardly rule: use the string form when the replacement is template-only, use the callable form when the replacement needs per-match logic.

### Lines 14–17: `sub` with `\1`, `\2`, `\3` — the historical form

```python
# 4. sub with \1, \2 positional backrefs (less readable, ambiguity risk)
def iso_to_slash_positional(date: str) -> str:
    return DATE_RE.sub(r"\1/\2/\3", date)
```

`\1` is the positional backref — "the first capture group's text". `\2` is the second, `\3` the third. The result is `"2026/10/23"` — the same as the `\g<name>` form. The two are equivalent *in this case* because none of the backrefs is followed by a digit.

The trap: when a backref is followed by a digit literal, the parser decodes the backref as octal. `r"\1/\2/\32"` would be parsed as `\1` (group 1), `/`, `\2` (group 2), `/`, `\32` (octal `032` = ASCII `\x1a`). The engine does not raise; it silently substitutes the octal character. The result is a string with an embedded control character that the operator does not see until they hex-dump the output. The fix is `\g<3>2` — the `<...>` delimiters make the group reference self-terminating.

**Warning — `\1` followed by a digit is silently octal.**

This bug is hard to spot in code review because the template reads naturally and the output *almost* looks right. The `\g<name>` form is the only one that prevents it. Lint for `\d` followed by a digit in `re.sub` templates. The fix is mechanical: replace `\1` with `\g<1>`, `\2` with `\g<2>`, etc. The cost is one keystroke; the benefit is never debugging octal escapes in templates again.

### Lines 19–33: `sub` with a callable — per-match logic

```python
# 5. sub with a callable repl — transform per match with real logic
def humanise_date(date: str) -> str:
    # The callable receives the Match; returns the replacement string.
    # Real per-match logic: convert "2026-10-23" into "Q4-2026 day 23".
    month_to_quarter = {
        "01": "Q1", "02": "Q1", "03": "Q1",
        "04": "Q2", "05": "Q2", "06": "Q2",
        "07": "Q3", "08": "Q3", "09": "Q3",
        "10": "Q4", "11": "Q4", "12": "Q4",
    }
    def repl(m: re.Match) -> str:
        quarter = month_to_quarter[m.group("month")]
        return f"{quarter}-{m.group('year')} day {m.group('day')}"
    return DATE_RE.sub(repl, date)
```

`DATE_RE.sub(repl, date)` where `repl` is a `def repl(m: re.Match) -> str: ...` function calls `repl` once per match, passing the `Match` object as the argument. The return value is the replacement string. The engine does the same scanning and replacing as the string `repl` form; the difference is that the replacement is *computed* per match, not templated.

`humanise_date("2026-10-23")` produces `"Q4-2026 day 23"`. The `month_to_quarter` dict is consulted *inside* the callable, so each match can look up its own quarter. A string `repl` could not do this — the template form has no way to "look up `month` in a dict and emit the quarter". The callable form is the only way to do per-match lookups, conditionals, transformations, anything that requires Python code.

The callable is called once per match, with the `Match` object. It receives *the whole match* — `.group(0)`, `.group("year")`, `.group("month")`, `.group("day")`, `.span()`, `.string`, all of it. It can return *any* string — including one longer or shorter than the original match. The engine substitutes the return value for the matched text in the output. If the callable returns `None`, `re.sub` raises `TypeError`; the contract is "return a string".

**Why not just `findall` + `str.replace`?** Because that re-implements `sub` badly. The naive approach — `for match in finditer(pattern, text): text = text.replace(match.group(0), replacement, 1)` — has three bugs: (1) `str.replace` finds the *first* occurrence of the matched text, which may be inside a previous match's replacement, leading to double substitution; (2) it walks the string once per match, O(N*M) where M is the match count; (3) it does not handle overlapping matches correctly. `re.sub` with a callable does the right thing: the engine walks the string once, calls the callable per match, and assembles the output as it goes. There is no double substitution, no quadratic walk, no overlap bug.

### Lines 35–38: `subn` — return the count alongside the new string

```python
# 6. subn — returns (new_string, num_substitutions)
def count_and_replace(text: str, repl: str = "X") -> tuple[str, int]:
    return re.subn(r"\d+", repl, text)
```

`re.subn(pattern, repl, string, count=0, flags=0)` has the same signature as `re.sub` but returns a `(new_string, num_substitutions)` tuple instead of just the new string. The `num_substitutions` is the number of matches the engine actually replaced (which is `min(count, total_matches)` when `count > 0`, or `total_matches` when `count == 0`).

`count_and_replace("a1 b22 c333")` returns `("aX bX cX", 3)` — the new string and the count of three matches. `count_and_replace("a1 b22 c333", repl="#")` returns `("a# b# c#", 3)`. The count tells you how many matches fired, which is what you need when the substitution is part of a metric ("how many ticket-ids were normalised in this audit log?") or a guard ("if zero substitutions, the input had no matches — log a warning").

`re.sub` is `re.subn(...)[0]` — the string alone, with the count discarded. There is no performance difference; `re.sub` internally calls `re.subn` and unpacks the first element. The two API forms exist because the count is sometimes useful and sometimes noise; `re.sub` is the convenience form, `re.subn` is the explicit form.

**Why would you use `subn` instead of `sub` and `len(re.findall(...))`?** Because `sub` + `findall` walks the string twice — once to substitute, once to count — and the two walks can disagree if the input is mutated between calls (say, by a threaded consumer). `subn` walks the string once, substitutes, and counts, atomically. For a single-threaded script the difference is just speed; for a system where the input can change between the substitute and the count, `subn` is the correctness choice.

### Lines 40–45: `Match.expand(template)` — apply a template to one match

```python
# 7. expand() — apply a template to a single Match
def expand_demo() -> str:
    m = DATE_RE.fullmatch(ISO_DATE)
    # expand() applies the same \g<name> / \1 syntax as sub's repl string,
    # but on a single Match rather than across a whole string.
    return m.expand(r"year=\g<year>; month=\g<month>; day=\g<day>")
```

`m.expand(template)` applies the same template syntax as `re.sub`'s string `repl`, but on a single `Match` instead of across a whole string. The template syntax (`\g<name>`, `\1`, `\g<1>`) is identical; the difference is that `expand` operates on one `Match` you already have, while `sub` finds its own matches and applies the template to each.

`expand_demo()` calls `DATE_RE.fullmatch(ISO_DATE)` to get one `Match`, then `m.expand(r"year=\g<year>; month=\g<month>; day=\g<day>")` to produce `"year=2026; month=10; day=23"`. The result is the same as `re.sub(DATE_RE, r"year=\g<year>; ...", ISO_DATE)` — but you already had the `Match`, so `expand` is more efficient (no second scan) and more readable (the template is applied to the match you held, not to the whole string).

`expand` is most useful when you have done *other* work on the `Match` first — looked up a group in a dict, decided which template to use, conditional logic — and then want to materialise the template. Without `expand`, you would fall back to f-strings with `m.group("name")` access; with `expand`, the template syntax is uniform with `re.sub`'s string `repl`, so you can share the template between the two contexts.

**Why use `expand` instead of an f-string?** When the template is data, not code. If the template is read from a config file or passed in as a function argument, you do not have the option of writing `f"{m.group('year')}-..."` — you have a *string*, not Python source. `expand` lets the string template be data: it can be loaded, stored, transmitted, edited by non-programmers. The f-string form is fine for one-off code where the template is inline; `expand` is the right call when the template is a runtime value.

### Lines 47–53: The `.NET (?<name>...)` form — Python does NOT support this

```python
# 8. The .NET-style (?<name>...) — Python does NOT support this
def try_dotnet_named() -> None:
    try:
        re.compile(r"(?<year>\d{4})")
    except re.error as e:
        print(f"  (?<year>...) raised: {e}")
```

This block is a negative example — it shows what *does not work*. The .NET regex engine and JavaScript (ES2018+) use `(?<name>...)` for named groups; Python uses `(?P<name>...)`. The two forms are not interchangeable. `re.compile(r"(?<year>\d{4})")` raises `re.error: unknown extension ?<y at position 1` — the parser sees `(?<`, treats `<` as the start of an extension it does not recognise, and stops.

The reason this matters: students who learned regex in JavaScript or .NET often try to port patterns to Python and hit this error. The fix is to add the `P`: `(?P<year>\d{4})`. There is no Python feature flag, no compatibility shim — the syntax is what it is. If you are writing patterns that need to be portable across Python and JavaScript, you have to use numbered groups (`(\d{4})` and `\1`), which both engines support.

**Danger — `(?<name>...)` raises `re.error`, not a `SyntaxError`.**

The error happens at runtime, when `re.compile` is called — not at module-load time when the string literal is parsed. A module that defines `BAD_RE = re.compile(r"(?<year>\d{4})")` at module scope raises `re.error` on first import, which can take down a FastAPI worker on the first request that imports the module. Lint for `(?<` (without the `P`) in your regex literals; the fix is mechanical.

### Lines 55–63: `sub` with a callable for per-match normalisation

```python
# 9. Multiple matches with callable repl — per-match normalisation
def normalise_ticket_ids(text: str) -> str:
    # Lowercase the ticket-id body and zero-pad to 12 hex chars after the prefix
    pat = re.compile(r"TKT-([A-Fa-f0-9]{6,12})")
    def repl(m: re.Match) -> str:
        body = m.group(1).lower().rjust(12, "0")  # pad with leading zeros
        return f"TKT-{body}"
    return pat.sub(repl, text)
```

This block is the production-shaped example. `normalise_ticket_ids("alice TKT-AB12CD and bob TKT-ef012345")` returns `"alice TKT-000000ab12cd and bob TKT-0000ef012345"`. The callable `repl` is called once per match — once for `TKT-AB12CD`, once for `TKT-ef012345` — and each call gets the `Match` for that specific occurrence. The replacement string is computed per match: `m.group(1).lower().rjust(12, "0")` lowercases the body and zero-pads it to 12 characters.

This is the use case the string `repl` form cannot handle. The replacement depends on the *length* of the matched body (`rjust(12, "0")` pads differently for a 6-character body and an 8-character body), which means it depends on per-match state. The string `repl` form is a template; it cannot compute. The callable form is a function; it can.

The pattern `r"TKT-([A-Fa-f0-9]{6,12})"` accepts 6–12 hex characters after `TKT-`. The `{6,12}` is a *bounded* quantifier, which matters for the ReDoS discussion in lesson 04 — bounded quantifiers cannot blow up the way unbounded ones can. The lesson 04 catastrophic-backtracking example uses the unbounded `(a+)+` form, which is exactly what bounded quantifiers prevent. Lesson 04 walks this in detail.

**Why is the body match `[A-Fa-f0-9]` and not `[a-f0-9]`?** Because the input may contain uppercase hex characters (`TKT-AB12CD`) that need to be *lowercased* as part of normalisation. If the pattern only accepted lowercase, the uppercase matches would be missed — and the `lower()` call inside `repl` would never run on them. The pattern accepts both cases; the callable normalises to lowercase. This is the *accept-then-normalise* pattern: the pattern is permissive on input, the callable is strict on output. The alternative — pattern only accepts lowercase, callable is identity — would leave uppercase input unchanged and unnormalised, which defeats the purpose.

## Execution Trace

```bash
$ uv run python boardly/format/sub_and_named_groups.py
string repl with \g<name>: 2026/10/23
string repl with \1 \2 \3: 2026/10/23
callable repl (quarter+year+day): Q4-2026 day 23

subn on 'a1 b22 c333': ('aX bX cX', 3)
subn on 'a1 b22 c333', repl='#': ('a# b# c#', 3)

expand() demo: year=2026; month=10; day=23

Trying .NET (?<name>...) syntax:
  (?<year>...) raised: unknown extension ?<y at position 1

normalise_ticket_ids:
  alice TKT-000000ab12cd and bob TKT-0000ef012345
```

## Common Mistakes

### Mistake 1: `\1` followed by a digit becomes octal

```python
re.sub(r"(\d)", r"\12", "5")          # returns '\x1a', not '52'
```

**Symptom:** The substitution produces a control character or garbage instead of the expected group-1 + literal-digit output. The string `"5"` becomes `"\x1a"` (a SUB character) instead of `"52"`.
**Why:** The Python string parser sees `\12` and decodes it as the octal escape `\o12` = ASCII `\x1a`. The `re` engine never gets a chance to interpret `\1` as "group 1 followed by `2`" because the parser already converted the literal.
**Fix:** Use `\g<1>2` — the `<...>` delimiters make the group reference self-terminating:

```python
re.sub(r"(\d)", r"\g<1>2", "5")        # returns '52' — correct
```

Or use named groups and `\g<name>` exclusively, which is the lesson's default recommendation.

### Mistake 2: `repl` callable returns `None`

```python
def repl(m):
    if m.group(0) == "skip":
        return None                    # accidental
    return m.group(0).upper()

re.sub(r"\w+", repl, "hello world")    # TypeError: sequence item 1: expected str, NoneType found
```

**Symptom:** `TypeError: expected str, NoneType found` from inside `re.sub`. The error does not name the callable or the match; it just says the result sequence has a `None`.
**Why:** `re.sub`'s callable `repl` contract is "return a string". Returning `None` violates the contract — the engine tries to splice `None` into the output string and fails. A common cause is an `if` branch that forgets to `return` (Python returns `None` implicitly).
**Fix:** Always return a string, even for the "skip" case:

```python
def repl(m):
    if m.group(0) == "skip":
        return m.group(0)              # return the original — i.e., no change
    return m.group(0).upper()
```

Or raise an exception, which is loud and at least does not produce a corrupt output.

### Mistake 3: Using `sub` when you need `subn`'s count

```python
new_text = re.sub(r"TKT-[a-f0-9]+", normalise, log)
# how many were normalised? We don't know.
matches = len(re.findall(r"TKT-[a-f0-9]+", log))   # walks the string AGAIN
```

**Symptom:** No bug visible — but the code walks the log twice, and the count is *approximately* the number of substitutions (it is exact if `normalise` returns a string that matches the same pattern, but the second `findall` walks the *new* text, not the original).
**Why:** `re.sub` discards the count. `re.subn` keeps it. Walking the string twice to recover the count is the cost of using the wrong API.
**Fix:** Use `re.subn`:

```python
new_text, count = re.subn(r"TKT-[a-f0-9]+", normalise, log)
print(f"normalised {count} ticket ids")
```

`subn` returns both in one walk; the count is the exact number of matches the engine replaced.

### Mistake 4: Trying to use `(?<name>...)` instead of `(?P<name>...)`

```python
re.compile(r"(?<year>\d{4})")        # re.error: unknown extension ?<y at position 1
```

**Symptom:** `re.error: unknown extension ?<y at position 1` at module import or first use. The error message is unhelpful — it points at the second character of the extension and says "unknown extension".
**Why:** The .NET/JavaScript `(?<name>...)` form is not supported by Python's `re` engine. The engine sees `(?<`, treats `<` as the start of an extension, and fails. The fix is the `P`: `(?P<name>...)`.
**Fix:** Add the `P`:

```python
re.compile(r"(?P<year>\d{4})")       # works
```

Or use numbered groups `(\d{4})` if the pattern needs to be portable across Python and JavaScript.

## Engineering Trade-Offs

**Decision:** `boardly` uses `\g<name>` for every backref in `re.sub` templates, callable `repl` for every substitution that needs per-match logic, and `re.subn` whenever the count matters.
**Both sides:** The alternative is `\1` everywhere (shorter, historical, octal-escape risk) and string `repl` everywhere (faster, no per-match logic). The trade-off: `\1` is shorter by one character per backref, but the octal-escape trap is a recurring source of silent bugs. The string `repl` is faster (no per-match Python call) but cannot express lookups or conditionals. `boardly` commits to the safe and expressive forms — `\g<name>` and callable `repl` — because the cost (one keystroke, one function-call overhead per match) is small and the benefit (no octal bugs, no double-walk bugs) is recurring. The string `repl` form is used when the replacement is purely templated (`iso_to_slash` is a template); the callable form is used when the replacement is computed (`humanise_date`, `normalise_ticket_ids`).
**Commitment:** `boardly`'s date formatters and ticket-id normalisers all use `\g<name>` for templates and callable `repl` for transformations. The `Field(pattern=...)` form in lesson 04 uses neither — Pydantic does not expose the `repl` API for declarative validation; the validator only accepts or rejects.

## Exercises

1. **Exercise 1 — Add a backslash form.** Add a function `iso_to_dot(date: str) -> str` that uses `re.sub` to produce `"2026.10.23"`. Use the `\g<name>` form. Confirm `iso_to_dot("2026-10-23") == "2026.10.23"`. `Verify: uv run python -c "from boardly.format.sub_and_named_groups import iso_to_dot; assert iso_to_dot('2026-10-23') == '2026.10.23'"`
2. **Exercise 2 — Trigger the octal bug.** Modify `iso_to_slash_positional` to use the template `r"\1/\2/\32"` and confirm the output ends with a control character (`\x1a`) instead of the day followed by `2`. Then fix it with `r"\1/\2/\g<3>2"`. `Verify: uv run python -c "from boardly.format.sub_and_named_groups import iso_to_slash_positional; import re; out = re.sub(re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'), r'\1/\2/\32', '2026-10-23'); assert '\\x1a' in repr(out)"`
3. **Exercise 3 — Add a `subn` metric.** Write a function `normalise_with_count(text: str) -> tuple[str, int]` that uses `re.subn` with the same `repl` as `normalise_ticket_ids` and returns the new string alongside the count. Confirm the count for `"alice TKT-AB12CD and bob TKT-ef012345"` is `2`. `Verify: uv run python -c "from boardly.format.sub_and_named_groups import normalise_with_count; s, n = normalise_with_count('alice TKT-AB12CD and bob TKT-ef012345'); assert n == 2"`
4. **Exercise 4 — `expand` on a single match.** Write a function `format_from_template(m: re.Match, template: str) -> str` that calls `m.expand(template)`. Use it with the template `r"\g<day> \g<month> \g<year>"` on a `DATE_RE.fullmatch("2026-10-23")` and confirm the output is `"23 10 2026"`. `Verify: uv run python -c "from boardly.format.sub_and_named_groups import DATE_RE, format_from_template; m = DATE_RE.fullmatch('2026-10-23'); assert format_from_template(m, r'\g<day> \g<month> \g<year>') == '23 10 2026'"`
5. **Exercise 5 — Transform with conditional logic.** Write a function `classify_ticket(text: str) -> str` that uses `re.sub` with a callable `repl` to replace `TKT-...` matches with `TKT-... [internal]` if the body starts with `a-f` and `TKT-... [external]` if it starts with `0-9`. Confirm the classification is correct for both inputs. `Verify: uv run python -c "from boardly.format.sub_and_named_groups import classify_ticket; out = classify_ticket('see TKT-abcd1234 and TKT-01234567'); assert 'internal' in out and 'external' in out"`

## Verification

```bash
$ uv run python boardly/format/sub_and_named_groups.py
string repl with \g<name>: 2026/10/23
string repl with \1 \2 \3: 2026/10/23
callable repl (quarter+year+day): Q4-2026 day 23

subn on 'a1 b22 c333': ('aX bX cX', 3)
subn on 'a1 b22 c333', repl='#': ('a# b# c#', 3)

expand() demo: year=2026; month=10; day=23

Trying .NET (?<name>...) syntax:
  (?<year>...) raised: unknown extension ?<y at position 1

normalise_ticket_ids:
  alice TKT-000000ab12cd and bob TKT-0000ef012345
```

## Previously Learned Here

- [[22-re/01-compile-and-match]] — the `Match` object and the `(?P<name>...)` named-group syntax that this lesson's `\g<name>` backrefs and `m.group("name")` rely on.
- [[22-re/02-search-findall-finditer]] — the multi-match engine that `re.sub` uses internally; `sub` finds every match in the string the same way `finditer` does.
- [[02-functools/03-partial]] — the function-as-value pattern that `sub`'s callable `repl` relies on; `partial` is the related way to bake in a partial argument.

## What's Next

[[22-re/04-re-in-validation]] — Lessons 01, 02, and 03 covered the `re` API surface: compile, match, fullmatch, search, findall, finditer, sub, subn, expand, named groups. Lesson 04 is the *use case*: `re` inside Pydantic `field_validator`s and FastAPI `Field(pattern=...)` declarations. The lesson covers the declarative `Field(pattern=r"^...$")` form that lets Pydantic do the regex check at the boundary, the `field_validator` form that lets you transform and validate in one pass, and the *anti-pattern*: parsing HTML or email with regex (use `email-validator` and `html.parser` instead). The lesson ends with the catastrophic-backtracking ReDoS trap — the `(a+)+` family of patterns that take exponential time on near-miss inputs — and the defences: bounded quantifiers, the `signal`-based timeout trick, and the atomic groups `(?>...)` and possessive quantifiers `a*+` that Python 3.11+ supports.

- **Lesson 04** — `re` in Pydantic validators, the "don't parse HTML with regex" rule, the ReDoS trap, `re.ASCII` / `re.LOCALE` flags.

## Sources

- **Python `re` module documentation** — https://docs.python.org/3/library/re.html — accessed 2026-10-23 — the source-of-truth reference for `re.sub`, `re.subn`, `Match.expand`, and the `(?P<name>...)` named-group syntax.
- **Python `re` "sub" reference** — https://docs.python.org/3/library/re.html#re.sub — accessed 2026-10-23 — the `repl` argument's two forms (string with backrefs, callable) and the `\g<name>` unambiguous backref syntax.
- **Python `re` "Atomic Groups and Possessive Quantifiers" reference** — https://docs.python.org/3/library/re.html#atomic-groups — accessed 2026-10-23 — the `(?>...)` atomic groups and `*+`/`++`/`?+` possessive quantifiers, added in Python 3.11; lesson 04 walks these in the ReDoS context.

## What We Learned

- You can now write `re.sub` with `\g<name>` backrefs and explain why `\1` is risky (octal-escape ambiguity when followed by a digit).
- You can use `re.sub` with a callable `repl` for per-match logic and explain why the callable form is the right choice when the replacement needs lookups, conditionals, or transformations.
- You can read `re.subn`'s `(new_string, num_substitutions)` return and explain when you reach for `subn` instead of `sub` (any time the count matters).
- You can use `(?P<name>...)` named groups and explain that Python does *not* support the .NET `(?<name>...)` form (which raises `re.error`).
- You can use `Match.expand(template)` for the case where you already have a `Match` and want to apply the same template syntax `re.sub`'s string `repl` uses, without re-scanning the input.
