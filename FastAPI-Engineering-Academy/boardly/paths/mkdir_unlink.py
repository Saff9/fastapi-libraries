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
