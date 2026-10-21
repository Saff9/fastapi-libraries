---
title: "Lesson 02: register and Virtual Subclasses"
aliases:
 - ABCMeta.register
 - virtual subclasses
 - __subclasshook__
 - get_cache_token
tags:
 - abc
 - abcmeta
 - register
 - subclasshook
 - virtual-subclass
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "30–40 minutes"
prerequisites:
 - "[[11-abc/01-ABC-and-abstractmethod]]"
 - "[[05-collections-abc/05-Custom-ABCs]]"
related_lessons:
 - "[[11-abc/03-ABC-vs-Protocol-vs-collections-abc]]"
 - "[[05-collections-abc/01-The-ABC-Hierarchy]]"
---

# Lesson 02: register and Virtual Subclasses

*`ABCMeta.register(OtherClass)` for nominal virtual subclasses — no inheritance needed — `ABCMeta.__subclasshook__` for structural conformance (the hook `collections.abc.Iterable` uses to make `isinstance(x, Iterable)` true for any class with `__iter__`), and `get_cache_token()` for cache invalidation. The two ways an ABC can "lie" to `isinstance`.*

**You're at the very beginning of Section 11 — Lesson 02.**

Lesson 01 taught you the contract: `class Plugin(ABC)` + `@abstractmethod` and `TypeError` at construction time. But every contract you wrote there required real inheritance — `class MyPlugin(Plugin):`. That is too strict for one common case: third-party classes you cannot edit. You cannot retroactively make `requests.Session` a subclass of your `Closeable` ABC. The `abc` module gives you two escape hatches: `register`, which lets you declare "this class is a virtual subclass of my ABC" without inheritance, and `__subclasshook__`, which lets the ABC decide conformance at `isinstance` time based on the candidate class's attributes. This lesson walks both, and the cache-token mechanism that keeps `isinstance` results honest after a registration.

Take your time. Type every example. **This is how you learn.**

#abc #register #subclasshook

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `ABCMeta.register(cls)`** to declare a class as a virtual subclass of your ABC — `isinstance(x, MyABC)` returns `True` without inheritance.
2. **Distinguish real subclasses from virtual ones** — `__mro__`, `__subclasses__()`, and `__abstractmethods__` all behave differently between the two.
3. **Implement `__subclasshook__`** to make `isinstance` checks structural — any class with the right methods conforms, without registration.
4. **Use `get_cache_token()`** to invalidate any `isinstance` cache you maintain when a virtual subclass is registered.

## Prerequisites

Before starting, you need:

- **[[11-abc/01-ABC-and-abstractmethod]]** — `abc.ABC` + `@abstractmethod`; this lesson extends the contract with virtual registration.
- **[[05-collections-abc/05-Custom-ABCs]]** — the metaclass-level view of `register` and `__subclasshook__`; this lesson is the same mechanism, written for a fresh example.
- **About 35 minutes of focused time.**

**The most common gap: confusing `register` with `__subclasshook__`.**

`register` is *nominal* — you explicitly declare "this class is a virtual subclass of that ABC", once, at module load time. The registry is a set; `__instancecheck__` does a set lookup. `__subclasshook__` is *structural* — the ABC's classmethod inspects the candidate class's attributes on every `isinstance` check. `collections.abc` uses `__subclasshook__` so any class with `__iter__` is `Iterable`; user code typically uses `register` for one-off third-party adapters. Read this lesson with "nominal-and-explicit vs structural-and-automatic" front of mind.

## The Problem

Here is the bug. `boardly` has a plugin contract from Lesson 01:

```python
from abc import ABC, abstractmethod

class Plugin(ABC):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def run(self, ctx: dict): ...
```

The team writes a `LegacyJsonExport` adapter around an old internal library — a class that already has `name()` and `run()` and satisfies the contract *spiritually*, but does not inherit from `Plugin`. They cannot edit the class body; they only own the adapter call site:

```python
class LegacyJsonExport:
    def name(self) -> str: return "legacy_json"
    def run(self, ctx: dict): return f"exported {len(ctx.get('tickets', []))} tickets to JSON"
```

The team wants `isinstance(LegacyJsonExport(), Plugin)` to be `True` so existing `Plugin`-typed code paths accept the adapter. They cannot add `(Plugin)` to the class bases — that would make `LegacyJsonExport` itself a `Plugin` subclass and require it to be re-declared as one. The `abc` module's answer is `Plugin.register(LegacyJsonExport)`:

```python
Plugin.register(LegacyJsonExport)
# now: isinstance(LegacyJsonExport(), Plugin) is True
# but: LegacyJsonExport.__mro__ is still (LegacyJsonExport, object) — no inheritance
```

The class is now a *virtual subclass* of `Plugin`. `isinstance` and `issubclass` agree; the MRO does not. That distinction — `isinstance` lies, `__mro__` tells the truth — is the lesson.

This lesson walks the second mechanism too: `__subclasshook__`. The stdlib `collections.abc.Iterable` does *not* `register` every iterable class in the world — there are too many. Instead, `Iterable` defines a `__subclasshook__` that returns `True` for any class with `__iter__`. We will re-implement that hook for `boardly` and compare it to the `register` approach.

## The Code

```python
# boardly/plugin_virtual.py
"""register() and __subclasshook__ for the boardly Plugin contract.

Three demonstrations:
  1. Plugin.register(LegacyJsonExport) — virtual subclass, no inheritance.
  2. StructuralPlugin.__subclasshook__ — structural conformance, no register.
  3. get_cache_token() — the token that changes on every register().
"""
from abc import ABC, abstractmethod, get_cache_token
from typing import Any


class Plugin(ABC):
    """The boardly plugin contract — nominal, requires inheritance or register."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx: dict) -> Any: ...


class CsvExportPlugin(Plugin):
    """A real (inheriting) subclass — the only kind __subclasses__() sees."""

    def name(self) -> str:
        return "csv_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to CSV"


class LegacyJsonExport:
    """Third-party-ish class — does not inherit from Plugin."""

    def name(self) -> str:
        return "legacy_json"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to JSON"


# --- register: nominal virtual subclass, no inheritance ---
Plugin.register(LegacyJsonExport)


# --- __subclasshook__: structural conformance, no register needed ---

class StructuralPlugin(ABC):
    """Like Plugin but conformance is structural, checked at isinstance time."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx): ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not StructuralPlugin:
            return NotImplemented   # only fire for StructuralPlugin itself
        if hasattr(subclass, "name") and hasattr(subclass, "run"):
            return True
        return NotImplemented   # fall back to default MRO check


if __name__ == "__main__":
    print("--- Real subclass: CsvExportPlugin ---")
    p = CsvExportPlugin()
    print(f"isinstance(p, Plugin):                 {isinstance(p, Plugin)}")
    print(f"issubclass(CsvExportPlugin, Plugin):   {issubclass(CsvExportPlugin, Plugin)}")
    print(f"CsvExportPlugin in Plugin.__subclasses__(): "
          f"{CsvExportPlugin in Plugin.__subclasses__()}")

    print("\n--- Virtual subclass: LegacyJsonExport (no inheritance) ---")
    legacy = LegacyJsonExport()
    print(f"isinstance(legacy, Plugin):            {isinstance(legacy, Plugin)}")
    print(f"issubclass(LegacyJsonExport, Plugin):  {issubclass(LegacyJsonExport, Plugin)}")
    print(f"LegacyJsonExport in Plugin.__subclasses__(): "
          f"{LegacyJsonExport in Plugin.__subclasses__()}")
    print(f"LegacyJsonExport.__mro__:               "
          f"{[c.__name__ for c in LegacyJsonExport.__mro__]}")
    print(f"Plugin.__subclasses__():                "
          f"{[c.__name__ for c in Plugin.__subclasses__()]}")

    print("\n--- Structural ABC: StructuralPlugin ---")
    class AdHoc:
        def name(self): return "ad-hoc"
        def run(self, ctx): return "ok"
    a = AdHoc()
    print(f"isinstance(a, StructuralPlugin):        {isinstance(a, StructuralPlugin)}")
    print(f"isinstance(a, Plugin):                  "
          f"{isinstance(a, Plugin)}  (Plugin uses register, not __subclasshook__)")

    print("\n--- get_cache_token: changes when a virtual subclass is registered ---")
    t1 = get_cache_token()
    class FreshPlugin:
        def name(self): return "fresh"
        def run(self, ctx): return "ok"
    Plugin.register(FreshPlugin)
    t2 = get_cache_token()
    print(f"token before register(FreshPlugin): {t1}")
    print(f"token after  register(FreshPlugin): {t2}")
    print(f"token changed: {t1 != t2}")

    print("\n--- register as a decorator ---")
    @Plugin.register
    class DecoratedPlugin:
        def name(self): return "deco"
        def run(self, ctx): return "ok"
    print(f"isinstance(DecoratedPlugin(), Plugin):  {isinstance(DecoratedPlugin(), Plugin)}")
```

## Line-by-Line Deep Dive

### Lines 1–9: Imports

```python
# boardly/plugin_virtual.py
"""register() and __subclasshook__ for the boardly Plugin contract.

Three demonstrations:
  1. Plugin.register(LegacyJsonExport) — virtual subclass, no inheritance.
  2. StructuralPlugin.__subclasshook__ — structural conformance, no register.
  3. get_cache_token() — the token that changes on every register().
"""
from abc import ABC, abstractmethod, get_cache_token
from typing import Any
```

`from abc import ABC, abstractmethod, get_cache_token` — three names from `abc`. `ABC` is the 3.4+ base class (Lesson 01). `abstractmethod` is the decorator (Lesson 01). `get_cache_token` is the function this lesson introduces — it returns an opaque token (an `int` in CPython) that changes *every time* someone calls `register()` on any ABC in the process. The token is the mechanism `abc` uses to invalidate any cached `isinstance`/`issubclass` results that depend on registration state.

**Why is `get_cache_token` not a method on `ABCMeta`?** Because the registry is *global* — every `register()` call on any ABC in the process invalidates every cached `isinstance` result, regardless of which ABC the cache was for. A global token models that correctly. The CPython `collections` module uses the token to invalidate its `_collections_abc` caches; the standard library uses it internally for `copy` and `pickle`. User code rarely needs it — only if you cache `isinstance` results yourself.

### Lines 12–18: `Plugin` — the nominal ABC

```python
class Plugin(ABC):
    """The boardly plugin contract — nominal, requires inheritance or register."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx: dict) -> Any: ...
```

`Plugin` is the contract from Lesson 01. Two abstract methods, both required for instantiation. `Plugin()` raises `TypeError`. `class MyPlugin(Plugin):` works once both methods are overridden.

`Plugin` has no `__subclasshook__` of its own. `ABCMeta.__instancecheck__` consults `__subclasshook__`, and the default `ABCMeta.__subclasshook__` returns `NotImplemented` (which delegates back to the MRO check). So without `register`, only real subclasses of `Plugin` (or classes that explicitly inherit) report as `Plugin` instances.

### Lines 21–28: `CsvExportPlugin` — a real subclass

```python
class CsvExportPlugin(Plugin):
    """A real (inheriting) subclass — the only kind __subclasses__() sees."""

    def name(self) -> str:
        return "csv_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to CSV"
```

`class CsvExportPlugin(Plugin):` — real inheritance. `CsvExportPlugin.__mro__` is `(CsvExportPlugin, Plugin, object)`. `Plugin.__subclasses__()` returns `[CsvExportPlugin]` (plus any other real subclasses defined later). The MRO is the source of truth — `CsvExportPlugin` *is* a `Plugin` in every sense: construction-time check, MRO walk, `__subclasses__` listing, and `isinstance`/`issubclass` agreement.

### Lines 31–38: `LegacyJsonExport` — the third-party-shaped class

```python
class LegacyJsonExport:
    """Third-party-ish class — does not inherit from Plugin."""

    def name(self) -> str:
        return "legacy_json"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to JSON"
```

`LegacyJsonExport` does *not* inherit from `Plugin`. Its `__mro__` is `(LegacyJsonExport, object)`. The methods happen to satisfy the `Plugin` contract, but Python does not know that — the type system is nominal. Without `register`, `isinstance(LegacyJsonExport(), Plugin)` would be `False`.

**Why would you not just edit `LegacyJsonExport` to inherit from `Plugin`?** Three reasons, ranked by frequency: (1) you do not own the class — it lives in an internal library or a vendored dependency; (2) inheriting from `Plugin` would force `LegacyJsonExport` to be re-declared at its definition site, which might be hundreds of files away; (3) the class is already deployed in production and you do not want to invalidate any existing `isinstance(x, LegacyJsonExport)` checks. `register` lets you make the relationship from *your* code, without touching the third-party class.

### Lines 41–42: `register` — the virtual-subclass declaration

```python
# --- register: nominal virtual subclass, no inheritance ---
Plugin.register(LegacyJsonExport)
```

`Plugin.register(LegacyJsonExport)` adds `LegacyJsonExport` to `Plugin._abc_registry` (a `WeakSet` on `ABCMeta`). Now `isinstance(LegacyJsonExport(), Plugin)` returns `True`. The class itself is unchanged — its `__mro__` is still `(LegacyJsonExport, object)`. The MRO is the source of truth; `register` is a *runtime declaration* that bypasses the MRO for `isinstance` and `issubclass` only.

`register` is also a *decorator*, so the canonical use is:

```python
@Plugin.register
class LegacyJsonExport:
    def name(self) -> str: return "legacy_json"
    def run(self, ctx: dict): ...
```

This puts the registration at the class-definition site, so a reader of `LegacyJsonExport` knows immediately that it is a virtual `Plugin`. The two forms — function call and decorator — are identical in effect.

**Why is `register` a method on the metaclass (`ABCMeta.register`), not on `ABC` itself?** Because the registry is a per-class attribute on the metaclass. `ABCMeta.register(cls, subclass)` adds `subclass` to `cls._abc_registry`. Because `register` is on the metaclass, calling `MyABC.register(OtherClass)` is `ABCMeta.register(MyABC, OtherClass)` — the ABC is the implicit `cls`. The decorator form `@MyABC.register` works because the method returns the subclass unchanged.

### Lines 47–62: `StructuralPlugin` — the `__subclasshook__` ABC

```python
class StructuralPlugin(ABC):
    """Like Plugin but conformance is structural, checked at isinstance time."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx): ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not StructuralPlugin:
            return NotImplemented   # only fire for StructuralPlugin itself
        if hasattr(subclass, "name") and hasattr(subclass, "run"):
            return True
        return NotImplemented   # fall back to default MRO check
```

`__subclasshook__` is a `@classmethod` that `ABCMeta.__instancecheck__` and `ABCMeta.__subclasscheck__` call (via `__subclasshook__`) when someone runs `isinstance(x, StructuralPlugin)` or `issubclass(C, StructuralPlugin)`. The hook returns:

- `True` — `subclass` is considered a subclass of `cls` (and `isinstance` returns `True` for instances of `subclass`).
- `False` — `subclass` is *not* a subclass of `cls` (and `isinstance` returns `False`).
- `NotImplemented` — fall back to the default behaviour (MRO walk plus the registry).

`if cls is not StructuralPlugin: return NotImplemented` — the *critical guard*. `__subclasshook__` is inherited by subclasses; without the guard, a subclass of `StructuralPlugin` (say, `MyStructuralPlugin(StructuralPlugin)`) would inherit the same hook and answer `isinstance(x, MyStructuralPlugin)` queries as if they were `StructuralPlugin` queries. That is rarely what you want — different ABCs have different conformance rules. The guard ensures the hook only fires when the query is *about* `StructuralPlugin` itself, not its subclasses.

`if hasattr(subclass, "name") and hasattr(subclass, "run"): return True` — the structural check. Any class with `name` and `run` attributes is considered a `StructuralPlugin` subclass. `AdHoc` (defined in the smoke test) has both, so `isinstance(AdHoc(), StructuralPlugin)` is `True` — without inheritance, without registration.

`return NotImplemented` at the end — the fall-through. If `subclass` lacks one of the methods, return `NotImplemented` rather than `False`. The default `ABCMeta.__instancecheck__` will then try the MRO and the registry; if those also fail, the answer is `False`. Returning `NotImplemented` (rather than `False`) preserves the *real subclass* path: a class that inherits from `StructuralPlugin` should still report as a subclass even if the structural check would have said `False`.

**Why does `collections.abc` use `__subclasshook__` rather than `register`?** Because `Iterable`, `Sequence`, `Mapping`, and friends are contracts the world already satisfies — there are hundreds of iterable classes in CPython alone, plus an unbounded number in user code and third-party libraries. `register` would require someone to enumerate every one of them. `__subclasshook__` lets the ABC answer "is this class iterable?" by checking `__iter__` — the *one* method that makes a class iterable. One hook, infinite conforming classes.

### Lines 65–71: Real subclass — `__subclasses__()` agrees with `isinstance`

```python
if __name__ == "__main__":
    print("--- Real subclass: CsvExportPlugin ---")
    p = CsvExportPlugin()
    print(f"isinstance(p, Plugin):                 {isinstance(p, Plugin)}")
    print(f"issubclass(CsvExportPlugin, Plugin):   {issubclass(CsvExportPlugin, Plugin)}")
    print(f"CsvExportPlugin in Plugin.__subclasses__(): "
          f"{CsvExportPlugin in Plugin.__subclasses__()}")
```

For real subclasses, every check agrees. `isinstance(p, Plugin)` is `True`. `issubclass(CsvExportPlugin, Plugin)` is `True`. `CsvExportPlugin in Plugin.__subclasses__()` is `True` (the `__subclasses__` list is populated by `type.__subclasses__`, which tracks direct inheritors). The MRO and the registry agree.

### Lines 73–80: Virtual subclass — `__subclasses__()` disagrees with `isinstance`

```python
    print("\n--- Virtual subclass: LegacyJsonExport (no inheritance) ---")
    legacy = LegacyJsonExport()
    print(f"isinstance(legacy, Plugin):            {isinstance(legacy, Plugin)}")
    print(f"issubclass(LegacyJsonExport, Plugin):  {issubclass(LegacyJsonExport, Plugin)}")
    print(f"LegacyJsonExport in Plugin.__subclasses__(): "
          f"{LegacyJsonExport in Plugin.__subclasses__()}")
    print(f"LegacyJsonExport.__mro__:               "
          f"{[c.__name__ for c in LegacyJsonExport.__mro__]}")
    print(f"Plugin.__subclasses__():                "
          f"{[c.__name__ for c in Plugin.__subclasses__()]}")
```

For virtual subclasses, `isinstance` and `issubclass` agree — both `True`. But `LegacyJsonExport in Plugin.__subclasses__()` is `False` — `__subclasses__` tracks direct inheritors only; virtual registrations are stored separately in `Plugin._abc_registry`, which is not exposed by `__subclasses__`. And `LegacyJsonExport.__mro__` is `(LegacyJsonExport, object)` — `Plugin` is *not* in the MRO. The MRO tells the truth: there is no inheritance. The `isinstance` check lies: it consults the registry and reports `True`.

This is the *fundamental distinction* between a real subclass and a virtual one. A real subclass inherits methods from the ABC (via the MRO), is listed in `__subclasses__()`, and shows up in `inspect.getmro`. A virtual subclass gets only the `isinstance`/`issubclass` answer; it does not inherit any method, it does not appear in `__subclasses__`, and `super()` does not work to call the ABC's methods. The virtual subclass is a *runtime declaration* that bypasses the MRO for `isinstance` only.

**Why does this matter for `super()`?** Because `super()` walks the MRO. If `LegacyJsonExport` had a method that wanted to call `Plugin.name()`, `super().name()` would not find `Plugin.name` — `Plugin` is not in `LegacyJsonExport`'s MRO. Virtual subclassing is not a substitute for inheritance when the subclass needs the ABC's mixins or default implementations.

### Lines 82–87: `__subclasshook__` — structural conformance without registration

```python
    print("\n--- Structural ABC: StructuralPlugin ---")
    class AdHoc:
        def name(self): return "ad-hoc"
        def run(self, ctx): return "ok"
    a = AdHoc()
    print(f"isinstance(a, StructuralPlugin):        {isinstance(a, StructuralPlugin)}")
    print(f"isinstance(a, Plugin):                  "
          f"{isinstance(a, Plugin)}  (Plugin uses register, not __subclasshook__)")
```

`AdHoc` has `name` and `run` but is not registered anywhere. `isinstance(a, StructuralPlugin)` is `True` — the `__subclasshook__` fired. `isinstance(a, Plugin)` is `False` — `Plugin` has no `__subclasshook__`, so only the registry (which does not contain `AdHoc`) and the MRO (which does not include `Plugin`) are consulted.

This is the contrast between the two mechanisms:

- `register` is *nominal* — explicit, once, at module load. The registry is a set; `__instancecheck__` does a set lookup. Predictable, fast, requires you to know the conforming classes up front.
- `__subclasshook__` is *structural* — automatic, on every `isinstance` call. The hook inspects the candidate class's attributes. Open-set — any class with the right methods conforms, including classes that did not exist when you wrote the ABC.

### Lines 89–98: `get_cache_token` — the cache-invalidation signal

```python
    print("\n--- get_cache_token: changes when a virtual subclass is registered ---")
    t1 = get_cache_token()
    class FreshPlugin:
        def name(self): return "fresh"
        def run(self, ctx): return "ok"
    Plugin.register(FreshPlugin)
    t2 = get_cache_token()
    print(f"token before register(FreshPlugin): {t1}")
    print(f"token after  register(FreshPlugin): {t2}")
    print(f"token changed: {t1 != t2}")
```

`get_cache_token()` returns an opaque token — in CPython, an `int` (the `_abc_invalidation_counter` attribute on `ABCMeta`, initialised to `0` in `_py_abc.py`) that increments on every `register()` call anywhere in the process. The token is the cache-invalidation signal: if you cache `isinstance` results yourself, store the token alongside the cache; on the next lookup, compare the stored token to the current one. If they differ, a `register()` happened since your cache was built and your cached `isinstance` results may be stale.

Note that by the time *your* code runs, the token is already well past `0` — the stdlib itself calls `register()` (and the import of `collections.abc` triggers more) during interpreter startup. On a fresh 3.12 process the token sits at around `23` before any user code executes; the absolute value is non-deterministic and only the *difference* between two snapshots is meaningful.

This is the mechanism `copy.deepcopy` and `collections.OrderedDict`-as-cache use internally. User code rarely needs it — `isinstance` itself is fast (a few microseconds), and the `ABCMeta.__instancecheck__` cache is per-class. But if you memoize a function that branches on `isinstance(x, MyABC)` and you support third-party plugins calling `MyABC.register(TheirClass)` at runtime, you must invalidate your cache when the token changes.

**Why does the token increment on *any* `register()` call, not just `register()` on `MyABC`?** Because the cache that `abc` itself maintains (`_abc_cache` on `ABCMeta`) is shared across all ABCs. One global token models that correctly — there is no per-ABC token because the cache is not per-ABC. This is a design choice from the original PEP 3119 implementation; you can read it in `Lib/abc.py`.

### Lines 100–106: `register` as a decorator

```python
    print("\n--- register as a decorator ---")
    @Plugin.register
    class DecoratedPlugin:
        def name(self): return "deco"
        def run(self, ctx): return "ok"
    print(f"isinstance(DecoratedPlugin(), Plugin):  {isinstance(DecoratedPlugin(), Plugin)}")
```

`@Plugin.register` is the decorator form. It registers `DecoratedPlugin` as a virtual subclass of `Plugin` at class-definition time. The decorator returns the class unchanged — the registration is a side effect, not a transformation. The decorator form is preferred when you own the class definition; the function-call form is preferred when the class is defined elsewhere (you cannot decorate a class you did not write).

## Execution Trace

```bash
$ uv run python boardly/plugin_virtual.py
--- Real subclass: CsvExportPlugin ---
isinstance(p, Plugin):                 True
issubclass(CsvExportPlugin, Plugin):   True
CsvExportPlugin in Plugin.__subclasses__(): True

--- Virtual subclass: LegacyJsonExport (no inheritance) ---
isinstance(legacy, Plugin):            True
issubclass(LegacyJsonExport, Plugin):  True
LegacyJsonExport in Plugin.__subclasses__(): False
LegacyJsonExport.__mro__:               ['LegacyJsonExport', 'object']
Plugin.__subclasses__():                ['CsvExportPlugin']

--- Structural ABC: StructuralPlugin ---
isinstance(a, StructuralPlugin):        True
isinstance(a, Plugin):                  False  (Plugin uses register, not __subclasshook__)

--- get_cache_token: changes when a virtual subclass is registered ---
token before register(FreshPlugin): 25
token after  register(FreshPlugin): 26
token changed: True

--- register as a decorator ---
isinstance(DecoratedPlugin(), Plugin):  True
```

(The exact `get_cache_token` numbers depend on how many `register()` calls have happened in the process before your script ran; the *difference* between the before and after token is the invariant — it increments by 1 per `register()` call.)

## Common Mistakes

### Mistake 1: `register` on an instance instead of a class

```python
third = LegacyJsonExport()
Plugin.register(third)   # student expects isinstance(third, Plugin) to work
```

**Symptom:** `isinstance(third, Plugin)` is still `False` — the registration did nothing visible.

**Why:** `register` expects a *class* argument. Passing an instance adds the instance to the registry, but `__instancecheck__` consults `type(instance).__mro__` and the registry of *classes*; an instance is not a class and is never consulted. The instance's *class* is what needs to be registered.

**Fix:** `Plugin.register(type(third))` — or, better, register the class by name at the class-definition site: `@Plugin.register\nclass LegacyJsonExport: ...`.

### Mistake 2: `__subclasshook__` returns `True` for subclasses of the ABC

```python
class StructuralPlugin(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return True   # student thinks this is fine
```

**Symptom:** `isinstance(anything, StructuralPlugin)` returns `True` for *everything* — including subclasses of `StructuralPlugin` that should not conform.

**Why:** Without the `if cls is not StructuralPlugin: return NotImplemented` guard, the hook returns `True` for any `cls` that inherits the hook. That includes subclasses of `StructuralPlugin` that might want their own structural rules. The hook fires for *every* ABC that inherits it, not just `StructuralPlugin` itself.

**Fix:** Always start the hook with `if cls is not MyABC: return NotImplemented`. That ensures the structural behaviour only applies to the ABC you defined, not to its subclasses.

### Mistake 3: Trusting `isinstance` after `register` to mean "inherits from"

```python
Plugin.register(LegacyJsonExport)
super(LegacyJsonExport, LegacyJsonExport()).name()  # student expects Plugin.name
```

**Symptom:** `AttributeError: 'super' object has no attribute 'name'` — or, depending on the Python version, `TypeError: super(type, obj): obj must be an instance or subtype of type`.

**Why:** `super()` walks the MRO. `LegacyJsonExport.__mro__` is `(LegacyJsonExport, object)` — `Plugin` is not in the MRO. `register` only updates `__instancecheck__`; it does not change the MRO. `super()` cannot find `Plugin.name` because `Plugin` is not a real base class.

**Fix:** Do not use `register` when the subclass needs the ABC's method implementations. Either inherit (and use `super()` normally) or re-implement the method on the subclass. Virtual subclassing is a typing declaration, not an inheritance relationship.

## Engineering Trade-Offs

**Decision:** Use `register` for *nominal* virtual subclasses (you know the conforming classes). Use `__subclasshook__` for *structural* conformance (any class with the right methods). Use `get_cache_token` only when you cache `isinstance` results across plugin loads.

**Both sides:**

`register` wins on:

1. **Explicit intent.** The registration is a statement at the class-definition site or in an adapter module; readers know exactly which classes conform.
2. **Performance.** The registry is a `WeakSet`; `__instancecheck__` does a set lookup. `__subclasshook__` runs a method on every check.
3. **Predictability.** The set of conforming classes is closed — you listed them. No class outside the registry conforms.

`__subclasshook__` wins on:

1. **Open-set conformance.** Any class with the right methods conforms, including classes that did not exist when you wrote the ABC.
2. **Third-party integration.** You cannot always register a third-party class (you may not own the import); `__subclasshook__` lets the third-party class conform without code changes on either side.
3. **The `collections.abc` pattern.** `isinstance(x, Iterable)` returns `True` for any class with `__iter__` — by design, because the Python core team wanted the contract to be open-ended.

`get_cache_token` wins on:

1. **Cache correctness across plugin loads.** If your framework loads plugins at runtime and the plugins call `register()`, your cached `isinstance` results may be stale. The token is the invalidation signal.
2. **Standard-library parity.** `copy`, `pickle`, and `collections` use the token; matching their pattern makes your cache consistent with the rest of the ecosystem.

**Commitment:** `boardly/plugin_virtual.py` defines `Plugin` with `register` (plugins are explicitly registered at startup; the set is closed and known) and `StructuralPlugin` with `__subclasshook__` (for the rare case where a third-party class satisfies the contract by accident and the team cannot edit it). The rule: "Know the conforming classes? `register`. Open set? `__subclasshook__`. Caching `isinstance` across plugin loads? `get_cache_token`."

## Exercises

1. **Exercise 1 — Verify `Plugin()` raises.** Try to instantiate `Plugin` and confirm `TypeError`. `Verify: uv run python -c "from boardly.plugin_virtual import Plugin\ntry:\n    Plugin()\nexcept TypeError as e:\n    print('TypeError:', e)"`
2. **Exercise 2 — `register` enables `isinstance`.** Define a class with `name` and `run`, register it, confirm `isinstance` is `True`. `Verify: uv run python -c "from abc import ABC, abstractmethod\nclass P(ABC):\n  @abstractmethod\n  def name(self): ...\n  @abstractmethod\n  def run(self, ctx): ...\nclass Q:\n  def name(self): return 'q'\n  def run(self, ctx): return 'ok'\nP.register(Q)\nprint(isinstance(Q(), P))"`
3. **Exercise 3 — `__subclasshook__` makes it structural.** Define an ABC with `__subclasshook__` that checks for a method, and confirm a class with that method conforms without registration. `Verify: uv run python -c "from abc import ABC, abstractmethod\nclass S(ABC):\n  @classmethod\n  def __subclasshook__(cls, sub):\n    if cls is not S: return NotImplemented\n    return hasattr(sub, 'x') or NotImplemented\nclass C:\n  def x(self): return 1\nprint(isinstance(C(), S))"`
4. **Exercise 4 — Virtual subclass is *not* in `__subclasses__()`.** Register a class as virtual, confirm `isinstance` is `True` but `__subclasses__()` does not list it. `Verify: uv run python -c "from abc import ABC, abstractmethod\nclass A(ABC):\n  pass\nclass B: pass\nA.register(B)\nprint(isinstance(B(), A), B in A.__subclasses__())"`
5. **Exercise 5 — `get_cache_token` changes on `register`.** Snapshot the token, call `register`, confirm the token incremented. `Verify: uv run python -c "from abc import ABC, get_cache_token\nclass A(ABC): pass\nclass B: pass\nt1 = get_cache_token()\nA.register(B)\nt2 = get_cache_token()\nprint(t1 != t2, t2 - t1)"`

## Verification

```bash
$ uv run python boardly/plugin_virtual.py
--- Real subclass: CsvExportPlugin ---
isinstance(p, Plugin):                 True
issubclass(CsvExportPlugin, Plugin):   True
CsvExportPlugin in Plugin.__subclasses__(): True

--- Virtual subclass: LegacyJsonExport (no inheritance) ---
isinstance(legacy, Plugin):            True
issubclass(LegacyJsonExport, Plugin):  True
LegacyJsonExport in Plugin.__subclasses__(): False
LegacyJsonExport.__mro__:               ['LegacyJsonExport', 'object']
Plugin.__subclasses__():                ['CsvExportPlugin']

--- Structural ABC: StructuralPlugin ---
isinstance(a, StructuralPlugin):        True
isinstance(a, Plugin):                  False  (Plugin uses register, not __subclasshook__)

--- get_cache_token: changes when a virtual subclass is registered ---
token before register(FreshPlugin): 25
token after  register(FreshPlugin): 26
token changed: True

--- register as a decorator ---
isinstance(DecoratedPlugin(), Plugin):  True
```

## Previously Learned Here

- [[11-abc/01-ABC-and-abstractmethod]] — `ABC` + `@abstractmethod`; this lesson extends the contract with virtual registration.
- [[05-collections-abc/05-Custom-ABCs]] — the metaclass-level view of `register` and `__subclasshook__`; this lesson is the user-facing API on top.
- [[05-collections-abc/01-The-ABC-Hierarchy]] — the ABC tree `collections.abc` builds with `__subclasshook__`.

## What's Next

[[11-abc/03-ABC-vs-Protocol-vs-collections-abc]] — the decision lesson. `abc.ABC` (nominal, must inherit, runtime `TypeError`), `typing.Protocol` (structural at static-check time, `@runtime_checkable` opt-in), and `collections.abc.Iterable` (structural at runtime via `__subclasshook__`, pre-defined contracts). When each wins, and why the modern trend is towards `Protocol` for new custom contracts while `collections.abc` is not going anywhere for the stdlib contracts.

## Sources

- **Python `abc` module documentation** — https://docs.python.org/3/library/abc.html — accessed 2026-10-23 — the canonical reference for `register`, `__subclasshook__`, `get_cache_token`, and the `_abc_registry` / `_abc_cache` internals.
- **PEP 3119 — `__subclasshook__` design** — https://peps.python.org/pep-3119/#overloading-isinstance-and-issubclass — accessed 2026-10-23 — the design rationale for structural subtyping at the runtime level.
- **CPython `abc.py` source** — https://github.com/python/cpython/blob/3.12/Lib/abc.py — accessed 2026-10-23 — the file to read once; `register`, `__instancecheck__`, and `get_cache_token` are all here.

## What We Learned

- `ABCMeta.register(OtherClass)` adds `OtherClass` as a *virtual* subclass of the ABC — `isinstance(x, MyABC)` returns `True` without inheritance.
- A real subclass appears in `__subclasses__()` and `__mro__`; a virtual subclass does neither — `isinstance` lies, `__mro__` tells the truth.
- `__subclasshook__` is the *structural* mechanism: a `@classmethod` that decides conformance based on the candidate class's attributes. `collections.abc.Iterable` uses it to make any class with `__iter__` conform.
- Always guard `__subclasshook__` with `if cls is not MyABC: return NotImplemented` — the hook is inherited by subclasses.
- `get_cache_token()` returns an opaque token that increments on every `register()` call anywhere in the process; use it to invalidate any `isinstance` cache you maintain.
- `register` is for nominal virtual subclasses (closed set); `__subclasshook__` is for open-set structural conformance.
