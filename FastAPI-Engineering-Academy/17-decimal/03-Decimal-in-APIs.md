---
title: "Lesson 03: Decimal in APIs"
aliases:
 - FastAPI Decimal
 - Pydantic Decimal
 - Decimal JSON serialisation
 - never accept float from JSON
tags:
 - decimal
 - canonical
 - python-stdlib
 - fastapi
 - pydantic
 - openapi
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "45–60 minutes"
prerequisites:
 - "[[17-decimal/01-Decimal-Basics]]"
 - "[[17-decimal/02-Context-and-precision]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[09-enum/05-Enum-in-APIs]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
first_taught_in: "17-decimal/03-Decimal-in-APIs"
---

# Lesson 03: Decimal in APIs

*How `boardly`'s `POST /projects` endpoint accepts `{"budget": "1000.00"}`, validates the value as a `Decimal`, computes the remaining budget exactly, and returns `{"budget": "1000.00"}` to the client — and the one-line `field_validator` that turns Pydantic's silent float-acceptance into a loud `422`.*

**You're at the very beginning of Section 17 — three lessons in. This is the FastAPI connection.**

You can construct a `Decimal` and you can scope its precision. Now you need to put it on the wire. A `Decimal` field in a Pydantic model serialises to a JSON string (`"1.00"`, not `1.0`), and that is the *correct* behaviour — but it has a surprise. The request side is the surprise: Pydantic v2 *does* accept a JSON number for a `Decimal` field, captures the float's exact value, and stores it. That is the section's silent bug, on the boundary, where the section's cardinal rule ("never accept a float") has to be enforced by hand. This lesson walks the full request → validate → compute → respond path with `boardly`'s `POST /projects` endpoint, shows you the validator that makes float acceptance a `422`, and introduces the `int`-cents alternative for systems where `Decimal` overhead is genuinely too high. Take your time. Type every example. **This is how you learn.**

#decimal #canonical #fastapi #pydantic

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare a `Decimal` field in a Pydantic model** — write `budget: Decimal` and predict what the OpenAPI schema's `budget` property will say for both the request and the response.
2. **Read the serialisation contract** — explain why `str(Decimal("1.00"))` is `"1.00"` and why FastAPI's `jsonable_encoder` and `model_dump_json()` emit a JSON string for a `Decimal`, not a JSON number.
3. **Implement the "never accept float" rule** with a `field_validator(mode='before')` that rejects `isinstance(value, float)` and returns a `422` to the client.
4. **Apply the `Annotated[Decimal, Field(max_digits=..., decimal_places=...)]` constraint** to bound the digits and decimal places, and explain why this constraint also catches the `0.1 + 0.2` float imprecision as a side effect.
5. **Walk the int-cents alternative** — `amount_cents: int` instead of `amount: Decimal`; explain when it wins (JSON-native, faster, no precision trap) and when it loses (scale tracking, fractional-cent pricing).
6. **Read a FastAPI route's OpenAPI schema** and identify which fields are `Decimal`-typed (request: `anyOf: [number, string]`; response: `string`).

## Prerequisites

Before starting, you need:

- **The string-constructor rule** — [[17-decimal/01-Decimal-Basics]]. This lesson's `field_validator` exists to enforce that rule at the API boundary; if you do not understand *why* the rule matters, the validator looks paranoid.
- **`localcontext()` and `quantize()`** — [[17-decimal/02-Context-and-precision]]. The route's tax computation needs half-up rounding scoped to a single function.
- **A typed model to attach the field to** — [[06-dataclasses/01-dataclass-Basics]]. The route uses a Pydantic `BaseModel`, but the dataclass lesson is where the field-with-default machinery lives; Pydantic mirrors it.
- **FastAPI's `response_model` and `field_validator`** — basic familiarity with FastAPI route signatures and Pydantic v2 validators. About 45–60 minutes of focused time.

**The most common gap: assuming Pydantic rejects JSON numbers for a `Decimal` field.**

It does not. Pydantic v2's `Decimal` field accepts both `"1.00"` (JSON string) and `1.00` (JSON number), converts each to a `Decimal`, and stores the result. For the string path the result is `Decimal("1.00")` (exact). For the number path, the result is `Decimal(<float>)` — which captures the float's exact binary value. A JSON `0.1` becomes `Decimal("0.1")` (Pydantic happens to call `str(float)` first, which round-trips for `0.1`), but a JSON `0.30000000000000004` becomes `Decimal("0.30000000000000004")` (the imprecision is exposed). The boundary is unsafe by default; you have to make it safe.

## The Problem

Here is the bug, on the wire. Read it slowly.

```python
# boardly/api/bad_routes.py — the bad old days
from fastapi import FastAPI
from pydantic import BaseModel
from decimal import Decimal

class Project(BaseModel):
    name: str
    budget: Decimal

app = FastAPI()

@app.post('/projects', response_model=Project)
def create(p: Project):
    return p
```

You deploy that. A client POSTs `{"name": "alpha", "budget": 0.1}` — a JSON number. Pydantic sees a `Decimal` field on the request, sees the JSON number `0.1`, and constructs `Decimal(0.1)`... or does it? Actually, Pydantic v2 does something subtler: it converts the JSON number to a Python `float` (because that is what `json.loads` produces), then calls `Decimal(str(float))`. For `0.1`, `str(0.1)` is `"0.1"` (since Python 3.2, `repr(float)` and `str(float)` round-trip the shortest representation that uniquely identifies the float), so `Decimal("0.1")` is what gets stored — looking clean. But for `0.1 + 0.2 = 0.30000000000000004`, the float's imprecision survives into the stored `Decimal`. The boundary is silently wrong for the cases where `str(float)` does not round-trip cleanly.

Worse: the OpenAPI schema for the *request* model declares `budget` as `anyOf: [{type: number}, {type: string}]`. The schema is honest — the route really does accept both. But the OpenAPI UI lets the user click "number" and post `0.1`, and you cannot tell from the schema which path (string or number) any given client will take. You ship with two behaviours and no enforcement.

The fix is the `field_validator(mode='before')` that this lesson teaches: reject `isinstance(value, float)` at the boundary, force the client to send a string. The schema narrows to `{type: string}`. The route is now either safe or loudly wrong; never silently wrong.

## The Code

```python
# boardly/api/projects_routes.py
"""POST /projects with a Decimal budget — the safe version."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing_extensions import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from fastapi.encoders import jsonable_encoder


# 1. The request model — rejects floats at the boundary
class ProjectCreate(BaseModel):
    name: str
    budget: Annotated[Decimal, Field(max_digits=12, decimal_places=2)]

    @field_validator("budget", mode="before")
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("budget must be a JSON string, not a number")
        return v

# 2. The response model — same fields, separate class (so we can differ later)
class ProjectOut(BaseModel):
    name: str
    budget: Decimal

# 3. The boardly app
app = FastAPI(title="boardly")

@app.post("/projects", response_model=ProjectOut)
def create_project(p: ProjectCreate) -> ProjectOut:
    """Create a project; tax-aware remaining-budget computation lives in the service."""
    return ProjectOut(name=p.name, budget=p.budget)

@app.get("/projects/{name}/remaining", response_model=ProjectOut)
def remaining(name: str, spent: Decimal = Decimal("0.00")) -> ProjectOut:
    """Compute remaining budget given a spent amount; rounds half-up to 2dp."""
    budget = Decimal("1000.00")
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        remaining_value = (budget - spent).quantize(Decimal("0.01"))
    return ProjectOut(name=name, budget=remaining_value)

# 4. The serialisation contract — str(Decimal) round-trips
sample = ProjectOut(name="alpha", budget=Decimal("1000.00"))
print("model_dump:", sample.model_dump())          # {'name': 'alpha', 'budget': Decimal('1000.00')}
print("model_dump_json:", sample.model_dump_json())  # {"name":"alpha","budget":"1000.00"}
print("jsonable_encoder:", jsonable_encoder(sample))  # {'name': 'alpha', 'budget': '1000.00'}
print("str(Decimal):", str(Decimal("1.00")))        # 1.00

# 5. The int-cents alternative — for systems that need the speed
class ProjectCents(BaseModel):
    name: str
    budget_cents: int = Field(ge=0)   # $1.00 stored as 100

print("int-cents json:", ProjectCents(name="alpha", budget_cents=1000).model_dump_json())
# {"name":"alpha","budget_cents":1000}
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 1–9: Imports and the field validator location

```python
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing_extensions import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from fastapi.encoders import jsonable_encoder
```

The `decimal` imports are the section's toolkit: `Decimal` (the type), `ROUND_HALF_UP` (the rounding mode for consumer tax), and `localcontext` (the scoped context manager from lesson 02). The `Annotated` import from `typing_extensions` (or `typing` on Python 3.9+) is what lets us attach `Field(max_digits=12, decimal_places=2)` to the `Decimal` type — the same `Annotated` machinery you met in [[01-typing/02-Annotated-and-Metadata]].

The Pydantic imports are three: `BaseModel` (the model base class), `Field` (the per-field constraint helper — the Pydantic analogue of `dataclasses.field`), and `field_validator` (the per-field validator decorator, new in Pydantic v2 — it replaces the v1 `@validator`). The `fastapi.encoders.jsonable_encoder` import is for the explicit serialisation demonstration in the script's print lines; in a real route you would not import it directly — FastAPI calls it for you on the `response_model` return value.

**Why `Annotated[Decimal, Field(max_digits=12, decimal_places=2)]` and not `Decimal = Field(max_digits=12, decimal_places=2)`?** Because Pydantic v2 moved constraint attachment to the type via `Annotated`. The v1 form (`budget: Decimal = Field(...)`) still works for backward compatibility, but the v2-idiomatic form puts the metadata inside the type annotation. The two are equivalent in effect; the `Annotated` form is what FastAPI's OpenAPI generator reads when building the schema, and it composes better with other `Annotated` metadata (e.g., `Annotated[Decimal, Field(...), SomeType]`).

### Lines 11–21: The request model with the float-rejecting validator

```python
class ProjectCreate(BaseModel):
    name: str
    budget: Annotated[Decimal, Field(max_digits=12, decimal_places=2)]

    @field_validator("budget", mode="before")
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("budget must be a JSON string, not a number")
        return v
```

The `Field(max_digits=12, decimal_places=2)` constraint bounds the *stored `Decimal`* to 12 significant digits and 2 decimal places — the budget is a money field and money has two decimal places. The `Annotated[Decimal, Field(...)]` form is Pydantic v2's idiomatic way to attach metadata to the type (see [[01-typing/02-Annotated-and-Metadata]]); the v1 form `budget: Decimal = Field(...)` still works for backward compatibility but does not compose with other `Annotated` metadata.

**Note — Pydantic v2 `field_validator` decorator order**

Pydantic v2's `@field_validator` decorator (replacing v1's `@validator`) must be the outermost decorator. Below it sits `@classmethod`, because the function takes `cls` as its first argument (it is a class method). The order is: `@field_validator(...)` then `@classmethod` then `def`. Any other order breaks — for example, `@classmethod` above `@field_validator` would treat the validator function as a plain class method and the field validator decorator would never see it.

The `mode="before"` argument is the critical piece. Pydantic v2 runs validators at three points: `before` (before Pydantic's own type coercion), `after` (after coercion, before storage), and `wrap` (around coercion, with the validator calling the inner). For our use case — rejecting floats *before* Pydantic coerces them into `Decimal` — `mode="before"` is the right choice. Inside, `isinstance(v, float)` checks the type: if the JSON value was a number, `json.loads` produced a `float`, and the validator sees a `float`. If the JSON value was a string, the validator sees a `str`. We raise `ValueError` on the float path; Pydantic catches the `ValueError` and converts it into a `422` response with the error message in the body.

**Why `mode='before'` and not `mode='after'`?** Because by the time the `mode='after'` validator runs, Pydantic has already called `Decimal(value)` on the input — the float has already been converted (via `str(float)` then `Decimal(str)`) and stored. The `mode='after'` validator would see a `Decimal` and have to inspect `as_tuple()` to detect the imprecision — possible but fragile. `mode='before'` lets us inspect the raw Python value (the `float` from `json.loads`) and reject it directly, before any coercion. The `before` mode is the right tool for type-rejection; the `after` mode is the right tool for value-rejection.

### Lines 23–26: The response model — same fields, separate class

```python
class ProjectOut(BaseModel):
    name: str
    budget: Decimal
```

The response model has the same fields as the request model — but no validator, no `Annotated` constraint. The reason for the *separate* class is separation of concerns: the request model defines what clients may *send* (a string budget, two decimal places, max 12 digits); the response model defines what the server *returns* (a `Decimal` that Pydantic will serialise as a JSON string). The two contracts can drift over time — for example, the response might later include a `remaining: Decimal` field that the request never has, or a `created_at: datetime` field. Splitting the classes now is cheap; merging them later is a breaking change.

Pydantic v2's `model_dump()` returns a Python dict with `Decimal` instances intact (`{'budget': Decimal('1000.00')}`); `model_dump_json()` returns a JSON string with `Decimal` serialised as a JSON string (`{"budget":"1000.00"}`). The JSON-string serialisation is the contract — the client always sees a string, never a number.

**Why serialise `Decimal` as a JSON string and not a JSON number?** Three reasons. First, JSON numbers in most parsers (including JavaScript's, which is the dominant client) are IEEE 754 doubles — the same binary-float imprecision we are trying to escape. If we serialised `Decimal("1000.00")` as the JSON number `1000.00`, JavaScript would parse it into a `double`, and `1000.00 + 12.34` on the client would have the same bug we just fixed on the server. The string form `"1000.00"` round-trips through `parseFloat` (or `Number()`) on the client *only when the client chooses to*, and most clients that care pass the string straight through to the next request without ever converting to a number. Second, JSON numbers cannot represent trailing zeros: `1.00` becomes `1.0` becomes `1` in transit. The string form preserves the digits exactly. Third, the JSON Schema spec recommends that arbitrarily-large numbers be sent as strings, and `Decimal` is the type for arbitrarily-large numbers.

### Lines 28–35: The route and the `response_model`

```python
app = FastAPI(title="boardly")

@app.post("/projects", response_model=ProjectOut)
def create_project(p: ProjectCreate) -> ProjectOut:
    """Create a project; tax-aware remaining-budget computation lives in the service."""
    return ProjectOut(name=p.name, budget=p.budget)
```

The `@app.post("/projects", response_model=ProjectOut)` decorator does two things. The `"/projects"` argument registers the route path. The `response_model=ProjectOut` argument tells FastAPI: "Take whatever this function returns, run it through `ProjectOut.model_validate(...)` (Pydantic validation), then call `jsonable_encoder(...)` to convert to JSON-serialisable Python objects, then `json.dumps(...)` to produce the response body." The response model is the *contract* the route publishes to OpenAPI; FastAPI's generator emits the `ProjectOut` schema under `components/schemas/` and references it from the route's `responses[200]`.

The `p: ProjectCreate` parameter is the request body. FastAPI sees a Pydantic model as the parameter type, parses the request body as JSON, calls `ProjectCreate.model_validate(parsed_json)`, and passes the resulting instance to the function. If validation fails (a `ValidationError` is raised), FastAPI converts it to a `422 Unprocessable Entity` response with the error details in the body. That is the path our `reject_float` validator uses — the `ValueError` it raises becomes a `ValidationError`, which becomes a `422`.

**Why specify both `p: ProjectCreate` and `-> ProjectOut`?** Because FastAPI uses the parameter type for the request schema and the return type (or `response_model`, which overrides the return type) for the response schema. The two are independent — the request can be `ProjectCreate` (with the float-rejecting validator) and the response can be `ProjectOut` (without it). The separation is what lets the route accept a constrained input and return a less-constrained output.

### Lines 37–44: The tax-aware remaining-budget computation

```python
@app.get("/projects/{name}/remaining", response_model=ProjectOut)
def remaining(name: str, spent: Decimal = Decimal("0.00")) -> ProjectOut:
    """Compute remaining budget given a spent amount; rounds half-up to 2dp."""
    budget = Decimal("1000.00")
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        remaining_value = (budget - spent).quantize(Decimal("0.01"))
    return ProjectOut(name=name, budget=remaining_value)
```

The route's `spent: Decimal = Decimal("0.00")` parameter is a FastAPI query parameter — FastAPI parses it from the query string (e.g., `?spent=12.34`) into a `Decimal`. The default `Decimal("0.00")` is the value used when the query parameter is omitted. Note the default is a string-constructed `Decimal`, never a float — the section's cardinal rule applies to defaults too.

Inside the function, `with localcontext() as ctx: ctx.rounding = ROUND_HALF_UP` is the scoped-override pattern from lesson 02. The subtraction `budget - spent` is exact (the result has at most 2 decimal places from each operand, summing to 2 decimal places in the result — no precision loss). The `quantize(Decimal("0.01"))` forces the result to exactly 2 decimal places with the scoped `ROUND_HALF_UP` rounding mode — the consumer-tax convention. The result is a `Decimal` with `exponent=-2` and the exact value `Decimal("987.66")` (for `spent=Decimal("12.34")`).

The `ProjectOut(name=name, budget=remaining_value)` constructs the response model. The `remaining_value` is already a `Decimal` with the right exponent and digits; Pydantic accepts it as-is (it does not re-coerce or re-round) and `model_dump_json()` produces `{"name":"alpha","budget":"987.66"}`.

**Why scope the rounding in a route handler and not at module load?** Because the consumer-tax rounding is a property of *this computation*, not of every `Decimal` operation in the process. Setting `getcontext().rounding = ROUND_HALF_UP` at module load would affect every other route on the same thread — and on a FastAPI server with a thread pool, that means every other concurrent request. The scoped `with localcontext()` block confines the override to this function's body, and the change reverts on `__exit__`. That is the lesson 02 discipline, applied at the API boundary.

### Lines 46–51: The serialisation contract

```python
sample = ProjectOut(name="alpha", budget=Decimal("1000.00"))
print("model_dump:", sample.model_dump())          # {'name': 'alpha', 'budget': Decimal('1000.00')}
print("model_dump_json:", sample.model_dump_json())  # {"name":"alpha","budget":"1000.00"}
print("jsonable_encoder:", jsonable_encoder(sample))  # {'name': 'alpha', 'budget': '1000.00'}
print("str(Decimal):", str(Decimal("1.00")))        # 1.00
```

`sample.model_dump()` returns a plain `dict` with the `Decimal` instance intact. This is the "Python-native" form — useful for passing the model's data to other Python code that expects `Decimal`s (a database layer, a billing service). The `Decimal` is not converted; it is the same object.

`sample.model_dump_json()` returns a JSON string. The `Decimal` is converted via `str(Decimal)` — that is `Decimal.__str__`, which returns the digit sequence with no exponent notation for normal-magnitude values. `str(Decimal("1000.00"))` is `"1000.00"` — exactly the digits you typed, with the trailing zeros preserved. Pydantic v2 uses `str(Decimal)` (not `repr(Decimal)`, which would be `Decimal('1000.00')`, and not a float conversion) for the JSON form.

`jsonable_encoder(sample)` is what FastAPI calls internally before `json.dumps`. It returns a Python object that `json.dumps` can handle — for a `Decimal`, that is a `str`. The function is the bridge between Pydantic's `model_dump` (which keeps `Decimal`s) and the JSON encoder (which cannot handle `Decimal`s natively — `json.dumps(Decimal("1.00"))` raises `TypeError: Object of type Decimal is not JSON serializable`).

`str(Decimal("1.00"))` is `"1.00"` — the contract that everything else depends on. The string form is what the client sees; the string form is what round-trips through JSON; the string form is what the next request can send back. The whole section's "always pass a string" rule is, at the API level, "always send and receive a string" — and Pydantic's `Decimal` serialisation does that for you, automatically, on every response.

**Why does `json.dumps(Decimal("1.00"))` raise?** Because the `json` module's default encoder knows about `int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, `None` — and nothing else. `Decimal` is not in that list; the encoder calls `default(obj)`, which raises `TypeError`. FastAPI's `jsonable_encoder` pre-walks the object tree and converts `Decimal` to `str` before the standard `json.dumps` ever sees it. That pre-walk is why FastAPI can return Pydantic models with `Decimal` fields from route handlers — without it, every `Decimal`-returning route would raise `TypeError` at response time.

### Lines 53–58: The int-cents alternative

```python
class ProjectCents(BaseModel):
    name: str
    budget_cents: int = Field(ge=0)   # $1.00 stored as 100

print("int-cents json:", ProjectCents(name="alpha", budget_cents=1000).model_dump_json())
# {"name":"alpha","budget_cents":1000}
```

The `int`-cents alternative stores every money amount as an integer count of the smallest currency unit (cents, for USD/EUR/etc.). `$1.00` becomes `100`; `$1.50` becomes `150`; `$0.01` becomes `1`. Arithmetic is integer arithmetic (`150 + 100 = 250`), which is exact on every platform and needs no `Decimal` machinery at all. The JSON form is a JSON number (`1000`), which serialises natively in every JSON parser without the string-form workaround.

The trade-off is what the alternative gives up:

- **Scale tracking.** The `Decimal` form carries its own scale (`as_tuple().exponent`); the `int`-cents form has to know, by convention, that `1000` means `$10.00` not `$1000` or `$1.000`. That convention has to be enforced at every boundary — display, persistence, client communication.
- **Fractional cents.** A per-API-call price of `$0.0001` cannot be represented as integer cents without scaling up to a smaller unit (microdollars? ten-thousandths of a cent?). The `Decimal` form handles arbitrary scales for free.
- **Display conversion.** Every place that prints a money value has to divide by 100 and format the result — `f"${cents / 100:.2f}"` or, more safely, `Decimal(cents) / Decimal(100)`. That conversion is now a code path with its own potential bugs.

**Why choose `int`-cents over `Decimal` at all?** Speed and JSON-nativeness. Integer arithmetic in Python is roughly 10× faster than `Decimal` arithmetic (the C implementation in CPython 3.11+ narrowed the gap, but it is still 2–5× slower). And the JSON number form parses natively on every client without a string→Decimal conversion step. For a high-throughput system where every amount is a whole-cent multiple (which is most consumer-facing billing — ticket prices, line items, totals), the speed wins are real and the precision trap is fully avoided. The `boardly` project uses `Decimal` because the team is small and the scale-tracking buys more than the speed costs; a larger team or a higher-traffic system might reasonably choose `int`-cents. The decision is documented in [[25-Reference-Library/Engineering-Decision-Log]].

## Execution Trace

```bash
$ uv run python boardly/api/projects_routes.py
model_dump: {'name': 'alpha', 'budget': Decimal('1000.00')}
model_dump_json: {"name":"alpha","budget":"1000.00"}
jsonable_encoder: {'name': 'alpha', 'budget': '1000.00'}
str(Decimal): 1.00
int-cents json: {"name":"alpha","budget_cents":1000}
```

To see the route behaviour end-to-end, start a server and exercise it with the FastAPI `TestClient`:

```bash
$ uv run python -c "
from fastapi.testclient import TestClient
from boardly.api.projects_routes import app
c = TestClient(app)
print('str ok  :', c.post('/projects', json={'name':'a','budget':'1.00'}).json())
print('float  :', c.post('/projects', json={'name':'b','budget':0.1}).status_code)
print('0.1+0.2:', c.post('/projects', json={'name':'c','budget':0.1+0.2}).status_code)
print('too many dp:', c.post('/projects', json={'name':'d','budget':'1.234'}).status_code)
print('remaining:', c.get('/projects/alpha/remaining?spent=12.34').json())
"
str ok  : {'name': 'a', 'budget': '1.00'}
float  : 422
0.1+0.2: 422
too many dp: 422
remaining: {'name': 'alpha', 'budget': '987.66'}
```

The `float` and `0.1+0.2` requests both return `422` — our `reject_float` validator caught them. The `1.234` request returns `422` — the `max_digits=12, decimal_places=2` constraint caught the third decimal place. The `?spent=12.34` query is parsed as `Decimal("12.34")`, the subtraction is exact, the `quantize(Decimal("0.01"))` under `ROUND_HALF_UP` produces `Decimal("987.66")`, and the response is `{"budget":"987.66"}`.

## Common Mistakes

### Mistake 1: Forgetting the `field_validator` and accepting floats

```python
class ProjectCreate(BaseModel):
    name: str
    budget: Decimal   # no validator — accepts floats silently
```

**Symptom:** A client posts `{"budget": 0.1}` (a JSON number). The route accepts it with `200 OK`. Most of the time the result looks clean. But a client that does JavaScript math (`0.1 + 0.2`) and posts the result gets `0.30000000000000004` stored as a `Decimal`, and the imprecision compounds through your billing pipeline.
**Why:** Pydantic v2's `Decimal` field accepts both strings and numbers; the number path converts via `str(float)` then `Decimal(str)`. For values where `str(float)` round-trips cleanly (`0.1`), the result looks fine; for values where it does not (`0.1 + 0.2`), the imprecision leaks. The boundary is unsafe by default.
**Fix:** Add the `reject_float` `field_validator(mode='before')` shown in the code block above. The validator makes the boundary loudly wrong (`422`) instead of silently wrong (`200 OK` with a corrupted value).

### Mistake 2: Serialising `Decimal` with `json.dumps` directly

```python
import json
json.dumps({"budget": Decimal("1.00")})   # TypeError: Object of type Decimal is not JSON serializable
```

**Symptom:** `TypeError` at response time, in code that worked with a `dict[str, float]` but breaks with a `dict[str, Decimal]`.
**Why:** The `json` module's default encoder does not know about `Decimal`. It calls `default(obj)`, which raises `TypeError` for any type it does not recognise.
**Fix:** Either use `model_dump_json()` (which calls Pydantic's serialiser, which knows about `Decimal`), or pre-convert with `jsonable_encoder(...)` before `json.dumps(...)`, or pass a custom `default` function: `json.dumps(obj, default=lambda o: str(o) if isinstance(o, Decimal) else ...)`. The first form is the FastAPI-native one; the second is what FastAPI uses internally; the third is for hand-rolled JSON serialisation outside FastAPI.

### Mistake 3: Using `response_model=Decimal` directly (no model wrapper)

```python
@app.get("/budget", response_model=Decimal)
def get_budget() -> Decimal:
    return Decimal("1000.00")
```

**Symptom:** FastAPI's OpenAPI generator produces a schema with `type: string` for the response, but the route returns the bare string `"1000.00"` rather than a JSON-quoted string. Or, more commonly, the route returns a `Decimal` directly and FastAPI's `jsonable_encoder` converts it to `str` correctly, but the OpenAPI schema looks wrong.
**Why:** FastAPI's `response_model` expects a Pydantic model (or a primitive). For a primitive `response_model=Decimal`, the OpenAPI schema is `{"type": "string", ...}` (correct), but the route's return value is a `Decimal` instance that FastAPI serialises via `jsonable_encoder` to `str` then to a JSON string. The behaviour works; the readability is poor — a bare `Decimal` response_model is harder for clients to consume than a model with a named field.
**Fix:** Wrap the response in a model: `class BudgetOut(BaseModel): amount: Decimal`, and `response_model=BudgetOut`. The named field makes the API self-documenting and lets you add more fields later (`currency: str`, `as_of: datetime`) without a breaking change.

### Mistake 4: Treating `Field(max_digits=, decimal_places=)` as a substitute for the float-rejecting validator

```python
class ProjectCreate(BaseModel):
    budget: Annotated[Decimal, Field(max_digits=12, decimal_places=2)]   # no field_validator
```

**Symptom:** You think the digit constraint catches floats. It does catch *some* — `0.1 + 0.2 = 0.30000000000000004` has 17 significant digits, exceeding `max_digits=12`, and Pydantic rejects it. But `0.1` itself has only 1 significant digit, well under `max_digits=12`, and is accepted — silently.
**Why:** The `max_digits` and `decimal_places` constraints validate the *stored `Decimal`*'s digit count, not the input's Python type. A float that happens to coerce to a `Decimal` with the right digit count passes; a float that does not, fails. The digit constraint is a defence-in-depth, not a substitute for the type check.
**Fix:** Use both. The `field_validator(mode='before')` rejects floats by type; the `max_digits`/`decimal_places` constraint catches malformed strings (`"1.234"`) and oversized values (`"999999999999.99"`). Together they form the boundary contract; either alone is insufficient.

## Engineering Trade-Offs

**Decision:** `boardly` uses `Decimal` for every money field in Pydantic models, with a `field_validator(mode='before')` that rejects floats, and `Annotated[Decimal, Field(max_digits=..., decimal_places=...)]` for digit-bound constraints. Serialisation is via Pydantic's `model_dump_json()` (string form). The `int`-cents alternative is documented but not used.
**Both sides:** The alternative is `int`-cents (`budget_cents: int`), which is faster, JSON-native, and has no precision trap. The trade-off is scale tracking — every display conversion has to know the scale, and every fractional-cent use case has to be reshaped into a smaller unit. `Decimal` carries its own scale (`as_tuple().exponent`), so the scale is always present where the value is. The `Decimal` overhead (2–5× slower than `int` in CPython 3.11+) is real but rarely the bottleneck on a typical FastAPI route (the database call usually dominates).
**Commitment:** `boardly` uses `Decimal`. The validator pattern (`reject_float` at `mode='before'`, `Field(max_digits=, decimal_places=)` for digit bounds) is enforced by lint — every `Decimal` field in a `BaseModel` must have both. The `int`-cents alternative is documented in [[25-Reference-Library/Engineering-Decision-Log]] for systems where the `Decimal` overhead is genuinely the bottleneck; we are not there.

## Exercises

1. **Exercise 1 — Verify the validator fires.** Send a `POST /projects` with `{"name":"x","budget":0.1}` (a JSON number). Confirm the response is `422 Unprocessable Entity` and the error message mentions "must be a JSON string". `Verify: uv run python -c "from fastapi.testclient import TestClient; from boardly.api.projects_routes import app; c=TestClient(app); r=c.post('/projects', json={'name':'x','budget':0.1}); print(r.status_code, r.status_code==422)"`
2. **Exercise 2 — Verify the digit constraint catches over-precision.** Send `{"name":"y","budget":"1.234"}`. Confirm the response is `422` and the error mentions "no more than 2 decimal places". `Verify: uv run python -c "from fastapi.testclient import TestClient; from boardly.api.projects_routes import app; c=TestClient(app); r=c.post('/projects', json={'name':'y','budget':'1.234'}); print(r.status_code==422)"`
3. **Exercise 3 — Read the OpenAPI schema.** Print the OpenAPI schema for `ProjectCreate` (request) and `ProjectOut` (response). Confirm the request has `budget` as `anyOf: [{type: number}, {type: string}]` (Pydantic's default for `Decimal` — note that the `reject_float` validator does not narrow this schema, because Pydantic's schema generator does not introspect validator contents) and the response has `budget` as `{type: string}`. Document in a comment that the schema under-promises: clients will think they can post a number, and the route will return `422` when they do. `Verify: uv run python -c "from boardly.api.projects_routes import app; import json; s=app.openapi(); print('ProjectCreate budget:', json.dumps(s['components']['schemas']['ProjectCreate-Input']['properties']['budget']))"`
4. **Exercise 4 — Implement the int-cents alternative.** Add a `POST /projects/cents` route that accepts `ProjectCents` and returns it. Confirm a request `{"name":"z","budget_cents":1000}` round-trips as `{"name":"z","budget_cents":1000}` (a JSON number, not a string). Then write a `display_amount(cents: int) -> str` function that returns `f"${cents // 100}.{cents % 100:02d}"` and verify `display_amount(1000) == "$10.00"`. `Verify: uv run python -c "from boardly.api.projects_routes import display_amount; assert display_amount(1000)=='\$10.00'; print('ok')"`
5. **Exercise 5 — Cross-link to the dataclass pattern.** Convert `ProjectOut` from a `BaseModel` to a `@dataclass` (see [[06-dataclasses/01-dataclass-Basics]]). Confirm that `@dataclass` does *not* validate the `Decimal` field (no `max_digits` enforcement), and that you have to call `Decimal(...)` yourself at construction time. Document in a comment which layer (`@dataclass` vs `BaseModel`) you would use for an internal service model vs an API model. `Verify: uv run python -c "from dataclasses import dataclass; from decimal import Decimal; @dataclass\nclass P:\n    name: str\n    budget: Decimal\np=P('a', Decimal('1.00')); print('ok', p)"`

## Verification

```bash
$ uv run python boardly/api/projects_routes.py
model_dump: {'name': 'alpha', 'budget': Decimal('1000.00')}
model_dump_json: {"name":"alpha","budget":"1000.00"}
jsonable_encoder: {'name': 'alpha', 'budget': '1000.00'}
str(Decimal): 1.00
int-cents json: {"name":"alpha","budget_cents":1000}

$ uv run python -c "
from fastapi.testclient import TestClient
from boardly.api.projects_routes import app
c = TestClient(app)
print('str ok  :', c.post('/projects', json={'name':'a','budget':'1.00'}).json())
print('float  :', c.post('/projects', json={'name':'b','budget':0.1}).status_code)
print('0.1+0.2:', c.post('/projects', json={'name':'c','budget':0.1+0.2}).status_code)
print('too many dp:', c.post('/projects', json={'name':'d','budget':'1.234'}).status_code)
print('remaining:', c.get('/projects/alpha/remaining?spent=12.34').json())
"
str ok  : {'name': 'a', 'budget': '1.00'}
float  : 422
0.1+0.2: 422
too many dp: 422
remaining: {'name': 'alpha', 'budget': '987.66'}
```

## Previously Learned Here

- [[17-decimal/01-Decimal-Basics]] — the `Decimal` type and the string-constructor rule this lesson's `reject_float` validator enforces at the boundary.
- [[17-decimal/02-Context-and-precision]] — `localcontext()` and `quantize()`, used in the `remaining` route for the half-up tax rounding.
- [[06-dataclasses/01-dataclass-Basics]] — the `@dataclass` alternative to Pydantic's `BaseModel`. The two share the field-with-default pattern; the difference is validation, which `BaseModel` does and `@dataclass` does not. Lesson 03 of the dataclasses section is the bridge.
- [[01-typing/02-Annotated-and-Metadata]] — the `Annotated[Decimal, Field(...)]` form this lesson uses to attach digit constraints to the type.

## What's Next

You have finished the `decimal` section. The three lessons gave you the type (lesson 01), the context machinery (lesson 02), and the API integration (lesson 03). The natural next stops in the standard-library arc are [[18-operator/00-operator-MOC]] (the `operator` module — `operator.add` and friends, useful when you write functional-style money arithmetic) and [[19-weakref/00-weakref-MOC]] (the `weakref` module — useful for caching `Decimal` computations without preventing garbage collection). For the FastAPI arc, the next relevant section is the [[25-Reference-Library/Engineering-Decision-Log]] entry on "why `Decimal` not `int`-cents" — the decision this lesson's exercises documented.

- **[[18-operator/00-operator-MOC]]** — `operator.add`, `operator.mul`, and the functional patterns for money pipelines.
- **[[25-Reference-Library/Engineering-Decision-Log]]** — the recorded decision to use `Decimal` over `int`-cents in `boardly`.

## Sources

- **Python `decimal` module documentation** — https://docs.python.org/3/library/decimal.html — accessed 2026-10-23 — the source-of-truth reference for `Decimal`, `Context`, `localcontext`, and the rounding modes.
- **Pydantic v2 — `Decimal` types** — https://docs.pydantic.dev/2.12/concepts/types/#decimal — accessed 2026-10-23 — Pydantic v2's `Decimal` field documentation, including the `max_digits`/`decimal_places` constraints and the default string serialisation.
- **FastAPI — `jsonable_encoder`** — https://fastapi.tiangolo.com/tutorial/custom-response/ — accessed 2026-10-23 — the FastAPI encoder that converts `Decimal` to `str` before `json.dumps`; the bridge between Pydantic's `model_dump` and the JSON encoder.
- **JSON Schema — `number` vs `integer` vs `string`** — https://json-schema.org/understanding-json-schema/reference/numeric — accessed 2026-10-23 — why large-precision numbers should be sent as JSON strings (the spec recommends it for anything beyond `2^53`).

## What We Learned

- You can now declare a `Decimal` field in a Pydantic model and predict the OpenAPI request schema (`anyOf: [number, string]`) and response schema (`string`).
- You can implement the "never accept float" rule with `@field_validator(mode='before')` that rejects `isinstance(value, float)` and converts the rejection to a `422`.
- You can apply `Annotated[Decimal, Field(max_digits=, decimal_places=)]` to bound the digits and decimal places, and you can explain why this constraint is *defence-in-depth*, not a substitute for the float-rejecting validator.
- You can explain why Pydantic serialises `Decimal` as a JSON string (binary-float parsers on clients, trailing-zero preservation, JSON Schema recommendation) and how `jsonable_encoder` bridges Pydantic's `model_dump` to the standard `json.dumps`.
- You can defend the choice between `Decimal` and `int`-cents, naming the speed/JSON-nativeness trade-off for `int`-cents and the scale-tracking/fractional-cents trade-off for `Decimal`.
