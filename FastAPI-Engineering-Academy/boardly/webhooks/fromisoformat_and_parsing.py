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