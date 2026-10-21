"""Discover boardly exporters via importlib.metadata entry points."""
from __future__ import annotations
import importlib.metadata as md
from dataclasses import dataclass


@dataclass
class ExporterInfo:
    name: str
    distribution: str
    factory: object


def discover_exporters(group: str = "boardly.exporters") -> list[ExporterInfo]:
    """Return every exporter declared under the given entry-point group."""
    found: list[ExporterInfo] = []
    for ep in md.entry_points().select(group=group):
        try:
            factory = ep.load()                 # the dotted object from `module:attr`
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip exporter {ep.name!r}: {exc}")
            continue
        found.append(ExporterInfo(
            name=ep.name,
            distribution=ep.dist.name if ep.dist else "(unknown)",
            factory=factory,
        ))
    return found


def fastapi_version() -> str:
    """Return the installed FastAPI version, or raise if missing."""
    return md.version("fastapi")


def requires_python(name: str) -> str | None:
    """Return the package's Requires-Python constraint, or None."""
    return md.metadata(name).get("Requires-Python")


if __name__ == "__main__":
    # 1. version()
    print("--- md.version ---")
    print(f"fastapi version: {fastapi_version()}")
    try:
        md.version("nonexistent_xyz_pkg")
    except md.PackageNotFoundError as exc:
        print(f"missing pkg error: {exc}")

    # 2. metadata()
    print("\n--- md.metadata ---")
    meta = md.metadata("fastapi")
    print(f"type:   {type(meta).__name__}")
    print(f"Name:   {meta['Name']}")
    print(f"Version: {meta['Version']}")
    print(f"Summary: {meta.get('Summary')}")
    print(f"Requires-Python: {requires_python('fastapi')}")
    print("Requires-Dist (first 3):")
    for line in (meta.get_all("Requires-Dist") or [])[:3]:
        print(f"  {line}")

    # 3. entry_points()
    print("\n--- md.entry_points ---")
    all_eps = md.entry_points()
    print(f"type: {type(all_eps).__name__}")
    cs = all_eps.select(group="console_scripts")
    print(f"console_scripts count: {len(cs)}")
    for ep in list(cs)[:3]:
        print(f"  name={ep.name!r}  value={ep.value!r}  group={ep.group!r}")

    # 4. distribution()
    print("\n--- md.distribution ---")
    dist = md.distribution("fastapi")
    print(f"type:           {type(dist).__name__}")
    print(f"dist.version:   {dist.version}")
    print(f"dist.metadata['Name']: {dist.metadata['Name']}")
    print(f"dist.entry_points count: {len(list(dist.entry_points))}")
    print(f"dist.files (first 3):")
    for p in list(dist.files or [])[:3]:
        print(f"  {p}  ({type(p).__name__})")
    record_text = dist.read_text("RECORD")
    print(f"dist.read_text('RECORD') first 60 chars: {(record_text or '')[:60]!r}")

    # 5. packages_distributions()
    print("\n--- md.packages_distributions ---")
    pd = md.packages_distributions()
    print(f"total mappings: {len(pd)}")
    for import_name in ("PIL", "fastapi", "pydantic_core", "email_validator"):
        print(f"  {import_name!r} -> {pd.get(import_name)}")
