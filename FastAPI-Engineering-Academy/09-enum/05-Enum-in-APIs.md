---
title: "Lesson 05: Enum in APIs"
aliases:
 - FastAPI enum
 - enum OpenAPI schema
 - StrEnum in FastAPI
 - Literal vs Enum
tags:
 - enum
 - canonical
 - python-stdlib
 - fastapi
 - openapi
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[09-enum/02-IntEnum-and-StrEnum]]"
 - "[[09-enum/04-auto-and-value]]"
related_lessons:
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
 - "[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]"
first_taught_in: "09-enum/05-Enum-in-APIs"
---

# Lesson 05: Enum in APIs

*How `boardly`'s FastAPI route turns `status: TicketStatus = TicketStatus.OPEN` into an OpenAPI schema with `"enum": ["open", "done"]`, validates the query string at the boundary, and serialises the response with the member's `.value` — and the `Literal[...]` alternative that does the same job with no class.*

**You're at the very beginning of Section 09 — five lessons in. This is the FastAPI connection.**

You have written `status: TicketStatus = TicketStatus.OPEN` in a FastAPI route. You have seen the route work — `"open"` comes back in the JSON, `"closed"` returns HTTP 422. You have not seen what FastAPI actually does to make that happen. This lesson shows you: the Pydantic schema, the OpenAPI `enum` keyword, the serialisation path, and the `Literal` alternative. Take your time. Type every example. **This is how you learn.**

#enum #canonical #fastapi

## Learning Objectives

By the end of this lesson you will be able to:

1. **Read FastAPI's enum handling** — explain the three things FastAPI does when it sees a `StrEnum` on a route signature: schema generation, query validation, response serialisation.
2. **Inspect the OpenAPI output** — navigate `/openapi.json` and find the `{"type": "string", "enum": ["open", "done"]}` block that documents the allowed values.
3. **Predict the validation response** — explain why an invalid value (`?status=closed`) returns HTTP 422 with a structured error body, not HTTP 400.
4. **Compare `StrEnum` to `Literal`** — write `status: Literal["open", "done"] = "open"` as the no-class alternative, and explain the trade-off (no `.value`, no methods, no iteration, no `auto()`).
5. **Pick the right tool** — for a given API field, decide between `StrEnum`, `Literal`, and a plain `str` with a `Field(description=...)` based on whether the field is internal, schema-only, or domain-meaningful.

## Prerequisites

Before starting, you need:

- **Lesson 02** — [[09-enum/02-IntEnum-and-StrEnum]] — `StrEnum` (3.11+) and the `str()` behaviour that makes JSON serialisation work.
- **Lesson 04** — [[09-enum/04-auto-and-value]] — `auto()` with `_generate_next_value_` returning `name.lower()` — the canonical `StrEnum` pattern for API wire values.
- **About 40–55 minutes of focused time.**

**The most common gap: assuming FastAPI serialises the enum's *name* (e.g., `OPEN`) instead of its *value* (e.g., `"open"`).** It serialises the value. The name is for Python source code; the value is for the wire. `StrEnum` with `auto()` returning `name.lower()` makes the two agree — `"open"` is both the source-code name and the wire value — but they are conceptually different and you should know which one the API contract uses.

## The Problem

Here is the bug that motivates FastAPI's enum integration. `boardly` had this route:

```python
# boardly/routes/tickets.py — the bad old days
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/tickets/{id}")
def get_ticket(id: int, status: Optional[str] = None):
    if status not in ("open", "in_progress", "blocked", "done"):
        # the values are duplicated here
        return {"error": "invalid status"}
    return {"id": id, "status": status or "open"}
```

Three bugs:

1. **The allowed values are duplicated between the route and the documentation.** The OpenAPI schema has no `enum` keyword; the docs say `status: string (optional)`. A client has to read the source to know the allowed values.
2. **The validation error is HTTP 200 with `{"error": ...}`.** It should be HTTP 422 with a structured error body — that is what FastAPI's validation layer returns for everything else. By rolling your own validation, you break the contract.
3. **The default value `"open"` is a string literal.** If the canonical wire value changes (say, to `"opened"`), the route has to be hand-edited. There is no single source of truth.

A `StrEnum` fixes all three. The schema gets an `enum` keyword with the allowed values. Validation happens at the FastAPI/Pydantic layer, returning HTTP 422 with a structured error. The default value is a named constant, not a string literal.

## The Code

```python
# boardly/api/tickets.py
"""boardly's ticket-status FastAPI routes — enum-end-to-end."""
from enum import StrEnum, auto, unique
from typing import Annotated, Literal

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel


# 1. The canonical StrEnum — wire value derives from name
@unique
class TicketStatus(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    OPEN    = auto()
    IN_PROGRESS  = auto()
    BLOCKED = auto()
    DONE    = auto()


# 2. A response_model that uses the enum
class TicketOut(BaseModel):
    id: int
    status: TicketStatus


# 3. The route — query parameter, response_model
app = FastAPI(title="boardly")

StatusQuery = Annotated[
    TicketStatus,
    Query(description="Filter tickets by status.", examples=["open"]),
]


@app.get("/tickets/{id}", response_model=TicketOut)
def get_ticket(id: int, status: StatusQuery = TicketStatus.OPEN) -> TicketOut:
    return TicketOut(id=id, status=status)


# 4. The Literal alternative — same wire contract, no class
@app.get("/literal/{id}")
def get_literal(id: int, status: Literal["open", "in_progress", "blocked", "done"] = "open"):
    return {"id": id, "status": status}


# 5. Demonstration: schema, validation, serialisation
client = TestClient(app)

# Schema inspection
schema = client.get("/openapi.json").json()
ts_schema = schema["components"]["schemas"]["TicketStatus"]
print("--- TicketStatus in the OpenAPI schema ---")
print(ts_schema)
# {'type': 'string', 'enum': ['open', 'in_progress', 'blocked', 'done'], 'title': 'TicketStatus'}

# Serialisation: response uses the member's .value
r = client.get("/tickets/42")
print("\n--- GET /tickets/42 (default) ---")
print(r.status_code, r.json())
# 200 {'id': 42, 'status': 'open'}

# Validation: invalid value returns 422 with a structured error
r = client.get("/tickets/42?status=closed")
print("\n--- GET /tickets/42?status=closed ---")
print(r.status_code, r.json())
# 422 {'detail': [{'type': 'enum', 'loc': ['query', 'status'], 'msg': "Input should be 'open', 'in_progress', 'blocked' or 'done'", ...}]}

# The Literal route behaves the same way
r = client.get("/literal/42?status=closed")
print("\n--- GET /literal/42?status=closed ---")
print(r.status_code, "— same 422")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 9–17: The canonical `StrEnum`

```python
@unique
class TicketStatus(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    OPEN    = auto()
    IN_PROGRESS  = auto()
    BLOCKED = auto()
    DONE    = auto()
```

This is the lesson 02 + lesson 04 pattern in one block: `StrEnum` (3.11+), `auto()` for the values, `_generate_next_value_` returning `name.lower()` so the wire value matches the source name, `@unique` so a typo like `CLOSED = auto()` (when you meant `CANCELLED`) does not silently create an alias.

The wire values are `"open"`, `"in_progress"`, `"blocked"`, `"done"`. They match the source-code names, lowercase. That match is the *purpose* of the override — the wire format is part of the API contract, and you want one source of truth.

**Why `StrEnum` and not plain `Enum` for the API field?** Because FastAPI's Pydantic serialiser, when it sees a field annotated `TicketStatus`, calls `str(member)` to get the wire value. For plain `Enum`, that returns `"TicketStatus.OPEN"` (the qualified name) — wrong wire value. For `StrEnum` (3.11+), it returns `member.value` — `"open"`. The `StrEnum.__str__` override is the only thing that makes the JSON response contain `"open"` instead of `"TicketStatus.OPEN"`. See lesson 02 for the full PEP 663 motivation.

**Tip — `@unique` is the cheapest insurance you will ever buy**

The decorator costs zero at runtime and catches the typo at import. Every wire-serialised enum in `boardly` has it. There is no scenario where you want a wire-serialised enum to have aliases — aliases cause the iteration-skips-dropdown bug (lesson 04) and the validation-passes-but-name-is-missing bug.

### Lines 20–22: The `response_model`

```python
class TicketOut(BaseModel):
    id: int
    status: TicketStatus
```

`TicketOut` is a Pydantic `BaseModel`. The `status` field is annotated `TicketStatus` — a `StrEnum` subclass. Pydantic reads that annotation, sees it is an `Enum` subclass, and registers a custom validator + serialiser for the field.

When the route returns `TicketOut(id=42, status=TicketStatus.OPEN)`, Pydantic validates the `status` value: `TicketStatus.OPEN` is a member of `TicketStatus`, so validation passes. When Pydantic serialises the response, it calls `TicketStatus.OPEN.__str__()` (via the `StrEnum` override) and gets `"open"`. The JSON response contains `{"status": "open"}`.

**Note — Pydantic does not call `.value` directly; it relies on `StrEnum.__str__`**

The Pydantic serialiser uses `str(member)` for `StrEnum` fields (not `member.value`). For plain `Enum` fields, it uses `member.value`. So:
- `StrEnum` field: `str(member)` → `"open"` (the StrEnum override)
- `Enum` field with `str` values: `member.value` → `"open"` (the value)

The first is cleaner; the second requires plain `Enum` (no `StrEnum`) with explicit string values. The boardly project uses `StrEnum` because it is the modern, opinionated default.

### Lines 27–32: The route with `Annotated[..., Query(...)]`

```python
StatusQuery = Annotated[
    TicketStatus,
    Query(description="Filter tickets by status.", examples=["open"]),
]


@app.get("/tickets/{id}", response_model=TicketOut)
def get_ticket(id: int, status: StatusQuery = TicketStatus.OPEN) -> TicketOut:
    return TicketOut(id=id, status=status)
```

`Annotated[TicketStatus, Query(...)]` is the FastAPI idiom (PEP 593 `Annotated`, see [[01-typing/02-Annotated-and-Metadata]]) for adding OpenAPI metadata to a parameter without changing its runtime type. FastAPI reads the annotation via `typing.get_type_hints(..., include_extras=True)` — see [[10-inspect/06-How-FastAPI-uses-inspect]] for the full call chain — and uses the `Query` metadata to enrich the OpenAPI schema.

The default value `TicketStatus.OPEN` is a member of `TicketStatus`. FastAPI serialises that default into the OpenAPI schema as `"default": "open"` (the member's `.value`, since Pydantic serialises the default the same way it serialises a response field).

The return annotation `-> TicketOut` is the `response_model`. FastAPI uses it (along with the explicit `response_model=TicketOut` keyword arg) to validate the response before sending it. If the route returned `{"id": 42, "status": "garbage"}`, FastAPI would raise a `ResponseValidationError` because `"garbage"` is not a valid `TicketStatus`.

**Why both `response_model=TicketOut` and `-> TicketOut`?** Because the keyword arg is the canonical source of truth. The return annotation is a hint for static analysis and for tooling that reads signatures (like FastAPI's own dependency reader). When they conflict, the keyword arg wins. The boardly project specifies both for documentation, but the keyword arg is the runtime contract.

### Lines 36–39: The `Literal` alternative

```python
@app.get("/literal/{id}")
def get_literal(id: int, status: Literal["open", "in_progress", "blocked", "done"] = "open"):
    return {"id": id, "status": status}
```

`Literal["open", "in_progress", "blocked", "done"]` is the no-class alternative. It produces an OpenAPI schema with the same `"enum"` keyword. It produces the same validation error on invalid values. It has no `.name`, no `.value`, no `__members__`, no `auto()`, no `@unique`, no methods — it is just a typing construct.

**Why would you choose `Literal` over `StrEnum`?** Three reasons:

1. **The values are external and stable.** If the allowed values come from a spec you do not own (an RFC, a vendor's API), `Literal` lets you encode them without creating a class that pretends to be the source of truth.
2. **The set is small and stable.** A two-value enum (`Literal["on", "off"]`) does not need a class.
3. **You need it in a context where classes are awkward.** A `TypedDict` field, a `dataclass` field, a `@overload` — all of these accept `Literal` more naturally than an `Enum` class.

**Why would you choose `StrEnum` over `Literal`?** Three reasons:

1. **The set has business logic.** Methods, properties, helper functions — these live on a class.
2. **The set is referenced from multiple modules.** A class is importable; a `Literal` is typing-only.
3. **You want `auto()` and `@unique`.** These only exist on `Enum` subclasses.

**Danger — `Literal` values are duplicated, `StrEnum` values are not**

```python
Literal["open", "in_progress", "blocked", "done"]   # repeated in every place you use it

class TicketStatus(StrEnum):                          # defined once, imported everywhere
    OPEN    = auto()
    IN_PROGRESS  = auto()
    BLOCKED = auto()
    DONE    = auto()
```

If the canonical wire value changes — say, `"in_progress"` becomes `"in-progress"` — the `Literal` form has to be edited everywhere it appears. The `StrEnum` form is edited once (the `_generate_next_value_` override). For a value used in more than one place, the class wins.

### Lines 41–49: OpenAPI schema inspection

```python
schema = client.get("/openapi.json").json()
ts_schema = schema["components"]["schemas"]["TicketStatus"]
print("--- TicketStatus in the OpenAPI schema ---")
print(ts_schema)
# {'type': 'string', 'enum': ['open', 'in_progress', 'blocked', 'done'], 'title': 'TicketStatus'}
```

The `/openapi.json` endpoint (which FastAPI serves by default) contains a `components/schemas` block with one entry per Pydantic model *and* one entry per enum. The `TicketStatus` entry is:

```json
{
  "type": "string",
  "enum": ["open", "in_progress", "blocked", "done"],
  "title": "TicketStatus"
}
```

The `"type": "string"` comes from the fact that `StrEnum` is a `str` subclass — Pydantic sees `issubclass(TicketStatus, str)` is `True` and emits `type: string`. The `"enum"` keyword lists the wire values — Pydantic iterates `TicketStatus.__members__` and emits each member's `.value`. The `"title"` is the class name.

**Why does this matter?** Because clients generate code from this schema. A TypeScript client will produce `type TicketStatus = "open" | "in_progress" | "blocked" | "done"`. A Python client will produce `TicketStatus = Literal["open", "in_progress", "blocked", "done"]`. The OpenAPI `enum` keyword is the wire contract — if the schema is wrong, every generated client is wrong.

**Warning — The `enum` keyword uses `.value`, not `.name`**

If your `StrEnum` has `OPEN = "open"`, the schema says `"enum": ["open"]` (the value). If you wrote `OPEN = "O"` (an abbreviation), the schema says `"enum": ["O"]` (the value `"O"`, not the name `"OPEN"`). The schema is the wire format; the names are a Python-side concern.

### Lines 52–56: Serialisation — response uses the member's value

```python
r = client.get("/tickets/42")
print("\n--- GET /tickets/42 (default) ---")
print(r.status_code, r.json())
# 200 {'id': 42, 'status': 'open'}
```

`GET /tickets/42` with no `?status=` query uses the default value `TicketStatus.OPEN`. The route returns `TicketOut(id=42, status=TicketStatus.OPEN)`. Pydantic serialises the response: `id` is an int, serialised as `42`; `status` is a `StrEnum` member, serialised via `str(member)` which returns `"open"` (the StrEnum override).

The JSON response is `{"id": 42, "status": "open"}`. The wire value `"open"` matches the OpenAPI schema. The round-trip — FastAPI → JSON → OpenAPI client → FastAPI — is consistent.

**Why does the default value serialise as `"open"` and not `TicketStatus.OPEN`?** Because Pydantic's serialiser calls `str()` on the member. For `StrEnum`, `str()` returns `self._value_` (the value). For plain `Enum`, `str()` returns `"TicketStatus.OPEN"` (the qualified name) — wrong wire value. This is the same reason the response field serialises correctly only with `StrEnum`. The default value goes through the same path.

### Lines 59–63: Validation — invalid value returns HTTP 422

```python
r = client.get("/tickets/42?status=closed")
print("\n--- GET /tickets/42?status=closed ---")
print(r.status_code, r.json())
# 422 {'detail': [{'type': 'enum', 'loc': ['query', 'status'], 'msg': "Input should be 'open', 'in_progress', 'blocked' or 'done'", ...}]}
```

`GET /tickets/42?status=closed` is a request with an invalid query value. FastAPI's validation layer — Pydantic — tries to coerce `"closed"` into a `TicketStatus` member. It calls `TicketStatus("closed")` (the value lookup from lesson 01). That raises `ValueError: 'closed' is not a valid TicketStatus`. Pydantic catches the `ValueError` and converts it into a 422 response with a structured error body.

The 422 response shape is:

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["query", "status"],
      "msg": "Input should be 'open', 'in_progress', 'blocked' or 'done'",
      "input": "closed",
      "ctx": {"expected": "'open', 'in_progress', 'blocked' or 'done'"}
    }
  ]
}
```

The `"type": "enum"` is Pydantic's enum-error type tag — clients can pattern-match on it. The `"loc"` tells the client which parameter failed. The `"msg"` lists the allowed values, derived from the OpenAPI `enum` keyword. The `"input"` echoes the rejected value.

**Why HTTP 422 and not 400?** Because HTTP 400 means "the request itself is malformed" — a syntax error, a missing required header. HTTP 422 means "the request is syntactically valid but semantically rejected" — the query string is fine, the value just is not in the allowed set. FastAPI's choice of 422 for validation errors follows the WebDAV convention (RFC 4918) and is the same convention every JSON:API server uses. It is a deliberate choice, and it lets clients distinguish "your request was malformed" (400) from "your request was valid but the value was wrong" (422).

### Lines 66–69: The `Literal` route behaves the same way

```python
r = client.get("/literal/42?status=closed")
print("\n--- GET /literal/42?status=closed ---")
print(r.status_code, "— same 422")
```

The `Literal` route returns the same 422 status code on an invalid value. Pydantic validates `Literal["open", "in_progress", "blocked", "done"]` the same way it validates `TicketStatus` — both produce an `enum` schema and both reject invalid values with HTTP 422. From the client's perspective, the two routes are indistinguishable.

**Why does `Literal` produce the same schema?** Because Pydantic's schema generator checks for `typing.Literal` and emits an `enum` keyword with the literal values. The runtime behaviour is identical to a `StrEnum` with the same values. The difference is on the Python side — `StrEnum` gives you a class with methods and iteration; `Literal` is just a type hint.

## Execution Trace

```bash
$ python boardly/api/tickets.py
--- TicketStatus in the OpenAPI schema ---
{'type': 'string', 'enum': ['open', 'in_progress', 'blocked', 'done'], 'title': 'TicketStatus'}

--- GET /tickets/42 (default) ---
200 {'id': 42, 'status': 'open'}

--- GET /tickets/42?status=closed ---
422 {'detail': [{'type': 'enum', 'loc': ['query', 'status'], 'msg': "Input should be 'open', 'in_progress', 'blocked' or 'done'", 'input': 'closed', 'ctx': {'expected': "'open', 'in_progress', 'blocked' or 'done'"}}]}

--- GET /literal/42?status=closed ---
422 — same 422
```

## Common Mistakes

### Mistake 1: Using plain `Enum` instead of `StrEnum` for the API field

```python
class TicketStatus(Enum):     # plain Enum, not StrEnum
    OPEN = "open"
    DONE = "done"

class TicketOut(BaseModel):
    status: TicketStatus

# Response: {"status": "TicketStatus.OPEN"}   <- the bug
```

**Symptom:** The JSON response contains `"TicketStatus.OPEN"` instead of `"open"`. Clients receive a string they did not expect.
**Why:** Plain `Enum`'s `__str__` returns the qualified name. Pydantic's serialiser calls `str(member)` and gets the wrong value. This is the lesson 02 surprise, applied to the API surface.
**Fix:** Use `StrEnum` (3.11+). The `__str__` override returns `self._value_`, and the JSON response contains the wire value.

### Mistake 2: Forgetting the `response_model`

```python
@app.get("/tickets/{id}")     # no response_model
def get_ticket(id: int) -> dict:
    return {"id": id, "status": TicketStatus.OPEN}
```

**Symptom:** The response is `{"id": 42, "status": "TicketStatus.OPEN"}` — no validation, no schema, wrong wire value.
**Why:** Without a `response_model`, FastAPI does not run Pydantic on the response. The `dict` is serialised with `json.dumps`, which calls `str(member)` on the `StrEnum` — and for plain `StrEnum`, that *does* return the value... wait, does it? Actually yes, `str(StrEnum.OPEN)` returns `"open"`. So the wire value is correct. But there is no schema entry, no validation, no documentation.
**Fix:** Always specify `response_model`. It costs nothing at runtime (the validation is fast) and it gives you the OpenAPI schema, the validation safety net, and the documentation.

### Mistake 3: Returning the member's `.name` instead of the member itself

```python
@app.get("/tickets/{id}", response_model=TicketOut)
def get_ticket(id: int) -> TicketOut:
    return TicketOut(id=id, status=TicketStatus.OPEN.name)   # bug: "OPEN" not the member
```

**Symptom:** The route raises `ResponseValidationError` because `"OPEN"` is not a valid `TicketStatus` member value. (`TicketStatus("OPEN")` raises `ValueError`.)
**Why:** `.name` returns the source-code name (`"OPEN"`), not the wire value (`"open"`). Pydantic tries to coerce `"OPEN"` back into a `TicketStatus` member and fails.
**Fix:** Return the member itself (`TicketStatus.OPEN`), or return the value (`TicketStatus.OPEN.value` if you must serialise manually). Never return `.name` for a wire field.

## Engineering Trade-Offs

**Decision:** Use `StrEnum` with `auto()` + `_generate_next_value_` returning `name.lower()` and `@unique` for every API-facing string enum. Use `Literal[...]` only for tiny sets (≤3 values) referenced from a single route.
**Both sides:** `StrEnum` gives you a class with methods, `__members__` iteration, `auto()`, and `@unique` — but it adds a class to your module. `Literal` is lighter (no class) but duplicates the values everywhere it appears and has no methods. The trade-off is "lighter code, more duplication" vs "one class, one source of truth".
**Commitment:** `boardly` uses `StrEnum` for every status, role, kind, and type field that crosses the API. `Literal` is reserved for one-off values that are not part of the domain model (e.g., a `Literal["summary", "detailed"]` `detail` flag on a single GET endpoint).

## A stdlib `IntEnum` you already use: `http.HTTPStatus`

You have been writing `IntEnum` members since the day you wrote your first FastAPI route that returned anything other than 200. The standard library ships one — and only one — production-grade `IntEnum` you will reach for daily: `http.HTTPStatus` from the `http` module.

```python
# boardly/api/tickets.py — the status_code argument is an IntEnum member
from http import HTTPStatus
from fastapi import FastAPI, Response

@app.post("/tickets", status_code=HTTPStatus.CREATED)        # 201
def create_ticket(...) -> TicketOut: ...

@app.delete("/tickets/{id}", status_code=HTTPStatus.NO_CONTENT)  # 204
def delete_ticket(id: int) -> None: ...

@app.get("/health")
def health() -> dict:
    return {"status": HTTPStatus.OK.phrase}                   # "OK"
```

**Why this matters here.** `HTTPStatus` is a subclass of `IntEnum` (verified: `issubclass(HTTPStatus, IntEnum)` is `True`), and `IntEnum` is `(int, Enum)`. So `HTTPStatus.CREATED == 201` is `True` (not `False`, the way it would be for a plain `Enum` — see [[09-enum/01-Enum-Basics]] for the `TicketStatus.OPEN == 1` is `False` lesson). That is the whole reason FastAPI accepts `status_code=HTTPStatus.CREATED` interchangeably with `status_code=201` — the underlying integer value flows straight through to the WSGI/ASGI response.

**Why it is an `IntEnum` and not a `StrEnum`.** HTTP status codes *are* integers on the wire (`HTTP/1.1 201 Created`). The integer value (`201`) is the wire form; the `.name` (`"CREATED"`) is the source-code form; the `.phrase` (`"Created"`, a `.phrase` attribute `IntEnum` does not have but `HTTPStatus` adds via a custom `_http_` mapping) is the human-readable form. Three representations of the same concept, one `IntEnum` class to hold them all. The same shape you saw in lesson 02 with `Priority(IntEnum)` — `Priority.HIGH == 3` — applied to a much bigger domain.

**Note — `HTTPStatus` is a *direct* subclass of `IntEnum`.** Verified on the 3.12 runtime: `HTTPStatus.__bases__` is `(IntEnum,)` and `issubclass(HTTPStatus, IntEnum)` is `True`. The class is defined with each member constructed by name + (value, phrase) tuple, and the `.phrase` attribute is added by the `HTTPStatus` class itself (not inherited from `IntEnum`) via the `_http_` lookup table. The members iterate in numeric order (`HTTPStatus.CONTINUE` (100) comes before `HTTPStatus.OK` (200)), and `HTTPStatus.CONTINUE < HTTPStatus.OK` is `True` — the integer ordering is inherited from `int` via `IntEnum`. Plain `Enum` would iterate in *definition* order; `IntEnum` gives you numeric order for free. Use `for status in HTTPStatus:` if you ever need to walk the full table — useful for a "list every status this server can return" introspection route.

**Why use `HTTPStatus.CREATED` and not `201`?** Three reasons, all already familiar from this lesson: (1) the named constant is grep-able, the magic number is not; (2) typo-protection — `HTTPStatus.CREAETED` raises `AttributeError` at import, `201`-vs-`211` does not; (3) the OpenAPI schema documents the status code by name (`"CREATED"`) when you use the enum form, not just by number. The cost is one extra import line. `boardly`'s rule: every `status_code=` argument in every route uses `HTTPStatus.NAME`, never a bare integer.

## Exercises

1. **Exercise 1 — Inspect the schema.** Run the script and confirm the `TicketStatus` schema contains `"enum": ["open", "in_progress", "blocked", "done"]`. `Verify: python boardly/api/tickets.py | head -5`
2. **Exercise 2 — Add a member.** Add `CANCELLED = auto()` to `TicketStatus`. Re-run. Confirm the schema's `enum` array now has five entries. `Verify: python -c "from boardly.api.tickets import app; from fastapi.testclient import TestClient; c=TestClient(app); s=c.get('/openapi.json').json(); print(len(s['components']['schemas']['TicketStatus']['enum']))"`
3. **Exercise 3 — Trigger 422.** Hit `/tickets/42?status=garbage` and confirm the response is HTTP 422 with `"type": "enum"` in the detail. `Verify: python -c "from boardly.api.tickets import app; from fastapi.testclient import TestClient; c=TestClient(app); r=c.get('/tickets/42?status=garbage'); assert r.status_code==422; print(r.json()['detail'][0]['type'])"`
4. **Exercise 4 — Compare with `Literal`.** Add a second route using `Literal["open", "done"]` and inspect its OpenAPI schema. Confirm the `enum` keyword matches. `Verify: python -c "from boardly.api.tickets import app; from fastapi.testclient import TestClient; c=TestClient(app); s=c.get('/openapi.json').json(); print([p for p in s['paths']])"`
5. **Exercise 5 — Build a response_model with two enums.** Define `MemberRole(StrEnum)` with `OWNER`, `MEMBER`, `VIEWER`. Add a `MemberOut(BaseModel)` with `id: int` and `role: MemberRole`. Add a route `/members/{id}` that returns it. Confirm the OpenAPI schema has two enum schemas. `Verify: python -c "from boardly.api.tickets import app; from fastapi.testclient import TestClient; c=TestClient(app); s=c.get('/openapi.json').json(); print('MemberRole' in s['components']['schemas'])"`

## Verification

```bash
$ python boardly/api/tickets.py | head -2
--- TicketStatus in the OpenAPI schema ---
{'type': 'string', 'enum': ['open', 'in_progress', 'blocked', 'done'], 'title': 'TicketStatus'}
$ python -c "from boardly.api.tickets import app, TicketStatus; from fastapi.testclient import TestClient; c=TestClient(app); r=c.get('/tickets/42'); print(r.json())"
{'id': 42, 'status': 'open'}
$ python -c "from boardly.api.tickets import app; from fastapi.testclient import TestClient; c=TestClient(app); r=c.get('/tickets/42?status=closed'); print(r.status_code)"
422
```

## Previously Learned Here

- [[09-enum/02-IntEnum-and-StrEnum]] — `StrEnum`'s `__str__` override is what makes FastAPI serialise `"open"` instead of `"TicketStatus.OPEN"`.
- [[09-enum/04-auto-and-value]] — `auto()` with `_generate_next_value_` returning `name.lower()` is the canonical `StrEnum` pattern for API wire values.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated[TicketStatus, Query(...)]` is the FastAPI idiom for adding OpenAPI metadata to a parameter.

## What's Next

[[10-inspect/06-How-FastAPI-uses-inspect]] — You have now seen the *output* of FastAPI's enum handling: the OpenAPI schema, the validation, the serialisation. The next section shows you the *input*: the call chain `inspect.signature(route.endpoint)` → `typing.get_type_hints(..., include_extras=True)` → for each `Annotated[TicketStatus, Query(...)]` parameter, resolve the dependency tree. The lesson shows you a minimal re-implementation of FastAPI's dependency resolution, with `TicketStatus` as the example field.

- **Section 10 — `inspect`** — `signature`, `Parameter`, `get_type_hints`, `iscoroutinefunction`, `bind`/`BoundArguments`.
- **[[10-inspect/06-How-FastAPI-uses-inspect]]** — the senior deep-dive that ties the `inspect` section back to the `StrEnum` you just declared.
- **[[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]]** — the cross-comparison: `StrEnum` works with Pydantic natively; `@dataclass` fields do not auto-serialise enums.

## Sources

- **FastAPI documentation — Handling enums** — https://fastapi.tiangolo.com/tutorial/path-params/#path-parameters-with-enums — accessed 2026-10-23 — the official FastAPI tutorial section that shows `Enum` on a path parameter.
- **Pydantic V2 documentation — Enum handling** — https://docs.pydantic.dev/latest/concepts/fields/#enums — accessed 2026-10-23 — the Pydantic-side behaviour: how `StrEnum` fields are validated and serialised.
- **Python `enum` module documentation — `StrEnum`** — https://docs.python.org/3/library/enum.html#enum.StrEnum — accessed 2026-10-23 — the `StrEnum.__str__` override that is the whole reason FastAPI serialises `"open"` and not `"TicketStatus.OPEN"`.
- **PEP 593 — Flexible function and variable annotations** — https://peps.python.org/pep-0593/ — accessed 2026-10-23 — the `Annotated` PEP that `Annotated[TicketStatus, Query(...)]` is built on. Section 10 lesson 06 walks FastAPI's read path for this metadata.
- **RFC 4918 — HTTP 422 Unprocessable Entity** — https://datatracker.ietf.org/doc/html/rfc4918#section-11.2 — accessed 2026-10-23 — the WebDAV RFC that defined 422 for semantic validation errors. FastAPI's choice of 422 for enum-validation failures follows this convention.

## What We Learned

- You can now read FastAPI's three-step enum handling: schema generation (the `enum` keyword in OpenAPI), query validation (HTTP 422 on invalid), response serialisation (`str(member)` returns the wire value).
- You can now inspect `/openapi.json` and find the `{"type": "string", "enum": [...]}` block for any `StrEnum` field.
- You can now predict that an invalid query value returns HTTP 422 with `"type": "enum"` in the structured error body.
- You can now write `Literal[...]` as the no-class alternative and explain the trade-off (lighter code, more duplication).
- You can now choose between `StrEnum` and `Literal` for a given API field based on whether it has business logic, is referenced from multiple modules, and whether the set is small.
