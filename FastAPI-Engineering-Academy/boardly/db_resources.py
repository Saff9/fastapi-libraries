"""Read the bundled SQL schema via importlib.resources."""
from __future__ import annotations
import importlib.resources as resources


def read_schema_text() -> str:
    """Return the contents of boardly/schema.sql as a string."""
    schema = resources.files("boardly").joinpath("schema.sql")
    return schema.read_text(encoding="utf-8")


def read_schema_bytes() -> bytes:
    """Return the contents of boardly/schema.sql as bytes (for hash check)."""
    schema = resources.files("boardly") / "schema.sql"
    return schema.read_bytes()


def schema_path_for_c_library():
    """Yield a real filesystem path to schema.sql for a C consumer."""
    schema = resources.files("boardly") / "schema.sql"
    with resources.as_file(schema) as real_path:
        return real_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    print("--- read_text ---")
    demo_text = resources.files("email").joinpath("charset.py").read_text(encoding="utf-8")
    print(f"length: {len(demo_text)} chars")
    print(f"first 50 chars: {demo_text[:50]!r}")

    print("\n--- read_bytes ---")
    demo_bytes = resources.files("email").joinpath("charset.py").read_bytes()
    print(f"length: {len(demo_bytes)} bytes")
    print(f"first 10 bytes: {demo_bytes[:10]!r}")

    print("\n--- as_file context manager ---")
    charset = resources.files("email") / "charset.py"
    with resources.as_file(charset) as p:
        print(f"yielded path: {p}")
        print(f"type: {type(p).__name__}")
        print(f"exists on disk: {p.exists()}")
        print(f"open(p).read(50): {open(p).read(50)!r}")

    print("\n--- Traversable interface ---")
    root = resources.files("email")
    print(f"files('email') type: {type(root).__name__}")
    print(f"is_dir:  {root.is_dir()}")
    print(f"is_file: {root.is_file()}")
    print("iterdir (first 3 children):")
    for child in list(root.iterdir())[:3]:
        print(f"  {child.name}  (is_file={child.is_file()})")
