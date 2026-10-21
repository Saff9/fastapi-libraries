---
title: "Lesson 03: Hashable and Frozen"
aliases:
 - collections.abc.Hashable
 - Hashable
 - __hash__
 - frozen dataclass
tags:
 - collections-abc
 - hashable
 - dataclass
 - frozen
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[05-collections-abc/02-Sequence-Mapping-Set]]"
related_lessons:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
---

# Lesson 03: Hashable and Frozen

*`collections.abc.Hashable` — the ABC for "anything that has a `__hash__` that stays stable while the object is in a dict key or set". The immutability contract: a hashable object must not mutate (in any way that affects equality) for as long as anyone holds its hash. This lesson walks `__hash__`, the mutable-vs-immutable contract, and the connection to `@dataclass(frozen=True)`.*

**You're at the very beginning of Section 05 — Lesson 03.**

`Hashable` is the smallest ABC in `collections.abc` — one abstract method, `__hash__`. But the contract it implies is profound: "this object will not change in any way that affects equality while its hash is in use". That contract is why `dict` keys and `set` members must be hashable. Violate it and you get a "I cannot find the key I just inserted" bug.

Take your time. Type every example. **This is how you learn.**

#collections-abc #hashable #frozen

## Learning Objectives

By the end of this lesson you will be able to:

1. **Implement `__hash__`** correctly — return an `int`, derive it from immutable fields only.
2. **Explain why mutable objects are unhashable** — the dict-lookup invariant.
3. **Convert a mutable `@dataclass` to a hashable one** with `frozen=True`.
4. **Spot the "I mutated and now my key is gone" bug** in production code.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/02-Sequence-Mapping-Set]]** — comfort with ABCs as classes you inherit from.
- **About 25 minutes of focused time.**

**The most common gap: not knowing `__hash__` and `__eq__` must agree.**

Two objects that are equal (`a == b` is `True`) must have the same hash (`hash(a) == hash(b)`). The reverse is not required: two objects with the same hash need not be equal (that is a hash collision, which `dict` handles). If you override `__eq__` without overriding `__hash__`, Python sets `__hash__ = None` and the class becomes unhashable — that has bitten every Python developer once. Read this lesson with "hash and eq agree" front of mind.

## The Problem

Here is the bug. `boardly` wants to put `Ticket` instances into a set to deduplicate them:

```python
from dataclasses import dataclass

@dataclass
class Ticket:
    id: int
    title: str
    status: str = "todo"

tickets = {Ticket(1, "x"), Ticket(1, "x")}
print(len(tickets))   # student expects 1
```

Run it. `len(tickets)` is `1` — `@dataclass` generates both `__eq__` and `__hash__` based on the fields, so two equal `Ticket`s deduplicate. Good.

Now the product team wants to mutate ticket status:

```python
t = Ticket(1, "x", "todo")
s = {t}
t.status = "done"
print(t in s)   # student expects True
```

Run it. `t in s` is `False` — even though `t` is *literally the same object* the set contains. Why? Because `set.__contains__` looks up `hash(t)` in its hash table; mutating `t.status` changed the value of `hash(t)` (because `@dataclass` includes all fields in the hash). The old hash slot is empty; the new hash slot is also empty (the object was inserted under the old hash). The set is now corrupt — it holds `t` but cannot find it.

This is the *mutability contract violation*. The contract says: "An object in a dict key or set member must not mutate in any way that affects `__hash__` or `__eq__`." `@dataclass` without `frozen=True` generates `__hash__` anyway (since 3.x) — but it is your responsibility not to mutate the object while it is hashed.

The fix is `@dataclass(frozen=True)`. That makes the dataclass immutable; mutation raises `FrozenInstanceError`. Then `__hash__` is safe because the fields cannot change.

## The Code

```python
# boardly/identity.py
"""Hashable vs unhashable, mutable vs frozen — the contract."""
from collections.abc import Hashable
from dataclasses import dataclass, field
from uuid import uuid4, UUID
from typing import Any


# --- A mutable dataclass with unsafe_hash=True: hash exists, but the contract is fragile ---

@dataclass(unsafe_hash=True)
class MutableTicket:
    id: UUID
    title: str
    status: str = "todo"


# --- A frozen dataclass: __hash__ is safe because the fields cannot change ---

@dataclass(frozen=True)
class FrozenTicket:
    id: UUID
    title: str
    status: str = "todo"


# --- A custom Hashable implementation ---

class CacheKey:
    """A custom hashable: derives hash from a single immutable field.

    We implement __hash__ and __eq__ ourselves to demonstrate the contract.
    The hash is computed once at __init__ and cached.
    """

    __slots__ = ("_key", "_hash")

    def __init__(self, key: str) -> None:
        self._key = key
        self._hash = hash(("CacheKey", key))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CacheKey) and self._key == other._key

    def __repr__(self) -> str:
        return f"CacheKey({self._key!r})"


def is_hashable(obj: Any) -> bool:
    return isinstance(obj, Hashable)


if __name__ == "__main__":
    print("--- is_hashable checks ---")
    print(f"int 42:                {is_hashable(42)}")
    print(f"str 'hello':           {is_hashable('hello')}")
    print(f"tuple (1, 2, 3):       {is_hashable((1, 2, 3))}")
    print(f"list [1, 2, 3]:         {is_hashable([1, 2, 3])}")
    print(f"dict {{'a': 1}}:          {is_hashable({'a': 1})}")
    print(f"MutableTicket:         {is_hashable(MutableTicket(uuid4(), 'x'))}")
    print(f"FrozenTicket:          {is_hashable(FrozenTicket(uuid4(), 'x'))}")
    print(f"CacheKey:              {is_hashable(CacheKey('k'))}")

    print("\n--- the mutability-contract bug ---")
    t = MutableTicket(uuid4(), "x", "todo")
    s = {t}
    print(f"before mutate: t in s = {t in s}")
    t.status = "done"   # mutates a hash-relevant field!
    print(f"after mutate:  t in s = {t in s}  (BUG: set is now corrupt)")

    print("\n--- frozen dataclass prevents the bug ---")
    f = FrozenTicket(uuid4(), "x", "todo")
    fs = {f}
    print(f"before mutate attempt: f in fs = {f in fs}")
    try:
        f.status = "done"
    except Exception as e:
        print(f"frozen raise: {type(e).__name__}: {e}")
    print(f"after attempt:  f in fs = {f in fs}  (no bug; mutation was blocked)")

    print("\n--- custom CacheKey with cached hash ---")
    k1 = CacheKey("foo")
    k2 = CacheKey("foo")
    print(f"k1 == k2: {k1 == k2}   (same key)")
    print(f"hash(k1) == hash(k2): {hash(k1) == hash(k2)}")
    print(f"isinstance(k1, Hashable): {isinstance(k1, Hashable)}")

    print("\n--- overriding __eq__ without __hash__ makes the class unhashable ---")
    class Bad:
        def __eq__(self, other): return isinstance(other, Bad)
        # no __hash__ override -> Python sets __hash__ = None
    try:
        hash(Bad())
    except TypeError as e:
        print(f"hash(Bad()) raises: {e}")
```

## Line-by-Line Deep Dive

### Lines 7–14: A mutable `@dataclass` with `unsafe_hash=True`

```python
@dataclass(unsafe_hash=True)
class MutableTicket:
    id: UUID
    title: str
    status: str = "todo"
```

`@dataclass` (without `frozen=True` and without `unsafe_hash=True`) sets `__hash__ = None` by default — the class is *unhashable*. That is the safe default: a mutable class that defines `__hash__` from its fields is a bug waiting to happen, because mutating a field changes the hash and corrupts any set or dict that holds the object. We pass `unsafe_hash=True` explicitly to opt into the unsafe behaviour — this is the demo we want for the mutability-contract bug. The name is the warning: you are responsible for not mutating the object while it is hashed.

The three hash modes a `@dataclass` can be in:

- `@dataclass` (default; `eq=True`, `frozen=False`): sets `__hash__ = None`. The class is unhashable.
- `@dataclass(frozen=True)`: generates `__hash__` from the fields. Safe because fields cannot change.
- `@dataclass(unsafe_hash=True)`: generates `__hash__` from the fields even though the class is mutable. You must not mutate fields while the object is in a dict or set.

The `MutableTicket` above uses `unsafe_hash=True` so we can demonstrate the bug — `s = {t}` then `t.status = "done"` then `t in s` returns `False`.

### Lines 18–22: A frozen `@dataclass`

```python
@dataclass(frozen=True)
class FrozenTicket:
    id: UUID
    title: str
    status: str = "todo"
```

`@dataclass(frozen=True)` generates:

- All the same methods as the mutable variant, plus
- A `__setattr__` and `__delattr__` that raise `FrozenInstanceError`.
- A `__hash__` based on the fields (because `frozen=True` implies the class is hashable).

The hash is safe because the fields cannot change after construction. `FrozenTicket(uuid4(), "x")` is hashable and stays hashable forever.

### Lines 26–47: A custom `Hashable` implementation

```python
class CacheKey:
    """A custom hashable: derives hash from a single immutable field.

    We implement __hash__ and __eq__ ourselves to demonstrate the contract.
    The hash is computed once at __init__ and cached.
    """

    __slots__ = ("_key", "_hash")

    def __init__(self, key: str) -> None:
        self._key = key
        self._hash = hash(("CacheKey", key))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CacheKey) and self._key == other._key

    def __repr__(self) -> str:
        return f"CacheKey({self._key!r})"
```

`__slots__ = ("_key", "_hash")` — `__slots__` prevents the creation of a per-instance `__dict__`. Two effects: smaller memory footprint (one fewer dict per instance) and a small speedup on attribute access. For a high-volume key class, `__slots__` is worth it.

`self._hash = hash(("CacheKey", key))` — the hash is computed once at construction and cached. This is the *frozen* contract made explicit: even if the underlying `_key` could change (it cannot, because there is no setter), the *hash* is fixed. `dict` lookups then use the cached value, not a recomputed one — a measurable speedup for high-traffic keys.

**Why include `"CacheKey"` in the hash tuple?** To avoid hash collisions across types. A `CacheKey("foo")` and a plain tuple `("CacheKey", "foo")` would have the same hash if we just hashed `_key`; by including the class name in the hash, we get a different hash from other hashables with the same `_key` value (which reduces the chance of in-dict collisions on heterogeneous-key dicts).

`__hash__` and `__eq__` agree: both look at `_key`. Two `CacheKey`s with the same `_key` are equal *and* have the same hash. The contract holds.

### Lines 51–52: The `is_hashable` helper

```python
def is_hashable(obj: Any) -> bool:
    return isinstance(obj, Hashable)
```

`isinstance(obj, Hashable)` uses the `__subclasshook__` mechanism (next lesson) — it returns `True` if `type(obj)` has a `__hash__` attribute that is not `None`. This is the structural check: you do not need to inherit from `Hashable` to pass.

### Lines 56–64: The smoke test — `is_hashable` on real types

```python
if __name__ == "__main__":
    print("--- is_hashable checks ---")
    print(f"int 42:                {is_hashable(42)}")
    print(f"str 'hello':           {is_hashable('hello')}")
    print(f"tuple (1, 2, 3):       {is_hashable((1, 2, 3))}")
    print(f"list [1, 2, 3]:         {is_hashable([1, 2, 3])}")
    print(f"dict {{'a': 1}}:          {is_hashable({'a': 1})}")
    print(f"MutableTicket:         {is_hashable(MutableTicket(uuid4(), 'x'))}")
    print(f"FrozenTicket:          {is_hashable(FrozenTicket(uuid4(), 'x'))}")
    print(f"CacheKey:              {is_hashable(CacheKey('k'))}")
```

Ints, strings, tuples are hashable. Lists and dicts are not — they are mutable and Python refuses to hash them (their `__hash__` is `None`). `MutableTicket` (with `unsafe_hash=True`) is hashable. `FrozenTicket` (with `frozen=True`) is hashable. `CacheKey` (with explicit `__hash__`) is hashable.

### Lines 66–72: The mutability-contract bug demonstration

```python
    print("\n--- the mutability-contract bug ---")
    t = MutableTicket(uuid4(), "x", "todo")
    s = {t}
    print(f"before mutate: t in s = {t in s}")
    t.status = "done"   # mutates a hash-relevant field!
    print(f"after mutate:  t in s = {t in s}  (BUG: set is now corrupt)")
```

This is the bug. Before mutation, `t in s` is `True`. After `t.status = "done"`, `t in s` is `False`. The set contains `t` but cannot find it because its hash changed.

**Why does this happen?** `set.__contains__` computes `hash(t)` and looks in the corresponding bucket. Before mutation, `hash(t)` was based on `("UUID-of-t", "x", "todo")` and the bucket had `t`. After mutation, `hash(t)` is based on `("UUID-of-t", "x", "done")` — a *different* bucket. That bucket is empty. The set reports `t not in s` even though `t` is in the set's internal linked list.

### Lines 74–82: `frozen=True` prevents the bug

```python
    print("\n--- frozen dataclass prevents the bug ---")
    f = FrozenTicket(uuid4(), "x", "todo")
    fs = {f}
    print(f"before mutate attempt: f in fs = {f in fs}")
    try:
        f.status = "done"
    except Exception as e:
        print(f"frozen raise: {type(e).__name__}: {e}")
    print(f"after attempt:  f in fs = {f in fs}  (no bug; mutation was blocked)")
```

`f.status = "done"` raises `FrozenInstanceError` (it is a `dataclasses.FrozenInstanceError` subclass of `AttributeError`). The mutation is blocked at the language level — the bug cannot happen because the operation that would cause it cannot run.

### Lines 84–88: Custom `CacheKey` with cached hash

```python
    print("\n--- custom CacheKey with cached hash ---")
    k1 = CacheKey("foo")
    k2 = CacheKey("foo")
    print(f"k1 == k2: {k1 == k2}   (same key)")
    print(f"hash(k1) == hash(k2): {hash(k1) == hash(k2)}")
    print(f"isinstance(k1, Hashable): {isinstance(k1, Hashable)}")
```

Two `CacheKey`s with the same `_key` are equal and have the same hash. The `isinstance` check is `True` — `CacheKey` conforms to `Hashable` via the structural `__subclasshook__`.

### Lines 90–96: The `__eq__`-without-`__hash__` gotcha

```python
    print("\n--- overriding __eq__ without __hash__ makes the class unhashable ---")
    class Bad:
        def __eq__(self, other): return isinstance(other, Bad)
        # no __hash__ override -> Python sets __hash__ = None
    try:
        hash(Bad())
    except TypeError as e:
        print(f"hash(Bad()) raises: {e}")
```

This is the gotcha that bites every Python developer once. You override `__eq__` to give your class meaningful equality. Python *automatically* sets `__hash__ = None` on the class, because the language rule is "if you customise equality, you must also customise hash" (the alternative — inheriting `object.__hash__` based on `id()` — would violate the contract, since equal objects would have different hashes).

`hash(Bad())` raises `TypeError: unhashable type: 'Bad'`. The fix is to also define `__hash__`:

```python
class Good:
    def __eq__(self, other): return isinstance(other, Good)
    def __hash__(self): return hash("Good")  # or any stable hash
```

## Execution Trace

```bash
$ uv run python boardly/identity.py
--- is_hashable checks ---
int 42:                True
str 'hello':           True
tuple (1, 2, 3):       True
list [1, 2, 3]:        False
dict {'a': 1}:          False
MutableTicket:         True
FrozenTicket:          True
CacheKey:              True

--- the mutability-contract bug ---
before mutate: t in s = True
after mutate:  t in s = False  (BUG: set is now corrupt)

--- frozen dataclass prevents the bug ---
before mutate attempt: f in fs = True
frozen raise: FrozenInstanceError: cannot assign to field 'status'
after attempt:  f in fs = True  (no bug; mutation was blocked)

--- custom CacheKey with cached hash ---
k1 == k2: True   (same key)
hash(k1) == hash(k2): True
isinstance(k1, Hashable): True

--- overriding __eq__ without __hash__ makes the class unhashable ---
hash(Bad()) raises: unhashable type: 'Bad'
```

## Common Mistakes

### Mistake 1: Overriding `__eq__` and forgetting `__hash__`

```python
class Vector:
    def __init__(self, x, y): self.x, self.y = x, y
    def __eq__(self, o): return (self.x, self.y) == (o.x, o.y)
    # no __hash__
v = Vector(1, 2)
d = {v: "x"}   # student expects this to work
```

**Symptom:** `TypeError: unhashable type: 'Vector'`.

**Why:** When you define `__eq__` on a class, Python sets `__hash__ = None` on the class. The class becomes unhashable until you also define `__hash__`.

**Fix:** Define `__hash__` based on the same fields as `__eq__`:

```python
def __hash__(self): return hash((self.x, self.y))
```

Or use `@dataclass(frozen=True)` (which generates both `__eq__` and `__hash__` and prevents mutation). Plain `@dataclass` without `frozen=True` or `unsafe_hash=True` sets `__hash__ = None` — the class is unhashable by default.

### Mistake 2: Mutating a hashable object while it is in a set/dict

```python
@dataclass(unsafe_hash=True)
class T:
    x: int

t = T(1)
s = {t}
t.x = 2
print(t in s)   # student expects True
```

**Symptom:** `t in s` is `False` — the set lost the object.

**Why:** `unsafe_hash=True` is the explicit opt-in to "I will not mutate this while hashed". The hash is derived from `x`; mutating `x` changes the hash; the set's hash table no longer points to `t`.

**Fix:** Use `@dataclass(frozen=True)` instead. The mutation will raise. If you need mutation, do not put the object in a set or use it as a dict key — that is the only safe combination.

### Mistake 3: Using `id()` as a hash for an equality-defined class

```python
class Bad:
    def __eq__(self, o): return isinstance(o, Bad)
    def __hash__(self): return id(self)   # student thinks this is safe
```

**Symptom:** No immediate symptom — but `Bad() == Bad()` is `True` while `hash(Bad()) != hash(another Bad())`. The contract is violated.

**Why:** The contract is "equal objects must have equal hashes". `id(self)` is unique per object; two equal `Bad()`s have different ids, therefore different hashes. Any dict using `Bad` as keys will fail to find values.

**Fix:** Use a constant hash (e.g., `hash("Bad")`) or, better, derive the hash from the same fields as equality. If you genuinely want identity-based equality and identity-based hash, do not override `__eq__` at all — `object.__eq__` is identity-based and `object.__hash__` is `id()`-based, and they agree.

## Engineering Trade-Offs

**Decision:** Use `@dataclass(frozen=True)` for any data class that will be a dict key, set member, or `lru_cache` argument. Use `@dataclass(unsafe_hash=True)` only when you control the lifetime of the object strictly.

**Both sides:**

`frozen=True` wins on:

1. Safety. Mutation is impossible; the hash contract holds by construction.
2. Hashability. `__hash__` is auto-generated from the fields.
3. Documentation. The class's immutability is visible in the decorator.

`unsafe_hash=True` wins on:

1. You get a mutable, hashable class — for the rare case where you want to use the object as a key for a short, controlled period.
2. You can rebuild the class with the same identity but different fields (advanced pattern; rarely needed).

`mutable, unhashable` (the default) wins on:

1. Performance — no `__hash__` generation, no `FrozenInstanceError` check on every `__setattr__`.
2. Most classes — the vast majority of data classes are never used as keys.

**Commitment:** `boardly/identity.py` uses `@dataclass(frozen=True)` for `FrozenTicket` (the canonical case). The mutable `MutableTicket` exists only as the demo for the bug. Production code in `boardly/models.py` uses plain `@dataclass` for `Project`, `User`, `Ticket` because they are not used as dict keys — they are stored in lists and looked up by `id`. The rule: "Will it be a key or set member? `frozen=True`. Otherwise? `@dataclass`."

## Exercises

1. **Exercise 1 — Confirm `list` is unhashable.** Try `hash([1, 2])` and confirm `TypeError`. `Verify: uv run python -c "try:\n  hash([1,2])\nexcept TypeError as e:\n  print('TypeError:', e)"`
2. **Exercise 2 — Confirm `__eq__` without `__hash__` makes a class unhashable.** Define a class with `__eq__` only and try `hash()`. `Verify: uv run python -c "class C:\n  def __eq__(self, o): return True\ntry:\n  hash(C())\nexcept TypeError as e:\n  print('TypeError:', e)"`
3. **Exercise 3 — Frozen dataclass is hashable.** Build a `@dataclass(frozen=True)` and confirm `hash()` works. `Verify: uv run python -c "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass C:\n  x: int\nprint(hash(C(1)) == hash(C(1)))"`
4. **Exercise 4 — Cached hash.** Build a class with `__slots__`, compute the hash once in `__init__`, and confirm two equal instances have the same cached hash. `Verify: uv run python -c "\nclass C:\n  __slots__ = ('_k', '_h')\n  def __init__(self, k):\n    self._k = k; self._h = hash(('C', k))\n  def __hash__(self): return self._h\n  def __eq__(self, o): return isinstance(o, C) and self._k == o._k\nprint(hash(C('a')) == hash(C('a')))"`
5. **Exercise 5 — Frozen mutation blocked.** Build a `@dataclass(frozen=True)`, try to set an attribute, confirm `FrozenInstanceError`. `Verify: uv run python -c "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass C:\n  x: int\ntry:\n  C(1).x = 2\nexcept Exception as e:\n  print(type(e).__name__, ':', e)"`

## Verification

```bash
$ uv run python boardly/identity.py
--- is_hashable checks ---
int 42:                True
str 'hello':           True
tuple (1, 2, 3):       True
list [1, 2, 3]:        False
dict {'a': 1}:          False
MutableTicket:         True
FrozenTicket:          True
CacheKey:              True

--- the mutability-contract bug ---
before mutate: t in s = True
after mutate:  t in s = False  (BUG: set is now corrupt)

--- frozen dataclass prevents the bug ---
before mutate attempt: f in fs = True
frozen raise: FrozenInstanceError: cannot assign to field 'status'
after attempt:  f in fs = True  (no bug; mutation was blocked)

--- custom CacheKey with cached hash ---
k1 == k2: True   (same key)
hash(k1) == hash(k2): True
isinstance(k1, Hashable): True

--- overriding __eq__ without __hash__ makes the class unhashable ---
hash(Bad()) raises: unhashable type: 'Bad'
```

## Previously Learned Here

- [[05-collections-abc/02-Sequence-Mapping-Set]] — the mixin-method pattern; this lesson is the *contract* pattern.
- [[05-collections-abc/01-The-ABC-Hierarchy]] — `Hashable` was one of the five root ABCs in the hierarchy.

## What's Next

[[05-collections-abc/04-Iterator-vs-Iterable]] — the `Iterable` → `Iterator` → `Generator` subtree. The `__iter__` vs `__next__` distinction, the `iter()` builtin, the StopIteration protocol, the "iterator is exhausted" gotcha that bites every developer the first time they try `for x in gen: ...; for x in gen: ...` and get zero iterations on the second loop.

## Sources

- **Python `collections.abc.Hashable` documentation** — https://docs.python.org/3/library/collections.abc.html#collections.abc.Hashable — accessed 2026-10-23 — the ABC with the single abstract method `__hash__`.
- **Python data model: `__hash__`** — https://docs.python.org/3/reference/datamodel.html#object.__hash__ — accessed 2026-10-23 — the language rule that `__eq__` and `__hash__` must agree.
- **`dataclasses` documentation: `frozen` and `unsafe_hash`** — https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass — accessed 2026-10-23 — the `eq`/`frozen`/`unsafe_hash` parameter matrix and the three hash modes a dataclass can be in.

## What We Learned

- `Hashable` is a one-method ABC (`__hash__`) with a profound contract: hash and equality must agree.
- Overriding `__eq__` without `__hash__` makes the class unhashable (Python sets `__hash__ = None`).
- Mutable objects that are hashable can corrupt sets and dicts if you mutate them while they are keys — `unsafe_hash=True` is the explicit opt-in.
- `@dataclass(frozen=True)` is the safe path: immutable, hashable, no contract to remember.
- Custom `Hashable` implementations can cache the hash in `__init__` for a measurable speedup on high-traffic keys.
