# boardly/grouping.py
"""Group tickets by various keys using collections.defaultdict."""
from collections import defaultdict
from uuid import UUID
from boardly.models import Ticket


def group_by_assignee(tickets: list[Ticket]) -> defaultdict[UUID, list[Ticket]]:
    """Map assignee_id -> list of tickets assigned to that user."""
    groups: defaultdict[UUID, list[Ticket]] = defaultdict(list)
    for t in tickets:
        if t.assignee_id is not None:
            groups[t.assignee_id].append(t)
    return groups


def unique_statuses_per_project(tickets: list[Ticket]) -> defaultdict[UUID, set[str]]:
    """Map project_id -> set of statuses seen on that project's tickets."""
    groups: defaultdict[UUID, set[str]] = defaultdict(set)
    for t in tickets:
        groups[t.project_id].add(t.status)
    return groups


def count_tickets_per_project(tickets: list[Ticket]) -> defaultdict[UUID, int]:
    """Map project_id -> number of tickets. Same shape as Counter, mutable."""
    groups: defaultdict[UUID, int] = defaultdict(int)
    for t in tickets:
        groups[t.project_id] += 1
    return groups


def first_ticket_per_status(tickets: list[Ticket]) -> defaultdict[str, Ticket | None]:
    """Map status -> first ticket seen with that status (or None if none yet).

    Uses a custom factory: a closure over a mutable cell.
    """
    seen: dict[str, bool] = {}

    def _first_or_none() -> Ticket | None:
        return None  # placeholder; the loop overwrites immediately

    groups: defaultdict[str, Ticket | None] = defaultdict(_first_or_none)
    for t in tickets:
        groups[t.status] = t   # always overwrites; the factory only fires on first read of a NEW key
    return groups


if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    p1, p2 = uuid4(), uuid4()
    u1, u2 = uuid4(), uuid4()
    sample = [
        Ticket(uuid4(), p1, "t1", u1, "todo", 2),
        Ticket(uuid4(), p1, "t2", u2, "in_progress", 3),
        Ticket(uuid4(), p2, "t3", u1, "todo", 4),
        Ticket(uuid4(), p2, "t4", u1, "done", 1),
    ]
    by_assignee = group_by_assignee(sample)
    print("by_assignee:", {k: len(v) for k, v in by_assignee.items()})
    print("statuses per project:", {str(k): sorted(v) for k, v in unique_statuses_per_project(sample).items()})
    print("counts per project:", dict(count_tickets_per_project(sample)))
