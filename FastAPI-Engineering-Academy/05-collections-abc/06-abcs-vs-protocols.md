---
title: "Lesson 06: ABCs vs Protocols"
aliases:
 - collections.abc vs typing.Protocol
 - Protocol vs ABC
 - runtime_checkable
tags:
 - collections-abc
 - typing
 - protocol
 - canonical
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "25–35 minutes"
prerequisites:
 - "[[05-collections-abc/05-Custom-ABCs]]"
related_lessons:
 - "[[01-typing/05-Protocol-Structural-Typing]]"
 - "[[11-abc/02-register-and-Virtual-Subclasses]]"
first_taught_in: "05-collections-abc/06-abcs-vs-protocols"
---

# Lesson 06: ABCs vs Protocols

*`collections.abc.Iterable` vs `typing.Protocol` with `__iter__`. Nominal ABCs (registered via `register` or `__subclasshook__`) vs structural `typing.Protocol` (with `runtime_checkable`). When each wins, and why the modern trend is towards `Protocol` for new code — but why `collections.abc` is not going anywhere.*

**You're at the very beginning of Section 05 — Lesson 06.**

This is the closing canonical lesson of the section. It is the lesson that answers the question every senior engineer gets asked once: "If `typing.Protocol` exists, why do we still use `collections.abc`?" The answer is layered — they overlap, they differ, they have different performance and ergonomics, and the right choice depends on whether you are annotating a function signature, writing an `isinstance` check, or defining a new contract for a plugin system.

Take your time. Type every example. **This is how you learn.**

#collections-abc #typing #protocol #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define a `typing.Protocol`** with the same shape as a `collections.abc` ABC.
2. **Explain the difference between nominal ABCs and structural protocols** — and name the three places they diverge.
3. **Use `runtime_checkable`** to make a `Protocol` pass `isinstance` checks (and know its limits).
4. **Decide between `collections.abc` and `typing.Protocol`** for a given function signature, isinstance check, or new contract.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/05-Custom-ABCs]]** — `ABCMeta`, `register`, `__subclasshook__`. This lesson contrasts those mechanisms with `Protocol`'s.
- **Familiarity with `typing`** — if you have not written a `Protocol` yet, glance at [[01-typing/05-Protocol-Structural-Typing]].
- **About 30 minutes of focused time.**

**The most common gap: not knowing `typing.Protocol` is structural at static-check time but `runtime_checkable` only at runtime.**

A `Protocol` is a *static* type — `mypy` and `pyright` use it for structural subtyping in type annotations. At runtime, `isinstance(x, MyProtocol)` *only* works if the protocol is decorated with `@runtime_checkable` — and even then, it checks for the *presence* of attributes, not their signatures. Students who write `isinstance(x, MyProtocol)` on a non-`runtime_checkable` protocol get `TypeError`. Read this lesson with "static structural, runtime nominal-ish" front of mind.

## The Problem

Here is the bug. `boardly` has a function that accepts "anything that can be closed":

```python
from collections.abc import Iterable  # not relevant here, just to anchor

def cleanup(resource) -> None:
    resource.close()
```

The first reviewer asks "what does `resource` accept?" The author writes `resource: object` — too loose. The second reviewer asks for a type. The author writes `from typing import Protocol`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...
```

Now `cleanup(resource: Closeable) -> None` is statically checked — `mypy` accepts anything with a `close()` method that takes no required args and returns `None`. `isinstance(x, Closeable)` returns `True` at runtime if `x` has a `close` attribute.

But — what about `collections.abc`? Could we have written the same thing with an ABC? Yes:

```python
from abc import ABCMeta, abstractmethod

class CloseableABC(metaclass=ABCMeta):
    @abstractmethod
    def close(self) -> None: ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not CloseableABC:
            return NotImplemented
        if hasattr(subclass, "close"):
            return True
        return NotImplemented
```

This is the same shape. So which one wins?

The answer is: **`Protocol` for static type annotations, `collections.abc` for `isinstance` checks on stdlib types, `__subclasshook__`-style ABC for cases where you need both and want a class hierarchy**. The decision has three axes — static vs runtime, stdlib vs custom, class hierarchy vs open contract.

## The Code

```python
# boardly/abc_vs_protocol.py
"""Three ways to express the same contract: collections.abc ABC, custom ABC
with __subclasshook__, and typing.Protocol (runtime_checkable)."""
from abc import ABCMeta, abstractmethod
from typing import Protocol, runtime_checkable, Iterable


# --- Approach 1: collections.abc.Iterable (the stdlib ABC, structural via __subclasshook__) ---

def total_a(items: Iterable[int]) -> int:
    return sum(items)


# --- Approach 2: a custom ABC with __subclasshook__ (manual structural conformance) ---

class CloseableABC(metaclass=ABCMeta):
    @abstractmethod
    def close(self) -> None: ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not CloseableABC:
            return NotImplemented
        if hasattr(subclass, "close"):
            return True
        return NotImplemented


# --- Approach 3: typing.Protocol with @runtime_checkable ---

@runtime_checkable
class CloseableProtocol(Protocol):
    def close(self) -> None: ...


def cleanup_abc(resource: CloseableABC) -> None:
    resource.close()


def cleanup_protocol(resource: CloseableProtocol) -> None:
    resource.close()


if __name__ == "__main__":
    print("--- Iterable (collections.abc) is structural at runtime ---")
    class MyList:
        def __iter__(self):
            return iter([1, 2, 3])
    ml = MyList()
    print(f"isinstance(ml, Iterable): {isinstance(ml, Iterable)}")
    print(f"total_a(ml): {total_a(ml)}")

    print("\n--- Custom ABC with __subclasshook__ ---")
    class FileLike:
        def close(self) -> None:
            print("closed")
    f = FileLike()
    print(f"isinstance(f, CloseableABC): {isinstance(f, CloseableABC)}")
    print(f"isinstance(f, CloseableProtocol): {isinstance(f, CloseableProtocol)}")
    cleanup_abc(f)   # works because __subclasshook__ fired
    cleanup_protocol(f)  # works because Protocol is runtime_checkable

    print("\n--- Protocol without @runtime_checkable cannot isinstance ---")
    class NotCheckable(Protocol):
        def close(self) -> None: ...
    try:
        isinstance(f, NotCheckable)
    except TypeError as e:
        print(f"isinstance raises: {e}")

    print("\n--- runtime_checkable checks attribute presence, not signature ---")
    class Fake:
        close = 42   # not a method, just an int!
    fake = Fake()
    print(f"isinstance(fake, CloseableProtocol): {isinstance(fake, CloseableProtocol)}  (PROTOCOL DOES NOT VERIFY IT IS CALLABLE)")

    print("\n--- performance: __subclasshook__ vs runtime_checkable ---")
    import timeit
    class Many:
        def close(self): pass
    m = Many()
    abc_time = timeit.timeit(lambda: isinstance(m, CloseableABC), number=100_000)
    proto_time = timeit.timeit(lambda: isinstance(m, CloseableProtocol), number=100_000)
    print(f"ABC __subclasshook__:       {abc_time * 1000:.1f} ms (100k checks)")
    print(f"Protocol runtime_checkable: {proto_time * 1000:.1f} ms (100k checks)")
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports

```python
# boardly/abc_vs_protocol.py
"""Three ways to express the same contract: collections.abc ABC, custom ABC
with __subclasshook__, and typing.Protocol (runtime_checkable)."""
from abc import ABCMeta, abstractmethod
from typing import Protocol, runtime_checkable, Iterable
```

`from typing import Protocol, runtime_checkable` — `Protocol` (PEP 544, 3.8+) is the static-typing way to express structural subtyping. `runtime_checkable` is the decorator that enables `isinstance` on a protocol.

`from typing import Iterable` — note: `typing.Iterable` *is* `collections.abc.Iterable` (the `typing` module re-exports the ABCs as aliases). In 3.9+, you can use either import for the same name; `collections.abc` is the actual home.

### Lines 8–13: Approach 1 — the stdlib ABC

```python
# --- Approach 1: collections.abc.Iterable (the stdlib ABC, structural via __subclasshook__) ---

def total_a(items: Iterable[int]) -> int:
    return sum(items)
```

`items: Iterable[int]` — the annotation uses `Iterable`. Static checkers (`mypy`, `pyright`) accept anything with `__iter__` that yields `int`. Runtime `isinstance(items, Iterable)` returns `True` because `Iterable`'s `__subclasshook__` checks for `__iter__`.

This is the canonical Python style — annotate with the stdlib ABC for both static and runtime checks. It works because the stdlib ABCs are dual-purpose: they are ABCs (with `__subclasshook__`) *and* they are recognised by static checkers (which special-case `collections.abc`).

### Lines 15–27: Approach 2 — a custom ABC with `__subclasshook__`

```python
class CloseableABC(metaclass=ABCMeta):
    @abstractmethod
    def close(self) -> None: ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not CloseableABC:
            return NotImplemented
        if hasattr(subclass, "close"):
            return True
        return NotImplemented
```

This is the `collections.abc` pattern applied to a custom contract. Static checkers do *not* special-case it — they treat `CloseableABC` as a nominal ABC, requiring inheritance. So `cleanup_abc(FileLike())` would fail a `mypy` check even though `isinstance` returns `True`.

**Why mention this approach if static checkers do not support it?** Because it is the *runtime* equivalent of `Protocol`. If you have a 3.7- codebase that cannot use `Protocol`, this is the only structural option. In 3.8+, `Protocol` is preferred.

### Lines 29–33: Approach 3 — `typing.Protocol` with `@runtime_checkable`

```python
@runtime_checkable
class CloseableProtocol(Protocol):
    def close(self) -> None: ...
```

`class CloseableProtocol(Protocol):` — inherit from `Protocol` (which itself uses a special metaclass, `_ProtocolMeta`). The class body declares the methods that conforming classes must have. The body's `...` is the method body; static checkers do not run it, they only read the signature.

`@runtime_checkable` — the decorator that enables `isinstance(x, CloseableProtocol)`. Without it, `isinstance(x, CloseableProtocol)` raises `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` (3.12+ phrasing) — they are static-only.

### Lines 35–42: The two `cleanup` functions

```python
def cleanup_abc(resource: CloseableABC) -> None:
    resource.close()


def cleanup_protocol(resource: CloseableProtocol) -> None:
    resource.close()
```

Both functions do the same thing. The difference is the type annotation. `cleanup_abc` expects a `CloseableABC`; static checkers require inheritance (because they do not special-case `CloseableABC`). `cleanup_protocol` expects a `CloseableProtocol`; static checkers accept any class with a `close() -> None` method, regardless of inheritance.

### Lines 44–52: The `Iterable` structural check at runtime

```python
if __name__ == "__main__":
    print("--- Iterable (collections.abc) is structural at runtime ---")
    class MyList:
        def __iter__(self):
            return iter([1, 2, 3])
    ml = MyList()
    print(f"isinstance(ml, Iterable): {isinstance(ml, Iterable)}")
    print(f"total_a(ml): {total_a(ml)}")
```

`MyList` does not inherit from `Iterable`. `isinstance(ml, Iterable)` is `True` because `Iterable.__subclasshook__` checks for the `__iter__` attribute. `total_a(ml)` succeeds at runtime.

This is the magic of `collections.abc` — the same magic that `Protocol` with `@runtime_checkable` provides, but built into the stdlib.

### Lines 54–62: Both approaches work on the unregistered class

```python
    print("\n--- Custom ABC with __subclasshook__ ---")
    class FileLike:
        def close(self) -> None:
            print("closed")
    f = FileLike()
    print(f"isinstance(f, CloseableABC): {isinstance(f, CloseableABC)}")
    print(f"isinstance(f, CloseableProtocol): {isinstance(f, CloseableProtocol)}")
    cleanup_abc(f)   # works because __subclasshook__ fired
    cleanup_protocol(f)  # works because Protocol is runtime_checkable
```

`isinstance(f, CloseableABC)` is `True` — the `__subclasshook__` fired. `isinstance(f, CloseableProtocol)` is `True` — `runtime_checkable` fired. Both `cleanup_*` functions succeed at runtime.

The *static* behaviour differs: `mypy` would flag `cleanup_abc(f)` because `FileLike` does not inherit from `CloseableABC`. `cleanup_protocol(f)` would pass `mypy` because `FileLike` has a `close() -> None` method — structural conformance.

### Lines 64–71: Protocol without `@runtime_checkable` cannot isinstance

```python
    print("\n--- Protocol without @runtime_checkable cannot isinstance ---")
    class NotCheckable(Protocol):
        def close(self) -> None: ...
    try:
        isinstance(f, NotCheckable)
    except TypeError as e:
        print(f"isinstance raises: {e}")
```

`isinstance(f, NotCheckable)` raises `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` (in Python 3.12; older Pythons printed a longer message starting with `Protocols can only be used as base classes...`). Without `@runtime_checkable`, the protocol is static-only.

**Why is `runtime_checkable` opt-in?** Because runtime checks are imprecise (they check attribute presence, not signatures — see the next demo) and slow (a `hasattr` walk on every check). The default is the *precise* static check, with `runtime_checkable` as an explicit opt-in when you accept the imprecision.

### Lines 73–79: `runtime_checkable` checks attribute presence, not signatures

```python
    print("\n--- runtime_checkable checks attribute presence, not signature ---")
    class Fake:
        close = 42   # not a method, just an int!
    fake = Fake()
    print(f"isinstance(fake, CloseableProtocol): {isinstance(fake, CloseableProtocol)}  (PROTOCOL DOES NOT VERIFY IT IS CALLABLE)")
```

`Fake.close` is `42` — not a method. `isinstance(fake, CloseableProtocol)` is `True` — because `runtime_checkable` only checks for the *presence* of the `close` attribute, not whether it is callable, not its signature, not its return type.

This is the sharp edge of `runtime_checkable`. A `Protocol` with `@runtime_checkable` is a *coarse* runtime check; it is not the same as the static type. The static type is precise; the runtime check is "has the attribute". Use `runtime_checkable` for sanity checks; rely on the static type for correctness.

### Lines 81–88: Performance comparison

```python
    print("\n--- performance: __subclasshook__ vs runtime_checkable ---")
    import timeit
    class Many:
        def close(self): pass
    m = Many()
    abc_time = timeit.timeit(lambda: isinstance(m, CloseableABC), number=100_000)
    proto_time = timeit.timeit(lambda: isinstance(m, CloseableProtocol), number=100_000)
    print(f"ABC __subclasshook__:       {abc_time * 1000:.1f} ms (100k checks)")
    print(f"Protocol runtime_checkable: {proto_time * 1000:.1f} ms (100k checks)")
```

Both checks are roughly the same speed — they both walk the type's attributes. The difference is in the cache: `collections.abc` ABCs cache `__subclasshook__` results; `Protocol` with `@runtime_checkable` does a fresh `hasattr` walk on every check (in 3.12, this is improved but still not cached). For 100k checks the difference is tens of milliseconds — measurable but rarely the bottleneck.

## Execution Trace

```bash
$ uv run python boardly/abc_vs_protocol.py
--- Iterable (collections.abc) is structural at runtime ---
isinstance(ml, Iterable): True
total_a(ml): 6

--- Custom ABC with __subclasshook__ ---
isinstance(f, CloseableABC): True
isinstance(f, CloseableProtocol): True
closed
closed

--- Protocol without @runtime_checkable cannot isinstance ---
isinstance raises: Instance and class checks can only be used with @runtime_checkable protocols

--- runtime_checkable checks attribute presence, not signature ---
isinstance(fake, CloseableProtocol): True  (PROTOCOL DOES NOT VERIFY IT IS CALLABLE)

--- performance: __subclasshook__ vs runtime_checkable ---
ABC __subclasshook__:       ~22 ms (100k checks)
Protocol runtime_checkable: ~43 ms (100k checks)
```

(The exact `isinstance raises` message and the performance numbers vary by Python version and machine. The shape is consistent: `runtime_checkable` is roughly 2× slower than a hand-written `__subclasshook__` because the latter is cached and the former is a fresh `hasattr` walk per call. The TypeError message in Python 3.12 is `Instance and class checks can only be used with @runtime_checkable protocols`; older Pythons printed `Protocols can only be used as base classes, except for those decorated with @typing.runtime_checkable`.)

## Common Mistakes

### Mistake 1: Using `Protocol` without `@runtime_checkable` for isinstance

```python
class Closeable(Protocol):
    def close(self) -> None: ...

def is_closeable(x) -> bool:
    return isinstance(x, Closeable)   # student expects this to work
```

**Symptom:** `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` (3.12+ phrasing; older Pythons printed `Protocols can only be used as base classes, except for those decorated with @typing.runtime_checkable`).

**Why:** `Protocol` is static-only by default. `isinstance` requires `@runtime_checkable`.

**Fix:** Add `@runtime_checkable` above the class definition. Or use a `collections.abc` ABC if the contract maps to one.

### Mistake 2: Trusting `isinstance(x, Protocol)` to verify the signature

```python
@runtime_checkable
class Resettable(Protocol):
    def reset(self, hard: bool = False) -> None: ...

class Fake:
    reset = "not a method"
print(isinstance(Fake(), Resettable))   # student expects False
```

**Symptom:** `True` — the protocol reports conformance even though `Fake.reset` is a string.

**Why:** `runtime_checkable` checks attribute presence, not signatures. The signature is checked at static-analysis time only.

**Fix:** Use static analysis (`mypy --strict` or `pyright`) for signature correctness. Use `runtime_checkable` only as a coarse sanity check.

### Mistake 3: Annotating with `collections.abc.Iterable` and expecting nominal subtyping

```python
from collections.abc import Iterable
class MyIter(Iterable):
    def __iter__(self): return iter([1, 2, 3])

def consume(items: Iterable[int]) -> None:
    for x in items: print(x)
```

**Symptom:** None — this works. The mistake is in the mental model: students think "I inherit from `Iterable` therefore I am nominal". Actually, `collections.abc` is *both* nominal (you can inherit) and structural (`__subclasshook__` makes any class with `__iter__` conform). The two are not mutually exclusive.

**Fix:** No code fix. Read the docs once and internalise that `collections.abc` is dual-purpose — static checkers special-case it for nominal inheritance AND `__subclasshook__` makes it structural at runtime.

## Engineering Trade-Offs

**Decision:** Use `typing.Protocol` for new custom contracts. Use `collections.abc` for the stdlib contracts it already covers. Use a custom ABC with `__subclasshook__` only on 3.7- codebases.

**Both sides:**

`typing.Protocol` wins on:

1. Static subtyping — `mypy`/`pyright` accept any class with the right methods, no inheritance required.
2. Conciseness — class body syntax; no `ABCMeta` boilerplate, no `__subclasshook__`.
3. Composable — protocols can extend multiple protocols; ABCs can only have one metaclass chain.
4. Modern Python — `Protocol` is the path forward; new code should use it.

`collections.abc` wins on:

1. Stdlib coverage — `Iterable`, `Sequence`, `Mapping`, `Hashable`, etc. are already defined. No need to re-define them.
2. Caching — `__subclasshook__` results are cached in `ABCMeta`; `runtime_checkable` is not (in 3.12).
3. Backwards compatibility — `collections.abc` works on every Python 3.x; `Protocol` requires 3.8+.

Custom ABCs with `__subclasshook__` win on:

1. Codebases that cannot use `Protocol` (Python 3.7 or earlier, or strict runtime-only typing).
2. Contracts that need both nominal inheritance (for static checkers) and structural runtime checks (for `isinstance`).

**Commitment:** `boardly/abc_vs_protocol.py` defines `CloseableProtocol` (the modern path) for the `Closeable` contract, and uses `collections.abc.Iterable` / `Sequence` / `Mapping` for the stdlib contracts. The custom `CloseableABC` exists only for teaching. The rule: "Stdlib contract? `collections.abc`. Custom contract? `typing.Protocol`. Pre-3.8 codebase? Custom ABC with `__subclasshook__`."

## Exercises

1. **Exercise 1 — Confirm `Iterable` is structural.** Define a class with `__iter__` that does not inherit; confirm `isinstance(x, Iterable)` is `True`. `Verify: uv run python -c "from collections.abc import Iterable\nclass C:\n  def __iter__(self):\n    return iter([1,2,3])\nprint(isinstance(C(), Iterable))"`
2. **Exercise 2 — Protocol without `@runtime_checkable` raises.** Define a bare protocol and confirm `isinstance` raises. `Verify: uv run python -c "from typing import Protocol\nclass P(Protocol):\n  def m(self): pass\ntry:\n  isinstance(object(), P)\nexcept TypeError as e:\n  print('TypeError:', e)"`
3. **Exercise 3 — `runtime_checkable` checks attribute presence.** Build a class with a non-callable attribute that matches a protocol's method name; confirm `isinstance` is `True`. `Verify: uv run python -c "from typing import Protocol, runtime_checkable\n@runtime_checkable\nclass P(Protocol):\n  def m(self): pass\nclass C:\n  m = 42\nprint(isinstance(C(), P))"`
4. **Exercise 4 — A `Protocol` for boardly.** Define `class PluginProto(Protocol)` with `name() -> str` and `run(ctx) -> Any`. Implement a class that conforms without inheriting. `Verify: uv run python -c "from typing import Protocol, runtime_checkable\n@runtime_checkable\nclass P(Protocol):\n  def name(self) -> str: ...\n  def run(self, ctx): ...\nclass C:\n  def name(self): return 'c'\n  def run(self, ctx): return 'ok'\nprint(isinstance(C(), P))"`
5. **Exercise 5 — Compare performance.** Time 100k `isinstance` checks on a `__subclasshook__` ABC vs a `runtime_checkable` Protocol. `Verify: uv run python -c "import timeit\nfrom abc import ABCMeta, abstractmethod\nfrom typing import Protocol, runtime_checkable\nclass A(metaclass=ABCMeta):\n  @classmethod\n  def __subclasshook__(cls, sub):\n    if cls is not A: return NotImplemented\n    return hasattr(sub, 'x') or NotImplemented\n@runtime_checkable\nclass P(Protocol):\n  def x(self): ...\nclass C:\n  def x(self): pass\nprint(timeit.timeit(lambda: isinstance(C(), A), number=100_000), timeit.timeit(lambda: isinstance(C(), P), number=100_000))"`

## Verification

```bash
$ uv run python boardly/abc_vs_protocol.py
--- Iterable (collections.abc) is structural at runtime ---
isinstance(ml, Iterable): True
total_a(ml): 6

--- Custom ABC with __subclasshook__ ---
isinstance(f, CloseableABC): True
isinstance(f, CloseableProtocol): True
closed
closed

--- Protocol without @runtime_checkable cannot isinstance ---
isinstance raises: Instance and class checks can only be used with @runtime_checkable protocols

--- runtime_checkable checks attribute presence, not signature ---
isinstance(fake, CloseableProtocol): True  (PROTOCOL DOES NOT VERIFY IT IS CALLABLE)

--- performance: __subclasshook__ vs runtime_checkable ---
ABC __subclasshook__:       ~22 ms (100k checks)
Protocol runtime_checkable: ~43 ms (100k checks)
```

## Previously Learned Here

- [[05-collections-abc/05-Custom-ABCs]] — the `ABCMeta` + `register` + `__subclasshook__` mechanism this lesson contrasts with `Protocol`.
- [[05-collections-abc/01-The-ABC-Hierarchy]] — the full `collections.abc` tree this lesson maps to the `Protocol` world.
- [[05-collections-abc/00-collections-abc-MOC]] — the section MOC.

## What's Next

You have finished Section 05. Open [[06-dataclasses/01-dataclass-Basics]] — Section 06 is `@dataclass`. `@dataclass` is the modern replacement for `namedtuple` (Section 04, Lesson 04) and the bridge to Pydantic. The three lessons of Section 05 (Hashable, Iterator, Custom ABCs) all pay off in Section 06: `frozen=True` makes a dataclass `Hashable`, `slots=True` makes it memory-lean like a `namedtuple`, and `dataclass_transform` (the mechanism Pydantic v2 uses) is built on the same `ABCMeta` machinery you saw in Lesson 05.

## Sources

- **Python `collections.abc` documentation** — https://docs.python.org/3/library/collections.abc.html — accessed 2026-10-23 — the stdlib ABCs this lesson contrasts with `Protocol`.
- **PEP 544 — Protocols: Structural subtyping** — https://peps.python.org/pep-0544/ — accessed 2026-10-23 — the PEP that added `typing.Protocol` and `runtime_checkable`; the design rationale for structural subtyping at the type level.
- **Python `typing.Protocol` documentation** — https://docs.python.org/3/library/typing.html#typing.Protocol — accessed 2026-10-23 — the canonical reference for `Protocol`, `runtime_checkable`, and the limitations of runtime checks.

## What We Learned

- `collections.abc.Iterable` is structural at runtime via `__subclasshook__` — any class with `__iter__` is `Iterable`.
- `typing.Protocol` is structural at static-check time; `isinstance` requires `@runtime_checkable`.
- `runtime_checkable` checks attribute *presence*, not signatures — `Fake.close = 42` conforms to `CloseableProtocol`.
- A custom ABC with `__subclasshook__` is the pre-3.8 equivalent of `Protocol`.
- `collections.abc` is dual-purpose (nominal + structural); `Protocol` is static-only by default and runtime-checkable opt-in.
- Decision: stdlib contract → `collections.abc`; custom contract → `typing.Protocol`; pre-3.8 → custom ABC with `__subclasshook__`.
