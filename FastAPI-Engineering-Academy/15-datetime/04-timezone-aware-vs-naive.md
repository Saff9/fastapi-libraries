---
title: "Lesson 04: timezone-aware vs naive"
aliases:
 - aware vs naive
 - naive datetime
 - astimezone
 - TypeError offset-naive offset-aware
 - tzinfo is None
tags:
 - datetime
 - python-stdlib
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[15-datetime/01-datetime-and-timezone]]"
 - "[[15-datetime/02-timedelta]]"
 - "[[15-datetime/03-ISO-8601-format]]"
related_lessons:
 - "[[15-datetime/03-ISO-8601-format]]"
 - "[[15-datetime/05-fromisoformat-and-parsing]]"
---

# Lesson 04: timezone-aware vs naive

*The `TypeError: can't compare offset-naive and offset-aware datetimes` exception that has saved more production incidents than it has caused — and the "store aware UTC, render in the user's timezone at the edge" rule that prevents the bug at the source.*

**You're at the very beginning of Section 15, Lesson 04.**

You have written `datetime.now(timezone.utc)` for every `created_at` and stored the values, and one day a junior engineer adds a `deadline` field and forgets the `tzinfo=timezone.utc` argument — `datetime(2026, 12, 31, 23, 59, 59)`, naive. The dataclass accepts it (both are `datetime`), the database stores it, the API serialises it. And then the first `if now > ticket.deadline:` line in the breach-check service raises `TypeError: can't compare offset-naive and offset-aware datetimes` in production, at 2am, on a Sunday. This lesson walks that exception — what the type system is telling you, why Python got it right by raising instead of guessing, and the cardinal rule that prevents it: never let a naive `datetime` past the parse boundary. Take your time. Type every example. **This is how you learn.**

#datetime #aware-vs-naive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Read the `tzinfo is None` test** — write `if dt.tzinfo is None:` to detect naivety, and explain why `is None` is the right comparison (not `== None`, not `not dt.tzinfo`).
2. **Trigger and read the `TypeError`** — write `naive < aware` and reproduce the `TypeError: can't compare offset-naive and offset-aware datetimes` exception, and explain why the type system raises instead of silently guessing.
3. **Use `dt.astimezone(tz)`** — convert an aware `datetime` from one timezone to another, including `astimezone(timezone.utc)` to normalise to UTC and `astimezone(ZoneInfo(...))` for an IANA zone.
4. **State the cardinal rule** — store aware UTC, render in the user's timezone at the edge, never let a naive `datetime` past the parse boundary.
5. **Implement the breach-check service** — write the `is_overdue` predicate that compares an aware UTC `now` to an aware UTC `deadline` and explain why the comparison is safe.

## Prerequisites

Before starting, you need:

- **The `datetime` constructor and aware UTC** — [[15-datetime/01-datetime-and-timezone]]. The `tzinfo` slot is the field this lesson hinges on; you need to be fluent with it.
- **`timedelta` arithmetic** — [[15-datetime/02-timedelta]]. The `is_overdue` predicate uses `datetime > datetime` which depends on the arithmetic-rules lesson 02 walked.
- **ISO 8601 serialisation** — [[15-datetime/03-ISO-8601-format]]. The "no suffix" symptom of a naive `datetime` is the visible marker of the bug this lesson catches.
- **About 30–45 minutes of focused time.**

**The most common gap: treating the `TypeError` as an annoyance instead of a feature.**

It is a feature. The single biggest mistake students make when they hit `TypeError: can't compare offset-naive and offset-aware datetimes` is to "fix" it by stripping the `tzinfo` off the aware value (`aware.replace(tzinfo=None)`) so the comparison stops raising. That "fix" makes the exception go away; it does not make the bug go away — it converts a loud failure into a silent wrong answer, because comparing a naive UTC value to a naive local value produces a result that is wrong by the timezone delta between the two machines that wrote them. The right fix is the opposite direction: make the naive value aware (`naive.replace(tzinfo=timezone.utc)`), not the aware value naive. The `TypeError` is the type system telling you the value's meaning is ambiguous; suppressing it does not resolve the ambiguity. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/breach/bad_overdue.py — the bad old days
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class Ticket:
    id: int
    deadline: datetime          # ← contract says "aware UTC" but type doesn't enforce


# A junior engineer forgets tzinfo=timezone.utc — naive deadline
ticket = Ticket(id=1, deadline=datetime(2026, 12, 31, 23, 59, 59))

# The breach-check service runs with an aware UTC now
now = datetime.now(timezone.utc)
print(ticket.deadline.tzinfo)              # None — naive
print(now.tzinfo)                          # UTC — aware

# The comparison that raises at 2am
if now > ticket.deadline:                   # TypeError: can't compare offset-naive and offset-aware
    print("overdue!")
```

The dataclass accepts the naive `deadline` because the type annotation is `datetime` — Python's type system does not distinguish naive from aware at the annotation level (both are `datetime`). The bug surfaces only at the comparison line, where `now > ticket.deadline` raises `TypeError: can't compare offset-naive and offset-aware datetimes`. The exception is loud, late, and unhelpful: it tells you the comparison is meaningless but not which value is wrong, and the production stack trace points at the comparison line, not at the constructor 50 lines earlier where the bug was actually written.

This is not a Python problem. It is a "what does this wall-clock reading mean?" problem. Every language with a datetime type hits it: Java's `java.util.Date` and `java.time.Instant` cannot be compared silently; Go's `time.Time` reports a `Location()` of `nil` for naive values; JavaScript's `Date` is always UTC-flavoured and silently wrong for non-UTC timezones. Python's answer is the `tzinfo` slot and the loud `TypeError` — the type system refuses to guess whether a naive value means UTC, local, or some other zone, and forces the caller to make the choice explicit.

`datetime.astimezone(tz)` is the standard-library answer to "I have an aware `datetime` in one timezone and I need it in another". The method takes a `tzinfo` instance (`timezone.utc`, `timezone(timedelta(...))`, or `ZoneInfo("America/New_York")`) and returns a new `datetime` whose wall-clock reading is the equivalent instant in the target timezone. The original instant is preserved — `dt.astimezone(timezone.utc)` and `dt.astimezone(ZoneInfo("America/New_York"))` represent the same moment in time, just printed with different wall-clock readings. Combined with the rule "store aware UTC", `astimezone` is the only conversion the application layer should ever need — and only at the display boundary, never at the storage boundary.

## The Code

```python
# boardly/breach/aware_vs_naive.py
"""The aware-vs-naive distinction, the TypeError exception, the astimezone
conversion, and the store-aware-UTC-render-at-the-edge rule."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


# 1. The two kinds of datetime: aware and naive
aware = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
naive = datetime(2026, 10, 23, 12, 0, 0)
print("aware.tzinfo:", aware.tzinfo, "| is None:", aware.tzinfo is None)
print("naive.tzinfo:", naive.tzinfo, "| is None:", naive.tzinfo is None)

# 2. The TypeError — comparing naive to aware raises
try:
    print("naive < aware:", naive < aware)
except TypeError as e:
    print("TypeError:", e)

# 3. Subtracting naive from aware also raises
try:
    print("naive - aware:", naive - aware)
except TypeError as e:
    print("TypeError:", e)

# 4. The fix: make the naive value aware (not the aware value naive!)
naive_fixed = naive.replace(tzinfo=timezone.utc)
print("naive_fixed.tzinfo:", naive_fixed.tzinfo)
print("naive_fixed < aware:", naive_fixed < aware)         # False — same instant

# 5. astimezone: convert an aware datetime to another timezone
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
ny_tz = ZoneInfo("America/New_York")
aware_ny = aware_utc.astimezone(ny_tz)
print("aware UTC:  ", aware_utc)
print("aware NY:   ", aware_ny)
print("same instant (utc == ny):", aware_utc == aware_ny)   # True

# 6. astimezone(None) — convert aware to system local
system_local = aware_utc.astimezone()
print("system local:", system_local, "| tzinfo:", system_local.tzinfo)

# 7. The store-aware-UTC-render-at-the-edge rule
@dataclass
class Ticket:
    id: int
    summary: str
    deadline: datetime                              # always aware UTC; contract
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_overdue(self, now: datetime) -> bool:
        # both sides must be aware; the type system enforces this loudly
        return now > self.created_at + (self.deadline - self.created_at)


# A correct ticket — both fields aware UTC
t = Ticket(
    id=1,
    summary="login broken",
    deadline=datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc),
)
now = datetime(2026, 10, 23, 13, 0, 0, tzinfo=timezone.utc)
print("Ticket.is_overdue (within window):", t.is_overdue(now))    # False

# 8. Rendering in the user's timezone at the edge
user_tz = ZoneInfo("America/New_York")
deadline_for_user = t.deadline.astimezone(user_tz)
print("deadline in user's tz:", deadline_for_user)

# 9. The bug that the type system catches
buggy_ticket = Ticket(
    id=2,
    summary="forgot tzinfo",
    deadline=datetime(2026, 10, 24, 12, 0, 0),   # ← naive — bug!
)
try:
    buggy_ticket.is_overdue(now)
except TypeError as e:
    print("buggy_ticket TypeError:", e)

# 10. The DST fold case — astimezone handles it correctly
# 2026-11-01 01:30 in America/New_York occurs twice (EDT -> EST fall-back)
dst_instant_utc = datetime(2026, 11, 1, 5, 30, 0, tzinfo=timezone.utc)
edt_reading = dst_instant_utc.astimezone(ny_tz)              # fold=0 (EDT, offset -04:00)
est_reading = dst_instant_utc.astimezone(ny_tz).replace(fold=1)  # fold=1 (EST, offset -05:00)
print("DST instant UTC:", dst_instant_utc)
print("NY (fold=0 EDT):", edt_reading, "tzname:", edt_reading.tzname())
print("NY (fold=1 EST):", est_reading, "tzname:", est_reading.tzname())
print("== (same tzinfo quirk):", edt_reading == est_reading)    # True — wall-clock compare, NOT same instant
print("normalise via UTC:  ", edt_reading.astimezone(timezone.utc) == est_reading.astimezone(timezone.utc))   # False
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–9: The two kinds of `datetime`

```python
# 1. The two kinds of datetime: aware and naive
aware = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
naive = datetime(2026, 10, 23, 12, 0, 0)
print("aware.tzinfo:", aware.tzinfo, "| is None:", aware.tzinfo is None)
print("naive.tzinfo:", naive.tzinfo, "| is None:", naive.tzinfo is None)
```

The two `datetime` values look identical at the wall-clock level — both are `2026-10-23 12:00:00`. The difference is in the `tzinfo` slot: `aware` has `tzinfo=timezone.utc` (an instance of the `timezone` class), `naive` has `tzinfo=None` (no offset recorded). The `is None` test on `tzinfo` is the canonical naivety check — `dt.tzinfo is None` is `True` for naive values, `False` for aware values. The `is` comparison is correct (not `== None` and not `not dt.tzinfo`) because `tzinfo` is either `None` (the singleton) or an instance — there is no third state, and `is` is the cheap identity check.

The two values mean different things. `aware` is the instant `2026-10-23 12:00:00 UTC` — the same moment in Tokyo, London, and New York (12:00 UTC = 21:00 in Tokyo, 13:00 in London, 08:00 in New York). `naive` is the wall-clock reading `2026-10-23 12:00:00` with no timezone specified — it could be UTC, local, IST, or any other zone; the value itself does not record which. The moment you cross a process boundary, `naive` becomes ambiguous: the next machine has to *guess* the timezone, and different consumers guess differently.

The distinction is the entire reason `tzinfo` exists. Without the slot, every `datetime` would be naive, every comparison would be ambiguous, and every cross-process value would be a bug. The slot is the marker that pins a value to a specific zone; the absence of the slot (`tzinfo is None`) is the marker that the value is *not pinned* and therefore cannot be safely compared to a pinned one.

**Why is `tzinfo is None` the test and not `isinstance(dt, AwareDatetime)`?** Because Python does not have separate types for aware and naive `datetime`. The `datetime` class is one type; the awareness lives in the `tzinfo` slot. This was a design choice in PEP 0 (the original `datetime` PEP, predating the `abc` module): a single type with a nullable `tzinfo` field, where the field's value (set or `None`) carries the awareness. The trade-off is type-system simplicity (one `datetime` class, one set of methods) vs type-system strictness (the type checker cannot distinguish naive from aware at the annotation level). The discipline of "always store aware UTC" is what the application layer uses to compensate for the type-system's looseness.

### Lines 11–19: The `TypeError` — comparing naive to aware raises

```python
# 2. The TypeError — comparing naive to aware raises
try:
    print("naive < aware:", naive < aware)
except TypeError as e:
    print("TypeError:", e)

# 3. Subtracting naive from aware also raises
try:
    print("naive - aware:", naive - aware)
except TypeError as e:
    print("TypeError:", e)
```

`naive < aware` raises `TypeError: can't compare offset-naive and offset-aware datetimes`. The exception is raised by `datetime.__lt__` (and `__gt__`, `__eq__` is a separate case — see below). The reason is that the comparison is *meaningful only if both sides are on the same kind of clock*; comparing a wall-clock reading (naive) to an instant (aware) requires the type system to guess whether the naive value means UTC, local, or some other zone, and Python refuses to guess.

The same `TypeError` fires for subtraction: `naive - aware` raises. The arithmetic-rules lesson (lesson 02) walked the rule that `datetime - datetime` requires both sides to be either naive (both) or aware (both, with any tzinfo); the lesson 04 angle is that the `TypeError` is the loud signal that the comparison is meaningless, and the right fix is to make the naive side aware, not to make the aware side naive.

The exception is the production-saver. Without it, the comparison would silently return a wrong answer — `naive < aware` would be `True` or `False` based on the wall-clock readings alone, ignoring the timezone delta, and the application would compute "the ticket is overdue" or "the ticket is not overdue" based on a comparison that did not account for which timezone each value was in. The `TypeError` forces the bug to surface at the comparison line, in development, before it ships to production.

**Why does `==` not raise between naive and aware, but `<` does?** Because `datetime.__eq__` was defined in PEP 0 to return `False` (not raise) when comparing a naive and an aware value — the comparison is well-defined ("a naive `datetime` is never equal to an aware `datetime`") and returning `False` is unambiguous. The ordering comparisons (`<`, `>`, `<=`, `>=`) raise because the ordering is *not* well-defined without knowing the timezone of the naive side. The asymmetry is a deliberate choice: `==` returns a definite answer, `<` refuses to guess. Both are correct for their semantics.

### Lines 21–24: The right fix — make the naive value aware

```python
# 4. The fix: make the naive value aware (not the aware value naive!)
naive_fixed = naive.replace(tzinfo=timezone.utc)
print("naive_fixed.tzinfo:", naive_fixed.tzinfo)
print("naive_fixed < aware:", naive_fixed < aware)         # False — same instant
```

`naive.replace(tzinfo=timezone.utc)` returns a new `datetime` with the same wall-clock reading (`2026-10-23 12:00:00`) but with `tzinfo=timezone.utc` set. The `replace()` method takes any of the `datetime` fields as a keyword argument and returns a new instance with that field changed — `year`, `month`, `day`, `hour`, `minute`, `second`, `microsecond`, `tzinfo`, `fold`. The original is unchanged (immutable).

The crucial detail: `replace(tzinfo=...)` does *not* convert the wall-clock reading. It stamps the existing reading with the new `tzinfo` and trusts the caller's claim. So `naive.replace(tzinfo=timezone.utc)` asserts "this `2026-10-23 12:00:00` reading was actually a UTC reading" — and the comparison `naive_fixed < aware` now returns `False` because both are `2026-10-23 12:00:00 UTC`, the same instant. The fix is to make the naive side aware, *asserting* the timezone that the original constructor call forgot to specify.

The opposite direction — `aware.replace(tzinfo=None)` — is the wrong fix. It strips the offset off the aware value, making it naive, and the comparison stops raising. But the bug is still there: the aware value's wall-clock reading was UTC, the naive value's wall-clock reading was local (or UTC, or whatever the constructor meant), and the comparison is now silently wrong by the timezone delta. The right fix makes the silent value loud; the wrong fix makes the loud value silent.

**Why does `replace(tzinfo=...)` not convert the wall-clock reading?** Because `replace` is the *field-setter* API, not the *conversion* API. If you want to convert a wall-clock reading from one timezone to another, you call `astimezone(tz)` (the conversion API, see below), which *does* change the reading. `replace(tzinfo=...)` is for "I know what timezone this reading was taken in; stamp it"; `astimezone(tz)` is for "I have an aware value; show me the equivalent wall-clock reading in a different zone". The two are different operations; confusing them is a bug.

### Lines 26–33: `astimezone(tz)` — convert an aware `datetime` to another timezone

```python
# 5. astimezone: convert an aware datetime to another timezone
aware_utc = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
ny_tz = ZoneInfo("America/New_York")
aware_ny = aware_utc.astimezone(ny_tz)
print("aware UTC:  ", aware_utc)
print("aware NY:   ", aware_ny)
print("same instant (utc == ny):", aware_utc == aware_ny)   # True
```

`dt.astimezone(tz)` converts an aware `datetime` to another timezone. The method takes a `tzinfo` instance (here `ZoneInfo("America/New_York")`, an IANA timezone from Python 3.9+ PEP 615) and returns a new `datetime` whose wall-clock reading is the equivalent instant in the target timezone. The original instant is preserved — `aware_utc` and `aware_ny` represent the *same moment in time*, just printed with different wall-clock readings.

For `aware_utc = 2026-10-23 12:00:00 UTC`, the conversion to `America/New_York` (which is `-04:00` EDT in October 2026, observing DST) produces `aware_ny = 2026-10-23 08:00:00-04:00` — four hours earlier in wall-clock, but the same UTC instant. The `==` comparison returns `True` because the two values represent the same instant; `datetime.__eq__` for aware values normalises through UTC and compares the instants.

The `astimezone()` method is the *only* correct way to convert a wall-clock reading between timezones. `replace(tzinfo=...)` does not convert — it stamps. `astimezone()` does convert — it computes the wall-clock reading in the target zone that corresponds to the same instant as the source. The two are not interchangeable; using `replace` when you mean `astimezone` produces a value whose wall-clock reading is wrong by the timezone delta.

The `ZoneInfo("America/New_York")` import is from `zoneinfo` (Python 3.9+, PEP 615). The IANA timezone database is shipped with the OS (Linux/macOS) or via the `tzdata` PyPI package on Windows. The `ZoneInfo` class implements `tzinfo` and handles DST transitions correctly — the offset changes twice a year, and `ZoneInfo` knows the rules. Lesson 05 walks `ZoneInfo` in detail; this lesson uses it as the canonical IANA-timezone value for `astimezone`.

**Why does `aware_utc == aware_ny` return `True` when the wall-clock readings differ?** Because `datetime.__eq__` for two aware values normalises through UTC. The two values represent the same UTC instant (12:00 UTC = 08:00 EDT); the normalisation confirms they are the same moment; `__eq__` returns `True`. This is the behaviour you want — two values that mean the same moment should compare equal regardless of which timezone they are printed in. The `<` and `>` operators do the same normalisation, which is why `aware_utc < aware_ny` is `False` (they are equal, not less-than). The comparison is on the *instant*, not on the wall-clock reading.

### Lines 35–37: `astimezone(None)` — convert aware to system local

```python
# 6. astimezone(None) — convert aware to system local
system_local = aware_utc.astimezone()
print("system local:", system_local, "| tzinfo:", system_local.tzinfo)
```

`dt.astimezone()` with no argument (equivalent to `dt.astimezone(None)`) converts the aware `datetime` to the *system local timezone* — the timezone the operating system reports via the `TZ` environment variable or the OS timezone database. The result is an aware `datetime` whose `tzinfo` is a `datetime.timezone` instance representing the system's current offset from UTC (so for a London machine in October 2026, the result has `tzinfo=timezone(timedelta(hours=1))` for BST).

The system-local conversion is the *display* boundary's escape hatch — when you want to render a UTC value in the user's local time and you do not have an explicit user timezone, `astimezone()` produces the system-local reading. The catch is that the "system local" is the *server's* local timezone, not the *user's* — for a backend service running in a Tokyo data centre, `astimezone()` returns Tokyo time, which is wrong for a user in London. The discipline is: use `astimezone(ZoneInfo(user.timezone))` at the display boundary, with the user's timezone passed in from the request (a `timezone` field on the user model, an `Accept-Timezone` header, etc.); reserve `astimezone()` with no argument for log lines and CLI tools where the local-machine reading is the right answer.

**Why does `astimezone(None)` produce a `timezone` instance and not a `ZoneInfo`?** Because the system local timezone is a *fixed offset* (the offset the machine reports at the instant of the call), not a *named zone* (which would have DST rules). A `timezone(timedelta(hours=1))` instance correctly represents "the offset is +01:00 right now"; a `ZoneInfo("Europe/London")` instance would represent "the named zone is Europe/London, with DST rules". The two are different — the fixed offset is correct for the instant of the call but wrong for a date six months in the future (DST would change the offset); the named zone is correct for any date. The `astimezone(None)` call returns the fixed-offset form because it cannot know which named zone the system is in (the OS reports an offset, not a name).

### Lines 39–55: The store-aware-UTC-render-at-the-edge rule, in a boardly model

```python
# 7. The store-aware-UTC-render-at-the-edge rule
@dataclass
class Ticket:
    id: int
    summary: str
    deadline: datetime                              # always aware UTC; contract
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_overdue(self, now: datetime) -> bool:
        # both sides must be aware; the type system enforces this loudly
        return now > self.created_at + (self.deadline - self.created_at)


# A correct ticket — both fields aware UTC
t = Ticket(
    id=1,
    summary="login broken",
    deadline=datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc),
)
now = datetime(2026, 10, 23, 13, 0, 0, tzinfo=timezone.utc)
print("Ticket.is_overdue (within window):", t.is_overdue(now))    # False
```

The `Ticket` model is the production example. Every `datetime` field is aware UTC: `created_at` defaults to `datetime.now(timezone.utc)` (lesson 01); `deadline` requires an aware UTC `datetime` at construction (no default — the caller must pass one). The contract is enforced by the call site (the caller passes `datetime(..., tzinfo=timezone.utc)`) and *would* be enforced by a Pydantic `field_validator` in the API layer (lesson 05 walks that integration).

The `is_overdue(now)` predicate is the breach-check service in one line: `now > self.created_at + (self.deadline - self.created_at)`. The expression simplifies to `now > self.deadline` but writes it as "the deadline is the creation time plus the window" to make the contract explicit. The comparison is `datetime > datetime` — both sides aware (the caller passes `now = datetime.now(timezone.utc)`); the type system does the right thing; no `TypeError`.

The two `print` calls confirm: `t.is_overdue(now)` returns `False` because `now` (`2026-10-23 13:00 UTC`) is before `t.deadline` (`2026-10-24 12:00 UTC`). The ticket is within its 23-hour window (created at 12:00 UTC, deadline 24h later, now 1h after creation). The arithmetic is correct because every value is aware UTC; the comparison is safe because the type system normalises through UTC and the instants are well-defined.

**Why does the contract live at the model layer and not in a `field_validator`?** Because the dataclass is the *storage* layer — the place where the value enters the system and where it lives. A `field_validator` at the Pydantic layer (lesson 05) catches the bug at the *API* boundary, but only if every entry point is the API. For internal callers (background jobs, scripts, tests), the dataclass contract is the gate. The two-layer discipline (Pydantic `field_validator` for the API, dataclass contract for the internal model) is belt-and-suspenders; the bug is most easily caught at the *first* gate, which is whichever layer the caller hits first.

### Lines 57–60: Rendering in the user's timezone at the edge

```python
# 8. Rendering in the user's timezone at the edge
user_tz = ZoneInfo("America/New_York")
deadline_for_user = t.deadline.astimezone(user_tz)
print("deadline in user's tz:", deadline_for_user)
```

`t.deadline.astimezone(user_tz)` converts the aware UTC deadline to the user's timezone — `2026-10-24 08:00:00-04:00` for an `America/New_York` user in October 2026 (EDT, -04:00). The value is for *display* only; it is never stored, never serialised, never compared. The display boundary is the only place `astimezone` is called; the storage and comparison layers always work in UTC.

The discipline is: store aware UTC, compare aware UTC, render in the user's timezone at the edge. The "edge" is the API response layer (the FastAPI route that returns the ticket to the frontend), the HTML template layer (the Jinja2 template that renders the deadline in the user's local time), the email body layer (the rendered "your ticket is overdue" message). Every layer that produces output for a human calls `astimezone(user_tz)` on the UTC value; every layer that stores, computes, or compares works in UTC.

The user's timezone comes from the user model (`user.timezone`, an IANA name like `"America/New_York"`) or from the request (`Accept-Timezone` header, `timezone` query parameter). The frontend never sends a wall-clock reading; it sends an ISO 8601 string with the offset suffix, and the backend parses it to aware UTC at the boundary (lesson 05).

**Why render at the edge and not in the model layer?** Because the user's timezone is a *display* concern, not a *data* concern. The deadline's value is the same regardless of which user is reading it; only the *displayed* wall-clock reading differs. Putting `astimezone(user_tz)` in the model layer would couple the model to the user (every `Ticket` instance would need a `user_tz` field, or the method would need a `user_tz` argument), and the model would no longer be a pure data structure. The edge is the right place — the route handler has the user's timezone (from the authenticated request), the model does not.

### Lines 62–69: The bug the type system catches

```python
# 9. The bug that the type system catches
buggy_ticket = Ticket(
    id=2,
    summary="forgot tzinfo",
    deadline=datetime(2026, 10, 24, 12, 0, 0),   # ← naive — bug!
)
try:
    buggy_ticket.is_overdue(now)
except TypeError as e:
    print("buggy_ticket TypeError:", e)
```

The `buggy_ticket` is the junior-engineer bug — the `deadline` is constructed without `tzinfo=timezone.utc`, producing a naive `datetime`. The dataclass accepts it (the type annotation is `datetime`, not `AwareDatetime`); the constructor does not raise; the value is stored. The bug surfaces only at the `is_overdue(now)` call, where `self.deadline - self.created_at` (a subtraction, used to compute the SLA window) raises `TypeError: can't subtract offset-naive and offset-aware datetimes` because `self.created_at` is aware UTC and `self.deadline` is naive. The exception fires before the `>` comparison is even reached.

The exception message names the bug *exactly* — "offset-naive and offset-aware". The "offset" is the UTC offset recorded in the `tzinfo` slot; "naive" means no offset (the `tzinfo is None` case); "aware" means an offset is set. The fix is the right direction: `buggy_ticket.deadline = buggy_ticket.deadline.replace(tzinfo=timezone.utc)` — assert the timezone the constructor forgot to specify. The wrong fix is `now.replace(tzinfo=None)` or `buggy_ticket.created_at.replace(tzinfo=None)` — strip the awareness off the value that was correctly stored.

The lesson is: the `TypeError` is your friend. It tells you the value's meaning is ambiguous before the comparison silently returns a wrong answer. Do not suppress it; do not "fix" it by stripping awareness; do fix it by adding awareness. The cardinal rule "never let a naive `datetime` past the parse boundary" prevents the bug from being written in the first place; the `TypeError` catches the bug if the rule is broken.

### Lines 71–77: The DST fold case — `astimezone` handles it correctly

```python
# 10. The DST fold case — astimezone handles it correctly
# 2026-11-01 01:30 in America/New_York occurs twice (EDT -> EST fall-back)
dst_instant_utc = datetime(2026, 11, 1, 5, 30, 0, tzinfo=timezone.utc)
edt_reading = dst_instant_utc.astimezone(ny_tz)              # fold=0 (EDT, offset -04:00)
est_reading = dst_instant_utc.astimezone(ny_tz).replace(fold=1)  # fold=1 (EST, offset -05:00)
print("DST instant UTC:", dst_instant_utc)
print("NY (fold=0 EDT):", edt_reading, "tzname:", edt_reading.tzname())
print("NY (fold=1 EST):", est_reading, "tzname:", est_reading.tzname())
print("== (same tzinfo quirk):", edt_reading == est_reading)    # True — wall-clock compare, NOT same instant
print("normalise via UTC:  ", edt_reading.astimezone(timezone.utc) == est_reading.astimezone(timezone.utc))   # False
```

The DST fold case is the deepest part of the aware-vs-naive distinction. On 2026-11-01 in `America/New_York`, the clocks fall back from EDT (`-04:00`) to EST (`-05:00`) at 02:00 — so the wall-clock reading `01:30` *occurs twice*: once at 01:30 EDT (the UTC instant `05:30`) and once at 01:30 EST (the UTC instant `06:30`). A naive `datetime(2026, 11, 1, 1, 30)` is ambiguous — it could be either. A `ZoneInfo`-aware `datetime` with `fold=0` is the first occurrence (EDT); with `fold=1` is the second (EST). The `fold` attribute (PEP 495, Python 3.6+) is the disambiguator.

The `dst_instant_utc = datetime(2026, 11, 1, 5, 30, 0, tzinfo=timezone.utc)` is the *first* occurrence — 01:30 EDT = 05:30 UTC. `astimezone(ny_tz)` produces a `datetime` with `fold=0` (the default), `tzname=EDT`, and offset `-04:00`. Calling `.replace(fold=1)` on that result produces a *different* `datetime`: same wall-clock (`01:30`), same `tzinfo` object (the `ZoneInfo` is preserved by `replace`), but `fold=1`. The `fold` attribute changes which offset `ZoneInfo` reports for that wall-clock — `utcoffset()` now returns `-05:00` (EST) instead of `-04:00` (EDT), and `tzname()` returns `"EST"`. The new value therefore represents a *different* UTC instant: `01:30 - (-05:00) = 06:30 UTC`, not the original `05:30 UTC`.

The `==` comparison `edt_reading == est_reading` returns `True` — but the reason is subtle. CPython's `datetime.__eq__` for two aware datetimes that *share the same `tzinfo` object* (as `edt_reading` and `est_reading` do, because `replace(fold=1)` preserves the tzinfo) compares the *wall-clock fields* directly, *ignoring* the offsets. Both have wall-clock `2026-11-01 01:30:00`, so the comparison returns `True`. The two values are *not* the same UTC instant (`edt_reading.astimezone(timezone.utc)` is `05:30`; `est_reading.astimezone(timezone.utc)` is `06:30`), but `==` does not normalise through UTC when the `tzinfo` is shared. To compare the actual instants, normalise explicitly: `edt_reading.astimezone(timezone.utc) == est_reading.astimezone(timezone.utc)` returns `False`, or compare `.timestamp()` values (`1793511000.0` vs `1793514600.0` — a one-hour delta). The rule: when comparing aware datetimes that share a `ZoneInfo` tzinfo across a DST fold boundary, *normalise through UTC explicitly* — the bare `==` does not catch the difference.

**Why does the lesson show the DST fold case if the cardinal rule is "store aware UTC"?** Because the case arises when you convert an aware UTC value to a `ZoneInfo` timezone for display — the display layer has to handle the fold. If the user is in `America/New_York` and the deadline's UTC instant is `2026-11-01 05:30:00 UTC`, the display layer's `astimezone(ny_tz)` produces a wall-clock reading of `01:30` with `fold=0` (EDT). If the user reads the value as `01:30 EDT` and asks "what about the *other* 01:30 — the EST one?", the display layer has to know the fold attribute to answer. For most applications, the default `fold=0` is correct; for calendar applications, scheduling systems, and any UI that asks the user "which 01:30 do you mean?", the `fold` attribute is the API. The `==` quirk is the trap the test in the demo is meant to expose — `edt_reading == est_reading` is `True`, but the two values represent different instants, and only normalising through UTC reveals it.

## Execution Trace

```bash
$ uv run python boardly/breach/aware_vs_naive.py
aware.tzinfo: UTC | is None: False
naive.tzinfo: None | is None: True
TypeError: can't compare offset-naive and offset-aware datetimes
TypeError: can't subtract offset-naive and offset-aware datetimes
naive_fixed.tzinfo: UTC
naive_fixed < aware: False
aware UTC:   2026-10-23 12:00:00+00:00
aware NY:    2026-10-23 08:00:00-04:00
same instant (utc == ny): True
system local: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Ticket.is_overdue (within window): False
deadline in user's tz: 2026-10-24 08:00:00-04:00
buggy_ticket TypeError: can't subtract offset-naive and offset-aware datetimes
DST instant UTC: 2026-11-01 05:30:00+00:00
NY (fold=0 EDT): 2026-11-01 01:30:00-04:00 tzname: EDT
NY (fold=1 EST): 2026-11-01 01:30:00-05:00 tzname: EST
== (same tzinfo quirk): True
normalise via UTC:   False
```

The `system local` value is the runtime system timezone (UTC on this sandbox); it may differ on a London or Tokyo machine. The DST fold trace is deterministic. Note the `==` quirk: `== (same tzinfo quirk): True` even though the two values represent different UTC instants (`05:30` vs `06:30`) — see the prose for why (CPython's `__eq__` for two aware datetimes sharing the same `tzinfo` object compares wall-clock fields, ignoring offsets). Normalising both through `astimezone(timezone.utc)` reveals the real relationship: `normalise via UTC: False`.

## Common Mistakes

### Mistake 1: Suppressing the `TypeError` by stripping awareness

```python
aware_now = datetime.now(timezone.utc)
naive_deadline = datetime(2026, 12, 31, 23, 59, 59)         # naive — bug
if aware_now > naive_deadline.replace(tzinfo=None):          # ← wrong fix
    print("overdue")
```

**Symptom:** The `TypeError` goes away. The comparison produces a result. The result is silently wrong — it does not account for the timezone delta between the (UTC) `now` and the (unknown-timezone) `deadline`.
**Why:** `replace(tzinfo=None)` strips the awareness off the value that was correctly stored, making it naive. The comparison `aware > naive` still raises, so the engineer suppresses it on the *aware* side instead — `aware.replace(tzinfo=None) > naive` works, but both sides are now naive and the comparison is on wall-clock readings alone, with no offset normalisation.
**Fix:** Make the naive side aware: `aware_now > naive_deadline.replace(tzinfo=timezone.utc)`. This asserts "the naive deadline was actually a UTC reading" and lets the comparison normalise through UTC. If you do not know which timezone the naive value was meant to be in, you have a *data* bug — the value should never have been stored naive, and the fix is at the storage layer, not the comparison layer.

### Mistake 2: Using `replace(tzinfo=...)` when you mean `astimezone(tz)`

```python
utc_deadline = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
ny_deadline = utc_deadline.replace(tzinfo=ZoneInfo("America/New_York"))   # ← wrong
# ny_deadline is 2026-10-23 12:00:00-04:00 — same wall-clock, different offset
# this is NOT the same instant as utc_deadline; it is 4 hours later
```

**Symptom:** The converted value has the same wall-clock reading as the source but a different offset suffix. The two values are *not* the same instant; the conversion has shifted the value by the timezone delta.
**Why:** `replace(tzinfo=...)` is the *field-setter* API — it stamps the existing reading with a new `tzinfo` and does not change the wall-clock. `astimezone(tz)` is the *conversion* API — it computes the wall-clock reading in the target zone for the same instant.
**Fix:** Use `astimezone(tz)` for conversion: `ny_deadline = utc_deadline.astimezone(ZoneInfo("America/New_York"))` produces `2026-10-23 08:00:00-04:00` — the same UTC instant, four hours earlier in NY wall-clock. Reserve `replace(tzinfo=...)` for stamping a naive value with the timezone you know it was taken in.

### Mistake 3: Storing naive `datetime` values and treating them as UTC

```python
created_at = datetime.now()                  # naive local — could be UTC, could be BST
stored = created_at.isoformat()              # '2026-10-23T12:00:00' — no suffix
# downstream parsers guess the timezone; the value is ambiguous
```

**Symptom:** The stored value has no `+00:00` suffix. Postgres `to_timestamp` treats it as UTC; JavaScript `new Date` treats it as local; Go `time.Parse(time.RFC3339, ...)` rejects it. The value's meaning drifts by the timezone delta between the writer and the reader.
**Why:** `datetime.now()` returns naive local time with `tzinfo=None`; `isoformat()` faithfully records the absence of the offset. The downstream parser has to guess.
**Fix:** Store aware UTC: `created_at = datetime.now(timezone.utc)`. The stored value has the `+00:00` suffix, every downstream parser knows the value is UTC, and the round-trip is unambiguous. Lesson 01 walked this rule; lesson 04 reinforces it with the `TypeError` that catches the bug if the rule is broken.

### Mistake 4: Calling `astimezone()` with no argument on a backend service

```python
# A backend service running in a Tokyo data centre
local_deadline = utc_deadline.astimezone()   # Tokyo time — wrong for a London user
```

**Symptom:** The displayed value is in the *server's* local timezone, not the *user's*. A user in London sees Tokyo wall-clock readings and is confused.
**Why:** `astimezone()` with no argument uses the *system* timezone, which on a backend server is the data centre's timezone — not the user's. The conversion is correct for the server's local context but wrong for the user's display context.
**Fix:** Pass the user's timezone explicitly: `utc_deadline.astimezone(ZoneInfo(user.timezone))` where `user.timezone` is the IANA name from the user model. Reserve `astimezone()` (no argument) for log lines and CLI tools where the local-machine reading is the right answer.

## Engineering Trade-Offs

**Decision:** Store every `datetime` field as aware UTC. Compare aware UTC to aware UTC. Render in the user's timezone at the edge (the API response, the HTML template, the email body) using `astimezone(ZoneInfo(user.timezone))`. Never call `astimezone()` with no argument in a backend service.
**Both sides:** The alternative is to store naive local time — what `datetime.now()` returns and what older codebases do. Naive local is *simpler to display* (the wall-clock value is the displayed value) but it is *ambiguous the moment it crosses a process boundary* and it raises `TypeError` when compared to an aware value. Aware UTC is *unambiguous* (the same instant on every machine, in every timezone) and *comparable* (the type system normalises through UTC), but it requires a conversion step at the display boundary. The trade-off is "simple display, ambiguous storage, `TypeError` on comparison" vs "explicit conversion, unambiguous storage, safe comparison". For a backend service that runs in one data centre today and another tomorrow, the aware UTC commitment is non-negotiable.
**Commitment:** `boardly` stores every `created_at`, `updated_at`, and `deadline` as aware UTC. The `Ticket` dataclass requires `deadline: datetime` to be aware (the contract is enforced at the call site, and would be enforced by a Pydantic `field_validator` in the API layer — lesson 05). The `is_overdue(now)` predicate compares aware-to-aware and depends on the type system's `TypeError` to catch any naive value that slips through. The display layer calls `astimezone(ZoneInfo(user.timezone))` at the edge; the storage and comparison layers never convert. This is the rule the section depends on; the rest of the lessons (01, 02, 03, 05) build on it.

## Exercises

1. **Exercise 1 — Reproduce the `TypeError`.** Construct a naive `datetime(2026, 10, 23, 12, 0, 0)` and an aware `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)`. Try `naive < aware` and confirm `TypeError: can't compare offset-naive and offset-aware datetimes`. `Verify: uv run python -c "from datetime import datetime, timezone; n=datetime(2026,10,23,12); a=datetime(2026,10,23,12,tzinfo=timezone.utc); 
try:
 n<a
except TypeError as e: print('TypeError:', e)"`
2. **Exercise 2 — Fix the naive value.** Use `.replace(tzinfo=timezone.utc)` on the naive value from Exercise 1. Confirm the comparison now returns `False` (both are the same UTC instant). `Verify: uv run python -c "from datetime import datetime, timezone; n=datetime(2026,10,23,12).replace(tzinfo=timezone.utc); a=datetime(2026,10,23,12,tzinfo=timezone.utc); print(n<a)"`
3. **Exercise 3 — Verify `astimezone` preserves the instant.** Construct `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)`, call `.astimezone(ZoneInfo("America/New_York"))`, and confirm the two values are `==` (same instant). `Verify: uv run python -c "from datetime import datetime, timezone; from zoneinfo import ZoneInfo; a=datetime(2026,10,23,12,tzinfo=timezone.utc); b=a.astimezone(ZoneInfo('America/New_York')); print(a==b)"`
4. **Exercise 4 — Reproduce the DST fold.** Construct `datetime(2026, 11, 1, 5, 30, 0, tzinfo=timezone.utc)`, call `.astimezone(ZoneInfo("America/New_York"))` to get the EDT reading (`tzname()` returns `"EDT"`), and call `.replace(fold=1)` to get the EST reading (`tzname()` returns `"EST"`). Confirm the two values are `==`. `Verify: uv run python -c "from datetime import datetime, timezone; from zoneinfo import ZoneInfo; tz=ZoneInfo('America/New_York'); a=datetime(2026,11,1,5,30,tzinfo=timezone.utc).astimezone(tz); b=a.replace(fold=1); print(a.tzname(), b.tzname(), a==b)"`
5. **Exercise 5 — Build a `to_user_display` method.** Add `def to_user_display(self, user_tz: str) -> str: return self.deadline.astimezone(ZoneInfo(user_tz)).isoformat()` to the `Ticket` dataclass. Confirm `t.to_user_display("America/New_York")` returns `2026-10-24T08:00:00-04:00`. `Verify: uv run python -c "import sys; sys.path.insert(0,'.'); from boardly.breach.aware_vs_naive import Ticket; from datetime import datetime, timezone; t=Ticket(id=1,summary='x',deadline=datetime(2026,10,24,12,tzinfo=timezone.utc)); print(t.to_user_display('America/New_York'))"`

## Verification

```bash
$ uv run python boardly/breach/aware_vs_naive.py
aware.tzinfo: UTC | is None: False
naive.tzinfo: None | is None: True
TypeError: can't compare offset-naive and offset-aware datetimes
TypeError: can't subtract offset-naive and offset-aware datetimes
naive_fixed.tzinfo: UTC
naive_fixed < aware: False
aware UTC:   2026-10-23 12:00:00+00:00
aware NY:    2026-10-23 08:00:00-04:00
same instant (utc == ny): True
system local: 2026-10-23 12:00:00+00:00 | tzinfo: UTC
Ticket.is_overdue (within window): False
deadline in user's tz: 2026-10-24 08:00:00-04:00
buggy_ticket TypeError: can't subtract offset-naive and offset-aware datetimes
DST instant UTC: 2026-11-01 05:30:00+00:00
NY (fold=0 EDT): 2026-11-01 01:30:00-04:00 tzname: EDT
NY (fold=1 EST): 2026-11-01 01:30:00-05:00 tzname: EST
== (same tzinfo quirk): True
```

## Previously Learned Here

- [[15-datetime/01-datetime-and-timezone]] — the `tzinfo` slot, `timezone.utc`, and the aware-UTC rule that this lesson enforces. The `TypeError` is the type system's enforcement mechanism for the contract lesson 01 stated.
- [[15-datetime/02-timedelta]] — `datetime - datetime -> timedelta` arithmetic; the same `TypeError` fires for subtraction as for ordering comparison.
- [[15-datetime/03-ISO-8601-format]] — the `+00:00` suffix in the serialised form is the visible marker of awareness; the absence of the suffix is the visible marker of naivety.

## What's Next

[[15-datetime/05-fromisoformat-and-parsing]] — Now that you can detect naivety and convert aware values across timezones, you need the *parse* boundary: how an ISO 8601 string from a webhook payload becomes an aware `datetime`. Lesson 05 walks `datetime.fromisoformat(s)` (Python 3.7+; extended in 3.11+ to handle more ISO 8601 variants — version-gated), `datetime.fromtimestamp(ts, tz=...)` (always pass `tz=timezone.utc`), `zoneinfo.ZoneInfo(key)` (3.9+, PEP 615) for IANA timezone names, and the "if the format is ISO, use stdlib; otherwise use `dateutil`" rule.

- **Lesson 05** — `fromisoformat()`, `fromtimestamp()`, `zoneinfo`, parsing at the boundary.

## Sources

- **Python `datetime` module documentation — aware vs naive** — https://docs.python.org/3/library/datetime.html#aware-and-naive-objects — accessed 2026-10-23 — the canonical CPython definition of "aware" (`tzinfo` set, offset known) vs "naive" (`tzinfo is None`, offset unknown), and the rule that comparisons between the two raise `TypeError`.
- **Python `datetime` module documentation — `datetime.astimezone()`** — https://docs.python.org/3/library/datetime.html#datetime.datetime.astimezone — accessed 2026-10-23 — the conversion method that takes an aware `datetime` and returns a new aware `datetime` in the target timezone, preserving the instant.
- **PEP 495 — Local Time Disambiguation** — https://peps.python.org/pep-0495/ — accessed 2026-10-23 — the `fold` attribute (Python 3.6+) that disambiguates the two wall-clock readings of an ambiguous DST fall-back transition; source for the fold case in this lesson.
- **`zoneinfo` — IANA time zone support** — https://docs.python.org/3/library/zoneinfo.html — accessed 2026-10-23 — the `ZoneInfo` class (Python 3.9+, PEP 615) used by `astimezone()` for IANA-named timezones; lesson 05 walks it in detail.

## What We Learned

- You can now read `dt.tzinfo is None` to detect a naive `datetime` and explain why `is None` is the right comparison (not `== None`, not `not dt.tzinfo`).
- You can trigger and read the `TypeError: can't compare offset-naive and offset-aware datetimes` exception that catches the bug when a naive value slips into a comparison.
- You can use `dt.astimezone(tz)` to convert an aware `datetime` from one timezone to another (preserving the instant), and explain why `replace(tzinfo=...)` is the wrong tool for conversion.
- You can state the cardinal rule: store aware UTC, compare aware UTC, render in the user's timezone at the edge using `astimezone(ZoneInfo(user.timezone))`, and never let a naive `datetime` past the parse boundary.
- You can read the `fold` attribute (PEP 495) that disambiguates the two wall-clock readings of a DST fall-back transition, and explain why `fold` is for display disambiguation, not for instant disambiguation.
