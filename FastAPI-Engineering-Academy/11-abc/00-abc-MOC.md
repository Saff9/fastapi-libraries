---
title: "abc — Section Map of Content"
aliases:
 - abc MOC
 - 11-abc MOC
 - ABC section
tags:
 - abc
 - moc
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "1.5–2 hours across 3 lessons"
prerequisites:
 - "[[05-collections-abc/01-The-ABC-Hierarchy]]"
---

# abc — Section Map of Content

*The `ABCMeta` + `@abstractmethod` pair that lets a class refuse instantiation until every abstract method is implemented — and the `register` virtual-subclass hook and `__subclasshook__` structural check that lets an ABC lie to `isinstance` for third-party classes that cannot inherit.*

**You're at the very beginning of Section 11.**

Section 05 walked the *built-in* ABC tree (`Iterable`, `Sequence`, `Mapping`) and the `ABCMeta` machinery underneath. This section is the *user-facing* layer — the `abc` module's public API for writing your own ABCs. Where Section 05 was "here are the contracts the stdlib ships", Section 11 is "here is how you write your own". Three lessons: the contract (`abc.ABC` + `@abstractmethod`), the registration mechanisms (`register` + `__subclasshook__`), and the decision (`abc.ABC` vs `typing.Protocol` vs `collections.abc`).

Take your time. Type every example. **This is how you learn.**

#abc #moc

## The lessons

| # | Lesson | One-sentence summary |
|---|--------|----------------------|
| 01 | [[11-abc/01-ABC-and-abstractmethod]] | `abc.ABC` (the 3.4+ shortcut for `metaclass=ABCMeta`) and `@abstractmethod` enforce construction-time `TypeError` until every abstract method is implemented; abstract properties and abstract classmethods follow the "abstractmethod innermost" stacking rule. |
| 02 | [[11-abc/02-register-and-Virtual-Subclasses]] | `ABCMeta.register(OtherClass)` makes a class a *virtual* subclass — `isinstance` lies without inheritance — and `__subclasshook__` is the *structural* hook `collections.abc.Iterable` uses to make any class with `__iter__` conform automatically. |
| 03 | [[11-abc/03-ABC-vs-Protocol-vs-collections-abc]] | The three-way decision: `abc.ABC` (nominal, must inherit, runtime `TypeError`), `typing.Protocol` (structural at static-check time, `@runtime_checkable` opt-in and coarse), `collections.abc.X` (structural at runtime via `__subclasshook__`, pre-defined contracts). |

## Mindmap

```mermaid
mindmap
  root((abc))
    The contract
      abc.ABC
        3.4+ shortcut<br/>metaclass=ABCMeta
        ABCMeta.__new__ scans class body
        collects __abstractmethods__ frozenset
      @abstractmethod
        sets __isabstractmethod__ = True
        must be innermost decorator
      abstract property
        @property outside @abstractmethod
      abstract classmethod
        @classmethod outside @abstractmethod
      construction-time check
        ABCMeta.__call__ reads __abstractmethods__
        TypeError names every missing method
    Virtual registration
      ABCMeta.register(cls)
        virtual subclass, no inheritance
        isinstance lies; __mro__ tells truth
        WeakSet _abc_registry
        usable as @decorator
      __subclasshook__
        structural, automatic
        collections.abc pattern
        guard: if cls is not MyABC: return NotImplemented
        returns True / False / NotImplemented
      get_cache_token()
        invalidates isinstance caches
        increments on every register()
    The decision
      abc.ABC
        nominal, must inherit
        runtime TypeError
        internal contracts you own
      typing.Protocol
        structural at static-check time
        @runtime_checkable opt-in
        checks presence, not signatures
        third-party plug-in contracts
      collections.abc.X
        structural at runtime via __subclasshook__
        pre-defined contracts
        Iterable, Sequence, Mapping, ...
```

## Reading order

Read the lessons in numbered order. The first lesson is the contract — it is also the canonical lesson for the `abc.ABC` + `@abstractmethod` pair. The second lesson extends the contract with virtual registration: `register` for nominal virtual subclasses (you know the conforming classes) and `__subclasshook__` for structural conformance (any class with the right methods). The third lesson is the decision: when each of `abc.ABC`, `typing.Protocol`, and `collections.abc.X` wins, and why the modern trend is towards `Protocol` for new custom contracts while `collections.abc` is not going anywhere for the stdlib contracts.

If you only have time for two lessons, read 01 (the contract) and 03 (the decision). Lesson 02 is the depth on the registration mechanisms; it is essential if you maintain a plugin system, but skippable on first read if you just want the decision matrix.

## Prerequisites

- **[[05-collections-abc/01-The-ABC-Hierarchy]]** — the canonical lesson on what an ABC *is* and the tree `collections.abc` exposes. Section 11 assumes you know `Iterable`, `Sequence`, `Mapping`, and the `ABCMeta` mechanism underneath.
- **[[05-collections-abc/05-Custom-ABCs]]** — the explicit `metaclass=ABCMeta` form, with `register` and `__subclasshook__` first introduced. Lesson 01 of this section is the same machinery written more concisely.
- **[[01-typing/05-Protocol-Structural-Typing]]** — `typing.Protocol` and `@runtime_checkable`. Lesson 03 of this section assumes you have written a `Protocol` before.

If you have not read Section 05, start there. The `11-abc` lessons are the *user-facing* layer on top of the `ABCMeta` machinery Section 05 walks from the inside.

## What you will be able to do by the end of Section 11

- Define a custom ABC with `abc.ABC` + `@abstractmethod` and predict the exact `TypeError` raised when a subclass skips a method.
- Use `@property` + `@abstractmethod` (in that order) and `@classmethod` + `@abstractmethod` to declare abstract properties and abstract classmethods.
- Explain why `register` makes `isinstance` lie but does not change `__mro__`, and why `super()` does not work through a virtual-subclass relationship.
- Implement `__subclasshook__` with the `if cls is not MyABC: return NotImplemented` guard to make `isinstance` checks structural.
- Use `get_cache_token()` to invalidate any `isinstance` cache you maintain across plugin loads.
- Decide between `abc.ABC`, `typing.Protocol`, and `collections.abc.X` for a new contract and defend the choice with the three-axis decision: nominal vs structural, runtime vs static, closed set vs open set.

## What's next

Open [[11-abc/01-ABC-and-abstractmethod]] to begin. The first lesson is the contract — `abc.ABC` + `@abstractmethod` and the construction-time `TypeError`. It is the canonical lesson for the `abc.ABC` + `@abstractmethod` pair, so any later lesson that references "the ABC contract" links here.

After Section 11, the natural next sections are [[12-types/00-types-MOC]] (the `types` module, including `GenericAlias` and `MappingProxyType` — which lean on the metaclass machinery you saw here), [[13-future/00-future-MOC]] (`from __future__ import annotations` and PEP 649 — which interact with the ABC introspection in Lesson 01), and [[14-importlib/00-importlib-MOC]] (`importlib` plugin loading — which builds real plugin systems on top of `abc.ABC` + `register`).

## Sources

- **Python `abc` module documentation** — https://docs.python.org/3/library/abc.html — accessed 2026-10-23 — the canonical reference for `ABC`, `ABCMeta`, `abstractmethod`, `register`, `__subclasshook__`, and `get_cache_token`.
- **PEP 3119 — Introducing Abstract Base Classes** — https://peps.python.org/pep-3119/ — accessed 2026-10-23 — the original ABC PEP; the design rationale for `ABCMeta`, `register`, and `__subclasshook__`.
- **PEP 544 — Protocols: Structural subtyping** — https://peps.python.org/pep-0544/ — accessed 2026-10-23 — the PEP that added `typing.Protocol` and `runtime_checkable`; the design rationale for structural subtyping at the type level, which Lesson 03 contrasts with the `abc` mechanism.

## What we learned in this section

- You opened the MOC. **That is the first step.**
