---
title: "Lesson 04: mkdir, rmdir, unlink"
aliases:
 - Path.mkdir
 - Path.rmdir
 - Path.unlink
 - Path.touch
 - Path.rename
 - Path.replace
tags:
 - pathlib
 - python-stdlib
 - filesystem
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
 - "[[08-pathlib/02-read-write-text-binary]]"
related_lessons:
 - "[[08-pathlib/03-glob-and-rglob]]"
 - "[[08-pathlib/01-Path-Basics]]"
---

# Lesson 04: mkdir, rmdir, unlink

*Why `boardly`'s `data_dir.mkdir(parents=True, exist_ok=True)` is the `mkdir -p` spelling, why `Path.rmdir()` raises on a non-empty directory, and why `Path.replace(target)` is the portable rename — not `Path.rename`.*

**You're at the very beginning of Section 08, lesson 04.**

You have written `os.makedirs(path, exist_ok=True)` and `os.remove(path)` and `shutil.rmtree(path)` and felt the API sprawl. Each function lives in a different module (`os`, `os.path`, `shutil`). Each has a slightly different naming convention (`makedirs` vs `remove` vs `rmtree`). Each takes a *string* path, not a `Path`. The `pathlib.Path` mutator methods fix all of that. `Path.mkdir(parents=True, exist_ok=True)` is the `mkdir -p` spelling. `Path.rmdir()` removes an empty directory. `Path.unlink(missing_ok=True)` removes a file (the `missing_ok` kwarg is 3.8+). `Path.touch()` creates an empty file. `Path.rename(target)` and `Path.replace(target)` move files. One type. Every operation. Same spelling on every OS. Take your time. Type every example. **This is how you learn.**

#pathlib #filesystem

## Learning Objectives

By the end of this lesson you will be able to:

1. **Create a directory** with `Path.mkdir(mode=0o777, parents=False, exist_ok=False)` — explain that `parents=True` is the `mkdir -p` spelling (creates intermediate dirs), `exist_ok=True` swallows the `FileExistsError` if the directory already exists, and `mode` is the permission bits masked by the process's umask.
2. **Remove a directory** with `Path.rmdir()` — explain that it removes an *empty* directory only, raises `OSError` (errno 39, `Directory not empty`) if the directory has any entries, and is *not* the recursive removal — that's `shutil.rmtree` (which the stdlib chose not to add to `pathlib` because recursive removal is dangerous).
3. **Remove a file** with `Path.unlink(missing_ok=False)` — explain that `missing_ok=True` (Python 3.8+) does not raise `FileNotFoundError` if the file does not exist, and that `unlink` is the historical Unix name for "remove the directory entry" (a file with multiple hard links loses one entry, not the inode).
4. **Touch a file** with `Path.touch(mode=0o666, exist_ok=True)` — explain that it creates the file if missing, updates the mtime if present, and that the `exist_ok=True` default is the opposite of `mkdir`'s `exist_ok=False` default because touching is idempotent.
5. **Rename and replace** with `Path.rename(target)` and `Path.replace(target)` — explain that `rename` has platform-dependent overwrite semantics (POSIX overwrites a file target, Windows raises), while `replace` overwrites the target on every platform — the portable rename-to-existing is `replace`.

## Prerequisites

Before starting, you need:

- **Path basics** — [[08-pathlib/01-Path-Basics]]. This lesson calls `mkdir` / `rmdir` / `unlink` on `Path` objects; you need to be comfortable constructing a `Path`.
- **Read & write** — [[08-pathlib/02-read-write-text-binary]]. The lesson's demos seed files with `write_text` before removing them; you need the I/O methods.
- **About 30–45 minutes of focused time.**

**The most common gap: treating `Path.rmdir` as a recursive delete.**

It is not. `Path.rmdir()` removes an *empty* directory only. The single biggest mistake students make in this lesson is writing `non_empty_dir.rmdir()` and being surprised by `OSError: [Errno 39] Directory not empty`. The stdlib chose not to add a recursive-delete method to `pathlib` because recursive deletion is dangerous — `shutil.rmtree(path)` is the spelling, and it lives in `shutil` precisely because the stdlib wants the call to be a *deliberate* choice. The rule "if you need recursive delete, reach for `shutil.rmtree`" is the lesson's most important commitment.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/paths/bad_mutation.py — the bad old days
import os
import os.path
import shutil

# 1. mkdir with intermediate dirs needs a separate function
os.makedirs("boardly/data/archive", exist_ok=True)

# 2. rmdir on a non-empty dir needs shutil.rmtree, not os.rmdir
try:
    os.rmdir("boardly/data/archive")          # raises OSError if non-empty
except OSError:
    shutil.rmtree("boardly/data/archive")    # silent recursive delete

# 3. Remove a file that might not exist needs a try/except
try:
    os.remove("boardly/data/projects.json")   # raises if missing
except FileNotFoundError:
    pass                                       # explicit "ignore missing"

# 4. Rename with overwrite needs os.replace (not os.rename on Windows)
os.replace("boardly/data/projects.json.bak", "boardly/data/projects.json")
```

Every line works. The bug is not that it crashes; the bug is that the four operations live in three modules (`os`, `os.path`, `shutil`) with inconsistent names (`makedirs` vs `rmdir` vs `remove` vs `rmtree` vs `replace`). The student has to remember which function lives in which module, and the API surface sprawls. Worse, the `os.rmdir` vs `shutil.rmtree` distinction is implicit — there is no marker on the call site that says "this is non-recursive" or "this is recursive", and the student picks the wrong one half the time.

`pathlib.Path.mkdir`, `Path.rmdir`, `Path.unlink`, `Path.touch`, `Path.rename`, `Path.replace` were added in Python 3.4 (and refined through 3.6, 3.8, 3.10) to consolidate these into one type. `Path.mkdir(parents=True, exist_ok=True)` is the `mkdir -p` spelling — one call creates intermediate dirs and does not raise if the leaf exists. `Path.rmdir()` removes an *empty* directory only and raises loudly if it is non-empty — the stdlib deliberately did not add a recursive-delete method to `pathlib`, forcing the student to reach for `shutil.rmtree` deliberately. `Path.unlink(missing_ok=True)` (the `missing_ok` kwarg is 3.8+) removes a file and does not raise if it is missing. `Path.touch(mode=0o666, exist_ok=True)` creates an empty file or updates its mtime. `Path.rename(target)` and `Path.replace(target)` move files, with the platform-dependent-overwrite vs portable-overwrite distinction made explicit by the *method name* rather than the *platform*.

The `pathlib` mutator methods are the standard-library answer to "I have a `Path`, I want to mutate the filesystem". `Path.mkdir()` creates a directory. `Path.rmdir()` removes an empty directory. `Path.unlink()` removes a file. `Path.touch()` creates or refreshes a file. `Path.rename(target)` and `Path.replace(target)` move files. The methods compose with the `Path` you constructed in lesson 01 — you do not pass a `str`, you call a method on the `Path` you already have. There is no `os.makedirs` vs `os.mkdir` distinction; the `parents=True` argument unifies them. There is no `os.remove` vs `os.unlink` distinction; `Path.unlink` is the only spelling. The recursion-or-not choice is made by reaching for `shutil.rmtree` or not — the stdlib makes the dangerous choice *deliberate*.

## The Code

```python
# boardly/paths/mkdir_unlink.py
"""Pathlib mkdir/rmdir/unlink/touch/rename/replace: filesystem mutators."""
from pathlib import Path
import tempfile

# 0. Build a tmpdir that stands in for the boardly deployment's tree
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    scratch = root / "boardly" / "scratch"
    scratch.mkdir(parents=True)

    # 1. mkdir — basic; raises FileExistsError if the dir already exists
    new_dir = scratch / "new"
    new_dir.mkdir()
    print("1. mkdir ok, exists=", new_dir.exists())
    try:
        new_dir.mkdir()
    except FileExistsError as e:
        print("   second mkdir raises FileExistsError:", e)
    # exist_ok=True swallows the FileExistsError
    new_dir.mkdir(exist_ok=True)
    print("   mkdir(exist_ok=True) -> no error")

    # 2. mkdir(parents=True) = `mkdir -p` — creates intermediate dirs
    nested = scratch / "a" / "b" / "c"
    nested.mkdir(parents=True)
    print("2. mkdir(parents=True) ok, exists=", nested.exists())
    try:
        scratch / "x" / "y" / "z"
        (scratch / "x" / "y" / "z").mkdir(parents=False)
    except FileNotFoundError as e:
        print("   parents=False on missing parent raises FileNotFoundError:", e)

    # 3. rmdir — removes an EMPTY directory only; raises OSError if non-empty
    empty = scratch / "empty"
    empty.mkdir()
    empty.rmdir()
    print("3. rmdir empty ok, exists=", empty.exists())
    non_empty = scratch / "non_empty"
    non_empty.mkdir()
    (non_empty / "junk.txt").write_text("x", encoding="utf-8")
    try:
        non_empty.rmdir()
    except OSError as e:
        print("   rmdir non-empty raises OSError:", e)

    # 4. unlink — removes a FILE (not a directory); missing_ok=True is 3.8+
    f = scratch / "trash.txt"
    f.write_text("trash", encoding="utf-8")
    f.unlink()
    print("4. unlink ok, exists=", f.exists())
    try:
        f.unlink()
    except FileNotFoundError as e:
        print("   unlink on missing raises FileNotFoundError:", e)
    f.unlink(missing_ok=True)
    print("   unlink(missing_ok=True) -> no error")

    # 5. touch — creates the file if missing; updates mtime if present
    t = scratch / "touched.txt"
    t.touch()
    print("5. touch ok, exists=", t.exists())
    t.touch()  # second touch updates mtime; does not raise
    print("   second touch ok (mtime updated)")

    # 6. rename — POSIX overwrites if target is a file; Windows raises FileExistsError
    a = scratch / "a.txt"
    a.write_text("A", encoding="utf-8")
    b = scratch / "b.txt"
    b.write_text("B", encoding="utf-8")
    a.rename(b)
    print("6. rename(a -> b): a.txt exists=", a.exists(), ", b.txt contents=", repr(b.read_text(encoding="utf-8")))

    # 7. replace — overwrites the target on every platform (the portable rename-to-existing)
    c = scratch / "c.txt"
    c.write_text("C-original", encoding="utf-8")
    d = scratch / "d.txt"
    d.write_text("D", encoding="utf-8")
    d.replace(c)
    print("7. replace(d -> c): c.txt contents=", repr(c.read_text(encoding="utf-8")), "(was 'C-original')")

    # 8. iterdir — lazy iteration over a directory's direct children
    print("--- scratch.iterdir() ---")
    for p in sorted(scratch.iterdir()):
        print("  ", p.name, "(is_dir=", p.is_dir(), ", is_file=", p.is_file(), ")")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–8: Setup — the tmpdir scratch tree

```python
from pathlib import Path
import tempfile

# 0. Build a tmpdir that stands in for the boardly deployment's tree
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    scratch = root / "boardly" / "scratch"
    scratch.mkdir(parents=True)
```

The imports are minimal: `Path` from `pathlib`, `TemporaryDirectory` from `tempfile`. The `with tempfile.TemporaryDirectory() as td:` block creates a fresh, empty tree that vanishes on exit, so the demo is reproducible across machines without leaving files behind. `root = Path(td)` wraps the tmpdir string in a `Path`; from here, every path operation uses `/` and the `Path` API. `scratch = root / "boardly" / "scratch"` builds the scratch directory path with the `/` operator. `scratch.mkdir(parents=True)` is the first mutator call of the lesson — `parents=True` is the `mkdir -p` spelling, creating the `boardly/` and `boardly/scratch/` directories in one call.

The `scratch.mkdir(parents=True)` call is the *first* filesystem mutation in the demo, and it demonstrates the lesson's first teaching point: `parents=True` is the `mkdir -p` spelling. The equivalent `os.makedirs(scratch, exist_ok=False)` would do the same thing (create intermediate dirs); `os.mkdir(scratch)` would raise `FileNotFoundError` because `boardly/` does not exist yet. The `Path.mkdir(parents=True)` spelling unifies `os.mkdir` (no parents) and `os.makedirs` (with parents) into one method with a flag — the choice is explicit at the call site.

**Why `parents=False` as the default and not `True`?** Because the default matches the *lower-level* operation (`mkdir(2)` syscall, which creates one directory and raises if the parent does not exist), and the stdlib's policy is to make the lower-level operation the default. The `parents=True` flag is the *convenience* spelling for the `mkdir -p` case, and the default is the *safe* spelling — `Path.mkdir` without `parents=True` will not silently create a chain of directories you did not ask for. The asymmetry with `exist_ok=False` (the default that raises on existing) is the same shape: the default is the safe spelling, the flag is the convenience spelling. The student who writes `Path.mkdir(path)` and gets a `FileNotFoundError` has learned that they need `parents=True` — and the lesson is "be explicit about what you want", which is the pathlib design philosophy.

### Lines 10–16: `Path.mkdir` basic and the `FileExistsError` boundary

```python
# 1. mkdir — basic; raises FileExistsError if the dir already exists
new_dir = scratch / "new"
new_dir.mkdir()
print("1. mkdir ok, exists=", new_dir.exists())
try:
    new_dir.mkdir()
except FileExistsError as e:
    print("   second mkdir raises FileExistsError:", e)
# exist_ok=True swallows the FileExistsError
new_dir.mkdir(exist_ok=True)
print("   mkdir(exist_ok=True) -> no error")
```

`new_dir = scratch / "new"` builds the path; `new_dir.mkdir()` creates the directory. The signature is `Path.mkdir(self, mode=0o777, parents=False, exist_ok=False)`. The default `mode=0o777` is the permission bits — note that the actual permission on disk is `mode & ~umask`, so on a typical Linux umask of `022`, the directory is created with `0o755` (rwxr-xr-x). The default `parents=False` means "do not create intermediate dirs" — if `scratch` did not exist (it does, from line 7), the call would raise `FileNotFoundError`. The default `exist_ok=False` means "raise `FileExistsError` if the leaf already exists" — the *second* `new_dir.mkdir()` call on line 13 raises `FileExistsError` because the directory now exists.

`new_dir.mkdir(exist_ok=True)` is the *idempotent* spelling — the call creates the directory if it does not exist, and does nothing (no raise) if it does. The output `mkdir(exist_ok=True) -> no error` confirms the swallow. This is the spelling you use in deployment scripts and init code where you do not care whether the directory was already there — the equivalent of `mkdir -p` without the `parents` part.

Internally, `Path.mkdir` calls `os.mkdir(self, mode)` if `parents=False` or `os.makedirs(self, mode, exist_ok=exist_ok)` if `parents=True`. The `os.mkdir` syscall creates one directory and raises `FileExistsError` if it exists; `os.makedirs` walks the path components left to right, calling `os.mkdir` on each missing one. The `exist_ok` flag is forwarded to `os.makedirs`'s `exist_ok` argument; for `parents=False`, the flag is checked before the `os.mkdir` call (the `path.exists()` check is one stat call, then the `os.mkdir` is conditional).

**Why does `exist_ok=False` raise rather than swallow?** Because the default is the *safe* spelling — the student who writes `Path.mkdir(path)` and gets a `FileExistsError` has learned that the path already exists, which is information they might want (e.g. they are creating a fresh workspace and the existence of the directory means a previous run did not clean up). The `exist_ok=True` flag is the *idempotent* spelling for the case where you do not care. The default asymmetry with `touch`'s `exist_ok=True` (next section) is because `mkdir` is *not* idempotent in intent — you usually want to know if the directory already existed; `touch` *is* idempotent in intent — you usually just want the file to exist with a fresh mtime.

### Lines 18–25: `Path.mkdir(parents=True)` is `mkdir -p`

```python
# 2. mkdir(parents=True) = `mkdir -p` — creates intermediate dirs
nested = scratch / "a" / "b" / "c"
nested.mkdir(parents=True)
print("2. mkdir(parents=True) ok, exists=", nested.exists())
try:
    scratch / "x" / "y" / "z"
    (scratch / "x" / "y" / "z").mkdir(parents=False)
except FileNotFoundError as e:
    print("   parents=False on missing parent raises FileNotFoundError:", e)
```

`nested = scratch / "a" / "b" / "c"` builds a path three levels deep — `scratch/a/b/c`. None of `a/`, `b/`, `c/` exist yet. `nested.mkdir(parents=True)` creates all four levels in one call: `scratch/a/`, `scratch/a/b/`, `scratch/a/b/c/`. The output `mkdir(parents=True) ok, exists=True` confirms the chain was created. The `parents=True` flag is the `mkdir -p` spelling — it makes the operation idempotent w.r.t. intermediate dirs: if `scratch/a/` already existed, the call would create `b/` and `c/` and not raise on `a/`.

The contrast on lines 22–24 shows the failure mode without `parents=True`: `(scratch / "x" / "y" / "z").mkdir(parents=False)` raises `FileNotFoundError` because `scratch/x/` does not exist. The error message `[Errno 2] No such file or directory: '/tmp/.../scratch/x/y/z'` is misleading — it names the *whole* path, not the *first missing component* (which is `scratch/x/`). This is because `os.mkdir` (the underlying syscall) takes the whole path and raises on the first missing ancestor; the error message is the syscall's, not pathlib's. The fix is `parents=True` — the `os.makedirs` function walks the path and creates each missing ancestor in turn.

The `parents=True` flag is what makes `Path.mkdir` the *one-call* replacement for the shell's `mkdir -p` — and for the Python `os.makedirs(path, exist_ok=...)` pattern. The two flags `parents=True` and `exist_ok=True` together give the full `mkdir -p` semantics: create intermediate dirs, do not raise if the leaf exists.

**Why does `parents=True` *also* need `exist_ok=True` for full `mkdir -p`?** Because the two flags answer different questions. `parents=True` answers "should I create missing *intermediate* dirs?" — yes. `exist_ok=True` answers "should I raise if the *leaf* already exists?" — no. The shell's `mkdir -p` answers both questions with yes/no respectively; the Python API separates them so you can mix — e.g. `parents=True, exist_ok=False` is "create intermediate dirs but raise if the leaf already exists" (useful if you want to assert the leaf is new). The two flags are independent; the most common combo is `parents=True, exist_ok=True` (full `mkdir -p`), but the API does not force it.

### Lines 27–34: `Path.rmdir` — empty-directory-only, raises on non-empty

```python
# 3. rmdir — removes an EMPTY directory only; raises OSError if non-empty
empty = scratch / "empty"
empty.mkdir()
empty.rmdir()
print("3. rmdir empty ok, exists=", empty.exists())
non_empty = scratch / "non_empty"
non_empty.mkdir()
(non_empty / "junk.txt").write_text("x", encoding="utf-8")
try:
    non_empty.rmdir()
except OSError as e:
    print("   rmdir non-empty raises OSError:", e)
```

`empty = scratch / "empty"` builds the path; `empty.mkdir()` creates it; `empty.rmdir()` removes it. The signature is `Path.rmdir(self)` — no arguments. The output `rmdir empty ok, exists=False` confirms the removal. `Path.rmdir` calls `os.rmdir(self)`, which is the `rmdir(2)` syscall — it removes a directory entry only if the directory is *empty*. An empty directory is one with no entries (no files, no subdirs, no `.` or `..` — those are implicit).

The contrast on lines 31–34 shows the failure mode for a non-empty directory: `non_empty.rmdir()` raises `OSError: [Errno 39] Directory not empty: '/tmp/.../scratch/non_empty'`. The `OSError` (subclass of `Exception`, with `errno=39` `ENOTEMPTY`) is the syscall's error; `pathlib` does not wrap it. The error message names the directory that was non-empty.

The stdlib deliberately did not add a recursive-delete method to `pathlib` — `Path.rmdir` is empty-only, and the recursive case is `shutil.rmtree(path)`. The choice is a *safety* one: recursive deletion is dangerous (a typo in the path can wipe a deployment), and the stdlib wants the call to be a *deliberate* import of `shutil` and a *deliberate* call to `rmtree`. The student who writes `non_empty.rmdir()` and gets `OSError` has learned that they need `shutil.rmtree` — and the lesson is "be deliberate about recursive deletion", which is the pathlib design philosophy.

**Why is `rmdir` empty-only?** Because the `rmdir(2)` syscall is empty-only, and `pathlib` mirrors the syscall. The Unix model is: `mkdir(2)` creates one directory, `rmdir(2)` removes one empty directory, `unlink(2)` removes one directory entry (a file). Recursive operations are a *higher-level* concern, and the stdlib puts them in `shutil` (shell utilities) rather than `os` (syscalls) or `pathlib` (object-oriented paths). The three-layer model — `pathlib` for path objects, `os` for syscalls, `shutil` for shell-style operations — is the stdlib's policy: each layer has a clear scope, and recursive operations live in the highest layer where the danger is most visible.

### Lines 36–44: `Path.unlink` — file removal, `missing_ok=True` is 3.8+

```python
# 4. unlink — removes a FILE (not a directory); missing_ok=True is 3.8+
f = scratch / "trash.txt"
f.write_text("trash", encoding="utf-8")
f.unlink()
print("4. unlink ok, exists=", f.exists())
try:
    f.unlink()
except FileNotFoundError as e:
    print("   unlink on missing raises FileNotFoundError:", e)
f.unlink(missing_ok=True)
print("   unlink(missing_ok=True) -> no error")
```

`f = scratch / "trash.txt"` builds the path; `f.write_text("trash", encoding="utf-8")` creates the file; `f.unlink()` removes it. The signature is `Path.unlink(self, missing_ok=False)`. The output `unlink ok, exists=False` confirms the removal. `Path.unlink` calls `os.unlink(self)`, which is the `unlink(2)` syscall — it removes one directory entry (the file's name in its parent directory). The file's inode is freed only if this was the last hard link to it; a file with multiple hard links loses one entry but keeps its data.

The contrast on lines 39–41 shows the failure mode for a missing file: `f.unlink()` raises `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/.../scratch/trash.txt'` because the file does not exist (it was just unlinked on line 37). The default `missing_ok=False` means "raise if the file does not exist" — the *safe* spelling that tells you the file was not there.

`f.unlink(missing_ok=True)` on line 43 is the *idempotent* spelling — the call removes the file if it exists, and does nothing (no raise) if it does not. The output `unlink(missing_ok=True) -> no error` confirms the swallow. The `missing_ok` parameter was added to `Path.unlink` in Python 3.8 (bpo-32981); before 3.8, the workaround was the `try: path.unlink(); except FileNotFoundError: pass` dance that the demo's lines 39–41 show.

The `missing_ok` parameter is the unlink-side equivalent of `mkdir`'s `exist_ok`. The default `missing_ok=False` is the *safe* spelling — the student who writes `f.unlink()` and gets `FileNotFoundError` has learned that the file was not there, which is information they might want (e.g. they are cleaning up a known file and the absence means a previous step failed). The `missing_ok=True` flag is the *idempotent* spelling for the case where you do not care — the equivalent of `rm -f` in the shell.

**Why was `missing_ok` added in 3.8 and not in 3.4?** Because the `try`/`except FileNotFoundError` dance was the most common pathlib bug reported on the issue tracker through 3.7 — students would write `path.unlink()` and crash on the missing case, then add the `try`/`except` and feel the API was hostile. The `missing_ok` flag was added in 3.8 to make the idempotent spelling one keyword away. On the 3.12 runtime this vault targets, the flag is available; on 3.7 and earlier, the `try`/`except` dance is the workaround.

### Lines 46–50: `Path.touch` — create-if-missing, update-mtime-if-present

```python
# 5. touch — creates the file if missing; updates mtime if present
t = scratch / "touched.txt"
t.touch()
print("5. touch ok, exists=", t.exists())
t.touch()  # second touch updates mtime; does not raise
print("   second touch ok (mtime updated)")
```

`t = scratch / "touched.txt"` builds the path; `t.touch()` creates the file (empty) if it does not exist, or updates the file's mtime (modification time) if it does. The signature is `Path.touch(self, mode=0o666, exist_ok=True)`. The output `touch ok, exists=True` confirms the creation; the second `t.touch()` does not raise (the default `exist_ok=True` swallows the would-be `FileExistsError`), and updates the mtime to the current time.

The `mode=0o666` default is the permission bits — same `mode & ~umask` rule as `mkdir`, so on a typical Linux umask of `022`, the file is created with `0o644` (rw-r--r--). The `exist_ok=True` default is the *opposite* of `mkdir`'s `exist_ok=False` default — touching is idempotent (the file's existence is the success condition), while `mkdir` is not (the directory's existence is the failure condition for a fresh-create intent).

Internally, `Path.touch` branches on whether the file exists. If the file does not exist, `touch` calls `os.open(self, flags, mode)` with `flags = O_CREAT | O_WRONLY` (and `O_EXCL` if `exist_ok=False`), then `os.close(fd)`, then `os.utime(self, None)` to update the mtime. If the file *does* exist and `exist_ok=True` (the default), `touch` skips the open/close and just calls `os.chmod(self, mode)` (to apply `mode`'s permission bits to the existing file) followed by `os.utime(self, None)` to refresh the mtime. If `exist_ok=False` and the file exists, `touch` raises `FileExistsError` instead of touching. The two-step (open, then utime) for the create path is what makes `touch` update the mtime even on a freshly-created file — the file gets a default mtime from the open, and the utime bumps it to the current time explicitly.

**Why is `exist_ok=True` the default for `touch` but `exist_ok=False` for `mkdir`?** Because the *intent* of `touch` is idempotent — you want the file to exist with a fresh mtime, and the existence is the success condition. The *intent* of `mkdir` is creative — you want to create a *new* directory, and the existence is the failure condition (you wanted fresh, you got existing). The asymmetry reflects the different semantics of the two operations: `touch` is "make sure this file is here and fresh", `mkdir` is "create a new directory here". The default for each is the spelling that matches the intent.

### Lines 52–55: `Path.rename` — POSIX overwrites a file target, Windows raises

```python
# 6. rename — POSIX overwrites if target is a file; Windows raises FileExistsError
a = scratch / "a.txt"
a.write_text("A", encoding="utf-8")
b = scratch / "b.txt"
b.write_text("B", encoding="utf-8")
a.rename(b)
print("6. rename(a -> b): a.txt exists=", a.exists(), ", b.txt contents=", repr(b.read_text(encoding="utf-8")))
```

`a = scratch / "a.txt"` and `b = scratch / "b.txt"` build two paths; both files are created with `write_text`. `a.rename(b)` moves `a.txt` to `b.txt`. The signature is `Path.rename(self, target)`. The output `rename(a -> b): a.txt exists=False, b.txt contents='A'` confirms the move — `a.txt` no longer exists, and `b.txt`'s contents are now `'A'` (the original contents of `a.txt`).

The interesting part is what happens when the target already exists. On POSIX, the `rename(2)` syscall *overwrites* the target if it is a file — so `a.rename(b)` where `b.txt` already existed silently replaced `b.txt`'s contents with `a.txt`'s contents (the original `'B'` is gone, the new contents are `'A'`). On Windows, the `MoveFileEx` API raises `FileExistsError` if the target exists — so the same call would raise on Windows. The platform-dependent behaviour is the *historical* behaviour of `os.rename`, which `pathlib` mirrors; the student who writes `a.rename(b)` and runs on POSIX gets overwrite, on Windows gets raise.

The asymmetry is a *portability* bug waiting to happen. The fix is `Path.replace(target)` (next section), which has the *portable* overwrite semantics — overwrite on every platform. The `rename` method exists for compatibility with the historical `os.rename` and for the case where you *want* the platform-dependent behaviour (rare); the `replace` method is the spelling for new code.

**Why does POSIX `rename(2)` overwrite a file target?** Because the original Unix `rename(2)` was designed for atomic file replacement — you write the new contents to a temp file, then `rename` the temp over the target, and the replacement is atomic (no window where the target does not exist). The POSIX `rename(2)` overwrites a file target atomically; it raises `ENOTEMPTY` if the target is a *non-empty* directory. The Windows `MoveFileEx` API has different semantics — it raises if the target exists unless you pass `MOVEFILE_REPLACE_EXISTING`. The `pathlib` API exposes both: `rename` mirrors `os.rename` (platform-dependent), `replace` mirrors `os.replace` (always-overwrite).

### Lines 57–62: `Path.replace` — the portable rename-to-existing

```python
# 7. replace — overwrites the target on every platform (the portable rename-to-existing)
c = scratch / "c.txt"
c.write_text("C-original", encoding="utf-8")
d = scratch / "d.txt"
d.write_text("D", encoding="utf-8")
d.replace(c)
print("7. replace(d -> c): c.txt contents=", repr(c.read_text(encoding="utf-8")), "(was 'C-original')")
```

`c = scratch / "c.txt"` and `d = scratch / "d.txt"` build two paths; `c.txt` is created with `'C-original'`, `d.txt` with `'D'`. `d.replace(c)` moves `d.txt` to `c.txt`, *overwriting* the existing `c.txt`. The signature is `Path.replace(self, target)`. The output `replace(d -> c): c.txt contents='D' (was 'C-original')` confirms the overwrite — `c.txt`'s contents are now `'D'`, the original `'C-original'` is gone, and `d.txt` no longer exists.

`Path.replace` is the *portable* rename-to-existing — it overwrites the target on every platform. On POSIX, it calls `os.replace(self, target)` which is the same as `os.rename` (POSIX `rename(2)` overwrites). On Windows, it calls `os.replace(self, target)` which calls `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` — the explicit overwrite flag. The result is identical behaviour on both platforms: the target is replaced, no raise.

The `replace` method was added to `os` in Python 3.3 (bpo-13600) and to `pathlib` in 3.4 (the original pathlib release). The historical `os.rename` had the platform-dependent behaviour (overwrite on POSIX, raise on Windows), which was a portability bug; `os.replace` was added to fix it. The `pathlib` API exposes both: `Path.rename` mirrors the historical `os.rename`, `Path.replace` mirrors the portable `os.replace`. The rule for new code is "use `replace` if the target might exist" — the only reason to use `rename` is if you *want* the platform-dependent behaviour (very rare) or if you are mirroring legacy `os.rename` code.

**Why does `pathlib` keep both `rename` and `replace`?** Because the two answer different questions. `rename` answers "move this path to that path, with whatever overwrite semantics the platform has" — the historical behaviour, kept for compatibility. `replace` answers "move this path to that path, overwriting the target if it exists, on every platform" — the portable behaviour, the new-code spelling. The stdlib chose to keep both rather than deprecate `rename` because (a) backwards compatibility — there is millions of lines of `os.rename` and `Path.rename` code, and the stdlib does not break it; (b) the platform-dependent behaviour of `rename` is *useful* in the rare case where you want to assert the target does not exist on Windows (you get a `FileExistsError`). The new-code rule is "use `replace` if the target might exist"; the legacy rule is "use `rename` if you are matching old `os.rename` code".

### Lines 64–67: `Path.iterdir` — the lazy directory iterator

```python
# 8. iterdir — lazy iteration over a directory's direct children
print("--- scratch.iterdir() ---")
for p in sorted(scratch.iterdir()):
    print("  ", p.name, "(is_dir=", p.is_dir(), ", is_file=", p.is_file(), ")")
```

`scratch.iterdir()` returns a *generator* of `Path` objects — one per direct child of `scratch`. The output shows six entries: the `a/`, `b.txt`, `c.txt`, `new/`, `non_empty/`, and `touched.txt` paths we created earlier in the demo. Each entry is a `Path`, with `.name`, `.is_dir()`, `.is_file()`, and every other pathlib accessor and method. The `sorted(...)` materialises the generator into a sorted list (so the output is deterministic — the generator's order is filesystem-dependent and not stable).

`Path.iterdir` is the non-pattern form of `Path.glob` — it yields *every* direct child, with no pattern filtering. The signature is `Path.iterdir(self)` — no arguments. Internally, it calls `os.scandir(self)` and yields a `Path` for each `DirEntry`. The laziness matters for directories with millions of entries — the generator uses constant memory, and you can break out early.

The `iterdir` method is the foundation that `Path.glob` is built on — `Path.glob(pattern)` is essentially `for p in self.iterdir(): if fnmatch(p.name, pattern): yield p`, with the `**` recursive marker adding the recursive walk. The `iterdir` method is the *raw* form, for the case where you want to filter by something other than a pattern (e.g. `for p in dir.iterdir(): if p.stat().st_size > 1024: ...`).

**Why `iterdir` and not just `glob("*")`?** Because `iterdir` is *faster* — it skips the `fnmatch` call and the pattern compilation, and on Windows it uses `FindFirstFile`/`FindNextFile` directly. The `glob("*")` form does the same scan but adds the `fnmatch` overhead. For the "give me everything" case, `iterdir` is the right call. For the "give me everything matching X" case, `glob` is the right call. The two are not interchangeable; they answer different questions.

## Execution Trace

```bash
$ uv run python boardly/paths/mkdir_unlink.py
1. mkdir ok, exists= True
   second mkdir raises FileExistsError: [Errno 17] File exists: '/tmp/tmp0uukjq41/boardly/scratch/new'
   mkdir(exist_ok=True) -> no error
2. mkdir(parents=True) ok, exists= True
   parents=False on missing parent raises FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp0uukjq41/boardly/scratch/x/y/z'
3. rmdir empty ok, exists= False
   rmdir non-empty raises OSError: [Errno 39] Directory not empty: '/tmp/tmp0uukjq41/boardly/scratch/non_empty'
4. unlink ok, exists= False
   unlink on missing raises FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp0uukjq41/boardly/scratch/trash.txt'
   unlink(missing_ok=True) -> no error
5. touch ok, exists= True
   second touch ok (mtime updated)
6. rename(a -> b): a.txt exists= False , b.txt contents= 'A'
7. replace(d -> c): c.txt contents= 'D' (was 'C-original')
--- scratch.iterdir() ---
   a (is_dir= True , is_file= False )
   b.txt (is_dir= False , is_file= True )
   c.txt (is_dir= False , is_file= True )
   new (is_dir= True , is_file= False )
   non_empty (is_dir= True , is_file= False )
   touched.txt (is_dir= False , is_file= True )
```

The `/tmp/tmp0uukjq41/` prefix on the `FileExistsError` and `FileNotFoundError` messages is the tmpdir the demo created; the prefix changes on every run, but the rest of the line is deterministic. The `errno 17` (`File exists`), `errno 2` (`No such file or directory`), and `errno 39` (`Directory not empty`) are the syscall errno values; the `OSError` subclass for `rmdir` on a non-empty directory is `OSError` (not a more specific subclass like `FileNotFoundError`).

## Common Mistakes

### Mistake 1: `rmdir` on a non-empty directory

```python
non_empty_dir.rmdir()    # OSError: [Errno 39] Directory not empty
```

**Symptom:** `OSError: [Errno 39] Directory not empty: '/path/to/dir'` — the call raises instead of removing the directory.
**Why:** `Path.rmdir` calls `os.rmdir`, which is the `rmdir(2)` syscall — it removes an *empty* directory only. A directory with any entries (files, subdirs) raises `ENOTEMPTY` (errno 39). The stdlib deliberately did not add a recursive-delete method to `pathlib`; the recursive case is `shutil.rmtree(path)`.
**Fix:** Decide what you want. For an empty directory: `path.rmdir()`. For a recursive delete: `import shutil; shutil.rmtree(path)`. The `shutil.rmtree` call is the spelling for recursive removal; the `path.rmdir` call is the spelling for empty-only. The two are not interchangeable; the choice is *deliberate* — the stdlib wants the dangerous recursive call to be a deliberate import of `shutil`, not a one-keystroke difference from the safe `rmdir`.

### Mistake 2: `unlink` without `missing_ok=True` on a maybe-missing file

```python
path.unlink()    # FileNotFoundError if the file is not there
```

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: '/path/to/file'` — the call raises instead of being a no-op.
**Why:** `Path.unlink` with the default `missing_ok=False` raises `FileNotFoundError` if the file does not exist. The default is the *safe* spelling — the student who writes `path.unlink()` and gets `FileNotFoundError` has learned the file was not there, which is information they might want.
**Fix:** If you want idempotent removal (remove if exists, no-op if not), pass `missing_ok=True`: `path.unlink(missing_ok=True)`. The `missing_ok` parameter is 3.8+; on 3.7 and earlier, the workaround is `try: path.unlink(); except FileNotFoundError: pass`. On the 3.12 runtime this vault targets, the flag is available.

### Mistake 3: `rename` to an existing target on Windows

```python
a.rename(b)    # FileExistsError on Windows; silent overwrite on POSIX
```

**Symptom:** On Windows, `FileExistsError: [Errno 17] File exists` — the call raises instead of overwriting. On POSIX, the call silently overwrites the target — the bug is the *opposite* on the two platforms.
**Why:** `Path.rename` mirrors `os.rename`, which has platform-dependent overwrite semantics: POSIX `rename(2)` overwrites a file target; Windows `MoveFileEx` raises unless you pass `MOVEFILE_REPLACE_EXISTING`. The asymmetry is a portability bug waiting to happen — the same code does different things on different OSes.
**Fix:** Use `Path.replace(target)` for portable overwrite: it calls `os.replace`, which overwrites the target on every platform. The `replace` method is the *new-code* spelling; `rename` is the *legacy* spelling. The only reason to use `rename` is if you want the platform-dependent behaviour (rare) or if you are mirroring legacy `os.rename` code.

### Mistake 4: `mkdir` without `parents=True` on a missing parent

```python
nested = Path("a/b/c")
nested.mkdir()    # FileNotFoundError: [Errno 2] No such file or directory: 'a'
```

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: '...'` — the call raises because the parent directory does not exist.
**Why:** `Path.mkdir` with the default `parents=False` calls `os.mkdir`, which is the `mkdir(2)` syscall — it creates one directory and raises if the parent does not exist. The default is the *safe* spelling — the student who writes `path.mkdir()` and gets `FileNotFoundError` has learned the parent was missing.
**Fix:** Pass `parents=True` for the `mkdir -p` spelling: `path.mkdir(parents=True)`. The `parents=True` flag calls `os.makedirs`, which creates intermediate dirs. The full `mkdir -p` semantics is `path.mkdir(parents=True, exist_ok=True)` — create intermediate dirs and do not raise if the leaf exists.

## Engineering Trade-Offs

**Decision:** Use `Path.mkdir`, `Path.rmdir`, `Path.unlink`, `Path.touch`, `Path.replace` for all filesystem mutation in `boardly`. Never `os.mkdir`, `os.makedirs`, `os.rmdir`, `os.remove`, `os.unlink`, `os.rename`, `os.replace`. Use `shutil.rmtree` for recursive directory removal (the deliberate recursive-delete spelling).
**Both sides:** The alternative is the `os` and `shutil` modules — `os.mkdir` (one dir), `os.makedirs` (recursive), `os.rmdir` (empty-only), `os.remove` / `os.unlink` (file), `os.rename` (platform-dependent overwrite), `os.replace` (portable overwrite), `shutil.rmtree` (recursive delete). The `os` functions lose to `pathlib` on (a) the result type (`os.*` takes `str`, `pathlib` takes `Path`), (b) the API sprawl (`mkdir` vs `makedirs`, `remove` vs `unlink` — `pathlib` unifies), and (c) the call-site brevity (`path.mkdir()` vs `os.mkdir(str(path))`). The `shutil` functions are the right spelling for the operations `pathlib` does not provide — `shutil.rmtree` (recursive delete), `shutil.copy` (file copy), `shutil.copytree` (recursive copy). The `pathlib` mutator methods cover creation and removal; the `shutil` functions cover copying and recursive operations.
**Commitment:** `boardly` uses `Path.mkdir(parents=True, exist_ok=True)` for directory creation (the `mkdir -p` spelling), `Path.unlink(missing_ok=True)` for file removal (the idempotent spelling), `Path.rmdir()` for empty-directory removal (the safe spelling), `Path.touch()` for file creation/mtime-update, and `Path.replace(target)` for portable rename-to-existing. The `shutil.rmtree` call is the spelling for recursive directory removal — it lives in `shutil`, not `pathlib`, deliberately. The `os.*` functions are forbidden in new code; the lint rule is `rg "os\.(mkdir|makedirs|rmdir|remove|unlink|rename|replace)\(" boardly/` returning zero matches.

## Exercises

1. **Exercise 1 — Create a nested tree.** Use `Path.mkdir(parents=True)` to create `boardly/data/archive/2024/10/` in a tmpdir. Confirm all four levels exist. `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); p = td / 'boardly' / 'data' / 'archive' / '2024' / '10'; p.mkdir(parents=True); assert p.exists() and p.is_dir(); print('nested ok')"`
2. **Exercise 2 — Test the `rmdir` empty-only behaviour.** Create a directory with one file in it, try `rmdir`, confirm `OSError`. Then remove the file with `unlink`, and confirm `rmdir` now succeeds. `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); d = td / 'd'; d.mkdir(); (d / 'f.txt').write_text('x', encoding='utf-8'); 
try:
    d.rmdir()
    print('FAIL: should have raised')
except OSError:
    print('raised ok')
(d / 'f.txt').unlink()
d.rmdir()
assert not d.exists(); print('rmdir ok')"`
3. **Exercise 3 — `unlink(missing_ok=True)` is idempotent.** Write a function `safe_unlink(path: Path)` that calls `path.unlink(missing_ok=True)` and returns `True` whether the file existed or not. Confirm it does not raise on a missing file. `Verify: uv run python -c "from pathlib import Path; import tempfile, sys; sys.path.insert(0, 'boardly/paths'); from mkdir_unlink import safe_unlink; td = Path(tempfile.mkdtemp()); p = td / 'missing.txt'; assert safe_unlink(p) is True; print('safe unlink ok')"` (you will need to add the `safe_unlink` function to `mkdir_unlink.py` for this exercise).
4. **Exercise 4 — `replace` is portable, `rename` is not.** Create two files `a.txt` and `b.txt`. Call `a.replace(b)` and confirm `b.txt`'s contents are now `a.txt`'s contents. Then do the same with `rename` and confirm the behaviour (on POSIX, same overwrite; on Windows, would raise). `Verify: uv run python -c "from pathlib import Path; import tempfile; td = Path(tempfile.mkdtemp()); a = td / 'a.txt'; b = td / 'b.txt'; a.write_text('A', encoding='utf-8'); b.write_text('B', encoding='utf-8'); a.replace(b); assert b.read_text(encoding='utf-8') == 'A' and not a.exists(); print('replace ok')"`
5. **Exercise 5 — Implement `safe_rmtree(path)` using only pathlib + iterdir.** Write a function `safe_rmtree(path: Path)` that recursively removes a directory tree using *only* `Path.iterdir`, `Path.is_dir`, `Path.rmdir`, and `Path.unlink` — no `shutil`. The function should walk the tree, unlink files, recurse into subdirs, then rmdir the empty subdirs from the leaves up. Compare its behaviour to `shutil.rmtree` on a 3-level tree. `Verify: uv run python -c "from pathlib import Path; import tempfile, sys; sys.path.insert(0, 'boardly/paths'); from mkdir_unlink import safe_rmtree; td = Path(tempfile.mkdtemp()); root = td / 'tree'; root.mkdir(); (root / 'a.txt').write_text('x', encoding='utf-8'); sub = root / 'sub'; sub.mkdir(); (sub / 'b.txt').write_text('y', encoding='utf-8'); safe_rmtree(root); assert not root.exists(); print('rmtree ok')"` (you will need to add the `safe_rmtree` function to `mkdir_unlink.py` for this exercise).

## Verification

```bash
$ uv run python boardly/paths/mkdir_unlink.py
1. mkdir ok, exists= True
   second mkdir raises FileExistsError: [Errno 17] File exists: '/tmp/tmp0uukjq41/boardly/scratch/new'
   mkdir(exist_ok=True) -> no error
2. mkdir(parents=True) ok, exists= True
   parents=False on missing parent raises FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp0uukjq41/boardly/scratch/x/y/z'
3. rmdir empty ok, exists= False
   rmdir non-empty raises OSError: [Errno 39] Directory not empty: '/tmp/tmp0uukjq41/boardly/scratch/non_empty'
4. unlink ok, exists= False
   unlink on missing raises FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp0uukjq41/boardly/scratch/trash.txt'
   unlink(missing_ok=True) -> no error
5. touch ok, exists= True
   second touch ok (mtime updated)
6. rename(a -> b): a.txt exists= False , b.txt contents= 'A'
7. replace(d -> c): c.txt contents= 'D' (was 'C-original')
--- scratch.iterdir() ---
   a (is_dir= True , is_file= False )
   b.txt (is_dir= False , is_file= True )
   c.txt (is_dir= False , is_file= True )
   new (is_dir= True , is_file= False )
   non_empty (is_dir= True , is_file= False )
   touched.txt (is_dir= False , is_file= True )
```

The `/tmp/tmp0uukjq41/` prefix on the `FileExistsError` and `FileNotFoundError` messages is the tmpdir the demo created; the prefix changes on every run, but the rest of the line is deterministic. The `errno 17`, `errno 2`, and `errno 39` are the syscall errno values; the `OSError` subclass for `rmdir` on a non-empty directory is `OSError` (not a more specific subclass). The `iterdir` output shows the six paths the demo created earlier — `a/`, `b.txt`, `c.txt`, `new/`, `non_empty/`, and `touched.txt`.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `Path` construction and `/` operator this lesson uses to build `scratch`, `nested`, `empty`, and the other paths; the basics lesson is the foundation for the mutator methods this lesson walks.
- [[08-pathlib/02-read-write-text-binary]] — the `write_text(encoding="utf-8")` calls this lesson uses to seed files before removing them; the I/O lesson is where the file-creation methods are walked.
- [[08-pathlib/03-glob-and-rglob]] — the `iterdir` method (mentioned at the end of this lesson) is the non-pattern form of `glob`; the glob lesson covers the pattern-matching form.

## What's Next

The next lessons in this section walk the remaining pathlib surface. **Lesson 05** walks `PurePath` vs `Path` — the no-I/O string-algebra base class that lets you manipulate Windows path strings on a Linux machine (config validation), and why a config validator should accept `PurePath` not `Path`. **Lesson 06** walks `Path.iterdir` and `Path.walk` (3.12+) — the lazy directory iterator and the `os.walk` replacement yielding `(dirpath, dirnames, filenames)`. **Lesson 07** walks `Path.stat` and permissions — `.stat().st_size` / `.st_mtime`, `lstat()` for symlinks, `chmod(0o644)`, the `S_*` mode bits.

- **[[08-pathlib/05-PurePath-vs-Path]]** — `PurePath` vs `Path` (the no-I/O base class).
- **[[08-pathlib/06-walk-and-iterdir]]** — `iterdir` and `walk` (3.12+) for directory traversal.
- **[[08-pathlib/07-stat-and-permissions]]** — `stat`, `lstat`, `chmod`, permissions.

## Sources

- **Python `pathlib` module documentation** — https://docs.python.org/3/library/pathlib.html — accessed 2026-10-23 — the source-of-truth reference for `Path.mkdir`, `Path.rmdir`, `Path.unlink` (with `missing_ok` 3.8+), `Path.touch`, `Path.rename`, `Path.replace`, `Path.iterdir`; documents the `parents`/`exist_ok` flags and the platform-dependent `rename` semantics.
- **Python `os` module documentation** — https://docs.python.org/3/library/os.html — accessed 2026-10-23 — the underlying syscalls `pathlib` wraps (`mkdir(2)`, `rmdir(2)`, `unlink(2)`, `rename(2)`); documents the `errno` values (17 `EEXIST`, 2 `ENOENT`, 39 `ENOTEMPTY`).
- **Python `shutil` module documentation** — https://docs.python.org/3/library/shutil.html — accessed 2026-10-23 — the recursive operations `pathlib` deliberately does not provide (`shutil.rmtree`, `shutil.copy`, `shutil.copytree`); documents why the stdlib keeps recursive deletion in `shutil` rather than `pathlib`.

## What We Learned

- You can now create a directory with `Path.mkdir(parents=True, exist_ok=True)` and explain why `parents=True` is the `mkdir -p` spelling and `exist_ok=True` swallows `FileExistsError`.
- You can remove an empty directory with `Path.rmdir()` and explain why it raises `OSError` (errno 39, `Directory not empty`) on a non-empty directory — and that the recursive case is `shutil.rmtree`, deliberately.
- You can remove a file with `Path.unlink(missing_ok=True)` and explain why the `missing_ok` kwarg (3.8+) is the idempotent spelling.
- You can touch a file with `Path.touch(mode=0o666, exist_ok=True)` and explain why `exist_ok=True` is the default for `touch` but `exist_ok=False` is the default for `mkdir` — the asymmetry reflects intent.
- You can rename a file with `Path.replace(target)` (portable overwrite) and explain why `Path.rename(target)` (platform-dependent overwrite) is the legacy spelling — and that the new-code rule is "use `replace` if the target might exist".
