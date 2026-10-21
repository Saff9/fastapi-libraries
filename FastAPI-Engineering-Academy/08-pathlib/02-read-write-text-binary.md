---
title: "Lesson 02: read & write text and binary"
aliases:
 - Path.read_text
 - Path.read_bytes
 - Path.write_text
 - Path.write_bytes
 - Path.open
 - never call open() directly
tags:
 - pathlib
 - python-stdlib
 - io
status: complete
course_level: intermediate
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites:
 - "[[08-pathlib/01-Path-Basics]]"
related_lessons:
 - "[[08-pathlib/03-glob-and-rglob]]"
 - "[[08-pathlib/04-mkdir-rmdir-unlink]]"
---

# Lesson 02: read & write text and binary

*Why `boardly`'s `projects_path.write_text(json.dumps(data), encoding="utf-8")` is one line, and why the `encoding=` argument is the difference between a deployable service and a `UnicodeDecodeError` filed as a bug six months later.*

**You're at the very beginning of Section 08, lesson 02.**

You have written `with open(path, "r") as f: data = f.read()` and shipped it. On your Linux laptop it worked. On the staging server it worked. In the customer's on-prem install it crashed with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 1234: character maps to <undefined>`. The bug is not in your code; the bug is in the *default* — Python's `open()` on Windows uses the locale codepage (`cp1252` in US/Western-Europe, `cp932` in Japan, `cp936` in China) unless you tell it otherwise, and your file was UTF-8. The `pathlib.Path` I/O methods are the stdlib's fix: `Path.read_text(encoding="utf-8")` is shorter, safer, and self-documenting, and the `encoding=` argument stops being optional the moment you care about a second operating system. Take your time. Type every example. **This is how you learn.**

#pathlib #io

## Learning Objectives

By the end of this lesson you will be able to:

1. **Read a text file** with `Path.read_text(encoding=None, errors=None)` — explain that `encoding=None` means "use `locale.getpreferredencoding(False)`", which is UTF-8 on most Linux/macOS systems and the locale codepage on Windows, and that you should *always* pass `encoding="utf-8"` explicitly.
2. **Read a binary file** with `Path.read_bytes()` — explain that there is no `encoding=` argument because bytes are not characters, and that this is the right call for any file whose contents you will not display as text (PNG, pickled data, protobuf).
3. **Write text** with `Path.write_text(data, encoding=None, errors=None, newline=None)` — explain that the `newline=` parameter (added in 3.10) controls universal-newline translation and is the difference between a CSV that Excel opens correctly and one that arrives as a single line.
4. **Write bytes** with `Path.write_bytes(data)` — explain that this is the binary equivalent of `write_text`, takes a `bytes` (not `str`), and is the right call for writing structured data that you will `read_bytes` back later.
5. **Open a path** with `Path.open(mode="r", buffering=-1, encoding=None, errors=None, newline=None)` as a context manager — explain that this is the streaming form for files too large to read into memory, and that it composes with `with` because it returns a file object.

## Prerequisites

Before starting, you need:

- **Path basics** — [[08-pathlib/01-Path-Basics]]. This lesson writes `Path(...)` and uses the accessors; you need to be comfortable constructing a `Path` and reading its properties.
- **About 30–45 minutes of focused time.**

**The most common gap: calling `open()` directly in new code.**

The single biggest mistake students make in this lesson is writing `with open(path, "r") as f: ...` in new code. It works. It is not wrong. It is just *obsolete* — `path.open()` is the modern form, it returns the same file object, and it is shorter because the path is already a `Path`. The deeper mistake is forgetting `encoding=`: `open(path, "r")` and `path.read_text()` both default to `encoding=None`, which means "use the locale encoding", which is UTF-8 on Linux/macOS and the locale codepage on Windows. The Windows default is the bug. The fix is to *always* pass `encoding="utf-8"` when the file contains text — and `path.read_text(encoding="utf-8")` is one call shorter than the `with open(...)` form, which is the second reason to prefer the pathlib spelling.

## The Problem

Here is the bug. Read it slowly.

```python
# boardly/paths/bad_io.py — the bad old days
def load_projects(path):
    # On the dev's Linux laptop: works (locale is UTF-8)
    # On the customer's Windows server: UnicodeDecodeError
    with open(path, "r") as f:
        return f.read()

def save_projects(path, text):
    # Same bug, write side: 'charmap' codec can't encode character
    # because the customer's locale is cp1252 and the JSON has é
    with open(path, "w") as f:
        f.write(text)

def save_snapshot(path, raw_bytes):
    # This one is fine — binary mode ignores encoding
    with open(path, "wb") as f:
        f.write(raw_bytes)
```

The first two functions work on Linux because the default encoding on a Linux terminal is UTF-8 — Python calls `locale.getpreferredencoding(False)`, which on a typical Linux box returns `UTF-8`. On a Windows server, the same call returns `cp1252` (US/Western-Europe), `cp932` (Japan), or another locale codepage. A UTF-8 file read with `cp1252` raises `UnicodeDecodeError` on the first byte that does not map cleanly; a UTF-8 string written with `cp1252` raises `UnicodeEncodeError` on the same kind of byte. The bug is silent on Linux and loud on Windows — which is why it always ships to the customer before anyone notices.

The third function is fine because binary mode (`"wb"`) does not decode or encode — it writes raw bytes. The bug is *only* in the text path, and the fix is to pass `encoding="utf-8"` explicitly. The `pathlib.Path` I/O methods make that easier: `path.read_text(encoding="utf-8")` is one call, the `encoding=` argument is right there in the call site, and there is no `with open(...)` boilerplate to forget the `encoding=` in. For files too large to read into memory, `path.open(mode="r", encoding="utf-8")` is the streaming form, and it composes with `with` because it returns a file object.

The `pathlib` I/O methods are the standard-library answer to "I have a `Path`, I want to read or write a file". `Path.read_text(encoding="utf-8")` reads the whole file as a string. `Path.read_bytes()` reads the whole file as `bytes`. `Path.write_text(data, encoding="utf-8")` writes a string to the file, overwriting any previous content. `Path.write_bytes(data)` writes raw bytes. `Path.open(mode="r", encoding="utf-8")` is the streaming form for files too large to fit in memory. The methods compose with the `Path` you constructed in lesson 01 — you do not pass a `str`, you call a method on the `Path` you already have. There is no `open()` call to forget `encoding=` in; the `encoding=` argument is on the same line as the path it applies to.

## The Code

```python
# boardly/paths/read_write.py
"""Pathlib text and binary I/O: read_text, read_bytes, write_text, write_bytes, open."""
from pathlib import Path
import tempfile
import sys

# 0. Build a tmpdir that stands in for the boardly deployment's data dir
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    data_dir = root / "boardly" / "data"
    data_dir.mkdir(parents=True)
    projects_path = data_dir / "projects.json"

    # 1. write_text — write a JSON blob (the encoding= arg is mandatory)
    projects_path.write_text(
        '{"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}',
        encoding="utf-8",
    )
    print("write_text ok ->", projects_path)

    # 2. read_text — read it back as a string
    text = projects_path.read_text(encoding="utf-8")
    print("read_text   ->", text)

    # 3. read_bytes — read it as raw bytes (the encoding layer is yours)
    raw = projects_path.read_bytes()
    print("read_bytes  ->", raw)

    # 4. write_bytes — write binary directly (no encoding step)
    bin_path = data_dir / "snapshot.bin"
    bin_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
    print("write_bytes ok ->", bin_path)
    print("read_bytes  ->", bin_path.read_bytes())

    # 5. Path.open() as a context manager — streaming large files
    big_log = data_dir / "audit.log"
    with big_log.open("w", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(f"audit event {i}\n")
    with big_log.open("r", encoding="utf-8") as fh:
        for line in fh:
            print("  log line:", line.rstrip())

    # 6. The Windows cp1252 gotcha, simulated on POSIX
    #    On Windows, open("r") without encoding= uses the locale codepage
    #    (cp1252 in US/Western-Europe), which mangles non-ASCII bytes.
    emoji_path = data_dir / "unicode.txt"
    emoji_path.write_text("ticket: café α\n", encoding="utf-8")
    # Reading without encoding= works on Linux (utf-8 locale) but breaks on Windows
    print("no encoding (POSIX):", repr(emoji_path.read_text()))
    # The rule: always pass encoding= explicitly so behaviour is cross-platform
    print("with encoding=utf-8:", repr(emoji_path.read_text(encoding="utf-8")))

    # 7. write_text with newline= (3.10+) — universal newline translation
    csv_path = data_dir / "export.csv"
    csv_path.write_text("id,name\r\n1,alpha\r\n", encoding="utf-8", newline="")
    print("newline='' bytes:", csv_path.read_bytes())

    # 8. The rule, side by side
    print("---")
    print("Python:", sys.version.split()[0])
    print("platform.open_text default encoding:", emoji_path.read_text(encoding="utf-8")[:8])
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–11: Setup — the tmpdir as a stand-in for the deployment's data dir

```python
from pathlib import Path
import tempfile
import sys

# 0. Build a tmpdir that stands in for the boardly deployment's data dir
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    data_dir = root / "boardly" / "data"
    data_dir.mkdir(parents=True)
    projects_path = data_dir / "projects.json"
```

The imports are minimal: `Path` from `pathlib`, `TemporaryDirectory` from `tempfile` (so the demo does not pollute the repo), and `sys` (so we can print the Python version). The `with tempfile.TemporaryDirectory() as td:` line creates a fresh, empty directory and removes it on `__exit__` — the demo writes files into it, and the directory vanishes when the `with` block exits. In a real `boardly` deployment, `td` would be the deployment's persistent data directory (e.g. `/var/lib/boardly`), and you would not use a tmpdir; the tmpdir is here so the demo is reproducible across machines.

`root = Path(td)` wraps the tmpdir string in a `Path` — from this point on, every path operation uses `/` and the `Path` accessors. `data_dir = root / "boardly" / "data"` builds the data directory path with the `/` operator (lesson 01). `data_dir.mkdir(parents=True)` creates the directory (lesson 04 walks `mkdir` in detail; for now, `parents=True` means `mkdir -p`). `projects_path = data_dir / "projects.json"` is the file we will read and write — it is a `Path`, not a `str`.

**Why a tmpdir and not a real `boardly/data` directory?** Because the demo must be reproducible across machines without leaving files behind. A real deployment writes to `/var/lib/boardly` (or `%APPDATA%\boardly` on Windows) and the directory persists; a demo writes to `/tmp/...` and the directory vanishes on exit. The `Path` API does not care which one it is — `Path("/var/lib/boardly").write_text(...)` and `Path("/tmp/.../boardly").write_text(...)` use the same method calls. The tmpdir is a teaching convenience, not a production pattern.

### Lines 13–19: `write_text` — the one-line text write

```python
# 1. write_text — write a JSON blob (the encoding= arg is mandatory)
projects_path.write_text(
    '{"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}',
    encoding="utf-8",
)
print("write_text ok ->", projects_path)
```

`projects_path.write_text(data, encoding="utf-8")` is the one-line equivalent of `with open(path, "w", encoding="utf-8") as f: f.write(data)`. The signature is `Path.write_text(self, data, encoding=None, errors=None, newline=None)` — `data` is a `str`, `encoding` defaults to `None` (which means "use `locale.getpreferredencoding(False)`"), `errors` defaults to `None` (which means "use the strict error handler — raise on any decode/encode error"), and `newline` (added in Python 3.10) controls how `\n` characters in `data` are translated to the file's newline bytes.

The `encoding="utf-8"` argument is the line that prevents the Windows `cp1252` gotcha. Without it, on a Windows machine whose locale is `cp1252`, the same call would attempt to encode the JSON string as `cp1252` — which works for ASCII but raises `UnicodeEncodeError` on the first non-ASCII byte (e.g. an `é` in a project name). With `encoding="utf-8"`, the bytes written are UTF-8 regardless of the locale, and the file is portable across operating systems.

Internally, `write_text` opens the file in text mode (`"w"`, with `encoding=`, `errors=`, `newline=` forwarded), writes `data`, and closes the file. The file is opened and closed on every call — `write_text` is *not* a streaming API; if you are writing 10 GB, use `path.open("w", encoding="utf-8")` and stream the writes. The `write_text` method returns the number of characters (not bytes) written, which is the same number `file.write(data)` returns; the demo ignores the return value because the JSON is small enough that the count is not interesting.

**Why does `write_text` take `data` as a positional argument and `encoding` as a keyword?** Because `data` is the only thing you always pass, and `encoding` is the thing you *should* always pass but the stdlib could not make it required without breaking backwards compatibility. The signature order (`data, encoding=None, errors=None, newline=None`) puts the positional argument first and the optional ones as keyword defaults — this is the Python convention for "required positional, optional keyword". The bug-prone default (`encoding=None` → locale encoding) was locked in by the original 3.4 pathlib design, which mirrored `open()`'s default. Changing the default to `"utf-8"` now (PEP 597 proposed it for `open()`) would break code that already runs on Linux and relies on the locale default; the fix is to teach students to *always* pass `encoding="utf-8"` explicitly, which is what this lesson does.

### Lines 21–23: `read_text` — the one-line text read

```python
# 2. read_text — read it back as a string
text = projects_path.read_text(encoding="utf-8")
print("read_text   ->", text)
```

`projects_path.read_text(encoding="utf-8")` is the one-line equivalent of `with open(path, "r", encoding="utf-8") as f: return f.read()`. The signature is `Path.read_text(self, encoding=None, errors=None)` — note there is *no* `newline=` argument because reading always does universal-newline translation: `\r\n`, `\r`, and `\n` in the file are all returned as `\n` in the string. If you need the raw bytes (with the original newlines), use `read_bytes()`.

The `encoding="utf-8"` argument is the line that prevents the Windows `cp1252` gotcha on the read side. Without it, on a Windows machine whose locale is `cp1252`, the same call would attempt to decode the file bytes as `cp1252` — which works for ASCII but raises `UnicodeDecodeError` on the first non-ASCII byte (e.g. the `é` in `café`). With `encoding="utf-8"`, the bytes are decoded as UTF-8 regardless of the locale, and the file is portable across operating systems.

Internally, `read_text` opens the file in text mode (`"r"`, with `encoding=`, `errors=` forwarded), reads the whole file into a string, and closes the file. The whole-file read is *not* a streaming API; if you are reading 10 GB, use `path.open("r", encoding="utf-8")` and iterate lines. The `read_text` method returns the string; the demo prints it.

**Why is there no `newline=` on `read_text`?** Because reading *always* does universal-newline translation — `\r\n`, `\r`, and `\n` are all normalised to `\n` in the returned string. This matches `open(...).read()`'s default behaviour (where `newline=None` does the same normalisation). If you want the raw bytes with their original newline bytes, you call `read_bytes()` and decode yourself, or you use `path.open("r", encoding="utf-8", newline="")` which disables translation. The asymmetry — `write_text` has `newline=` but `read_text` does not — is because *writing* has a choice (translate `\n` to `\r\n` for Windows consumers, or keep `\n` for POSIX consumers), but *reading* always normalises to `\n` because that is the canonical Python string form.

### Lines 25–27: `read_bytes` — the binary read

```python
# 3. read_bytes — read it as raw bytes (the encoding layer is yours)
raw = projects_path.read_bytes()
print("read_bytes  ->", raw)
```

`projects_path.read_bytes()` reads the whole file as `bytes`. There is no `encoding=` argument because bytes are not characters — the file is returned exactly as it sits on disk, no decode step. The signature is `Path.read_bytes(self)` — no arguments at all. This is the right call for any file whose contents you will not display as text: a PNG image, a pickled object, a protobuf message, a `tar` archive. For text files where you want to control the decode (e.g. read as bytes then decode with a fallback codec), `read_bytes()` plus an explicit `.decode(...)` is the explicit form.

Internally, `read_bytes` opens the file in binary mode (`"rb"`, no `encoding=`, no `errors=` — those are text-mode arguments), reads the whole file into a `bytes` object, and closes the file. The whole-file read is *not* a streaming API; if you are reading 10 GB, use `path.open("rb")` and iterate in chunks. The `read_bytes` method returns the `bytes`; the demo prints them with `repr` so the `\x89` and `\r\n` escapes are visible.

The output `b'{"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}'` shows the same JSON as `read_text` returned, but as `bytes`. The bytes are the UTF-8 encoding of the string — for ASCII characters, byte value equals code point; for non-ASCII characters, the bytes are the multi-byte UTF-8 sequence. The encoding layer is *yours* — `read_text(encoding="utf-8")` does the decode for you; `read_bytes()` gives you the raw bytes and lets you decode however you want (UTF-8, UTF-16, latin-1, a fallback chain).

**Why use `read_bytes` instead of `read_text` for text files?** When you cannot trust the encoding. A file you received from a customer might be UTF-8, latin-1, cp1252, or some mix; `read_text(encoding="utf-8")` will raise on the first non-UTF-8 byte, but `read_bytes()` gives you the raw bytes and you can decode with `errors="replace"` or `errors="ignore"` to recover. The `read_bytes` plus `bytes.decode(encoding, errors="replace")` form is the *production* pattern for files of unknown encoding — the `errors=` argument is what lets you keep going past a bad byte. The pathlib `read_text(errors="replace")` form is the *convenience* spelling for the same thing; use whichever you find more readable.

### Lines 29–32: `write_bytes` — the binary write

```python
# 4. write_bytes — write binary directly (no encoding step)
bin_path = data_dir / "snapshot.bin"
bin_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
print("write_bytes ok ->", bin_path)
print("read_bytes  ->", bin_path.read_bytes())
```

`bin_path.write_bytes(data)` writes raw `bytes` to the file, overwriting any previous content. The signature is `Path.write_bytes(self, data)` — `data` is a `bytes` (or `bytearray` or `memoryview`), no `encoding=` argument because bytes are not characters. This is the right call for writing structured binary data: a PNG header (as the demo shows — `b"\x89PNG\r\n\x1a\n..."` is the PNG magic number), a pickled object, a protobuf message.

Internally, `write_bytes` opens the file in binary mode (`"wb"`, no `encoding=`, no `errors=`), writes `data`, and closes the file. The whole-file write is *not* a streaming API; if you are writing 10 GB, use `path.open("wb")` and stream the writes. The `write_bytes` method returns the number of *bytes* written (not characters — there are no characters), which is the same number `file.write(data)` returns.

The demo's `bin_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")` writes the 16-byte PNG file header. The bytes are: `\x89` (the high-bit-set first byte that distinguishes PNG from text), `PNG` (the ASCII tag), `\r\n` (CRLF — a deliberate cross-platform marker that helps detect binary-corruption transfers), `\x1a` (Ctrl-Z, a DOS end-of-file marker that prevents `TYPE` from dumping garbage on Windows), `\n` (LF), and the 8-byte IHDR chunk header. None of these bytes are characters; writing them as text with `write_text` would raise because `\x89` is not a valid UTF-8 start byte. The `write_bytes` method is the *only* way to write a file whose contents are not text.

**Why is there no `encoding=` on `write_bytes`?** Because `bytes` objects *are* the encoded form — there is no decode or encode step. A `str` is a sequence of Unicode code points; a `bytes` is a sequence of byte values. The `write_text` method takes a `str`, encodes it to `bytes` using `encoding=`, and writes those bytes. The `write_bytes` method takes a `bytes` directly — the caller is responsible for the encoding. The asymmetry is the same as `open(path, "w")` (text mode, takes `str`, needs `encoding=`) vs `open(path, "wb")` (binary mode, takes `bytes`, no `encoding=`).

### Lines 34–41: `Path.open()` as a context manager — the streaming form

```python
# 5. Path.open() as a context manager — streaming large files
big_log = data_dir / "audit.log"
with big_log.open("w", encoding="utf-8") as fh:
    for i in range(3):
        fh.write(f"audit event {i}\n")
with big_log.open("r", encoding="utf-8") as fh:
    for line in fh:
        print("  log line:", line.rstrip())
```

`big_log.open("w", encoding="utf-8")` opens the file for writing and returns a file object — the same kind of object `open(big_log, "w", encoding="utf-8")` returns. The signature is `Path.open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None)` — the same arguments as `open()`, with `mode` defaulting to `"r"`. The `with ... as fh:` form is the context-manager spelling: `__enter__` returns the file object, `__exit__` closes it (even on exception), and the file is guaranteed closed when the block exits.

The `for i in range(3): fh.write(...)` loop writes three lines one at a time, *streaming* the writes — the file is opened once, three writes happen, the file is closed once. The whole-file `write_text` would do the same three writes internally, but it would also open and close the file on every call — `write_text` is the convenience spelling for small files, `open()` is the streaming spelling for large files. The cutoff is roughly: if the file fits in memory, use `write_text`; if it does not, use `open("w")` and stream.

The `for line in fh:` loop on the read side is the canonical line-by-line iteration — the file object is an *iterator* over its own lines, yielding one line per `__next__` call. The whole file is *never* loaded into memory; one line is read at a time, processed, and discarded. The `line.rstrip()` strips the trailing `\n` (and any `\r` that survived the universal-newline translation), and the print adds its own `\n`. For a 10 GB log file, this loop uses constant memory; the equivalent `for line in path.read_text().splitlines():` would load 10 GB into a single string and crash.

**Why use `path.open()` and not `open(path)`?** Because `path` is already a `Path` (you constructed it in lesson 01), and calling a method on it is shorter than passing it as an argument. The two are functionally identical — `open(path)` accepts `Path` since 3.6 via the `__fspath__` protocol, and `path.open()` calls `open(str(self))` internally. The `path.open()` form is preferred in new code because (a) it is one call shorter, (b) the path is the *receiver* of the call rather than an *argument*, which matches the OO style of the rest of the `pathlib` API, and (c) the call site reads as "open this path" rather than "open this string", which is the intent. The `open(path)` form is fine when you already have a string-shaped path (e.g. a config value), but for new code that holds a `Path`, `path.open()` is the spelling.

### Lines 43–50: The Windows `cp1252` gotcha, simulated on POSIX

```python
# 6. The Windows cp1252 gotcha, simulated on POSIX
#    On Windows, open("r") without encoding= uses the locale codepage
#    (cp1252 in US/Western-Europe), which mangles non-ASCII bytes.
emoji_path = data_dir / "unicode.txt"
emoji_path.write_text("ticket: café α\n", encoding="utf-8")
# Reading without encoding= works on Linux (utf-8 locale) but breaks on Windows
print("no encoding (POSIX):", repr(emoji_path.read_text()))
# The rule: always pass encoding= explicitly so behaviour is cross-platform
print("with encoding=utf-8:", repr(emoji_path.read_text(encoding="utf-8")))
```

`emoji_path.write_text("ticket: café α\n", encoding="utf-8")` writes a string with non-ASCII characters (the `é` in `café` is U+00E9, the α is U+03B1) to a UTF-8 file. The bytes on disk are the UTF-8 encoding: `é` is `\xc3\xa9` (two bytes), α is `\xce\xb1` (two bytes). The file is portable across operating systems because UTF-8 is a fixed, well-defined encoding.

`emoji_path.read_text()` — with no `encoding=` argument — reads the file using `locale.getpreferredencoding(False)`. On the Linux sandbox, that returns `UTF-8`, so the read succeeds and returns the original string. On a Windows machine whose locale is `cp1252`, the same call would attempt to decode the bytes as `cp1252`: `\xc3` decodes to `Ã`, `\xa9` decodes to `©`, `\xe2` decodes to `â`, etc. — the string comes back as `"ticket: cafÃ© â\x98\x95\n"`, *mojibake*. On a Windows machine whose locale is `cp932` (Japan), the call would raise `UnicodeDecodeError` on the first byte that does not map cleanly in `cp932`.

`emoji_path.read_text(encoding="utf-8")` reads the file as UTF-8 regardless of the locale. The result is the original string on every operating system. This is the *production* pattern: always pass `encoding="utf-8"` explicitly when the file contains text, so the behaviour is cross-platform and does not depend on the customer's locale. The `pathlib` methods make this easy because the `encoding=` argument is right there on the call site — there is no `with open(...)` boilerplate to forget it in.

**Why does Python not default to `encoding="utf-8"`?** Backwards compatibility. The default `encoding=None` (→ locale encoding) was locked in by the original 3.0 `open()` design, which inherited it from Python 2's `file` type. Changing the default now would break code that runs on Linux and relies on the locale default (rare, but it exists). PEP 597 (Python 3.7+) proposed an `EncodingWarning` to flag implicit-encoding calls, and Python 3.15 is moving toward making `encoding="utf-8"` the default — but until then, the rule is to *always* pass `encoding=` explicitly. The `pathlib` methods make this one keystroke easier than `open()`, which is the second reason (after the OO style) to prefer them.

### Lines 52–55: `write_text` with `newline=` — universal-newline control (3.10+)

```python
# 7. write_text with newline= (3.10+) — universal newline translation
csv_path = data_dir / "export.csv"
csv_path.write_text("id,name\r\n1,alpha\r\n", encoding="utf-8", newline="")
print("newline='' bytes:", csv_path.read_bytes())
```

`csv_path.write_text("id,name\r\n1,alpha\r\n", encoding="utf-8", newline="")` writes a string with `\r\n` (CRLF) line terminators to a file, *without* Python's universal-newline translation modifying them. The `newline=""` argument disables translation: `\n` in the string is written as `\n` (no `\r\n` conversion), and `\r\n` in the string is written as `\r\n` (no `\n` conversion). Without `newline=""` (the default `newline=None`), Python would translate any `\n` in the string to the OS line separator (`\n` on POSIX, `\r\n` on Windows) — which is the *wrong* behaviour for CSV files that must use CRLF regardless of the OS.

The `csv_path.read_bytes()` call confirms the bytes on disk: `b'id,name\r\n1,alpha\r\n'` — the CRLF survives. This is the right call for CSV files consumed by Excel (which expects CRLF on every OS), for HTTP-style headers (`\r\n` is the spec), and for any cross-platform file format where the line terminator is part of the format, not the OS.

The `newline=` parameter was added to `Path.write_text` in Python 3.10 (bpo-33509). Before 3.10, `write_text` always used `newline=None` (translate on write), which made it impossible to write a CRLF file on POSIX or a LF-only file on Windows. The 3.10 fix brought `write_text` to parity with `open(..., newline=...)`. On the 3.12 runtime this vault targets, the `newline=` argument is available; on 3.9 and earlier, the streaming form `path.open("w", encoding="utf-8", newline="")` is the workaround.

**Why does `newline=""` disable translation rather than enabling it?** Because the default (`newline=None`) already *enables* translation — `\n` in the string is converted to the OS separator on write. The `newline=""` argument is the *opt-out* spelling: "do not translate, write the bytes I gave you". The other `newline=` values are: `newline="\n"` (translate `\n` to `\n`, no-op on POSIX, writes `\n` on Windows), `newline="\r"` (translate `\n` to `\r`, the old Mac classic convention), `newline="\r\n"` (translate `\n` to `\r\n`, the Windows convention). The empty-string spelling `newline=""` is the "leave my bytes alone" form, which is what you want for CSV, HTTP, and any cross-platform format.

### Lines 57–60: The rule, side by side

```python
# 8. The rule, side by side
print("---")
print("Python:", sys.version.split()[0])
print("platform.open_text default encoding:", emoji_path.read_text(encoding="utf-8")[:8])
```

The closing block prints the Python version (confirming 3.12+ on the sandbox) and confirms that `read_text(encoding="utf-8")` returns the original string. The "rule" the block enforces is the one sentence the lesson is built around: **always pass `encoding="utf-8"` when the file contains text**. The pathlib methods make that one keystroke easier than `open()` — the `encoding=` argument is on the call site, not buried in a `with open(...)` boilerplate that you might forget.

**Why not just use `open()` with `encoding=`?** You can. `open(path, "r", encoding="utf-8")` works on `Path` since 3.6 (the `__fspath__` protocol), and it is functionally identical to `path.open("r", encoding="utf-8")`. The pathlib methods are preferred in new code for three reasons: (1) the path is the *receiver* of the call, which matches the OO style of the rest of the pathlib API; (2) the `read_text` and `write_text` methods are one-line shortenings of the `with open(...)` form for whole-file reads and writes; (3) the `encoding=` argument is on the same line as the path it applies to, which makes the "always pass encoding=" rule easier to follow. The `open()` form is fine when you already have a string-shaped path or when you need the file object for a long-running streaming context; the pathlib form is the default for new code that holds a `Path`.

## Execution Trace

```bash
$ uv run python boardly/paths/read_write.py
write_text ok -> /tmp/tmpil5jgho7/boardly/data/projects.json
read_text   -> {"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}
read_bytes  -> b'{"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}'
write_bytes ok -> /tmp/tmpil5jgho7/boardly/data/snapshot.bin
read_bytes  -> b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
  log line: audit event 0
  log line: audit event 1
  log line: audit event 2
no encoding (POSIX): 'ticket: café α\n'
with encoding=utf-8: 'ticket: café α\n'
newline='' bytes: b'id,name\r\n1,alpha\r\n'
---
Python: 3.12.15
platform.open_text default encoding: ticket: 
```

The `/tmp/tmpil5jgho7/` prefix on the `write_text ok ->` and `write_bytes ok ->` lines is the tmpdir the demo created; the prefix changes on every run (because `TemporaryDirectory` makes a fresh dir), but the rest of the line — the `boardly/data/...` suffix and the file contents — is deterministic. The `no encoding (POSIX)` line shows that on Linux (UTF-8 locale), reading without `encoding=` returns the original string; on a Windows machine, the same line would raise `UnicodeDecodeError` or return mojibake, which is the bug the lesson teaches you to avoid.

## Common Mistakes

### Mistake 1: Forgetting `encoding=` on Windows

```python
text = path.read_text()    # works on Linux, raises UnicodeDecodeError on Windows
```

**Symptom:** The code works on the developer's Linux laptop and on the Linux CI, then crashes on the customer's Windows server with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 1234: character maps to <undefined>`.
**Why:** `read_text()` with no `encoding=` argument uses `locale.getpreferredencoding(False)`, which is UTF-8 on most Linux/macOS systems and the locale codepage (`cp1252` in US/Western-Europe, `cp932` in Japan, `cp936` in China) on Windows. A UTF-8 file with a non-ASCII byte raises on Windows; an ASCII-only file works on every OS, which is why the bug ships to the customer before anyone notices.
**Fix:** Always pass `encoding="utf-8"` explicitly: `path.read_text(encoding="utf-8")`. The pathlib methods make this one keystroke easier than `open()` because the `encoding=` argument is on the call site. The rule is: if the file contains text, pass `encoding=`. If the file is binary, use `read_bytes()` (no `encoding=` needed).

### Mistake 2: Calling `open()` directly in new code

```python
with open(path, "r", encoding="utf-8") as f:    # path is a Path; works since 3.6
    text = f.read()
```

**Symptom:** The code works, but the call site reads as "open this string" rather than "open this path", and the path's `Path`-ness is invisible at the call site.
**Why:** `open()` accepts `Path` since 3.6 (the `__fspath__` protocol), so the runtime is fine. The bug is stylistic — the `pathlib` API was designed so that `Path` is the *receiver* of file operations (`path.open()`, `path.read_text()`, `path.write_text()`), and calling `open(path)` treats the path as an *argument* to a function that does not belong to it. The `open()` form is also one call longer for whole-file reads/writes.
**Fix:** Use `path.open("r", encoding="utf-8")` for streaming and `path.read_text(encoding="utf-8")` for whole-file reads. The `path.open()` form is the OO spelling; the `path.read_text()` form is the one-line spelling. Both keep the `Path` as the receiver. The `open()` form is fine in legacy code or when you have a string-shaped path; for new code that holds a `Path`, prefer the pathlib methods.

### Mistake 3: Confusing `read_text` and `read_bytes`

```python
text = path.read_text()              # str, decoded
raw = path.read_bytes()              # bytes, raw
text == raw                           # TypeError: str != bytes (Python 3)
```

**Symptom:** A `TypeError` or a silent logic bug where a string is compared to bytes, or vice versa.
**Why:** `read_text` returns a `str` (the file decoded as text); `read_bytes` returns `bytes` (the raw file). The two types are not interchangeable — `str == bytes` raises `TypeError` in Python 3. The student who writes `if path.read_text() == b'{"projects":...}'` will get a `TypeError`; the student who writes `if path.read_bytes() == '{"projects":...}'` will get the same.
**Fix:** Decide which one you want. For text files where you control the encoding: `read_text(encoding="utf-8")` returns the string. For binary files or files of unknown encoding: `read_bytes()` returns the bytes, and you decode yourself with `.decode(encoding, errors="replace")` if you need a string. The rule: if the file is text, `read_text`; if the file is binary or unknown, `read_bytes`.

### Mistake 4: Using `read_text()` on a 10 GB file

```python
text = path.read_text(encoding="utf-8")    # loads 10 GB into memory
```

**Symptom:** `MemoryError` or the process is OOM-killed by the kernel.
**Why:** `read_text()` (and `read_bytes()`) reads the *whole* file into memory before returning. For a 10 GB log file, that means 10 GB of RAM (or 20 GB if the decode produces a string with multi-byte characters that double in size). The pathlib methods are convenience spells for *small* files; they are not streaming APIs.
**Fix:** Use the streaming form: `with path.open("r", encoding="utf-8") as f: for line in f: ...`. The file object is an *iterator* over its own lines, yielding one line at a time, constant memory. For binary streaming, `with path.open("rb") as f: while chunk := f.read(4096): ...` reads in fixed-size chunks. The cutoff is roughly: if the file fits in memory, `read_text`/`read_bytes` are fine; if it does not, `open()` and stream.

## Engineering Trade-Offs

**Decision:** Use `Path.read_text(encoding="utf-8")` and `Path.write_text(data, encoding="utf-8")` for all text I/O in `boardly`. Use `Path.read_bytes()` and `Path.write_bytes(data)` for binary I/O. Use `Path.open(mode, encoding="utf-8")` only when streaming is required.
**Both sides:** The alternative is `open(path, mode, encoding="utf-8")` (the legacy spelling) or `io.open` (the same thing). Both are functionally identical to the pathlib methods, but they treat the path as an *argument* rather than a *receiver*, and the whole-file reads/writes are one call longer (`with open(...) as f: return f.read()` vs `path.read_text()`). The pathlib methods win on (a) call-site brevity for whole-file I/O, (b) OO style consistency with the rest of the pathlib API, and (c) the `encoding=` argument being on the same line as the path it applies to, which makes the "always pass encoding=" rule easier to follow. The `open()` form wins when you have a string-shaped path (e.g. a config value) or when the streaming context is long-running and the file object's lifetime is not tied to a `with` block.
**Commitment:** `boardly` uses `path.read_text(encoding="utf-8")` and `path.write_text(data, encoding="utf-8")` for every text I/O call. The `encoding="utf-8"` argument is *always* passed explicitly — the rule is "if the file contains text, pass `encoding=`; if the file is binary, use `read_bytes`/`write_bytes`". The `path.open(...)` form is used only for streaming large files (logs, exports); the `read_text`/`write_text` form is used for whole-file I/O where the file fits in memory. The legacy `open()` form is forbidden in new code; the lint rule is `rg "open\(" boardly/ | rg -v "path\.open\("` to catch direct `open()` calls.

## Exercises

1. **Exercise 1 — Read the projects.json.** Modify the demo to write a different JSON string and re-read it. Confirm `read_text(encoding="utf-8")` returns the exact string you wrote. `Verify: uv run python boardly/paths/read_write.py | rg 'read_text'`
2. **Exercise 2 — Test the binary round-trip.** Write a 32-byte binary blob with `write_bytes`, read it back with `read_bytes`, and assert the two `bytes` objects are `==`. `Verify: uv run python -c "from pathlib import Path; import tempfile; p = Path(tempfile.mkdtemp()) / 'blob.bin'; src = bytes(range(32)); p.write_bytes(src); assert p.read_bytes() == src; print('round-trip ok')"`
3. **Exercise 3 — Stream a 1000-line log.** Use `path.open("w", encoding="utf-8")` to write 1000 lines (`for i in range(1000): fh.write(f'line {i}\n')`), then `path.open("r", encoding="utf-8")` to count them. Confirm the count is 1000. `Verify: uv run python -c "from pathlib import Path; import tempfile; p = Path(tempfile.mkdtemp()) / 'log.txt'; 
with p.open('w', encoding='utf-8') as f:
    for i in range(1000):
        f.write(f'line {i}\n')
with p.open('r', encoding='utf-8') as f:
    n = sum(1 for _ in f)
assert n == 1000; print('count ok')"`
4. **Exercise 4 — Write a CRLF CSV with `newline=""`.** Write a 3-row CSV (`id,name\r\n1,alpha\r\n2,beta\r\n`) using `write_text(data, encoding="utf-8", newline="")`. Read the bytes back and confirm they end with `\r\n` on every OS. `Verify: uv run python -c "from pathlib import Path; import tempfile; p = Path(tempfile.mkdtemp()) / 'export.csv'; p.write_text('id,name\r\n1,alpha\r\n2,beta\r\n', encoding='utf-8', newline=''); assert p.read_bytes().count(b'\r\n') == 3; print('crlf ok')"`
5. **Exercise 5 — Write a `safe_read_text` helper.** Write a function `safe_read_text(path: Path) -> str` that reads the file as bytes, then tries to decode as UTF-8 with `errors="strict"`, falls back to `latin-1` with `errors="replace"` if UTF-8 fails. The function should never raise on a bad byte; it should return a string with replacement characters for un-decodable bytes. `Verify: uv run python -c "from pathlib import Path; import tempfile; p = Path(tempfile.mkdtemp()) / 'mixed.txt'; p.write_bytes(b'good \xff bad'); import sys; sys.path.insert(0, 'boardly/paths'); from read_write import safe_read_text; out = safe_read_text(p); assert 'good' in out and 'bad' in out; print('safe ok')"`

## Verification

```bash
$ uv run python boardly/paths/read_write.py
write_text ok -> /tmp/tmpil5jgho7/boardly/data/projects.json
read_text   -> {"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}
read_bytes  -> b'{"projects": [{"id": "p-1", "name": "alpha", "budget": "1000.00"}]}'
write_bytes ok -> /tmp/tmpil5jgho7/boardly/data/snapshot.bin
read_bytes  -> b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
  log line: audit event 0
  log line: audit event 1
  log line: audit event 2
no encoding (POSIX): 'ticket: café α\n'
with encoding=utf-8: 'ticket: café α\n'
newline='' bytes: b'id,name\r\n1,alpha\r\n'
---
Python: 3.12.15
platform.open_text default encoding: ticket: 
```

The `/tmp/tmp...` prefix on the `write_text ok ->` and `write_bytes ok ->` lines is the tmpdir the demo created; it changes on every run, but the rest of the line is deterministic. The `no encoding (POSIX)` line shows that on Linux (UTF-8 locale), reading without `encoding=` returns the original string; on a Windows machine, the same line would raise `UnicodeDecodeError` or return mojibake. The `newline='' bytes` line shows the CRLF preserved on disk because `newline=""` disabled translation.

## Previously Learned Here

- [[08-pathlib/01-Path-Basics]] — the `Path` construction and `/` operator this lesson uses to build `data_dir` and `projects_path`; the basics lesson is the foundation for the I/O methods this lesson walks.

## What's Next

[[08-pathlib/03-glob-and-rglob]] — Now that you can read and write individual files, the next lesson makes the `Path` *find* files. `Path.glob("*.json")` matches direct children; `Path.rglob("*.log")` walks the tree recursively; the `**` pattern is the recursive glob. The `case_sensitive=` parameter (added in Python 3.12) lets you do case-insensitive matching on case-sensitive filesystems, and the lesson covers the "no `glob.glob` — use `Path.glob`" rule that keeps path code in one API.

- **Lesson 03** — `glob`, `rglob`, the `**` pattern, the `case_sensitive` kwarg.
- **Lesson 04** — `mkdir`, `rmdir`, `unlink`, `touch`, `rename`, `replace` for filesystem mutation.

## Sources

- **Python `pathlib` module documentation** — https://docs.python.org/3/library/pathlib.html — accessed 2026-10-23 — the source-of-truth reference for `Path.read_text`, `Path.read_bytes`, `Path.write_text`, `Path.write_bytes`, and `Path.open`; documents the `newline=` parameter added in 3.10 and the `encoding=None` default behaviour.
- **PEP 597 — Add optional EncodingWarning** — https://peps.python.org/pep-0597/ — accessed 2026-10-23 — the proposal to flag implicit-encoding `open()` calls; documents the Windows `cp1252` gotcha this lesson walks.
- **Python `io` module documentation** — https://docs.python.org/3/library/io.html — accessed 2026-10-23 — the underlying file-object API that `Path.open` returns; documents the `newline=` translation modes (`None`, `""`, `"\n"`, `"\r"`, `"\r\n"`).

## What We Learned

- You can now read a text file with `Path.read_text(encoding="utf-8")` and explain why the `encoding=` argument is mandatory on Windows (the locale codepage default).
- You can read a binary file with `Path.read_bytes()` and explain why there is no `encoding=` argument (bytes are not characters).
- You can write text with `Path.write_text(data, encoding="utf-8")` and use the `newline=` parameter (3.10+) to control universal-newline translation for cross-platform CSV.
- You can write bytes with `Path.write_bytes(data)` and explain why it is the only way to write a file whose contents are not text.
- You can open a path with `Path.open(mode, encoding="utf-8")` as a context manager for streaming large files, and explain why it is preferred over `open(path)` in new code that holds a `Path`.
