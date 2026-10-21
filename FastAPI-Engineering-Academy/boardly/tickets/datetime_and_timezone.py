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