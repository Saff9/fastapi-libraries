---
title: "Lesson 01: import_module and dotted-path imports"
aliases:
 - importlib.import_module
 - dynamic import
 - plugin loading
tags:
 - importlib
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
related_lessons:
 - "[[14-importlib/02-resources]]"
 - "[[14-importlib/03-metadata]]"
 - "[[14-importlib/04-reload]]"
first_taught_in: "14-importlib/01-import_module"
---

# Lesson 01: import_module and dotted-path imports

*How `boardly`'s plugin loader turns the string `"boardly.routers.projects"` into a live module object — the same call FastAPI's `lifespan` hook makes when it loads router modules from config.*

**You're at the very beginning of Section 14.**

You have written `import boardly.routers.projects` a hundred times. You have not yet asked what Python does when the module name is a *string* — when the dotted path comes from a config file, a CLI flag, or an HTTP header. That is the problem this lesson solves. `importlib.import_module` is the public, batteries-included way to import a module by name at runtime. By the end of the lesson you can load `boardly.routers.projects` from a config string and use it. Take your time. Type every example. **This is how you learn.**

#importlib #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `importlib.import_module`** — pass a dotted module name, get back the leaf module object, not the top-level package.
2. **Explain the difference from `__import__`** — `__import__("a.b")` returns `a`, `import_module("a.b")` returns `b`. Name the trade-off that made `import_module` the recommended API.
3. **Use the `package=` argument for relative imports** — `import_module(".routers.projects", package="boardly")` resolves the same way `from .routers import projects` does inside a module.
4. **Build a plugin loader** — read dotted paths from a config, import each one, validate that it exposes the expected interface, and skip the broken ones gracefully.

## Prerequisites

Before starting, you need:

- **Familiarity with the `import` statement** — `import a.b.c` and `from a.b import c` should be second nature. The mechanics (the importer protocol, the `sys.modules` cache) are not required reading, but if you want the deep dive, [[10-inspect/01-signature-and-Parameter]] shows you what `inspect.signature` does with a module you have imported.
- **About 25–35 minutes of focused time.**

**The most common gap: assuming `import "a.b"` works.** Python's `import` statement takes a syntactic name (`import a.b.c`), not a string. The moment the module name comes from outside the source — config, env var, CLI arg — the `import` statement cannot help you, because Python parses the `import` name at compile time. `importlib.import_module` is the runtime-callable form of `import`. Students who reach for `exec(f"import {name}")` are reinventing `import_module` badly.

## The Problem

Here is the bug. `boardly` ships with a router registry — a YAML file that lists the router modules to mount at startup:

```yaml
# boardly/config.yaml
routers:
  - boardly.routers.projects
  - boardly.routers.tickets
  - boardly.routers.users
  - boardly.routers.audit
```

The startup code reads the file, gets a list of strings, and now needs to turn each string into a *module object* so it can call `module.router` and mount it on the FastAPI app. The naive approach fails immediately:

```python
# boardly/loader.py — the broken approach
for name in config["routers"]:
    module = import name              # SyntaxError: Python can't parse a variable here
    app.include_router(module.router)
```

`import name` is a syntax error because `import` is a statement that takes a *dotted identifier*, not a variable. The next thing a student reaches for is `exec`:

```python
# boardly/loader.py — the scary approach
for name in config["routers"]:
    exec(f"import {name}")            # works, but...
    module = ...                      # how do you get the module object back?
    app.include_router(module.router)
```

`exec(f"import {name}")` runs the import, but the resulting module object is now bound in the `exec`'s namespace, not in your local scope. You can dig it out of `sys.modules[name]`, but you have just reinvented `import_module` with worse error handling, no relative-import support, and a code-injection hole if `name` ever comes from an untrusted source. `importlib.import_module` solves all three of those problems in one call.

## The Code

```python
# boardly/plugins/loader.py
"""Load router modules by dotted name from a config list."""
from __future__ import annotations
import importlib
from dataclasses import dataclass


@dataclass
class LoadedRouter:
    name: str
    router: object


def load_router(dotted_name: str) -> LoadedRouter:
    """Import a dotted module name and pull its `.router` attribute."""
    module = importlib.import_module(dotted_name)
    if not hasattr(module, "router"):
        raise AttributeError(
            f"module {dotted_name!r} has no `router` attribute; "
            f"did you forget to define `router = APIRouter()`?"
        )
    return LoadedRouter(name=dotted_name, router=module.router)


def load_routers(names: list[str]) -> list[LoadedRouter]:
    """Import every router; skip broken ones with a warning."""
    loaded: list[LoadedRouter] = []
    for name in names:
        try:
            loaded.append(load_router(name))
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip router {name!r}: {exc}")
    return loaded


if __name__ == "__main__":
    import sys
    # Simulate a config-driven loader. For the demo we use stdlib modules
    # that expose a `version` attribute as a stand-in for a `router`.
    candidates = ["importlib.metadata", "importlib.resources", "no.such.module"]
    print(f"Loading {len(candidates)} plugin candidates...\n")
    for cand in candidates:
        try:
            mod = importlib.import_module(cand)
            print(f"  ok   {cand} -> {mod.__name__} (file={getattr(mod, '__file__', '(built-in)')})")
        except ImportError as exc:
            print(f"  FAIL {cand} -> {exc}")
    print()

    # The package= argument for relative imports.
    # Resolves ".metadata" against the package "importlib".
    relative = importlib.import_module(".metadata", package="importlib")
    print("import_module('.metadata', package='importlib'):")
    print(f"  -> {relative.__name__}")
    print(f"  is importlib.metadata? {relative is importlib.metadata}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 4–9: Imports and the `LoadedRouter` dataclass

```python
import importlib
from dataclasses import dataclass


@dataclass
class LoadedRouter:
    name: str
    router: object
```

`importlib` is a top-level stdlib package; `importlib.import_module` lives directly on it, no submodule import needed. The `LoadedRouter` dataclass is the return contract: a value object that pairs the dotted name (for logging and error messages) with the live router object (the `APIRouter()` instance the module exposes). We use a dataclass instead of returning the bare `router` because the loader's caller — the FastAPI startup hook — wants both the router *and* its source name, so it can emit "mounted boardly.routers.projects" log lines without re-parsing the config.

`router: object` is deliberately loose. `APIRouter` lives in `fastapi`, and `boardly.plugins.loader` should not depend on `fastapi` just to type a return value. We trade a precise return type for a clean dependency boundary; the actual `APIRouter` instance is what comes back at runtime, and any type checker worth its salt will narrow it the moment the caller calls `module.router.get/routes/...`.

### Lines 12–22: `load_router` — the single import

```python
def load_router(dotted_name: str) -> LoadedRouter:
    """Import a dotted module name and pull its `.router` attribute."""
    module = importlib.import_module(dotted_name)
    if not hasattr(module, "router"):
        raise AttributeError(
            f"module {dotted_name!r} has no `router` attribute; "
            f"did you forget to define `router = APIRouter()`?"
        )
    return LoadedRouter(name=dotted_name, router=module.router)
```

`importlib.import_module(dotted_name)` is the whole story. Given `"boardly.routers.projects"`, Python walks its import machinery: looks up `boardly` in `sys.modules`, then `boardly.routers`, then `boardly.routers.projects`. If any segment is missing, you get `ModuleNotFoundError`. If every segment is already in `sys.modules` (which it almost always is for a warm process), the call is essentially a dictionary lookup — the import machinery does not re-execute the module's code.

The return value is the *leaf* module — `boardly.routers.projects`, not `boardly`. That is the single most important semantic difference between `import_module` and the lower-level `__import__` builtin, and we will dig into it in the trade-offs section.

The `hasattr(module, "router")` guard is the contract check: every boardly router module must expose a top-level `router = APIRouter()` symbol. The error message is deliberately specific — "did you forget to define `router = APIRouter()`?" — because the most common cause of this `AttributeError` is a router file where someone wrote `app.include_router(...)` inline instead of exporting the `APIRouter` instance. A precise error message saves the next developer ten minutes of grep.

**Why `hasattr` instead of `try: module.router / except AttributeError:`?** Both work; the difference is *intent*. `hasattr` reads as "check the contract"; the `try` form reads as "do the work and recover." For a one-time startup-time check, the readability of `hasattr` wins. Inside a hot loop or for an attribute that might raise on access (a property, a `__getattr__` side effect), `try/except` is the safer choice because it avoids the double-lookup.

### Lines 25–33: `load_routers` — the batch import with failure isolation

```python
def load_routers(names: list[str]) -> list[LoadedRouter]:
    loaded: list[LoadedRouter] = []
    for name in names:
        try:
            loaded.append(load_router(name))
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip router {name!r}: {exc}")
    return loaded
```

A plugin loader that hard-crashes on the first broken plugin is a plugin loader nobody trusts. The production version of this function catches `ImportError` (the plugin module is missing or has a bad import of its own) and `AttributeError` (the plugin exists but does not expose `router`), logs the failure, and keeps going. The `print` is a stand-in for the real logger; the lesson on `logging` ([[23-logging/00-logging-MOC]]) replaces it with `logger.warning("skip router %s: %s", name, exc)`.

The exception pair is *narrow*. A `SyntaxError` from a broken plugin file is an `ImportError` subclass on Python 3.12 (it surfaces inside `ModuleNotFoundError`'s chain), but if the plugin's `router = APIRouter()` line raises a *runtime* exception (e.g., a bad decorator), that propagates as `Exception` and crashes the loader — which is the correct behaviour, because a router that fails to construct is not a "skip and continue" condition, it is a "halt the startup" condition.

### Lines 36–48: The demo driver — `import_module` with the `package=` argument

```python
if __name__ == "__main__":
    import sys
    candidates = ["importlib.metadata", "importlib.resources", "no.such.module"]
    print(f"Loading {len(candidates)} plugin candidates...\n")
    for cand in candidates:
        try:
            mod = importlib.import_module(cand)
            print(f"  ok   {cand} -> {mod.__name__} (file={getattr(mod, '__file__', '(built-in)')})")
        except ImportError as exc:
            print(f"  FAIL {cand} -> {exc}")
    print()

    relative = importlib.import_module(".metadata", package="importlib")
    print("import_module('.metadata', package='importlib'):")
    print(f"  -> {relative.__name__}")
    print(f"  is importlib.metadata? {relative is importlib.metadata}")
```

The demo uses three stdlib module names instead of real `boardly.routers.*` modules — that keeps the lesson runnable without a FastAPI install. The third candidate, `"no.such.module"`, exercises the `ImportError` path so you can see the loader fail soft.

The last block is the second important API of this lesson: the `package=` argument. `importlib.import_module(".metadata", package="importlib")` is the runtime equivalent of `from . import metadata` *when called from inside the `importlib` package*. The leading dot says "relative import"; the `package=` argument says "resolve the dot against this package." Without `package=`, a name starting with `.` raises `TypeError: the 'package' argument is required to perform a relative import for '.'`.

**Why does `import_module` need a separate `package` argument instead of just resolving the relative name against `__package__`?** Because `import_module` is a *function*, not a statement. The `import` and `from ... import` statements can read the calling module's `__name__`/`__package__` from the frame because the compiler emits that information. A plain function call has no access to its caller's frame without a `sys._getframe()` hack. The `package=` argument makes the caller pass the context explicitly — verbose, but honest. Inside a module you can write `importlib.import_module(".sibling", package=__package__)` and it works.

## Execution Trace

```bash
$ python boardly/plugins/loader.py
Loading 3 plugin candidates...

  ok   importlib.metadata -> importlib.metadata (file=/home/z/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/lib/python3.12/importlib/metadata/__init__.py)
  ok   importlib.resources -> importlib.resources (file=/home/z/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/lib/python3.12/importlib/resources/__init__.py)
  FAIL no.such.module -> No module named 'no'

import_module('.metadata', package='importlib'):
  -> importlib.metadata
  is importlib.metadata? True
```

## Common Mistakes

### Mistake 1: Reaching for `__import__` instead of `import_module`

```python
import sys
module = __import__("boardly.routers.projects")
# You now hold `boardly`, not `boardly.routers.projects`.
router = module.routers.projects.router   # walk the dots by hand
```

**Symptom:** `module.router` raises `AttributeError` because `module` is the top-level `boardly` package, not the leaf `projects` module.
**Why:** `__import__("a.b.c")` returns `a` — the *top* of the dotted path, not the leaf. To get the leaf you have to walk down `module.b.c`, which means re-parsing the dotted string.
**Fix:** Use `importlib.import_module(name)`. It returns the leaf. The `import` statement uses `__import__` internally and then walks the dots for you; `import_module` does that walk inside the function so you do not have to.

### Mistake 2: Forgetting `package=` for a relative import

```python
importlib.import_module(".routers.projects")    # TypeError
```

**Symptom:** `TypeError: the 'package' argument is required to perform a relative import for '.routers.projects'`.
**Why:** A leading dot means "relative import." The `import` statement knows the caller's package from the frame; a function call does not. `import_module` requires you to pass the package explicitly.
**Fix:** Either pass `package=` (`importlib.import_module(".routers.projects", package="boardly")`) or use the absolute name (`importlib.import_module("boardly.routers.projects")`). The absolute form is almost always clearer in plugin-loader code.

### Mistake 3: Re-importing on every call

```python
def get_router(name: str):
    return importlib.import_module(name).router    # re-imports every call?
```

**Symptom:** No symptom — but the function is slower than necessary, and a student worries it re-runs the module's body.
**Why:** It does not. `import_module` consults `sys.modules` first; if the module is already imported, the call returns the cached module object. The function is cheap. The body of the module runs exactly once, on first import.
**Fix:** Leave the code alone. If you want to make the "this is cheap" intent obvious to readers, add a one-line comment: `# import_module consults sys.modules; this is a dict lookup, not a re-import.`

## Engineering Trade-Offs

**Decision:** Use `importlib.import_module` for every runtime-string import. Never `exec(f"import {name}")`. Never reach for `__import__` directly.
**Both sides:** The alternative is `__import__`. It is a C builtin, slightly faster on a microbenchmark (a few hundred nanoseconds), and it predates `import_module` (which was added in Python 2.7 / 3.1). But its return-value semantics — return the top-level package, not the leaf — is the source of countless bugs. The CPython docs themselves recommend `import_module` over `__import__` for new code. The microbenchmark is irrelevant when the call site is one-shot at startup.
**Commitment:** `boardly` uses `importlib.import_module` for all plugin loading. `__import__` appears only in `importlib`'s own internals (it is the lower-level hook the import machinery sits on top of) and in CPython's stdlib `runpy`. Application code never calls `__import__` directly.

**Why `import_module` instead of `importlib.__import__`?** Three reasons. First, the return value: `import_module("a.b")` returns `b` (the leaf you wanted); `__import__("a.b")` returns `a` (the top, which you almost never want when you write a dotted path). Second, the dotted-path handling: `import_module` parses the dots for you; with `__import__` you walk them yourself. Third, the *consistency*: `import_module` is what the import machinery itself calls under the hood — it is the public face of the import system, designed for application code. `__import__` is the low-level hook the import statement was originally implemented in terms of; it has stayed in the language for backward compatibility and for the import statement's own use.

## Exercises

1. **Exercise 1 — Import a stdlib module.** Call `importlib.import_module("json")` and print `module.__name__`. Confirm it returns the same object as `import json; json`. `Verify: python -c "import importlib, json; m=importlib.import_module('json'); print(m is json)"`
2. **Exercise 2 — The `__import__` trap.** Compare `importlib.import_module("os.path")` with `__import__("os.path")`. Print both return values and confirm the first returns the leaf (`posixpath` on POSIX) and the second returns the top (`os`). `Verify: python -c "import importlib, os; print(importlib.import_module('os.path').__name__, __import__('os.path').__name__)"`
3. **Exercise 3 — Relative import.** From inside the `boardly` package, call `importlib.import_module(".plugins.loader", package="boardly")`. Confirm it returns the same module as a plain `import boardly.plugins.loader`. `Verify: python -c "import importlib, boardly.plugins.loader as l; m=importlib.import_module('.plugins.loader', package='boardly'); print(m is l)"`
4. **Exercise 4 — Plugin validation.** Extend `load_router` to check that `module.router` is callable (it should be an `APIRouter` instance, which is callable). Raise `TypeError` if not. Hint: `callable(module.router)`. `Verify: python -c "from boardly.plugins.loader import load_router; r=load_router('importlib.metadata'); print('skip fastapi routers — exercise runs only with a real boardly router module')"`
5. **Exercise 5 — Config-driven loader.** Write a function `load_from_yaml(path: str) -> list[LoadedRouter]` that reads a YAML config (use the `yaml` package), iterates the `routers:` list, and calls `load_routers`. Handle the case where the YAML file is missing (return an empty list with a warning). `Verify: python -c "from boardly.plugins.loader import load_from_yaml; print(load_from_yaml('nonexistent.yaml'))"`

## Verification

```bash
$ python boardly/plugins/loader.py | head -2
Loading 3 plugin candidates...

$ python boardly/plugins/loader.py | tail -3
import_module('.metadata', package='importlib'):
  -> importlib.metadata
  is importlib.metadata? True

$ python -c "import importlib; m = importlib.import_module('json'); print(m.__name__)"
json
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature` operates on the *module object* this lesson returns. Once you have `module = importlib.import_module(name)`, the next step is usually `inspect.signature(module.some_function)`.

## What's Next

[[14-importlib/02-resources]] — You can now import a module by name. The next lesson shows you how to read a *data file* bundled inside a package — `boardly/schema.sql`, a SQL DDL file shipped inside the `boardly` package directory. `importlib.resources.files("boardly") / "schema.sql"` returns a `Traversable` path object that works whether `boardly` is installed on the filesystem or packaged as a zip. That is the resource-loading story, and it is the second half of the importlib you will reach for every day.

- **Lesson 02** — `importlib.resources.files`, `.read_text`, `.read_bytes`, the `as_file` context manager.
- **Lesson 03** — `importlib.metadata` for version strings, package metadata, and `entry_points` plugin discovery.
- **Lesson 04** — `importlib.reload`, the development-only hot-reload primitive.

## Sources

- **Python `importlib` module documentation — `importlib.import_module`** — https://docs.python.org/3/library/importlib.html#importlib.import_module — accessed 2026-10-23 — the canonical reference for the function signature, the `package=` argument semantics, and the explicit recommendation to prefer `import_module` over `__import__`.
- **Python `importlib` module documentation — `importlib.__import__`** — https://docs.python.org/3/library/functions.html#import__ — accessed 2026-10-23 — the low-level builtin that the `import` statement uses internally; the docs note its top-level-package return-value semantics and point to `import_module` for new code.
- **PEP 328 — Imports: Multi-Line and Absolute/Relative** — https://peps.python.org/pep-0328/ — accessed 2026-10-23 — the PEP that introduced relative imports and the leading-dot syntax that `import_module`'s `package=` argument supports.

## What We Learned

- You can now call `importlib.import_module("a.b.c")` and know it returns the leaf module `c`, not the top-level package `a`.
- You can now explain why `import_module` is preferred over `__import__` for runtime-string imports — simpler return value, dotted-path handling, consistent with the import machinery's own API.
- You can now use the `package=` argument to perform relative imports at runtime, and you know why the argument is required (a function call has no caller frame to read `__package__` from).
- You can now write a plugin loader that imports router modules from a config list, validates the `router` attribute contract, and isolates broken plugins so one bad module does not crash startup.
- You can now recognise the `exec(f"import {name}")` anti-pattern and replace it with `import_module` — the same call, with proper error handling and no code-injection hole.
