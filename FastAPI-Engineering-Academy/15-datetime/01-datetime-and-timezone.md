---
title: "Lesson 01: datetime and timezone"
aliases:
 - datetime
 - datetime.datetime
 - datetime.timezone
 - datetime.tzinfo
 - aware UTC
 - timezone.utc
tags:
 - datetime
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[15-datetime/02-timedelta]]"
 - "[[15-datetime/04-timezone-aware-vs-naive]]"
first_taught_in: "15-datetime/01-datetime-and-timezone"
---

# Lesson 01: datetime and timezone

*Why `boardly`'s `Ticket.created_at` is `datetime.now(timezone.utc)` and never `datetime.now()` — and the `tzinfo` field that distinguishes "an instant in time" from "a wall-clock reading with no meaning".*

**You're at the very beginning of Section 15.**

You have written `from datetime import datetime` and then `datetime.now()` and pasted the result into a database column, and been fine — until the day your service moves from a London data centre to a Tokyo one, and every `created_at` reading jumps nine hours, and the audit log no longer agrees with itself. This lesson shows you the standard-library fix: the `datetime.datetime` type with its `tzinfo` slot, the `datetime.timezone` concrete class, and the one-line rule that makes every timestamp in your system unambiguous — `datetime.now(timezone.utc)`, never `datetime.now()`. Take your time. Type every example. **This is how you learn.**

#datetime #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `datetime`** — write `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)` and explain what each of `year`/`month`/`day`/`hour`/`minute`/`second`/`microsecond`/`tzinfo`/`fold` means.
2. **Distinguish `date`, `time`, `datetime`, and `timedelta`** — name what each type represents and which one you reach for at which boundary.
3. **Explain the `tzinfo` slot** — `tzinfo=None` means naive (no timezone), `tzinfo=<instance>` means aware; `datetime.tzinfo` is the abstract base, `datetime.timezone` is the concrete fixed-offset subclass, `datetime.timezone.utc` is the singleton UTC instance.
4. **Read the `now(tz=...)` constructor** — `datetime.now()` returns naive local time, `datetime.now(timezone.utc)` returns aware UTC, and `datetime.utcnow()` is deprecated in 3.12 (and you should never call it).
5. **State the rule** the rest of the section depends on: store aware UTC, render in the user's timezone at the edge, and never let a naive `datetime` past the parse boundary.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. The boardly model uses `created_at: datetime`, and you need to be comfortable reading an annotation as a contract.
- **A typed model to attach the field to** — [[06-dataclasses/01-dataclass-Basics]]. This lesson writes `created_at: datetime` on a `Ticket` dataclass; the `@dataclass` machinery is taught in the dataclass lesson.
- **About 30–45 minutes of focused time.**

**The most common gap: treating `datetime` as "a timestamp, no further thought required".**

It is not. A `datetime` is *either* a fully-specified instant (an aware datetime, where the `tzinfo` slot pins it to UTC or a named zone) *or* an under-specified wall-clock reading (a naive datetime, where `tzinfo is None` and the value is ambiguous the moment it leaves the process). The single biggest mistake students make in this section is writing `datetime.now()` and treating the result as UTC — it is local time, naive, and indistinguishable from UTC at the type level until you compare two of them and get a `TypeError`. The fix is to never let `tz=None` survive past the constructor. `datetime.now(timezone.utc)` is the only call you should be making. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/tickets/bad_created_at.py — the bad old days
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime        # ← looks reasonable, isn't


# A new ticket — call .now(), paste the result
t = Ticket(id=1, summary="login broken", created_at=datetime.now())
print(t.created_at)             # 2026-10-23 07:00:03.957962 — local, naive
print(t.created_at.tzinfo)      # None — there is no timezone here
```

The dataclass accepts the value, the repr looks plausible, the field type is `datetime`, and the moment this code runs in two different data centres the values stop agreeing. `datetime.now()` returns the *local* time of the machine that ran it, with `tzinfo=None`. There is no UTC marker. There is no offset. There is nothing in the value itself that tells a downstream reader which timezone the reading was taken in — they have to *assume*, and assumptions about timezones are how production incidents start.

This is not a Python problem. It is a "wall-clock vs instant" problem. Every language with a datetime type has the same trap: Java's `java.util.Date` was naive for years before `java.time.Instant` arrived; JavaScript's `Date` is still naive-UTC-flavoured; Go's `time.Time` got it right by making the location mandatory. Python's answer is the `tzinfo` slot: a `datetime` whose `tzinfo` is set is an instant; a `datetime` whose `tzinfo` is `None` is a wall-clock reading that does not pin to any particular timezone.

The `datetime` module is the standard-library answer to "I need a value that means a specific instant, on any machine, in any timezone, that round-trips through any storage layer". `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)` is an instant — twelve hundred hours UTC on 2026-10-23, the same instant in Tokyo as in London, the same value when stored in Postgres and read back, the same value when serialised to ISO 8601 and re-parsed. The fix to the bug is one word: pass `tzinfo=timezone.utc`, or call `datetime.now(timezone.utc)` instead of `datetime.now()`.

## The Code

```python
# boardly/tickets/datetime_and_timezone.py
"""The datetime type, the tzinfo slot, the timezone concrete class, and the
aware-UTC rule that every boardly timestamp depends on."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone, tzinfo


# 1. The constructor: every kwarg, including fold
instant = datetime(
    2026, 10, 23, 12, 0, 0, 0,
    tzinfo=timezone.utc,
    fold=0,
)
print("instant:", instant)
print("tzinfo is None:", instant.tzinfo is None)
print("tzname:", instant.tzname())
print("utcoffset:", instant.utcoffset())

# 2. The four companion types
print("date:", date(2026, 10, 23))
print("time:", time(12, 0, 0, tzinfo=timezone.utc))
print("timedelta:", timedelta(hours=1))

# 3. tzinfo is an abstract base; timezone is the concrete fixed-offset subclass
print("tzinfo is subclass-of object (no ABC enforcement):", isinstance(tzinfo(), object))
print("timezone is a tzinfo subclass:", isinstance(timezone.utc, tzinfo))

# 4. timezone.utc singleton; fixed-offset for India (+05:30)
utc = timezone.utc
ist = timezone(timedelta(hours=5, minutes=30))
print("utc.utcoffset(None):", utc.utcoffset(None))
print("ist.utcoffset(None):", ist.utcoffset(None))

# 5. now(tz=None) — naive local; now(timezone.utc) — aware UTC
naive_now = datetime.now()                # ← don't do this in production
aware_utc = datetime.now(timezone.utc)    # ← do this instead
print("naive_now.tzinfo:", naive_now.tzinfo)            # None
print("aware_utc.tzinfo:", aware_utc.tzinfo)            # UTC

# 6. utcnow() is deprecated in 3.12 — emits DeprecationWarning
# datetime.utcnow()  # ← do not call; use datetime.now(timezone.utc)

# 7. The boardly Ticket model — created_at is aware UTC, always
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


t = Ticket(id=1, summary="login broken")
print("Ticket.created_at:", t.created_at)
print("Ticket.created_at.tzinfo:", t.created_at.tzinfo)

# 8. The deadline — Project with an aware UTC deadline
@dataclass
class Project:
    id: int
    name: str
    deadline: datetime                       # always aware; see lesson 04


p = Project(id=1, name="alpha", deadline=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
print("Project.deadline:", p.deadline)
print("Project.deadline.tzinfo:", p.deadline.tzinfo)
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–11: Imports and the constructor with every kwarg

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone, tzinfo


# 1. The constructor: every kwarg, including fold
instant = datetime(
    2026, 10, 23, 12, 0, 0, 0,
    tzinfo=timezone.utc,
    fold=0,
)
print("instant:", instant)
print("tzinfo is None:", instant.tzinfo is None)
print("tzname:", instant.tzname())
print("utcoffset:", instant.utcoffset())
```

The `from datetime import datetime, date, time, timedelta, timezone, tzinfo` line pulls the six names you will use all lesson. The module exports five *types* (`datetime`, `date`, `time`, `timedelta`, `timezone`) and one *abstract base class* (`tzinfo`). Note that `datetime` is *both* the module name and a class inside it — the `from datetime import datetime` form disambiguates by binding the class to the name `datetime` in your namespace. If you prefer the module-qualified form, write `import datetime` and then `datetime.datetime(2026, 10, 23, ...)`.

The constructor signature is `datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None, *, fold=0)`. `year`/`month`/`day` are required positional arguments; `hour`/`minute`/`second`/`microsecond` default to zero; `tzinfo` defaults to `None` (naive); `fold` is keyword-only and defaults to `0`. The `fold` argument is PEP 495 (Python 3.6+) — it disambiguates the two readings of a wall-clock time that occur during a DST fall-back transition (the clock hits 01:30 twice on the night the US clocks fall back from EDT to EST). `fold=0` is the *first* occurrence (the EDT reading); `fold=1` is the *second* (the EST reading). You will rarely construct a `fold` value by hand; you will meet it again in lesson 04 when you call `astimezone()` across a DST boundary.

The four `print` calls expose the basic accessors. `instant.tzinfo` is the slot itself — here `timezone.utc` (printed as `UTC` by its `__repr__`); `instant.tzinfo is None` is `False` because we set it. `instant.tzname()` calls the `tzinfo`'s `tzname()` method and returns a string like `"UTC"` (it is `tzname`, not `tzinfo`, that produces the abbreviation). `instant.utcoffset()` returns the offset from UTC as a `timedelta` — here `timedelta(0)` printed as `0:00:00`.

**Why is `fold` keyword-only?** Because every other argument is positional and you can pass seven of them (`year, month, day, hour, minute, second, microsecond`) without thinking; if `fold` were positional it would be the eighth positional argument and you would write `datetime(2026, 10, 23, 1, 30, 0, 0, 0, 1)` and no reader would know whether the trailing `1` was a microsecond or a fold. Making `fold` keyword-only forces the call site to name it (`fold=1`) and the intent becomes readable. This is the same design choice as `bool` vs `int` no longer being a positional `*args` in `dict` — Python's standard library increasingly uses `*` to separate required-from-the-front from by-name-only.

### Lines 13–16: The four companion types

```python
# 2. The four companion types
print("date:", date(2026, 10, 23))
print("time:", time(12, 0, 0, tzinfo=timezone.utc))
print("timedelta:", timedelta(hours=1))
```

The `datetime` module exports four sibling types and a `tzinfo` abstract base. Each one represents a *different question*:

- `date(year, month, day)` — a calendar date with no time-of-day and no timezone. You use it for "this ticket's due date is 2026-10-23" where the time of day is irrelevant.
- `time(hour, minute, second, microsecond, tzinfo, fold)` — a time-of-day with no date. You use it for "the stand-up is at 09:30" where the date is irrelevant. A `time` can be aware (`tzinfo` set) or naive (`tzinfo is None`).
- `datetime(year, month, day, hour, minute, second, microsecond, tzinfo, fold)` — a date *and* a time-of-day, with an optional timezone. This is the workhorse: every `created_at`, every `updated_at`, every `deadline`, every event timestamp in `boardly` is a `datetime`.
- `timedelta(days=0, seconds=0, microseconds=0, ...)` — a *duration* between two `datetime` (or `date`, or `time`) values. Lesson 02 is the deep dive on `timedelta`; the constructor takes `weeks`, `days`, `hours`, `minutes`, `seconds`, `milliseconds`, `microseconds` and normalises them internally.

**Why are `date` and `time` separate types and not just `datetime` with `hour=0`?** Because the *meaning* of "09:30" with no date is genuinely different from "2026-10-23 09:30" — the former is a recurring rule (every weekday at 09:30, the stand-up happens) and the latter is a single event. Conflating the two is how you ship bugs like "the meeting reminder fires for the wrong day because the calendar library assumed a date where there was none". The four types exist because the four kinds of question — "what day?", "what time?", "what instant?", "how long?" — are different, and the type system should tell you which one you are answering.

### Lines 18–20: `tzinfo` is abstract; `timezone` is the concrete subclass

```python
# 3. tzinfo is an abstract base; timezone is the concrete fixed-offset subclass
print("tzinfo is subclass-of object (no ABC enforcement):", isinstance(tzinfo(), object))
print("timezone is a tzinfo subclass:", isinstance(timezone.utc, tzinfo))
```

The `tzinfo` class is the abstract base for *every* timezone implementation. Its methods — `utcoffset(dt)`, `dst(dt)`, `tzname(dt)`, `fromutc(dt)` — are stubs that raise `NotImplementedError` when called on a bare `tzinfo` instance. The class does *not* use `abc.ABCMeta` to enforce the contract at construction time: `tzinfo()` does not raise. But the moment you call `tzinfo().utcoffset(None)`, Python raises `NotImplementedError: a tzinfo subclass must implement utcoffset()`. The abstractness is enforced at method-call time, not at `__init__` time — a design choice that predates the `abc` module and was kept for backwards compatibility.

`timezone` is the concrete subclass that ships with the standard library. It represents a *fixed* UTC offset — a constant `+HH:MM` or `-HH:MM` that does not change with the seasons. `timezone(timedelta(hours=5, minutes=30))` is India's offset (IST, +05:30) — but it is *not* India's *timezone*, because India does not observe DST and the offset is constant, so the fixed-offset type is correct here. For timezones with DST (`America/New_York`, `Europe/London`, `Australia/Sydney`), a fixed-offset `timezone` is *wrong* — the offset changes twice a year, and the `timezone` class cannot represent that. For DST-observing zones, you need `zoneinfo.ZoneInfo` (lesson 05).

The line `isinstance(timezone.utc, tzinfo)` returns `True` because `timezone` subclasses `tzinfo`. Every value you put in the `tzinfo` slot — whether a `timezone.utc` singleton, a `timezone(timedelta(hours=5, minutes=30))` for India, or a `ZoneInfo("America/New_York")` for New York — is an instance of `tzinfo`. That is the type the `datetime` constructor accepts in that slot.

**Why does the stdlib ship both `tzinfo` (abstract) and `timezone` (concrete)?** Because the abstract base is the *contract* the `datetime` type checks against (`isinstance(x, tzinfo)`), and the concrete subclass is the *simplest* implementation that satisfies it. You can subclass `tzinfo` yourself to implement a custom timezone — and the standard library's `zoneinfo` module does exactly that. The two-tier design lets you write `tzinfo`-aware code (`dt.astimezone(some_tzinfo)`) without locking yourself to one implementation; the abstract base is the interface, the concrete class is the default.

### Lines 22–25: The `timezone.utc` singleton and a fixed-offset for India

```python
# 4. timezone.utc singleton; fixed-offset for India (+05:30)
utc = timezone.utc
ist = timezone(timedelta(hours=5, minutes=30))
print("utc.utcoffset(None):", utc.utcoffset(None))
print("ist.utcoffset(None):", ist.utcoffset(None))
```

`timezone.utc` is a singleton instance of `timezone` with offset `timedelta(0)` — the UTC timezone. It is the value you should pass to `datetime.now(timezone.utc)` and to `datetime(..., tzinfo=timezone.utc)` whenever you mean "this is a UTC instant". The stdlib also exposes `datetime.UTC` (**Python 3.11+**, an alias for `timezone.utc`) — `import datetime; datetime.UTC is datetime.timezone.utc` is `True`. Either name works on 3.12; the long-form `timezone.utc` is the cross-version-safe form (it works on 3.7+ where `datetime.UTC` does not exist). Note that `datetime.UTC` is a *module*-level attribute, not a class attribute — `from datetime import datetime; datetime.UTC` raises `AttributeError` because the name `datetime` in your namespace is bound to the class, not the module. Use `import datetime` if you need the `datetime.UTC` alias.

`timezone(timedelta(hours=5, minutes=30))` constructs a fixed-offset timezone for India Standard Time. The argument is a `timedelta` representing the offset from UTC; positive means east of the prime meridian. `ist.utcoffset(None)` returns `timedelta(hours=5, minutes=30)` printed as `5:30:00`. The `None` argument is the `dt` parameter — for a `timezone` (fixed-offset) it is ignored because the offset does not depend on the date; for a `ZoneInfo` it is required because the offset depends on whether DST is in effect.

**Why is `timezone.utc` a singleton and not a class?** Because there is exactly one UTC offset (zero) and it never changes; constructing a new `timezone(timedelta(0))` instance every time would be wasteful and would break `is` comparisons. The singleton pattern lets you write `dt.tzinfo is timezone.utc` as a cheap identity check (no `__eq__` call) and lets the stdlib cache the value. The same singleton pattern shows up in `None`, `True`, `False`, and `NotImplemented` — values with one canonical instance.

### Lines 27–31: `now(tz=None)` naive vs `now(timezone.utc)` aware

```python
# 5. now(tz=None) — naive local; now(timezone.utc) — aware UTC
naive_now = datetime.now()                # ← don't do this in production
aware_utc = datetime.now(timezone.utc)    # ← do this instead
print("naive_now.tzinfo:", naive_now.tzinfo)            # None
print("aware_utc.tzinfo:", aware_utc.tzinfo)            # UTC
```

`datetime.now(tz=None)` is the constructor you must train yourself not to call. With `tz=None` (the default), it returns the *local* wall-clock time of the machine that runs it, with `tzinfo=None` — a naive `datetime`. The local timezone is read from the `TZ` environment variable or the operating-system timezone database; on a server without `TZ` set it defaults to UTC, but on a developer laptop in London it returns GMT/BST depending on the date. The value is ambiguous the moment it crosses a process boundary, because nothing in the value records which local time it was.

`datetime.now(timezone.utc)` is the call you should be making. With `tz=timezone.utc`, it returns the current UTC instant with `tzinfo=timezone.utc` set — an aware `datetime` that means the same thing on every machine on Earth. The value is unambiguous: it pins to UTC, it round-trips through ISO 8601, it stores cleanly in Postgres `timestamptz`, and it survives a migration from a London data centre to a Tokyo one with no value drift.

The comment `# ← don't do this in production` on the `naive_now` line is not stylistic preference. It is the line that prevents a class of bugs that surface months after deployment — the audit log that disagrees with itself, the SLA calculation that drifts by an hour, the `WHERE created_at > '2026-10-23'` query that returns different rows on the read replica than on the primary. Store aware UTC; render in the user's timezone at the edge. That is the rule.

**Why does `datetime.now()` default to `tz=None` (naive) instead of `tz=timezone.utc` (aware)?** Because the `datetime` module predates the `timezone` class — `timezone` was added in Python 3.2 (PEP 0 internally), and `datetime.now()` existed since Python 2.3 with the local-time default. Changing the default in 3.2 would have silently shifted every existing `datetime.now()` call from "local naive" to "UTC aware", which is a behaviour change that breaks every script that printed `datetime.now()` and expected to see wall-clock time. The stdlib authors chose backwards compatibility over correctness here; the cost is that every new Python programmer writes `datetime.now()` and ships the naive bug. The fix is discipline, not a default change.

### Lines 33–34: `utcnow()` is deprecated in 3.12

```python
# 6. utcnow() is deprecated in 3.12 — emits DeprecationWarning
# datetime.utcnow()  # ← do not call; use datetime.now(timezone.utc)
```

`datetime.utcnow()` is the *worst* form of the naive bug. It returns the current UTC time but sets `tzinfo=None` — so you get a value that *is* UTC but *looks* naive. Comparing it to an aware UTC `datetime` raises `TypeError`. Storing it next to an aware UTC `datetime` and then sorting the column gives nonsensical results. The deprecation landed in Python 3.12 (the warning is `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).`).

The line is commented out because the comment itself is the lesson — you do not run `datetime.utcnow()`; you delete it from your codebase. The migration is mechanical: `datetime.utcnow()` → `datetime.now(timezone.utc)`. If your codebase has more than a handful of `utcnow()` calls, write a one-line `sed` script and a CI check that rejects new occurrences. The deprecation is your friend; it tells you which calls to fix before they become a removal in some future Python version.

**Why was `utcnow()` deprecated instead of fixed?** Because fixing it would mean returning an aware `datetime`, which is a behaviour change. A caller that does `datetime.utcnow() + timedelta(hours=1)` and pastes the result into a `tzinfo=None` column gets one behaviour today (a naive UTC value, broken in the ways described above) and would get a different behaviour if the return type changed to aware. The stdlib cannot silently fix the bug without breaking callers that depend on the broken behaviour. The deprecation says: "we are not going to silently fix this; we are going to tell you it is broken, and you should fix it yourself with `datetime.now(timezone.utc)`".

### Lines 36–46: The `boardly` Ticket model

```python
# 7. The boardly Ticket model — created_at is aware UTC, always
@dataclass
class Ticket:
    id: int
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


t = Ticket(id=1, summary="login broken")
print("Ticket.created_at:", t.created_at)
print("Ticket.created_at.tzinfo:", t.created_at.tzinfo)
```

The `@dataclass` decorator generates `__init__`, `__repr__`, `__eq__`, and `__hash__` (where appropriate) from the three annotated fields. The `created_at: datetime` annotation tells `@dataclass` (and your type checker, and FastAPI in later sections) that this field holds a `datetime` instance. The `= field(default_factory=...)` is the mutable-default pattern — you cannot write `created_at: datetime = datetime.now(timezone.utc)` because that would call `datetime.now(timezone.utc)` *once* at class-definition time, and every `Ticket` instance would share the same `created_at` value (the time the class was defined, not the time the instance was created). The `default_factory` callable is invoked *per instance*, so each `Ticket` gets its own fresh `datetime.now(timezone.utc)` reading.

The lambda wraps the call because `default_factory` must be a zero-argument callable; `lambda: datetime.now(timezone.utc)` is the simplest such callable. (See [[06-dataclasses/02-field-and-Defaults]] for the full treatment of why `default_factory` is needed for any non-trivial default.)

The two `print` calls confirm the field is set: `t.created_at` is the current UTC instant (something like `2026-10-23 07:00:03.957962+00:00`); `t.created_at.tzinfo` is `timezone.utc` (printed as `UTC`). The `+00:00` suffix on the printed value is the visible marker of awareness — a naive `datetime` would print without it. Lesson 03 covers the format in detail.

**Why a lambda and not `default_factory=datetime.now`?** Because `datetime.now` takes a `tz` keyword argument; passing `datetime.now` directly as `default_factory` would call it with no `tz`, returning naive local time — exactly the bug we are trying to avoid. The lambda closes over `timezone.utc` and passes it explicitly: `lambda: datetime.now(timezone.utc)`. The lambda is one extra character of indirection that buys you the aware UTC guarantee on every call. Lint for `default_factory=datetime.now` in code review; it is the same bug in a different shape.

### Lines 48–54: The `Project.deadline` field — aware UTC by construction

```python
# 8. The deadline — Project with an aware UTC deadline
@dataclass
class Project:
    id: int
    name: str
    deadline: datetime                       # always aware; see lesson 04


p = Project(id=1, name="alpha", deadline=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
print("Project.deadline:", p.deadline)
print("Project.deadline.tzinfo:", p.deadline.tzinfo)
```

The `Project` model has a `deadline: datetime` field with no default — `Project(id=1, name="alpha")` would raise `TypeError: __init__() missing 1 required positional argument: 'deadline'`. The caller *must* supply a `datetime` at construction time, and the lesson's example supplies an aware UTC one: `datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)` — the last second of 2026 in UTC.

The `print` calls confirm the field is set with `tzinfo=timezone.utc` — `p.deadline.tzinfo` is `UTC`, the `+00:00` suffix appears in the repr, and the value is unambiguous. Lesson 04 walks the rule that *every* `deadline` value the application accepts must be aware; lesson 05 covers the parsing path that turns an ISO 8601 string from a webhook payload into an aware `datetime` at the boundary.

**Why doesn't `deadline` have a `default_factory` like `created_at`?** Because the deadline is *data* — it comes from the user (the project manager setting the due date) — not a *side-effect of construction* like the creation timestamp. Defaulting the deadline to "now" would silently make every project overdue the instant it was created. The contract is: the caller must supply a deadline; the type system enforces this by not providing a default. The two fields model the two directions a `datetime` field can come from — `created_at` is generated by the system (so it has a `default_factory`), `deadline` is supplied by the user (so it has no default and must be passed in).

## Execution Trace

The `Ticket.created_at` value is the runtime UTC instant and changes every time you run the script. The format and the `tzinfo` reading are what to check.

```bash
$ uv run python boardly/tickets/datetime_and_timezone.py
instant: 2026-10-23 12:00:00+00:00
tzinfo is None: False
tzname: UTC
utcoffset: 0:00:00
date: 2026-10-23
time: 12:00:00+00:00
timedelta: 1:00:00
tzinfo is subclass-of object (no ABC enforcement): True
timezone is a tzinfo subclass: True
utc.utcoffset(None): 0:00:00
ist.utcoffset(None): 5:30:00
naive_now.tzinfo: None
aware_utc.tzinfo: UTC
Ticket.created_at: 2026-10-23 07:04:21.358695+00:00
Ticket.created_at.tzinfo: UTC
Project.deadline: 2026-12-31 23:59:59+00:00
Project.deadline.tzinfo: UTC
```

## Common Mistakes

### Mistake 1: Calling `datetime.now()` and treating the result as UTC

```python
created_at = datetime.now()           # naive local — could be UTC, could be BST, could be JST
print(created_at.tzinfo)              # None
```

**Symptom:** The `created_at` value looks plausible but `tzinfo` is `None`. When the service moves data centres, every stored value silently shifts by the timezone delta between the old and new machine's local timezone. The audit log stops agreeing with itself.
**Why:** `datetime.now()` with no argument returns local wall-clock time with `tzinfo=None`. The local timezone is read from the OS; on a server without `TZ` set it defaults to UTC, but the value has no marker recording that fact. The next machine to read the value has to *assume*, and assumptions about timezones are how production incidents start.
**Fix:** Always call `datetime.now(timezone.utc)`. The result has `tzinfo=timezone.utc` set, the `+00:00` suffix appears in its ISO 8601 form, and the value is unambiguous. Lint for bare `datetime.now()` calls in code review; reject them in CI.

### Mistake 2: Calling `datetime.utcnow()` (deprecated in 3.12)

```python
created_at = datetime.utcnow()        # returns a naive UTC value — the worst form
```

**Symptom:** On Python 3.12+ the interpreter emits `DeprecationWarning: datetime.datetime.utcnow() is deprecated...`. Worse, the return value has `tzinfo=None` — it *is* UTC but *looks* naive, so comparing it to an aware UTC `datetime` raises `TypeError`.
**Why:** `utcnow()` predates the `timezone` class and was not updated when aware datetimes became first-class. The stdlib cannot silently change the return type without breaking callers that depend on the broken behaviour; the deprecation is the loud signal to fix it before the eventual removal.
**Fix:** Replace every `datetime.utcnow()` call with `datetime.now(timezone.utc)`. The migration is mechanical and can be scripted with `sed`. Add a CI check that rejects `utcnow()` so the bug does not reappear.

### Mistake 3: Constructing a `datetime` with `tzinfo=None` and storing it

```python
deadline = datetime(2026, 12, 31, 23, 59, 59)     # tzinfo defaults to None — naive
p = Project(id=1, name="alpha", deadline=deadline)
```

**Symptom:** The `deadline` value passes the dataclass type check (`isinstance(deadline, datetime)` is `True`) but is naive — `deadline.tzinfo is None`. Lesson 04 walks the bug this causes when you compare it to an aware `datetime`.
**Why:** The `datetime` constructor defaults `tzinfo` to `None` for backwards compatibility with pre-3.2 code. The type system does not distinguish naive from aware at the annotation level — both are `datetime`. The discipline must come from the call site, not the type.
**Fix:** Pass `tzinfo=timezone.utc` explicitly: `datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)`. Or parse from ISO 8601 with `fromisoformat` (lesson 05), which preserves the offset if one is present in the input.

### Mistake 4: Using `timezone(timedelta(hours=5, minutes=30))` for a DST-observing zone

```python
ny_naive = timezone(timedelta(hours=-5))           # wrong — NY observes DST, the offset changes
```

**Symptom:** A `datetime` stamped with this `tzinfo` has the wrong offset for half the year (when DST is in effect, NY is `-04:00`, not `-05:00`). The value drifts by one hour for any date in the DST window.
**Why:** The `timezone` class represents a *fixed* offset — a constant `+HH:MM` that does not change. DST-observing zones change their offset twice a year; the `timezone` class cannot represent that.
**Fix:** Use `zoneinfo.ZoneInfo("America/New_York")` (Python 3.9+, PEP 615) for any DST-observing zone. Lesson 05 walks `ZoneInfo` and the `astimezone()` conversion. The `timezone` class is for fixed-offset zones only (UTC, IST, and other no-DST zones).

## Engineering Trade-Offs

**Decision:** Store every `datetime` field as aware UTC (`tzinfo=timezone.utc`). Never store naive. Render in the user's timezone at the edge (the API response, the HTML template) using `astimezone(ZoneInfo(...))`.
**Both sides:** The alternative is to store naive local time — which is what `datetime.now()` returns and what older codebases do. Naive local is *simpler to display* (the wall-clock value the user sees is the value the database stores) but it is *ambiguous the moment it crosses a process boundary* — the value's meaning depends on the machine's local timezone, which is not recorded in the value. Aware UTC is *unambiguous* (the same instant on every machine, in every timezone) but it requires a conversion step at the display boundary. The trade-off is "simple display, ambiguous storage" vs "explicit conversion, unambiguous storage". For a backend service that runs in one data centre today and another tomorrow, ambiguous storage is a production bug waiting to happen.
**Commitment:** `boardly` stores every `created_at`, `updated_at`, and `deadline` as aware UTC. The `Ticket.created_at` field uses `default_factory=lambda: datetime.now(timezone.utc)`. The `Project.deadline` field requires an aware `datetime` at construction (no default). The API response layer calls `dt.astimezone(ZoneInfo(user.timezone))` at the edge to render in the user's local zone; the storage layer never converts. This is the rule the rest of the section depends on.

## Exercises

1. **Exercise 1 — Change the default factory.** Edit the `Ticket` dataclass to use `default_factory=datetime.now` (no lambda, no `tz` argument). Re-run the script. Confirm `t.created_at.tzinfo` is `None` (naive local) and the `+00:00` suffix is gone from the printed value. `Verify: uv run python boardly/tickets/datetime_and_timezone.py | rg 'Ticket.created_at:'`
2. **Exercise 2 — Construct a fixed-offset IST datetime.** Add a line `ist_dt = datetime(2026, 10, 23, 17, 30, 0, tzinfo=ist)` after the `ist` definition. Print it and confirm the suffix is `+05:30`. `Verify: uv run python boardly/tickets/datetime_and_timezone.py | rg '17:30'`
3. **Exercise 3 — Verify `datetime.UTC` is the same object as `timezone.utc`.** Run `import datetime; print(datetime.UTC is datetime.timezone.utc)` — confirm it prints `True`. Note that `datetime.UTC` is a module-level alias added in Python 3.11; you must `import datetime` (the module form) to access it. If you write `from datetime import datetime, timezone; print(datetime.UTC is timezone.utc)` you get `AttributeError: type object 'datetime.datetime' has no attribute 'UTC'` because the name `datetime` in your namespace is bound to the class, not the module. `Verify: uv run python -c "import datetime; print(datetime.UTC is datetime.timezone.utc)"`
4. **Exercise 4 — Trigger the `utcnow()` DeprecationWarning.** Uncomment the `datetime.utcnow()` line, run the script with `python -W always`, and confirm the warning is emitted. Then re-comment the line. `Verify: uv run python -W always boardly/tickets/datetime_and_timezone.py 2>&1 | rg 'utcnow'`
5. **Exercise 5 — Subclass `tzinfo` yourself.** Write a `MyTZ(tzinfo)` subclass that implements `utcoffset(self, dt)` to return `timedelta(hours=3)`, `tzname(self, dt)` to return `"MYTZ"`, and `dst(self, dt)` to return `timedelta(0)`. Construct a `datetime(2026, 10, 23, 12, 0, 0, tzinfo=MyTZ())` and confirm the suffix is `+03:00` and `tzname()` returns `"MYTZ"`. `Verify: uv run python -c "from datetime import datetime, timedelta, tzinfo; exec('class MyTZ(tzinfo):\n  def utcoffset(self,dt): return timedelta(hours=3)\n  def tzname(self,dt): return 'MYTZ'\n  def dst(self,dt): return timedelta(0)'); d=datetime(2026,10,23,12,0,0,tzinfo=MyTZ()); print(d, d.tzname())"`

## Verification

The `Ticket.created_at` value is the runtime UTC instant; everything else is deterministic. Check that the `+00:00` suffix appears on every aware value and that `tzinfo` reads as `UTC`.

```bash
$ uv run python boardly/tickets/datetime_and_timezone.py
instant: 2026-10-23 12:00:00+00:00
tzinfo is None: False
tzname: UTC
utcoffset: 0:00:00
date: 2026-10-23
time: 12:00:00+00:00
timedelta: 1:00:00
tzinfo is subclass-of object (no ABC enforcement): True
timezone is a tzinfo subclass: True
utc.utcoffset(None): 0:00:00
ist.utcoffset(None): 5:30:00
naive_now.tzinfo: None
aware_utc.tzinfo: UTC
Ticket.created_at: 2026-10-23 07:04:21.358695+00:00
Ticket.created_at.tzinfo: UTC
Project.deadline: 2026-12-31 23:59:59+00:00
Project.deadline.tzinfo: UTC
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — the annotation syntax `created_at: datetime` that this lesson writes on the `Ticket` dataclass field.
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` decorator that generates `__init__`/`__repr__`/`__eq__` for the `Ticket` and `Project` models this lesson uses as its running example.
- [[06-dataclasses/02-field-and-Defaults]] — the `field(default_factory=...)` pattern that the `created_at` field uses to call `datetime.now(timezone.utc)` per-instance instead of per-class.

## What's Next

[[15-datetime/02-timedelta]] — Now that you can construct an aware UTC `datetime`, you need the *arithmetic* layer: durations between two instants, deadlines plus offsets, SLA windows. Lesson 02 walks `datetime.timedelta` — the constructor that takes `weeks`, `days`, `hours`, `minutes`, `seconds`, `milliseconds`, `microseconds` and normalises them into `days`/`seconds`/`microseconds` internally; the `dt + timedelta(hours=1)` arithmetic; the `dt1 - dt2` subtraction that returns a `timedelta`; the `.total_seconds()` method; and the `timedelta // timedelta` floor-division that lets you count "how many hours apart are these two events".

- **Lesson 02** — `timedelta` arithmetic, normalisation, `total_seconds()`, floor-division.
- **Lesson 03** — `isoformat()` and the ISO 8601 serialisation contract.
- **Lesson 04** — aware vs naive, the `TypeError` comparison, and the production rule.

## Sources

- **Python `datetime` module documentation** — https://docs.python.org/3/library/datetime.html — accessed 2026-10-23 — the canonical CPython reference for `datetime`, `date`, `time`, `timedelta`, `tzinfo`, `timezone`, `timezone.utc`, the `now(tz=...)` constructor, and the `utcnow()` deprecation.
- **`zoneinfo` — IANA time zone support** — https://docs.python.org/3/library/zoneinfo.html — accessed 2026-10-23 — the `ZoneInfo` class (Python 3.9+, PEP 615) for IANA timezone names; lesson 05 walks it in detail.
- **PEP 495 — Local Time Disambiguation** — https://peps.python.org/pep-0495/ — accessed 2026-10-23 — the `fold` attribute (Python 3.6+) that disambiguates the two readings of a wall-clock time during a DST fall-back transition.
- **PEP 615 — The `zoneinfo` module** — https://peps.python.org/pep-0615/ — accessed 2026-10-23 — the standard-library `zoneinfo` module backed by the IANA timezone database.

## What We Learned

- You can now construct an aware UTC `datetime` with `datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)` and explain what every constructor argument means — including the keyword-only `fold`.
- You can distinguish `date` (calendar date), `time` (time-of-day), `datetime` (an instant), and `timedelta` (a duration) and name which one you reach for at which boundary.
- You can explain that `tzinfo` is the abstract base class (instantiable but its methods raise `NotImplementedError`) and `timezone` is the concrete fixed-offset subclass; `timezone.utc` is the UTC singleton.
- You can call `datetime.now(timezone.utc)` for aware UTC and refuse to call `datetime.now()` (naive local) or `datetime.utcnow()` (deprecated in 3.12, naive-UTC-flavoured).
- You can state the cardinal rule the rest of the section depends on: store aware UTC, render in the user's timezone at the edge, and never let a naive `datetime` past the parse boundary.
