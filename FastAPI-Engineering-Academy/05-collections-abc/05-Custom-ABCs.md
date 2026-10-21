---
title: "Lesson 05: Custom ABCs"
aliases:
 - ABCMeta
 - abstractmethod
 - register
 - __subclasshook__
tags:
 - collections-abc
 - abc
 - abcmeta
 - subclasshook
 - register
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–40 minutes"
prerequisites:
 - "[[05-collections-abc/04-Iterator-vs-Iterable]]"
related_lessons:
 - "[[11-abc/01-ABC-and-abstractmethod]]"
 - "[[05-collections-abc/06-abcs-vs-protocols]]"
---

# Lesson 05: Custom ABCs

*How to define your own ABC with `ABCMeta` and `@abstractmethod`, the `register()` virtual-subclass mechanism that lets a class "claim" conformance without inheriting, and the `__subclasshook__` pattern that `collections.abc` uses to make `isinstance(x, Iterable)` work on any class with `__iter__`.*

**You're at the very beginning of Section 05 — Lesson 05.**

You have used `collections.abc.Iterable`, `Sequence`, `Mapping` for four lessons now. This lesson is how those classes themselves are built — the metaclass (`ABCMeta`), the decorator (`@abstractmethod`), the virtual-subclass mechanism (`register()`), and the structural check (`__subclasshook__`). After this lesson you will be able to define your own ABCs, and you will see the inside of `collections.abc` as a small, predictable pattern.

Take your time. Type every example. **This is how you learn.**

#collections-abc #abc #abcmeta #subclasshook

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define a custom ABC** using `ABCMeta` as the metaclass and `@abstractmethod` on the abstract methods.
2. **Use `register()`** to make an unrelated class a "virtual subclass" of your ABC — `isinstance(x, MyABC)` returns `True` without inheritance.
3. **Implement `__subclasshook__`** to make `isinstance` checks structural — any class with the right methods conforms.
4. **Explain the difference between `register` and `__subclasshook__`** and when each is appropriate.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/04-Iterator-vs-Iterable]]** — comfort with the `Iterable` / `Iterator` ABCs and the contract pattern.
- **Familiarity with the `abc` module** — if you have not used `abc.ABC` and `abc.abstractmethod`, glance at the first 50 lines of [[11-abc/01-ABC-and-abstractmethod]].
- **About 35 minutes of focused time.**

**The most common gap: confusing `register` and `__subclasshook__`.**

`register` is *nominal* — you explicitly declare "this class is a virtual subclass of that ABC". `__subclasshook__` is *structural* — the ABC's classmethod inspects the candidate class's methods and decides conformance at `isinstance` time. `collections.abc` uses `__subclasshook__`; the `abc` module's user-facing API exposes `register`. Read this lesson with "nominal vs structural" front of mind.

## The Problem

Here is the bug. `boardly` has a plugin system — third-party classes implement a `Plugin` protocol with `name` and `run()`. The team writes:

```python
class Plugin:
    def name(self) -> str: raise NotImplementedError
    def run(self, ctx): raise NotImplementedError
```

This is *correct* but it has two problems:

1. **Subclasses can be instantiated without implementing the methods.** `class MyPlugin(Plugin): pass; MyPlugin()` works — `Plugin` is a regular class, not an ABC. The bug only surfaces when someone calls `MyPlugin().name()`, which is far from the construction site.
2. **Third-party classes that happen to have `name` and `run` are not `Plugin`s.** `isinstance(third_party, Plugin)` returns `False` even if the third-party class implements the contract — because it does not inherit.

A custom ABC fixes both:

```python
from abc import ABCMeta, abstractmethod

class Plugin(metaclass=ABCMeta):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def run(self, ctx): ...
```

Now `class MyPlugin(Plugin): pass; MyPlugin()` raises `TypeError` at construction. And third-party classes can be registered as virtual subclasses: `Plugin.register(ThirdPartyPlugin)` makes `isinstance(third_party, Plugin)` return `True`.

## The Code

```python
# boardly/plugin_abc.py
"""A custom ABC for plugins: ABCMeta + abstractmethod + register + __subclasshook__."""
from abc import ABCMeta, abstractmethod
from typing import Any, TYPE_CHECKING


class Plugin(metaclass=ABCMeta):
    """The boardly plugin contract.

    Two abstract methods: name() and run(ctx). Subclasses must implement both
    or instantiation raises TypeError. Third-party classes can be registered
    as virtual subclasses via Plugin.register(OtherClass).
    """

    @abstractmethod
    def name(self) -> str:
        """Return the plugin's display name."""

    @abstractmethod
    def run(self, ctx: dict) -> Any:
        """Execute the plugin against the boardly context."""

    # The classmethod form of register is also available; users can call it
    # as a decorator: @Plugin.register
    # or as a function: Plugin.register(SomeClass)


class CsvExportPlugin(Plugin):
    """A real plugin that implements the contract."""

    def name(self) -> str:
        return "csv_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to CSV"


# --- A third-party class that happens to implement the contract ---

class ThirdPartyJsonExport:
    """A class that did not inherit from Plugin but has the right methods."""

    def name(self) -> str:
        return "json_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to JSON"


# --- Register the third-party class as a virtual subclass ---

Plugin.register(ThirdPartyJsonExport)


# --- A structural __subclasshook__: any class with name and run is a Plugin ---

class StructuralPlugin(metaclass=ABCMeta):
    """Like Plugin but conformance is structural, not registered."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx): ...

    @classmethod
    def __subclasshook__(cls, subclass):
        """Decide conformance based on the methods present on `subclass`."""
        if cls is not StructuralPlugin:
            return NotImplemented   # delegate to the normal MRO check
        # Check whether subclass has both 'name' and 'run' attributes.
        if hasattr(subclass, "name") and hasattr(subclass, "run"):
            return True
        return NotImplemented   # fall back to default behaviour


if __name__ == "__main__":
    print("--- Plugin: ABCMeta + abstractmethod ---")
    try:
        Plugin()  # student expects this to fail
    except TypeError as e:
        print(f"Plugin() raises: {e}")

    p = CsvExportPlugin()
    print(f"CsvExportPlugin name: {p.name()}")
    print(f"run result: {p.run({'tickets': [1, 2, 3]})}")

    print("\n--- register: nominal virtual subclass ---")
    third = ThirdPartyJsonExport()
    print(f"isinstance(third, Plugin): {isinstance(third, Plugin)}")
    print(f"isinstance(third, CsvExportPlugin): {isinstance(third, CsvExportPlugin)}  (no, just Plugin)")

    print("\n--- __subclasshook__: structural conformance ---")
    class Unregistered:
        def name(self): return "x"
        def run(self, ctx): return "ok"
    u = Unregistered()
    print(f"isinstance(u, StructuralPlugin): {isinstance(u, StructuralPlugin)}")
    print(f"isinstance(u, Plugin): {isinstance(u, Plugin)}  (still False; Plugin uses register, not __subclasshook__)")

    print("\n--- the ABCMeta.__subclasses__ and __abstractmethods__ internals ---")
    print(f"Plugin.__abstractmethods__: {Plugin.__abstractmethods__}")
    print(f"StructuralPlugin.__subclasshook__ is callable: {callable(StructuralPlugin.__subclasshook__)}")
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports

```python
# boardly/plugin_abc.py
"""A custom ABC for plugins: ABCMeta + abstractmethod + register + __subclasshook__."""
from abc import ABCMeta, abstractmethod
from typing import Any, TYPE_CHECKING
```

`from abc import ABCMeta, abstractmethod` — `ABCMeta` is the metaclass that powers ABCs; `abstractmethod` is the decorator that marks a method as abstract. Both come from the `abc` module (Section 11), not `collections.abc`.

Note: in 3.4+, `from abc import ABC` works — `ABC` is a convenience class that uses `ABCMeta` as its metaclass. Inheriting from `ABC` is equivalent to `metaclass=ABCMeta`. Both are valid; this lesson uses `metaclass=ABCMeta` explicitly to make the mechanism visible.

### Lines 10–26: `Plugin` — the ABC

```python
class Plugin(metaclass=ABCMeta):
    """The boardly plugin contract.

    Two abstract methods: name() and run(ctx). Subclasses must implement both
    or instantiation raises TypeError. Third-party classes can be registered
    as virtual subclasses via Plugin.register(OtherClass).
    """

    @abstractmethod
    def name(self) -> str:
        """Return the plugin's display name."""

    @abstractmethod
    def run(self, ctx: dict) -> Any:
        """Execute the plugin against the boardly context."""

    # The classmethod form of register is also available; users can call it
    # as a decorator: @Plugin.register
    # or as a function: Plugin.register(SomeClass)
```

`class Plugin(metaclass=ABCMeta):` — the metaclass is what gives `Plugin` its ABC powers. `ABCMeta` is a subclass of `type` that overrides `__new__` to compute `__abstractmethods__` (a frozenset of names decorated with `@abstractmethod`) and overrides `__instancecheck__` and `__subclasscheck__` to consult `__subclasshook__`.

`@abstractmethod` on a method marks it as "must be overridden on a concrete subclass". `Plugin.__abstractmethods__` is `frozenset({"name", "run"})`. When you try to instantiate a subclass, `ABCMeta.__call__` checks the subclass's `__abstractmethods__`; if non-empty, it raises `TypeError`.

`@abstractmethod` works on functions, classmethods, staticmethods, and properties. The decorated method's body is irrelevant — the convention is to write either `...` or `raise NotImplementedError`.

### Lines 30–40: `CsvExportPlugin` — a real subclass

```python
class CsvExportPlugin(Plugin):
    """A real plugin that implements the contract."""

    def name(self) -> str:
        return "csv_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to CSV"
```

`class CsvExportPlugin(Plugin):` — inherit from `Plugin`. Override both abstract methods. `CsvExportPlugin.__abstractmethods__` is `frozenset()` (empty) because both methods are implemented on the subclass. `CsvExportPlugin()` is therefore constructible.

**Why no `@abstractmethod` on the overrides?** Because the subclass's overrides are concrete. `@abstractmethod` is a marker for "still abstract"; without it, the method is concrete and removes the name from the subclass's `__abstractmethods__`.

### Lines 44–55: A third-party class that does not inherit

```python
class ThirdPartyJsonExport:
    """A class that did not inherit from Plugin but has the right methods."""

    def name(self) -> str:
        return "json_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to JSON"
```

`ThirdPartyJsonExport` does not inherit from `Plugin`. It happens to have `name` and `run` methods that satisfy the contract. Without `register`, `isinstance(ThirdPartyJsonExport(), Plugin)` is `False`.

### Lines 58–59: `register` — the virtual-subclass mechanism

```python
# --- Register the third-party class as a virtual subclass ---

Plugin.register(ThirdPartyJsonExport)
```

`Plugin.register(ThirdPartyJsonExport)` adds `ThirdPartyJsonExport` to `Plugin`'s virtual-subclass registry (stored as `Plugin._abc_registry`). Now `isinstance(ThirdPartyJsonExport(), Plugin)` returns `True` — without inheritance. `ThirdPartyJsonExport` is still a subclass of `object`, not `Plugin`, in the MRO sense; but the `isinstance` check consults `Plugin._abc_registry` via `ABCMeta.__instancecheck__`.

`register` can be used as a decorator too:

```python
@Plugin.register
class ThirdPartyJsonExport:
    ...
```

This is the canonical use — decorate the third-party class definition itself so the registration is visible at the class definition site.

### Lines 63–78: `__subclasshook__` — the structural check

```python
class StructuralPlugin(metaclass=ABCMeta):
    """Like Plugin but conformance is structural, not registered."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx): ...

    @classmethod
    def __subclasshook__(cls, subclass):
        """Decide conformance based on the methods present on `subclass`."""
        if cls is not StructuralPlugin:
            return NotImplemented   # delegate to the normal MRO check
        # Check whether subclass has both 'name' and 'run' attributes.
        if hasattr(subclass, "name") and hasattr(subclass, "run"):
            return True
        return NotImplemented   # fall back to default behaviour
```

`__subclasshook__` is a classmethod that `ABCMeta.__subclasscheck__` (and `__instancecheck__`) calls when someone runs `isinstance(x, StructuralPlugin)` or `issubclass(C, StructuralPlugin)`. The hook returns:

- `True` — `subclass` is considered a subclass of `cls`.
- `False` — `subclass` is *not* a subclass.
- `NotImplemented` — fall back to the normal MRO-based check (the default behaviour).

`if cls is not StructuralPlugin: return NotImplemented` — important: `__subclasshook__` is inherited by subclasses. If you do not check `cls is StructuralPlugin`, the hook would also fire for subclasses of `StructuralPlugin`, which is rarely what you want. The check ensures the structural behaviour only applies to `StructuralPlugin` itself.

`if hasattr(subclass, "name") and hasattr(subclass, "run"): return True` — the structural check. Any class with `name` and `run` attributes (including methods) is considered a subclass. `Unregistered` (defined in the smoke test) has both, so `isinstance(Unregistered(), StructuralPlugin)` is `True` — without registration, without inheritance.

### Lines 80–85: The smoke test — `Plugin()` raises

```python
if __name__ == "__main__":
    print("--- Plugin: ABCMeta + abstractmethod ---")
    try:
        Plugin()  # student expects this to fail
    except TypeError as e:
        print(f"Plugin() raises: {e}")
```

`Plugin()` raises `TypeError: Can't instantiate abstract class Plugin without an implementation for abstract methods 'name', 'run'` (the message phrasing changed in Python 3.12; older Pythons printed `... with abstract methods name, run`). This is the ABC contract in action — abstract methods must be defined on the concrete subclass.

### Lines 87–89: A real subclass works

```python
    p = CsvExportPlugin()
    print(f"CsvExportPlugin name: {p.name()}")
    print(f"run result: {p.run({'tickets': [1, 2, 3]})}")
```

`CsvExportPlugin()` succeeds. Both abstract methods are implemented on the subclass; `__abstractmethods__` is empty; construction is allowed.

### Lines 91–93: `register` enables `isinstance` on the third-party class

```python
    print("\n--- register: nominal virtual subclass ---")
    third = ThirdPartyJsonExport()
    print(f"isinstance(third, Plugin): {isinstance(third, Plugin)}")
    print(f"isinstance(third, CsvExportPlugin): {isinstance(third, CsvExportPlugin)}  (no, just Plugin)")
```

`isinstance(third, Plugin)` is `True` — `register` made `ThirdPartyJsonExport` a virtual subclass of `Plugin`. `isinstance(third, CsvExportPlugin)` is `False` — registration is per-ABC, not inherited by subclasses of the ABC.

### Lines 95–100: `__subclasshook__` enables structural `isinstance`

```python
    print("\n--- __subclasshook__: structural conformance ---")
    class Unregistered:
        def name(self): return "x"
        def run(self, ctx): return "ok"
    u = Unregistered()
    print(f"isinstance(u, StructuralPlugin): {isinstance(u, StructuralPlugin)}")
    print(f"isinstance(u, Plugin): {isinstance(u, Plugin)}  (still False; Plugin uses register, not __subclasshook__)")
```

`Unregistered` has `name` and `run`. `isinstance(u, StructuralPlugin)` is `True` — the structural check fired. `isinstance(u, Plugin)` is `False` — `Plugin` does not have a `__subclasshook__` (it uses `register` only), so the structural check does not fire.

This is the distinction between the two mechanisms. `register` is nominal and explicit; `__subclasshook__` is structural and automatic. `collections.abc` uses `__subclasshook__` because the Python core team wanted any class with `__iter__` to be `Iterable`, regardless of inheritance.

### Lines 102–106: The internals

```python
    print("\n--- the ABCMeta.__subclasses__ and __abstractmethods__ internals ---")
    print(f"Plugin.__abstractmethods__: {Plugin.__abstractmethods__}")
    print(f"StructuralPlugin.__subclasshook__ is callable: {callable(StructuralPlugin.__subclasshook__)}")
```

`Plugin.__abstractmethods__` is `frozenset({"name", "run"})`. `ABCMeta.__new__` computed this set when `Plugin` was created by scanning the class body for `@abstractmethod`-decorated methods.

## Execution Trace

```bash
$ uv run python boardly/plugin_abc.py
--- Plugin: ABCMeta + abstractmethod ---
Plugin() raises: Can't instantiate abstract class Plugin without an implementation for abstract methods 'name', 'run'
CsvExportPlugin name: csv_export
run result: exported 3 tickets to CSV

--- register: nominal virtual subclass ---
isinstance(third, Plugin): True
isinstance(third, CsvExportPlugin): False  (no, just Plugin)

--- __subclasshook__: structural conformance ---
isinstance(u, StructuralPlugin): True
isinstance(u, Plugin): False  (still False; Plugin uses register, not __subclasshook__)

--- the ABCMeta.__subclasses__ and __abstractmethods__ internals ---
Plugin.__abstractmethods__: frozenset({'name', 'run'})
StructuralPlugin.__subclasshook__ is callable: True
```

## Common Mistakes

### Mistake 1: Forgetting `metaclass=ABCMeta`

```python
from abc import abstractmethod

class Plugin:
    @abstractmethod
    def name(self): ...
```

**Symptom:** `Plugin()` succeeds. The abstract-method decorator is decorative; no `TypeError` is raised at construction.

**Why:** Without `ABCMeta` as the metaclass, the class is a plain `class`. `@abstractmethod` adds a `__isabstractmethod__ = True` attribute to the method, but only `ABCMeta.__new__` collects those attributes into `__abstractmethods__`. A plain `type` metaclass does not.

**Fix:** Either `class Plugin(metaclass=ABCMeta):` or `from abc import ABC; class Plugin(ABC):` (the 3.4+ convenience shortcut).

### Mistake 2: Calling `register` on an instance instead of a class

```python
Plugin.register(third)   # student expects isinstance(third, Plugin) to work
```

**Symptom:** `isinstance(third, Plugin)` is still `False` — `register` did not do anything visible.

**Why:** `register` expects a *class* argument. Passing an instance adds it to the registry but the registry is consulted by `__instancecheck__` via `type(instance).__mro__`, not the instance itself. The instance's *class* is what needs to be registered.

**Fix:** `Plugin.register(type(third))` — or, better, register the class by name at the class definition site: `@Plugin.register\nclass ThirdPartyJsonExport: ...`.

### Mistake 3: `__subclasshook__` returns `True` for subclasses of the ABC

```python
class StructuralPlugin(metaclass=ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return True   # student thinks this is fine
```

**Symptom:** `isinstance(anything, StructuralPlugin)` returns `True` for *everything* — including subclasses that should not conform.

**Why:** Without the `if cls is not StructuralPlugin: return NotImplemented` guard, the hook returns `True` for any `cls` that inherits the hook. That includes subclasses of `StructuralPlugin` that might want their own structural rules.

**Fix:** Always start the hook with `if cls is not MyABC: return NotImplemented`. That ensures the structural behaviour only applies to the ABC you defined, not to subclasses.

## Engineering Trade-Offs

**Decision:** Use `register` for *nominal* virtual subclasses (you explicitly know the class). Use `__subclasshook__` for *structural* conformance (any class with the right methods).

**Both sides:**

`register` wins on:

1. Explicit intent — the registration is visible in the class definition or the call site.
2. Performance — `register` updates a set; `__subclasshook__` runs a method on every `isinstance` check.
3. Predictability — you know exactly which classes conform (the registered ones).

`__subclasshook__` wins on:

1. Open-set conformance — any class with the right methods conforms, including classes that did not exist when you wrote the ABC.
2. The `collections.abc` pattern — `isinstance(x, Iterable)` returns `True` for any class with `__iter__`, regardless of inheritance.
3. Third-party integration — you cannot always register a third-party class (you may not own the import); `__subclasshook__` lets the third-party class conform without code changes.

**Commitment:** `boardly/plugin_abc.py` defines `Plugin` with `register` (plugins are explicitly registered at startup) and `StructuralPlugin` with `__subclasshook__` (for the rare case where a third-party class satisfies the contract by accident). The rule: "Know the conforming classes? `register`. Open set? `__subclasshook__`."

## Exercises

1. **Exercise 1 — Verify `Plugin()` raises.** Try to instantiate `Plugin` and confirm `TypeError`. `Verify: uv run python -c "from abc import ABCMeta, abstractmethod\nclass P(metaclass=ABCMeta):\n  @abstractmethod\n  def m(self): ...\ntry:\n  P()\nexcept TypeError as e:\n  print('TypeError:', e)"`
2. **Exercise 2 — `register` enables `isinstance`.** Define a class with the right methods, register it, confirm `isinstance` is `True`. `Verify: uv run python -c "from abc import ABCMeta, abstractmethod\nclass P(metaclass=ABCMeta):\n  @abstractmethod\n  def m(self): pass\nclass Q:\n  def m(self): return 'q'\nP.register(Q)\nprint(isinstance(Q(), P))"`
3. **Exercise 3 — `__subclasshook__` makes it structural.** Define an ABC with `__subclasshook__` that checks for a method, and confirm a class with that method conforms without registration. `Verify: uv run python -c "from abc import ABCMeta, abstractmethod\nclass S(metaclass=ABCMeta):\n  @classmethod\n  def __subclasshook__(cls, sub):\n    if cls is not S: return NotImplemented\n    return hasattr(sub, 'x') or NotImplemented\nclass C:\n  def x(self): return 1\nprint(isinstance(C(), S))"`
4. **Exercise 4 — `__abstractmethods__` introspection.** Confirm `Plugin.__abstractmethods__` is `frozenset({'name', 'run'})`. `Verify: uv run python -c "from abc import ABCMeta, abstractmethod\nclass P(metaclass=ABCMeta):\n  @abstractmethod\n  def name(self): pass\n  @abstractmethod\n  def run(self, ctx): pass\nprint(P.__abstractmethods__)"`
5. **Exercise 5 — A custom ABC for boardly.** Define `class TicketFilter(metaclass=ABCMeta)` with `@abstractmethod def matches(self, ticket) -> bool`. Implement two subclasses. `Verify: uv run python -c "from abc import ABCMeta, abstractmethod\nclass TF(metaclass=ABCMeta):\n  @abstractmethod\n  def matches(self, t): pass\nclass StatusFilter(TF):\n  def __init__(self, s): self.s=s\n  def matches(self, t): return t.get('status')==self.s\nprint(StatusFilter('open').matches({'status':'open'}))"`

## Verification

```bash
$ uv run python boardly/plugin_abc.py
--- Plugin: ABCMeta + abstractmethod ---
Plugin() raises: Can't instantiate abstract class Plugin without an implementation for abstract methods 'name', 'run'
CsvExportPlugin name: csv_export
run result: exported 3 tickets to CSV

--- register: nominal virtual subclass ---
isinstance(third, Plugin): True
isinstance(third, CsvExportPlugin): False  (no, just Plugin)

--- __subclasshook__: structural conformance ---
isinstance(u, StructuralPlugin): True
isinstance(u, Plugin): False  (still False; Plugin uses register, not __subclasshook__)

--- the ABCMeta.__subclasses__ and __abstractmethods__ internals ---
Plugin.__abstractmethods__: frozenset({'name', 'run'})
StructuralPlugin.__subclasshook__ is callable: True
```

## Previously Learned Here

- [[05-collections-abc/04-Iterator-vs-Iterable]] — the contract pattern; this lesson generalises it to your own ABCs.
- [[05-collections-abc/01-The-ABC-Hierarchy]] — every ABC in `collections.abc` is built with the pattern this lesson walks.

## What's Next

[[05-collections-abc/06-abcs-vs-protocols]] — the closing canonical lesson. `collections.abc.Iterable` vs `typing.Protocol` with `__iter__`. Nominal ABCs (registered via `register` or `__subclasshook__`) vs structural `typing.Protocol` (with `runtime_checkable`). When each wins, and why the modern trend is towards `Protocol` for new code.

## Sources

- **Python `abc` module documentation** — https://docs.python.org/3/library/abc.html — accessed 2026-10-23 — the canonical reference for `ABCMeta`, `abstractmethod`, `register`, and the `__subclasshook__` pattern.
- **Python `collections.abc` source** — https://github.com/python/cpython/blob/3.12/Lib/_collections_abc.py — accessed 2026-10-23 — the `__subclasshook__` implementations for every ABC; this is the file to read once.
- **PEP 3119 — `__subclasshook__` design** — https://peps.python.org/pep-3119/#overloading-isinstance-and-issubclass — accessed 2026-10-23 — the design rationale for structural subtyping.

## What We Learned

- `ABCMeta` is the metaclass that powers ABCs; `@abstractmethod` marks methods that subclasses must implement.
- A subclass with non-empty `__abstractmethods__` raises `TypeError` at construction.
- `register(OtherClass)` adds `OtherClass` as a *virtual* subclass of the ABC — `isinstance` checks succeed without inheritance.
- `__subclasshook__` is the *structural* mechanism: a classmethod that decides conformance based on the candidate class's attributes.
- `collections.abc` uses `__subclasshook__` so any class with `__iter__` is `Iterable`, regardless of inheritance.
- `register` is for nominal virtual subclasses; `__subclasshook__` is for open-set structural conformance.
