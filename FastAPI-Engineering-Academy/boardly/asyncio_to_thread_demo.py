"""asyncio.to_thread and loop.run_in_executor on boardly.

to_thread (3.9+) is the canonical way to call blocking sync code from an
async function. run_in_executor is the lower-level form. The boardly use:
a sync `requests.get` call to an old internal service that we must call
until it's migrated — wrapped in to_thread so it doesn't block the loop.

Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class Project:
    slug: str
    name: str


# --- A blocking sync function. NOT async. This is the kind of code that
# would freeze the event loop if you called it directly from a coroutine. ---
def blocking_fetch_project(slug: str, *, latency: float = 0.05) -> Project:
    """Pretend this is `requests.get(...).json()` — a blocking call."""
    time.sleep(latency)            # sync sleep — blocks the calling thread
    return Project(slug=slug, name=slug.title())


# --- Pattern A: the wrong way — call blocking code directly from async ---
async def wrong_way() -> None:
    """Blocking call in an async function freezes the whole event loop."""
    print("  [wrong_way] start blocking call (loop is frozen)")
    result = blocking_fetch_project("alpha")    # blocks the entire loop
    print(f"  [wrong_way] {result.slug}")


# --- Pattern B: the right way — asyncio.to_thread (3.9+) ---
async def to_thread_way(slug: str) -> Project:
    """Run the blocking function in a worker thread; the loop keeps going."""
    # asyncio.to_thread(func, *args, **kwargs) — Python 3.9+.
    # Returns a coroutine. Awaiting it runs func(*args, **kwargs) in a thread
    # from the default ThreadPoolExecutor and returns its result.
    return await asyncio.to_thread(blocking_fetch_project, slug)


# --- Pattern C: the lower-level form — loop.run_in_executor ---
async def run_in_executor_way(slug: str) -> Project:
    """The lower-level form: explicit loop + executor + func + args."""
    loop = asyncio.get_running_loop()
    # executor=None -> default ThreadPoolExecutor
    # (max_workers = min(32, os.cpu_count() + 4) since 3.8).
    return await loop.run_in_executor(None, blocking_fetch_project, slug)


async def run_in_executor_custom_way(slug: str) -> Project:
    """A custom ThreadPoolExecutor with a fixed max_workers."""
    loop = asyncio.get_running_loop()
    # max_workers = min(32, os.cpu_count() + 4) is the default; you can override.
    with ThreadPoolExecutor(max_workers=2) as ex:
        return await loop.run_in_executor(ex, blocking_fetch_project, slug)


# --- Pattern D: concurrent to_thread calls keep the loop responsive ---
async def concurrent_to_thread_demo() -> None:
    print("=== concurrent to_thread (loop stays responsive) ===")
    # 3 blocking calls in parallel — each runs in its own worker thread.
    # The asyncio.sleep(0.001) coroutine co-operates with them, proving the
    # loop is not frozen.
    async def heartbeat() -> None:
        for i in range(15):
            print(f"    heartbeat tick {i}")
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    results = await asyncio.gather(
        to_thread_way("alpha"),
        to_thread_way("beta"),
        to_thread_way("gamma"),
    )
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    print(f"  results: {[p.slug for p in results]}")


# --- Pattern E: the rule — don't call requests.get in async; use httpx or to_thread ---
async def requests_rule_demo() -> None:
    print("\n=== the rule: don't call requests.get in async ===")
    # Demonstrate the principle with urllib (which is in the stdlib) instead
    # of requests, so the demo runs without an external dependency.
    # The WRONG way:
    #     import requests
    #     r = requests.get("https://example.com/projects/alpha")  # blocks the loop
    # The RIGHT way #1 (offload to a thread):
    #     r = await asyncio.to_thread(requests.get, url)
    # The RIGHT way #2 (use an async HTTP client):
    #     async with httpx.AsyncClient() as c:
    #         r = await c.get(url)

    def sync_get(url: str) -> int:
        # urllib.request.urlopen is blocking — same family as requests.get.
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status

    status = await asyncio.to_thread(sync_get, "https://example.com")
    print(f"  sync_get via to_thread -> {status}")
    print(f"  default ThreadPoolExecutor max_workers = min(32, os.cpu_count() + 4) = {min(32, os.cpu_count() + 4)}")


async def main() -> None:
    print("=== WRONG way: blocking call in async (loop frozen) ===")
    await wrong_way()

    await concurrent_to_thread_demo()
    await requests_rule_demo()


if __name__ == "__main__":
    asyncio.run(main())
