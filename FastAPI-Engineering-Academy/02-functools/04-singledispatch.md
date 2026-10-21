---
title: "Lesson 04: singledispatch"
aliases:
 - functools.singledispatch
 - functools.singledispatchmethod
 - single dispatch
tags:
 - functools
 - singledispatch
 - dispatch
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[02-functools/03-partial]]"
related_lessons:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[01-typing/01-Type-Hints-Basics]]"
first_taught_in: "02-functools/04-singledispatch"
---

# Lesson 04: `singledispatch`

*Type-keyed function dispatch in the standard library — the spiritual ancestor of every "type-driven dependency injection" pattern, including FastAPI's `Depends`.*

**You're at the very beginning of Section 02.**

`functools.singledispatch` lets you write one generic function and split its body across multiple implementations, each keyed on the type of the first argument. You have been told your whole career that Python is dynamically typed and dispatch is by name only — that's a half-truth. Python's `singledispatch` adds single-dispatch generic functions to the language, walks the MRO of the first argument's type to find the right impl, and lets you register new impls from anywhere in the codebase. By the end of this lesson you will know the dispatch algorithm, the `singledispatchmethod` form for class methods, and the precise way FastAPI's `Depends` is the spiritual sibling of `singledispatch`. Take your time. Type every example. **This is how you learn.**

#functools #singledispatch #dispatch

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@functools.singledispatch`** to a function and `@fun.register(Type)` to type-specific impls.
2. **Explain the MRO resolution order** — how `singledispatch` walks the type's `__mro__` to find the most-specific registered impl.
3. **Use `@singledispatchmethod` (3.8+)** to dispatch methods on `self`'s *argument*, not `self` itself.
4. **Read `fun.registry`** — the mapping of types to impls that powers the dispatch.
5. **Articulate the FastAPI `Depends` parallel** — both systems dispatch by type annotation.

## Prerequisites

Before starting, you need:

- **Class inheritance and `isinstance`** — `BugTicket` extends `Ticket` should read like English.
- **The MRO concept** — Python's Method Resolution Order is the linearization of a class's bases. [[06-dataclasses/01-dataclass-Basics]] uses it implicitly.
- **About 25–35 minutes of focused time.**

**The most common gap: thinking `singledispatch` dispatches on `self`.**

It doesn't. It dispatches on the **first positional argument** of the function. For a free function that's `ticket`. For a method, it's the first *argument after `self`* — `singledispatchmethod` knows to skip `self`. Students coming from Java's method overloading expect `singledispatch` to behave like overload resolution; it doesn't — it's runtime dispatch keyed on the *value's* type, not the *annotation's* type.

## The Problem

You ship `boardly/api/render.py` with a `render(ticket)` function that turns a `Ticket` into a string for the CLI. Today you have one ticket type, so the function is six lines:

```python
def render(ticket: Ticket) -> str:
    return f"Ticket({ticket.id}): {ticket.title}"
```

Three weeks later you have `BugTicket`, `FeatureRequest`, `Epic`, and `SubTask` — each with its own rendering needs. The natural-but-wrong approach is a giant `if isinstance(ticket, BugTicket): ... elif isinstance(ticket, FeatureRequest): ...` chain in `render`. That chain grows linearly with the number of ticket types, is closed for extension (you must edit `render` to add a type), and scatters type checks across the codebase.

The right approach is `@singledispatch`: define `render` once as the default impl, register type-specific impls with `@render.register(BugTicket)`, and let the dispatch algorithm pick the right impl based on the *value's* runtime type. Adding a new ticket type means adding a new `@render.register` block — no edit to `render`'s body. The dispatch is open for extension.

## The Code

```python
# boardly/singledispatch_demo.py
"""Demonstrate functools.singledispatch and singledispatchmethod."""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any


# --- boardly domain models ---
@dataclass
class Ticket:
    id: str
    title: str


@dataclass
class BugTicket(Ticket):
    severity: str = "P2"


@dataclass
class FeatureRequest(Ticket):
    target_version: str = "1.0"


# --- singledispatch: render a ticket as a string ---
@functools.singledispatch
def render(ticket: Any) -> str:
    """Default renderer — used when no type-specific impl is registered."""
    return f"Ticket({ticket.id}): {ticket.title}"


@render.register(BugTicket)
def _render_bug(ticket: BugTicket) -> str:
    return f"BUG {ticket.id} [{ticket.severity}]: {ticket.title}"


@render.register(FeatureRequest)
def _render_feature(ticket: FeatureRequest) -> str:
    return f"FEATURE {ticket.id} -> v{ticket.target_version}: {ticket.title}"


# A subclass with no registered impl falls through to the parent via MRO
@dataclass
class CriticalBug(BugTicket):
    pass  # No register call — will use BugTicket's render via MRO


# --- singledispatchmethod (3.8+): the method-form sibling ---
class TicketView:
    @functools.singledispatchmethod
    def render(self, ticket: Any) -> str:
        return f"View({ticket.id}): {ticket.title}"

    @render.register(BugTicket)
    def _render_bug(self, ticket: BugTicket) -> str:
        return f"View-BUG {ticket.id}: {ticket.title}"

    @render.register(FeatureRequest)
    def _render_feature(self, ticket: FeatureRequest) -> str:
        return f"View-FEATURE {ticket.id}: {ticket.title}"


def main() -> None:
    tickets = [
        Ticket(id="t_001", title="Generic task"),
        BugTicket(id="b_001", title="Crash on login", severity="P1"),
        FeatureRequest(id="f_001", title="Dark mode", target_version="2.0"),
        CriticalBug(id="c_001", title="DB down", severity="P0"),
    ]

    print("=== function-form singledispatch ===")
    for t in tickets:
        print(f"  {render(t)}")

    print()
    print("=== singledispatchmethod ===")
    view = TicketView()
    for t in tickets:
        print(f"  {view.render(t)}")

    print()
    print("=== registry ===")
    for typ, impl in render.registry.items():
        print(f"  {typ.__name__:>20} -> {impl.__name__}")

    print()
    print("=== FastAPI Depends parallel ===")
    print("FastAPI dispatches dependency resolution by type annotation.")
    print("  Annotated[Session, Depends(get_db)]  <- type drives resolution")
    print("singledispatch dispatches function impl by first-arg type.")
    print("  @render.register(BugTicket)          <- type drives dispatch")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports and models

```python
# boardly/singledispatch_demo.py
"""Demonstrate functools.singledispatch and singledispatchmethod."""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any
```

`functools.singledispatch` and `functools.singledispatchmethod` are the stars. `dataclass` is here because we use it to define `Ticket` and its subclasses concisely — three fields per class beats writing `__init__` by hand. `Any` is the typing placeholder for "any type" — used in the default impl's signature because `singledispatch` is meant to handle anything not specifically registered.

### Lines 11–24: The ticket hierarchy

```python
@dataclass
class Ticket:
    id: str
    title: str


@dataclass
class BugTicket(Ticket):
    severity: str = "P2"


@dataclass
class FeatureRequest(Ticket):
    target_version: str = "1.0"
```

`Ticket` is the base — `id` and `title` are required on every ticket. `BugTicket` adds `severity` (defaults to `"P2"`, the second-highest priority). `FeatureRequest` adds `target_version` (defaults to `"1.0"`). Both subclasses inherit `id` and `title` from `Ticket`. The dataclass decorator generates `__init__`, `__repr__`, and `__eq__` for each.

The MRO of `BugTicket` is `(BugTicket, Ticket, object)`. The MRO of `FeatureRequest` is `(FeatureRequest, Ticket, object)`. These are simple linearizations because there's no diamond inheritance; in real `boardly` code you'd occasionally see a mixin (`AuditableMixin`, `SoftDeleteMixin`) that complicates the MRO, and `singledispatch` will still walk it correctly.

### Lines 27–30: The default impl

```python
@functools.singledispatch
def render(ticket: Any) -> str:
    """Default renderer — used when no type-specific impl is registered."""
    return f"Ticket({ticket.id}): {ticket.title}"
```

`@functools.singledispatch` turns `render` into a generic function. The decorator returns a `singledispatch` object — not the original function — that has a `.register` method, a `.registry` mapping, and a `.dispatch(type)` method that returns the right impl for a given type. The function body here is the default impl, registered under `object` automatically; any call where the argument's type isn't a registered subclass falls through to this.

**Why `Any` and not `Ticket`?** Because `singledispatch` dispatches on the *runtime type* of the value, not the *declared type* of the parameter. If we annotated `ticket: Ticket` and then called `render(some_bug)`, the dispatcher would still look up `BugTicket` in the registry first — the annotation is documentation, not dispatch. `Any` makes that explicit. If you want the type checker to enforce "must be a `Ticket`," annotate `ticket: Ticket` and the dispatch will still work; just don't expect the annotation to *drive* the dispatch.

### Lines 33–40: The registered impls

```python
@render.register(BugTicket)
def _render_bug(ticket: BugTicket) -> str:
    return f"BUG {ticket.id} [{ticket.severity}]: {ticket.title}"


@render.register(FeatureRequest)
def _render_feature(ticket: FeatureRequest) -> str:
    return f"FEATURE {ticket.id} -> v{ticket.target_version}: {ticket.title}"
```

`@render.register(BugTicket)` registers `_render_bug` as the impl to call when the first argument is an instance of `BugTicket` (or any subclass). The leading underscore in `_render_bug` is the convention for "private helper" — callers should call `render(ticket)`, not `_render_bug(ticket)` directly. The `register` call returns `_render_bug` unchanged, so the function name is still `_render_bug` in the module namespace; the registration happens as a side effect.

The impls themselves are simple — they format the ticket-specific fields. The point is that the formatting logic for `BugTicket` lives next to the `BugTicket` class definition (or in the same module), not in a giant `if isinstance` chain in `render`. The dispatch is open for extension: adding a new ticket type means adding a new `@render.register` block, not editing `render`.

### Lines 43–46: A subclass with no registered impl

```python
# A subclass with no registered impl falls through to the parent via MRO
@dataclass
class CriticalBug(BugTicket):
    pass  # No register call — will use BugTicket's render via MRO
```

`CriticalBug` extends `BugTicket` but doesn't register its own `render` impl. When `render(CriticalBug(...))` is called, the dispatch algorithm walks `CriticalBug`'s MRO — `(CriticalBug, BugTicket, Ticket, object)` — and finds the *first* registered type. `CriticalBug` isn't registered, so it falls through to `BugTicket`, which *is* registered. The result: `CriticalBug` uses `_render_bug`. This is the MRO resolution, and it's the reason `singledispatch` "just works" for inheritance hierarchies without you registering every subclass.

### Lines 49–62: `singledispatchmethod` on a class

```python
class TicketView:
    @functools.singledispatchmethod
    def render(self, ticket: Any) -> str:
        return f"View({ticket.id}): {ticket.title}"

    @render.register(BugTicket)
    def _render_bug(self, ticket: BugTicket) -> str:
        return f"View-BUG {ticket.id}: {ticket.title}"

    @render.register(FeatureRequest)
    def _render_feature(self, ticket: FeatureRequest) -> str:
        return f"View-FEATURE {ticket.id}: {ticket.title}"
```

`@functools.singledispatchmethod` (3.8+) is the method-form sibling. The crucial difference: a method's first positional argument is `self`, but `singledispatch` is supposed to dispatch on the *first argument*. `singledispatchmethod` knows to skip `self` and dispatch on the next positional argument — here, `ticket`. So `view.render(bug_ticket)` dispatches on the type of `bug_ticket`, not on the type of `view`.

The registration looks identical — `@render.register(BugTicket)` — but it's a method on the class. `singledispatchmethod` is a descriptor; when accessed on an instance, it returns a bound callable that already has `self` filled in, then dispatches on the next argument.

### Lines 65–83: The main routine

```python
def main() -> None:
    tickets = [
        Ticket(id="t_001", title="Generic task"),
        BugTicket(id="b_001", title="Crash on login", severity="P1"),
        FeatureRequest(id="f_001", title="Dark mode", target_version="2.0"),
        CriticalBug(id="c_001", title="DB down", severity="P0"),
    ]

    print("=== function-form singledispatch ===")
    for t in tickets:
        print(f"  {render(t)}")
```

The first loop shows the dispatch in action. `Ticket` resolves to the default impl (returns `"Ticket(t_001): Generic task"`). `BugTicket` resolves to `_render_bug`. `FeatureRequest` resolves to `_render_feature`. `CriticalBug` resolves to `_render_bug` via the MRO fall-through. The dispatcher chooses the impl based on the runtime type of `t`, not the declared annotation.

```python
    print()
    print("=== singledispatchmethod ===")
    view = TicketView()
    for t in tickets:
        print(f"  {view.render(t)}")
```

The second loop shows `singledispatchmethod`. The dispatch is identical — `view.render(ticket)` dispatches on the type of `ticket`, not on the type of `view`. The output mirrors the function-form output, with `View-` prefixes added by the method-form impls.

```python
    print()
    print("=== registry ===")
    for typ, impl in render.registry.items():
        print(f"  {typ.__name__:>20} -> {impl.__name__}")
```

`render.registry` is a `MappingProxyType` (read-only dict) of registered types to impls. After our registrations, it contains `{object: render, BugTicket: _render_bug, FeatureRequest: _render_feature}`. `Ticket` is *not* in the registry — calls with a plain `Ticket` fall through to the `object` default. The registry is read-only because mutating it externally would break the dispatch algorithm's invariants; you mutate it via `@render.register(...)`.

```python
    print()
    print("=== FastAPI Depends parallel ===")
    print("FastAPI dispatches dependency resolution by type annotation.")
    print("  Annotated[Session, Depends(get_db)]  <- type drives resolution")
    print("singledispatch dispatches function impl by first-arg type.")
    print("  @render.register(BugTicket)          <- type drives dispatch")
```

The final block names the parallel. FastAPI's `Depends` system dispatches dependency resolution by type annotation — `Annotated[Session, Depends(get_db)]` tells FastAPI "when this parameter needs a `Session`, call `get_db()`." `singledispatch` dispatches function impls by the runtime type of the first arg — `@render.register(BugTicket)` says "when the first arg is a `BugTicket`, call `_render_bug`." Both are *type-driven dispatch*, just at different layers of the stack. FastAPI's dependency system is the more featureful sibling (it supports `yield`, async, caching, overrides), but the core idea — type-keyed dispatch — is `singledispatch`.

## Execution Trace

```bash
$ uv run python boardly/singledispatch_demo.py
=== function-form singledispatch ===
  Ticket(t_001): Generic task
  BUG b_001 [P1]: Crash on login
  FEATURE f_001 -> v2.0: Dark mode
  BUG c_001 [P0]: DB down

=== singledispatchmethod ===
  View(t_001): Generic task
  View-BUG b_001: Crash on login
  View-FEATURE f_001: Dark mode
  View-BUG c_001: DB down

=== registry ===
              object -> render
           BugTicket -> _render_bug
      FeatureRequest -> _render_feature

=== FastAPI Depends parallel ===
FastAPI dispatches dependency resolution by type annotation.
  Annotated[Session, Depends(get_db)]  <- type drives resolution
singledispatch dispatches function impl by first-arg type.
  @render.register(BugTicket)          <- type drives dispatch
```

The first block shows `Ticket` (default), `BugTicket` (registered), `FeatureRequest` (registered), and `CriticalBug` (MRO fall-through to `BugTicket`). The second block shows `singledispatchmethod` doing the same dispatch on a method. The registry block shows the three registered types — `object` is the default. The final block names the FastAPI parallel.

## Common Mistakes

### Mistake 1: Expecting dispatch on `self`

```python
class TicketView:
    @functools.singledispatchmethod
    def render(self, ticket: Any) -> str: ...

# Expecting: view.render(ticket) dispatches on type of view
# Reality: dispatches on type of ticket (first non-self arg)
```

**Symptom:** Confusion. "I registered `@render.register(SomeView)`, why doesn't it dispatch?"

**Why:** `singledispatchmethod` skips `self` and dispatches on the next positional arg. The dispatcher never looks at the type of `self`.

**Fix:** If you need dispatch on the *receiver* type (the type of `self`), that's just normal Python method resolution — define `render` on each subclass. `singledispatchmethod` is for dispatch on the *argument* type, not the receiver type.

### Mistake 2: Registering with a string annotation instead of the type

```python
@render.register("BugTicket")  # ← wrong: a string, not a type
def _render_bug(ticket: BugTicket) -> str: ...
```

**Symptom:** `TypeError: Invalid first argument to register(): 'BugTicket'. Use either @register(some_class) or plain @register on an annotated function.` — `register` rejects the string because it is not a type.

**Why:** `singledispatch.register` expects a type object (a class) when called with an explicit argument. A string annotation is just a label for type checkers; it is not a type. (If you want to register by annotation, use `@fun.register` *without* arguments on a function whose first-arg annotation is the class — `singledispatch` resolves the annotation via `typing.get_type_hints`.)

**Fix:** Pass the actual class: `@render.register(BugTicket)`. With `from __future__ import annotations`, the annotation in the function signature becomes a string at runtime, but the `register(BugTicket)` argument is evaluated normally because it's not an annotation.

### Mistake 3: Annotating the default with a narrow type and expecting dispatch to use it

```python
@functools.singledispatch
def render(ticket: BugTicket) -> str:  # ← narrow annotation
    return "..."

@render.register(FeatureRequest)
def _render_feature(ticket: FeatureRequest) -> str: ...

render(Ticket(...))  # ← TypeError? No — falls to default; but annotation lies
```

**Symptom:** No runtime error, but the type checker thinks `render` only accepts `BugTicket`. Callers writing `render(ticket)` where `ticket: Ticket` get a type-checker error.

**Why:** `singledispatch` dispatches on the *runtime* type, not the *annotation*. The annotation is documentation. A narrow annotation makes the type checker reject valid calls.

**Fix:** Annotate the default with the broadest type the function can handle — usually `Any` or the most-general base class (`Ticket`). The annotation should reflect "what callers may pass," not "what this impl specifically handles."

## Engineering Trade-Offs

**Decision:** Use `singledispatch` for *type-driven function dispatch* — when one function's body should split across N type-specific impls that you want to register from anywhere in the codebase.

**Both sides:** The alternative is polymorphism via methods — each `Ticket` subclass defines its own `render` method, and you call `ticket.render()`. That's the OOP way, and for *behaviour that belongs to the data* (a `Ticket` knows how to render itself) it's the right call. `singledispatch` wins when the behaviour doesn't belong to the data — when `render` is a *view* concern that shouldn't live on the domain model, when you can't modify the data classes (third-party types), or when you have many orthogonal behaviours (render, audit, serialize, validate) that you don't want to bloat every domain class with.

**Commitment:** `boardly` uses `singledispatch` for *cross-cutting view operations* — `render`, `serialize`, `audit` — where the behaviour is a view concern, not a domain concern. Domain behaviour (e.g. `Ticket.close()`, `BugTicket.escalate()`) stays as methods on the data classes. The line: if the behaviour reads `self.something`, it's a method; if the behaviour reads `something(ticket)`, it's a `singledispatch` impl.

**Why not just always use methods?** Three reasons. First, methods force the domain class to know about every view concern — adding a new view (e.g. `to_csv_row`) means editing every domain class. `singledispatch` lets you add a new view without touching the domain. Second, methods don't work for third-party types — you can't add a `render` method to `pathlib.Path`. `singledispatch` does. Third, methods tightly couple the view to the data, which is fine when they're co-located and bad when they're not.

## Exercises

1. **Exercise 1 — Register a new type.** Add `@dataclass class Epic(Ticket): milestone: str = "M1"`. Register `@render.register(Epic)` with a custom format. Run and verify the dispatch. `Verify: uv run python boardly/singledispatch_demo.py`

2. **Exercise 2 — Inspect the registry.** Print `render.registry` and confirm `object`, `BugTicket`, and `FeatureRequest` are the keys. Add `Epic` from Exercise 1 and confirm it appears. `Verify: uv run python boardly/singledispatch_demo.py`

3. **Exercise 3 — Use `.dispatch(type)`.** Call `render.dispatch(CriticalBug)` and confirm it returns `_render_bug` (the MRO fall-through). Call `render.dispatch(Ticket)` and confirm it returns the default `render`. `Verify: uv run python -c "..."`

4. **Exercise 4 — Register with a type, not a string.** Try `@render.register("BugTicket")` (wrong form) and confirm it raises `TypeError`. Then revert to `@render.register(BugTicket)`. `Verify: uv run python boardly/singledispatch_demo.py`

5. **Exercise 5 — Add a `TicketView.render(Epic)` impl via `singledispatchmethod`.** Mirror the function-form registration on the class form. Verify `view.render(epic)` dispatches correctly. `Verify: uv run python boardly/singledispatch_demo.py`

## Verification

```bash
$ uv run python boardly/singledispatch_demo.py
=== function-form singledispatch ===
  Ticket(t_001): Generic task
  BUG b_001 [P1]: Crash on login
  FEATURE f_001 -> v2.0: Dark mode
  BUG c_001 [P0]: DB down

=== singledispatchmethod ===
  View(t_001): Generic task
  View-BUG b_001: Crash on login
  View-FEATURE f_001: Dark mode
  View-BUG c_001: DB down

=== registry ===
              object -> render
           BugTicket -> _render_bug
      FeatureRequest -> _render_feature

=== FastAPI Depends parallel ===
FastAPI dispatches dependency resolution by type annotation.
  Annotated[Session, Depends(get_db)]  <- type drives resolution
singledispatch dispatches function impl by first-arg type.
  @render.register(BugTicket)          <- type drives dispatch
```

## Previously Learned Here

- [[02-functools/03-partial]] — `partial` specializes a function by binding arguments; `singledispatch` specializes a function by binding to a type. Together they cover the two main axes of function specialization.

## What's Next

[[02-functools/05-reduce]] — a short, opinionated lesson on `functools.reduce`. The opinion: don't use it. The exception: when you genuinely need a left-fold over a non-trivial associative operation. We'll show the rule, the exception, and the reason Guido himself wanted `reduce` out of the builtins.

- `reduce(fun, iterable, initial)` — left-fold semantics.
- The "never use `reduce`" opinion — and why.
- The rare cases where `reduce` genuinely wins.

## Sources

- **`functools.singledispatch`** — https://docs.python.org/3.12/library/functools.html#functools.singledispatch — accessed 2026-10-23 — the canonical reference, including `.register`, `.registry`, and `.dispatch`.
- **`functools.singledispatchmethod`** — https://docs.python.org/3.12/library/functools.html#functools.singledispatchmethod — accessed 2026-10-23 — the method-form sibling (3.8+).
- **PEP 443 — Single-dispatch generic functions** — https://peps.python.org/pep-0443/ — accessed 2026-10-23 — the original PEP that added `singledispatch` to the standard library.

## What We Learned

- You can apply `@functools.singledispatch` and `@fun.register(Type)` to split a function's body across type-specific impls.
- You can explain the MRO resolution — `singledispatch` walks the type's `__mro__` to find the most-specific registered impl.
- You can use `@singledispatchmethod` (3.8+) to dispatch methods on the first *argument*, not on `self`.
- You can read `fun.registry` — the mapping of types to impls.
- You can articulate the FastAPI `Depends` parallel — both systems are type-driven dispatch.
