---
title: "Lesson 02: resources — reading package-bundled data files"
aliases:
 - importlib.resources
 - files API
 - as_file
 - Traversable
tags:
 - importlib
 - resources
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[14-importlib/01-import_module]]"
related_lessons:
 - "[[14-importlib/03-metadata]]"
 - "[[14-importlib/04-reload]]"
 - "[[08-pathlib/00-pathlib-MOC]]"
---

# Lesson 02: resources — reading package-bundled data files

*How `boardly`'s database init reads `boardly/schema.sql` — a SQL DDL file shipped inside the `boardly` package — without caring whether the package is installed as a folder on disk or packaged as a single `.zip` / `.whl`.*

**You're at the very beginning of Section 14's second lesson.**

You imported a module by name in lesson 01. Now you need to read a *file* that ships inside a package — a SQL schema, a JSON template, a YAML default, a PNG asset. The naive `open("boardly/schema.sql")` works on your laptop, fails in a `pip install`'d wheel, and dies silently in a frozen zipapp. `importlib.resources` is the public API for reading package data that survives every packaging form Python supports. By the end of this lesson you can read a bundled SQL file and hand a real filesystem path to a C library that needs one. Take your time. Type every example. **This is how you learn.**

#importlib #resources

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `importlib.resources.files(package)`** — get back a `Traversable` for the package's root, then walk it with `/` and `.joinpath`.
2. **Read text and bytes** — use `.read_text(encoding="utf-8")` and `.read_bytes()` on a `Traversable` and explain why they are preferred over `open(path).read()`.
3. **Use the `as_file()` context manager** — extract a resource to a real filesystem path when the consumer needs a `str` (e.g., a C library `open()`), and explain when extraction is *required* (zip packages).
4. **Recognise the deprecated old API** — name `importlib.resources.path`, `read_text`, `read_binary` as the 3.11-deprecated functions, and write the modern equivalent.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `importlib.import_module`. The `files()` API takes a package name or a package module object, the same kind of thing `import_module` returns. See [[14-importlib/01-import_module]] for the canonical introduction.
- **About 30–40 minutes of focused time.**

**The most common gap: assuming the package is a folder.** Students learn `import boardly` and assume there is a `boardly/` directory on disk somewhere with `schema.sql` inside it. That is true for `pip install -e .` (editable install) and false for `pip install boardly` (a wheel installs into `site-packages`, where the package may still be a folder) and false again for `pip install boardly-zipapp` (the package is a single zip file, no folder exists). The `importlib.resources` API exists because the file-on-disk assumption is true only sometimes; the API works in *all* packaging forms.

## The Problem

Here is the bug. `boardly` ships a SQL schema inside the package — when the application starts, it runs the schema to initialise the database. The first version of the code looked like this:

```python
# boardly/db.py — the broken approach
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_db():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    engine.execute(sql)
```

That works when you run `python -m boardly` from a git checkout. It works when you `pip install -e .`. It *breaks* the moment you ship `boardly` as a wheel (yes, wheels unpack into a folder, so this still works — but only because `pip` happens to unpack). It *breaks hard* the moment you ship `boardly` as a zipapp or a single-file frozen executable — `Path(__file__).parent` points inside the zip, and `read_text` raises `FileNotFoundError` because there is no real file on disk to read.

Even worse, the second broken pattern:

```python
# boardly/db.py — the slightly-less-broken approach
import os
schema_dir = os.path.dirname(__file__)    # same as Path(__file__).parent
schema_path = os.path.join(schema_dir, "schema.sql")
with open(schema_path, encoding="utf-8") as f:
    sql = f.read()
```

Same problem: assumes a real folder. Same failure modes. The `importlib.resources` API was added to Python (3.7 for the older `path()` form, 3.9 for the `files()` form) to give you one call that works regardless of packaging. The 3.9+ `files()` API returns a `Traversable` — an abstract path-like object that knows how to `read_text`, `read_bytes`, `open`, `is_file`, `iterdir` whether the underlying storage is a real folder or a virtual zip entry.

## The Code

```python
# boardly/db_resources.py
"""Read the bundled SQL schema via importlib.resources."""
from __future__ import annotations
import importlib.resources as resources


def read_schema_text() -> str:
    """Return the contents of boardly/schema.sql as a string."""
    schema = resources.files("boardly").joinpath("schema.sql")
    return schema.read_text(encoding="utf-8")


def read_schema_bytes() -> bytes:
    """Return the contents of boardly/schema.sql as bytes (for hash check)."""
    schema = resources.files("boardly") / "schema.sql"
    return schema.read_bytes()


def schema_path_for_c_library():
    """Yield a real filesystem path to schema.sql for a C consumer."""
    schema = resources.files("boardly") / "schema.sql"
    with resources.as_file(schema) as real_path:
        # Inside this `with`, `real_path` is a real PosixPath on disk.
        # Outside it, the temp file is deleted.
        return real_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    # For the demo we use the stdlib `email` package and its `charset.py`
    # as a stand-in for `boardly/schema.sql`, so the demo runs without a
    # real boardly install.
    print("--- read_text ---")
    demo_text = resources.files("email").joinpath("charset.py").read_text(encoding="utf-8")
    print(f"length: {len(demo_text)} chars")
    print(f"first 50 chars: {demo_text[:50]!r}")

    print("\n--- read_bytes ---")
    demo_bytes = resources.files("email").joinpath("charset.py").read_bytes()
    print(f"length: {len(demo_bytes)} bytes")
    print(f"first 10 bytes: {demo_bytes[:10]!r}")

    print("\n--- as_file context manager ---")
    charset = resources.files("email") / "charset.py"
    with resources.as_file(charset) as p:
        print(f"yielded path: {p}")
        print(f"type: {type(p).__name__}")
        print(f"exists on disk: {p.exists()}")
        print(f"open(p).read(50): {open(p).read(50)!r}")

    print("\n--- Traversable interface ---")
    root = resources.files("email")
    print(f"files('email') type: {type(root).__name__}")
    print(f"is_dir:  {root.is_dir()}")
    print(f"is_file: {root.is_file()}")
    print("iterdir (first 3 children):")
    for child in list(root.iterdir())[:3]:
        print(f"  {child.name}  (is_file={child.is_file()})")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 4–7: The import and what `files()` returns

```python
import importlib.resources as resources


def read_schema_text() -> str:
    schema = resources.files("boardly").joinpath("schema.sql")
    return schema.read_text(encoding="utf-8")
```

`importlib.resources` is a submodule of `importlib`, imported separately. The two functions you will reach for are `files()` and `as_file()` — both are top-level.

`resources.files("boardly")` returns a `Traversable` — an abstract path-like object — pointing at the `boardly` package's root. When `boardly` is installed on disk as a normal folder (the common case), the returned object is a `PosixPath` (or `WindowsPath` on Windows) — a real `pathlib.Path` subclass, because `pathlib.Path` happens to satisfy the `Traversable` interface. When `boardly` is packaged as a zip, the returned object is `importlib.resources.abc.Traversable`'s zip-aware subclass — *not* a `pathlib.Path`, because a zip entry is not a real file. The lesson here is: do not assume `isinstance(path, pathlib.Path)`. Call the `Traversable` methods (`.read_text`, `.read_bytes`, `.is_file`, `.open`, `.iterdir`) and let the implementation handle storage.

`.joinpath("schema.sql")` walks one segment down. The `/` operator also works (`files("boardly") / "schema.sql"`) because `Traversable.__truediv__` is defined. The two forms are identical; pick the one that reads best in your code.

`.read_text(encoding="utf-8")` returns the file's contents as a string. Always pass `encoding=` — the default encoding is `locale.getpreferredencoding(False)`, which is `"UTF-8"` on most Linux systems but `"cp1252"` on Windows. Passing `encoding="utf-8"` makes the call site deterministic; your SQL file is the same bytes on every machine. The same rule applies to `.read_bytes()` if you want raw bytes for a hash check or a binary format.

**Why `files(package).joinpath(name).read_text()` instead of the older `read_text(package, name)`?** Because the new `files()` API gives you a `Traversable` you can walk, list, and pass around. The old `read_text(package, name)` was a one-shot helper — it returned a string and gave you no path object to introspect. If you wanted to also list the package's contents, you had to call `importlib.resources.contents(package)` separately. The new API unifies everything onto the `Traversable` interface: `files(pkg)` gives you a path you can `iterdir`, `/` into, `read_text`, `read_bytes`, or `as_file`. One object, many operations.

### Lines 13–16: Reading bytes for a hash check

```python
def read_schema_bytes() -> bytes:
    schema = resources.files("boardly") / "schema.sql"
    return schema.read_bytes()
```

`read_bytes()` is the binary twin of `read_text()`. Use it when the file is binary (PNG, pickle, a sqlite DB shipped as a template) or when you want a stable byte sequence for a hash. Text files have an encoding parameter; bytes do not. The two are not interchangeable — `read_text` returns `str`, `read_bytes` returns `bytes`, and `str` ≠ `bytes` in Python 3.

The boardly use case for `read_bytes` is the schema integrity check: hash the bytes of `schema.sql` at startup and compare to a stored hash, so a tampered or half-installed package fails loudly before the application starts.

### Lines 19–24: `as_file` — the context manager for a real path

```python
def schema_path_for_c_library():
    schema = resources.files("boardly") / "schema.sql"
    with resources.as_file(schema) as real_path:
        return real_path.read_text(encoding="utf-8")
```

`as_file(traversable)` is a context manager. Inside the `with` block, `real_path` is a real `pathlib.Path` on disk — always. When the package is on a normal filesystem, `as_file` yields the same path the `Traversable` wrapped (no extraction, no copy). When the package is in a zip, `as_file` extracts the resource to a temporary file (`/tmp/<random>schema.sql`), yields that temp path, and deletes the temp file on exit.

You reach for `as_file` when the consumer of the resource *requires* a real filesystem path — typically a C library that does its own `fopen`, an external program you spawn with `subprocess.run([..., str(path), ...])`, or a tool that only takes a path string. The boardly example: the `sqlite3` CLI can be invoked to load a schema via `subprocess.run(["sqlite3", db_path, ".read", str(schema_path)])`. That CLI does its own file I/O and cannot read a `Traversable`; `as_file` hands it a real path.

**Why is `as_file` a context manager and not a plain function?** Because of the cleanup contract. When the package is in a zip, the resource does not exist on disk until extracted; the extraction creates a temp file; that temp file must be deleted when you are done with it. A plain function returning a path would have no signal for "I am done with this file" — the temp file would leak. The context manager's `__exit__` is the cleanup hook. When the package is on a normal filesystem, `as_file` is a no-op (yields the same path, deletes nothing) — the context manager is a no-cost abstraction in the common case and a correctness-saver in the zip case.

### Lines 27–50: The demo driver

```python
if __name__ == "__main__":
    print("--- read_text ---")
    demo_text = resources.files("email").joinpath("charset.py").read_text(encoding="utf-8")
    print(f"length: {len(demo_text)} chars")
    print(f"first 50 chars: {demo_text[:50]!r}")

    print("\n--- read_bytes ---")
    demo_bytes = resources.files("email").joinpath("charset.py").read_bytes()
    print(f"length: {len(demo_bytes)} bytes")
    print(f"first 10 bytes: {demo_bytes[:10]!r}")

    print("\n--- as_file context manager ---")
    charset = resources.files("email") / "charset.py"
    with resources.as_file(charset) as p:
        print(f"yielded path: {p}")
        print(f"type: {type(p).__name__}")
        print(f"exists on disk: {p.exists()}")
        print(f"open(p).read(50): {open(p).read(50)!r}")

    print("\n--- Traversable interface ---")
    root = resources.files("email")
    print(f"files('email') type: {type(root).__name__}")
    print(f"is_dir:  {root.is_dir()}")
    print(f"is_file: {root.is_file()}")
    print("iterdir (first 3 children):")
    for child in list(root.iterdir())[:3]:
        print(f"  {child.name}  (is_file={child.is_file()})")
```

The demo uses stdlib's `email` package and its `charset.py` file as a stand-in for `boardly/schema.sql`, so the demo runs without a real boardly install. The `email` package is a real, always-installed package that ships real `.py` files inside it — perfect for showing every behaviour `importlib.resources` provides.

The `as_file` block prints the yielded path and its type. On a normal Python install, the type is `PosixPath` — a real `pathlib.Path` subclass pointing at the actual file in the stdlib tree. The `open(p).read(50)` line then opens the path as if you had written `open("/usr/lib/.../email/charset.py")`. That is the whole point: inside the `with`, `p` is a real path you can hand to anything that takes a path.

The last block exercises the `Traversable` interface: `is_dir()` (True for the package root), `is_file()` (False for the package root), and `iterdir()` (yields each child). `iterdir` returns an iterator of `Traversable` objects — call `.name` on each to get the basename, `.is_file()` to filter, `.is_dir()` to recurse. This is the same interface as `pathlib.Path.iterdir`, deliberately — `Traversable` was designed to be a drop-in for `pathlib.Path`'s read-only methods.

**Why does `files(package)` return `PosixPath` on disk and a `Traversable` subclass in a zip?** Because on disk, `pathlib.Path` *is* a valid `Traversable` (it implements every method the `Traversable` ABC requires), so the import machinery returns the real `Path` object instead of wrapping it. In a zip, no real `Path` exists, so the import machinery returns the zip-aware `Traversable` subclass. The student-facing rule is: never check `isinstance(result, pathlib.Path)`. Use the `Traversable` methods — they work in both cases. (The 08-pathlib lessons, when they land, will cover the `pathlib.Path` interface in depth; [[08-pathlib/00-pathlib-MOC]] is the planned index.)

## Execution Trace

```bash
$ python boardly/db_resources.py
--- read_text ---
length: 17063 chars
first 50 chars: '# Copyright (C) 2001-2007 Python Software Foundati'

--- read_bytes ---
length: 17063 bytes
first 10 bytes: b'# Copyrigh'

--- as_file context manager ---
yielded path: /home/z/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/lib/python3.12/email/charset.py
type: PosixPath
exists on disk: True
open(p).read(50): '# Copyright (C) 2001-2007 Python Software Foundati'

--- Traversable interface ---
files('email') type: PosixPath
is_dir:  True
is_file: False
iterdir (first 3 children):
  base64mime.py  (is_file=True)
  _header_value_parser.py  (is_file=True)
  contentmanager.py  (is_file=True)
```

## Common Mistakes

### Mistake 1: Using the deprecated `read_text(package, name)` form

```python
# Deprecated since 3.11; works on 3.12, scheduled for removal.
import importlib.resources as r
text = r.read_text("boardly", "schema.sql", encoding="utf-8")
```

**Symptom:** No symptom on 3.12 — the call works. The break comes on a future Python where the deprecated functions are removed.
**Why:** The 3.9 `files()` API was added precisely because the old `read_text(package, resource)` form was a one-shot — no path object to introspect, no consistent interface with directory walking. The docs deprecated the old form in 3.11.
**Fix:** Use `r.files("boardly").joinpath("schema.sql").read_text(encoding="utf-8")`. Same result, future-proof, and you have a `Traversable` you can reuse for `read_bytes`, `as_file`, or `iterdir`.

### Mistake 2: Assuming `files(pkg)` returns a `pathlib.Path`

```python
from pathlib import Path
p = resources.files("boardly")
if isinstance(p, Path):        # True on disk, False in a zip
    do_something_with(p.stat())   # breaks in a zip
```

**Symptom:** The `isinstance` check passes on a dev machine and fails in a deployed zipapp or wheel-packaged-as-zip.
**Why:** On disk, `files()` returns a real `pathlib.Path` (because `Path` satisfies `Traversable`). In a zip, it returns a zip-aware `Traversable` that is *not* a `Path` subclass. The `isinstance` check is a fragile assumption.
**Fix:** Use the `Traversable` interface directly: `.read_text()`, `.read_bytes()`, `.is_file()`, `.iterdir()`, `.open()`, `.name`, `.parent`. If you must have a real `pathlib.Path` (for a C library, an external subprocess), use `with resources.as_file(p) as real_path:` and operate on `real_path` inside the `with`.

### Mistake 3: Using `as_file` and then exiting the `with` block before using the path

```python
with resources.as_file(schema) as p:
    pass
# Now `p` is a stale path; the temp file may be deleted
subprocess.run(["sqlite3", db_path, ".read", str(p)])   # FileNotFoundError
```

**Symptom:** `FileNotFoundError` from the subprocess because the temp file was already deleted.
**Why:** `as_file`'s `__exit__` deletes the temp file when the `with` block ends. Anything that uses the path outside the `with` is reading a stale reference.
**Fix:** Move the consumer inside the `with` block. The pattern is: `with as_file(p) as real_path: subprocess.run([...str(real_path)...])`. The `with` block's scope *is* the lifetime of the extracted path.

## Engineering Trade-Offs

**Decision:** Use `importlib.resources.files()` and `as_file()` for every read of a package-bundled data file. Never `Path(__file__).parent / "schema.sql"`.
**Both sides:** The alternative is `Path(__file__).parent` — the "read a sibling file" pattern. It works on disk, it is one line shorter, and it gives you a real `pathlib.Path` you can manipulate freely. It also breaks the moment you package the application as a zipapp, a frozen binary, or — in some deployment styles — a wheel where the package's location is not what you expect. The `files()` API costs you one extra import and one extra method call (essentially free) and gains you correctness in every packaging form Python supports.
**Commitment:** `boardly` uses `files("boardly") / "schema.sql"` for reading bundled data. The `Path(__file__).parent` pattern is banned in code review. `as_file` is used at the single place where the `sqlite3` CLI is invoked with the schema file path — the only consumer that requires a real filesystem path.

**Why `files()` over the older `path()` function?** Three reasons. First, the older `importlib.resources.path(package, resource)` was a context manager that returned a `pathlib.Path` — strictly less capable than `files()` because you could not walk the package root or list siblings. Second, `path()` was deprecated in 3.11 and is scheduled for removal; `files()` is the long-term API. Third, `files()` returns a `Traversable` you can hold onto and reuse — call `read_text` today, `as_file` tomorrow, `iterdir` next week — all on the same object. The older API made you re-look-up the resource for each operation.

## Exercises

1. **Exercise 1 — Read a stdlib resource.** Use `resources.files("json")` and `.joinpath("tool.py").read_text(encoding="utf-8")` to read the `json.tool` module. Print the first 40 characters. `Verify: python -c "import importlib.resources as r; print(r.files('json').joinpath('tool.py').read_text(encoding='utf-8')[:40])"`
2. **Exercise 2 — Bytes vs text.** Read the same file with `read_bytes()` and confirm `len(text_bytes) == len(text_string) == file size`. Explain why they are equal (hint: ASCII file, 1 byte per character). `Verify: python -c "import importlib.resources as r; t=r.files('json').joinpath('tool.py').read_text(encoding='utf-8'); b=r.files('json').joinpath('tool.py').read_bytes(); print(len(t)==len(b), len(t))"`
3. **Exercise 3 — `as_file` extraction.** Use `with resources.as_file(files('json') / 'tool.py') as p:` and print the yielded path. Confirm its `type(p).__name__` is `PosixPath` on disk. `Verify: python -c "import importlib.resources as r; from contextlib import suppress; exec('with r.as_file(r.files(\"json\") / \"tool.py\") as p: print(type(p).__name__, p.exists())')"`
4. **Exercise 4 — List a package.** Write a function `list_package_files(pkg_name: str) -> list[str]` that returns the `.name` of every file (skip subdirectories) inside the package root. Test on `email`. `Verify: python -c "from boardly.db_resources import *; import importlib.resources as r; print(len([c.name for c in r.files('email').iterdir() if c.is_file()]) > 0)"`
5. **Exercise 5 — A zip-packaged resource.** Build a zip containing a package `mypkg` with a `data.txt` file. Add the zip to `sys.path`. Use `files("mypkg") / "data.txt"` to read it, and `as_file` to extract it — confirm the extracted path is a real `PosixPath` pointing at a `tempfile.gettempdir()` location, not inside the zip. `Verify: python -c "import importlib.resources as r; import sys; sys.path.insert(0, '/tmp/mypkg.zip'); print(r.files('mypkg').joinpath('data.txt').read_text(encoding='utf-8'))"`

## Verification

```bash
$ python boardly/db_resources.py | head -2
--- read_text ---
length: 17063 chars

$ python -c "import importlib.resources as r; print(type(r.files('email')).__name__)"
PosixPath

$ python -c "import importlib.resources as r; print(r.files('email').joinpath('charset.py').read_bytes()[:10])"
b'# Copyrigh'
```

## Previously Learned Here

- [[14-importlib/01-import_module]] — `import_module` returns the module object you pass to `files()` (the API accepts either a string name or a module object).

## What's Next

[[14-importlib/03-metadata]] — You can now read a *file* inside a package. The next lesson shows you how to read a package's *metadata* — the version string, the dependencies, the entry points, the author. `importlib.metadata.version("fastapi")` returns `"0.128.0"`; `entry_points(group="boardly.exporters")` is how `boardly` discovers installed exporter plugins at runtime. That is the second half of the resources story — the data file lives next to the package's source, the metadata lives in the `.dist-info` directory next to the package.

- **Lesson 03** — `importlib.metadata` for version, metadata, distribution, entry_points, packages_distributions.
- **Lesson 04** — `importlib.reload`, the development-only hot-reload primitive.
- **[[08-pathlib/00-pathlib-MOC]]** (planned) — `pathlib.Path` is the sibling API; the `Traversable` interface was designed to be drop-in compatible with `Path`'s read methods.

## Sources

- **Python `importlib.resources` documentation** — https://docs.python.org/3/library/importlib.resources.html — accessed 2026-10-23 — the canonical reference for `files()`, `as_file()`, the `Traversable` ABC, and the deprecation notes for the old `path()` / `read_text()` / `read_binary()` module-level functions.
- **Python `importlib.resources.abc.Traversable`** — https://docs.python.org/3/library/importlib.resources.abc.html — accessed 2026-10-23 — the ABC that both `pathlib.Path` and the zip-aware resource handlers implement; reading it confirms which methods you can rely on across packaging forms.
- **PEP 396 — Module Support for Version Numbers** — https://peps.python.org/pep-0396/ — accessed 2026-10-23 — historical context for why package-resource access moved from `os.path.dirname(__file__)` to a formal API; motivates the deprecation story.

## What We Learned

- You can now call `importlib.resources.files("boardly")` and get a `Traversable` for the package root.
- You can now read a bundled file with `.read_text(encoding="utf-8")` or `.read_bytes()` and know the call works whether the package is a folder or a zip.
- You can now use the `as_file()` context manager to extract a resource to a real `pathlib.Path` for consumers (C libraries, subprocesses) that require a real filesystem path.
- You can now recognise the deprecated `read_text(package, resource)` form and rewrite it as `files(package).joinpath(resource).read_text()`.
- You can now explain why `files()` returns `PosixPath` on disk and a different `Traversable` subclass in a zip — and why you should never check `isinstance(result, pathlib.Path)`.
