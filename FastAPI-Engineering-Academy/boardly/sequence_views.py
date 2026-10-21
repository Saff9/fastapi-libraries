# boardly/sequence_views.py
"""Custom Sequence, Mapping, and Set subclasses to demo ABC mixins."""
from collections.abc import Sequence, Mapping, Set
from typing import Iterator
from boardly.models import Ticket


class TicketList(Sequence):
    """A read-only sequence view over a list of tickets.

    Sequence requires __getitem__ and __len__. It provides __contains__,
    __iter__, __reversed__, index, and count as mixins.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __getitem__(self, index):
        return self._tickets[index]

    def __len__(self):
        return len(self._tickets)

    def __repr__(self):
        return f"TicketList({self._tickets!r})"


class FrozenConfig(Mapping):
    """A read-only mapping view over a config dict.

    Mapping requires __getitem__, __iter__, __len__. It provides __contains__,
    keys, values, items, get, __eq__, __ne__ as mixins.
    """

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class RoleSet(Set):
    """A read-only set view over a list of role strings.

    Set requires __contains__ and __iter__ and __len__. It provides the set
    operators __le__, __lt__, __gt__, __ge__, __and__, __or__, __sub__, __xor__,
    and isdisjoint as mixins.
    """

    def __init__(self, roles: list[str]) -> None:
        # Materialise into a real set for O(1) lookup; the view is read-only.
        self._roles = set(roles)

    def __contains__(self, role: object) -> bool:
        return role in self._roles

    def __iter__(self) -> Iterator[str]:
        return iter(self._roles)

    def __len__(self) -> int:
        return len(self._roles)


if __name__ == "__main__":
    from uuid import uuid4

    print("--- TicketList: Sequence mixins ---")
    ts = TicketList([
        Ticket(uuid4(), uuid4(), "t1", None, "open", 1),
        Ticket(uuid4(), uuid4(), "t2", None, "open", 2),
        Ticket(uuid4(), uuid4(), "t3", None, "done", 3),
    ])

    print(f"len: {len(ts)}")
    print(f"ts[0].title: {ts[0].title}")
    print(f"ts[-1].title: {ts[-1].title}")   # negative index works
    t0 = ts[0]
    print(f"t0 in ts: {t0 in ts}")             # __contains__ mixin
    print(f"[t.title for t in ts]: {[t.title for t in ts]}")   # __iter__ mixin
    print(f"[t.title for t in reversed(ts)]: {[t.title for t in reversed(ts)]}")  # __reversed__ mixin
    print(f"ts.index(t0): {ts.index(t0)}")     # index mixin
    print(f"ts.count(t0): {ts.count(t0)}")     # count mixin

    print("\n--- FrozenConfig: Mapping mixins ---")
    cfg = FrozenConfig({"db_url": "x", "log_level": "INFO", "max_tickets": 1000})
    print(f"len: {len(cfg)}")
    print(f"cfg['db_url']: {cfg['db_url']}")
    print(f"'db_url' in cfg: {'db_url' in cfg}")            # __contains__ mixin
    print(f"keys: {list(cfg.keys())}")                     # keys mixin
    print(f"values: {list(cfg.values())}")                 # values mixin
    print(f"items: {list(cfg.items())}")                   # items mixin
    print(f"cfg.get('missing', 'default'): {cfg.get('missing', 'default')}")  # get mixin
    print(f"cfg == FrozenConfig(cfg._data): {cfg == FrozenConfig(cfg._data)}")  # __eq__ mixin

    print("\n--- RoleSet: Set mixins ---")
    rs = RoleSet(["admin", "editor", "viewer"])
    rs2 = RoleSet(["admin", "viewer"])
    print(f"'admin' in rs: {'admin' in rs}")
    print(f"rs <= rs2: {rs <= rs2}")           # subset
    print(f"rs2 <= rs: {rs2 <= rs}")
    print(f"rs - rs2: {set(rs - rs2)}")        # set difference
    print(f"rs & rs2: {set(rs & rs2)}")        # intersection
    print(f"rs | RoleSet(['x']): {set(rs | RoleSet(['x']))}")  # union
    print(f"rs ^ rs2: {set(rs ^ rs2)}")        # symmetric difference
    print(f"rs.isdisjoint(RoleSet(['z'])): {rs.isdisjoint(RoleSet(['z']))}")
