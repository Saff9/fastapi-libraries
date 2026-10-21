# boardly/iteration.py
"""The Iterable/Iterator protocol: __iter__, __next__, StopIteration, and the
'exhausted iterator' gotcha."""
from collections.abc import Iterable, Iterator
from typing import Any
from boardly.models import Ticket


class TicketBatch(Iterable[Ticket]):
    """A custom Iterable: returns a fresh Iterator each time __iter__ is called.

    Iterable requires __iter__. The contract: __iter__ MUST return a fresh
    Iterator each call. Reusing the same Iterator across calls is the
    'exhausted after first loop' bug.
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets

    def __iter__(self) -> Iterator[Ticket]:
        # Each call to __iter__ must return a fresh Iterator.
        return iter(self._tickets)


class ReverseTicketIterator(Iterator[Ticket]):
    """A custom Iterator: walks the tickets in reverse.

    Iterator requires __next__ AND __iter__ (which returns self).
    The contract: __next__ either returns the next value or raises
    StopIteration. Once StopIteration has been raised, every subsequent
    __next__ MUST also raise StopIteration (the 'exhausted' state).
    """

    def __init__(self, tickets: list[Ticket]) -> None:
        self._tickets = tickets
        self._index = len(tickets)   # start past the end; decrement before yield

    def __iter__(self) -> Iterator[Ticket]:
        # Iterator's __iter__ returns self — that is what makes an Iterator
        # iterable (and what makes the 'for x in iterator' loop work).
        return self

    def __next__(self) -> Ticket:
        if self._index <= 0:
            # The exhausted state: raise StopIteration forever.
            raise StopIteration
        self._index -= 1
        return self._tickets[self._index]


class Range10:
    """A minimal Iterable demonstrating the protocol in 15 lines."""

    def __iter__(self):
        # A generator function: calling it returns a fresh generator.
        for i in range(10):
            yield i


if __name__ == "__main__":
    from uuid import uuid4

    print("--- iter() builtin: for x in obj -> iter(obj) -> next() loop ---")
    r = Range10()
    total = 0
    for x in r:                # for calls iter(r) -> generator; then next() until StopIteration
        total += x
    print(f"sum of 0..9: {total}")
    # for x in r: print(x)    # Range10's __iter__ returns a fresh generator — repeatable

    print("\n--- TicketBatch: Iterable that returns a fresh iterator each call ---")
    ts = [Ticket(uuid4(), uuid4(), f"t{i}", None, "open", i) for i in range(3)]
    batch = TicketBatch(ts)
    print(f"first iteration: {[t.title for t in batch]}")
    print(f"second iteration: {[t.title for t in batch]}   (works: fresh iterator)")

    print("\n--- ReverseTicketIterator: a custom Iterator ---")
    rti = ReverseTicketIterator(ts)
    print(f"isinstance(rti, Iterator): {isinstance(rti, Iterator)}")
    print(f"isinstance(rti, Iterable): {isinstance(rti, Iterable)}")
    print(f"first loop: {[t.title for t in rti]}")
    print(f"second loop: {[t.title for t in rti]}   (BUG: zero items — iterator exhausted)")

    print("\n--- the iter() + next() protocol, inlined ---")
    gen = (i for i in range(3))
    it = iter(gen)        # iter() returns the iterator (gen already is one)
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    print(f"next(it): {next(it)}")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration (iterator exhausted)")
    try:
        next(it)
    except StopIteration:
        print("next(it): StopIteration again (once exhausted, always exhausted)")
