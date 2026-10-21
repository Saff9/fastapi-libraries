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