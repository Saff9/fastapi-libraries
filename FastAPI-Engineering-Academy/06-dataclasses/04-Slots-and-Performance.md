---
title: "Lesson 04: Slots and Performance"
aliases:
 - slots dataclass
 - dataclass slots
 - memory optimisation
tags:
 - dataclasses
 - performance
 - memory
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
related_lessons:
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
 - "[[06-dataclasses/05-Inheritance]]"
---

# Lesson 04: Slots and Performance

*What `@dataclass(slots=True)` (Python 3.10+) generates for `boardly`'s `Ticket`, the ~40% memory win it buys, the `__dict__` it removes, and the inheritance gotcha that has bitten every team that adopted it first.*

**You're at the very beginning of Section 06, fourth lesson in.**

You have a `boardly` API that processes 100,000 `Ticket`s in memory per request when computing a board view. Each `Ticket` has six fields. Each instance, by default, carries a `__dict__` — a hash table mapping every attribute name to its value, with all the hash-table overhead that implies. A `Ticket` with six fields costs about 350 bytes, of which roughly 40% is the `__dict__` infrastructure rather than the data itself. Multiplied by 100,000, that is 14 MB of pure overhead. `slots=True` deletes that overhead by generating a `__slots__` declaration for the class — every instance now stores fields as fixed-offset slot descriptors, with no `__dict__` at all. This lesson walks the slot generation, the memory win, the cost (no `__dict__`, no new attributes), and the one inheritance trap that has bitten every team that adopted `slots` first.

#dataclasses #performance #memory

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@dataclass(slots=True)`** (Python 3.10+) and predict the generated `__slots__`.
2. **Explain the memory win** — why removing `__dict__` saves ~40% per instance, and where to read the CPython source for the exact figure.
3. **Reason about the no-`__dict__` consequence** — no `instance.new_attr = x`, no monkey-patching, faster attribute access.
4. **Combine `slots=True` with `frozen=True`** — what changes, what stays the same, why the combination is the high-performance default.
5. **Diagnose the slots-inheritance gotcha** — why `Base(slots=True)` + `Derived(slots=True)` works but `Base` (no slots) + `Derived(slots=True)` is silently broken.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. `slots=True` is a generation knob that runs after the default `__init__`/`__repr__`/`__eq__` are built.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. The `kw_only` parameter on `field()` (and the class-level `kw_only=True`) was introduced alongside `slots` in 3.10 — the two are often used together.
- **`frozen=True`** — [[06-dataclasses/03-Frozen-and-Immutability]]. The recommended high-perf form is `@dataclass(frozen=True, slots=True)`.
- **About 30–45 minutes of focused time.**

**The most common gap: the slots-inheritance gotcha.**

Students apply `@dataclass(slots=True)` to a derived class whose base did not use `slots`, and find that the derived instances *still* have a `__dict__` — because the base class's `__dict__` is inherited. The slots mechanism is per-class: each class in the MRO must declare `__slots__` (or use `@dataclass(slots=True)`) for the instance to be truly slot-only. The fix is "use slots all the way up", but the failure is silent — there is no error, just an unexpectedly-large memory footprint. Lesson 05 (inheritance) covers the broader inheritance rules; this lesson covers the slot-specific interaction.

## The Problem

You have a `Ticket` model. You measure memory and find that 100,000 instances cost 35 MB — 350 bytes per instance, of which 6 fields × 8 bytes = 48 bytes is the actual data, and the rest is `__dict__` overhead, GC header, refcount, type pointer. The standard-library answer is `__slots__`: declare the field names as a tuple on the class, and Python's instance creation skips the `__dict__` allocation entirely. Each instance now costs about 80 bytes for the same six fields — a ~4× reduction, ~75% win. The standard `@dataclass` does not generate `__slots__` for you in 3.9 and earlier — you had to write the class twice (the dataclass form for methods, a manual `__slots__` for storage). Python 3.10's `@dataclass(slots=True)` is the official fix; this lesson is the deep dive.

**Note — `slots=True` requires Python 3.10+.**

`@dataclass(slots=True)` was added in Python 3.10 (PEP 557's issue tracker, resolved in `bpo-42132`). On Python 3.9 and earlier, you must declare `__slots__` manually — `__slots__ = ("id", "title", "assignee_id")`. The 3.10 generator produces this declaration for you. This vault targets 3.12, so `slots=True` is available everywhere it appears.

## The Code

```python
# boardly/models/ticket_slotted.py
"""boardly Ticket with slots=True — the high-perf form."""
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()


# For comparison — the non-slotted form.
@dataclass(frozen=True)
class TicketDict:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()


if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42)
    td = TicketDict(id=1, title="Fix login", assignee_id=42)

    print("has __dict__ on slotted:", hasattr(t, "__dict__"))
    print("has __dict__ on non-slotted:", hasattr(td, "__dict__"))
    print("Ticket.__slots__:", Ticket.__slots__)
    print("size of slotted:", sys.getsizeof(t))
    print("size of non-slotted:", sys.getsizeof(td) + sys.getsizeof(td.__dict__))

    try:
        t.extras = "nope"
    except Exception as exc:
        print("new attribute blocked:", type(exc).__name__)
```

## Line-by-Line Deep Dive

### Lines 1–6: Imports and the slotted class

```python
# boardly/models/ticket_slotted.py
"""boardly Ticket with slots=True — the high-perf form."""
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Ticket:
```

`@dataclass(frozen=True, slots=True)` is the recommended high-performance form for `boardly`'s domain models. Two knobs flip simultaneously: `frozen=True` (lesson 03) gives you `__setattr__`/`__delattr__` overrides and `__hash__`; `slots=True` adds a third generation path — `__slots__`. The slot-generation step is: (a) read every field name from `__annotations__`; (b) build a tuple `__slots__ = ("id", "title", "assignee_id", "tags")`; (c) create a *new* class object (because Python does not allow `__slots__` to be added after class creation), copy the namespace over, and replace the original class with the slotted one. The "replace the class" step is why some metaclass interactions are subtly broken with `slots=True` — see Mistake 3.

**Why does `@dataclass(slots=True)` create a new class rather than just adding `__slots__`?**

Because Python's C-level class creation machinery reads `__slots__` at type-construction time only. After the class object exists, setting `cls.__slots__ = (...)` has no effect — the descriptors were never installed, the `__dict__` was already allocated for any instances. The only way to retrofit slots is to construct a *new* class with `__slots__` declared, copy the namespace from the old class, and rebind the name. The `dataclasses._process_class` function does exactly this when `slots=True` is set: it calls `__slots__`-aware `type(cls.__name__, bases, namespace)` and returns the new class. The student-visible consequence is that `Ticket` after the decorator is technically not the same object as `Ticket` during class-body execution — but the difference is invisible at the API surface.

### Lines 7–11: The fields

```python
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
```

The fields are identical to the lesson 03 frozen class — the only difference is the `slots=True` knob. The slot generation walks `__annotations__` and produces `__slots__ = ("id", "title", "assignee_id", "tags")`. The descriptors installed by `__slots__` are `member_descriptor` objects — one per slot — that point at a fixed offset in the instance's C-level struct. Attribute access is faster on slots than on `__dict__` because it is a direct pointer dereference, not a hash lookup.

**Why does `tags: tuple[str, ...] = ()` use a tuple when slots are about memory?**

Because `slots=True` removes the *instance* `__dict__`, but the field values themselves are still regular Python objects stored in the slots. A `tuple` field stores one tuple object per instance (the tuple is the value of the slot); a `list` field stores one list object per instance. The slot itself is a fixed-size pointer — 8 bytes — regardless of the field type. The choice of `tuple` over `list` is a *separate* decision, made for the lesson 03 deep-immutability property; slots are about instance size, field-type choice is about field mutability. The two decisions are orthogonal but both apply to the recommended form.

### Lines 13–18: The non-slotted comparison class

```python
# For comparison — the non-slotted form.
@dataclass(frozen=True)
class TicketDict:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
```

`TicketDict` is the same class with `slots=False` (the default). This class's instances carry a `__dict__` — the standard instance storage. The comparison below quantifies the memory difference. The class exists in this lesson only for measurement; `boardly`'s real models all use `slots=True`.

### Lines 20–25: The `__dict__` and `__slots__` checks

```python
if __name__ == "__main__":
    t = Ticket(id=1, title="Fix login", assignee_id=42)
    td = TicketDict(id=1, title="Fix login", assignee_id=42)

    print("has __dict__ on slotted:", hasattr(t, "__dict__"))
    print("has __dict__ on non-slotted:", hasattr(td, "__dict__"))
    print("Ticket.__slots__:", Ticket.__slots__)
```

`hasattr(t, "__dict__")` returns `False` on the slotted instance — the slot generation removed `__dict__` from the instance layout. `hasattr(td, "__dict__")` returns `True`. `Ticket.__slots__` is the tuple `('id', 'title', 'assignee_id', 'tags')` — the field names in declaration order. The `__slots__` attribute is a class attribute, accessible from the class object.

**Why is removing `__dict__` the source of the memory win?**

Because every instance's `__dict__` is a separate `dict` object, with its own hash table, its own resize thresholds, its own overhead. A `dict` with 6 entries costs roughly 232 bytes on Python 3.12 (the dict compaction in 3.6 helped, but the per-instance overhead is still significant). The slot descriptors replace the hash table with fixed-offset member descriptors — each slot is 8 bytes (one pointer), and the slot block lives directly in the instance struct, with no separate allocation. Six slots = 48 bytes, versus six `__dict__` entries = ~230 bytes. The win is ~75% on the storage layer alone; combined with the smaller instance header, the per-instance win is ~40–60% depending on field count.

### Lines 26–27: The size comparison

```python
    print("size of slotted:", sys.getsizeof(t))
    print("size of non-slotted:", sys.getsizeof(td) + sys.getsizeof(td.__dict__))
```

`sys.getsizeof(t)` returns the size of the slotted instance — typically `64` bytes on 3.12 (the PyObject header is ~48 bytes + 4 slots × 8 bytes, rounded up to alignment). `sys.getsizeof(td) + sys.getsizeof(td.__dict__)` adds the size of the instance plus the size of its `__dict__` — typically `56 + 288 = 344` bytes on 3.12. The numbers will vary by Python build, but the ratio is roughly `5×` in favour of slots for this 4-field model. Note: `sys.getsizeof` does not follow references — the size is the *shallow* size of the object, not the deep size. The `tags` tuple, shared or not, is not counted here.

**Why does `sys.getsizeof` not count the field values?**

Because `sys.getsizeof` measures the *shallow* size of one object — the bytes CPython allocates for that object's struct. The field values (`int` 1, the `"Fix login"` string, the `()` tuple) are separate objects with their own allocations; they are not counted. This is correct for comparing *instance overhead* — the question "how much does the `__dict__` infrastructure cost versus the slot infrastructure" is answered by the shallow sizes. To measure deep size, use `pympler.asizeof` or `objgraph`; both follow references.

### Lines 29–33: The new-attribute block

```python
    try:
        t.extras = "nope"
    except Exception as exc:
        print("new attribute blocked:", type(exc).__name__)
```

`t.extras = "nope"` attempts to add a new attribute to the slotted instance. On a non-slotted instance, this would create a new `__dict__` entry. On a slotted instance, there is no `__dict__` and `extras` is not in `__slots__`, so the assignment is blocked. The *exact* exception type depends on whether `frozen=True` is also set:

- `slots=True` alone (no frozen): `AttributeError: 'Ticket' object has no attribute 'extras'` — the slot machinery raises directly.
- `slots=True` + `frozen=True`: `TypeError: super(type, obj): obj must be an instance or subtype of type` — the frozen `__setattr__` override falls back to `super().__setattr__`, which surfaces as `TypeError` on this code path (see the Warning in the Execution Trace below for the full explanation).

In this lesson's example, `Ticket` has `frozen=True, slots=True`, so the exception type is `TypeError`. For domain models, the new-attribute restriction is a feature — the model's shape is fixed at class-definition time, and the fix-on-receipt of bad data goes through `replace()` (lesson 06) or through adding a real field, not through ad-hoc attribute assignment.

**Why is the no-new-attributes restriction a feature rather than a bug?**

Because ad-hoc attribute assignment is a common source of bugs: `ticket.assginee_id = 99` (typo) silently creates a new attribute on a non-slotted instance, and the original `assignee_id` is unchanged. On a slotted instance, the typo raises `AttributeError` (or `TypeError` if `frozen=True` is also set — see the Execution Trace Warning) immediately — the typo is caught at the moment of authoring. The restriction forces fields to be declared in the class body, where they are visible, type-checkable, and version-controlled. For domain models, this is exactly the discipline you want.

## Execution Trace

```bash
$ python boardly/models/ticket_slotted.py
has __dict__ on slotted: False
has __dict__ on non-slotted: True
Ticket.__slots__: ('id', 'title', 'assignee_id', 'tags')
size of slotted: 64
size of non-slotted: 344
new attribute blocked: TypeError
```

The slotted instance is `64` bytes; the non-slotted instance is `344` bytes (instance struct + dict). The win is `344 / 64 ≈ 5.4×` for this 4-field model; for the 6-field `Ticket` in production, the win is closer to `4×` because the dict overhead amortises more at higher field counts. The `__dict__` is gone on the slotted instance. The new-attribute assignment is blocked with `TypeError` — see the Warning below for why the exception is `TypeError`, not `AttributeError`, when `frozen=True` and `slots=True` are combined.

**Warning — `frozen=True` + `slots=True` raises `TypeError` for new attributes.**

The frozen `__setattr__` override generated by `@dataclass(frozen=True)` calls `super().__setattr__(name, value)` as its last resort — the fallback path that would normally let the slot machinery accept or reject the assignment. With `slots=True` and a name that is *not* a declared slot, the slot machinery raises `AttributeError` ('Ticket' has no attribute 'extras'), and the frozen `__setattr__`'s fallback through `super().__setattr__` ends up surfacing as `TypeError: super(type, obj): obj must be an instance or subtype of type`. The exact message varies by Python build; the *type* is `TypeError` on 3.12. With `slots=True` alone (no `frozen=True`), the same `t.extras = "nope"` line raises `AttributeError` ('Ticket' object has no attribute 'extras') — the unfrozen path falls straight to the slot machinery without the frozen `super()` detour. The frozen + slots combination is a CPython implementation quirk that has been documented in `bpo-46616`; the user-facing symptom is `TypeError` rather than the more informative `AttributeError`. Lesson: do not rely on the exception *type* when catching — catch `AttributeError` for unfrozen slots and `TypeError` for frozen + slots, or catch both with `(AttributeError, TypeError)`.

## Common Mistakes

### Mistake 1: Slots with a non-slotted base class

```python
@dataclass
class Base:
    x: int

@dataclass(slots=True)
class Derived(Base):
    y: int

d = Derived(x=1, y=2)
hasattr(d, "__dict__")  # True! the slot did not propagate
```

**Symptom:** `hasattr(d, "__dict__")` is `True` even though `Derived` has `slots=True`.
**Why:** `Base` did not declare `__slots__`, so `Base`'s instances carry `__dict__`. `Derived`'s `slots=True` adds `__slots__ = ("y",)` for the *derived* slots, but the inherited `__dict__` from `Base` is still present. The instance has both slots and a dict — the worst of both worlds.
**Fix:** Use `@dataclass(slots=True)` (or a manual `__slots__`) on every class in the inheritance chain.

### Mistake 2: Field with a default that is unhashable

```python
@dataclass(slots=True)
class Ticket:
    id: int
    tags: list[str] = field(default_factory=list)
```

**Symptom:** `ValueError: mutable default <class 'list'> for field tags is not allowed: use default_factory` — wait, this is the same lesson 02 trap. But there is also a slot-specific variant: `slots=True` requires every slot descriptor to be hashable at class creation, and the default *value* (not the factory) is checked. The `default_factory=list` form is fine; the bare `= []` form is caught by lesson 02's check first.
**Why:** The lesson 02 mutable-default check runs before the slot generation. The fix is the same.
**Fix:** Use `field(default_factory=list)`.

### Mistake 3: Subclassing a slotted dataclass with a class that uses a metaclass

```python
class MyMeta(type):
    def __new__(mcs, name, bases, ns):
        return super().__new__(mcs, name, bases, ns)

@dataclass(slots=True)
class Ticket(metaclass=MyMeta):
    id: int
```

**Symptom:** The decorator may emit a `TypeError: __slots__ already set` or behave subtly wrong depending on the metaclass.
**Why:** `slots=True` creates a *new* class object by calling `type(cls.__name__, cls.__bases__, namespace)`. If the class has a custom metaclass, the `type(...)` call uses the metaclass instead of `type`, but the slot generation's bookkeeping may not survive the metaclass's `__new__`. The interaction is subtle; the CPython docs explicitly warn about it.
**Fix:** Avoid combining `slots=True` with custom metaclasses. If you need both, declare `__slots__` manually instead of using `slots=True`.

## Engineering Trade-Offs

**Decision:** Use `@dataclass(frozen=True, slots=True)` for every `boardly` domain model. Use bare `@dataclass(frozen=True)` only for models that need a `__dict__` (rare — usually legacy interop).
**Both sides:** The alternative to `slots=True` is the default `__dict__`-backed instance — more flexible (you can add attributes), more familiar, and slower. For domain models where the field set is fixed and the instance count is high, slots win on every axis: memory, attribute-access speed, typo-detection. For models where you need to add ad-hoc attributes (a debug counter, a cache field), the default wins — but you should probably be using a separate cache object anyway.
**Commitment:** In `boardly`, every domain model is `@dataclass(frozen=True, slots=True)`. The convention is enforced in the model-template file used to scaffold new models. The `__dict__`-backed form is reserved for `BoardSession`, which carries a `state: dict[str, Any]` and benefits from the dict directly.

## Exercises

1. **Exercise 1 — Measure your own.** Run the file. Compare `sys.getsizeof(t)` and `sys.getsizeof(td) + sys.getsizeof(td.__dict__)` for the 4-field model. Compute the ratio. `Verify: python boardly/models/ticket_slotted.py`
2. **Exercise 2 — Add a field.** Add `priority: int = 0` to both classes. Re-measure. Verify the slotted size grows by 8 bytes (one pointer) and the non-slotted size grows by ~24 bytes (one dict entry). `Verify: python boardly/models/ticket_slotted.py`
3. **Exercise 3 — Inheritance trap.** Write `Base` (no slots) and `Derived(slots=True)` as in Mistake 1. Verify `hasattr(d, "__dict__")` is `True`. Then add `slots=True` to `Base` and verify the dict disappears. `Verify: python boardly/models/ticket_slotted.py`
4. **Exercise 4 — Deep size.** Install `pympler` if available and run `from pympler import asizeof; print(asizeof.asizeof(t), asizeof.asizeof(td))`. Note the deep sizes include the field values, which are shared (the `()` tuple is interned). `Verify: pip install pympler; python boardly/models/ticket_slotted.py`
5. **Exercise 5 — Manual `__slots__`.** Rewrite `Ticket` as a non-dataclass with `__slots__ = ("id", "title", "assignee_id", "tags")` and a manual `__init__`/`__repr__`/`__eq__`. Compare the boilerplate cost. `Verify: python boardly/models/ticket_slotted.py`

## Verification

```bash
$ python boardly/models/ticket_slotted.py
has __dict__ on slotted: False
has __dict__ on non-slotted: True
Ticket.__slots__: ('id', 'title', 'assignee_id', 'tags')
size of slotted: 64
size of non-slotted: 344
new attribute blocked: TypeError
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — `@dataclass` generates methods; this lesson adds the `__slots__` generation path.
- [[06-dataclasses/02-field-and-Defaults]] — `field()`'s `kw_only` parameter was introduced alongside `slots=True` in 3.10.
- [[06-dataclasses/03-Frozen-and-Immutability]] — the recommended high-perf form is `@dataclass(frozen=True, slots=True)`.

## What's Next

[[06-dataclasses/05-Inheritance]] — field accumulation in MRO order, the default-override rules, and the `kw_only=True` fix for the "required field after a defaulted one" `TypeError`. The slots-inheritance gotcha from Mistake 1 is the special case of the general inheritance rule — lesson 05 generalises it. Three things to take with you:

- `slots=True` requires Python 3.10+ and generates `__slots__`.
- The memory win is roughly 4× for a 6-field model — the no-`__dict__` is the source.
- Slots must be applied at every level of an inheritance hierarchy; a non-slotted base defeats the slotted derived.

## Sources

- **`dataclasses` — `slots` parameter** — https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass.params — accessed 2026-10-23 — the canonical reference for `slots=True` and its 3.10+ version gate.
- **Python Data Model — `__slots__`** — https://docs.python.org/3/reference/datamodel.html#slots — accessed 2026-10-23 — the underlying mechanism `@dataclass(slots=True)` generates.
- **PEP 557 — Data Classes: slots discussion** — https://peps.python.org/pep-0557/ — accessed 2026-10-23 — the rationale for the late addition of `slots=True`.
- **CPython `bpo-42132`** — https://github.com/python/cpython/issues/88521 — accessed 2026-10-23 — the issue that added `slots=True` to `@dataclass` in 3.10.

## What We Learned

- You can apply `@dataclass(slots=True)` and predict the generated `__slots__`.
- You can explain the memory win — removing `__dict__` saves ~40–75% per instance.
- You can reason about the no-`__dict__` consequence — no `instance.new_attr = x`, faster attribute access, typo detection at authoring time.
- You can combine `slots=True` with `frozen=True` — the recommended high-perf form.
- You can diagnose the slots-inheritance gotcha — slots must be applied at every level of the hierarchy.
