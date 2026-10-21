---
title: "Lesson 03: glob and rglob"
aliases:
 - Path.glob
 - Path.rglob
 - the ** pattern
 - case_sensitive kwarg
 - no glob.glob use Path.glob
tags:
 - pathlib
 - python-stdlib
 - glob
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
 - "[[08-pathlib/02-read-write-text-binary]]"
related_lessons:
 - "[[08-pathlib/04-mkdir-rmdir-unlink]]"
 - "[[08-pathlib/01-Path-Basics]]"
---

# Lesson 03: glob and rglob

*Why `boardly`'s `for p in data_dir.glob("archive.*.json")` finds every archive file in one line, why `rglob` is the recursive form, and why you should never write `glob.glob` in new code.*

**You're at the very beginning of Section 08, lesson 03.**

You have written `import glob; for p in glob.glob("boardly/data/*.json"): ...` and watched the loop body treat `p` as a `str` — a `str` you immediately have to wrap in `Path(p)` to do anything useful with. You have written `os.walk` to recurse into subdirectories and seen the three-tuple (`dirpath`, `dirnames`, `filenames`) that forces you to re-join the dirpath with each filename by hand. The `pathlib.Path.glob` and `Path.rglob` methods fix both. They return `Path` objects — not `str` — so the loop body has the full pathlib API. They recurse with the `**` pattern, so one call walks the tree. And the `case_sensitive=` parameter (Python 3.12+) lets you do case-insensitive matching on filesystems where the default is case-sensitive. Take your time. Type every example. **This is how you learn.**

#pathlib #glob

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `Path.glob(pattern)`** for non-recursive matching — explain that it matches *direct children* of the calling `Path` only, returns a *generator* of `Path` objects (lazy, materialised on iteration), and supports the `*`, `?`, and `[...]` wildcards the `glob` module has always supported.
2. **Call `Path.rglob(pattern)`** for recursive matching — explain that it is exactly equivalent to `Path.glob("**/" + pattern)` and is the spelling the stdlib provides for the common "walk the tree" case.
3. **Use the `**` pattern** — explain that `**` matches any number of directories (including zero), so `**/*.json` finds every JSON file in the tree at any depth.
4. **Use the `case_sensitive=` parameter (3.12+)** — explain that the default is `None` (use the filesystem's case-sensitivity), `True` forces case-sensitive matching, `False` forces case-insensitive matching, and the parameter is version-gated because it was added in 3.12.
5. **State the rule** that the rest of the section depends on: never write `glob.glob` in new code. Use `Path.glob` / `Path.rglob` because the result is `Path` objects, not `str`.

## Prerequisites

Before starting, you need:

- **Path basics** — [[08-pathlib/01-Path-Basics]]. This lesson calls `.glob()` on `Path` objects; you need to be comfortable constructing a `Path`.
- **Read & write** — [[08-pathlib/02-read-write-text-binary]]. The lesson reads files matched by glob, so you need to know `Path.read_text(encoding="utf-8")`.
- **About 30–45 minutes of focused time.**

**The most common gap: treating `Path.glob` and `glob.glob` as interchangeable.**

They are not. `glob.glob("path/*.json")` returns a `list[str]` — a list of string paths that you immediately have to wrap in `Path(...)` to do anything useful with. `Path("path").glob("*.json")` returns a *generator* of `Path` objects — lazy, materialised one at a time, with the full pathlib API on each. The single biggest mistake students make in this lesson is reaching for the `glob` module out of habit and ending up with a list of `str` they have to re-wrap. The fix is the rule "no `glob.glob` in new code" — the pathlib methods exist precisely so the loop body has `Path` objects, not `str`.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/paths/bad_glob.py — the bad old days
import glob
import os.path

# 1. Non-recursive glob returns list[str] — you wrap every element in Path
archives = glob.glob("boardly/data/archive.*.json")    # list[str]
for path_str in archives:
    path = Path(path_str)                              # re-wrap every element
    text = path.read_text(encoding="utf-8")
    process(text)

# 2. Recursive glob needs glob.glob with recursive=True
all_logs = glob.glob("boardly/**/*.log", recursive=True)  # 3.5+ recursive
for path_str in all_logs:
    path = Path(path_str)                              # re-wrap every element

# 3. Case-insensitive matching is a separate library call (no glob kwarg pre-3.12)
case_insensitive = []
for path_str in glob.glob("boardly/data/*.JSON"):
    case_insensitive.append(Path(path_str))
# This misses 'projects.json' on Linux because *.JSON is case-sensitive
```

Every line works. The bug is not that it crashes; the bug is that every `path_str` has to be re-wrapped in `Path(...)` before you can use the pathlib API. The path object never exists in the `glob` module's return value; you reconstruct it on every iteration. The recursive form needs the `recursive=True` keyword (added in 3.5) and the `**` pattern, which is a separate code path from the non-recursive `*`. Case-insensitive matching needs a separate library (`fnmatch` or `pathlib`'s 3.12+ `case_sensitive=` kwarg) — there is no `glob.glob(..., case_insensitive=True)` argument.

`pathlib.Path.glob(pattern)` and `Path.rglob(pattern)` were added in Python 3.5 to fix all of this. The pattern matches against the *children* of the calling `Path`, and the result is a generator of `Path` objects — lazy, materialised on iteration, with the full pathlib API on each. The `**` pattern is the recursive marker (added in 3.5 with the original `Path.glob`); `rglob` is the shortcut spelling for `glob("**/" + pattern)`. The `case_sensitive=` parameter (Python 3.12+) lets you do case-insensitive matching on filesystems where the default is case-sensitive. There is no `glob.glob` to remember; there is no `recursive=True` keyword; there is no `str` to re-wrap.

The `pathlib` glob methods are the standard-library answer to "I have a `Path`, I want to find files under it". `Path("boardly/data").glob("*.json")` yields every JSON file directly under `boardly/data`. `Path("boardly").rglob("*.log")` yields every log file anywhere under `boardly`, recursively. The result is `Path` objects, so the loop body has `.read_text()`, `.parent`, `.name`, `.stem` — every accessor from lesson 01 and every I/O method from lesson 02. The pattern language is the same `*`/`?`/`[...]` the `glob` module has always supported, plus `**` for recursion.

## The Code

```python
# boardly/paths/glob_demo.py
"""Pathlib glob/rglob: pattern matching, recursive **, case_sensitive (3.12+)."""
from pathlib import Path
import sys
import tempfile

# 0. Build a tmpdir that stands in for a boardly deployment's tree
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    data_dir = root / "boardly" / "data"
    logs_dir = root / "boardly" / "logs"
    crashes_dir = logs_dir / "crashes"
    archive_dir = data_dir / "archive"
    data_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    crashes_dir.mkdir()
    archive_dir.mkdir()

    # Seed files (mix of .json and .log; mixed-case names for case-sensitivity test)
    (data_dir / "projects.json").write_text("{}", encoding="utf-8")
    (data_dir / "Users.JSON").write_text("{}", encoding="utf-8")
    (archive_dir / "archive.2024.json").write_text("{}", encoding="utf-8")
    (archive_dir / "archive.2025.json").write_text("{}", encoding="utf-8")
    (logs_dir / "app.log").write_text("line1\n", encoding="utf-8")
    (logs_dir / "app.log.1").write_text("old\n", encoding="utf-8")
    (crashes_dir / "segfault-2024.log").write_text("boom\n", encoding="utf-8")
    (crashes_dir / "oom-2024.log").write_text("oom\n", encoding="utf-8")

    # 1. glob — non-recursive, matches direct children of the calling Path
    print("--- data_dir.glob('*.json') (direct children only) ---")
    for p in sorted(data_dir.glob("*.json")):
        print("  glob:", p.name)

    # 2. glob with ** — RECURSIVE; ** matches any number of dirs (incl. zero)
    print("--- root.glob('**/*.json') (recursive) ---")
    for p in sorted(root.glob("**/*.json")):
        print("  **:", p.relative_to(root))

    # 3. rglob — equivalent to glob("**/" + pattern); shorter spelling
    print("--- root.rglob('*.log') (recursive) ---")
    for p in sorted(root.rglob("*.log")):
        print("  rglob:", p.relative_to(root))

    # 4. glob is lazy: it returns a generator, materialised on iteration
    gen = data_dir.glob("*.json")
    print("--- generator type:", type(gen).__name__)
    # Materialise once into a list to inspect; do NOT call list() twice
    print("--- list(gen):", [p.name for p in sorted(gen)])

    # 5. case_sensitive kwarg (3.12+)
    #    Default on Linux is case-SENSITIVE; *.json does NOT match Users.JSON
    print("--- data_dir.glob('*.JSON') (default case) ---")
    print("  matches:", [p.name for p in sorted(data_dir.glob("*.JSON"))])
    print("--- data_dir.glob('*.JSON', case_sensitive=False) (3.12+) ---")
    print("  matches:", [p.name for p in sorted(data_dir.glob("*.JSON", case_sensitive=False))])

    # 6. glob vs iglob — the difference
    #    pathlib.Path.glob is a method on Path; it returns Path objects.
    #    The stdlib glob module's glob.glob returns a list of str.
    #    glob.iglob returns a generator of str.
    #    The "no glob.glob" rule: use Path.glob for new code.
    import glob as glob_module
    print("--- glob.glob (stdlib, returns list[str]) ---")
    print("  ", [x for x in sorted(glob_module.glob(str(data_dir / "*.json")))])
    print("--- glob.iglob (stdlib, returns generator[str]) ---")
    ig = glob_module.iglob(str(data_dir / "*.json"))
    print("  type:", type(ig).__name__, "->", sorted(ig))

    # 7. Version gate summary
    print("---")
    print("Python:", sys.version.split()[0])
    print("Path.glob signature:", __import__("inspect").signature(Path.glob))
    print("Path.rglob signature:", __import__("inspect").signature(Path.rglob))
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–27: Setup — the tmpdir tree with mixed-case files

```python
from pathlib import Path
import sys
import tempfile

# 0. Build a tmpdir that stands in for a boardly deployment's tree
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    data_dir = root / "boardly" / "data"
    logs_dir = root / "boardly" / "logs"
    crashes_dir = logs_dir / "crashes"
    archive_dir = data_dir / "archive"
    data_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    crashes_dir.mkdir()
    archive_dir.mkdir()

    # Seed files (mix of .json and .log; mixed-case names for case-sensitivity test)
    (data_dir / "projects.json").write_text("{}", encoding="utf-8")
    (data_dir / "Users.JSON").write_text("{}", encoding="utf-8")
    (archive_dir / "archive.2024.json").write_text("{}", encoding="utf-8")
    (archive_dir / "archive.2025.json").write_text("{}", encoding="utf-8")
    (logs_dir / "app.log").write_text("line1\n", encoding="utf-8")
    (logs_dir / "app.log.1").write_text("old\n", encoding="utf-8")
    (crashes_dir / "segfault-2024.log").write_text("boom\n", encoding="utf-8")
    (crashes_dir / "oom-2024.log").write_text("oom\n", encoding="utf-8")
```

The imports are `Path` from `pathlib`, `sys`, and `tempfile` — the same trio as lesson 02. The `with tempfile.TemporaryDirectory() as td:` block creates a fresh tree that vanishes on exit, so the demo is reproducible across machines without leaving files behind. `root = Path(td)` wraps the tmpdir string in a `Path`; from here, every path operation uses `/` and the `Path` API.

The tree the demo builds has two top-level directories (`data` and `logs`), one nested directory under each (`archive` under `data`, `crashes` under `logs`), and a mix of `.json` and `.log` files distributed across them. The two `.log` files in `crashes/` are what the recursive `rglob` will find that the non-recursive `glob` from `logs_dir` would miss — the lesson's whole point is the recursive-vs-non-recursive distinction.

The `Users.JSON` file (capital `JSON`) is the case-sensitivity probe. On Linux's default `ext4`/`xfs` filesystem, `projects.json` and `Users.JSON` are *different files* with *different case* — the filesystem is case-sensitive. On macOS's default `APFS` (case-insensitive but case-preserving), the two would be considered the same name; on Windows's `NTFS`, the same. The case-sensitivity test the demo runs (`*.JSON` default vs `*.JSON` with `case_sensitive=False`) is the lesson's case-sensitivity teaching point.

**Why mixed-case files in the demo?** Because case-sensitivity is a real-world concern that the demo has to *show*, not just *describe*. A `boardly` deployment on Linux will have `projects.json` and might have `Users.JSON` (from a Windows-edited export). The student has to see that `*.JSON` matches only `Users.JSON` on Linux by default, and that `*.JSON` with `case_sensitive=False` matches both. The mixed-case files in the seed are what make the case-sensitivity test produce a non-empty result for both default and `case_sensitive=False` calls.

### Lines 29–32: `Path.glob(pattern)` — non-recursive, direct children only

```python
# 1. glob — non-recursive, matches direct children of the calling Path
print("--- data_dir.glob('*.json') (direct children only) ---")
for p in sorted(data_dir.glob("*.json")):
    print("  glob:", p.name)
```

`data_dir.glob("*.json")` calls `Path.glob` on `data_dir`, with the pattern `"*.json"`. The pattern is *relative* — it matches against the *direct children* of `data_dir`. The `*` matches any sequence of characters in the filename (not crossing `/`); the `.json` is a literal. The result is a generator of `Path` objects, one per matching direct child of `data_dir`. The `sorted(...)` materialises the generator into a sorted list (so the demo's output is deterministic — the generator's order is filesystem-dependent and not stable).

The output shows `glob: projects.json` — the only direct child of `data_dir` that ends in `.json`. `Users.JSON` is not matched because `.JSON` (capital) does not equal `.json` (lowercase) on the case-sensitive Linux filesystem. `archive.2024.json` and `archive.2025.json` are *not* matched because they are direct children of `archive_dir`, not `data_dir` — the `*.json` pattern does not cross `/`. To find them, you need the recursive `**` pattern (lines 34–37) or `rglob` (lines 39–42).

Internally, `Path.glob` calls `os.scandir(self)` (the directory iterator) and applies the pattern via `fnmatch.fnmatchcase` (case-sensitive) or `fnmatch.fnmatch` (case-insensitive) to each child's name. The `os.scandir` call is lazy — it returns an iterator that yields `DirEntry` objects, and `Path.glob` wraps each matching `DirEntry`'s path in a `Path` and yields it. The whole directory is *not* loaded into memory; one `DirEntry` is read at a time, which is what makes `glob` usable on directories with millions of entries.

**Why does `*.json` not cross `/`?** Because the `*` wildcard matches "any sequence of characters *in a single path component*" — it does not cross the OS separator. This is the same rule the `glob` shell command uses (`ls boardly/*.json` lists direct children of `boardly/`, not recursively). To cross `/`, you need the `**` pattern, which is the recursive marker. The two wildcards are not interchangeable; they answer different questions. `*` answers "what files in this directory match?"; `**` answers "what files anywhere under this directory match?".

### Lines 34–37: `Path.glob("**/*.json")` — the recursive `**` pattern

```python
# 2. glob with ** — RECURSIVE; ** matches any number of dirs (incl. zero)
print("--- root.glob('**/*.json') (recursive) ---")
for p in sorted(root.glob("**/*.json")):
    print("  **:", p.relative_to(root))
```

`root.glob("**/*.json")` calls `Path.glob` on `root`, with the pattern `"**/*.json"`. The `**` is the *recursive* marker — it matches any number of directory levels (including zero). The pattern `**/*.json` therefore matches every `.json` file anywhere under `root`, at any depth: direct children of `root` (zero levels), children of `root/boardly` (one level), children of `root/boardly/data` (two levels), children of `root/boardly/data/archive` (three levels), etc.

The output shows three matches: `boardly/data/archive/archive.2024.json`, `boardly/data/archive/archive.2025.json`, and `boardly/data/projects.json`. The `archive.*` files are three levels deep; the `projects.json` file is two levels deep. The `**` matched the directory chain in each case.

The `**` pattern was added to `Path.glob` in Python 3.5 (alongside the original `Path.glob` itself — the `**` is not a separate feature, it is part of the pattern language). The `recursive=True` keyword on the `glob` module's `glob.glob` is the *same feature* expressed in the function-call API; in `pathlib`, the `**` is in the pattern, not as a keyword. This is one of the design choices that makes `Path.glob` shorter than `glob.glob` for recursive matching: `Path("root").glob("**/*.json")` vs `glob.glob("root/**/*.json", recursive=True)`.

**Why is `**` "any number of directories including zero"?** Because that is what `find -name` does (`find root -name '*.json'` finds files at any depth including root itself), and the `glob` module's `**` was designed to match `find`'s semantics. The "including zero" case matters: `root.glob("**/*.json")` matches `root/projects.json` if it exists (the `**` matches the empty directory chain), not just `root/boardly/projects.json`. If you want "at least one directory level", you write `*/*.json` (one level) or `**/**/*.json` (one or more levels — the leading `**/` matches zero, the trailing `**/` matches at least one). The "including zero" rule is the rule that makes `**` behave like the shell's `**` (zsh, bash `globstar`), not like the regular expression `.*`.

### Lines 39–42: `Path.rglob(pattern)` — the recursive shortcut

```python
# 3. rglob — equivalent to glob("**/" + pattern); shorter spelling
print("--- root.rglob('*.log') (recursive) ---")
for p in sorted(root.rglob("*.log")):
    print("  rglob:", p.relative_to(root))
```

`root.rglob("*.log")` is exactly equivalent to `root.glob("**/" + pattern)` — i.e. `root.glob("**/*.log")`. The `rglob` method is the *shortcut spelling* for the recursive case. The result is the same generator of `Path` objects; the only difference is the pattern you pass — `rglob` adds the `**/` prefix for you.

The output shows three matches: `boardly/logs/app.log`, `boardly/logs/crashes/oom-2024.log`, and `boardly/logs/crashes/segfault-2024.log`. The `app.log` file is two levels deep; the two `crashes/` files are three levels deep. The `**` matched the directory chain in each case.

The two spellings (`rglob` vs `glob` with `**/`) are functionally identical — pick whichever reads better in context. `rglob` is shorter and reads as "recursive glob"; `glob("**/" + pattern)` is more explicit about *what* the pattern does. The stdlib provides both because the recursive case is overwhelmingly common (you usually want "every file of type X under Y, at any depth"), and the shortcut spelling makes the common case shorter.

**Why does `rglob` exist as a separate method?** Because `glob("**/" + pattern)` requires the student to know that `**/` is the recursive marker, and that knowledge is not obvious from the pattern. The `rglob` spelling puts the recursion in the *method name* — `r` for "recursive" — so the call site reads as "recursive glob of pattern" without the student having to know the `**` convention. The stdlib added `rglob` in 3.5 alongside `glob`'s `**` for the same reason: the recursive case is common, and a one-letter method prefix is a clearer signal than a three-character pattern prefix.

### Lines 44–47: `glob` is lazy — it returns a generator

```python
# 4. glob is lazy: it returns a generator, materialised on iteration
gen = data_dir.glob("*.json")
print("--- generator type:", type(gen).__name__)
# Materialise once into a list to inspect; do NOT call list() twice
print("--- list(gen):", [p.name for p in sorted(gen)])
```

`gen = data_dir.glob("*.json")` does not actually scan the directory — it returns a *generator* object. The output `generator type: generator` confirms this: `Path.glob` returns a `generator`, not a `list`. The directory scan happens lazily, one entry at a time, when the generator is iterated.

`sorted(gen)` materialises the generator — it iterates it to exhaustion, collects the results into a list, sorts the list, and returns the sorted list. After this call, `gen` is *exhausted* — iterating it again yields nothing. This is the standard generator behaviour; it is not specific to `Path.glob`. The `sorted(...)` call in the demo materialises the generator once; the comment "do NOT call list() twice" is the warning that `list(gen)` followed by `list(gen)` returns `[<matches>]` then `[]` — the second call exhausts the already-exhausted generator.

The laziness matters for two reasons: (1) for directories with millions of entries, the generator uses constant memory — the list would use O(n) memory; (2) you can break out of iteration early (`for p in dir.glob("*.json"): if p.name == "target.json": return p`) and the generator stops scanning as soon as you return. The `list` form materialises everything before you can break.

**Why a generator and not a list?** Because laziness is the right default for I/O. A directory scan is an I/O operation; materialising the whole result up front means doing all the I/O before the caller has seen any of it. The generator form lets the caller control the I/O — they can break early, they can interleave with other I/O, they can pipe to a streaming consumer. The list form is available via `list(dir.glob(...))` if the caller wants it, but the default is lazy. The `glob` module's `glob.iglob` returns a generator for the same reason; `glob.glob` (without the `i`) returns a list because it predates the lazy form.

### Lines 49–55: The `case_sensitive=` parameter (Python 3.12+)

```python
# 5. case_sensitive kwarg (3.12+)
#    Default on Linux is case-SENSITIVE; *.json does NOT match Users.JSON
print("--- data_dir.glob('*.JSON') (default case) ---")
print("  matches:", [p.name for p in sorted(data_dir.glob("*.JSON"))])
print("--- data_dir.glob('*.JSON', case_sensitive=False) (3.12+) ---")
print("  matches:", [p.name for p in sorted(data_dir.glob("*.JSON", case_sensitive=False))])
```

`data_dir.glob("*.JSON")` — with the default `case_sensitive=None` — uses the filesystem's case-sensitivity. On Linux (case-sensitive `ext4`/`xfs`), `*.JSON` matches `Users.JSON` (capital `JSON`) and does *not* match `projects.json` (lowercase `json`). The output `matches: ['Users.JSON']` confirms this. On macOS (case-insensitive `APFS`) or Windows (case-insensitive `NTFS`), the same call would match both files.

`data_dir.glob("*.JSON", case_sensitive=False)` — with `case_sensitive=False` — *forces* case-insensitive matching regardless of the filesystem. The output `matches: ['Users.JSON', 'projects.json']` confirms this: both files match because the comparison is case-insensitive. The `case_sensitive=True` form would force case-sensitive matching (the Linux default on a case-insensitive filesystem — useful if you want to *ensure* the pattern matches case-sensitively even on macOS/Windows).

The `case_sensitive` parameter was added to `Path.glob` and `Path.rglob` in Python 3.12 (bpo-40602 / issue from the pathlib 3.12 overhaul). Before 3.12, there was no way to override the filesystem's case-sensitivity from `Path.glob`; the workaround was to scan with `iterdir()` and filter with `fnmatch.fnmatch` (case-insensitive) or `fnmatch.fnmatchcase` (case-sensitive) yourself. The 3.12 addition makes the override one keyword away.

The version-gate is clear: on Python 3.11 and earlier, `Path.glob(..., case_sensitive=False)` raises `TypeError: glob() got an unexpected keyword argument 'case_sensitive'`. On the 3.12 runtime this vault targets, the argument is available. If you are writing code that must run on 3.11, use `path.iterdir()` plus `fnmatch.fnmatch(path.name, pattern)` (case-insensitive) or `fnmatch.fnmatchcase` (case-sensitive) — but the pathlib 3.12+ `case_sensitive=` is the spelling you should use when you can.

**Why is the default `case_sensitive=None` and not `True` or `False`?** Because `None` means "use the filesystem's case-sensitivity", which is the principle of least surprise. On Linux, where the filesystem is case-sensitive, you expect `*.JSON` to match only capital-`JSON` files; on macOS/Windows, where the filesystem is case-insensitive, you expect it to match both. The `None` default preserves the filesystem's behaviour; the `True`/`False` overrides let you force a specific behaviour when you need it (e.g. cross-platform tests, or matching a case-insensitive spec like HTTP content-types on a case-sensitive filesystem). The `None` default was added in 3.12 specifically to make the filesystem-respecting behaviour the *explicit* default rather than the *implicit* behaviour, so students reading the call site see that the case-sensitivity is intentional.

### Lines 57–65: `glob` vs `iglob` — the difference

```python
# 6. glob vs iglob — the difference
#    pathlib.Path.glob is a method on Path; it returns Path objects.
#    The stdlib glob module's glob.glob returns a list of str.
#    glob.iglob returns a generator of str.
#    The "no glob.glob" rule: use Path.glob for new code.
import glob as glob_module
print("--- glob.glob (stdlib, returns list[str]) ---")
print("  ", [x for x in sorted(glob_module.glob(str(data_dir / "*.json")))])
print("--- glob.iglob (stdlib, returns generator[str]) ---")
ig = glob_module.iglob(str(data_dir / "*.json"))
print("  type:", type(ig).__name__, "->", sorted(ig))
```

The `glob` module (not `pathlib.Path.glob` — the standalone `glob` stdlib module) exposes two functions: `glob.glob(pattern, recursive=False, include_hidden=False, case_sensitive=None)` returns a `list[str]`, and `glob.iglob(pattern, recursive=False, include_hidden=False, case_sensitive=None)` returns a `generator[str]`. The two functions have identical pattern-matching behaviour; the only difference is the return type — `glob` materialises the list up front, `iglob` is lazy.

`glob_module.glob(str(data_dir / "*.json"))` builds the pattern string `"boardly/data/*.json"` (note: the `glob` module takes a *string* pattern, not a `Path` — you have to convert the path to `str` and embed it in the pattern). The result is `['/tmp/.../boardly/data/projects.json']` — a `list[str]`. Each element is a *string path*, not a `Path`. To do anything useful with it, you wrap it in `Path(...)`: `for path_str in result: path = Path(path_str); ...`. The wrap is the bug the pathlib API was designed to eliminate.

`glob_module.iglob(str(data_dir / "*.json"))` returns a `generator` of `str` — lazy, same pattern-matching behaviour. The result is the same set of paths, just materialised lazily. The wrap-in-`Path` problem is identical.

The "no `glob.glob` in new code" rule has three reasons: (1) `Path.glob` returns `Path` objects, not `str` — the loop body has the full pathlib API; (2) `Path.glob` takes a relative pattern, so the call site reads as `data_dir.glob("*.json")` rather than `glob.glob(str(data_dir) + "/*.json")` — shorter and clearer; (3) `Path.glob` and `Path.rglob` compose with the rest of the pathlib API (`.read_text`, `.parent`, etc.) without conversion. The `glob` module is fine for legacy code that already uses `str` paths; for new code that holds a `Path`, the pathlib methods are the spelling.

**Why does the `glob` module still exist?** Because legacy code uses it, and the stdlib does not break backwards compatibility. The `glob` module predates `pathlib` (it was added in Python 2.2; `pathlib` was added in 3.4), and there are millions of lines of `glob.glob` in production. The stdlib's policy is to keep both — `pathlib.Path.glob` for new code, `glob.glob` for legacy — and let students learn the difference. The rule "no `glob.glob` in new code" is the same shape as "no `os.path.join` in new code": the older API works, the newer API is better, and the lint rule is to prefer the newer one.

### Lines 67–71: Version-gate summary

```python
# 7. Version gate summary
print("---")
print("Python:", sys.version.split()[0])
print("Path.glob signature:", __import__("inspect").signature(Path.glob))
print("Path.rglob signature:", __import__("inspect").signature(Path.rglob))
```

The closing block prints the Python version (3.12.15 on the sandbox) and the signatures of `Path.glob` and `Path.rglob`. The signatures are `(self, pattern, *, case_sensitive=None)` — note the `*` separating positional `pattern` from keyword-only `case_sensitive`, which means `case_sensitive` must be passed as a keyword argument, not positionally. The version-gate is clear: `case_sensitive` is 3.12+; on 3.11 and earlier, the signature is `(self, pattern)` with no `case_sensitive` argument.

The `__import__("inspect").signature(Path.glob)` call is the runtime feature-detection pattern: ask the stdlib what arguments the function takes, and adapt. For application code that needs `case_sensitive`, the import-time pattern is `import sys; if sys.version_info >= (3, 12): use_case_sensitive_kwarg(); else: use_fnmatch_workaround()`. The runtime pattern (signature inspection) is more flexible but slower; the import-time pattern is faster but coarser. Use whichever fits your case.

## Execution Trace

```bash
$ uv run python boardly/paths/glob_demo.py
--- data_dir.glob('*.json') (direct children only) ---
  glob: projects.json
--- root.glob('**/*.json') (recursive) ---
  **: boardly/data/archive/archive.2024.json
  **: boardly/data/archive/archive.2025.json
  **: boardly/data/projects.json
--- root.rglob('*.log') (recursive) ---
  rglob: boardly/logs/app.log
  rglob: boardly/logs/crashes/oom-2024.log
  rglob: boardly/logs/crashes/segfault-2024.log
--- generator type: generator
--- list(gen): ['projects.json']
--- data_dir.glob('*.JSON') (default case) ---
  matches: ['Users.JSON']
--- data_dir.glob('*.JSON', case_sensitive=False) (3.12+) ---
  matches: ['Users.JSON', 'projects.json']
--- glob.glob (stdlib, returns list[str]) ---
   ['/tmp/tmpj3fyrs0m/boardly/data/projects.json']
--- glob.iglob (stdlib, returns generator[str]) ---
  type: generator -> ['/tmp/tmpj3fyrs0m/boardly/data/projects.json']
---
Python: 3.12.15
Path.glob signature: (self, pattern, *, case_sensitive=None)
Path.rglob signature: (self, pattern, *, case_sensitive=None)
```

The `/tmp/tmpj3fyrs0m/` prefix on the `glob.glob` and `glob.iglob` lines is the tmpdir the demo created; the prefix changes on every run, but the rest of the line is deterministic. The `generator type: generator` line confirms `Path.glob` is lazy. The `matches: ['Users.JSON']` line (default case) and `matches: ['Users.JSON', 'projects.json']` line (`case_sensitive=False`) confirm the case-sensitivity override works on the 3.12 runtime.

## Common Mistakes

### Mistake 1: Treating `glob` as a list

```python
files = data_dir.glob("*.json")    # generator, not list
files.append(extra)                 # AttributeError: 'generator' object has no attribute 'append'
```

**Symptom:** `AttributeError: 'generator' object has no attribute 'append'` (or `extend`, `sort`, etc.) when you try to mutate the result of `Path.glob`.
**Why:** `Path.glob` returns a *generator*, not a list. Generators are single-use iterators — they support `for ... in`, `next()`, and `sorted()`, but not list methods. The laziness is a feature (constant memory on large directories, early-exit support); the cost is that you cannot mutate the result in place.
**Fix:** Materialise the generator into a list if you need list operations: `files = list(data_dir.glob("*.json"))`. Or use `sorted(data_dir.glob("*.json"))` if you need a sorted list. The `list(...)` call iterates the generator to exhaustion and collects the results; after that, `files` is a `list[Path]` you can mutate. Do not call `list(gen)` twice on the same generator — the second call returns `[]`.

### Mistake 2: Using `*` when you meant `**`

```python
# Find every .log file under boardly, at any depth
for p in Path("boardly").glob("*.log"):    # WRONG — only direct children
    ...
```

**Symptom:** The loop body sees only the `.log` files directly under `boardly/` (e.g. `boardly/app.log`), and misses the ones in subdirectories (`boardly/logs/crashes/oom-2024.log`).
**Why:** The `*` wildcard matches "any sequence of characters *in a single path component*" — it does not cross `/`. So `boardly/*.log` matches `boardly/app.log` but not `boardly/logs/app.log`. To cross `/`, you need the `**` recursive marker.
**Fix:** Use `Path("boardly").rglob("*.log")` (the recursive shortcut) or `Path("boardly").glob("**/*.log")` (the explicit `**` form). Both walk the tree recursively. The two are functionally identical; `rglob` is shorter, `glob` with `**` is more explicit about what the pattern does.

### Mistake 3: Forgetting the `case_sensitive=` version gate

```python
files = data_dir.glob("*.JSON", case_sensitive=False)    # 3.12+ only
```

**Symptom:** `TypeError: glob() got an unexpected keyword argument 'case_sensitive'` on Python 3.11 and earlier.
**Why:** The `case_sensitive` parameter was added to `Path.glob` and `Path.rglob` in Python 3.12. On 3.11 and earlier, the signature is `(self, pattern)` with no `case_sensitive` argument; passing it raises `TypeError`. The 3.12 runtime this vault targets supports the argument; older runtimes do not.
**Fix:** Version-gate the call. For application code that must run on 3.11, use `path.iterdir()` plus `fnmatch.fnmatch(path.name, pattern)` (case-insensitive) or `fnmatch.fnmatchcase(path.name, pattern)` (case-sensitive). For code that targets 3.12+ (like this vault), pass `case_sensitive=False` directly. The runtime feature-detection pattern (signature inspection) is also viable but slower; the import-time pattern (`sys.version_info >= (3, 12)`) is the standard spelling.

### Mistake 4: Using `glob.glob` in new code

```python
import glob
files = glob.glob("boardly/data/*.json")    # list[str], not list[Path]
for path_str in files:
    path = Path(path_str)                    # re-wrap every element
    text = path.read_text(encoding="utf-8")
```

**Symptom:** The loop body has to re-wrap every `path_str` in `Path(...)` to use the pathlib API, which is two extra lines per loop and a `str`-to-`Path` conversion on every iteration.
**Why:** The `glob` module predates `pathlib` and returns `str`, not `Path`. The two APIs are not interchangeable — `glob.glob` returns `list[str]`, `Path.glob` returns `generator[Path]`. The `str` form has no `.read_text`, no `.parent`, no `.stem` — you reconstruct the `Path` on every iteration.
**Fix:** Use `Path("boardly/data").glob("*.json")` — the result is `Path` objects, the loop body has the full pathlib API, and there is no re-wrap. The "no `glob.glob` in new code" rule is the lint: `rg "glob\.glob\(" boardly/` should return zero matches. The `glob` module is fine for legacy code that already uses `str` paths; for new code that holds a `Path`, the pathlib methods are the spelling.

## Engineering Trade-Offs

**Decision:** Use `Path.glob` and `Path.rglob` for all file-discovery in `boardly`. Never `glob.glob`. Never `os.walk` for tree iteration in new code (use `Path.walk` on 3.12+, lesson 06).
**Both sides:** The alternative is the `glob` module (`glob.glob` returns `list[str]`, `glob.iglob` returns `generator[str]`) or `os.walk` (the recursive directory walker). `glob.glob` loses to `Path.glob` on the result type — `str` vs `Path` — and on the call-site brevity (`glob.glob(str(path) + "/*.json")` vs `path.glob("*.json")`). `os.walk` loses on the result shape — it yields `(dirpath, dirnames, filenames)` triples, forcing you to re-join the dirpath with each filename by hand; `Path.rglob` yields `Path` objects directly. The one place `os.walk` wins is when you need to *modify* the directory tree as you walk it (e.g. prune `dirnames` to skip subtrees), which `Path.rglob` does not support — `Path.walk` (3.12+, lesson 06) is the pathlib replacement.
**Commitment:** `boardly` uses `Path.glob` for non-recursive matching and `Path.rglob` for recursive matching. The `case_sensitive=` parameter is used on 3.12+ for case-insensitive matches (e.g. matching `.JSON` and `.json` files from Windows-edited exports). The `glob` module is forbidden in new code; the lint rule is `rg "glob\.glob\(" boardly/` returning zero matches. `os.walk` is replaced by `Path.walk` on 3.12+ (lesson 06 walks the `walk` API in detail).

## Exercises

1. **Exercise 1 — Change the pattern.** Modify the demo to use `data_dir.glob("*.JSON")` (capital) and re-run. Confirm the default case matches only `Users.JSON` on Linux. Then change to `case_sensitive=False` and confirm both files match. `Verify: uv run python boardly/paths/glob_demo.py | rg 'case'`
2. **Exercise 2 — Find every `.log` file recursively.** Use `Path.rglob` to find every `.log` file under `logs_dir`. Confirm the count is 3 (`app.log`, `oom-2024.log`, `segfault-2024.log`). `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); 
logs = td / 'boardly' / 'logs'
logs.mkdir(parents=True)
(logs / 'app.log').write_text('x', encoding='utf-8')
cr = logs / 'crashes'
cr.mkdir()
(cr / 'oom-2024.log').write_text('x', encoding='utf-8')
(cr / 'segfault-2024.log').write_text('x', encoding='utf-8')
assert sum(1 for _ in logs.rglob('*.log')) == 3; print('count ok')"`
3. **Exercise 3 — Use the `**` pattern explicitly.** Reproduce the `rglob("*.log")` result using `glob("**/*.log")`. Confirm the two calls return the same set of paths (compare as sorted lists). `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); 
logs = td / 'boardly' / 'logs'
logs.mkdir(parents=True)
(logs / 'app.log').write_text('x', encoding='utf-8')
a = sorted(logs.rglob('*.log'))
b = sorted(logs.glob('**/*.log'))
assert a == b; print('equivalent ok')"`
4. **Exercise 4 — Verify the generator is lazy.** Write a generator that yields from `data_dir.glob("*.json")` and breaks after the first match. Confirm the generator is not exhausted (you can iterate it again from the start, but the same `gen` object is exhausted). `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); d = td / 'data'
d.mkdir(parents=True)
(d / 'a.json').write_text('{}', encoding='utf-8')
(d / 'b.json').write_text('{}', encoding='utf-8')
gen = d.glob('*.json')
first = next(gen)
print('first:', first.name)
second = next(gen)
print('second:', second.name)
print('lazy ok')"`
5. **Exercise 5 — Write a `find_archives(root, year)` helper.** Write a function that finds every `archive.<year>.json` file under `root` recursively, using `Path.rglob` and a `*` pattern. The function should return a `list[Path]`, sorted by name. Test it with year 2024 and confirm it returns one match in the demo tree. `Verify: uv run python -c "from pathlib import Path; import sys, tempfile; sys.path.insert(0, 'boardly/paths'); from glob_demo import find_archives; 
td = Path(tempfile.mkdtemp())
root = td / 'boardly'
data = root / 'data'
archive = data / 'archive'
archive.mkdir(parents=True)
(archive / 'archive.2024.json').write_text('{}', encoding='utf-8')
(archive / 'archive.2025.json').write_text('{}', encoding='utf-8')
res = find_archives(root, 2024)
assert len(res) == 1 and res[0].name == 'archive.2024.json'; print('archives ok')"` (you will need to add the `find_archives` function to `glob_demo.py` for this exercise).

## Verification

```bash
$ uv run python boardly/paths/glob_demo.py
--- data_dir.glob('*.json') (direct children only) ---
  glob: projects.json
--- root.glob('**/*.json') (recursive) ---
  **: boardly/data/archive/archive.2024.json
  **: boardly/data/archive/archive.2025.json
  **: boardly/data/projects.json
--- root.rglob('*.log') (recursive) ---
  rglob: boardly/logs/app.log
  rglob: boardly/logs/crashes/oom-2024.log
  rglob: boardly/logs/crashes/segfault-2024.log
--- generator type: generator
--- list(gen): ['projects.json']
--- data_dir.glob('*.JSON') (default case) ---
  matches: ['Users.JSON']
--- data_dir.glob('*.JSON', case_sensitive=False) (3.12+) ---
  matches: ['Users.JSON', 'projects.json']
--- glob.glob (stdlib, returns list[str]) ---
   ['/tmp/tmpj3fyrs0m/boardly/data/projects.json']
--- glob.iglob (stdlib, returns generator[str]) ---
  type: generator -> ['/tmp/tmpj3fyrs0m/boardly/data/projects.json']
---
Python: 3.12.15
Path.glob signature: (self, pattern, *, case_sensitive=None)
Path.rglob signature: (self, pattern, *, case_sensitive=None)
```

The `generator type: generator` line confirms `Path.glob` is lazy. The `matches: ['Users.JSON']` (default) and `matches: ['Users.JSON', 'projects.json']` (`case_sensitive=False`) lines confirm the case-sensitivity override works on the 3.12 runtime. The `Path.glob signature` line includes the `case_sensitive` keyword-only argument, confirming the 3.12+ signature.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `Path` construction and `/` operator this lesson uses to build `root`, `data_dir`, `logs_dir`; the basics lesson is the foundation for the glob methods.
- [[08-pathlib/02-read-write-text-binary]] — the `write_text(encoding="utf-8")` calls this lesson uses to seed the demo tree; the I/O lesson is where the file-creation methods are walked.

## What's Next

[[08-pathlib/04-mkdir-rmdir-unlink]] — Now that you can find files, the next lesson makes the `Path` *mutate* the filesystem. `Path.mkdir(parents=True, exist_ok=True)` is the `mkdir -p` spelling; `Path.rmdir()` removes an empty directory; `Path.unlink(missing_ok=True)` removes a file (the `missing_ok` kwarg is 3.8+); `Path.touch()` creates an empty file or updates its mtime; `Path.rename(target)` and `Path.replace(target)` move files (with the POSIX-overwrite-vs-Windows-raises distinction). The lesson covers the directory-vs-file distinction that catches out ex-`os` users, and the `FileExistsError`/`FileNotFoundError` boundaries that the methods raise.

- **Lesson 04** — `mkdir`, `rmdir`, `unlink`, `touch`, `rename`, `replace` for filesystem mutation.
- **Lesson 05** — `PurePath` vs `Path` (the no-I/O string-algebra base class).

## Sources

- **Python `pathlib` module documentation** — https://docs.python.org/3/library/pathlib.html — accessed 2026-10-23 — the source-of-truth reference for `Path.glob`, `Path.rglob`, the `**` pattern, and the `case_sensitive` parameter (3.12+).
- **Python `glob` module documentation** — https://docs.python.org/3/library/glob.html — accessed 2026-10-23 — the older `glob.glob` / `glob.iglob` API this lesson replaces; documents the `recursive=True` keyword and the `case_sensitive` parameter added in 3.12.
- **Python `fnmatch` module documentation** — https://docs.python.org/3/library/fnmatch.html — accessed 2026-10-23 — the pattern-matching engine `Path.glob` uses internally; documents `fnmatch` (case-insensitive) vs `fnmatchcase` (case-sensitive) for the pre-3.12 workaround.

## What We Learned

- You can now call `Path.glob(pattern)` for non-recursive matching of direct children, and explain that the result is a *generator* of `Path` objects (lazy, materialised on iteration).
- You can call `Path.rglob(pattern)` for recursive matching and explain that it is exactly equivalent to `Path.glob("**/" + pattern)`.
- You can use the `**` pattern to match any number of directories (including zero) and explain why `*` does not cross `/`.
- You can use the `case_sensitive=` parameter (3.12+) to force case-insensitive matching on a case-sensitive filesystem, and version-gate the parameter for code that must run on 3.11.
- You can state the rule: never write `glob.glob` in new code. Use `Path.glob` / `Path.rglob` because the result is `Path` objects, not `str`, and the loop body has the full pathlib API.
