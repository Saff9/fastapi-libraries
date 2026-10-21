---
title: "Lesson 04: namedtuple"
aliases:
 - collections.namedtuple
 - namedtuple
 - typing.NamedTuple
tags:
 - collections
 - namedtuple
 - typing
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "25–35 minutes"
prerequisites:
 - "[[04-collections/03-deque]]"
related_lessons:
 - "[[04-collections/05-ChainMap]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
---

# Lesson 04: namedtuple

*`collections.namedtuple` and `typing.NamedTuple` — the lightest "record" types in the standard library. A `namedtuple` has the memory footprint of a tuple (one object header plus N pointers, no per-instance `__dict__`), named-field access, an `_asdict()`, an immutable `_replace()`, and (with `typing.NamedTuple`) full type hints.*

**You're at the very beginning of Section 04 — Lesson 04.**

`namedtuple` is the bridge between tuples and classes. It gives you named access (`ticket.title` instead of `ticket[2]`) without the per-instance `__dict__` that a `class` would allocate. For high-volume read-only records — coordinates, log lines, audit events — it is often the right answer. This lesson walks the factory, the underscore-prefixed helpers, the `typing.NamedTuple` upgrade, and the decision between `namedtuple` and `dataclass`.

Take your time. Type every example. **This is how you learn.**

#collections #namedtuple #typing

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define a `namedtuple`** with `namedtuple("X", ["a", "b"])` and with `typing.NamedTuple`, and explain the difference.
2. **Use `_fields`, `_replace`, `_make`, and `_asdict`** correctly and predict their results.
3. **Compare memory footprint** against a `class` and a `@dataclass` — and know when the win matters.
4. **Decide between `namedtuple`, `typing.NamedTuple`, and `@dataclass`** for a given record.

## Prerequisites

Before starting, you need:

- **[[04-collections/03-deque]]** — comfort with the `collections` module's "small focused class" pattern.
- **Familiarity with `tuple`** — unpacking, immutability, the `tuple` is iterable idea.
- **About 25 minutes of focused time.**

**The most common gap: not knowing `namedtuple` returns a class, not an instance.**

`namedtuple("Ticket", ["id", "title"])` *returns a class*. To get an instance, you call that class: `Ticket(id=1, title="x")`. Students who skim the docs write `t = namedtuple(...)` and then try `t.id` — which works only by accident because `t` is the class itself and accessing an attribute on the class raises `AttributeError`. Read this lesson with "factory that returns a class" front of mind.

## The Problem

Here is the bug. `boardly` has a tiny `Point` type for rendering ticket positions on a board:

```python
def render_point(p: tuple[float, float]) -> str:
    return f"({p[0]}, {p[1]})"
```

This is correct. It is also a code-review problem waiting to happen: the next person to read `p[0]` does not know whether it is x or y, and there is no type to lean on. The obvious next move is a class:

```python
class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
```

But a `class` pays a per-instance cost: every `Point` object has a `__dict__` that holds `{"x": ..., "y": ...}`. For a board with 50,000 tickets × 4 corners × 1 line of history, that is 200,000 dicts — about 30 MB of pure dict overhead.

`namedtuple` gives you named access *and* the memory of a tuple. The class is generated once; instances are tuples with named accessors on the class. No per-instance `__dict__`. The board drops from 30 MB of overhead to 3 MB.

## The Code

```python
# boardly/geometry.py
"""Tiny record types for board layout using namedtuple and typing.NamedTuple."""
from collections import namedtuple
from typing import NamedTuple
from uuid import UUID
from datetime import datetime


# --- collections.namedtuple: the original factory ---

# namedtuple returns a class. The class subclasses tuple. Fields are class-level
# descriptors (property-like objects) that map to tuple slots.
Point = namedtuple("Point", ["x", "y"])
Point.__doc__ = "A 2-D point on the board layout."

# Default values are positional and only allowed on the rightmost fields.
Region = namedtuple("Region", ["x", "y", "w", "h"], defaults=[0, 0])
Region.__doc__ = "A rectangle on the board. w and h default to 0."


# --- typing.NamedTuple: the typed alternative (3.6.1+), same instance shape ---

class TicketSummary(NamedTuple):
    """A summary view of a ticket — for list endpoints, not detail."""
    id: UUID
    title: str
    status: str
    priority: int
    assignee_id: UUID | None = None   # default values work the same way


# --- The underscore-prefixed helpers, demoed in __main__ ---

if __name__ == "__main__":
    # Construct from positional or keyword
    p = Point(3.0, 4.0)
    print(f"Point: {p}, x={p.x}, y={p.y}")

    # _fields is a tuple of field names — the public schema
    print(f"_fields: {Point._fields}")

    # _asdict() returns a plain dict (3.8+ returns a real dict, not OrderedDict)
    print(f"_asdict: {p._asdict()}")

    # _replace returns a new instance with the named fields replaced
    p2 = p._replace(x=10.0)
    print(f"_replace(x=10.0): {p2}; original unchanged: {p}")

    # _make is the alternative constructor for an existing iterable
    coords = (5.0, 6.0)
    p3 = Point._make(coords)
    print(f"_make((5.0, 6.0)): {p3}")

    # Default values on Region
    r = Region(1.0, 2.0)
    print(f"Region(1.0, 2.0) -> {r}")

    # typing.NamedTuple usage — same instance shape, typed fields
    from uuid import uuid4
    ts = TicketSummary(uuid4(), "Write docs", "todo", 2)
    print(f"TicketSummary: {ts}")
    ts2 = TicketSummary(uuid4(), "Fix bug", "in_progress", 4, uuid4())
    print(f"With assignee: {ts2.assignee_id is not None}")
    print(f"  _fields: {TicketSummary._fields}")
    print(f"  _asdict keys: {list(ts2._asdict().keys())}")
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports

```python
# boardly/geometry.py
"""Tiny record types for board layout using namedtuple and typing.NamedTuple."""
from collections import namedtuple
from typing import NamedTuple
from uuid import UUID
from datetime import datetime
```

`from collections import namedtuple` — note the lowercase. `namedtuple` is a *function*, not a class. You call it with a type name and a list of field names; it returns a class.

`from typing import NamedTuple` — note the capitalisation. `typing.NamedTuple` is a *metaclass-based* mechanism that lets you define named-tuple classes with class-body syntax (which is the only way to attach type hints to fields). Both produce instances with the same memory layout.

### Lines 11–16: The `namedtuple` factory

```python
# namedtuple returns a class. The class subclasses tuple. Fields are class-level
# descriptors (property-like objects) that map to tuple slots.
Point = namedtuple("Point", ["x", "y"])
Point.__doc__ = "A 2-D point on the board layout."
```

`namedtuple("Point", ["x", "y"])` — the first argument is the type name (as a string); it becomes the `__name__` of the generated class. The second argument is the field spec; a list, a space-or-comma-separated string, or an iterable all work (`"x y"`, `"x,y"`, `["x", "y"]`, `("x", "y")` all produce the same class).

The return value is a class object. We assign it to `Point` — and now `Point(3.0, 4.0)` constructs an instance.

`Point.__doc__ = "..."` — `namedtuple` accepts a `docstring=` argument in 3.7+ but the assignment-after form works on every version. Setting `__doc__` is the cheapest way to give the class a self-description; `help(Point)` will print it.

**Why is the first argument a string at all?** Because `namedtuple` uses `type(name, bases, namespace)` to build the class, and `type`'s first argument is the name as a string. The string becomes the class's `__name__` and shows up in `repr` — `Point(x=3.0, y=4.0)`. If you wrote `namedtuple(Point, ["x", "y"])` (passing the bare name `Point`), Python would have looked up `Point` *before* `namedtuple` had a chance to define it — `NameError`. The string is a forward reference to the type's name.

### Lines 18–20: Default values — rightmost only

```python
# Default values are positional and only allowed on the rightmost fields.
Region = namedtuple("Region", ["x", "y", "w", "h"], defaults=[0, 0])
Region.__doc__ = "A rectangle on the board. w and h default to 0."
```

`defaults=[0, 0]` provides default values for the *last two* fields — `w` and `h`. The `defaults` list is positional and right-aligned: it always applies to the trailing fields, never the leading ones. This mirrors function defaults in Python — you cannot have `def f(a=1, b)` because non-default args cannot follow default args.

`Region(1.0, 2.0)` therefore fills `x=1.0, y=2.0, w=0, h=0`. `Region(1.0, 2.0, 3.0, 4.0)` fills all four. `Region(1.0)` raises `TypeError` because `y` has no default.

**Why right-aligned?** Because the generated class's `__new__` has the signature `__new__(cls, x, y, w=0, h=0)` — a normal function signature with defaults only on the trailing args.

### Lines 25–32: `typing.NamedTuple` — the typed upgrade

```python
class TicketSummary(NamedTuple):
    """A summary view of a ticket — for list endpoints, not detail."""
    id: UUID
    title: str
    status: str
    priority: int
    assignee_id: UUID | None = None   # default values work the same way
```

`class TicketSummary(NamedTuple):` — the class inherits from `typing.NamedTuple`. The class body uses type-annotated assignments; the metaclass behind `NamedTuple` reads those annotations and builds the corresponding `namedtuple`-shaped class.

The result *is* a namedtuple: `TicketSummary._fields` exists, `_asdict` works, instances are tuples. The only difference from a plain `namedtuple` is that the class body gave us a place to write type hints — which `mypy`, `pyright`, and Pydantic's introspection (used by FastAPI) all read.

**Why prefer `typing.NamedTuple` in 3.12 code?** Because the type hints survive. `namedtuple("X", ["a", "b"])` produces a class with no annotations; downstream tools have no idea what types `a` and `b` are. `typing.NamedTuple` is the same memory layout, with annotations attached. There is no downside.

### Lines 36–40: Constructing instances — positional or keyword

```python
    # Construct from positional or keyword
    p = Point(3.0, 4.0)
    print(f"Point: {p}, x={p.x}, y={p.y}")
```

`Point(3.0, 4.0)` — positional construction, the same as any tuple. `Point(x=3.0, y=4.0)` works too — the generated class accepts both. `p.x` is a class-level descriptor (a `_tuplegetter` in CPython) that returns `self[0]`. It is *not* an instance attribute; the instance is a plain tuple underneath.

### Lines 42–46: `_fields` and `_asdict()`

```python
    # _fields is a tuple of field names — the public schema
    print(f"_fields: {Point._fields}")

    # _asdict() returns a plain dict (3.8+ returns a real dict, not OrderedDict)
    print(f"_asdict: {p._asdict()}")
```

`Point._fields` is `("x", "y")` — a tuple of the field names, available on the class. This is the public schema; you iterate it when serialising or introspecting. The leading underscore is the convention for "this is part of the public API but is named to avoid colliding with field names" — if a field were called `fields`, the `_fields` slot would not shadow it.

`p._asdict()` returns `{"x": 3.0, "y": 4.0}`. In Python 3.8+ this is a plain `dict`; before 3.8 it was an `OrderedDict`. In 3.12 you do not need to wrap it in `dict(...)` for JSON serialisation — `json.dumps` accepts it directly.

### Lines 48–51: `_replace` — functional update

```python
    # _replace returns a new instance with the named fields replaced
    p2 = p._replace(x=10.0)
    print(f"_replace(x=10.0): {p2}; original unchanged: {p}")
```

`p._replace(x=10.0)` returns a new `Point` with `x=10.0` and `y` copied from `p`. The original `p` is unchanged — namedtuples are immutable, like tuples. `_replace` is the namedtuple equivalent of `dataclasses.replace`.

**Why "replace" and not "with"?** Because the method existed long before `dataclasses.replace`; the name stuck. The semantics are pure functional update: the input is untouched, the output is a new instance.

### Lines 53–57: `_make` — alternative constructor

```python
    # _make is the alternative constructor for an existing iterable
    coords = (5.0, 6.0)
    p3 = Point._make(coords)
    print(f"_make((5.0, 6.0)): {p3}")
```

`Point._make(iterable)` is equivalent to `Point(*iterable)` — unpacking. The reason it exists as a separate method: it accepts *any* iterable, including non-sequence iterables (generators, sets when order is not a concern, `map` results). `Point(*gen)` works too — `_make` is for readability and for the case where the iterable might not be unpackable by `*`.

**Why `_make` and not `from_iter`?** Historical. The leading underscore signals the same "public but underscore-prefixed to avoid field-name collision" idea as `_fields`.

### Lines 59–63: Default values in action

```python
    # Default values on Region
    r = Region(1.0, 2.0)
    print(f"Region(1.0, 2.0) -> {r}")
```

`Region(1.0, 2.0)` constructs a `Region` with `w=0, h=0` filled in from defaults. The repr is `Region(x=1.0, y=2.0, w=0, h=0)`.

### Lines 65–71: `typing.NamedTuple` in use

```python
    # typing.NamedTuple usage — same instance shape, typed fields
    from uuid import uuid4
    ts = TicketSummary(uuid4(), "Write docs", "todo", 2)
    print(f"TicketSummary: {ts}")
    ts2 = TicketSummary(uuid4(), "Fix bug", "in_progress", 4, uuid4())
    print(f"With assignee: {ts2.assignee_id is not None}")
    print(f"  _fields: {TicketSummary._fields}")
    print(f"  _asdict keys: {list(ts2._asdict().keys())}")
```

`TicketSummary(uuid4(), "Write docs", "todo", 2)` constructs without the optional `assignee_id` — it defaults to `None`. `ts2` passes all five fields positionally. Both instances have the same shape; both serialise the same way.

## Execution Trace

```bash
$ uv run python boardly/geometry.py
Point: Point(x=3.0, y=4.0), x=3.0, y=4.0
_fields: ('x', 'y')
_asdict: {'x': 3.0, 'y': 4.0}
_replace(x=10.0): Point(x=10.0, y=4.0); original unchanged: Point(x=3.0, y=4.0)
_make((5.0, 6.0)): Point(x=5.0, y=6.0)
Region(1.0, 2.0) -> Region(x=1.0, y=2.0, w=0, h=0)
TicketSummary: TicketSummary(id=UUID('...'), title='Write docs', status='todo', priority=2, assignee_id=None)
With assignee: True
  _fields: ('id', 'title', 'status', 'priority', 'assignee_id')
  _asdict keys: ['id', 'title', 'status', 'priority', 'assignee_id']
```

## Common Mistakes

### Mistake 1: Treating `namedtuple` as if it returns an instance

```python
t = namedtuple("Ticket", ["id", "title"])   # student expects an instance
t.id   # AttributeError
```

**Symptom:** `AttributeError: 'function' object has no attribute 'id'` (or, if they used the class-level form, `AttributeError: type object 'Ticket' has no attribute 'id'`).

**Why:** `namedtuple` returns the *class*. The class itself does not have `id` as an attribute — `id` is a descriptor that fires on instances. Accessing `Ticket.id` (the class) does not invoke the descriptor; it tries to look up `id` on the class, which is absent.

**Fix:** Call the class to make an instance: `Ticket = namedtuple("Ticket", ["id", "title"]); t = Ticket(1, "x"); t.id`.

### Mistake 2: Mutating a field by assignment

```python
p = Point(3.0, 4.0)
p.x = 10.0   # student expects success
```

**Symptom:** `AttributeError: can't set attribute` — namedtuples are immutable.

**Why:** The `x` descriptor on the class is a `_tuplegetter` — a read-only descriptor with no `__set__`. There is no `__dict__` to write into either (instances are tuples underneath, with no per-instance dict).

**Fix:** Use `_replace`: `p = p._replace(x=10.0)`. If you need mutability, use `@dataclass` (Section 06) or `typing.NamedTuple` with `dataclass_transform` decorators — but those are not namedtuple.

### Mistake 3: A field name that collides with a method

```python
T = namedtuple("T", ["_fields", "x"])   # _fields is reserved
```

**Symptom:** `ValueError: Encountered duplicate field name: '_fields'` (or, for some reserved names, a more cryptic error).

**Why:** `namedtuple` reserves `_fields`, `_asdict`, `_replace`, `_make`, `_source`, and the dunder names. Field names cannot start with an underscore (the convention marks namedtuple's own API) and cannot collide with the reserved names.

**Fix:** Rename the field. If you really need a field called `fields`, use `@dataclass`.

## Engineering Trade-Offs

**Decision:** Use `typing.NamedTuple` for high-volume read-only records where memory matters; use `@dataclass` for everything else.

**Both sides:**

`typing.NamedTuple` wins on:

1. Memory. A namedtuple is one C-level tuple object — `sizeof(Point(3.0, 4.0))` is 64 bytes (the tuple header plus two pointers). The equivalent `@dataclass` is 152 bytes (object header, `__dict__`, two pointers in the dict).
2. Hashability. Namedtuples are hashable by default (they inherit tuple's `__hash__`), so they go straight into sets and dict keys.
3. Tuple compatibility. A namedtuple *is a tuple*, so it works anywhere a tuple is expected: `for x, y in points`, `dict(zip(fields, point))`, JSON serialisation via `tuple(point)`.

`@dataclass` wins on:

1. Mutability. `@dataclass` defaults to mutable; namedtuples are immutable.
2. Inheritance. `@dataclass` inheritance works cleanly with `field()` defaults and `InitVar`; `NamedTuple` inheritance is finicky.
3. Methods. `@dataclass` lets you add methods and `__post_init__` cleanly; `NamedTuple` lets you add methods but the class body is constrained.
4. Forward compatibility. `@dataclass(slots=True, frozen=True)` (Section 06) approaches namedtuple's memory while keeping the class-body ergonomics.

**Commitment:** `boardly/geometry.py` uses `typing.NamedTuple` for `TicketSummary` (read-only list endpoints) and `namedtuple` for `Point`/`Region` (tiny records with no type-hint benefit). For mutable records (`Ticket`, `Project`, `User`), `boardly/models.py` uses `@dataclass`. The rule: "immutable record with millions of instances → `NamedTuple`; mutable record or rich class → `@dataclass`."

## Exercises

1. **Exercise 1 — Inspect `__sizeof__`.** Print `Point(3.0, 4.0).__sizeof__()` and compare with a class with two float attributes. `Verify: uv run python -c "from collections import namedtuple; P=namedtuple('P',['x','y']); print(P(1.0,2.0).__sizeof__())"`
2. **Exercise 2 — String field spec.** Construct a `namedtuple` with fields given as a space-separated string `"x y"`. Confirm it works. `Verify: uv run python -c "from collections import namedtuple; P=namedtuple('P','x y'); print(P(1,2))"`
3. **Exercise 3 — Defaults.** Build a `namedtuple` with `defaults=[1]` for three fields and confirm the rightmost field defaults. `Verify: uv run python -c "from collections import namedtuple; R=namedtuple('R',['a','b','c'],defaults=[1]); print(R(0,0))"`
4. **Exercise 4 — `_asdict` round-trip.** Take a `Point`, call `_asdict`, and reconstruct it from the dict via `_make(d.values())`. Confirm equality. `Verify: uv run python -c "from collections import namedtuple; P=namedtuple('P',['x','y']); p=P(1,2); q=P._make(p._asdict().values()); print(p==q)"`
5. **Exercise 5 — Convert to `typing.NamedTuple`.** Rewrite `Point` as a `class Point(NamedTuple)` with type hints. Confirm `mypy --strict` passes (or `pyright`) on the file. `Verify: uv run python -c "from boardly.geometry import Point; print(Point._fields, hasattr(Point,'__annotations__'))"`

## Verification

```bash
$ uv run python boardly/geometry.py
Point: Point(x=3.0, y=4.0), x=3.0, y=4.0
_fields: ('x', 'y')
_asdict: {'x': 3.0, 'y': 4.0}
_replace(x=10.0): Point(x=10.0, y=4.0); original unchanged: Point(x=3.0, y=4.0)
_make((5.0, 6.0)): Point(x=5.0, y=6.0)
Region(1.0, 2.0) -> Region(x=1.0, y=2.0, w=0, h=0)
TicketSummary: TicketSummary(id=UUID('...'), title='Write docs', status='todo', priority=2, assignee_id=None)
With assignee: True
  _fields: ('id', 'title', 'status', 'priority', 'assignee_id')
  _asdict keys: ['id', 'title', 'status', 'priority', 'assignee_id']
```

## Previously Learned Here

- [[04-collections/03-deque]] — the dynamic-container side of `collections`.
- [[04-collections/01-Counter]] — the gentlest entry, where the section's "small focused class" pattern started.

## What's Next

[[04-collections/05-ChainMap]] — back to mapping-land, but for a different problem: layering. `ChainMap(d1, d2)` is a *view* over multiple dicts — reads fall through to the next layer, writes go to the first. It is the data structure for "defaults + env + user config" without copying anything. We will see how it differs from `{**defaults, **env, **user}` (which copies) and why FastAPI's config layering often has a `ChainMap`-shaped structure underneath.

## Sources

- **Python `collections.namedtuple` documentation** — https://docs.python.org/3/library/collections.html#collections.namedtuple — accessed 2026-10-23 — the canonical reference for the factory, the underscore helpers, the `defaults` argument, and the rename behaviour.
- **`typing.NamedTuple` documentation** — https://docs.python.org/3/library/typing.html#typing.NamedTuple — accessed 2026-10-23 — the typed alternative, with class-body syntax and annotations.
- **PEP 526 — Variable and class-level annotations** — https://peps.python.org/pep-0526/ — accessed 2026-10-23 — the syntax `typing.NamedTuple` relies on for its class-body field declarations.

## What We Learned

- `namedtuple("X", ["a", "b"])` returns a class; call the class to make instances.
- The class subclasses `tuple`; fields are class-level read-only descriptors backed by tuple slots.
- `_fields` is the public schema tuple; `_asdict()` returns a real `dict` (3.8+); `_replace(**kw)` does functional update; `_make(iterable)` unpacks.
- Defaults are right-aligned: `defaults=[d1, d2]` applies to the trailing fields.
- `typing.NamedTuple` is the same memory layout with type annotations — prefer it in 3.12 code.
- A namedtuple is 60–90 bytes; a `@dataclass` is ~150 bytes. The win matters at high volume.
