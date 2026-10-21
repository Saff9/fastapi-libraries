---
title: "Lesson 01: dataclass Basics"
aliases:
 - dataclass Basics
 - @dataclass
 - dataclass decorator
tags:
 - dataclasses
 - canonical
status: complete
course_level: beginner
difficulty: beginner
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[06-dataclasses/02-field-and-Defaults]]"
 - "[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]"
first_taught_in: "06-dataclasses/01-dataclass-Basics"
---

# Lesson 01: dataclass Basics

*What `@dataclass` actually generates for `boardly`'s `Project` model — and why `eq=True` is on by default while `order=False` is off.*

**You're at the very beginning of Section 06.**

You have written `class Project: def __init__(self, id: int, name: str): ...` a hundred times. You have written a `__repr__` for it. You have written an `__eq__`. You have done this for `User`, for `Ticket`, for `Comment`, for `Label`, for `Milestone`. It is the same six methods every time, every project, every codebase. `@dataclass` is the standard library's answer to that repetition. It is not magic — it is a class decorator that runs at import time and writes those six methods for you by calling `exec` on generated source. This lesson walks what it writes, line by line, so the rest of the section can build on a foundation you have already seen the source of.

#dataclasses #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `@dataclass`** to a typed class and predict every method Python generates for it.
2. **Explain the `eq=True` / `order=False` default** — why equality is on by default but ordering is off, and what changes when you flip `order=True`.
3. **Distinguish `field()` from `= value` defaults** — when each is legal, when each is required, and the mutable-default trap that motivates `field(default_factory=...)`.
4. **Read the generated `__init__` signature** from a class body and predict the parameter order, the keyword-only boundary, and which arguments are required.
5. **Diagnose the missing-annotation `TypeError`** that fires when a field has no type hint — and explain *why* `@dataclass` requires annotations to identify fields.

## Prerequisites

Before starting, you need:

- **Type hints** — [[01-typing/01-Type-Hints-Basics]]. `@dataclass` walks `__annotations__` to find fields; a class with `name = "x"` and no annotation is invisible to the decorator.
- **About 30–45 minutes of focused time.**

**The most common gap: the type-hint requirement.**

Students who hit `@dataclass` for the first time almost always write `class Project: id = 1` (no annotation) and then are surprised when the generated `__init__` has no `id` parameter. The decorator does not look at the class body for attributes — it looks at `cls.__annotations__`, which is a dict Python only populates when you write `id: int = 1`. The annotation *is* the field declaration. Without it, the line is a regular class attribute and `@dataclass` ignores it.

## The Problem

You have a `boardly` project-management API with five models — `Project`, `User`, `Ticket`, `Comment`, `Label` — and you write this for each one:

```python
class Project:
    def __init__(self, id: int, name: str, owner_id: int):
        self.id = id
        self.name = name
        self.owner_id = owner_id

    def __repr__(self):
        return f"Project(id={self.id!r}, name={self.name!r}, owner_id={self.owner_id!r})"

    def __eq__(self, other):
        if not isinstance(other, Project):
            return NotImplemented
        return (self.id, self.name, self.owner_id) == (other.id, other.name, other.owner_id)
```

That is 14 lines for three fields. For five models with an average of six fields each, you are writing 700 lines of `__init__`/`__repr__`/`__eq__` boilerplate — all of it identical in shape, all of it copy-pasteable, all of it a place for a typo to hide for six months. The `__eq__` above is *almost* right but forgets `__hash__`, so `Project` ends up unhashable and you cannot put it in a set. The `__repr__` is *almost* right but uses `=` instead of `!r` for `name`, so `Project(name="ab\"c")` renders with a syntax error. These bugs are not rare. They are the standard outcome of writing the methods by hand.

`@dataclass` solves all of this by generating the methods for you, correctly, once, by the same Python core team that wrote the language. The methods are not just shorter — they are *right*.

## The Code

```python
# boardly/models/project.py
"""boardly Project model — the canonical @dataclass example."""
from dataclasses import dataclass


@dataclass
class Project:
    id: int
    name: str
    owner_id: int
    archived: bool = False


# Sanity check the generated methods.
if __name__ == "__main__":
    p = Project(id=1, name="boardly MVP", owner_id=42)
    print(p)
    print(p == Project(id=1, name="boardly MVP", owner_id=42))
    print(p == Project(id=1, name="boardly MVP", owner_id=99))
    print(hash(p) if hasattr(p, "__hash__") and p.__hash__ else "unhashable")
```

## Line-by-Line Deep Dive

### Lines 1–4: Module header and import

```python
# boardly/models/project.py
"""boardly Project model — the canonical @dataclass example."""
from dataclasses import dataclass
```

The module docstring is the only string in the file before the import. We import the `dataclass` decorator from the `dataclasses` module — note the singular name (`dataclass` the decorator) versus the plural module name (`dataclasses`). The decorator is a function: `def dataclass(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False): ...`. Every parameter except `cls` is keyword-only (the `/` then `*` signature pins `cls` as positional-only and the rest as keyword-only). The keyword arguments are the knobs the rest of this section turns. In this lesson we touch none of them and accept every default.

**Python 3.12+:** the `weakref_slot` parameter was added in 3.12 (alongside `slots=True`-aware weakref support). On 3.10 and 3.11, `dataclass`'s signature ends at `slots=False` — `weakref_slot` is the 3.12 addition. This vault targets 3.12, so the parameter is available; on older runtimes, omit it.

**Why does `@dataclass` accept `cls=None` as the first positional argument?**

Because the decorator is designed to be called both bare (`@dataclass`) and with arguments (`@dataclass(frozen=True)`). When used bare, `cls` is the class being decorated. When used with arguments, `cls` is `None` and the decorator returns a closure that Python then applies to the class. The `cls=None` sentinel is the implementation detail that makes both call sites work with one function. You can read this directly in `Lib/dataclasses.py`.

### Lines 6–11: The decorated class

```python
@dataclass
class Project:
    id: int
    name: str
    owner_id: int
    archived: bool = False
```

`@dataclass` runs at class-body-evaluation time, *after* Python has finished building the `Project` class object. The decorator inspects `Project.__annotations__` — a dict Python populated automatically when you wrote `id: int`, `name: str`, and `owner_id: int`. The keys are the field names (`"id"`, `"name"`, `"owner_id"`, `"archived"`); the values are the annotation expressions evaluated at class-body scope (`int`, `str`, `int`, `bool`). For each annotated name, `@dataclass` looks at the class `__dict__` to see if a default value was assigned. `id`, `name`, `owner_id` have no value in `__dict__` — they are required. `archived` has `False` in `__dict__` — it has a default.

From this, `@dataclass` builds a `Field` object per field, then generates `__init__` source as a string and `exec`s it into the `Project` namespace. The generated `__init__` is, in effect:

```python
def __init__(self, id: int, name: str, owner_id: int, archived: bool = False):
    self.id = id
    self.name = name
    self.owner_id = owner_id
    self.archived = archived
```

Required fields come first, defaulted fields last — Python syntax requires this, and `@dataclass` enforces it for you (lesson 05 explains how `kw_only` breaks the rule). The order in the generated signature is the order in which the fields were declared, because `__annotations__` is an ordered dict in Python 3.7+.

**Why is the annotation required? Why can't `@dataclass` just look at the class body?**

Because Python only adds `name = "default"` to `__dict__` — it has no way to know whether `name` is a field declaration or a regular class attribute (a constant, a method, a cached value, a descriptor). The annotation is the unambiguous field marker: it tells `@dataclass` "this name is a field, not an attribute". `name: str` is a field. `MAX_TICKETS = 1000` (no annotation) is a regular class attribute and `@dataclass` skips it. The rule is not arbitrary — it is the only way to disambiguate the two.

### Lines 6–7: The decorator and class signature

```python
@dataclass
class Project:
```

`@dataclass` is *not* `@dataclass()` — it is the bare form, which is the same as `@dataclass()` with every default accepted. You will sometimes see `@dataclass()` (with empty parens) in code that emphasises the decorator is parameterised; both forms are equivalent here, because every argument to `dataclass` is keyword-only and has a default.

**Why are all of `dataclass`'s arguments keyword-only?**

Because the CPython maintainers wanted to add new arguments later without breaking existing call sites. If `frozen` were positional, `@dataclass(True)` would mean frozen-or-not and adding a new positional slot would shift every existing caller's arguments. The `cls=None, /, *, ...` signature (note the `/` then `*`) pins `cls` as positional-only and everything else as keyword-only — the call surface is fixed forever and future arguments can be appended without breaking the world.

### Lines 8–11: Field declarations

```python
    id: int
    name: str
    owner_id: int
    archived: bool = False
```

Each annotated name is a field. The annotation `int`, `str`, `int`, `bool` is evaluated at class-body scope and stored in `__annotations__`. `@dataclass` does *not* use the annotation for validation, type-checking, or coercion — it stores the annotation on the `Field` object and copies it onto the generated `__init__` signature so static checkers (mypy, pyright) can read it. At runtime, `Project(id="oops")` succeeds — the string is assigned to `self.id` with no complaint. This is the central design choice of `@dataclass`: it is a code generator, not a validator. Lesson 07 contrasts this directly with Pydantic.

### Lines 13–18: Sanity check

```python
if __name__ == "__main__":
    p = Project(id=1, name="boardly MVP", owner_id=42)
    print(p)
    print(p == Project(id=1, name="boardly MVP", owner_id=42))
    print(p == Project(id=1, name="boardly MVP", owner_id=99))
    print(hash(p) if hasattr(p, "__hash__") and p.__hash__ else "unhashable")
```

`Project(id=1, name="boardly MVP", owner_id=42)` calls the generated `__init__`, which assigns the three fields. `archived` defaults to `False`. `print(p)` calls the generated `__repr__`, which produces `Project(id=1, name='boardly MVP', owner_id=42, archived=False)`. The `==` comparisons call the generated `__eq__`, which compares fields as a tuple — `(self.id, self.name, self.owner_id, self.archived) == (other.id, other.name, other.owner_id, other.archived)`. The two instances with identical fields compare equal; the third, with a different `owner_id`, does not. The `hash(p)` line checks hashability — which is where the `eq=True` / `order=False` default matters.

**Why does `@dataclass(eq=True)` set `__hash__ = None` by default?**

Because Python's data model says: if a class defines `__eq__` and does *not* define `__hash__`, then `__hash__` is set to `None` to make the instance unhashable. The rule exists because equal objects must hash equal — and if you wrote `__eq__` by hand but forgot `__hash__`, the default identity-based hash would be wrong, silently breaking `set` and `dict`. `@dataclass(eq=True)` follows this rule by default: it sets `__hash__ = None` (instance is unhashable), unless you pass `frozen=True` (lesson 03) or `unsafe_hash=True` (rarely needed — `unsafe_hash` exists for legacy interop, not for new code). So `p` in the example above is *unhashable*; the `print(hash(p) ...)` line prints `"unhashable"`.

## Execution Trace

```bash
$ python boardly/models/project.py
Project(id=1, name='boardly MVP', owner_id=42, archived=False)
True
False
unhashable
```

The first line is the generated `__repr__` — note the `=` between field name and value, the quotes around the string field (because `!r` was used), and the inclusion of `archived=False` even though we never set it. The second line is the field-tuple `__eq__` matching two identical instances. The third line is the same `__eq__` failing on a different `owner_id`. The fourth is the unhashable fallback we predicted.

## Common Mistakes

### Mistake 1: Missing annotation, no field generated

```python
@dataclass
class Project:
    id = 1
    name = "untitled"
```

**Symptom:** `Project()` succeeds with no arguments; `Project(id=1)` raises `TypeError: __init__() got an unexpected keyword argument 'id'`.
**Why:** `@dataclass` reads `__annotations__`, not `__dict__`. Without `id: int`, the line `id = 1` is a regular class attribute, not a field. The generated `__init__` takes no parameters.
**Fix:**

```python
@dataclass
class Project:
    id: int = 1
    name: str = "untitled"
```

### Mistake 2: Mutable default value

```python
@dataclass
class Project:
    id: int
    tags: list[str] = []
```

**Symptom:** `ValueError: mutable default <class 'list'> for field tags is not allowed: use default_factory`.
**Why:** `@dataclass` enforces the well-known Python footgun: mutable defaults are shared across instances, so mutating `Project(id=1).tags` would mutate every `Project` instance's `tags`. `@dataclass` catches this at decoration time and refuses to generate the class.
**Fix:** Use `field(default_factory=list)` — see [[06-dataclasses/02-field-and-Defaults]] for the full mechanism.

### Mistake 3: Treating `@dataclass` as Pydantic

```python
@dataclass
class Project:
    id: int
    name: str

p = Project(id="not-an-int", name="boardly")  # no error!
```

**Symptom:** No exception at construction; `p.id` is `"not-an-int"`, a string.
**Why:** `@dataclass` generates `__init__` that assigns each argument to the attribute verbatim. It does not validate types. The annotation is a *static* hint, not a runtime check.
**Fix:** If you need runtime validation, use `pydantic.BaseModel` (see [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]). If you keep `@dataclass`, add a `__post_init__` (lesson 08) or run mypy at CI time.

## Engineering Trade-Offs

**Decision:** Default `eq=True`, `order=False`, `frozen=False`, `slots=False`.
**Both sides:** `eq=True` is on by default because equality is a near-universal need and the generated `__eq__` is faster and more correct than what most engineers write by hand. `order=False` is off by default because ordering models by their fields is a rare need and turning it on generates `__lt__`/`__le__`/`__gt__`/`__ge__` you may never call. `frozen=False` and `slots=False` are off by default because the frozen and slots code paths trade flexibility for safety/perf — the trade is yours to commit to, not the module's.
**Commitment:** In `boardly`, models that represent *immutable domain facts* (`Project`, `Ticket`, `User`) use `@dataclass(frozen=True)`. Models that represent *mutable session state* (`BoardSession`, `DraftTicket`) use the bare `@dataclass`. Lesson 03 commits to frozen in detail.

## Exercises

1. **Exercise 1 — Add a field.** Add `description: str = ""` to `Project` after `archived`. Re-run the file. Verify the `__repr__` includes `description=''`. `Verify: python boardly/models/project.py`
2. **Exercise 2 — Inspect `__init__`.** Add `import inspect; print(inspect.signature(Project.__init__))` after the class. Run and observe the generated signature. `Verify: python -c "import inspect; from boardly.models.project import Project; print(inspect.signature(Project.__init__))"`
3. **Exercise 3 — Confirm hashability.** Construct two `Project` instances and put them in a set — `s = {p, Project(id=1, name='boardly MVP', owner_id=42)}`. Read the `TypeError` you get and explain why the rule exists. `Verify: python boardly/models/project.py`
4. **Exercise 4 — Read `__annotations__`.** After the class definition, `print(Project.__annotations__)` and `print(Project.__dict__.keys())`. Explain why `archived` appears in both but `id`, `name`, `owner_id` appear only in the annotations. `Verify: python boardly/models/project.py`
5. **Exercise 5 — Field-order matters.** Reverse the field order so `archived: bool = False` is the first line and `id: int` is the last. Read the `TypeError` and explain why a defaulted field cannot precede a required one — then preview the `kw_only` fix from lesson 08. `Verify: python boardly/models/project.py`

## Verification

```bash
$ python boardly/models/project.py
Project(id=1, name='boardly MVP', owner_id=42, archived=False)
True
False
unhashable
```

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — the type-hint vocabulary `@dataclass` depends on (annotations are fields).

## What's Next

[[06-dataclasses/02-field-and-Defaults]] — `field(default_factory=list)`, the `init`/`repr`/`compare`/`hash`/`metadata` knobs, and the FastAPI `Field` parallel. The mutable-default trap from Mistake 2 above is the canonical motivation for `field()`, and the lesson closes it. Three things to take with you:

- `@dataclass` reads `__annotations__`; annotations are fields, bare assignments are not.
- The default `eq=True` sets `__hash__ = None` — your instance is unhashable unless you also pass `frozen=True`.
- `@dataclass` is a code generator, not a validator. Runtime type-checking is not its job.

## Sources

- **`dataclasses` — Support for data classes** — https://docs.python.org/3/library/dataclasses.html — accessed 2026-10-23 — the canonical CPython reference for `@dataclass`, `field`, and every helper.
- **PEP 557 — Data Classes** — https://peps.python.org/pep-0557/ — accessed 2026-10-23 — the original PEP; the "Rationale" and "Specification" sections are still the clearest high-level explanation.
- **Python Data Model — `__hash__` and `__eq__` interaction** — https://docs.python.org/3/reference/datamodel.html#object.__hash__ — accessed 2026-10-23 — the rule that links `__eq__` definition to `__hash__ = None`.

## What We Learned

- You can now apply `@dataclass` to a typed class and predict every method Python generates.
- You can explain why `eq=True` is on by default and `order=False` is off — and what flips when you turn ordering on.
- You can distinguish `field()` from `= value` defaults and name the mutable-default trap that motivates `default_factory`.
- You can read the generated `__init__` signature from the class body and predict which arguments are required.
- You can diagnose the missing-annotation `TypeError` and explain *why* annotations are the field marker.
