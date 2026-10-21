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
