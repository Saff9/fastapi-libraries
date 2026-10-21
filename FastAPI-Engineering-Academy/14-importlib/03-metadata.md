---
title: "Lesson 03: metadata — version, metadata, entry_points"
aliases:
 - importlib.metadata
 - entry_points
 - packages_distributions
 - distribution
tags:
 - importlib
 - metadata
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[14-importlib/01-import_module]]"
related_lessons:
 - "[[14-importlib/02-resources]]"
 - "[[14-importlib/04-reload]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
---

# Lesson 03: metadata — version, metadata, entry_points

*How `boardly`'s exporter registry asks `pip`-installed plugins `who is out there?` — `entry_points(group="boardly.exporters")` returns every distribution that declared itself a boardly exporter in its `pyproject.toml`, with zero imports.*

**You're at the very beginning of Section 14's third lesson.**

You can import a module by name (lesson 01) and read a file inside a package (lesson 02). Now you need to ask a *distribution* questions: what is its version, what are its dependencies, what plugins has it registered? `importlib.metadata` is the public API for inspecting installed distributions — the `pip install`'d packages on your system. By the end of this lesson you can read FastAPI's version, list the requirements, and walk an entry-point group to discover plugins. Take your time. Type every example. **This is how you learn.**

#importlib #metadata

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `importlib.metadata.version`** — pass a distribution name, get back the version string, handle `PackageNotFoundError` when the distribution is not installed.
2. **Read `importlib.metadata.metadata`** — get the email-message-format `PackageMetadata` object, walk its headers (`Name`, `Version`, `Requires-Dist`, `Summary`).
3. **Discover plugins with `entry_points`** — call `entry_points().select(group="boardly.exporters")`, load each `EntryPoint`, call `.load()` to get the underlying callable.
4. **Map import names to distribution names** — use `packages_distributions()` to answer "what distribution provides `PIL`?" (`pillow`) and "what distribution provides `pydantic_core`?" (`pydantic_core`).
5. **Inspect a `Distribution` object** — call `distribution("fastapi")` and read its `.version`, `.metadata`, `.entry_points` attributes.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `importlib.import_module`. `entry_points`'s `EntryPoint.load()` calls `import_module` under the hood; knowing how `import_module` returns the leaf module makes the load semantics predictable. See [[14-importlib/01-import_module]].
- **A passing familiarity with `pyproject.toml`** — you have seen an `[project]` table and an `[project.entry-points."some.group"]` section. If not, the lesson walks the syntax; you do not need to be fluent.
- **About 30–40 minutes of focused time.**

**The most common gap: confusing the *distribution* name with the *import* name.** The distribution is what `pip install`'d (e.g., `pip install pillow`, `pip install python-dateutil`). The import name is what you write in code (`import PIL`, `import dateutil`). They are often different (`PIL` vs `pillow`, `dateutil` vs `python-dateutil`) and occasionally the same (`fastapi` vs `fastapi`). `importlib.metadata.version("pillow")` works; `importlib.metadata.version("PIL")` raises `PackageNotFoundError`. The two namespaces are independent, and `packages_distributions()` is the bridge between them.

## The Problem

Here is the bug. `boardly` ships an exporter API: any package can register itself as a "boardly exporter" and `boardly` will discover it at startup. The naive approach hard-codes the list:

```python
# boardly/exporters/__init__.py — the broken approach
from boardly.exporters.csv import CSVExporter
from boardly.exporters.json import JSONExporter
# Every new exporter is a code change in this file. Yuck.
```

That works for the exporters `boardly` itself ships. It fails the moment a third party writes `boardly-exporter-parquet` and wants `boardly` to find it without forking the core. The third-party package cannot edit `boardly/exporters/__init__.py` — it does not have access to that file.

The standard library's answer is entry points. A distribution declares an entry point in its `pyproject.toml`:

```toml
# pyproject.toml — the third-party exporter's metadata
[project]
name = "boardly-exporter-parquet"
version = "0.1.0"

[project.entry-points."boardly.exporters"]
parquet = "boardly_exporter_parquet:ParquetExporter"
```

The `[project.entry-points."boardly.exporters"]` table says: "this distribution declares one entry point in the group `boardly.exporters`, named `parquet`, pointing at the `ParquetExporter` object in the `boardly_exporter_parquet` module." When the distribution is installed, `pip` writes the entry point into the distribution's `.dist-info` directory. `importlib.metadata.entry_points(group="boardly.exporters")` reads every distribution's `.dist-info` and returns the matching entry points. `boardly` discovers the third-party exporter with zero imports of `boardly`'s own code.

## The Code

```python
# boardly/plugins/exporter_registry.py
"""Discover boardly exporters via importlib.metadata entry points."""
from __future__ import annotations
import importlib.metadata as md
from dataclasses import dataclass


@dataclass
class ExporterInfo:
    name: str
    distribution: str
    factory: object


def discover_exporters(group: str = "boardly.exporters") -> list[ExporterInfo]:
    """Return every exporter declared under the given entry-point group."""
    found: list[ExporterInfo] = []
    for ep in md.entry_points().select(group=group):
        try:
            factory = ep.load()                 # the dotted object from `module:attr`
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip exporter {ep.name!r}: {exc}")
            continue
        found.append(ExporterInfo(
            name=ep.name,
            distribution=ep.dist.name if ep.dist else "(unknown)",
            factory=factory,
        ))
    return found


def fastapi_version() -> str:
    """Return the installed FastAPI version, or raise if missing."""
    return md.version("fastapi")


def requires_python(name: str) -> str | None:
    """Return the package's Requires-Python constraint, or None."""
    return md.metadata(name).get("Requires-Python")


if __name__ == "__main__":
    # 1. version()
    print("--- md.version ---")
    print(f"fastapi version: {fastapi_version()}")
    try:
        md.version("nonexistent_xyz_pkg")
    except md.PackageNotFoundError as exc:
        print(f"missing pkg error: {exc}")

    # 2. metadata()
    print("\n--- md.metadata ---")
    meta = md.metadata("fastapi")
    print(f"type:   {type(meta).__name__}")
    print(f"Name:   {meta['Name']}")
    print(f"Version: {meta['Version']}")
    print(f"Summary: {meta.get('Summary')}")
    print(f"Requires-Python: {requires_python('fastapi')}")
    print("Requires-Dist (first 3):")
    for line in (meta.get_all("Requires-Dist") or [])[:3]:
        print(f"  {line}")

    # 3. entry_points()
    print("\n--- md.entry_points ---")
    all_eps = md.entry_points()
    print(f"type: {type(all_eps).__name__}")
    cs = all_eps.select(group="console_scripts")
    print(f"console_scripts count: {len(cs)}")
    for ep in list(cs)[:3]:
        print(f"  name={ep.name!r}  value={ep.value!r}  group={ep.group!r}")

    # 4. distribution()
    print("\n--- md.distribution ---")
    dist = md.distribution("fastapi")
    print(f"type:           {type(dist).__name__}")
    print(f"dist.version:   {dist.version}")
    print(f"dist.metadata['Name']: {dist.metadata['Name']}")
    print(f"dist.entry_points count: {len(list(dist.entry_points))}")
    print(f"dist.files (first 3):")
    for p in list(dist.files or [])[:3]:
        print(f"  {p}  ({type(p).__name__})")
    record_text = dist.read_text("RECORD")
    print(f"dist.read_text('RECORD') first 60 chars: {(record_text or '')[:60]!r}")

    # 5. packages_distributions()
    print("\n--- md.packages_distributions ---")
    pd = md.packages_distributions()
    print(f"total mappings: {len(pd)}")
    for import_name in ("PIL", "fastapi", "pydantic_core", "email_validator"):
        print(f"  {import_name!r} -> {pd.get(import_name)}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 4–12: Imports and the `ExporterInfo` dataclass

```python
import importlib.metadata as md
from dataclasses import dataclass


@dataclass
class ExporterInfo:
    name: str
    distribution: str
    factory: object
```

`importlib.metadata` is a submodule of `importlib`. It is the public face of Python's distribution-inspection API; before 3.8 it existed as the third-party `importlib_metadata` backport, which is still installable for older Python. On 3.8+ it is in the stdlib, so the backport is unnecessary. (If you see `import importlib_metadata` in older code, that is the pre-3.8 backport — replace with `import importlib.metadata`.)

`ExporterInfo` is the registry entry: the entry point's name (e.g., `"csv"`, `"json"`, `"parquet"`), the distribution that declared it (for logging — "exporter `parquet` from `boardly-exporter-parquet`"), and the factory object itself (a class or callable that produces an exporter instance). The `factory: object` annotation is intentionally loose for the same reason as `LoadedRouter.router` in lesson 01 — keeping the registry free of a hard `boardly.exporters` import boundary lets the registry sit in a low-level module that any plugin can subclass.

### Lines 15–27: `discover_exporters` — the entry-point walk

```python
def discover_exporters(group: str = "boardly.exporters") -> list[ExporterInfo]:
    found: list[ExporterInfo] = []
    for ep in md.entry_points().select(group=group):
        try:
            factory = ep.load()
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip exporter {ep.name!r}: {exc}")
            continue
        found.append(ExporterInfo(
            name=ep.name,
            distribution=ep.dist.name if ep.dist else "(unknown)",
            factory=factory,
        ))
    return found
```

This is the core pattern. `md.entry_points()` returns an `EntryPoints` collection of every entry point in every installed distribution. The `.select(group=...)` method narrows to one group — `boardly.exporters`, `console_scripts`, `pytest11`, `babel.extractors`, or whatever group you declared in `pyproject.toml`.

The `EntryPoints.select` method is the modern 3.10+ API. `entry_points(group=...)` is functionally equivalent on 3.10+ — the function signature is `entry_points(**params) -> EntryPoints`, and the body just calls `EntryPoints(eps).select(**params)`. Both forms return the same `EntryPoints` object. The `.select` form is what we use here because it composes (you can store the unfiltered `EntryPoints` once and call `.select` on it multiple times for different groups). The historical deprecation is *not* the kwarg form — it is the *3.8/3.9 form*, where `entry_points()` returned a `dict` keyed by group name and you indexed it like `entry_points()["console_scripts"]`. That dict-returning form was deprecated in 3.10 and **removed in 3.12**; code that still treats the result as a dict hits two distinct errors on 3.12 — `KeyError` on bracket-indexing by group name (because `EntryPoints.__getitem__` looks up by *entry-point name*, not by group) and `AttributeError` on `.get` (because `EntryPoints`, a `tuple` subclass, has no `get` method). The `.select(group=...)` (or the equivalent `entry_points(group=...)`) form is the modern replacement.

For each `EntryPoint`, `ep.load()` does the dotted-path import: `boardly_exporter_parquet:ParquetExporter` is split on the colon, the left side is `import_module`'d (lesson 01), the right side is `getattr`'d off the resulting module. The result is the live object — typically a class. If the module is missing (`ImportError`) or the attribute does not exist (`AttributeError`), the load fails. Catching both and logging the failure keeps one broken exporter from breaking startup — same pattern as the plugin loader in lesson 01.

`ep.dist` is the `Distribution` that declared the entry point (3.9+ attribute). It is `None` when the entry point was registered through some legacy path that does not carry distribution context. The `if ep.dist else "(unknown)"` guard handles that case — usually the entry point's source distribution is always known, but the guard is the safety net.

**Why `entry_points(group=...)` over scanning `sys.path` for `boardly_exporter_*` directories?** Three reasons. First, the entry-point mechanism is the official, documented extension protocol — third-party packages know about it, so you do not need to invent a new protocol. Second, scanning `sys.path` is brittle: it misses zip-installed packages, namespace packages, and packages installed with non-standard schemes (`--target`, editable installs with `.pth` files). `entry_points` reads the canonical metadata that `pip` writes into `.dist-info` directories — the same metadata `pip list` uses. Third, the entry-point mechanism is opt-in: a package declares itself a boardly exporter by writing a `pyproject.toml` table, not by being named a certain way. That avoids false positives — packages whose names happen to match the prefix but were never meant to be boardly exporters.

### Lines 30–39: `fastapi_version` and `requires_python` — thin wrappers

```python
def fastapi_version() -> str:
    return md.version("fastapi")


def requires_python(name: str) -> str | None:
    return md.metadata(name).get("Requires-Python")
```

`md.version("fastapi")` returns the version string — `"0.128.0"`. If `fastapi` is not installed, it raises `md.PackageNotFoundError`, which is the canonical "this package is not installed" exception. The function above lets the exception propagate; callers who want graceful handling should `try/except PackageNotFoundError`. The exception's message is `"No package metadata was found for fastapi"` — actionable and specific.

`md.metadata(name)` returns a `PackageMetadata` object — on 3.12, the concrete class is `email.message.Message`, the same class email-message parsing uses. That choice is deliberate: a distribution's `METADATA` file is an RFC 822-style email message with headers like `Name:`, `Version:`, `Requires-Dist:`, `Summary:`. The `Message` class already knows how to parse that format. `meta["Version"]` reads the `Version` header; `meta.get("Requires-Python")` reads the `Requires-Python` header (or returns `None`); `meta.get_all("Requires-Dist")` reads every `Requires-Dist` header (a distribution can have many) into a list.

`requires_python` returns `None` when the package's metadata has no `Requires-Python` field. That is a real possibility — packages without a Python version constraint simply do not declare one. The `Optional[str]` return type reflects that.

### Lines 42–49: The `version()` demo

```python
if __name__ == "__main__":
    print("--- md.version ---")
    print(f"fastapi version: {fastapi_version()}")
    try:
        md.version("nonexistent_xyz_pkg")
    except md.PackageNotFoundError as exc:
        print(f"missing pkg error: {exc}")
```

`md.version("fastapi")` returns `"0.128.0"` on the test machine — the exact string `fastapi.__version__` would give, but without importing `fastapi`. The "without importing" part is the point: a startup version check should not pull FastAPI's entire import tree into memory just to read three characters. `importlib.metadata` reads the `.dist-info/METADATA` file directly, no code execution.

`md.version("nonexistent_xyz_pkg")` raises `md.PackageNotFoundError`. The exception is importable directly from `importlib.metadata` — you do not need to import it from a deeper submodule. Catch it specifically; do not catch `Exception` because the version-lookup path can raise `ValueError` (malformed version string) and you want that to surface.

### Lines 52–62: The `metadata()` demo

```python
print("--- md.metadata ---")
meta = md.metadata("fastapi")
print(f"type:   {type(meta).__name__}")
print(f"Name:   {meta['Name']}")
print(f"Version: {meta['Version']}")
print(f"Summary: {meta.get('Summary')}")
print(f"Requires-Python: {requires_python('fastapi')}")
print("Requires-Dist (first 3):")
for line in (meta.get_all("Requires-Dist") or [])[:3]:
    print(f"  {line}")
```

The metadata object is an `email.message.Message`. Its interface is dict-like for single headers (`meta["Name"]`) and `get`-like for optional ones (`meta.get("Summary")`). For multi-valued headers — `Requires-Dist`, `Classifier`, `Project-URL` — use `.get_all(name)` which returns a list of strings or `None`.

The `Requires-Dist` headers tell you the package's runtime dependencies: `starlette<0.51.0,>=0.40.0`, `pydantic>=2.7.0`, `typing-extensions>=4.8.0`. That is the metadata `pip` itself uses to resolve dependencies. `importlib.metadata` is the read-only, non-installing half of `pip`'s machinery — `pip` reads the same `.dist-info` files, but it also resolves and downloads; `importlib.metadata` only reads.

**Why is `metadata()` an email-message instead of a dict?** Because the PEP 566 metadata format is RFC 822 email-message-style headers. Reusing the `email.message.Message` class gave the stdlib a parser for free, kept the on-disk format a stable text format that humans can read with `cat METADATA`, and made multi-valued headers (multiple `Classifier:` lines, multiple `Requires-Dist:` lines) work correctly out of the box. The cost is the slightly clunky `meta.get_all("Requires-Dist")` instead of `meta["requires_dist"]` — but the headers are named exactly as they appear in the file, which makes the round-trip obvious.

### Lines 65–72: The `entry_points()` demo

```python
print("--- md.entry_points ---")
all_eps = md.entry_points()
print(f"type: {type(all_eps).__name__}")
cs = all_eps.select(group="console_scripts")
print(f"console_scripts count: {len(cs)}")
for ep in list(cs)[:3]:
    print(f"  name={ep.name!r}  value={ep.value!r}  group={ep.group!r}")
```

`md.entry_points()` returns an `EntryPoints` collection. On 3.10+, that collection supports `.select(group=..., name=...)` for filtering. Without arguments, `.select()` returns every entry point in every distribution. With `group="console_scripts"`, it returns the entry points `pip install`'d console scripts (the binaries that land in `~/.local/bin/`).

Each `EntryPoint` has three primary attributes: `.name` (e.g., `"pytest"`, `"pip"`), `.value` (e.g., `"pytest:main"`, `"pip._internal.cli.main:main"`), and `.group` (e.g., `"console_scripts"`, `"pytest11"`). The `.value` is the `module:attribute` dotted form — split on the colon, `import_module` the left side, `getattr` the right side. `ep.load()` does that for you and returns the live object.

`EntryPoint` also has `.dist` (3.9+), the `Distribution` that declared the entry point. That lets you log "found pytest from pytest 8.0.0" by reading `ep.dist.version` without an extra `md.version("pytest")` call.

### Lines 75–83: The `distribution()` demo

```python
print("--- md.distribution ---")
dist = md.distribution("fastapi")
print(f"type:           {type(dist).__name__}")
print(f"dist.version:   {dist.version}")
print(f"dist.metadata['Name']: {dist.metadata['Name']}")
print(f"dist.entry_points count: {len(list(dist.entry_points))}")
print(f"dist.files (first 3):")
for p in list(dist.files or [])[:3]:
    print(f"  {p}  ({type(p).__name__})")
record_text = dist.read_text("RECORD")
print(f"dist.read_text('RECORD') first 60 chars: {(record_text or '')[:60]!r}")
```

`md.distribution("fastapi")` returns a `Distribution` object — on 3.12, the concrete class is `PathDistribution`, which wraps the `.dist-info` directory on disk. The `Distribution` is the most general API: it gives you `.version`, `.metadata`, `.entry_points`, `.files`, and `.read_text(filename)`.

`dist.version` is the same string `md.version("fastapi")` returns; they share the implementation. `dist.metadata` is the same `Message` object `md.metadata("fastapi")` returns. `dist.entry_points` is the entry points this specific distribution declared (without the global select filter). The pattern is: `md.version`, `md.metadata`, and `md.entry_points` are convenience wrappers that internally find the `Distribution` for the named package and read its attributes. Calling `md.distribution(name)` directly is the lower-level form when you want multiple attributes of one package — one lookup instead of several.

`dist.files` returns a list of `PackagePath` objects (a `pathlib.Path` subclass), one per file the distribution installed. Each `PackagePath` knows the file's location relative to its `.dist-info/RECORD` entry; `path.locate()` returns the absolute `PosixPath` on disk. `pip uninstall` walks the same list to know what to delete. `importlib.metadata` exposes it because some tools (security scanners, license auditors, reproducibility checkers) need to enumerate the installed files. The list may be `None` for editable installs (`pip install -e .`), where `RECORD` is incomplete because the files live in your source tree, not `site-packages` — the `dist.files or []` guard in the loop above handles that.

`dist.read_text(filename)` reads a file directly from the `.dist-info` directory. `"RECORD"`, `"METADATA"`, `"INSTALLER"`, `"LICENSE"` are typical filenames. The method is the robust one-call form for getting a dist-info file's contents — robust because `read_text` works whether the distribution is installed normally, in a zip, or with `--target`, whereas a `pathlib.Path` you build yourself may not exist on disk.

### Lines 86–92: The `packages_distributions()` demo

```python
print("--- md.packages_distributions ---")
pd = md.packages_distributions()
print(f"total mappings: {len(pd)}")
for import_name in ("PIL", "fastapi", "pydantic_core", "email_validator"):
    print(f"  {import_name!r} -> {pd.get(import_name)}")
```

`md.packages_distributions()` returns a `dict` mapping import name (top-level package) to a list of distribution names. Most import names map to a single distribution (`"fastapi" -> ["fastapi"]`, `"PIL" -> ["pillow"]`); a few import names map to multiple distributions when namespace packages are involved (`"zope"` may map to several distributions that each contribute subpackages). The list-of-distributions return type accommodates the namespace-package case; for the common case, the list has one element.

This is the bridge between import name and distribution name — the answer to "which distribution provides `import PIL`?" (`pillow`) and "which distribution provides `import dateutil`?" (`python-dateutil`). It is 3.10+; on 3.8/3.9 you have to walk `importlib.metadata.distributions()` and read each `Distribution.top_level` attribute. The `packages_distributions` function is the curated, ready-to-use form.

**Why is the mapping import-name -> list-of-distribution-names instead of distribution-name -> import-name?** Because the question you typically ask is "given this import name, what distribution do I need to `pip install`?" — the reverse direction. `import PIL` fails with `ModuleNotFoundError`, you grep `packages_distributions()` for `PIL`, you find `["pillow"]`, you `pip install pillow`. The mapping is indexed the way it is queried.

## Execution Trace

```bash
$ python boardly/plugins/exporter_registry.py
--- md.version ---
fastapi version: 0.128.0
missing pkg error: No package metadata was found for nonexistent_xyz_pkg

--- md.metadata ---
type:   Message
Name:   fastapi
Version: 0.128.0
Summary: FastAPI framework, high performance, easy to learn, fast to code, ready for production
Requires-Python: >=3.9
Requires-Dist (first 3):
  starlette<0.51.0,>=0.40.0
  pydantic>=2.7.0
  typing-extensions>=4.8.0

--- md.entry_points ---
type: EntryPoints
console_scripts count: 144
  name='scour'  value='scour.scour:run'  group='console_scripts'
  name='jlpm'  value='jupyterlab.jlpmapp:main'  group='console_scripts'
  name='jupyter-lab'  value='jupyterlab.labapp:main'  group='console_scripts'

--- md.distribution ---
type:           PathDistribution
dist.version:   0.128.0
dist.metadata['Name']: fastapi
dist.entry_points count: 1
dist.files (first 3):
  ../../../bin/fastapi  (PackagePath)
  fastapi-0.128.0.dist-info/INSTALLER  (PackagePath)
  fastapi-0.128.0.dist-info/METADATA  (PackagePath)
dist.read_text('RECORD') first 60 chars: '../../../bin/fastapi,sha256=jAg-hwxMNz9RT0FeVwoTpqBpQa2Vu0JQ'

--- md.packages_distributions ---
total mappings: 469
  'PIL' -> ['pillow']
  'fastapi' -> ['fastapi']
  'pydantic_core' -> ['pydantic_core']
  'email_validator' -> ['email-validator']
```

## Common Mistakes

### Mistake 1: Passing the *import* name to `version()`

```python
import importlib.metadata as md
md.version("PIL")           # PackageNotFoundError
md.version("email_validator")  # PackageNotFoundError (distribution is "email-validator")
```

**Symptom:** `PackageNotFoundError: No package metadata was found for PIL`.
**Why:** `version()` takes the *distribution* name, not the import name. The distribution name is what `pip install`'d the package as. For `pillow` the import name is `PIL` and the distribution name is `pillow`; for `email-validator` the import name is `email_validator` (underscore) and the distribution name is `email-validator` (hyphen).
**Fix:** Use `md.packages_distributions()` to translate import name → distribution name first, then call `version()` on the distribution name. Or just remember the common cases (`PIL`/`pillow`, `dateutil`/`python-dateutil`, `email_validator`/`email-validator`, `sklearn`/`scikit-learn`).

### Mistake 2: Treating `entry_points()` as a `dict` (the 3.8/3.9 form, removed in 3.12)

```python
eps = md.entry_points()
scripts = eps["console_scripts"]   # 3.8/3.9 form — KeyError on 3.12
# or
scripts = eps.get("console_scripts", [])  # AttributeError on 3.12
```

**Symptom:** Two distinct errors. (a) `KeyError: 'console_scripts'` from the bracket-indexing form. (b) `AttributeError: 'EntryPoints' object has no attribute 'get'` from the `.get()` form. Slicing with an integer (`eps[0]`) also fails — `KeyError: 0`.
**Why:** On Python 3.8 and 3.9, `entry_points()` returned a `dict` keyed by group name, so `eps["console_scripts"]` returned a `list[EntryPoint]` and `eps.get("group", [])` worked. The dict-returning form was deprecated in 3.10 and **removed in 3.12** — `entry_points()` now returns an `EntryPoints` object (a `tuple` subclass whose `__getitem__` is wired through `.select(name=name)` and looks up an entry point *by name*, not by group and not by index). Bracket-indexing by group name therefore raises `KeyError(name)`; `.get` does not exist (tuples have no `get` method); integer indexing raises `KeyError(0)`.
**Fix:** Use `.select(group="...")` (or the equivalent `entry_points(group="...")`): `scripts = md.entry_points().select(group="console_scripts")`. To get a single entry by name: `md.entry_points().select(name="pytest")` — but be aware this returns an `EntryPoints` (possibly empty), so iterate it or call `next(iter(...), None)`. To get a list, write `list(eps.select(group="..."))`.

### Mistake 3: Forgetting `PackageNotFoundError` on optional-dependency code paths

```python
def get_fastapi_version():
    return md.version("fastapi")     # raises if fastapi not installed
```

**Symptom:** The function works on the developer's machine (FastAPI is installed) and crashes in production where FastAPI may be installed under a different distribution or not at all (e.g., a static-analysis tool that does not need to import FastAPI).
**Why:** `md.version` raises `PackageNotFoundError` when the distribution is not installed. The exception's MRO is `PackageNotFoundError -> ModuleNotFoundError -> ImportError -> Exception`, so it *is* a subclass of `ImportError` — a broad `except ImportError` will catch it. But the recommendation is still to catch the specific `PackageNotFoundError` because a broader `except ImportError` may also swallow real import failures (broken plugin module, syntax error in the target package) that you wanted to surface. Catch the narrow exception, let the broader ones propagate.
**Fix:** Catch `md.PackageNotFoundError` specifically if the function should be tolerant:
```python
try:
    return md.version("fastapi")
except md.PackageNotFoundError:
    return "(fastapi not installed)"
```

## Engineering Trade-Offs

**Decision:** Use `importlib.metadata.entry_points(group=...)` for every plugin-discovery problem. Never scan `sys.path` for prefix-named modules.
**Both sides:** The alternative is `pkgutil.iter_modules(sys.path)` filtered by name prefix. It works in a development checkout, finds new plugins without a `pyproject.toml` entry, and avoids the `.dist-info` machinery. It also misses zip-installed packages, namespace packages, and any plugin installed with `--target` or as an editable install. The entry-point mechanism reads the canonical metadata `pip` itself uses; it is the official plugin-discovery protocol for the Python ecosystem. Pytest (`pytest11` group), Babel (`babel.extractors`), Sphinx (`sphinx.builders`), pip itself (`pipx` uses entry points) — every major tool uses entry points. So should you.
**Commitment:** `boardly` declares its `boardly.exporters` group in `pyproject.toml` and discovers exporters via `entry_points().select(group="boardly.exporters")`. Third-party exporter packages declare themselves by adding a `[project.entry-points."boardly.exporters"]` table to their own `pyproject.toml`. No `sys.path` scanning in `boardly`'s core.

**Why `importlib.metadata` over the `pkg_resources` API?** Three reasons. First, `importlib.metadata` is in the stdlib (3.8+) — no `setuptools` dependency. `pkg_resources` is part of `setuptools`, which is heavy and increasingly not assumed to be installed. Second, the API is smaller and faster: `entry_points()` returns a frozen `EntryPoints` collection rather than `pkg_resources`'s working-set machinery. Third, the PEP 566 / PEP 621 / PEP 660 ecosystem has converged on `importlib.metadata` as the canonical reader; `pip`'s `--dry-run` introspection, `build`'s metadata reading, and tooling like `pip-audit` all use `importlib.metadata`. `pkg_resources` is the legacy path; new code should not depend on it.

## Exercises

1. **Exercise 1 — Version of a stdlib-adjacent package.** Call `md.version("pip")` and `md.version("setuptools")`; print both. Then call `md.version("no_such_pkg")` and confirm you get `PackageNotFoundError`. `Verify: python -c "import importlib.metadata as md; print(md.version('pip'), md.version('setuptools'))"`
2. **Exercise 2 — Read metadata headers.** Use `md.metadata("pydantic")` to print the package's `Name`, `Version`, `Summary`, and `Requires-Python`. Then use `.get_all("Requires-Dist")` to list the first three runtime dependencies. `Verify: python -c "import importlib.metadata as md; m=md.metadata('pydantic'); print(m['Name'], m['Version'], m.get('Requires-Python'))"`
3. **Exercise 3 — List entry points.** Call `md.entry_points().select(group="pytest11")` and print the first three entry points' names. (If pytest is not installed, fall back to `group="console_scripts"`.) Explain what the `pytest11` group is for. `Verify: python -c "import importlib.metadata as md; eps=md.entry_points().select(group='pytest11') or md.entry_points().select(group='console_scripts'); print(len(eps) > 0)"`
4. **Exercise 4 — Translate import to distribution.** Use `md.packages_distributions()` to look up `"PIL"`, `"dateutil"`, and `"yaml"` (if installed). Write a function `distribution_for(import_name: str) -> str | None` that returns the first distribution name for the import name. `Verify: python -c "from boardly.plugins.exporter_registry import *; import importlib.metadata as md; pd=md.packages_distributions(); print(pd.get('PIL'))"`
5. **Exercise 5 — Register an entry point.** Create a tiny package `boardly_exporter_dummy` with a `pyproject.toml` declaring an entry point in `boardly.exporters` named `dummy` pointing at `boardly_exporter_dummy:DummyExporter`. `pip install -e .` it. Run `discover_exporters()` and confirm `dummy` appears in the result. `Verify: python -c "from boardly.plugins.exporter_registry import discover_exporters; print([e.name for e in discover_exporters()])"`

## Verification

```bash
$ python boardly/plugins/exporter_registry.py | head -3
--- md.version ---
fastapi version: 0.128.0
missing pkg error: No package metadata was found for nonexistent_xyz_pkg

$ python -c "import importlib.metadata as md; print(md.version('fastapi'))"
0.128.0

$ python -c "import importlib.metadata as md; print(type(md.entry_points()).__name__)"
EntryPoints
```

## Previously Learned Here

- [[10-inspect/06-How-FastAPI-uses-inspect]] — FastAPI itself uses `importlib.metadata` (via `typer`, via `click`) to read its own version and entry points; the same API `boardly` uses to discover exporters.
- [[14-importlib/01-import_module]] — `EntryPoint.load()` calls `import_module` under the hood for the module half of `module:attribute`. Lesson 01 covers the dotted-path semantics.

## What's Next

[[14-importlib/04-reload]] — You can import modules, read resources, discover distributions. The last lesson covers `importlib.reload(module)` — re-executing a module's code in its existing module object. That is the development-time hot-reload primitive, the IPython `%reload_ext` mechanism, and the source of one of the most common "why didn't my change take effect?" confusions. It is also the one `importlib` function you almost never call in production.

- **Lesson 04** — `importlib.reload`, the `from x import y` gotcha, the IPython use case.
- **[[10-inspect/01-signature-and-Parameter]]** — `inspect.signature` works on objects from any module, including modules loaded via `import_module` or `EntryPoint.load()`. The inspect section is the natural next deep dive after `importlib`.

## Sources

- **Python `importlib.metadata` documentation** — https://docs.python.org/3/library/importlib.metadata.html — accessed 2026-10-23 — the canonical reference for `version`, `metadata`, `entry_points`, `distribution`, `packages_distributions`, and the `PackageNotFoundError` exception.
- **Python `importlib.metadata` — `EntryPoint` objects** — https://docs.python.org/3/library/importlib.metadata.html#entry-points — accessed 2026-10-23 — the reference for `EntryPoint.load()`, `EntryPoint.name`, `EntryPoint.value`, `EntryPoint.group`, and `EntryPoint.dist`.
- **PEP 566 — Metadata for Python Software Packages 2.1** — https://peps.python.org/pep-0566/ — accessed 2026-10-23 — the PEP that defined the modern `METADATA` file format `importlib.metadata` reads; explains why the format is email-message-style headers.
- **PEP 621 — Storing project metadata in `pyproject.toml`** — https://peps.python.org/pep-0621/ — accessed 2026-10-23 — the PEP that standardised `[project.entry-points."group"]` in `pyproject.toml`; the modern alternative to `setup.py`'s `entry_points=` argument.

## What We Learned

- You can now call `importlib.metadata.version("fastapi")` and get the version string, and handle `PackageNotFoundError` when the distribution is missing.
- You can now read `importlib.metadata.metadata("fastapi")` and walk its email-message-style headers — `Name`, `Version`, `Summary`, `Requires-Python`, `Requires-Dist`.
- You can now discover plugins with `entry_points().select(group="boardly.exporters")` and call `EntryPoint.load()` to get the live factory object.
- You can now translate import names to distribution names via `packages_distributions()` and explain why `PIL` -> `pillow` and `email_validator` -> `email-validator`.
- You can now explain why `importlib.metadata` is the modern stdlib replacement for `pkg_resources`, and why new plugin-discovery code should use entry points rather than `sys.path` scanning.
