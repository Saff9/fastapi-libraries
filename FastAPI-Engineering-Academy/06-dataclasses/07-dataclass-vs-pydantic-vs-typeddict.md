---
title: "Lesson 07: dataclass vs Pydantic vs TypedDict"
aliases:
 - dataclass vs pydantic vs typeddict
 - when to use dataclass
 - when to use pydantic
 - when to use typeddict
tags:
 - dataclasses
 - pydantic
 - typeddict
 - canonical
status: complete
course_level: advanced
difficulty: advanced
estimated_time: "40–60 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[06-dataclasses/02-field-and-Defaults]]"
 - "[[06-dataclasses/03-Frozen-and-Immutability]]"
related_lessons:
 - "[[06-dataclasses/06-asdict-astuple-replace]]"
 - "[[01-typing/07-TypedDict]]"
first_taught_in: "06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict"
---

# Lesson 07: dataclass vs Pydantic vs TypedDict

*The senior decision every `boardly` engineer makes per model — `@dataclass` (fastest, no validation), Pydantic `BaseModel` (validation, slower), `TypedDict` (type-only, zero runtime). When each wins, when each loses, and the four rules of thumb.*

**You're at the very beginning of Section 06, seventh lesson in.**

You have written a `@dataclass`. You have used `field()`. You have frozen it, slotted it, replaced it. Now you stand at the fork the whole section has been building toward: for any given shape in `boardly` — the `Ticket` returned from the database, the JSON body POSTed to the create-ticket endpoint, the dict returned by an external API — which of the three tools do you reach for? `@dataclass` is the standard-library answer; Pydantic `BaseModel` is the FastAPI answer; `TypedDict` is the zero-runtime-overhead answer. They look similar — all three are typed, all three produce values you pass around — but they are not interchangeable. This lesson commits the decision to print.

#dataclasses #pydantic #typeddict #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Name the three primitives** — `@dataclass`, `pydantic.BaseModel`, `TypedDict` — and one-sentence each, what they do and do not do at runtime.
2. **Reason about the validation axis** — `@dataclass` validates nothing; Pydantic validates everything; `TypedDict` validates nothing at runtime but mypy/pyright check it statically.
3. **Reason about the runtime-cost axis** — `@dataclass` is a code generator (zero per-construction overhead beyond the function call); Pydantic builds a validator per field at class creation and runs it on every `__init__`; `TypedDict` is a `dict` with no extra object.
4. **Choose correctly for six `boardly` shapes** — domain model, request body, response body, external API payload, config, JSON-RPC envelope.
5. **Defend the choice** — name the trade-off explicitly and the failure mode if the wrong choice is made.

## Prerequisites

Before starting, you need:

- **`@dataclass` basics** — [[06-dataclasses/01-dataclass-Basics]]. The lesson 01 fact that `@dataclass` does not validate is the central data point for this comparison.
- **`field()` and defaults** — [[06-dataclasses/02-field-and-Defaults]]. Pydantic's `Field()` is parameter-compatible with `dataclasses.field()`; the parallel is the bridge.
- **`frozen` and `slots`** — [[06-dataclasses/03-Frozen-and-Immutability]] and [[06-dataclasses/04-Slots-and-Performance]]. Pydantic v2's `model_config = ConfigDict(frozen=True)` mirrors the dataclass knobs; the API surface is deliberately close.
- **`TypedDict`** — [[01-typing/07-TypedDict]]. The PEP 589 introduction; this lesson commits when to use it over the alternatives.
- **About 40–60 minutes of focused time.**

**The most common gap: choosing Pydantic for everything.**

Students who arrive at FastAPI tend to default to `pydantic.BaseModel` for every model — domain, request, response, external. This works (Pydantic is fast enough at v2 for most workloads), but it pays validation cost on every `__init__` even when the source is already trusted (a database row that just came back from a `SELECT`, an internal service that already validated). The senior decision is to use the cheapest tool that meets the safety requirement: `TypedDict` for JSON envelopes you only need to type statically, `@dataclass` for trusted-data domain models, Pydantic `BaseModel` only at untrusted-data boundaries (HTTP request bodies, external API responses).

## The Problem

You are designing the `boardly` API. You have six shapes to model:

1. **`Ticket` domain model** — lives in the database; comes back from `SELECT * FROM tickets`; passed through the service layer; serialised to a response body.
2. **`CreateTicketRequest`** — the JSON body POSTed to `POST /tickets`; untrusted; needs validation (title not empty, assignee_id is a positive int).
3. **`TicketResponse`** — the JSON body returned to the client; trusted (you constructed it); needs `model_dump()` for JSON encoding.
4. **`GitHubIssuePayload`** — the JSON body returned from GitHub's API; untrusted; needs validation (state is one of `"open"`, `"closed"`).
5. **`BoardlyConfig`** — the YAML config loaded at startup; trusted after load; needs typed access.
6. **`JSONRPCError`** — the error envelope returned by every error in the JSON-RPC layer; trusted; needs to be a `dict` for `json.dumps`.

For each, the question is: `@dataclass`, `pydantic.BaseModel`, or `TypedDict`? The answer is not "Pydantic for everything". The answer is per-shape, and this lesson commits it.

## The Code

```python
# boardly/models/decision.py
"""The senior decision — three primitives, three files side by side."""
from dataclasses import dataclass, field
from typing import TypedDict

# (1) @dataclass — for the trusted Ticket domain model.
@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()


# (2) pydantic.BaseModel — for the untrusted CreateTicketRequest.
try:
    from pydantic import BaseModel, Field

    class CreateTicketRequest(BaseModel):
        title: str = Field(min_length=1, max_length=200)
        assignee_id: int = Field(gt=0)
        tags: list[str] = Field(default_factory=list, max_length=20)

except ImportError:
    # Pydantic may not be installed in the sandbox — the lesson still teaches the shape.
    pass


# (3) TypedDict — for the trusted JSONRPCError envelope (no runtime cost).
class JSONRPCError(TypedDict):
    code: int
    message: str
    data: dict


if __name__ == "__main__":
    # @dataclass — no validation; the int field accepts a string.
    t = Ticket(id=1, title="Fix login", assignee_id="oops")
    print("ticket (no validation):", t)
    print("ticket.assignee_id type:", type(t.assignee_id).__name__)

    # TypedDict — it IS a dict at runtime; the type is a static hint only.
    err: JSONRPCError = {"code": -32600, "message": "Invalid Request", "data": {}}
    print("error is dict:", isinstance(err, dict))

    # Pydantic — would validate; comment shows the equivalent if available.
    # CreateTicketRequest(title="", assignee_id=0)  # ValidationError
```

## Line-by-Line Deep Dive

### Lines 1–10: The `@dataclass` form

```python
# boardly/models/decision.py
"""The senior decision — three primitives, three files side by side."""
from dataclasses import dataclass, field
from typing import TypedDict

# (1) @dataclass — for the trusted Ticket domain model.
@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    title: str
    assignee_id: int = 0
    tags: tuple[str, ...] = ()
```

This is the lesson 03 + 04 frozen-slotted form. `Ticket` is the *trusted* domain model — it lives in the database, comes back from `SELECT`, gets passed through the service layer. The database already validated the column types; the service layer trusts the row. `@dataclass` is the cheapest tool: zero per-construction overhead beyond the `__init__` call, zero validation (because none is needed), smallest memory footprint (slots). The `assignee_id` is typed `int` but `Ticket(id=1, title="x", assignee_id="oops")` succeeds — `@dataclass` does not coerce or validate.

**Why does the trusted-data rule make `@dataclass` the right choice for `Ticket`?**

Because validation is *expensive* — Pydantic's per-field validator runs on every `__init__` call, and the cost adds up at 1000 requests/second. If the data is already validated by a trusted source (the database column constraints, an internal service contract), re-validating is paying for safety you already have. `@dataclass` skips the validation; the savings are real. The `boardly` `Ticket` is constructed from a database row that has `assignee_id BIGINT NOT NULL CHECK (assignee_id > 0)` — the database enforced the constraint at `INSERT` time. Re-enforcing it at `Ticket(row)` construction time is paying twice.

### Lines 12–22: The Pydantic form

```python
# (2) pydantic.BaseModel — for the untrusted CreateTicketRequest.
try:
    from pydantic import BaseModel, Field

    class CreateTicketRequest(BaseModel):
        title: str = Field(min_length=1, max_length=200)
        assignee_id: int = Field(gt=0)
        tags: list[str] = Field(default_factory=list, max_length=20)

except ImportError:
    # Pydantic may not be installed in the sandbox — the lesson still teaches the shape.
    pass
```

`CreateTicketRequest` is the *untrusted* request body. The client can send anything; the server must reject invalid input. Pydantic's `Field(min_length=1, max_length=200)` on `title` enforces a non-empty title of at most 200 characters at `__init__` time. `Field(gt=0)` on `assignee_id` enforces a positive integer. `Field(max_length=20)` on `tags` enforces at most 20 tags. The validators run on every construction; invalid input raises `pydantic.ValidationError`, which FastAPI catches and converts to an HTTP 422 response with a structured error body. The `try/except ImportError` block is a courtesy for the sandbox — Pydantic may not be installed; the lesson still teaches the shape.

**Why is Pydantic the right choice for `CreateTicketRequest`?**

Because the cost of a `ValidationError` is much less than the cost of letting bad data into the database or the service layer. A request with `assignee_id=-5` or `title=""` should never reach the `Ticket` constructor — and the only way to enforce that at the HTTP boundary is to validate at construction. Pydantic's `BaseModel` is the standard-library-adjacent tool for that: it builds a validator per field at class-creation time (using the `pydantic-core` Rust backend in v2), runs the validator on `__init__`, and raises `ValidationError` with a structured field path. The cost is ~5–10× a `@dataclass` `__init__` — acceptable at the request boundary, unacceptable at the database-row boundary.

### Lines 24–28: The `TypedDict` form

```python
# (3) TypedDict — for the trusted JSONRPCError envelope (no runtime cost).
class JSONRPCError(TypedDict):
    code: int
    message: str
    data: dict
```

`JSONRPCError` is a *TypedDict* — a `dict` subclass at the type-checker level, a plain `dict` at runtime. The class body declares the keys and their types; mypy and pyright enforce the keys exist and the values match the types. At runtime, `JSONRPCError` *is* a `dict` — `isinstance(err, dict)` is `True`, `err["code"]` works, `json.dumps(err)` works. There is no `__init__`, no validators, no instance overhead. The class is purely a static-type declaration.

**Why is `TypedDict` the right choice for `JSONRPCError`?**

Because the error envelope is constructed by `boardly` itself, from trusted values, and immediately serialised to JSON. A `@dataclass` would add an `__init__` call and a `asdict()` call before `json.dumps`; Pydantic would add an `__init__` and a `model_dump()`. `TypedDict` adds neither — the value *is* a `dict`, `json.dumps` works directly. The type annotation gives mypy/pyright the static guarantee; the runtime cost is zero. For envelope-shaped data (JSON-RPC responses, webhook payloads, internal API contracts), `TypedDict` is the cheapest possible tool that still gives you type safety.

### Lines 30–35: The sanity check

```python
if __name__ == "__main__":
    # @dataclass — no validation; the int field accepts a string.
    t = Ticket(id=1, title="Fix login", assignee_id="oops")
    print("ticket (no validation):", t)
    print("ticket.assignee_id type:", type(t.assignee_id).__name__)
```

`Ticket(id=1, title="Fix login", assignee_id="oops")` succeeds — `@dataclass` does not validate or coerce. `t.assignee_id` is the string `"oops"`, not an int. The print confirms: `type(t.assignee_id).__name__` is `str`. This is the central design fact of `@dataclass`: it is a code generator, not a validator. The annotation is a *static* hint; mypy will warn (if you run it) but the runtime is silent.

**Why does `@dataclass` not validate?**

Because validation is a separate concern, and the standard library's position is: the type system is static, not runtime. `typing`'s annotations are for static checkers (mypy, pyright, pytype); at runtime, Python's duck typing rules. `@dataclass` follows this principle: it copies the annotations onto the generated `__init__` signature so the static checkers can read them, but it does not add a runtime check. Pydantic takes the opposite position: it provides runtime validation by *interpreting* the same annotations. The two are not in conflict — they are different choices on the same axis (static vs runtime). FastAPI uses both: Pydantic for request/response models, `@dataclass` for internal trusted state.

### Lines 37–38: The TypedDict sanity check

```python
    # TypedDict — it IS a dict at runtime; the type is a static hint only.
    err: JSONRPCError = {"code": -32600, "message": "Invalid Request", "data": {}}
    print("error is dict:", isinstance(err, dict))
```

The literal `{"code": -32600, "message": "Invalid Request", "data": {}}` is annotated `: JSONRPCError`. At runtime, `err` is a plain `dict`; `isinstance(err, dict)` is `True`. The type annotation gives mypy the guarantee that the keys `code`, `message`, `data` exist and have the declared types. If you write `err["code"] = "not-an-int"`, mypy will warn; the runtime will not. The `TypedDict` is the static-only tool — zero runtime cost, zero runtime safety.

### Lines 40–41: The Pydantic sanity check

```python
    # Pydantic — would validate; comment shows the equivalent if available.
    # CreateTicketRequest(title="", assignee_id=0)  # ValidationError
```

The Pydantic line is commented out because Pydantic may not be installed in the sandbox. If it were, `CreateTicketRequest(title="", assignee_id=0)` would raise `pydantic.ValidationError` with a structured error body — `title` is too short (`min_length=1`), `assignee_id` is not `> 0`. FastAPI catches the `ValidationError` and converts it to an HTTP 422 response. The structured error body is one of the reasons Pydantic is the right choice at the HTTP boundary: the client gets a useful error message, not a 500.

**Why does Pydantic raise `ValidationError` rather than `TypeError`?**

Because the validation logic is more nuanced than "is this an int". `Field(gt=0)` is not a type check — it is a value check (greater than zero). Pydantic's error taxonomy distinguishes `type_error` (wrong type), `value_error` (right type, wrong value), `constraint_error` (constraint not met). The structured error body has `loc` (field path), `msg` (human-readable), `type` (error category). `TypeError` would not carry this metadata. Pydantic's `ValidationError` is one of its main value-adds over `@dataclass` + manual `__post_init__`.

## Execution Trace

```bash
$ python boardly/models/decision.py
ticket (no validation): Ticket(id=1, title='Fix login', assignee_id='oops', tags=())
ticket.assignee_id type: str
error is dict: True
```

The `Ticket` instance has a string `assignee_id` despite the `int` annotation — the runtime did not coerce. The `JSONRPCError` is a plain `dict` — the type was a static hint only.

## Common Mistakes

### Mistake 1: Using `@dataclass` for an HTTP request body

```python
@dataclass
class CreateTicketRequest:
    title: str
    assignee_id: int
```

**Symptom:** The endpoint accepts `{"title": "", "assignee_id": -5}` and constructs a `Ticket` with an empty title and a negative assignee. The constraint you *meant* to enforce (non-empty title, positive assignee) is missing.
**Why:** `@dataclass` does not validate. The annotation is a static hint, not a runtime check.
**Fix:** Use `pydantic.BaseModel` with `Field(min_length=1, gt=0)`.

### Mistake 2: Using Pydantic for a domain model that comes from the database

```python
class Ticket(BaseModel):
    id: int
    title: str
    assignee_id: int = Field(gt=0)
```

**Symptom:** The service layer pays Pydantic validation cost on every database-row-to-model conversion. At 1000 rows per query, the cost is real.
**Why:** The database already enforced the constraints at `INSERT` time. Re-validating is paying twice.
**Fix:** Use `@dataclass(frozen=True, slots=True)` for the trusted-data domain model.

### Mistake 3: Using `TypedDict` for a request body

```python
class CreateTicketRequest(TypedDict):
    title: str
    assignee_id: int
```

**Symptom:** The endpoint accepts `{"title": 42}` (a number, not a string) and the `Ticket` constructor later fails with `TypeError`.
**Why:** `TypedDict` is a static-only tool — at runtime, it is a plain `dict`, no validation. The annotation does not enforce.
**Fix:** Use Pydantic for untrusted request bodies. Use `TypedDict` only for trusted JSON envelopes.

## Engineering Trade-Offs

**Decision:** In `boardly`:
- Domain models (trusted, from DB or internal service): `@dataclass(frozen=True, slots=True)`.
- Request bodies (untrusted, from HTTP): `pydantic.BaseModel` with `Field(...)`.
- Response bodies (trusted, you constructed them): `@dataclass` + `asdict`, or `TypedDict` if you want zero runtime cost.
- External API payloads (untrusted): `pydantic.BaseModel` with `Field(...)`.
- Config (trusted after load): `@dataclass(frozen=True, slots=True)`.
- JSON envelopes (trusted, JSON-RPC, webhooks): `TypedDict`.

**Both sides:** The alternative to this matrix is "Pydantic everywhere" — simpler, more uniform, slower. For low-traffic services, the uniformity wins. For high-traffic services, the per-shape choice wins. The matrix is the senior decision; the uniform choice is the junior default.
**Commitment:** `boardly` uses the matrix. The model-template file documents which form to use for which shape. The convention is enforced in code review.

## Exercises

1. **Exercise 1 — Reproduce no-validation.** Run the file. Confirm `t.assignee_id` is the string `"oops"`. Explain to a colleague why `@dataclass` does not coerce. `Verify: python boardly/models/decision.py`
2. **Exercise 2 — Install Pydantic and verify.** `pip install pydantic && python -c "from boardly.models.decision import CreateTicketRequest; CreateTicketRequest(title='', assignee_id=0)"` — confirm the `ValidationError` is raised with structured fields. `Verify: python -c "import pydantic; print(pydantic.VERSION)"`
3. **Exercise 3 — Convert the domain model.** Change `Ticket` to a `pydantic.BaseModel` and measure the construction time of 100,000 instances. Compare to the `@dataclass` form. `Verify: python -m timeit -s "from boardly.models.decision import Ticket" "Ticket(id=1, title='x', assignee_id=42)"`
4. **Exercise 4 — Add a `TypedDict` for webhook payloads.** Define `class TicketWebhook(TypedDict): event: str; ticket: dict` — explain why `TypedDict` is the right choice for a webhook envelope you only forward. `Verify: python boardly/models/decision.py`
5. **Exercise 5 — The config shape.** Define `BoardlyConfig` as both `@dataclass` and `TypedDict`. Explain which is right if the config is loaded once at startup and never modified, and why. `Verify: python boardly/models/decision.py`

## Verification

```bash
$ python boardly/models/decision.py
ticket (no validation): Ticket(id=1, title='Fix login', assignee_id='oops', tags=())
ticket.assignee_id type: str
error is dict: True
```

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — `@dataclass` is a code generator, not a validator. This lesson commits when that matters.
- [[06-dataclasses/02-field-and-Defaults]] — `field()` and Pydantic's `Field()` share a parameter surface.
- [[06-dataclasses/06-asdict-astuple-replace]] — `asdict` is the `@dataclass` analogue of Pydantic's `model_dump()`.
- [[01-typing/07-TypedDict]] — the PEP 589 introduction; this lesson commits when `TypedDict` wins over the alternatives.

## What's Next

[[06-dataclasses/08-KW_ONLY-and-InitVar]] — the `KW_ONLY` sentinel and `InitVar[T]` for init-only fields. The `__post_init__` lifecycle is the last piece of the `@dataclass` API surface, and the place where `@dataclass` *can* do a small amount of validation (if you choose to). Three things to take with you:

- `@dataclass` validates nothing at runtime; Pydantic validates everything; `TypedDict` is static-only.
- `@dataclass` for trusted-data domain models; Pydantic for untrusted HTTP bodies; `TypedDict` for trusted JSON envelopes.
- The cost ratio is roughly `1 : 5–10 : 0` (`@dataclass` : Pydantic : `TypedDict`) per construction.

## Sources

- **`dataclasses` — Support for data classes** — https://docs.python.org/3/library/dataclasses.html — accessed 2026-10-23 — the canonical reference for `@dataclass`.
- **Pydantic — Models** — https://docs.pydantic.dev/latest/concepts/models/ — accessed 2026-10-23 — the canonical reference for `BaseModel`, `Field`, `model_dump()`, `model_copy()`.
- **`typing.TypedDict`** — https://docs.python.org/3/library/typing.html#typing.TypedDict — accessed 2026-10-23 — the PEP 589 reference, including `total=False`, `Required`/`NotRequired`.
- **PEP 557 — Data Classes** — https://peps.python.org/pep-0557/ — accessed 2026-10-23 — the rationale section "Comparison with namedtuple" and "Comparison with attr" are the senior-decision precedents for this lesson.
- **PEP 589 — TypedDict** — https://peps.python.org/pep-0589/ — accessed 2026-10-23 — the rationale for the static-only semantics.

## What We Learned

- You can name the three primitives and one-sentence each what they do and do not do at runtime.
- You can reason about the validation axis — `@dataclass` validates nothing; Pydantic validates everything; `TypedDict` is static-only.
- You can reason about the runtime-cost axis — `@dataclass` is a code generator; Pydantic runs validators per `__init__`; `TypedDict` is a `dict`.
- You can choose correctly for six `boardly` shapes — domain model, request body, response body, external payload, config, envelope.
- You can defend the choice — name the trade-off explicitly and the failure mode if the wrong choice is made.
