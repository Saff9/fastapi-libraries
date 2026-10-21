# boardly/geometry.py
"""Tiny record types for board layout using namedtuple and typing.NamedTuple."""
from collections import namedtuple
from typing import NamedTuple
from uuid import UUID
from datetime import datetime


# --- collections.namedtuple: the original factory ---

# namedtuple returns a class. The class subclasses tuple. Fields are class-level
# descriptors (property-like objects) that map to tuple slots.
Point = namedtuple("Point", ["x", "y"])
Point.__doc__ = "A 2-D point on the board layout."

# Default values are positional and only allowed on the rightmost fields.
Region = namedtuple("Region", ["x", "y", "w", "h"], defaults=[0, 0])
Region.__doc__ = "A rectangle on the board. w and h default to 0."


# --- typing.NamedTuple: the typed alternative (3.6.1+), same instance shape ---

class TicketSummary(NamedTuple):
    """A summary view of a ticket — for list endpoints, not detail."""
    id: UUID
    title: str
    status: str
    priority: int
    assignee_id: UUID | None = None   # default values work the same way


# --- The underscore-prefixed helpers, demoed in __main__ ---

if __name__ == "__main__":
    # Construct from positional or keyword
    p = Point(3.0, 4.0)
    print(f"Point: {p}, x={p.x}, y={p.y}")

    # _fields is a tuple of field names — the public schema
    print(f"_fields: {Point._fields}")

    # _asdict() returns a plain dict (3.8+ returns a real dict, not OrderedDict)
    print(f"_asdict: {p._asdict()}")

    # _replace returns a new instance with the named fields replaced
    p2 = p._replace(x=10.0)
    print(f"_replace(x=10.0): {p2}; original unchanged: {p}")

    # _make is the alternative constructor for an existing iterable
    coords = (5.0, 6.0)
    p3 = Point._make(coords)
    print(f"_make((5.0, 6.0)): {p3}")

    # Default values on Region
    r = Region(1.0, 2.0)
    print(f"Region(1.0, 2.0) -> {r}")

    # typing.NamedTuple usage — same instance shape, typed fields
    from uuid import uuid4
    ts = TicketSummary(uuid4(), "Write docs", "todo", 2)
    print(f"TicketSummary: {ts}")
    ts2 = TicketSummary(uuid4(), "Fix bug", "in_progress", 4, uuid4())
    print(f"With assignee: {ts2.assignee_id is not None}")
    print(f"  _fields: {TicketSummary._fields}")
    print(f"  _asdict keys: {list(ts2._asdict().keys())}")
