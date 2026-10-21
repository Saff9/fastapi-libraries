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