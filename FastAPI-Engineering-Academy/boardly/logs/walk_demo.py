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
