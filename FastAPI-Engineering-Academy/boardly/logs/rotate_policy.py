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
