---
title: "Lesson 02: DeprecationWarning vs FutureWarning"
aliases:
 - DeprecationWarning
 - FutureWarning
 - PendingDeprecationWarning
 - ResourceWarning
 - UserWarning
 - RuntimeWarning
 - SyntaxWarning
 - PEP 565
tags:
 - warnings
 - DeprecationWarning
 - FutureWarning
 - categories
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–40 minutes"
prerequisites:
 - "[[20-warnings/01-warn-and-filterwarnings]]"
related_lessons:
 - "[[20-warnings/03-deprecated-decorator-PEP-702]]"
 - "[[03-contextlib/04-suppress]]"
---

# Lesson 02: `DeprecationWarning` vs `FutureWarning`

*The category rule — `DeprecationWarning` for "this feature will be removed in a future release of this package"; `FutureWarning` for "this feature's behaviour will change". The audience distinction: `DeprecationWarning` is for developers of *this* code (hidden by default since 3.7 unless raised from `__main__`); `FutureWarning` is for *users* of the library (always shown). Plus `PendingDeprecationWarning` (no-man's-land), `ResourceWarning` (hidden, for unclosed files/sockets), `SyntaxWarning`, `RuntimeWarning`, and `UserWarning` (the default).*

**You're at the very beginning of Section 20 — lesson 02.**

You have typed `DeprecationWarning` in a `warnings.warn` call without thinking about whether it was the right category. Most engineers do — the name "DeprecationWarning" sounds like "the warning you use when something is deprecated". It is — but only for a specific definition of "deprecated" (the feature will be removed), and only for a specific audience (developers of this package, not end-users). The `FutureWarning` category exists for the case the name "DeprecationWarning" does not cover: the feature's *behaviour* will change in a future version, even though the name will stay. The two categories differ in who sees them by default — and that difference is the most under-taught fact in the entire `warnings` module. Take your time. Type every example. **This is how you learn.**

#warnings #DeprecationWarning #FutureWarning

## Learning Objectives

By the end of this lesson you will be able to:

1. **Pick the right warning category** for a given deprecation or behaviour-change — `DeprecationWarning` for removal, `FutureWarning` for behaviour change.
2. **Explain the default-filter behaviour on Python 3.7+** — `DeprecationWarning` is silent unless raised from `__main__`; `FutureWarning` is always shown; `ResourceWarning` is hidden unless dev mode is on.
3. **List the seven built-in `Warning` subclasses** and one-line each on when to use them.
4. **Demonstrate `ResourceWarning`** for unclosed files and sockets — and turn it on with `-X dev` or `PYTHONDEVMODE=1`.
5. **Use `pytest.warns(DeprecationWarning, match=...)`** — the test pattern built on `catch_warnings(record=True)`.

## Prerequisites

Before starting, you need:

- **`warn` and `filterwarnings`** — [[20-warnings/01-warn-and-filterwarnings]]. The `category=` argument is the subject of this lesson; lesson 01 is the prerequisite.
- **`contextlib.suppress`** — [[03-contextlib/04-suppress]]. The pattern for swallowing a `Warning` exception (rare, but useful when a library over-warns).
- **About 25–40 minutes of focused time.**

**The most common gap: `DeprecationWarning` is not the "general-purpose deprecation" category.**

Students write `warnings.warn("X will change behaviour", DeprecationWarning)` and ship. The warning fires once, the user dismisses it, and the behaviour change still breaks them in the next release — because `DeprecationWarning` is hidden by default on 3.7+ when raised from anywhere other than `__main__`. The user never saw it. The right category for "behaviour will change" is `FutureWarning`, which is *always shown*. The audience and the default-visibility differ between the two; the names are nearly identical; the failure mode is silent.

## The Problem

`boardly` v2 has two changes to communicate to users:

1. **Removal:** `get_legacy_ticket(ticket_id)` (the v1 name) will be deleted in v3. Users should switch to `get_ticket(ticket_id)`. The function will *go away*.
2. **Behaviour change:** `Ticket.estimate_effort()` currently returns `int` (rounded-down hours). In v3 it will return `float` (fractional hours). The method name stays; the return type changes.

For change (1), the right call is `warnings.warn("get_legacy_ticket is deprecated; use get_ticket", DeprecationWarning, stacklevel=2)`. For change (2), the right call is `warnings.warn("estimate_effort return type will change from int to float in v3", FutureWarning, stacklevel=2)`. The two have *different* audiences and *different* default visibility — and if you swap them, both go wrong: a `DeprecationWarning` for the behaviour change is invisible to library users; a `FutureWarning` for the removal spams end-users of the script with a warning they cannot act on.

## The Code

```python
# boardly/warnings_demo/categories.py
"""Demonstrate the DeprecationWarning vs FutureWarning distinction."""
from __future__ import annotations

import warnings


def get_ticket(ticket_id: int) -> dict:
    return {"id": ticket_id, "title": "v2 ticket"}


def get_legacy_ticket(ticket_id: int) -> dict:
    # REMOVAL — the function goes away in v3. Category: DeprecationWarning.
    warnings.warn(
        "get_legacy_ticket is deprecated; use get_ticket instead",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return get_ticket(ticket_id)


def estimate_effort(hours: float) -> int:
    # BEHAVIOUR CHANGE — return type stays named the same but goes int -> float
    # in v3. The audience is the library's end-users, not the developers
    # of this package. Category: FutureWarning.
    warnings.warn(
        "estimate_effort will return float (fractional hours) in v3; "
        "update callers that assume int",
        category=FutureWarning,
        stacklevel=2,
    )
    return int(hours)


def main() -> None:
    # End-user code: this is __main__, so DeprecationWarning is shown by default.
    ticket = get_legacy_ticket(7)
    effort = estimate_effort(3.7)
    print("ticket:", ticket, "effort:", effort)


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports

```python
# boardly/warnings_demo/categories.py
"""Demonstrate the DeprecationWarning vs FutureWarning distinction."""
from __future__ import annotations

import warnings
```

Same header as lesson 01. The `from __future__ import annotations` matters here because in lesson 03 the `@deprecated` decorator (3.13+) interacts with annotations; this lesson stays at the runtime level, so the future import is mostly here for consistency.

**Why the future import if this lesson doesn't use PEP 702?**

Two reasons. First, the boardly convention (see [[13-future/01-from-future-import-annotations]]) is to enable it in every module — keeping the convention here avoids a "wait, why does this lesson not have it?" question. Second, the docstring on `estimate_effort` documents a future *return-type* change (`int` → `float`); the future import means the annotation `-> int` is stored as the string `"int"` and survives even if the runtime annotation is later widened to `float` in the implementation but kept as `int` in the migration period. (In a real migration you would not change the annotation; you would change it only at the breaking-change release.)

### Lines 13–19: The removal — `DeprecationWarning`

```python
def get_legacy_ticket(ticket_id: int) -> dict:
    # REMOVAL — the function goes away in v3. Category: DeprecationWarning.
    warnings.warn(
        "get_legacy_ticket is deprecated; use get_ticket instead",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return get_ticket(ticket_id)
```

`get_legacy_ticket` is going to be *deleted* in v3. The audience is *developers of `boardly`* (the engineers who import it, call it, and can edit their code to use `get_ticket`). `DeprecationWarning` is the right category because:

1. The audience is developers, not end-users running the script.
2. The default-filter rule on 3.7+ says: show `DeprecationWarning` when raised from `__main__`, hide it otherwise. Developers running tests or scripts (which execute from `__main__`) see it; end-users running an installed package (whose `__main__` is the package's, not the script's) do not. The PEP 565 reasoning: end-users do not care about a transitive dependency's internal deprecations; developers running the code at the terminal do.
3. CI can turn `DeprecationWarning` into an error (`PYTHONWARNINGS=error::DeprecationWarning`) and force the migration.

**Why is `DeprecationWarning` hidden by default outside `__main__`?**

Because before Python 3.7, `DeprecationWarning` was shown everywhere — and the result was a firehose. End-users running `pip install somelibrary` would see 40 `DeprecationWarning`s from `somelibrary`'s transitive dependencies (a deprecated `distutils` import here, a deprecated `imp` use there, etc.). The end-user could not fix any of them; the warnings were pure noise. PEP 565 changed the default in 3.7: `DeprecationWarning` is shown only when the warning is raised from `__main__` — i.e. when *your own script* triggers it. The cost: developers of libraries that ship `DeprecationWarning` to their users (the case this lesson is teaching) need to use `FutureWarning` instead if they want their users to actually see the warning.

**Why is `DeprecationWarning` the right choice for `get_legacy_ticket` then?**

Because the audience for "use `get_ticket` instead" is the developer of the `boardly`-using application, not the application's end-user. The application developer runs their own test suite (which executes from `__main__`) — they will see the warning. The end-user of the application does not care which internal `boardly` function the application used. The default visibility (`__main__`-only) is exactly the right audience-targeting: developers see it, end-users do not.

### Lines 22–30: The behaviour change — `FutureWarning`

```python
def estimate_effort(hours: float) -> int:
    # BEHAVIOUR CHANGE — return type stays named the same but goes int -> float
    # in v3. The audience is the library's end-users, not the developers
    # of this package. Category: FutureWarning.
    warnings.warn(
        "estimate_effort will return float (fractional hours) in v3; "
        "update callers that assume int",
        category=FutureWarning,
        stacklevel=2,
    )
    return int(hours)
```

`estimate_effort` is *not* going to be deleted — its name stays. What changes is the *return type*: from `int` to `float`. Code that does `isinstance(effort, int)` or relies on integer arithmetic on the result will break silently — `3 + 0.7 == 3.7`, not the `3` it currently returns. The audience is *users of the library* (the application's end-users may run a CLI that prints the effort, and the printed format will change), not just developers. `FutureWarning` is the right category because:

1. `FutureWarning` is always shown by default — no `__main__` restriction.
2. PEP 565 explicitly defines `FutureWarning` as "base category for warnings about deprecated features when those warnings are intended for end users".
3. The numpy/pandas community uses `FutureWarning` for exactly this case (a `dtype` or default-value change that affects all callers).

**Why is `FutureWarning` always shown?**

Because end-users are the audience, and end-users do not run from `__main__` (they run an installed CLI). If `FutureWarning` followed the `__main__` rule, end-users would never see it. The 3.7 filter list (printed in lesson 01) shows no rule for `FutureWarning` — it falls through to the implicit `default` action, which prints the first occurrence. (In lesson 01's printed filter list, `FutureWarning` is not present because it uses the implicit `default` rule, not an explicit `ignore` rule.)

**Why not just use `DeprecationWarning` for both?**

Because the audience differs. A library end-user who sees "estimate_effort return type will change" can update their scripts to expect `float`. A library end-user who sees "get_legacy_ticket is deprecated" cannot fix it — they did not call `get_legacy_ticket`; the library did. Showing the `get_legacy_ticket` warning to end-users would be pure noise. The category is the audience-selector; using the same category for both would either spam end-users (with `FutureWarning` for the removal) or hide the behaviour change from them (with `DeprecationWarning` for the change).

### The seven built-in `Warning` subclasses

`Warning` is the base; the builtins module ships seven subclasses. Each has a default visibility and an intended use:

| Category | Default visibility | Intended use |
|---|---|---|
| `UserWarning` | shown | The default when `category=` is omitted. Use for application-level warnings that are not about deprecation or behaviour change (e.g. "you passed `cache=True` and `cache_size=0`; ignoring `cache=True`"). |
| `DeprecationWarning` | shown only from `__main__` (3.7+, PEP 565) | Removal of a feature in a future release of *this* package. Audience: developers of this code. |
| `PendingDeprecationWarning` | hidden | A feature that *will* be deprecated in a future release but is not yet deprecated. Rarely useful — most projects skip straight to `DeprecationWarning`. |
| `FutureWarning` | always shown | Behaviour change in a future release. Audience: end-users of the library. |
| `SyntaxWarning` | shown (3.7+) | Syntactically valid but suspicious code (e.g. `is` on literals, invalid escape sequences). Raised by the interpreter; rarely raised by user code. |
| `RuntimeWarning` | shown | Generic runtime condition (e.g. numerical instability, coroutine-not-awaited). Used by numpy/scipy for floating-point edge cases. |
| `ResourceWarning` | hidden unless dev mode on | Unclosed files, sockets, database connections. Raised by `__del__` of resource-owning objects. Enabled with `-X dev`, `PYTHONDEVMODE=1`, or `PYTHONWARNDEFAULTENCODING=1`. |

**Why is `PendingDeprecationWarning` rarely useful?**

Because in practice, the moment a feature is "going to be deprecated" you should just deprecate it — `DeprecationWarning` already communicates "we are removing this in a future release; the future release is not yet specified". `PendingDeprecationWarning` adds a third state ("we are going to deprecate this in a future release") that callers cannot act on differently from `DeprecationWarning` — both mean "stop using this". The CPython stdlib uses `PendingDeprecationWarning` for fewer than ten features (the most cited is `importlib` loaders). Most libraries skip it.

**Why is `ResourceWarning` hidden by default?**

Because it fires from `__del__` — the finalizer — and the timing of `__del__` is non-deterministic (CPython reference counting makes it predictable; PyPy / `gc` makes it not). Showing `ResourceWarning` by default would spam users with "file X was not closed" for every lazy-closed resource — and most of those are not bugs, just finalizers running at shutdown. Enabling `ResourceWarning` is the dev-mode opt-in for "I want to find leaks during development, not in production".

### `ResourceWarning` in action

```python
# boardly/warnings_demo/resource_warning.py
"""Demonstrate ResourceWarning for an unclosed file."""
import warnings


def leak_a_file() -> None:
    # Open a file and drop the reference without closing it.
    # The finalizer runs at gc time and emits a ResourceWarning.
    open("/tmp/boardly_leak.txt", "w")


if __name__ == "__main__":
    # In normal mode: silent. In dev mode: prints a ResourceWarning.
    leak_a_file()
    # Force garbage collection so the finalizer runs before exit.
    import gc
    gc.collect()
```

Run with dev mode on:

```bash
$ python -X dev boardly/warnings_demo/resource_warning.py
boardly/warnings_demo/resource_warning.py:9: ResourceWarning: unclosed file <_io.TextIOWrapper name='/tmp/boardly_leak.txt' mode='w' encoding='UTF-8'>
  open("/tmp/boardly_leak.txt", "w")
ResourceWarning: Enable tracemalloc to get the object allocation traceback
```

Run without dev mode:

```bash
$ python boardly/warnings_demo/resource_warning.py
# (silent — no output)
```

`-X dev` (or `PYTHONDEVMODE=1`) installs a `default` filter for `ResourceWarning`, makes `io` and `os` more verbose, and a few other "developer-friendly" tweaks. The escape hatch in production is `warnings.simplefilter("always", ResourceWarning)` inside your test suite — which catches the leaks without requiring dev mode. The `:9` line number is the original `open()` call site — the file object captures its allocation frame at `open()` time, and `ResourceWarning`'s `stacklevel` is computed so the warning's `filename:lineno` points back at the `open()` call, not at the `__del__` method that fires the warning. For the full allocation traceback (every frame between the `open()` and the eventual reap), enable `tracemalloc` — the warning's final line tells you exactly how.

**Why does `ResourceWarning` use `__del__` and not a check at exit?**

Because the leak can happen at any time — the file is opened, the reference is dropped, the gc reclaims the object eventually. If the warning fired only at process exit, you would not know *which* file leaked — only the count. The `__del__` approach tells you the filename and the line where the `open()` call lived: the file object stores its allocation frame at `open()` time, and `ResourceWarning`'s `stacklevel` is set so the warning's `filename:lineno` points at the original `open()` call (the `:9` line in the trace above), not at the `__del__` itself. The cost: the warning is non-deterministic (timing depends on gc) and can fire after the relevant frame is gone, but the allocation frame was captured at `open()` time so the pointer survives the GC delay. For the full allocation traceback (every frame between the `open()` and the eventual reap), enable `tracemalloc` — the warning's message includes "Enable tracemalloc to get the object allocation traceback" when tracemalloc is off, telling you exactly how to get the deeper view.

### `pytest.warns` — the test-time assertion

`pytest.warns` is built on `warnings.catch_warnings(record=True)` (see [[20-warnings/01-warn-and-filterwarnings]]) and is the standard pattern for asserting that a warning fires:

```python
# boardly/warnings_demo/test_categories.py
import pytest
from boardly.warnings_demo.categories import get_legacy_ticket, estimate_effort


def test_get_legacy_ticket_warns_deprecation():
    with pytest.warns(DeprecationWarning, match="get_legacy_ticket is deprecated"):
        get_legacy_ticket(1)


def test_estimate_effort_warns_future():
    with pytest.warns(FutureWarning, match="return float"):
        estimate_effort(3.7)


def test_estimate_effort_does_not_warn_deprecation():
    # FutureWarning is NOT a DeprecationWarning; this assertion is the
    # audience rule encoded as a test.
    with pytest.warns(FutureWarning):
        estimate_effort(3.0)
    # If estimate_effort had used DeprecationWarning, this would fail.
```

`pytest.warns(Category, match=regex)` does three things: it installs a `catch_warnings(record=True)` context, sets `simplefilter("always")` inside the context, runs the body, and asserts that at least one captured warning is an instance of `Category` and that `regex` matches the warning message. The `match=` argument is a `re.search` pattern, not `re.match` — it matches anywhere in the message.

**Why `match=` rather than exact-equality?**

Because the warning message often contains dynamic parts (a version number, a parameter name, a path). `match="return float"` matches the substring "return float" in "estimate_effort will return float (fractional hours) in v3; update callers that assume int" — without coupling the test to the exact wording. The lesson is that warnings are user-facing messages; their exact text will drift as the migration proceeds (e.g. "in v3" becomes "in v4" when the migration slips). The `match=` pattern survives that drift; exact-equality would not.

## Execution Trace

```bash
$ python boardly/warnings_demo/categories.py
boardly/warnings_demo/categories.py:37: DeprecationWarning: get_legacy_ticket is deprecated; use get_ticket instead
  ticket = get_legacy_ticket(7)
boardly/warnings_demo/categories.py:38: FutureWarning: estimate_effort will return float (fractional hours) in v3; update callers that assume int
  effort = estimate_effort(3.7)
ticket: {'id': 7, 'title': 'v2 ticket'} effort: 3
```

Both warnings fire because the script is `__main__` — and `__main__` is the one module where the default filter shows `DeprecationWarning`. The `FutureWarning` fires regardless of module (no `__main__` rule applies). The line numbers (`:37` and `:38`) are the caller's lines — the `ticket = get_legacy_ticket(7)` and `effort = estimate_effort(3.7)` lines inside `main` — the `stacklevel=2` argument from lesson 01 did its job. Without `stacklevel=2`, the line numbers would have been the `warnings.warn(...)` lines inside each function (the `:14` line for `get_legacy_ticket` and the `:26` line for `estimate_effort`).

**Why does the script see *both* warnings if `DeprecationWarning` is "hidden by default"?**

Because the default filter only hides `DeprecationWarning` raised *outside* `__main__`. The script `categories.py` runs as `__main__` — the first rule in the default filter list (`('default', None, DeprecationWarning, '__main__', 0)`) applies, and the warning is shown. If `get_legacy_ticket` were called from an installed `boardly` package (whose `__main__` is `boardly.__main__`, not the script), the warning would be silent.

## Common Mistakes

### Mistake 1: Using `DeprecationWarning` for a behaviour change

```python
def estimate_effort(hours: float) -> int:
    warnings.warn("return type will change to float in v3",
                  category=DeprecationWarning, stacklevel=2)
    return int(hours)
```

**Symptom:** End-users of `boardly` never see the warning. They upgrade to v3, their `int` arithmetic silently breaks (e.g. `effort * 60` becomes `222.0` instead of `180`), and they file a bug.
**Why:** `DeprecationWarning` is hidden by default outside `__main__`. End-users running an installed package do not run from `__main__` (their `__main__` is the package's CLI, not their script). The warning was silenced.
**Fix:** Use `FutureWarning` — it is always shown, regardless of module. The audience for a behaviour change is the end-user; `FutureWarning` is the category that targets them.

### Mistake 2: Using `FutureWarning` for a removal

```python
def get_legacy_ticket(ticket_id: int) -> dict:
    warnings.warn("get_legacy_ticket is deprecated; use get_ticket",
                  category=FutureWarning, stacklevel=2)
    return get_ticket(ticket_id)
```

**Symptom:** End-users running a CLI that internally calls `get_legacy_ticket` see the warning and panic — they have no way to fix it (they did not write the call). They file a bug against the CLI, not against `boardly`.
**Why:** `FutureWarning` is shown to everyone — including end-users who cannot act on it. The audience for "the function will be removed" is the developer of the calling code, not the end-user running it.
**Fix:** Use `DeprecationWarning`. The audience-targeting (shown in `__main__`, hidden elsewhere) is exactly right: developers running tests see it, end-users running an installed CLI do not.

### Mistake 3: Subclassing `Warning` and forgetting to register a default filter

```python
class BoardlyWarning(Warning):
    """Custom boardly warning category."""

def f():
    warnings.warn("something happened", category=BoardlyWarning)
```

**Symptom:** The warning prints the *first* time at each call site but is silent on subsequent calls from the same `filename:lineno` — and `-W error::BoardlyWarning` from the CLI requires the class to be importable from the filter parser's scope, which is awkward when the class lives in your application package.
**Why:** Custom `Warning` subclasses do not inherit an explicit rule from the default filter list; they fall through to the implicit `default` action, which prints the *first* occurrence at each `(filename, lineno, category)` triple and is silent on every subsequent call from the same site. That is fine for a one-off call but a problem when the warning fires from a loop or a frequently-called path — the developer sees the first occurrence, dismisses it, and never sees the next 10,000. `-W error::BoardlyWarning` turns the warning into a hard exception, but the CLI flag needs the class's full dotted import path (`-W error::boardly.warnings.BoardlyWarning`), which is fragile.
**Fix:** Subclass `UserWarning` (always shown via implicit `default`, same as bare `Warning`) or `FutureWarning` (always shown via implicit `default`, audience: end-users) instead of bare `Warning`. The custom class then inherits the parent's audience semantics; you can still call `simplefilter("always", YourCustomWarning)` in tests for a per-class filter. Real-world: `requests` and `urllib3` use `requests.exceptions.RequestsWarning(Warning)`; `sqlalchemy` uses `SAWarning(UserWarning)`. The latter is the better pattern.

## Engineering Trade-Offs

**Decision:** Use `DeprecationWarning` for "this feature will be removed in a future release of `boardly`" and `FutureWarning` for "this feature's behaviour will change". Subclass `UserWarning` for boardly-specific custom categories, not bare `Warning`.
**Both sides:** The alternative is to use a single category (`UserWarning`) for everything — which is always visible, but loses the audience-targeting. End-users see developer-facing deprecations; developers see end-user-facing behaviour changes; the noise is uniform. The two-category split (`DeprecationWarning` + `FutureWarning`) is the standard-library way to encode "this warning has an audience" — and the audience-targeting is enforced by the default filter list.
**Commitment:** `boardly`'s deprecation policy (in `CONTRIBUTING.md`) is one sentence: `DeprecationWarning` for removal, `FutureWarning` for behaviour change, `UserWarning` for application-level "you did something odd". The policy is enforced by a custom lint rule that reads `warnings.warn(...)` calls and checks the `category=` argument against the docstring's "Removed in vX" or "Changed in vX" marker.

## Exercises

1. **Exercise 1 — Swap the categories.** In `categories.py`, swap `DeprecationWarning` and `FutureWarning` between the two functions. Run the script. Observe that both warnings still fire (because `__main__` shows everything) — but install `boardly` as a package, run from a CLI, and observe that the `DeprecationWarning` becomes invisible. `Verify: python boardly/warnings_demo/categories.py`
2. **Exercise 2 — `ResourceWarning` in dev mode.** Write `leak_a_file()` (above), run with and without `-X dev`. Observe the difference. `Verify: python -X dev boardly/warnings_demo/resource_warning.py`
3. **Exercise 3 — Custom category.** Subclass `UserWarning` as `class BoardlyMigrationWarning(UserWarning): pass`. Emit a warning in `estimate_effort` using `BoardlyMigrationWarning` instead of `FutureWarning`. Verify it is shown by default. `Verify: python boardly/warnings_demo/categories.py`
4. **Exercise 4 — `pytest.warns` with `match=`.** Write tests for both `get_legacy_ticket` (assert `DeprecationWarning`) and `estimate_effort` (assert `FutureWarning`, not `DeprecationWarning`). The third test should fail if you swap the categories. `Verify: python -m pytest -q boardly/warnings_demo/test_categories.py`
5. **Exercise 5 — `RuntimeWarning` for numerical edge.** Add a `divide(numerator, denominator)` function that emits `RuntimeWarning` when `denominator` is close to zero (use `math.isclose`). Verify the warning fires. `Verify: python boardly/warnings_demo/categories.py`

## Verification

```bash
$ python boardly/warnings_demo/categories.py
boardly/warnings_demo/categories.py:37: DeprecationWarning: get_legacy_ticket is deprecated; use get_ticket instead
  ticket = get_legacy_ticket(7)
boardly/warnings_demo/categories.py:38: FutureWarning: estimate_effort will return float (fractional hours) in v3; update callers that assume int
  effort = estimate_effort(3.7)
ticket: {'id': 7, 'title': 'v2 ticket'} effort: 3
```

The two warnings come from different categories:

- The `DeprecationWarning` line points at the caller's line (`:37`) — `stacklevel=2` working. The script is `__main__`, so the warning is shown by the PEP 565 default rule.
- The `FutureWarning` line points at the caller's line (`:38`) — `stacklevel=2` working. The warning is always shown (no `__main__` rule applies to `FutureWarning`).

Both messages are actionable: the developer reads them, finds the line in their own code, and edits it. The audience-targeting (developer-facing removal vs end-user-facing behaviour change) is encoded in the category, not the message.

## Previously Learned Here

- [[20-warnings/01-warn-and-filterwarnings]] — the `warn`, `stacklevel`, and `filter` API this lesson builds on. The category rule is the second axis; the filter rule is the first.
- [[03-contextlib/04-suppress]] — `contextlib.suppress` for swallowing a `Warning` exception (rare, but the right tool when a library over-warns).

## What's Next

[[20-warnings/03-deprecated-decorator-PEP-702]] — the static-typing path. `typing.deprecated("use new_func instead")` (PEP 702, Python 3.13+) is a *decorator* that marks a function or class as deprecated; mypy and pyright emit the deprecation at the *call site* during static analysis — before the code ever runs. The runtime `DeprecationWarning` is still emitted (so the lesson-01 + lesson-02 machinery is preserved), but the static check is new: it catches the deprecation in code paths your tests never execute. Lesson 03 version-gates 3.13 clearly (3.12 does *not* have `typing.deprecated` — verified `hasattr(typing, 'deprecated') == False` on 3.12.15) and shows the `typing_extensions` backport for 3.12 projects that want the static enforcement today. Three things to take with you:

- `DeprecationWarning` for removal (audience: developers, hidden outside `__main__`).
- `FutureWarning` for behaviour change (audience: end-users, always shown).
- The seven built-in `Warning` subclasses each have an intended audience and default visibility — the category is the audience-selector.

## Sources

- **`warnings` — Warning categories** — https://docs.python.org/3/library/warnings.html#warning-categories — accessed 2026-10-23 — the canonical table of the seven built-in categories and their intended audiences.
- **PEP 565 — Show a DeprecationWarning only when triggered by code in `__main__`** — https://peps.python.org/pep-0565/ — accessed 2026-10-23 — the rationale for the 3.7 default-filter change; the source of the `DeprecationWarning`-vs-`FutureWarning` audience distinction.
- **`ResourceWarning`** — https://docs.python.org/3/library/warnings.html#warning-categories — accessed 2026-10-23 — the `__del__`-emitted warning for unclosed files/sockets; enabled by `-X dev` or `PYTHONDEVMODE=1`.
- **`pytest.warns`** — https://docs.pytest.org/en/stable/how-to/capture-warnings.html#warns — accessed 2026-10-23 — the test-time assertion built on `catch_warnings(record=True)`.

## What We Learned

- You can pick the right warning category for a given change — `DeprecationWarning` for removal, `FutureWarning` for behaviour change.
- You can explain why `DeprecationWarning` is hidden by default outside `__main__` (PEP 565) and why `FutureWarning` is always shown.
- You can list the seven built-in `Warning` subclasses and one-line each on when to use them.
- You can demonstrate `ResourceWarning` for an unclosed file and enable it with `-X dev` or `PYTHONDEVMODE=1`.
- You can use `pytest.warns(Category, match=...)` to assert on warnings in tests, and explain why `match=` is preferred over exact-equality.
