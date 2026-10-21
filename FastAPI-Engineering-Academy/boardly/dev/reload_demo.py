"""Demonstrates importlib.reload and the from-import gotcha."""
from __future__ import annotations
import importlib
import sys
import tempfile
import textwrap
from pathlib import Path


def _write_module(dir_path: Path, name: str, source: str):
    """Write a Python file into a directory."""
    (dir_path / f"{name}.py").write_text(source, encoding="utf-8")


def main():
    # Set up a throwaway package on disk.
    tmpdir = Path(tempfile.mkdtemp())
    print(f"workspace: {tmpdir}")
    sys.path.insert(0, str(tmpdir))

    # Version 1 of `routers.projects` and a consumer `app`.
    _write_module(tmpdir, "routers", textwrap.dedent("""
        class Router:
            color = "red"
            def handle(self):
                return "handle-v1"
        ROUTER_INSTANCE = Router()
    """))
    _write_module(tmpdir, "app", textwrap.dedent("""
        from routers import Router, ROUTER_INSTANCE

        def describe():
            return f"Router.color={Router.color}, instance={ROUTER_INSTANCE.hello() if hasattr(ROUTER_INSTANCE, 'hello') else ROUTER_INSTANCE.handle()}"
    """))

    import routers
    import app

    print("\n--- before reload ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")

    # Edit routers.py to version 2.
    _write_module(tmpdir, "routers", textwrap.dedent("""
        class Router:
            color = "blue"
            def handle(self):
                return "handle-v2"
        ROUTER_INSTANCE = Router()
    """))

    # Reload routers, but NOT app.
    importlib.reload(routers)
    print("\n--- after reload(routers), app NOT reloaded ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")

    # Reload app too.
    importlib.reload(app)
    print("\n--- after reload(app) too ---")
    print(f"  routers.Router.color:     {routers.Router.color}")
    print(f"  app.Router.color:        {app.Router.color}")
    print(f"  app.Router is routers.Router? {app.Router is routers.Router}")
    print(f"  app.describe():          {app.describe()}")


if __name__ == "__main__":
    main()
