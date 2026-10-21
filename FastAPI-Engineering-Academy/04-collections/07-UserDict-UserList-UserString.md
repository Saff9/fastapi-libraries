---
title: "Lesson 07: UserDict, UserList, UserString"
aliases:
 - collections.UserDict
 - collections.UserList
 - collections.UserString
 - UserDict
tags:
 - collections
 - userdict
 - subclassing
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[04-collections/06-OrderedDict]]"
related_lessons:
 - "[[04-collections/02-defaultdict]]"
 - "[[05-collections-abc/02-Sequence-Mapping-Set]]"
---

# Lesson 07: UserDict, UserList, UserString

*`collections.UserDict` / `UserList` / `UserString` — the *safe* base classes for subclassing `dict` / `list` / `str`. They hold the real storage in a `.data` attribute and route every method through `__getitem__` / `__setitem__`, so your override actually fires when `update` or `__init__` runs. Without them, you are standing in a `dict.update`-did-not-call-my-`__setitem__` bug.*

**You're at the very beginning of Section 04 — Lesson 07.**

This is the last stop in the section, and the lesson that explains the underlying pattern of the whole module. `UserDict` looks redundant — `class MyDict(dict): ...` works, and you do not see why anyone would write `class MyDict(UserDict): ...` until they ship a `__setitem__` override and discover `dict.update` ignores it. By the end of this lesson you will know exactly when to reach for `UserDict`, `UserList`, or `UserString`, and when the raw builtin is fine.

Take your time. Type every example. **This is how you learn.**

#collections #userdict #subclassing

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `UserDict` / `UserList` / `UserString`** and locate the real storage in `.data`.
2. **Override `__setitem__` on a `UserDict`** and confirm that `.update()` and `__init__()` call your override (the bug on raw `dict` subclassing).
3. **Explain the historical context** — why `UserDict` was added (Python 1.x had the same trap on `dict`), and why `UserList` / `UserString` followed.
4. **Decide between `UserDict` and `dict`** for a given custom mapping.

## Prerequisites

Before starting, you need:

- **[[04-collections/06-OrderedDict]]** — comfort with the `collections` mapping family and the subclassing pattern.
- **Basic familiarity with `dict.__getitem__` / `dict.__setitem__`** — the methods that fire on `d[k]` and `d[k] = v`.
- **About 25 minutes of focused time.**

**The most common gap: not knowing `dict.update` does not call `__setitem__`.**

Students write `class MyDict(dict): def __setitem__(self, k, v): ...; print("set!")`. They construct `MyDict({"a": 1})` and the `print` does not fire. They call `MyDict().update({"a": 1})` and the print does not fire. They read the docs, learn that `dict` is implemented in C and its methods bypass `__setitem__` for performance, and reach for `UserDict`. This lesson walks that entire arc in one file.

## The Problem

Here is the bug. `boardly` wants a `CaseInsensitiveDict` that lowercases keys on the way in. The first implementation everyone writes:

```python
class CaseInsensitiveDict(dict):
    def __setitem__(self, key: str, value: object) -> None:
        super().__setitem__(key.lower(), value)

d = CaseInsensitiveDict({"Content-Type": "application/json"})
print("Content-Type" in d, "content-type" in d)
```

Run it. The expected output is `True True` — the constructor should have lowercased the key. The *actual* output is `True False` — the original-case key is in the dict, the lowercased one is not. The constructor never called `__setitem__`.

`dict` is implemented in C. `dict.__init__` and `dict.update` and `dict.setdefault` all write directly to the C-level hash table; they do not call back into Python-level `__setitem__`. The override exists but it is dead code on those paths.

`UserDict` solves this. It is implemented in Python and routes every write through `__setitem__`:

```python
from collections import UserDict

class CaseInsensitiveDict(UserDict):
    def __setitem__(self, key: str, value: object) -> None:
        super().__setitem__(key.lower(), value)

d = CaseInsensitiveDict({"Content-Type": "application/json"})
print("content-type" in d)   # True — the constructor DID call __setitem__
```

## The Code

```python
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
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports

```python
# boardly/cidict.py
"""Case-insensitive header dict using collections.UserDict."""
from collections import UserDict, UserList, UserString
from typing import Any, Iterator
```

`from collections import UserDict, UserList, UserString` — all three live in `collections`. They are capitalised because they are real classes (not factory functions like `namedtuple`), and they were named in the Python 1.x era when "user-facing class" naming conventions were less settled.

### Lines 9–35: `CaseInsensitiveDict` — the canonical UserDict use case

```python
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
```

`class CaseInsensitiveDict(UserDict):` — `UserDict` is the safe base. Underneath, `UserDict` holds a `self.data` attribute that is a plain `dict`; every method (`__getitem__`, `__setitem__`, `__delitem__`, `__contains__`, `__iter__`, `keys`, `values`, `items`, `update`, `get`, `pop`, `setdefault`, `__eq__`, `__len__`, `__repr__`) routes through `__getitem__` / `__setitem__` / `__delitem__` on `self.data`.

`super().__setitem__(key.lower(), value)` — `UserDict.__setitem__` is `self.data[key] = value`. So your override lowercases the key, then calls `super().__setitem__`, which stores it in `self.data`.

The four overrides — `__setitem__`, `__getitem__`, `__delitem__`, `__contains__` — cover the read/write/delete/test paths. Together they give you a fully case-insensitive mapping without touching the constructor or `.update`.

**Why does `UserDict.__init__` route through `__setitem__`?** Because `UserDict.__init__` is implemented in Python and uses `self.update(iterable)`, which calls `self[k] = v` for each pair, which calls `self.__setitem__`. That is the entire reason `UserDict` exists. The same applies to `UserList.__init__` (which calls `self.extend`) and `UserString` (which stores the raw input in `self.data` and exposes the str methods via `__getattr__`).

### Lines 39–58: `BoundedList` — the UserList pattern

```python
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
```

`UserList` is to `list` what `UserDict` is to `dict`. Underneath, `UserList.data` is a plain `list`. Every list method is overridden in Python to route through `self.data`.

The `append` override on `UserList` *does* fire when you call `my_list.append(x)`, because `UserList.append` is a Python method that calls `self.data.append`. The catch is `__init__`: `UserList.__init__` calls `self.data.extend(init)` — *not* `self.append`. So your `append` override does not fire during construction. We work around that by truncating in `__init__` after the fact, and by overriding `extend` to route through `append` (which fires our check).

### Lines 62–69: `HexString` — UserString for validation

```python
class HexString(UserString):
    """A string that validates it contains only hex characters."""

    def __init__(self, s: str) -> None:
        super().__init__(s)
        # Validate after init; UserString stores the raw string in self.data.
        if not all(c in "0123456789abcdefABCDEF" for c in self.data):
            raise ValueError(f"not a hex string: {s!r}")
```

`UserString` is the same pattern applied to `str`. `self.data` is a plain `str`. Every string method (`upper`, `lower`, `split`, `join`, ...) is a `UserString` method that calls `self.data.upper()` etc. and returns a `UserString` (where appropriate) or a plain `str`.

**Why subclass `UserString` instead of `str`?** Because `str` is a built-in C type and is *immutable* — overriding `__new__` to validate is the only way to get a "validated str". `UserString` is a Python class with a `data` attribute, so you can validate in `__init__` (or in `__new__`) and the construction path is clean.

### Lines 73–94: The `__main__` smoke test — including the buggy raw-dict version

```python
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
```

The smoke test deliberately includes `BuggyCIDict(dict)` so you can see the bug with your own eyes. The constructor passes `{"Content-Type": "x"}` to `dict.__init__`, which writes the key directly without calling `__setitem__`. The result: `"content-type" in buggy` is `False`, even though the override was supposed to lowercase.

## Execution Trace

```bash
$ uv run python boardly/cidict.py
--- CaseInsensitiveDict ---
"content-type" in h: True
h['Content-Type']: application/json
keys: ['content-type']

--- compare with raw dict subclass ---
buggy: "content-type" in d = False (should be True)

--- BoundedList ---
init: [1, 2, 3]
append(4) raised: capacity 3 exceeded

--- HexString ---
hex: deadBEEF
HexString('not hex') raised: not a hex string: 'not hex'
```

The two prints that prove the lesson are `"content-type" in h: True` (the UserDict version) and `buggy: "content-type" in d = False` (the raw dict version). The exact same `__setitem__` override behaves differently on the two base classes because only `UserDict.__init__` routes through `__setitem__`.

## Common Mistakes

### Mistake 1: Subclassing `dict` and expecting `update` to call `__setitem__`

```python
class MyDict(dict):
    def __setitem__(self, k, v):
        print(f"set {k}={v}")
        super().__setitem__(k, v)

d = MyDict()
d.update({"a": 1, "b": 2})
# student expects two prints
```

**Symptom:** Zero prints. `d` is `{"a": 1, "b": 2}` but no `__setitem__` call fired.

**Why:** `dict.update` is implemented in C and writes directly to the hash table. It is performance-optimised; calling back into Python for every write would be measurably slower. The override exists for `d[k] = v` (the syntactic-sugar path) but not for `d.update(...)`, `dict(d, **other)`, `d.setdefault(k, default)`, or `d.__init__(other)`.

**Fix:** Subclass `UserDict`. `UserDict.update` is implemented in Python and routes every write through `self.__setitem__`, so the override fires consistently.

### Mistake 2: Forgetting that `UserList.__init__` does not call `self.append`

```python
class BoundedList(UserList):
    def __init__(self, init=None):
        super().__init__(init)
    def append(self, x):
        if len(self) >= 3: raise ValueError
        super().append(x)

bl = BoundedList([1, 2, 3, 4, 5])  # student expects ValueError
```

**Symptom:** No `ValueError`. `bl.data == [1, 2, 3, 4, 5]`.

**Why:** `UserList.__init__` calls `self.data.extend(init)`, not `self.extend(init)`. The `append` override only fires on `bl.append(...)` calls — not on the constructor path.

**Fix:** Override `__init__` to validate/truncate after `super().__init__` runs, or override `extend` (which `__init__` *does* call via `self.data.extend` — but `self.data.extend` is the *list's* extend, not your `extend`). The simplest fix is the post-hoc truncate shown in the lesson's `BoundedList.__init__`.

### Mistake 3: Using `UserString` when you really want `str` validation in `__new__`

```python
class HexStr(str):
    def __new__(cls, s):
        if not all(c in "0123456789abcdefABCDEF" for c in s):
            raise ValueError
        return super().__new__(cls, s)

hs = HexStr("deadBEEF") + HexStr("00")
# student expects the result to be a HexStr
```

**Symptom:** The concatenation `HexStr(...) + HexStr(...)` returns a plain `str`, not a `HexStr`. The student's mental model broke.

**Why:** `str.__add__` returns a plain `str`. Subclassing `str` for validated strings works for construction but the type is "lost" as soon as you operate on the value. `UserString` has the same limitation — `UserString.__add__` returns a `UserString`, but if you mix `UserString` and `str`, the result type depends on the order.

**Fix:** For "validated string that flows through operations", `UserString` is the right base but you need to override the binary operators. For "validated string that I just want to construct once and use as a `str`", subclass `str` in `__new__` and live with the type-loss on binary ops.

## Engineering Trade-Offs

**Decision:** Use `UserDict` / `UserList` / `UserString` whenever you override a write-path method (`__setitem__`, `__delitem__`, `append`, `extend`). Use the raw `dict` / `list` / `str` for everything else.

**Both sides:**

Raw `dict` / `list` / `str` wins on:

1. Speed. The C-implemented methods are 2–10× faster than the Python routes. `dict.update` on a million-item dict is meaningfully faster than `UserDict.update`.
2. Memory. `UserDict` carries an extra `self.data` reference; raw `dict` is one object.
3. JSON-friendliness. `json.dumps(d)` on a `dict` subclass is unambiguously a JSON object; on a `UserDict` subclass it works because `UserDict` is a `Mapping` and `json` checks `isinstance(..., Mapping)`.

`UserDict` / `UserList` / `UserString` wins on:

1. Override consistency. Every method routes through your overrides.
2. Pure-Python debuggability. You can `import pdb; pdb.set_trace()` inside `UserDict.update`; you cannot (practically) inside `dict.update`.
3. As the *recommended* base in the Python docs. The `dict` subclassing trap has bitten enough people that the docs say "subclass `UserDict` instead".

**Commitment:** `boardly/cidict.py` uses `UserDict` for `CaseInsensitiveDict` because the `__setitem__` override is the whole point. `boardly/models.py` uses `@dataclass` (not `UserList` or `UserDict`) for record types because data classes are about field shape, not method overriding. The rule: "Override a builtin write path? `UserDict` / `UserList` / `UserString`. Otherwise? `dict` / `list` / `str`."

## Exercises

1. **Exercise 1 — Confirm the trap on raw `dict`.** Subclass `dict`, override `__setitem__` to print, and call `d.update({"a": 1})`. Confirm no print. `Verify: uv run python -c "class D(dict):\n  def __setitem__(self, k, v):\n    print(f'set {k}')\n    super().__setitem__(k, v)\nd=D(); d.update({'a':1}); print(d)"`
2. **Exercise 2 — Confirm `UserDict` routes correctly.** Same override on `UserDict`, same `update` call. Confirm the print fires. `Verify: uv run python -c "from collections import UserDict\nclass D(UserDict):\n  def __setitem__(self, k, v):\n    print(f'set {k}')\n    super().__setitem__(k, v)\nd=D(); d.update({'a':1}); print(d)"`
3. **Exercise 3 — Inspect `.data`.** Build a `UserList([1, 2, 3])` and confirm `bl.data is not bl` and `bl.data == [1, 2, 3]`. `Verify: uv run python -c "from collections import UserList; u=UserList([1,2,3]); print(u.data, u.data is u)"`
4. **Exercise 4 — A `UserString` subclass.** Build a `PalindromeString(UserString)` that raises on construction if the input is not a palindrome. `Verify: uv run python -c "from collections import UserString\nclass P(UserString):\n  def __init__(self, s):\n    super().__init__(s)\n    if s != s[::-1]: raise ValueError('not palindrome')\nprint(P('racecar'))"`
5. **Exercise 5 — A `LimitedDict` with capacity.** Build a `UserDict` subclass that raises `ValueError` on the 1,001st distinct key. `Verify: uv run python -c "from collections import UserDict\nclass L(UserDict):\n  def __init__(self, cap=3, init=None):\n    super().__init__(init or {}); self._cap=cap\n  def __setitem__(self, k, v):\n    if k not in self.data and len(self.data) >= self._cap: raise ValueError('full')\n    super().__setitem__(k, v)\nd=L(3); d['a']=1; d['b']=2; d['c']=3\ntry:\n  d['d']=4\nexcept ValueError as e: print(e)"`

## Verification

```bash
$ uv run python boardly/cidict.py
--- CaseInsensitiveDict ---
"content-type" in h: True
h['Content-Type']: application/json
keys: ['content-type']

--- compare with raw dict subclass ---
buggy: "content-type" in d = False (should be True)

--- BoundedList ---
init: [1, 2, 3]
append(4) raised: capacity 3 exceeded

--- HexString ---
hex: deadBEEF
HexString('not hex') raised: not a hex string: 'not hex'
```

## Previously Learned Here

- [[04-collections/06-OrderedDict]] — `OrderedDict` is also a `dict` subclass, but its overrides are at the C level too (it just adds new methods like `move_to_end`). `UserDict` is the pure-Python alternative.
- [[04-collections/01-Counter]] — `Counter` is a `dict` subclass whose `__missing__` is overridden; that override *does* fire because it is a read-path override, not a write-path override. (The `dict.update` trap only affects write-path overrides.)
- [[04-collections/00-collections-MOC]] — the section map.

## What's Next

You have finished Section 04. Open [[05-collections-abc/00-collections-abc-MOC]] — Section 05 is the ABC hierarchy that lives at `collections.abc`. Where Section 04 was "concrete classes for common problems", Section 05 is "the abstract base classes those classes conform to" — `Iterable`, `Sequence`, `Mapping`, `Hashable`, and the rest of the tree that `isinstance` checks against. Section 05 is the bridge between Section 04 and the rest of the standard library; `dataclasses` leans on `Hashable`, `itertools` leans on `Iterable`, `functools` leans on `Callable`. By the end you will see the ABC hierarchy as the *type system* of the standard library.

## Sources

- **Python `collections.UserDict` documentation** — https://docs.python.org/3/library/collections.html#collections.UserDict — accessed 2026-10-23 — the canonical reference for `UserDict`, the `.data` attribute, and the explicit recommendation to subclass `UserDict` instead of `dict`.
- **Python `collections.UserList` documentation** — https://docs.python.org/3/library/collections.html#collections.UserList — accessed 2026-10-23 — the parallel reference for `UserList`.
- **Python `collections.UserString` documentation** — https://docs.python.org/3/library/collections.html#collections.UserString — accessed 2026-10-23 — the parallel reference for `UserString`.
- **Why `dict` subclassing is a trap — Python docs note** — https://docs.python.org/3/library/collections.html#userdict-objects — accessed 2026-10-23 — the paragraph that begins "If the user wants to extend `dict` ... the `UserDict` class is provided as a substitute for the `dict` class".

## What We Learned

- `UserDict` / `UserList` / `UserString` are pure-Python wrappers that hold the real storage in a `.data` attribute.
- The raw `dict` / `list` / `str` builtins are C-implemented; their methods (`update`, `__init__`, `setdefault`, etc.) bypass Python-level overrides like `__setitem__` for performance.
- `UserDict` routes every method through Python-level `__getitem__` / `__setitem__` / `__delitem__`, so your overrides actually fire on every path.
- `UserList.__init__` calls `self.data.extend(init)` — not `self.extend(init)` — so `append` overrides do not fire on the constructor path. You must override `__init__` to validate after construction.
- The rule: override a builtin write path → `UserDict` / `UserList` / `UserString`; otherwise → `dict` / `list` / `str`.
