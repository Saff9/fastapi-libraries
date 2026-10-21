---
title: "Lesson 06: redirect_stdout and redirect_stderr"
aliases:
 - contextlib.redirect_stdout
 - contextlib.redirect_stderr
 - redirect_stdout
 - redirect_stderr
tags:
 - contextlib
 - redirect-stdout
 - testing
 - context-managers
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[03-contextlib/01-contextmanager]]"
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
 - "[[03-contextlib/04-suppress]]"
related_lessons:
 - "[[03-contextlib/03-ExitStack-and-AsyncExitStack]]"
 - "[[03-contextlib/04-suppress]]"
 - "[[03-contextlib/07-contextmanager-decorator-internals]]"
---

# Lesson 06: `redirect_stdout` and `redirect_stderr`

*`with redirect_stdout(buf): print(...)` — capture stdout (or stderr) into a `StringIO`, run code that prints, read the buffer. The test-capture primitive, and the right way to do it instead of `unittest.mock.patch("sys.stdout", ...)`.*

**You're at the very beginning of Section 03.**

`contextlib.redirect_stdout` and `contextlib.redirect_stderr` are the two context managers you reach for in test code when a function you're testing prints to stdout or stderr and you need to assert on the output. They swap `sys.stdout` (or `sys.stderr`) for a target you pass in — typically an `io.StringIO` — for the duration of the `with` block, then restore the original on exit. The mechanism is simple (a `try`/`finally` around `sys.stdout = new_target`), but the composition patterns matter: the `ExitStack` combo for capturing both at once, the `SwallowErrors` helper that pairs capture with `suppress`, and the question of when this beats `unittest.mock.patch`. By the end of this lesson you will know the four canonical shapes and the one rule about `redirect_stdin`. Take your time. Type every example. **This is how you learn.**

#contextlib #redirect-stdout #testing

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply** `contextlib.redirect_stdout(new_target)` and `redirect_stderr(new_target)` to capture `print()` output and `sys.stderr.write()` output into an `io.StringIO`.
2. **Compose** multiple redirects with `ExitStack` to capture both stdout and stderr in one block, and to pair capture with `suppress` (the `SwallowErrors` pattern).
3. **Explain** the `try`/`finally` mechanism both redirects use — the swap-then-restore guarantees cleanup on exception.
4. **State** that `contextlib` does **not** provide `redirect_stdin`, and demonstrate the manual `sys.stdin = new_target` + `try`/`finally` workaround for stdin capture.
5. **Decide** between `contextlib.redirect_stdout` and `unittest.mock.patch("sys.stdout", new=...)` — and explain why `redirect_stdout` is safer for test code (it always restores, even if `__exit__` raises).

## Prerequisites

Before starting, you need:

- **[[03-contextlib/01-contextmanager]]** — the canonical context-manager lesson.
- **[[03-contextlib/03-ExitStack-and-AsyncExitStack]]** — the dynamic-resource manager; this lesson composes multiple redirects via `ExitStack`.
- **[[03-contextlib/04-suppress]]** — the `SwallowErrors` pattern pairs capture with `suppress`.
- **About 20–30 minutes of focused time.**

**The most common gap: reaching for `unittest.mock.patch("sys.stdout", ...)` when `redirect_stdout` is shorter and safer.**

`mock.patch` works, but it carries overhead — it patches the *attribute* on the `sys` module (which `mock.patch` does by importing `sys` and setting `sys.stdout`), and on Python 3.12 the `mock.patch` machinery can leave the original restored incorrectly if the patched object's `__exit__` itself raises. `redirect_stdout` is simpler — it is `sys.stdout = new_target` in `__enter__` and `sys.stdout = old_target` in a `try`/`finally` — and is the recommended tool for capture. Reach for `mock.patch` when you need to mock the *behavior* of a `print` call (e.g., assert it was called with specific arguments); reach for `redirect_stdout` when you only need to capture the bytes.

## The Problem

You ship `boardly/cli/list_tickets.py`. The CLI prints the list of tickets to stdout — that is the user-facing output, no JSON, no logging framework, just `print()`. You need a test:

```python
def test_list_tickets_prints_one_per_line():
    # How do I capture stdout?
    list_tickets_cli()  # prints to stdout
    # assert "ticket-1" in captured_stdout
```

Three options for capturing stdout, in increasing order of sophistication:

1. **Manual swap** — `old = sys.stdout; sys.stdout = io.StringIO(); ...; sys.stdout = old`. Works, but no `try`/`finally` — if `list_tickets_cli()` raises, stdout is left swapped.
2. **`unittest.mock.patch("sys.stdout", new=io.StringIO())`** — works, but adds the `mock` dependency, and the patched StringIO is accessed differently (`mock_stdout` is the *replacement*, not the captured value).
3. **`contextlib.redirect_stdout(io.StringIO())`** — works, no `mock` dependency, `try`/`finally` guarantees restore on exception, the StringIO is the captured value.

`redirect_stdout` is the right tool. The lesson walks the four shapes: simple, stderr, `ExitStack` combo, `SwallowErrors`.

## The Code

```python
# boardly/redirect_demo.py
"""redirect_stdout / redirect_stderr — capture stdout and stderr in tests."""
from __future__ import annotations

import contextlib
import io
import sys
from typing import Any


def list_tickets_cli() -> None:
    """Print tickets, one per line — the function under test."""
    for tid, title in TICKETS.items():
        print(f"  {tid}: {title}")


TICKETS: dict[int, str] = {1: "first", 2: "second"}


def warn_on_missing(ticket_id: int) -> None:
    """Print a warning to stderr if a ticket is missing."""
    if ticket_id not in TICKETS:
        sys.stderr.write(f"warning: ticket {ticket_id} not found\n")


# --- A composed context manager: capture stdout + stderr + swallow exceptions ---
class SwallowErrors:
    """Capture stdout and stderr AND swallow a specific exception, via ExitStack."""

    def __init__(self, *exc_types: type[BaseException]) -> None:
        self._exc_types = exc_types
        self._stack = contextlib.ExitStack()
        self.out = io.StringIO()
        self.err = io.StringIO()

    def __enter__(self) -> "SwallowErrors":
        s = self._stack
        s.enter_context(contextlib.redirect_stdout(self.out))
        s.enter_context(contextlib.redirect_stderr(self.err))
        s.enter_context(contextlib.suppress(*self._exc_types))
        return self

    def __exit__(self, *exc: Any) -> bool:
        return self._stack.__exit__(*exc)


def manual_stdin_capture(input_text: str, fn: Any) -> str:
    """Manually swap sys.stdin (contextlib has no redirect_stdin)."""
    new_stdin = io.StringIO(input_text)
    old_stdin = sys.stdin
    try:
        sys.stdin = new_stdin
        out_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf):
            fn()
        return out_buf.getvalue()
    finally:
        sys.stdin = old_stdin


if __name__ == "__main__":
    # 1. Simple redirect_stdout.
    print("--- redirect_stdout ---")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("hello captured")
        print("line two")
    print("captured:", repr(buf.getvalue()))

    # 2. redirect_stderr.
    print("\n--- redirect_stderr ---")
    err_buf = io.StringIO()
    with contextlib.redirect_stderr(err_buf):
        sys.stderr.write("error line\n")
    print("captured stderr:", repr(err_buf.getvalue()))

    # 3. ExitStack combo — both at once.
    print("\n--- ExitStack combo (both) ---")
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(contextlib.redirect_stdout(out_buf))
        stack.enter_context(contextlib.redirect_stderr(err_buf))
        list_tickets_cli()              # prints to stdout
        warn_on_missing(99)             # writes to stderr
    print("stdout:", repr(out_buf.getvalue()))
    print("stderr:", repr(err_buf.getvalue()))

    # 4. SwallowErrors — capture + suppress.
    print("\n--- SwallowErrors pattern ---")
    with SwallowErrors(ValueError) as se:
        print("stdout line")
        raise ValueError("swallowed")
    print("captured stdout:", repr(se.out.getvalue()))
    print("captured stderr:", repr(se.err.getvalue()))

    # 5. Manual stdin capture (contextlib has no redirect_stdin).
    print("\n--- manual stdin capture ---")
    def ask_and_print() -> None:
        name = input("name? ")
        print(f"hello, {name}")
    captured = manual_stdin_capture("alice\n", ask_and_print)
    print("manual capture:", repr(captured))
```

## Line-by-Line Deep Dive

### Lines 1–8: Module header and imports

```python
# boardly/redirect_demo.py
"""redirect_stdout / redirect_stderr — capture stdout and stderr in tests."""
from __future__ import annotations

import contextlib
import io
import sys
from typing import Any
```

We import `contextlib` (for `redirect_stdout`, `redirect_stderr`, `ExitStack`, `suppress`), `io` (for `StringIO`), and `sys` (for `sys.stdin` manual swap and `sys.stderr.write`). The `from __future__ import annotations` keeps the type annotations as strings — irrelevant to behaviour but consistent with the boardly codebase. `typing.Any` is used only in the `SwallowErrors.__exit__` signature.

**Why is `io.StringIO` the default target?**

Because it implements the file-like interface `print()` expects — `.write(str)`, `.flush()`, `.fileno()` (the last raises `io.UnsupportedOperation`, which `print` does not call unless you ask for `file=`). `StringIO` also accumulates the bytes written, exposed via `.getvalue()` — that is the captured output. Alternatives: `io.BytesIO` (for binary streams, requires `sys.stdout.buffer` redirection), a real file object (`open("/tmp/out", "w")` — useful for end-to-end tests), a custom class with a `.write` method (useful for streaming assertions). `StringIO` is the standard in-memory target.

### Lines 10–18: The CLI under test and the warning helper

```python
def list_tickets_cli() -> None:
    """Print tickets, one per line — the function under test."""
    for tid, title in TICKETS.items():
        print(f"  {tid}: {title}")


TICKETS: dict[int, str] = {1: "first", 2: "second"}


def warn_on_missing(ticket_id: int) -> None:
    """Print a warning to stderr if a ticket is missing."""
    if ticket_id not in TICKETS:
        sys.stderr.write(f"warning: ticket {ticket_id} not found\n")
```

`list_tickets_cli` uses `print()` — which writes to `sys.stdout` (the *current* `sys.stdout`, whatever that is). When `redirect_stdout(buf)` is active, `print()` writes to `buf`. When the redirect exits, `print()` writes to the original `sys.stdout` again. The function is *unaware* of the redirect — it just calls `print()`. That is the entire point: the function under test has no test-awareness; the test wraps it in a redirect.

`warn_on_missing` writes to `sys.stderr` directly (not via `print(..., file=sys.stderr)`) — to demonstrate that `redirect_stderr` catches both shapes. Any code path that ends in `sys.stderr.write(...)` is captured.

### Lines 21–37: The `SwallowErrors` composed context manager

```python
class SwallowErrors:
    """Capture stdout and stderr AND swallow a specific exception, via ExitStack."""

    def __init__(self, *exc_types: type[BaseException]) -> None:
        self._exc_types = exc_types
        self._stack = contextlib.ExitStack()
        self.out = io.StringIO()
        self.err = io.StringIO()

    def __enter__(self) -> "SwallowErrors":
        s = self._stack
        s.enter_context(contextlib.redirect_stdout(self.out))
        s.enter_context(contextlib.redirect_stderr(self.err))
        s.enter_context(contextlib.suppress(*self._exc_types))
        return self

    def __exit__(self, *exc: Any) -> bool:
        return self._stack.__exit__(*exc)
```

`SwallowErrors` composes three context managers via an `ExitStack`: `redirect_stdout`, `redirect_stderr`, and `suppress(*exc_types)`. The `__enter__` enters all three; the `__exit__` delegates to the `ExitStack`'s `__exit__`, which runs each registered manager's `__exit__` in LIFO order. The captured stdout/stderr are accessible via `.out.getvalue()` and `.err.getvalue()` after the block exits.

This is the canonical "compose captures and suppressions into one test harness" pattern — a frequent shape in test code, where you want to assert on stdout AND assert the function swallowed an expected exception. The `ExitStack` makes the composition atomic — if any `__enter__` raises, the prior ones are unwound via the stack's own cleanup; if the body raises, all three `__exit__`s run in reverse order.

**Why not just three nested `with` blocks?**

You can — `with redirect_stdout(out), redirect_stderr(err), suppress(ValueError):` is functionally equivalent. The `ExitStack` form wins when the set of managers is dynamic (computed at runtime from a list, say) or when you want the composed manager to be reusable (a class wrapping the stack). For a one-shot test, three nested `with`s is fine and more readable. For a reusable test helper, the `ExitStack` form is the right shape.

### Lines 40–52: Manual `sys.stdin` capture — `redirect_stdin` does not exist

```python
def manual_stdin_capture(input_text: str, fn: Any) -> str:
    """Manually swap sys.stdin (contextlib has no redirect_stdin)."""
    new_stdin = io.StringIO(input_text)
    old_stdin = sys.stdin
    try:
        sys.stdin = new_stdin
        out_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf):
            fn()
        return out_buf.getvalue()
    finally:
        sys.stdin = old_stdin
```

**Note — `contextlib.redirect_stdin` does not exist.**

A common surprise: `contextlib` provides `redirect_stdout` and `redirect_stderr` but *not* `redirect_stdin`. The asymmetry is by design — stdout and stderr are *sinks* (you write to them and capture the writes), while stdin is a *source* (you read from it, and reading is harder to capture cleanly because of buffering and blocking behaviour). CPython never added `redirect_stdin`; if you need to redirect stdin in a test, you swap `sys.stdin` manually in a `try`/`finally`.

The function above is the canonical workaround: build an `io.StringIO(input_text)`, save `sys.stdin`, swap it in, run the function (which calls `input()` or reads `sys.stdin`), restore `sys.stdin` in a `finally`. The `redirect_stdout` inside the same block captures any prompts `input()` prints. This pattern is what `unittest.mock.patch("sys.stdin", new=...)` does internally — `mock.patch` is the cleaner alternative if you already have `mock` imported.

**Why does `redirect_stdout` exist but `redirect_stdin` not?**

The CPython maintainers added `redirect_stdout` (3.4, [bpo-1](https://github.com/python/cpython/issues/1)-ish) to support the common test case of "a function prints, I want to assert on the print". The stdin case is rarer — most code that needs testable input takes it as a parameter (`def f(data): ...`) rather than reading from `sys.stdin`. The functions that *do* read from `sys.stdin` (CLI prompts, `input()`) are usually thin wrappers around a real function — and you test the real function with explicit input. `redirect_stdin` would have been marginal utility, and the maintainers chose to ship only the two output-capture managers.

### Lines 56–62: Simple `redirect_stdout`

```python
    # 1. Simple redirect_stdout.
    print("--- redirect_stdout ---")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("hello captured")
        print("line two")
    print("captured:", repr(buf.getvalue()))
```

The simplest shape. `buf = io.StringIO()` is the capture target. `with contextlib.redirect_stdout(buf):` swaps `sys.stdout` to `buf` for the block. The two `print()` calls write to `buf`. After the `with` exits, `print("captured:", repr(buf.getvalue()))` writes to the *real* stdout — and `buf.getvalue()` returns `'hello captured\nline two\n'`. This is the test-capture primitive in its smallest form.

**Why is the captured value accessed via `buf.getvalue()` and not via a return value of the `with`?**

Because the `with ... as x:` `x` is what `__enter__` *returns* — and `redirect_stdout.__enter__` returns the *new target* (i.e., `buf` itself), not the captured content. You access the captured content via `buf.getvalue()` after the block. This is consistent with how file objects work — you write to the file, then `.read()` or `.getvalue()` to retrieve. The pattern feels awkward at first ("why don't I just get the captured string out of the with?"), but it composes: you can swap any file-like object in, including a real file, a network socket wrapper, a custom logger — and the `with` block doesn't need to know which.

### Lines 64–70: `redirect_stderr` — same shape, different stream

```python
    # 2. redirect_stderr.
    print("\n--- redirect_stderr ---")
    err_buf = io.StringIO()
    with contextlib.redirect_stderr(err_buf):
        sys.stderr.write("error line\n")
    print("captured stderr:", repr(err_buf.getvalue()))
```

`redirect_stderr` is structurally identical to `redirect_stdout` — it swaps `sys.stderr` instead. The two are separate context managers because the two streams are separate (you might want to capture stdout but let stderr through, or vice versa). The composition of both at once is the `ExitStack` shape, walked next.

### Lines 72–82: `ExitStack` combo — both streams at once

```python
    # 3. ExitStack combo — both at once.
    print("\n--- ExitStack combo (both) ---")
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(contextlib.redirect_stdout(out_buf))
        stack.enter_context(contextlib.redirect_stderr(err_buf))
        list_tickets_cli()              # prints to stdout
        warn_on_missing(99)             # writes to stderr
    print("stdout:", repr(out_buf.getvalue()))
    print("stderr:", repr(err_buf.getvalue()))
```

The `ExitStack` lets you push multiple context managers dynamically. `enter_context(cm)` calls `cm.__enter__()` immediately and registers `cm.__exit__` to run on stack exit (LIFO order). When the `with ExitStack()` block exits, all registered `__exit__`s run in reverse order — `redirect_stderr.__exit__` first, then `redirect_stdout.__exit__`. The result: both streams are captured, both are restored. The body (`list_tickets_cli()` and `warn_on_missing(99)`) is unaware of the capture — it just writes to `sys.stdout` and `sys.stderr`.

**Why `ExitStack` and not a comma-separated `with A, B:`?**

Three reasons. (1) The set of captures is dynamic in some tests (you might conditionally add `suppress(TimeoutError)` based on a flag). (2) `ExitStack` is a context manager itself — you can return it from a `@contextmanager` generator or wrap it in a class (as `SwallowErrors` does below). (3) `with A, B:` runs `__enter__` in order A→B and `__exit__` in order B→A; if A's `__enter__` raises, B is never entered and cleanup is correct — but the comma form requires A and B to be known at authoring time. `ExitStack` allows them to be added at runtime.

### Lines 84–90: The `SwallowErrors` pattern in action

```python
    # 4. SwallowErrors — capture + suppress.
    print("\n--- SwallowErrors pattern ---")
    with SwallowErrors(ValueError) as se:
        print("stdout line")
        raise ValueError("swallowed")
    print("captured stdout:", repr(se.out.getvalue()))
    print("captured stderr:", repr(se.err.getvalue()))
```

The body prints `"stdout line"` to (redirected) stdout and raises `ValueError`. The `suppress(ValueError)` part of `SwallowErrors` swallows it. After the block, `se.out.getvalue()` returns `'stdout line\n'` — captured. `se.err.getvalue()` returns `''` — nothing was written to stderr. The composed manager did two things at once: capture and swallow. This is the test pattern for "the function prints AND raises an expected exception; I want to assert on the print and on the swallowed exception type".

**Why would I want to capture stdout AND swallow an exception?**

Common case: a function that logs a deprecation warning to stdout, then raises a `DeprecationWarning` that the test framework turns into an error. You want to assert the warning text was printed (the stdout capture) *and* not let the `DeprecationWarning` break the test (the suppress). Or: a CLI that prints usage to stdout when given `--help` and then calls `sys.exit(0)` (which raises `SystemExit`). You capture stdout to assert the usage text and suppress `SystemExit` to keep the test running. The `SwallowErrors` pattern is the tool for these cases.

### Lines 92–98: Manual stdin capture in action

```python
    # 5. Manual stdin capture (contextlib has no redirect_stdin).
    print("\n--- manual stdin capture ---")
    def ask_and_print() -> None:
        name = input("name? ")
        print(f"hello, {name}")
    captured = manual_stdin_capture("alice\n", ask_and_print)
    print("manual capture:", repr(captured))
```

`ask_and_print` calls `input()` — which reads from `sys.stdin` and writes the prompt to `sys.stdout`. `manual_stdin_capture` swaps in a `StringIO("alice\n")` for `sys.stdin` and redirects `sys.stdout` to another `StringIO`. The body runs, reads `"alice"`, prints `"hello, alice"`. After the block, the captured stdout (`'name? hello, alice\n'`) is returned. The `sys.stdin` swap is restored in a `finally`. This is the workaround for the missing `redirect_stdin`.

## Execution Trace

```bash
$ python boardly/redirect_demo.py
--- redirect_stdout ---
captured: 'hello captured\nline two\n'

--- redirect_stderr ---
captured stderr: 'error line\n'

--- ExitStack combo (both) ---
stdout: '  1: first\n  2: second\n'
stderr: 'warning: ticket 99 not found\n'

--- SwallowErrors pattern ---
captured stdout: 'stdout line\n'
captured stderr: ''

--- manual stdin capture ---
manual capture: 'name? hello, alice\n'
```

The five blocks each prove a property: simple stdout capture, stderr capture, the `ExitStack` composition (both streams in one block), the `SwallowErrors` pattern (capture + swallow), and the manual stdin swap (the workaround for the missing `redirect_stdin`).

## Common Mistakes

### Mistake 1: Forgetting to `.getvalue()` — printing the `StringIO` object

```python
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print("hello")
print("captured:", buf)   # ← prints the StringIO object, not the content
```

**Symptom:** The output shows `<_io.StringIO object at 0x...>` instead of `'hello\n'`.
**Why:** `io.StringIO` is a file-like object, not a string. Its repr is the object's address, not the content.
**Fix:**

```python
print("captured:", buf.getvalue())
```

`.getvalue()` returns the string accumulated in the buffer. (`.read()` also works, but only once — subsequent `.read()` returns `''` because the read pointer has advanced.)

### Mistake 2: Reading `sys.stdout` after the redirect exits — it's the original

```python
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print("inside")
print(sys.stdout.getvalue())  # ← AttributeError — sys.stdout is the real stdout
```

**Symptom:** `AttributeError: '_io.TextIOWrapper' object has no attribute 'getvalue'`.
**Why:** After the `with` block exits, `sys.stdout` is restored to the original (a `TextIOWrapper` around the OS file descriptor). The `buf` variable still holds the captured content; `sys.stdout` does not.
**Fix:**

```python
print(buf.getvalue())  # read the captured buffer, not sys.stdout
```

The captured content lives in the `StringIO` you passed to `redirect_stdout`. `sys.stdout` is the *current* stdout stream — only inside the `with` block does it point at `buf`.

### Mistake 3: Expecting `contextlib.redirect_stdin` to exist

```python
with contextlib.redirect_stdin(io.StringIO("input\n")):   # ← AttributeError
    x = input()
```

**Symptom:** `AttributeError: module 'contextlib' has no attribute 'redirect_stdin'`.
**Why:** `contextlib` does not provide `redirect_stdin`. The asymmetry is intentional — stdout and stderr are sinks, stdin is a source, and the capture patterns differ.
**Fix:** Swap `sys.stdin` manually in a `try`/`finally` (as `manual_stdin_capture` above does), or use `unittest.mock.patch("sys.stdin", new=io.StringIO("input\n"))` if `mock` is already imported.

## Engineering Trade-Offs

**Decision:** Use `contextlib.redirect_stdout` / `redirect_stderr` for capture in tests; reserve `unittest.mock.patch("sys.stdout", ...)` for cases where you need to assert on `print`'s call signature.
**Both sides:** `mock.patch` is more general — it patches any attribute on any object, supports autospec, supports `side_effect`. The cost is: it requires the `mock` dependency (one more import), the patched object's `__exit__` can leave things in a bad state if it raises, and the capture is one indirection deeper (you read `mock_stdout.getvalue()` where `mock_stdout` is the replacement object, which is the same as the captured buffer). `redirect_stdout` is narrower — it only swaps `sys.stdout` — and its `try`/`finally` is bulletproof. For pure capture (no behaviour assertion), `redirect_stdout` is the right tool.
**Commitment:** boardly uses `redirect_stdout` / `redirect_stderr` everywhere in the test suite. `mock.patch` is used only to patch the *behaviour* of dependencies (e.g., patching `requests.get` to return a fake response). For capture, `redirect_*` is the only allowed tool — and the `SwallowErrors` class is the composed helper for the "capture and swallow" case.

## Exercises

1. **Exercise 1 — Run the file.** Save the code above as `boardly/redirect_demo.py` and run it. Compare your output to the Execution Trace. `Verify: python boardly/redirect_demo.py`
2. **Exercise 2 — Capture `print(..., file=sys.stderr)`.** Modify `warn_on_missing` to use `print(f"warning: ticket {ticket_id} not found", file=sys.stderr)`. Confirm `redirect_stderr` still captures it (it should — both `print(file=sys.stderr)` and `sys.stderr.write(...)` end up at the same place). `Verify: python -c "from boardly.redirect_demo import warn_on_missing, TICKETS; import contextlib, io; \nbuf = io.StringIO(); \nwith contextlib.redirect_stderr(buf): warn_on_missing(99) \nprint('got:', repr(buf.getvalue()))"`
3. **Exercise 3 — `SwallowErrors` with `SystemExit`.** Call `sys.exit(0)` inside a `with SwallowErrors(SystemExit):` block. Confirm the block exits cleanly (no `SystemExit` raised) and that any stdout printed before the `sys.exit` is captured. This is the test pattern for "the CLI exits with status 0 after printing usage". `Verify: python -c "from boardly.redirect_demo import SwallowErrors; \nwith SwallowErrors(SystemExit) as se: \n  import sys; print('usage'); sys.exit(0) \nprint('survived, captured:', repr(se.out.getvalue()))"`
4. **Exercise 4 — Timeit-style benchmarking with capture.** Write a function that runs `list_tickets_cli()` 1000 times inside a `redirect_stdout(io.StringIO())` and measures the time. Confirm the captured buffer is 1000× the single-run output. `Verify: python -c "import time, contextlib, io; from boardly.redirect_demo import list_tickets_cli; \nbuf = io.StringIO(); t = time.perf_counter(); \nwith contextlib.redirect_stdout(buf): \n  for _ in range(1000): list_tickets_cli() \nprint('elapsed:', time.perf_counter() - t, 'lines:', buf.getvalue().count(chr(10)))"`
5. **Exercise 5 — Custom capture target.** Write a `CountingStream` class with `.write(s)` that counts characters and stores nothing. Use it as the target for `redirect_stdout`. Print 5 lines and assert the counter is the sum of their lengths (plus newlines). This generalises `redirect_stdout` beyond `StringIO` to any file-like target. `Verify: python -c "from boardly.redirect_demo import CountingStream; \nimport contextlib \ncs = CountingStream(); \nwith contextlib.redirect_stdout(cs): \n  print('hello'); print('world') \nprint('count:', cs.count)"`

## Verification

```bash
$ python boardly/redirect_demo.py
--- redirect_stdout ---
captured: 'hello captured\nline two\n'

--- redirect_stderr ---
captured stderr: 'error line\n'

--- ExitStack combo (both) ---
stdout: '  1: first\n  2: second\n'
stderr: 'warning: ticket 99 not found\n'

--- SwallowErrors pattern ---
captured stdout: 'stdout line\n'
captured stderr: ''

--- manual stdin capture ---
manual capture: 'name? hello, alice\n'
```

If the output matches, you have reproduced all five shapes: simple capture, stderr capture, the `ExitStack` combo, the `SwallowErrors` pattern, and the manual stdin swap.

## Previously Learned Here

- [[03-contextlib/01-contextmanager]] — the `with` protocol that `redirect_stdout` implements.
- [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — the `ExitStack` used to compose `redirect_stdout` + `redirect_stderr` + `suppress`. This lesson is the canonical use case for the dynamic stack.
- [[03-contextlib/04-suppress]] — `suppress` is the third piece of the `SwallowErrors` pattern.

## What's Next

[[03-contextlib/07-contextmanager-decorator-internals]] — the senior deep-dive on how `@contextmanager` actually works. You have used `redirect_stdout` (a class-based context manager) and `SwallowErrors` (a class wrapping an `ExitStack`). Lesson 07 walks the *generator*-based form: how `@contextmanager` turns a generator function into a `_GeneratorContextManager` instance, the one-yield rule (raise `RuntimeError` if the generator does not yield exactly once), and the exception-rethrow via `gen.throw()`. Three things to look for in lesson 07:

- The minimal reimplementation of `@contextmanager` — about 30 lines of Python.
- Why the body's exception is *thrown into* the generator at the `yield` point.
- The `_GeneratorContextManager` MRO and why `@contextmanager` instances also work as decorators (the `ContextDecorator` mixin).

Take your time. Type every example. **This is how you learn.**

## Sources

- **`contextlib.redirect_stdout`, `redirect_stderr` — CPython reference** — https://docs.python.org/3/library/contextlib.html#contextlib.redirect_stdout — accessed 2026-10-23 — the canonical API documentation. Note: `redirect_stdin` is *not* documented — it does not exist.
- **`io.StringIO` — CPython reference** — https://docs.python.org/3/library/io.html#io.StringIO — accessed 2026-10-23 — the in-memory text stream used as the capture target.
- **CPython source — `Lib/contextlib.py` (redirect_stdout)** — https://github.com/python/cpython/blob/3.12/Lib/contextlib.py — accessed 2026-10-23 — the implementation; a `_RedirectStream` class with `__enter__`/`__exit__` wrapping `sys.stdout`/`sys.stderr` swap in `try`/`finally`.
- **`unittest.mock.patch` — CPython reference** — https://docs.python.org/3/library/unittest.mock.html#unittest.mock.patch — accessed 2026-10-23 — the alternative tool; used when behaviour assertion is needed over pure capture.

## What We Learned

- `contextlib.redirect_stdout(new_target)` swaps `sys.stdout` for the duration of a `with` block; `redirect_stderr` does the same for `sys.stderr`. Both use `try`/`finally` to guarantee restoration on exception.
- `io.StringIO` is the default capture target; `.getvalue()` returns the accumulated string.
- `ExitStack` composes multiple redirects (and `suppress`) into one block — the dynamic-stack composition pattern from [[03-contextlib/03-ExitStack-and-AsyncExitStack]].
- The `SwallowErrors` class is the canonical "capture stdout + stderr + swallow a specific exception" test helper, built on `ExitStack`.
- `contextlib` does **not** provide `redirect_stdin` — the asymmetry is intentional (stdout/stderr are sinks, stdin is a source). The workaround is a manual `sys.stdin = ...` swap in a `try`/`finally`, or `unittest.mock.patch("sys.stdin", new=...)`.
- `contextlib.redirect_stdout` is preferred over `mock.patch("sys.stdout", ...)` for pure capture — narrower, faster, and the `try`/`finally` is bulletproof. `mock.patch` wins when you need behaviour assertion (e.g., assert `print` was called with specific arguments).
