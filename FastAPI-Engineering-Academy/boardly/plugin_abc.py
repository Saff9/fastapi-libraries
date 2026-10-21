# boardly/plugin_abc.py
"""A custom ABC for plugins: ABCMeta + abstractmethod + register + __subclasshook__."""
from abc import ABCMeta, abstractmethod
from typing import Any, TYPE_CHECKING


class Plugin(metaclass=ABCMeta):
    """The boardly plugin contract.

    Two abstract methods: name() and run(ctx). Subclasses must implement both
    or instantiation raises TypeError. Third-party classes can be registered
    as virtual subclasses via Plugin.register(OtherClass).
    """

    @abstractmethod
    def name(self) -> str:
        """Return the plugin's display name."""

    @abstractmethod
    def run(self, ctx: dict) -> Any:
        """Execute the plugin against the boardly context."""

    # The classmethod form of register is also available; users can call it
    # as a decorator: @Plugin.register
    # or as a function: Plugin.register(SomeClass)


class CsvExportPlugin(Plugin):
    """A real plugin that implements the contract."""

    def name(self) -> str:
        return "csv_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to CSV"


# --- A third-party class that happens to implement the contract ---

class ThirdPartyJsonExport:
    """A class that did not inherit from Plugin but has the right methods."""

    def name(self) -> str:
        return "json_export"

    def run(self, ctx: dict) -> Any:
        return f"exported {len(ctx.get('tickets', []))} tickets to JSON"


# --- Register the third-party class as a virtual subclass ---

Plugin.register(ThirdPartyJsonExport)


# --- A structural __subclasshook__: any class with name and run is a Plugin ---

class StructuralPlugin(metaclass=ABCMeta):
    """Like Plugin but conformance is structural, not registered."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, ctx): ...

    @classmethod
    def __subclasshook__(cls, subclass):
        """Decide conformance based on the methods present on `subclass`."""
        if cls is not StructuralPlugin:
            return NotImplemented   # delegate to the normal MRO check
        # Check whether subclass has both 'name' and 'run' attributes.
        if hasattr(subclass, "name") and hasattr(subclass, "run"):
            return True
        return NotImplemented   # fall back to default behaviour


if __name__ == "__main__":
    print("--- Plugin: ABCMeta + abstractmethod ---")
    try:
        Plugin()  # student expects this to fail
    except TypeError as e:
        print(f"Plugin() raises: {e}")

    p = CsvExportPlugin()
    print(f"CsvExportPlugin name: {p.name()}")
    print(f"run result: {p.run({'tickets': [1, 2, 3]})}")

    print("\n--- register: nominal virtual subclass ---")
    third = ThirdPartyJsonExport()
    print(f"isinstance(third, Plugin): {isinstance(third, Plugin)}")
    print(f"isinstance(third, CsvExportPlugin): {isinstance(third, CsvExportPlugin)}  (no, just Plugin)")

    print("\n--- __subclasshook__: structural conformance ---")
    class Unregistered:
        def name(self): return "x"
        def run(self, ctx): return "ok"
    u = Unregistered()
    print(f"isinstance(u, StructuralPlugin): {isinstance(u, StructuralPlugin)}")
    print(f"isinstance(u, Plugin): {isinstance(u, Plugin)}  (still False; Plugin uses register, not __subclasshook__)")

    print("\n--- the ABCMeta.__subclasses__ and __abstractmethods__ internals ---")
    print(f"Plugin.__abstractmethods__: {Plugin.__abstractmethods__}")
    print(f"StructuralPlugin.__subclasshook__ is callable: {callable(StructuralPlugin.__subclasshook__)}")
