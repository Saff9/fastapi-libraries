---
title: "Lesson 01: Path Basics"
aliases:
 - pathlib.Path
 - Path
 - Path basics
 - the / operator on Path
 - Path.home Path.cwd
tags:
 - pathlib
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[08-pathlib/02-read-write-text-binary]]"
 - "[[08-pathlib/03-glob-and-rglob]]"
first_taught_in: "08-pathlib/01-Path-Basics"
---

# Lesson 01: Path Basics

*Why `boardly`'s `data_dir = boardly_root / "data" / "projects.json"` is one line, on every OS, with no `os.path.join` in sight — and why the accessors on that one object replace nine `os.path.*` functions.*

**You're at the very beginning of Section 08.**

You have written `os.path.join("boardly", "data", "projects.json")` and felt the friction. You have written `os.path.dirname(...)` and `os.path.basename(...)` and `os.path.splitext(...)` and noticed that each one returns a *string* — a string you have to re-wrap in another `os.path.*` call the moment you want to do anything more with it. You have written `with open(os.path.join(...)) as f:` and watched the path string vanish into the file object, never to be inspected again. The `pathlib.Path` type fixes all of that. It is one object that holds the path string *and* the operations you want to do on it — join, split, resolve, read, write, glob — chained as methods, on every operating system, with the same spelling. Take your time. Type every example. **This is how you learn.**

#pathlib #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `Path` from segments** — write `Path("a", "b", "c")` and `Path("a/b/c")`, explain that on POSIX the concrete class is `PosixPath` and on Windows it is `WindowsPath`, and that both subclass `PurePath` (the no-I/O string-algebra base) and `Path` (the I/O-capable subclass).
2. **Join paths with the `/` operator** — write `Path("/") / "a" / "b"` and explain that `Path.__truediv__` calls the same internal `_from_parts_join` machinery that the constructor uses, returning a *new* `Path` (because `Path` is immutable).
3. **Use the class methods `Path.home()` and `Path.cwd()`** — call them and explain that they read `$HOME` and `getcwd(2)` respectively, returning a `Path` so the result composes with the `/` operator.
4. **Read the seven accessors** — `.name`, `.stem`, `.suffix`, `.suffixes`, `.parent`, `.parents`, `.anchor`, and `.parts` — and explain what each one returns on a relative path, an absolute path, and a multi-suffix path like `archive.2024.json`.
5. **Resolve a path** with `.resolve(strict=False)` — collapse `.` and `..`, make the path absolute, and explain why `strict=True` (the historical default) raises `FileNotFoundError` if the path does not exist.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. This lesson writes `path: Path` annotations on helper functions; you need to be comfortable reading an annotation as a contract.
- **A typed model to attach paths to** — [[06-dataclasses/01-dataclass-Basics]]. The later lessons in this section write `data_dir: Path` on a `ProjectRepo` dataclass; this lesson is the foundation.
- **About 30–45 minutes of focused time.**

**The most common gap: treating `Path` as a fancier `str`.**

It is not. `Path` is an object that *holds* a string and *exposes operations*. The single biggest mistake students make is writing `str(Path("a/b"))` everywhere "to be safe" — and then immediately losing the methods they bought the type for. `Path` is the public type; you convert to `str` only at the boundary (a system call, a `subprocess` arg, an `os.*` function that has not been modernised). Inside your code, the path stays a `Path`. That is the whole lesson's worth of decisions in one sentence.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/paths/bad_paths.py — the bad old days
import os.path

DATA_DIR = os.path.join("boardly", "data")
PROJECTS = os.path.join(DATA_DIR, "projects.json")

def project_name():
    # basename, splitext — three calls to get the stem
    name = os.path.basename(PROJECTS)        # projects.json
    stem, _ = os.path.splitext(name)         # projects
    return stem

def parent_dir():
    return os.path.dirname(PROJECTS)          # boardly/data

def archive_files():
    # The moment we want to glob, we leave os.path entirely.
    import glob
    return glob.glob(os.path.join(DATA_DIR, "archive.*.json"))
```

Every line works. The bug is not that it crashes; the bug is that each `os.path.*` call returns a *string* you immediately have to feed into the next `os.path.*` call. The path object never exists. You cannot write `PROJECTS.parent` or `PROJECTS.stem` because `PROJECTS` is a `str`, and `str` does not know it is a path. The moment you want to do something `os.path` does not provide — read the file, glob a pattern, walk a tree — you switch modules, and the path string travels across the module boundary as an opaque token.

`pathlib.Path` was added in Python 3.4 to fix this. The path object holds the string and exposes every operation you want to do on it: join (`/`), split (`.parent`, `.name`, `.stem`, `.suffix`), absolute resolve (`.resolve()`), read (`.read_text()`, `.read_bytes()`), write (`.write_text()`, `.write_bytes()`), glob (`.glob()`, `.rglob()`), walk (`.iterdir()`, `.walk()` 3.12+), and stat (`.stat()`). One type. Every operation. Same spelling on Linux, macOS, and Windows. The path stays a `Path` end to end; you convert to `str` only when a non-`pathlib` API demands it.

The `pathlib` module is the standard-library answer to "I have a path string and I want to do anything with it". `Path("a") / "b" / "c"` joins paths. `Path.cwd()` and `Path.home()` return class-method factories. `p.name`, `p.stem`, `p.suffix`, `p.parent`, `p.parts`, `p.anchor` are properties, not functions. `p.resolve()` collapses `.` and `..` and makes the path absolute. There is no `os.path.join` to remember. There is no `os.path.dirname` to forget. There is one object, and the operations hang off it.

## The Code

```python
# boardly/paths/path_basics.py
"""Pathlib basics: construction, the / operator, accessors, resolve()."""
from pathlib import Path

# 1. Construction from pathsegments
print("Path():", Path())                                  # .
print("Path('a', 'b', 'c'):", Path("a", "b", "c"))        # a/b/c
print("Path('a/b/c'):", Path("a/b/c"))                    # a/b/c
print("type:", type(Path(".")).__name__)                  # PosixPath on Linux/Mac

# 2. The / operator joins paths
print("Path('/') / 'a' / 'b':", Path("/") / "a" / "b")    # /a/b

# 3. Class methods for home and cwd
print("Path.home():", Path.home())
print("Path.cwd():", Path.cwd())

# 4. Accessors on a boardly-style relative path
p = Path("boardly/data/projects.json")
print("p:", p)
print("  .name:", p.name)                # projects.json
print("  .stem:", p.stem)                # projects
print("  .suffix:", p.suffix)            # .json
print("  .suffixes:", p.suffixes)        # ['.json']
print("  .parent:", p.parent)            # boardly/data
print("  .parents:", [str(x) for x in p.parents])
print("  .anchor:", repr(p.anchor))      # '' (relative path has no anchor)
print("  .parts:", p.parts)              # ('boardly', 'data', 'projects.json')
print("  .as_posix():", p.as_posix())    # boardly/data/projects.json

# 5. Absolute path with anchor
abs_p = Path("/etc/passwd")
print("abs_p:", abs_p)
print("  .anchor:", repr(abs_p.anchor))  # '/'
print("  .parts:", abs_p.parts)          # ('/', 'etc', 'passwd')

# 6. resolve() — collapse . and .. and make absolute
rel = Path("boardly/./data/../data/projects.json")
print("rel:", rel)
print("  .resolve(strict=False):", rel.resolve(strict=False))

# 7. resolve(strict=True) raises if the path doesn't exist
try:
    Path("does/not/exist").resolve(strict=True)
except FileNotFoundError as e:
    print("strict=True raises FileNotFoundError:", e)

# 8. Multi-suffix path
archive = Path("boardly/data/archive.2024.json")
print("archive:", archive)
print("  .stem:", archive.stem)          # archive.2024
print("  .suffix:", archive.suffix)      # .json
print("  .suffixes:", archive.suffixes)  # ['.2024', '.json']

# 9. is_relative_to (3.9+) — check whether one path is under another
print("p.is_relative_to('boardly'):", p.is_relative_to("boardly"))
print("p.is_relative_to('logs'):", p.is_relative_to("logs"))
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–8: Construction from pathsegments

```python
from pathlib import Path
# 1. Construction from pathsegments
print("Path():", Path())                                  # .
print("Path('a', 'b', 'c'):", Path("a", "b", "c"))        # a/b/c
print("Path('a/b/c'):", Path("a/b/c"))                    # a/b/c
print("type:", type(Path(".")).__name__)                  # PosixPath on Linux/Mac
```

`from pathlib import Path` is the only import you need for this lesson. The `pathlib` module exports `Path` (the concrete class — your day-to-day type), `PurePath` (the no-I/O base class — lesson 05), `PurePosixPath` / `PureWindowsPath` (string-algebra types that work on any OS for any OS's paths), and `PosixPath` / `WindowsPath` (the I/O-capable concrete classes). `Path` itself is a *dispatcher*: when you call `Path(...)`, its `__new__` inspects `os.name` and returns a `PosixPath` on POSIX (`os.name == "posix"`) or a `WindowsPath` on Windows (`os.name == "nt"`). You almost never write `PosixPath` or `WindowsPath` directly; you write `Path` and let the platform dispatch pick the right concrete class.

`Path()` with no arguments returns `Path(".")` — the current directory. `Path("a", "b", "c")` joins the segments with the OS separator (`/` on POSIX, `\` on Windows) and returns a single `Path` — so you do not need `os.path.join` any more. `Path("a/b/c")` parses the literal string; the forward slashes work on Windows too (the `WindowsPath` parser accepts both `/` and `\`), so a forward-slash literal is portable across operating systems. The `type(Path(".")).__name__` line confirms the dispatcher: on the Linux sandbox, it prints `PosixPath`; on a Windows machine, the same line prints `WindowsPath`. The dispatch happens at construction time, not at method-call time, so the object you get back is already the concrete class.

**Why does `Path` not just always return a `PurePath`?** Because `PurePath` cannot do I/O. `PurePath` is the no-filesystem-access ancestor — it knows about path *syntax* (joining, splitting, suffixes) but nothing about `exists()`, `read_text()`, `glob()`. `Path` is the I/O-capable subclass, and it has to know which OS's filesystem conventions to use: a `PosixPath` calls `open(2)` with POSIX semantics, a `WindowsPath` calls `CreateFile` with Windows semantics. The dispatcher at `Path.__new__` is what picks the right one. If you write `Path("a/b")` on Windows you get a `WindowsPath` whose `/` and `\` both work; if you write it on Linux you get a `PosixPath` that only knows `/`. Lesson 05 walks `PurePath` in detail and shows the case where you *want* to manipulate a Windows path string on a Linux machine (config validation) — there you write `PureWindowsPath("a\\b")` explicitly.

### Lines 10–11: The `/` operator joins paths

```python
# 2. The / operator joins paths
print("Path('/') / 'a' / 'b':", Path("/") / "a" / "b")    # /a/b
```

`Path("/") / "a"` calls `Path.__truediv__` (the method that backs the `/` operator). Internally, `__truediv__` calls `_from_parts_join` on the parts of `self` and the joined segments of the right-hand operand — it appends the right-hand segments to `self._parts`, normalises empty segments, and returns a *new* `Path` with those parts. `Path` is immutable; the `/` operator never mutates `self`, it returns a fresh object. So `Path("/") / "a" / "b"` chains two `__truediv__` calls: first `Path("/") / "a"` → `Path("/a")`, then `Path("/a") / "b"` → `Path("/a/b")`.

The right-hand operand of `/` can be a `str` *or* a `Path` *or* an `os.PathLike`. So `Path("/") / Path("a") / "b"` works, and `Path("/") / os.DirEntry(...)` works. The left-hand operand *must* be a `Path` — Python's operator dispatch tries `Path.__truediv__` first, and if the left side is a `str`, it falls through to `str.__truediv__` which raises `TypeError: unsupported operand type(s) for /: 'str' and 'Path'`. The fix is to make the leftmost operand a `Path`: write `Path("base") / "sub"` not `"base" / Path("sub"`).

**Why `/` and not `+`?** Because `+` is *string concatenation* and would lie about what you are doing. `"a" + "b"` is `"ab"`, which for paths is meaningless; `"a" + "/" + "b"` *looks* right but produces `"a/b"` only on POSIX. The `/` operator is the *mathematical* "divide into sub-path" gesture, and it dispatches to `Path.__truediv__` which knows the OS separator. The PEP 428 authors chose `/` deliberately so that path joining would *look* different from string concatenation — the same reason `urllib.parse.urljoin` exists instead of `+` for URLs. You cannot accidentally join with the wrong separator; the operator picks it.

### Lines 13–15: `Path.home()` and `Path.cwd()`

```python
# 3. Class methods for home and cwd
print("Path.home():", Path.home())
print("Path.cwd():", Path.cwd())
```

`Path.home()` is a class method that returns the current user's home directory as a `Path`. Internally it calls `os.path.expanduser("~")` on 3.10 and earlier, and `os.getuid()` + `pwd.getpwuid(...)` on 3.12+ (the implementation switched in CPython 3.12 to a faster, locale-independent path). The result composes with the `/` operator: `Path.home() / ".config" / "boardly"` is a one-line config-path build.

`Path.cwd()` is a class method that returns the process's current working directory as a `Path`. Internally it calls `os.getcwd()`. The CWD can change between calls — if you `os.chdir(...)` between two `Path.cwd()` calls, the second call returns the new CWD. `Path.home()` is invariant across `os.chdir` because it reads the user database, not the CWD. The rule of thumb: use `Path.cwd()` for *relative-to-here* paths (the deployment's current directory), use `Path.home()` for *user-scoped* paths (config files, caches, dotfiles).

**Why are these class methods and not module-level functions?** Because they return a `Path`, and `Path` is the type the rest of the API hangs off. If they were module-level functions like `pathlib.home()`, you would write `pathlib.home() / ".config"` and the `pathlib` prefix would be noise. As class methods on `Path`, the call site reads as `Path.home() / ".config"` — `Path` is both the receiver and the result type, and the call site composes with the `/` operator the same way every other `Path` operation does. The class-method shape is what makes `Path` an end-to-end path object instead of a procedural API.

### Lines 17–29: The seven accessors on a relative path

```python
# 4. Accessors on a boardly-style relative path
p = Path("boardly/data/projects.json")
print("p:", p)
print("  .name:", p.name)                # projects.json
print("  .stem:", p.stem)                # projects
print("  .suffix:", p.suffix)            # .json
print("  .suffixes:", p.suffixes)        # ['.json']
print("  .parent:", p.parent)            # boardly/data
print("  .parents:", [str(x) for x in p.parents])
print("  .anchor:", repr(p.anchor))      # '' (relative path has no anchor)
print("  .parts:", p.parts)              # ('boardly', 'data', 'projects.json')
print("  .as_posix():", p.as_posix())    # boardly/data/projects.json
```

`p = Path("boardly/data/projects.json")` constructs a relative path. The properties read it without doing any I/O — they are pure string algebra on the parts tuple. The parts tuple is `('boardly', 'data', 'projects.json')`; the accessors project different slices of that tuple.

`.name` returns the final component: `projects.json`. It is the equivalent of `os.path.basename`. `.stem` returns the final component with the final suffix stripped: `projects`. `.suffix` returns the final suffix *including* the dot: `.json`. `.suffixes` returns a list of *all* suffixes, including the dot on each: `['.json']` for `projects.json` and `['.2024', '.json']` for `archive.2024.json` (see lines 47–52). `.parent` returns the immediate parent: `boardly/data`. `.parents` returns a `_PathParents` sequence (indexable, iterable, with `len()`) of *all* ancestors, walking up the tree: `[Path('boardly/data'), Path('boardly'), Path('.')]`. `.anchor` returns the root prefix — empty string for a relative path, `/` for an absolute POSIX path, `C:\` for an absolute Windows path. `.parts` returns the tuple of components, with the anchor prepended if the path is absolute. `.as_posix()` returns the string form with `/` separators (useful for serialising a path into a POSIX-only context like a URL, even on Windows).

The properties are *lazy*: they read from `self._str` (the cached string form) the first time they are accessed and store the result. `Path` objects are *immutable* after construction — `p.name = "x"` raises `AttributeError: property 'name' of 'PosixPath' object has no setter`. To change a component, you construct a new path: `p.with_name("users.json")` returns `Path('boardly/data/users.json')`, leaving `p` unchanged.

**Why `.suffixes` *and* `.suffix`?** Because real-world filenames stack suffixes and the two answer different questions. `.suffix` answers "what file type is this?" — `archive.2024.json` is a JSON file, so `.suffix == ".json"`. `.suffixes` answers "what is the full suffix stack?" — `['.2024', '.json']`, which is what you need if you want to strip *just* the year: `archive.with_suffix("").with_suffix(".json")` won't work (it strips only `.json`), but reading `.suffixes` tells you the year is the second-to-last element. The two properties exist because the two questions are real and the stdlib does not want to force you to do string surgery to answer either.

**Why `.parent` (singular) *and* `.parents` (plural)?** Because the immediate parent and the ancestor chain answer different questions. `.parent` answers "where does this file live?" — `boardly/data`. `.parents` answers "walk up the tree to the root" — `[boardly/data, boardly, .]`. The `os.path` equivalent of `.parents` is a `while` loop calling `os.path.dirname` until you hit the root; `pathlib` gives you a sequence with one accessor. The singular exists because the immediate parent is the overwhelmingly common case; the plural exists because the ancestor walk is common enough that the stdlib does not want you to write the loop.

### Lines 31–35: An absolute path's `.anchor` and `.parts`

```python
# 5. Absolute path with anchor
abs_p = Path("/etc/passwd")
print("abs_p:", abs_p)
print("  .anchor:", repr(abs_p.anchor))  # '/'
print("  .parts:", abs_p.parts)          # ('/', 'etc', 'passwd')
```

`Path("/etc/passwd")` is an absolute POSIX path. Its `.anchor` is `'/'` — the root separator. Its `.parts` is `('/', 'etc', 'passwd')` — note the leading `'/'`, which is how `pathlib` distinguishes "absolute" from "relative" in the parts tuple. A relative path like `Path("etc/passwd")` has `.anchor == ''` and `.parts == ('etc', 'passwd')`; an absolute path has the anchor in `parts[0]`.

On Windows, `Path("C:/Users/z")` has `.anchor == 'C:\\'` (the drive letter + root separator, in the platform's native form) and `.parts == ('C:\\', 'Users', 'z')`. The `.anchor` accessor combines what Windows calls the "drive" (`C:`) and the "root" (`\`) into one string, because in practice you almost never want one without the other. (If you do, `.drive` and `.root` are exposed separately as well.)

**Why does `.parts` include the anchor as element 0?** Because the tuple is the *round-trippable* representation: `Path(*abs_p.parts)` reconstructs the original path. Try it: `Path(*Path("/etc/passwd").parts)` → `Path("/etc/passwd")`. This is the design pattern that lets you decompose a path, manipulate the parts, and rebuild it in one line: `Path(*abs_p.parts[:-1], "group")` → `Path("/etc/group")`. The round-trip property is what makes `.parts` more useful than a tuple of just the components.

### Lines 37–40: `resolve()` collapses `.` and `..` and makes absolute

```python
# 6. resolve() — collapse . and .. and make absolute
rel = Path("boardly/./data/../data/projects.json")
print("rel:", rel)
print("  .resolve(strict=False):", rel.resolve(strict=False))
```

`rel = Path("boardly/./data/../data/projects.json")` is a path with `.` and `..` segments in it. These are syntactically valid but semantically noisy — they refer to "current dir" and "parent dir" respectively. `rel.resolve(strict=False)` walks the path left to right, calls `os.getcwd()` for the starting absolute base, applies each segment in turn (`boardly`, then `.` (no-op), then `data`, then `..` (pop the last), then `data`, then `projects.json`), and returns a fully-absolute `Path` with the `.` and `..` collapsed. The result is `/home/z/.../boardly/data/projects.json` — the same logical file as `Path("boardly/data/projects.json").resolve()`.

`strict=False` (the default since Python 3.6) does not require the path to *exist* — it only collapses the *syntax*. The historical default was `strict=True`, which raised `FileNotFoundError` if any segment of the resolved path did not exist on disk. In 3.6, the default was flipped to `False` so that `resolve()` could be used to canonicalise paths you are *about* to create (a config file that does not exist yet, an output directory you have not made yet). If you want the strict behaviour — for example, to verify a config file actually exists before resolving symlinks in it — pass `strict=True` explicitly.

**Why does `resolve()` make the path absolute?** Because `.` and `..` are *relative to the CWD*, and the only way to resolve them is to know what the CWD is. If `resolve()` returned a relative path, it would have to either keep the `.` and `..` segments (which is what the original path already does — pointless) or pick an arbitrary base to collapse against (which would lie about the result). The choice the stdlib made is: `resolve()` makes the path absolute, calling `os.getcwd()` for the base, and the result is a fully-absolute path with no `.` or `..` segments. If you want a relative path back, you call `os.path.relpath(str(resolved), str(other_base))` — but the stdlib defaults to absolute because that is the unambiguous answer.

### Lines 42–46: `strict=True` raises on missing paths

```python
# 7. resolve(strict=True) raises if the path doesn't exist
try:
    Path("does/not/exist").resolve(strict=True)
except FileNotFoundError as e:
    print("strict=True raises FileNotFoundError:", e)
```

`Path("does/not/exist").resolve(strict=True)` walks the path left to right and *stat(2)*s each segment. The first segment that does not exist on disk raises `FileNotFoundError`, with the failing segment in the error message. On the sandbox, the error reads `[Errno 2] No such file or directory: 'does'` — note that `does` is the *first* failing segment, not the whole path. This is because `resolve(strict=True)` stat-checks each level as it walks, so the first missing ancestor is what raises.

The strict mode is what you want when you need the *resolved* path to point at a real file — for example, before passing the path to a C library that cannot tolerate symlinks. The non-strict mode (default) is what you want when you are *about to create* the file — for example, computing the output path for a build artefact that has not been written yet. The default flipped in 3.6 because the strict behaviour was the more common gotcha: students would call `resolve()` on a path they were about to `open(mode="w")` and get a spurious `FileNotFoundError`.

**Why does the error message say `'does'` instead of `'does/not/exist'`?** Because `resolve(strict=True)` checks segments incrementally, not the whole path at once. The `os.path` equivalent (`os.path.realpath`) does the same incremental walk. If you want a single-shot "does the whole path exist?" check, you call `Path.exists()` after `resolve(strict=False)` — that is one stat call on the leaf, not one per ancestor. The two patterns serve different questions: strict-resolve answers "is every *ancestor* real?" (catches a typo in a parent dir); `exists()` answers "is the *leaf* real?" (catches a typo in the filename).

### Lines 48–53: Multi-suffix paths and the `.suffixes` list

```python
# 8. Multi-suffix path
archive = Path("boardly/data/archive.2024.json")
print("archive:", archive)
print("  .stem:", archive.stem)          # archive.2024
print("  .suffix:", archive.suffix)      # .json
print("  .suffixes:", archive.suffixes)  # ['.2024', '.json']
```

`Path("boardly/data/archive.2024.json")` is a *multi-suffix* path. The `.stem` accessor strips only the *final* suffix: `archive.2024`. The `.suffix` accessor returns only the *final* suffix: `.json`. The `.suffixes` accessor returns the *list of all suffixes*, in order: `['.2024', '.json']`. The list includes the dot on each element, so `"".join(p.suffixes)` reconstructs the suffix portion of the path.

This matters when you want to *strip* the year and keep the type, or vice versa. `archive.with_suffix(".yaml")` returns `Path("boardly/data/archive.2024.yaml")` — only the final suffix is replaced. `archive.with_name("archive.2025.json")` returns a path with the whole final component replaced. To strip the year and keep the JSON type, you go through the parts: `Path(archive.parent, archive.stem.removesuffix(".2024") + archive.suffix)` — there is no one-call `with_stem` because the design philosophy is "the suffix is the file type; the stem is the rest; if you need to do something the accessors do not do, you build the new path from the parts you want".

**Why does `.stem` strip *only* the final suffix?** Because the suffix is defined as "the last dot-separated extension", and the stem is "everything else". `archive.2024.json`'s final suffix is `.json` (the file type), and the stem is `archive.2024` (the rest of the name). This matches the `os.path.splitext` behaviour, which is the rule most filesystem tools expect: `tar` strips `.gz`, `unzip` strips `.zip`, `file` strips the extension it knows. The rule "final suffix only" is what makes `archive.2024.json` recognised as JSON by tools that pattern-match on `.json`.

### Lines 55–57: `is_relative_to` — the parent-check predicate (3.9+)

```python
# 9. is_relative_to (3.9+) — check whether one path is under another
print("p.is_relative_to('boardly'):", p.is_relative_to("boardly"))
print("p.is_relative_to('logs'):", p.is_relative_to("logs"))
```

`Path.is_relative_to(other)` was added in Python 3.9 to answer the question "is this path underneath that other path?" without you having to compute the relative path and catch `ValueError`. `p.is_relative_to("boardly")` returns `True` because `boardly/data/projects.json` is under `boardly`. `p.is_relative_to("logs")` returns `False` because it is not. The argument can be a `Path` or a `str` (it is converted internally via `Path(other)`); the comparison is done on the parts tuple, not the string form, so `Path("/a/b").is_relative_to("/a")` works even with no trailing slashes to normalise.

**Why does `is_relative_to` exist when `relative_to` already did?** Because `relative_to` raises `ValueError` on a non-relative relationship, and the `try`/`except ValueError` dance around it was the *most common* pathlib bug reported on the issue tracker. The stdlib added `is_relative_to` in 3.9 so the question "is this under that?" could be answered with a plain boolean, no exception. The implementation is the obvious one: `Path(other) in self.parents or self == Path(other)` — a parts-tuple comparison. If you are on a Python older than 3.9 (you are not, in this vault), the equivalent is `try: p.relative_to(other); except ValueError: return False; else: return True`. The `is_relative_to` method is the stdlib saying "we got tired of the dance too; here is the boolean".

## Execution Trace

```bash
$ uv run python boardly/paths/path_basics.py
Path(): .
Path('a', 'b', 'c'): a/b/c
Path('a/b/c'): a/b/c
type: PosixPath
Path('/') / 'a' / 'b': /a/b
Path.home(): /home/z
Path.cwd(): /home/z/my-project/FastAPI-Engineering-Academy
p: boardly/data/projects.json
  .name: projects.json
  .stem: projects
  .suffix: .json
  .suffixes: ['.json']
  .parent: boardly/data
  .parents: ['boardly/data', 'boardly', '.']
  .anchor: ''
  .parts: ('boardly', 'data', 'projects.json')
  .as_posix(): boardly/data/projects.json
abs_p: /etc/passwd
  .anchor: '/'
  .parts: ('/', 'etc', 'passwd')
rel: boardly/data/../data/projects.json
  .resolve(strict=False): /home/z/my-project/FastAPI-Engineering-Academy/boardly/data/projects.json
strict=True raises FileNotFoundError: [Errno 2] No such file or directory: 'does'
archive: boardly/data/archive.2024.json
  .stem: archive.2024
  .suffix: .json
  .suffixes: ['.2024', '.json']
p.is_relative_to('boardly'): True
p.is_relative_to('logs'): False
```

The `Path.home()` and `Path.cwd()` lines reflect the sandbox user and the directory you ran from; they will differ on your machine but the shape (an absolute path with `/home/...`) will match. The `rel:` line shows that `Path` normalises away the redundant `./` segment at construction time (the literal `boardly/./data/../data/projects.json` is stored as `boardly/data/../data/projects.json`); `resolve(strict=False)` then collapses the `..` to produce an absolute path with no `.` or `..` segments. The `resolve(strict=False)` line is anchored to wherever you ran the script from; the path it prints is the absolute form of `boardly/data/projects.json` under your CWD.

## Common Mistakes

### Mistake 1: Joining with `+` instead of `/`

```python
p = Path("boardly") + "data" + "projects.json"
```

**Symptom:** `TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'`. The error message is loud, which is the point — `Path` does not define `__add__`, so any `+` against a `Path` raises immediately.
**Why:** `Path` is immutable and the stdlib deliberately did not define `__add__` because string concatenation would not respect the OS separator. The `/` operator is the *only* concatenation spelling, and it dispatches to `__truediv__` which knows the separator.
**Fix:** Use the `/` operator: `p = Path("boardly") / "data" / "projects.json"`. The leftmost operand *must* be a `Path` (or `os.PathLike`); if you have a `str` on the left, wrap it: `p = Path("boardly") / "data" / "projects.json"`.

### Mistake 2: Treating `Path` as a `str`

```python
def load(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:    # path is a str
        return f.read()
# caller:
load(Path("boardly/data/projects.json"))             # TypeError
```

**Symptom:** `TypeError: expected str, bytes or os.PathLike object, not PosixPath` — wait, no: actually `open()` accepts `Path` since 3.6 (the `Path.__fspath__` protocol). So this works. The bug is *upstream*: the function's annotation says `path: str` but the caller passes a `Path`, and your type checker (`mypy`, `pyright`) flags it as an error even though it runs.
**Why:** `Path` implements the `os.PathLike` protocol (`__fspath__`), so `open()` and most stdlib functions accept it transparently. The bug is the *annotation* — `path: str` is a lie if you intend to accept `Path`. The type checker complains; the runtime does not.
**Fix:** Annotate with `Path` (preferred) or `str | Path` (if you must accept both). Inside the function, use the path directly: `with path.open("r", encoding="utf-8") as f:` is the idiomatic pathlib form (lesson 02). Convert to `str` only at the boundary with a non-`pathlib` API.

### Mistake 3: Forgetting `strict=True` is the historical default

```python
# 3.5 and earlier:
p = Path("does/not/exist").resolve()        # FileNotFoundError
# 3.6+:
p = Path("does/not/exist").resolve()        # Path object (no error)
```

**Symptom:** Code that worked on 3.5 raises `FileNotFoundError` on 3.6+ when you read old migration notes that say "you have to catch the error". Or the opposite: code that worked on 3.6 silently returns a `Path` to a non-existent file when you expected strict behaviour.
**Why:** The default value of `strict` was flipped from `True` to `False` in Python 3.6 (bpo-19711). The 3.5 default was `strict=True` because the historical `realpath()`-equivalent behaviour was strict; the 3.6 flip made `resolve()` useful for paths you are about to create. Code written against 3.5 that relied on the strict default will silently get non-strict behaviour on 3.6+; code written against 3.6+ that expects non-strict will raise on 3.5.
**Fix:** Always pass `strict=` explicitly if the behaviour matters. `resolve(strict=False)` is what you want 95% of the time (canonicalise the syntax, do not check existence). `resolve(strict=True)` is what you want when you need to verify the path actually exists on disk (e.g. before passing to a C library that cannot tolerate broken symlinks). On the 3.12 runtime this vault targets, the default is `False`.

### Mistake 4: Using `.stem` when you meant "the name without all suffixes"

```python
archive = Path("archive.2024.json")
stem = archive.stem           # 'archive.2024' (only the .json stripped)
# what you wanted: 'archive'
```

**Symptom:** You got `archive.2024` back when you wanted `archive`. The next step of your pipeline treats `2024` as part of the name and breaks.
**Why:** `.stem` is defined as "the final component without its *final* suffix". The rule is one suffix only. The stdlib does not provide a "strip all suffixes" accessor because the answer to "what is the name without suffixes" is ambiguous when the file has multiple dots — `archive.2024.json` could be `archive.2024` (year-prefix), `archive` (no metadata), or even `archive.2024.json` (whole name).
**Fix:** Decide what you mean. To strip the final suffix only: `archive.stem` (which is `archive.2024`). To strip *all* suffixes: `archive.name.split('.')[0]` — but verify the input first; this lies for filenames like `.gitignore` (no stem) or `archive.2024.json` (returns `archive`). To replace the final suffix: `archive.with_suffix(".yaml")` → `archive.2024.yaml`. To replace the whole final component: `archive.with_name("archive.2025.json")`. There is no `with_stem`; build from parts.

## Engineering Trade-Offs

**Decision:** Use `Path` everywhere in `boardly`. Never `os.path.*`. Never `str` for a path variable.
**Both sides:** The alternative is `os.path` (older, string-based, more verbose) or `str` (no operations, no safety). `os.path` loses to `pathlib` on composability — every call returns a `str` you have to re-wrap. `str` loses on safety — there is no `Path` accessor to call, so you fall back to `os.path.*` and re-introduce the composability problem. The one place `str` wins is at the *boundary* with a non-`pathlib` API (a C extension, a `subprocess` arg list that some shells mishandle with `Path`, a JSON serialisation step that wants the string form). At that boundary, you call `str(path)` explicitly; inside your code, the path stays a `Path`.
**Commitment:** `boardly` uses `Path` for every path variable — `data_dir: Path`, `projects_path: Path`, `log_dir: Path`. The `Path.__fspath__` protocol means `open(path)`, `subprocess.run([..., str(path), ...])`, and `shutil.copy(path, dest)` all work without conversion. The only place we call `str(path)` is when serialising to JSON (a path is not natively JSON-serialisable) or when handing the path to a tool that does not implement the `PathLike` protocol. The rule is: `Path` is the in-code type; `str` is the at-the-boundary type.

## Exercises

1. **Exercise 1 — Print your own home and CWD.** Add a line `print("home relative to cwd:", Path.home().relative_to(Path.cwd()))` and re-run. If your home is not under your CWD, catch the `ValueError` and print "home not under cwd". `Verify: uv run python boardly/paths/path_basics.py | rg 'home relative'`
2. **Exercise 2 — Build the `boardly/data/archive/<year>/<month>.json` path.** Use the `/` operator and the `Path` constructor to build the path for year 2024, month 10. Print `.parts` and `.parents` of the result. Confirm `.parts` has 5 elements. `Verify: uv run python -c "from pathlib import Path; p = Path('boardly') / 'data' / 'archive' / '2024' / '10.json'; assert len(p.parts) == 5 and p.parts[-1] == '10.json'; print(p)"`
3. **Exercise 3 — Replace the final suffix.** Use `Path("boardly/data/projects.json").with_suffix(".yaml")` and print the result. Then use `.with_name("users.json")` and print. Confirm `.with_suffix` only swaps the final suffix and `.with_name` swaps the whole final component. `Verify: uv run python -c "from pathlib import Path; p = Path('boardly/data/projects.json'); assert p.with_suffix('.yaml').name == 'projects.yaml'; assert p.with_name('users.json').name == 'users.json'; print('ok')"`
4. **Exercise 4 — Reconstruct from parts.** Take `Path("/etc/passwd")`, read its `.parts`, and reconstruct an equivalent path using `Path(*parts)`. Confirm the two paths are `==`. `Verify: uv run python -c "from pathlib import Path; p = Path('/etc/passwd'); assert Path(*p.parts) == p; print('round-trip ok')"`
5. **Exercise 5 — Write a `is_safe_relative(path, base)` helper.** Write a function that returns `True` iff `path` is a relative path under `base` *and* `path` does not escape `base` via `..`. Use `.is_relative_to(base)` and `.resolve(strict=False)` and check the resolved path is still under `base.resolve(strict=False)`. The function should return `False` for `Path("boardly/../../etc/passwd")` against `base=Path("boardly")`. `Verify: uv run python -c "from pathlib import Path; import sys; sys.path.insert(0, 'boardly/paths'); from path_basics import is_safe_relative; assert is_safe_relative(Path('boardly/data/x'), Path('boardly')) is True; assert is_safe_relative(Path('boardly/../../etc/passwd'), Path('boardly')) is False; print('safe')"` (you will need to add the `is_safe_relative` function to `path_basics.py` for this exercise).

## Verification

```bash
$ uv run python boardly/paths/path_basics.py
Path(): .
Path('a', 'b', 'c'): a/b/c
Path('a/b/c'): a/b/c
type: PosixPath
Path('/') / 'a' / 'b': /a/b
Path.home(): /home/z
Path.cwd(): /home/z/my-project/FastAPI-Engineering-Academy
p: boardly/data/projects.json
  .name: projects.json
  .stem: projects
  .suffix: .json
  .suffixes: ['.json']
  .parent: boardly/data
  .parents: ['boardly/data', 'boardly', '.']
  .anchor: ''
  .parts: ('boardly', 'data', 'projects.json')
  .as_posix(): boardly/data/projects.json
abs_p: /etc/passwd
  .anchor: '/'
  .parts: ('/', 'etc', 'passwd')
rel: boardly/data/../data/projects.json
  .resolve(strict=False): /home/z/my-project/FastAPI-Engineering-Academy/boardly/data/projects.json
strict=True raises FileNotFoundError: [Errno 2] No such file or directory: 'does'
archive: boardly/data/archive.2024.json
  .stem: archive.2024
  .suffix: .json
  .suffixes: ['.2024', '.json']
p.is_relative_to('boardly'): True
p.is_relative_to('logs'): False
```

The `Path.home()` and `Path.cwd()` lines reflect the sandbox user (`/home/z`) and the project root — they will differ on your machine. The `PosixPath` line will read `WindowsPath` on a Windows machine. The `rel:` line shows that `Path` normalises the redundant `./` segment away at construction time (the literal `boardly/./data/../data/projects.json` is stored as `boardly/data/../data/projects.json`); `resolve(strict=False)` then collapses the `..` to produce a fully-absolute path with no `.` or `..` segments. The `resolve(strict=False)` line is anchored to wherever you ran the script from; the path it prints is the absolute form of `boardly/data/projects.json` under your CWD.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — the `path: Path` annotation this lesson writes on the demo's local variables; the typing lesson covers the annotation-as-contract rule.
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` decorator the later lessons in this section use to attach `Path` fields to a `ProjectRepo` model.

## What's Next

[[08-pathlib/02-read-write-text-binary]] — Now that you can construct a `Path` and read its components, the next lesson makes the path *do something*: read and write files. `Path.read_text(encoding="utf-8")` replaces `open(path).read()` in one call; `Path.write_bytes(data)` replaces `open(path, "wb").write(data)`; `Path.open(mode="r", encoding="utf-8")` is the context-manager form for streaming. The lesson also walks the **encoding= is mandatory** rule — the rule that prevents the Windows `cp1252` gotcha where reading a UTF-8 file as `cp1252` silently mangles every non-ASCII byte. The `newline=` parameter on `write_text` (added in Python 3.10) is covered with the CSV-export use case that motivates it.

- **Lesson 02** — `read_text`, `read_bytes`, `write_text`, `write_bytes`, `Path.open()` context manager.
- **Lesson 03** — `glob` and `rglob` for pattern-based file discovery.
- **Lesson 04** — `mkdir`, `rmdir`, `unlink`, `touch`, `rename`, `replace` for filesystem mutation.

## Sources

- **Python `pathlib` module documentation** — https://docs.python.org/3/library/pathlib.html — accessed 2026-10-23 — the source-of-truth reference for `Path`, the `/` operator, the accessors (`.name`/`.stem`/`.suffix`/`.suffixes`/`.parent`/`.parents`/`.anchor`/`.parts`), `Path.home()`/`Path.cwd()`, and `resolve(strict=)`.
- **PEP 428 — The pathlib module — object-oriented filesystem paths** — https://peps.python.org/pep-0428/ — accessed 2026-10-23 — the design rationale for choosing `/` as the join operator and for the `PurePath`/`Path` split that lesson 05 walks in detail.
- **Python `os.path` documentation** — https://docs.python.org/3/library/os.path.html — accessed 2026-10-23 — the older string-based API this lesson replaces; useful for the side-by-side `os.path.join` / `Path /` comparison.

## What We Learned

- You can now construct a `Path` from segments (`Path("a", "b", "c")`) and explain that `Path` is a dispatcher returning `PosixPath` on POSIX or `WindowsPath` on Windows.
- You can join paths with the `/` operator and explain why `+` is forbidden — `__truediv__` knows the OS separator, `__add__` would not.
- You can call `Path.home()` and `Path.cwd()` and explain that they read `$HOME` and `os.getcwd()` respectively, returning `Path` objects that compose with `/`.
- You can read the seven accessors (`.name`, `.stem`, `.suffix`, `.suffixes`, `.parent`, `.parents`, `.anchor`, `.parts`) and explain what each returns on a relative path, an absolute path, and a multi-suffix path like `archive.2024.json`.
- You can call `.resolve(strict=False)` to collapse `.` and `..` and make a path absolute, and explain why the default flipped from `strict=True` to `strict=False` in Python 3.6.
