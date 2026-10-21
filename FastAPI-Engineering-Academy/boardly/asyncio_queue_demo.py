"""asyncio.Queue on boardly: the producer-consumer pattern, with join/task_done,
maxsize backpressure, and the *_nowait variants. The 3.13+ Queue.shutdown()
method is version-gated inline (it does not exist on the 3.12 runtime).
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass


@dataclass
class Ticket:
    id: int
    title: str


# --- Pattern A: bounded producer-consumer with maxsize backpressure ---
async def producer(q: asyncio.Queue[Ticket | None], n: int, n_consumers: int) -> None:
    for i in range(n):
        ticket = Ticket(id=i, title=f"ticket-{i}")
        await q.put(ticket)              # blocks if the queue is full
        print(f"  [producer] put {ticket.id}")
    # One sentinel per consumer: when a consumer sees None, it exits.
    for _ in range(n_consumers):
        await q.put(None)
    print("  [producer] done")


async def consumer(q: asyncio.Queue[Ticket | None], name: str) -> int:
    processed = 0
    while True:
        ticket = await q.get()
        if ticket is None:              # sentinel -> exit
            q.task_done()
            break
        print(f"  [consumer {name}] got {ticket.id} ({ticket.title})")
        await asyncio.sleep(0.005)      # simulate work
        q.task_done()                   # decrement the unfinished counter
        processed += 1
    return processed


async def producer_consumer_demo() -> None:
    print("=== bounded producer-consumer (maxsize=3, 2 consumers) ===")
    q: asyncio.Queue[Ticket | None] = asyncio.Queue(maxsize=3)
    prod = asyncio.create_task(producer(q, 6, n_consumers=2))
    cons1 = asyncio.create_task(consumer(q, "A"))
    cons2 = asyncio.create_task(consumer(q, "B"))
    await prod
    await q.join()                     # waits for every task_done() to land
    # Both consumers see their sentinel and exit on their own — no cancel needed.
    results = await asyncio.gather(cons1, cons2)
    print(f"  processed: A={results[0]}, B={results[1]}")


# --- Pattern B: the *_nowait variants (raise instead of block) ---
async def nowait_demo() -> None:
    print("\n=== put_nowait / get_nowait ===")
    q: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
    q.put_nowait(1)                    # ok, queue had room
    try:
        q.put_nowait(2)                # queue full -> QueueFull
    except asyncio.QueueFull as e:
        print(f"  put_nowait raised: {type(e).__name__}")
    print(f"  get_nowait -> {q.get_nowait()}")   # ok, queue had an item
    try:
        q.get_nowait()                 # queue empty -> QueueEmpty
    except asyncio.QueueEmpty as e:
        print(f"  get_nowait raised: {type(e).__name__}")


# --- Pattern C: q.join() needs every get() to be matched by a task_done() ---
async def join_without_task_done_demo() -> None:
    print("\n=== join() waits for task_done() (and the bug if you forget) ===")
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.put_nowait(2)
    _ = q.get_nowait()                  # forgot to call task_done()
    q.task_done()                       # only matched one get()
    try:
        await asyncio.wait_for(q.join(), timeout=0.1)
    except TimeoutError:
        print("  join() timed out — one task_done() missing")


# --- Pattern D: 3.13+ Queue.shutdown() (version-gated; not in 3.12) ---
async def shutdown_demo() -> None:
    print("\n=== Queue.shutdown() — Python 3.13+, version-gated ===")
    if sys.version_info < (3, 13):
        print(f"  running Python {sys.version_info[:3]} -> shutdown() not available")
        print("  (3.13+: q.shutdown() closes the queue immediately;")
        print("   pending get() raises QueueShutDown; put() raises QueueShutDown)")
        return
    # On 3.13+ this branch runs:
    q: asyncio.Queue[int] = asyncio.Queue()
    q.put_nowait(1)
    q.shutdown()                       # 3.13+: immediately close the queue
    try:
        await q.get()                  # already-empty + shut down
    except asyncio.QueueShutDown as e:
        print(f"  get() raised: {type(e).__name__}")


async def main() -> None:
    await producer_consumer_demo()
    await nowait_demo()
    await join_without_task_done_demo()
    await shutdown_demo()


if __name__ == "__main__":
    asyncio.run(main())
