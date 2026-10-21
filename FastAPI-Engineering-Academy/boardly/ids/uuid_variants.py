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
