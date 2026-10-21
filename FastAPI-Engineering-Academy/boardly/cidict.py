# boardly/cidict.py
"""Case-insensitive header dict using collections.UserDict."""
from collections import UserDict, UserList, UserString
from typing import Any, Iterator


class CaseInsensitiveDict(UserDict):
    """A dict whose keys are case-insensitive.

    Subclassing dict directly does NOT work for this — dict.__init__ and
    dict.update bypass __setitem__ for performance. UserDict routes every
    write through __setitem__, so the override actually fires.
    """

    def __setitem__(self, key: str, value: Any) -> None:
        # Lowercase the key before storing; super().__setitem__ stores in self.data.
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key: str) -> Any:
        # Lowercase on read so d["Content-Type"] finds d["content-type"].
        return super().__getitem__(key.lower())

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key.lower())

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return super().__contains__(key.lower())
        return False

    def __iter__(self) -> Iterator[str]:
        # Iteration yields lowercased keys (since they are stored lowercased).
        return super().__iter__()


class BoundedList(UserList):
    """A list that refuses to grow past a fixed capacity."""

    def __init__(self, capacity: int, init: list | None = None) -> None:
        # UserList.__init__ calls self.extend(init) — which calls __setitem__? No:
        # UserList.extend appends via self.data.append, but __init__ sets self.data
        # directly from the iterable. So we override __init__ to truncate.
        super().__init__(init or [])
        self._capacity = capacity
        # Truncate if the init iterable exceeded capacity.
        if len(self.data) > self._capacity:
            self.data = self.data[: self._capacity]

    def append(self, item: Any) -> None:
        if len(self.data) >= self._capacity:
            raise ValueError(f"capacity {self._capacity} exceeded")
        self.data.append(item)

    def extend(self, items) -> None:
        for item in items:
            self.append(item)


class HexString(UserString):
    """A string that validates it contains only hex characters."""

    def __init__(self, s: str) -> None:
        super().__init__(s)
        # Validate after init; UserString stores the raw string in self.data.
        if not all(c in "0123456789abcdefABCDEF" for c in self.data):
            raise ValueError(f"not a hex string: {s!r}")


if __name__ == "__main__":
    print("--- CaseInsensitiveDict ---")
    h = CaseInsensitiveDict({"Content-Type": "application/json"})
    print(f"\"content-type\" in h: {'content-type' in h}")
    print(f"h['Content-Type']: {h['Content-Type']}")
    print(f"keys: {list(h.keys())}")

    print("\n--- compare with raw dict subclass ---")
    class BuggyCIDict(dict):
        def __setitem__(self, k, v): super().__setitem__(k.lower(), v)
    buggy = BuggyCIDict({"Content-Type": "x"})
    print(f"buggy: \"content-type\" in d = {'content-type' in buggy} (should be True)")

    print("\n--- BoundedList ---")
    bl = BoundedList(capacity=3, init=[1, 2, 3])
    print(f"init: {bl.data}")
    try:
        bl.append(4)
    except ValueError as e:
        print(f"append(4) raised: {e}")

    print("\n--- HexString ---")
    hs = HexString("deadBEEF")
    print(f"hex: {hs}")
    try:
        HexString("not hex")
    except ValueError as e:
        print(f"HexString('not hex') raised: {e}")
