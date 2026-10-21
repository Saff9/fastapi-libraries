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