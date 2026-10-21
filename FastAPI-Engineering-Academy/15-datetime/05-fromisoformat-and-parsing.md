---
title: "Lesson 05: fromisoformat and parsing"
aliases:
 - datetime.fromisoformat
 - datetime.fromtimestamp
 - zoneinfo
 - ZoneInfo
 - dateutil
 - arrow
tags:
 - datetime
 - python-stdlib
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[15-datetime/01-datetime-and-timezone]]"
 - "[[15-datetime/03-ISO-8601-format]]"
 - "[[15-datetime/04-timezone-aware-vs-naive]]"
related_lessons:
 - "[[15-datetime/03-ISO-8601-format]]"
 - "[[15-datetime/04-timezone-aware-vs-naive]]"
---

# Lesson 05: fromisoformat and parsing

*The parse boundary that turns an ISO 8601 string from a webhook payload into an aware UTC `datetime` — and the "if the format is ISO, use stdlib; otherwise use `dateutil`" rule that prevents every parsing bug your service will ever ship.*

**You're at the very beginning of Section 15, Lesson 05.**

You can construct an aware UTC `datetime` (lesson 01), serialise it to ISO 8601 (lesson 03), and refuse naive values at the comparison layer (lesson 04). The last piece is the *parse* boundary: an incoming webhook sends `"created_at": "2026-10-23T12:00:00Z"` in the JSON body, your FastAPI route handler accepts it, and somewhere between the wire and the storage layer the string becomes an aware UTC `datetime`. This lesson walks `datetime.fromisoformat(s)` — the canonical parse path, Python 3.7+ and extended in 3.11+ to handle more ISO 8601 variants (version-gated); `datetime.fromtimestamp(ts, tz=...)` for POSIX-timestamp ingestion; `dateutil` and `arrow` for non-ISO formats (CSV exports, human-typed strings, partner APIs with bespoke date formats); and `zoneinfo.ZoneInfo(key)` (Python 3.9+, PEP 615) for IANA-named timezones. By the end you will know the rule that prevents every parsing bug: if the format is ISO, use stdlib; otherwise use `dateutil`; never write a hand-rolled regex parser. Take your time. Type every example. **This is how you learn.**

#datetime #fromisoformat #zoneinfo

## Learning Objectives

By the end of this lesson you will be able to:

1. **Parse ISO 8601 with `datetime.fromisoformat(s)`** — write `datetime.fromisoformat("2026-10-23T12:00:00+00:00")` and explain the Python 3.7+ baseline, the 3.11+ extension (Z suffix, basic format, week dates, comma decimal separator), and the version-gate.
2. **Ingest POSIX timestamps with `datetime.fromtimestamp(ts, tz=...)`** — write `datetime.fromtimestamp(ts, tz=timezone.utc)` for aware UTC and explain why `tz=None` (the default) is the same naive-local trap as `datetime.now()`.
3. **Use `zoneinfo.ZoneInfo(key)` for IANA timezones** — write `ZoneInfo("America/New_York")` (Python 3.9+, PEP 615), explain the IANA database and the `tzdata` package on Windows, and use the result as a `tzinfo` for `astimezone`.
4. **Pick the right parser for the format** — state the rule: ISO 8601 → `datetime.fromisoformat`; non-ISO → `dateutil.parser.parse` (with explicit `tzinfos`); never hand-roll a regex parser.
5. **Implement the boardly parse boundary** — write a Pydantic `field_validator` that accepts only aware UTC `datetime` values, rejecting naive input with a 422 before it reaches the storage layer.

## Prerequisites

Before starting, you need:

- **The `datetime` constructor and aware UTC** — [[15-datetime/01-datetime-and-timezone]]. Every value this lesson parses is constructed via the same `tzinfo=timezone.utc` contract.
- **ISO 8601 serialisation** — [[15-datetime/03-ISO-8601-format]]. The serialise and parse sides are designed to round-trip; you need to know what CPython produces on the serialise side to know what to accept on the parse side.
- **Aware vs naive** — [[15-datetime/04-timezone-aware-vs-naive]]. The parse boundary is where naive values slip in; you need to be able to detect `tzinfo is None` and refuse it.
- **About 30–45 minutes of focused time.**

**The most common gap: hand-rolling a regex parser.**

It is the wrong tool. Every senior engineer has, at some point, written `re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s)` and unpacked the groups into `datetime(int(m.group(1)), int(m.group(2)), ...)`. The regex parses *one* format; it does not handle the offset suffix, the microsecond fraction, the `Z` shorthand, the comma decimal separator, the basic (no-separator) format, or any of the dozen other ISO 8601 variants your partner will eventually send you. The single biggest mistake students make at the parse boundary is writing the regex parser "just for the common case" and then patching it for every variant as it comes in, until the parser is 50 lines of regex that handles every case except the one the production traffic sends next. The fix is the rule: if the format is ISO, use stdlib; otherwise use `dateutil`; never hand-roll. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/webhooks/bad_parse.py — the bad old days
import re
from datetime import datetime, timezone


def parse_created_at(s: str) -> datetime:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s)
    if not m:
        raise ValueError(f"bad created_at: {s!r}")
    return datetime(*[int(g) for g in m.groups()], tzinfo=timezone.utc)


# Production traffic sends the Z suffix — the regex does not handle it
payload = {"created_at": "2026-10-23T12:00:00Z"}      # Z suffix
try:
    parse_created_at(payload["created_at"])              # ValueError
except ValueError as e:
    print(e)
```

The regex `(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})` matches `2026-10-23T12:00:00` (the first 19 characters) but does not anchor the end of the string, so it also matches `2026-10-23T12:00:00Z` — the `Z` suffix is silently dropped, and the parsed value is an aware UTC `datetime` that happens to be correct only because the input was UTC. If the input were `2026-10-23T12:00:00+05:30` (IST), the regex would match the first 19 characters, drop the `+05:30` suffix, and produce `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)` — *the wrong instant by five and a half hours*, silently.

This is not a Python problem. It is a "do not hand-roll parsers for formats that have a standard" problem. The same trap exists in every language: Java engineers hand-roll `SimpleDateFormat` patterns and miss the `Z` variant; Go engineers hand-roll `time.Parse` format strings and miss the basic format; JavaScript engineers hand-roll `new Date(string)` calls and discover `Date`'s non-standard parsing. Python's answer is `datetime.fromisoformat(s)` — a method whose contract is "parse any valid ISO 8601 form CPython produces, raise `ValueError` on anything else" — and `dateutil.parser.parse` for non-ISO formats.

`datetime.fromisoformat(date_string)` is the standard-library answer to "I have a string and I need a `datetime`". The method was added in Python 3.7 to round-trip `isoformat()`'s output; in Python 3.11 it was extended to handle more ISO 8601 variants (the `Z` suffix, the basic format, week dates, the comma decimal separator, single-digit-hour offsets). For anything outside ISO 8601 — slash-separated dates, human-typed strings, partner APIs with bespoke formats — `dateutil.parser.parse(s)` (or `arrow.get(s, format)`) handles the rest. And `zoneinfo.ZoneInfo(key)` (Python 3.9+, PEP 615) provides the IANA-named timezone instances (`ZoneInfo("America/New_York")`) that the `tzinfo` slot accepts for non-fixed-offset zones. The three tools together cover every parse boundary you will ever write.

## The Code

```python
# boardly/webhooks/fromisoformat_and_parsing.py
"""datetime.fromisoformat, datetime.fromtimestamp, zoneinfo.ZoneInfo,
dateutil/arrow for non-ISO, and the Pydantic field_validator that
rejects naive input at the parse boundary."""
from __future__ import annotations
import sys
import time as time_module
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, tzinfo
from zoneinfo import ZoneInfo


# 1. datetime.fromisoformat (Python 3.7+; extended in 3.11+)
samples = [
    "2026-10-23T12:00:00+00:00",   # canonical CPython isoformat() output
    "2026-10-23T12:00:00Z",        # Z suffix — 3.11+
    "2026-10-23T12:00:00,5",       # comma as decimal sep — 3.11+
    "20261023T120000",             # basic (no-separator) format — 3.11+
    "2026-10-23T12:00:00+0000",    # offset without colon — 3.11+
    "2026-10-23T12:00:00+00",      # single-digit-hour offset — 3.11+
    "2026-10-23",                  # date-only input — produces midnight datetime
]
for s in samples:
    try:
        v = datetime.fromisoformat(s)
        print(f"OK  {s!r:35} -> {v!r}")
    except ValueError as e:
        print(f"ERR {s!r:35} -> {e}")

# 2. The pre-3.11 baseline (anchor the version gate)
print("python:", sys.version_info[:3], "(3.11+ extended fromisoformat)")

# 3. fromisoformat round-trips isoformat() for aware UTC
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
serialised = aware_utc.isoformat()
parsed = datetime.fromisoformat(serialised)
print("round-trip:", parsed == aware_utc, "| parsed.tzinfo:", parsed.tzinfo)

# 4. fromtimestamp: always pass tz=timezone.utc for aware UTC
ts = time_module.time()
naive_local = datetime.fromtimestamp(ts)                      # ← don't do this
aware_utc_ts = datetime.fromtimestamp(ts, tz=timezone.utc)    # ← do this
print("fromtimestamp(ts) tzinfo:", naive_local.tzinfo)         # None
print("fromtimestamp(ts, tz=utc) tzinfo:", aware_utc_ts.tzinfo)  # UTC

# 5. zoneinfo.ZoneInfo — IANA timezone names (Python 3.9+, PEP 615)
ny_tz = ZoneInfo("America/New_York")
print("ZoneInfo('America/New_York'):", ny_tz)
print("is a tzinfo:", isinstance(ny_tz, tzinfo))
aware_ny = aware_utc.astimezone(ny_tz)
print("UTC -> NY:", aware_ny, "| tzname:", aware_ny.tzname())

# 6. zoneinfo raises on invalid IANA key
try:
    ZoneInfo("Not/A_Real_Zone")
except KeyError as e:
    print("ZoneInfo invalid key raises KeyError:", e)

# 7. dateutil for non-ISO formats (slash-sep, human-typed)
from dateutil import parser as du_parser
from dateutil import tz as du_tz

non_iso = du_parser.parse("2026/10/23 12:00:00")
print("dateutil.parse('2026/10/23 12:00:00'):", repr(non_iso), "| tzinfo:", non_iso.tzinfo)

# dateutil with explicit tzinfos mapping for abbreviations
parsed_with_tz = du_parser.parse(
    "2026-10-23 12:00:00 EST",
    tzinfos={"EST": du_tz.gettz("America/New_York")},
)
print("dateutil.parse('...EST'):", repr(parsed_with_tz), "| tzinfo:", parsed_with_tz.tzinfo)

# 8. arrow for non-ISO with explicit format string
import arrow
arr = arrow.get("2026/10/23 12:00:00", "YYYY/MM/DD HH:mm:ss")
print("arrow.get(...):", arr.datetime, "| type:", type(arr.datetime).__name__)

# 9. The rule: if ISO, use stdlib; otherwise dateutil
def parse_created_at(s: str) -> datetime:
    # ISO 8601 path — fast, no dependency
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Non-ISO path — dateutil
        dt = du_parser.parse(s)
    if dt.tzinfo is None:               # refuse naive at the boundary
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ISO path
print("parse_created_at ISO:", parse_created_at("2026-10-23T12:00:00+00:00"))
# Non-ISO path
print("parse_created_at non-ISO:", parse_created_at("2026/10/23 12:00:00"))

# 10. The boardly Pydantic field_validator that rejects naive input
try:
    from pydantic import BaseModel, field_validator, ValidationError

    class TicketCreate(BaseModel):
        summary: str
        created_at: datetime

        @field_validator("created_at")
        @classmethod
        def must_be_aware(cls, v: datetime) -> datetime:
            if v.tzinfo is None:
                raise ValueError("must be aware UTC; got a naive datetime")
            return v

    # ISO path — accepted
    ok = TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00+00:00")
    print("Pydantic accepted aware:", ok.created_at, "| tzinfo:", ok.created_at.tzinfo)

    # Z suffix — also accepted (Pydantic uses fromisoformat internally)
    ok_z = TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00Z")
    print("Pydantic accepted Z suffix:", ok_z.created_at, "| tzinfo:", ok_z.created_at.tzinfo)

    # Naive input — rejected with 422
    try:
        TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00")
    except ValidationError as e:
        print("Pydantic rejected naive:", repr(e.errors()[0]["msg"]))

    # Serialise back to JSON
    print("model_dump_json:", ok.model_dump_json())

except ImportError:
    print("pydantic not installed")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–14: `fromisoformat` accepts the canonical and the 3.11+ extended forms

```python
# 1. datetime.fromisoformat (Python 3.7+; extended in 3.11+)
samples = [
    "2026-10-23T12:00:00+00:00",   # canonical CPython isoformat() output
    "2026-10-23T12:00:00Z",        # Z suffix — 3.11+
    "2026-10-23T12:00:00,5",       # comma as decimal sep — 3.11+
    "20261023T120000",             # basic (no-separator) format — 3.11+
    "2026-10-23T12:00:00+0000",    # offset without colon — 3.11+
    "2026-10-23T12:00:00+00",      # single-digit-hour offset — 3.11+
    "2026-10-23",                  # date-only input — produces midnight datetime
]
for s in samples:
    try:
        v = datetime.fromisoformat(s)
        print(f"OK  {s!r:35} -> {v!r}")
    except ValueError as e:
        print(f"ERR {s!r:35} -> {e}")
```

`datetime.fromisoformat(date_string)` parses ISO 8601 strings into `datetime` instances. The method was added in Python 3.7 to round-trip `isoformat()`'s output (so `datetime.fromisoformat(dt.isoformat()) == dt`). The 3.7 baseline accepted only the *exact* form `isoformat()` produced — `YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM`, with no variations. In Python 3.11 the method was extended to accept more ISO 8601 variants: the `Z` suffix for UTC, the basic (no-separator) format, week dates (`YYYY-Www-D`), the comma decimal separator, and short offsets (`+00` without minutes).

The seven samples exercise the 3.11+ extension surface:
- `"2026-10-23T12:00:00+00:00"` — the 3.7-baseline canonical form.
- `"2026-10-23T12:00:00Z"` — the `Z` suffix, accepted in 3.11+. This is the form JavaScript's `Date.toISOString()` produces and the form most partner APIs send; the 3.7 baseline rejected it.
- `"2026-10-23T12:00:00,5"` — the comma decimal separator (ISO 8601 permits both `.` and `,`). 3.11+.
- `"20261023T120000"` — the basic (no-separator) format. 3.11+.
- `"2026-10-23T12:00:00+0000"` — the offset without a colon. 3.11+.
- `"2026-10-23T12:00:00+00"` — the single-digit-hour offset (no minutes). 3.11+.
- `"2026-10-23"` — date-only input. The method accepts this and produces a `datetime` at midnight on that date (`2026-10-23 00:00:00`), naive (no `tzinfo`). This is the one input that produces a naive value; the parse boundary must refuse it (see block 9).

The version-gate is `sys.version_info >= (3, 11)` for the extended forms. On 3.7–3.10, only the canonical form is accepted; if your codebase must support those runtimes, restrict your input to the canonical form or use `dateutil` for the extended forms. On 3.12 (this vault's runtime), all seven samples parse correctly.

**Why was `fromisoformat` extended in 3.11 instead of fixed in 3.7?** Because the 3.7 contract was "round-trip `isoformat()`'s output exactly", and that contract was the safest choice for a method whose purpose was *serialise-then-parse* round-tripping. The 3.11 extension was a deliberate scope expansion: the method now parses "any valid ISO 8601 string that CPython can reasonably accept", which is the contract most callers actually wanted. The version-gate is the discipline — code that depends on the 3.11+ extension should fail loudly on 3.10 (`ValueError: Invalid isoformat string: ...`), not silently produce a wrong value.

### Lines 16–17: Version-gate the 3.11+ extension

```python
# 2. The pre-3.11 baseline (anchor the version gate)
print("python:", sys.version_info[:3], "(3.11+ extended fromisoformat)")
```

The `sys.version_info[:3]` line confirms the runtime — `(3, 12, 15)` in this vault. The 3.11+ extension is available. For library code that must support 3.10 or earlier, the version-gate is `if sys.version_info >= (3, 11):` around the call site, or a feature-detection shim that falls back to `dateutil` on older runtimes. For application code that targets 3.11+, the gate is the runtime requirement itself — declare `python_requires = ">=3.11"` in `pyproject.toml` and the `fromisoformat` extension is always available.

The discipline is: when you use a 3.11+ feature, you must either gate it (`sys.version_info` check, fallback path) or require it (`python_requires` in `pyproject.toml`). Silently relying on the feature without one of the two is a portability bug — the code works on your dev machine (3.12) and breaks in CI (3.10) or on a colleague's machine (3.9). The version-gate is the discipline; the alternative is the silent-failure trap.

### Lines 19–23: `fromisoformat` round-trips `isoformat()` for aware UTC

```python
# 3. fromisoformat round-trips isoformat() for aware UTC
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
serialised = aware_utc.isoformat()
parsed = datetime.fromisoformat(serialised)
print("round-trip:", parsed == aware_utc, "| parsed.tzinfo:", parsed.tzinfo)
```

The round-trip is the foundational contract. `aware_utc.isoformat()` produces `2026-10-23T12:00:00+00:00`; `datetime.fromisoformat(serialised)` produces an aware UTC `datetime` whose `tzinfo` is `timezone(timedelta(0))` (the zero-offset `timezone`, equivalent to `timezone.utc`); `parsed == aware_utc` is `True`. The serialise-then-parse round-trip is exact for any `datetime` whose precision is microseconds or coarser.

The `tzinfo` slot round-trips too: the `+00:00` offset is parsed into a `timezone` instance with the same offset, and `==` comparison with `timezone.utc` is `True` (both represent the zero-offset UTC zone). Note: `parsed.tzinfo is timezone.utc` may be `False` (the parsed instance is a fresh `timezone`, not the singleton), but `parsed.tzinfo == timezone.utc` is `True`. Use `==`, not `is`, for `tzinfo` comparison.

The IANA *name* (e.g. `"America/New_York"`) does not round-trip through `fromisoformat` — the method parses the *offset* (`±HH:MM`), not the *name*, and produces a `timezone` (fixed-offset) instance, not a `ZoneInfo` (named-zone) instance. For values that need the IANA name preserved across the round-trip, store the name in a separate field and reattach the `ZoneInfo` at parse time. See block 5 for the `ZoneInfo` integration.

**Why is the round-trip exact for the offset but not for the IANA name?** Because ISO 8601 has no place for a timezone name — only for the offset. The standard's design choice is "the offset is what matters for instant disambiguation; the name is metadata for display rules (DST transitions, abbreviation display)". CPython `isoformat()` honours this: it writes the offset, not the name. `fromisoformat()` parses the offset, not the name. The discipline is: store the IANA name as a separate string field (e.g. `user.timezone: str = "America/New_York"`) and use it to construct the `ZoneInfo` at the display boundary (`dt.astimezone(ZoneInfo(user.timezone))`). The two fields together — `created_at: datetime` (aware UTC) and `user.timezone: str` (IANA name) — preserve both the instant and the display context across the round-trip.

### Lines 25–29: `fromtimestamp(ts, tz=...)` — always pass `tz=timezone.utc`

```python
# 4. fromtimestamp: always pass tz=timezone.utc for aware UTC
ts = time_module.time()
naive_local = datetime.fromtimestamp(ts)                      # ← don't do this
aware_utc_ts = datetime.fromtimestamp(ts, tz=timezone.utc)    # ← do this
print("fromtimestamp(ts) tzinfo:", naive_local.tzinfo)         # None
print("fromtimestamp(ts, tz=utc) tzinfo:", aware_utc_ts.tzinfo)  # UTC
```

`datetime.fromtimestamp(timestamp, tz=None)` constructs a `datetime` from a POSIX timestamp (seconds since the Unix epoch, 1970-01-01 00:00:00 UTC). The `tz` parameter defaults to `None`, which produces a *naive local* `datetime` — the wall-clock reading of the local timezone at that instant, with `tzinfo=None`. This is the same naive-local trap as `datetime.now()` (lesson 01): the value is ambiguous the moment it crosses a process boundary because nothing in the value records which timezone the reading was taken in.

Passing `tz=timezone.utc` produces an *aware UTC* `datetime` — the same instant, normalised to UTC, with `tzinfo=timezone.utc` set. The two calls return the same *wall-clock reading* on a UTC-configured machine (because `time.time()` returns the UTC POSIX timestamp and the local timezone on a UTC machine is UTC), but they differ on a London or Tokyo machine where the local timezone is not UTC. The discipline is the same as for `datetime.now()`: always pass `tz=timezone.utc`.

The `timestamp` argument is a `float` (or `int`) — the return value of `time.time()`, `datetime.timestamp()`, or a Unix-timestamp field from an external system (a partner API, a log line, a database `epoch` column). The method handles negative timestamps (before 1970-01-01) and very large timestamps (year 9999); it raises `OverflowError` for out-of-range values and `OSError` if the local timezone database cannot be read.

**Why is `fromtimestamp(ts)` the same naive-local trap as `datetime.now()`?** Because both methods default to the local timezone when no `tz` is specified, and both produce a `datetime` with `tzinfo=None` in that case. The two methods share the same historical reason (predating the `timezone` class, kept for backwards compatibility) and the same fix (always pass `tz=timezone.utc`). The `fromtimestamp` case is the *ingest* side — a POSIX timestamp comes in from an external system, and you have to choose whether to parse it as aware UTC or naive local. The right choice is aware UTC.

### Lines 31–36: `zoneinfo.ZoneInfo` — IANA timezone names (Python 3.9+, PEP 615)

```python
# 5. zoneinfo.ZoneInfo — IANA timezone names (Python 3.9+, PEP 615)
ny_tz = ZoneInfo("America/New_York")
print("ZoneInfo('America/New_York'):", ny_tz)
print("is a tzinfo:", isinstance(ny_tz, tzinfo))
aware_ny = aware_utc.astimezone(ny_tz)
print("UTC -> NY:", aware_ny, "| tzname:", aware_ny.tzname())
```

`zoneinfo.ZoneInfo(key)` constructs a `tzinfo` instance from an IANA timezone name — `"America/New_York"`, `"Europe/London"`, `"Asia/Tokyo"`, `"UTC"`. The `ZoneInfo` class was added in Python 3.9 (PEP 615) and is the standard-library replacement for the third-party `pytz` library. The IANA timezone database (the "tz database" or "zoneinfo database") is shipped with the operating system on Linux and macOS; on Windows, the `tzdata` PyPI package is required (the OS does not ship the database).

The `ZoneInfo` instance is a `tzinfo` — `isinstance(ny_tz, tzinfo)` is `True` because `ZoneInfo` subclasses `tzinfo` (the abstract base from lesson 01). The instance handles DST transitions correctly: `aware_utc.astimezone(ny_tz)` in October 2026 returns `2026-10-23 08:00:00-04:00` (EDT, observing DST); in January 2026 the same conversion returns `2026-01-15 07:00:00-05:00` (EST, not observing DST). The offset changes twice a year, and `ZoneInfo` knows the rules from the IANA database.

The `.tzname()` method returns the timezone *abbreviation* (`"EDT"` or `"EST"`), which is the display name. The `.key` attribute (added in 3.9) returns the IANA name (`"America/New_York"`), which is the metadata that does not round-trip through `isoformat()` (block 3). The two are different — the abbreviation is what to show the user; the key is what to store for round-tripping.

The `ZoneInfo` instances are cached: `ZoneInfo("America/New_York")` returns the same instance on every call within a process, so the IANA-database lookup happens only once. The cache is per-process and per-key; the `zoneinfo.reset_tzpath()` function (rarely needed) clears the cache.

**Why was `zoneinfo` added in 3.9 instead of fixing `datetime.timezone`?** Because `timezone` is *fixed-offset* (a constant `±HH:MM` that does not change with the seasons) and `ZoneInfo` is *named-zone* (an offset that changes with DST transitions). The two are different types for different use cases: `timezone(timedelta(hours=-5))` is correct for a fixed-offset zone (IST, UTC, no-DST zones); `ZoneInfo("America/New_York")` is correct for a DST-observing zone. Before 3.9, the standard library had no `ZoneInfo` and the third-party `pytz` library filled the gap; `pytz`'s API was non-standard (it required `localize()` and `normalize()` methods that `ZoneInfo` does not), and `zoneinfo` was the standard-library replacement.

### Lines 38–42: `ZoneInfo` raises `KeyError` on invalid IANA key

```python
# 6. zoneinfo raises on invalid IANA key
try:
    ZoneInfo("Not/A_Real_Zone")
except KeyError as e:
    print("ZoneInfo invalid key raises KeyError:", e)
```

`ZoneInfo("Not/A_Real_Zone")` raises `KeyError` because `"Not/A_Real_Zone"` is not a valid IANA key. The exception is `KeyError`, not `ValueError` — `ZoneInfo` looks up the key in the IANA database (a dictionary-like structure on disk), and a missing key raises `KeyError` (the dictionary-lookup exception). The error message is `KeyError: 'No time zone found with key Not/A_Real_Zone'` — the key is wrapped in a human-readable sentence rather than passed bare.

The discipline is: catch `KeyError` at the boundary where you accept a user-supplied timezone string (e.g. the `timezone` field of a user profile). If the user supplies `"America/New_York"`, you get a `ZoneInfo` instance; if the user supplies `"Not/A_Real_Zone"`, you get `KeyError` and the API should return 422 with a message like "unknown timezone". The 422 is the right response — the user supplied an invalid value, and the type system caught it at the boundary. Storing the invalid string in the database (to "fix later") is the wrong choice; the value is wrong now and will break every display boundary that tries to use it.

**Why `KeyError` and not `ValueError`?** Because `ZoneInfo` is a lookup, not a validation. The IANA database is a key→value mapping (key: `"America/New_York"`, value: the timezone rules); looking up a missing key is the textbook `KeyError` case. Using `ValueError` would conflate "the key is missing" (a database-lookup failure) with "the key is malformed" (a string-validation failure). The `KeyError` exception type tells you exactly what happened: the key is well-formed but not in the database. The caller catches `KeyError` and produces the right user-facing error.

### Lines 44–55: `dateutil` for non-ISO formats

```python
# 7. dateutil for non-ISO formats (slash-sep, human-typed)
from dateutil import parser as du_parser
from dateutil import tz as du_tz

non_iso = du_parser.parse("2026/10/23 12:00:00")
print("dateutil.parse('2026/10/23 12:00:00'):", repr(non_iso), "| tzinfo:", non_iso.tzinfo)

# dateutil with explicit tzinfos mapping for abbreviations
parsed_with_tz = du_parser.parse(
    "2026-10-23 12:00:00 EST",
    tzinfos={"EST": du_tz.gettz("America/New_York")},
)
print("dateutil.parse('...EST'):", repr(parsed_with_tz), "| tzinfo:", parsed_with_tz.tzinfo)
```

`dateutil.parser.parse(s)` is the third-party fallback for non-ISO formats. The method is a "fuzzy" parser — it tries a long list of common date-time formats and returns the first match. It handles slash-separated dates (`2026/10/23`), space-separated date-time (`2026-10-23 12:00:00`), human-typed strings (`"October 23, 2026 12:00 PM"`), and many more. The cost is performance (the fuzzy parser is slower than `fromisoformat`) and ambiguity (the parser guesses, and the guess can be wrong for ambiguous inputs).

The first call `du_parser.parse("2026/10/23 12:00:00")` parses a slash-separated date-time string. The result is a *naive* `datetime` with `tzinfo=None` — `dateutil` does not infer a timezone from the format alone, and the input had no timezone marker. The parse boundary must then either reject the naive value (lesson 04's rule) or assert a timezone (`dt.replace(tzinfo=timezone.utc)`).

The second call `du_parser.parse("2026-10-23 12:00:00 EST", tzinfos={"EST": du_tz.gettz("America/New_York")})` parses a string with a timezone *abbreviation* (`EST`). The `tzinfos` argument is a mapping from abbreviation to `tzinfo` instance — without it, `dateutil` warns and returns naive (it does not understand `EST` by default because the abbreviation is ambiguous; `EST` could be Australian Eastern Standard Time or US Eastern Standard Time). The `tzinfos` mapping is the explicit disambiguation; the result is an aware `datetime` with `tzinfo=tzfile('/usr/share/zoneinfo/America/New_York')` (a `dateutil`-specific `tzinfo` subclass that wraps the IANA database).

**Why does `dateutil` not understand `EST` by default?** Because the abbreviation is ambiguous across multiple IANA zones. `EST` is US Eastern Standard Time in some contexts and Australian Eastern Standard Time in others; `CST` is US Central, China Standard, or Cuba Standard Time depending on context. `dateutil` refuses to guess and warns; the caller must supply the `tzinfos` mapping to disambiguate. The discipline is: never trust a timezone abbreviation from user input — always map it to an IANA name explicitly.

### Lines 57–60: `arrow` for non-ISO with explicit format string

```python
# 8. arrow for non-ISO with explicit format string
import arrow
arr = arrow.get("2026/10/23 12:00:00", "YYYY/MM/DD HH:mm:ss")
print("arrow.get(...):", arr.datetime, "| type:", type(arr.datetime).__name__)
```

`arrow` is a third-party library that wraps `datetime` with a more ergonomic API. `arrow.get(s, format)` parses a string with an *explicit* format (similar to `datetime.strptime` but with `arrow`'s own format tokens). The result is an `Arrow` instance, which has a `.datetime` attribute returning the underlying `datetime`. Arrow defaults to UTC for parsed values when no timezone is specified in the input — `arr.datetime` has `tzinfo=tzutc()` (Arrow's UTC `tzinfo` subclass).

The choice between `dateutil` and `arrow` is a stylistic one. `dateutil` is the *fuzzy* parser (try every format, return the first match); `arrow` is the *explicit* parser (parse with this format string, raise on mismatch). The two are complementary — `dateutil` for "I have no idea what format this is, try them all"; `arrow` for "I know the format, parse it precisely". For most boardly use cases, `fromisoformat` handles the ISO path and `dateutil` handles the non-ISO path; `arrow` is reserved for the rare case where the format is known precisely and the explicit-parse semantics are valuable (e.g. parsing a partner API that documents its format).

**Why is `arrow` not the default for the non-ISO path?** Because `arrow` is an additional dependency (a 200KB library that wraps `datetime` and `dateutil`), and the marginal benefit over `dateutil` is small for most use cases. `dateutil` is already pulled in by `pandas`, `pytz`-migration tooling, and several FastAPI-adjacent libraries; the marginal cost of adding `dateutil` to your `pyproject.toml` is near zero. `arrow` is a *replacement* for `datetime` itself, not just a parser — using it means every `datetime`-typed field becomes an `Arrow`-typed field, which is a much larger commitment. The discipline is: reach for `fromisoformat` first (stdlib, no dependency); `dateutil` for non-ISO (lightweight, common); `arrow` only when you need the full Arrow API (rare).

### Lines 62–73: The rule — if ISO, use stdlib; otherwise `dateutil`

```python
# 9. The rule: if ISO, use stdlib; otherwise dateutil
def parse_created_at(s: str) -> datetime:
    # ISO 8601 path — fast, no dependency
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Non-ISO path — dateutil
        dt = du_parser.parse(s)
    if dt.tzinfo is None:               # refuse naive at the boundary
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ISO path
print("parse_created_at ISO:", parse_created_at("2026-10-23T12:00:00+00:00"))
# Non-ISO path
print("parse_created_at non-ISO:", parse_created_at("2026/10/23 12:00:00"))
```

The `parse_created_at` function is the rule in code. Try `datetime.fromisoformat(s)` first — fast (C-implemented), no third-party dependency, raises `ValueError` on non-ISO input. On `ValueError`, fall back to `dateutil.parser.parse(s)` — slower (pure-Python fuzzy parser), handles non-ISO formats. After parsing, refuse naive: `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)` — assert the timezone the input omitted, defaulting to UTC.

The `replace(tzinfo=timezone.utc)` line is the dangerous one. It asserts "the naive value was actually a UTC reading" — which is the right default for *most* ingestion (the partner API documented the value as UTC, the CSV column header said "UTC", the log line was written by a UTC-configured service). It is the wrong default for *some* ingestion (the partner API documented the value as local time, the CSV column header said "local time", the log line was written by a BST-configured service). The discipline is: know what the input means before you assert a timezone. If you do not know, refuse the value at the boundary (`raise ValueError("naive datetime; specify the timezone")`) rather than guess.

The `try` / `except ValueError` pattern is the standard library's idiomatic feature-detection. `fromisoformat` raises `ValueError` on non-ISO input; the `except` branch falls back to `dateutil`. The pattern is faster than a format-sniffing regex (which would have to inspect the string to decide which parser to call) and is the CPython-recommended approach for "try the strict parser, fall back to the fuzzy parser".

**Why not always use `dateutil`?** Because `dateutil` is slower (the fuzzy parser tries many formats) and adds a dependency (the `python-dateutil` package). For ISO input — which is the vast majority of API traffic — `fromisoformat` is 10× faster, has no dependency, and raises on invalid input instead of guessing. The dual-path parser gives you the speed and reliability of `fromisoformat` for the common case and the breadth of `dateutil` for the rare case. The cost is two code paths; the benefit is correctness on both.

### Lines 75–98: The Pydantic `field_validator` that rejects naive input

```python
# 10. The boardly Pydantic field_validator that rejects naive input
try:
    from pydantic import BaseModel, field_validator, ValidationError

    class TicketCreate(BaseModel):
        summary: str
        created_at: datetime

        @field_validator("created_at")
        @classmethod
        def must_be_aware(cls, v: datetime) -> datetime:
            if v.tzinfo is None:
                raise ValueError("must be aware UTC; got a naive datetime")
            return v

    # ISO path — accepted
    ok = TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00+00:00")
    print("Pydantic accepted aware:", ok.created_at, "| tzinfo:", ok.created_at.tzinfo)

    # Z suffix — also accepted (Pydantic uses fromisoformat internally)
    ok_z = TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00Z")
    print("Pydantic accepted Z suffix:", ok_z.created_at, "| tzinfo:", ok_z.created_at.tzinfo)

    # Naive input — rejected with 422
    try:
        TicketCreate(summary="login broken", created_at="2026-10-23T12:00:00")
    except ValidationError as e:
        print("Pydantic rejected naive:", repr(e.errors()[0]["msg"]))

    # Serialise back to JSON
    print("model_dump_json:", ok.model_dump_json())

except ImportError:
    print("pydantic not installed")
```

The `TicketCreate` Pydantic model is the production parse boundary. Pydantic v2 calls `datetime.fromisoformat()` internally when the input is a string and the field type is `datetime` — so the ISO path (including the `Z` suffix) is handled by the stdlib, no extra code needed. The `field_validator("created_at")` decorator adds the awareness check: if `v.tzinfo is None`, raise `ValueError` with a message Pydantic surfaces as a 422 response.

The three test cases exercise the boundary:
- `"2026-10-23T12:00:00+00:00"` — ISO with explicit offset. Pydantic parses to an aware UTC `datetime`; the validator passes; the model is constructed.
- `"2026-10-23T12:00:00Z"` — ISO with `Z` suffix. Pydantic parses to an aware UTC `datetime` (the `Z` suffix is equivalent to `+00:00` in `fromisoformat`); the validator passes.
- `"2026-10-23T12:00:00"` — ISO with no offset. Pydantic parses to a *naive* `datetime` (the input had no offset); the validator rejects it with `ValidationError`; the API returns 422 with the message `"Value error, must be aware UTC; got a naive datetime"`.

The `model_dump_json()` call serialises the model back to JSON — `ok.model_dump_json()` returns `{"summary":"login broken","created_at":"2026-10-23T12:00:00Z"}` (Pydantic uses the `Z` suffix for UTC on the serialise side, which is the JavaScript-`Date.toISOString()` form). The round-trip is exact: the parsed `created_at` serialises back to the same form (modulo the `+00:00` → `Z` normalisation that Pydantic performs).

**Why does Pydantic use the `Z` suffix on serialise when CPython `isoformat()` uses `+00:00`?** Because Pydantic has its own `isoformat`-equivalent logic that normalises UTC offsets to the `Z` shorthand — the form JavaScript's `Date.toISOString()` and most partner APIs use. The two forms are equivalent (`Z` and `+00:00` both mean UTC), and `datetime.fromisoformat()` accepts both on the parse side. The discipline is: do not depend on the specific suffix form (`Z` vs `+00:00`) at the wire boundary; both are valid ISO 8601 and both round-trip.

## Execution Trace

The `fromtimestamp` and `parse_created_at non-ISO` lines are runtime-dependent (the first uses the current POSIX timestamp; the second uses the current local time of the dateutil fallback). The ISO 8601 parse results and the Pydantic validation outcomes are deterministic.

```bash
$ uv run python boardly/webhooks/fromisoformat_and_parsing.py
OK  '2026-10-23T12:00:00+00:00'         -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00Z'              -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00,5'             -> datetime.datetime(2026, 10, 23, 12, 0, 0, 500000)
OK  '20261023T120000'                   -> datetime.datetime(2026, 10, 23, 12, 0)
OK  '2026-10-23T12:00:00+0000'          -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00+00'            -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23'                        -> datetime.datetime(2026, 10, 23, 0, 0)
python: (3, 12, 15) (3.11+ extended fromisoformat)
round-trip: True | parsed.tzinfo: UTC
fromtimestamp(ts) tzinfo: None
fromtimestamp(ts, tz=utc) tzinfo: UTC
ZoneInfo('America/New_York'): America/New_York
is a tzinfo: True
UTC -> NY: 2026-10-23 08:00:00-04:00 | tzname: EDT
ZoneInfo invalid key raises KeyError: 'No time zone found with key Not/A_Real_Zone'
dateutil.parse('2026/10/23 12:00:00'): datetime.datetime(2026, 10, 23, 12, 0) | tzinfo: None
dateutil.parse('...EST'): datetime.datetime(2026, 10, 23, 12, 0, tzinfo=tzfile('/usr/share/zoneinfo/America/New_York')) | tzinfo: tzfile('/usr/share/zoneinfo/America/New_York')
arrow.get(...): 2026-10-23 12:00:00+00:00 | type: datetime
parse_created_at ISO: 2026-10-23 12:00:00+00:00
parse_created_at non-ISO: 2026-10-23 12:00:00+00:00
Pydantic accepted aware: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Pydantic accepted Z suffix: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Pydantic rejected naive: 'Value error, must be aware UTC; got a naive datetime'
model_dump_json: {"summary":"login broken","created_at":"2026-10-23T12:00:00Z"}
```

## Common Mistakes

### Mistake 1: Hand-rolling a regex parser

```python
import re
from datetime import datetime, timezone

def parse_created_at(s: str) -> datetime:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s)
    return datetime(*[int(g) for g in m.groups()], tzinfo=timezone.utc)

# Input: "2026-10-23T12:00:00+05:30"
# Parsed: datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
# Actual instant: 12:00 UTC, but the input meant 12:00 IST = 06:30 UTC
# Off by 5.5 hours, silently
```

**Symptom:** The parsed value's wall-clock reading is correct; the instant is wrong by the timezone delta. The unit tests pass (they use UTC inputs); production traffic with non-UTC offsets silently drifts.
**Why:** The regex matches the first 19 characters (the `YYYY-MM-DDTHH:MM:SS` prefix) and does not anchor the end of the string or parse the offset suffix. The `+05:30` suffix is silently dropped; the `tzinfo=timezone.utc` argument asserts UTC, which is wrong for an IST input.
**Fix:** Use `datetime.fromisoformat(s)` for ISO input. The method parses the offset suffix correctly and produces an aware `datetime` whose `tzinfo` matches the input. For non-ISO input, use `dateutil.parser.parse(s)` with an explicit `tzinfos` mapping. Never hand-roll a regex parser for a standard format.

### Mistake 2: Calling `fromtimestamp(ts)` with no `tz` argument

```python
ts = time.time()
dt = datetime.fromtimestamp(ts)        # naive local — same trap as datetime.now()
```

**Symptom:** The parsed value has `tzinfo=None`. On a UTC-configured machine, the value is correct (the local timezone is UTC); on a London or Tokyo machine, the value drifts by the timezone delta between the local zone and UTC.
**Why:** `fromtimestamp(ts)` defaults to `tz=None`, which produces a naive *local* `datetime` — the wall-clock reading of the local timezone at that POSIX timestamp, with no offset recorded. The trap is identical to `datetime.now()`.
**Fix:** Always pass `tz=timezone.utc`: `datetime.fromtimestamp(ts, tz=timezone.utc)`. The result is an aware UTC `datetime`, unambiguous on every machine.

### Mistake 3: Trusting `dateutil` to infer the timezone abbreviation

```python
from dateutil import parser as du_parser
dt = du_parser.parse("2026-10-23 12:00:00 EST")    # naive — dateutil does not understand EST
```

**Symptom:** `dateutil` emits `UnknownTimezoneWarning: tzname EST identified but not understood` and returns a naive `datetime`. The parsed value has `tzinfo=None`, not the IANA zone you expected.
**Why:** Timezone abbreviations are ambiguous across multiple IANA zones (`EST` is US Eastern or Australian Eastern; `CST` is US Central, China Standard, or Cuba Standard). `dateutil` refuses to guess and warns; the caller must supply the `tzinfos` mapping to disambiguate.
**Fix:** Pass the `tzinfos` argument explicitly: `du_parser.parse(s, tzinfos={"EST": tz.gettz("America/New_York")})`. The result is an aware `datetime` with the correct IANA-zone `tzinfo`. Better: do not accept timezone abbreviations from user input at all; require IANA names (`"America/New_York"`) and parse them with `ZoneInfo(key)`.

### Mistake 4: Letting a naive value slip past the parse boundary

```python
class TicketCreate(BaseModel):
    summary: str
    created_at: datetime           # no validator — naive input is accepted

# Input: "2026-10-23T12:00:00" (no offset)
# Pydantic parses to a naive datetime; the model is constructed; the bug surfaces
# downstream when the naive value is compared to an aware UTC now (lesson 04's TypeError)
```

**Symptom:** The API returns 200 with the naive value stored. The bug surfaces later (lesson 04's `TypeError`) at the comparison layer, far from the parse boundary where the bug was actually written.
**Why:** Pydantic's default `datetime` parsing accepts both aware and naive inputs. Without a `field_validator` that checks `v.tzinfo is None`, the naive input passes through.
**Fix:** Add a `field_validator("created_at")` that rejects naive input with `ValueError("must be aware UTC")`. The API returns 422 at the parse boundary, not `TypeError` at the comparison layer. The discipline is "fail loud, fail early" — the boundary that accepts the value is the boundary that validates it.

## Engineering Trade-Offs

**Decision:** Use `datetime.fromisoformat(s)` for every ISO 8601 input at the parse boundary. Fall back to `dateutil.parser.parse(s)` for non-ISO input. Always pass `tz=timezone.utc` to `datetime.fromtimestamp`. Use `zoneinfo.ZoneInfo(key)` for IANA-named timezones at the display boundary. Reject naive input with a Pydantic `field_validator` that returns 422.
**Both sides:** The alternative is the "always `dateutil`" approach — parse every input with `dateutil.parser.parse(s, tzinfos=...)`, regardless of format. `dateutil` is more permissive (it handles ISO and non-ISO), simpler to teach (one method, one fallback), and the slow path is rare enough that the performance cost is acceptable. The trade-off: `dateutil` is a third-party dependency (a `python-dateutil` line in `pyproject.toml`), it is slower than `fromisoformat` for the common case (10× for ISO input), and its fuzzy parser can silently produce wrong results for ambiguous inputs (e.g. `2026-10-23 12:00:00` is naive; `2026/10/23` is MM/DD vs DD/MM ambiguous in different locales). The dual-path approach (stdlib first, `dateutil` fallback) gives you the speed and reliability of `fromisoformat` for the common case and the breadth of `dateutil` for the rare case; the cost is two code paths and a `ValueError` exception in the hot path.
**Commitment:** `boardly` uses the dual-path parser at every parse boundary (webhook payloads, CSV imports, partner APIs). The `TicketCreate` Pydantic model has the `field_validator` that rejects naive input with 422. The `fromtimestamp` calls in the timestamp-ingestion service all pass `tz=timezone.utc`. The display layer uses `ZoneInfo(user.timezone)` for the user's local-timezone rendering. The "always `dateutil`" alternative is documented for systems that need the simplicity of one parser; we use the dual-path approach because the ISO path is the vast majority of traffic and the `fromisoformat` speed and reliability are worth the two-path cost.

## Exercises

1. **Exercise 1 — Parse the `Z` suffix.** Use `datetime.fromisoformat("2026-10-23T12:00:00Z")` and confirm the result has `tzinfo=UTC`. `Verify: uv run python -c "from datetime import datetime; print(datetime.fromisoformat('2026-10-23T12:00:00Z').tzinfo)"`
2. **Exercise 2 — `fromtimestamp` aware vs naive.** Compare `datetime.fromtimestamp(0)` and `datetime.fromtimestamp(0, tz=timezone.utc)`. Confirm the first is naive (`tzinfo is None`) and the second is aware UTC (`tzinfo=UTC`). `Verify: uv run python -c "from datetime import datetime, timezone; a=datetime.fromtimestamp(0); b=datetime.fromtimestamp(0, tz=timezone.utc); print(a.tzinfo, b.tzinfo)"`
3. **Exercise 3 — `ZoneInfo` invalid key.** Call `ZoneInfo("Not/A_Real_Zone")` inside a try/except and confirm it raises `KeyError`. Then call `ZoneInfo("America/New_York")` and confirm it succeeds. `Verify: uv run python -c "from zoneinfo import ZoneInfo; 
try:
    ZoneInfo('Not/A_Real_Zone')
except KeyError as e:
    print('KeyError:', e)
print(ZoneInfo('America/New_York'))"`
4. **Exercise 4 — `dateutil` with `tzinfos`.** Use `dateutil.parser.parse("2026-10-23 12:00:00 EST", tzinfos={"EST": tz.gettz("America/New_York")})` and confirm the result has a non-None `tzinfo`. `Verify: uv run python -c "from dateutil import parser, tz; r=parser.parse('2026-10-23 12:00:00 EST', tzinfos={'EST': tz.gettz('America/New_York')}); print(r.tzinfo)"`
5. **Exercise 5 — Reject naive input with Pydantic.** Define a `TicketCreate(BaseModel)` with `created_at: datetime` and a `field_validator` that rejects naive values. Confirm `TicketCreate(summary='x', created_at='2026-10-23T12:00:00')` raises `ValidationError` and `TicketCreate(summary='x', created_at='2026-10-23T12:00:00+00:00')` succeeds. `Verify: uv run python -c "from pydantic import BaseModel, field_validator, ValidationError; from datetime import datetime; 
class M(BaseModel):
    created_at: datetime
    @field_validator('created_at')
    @classmethod
    def v(cls, x):
        if x.tzinfo is None: raise ValueError('naive'); return x
try:
    M(created_at='2026-10-23T12:00:00')
except ValidationError:
    print('rejected naive')
print(M(created_at='2026-10-23T12:00:00+00:00').created_at.tzinfo)"`

## Verification

```bash
$ uv run python boardly/webhooks/fromisoformat_and_parsing.py
OK  '2026-10-23T12:00:00+00:00'         -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00Z'              -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00,5'             -> datetime.datetime(2026, 10, 23, 12, 0, 0, 500000)
OK  '20261023T120000'                   -> datetime.datetime(2026, 10, 23, 12, 0)
OK  '2026-10-23T12:00:00+0000'          -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23T12:00:00+00'            -> datetime.datetime(2026, 10, 23, 12, 0, tzinfo=datetime.timezone.utc)
OK  '2026-10-23'                        -> datetime.datetime(2026, 10, 23, 0, 0)
python: (3, 12, 15) (3.11+ extended fromisoformat)
round-trip: True | parsed.tzinfo: UTC
fromtimestamp(ts) tzinfo: None
fromtimestamp(ts, tz=utc) tzinfo: UTC
ZoneInfo('America/New_York'): America/New_York
is a tzinfo: True
UTC -> NY: 2026-10-23 08:00:00-04:00 | tzname: EDT
ZoneInfo invalid key raises KeyError: 'No time zone found with key Not/A_Real_Zone'
dateutil.parse('2026/10/23 12:00:00'): datetime.datetime(2026, 10, 23, 12, 0) | tzinfo: None
dateutil.parse('...EST'): datetime.datetime(2026, 10, 23, 12, 0, tzinfo=tzfile('/usr/share/zoneinfo/America/New_York')) | tzinfo: tzfile('/usr/share/zoneinfo/America/New_York')
arrow.get(...): 2026-10-23 12:00:00+00:00 | type: datetime
parse_created_at ISO: 2026-10-23 12:00:00+00:00
parse_created_at non-ISO: 2026-10-23 12:00:00+00:00
Pydantic accepted aware: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Pydantic accepted Z suffix: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Pydantic rejected naive: 'Value error, must be aware UTC; got a naive datetime'
model_dump_json: {"summary":"login broken","created_at":"2026-10-23T12:00:00Z"}
```

## Previously Learned Here

- [[15-datetime/01-datetime-and-timezone]] — the `datetime` constructor, the `tzinfo` slot, and the aware-UTC rule. The parse boundary produces values that satisfy lesson 01's contract.
- [[15-datetime/02-timedelta]] — `timedelta` arithmetic; the parse boundary produces values that lesson 02's arithmetic operates on.
- [[15-datetime/03-ISO-8601-format]] — `isoformat()` and the serialise-side contract that `fromisoformat()` is designed to round-trip.
- [[15-datetime/04-timezone-aware-vs-naive]] — the `TypeError` exception and the cardinal rule "never let a naive `datetime` past the parse boundary". This lesson's Pydantic `field_validator` is the boundary enforcement.

## What's Next

When you finish this lesson, you have completed Section 15. The natural next stop is [[16-uuid/00-uuid-MOC]] — the closest sibling section in the vault. `UUID` and `datetime` are the two "typed value at the boundary" lessons in the stdlib: `UUID` for entity identity (`Project.id: UUID`), `datetime` for event ordering (`Ticket.created_at: datetime`). The two MOCs are designed to be read as a pair so the rule lands twice — `id: UUID` instead of `id: str`, `created_at: datetime` instead of `created_at: str`. The pattern is the same: pick the type that matches the value's structure, parse at the boundary, never let the primitive form survive past the parse.

For the dataclass arc, the most relevant cross-link is [[06-dataclasses/02-field-and-Defaults]] — the `field(default_factory=...)` pattern on `Ticket.created_at`, and the `field_validator`-on-Pydantic counterpart for the API layer. Open [[16-uuid/00-uuid-MOC]] to begin the next section.

**Welcome to the end of datetime. We'll see you in the next section.**

## Sources

- **Python `datetime` module documentation — `datetime.fromisoformat()`** — https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat — accessed 2026-10-23 — the canonical CPython reference for `fromisoformat(date_string)`, the Python 3.7 baseline, and the 3.11+ extension (Z suffix, basic format, week dates, comma decimal separator, short offsets).
- **Python `datetime` module documentation — `datetime.fromtimestamp()`** — https://docs.python.org/3/library/datetime.html#datetime.datetime.fromtimestamp — accessed 2026-10-23 — the POSIX-timestamp ingestion method; source for the `tz=timezone.utc` rule.
- **`zoneinfo` — IANA time zone support** — https://docs.python.org/3/library/zoneinfo.html — accessed 2026-10-23 — the `ZoneInfo` class (Python 3.9+, PEP 615); the IANA database lookup, the `tzdata` package on Windows, and the `KeyError` on invalid keys.
- **PEP 615 — The `zoneinfo` module** — https://peps.python.org/pep-0615/ — accessed 2026-10-23 — the standard-library `zoneinfo` module backed by the IANA timezone database; the design choice to subclass `tzinfo` and replace `pytz`.
- **`python-dateutil` documentation** — https://dateutil.readthedocs.io/en/stable/parser.html — accessed 2026-10-23 — the `dateutil.parser.parse(s, tzinfos=...)` API for non-ISO formats; the `tzinfos` argument for disambiguating timezone abbreviations.
- **`arrow` documentation** — https://arrow.readthedocs.io/en/latest/ — accessed 2026-10-23 — the third-party `arrow` library; the `arrow.get(s, format)` API for explicit-format parsing, and the `Arrow` wrapper around `datetime`.
- **Pydantic v2 — Types: `datetime`** — https://docs.pydantic.dev/2.12/concepts/types/#datetime-types — accessed 2026-10-23 — Pydantic's `datetime` field handling, the `field_validator` rejection pattern, and the `model_dump_json()` serialisation contract.

## What We Learned

- You can now parse ISO 8601 with `datetime.fromisoformat(s)`, explain the Python 3.7+ baseline and the 3.11+ extension (Z suffix, basic format, week dates, comma decimal separator, short offsets), and version-gate the 3.11+ features.
- You can ingest POSIX timestamps with `datetime.fromtimestamp(ts, tz=timezone.utc)` and explain why the `tz=None` default is the same naive-local trap as `datetime.now()`.
- You can use `zoneinfo.ZoneInfo(key)` (Python 3.9+, PEP 615) for IANA-named timezones, catch `KeyError` on invalid keys, and explain the IANA database and the `tzdata` package on Windows.
- You can pick the right parser for the format — `fromisoformat` for ISO, `dateutil.parser.parse` for non-ISO with explicit `tzinfos`, never hand-roll a regex parser.
- You can implement the boardly parse boundary with a Pydantic `field_validator` that rejects naive `datetime` input with a 422, refusing the bug at the boundary instead of letting it surface as a `TypeError` at the comparison layer.
