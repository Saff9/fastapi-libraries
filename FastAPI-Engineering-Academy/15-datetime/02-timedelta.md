---
title: "Lesson 02: timedelta"
aliases:
 - timedelta
 - datetime.timedelta
 - total_seconds
 - timedelta floor division
tags:
 - datetime
 - python-stdlib
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "25–35 minutes"
prerequisites:
 - "[[15-datetime/01-datetime-and-timezone]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[15-datetime/01-datetime-and-timezone]]"
 - "[[15-datetime/03-ISO-8601-format]]"
---

# Lesson 02: timedelta

*Why `boardly`'s SLA window is `Ticket.created_at + timedelta(hours=24)` and never `created_at + 86400` — and the `weeks` → `days` → `seconds` normalisation that catches every "off by a week" bug before it ships.*

**You're at the very beginning of Section 15, Lesson 02.**

You can construct an aware UTC `datetime` now — that was lesson 01. But you cannot yet answer the question "how long until this ticket breaches its SLA?", because that question is *arithmetic*: a `datetime` minus a `datetime` produces a duration, and a `datetime` plus a duration produces a new `datetime`. The duration type is `datetime.timedelta`, and it has a normalisation rule that surprises every senior engineer the first time they hit it — `timedelta(weeks=1)` is `7 days` is `604800 seconds` is `604800000000 microseconds`, all stored as the *same* three-attribute internal form. This lesson walks `timedelta` end to end: the seven-argument constructor, the normalisation, the arithmetic, `total_seconds()`, and the floor-division operator that lets you count "how many hours apart are these two events". Take your time. Type every example. **This is how you learn.**

#datetime #timedelta

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `timedelta`** — write `timedelta(weeks=1, days=2, hours=3)` and explain the seven keyword arguments (`weeks`, `days`, `hours`, `minutes`, `seconds`, `milliseconds`, `microseconds`).
2. **Read the normalisation** — explain why `timedelta(weeks=1, days=2, hours=3)` internally stores only `days=9`, `seconds=10800`, `microseconds=0`, and how `weeks` and `hours` and `minutes` collapse into the three canonical fields.
3. **Do `datetime` arithmetic** — `dt + timedelta(hours=1)` for "an hour later", `dt1 - dt2` for the duration between two instants, and explain why the result of `dt1 - dt2` is a `timedelta` not a `datetime`.
4. **Read `.total_seconds()`** — explain why `total_seconds()` returns a `float` and not an `int`, and when the floating-point representation matters.
5. **Use the `//` and `%` operators** — `timedelta // timedelta(hours=1)` for floor-division counting (Python 3.2+), `timedelta % timedelta(...)` for the remainder, and explain when each is the right tool.

## Prerequisites

Before starting, you need:

- **The `datetime` constructor and aware UTC** — [[15-datetime/01-datetime-and-timezone]]. This lesson does arithmetic on `datetime` values; you need to be comfortable constructing an aware UTC `datetime` first.
- **A typed model** — [[06-dataclasses/01-dataclass-Basics]]. The running example is the `boardly` `Ticket` model with `created_at: datetime`.
- **About 25–35 minutes of focused time.**

**The most common gap: thinking `timedelta` stores every unit you pass to it.**

It does not. The single biggest mistake students make with `timedelta` is passing `weeks=1, days=2, hours=3, minutes=30` and being surprised that `td.days` returns `9` (not `1`), `td.seconds` returns `12600` (not `3`), and there is no `td.weeks` or `td.hours` attribute at all. `timedelta` normalises *everything* into three internal fields — `days`, `seconds` (0–86399), `microseconds` (0–999999) — and the seven constructor keyword arguments are convenience aliases for *input*, not for *storage*. The normalisation is what makes `timedelta(weeks=1) == timedelta(days=7)` true and what makes the comparison `timedelta(days=1) > timedelta(hours=23)` work without you having to convert units. The fix is to stop expecting `td.hours` to exist; read `td.days`, `td.seconds`, and `td.microseconds` directly, or call `.total_seconds()` for the single scalar.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/slas/bad_sla.py — the bad old days
from datetime import datetime, timedelta

# An SLA window of 24 hours after creation
def sla_deadline(created_at: datetime) -> datetime:
    return created_at + 86400       # ← int, not timedelta; TypeError

# A "week from now" calculation
def week_from_now(dt: datetime) -> datetime:
    return dt + timedelta(seconds=604800)   # ← works, but unreadable
```

The first function tries to add the bare `int` `86400` to a `datetime` and raises `TypeError: unsupported operand type(s) for +: 'datetime.datetime' and 'int'`. Python's type system correctly refuses to silently convert an integer count of seconds into a duration, because there is no marker on the integer that says "this is seconds, not milliseconds, not microseconds". The fix is to add a `timedelta(seconds=86400)` — a value whose *type* records the unit, not just whose name does.

The second function works but is unreadable. `604800` is the number of seconds in a week, but the only way to know that is to divide by 60, divide by 60 again, divide by 24, divide by 7 — or recognise the constant. Six months later you will not recognise it; you will write `timedelta(seconds=604800)` and three months after that you will write `timedelta(weeks=1)`, which is the same value, type-readable, and the form the rest of the section uses.

`timedelta` is the standard-library answer to "I need a duration that carries its own unit, that normalises across unit boundaries, and that arithmetic on `datetime` values just works". The constructor takes seven keyword arguments (`weeks`, `days`, `hours`, `minutes`, `seconds`, `milliseconds`, `microseconds`), normalises them into `days`/`seconds`/`microseconds` internally, and supports `+`/`-` with `datetime`, `-` between two `datetime` values, `*` and `/` by scalars, `//` and `%` by another `timedelta`, and the `total_seconds()` method that returns the duration as a single `float`.

## The Code

```python
# boardly/slas/timedelta_basics.py
"""The timedelta type, the seven-argument constructor, the normalisation
into days/seconds/microseconds, datetime arithmetic, total_seconds(),
and the // floor-division operator."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


# 1. The constructor accepts seven keyword arguments
td_full = timedelta(
    weeks=1, days=2, hours=3, minutes=4, seconds=5,
    milliseconds=6, microseconds=7,
)
print("td_full:", td_full)
print("td_full.days:", td_full.days)
print("td_full.seconds:", td_full.seconds)
print("td_full.microseconds:", td_full.microseconds)

# 2. Normalisation: weeks -> days, hours/minutes/seconds -> seconds, ms -> microseconds
td_weeks = timedelta(weeks=1)
print("timedelta(weeks=1).days:", td_weeks.days)               # 7
print("timedelta(weeks=1).seconds:", td_weeks.seconds)         # 0
print("timedelta(weeks=1) == timedelta(days=7):", td_weeks == timedelta(days=7))

# 3. The gotcha: hours/minutes collapse into .seconds (not .hours)
td_hours = timedelta(hours=25)
print("timedelta(hours=25).days:", td_hours.days)              # 1
print("timedelta(hours=25).seconds:", td_hours.seconds)       # 3600 (one hour)

# 4. Arithmetic: datetime + timedelta -> datetime
created = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
sla = created + timedelta(hours=24)
print("created + 24h:", sla)
print("type:", type(sla).__name__)

# 5. Subtraction: datetime - datetime -> timedelta
later = datetime(2026, 10, 24, 14, 30, 0, tzinfo=timezone.utc)
delta = later - created
print("later - created:", delta)
print("type:", type(delta).__name__)
print("total_seconds:", delta.total_seconds())

# 6. total_seconds() returns a float (with sub-microsecond precision possible)
print("total_seconds type:", type(delta.total_seconds()).__name__)

# 7. Floor-division: timedelta // timedelta -> int (Python 3.2+)
hours_apart = delta // timedelta(hours=1)
print("hours_apart (floor):", hours_apart)
remainder = delta % timedelta(hours=1)
print("remainder:", remainder)

# 8. The boardly Ticket model with an SLA window
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def sla_breach_at(self, window: timedelta = timedelta(hours=24)) -> datetime:
        return self.created_at + window

    def is_overdue(self, now: datetime, window: timedelta = timedelta(hours=24)) -> bool:
        return now > self.created_at + window


t = Ticket(id=1, summary="login broken")
now = t.created_at + timedelta(hours=25)          # 1 hour past SLA
print("SLA breach at:", t.sla_breach_at())
print("is_overdue (25h later):", t.is_overdue(now))

# 9. Scalar multiplication and division
half_day = timedelta(hours=12) * 0.5
print("half_day:", half_day, "| type:", type(half_day).__name__)
hour_in_seconds = timedelta(hours=1) / 2
print("hour / 2:", hour_in_seconds)
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–12: The seven-argument constructor and the three-attribute readout

```python
# 1. The constructor accepts seven keyword arguments
td_full = timedelta(
    weeks=1, days=2, hours=3, minutes=4, seconds=5,
    milliseconds=6, microseconds=7,
)
print("td_full:", td_full)
print("td_full.days:", td_full.days)
print("td_full.seconds:", td_full.seconds)
print("td_full.microseconds:", td_full.microseconds)
```

The constructor signature is `timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)`. The arguments can be `int` or `float`, positive or negative, and any combination of them is allowed. The two positional arguments are `days` and `seconds` (so `timedelta(1, 30)` means `days=1, seconds=30`); the rest are keyword-only in practice though not enforced by `*`. The seven units are: `weeks` (7 days each), `days` (24 hours each), `hours` (60 minutes each), `minutes` (60 seconds each), `seconds` (1000 milliseconds each), `milliseconds` (1000 microseconds each), `microseconds` (the atomic unit).

The three `print` calls expose the only three attributes a `timedelta` instance actually has: `.days` (an `int`), `.seconds` (an `int` in `0..86399`), and `.microseconds` (an `int` in `0..999999`). There is no `.weeks`, no `.hours`, no `.minutes`, no `.milliseconds` — they were *inputs* to the constructor, not *attributes* of the result. The constructor's job is to take the seven inputs and normalise them into the three internal fields; the instance exposes only the canonical normalised form.

For `td_full = timedelta(weeks=1, days=2, hours=3, minutes=4, seconds=5, milliseconds=6, microseconds=7)`, the normalisation produces `.days=9` (7 from the week + 2 from the days), `.seconds=11045` (3 hours = 10800 seconds + 4 minutes = 240 seconds + 5 seconds = 11045), and `.microseconds=6007` (6 milliseconds = 6000 microseconds + 7 microseconds = 6007). The printed form `9 days, 3:04:05.006007` is just the three attributes formatted into a human-readable string.

**Why are there seven input units but only three storage fields?** Because the seven input units are *convenience for the human writing the call* (`weeks=1` is more readable than `seconds=604800`), and the three storage fields are *the canonical form that makes arithmetic and comparison unambiguous*. If `timedelta` stored `weeks`, `days`, `hours`, etc. as separate fields, then `timedelta(weeks=1) == timedelta(days=7)` would have to perform a cross-unit equality check on every comparison — the same value represented two ways would need normalisation on every `__eq__` call. By normalising once at construction time and storing only the canonical form, the type guarantees that *equal durations are the same instance form* and the `__eq__` is a flat three-field compare. The asymmetry (seven inputs, three outputs) is the price you pay for O(1) comparison.

### Lines 14–17: Normalisation — `weeks` becomes `days`

```python
# 2. Normalisation: weeks -> days, hours/minutes/seconds -> seconds, ms -> microseconds
td_weeks = timedelta(weeks=1)
print("timedelta(weeks=1).days:", td_weeks.days)               # 7
print("timedelta(weeks=1).seconds:", td_weeks.seconds)         # 0
print("timedelta(weeks=1) == timedelta(days=7):", td_weeks == timedelta(days=7))
```

`timedelta(weeks=1)` is the textbook normalisation case. You pass `weeks=1`; the constructor multiplies by 7 and stores `days=7`; `.seconds` is `0`; `.microseconds` is `0`. The `==` comparison with `timedelta(days=7)` returns `True` because both instances have the same canonical form — `days=7, seconds=0, microseconds=0`. The two are *the same duration*, written two ways, and the type says so.

The normalisation rules are:
- `weeks` → multiplied by 7 → added to `days`.
- `days` → stored directly into `days` (can exceed 1, can be negative).
- `hours`, `minutes`, `seconds` → multiplied into seconds → added to `seconds`.
- `milliseconds` → multiplied by 1000 → added to `microseconds`.
- `microseconds` → stored directly into `microseconds`.
- After accumulation: if `seconds >= 86400`, the overflow is divided into `days` (each 86400 seconds adds 1 day); if `microseconds >= 1000000`, the overflow is divided into `seconds` (each 1000000 microseconds adds 1 second).

The result is that `.seconds` is always in `0..86399` (a day's worth), `.microseconds` is always in `0..999999` (a second's worth), and `.days` carries the remainder unbounded. This invariant is what makes `timedelta(weeks=1)` and `timedelta(days=7)` and `timedelta(hours=168)` and `timedelta(seconds=604800)` all *the same instance form* — every one of them normalises to `days=7, seconds=0, microseconds=0`.

**Why does `weeks` collapse to `days` and not to `seconds`?** Because `weeks` and `days` are both *calendar-ish* units (multiples of 24 hours), and `seconds` and `microseconds` are *intra-day* units. The three-field split — `days`/`seconds`/`microseconds` — maps cleanly to "how many days, and what time-of-day-remainder". A `timedelta` of `9 days, 3:04:05.006007` reads as "nine days and a bit"; the `3:04:05.006007` part is the *intra-day remainder*, never more than a day. This is also the form that lets `timedelta.__repr__` produce a readable string ("9 days, 3:04:05.006007" is a much better debugging aid than "797045.006007 seconds").

### Lines 19–22: The gotcha — `hours` collapses into `.seconds`, not `.hours`

```python
# 3. The gotcha: hours/minutes collapse into .seconds (not .hours)
td_hours = timedelta(hours=25)
print("timedelta(hours=25).days:", td_hours.days)              # 1
print("timedelta(hours=25).seconds:", td_hours.seconds)       # 3600 (one hour)
```

This is the line that catches every senior engineer the first time. `timedelta(hours=25)` *looks* like it should have `.hours = 25`, and it does not — there is no `.hours` attribute at all. The normalisation puts `25 hours` into `1 day + 1 hour`, stores `days=1` and `seconds=3600` (one hour's worth of seconds), and the only way to recover "25 hours" is `td_hours.days * 24 + td_hours.seconds // 3600`, or `.total_seconds() / 3600`.

The symptom in production: you write `td = datetime.now(timezone.utc) - some_event` and check `if td.hours > 24:` to detect an SLA breach. The `AttributeError: 'timedelta' object has no attribute 'hours'` raises at runtime — the bug is caught loud, but late. The fix is to compare against the duration directly: `if td > timedelta(hours=24):` — no attribute access, no unit conversion, just a duration-vs-duration comparison that the type's `__gt__` handles correctly because both sides normalise to the same three-field form.

**Why doesn't `timedelta` expose `.hours` and `.minutes` as derived properties?** The stdlib authors chose to expose only the canonical storage fields (`days`, `seconds`, `microseconds`) and leave unit-conversion to the caller via `.total_seconds()`. The reasoning is that exposing derived properties (`hours`, `minutes`, `weeks`) would invite bugs — `td.hours` for `timedelta(hours=25)` would have to return `25` or `1` (the day-truncated part), and either answer is a footgun. The flat rule "there are three attributes, period" is simpler to teach, simpler to remember, and forces the caller to think about what they mean by "hours" before they write it. The cost is the gotcha this section exists to flag.

### Lines 24–28: Arithmetic — `datetime + timedelta -> datetime`

```python
# 4. Arithmetic: datetime + timedelta -> datetime
created = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
sla = created + timedelta(hours=24)
print("created + 24h:", sla)
print("type:", type(sla).__name__)
```

`datetime + timedelta` returns a `datetime`. The arithmetic is "field-wise": the `timedelta`'s `days`, `seconds`, and `microseconds` are added to the `datetime`'s date and time components, with carry-through at every unit boundary (seconds overflow to minutes, minutes to hours, hours to days, days to months, months to years). The result is a new `datetime` instance — `timedelta` arithmetic is *non-mutating* (the original `created` is unchanged; the new `sla` is a separate object).

The `tzinfo` slot is *preserved*: an aware `datetime` plus a `timedelta` returns an aware `datetime` with the same `tzinfo`. So `created` (UTC) plus `timedelta(hours=24)` returns a `datetime` in UTC. This is the right behaviour for SLA computation — the SLA window is "24 wall-hours of elapsed time", which in UTC is unambiguous, and the result `sla` is comparable to any other aware UTC `datetime`. (Lesson 04 walks what happens when you cross a DST boundary in a non-UTC zone — the answer is "the wall-clock result is what `timedelta` arithmetic gives you, which may or may not be what you want for calendar arithmetic".)

The `type(sla).__name__` confirms the return type — `datetime`. This matters because students sometimes expect `datetime + timedelta` to return a `timedelta` (it doesn't — addition of an instant and a duration is an instant) or a `tuple` (it doesn't — that would be the `date`/`time` split, which has nothing to do with addition). The type pin is `datetime`.

**Why does `datetime + timedelta` return a `datetime` and not a new type like `datetime_with_offset`?** Because the result *is* an instant — a fully-specified point in time. The fact that you arrived at it by adding 24 hours to another instant does not change its type; it is still an instant, with a date, a time-of-day, and (if the original was aware) a timezone. Introducing a new "datetime-with-offset" type would break every consumer of `datetime` that does not know about the new type — the stdlib's choice is to keep `datetime + timedelta -> datetime` and let the caller's intent (SLA deadline, scheduled event, etc.) live in the variable name (`sla`, `scheduled_for`, `expires_at`) rather than the type.

### Lines 30–35: Subtraction — `datetime - datetime -> timedelta`

```python
# 5. Subtraction: datetime - datetime -> timedelta
later = datetime(2026, 10, 24, 14, 30, 0, tzinfo=timezone.utc)
delta = later - created
print("later - created:", delta)
print("type:", type(delta).__name__)
print("total_seconds:", delta.total_seconds())
```

`datetime - datetime` returns a `timedelta`. The arithmetic is the inverse of `+`: subtract the dates and the time-of-day components, with borrow-through at every unit boundary (the inverse of carry-through). The result is a `timedelta` with the duration between the two instants — `later` minus `created` is `1 day, 2 hours, 30 minutes = 1 day, 9000 seconds` printed as `1 day, 2:30:00`.

The `tzinfo` constraint matters here: you can subtract two aware `datetime` values (any `tzinfo`, even different offsets — the arithmetic works on the *instants*, normalising through UTC internally), or two naive `datetime` values (both `tzinfo is None` — the arithmetic works on the wall-clock readings, treating them as the same unspecified zone). You cannot subtract a naive `datetime` from an aware `datetime` — that raises `TypeError: can't subtract offset-naive and offset-aware datetimes` (lesson 04 walks the rule). The reason is that the operation is *meaningful only if both sides are on the same kind of clock*, and the type system checks the `tzinfo` slot to enforce that.

The `.total_seconds()` call returns the duration as a single `float` — here `95400.0` (one day = 86400 seconds, plus 2 hours 30 minutes = 9000 seconds, total 95400). The three-field form (`days=1`, `seconds=9000`, `microseconds=0`) is exact; the `float` form is exact for any duration under ~104 days and is what the rest of the system (Postgres `interval` columns, `time.sleep()`, `time.time()`) expects.

**Why does `total_seconds()` return a `float` and not an `int`?** Because `timedelta` has microsecond resolution, and the integer count of microseconds can exceed `2**53` for durations of more than ~104 days — at which point a `float` would lose precision but an `int` would not. The stdlib's choice is `float` for ergonomics: most call sites want `total_seconds()` as a `float` (for `time.time()` comparison, for `sleep()`, for logging elapsed seconds with `%.3f`), and the precision loss for sub-microsecond values past 104 days is rare in practice. If you need exact microsecond precision past that horizon, use `td.days * 86400 + td.seconds` and `td.microseconds` directly — the type does not lose precision internally, only at the `total_seconds()` boundary.

### Lines 37–38: `.total_seconds()` is a `float`

```python
# 6. total_seconds() returns a float (with sub-microsecond precision possible)
print("total_seconds type:", type(delta.total_seconds()).__name__)
```

The single `print` confirms the return type — `float`. This is the line that catches engineers who `assert isinstance(delta.total_seconds(), int)` and fail. The float is exact for any duration under ~104 days (because `2**53` microseconds is `9_007_199_254_740_992` microseconds, which divided by `10**6` is `9_007_199_254` seconds, which is `~104` days). Past that horizon, the float loses precision — but you would have to be computing durations of *months* in microseconds for it to matter.

The lesson here is not "avoid `total_seconds()`"; the lesson is "know what type you are getting". If you want a duration in seconds for use with `time.sleep(s)` or `time.time() - start` — both `float` APIs — `total_seconds()` is the right call. If you want a duration for `timedelta` arithmetic, keep it as a `timedelta` and use `//` (the next block). The two are *different operations on different types*; mixing them is the bug.

### Lines 40–44: Floor-division — `timedelta // timedelta -> int` (Python 3.2+)

```python
# 7. Floor-division: timedelta // timedelta -> int (Python 3.2+)
hours_apart = delta // timedelta(hours=1)
print("hours_apart (floor):", hours_apart)
remainder = delta % timedelta(hours=1)
print("remainder:", remainder)
```

`timedelta // timedelta` returns an `int` — the floor-division count of how many whole units of the right-hand `timedelta` fit into the left-hand `timedelta`. For `delta` of `1 day, 2 hours, 30 minutes` and `timedelta(hours=1)` as the divisor, the answer is `26` (24 hours in the day + 2 hours in the remainder; the 30 minutes is less than a whole hour and is dropped on the floor). The `//` operator was added to `timedelta` in Python 3.2 (the same 3.2 release that added `datetime.timezone`); on 3.12 it is fully supported.

The `%` operator returns the *remainder* — a `timedelta` representing what was left over after the floor-division. For `delta % timedelta(hours=1)`, the remainder is `timedelta(minutes=30)`. The two operators compose: `delta = (delta // unit) * unit + (delta % unit)`, the same floor-division/remainder identity as for integers.

This is the tool for SLA "breach in N hours" calculations. If a ticket was created 47 hours ago and the SLA window is 24 hours, `delta // timedelta(hours=24)` returns `1` (one full window overdue); the `if delta // timedelta(hours=24) > 0:` check is the "more than 24 hours overdue" predicate. For finer-grained checks, `delta // timedelta(hours=1)` gives "how many hours overdue".

**Why floor-division and not regular division?** Because `timedelta / timedelta` returns a `float` (e.g. `2.5`), which loses precision for very large durations and forces the caller to round manually. `//` returns an `int`, which is the natural type for "count of units". The two operators cover the two cases: `//` when you want an integer count (which slot of the SLA ladder are we in? how many billing hours?); `/` when you want a fractional ratio (this event took 2.5× the budgeted time). The stdlib authors added both; the choice is the caller's.

### Lines 46–58: The `boardly` Ticket model with SLA methods

```python
# 8. The boardly Ticket model with an SLA window
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def sla_breach_at(self, window: timedelta = timedelta(hours=24)) -> datetime:
        return self.created_at + window

    def is_overdue(self, now: datetime, window: timedelta = timedelta(hours=24)) -> bool:
        return now > self.created_at + window


t = Ticket(id=1, summary="login broken")
now = t.created_at + timedelta(hours=25)          # 1 hour past SLA
print("SLA breach at:", t.sla_breach_at())
print("is_overdue (25h later):", t.is_overdue(now))
```

The `Ticket` dataclass is the running example from lesson 01 with two new methods. `sla_breach_at` returns the `datetime` at which the SLA window is breached — `created_at + window`, pure `timedelta` arithmetic, returns a `datetime`. The default `window=timedelta(hours=24)` is a 24-hour SLA; callers can override it (`t.sla_breach_at(window=timedelta(hours=48))` for a 48-hour SLA).

`is_overdue` is a `bool`-returning predicate: `now > self.created_at + window`. The comparison is `datetime > datetime`, which works because both sides are aware (lesson 01 established that `created_at` defaults to `datetime.now(timezone.utc)`, and `now = t.created_at + timedelta(hours=25)` preserves the `tzinfo`). If either side were naive, the comparison would raise `TypeError` — lesson 04 walks the rule.

The `now = t.created_at + timedelta(hours=25)` line in the test simulates "1 hour past SLA" without sleeping — the test runs instantly because the `timedelta` arithmetic is pure. The `is_overdue(now)` call returns `True` because `now` is past `created_at + timedelta(hours=24)`.

**Why does `sla_breach_at` return a `datetime` and not a `timedelta`?** Because the breach time is an *instant* — a specific point in time when the SLA expires — not a *duration*. The two are different types for different questions: "when does the SLA expire?" (`datetime`) vs "how long until the SLA expires?" (`timedelta`, computed as `sla_breach_at(now) - now`). Returning the `datetime` lets the caller store it, compare it, render it in ISO 8601 (lesson 03), and convert it to the user's timezone (lesson 05). Returning a `timedelta` would force the caller to re-add `now` to get the breach time, and the two-step computation is more error-prone than the single-step `created_at + window`.

### Lines 60–63: Scalar multiplication and division

```python
# 9. Scalar multiplication and division
half_day = timedelta(hours=12) * 0.5
print("half_day:", half_day, "| type:", type(half_day).__name__)
hour_in_seconds = timedelta(hours=1) / 2
print("hour / 2:", hour_in_seconds)
```

`timedelta * scalar` and `timedelta / scalar` are the *ratio* operations — multiply a duration by 2 to double it, divide by 2 to halve it. The result is a `timedelta` (not a `float` — that would be `total_seconds()`); the type carries the duration across the multiplication. `timedelta(hours=12) * 0.5` returns `timedelta(hours=6)`; `timedelta(hours=1) / 2` returns `timedelta(seconds=1800)` (half an hour). The internal normalisation handles fractional microseconds — if the result of the multiplication is, say, `1.5 microseconds`, the half-microsecond is dropped (rounded towards zero) because `timedelta` has microsecond resolution and cannot represent sub-microsecond durations.

These two operators round out the arithmetic surface: `+` and `-` for `datetime`↔`timedelta` and `timedelta`↔`timedelta`, `*` and `/` for `timedelta`↔`scalar`, `//` and `%` for `timedelta`↔`timedelta` (integer quotient and remainder). With those six operators you can express any duration computation; the rest is readability and intent.

**Why does `timedelta * 0.5` work but `timedelta * 0.5 == timedelta(hours=6)` for `timedelta(hours=12)`?** Because `timedelta.__mul__` accepts any `int` or `float` and produces a new `timedelta` with the scaled value. The result is *normalised* after the multiplication, so `timedelta(hours=12) * 0.5` produces a `timedelta` whose internal `days=0`, `seconds=21600` (6 hours = 21600 seconds), `microseconds=0` — exactly the same form as `timedelta(hours=6)`. The `==` is a three-field compare; both sides have the same three-field form; `True`. The multiplication is *exact* for any rational scalar whose result has no sub-microsecond remainder; for irrationals or repeating fractions, the result is rounded to the nearest microsecond (round-towards-zero).

## Execution Trace

```bash
$ uv run python boardly/slas/timedelta_basics.py
td_full: 9 days, 3:04:05.006007
td_full.days: 9
td_full.seconds: 11045
td_full.microseconds: 6007
timedelta(weeks=1).days: 7
timedelta(weeks=1).seconds: 0
timedelta(weeks=1) == timedelta(days=7): True
timedelta(hours=25).days: 1
timedelta(hours=25).seconds: 3600
created + 24h: 2026-10-24 12:00:00+00:00
type: datetime
later - created: 1 day, 2:30:00
type: timedelta
total_seconds: 95400.0
total_seconds type: float
hours_apart (floor): 26
remainder: 0:30:00
SLA breach at: 2026-10-24 07:07:59.966222+00:00
is_overdue (25h later): True
half_day: 6:00:00 | type: timedelta
hour / 2: 0:30:00
```

The `SLA breach at` value is the runtime UTC instant plus 24 hours and changes every time you run the script. The duration arithmetic and the boolean result are what to check.

## Common Mistakes

### Mistake 1: Adding an `int` to a `datetime`

```python
sla = created_at + 86400          # TypeError: unsupported operand type(s) for +: 'datetime' and 'int'
```

**Symptom:** `TypeError` at the arithmetic line. The script never produces the SLA value.
**Why:** `datetime.__add__` only accepts `timedelta`, not `int`. The bare integer has no marker saying "this is seconds, not milliseconds, not microseconds"; the type system refuses to guess.
**Fix:** Add a `timedelta`: `sla = created_at + timedelta(seconds=86400)`. Or, more readable, `timedelta(hours=24)` — same value, self-documenting unit.

### Mistake 2: Reading `td.hours` or `td.minutes`

```python
if (datetime.now(timezone.utc) - created_at).hours > 24:    # AttributeError
    ...
```

**Symptom:** `AttributeError: 'timedelta' object has no attribute 'hours'`. The condition never evaluates.
**Why:** `timedelta` exposes only `.days`, `.seconds`, `.microseconds`. There is no `.hours`, `.minutes`, `.weeks`, or `.milliseconds` attribute. The seven constructor keyword arguments are inputs, not attributes.
**Fix:** Compare against a `timedelta` directly: `if datetime.now(timezone.utc) - created_at > timedelta(hours=24):`. No attribute access, no unit conversion — the type's `__gt__` handles the comparison because both sides normalise to the three-field form.

### Mistake 3: Calling `total_seconds()` and assuming it is an `int`

```python
elapsed = (now - created_at).total_seconds()
assert isinstance(elapsed, int)        # AssertionError
```

**Symptom:** An `isinstance` assertion fails because `total_seconds()` returns a `float`, not an `int`.
**Why:** `total_seconds()` returns a `float` so that sub-second precision (microseconds) is preserved without forcing the caller to compute `td.days * 86400 + td.seconds + td.microseconds / 1e6`. The float is exact for any duration under ~104 days; past that, it loses precision. The integer count of seconds is recoverable as `int(td.total_seconds())` but is rarely what the caller wants.
**Fix:** Either accept the `float` (for `time.sleep`, `time.time()` comparison, etc.) or compute the integer directly from the three attributes: `int_seconds = td.days * 86400 + td.seconds`. The integer form is exact for any duration; the float form is ergonomic for most call sites.

### Mistake 4: Mixing `timedelta` units in equality

```python
if created_at + timedelta(days=1) == created_at + timedelta(hours=24):
    print("equal")        # this runs — the two are the same duration
```

**Symptom:** None — this is the *correct* behaviour, but engineers often assume `timedelta(days=1)` and `timedelta(hours=24)` are different objects because the constructor keywords differ.
**Why:** `timedelta` normalises at construction time. `timedelta(days=1)` and `timedelta(hours=24)` both produce the same internal `days=1, seconds=0, microseconds=0` form, so `==` is `True`. The constructor keywords are *input units*, not *storage*; the storage is the canonical three-field form.
**Fix:** No fix needed — the equality is correct. The lesson is that `timedelta` equality is *normalised equality*, not *constructor-form equality*; the same duration written two ways is the same value.

## Engineering Trade-Offs

**Decision:** Use `timedelta` for every duration in `boardly`. Never use bare `int` seconds. Never use `float` for durations longer than the SLA window.
**Both sides:** The alternative is the `int`-seconds convention — store every duration as a count of seconds (an `int`), do integer arithmetic, multiply by 1000 for milliseconds. `int`-seconds is *faster* (no object overhead), *JSON-native* (serialise as a number), and *exact* (no floating-point representation). The trade-off: `int`-seconds is *unit-ambiguous* at the type level — `86400` is indistinguishable from `86400` seconds, milliseconds, or microseconds, and a single mis-typed `* 1000` in one function breaks every downstream computation silently. `timedelta` carries its own unit (the type *is* the unit), so `created_at + timedelta(seconds=86400)` is type-checked, normalised, and self-documenting. For an SLA window that the team will read and modify for years, the readability win outweighs the speed cost.
**Commitment:** `boardly` uses `timedelta` for every duration field and every duration computation. The `Ticket.sla_breach_at` and `Ticket.is_overdue` methods take `window: timedelta` parameters with default `timedelta(hours=24)`. The API layer exposes durations as ISO 8601 strings (lesson 03); the storage layer stores them as `timedelta` columns in Postgres (`interval` type, which round-trips with `timedelta`). The `int`-seconds alternative is documented for systems that need the speed; we use `timedelta` because the unit-tracking buys us more than the speed costs us.

## Exercises

1. **Exercise 1 — Change the SLA window.** Edit the `is_overdue` call to use a 48-hour window: `t.is_overdue(now, window=timedelta(hours=48))`. Confirm `is_overdue` returns `False` (the ticket is only 25 hours old, less than 48). `Verify: uv run python boardly/slas/timedelta_basics.py | rg 'is_overdue'`
2. **Exercise 2 — Reproduce the `td.hours` AttributeError.** Add a line `print(timedelta(hours=25).hours)` to the script. Confirm `AttributeError: 'timedelta' object has no attribute 'hours'`. Then remove the line. `Verify: uv run python -c "from datetime import timedelta; timedelta(hours=25).hours" 2>&1 | rg 'AttributeError'`
3. **Exercise 3 — Compute the remainder in seconds.** Use `delta % timedelta(hours=1)` and convert to seconds via `.total_seconds()`. Confirm the result is `1800.0` (30 minutes) for the script's `delta` of `1 day, 2:30:00`. `Verify: uv run python -c "from datetime import datetime, timedelta, timezone; a=datetime(2026,10,23,12,tzinfo=timezone.utc); b=datetime(2026,10,24,14,30,tzinfo=timezone.utc); print(((b-a) % timedelta(hours=1)).total_seconds())"`
4. **Exercise 4 — Verify the normalisation identity.** Write a function `normalise(td: timedelta) -> tuple[int, int, int]` returning `(td.days, td.seconds, td.microseconds)`. Confirm `normalise(timedelta(weeks=1, hours=3))` returns `(7, 10800, 0)`. `Verify: uv run python -c "from datetime import timedelta; f=lambda td:(td.days,td.seconds,td.microseconds); assert f(timedelta(weeks=1,hours=3))==(7,10800,0); print('ok')"`
5. **Exercise 5 — Add a "breach severity" method.** Add `def breach_severity(self, now: datetime, window: timedelta = timedelta(hours=24)) -> int` to the `Ticket` dataclass that returns `0` if not overdue, otherwise `(now - self.created_at - window) // timedelta(hours=1)` (how many hours past the SLA). Confirm `t.breach_severity(now)` returns `1` for the script's `now` (25 hours after `created_at`). `Verify: uv run python -c "from boardly.slas.timedelta_basics import Ticket; from datetime import datetime, timedelta, timezone; t=Ticket(id=1,summary='x'); now=t.created_at+timedelta(hours=25); assert t.breach_severity(now)==1; print('ok')"`

## Verification

```bash
$ uv run python boardly/slas/timedelta_basics.py
td_full: 9 days, 3:04:05.006007
td_full.days: 9
td_full.seconds: 11045
td_full.microseconds: 6007
timedelta(weeks=1).days: 7
timedelta(weeks=1).seconds: 0
timedelta(weeks=1) == timedelta(days=7): True
timedelta(hours=25).days: 1
timedelta(hours=25).seconds: 3600
created + 24h: 2026-10-24 12:00:00+00:00
type: datetime
later - created: 1 day, 2:30:00
type: timedelta
total_seconds: 95400.0
total_seconds type: float
hours_apart (floor): 26
remainder: 0:30:00
SLA breach at: 2026-10-24 07:07:59.966222+00:00
is_overdue (25h later): True
half_day: 6:00:00 | type: timedelta
hour / 2: 0:30:00
```

## Previously Learned Here

- [[15-datetime/01-datetime-and-timezone]] — the `datetime` constructor, the `tzinfo` slot, and the aware-UTC rule that this lesson's arithmetic depends on (`created_at` is aware UTC, so `created_at + timedelta(hours=24)` is also aware UTC).
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` decorator that generates the `Ticket` model this lesson extends with `sla_breach_at` and `is_overdue` methods.
- [[06-dataclasses/02-field-and-Defaults]] — the `field(default_factory=...)` pattern on the `created_at` field.

## What's Next

[[15-datetime/03-ISO-8601-format]] — Now that you can construct an aware `datetime` and do `timedelta` arithmetic on it, you need the *serialisation* layer: how a `datetime` becomes a string and back. Lesson 03 walks `datetime.isoformat()` — the canonical ISO 8601 form `2026-10-23T12:00:00+00:00`, the `sep='T'` and `timespec='auto'` parameters, the `timespec` options (`hours`/`minutes`/`seconds`/`milliseconds`/`microseconds`), and the round-trip with `datetime.fromisoformat(s)` that re-creates the same `datetime` from the string.

- **Lesson 03** — `isoformat()`, ISO 8601, `timespec`, the round-trip.
- **Lesson 04** — aware vs naive, the `TypeError` comparison, the production rule.
- **Lesson 05** — `fromisoformat()`, `fromtimestamp()`, `zoneinfo`, parsing at the boundary.

## Sources

- **Python `datetime` module documentation — `timedelta` objects** — https://docs.python.org/3/library/datetime.html#timedelta-objects — accessed 2026-10-23 — the canonical CPython reference for the `timedelta` constructor, the normalisation rules, `.days`/`.seconds`/`.microseconds`, `.total_seconds()`, and the `//` and `%` operators.
- **Python `datetime` module documentation — arithmetic** — https://docs.python.org/3/library/datetime.html#datetime-objects — accessed 2026-10-23 — the `datetime + timedelta -> datetime` and `datetime - datetime -> timedelta` arithmetic rules, including the `tzinfo` preservation semantics.
- **What's New in Python 3.2 — `timedelta` floor-division** — https://docs.python.org/3.2/whatsnew/3.2.html — accessed 2026-10-23 — confirms that `timedelta // timedelta` and `timedelta % timedelta` were added in Python 3.2 (the same release that added `datetime.timezone`).

## What We Learned

- You can now construct a `timedelta` with any of the seven keyword arguments (`weeks`, `days`, `hours`, `minutes`, `seconds`, `milliseconds`, `microseconds`) and explain how they normalise into `days`/`seconds`/`microseconds` internally.
- You can read `.days`, `.seconds`, and `.microseconds` directly and explain why `.hours` and `.minutes` do not exist as attributes.
- You can do `datetime + timedelta -> datetime` arithmetic and `datetime - datetime -> timedelta` subtraction, and explain why the result type differs.
- You can call `.total_seconds()` and know it returns a `float` (with sub-microsecond precision for short durations).
- You can use `timedelta // timedelta` for integer floor-division and `timedelta % timedelta` for the remainder, and explain when each is the right tool for SLA breach-counting.
