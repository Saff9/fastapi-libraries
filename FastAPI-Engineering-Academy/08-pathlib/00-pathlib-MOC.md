---
title: pathlib — Map of Content
aliases:
 - pathlib MOC
 - path MOC
tags:
 - moc
 - pathlib
status: complete
---

# Section 08 — `pathlib` — Map of Content

*Object-oriented filesystem paths. `Path("a") / "b" / "c"` instead of `os.path.join("a", "b", "c")`. The modern replacement for `os.path` string-crime.*

**You're at the very beginning of Section 08.**

`pathlib` turns filesystem paths from strings (which you must pass through `os.path.join`, `os.path.exists`, `open`, `os.remove`, `os.path.dirname`, ... 12 different functions) into `Path` objects (which have `.joinpath`, `.exists`, `.read_text`, `.unlink`, `.parent` — methods on the object). The `/` operator joins paths. `Path.home()` and `Path.cwd()` are the two anchors. The class hierarchy: `PurePath` (no I/O — pure string arithmetic) → `Path` (adds `exists()`, `stat()`, `read_text()`, ...). On POSIX: `PurePosixPath` → `PosixPath`; on Windows: `PureWindowsPath` → `WindowsPath`. New code uses `Path`; `os.path` is for legacy.

#pathlib #filesystem #paths

## Lessons

| # | Lesson | What you learn |
|---|---|---|
| 01 | [[08-pathlib/01-Path-Basics]] | `Path(*parts)`, the `/` operator, `.name`/`.stem`/`.suffix`/`.parent`/`.parts`, `.resolve()`. *Canonical.* |
| 02 | [[08-pathlib/02-read-write-text-binary]] | `read_text`/`read_bytes`/`write_text`/`write_bytes`/`open`. The "use Path not `open()`" rule. |
| 03 | [[08-pathlib/03-glob-and-rglob]] | `glob(pattern)`, `rglob(pattern)` (recursive), the `**` pattern, `case_sensitive` (3.12+). |
| 04 | [[08-pathlib/04-mkdir-rmdir-unlink]] | `mkdir(parents=True, exist_ok=True)`, `rmdir` (empty only), `unlink(missing_ok=True)`, `touch`, `rename`/`replace`. |
| 05 | [[08-pathlib/05-PurePath-vs-Path]] | `PurePath` (no I/O — pure string arithmetic), `Path` (adds `exists`/`stat`/`read_text`). Cross-platform path parsing. |
| 06 | [[08-pathlib/06-walk-and-iterdir]] | `iterdir()` (immediate children), `walk()` (3.12+ recursive — the modern `os.walk`), the `rglob("*")` alternative. |
| 07 | [[08-pathlib/07-stat-and-permissions]] | `stat()` → `os.stat_result`, `.st_size`/`.st_mtime`/`.st_mode`, `is_file()`/`is_dir()`/`is_symlink()`, `chmod(mode)`. |

## Reading order

Start with [[08-pathlib/01-Path-Basics]] (the foundation) → [[08-pathlib/02-read-write-text-binary]] (the everyday I/O) → [[08-pathlib/03-glob-and-rglob]] (the file-discovery) → the rest in order. The lessons are self-contained; read any one standalone.

## Concepts first taught here

- **The `Path` object-oriented filesystem API** — taught in Lesson 01.
- **`PurePath` vs `Path`** (path arithmetic vs I/O) — taught in Lesson 05.
- **The `walk()` generator (3.12+)** — taught in Lesson 06.

## Prerequisites

- [[03-contextlib/05-contextvars]] — `Path.open()` is a context manager; the `with` pattern is the prerequisite.
- [[07-itertools/01-chain-and-islice]] — `Path.walk` and `Path.glob` return iterators; understanding lazy iteration is the prerequisite.

## What's next

[[14-importlib/02-resources]] — `importlib.resources.files()` returns a `Traversable` that mirrors `Path`'s interface for files inside packages (which may be zipped). Or jump to [[22-re/01-compile-and-match]] for the regex validation that often pairs with file-path parsing.
