---
title: "Lesson 04: reload and the from-import gotcha"
aliases:
 - importlib.reload
 - hot reload
 - module reload
tags:
 - importlib
 - reload
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[14-importlib/01-import_module]]"
related_lessons:
 - "[[14-importlib/02-resources]]"
 - "[[14-importlib/03-metadata]]"
 - "[[10-inspect/01-signature-and-Parameter]]"
---

# Lesson 04: reload and the from-import gotcha

*Why `boardly`'s developer "I edited `boardly/routers/projects.py` — why is the running app still using the old code?" bug is a `from x import y` trap, and why `importlib.reload(module)` fixes only half of it.*

**You're at the very beginning of Section 14's last lesson.**

You have learned to import a module by name, read its data files, and inspect its distribution metadata. The last `importlib` function — `reload` — is the one you almost never call in production but should understand deeply because every developer hits the bug it causes. `importlib.reload(module)` re-executes the module's code in its existing module object. That sounds like "fix my running app after an edit." It is not. By the end of this lesson you will know why, and you will know the IPython `%autoreload` trick that does work. Take your time. Type every example. **This is how you learn.**

#importlib #reload

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `importlib.reload(module)`** — pass an existing module object (not a name), get back the same module object with its `__dict__` re-populated.
2. **Explain the `from x import y` gotcha** — names imported into *other* modules are not updated by reloading the source module; the `from x import y` line runs once, at import time.
3. **Explain the instance-identity gotcha** — instances of a class created before a reload keep their *old* class; the reloaded module defines a new class object, but old instances point at the old one.
4. **Recognise the IPython `%autoreload 2` use case** — the magic that walks `sys.modules` and reloads every changed module before each cell runs, and why you almost never want `reload` in production.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `importlib.import_module`. `reload(module)` takes a *module object*, the same kind of thing `import_module` returns. See [[14-importlib/01-import_module]] for the canonical introduction.
- **About 25–35 minutes of focused time.**

**The most common gap: assuming `reload(x)` is like "press F5 in the browser."** It is not. Reloading a web page replaces the entire page; the browser does not keep any old JavaScript references. Reloading a Python module updates the module's `__dict__` but does *not* rewrite every place that imported a name from that module. Old references to `module.Thing` keep pointing at the *old* `Thing` class object; the reloaded module defines a *new* `Thing` class object. The two are different objects, and `old_instance.__class__` is still the old `Thing`. Students who do not understand this get one of two symptoms: "I reloaded and my code did not pick up the change" (the `from x import y` gotcha) or "I reloaded and now my class instances fail `isinstance` checks" (the instance-identity gotcha).

## The Problem

Here is the bug. `boardly`'s `routers/projects.py` defines a `Project` class:

```python
# boardly/routers/projects.py — version 1
class Project:
    color = "red"
```

A second module imports it:

```python
# boardly/app.py
from boardly.routers.projects import Project

def get_color():
    return Project.color   # uses the Project captured at import time
```

You start the app. `get_color()` returns `"red"`. You edit `projects.py` to change `color = "red"` to `color = "blue"`. You reload the projects module:

```python
>>> import boardly.routers.projects as projects
>>> import importlib
>>> importlib.reload(projects)
<module 'boardly.routers.projects'>
>>> projects.Project.color
'blue'       # the module-level reference is updated
```

You then call `get_color()` from `app.py` and expect `"blue"`. You get `"red"`. The reload updated `projects.Project`, but `app.py`'s `Project` is a *different name* — it is a binding in `app.py`'s `__dict__`, captured once at the time `app.py` was imported (long before the reload). The reload has no way to walk every consumer module and rewrite its `Project` binding. The "press F5" intuition fails.

The IPython/Jupyter notebook use case is real — you are editing `projects.py` in another editor and you want the notebook to pick up the change. The naive `importlib.reload(projects)` does not help; you need to reload every consumer of `projects` too. IPython's `autoreload` extension does that walk for you, every time you execute a cell. In production, the answer is almost never `reload` — it is "restart the process."

## The Code

```python
# boardly/dev/reload_demo.py
"""Demonstrates importlib.reload and the from-import gotcha."""
from __future__ import annotations
import importlib
import sys
import tempfile
import textwrap
from pathlib import Path


def _write_module(dir_path: Path, name: str, source: str):
    """Write a Python file into a directory."""
    (dir_path / f"{name}.py").write_text(source, encoding="utf-8")


def main():
    # Set up a throwaway package on disk.
    tmpdir = Path(tempfile.mkdtemp())
    print(f"workspace: {tmpdir}")
    sys.path.insert(0, str(tmpdir))

    # Version 1 of `routers.projects` and a consumer `app`.
    _write_module(tmpdir, "routers", textwrap.dedent("""
        class Router:
            color = "red"
            def handle(self):
                return "handle-v1"
        ROUTER_INSTANCE = Router()
    """))
    _write_module(tmpdir, "app", textwrap.dedent("""
        from routers import Router, ROUTER_INSTANCE

        def describe():
            return f"Router.color={Router.color}, instance={ROUTER_INSTANCE.hello() if hasattr(ROUTER_INSTANCE, 'hello') else ROUTER_INSTANCE.handle()}"
    """))

    import routers
    import app

    print("\n--- before reload ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")

    # Edit routers.py to version 2.
    _write_module(tmpdir, "routers", textwrap.dedent("""
        class Router:
            color = "blue"
            def handle(self):
                return "handle-v2"
        ROUTER_INSTANCE = Router()
    """))

    # Reload routers, but NOT app.
    importlib.reload(routers)
    print("\n--- after reload(routers), app NOT reloaded ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")

    # Reload app too.
    importlib.reload(app)
    print("\n--- after reload(app) too ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")


if __name__ == "__main__":
    main()
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 4–10: Imports and `_write_module`

```python
import importlib
import sys
import tempfile
import textwrap
from pathlib import Path


def _write_module(dir_path: Path, name: str, source: str):
    (dir_path / f"{name}.py").write_text(source, encoding="utf-8")
```

The demo needs to write a module to disk, run code that imports it, edit the file, reload, and observe the new state. `tempfile.mkdtemp()` gives us a throwaway directory; `_write_module` writes a Python file into it; `sys.path.insert(0, str(tmpdir))` puts the directory on `sys.path` so `import routers` finds it. The whole setup is a controlled experiment — in a real dev session you would just edit your package's real files; here we need the experiment to be reproducible.

### Lines 13–17: Version 1 of `routers.py`

```python
_write_module(tmpdir, "routers.py", textwrap.dedent("""
    class Router:
        color = "red"
        def handle(self):
            return "handle-v1"
    ROUTER_INSTANCE = Router()
"""))
```

The version-1 module defines `Router` with `color = "red"` and a module-level `ROUTER_INSTANCE = Router()`. The instance is created *at module import time* — the `Router()` call runs as part of the module body's execution. When the module is reloaded later, the body runs again, `Router()` runs again, and `ROUTER_INSTANCE` is rebound to a *new* instance of the *new* `Router` class. That is the instance-identity gotcha in a single line.

### Lines 18–22: Version 1 of `app.py`

```python
_write_module(tmpdir, "app.py", textwrap.dedent("""
    from routers import Router, ROUTER_INSTANCE

    def describe():
        return f"Router.color={Router.color}, instance={ROUTER_INSTANCE.hello() if hasattr(ROUTER_INSTANCE, 'hello') else ROUTER_INSTANCE.handle()}"
"""))
```

The consumer module does `from routers import Router, ROUTER_INSTANCE`. That line executes *once*, when `app` is first imported. It captures the *current* `Router` and `ROUTER_INSTANCE` from `routers` and binds them in `app`'s namespace. From that point on, `app.Router` and `app.ROUTER_INSTANCE` are independent of any subsequent changes to `routers.Router` or `routers.ROUTER_INSTANCE` — they are bindings in `app`'s `__dict__`, not live lookups into `routers`'s `__dict__`.

The `hasattr(ROUTER_INSTANCE, 'hello')` ternary is a small detail: version 1 of `Router` does not have a `hello` method, only `handle`. We call `handle` to read the version string out of the instance. After a reload that updates `routers.Router` to a new class with a new `handle` method, the *instance* the reloaded module created still has the *old* handle implementation — because `ROUTER_INSTANCE.__class__` is the *old* `Router` class object.

### Lines 25–33: First-import state

```python
import routers
import app

print("\n--- before reload ---")
print(f"  routers.Router.color:     {routers.Router.color}")
print(f"  app.Router.color:        {app.Router.color}")
print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
print(f"  app.describe():          {app.describe()}")
```

At first import, `routers.Router.color` is `"red"` and `app.Router.color` is also `"red"` — they are the *same* class object, so reading `color` from either returns the same value. The `is` check confirms identity: `app.Router is routers.Router` is `True`. This is the only moment in the demo where the two are the same object.

`app.describe()` returns `"Router.color=red, instance=handle-v1"` — the `ROUTER_INSTANCE` captured by `app` is the one from version 1, and its `handle()` returns `"handle-v1"`.

### Lines 36–42: Edit and reload only `routers`

```python
_write_module(tmpdir, "routers.py", textwrap.dedent("""
    class Router:
        color = "blue"
        def handle(self):
            return "handle-v2"
    ROUTER_INSTANCE = Router()
"""))

importlib.reload(routers)
```

`_write_module` overwrites `routers.py` with version 2: `color = "blue"`, `handle` returns `"handle-v2"`. The file on disk is now the new version; the module *object* in `sys.modules["routers"]` is still the old one.

`importlib.reload(routers)` re-executes the module's code in the existing module object. The module's `__dict__` is updated in place: `routers.Router` is rebound to the new `Router` class object; `routers.ROUTER_INSTANCE` is rebound to a new instance of the new `Router`. The module object's identity is preserved (`sys.modules["routers"]` is the same module object before and after), but its contents are new.

**Why `reload(module)` instead of `del sys.modules[name]; import_module(name)`?** Because the existing module object is what every consumer holds a reference to. If you delete the module from `sys.modules` and re-import, you get a *new* module object — but every consumer that imported the module by name still holds a reference to the *old* module object, and `sys.modules` now contains the *new* one. That is worse than the reload approach: not only are `from x import y` bindings stale, but `sys.modules["x"]` is also out of sync with what consumers hold. `reload` keeps the module identity stable so that `module-level attribute lookups` (e.g., `routers.Router` from anywhere) see the new version. The `from x import y` bindings remain stale in both cases — that is the gotcha.

### Lines 43–48: Observe the `from x import y` gotcha

```python
print("\n--- after reload(routers), app NOT reloaded ---")
print(f"  routers.Router.color:     {routers.Router.color}")
print(f"  app.Router.color:        {app.Router.color}")
print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
print(f"  app.describe():          {app.describe()}")
```

After `reload(routers)`:
- `routers.Router.color` is `"blue"` — the module-level lookup reads the new `Router` class.
- `app.Router.color` is `"red"` — `app.Router` is the *old* `Router` class object, captured when `app` was first imported. It still has `color = "red"`.
- `app.Router is routers.Router` is `False` — they are different class objects now. The reloaded module has a new `Router`; the consumer has the old one.
- `app.describe()` is `"Router.color=red, instance=handle-v1"` — `app`'s `Router` and `ROUTER_INSTANCE` are both the old objects, so reading them gives the old values.

The reload did *not* propagate to `app`. This is the gotcha in one sentence: **`importlib.reload(module)` updates the module's `__dict__`; it does not update any other module's `__dict__`.**

### Lines 51–56: Reload `app` too, observe identity restoration

```python
importlib.reload(app)
print("\n--- after reload(app) too ---")
print(f"  routers.Router.color:     {routers.Router.color}")
print(f"  app.Router.color:        {app.Router.color}")
print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
print(f"  app.describe():          {app.describe()}")
```

After `reload(app)` too:
- `routers.Router.color` is `"blue"` (unchanged — reloading `app` does not touch `routers`).
- `app.Router.color` is `"blue"` — re-running `app`'s `from routers import Router` line captures the *current* `routers.Router` (the new blue one).
- `app.Router is routers.Router` is `True` — both point at the new `Router`.
- `app.describe()` is `"Router.color=blue, instance=handle-v2"` — the new `ROUTER_INSTANCE` is captured too, and its `handle()` returns `"handle-v2"`.

The lesson: reloading a module updates that module's view of the world. To update a *consumer's* view, you must reload the consumer too. The general rule: reload every module that has done a `from x import y` of the changed module — and every module that has done a `from z import y` of *those* modules, transitively. The naive single-module reload updates one slice of the dependency graph; the rest of the graph keeps the old bindings.

**Why does IPython's `%autoreload 2` work then?** Because the `autoreload` extension walks `sys.modules` before every cell execution, detects which modules' source files have changed (by reading mtime/size), reloads *every* changed module, and then re-runs the `from x import y` lines in every consumer module by manipulating their `__dict__`. It is not using `reload(module)` alone; it is using `reload` *plus* a manual rewrite of the `from x import y` bindings in every consumer. That is the only way to make "edit a file, see the change in the next cell" actually work. You almost never want to reimplement that machinery yourself.

## Execution Trace

```bash
$ python boardly/dev/reload_demo.py
workspace: /tmp/tmpXXXXXXXX

--- before reload ---
  routers.Router.color:     red
  app.Router.color:        red
  app.Router is routers.Router? True
  app.describe():          Router.color=red, instance=handle-v1

--- after reload(routers), app NOT reloaded ---
  routers.Router.color:     blue
  app.Router.color:        red
  app.Router is routers.Router? False
  app.describe():          Router.color=red, instance=handle-v1

--- after reload(app) too ---
  routers.Router.color:     blue
  app.Router.color:        blue
  app.Router is routers.Router? True
  app.describe():          Router.color=blue, instance=handle-v2
```

## Common Mistakes

### Mistake 1: Reloading one module and expecting consumers to update

```python
import boardly.routers.projects as projects
importlib.reload(projects)
# app.py's `from boardly.routers.projects import Project` is NOT updated
```

**Symptom:** You reloaded `projects`, but `app.Project` still points at the old class. Your running app behaves as if you never reloaded.
**Why:** `from x import y` runs once, at import time. The binding `app.Project` is a name in `app`'s `__dict__`, set once. Reloading `projects` rebinds `projects.Project` (the module-level attribute), not `app.Project` (the consumer's binding).
**Fix:** Reload `app` too. Or — better — restart the process. The reload-aware IPython extension is `%load_ext autoreload; %autoreload 2`; it walks `sys.modules` for you.

### Mistake 2: Reloading a module and expecting existing instances to migrate

```python
old_instance = routers.ROUTER_INSTANCE      # the v1 instance
importlib.reload(routers)
new_instance = routers.ROUTER_INSTANCE     # the v2 instance
isinstance(old_instance, routers.Router)  # False
```

**Symptom:** `isinstance(old_instance, routers.Router)` returns `False` even though `old_instance` is clearly an instance of "the Router class."
**Why:** After the reload, `routers.Router` is a *new* class object. `old_instance.__class__` is the *old* class object. The two are different objects; `isinstance` checks `__class__` identity. So `isinstance(old_instance, routers.Router)` is `False`.
**Fix:** Re-create the instance. In the demo, `routers.ROUTER_INSTANCE = Router()` runs again on reload, so `routers.ROUTER_INSTANCE` *is* a new instance of the new class — but the *old* instance still exists in memory until every reference to it is dropped. The fix is "do not expect old instances to migrate to a new class definition." Design your code so instances are short-lived (per-request, not module-level) if you expect to reload.

### Mistake 3: Passing a *name* to `reload` instead of a module object

```python
importlib.reload("boardly.routers.projects")   # TypeError
```

**Symptom:** `TypeError: reload() argument must be a module` (raised at the `reload` call site).
**Why:** `reload()` takes a module object (the thing `import` binds in your namespace), not the dotted string name. The function signature is `reload(module)` — it walks the module's `__spec__`, `__loader__`, `__name__` to know which file to re-execute. None of those exist on a string.
**Fix:** Import the module first, then reload it: `import boardly.routers.projects as projects; importlib.reload(projects)`. Or use `importlib.import_module` to get the module object: `importlib.reload(importlib.import_module("boardly.routers.projects"))`.

## Engineering Trade-Offs

**Decision:** Use `importlib.reload` for development only — for IPython/Jupyter sessions where you want to test a code change without restarting the kernel. Never in production.
**Both sides:** The alternative in production is process restart — `gunicorn --reload` (which watches files and *restarts the worker process*, not reloads modules in-place), `uvicorn --reload` (same model), or a graceful worker-rollover deploy. Process restart is heavy (re-import every module, re-warm caches, drop in-flight connections) but correct (no stale bindings, no orphaned classes). Module reload is cheap (re-execute one module) but only correct if you reload every transitive consumer — and even then, long-lived instances keep their old `__class__`. For production the correctness wins; for a notebook session the cheapness wins.
**Commitment:** `boardly`'s production deployment uses `uvicorn --reload` (in dev) and `gunicorn --workers N --reload` (in prod staging) — both watch files and restart the worker, never `importlib.reload` in application code. The `reload` function appears only in `boardly/dev/reload_demo.py` — a development-only script that demonstrates the gotcha. No production code calls `importlib.reload`.

**Why is `reload` in the stdlib if you should not use it in production?** Three reasons. First, it predates the modern hot-reload story — `reload` was added in Python 2.x when "no process restart" was a real productivity win on slow machines. Second, it powers IPython's `%autoreload` extension, which IS a legitimate development tool. Third, it is occasionally useful for one-off debugging — "reload this one module so I can poke at the new class in the REPL without losing my session." All three are development use cases. None is a production use case. The function is in the stdlib because development is part of Python.

## Exercises

1. **Exercise 1 — The basic reload.** Import a module, change its source file, call `importlib.reload(module)`, confirm the module-level attribute reflects the new source. `Verify: python -c "import importlib, json; print(importlib.reload(json) is json)"`
2. **Exercise 2 — The `from x import y` gotcha.** Build the demo from this lesson. Reload `routers` only. Confirm `app.Router is routers.Router` is `False` after the reload. `Verify: python -c "import importlib, sys, tempfile, textwrap; from pathlib import Path; d=Path(tempfile.mkdtemp()); sys.path.insert(0,str(d)); (d/'a.py').write_text('class A:\n  v=1'); import a; (d/'a.py').write_text('class A:\n  v=2'); importlib.reload(a); print(a.A.v)"`
3. **Exercise 3 — Reload the consumer too.** Extend exercise 2: also reload the consumer module. Confirm the consumer's reference now matches the reloaded module. `Verify: python -c "import importlib, sys, tempfile, textwrap; from pathlib import Path; d=Path(tempfile.mkdtemp()); sys.path.insert(0,str(d)); (d/'a.py').write_text('class A:\n  v=1'); (d/'b.py').write_text('from a import A'); import a, b; (d/'a.py').write_text('class A:\n  v=2'); importlib.reload(a); importlib.reload(b); print(b.A.v, b.A is a.A)"`
4. **Exercise 4 — The instance-identity trap.** Create an instance of a class, reload the module, and confirm `isinstance(old_instance, NewClass)` is `False`. Write a short comment in your code explaining why. `Verify: python -c "import importlib, sys, tempfile; from pathlib import Path; d=Path(tempfile.mkdtemp()); sys.path.insert(0,str(d)); (d/'x.py').write_text('class C:\n  pass\nI=C()'); import x; old=x.I; (d/'x.py').write_text('class C:\n  pass\nI=C()'); importlib.reload(x); print(isinstance(old, x.C), old is x.I)"`
5. **Exercise 5 — IPython `%autoreload`.** In a Jupyter notebook or IPython session, run `%load_ext autoreload` and `%autoreload 2`. Edit a Python file in another editor. Confirm the next cell sees the new version without an explicit `importlib.reload` call. Explain in a comment how `autoreload` differs from `reload`. `Verify: ipython -c "%load_ext autoreload; %autoreload 2; print('autoreload active')"`

## Verification

```bash
$ python boardly/dev/reload_demo.py | grep -E '^(---|  )' | head -8
--- before reload ---
  routers.Router.color:     red
  app.Router.color:        red
  app.Router is routers.Router? True
  app.describe():          Router.color=red, instance=handle-v1

--- after reload(routers), app NOT reloaded ---
  routers.Router.color:     blue

$ python -c "import importlib, json; print(importlib.reload(json) is json)"
True

$ python -c "import importlib; print(importlib.reload.__doc__[:50])"
Reload the module and return it.
```

## Previously Learned Here

- [[14-importlib/01-import_module]] — `import_module` returns the module object that `reload(module)` takes. The two functions are siblings: `import_module` for the first import, `reload` for re-importing an already-loaded module.
- [[14-importlib/03-metadata]] — `entry_points().load()` calls `import_module`; if a plugin module is reloaded later, the cached `EntryPoint.load()` result is unaffected unless you re-call `.load()`.

## What's Next

[[10-inspect/01-signature-and-Parameter]] — `inspect.signature` operates on the live objects in a module after `reload`. The inspect section shows you how to read what `reload` left behind — the new `__code__`, the new `__defaults__`, the new `__annotations__` of every function the reloaded module defines.

- **[[10-inspect/01-signature-and-Parameter]]** — `inspect.signature` on a reloaded function.
- **[[10-inspect/02-get_type_hints]]** — `get_type_hints` on a reloaded function's annotations.
- **[[14-importlib/00-importlib-MOC]]** — the section index; the four lessons you have just completed.

## Sources

- **Python `importlib` module documentation — `importlib.reload`** — https://docs.python.org/3/library/importlib.html#importlib.reload — accessed 2026-10-23 — the canonical reference for the function signature and the explicit note that `reload` re-executes module code in the existing module object.
- **Python `importlib` module documentation — reload caveats** — https://docs.python.org/3/library/importlib.html#module-importlib — accessed 2026-10-23 — the docs note explicitly that `from x import y` bindings in other modules are not updated by `reload`, and that `isinstance` checks against reloaded classes can fail.
- **IPython `autoreload` extension documentation** — https://ipython.readthedocs.io/en/stable/config/extensions/#autoreload — accessed 2026-10-23 — the production-quality hot-reload mechanism for IPython / Jupyter sessions; the right way to get "edit, re-run cell" semantics.

## What We Learned

- You can now call `importlib.reload(module)` and know it takes a module object (not a name string) and re-executes the module's code in the existing module object.
- You can now explain the `from x import y` gotcha — names imported into other modules are not updated by reloading the source; the binding is captured once, at import time.
- You can now explain the instance-identity gotcha — instances created before a reload keep their old `__class__`; the reloaded module defines a new class object; `isinstance(old, NewClass)` is `False`.
- You can now recognise IPython's `%autoreload 2` as the legitimate development use case, and you know it works by reloading *every* changed module plus rewriting every consumer's `from x import y` bindings before each cell execution.
- You can now explain why `importlib.reload` is in the stdlib despite being a development-only tool — it powers `%autoreload`, it predates process-restart hot-reload, and it is occasionally useful for one-off debugging in a REPL session.
