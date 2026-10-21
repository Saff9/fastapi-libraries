# boardly/abc_vs_protocol.py
"""Three ways to express the same contract: collections.abc ABC, custom ABC
with __subclasshook__, and typing.Protocol (runtime_checkable)."""
from abc import ABCMeta, abstractmethod
from typing import Protocol, runtime_checkable, Iterable


# --- Approach 1: collections.abc.Iterable (the stdlib ABC, structural via __subclasshook__) ---

def total_a(items: Iterable[int]) -> int:
    return sum(items)


# --- Approach 2: a custom ABC with __subclasshook__ (manual structural conformance) ---

class CloseableABC(metaclass=ABCMeta):
    @abstractmethod
    def close(self) -> None: ...

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is not CloseableABC:
            return NotImplemented
        if hasattr(subclass, "close"):
            return True
        return NotImplemented


# --- Approach 3: typing.Protocol with @runtime_checkable ---

@runtime_checkable
class CloseableProtocol(Protocol):
    def close(self) -> None: ...


def cleanup_abc(resource: CloseableABC) -> None:
    resource.close()


def cleanup_protocol(resource: CloseableProtocol) -> None:
    resource.close()


if __name__ == "__main__":
    print("--- Iterable (collections.abc) is structural at runtime ---")
    class MyList:
        def __iter__(self):
            return iter([1, 2, 3])
    ml = MyList()
    print(f"isinstance(ml, Iterable): {isinstance(ml, Iterable)}")
    print(f"total_a(ml): {total_a(ml)}")

    print("\n--- Custom ABC with __subclasshook__ ---")
    class FileLike:
        def close(self) -> None:
            print("closed")
    f = FileLike()
    print(f"isinstance(f, CloseableABC): {isinstance(f, CloseableABC)}")
    print(f"isinstance(f, CloseableProtocol): {isinstance(f, CloseableProtocol)}")
    cleanup_abc(f)   # works because __subclasshook__ fired
    cleanup_protocol(f)  # works because Protocol is runtime_checkable

    print("\n--- Protocol without @runtime_checkable cannot isinstance ---")
    class NotCheckable(Protocol):
        def close(self) -> None: ...
    try:
        isinstance(f, NotCheckable)
    except TypeError as e:
        print(f"isinstance raises: {e}")

    print("\n--- runtime_checkable checks attribute presence, not signature ---")
    class Fake:
        close = 42   # not a method, just an int!
    fake = Fake()
    print(f"isinstance(fake, CloseableProtocol): {isinstance(fake, CloseableProtocol)}  (PROTOCOL DOES NOT VERIFY IT IS CALLABLE)")

    print("\n--- performance: __subclasshook__ vs runtime_checkable ---")
    import timeit
    class Many:
        def close(self): pass
    m = Many()
    abc_time = timeit.timeit(lambda: isinstance(m, CloseableABC), number=100_000)
    proto_time = timeit.timeit(lambda: isinstance(m, CloseableProtocol), number=100_000)
    print(f"ABC __subclasshook__:       {abc_time * 1000:.1f} ms (100k checks)")
    print(f"Protocol runtime_checkable: {proto_time * 1000:.1f} ms (100k checks)")
