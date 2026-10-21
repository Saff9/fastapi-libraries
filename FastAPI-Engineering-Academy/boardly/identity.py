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
