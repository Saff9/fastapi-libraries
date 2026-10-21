---
title: "Lesson 06: walk and iterdir"
aliases:
 - pathlib iterdir
 - pathlib walk
 - Path.walk
 - top_down pruning
 - rglob vs walk
 - os.walk replacement
tags:
 - pathlib
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
 - "[[08-pathlib/03-glob-and-rglob]]"
 - "[[08-pathlib/05-PurePath-vs-Path]]"
related_lessons:
 - "[[08-pathlib/07-stat-and-permissions]]"
 - "[[03-contextlib/04-suppress]]"
first_taught_in: "08-pathlib/06-walk-and-iterdir"
---

# Lesson 06: walk and iterdir

*How `boardly`'s log-archival job walks `boardly/logs/` and prunes `.git`, `__pycache__`, and `.venv` mid-traversal — and why the 3.12+ `Path.walk()` method replaced `os.walk`.*

**You're at the very beginning of Section 08 — six lessons in. This is the traversal lesson.**

You know what `Path` is and you know the difference between `PurePath` and `Path`. Now we cross into the I/O surface and meet the three traversal methods. `Path.iterdir()` lists the immediate children of a directory — flat, one level, lazy. `Path.walk(top_down=True, on_error=None, follow_symlinks=False)` is the 3.12+ recursive walker, yielding `(dirpath, dirnames, filenames)` tuples, and it is the method that finally retired `os.walk` in idiomatic Python. `Path.rglob("*")` is the recursive glob, the pre-3.12 way to recurse, still useful when you do not need to prune. The headline of this lesson is the pruning trick: with `top_down=True` (the default), you can mutate the `dirnames` list in-place to *prevent* the walker from descending into directories you want to skip. That is the one capability `rglob` does not have, and the one reason `walk` is the right tool when you need it. Take your time. Type every example. **This is how you learn.**

#pathlib #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use `Path.iterdir()` for non-recursive listing** — call it on a directory and iterate the lazy generator of immediate `Path` children (files and sub-directories, no recursion). Know it is the `Path` analogue of `os.listdir`, but yields `Path` objects, not strings.
2. **Use `Path.walk(top_down=True, on_error=None, follow_symlinks=False)`** for recursive traversal — unpack each `(dirpath, dirnames, filenames)` tuple, version-gate the method to Python 3.12+ (PEP-related: the pathlib walk method landed in 3.12), and know it is the modern replacement for `os.walk`.
3. **Prune `dirnames` in-place** to skip directories mid-walk — remove entries from the `dirnames` list (mutating the list, not rebinding it) before the next iteration when `top_down=True`, and explain why `top_down=False` disables pruning.
4. **Choose `rglob("*")` vs `walk()`** — pick `rglob` when you want a flat list of matches with no per-directory decisions; pick `walk` when you need to prune (`.git`, `__pycache__`, `.venv`), or when the per-directory tuple shape (with `dirnames` and `filenames` separated) makes your loop clearer.
5. **Handle `on_error`** — pass `on_error=None` (the default, which silently swallows OS errors) or a callable that takes an `OSError` and decides whether to raise, log, or continue.
6. **Reason about `follow_symlinks=False`** — explain why the default is False (defends against symlink loops), and explain when to flip it to True (you genuinely want to follow a known-good symlink into a real sub-tree).

## Prerequisites

Before starting, you need:

- **The `Path` constructor and the `/` operator** — [[08-pathlib/01-Path-Basics]]. The lesson builds directories with `Path("boardly/logs") / "subdir"`.
- **`glob()` and `rglob()`** — [[08-pathlib/03-glob-and-rglob]]. The lesson compares `walk` against `rglob` directly; if you have not seen `rglob` you will miss half the comparison.
- **The `PurePath` vs `Path` split** — [[08-pathlib/05-PurePath-vs-Path]]. `iterdir`, `walk`, and `rglob` are all `Path` methods — none of them exist on `PurePath` because they all touch the disk. The lesson assumes you already understand why.
- **About 35–50 minutes of focused time.**

**The most common gap: assuming `os.walk` is still the right tool.**

It is not. Python 3.12 (released October 2023) added `Path.walk()` to the concrete `Path` class, and the pathlib documentation now describes it as the canonical recursive walker. `os.walk` still works (it is not deprecated), but the pathlib version returns `Path` objects (not `str`) for `dirpath`, integrates with the rest of the `Path` API (you can call `.stat()` or `.is_file()` on the yielded `dirpath` without rewrapping), and respects the `follow_symlinks=False` default that prevents the most common symlink-loop bug. Students who learned Python before 3.12 reach for `os.walk` out of habit; the lesson shows the new shape and explains where the old shape still wins (nowhere, for new code).

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/logs/archive_bad.py — the bad old days
import os
import shutil

def archive_logs(root: str) -> list[str]:
    """Walk boardly/logs/ and archive every *.log file older than 30 days."""
    archived = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".log"):
                full = os.path.join(dirpath, name)
                # ... archive logic ...
                archived.append(full)
    return archived
```

You ship that. A boardly worker runs it nightly. The walk descends into `boardly/logs/.git/objects/pack/` — because somebody initialized a git repo inside the logs directory by accident — and tries to archive 50,000 git pack files. Then it descends into `boardly/logs/.venv/lib/python3.12/site-packages/` because somebody ran `uv venv` in the wrong directory, and tries to archive another 8,000 `.log` files that are pip's logging shims. The job takes six hours, fills the archive bucket, costs the company four hundred dollars in S3 PUT requests, and pages you at 2 a.m. because the disk is full.

Worse: you cannot prune with `rglob`. `rglob` returns a flat generator of `Path` objects; the API does not expose `dirnames`. Once you call `Path(root).rglob("*.log")`, the walk is committed — there is no way to say "skip `.git`". You can filter *after* the fact (post-filter the returned `Path` objects by checking `".git" in p.parts`), but the walk has already touched every directory. The disk reads have already happened. The fix is `walk` with `top_down=True` and a `dirnames.remove(".git")` call, which prevents the walker from descending into `.git` at all.

The second bug is more subtle: `os.walk` yields `str` for `dirpath`, so `full = os.path.join(dirpath, name)` re-enters the `os.path` string-API world. Every `Path`-method call downstream (`Path(full).stat()`, `Path(full).read_text()`) rewraps a string into a `Path` — losing the type-level cleanliness that made you switch to `pathlib` in the first place. `Path.walk()` yields `Path` for `dirpath`, so `dirpath / name` is a pure `/`-operator join with no rewrap.

## The Code

```python
# boardly/logs/walk_demo.py
"""iterdir, walk, and rglob — the three traversal methods."""
from pathlib import Path


# 0. Build a small boardly/logs/ tree to walk
def build_demo_tree(base: Path) -> None:
    """Idempotent: create the demo tree under base."""
    if base.exists():
        return
    (base / "2026-10-23").mkdir(parents=True)
    (base / "2026-10-23" / "app.log").write_text("line\n")
    (base / "2026-10-23" / "error.log").write_text("boom\n")
    (base / "2026-10-24").mkdir()
    (base / "2026-10-24" / "app.log").write_text("line2\n")
    (base / ".git").mkdir()
    (base / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (base / ".git" / "objects").mkdir()
    (base / ".git" / "objects" / "pack").mkdir()
    (base / ".git" / "objects" / "pack" / "big.pack").write_text("PACK")
    (base / ".venv").mkdir()
    (base / ".venv" / "lib").mkdir()
    (base / ".venv" / "lib" / "site-packages").mkdir()
    (base / ".venv" / "lib" / "site-packages" / "pip.log").write_text("pip")


# 1. iterdir — immediate children, non-recursive, lazy
def iterdir_demo(root: Path) -> None:
    print("\n=== iterdir (immediate children, non-recursive) ===")
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        kind = "DIR " if child.is_dir() else "FILE"
        print(f"  {kind} {child.name}")


# 2. walk top_down=True (default) — recursive, no pruning
def walk_no_prune(root: Path) -> None:
    print("\n=== walk top_down=True (no pruning) ===")
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames.sort()                       # deterministic visit order
        rel = dirpath.relative_to(root)
        print(f"  {rel}  dirs={dirnames}  files={sorted(filenames)}")


# 3. walk with pruning — skip .git and .venv mid-walk
def walk_pruned(root: Path) -> None:
    print("\n=== walk with pruning (skip .git and .venv) ===")
    skip = {".git", ".venv", "__pycache__", ".mypy_cache"}
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        # Mutate dirnames IN PLACE to prune the walk
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        rel = dirpath.relative_to(root)
        print(f"  {rel}  dirs={dirnames}  files={sorted(filenames)}")


# 4. rglob — flat recursive glob, no per-directory decisions
def rglob_demo(root: Path) -> None:
    print('\n=== rglob("*.log") — flat, recursive ===')
    for p in sorted(root.rglob("*.log")):
        print(f"  {p.relative_to(root)}")


# 5. on_error — handle permission errors instead of silently swallowing
def walk_with_error_handler(root: Path) -> None:
    print("\n=== walk with on_error handler ===")

    def report(exc: OSError) -> None:
        print(f"  [skip] {exc.filename}: {exc.strerror}")

    for dirpath, dirnames, filenames in root.walk(
        top_down=True, on_error=report
    ):
        dirnames.sort()
        rel = dirpath.relative_to(root)
        print(f"  {rel}  files={len(filenames)}")


# 6. follow_symlinks=False (default) defends against symlink loops
def walk_symlink_safe(root: Path) -> None:
    print("\n=== walk follow_symlinks=False (default) ===")
    count = 0
    for dirpath, _, filenames in root.walk(follow_symlinks=False):
        count += len(filenames)
    print(f"  total files (no symlink follow): {count}")


# 7. The boardly archival job — the real-world shape
def archive_logs(root: Path) -> list[Path]:
    """Walk boardly/logs/, skip .git/.venv, archive *.log files."""
    archived: list[Path] = []
    skip = {".git", ".venv", "__pycache__"}
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames[:] = [d for d in dirnames if d not in skip]
        dirnames.sort()                   # deterministic visit order
        for name in filenames:
            if name.endswith(".log"):
                archived.append(dirpath / name)
    return archived


if __name__ == "__main__":
    base = Path("/tmp/boardly-walk-demo")
    build_demo_tree(base)

    iterdir_demo(base)
    walk_no_prune(base)
    walk_pruned(base)
    rglob_demo(base)
    walk_with_error_handler(base)
    walk_symlink_safe(base)

    print("\n=== boardly archive_logs result ===")
    for p in archive_logs(base):
        print(f"  archived: {p.relative_to(base)}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 7–26: Building the demo tree

```python
def build_demo_tree(base: Path) -> None:
    """Idempotent: create the demo tree under base."""
    if base.exists():
        return
    (base / "2026-10-23").mkdir(parents=True)
    (base / "2026-10-23" / "app.log").write_text("line\n")
    (base / "2026-10-23" / "error.log").write_text("boom\n")
    (base / "2026-10-24").mkdir()
    (base / "2026-10-24" / "app.log").write_text("line2\n")
    (base / ".git").mkdir()
    (base / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (base / ".git" / "objects").mkdir()
    (base / ".git" / "objects" / "pack").mkdir()
    (base / ".git" / "objects" / "pack" / "big.pack").write_text("PACK")
    (base / ".venv").mkdir()
    (base / ".venv" / "lib").mkdir()
    (base / ".venv" / "lib" / "site-packages").mkdir()
    (base / ".venv" / "lib" / "site-packages" / "pip.log").write_text("pip")
```

The setup builds the exact tree the lesson's headline bug describes: dated log sub-directories (`2026-10-23`, `2026-10-24`) with real `.log` files, plus the two poison directories — `.git` with a deeply nested `objects/pack/big.pack`, and `.venv` with a `pip.log` shim deep inside `lib/site-packages/`. The walk demos below will descend into these poison directories when unpruned and skip them when pruned; the contrast is the lesson.

`Path.mkdir(parents=True)` creates the directory and any missing parents — without `parents=True`, mkdir would raise `FileNotFoundError` if `base` itself did not exist. `Path.write_text("...")` creates the file (or truncates it) and writes the string. The `if base.exists(): return` guard makes the function idempotent — running the script twice does not raise `FileExistsError` on the second run. Note that this guard has a TOCTOU (time-of-check, time-of-use) window between `exists()` and `mkdir()`, but for a demo script under `/tmp` the window is acceptable; for production you would use `Path.mkdir(parents=True, exist_ok=True)` and let the OS be the source of truth.

**Why `Path` and not `str` for the `base` parameter?** Because the `/` operator on `Path` returns a `Path` — every `(base / "2026-10-23")` expression in this function returns a `Path` that we can call `.mkdir()` on directly, no rewrap. If `base` were a `str`, every join would be `os.path.join(base, "2026-10-23")` returning a `str`, and every subsequent `.mkdir()` would need a `Path(...)` rewrap. The `Path` annotation keeps the entire function in the `Path` API.

### Lines 29–34: `iterdir` — non-recursive, immediate children

```python
def iterdir_demo(root: Path) -> None:
    print("\n=== iterdir (immediate children, non-recursive) ===")
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        kind = "DIR " if child.is_dir() else "FILE"
        print(f"  {kind} {child.name}")
```

`Path.iterdir()` returns a *generator* (technically a `_SelectorIterator` in CPython's implementation, but it satisfies the generator protocol) yielding `Path` objects for each immediate child of `root` — files and directories at the top level, no recursion. The order is filesystem-dependent (not sorted); for deterministic output, the demo wraps in `sorted(root.iterdir(), key=lambda p: p.name)`. The yielded `Path` objects are concrete (`PosixPath` on Linux), so `child.is_dir()` calls `os.stat` on the child and returns True if the child is a directory. Each iteration is one `os.stat` call — lazy evaluation means we only stat the children we actually consume.

**Why `iterdir()` instead of `os.listdir()`?** Three reasons. First, the return type is `Path` objects, not strings — no rewrap when you call `.is_dir()` or `.read_text()` on the result. Second, `iterdir()` is a generator: it does not materialise the full list before yielding, which matters for directories with millions of entries. Third, the iteration is interruptible — you can `break` out of the loop and the generator is garbage-collected, freeing the directory handle. `os.listdir()` returns a full list and is not interruptible mid-construction. The laziness is a real win on huge directories.

**Why `key=lambda p: p.name` and not the default `sorted(root.iterdir())`?** Because the default sort key for `Path` objects is the *whole* path string, not the name. For a directory listing where every entry shares the same parent, the two give the same order — but if you ever mix in paths from other directories, the default sort breaks the directory-grouping. Sorting by `.name` explicitly is the safe form.

**Warning — `iterdir()` on a non-existent directory raises `FileNotFoundError`.**

`Path.iterdir()` calls `os.scandir` under the hood, which raises `FileNotFoundError` if the directory does not exist. If you are not sure the directory exists, guard with `if root.is_dir():` first, or use `try/except FileNotFoundError` (or `contextlib.suppress(FileNotFoundError)`, see [[03-contextlib/04-suppress]]).

### Lines 37–42: `walk(top_down=True)` — no pruning, the baseline

```python
def walk_no_prune(root: Path) -> None:
    print("\n=== walk top_down=True (no pruning) ===")
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames.sort()                       # deterministic visit order
        rel = dirpath.relative_to(root)
        print(f"  {rel}  dirs={dirnames}  files={sorted(filenames)}")
```

`Path.walk(top_down=True, on_error=None, follow_symlinks=False)` is the 3.12+ recursive walker. Each iteration yields a 3-tuple: `(dirpath: Path, dirnames: list[str], filenames: list[str])`. The `dirpath` is a concrete `Path` object (not a `str`, unlike `os.walk`) — you can call `.stat()` or `.is_dir()` on it directly. The `dirnames` and `filenames` are *lists of strings* — the names of immediate children, not their full paths. To get the full path of a child, join: `dirpath / name`.

`top_down=True` (the default) means each directory's tuple is yielded *before* the directory's sub-directories are visited. That ordering is what makes pruning work: when you receive the tuple for `boardly/logs/`, you see `.git` and `.venv` in `dirnames` *before* the walker descends into them, so you can remove them from the list and the walker skips them entirely. With `top_down=False`, sub-directories are visited *first* and then the parent's tuple is yielded — by the time you receive the parent tuple, the walker has already descended into `.git` and `.venv`, so pruning is impossible. Always use `top_down=True` when you intend to prune.

**Note — `dirpath.relative_to(root)` requires `dirpath` to be a descendant of `root`.**

The `Path.relative_to()` method raises `ValueError` if the path is not a descendant of the argument. `walk()` always yields `dirpath` values that are descendants of `root` (or equal to `root`, in which case `relative_to` returns `Path(".")`), so this is safe. If you ever pass a different `root` mid-loop (you should not), the `relative_to` call would raise. The same safety applies when `follow_symlinks=True` and a symlink points outside the tree — `relative_to` may raise; that is a real bug to watch for.

### Lines 45–52: `walk` with in-place pruning

```python
def walk_pruned(root: Path) -> None:
    print("\n=== walk with pruning (skip .git and .venv) ===")
    skip = {".git", ".venv", "__pycache__", ".mypy_cache"}
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        # Mutate dirnames IN PLACE to prune the walk
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        rel = dirpath.relative_to(root)
        print(f"  {rel}  dirs={dirnames}  files={sorted(filenames)}")
```

This block is the lesson's headline. The line `dirnames[:] = sorted(d for d in dirnames if d not in skip)` is *in-place* mutation of the `dirnames` list — the slice assignment `dirnames[:] = ...` replaces the *contents* of the list without rebinding the name. The walker keeps a reference to the same list object, so when it consults `dirnames` to decide which sub-directories to descend into next, it sees your filtered list. The directories in `skip` (`.git`, `.venv`, `__pycache__`, `.mypy_cache`) are removed before the walker's recursion proceeds, so their contents are never visited. The disk reads that would have descended into those sub-trees never happen.

The slicing assignment `dirnames[:] = ...` is the *idiomatic* form. You could also write `dirnames.clear(); dirnames.extend([d for d in dirnames if d not in skip])` — but the slicing form is the one you will see in the CPython `os.walk` documentation, and the one every senior Python engineer recognises. Rebinding (`dirnames = [d for d in dirnames if d not in skip]`) does *not* work — you create a new list, the walker still holds the old list, the pruning never reaches the walker's recursion.

The `sorted(d for d in ...)` wrapper is a *display* nicety — it makes the printed `dirnames` (and the walker's visit order) deterministic, so the Execution Trace below is reproducible across runs and filesystems. The pruning itself works without the `sorted` call; the call only affects order, not membership. In production you would usually skip the `sorted` (the walker visits in filesystem order, which is the cheapest) and only sort at the point of display.

**Why a set for `skip` and not a list?** Because the `d not in skip` check is `O(1)` on a set and `O(n)` on a list. For four entries the difference is invisible, but the idiomatic form scales: a `boardly` skip-list might grow to 20+ entries (every cache directory under the sun), and the `in` check runs once per directory name per directory tuple. Set membership is the right shape. The same shape applies to `filenames` filtering, but `filenames` is not prunable — mutating it does not affect the walk (the walker does not consult `filenames` for recursion decisions).

**Why mutate `dirnames` and not just `continue` on the directories you want to skip?** Because `continue` happens *after* the walker has already descended. The walker's flow is: (1) yield the parent tuple, (2) iterate `dirnames`, (3) for each name in `dirnames`, recurse into `parent / name`. If you `continue` on a parent tuple, you skip the *current* iteration's body but the walker has still scheduled the recursion into the children — you have not pruned anything. To actually skip the recursion, you must remove the name from `dirnames` *before* the walker reads the list back to decide what to recurse into. That is what `dirnames[:] = ...` does. There is no other API for pruning.

### Lines 55–59: `rglob` — flat recursive glob, the pre-3.12 alternative

```python
def rglob_demo(root: Path) -> None:
    print('\n=== rglob("*.log") — flat, recursive ===')
    for p in sorted(root.rglob("*.log")):
        print(f"  {p.relative_to(root)}")
```

`Path.rglob(pattern)` returns a generator of `Path` objects matching the glob pattern, recursively. The `"*.log"` pattern matches any filename ending in `.log`, at any depth. The output is a flat list — there is no per-directory tuple, no `dirnames` to prune. You cannot skip `.git` or `.venv` from inside the `rglob` call. You can only filter the returned `Path` objects after the fact — but the disk reads to enumerate those directories have already happened.

`sorted(root.rglob("*.log"))` materialises the entire generator into a list and sorts it; without `sorted`, the order is filesystem-dependent. The materialisation is fine here (small tree), but on a large tree it defeats the laziness — you would iterate the generator directly and sort lazily if you needed to. For the demo, `sorted` gives deterministic output.

**Why use `rglob` at all if `walk` is strictly more powerful?** Three reasons. First, `rglob` pre-dates `walk` — Python 3.9 had `rglob`, Python 3.12 added `walk`. Code written before 3.12 had no choice. Second, `rglob` is more *concise* when you do not need pruning: `for p in root.rglob("*.log"):` is one line, where the equivalent `walk` is four lines (unpack tuple, filter `filenames` by suffix, join, append). Third, `rglob` is the right tool when you want a *flat* list and the per-directory tuple shape is noise. If you want "every `.log` file anywhere under here, in a flat list, no per-directory decisions", `rglob` is shorter and clearer.

**Warning — `rglob` cannot prune; `walk` can. That is the choice.**

If you need to skip a directory *before* the walker descends into it (which is what "skip" means for a walk), you need `walk` with `top_down=True` and `dirnames[:] = ...`. There is no `rglob(prune={".git"})` API. If you find yourself post-filtering `rglob` output with `"if '.git' in p.parts: continue"`, you are paying the disk cost of walking `.git` and throwing the results away — `walk` would have skipped the disk cost entirely.

### Lines 62–71: `on_error` — handle OS errors instead of swallowing

```python
def walk_with_error_handler(root: Path) -> None:
    print("\n=== walk with on_error handler ===")

    def report(exc: OSError) -> None:
        print(f"  [skip] {exc.filename}: {exc.strerror}")

    for dirpath, dirnames, filenames in root.walk(
        top_down=True, on_error=report
    ):
        rel = dirpath.relative_to(root)
        print(f"  {rel}  files={len(filenames)}")
```

The `on_error` parameter accepts either `None` (the default, which silently swallows every `OSError` raised during iteration — permission denied, missing directory, broken symlink) or a callable that takes a single `OSError` argument. The callable is called *instead of* the default swallow — your function decides whether to log, raise, or continue. To raise, call `raise` inside the callable (re-raise the exception). To log and continue, print and return. To log and abort, raise a different exception.

The default `None` is dangerous in production because it silently masks real bugs. If `walk` encounters a `PermissionError` on a directory, the default swallows it and the walk silently produces an incomplete result — you believe you walked the whole tree, but you only walked the parts you had permission to read. For a log-archival job, that means some logs are silently not archived, and the only way you find out is when the customer asks where their old logs went. The lesson's `archive_logs` function does not pass `on_error` — that is a bug we will fix in lesson 07's exercises; for now, the demo shows the *pattern* of a logging handler.

**Why a callable and not a boolean?** Because the decision of what to do with an error is contextual. A `report` handler that logs and continues is right for a background archival job. A `raise`-it handler is right for a foreground `--dry-run` mode where you want to surface every problem immediately. A `count` handler that increments a counter is right for a metrics-export job. The callable lets each caller choose. The default `None` corresponds to "swallow silently" — which is wrong by default for production, hence the warning.

### Lines 74–80: `follow_symlinks=False` — the default that defends against loops

```python
def walk_symlink_safe(root: Path) -> None:
    print("\n=== walk follow_symlinks=False (default) ===")
    count = 0
    for dirpath, _, filenames in root.walk(follow_symlinks=False):
        count += len(filenames)
    print(f"  total files (no symlink follow): {count}")
```

`follow_symlinks=False` (the default) means the walker treats every symlink as a file (it appears in `filenames`, not `dirnames`), and never follows a symlink into a sub-tree. The walker is therefore loop-safe: a symlink that points at its own parent (a classic Unix misconfiguration) does not cause infinite recursion, because the walker never descends through the symlink.

`follow_symlinks=True` flips this: the walker treats a symlink to a directory as a directory (it appears in `dirnames`, the walker recurses through it). The loop protection is gone — if your tree contains a symlink loop, the walker will follow it forever (or until the OS raises `OSError` after too many symlink resolutions, which is platform-dependent and not reliable).

**Why is `False` the default?** Because the symlink-loop bug is a real, common, hard-to-diagnose production failure. The most common form: a deployment script copies a directory tree and creates a symlink to the parent for "convenience" — `logs/current -> .` — and then walks the tree to compute total size. With `follow_symlinks=True`, the walk enters `logs/current/`, which contains `current/` again, which contains `current/` again, ad infinitum. With `False`, the symlink appears as a single file in `filenames`, the walk terminates, the size is correct. The 3.12 pathlib authors chose the safe default and required the caller to opt into the unsafe behaviour. The same default applies to `os.walk` (which also defaults to `followlinks=False`).

### Lines 83–92: The boardly archival job — the production shape

```python
def archive_logs(root: Path) -> list[Path]:
    """Walk boardly/logs/, skip .git/.venv, archive *.log files."""
    archived: list[Path] = []
    skip = {".git", ".venv", "__pycache__"}
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames[:] = [d for d in dirnames if d not in skip]
        dirnames.sort()                   # deterministic visit order
        for name in filenames:
            if name.endswith(".log"):
                archived.append(dirpath / name)
    return archived
```

The final function assembles everything: `top_down=True` for pruning, `dirnames[:] = ...` to skip `.git`/`.venv`/`__pycache__` in-place, `dirnames.sort()` for deterministic visit order (so the demo's `archive_logs` output is reproducible across runs and filesystems; in production you might drop the sort for filesystem-order speed), `name.endswith(".log")` to filter `filenames` (which *is* a string-list, no Path objects — joining with `dirpath / name` produces a `Path`). The `dirpath / name` join is the same `/` operator you met in lesson 01; `dirpath` is a `Path` (yielded by `walk`), `name` is a `str`, the operator handles the mixed types via `PurePath.__truediv__`.

The function returns `list[Path]` — every archived entry is a `Path` object, ready for the caller to call `.stat()` or `.read_text()` or `.rename()` on without rewrapping. The whole walk stays in the `Path` API; the only string-API call is `name.endswith(".log")`, which is operating on the *name* (a string), not the path — and that is the correct level for suffix filtering. Lesson 03 (glob and rglob) showed that `Path.match("*.log")` also works, but `name.endswith(".log")` is faster (no glob compilation) and equally clear for a simple suffix check.

**Why does `archive_logs` not include `.venv/lib/site-packages/pip.log`?** Because `.venv` is pruned from `dirnames` before the walker descends — the walker never enters `.venv`, never enumerates its `lib/site-packages/` sub-tree, and never sees `pip.log`. The `rglob_demo` above *does* include `pip.log` because `rglob` cannot prune — it walks the whole tree, including `.venv`. The contrast is the lesson's whole point: `walk` skips the disk reads for `.venv`; `rglob` does not. In the archival job, the disk saving is real (skip thousands of files in `.venv/lib/site-packages/`); in the `rglob` demo, the saving is invisible (we walked a 6-file tree) but the principle is the same.

**Warning — This function silently swallows OS errors (no `on_error`).**

`archive_logs` does not pass `on_error`, so it uses the default `None` — silently swallowing every `OSError`. If a sub-directory is permission-denied, the function silently omits its `.log` files from the `archived` list. The caller cannot distinguish "no log files in that directory" from "could not read that directory". For a production archival job, you would pass an `on_error` handler that logs to a metrics counter and continues, or that raises and aborts. The lesson's exercise 4 asks you to add that handler.

## Execution Trace

```bash
$ uv run python boardly/logs/walk_demo.py

=== iterdir (immediate children, non-recursive) ===
  DIR  .git
  DIR  .venv
  DIR  2026-10-23
  DIR  2026-10-24

=== walk top_down=True (no pruning) ===
  .  dirs=['.git', '.venv', '2026-10-23', '2026-10-24']  files=[]
  .git  dirs=['objects']  files=['HEAD']
  .git/objects  dirs=['pack']  files=[]
  .git/objects/pack  dirs=[]  files=['big.pack']
  .venv  dirs=['lib']  files=[]
  .venv/lib  dirs=['site-packages']  files=[]
  .venv/lib/site-packages  dirs=[]  files=['pip.log']
  2026-10-23  dirs=[]  files=['app.log', 'error.log']
  2026-10-24  dirs=[]  files=['app.log']

=== walk with pruning (skip .git and .venv) ===
  .  dirs=['2026-10-23', '2026-10-24']  files=[]
  2026-10-23  dirs=[]  files=['app.log', 'error.log']
  2026-10-24  dirs=[]  files=['app.log']

=== rglob("*.log") — flat, recursive ===
  .venv/lib/site-packages/pip.log
  2026-10-23/app.log
  2026-10-23/error.log
  2026-10-24/app.log

=== walk with on_error handler ===
  .  files=0
  .git  files=1
  .git/objects  files=0
  .git/objects/pack  files=1
  .venv  files=0
  .venv/lib  files=0
  .venv/lib/site-packages  files=1
  2026-10-23  files=2
  2026-10-24  files=1

=== walk follow_symlinks=False (default) ===
  total files (no symlink follow): 6

=== boardly archive_logs result ===
  archived: 2026-10-23/app.log
  archived: 2026-10-23/error.log
  archived: 2026-10-24/app.log
```

The unpruned walk has eight tuples (the root + seven sub-directories). The pruned walk has three tuples (the root + two date sub-directories — `.git` and `.venv` are gone from `dirnames` before the walker recurses). The `rglob` result includes `.venv/lib/site-packages/pip.log` (because `rglob` cannot prune); the `archive_logs` result *excludes* `pip.log` (because `walk` pruned `.venv` before descending). That is the lesson's headline contrast: `walk` saves the disk reads; `rglob` does not. The `total files (no symlink follow)` count of 6 covers the four `.log` files plus `HEAD` plus `big.pack` — every file the unpruned walker visits when there are no symlinks to follow.

## Common Mistakes

### Mistake 1: Rebinding `dirnames` instead of mutating in place

```python
for dirpath, dirnames, filenames in root.walk(top_down=True):
    dirnames = [d for d in dirnames if d != ".git"]   # WRONG
    # ... walker still descends into .git ...
```

**Symptom:** The walker descends into `.git` despite the assignment. The pruning does not take effect.
**Why:** The assignment `dirnames = [...]` rebinds the *local* name `dirnames` to a new list. The walker keeps a reference to the original list object; it never sees your new list. The walker consults the original list to decide which sub-directories to recurse into, so `.git` is still in the list, the walker still recurses.
**Fix:** Use slice assignment to mutate in place: `dirnames[:] = [d for d in dirnames if d != ".git"]`. The walker reads the same list object after your mutation; `.git` is now gone; the walker skips it.

### Mistake 2: Calling `walk` on a non-existent directory

```python
root = Path("/nonexistent/boardly/logs")
for dirpath, dirnames, filenames in root.walk(top_down=True):
    ...
```

**Symptom:** With `on_error=None` (the default), nothing — the loop body never executes, no error raised. The function silently returns an empty result.
**Why:** `walk` catches the `FileNotFoundError` from `os.scandir` internally and passes it to `on_error`. With `on_error=None`, the error is swallowed. The walk produces zero tuples; the for-loop iterates zero times; the function returns whatever the empty loop produced.
**Fix:** Check `root.is_dir()` before calling `walk`, or pass an `on_error` callable that raises on `FileNotFoundError` specifically. For a configuration-driven job where the root is a user-supplied path, the `is_dir()` check at the boundary is the right pattern.

### Mistake 3: Using `top_down=False` and expecting to prune

```python
for dirpath, dirnames, filenames in root.walk(top_down=False):
    dirnames[:] = [d for d in dirnames if d != ".git"]   # too late
    ...
```

**Symptom:** The walker descends into `.git` despite the in-place mutation. The pruning does not take effect.
**Why:** With `top_down=False`, the walker yields the parent's tuple *after* it has already recursed into all the children. By the time you receive the parent tuple and mutate `dirnames`, the walker has already finished descending into `.git` — the mutation is too late.
**Fix:** Use `top_down=True` (the default) when you intend to prune. Use `top_down=False` only when you need to delete directories during the walk (e.g., recursive `rmdir`), where you must empty sub-directories before removing their parent — a pattern covered in lesson 04.

## Engineering Trade-Offs

**Decision:** Use `walk(top_down=True)` with `dirnames[:] = ...` pruning for production tree-walkers; use `rglob` only for one-liners that do not need pruning.
**Both sides:** `rglob` is shorter and reads more naturally for a "give me every X under Y" query — `root.rglob("*.log")` is one line, no setup. The cost is no pruning, no per-directory decisions, no `on_error` integration. For a CI script that finds every test file under a repo, `rglob` is the right tool — there is nothing to prune. For a production archival job that walks a tree containing `.git`, `.venv`, and `__pycache__`, the pruning is the entire point, and `walk` is the right tool. The decision is not "always use walk" — it is "use walk when you need its capabilities, use rglob when you do not".
**Commitment:** `boardly`'s log-archival job uses `walk` because the tree contains poison directories. `boardly`'s test-collection CI script uses `rglob("test_*.py")` because there is nothing to prune and the one-liner reads better. The choice is per-job, not per-codebase.

## Exercises

1. **Exercise 1 — Print the immediate children.** Modify the script to call `iterdir()` on `Path("/tmp/boardly-walk-demo")` and print only the directories. `Verify: uv run python boardly/logs/walk_demo.py | rg '^  DIR'`
2. **Exercise 2 — Change the skip set.** Add `"node_modules"` to the `skip` set in `archive_logs` and rerun. Confirm the walker still skips `.git` and `.venv`. `Verify: uv run python boardly/logs/walk_demo.py | rg 'node_modules'`
3. **Exercise 3 — Top-down vs bottom-up.** Change `walk_pruned` to use `top_down=False` and observe that pruning no longer works — `.git` and `.venv` appear in the output. Explain in a comment why. `Verify: uv run python boardly/logs/walk_demo.py | rg 'no-prune'`
4. **Exercise 4 — Add an `on_error` handler to `archive_logs`.** Modify the function to accept an `on_error` callable, default it to a logging handler, and have the handler increment a counter. Print the counter at the end. `Verify: uv run python boardly/logs/walk_demo.py | rg 'errors='`
5. **Exercise 5 — Walk with `follow_symlinks=True`.** Create a symlink from `boardly/logs/current` to `boardly/logs/2026-10-23`, then run `walk(follow_symlinks=True)` and observe the walker descending through the symlink. Restore `follow_symlinks=False` and observe the symlink appearing as a file in `filenames`. `Verify: uv run python boardly/logs/walk_demo.py | rg 'follow_symlinks'`

## Verification

```bash
$ uv run python boardly/logs/walk_demo.py | head -30

=== iterdir (immediate children, non-recursive) ===
  DIR  .git
  DIR  .venv
  DIR  2026-10-23
  DIR  2026-10-24

=== walk top_down=True (no pruning) ===
  .  dirs=['.git', '.venv', '2026-10-23', '2026-10-24']  files=[]
  .git  dirs=['objects']  files=['HEAD']
  .git/objects  dirs=['pack']  files=[]
  .git/objects/pack  dirs=[]  files=['big.pack']
  .venv  dirs=['lib']  files=[]
  .venv/lib  dirs=['site-packages']  files=[]
  .venv/lib/site-packages  dirs=[]  files=['pip.log']
  2026-10-23  dirs=[]  files=['app.log', 'error.log']
  2026-10-24  dirs=[]  files=['app.log']

=== walk with pruning (skip .git and .venv) ===
  .  dirs=['2026-10-23', '2026-10-24']  files=[]
  2026-10-23  dirs=[]  files=['app.log', 'error.log']
  2026-10-24  dirs=[]  files=['app.log']
```

The unpruned walk descends into `.git` and `.venv`. The pruned walk does not. `iterdir()` lists four immediate children without recursion.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `Path` constructor and the `/` operator. `walk`'s yielded `dirpath` is a `Path`, and `dirpath / name` is the lesson-01 join.
- [[08-pathlib/03-glob-and-rglob]] — `glob()` and `rglob()`. The lesson compared `walk` against `rglob` directly; you should already know the glob syntax.
- [[08-pathlib/05-PurePath-vs-Path]] — the pure-vs-concrete split. `iterdir`, `walk`, `rglob` are all `Path` methods (none exist on `PurePath`); this is the I/O surface lesson that follows the class-hierarchy lesson.

## What's Next

[[08-pathlib/07-stat-and-permissions]] — the last I/O lesson, on file metadata. Now that you can walk a tree, you need to inspect each file's metadata: `Path.stat()` returns `os.stat_result` with `.st_size`, `.st_mtime`, `.st_mode`, `.st_uid`, `.st_gid`, `.st_ino`, `.st_dev`, `.st_nlink`. `Path.lstat()` is the symlink-safe variant. The `is_file()` / `is_dir()` / `is_symlink()` / `is_socket()` / `is_fifo()` / `is_block_device()` / `is_char_device()` predicates give you the file's type. `Path.chmod(mode)` and `Path.lchmod(mode)` change permissions; `Path.owner()` and `Path.group()` return the username and groupname strings. Lesson 07 puts it all together for `boardly`'s log-rotation policy: walk the tree (lesson 06), stat each file (lesson 07), archive the ones over 10 MB, compress the ones older than 30 days.

## Sources

- **pathlib — Python 3.12 documentation** — https://docs.python.org/3.12/library/pathlib.html — accessed 2026-10-23 — the canonical reference for `Path.iterdir`, `Path.walk`, `Path.rglob`. The `walk` method is documented under "Concrete Paths" with the full signature `(top_down=True, on_error=None, follow_symlinks=False)`.
- **What's New in Python 3.12 — pathlib** — https://docs.python.org/3.12/whatsnew/3.12.html#pathlib — accessed 2026-10-23 — the changelog entry that introduced `Path.walk()` and the `pathlib.Path.walk` method's relationship to `os.walk`. Notes the `top_down` parameter and the in-place pruning pattern.
- **os — Python 3.12 documentation (os.walk)** — https://docs.python.org/3.12/library/os.html#os.walk — accessed 2026-10-23 — the legacy `os.walk` API, included for comparison. The `Path.walk` signature mirrors `os.walk`'s, with the type-level improvement that `dirpath` is a `Path` instead of a `str`.

## What We Learned

- You can now use `Path.iterdir()` for non-recursive immediate-children listing — it returns a lazy generator of `Path` objects, not a list of strings.
- You can call `Path.walk(top_down=True, on_error=None, follow_symlinks=False)` (Python 3.12+) for recursive traversal yielding `(dirpath: Path, dirnames: list[str], filenames: list[str])` tuples.
- You can prune `dirnames` in-place with `dirnames[:] = [d for d in dirnames if d not in skip]` to prevent the walker from descending into directories like `.git` and `.venv` — and you understand that rebinding (without the slice) does not work because the walker keeps a reference to the original list.
- You can choose between `walk` and `rglob` based on whether you need pruning; `rglob` is more concise but cannot prune.
- You can pass an `on_error` callable to handle OS errors instead of silently swallowing them — the default `None` is dangerous in production because it masks real bugs.
- You understand why `follow_symlinks=False` is the safe default (loop protection) and when you would flip it to `True` (you know the tree has no loops and you want to follow a known-good symlink).
