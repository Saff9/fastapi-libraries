"""asyncio.Semaphore and asyncio.Condition on boardly.

Semaphore = capacity control. The boardly use: a pool of N DB connections;
every outbound query acquires one slot via `async with sem:` so we never
exceed the limit. Condition = the wait/notify pattern: a producer publishes
new data and notifies one or all waiters.

Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class Project:
    slug: str


# --- Pattern A: Semaphore for bounded concurrency (DB pool) ---
class DbPool:
    """A bounded pool of N connections; Semaphore enforces the cap."""

    def __init__(self, capacity: int) -> None:
        self._sem = asyncio.Semaphore(value=capacity)
        self._active = 0
        self._peak = 0

    async def query(self, slug: str) -> Project:
        async with self._sem:               # acquire a slot (blocks if all in use)
            self._active += 1
            self._peak = max(self._peak, self._active)
            await asyncio.sleep(0.02)        # simulate DB round-trip
            self._active -= 1
            return Project(slug=slug)

    @property
    def peak(self) -> int:
        return self._peak


async def bounded_concurrency_demo() -> None:
    print("=== Semaphore bounds concurrent DB queries ===")
    pool = DbPool(capacity=3)                # only 3 connections
    # 10 concurrent queries — without the Semaphore, all 10 would hit the DB
    # at the same instant. With it, only 3 are active at any moment.
    tasks = [asyncio.create_task(pool.query(f"p{i}")) for i in range(10)]
    results = await asyncio.gather(*tasks)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")
    print(f"  peak concurrency: {pool.peak} (capped at 3)")


# --- Pattern B: Semaphore(value=1) is NOT a Lock (semantics differ) ---
async def semaphore_vs_lock_demo() -> None:
    print("\n=== Semaphore(1) is NOT a Lock (release-without-acquire) ===")
    sem = asyncio.Semaphore(value=1)
    # Lock would raise RuntimeError("release unlocked lock"); Semaphore just
    # increments its internal counter. So Semaphore(1) lets a buggy caller
    # 'release' without acquiring — and a second task can then acquire it
    # concurrently with the first.
    sem.release()                          # release without acquire
    async with sem:                        # acquires (counter goes 2 -> 1)
        print("  inside sem: counter would be 1 (should be 0 for a Lock)")
    # Use asyncio.Lock when you need mutual-exclusion semantics. Use a
    # Semaphore when you mean capacity (e.g. a pool of N connections).


# --- Pattern C: Condition — notify_one / notify_all / wait ---
async def condition_demo() -> None:
    print("\n=== Condition: notify_one / notify_all / wait ===")
    cond = asyncio.Condition()
    state: dict[str, str] = {"status": "init"}

    async def waiter(name: str) -> None:
        async with cond:                    # MUST hold the lock to wait
            await cond.wait()               # releases the lock while waiting
            print(f"  {name} woke up; status={state['status']!r}")

    async def producer() -> None:
        await asyncio.sleep(0.01)            # let waiters queue first
        async with cond:
            state["status"] = "ready"
            cond.notify_all()                # wake every waiter
            print("  producer: notify_all() sent")

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(3)]
    await producer()
    await asyncio.gather(*waiters)


# --- Pattern D: notify_one wakes exactly one waiter ---
async def notify_one_demo() -> None:
    print("\n=== notify_one wakes exactly one waiter ===")
    cond = asyncio.Condition()
    woke: list[str] = []

    async def waiter(name: str) -> None:
        async with cond:
            await cond.wait()
            woke.append(name)

    async def producer(n: int) -> None:
        await asyncio.sleep(0.01)
        async with cond:
            for _ in range(n):
                cond.notify(1)               # wake one waiter at a time

    waiters = [asyncio.create_task(waiter(f"w{i}")) for i in range(4)]
    await producer(2)                        # only 2 of the 4 will be woken
    await asyncio.sleep(0.01)
    print(f"  woke: {woke} (notify_one called twice; 2 waiters left blocked)")
    for w in waiters:
        if not w.done():
            w.cancel()
            try:
                await w
            except asyncio.CancelledError:
                pass


async def main() -> None:
    await bounded_concurrency_demo()
    await semaphore_vs_lock_demo()
    await condition_demo()
    await notify_one_demo()


if __name__ == "__main__":
    asyncio.run(main())
