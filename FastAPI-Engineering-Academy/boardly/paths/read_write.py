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
