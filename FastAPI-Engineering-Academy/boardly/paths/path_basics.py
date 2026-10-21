"""Pathlib basics: construction, the / operator, accessors, resolve()."""
from pathlib import Path

# 1. Construction from pathsegments
print("Path():", Path())                                  # .
print("Path('a', 'b', 'c'):", Path("a", "b", "c"))        # a/b/c
print("Path('a/b/c'):", Path("a/b/c"))                    # a/b/c
print("type:", type(Path(".")).__name__)                  # PosixPath on Linux/Mac

# 2. The / operator joins paths
print("Path('/') / 'a' / 'b':", Path("/") / "a" / "b")    # /a/b

# 3. Class methods for home and cwd
print("Path.home():", Path.home())
print("Path.cwd():", Path.cwd())

# 4. Accessors on a boardly-style relative path
p = Path("boardly/data/projects.json")
print("p:", p)
print("  .name:", p.name)                # projects.json
print("  .stem:", p.stem)                # projects
print("  .suffix:", p.suffix)            # .json
print("  .suffixes:", p.suffixes)        # ['.json']
print("  .parent:", p.parent)            # boardly/data
print("  .parents:", [str(x) for x in p.parents])
print("  .anchor:", repr(p.anchor))      # '' (relative path has no anchor)
print("  .parts:", p.parts)              # ('boardly', 'data', 'projects.json')
print("  .as_posix():", p.as_posix())    # boardly/data/projects.json

# 5. Absolute path with anchor
abs_p = Path("/etc/passwd")
print("abs_p:", abs_p)
print("  .anchor:", repr(abs_p.anchor))  # '/'
print("  .parts:", abs_p.parts)          # ('/', 'etc', 'passwd')

# 6. resolve() — collapse . and .. and make absolute
rel = Path("boardly/./data/../data/projects.json")
print("rel:", rel)
print("  .resolve(strict=False):", rel.resolve(strict=False))

# 7. resolve(strict=True) raises if the path doesn't exist
try:
    Path("does/not/exist").resolve(strict=True)
except FileNotFoundError as e:
    print("strict=True raises FileNotFoundError:", e)

# 8. Multi-suffix path
archive = Path("boardly/data/archive.2024.json")
print("archive:", archive)
print("  .stem:", archive.stem)          # archive.2024
print("  .suffix:", archive.suffix)      # .json
print("  .suffixes:", archive.suffixes)  # ['.2024', '.json']

# 9. is_relative_to (3.9+) — check whether one path is under another
print("p.is_relative_to('boardly'):", p.is_relative_to("boardly"))
print("p.is_relative_to('logs'):", p.is_relative_to("logs"))
