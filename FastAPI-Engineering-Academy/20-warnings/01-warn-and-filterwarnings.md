---
title: "Lesson 01: warn and filterwarnings"
aliases:
 - warnings.warn
 - stacklevel
 - filterwarnings
 - simplefilter
 - PYTHONWARNINGS
 - W flag
tags:
 - warnings
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[02-functools/02-wraps-and-Decorators]]"
 - "[[13-future/01-from-future-import-annotations]]"
related_lessons:
 - "[[20-warnings/02-DeprecationWarning-vs-FutureWarning]]"
 - "[[20-warnings/03-deprecated-decorator-PEP-702]]"
first_taught_in: "20-warnings/01-warn-and-filterwarnings"
---

# Lesson 01: `warn` and `filterwarnings`

*`warnings.warn(message, category=DeprecationWarning, stacklevel=2)` — the one line that ships in every library that deprecates anything. The `stacklevel=2` gotcha (default `1` points the warning at the `warn` call itself, not at the caller). The filter stack — `simplefilter`, `filterwarnings`, `catch_warnings(record=True)` for tests — and the `-W` / `PYTHONWARNINGS` escape hatches.*

**You're at the very beginning of Section 20.**

You have seen `DeprecationWarning` printed to a terminal a thousand times. You may not have noticed that on Python 3.7+ a `DeprecationWarning` is silent by default — unless it is raised from `__main__`, which is to say from the script you typed at the terminal and not from inside an installed package. That single fact is why every library author eventually reaches for `warnings.warn(..., stacklevel=2)` and why every CI pipeline eventually runs `python -W error::DeprecationWarning`. The `warnings` module is the standard-library machinery for telling your users "this will break in a future version" without breaking them now — and the `stacklevel` argument is the one parameter almost everyone gets wrong on the first try. Take your time. Type every example. **This is how you learn.**

#warnings #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `warnings.warn(message, category, stacklevel)`** with the correct `stacklevel` so the warning points at the caller, not at the `warn` line itself.
2. **Explain why `stacklevel=2` is almost always the value you want** — and predict what `stacklevel=1` (the default) and `stacklevel=3` (one extra wrapper) actually produce.
3. **Use `warnings.simplefilter` and `warnings.filterwarnings`** to silence, escalate, or once-only a category — and explain the action vocabulary (`error`, `ignore`, `always`, `default`, `module`, `once`).
4. **Use `warnings.catch_warnings(record=True)`** in tests to assert that a deprecation fires — without polluting the global filter state.
5. **Drive the warning machinery from outside the process** — the `-W` CLI flag and the `PYTHONWARNINGS` environment variable — for CI and ops.

## Prerequisites

Before starting, you need:

- **Decorators and `@wraps`** — [[02-functools/02-wraps-and-Decorators]]. The `stacklevel` discussion is about wrapped functions; `@wraps` is the precondition for `inspect` to still find the caller.
- **`from __future__ import annotations`** — [[13-future/01-from-future-import-annotations]]. The `@deprecated` decorator (lesson 03) interacts with forward references; this lesson is the runtime foundation.
- **About 30–45 minutes of focused time.**

**The most common gap: `stacklevel=2` is not optional.**

Students write `warnings.warn("use new_func instead", DeprecationWarning)` and ship it. The warning fires, but the `filename:lineno` in the `RuntimeWarning` traceback points at the `warn` line inside the library — not at the caller's code. The library user reads the warning, opens their own source, and finds... nothing useful. They have to grep the installed library to find the file, which they cannot edit. `stacklevel=2` makes the warning point at the caller's line — the line they actually need to change. This single argument is the difference between "actionable" and "frustrating", and the default of `1` is almost never what you want.

## The Problem

`boardly` has shipped a v1 endpoint `get_legacy_ticket(ticket_id)` for a year. In v2 the canonical name is `get_ticket(ticket_id)`. You want to:

1. Keep `get_legacy_ticket` working — do not break the call sites that already use it.
2. Print a warning that tells the caller "this function is going away; switch to `get_ticket`".
3. Point the warning at the *caller's* code (so the developer reading the warning knows which line to fix), not at the line `warnings.warn(...)` lives on inside `boardly`.
4. Let CI turn the warning into a hard error (`-W error::DeprecationWarning`) so the migration cannot be forgotten.

You can do all four with one `warnings.warn(..., stacklevel=2)` call, one `simplefilter("default")` baseline, and one `-W` flag in the CI step. The first attempt — without `stacklevel` — produces a warning that points at itself; the second attempt — with `stacklevel=2` — points at the caller. The difference is one integer and it is the difference between "this library is unusable" and "this library is helpful".

## The Code

```python
# boardly/warnings_demo/warn_and_filter.py
"""Demonstrate warn() and the filter stack — the boardly deprecation path."""
from __future__ import annotations

import warnings


def get_ticket(ticket_id: int) -> dict:
    """v2 canonical API."""
    return {"id": ticket_id, "title": "v2 ticket"}


def get_legacy_ticket(ticket_id: int) -> dict:
    """v1 name; kept for backward compat; emits a DeprecationWarning."""
    warnings.warn(
        "get_legacy_ticket is deprecated; use get_ticket instead",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return get_ticket(ticket_id)


def main() -> None:
    print("--- calling the deprecated function ---")
    result = get_legacy_ticket(42)
    print("result:", result)


if __name__ == "__main__":
    # Turn DeprecationWarnings into hard errors so CI fails loudly.
    warnings.simplefilter("error", DeprecationWarning)
    try:
        main()
    except DeprecationWarning as exc:
        print("CAUGHT:", exc)
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports and the future statement

```python
# boardly/warnings_demo/warn_and_filter.py
"""Demonstrate warn() and the filter stack — the boardly deprecation path."""
from __future__ import annotations

import warnings
```

`from __future__ import annotations` stringifies annotations in this module — it is the prerequisite for the PEP 702 `@deprecated` decorator (lesson 03) to interact cleanly with forward references. The `import warnings` line pulls in the standard-library `warnings` module, which is registered as a builtin singleton: every `warnings.warn` call in the process shares the same filter list. The filter list is mutated in place by `simplefilter` and `filterwarnings` — there is no per-module isolation unless you use `catch_warnings` (which we will, in tests).

**Why does `import warnings` not need a `from warnings import warn` form?**

Because `warnings.warn` mutates module-level state — the filter list and the `warnings.onceregistry`. The dotted form `warnings.warn` makes it visually obvious that you are touching shared global state; the bare `warn` form would hide it. Library style guides (PEP 8 itself is silent on this) generally prefer the dotted form for `warnings`, `logging`, and `os.environ` — three modules whose calls mutate process-wide state. The convention is a code-review signal: a reviewer reading `warnings.simplefilter(...)` immediately knows the call is global.

### Lines 9–12: The v2 canonical API

```python
def get_ticket(ticket_id: int) -> dict:
    """v2 canonical API."""
    return {"id": ticket_id, "title": "v2 ticket"}
```

`get_ticket` is the name `boardly` wants everyone to use. It takes a `ticket_id`, returns a `dict`, and has no warning machinery. The deprecation lesson is entirely about *the wrapper around it* — `get_legacy_ticket` — and the `stacklevel` argument in that wrapper.

**Why a `dict` and not a `dataclass`?**

To keep this lesson's code block focused on the `warnings` API. The boardly codebase itself uses `@dataclass` models (see [[06-dataclasses/01-dataclass-Basics]]); here, the `dict` is a placeholder so the line-by-line deep dive stays on `warn` and `stacklevel`. You would replace the body with `return Ticket(id=ticket_id, title="v2 ticket")` in the real project.

### Lines 15–22: The deprecated wrapper and `stacklevel=2`

```python
def get_legacy_ticket(ticket_id: int) -> dict:
    """v1 name; kept for backward compat; emits a DeprecationWarning."""
    warnings.warn(
        "get_legacy_ticket is deprecated; use get_ticket instead",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return get_ticket(ticket_id)
```

`warnings.warn(message, category=DeprecationWarning, stacklevel=2)` is the call. The three arguments:

- `message` — a `str` (or a `Warning` subclass instance; the str form is more common).
- `category` — a `Warning` subclass. `DeprecationWarning` is the right category here: the function is being removed in a future release of this package. (Lesson 02 walks the full category vocabulary — `DeprecationWarning` vs `FutureWarning` vs `PendingDeprecationWarning`.)
- `stacklevel=2` — the integer that controls which frame in the call stack the warning points at. `stacklevel=1` (the default) points at the `warn()` call itself — the line you are reading now. `stacklevel=2` points at the *caller* of `get_legacy_ticket` — i.e. the line `result = get_legacy_ticket(42)` in `main`. `stacklevel=3` would point at the caller of the caller — used when the wrapper is itself wrapped by another helper.

Internally, `warn()` calls `sys._getframe(stacklevel)` to grab the frame at that depth, then reads `frame.f_code.co_filename` and `frame.f_lineno` to build the `filename:lineno` shown in the warning. With `stacklevel=2`, the frame is `main`'s — the developer's code. With `stacklevel=1`, the frame is `get_legacy_ticket`'s — the library's code, which the developer cannot edit.

**Why is `stacklevel=2` not the default?**

Because `warnings.warn` was designed (CPython 2.1) to be called both from inside library functions *and* directly at the top of a script. The default `stacklevel=1` is correct for the "I am the script, warn about me" use case — the script's own line is what should be reported. The "I am a library, warn about my caller" case is more common in modern library code, but it was not the only case in 2001. The default is conservative — it never over-reports — and the cost is that every library author has to remember to write `stacklevel=2`. The PyPI download counts for libraries that forgot `stacklevel=2` are large; this lesson exists to make sure `boardly` is not one of them.

**Why `category=DeprecationWarning` rather than the default `UserWarning`?**

Because the `warnings` filter stack treats `DeprecationWarning` specially. By default on Python 3.7+, `DeprecationWarning` is *ignored* except when raised from `__main__` (the script you typed). The reasoning (PEP 565) is that end-users running a script see deprecations from their own code — useful — but should not see the firehose of deprecations from every installed third-party library they happen to transitively depend on. `UserWarning` (the default) is always shown. `FutureWarning` (lesson 02) is always shown. The choice of category is therefore a choice of audience: `DeprecationWarning` is for *developers of this code*; `FutureWarning` is for *users of this library*.

### Lines 24–28: The `main` caller

```python
def main() -> None:
    print("--- calling the deprecated function ---")
    result = get_legacy_ticket(42)
    print("result:", result)
```

`main()` is the caller. Line `result = get_legacy_ticket(42)` is the line the `stacklevel=2` warning will point at — when you run this script, the warning's `filename:lineno` will be `warn_and_filter.py:26` (the `result = ...` line), not `warn_and_filter.py:18` (the `warnings.warn(...)` line). That is the whole point of `stacklevel=2`.

**Why put the call in a `main()` instead of at module top level?**

So the call has a real caller frame. If you wrote `get_legacy_ticket(42)` at module top level, the warning would point at the top-level line — which is correct, but it obscures the stacklevel mechanism. Wrapping the call in `main()` makes the "caller vs callee" distinction concrete: `main` is frame 1, `get_legacy_ticket` is frame 2 (relative to the `warn` call), so `stacklevel=2` selects `main`'s frame.

### Lines 30–36: Turning the warning into a hard error

```python
if __name__ == "__main__":
    # Turn DeprecationWarnings into hard errors so CI fails loudly.
    warnings.simplefilter("error", DeprecationWarning)
    try:
        main()
    except DeprecationWarning as exc:
        print("CAUGHT:", exc)
```

`warnings.simplefilter("error", DeprecationWarning)` prepends an `('error', None, DeprecationWarning, None, 0)` rule to the filter list. Any `DeprecationWarning` becomes a `DeprecationWarning` exception, raised at the `warn()` call site. Note that `PendingDeprecationWarning` and `FutureWarning` are NOT subclasses of `DeprecationWarning` — they are sibling direct subclasses of `Warning` — so this rule does *not* affect them. To turn those into errors too, install separate rules: `simplefilter("error", PendingDeprecationWarning)` and `simplefilter("error", FutureWarning)`. Both `simplefilter` and `filterwarnings` *prepend* to the existing filter list (with dedup against exactly-matching rules); the difference is specificity — `simplefilter(action, category, lineno, append)` matches all messages and modules for the category, while `filterwarnings(action, message, category, module, lineno, append)` accepts regex patterns for `message` and `module`. For CI you almost always want `simplefilter("error", ...)` — the prepended rule wins for its category, and the existing default filters (PEP 565's `__main__`-only `DeprecationWarning` rule, the hidden `ResourceWarning` rule) stay in place.

**Why catch the `DeprecationWarning` rather than let it crash the script?**

For the demo — so the script prints a clean `CAUGHT: ...` line and exits `0`. In real CI you would *not* catch it; you would let the test runner report the failure, the build go red, and the developer fix the call site. The catch here is for the lesson's execution trace; in production `boardly` tests, the `pytest.warns` context manager (lesson 02) is the standard pattern instead.

**Why `simplefilter` and not `filterwarnings("error", category=DeprecationWarning)`?**

For this lesson's CI gate, the two are interchangeable — both prepend an `error` rule for `DeprecationWarning` and the warning is raised. The real difference is specificity: `simplefilter(action, category, lineno, append)` cannot filter on the message text or the module name; `filterwarnings(action, message, category, module, lineno, append)` accepts regex patterns for both. So `-W ignore::DeprecationWarning:sqlalchemy.*` (silence a noisy third-party's deprecations by module regex) requires `filterwarnings`, not `simplefilter`. Use `simplefilter` for "this category raises" / "this category is silent" gates that don't care about message or module; use `filterwarnings` when you need to target a specific message or a specific module. The two share the same prepend-with-dedup semantics — neither replaces the list.

### The filter stack — what the actions mean

`simplefilter` and `filterwarnings` accept one of six action strings:

| Action | Behaviour |
|---|---|
| `error` | Convert the warning to an exception (raised at the `warn` call). |
| `ignore` | Never print the warning; never raise. |
| `always` | Always print the warning (even if it has been printed before). |
| `default` | Print the first occurrence at each (filename, lineno, category) combination. |
| `module` | Print the first occurrence at each (module, lineno, category) combination. |
| `once` | Print the first occurrence at each (message, category) combination — across the whole process. |

The default filter list on Python 3.7+ is (verified by printing `warnings.filters` on 3.12.15):

```python
[('default', None, <class 'DeprecationWarning'>, '__main__', 0),
 ('ignore',  None, <class 'DeprecationWarning'>, None, 0),
 ('ignore',  None, <class 'PendingDeprecationWarning'>, None, 0),
 ('ignore',  None, <class 'ImportWarning'>, None, 0),
 ('ignore',  None, <class 'ResourceWarning'>, None, 0)]
```

The first rule — `('default', ..., DeprecationWarning, '__main__', 0)` — is the PEP 565 rule: `DeprecationWarning` is *shown* (action `default`) when it comes from a module named `__main__` (the script you typed at the terminal). The second rule — `('ignore', ..., DeprecationWarning, None, 0)` — hides `DeprecationWarning` from any other module. The combination is the "show your own deprecations, hide your dependencies' deprecations" behaviour.

**Why `default` and not `always` as the baseline action?**

Because `always` would print the warning every single call — at high call counts (a `DeprecationWarning` inside a `for` loop with 10,000 iterations) the terminal would be unusable. `default` prints the first occurrence at each `(filename, lineno, category)` — so a loop prints the warning once, not 10,000 times. The `default` action is the right baseline for almost every case; `always` is for debugging when you suspect `default` is hiding occurrences you wanted to see.

### `catch_warnings(record=True)` — the test-time pattern

The `warnings.catch_warnings(record=True)` context manager is how you assert on warnings in tests without polluting the global filter state:

```python
import warnings

def test_get_legacy_ticket_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")  # override inside the context
        from boardly.warnings_demo.warn_and_filter import get_legacy_ticket
        get_legacy_ticket(42)

    assert len(caught) == 1
    assert issubclass(caught[0].category, DeprecationWarning)
    assert "get_legacy_ticket is deprecated" in str(caught[0].message)
```

`catch_warnings(record=True)` does two things: it snapshots the current filter list on entry and restores it on exit (so the test's `simplefilter("always")` does not leak), and it replaces the `showwarning` function with one that appends each warning to the `caught` list (a `list[warnings.WarningMessage]`) instead of printing to stderr. The `WarningMessage` has `.category`, `.message`, `.filename`, `.lineno` attributes. pytest's `pytest.warns(DeprecationWarning, match="...")` is a thin wrapper around this; the underlying mechanism is `catch_warnings`.

**Why snapshot-and-restore rather than a per-module filter?**

Because the warnings machinery is global — there is one filter list per process, no per-module isolation. A test that calls `simplefilter("error")` and forgets to restore it would turn *every* subsequent test's deprecation into an error. The snapshot-and-restore pattern is the only safe way to mutate filters in a test. `catch_warnings` does this for you; you should never call `simplefilter` or `filterwarnings` outside a `catch_warnings` block in tests.

### The `-W` flag and `PYTHONWARNINGS` — out-of-process control

The same six actions are available from the command line and the environment, with no code change:

```bash
# Turn DeprecationWarnings into exceptions — the CI pattern.
python -W error::DeprecationWarning boardly/warnings_demo/warn_and_filter.py

# Print every warning (the "show me everything" debugging pattern).
python -W always boardly/warnings_demo/warn_and_filter.py

# Silence a noisy third-party library by module regex.
python -W ignore::DeprecationWarning:sqlalchemy.* boardly/app.py

# Same, via the environment (works for child processes — useful for pytest).
PYTHONWARNINGS=error::DeprecationWarning pytest -q
```

The `-W` flag grammar is `action:message:category:module:lineno`. Any field can be empty (the trailing colons are optional). `PYTHONWARNINGS` accepts the same syntax (you can pass multiple `-W` flags by repeating `PYTHONWARNINGS` entries separated by commas on POSIX). The flag is parsed at interpreter startup *before* your code runs — so it can override filters that `boardly` itself installs.

**Why use `-W error::DeprecationWarning` in CI rather than asserting in tests?**

Two reasons. First, the `-W` flag catches deprecations in code paths your tests do not cover — the import of a third-party package that triggers a `DeprecationWarning` at module load, before any test runs. Second, the flag turns the warning into a *raised exception* with a real traceback — the developer sees the exact `filename:lineno` (the caller's, if `stacklevel=2` was used) and the migration message. `pytest.warns(...)` only checks the warnings you predicted; `-W error::DeprecationWarning` catches the ones you did not.

**Why prefer `PYTHONWARNINGS` over `-W` for pytest?**

Because pytest spawns child processes (for `pytest-xdist` parallel runs) and re-imports your package in each. The `-W` flag is parsed by the parent `python` process; child processes inherit `PYTHONWARNINGS` from the environment but not the parent's `-W` flag. For consistent behaviour across the parent and the children, `PYTHONWARNINGS` is the right lever. For a one-off `python script.py`, `-W` is fine.

## Execution Trace

```bash
$ python boardly/warnings_demo/warn_and_filter.py
--- calling the deprecated function ---
CAUGHT: get_legacy_ticket is deprecated; use get_ticket instead
```

The script:

1. Runs `warnings.simplefilter("error", DeprecationWarning)` — every `DeprecationWarning` from now on is raised as an exception.
2. Calls `main()`.
3. `main` calls `get_legacy_ticket(42)`.
4. `get_legacy_ticket` calls `warnings.warn(..., stacklevel=2)`. Because the filter says `error`, `warn` *raises* a `DeprecationWarning` instead of printing it.
5. The exception's traceback points at `warn_and_filter.py:26` — the `result = get_legacy_ticket(42)` line in `main`, not the `warnings.warn(...)` line in `get_legacy_ticket`. `stacklevel=2` did its job.
6. The `except DeprecationWarning` clause in the `__main__` block catches the warning, prints `CAUGHT: ...`, and exits `0`.

Without the `simplefilter("error", ...)` line, the output would have been:

```bash
$ python boardly/warnings_demo/warn_and_filter.py
--- calling the deprecated function ---
boardly/warnings_demo/warn_and_filter.py:26: DeprecationWarning: get_legacy_ticket is deprecated; use get_ticket instead
  result = get_legacy_ticket(42)
result: {'id': 42, 'title': 'v2 ticket'}
```

The `boardly/warnings_demo/warn_and_filter.py:26:` prefix — `filename:lineno` — is the `stacklevel=2` evidence: the warning points at the caller's line, not the `warn()` line.

## Common Mistakes

### Mistake 1: Forgetting `stacklevel=2`

```python
def get_legacy_ticket(ticket_id: int) -> dict:
    warnings.warn("get_legacy_ticket is deprecated; use get_ticket instead",
                  category=DeprecationWarning)
    return get_ticket(ticket_id)
```

**Symptom:** The warning's `filename:lineno` points at the `warnings.warn(...)` line *inside the library* — i.e. at the line `warnings.warn(...)` itself. The developer reads the warning, opens the file the warning points at, and finds the `warn()` call — not their own code.
**Why:** The default `stacklevel=1` selects the *current* frame — the frame the `warn()` call is in. The warning therefore reports the `warn()` line's filename and lineno, not the caller's.
**Fix:** Pass `stacklevel=2`. The integer is "how many frames up from `warn` to look"; `2` selects the caller of the function that called `warn`.

### Mistake 2: Installing `ignore` *after* `error` and expecting `error` to win

```python
import warnings
warnings.filterwarnings("error", category=DeprecationWarning)  # prepends ('error', None, DeprecationWarning, None, 0)
warnings.filterwarnings("ignore", category=DeprecationWarning)  # prepends ('ignore', None, DeprecationWarning, None, 0)
# Later: warnings.warn("...", DeprecationWarning)  -> SILENT, not raised.
```

**Symptom:** A `DeprecationWarning` that you *expected* to raise (because you installed an `error` filter first) is silently ignored.
**Why:** Both `simplefilter` and `filterwarnings` *prepend* their new rule to the front of the filter list (with dedup against an exactly-matching existing rule). The first matching rule wins — and the most-recently-prepended rule sits at the front. So if you install `error` and then `ignore` (in that order), the `ignore` rule (prepended last) wins; the `error` rule (prepended first) is never reached. This is the opposite of what most engineers expect — many assume "first-installed wins" or "later overrides earlier"; neither is correct. The truth is "most-recently-prepended wins".
**Fix:** Install your `error` rule *last* in the sequence (so it prepends last and wins), or call `warnings.resetwarnings()` to clear the entire filter list before installing your gate. The two functions (`simplefilter`, `filterwarnings`) share the same prepend-with-dedup semantics — neither replaces the list.

### Mistake 3: Mutating filters outside `catch_warnings` in tests

```python
def test_warns():
    warnings.simplefilter("always")  # mutates the GLOBAL filter list
    get_legacy_ticket(42)
    # ... assert on captured stderr ...
```

**Symptom:** The test passes in isolation; the next test in the suite fails because `simplefilter("always")` leaked into the global state. Subsequent tests see warnings they should not see (or miss warnings they should see).
**Why:** `simplefilter` mutates the process-global filter list. Without a snapshot-and-restore, the change persists across tests.
**Fix:** Use `with warnings.catch_warnings(record=True) as caught:` — it snapshots on entry, restores on exit, and collects the warnings into `caught`.

## Engineering Trade-Offs

**Decision:** Use `warnings.warn(message, category=DeprecationWarning, stacklevel=2)` for every deprecation in `boardly`. Turn on `-W error::DeprecationWarning` (or `PYTHONWARNINGS=error::DeprecationWarning`) in CI.
**Both sides:** The alternative is to *raise* a `DeprecationWarning` exception directly (`raise DeprecationWarning(...)`) — which forces every caller to handle it now. That breaks the "deprecate first, remove later" contract; the entire point of the `warnings` machinery is to let callers *opt out* of the breakage via filters. The other alternative is to print a log line — which does not give the caller a `filename:lineno` they can act on and is not filterable.
**Commitment:** `boardly` uses `warnings.warn(..., stacklevel=2)` for every deprecation; the `stacklevel=2` rule is enforced by a custom linter in `pre-commit`. CI runs `PYTHONWARNINGS=error::DeprecationWarning` for the entire pytest suite. The combination catches deprecations the test author did not predict (a transitive import firing at load time) and gives the developer an actionable traceback.

## Exercises

1. **Exercise 1 — Drop `stacklevel=2`.** Change `stacklevel=2` to the default (delete the argument). Re-run the script. Observe that the warning's `filename:lineno` now points at the `warnings.warn(...)` line inside `get_legacy_ticket`, not at the caller. `Verify: python boardly/warnings_demo/warn_and_filter.py`
2. **Exercise 2 — Try `stacklevel=3`.** Change `stacklevel=2` to `stacklevel=3`. The warning now points at the *caller of `main`* — i.e. at the `if __name__ == "__main__":` block. Explain why. `Verify: python boardly/warnings_demo/warn_and_filter.py`
3. **Exercise 3 — `catch_warnings` in a test.** Write a `test_legacy_warns()` function that uses `with warnings.catch_warnings(record=True) as caught:` and asserts that exactly one `DeprecationWarning` is captured. `Verify: python -m pytest -q boardly/warnings_demo/test_warn.py`
4. **Exercise 4 — `-W always`.** Run `python -W always boardly/warnings_demo/warn_and_filter.py` and observe that the warning fires on *every* call (if you call `get_legacy_ticket` in a loop). `Verify: python -W always boardly/warnings_demo/warn_and_filter.py`
5. **Exercise 5 — `simplefilter("once")`.** Add a `simplefilter("once", DeprecationWarning)` and call `get_legacy_ticket` twice. Because the warning message is identical on both calls, the `once` action prints it the first time and silences the second call. Then change the message in the function body between the two calls — observe that *both* calls now print, because `once` deduplicates by `(message, category)` pair, so two different messages are two different "onces". `Verify: python boardly/warnings_demo/warn_and_filter.py`

## Verification

```bash
$ python boardly/warnings_demo/warn_and_filter.py
--- calling the deprecated function ---
CAUGHT: get_legacy_ticket is deprecated; use get_ticket instead
```

The `CAUGHT:` line proves three things:

- `warnings.warn(..., stacklevel=2)` fired (the message text matches).
- The `simplefilter("error", DeprecationWarning)` rule was installed before the call.
- The exception propagated up through `get_legacy_ticket` and `main` to the `except DeprecationWarning` clause — the warning was raised, not printed.

## Previously Learned Here

- [[02-functools/02-wraps-and-Decorators]] — `@wraps` is what keeps `inspect.signature` honest on a wrapper; `stacklevel=2` is what keeps the warning's `filename:lineno` honest on the same wrapper. The two are the "don't lie about location" pair.
- [[13-future/01-from-future-import-annotations]] — `from __future__ import annotations` is the migration-import for *interpreter* behaviour; `warnings.warn` is the runtime API for *library* behaviour. Lesson 03 combines them.

## What's Next

[[20-warnings/02-DeprecationWarning-vs-FutureWarning]] — the category rule. The `warnings.warn` call takes a `category=` argument; this lesson used `DeprecationWarning` without justifying why. Lesson 02 walks the full vocabulary — `DeprecationWarning` (for developers of this code; hidden by default since 3.7 unless raised from `__main__`), `FutureWarning` (for users of the library; always shown), `PendingDeprecationWarning` (the no-man's-land rarely useful), `ResourceWarning` (hidden; fires for unclosed files/sockets with `-X dev`), `SyntaxWarning`, `RuntimeWarning`, `UserWarning` (the default). The rule is: `DeprecationWarning` for "this feature will be removed"; `FutureWarning` for "this feature's behaviour will change". Three things to take with you:

- `stacklevel=2` is the value you want whenever you call `warn` inside a library function — it points the warning at the caller, not at the `warn()` line.
- `simplefilter` *replaces* the filter list; `filterwarnings` *prepends* to it. The two are not interchangeable.
- `catch_warnings(record=True)` is the only safe way to mutate filters in a test — it snapshots and restores the global state.

## Sources

- **`warnings` — Warning control** — https://docs.python.org/3/library/warnings.html — accessed 2026-10-23 — the canonical reference for `warn`, `filterwarnings`, `simplefilter`, `catch_warnings`, and the `-W` / `PYTHONWARNINGS` syntax.
- **PEP 565 — Show a DeprecationWarning only when triggered by code in `__main__`** — https://peps.python.org/pep-0565/ — accessed 2026-10-23 — the rationale for the 3.7 default-filter change that makes `DeprecationWarning` silent outside `__main__`.
- **CPython `warnings.py`** — https://github.com/python/cpython/blob/3.12/Lib/warnings.py — accessed 2026-10-23 — the implementation of `warn`, `filters`, and `catch_warnings`; the source for the "first matching rule wins" rule and the snapshot-and-restore behaviour.

## What We Learned

- You can call `warnings.warn(message, category=DeprecationWarning, stacklevel=2)` and explain why `stacklevel=2` is the value you want when calling from inside a library function.
- You can list the six filter actions (`error`, `ignore`, `always`, `default`, `module`, `once`) and explain the difference between `simplefilter` (replaces) and `filterwarnings` (prepends).
- You can use `warnings.catch_warnings(record=True)` to assert on warnings in tests without leaking filter state across tests.
- You can drive the filter stack from outside the process via `-W error::DeprecationWarning` (CLI) and `PYTHONWARNINGS=error::DeprecationWarning` (env) for CI.
- You can predict the `stacklevel=1` failure mode — the warning's `filename:lineno` points at the `warn()` line, not the caller's.
