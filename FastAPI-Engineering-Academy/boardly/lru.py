# boardly/lru.py
"""Tiny LRU cache on top of collections.OrderedDict."""
from collections import OrderedDict
from typing import Callable, Generic, TypeVar
from uuid import UUID

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """A fixed-capacity LRU cache built on OrderedDict.

    OrderedDict's move_to_end(last=True) and popitem(last=False) are the
    only two operations an LRU needs. Both are O(1).
    """

    def __init__(self, capacity: int, loader: Callable[[K], V]) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._loader = loader
        # OrderedDict preserves insertion order; we maintain "MRU at the end".
        self._store: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V:
        if key in self._store:
            # Cache hit — move to the MRU end (one operation, in place).
            self._store.move_to_end(key, last=True)
            return self._store[key]
        # Cache miss — load, store, evict if over capacity.
        value = self._loader(key)
        self._store[key] = value
        if len(self._store) > self._capacity:
            # Pop the LRU entry (the first-inserted / least-recently-moved).
            self._store.popitem(last=False)
        return value

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store


if __name__ == "__main__":
    def load_user(uid: UUID) -> str:
        return f"perms_for_{uid}"

    cache: LRUCache[UUID, str] = LRUCache(capacity=3, loader=load_user)
    u1, u2, u3, u4 = UUID("00000000-0000-0000-0000-000000000001"), \
                     UUID("00000000-0000-0000-0000-000000000002"), \
                     UUID("00000000-0000-0000-0000-000000000003"), \
                     UUID("00000000-0000-0000-0000-000000000004")

    cache.get(u1); cache.get(u2); cache.get(u3)
    print(f"after 3 gets: len={len(cache)}")
    cache.get(u1)  # touch u1 -> it should now be MRU; u2 is LRU
    cache.get(u4)  # miss; u2 should be evicted
    print(f"after touch + new miss: len={len(cache)}")
    print(f"u1 in cache: {u1 in cache}")
    print(f"u2 in cache: {u2 in cache}")  # should be False — evicted

    print("\n--- order-sensitive equality demo ---")
    a = OrderedDict([("x", 1), ("y", 2)])
    b = OrderedDict([("y", 2), ("x", 1)])
    c = {"x": 1, "y": 2}
    d = {"y": 2, "x": 1}
    print(f"a == b (OrderedDict, different order): {a == b}")  # False
    print(f"c == d (dict, different order): {c == d}")          # True
    print(f"a == c (OrderedDict vs dict, same order): {a == c}")  # True
