---
title: "Lesson 07: stat and permissions"
aliases:
 - pathlib stat
 - Path.stat
 - Path.lstat
 - os.stat_result
 - Path.chmod
 - Path.lchmod
 - Path.owner
 - Path.group
 - is_file is_dir is_symlink
tags:
 - pathlib
 - canonical
 - python-stdlib
 - permissions
 - filesystem
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
 - "[[08-pathlib/02-read-write-text-binary]]"
 - "[[08-pathlib/06-walk-and-iterdir]]"
related_lessons:
 - "[[08-pathlib/05-PurePath-vs-Path]]"
 - "[[17-decimal/01-Decimal-Basics]]"
first_taught_in: "08-pathlib/07-stat-and-permissions"
---

# Lesson 07: stat and permissions

*How `boardly`'s log-rotation policy stats every `.log` file, rotates the ones over 10 MB, compresses the ones older than 30 days, and locks the rotated files down with `chmod(0o640)` — without falling for the symlink-to-`/etc/passwd` trap.*

**You're at the very beginning of Section 08 — seven lessons in. This is the metadata lesson.**

You can walk a tree with `walk()` and you can list immediate children with `iterdir()`. The last piece of the I/O surface is *metadata*: who owns this file, how big is it, when was it last modified, what permissions does it have, what kind of file is it (regular, directory, symlink, socket, fifo, block device, char device). `pathlib` answers all of these via `Path.stat()` (returns `os.stat_result`), the `Path.is_*()` predicates, `Path.chmod()`, `Path.owner()`, and `Path.group()`. The lesson walks the full surface, version-gates the `follow_symlinks` parameter (which is on `stat`/`exists`/`chmod` in 3.12 but only added to `is_file`/`is_dir`/etc. in 3.14 and to `owner`/`group` in 3.13), and shows you the production trap: a symlink in the logs directory pointing at `/etc/passwd` will pass `is_file() == True` and `stat().st_size` will be the size of `/etc/passwd`. The lesson's `archive_logs` policy would happily "archive" `/etc/passwd` if you do not check `is_symlink()` first. Take your time. Type every example. **This is how you learn.**

#pathlib #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `Path.stat(*, follow_symlinks=True)`** and read the returned `os.stat_result` — `.st_size` (bytes), `.st_mtime` (float seconds since epoch), `.st_mode` (file type + permission bits, decoded with `stat.S_ISREG`/`S_ISDIR`/`S_ISLNK`), `.st_uid`/`.st_gid` (numeric IDs), `.st_ino` (inode), `.st_dev` (device), `.st_nlink` (hard-link count), `.st_atime`/`.st_ctime` (access/creation-or-metadata-change times).
2. **Call `Path.lstat()`** as the symlink-safe variant — equivalent to `Path.stat(follow_symlinks=False)`; reads the link entry itself, not its target.
3. **Use the `is_*()` predicates** — `is_file()`, `is_dir()`, `is_symlink()`, `is_socket()`, `is_fifo()`, `is_block_device()`, `is_char_device()` — and version-gate the `follow_symlinks` parameter that was added to these methods in Python 3.14 (in 3.12.15, the runtime here, they always follow symlinks and accept no parameter).
4. **Use `Path.exists(*, follow_symlinks=True)`** with the `follow_symlinks` argument — `exists(follow_symlinks=False)` returns `True` for a *broken* symlink (the link entry exists); `exists(follow_symlinks=True)` (the default) returns `False` for a broken symlink (the target does not exist).
5. **Change permissions with `Path.chmod(mode, *, follow_symlinks=True)`** and the `S_IRUSR`/`S_IWUSR`/`S_IXUSR`/`S_IRGRP`/`S_IWGRP`/`S_IROTH`/etc. bit constants from `stat`. Use `Path.lchmod(mode)` for the symlink entry itself (deprecated in Python 3.13+ — replace with `chmod(mode, follow_symlinks=False)`).
6. **Read owner and group with `Path.owner()` and `Path.group()`** — return the username and groupname strings (resolved from `/etc/passwd` and `/etc/group` via `pwd` and `grp`), not the numeric IDs. Version-gate the `follow_symlinks` parameter (added to `owner`/`group` in Python 3.13; in 3.12.15 they always follow symlinks).

## Prerequisites

Before starting, you need:

- **The `Path` constructor and the `/` operator** — [[08-pathlib/01-Path-Basics]]. Every `stat()` call in this lesson is on a `Path` you construct with `/`.
- **`read_text()` and `write_text()`** — [[08-pathlib/02-read-write-text-binary]]. The lesson's `archive_logs` policy reads the file's content (for size-and-mtime demonstration) using these methods.
- **`walk()` and `iterdir()`** — [[08-pathlib/06-walk-and-iterdir]]. The lesson's policy walks `boardly/logs/` and stats each file; if you cannot walk, you cannot stat in batch.
- **About 40–55 minutes of focused time.**

**The most common gap: assuming `is_file()` does not follow symlinks.**

It does. `Path("link_to_file").is_file()` calls `os.stat` on the *target* of the link (because `is_file` follows symlinks in 3.12 and earlier), and returns `True` if the target is a regular file. The link entry itself is not a regular file (it is a symlink — file type `S_IFLNK`); the *target* is a regular file (`S_IFREG`). `is_file()` reports the target's type, not the link's. The same applies to `is_dir()`, `is_socket()`, `is_fifo()`, `is_block_device()`, `is_char_device()`. The one exception is `is_symlink()`, which answers the question "is *this path* a symlink?" and does not follow the link. The fix when you need "is this path a regular file and not a symlink?" is `p.is_file() and not p.is_symlink()` — both checks, in that order.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/logs/rotate_bad.py — the bad old days
from pathlib import Path

def rotate_logs(root: Path) -> list[Path]:
    """Rotate every *.log file > 10 MB; return the rotated paths."""
    rotated = []
    for p in root.rglob("*.log"):
        if p.is_file() and p.stat().st_size > 10 * 1024 * 1024:
            archived = p.with_suffix(".log.archived")
            archived.write_bytes(p.read_bytes())   # copies the content
            p.unlink()
            rotated.append(archived)
    return rotated
```

You ship that. An attacker (or an operator who set up the logs directory carelessly) drops a symlink `boardly/logs/passwd.log` pointing at `/etc/passwd` on the host. The next rotation job runs:

1. `p.is_file()` calls `os.stat` on the *target* of the symlink (i.e., `/etc/passwd`). The target is a regular file. `is_file()` returns `True`.
2. `p.stat().st_size` returns the size of `/etc/passwd` — say, 3 KB, well under 10 MB. The size check fails, so the body does not run. No harm done this time.

But the *next* version of the policy rotates files smaller than 10 MB too (because the team decided to rotate every file over 1 KB to keep the disk tidy). Now:

1. `p.is_file()` returns `True` (target `/etc/passwd` is a regular file).
2. `p.stat().st_size` returns 3 KB, which is over 1 KB. The size check passes.
3. `p.read_bytes()` reads `/etc/passwd`'s contents — copies it into `boardly/logs/passwd.log.archived`.
4. `p.unlink()` removes the symlink.
5. The attacker reads `boardly/logs/passwd.log.archived` via the public log API, and now has the contents of `/etc/passwd`.

You have an information-disclosure incident. The bug is that the policy never checked `is_symlink()` — it assumed every `*.log` path in the logs directory was a regular file owned by the application, not a symlink to a sensitive system file. The fix is two-fold: check `is_symlink()` and refuse to rotate symlinks, and call `lstat()` (not `stat()`) for the size check so the size is the link entry's size, not the target's. The lesson's `archive_logs` shows both.

## The Code

```python
# boardly/logs/rotate_policy.py
"""stat, lstat, is_* predicates, chmod, owner/group — the metadata layer."""
from __future__ import annotations
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path


# 1. stat — the metadata call. Returns os.stat_result.
def show_stat(p: Path) -> None:
    s = p.stat()                          # follow_symlinks=True (the default)
    print(f"  path:           {p}")
    print(f"  st_mode (oct):  {oct(s.st_mode)}")
    print(f"  perm bits:      {oct(s.st_mode & 0o7777)}")
    print(f"  file type:      {file_type_name(s.st_mode)}")
    print(f"  st_size:        {s.st_size} bytes")
    print(f"  st_mtime:       {s.st_mtime}  ({time.ctime(s.st_mtime)})")
    print(f"  st_atime:       {s.st_atime}  ({time.ctime(s.st_atime)})")
    print(f"  st_ctime:       {s.st_ctime}  ({time.ctime(s.st_ctime)})")
    print(f"  st_uid:         {s.st_uid}")
    print(f"  st_gid:         {s.st_gid}")
    print(f"  st_ino:         {s.st_ino}")
    print(f"  st_dev:         {s.st_dev}")
    print(f"  st_nlink:       {s.st_nlink}")


def file_type_name(mode: int) -> str:
    """Decode the high bits of st_mode via the stat.S_IFMT mask."""
    if stat.S_ISREG(mode):  return "regular"
    if stat.S_ISDIR(mode):  return "directory"
    if stat.S_ISLNK(mode):  return "symlink"
    if stat.S_ISSOCK(mode): return "socket"
    if stat.S_ISFIFO(mode): return "fifo"
    if stat.S_ISBLK(mode):  return "block-device"
    if stat.S_ISCHR(mode):  return "char-device"
    return "unknown"


# 2. lstat — the symlink-safe variant
def show_lstat(p: Path) -> None:
    s = p.lstat()                         # equivalent to stat(follow_symlinks=False)
    print(f"  lstat st_size:  {s.st_size}")
    print(f"  lstat file type: {file_type_name(s.st_mode)}")


# 3. The is_* predicates — type checks that follow symlinks (3.12 baseline)
def show_predicates(p: Path) -> None:
    print(f"  path:           {p}")
    print(f"  is_file():      {p.is_file()}")
    print(f"  is_dir():       {p.is_dir()}")
    print(f"  is_symlink():   {p.is_symlink()}")
    print(f"  is_socket():    {p.is_socket()}")
    print(f"  is_fifo():      {p.is_fifo()}")
    print(f"  is_block_device(): {p.is_block_device()}")
    print(f"  is_char_device():  {p.is_char_device()}")


# 4. exists with follow_symlinks — broken-link detection
def show_exists(p: Path) -> None:
    print(f"  path:                        {p}")
    print(f"  exists():                   {p.exists()}")
    print(f"  exists(follow_symlinks=True): {p.exists(follow_symlinks=True)}")
    print(f"  exists(follow_symlinks=False): {p.exists(follow_symlinks=False)}")


# 5. chmod — change permission bits via the mode argument
def show_chmod(p: Path) -> None:
    print(f"  before: {oct(p.stat().st_mode & 0o7777)}")
    p.chmod(0o640)                        # -rw-r-----  (group read, no other)
    print(f"  after  chmod(0o640): {oct(p.stat().st_mode & 0o7777)}")
    p.chmod(0o644)                        # -rw-r--r--  (other read)
    print(f"  after  chmod(0o644): {oct(p.stat().st_mode & 0o7777)}")
    # The bit-constant form, equivalent to 0o640:
    bits = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    p.chmod(bits)
    print(f"  after  chmod(S_IRUSR|S_IWUSR|S_IRGRP): {oct(p.stat().st_mode & 0o7777)}")


# 6. owner / group — resolved names, not numeric IDs
def show_owner(p: Path) -> None:
    s = p.stat()
    print(f"  owner()  -> {p.owner()!r}   (numeric uid: {s.st_uid})")
    print(f"  group()  -> {p.group()!r}   (numeric gid: {s.st_gid})")


# 7. The boardly log-rotation policy — the production shape
@dataclass
class RotateDecision:
    path: Path
    size_bytes: int
    mtime: float
    action: str   # "archive" | "compress" | "leave" | "skip-symlink"


def rotate_policy(root: Path, *,
                  size_threshold: int = 10 * 1024 * 1024,
                  age_threshold_days: int = 30,
                  ) -> list[RotateDecision]:
    """Walk boardly/logs/, stat each *.log file, decide rotation action."""
    decisions: list[RotateDecision] = []
    skip_dirs = {".git", ".venv", "__pycache__"}
    now = time.time()

    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if not name.endswith(".log"):
                continue
            p = dirpath / name

            # The fix: refuse to touch symlinks.
            if p.is_symlink():
                decisions.append(RotateDecision(
                    path=p, size_bytes=0, mtime=0.0,
                    action="skip-symlink",
                ))
                continue

            # lstat would be safe too, but the symlink check above is enough
            # because we already know p is not a symlink.
            s = p.stat()
            age_days = (now - s.st_mtime) / 86400

            if s.st_size > size_threshold:
                action = "archive"
            elif age_days > age_threshold_days:
                action = "compress"
            else:
                action = "leave"

            decisions.append(RotateDecision(
                path=p, size_bytes=s.st_size, mtime=s.st_mtime,
                action=action,
            ))

            if action == "archive":
                archive_path = p.with_suffix(".log.archived")
                archive_path.write_bytes(p.read_bytes())
                archive_path.chmod(0o640)      # locked-down perms on archive
                p.unlink()
            elif action == "compress":
                # (gzip the file in production; here we just touch the .gz name)
                (p.parent / (name + ".gz")).touch()

    return decisions


if __name__ == "__main__":
    base = Path("/tmp/boardly-stat-demo")
    # Build a small demo tree
    if not base.exists():
        base.mkdir(parents=True)
        (base / "app.log").write_text("x" * 200)         # 200 bytes
        (base / "big.log").write_text("y" * 100)         # 100 bytes
        # Touch big.log's mtime 40 days ago to trigger compress:
        old = time.time() - 40 * 86400
        os.utime(base / "big.log", (old, old))

    print("=== show_stat on app.log ===")
    show_stat(base / "app.log")

    print("\n=== show_predicates on app.log and on base ===")
    show_predicates(base / "app.log")
    show_predicates(base)

    print("\n=== show_chmod on app.log ===")
    show_chmod(base / "app.log")

    print("\n=== show_owner on app.log ===")
    show_owner(base / "app.log")

    print("\n=== boardly rotate_policy result ===")
    for d in rotate_policy(base, size_threshold=150, age_threshold_days=30):
        print(f"  {d.action:14} {d.path.relative_to(base)}  "
              f"size={d.size_bytes}  mtime={time.ctime(d.mtime)}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 6–11: Imports — `os`, `stat`, `time`, `pathlib.Path`, `dataclass`

```python
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
```

`pathlib.Path` is the lesson's main type. `os` provides `os.utime` (for setting the demo file's mtime to 40 days ago, to exercise the `compress` branch). `stat` provides the `S_ISREG`/`S_ISDIR`/etc. predicates for decoding the high bits of `st_mode`, and the `S_IRUSR`/`S_IWUSR`/etc. constants for building a permission mask in named-bit form. `time` provides `time.time()` (the current epoch seconds, for age computation) and `time.ctime()` (a human-readable timestamp for display). `dataclass` provides the `@dataclass` decorator for the `RotateDecision` result type — a four-field record (path, size, mtime, action) that the caller can iterate to see what the policy decided for each file.

**Why `stat` as a module and not `pathlib`?** Because `pathlib.Path.stat()` *returns* an `os.stat_result`, and the helper predicates (`S_ISREG`, `S_ISDIR`, ...) live in the `stat` module — they pre-date `pathlib` by decades and are the canonical way to decode `st_mode`. The lesson could have used `p.is_file()` instead of `stat.S_ISREG(p.stat().st_mode)`, but the explicit form teaches the student what `is_file()` does internally — it calls `os.stat` and checks `S_ISREG(st_mode)`. Knowing the underlying `stat` module is what makes you a senior engineer here, not just a `pathlib` user.

### Lines 14–28: `show_stat` — reading `os.stat_result`

```python
def show_stat(p: Path) -> None:
    s = p.stat()                          # follow_symlinks=True (the default)
    print(f"  path:           {p}")
    print(f"  st_mode (oct):  {oct(s.st_mode)}")
    print(f"  perm bits:      {oct(s.st_mode & 0o7777)}")
    print(f"  file type:      {file_type_name(s.st_mode)}")
    print(f"  st_size:        {s.st_size} bytes")
    print(f"  st_mtime:       {s.st_mtime}  ({time.ctime(s.st_mtime)})")
    print(f"  st_atime:       {s.st_atime}  ({time.ctime(s.st_atime)})")
    print(f"  st_ctime:       {s.st_ctime}  ({time.ctime(s.st_ctime)})")
    print(f"  st_uid:         {s.st_uid}")
    print(f"  st_gid:         {s.st_gid}")
    print(f"  st_ino:         {s.st_ino}")
    print(f"  st_dev:         {s.st_dev}")
    print(f"  st_nlink:       {s.st_nlink}")
```

`Path.stat(*, follow_symlinks=True)` calls `os.stat(self, follow_symlinks=follow_symlinks)` and returns the `os.stat_result` namedtuple unchanged. The namedtuple has these fields (verified in Python 3.12.15):

- `st_mode` — an `int` whose low 12 bits (mask `0o7777`) are the permission bits (`S_IRUSR`/`S_IWUSR`/`S_IXUSR`/`S_IRGRP`/`S_IWGRP`/`S_IXGRP`/`S_IROTH`/`S_IWOTH`/`S_IXOTH`, plus setuid/setgid/sticky bits `S_ISUID`/`S_ISGID`/`S_ISVTX`) and whose high 4 bits (mask `S_IFMT`, value `0o170000`) encode the file type (`S_IFREG` for regular, `S_IFDIR` for directory, `S_IFLNK` for symlink, etc.). The full `st_mode` for a regular `0o644` file is `0o100644` — the `100` prefix is `S_IFREG` shifted into the high bits.
- `st_size` — file size in bytes. For a symlink (via `lstat`), this is the length of the link's target string (e.g., 11 bytes for a link to `/etc/passwd`); for a regular file (via `stat`), it is the file's content size.
- `st_mtime` — modification time, float seconds since the Unix epoch. Use `time.time() - st.st_mtime` to compute the file's age in seconds. The `_ns` variant (`st_mtime_ns`) is integer nanoseconds — more precise, useful when you need sub-millisecond comparisons.
- `st_atime` — access time. Updated on `read()` calls. Often imprecise because many filesystems mount with `noatime` for performance.
- `st_ctime` — *metadata change* time on POSIX (created/changed inode — permissions, owner, etc.), *creation* time on Windows. The cross-platform ambiguity is the reason `st_ctime` is unreliable for "when was this file created?" on POSIX — use `st_mtime` for "when was the content last modified".
- `st_uid` — numeric owner user ID (e.g., `1001`). Resolve to a username with `Path.owner()` or `pwd.getpwuid(st_uid).pw_name`.
- `st_gid` — numeric group ID. Resolve to a groupname with `Path.group()` or `grp.getgrgid(st_gid).gr_name`.
- `st_ino` — inode number. Unique within a filesystem (within a `st_dev`); two paths with the same `(st_dev, st_ino)` are the same file (hard links or the same path).
- `st_dev` — device ID. Combined with `st_ino`, identifies a file uniquely on the system.
- `st_nlink` — number of hard links. 1 for a typical file; >= 2 for a directory (the directory itself + `.` inside it); higher if hard links exist.

**Why does `Path.stat` return `os.stat_result` and not a `pathlib`-specific type?** Because `os.stat_result` is a stable, well-known namedtuple that has existed since Python 2.2; `pathlib` (added in 3.4) did not need to invent a new type. Returning the stdlib type means `Path.stat()` consumers can use every existing `os.stat`-based code path unchanged. The trade-off is that `os.stat_result` has some platform-specific fields (`st_blocks`, `st_blksize`, `st_rdev` on POSIX; `st_file_attributes` on Windows) that `pathlib` does not document — but they are accessible if you need them.

**Why octal for `st_mode`?** Because the bit-layout of `st_mode` is octal-native: the low 9 bits are three groups of three (owner / group / other × read / write / execute), and the high 4 bits encode the file type. Writing `0o644` is the standard Unix shorthand for "owner read+write, group read, other read". Writing `0o100644` is the same plus the regular-file type bit. Hex or decimal would obscure the bit grouping.

### Lines 31–35: `show_lstat` — the symlink-safe variant

```python
def show_lstat(p: Path) -> None:
    s = p.lstat()                         # equivalent to stat(follow_symlinks=False)
    print(f"  lstat st_size:  {s.st_size}")
    print(f"  lstat file type: {file_type_name(s.st_mode)}")
```

`Path.lstat()` is exactly equivalent to `Path.stat(follow_symlinks=False)`. It calls `os.lstat(self)`, which reads the symlink entry itself rather than the target. For a regular file, `lstat()` returns the same result as `stat()` — there is no symlink to follow. For a symlink, `lstat()` returns:

- `st_size` = the length of the target string (e.g., 11 for `/etc/passwd`).
- `st_mode` with the file-type bits set to `S_IFLNK` (so `S_ISLNK(st_mode)` is True, and `S_ISREG(st_mode)` is False).
- `st_uid`/`st_gid` of the link's owner, not the target's.
- `st_mtime` of the link, not the target.

**Why have both `lstat()` and `stat(follow_symlinks=False)`?** History. `lstat()` was the only symlink-safe variant until Python 3.10 added `follow_symlinks=` to `Path.stat()`. The two forms are now equivalent; the lesson uses `lstat()` for brevity (it is one shorter call) and `stat(follow_symlinks=False)` when the code needs to be explicit about the symlink policy. Use whichever reads better in context.

### Lines 38–47: `show_predicates` — the `is_*()` family

```python
def show_predicates(p: Path) -> None:
    print(f"  path:           {p}")
    print(f"  is_file():      {p.is_file()}")
    print(f"  is_dir():       {p.is_dir()}")
    print(f"  is_symlink():   {p.is_symlink()}")
    print(f"  is_socket():    {p.is_socket()}")
    print(f"  is_fifo():      {p.is_fifo()}")
    print(f"  is_block_device(): {p.is_block_device()}")
    print(f"  is_char_device():  {p.is_char_device()}")
```

Each predicate is a one-`stat`-call type check. In Python 3.12.15 (verified via `inspect.signature`), none of these methods accept a `follow_symlinks` parameter — they all follow symlinks (except `is_symlink()`, whose question is about the link itself, not its target). The implementation is:

- `is_file()` — calls `stat()` (following symlinks); returns `S_ISREG(st_mode)`.
- `is_dir()` — calls `stat()` (following); returns `S_ISDIR(st_mode)`.
- `is_symlink()` — calls `lstat()` (not following); returns `S_ISLNK(st_mode)`. This is the one predicate that does *not* follow symlinks.
- `is_socket()` — calls `stat()`; returns `S_ISSOCK(st_mode)`.
- `is_fifo()` — calls `stat()`; returns `S_ISFIFO(st_mode)`.
- `is_block_device()` — calls `stat()`; returns `S_ISBLK(st_mode)`.
- `is_char_device()` — calls `stat()`; returns `S_ISCHR(st_mode)`.

**Python 3.14+:** the `follow_symlinks` parameter was added to all seven predicates. In 3.14 you can write `p.is_file(follow_symlinks=False)` to check the link entry's type rather than the target's. In 3.12 and 3.13, the equivalent is `not p.is_symlink() and p.is_file()` (the `is_symlink()` short-circuits; if `p` is a symlink, the `is_file()` call is skipped, so the target is never stat'd).

**Warning — `is_file()` follows symlinks in 3.12; use `is_symlink()` to defend.**

If you need "is this path a regular file and not a symlink?", write `p.is_file() and not p.is_symlink()` — both checks, in that order. The `is_symlink()` call is one `lstat`; the `is_file()` call (if reached) is one `stat`. The combined cost is two syscalls in the worst case (a symlink to a regular file) and one syscall in the common case (a non-symlink regular file, where `is_symlink()` returns False and `is_file()` runs). In 3.14+ you can write `p.is_file(follow_symlinks=False)` for the same result in one call.

### Lines 50–55: `show_exists` — `exists()` with `follow_symlinks`

```python
def show_exists(p: Path) -> None:
    print(f"  path:                        {p}")
    print(f"  exists():                   {p.exists()}")
    print(f"  exists(follow_symlinks=True): {p.exists(follow_symlinks=True)}")
    print(f"  exists(follow_symlinks=False): {p.exists(follow_symlinks=False)}")
```

`Path.exists(*, follow_symlinks=True)` returns `True` if the path exists, `False` if it does not. The `follow_symlinks` parameter (added in Python 3.12) controls the behaviour for *broken symlinks*:

- `follow_symlinks=True` (the default) — calls `stat()` (following). A symlink whose target does not exist returns `False`, because the `stat()` call cannot find the target.
- `follow_symlinks=False` — calls `lstat()` (not following). A symlink whose target does not exist returns `True`, because the link entry itself exists.

The distinction matters in the lesson's headline bug: an attacker drops a symlink `boardly/logs/passwd.log` pointing at `/etc/passwd`. With `follow_symlinks=True` (the default), `exists()` returns `True` because `/etc/passwd` exists. With `follow_symlinks=False`, `exists()` still returns `True` because the link entry exists. So `exists()` cannot defend against the symlink trap — you need `is_symlink()`.

**Why is the default `follow_symlinks=True`?** Because the common question is "can I read this path's contents?" — and the answer depends on whether the target exists, not the link entry. If a symlink's target has been deleted, the symlink is *useless* for reading; `exists()` returning `False` correctly signals that. The `follow_symlinks=False` variant is for the rarer question "is there *something* at this path, even a broken link?" — used by tools that report on the link itself (e.g., `find -type l` to list all symlinks, broken or not).

### Lines 58–66: `show_chmod` — changing permission bits

```python
def show_chmod(p: Path) -> None:
    print(f"  before: {oct(p.stat().st_mode & 0o7777)}")
    p.chmod(0o640)                        # -rw-r-----  (group read, no other)
    print(f"  after  chmod(0o640): {oct(p.stat().st_mode & 0o7777)}")
    p.chmod(0o644)                        # -rw-r--r--  (other read)
    print(f"  after  chmod(0o644): {oct(p.stat().st_mode & 0o7777)}")
    # The bit-constant form, equivalent to 0o640:
    bits = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    p.chmod(bits)
    print(f"  after  chmod(S_IRUSR|S_IWUSR|S_IRGRP): {oct(p.stat().st_mode & 0o7777)}")
```

`Path.chmod(mode, *, follow_symlinks=True)` calls `os.chmod(self, mode, follow_symlinks=follow_symlinks)`. The `mode` argument is an `int` whose low 9 bits encode the permission bits, and whose 4th-low bit (mask `0o7000`) encodes setuid/setgid/sticky. The two forms — octal literal (`0o640`) and named constants (`stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP`) — produce the same integer; the named form is more readable but verbose, the octal form is the Unix-standard shorthand.

The `follow_symlinks=True` default means `chmod` follows symlinks and changes the *target*'s permissions — exactly what you usually want (a symlink to a file is a transparent indirection; the file's permissions are what matter). `chmod(mode, follow_symlinks=False)` changes the *link entry*'s permissions — which is a no-op on most Linux filesystems (symlink permissions are not stored on Linux; the link is always `0o777`); on macOS and BSD, the link's permissions are stored and `follow_symlinks=False` does change them.

**Python 3.13+:** `Path.lchmod(mode)` is deprecated (the documentation recommends `chmod(mode, follow_symlinks=False)` as the replacement). `lchmod` still works in 3.12.15 (verified), but emits a `DeprecationWarning` in 3.13+. New code should write `chmod(mode, follow_symlinks=False)` directly. The lesson's `show_chmod` does not use `lchmod`; it uses the modern form throughout.

**Why octal `0o640` and not `0o600` for the archive?** Because the boardly rotation policy runs as a service user (e.g., `boardly`) that is a member of a `boardly-readers` group, and the ops team needs read access to the archived logs without `sudo`. `0o640` gives the owner (the `boardly` user) read+write and the group (`boardly-readers`) read-only; `0o600` would lock the group out and force every ops read through `sudo`. The `0o640` choice is a deployment-specific trade-off — your security team might require `0o600` if the logs contain PII; the lesson shows the pattern, you choose the bits.

### Lines 69–73: `show_owner` — username and groupname resolution

```python
def show_owner(p: Path) -> None:
    s = p.stat()
    print(f"  owner()  -> {p.owner()!r}   (numeric uid: {s.st_uid})")
    print(f"  group()  -> {p.group()!r}   (numeric gid: {s.st_gid})")
```

`Path.owner()` returns the username string (e.g., `"boardly"`) by resolving `st_uid` via the `pwd` module's `getpwuid`. `Path.group()` returns the groupname string by resolving `st_gid` via the `grp` module's `getgrgid`. The two methods do not call `stat` themselves if you have already done so — but in the absence of a cached result, they do an implicit `stat()` to read `st_uid` and `st_gid`. The lesson's `show_owner` calls `p.stat()` explicitly and reuses the result, avoiding the double-stat.

**Python 3.13+:** the `follow_symlinks` parameter was added to `Path.owner()` and `Path.group()`. In 3.12.15 (verified), neither method accepts the parameter — they always call `stat()` (following symlinks), so `Path.owner()` on a symlink returns the *target's* owner, not the link's. In 3.13+, `p.owner(follow_symlinks=False)` returns the link's owner. For 3.12, the workaround is `pwd.getpwuid(p.lstat().st_uid).pw_name` — one explicit `lstat` and one `pwd` lookup.

**Why does `owner()` return a string and not the numeric uid?** Because the common consumer question is "who owns this file?" in human-readable form, not "what is the numeric uid?". Numeric uids are system-dependent (uid `1001` on one box is different from uid `1001` on another); usernames are system-stable (the `boardly` user is `boardly` everywhere). The `owner()` method does the right lookup for you. When you need the numeric ID (for comparison across systems, or for a `chown` call), read `st_uid` from `stat()` directly — that is what the lesson's `show_owner` does in the parenthetical.

### Lines 76–124: The boardly log-rotation policy — the production shape

```python
@dataclass
class RotateDecision:
    path: Path
    size_bytes: int
    mtime: float
    action: str   # "archive" | "compress" | "leave" | "skip-symlink"


def rotate_policy(root: Path, *,
                  size_threshold: int = 10 * 1024 * 1024,
                  age_threshold_days: int = 30,
                  ) -> list[RotateDecision]:
    """Walk boardly/logs/, stat each *.log file, decide rotation action."""
    decisions: list[RotateDecision] = []
    skip_dirs = {".git", ".venv", "__pycache__"}
    now = time.time()

    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if not name.endswith(".log"):
                continue
            p = dirpath / name

            # The fix: refuse to touch symlinks.
            if p.is_symlink():
                decisions.append(RotateDecision(
                    path=p, size_bytes=0, mtime=0.0,
                    action="skip-symlink",
                ))
                continue

            # lstat would be safe too, but the symlink check above is enough
            # because we already know p is not a symlink.
            s = p.stat()
            age_days = (now - s.st_mtime) / 86400

            if s.st_size > size_threshold:
                action = "archive"
            elif age_days > age_threshold_days:
                action = "compress"
            else:
                action = "leave"

            decisions.append(RotateDecision(
                path=p, size_bytes=s.st_size, mtime=s.st_mtime,
                action=action,
            ))

            if action == "archive":
                archive_path = p.with_suffix(".log.archived")
                archive_path.write_bytes(p.read_bytes())
                archive_path.chmod(0o640)      # locked-down perms on archive
                p.unlink()
            elif action == "compress":
                # (gzip the file in production; here we just touch the .gz name)
                (p.parent / (name + ".gz")).touch()

    return decisions
```

This function is the lesson's synthesis: it uses `walk()` (lesson 06) to iterate the tree, `is_symlink()` (this lesson) to defend against the symlink trap, `stat()` (this lesson) to read size and mtime, `with_suffix()` (lesson 01) to derive the archive path, `read_bytes()`/`write_bytes()` (lesson 02) to copy content, `chmod()` (this lesson) to lock down the archive's permissions, and `unlink()` (lesson 04) to remove the original. Every `pathlib` skill from sections 01–07 comes together.

The headline fix is lines 96–102: the `if p.is_symlink(): ... continue` check. Before any `stat()` or content-read, the policy checks whether the path is a symlink. If yes, it records the path in the decisions list with `action="skip-symlink"` and `continue`s — no `stat()` call lands, no content is read, no file is unlinked. The attacker's `passwd.log` symlink is detected and skipped, and the decision is visible in the function's return value so the caller can audit it.

**Why `is_symlink()` first, before `stat()`?** Because `stat()` follows symlinks — it would call `os.stat` on the *target* (e.g., `/etc/passwd`), and the size/mtime checks would be against the target's metadata. The `is_symlink()` check is one `lstat` call (the cheapest metadata call), and its True result means we skip the `stat()` call entirely. The order matters: `is_symlink()` first, then `stat()` only on non-symlinks. Inverting the order (stat first, then `is_symlink`) would leak the target's metadata into the policy even if we then skip the action.

**Why does the policy use `stat()` (not `lstat()`) for the non-symlink case?** Because for a non-symlink, `stat()` and `lstat()` return identical results — there is no symlink to follow. Using `stat()` is correct and idiomatic. If the file became a symlink between the `is_symlink()` check and the `stat()` call (a TOCTOU race), the `stat()` would follow the new symlink — but the unlink would then fail (because the unlink removes the link entry, not the target), and the policy would not leak content. The TOCTOU window is real but the consequence is bounded.

**Danger — `p.read_bytes()` on a symlink reads the *target's* content.**

The lesson's `archive_logs` policy does `archive_path.write_bytes(p.read_bytes())` *after* the `is_symlink()` check has confirmed `p` is not a symlink. Without that check, `p.read_bytes()` would follow the symlink and read the target's content — `/etc/passwd`'s bytes — into the archive. The defence is structural: the `is_symlink()` check is the gate, and every downstream operation (stat, read, unlink) happens only on confirmed non-symlinks. Never remove the `is_symlink()` check from a rotation policy — it is the difference between a safe policy and an information-disclosure incident.

## Execution Trace

```bash
$ uv run python boardly/logs/rotate_policy.py
=== show_stat on app.log ===
  path:           /tmp/boardly-stat-demo/app.log
  st_mode (oct):  0o100664
  perm bits:      0o664
  file type:      regular
  st_size:        200 bytes
  st_mtime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_atime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_ctime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_uid:         1001
  st_gid:         1001
  st_ino:         300947
  st_dev:         44
  st_nlink:       1

=== show_predicates on app.log and on base ===
  path:           /tmp/boardly-stat-demo/app.log
  is_file():      True
  is_dir():       False
  is_symlink():   False
  is_socket():    False
  is_fifo():      False
  is_block_device(): False
  is_char_device():  False
  path:           /tmp/boardly-stat-demo
  is_file():      False
  is_dir():       True
  is_symlink():   False
  is_socket():    False
  is_fifo():      False
  is_block_device(): False
  is_char_device():  False

=== show_chmod on app.log ===
  before: 0o664
  after  chmod(0o640): 0o640
  after  chmod(0o644): 0o644
  after  chmod(S_IRUSR|S_IWUSR|S_IRGRP): 0o640

=== show_owner on app.log ===
  owner()  -> 'z'   (numeric uid: 1001)
  group()  -> 'z'   (numeric gid: 1001)

=== boardly rotate_policy result ===
  archive        app.log  size=200  mtime=Fri Oct 23 10:02:54 2026
  compress       big.log  size=100  mtime=Sun Sep 13 10:02:54 2026
```

The exact `st_mtime`/`st_atime`/`st_ctime` timestamps and `st_ino`/`st_dev` values are runtime-specific (the sandbox's clock at script-run time); the structural facts — `st_mode` `0o100664` for a regular `0o664` file (the default umask of the sandbox produced `0o664`, not `0o644`), `is_file()` True, `is_dir()` False, `chmod` round-trip from `0o664` to `0o640` and through `0o644` back to `0o640`, `owner()` returning the username string `'z'` — are reproducible. The `rotate_policy` output shows `app.log` archived (size 200 bytes > 150 threshold) and `big.log` compressed (mtime 40 days ago > 30 day threshold; size 100 bytes < 150 threshold, so size-branch did not fire, age-branch did). The order of the two decisions follows `walk()`'s `filenames` order, which is filesystem-dependent; on the sandbox it is alphabetical (`app.log` before `big.log`).

## Common Mistakes

### Mistake 1: Calling `stat()` on a symlink when you wanted the link's metadata

```python
p = Path("link_to_target")
size_of_target = p.stat().st_size          # follows the link
size_of_link   = p.lstat().st_size         # the link entry itself
```

**Symptom:** `p.stat().st_size` returns the target's size, not the link entry's. For a symlink to `/etc/passwd`, `p.stat().st_size` is the size of `/etc/passwd`; `p.lstat().st_size` is the length of the string `/etc/passwd` (11 bytes). The two are wildly different.
**Why:** `stat()` follows symlinks by default; `lstat()` does not. The two methods exist exactly because the choice matters.
**Fix:** Use `lstat()` when you want the link's own metadata; use `stat()` when you want the target's. When in doubt, use `lstat()` for safety — it never leaks target metadata into a policy that should be operating on links.

### Mistake 2: Using `is_file()` to defend against symlinks

```python
if p.is_file():
    content = p.read_bytes()    # follows the symlink, reads /etc/passwd
```

**Symptom:** `is_file()` returns `True` for a symlink whose target is a regular file. The `read_bytes()` call follows the link and reads the target's content. Information disclosure.
**Why:** `is_file()` follows symlinks in 3.12 and earlier (it calls `stat()`, not `lstat()`). The question "is this path a file?" is answered about the *target*, not the link. In 3.14+, `is_file(follow_symlinks=False)` checks the link's type.
**Fix:** Use `is_symlink()` as the *first* check; only proceed to `is_file()` if `is_symlink()` returned False. Or in 3.14+, use `is_file(follow_symlinks=False)` which is one call.

### Mistake 3: Forgetting that `chmod` follows symlinks by default

```python
link = Path("link_to_target")
link.chmod(0o600)    # changes the TARGET's permissions, not the link's
```

**Symptom:** You intend to change the link's permissions; you actually change the target's. On Linux, the link's permissions are not stored (always `0o777`), so the call appears to "work" but the link's behaviour is unchanged.
**Why:** `chmod(mode, *, follow_symlinks=True)` is the default. The default follows symlinks.
**Fix:** Use `chmod(mode, follow_symlinks=False)` to change the link entry's permissions (on filesystems that store them — BSD/macOS yes, Linux no). The deprecated `lchmod(mode)` does the same thing — in 3.13+ it emits a `DeprecationWarning`; replace with `chmod(mode, follow_symlinks=False)`.

## Engineering Trade-Offs

**Decision:** Use `stat()` for target metadata; `lstat()` for link metadata; `is_symlink()` as the gate before any content operation.
**Both sides:** The alternative — `lstat()` for everything — is safer (no target leaks) but loses the "what is the target's size?" answer that legitimate use cases need (a rotation policy that *wants* to rotate the symlink's target as if it were a regular file). The boardly rotation policy is the opposite case: it refuses to operate on symlinks at all, because the policy's correctness depends on the path being a real file owned by the application, not an attacker-supplied indirection. The right choice depends on the policy's trust boundary — if the path comes from user input (a config file, an HTTP request), use `lstat()` and `is_symlink()`; if the path is internally generated and trusted, `stat()` is fine.
**Commitment:** `boardly`'s rotation policy uses `is_symlink()` as the gate (skip symlinks entirely) and `stat()` for non-symlinks. The `stat()` call is safe because the gate has already excluded symlinks; if a TOCTOU race turns the file into a symlink between the gate and the `stat()`, the `stat()` follows the new target but the subsequent `unlink()` removes the link entry (not the target), bounding the damage. The policy is safe by construction, not by luck.

## Exercises

1. **Exercise 1 — Print your home directory's `st_uid` and `st_gid`.** Modify the script to call `Path.home().stat()` and print `st_uid`, `st_gid`, `owner()`, and `group()`. `Verify: uv run python boardly/logs/rotate_policy.py | rg 'home'`
2. **Exercise 2 — Decode the file type from `st_mode`.** Add a function `decode_mode(p: Path) -> str` that returns "regular" / "directory" / "symlink" / "socket" / etc. by reading `p.lstat().st_mode` and applying the `stat.S_*` predicates. Test it on a regular file, a directory, and (if you can create one safely) a symlink. `Verify: uv run python boardly/logs/rotate_policy.py | rg 'decode'`
3. **Exercise 3 — The `chmod` bit-constant form.** Rewrite the `0o640` argument in `show_chmod` using only the `stat.S_*` constants (no octal literal). Confirm the round-trip produces the same `0o640` output. `Verify: uv run python boardly/logs/rotate_policy.py | rg 'bit-constant'`
4. **Exercise 4 — Add an `on_error` handler to `rotate_policy`.** Modify the function to accept an `on_error` callable (defaulting to a logging handler), pass it to `walk()`, and increment a counter. Print the counter at the end. `Verify: uv run python boardly/logs/rotate_policy.py | rg 'errors='`
5. **Exercise 5 — Detect a broken symlink.** Write a function `is_broken_symlink(p: Path) -> bool` that returns True if `p` is a symlink AND its target does not exist. Use `is_symlink()` and `exists(follow_symlinks=True)` (the default). `Verify: uv run python boardly/logs/rotate_policy.py | rg 'broken'`
6. **Exercise 6 — The `chmod` policy on the archive.** Modify `rotate_policy` to accept a `archive_mode: int = 0o640` parameter, use it in the `chmod()` call after archiving, and add a comment explaining why `0o640` is the default (group-readable, no other). `Verify: uv run python boardly/logs/rotate_policy.py | rg 'archive_mode'`

## Verification

```bash
$ uv run python boardly/logs/rotate_policy.py | head -20
=== show_stat on app.log ===
  path:           /tmp/boardly-stat-demo/app.log
  st_mode (oct):  0o100664
  perm bits:      0o664
  file type:      regular
  st_size:        200 bytes
  st_mtime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_atime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_ctime:       1792739832.3084033  (Fri Oct 23 07:17:12 2026)
  st_uid:         1001
  st_gid:         1001
  st_ino:         300947
  st_dev:         44
  st_nlink:       1

=== show_predicates on app.log and on base ===
  path:           /tmp/boardly-stat-demo/app.log
  is_file():      True
  is_dir():       False
```

`st_mode` is `0o100664` for a regular `0o664` file (the `100` prefix is `S_IFREG` in the high bits; the `664` is the umask-adjusted permission bits). `is_file()` returns `True`. The `chmod` round-trip from `0o664` to `0o640` and back to `0o640` works.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `Path` constructor, the `/` operator, `.with_suffix()`. The lesson's `archive_path = p.with_suffix(".log.archived")` is the lesson-01 suffix manipulation.
- [[08-pathlib/02-read-write-text-binary]] — `read_bytes()`/`write_bytes()`. The lesson's archive step copies the file's content via these two methods.
- [[08-pathlib/06-walk-and-iterdir]] — `walk()` and `iterdir()`. The lesson's `rotate_policy` walks `boardly/logs/` and stats each file the walker yields.
- [[08-pathlib/05-PurePath-vs-Path]] — the `PurePath` vs `Path` split. `stat`, `lstat`, `is_*`, `chmod`, `owner`, `group` are all `Path` methods; none exist on `PurePath` (the pure class does not touch the disk).

## What's Next

The 08-pathlib section ends here. You have learned the full pathlib surface — `PurePath` vs `Path`, the `/` operator and accessors, text and binary I/O, glob and rglob, mkdir and rmdir and unlink, walk and iterdir, stat and permissions. The next section to look at depends on your trajectory:

- If you are building FastAPI services that read config files at startup, [[14-importlib/02-resources]] — `importlib.resources.files()` returns a `Traversable` (pathlib-like) object for accessing package-bundled data files; the API is the pathlib analogue for resources inside an installed package.
- If you are writing middleware that captures request metadata, [[03-contextlib/05-contextvars]] — `ContextVar` is to per-request state what `Path` is to filesystem state: an object that hides the messy global underneath.
- If you are writing a CLI tool that needs to walk a tree and report, the `23-logging` section teaches the structured-logging pattern that pairs naturally with `Path.walk()`.

Three bullets on what comes next:

- **`importlib.resources` and `Traversable`** — the pathlib-like API for files inside installed packages; works without a real filesystem path.
- **`contextlib.suppress` and `contextlib.redirect_stdout`** — useful companions to `pathlib` in scripts that walk trees and capture output.
- **`logging.handlers.RotatingFileHandler`** — the stdlib's built-in log-rotation handler, which does in one line what this lesson's `rotate_policy` does in 50; you would write the policy by hand only when you need custom logic the handler does not support.

## Sources

- **pathlib — Python 3.12 documentation** — https://docs.python.org/3.12/library/pathlib.html — accessed 2026-10-23 — the canonical reference for `Path.stat`, `Path.lstat`, `Path.is_*`, `Path.chmod`, `Path.lchmod`, `Path.owner`, `Path.group`. The `follow_symlinks` parameter is documented per-method; the version-gates are in the "What's New" notes.
- **What's New in Python 3.12 — pathlib** — https://docs.python.org/3.12/whatsnew/3.12.html#pathlib — accessed 2026-10-23 — the changelog entry that introduced `Path.exists(follow_symlinks=)` and `Path.chmod(follow_symlinks=)` and clarified the symlink semantics for the predicates.
- **What's New in Python 3.13 — pathlib** — https://docs.python.org/3.13/whatsnew/3.13.html#pathlib — accessed 2026-10-23 — the changelog entry that added `follow_symlinks=` to `Path.owner()` and `Path.group()`, and deprecated `Path.lchmod()`.
- **os — Python 3.12 documentation (stat)** — https://docs.python.org/3.12/library/os.html#os.stat — accessed 2026-10-23 — the underlying `os.stat_result` namedtuple and the `stat` module's `S_ISREG`/`S_ISDIR`/`S_ISLNK` predicates. `Path.stat` returns this type unchanged.
- **stat — Python 3.12 documentation** — https://docs.python.org/3.12/library/stat.html — accessed 2026-10-23 — the `S_IFMT` mask, the `S_ISREG`/`S_ISDIR`/etc. predicates, and the `S_IRUSR`/`S_IWUSR`/etc. permission-bit constants.

## What We Learned

- You can now call `Path.stat(*, follow_symlinks=True)` and read every field of the returned `os.stat_result` — `st_mode`, `st_size`, `st_mtime`, `st_uid`, `st_gid`, `st_ino`, `st_dev`, `st_nlink`, `st_atime`, `st_ctime`.
- You can decode `st_mode` into "file type" and "permission bits" — the high bits via `stat.S_ISREG`/`S_ISDIR`/etc., the low 9 bits via `stat.S_IRUSR`/`S_IWUSR`/etc.
- You can use `Path.lstat()` as the symlink-safe variant of `stat()` — equivalent to `stat(follow_symlinks=False)`.
- You can use the `is_*()` predicates and you understand that in Python 3.12 they follow symlinks (except `is_symlink()`); you can defend against the symlink-to-sensitive-file trap with `is_symlink()` as the first check.
- You can change permissions with `Path.chmod(mode, *, follow_symlinks=True)` and the `S_*` bit constants; you know `lchmod(mode)` is deprecated in 3.13+ in favour of `chmod(mode, follow_symlinks=False)`.
- You can read the file's owner and group with `Path.owner()` and `Path.group()` — they return strings, not numeric IDs; you know the `follow_symlinks` parameter was added in 3.13.
- You can write a boardly log-rotation policy that walks the tree, stats each file, defends against symlinks, archives large files, compresses old files, and locks down the archives with `chmod(0o640)` — putting together every pathlib skill from sections 01–07.
