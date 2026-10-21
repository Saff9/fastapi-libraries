---
title: "Lesson 01: The ABC Hierarchy"
aliases:
 - collections.abc
 - ABC hierarchy
tags:
 - collections-abc
 - abc
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[04-collections/07-UserDict-UserList-UserString]]"
related_lessons:
 - "[[05-collections-abc/02-Sequence-Mapping-Set]]"
 - "[[11-abc/01-ABC-and-abstractmethod]]"
first_taught_in: "05-collections-abc/01-The-ABC-Hierarchy"
---

# Lesson 01: The ABC Hierarchy

*The full tree of `collections.abc` — five roots (`Iterable`, `Container`, `Sized`, `Hashable`, `Callable`), `Collection` (3.6+, the union), `Reversible`, `Iterator`→`Generator`, `Sequence`/`MutableSequence`, `Mapping`/`MutableMapping`, `Set`/`MutableSet`, the views, and `Buffer` (3.12). Every concrete container in Section 04 is an instance of one or more of these.*

**You're at the very beginning of Section 05.**

This lesson is the map. Every later lesson in this section zooms into one branch of the tree — `Sequence` and its mixins, `Hashable` and the immutability contract, `Iterator` vs `Iterable`. Read this one first; the rest is depth on each subtree.

Take your time. Type every example. **This is how you learn.**

#collections-abc #abc #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Draw the ABC hierarchy from memory** — the five root ABCs, the three collection-tier ABCs, the mutable/immutable split.
2. **Identify which ABC a concrete container conforms to** — `deque` is a `MutableSequence`; `Counter` is a `Counter` (which is a `dict`, which is a `MutableMapping`).
3. **Use `isinstance(x, abc.X)`** to test conformance without importing the concrete class.
4. **Explain what changed in 3.6** (`Collection` was added) and **3.12** (`Buffer` was added).

## Prerequisites

Before starting, you need:

- **[[04-collections/07-UserDict-UserList-UserString]]** — comfort with the concrete `collections` classes that this section abstracts.
- **About 35 minutes of focused time.**

**The most common gap: confusing `collections.abc` with `collections`.**

`collections` (Section 04) is concrete classes: `Counter`, `deque`, `ChainMap`. `collections.abc` (this section) is *abstract base classes*: `Iterable`, `Sequence`, `Mapping`. They are different modules with different purposes. The `abc` submodule uses `isinstance` checks; the parent module uses concrete instances. Read this lesson with "abstract vs concrete" front of mind.

## The Problem

Here is the bug. `boardly` has a function that accepts "something list-like":

```python
def total_priority(tickets) -> int:
    return sum(t.priority for t in tickets)
```

This works on a `list[Ticket]`, a `deque[Ticket]`, a `tuple[Ticket, ...]`, a generator, a set. But the type annotation is missing — `tickets` could be anything. A reviewer asks "what does this accept?" and the answer is "iterable of tickets, where each ticket has a `.priority` attribute". How do we encode that?

The first attempt — `tickets: list[Ticket]` — is too narrow. It rejects `deque[Ticket]`, which is a valid input from the audit log. The second attempt — `tickets: Iterable[Ticket]` (from `collections.abc`) — is correct. It says "anything with `__iter__` that yields tickets".

```python
from collections.abc import Iterable
from boardly.models import Ticket

def total_priority(tickets: Iterable[Ticket]) -> int:
    return sum(t.priority for t in tickets)
```

The `Iterable` annotation comes from `collections.abc`. It is an abstract base class that `list`, `tuple`, `set`, `deque`, `dict` (iterates keys), `str` (iterates characters), generators, and any user class with `__iter__` all conform to. This lesson walks the full hierarchy it belongs to.

## The Code

```python
# boardly/abc_demo.py
"""Walk the collections.abc hierarchy with isinstance checks."""
from collections.abc import (
    Iterable, Container, Sized, Hashable, Callable,
    Iterator, Reversible, Generator,
    Collection, Sequence, MutableSequence,
    Mapping, MutableMapping,
    Set, MutableSet,
    ByteString, Buffer,
    ItemsView, KeysView, ValuesView,
)
from collections import Counter, deque, ChainMap, OrderedDict, defaultdict
from boardly.models import Ticket
from uuid import uuid4


def report(obj, label):
    print(f"{label:30s} -> ", end="")
    checks = [
        ("Iterable",     isinstance(obj, Iterable)),
        ("Container",    isinstance(obj, Container)),
        ("Sized",        isinstance(obj, Sized)),
        ("Hashable",     isinstance(obj, Hashable)),
        ("Callable",     isinstance(obj, Callable)),
        ("Collection",   isinstance(obj, Collection)),
        ("Iterator",     isinstance(obj, Iterator)),
        ("Reversible",   isinstance(obj, Reversible)),
        ("Generator",    isinstance(obj, Generator)),
        ("Sequence",     isinstance(obj, Sequence)),
        ("MutableSeq",   isinstance(obj, MutableSequence)),
        ("Mapping",      isinstance(obj, Mapping)),
        ("MutableMap",   isinstance(obj, MutableMapping)),
        ("Set",          isinstance(obj, Set)),
        ("MutableSet",   isinstance(obj, MutableSet)),
        ("ByteString",   isinstance(obj, ByteString)),
        ("Buffer",       isinstance(obj, Buffer)),
    ]
    yes = [name for name, ok in checks if ok]
    print(", ".join(yes) or "(none)")


if __name__ == "__main__":
    print("--- The five root ABCs and what conforms ---")
    report(42,                 "int")
    report("hello",           "str")
    report([1, 2, 3],          "list")
    report((1, 2, 3),         "tuple")
    report({1, 2, 3},          "set")
    report({"a": 1},           "dict")
    report(deque([1, 2, 3]),  "deque")
    report(Counter("aaabb"),   "Counter")
    report(lambda x: x,        "lambda")

    print("\n--- ChainMap and OrderedDict are Mappings ---")
    report(ChainMap({"a": 1}), "ChainMap")
    report(OrderedDict({"a": 1}), "OrderedDict")
    report(defaultdict(list),  "defaultdict")

    print("\n--- Generators and iterators ---")
    gen = (x for x in [1, 2, 3])
    report(gen, "generator expr")

    print("\n--- The views ---")
    d = {"a": 1, "b": 2}
    report(d.keys(),  "dict.keys()")
    report(d.values(),"dict.values()")
    report(d.items(), "dict.items()")

    print("\n--- Buffer (3.12) ---")
    report(b"hello", "bytes")
    report(bytearray(b"hi"), "bytearray")
    report(memoryview(b"hi"), "memoryview")
```

## Line-by-Line Deep Dive

### Lines 1–13: The import block — every public ABC

```python
# boardly/abc_demo.py
"""Walk the collections.abc hierarchy with isinstance checks."""
from collections.abc import (
    Iterable, Container, Sized, Hashable, Callable,
    Iterator, Reversible, Generator,
    Collection, Sequence, MutableSequence,
    Mapping, MutableMapping,
    Set, MutableSet,
    ByteString, Buffer,
    ItemsView, KeysView, ValuesView,
)
```

Every name here is an ABC. The import is grouped by subtree to make the hierarchy visible:

- **The five roots** (`Iterable`, `Container`, `Sized`, `Hashable`, `Callable`) — every other ABC descends from one or more of these.
- **The collection-tier** (`Collection`) — the union of `Iterable` + `Container` + `Sized`, added in 3.6.
- **The iterator subtree** (`Iterator`, `Reversible`, `Generator`) — `Iterator` extends `Iterable`; `Generator` extends `Iterator`.
- **The sequence subtree** (`Sequence`, `MutableSequence`, `ByteString`).
- **The mapping subtree** (`Mapping`, `MutableMapping`).
- **The set subtree** (`Set`, `MutableSet`).
- **`Buffer`** — its own root, added in 3.12 (PEP 688). Does not descend from the other roots.
- **The dict views** (`ItemsView`, `KeysView`, `ValuesView`) — `KeysView` and `ItemsView` are both `Mapping` and `Set`; `ValuesView` is `Mapping` only.

### Lines 17–35: The `report` helper

```python
def report(obj, label):
    print(f"{label:30s} -> ", end="")
    checks = [
        ("Iterable",     isinstance(obj, Iterable)),
        ("Container",    isinstance(obj, Container)),
        ("Sized",        isinstance(obj, Sized)),
        ("Hashable",     isinstance(obj, Hashable)),
        ("Callable",     isinstance(obj, Callable)),
        ("Collection",   isinstance(obj, Collection)),
        ("Iterator",     isinstance(obj, Iterator)),
        ("Reversible",   isinstance(obj, Reversible)),
        ("Generator",    isinstance(obj, Generator)),
        ("Sequence",     isinstance(obj, Sequence)),
        ("MutableSeq",   isinstance(obj, MutableSequence)),
        ("Mapping",      isinstance(obj, Mapping)),
        ("MutableMap",   isinstance(obj, MutableMapping)),
        ("Set",          isinstance(obj, Set)),
        ("MutableSet",   isinstance(obj, MutableSet)),
        ("ByteString",   isinstance(obj, ByteString)),
        ("Buffer",       isinstance(obj, Buffer)),
    ]
    yes = [name for name, ok in checks if ok]
    print(", ".join(yes) or "(none)")
```

`isinstance(obj, Iterable)` returns `True` if `obj`'s class (or any of its MRO) is registered as a virtual subclass of `Iterable`. The registration is *structural* — `collections.abc` uses `__subclasshook__` to check whether the candidate class has the right method (`__iter__` for `Iterable`, `__len__` for `Sized`, etc.). That is the magic that lets `isinstance(my_class_with_iter, Iterable)` return `True` even if `my_class_with_iter` did not explicitly inherit from `Iterable`.

**Why is `isinstance(obj, Iterable)` better than `hasattr(obj, '__iter__')`?** Three reasons:

1. It is *semantic*. `hasattr(obj, '__iter__')` returns `True` if `obj` has any attribute named `__iter__`, including a non-callable one. The ABC check goes through `ABCMeta.__instancecheck__`, which consults `__subclasshook__`, which checks the type's MRO *and* the method's presence.
2. It composes. `isinstance(obj, Sequence)` checks for the *combination* of methods `__getitem__` and `__len__` — not just one.
3. It documents intent. `isinstance(obj, Iterable)` in a function body says "I need this thing to be iterable" — clearer than `hasattr(obj, '__iter__')`.

### Lines 38–48: Smoke test — the concrete containers

```python
if __name__ == "__main__":
    print("--- The five root ABCs and what conforms ---")
    report(42,                 "int")
    report("hello",           "str")
    report([1, 2, 3],          "list")
    report((1, 2, 3),         "tuple")
    report({1, 2, 3},          "set")
    report({"a": 1},           "dict")
    report(deque([1, 2, 3]),  "deque")
    report(Counter("aaabb"),   "Counter")
    report(lambda x: x,        "lambda")
```

The smoke test walks the most common concrete types and prints which ABCs they conform to. The output (see Execution Trace) is the entire hierarchy's behaviour on real instances — read it as a lookup table.

### Lines 50–56: `ChainMap`, `OrderedDict`, `defaultdict` are all `Mapping`s

```python
    print("\n--- ChainMap and OrderedDict are Mappings ---")
    report(ChainMap({"a": 1}), "ChainMap")
    report(OrderedDict({"a": 1}), "OrderedDict")
    report(defaultdict(list),  "defaultdict")
```

All three concrete mapping classes from Section 04 conform to `MutableMapping`. That is the contract that lets code say `isinstance(x, Mapping)` and accept any of them.

### Lines 60–62: Generators conform to `Iterator` and `Generator`

```python
    print("\n--- Generators and iterators ---")
    gen = (x for x in [1, 2, 3])
    report(gen, "generator expr")
```

A generator expression yields a `generator` object. That object conforms to `Generator` (and therefore `Iterator`, and therefore `Iterable`). The full chain is `Iterable` → `Iterator` → `Generator`.

### Lines 65–69: Dict views

```python
    print("\n--- The views ---")
    d = {"a": 1, "b": 2}
    report(d.keys(),  "dict.keys()")
    report(d.values(),"dict.values()")
    report(d.items(), "dict.items()")
```

`d.keys()` conforms to `KeysView` (which extends `Set`), so you can do set operations on dict keys (`d.keys() & {"a", "b"}`). `d.items()` is `ItemsView`, which also extends `Set`. `d.values()` is `ValuesView`, which extends `Collection` only — *not* a `Set` (because dict values may be unhashable and may repeat) and *not* a `Mapping`. Some Python documentation summaries list `ItemsView` and `ValuesView` as extending `Mapping`; the actual 3.12 source shows `ItemsView(MappingView, Set)`, `KeysView(MappingView, Set)`, and `ValuesView(MappingView, Collection)` — none of them extend `Mapping`. The C-level `dict_keys` / `dict_items` / `dict_values` types are registered as virtual subclasses of the corresponding ABCs (`isinstance(d.keys(), KeysView)` is `True`), but `isinstance(d.keys(), Mapping)` is `False`.

### Lines 71–75: `Buffer` (3.12)

```python
    print("\n--- Buffer (3.12) ---")
    report(b"hello", "bytes")
    report(bytearray(b"hi"), "bytearray")
    report(memoryview(b"hi"), "memoryview")
```

`bytes`, `bytearray`, and `memoryview` all conform to `Buffer`. The `Buffer` ABC was added in Python 3.12 (PEP 688) to give the buffer protocol a first-class type. It is its own root — it does not descend from `Iterable` or `Sized`, even though `bytes` happens to be both. `Buffer` is purely about the buffer protocol (the C-level `tp_buffer` slot); it has no methods on the ABC itself.

**Python 3.14+:** `collections.abc.ByteString` is deprecated as of 3.12 and is slated for removal in 3.14. Use `collections.abc.Buffer` (or `typing.Buffer` on 3.12+) in new annotations. The smoke test still checks `ByteString` because it is part of the hierarchy in 3.12, but importing it will raise a `DeprecationWarning`.

## Execution Trace

```bash
$ uv run python boardly/abc_demo.py
--- The five root ABCs and what conforms ---
int                            -> Hashable
str                            -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence
list                           -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq
tuple                          -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence
set                            -> Iterable, Container, Sized, Collection, Set, MutableSet
dict                           -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
deque                          -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq
Counter                        -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
lambda                         -> Hashable, Callable

--- ChainMap and OrderedDict are Mappings ---
ChainMap                       -> Iterable, Container, Sized, Collection, Mapping, MutableMap
OrderedDict                    -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
defaultdict                    -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap

--- Generators and iterators ---
generator expr                 -> Iterable, Hashable, Iterator, Generator

--- The views ---
dict.keys()                    -> Iterable, Container, Sized, Collection, Reversible, Set
dict.values()                  -> Iterable, Container, Sized, Hashable, Collection, Reversible
dict.items()                   -> Iterable, Container, Sized, Collection, Reversible, Set

--- Buffer (3.12) ---
bytes                          -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence, ByteString, Buffer
bytearray                      -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq, ByteString, Buffer
memoryview                     -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence, Buffer
```

stderr (Python 3.12):
```
boardly/abc_demo.py:35: DeprecationWarning: 'collections.abc.ByteString' is deprecated and slated for removal in Python 3.14
  ("ByteString",   isinstance(obj, ByteString)),
```

(The warning fires once per `isinstance` call against `ByteString` — Python's default filter deduplicates identical warnings, so under default warning filters only the first call surfaces it. Run with `python -W all` to see the full chain.)

Read the trace as a lookup table. The order of ABCs in each line follows the order in the `checks` list — `Iterable`, `Container`, `Sized`, `Hashable`, `Callable`, `Collection`, `Iterator`, `Reversible`, `Generator`, `Sequence`, `MutableSeq`, `Mapping`, `MutableMap`, `Set`, `MutableSet`, `ByteString`, `Buffer`. A few things to notice:

1. `lambda` is *both* `Hashable` and `Callable`. `Hashable` is structural: `isinstance(x, Hashable)` returns `True` whenever `type(x).__hash__` is not `None`. Functions inherit `object.__hash__` (which is id-based), so they are hashable.
2. `generator expr` is `Hashable` for the same reason — generators use the default id-based hash.
3. `dict.values()` is `Hashable` because `dict_values` has no `__hash__ = None` override (its instances are technically hashable by id, even though dict_values objects are rarely used as dict keys).
4. `dict.keys()` and `dict.items()` are `Set` but *not* `Mapping`. `dict.values()` is neither `Mapping` nor `Set` — only `Collection`.
5. `ByteString` raises a `DeprecationWarning` in 3.12 (it is slated for removal in 3.14). The smoke test still includes it for completeness, but new code should use `Buffer`.

## Common Mistakes

### Mistake 1: Using `isinstance(x, list)` when you mean `isinstance(x, Sequence)`

```python
def first(items) -> object:
    if not isinstance(items, list):
        raise TypeError("expected a list")
    return items[0]
```

**Symptom:** The function rejects `tuple`, `deque`, `range`, custom sequences — anything that is not a literal `list`.

**Why:** `list` is a concrete type. `Sequence` is the ABC for "anything indexable and sized". The contract of `first()` is "give me something I can index and read length from" — that is `Sequence`, not `list`.

**Fix:** `isinstance(items, Sequence)`. Or, even better, type-annotate `items: Sequence` and let static checkers enforce it.

### Mistake 2: Using `Iterable` when you mean `Collection`

```python
def nonempty(items: Iterable) -> bool:
    return len(items) > 0   # student expects this to work
```

**Symptom:** `TypeError: object of type 'generator' has no len()` when `items` is a generator.

**Why:** `Iterable` only guarantees `__iter__`. `len()` requires `__len__`, which is the `Sized` ABC. Generators are `Iterable` but not `Sized`. The intersection of `Iterable` + `Sized` + `Container` is `Collection` (3.6+).

**Fix:** Either annotate `items: Collection` (so callers cannot pass a generator) or restructure the function to consume the iterable: `return any(True for _ in items)`.

### Mistake 3: Forgetting `Buffer` is its own root

```python
from collections.abc import Iterable, Buffer
def process(b: Iterable[int]) -> None: ...
process(b"hello")   # student expects TypeError
```

**Symptom:** No error — `bytes` happens to be `Iterable[int]` (it iterates `int`s). The function processes the bytes one byte at a time, which is not what the caller wanted.

**Why:** `bytes` conforms to *both* `Iterable` (yielding `int`) and `Buffer` (the 3.12 ABC for the buffer protocol). The two are independent; `bytes` happens to satisfy both. If your function actually wants the buffer protocol (zero-copy slicing, `memoryview`-style access), annotate as `Buffer` not `Iterable[int]`.

**Fix:** Use `collections.abc.Buffer` (3.12+) for the buffer-protocol contract. For older Python, `typing.Union[bytes, bytearray, memoryview]` is the honest approximation.

## Engineering Trade-Offs

**Decision:** Use `collections.abc` ABCs for `isinstance` checks and for type annotations on functions that accept "any X-like thing". Use concrete classes (`list`, `dict`, `deque`) only when you specifically need that class's extras.

**Both sides:**

Concrete classes win on:

1. Construction clarity — `list(x)` makes a list; readers do not have to think.
2. Specific behaviour — `list.pop(0)` is O(n) and you want that fact visible; `Sequence.pop` does not exist as a mixin method on the ABC.
3. Pickling and copy — concrete classes pickle cleanly; ABCs do not (you cannot pickle "a Sequence").

`collections.abc` wins on:

1. Generality — a function annotated `Sequence` accepts `list`, `tuple`, `deque`, `range`, custom sequences.
2. Documentation — the type annotation *is* the contract.
3. Subclassing — your custom class inherits the ABC's mixin methods (next lesson).

**Commitment:** `boardly` uses ABCs for function signatures (`Iterable`, `Sequence`, `Mapping`, `Hashable`) and concrete classes for instantiation (`list()`, `dict()`, `deque()`). The rule: "Type-annotate with ABCs; construct with concretes."

## Exercises

1. **Exercise 1 — Verify `deque` is a `MutableSequence`.** Run `isinstance(deque(), MutableSequence)`. `Verify: uv run python -c "from collections import deque; from collections.abc import MutableSequence; print(isinstance(deque(), MutableSequence))"`
2. **Exercise 2 — A `Buffer` instance.** Confirm `isinstance(b'x', Buffer)` is `True`. `Verify: uv run python -c "from collections.abc import Buffer; print(isinstance(b'x', Buffer))"`
3. **Exercise 3 — `set` is a `MutableSet`.** Run `isinstance(set(), Set)` and `isinstance(set(), MutableSet)`. `Verify: uv run python -c "from collections.abc import Set, MutableSet; print(isinstance(set(), Set), isinstance(set(), MutableSet))"`
4. **Exercise 4 — `Generator` is `Iterator` is `Iterable`.** Confirm `g = (x for x in [1])` conforms to all three. `Verify: uv run python -c "from collections.abc import Iterable, Iterator, Generator; g=(x for x in [1]); print(isinstance(g, Iterable), isinstance(g, Iterator), isinstance(g, Generator))"`
5. **Exercise 5 — A custom class that conforms to `Iterable`.** Write `class MyIter: def __iter__(self): return iter([1,2,3])` and confirm `isinstance(MyIter(), Iterable)` is `True` without inheriting. `Verify: uv run python -c "from collections.abc import Iterable\nclass M:\n  def __iter__(self):\n    return iter([1,2,3])\nprint(isinstance(M(), Iterable))"`

## Verification

```bash
$ uv run python boardly/abc_demo.py
--- The five root ABCs and what conforms ---
int                            -> Hashable
str                            -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence
list                           -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq
tuple                          -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence
set                            -> Iterable, Container, Sized, Collection, Set, MutableSet
dict                           -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
deque                          -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq
Counter                        -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
lambda                         -> Hashable, Callable

--- ChainMap and OrderedDict are Mappings ---
ChainMap                       -> Iterable, Container, Sized, Collection, Mapping, MutableMap
OrderedDict                    -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap
defaultdict                    -> Iterable, Container, Sized, Collection, Reversible, Mapping, MutableMap

--- Generators and iterators ---
generator expr                 -> Iterable, Hashable, Iterator, Generator

--- The views ---
dict.keys()                    -> Iterable, Container, Sized, Collection, Reversible, Set
dict.values()                  -> Iterable, Container, Sized, Hashable, Collection, Reversible
dict.items()                   -> Iterable, Container, Sized, Collection, Reversible, Set

--- Buffer (3.12) ---
bytes                          -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence, ByteString, Buffer
bytearray                      -> Iterable, Container, Sized, Collection, Reversible, Sequence, MutableSeq, ByteString, Buffer
memoryview                     -> Iterable, Container, Sized, Hashable, Collection, Reversible, Sequence, Buffer
```

## Previously Learned Here

- [[04-collections/07-UserDict-UserList-UserString]] — the concrete classes that this section abstracts.
- [[04-collections/00-collections-MOC]] — Section 04 overview.

## What's Next

[[05-collections-abc/02-Sequence-Mapping-Set]] — the mixin methods each ABC provides. Implement `__getitem__` and `__len__` on a custom class, inherit from `Sequence`, and you get `__contains__`, `__iter__`, `__reversed__`, `index`, `count` for free. That is the magic of `collections.abc` — and the reason FastAPI can accept "any mapping-like" config object without writing five different code paths.

## Sources

- **Python `collections.abc` documentation** — https://docs.python.org/3/library/collections.abc.html — accessed 2026-10-23 — the canonical reference for the entire hierarchy, with a table of which abstract methods each ABC requires and which mixin methods it provides.
- **PEP 3119 — Introducing Abstract Base Classes** — https://peps.python.org/pep-3119/ — accessed 2026-10-23 — the original ABC PEP; the design rationale.
- **PEP 688 — `Buffer` ABC (3.12)** — https://peps.python.org/pep-0688/ — accessed 2026-10-23 — the PEP that added `Buffer` as a first-class ABC.

## What We Learned

- Five root ABCs: `Iterable`, `Container`, `Sized`, `Hashable`, `Callable`. Every other ABC descends from one or more of these.
- `Collection` (3.6+) is the union of `Iterable` + `Container` + `Sized`.
- `Sequence` / `MutableSequence`, `Mapping` / `MutableMapping`, `Set` / `MutableSet` are the three "mutable / immutable" subtrees.
- `Iterator` extends `Iterable`; `Generator` extends `Iterator`.
- `Buffer` (3.12) is its own root for the buffer protocol.
- `isinstance(x, abc.X)` uses `__subclasshook__` for structural checks — your class does not have to inherit to conform.
- Annotate function signatures with ABCs; construct with concrete classes.
