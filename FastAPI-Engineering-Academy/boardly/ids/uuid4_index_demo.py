# boardly/ids/uuid4_index_demo.py
"""Why uuid4 hurts DB indexes — and what uuid7 (3.14+) would do instead."""
import random
import sys
import uuid
from dataclasses import dataclass, field


@dataclass
class Project:
    # The field type is UUID either way — lesson 01's commitment to the
    # type does not depend on the factory. Only the default_factory changes.
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""


def make_uuid4_batch(n: int, rng: random.Random) -> list[uuid.UUID]:
    """Build n v4 UUIDs.

    In production you call uuid.uuid4() (which uses os.urandom). Here we
    drive a seeded rng so this script prints reproducible output for the
    lesson. The index-locality behaviour is identical: the .int values
    are scattered uniformly across the 2^122 space, regardless of seed.
    """
    return [uuid.UUID(int=rng.getrandbits(128), version=4) for _ in range(n)]


def make_uuid7_batch(n: int, rng: random.Random) -> list[uuid.UUID]:
    """Build n v7 UUIDs — Python 3.14+ only.

    On 3.14+ you would call uuid.uuid7() directly. This function reconstructs
    the same layout from a millisecond timestamp + random tail, so the lesson
    can describe what the index would look like on a 3.12 runtime. In real
    code on 3.14+, just call uuid.uuid7() — it does the timestamp + random
    work for you.
    """
    import time
    out = []
    base_ms = 1792737785650           # fixed for reproducible output; in production,
                                     # uuid.uuid7() reads time.time_ns() each call
    for i in range(n):
        ms = base_ms + i                   # advance the ms clock every UUID
        rand_a = rng.getrandbits(12)
        rand_b = rng.getrandbits(62)
        v7_int = (ms & ((1 << 48) - 1)) << 80           # 48 bits of timestamp at the top
        v7_int |= 0x7 << 76                              # 4-bit version (7)
        v7_int |= (rand_a & ((1 << 12) - 1)) << 64       # 12-bit rand_a
        v7_int |= 0b10 << 62                             # 2-bit variant marker
        v7_int |= rand_b & ((1 << 62) - 1)               # 62-bit rand_b at the bottom
        # NOTE: do NOT pass version=7 to the UUID ctor on 3.12 — the ctor
        # rejects versions > 5 (the version range was extended to 6/7/8 in
        # 3.14). The bits above already encode version=7 in the right place,
        # so a plain UUID(int=v7_int) reads back as version=7 on .version.
        out.append(uuid.UUID(int=v7_int))
    return out


if __name__ == "__main__":
    rng = random.Random(1234)

    batch = make_uuid4_batch(8, rng)
    print("--- 8 uuid4 values, raw insertion order ---")
    for i, u in enumerate(batch, start=1):
        print(f"{i:2}. int={u.int:>39}  uuid={u}")

    print("\n--- same 8 uuid4 values, sorted ascending by .int ---")
    for i, u in enumerate(sorted(batch, key=lambda x: x.int), start=1):
        print(f"{i:2}. int={u.int:>39}  uuid={u}")

    insertion_order = {u: i for i, u in enumerate(batch, start=1)}
    print("\n--- insertion-position vs sorted-position (uuid4) ---")
    for sorted_pos, u in enumerate(sorted(batch, key=lambda x: x.int), start=1):
        print(f"inserted at {insertion_order[u]:2}, sorted at {sorted_pos:2}")

    seq = list(range(8))
    print("\n--- 8 sequential surrogate ints (autoincrement) ---")
    print("sorted(seq) == seq:", sorted(seq) == seq)

    # uuid7 — only on 3.14+. On 3.12, we describe what it would do.
    print("\n--- uuid7 demo (Python 3.14+ only) ---")
    if hasattr(uuid, "uuid7"):
        v7_batch = [uuid.uuid7() for _ in range(8)]
        for i, u in enumerate(v7_batch, start=1):
            print(f"{i:2}. uuid={u}  version={u.version}  variant={u.variant}")
        print("sorted(v7_batch) == v7_batch:", sorted(v7_batch) == v7_batch)
    else:
        # Reconstruct the layout so you can see the shape. This is NOT
        # the production path; it is a visualisation. In production on
        # 3.14+, just call uuid.uuid7().
        v7_batch = make_uuid7_batch(8, rng)
        for i, u in enumerate(v7_batch, start=1):
            print(f"{i:2}. uuid={u}  version={u.version}  variant={u.variant}")
        print("sorted(v7_batch) == v7_batch:", sorted(v7_batch) == v7_batch)
        print(f"(runtime: Python {sys.version_info[:3]} — uuid.uuid7 not available,")
        print(" layout reconstructed for visualisation only)")

    p = Project(name="alpha")
    print(f"\nProject.id type: {type(p.id).__name__} (UUID either way)")
    print(f"Project.id factory: uuid4 (default) — see migration rule below")
