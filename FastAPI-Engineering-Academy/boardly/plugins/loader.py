"""Load router modules by dotted name from a config list."""
from __future__ import annotations
import importlib
from dataclasses import dataclass


@dataclass
class LoadedRouter:
    name: str
    router: object


def load_router(dotted_name: str) -> LoadedRouter:
    """Import a dotted module name and pull its `.router` attribute."""
    module = importlib.import_module(dotted_name)
    if not hasattr(module, "router"):
        raise AttributeError(
            f"module {dotted_name!r} has no `router` attribute; "
            f"did you forget to define `router = APIRouter()`?"
        )
    return LoadedRouter(name=dotted_name, router=module.router)


def load_routers(names: list[str]) -> list[LoadedRouter]:
    """Import every router; skip broken ones with a warning."""
    loaded: list[LoadedRouter] = []
    for name in names:
        try:
            loaded.append(load_router(name))
        except (ImportError, AttributeError) as exc:
            print(f"[boardly] skip router {name!r}: {exc}")
    return loaded


if __name__ == "__main__":
    import sys
    # Simulate a config-driven loader. For the demo we use stdlib modules
    # that expose a `version` attribute as a stand-in for a `router`.
    candidates = ["importlib.metadata", "importlib.resources", "no.such.module"]
    print(f"Loading {len(candidates)} plugin candidates...\n")
    for cand in candidates:
        try:
            mod = importlib.import_module(cand)
            print(f"  ok   {cand} -> {mod.__name__} (file={getattr(mod, '__file__', '(built-in)')})")
        except ImportError as exc:
            print(f"  FAIL {cand} -> {exc}")
    print()

    # The package= argument for relative imports.
    # Resolves ".metadata" against the package "importlib".
    relative = importlib.import_module(".metadata", package="importlib")
    print("import_module('.metadata', package='importlib'):")
    print(f"  -> {relative.__name__}")
    print(f"  is importlib.metadata? {relative is importlib.metadata}")
