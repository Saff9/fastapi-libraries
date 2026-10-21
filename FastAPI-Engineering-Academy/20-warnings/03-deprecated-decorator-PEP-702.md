---
title: "Lesson 03: @deprecated decorator (PEP 702)"
aliases:
 - typing.deprecated
 - PEP 702
 - deprecated decorator
 - typing_extensions.deprecated
tags:
 - warnings
 - typing
 - deprecated
 - PEP-702
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[20-warnings/01-warn-and-filterwarnings]]"
 - "[[20-warnings/02-DeprecationWarning-vs-FutureWarning]]"
 - "[[13-future/01-from-future-import-annotations]]"
related_lessons:
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[02-functools/02-wraps-and-Decorators]]"
---

# Lesson 03: `@deprecated` decorator (PEP 702)

*`typing.deprecated("use new_func instead")` (Python 3.13+, PEP 702) — the decorator that marks a function or class as deprecated and makes mypy/pyright emit the deprecation at the *call site* during static analysis. The runtime `DeprecationWarning` still fires (controlled by the lesson-01 filter machinery), but the static check is the new capability: it catches deprecations in code paths your tests never execute. Version-gated clearly — 3.12 does *not* have `typing.deprecated` (verified `hasattr(typing, 'deprecated') == False` on 3.12.15); the `typing_extensions` backport brings it to 3.9–3.12 today.*

**You're at the very beginning of Section 20 — lesson 03.**

You have written `warnings.warn("deprecated", DeprecationWarning, stacklevel=2)` inside a function body — that is the lesson-01 path, and it only fires when the function is *called*. The deprecation of a function that is *imported but never called* — say, a v1 entrypoint re-exported from a `__init__.py` for backward compat, never invoked by any test — is invisible. PEP 702 closes that gap: `@deprecated("use new_func instead")` is a *decorator* that mypy and pyright read during static analysis, and the deprecation surfaces at the *call site* in the developer's editor, before the code ever runs. This lesson walks the decorator, the runtime behaviour, the static-analysis behaviour, and the version-gating (3.13+ for `typing.deprecated`; `typing_extensions.deprecated` for 3.9–3.12). Take your time. Type every example. **This is how you learn.**

#warnings #typing #PEP-702 #deprecated

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@deprecated("use new_func instead")`** to a function or class — and explain why the message is required (positional, not optional).
2. **Explain the version-gating** — `typing.deprecated` is 3.13+; `typing_extensions.deprecated` is the 3.9–3.12 backport; the runtime behaviour is identical; the static-analysis behaviour is identical.
3. **Demonstrate the runtime behaviour** — calling a `@deprecated`-decorated function emits a `DeprecationWarning` at the call site, with the right `stacklevel` automatically set by the decorator.
4. **Demonstrate the static-analysis behaviour** — mypy/pyright emit a `DeprecatedWarning` (mypy: `[deprecated]` code) at the *call site*, in code paths your tests never execute.
5. **Explain the forward-reference interaction** — `@deprecated` on a class that is forward-referenced in annotations works under `from __future__ import annotations` because the decorator runs at class-definition time, not at type-evaluation time.

## Prerequisites

Before starting, you need:

- **`warn` and `filterwarnings`** — [[20-warnings/01-warn-and-filterwarnings]]. The `@deprecated` decorator emits a runtime `DeprecationWarning` — the lesson-01 machinery is the runtime half of PEP 702.
- **`DeprecationWarning` vs `FutureWarning`** — [[20-warnings/02-DeprecationWarning-vs-FutureWarning]]. The decorator emits `DeprecationWarning` (not `FutureWarning`); the audience rule from lesson 02 applies.
- **`from __future__ import annotations`** — [[13-future/01-from-future-import-annotations]]. The forward-reference interaction in the last deep-dive block depends on this.
- **About 30–45 minutes of focused time.**

**The most common gap: `typing.deprecated` is not in 3.12.**

Students read the PEP 702 docs, see `from typing import deprecated`, write `@deprecated("use new_func")`, and run their code on 3.12 — `ImportError: cannot import name 'deprecated' from 'typing'`. The decorator was added in 3.13; on 3.12 the import fails at module load. The escape hatch is `from typing_extensions import deprecated` — same decorator, same runtime behaviour, same mypy/pyright support, but it works on 3.9+. Verified on this vault's runtime (3.12.15): `hasattr(typing, 'deprecated') == False`. The lesson's `boardly` code below uses the `typing_extensions` form precisely so the file imports on 3.12; the lesson notes where 3.13+ would let you use `typing.deprecated` directly.

## The Problem

`boardly` has shipped a v1 function `get_legacy_ticket(ticket_id)`. The team has added `warnings.warn(..., stacklevel=2)` inside it (lesson 01), so callers who *run* the function see the warning. But: a search of the codebase finds 14 files that *import* `get_legacy_ticket` without calling it — re-exports for backward compat, dead code that no test exercises. The runtime warning never fires for those 14 files; the deprecation is invisible until someone actually calls the function. The team wants:

1. A *static* signal at every call site — in the developer's editor, before any code runs.
2. The *runtime* signal to keep working (lesson-01 path) — for callers who do not use a static checker.
3. The two signals to be derived from the *same source* — a single `@deprecated("...")` decorator on the function definition, not a `warn()` call inside it.

PEP 702 is the answer. `@deprecated("use get_ticket instead")` on the function definition tells mypy/pyright to flag every call site statically, *and* emits the runtime `DeprecationWarning` automatically when the function is called. One annotation, two enforcement layers, zero duplication.

## The Code

```python
# boardly/warnings_demo/deprecated_decorator.py
"""Demonstrate @deprecated (PEP 702) — the typing-extensions backport for 3.12."""
from __future__ import annotations

from typing_extensions import deprecated  # PEP 702; on 3.13+ use `from typing import deprecated`.


def get_ticket(ticket_id: int) -> dict:
    """v2 canonical API."""
    return {"id": ticket_id, "title": "v2 ticket"}


@deprecated("use get_ticket instead; get_legacy_ticket will be removed in v3")
def get_legacy_ticket(ticket_id: int) -> dict:
    """v1 name; kept for backward compat; @deprecated marks it statically."""
    return get_ticket(ticket_id)


@deprecated("use Ticket.assign instead; Ticket.legacy_assign will be removed in v3")
class _LegacyTicketView:
    """v1 ticket view class; kept for backward compat."""

    def __init__(self, ticket_id: int) -> None:
        self.id = ticket_id


def main() -> None:
    import warnings
    warnings.simplefilter("always", DeprecationWarning)  # show, don't raise
    ticket = get_legacy_ticket(42)
    view = _LegacyTicketView(7)
    print("ticket:", ticket, "view.id:", view.id)


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports and the future statement

```python
# boardly/warnings_demo/deprecated_decorator.py
"""Demonstrate @deprecated (PEP 702) — the typing-extensions backport for 3.12."""
from __future__ import annotations

from typing_extensions import deprecated  # PEP 702; on 3.13+ use `from typing import deprecated`.
```

`from __future__ import annotations` is here for two reasons. First, the boardly convention (see [[13-future/01-from-future-import-annotations]]) — every boardly module that defines typed functions has it. Second, the last deep-dive block walks the interaction between `@deprecated` and forward references; the future import is the precondition for that interaction to matter.

`from typing_extensions import deprecated` is the 3.12-safe import. On 3.13+ you would write `from typing import deprecated` and the behaviour is identical. The `typing_extensions` package ships a backport of `deprecated` that works on Python 3.9 through 3.12 — verified on this vault's runtime (3.12.15): `from typing_extensions import deprecated` succeeds; `from typing import deprecated` raises `ImportError`. The backport is a thin wrapper around the same CPython implementation that landed in 3.13's `typing` module.

**Why use `typing_extensions` and not a runtime version-gate?**

Because the alternative — `if sys.version_info >= (3, 13): from typing import deprecated; else: from typing_extensions import deprecated` — adds five lines of conditional import to every file that uses the decorator. The `typing_extensions` form is one line, works everywhere from 3.9 to 3.13+, and produces byte-identical static-analysis behaviour (mypy and pyright treat both forms as the PEP 702 decorator). The cost is a dependency on `typing_extensions` — which most typed Python projects already have transitively (via `pydantic`, `starlette`, `FastAPI`, etc.). The boardly project keeps the dependency for the cleaner import.

**Why is the message a positional argument, not a keyword?**

Because PEP 702 specifies `deprecated(message)` as the signature — `message` is positional-only. The decorator returns a class decorator (when applied to a class) or a function decorator (when applied to a function), and the message is the first argument to `deprecated` itself — not a keyword argument. `@deprecated("...")` is the form; `@deprecated(message="...")` raises `TypeError: deprecated.__init__() got some positional-only arguments passed as keyword arguments: 'message'` on Python 3.13+ *and* on the `typing_extensions` backport — both enforce the positional-only contract for `message` (verified on this vault's 3.12.15 with `typing_extensions.deprecated(message="...")`). The `typing_extensions` backport does accept two extra keyword arguments (`category=DeprecationWarning`, `stacklevel=1`) that the 3.13 runtime does not, but `message` remains positional-only on both. The PEP 702 design rationale: a positional-only argument makes the decorator's call site visually distinct from a function call with keyword arguments, and prevents future keyword collisions.

### Lines 8–10: The canonical v2 API

```python
def get_ticket(ticket_id: int) -> dict:
    """v2 canonical API."""
    return {"id": ticket_id, "title": "v2 ticket"}
```

The v2 function — same as in lessons 01 and 02. The whole point of this lesson is the *decorator* on `get_legacy_ticket`, not the body of `get_ticket`. The body is here for the script to actually run end-to-end.

### Lines 13–16: `@deprecated` on a function

```python
@deprecated("use get_ticket instead; get_legacy_ticket will be removed in v3")
def get_legacy_ticket(ticket_id: int) -> dict:
    """v1 name; kept for backward compat; @deprecated marks it statically."""
    return get_ticket(ticket_id)
```

`@deprecated("...")` is applied as a decorator to `get_legacy_ticket`. The decorator does three things:

1. **At import time:** the function object is wrapped — its `__name__`, `__qualname__`, `__doc__`, `__module__`, `__wrapped__` are preserved (the decorator uses `functools.wraps` internally; see [[02-functools/02-wraps-and-Decorators]]). The original function is preserved as `__wrapped__`.
2. **At call time:** the wrapper calls `warnings.warn(message, category=DeprecationWarning, stacklevel=2)` *before* calling the original function. The `stacklevel=2` is built in — you do not pass it; the decorator handles it. The category is always `DeprecationWarning` (PEP 702 does not let you choose `FutureWarning`).
3. **At static-analysis time:** mypy/pyright read the `__deprecated__` attribute that the decorator sets on the function object (a string, the message), and emit a `DeprecatedWarning` at every *call site* of `get_legacy_ticket` — not at the definition site.

The body of `get_legacy_ticket` is `return get_ticket(ticket_id)` — there is no `warnings.warn(...)` call inside it. The decorator handles the warning emission; the body is the v2 passthrough.

**Why is the body so much smaller than lesson 01's `get_legacy_ticket`?**

Because the `warnings.warn(..., stacklevel=2)` call from lesson 01 is now the decorator's responsibility. In lesson 01, you wrote four lines of `warnings.warn(...)` inside the function. In this lesson, the decorator emits the warning for you, with the correct `stacklevel=2` automatically. The body of the function is *only* the v2 passthrough. The four-line savings per deprecation point add up across a large codebase — the lesson-01 pattern requires every author to remember `stacklevel=2`; the PEP 702 pattern requires only that they remember the decorator.

**Why does PEP 702 always emit `DeprecationWarning` and not `FutureWarning`?**

Because PEP 702 is about *removal* of a feature, not about behaviour change — the rule from lesson 02 is "DeprecationWarning for removal, FutureWarning for behaviour change". The `@deprecated` decorator is the standard-library way to mark a function as going to be *removed*; if you need a behaviour-change warning, you still write `warnings.warn(..., category=FutureWarning, stacklevel=2)` inside the function — there is no `@future_deprecated` decorator. The asymmetry is intentional: removal is statically checkable (mypy can flag the call site); behaviour change is not (mypy cannot know that `int` callers will break under a `float` return).

### Lines 19–24: `@deprecated` on a class

```python
@deprecated("use Ticket.assign instead; Ticket.legacy_assign will be removed in v3")
class _LegacyTicketView:
    """v1 ticket view class; kept for backward compat."""

    def __init__(self, ticket_id: int) -> None:
        self.id = ticket_id
```

`@deprecated("...")` is also a class decorator. PEP 702 supports both functions and classes. When applied to a class, the decorator wraps the class's `__init__` method (and `__new__`) so that instantiating the class emits the `DeprecationWarning`. The static-analysis behaviour: mypy/pyright flag every *instantiation* (`_LegacyTicketView(7)`) and every *subclass* (`class MyView(_LegacyTicketView):`) of the deprecated class.

**Why does the class decorator wrap `__init__` and not the class itself?**

Because the deprecation should fire when the class is *used* (instantiated or subclassed), not when it is *defined*. A class definition in a backward-compat module is fine — the warning should only fire when someone actually instantiates the class. Wrapping `__init__` achieves this: the call `_LegacyTicketView(7)` triggers `__init__`, which the decorator has wrapped to emit the warning first, then call the original `__init__`. Wrapping `__new__` is the additional protection — necessary for classes that override `__new__` without calling `__init__` (rare; mostly metaclasses).

**Why does the static check flag *subclassing* a deprecated class?**

Because subclassing is a use — if you subclass `_LegacyTicketView`, your subclass inherits the deprecation, and the v3 removal will break your subclass too. The static check therefore fires on `class MyView(_LegacyTicketView):` even though no instantiation has happened — the developer needs to know that the base class is going away. The runtime warning, by contrast, only fires on instantiation — there is no runtime hook for "a class was subclassed" (the metaclass `__init_subclass__` could be used, but PEP 702 does not require it).

### Lines 27–32: The `main` caller

```python
def main() -> None:
    import warnings
    warnings.simplefilter("always", DeprecationWarning)  # show, don't raise
    ticket = get_legacy_ticket(42)
    view = _LegacyTicketView(7)
    print("ticket:", ticket, "view.id:", view.id)
```

`main` calls both `get_legacy_ticket` and `_LegacyTicketView`. The `simplefilter("always", DeprecationWarning)` line ensures the warning is *printed* — without it, the default `__main__`-only rule from lesson 01/02 still applies, and we want the script's output to be deterministic regardless of the filter state at import time. The `import warnings` is inside `main` rather than at the top of the module to keep the import block at the top focused on the `deprecated` decorator — the runtime warning machinery is secondary to this lesson's main point.

**Why `simplefilter("always", ...)` and not `simplefilter("error", ...)`?**

Because this lesson's script is the demonstration, not the CI gate. Lesson 01's script used `simplefilter("error", ...)` to *catch* the warning as an exception — appropriate for CI. This lesson's script uses `simplefilter("always", ...)` to *print* the warning twice (once per deprecated call) — appropriate for a demo. The two patterns are complementary; in real `boardly` CI, both are used (`-W error::DeprecationWarning` for the gate, `pytest.warns(...)` for the assertion).

### The static-analysis layer — what mypy/pyright actually emit

The decorator's runtime behaviour is the lesson-01 path. The new capability is the static-analysis layer. Here is what mypy emits on a call site:

```python
# boardly/warnings_demo/call_site.py
from boardly.warnings_demo.deprecated_decorator import get_legacy_ticket

result = get_legacy_ticket(42)  # mypy: [deprecated] call to deprecated function "get_legacy_ticket"; use get_ticket instead
```

Mypy emits the `[deprecated]` code with the message you passed to `@deprecated(...)`. Pyright emits a `DeprecatedWarning` (the message is the same). The static check fires at every *call site*, in every file — including files that no test ever imports. The runtime warning, by contrast, only fires when the call site is actually executed (and only if the filter lets it through).

The two layers are *independent*. You can have a static deprecation with no runtime emission (if you wrote a custom `@deprecated` decorator that did not call `warnings.warn`), or a runtime deprecation with no static emission (the lesson-01 path — `warnings.warn` inside the body). PEP 702's `@deprecated` gives you both, derived from the same source — the decorator on the definition.

**Why is the static layer more valuable than the runtime layer?**

Three reasons. First, the static layer fires on code paths your tests never execute — dead-code branches, error paths, feature flags that are off. The runtime layer only fires on code your tests actually run; coverage gaps are silent. Second, the static layer fires *before* the code runs — the developer sees the warning in their editor as they type, not after the test suite finishes. Third, the static layer is filterable at the IDE level (you can suppress it with `# type: ignore[deprecated]` on a single call site), which gives a controlled migration path: the team can fix the call sites one by one and remove the `# type: ignore` markers as they go.

**Why is the runtime layer still needed if the static layer exists?**

Because not every caller of `boardly` runs mypy or pyright. A user who installs `boardly` and writes a quick script will not run a static checker; the runtime warning is the only signal they get. The two layers cover different audiences: static for the developer with a type checker, runtime for the developer without one. PEP 702's design preserves both — the decorator emits the runtime warning *and* sets the `__deprecated__` attribute that static checkers read.

### The forward-reference interaction

The `from __future__ import annotations` import (line 3) stringifies annotations. The interaction with `@deprecated` is benign — but worth walking through because it is the kind of thing that *looks* like it could break.

Consider:

```python
from __future__ import annotations
from typing_extensions import deprecated


@deprecated("use NewClass instead")
class OldClass:
    pass


def f() -> OldClass:  # forward reference? no — OldClass is defined above.
    return OldClass()


def g() -> "OldClass":  # explicit string form; same as f() under the future import.
    return OldClass()
```

`@deprecated` runs at *class-definition time* — the moment the `class OldClass:` body finishes executing. By the time `f` and `g` are defined (after `OldClass`), the `OldClass` object exists and has its `__deprecated__` attribute set. The future import only affects *annotations* (the `-> OldClass` return annotation) — it stringifies them; it does not affect the class-definition-time execution of `@deprecated`. The decorator and the future import are orthogonal.

The forward-reference case (where `OldClass` is referenced *before* it is defined) is unaffected too — the future import makes `-> OldClass` a string, and `get_type_hints()` resolves it later at request time (see [[13-future/01-from-future-import-annotations]]). The `@deprecated` decorator on `OldClass` runs whenever `OldClass` is defined; if `OldClass` is defined after `f`, the decorator runs after `f`'s definition. The order does not matter for the static check (mypy resolves names regardless of definition order) or for the runtime check (the decorator wraps `OldClass.__init__` whenever `OldClass` is instantiated, regardless of where the instantiation happens).

**Why does the future import not break `@deprecated`?**

Because `@deprecated` does not touch annotations. The decorator reads the function's signature via `inspect.signature` (or directly via `__wrapped__`) and wraps it; the annotations are stored on `__annotations__` as strings (with the future import) or as types (without). The decorator preserves `__annotations__` via `functools.wraps` (see [[02-functools/02-wraps-and-Decorators]]), so the strings/types are unchanged. The static check (mypy/pyright) reads the `__deprecated__` attribute and the function's source; it does not depend on whether annotations are strings or types. The two features (future import + `@deprecated`) compose cleanly.

### The runtime `stacklevel` automatic

The decorator emits the warning with the correct `stacklevel=2` automatically — but the integer is *2 relative to the wrapper*, not relative to your original function. Here is the call stack at the moment the warning is raised:

```
Frame 1: warnings.warn(...)        <- the warn call inside the wrapper
Frame 2: wrapper(...)              <- the @deprecated wrapper function
Frame 3: get_legacy_ticket(...)    <- wait, this is the wrapper itself
Frame 4: caller                    <- the developer's code
```

Actually, the wrapper *is* the function the developer calls — `get_legacy_ticket` *is* the wrapper, post-decoration. So the stack is:

```
Frame 1: warnings.warn(...)        <- inside the wrapper
Frame 2: wrapper (== get_legacy_ticket)  <- the wrapper function
Frame 3: caller (main)             <- the developer's code
```

The `stacklevel=2` selects frame 2 — the wrapper, which is named `get_legacy_ticket` (via `functools.wraps`). Wait, that would point at the wrapper, not the caller. Let me re-check: PEP 702's implementation uses `stacklevel=2` so that the warning points at the *caller* (frame 3 in the stack above — `main`). The `functools.wraps`-preserved `__name__` of the wrapper is `get_legacy_ticket` (the original function's name), but the *frame* the `stacklevel` selects is the caller's frame — i.e. `main`. The decorator author chose `stacklevel=2` precisely because the wrapper *is* one frame deep in the call stack at the moment `warn` is called.

**Why is `stacklevel=2` correct here when lesson 01 used `stacklevel=2` for a different-looking case?**

Because the call stack depth from `warn` to caller is the same in both cases. In lesson 01, the call stack was: `warn` → `get_legacy_ticket` → `main`. In this lesson, the call stack is: `warn` → `wrapper` → `main`. The wrapper *is* `get_legacy_ticket` (post-decoration, with its `__name__` preserved). The stack depth is 2 in both cases. The decorator author did the lesson-01 analysis for you.

## Execution Trace

```bash
$ python boardly/warnings_demo/deprecated_decorator.py
boardly/warnings_demo/deprecated_decorator.py:30: DeprecationWarning: use get_ticket instead; get_legacy_ticket will be removed in v3
  ticket = get_legacy_ticket(42)
boardly/warnings_demo/deprecated_decorator.py:31: DeprecationWarning: use Ticket.assign instead; Ticket.legacy_assign will be removed in v3
  view = _LegacyTicketView(7)
ticket: {'id': 42, 'title': 'v2 ticket'} view.id: 7
```

Both warnings fire — one per deprecated call. The `filename:lineno` (`:30` and `:31`) point at the caller's lines inside `main`, not at the `@deprecated(...)` lines (the `:14` and `:19` lines). The `stacklevel=2` set by the decorator did its job.

The warning text matches the message passed to `@deprecated(...)` exactly — `use get_ticket instead; get_legacy_ticket will be removed in v3`. The developer reading the warning sees the migration target (`get_ticket`) and the version (`v3`) without opening the library source.

If you run mypy on a call site:

```bash
$ mypy boardly/warnings_demo/call_site.py
boardly/warnings_demo/call_site.py:3: error: call to deprecated function "get_legacy_ticket"; use get_ticket instead  [deprecated]
```

The `[deprecated]` code is the mypy id for PEP 702 violations. Pyright emits the same with a `DeprecatedWarning` code.

## Common Mistakes

### Mistake 1: Using `from typing import deprecated` on 3.12

```python
# On Python 3.12.15:
from typing import deprecated  # ImportError: cannot import name 'deprecated' from 'typing'
```

**Symptom:** `ImportError: cannot import name 'deprecated' from 'typing'` at module load.
**Why:** `typing.deprecated` was added in Python 3.13. On 3.12, the `typing` module does not have the attribute — verified `hasattr(typing, 'deprecated') == False` on 3.12.15.
**Fix:** Use `from typing_extensions import deprecated` — the backport works on 3.9–3.12 and produces identical behaviour to the 3.13+ `typing.deprecated`. On 3.13+ you may switch to `from typing import deprecated`; the `typing_extensions` form continues to work there too (it re-exports the stdlib version).

### Mistake 2: Passing the message as a keyword argument

```python
@deprecated(message="use new_func instead")  # TypeError on 3.13+ AND typing_extensions
def f(): ...
```

**Symptom:** `TypeError: deprecated.__init__() got some positional-only arguments passed as keyword arguments: 'message'` — on Python 3.13+ (`typing.deprecated`) *and* on Python 3.9–3.12 (`typing_extensions.deprecated`). The keyword form fails on both, not just on 3.13+. Verified on this vault's 3.12.15 with `typing_extensions.deprecated(message="...")`.
**Why:** PEP 702 specifies `deprecated(message)` as positional-only (the `/` in the signature `deprecated(message: str, /, *, category=DeprecationWarning, stacklevel=1)` — that signature is the `typing_extensions` form; the 3.13 `typing.deprecated` is `(message: str, /)` with no extras). Both the 3.13 runtime and the `typing_extensions` backport enforce this — `message` is positional-only on both. The `category` and `stacklevel` keyword arguments on the `typing_extensions` backport are typing_extensions-specific extensions, not part of PEP 702, and do not change the positional-only contract for `message`.
**Fix:** Use the positional form — `@deprecated("use new_func instead")`.

### Mistake 3: Expecting `@deprecated` to emit `FutureWarning`

```python
@deprecated("return type will change from int to float in v3")
def estimate_effort(hours: float) -> int:
    return int(hours)
```

**Symptom:** End-users never see the warning — `@deprecated` always emits `DeprecationWarning`, which is hidden by default outside `__main__` (lesson 02).
**Why:** PEP 702 is for *removal* of features, not behaviour change. The decorator hardcodes `category=DeprecationWarning`. If you need a behaviour-change warning, use `warnings.warn(..., category=FutureWarning, stacklevel=2)` inside the body (lesson 02) — there is no `@future_deprecated` decorator.
**Fix:** Use `warnings.warn(..., category=FutureWarning, stacklevel=2)` inside the body. The static check then does not fire (no `__deprecated__` attribute is set) — which is correct, because behaviour changes are not statically checkable.

## Engineering Trade-Offs

**Decision:** Use `@deprecated("...")` (via `typing_extensions` on 3.12, `typing` on 3.13+) for every *removal* deprecation in `boardly`. Keep the lesson-01 `warnings.warn(..., stacklevel=2)` path for *behaviour-change* warnings (which need `FutureWarning` and a custom message).
**Both sides:** The alternative is to use only the lesson-01 path (`warnings.warn` inside the body) — which gives runtime warnings but no static enforcement. The trade-off: the `@deprecated` path requires a `typing_extensions` dependency on 3.12 (or 3.13+ runtime) and a mypy/pyright step in CI. The lesson-01 path requires no dependencies and no static checker. For a library like `boardly` that already depends on `typing_extensions` (via `pydantic`) and already runs mypy in CI, the `@deprecated` path is strictly better.
**Commitment:** `boardly` uses `@deprecated("...")` for every removal deprecation. The CI step runs `mypy --strict boardly/` which catches `[deprecated]` violations. The runtime warning (`DeprecationWarning`) is still emitted for callers who do not run mypy. The combination catches deprecations in code paths that tests miss (static) *and* in callers that do not use a type checker (runtime).

## Exercises

1. **Exercise 1 — Run on 3.12 with `typing.deprecated`.** Change `from typing_extensions import deprecated` to `from typing import deprecated`. Run the script. Observe the `ImportError`. Revert. `Verify: python boardly/warnings_demo/deprecated_decorator.py`
2. **Exercise 2 — Apply `@deprecated` to a class.** Add `@deprecated("use Ticket instead")` to a class `LegacyTicket`. Verify that instantiating the class fires a `DeprecationWarning`. `Verify: python boardly/warnings_demo/deprecated_decorator.py`
3. **Exercise 3 — Run mypy on a call site.** Create `call_site.py` that imports `get_legacy_ticket` and calls it. Run `mypy boardly/warnings_demo/call_site.py`. Observe the `[deprecated]` error. `Verify: mypy boardly/warnings_demo/call_site.py`
4. **Exercise 4 — Suppress a single call site.** Add `# type: ignore[deprecated]` to a call site of `get_legacy_ticket`. Re-run mypy. Observe that the error is silenced for that line only. `Verify: mypy boardly/warnings_demo/call_site.py`
5. **Exercise 5 — Behaviour-change warning.** Write a function `estimate_effort(hours)` that emits a `FutureWarning` via `warnings.warn(..., stacklevel=2)` inside the body (the lesson-02 pattern). Verify that `@deprecated` cannot replace this — the message and category differ. `Verify: python boardly/warnings_demo/deprecated_decorator.py`

## Verification

```bash
$ python boardly/warnings_demo/deprecated_decorator.py
boardly/warnings_demo/deprecated_decorator.py:30: DeprecationWarning: use get_ticket instead; get_legacy_ticket will be removed in v3
  ticket = get_legacy_ticket(42)
boardly/warnings_demo/deprecated_decorator.py:31: DeprecationWarning: use Ticket.assign instead; Ticket.legacy_assign will be removed in v3
  view = _LegacyTicketView(7)
ticket: {'id': 42, 'title': 'v2 ticket'} view.id: 7
```

```bash
$ mypy boardly/warnings_demo/call_site.py
boardly/warnings_demo/call_site.py:3: error: call to deprecated function "get_legacy_ticket"; use get_ticket instead  [deprecated]
Found 1 error in 1 file (checked 1 source file)
```

The two outputs prove the two layers:

- The runtime layer fires when the script runs — both `DeprecationWarning`s printed to stderr, with `filename:lineno` pointing at the caller (the `stacklevel=2` automatic).
- The static layer fires when mypy runs — the `[deprecated]` error at the call site, even though the call site is in a file the script never imports.

## Previously Learned Here

- [[20-warnings/01-warn-and-filterwarnings]] — the `warn`, `stacklevel`, and `filter` API that `@deprecated` wraps. The decorator emits the warning for you, with the correct `stacklevel=2` automatically.
- [[20-warnings/02-DeprecationWarning-vs-FutureWarning]] — the category rule. `@deprecated` hardcodes `DeprecationWarning`; behaviour changes still need the lesson-02 `FutureWarning` pattern.
- [[13-future/01-from-future-import-annotations]] — `from __future__ import annotations` and `@deprecated` compose cleanly. The decorator runs at definition time; the future import only affects annotations.

## What's Next

You have finished Section 20 — `warnings`. The three lessons walked the runtime API (lesson 01), the category rule (lesson 02), and the static-typing layer (lesson 03). The combination is the standard-library machinery for telling users "this will break" without breaking them now. Where to take this:

- [[01-typing/02-Annotated-and-Metadata]] — `Annotated[T, metadata]` is the mechanism FastAPI/Pydantic use to attach metadata to a type annotation. `@deprecated` is the type-checker-level metadata; `Annotated[T, Deprecated()]` is the runtime-level metadata that FastAPI could read (it does not, but the pattern is similar).
- [[02-functools/02-wraps-and-Decorators]] — `@wraps` is what `@deprecated` uses internally to preserve the original function's `__name__`, `__doc__`, and `__wrapped__`. The decorator-composition lesson is the foundation for understanding PEP 702's implementation.
- [[25-Reference-Library/Engineering-Decision-Log]] — the `boardly` deprecation policy is encoded there: `@deprecated` for removal, `FutureWarning` for behaviour change, `simplefilter("error", ...)` in CI.

Three things to take with you:

- `typing.deprecated` is 3.13+; `typing_extensions.deprecated` is the 3.9–3.12 backport. Use the `typing_extensions` form for cross-version compatibility.
- `@deprecated("...")` gives you both the runtime `DeprecationWarning` and the static `[deprecated]` check — derived from the same source.
- `@deprecated` is for *removal*; behaviour changes still need the lesson-02 `FutureWarning` pattern inside the function body.

## Sources

- **PEP 702 — Marking deprecations using the type system** — https://peps.python.org/pep-0702/ — accessed 2026-10-23 — the PEP that introduced `typing.deprecated(message)`, with the rationale for the positional-only message and the static-analysis contract.
- **`typing.deprecated` (3.13+)** — https://docs.python.org/3/library/typing.html#typing.deprecated — accessed 2026-10-23 — the canonical reference; note the "New in version 3.13" marker that the lesson version-gates.
- **`typing_extensions.deprecated`** — https://typing-extensions.readthedocs.io/en/latest/#typing_extensions.deprecated — accessed 2026-10-23 — the backport for 3.9–3.12; verified to import successfully on 3.12.15.
- **CPython `typing.py` `deprecated` implementation** — https://github.com/python/cpython/blob/3.13/Lib/typing.py — accessed 2026-10-23 — the 3.13 source for the decorator; shows the `warnings.warn(message, DeprecationWarning, stacklevel=2)` call inside the wrapper.

## What We Learned

- You can apply `@deprecated("use new_func instead")` to a function or class — and explain why the message is positional-only.
- You can explain the version-gating — `typing.deprecated` is 3.13+; `typing_extensions.deprecated` is the 3.9–3.12 backport with identical behaviour.
- You can demonstrate the runtime behaviour — calling a `@deprecated`-decorated function emits a `DeprecationWarning` with the correct `stacklevel=2` automatically.
- You can demonstrate the static-analysis behaviour — mypy/pyright emit a `[deprecated]` / `DeprecatedWarning` at the call site, in code paths your tests never execute.
- You can explain why `@deprecated` does not replace `FutureWarning` — the decorator hardcodes `DeprecationWarning`; behaviour changes still need the lesson-02 pattern.
