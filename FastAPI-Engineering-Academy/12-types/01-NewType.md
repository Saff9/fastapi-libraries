---
title: "Lesson 01: NewType"
aliases:
 - NewType
 - typing.NewType
 - nominal typing
tags:
 - types
 - typing
 - newtype
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/02-Annotated-and-Metadata]]"
related_lessons:
 - "[[12-types/02-SimpleNamespace]]"
 - "[[12-types/03-GenericAlias-and-UnionType]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
first_taught_in: "12-types/01-NewType"
---

# Lesson 01: NewType

*`UserId = NewType("UserId", int)` — the one-line construct that makes mypy distinguish a user id from a project id even though, at runtime, both are just `int` and `UserId(5) is 5`.*

**You're at the very beginning of Section 12.**

`types` is the standard-library home for the runtime type objects Python itself is built from — the types behind `def`, `import`, `list[int]`, and a bound method. The first construct we meet, `NewType`, is the one that lives in `typing` (it is a static-only concept) but is most naturally paired with the runtime-type vocabulary you will meet in the rest of this section. `NewType` is a one-liner that gives you nominal typing for free: mypy treats `UserId` and `ProjectId` as incompatible types, but at runtime `UserId(5)` *is* the integer `5` — same object, same arithmetic, zero cost. This lesson shows you when that trade is the right one to make. Take your time. Type every example. **This is how you learn.**

#types #typing #newtype #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare** a `NewType` — `UserId = NewType("UserId", int)` — and predict that `UserId(5) is 5` evaluates `True` at runtime.
2. **Explain** the "static-only concept" framing — `NewType` returns a callable that is identity at runtime, and only static checkers (mypy, pyright) treat it as distinct from `int`.
3. **Read** a `NewType` object's introspection attributes — `.__name__`, `.__supertype__`, `type(...).__name__ == "NewType"`.
4. **Articulate** when `NewType` beats `int` in an API contract — and when it loses to a `dataclass` or an `Annotated[int, Field(...)]` validation layer.
5. **Diagnose** the most common `NewType` confusion — expecting runtime validation and being surprised that `UserId(-1)` constructs silently.

## Prerequisites

Before starting, you need:

- **Type hints basics** — you must be comfortable with `def f(x: int) -> str:` and `list[int]`. See [[01-typing/01-Type-Hints-Basics]] for the canonical introduction.
- **The `Annotated` metadata primitive** — `NewType` is often paired with `Annotated` to attach a *runtime* validator. See [[01-typing/02-Annotated-and-Metadata]] for the canonical lesson.
- **About 20–30 minutes of focused time.**

**The most common gap: expecting `NewType` to validate at runtime.**

Students arrive having read that `NewType("UserId", int)` "makes UserId distinct from int". They expect `UserId("not-an-int")` to raise, `UserId(-1)` to raise, and a function annotated `def f(uid: UserId) -> ...` to refuse a bare `int` at runtime. None of this happens. `NewType` is a *static-only* concept — the runtime callable is `lambda x: x`, identity, no checks. Validation, if you want it, must live in a different layer (`Annotated[int, Field(ge=0)]`, a Pydantic model, a custom dependency). The whole point of `NewType` is that it is the *zero-cost* way to make two `int`-typed things distinct *to the type-checker*. If you want zero-cost, you accept zero-validation. If you want validation, you pay for it elsewhere.

## The Problem

Here is the bug. `boardly` has three resources — `User`, `Project`, `Ticket` — and every one of them has an integer id. A naive codebase writes:

```python
# boardly/api/bad_ids.py — the bad old days
def fetch_user(user_id: int) -> dict: ...
def fetch_project(project_id: int) -> dict: ...
def fetch_ticket(ticket_id: int) -> dict: ...

# A caller (or you, at 2am, mid-incident) writes:
fetch_user(project_id)   # silent bug — fetches a user that does not exist
fetch_ticket(user_id)    # silent bug — fetches a ticket that does not exist
```

The type system *cannot* catch this. Every id is `int`. mypy sees `fetch_user(int)` and a `project_id: int` and shrugs: "they are both `int`, looks fine to me". The bug ships. The customer sees "user not found" when they asked for their project. The incident report says "we passed a `project_id` where a `user_id` was expected" — and the fix is "use better variable names". Better variable names are good; better *types* are better.

`NewType` is the standard library's answer:

```python
UserId = NewType("UserId", int)
ProjectId = NewType("ProjectId", int)

def fetch_user(user_id: UserId) -> dict: ...
def fetch_project(project_id: ProjectId) -> dict: ...

# Now the bug from above is a mypy error, not a runtime incident:
fetch_user(project_id)  # mypy: Argument 1 to "fetch_user" has incompatible type "ProjectId"; expected "UserId"
```

`NewType` exists because some bugs are *type* bugs — they are caused by passing the wrong kind of value, not the wrong shape of value. For those bugs, you do not need runtime validation (you already have a correct value), you need the type system to refuse to let you mix them up. That is exactly what `NewType` does, at zero runtime cost.

## The Code

```python
# boardly/models/ids.py
"""boardly — NewType for nominal ID typing (static-only, zero runtime cost)."""
from typing import NewType

# Nominal-distinction IDs — same runtime type (int), distinct static types.
UserId = NewType("UserId", int)
ProjectId = NewType("ProjectId", int)
TicketId = NewType("TicketId", int)

# A function that should only accept a UserId — not a ProjectId, not a bare int.
def fetch_user(user_id: UserId) -> dict:
    return {"id": user_id, "name": "Ada Lovelace"}

# Construction is identity at runtime: UserId(5) IS the int 5 — same object.
got = UserId(5)
expected = 5
print("got:", got, "type(got).__name__:", type(got).__name__)
print("got is expected:", got is expected)
print("isinstance(got, int):", isinstance(got, int))

# Arithmetic still works — runtime is plain int.
print("UserId(42) + 1:", UserId(42) + 1)

# You CAN pass a bare int at runtime — NewType does not validate.
# mypy would reject this; CPython will not.
print("fetch_user(99):", fetch_user(99))

# You CAN mix UserId and ProjectId at runtime — they're all just ints.
p = ProjectId(7)
print("fetch_user(ProjectId(7)):", fetch_user(p))

# Inspecting the NewType object itself.
print("\n--- inspecting the NewType object ---")
print("type(UserId).__name__:", type(UserId).__name__)
print("UserId.__name__:", UserId.__name__)
print("UserId.__supertype__:", UserId.__supertype__)
print("callable(UserId):", callable(UserId))

# Why no validation is the point: a validation layer belongs elsewhere.
bad = UserId(-1)
print("\nbad (negative) id constructed at runtime:", bad)
```

## Line-by-Line Deep Dive

### Lines 1–8: The `NewType` declarations

```python
# boardly/models/ids.py
"""boardly — NewType for nominal ID typing (static-only, zero runtime cost)."""
from typing import NewType

# Nominal-distinction IDs — same runtime type (int), distinct static types.
UserId = NewType("UserId", int)
ProjectId = NewType("ProjectId", int)
TicketId = NewType("TicketId", int)
```

`NewType("UserId", int)` constructs and returns a `typing.NewType` object. Three things happen. (1) The first argument, the string `"UserId"`, becomes `.__name__` on the object — it is the label mypy and `repr` use. (2) The second argument, the class `int`, becomes `.__supertype__` — it is the type the NewType "wraps". (3) The object is *callable*: calling `UserId(5)` returns `5`, unchanged.

The variable name (`UserId`) and the string (`"UserId"`) are independent — but the convention is to keep them identical. Mismatching them (`X = NewType("Y", int)`) is legal; mypy will refer to `Y` in error messages, which the reader cannot find. The same "always name the NewType with the same identifier" rule applies as for `TypeVar` (lesson [[01-typing/03-TypeVar-and-Generics]]).

**Why is `NewType` not a class — why is it an object you assign to a module-level variable?**

Because `NewType` is a *static-only* concept. At runtime, the only thing `UserId(5)` does is return `5`. mypy reads the source file, sees `UserId = NewType("UserId", int)`, records "the name `UserId` is a nominal-distinct alias of `int`" in its type tables, and from then on treats `UserId` as incompatible with `int`. The runtime has no such tables — it does not need them, because the runtime is the identity function. Making `NewType` a class would imply runtime semantics that do not exist; making it a callable object that returns its argument exactly captures what is actually happening.

### Lines 10–12: The function annotated with `UserId`

```python
# A function that should only accept a UserId — not a ProjectId, not a bare int.
def fetch_user(user_id: UserId) -> dict:
    return {"id": user_id, "name": "Ada Lovelace"}
```

The annotation `user_id: UserId` is what makes this work. mypy sees the annotation, looks up `UserId` in its tables, finds it is a NewType with supertype `int`, and records that the parameter accepts only the type `UserId` — *not* `int`, *not* `ProjectId`. At a call site `fetch_user(some_value)`, mypy checks that `some_value`'s static type is `UserId`. A bare `int` literal is rejected; a `ProjectId` value is rejected. The body of `fetch_user` treats `user_id` as an `int` (it can — the supertype is `int`, so mypy allows every `int` operation on a `UserId`).

**Why does mypy let the function body use `user_id` as an `int` but refuse a bare `int` at the call site?**

Because the supertype relationship is one-way for the type-checker. `UserId` *is-a* `int` (the supertype is `int`), so anything you can do to an `int` you can do to a `UserId`. But `int` is *not-a* `UserId` — the relationship is not symmetric. The runtime enforces nothing; mypy's checker enforces the one-way relationship. This is the entire nominal-typing point: `UserId` is a *name* the type-checker uses to distinguish a value, but the value *is* an `int` and is usable as one. The same one-way relationship is what makes subclassing work — `Cat` is-an `Animal`, but `Animal` is not a `Cat`.

### Lines 14–18: The zero-cost runtime demonstration

```python
# Construction is identity at runtime: UserId(5) IS the int 5 — same object.
got = UserId(5)
expected = 5
print("got:", got, "type(got).__name__:", type(got).__name__)
print("got is expected:", got is expected)
print("isinstance(got, int):", isinstance(got, int))
```

Three things to verify. (1) `type(got).__name__` is `"int"` — the object *is* a plain `int`, not some `UserId`-flavoured int. There is no `UserId` class at runtime. (2) `got is expected` is `True` — `UserId(5)` and the literal `5` are *the same object*, not just equal. (For small ints, CPython caches them in a singleton table, so `5` is always the same `int` object; `UserId(5)` returns that same singleton.) (3) `isinstance(got, int)` is `True` — `UserId` has zero runtime footprint. There is no `isinstance(x, UserId)` you can write; that would raise `TypeError: isinstance() arg 2 must be a type, a tuple of types, or a union`. The runtime does not know `UserId` is a type at all.

**Why does CPython emit a `SyntaxWarning` when you write `UserId(5) is 5`?**

Because comparing an integer to an integer literal with `is` is almost always a bug — `is` is for identity, not equality, and integer identity is implementation-dependent (only small ints are cached; large ints are not). CPython 3.12 warns you to use `==` instead. In our demo we deliberately assign the literal to a variable (`expected = 5`) before the `is` comparison, which suppresses the warning — the headline fact we want to demonstrate is that `UserId(5) is 5` returns `True`, but writing it as `UserId(5) is 5` literally in your source triggers the linter. The variable trick is the clean way to show the same fact.

### Lines 20–21: Arithmetic still works

```python
# Arithmetic still works — runtime is plain int.
print("UserId(42) + 1:", UserId(42) + 1)
```

`UserId(42) + 1` evaluates to `43`. mypy allows this in the body of a function annotated `UserId` because the supertype is `int` and `int + int` is `int`. Outside such a body, mypy would actually complain that `UserId(42) + 1` "returns `int`, not `UserId`" — `+` on a `UserId` produces an `int`, not a `UserId`. This is sometimes surprising: arithmetic on a `NewType` value *drops* the nominal type. If you need to construct a `UserId` from an arithmetic result, you have to re-wrap: `UserId(UserId(42) + 1)`.

### Lines 23–28: The "no validation" demonstration

```python
# You CAN pass a bare int at runtime — NewType does not validate.
# mypy would reject this; CPython will not.
print("fetch_user(99):", fetch_user(99))

# You CAN mix UserId and ProjectId at runtime — they're all just ints.
p = ProjectId(7)
print("fetch_user(ProjectId(7)):", fetch_user(p))
```

Both calls succeed at runtime and return `{"id": 99, ...}` and `{"id": 7, ...}` respectively. mypy, if you ran it over this file, would flag line 24 (`fetch_user(99)`) with `Argument 1 to "fetch_user" has incompatible type "int"; expected "UserId"` and line 28 (`fetch_user(p)`) with `Argument 1 to "fetch_user" has incompatible type "ProjectId"; expected "UserId"`. CPython does not. The gap is the lesson: `NewType` is enforced *only* by static checkers. A codebase that runs but never type-checks will let both bugs through silently. If you want runtime enforcement, you need a different layer (see the Trade-Offs section).

**Why does Python not check at runtime when it has the type information right there?**

Two reasons. (1) Performance — adding a runtime `isinstance` check on every annotated function call would slow Python by a measurable factor, and the whole design of PEP 484 was "types are static; runtime is unchanged". (2) The annotations are *not actually present at runtime* in the form you wrote them — `from __future__ import annotations` (PEP 563) stringifies them, and even without that, `UserId` is a module-level variable that resolves to the identity callable, not a type. The runtime literally has no information to enforce. The static checker runs before the program does and can see the source; the runtime cannot.

### Lines 30–35: Introspecting the `NewType` object itself

```python
# Inspecting the NewType object itself.
print("\n--- inspecting the NewType object ---")
print("type(UserId).__name__:", type(UserId).__name__)
print("UserId.__name__:", UserId.__name__)
print("UserId.__supertype__:", UserId.__supertype__)
print("callable(UserId):", callable(UserId))
```

Four facts: `type(UserId).__name__` is `"NewType"` (the class is `typing.NewType`, a single class for every NewType you ever declare); `UserId.__name__` is `"UserId"` (the string you passed); `UserId.__supertype__` is `<class 'int'>` (the type you passed); `callable(UserId)` is `True` (calling it is the identity). These four attributes are how you programmatically inspect a `NewType` at runtime — for instance, a documentation generator that wants to render `UserId (an int)` in a sidebar would read `.__supertype__` and `.__name__`. There is no `isinstance(x, UserId)` you can write — that is the static/runtime split made concrete.

### Lines 37–39: The negative-id demonstration

```python
# Why no validation is the point: a validation layer belongs elsewhere.
bad = UserId(-1)
print("\nbad (negative) id constructed at runtime:", bad)
```

`UserId(-1)` returns `-1`. No validation. A user id of `-1` is nonsense, but `NewType` does not care. If you want to refuse negative ids, you have three options: (a) write an `Annotated[int, Field(ge=0)]` and let Pydantic enforce at the request boundary (the canonical FastAPI pattern, lesson [[01-typing/02-Annotated-and-Metadata]]); (b) write a `dataclass` with a `__post_init__` validator (lesson [[06-dataclasses/01-dataclass-Basics]]); (c) write a runtime check in the function body (`if user_id < 0: raise ValueError(...)`). `NewType` is none of these — it is the *zero-cost* layer that does not validate, deliberately, so that you can pay the validation cost only at the boundaries where it matters.

## Execution Trace

```bash
$ python boardly/models/ids.py
got: 5 type(got).__name__: int
got is expected: True
isinstance(got, int): True
UserId(42) + 1: 43
fetch_user(99): {'id': 99, 'name': 'Ada Lovelace'}
fetch_user(ProjectId(7)): {'id': 7, 'name': 'Ada Lovelace'}

--- inspecting the NewType object ---
type(UserId).__name__: NewType
UserId.__name__: UserId
UserId.__supertype__: <class 'int'>
callable(UserId): True

bad (negative) id constructed at runtime: -1
```

Three things to verify in the trace. First, `got is expected` is `True` — the headline fact: `UserId(5)` is literally the integer `5`. Second, `fetch_user(99)` and `fetch_user(ProjectId(7))` both succeed at runtime — the static-only enforcement is not visible here because CPython does not enforce it. Run `mypy boardly/models/ids.py` separately to see the static errors. Third, the introspection block shows `type(UserId).__name__ == "NewType"` and `UserId.__supertype__ == int` — these are the runtime facts you can rely on.

## Common Mistakes

### Mistake 1: Expecting runtime validation

```python
UserId = NewType("UserId", int)
def create_user(uid: UserId) -> None: ...
create_user(-1)   # student expects ValueError; gets nothing
create_user("not-an-int")  # student expects TypeError; gets nothing
```

**Symptom:** "I added `NewType` and bad values still get through — NewType doesn't work."
**Why:** `NewType` is a static-only concept. The runtime callable is the identity function. mypy catches `create_user(-1)` if the literal is in a checked file; CPython does not.
**Fix:** Add a validation layer where you need it. For API boundaries, use `Annotated[int, Field(ge=0)]` and Pydantic (lesson [[01-typing/02-Annotated-and-Metadata]]). For internal calls, write an explicit `if uid < 0: raise ValueError(...)`. `NewType` is the *naming* layer, not the *validation* layer.

### Mistake 2: Subclassing a `NewType`

```python
UserId = NewType("UserId", int)
class AdminUser(UserId):   # TypeError: cannot subclass NewType
    ...
```

**Symptom:** `TypeError: Cannot subclass an instance of NewType. Perhaps you were looking for: `AdminUser = NewType('AdminUser', UserId)`` at class-definition time.
**Why:** `NewType` is not a class — it is a callable object. You cannot subclass a non-class. CPython's error message is explicit about this and even suggests the correct form (`AdminUser = NewType('AdminUser', UserId)`).
**Fix:** Use composition. Define `AdminUser` as a separate `NewType("AdminUser", UserId)` (which is itself a `NewType("AdminUser", int)` in identity terms), or as a `@dataclass` with a `user_id: UserId` field. If you genuinely need a subclass relationship, use real classes (`class AdminUser(User): ...`) and accept the runtime cost.

### Mistake 3: Trying `isinstance(x, UserId)`

```python
UserId = NewType("UserId", int)
def is_user_id(x: object) -> bool:
    return isinstance(x, UserId)  # TypeError at call time
```

**Symptom:** `TypeError: isinstance() arg 2 must be a type, a tuple of types, or a union` — at the call site.
**Why:** `UserId` is a `typing.NewType` object, not a class. `isinstance` requires a class (or tuple of classes, or a union of them) as its second argument. `NewType` is none of those — it is a callable object with `__name__` and `__supertype__` attributes, but it is not itself a class.
**Fix:** Use `isinstance(x, int)` and trust the static checker to ensure only `UserId`-typed values reach the check. If you genuinely need to discriminate `UserId` from `int` at runtime, you need a wrapper class (a `@dataclass` or a Pydantic model) — `NewType` cannot do this by design.

## Engineering Trade-Offs

**Decision:** Use `NewType` for nominal-distinction ids (`UserId`, `ProjectId`, `TicketId`) and rely on a *separate* validation layer (`Annotated[int, Field(ge=0)]` + Pydantic at the FastAPI request boundary) for value validation.
**Both sides:** The alternative is a real class — `@dataclass class UserId: value: int`. This gives you runtime validation (in `__post_init__`), `isinstance` support, and a place to hang methods. The cost is per-id object overhead (an allocation, a pointer indirection), more code, and an API surface that callers must learn (`UserId(value=int(...))` vs `UserId(int(...))`). For ids that are *passive* (you never call methods on them, only pass them around), `NewType` is strictly better: zero cost, zero ceremony, full type-checker support.
**Commitment:** boardly uses `NewType` for every id type. Validation (non-negative, max-length, format) is done by Pydantic at the FastAPI boundary using `Annotated[UserId, Field(ge=0)]` — the `Annotated` carries the validator, the `NewType` carries the name. The two layers compose because `Annotated` is itself a static-and-runtime construct: mypy reads `Annotated[UserId, ...]` as `UserId`; Pydantic reads the metadata and applies the validator. The composition is the canonical FastAPI pattern — see lesson [[01-typing/02-Annotated-and-Metadata]] for the full treatment.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/models/ids.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/models/ids.py`
2. **Exercise 2 — Add a fourth id type.** Add `CommentId = NewType("CommentId", int)` and a `fetch_comment(comment_id: CommentId) -> dict` function. Call `fetch_comment(UserId(1))` and confirm (a) runtime succeeds, (b) mypy rejects with an `incompatible type` error. `Verify: python -c "from boardly.models.ids import CommentId, fetch_comment; print(fetch_comment(CommentId(1)))"`
3. **Exercise 3 — Arithmetic drops the type.** Add `x = UserId(5); y = x + 1` and confirm that `reveal_type(y)` (mypy) shows `int`, not `UserId`. Re-wrap as `UserId(x + 1)` to recover the nominal type. `Verify: mypy --reveal boardly/models/ids.py 2>&1 | head -5`
4. **Exercise 4 — Compose with `Annotated`.** Add `from typing import Annotated` and `from pydantic import Field` and write `NonNegUserId = Annotated[UserId, Field(ge=0)]`. Run the file and confirm the introspection prints (`Annotated[UserId, FieldInfo(...)]` is its own runtime type — see lesson 03). `Verify: python -c "from boardly.models.ids import NonNegUserId; print(NonNegUserId)"`
5. **Exercise 5 — Build a `NewType` on a non-int.** Declare `Slug = NewType("Slug", str)` and a `def fetch_by_slug(slug: Slug) -> dict`. Pass a bare `str`; confirm runtime succeeds and mypy rejects. Then add a normalisation function `def normalise(s: str) -> Slug: return Slug(s.strip().lower())` and confirm the return type is `Slug`, not `str`. `Verify: python -c "from boardly.models.ids import Slug, normalise; print(normalise('  Hello '))"`

## Verification

```bash
$ python boardly/models/ids.py
got: 5 type(got).__name__: int
got is expected: True
isinstance(got, int): True
UserId(42) + 1: 43
fetch_user(99): {'id': 99, 'name': 'Ada Lovelace'}
fetch_user(ProjectId(7)): {'id': 7, 'name': 'Ada Lovelace'}

--- inspecting the NewType object ---
type(UserId).__name__: NewType
UserId.__name__: UserId
UserId.__supertype__: <class 'int'>
callable(UserId): True

bad (negative) id constructed at runtime: -1
```

If `got is expected: True`, `type(UserId).__name__: NewType`, and `UserId.__supertype__: <class 'int'>` all appear, you have the static-only concept working: at runtime, `UserId` is a callable identity function whose only useful state is its name and supertype; the type-checker does the rest.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `def f(x: int) -> str:`. `NewType` builds on the same annotation layer: the *only* way the type-checker learns `fetch_user` accepts a `UserId` is by reading the annotation.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated[T, ...]`. `Annotated[UserId, Field(ge=0)]` is how you add a runtime validation layer to a `NewType` — the canonical FastAPI pattern.
- [[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T")` constructs a similar "static-checker-facing object" — the two have parallel shapes (a string name, runtime-callable behaviour, no `isinstance` support). The two lessons are siblings.

## What's Next

[[12-types/02-SimpleNamespace]] — the next stop is `types.SimpleNamespace`, the standard-library "ad-hoc attribute bag". Where `NewType` gives you a *typed* primitive that the static checker understands, `SimpleNamespace` gives you an *untyped* mutable attribute container that the static checker mostly treats as `Any`. It is the right tool for test fixtures, config prototypes, and the "I have a dict and I want dot-access" case. Three things to look for in lesson 02:

- `SimpleNamespace(a=1, b=2)` constructs an object whose `repr` is `namespace(a=1, b=2)`.
- `SimpleNamespace(**dict)` is the canonical dict-to-namespace pattern.
- When `SimpleNamespace` wins (ad-hoc attribute bags) vs when `@dataclass` wins (typed models, validation, equality) — the boundary is the lesson's whole point.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.NewType — CPython reference** — https://docs.python.org/3/library/typing.html#typing.NewType — accessed 2026-10-23 — the canonical API for `NewType`, including the `__name__` and `__supertype__` attributes and the explicit statement that "the identity function at runtime, which makes it a zero-cost operation".
- **PEP 484 — Type Hints (the NewType section)** — https://peps.python.org/pep-0484/#newtype — accessed 2026-10-23 — the original PEP where `NewType` was introduced (Python 3.5.3+), with the rationale that the type-checker treats `NewType` as a new type while the runtime treats it as the supertype.
- **typing.Annotated — CPython reference** — https://docs.python.org/3/library/typing.html#typing.Annotated — accessed 2026-10-23 — the canonical reference for the `Annotated[T, metadata]` form that composes with `NewType` to add runtime validation.
- **types — Dynamic type creation — CPython reference** — https://docs.python.org/3/library/types.html — accessed 2026-10-23 — the section home for the rest of the `12-types` lessons; `NewType` is the only construct covered here that lives in `typing` rather than `types`, and the lesson explains why.

## What We Learned

- `NewType("UserId", int)` constructs a callable object whose only runtime job is the identity function — `UserId(5) is 5` is `True`.
- `NewType` is a static-only concept: mypy and pyright treat `UserId` as distinct from `int`; CPython does not.
- Arithmetic on a `NewType` value *drops* the nominal type — `UserId(5) + 1` is `int`, not `UserId`. Re-wrap with `UserId(...)` if you need to preserve the nominal type.
- You cannot `isinstance(x, UserId)` — `NewType` is not a class. Use `isinstance(x, int)` and trust the static checker.
- The right pattern for *typed-and-validated* ids is `Annotated[UserId, Field(ge=0)]` — `NewType` provides the name, `Annotated` carries the validator, Pydantic enforces at the FastAPI boundary.
- `type(x).__name__` for a `NewType` is `"NewType"`; `x.__name__` is the string you passed; `x.__supertype__` is the type you passed. These three attributes are all the runtime introspection you get.
