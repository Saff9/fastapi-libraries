---
title: "importlib — Section Map of Content"
aliases:
 - importlib MOC
 - 14-importlib MOC
tags:
 - importlib
 - moc
status: complete
---

# importlib — Section Map of Content

*The Python import machinery exposed as a Python API — `import_module` for dotted-path runtime imports, `resources` for reading package-bundled data files, `metadata` for inspecting installed distributions, `reload` for development-time module re-execution. Four lessons, four stdlib functions, the complete surface of the importlib you will reach for every working day.*

## Lessons in this section

| Lesson | Function(s) | One-sentence summary |
|--------|-------------|------------------------|
| [[14-importlib/01-import_module]] | `importlib.import_module` | Import a module by dotted string name; get the leaf module back (not the top-level package like `__import__`); the public API for plugin loaders. |
| [[14-importlib/02-resources]] | `importlib.resources.files`, `.read_text`, `.read_bytes`, `as_file` | Read a data file (SQL schema, JSON template, binary asset) bundled inside a package, regardless of whether the package is on disk or in a zip. |
| [[14-importlib/03-metadata]] | `importlib.metadata.version`, `metadata`, `entry_points`, `distribution`, `packages_distributions` | Read a distribution's version, metadata, declared entry points, and the import-name to distribution-name mapping; the public alternative to `pkg_resources`. |
| [[14-importlib/04-reload]] | `importlib.reload` | Re-execute a module's code in its existing module object — the development-time primitive with the famous `from x import y` gotcha and the instance-identity trap. |

## The four pillars of `importlib`

`importlib` is the standard library's "Python's own import system, exposed as Python functions" module. Everything you can do with `import x` from source you can do with `importlib` at runtime, plus a few things the import statement cannot do at all (read package data, inspect installed distributions, hot-reload a module). The four pillars:

- **`import_module(name, package=None)`** — the runtime-callable form of `import`. Returns the leaf module of a dotted path; the `package=` argument supports relative imports.
- **`resources` submodule** — read files bundled inside a package, robust to every packaging form (folder on disk, zip, wheel, frozen). The 3.9+ `files()` API returns a `Traversable`; `as_file()` extracts to a real path for C-library consumers.
- **`metadata` submodule** — inspect installed distributions (the things `pip install`'d). Read version strings, full metadata, declared entry points, the import-name-to-distribution-name mapping.
- **`reload(module)`** — re-execute a module's code in its existing module object. A development tool, not a production primitive; the source of the `from x import y` gotcha and the instance-identity trap.

```mermaid
mindmap
  root((importlib))
    import_module
      dotted path -> leaf module
      package= for relative imports
      plugin loading
      beats __import__
    resources
      files(package) -> Traversable
      read_text / read_bytes
      as_file context manager
      zip vs disk
    metadata
      version(name) -> str
      metadata(name) -> Message
      entry_points().select(group=)
      distribution(name) -> Distribution
      packages_distributions()
    reload
      reload(module) -> module
      from x import y gotcha
      instance identity trap
      IPython %autoreload
```

## Suggested reading order

**Beginner (start here):**
1. [[14-importlib/01-import_module]] — the runtime `import`; the gateway to all four pillars.
2. [[14-importlib/02-resources]] — the resource story; what to do when you need to read a SQL or JSON file inside your package.

**Intermediate:**
3. [[14-importlib/03-metadata]] — distribution introspection; the entry-point plugin-discovery protocol.

**Advanced (skip if not on a dev workflow):**
4. [[14-importlib/04-reload]] — development-only hot-reload; the gotcha every Python dev eventually hits.

## Concepts first taught here

- **`import_module` dotted-path return value** — canonical lesson [[14-importlib/01-import_module]].
- **`import_module` vs `__import__` trade-off** — canonical lesson [[14-importlib/01-import_module]].
- **`importlib.resources.files` and the `Traversable` interface** — canonical lesson [[14-importlib/02-resources]].
- **`importlib.resources.as_file` context manager** — canonical lesson [[14-importlib/02-resources]].
- **`importlib.metadata.entry_points` and plugin discovery** — canonical lesson [[14-importlib/03-metadata]].
- **`importlib.reload` and the `from x import y` gotcha** — canonical lesson [[14-importlib/04-reload]].

## Prerequisites

- **Familiarity with the `import` statement** — `import a.b.c` and `from a.b import c` are second nature. The import-statement syntax is what `import_module` exposes as a runtime call.
- **A passing familiarity with `pyproject.toml`** — for lesson 03 (metadata), you have seen an `[project]` table. The lesson walks the syntax.

## What you will be able to do after this section

- Import a module by string name at runtime (config-driven plugin loading).
- Read a data file bundled inside a Python package, robust to every packaging form Python supports.
- Discover pip-installed plugins via entry-point groups, without scanning `sys.path`.
- Translate between import names (`PIL`) and distribution names (`pillow`).
- Explain why `importlib.reload(module)` is a development tool, not a production hot-reload primitive, and why IPython's `%autoreload` is the right answer for the edit-then-rerun workflow.
- Recognise the `from x import y` gotcha and the instance-identity trap when a colleague's "I reloaded, why didn't my change take effect?" question comes up.

## Cross-links

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature` operates on the live objects in a module after `import_module` or `EntryPoint.load()` returns it. `importlib` and `inspect` are siblings: `importlib` loads, `inspect` introspects.
- [[10-inspect/06-How-FastAPI-uses-inspect]] — FastAPI itself uses `importlib.metadata` to read its own version; the same API `boardly` uses to discover exporters.
- [[08-pathlib/00-pathlib-MOC]] (planned) — `pathlib.Path` is the sibling API of `importlib.resources`'s `Traversable`. The `Traversable` interface was designed to be drop-in compatible with `pathlib.Path`'s read methods; the planned 08-pathlib lessons cover `Path` in depth.

## Sources

- **Python `importlib` module documentation** — https://docs.python.org/3/library/importlib.html — accessed 2026-10-23 — the canonical reference for the four functions covered in this section; the docs explicitly recommend `import_module` over `__import__` and note the `from x import y` gotcha for `reload`.
- **Python `importlib.resources` documentation** — https://docs.python.org/3/library/importlib.resources.html — accessed 2026-10-23 — the canonical reference for `files()`, `as_file()`, and the deprecation notes for the old `path()` / `read_text()` module-level functions.
- **Python `importlib.metadata` documentation** — https://docs.python.org/3/library/importlib.metadata.html — accessed 2026-10-23 — the canonical reference for `version`, `metadata`, `entry_points`, `distribution`, `packages_distributions`, and the `PackageNotFoundError` exception.
- **PEP 451 — A Module Spec Type for Python's Import System** — https://peps.python.org/pep-0451/ — accessed 2026-10-23 — the PEP that defined the `ModuleSpec` type `import_module` uses internally; useful background for understanding what `import_module` does between the call and the return.
- **PEP 566 — Metadata for Python Software Packages 2.1** — https://peps.python.org/pep-0566/ — accessed 2026-10-23 — the PEP that defined the modern `METADATA` file format `importlib.metadata` reads.
- **PEP 621 — Storing project metadata in `pyproject.toml`** — https://peps.python.org/pep-0621/ — accessed 2026-10-23 — the PEP that standardised `[project.entry-points."group"]` in `pyproject.toml`; the modern alternative to `setup.py`'s `entry_points=` argument.
- **IPython `autoreload` extension documentation** — https://ipython.readthedocs.io/en/stable/config/extensions/#autoreload — accessed 2026-10-23 — the production-quality hot-reload mechanism for IPython / Jupyter sessions; the right way to get "edit, re-run cell" semantics.

## Where to start

You are in the right section. Start with [[14-importlib/01-import_module]] — it covers the runtime `import` and the gateway to every other lesson in this section.
