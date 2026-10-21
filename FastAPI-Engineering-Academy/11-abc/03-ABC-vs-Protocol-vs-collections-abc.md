---
title: "Lesson 03: ABC vs Protocol vs collections.abc"
aliases:
 - ABC vs Protocol
 - abc vs typing
 - collections.abc vs Protocol
 - runtime_checkable
tags:
 - abc
 - typing
 - protocol
 - collections-abc
 - decision
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "25–35 minutes"
prerequisites:
 - "[[11-abc/01-ABC-and-abstractmethod]]"
 - "[[11-abc/02-register-and-Virtual-Subclasses]]"
 - "[[01-typing/05-Protocol-Structural-Typing]]"
related_lessons:
 - "[[05-collections-abc/06-abcs-vs-protocols]]"
 - "[[05-collections-abc/01-The-ABC-Hierarchy]]"
---

# Lesson 03: ABC vs Protocol vs collections.abc

*The three-way decision: `abc.ABC` (nominal, must inherit, runtime `TypeError`), `typing.Protocol` (structural at static-check time, `@runtime_checkable` opt-in and coarse), `collections.abc.Iterable` (structural at runtime via `__subclasshook__`, pre-defined contracts). When each wins.*

**You're at the very beginning of Section 11 — Lesson 03.**

You have written a custom ABC (Lesson 01). You have seen the virtual-subclass mechanism (Lesson 02). You have seen `typing.Protocol` back in Section 01. This lesson answers the question every senior backend engineer gets asked once: "I have a contract. Which of the three do I use?" The answer is layered — they overlap, they differ, they have different ergonomics and different performance, and the right choice depends on whether you are annotating a function signature, writing an `isinstance` check, defining a new contract for a plugin system, or hooking into something the stdlib already defines. By the end of this lesson you will have a decision table you can apply to every new contract you write.

Take your time. Type every example. **This is how you learn.**

#abc #typing #protocol #collections-abc

## Learning Objectives

By the end of this lesson you will be able to:

1. **State the three mechanisms** — `abc.ABC` (nominal, must inherit), `typing.Protocol` (structural at static-check time, `@runtime_checkable` opt-in), `collections.abc.X` (structural at runtime via `__subclasshook__`).
2. **Decide between the three** for a given contract — function signature, isinstance check, plugin extension point, stdlib contract — and defend the choice.
3. **Explain why `runtime_checkable` is coarse** — it checks attribute presence, not signatures — and what that means for trusting `isinstance(x, MyProtocol)` results.
4. **Explain why `collections.abc` is dual-purpose** — nominal (you can inherit) *and* structural (via `__subclasshook__`) — and how that makes it different from both `abc.ABC` and `typing.Protocol`.

## Prerequisites

Before starting, you need:

- **[[11-abc/01-ABC-and-abstractmethod]]** — `abc.ABC` + `@abstractmethod`; this lesson contrasts that mechanism with the other two.
- **[[11-abc/02-register-and-Virtual-Subclasses]]** — `register` and `__subclasshook__`; this lesson positions them in the broader decision.
- **[[01-typing/05-Protocol-Structural-Typing]]** — `typing.Protocol` and `@runtime_checkable`; this lesson assumes you have written a `Protocol` before.
- **About 30 minutes of focused time.**

**The most common gap: assuming the three are interchangeable.**

They are not. `abc.ABC` is *nominal* — a class is an `ABC` subclass because it inherits. `typing.Protocol` is *structural at static-check time* and *optional and coarse at runtime* — `mypy`/`pyright` check signatures; `isinstance` (with `@runtime_checkable`) only checks attribute presence. `collections.abc.Iterable` is *structural at runtime* via `__subclasshook__` — any class with `__iter__` conforms, automatically, at runtime. Three mechanisms, three failure modes, three performance profiles. Read this lesson with "they are not interchangeable" front of mind.

## The Problem

Here is the bug. `boardly` has an export-plugin API:

```python
def export_to_format(exporter, rows: list) -> bytes:
    return exporter.export(rows)
```

The function accepts "anything with an `export(rows: list) -> bytes` method". Three reviewers ask three questions:

1. **Reviewer A** — "What does `exporter` accept? The type annotation is missing." The team's first attempt is `exporter: object` — too loose. The team's second attempt is `exporter: ExporterABC` — too strict, requires inheritance.
2. **Reviewer B** — "Can we accept third-party exporters without forcing them to inherit?" The team's first answer is "use `register`" (Lesson 02). That works but requires explicit registration on each third-party class.
3. **Reviewer C** — "Is there a way to express this contract that gives us both static-checker enforcement *and* runtime `isinstance` checks?" The team's answer is `typing.Protocol` with `@runtime_checkable`.

Three reviewers, three answers, three mechanisms. The decision is which one (or which combination) to commit to. This lesson writes the same contract three ways — `abc.ABC`, `typing.Protocol`, `collections.abc.Iterable` — and walks the trade-offs side by side.

## The Code

```python
# boardly/export_contract_three_ways.py
"""Three contracts, three mechanisms, for the boardly export-plugin API.

  Approach 1: abc.ABC           — nominal, must inherit, runtime TypeError.
  Approach 2: typing.Protocol   — structural at static-check; isinstance needs @runtime_checkable.
  Approach 3: collections.abc   — structural at runtime via __subclasshook__; pre-defined contracts.
"""
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from collections.abc import Iterable


# --- Approach 1: abc.ABC — nominal, must inherit ---

class ExporterABC(ABC):
    @abstractmethod
    def export(self, rows: list) -> bytes: ...


class CsvExporter(ExporterABC):
    def export(self, rows: list) -> bytes:
        return ",".join(str(r) for r in rows).encode()


# --- Approach 2: typing.Protocol — structural, runtime_checkable opt-in ---

@runtime_checkable
class ExporterProto(Protocol):
    def export(self, rows: list) -> bytes: ...


class JsonExporter:
    """Does not inherit from anything; satisfies the protocol structurally."""

    def export(self, rows: list) -> bytes:
        return b"[]"


# --- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---

def export_all(plugins: Iterable) -> list:
    """Iterate plugins; call export() on each (presence-checked)."""
    return [p.export([1, 2, 3]) if hasattr(p, "export") else b"" for p in plugins]


if __name__ == "__main__":
    print("--- Approach 1: abc.ABC — nominal ---")
    try:
        ExporterABC()
    except TypeError as e:
        print(f"ExporterABC() raises: {e}")
    csv = CsvExporter()
    print(f"isinstance(csv, ExporterABC):  {isinstance(csv, ExporterABC)}")

    print("\n--- Approach 2: typing.Protocol — structural, runtime_checkable ---")
    j = JsonExporter()
    print(f"isinstance(j, ExporterABC):    {isinstance(j, ExporterABC)}  (ABC requires inheritance)")
    print(f"isinstance(j, ExporterProto):  {isinstance(j, ExporterProto)}  (Protocol is structural at runtime)")

    print("\n--- Protocol WITHOUT @runtime_checkable raises ---")
    class BareProto(Protocol):
        def export(self, rows: list) -> bytes: ...
    try:
        isinstance(j, BareProto)
    except TypeError as e:
        print(f"isinstance raises: {e}")

    print("\n--- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---")
    class AdHoc:
        def __iter__(self): return iter([csv, j])
    ad = AdHoc()
    print(f"isinstance(ad, Iterable):      {isinstance(ad, Iterable)}  (no inheritance, no register)")
    print(f"export_all(ad):                {export_all(ad)}")

    print("\n--- Decision matrix ---")
    print("abc.ABC              — nominal, must inherit, runtime TypeError on partial implementation")
    print("typing.Protocol      — structural at static-time; isinstance needs @runtime_checkable (presence-only)")
    print("collections.abc.X    — structural at runtime via __subclasshook__; pre-defined contracts (Iterable, ...)")
```

## Line-by-Line Deep Dive

### Lines 1–11: Imports — three mechanisms in one file

```python
# boardly/export_contract_three_ways.py
"""Three contracts, three mechanisms, for the boardly export-plugin API.

  Approach 1: abc.ABC           — nominal, must inherit, runtime TypeError.
  Approach 2: typing.Protocol   — structural at static-check; isinstance needs @runtime_checkable.
  Approach 3: collections.abc   — structural at runtime via __subclasshook__; pre-defined contracts.
"""
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from collections.abc import Iterable
```

`from abc import ABC, abstractmethod` — the *nominal* mechanism (Lesson 01). `ABC` is the 3.4+ base class; `abstractmethod` is the decorator that marks methods a subclass must override.

`from typing import Protocol, runtime_checkable` — the *static structural* mechanism (PEP 544, 3.8+). `Protocol` is the base class for structural types; `runtime_checkable` is the decorator that opts a protocol into `isinstance` checks.

`from collections.abc import Iterable` — the *runtime structural* mechanism. `Iterable` is a pre-defined ABC whose `__subclasshook__` (Lesson 02) makes any class with `__iter__` conform. Note that `typing.Iterable` is *also* `collections.abc.Iterable` — the `typing` module re-exports the stdlib ABCs as aliases. In 3.9+, both imports give you the same class; the canonical home is `collections.abc`.

**Why three imports for the same shape of contract?** Because the three mechanisms exist at different layers — `abc` is runtime + nominal; `typing.Protocol` is static + structural (with runtime opt-in); `collections.abc` is runtime + structural (via `__subclasshook__`). The right mechanism depends on what you want: enforcement at runtime? at static-check time? on a closed set of conforming classes? on an open set?

### Lines 14–24: Approach 1 — `abc.ABC`, nominal, must inherit

```python
# --- Approach 1: abc.ABC — nominal, must inherit ---

class ExporterABC(ABC):
    @abstractmethod
    def export(self, rows: list) -> bytes: ...


class CsvExporter(ExporterABC):
    def export(self, rows: list) -> bytes:
        return ",".join(str(r) for r in rows).encode()
```

`class ExporterABC(ABC):` — nominal ABC. The contract is "if you want to be an `ExporterABC`, you inherit from `ExporterABC` and override `export`". `ExporterABC()` raises `TypeError` (Lesson 01); `CsvExporter` is concrete; `isinstance(csv, ExporterABC)` is `True` because `CsvExporter.__mro__` contains `ExporterABC`.

The trade-off: a third-party class that already has an `export` method does *not* conform — it does not inherit. You can `ExporterABC.register(ThirdParty)` (Lesson 02) to make `isinstance` lie, but `mypy`/`pyright` still require real inheritance in static type annotations. So `abc.ABC` is the choice when *you* own the subclasses and want the construction-time `TypeError` for safety.

**Why does `mypy` not understand `register`?** Because `register` is a *runtime* declaration; the static checker would have to execute the code (or analyse the registration calls) to know about the virtual relationship. PEP 544 (`Protocol`) was designed specifically to give static checkers a structural subtyping mechanism that does not require inheritance — that is why `Protocol` exists.

### Lines 27–39: Approach 2 — `typing.Protocol`, structural, opt-in runtime check

```python
# --- Approach 2: typing.Protocol — structural, runtime_checkable opt-in ---

@runtime_checkable
class ExporterProto(Protocol):
    def export(self, rows: list) -> bytes: ...


class JsonExporter:
    """Does not inherit from anything; satisfies the protocol structurally."""

    def export(self, rows: list) -> bytes:
        return b"[]"
```

`class ExporterProto(Protocol):` — a `Protocol` is a structural type. `mypy`/`pyright` check that any class used where `ExporterProto` is expected has an `export(rows: list) -> bytes` method, *regardless of inheritance*. `JsonExporter` conforms statically because it has the right method.

`@runtime_checkable` — the decorator that opts `ExporterProto` into `isinstance` checks. Without it, `isinstance(j, ExporterProto)` raises `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` (Python 3.12 wording). With it, `isinstance(j, ExporterProto)` returns `True` if `j` has an `export` attribute.

**Why is `runtime_checkable` opt-in?** Because the runtime check is *imprecise*. `@runtime_checkable` checks for the *presence* of attributes named in the Protocol; it does not check signatures, return types, or even whether the attribute is callable. The static check is precise; the runtime check is a coarse sanity check. The Python docs are explicit: "An `isinstance()` check against a runtime-checkable protocol is superficially similar to a `hasattr()`-based check". Defaulting to opt-in would have encouraged developers to rely on a coarse check; the opt-in makes the choice deliberate.

### Lines 42–47: Approach 3 — `collections.abc.Iterable`, structural via `__subclasshook__`

```python
# --- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---

def export_all(plugins: Iterable) -> list:
    """Iterate plugins; call export() on each (presence-checked)."""
    return [p.export([1, 2, 3]) if hasattr(p, "export") else b"" for p in plugins]
```

`plugins: Iterable` — the annotation uses `collections.abc.Iterable`. Static checkers accept any class with `__iter__`; runtime `isinstance(plugins, Iterable)` returns `True` for any class with `__iter__`. The structural check is *automatic* — no `register`, no `@runtime_checkable`, no inheritance.

The body of `export_all` *also* checks `hasattr(p, "export")` because `Iterable` only promises `__iter__`, not `export`. The lesson here is that `collections.abc` gives you the *minimal* contract; if you need a richer contract, you either extend the ABC (with a custom subclass that adds an abstract `export` method) or use a `Protocol` to express the richer shape.

**Why would you ever use `collections.abc` over a custom `Protocol`?** Three reasons. First, `Iterable` is a *standard* — readers know what it means without reading your code. Second, `collections.abc` is *cached* at runtime — `__subclasshook__` results are cached in `ABCMeta._abc_cache`; `runtime_checkable` does a fresh `hasattr` walk per call. Third, `collections.abc` covers the contracts the world already satisfies (`Iterable`, `Sequence`, `Mapping`, `Hashable`, `Callable`) — there is no need to redefine them.

### Lines 50–56: Approach 1 in action — `ExporterABC()` raises

```python
if __name__ == "__main__":
    print("--- Approach 1: abc.ABC — nominal ---")
    try:
        ExporterABC()
    except TypeError as e:
        print(f"ExporterABC() raises: {e}")
    csv = CsvExporter()
    print(f"isinstance(csv, ExporterABC):  {isinstance(csv, ExporterABC)}")
```

`ExporterABC()` raises `TypeError` — the construction-time check. `isinstance(csv, ExporterABC)` is `True` — `CsvExporter.__mro__` contains `ExporterABC`. This is the *nominal* path: a class is an `ExporterABC` because it inherits; the runtime enforces the contract at `MyClass()`.

### Lines 58–62: Approach 2 in action — `Protocol` is structural at runtime

```python
    print("\n--- Approach 2: typing.Protocol — structural, runtime_checkable ---")
    j = JsonExporter()
    print(f"isinstance(j, ExporterABC):    {isinstance(j, ExporterABC)}  (ABC requires inheritance)")
    print(f"isinstance(j, ExporterProto):  {isinstance(j, ExporterProto)}  (Protocol is structural at runtime)")
```

`isinstance(j, ExporterABC)` is `False` — `JsonExporter` does not inherit. `isinstance(j, ExporterProto)` is `True` — `JsonExporter` has an `export` attribute, so the `runtime_checkable` check passes. The *static* behaviour differs from `ExporterABC`: `mypy`/`pyright` accept `JsonExporter` wherever `ExporterProto` is expected, no inheritance required.

**Why is `isinstance(j, ExporterProto)` *True* even though `JsonExporter.export` returns a constant?** Because `runtime_checkable` checks *presence*, not signatures. `JsonExporter.export` could be a string, a number, or `None` — `isinstance` would still return `True` as long as the attribute exists. The signature is enforced at static-check time; the runtime check is a coarse sanity check.

### Lines 64–71: Approach 2 limitation — bare `Protocol` raises

```python
    print("\n--- Protocol WITHOUT @runtime_checkable raises ---")
    class BareProto(Protocol):
        def export(self, rows: list) -> bytes: ...
    try:
        isinstance(j, BareProto)
    except TypeError as e:
        print(f"isinstance raises: {e}")
```

`isinstance(j, BareProto)` raises `TypeError` — the protocol is static-only. Without `@runtime_checkable`, the protocol is a *type-system construct*, not a runtime check. This is the trade-off: `Protocol` is precise at static-check time, coarse at runtime (with opt-in), or absent at runtime (without opt-in).

### Lines 73–79: Approach 3 in action — `Iterable` is structural automatically

```python
    print("\n--- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---")
    class AdHoc:
        def __iter__(self): return iter([csv, j])
    ad = AdHoc()
    print(f"isinstance(ad, Iterable):      {isinstance(ad, Iterable)}  (no inheritance, no register)")
    print(f"export_all(ad):                {export_all(ad)}")
```

`AdHoc` does not inherit from `Iterable`, is not registered, and has no `@runtime_checkable` decorator. `isinstance(ad, Iterable)` is `True` because `Iterable.__subclasshook__` checks for `__iter__` and returns `True`. The structural check is *automatic* — that is what `collections.abc` is for.

**Why is `collections.abc` structural at runtime while `typing.Protocol` is opt-in?** Because the stdlib ABCs (`Iterable`, `Sequence`, `Mapping`) were designed (PEP 3119) to *make* the contracts open-ended — the Python core team wanted any class with `__iter__` to be `Iterable`, regardless of inheritance. `typing.Protocol` was designed later (PEP 544, 3.8+) for the *static* type system; the runtime check was added as a deliberate opt-in to prevent developers from over-relying on coarse runtime checks. Different design goals, different defaults.

### Lines 81–84: The decision matrix

```python
    print("\n--- Decision matrix ---")
    print("abc.ABC              — nominal, must inherit, runtime TypeError on partial implementation")
    print("typing.Protocol      — structural at static-time; isinstance needs @runtime_checkable (presence-only)")
    print("collections.abc.X    — structural at runtime via __subclasshook__; pre-defined contracts (Iterable, ...)")
```

The decision matrix is the lesson's takeaway. The same contract — "anything with an `export` method" — can be expressed three ways, and the choice is a *layer* decision: where do you want the check to happen? Runtime (`abc.ABC` with `TypeError`)? Static (`typing.Protocol` without `@runtime_checkable`)? Both (with `@runtime_checkable`)? Pre-defined (`collections.abc` for stdlib contracts)?

## Execution Trace

```bash
$ uv run python boardly/export_contract_three_ways.py
--- Approach 1: abc.ABC — nominal ---
ExporterABC() raises: Can't instantiate abstract class ExporterABC without an implementation for abstract method 'export'
isinstance(csv, ExporterABC):  True

--- Approach 2: typing.Protocol — structural, runtime_checkable ---
isinstance(j, ExporterABC):    False  (ABC requires inheritance)
isinstance(j, ExporterProto):  True  (Protocol is structural at runtime)

--- Protocol WITHOUT @runtime_checkable raises ---
isinstance raises: Instance and class checks can only be used with @runtime_checkable protocols

--- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---
isinstance(ad, Iterable):      True  (no inheritance, no register)
export_all(ad):                [b'1,2,3', b'[]']

--- Decision matrix ---
abc.ABC              — nominal, must inherit, runtime TypeError on partial implementation
typing.Protocol      — structural at static-time; isinstance needs @runtime_checkable (presence-only)
collections.abc.X    — structural at runtime via __subclasshook__; pre-defined contracts (Iterable, ...)
```

## Common Mistakes

### Mistake 1: Using `Protocol` without `@runtime_checkable` for `isinstance`

```python
class Closeable(Protocol):
    def close(self) -> None: ...

def is_closeable(x) -> bool:
    return isinstance(x, Closeable)   # student expects this to work
```

**Symptom:** `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` (Python 3.12 wording; pre-3.12 was `Protocols can only be used as base classes ...`).

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

**Why:** `runtime_checkable` checks attribute *presence*, not signatures. The signature is checked at static-analysis time only.

**Fix:** Use static analysis (`mypy --strict` or `pyright`) for signature correctness. Use `runtime_checkable` only as a coarse sanity check. If you need signature enforcement at runtime, write a custom `__init_subclass__` or use `inspect.signature` — `Protocol` cannot do it.

### Mistake 3: Using `abc.ABC` when you need third-party structural conformance

```python
class ExporterABC(ABC):
    @abstractmethod
    def export(self, rows: list) -> bytes: ...

def export_to_format(exporter: ExporterABC, rows: list) -> bytes:
    return exporter.export(rows)

# third-party:
class YamlExporter:  # does not inherit from ExporterABC
    def export(self, rows: list) -> bytes: ...

export_to_format(YamlExporter(), [...])  # student expects this to work
```

**Symptom:** `mypy`/`pyright` flag `YamlExporter()` as incompatible with `ExporterABC`. The static check fails because `YamlExporter` does not inherit.

**Why:** `abc.ABC` is nominal — the contract requires inheritance. `register` (Lesson 02) makes `isinstance` lie, but `mypy` does not consult `register`; the static check still requires real inheritance.

**Fix:** Use `typing.Protocol` for the type annotation. `class ExporterProto(Protocol): def export(self, rows: list) -> bytes: ...` accepts `YamlExporter` statically because the protocol is structural. Use `register` only for runtime `isinstance` checks.

## Engineering Trade-Offs

**Decision:** Use `abc.ABC` for internal contracts you own and want enforced at construction time. Use `typing.Protocol` for custom contracts that need to accept third-party classes structurally. Use `collections.abc.X` for the stdlib contracts it already defines (`Iterable`, `Sequence`, `Mapping`, `Hashable`, `Callable`, `Buffer`).

**Both sides:**

`abc.ABC` wins on:

1. **Construction-time enforcement.** `TypeError` at `MyClass()` is the strongest contract Python offers — far stronger than `raise NotImplementedError`, which fires only when the missing method is called.
2. **Self-documenting hierarchy.** `class MyRepo(Repository)` says "I am a Repository"; the reader does not have to scan the methods.
3. **Backwards compatibility.** `abc.ABC` (3.4+) works on every Python 3.x; `typing.Protocol` requires 3.8+.

`typing.Protocol` wins on:

1. **Structural conformance.** A class can conform without inheriting — useful for third-party classes you cannot edit. `abc.ABC` requires real inheritance.
2. **Static-only checks.** `Protocol` is a *static* type — `mypy`/`pyright` enforce structural subtyping without runtime cost. `abc.ABC` enforces at runtime only.
3. **Composable signatures.** Protocols can extend multiple protocols; ABCs can only have one metaclass chain.
4. **Modern Python.** `Protocol` is the path forward for new custom contracts; the community trend is towards it.

`collections.abc` wins on:

1. **Stdlib coverage.** `Iterable`, `Sequence`, `Mapping`, `Hashable`, `Callable` are already defined. No need to re-define them.
2. **Caching.** `__subclasshook__` results are cached in `ABCMeta._abc_cache`; `runtime_checkable` is not (in 3.12).
3. **Open-set runtime checks.** Any class with `__iter__` is `Iterable` — automatically, no opt-in.
4. **Standards.** Readers know what `Iterable` means without reading your code.

**Commitment:** `boardly/export_contract_three_ways.py` defines `ExporterABC` for the *internal* exporter contract (subclasses are owned by the team; construction-time `TypeError` is the bug-shape we want), `ExporterProto` for the *plug-in* exporter contract (third-party exporters may conform without inheriting), and uses `collections.abc.Iterable` for the *stdlib* contract on `export_all` (any iterable of plugins). The rule: "Internal contract? `abc.ABC`. Custom plug-in contract? `typing.Protocol`. Stdlib contract? `collections.abc.X`."

## Exercises

1. **Exercise 1 — Confirm `ExporterABC()` raises.** Try to instantiate the ABC and confirm `TypeError`. `Verify: uv run python -c "from boardly.export_contract_three_ways import ExporterABC\ntry:\n    ExporterABC()\nexcept TypeError as e:\n    print('TypeError:', e)"`
2. **Exercise 2 — `runtime_checkable` is structural at runtime.** Define a class with the right method, confirm `isinstance(x, MyProtocol)` is `True` without inheritance. `Verify: uv run python -c "from typing import Protocol, runtime_checkable\n@runtime_checkable\nclass P(Protocol):\n  def export(self, rows): ...\nclass C:\n  def export(self, rows): return b'x'\nprint(isinstance(C(), P))"`
3. **Exercise 3 — Bare `Protocol` raises on `isinstance`.** Define a non-`runtime_checkable` protocol and confirm `isinstance` raises. `Verify: uv run python -c "from typing import Protocol\nclass P(Protocol):\n  def m(self): ...\nclass C:\n  def m(self): pass\ntry:\n    isinstance(C(), P)\nexcept TypeError as e:\n    print('TypeError:', e)"`
4. **Exercise 4 — `Iterable` is structural automatically.** Define a class with `__iter__` (no inheritance, no register), confirm `isinstance(x, Iterable)` is `True`. `Verify: uv run python -c "from collections.abc import Iterable\nclass C:\n  def __iter__(self): return iter([1, 2])\nprint(isinstance(C(), Iterable))"`
5. **Exercise 5 — A boardly plug-in protocol.** Define `class PluginProto(Protocol)` with `name() -> str` and `run(ctx) -> Any`. Implement a class that conforms without inheriting; confirm `isinstance` is `True` (with `@runtime_checkable`) and that `mypy` accepts it as a `PluginProto`. `Verify: uv run python -c "from typing import Protocol, runtime_checkable, Any\n@runtime_checkable\nclass PluginProto(Protocol):\n  def name(self) -> str: ...\n  def run(self, ctx) -> Any: ...\nclass C:\n  def name(self): return 'c'\n  def run(self, ctx): return 'ok'\nprint(isinstance(C(), PluginProto))"`

## Verification

```bash
$ uv run python boardly/export_contract_three_ways.py
--- Approach 1: abc.ABC — nominal ---
ExporterABC() raises: Can't instantiate abstract class ExporterABC without an implementation for abstract method 'export'
isinstance(csv, ExporterABC):  True

--- Approach 2: typing.Protocol — structural, runtime_checkable ---
isinstance(j, ExporterABC):    False  (ABC requires inheritance)
isinstance(j, ExporterProto):  True  (Protocol is structural at runtime)

--- Protocol WITHOUT @runtime_checkable raises ---
isinstance raises: Instance and class checks can only be used with @runtime_checkable protocols

--- Approach 3: collections.abc.Iterable — structural via __subclasshook__ ---
isinstance(ad, Iterable):      True  (no inheritance, no register)
export_all(ad):                [b'1,2,3', b'[]']

--- Decision matrix ---
abc.ABC              — nominal, must inherit, runtime TypeError on partial implementation
typing.Protocol      — structural at static-time; isinstance needs @runtime_checkable (presence-only)
collections.abc.X    — structural at runtime via __subclasshook__; pre-defined contracts (Iterable, ...)
```

## Previously Learned Here

- [[11-abc/01-ABC-and-abstractmethod]] — `abc.ABC` + `@abstractmethod`; this lesson contrasts that mechanism with the other two.
- [[11-abc/02-register-and-Virtual-Subclasses]] — `register` and `__subclasshook__`; this lesson positions them in the broader decision.
- [[01-typing/05-Protocol-Structural-Typing]] — `typing.Protocol` and `@runtime_checkable`; this lesson assumes you have written a `Protocol` before.
- [[05-collections-abc/06-abcs-vs-protocols]] — the two-way decision (ABC vs Protocol) that this lesson extends to three ways.

## What's Next

You have finished Section 11. The three lessons together give you the full picture of Python's abstract-base-class story: Lesson 01 taught the contract (`abc.ABC` + `@abstractmethod`), Lesson 02 taught the registration mechanisms (`register` + `__subclasshook__`), and Lesson 03 taught the decision (when each of `abc.ABC`, `typing.Protocol`, and `collections.abc.X` wins). The next sections apply this picture:

- **[[12-types/00-types-MOC]]** — the `types` module, including `GenericAlias`, `UnionType`, and `MappingProxyType`. Section 12 leans on the metaclass machinery you saw here.
- **[[13-future/00-future-MOC]]** — `from __future__ import annotations` (PEP 563) and PEP 649 (deferred evaluation, default in 3.14). Section 13 explains how `get_type_hints` interacts with the ABC introspection you saw in Lesson 01.
- **[[14-importlib/00-importlib-MOC]]** — `importlib` plugin loading; Section 14 builds a real plugin system on top of `abc.ABC` + `register`.

Open [[12-types/00-types-MOC]] to continue.

## Sources

- **Python `abc` module documentation** — https://docs.python.org/3/library/abc.html — accessed 2026-10-23 — the canonical reference for `ABC`, `ABCMeta`, `abstractmethod`, and the `register` / `__subclasshook__` mechanisms.
- **Python `typing.Protocol` documentation** — https://docs.python.org/3/library/typing.html#typing.Protocol — accessed 2026-10-23 — the canonical reference for `Protocol`, `runtime_checkable`, and the limitations of runtime checks.
- **Python `collections.abc` documentation** — https://docs.python.org/3/library/collections.abc.html — accessed 2026-10-23 — the stdlib ABCs whose `__subclasshook__` makes `isinstance(x, Iterable)` structural.
- **PEP 544 — Protocols: Structural subtyping** — https://peps.python.org/pep-0544/ — accessed 2026-10-23 — the PEP that added `typing.Protocol` and `runtime_checkable`; the design rationale for structural subtyping at the type level.
- **PEP 3119 — Introducing Abstract Base Classes** — https://peps.python.org/pep-3119/ — accessed 2026-10-23 — the original ABC PEP; the design rationale for `ABCMeta`, `register`, and `__subclasshook__`.

## What We Learned

- `abc.ABC` is *nominal* — a class conforms by inheriting; `TypeError` at construction enforces the contract.
- `typing.Protocol` is *structural at static-check time*; `isinstance` requires `@runtime_checkable` and is coarse (attribute presence only).
- `collections.abc.X` is *structural at runtime* via `__subclasshook__` — any class with the right methods conforms automatically.
- `Protocol` and `runtime_checkable` are *opt-in*; `collections.abc`'s structural checks are *automatic* by design.
- `register` makes `isinstance` lie for an `abc.ABC`, but `mypy`/`pyright` still require real inheritance — `Protocol` was designed to give static checkers a structural mechanism.
- Decision: internal contract, use `abc.ABC`; custom plug-in contract, use `typing.Protocol`; stdlib contract, use `collections.abc.X`.
