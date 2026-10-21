---
title: "Lesson 02: uuid4 vs uuid7"
aliases:
 - uuid4 vs uuid7
 - uuid7
 - UUID index locality
 - database primary key UUID
tags:
 - uuid
 - python-stdlib
 - database
 - version-gated-3.14
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[16-uuid/01-UUID-variants]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[16-uuid/01-UUID-variants]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[17-decimal/01-Decimal-Basics]]"
---

# Lesson 02: uuid4 vs uuid7

*Why `uuid4` is great for uniqueness and terrible for database indexes — and why `uuid7` (Python 3.14+, version-gated) is the right default for new primary keys in `boardly`.*

**You're at the very beginning of Section 16, Lesson 02.**

You read lesson 01 and committed your dataclass to `id: UUID`. Good. Now you have a factory choice to make. The default reflex — `uuid.uuid4()` everywhere — is right for correlation tokens and request IDs and right for *uniqueness*, but it is wrong for *database primary keys*. This lesson shows you why: `uuid4` is 122 random bits, scattered uniformly across the `2^122` space, and a B-tree index on that column will fragment the moment it has more than a leaf page of rows. The fix is `uuid7` — Python 3.14+, version-gated — whose 48-bit millisecond-timestamp prefix makes new rows land on the rightmost leaf page, where append-mostly writes belong. We will run the `uuid4` demo on this 3.12 runtime (it works), describe what `uuid7` would do (it doesn't exist here), and commit to a migration rule: new tables use `uuid7`; existing tables keep `uuid4`. Take your time. Type every example. **This is how you learn.**

#uuid #database #version-gated-3.14

## Learning Objectives

By the end of this lesson you will be able to:

1. **Explain why `uuid4` hurts B-tree indexes** — name the three failure modes (page fragmentation, write amplification, cache-miss locality) and explain how each follows from the random-bit layout.
2. **Describe the `uuid7` layout** — 48-bit millisecond-timestamp prefix + 12 random bits + 62 random bits + version/variant markers — and explain why the timestamp prefix produces monotonically increasing values within a millisecond bucket.
3. **Version-gate `uuid7` correctly** — `hasattr(uuid, "uuid7")` for runtime feature detection, `sys.version_info >= (3, 14)` for import-time fail-fast, and know that on the 3.12 runtime this vault targets, `uuid.uuid7()` does not exist.
4. **State the migration rule** — new tables use `uuid7` for primary keys; existing tables keep `uuid4`. Never change primary-key type on existing rows. Cross-link to [[06-dataclasses/01-dataclass-Basics]] for the `id: UUID` field pattern that survives the migration.
5. **Distinguish "opaque ID" from "ordered ID"** — pick `uuid4` for correlation tokens and request IDs (where you do not want timestamp leakage), pick `uuid7` for database primary keys (where you want index locality).

## Prerequisites

Before starting, you need:

- **Lesson 01 of this section** — [[16-uuid/01-UUID-variants]]. Lesson 01 committed the type (`id: UUID`); this lesson commits the factory. You need the type, the accessors, and the eight-variant map from lesson 01 in your head before this lesson's index-locality argument makes sense.
- **The `@dataclass` field pattern** — [[06-dataclasses/01-dataclass-Basics]]. The `id: UUID` field with a `uuid.uuid4()` (or, on 3.14+, `uuid.uuid7()`) default is the canonical `field()` example; the dataclass lesson is where the surrounding machinery lives.
- **About 40–55 minutes of focused time.**

**The most common gap: confusing "uniqueness" with "ordering".**

`uuid4` and `uuid7` are equally unique — both are 128-bit values with collision-resistant randomness in the tail — but they are not equally *ordered*. A `uuid4` carries no ordering information at all; the `.int` of two `uuid4`s generated microseconds apart is just as likely to be larger-smaller as smaller-larger. A `uuid7` carries a millisecond timestamp in its high bits, so two `uuid7`s generated microseconds apart are *monotonically increasing* (same millisecond bucket → random ordering within; different millisecond buckets → strictly increasing). The single biggest mistake students make in this lesson is reaching for `uuid4` on a primary key because "it's random, so it's safe" — it is safe, and it is also uniquely bad for indexes. Uniqueness is necessary; ordering is what an index needs. That is the lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/ids/uuid4_primary_key.py — the bad old days
import uuid
from dataclasses import dataclass, field


@dataclass
class Project:
    id: uuid.UUID = field(default_factory=uuid.uuid4)   # ← looks reasonable, isn't
    name: str = ""


# Insert 1 000 000 projects over the lifetime of the service.
# Every Project.id is a fresh uuid4 — 122 random bits.
# The Postgres table has a PRIMARY KEY on id.
# Six months in, the DBA files a ticket: "the projects table's
# index has 73% bloat; insert latency has tripled."
```

The Postgres `PRIMARY KEY` constraint creates a B-tree index on the `id` column. Every B-tree index stores its rows in *key order*, not in *insertion order* — that is the definition of a B-tree. So when you insert a `uuid4` whose `.int` value is, say, `262791086757678410604892959704602962740`, the B-tree does *not* append that row to the rightmost leaf page (which would be one write, one page, no fragmentation). It walks the tree from the root, finds the leaf page whose key range brackets `262791086...`, and inserts the row there — wherever "there" happens to be, which is uniformly random across the `2^122` space, equally likely to land on a hot page or a cold page, equally likely to land near the start of the table or the end.

Three things go wrong, all simultaneously:

1. **Page fragmentation.** A leaf page that is 90% full and gets a new row insertion splits into two 45% full pages. A `uuid4` index hits this constantly, because every insertion lands somewhere already-occupied. The index file grows to 1.5–2x its minimum size; the buffer pool has to hold more pages; cold pages accumulate.
2. **Write amplification.** Each insertion is a random-position write to a random leaf page. On a spinning disk this is seek hell; on an NVMe SSD it is cache-miss hell. The database's write-ahead log writes the same row twice — once to the WAL (sequential, fast) and once to the random-position leaf page (random, slow).
3. **Cache-miss locality.** The hottest leaf page today is the same as the hottest leaf page tomorrow — except with `uuid4` it isn't, because the hot page is "whatever page the random UUID happens to land on". The buffer pool's LRU cache thrashes; the working set is the whole table.

None of this is a Python problem. It is a *factory* problem. The `uuid4` factory generates values that are correct for uniqueness and wrong for ordering. The `uuid7` factory generates values that are correct for both — equal uniqueness (122 random bits in the tail), strict ordering (millisecond timestamp in the prefix).

## The Code

```python
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
```

## Line-by-Line Deep Dive

### Lines 1–12: The model — `id: UUID`, default factory is the choice

```python
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
```

The dataclass field type is `uuid.UUID` — the same commitment lesson 01 made. What changes in this lesson is the `default_factory`: lesson 01 uses `uuid.uuid4`; lesson 02 will commit to `uuid.uuid7` for *new* primary-key fields (with a 3.14+ version-gate). The `field(default_factory=...)` form is the standard dataclass pattern for mutable defaults — calling `uuid.uuid4` (no parens) passes the callable, and the dataclass-generated `__init__` calls it on every new instance. We import `random` for the seeded demo, `sys` for the version check, and `field` from `dataclasses` for the `default_factory` kwarg. Cross-link to [[06-dataclasses/01-dataclass-Basics]] for the surrounding `field()` machinery — `default_factory` is where the field-with-default lesson lives.

**Why `default_factory` and not `default=uuid.uuid4()`?**

Because `default=uuid.uuid4()` would call the factory *once at class-definition time* and assign the resulting `UUID` as the class-level default. Every `Project()` instance that did not pass `id=...` would share the *same* `UUID` value. `default_factory=uuid.uuid4` instead stores the callable and calls it once per instance — every `Project()` gets a fresh UUID. The rule is the same as the rule for `list` and `dict` defaults on dataclasses: mutable defaults need a factory; `UUID` is immutable but the *factory* needs to be re-invoked, so the same rule applies.

### Lines 15–25: The `make_uuid4_batch` helper — and why we seed it

```python
def make_uuid4_batch(n: int, rng: random.Random) -> list[uuid.UUID]:
    """Build n v4 UUIDs.

    In production you call uuid.uuid4() (which uses os.urandom). Here we
    drive a seeded rng so this script prints reproducible output for the
    lesson. The index-locality behaviour is identical: the .int values
    are scattered uniformly across the 2^122 space, regardless of seed.
    """
    return [uuid.UUID(int=rng.getrandbits(128), version=4) for _ in range(n)]
```

The helper generates `n` UUIDs by drawing 128 random bits from a *private* `random.Random` instance and constructing `uuid.UUID(int=bits, version=4)`. In production you would never do this — you would call `uuid.uuid4()`, which uses `os.urandom` (cryptographically secure, non-deterministic). The reason we drive a seeded `rng` here is reproducibility: the lesson's Execution Trace has to print the same UUIDs every time, or it is not a verifiable lesson. The `random.Random` instance is private (a function argument, not the global `random` module) so seeding it does not affect any other code that uses `random`.

The crucial honesty note is in the docstring: *the index-locality behaviour is identical*. A seeded RNG and `os.urandom` both produce uniformly distributed bits; the only difference is whether the seed is reproducible. The scatter pattern that hurts the B-tree is the *uniform distribution*, not the seed.

**Why use `version=4` in the constructor here, not just `uuid.UUID(int=bits)`?**

Because passing `version=4` sets the version and variant bits correctly (the top 4 bits of the 7th hex char become `0x4`, the top 2 bits of the 9th hex char become `0b10`). Without `version=4`, the bits would be whatever the rng produced — possibly not a valid v4 UUID at all, possibly a v0 or v8 layout. With `version=4`, the result is indistinguishable from `uuid.uuid4()` output in every accessor (`.version == 4`, `.variant == specified in RFC 4122`). Lesson 01 covered this pattern in its "version= kwarg" block — revisit [[16-uuid/01-UUID-variants]] for the canonical explanation.

### Lines 28–56: The `make_uuid7_batch` helper — and the version-gate

```python
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
```

This function is **not the production path**. On Python 3.14+, you call `uuid.uuid7()` and the standard library does the timestamp extraction and bit packing for you. This function exists in the lesson for one reason: to show you the *shape* of a v7 UUID on the 3.12 runtime this vault targets, where `uuid.uuid7` does not exist. The layout is RFC 9562 §5.7: 48 bits of Unix millisecond timestamp at the top, then 4 bits of version (`0x7`), then 12 bits of `rand_a`, then 2 bits of variant marker (`0b10`), then 62 bits of `rand_b`. The bit shifts in the body of the function assemble those fields into a single 128-bit int, which `uuid.UUID(int=v7_int)` reads back as a v7 UUID (`u.version == 7`). On 3.12, the `UUID(...)` constructor rejects `version=7` as a keyword argument (the version range was 1–5; 6/7/8 were added in 3.14), so the helper packs the version bits into the int directly and passes only `int=` to the constructor.

The crucial property is in the first field: `ms = base_ms + i`. The millisecond timestamp is the *high* 48 bits, so two UUIDs with different `ms` are strictly ordered by `ms` — the first 12 hex chars of the dashed form encode the millisecond timestamp, monotonically increasing across iterations. Within a single millisecond, the 12 bits of `rand_a` and 62 bits of `rand_b` provide `2^74` of random uniqueness — collision-free for any realistic insert rate — but the order *within* a millisecond is random, not monotonic. In production on 3.14+, `uuid.uuid7()` reads the current wall-clock time on every call, so calls that happen in different milliseconds are strictly increasing, and calls that happen in the same millisecond share a timestamp prefix (and therefore land on the same B-tree leaf page — still a massive index-locality win over `uuid4`).

**Warning — `make_uuid7_batch` here is a visualisation, not a library call.**

In production on Python 3.14+, call `uuid.uuid7()`. The standard library handles the timestamp extraction (it reads `time.time_ns()` and converts to milliseconds), the bit packing, and the variant marker. The function above reconstructs the layout so the lesson can show you the shape on 3.12; do not copy it into application code. Note also that on 3.12, the `UUID(...)` constructor rejects `version=7` (the version range was 1–5; 6/7/8 were added in 3.14), so the helper builds the int with the version bits already set and passes only `int=` to the constructor — `UUID(int=v7_int)` reads back `.version == 7` because the version bits are in the correct position in the integer.

### Lines 61–66: The uuid4 insertion-order dump

```python
batch = make_uuid4_batch(8, rng)
print("--- 8 uuid4 values, raw insertion order ---")
for i, u in enumerate(batch, start=1):
    print(f"{i:2}. int={u.int:>39}  uuid={u}")
```

We generate 8 UUIDs and print their `.int` and `str()` form. The `.int` is the full 128-bit value as a Python `int`; the `uuid=` shows the canonical dashed form. The `.int` values are scattered: `39762171245838760582140720650759274425`, `320727959146423810831530906581765649940`, `11884758421083137989320289686624923345`, and so on. There is no monotonic structure. The `.int` of the second UUID is larger than the first; the third is smaller than both; the fourth is in between. The pattern continues — every row is a random scatter.

### Lines 68–71: The uuid4 sorted-by-`.int` dump

```python
print("\n--- same 8 uuid4 values, sorted ascending by .int ---")
for i, u in enumerate(sorted(batch, key=lambda x: x.int), start=1):
    print(f"{i:2}. int={u.int:>39}  uuid={u}")
```

Sorting the same batch by `.int` gives a completely different order. This is what a B-tree index on the `id` column would do internally: store rows in `.int` order, regardless of insertion order. The leaf page a row belongs to depends on its `.int`, *not* on when it was inserted. Every insertion is a random-position write to a random leaf page — and this is exactly what causes the three failure modes (page fragmentation, write amplification, cache-miss locality) that the lesson's Problem section named.

### Lines 73–77: The insertion-vs-sorted table — the smoking gun

```python
insertion_order = {u: i for i, u in enumerate(batch, start=1)}
print("\n--- insertion-position vs sorted-position (uuid4) ---")
for sorted_pos, u in enumerate(sorted(batch, key=lambda x: x.int), start=1):
    print(f"inserted at {insertion_order[u]:2}, sorted at {sorted_pos:2}")
```

This table is the demonstration. For each UUID in the batch, we print "inserted at X, sorted at Y". For a monotonically increasing factory (autoincrement int, or `uuid7` on 3.14+), X equals Y for every row. For `uuid4`, X and Y are unrelated: row 6 is sorted at position 1, row 5 is sorted at position 2, row 3 is sorted at position 3 (a coincidence), row 8 is sorted at position 4, row 4 is sorted at position 5, row 1 is sorted at position 6, row 7 is sorted at position 7 (another coincidence), row 2 is sorted at position 8. Six of eight rows are in the wrong place — that is the page-split rate the B-tree experiences.

**Why does this matter for the database, not just the demo?**

Because the B-tree on the `id` column *is* the sorted order. The database's leaf pages are filled in `.int` order; an insertion is a write to whichever leaf page brackets the new `.int`. With `uuid4`, every insertion lands on a random leaf page — some already-90%-full page that splits into two 45%-full pages, growing the index, fragmenting the file, thrashing the buffer pool. With `uuid7` on 3.14+, every insertion lands on the *rightmost* leaf page (because the timestamp makes the new value larger than all existing values) — the rightmost page fills, fills, fills, splits cleanly into a new rightmost page, and the index grows linearly at the right edge with zero fragmentation in the body. That is the locality the lesson is teaching.

### Lines 79–81: The counter-example — sequential ints

```python
seq = list(range(8))
print("\n--- 8 sequential surrogate ints (autoincrement) ---")
print("sorted(seq) == seq:", sorted(seq) == seq)
```

The counter-example prints `True` — a sequential surrogate (Postgres `SERIAL`, MySQL `AUTO_INCREMENT`, a monotonic int) preserves insertion order in the B-tree. Every new row goes to the rightmost leaf page; every page split creates a new rightmost page; the file grows at the right edge. This is what a `uuid7` index looks like on 3.14+ — the millisecond timestamp at the front of the value produces the same monotonic structure, with the bonus of being a 128-bit globally-unique value (no central counter coordination, no integer overflow, no per-shard sequences).

**Why not just use `SERIAL` then?**

Because `SERIAL` (or `AUTO_INCREMENT`) is a 32-bit or 64-bit integer assigned by the database, and it brings three costs the UUID-type lesson 01 already committed against: (1) every shard needs its own counter range, or you need a central coordinator, or you accept collisions across sharded inserts; (2) the value is enumerable — an attacker who learns `project_id=42` knows to try `project_id=43`; (3) merging two databases requires re-keying every row, because both will have a row with `id=1`. A `uuid7` value is 128-bit, globally unique without coordination, opaque (no enumeration), and merge-safe. You pay a 16-byte storage cost (vs 4 or 8 for the int) and gain all of the above. For a primary key, that trade is worth it.

### Lines 83–92: The uuid7 demo — version-gated at runtime

```python
print("\n--- uuid7 demo (Python 3.14+ only) ---")
if hasattr(uuid, "uuid7"):
    v7_batch = [uuid.uuid7() for _ in range(8)]
    for i, u in enumerate(v7_batch, start=1):
        print(f"{i:2}. uuid={u}  version={u.version}")
    print("sorted(v7_batch) == v7_batch:", sorted(v7_batch) == v7_batch)
else:
    # Reconstruct the layout so you can see the shape. This is NOT
    # the production path; it is a visualisation. In production on
    # 3.14+, just call uuid.uuid7().
    v7_batch = make_uuid7_batch(8, rng)
    for i, u in enumerate(v7_batch, start=1):
        print(f"{i:2}. uuid={u}  version={u.version}")
    print("sorted(v7_batch) == v7_batch:", sorted(v7_batch) == v7_batch)
    print(f"(runtime: Python {sys.version_info[:3]} — uuid.uuid7 not available,")
    print(" layout reconstructed for visualisation only)")
```

The `if hasattr(uuid, "uuid7"):` branch is runtime feature-detection. On Python 3.14+, it takes the *real* path — calls `uuid.uuid7()` eight times and prints the values, then verifies `sorted(v7_batch) == v7_batch` is `True` (because the timestamp prefix makes the values monotonic). On Python 3.12 (this vault's runtime), `hasattr(uuid, "uuid7")` is `False`, so the branch falls back to `make_uuid7_batch` — the visualisation helper that reconstructs the layout — and prints the same shape with an explicit "reconstructed for visualisation only" disclaimer. The disclaimer is the version-gate: it tells the student "this is what uuid7 would do; the real factory is 3.14+".

**Why `hasattr` for runtime and `sys.version_info` for import-time?**

Because they catch different failure modes. `hasattr(uuid, "uuid7")` catches "the runtime is 3.12 but the import succeeded" — useful if your library is loaded into an interpreter you did not choose (a notebook, a Lambda runtime, a customer's environment). `sys.version_info >= (3, 14)` catches "the runtime is wrong at deploy time" — useful as an `assert` at the top of a module that *requires* `uuid7`, so the failure surfaces on the first `import` in CI, not on the first `INSERT` in production. Production code that *requires* `uuid7` should assert at import time; library code that *prefers* `uuid7` and falls back to `uuid4` should feature-detect at runtime. The lesson's `hasattr` here is the second pattern.

### Lines 94–96: The unchanged model — type vs factory

```python
p = Project(name="alpha")
print(f"\nProject.id type: {type(p.id).__name__} (UUID either way)")
print(f"Project.id factory: uuid4 (default) — see migration rule below")
```

The model instance `p` is created without an explicit `id=`, so the dataclass calls the `default_factory=uuid.uuid4` and assigns a fresh v4. The type is still `UUID` — lesson 01's commitment survives. The factory is `uuid4` because that is the default this lesson's dataclass uses; the migration rule below commits the project to `uuid7` for *new* tables on 3.14+, while keeping `uuid4` for existing tables.

## Execution Trace

```bash
$ uv run python boardly/ids/uuid4_index_demo.py
--- 8 uuid4 values, raw insertion order ---
 1. int= 39762171245838760582140720650759274425  uuid=1de9ea66-70d3-4a1f-8735-df5ef7697fb9
 2. int=320727959146423810831530906581765649940  uuid=f149f542-e935-4870-9734-6b4501eaf614
 3. int= 11884758421083137989320289686624923345  uuid=08f0ebd4-950c-4dd9-8e97-b5bdf073eed1
 4. int= 33491286794524966119053879321868080530  uuid=19322fed-157c-49c6-b16e-2d5cabeb9592
 5. int=  5930457586169277751930561685632849974  uuid=04762a22-3c9f-40c9-9ac9-6628c4381836
 6. int=  5390216476892376724497546072421526880  uuid=040e1e30-c9ed-4248-bc97-99a707e36d60
 7. int=164780345928077942983130787383688644947  uuid=7bf78a4d-9f8f-4ffb-a5f8-0a0a58994953
 8. int= 31063428178024519248397156363360671997  uuid=175e9941-2607-4d5f-b6ab-14759da618fd

--- same 8 uuid4 values, sorted ascending by .int ---
 1. int=  5390216476892376724497546072421526880  uuid=040e1e30-c9ed-4248-bc97-99a707e36d60
 2. int=  5930457586169277751930561685632849974  uuid=04762a22-3c9f-40c9-9ac9-6628c4381836
 3. int= 11884758421083137989320289686624923345  uuid=08f0ebd4-950c-4dd9-8e97-b5bdf073eed1
 4. int= 31063428178024519248397156363360671997  uuid=175e9941-2607-4d5f-b6ab-14759da618fd
 5. int= 33491286794524966119053879321868080530  uuid=19322fed-157c-49c6-b16e-2d5cabeb9592
 6. int= 39762171245838760582140720650759274425  uuid=1de9ea66-70d3-4a1f-8735-df5ef7697fb9
 7. int=164780345928077942983130787383688644947  uuid=7bf78a4d-9f8f-4ffb-a5f8-0a0a58994953
 8. int=320727959146423810831530906581765649940  uuid=f149f542-e935-4870-9734-6b4501eaf614

--- insertion-position vs sorted-position (uuid4) ---
inserted at  6, sorted at  1
inserted at  5, sorted at  2
inserted at  3, sorted at  3
inserted at  8, sorted at  4
inserted at  4, sorted at  5
inserted at  1, sorted at  6
inserted at  7, sorted at  7
inserted at  2, sorted at  8

--- 8 sequential surrogate ints (autoincrement) ---
sorted(seq) == seq: True

--- uuid7 demo (Python 3.14+ only) ---
 1. uuid=01a1677f-b732-72ed-8752-8ac4b6a20bb0  version=7  variant=specified in RFC 4122
 2. uuid=01a1677f-b733-7d86-a032-85ed03be0e66  version=7  variant=specified in RFC 4122
 3. uuid=01a1677f-b734-77c9-bdc0-f27fe1668271  version=7  variant=specified in RFC 4122
 4. uuid=01a1677f-b735-73ff-aab4-509a10872756  version=7  variant=specified in RFC 4122
 5. uuid=01a1677f-b736-78a8-9dd1-4835e98d7c35  version=7  variant=specified in RFC 4122
 6. uuid=01a1677f-b737-7118-ab35-479999f9823c  version=7  variant=specified in RFC 4122
 7. uuid=01a1677f-b738-716c-a50e-614883d9fca7  version=7  variant=specified in RFC 4122
 8. uuid=01a1677f-b739-70bc-b4c2-ab5245038e22  version=7  variant=specified in RFC 4122
sorted(v7_batch) == v7_batch: True
(runtime: Python (3, 12, 15) — uuid.uuid7 not available,
 layout reconstructed for visualisation only)

Project.id type: UUID (UUID either way)
Project.id factory: uuid4 (default) — see migration rule below
```

The first three blocks (uuid4 dump, uuid4 sorted, insertion-vs-sorted) are deterministic and reproducible — they will print exactly the values above on every run, because the demo drives a seeded `random.Random(1234)`. The uuid7 block prints reconstructed values whose first 12 hex chars (`01a1677f-b732` through `01a1677f-b739`) encode the millisecond timestamp — strictly increasing across the 8 rows because the demo advances the millisecond clock every iteration (`base_ms = 1792737785650` is fixed for reproducibility; in production `uuid.uuid7()` reads `time.time_ns()` on every call). The `.version` field on every reconstructed UUID reads `7` — that is the standard library confirming the version bits are in the correct position in the integer (we did not pass `version=7` to the constructor; the bits were packed into the int directly). On Python 3.14+, replace `make_uuid7_batch` with `uuid.uuid7()` calls; the same `version=7` and `sorted == insertion` properties hold.

## Common Mistakes

### Mistake 1: Using `uuid4` for a high-write primary key

```python
@dataclass
class Event:
    id: uuid.UUID = field(default_factory=uuid.uuid4)   # ← 100M events later...
    payload: str = ""

# Six months later, the DBA files: "events table index is 1.8x bloat,
# insert latency 4x baseline, buffer pool miss rate 22%."
```

**Symptom:** the database's primary-key index on `id` fragments over time; insert latency grows super-linearly with row count; the buffer pool's hit rate degrades.

**Why:** `uuid4` produces uniformly random 128-bit values; a B-tree index stores rows in `.int` order; every insertion lands on a random leaf page; random leaf pages fragment and thrash.

**Fix (on Python 3.14+):**

```python
@dataclass
class Event:
    id: uuid.UUID = field(default_factory=uuid.uuid7)   # monotonic prefix
    payload: str = ""
```

**Fix (on Python 3.12):** Either keep `uuid4` and accept the index cost, or use a `BIGSERIAL` column (a 64-bit monotonic int from Postgres) and accept the int-identifier trade-offs (enumerable, shard-coordination cost, merge-unsafe). On 3.12, there is no `uuid7`; the trade-off is real.

### Mistake 2: Migrating an existing `uuid4` table to `uuid7`

```python
# boardly/migrations/bad_uuid7_migration.py — wrong
# "Let's just change the factory and re-INSERT every row."
def migrate_projects_to_uuid7(session):
    for p in session.query(Project):
        p.id = uuid.uuid7()              # ← changes the primary key
        session.add(p)
    session.commit()
# Every foreign key referencing project.id is now dangling.
# Every cached URL with the old uuid4 is broken.
# Every log line correlating to the old id is orphaned.
```

**Symptom:** every foreign-key reference to `project.id` becomes a dangling row; every cached URL (`/projects/<uuid>/`) returns 404; every correlation log breaks.

**Why:** primary keys are *referenced*. Changing the value of a primary key invalidates every reference to it. The `uuid7` migration story is *new tables use uuid7*; existing tables keep `uuid4` forever (or until they are decommissioned and rebuilt).

**Fix:** Do not migrate. New tables (created after the deploy that adds `uuid7` support) use `uuid.uuid7()` as their default factory; existing tables keep `uuid.uuid4()`. The two coexist; the application code routes through the table's known factory; the database layer accepts both as `UUID` (the type is unchanged — lesson 01's commitment holds).

### Mistake 3: Version-gating at runtime when you should fail at import

```python
# boardly/ids/lazy_version_gate.py — wrong
def new_project_id() -> uuid.UUID:
    if hasattr(uuid, "uuid7"):
        return uuid.uuid7()
    return uuid.uuid4()              # ← silently degrades to the random factory
```

**Symptom:** in production on 3.14+, the primary keys are `uuid7` and the index is healthy. In a notebook or a Lambda on 3.12, the same code silently generates `uuid4` primary keys — which fragment the index the team explicitly chose `uuid7` to avoid. Nobody notices until the index bloat ticket comes in.

**Why:** `hasattr` is the *library* pattern (where you legitimately fall back). An *application* that *requires* `uuid7` for index health should fail at import time, on the wrong runtime, before any row is inserted.

**Fix:**

```python
# boardly/ids/project_id.py — right
import sys
import uuid

assert sys.version_info >= (3, 14), "Project.id requires uuid.uuid7 (Python 3.14+)"

def new_project_id() -> uuid.UUID:
    return uuid.uuid7()
```

The `assert` raises `AssertionError` at import time on 3.12 — CI catches it on the first run, before any row is written to the table. Reserve `hasattr`-based fallback for library code that supports both; use `sys.version_info` asserts for application code that requires the new factory.

## Engineering Trade-Offs

**Decision:** New `boardly` tables on Python 3.14+ use `uuid.uuid7()` for primary keys. Existing tables keep `uuid.uuid4()`. Opaque IDs (request IDs, correlation tokens) keep `uuid.uuid4()` on every runtime.

**Both sides:** The alternative — `uuid4` everywhere — wins in three narrow cases: (1) a system with so few rows per table (under a few hundred thousand) that the index never reaches the fragmentation threshold; (2) a system whose indexes are rebuilt frequently enough (a nightly `REINDEX`) that fragmentation is amortised; (3) a system whose consumers explicitly *want* the random-order property (a random-sample table, a hash-sharded dataset). The `uuid7` choice wins in every other case — index locality, write-amplification reduction, cache locality, debuggability (the timestamp in the prefix tells you when the row was inserted). The cost is a runtime dependency on Python 3.14+ and a bit of conceptual complexity (the student has to internalise "the type is UUID; the factory is a separate choice").

**Commitment:** boardly commits to: (a) `Project.id` and `Ticket.public_id` stay `uuid.UUID` on the dataclass — the type is the lesson 01 commitment, unchanged; (b) *new* tables created after the 3.14 deploy use `uuid.uuid7()` as the `default_factory`; (c) *existing* tables keep `uuid.uuid4()` and are never migrated — primary-key migration is a destructive operation; (d) opaque IDs (request IDs in the log correlation middleware) keep `uuid.uuid4()` on every runtime, because the timestamp prefix on `uuid7` would leak timing information that an attacker could use to fingerprint the service. Cross-link to [[06-dataclasses/01-dataclass-Basics]] for the `id: UUID = field(default_factory=...)` field pattern that both factories share.

## Exercises

1. **Exercise 1 — Run the demo and verify the scatter.** Run `boardly/ids/uuid4_index_demo.py` and verify the insertion-position-vs-sorted-position table prints six rows where X != Y. Modify the seed (`random.Random(42)` instead of `1234`) and re-run; the values change but the property (most rows out of order) does not. `Verify: uv run python boardly/ids/uuid4_index_demo.py | grep -c "sorted at"` should print `8`.
2. **Exercise 2 — Demonstrate the within-millisecond property of uuid7's layout.** In the `make_uuid7_batch` helper, change `ms = base_ms + i` to `ms = base_ms` so every UUID gets the *same* millisecond timestamp. Re-run; verify `sorted(v7_batch) == v7_batch` is now `False` — within a millisecond, the 74 random bits determine the order, and the order is random. This is the *within-millisecond* behaviour; in production, `uuid.uuid7()` reads the wall-clock time on every call, so calls that fit in the same millisecond share a prefix (and land on the same B-tree leaf page — still a locality win over `uuid4`), but are not strictly ordered between themselves. `Verify: uv run python boardly/ids/uuid4_index_demo.py | grep sorted` — should print `sorted(v7_batch) == v7_batch: False`.
3. **Exercise 3 — Add a `uuid7` factory path to the `Project` dataclass.** Write a `new_project_id()` function that asserts `sys.version_info >= (3, 14)` and returns `uuid.uuid7()`. Change `Project.id`'s `default_factory` to `new_project_id`. Verify that on 3.12 the import fails with `AssertionError`, and on 3.14+ the import succeeds and `Project()` instances get v7 IDs. `Verify: uv run python -c "import boardly.ids.project"` should raise `AssertionError` on 3.12.
4. **Exercise 4 — Measure the index-locality gap.** Write a script that generates 10 000 `uuid4` values, sorts them, and counts how many pairs of consecutive values (in insertion order) are also consecutive in sorted order. Do the same for `make_uuid4_batch` with a `+ i // 100` timestamp-prefix simulation (mimicking `uuid7`). The fraction should be roughly `1/10000` for `uuid4` and roughly `1` for the timestamp-prefix variant. `Verify: uv run python boardly/ids/locality_measure.py` should print two fractions.
5. **Exercise 5 — Document the migration rule for your team.** Write a one-page `boardly/migrations/UUID_POLICY.md` that states: (1) new tables on Python 3.14+ use `uuid.uuid7()` for primary keys; (2) existing tables keep `uuid.uuid4()` and are never migrated; (3) opaque IDs (request IDs, correlation tokens) keep `uuid.uuid4()` on every runtime, because the `uuid7` timestamp prefix leaks timing information. This exercise has no `Verify:` block — the deliverable is the doc.

## Verification

```bash
$ uv run python boardly/ids/uuid4_index_demo.py 2>&1 | tail -8
--- uuid7 demo (Python 3.14+ only) ---
 1. uuid=01a1677f-b732-72ed-8752-8ac4b6a20bb0  version=7  variant=specified in RFC 4122
 2. uuid=01a1677f-b733-7d86-a032-85ed03be0e66  version=7  variant=specified in RFC 4122
 3. uuid=01a1677f-b734-77c9-bdc0-f27fe1668271  version=7  variant=specified in RFC 4122
 4. uuid=01a1677f-b735-73ff-aab4-509a10872756  version=7  variant=specified in RFC 4122
 5. uuid=01a1677f-b736-78a8-9dd1-4835e98d7c35  version=7  variant=specified in RFC 4122
 6. uuid=01a1677f-b737-7118-ab35-479999f9823c  version=7  variant=specified in RFC 4122
 7. uuid=01a1677f-b738-716c-a50e-614883d9fca7  version=7  variant=specified in RFC 4122
 8. uuid=01a1677f-b739-70bc-b4c2-ab5245038e22  version=7  variant=specified in RFC 4122
sorted(v7_batch) == v7_batch: True
(runtime: Python (3, 12, 15) — uuid.uuid7 not available,
 layout reconstructed for visualisation only)
```

The `version=7` field on every reconstructed UUID verifies the bit packing is correct — the standard library reads the version from the integer's high bits (positions 48–51, the 13th hex char of the dashed form), and `0x7` there is the RFC 9562 §5.7 marker. The lesson's helper passes only `int=v7_int` to the constructor (not `version=7` as a kwarg) because 3.12's `UUID(...)` ctor rejects versions > 5; the version bits in the int are still correct, so `.version` reads `7`. On Python 3.14+, replace `make_uuid7_batch` with `uuid.uuid7()` calls; the same `version=7` and `sorted == insertion` properties hold.

## Previously Learned Here

- [[16-uuid/01-UUID-variants]] — the canonical lesson for the `UUID` type and the eight RFC 9562 variants. Lesson 01 committed the *type* (`id: UUID`); this lesson committed the *factory* (`uuid.uuid7()` on 3.14+ for primary keys, `uuid.uuid4()` for opaque IDs and on older runtimes). Referenced from this lesson's "version= kwarg" block and the `default_factory` discussion.

## What's Next

[[17-decimal/00-decimal-MOC]] — the closest sibling section in the vault. `UUID` and `Decimal` are the two "never use the primitive type" lessons in the stdlib: never use `str` for an identifier (use `UUID`), never use `float` for money (use `Decimal`). The two MOCs are designed to be read as a pair so the rule lands twice, and the next section (17-decimal) gives you the *exact* shape of the same commitment applied to money — `Decimal("0.10")` instead of `0.1`, `id: UUID` instead of `id: str`. The pattern is the same: pick the type that matches the value's structure, convert at the boundary, never let the primitive form survive past the parse.

- The decimal lesson pair — `Decimal` for money, `UUID` for identifiers; both are "never use the primitive" rules.
- The float-bug twin of the str-id bug — `Decimal(0.1)` captures the float's binary approximation the same way `id: str` accepts `"banana"`; both fail silently at the boundary.
- The boundary-conversion pattern — `uuid.UUID(body["id"])` at the request parser is the twin of `Decimal(body["price"])` at the request parser; both are "convert at the edge, store the type, never let the primitive in".

## Sources

- **`uuid` — UUID objects and generators** — https://docs.python.org/3/library/uuid.html — accessed 2026-10-23 — the canonical CPython reference. Documents `uuid.uuid4()` (the random factory), the `version=4` marker bits, and the `UUID(int=..., version=...)` constructor form used in the lesson's visualisation helper.
- **RFC 9562 — Universally Unique IDentifiers (UUIDs)** — https://www.rfc-editor.org/rfc/rfc9562.html — accessed 2026-10-23 — §5.7 defines the uuid7 layout (48-bit millisecond timestamp + 4-bit version + 12-bit `rand_a` + 2-bit variant + 62-bit `rand_b`). Source for the bit-packing in `make_uuid7_batch` and the monotonic-prefix claim.
- **What's New in Python 3.14 — `uuid`** — https://docs.python.org/3.14/whatsnew/3.14.html — accessed 2026-10-23 — confirms `uuid.uuid7` was added in Python 3.14 (does not exist in 3.12 or 3.13). Source for the version-gate language throughout this lesson.
- **PostgreSQL — `uuid` data type** — https://www.postgresql.org/docs/current/datatype-uuid.html — accessed 2026-10-23 — documents the 16-byte native `uuid` column type and the B-tree index behaviour that motivates the page-fragmentation argument in this lesson's Problem section.

## What We Learned

- You can now explain why `uuid4` hurts a B-tree primary-key index — name the three failure modes (page fragmentation, write amplification, cache-miss locality) and explain how each follows from the uniform-random bit layout.
- You can describe the `uuid7` layout (48-bit millisecond timestamp + 4-bit version + 12-bit `rand_a` + 2-bit variant + 62-bit `rand_b`) and explain why the timestamp prefix produces monotonically increasing values within and across millisecond buckets.
- You can version-gate `uuid7` correctly: `hasattr(uuid, "uuid7")` for runtime feature detection (library code), `sys.version_info >= (3, 14)` for import-time fail-fast (application code that requires the factory).
- You can state the migration rule: new tables use `uuid.uuid7()` on 3.14+ for primary keys; existing tables keep `uuid.uuid4()` and are never migrated; opaque IDs (request IDs, correlation tokens) keep `uuid.uuid4()` on every runtime because the `uuid7` timestamp prefix leaks timing information.
- You can distinguish "opaque ID" (`uuid4`, no ordering, no metadata) from "ordered ID" (`uuid7`, monotonic prefix, debuggable timestamp) and pick the right factory for each context.
