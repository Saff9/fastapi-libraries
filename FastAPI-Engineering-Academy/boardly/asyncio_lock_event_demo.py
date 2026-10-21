"""asyncio.Lock and asyncio.Event on boardly.

Lock = async mutual exclusion (only one task in the critical section).
Event = one-to-many signal (one setter, N waiters wake up at the same time).

The boardly use: a tiny in-process cache guarded by a Lock so two concurrent
refresh tasks don't stampede the upstream; an Event that signals "the cache
is primed" so N worker coroutines can start at the same instant.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class Project:
    slug: str
    name: str


# --- The shared state we protect ---
class ProjectCache:
    """Tiny in-process cache. The Lock serialises refresh."""

    def __init__(self) -> None:
        self._cache: dict[str, Project] = {}
        self._lock = asyncio.Lock()           # async mutual exclusion
        self._primed = asyncio.Event()        # "cache is ready" signal
        self._refresh_calls = 0

    async def _refresh(self, slug: str) -> Project:
        # Simulate a 30ms DB round-trip.
        await asyncio.sleep(0.03)
        self._refresh_calls += 1
        return Project(slug=slug, name=slug.title())

    async def get(self, slug: str) -> Project:
        async with self._lock:               # FIFO fair; only one task in here
            if slug not in self._cache:      # double-checked pattern
                self._cache[slug] = await self._refresh(slug)
            return self._cache[slug]

    async def prime_initial_set(self, slugs: list[str]) -> None:
        async with self._lock:
            for slug in slugs:
                self._cache[slug] = await self._refresh(slug)
        self._primed.set()                   # wake every waiter at once

    async def wait_until_ready(self) -> None:
        await self._primed.wait()            # blocks this task only

    @property
    def refresh_calls(self) -> int:
        return self._refresh_calls


# --- Demo A: the Lock prevents a stampede ---
async def stampede_demo() -> None:
    print("=== Lock prevents a stampede ===")
    cache = ProjectCache()

    # 5 concurrent gets for the SAME slug — without the lock, all 5 would
    # miss the cache and hit the DB 5 times. With the Lock, the first task
    # populates the cache; the other 4 wait and read the cached value.
    tasks = [asyncio.create_task(cache.get("alpha")) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print(f"  results: {[r.name for r in results]}")
    print(f"  upstream calls: {cache.refresh_calls} (expected 1)")


# --- Demo B: the Event wakes N waiters at the same instant ---
async def event_demo() -> None:
    print("\n=== Event wakes N waiters at once ===")
    cache = ProjectCache()

    async def worker(name: str) -> str:
        await cache.wait_until_ready()       # every worker blocks here
        proj = await cache.get(name)
        return f"{name} -> {proj.name}"

    workers = [asyncio.create_task(worker(s)) for s in ("alpha", "beta", "gamma")]
    # Give the workers a turn to start and block on the Event.
    await asyncio.sleep(0.01)
    print("  priming cache...")
    await cache.prime_initial_set(["alpha", "beta", "gamma"])
    results = await asyncio.gather(*workers)
    print(f"  results: {results}")


# --- Demo C: Lock is FIFO fair (3.10+ guarantee) ---
async def fifo_demo() -> None:
    print("\n=== Lock is FIFO fair (3.10+) ===")
    lock = asyncio.Lock()
    order: list[str] = []

    async def worker(name: str) -> None:
        async with lock:
            order.append(name)
            await asyncio.sleep(0.001)      # yield so others queue up

    # Acquire the lock first, so the workers queue in creation order.
    async with lock:
        tasks = [asyncio.create_task(worker(f"w{i}")) for i in range(5)]
        await asyncio.sleep(0.01)            # let them all queue
    await asyncio.gather(*tasks)
    print(f"  acquisition order: {order}  (expected ['w0','w1','w2','w3','w4'])")


# --- Demo D: NOT reentrant — re-acquire from the same task deadlocks ---
async def reentrancy_demo() -> None:
    print("\n=== asyncio.Lock is NOT reentrant (deadlock if you try) ===")
    lock = asyncio.Lock()

    async def inner() -> None:
        async with lock:                    # ← second acquire from the same task
            print("  this never prints")

    # Cancel after a short delay so the demo doesn't hang forever.
    task = asyncio.create_task(_hold_and_call_inner(lock, inner))
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
    except TimeoutError:
        task.cancel()
        print("  cancelled — would deadlock forever without the timeout")


async def _hold_and_call_inner(lock: asyncio.Lock, inner: Callable[[], Awaitable[None]]) -> None:
    async with lock:
        await inner()                       # tries to re-acquire


async def main() -> None:
    await stampede_demo()
    await event_demo()
    await fifo_demo()
    await reentrancy_demo()


if __name__ == "__main__":
    asyncio.run(main())
