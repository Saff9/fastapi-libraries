---
title: "Lesson 01: ABC and abstractmethod"
aliases:
 - abc.ABC
 - abstractmethod
 - abstract properties
 - abstract classmethods
 - ABCMeta shortcut
tags:
 - abc
 - abcmeta
 - abstractmethod
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[05-collections-abc/01-The-ABC-Hierarchy]]"
 - "[[05-collections-abc/05-Custom-ABCs]]"
related_lessons:
 - "[[11-abc/02-register-and-Virtual-Subclasses]]"
 - "[[11-abc/03-ABC-vs-Protocol-vs-collections-abc]]"
first_taught_in: "11-abc/01-ABC-and-abstractmethod"
---

# Lesson 01: ABC and abstractmethod

*`abc.ABC` (the 3.4+ shortcut for `metaclass=ABCMeta`), `@abstractmethod`, the construction-time `TypeError` that fires until every abstract is implemented, abstract properties (`@property` + `@abstractmethod`), and abstract classmethods. The mechanism behind `collections.abc` and every plugin system.*

**You're at the very beginning of Section 11.**

You have already used `collections.abc.Iterable` and `Sequence` for five lessons. You have seen the `ABCMeta` machinery in Section 05, Lesson 05, where we wrote `class Plugin(metaclass=ABCMeta)`. This lesson is the shorter, more idiomatic form — `class Plugin(ABC):` — and the discipline of `@abstractmethod` that goes with it. After this lesson you will be able to write an ABC the way the Python standard library itself writes one: small, declarative, and impossible to misuse silently.

Take your time. Type every example. **This is how you learn.**

#abc #abcmeta #abstractmethod #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define an ABC** using `abc.ABC` (the 3.4+ shortcut) and explain why it is preferred over the explicit `metaclass=ABCMeta` form.
2. **Use `@abstractmethod`** to mark methods a subclass must implement, and predict the exact `TypeError` raised when a subclass skips one.
3. **Define abstract properties** with `@property` + `@abstractmethod` (in that order), and abstract classmethods/staticmethods by stacking `@classmethod` (or `@staticmethod`) outside `@abstractmethod`.
4. **Introspect `__abstractmethods__`** to debug the frozenset of names a subclass still owes the ABC.

## Prerequisites

Before starting, you need:

- **[[05-collections-abc/01-The-ABC-Hierarchy]]** — the canonical lesson on what an ABC *is* and the tree `collections.abc` exposes.
- **[[05-collections-abc/05-Custom-ABCs]]** — the `metaclass=ABCMeta` form. This lesson is the same machinery, written more concisely.
- **About 35 minutes of focused time.**

**The most common gap: assuming `@abstractmethod` works without `ABCMeta` underneath.**

Students see the decorator and write `class Plugin: @abstractmethod def run(self): ...` — no `ABC` base, no `metaclass=ABCMeta`. The decorator attaches a `__isabstractmethod__ = True` flag to the function object, but only the `ABCMeta.__new__` metaclass call walks the class body and collects those flags into `__abstractmethods__`. Without `ABCMeta`, the flags are set on the functions but never read, so `Plugin()` succeeds and the contract is decorative. Read this lesson with "the metaclass and the decorator are a pair" front of mind.

## The Problem

Here is the bug. `boardly` has a persistence layer with three models — `Project`, `User`, `Ticket` — and the team writes a base repository:

```python
class Repository:
    def get(self, key: str): raise NotImplementedError
    def save(self, key: str, value: object) -> None: raise NotImplementedError
```

This is *correct* in that subclasses must override both methods. But it has two failure modes:

1. **Construction never fails.** `class Broken(Repository): pass; Broken()` succeeds — `Repository` is a regular class, not an ABC. The bug only surfaces when someone calls `Broken().get("proj-1")`, which is far from the construction site. By then the stack trace points at the abstract method, not at the missing override.
2. **`NotImplementedError` is an after-the-fact apology.** The error is raised on the *call*, not on the *instantiation*. The team wants the error the moment someone forgets to implement a method — at construction time, with the missing method's name in the message.

The fix is `abc.ABC` + `@abstractmethod`:

```python
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def get(self, key: str): ...
    @abstractmethod
    def save(self, key: str, value: object) -> None: ...
```

Now `class Broken(Repository): pass; Broken()` raises `TypeError: Can't instantiate abstract class Broken without an implementation for abstract method 'get'` — at the construction site, with the missing method's name in the message. The error moved from "the moment you call the missing method" to "the moment you build the object", which is exactly where you want it.

This lesson walks the full surface of that pair: `ABC`, `abstractmethod`, the abstract property, the abstract classmethod, and the introspection trick (`__abstractmethods__`) that tells you *which* methods a subclass still owes.

## The Code

```python
# boardly/repository_abc.py
"""An ABC for boardly repositories — ABC, abstractmethod, abstract property,
abstract classmethod. Subclasses cannot be instantiated until every abstract
is implemented."""
from abc import ABC, abstractmethod
from typing import Iterable


class Repository(ABC):
    """The boardly persistence contract.

    Four abstract members:
      - table (abstract property)
      - get(key) (abstract method)
      - save(key, value) (abstract method)
      - all_ids() (abstract classmethod)

    Subclasses cannot be instantiated until all four are implemented.
    Construction-time TypeError is the contract.
    """

    @property
    @abstractmethod
    def table(self) -> str:
        """The SQL table name for this repository."""

    @abstractmethod
    def get(self, key: str) -> object | None:
        """Return the row keyed by `key`, or None."""

    @abstractmethod
    def save(self, key: str, value: object) -> None:
        """Upsert `value` at `key`."""

    @classmethod
    @abstractmethod
    def all_ids(cls) -> Iterable[str]:
        """Return every key present in the backing store."""


class ProjectRepository(Repository):
    """A concrete repository for the Project model — all four implemented."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    @property
    def table(self) -> str:
        return "projects"

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def save(self, key: str, value: object) -> None:
        self._store[key] = value

    @classmethod
    def all_ids(cls) -> Iterable[str]:
        return ["proj-1", "proj-2"]


class IncompleteRepository(Repository):
    """A subclass that forgets all_ids and table — must fail to construct."""

    def get(self, key: str) -> object | None: ...
    def save(self, key: str, value: object) -> None: ...


if __name__ == "__main__":
    print("--- Repository is an ABC; direct instantiation fails ---")
    try:
        Repository()
    except TypeError as e:
        print(f"Repository() raises: {e}")

    print("\n--- ProjectRepository is concrete; works ---")
    repo = ProjectRepository()
    print(f"table: {repo.table}")
    print(f"all_ids: {ProjectRepository.all_ids()}")

    print("\n--- IncompleteRepository forgets all_ids and table ---")
    try:
        IncompleteRepository()
    except TypeError as e:
        print(f"IncompleteRepository() raises: {e}")

    print("\n--- __abstractmethods__ introspection ---")
    print(f"Repository.__abstractmethods__:        {Repository.__abstractmethods__}")
    print(f"ProjectRepository.__abstractmethods__: {ProjectRepository.__abstractmethods__}")
    print(f"IncompleteRepository.__abstractmethods__: {IncompleteRepository.__abstractmethods__}")
```

## Line-by-Line Deep Dive

### Lines 1–5: The import block

```python
# boardly/repository_abc.py
"""An ABC for boardly repositories — ABC, abstractmethod, abstract property,
abstract classmethod. Subclasses cannot be instantiated until every abstract
is implemented."""
from abc import ABC, abstractmethod
from typing import Iterable
```

`from abc import ABC, abstractmethod` — `ABC` is the 3.4+ helper class. Its body is exactly:

```python
class ABC(metaclass=ABCMeta):
    """Helper class that provides a standard way to create an ABC using
    inheritance, avoiding the sometimes confusing metaclass=ABCMeta syntax.
    """
```

So inheriting from `ABC` is *identical* to writing `metaclass=ABCMeta` — both make `ABCMeta` the metaclass of your class. `ABC` exists purely so you do not have to type `metaclass=ABCMeta` and so the syntax is the same as inheriting from any other class. Pre-3.4 codebases — and the `collections.abc` source itself, for historical reasons — write `class X(metaclass=ABCMeta):`; new code writes `class X(ABC):`.

`abstractmethod` is the only other public name you need from `abc`. It is a function (not a class) that sets `__isabstractmethod__ = True` on the function it decorates and returns the function unchanged.

`from typing import Iterable` — used only for the return-type annotation on `all_ids`. We could also write `from collections.abc import Iterable` (the typing re-export is an alias for the same class). This lesson uses `typing.Iterable` to keep annotations consistent with the rest of `boardly`.

### Lines 8–34: `Repository` — the ABC, with four abstract members

```python
class Repository(ABC):
    """The boardly persistence contract.

    Four abstract members:
      - table (abstract property)
      - get(key) (abstract method)
      - save(key, value) (abstract method)
      - all_ids() (abstract classmethod)

    Subclasses cannot be instantiated until all four are implemented.
    Construction-time TypeError is the contract.
    """

    @property
    @abstractmethod
    def table(self) -> str:
        """The SQL table name for this repository."""

    @abstractmethod
    def get(self, key: str) -> object | None:
        """Return the row keyed by `key`, or None."""

    @abstractmethod
    def save(self, key: str, value: object) -> None:
        """Upsert `value` at `key`."""

    @classmethod
    @abstractmethod
    def all_ids(cls) -> Iterable[str]:
        """Return every key present in the backing store."""
```

`class Repository(ABC):` — inheriting from `ABC` makes `ABCMeta` the metaclass of `Repository`. From here on, every operation the metaclass performs — including class creation — runs `ABCMeta.__new__`, which scans the class body for attributes carrying `__isabstractmethod__ = True` and assembles them into the `__abstractmethods__` frozenset on the new class.

`@abstractmethod def get(self, key): ...` — the simplest form. The decorator sets `__isabstractmethod__ = True` on the function object; `ABCMeta.__new__` collects the name `get` into `Repository.__abstractmethods__`. The body (`...`) is irrelevant — `abstractmethod` does not enforce the body; it only flags the function. Convention is `...` for a stub or `raise NotImplementedError` if you want a real fallback for subclasses that call `super().get(...)`.

`@property @abstractmethod def table(self) -> str: ...` — the abstract property form. The order matters: `@abstractmethod` must be the *innermost* decorator (closest to `def`), so it touches the function first; `@property` then wraps the function-turned-abstract into a `property` object. The resulting `property` carries `__isabstractmethod__ = True` (because `property` propagates the flag from its fget), and `ABCMeta.__new__` collects the name `table` into `__abstractmethods__`. Swap the order and `property` wraps a plain function, the abstract flag is lost, and the subclass can be instantiated without overriding `table` — the contract silently degrades.

`@classmethod @abstractmethod def all_ids(cls) -> Iterable[str]: ...` — the abstract classmethod form. Again, `@abstractmethod` is innermost: it touches the function first, then `@classmethod` wraps the abstract function into a `classmethod` descriptor. The same rule applies to `@staticmethod` for abstract staticmethods. The Python documentation spells out the order: "When `abstractmethod()` is applied in combination with other method decorators, it should be applied as the innermost decorator."

**Why is the innermost rule so strict?** Because the outer decorators (`property`, `classmethod`, `staticmethod`) create *new* descriptor objects that wrap the function. If `@abstractmethod` were outermost, it would decorate the descriptor — and the descriptor types (`property`, `classmethod`, `staticmethod`) are themselves functions that return distinct objects with their own attributes. The flag `__isabstractmethod__` would land on the descriptor wrapper, but `ABCMeta.__new__` checks the descriptor's *own* `__isabstractmethod__` — which `property`, `classmethod`, and `staticmethod` only forward if the underlying function had the flag set. So the flag has to be on the underlying function, which means `@abstractmethod` has to apply *before* the descriptor constructor.

**Why does `Repository` itself exist, then, if it cannot be instantiated?** Two reasons. First, it documents the contract — the four abstract members are the entire `Repository` interface, in one place. Second, it provides a nominal type for `isinstance` and for type annotations. `def load(repo: Repository) -> None` says "any subclass of `Repository`"; `mypy` accepts any subclass because `Repository` is nominal. A reader of the function knows exactly what `repo` can do without reading the implementation.

### Lines 37–55: `ProjectRepository` — a concrete subclass

```python
class ProjectRepository(Repository):
    """A concrete repository for the Project model — all four implemented."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    @property
    def table(self) -> str:
        return "projects"

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def save(self, key: str, value: object) -> None:
        self._store[key] = value

    @classmethod
    def all_ids(cls) -> Iterable[str]:
        return ["proj-1", "proj-2"]
```

`class ProjectRepository(Repository):` — inherit from `Repository`. Override all four abstract members. Notice three things:

1. **No `@abstractmethod` on the overrides.** The overrides are concrete; `ABCMeta.__new__` recomputes `ProjectRepository.__abstractmethods__` by walking the MRO and *subtracting* any name that has a non-abstract implementation on `ProjectRepository` itself. With all four overridden, `ProjectRepository.__abstractmethods__` becomes `frozenset()` — empty — and construction is allowed.
2. **`@property def table(self) -> str:` still uses the `property` decorator.** The override is a regular property; `abstractmethod` is *not* stacked underneath because the override is concrete. The name `table` is removed from `__abstractmethods__` because the new property on `ProjectRepository` does not carry `__isabstractmethod__ = True`.
3. **`__init__` is a regular method, not abstract.** You can mix concrete and abstract freely. `__init__` is the construction entrypoint; `ABCMeta.__call__` is what checks `__abstractmethods__` before delegating to `__init__`, so `__init__` runs *only after* the abstract-method check has passed.

**Why does `ABCMeta.__call__` perform the check and not `ABCMeta.__new__`?** Because the check needs `cls.__abstractmethods__` *on the most-derived class*, which is the class the user actually instantiates. `ABCMeta.__new__` runs at class-creation time and would set the attribute, but it does not know whether the user is about to subclass further. `__call__` is the metaclass's hook for `MyClass()` — it runs once per instantiation, on the class the user is constructing. The order is: `__call__` checks `cls.__abstractmethods__`; if non-empty, raise `TypeError`; otherwise, dispatch to `__new__`/`__init__` as usual.

### Lines 58–61: `IncompleteRepository` — partial implementation

```python
class IncompleteRepository(Repository):
    """A subclass that forgets all_ids and table — must fail to construct."""

    def get(self, key: str) -> object | None: ...
    def save(self, key: str, value: object) -> None: ...
```

`IncompleteRepository` overrides `get` and `save` — but forgets `table` and `all_ids`. `ABCMeta.__new__` walks the MRO, subtracts `get` and `save` (now non-abstract on the subclass), and leaves `table` and `all_ids` in `IncompleteRepository.__abstractmethods__`. So `IncompleteRepository()` raises `TypeError` listing those two names.

This is the partial-implementation gotcha: the subclass implements *some* of the abstract methods and the rest still block construction. The error message names the remaining ones, so the fix is mechanical.

### Lines 64–79: The smoke test — `Repository()` raises

```python
if __name__ == "__main__":
    print("--- Repository is an ABC; direct instantiation fails ---")
    try:
        Repository()
    except TypeError as e:
        print(f"Repository() raises: {e}")

    print("\n--- ProjectRepository is concrete; works ---")
    repo = ProjectRepository()
    print(f"table: {repo.table}")
    print(f"all_ids: {ProjectRepository.all_ids()}")
```

`Repository()` raises `TypeError: Can't instantiate abstract class Repository without an implementation for abstract methods 'all_ids', 'get', 'save', 'table'`. The wording changed in Python 3.12: pre-3.12 it was "Can't instantiate abstract class Repository with abstract methods all_ids, get, save, table"; 3.12+ rephrases to "without an implementation for abstract methods" — the contract is the same, the phrasing is clearer. Both name every missing method, which is the actionable part of the error.

`ProjectRepository()` succeeds. `repo.table` returns `"projects"` — the property fires. `ProjectRepository.all_ids()` returns the list — the classmethod fires. The contract is fulfilled because `__abstractmethods__` is empty on the subclass.

### Lines 81–86: `IncompleteRepository()` raises — partial implementation

```python
    print("\n--- IncompleteRepository forgets all_ids and table ---")
    try:
        IncompleteRepository()
    except TypeError as e:
        print(f"IncompleteRepository() raises: {e}")
```

`IncompleteRepository()` raises `TypeError: Can't instantiate abstract class IncompleteRepository without an implementation for abstract methods 'all_ids', 'table'`. The error names the two methods still owed — `get` and `save` are implemented, so they dropped out of `__abstractmethods__`.

### Lines 88–91: Introspecting `__abstractmethods__`

```python
    print("\n--- __abstractmethods__ introspection ---")
    print(f"Repository.__abstractmethods__:        {Repository.__abstractmethods__}")
    print(f"ProjectRepository.__abstractmethods__: {ProjectRepository.__abstractmethods__}")
    print(f"IncompleteRepository.__abstractmethods__: {IncompleteRepository.__abstractmethods__}")
```

`Repository.__abstractmethods__` is `frozenset({'get', 'table', 'all_ids', 'save'})` — set at class-creation time by `ABCMeta.__new__`. `ProjectRepository.__abstractmethods__` is `frozenset()` — empty, because all four are overridden on the subclass. `IncompleteRepository.__abstractmethods__` is `frozenset({'table', 'all_ids'})` — the two that are still owed.

`__abstractmethods__` is the single most useful introspection attribute on an ABC. When a subclass fails to construct, the error message tells you the names; when you want to know programmatically whether a class is fully concrete, `not cls.__abstractmethods__` is the test. `ABCMeta` itself uses this same test in `__call__`.

**Why is `__abstractmethods__` a frozenset, not a list?** Because it is *immutable* and *hashable* — you can use it as a dict key, and you cannot accidentally mutate it from a subclass. The frozenset is computed once at class creation by `ABCMeta.__new__` and never modified; a subclass's `__abstractmethods__` is a fresh frozenset, not a mutated copy of the parent's.

## Execution Trace

```bash
$ uv run python boardly/repository_abc.py
--- Repository is an ABC; direct instantiation fails ---
Repository() raises: Can't instantiate abstract class Repository without an implementation for abstract methods 'all_ids', 'get', 'save', 'table'

--- ProjectRepository is concrete; works ---
table: projects
all_ids: ['proj-1', 'proj-2']

--- IncompleteRepository forgets all_ids and table ---
IncompleteRepository() raises: Can't instantiate abstract class IncompleteRepository without an implementation for abstract methods 'all_ids', 'table'

--- __abstractmethods__ introspection ---
Repository.__abstractmethods__:        frozenset({'get', 'table', 'all_ids', 'save'})
ProjectRepository.__abstractmethods__: frozenset()
IncompleteRepository.__abstractmethods__: frozenset({'table', 'all_ids'})
```

## Common Mistakes

### Mistake 1: `@abstractmethod` without `ABCMeta` underneath

```python
from abc import abstractmethod

class Repository:
    @abstractmethod
    def get(self, key: str): ...
```

**Symptom:** `Repository()` succeeds. The abstract-method decorator is decorative; no `TypeError` is raised at construction.

**Why:** `@abstractmethod` sets `__isabstractmethod__ = True` on the function, but only `ABCMeta.__new__` walks the class body and collects those flags into `__abstractmethods__`. A plain `class` statement uses `type` as its metaclass, which does not perform that walk. The flag is set, the set is empty, and the contract is silent.

**Fix:** Inherit from `abc.ABC` (or write `metaclass=ABCMeta` explicitly). The base class *and* the decorator are a pair — neither alone is enough.

### Mistake 2: Stacking `@abstractmethod` outside `@property`

```python
class Repository(ABC):
    @abstractmethod
    @property
    def table(self) -> str: ...
```

**Symptom:** `ProjectRepository()` succeeds even if the subclass forgets to override `table`. The contract silently degrades.

**Why:** `@abstractmethod` is applied *after* `@property`, so it sets `__isabstractmethod__` on the `property` object — but `property` already wraps the original function, which has no abstract flag. When `ABCMeta.__new__` reads the `table` attribute on `Repository`, it sees a `property` whose fget is a plain function with `__isabstractmethod__ = False`. The flag never propagates. The order matters: `@abstractmethod` must be the *innermost* decorator.

**Fix:** Swap the order:

```python
@property
@abstractmethod
def table(self) -> str: ...
```

The Python documentation states the rule explicitly: "When `abstractmethod()` is applied in combination with other method decorators, it should be applied as the innermost decorator."

### Mistake 3: Re-applying `@abstractmethod` on overrides

```python
class ProjectRepository(Repository):
    @abstractmethod
    def get(self, key: str): ...   # student thinks this is "the override pattern"
```

**Symptom:** `ProjectRepository()` raises `TypeError` listing `get` — even though `get` is *defined* on the subclass.

**Why:** `@abstractmethod` on the override re-marks `get` as abstract. `ABCMeta.__new__` sees the flag, leaves `get` in `ProjectRepository.__abstractmethods__`, and the subclass cannot be instantiated.

**Fix:** Do *not* decorate overrides. The override is concrete — `abstractmethod` is a marker for "still abstract", not for "this is an override".

## Engineering Trade-Offs

**Decision:** Use `abc.ABC` (the 3.4+ shortcut) + `@abstractmethod` for plugin-style contracts where the contract owner wants to enforce implementation at construction time.

**Both sides:**

`abc.ABC` wins on:

1. **Construction-time enforcement.** `TypeError` at `MyClass()` is the strongest contract Python offers — far stronger than `raise NotImplementedError` in the body, which fires only when the missing method is called.
2. **Self-documenting hierarchy.** `class MyRepo(Repository)` says "I am a Repository"; the reader does not have to scan the methods.
3. **Stable across runtimes.** `abc.ABC` predates `typing.Protocol` (3.4 vs 3.8) and works on every Python 3.x. For libraries that support 3.7 or earlier, `abc.ABC` is the only structural-ish option.

`typing.Protocol` wins on:

1. **Structural conformance.** A class can conform without inheriting — useful for third-party classes you cannot edit. `abc.ABC` requires real inheritance (or `register`, Lesson 02).
2. **Static-only checks.** `Protocol` is a *static* type — `mypy`/`pyright` enforce structural subtyping without runtime cost. `abc.ABC` enforces at runtime only.
3. **No metaclass conflicts.** `Protocol` uses `_ProtocolMeta`, which composes with other metaclasses; `ABCMeta` is its own metaclass and can conflict if a subclass already has a different metaclass.

**Commitment:** `boardly/repository_abc.py` uses `abc.ABC` because repositories are an internal contract — the team owns every subclass, so nominal inheritance is fine, and the construction-time `TypeError` is the bug-shape the team wants. The rule: "Internal contract that we own? `abc.ABC`. Third-party plug-in contract? `typing.Protocol` (Lesson 03)."

## Exercises

1. **Exercise 1 — Verify `Repository()` raises.** Run the smoke test and confirm the exact `TypeError`. `Verify: uv run python -c "from boardly.repository_abc import Repository\ntry:\n    Repository()\nexcept TypeError as e:\n    print('TypeError:', e)"`
2. **Exercise 2 — `__abstractmethods__` is a frozenset.** Print `Repository.__abstractmethods__` and confirm it is a `frozenset`. `Verify: uv run python -c "from boardly.repository_abc import Repository\nprint(type(Repository.__abstractmethods__))"`
3. **Exercise 3 — Drop one method, see the error change.** Comment out `ProjectRepository.table` and re-run; confirm the error names only `table`. `Verify: uv run python -c "from abc import ABC, abstractmethod\nclass R(ABC):\n  @property\n  @abstractmethod\n  def table(self): ...\n  @abstractmethod\n  def get(self, k): ...\nclass Sub(R):\n  def get(self, k): return None\ntry:\n    Sub()\nexcept TypeError as e:\n    print('TypeError:', e)"`
4. **Exercise 4 — Abstract staticmethod.** Add an abstract `@staticmethod def schema_version() -> int` to `Repository` and override it on `ProjectRepository`. Confirm `ProjectRepository()` still works. `Verify: uv run python -c "from abc import ABC, abstractmethod\nclass R(ABC):\n  @staticmethod\n  @abstractmethod\n  def schema_version(): return 1\nclass Sub(R):\n  @staticmethod\n  def schema_version(): return 2\nprint(Sub.schema_version())"`
5. **Exercise 5 — A second concrete repository for `Ticket`.** Write `class TicketRepository(Repository)` with all four members. Add an abstract method `archive(ticket_id) -> None` to `Repository` and confirm both `ProjectRepository` and `TicketRepository` break until they implement it. `Verify: uv run python -c "from boardly.repository_abc import Repository\ntry:\n    Repository()\nexcept TypeError as e:\n    print('Repository still abstract:', 'archive' in str(e) or 'get' in str(e))"`

## Verification

```bash
$ uv run python boardly/repository_abc.py
--- Repository is an ABC; direct instantiation fails ---
Repository() raises: Can't instantiate abstract class Repository without an implementation for abstract methods 'all_ids', 'get', 'save', 'table'

--- ProjectRepository is concrete; works ---
table: projects
all_ids: ['proj-1', 'proj-2']

--- IncompleteRepository forgets all_ids and table ---
IncompleteRepository() raises: Can't instantiate abstract class IncompleteRepository without an implementation for abstract methods 'all_ids', 'table'

--- __abstractmethods__ introspection ---
Repository.__abstractmethods__:        frozenset({'get', 'table', 'all_ids', 'save'})
ProjectRepository.__abstractmethods__: frozenset()
IncompleteRepository.__abstractmethods__: frozenset({'table', 'all_ids'})
```

## Previously Learned Here

- [[05-collections-abc/01-The-ABC-Hierarchy]] — the canonical lesson on what an ABC is; this lesson is the user-facing API.
- [[05-collections-abc/05-Custom-ABCs]] — the explicit `metaclass=ABCMeta` form; this lesson is the same machinery, written more concisely with `abc.ABC`.
- [[05-collections-abc/06-abcs-vs-protocols]] — the trade-off this lesson hints at; Lesson 03 of this section goes deeper.

## What's Next

[[11-abc/02-register-and-Virtual-Subclasses]] — `ABCMeta.register(OtherClass)` makes an unrelated class a *virtual* subclass of your ABC: `isinstance(x, MyABC)` returns `True` without inheritance. The mechanism is `ABCMeta._abc_registry`, consulted by `__instancecheck__`. The lesson also walks `__subclasshook__` — the *structural* hook `collections.abc` uses to make `isinstance(x, Iterable)` true for any class with `__iter__`. After Lesson 02 you will know the two ways an ABC can "lie" to `isinstance` — `register` (nominal, explicit) and `__subclasshook__` (structural, automatic) — and when each is the right tool.

## Sources

- **Python `abc` module documentation** — https://docs.python.org/3/library/abc.html — accessed 2026-10-23 — the canonical reference for `ABC`, `ABCMeta`, `abstractmethod`, the decorator-ordering rules for abstract properties and classmethods, and the `__abstractmethods__` frozenset.
- **PEP 3119 — Introducing Abstract Base Classes** — https://peps.python.org/pep-3119/ — accessed 2026-10-23 — the original ABC PEP; the design rationale for `ABCMeta`, `__abstractmethods__`, and the construction-time check.
- **CPython `abc.py` source** — https://github.com/python/cpython/blob/3.12/Lib/abc.py — accessed 2026-10-23 — the file to read once; `ABC` is 4 lines and `abstractmethod` is 6.

## What We Learned

- `abc.ABC` (3.4+) is the shortcut for `metaclass=ABCMeta` — both make `ABCMeta` the metaclass of your class; `ABC` is preferred for new code.
- `@abstractmethod` sets `__isabstractmethod__ = True` on the function; `ABCMeta.__new__` collects flagged names into `__abstractmethods__`.
- `ABCMeta.__call__` checks `cls.__abstractmethods__` at construction time; if non-empty, raises `TypeError` naming every missing method — the contract is enforced at `MyClass()`, not at the missing-method call.
- For abstract properties: `@property` outside `@abstractmethod` (abstractmethod innermost). For abstract classmethods: `@classmethod` outside `@abstractmethod`. The same rule applies to `@staticmethod`.
- `__abstractmethods__` is a `frozenset`; each subclass gets a fresh frozenset computed by MRO subtraction — overrides remove names from the set.
- The decorator and the metaclass are a pair: neither alone enforces the contract. `@abstractmethod` on a plain `class` does nothing.
