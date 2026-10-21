# boardly/audit.py
"""In-memory audit-log ring buffer with collections.deque."""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID


@dataclass
class AuditEvent:
    actor_id: UUID
    action: str
    target_id: UUID
    at: datetime


class AuditLog:
    """A fixed-size ring buffer of audit events."""

    def __init__(self, capacity: int = 1000) -> None:
        # maxlen turns this deque into a ring buffer: when full, append drops
        # the oldest entry from the opposite end automatically.
        self._events: deque[AuditEvent] = deque(maxlen=capacity)

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)   # O(1); drops oldest if at maxlen

    def recent(self, n: int = 50) -> list[AuditEvent]:
        # list() walks the deque; O(n) but only on read paths
        return list(self._events)[-n:]

    def rotate(self, n: int) -> None:
        # Rotate the buffer in place; O(k) where k = min(|n|, len)
        self._events.rotate(n)

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self):
        return iter(self._events)


def partition_by_priority(
    events: list[AuditEvent], threshold: int
) -> tuple[deque[AuditEvent], deque[AuditEvent]]:
    """Walk events left-to-right; high-priority go to the LEFT deque head."""
    high, low = deque(), deque()
    for e in events:
        # extendleft pushes onto the head, so we get reverse order unless we reverse first
        high.appendleft(e) if e.action.startswith("urgent") else low.append(e)
    return high, low


if __name__ == "__main__":
    from uuid import uuid4

    log = AuditLog(capacity=3)
    for i in range(5):
        log.record(AuditEvent(uuid4(), f"action_{i}", uuid4(), datetime.now(UTC)))
    print(f"capacity 3, recorded 5 -> len={len(log)}")
    print("recent 3:", [e.action for e in log.recent(3)])

    print("\n--- rotate demo ---")
    d = deque([1, 2, 3, 4, 5])
    print("before:", list(d))
    d.rotate(2)
    print("rotate(2):", list(d))
    d.rotate(-1)
    print("rotate(-1):", list(d))

    print("\n--- extendleft demo ---")
    d2 = deque([1, 2, 3])
    d2.extendleft([4, 5, 6])   # note the reversed result
    print("extendleft([4,5,6]) ->", list(d2))
