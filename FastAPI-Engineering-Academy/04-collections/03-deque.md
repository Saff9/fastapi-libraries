---
title: "Lesson 03: deque"
aliases:
 - collections.deque
 - deque
 - double-ended queue
tags:
 - collections
 - deque
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[04-collections/02-defaultdict]]"
related_lessons:
 - "[[04-collections/04-namedtuple]]"
 - "[[05-collections-abc/02-Sequence-Mapping-Set]]"
first_taught_in: "04-collections/03-deque"
---

# Lesson 03: deque

*`collections.deque` — the double-ended queue that gives you O(1) `appendleft`/`popleft`, an optional `maxlen` that turns it into a fixed-size ring buffer, and a `rotate(n)` that is the cheapest "shift everything by N" in the standard library. FastAPI itself uses `deque` for its middleware stack.*

**You're at the very beginning of Section 04 — Lesson 03.**

`deque` is the class that proves "lists are great but they are not the only sequence". `list.append` and `list.pop` are O(1); `list.pop(0)` and `list.insert(0, x)` are O(n). When the bottleneck is "things coming in at one end and out at the other", `deque` is the answer. This lesson walks the API, the `maxlen` ring buffer, and the one operation you should never use.

Take your time. Type every example. **This is how you learn.**

#collections #deque #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `deque`** with and without `maxlen`, and explain what `maxlen` does internally.
2. **Use `appendleft`/`popleft`/`extendleft`/`rotate`** and predict the result without running the code.
3. **Avoid `deque.insert` and `deque[index] = x`** in performance-sensitive code, and explain why they are O(n).
4. **Choose between `deque` and `list`** for a given append/pop pattern, and name the one case where `list` wins.

## Prerequisites

Before starting, you need:

- **[[04-collections/02-defaultdict]]** — comfort with the `collections` module's general shape and the way it ships small focused classes.
- **About 30 minutes of focused time.**

**The most common gap: assuming `deque` is just a faster `list`.**

It is not. `deque` is a doubly-linked-list-of-blocks under the hood; `list` is a contiguous array of pointers. That gives `deque` O(1) at *both* ends but O(n) random access in the middle. A surprising amount of code "just works" when you swap `list` for `deque` — until someone calls `q[100_000]` and your endpoint slows by a factor of 50.

## The Problem

Here is the bug. `boardly` keeps an in-memory audit log of the last 1,000 events so the dashboard can show "what just happened" without hitting the database. The first implementation everyone writes:

```python
audit_log: list[AuditEvent] = []

def record(event: AuditEvent) -> None:
    audit_log.append(event)
    if len(audit_log) > 1000:
        audit_log.pop(0)   # O(n) — shifts 999 elements left
```

This is correct. It is also O(n) per call: `list.pop(0)` shifts every remaining element down by one index. For 1,000 events at 1,000 events/second that is a million element-shifts per second of pure waste.

The fix is one character: replace `list` with `deque` and `pop(0)` with `popleft()`.

```python
from collections import deque

audit_log: deque[AuditEvent] = deque(maxlen=1000)

def record(event: AuditEvent) -> None:
    audit_log.append(event)   # automatically drops the oldest when len > maxlen
```

Two lines. No `if`. The `maxlen` argument turns the `deque` into a ring buffer that drops from the *opposite* end when full — exactly the behaviour we want, with zero conditional code.

## The Code

```python
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
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports and the `AuditEvent` dataclass

```python
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
```

`from collections import deque` — lowercase class name, same convention as `defaultdict`. The import is the standard one; you do not need a `deque` from anywhere else.

`AuditEvent` is a `@dataclass` with four fields. We will cover `dataclass` in detail in Section 06; for now, read it as "a record type with auto-generated `__init__`, `__repr__`, and `__eq__`". It is the right shape for audit events because they are immutable data carriers.

### Lines 18–28: `deque(maxlen=capacity)` — the ring buffer

```python
class AuditLog:
    """A fixed-size ring buffer of audit events."""

    def __init__(self, capacity: int = 1000) -> None:
        # maxlen turns this deque into a ring buffer: when full, append drops
        # the oldest entry from the opposite end automatically.
        self._events: deque[AuditEvent] = deque(maxlen=capacity)

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)   # O(1); drops oldest if at maxlen
```

`deque(maxlen=capacity)` — the `maxlen` argument is the entire reason this class exists for the audit-log use case. When `len(self._events) == maxlen` and you `append`, the `deque` first pops from the *opposite* end (the left), then appends to the right. The pop-and-append is one atomic step from the caller's perspective; there is no moment where `len > maxlen`.

Internally, `deque` is implemented as a doubly-linked list of fixed-size "blocks" (each block is an array of 64 pointers, give or take). `append` and `popleft` are O(1) — they update a pointer in the head or tail block. When the deque is at `maxlen`, `append` performs a `popleft` then the `append` in one operation. There is no GIL contention beyond the obvious "Python-level operation" — this is the "GIL-free ring buffer" the marketing copy refers to: the rotation happens entirely in C with no Python-level intermediate state.

`self._events.append(event)` — `append` is the right-end operation. The oldest entry is at the left; when full, the next `append` drops the leftmost. Exactly what an audit log wants.

### Lines 30–32: `recent(n)` — read paths are O(n) and that is fine

```python
    def recent(self, n: int = 50) -> list[AuditEvent]:
        # list() walks the deque; O(n) but only on read paths
        return list(self._events)[-n:]
```

`list(self._events)` walks the deque left-to-right, copying every element into a fresh list. That is O(n) — n pointer copies. The `[-n:]` slice at the end is O(n) again. Both are cheap because they happen on read paths, not on the hot write path.

**Why copy at all?** Because we want a stable snapshot. If we returned `self._events` directly and the caller iterated it while another thread was appending, the iteration would race. Copying into a list gives the caller a frozen view.

### Lines 34–36: `rotate(n)` — the cheapest "shift everything" in the stdlib

```python
    def rotate(self, n: int) -> None:
        # Rotate the buffer in place; O(k) where k = min(|n|, len)
        self._events.rotate(n)
```

`deque.rotate(n)` shifts elements circularly. `rotate(1)` moves the rightmost element to the leftmost slot (so `[1,2,3,4,5]` becomes `[5,1,2,3,4]`). `rotate(-1)` moves the leftmost to the rightmost (`[2,3,4,5,1]`). `rotate(n)` is O(min(|n|, len)) — it does not shift every element; it walks a `min(|n|, len)` slice around the ring.

**Why is `rotate` useful?** Two real cases:

1. **Round-robin scheduling.** A pool of workers; you want to "advance to the next worker without losing the queue order". `rotate(-1)` puts the head at the back; the new head is the next worker.
2. **Implementing `popleft`-then-pushback.** If you want "process and requeue", you can `popleft` and `append`, or you can `rotate(-1)` and `pop()` — same effect, one operation cheaper.

### Lines 42–50: `extendleft` reverses the input — the gotcha

```python
def partition_by_priority(
    events: list[AuditEvent], threshold: int
) -> tuple[deque[AuditEvent], deque[AuditEvent]]:
    """Walk events left-to-right; high-priority go to the LEFT deque head."""
    high, low = deque(), deque()
    for e in events:
        # extendleft pushes onto the head, so we get reverse order unless we reverse first
        high.appendleft(e) if e.action.startswith("urgent") else low.append(e)
    return high, low
```

`high.appendleft(e)` — O(1) prepend. This is the case where `deque` beats `list`: `list.insert(0, x)` is O(n) because it shifts every existing element down; `deque.appendleft(x)` is O(1).

`extendleft` deserves a `Danger` callout — see below.

### Lines 53–67: The `__main__` smoke test

```python
if __name__ == "__main__":
    from uuid import uuid4

    log = AuditLog(capacity=3)
    for i in range(5):
        log.record(AuditEvent(uuid4(), f"action_{i}", uuid4(), datetime.now(UTC)))
    print(f"capacity 3, recorded 5 -> len={len(log)}")
    print("recent 3:", [e.action for e in log.recent(3)])
```

The smoke test records 5 events into a 3-slot buffer and prints the result. Because of `maxlen=3`, the buffer keeps `action_2`, `action_3`, `action_4` — the last three in. That is the ring-buffer behaviour.

## Execution Trace

```bash
$ uv run python boardly/audit.py
capacity 3, recorded 5 -> len=3
recent 3: ['action_2', 'action_3', 'action_4']

--- rotate demo ---
before: [1, 2, 3, 4, 5]
rotate(2): [4, 5, 1, 2, 3]
rotate(-1): [5, 1, 2, 3, 4]

--- extendleft demo ---
extendleft([4,5,6]) -> [6, 5, 4, 1, 2, 3]
```

Read the `extendleft` line twice: `extendleft([4, 5, 6])` produced `[6, 5, 4, 1, 2, 3]`, not `[4, 5, 6, 1, 2, 3]`. That is because `extendleft` pushes *one at a time* onto the head: 4 goes to the head, then 5 goes to the head (pushing 4 right), then 6 goes to the head. The result is the input reversed.

## Common Mistakes

### Mistake 1: `extendleft` reverses the input — the canonical gotcha

```python
d = deque([1, 2, 3])
d.extendleft([4, 5, 6])
# student expects [4, 5, 6, 1, 2, 3]
```

**Symptom:** `d` is `[6, 5, 4, 1, 2, 3]`. The input list appears reversed.

**Why:** `extendleft` is defined as `for x in iterable: self.appendleft(x)`. Each `appendleft` puts the new item at position 0, pushing the previous item to position 1. Walking the input left-to-right means the *last* item pushed ends up at the head. The result is the input reversed.

**Fix:** If you want the input order preserved, reverse the input first: `d.extendleft(reversed([4, 5, 6]))`. Or use `d.extend([4, 5, 6])` and then `d.rotate(3)` — equivalent and reads more clearly.

### Mistake 2: `deque.insert(i, x)` is O(n) — the trap

```python
d = deque(range(100_000))
d.insert(0, "head")   # student expects O(1) because deque
```

**Symptom:** `d.insert(0, "head")` is slow — about as slow as `list.insert(0, ...)` for the same size.

**Why:** `deque.insert(i, x)` exists for API parity with `list`, but internally it walks from the nearer end to position `i`, then shifts every element between `i` and that end. That is O(n) — the same shape as `list.insert(0, ...)`. The deque does not magically make middle-index operations cheap.

**Fix:** Do not use `deque.insert`. If you need a middle insert, you almost certainly want a `list` — or a different data structure entirely (a `sortedcontainers.SortedList`, or a `list` you keep sorted with `bisect`). The `deque` API surface *has* `insert` for completeness, but using it is a bug.

### Mistake 3: Indexing into a long `deque` for random access

```python
d = deque(range(1_000_000))
x = d[500_000]   # student expects O(1)
```

**Symptom:** Random indexing on a million-element `deque` is measurable — nanoseconds in CPython terms, but enough to dominate a tight loop.

**Why:** `deque.__getitem__(i)` walks from the nearer end (head or tail) to position `i`. The walk is O(min(i, len-i)) — for `i = 500_000` in a million-element deque that is half a million pointer dereferences.

**Fix:** If you need random access by index, convert to `list` once and index the list. If the use case is genuinely random-access, `deque` is the wrong data structure — `list` is.

## Engineering Trade-Offs

**Decision:** Use `deque` for any FIFO, LIFO, ring-buffer, or "popleft/appendleft" pattern. Use `list` for random access and middle-index mutation.

**Both sides:** `list` wins for:

1. Random access (`d[i]`, `d[i:j]`) — O(1) for `list`, O(min(i, n-i)) for `deque`.
2. Middle insertion / deletion (`d.insert(i, x)`, `del d[i]`) — both O(n), but `list` has a smaller constant factor.
3. Slicing (`d[i:j:k]`) — `list` slice is O(j-i); `deque` slice requires a full walk.
4. Memory — `list` is a contiguous pointer array (one allocation, amortised); `deque` is a linked list of fixed-size blocks (more allocations, more pointer-chasing, worse cache locality for full scans).

`deque` wins for:

1. `appendleft` / `popleft` — O(1) vs `list`'s O(n).
2. `maxlen` ring buffer — there is no `list` equivalent; you have to write `if len > cap: pop(0)` yourself.
3. `rotate(n)` — there is no `list.rotate`; you would write `d[:] = d[-n:] + d[:-n]` which is O(n) with copies.

**Commitment:** `boardly/audit.py` uses `deque(maxlen=1000)` for the audit log. `boardly/metrics.py` and `boardly/grouping.py` use `list` and `dict` respectively because they need random access. The rule of thumb the codebase follows: "If you find yourself writing `pop(0)` or `insert(0, ...)`, reach for `deque`."

## Exercises

1. **Exercise 1 — Capacity change.** Change `AuditLog(capacity=3)` to `capacity=10` and re-run. Confirm the buffer now keeps all 5 events. `Verify: uv run python -c "from boardly.audit import AuditLog; from uuid import uuid4; from datetime import datetime, UTC; from dataclasses import dataclass; log=AuditLog(capacity=10); [log.record(type('E',(),{'actor_id':uuid4(),'action':f'a_{i}','target_id':uuid4(),'at':datetime.now(UTC)})()) for i in range(5)]; print(len(log))"`
2. **Exercise 2 — `rotate(0)`.** Confirm that `deque.rotate(0)` is a no-op. `Verify: uv run python -c "from collections import deque; d=deque([1,2,3]); d.rotate(0); print(list(d))"`
3. **Exercise 3 — Time `popleft` vs `pop(0)`.** Build a 100,000-element `deque` and `list`. Time `popleft` and `pop(0)` of 1,000 elements. Confirm `deque` is roughly 1000× faster. `Verify: uv run python -c "from collections import deque; import timeit; print('deque:', timeit.timeit('from collections import deque; d=deque(range(10000)); [d.popleft() for _ in range(1000)]', number=100)); print('list:', timeit.timeit('d=list(range(10000)); [d.pop(0) for _ in range(1000)]', number=100))"`
4. **Exercise 4 — `index` (3.5+).** Use `deque.index(x)` to find the position of an element. Confirm it is O(min(i, n-i)) not O(1). `Verify: uv run python -c "from collections import deque; d=deque([1,2,3,4,5]); print(d.index(3))"`
5. **Exercise 5 — Round-robin scheduler.** Build a `deque` of three worker UUIDs and a `next_worker()` function that uses `rotate(-1)` and returns the new head. `Verify: uv run python -c "from collections import deque; from uuid import uuid4; ws=deque([uuid4() for _ in range(3)]); ws.rotate(-1); print(ws[0])"`

## Verification

```bash
$ uv run python boardly/audit.py
capacity 3, recorded 5 -> len=3
recent 3: ['action_2', 'action_3', 'action_4']

--- rotate demo ---
before: [1, 2, 3, 4, 5]
rotate(2): [4, 5, 1, 2, 3]
rotate(-1): [5, 1, 2, 3, 4]

--- extendleft demo ---
extendleft([4,5,6]) -> [6, 5, 4, 1, 2, 3]
```

## Previously Learned Here

- [[04-collections/01-Counter]] — `Counter` is the gentlest entry to `collections`.
- [[04-collections/02-defaultdict]] — `defaultdict` shows the "small focused class" pattern that `deque` continues.

## What's Next

[[04-collections/04-namedtuple]] — leave the dynamic-container side of `collections` and enter the static-record side. `namedtuple` gives you a class with named fields, an `_asdict()`, and the memory footprint of a tuple (one object header plus N pointers, no per-instance `__dict__`). It is the lightest "data carrier" the standard library offers — and the bridge to `dataclasses`, which is Section 06.

## Sources

- **Python `collections.deque` documentation** — https://docs.python.org/3/library/collections.html#collections.deque — accessed 2026-10-23 — the canonical reference for `maxlen`, `appendleft`, `popleft`, `rotate`, `extendleft`, `index`, and `insert`.
- **CPython `_collectionsmodule.c` (deque C source)** — https://github.com/python/cpython/blob/3.12/Modules/_collectionsmodule.c — accessed 2026-10-23 — the actual C implementation of `deque`; the block-layout comment at the top is worth reading.
- **What's New in Python 3.5 — `deque` methods** — https://docs.python.org/3/whatsnew/3.5.html#collections — accessed 2026-10-23 — the changelog entry for the `deque.index`, `deque.insert`, `deque.copy`, and `deque.count` additions (no dedicated PEP; the additions landed in the 3.5 release).

## What We Learned

- `deque(maxlen=N)` is a ring buffer: when full, `append` drops from the opposite end.
- `appendleft` and `popleft` are O(1); `insert(0, ...)` and `pop(0)` on `list` are O(n).
- `rotate(n)` is O(min(|n|, len)) — it walks a slice around the ring, not every element.
- `extendleft` pushes one item at a time onto the head, so the result is the input reversed.
- `deque.insert(i, x)` exists for API parity but is O(n) — do not use it.
- Random indexing on a `deque` walks from the nearer end; for random access, `list` wins.
