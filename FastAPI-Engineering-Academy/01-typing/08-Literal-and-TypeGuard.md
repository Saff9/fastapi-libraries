---
title: "Lesson 08: Literal and TypeGuard"
aliases:
 - Literal and TypeGuard
 - 08-Literal-and-TypeGuard
 - Literal
 - TypeGuard
 - LiteralString
 - TypeIs
tags:
 - typing
 - literal
 - pep-586
 - typeguard
 - pep-642
 - type-narrowing
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/07-TypedDict]]"
related_lessons:
 - "[[01-typing/07-TypedDict]]"
 - "[[09-enum/01-Enum-Basics]]"
 - "[[01-typing/09-Overload]]"
---

# Lesson 08: Literal and TypeGuard

*`Literal["active", "archived"]` (PEP 586) for fixed-set string values, `LiteralString` (3.11+) for SQL-injection-safe strings, and `TypeGuard[T]` (3.10+, PEP 642) for type-narrowing after a runtime check.*

**You're at the very beginning of Section 01's type-narrowing lesson.**

You have `status: str` everywhere. Half your functions check `if status == "active": ...` and call `process_active(status)`. mypy does not narrow `str` to `"active"` inside the `if` — it sees `str` throughout. You get false positives ("`process_active` expects `Literal["active"]`, got `str`") even though the `if` makes it safe. Two `typing` constructs solve this. `Literal["active", "archived"]` makes the *type* the fixed set, so mypy narrows on `==` comparisons. `TypeGuard[T]` makes a *function* that narrows a value's type when it returns `True`. Take your time. Type every example. **This is how you learn.**

#typing #literal #typeguard #type-narrowing

## Learning Objectives

By the end of this lesson you will be able to:

1. **Define** `Literal["active", "archived"]` and use it for fields whose value is from a fixed set; explain when `Literal` beats `Enum`.
2. **Inspect** a `Literal` form with `get_args` and `get_origin` at runtime.
3. **Use** `LiteralString` (3.11+) to constrain a function's argument to literal strings (e.g., a SQL builder that refuses interpolated input).
4. **Write** a `TypeGuard[T]`-annotated function that narrows a value's type after a runtime check; explain the *asymmetric* narrowing behaviour.
5. **Version-gate** `TypeIs[T]` (3.13+, PEP 742) — the stricter, symmetric version of `TypeGuard` — and explain when it would matter.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — `int | str`, `Optional[X]`, `get_type_hints`.
- **[[01-typing/07-TypedDict]]** — `TypedDict` for JSON shapes, since `Literal` often appears as a TypedDict field.
- **About 35–50 minutes of focused time.**

**The most common gap: assuming `TypeGuard` narrows symmetrically.**

Students arrive having written `def is_int(x: object) -> TypeGuard[int]: return isinstance(x, int)` and assume that when the function returns `False`, mypy narrows to "not int". It does *not*. `TypeGuard` is *asymmetric*: `True` narrows to the guarded type; `False` leaves the type alone (does *not* narrow to the negation). The new `TypeIs[T]` (3.13+) fixes this — it is symmetric. If you only target 3.12, you must accept `TypeGuard`'s asymmetry or write the negation manually. We cover both.

## The Problem

Here is the bug this lesson prevents. boardly's `Ticket` has a `status` field that is one of `"active"`, `"archived"`, `"deleted"`. The first version of the codebase wrote:

```python
def list_tickets(status: str = "active") -> list[int]:
    if status == "active":
        return [1, 2, 3]
    elif status == "archived":
        return [4, 5]
    elif status == "deleted":
        return [6]
    else:
        raise ValueError(f"unknown status: {status}")

# Caller:
list_tickets("active")     # OK
list_tickets("invalid")    # runs, raises at runtime — no static check!
```

`status: str` accepts any string. A typo (`list_tickets("actve")`) is a runtime error, not a static one. The OpenAPI doc shows `status` as a generic string, not the three allowed values — no enum constraint in the API client.

`Literal` fixes this:

```python
TicketStatus = Literal["active", "archived", "deleted"]
def list_tickets(status: TicketStatus = "active") -> list[int]: ...
```

Now `list_tickets("actve")` is a *static* type error — mypy catches it before runtime. FastAPI's OpenAPI generation produces an `enum: ["active", "archived", "deleted"]` constraint in the schema — clients see the allowed values. The same pattern catches SQL injection when combined with `LiteralString`.

## The Code

```python
# boardly/literal_typeguard.py
"""boardly — Literal (PEP 586), LiteralString (3.11+), TypeGuard (3.10+), TypeIs (3.13+)."""
from typing import Literal, TypeGuard, get_args, get_origin
import sys

# --- Literal: a value of a fixed, enumerated set. ---
TicketStatus = Literal["active", "archived", "deleted"]

# A boardly route using Literal for the status query param.
def list_tickets(status: TicketStatus = "active") -> list[int]:
    # The checker narrows status to one of the three strings.
    return [{"active": [1, 2, 3], "archived": [4, 5], "deleted": [6]}[status]][0]

# --- LiteralString (3.11+): any string, but at compile time it must be literal-typed. ---
try:
    from typing import LiteralString
    def build_query(table: LiteralString) -> str:
        # 'table' must be a literal string at the call site — guards against injection.
        return f"SELECT * FROM {table}"
    HAS_LITERAL_STRING = True
except ImportError:
    HAS_LITERAL_STRING = False

# --- TypeGuard: a function that returns bool but also narrows the input type. ---
def is_active_status(s: object) -> TypeGuard[TicketStatus]:
    """Returns True iff s is one of the literal TicketStatus strings."""
    return s in ("active", "archived", "deleted")

def process_status(maybe: object) -> int:
    if is_active_status(maybe):
        # mypy now narrows 'maybe' from object -> TicketStatus.
        return len(maybe)
    return 0

# --- TypeGuard with a list narrowing ---
def is_int_list(xs: list[object]) -> TypeGuard[list[int]]:
    return all(isinstance(x, int) for x in xs)

def sum_ints(xs: list[object]) -> int:
    if is_int_list(xs):
        # mypy narrows xs from list[object] -> list[int]
        return sum(xs)
    return 0

if __name__ == "__main__":
    print("active ids:", list_tickets())
    print("archived ids:", list_tickets("archived"))
    print("Literal args:", get_args(TicketStatus))
    print("Literal origin:", get_origin(TicketStatus))

    print("is_active_status('active'):", is_active_status("active"))
    print("is_active_status('unknown'):", is_active_status("unknown"))
    print("process_status('active'):", process_status("active"))
    print("process_status('xyz'):", process_status("xyz"))

    mixed: list[object] = [1, 2, 3]
    print("is_int_list(mixed):", is_int_list(mixed))
    print("sum_ints(mixed):", sum_ints(mixed))
    bad: list[object] = [1, "x", 3]
    print("sum_ints(bad):", sum_ints(bad))

    print("HAS_LITERAL_STRING:", HAS_LITERAL_STRING)
    print("Python:", sys.version_info)
```

## Line-by-Line Deep Dive

### Lines 1–5: Imports

```python
# boardly/literal_typeguard.py
"""boardly — Literal (PEP 586), LiteralString (3.11+), TypeGuard (3.10+), TypeIs (3.13+)."""
from typing import Literal, TypeGuard, get_args, get_origin
import sys
```

`Literal` was added in Python 3.8 (PEP 586). `TypeGuard` was added in Python 3.10 (PEP 642). `LiteralString` was added in Python 3.11 (PEP 675). `TypeIs` was added in Python 3.13 (PEP 742) — **not** in 3.12, must be version-gated. In 3.12 — the vault runtime — we have `Literal`, `TypeGuard`, and `LiteralString` natively; we do not have `TypeIs` and `ReadOnly`.

We will try-import `LiteralString` from `typing` — it works in 3.12 because 3.11+ has it. The `try/except ImportError` is belt-and-suspenders for users running on 3.10; on 3.12 the import always succeeds.

**Why was `Literal` added in 3.8?**

Because before `Literal`, the only way to type "this string must be one of three values" was `Union[Literal["active"], Literal["archived"]]` (no) or just `str` (no type-checking). PEP 586 introduced `Literal["active", "archived"]` as a first-class form, and type-checkers immediately used it to narrow `==` comparisons. mypy's `if status == "active":` now narrows `status` to `Literal["active"]` inside the `if` — a feature called *narrowing by equality*.

### Lines 7–13: The `Literal` type alias and the route

```python
# --- Literal: a value of a fixed, enumerated set. ---
TicketStatus = Literal["active", "archived", "deleted"]

# A boardly route using Literal for the status query param.
def list_tickets(status: TicketStatus = "active") -> list[int]:
    # The checker narrows status to one of the three strings.
    return [{"active": [1, 2, 3], "archived": [4, 5], "deleted": [6]}[status]][0]
```

`TicketStatus = Literal["active", "archived", "deleted"]` is a *type alias* for a `Literal` form. A value of type `TicketStatus` is exactly one of those three strings — not `str`, not any other string. mypy enforces at the call site: `list_tickets("active")` is fine; `list_tickets("invalid")` is a type error.

Inside the function, `status` is `Literal["active", "archived", "deleted"]`. The dict lookup `[...][status]` works because mypy knows `status` is one of the three keys. The `[0]` index extracts the single list from the one-key result. (This is a contrived demo; in real boardly the body would be a `match` statement or an `if/elif` chain.)

**Why use `Literal` instead of `Enum` here?**

Three reasons. (1) **API ergonomics**: a FastAPI route with `status: Literal["active", "archived"]` accepts the JSON string `"active"` directly — no `Enum` deserialiser needed. An `Enum` requires `class Status(str, Enum): ...` and an extra import. (2) **Schema readability**: the OpenAPI doc shows `enum: ["active", "archived"]` for the field — clean strings, not `"Status.active"`. (3) **No state**: `Literal` is a type, not a runtime object. `Enum` is a class with members. `Literal` is lighter. The trade-off: `Enum` gives you methods, iteration (`for s in Status:`), and member access (`Status.active`) — useful for a status field that needs custom serialisation. For a pure-string fixed-set, `Literal` wins. We cover `Enum` in section `09-enum`.

### Lines 15–23: `LiteralString` (3.11+) for SQL safety

```python
# --- LiteralString (3.11+): any string, but at compile time it must be literal-typed. ---
try:
    from typing import LiteralString
    def build_query(table: LiteralString) -> str:
        # 'table' must be a literal string at the call site — guards against injection.
        return f"SELECT * FROM {table}"
    HAS_LITERAL_STRING = True
except ImportError:
    HAS_LITERAL_STRING = False
```

`LiteralString` (PEP 675, 3.11+) is a special type that means "any string, but at the *call site* it must be a literal — not a runtime value, not an f-string interpolation". `build_query(table: LiteralString)` accepts `build_query("tickets")` (literal) but rejects `build_query(user_input)` (runtime value) — mypy flags the latter. This is the **SQL injection guard at the type level**.

The trick is that `LiteralString` is also assignable to `str` (subtypes), but `str` is *not* assignable to `LiteralString`. So a function that returns `LiteralString` produces a value that can only flow into other `LiteralString` parameters — preventing the string from being constructed from runtime data. Used carefully, `LiteralString` makes a SQL-builder library provably injection-safe at the type level.

**Why use a `try/except ImportError` for `LiteralString`?**

Because `LiteralString` is 3.11+. If you support 3.10, you must import from `typing_extensions` instead. The `try: from typing import LiteralString / except ImportError: from typing_extensions import LiteralString` pattern is the standard 3.10-compatibility shim. In boardly (which targets 3.12), we use the simple `from typing import LiteralString` form — the `try/except` is here only to demonstrate the version-gate pattern.

### Lines 25–33: `TypeGuard[T]` for narrowing

```python
# --- TypeGuard: a function that returns bool but also narrows the input type. ---
def is_active_status(s: object) -> TypeGuard[TicketStatus]:
    """Returns True iff s is one of the literal TicketStatus strings."""
    return s in ("active", "archived", "deleted")

def process_status(maybe: object) -> int:
    if is_active_status(maybe):
        # mypy now narrows 'maybe' from object -> TicketStatus.
        return len(maybe)
    return 0
```

`TypeGuard[T]` (PEP 642, 3.10+) is the *return type* of a function that returns `bool`. When the function returns `True`, mypy narrows the input parameter's type to `T`. Here, `is_active_status(s: object) -> TypeGuard[TicketStatus]` — when it returns `True`, mypy narrows `s` from `object` to `TicketStatus` (the `Literal["active", "archived", "deleted"]` form). Inside the `if`, `len(maybe)` is well-typed because `TicketStatus` is a `str` (Literals are strings), so `len()` works.

The function body `return s in ("active", "archived", "deleted")` is a normal `bool`-returning expression. The `TypeGuard[TicketStatus]` annotation is purely a *signal to the type-checker* — it does not change runtime behaviour. mypy trusts the function: if it returns `True`, the narrowing applies; if it returns `False`, no narrowing.

**Why does `TypeGuard` need to trust the function's body?**

Because mypy cannot *prove* that `s in (...)` means `s` has type `TicketStatus`. The check is `s in ("active", "archived", "deleted")` — that returns `bool`, but the *static* inference would be "is `s` an element of the tuple", which does not give a type. `TypeGuard` is the explicit assertion that *when this function returns `True`, the input has type `T`*. It is the type-checker's contract with you: "I will trust your assertion; you must make it true." If your `TypeGuard` function lies (returns `True` when the narrowing is wrong), mypy's downstream checks are unsound — but that is your bug, not mypy's.

### Lines 35–43: `TypeGuard` for list narrowing

```python
# --- TypeGuard with a list narrowing ---
def is_int_list(xs: list[object]) -> TypeGuard[list[int]]:
    return all(isinstance(x, int) for x in xs)

def sum_ints(xs: list[object]) -> int:
    if is_int_list(xs):
        # mypy narrows xs from list[object] -> list[int]
        return sum(xs)
    return 0
```

`TypeGuard[list[int]]` narrows a `list[object]` to `list[int]` when the function returns `True`. This is the *generic* narrowing form — `T` can itself be a generic alias. The narrowing is structural: mypy treats `xs` as `list[int]` inside the `if`, so `sum(xs)` is well-typed.

The function body `return all(isinstance(x, int) for x in xs)` walks every element and checks `isinstance`. This is *O(n)* runtime cost — be aware that `TypeGuard` functions are called every time the narrowing is needed; for hot paths, this matters. For one-off narrowing at the boundary (e.g., validating incoming JSON before processing), the cost is fine.

**Why not use `isinstance(xs, list[int])` directly?**

Because `isinstance(xs, list[int])` is a `TypeError` at runtime in 3.8/3.9 — `isinstance` only accepts runtime types, and `list[int]` is a generic alias, not a runtime type. Even in 3.12, `isinstance(xs, list[int])` raises `TypeError: isinstance() argument 2 cannot be a parameterized generic`. The only way to narrow a generic alias is a user-defined `TypeGuard` function. This is a *language limitation* — there is no syntax for `isinstance(x, list[int])`. `TypeGuard` is the workaround.

### Lines 45–67: The `__main__` block

```python
if __name__ == "__main__":
    print("active ids:", list_tickets())
    print("archived ids:", list_tickets("archived"))
    print("Literal args:", get_args(TicketStatus))
    print("Literal origin:", get_origin(TicketStatus))

    print("is_active_status('active'):", is_active_status("active"))
    print("is_active_status('unknown'):", is_active_status("unknown"))
    print("process_status('active'):", process_status("active"))
    print("process_status('xyz'):", process_status("xyz"))

    mixed: list[object] = [1, 2, 3]
    print("is_int_list(mixed):", is_int_list(mixed))
    print("sum_ints(mixed):", sum_ints(mixed))
    bad: list[object] = [1, "x", 3]
    print("sum_ints(bad):", sum_ints(bad))

    print("HAS_LITERAL_STRING:", HAS_LITERAL_STRING)
    print("Python:", sys.version_info)
```

We exercise `Literal` (route dispatch), `LiteralString` (presence detection), and `TypeGuard` (status narrowing, list narrowing). The introspection prints — `get_args(TicketStatus) == ('active', 'archived', 'deleted')` and `get_origin(TicketStatus) is typing.Literal` — let frameworks recover the allowed values. FastAPI's OpenAPI generator does exactly this walk to produce `enum: [...]` in the JSON Schema.

## Execution Trace

```bash
$ python boardly/literal_typeguard.py
active ids: [1, 2, 3]
archived ids: [4, 5]
Literal args: ('active', 'archived', 'deleted')
Literal origin: typing.Literal
is_active_status('active'): True
is_active_status('unknown'): False
process_status('active'): 6
process_status('xyz'): 0
is_int_list(mixed): True
sum_ints(mixed): 6
sum_ints(bad): 0
HAS_LITERAL_STRING: True
Python: sys.version_info(major=3, minor=12, micro=15, releaselevel='final', serial=0)
```

Three things to verify. First, `Literal args: ('active', 'archived', 'deleted')` — the tuple of allowed values, recovered at runtime. Second, `process_status('active'): 6` — the narrowing let `len(maybe)` run on a `TicketStatus` value (length of `"active"` is 6). Third, `HAS_LITERAL_STRING: True` — confirms 3.12 has `LiteralString`.

## Common Mistakes

### Mistake 1: Assuming `TypeGuard` narrows symmetrically

```python
def is_int(x: object) -> TypeGuard[int]:
    return isinstance(x, int)

def f(x: object) -> str:
    if is_int(x):
        return str(x + 1)  # ← mypy: x is int
    else:
        return str(x + 1)  # ← mypy: x is STILL object — not "not int"
```

**Symptom:** mypy flags `x + 1` in the `else` branch as a type error (`object` does not support `+`), even though you might expect the `else` to mean "x is not int".
**Why:** `TypeGuard` is *asymmetric*. `True` narrows to `T`; `False` leaves the type as it was. It does *not* narrow to the negation.
**Fix:** Either manually narrow in the `else` (e.g., `assert not isinstance(x, int)` if you want to assert the negation — though that's clunky), or upgrade to `TypeIs[T]` (3.13+) which is symmetric. In 3.12, you must accept the asymmetry and write the `else` accordingly — e.g., `else: return str(x)` without operations that assume int.

### Mistake 2: Using `Literal` where `Enum` is right

```python
Color = Literal["red", "green", "blue", "yellow", "purple", "orange", "black", "white"]
# ... and you also need to iterate the set, access members by name, serialise to int codes...
```

**Symptom:** No runtime error, but the type becomes unwieldy; you find yourself re-listing the literal values in multiple places.
**Why:** `Literal` is for fixed sets that need *no behaviour* — just the values. When you need iteration (`for c in AllColors:`), named member access (`Color.RED`), custom serialisation, or behaviour-on-the-values, `Enum` is the right tool.
**Fix:** Switch to `class Color(str, Enum): RED = "red"; ...`. The trade-off is two extra lines and a class instead of a type alias. See section `09-enum` for the full `Enum` treatment.

### Mistake 3: Lying in a `TypeGuard` function

```python
def is_int(x: object) -> TypeGuard[int]:
    return True  # ← lying — returns True for everything

def f(x: object) -> int:
    if is_int(x):
        return x + 1  # ← runtime TypeError if x is "hello"
```

**Symptom:** Code type-checks cleanly with mypy but fails at runtime with `TypeError: unsupported operand` on a non-int `x`.
**Why:** `TypeGuard` is a *contract* you sign with the type-checker. mypy trusts the body; it does not verify the body's correctness. If your `TypeGuard` lies (returns `True` when the narrowing is wrong), mypy's downstream checks become unsound — and the failure shows up at runtime, not at type-check time.
**Fix:** Make sure your `TypeGuard` body genuinely checks what the narrowing claims. For `TypeGuard[int]`, the body should be `return isinstance(x, int)`. For `TypeGuard[list[int]]`, the body should walk every element. If your check is approximate (e.g., "x has an `id` attribute" but you narrow to `Ticket`), be conservative — narrow to a `Protocol` (lesson 05) rather than a concrete class.

## Engineering Trade-Offs

**Decision:** Use `Literal` for fixed-set string fields, `LiteralString` for SQL-builder library boundaries, `TypeGuard` for narrowing in the small (no `TypeIs` since we target 3.12).
**Both sides:** `Literal` is lighter than `Enum` (no class, no methods) but offers no iteration or named members. `TypeGuard` is the only way to narrow generic aliases but is asymmetric in 3.12; `TypeIs` (3.13+) is symmetric but not available cross-version.
**Commitment:** boardly uses `Literal` for ticket status, user role, and similar small fixed sets. We use `LiteralString` for any function that builds SQL fragments from string arguments — the type-level injection guard is worth the import. We use `TypeGuard` for the JSON-input validation layer (e.g., `is_create_ticket_request(x: object) -> TypeGuard[CreateTicket]`). We do not use `TypeIs` because we target 3.12; if we move to 3.13+ as a minimum, we will switch to `TypeIs` for symmetric narrowing.

**Python 3.13+: `TypeIs[T]` (PEP 742)**
`TypeIs[T]` is the symmetric, stricter version of `TypeGuard`. Where `TypeGuard` narrows on `True` and leaves the type alone on `False`, `TypeIs` narrows on `True` *and* narrows to the negation on `False`. It is **not available in Python 3.12** (it is 3.13+). If you need symmetric narrowing and cannot upgrade, you must either (a) write the negation manually in the `else` branch, or (b) use `typing_extensions.TypeIs` (the backport). For 3.12-native code, `TypeGuard` is what you have.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/literal_typeguard.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/literal_typeguard.py`
2. **Exercise 2 — Add `UserRole` Literal.** Define `UserRole = Literal["admin", "member", "viewer"]` and a function `def can_delete(role: UserRole) -> bool: return role == "admin"`. Verify mypy accepts `can_delete("admin")` and rejects `can_delete("invalid")`. `Verify: python -c "from boardly.literal_typeguard import can_delete; print(can_delete('admin'))"`
3. **Exercise 3 — Use `LiteralString` for a SQL builder.** Add `def select(table: LiteralString) -> str: return f"SELECT * FROM {table}"`. Call `select("tickets")` (OK) and confirm a runtime-variable form (`table = input(); select(table)`) is a mypy error. `Verify: python -c "from boardly.literal_typeguard import select; print(select('tickets'))"`
4. **Exercise 4 — Add a `TypeGuard` for `TicketJSON`.** Define `def is_ticket_dict(d: object) -> TypeGuard[dict[str, object]]: return isinstance(d, dict) and 'id' in d and 'title' in d`. Use it to narrow `object` to `dict[str, object]` before processing. `Verify: python -c "from boardly.literal_typeguard import is_ticket_dict; print(is_ticket_dict({'id': 1, 'title': 'x'}))"`
5. **Exercise 5 — Compare `TypeGuard` to `TypeIs`.** If you have access to 3.13+ or `typing_extensions`, write the same narrowing with `TypeIs[T]` and observe that the `else` branch narrows to the negation. Document the difference. `Verify: python -c "import typing_extensions as te; print(hasattr(te, 'TypeIs'))"`

## Verification

```bash
$ python boardly/literal_typeguard.py
active ids: [1, 2, 3]
archived ids: [4, 5]
Literal args: ('active', 'archived', 'deleted')
Literal origin: typing.Literal
is_active_status('active'): True
is_active_status('unknown'): False
process_status('active'): 6
process_status('xyz'): 0
is_int_list(mixed): True
sum_ints(mixed): 6
sum_ints(bad): 0
HAS_LITERAL_STRING: True
Python: sys.version_info(major=3, minor=12, micro=15, releaselevel='final', serial=0)
```

If `Literal args: ('active', 'archived', 'deleted')` and `Literal origin: typing.Literal` both appear, you have the `Literal` form working and introspectable. If `process_status('active'): 6` is correct, the `TypeGuard` narrowing let `len()` run on a string of length 6.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `X | Y` for unions. `Literal[...]` is a closed-form union of literal values — narrower than `str` or `int`.
- [[01-typing/07-TypedDict]] — `TypedDict` for JSON shapes. `Literal` fields inside a `TypedDict` give you "this key is one of three strings" — perfect for status fields in API bodies.

## What's Next

[[01-typing/09-Overload]] — `@overload` for functions with multiple signatures. `Literal` is one way to make a function's behaviour depend on a fixed set; `@overload` is the more general mechanism for "the function takes `int` and returns `int`, or takes `str` and returns `str`". Three things to look for in lesson 09:

- `@overload` stubs before the real implementation — why mypy needs them.
- The runtime stub-vs-implementation distinction (the stubs are ignored at runtime; only the final definition runs).
- When `@overload` with `Literal` is the right combination (the "string-in, literal-out" pattern).

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.Literal — CPython reference** — https://docs.python.org/3/library/typing.html#typing.Literal — accessed 2026-10-23 — the canonical API for `Literal["active", "archived"]` and `get_args`/`get_origin` on Literal forms.
- **typing.TypeGuard — CPython reference** — https://docs.python.org/3/library/typing.html#typing.TypeGuard — accessed 2026-10-23 — the canonical API for `TypeGuard[T]` user-defined narrowing functions, including the asymmetric behaviour warning.
- **typing.LiteralString — CPython reference** — https://docs.python.org/3/library/typing.html#typing.LiteralString — accessed 2026-10-23 — the canonical API for `LiteralString` (3.11+), the SQL-injection-safe string type.
- **PEP 586 — Literal Types** — https://peps.python.org/pep-0586/ — accessed 2026-10-23 — the PEP that introduced `Literal` in 3.8.
- **PEP 642 — User-Defined Type Guards (`TypeGuard`)** — https://peps.python.org/pep-0642/ — accessed 2026-10-23 — the PEP that introduced `TypeGuard` in 3.10, including the asymmetric narrowing specification.
- **PEP 675 — LiteralString** — https://peps.python.org/pep-0675/ — accessed 2026-10-23 — the PEP that introduced `LiteralString` in 3.11.
- **PEP 742 — `TypeIs`** — https://peps.python.org/pep-0742/ — accessed 2026-10-23 — the PEP that introduced `TypeIs` in 3.13 (version-gated; not in 3.12).

## What We Learned

- `Literal["active", "archived"]` is a closed-form union of literal values — narrower than `str`, with `get_args` returning the allowed values.
- `Literal` is the lighter alternative to `Enum` for fixed-set string fields with no behaviour; `Enum` wins when you need iteration or named members.
- `LiteralString` (3.11+) restricts a function's argument to literal strings at the call site — the SQL-injection guard at the type level.
- `TypeGuard[T]` (3.10+, PEP 642) is the return type of a function that returns `bool` — when it returns `True`, mypy narrows the input type to `T`.
- `TypeGuard` is *asymmetric*: `True` narrows to `T`, `False` leaves the type alone. There is no narrowing to the negation.
- `TypeIs[T]` (3.13+, PEP 742, version-gated) is the symmetric version of `TypeGuard`; use `typing_extensions.TypeIs` for cross-version support.
- `isinstance(x, list[int])` raises `TypeError` — `TypeGuard` is the only way to narrow a parameterised generic.
