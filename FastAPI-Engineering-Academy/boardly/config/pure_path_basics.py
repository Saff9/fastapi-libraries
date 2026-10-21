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
