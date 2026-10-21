---
title: "Lesson 07: TypedDict"
aliases:
 - TypedDict
 - 07-TypedDict
 - PEP 589
tags:
 - typing
 - typeddict
 - pep-589
 - json
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "40–55 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
related_lessons:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[01-typing/05-Protocol-Structural-Typing]]"
 - "[[01-typing/08-Literal-and-TypeGuard]]"
---

# Lesson 07: TypedDict

*`TypedDict` (PEP 589) — typed dictionaries for the JSON envelopes your API sends and receives. With `total=False`, `Required`/`NotRequired` (3.11+), and `ReadOnly` (3.13+, version-gated).*

**You're at the very beginning of Section 01's JSON-shape lesson.**

Every FastAPI request body is a JSON object. Every FastAPI response body is a JSON object. You can model these as `dict[str, Any]` (untyped), as `@dataclass` (typed but heavier), as a Pydantic `BaseModel` (typed and validating, but heavyweight), or as a `TypedDict` (typed and lightweight — a `dict` at runtime, with a type-checker-friendly shape). `TypedDict` is the right answer when you want the JSON shape to be a real `dict` (so `json.loads` produces one directly) but also type-checked at the field level. Take your time. Type every example. **This is how you learn.**

#typing #typeddict #json

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define** a `TypedDict` with required fields and use it as a parameter/return type.
2. **Apply** `total=False` to make every field optional, and explain when to use it versus `Required`/`NotRequired`.
3. **Use** `Required[T]` and `NotRequired[T]` (Python 3.11+) to mix required and optional fields in the same `TypedDict`.
4. **Read** the `__required_keys__` and `__optional_keys__` introspection attributes that frameworks (FastAPI, Pydantic) use.
5. **Version-gate** `ReadOnly[T]` (3.13+) and choose between `TypedDict`, `@dataclass`, and `Pydantic` for a given shape.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — `list[int]`, `dict[str, X]`.
- **[[01-typing/02-Annotated-and-Metadata]]** — `get_type_hints(..., include_extras=True)` — `TypedDict`'s fields are read with the same machinery.
- **About 40–55 minutes of focused time.**

**The most common gap: assuming `TypedDict` validates at runtime.**

Students arrive having seen `class TicketJSON(TypedDict): id: int; title: str` and assuming that creating `t = TicketJSON(id="oops", title=1)` will raise a `TypeError` at runtime. It will *not*. `TypedDict` is purely a *static* type — at runtime, `t` is just a `dict` (`isinstance(t, dict)` is `True`). The `id: int` annotation is enforced only by mypy; if you bypass mypy, you can put anything in the dict. This is the most dangerous `TypedDict` misconception. For runtime validation, use Pydantic (covered in `06-dataclasses`).

## The Problem

Here is the bug this lesson prevents. boardly's `create_ticket` endpoint accepts a JSON body like `{"title": "Fix login", "status": "open"}`. The first version of the codebase wrote:

```python
def create_ticket(payload: dict) -> Ticket:
    return Ticket(id=1, title=payload["title"], status=payload.get("status", "open"))
```

The `payload: dict` annotation tells mypy *nothing* — `payload` could be any `dict`, including `{"foo": "bar"}`, and `payload["title"]` would `KeyError` at runtime. mypy cannot catch this. Worse, the OpenAPI schema FastAPI generates for the body is "any object" because there is no shape to introspect.

`TypedDict` fixes this:

```python
class CreateTicket(TypedDict):
    title: str
    status: NotRequired[str]

def create_ticket(payload: CreateTicket) -> Ticket:
    return Ticket(id=1, title=payload["title"], status=payload.get("status", "open"))
```

Now mypy knows `payload["title"]` is `str` (not `Any`), `payload["status"]` may or may not exist, and FastAPI can introspect `CreateTicket` to generate the JSON Schema in the OpenAPI doc. `payload` is still a plain `dict` at runtime — `json.loads(body)` produces one directly, no conversion needed.

## The Code

```python
# boardly/typeddict_basics.py
"""boardly — TypedDict (PEP 589) for typing dicts that come from JSON."""
from typing import TypedDict, Required, NotRequired, get_type_hints
import sys

# --- The basic form: every key required, every value typed. ---
class TicketJSON(TypedDict):
    id: int
    title: str
    status: str

# total=False: every key becomes optional.
class PatchTicket(TypedDict, total=False):
    title: str
    status: str

# Mixed required + optional via Required/NotRequired (Python 3.11+).
class CreateTicket(TypedDict):
    title: str                        # implicitly required
    status: NotRequired[str]          # 3.11+: explicitly optional
    description: NotRequired[str]

# Nested TypedDicts.
class UserJSON(TypedDict):
    id: int
    name: str

class CommentJSON(TypedDict):
    id: int
    body: str
    author: UserJSON                  # nested TypedDict value

# A typical boardly route: takes a TypedDict body and returns a TypedDict.
def create_ticket(payload: CreateTicket) -> TicketJSON:
    return {
        "id": 1,
        "title": payload["title"],
        "status": payload.get("status", "open"),
    }

if __name__ == "__main__":
    print("TicketJSON hints:", get_type_hints(TicketJSON))
    print("PatchTicket hints:", get_type_hints(PatchTicket))
    print("PatchTicket __total__:", PatchTicket.__total__)
    print("PatchTicket __required_keys__:", PatchTicket.__required_keys__)
    print("PatchTicket __optional_keys__:", PatchTicket.__optional_keys__)
    print("CreateTicket __required_keys__:", CreateTicket.__required_keys__)
    print("CreateTicket __optional_keys__:", CreateTicket.__optional_keys__)
    print("CommentJSON hints:", get_type_hints(CommentJSON))

    t: TicketJSON = {"id": 1, "title": "Fix login", "status": "open"}
    print("create_ticket:", create_ticket({"title": "Fix login"}))
    print("create_ticket w/ status:", create_ticket({"title": "Fix login", "status": "closed"}))

    print("Python version:", sys.version_info)
```

## Line-by-Line Deep Dive

### Lines 1–5: Module header and imports

```python
# boardly/typeddict_basics.py
"""boardly — TypedDict (PEP 589) for typing dicts that come from JSON."""
from typing import TypedDict, Required, NotRequired, get_type_hints
import sys
```

`TypedDict` was added in Python 3.8 (PEP 589). `Required` and `NotRequired` were added in Python 3.11 (PEP 655). Both are stable in 3.12. `ReadOnly` was added in Python 3.13 (PEP 705) — it is **not** in 3.12 and must be version-gated; we mention it in the Trade-Offs but do not use it in the runnable code.

`TypedDict` is a *special form* — not a class in the usual sense. When you write `class TicketJSON(TypedDict): ...`, `TypedDict`'s metaclass intercepts the class body, walks the annotations, and produces a *new* class whose instances are plain `dict`. The `class TicketJSON(TypedDict):` is sugar for `TicketJSON = _TypedDictMeta("TicketJSON", (dict,), {...})`.

**Why is `TypedDict` not just a regular class with `dict`?**

Because the type-checker needs to track *which keys exist* and *what their types are*. A regular class with `dict` as a base would let you `TicketJSON()` and then set arbitrary keys; the type-checker could not enforce the schema. `TypedDict`'s metaclass produces a `dict`-like object whose *type-level* schema is fixed — you can only set the declared keys (statically). At runtime, of course, you can put anything in a `dict`, but the type-checker refuses.

### Lines 7–11: The basic `TypedDict` form

```python
# --- The basic form: every key required, every value typed. ---
class TicketJSON(TypedDict):
    id: int
    title: str
    status: str
```

Every field is required by default — `total=True` is the implicit default. `TicketJSON` says "a dict with `id: int`, `title: str`, `status: str` — all three required". mypy enforces at construction: `TicketJSON(id=1, title="x", status="open")` is fine; `TicketJSON(id=1, title="x")` is a type error (`status` missing).

At runtime, `TicketJSON(...)` is just `dict(...)` — `TicketJSON(id=1, title="x")` returns a plain `dict`. `isinstance(t, dict)` is `True`; `isinstance(t, TicketJSON)` is `False` (TypedDicts are not classes you can isinstance against — they are static types only). If you need runtime checks, use Pydantic.

**Why does `TicketJSON(id="oops")` not raise at runtime?**

Because `TypedDict` is static. At runtime, `TicketJSON(...)` is `dict(...)` — Python does not enforce the field types. `TicketJSON(id="oops", title="x", status="y")` produces `{"id": "oops", "title": "x", "status": "y"}` without complaint. mypy would flag it (`id` should be `int`, not `str`), but if you run the code without mypy, it just runs. This is the key trade-off: `TypedDict` is documentation and type-checker support, *not* runtime validation. Use Pydantic for runtime validation.

### Lines 13–16: `total=False` makes every key optional

```python
# total=False: every key becomes optional.
class PatchTicket(TypedDict, total=False):
    title: str
    status: str
```

`total=False` is a class-level keyword that flips the default: every field becomes optional. `PatchTicket` describes a dict that may have `title`, may have `status`, may have neither, may have both. mypy will allow `PatchTicket()` (empty dict), `PatchTicket(title="x")`, `PatchTicket(title="x", status="y")`. Accessing `payload["status"]` is flagged by mypy as `str | KeyError`-ish — you should use `payload.get("status", default)` to handle the absence.

The `__total__` attribute on the class is `False` after this — we print it to demonstrate.

**Why use `total=False` versus per-field `NotRequired`?**

Two reasons. (1) **Bulk**: when *most* fields are optional (e.g., a PATCH endpoint where every field is optional), `total=False` is one keyword versus annotating each field with `NotRequired`. (2) **Pre-3.11 compatibility**: `total=False` works in 3.8+; `NotRequired` requires 3.11. If you support 3.8–3.10, you must use `total=False`. The downside of `total=False` is that *all* fields are optional — you cannot mix required and optional within the same `TypedDict` without `Required`/`NotRequired`.

### Lines 18–23: Mixing required and optional with `NotRequired` (3.11+)

```python
# Mixed required + optional via Required/NotRequired (Python 3.11+).
class CreateTicket(TypedDict):
    title: str                        # implicitly required
    status: NotRequired[str]          # 3.11+: explicitly optional
    description: NotRequired[str]
```

`NotRequired[T]` marks a single field as optional within an otherwise-required TypedDict. `Required[T]` does the opposite — marks a single field as required within an otherwise-optional (`total=False`) TypedDict. The two together let you express *any* mix of required and optional in a single TypedDict.

`CreateTicket` has `title` required, `status` optional, `description` optional. The introspection attributes `__required_keys__` and `__optional_keys__` (which FastAPI reads!) report the split: `__required_keys__ == frozenset({"title"})` and `__optional_keys__ == frozenset({"status", "description"})`. We print both in `__main__` to demonstrate.

**Why are `Required` and `NotRequired` 3.11+?**

PEP 655 landed in 3.11 because the metaclass machinery needed to track per-field optionality — the existing `__required_keys__` and `__optional_keys__` had to be populated based on the annotations, not just the class-level `total=` keyword. For 3.8–3.10, the only way to mix required and optional was to use *two* TypedDicts — a required base class and an optional subclass with `total=False` (mypy supports the inheritance merge). It works, but `Required`/`NotRequired` is cleaner.

### Lines 25–35: Nested `TypedDict`s

```python
# Nested TypedDicts.
class UserJSON(TypedDict):
    id: int
    name: str

class CommentJSON(TypedDict):
    id: int
    body: str
    author: UserJSON                  # nested TypedDict value
```

A `TypedDict` field can itself be a `TypedDict` — `CommentJSON`'s `author` field is `UserJSON`. mypy tracks the nesting: `comment["author"]["name"]` is statically `str`. The runtime object is just a nested dict-of-dicts. JSON naturally maps to nested `TypedDict`s because JSON objects are dicts.

The `get_type_hints(CommentJSON)` output will show `'author': <class 'UserJSON'>` — the field's type is the `UserJSON` TypedDict, which is itself a `dict` subclass at runtime. Pydantic and FastAPI can introspect this recursively to generate nested JSON Schema.

**Why nest TypedDicts instead of using `dict[str, dict[str, int]]`?**

Because the inner `dict[str, dict[str, int]]` form has no field names — mypy cannot track `comment["author"]["name"]` versus `comment["author"]["email"]`. Nested TypedDicts give the inner dict a *named shape*, so the type-checker tracks every key.

### Lines 37–43: A boardly route using the TypedDict

```python
# A typical boardly route: takes a TypedDict body and returns a TypedDict.
def create_ticket(payload: CreateTicket) -> TicketJSON:
    return {
        "id": 1,
        "title": payload["title"],
        "status": payload.get("status", "open"),
    }
```

A real FastAPI route would look exactly like this — `def create_ticket(payload: CreateTicket) -> TicketJSON`. mypy knows `payload["title"]` is `str`, so the returned dict's `"title"` value is `str`. `payload.get("status", "open")` is `str` (because `"open"` is `str`). The returned dict matches the `TicketJSON` schema — `id: int`, `title: str`, `status: str`.

FastAPI would introspect `CreateTicket` to generate the request-body JSON Schema and `TicketJSON` to generate the response-body JSON Schema. The OpenAPI doc is built automatically from the TypedDicts. Pydantic v2 supports TypedDicts natively — you can write a Pydantic model *from* a TypedDict using `pydantic.TypeAdapter(CreateTicket)`.

**Why use TypedDict over a Pydantic model for the response?**

Two reasons. (1) **Performance**: Pydantic validates on construction. For a response you have already validated, you do not need to revalidate on output — you just want to serialise. A TypedDict response skips the validation overhead. (2) **Zero-copy**: a TypedDict is a `dict`; serialising to JSON is direct. A Pydantic model has its own internal structure that needs converting to a dict before serialisation. For high-throughput endpoints, TypedDict responses are noticeably faster. The boardly project uses TypedDict for *responses* (where input is already validated upstream) and Pydantic for *request bodies* (where validation is the point).

### Lines 45–58: The `__main__` block

```python
if __name__ == "__main__":
    print("TicketJSON hints:", get_type_hints(TicketJSON))
    print("PatchTicket hints:", get_type_hints(PatchTicket))
    print("PatchTicket __total__:", PatchTicket.__total__)
    print("PatchTicket __required_keys__:", PatchTicket.__required_keys__)
    print("PatchTicket __optional_keys__:", PatchTicket.__optional_keys__)
    print("CreateTicket __required_keys__:", CreateTicket.__required_keys__)
    print("CreateTicket __optional_keys__:", CreateTicket.__optional_keys__)
    print("CommentJSON hints:", get_type_hints(CommentJSON))

    t: TicketJSON = {"id": 1, "title": "Fix login", "status": "open"}
    print("create_ticket:", create_ticket({"title": "Fix login"}))
    print("create_ticket w/ status:", create_ticket({"title": "Fix login", "status": "closed"}))

    print("Python version:", sys.version_info)
```

The introspection prints are the senior moment. `__total__` is `False` for `PatchTicket` (every key optional). `__required_keys__` is `frozenset()` for `PatchTicket` (no required keys) and `frozenset({"title"})` for `CreateTicket` (only `title` required). `__optional_keys__` is `frozenset({"title", "status"})` for `PatchTicket` (both optional) and `frozenset({"status", "description"})` for `CreateTicket`. These frozensets are what frameworks read to generate JSON Schema and to decide which fields to require.

The `CommentJSON hints` print shows `author: UserJSON` — the nested TypedDict is preserved by `get_type_hints` as a class reference. Pydantic v2 walks this recursively.

## Execution Trace

```bash
$ python boardly/typeddict_basics.py
TicketJSON hints: {'id': <class 'int'>, 'title': <class 'str'>, 'status': <class 'str'>}
PatchTicket hints: {'title': <class 'str'>, 'status': <class 'str'>}
PatchTicket __total__: False
PatchTicket __required_keys__: frozenset()
PatchTicket __optional_keys__: frozenset({'title', 'status'})
CreateTicket __required_keys__: frozenset({'title'})
CreateTicket __optional_keys__: frozenset({'description', 'status'})
CommentJSON hints: {'id': <class 'int'>, 'body': <class 'str'>, 'author': <class '__main__.UserJSON'>}
create_ticket: {'id': 1, 'title': 'Fix login', 'status': 'open'}
create_ticket w/ status: {'id': 1, 'title': 'Fix login', 'status': 'closed'}
Python version: sys.version_info(major=3, minor=12, micro=15, releaselevel='final', serial=0)
```

Three things to verify. First, `PatchTicket __total__: False` — the keyword was applied. Second, the `__required_keys__` / `__optional_keys__` split reflects the field annotations (PatchTicket has nothing required; CreateTicket has only `title` required). Third, the `CommentJSON hints` shows the nested `UserJSON` class reference — nesting is preserved.

## Common Mistakes

### Mistake 1: Assuming `TypedDict` validates at runtime

```python
class T(TypedDict):
    id: int

t = T(id="oops", title="extra")  # ← mypy flags; runtime: silently OK
print(t)  # {'id': 'oops', 'title': 'extra'}
```

**Symptom:** The code runs without error and produces `{'id': 'oops', 'title': 'extra'}` — even though `id` should be `int` and `title` is not a declared field.
**Why:** `TypedDict` is purely static. At runtime, `T(...)` is `dict(...)` — Python does not enforce the field types or the field set.
**Fix:** If you need runtime validation, use Pydantic (`pydantic.TypeAdapter(T)` gives you a runtime validator). If you only need static typing and trust your data source (e.g., a controlled internal API), `TypedDict` is fine — but mypy must run in CI.

### Mistake 2: Using `Optional[T]` to mean "optional key"

```python
class T(TypedDict):
    id: int
    title: Optional[str]  # ← WRONG; this is "title is str | None" not "title is optional"
```

**Symptom:** mypy still requires `title` at construction — `Optional[T]` does not make a *key* optional; it makes the *value* type `T | None`.
**Why:** `Optional[T]` is a value-level union with `None`. It does not affect the *key's* presence. To make a key optional, use `NotRequired[T]` (3.11+) or `total=False` for the whole class.
**Fix:**

```python
class T(TypedDict):
    id: int
    title: NotRequired[str]  # ← key is optional; value is str (not None) when present
```

### Mistake 3: Inheriting two `TypedDict`s and being surprised by the merge

```python
class Base(TypedDict):
    id: int

class Patch(Base, total=False):
    id: NotRequired[int]  # ← overrides Base's required id to optional
    title: str
```

**Symptom:** mypy allows you to *re-declare* `id` as `NotRequired[int]` in the subclass, but the resulting `__required_keys__` may or may not include `id` depending on mypy's inheritance-merge rules. Different mypy versions have resolved this differently.
**Why:** `TypedDict` inheritance merges keys. Re-declaring a key with different optionality in a subclass is supported but subtle — `__required_keys__` reflects the *child*'s override.
**Fix:** Be explicit. Use a single `TypedDict` with explicit `Required`/`NotRequired` markers (3.11+) rather than inheritance, when you can. Inheritance is still useful for shared base fields, but re-declaring optionality in subclasses is fragile.

## Engineering Trade-Offs

**Decision:** Use `TypedDict` for response models and for unvalidated request models; use Pydantic `BaseModel` for validated request models; use `@dataclass` for internal value objects (not for JSON).
**Both sides:** `TypedDict` is the fastest (a `dict` at runtime), but does not validate. Pydantic validates but has construction overhead. `@dataclass` is a typed value object but its `asdict()` produces a dict with field-name keys, not JSON camelCase — it is not a JSON shape directly. Each tool has its lane.
**Commitment:** boardly uses `TypedDict` for response envelopes (`TicketJSON`, `UserJSON`), Pydantic for request bodies (`CreateTicketRequest` — validation is the point), and `@dataclass` for internal domain objects (`Ticket`, `User`). The three tools compose: a Pydantic request body validates, the handler constructs a `@dataclass` from it, and the response is serialised via a `TypedDict` constructed from the `@dataclass`'s fields.

**Python 3.13+: `ReadOnly[T]` (PEP 705)**
`ReadOnly[T]` marks a `TypedDict` field as read-only at the type level — after construction, mypy refuses assignments to that field. It is **not available in Python 3.12** (it is 3.13+). To use it in a 3.12-target codebase, import from `typing_extensions`:

```python
try:
    from typing import ReadOnly  # 3.13+
except ImportError:
    from typing_extensions import ReadOnly  # backport for 3.12
```

boardly does not use `ReadOnly` because we target 3.12 natively; if you need cross-version read-only semantics, the `typing_extensions` backport is the answer.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/typeddict_basics.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/typeddict_basics.py`
2. **Exercise 2 — Add an optional `tags` field.** Add `tags: NotRequired[list[str]]` to `CreateTicket` and update `create_ticket` to default it to `[]`. Verify the `__optional_keys__` includes `tags`. `Verify: python -c "from boardly.typeddict_basics import CreateTicket; print('tags' in CreateTicket.__optional_keys__)"`
3. **Exercise 3 — Add a nested list field.** Add `comments: NotRequired[list[CommentJSON]]` to a new `TicketDetailJSON(TypedDict)` and confirm the nested-list-of-TypedDicts form works in mypy. `Verify: python -c "from boardly.typeddict_basics import TicketDetailJSON; from typing import get_type_hints; print(get_type_hints(TicketDetailJSON)['comments'])"`
4. **Exercise 4 — Use `total=False` for a PATCH.** Define `class PatchTicketJSON(TypedDict, total=False): title: str; status: str; tags: list[str]` and a `patch_ticket(id: int, patch: PatchTicketJSON) -> TicketJSON` that updates only the supplied fields. `Verify: python -c "from boardly.typeddict_basics import patch_ticket; print(patch_ticket(1, {'title': 'new'})['title'])"`
5. **Exercise 5 — Compare with Pydantic.** Use `pydantic.TypeAdapter(CreateTicket)` (or `from pydantic import TypeAdapter; ta = TypeAdapter(CreateTicket)`) to construct a validator from the TypedDict. Confirm `ta.validate_python({"title": "x"})` succeeds and `ta.validate_python({})` raises a `ValidationError`. Document when you would use each. `Verify: python -c "from pydantic import TypeAdapter; from boardly.typeddict_basics import CreateTicket; ta = TypeAdapter(CreateTicket); print(ta.validate_python({'title': 'x'}))"`

## Verification

```bash
$ python boardly/typeddict_basics.py
TicketJSON hints: {'id': <class 'int'>, 'title': <class 'str'>, 'status': <class 'str'>}
PatchTicket hints: {'title': <class 'str'>, 'status': <class 'str'>}
PatchTicket __total__: False
PatchTicket __required_keys__: frozenset()
PatchTicket __optional_keys__: frozenset({'title', 'status'})
CreateTicket __required_keys__: frozenset({'title'})
CreateTicket __optional_keys__: frozenset({'description', 'status'})
CommentJSON hints: {'id': <class 'int'>, 'body': <class 'str'>, 'author': <class '__main__.UserJSON'>}
create_ticket: {'id': 1, 'title': 'Fix login', 'status': 'open'}
create_ticket w/ status: {'id': 1, 'title': 'Fix login', 'status': 'closed'}
Python version: sys.version_info(major=3, minor=12, micro=15, releaselevel='final', serial=0)
```

If `PatchTicket __required_keys__: frozenset()` (empty) and `CreateTicket __required_keys__: frozenset({'title'})` (only `title`), the two optionality mechanisms (`total=False` and `NotRequired`) are both working and introspectable.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `dict[str, X]`. `TypedDict` is `dict` with named, typed keys.
- [[01-typing/02-Annotated-and-Metadata]] — `get_type_hints(include_extras=True)`. `TypedDict`'s fields are read with the same machinery.

## What's Next

[[01-typing/08-Literal-and-TypeGuard]] — `Literal["active", "archived"]` (PEP 586) for type-checking string values that come from a fixed set, and `TypeGuard[T]` (3.10+, PEP 642) for narrowing a value's type after a runtime check. Three things to look for in lesson 08:

- `Literal["active", "archived"]` for ticket status fields — narrow `str` to one of two strings.
- `TypeGuard[int]` on a function that returns `bool` — mypy narrows the input type if the function returns `True`.
- `TypeIs[T]` (3.13+, version-gated) — the stricter, symmetric version of `TypeGuard`.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.TypedDict — CPython reference** — https://docs.python.org/3/library/typing.html#typing.TypedDict — accessed 2026-10-23 — the canonical API for `TypedDict`, `total=False`, `Required`, `NotRequired`, and `__required_keys__`/`__optional_keys__`.
- **PEP 589 — TypedDict** — https://peps.python.org/pep-0589/ — accessed 2026-10-23 — the original TypedDict PEP (3.8). Read the "Usage" section for the JSON-shape use case.
- **PEP 655 — Required and NotRequired in TypedDict** — https://peps.python.org/pep-0655/ — accessed 2026-10-23 — the PEP that introduced `Required`/`NotRequired` in 3.11.
- **PEP 705 — ReadOnly for TypedDict** — https://peps.python.org/pep-0705/ — accessed 2026-10-23 — the PEP that introduced `ReadOnly` in 3.13 (version-gated; not in 3.12).

## What We Learned

- `class T(TypedDict): id: int; title: str` declares a dict type with named, typed, *required* keys — enforced statically, not at runtime.
- `total=False` makes every key in a TypedDict optional.
- `Required[T]` and `NotRequired[T]` (3.11+) let you mix required and optional keys in a single TypedDict.
- `__required_keys__` and `__optional_keys__` are frozensets of key names — frameworks (FastAPI, Pydantic) read these to generate JSON Schema.
- `TypedDict` fields can be nested `TypedDict`s for hierarchical JSON shapes.
- `TypedDict` is the right choice for response shapes (unvalidated, fast); Pydantic is the right choice for request bodies (validated, slower); `@dataclass` is for internal value objects.
- `ReadOnly[T]` (PEP 705, 3.13+) is not in 3.12 — use `typing_extensions.ReadOnly` if you need it cross-version.
