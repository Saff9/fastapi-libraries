---
title: "Lesson 03: ISO 8601 format"
aliases:
 - ISO 8601
 - datetime.isoformat
 - datetime.fromisoformat
 - timespec
tags:
 - datetime
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[15-datetime/01-datetime-and-timezone]]"
 - "[[15-datetime/02-timedelta]]"
related_lessons:
 - "[[15-datetime/02-timedelta]]"
 - "[[15-datetime/05-fromisoformat-and-parsing]]"
---

# Lesson 03: ISO 8601 format

*Why `boardly`'s `Ticket.created_at` is serialised with `dt.isoformat()` to `2026-10-23T12:00:00+00:00` — and the `timespec` parameter that decides whether microseconds appear or get truncated at the wire boundary.*

**You're at the very beginning of Section 15, Lesson 03.**

You can construct an aware UTC `datetime` (lesson 01), you can do `timedelta` arithmetic on it (lesson 02), and now you need to send it across a wire. A JSON body, an HTTP header, a log line, a Postgres `timestamptz` column — every external system your `boardly` service talks to expects a string, and the string has to round-trip back to the same `datetime` on the way in. The format you use is ISO 8601, and the stdlib method that produces it is `datetime.isoformat()`. This lesson walks `isoformat()` end to end — the `sep='T'` default, the `timespec='auto'` parameter, the six `timespec` options, the `+00:00` suffix that distinguishes aware UTC from naive, and the round-trip with `datetime.fromisoformat(s)` that re-creates the same `datetime` from the string. Take your time. Type every example. **This is how you learn.**

#datetime #iso8601

## Learning Objectives

By the end of this lesson you will be able to:

1. **Serialise a `datetime` to ISO 8601** — write `dt.isoformat()` and read the output `2026-10-23T12:00:00.ffffff+00:00`, naming every component.
2. **Use the `timespec` parameter** — pass `'auto'` / `'hours'` / `'minutes'` / `'seconds'` / `'milliseconds'` / `'microseconds'` and explain which output each one produces.
3. **Explain the `sep` parameter** — pass `sep='T'` (default) vs `sep=' '` (the human-readable form) and explain which boundary each one is for.
4. **Read the offset suffix** — distinguish `+00:00` (UTC), `+05:30` (IST), and *no suffix* (naive — a wall-clock reading with no timezone).
5. **Round-trip a `datetime` through ISO 8601** — call `datetime.fromisoformat(dt.isoformat())` and confirm the result is `==` the original (modulo the `timespec` truncation).

## Prerequisites

Before starting, you need:

- **The `datetime` constructor and aware UTC** — [[15-datetime/01-datetime-and-timezone]]. You need to be comfortable constructing an aware UTC `datetime` before you serialise one.
- **`timedelta` arithmetic** — [[15-datetime/02-timedelta]]. The lesson uses `timedelta` to construct the `datetime` values that get serialised.
- **About 25–35 minutes of focused time.**

**The most common gap: assuming ISO 8601 is one format, not a family.**

It is a family. The ISO 8601 standard specifies *dozens* of permitted forms — `2026-10-23` (date only), `2026-10-23T12:00:00` (no offset, naive), `2026-10-23T12:00:00Z` (Z suffix for UTC), `2026-10-23T12:00:00+00:00` (numeric offset), `20261023T120000` (basic format, no separators), `2026-10-23T12:00:00,5` (comma as the decimal separator), `2026-W43-3T12:00:00` (week date) — and each downstream system accepts a slightly different subset. The single biggest mistake students make is writing `dt.isoformat()` and assuming the output is "the" ISO 8601 string; it is *one* ISO 8601 string, the canonical CPython form, and your Postgres column, your JSON serialiser, and your partner's webhook may each accept a slightly different set. The fix is to know what CPython produces by default, what `timespec` you can change, and what the round-trip rules are. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/api/bad_serialise.py — the bad old days
from datetime import datetime, timezone

def to_json_field(dt: datetime) -> str:
    return str(dt)                      # ← str() not isoformat(); works for naive, wrong for aware


created = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
print(to_json_field(created))           # '2026-10-23 12:00:00+00:00' — space sep, not 'T'
```

The `str(dt)` call produces `2026-10-23 12:00:00+00:00` — a space separator instead of the ISO 8601 `T`, no `timespec` control, and a form that downstream ISO 8601 parsers may reject (some accept the space form, some do not, and you cannot rely on which). The `str(dt)` call is convenient because it is one character shorter than `dt.isoformat()`, and it happens to produce the same characters when `tzinfo is None` — but the moment you go aware, the format drifts from canonical ISO 8601 and your partner's webhook starts returning 422.

This is not a Python problem. It is a "what format does each call produce" problem. Every language with a datetime type has the same family of forms, and the discipline is to use the canonical one (`isoformat()` in Python, `toISOString()` in JavaScript, `FormatRFC3339` in Go) at every boundary where the value crosses a process. The fix is to call `dt.isoformat()` (not `str(dt)`), pass `timespec` explicitly when you need to control precision, and round-trip the value with `datetime.fromisoformat(s)` at the parse boundary.

`datetime.isoformat()` is the standard-library answer to "I need a string form of this `datetime` that is unambiguous, ISO 8601-compliant, and round-trips". The default is `sep='T'` (the ISO 8601 separator between date and time) and `timespec='auto'` (the full precision the value carries, with trailing zeros truncated). The output is `YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM` for an aware datetime with microseconds, `YYYY-MM-DDTHH:MM:SS+HH:MM` for an aware datetime without, and `YYYY-MM-DDTHH:MM:SS` for a naive datetime (no suffix). Lesson 05 walks `fromisoformat()` in detail; this lesson focuses on the serialise side.

## The Code

```python
# boardly/api/iso8601_format.py
"""datetime.isoformat(), the sep and timespec parameters, the offset suffix,
and the round-trip with datetime.fromisoformat."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


# 1. The default: isoformat() with no arguments
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
print("aware_utc.isoformat():", aware_utc.isoformat())

# 2. With microseconds
aware_us = datetime(2026, 10, 23, 12, 0, 0, 500000, tzinfo=timezone.utc)
print("aware_us.isoformat():", aware_us.isoformat())

# 3. Naive datetime — no offset suffix
naive = datetime(2026, 10, 23, 12, 0, 0)
print("naive.isoformat():", naive.isoformat())

# 4. Non-UTC offset: +05:30 for IST
ist = timezone(timedelta(hours=5, minutes=30))
aware_ist = datetime(2026, 10, 23, 17, 30, 0, tzinfo=ist)
print("aware_ist.isoformat():", aware_ist.isoformat())

# 5. The sep parameter: default 'T', alternative ' ' (RFC 3339 / human-readable)
print("sep='T':", aware_utc.isoformat(sep='T'))
print("sep=' ': ", aware_utc.isoformat(sep=' '))

# 6. The timespec parameter: control over the precision of the time component
print("timespec='auto'        :", aware_utc.isoformat(timespec='auto'))
print("timespec='hours'       :", aware_utc.isoformat(timespec='hours'))
print("timespec='minutes'     :", aware_utc.isoformat(timespec='minutes'))
print("timespec='seconds'     :", aware_utc.isoformat(timespec='seconds'))
print("timespec='milliseconds':", aware_utc.isoformat(timespec='milliseconds'))
print("timespec='microseconds':", aware_utc.isoformat(timespec='microseconds'))

# 7. timespec='nanoseconds' is NOT a valid option — ValueError
try:
    aware_utc.isoformat(timespec='nanoseconds')
except ValueError as e:
    print("timespec='nanoseconds' raises:", e)

# 8. Round-trip: isoformat() -> fromisoformat()
serialised = aware_utc.isoformat()
parsed = datetime.fromisoformat(serialised)
print("round-trip parsed:", parsed)
print("round-trip equal:", parsed == aware_utc)

# 9. Round-trip preserves microsecond precision
serialised_us = aware_us.isoformat()
parsed_us = datetime.fromisoformat(serialised_us)
print("round-trip parsed_us:", parsed_us)
print("round-trip_us equal:", parsed_us == aware_us)

# 10. The boardly Ticket model — JSON-friendly ISO 8601
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),   # canonical ISO 8601
        }


t = Ticket(id=1, summary="login broken")
print("Ticket.to_json():", t.to_json())

# 11. Truncating microseconds for log lines (timespec='seconds')
log_line_created = t.created_at.isoformat(timespec='seconds')
print("log_line created_at:", log_line_created)

# 12. The deadline — Project with an aware UTC deadline, serialised
@dataclass
class Project:
    id: int
    name: str
    deadline: datetime


p = Project(id=1, name="alpha", deadline=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
print("Project.deadline.isoformat():", p.deadline.isoformat())
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–8: The default `isoformat()` call

```python
# 1. The default: isoformat() with no arguments
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
print("aware_utc.isoformat():", aware_utc.isoformat())
```

The `datetime.isoformat(sep='T', timespec='auto')` signature has two keyword arguments with defaults. With no arguments, the call produces the canonical CPython ISO 8601 form for the value — `2026-10-23T12:00:00+00:00` for an aware UTC `datetime` with no microseconds. The components are:
- `2026-10-23` — the date in `YYYY-MM-DD` form (zero-padded month and day).
- `T` — the separator between date and time (the ISO 8601 default; controlled by `sep`).
- `12:00:00` — the time in `HH:MM:SS` form (24-hour clock, zero-padded).
- `+00:00` — the UTC offset in `±HH:MM` form (zero for UTC).

The form is unambiguous: a downstream parser knows the date, the time, and the offset; there is no implicit timezone assumption. The `+00:00` suffix is the visible marker of awareness — without it, the value is naive and the offset is unspecified. Lesson 04 walks the rule that "no suffix" means "the value is ambiguous the moment it crosses a process boundary"; for now, the rule is "an aware `datetime` always has the suffix, a naive `datetime` never does".

**Why is the separator `T` and not a space?** Because the ISO 8601 standard requires either `T` or a space, and the `T` form is the strict canonical form that every ISO 8601 parser accepts. The space form is permitted by ISO 8601 (and by RFC 3339, which is a profile of ISO 8601) but some downstream parsers — Postgres `to_timestamp` with certain format strings, older `dateutil` versions, hand-rolled regex validators — accept only the `T` form. Using `T` by default is the conservative choice; you can switch to a space with `sep=' '` when you know the downstream parser accepts it (e.g. when the consumer is a human reading a log line).

### Lines 10–12: Microseconds in the serialised form

```python
# 2. With microseconds
aware_us = datetime(2026, 10, 23, 12, 0, 0, 500000, tzinfo=timezone.utc)
print("aware_us.isoformat():", aware_us.isoformat())
```

A `datetime` with a non-zero `microsecond` field includes a `.ffffff` component in the serialised form. `aware_us.isoformat()` returns `2026-10-23T12:00:00.500000+00:00` — the `.500000` is six digits of microsecond precision. The fractional part is always six digits (zero-padded), even when only one digit is significant — `microsecond=500000` is exactly half a second, and the trailing zeros are not truncated. (Compare with `timespec='auto'`, which does truncate trailing zeros — see below.)

The microsecond precision is the *maximum* CPython supports. There is no nanosecond precision in `datetime` — the type's atomic unit is the microsecond, and any value with more precision gets truncated at construction time. Lesson 05 walks the `timespec='nanoseconds'` mistake (it raises `ValueError`); for now, the rule is "if you need nanosecond precision, `datetime` is the wrong type — use `time.time_ns()` or a custom `int`-nanoseconds field".

**Why six digits and not three?** Because `datetime` stores microseconds, and a microsecond is one-millionth of a second (six decimal places). Three digits would be millisecond precision (one-thousandth), which is what `timespec='milliseconds'` produces. The six-digit form is the *full precision* form; the three-digit form is the *truncated-to-milliseconds* form; and `timespec='auto'` chooses between them based on whether the microsecond field is zero.

### Lines 14–16: Naive datetime — no offset suffix

```python
# 3. Naive datetime — no offset suffix
naive = datetime(2026, 10, 23, 12, 0, 0)
print("naive.isoformat():", naive.isoformat())
```

`naive.isoformat()` returns `2026-10-23T12:00:00` — no `+00:00` suffix, no `Z` suffix, nothing. The form is ISO 8601-compliant for a "local datetime" (a wall-clock reading with no offset), and it round-trips: `datetime.fromisoformat("2026-10-23T12:00:00")` returns a naive `datetime` with `tzinfo is None`. The serialised form faithfully records the value's awareness — if `tzinfo` was `None` at serialise time, the suffix is absent; if `tzinfo` was set, the suffix appears.

The danger of this form is that downstream parsers treat it inconsistently. Postgres `to_timestamp('2026-10-23T12:00:00', 'YYYY-MM-DD"T"HH24:MI:SS')` returns an aware UTC timestamp (because `to_timestamp` always returns `timestamptz`); JavaScript `new Date('2026-10-23T12:00:00')` treats the value as *local time* (the browser's timezone); Go `time.Parse(time.RFC3339, ...)` rejects the value entirely because RFC 3339 requires an offset. The naive ISO 8601 form is the *most ambiguous* of the family, and lesson 04's rule — "store aware UTC, never naive" — exists precisely because of this ambiguity.

**Why does the suffix appear only for aware values?** Because the `tzinfo` slot is the only place the offset is stored. A naive `datetime` has `tzinfo is None`, so there is no offset to write; the suffix is omitted. The serialiser cannot invent an offset (it would have to lie about the value's meaning); it can only record what the value carries. The discipline of "always store aware UTC" produces values that always have the `+00:00` suffix, always round-trip, and never trigger the "which timezone did this come from?" question.

### Lines 18–21: Non-UTC offset — `+05:30` for IST

```python
# 4. Non-UTC offset: +05:30 for IST
ist = timezone(timedelta(hours=5, minutes=30))
aware_ist = datetime(2026, 10, 23, 17, 30, 0, tzinfo=ist)
print("aware_ist.isoformat():", aware_ist.isoformat())
```

`aware_ist.isoformat()` returns `2026-10-23T17:30:00+05:30` — the offset is `+05:30`, India Standard Time. The offset is always in `±HH:MM` form (zero-padded hours and minutes, colon separator), even when the minutes part is zero (`+05:00`, not `+05`). The form is unambiguous: a downstream parser knows the wall-clock reading was `17:30` in a zone that is five-and-a-half hours ahead of UTC, and can convert to UTC (`12:00 UTC`) or to any other zone via `astimezone`.

The `+05:30` is the *offset*, not the *timezone name*. ISO 8601 has no place for "IST" or "America/New_York" — only for the numeric offset. The IANA name (the "timezone") is metadata that lives outside the string form; the offset is what the string records. This matters when you store a `datetime` and the offset changes later (e.g. the zone observes DST and the offset at the stored instant is different from the offset at read time). Lesson 05 walks the `zoneinfo.ZoneInfo` integration, which is how you preserve the IANA name across the round-trip.

**Why `+05:30` and not `+0530` or `+5:30`?** Because the ISO 8601 standard requires `±HH:MM` form with zero-padded hours and minutes and a colon separator. The basic format (`+0530`, no colon) is also valid ISO 8601 but CPython does not produce it; you have to write the formatter yourself if a downstream system requires the basic form. The colon form is the *extended* format and is the default for every modern ISO 8601 consumer (Postgres, RFC 3339, JSON Schema `date-time`).

### Lines 23–25: The `sep` parameter — `T` vs space

```python
# 5. The sep parameter: default 'T', alternative ' ' (RFC 3339 / human-readable)
print("sep='T':", aware_utc.isoformat(sep='T'))
print("sep=' ': ", aware_utc.isoformat(sep=' '))
```

The `sep` parameter is a one-character string that goes between the date and the time. The default is `'T'` (the strict ISO 8601 form); the alternative is `' '` (a space, which is permitted by ISO 8601 §4.3.2 and by RFC 3339 §5.6, and is more human-readable). The output of `aware_utc.isoformat(sep=' ')` is `2026-10-23 12:00:00+00:00` — identical to `str(aware_utc)`, which is the relationship that makes `str(dt)` look like a reasonable shortcut until you remember it does not let you pass `timespec`.

The discipline is: use `sep='T'` (the default) for machine-to-machine boundaries (JSON bodies, HTTP headers, Postgres `timestamptz` round-trips). Use `sep=' '` only for human-readable boundaries (log lines, CLI output, error messages) where you know the downstream consumer is a human and the readability win outweighs the strict-canonical-form loss. The default `T` is the safe choice everywhere; `sep=' '` is an opt-in for specific call sites.

**Why is `sep` a parameter and not a method like `isoformat_machine()` and `isoformat_human()`?** Because the separator is one character and the only variation point; a parameter is simpler than two methods. The same reasoning applies to `timespec` — six options, one parameter, no six-method API surface. The stdlib's design here is "one method, two parameters, full control"; the cost is that the call site has to know the parameter names, but the benefit is that the API surface stays small.

### Lines 27–33: The `timespec` parameter — control over precision

```python
# 6. The timespec parameter: control over the precision of the time component
print("timespec='auto'        :", aware_utc.isoformat(timespec='auto'))
print("timespec='hours'       :", aware_utc.isoformat(timespec='hours'))
print("timespec='minutes'     :", aware_utc.isoformat(timespec='minutes'))
print("timespec='seconds'     :", aware_utc.isoformat(timespec='seconds'))
print("timespec='milliseconds':", aware_utc.isoformat(timespec='milliseconds'))
print("timespec='microseconds':", aware_utc.isoformat(timespec='microseconds'))
```

The `timespec` parameter controls the precision of the time component in the serialised form. The six options are:
- `'auto'` (default) — full precision, with trailing zeros truncated. If `microsecond` is zero, no fractional part appears; if it is non-zero, six digits appear.
- `'hours'` — truncate to hours: `2026-10-23T12+00:00`. The minutes, seconds, and microseconds are dropped.
- `'minutes'` — truncate to minutes: `2026-10-23T12:00+00:00`.
- `'seconds'` — truncate to seconds: `2026-10-23T12:00:00+00:00`. Always three digits of seconds, no fractional part.
- `'milliseconds'` — truncate to milliseconds: `2026-10-23T12:00:00.000+00:00`. Always three digits (one-thousandth precision).
- `'microseconds'` — full microsecond precision: `2026-10-23T12:00:00.000000+00:00`. Always six digits (one-millionth precision), even when the trailing digits are zero.

The truncation is *towards zero*, not rounding: `aware_us.isoformat(timespec='seconds')` drops the `.500000` microsecond field, producing `2026-10-23T12:00:00+00:00` — not `12:00:01`. This is the right default for serialisation (rounding would change the value's meaning) but it is a footgun for log lines where you might want to display "rounded to the nearest second" — that requires `dt.replace(microsecond=round(dt.microsecond / 1e6) * 1e6 if dt.microsecond >= 500000 else 0)` and then `.isoformat(timespec='seconds')`. Most call sites want truncation, so the default is truncation.

**Why is `'auto'` the default and not `'microseconds'`?** Because `'auto'` produces the most compact form that round-trips — a `datetime` with no microseconds serialises to `12:00:00` (no fractional part), and a `datetime` with microseconds serialises to `12:00:00.500000` (six digits). The `'microseconds'` option would always produce six digits, even when they are all zero, which is wasted bytes for the common case (most `datetime` values have no microseconds). The `'auto'` choice is "show precision only when it matters"; the cost is that downstream parsers have to handle both forms.

### Lines 35–38: `timespec='nanoseconds'` is not a valid option

```python
# 7. timespec='nanoseconds' is NOT a valid option — ValueError
try:
    aware_utc.isoformat(timespec='nanoseconds')
except ValueError as e:
    print("timespec='nanoseconds' raises:", e)
```

The `'nanoseconds'` value is *not* a valid `timespec` argument. Passing it raises `ValueError: Unknown timespec value`. There is no nanosecond precision in `datetime` — the type's atomic unit is the microsecond — and the stdlib's choice is to refuse the option rather than silently truncate to microseconds (which would be a silent-precision-loss bug). If you need nanosecond precision for high-frequency trading, scientific timestamps, or distributed tracing, use `time.time_ns()` (which returns an `int` count of nanoseconds since the epoch) and store the value as an `int`, not a `datetime`.

**Danger — `'nanoseconds'` is the silent trap**

The Python documentation for some versions of 3.11 mentioned `'nanoseconds'` as a planned future option, and some third-party tutorials list it as a valid value. It is not. Passing `'nanoseconds'` to `isoformat()` raises `ValueError` on every Python version that ships `datetime.isoformat(timespec=...)` (Python 3.6+). Lint for `timespec='nanoseconds'` in code review; it is always a bug.

### Lines 40–46: Round-trip — `isoformat()` ↔ `fromisoformat()`

```python
# 8. Round-trip: isoformat() -> fromisoformat()
serialised = aware_utc.isoformat()
parsed = datetime.fromisoformat(serialised)
print("round-trip parsed:", parsed)
print("round-trip equal:", parsed == aware_utc)
```

The pair `isoformat()` and `fromisoformat()` are designed to round-trip. `serialised = aware_utc.isoformat()` produces `2026-10-23T12:00:00+00:00`; `parsed = datetime.fromisoformat(serialised)` produces a `datetime` that `==` the original. The equality is exact for any `datetime` whose precision is microseconds or coarser — the serialise side records every field, the parse side restores every field, and the two are byte-for-byte identical in their internal representation.

The `tzinfo` round-trips too: a `+00:00` offset on the serialise side becomes a `timezone` instance on the parse side that `==` `timezone.utc` (the same offset). A `+05:30` offset becomes a `timezone(timedelta(hours=5, minutes=30))` instance, which `==` the IST `timezone` constructed at serialise time. The IANA *name* (`"America/New_York"`) does not round-trip — `isoformat()` writes the offset, not the name, and `fromisoformat()` parses the offset into a `timezone` instance, not a `ZoneInfo` instance. For values that need the IANA name preserved across the round-trip, store the name in a separate field and reattach the `ZoneInfo` at parse time.

**Why is the round-trip exact for `==` but not for `is`?** Because `isoformat()` serialises the *value* (the offset), and `fromisoformat()` constructs a *new* `timezone` instance from that offset. Two `timezone(timedelta(0))` instances have the same `__eq__` (they are both the zero-offset timezone) but they are not the same object — `parsed.tzinfo is timezone.utc` *would* be `False` if Python constructed a fresh instance. **Python 3.11+ special-cases the `+00:00` form**: `datetime.fromisoformat("2026-10-23T12:00:00+00:00").tzinfo is timezone.utc` returns `True` (the singleton is returned directly). For other offsets (`+05:30`, `-08:00`), a fresh `timezone` instance is constructed on each parse; `is` comparisons against the original-tzinfo object will be `False`, but `==` comparisons succeed. The discipline is: compare `==` for `datetime` equality, not `is`; the type's `__eq__` handles the offset comparison correctly.

### Lines 48–52: Microsecond-precision round-trip

```python
# 9. Round-trip preserves microsecond precision
serialised_us = aware_us.isoformat()
parsed_us = datetime.fromisoformat(serialised_us)
print("round-trip parsed_us:", parsed_us)
print("round-trip_us equal:", parsed_us == aware_us)
```

The microsecond-precision round-trip is also exact. `aware_us = datetime(2026, 10, 23, 12, 0, 0, 500000, tzinfo=timezone.utc)` serialises to `2026-10-23T12:00:00.500000+00:00`; `fromisoformat` parses the `.500000` back to `microsecond=500000`. The `==` is `True`. The round-trip preserves every field CPython `datetime` carries — year, month, day, hour, minute, second, microsecond, and the offset.

The trap is `timespec`. If you serialise with `timespec='seconds'`, the microseconds are *truncated* in the serialised form, and the round-trip produces a `datetime` with `microsecond=0` — `==` against the original is `False`. This is not a bug; it is the contract of `timespec`. The discipline is: only use a non-`auto` `timespec` when you do not need the truncated precision to round-trip. For storage and round-trip, always use `timespec='auto'` (the default).

### Lines 54–63: The `boardly` Ticket model with `to_json()`

```python
# 10. The boardly Ticket model — JSON-friendly ISO 8601
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),   # canonical ISO 8601
        }


t = Ticket(id=1, summary="login broken")
print("Ticket.to_json():", t.to_json())
```

The `to_json()` method serialises the `Ticket` to a `dict` suitable for `json.dumps()`. The `created_at` field is serialised with `self.created_at.isoformat()` — the canonical CPython ISO 8601 form, `2026-10-23T12:00:00.ffffff+00:00` (with microseconds if present, without if not). The output is JSON-safe (the string contains no characters that need escaping beyond the JSON string-quote), is human-readable, and round-trips through `datetime.fromisoformat()` at the parse boundary.

The choice of `isoformat()` over `str(self.created_at)` is deliberate: `isoformat()` lets you pass `timespec` and `sep` if you need to control the form, and it produces the canonical `T`-separated form that every ISO 8601 parser accepts. `str(dt)` is a one-character shortcut that produces the space-separated form and does not let you pass `timespec`; it is the wrong choice for a JSON boundary. Use `isoformat()` at every wire boundary.

**Why not `json.dumps(self.created_at, default=...)`?** Because `json.dumps()` does not know how to serialise a `datetime` by default (it raises `TypeError: Object of type datetime is not JSON serializable`), and the `default=...` hook is the place to call `isoformat()`. But the discipline is to convert *before* the `json.dumps` call, in the `to_json()` method, so the type contract is explicit at the model layer. The `default=...` hook is a fallback for nested values you forgot to convert; it should not be the primary path. Lesson 05 walks the FastAPI integration, where Pydantic's `model_dump_json()` calls `isoformat()` for you.

### Lines 65–68: Truncating microseconds for log lines

```python
# 11. Truncating microseconds for log lines (timespec='seconds')
log_line_created = t.created_at.isoformat(timespec='seconds')
print("log_line created_at:", log_line_created)
```

The log-line form is `timespec='seconds'` — truncate the microseconds, produce `2026-10-23T12:00:00+00:00`. The form is shorter (no `.ffffff` part), is easier to read in a `tail -f` of a log file, and is precise enough for most operational log lines (the SLA window is in hours, not microseconds). The `timespec='seconds'` form is what `logging.Formatter` should produce by default for `created_at` fields in log records; it is what `uvicorn`'s default log format produces for the access-log timestamp.

The discipline is: use `timespec='auto'` (the default) for storage and round-trip; use `timespec='seconds'` for human-readable log lines; use `timespec='milliseconds'` for high-frequency request tracing where you need sub-second precision but not full microsecond precision. The choice is per-call-site, not per-field — the same `created_at` value can be serialised three different ways at three different boundaries (storage, log, audit), each with the `timespec` that fits the consumer.

### Lines 70–76: The `Project.deadline` serialised

```python
# 12. The deadline — Project with an aware UTC deadline, serialised
@dataclass
class Project:
    id: int
    name: str
    deadline: datetime


p = Project(id=1, name="alpha", deadline=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
print("Project.deadline.isoformat():", p.deadline.isoformat())
```

The `Project.deadline` field is an aware UTC `datetime` (the contract from lesson 01), and `isoformat()` produces `2026-12-31T23:59:59+00:00` — the last second of 2026 in UTC. The form is the canonical CPython output; round-trips through `datetime.fromisoformat()` at the parse boundary (lesson 05); is JSON-safe; and is unambiguous about the timezone (the `+00:00` suffix says "this is UTC, not local, not unspecified").

The deadline is the second canonical boardly field that demonstrates the "store aware UTC, serialise with isoformat, parse with fromisoformat" pattern — the same pattern as `Ticket.created_at`. Every `datetime` field in the boardly models follows this contract, and the consistency is what lets the API layer serialise and the storage layer parse without per-field configuration. Lesson 04 walks the production rule that this contract depends on ("never store naive"); lesson 05 walks the parse-side `fromisoformat()` mechanics.

## Execution Trace

The `Ticket.created_at` value is the runtime UTC instant and changes every time you run the script. The ISO 8601 format and the round-trip booleans are what to check.

```bash
$ uv run python boardly/api/iso8601_format.py
aware_utc.isoformat(): 2026-10-23T12:00:00+00:00
aware_us.isoformat(): 2026-10-23T12:00:00.500000+00:00
naive.isoformat(): 2026-10-23T12:00:00
aware_ist.isoformat(): 2026-10-23T17:30:00+05:30
sep='T': 2026-10-23T12:00:00+00:00
sep=' ':  2026-10-23 12:00:00+00:00
timespec='auto'        : 2026-10-23T12:00:00+00:00
timespec='hours'       : 2026-10-23T12+00:00
timespec='minutes'     : 2026-10-23T12:00+00:00
timespec='seconds'     : 2026-10-23T12:00:00+00:00
timespec='milliseconds': 2026-10-23T12:00:00.000+00:00
timespec='microseconds': 2026-10-23T12:00:00.000000+00:00
timespec='nanoseconds' raises: Unknown timespec value
round-trip parsed: 2026-10-23 12:00:00+00:00
round-trip equal: True
round-trip parsed_us: 2026-10-23 12:00:00.500000+00:00
round-trip_us equal: True
Ticket.to_json(): {'id': 1, 'summary': 'login broken', 'created_at': '2026-10-23T07:07:59.966222+00:00'}
log_line created_at: 2026-10-23T07:07:59+00:00
Project.deadline.isoformat(): 2026-12-31T23:59:59+00:00
```

## Common Mistakes

### Mistake 1: Using `str(dt)` instead of `dt.isoformat()`

```python
json_field = str(created_at)   # '2026-10-23 12:00:00+00:00' — space sep, not 'T'
```

**Symptom:** The downstream parser (a partner's webhook, a strict ISO 8601 validator, Postgres `to_timestamp` with the wrong format string) rejects the value with a 422 or a parse error. The local test suite passes because the local parser is lenient.
**Why:** `str(dt)` produces a space separator instead of `T`, does not let you pass `timespec`, and is the *display* form rather than the *wire* form. The two happen to produce the same characters when `tzinfo is None` (both omit the suffix), but they diverge for aware values where the form matters.
**Fix:** Use `dt.isoformat()` at every wire boundary. Reserve `str(dt)` for human-readable contexts where the format does not have to round-trip (debug `print` statements, interactive REPL sessions).

### Mistake 2: Passing `timespec='nanoseconds'`

```python
serialised = dt.isoformat(timespec='nanoseconds')   # ValueError: Unknown timespec value
```

**Symptom:** `ValueError` at the `isoformat()` call. The script never produces a serialised value.
**Why:** `'nanoseconds'` is not a valid `timespec` argument on any Python version. `datetime`'s atomic unit is the microsecond; there is no nanosecond precision in the type. Some third-party documentation lists `'nanoseconds'` as a planned future option; it has never shipped.
**Fix:** Use `timespec='microseconds'` (the maximum precision `datetime` supports) or `timespec='auto'` (the default, which produces full precision with trailing zeros truncated). If you genuinely need nanosecond precision, use `time.time_ns()` and store the value as an `int`, not a `datetime`.

### Mistake 3: Truncating microseconds for storage and expecting round-trip

```python
serialised = created_at.isoformat(timespec='seconds')   # '2026-10-23T12:00:00+00:00'
parsed = datetime.fromisoformat(serialised)
parsed == created_at        # False — microseconds were truncated at serialise
```

**Symptom:** The round-trip equality check fails. The stored value and the parsed value differ in the `microsecond` field.
**Why:** `timespec='seconds'` truncates the microseconds in the serialised form; `fromisoformat` cannot recover what was never written. The contract of `timespec` is "produce the form with this precision"; the contract does not include "round-trip the original value".
**Fix:** Use `timespec='auto'` (the default) for storage and round-trip. Reserve `timespec='seconds'` and `timespec='milliseconds'` for display boundaries where the precision loss is intentional and the value does not have to round-trip.

### Mistake 4: Serialising a naive `datetime` and assuming it means UTC

```python
naive_utc = datetime(2026, 10, 23, 12, 0, 0)    # naive — no tzinfo
serialised = naive_utc.isoformat()              # '2026-10-23T12:00:00' — no suffix
parsed = datetime.fromisoformat(serialised)     # naive — tzinfo is None
```

**Symptom:** The serialised form has no `+00:00` suffix; downstream parsers (Postgres, JavaScript, Go) interpret the value inconsistently — Postgres as UTC, JavaScript as local, Go rejects it. The round-trip back to Python preserves the naivety, but the value's meaning has drifted by the time it leaves the process.
**Why:** The `tzinfo is None` slot is what the serialiser reads. With no `tzinfo`, there is no offset to write, and the suffix is omitted. The downstream parser has to *guess* the timezone, and different parsers guess differently.
**Fix:** Store aware UTC: `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)`. The serialised form has the `+00:00` suffix, downstream parsers know it is UTC, and the value's meaning is preserved across the round-trip. Lesson 04 walks the production rule this depends on.

## Engineering Trade-Offs

**Decision:** Serialise every `datetime` field with `dt.isoformat()` (the default `sep='T'`, `timespec='auto'`) at every wire boundary. Use `timespec='seconds'` only for human-readable log lines. Never use `str(dt)`.
**Both sides:** The alternative is the `f"{dt:%Y-%m-%dT%H:%M:%S%z}"` format-string form, which gives you full control over every character but is verbose, error-prone, and loses the `timespec` ergonomics. The `isoformat()` method is the canonical shortcut for the common case (canonical ISO 8601 with the offset suffix); the format-string form is the escape hatch for the rare case (custom separators, custom precision, custom offset formats). The trade-off is "ergonomic common case, verbose rare case" vs "uniform verboseness everywhere".
**Commitment:** `boardly` uses `dt.isoformat()` for every `datetime` field in every `to_json()` method, in every FastAPI response model, and in every Postgres `timestamptz` round-trip. The `Ticket.to_json()` method calls `self.created_at.isoformat()` explicitly so the type contract is at the model layer. The FastAPI integration (Pydantic's `model_dump_json()`) calls `isoformat()` under the hood; the storage layer (Postgres `timestamptz` column) round-trips through `fromisoformat()` on the way back. The format-string form is reserved for one-off CLI output and never appears in the wire path.

## Exercises

1. **Exercise 1 — Switch to `str(dt)`.** Edit `Ticket.to_json()` to use `str(self.created_at)` instead of `self.created_at.isoformat()`. Re-run and confirm the `created_at` value uses a space separator instead of `T`. Then revert. `Verify: uv run python boardly/api/iso8601_format.py | rg 'Ticket.to_json'`
2. **Exercise 2 — Truncate microseconds for a log line.** Add a `to_log_line()` method to `Ticket` that returns `f"[{self.created_at.isoformat(timespec='seconds')}] {self.summary}"`. Confirm the timestamp has no fractional part. `Verify: uv run python -c "import sys; sys.path.insert(0, '.'); from boardly.api.iso8601_format import Ticket; t=Ticket(id=1,summary='x'); print(t.to_log_line())" 2>&1 | rg '^\['`
3. **Exercise 3 — Round-trip with `timespec='seconds'`.** Serialise `aware_us` (which has `microsecond=500000`) with `timespec='seconds'`, parse back with `fromisoformat`, and confirm the round-trip equality is `False` (the microseconds were truncated). `Verify: uv run python -c "from datetime import datetime, timezone; a=datetime(2026,10,23,12,0,0,500000,tzinfo=timezone.utc); s=a.isoformat(timespec='seconds'); print(datetime.fromisoformat(s)==a)"`
4. **Exercise 4 — Verify the offset suffix for IST.** Construct `datetime(2026, 10, 23, 17, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))` and confirm `isoformat()` produces `2026-10-23T17:30:00+05:30`. `Verify: uv run python -c "from datetime import datetime, timezone, timedelta; print(datetime(2026,10,23,17,30,0,tzinfo=timezone(timedelta(hours=5,minutes=30))).isoformat())"`
5. **Exercise 5 — Build a JSON-safe logger.** Write a function `serialise_for_log(dt: datetime, precision: str = 'seconds') -> str` that returns `dt.isoformat(sep=' ', timespec=precision)`. Confirm it produces `2026-10-23 12:00:00+00:00` for an aware UTC `datetime` with `timespec='seconds'`. Add a `try/except` for the `'nanoseconds'` value and confirm it raises `ValueError`. `Verify: uv run python -c "from datetime import datetime, timezone; print((lambda dt, p='seconds': dt.isoformat(sep=' ', timespec=p))(datetime(2026,10,23,12,tzinfo=timezone.utc)))"`

## Verification

The `Ticket.to_json()` value is the runtime UTC instant and changes every time you run the script. The ISO 8601 format strings and the round-trip booleans are what to check.

```bash
$ uv run python boardly/api/iso8601_format.py
aware_utc.isoformat(): 2026-10-23T12:00:00+00:00
aware_us.isoformat(): 2026-10-23T12:00:00.500000+00:00
naive.isoformat(): 2026-10-23T12:00:00
aware_ist.isoformat(): 2026-10-23T17:30:00+05:30
sep='T': 2026-10-23T12:00:00+00:00
sep=' ':  2026-10-23 12:00:00+00:00
timespec='auto'        : 2026-10-23T12:00:00+00:00
timespec='hours'       : 2026-10-23T12+00:00
timespec='minutes'     : 2026-10-23T12:00+00:00
timespec='seconds'     : 2026-10-23T12:00:00+00:00
timespec='milliseconds': 2026-10-23T12:00:00.000+00:00
timespec='microseconds': 2026-10-23T12:00:00.000000+00:00
timespec='nanoseconds' raises: Unknown timespec value
round-trip parsed: 2026-10-23 12:00:00+00:00
round-trip equal: True
round-trip parsed_us: 2026-10-23 12:00:00.500000+00:00
round-trip_us equal: True
Ticket.to_json(): {'id': 1, 'summary': 'login broken', 'created_at': '2026-10-23T07:07:59.966222+00:00'}
log_line created_at: 2026-10-23T07:07:59+00:00
Project.deadline.isoformat(): 2026-12-31T23:59:59+00:00
```

## Previously Learned Here

- [[15-datetime/01-datetime-and-timezone]] — the `datetime` constructor, the `tzinfo` slot, and the aware-UTC rule. Every value this lesson serialises is an aware UTC `datetime` constructed in lesson 01.
- [[15-datetime/02-timedelta]] — `timedelta` arithmetic; used here to construct the `+05:30` IST offset via `timezone(timedelta(hours=5, minutes=30))`.
- [[06-dataclasses/02-field-and-Defaults]] — the `field(default_factory=...)` pattern on the `Ticket.created_at` field, which `isoformat()` serialises.

## What's Next

[[15-datetime/04-timezone-aware-vs-naive]] — Now that you can serialise an aware `datetime` to ISO 8601 and round-trip it back, you need the production bug lesson: what happens when a naive `datetime` slips into the pipeline and gets compared to an aware one. Lesson 04 walks the `TypeError: can't compare offset-naive and offset-aware datetimes` exception, the `dt.tzinfo is None` test for naivety, the `dt.astimezone(tz)` conversion, and the cardinal rule "store aware UTC, render in the user's timezone at the edge".

- **Lesson 04** — aware vs naive, the `TypeError` comparison, the production rule.
- **Lesson 05** — `fromisoformat()` and `fromtimestamp()` at the parse boundary, `zoneinfo.ZoneInfo` for IANA names.

## Sources

- **Python `datetime` module documentation — `datetime.isoformat()`** — https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat — accessed 2026-10-23 — the canonical CPython reference for `isoformat(sep='T', timespec='auto')`, the six `timespec` options, and the round-trip contract with `fromisoformat()`.
- **Python `datetime` module documentation — `datetime.fromisoformat()`** — https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat — accessed 2026-10-23 — the parse-side counterpart that re-creates a `datetime` from an ISO 8601 string; lesson 05 walks it in detail.
- **ISO 8601 — Date and time format** — https://www.iso.org/standard/70907.html — accessed 2026-10-23 — the international standard that defines the `YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM` family of formats CPython `isoformat()` produces.
- **RFC 3339 — Date and Time on the Internet: Timestamps** — https://www.rfc-editor.org/rfc/rfc3339.html — accessed 2026-10-23 — the IETF profile of ISO 8601 that constrains the form for internet protocols; the source of the `T` vs space separator debate.

## What We Learned

- You can now serialise an aware UTC `datetime` with `dt.isoformat()` to `2026-10-23T12:00:00+00:00` and read every component of the ISO 8601 form.
- You can pass the `timespec` parameter (`'auto'`/`'hours'`/`'minutes'`/`'seconds'`/`'milliseconds'`/`'microseconds'`) to control the precision of the time component in the serialised form.
- You can pass `sep='T'` (default, machine-to-machine) or `sep=' '` (human-readable) and explain which boundary each one is for.
- You can read the offset suffix — `+00:00` for UTC, `+05:30` for IST, no suffix for naive — and explain why "no suffix" is the ambiguous case.
- You can round-trip a `datetime` through `datetime.fromisoformat(dt.isoformat())` and confirm the result `==` the original, with the caveat that `timespec` truncation breaks the round-trip if you use a precision-coarser-than-the-value's.
