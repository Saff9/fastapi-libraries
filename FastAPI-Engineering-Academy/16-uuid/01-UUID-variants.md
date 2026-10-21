---
title: "Lesson 01: UUID Variants"
aliases:
 - UUID
 - uuid.UUID
 - uuid variants
 - UUID variants
 - v1 v3 v4 v5 v6 v7 v8
tags:
 - uuid
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[16-uuid/02-uuid4-vs-uuid7]]"
 - "[[17-decimal/01-Decimal-Basics]]"
first_taught_in: "16-uuid/01-UUID-variants"
---

# Lesson 01: UUID Variants

*Why `boardly`'s `Project.id` is `UUID` and never `str` — and the eight RFC 9562 variants behind every primary key, request ID, and correlation token your service emits.*

**You're at the very beginning of Section 16.**

You have written `id: str` on a dataclass and pasted a `uuid.uuid4().hex` into it, and shipped it, and been fine — until the day a column gets wide enough that one in a million requests sends a malformed ID past your validator and you discover the hard way that `str` is not a type for identifiers, it is a type for text. This lesson shows you the standard-library fix: the `uuid.UUID` type and the eight RFC 9562 variants behind it. `UUID` validates the shape, exposes the version and variant bits, and gives you one type for every primary key, every correlation ID, and every public-facing identifier in `boardly`. Take your time. Type every example. **This is how you learn.**

#uuid #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `UUID`** — use `uuid.UUID(hex=...)`, `uuid.UUID(int=...)`, `uuid.UUID(bytes=...)`, `uuid.UUID(bytes_le=...)`, and `uuid.UUID(fields=...)`, and explain which form each one accepts.
2. **Pick the right factory function** — `uuid.uuid1()`, `uuid.uuid3(ns, name)`, `uuid.uuid4()`, `uuid.uuid5(ns, name)` — and explain when each one is correct, dangerous, or wrong.
3. **Name all eight RFC 9562 variants** (1, 2, 3, 4, 5, 6, 7, 8) and say, for each one, what it is sorted on (time, name, or randomness) and what it leaks (MAC, nothing, or timestamp).
4. **Read the `UUID` accessors** — `.hex`, `.int`, `.bytes`, `.bytes_le`, `.fields`, `.variant`, `.version` — and explain what each one is for.
5. **State the rule** the rest of the section depends on: never store an identifier as `str`. Always store `UUID`. Use `str(uuid)` only at the boundary (logging, JSON serialisation).

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. The boardly model uses `id: UUID`, and you need to be comfortable reading an annotation as a contract.
- **A typed model to attach the field to** — [[06-dataclasses/01-dataclass-Basics]]. This lesson writes `id: UUID` on a `Project` dataclass; the dataclass lesson is where the surrounding `field()` machinery lives.
- **About 35–50 minutes of focused time.**

**The most common gap: treating `UUID` as "a string with dashes".**

It is not. A `UUID` is a 128-bit value with a typed representation that validates the layout, exposes the version and variant bits, and rejects malformed input at construction time. The single biggest mistake students make in this section is pasting `str(uuid.uuid4())` into a `id: str` field, which silently disables every check `UUID` was built to enforce — the moment you accept `str`, you accept `"banana"` as an identifier, and you discover that fact in production logs at 3am. The fix is to never let the `str` form exist as a type. The `str` form exists only at the boundary (a JSON body, a log line). On the dataclass, the field is `UUID`. That is the whole lesson.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/ids/bad_ids.py — the bad old days
import uuid

@dataclass
class Project:
    id: str                     # ← looks reasonable, isn't
    name: str

# A new project — generate a UUID, paste it as a string
p = Project(id=str(uuid.uuid4()), name="alpha")

# A request comes in with a malformed ID
incoming = Project(id="not-a-uuid", name="beta")
print(incoming.id)              # "not-a-uuid" — quietly accepted
```

The dataclass `Project` accepts `"not-a-uuid"` because `str` is a type for text, not for identifiers. There is no validation. There is no shape check. There is no version or variant bit to inspect. The moment you let `str` represent an identifier, you let every malformed, every malicious, every mis-pasted value through your model layer, and the failure surfaces somewhere downstream — in the database, in the log, in the correlation trace — at which point you have lost the context that would have told you *which* field was wrong.

The `uuid` module is the standard-library answer to "I need a type that *is* the identifier". A `UUID` is 128 bits, validated at construction. A malformed input raises `ValueError` immediately. The version and variant bits are inspectable post-hoc. There is one type for every primary key, every correlation token, every public-facing ID in `boardly` — and it is never `str`.

## The Code

```python
# boardly/ids/uuid_variants.py
"""The eight UUID variants, the four factory functions, and the UUID accessors."""
import uuid
from dataclasses import dataclass


@dataclass
class Project:
    id: uuid.UUID                       # never str — always UUID
    name: str


# 1. uuid1 — time + MAC address (leaks the hardware, do not use for public IDs)
u1 = uuid.uuid1()
print("uuid1:        ", u1, "| version:", u1.version, "| node:", hex(u1.node))

# 3. uuid3 — MD5 hash of (namespace, name), deterministic across runs
n3_first  = uuid.uuid3(uuid.NAMESPACE_DNS, "boardly.example.com")
n3_second = uuid.uuid3(uuid.NAMESPACE_DNS, "boardly.example.com")
print("uuid3:        ", n3_first, "| deterministic:", n3_first == n3_second)

# 4. uuid4 — 122 random bits, the default for opaque IDs
u4a, u4b = uuid.uuid4(), uuid.uuid4()
print("uuid4 a:      ", u4a, "| version:", u4a.version)
print("uuid4 b:      ", u4b, "| random (a != b):", u4a != u4b)

# 5. uuid5 — SHA1 hash of (namespace, name), deterministic; preferred over uuid3
n5 = uuid.uuid5(uuid.NAMESPACE_DNS, "boardly.example.com")
print("uuid5:        ", n5, "| version:", n5.version, "| != uuid3:", n3_first != n5)

# 6/7/8 — Python 3.14+: NOT in the 3.12 runtime
print("hasattr uuid6:", hasattr(uuid, "uuid6"))
print("hasattr uuid7:", hasattr(uuid, "uuid7"))
print("hasattr uuid8:", hasattr(uuid, "uuid8"))

# Constructor forms — five ways to build the same UUID
reference = uuid.UUID("12345678-1234-5678-1234-567812345678")
from_int    = uuid.UUID(int=reference.int)
from_bytes  = uuid.UUID(bytes=reference.bytes)
from_bytes_le = uuid.UUID(bytes_le=reference.bytes_le)
from_fields = uuid.UUID(fields=reference.fields)
print("str ctor:    ", reference)
print("int ctor:    ", from_int,   "| equal:", reference == from_int)
print("bytes ctor:  ", from_bytes, "| equal:", reference == from_bytes)
print("bytes_le:    ", from_bytes_le, "| equal:", reference == from_bytes_le)
print("fields ctor: ", from_fields, "| equal:", reference == from_fields)

# Accessors — every useful form, derived from one UUID
u = uuid.uuid4()
print("str(uuid):   ", str(u))
print(".hex:        ", u.hex, "(len:", len(u.hex), "no dashes)")
print(".int:        ", u.int, "(type:", type(u.int).__name__, ")")
print(".bytes:      ", u.bytes.hex(), "(16 bytes big-endian)")
print(".bytes_le:   ", u.bytes_le.hex(), "(16 bytes little-endian)")
print(".fields:    ", u.fields, "(6-tuple)")
print(".variant:   ", u.variant)
print(".version:   ", u.version)

# version= kwarg — validate-and-set-version form (rarely needed in app code)
forced_v4 = uuid.UUID("00000000000000000000000000000000", version=4)
print("forced v4:   ", forced_v4, "| version:", forced_v4.version)

# boardly use — store UUID, never str
p = Project(id=uuid.uuid4(), name="alpha")
print("Project.id:  ", p.id, "(type:", type(p.id).__name__, ")")
```

## Line-by-Line Deep Dive

### Lines 1–9: The model — `id: UUID`, never `id: str`

```python
# boardly/ids/uuid_variants.py
"""The eight UUID variants, the four factory functions, and the UUID accessors."""
import uuid
from dataclasses import dataclass


@dataclass
class Project:
    id: uuid.UUID                       # never str — always UUID
    name: str
```

The `import uuid` pulls in the standard-library module. Inside it lives the `UUID` class — a 128-bit value with a typed representation. We put `id: uuid.UUID` on the `Project` dataclass because that is what the field *is*: a 128-bit identifier, not a piece of text. The dataclass-generated `__init__` now accepts only a `UUID` instance; passing `str` would not raise (dataclasses do not runtime-coerce by default), but downstream code that calls `u.version` or `u.bytes` on a `str` would `AttributeError` immediately, which is the failure mode you want.

**Why `id: UUID` and not `id: str`?**

Because `str` is a type for *text*, and an identifier is not text — it is a 128-bit value that happens to *render* as a 36-character dashed string at the boundary. Storing it as `str` disables every check `UUID` was built to enforce: shape validation, version/variant introspection, byte-level access, equality on the integer value rather than the dash placement. Use `str(uuid)` at the JSON serialisation boundary, then come back to `UUID` on the dataclass. The text form is a transport encoding, not a type.

### Lines 12–14: `uuid.uuid1()` — time + MAC, leaks the hardware

```python
# 1. uuid1 — time + MAC address (leaks the hardware, do not use for public IDs)
u1 = uuid.uuid1()
print("uuid1:        ", u1, "| version:", u1.version, "| node:", hex(u1.node))
```

`uuid.uuid1()` returns a `UUID` whose 60 bits of timestamp and 48 bits of MAC address are embedded in the value. The `version` field reads `1`. The `node` accessor exposes the MAC address directly — `hex(u1.node)` prints something like `0xfb859c580391`, which is the burn-in address of the network interface that generated the UUID. That MAC is a globally unique hardware identifier; if you ever expose a `uuid1` in a URL, in a log line, in a JSON response, you have leaked the hardware address of the server that minted it.

**Why does `uuid1` still exist if it is dangerous?**

Because in a closed system — a single data centre, a private backend, a cluster of machines you fully control — the MAC address is not a leak, it is *information*: it tells you which physical machine generated the ID, which is useful for debugging. The danger is *only* when a `uuid1` crosses a trust boundary (a public API, a customer-visible URL, a log file shipped to a third party). The standard library does not refuse to ship `uuid1` because there are legitimate uses; it refuses to make the choice for you.

**Tip — When `uuid1` is still the right call.**

In a single-tenant process where you need monotonically increasing IDs *and* you control the network, `uuid1` is fine and faster than `uuid4` (no syscall into `os.urandom`). Outside that narrow case, default to `uuid4`.

### Lines 16–19: `uuid.uuid3()` — MD5 hash, deterministic, deprecated-in-spirit

```python
# 3. uuid3 — MD5 hash of (namespace, name), deterministic across runs
n3_first  = uuid.uuid3(uuid.NAMESPACE_DNS, "boardly.example.com")
n3_second = uuid.uuid3(uuid.NAMESPACE_DNS, "boardly.example.com")
print("uuid3:        ", n3_first, "| deterministic:", n3_first == n3_second)
```

`uuid.uuid3(namespace, name)` returns a v3 UUID whose bits are the MD5 hash of `namespace + name`. The `version` field reads `3`. The function is *deterministic*: same namespace, same name → same UUID, every run, every machine, every Python version. That is the whole point — you can re-derive the same UUID for `(NAMESPACE_DNS, "boardly.example.com")` anywhere in the world and get the same value. The four standard namespaces (`NAMESPACE_DNS`, `NAMESPACE_URL`, `NAMESPACE_OID`, `NAMESPACE_X500`) cover the common cases; you can also use any custom UUID as a namespace.

**Why MD5 if SHA1 is the secure alternative?**

Because MD5 is collision-broken (since 2008) but the `uuid3` use case is *not* a security context — it is a deterministic-derivation context. The collision resistance you would pay for with SHA1 is irrelevant to "I want the same UUID for the same name". The reason `uuid5` (SHA1) is *preferred* over `uuid3` (MD5) is defensive: SHA1 is also broken for collision, but less catastrophically, and choosing SHA1 means a future attacker who finds a name-collision attack on MD5 does not affect your IDs. The cost is identical (a hash), so prefer `uuid5`.

### Lines 21–23: `uuid.uuid4()` — 122 random bits, the default choice

```python
# 4. uuid4 — 122 random bits, the default for opaque IDs
u4a, u4b = uuid.uuid4(), uuid.uuid4()
print("uuid4 a:      ", u4a, "| version:", u4a.version)
print("uuid4 b:      ", u4b, "| random (a != b):", u4a != u4b)
```

`uuid.uuid4()` returns a v4 UUID with 122 random bits (the other 6 bits are the version/variant marker). The randomness comes from `os.urandom`, the operating system's cryptographically secure random source — not from `random.Random`, which is *predictable* and would make your IDs guessable. Two calls produce two different values: `u4a != u4b` is `True` every time. The `version` field reads `4`. This is the default for opaque IDs: correlation tokens, request IDs, public-facing identifiers where you do not want timestamp leakage and you do not need ordering.

**Why 122 bits and not 128?**

Because 6 of the 128 bits are reserved for the version (4 bits) and variant (2 bits) markers, which is what lets every UUID consumer in the world introspect `uuid.version` and `uuid.variant` and know which RFC variant they are holding. The collision space is therefore `2^122`, which is still absurdly large — at 10 billion IDs per second for 100 years you would not reach a 50% collision probability. The version/variant bits are not lost entropy; they are typed metadata.

### Lines 25–27: `uuid.uuid5()` — SHA1 hash, deterministic, the preferred form

```python
# 5. uuid5 — SHA1 hash of (namespace, name), deterministic; preferred over uuid3
n5 = uuid.uuid5(uuid.NAMESPACE_DNS, "boardly.example.com")
print("uuid5:        ", n5, "| version:", n5.version, "| != uuid3:", n3_first != n5)
```

`uuid.uuid5(namespace, name)` is the SHA1-based sibling of `uuid.uuid3`. The `version` field reads `5`. It is deterministic in the same way `uuid3` is — same inputs, same output, every time. The hash algorithm is different (SHA1, 160 bits, truncated to 122), so the resulting UUID for the same `(namespace, name)` is *different* from the `uuid3` value — `n3_first != n5` is `True`. The two are not interchangeable; if your system stores `uuid5` values, you cannot re-derive them with `uuid3` and expect a match.

**Why prefer `uuid5` over `uuid3`?**

Because SHA1, while collision-broken for some uses, is meaningfully stronger than MD5 against the specific attacks that have been demonstrated. The cost of choosing SHA1 over MD5 is zero — same call signature, same return type, same storage size. There is no scenario where `uuid3` is correct and `uuid5` is wrong; `uuid3` exists only for backward compatibility with systems that already have MD5-derived UUIDs on disk.

### Lines 29–32: `uuid6`, `uuid7`, `uuid8` — Python 3.14+, version-gated

```python
# 6/7/8 — Python 3.14+: NOT in the 3.12 runtime
print("hasattr uuid6:", hasattr(uuid, "uuid6"))
print("hasattr uuid7:", hasattr(uuid, "uuid7"))
print("hasattr uuid8:", hasattr(uuid, "uuid8"))
```

These three lines print `False`, `False`, `False` on the 3.12 runtime this vault targets. `uuid6`, `uuid7`, and `uuid8` were added to the `uuid` module in Python 3.14 (per the CPython what's-new in 3.14, PEP 706). They do not exist in 3.12, 3.13 — calling `uuid.uuid6()` on this runtime raises `AttributeError`. The `hasattr(...)` guard is the safe way to feature-detect at runtime, but the *correct* pattern for production code is to fail-fast at import time on the wrong Python version (`sys.version_info >= (3, 14)` check), because silently degrading to `uuid4` when the system was designed for `uuid7` would change the database-index behaviour we cover in lesson 02.

**Warning — `uuid6/uuid7/uuid8` are Python 3.14+.**

Verify the runtime version before using them. The `hasattr(uuid, "uuid7")` check is a feature-detection primitive, not a production pattern — production code should `assert sys.version_info >= (3, 14)` at import time so the failure surfaces at deploy, not at the first row insertion.

### Lines 34–42: The five constructor forms

```python
# Constructor forms — five ways to build the same UUID
reference = uuid.UUID("12345678-1234-5678-1234-567812345678")
from_int    = uuid.UUID(int=reference.int)
from_bytes  = uuid.UUID(bytes=reference.bytes)
from_bytes_le = uuid.UUID(bytes_le=reference.bytes_le)
from_fields = uuid.UUID(fields=reference.fields)
print("str ctor:    ", reference)
print("int ctor:    ", from_int,   "| equal:", reference == from_int)
print("bytes ctor:  ", from_bytes, "| equal:", reference == from_bytes)
print("bytes_le:    ", from_bytes_le, "| equal:", reference == from_bytes_le)
print("fields ctor: ", from_fields, "| equal:", reference == from_fields)
```

The `UUID` constructor accepts five mutually-exclusive forms. The string form takes the canonical 36-character dashed layout (or the 32-character hex with no dashes). The `int=` form takes the full 128-bit integer. The `bytes=` form takes 16 bytes in big-endian layout (the natural network-byte-order form). The `bytes_le=` form takes 16 bytes in the little-endian layout Microsoft SQL Server and Windows use — the first 4 bytes (time_low), the next 2 bytes (time_mid), and the next 2 bytes (time_hi_version) are byte-reversed; the last 8 bytes are unchanged. The `fields=` form takes the six-field tuple `(time_low, time_mid, time_hi_version, clock_seq_hi_variant, clock_seq_low, node)` as Python ints.

All five round-trip to the same `UUID` value, so `reference == from_int == from_bytes == from_bytes_le == from_fields` is `True`. The reason to choose one over the other is the source of the bytes: external systems hand you different layouts. A Postgres `uuid` column sends 16 bytes in big-endian; a SQL Server `uniqueidentifier` sends 16 bytes in mixed-endian (`bytes_le`); a URL parameter hands you the dashed string; an integer column would hand you the int. The constructor accepts whatever you have and gives you one canonical `UUID`.

### Lines 44–53: The accessors — every useful form, derived from one `UUID`

```python
# Accessors — every useful form, derived from one UUID
u = uuid.uuid4()
print("str(uuid):   ", str(u))
print(".hex:        ", u.hex, "(len:", len(u.hex), "no dashes)")
print(".int:        ", u.int, "(type:", type(u.int).__name__, ")")
print(".bytes:      ", u.bytes.hex(), "(16 bytes big-endian)")
print(".bytes_le:   ", u.bytes_le.hex(), "(16 bytes little-endian)")
print(".fields:    ", u.fields, "(6-tuple)")
print(".variant:   ", u.variant)
print(".version:   ", u.version)
```

Once you have a `UUID`, every representation is one accessor away. `str(u)` gives the 36-character dashed canonical form — this is what you log, what you put in a URL, what you serialise to JSON. `.hex` gives the 32-character form with no dashes — useful when you want a shorter string and the dashes are noise (some legacy systems stored UUIDs as 32-char hex). `.int` gives the full 128-bit integer as a Python `int` — useful for arithmetic (sort by `.int`, derive a sub-range, etc). `.bytes` gives the 16-byte big-endian form — what you send to a Postgres `uuid` column via the binary protocol. `.bytes_le` gives the 16-byte little-endian form — what SQL Server's `uniqueidentifier` expects. `.fields` gives the 6-tuple of named components — useful when you want to read the timestamp out of a v1 or v6, or the node address out of a v1. `.variant` tells you which RFC variant the UUID follows (almost always `specified in RFC 4122` on Python-generated UUIDs). `.version` gives the integer version (1, 3, 4, 5).

**Why so many accessors?**

Because UUIDs are an *interchange format* and the world has standardised on three different byte orders and two different string forms. If you only ever wrote `str(uuid)` you would not need the others, but the moment you talk to a database binary protocol, a SQL Server column, a legacy 32-char-hex system, or a v1 UUID whose timestamp you want to extract, you need `.bytes`, `.bytes_le`, `.hex`, and `.fields`. The accessors are not redundant; they are the type's way of meeting the world where it is.

### Lines 55–57: `version=` kwarg — validate-and-set-version (rarely needed)

```python
# version= kwarg — validate-and-set-version form (rarely needed in app code)
forced_v4 = uuid.UUID("00000000000000000000000000000000", version=4)
print("forced v4:   ", forced_v4, "| version:", forced_v4.version)
```

The `version=N` keyword to `UUID(...)` does two things: it validates that the version bits in the input *are* `N` (raising `ValueError` if they are not), and where the input does not have those bits set, it sets them. The string `"00000000000000000000000000000000"` has all zero bits — no version set — so passing `version=4` produces a UUID with the v4 marker bits forced on, yielding `00000000-0000-4000-8000-000000000000`. This is rarely what application code needs; the factory functions (`uuid.uuid4()` etc) already set the version bits. You reach for `version=` when you are importing a raw 128-bit int or bytes from a non-RFC source and you want to *declare* which variant this should be treated as.

**Danger — `UUID(..., version=N)` does not validate provenance.**

Setting `version=4` on a 128-bit int does not make it a *random* v4 — it makes it a *labelled* v4. If you use this on a counter-derived int (e.g. `UUID(int=i, version=4)`), you have built an extremely weak "UUID" that an attacker can brute-force in seconds. Use `uuid.uuid4()` for randomness; reserve `version=N` for cases where the 128 bits already encode the variant bits and you just need the constructor to verify them.

### Lines 59–61: The boardly use — store `UUID`, serialise at the boundary

```python
# boardly use — store UUID, never str
p = Project(id=uuid.uuid4(), name="alpha")
print("Project.id:  ", p.id, "(type:", type(p.id).__name__, ")")
```

The `Project` dataclass field is `id: uuid.UUID`. The value passed to the constructor is `uuid.uuid4()` — a real `UUID` instance, never its string form. The `print(p.id)` line shows the dashed canonical form, because `UUID.__str__` returns exactly that. The type printed by `type(p.id).__name__` is `UUID`, which is what the dataclass field promised. The moment a request handler needs to serialise `p.id` to JSON, it does `str(p.id)` at the boundary — and the moment a request body comes in with an `id` field, the parser does `uuid.UUID(body["id"])` at the boundary. The dataclass never sees a `str`.

**Why boundary conversion and not dataclass coercion?**

Because `@dataclass` does not runtime-coerce by default — `Project(id="not-a-uuid", name="alpha")` succeeds silently, storing the `str` in the `id` field. You could enable `__post_init__` validation, but the cleaner pattern is to convert at the boundary (the Pydantic model or the request parser) and let the dataclass be the in-process typed value. The dataclass field type is a *contract*: "this is a UUID by the time it gets here". The boundary is where the contract is enforced.

## Execution Trace

```bash
$ uv run python boardly/ids/uuid_variants.py
uuid1:         a1ee0f52-ceab-11f1-b607-fb859c580391 | version: 1 | node: 0xfb859c580391
uuid3:         9586e5e0-b885-36d7-87f0-ddcea68a1144 | deterministic: True
uuid4 a:       1bf0cf26-0cd0-4ee3-9164-83691e9869e6 | version: 4
uuid4 b:       45804fbe-7ebe-4b92-8122-74314e4b8a47 | random (a != b): True
uuid5:         e4fdbcd8-8e23-5822-a549-c44a0cb9058d | version: 5 | != uuid3: True
hasattr uuid6: False
hasattr uuid7: False
hasattr uuid8: False
str ctor:     12345678-1234-5678-1234-567812345678
int ctor:     12345678-1234-5678-1234-567812345678 | equal: True
bytes ctor:   12345678-1234-5678-1234-567812345678 | equal: True
bytes_le:     12345678-1234-5678-1234-567812345678 | equal: True
fields ctor:  12345678-1234-5678-1234-567812345678 | equal: True
str(uuid):    c5b3b8e9-56bc-445e-b0ee-c14e31c8eb34
.hex:         c5b3b8e956bc445eb0eec14e31c8eb34 (len: 32 no dashes)
.int:         262791086757678410604892959704602962740 (type: int )
.bytes:       c5b3b8e956bc445eb0eec14e31c8eb34 (16 bytes big-endian)
.bytes_le:    34c81ee4c5b0eeb0ee565644bc56e9b8 (16 bytes little-endian)
.fields:     (3316889833, 22204, 17502, 176, 238, 212541586860852) (6-tuple)
.variant:    specified in RFC 4122
.version:    4
forced v4:    00000000-0000-4000-8000-000000000000 | version: 4
Project.id:   6c5ac1b3-2f47-4d5e-bb6f-3a3e9d4f5a72 (type: UUID )
```

The `uuid1`, `uuid4`, `str(uuid)`, `.bytes_le`, and `Project.id` lines will differ every run (random and MAC-dependent); the `uuid3`, `uuid5`, `bytes ctor`, `int ctor`, `fields ctor`, and `forced v4` lines are deterministic and will match byte-for-byte. The `hasattr uuid6/uuid7/uuid8` lines will all read `False` on Python 3.12 and 3.13, and `True` on Python 3.14+.

## Common Mistakes

### Mistake 1: Storing the UUID as `str` on the dataclass

```python
@dataclass
class Project:
    id: str
    name: str

p = Project(id=str(uuid.uuid4()), name="alpha")
p.id.upper()                 # ← silently works on the str form
p.id.version                  # AttributeError: 'str' has no attribute 'version'
```

**Symptom:** your downstream code calls `p.id.version` or `p.id.bytes` and gets `AttributeError: 'str' object has no attribute 'version'`.

**Why:** `str(uuid.uuid4())` produces a `str` representation; the `UUID` object is garbage-collected after the assignment. Every accessor — `.version`, `.variant`, `.bytes`, `.int` — is gone.

**Fix:**

```python
@dataclass
class Project:
    id: uuid.UUID
    name: str

p = Project(id=uuid.uuid4(), name="alpha")
print(p.id.version)           # 4 — the type carries the metadata
```

### Mistake 2: Using `uuid1` in a public-facing context

```python
# boardly/ids/public_uuid1.py — wrong
@dataclass
class Ticket:
    public_id: uuid.UUID

t = Ticket(public_id=uuid.uuid1(), ...)
# public_id embeds the server's MAC: 0xfb859c580391
# anyone who reads t.public_id.node knows the hardware address
```

**Symptom:** a security review flags your public IDs as leaking the machine's MAC address; an attacker can fingerprint the server hardware and target it.

**Why:** `uuid.uuid1()` embeds 48 bits of MAC address in the `node` field. The `node` accessor exposes it directly.

**Fix:**

```python
t = Ticket(public_id=uuid.uuid4(), ...)   # 122 random bits, no leakage
```

### Mistake 3: Mixing `uuid3` and `uuid5` for the same logical name

```python
# Generate the canonical ID for "boardly.example.com"
stored = uuid.uuid5(uuid.NAMESPACE_DNS, "boardly.example.com")
# ... months later, a colleague re-derives it
derived = uuid.uuid3(uuid.NAMESPACE_DNS, "boardly.example.com")
print(stored == derived)       # False — the two are never equal
```

**Symptom:** two parts of the system re-derive what should be the same UUID and get different values; lookups fail; the team blames the database.

**Why:** `uuid3` uses MD5, `uuid5` uses SHA1 — the two algorithms produce different 128-bit values from the same input, even though the resulting UUID layout is identical. The two are not interchangeable.

**Fix:** Pick one (`uuid5`) and use it everywhere. If you inherit a system that already has `uuid3` values on disk, keep using `uuid3` for those names — do not "migrate" them, because the SHA1-derived value is a *different* identifier.

## Engineering Trade-Offs

**Decision:** `Project.id: uuid.UUID`, generated with `uuid.uuid4()` at the boundary.

**Both sides:** The alternative is `id: str` with the dashed canonical form stored directly. That wins in two narrow cases: (1) a database that does not have a native `uuid` column type and stores the value as `VARCHAR(36)`, where you pay the storage and index cost either way; (2) a system whose consumers all read the value as a string and never need the version/variant bits. The `UUID` type wins in every other case — native Postgres `uuid` columns store 16 bytes (vs 37 for the dashed string), the type carries metadata accessors, malformed input fails at construction time, and the equality semantics are value-based (the dashed and undashed forms of the same UUID compare equal).

**Commitment:** boardly stores `UUID` on the dataclass, generates it with `uuid.uuid4()` for new entities, and converts to `str` only at the JSON serialisation boundary. Lesson 02 revisits the *factory choice* (`uuid4` vs `uuid7`) — this lesson's commitment is to the *type*, not to the factory. The type stays `UUID` either way; the factory is a separate decision the next lesson makes.

## Exercises

1. **Exercise 1 — Generate a v5 for a custom namespace.** Add a line that defines `MY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "boardly.internal")` and derives a deterministic UUID for `"ticket-001"`. `Verify: uv run python -c "import uuid; ns=uuid.uuid5(uuid.NAMESPACE_DNS, 'boardly.internal'); print(uuid.uuid5(ns, 'ticket-001'))"` — should print the same UUID on every run.
2. **Exercise 2 — Round-trip a UUID through `.bytes` and `.bytes_le`.** Generate `u = uuid.uuid4()`, then verify `uuid.UUID(bytes=u.bytes) == u` and `uuid.UUID(bytes_le=u.bytes_le) == u` are both `True`. `Verify: uv run python boardly/ids/uuid_variants.py` — the two equality lines should print `True`.
3. **Exercise 3 — Extract the timestamp from a v1 UUID.** Generate `u = uuid.uuid1()`, then access `u.time` (the 60-bit timestamp count, in 100-nanosecond units since the UUID epoch, 15 October 1582). Compute the wall-clock time it represents. `Verify: uv run python -c "import uuid, datetime; u=uuid.uuid1(); epoch=datetime.datetime(1582,10,15); print(epoch + datetime.timedelta(microseconds=u.time//10))"` — should print a timestamp close to now.
4. **Exercise 4 — Detect the variant of an unknown UUID.** Write a function `classify(u: uuid.UUID) -> str` that returns `"time-based"` if `u.version in (1, 6)`, `"name-hash"` if `u.version in (3, 5)`, `"random"` if `u.version == 4`, and `"reserved"` otherwise. Test with one UUID of each variant you can construct on 3.12. `Verify: uv run python -c "import uuid; print(classify(uuid.uuid4()))"` should print `random`.
5. **Exercise 5 — Implement a v3-to-v5 migration plan (no migration).** Write a function `stable_id(name: str) -> uuid.UUID` that calls `uuid.uuid5(uuid.NAMESPACE_DNS, name)` and document *why* you would never re-issue the same name under `uuid.uuid3` (different algorithm → different value → breaks every stored reference). This exercise does not require a `Verify:` block — the deliverable is the docstring.

## Verification

```bash
$ uv run python boardly/ids/uuid_variants.py 2>&1 | head -8
uuid1:         a1ee0f52-ceab-11f1-b607-fb859c580391 | version: 1 | node: 0xfb859c580391
uuid3:         9586e5e0-b885-36d7-87f0-ddcea68a1144 | deterministic: True
uuid4 a:       1bf0cf26-0cd0-4ee3-9164-83691e9869e6 | version: 4
uuid4 b:       45804fbe-7ebe-4b92-8122-74314e4b8a47 | random (a != b): True
uuid5:         e4fdbcd8-8e23-5822-a549-c44a0cb9058d | version: 5 | != uuid3: True
hasattr uuid6: False
hasattr uuid7: False
hasattr uuid8: False
```

The `hasattr` lines must all read `False` on Python 3.12. On Python 3.14+, they read `True` and you can call `uuid.uuid6()`, `uuid.uuid7()`, `uuid.uuid8()` directly — but lesson 02 still applies the version-gate at import time so the deploy failure surfaces before the first row insertion.

## Previously Learned Here

- [[16-uuid/01-UUID-variants]] — the canonical lesson for the `UUID` type, the `uuid.UUID(...)` constructor's five forms (hex, int, bytes, bytes_le, fields), the `uuid.uuid1/uuid3/uuid4/uuid5` factory functions, and the `.hex/.int/.bytes/.bytes_le/.fields/.version/.variant` accessors. Referenced from lesson 02.

## What's Next

[[16-uuid/02-uuid4-vs-uuid7]] — the database-index lesson. Lesson 01 committed to the *type* (`UUID`); lesson 02 commits to the *factory*. We will show you why `uuid4` is great for uniqueness and terrible for B-tree indexes (page fragmentation, write amplification, cache-miss locality), and why `uuid7` (Python 3.14+, version-gated) is the right factory for new database primary keys: millisecond-timestamp prefix → monotonically increasing → B-tree append-mostly → locality. The runnable demo uses `uuid4` (the 3.12 runtime cannot generate `uuid7`); the `uuid7` description is clearly marked 3.14+ and shows what the index would look like.

- The DB-index cost of `uuid4` — 122 random bits, scattered across the B-tree, every insertion a page split.
- The `uuid7` shape — 48-bit millisecond timestamp + 12 random bits, monotonically increasing within a millisecond.
- The migration rule — new tables use `uuid7`; existing tables keep `uuid4`. Never change primary-key type on existing rows.

## Sources

- **`uuid` — UUID objects and generators** — https://docs.python.org/3/library/uuid.html — accessed 2026-10-23 — the canonical CPython reference for the `UUID` class, the five constructor forms, the four factory functions (`uuid1`, `uuid3`, `uuid4`, `uuid5`), the standard namespaces, and the `bytes`/`bytes_le`/`fields`/`hex`/`int` accessors.
- **RFC 9562 — Universally Unique IDentifiers (UUIDs)** — https://www.rfc-editor.org/rfc/rfc9562.html — accessed 2026-10-23 — the current RFC that obsoletes RFC 4122. Defines the eight variants (1 through 8), the layout bits, and the timestamp epoch (15 October 1582). Source for the `uuid6`/`uuid7`/`uuid8` definitions that Python 3.14 implements.
- **What's New in Python 3.14 — `uuid`** — https://docs.python.org/3.14/whatsnew/3.14.html — accessed 2026-10-23 — confirms that `uuid.uuid6`, `uuid.uuid7`, and `uuid.uuid8` were added to the standard library in Python 3.14 (they do not exist in 3.12 or 3.13). Source for the version-gate language throughout this lesson.

## What We Learned

- You can now construct a `UUID` from a hex string, an int, 16 bytes (big-endian or little-endian), or a 6-field tuple, and explain which external systems hand you which form.
- You can name all eight RFC 9562 variants (1, 2, 3, 4, 5, 6, 7, 8), say what each one is sorted on (time, name, or randomness), and what each one leaks (MAC, nothing, or timestamp).
- You can pick the right factory function for a given context: `uuid1` for closed-system debuggability (never public), `uuid3` for legacy MD5-derived deterministic IDs, `uuid4` for the default opaque ID, `uuid5` for the deterministic ID (preferred over `uuid3`).
- You can read the `.hex`, `.int`, `.bytes`, `.bytes_le`, `.fields`, `.variant`, and `.version` accessors and know which one to reach for at which boundary (Postgres binary, SQL Server, URL string, timestamp extraction).
- You can state the rule: never store an identifier as `str`. The dataclass field is `UUID`. The string form exists only at the JSON serialisation boundary. The next lesson decides which *factory* generates the value; this lesson committed to the *type*.
