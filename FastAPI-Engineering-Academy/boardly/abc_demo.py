# boardly/abc_demo.py
"""Walk the collections.abc hierarchy with isinstance checks."""
from collections.abc import (
    Iterable, Container, Sized, Hashable, Callable,
    Iterator, Reversible, Generator,
    Collection, Sequence, MutableSequence,
    Mapping, MutableMapping,
    Set, MutableSet,
    ByteString, Buffer,
    ItemsView, KeysView, ValuesView,
)
from collections import Counter, deque, ChainMap, OrderedDict, defaultdict
from boardly.models import Ticket
from uuid import uuid4


def report(obj, label):
    print(f"{label:30s} -> ", end="")
    checks = [
        ("Iterable",     isinstance(obj, Iterable)),
        ("Container",    isinstance(obj, Container)),
        ("Sized",        isinstance(obj, Sized)),
        ("Hashable",     isinstance(obj, Hashable)),
        ("Callable",     isinstance(obj, Callable)),
        ("Collection",   isinstance(obj, Collection)),
        ("Iterator",     isinstance(obj, Iterator)),
        ("Reversible",   isinstance(obj, Reversible)),
        ("Generator",    isinstance(obj, Generator)),
        ("Sequence",     isinstance(obj, Sequence)),
        ("MutableSeq",   isinstance(obj, MutableSequence)),
        ("Mapping",      isinstance(obj, Mapping)),
        ("MutableMap",   isinstance(obj, MutableMapping)),
        ("Set",          isinstance(obj, Set)),
        ("MutableSet",   isinstance(obj, MutableSet)),
        ("ByteString",   isinstance(obj, ByteString)),
        ("Buffer",       isinstance(obj, Buffer)),
    ]
    yes = [name for name, ok in checks if ok]
    print(", ".join(yes) or "(none)")


if __name__ == "__main__":
    print("--- The five root ABCs and what conforms ---")
    report(42,                 "int")
    report("hello",           "str")
    report([1, 2, 3],          "list")
    report((1, 2, 3),         "tuple")
    report({1, 2, 3},          "set")
    report({"a": 1},           "dict")
    report(deque([1, 2, 3]),  "deque")
    report(Counter("aaabb"),   "Counter")
    report(lambda x: x,        "lambda")

    print("\n--- ChainMap and OrderedDict are Mappings ---")
    report(ChainMap({"a": 1}), "ChainMap")
    report(OrderedDict({"a": 1}), "OrderedDict")
    report(defaultdict(list),  "defaultdict")

    print("\n--- Generators and iterators ---")
    gen = (x for x in [1, 2, 3])
    report(gen, "generator expr")

    print("\n--- The views ---")
    d = {"a": 1, "b": 2}
    report(d.keys(),  "dict.keys()")
    report(d.values(),"dict.values()")
    report(d.items(), "dict.items()")

    print("\n--- Buffer (3.12) ---")
    report(b"hello", "bytes")
    report(bytearray(b"hi"), "bytearray")
    report(memoryview(b"hi"), "memoryview")
