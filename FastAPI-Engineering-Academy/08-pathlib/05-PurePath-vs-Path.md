---
title: "Lesson 05: PurePath vs Path"
aliases:
 - PurePath
 - pathlib PurePath
 - PurePosixPath
 - PureWindowsPath
 - path arithmetic without IO
 - Path is PurePath subclass
tags:
 - pathlib
 - canonical
 - python-stdlib
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
 - "[[08-pathlib/02-read-write-text-binary]]"
related_lessons:
 - "[[08-pathlib/06-walk-and-iterdir]]"
 - "[[08-pathlib/07-stat-and-permissions]]"
first_taught_in: "08-pathlib/05-PurePath-vs-Path"
---

# Lesson 05: PurePath vs Path

*How `boardly`'s log-rotation config validates a Windows path like `C:\boardly\logs\app.log` on a Linux worker that has never seen a `C:` drive — and why the type annotation should be `PurePath`, not `Path`.*

**You're at the very beginning of Section 08 — five lessons in. This is the class hierarchy lesson.**

You can join paths with `/`, read text with `read_text()`, and walk trees with `glob()`. Now we step back and look at the *two* classes inside `pathlib` and the one rule that separates them: **`PurePath` does path arithmetic; `Path` does I/O.** That single sentence is the lesson. The rest is making the sentence concrete — showing you a `PureWindowsPath` parsed on a Linux box without a single `stat()` call landing, showing you the class tree so you understand why instantiating `PosixPath` on Windows raises `NotImplementedError`, and showing you the production bug that happens when you annotate a config validator with `Path` instead of `PurePath`. Take your time. Type every example. **This is how you learn.**

#pathlib #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **State the rule** — `PurePath` is for path *string* arithmetic (no filesystem access); `Path` is the `PurePath` subclass that adds `exists()`, `stat()`, `read_text()`, `iterdir()`, `walk()`, `chmod()` and every other method that touches the disk.
2. **Read the class tree** — `PurePath` is the root; `PurePosixPath` and `PureWindowsPath` are its concrete subclasses; `Path` inherits from `PurePath`; `PosixPath` is `Path` + `PurePosixPath`; `WindowsPath` is `Path` + `PureWindowsPath`. You can predict which of the four subclasses you can instantiate on which platform.
3. **Parse a Windows path on Linux** with `PureWindowsPath("C:\\Users\\x\\app.log")` — extract `.drive`, `.root`, `.parts`, `.parent`, `.name`, `.suffix`, `.suffixes` — and explain why no `stat()` call lands.
4. **Choose the right type for a function signature** — accept `PurePath` when you only need string manipulation (a config validator, a path normaliser, a glob matcher); accept `Path` only when the function reads, writes, lists, or stats.
5. **Explain the cross-platform trap** — instantiating `PurePosixPath` or `PureWindowsPath` works on any platform; instantiating `PosixPath` only works on POSIX and `WindowsPath` only works on Windows, because the concrete `Path` subclass is selected by the running platform.
6. **Read the I/O method table** — list every method that lives on `Path` and not on `PurePath`, and explain why each one *cannot* exist on `PurePath` (every one of them calls into the OS).

## Prerequisites

Before starting, you need:

- **The `/` operator and the accessors** — [[08-pathlib/01-Path-Basics]]. This lesson uses `.parts`, `.parent`, `.name`, `.stem`, `.suffix`, `.suffixes`, `.with_suffix()`, `.with_name()`, `.joinpath()`, `.relative_to()`, `.match()` — every one of those is a `PurePath` method you already met, but here we separate them from the I/O ones.
- **`read_text()` and `write_text()`** — [[08-pathlib/02-read-write-text-binary]]. The lesson's punchline depends on you having already *seen* that those methods exist on `Path` and not on `PurePath`.
- **About 30–45 minutes of focused time.**

**The most common gap: assuming `pathlib.Path` is one type.**

It is two types in disguise. When you write `Path("a/b/c")`, what you actually get on Linux is a `PosixPath`, and on Windows a `WindowsPath` — both of which are subclasses of both `Path` *and* the corresponding pure type. The split exists so that the I/O methods (`stat`, `read_text`, `iterdir`, ...) can dispatch to the right OS call (`os.stat`, `open`, `os.listdir`, ...) while the pure methods (`parts`, `parent`, `name`, ...) dispatch to the right string-parsing rules (`/`-separated on POSIX, `\`-separated on Windows). The student who treats `Path` as a single flat type misses the reason `PureWindowsPath` works on Linux and `WindowsPath` does not — the pure class has no OS call to dispatch to.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/config/log_config.py — the bad annotation
from pathlib import Path

def validate_log_path(raw: str, base: Path) -> Path:
    """Reject paths outside the base directory; return an absolute Path."""
    p = (base / raw).resolve()
    if base not in p.parents and p != base:
        raise ValueError(f"{raw!r} escapes base {base}")
    return p
```

You ship that. A boardly cluster has a Linux worker pulling its log config from a JSON payload authored on Windows — the on-call engineer's laptop wrote `"C:\\boardly\\logs\\app.log"` into the config map because that is where the worker is supposed to *appear* to write logs from the perspective of the Windows side of the network share. The Linux worker calls `validate_log_path("C:\\boardly\\logs\\app.log", Path("/var/log/boardly"))` — and `Path` on Linux silently parses that as a single relative filename `C:boardlylogsapp.log` (the backslashes are not path separators on POSIX), joins it onto `/var/log/boardly`, resolves the result, and returns `/var/log/boardly/C:boardlylogsapp.log`. No exception, no warning — just a path that will never exist when the worker tries to write to it. The bug surfaces six hours later as a "no logs" ticket.

Worse, the test suite you wrote against this validator passes, because your tests used POSIX-shaped strings on a POSIX box. The mismatch between "the path the Windows side sent" and "the path the POSIX side parsed" was never exercised. The `Path` annotation promised a typed boundary; it delivered a silent string-mash.

The fix is two-fold. First, when the path you are parsing is *from another platform*, parse it with the `PureWindowsPath` class so the backslashes and the drive letter are interpreted correctly. Second, when the function only does string manipulation on the path — and a config validator that checks "does this stay inside the base directory" qualifies — annotate it with `PurePath`, not `Path`. A `PurePath` annotation is a contract: *this function does not touch the disk*. Callers can hand it a `PureWindowsPath` and the type checker (and the reader) sees that no `stat()` will land.

## The Code

```python
# boardly/config/pure_path_basics.py
"""PurePath is path arithmetic; Path is I/O. Show both."""
from pathlib import (
    PurePath, PurePosixPath, PureWindowsPath,
    Path, PosixPath, WindowsPath,
)
import sys


# 1. The class tree — PurePath is the root; Path subclasses it
print("PurePath.__bases__:", PurePath.__bases__)
print("PurePosixPath.__bases__:", PurePosixPath.__bases__)
print("PureWindowsPath.__bases__:", PureWindowsPath.__bases__)
print("Path.__bases__:", Path.__bases__)
print("PosixPath.__bases__:", PosixPath.__bases__)
print("WindowsPath.__bases__:", WindowsPath.__bases__)


# 2. PureWindowsPath parses a Windows path on Linux — no FS access
win = PureWindowsPath(r"C:\Users\boardly\logs\app.log.1")
print("\nwin:", win)
print("win.parts:", win.parts)
print("win.drive:", win.drive)
print("win.root:", win.root)
print("win.parent:", win.parent)
print("win.name:", win.name)
print("win.suffix:", win.suffix)
print("win.suffixes:", win.suffixes)
print("win.stem:", win.stem)
print("win.with_suffix('.txt'):", win.with_suffix(".txt"))


# 3. PurePath has no filesystem methods — prove it
io_methods = [
    "exists", "stat", "lstat", "is_file", "is_dir", "is_symlink",
    "is_socket", "is_fifo", "is_block_device", "is_char_device",
    "chmod", "lchmod", "owner", "group", "read_text", "write_text",
    "read_bytes", "write_bytes", "open", "iterdir", "glob", "rglob",
    "walk", "mkdir", "rmdir", "unlink", "rename", "replace", "touch",
]
print("\nPurePath I/O surface (should all be False):")
for m in io_methods:
    print(f"  PurePath.{m:18}: {hasattr(PurePath, m)}")


# 4. Path on Linux is PosixPath; on Windows is WindowsPath
concrete = Path("a/b/c")
print("\nPath('a/b/c') ->", type(concrete).__name__,
      "on", sys.platform)
print("issubclass(PosixPath, PurePosixPath):",
      issubclass(PosixPath, PurePosixPath))
print("issubclass(WindowsPath, PureWindowsPath):",
      issubclass(WindowsPath, PureWindowsPath))


# 5. The cross-platform rule: pure any-platform; concrete same-platform
# PureWindowsPath works on Linux (no OS call):
print("\nPureWindowsPath on Linux? OK:", PureWindowsPath("C:/x"))
# PurePosixPath works on Windows too (theoretically) — pure:
print("PurePosixPath exists on this platform:",
      issubclass(PurePosixPath, PurePath))
# WindowsPath on Linux raises NotImplementedError at construction time:
try:
    WindowsPath("C:/x")
except NotImplementedError as exc:
    print("WindowsPath on Linux -> NotImplementedError:", exc)


# 6. The right type for a config validator — PurePath, not Path
def normalise(raw: str, base: PurePath) -> PurePath:
    """Pure string arithmetic. No stat() lands. No disk touched."""
    return base / raw

base = PurePosixPath("/var/log/boardly")
print("\nnormalise('app.log', base):", normalise("app.log", base))
print("normalise('../etc/passwd', base):", normalise("../etc/passwd", base))


# 7. The boardly contract: pure on input, Path only when you need I/O
def write_log_line(target: Path, line: str) -> None:
    """Now we need the disk — Path, not PurePath."""
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

print("\nwrite_log_line signature:", write_log_line.__annotations__)
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–7: Imports — the four pure classes and the two concrete classes

```python
from pathlib import (
    PurePath, PurePosixPath, PureWindowsPath,
    Path, PosixPath, WindowsPath,
)
import sys
```

`pathlib` exports six classes you care about. The three *pure* ones — `PurePath`, `PurePosixPath`, `PureWindowsPath` — do string arithmetic only; they never call `os.stat`, `os.listdir`, `open`, or any other syscall. The three *concrete* ones — `Path`, `PosixPath`, `WindowsPath` — subclass the pure ones and *add* the I/O surface. `Path` is the abstract concrete base: on a POSIX system `Path("a")` returns a `PosixPath` instance; on a Windows system it returns a `WindowsPath` instance. `PosixPath` and `WindowsPath` are not selectable from `pathlib` on the wrong platform — you can *import* them on any platform, but constructing one on the wrong platform raises `NotImplementedError` at `__new__` time. We demonstrate that below.

**Why import all six when the docs say "use `Path`"?** Because the docs are talking about the everyday case. When you are writing a config validator that parses paths from another platform, or a library that does path string manipulation without I/O, you need to *name* the pure classes explicitly — both to construct them (`PureWindowsPath(...)`) and to annotate with them (`base: PurePath`). The import block makes the six-class surface visible; the rest of the lesson shows when to reach for each.

### Lines 9–15: The class tree — `__bases__` evidence

```python
print("PurePath.__bases__:", PurePath.__bases__)
print("PurePosixPath.__bases__:", PurePosixPath.__bases__)
print("PureWindowsPath.__bases__:", PureWindowsPath.__bases__)
print("Path.__bases__:", Path.__bases__)
print("PosixPath.__bases__:", PosixPath.__bases__)
print("WindowsPath.__bases__:", WindowsPath.__bases__)
```

When this block runs, Python imports the `pathlib` module (it is already imported by your `from pathlib import ...` line), then accesses each class's `__bases__` tuple — the direct base classes. The output reads:

- `PurePath.__bases__: (<class 'object'>,)` — pure root, no parent in `pathlib`.
- `PurePosixPath.__bases__: (<class 'pathlib.PurePath'>,)` — direct subclass of `PurePath`.
- `PureWindowsPath.__bases__: (<class 'pathlib.PurePath'>,)` — direct subclass of `PurePath`.
- `Path.__bases__: (<class 'pathlib.PurePath'>,)` — `Path` subclasses `PurePath`, not `PurePosixPath` or `PureWindowsPath`. This is the key insight: `Path` *itself* is platform-neutral; the platform-specific behaviour is bolted on by the concrete `PosixPath`/`WindowsPath` classes via a second base.
- `PosixPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PurePosixPath'>)` — multiple inheritance: `Path` (I/O surface, platform-neutral interface) + `PurePosixPath` (POSIX string parsing rules).
- `WindowsPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PureWindowsPath'>)` — same shape with `PureWindowsPath`.

**Why multiple inheritance and not just `PosixPath(Path)`?** Because the string-parsing rules (`/` is the separator on POSIX, `\` is the separator on Windows, drive letters exist on Windows) live on the pure classes. `Path` itself defines the I/O methods (`stat`, `read_text`, `iterdir`, ...) and dispatches them to `os.stat`, `open`, `os.listdir` — which are the same calls on every platform. By splitting the parsing rules from the I/O, the same `Path.read_text()` code path works on both platforms, with the parsing dispatch handled by the pure mixin. This is the textbook use of mixin multiple inheritance: one base for behaviour, one base for policy.

### Lines 18–29: Parsing a Windows path on Linux with `PureWindowsPath`

```python
win = PureWindowsPath(r"C:\Users\boardly\logs\app.log.1")
print("\nwin:", win)
print("win.parts:", win.parts)
print("win.drive:", win.drive)
print("win.root:", win.root)
print("win.parent:", win.parent)
print("win.name:", win.name)
print("win.suffix:", win.suffix)
print("win.suffixes:", win.suffixes)
print("win.stem:", win.stem)
print("win.with_suffix('.txt'):", win.with_suffix(".txt"))
```

This block is the lesson's headline demonstration. We construct a `PureWindowsPath` from a raw Windows string — drive letter, backslashes, multi-dot filename — on a Linux box that has no `C:` drive. Then we read every property the pure class exposes. The output reads:

- `win: C:\Users\boardly\logs\app.log.1` — the canonicalised form (backslashes preserved because this is a Windows path).
- `win.parts: ('C:\\', 'Users', 'boardly', 'logs', 'app.log.1')` — the drive *and* the root are merged into one part (`'C:\\'`) because on Windows a drive letter implies the root of that drive; subsequent parts are the path components split on `\`.
- `win.drive: 'C:'` and `win.root: '\\'` — the drive and root are exposed separately too, but their combination lives as a single entry in `parts`.
- `win.parent: C:\Users\boardly\logs` — the parent directory, parsed by dropping the last component.
- `win.name: app.log.1`, `win.stem: app.log`, `win.suffix: .1`, `win.suffixes: ['.log', '.1']` — the multi-dot filename is split with the rule "the last dot starts the suffix; the stem is everything before it; `suffixes` is the list of all dot-led suffixes". So `app.log.1` has stem `app.log`, suffix `.1`, and `suffixes` `[.log, .1]`.
- `win.with_suffix('.txt'): C:\Users\boardly\logs\app.log.txt` — returns a *new* `PureWindowsPath` with the *last* suffix replaced (`.1` → `.txt`); the stem `app.log` is preserved because `with_suffix` operates on the final dot-led suffix only. The original `win` is unchanged (immutable value).

**Why does this work on Linux?** Because `PureWindowsPath` never calls the OS. The constructor parses the input string by Windows rules (`\` is a separator, drive letters are recognised) into the internal tuple of parts, and every accessor (`parts`, `parent`, `name`, ...) is pure string manipulation on that tuple. There is no `os.stat` call, no `os.path.realpath` call, no `open` call. The class is a string-algebra engine that happens to know Windows rules; it could run on a machine with no filesystem at all and still produce the same output. That is the "PurePath is path arithmetic" rule made concrete.

**Why `r"C:\Users\..."` and not `"C:\Users\..."`?** The raw-string prefix (`r"..."`) prevents Python's string parser from interpreting `\U`, `\b`, `\l`, `\a` as escape sequences. `\U` is a Unicode escape (4-8 hex digits), `\b` is backspace (0x08), `\a` is bell (0x07). Without the `r` prefix, `"C:\Users\boardly\logs\app.log.1"` is silently mangled into a string with embedded control characters. The raw prefix is mandatory for any Windows path string literal — the same rule applies to POSIX paths only if you have backslashes in them, which you should not.

### Lines 32–43: Proving `PurePath` has no I/O methods

```python
io_methods = [
    "exists", "stat", "lstat", "is_file", "is_dir", "is_symlink",
    "is_socket", "is_fifo", "is_block_device", "is_char_device",
    "chmod", "lchmod", "owner", "group", "read_text", "write_text",
    "read_bytes", "write_bytes", "open", "iterdir", "glob", "rglob",
    "walk", "mkdir", "rmdir", "unlink", "rename", "replace", "touch",
]
print("\nPurePath I/O surface (should all be False):")
for m in io_methods:
    print(f"  PurePath.{m:18}: {hasattr(PurePath, m)}")
```

This block is the falsification test. We list every I/O method `Path` defines and check `hasattr(PurePath, name)` for each one. Every result is `False` — `PurePath` does not have `exists`, `stat`, `lstat`, `is_file`, `is_dir`, `is_symlink`, `is_socket`, `is_fifo`, `is_block_device`, `is_char_device`, `chmod`, `lchmod`, `owner`, `group`, `read_text`, `write_text`, `read_bytes`, `write_bytes`, `open`, `iterdir`, `glob`, `rglob`, `walk`, `mkdir`, `rmdir`, `unlink`, `rename`, `replace`, or `touch`. Every one of those methods is defined on `Path` (the I/O subclass) and inherited by `PosixPath`/`WindowsPath`.

**Why does `hasattr` matter here?** Because the absent methods are the contract. If `PurePath` had an `exists` method, calling it would have to dispatch to the OS — and the OS call would behave differently on POSIX vs Windows. By *not* defining `exists` on `PurePath`, the type system enforces the rule "you cannot ask the disk about this path" at attribute-access time. A linter or type checker sees `PurePath(...).exists()` and reports it as an error: the method does not exist on the type. The I/O surface lives on `Path`, and only `Path`. That is what "PurePath is for path arithmetic; Path is for I/O" means at the Python level.

**Warning — `hasattr(PurePath, m)` returns `False` for I/O, `True` for pure methods.**

The pure surface — `parts`, `parent`, `name`, `stem`, `suffix`, `suffixes`, `drive`, `root`, `anchor`, `as_posix()`, `as_uri()`, `with_name()`, `with_suffix()`, `joinpath()`, `relative_to()`, `is_relative_to()`, `match()`, the `/` operator, `__truediv__`, `__rtruediv__` — lives on `PurePath` and is inherited by every subclass including `Path`. So `Path("a/b").parts` works because `Path` inherits it from `PurePath`, not because `Path` defines it. When you read the `pathlib` documentation, the methods are listed once under `PurePath` and not repeated under `Path` — `Path` adds I/O, nothing else.

### Lines 46–51: `Path("a/b/c")` returns the platform's concrete subclass

```python
concrete = Path("a/b/c")
print("\nPath('a/b/c') ->", type(concrete).__name__,
      "on", sys.platform)
print("issubclass(PosixPath, PurePosixPath):",
      issubclass(PosixPath, PurePosixPath))
print("issubclass(WindowsPath, PureWindowsPath):",
      issubclass(WindowsPath, PureWindowsPath))
```

This block prints `Path('a/b/c') -> PosixPath on linux` (or `WindowsPath` on win32). The `Path.__new__` method inspects `os.name` (which is `'posix'` on Linux/macOS, `'nt'` on Windows) and dispatches to `PosixPath.__new__` or `WindowsPath.__new__`. So `Path(...)` is a factory — it returns a `PosixPath` or `WindowsPath` instance, never a bare `Path` instance. The two `issubclass` checks confirm the multiple-inheritance tree: `PosixPath` is a `PurePosixPath` (so its `parts` accessor uses POSIX rules) and `WindowsPath` is a `PureWindowsPath` (so its `parts` accessor uses Windows rules).

**Why is `Path` a factory and not just `class Path: ...`?** Because the I/O methods have to dispatch to the right OS call, and the OS call depends on the running platform. If `Path` were a single class, every I/O method would need an `if os.name == 'posix': ... else: ...` branch. By dispatching at construction time to `PosixPath` or `WindowsPath`, the I/O methods can be defined once on `Path` and call `os.stat` (which itself dispatches correctly on the running platform); the parsing methods can be inherited from `PurePosixPath` or `PureWindowsPath` without any runtime branch. The factory pattern hides the platform split from the everyday caller.

### Lines 54–62: The cross-platform trap — pure any-platform, concrete same-platform

```python
# PureWindowsPath works on Linux (no OS call):
print("\nPureWindowsPath on Linux? OK:", PureWindowsPath("C:/x"))
# PurePosixPath works on Windows too (theoretically) — pure:
print("PurePosixPath exists on this platform:",
      issubclass(PurePosixPath, PurePath))
# WindowsPath on Linux raises NotImplementedError at construction time:
try:
    WindowsPath("C:/x")
except NotImplementedError as exc:
    print("WindowsPath on Linux -> NotImplementedError:", exc)
```

This block is the rule you must memorise. Constructing `PureWindowsPath("C:/x")` on Linux succeeds and returns `PureWindowsPath('C:/x')` — no exception, no syscall. Constructing `WindowsPath("C:/x")` on Linux raises `NotImplementedError("cannot instantiate 'WindowsPath' on your system")` at `__new__` time, before the body of `__init__` ever runs. The same rule applies symmetrically: `PosixPath("a/b")` on Windows raises `NotImplementedError`.

**Why does the concrete class raise?** Because `WindowsPath` is supposed to *do I/O* — `WindowsPath("C:/x").stat()` calls `os.stat` which, on Linux, would stat a Linux path. The semantics are wrong before the call ever lands. The CPython authors chose to make the wrong-platform concrete class uninstantiable at construction time, rather than letting every I/O method silently produce nonsense. The error is loud, immediate, and unmissable. Pure classes do not have this restriction because they have no OS call to dispatch — they are string engines, and the strings parse the same on every platform.

**Danger — Code that constructs `WindowsPath` directly is not portable.**

If you write `target = WindowsPath("C:/x")` in a script that runs on a CI runner that happens to be Linux, you get `NotImplementedError` and the build fails. The safe portability pattern is:

- For pure manipulation: `PureWindowsPath("C:/x")` — works everywhere.
- For I/O on the current platform: `Path("C:/x")` — returns `PosixPath` on Linux (and parses the string as a single relative filename because `:` is not a separator on POSIX and `C:` is just a filename component) or `WindowsPath` on Windows (parses the string as drive + path).
- For I/O on a specific platform: you cannot do it from the wrong platform. `pathlib` does not support remote-stat or remote-open. Use a remote procedure call.

### Lines 65–69: The right type for a config validator — `PurePath`, not `Path`

```python
def normalise(raw: str, base: PurePath) -> PurePath:
    """Pure string arithmetic. No stat() lands. No disk touched."""
    return base / raw

base = PurePosixPath("/var/log/boardly")
print("\nnormalise('app.log', base):", normalise("app.log", base))
print("normalise('../etc/passwd', base):", normalise("../etc/passwd", base))
```

This block is the production pattern. The function `normalise` takes a raw string and a base path, joins them with the `/` operator (which calls `PurePath.__truediv__`, inherited from `PurePath` because `base` is a `PurePosixPath`), and returns the result. The annotations `base: PurePath` and `-> PurePath` are contracts: *this function does not touch the disk*. A caller can pass a `PureWindowsPath` and the join uses Windows parsing rules; a caller can pass a `PurePosixPath` and the join uses POSIX parsing rules. Either way, no `stat()` lands, no `open()` is called, no `os.listdir` runs — because `PurePath` does not have those methods.

Note the output of `normalise("../etc/passwd", base)`: it is `/var/log/boardly/../etc/passwd`, *not* `/etc/passwd`. `PurePath.__truediv__` does literal string joining — it appends the segments without resolving `..`. To collapse the `..` you would need `Path.resolve()` (an I/O method that calls `os.path.realpath`), which is precisely the I/O capability `PurePath` refuses to provide. The trade-off is intentional: `..`-resolution requires reading the filesystem (because of symlinked directories that change what `..` resolves to), and `PurePath` does not read the filesystem. The function as written is *correct* for its pure contract — it returns the joined path; whether that path's `..` collapses is a question for a later, I/O-allowed caller.

**Why `PurePath` and not `PurePosixPath` as the parameter annotation?** Because the function is platform-neutral string arithmetic. Accepting the base class `PurePath` lets the caller pass either a `PurePosixPath` or a `PureWindowsPath` and the function still type-checks. If we annotated `base: PurePosixPath`, we would forbid the caller from passing a `PureWindowsPath` even when the function would work correctly on it. The narrower type adds restriction without adding safety — the function does not call any method whose behaviour differs between POSIX and Windows rules, because all the methods it calls (`/`, `__truediv__`) are defined on the common `PurePath` parent.

**Why not `Path`?** Because annotating `base: Path` would *allow* the caller to call `base.stat()` inside the function — the type checker would let it through. The wider `Path` annotation is permission to do I/O; the narrower `PurePath` annotation forbids it. When the function does not need I/O, the narrower annotation is correct: it documents intent (this is a pure function), it constrains the caller (you may pass any pure path, concrete or pure), and it prevents the implementation from accidentally growing an I/O call later without updating the signature. This is the same logic as accepting `Iterable` instead of `list` — accept the narrowest type that the function needs.

### Lines 72–76: When you *do* need I/O — annotate with `Path`

```python
def write_log_line(target: Path, line: str) -> None:
    """Now we need the disk — Path, not PurePath."""
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

print("\nwrite_log_line signature:", write_log_line.__annotations__)
```

The contrast. `write_log_line` *does* need the disk — it calls `target.open(...)`, which is a `Path` method (defined on `Path`, inherited by `PosixPath`/`WindowsPath`, *not* present on `PurePath`). The annotation `target: Path` is the right contract: this function touches the disk; pass a concrete path. A caller who passes a `PurePosixPath` would get a type-checker error (`PurePosixPath` is not a `Path`; `Path` requires I/O capability), which is the *correct* error — you cannot open a file on a pure path. The function signature carries the I/O requirement explicitly.

**Why `Path` and not `PosixPath`?** Because `Path` is the platform-neutral I/O annotation. On a POSIX system, `Path("a")` returns `PosixPath`; on Windows, `WindowsPath`. Annotating with `Path` lets the function work on both platforms without rewriting the signature. Annotating with `PosixPath` would forbid the function from running on Windows (the caller could not construct a `PosixPath` there). Use `Path` for I/O annotations unless you have a specific reason to constrain the platform.

## Execution Trace

```bash
$ uv run python boardly/config/pure_path_basics.py
PurePath.__bases__: (<class 'object'>,)
PurePosixPath.__bases__: (<class 'pathlib.PurePath'>,)
PureWindowsPath.__bases__: (<class 'pathlib.PurePath'>,)
Path.__bases__: (<class 'pathlib.PurePath'>,)
PosixPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PurePosixPath'>)
WindowsPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PureWindowsPath'>)

win: C:\Users\boardly\logs\app.log.1
win.parts: ('C:\\', 'Users', 'boardly', 'logs', 'app.log.1')
win.drive: C:
win.root: \
win.parent: C:\Users\boardly\logs
win.name: app.log.1
win.suffix: .1
win.suffixes: ['.log', '.1']
win.stem: app.log
win.with_suffix('.txt'): C:\Users\boardly\logs\app.log.txt

PurePath I/O surface (should all be False):
  PurePath.exists             : False
  PurePath.stat               : False
  PurePath.lstat              : False
  PurePath.is_file            : False
  PurePath.is_dir             : False
  PurePath.is_symlink         : False
  PurePath.is_socket          : False
  PurePath.is_fifo            : False
  PurePath.is_block_device    : False
  PurePath.is_char_device     : False
  PurePath.chmod              : False
  PurePath.lchmod             : False
  PurePath.owner              : False
  PurePath.group              : False
  PurePath.read_text          : False
  PurePath.write_text         : False
  PurePath.read_bytes         : False
  PurePath.write_bytes        : False
  PurePath.open               : False
  PurePath.iterdir            : False
  PurePath.glob               : False
  PurePath.rglob              : False
  PurePath.walk               : False
  PurePath.mkdir              : False
  PurePath.rmdir              : False
  PurePath.unlink             : False
  PurePath.rename             : False
  PurePath.replace            : False
  PurePath.touch              : False

Path('a/b/c') -> PosixPath on linux
issubclass(PosixPath, PurePosixPath): True
issubclass(WindowsPath, PureWindowsPath): True

PureWindowsPath on Linux? OK: C:\x
PurePosixPath exists on this platform: True
WindowsPath on Linux -> NotImplementedError: cannot instantiate 'WindowsPath' on your system

normalise('app.log', base): /var/log/boardly/app.log
normalise('../etc/passwd', base): /var/log/boardly/../etc/passwd

write_log_line signature: {'target': <class 'pathlib.Path'>, 'line': <class 'str'>, 'return': None}
```

## Common Mistakes

### Mistake 1: Calling `stat()` on a `PurePath`

```python
from pathlib import PurePosixPath
p = PurePosixPath("/var/log/boardly/app.log")
size = p.stat().st_size   # AttributeError
```

**Symptom:** `AttributeError: 'PurePosixPath' object has no attribute 'stat'`
**Why:** `PurePath` (and its subclasses `PurePosixPath`/`PureWindowsPath`) do not define any I/O methods. `stat` lives on `Path`, not on `PurePath`. The class hierarchy enforces the split at attribute-access time.
**Fix:** Use `Path` when you need `stat()`. If you only need the path's string form (its `.parts`, `.parent`, `.name`, ...), `PurePath` is the right type and `stat()` is the wrong call.

### Mistake 2: Constructing `WindowsPath` on Linux (or `PosixPath` on Windows)

```python
from pathlib import WindowsPath
# Running on Linux:
p = WindowsPath("C:/Users/boardly/app.log")   # NotImplementedError
```

**Symptom:** `NotImplementedError: cannot instantiate 'WindowsPath' on your system`
**Why:** The concrete `Path` subclasses (`PosixPath`, `WindowsPath`) dispatch I/O methods to the OS, and the OS calls are platform-specific. CPython refuses to construct the wrong-platform concrete class because the I/O would silently produce nonsense. Pure classes (`PurePosixPath`, `PureWindowsPath`) do not have this restriction because they have no I/O methods.
**Fix:** For pure string manipulation across platforms, use `PureWindowsPath` or `PurePosixPath`. For I/O on the current platform, use `Path(...)` and let the factory return the right subclass.

### Mistake 3: Annotating a pure function with `Path`

```python
from pathlib import Path

def join_under(raw: str, base: Path) -> Path:
    return base / raw   # only string arithmetic — no I/O needed
```

**Symptom:** No runtime symptom — the code runs. But the type checker permits any future contributor to add `base.stat()` inside the function body without a warning, because the annotation says I/O is allowed.
**Why:** The annotation `base: Path` is permission to do I/O. The function does not need that permission; it only does string arithmetic. The wider annotation is over-permissive.
**Fix:** Annotate with the narrowest type the function needs. For pure string arithmetic: `base: PurePath`. For I/O: `base: Path`. The narrow annotation documents intent and constrains future growth.

## Engineering Trade-Offs

**Decision:** Annotate pure-string-arithmetic functions with `PurePath` and I/O functions with `Path`.
**Both sides:** The alternative — annotate everything with `Path` — is simpler to teach (one type to remember) and easier for callers (every concrete path is a `Path`). The cost is that the type system no longer tells you whether a function touches the disk. In a codebase that grows over years, that distinction is worth preserving — a `PurePath`-annotated function is one you can call from a thread that has no filesystem access, from a config validator that runs at import time, from a linter that runs in a sandbox. A `Path`-annotated function can be all of those things too, but the type does not promise it.
**Commitment:** `boardly`'s config layer annotates with `PurePath`; its I/O layer (the `write_log_line` and `read_log_lines` functions in `boardly/logs/`) annotates with `Path`. The split is enforced by the import boundary: the config layer does not import `Path` at all, only `PurePath` and its subclasses; the I/O layer imports `Path` and accepts `PurePath` arguments only via explicit `Path(...)` construction at the call site. A contributor who adds an I/O call to the config layer has to add the `Path` import — a small but visible signal that the boundary has been crossed.

## Exercises

1. **Exercise 1 — Print the parts of a Windows path.** Modify the script to parse `r"D:\boardly\data\2026-10-23.json.gz"` with `PureWindowsPath` and print `parts`, `drive`, `name`, `stem`, `suffixes`. `Verify: uv run python boardly/config/pure_path_basics.py | rg 'D:'`
2. **Exercise 2 — Cross-platform matching.** Add a function `escape_check(raw: str, base: PurePath) -> bool` that returns `False` if joining `raw` onto `base` produces a path outside `base` (i.e., if any component of `raw` is `..` such that the result's `.parents` does not contain `base`). Test it with both `PurePosixPath("/var/log/boardly")` and `PureWindowsPath("C:\\boardly\\logs")` as the base. `Verify: uv run python boardly/config/pure_path_basics.py | rg 'escape'`
3. **Exercise 3 — The pure path join across platforms.** Write a function `cross_join(raw: str, posix_base: PurePosixPath, win_base: PureWindowsPath) -> tuple[PurePath, PurePath]` that joins `raw` onto each base and returns both results. Show that the same `raw = "sub/app.log"` produces `posix/sub/app.log` and `win\\sub\\app.log` — the separator follows the pure class's rules, not the input string's. `Verify: uv run python boardly/config/pure_path_basics.py | rg 'cross_join'`
4. **Exercise 4 — Add a `to_concrete` bridge.** Write a function `to_concrete(p: PurePath) -> Path` that returns `Path(str(p))` if `p` is a `PurePosixPath` on a POSIX system or a `PureWindowsPath` on a Windows system, and raises `ValueError` otherwise (because the wrong-platform concrete class would `NotImplementedError`). This is the bridge from pure path arithmetic back to I/O. `Verify: uv run python boardly/config/pure_path_basics.py | rg 'to_concrete'`

## Verification

```bash
$ uv run python boardly/config/pure_path_basics.py | head -20
PurePath.__bases__: (<class 'object'>,)
PurePosixPath.__bases__: (<class 'pathlib.PurePath'>,)
PureWindowsPath.__bases__: (<class 'pathlib.PurePath'>,)
Path.__bases__: (<class 'pathlib.PurePath'>,)
PosixPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PurePosixPath'>)
WindowsPath.__bases__: (<class 'pathlib.Path'>, <class 'pathlib.PureWindowsPath'>)

win: C:\Users\boardly\logs\app.log.1
win.parts: ('C:\\', 'Users', 'boardly', 'logs', 'app.log.1')
win.drive: C:
win.root: \
win.parent: C:\Users\boardly\logs
win.name: app.log.1
win.suffix: .1
```

The `__bases__` block matches the lesson's class tree. `PureWindowsPath` parses on Linux. Every `hasattr(PurePath, m)` is `False`. `Path('a/b/c')` returns `PosixPath` on the Linux sandbox.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `/` operator, `.parts`, `.parent`, `.name`, `.suffix`, `.stem`, `.suffixes`, `.with_suffix()`, `.with_name()`, `.joinpath()`, `.relative_to()`, `.match()`. All of those are `PurePath` methods inherited by `Path`; this lesson separated them from the I/O surface.
- [[08-pathlib/02-read-write-text-binary]] — `.read_text(encoding=...)`, `.write_text(...)`, `.open(mode=...)`. All of those are `Path` methods; this lesson showed that they are *not* present on `PurePath`.

## What's Next

[[08-pathlib/06-walk-and-iterdir]] — the I/O surface lesson for directory traversal. Now that you know `PurePath` is for arithmetic and `Path` is for I/O, the next three lessons drill into the I/O surface itself. Lesson 06 covers the three traversal methods:

- `Path.iterdir()` — the non-recursive immediate-children iterator (yields `Path` objects, lazy).
- `Path.walk(top_down=True, on_error=None, follow_symlinks=False)` — the 3.12+ recursive walker yielding `(dirpath, dirnames, filenames)` tuples, the modern `os.walk` replacement.
- `Path.rglob("*")` — the recursive glob, pre-3.12's only recursive option, still useful when you do not need to prune mid-walk.

We will walk a real `boardly/logs/` tree, prune `.git` and `__pycache__` mid-walk by mutating `dirnames` in place, and compare `walk`'s tuple shape to `iterdir`'s flat shape.

## Sources

- **pathlib — Python 3.12 documentation** — https://docs.python.org/3.12/library/pathlib.html — accessed 2026-10-23 — the canonical reference for the `PurePath`/`Path` class tree, the `PurePosixPath`/`PureWindowsPath` subclasses, and the I/O method table. The pure-vs-concrete split is documented under "Pure paths" and "Concrete paths" sections.
- **PEP 428 — The pathlib module** — https://peps.python.org/pep-0428/ — accessed 2026-10-23 — the original PEP, which explains the *design* rationale for splitting pure and concrete classes: "Pure paths ... don't access the filesystem ... Concrete paths ... are a subclass of pure paths and provide various I/O operations."

## What We Learned

- You can now state the rule that separates `PurePath` from `Path`: pure does string arithmetic, concrete does I/O, and the split is enforced by the class hierarchy at attribute-access time.
- You can read the `__bases__` tree and predict which classes are constructible on which platform: pure classes work everywhere; concrete classes only work on their own platform.
- You can parse a Windows path on Linux with `PureWindowsPath` and read its `.parts`, `.drive`, `.root`, `.name`, `.stem`, `.suffix`, `.suffixes` without any syscall landing.
- You can choose the right type annotation for a function: `PurePath` when only string arithmetic is needed; `Path` when I/O is needed. The narrower type is a contract.
- You can explain the `WindowsPath` on Linux `NotImplementedError` — concrete classes refuse to construct on the wrong platform because their I/O methods would silently produce nonsense.
- You can write a boardly config validator that accepts a pure path, does string arithmetic on it, and never touches the disk — even when the input string is from a different platform.
