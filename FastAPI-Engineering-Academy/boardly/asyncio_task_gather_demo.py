"""asyncio.create_task / asyncio.gather / asyncio.wait_for on boardly projects.

Shows the canonical boardly pattern: fetch N projects concurrently from a
slow upstream service, with a per-call timeout and a gather that never raises
(return_exceptions=True). Run it and read the trace top to bottom.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class Project:
    slug: str
    name: str
    budget_cents: int


# --- Fake upstream: a slow async "database" call ---
async def fetch_project(slug: str, *, delay: float = 0.05) -> Project:
    """Simulate a 50ms DB round-trip."""
    await asyncio.sleep(delay)
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)


async def fetch_project_or_timeout(slug: str, *, delay: float = 0.05) -> Project:
    """Same as fetch_project but raises ValueError for slug 'boom'."""
    await asyncio.sleep(delay)
    if slug == "boom":
        raise ValueError(f"project {slug!r} not found")
    return Project(slug=slug, name=slug.title(), budget_cents=10_000)


# --- Pattern 1: sequential (the slow baseline) ---
async def fetch_all_sequential(slugs: list[str]) -> list[Project]:
    return [await fetch_project(s) for s in slugs]


# --- Pattern 2: concurrent via create_task + gather ---
async def fetch_all_concurrent(slugs: list[str]) -> list[Project]:
    tasks = [asyncio.create_task(fetch_project(s)) for s in slugs]
    return await asyncio.gather(*tasks)


# --- Pattern 3: gather with return_exceptions=True (never raises) ---
async def fetch_all_tolerant(slugs: list[str]) -> list[Project | ValueError]:
    tasks = [asyncio.create_task(fetch_project_or_timeout(s)) for s in slugs]
    return await asyncio.gather(*tasks, return_exceptions=True)


# --- Pattern 4: wait_for with per-call timeout ---
async def fetch_with_timeout(slug: str, timeout: float = 0.02) -> Project | None:
    try:
        return await asyncio.wait_for(fetch_project(slug, delay=0.05), timeout=timeout)
    except TimeoutError:
        print(f"  [timeout] project {slug!r} did not respond in {timeout}s")
        return None


# --- Pattern 5: the bare-coroutine bug (fire-and-forget needs create_task) ---
async def fire_and_forget_bug() -> None:
    """The wrong way: a bare coro() is never scheduled."""
    fetch_project("ghost")  # ← never awaited, never scheduled
    await asyncio.sleep(0.01)  # give the loop a turn to print the warning


async def fire_and_forget_correct() -> None:
    """The right way: create_task schedules the coro on the loop."""
    task = asyncio.create_task(fetch_project("ghost"))
    # don't await — fire and forget. But you must keep a reference or the
    # task can be garbage-collected mid-flight (CPython 3.12 warning).
    await asyncio.sleep(0.06)
    if task.done():
        print(f"  [fire-and-forget] ghost result: {task.result()}")


async def main() -> None:
    slugs = ["alpha", "beta", "gamma"]

    print("=== sequential (3 × 50ms ≈ 150ms) ===")
    results = await fetch_all_sequential(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== concurrent via create_task + gather (≈ 50ms) ===")
    results = await fetch_all_concurrent(slugs)
    print(f"  {len(results)} projects: {[p.slug for p in results]}")

    print("\n=== gather with return_exceptions=True (no raise) ===")
    mixed = await fetch_all_tolerant(["alpha", "boom", "gamma"])
    for item in mixed:
        if isinstance(item, Project):
            print(f"  OK   {item.slug}")
        else:
            print(f"  FAIL {type(item).__name__}: {item}")

    print("\n=== wait_for with a too-short timeout ===")
    out = await fetch_with_timeout("delta", timeout=0.02)
    print(f"  delta result: {out}")

    print("\n=== bare-coroutine bug (warning to stderr) ===")
    await fire_and_forget_bug()

    print("\n=== fire-and-forget via create_task (the correct way) ===")
    await fire_and_forget_correct()


if __name__ == "__main__":
    asyncio.run(main())
