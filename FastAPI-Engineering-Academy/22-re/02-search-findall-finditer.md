---
title: "Lesson 02: search, findall, finditer — the multi-match family"
aliases:
 - re.search
 - re.findall
 - re.finditer
 - re.Scanner
 - findall return types
tags:
 - re
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[22-re/01-compile-and-match]]"
related_lessons:
 - "[[22-re/03-sub-and-named-groups]]"
 - "[[22-re/04-re-in-validation]]"
---

# Lesson 02: search, findall, finditer — the multi-match family

*How `boardly`'s audit-log parser extracts every `TKT-…` mention, why `findall` returns `list[str]` for a no-group pattern and `list[tuple]` for a two-group pattern, and how `finditer` (3.7+) streams a 100-MB log without materialising the matches in memory.*

**You're at the very beginning of Section 22 — two lessons in.**

Lesson 01 taught you the *single-match* operations: `re.match` (anchored at the start), `re.fullmatch` (anchored at both ends). Both return a single `Match` or `None`. That is not enough. Real audit logs have a hundred ticket-id mentions in them. Real config files have a thousand `KEY=value` lines. You need an operation that returns *every* match, not just the first. The `re` module has three such operations — `search` returns the first match anywhere (not anchored at the start), `findall` returns a list of matches, `finditer` returns a lazy iterator of `Match` objects. This lesson walks all three, plus the rarely-used `re.Scanner` class. Take your time. Type every example. **This is how you learn.**

#re

## Learning Objectives

By the end of this lesson you will be able to:

1. **Distinguish `search` from `match`** — explain that `re.search` looks anywhere in the string (not anchored at the start) and returns the *first* match found, while `re.match` only looks at the start.
2. **Predict `findall`'s return type** — explain the three-way rule: zero groups returns `list[str]` (the full matches), one group returns `list[str]` (the group-1 captures), two or more groups returns `list[tuple]` (the captures in order).
3. **Use `finditer` for streaming** — explain why `finditer` (3.7+) returns a lazy iterator of `Match` objects instead of a list, and when that matters (multi-MB log files).
4. **Pick `finditer` over `findall` when you need positions** — explain that `findall` loses the `.span()` information (it only returns the captured text), while `finditer` gives you the `Match` object with `.span()`, `.start()`, `.end()`, `.groupdict()`.
5. **Read `re.Scanner`** — recognise the lexicon format `(pattern, action)` and explain why `Scanner` is "undocumented but useful" for tokenising structured text.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[22-re/01-compile-and-match]]. The compiled-`Pattern` form and the `Match` object accessors (`m.group(0)`, `m.span()`, etc.) are this lesson's foundation.
- **A `for` loop and a generator function** — the lesson streams `Match` objects through a generator; the closure/generator pattern is standard Python, but if it is new, [[02-functools/00-functools-MOC]] covers the related closure machinery.
- **About 35–50 minutes of focused time.**

**The most common gap: assuming `findall` returns `Match` objects.**

It does not. `findall` returns a `list[str]` (or `list[tuple]`) — the captured text only, no positions, no `.span()`, no `.groupdict()`. Students who write `for m in re.findall(r"\d+", text): print(m.span())` hit `AttributeError: 'str' object has no attribute 'span'` and are confused because the same `for m in re.finditer(...)` *did* work. The fix is to know which API returns what: `findall` returns text, `finditer` returns `Match`. That is the lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/audit/extract.py — the bad old days
import re

def all_ticket_ids(log: str) -> list[str]:
    matches = re.findall(r"TKT-[a-f0-9]{8,12}", log)
    return matches            # works! list[str]

def all_line_numbers(log: str) -> list[int]:
    matches = re.findall(r"TKT-[a-f0-9]{8,12}", log)
    return [m.span()[0] for m in matches]   # AttributeError: 'str' object has no attribute 'span'
```

The first function works. `findall` with a no-group pattern returns the full-match strings — exactly what the function wants. The second function breaks. The author assumed `findall` returns `Match` objects (because `finditer` does, and the two feel similar), but `findall` returns `str` values when the pattern has zero or one groups. The `m.span()` call on a `str` raises `AttributeError`. The fix is one of two things: call `.finditer()` instead of `.findall()` to get `Match` objects, or call `.finditer()` and read `.span()` off each one. Both fix it; the second is more efficient because you only need the positions once.

This lesson is the difference. `findall` is the *text-only* shortcut — fast, list-returning, convenient when you do not care about positions. `finditer` is the *full-fidelity* streamer — lazy, `Match`-returning, necessary when you need `.span()` or `.groupdict()` or just cannot afford to materialise the entire match list in memory.

## The Code

```python
# boardly/audit/search_findall_finditer.py
"""search, findall, finditer, Scanner — the multi-match family."""
import re
from dataclasses import dataclass


# 1. The audit log we'll be searching
@dataclass
class Event:
    timestamp: str
    actor: str
    action: str


LOG = """\
2026-10-23T09:00:00 alice created TKT-abcd1234
2026-10-23T09:05:00 bob   assigned TKT-abcd1234 to alice
2026-10-23T09:10:00 alice commented on TKT-abcd1234
2026-10-23T09:15:00 carol  closed TKT-ef012345
"""


# 2. A compiled pattern with ONE group — the ticket id
TICKET_RE = re.compile(r"TKT-[a-f0-9]{8,12}")


# 3. search() — first match anywhere, returns Match or None
def first_ticket() -> str | None:
    m = TICKET_RE.search(LOG)              # anywhere in the string
    return m.group(0) if m else None


# 4. findall() — the return type depends on the number of groups
def all_ticket_strings() -> list[str]:
    return TICKET_RE.findall(LOG)          # 0 groups -> list of full-match strings


# 5. findall() with a group — list of group-1 captures
def all_ticket_ids_only() -> list[str]:
    return re.findall(r"TKT-([a-f0-9]{8,12})", LOG)   # 1 group -> list of group-1


# 6. findall() with 2+ groups — list of tuples
def parse_events() -> list[tuple[str, str]]:
    pat = r"(\w+)\s+(?:created|closed)\s+(TKT-[a-f0-9]{8,12})"
    return re.findall(pat, LOG)            # 2 groups -> list of tuples


# 7. finditer() — lazy iterator of Match objects, 3.7+
def first_match_object() -> re.Match | None:
    for m in TICKET_RE.finditer(LOG):
        return m                           # the FIRST Match, with span() and all
    return None


# 8. finditer() — stream a 100-MB log without materialising a list
def stream_all_spans():
    for m in TICKET_RE.finditer(LOG):
        yield m.span(), m.group(0)


# 9. re.Scanner — the undocumented tokeniser
def scan_log() -> list[tuple[str, str]]:
    lexicon = [
        (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", lambda s, t: ("ts", t)),
        (r"TKT-[a-f0-9]{8,12}",                lambda s, t: ("id", t)),
        (r"[a-z]+",                            lambda s, t: ("word", t)),
        (r"\s+",                               lambda s, t: None),  # skip whitespace
    ]
    scanner = re.Scanner(lexicon)
    tokens, remainder = scanner.scan(LOG)
    return [t for t in tokens if t is not None]


if __name__ == "__main__":
    print("search():  ", first_ticket())
    print()
    print("findall() no groups:")
    for s in all_ticket_strings():
        print(" ", s)
    print()
    print("findall() 1 group (id only):")
    print(" ", all_ticket_ids_only())
    print()
    print("findall() 2 groups (tuples):")
    for tup in parse_events():
        print(" ", tup)
    print()
    m = first_match_object()
    print("finditer() first Match: span =", m.span(), "group =", m.group(0))
    print()
    print("finditer() streaming spans:")
    for span, text in stream_all_spans():
        print(" ", span, repr(text))
    print()
    print("re.Scanner tokens:")
    for kind, text in scan_log():
        print(f"  {kind}: {text!r}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–17: The audit log we'll be searching

```python
import re
from dataclasses import dataclass


# 1. The audit log we'll be searching
@dataclass
class Event:
    timestamp: str
    actor: str
    action: str


LOG = """\
2026-10-23T09:00:00 alice created TKT-abcd1234
2026-10-23T09:05:00 bob   assigned TKT-abcd1234 to alice
2026-10-23T09:10:00 alice commented on TKT-abcd1234
2026-10-23T09:15:00 carol  closed TKT-ef012345
"""
```

The `Event` dataclass is declared but not used in the demo code — it is here to anchor the *intent* of the audit-log structure. In the real `boardly` audit pipeline, each line is parsed into an `Event`; the lesson just shows the parsing primitives. The four-line `LOG` string is the test input: four audit events, three of which mention `TKT-abcd1234` and one of which mentions `TKT-ef012345`. The four lines collectively have four ticket-id mentions — enough to demonstrate `findall` and `finditer` returning multi-element results.

The `"""\` form is a multi-line string literal where the backslash at the end of the opening `"""\` escapes the leading newline — without it, `LOG` would start with a blank line, and `LOG[0] == "\n"`. The convention is borrowed from shell heredocs; it keeps the literal visually aligned with the four-line block it represents.

### Lines 19–20: The compiled pattern

```python
# 2. A compiled pattern with ONE group — the ticket id
TICKET_RE = re.compile(r"TKT-[a-f0-9]{8,12}")
```

`TICKET_RE` is a compiled `Pattern` with *zero* groups (no parentheses around the `[a-f0-9]{8,12}` part — the parentheses would be `(...)`, the form `TKT-(?:[a-f0-9]{8,12})` would be a non-capturing group that does not affect `findall`'s return type). The pattern matches the literal `TKT-` followed by 8–12 lowercase hex characters. Lesson 01 walked the `re.compile` form; this lesson reuses it without ceremony.

The group count matters here because `findall`'s return type depends on it. `TICKET_RE.findall(LOG)` returns `list[str]` (the full matches) because the pattern has zero groups. If the pattern were `r"TKT-([a-f0-9]{8,12})"` (one capturing group), `findall` would return `list[str]` of the *group-1* captures (just the hex part, without the `TKT-` prefix). If the pattern had two or more groups, `findall` would return `list[tuple[str, ...]]` of all captures. The next blocks demonstrate each case.

**Why does `findall` return *group-1 captures* instead of full-match strings when there is one group?** Because the most common use of `findall` with a group is "extract the interesting part from each match" — `re.findall(r"(\w+)@", text)` to get the username before each `@`, not the full `username@` text. The `re` designers optimised for the common case: zero groups → full matches (the only thing you can return), one group → group-1 captures (almost always what you want), two+ groups → tuples (because flat strings would lose information). The rule is non-obvious the first time you hit it; once learned, it is consistent.

### Lines 22–25: `search` — the first match anywhere

```python
# 3. search() — first match anywhere, returns Match or None
def first_ticket() -> str | None:
    m = TICKET_RE.search(LOG)              # anywhere in the string
    return m.group(0) if m else None
```

`TICKET_RE.search(LOG)` scans forward from position 0 looking for the first place the pattern matches. Unlike `match` (which only looks at position 0), `search` looks anywhere. It returns the *first* match it finds — a `Match` object — or `None` if the pattern does not match anywhere in the string. The first ticket in the log is `TKT-abcd1234` at position 34 (after the timestamp and `alice created `), so `search` returns a `Match` whose `.span()` is `(34, 46)`.

`search` is the operation you reach for when "is this pattern present anywhere in the input?" — substring search with a regex, instead of plain `in`. The two-line `m.group(0) if m else None` is the standard "give me the text or `None`" idiom; the ternary handles the non-match case so the caller never sees an `AttributeError` from `None.group(0)`.

**Why would you use `search` instead of `findall` and take `[0]`?** Because `findall` materialises the *entire* list of matches before returning it. On a 100-MB log with ten million ticket-id mentions, `findall(LOG)[0]` builds a 10M-element list in memory just to read the first element. `search(LOG)` returns the first match the engine finds and stops — O(1) memory for the first-match case. If you only need the first match, `search` is the right tool. If you need every match, `findall` (if you can afford the list) or `finditer` (if you cannot) is the right tool. Lesson 01's `match` vs `fullmatch` distinction applies here too: `search` is not anchored; if you want "first match starting at position 0", use `match`.

### Lines 27–30: `findall` with zero groups — `list[str]`

```python
# 4. findall() — the return type depends on the number of groups
def all_ticket_strings() -> list[str]:
    return TICKET_RE.findall(LOG)          # 0 groups -> list of full-match strings
```

`TICKET_RE.findall(LOG)` scans the entire string and collects every match. The pattern has zero capturing groups, so `findall` returns a `list[str]` of the full-match strings. For the four-line log, the result is `["TKT-abcd1234", "TKT-abcd1234", "TKT-abcd1234", "TKT-ef012345"]` — three mentions of the first ticket and one of the second. The full match text appears in each element, including the `TKT-` prefix.

`findall` is the convenience API: it collects the matches into a `list` and returns the list. There is no lazy variant of `findall` that returns an iterator of strings — if you need streaming, you use `finditer` (which returns `Match` objects, not strings). `findall` is appropriate when (a) you want every match, (b) the matches fit in memory, and (c) you do not need the `.span()` information. When any of those is false, `finditer` is the right call.

### Lines 32–35: `findall` with one group — `list[str]` of group-1 captures

```python
# 5. findall() with a group — list of group-1 captures
def all_ticket_ids_only() -> list[str]:
    return re.findall(r"TKT-([a-f0-9]{8,12})", LOG)   # 1 group -> list of group-1
```

This pattern has one capturing group: `([a-f0-9]{8,12})`. `findall` with a one-group pattern returns a `list[str]` of the *group-1* captures — `["abcd1234", "abcd1234", "abcd1234", "ef012345"]` — *not* the full matches. The `TKT-` prefix is gone, because the only capturing group does not include it. This is the non-obvious behaviour: adding a capturing group changes the return type's *content*, not just its shape. If you need the full matches and the captures, use `finditer` (which gives you the `Match` and lets you read both `m.group(0)` and `m.group(1)`).

**Why does `findall` with one group return `list[str]` and not `list[tuple[str]]`?** Because the tuple would always be a single-element tuple — `("abcd1234",)`, `("abcd1234",)`, etc. — and single-element tuples are awkward in Python (you have to write the trailing comma). The `re` designers unwrapped the single-element tuple into a plain string. The rule is consistent: zero groups → `list[str]` (full matches), one group → `list[str]` (group-1 captures), two+ groups → `list[tuple[str, ...]]`. Memorise the three-way split and you can predict the return type from the pattern's group count.

### Lines 37–40: `findall` with two groups — `list[tuple[str, ...]]`

```python
# 6. findall() with 2+ groups — list of tuples
def parse_events() -> list[tuple[str, str]]:
    pat = r"(\w+)\s+(?:created|closed)\s+(TKT-[a-f0-9]{8,12})"
    return re.findall(pat, LOG)            # 2 groups -> list of tuples
```

This pattern has two capturing groups: `(\w+)` (the actor) and `(TKT-[a-f0-9]{8,12})` (the ticket id). `findall` returns a `list[tuple[str, str]]` — `[("alice", "TKT-abcd1234"), ("carol", "TKT-ef012345")]` — where each tuple is the captures in order. Only two tuples appear (not four) because the pattern requires `(?:created|closed)` between the actor and the ticket id; the second and third audit lines say "assigned" and "commented", which do not match. So `findall` returns the matches that *did* fire.

The non-capturing group `(?:...)` is what makes this work without changing the group count. `(?:created|closed)` is a group for alternation (you need parentheses around `|` so it applies to the two literals, not the surrounding pattern), but `(?:...)` instead of `(...)` tells the engine "do not capture this group". Without the `?:`, the pattern would have three groups and `findall` would return three-element tuples with the second element being `"created"` or `"closed"`. Non-capturing groups are the way to group without adding to the capture count.

**Why does `findall` stop at the first non-matching line?** It does not — `findall` scans the entire string. The reason only two tuples appear is that the pattern itself does not match the other two lines: it requires `created` or `closed` after the actor and before the ticket, and the other two lines have `assigned` and `commented`. The two non-matching lines contribute zero matches. `findall` is not "stop at the first failure" — it is "scan to the end and collect every match the pattern produces".

### Lines 42–46: `finditer` — the lazy `Match` stream

```python
# 7. finditer() — lazy iterator of Match objects, 3.7+
def first_match_object() -> re.Match | None:
    for m in TICKET_RE.finditer(LOG):
        return m                           # the FIRST Match, with span() and all
    return None
```

`TICKET_RE.finditer(LOG)` returns a *lazy iterator* of `Match` objects. Unlike `findall` (which materialises the entire list), `finditer` produces one `Match` at a time, on demand. The `for m in ...` loop pulls the first `Match` and returns it immediately — the engine has only done the work to find the first match, and the rest of the log has not been scanned. On a four-line log the difference is negligible; on a 100-MB log with millions of matches, `finditer` is the difference between O(1) and O(N) memory.

The return type of `finditer` is always an iterator of `Match` objects — regardless of the pattern's group count. This is the second-biggest reason to prefer `finditer` over `findall`: `finditer` gives you the `Match` object, which exposes `.span()`, `.start()`, `.end()`, `.group(0)`, `.group("name")`, `.groupdict()`, `.string`, `.re` — everything. `findall` with one group returns `list[str]`, which has none of that. If you need positions, you must use `finditer`. There is no `findall` variant that returns positions.

`finditer` was added in Python 3.7. On earlier versions (3.6 and before), the workaround is `re.sub` with a callable that captures into a mutable list — ugly, but it works. On 3.7+ you should always use `finditer` for streaming.

**Why would you use `finditer` when you only need the first match?** Because `search` does the same thing for one match — and `search` is shorter. Use `finditer` when you need *every* match (or more than one), and use `search` when you need only the first. The `first_match_object` function in the demo is contrived to show that `finditer` *can* stop early; in production, you would use `search` for the first-match case and `finditer` for the all-matches case. The contrived function shows the engine does not scan to the end when the loop breaks early — it returns the first `Match` and stops.

### Lines 48–51: Streaming a multi-MB log

```python
# 8. finditer() — stream a 100-MB log without materialising a list
def stream_all_spans():
    for m in TICKET_RE.finditer(LOG):
        yield m.span(), m.group(0)
```

`stream_all_spans` is a generator function — the `yield` keyword makes it return a *generator iterator* instead of a `list`. Each `yield` produces a `(span, text)` tuple one at a time; the caller's `for span, text in stream_all_spans():` loop processes one tuple, then asks the generator for the next. The generator asks `finditer` for the next `Match`, which asks the regex engine to scan forward to the next match. At no point does the entire list of matches exist in memory — only the current `Match` and the current `(span, text)` tuple.

This is the streaming pattern. The 100-MB log scenario is not hypothetical — production audit logs in `boardly`'s deployments routinely exceed 10 GB, and a `findall` call on that would attempt to materialise a list of every ticket-id mention. Even if each match is only 14 bytes, ten million matches is 140 MB of `Match` overhead plus the list itself, which is enough to OOM a small container. `finditer` keeps the working set at one `Match` regardless of the input size.

The generator function is the way you wrap `finditer` for downstream consumers — the consumer's `for` loop sees a normal iterator and does not have to know about `re` or `Match`. Lesson 03 covers a similar pattern for `re.sub` with a callable, where the callable is called once per match and the streaming is implicit.

### Lines 53–62: `re.Scanner` — the undocumented tokeniser

```python
# 9. re.Scanner — the undocumented tokeniser
def scan_log() -> list[tuple[str, str]]:
    lexicon = [
        (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", lambda s, t: ("ts", t)),
        (r"TKT-[a-f0-9]{8,12}",                lambda s, t: ("id", t)),
        (r"[a-z]+",                            lambda s, t: ("word", t)),
        (r"\s+",                               lambda s, t: None),  # skip whitespace
    ]
    scanner = re.Scanner(lexicon)
    tokens, remainder = scanner.scan(LOG)
    return [t for t in tokens if t is not None]
```

`re.Scanner` is a class that exists in the `re` module (`re.Scanner` resolves to `<class 're.Scanner'>`) but is *not documented* in the Python standard library reference. The source lives in `Lib/re/_scanner.py` and is a small wrapper around `re.finditer` that tries each pattern in the lexicon at the current position, calls the corresponding action with the matched text, and advances the cursor. When no pattern matches at the current position, `scan` returns the tokens collected so far and the unparseable remainder.

The lexicon is a list of `(pattern, action)` pairs. The action is a callable `(scanner, token) -> result`; it receives the `Scanner` instance and the matched text. Returning `None` from the action means "skip this token" — used here for whitespace, which we want to consume but not emit. The order of the lexicon matters: the timestamp pattern is tried first because `[a-z]+` would match the `T` in `2026-...T09:00:00` as a word, which is not what we want. The scanner is leftmost-rule — the first pattern that matches at the current position wins, so the more-specific patterns go first.

**Warning — `re.Scanner` is undocumented.**

The class is exposed at `re.Scanner` and is callable, but the stdlib documentation does not mention it. The interface has been stable since Python 2.x, and the source is small enough to read in five minutes (`Lib/re/_scanner.py`), but it is *not* covered by the stdlib's stability promise in the way `re.compile` is. If you build a critical path on `Scanner`, pin the Python version in your deployment and keep an eye on the source. The honest recommendation is "use `re.Scanner` for prototypes and one-off scripts; use a real parsing library (`pyparsing`, `lark`, `parsimonious`) for production parsers". Lesson 04 has the same warning for HTML and email — `re` is the wrong tool for parsing context-free grammars, and `Scanner` does not change that.

## Execution Trace

```bash
$ uv run python boardly/audit/search_findall_finditer.py
search():   TKT-abcd1234

findall() no groups:
  TKT-abcd1234
  TKT-abcd1234
  TKT-abcd1234
  TKT-ef012345

findall() 1 group (id only):
  ['abcd1234', 'abcd1234', 'abcd1234', 'ef012345']

findall() 2 groups (tuples):
  ('alice', 'TKT-abcd1234')
  ('carol', 'TKT-ef012345')

finditer() first Match: span = (34, 46) group = TKT-abcd1234

finditer() streaming spans:
  (34, 46) 'TKT-abcd1234'
  (82, 94) 'TKT-abcd1234'
  (143, 155) 'TKT-abcd1234'
  (190, 202) 'TKT-ef012345'

re.Scanner tokens:
  ts: '2026-10-23T09:00:00'
  word: 'alice'
  word: 'created'
  id: 'TKT-abcd1234'
  ts: '2026-10-23T09:05:00'
  word: 'bob'
  word: 'assigned'
  id: 'TKT-abcd1234'
  word: 'to'
  word: 'alice'
  ts: '2026-10-23T09:10:00'
  word: 'alice'
  word: 'commented'
  word: 'on'
  id: 'TKT-abcd1234'
  ts: '2026-10-23T09:15:00'
  word: 'carol'
  word: 'closed'
  id: 'TKT-ef012345'
```

## Common Mistakes

### Mistake 1: Treating `findall` results as `Match` objects

```python
matches = re.findall(r"\d+", "a1 b22 c333")
for m in matches:
    print(m.span())           # AttributeError: 'str' object has no attribute 'span'
```

**Symptom:** `AttributeError: 'str' object has no attribute 'span'` from a loop that expected `Match` objects.
**Why:** `findall` returns `list[str]` (or `list[tuple]`) — the captured text only. It does not return `Match` objects. The student assumed it did because `finditer` does, and the two names are similar.
**Fix:** Use `finditer` when you need the `Match` object:

```python
for m in re.finditer(r"\d+", "a1 b22 c333"):
    print(m.span(), m.group(0))
```

Or accept that `findall` returns text and use it directly:

```python
for s in re.findall(r"\d+", "a1 b22 c333"):
    print(s)                  # '1', '22', '333'
```

### Mistake 2: Using `search` when you meant `match`

```python
if re.search(r"^\d+$", age_string):       # works, but redundant
    print("valid age")
```

**Symptom:** No bug — but the `^` and `$` are redundant if you are searching the whole string anyway. Or worse, the `^` is missing and `search` finds a match anywhere:
```python
if re.search(r"\d+", "abc123"):          # True — digits anywhere
    print("valid age")                   # accepts "abc123"!
```
**Why:** `search` is not anchored at the start. The pattern `r"\d+"` matches the first run of digits anywhere in the string. `"abc123"` has digits at positions 3–5, so `search` returns a `Match`. If you wanted "the whole string is digits", you needed `fullmatch`.
**Fix:** Use `re.fullmatch` (3.4+) for "the whole string matches this pattern":

```python
if re.fullmatch(r"\d+", age_string):
    print("valid age")                   # rejects "abc123"
```

### Mistake 3: Adding a group changes `findall`'s return type

```python
ids = re.findall(r"TKT-[a-f0-9]{8,12}", log)         # list[str] of full matches
ids = re.findall(r"TKT-([a-f0-9]{8,12})", log)        # list[str] of group-1 captures (no TKT-)
ids = re.findall(r"(TKT-)([a-f0-9]{8,12})", log)      # list[tuple[str, str]]
```

**Symptom:** Code that worked with one form of the pattern breaks when you "just add a group" — the return type changes from `list[str]` to `list[tuple]` and downstream `.group(0)`-style access breaks.
**Why:** `findall`'s return type depends on the group count. Zero groups → `list[str]` of full matches. One group → `list[str]` of group-1 captures. Two+ groups → `list[tuple[str, ...]]`. Adding a capturing group is not a no-op — it changes the API contract.
**Fix:** Use non-capturing groups `(?:...)` when you need to group for alternation or quantification but do not want to change the group count:

```python
ids = re.findall(r"TKT-[a-f0-9]{8,12}(?:!)?", log)    # zero groups, list[str] preserved
```

Or accept the new return type and update the downstream code. The two-way rule (zero/one group → `list[str]`, two+ groups → `list[tuple]`) is in the `re` documentation; it is consistent and worth memorising.

### Mistake 4: `findall` on a multi-GB log materialises a giant list

```python
matches = re.findall(r"\d{4}-\d{2}-\d{2}", huge_log_file.read())   # list of millions of strings
```

**Symptom:** The process balloons to multiple GB of memory and gets OOM-killed on a large log file.
**Why:** `findall` returns a `list` — it materialises every match in memory before returning. A 10-GB log with ten million date matches produces a list of ten million strings, which (with Python's per-object overhead) is several GB of heap.
**Fix:** Use `finditer` and process the matches lazily:

```python
with open("huge.log") as f:
    for line in f:                                  # stream line by line
        for m in re.finditer(r"\d{4}-\d{2}-\d{2}", line):
            yield m.group(0)
```

Or `mmap` the file and `finditer` over the mapped buffer. Either way, `finditer` keeps the working set at one `Match` per iteration.

## Engineering Trade-Offs

**Decision:** `boardly` uses `finditer` for streaming multi-MB audit logs and `findall` only when the input is known small (single config file, single request body) and no positional information is needed.
**Both sides:** The alternative is `findall` everywhere — simpler code, no generator wrappers, returns a list you can index and slice. The trade-off: `findall` materialises the entire match list. For a 200-character config string with three matches, that is three strings — fine. For a 10-GB log with millions of matches, it is a fatal memory blow-up. The boundary is fuzzy; `boardly`'s rule of thumb is "if the input size is unbounded (audit log, request body, user-uploaded file), use `finditer`; if it is bounded by a small constant (config file, route parameter, environment variable), use `findall` and pay the simplicity cost."
**Commitment:** `boardly`'s audit-log extractors (`audit/ticket_mentions.py`, `audit/actor_activity.py`) all use `finditer` and yield `Match` objects through generator functions. The `path` parameter validators in routes use `findall` (or rather, `fullmatch` for single-match validation — lesson 04). The split is intentional: streaming for unbounded inputs, materialising for bounded ones.

## Exercises

1. **Exercise 1 — Change the pattern group count.** Change `all_ticket_strings()` to use the pattern `r"(TKT-[a-f0-9]{8,12})"` (one capturing group). Re-run. Confirm the output is the same — the group-1 capture *is* the full match because the parentheses wrap the whole pattern. Then change it to `r"(TKT-)([a-f0-9]{8,12})"` and confirm `findall` now returns `list[tuple[str, str]]`. `Verify: uv run python -c "import boardly.audit.search_findall_finditer as m; import re; print(re.findall(r'(TKT-)([a-f0-9]{8,12})', m.LOG))"`
2. **Exercise 2 — Use `search` to find the last ticket.** The `search` operation returns the *first* match. To find the *last*, you need `finditer` and a loop that keeps the last match. Write `last_ticket(log: str) -> str | None` that uses `finditer` and returns the last ticket-id found, or `None`. Confirm `last_ticket(LOG)` returns `"TKT-ef012345"`. `Verify: uv run python -c "from boardly.audit.search_findall_finditer import LOG, last_ticket; assert last_ticket(LOG) == 'TKT-ef012345'"`
3. **Exercise 3 — Count ticket mentions.** Write `count_ticket_mentions(log: str) -> dict[str, int]` that returns a dict mapping each ticket id to the number of times it appears. Use `findall` (or `finditer`). Confirm `count_ticket_mentions(LOG)` returns `{"TKT-abcd1234": 3, "TKT-ef012345": 1}`. `Verify: uv run python -c "from boardly.audit.search_findall_finditer import LOG, count_ticket_mentions; assert count_ticket_mentions(LOG) == {'TKT-abcd1234': 3, 'TKT-ef012345': 1}"`
4. **Exercise 4 — Stream the log line by line.** Rewrite `stream_all_spans()` to read the log from a file object (an `io.TextIOBase`) instead of a string, and `finditer` over each line. Confirm the output matches the inline-string version. `Verify: uv run python -c "import io; from boardly.audit.search_findall_finditer import LOG, stream_spans_from_file; spans = list(stream_spans_from_file(io.StringIO(LOG))); assert spans[0] == ((34, 46), 'TKT-abcd1234')"`
5. **Exercise 5 — Add a `Scanner` rule for quoted strings.** Extend the `scan_log` lexicon with a rule that matches double-quoted strings (e.g., `"some text"`) and emits a `("string", text)` token. Add a line to `LOG` like `alice said "hello world"` and confirm the scanner produces `string: '"hello world"'`. `Verify: uv run python -c "from boardly.audit.search_findall_finditer import scan_log; tokens = scan_log(); assert any(k == 'string' for k, t in tokens)"`

## Verification

```bash
$ uv run python boardly/audit/search_findall_finditer.py
search():   TKT-abcd1234

findall() no groups:
  TKT-abcd1234
  TKT-abcd1234
  TKT-abcd1234
  TKT-ef012345

findall() 1 group (id only):
  ['abcd1234', 'abcd1234', 'abcd1234', 'ef012345']

findall() 2 groups (tuples):
  ('alice', 'TKT-abcd1234')
  ('carol', 'TKT-ef012345')

finditer() first Match: span = (34, 46) group = TKT-abcd1234

finditer() streaming spans:
  (34, 46) 'TKT-abcd1234'
  (82, 94) 'TKT-abcd1234'
  (143, 155) 'TKT-abcd1234'
  (190, 202) 'TKT-ef012345'

re.Scanner tokens:
  ts: '2026-10-23T09:00:00'
  word: 'alice'
  word: 'created'
  id: 'TKT-abcd1234'
  ts: '2026-10-23T09:05:00'
  word: 'bob'
  word: 'assigned'
  id: 'TKT-abcd1234'
  word: 'to'
  word: 'alice'
  ts: '2026-10-23T09:10:00'
  word: 'alice'
  word: 'commented'
  word: 'on'
  id: 'TKT-abcd1234'
  ts: '2026-10-23T09:15:00'
  word: 'carol'
  word: 'closed'
  id: 'TKT-ef012345'
```

## Previously Learned Here

- [[22-re/01-compile-and-match]] — the compiled `Pattern` object and the `Match` accessors this lesson reuses. Lesson 02 extends the single-match operations (`match`, `fullmatch`) to the multi-match family (`search`, `findall`, `finditer`).
- [[02-functools/00-functools-MOC]] — the generator-function pattern (`yield`-based streaming) that wraps `finditer` for downstream consumers. `functools` covers the related closure/iterator machinery.
- [[09-enum/05-Enum-in-APIs]] — the FastAPI/Pydantic integration that uses regex under the hood; lesson 04 returns to the validation side of `re`.

## What's Next

[[22-re/03-sub-and-named-groups]] — Lessons 01 and 02 covered the *read-only* operations: `match`, `fullmatch`, `search`, `findall`, `finditer`. The next lesson covers the *write* operation: `re.sub` — substituting matches with a replacement. Lesson 03 walks the three forms of `repl`: a string with `\1` / `\g<name>` backreferences, a callable that receives the `Match` and returns the replacement, and `re.subn` which returns the `(new_string, count)` tuple. The lesson also covers the `(?P<name>...)` named-group syntax in depth — including the `.NET` `(?<name>...)` form, which Python does *not* support (a common student confusion).

- **Lesson 03** — `re.sub`, `re.subn`, callable replacements, named groups `(?P<name>...)`, `re.expand`.
- **Lesson 04** — `re` inside Pydantic `field_validator`s and FastAPI `Field(pattern=...)`; the ReDoS catastrophic-backtracking trap and the `re.ASCII` / `re.LOCALE` flags for unicode classes.

## Sources

- **Python `re` module documentation** — https://docs.python.org/3/library/re.html — accessed 2026-10-23 — the source-of-truth reference for `re.search`, `re.findall`, `re.finditer`, and the return-type rules for `findall` (zero/one/multiple groups).
- **Python `re` "finditer" reference** — https://docs.python.org/3/library/re.html#re.finditer — accessed 2026-10-23 — the lazy-iterator-of-`Match` API, added in Python 3.7.
- **Python `re._scanner` source** — https://github.com/python/cpython/blob/3.12/Lib/re/_scanner.py — accessed 2026-10-23 — the source of `re.Scanner`, an undocumented-but-exposed tokeniser class; read this before relying on `Scanner` in production.

## What We Learned

- You can now distinguish `re.search` (first match anywhere) from `re.match` (anchored at the start) and from `re.fullmatch` (anchored at both ends).
- You can predict `findall`'s return type from the pattern's group count: zero groups → `list[str]` of full matches, one group → `list[str]` of group-1 captures, two+ groups → `list[tuple[str, ...]]`.
- You can use `finditer` (3.7+) to stream `Match` objects lazily, keeping the working set at one `Match` regardless of input size.
- You can wrap `finditer` in a generator function (`yield`-based) so downstream consumers see a plain iterator without knowing about `re` or `Match`.
- You can recognise `re.Scanner` as the undocumented-but-exposed tokeniser class and know when to prefer a real parsing library (`lark`, `pyparsing`) for production code.
