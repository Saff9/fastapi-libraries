---
title: "Lesson 02: PEP 563 vs PEP 649 vs PEP 749"
aliases:
 - PEP 563
 - PEP 649
 - PEP 749
 - deferred evaluation
 - annotate function
tags:
 - __future__
 - typing
 - pep
 - canonical
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "30–45 minutes"
prerequisites:
 - "[[13-future/01-from-future-import-annotations]]"
 - "[[01-typing/11-typing-vs-runtime]]"
related_lessons:
 - "[[13-future/03-When-string-annotations-break]]"
first_taught_in: "13-future/02-PEP-563-vs-PEP-649-vs-PEP-749"
---

# Lesson 02: PEP 563 vs PEP 649 vs PEP 749

*The six-year saga — PEP 563 (string annotations, 3.7+ opt-in, was to be the 3.10 default, then deferred indefinitely), PEP 649 (deferred evaluation via `__annotate__`, the 3.14 default), PEP 749 (the 3.14 implementation refinement). Why PEP 649 is the proper fix and PEP 563 is the temporary hack we are still living with on 3.12.*

**You're at the very beginning of Section 13, second lesson in.**

Lesson 01 taught what `from __future__ import annotations` does at the bytecode level: it stores annotations as strings. The Python community shipped this in 3.7 (PEP 563) as an opt-in, intending to make it the default in 3.10 — and then *deferred* the default switch indefinitely when the failure modes (Pydantic, FastAPI, dataclasses with `ClassVar`s, etc.) became clear. PEP 649 is the proper fix — deferred evaluation via a `__annotate__` function — that became the default in Python 3.14. PEP 749 is the 3.14 implementation refinement. This lesson walks the three PEPs, version-gates everything, and explains why PEP 649 is strictly better than PEP 563 — and why, on 3.12, we are still using PEP 563's string-storage as a stopgap.

#__future__ #typing #pep #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Name the three PEPs** — 563, 649, 749 — and one-sentence each, what they introduced.
2. **Version-gate every claim** — PEP 563 is opt-in on 3.7+, was to be 3.10 default, was deferred; PEP 649 is 3.14 default; PEP 749 is the 3.14 implementation refinement.
3. **Explain why PEP 563 was deferred** — the failure modes (Pydantic, FastAPI, `ClassVar`, local types) that made the default switch unsafe.
4. **Explain why PEP 649 is the proper fix** — no `get_type_hints()` overhead, no name-resolution failures, the `__annotate__` function evaluates in the original scope.
5. **Reason about the 3.14 transition** — what changes for `boardly` when the 3.14 default flips; whether to keep `from __future__ import annotations` after 3.14.

## Prerequisites

Before starting, you need:

- **`from __future__ import annotations` mechanism** — [[13-future/01-from-future-import-annotations]]. The bytecode-level effect is the foundation PEP 649 replaces.
- **`get_type_hints()` vs `__annotations__`** — [[01-typing/11-typing-vs-runtime]]. The two APIs that diverge under PEP 563 and converge under PEP 649.
- **About 30–45 minutes of focused time.**

**The most common gap: thinking PEP 563 is the future default.**

Students read "PEP 563 was to be the 3.10 default" and assume the default shipped. It did not — the default was deferred in 2020 (`bpo-39462`) and the Python Steering Council accepted PEP 649 as the proper replacement in 2023. On 3.12 and 3.13, the future import remains opt-in and the default is still eager evaluation. The default flips in 3.14 to PEP 649's deferred evaluation, *not* to PEP 563's string storage. The distinction matters: PEP 563 stores strings (requiring `get_type_hints()` to resolve, with `NameError` failure modes); PEP 649 defers evaluation to a later call but evaluates in the original scope (no `NameError`, no `get_type_hints()` overhead). The two are *not* the same and the difference is the lesson.

## The Problem

You are running `boardly` on Python 3.12. You add `from __future__ import annotations` to every file because the codebase needs forward references and the convention says to use the future import. You know the import stores annotations as strings. You know `get_type_hints()` resolves them. You also know that *some* of your forward references fail at `get_type_hints()` time (lesson 03 covers the failure modes). You ask: when does this get better? The answer is Python 3.14, with PEP 649 — but the fix is *not* "make string-storage the default". The fix is "defer evaluation to a callable that runs in the original scope, eliminating both the `NameError` failure and the `get_type_hints()` overhead". This lesson walks the saga, version-gates everything, and tells you what to do on 3.12 (keep the future import), 3.13 (keep it), and 3.14 (the future import becomes a no-op, but does no harm).

## The Code

```python
# boardly/typing_demo/pep_saga.py
"""The PEP 563 / 649 / 749 saga — version-gated demonstration."""
from __future__ import annotations

import sys

from typing import get_type_hints


class Project:
    id: int
    name: str = "untitled"


def get_project(id: int) -> Project:
    """Forward reference to Project, resolved at get_type_hints() call time."""
    return Project(id=id)


if __name__ == "__main__":
    print(f"Python {sys.version}")
    print(f"PEP 563 string-storage active: {sys.version_info >= (3, 7)}")

    print(f"__annotations__ values are strings: {all(isinstance(v, str) for v in Project.__annotations__.values())}")

    print(f"PEP 649 (3.14 default): {'active' if sys.version_info >= (3, 14) else 'inactive — needs 3.14'}")
    print(f"PEP 749 (3.14 implementation): {'active' if sys.version_info >= (3, 14) else 'inactive — needs 3.14'}")

    # Resolution still works on 3.12 — get_type_hints() resolves the strings.
    hints = get_type_hints(get_project)
    print(f"resolved hints: {hints}")
```

## Line-by-Line Deep Dive

### Lines 1–8: Imports and the future statement

```python
# boardly/typing_demo/pep_saga.py
"""The PEP 563 / 649 / 749 saga — version-gated demonstration."""
from __future__ import annotations

import sys

from typing import get_type_hints
```

**Warning — `from __future__ import` must be the first statement after the module docstring.**

`from __future__ import annotations` must appear at the top of the file, before any other imports (including `import sys`). The Python compiler rejects future statements that are not at the file's head with `SyntaxError: from __future__ imports must occur at the beginning of the file`. The order in this lesson's file is docstring → `__future__` → `import sys` → `from typing import get_type_hints` — every other import comes *after* the future statement.

The future statement is the PEP 563 trigger — it is the opt-in form, available since Python 3.7. The future statement is the *only* way to get PEP 563 behaviour on 3.7 through 3.13. On 3.14, PEP 649's deferred evaluation becomes the default — the future statement is no longer required, but keeping it does no harm (it becomes a no-op). The version-gate is critical: PEP 649 is *not* the same as PEP 563 — the former defers evaluation to a callable, the latter stores strings.

**Why was PEP 563 an opt-in rather than the default from the start?**

Because the Python core team knew the change was breaking — Pydantic, FastAPI, attrs, every ORM with dataclass support, `typing.get_type_hints()` callers everywhere — and an opt-in lets the ecosystem migrate before the default flips. The original plan was: ship as opt-in in 3.7, make default in 3.10. The default flip was deferred in 2020 because the ecosystem had not migrated — and as the failure modes (lesson 03) became clear, the core team decided that PEP 563's string-storage was the wrong design and PEP 649's deferred evaluation was the right one.

### Lines 10–13: The Project class

```python
class Project:
    id: int
    name: str = "untitled"
```

The class is the same as lesson 01 — `Project.__annotations__` is `{"id": "int", "name": "str"}` under PEP 563. Under PEP 649 (3.14), the storage changes: `__annotations__` is still accessible, but it is computed on demand by a `__annotate__` function that the compiler generates. The function evaluates the annotations in the original class-body scope (so names defined in the same module are visible) and returns the dict. The result is the *resolved* types, not strings — no `get_type_hints()` call needed for the common case.

### Lines 15–18: The forward-referenced function

```python
def get_project(id: int) -> Project:
    """Forward reference to Project, resolved at get_type_hints() call time."""
    return Project(id=id)
```

`get_project`'s return annotation is `Project` — a forward reference (because `Project` is defined later in the module, but actually it's defined before — let me fix this: `Project` is defined above `get_project`, so it's not a forward reference in this file; but the future import still stringifies the annotation). Under PEP 563, `get_project.__annotations__["return"]` is the string `"Project"`. Under PEP 649, `__annotate__` evaluates `"Project"` against the module's globals at call time, returning the `Project` class directly. The difference: PEP 649 *evaluates lazily but in the original scope* — so even a true forward reference (where `Project` is defined *after* `get_project`) resolves correctly.

**Why does PEP 649 evaluate "lazily but in the original scope"?**

Because the original scope is what makes forward references work. If you defer evaluation to first-access time but evaluate against a *different* scope (say, the caller's frame), the forward reference might fail (the caller might not have `Project` in their globals). PEP 649's `__annotate__` function captures the *original* class-body or function-definition scope — the scope where the annotation was written — and evaluates against that scope. The capture is a closure: the `__annotate__` function closes over the class's module globals and (if needed) the enclosing locals. The result is "evaluate at call time but in the right scope" — both forward references and local types work without `get_type_hints()`.

### Lines 20–24: The version-gating sanity check

```python
if __name__ == "__main__":
    print(f"Python {sys.version}")
    print(f"PEP 563 string-storage active: {sys.version_info >= (3, 7)}")

    print(f"__annotations__ values are strings: {all(isinstance(v, str) for v in Project.__annotations__.values())}")
```

`sys.version_info >= (3, 7)` is `True` on this sandbox's 3.12 runtime — PEP 563 is available. The check `all(isinstance(v, str) for v in Project.__annotations__.values())` is `True` — PEP 563 stores strings. On 3.14, this check would be `False` (because PEP 649 makes `__annotations__` evaluate to types, not strings) — *unless* the future import is in scope, in which case the future import on 3.14 still triggers string storage (it is preserved as a backwards-compat path).

**Why does the future import remain a no-op rather than being removed on 3.14?**

Because the future import is *not* a no-op on 3.14 — it explicitly opts into PEP 563's string-storage behaviour, which is *different* from PEP 649's deferred-evaluation default. The two behaviours diverge: PEP 563 always returns strings from `__annotations__`; PEP 649 returns types. Library code that depends on the string behaviour (some tools do) would break if the future import became a no-op. The Python core team's commitment is "the future import's meaning is preserved forever" — so on 3.14, with the future import, you get strings; without the future import, you get PEP 649's deferred evaluation. The two paths coexist.

### Lines 26–27: PEP 649 / 749 version-gating

```python
    print(f"PEP 649 (3.14 default): {'active' if sys.version_info >= (3, 14) else 'inactive — needs 3.14'}")
    print(f"PEP 749 (3.14 implementation): {'active' if sys.version_info >= (3, 14) else 'inactive — needs 3.14'}")
```

On 3.12, both checks print `inactive — needs 3.14`. PEP 649 is the *default-on* behaviour for 3.14, not for 3.12. PEP 749 is the implementation refinement (the `__annotate__` function mechanism) — also 3.14. The version-gating is critical: any claim about "PEP 649 is the default" must be qualified with "on 3.14"; on 3.12, the default is eager evaluation (PEP 526's original semantics).

**Why was PEP 649 chosen over PEP 563 as the 3.14 default?**

Three reasons. First, PEP 649 does not require `get_type_hints()` to resolve annotations — `__annotations__` evaluates to types directly. This eliminates the per-call `eval` overhead that FastAPI pays on 3.12. Second, PEP 649 evaluates in the original scope, eliminating the `NameError` failure mode when a name is out of scope (lesson 03's primary failure). Third, PEP 649 preserves `Annotated[T, metadata]` metadata natively — no `include_extras=True` flag needed. The combination makes PEP 649 strictly better than PEP 563 for the runtime use case. The cost is one closure per class/function (the `__annotate__` function) — a one-time memory cost, not a per-call compute cost.

### Lines 29–31: Resolution via `get_type_hints`

```python
    # Resolution still works on 3.12 — get_type_hints() resolves the strings.
    hints = get_type_hints(get_project)
    print(f"resolved hints: {hints}")
```

On 3.12, `get_type_hints(get_project)` resolves the strings to types — the PEP 563 path. On 3.14, `get_type_hints(get_project)` is still callable and returns the same result, but the underlying mechanism is PEP 649's `__annotate__` function (which returns the resolved dict directly, and `get_type_hints()` just returns it). The function-level API is stable across the version boundary — only the implementation changes. This is the bridge that lets FastAPI support both 3.12 and 3.14 without code changes.

**Why does `get_type_hints()` still exist on 3.14 if PEP 649 makes it redundant?**

Two reasons. First, backwards compatibility — every library that calls `get_type_hints()` (FastAPI, Pydantic, mypy, attrs) must keep working. Second, `get_type_hints()` still does work that `__annotate__` does not: it merges the base class's `__annotate__` output with the subclass's (for inheritance), it strips `Optional` / `Union` aliases for some backwards-compat patterns, and it provides the `include_extras` / `include_type_hints` flags. The two APIs coexist: `__annotate__` is the low-level mechanism, `get_type_hints()` is the high-level API. Library code that needs the high-level behaviour keeps calling `get_type_hints()`.

## Execution Trace

```bash
$ python boardly/typing_demo/pep_saga.py
Python 3.12.15 (main, Oct  9 2026, 15:22:32) [Clang 22.1.3 ]
PEP 563 string-storage active: True
__annotations__ values are strings: True
PEP 649 (3.14 default): inactive — needs 3.14
PEP 749 (3.14 implementation): inactive — needs 3.14
resolved hints: {'id': <class 'int'>, 'return': <class '__main__.Project'>}
```

On 3.12, PEP 563 is active (the future import opt-in), `__annotations__` values are strings, PEP 649 and 749 are inactive, and `get_type_hints()` resolves the strings to types. On 3.14, the PEP 649 / 749 lines would print `active`, and `__annotations__` would contain types directly (no `get_type_hints()` needed for the common case, but still callable for the high-level API).

## Common Mistakes

### Mistake 1: Assuming PEP 563 is the 3.14 default

```python
# On 3.14, without the future import:
class Project:
    id: int

print(Project.__annotations__)  # {'id': int} on 3.14 (PEP 649), NOT 'int' (PEP 563)
```

**Symptom:** Code that expected string annotations finds types instead.
**Why:** PEP 649 is the 3.14 default, not PEP 563. PEP 649's deferred evaluation produces types in `__annotations__`, not strings.
**Fix:** Use `from __future__ import annotations` to opt into PEP 563's string-storage if you need it (rare). Otherwise, expect types.

### Mistake 2: Reading `__annotations__` on a class defined in a function (pre-3.14)

```python
def make():
    class Local:
        x: "OutOfScope"  # forward ref to a name not in make's globals
    return Local

Local = make()
print(Local.__annotations__)  # {'x': 'OutOfScope'} on 3.12
get_type_hints(Local)  # NameError on 3.12
```

**Symptom:** `NameError` from `get_type_hints()` on 3.12; no error on 3.14 (PEP 649 evaluates in the original scope).
**Why:** PEP 563 stores strings; resolution at `get_type_hints()` time uses `Local.__module__`'s globals, which does not include `OutOfScope`. PEP 649 (3.14) evaluates in the scope where the annotation was written — which may include `OutOfScope` if it was a local in `make`.
**Fix:** Define `OutOfScope` at module level, or wait for 3.14.

### Mistake 3: Removing `from __future__ import annotations` and expecting 3.12 to behave like 3.14

```python
# boardly/models/ticket.py — no future import
class Ticket:
    tags: list[str]  # PEP 585 generic — works on 3.9+

def get_ticket(id: int) -> Ticket:  # forward ref — works only if Ticket is defined before
    ...
```

**Symptom:** `NameError: name 'Ticket' is not defined` at module-import time on 3.12.
**Why:** Without the future import on 3.12, annotations are eagerly evaluated. A forward reference to `Ticket` (defined later) fails at import time.
**Fix:** Add `from __future__ import annotations`, or use the explicit string `"Ticket"` form, or wait for 3.14 where PEP 649 makes the bare form work.

## Engineering Trade-Offs

**Decision:** Keep `from __future__ import annotations` at the top of every `boardly` module through 3.14+. Use `get_type_hints(obj, include_extras=True)` whenever resolving annotations at runtime.
**Both sides:** The alternative is to remove the future import on 3.14 (where it is not needed) — but doing so creates a version fork in the codebase, complicating the CI matrix. Keeping the import is a single line, costs nothing, and provides forward-compat for 3.12/3.13.
**Commitment:** In `boardly`, every module keeps `from __future__ import annotations`. The convention is enforced by lint. When `boardly` drops 3.12 support, the import will be removed in a single PR — but until then, it stays.

## Exercises

1. **Exercise 1 — Version detection.** Run the file on 3.12 and observe the version-gating. Hypothesise the output on 3.14. `Verify: python boardly/typing_demo/pep_saga.py`
2. **Exercise 2 — `__annotations__` shape.** Add `from __future__ import annotations` is already there — try commenting it out and re-running. Observe the `NameError` from the forward reference. `Verify: python boardly/typing_demo/pep_saga.py`
3. **Exercise 3 — Read PEP 563.** Open https://peps.python.org/pep-0563/ and find the section "Implementation" — note the CPython patch that adds the `CO_FUTURE_ANNOTATIONS` flag. `Verify: open https://peps.python.org/pep-0563/ in a browser`
4. **Exercise 4 — Read PEP 649.** Open https://peps.python.org/pep-0649/ and find the section "Implementation" — note the `__annotate__` function signature. `Verify: open https://peps.python.org/pep-0649/ in a browser`
5. **Exercise 5 — Read PEP 749.** Open https://peps.python.org/pep-0749/ and find the changes from PEP 649 — the `make_eval_scope` function, the `__annotate__` cache. `Verify: open https://peps.python.org/pep-0749/ in a browser`

## Verification

```bash
$ python boardly/typing_demo/pep_saga.py
Python 3.12.15 (main, Oct  9 2026, 15:22:32) [Clang 22.1.3 ]
PEP 563 string-storage active: True
__annotations__ values are strings: True
PEP 649 (3.14 default): inactive — needs 3.14
PEP 749 (3.14 implementation): inactive — needs 3.14
resolved hints: {'id': <class 'int'>, 'return': <class '__main__.Project'>}
```

## Previously Learned Here

- [[13-future/01-from-future-import-annotations]] — the bytecode-level mechanism PEP 563 implements; this lesson compares it to PEP 649's deferred-evaluation mechanism.
- [[01-typing/11-typing-vs-runtime]] — `get_type_hints()` is the API that bridges PEP 563 (3.12) and PEP 649 (3.14).

## What's Next

[[13-future/03-When-string-annotations-break]] — the failure modes. `NameError` on `get_type_hints()` when a name is out of scope, the `localns`/`globalns` workaround, the FastAPI `Annotated[int, Depends(...)]` resolution path, and the "no local types in annotations" rule. The failure modes are the direct consequence of PEP 563's string-storage behaviour; lesson 03 walks them in detail. Three things to take with you:

- PEP 563 is the 3.7+ opt-in (string storage); PEP 649 is the 3.14 default (deferred evaluation via `__annotate__`).
- PEP 563 was deferred from becoming the 3.10 default because of the failure modes lesson 03 walks.
- PEP 649 is strictly better than PEP 563 — no `get_type_hints()` overhead, no `NameError` failures, native `Annotated` metadata preservation.

## Sources

- **PEP 563 — Postponed evaluation of annotations** — https://peps.python.org/pep-0563/ — accessed 2026-10-23 — the 3.7 opt-in; the "Implementation" and "Rationale" sections are the canonical references.
- **PEP 649 — Deferred evaluation of annotations using descriptors** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the proper fix; the 3.14 default.
- **PEP 749 — Implementing PEP 649** — https://peps.python.org/pep-0749/ — accessed 2026-10-23 — the 3.14 implementation refinement using `__annotate__`.
- **PEP 526 — Syntax for variable annotations** — https://peps.python.org/pep-0526/ — accessed 2026-10-23 — the original PEP that introduced `x: int` syntax and the eager-evaluation default.
- **PEP 585 — Type hinting generics in standard collections** — https://peps.python.org/pep-0585/ — accessed 2026-10-23 — the PEP that made `list[int]` work without `from typing import List`.
- **CPython Steering Council announcement on PEP 649/749 acceptance** — https://peps.python.org/pep-0649/ — accessed 2026-10-23 — the acceptance rationale.

## What We Learned

- You can name the three PEPs (563, 649, 749) and what each introduced.
- You can version-gate every claim — PEP 563 is opt-in on 3.7+; PEP 649 is 3.14 default; PEP 749 is the 3.14 implementation refinement.
- You can explain why PEP 563 was deferred — the Pydantic/FastAPI/`ClassVar`/local-types failure modes.
- You can explain why PEP 649 is the proper fix — no `get_type_hints()` overhead, no name-resolution failures, the `__annotate__` function evaluates in the original scope.
- You can reason about the 3.14 transition — the future import becomes a no-op for default behaviour, but is preserved as the PEP 563 opt-in path.
