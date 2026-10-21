---
title: "Lesson 05: Protocol — Structural Typing"
aliases:
 - Protocol Structural Typing
 - 05-Protocol-Structural-Typing
 - Protocol
 - runtime_checkable
 - structural typing
tags:
 - typing
 - protocol
 - pep-544
 - structural-typing
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "45–60 minutes"
prerequisites:
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[01-typing/07-TypedDict]]"
 - "[[11-abc/01-ABC-and-abstractmethod]]"
first_taught_in: "01-typing/05-Protocol-Structural-Typing"
---

# Lesson 05: Protocol — Structural Typing

*`Protocol` (PEP 544) for duck typing that the type-checker understands — and `@runtime_checkable` for when you need `isinstance` to work, with its limitations.*

**You're at the very beginning of Section 01's plug-in-points lesson.**

You have written `class FileStore` and `class MemoryStore`. They both have a `search()` method and a `close()` method. You want a function that takes "either kind of store" — but you do not want to make them inherit from a common base class (they have nothing in common except the methods; inheritance is overkill). In Python, that is *duck typing*: "if it quacks like a `Closable`, it is a `Closable`". PEP 544's `Protocol` brings duck typing into the type system. Take your time. Type every example. **This is how you learn.**

#typing #protocol #structural-typing #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define** a `Protocol` with method and attribute members and explain how a class satisfies it structurally (no inheritance required).
2. **Apply** `@runtime_checkable` to enable `isinstance` against a Protocol, and explain the *only* thing it checks (method names — *not* signatures).
3. **Use** a `Protocol` as a `TypeVar`'s `bound=...` — structural bounds, not class-hierarchy bounds.
4. **Define** a generic `Protocol[T]` for "anything that is a `Repository` of `T`" and pass concrete implementations through it.
5. **Choose** between `Protocol` and `ABC` for a given extension point and defend the choice.

## Prerequisites

Before starting, you need:

- **[[01-typing/03-TypeVar-and-Generics]]** — `TypeVar("T", bound=X)` for structural bounds.
- **About 45–60 minutes of focused time.**

**The most common gap: assuming `@runtime_checkable` checks signatures.**

Students arrive having seen `isinstance(x, MyProtocol)` and assume the check verifies that `x` has all the right methods *with the right signatures*. It does *not*. `@runtime_checkable` checks only that the methods named in the Protocol *exist as attributes on the object*. The argument types, return types, and even the callable status are not verified. A `Protocol` with `def close(self) -> None: ...` will return `True` for `isinstance(obj, MyProtocol)` on an object whose `close` attribute is a *string*. This is the single most dangerous `Protocol` misconception.

## The Problem

Here is the bug this lesson prevents. boardly has three "stores": a file store, a memory store, and (eventually) a Postgres-backed store. They share two methods — `search(q)` and `close()` — and that is it. The first version of the codebase did this:

```python
class BaseStore:
    def search(self, q: str) -> list: raise NotImplementedError
    def close(self) -> None: raise NotImplementedError

class FileStore(BaseStore):
    def search(self, q: str) -> list: ...
    def close(self) -> None: ...

class MemoryStore(BaseStore):
    def search(self, q: str) -> list: ...
    def close(self) -> None: ...
```

This works but it has two problems. (1) **Inherited coupling**: any future store *must* inherit from `BaseStore`, even if it has its own class hierarchy already (e.g., a SQLAlchemy `Session` subclass that we want to adapt). (2) **No third-party compatibility**: a `MemoryStore` from a different library that has the right methods but does not inherit from `BaseStore` cannot be passed to `run_query`. The type system is closed where it should be open.

PEP 544's `Protocol` solves both. You define a Protocol with the methods; any class that has those methods (structurally) satisfies the Protocol — no inheritance, no registration. You can pass any third-party class that fits.

## The Code

```python
# boardly/protocol_structural.py
"""boardly — Protocol (PEP 544) for duck typing with a static type-checker."""
from typing import Protocol, runtime_checkable, TypeVar, get_type_hints

# --- A plain Protocol: anything with a .close() method is Closable. ---
# NOTE: not @runtime_checkable — isinstance() against this will TypeError.
class Closable(Protocol):
    def close(self) -> None: ...

# A runtime-checkable Protocol: isinstance() works (but checks names only).
@runtime_checkable
class Searchable(Protocol):
    def search(self, q: str) -> list: ...

# boardly models that satisfy the protocols structurally — no inheritance.
class FileStore:
    """Stores tickets on disk. Has close() and search() but inherits from nothing."""
    def close(self) -> None:
        print("file store closed")
    def search(self, q: str) -> list:
        return [f"file-match-{q}"]

class MemoryStore:
    """Stores tickets in memory. Same shape, different class."""
    def close(self) -> None:
        print("memory store closed")
    def search(self, q: str) -> list:
        return [f"mem-match-{q}"]

# A function typed against the Protocol, not the concrete classes.
def run_query(store: Searchable, q: str) -> list:
    return store.search(q)

def cleanup(store: Closable) -> None:
    store.close()

# --- Protocol with non-method members (attributes). ---
@runtime_checkable
class HasTicketId(Protocol):
    ticket_id: int

class Ticket:
    def __init__(self, ticket_id: int) -> None:
        self.ticket_id = ticket_id

# --- Generic Protocol. ---
T = TypeVar("T")

class Repository(Protocol[T]):
    def get(self, id: int) -> T | None: ...
    def put(self, id: int, value: T) -> None: ...

class InMemoryTicketRepo:
    def __init__(self) -> None:
        self._db: dict[int, Ticket] = {}
    def get(self, id: int) -> Ticket | None:
        return self._db.get(id)
    def put(self, id: int, value: Ticket) -> None:
        self._db[id] = value

if __name__ == "__main__":
    fs = FileStore()
    ms = MemoryStore()
    print("file search:", run_query(fs, "alpha"))
    print("mem search:", run_query(ms, "beta"))
    cleanup(fs)
    cleanup(ms)

    # runtime_checkable lets you isinstance against the Protocol.
    print("fs is Searchable:", isinstance(fs, Searchable))

    # Closable is NOT @runtime_checkable — isinstance raises TypeError.
    try:
        isinstance(fs, Closable)
    except TypeError as exc:
        print("isinstance(fs, Closable) raised:", exc)

    t = Ticket(ticket_id=42)
    print("t is HasTicketId:", isinstance(t, HasTicketId))

    # Generic Protocol — InMemoryTicketRepo is structurally a Repository[Ticket].
    repo: Repository[Ticket] = InMemoryTicketRepo()
    repo.put(1, Ticket(ticket_id=1))
    fetched = repo.get(1)
    print("repo get(1):", fetched.ticket_id if fetched else None)
```

## Line-by-Line Deep Dive

### Lines 1–5: Module header and imports

```python
# boardly/protocol_structural.py
"""boardly — Protocol (PEP 544) for duck typing with a static type-checker."""
from typing import Protocol, runtime_checkable, TypeVar, get_type_hints
```

`Protocol` (3.8+) and `runtime_checkable` (3.8+) are both available since Python 3.8 — they were introduced by PEP 544. In 3.12 they are mature and stable. `Protocol` is the base class for all structural types; `runtime_checkable` is a decorator that opts a Protocol into `isinstance` support. We import `TypeVar` for the generic Protocol at the bottom of the file.

**Why does `Protocol` need `runtime_checkable` to be checked at runtime?**

Because checking at runtime is *expensive*. The check would have to walk the object's attributes, compare each method's signature to the Protocol's, and possibly recurse into nested types. Python's design choice: make `isinstance` against a Protocol opt-in via `@runtime_checkable`, and even then make it shallow (only check attribute existence, not signatures). That keeps `isinstance` fast for the common case (Protocol-as-static-type) and opt-in for the rare case (Protocol-as-runtime-gate).

### Lines 7–9: A plain (non-runtime-checkable) Protocol

```python
# --- A plain Protocol: anything with a .close() method is Closable. ---
# NOTE: not @runtime_checkable — isinstance() against this will TypeError.
class Closable(Protocol):
    def close(self) -> None: ...
```

`class Closable(Protocol):` declares a structural type. Any object with a `close(self) -> None` method is a `Closable` — at the type-checker's level. The body has `def close(self) -> None: ...` where `...` (the ellipsis) is the *body placeholder* — it says "the method exists with this signature; the implementation is not part of the contract". You could also write `pass` or a real `raise NotImplementedError`, but `...` is the conventional idiom in typing land.

The comment warns that `isinstance` against `Closable` raises `TypeError` because `Closable` is not `@runtime_checkable`. We demonstrate this in the `__main__` block.

**Why have plain Protocols at all if `isinstance` does not work?**

Because most use of a Protocol is at the *type-checker* level — `def cleanup(store: Closable) -> None:` says "any `Closable` is acceptable", and mypy checks at static-analysis time that callers pass an object with the right `close` method. The runtime `isinstance` is a *different* use case — runtime dispatch, e.g. `if isinstance(x, MyProtocol): ...`. Static use is more common; runtime use is opt-in. Plain Protocols are the default; `@runtime_checkable` is the exception.

### Lines 11–14: A runtime-checkable Protocol

```python
# A runtime-checkable Protocol: isinstance() works (but checks names only).
@runtime_checkable
class Searchable(Protocol):
    def search(self, q: str) -> list: ...
```

`@runtime_checkable` is a class decorator that adds `__instancecheck__` and `__subclasscheck__` to the Protocol. After applying it, `isinstance(obj, Searchable)` is legal — it returns `True` if `obj` has an attribute named `search`. The signature is *not* checked: `obj.search` can be a method, a string, a number — anything that exists as an attribute. This is the dangerous limitation.

**Why does `@runtime_checkable` check only names, not signatures?**

Two reasons. (1) **Cost**: signature comparison at runtime would have to walk `inspect.signature` on both sides and compare them — expensive, and fragile across runtime redefinitions. (2) **Soundness limits**: even if you checked signatures, a malicious or buggy class could lie about its signature. The Python core team chose to make the check shallow — fast, predictable, and explicitly documented as incomplete. PEP 544 says: "runtime_checkable() will check only the presence of the required methods, not their type signatures."

### Lines 16–27: Concrete classes that satisfy both Protocols structurally

```python
# boardly models that satisfy the protocols structurally — no inheritance.
class FileStore:
    """Stores tickets on disk. Has close() and search() but inherits from nothing."""
    def close(self) -> None:
        print("file store closed")
    def search(self, q: str) -> list:
        return [f"file-match-{q}"]

class MemoryStore:
    """Stores tickets in memory. Same shape, different class."""
    def close(self) -> None:
        print("memory store closed")
    def search(self, q: str) -> list:
        return [f"mem-match-{q}"]
```

Neither `FileStore` nor `MemoryStore` inherits from `Closable` or `Searchable` or any common base. They both have `close()` and `search()` methods with matching signatures. mypy therefore treats both as satisfying both Protocols — *structurally*. You can pass either to `run_query(store: Searchable, q: str)` and to `cleanup(store: Closable)`. This is the entire point of PEP 544: no inheritance, no registration, just shape.

This is genuinely different from `ABC` (the `abc` module). With `ABC`, a class must *register* as a virtual subclass (`BaseStore.register(FileStore)`) or inherit — both are explicit actions. With `Protocol`, the relationship is automatic and shape-based.

**Why does this matter for third-party libraries?**

Because you cannot always modify a third-party class to inherit from your base. If you depend on a SQLAlchemy `Session` and want to write a function that takes "anything with an `execute()` method", you cannot make SQLAlchemy's `Session` inherit from your `Executable` base — but you can define `class Executable(Protocol): def execute(self, stmt) -> Result: ...` and pass `Session` instances. The Protocol adapts to existing classes without modification.

### Lines 29–35: Functions typed against the Protocols

```python
# A function typed against the Protocol, not the concrete classes.
def run_query(store: Searchable, q: str) -> list:
    return store.search(q)

def cleanup(store: Closable) -> None:
    store.close()
```

Both functions take a Protocol, not a concrete class. `run_query` accepts any `Searchable` — `FileStore`, `MemoryStore`, or any future class that satisfies the Protocol. `cleanup` accepts any `Closable`. The body calls `.search(q)` or `.close()` knowing the type-checker has verified the methods exist with matching signatures.

**Why not just use `BaseStore` (an ABC) here?**

You could — and for an internal-only codebase with one inheritance hierarchy, `BaseStore` is fine. But the moment you want to accept a third-party store that does not inherit from `BaseStore`, you need either a wrapper (boilerplate) or a Protocol (zero boilerplate). The Protocol is the lower-ceremony choice for plug-in points that might extend to third-party code.

### Lines 37–44: Protocol with attribute members

```python
# --- Protocol with non-method members (attributes). ---
@runtime_checkable
class HasTicketId(Protocol):
    ticket_id: int

class Ticket:
    def __init__(self, ticket_id: int) -> None:
        self.ticket_id = ticket_id
```

A Protocol can have attributes, not just methods. `HasTicketId` declares `ticket_id: int` as an attribute — any object with a `ticket_id` attribute (instance or class level) satisfies the Protocol. `Ticket` sets `self.ticket_id` in `__init__`, so it satisfies `HasTicketId` at the type-checker's level. At runtime, `isinstance(t, HasTicketId)` checks that the attribute exists as a *member* of `t` — both as an instance attribute and as a class attribute (for the case where the class declares `ticket_id: int = 0` at class level).

**Why does `@runtime_checkable` allow attribute checks too?**

Because attribute access is the simplest possible runtime check — `hasattr(obj, 'ticket_id')` is constant-time. Method checks are the same: `hasattr(obj, 'search')` is the entire `isinstance` for `Searchable`. The Protocol machinery unifies methods and attributes — both are "names the object must have". The signature is irrelevant; only the name is checked.

### Lines 46–62: A generic Protocol

```python
# --- Generic Protocol. ---
T = TypeVar("T")

class Repository(Protocol[T]):
    def get(self, id: int) -> T | None: ...
    def put(self, id: int, value: T) -> None: ...

class InMemoryTicketRepo:
    def __init__(self) -> None:
        self._db: dict[int, Ticket] = {}
    def get(self, id: int) -> Ticket | None:
        return self._db.get(id)
    def put(self, id: int, value: Ticket) -> None:
        self._db[id] = value
```

`Repository(Protocol[T])` is a generic Protocol — parameterised over `T`. The methods use `T`: `get` returns `T | None`, `put` takes a `value: T`. At the use site, `Repository[Ticket]` is a "Repository of `Ticket`" — `get` returns `Ticket | None`, `put` takes a `Ticket`. `InMemoryTicketRepo` satisfies `Repository[Ticket]` structurally because its `get` returns `Ticket | None` and `put` takes a `Ticket` — the signatures match when `T = Ticket`.

Generic Protocols are how you type plug-in points that are parameterised over a type — dependency-injection containers, plugin registries, ORM sessions, etc. Anywhere you would have written `class BaseRepository(ABC, Generic[T])`, you can now write `class Repository(Protocol[T])` and skip the inheritance requirement.

**Why is `Repository` a Protocol and not an ABC?**

Because `InMemoryTicketRepo` is the *only* concrete implementation in boardly's tests, but production might swap in a `PostgresTicketRepo` (from a different module or even a different library). Forcing both to inherit from a common `BaseRepository` would couple them; Protocol decouples them. The interface is the contract; the implementations are independent.

### Lines 64–89: The `__main__` block

```python
if __name__ == "__main__":
    fs = FileStore()
    ms = MemoryStore()
    print("file search:", run_query(fs, "alpha"))
    print("mem search:", run_query(ms, "beta"))
    cleanup(fs)
    cleanup(ms)

    # runtime_checkable lets you isinstance against the Protocol.
    print("fs is Searchable:", isinstance(fs, Searchable))

    # Closable is NOT @runtime_checkable — isinstance raises TypeError.
    try:
        isinstance(fs, Closable)
    except TypeError as exc:
        print("isinstance(fs, Closable) raised:", exc)

    t = Ticket(ticket_id=42)
    print("t is HasTicketId:", isinstance(t, HasTicketId))

    # Generic Protocol — InMemoryTicketRepo is structurally a Repository[Ticket].
    repo: Repository[Ticket] = InMemoryTicketRepo()
    repo.put(1, Ticket(ticket_id=1))
    fetched = repo.get(1)
    print("repo get(1):", fetched.ticket_id if fetched else None)
```

We exercise five things. (1) `run_query` accepts both `FileStore` and `MemoryStore` because both satisfy `Searchable`. (2) `cleanup` accepts both because both satisfy `Closable`. (3) `isinstance(fs, Searchable)` is `True` — runtime-checkable Protocols work. (4) `isinstance(fs, Closable)` *raises `TypeError`* — because `Closable` is not `@runtime_checkable`. (5) `isinstance(t, HasTicketId)` is `True` — attribute Protocols work. The generic `Repository[Ticket]` line is the punchline: `InMemoryTicketRepo` is *structurally* a `Repository[Ticket]`, with no inheritance.

The `TypeError` on `isinstance(fs, Closable)` is the lesson in one line: a plain Protocol is *static-only*; `isinstance` against it fails at runtime. If you need runtime checking, you must opt in with `@runtime_checkable` — and accept that the check is shallow.

## Execution Trace

```bash
$ python boardly/protocol_structural.py
file search: ['file-match-alpha']
mem search: ['mem-match-beta']
file store closed
memory store closed
fs is Searchable: True
isinstance(fs, Closable) raised: Instance and class checks can only be used with @runtime_checkable protocols
t is HasTicketId: True
repo get(1): 1
```

Three lines matter. `fs is Searchable: True` — runtime-checkable Protocols work. `isinstance(fs, Closable) raised: ...` — plain Protocols raise `TypeError`. `repo get(1): 1` — generic Protocols work with structural conformance and no inheritance.

## Common Mistakes

### Mistake 1: Assuming `@runtime_checkable` checks signatures

```python
@runtime_checkable
class Greeter(Protocol):
    def greet(self, name: str) -> str: ...

class Fake:
    greet = "not a method"  # ← a string, not a method

isinstance(Fake(), Greeter)  # ← returns True (!)
```

**Symptom:** `isinstance` returns `True` for an object whose `greet` is a string, not a callable. Downstream code calls `obj.greet("ada")` and gets `TypeError: 'str' object is not callable`.
**Why:** `@runtime_checkable` only checks attribute *existence*, not signature or even callability. A string satisfies `hasattr(obj, 'greet')` just as well as a method.
**Fix:** Do not rely on `isinstance` against a runtime-checkable Protocol for correctness. Use it only as a *hint* (e.g., for plugin discovery). For correctness, call the method in a `try/except` or use static type-checking.

### Mistake 2: Forgetting to mark a Protocol `@runtime_checkable` and getting a `TypeError` at runtime

```python
class Closable(Protocol):
    def close(self) -> None: ...

# ... later ...
isinstance(obj, Closable)  # ← TypeError
```

**Symptom:** `TypeError: Instance and class checks can only be used with @runtime_checkable protocols` at the call site.
**Why:** Plain Protocols are static-only. `@runtime_checkable` is the opt-in flag.
**Fix:** Either add `@runtime_checkable` (if you accept the shallow-check limitation) or remove the `isinstance` call (if static checking is enough).

### Mistake 3: Using a Protocol where an ABC is the right answer

```python
class TicketBase(Protocol):  # ← should be ABC
    def id(self) -> int: ...

class BugTicket(TicketBase):  # ← this is wrong; TicketBase is a Protocol
    def id(self) -> int: return 1
```

**Symptom:** `class BugTicket(TicketBase)` actually *works* (subclasses of a Protocol are fine), but it defeats the purpose: you are now back to inheritance, which is what Protocol was meant to avoid. And the static type-checker treats `BugTicket` as inheriting the Protocol's "implicit abstract methods" — which is *not* what Protocol intends.
**Why:** Protocols are for *structural* typing — "shape" — not for inheritance hierarchies. If you want a base class with mandatory method overrides, that is `ABC` (lesson 11 of section `11-abc`), not `Protocol`.
**Fix:** Use `class TicketBase(ABC):` with `@abstractmethod` for inheritance-based contracts. Use `Protocol` only for plug-in points where you want to accept any class with the right shape.

## Engineering Trade-Offs

**Decision:** Use `Protocol` for plug-in points and for typing third-party classes we cannot modify; use `ABC` only when we explicitly want a base class with `@abstractmethod` enforcement.
**Both sides:** `Protocol` is lower-ceremony (no inheritance, no registration), but runtime `isinstance` is shallow. `ABC` is higher-ceremony (inheritance required, `@abstractmethod` enforced), but runtime checks are sound (signatures are inherited).
**Commitment:** boardly uses `Protocol` for store/repository/gateway plug-in points and for typing third-party classes (e.g., `Session` from SQLAlchemy). We use `ABC` for the boardly domain hierarchy where we want to enforce that subclasses override specific methods. The rule of thumb: if you would write `isinstance` to dispatch at runtime, prefer `ABC`; if you just want a *type* that says "has this shape", prefer `Protocol`.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/protocol_structural.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/protocol_structural.py`
2. **Exercise 2 — Add a `PostgresStore` class.** Add a third store class with the same `close()` and `search()` methods. Pass it to `run_query` and `cleanup`. Confirm it works with no changes to the functions. `Verify: python -c "from boardly.protocol_structural import run_query; from boardly.protocol_structural import PostgresStore; print(run_query(PostgresStore(), 'gamma'))"`
3. **Exercise 3 — Prove the shallow check.** Add a class `class BadStore: search = 42` (a string attribute, not a method). Confirm `isinstance(BadStore(), Searchable)` returns `True` (the bug). Then guard downstream code to handle the case. `Verify: python -c "from boardly.protocol_structural import Searchable; class B: search=42
print(isinstance(B(), Searchable))"` (use a script if the inline form breaks)
4. **Exercise 4 — Bound a TypeVar to a Protocol.** Define `class Stringify(Protocol): def __str__(self) -> str: ...`. Then `T = TypeVar("T", bound=Stringify)` and `def to_csv(items: list[T]) -> str: return "\n".join(str(x) for x in items)`. Pass `Ticket` instances (which have `__str__`). `Verify: python -c "from boardly.protocol_structural import to_csv, Ticket; print(to_csv([Ticket(1), Ticket(2)]))"`
5. **Exercise 5 — Compare to ABC.** Reimplement `Closable` as `class Closable(ABC)` with `@abstractmethod close`. Make `FileStore` inherit from it. Compare the type-checker behaviour and the runtime `isinstance` behaviour. Document which approach is right for which use case. `Verify: python -c "from abc import ABC, abstractmethod
class C(ABC):
    @abstractmethod
    def close(self): ...
try:
    C()
except TypeError as e:
    print('cannot instantiate:', e)"`

## Verification

```bash
$ python boardly/protocol_structural.py
file search: ['file-match-alpha']
mem search: ['mem-match-beta']
file store closed
memory store closed
fs is Searchable: True
isinstance(fs, Closable) raised: Instance and class checks can only be used with @runtime_checkable protocols
t is HasTicketId: True
repo get(1): 1
```

If `fs is Searchable: True` and `isinstance(fs, Closable) raised:` both appear, you have the runtime-checkable behaviour correct — and you have witnessed the failure mode of a plain Protocol. If `repo get(1): 1` appears, generic Protocols work.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `list[int]` and `get_type_hints`. Protocols are constructed at class-definition time and stored in `__annotations__` like any class.
- [[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T", bound=Shape)`. The `bound` can be a Protocol — structural bounds, not class-hierarchy bounds.

## What's Next

[[01-typing/06-Callable-and-Callable-Annotations]] — `Callable[[int, str], None]` for typing function parameters and returns. We used `Callable[P, R]` in lesson 04 — now we see the concrete form. Three things to look for in lesson 06:

- `Callable[[Arg1, Arg2], ReturnType]` — the standard form.
- `Callable[..., T]` — "any signature, returns `T`".
- The 3.12 `Callable[int, str]` shorthand and `collections.abc.Callable` vs `typing.Callable`.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.Protocol — CPython reference** — https://docs.python.org/3/library/typing.html#typing.Protocol — accessed 2026-10-23 — the canonical API for `Protocol`, `@runtime_checkable`, and structural conformance.
- **PEP 544 — Protocols: Structural subtyping (static duck typing)** — https://peps.python.org/pep-0544/ — accessed 2026-10-23 — the PEP that introduced `Protocol` and `runtime_checkable` in 3.8. Read the "Runtime Use of Protocols" section for the shallow-check warning.
- **typing.runtime_checkable — CPython reference** — https://docs.python.org/3/library/typing.html#typing.runtime_checkable — accessed 2026-10-23 — the decorator that opts a Protocol into `isinstance` support, with its documented limitations.

## What We Learned

- `class Closable(Protocol): def close(self) -> None: ...` declares a structural type. Any class with a matching `close` method satisfies it — no inheritance.
- `@runtime_checkable` opts a Protocol into `isinstance` support. Plain Protocols raise `TypeError` on `isinstance`.
- `@runtime_checkable` checks only attribute *names*, not signatures or callability. It is a hint, not a guarantee.
- Protocols can have attributes (`ticket_id: int`) and methods; both are checked as `hasattr`.
- Generic Protocols (`class Repository(Protocol[T]):`) work like generic classes — subscript with the concrete type at the use site.
- Protocols are for plug-in points and third-party typing; `ABC` is for inheritance-based contracts with `@abstractmethod` enforcement.
