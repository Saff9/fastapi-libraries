# boardly/metrics.py
"""Ticket-status counting with collections.Counter."""
from collections import Counter
from boardly.models import Ticket


def status_counts(tickets: list[Ticket]) -> Counter:
    """Return a Counter of status -> ticket count."""
    return Counter(t.status for t in tickets)


def top_n_statuses(tickets: list[Ticket], n: int = 3) -> list[tuple[str, int]]:
    """Return the top-n statuses by ticket count, descending."""
    return status_counts(tickets).most_common(n)


def merge_sprint_counts(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Combine two sprints' tickets; overlapping statuses add."""
    return Counter(t.status for t in sprint_a) + Counter(t.status for t in sprint_b)


def shared_statuses(sprint_a: list[Ticket], sprint_b: list[Ticket]) -> Counter:
    """Statuses present in BOTH sprints, min count."""
    return Counter(t.status for t in sprint_a) & Counter(t.status for t in sprint_b)


def expand_to_repeated_statuses(tickets: list[Ticket]) -> list[str]:
    """Yield each status once per ticket with that status."""
    c = status_counts(tickets)
    return list(c.elements())


if __name__ == "__main__":
    from boardly.models import Ticket
    from uuid import uuid4

    proj = uuid4()
    sample = [
        Ticket(uuid4(), proj, "write docs",   None,    "todo",        2),
        Ticket(uuid4(), proj, "fix login",    uuid4(), "in_progress", 4),
        Ticket(uuid4(), proj, "ship release", uuid4(), "in_progress", 5),
        Ticket(uuid4(), proj, "triage",       None,    "todo",        1),
        Ticket(uuid4(), proj, "done item",    uuid4(), "done",        2),
    ]
    print("counts:", status_counts(sample))
    print("top 2:", top_n_statuses(sample, 2))
    print("elements:", expand_to_repeated_statuses(sample))
