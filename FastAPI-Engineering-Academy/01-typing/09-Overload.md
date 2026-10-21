---
title: "Lesson 09: Overload"
aliases:
 - Overload
 - 09-Overload
 - "@overload"
tags:
 - typing
 - overload
 - dispatch
 - type-checking
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/08-Literal-and-TypeGuard]]"
related_lessons:
 - "[[01-typing/08-Literal-and-TypeGuard]]"
 - "[[01-typing/06-Callable-and-Callable-Annotations]]"
 - "[[02-functools/04-singledispatch]]"
---

# Lesson 09: Overload

*`@overload` for multiple signatures with one runtime implementation — and the runtime stub the type-checker sees but Python ignores.*

**You're at the very beginning of Section 01's typed-dispatch lesson.**

You have a function `get_ticket` that accepts *either* an `int` (an ID) *or* a `str` (a slug). The runtime implementation handles both via `isinstance`. But the return type is `dict` either way — mypy cannot tell the caller that `get_ticket(1)` returns a dict with key `"id"` while `get_ticket("ada")` returns a dict with key `"slug"`. The caller has to type-cast. `@overload` fixes this: write multiple stub signatures before the implementation, each describing a different input-output relationship. mypy uses the stubs for static checking; at runtime, only the implementation runs. Take your time. Type every example. **This is how you learn.**

#typing #overload #dispatch

## Learning Objectives

By the end of this lesson you will be able to:

1. **Write** `@overload` stubs before a function implementation and explain why the stubs do not run at runtime.
2. **Model** "string-in, literal-out" dispatch with `@overload` + `Literal` — the type-checker picks the right stub based on the input literal.
3. **Use** `@overload` for varying argument counts (one-arg vs two-arg) and keyword-only variations.
4. **Inspect** what `get_type_hints` returns for an overloaded function — and why it returns the *implementation*'s hints, not the stubs'.
5. **Choose** between `@overload`, `singledispatch`, and `match`-on-type for a given dispatch problem.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — `int | str`, `Optional[X]`, `get_type_hints`.
- **[[01-typing/08-Literal-and-TypeGuard]]** — `Literal[...]` for fixed-set values, which combines with `@overload` for "string-in, literal-out" dispatch.
- **About 30–45 minutes of focused time.**

**The most common gap: not realising the stubs are ignored at runtime.**

Students arrive having written three `@overload` stubs and an implementation, and assume that at runtime Python somehow dispatches between them. It does *not*. The `@overload` decorator is a *no-op* at runtime — the stubs are decorative; they exist only for the type-checker. At runtime, the function name `get_ticket` is bound to the *last definition* — the implementation. All the stubs are silently overwritten. This is the single most surprising thing about `@overload` and the most common bug (writing the stubs but forgetting the implementation, or vice versa).

## The Problem

Here is the bug this lesson prevents. boardly's `get_ticket` accepts an `int` ID or a `str` slug:

```python
def get_ticket(id_or_slug: int | str) -> dict:
    if isinstance(id_or_slug, int):
        return {"id": id_or_slug, "title": f"Ticket #{id_or_slug}"}
    return {"slug": id_or_slug, "title": id_or_slug.replace("-", " ").title()}

# Caller:
t1 = get_ticket(1)        # mypy: t1 is dict — caller doesn't know 'id' is in it
t2 = get_ticket("ada-1")  # mypy: t2 is dict — caller doesn't know 'slug' is in it
print(t1["slug"])  # ← KeyError at runtime; mypy did not catch it
```

`get_ticket(1)` returns a dict with `"id"` key; `get_ticket("ada-1")` returns a dict with `"slug"` key. But mypy sees only `dict` for both — the caller has no way to know which keys are present. Worse, the caller can write `t1["slug"]` and mypy allows it (`dict.__getitem__` accepts any key), then it `KeyError`s at runtime.

`@overload` lets you give mypy *two* signatures — one for the int case, one for the str case — so mypy can track the return shape per call:

```python
@overload
def get_ticket(id_or_slug: int) -> dict: ...
@overload
def get_ticket(id_or_slug: str) -> dict: ...
def get_ticket(id_or_slug):
    if isinstance(id_or_slug, int):
        return {"id": id_or_slug, "title": f"Ticket #{id_or_slug}"}
    return {"slug": id_or_slug, "title": id_or_slug.replace("-", " ").title()}
```

Now mypy knows `get_ticket(1)` is the int overload, and you can annotate the return as a `TypedDict` with the int-specific keys. The runtime behaviour is identical — the stubs are decorative — but the type information is per-call.

## The Code

```python
# boardly/overload_basics.py
"""boardly — @overload: multiple signatures, one runtime implementation."""
from typing import overload, Literal, get_type_hints

# --- Overload pattern: two signatures, one implementation. ---

@overload
def get_ticket(id_or_slug: int) -> dict: ...
@overload
def get_ticket(id_or_slug: str) -> dict: ...
def get_ticket(id_or_slug):
    """Real implementation — runtime sees only this version."""
    if isinstance(id_or_slug, int):
        return {"id": id_or_slug, "title": f"Ticket #{id_or_slug}"}
    return {"slug": id_or_slug, "title": id_or_slug.replace("-", " ").title()}

# --- Overload with Literal to model "string-in, literal-out" dispatch ---
@overload
def parse_status(s: Literal["active"]) -> int: ...
@overload
def parse_status(s: Literal["archived"]) -> int: ...
@overload
def parse_status(s: str) -> str: ...
def parse_status(s):
    """If s is a known status, return its numeric code; otherwise echo back."""
    table = {"active": 1, "archived": 2}
    return table.get(s, s)

# --- Overload on the number of arguments ---
@overload
def make_filter(key: str) -> dict: ...
@overload
def make_filter(key: str, value: str) -> dict: ...
@overload
def make_filter(key: str, *, case_insensitive: bool) -> dict: ...
def make_filter(key, value=None, case_insensitive=False):
    out = {"key": key}
    if value is not None:
        out["value"] = value
    if case_insensitive:
        out["ci"] = True
    return out

if __name__ == "__main__":
    # mypy sees:
    #   get_ticket(1) -> dict (int overload)
    #   get_ticket("ada-123") -> dict (str overload)
    print("get_ticket int:", get_ticket(1))
    print("get_ticket str:", get_ticket("ada-123"))

    print("parse_status active:", parse_status("active"))
    print("parse_status unknown:", parse_status("pending"))

    print("make_filter one arg:", make_filter("status"))
    print("make_filter two args:", make_filter("status", "open"))
    print("make_filter ci:", make_filter("status", case_insensitive=True))

    # The runtime ignores the @overload stubs entirely.
    print("get_ticket module has", sum(1 for v in globals().values() if getattr(v, '__name__', '') == 'get_ticket'), "get_ticket in module dict")
    print("get_ticket hints (impl):", get_type_hints(get_ticket))
    # The stubs are stored on __dict__ but the function attribute __wrapped__ shows the impl.
    print("get_ticket __name__:", get_ticket.__name__)
```

## Line-by-Line Deep Dive

### Lines 1–4: Imports

```python
# boardly/overload_basics.py
"""boardly — @overload: multiple signatures, one runtime implementation."""
from typing import overload, Literal, get_type_hints
```

`overload` is a decorator available since Python 3.5 (PEP 484). It is unique among `typing` constructs: at runtime, it is a *no-op*. The decorator just returns the function unchanged — `@overload def f(): ...` produces the same function object as `def f(): ...`. The stubs are decorative — they exist only so static type-checkers can read them.

`Literal` (lesson 08) combines with `@overload` for "string-in, literal-out" dispatch. `get_type_hints` lets us inspect what survives at runtime — spoiler: only the implementation's hints, not the stubs'.

**Why is `@overload` a no-op at runtime?**

Because the type system is static. The Python runtime has no concept of "multiple signatures" — a function name binds to exactly one function object. The `@overload` decorator cannot change that. So it returns the function unchanged, the next `@overload` stub rebinds the name to itself (also unchanged), and finally the implementation `def get_ticket(id_or_slug):` rebinds the name to itself. At runtime, only the implementation exists. The stubs are visible to type-checkers because they parse the source; they are not visible at runtime because Python's name binding overwrites them.

### Lines 6–14: The `@overload` pattern for int-or-str

```python
# --- Overload pattern: two signatures, one implementation. ---

@overload
def get_ticket(id_or_slug: int) -> dict: ...
@overload
def get_ticket(id_or_slug: str) -> dict: ...
def get_ticket(id_or_slug):
    """Real implementation — runtime sees only this version."""
    if isinstance(id_or_slug, int):
        return {"id": id_or_slug, "title": f"Ticket #{id_or_slug}"}
    return {"slug": id_or_slug, "title": id_or_slug.replace("-", " ").title()}
```

Two `@overload` stubs followed by the implementation. Each stub has `...` (ellipsis) as the body — this is the conventional "this is a stub" marker; you could also write `pass` or `raise NotImplementedError("stub")`. The stubs *must* be followed by exactly one *implementation* — a function with the same name, *without* `@overload`, that handles all the cases. If you forget the implementation, the function name is bound to the last stub, which returns nothing (the ellipsis), and every call returns `None` silently. If you forget the stubs, mypy sees only the implementation's `int | str -> dict` and cannot narrow per call.

The implementation `def get_ticket(id_or_slug):` has *no annotations*. This is on purpose — the stubs are the type contract; the implementation is the runtime behaviour. mypy does *not* check the implementation's annotations against the stubs (it checks the implementation's body against the stubs' signatures). The implementation can have any annotation or none; mypy ignores it.

**Why must the implementation come after the stubs, not before?**

Because Python name binding is sequential. The implementation must be the *last* definition of the name, so it is what runtime calls. If you put the implementation first, the stubs overwrite it, and runtime calls the last stub (which has `...` body and returns `None`). Always: stubs first, implementation last.

### Lines 16–26: `@overload` with `Literal` for "string-in, literal-out"

```python
# --- Overload with Literal to model "string-in, literal-out" dispatch ---
@overload
def parse_status(s: Literal["active"]) -> int: ...
@overload
def parse_status(s: Literal["archived"]) -> int: ...
@overload
def parse_status(s: str) -> str: ...
def parse_status(s):
    """If s is a known status, return its numeric code; otherwise echo back."""
    table = {"active": 1, "archived": 2}
    return table.get(s, s)
```

Three stubs: when the caller passes the literal `"active"`, mypy picks the first stub and the return is `int`. When the caller passes the literal `"archived"`, mypy picks the second and the return is `int`. When the caller passes any other `str` (a runtime variable, an unknown literal), mypy picks the third and the return is `str`. The implementation is unchanged — `table.get(s, s)` returns `int` for the two known keys and `str` (the input) otherwise.

This is the "string-in, literal-out" pattern — the type-checker picks the right stub *based on the literal at the call site*. `parse_status("active")` resolves to the int-returning stub; `parse_status(some_var)` where `some_var: str` resolves to the str-returning stub. The runtime does no dispatch — `table.get` is the same code path for both — but mypy tracks the per-call return type precisely.

**Why use `@overload` + `Literal` instead of just `Literal`?**

Because `Literal` alone cannot express "the return type *depends on* which literal was passed". A function `def f(s: Literal["active", "archived"]) -> int | str: ...` says "returns int or str" — mypy cannot tell which. `@overload` + `Literal` says "if you pass `"active"`, you get int; if you pass `"archived"`, you get int; if you pass another str, you get str" — the caller knows. This is *parametric* dispatch — the type-checker picks the stub based on the argument's *static* type.

### Lines 28–39: `@overload` on argument count

```python
# --- Overload on the number of arguments ---
@overload
def make_filter(key: str) -> dict: ...
@overload
def make_filter(key: str, value: str) -> dict: ...
@overload
def make_filter(key: str, *, case_insensitive: bool) -> dict: ...
def make_filter(key, value=None, case_insensitive=False):
    out = {"key": key}
    if value is not None:
        out["value"] = value
    if case_insensitive:
        out["ci"] = True
    return out
```

Three stubs for three calling conventions: one-arg, two-arg, one-arg-plus-keyword. mypy checks each call site against the matching stub. The implementation handles all three via defaults — `value=None`, `case_insensitive=False` — and the body uses `is not None` / truthy checks to build the right dict.

The third stub uses `*` to make `case_insensitive` keyword-only — so the call `make_filter("status", case_insensitive=True)` is valid but `make_filter("status", True)` is *not* (it would need the second stub which expects a `value: str`). mypy rejects the positional call.

**Why overload on argument count instead of just default values?**

Two reasons. (1) **Type-checker precision**: with a single signature `def make_filter(key, value=None, case_insensitive=False) -> dict`, mypy sees the return type as `dict` regardless of which arguments were passed. With three overloads, you could give each one a different return type — e.g., `make_filter(key)` returns `dict[str, str]` and `make_filter(key, value)` returns `dict[str, str | bool]`. (2) **API documentation**: the overloads are visible in the function's `__doc__` (via tools like `inspect.signature`) and in IDE hover-tooltips, showing the three calling conventions explicitly. Defaults hide the conventions.

### Lines 41–56: The `__main__` block

```python
if __name__ == "__main__":
    # mypy sees:
    #   get_ticket(1) -> dict (int overload)
    #   get_ticket("ada-123") -> dict (str overload)
    print("get_ticket int:", get_ticket(1))
    print("get_ticket str:", get_ticket("ada-123"))

    print("parse_status active:", parse_status("active"))
    print("parse_status unknown:", parse_status("pending"))

    print("make_filter one arg:", make_filter("status"))
    print("make_filter two args:", make_filter("status", "open"))
    print("make_filter ci:", make_filter("status", case_insensitive=True))

    # The runtime ignores the @overload stubs entirely.
    print("get_ticket module has", sum(1 for v in globals().values() if getattr(v, '__name__', '') == 'get_ticket'), "get_ticket in module dict")
    print("get_ticket hints (impl):", get_type_hints(get_ticket))
    # The stubs are stored on __dict__ but the function attribute __wrapped__ shows the impl.
    print("get_ticket __name__:", get_ticket.__name__)
```

We exercise all three overload patterns. The most important print is `get_ticket module has 1 get_ticket in module dict` — only *one* `get_ticket` exists at runtime, even though we wrote three (two stubs + one impl). The stubs were silently overwritten. The `get_ticket hints (impl): {}` print shows that `get_type_hints(get_ticket)` returns an empty dict — because the implementation has no annotations, and the stubs are gone from the runtime view. The `__name__` is `"get_ticket"` because the implementation's `__name__` is what survives.

This is the demonstration that `@overload` is purely static: at runtime, you have one function, unannotated, with no trace of the stubs. The stubs live in the source for type-checkers; runtime never sees them.

## Execution Trace

```bash
$ python boardly/overload_basics.py
get_ticket int: {'id': 1, 'title': 'Ticket #1'}
get_ticket str: {'slug': 'ada-123', 'title': 'Ada 123'}
parse_status active: 1
parse_status unknown: pending
make_filter one arg: {'key': 'status'}
make_filter two args: {'key': 'status', 'value': 'open'}
make_filter ci: {'key': 'status', 'ci': True}
get_ticket module has 1 get_ticket in module dict
get_ticket hints (impl): {}
get_ticket __name__: get_ticket
```

Three things to verify. First, `get_ticket int` and `get_ticket str` produce different dict shapes — the runtime dispatch is in the implementation, not in the stubs. Second, `parse_status active` returns `1` (int) while `parse_status unknown` returns `"pending"` (str) — same `table.get` code path, different return types. Third, `get_ticket module has 1` — confirms the stubs were silently overwritten at runtime; only the implementation survives.

## Common Mistakes

### Mistake 1: Forgetting the implementation after the stubs

```python
@overload
def f(x: int) -> int: ...
@overload
def f(x: str) -> str: ...
# ← no implementation!
```

**Symptom:** At runtime, `f(1)` returns `None` (the ellipsis body) and the caller gets `None` instead of the expected `int`. mypy also reports `error: Function "f" is missing an implementation`.
**Why:** Python name binding makes the last stub the runtime function. The ellipsis body returns `None`. mypy catches this at static-check time, but if you skip mypy in CI, the bug ships.
**Fix:** Always include the implementation as the last definition with the same name.

### Mistake 2: Stubs that disagree with the implementation

```python
@overload
def f(x: int) -> int: ...
def f(x):
    return str(x)  # ← returns str, not int
```

**Symptom:** mypy reports `error: Incompatible return value type (got "str", expected "int")` *only if* you annotate the implementation. If the implementation is unannotated (the common pattern), mypy does *not* check the body against the stubs — it assumes you know what you are doing.
**Why:** mypy trusts the implementation matches the stubs; it does not verify. If the body returns the wrong type, callers will see the stub's return type but get the wrong value at runtime — a silent bug.
**Fix:** Either annotate the implementation so mypy checks it, or write tests that assert the return types. The boardly convention is to write the implementation unannotated (per the typing community convention) but to have a unit test that calls each overload and asserts the type/value.

### Mistake 3: Stubs that are unreachable (overlap)

```python
@overload
def f(x: int) -> int: ...
@overload
def f(x: int | str) -> str: ...  # ← matches int as well; ambiguity
def f(x): ...
```

**Symptom:** mypy reports `error: Overload 2 overlaps with overload 1` — the stubs are not disjoint, so the type-checker cannot pick unambiguously.
**Why:** `@overload` requires the stubs to be *disjoint* in their input types. If two stubs both match a given call, mypy reports an overlap error. The order matters too — mypy picks the *first* matching stub, so list more specific stubs first.
**Fix:** Order stubs from most-specific to most-general. Use `Literal` to make the dispatch disjoint (e.g., `Literal["active"]` vs `Literal["archived"]` vs `str` — the third catches anything the first two do not).

## Engineering Trade-Offs

**Decision:** Use `@overload` for any function whose return type *depends* on the input type or value; use `singledispatch` for *runtime* dispatch on the first arg's type.
**Both sides:** `@overload` is static-only — the stubs are decorative; the implementation must handle all cases via `isinstance`/`match`. `singledispatch` is runtime — the dispatch happens via a registry of `type -> handler` functions, no `isinstance` needed. `@overload` is more flexible (can dispatch on `Literal` values, not just types) but requires you to write the dispatch logic in the implementation. `singledispatch` is less flexible (only type dispatch) but has cleaner separation per-type code.
**Commitment:** boardly uses `@overload` for public API functions whose return shape varies by input (`get_ticket`, `parse_status`, `make_filter`). We use `functools.singledispatch` for internal helpers where each type has a completely different implementation and we want the per-type code isolated (lesson `02-functools/04-singledispatch` covers this in depth). The two tools are complementary, not alternatives.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/overload_basics.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/overload_basics.py`
2. **Exercise 2 — Add a `Literal["deleted"]` overload.** Add a fourth stub for `parse_status(s: Literal["deleted"]) -> int` and update the implementation. Verify `parse_status("deleted")` returns `3`. `Verify: python -c "from boardly.overload_basics import parse_status; print(parse_status('deleted'))"`
3. **Exercise 3 — Return a `TypedDict` from `get_ticket`.** Replace the `dict` return with `TicketByID` (a `TypedDict` with `id: int` and `title: str`) for the int overload and `TicketBySlug` (a `TypedDict` with `slug: str` and `title: str`) for the str overload. Confirm the caller now sees the right shape. `Verify: python -c "from boardly.overload_basics import get_ticket; t = get_ticket(1); print(t['id'])"`
4. **Exercise 4 — Overload for `None`.** Add `@overload def get_ticket(id_or_slug: None) -> None: ...` and confirm `get_ticket(None)` returns `None`. Discuss when this is useful (e.g., optional parameters). `Verify: python -c "from boardly.overload_basics import get_ticket; print(get_ticket(None))"`
5. **Exercise 5 — Compare to `singledispatch`.** Reimplement `get_ticket` using `@functools.singledispatch` with `@register(int)` and `@register(str)` handlers. Document when `@overload` wins (return type varies) and when `singledispatch` wins (per-type implementations isolated). `Verify: python -c "from boardly.overload_basics import get_ticket_sd; print(get_ticket_sd(1))"`

## Verification

```bash
$ python boardly/overload_basics.py
get_ticket int: {'id': 1, 'title': 'Ticket #1'}
get_ticket str: {'slug': 'ada-123', 'title': 'Ada 123'}
parse_status active: 1
parse_status unknown: pending
make_filter one arg: {'key': 'status'}
make_filter two args: {'key': 'status', 'value': 'open'}
make_filter ci: {'key': 'status', 'ci': True}
get_ticket module has 1 get_ticket in module dict
get_ticket hints (impl): {}
get_ticket __name__: get_ticket
```

If `get_ticket module has 1` appears, you have demonstrated the stubs are decorative at runtime. If `get_ticket hints (impl): {}` appears, you have demonstrated that `get_type_hints` sees only the implementation's (empty) annotations.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `int | str` for union args. `@overload` lets you give *per-case* return types instead of the union of all.
- [[01-typing/08-Literal-and-TypeGuard]] — `Literal[...]` for fixed-set values. `@overload` + `Literal` is the "string-in, literal-out" pattern.

## What's Next

[[01-typing/10-Future-Annotations]] — `from __future__ import annotations` (PEP 563) and what it does to every annotation in a file. Three things to look for in lesson 10:

- Why `from __future__ import annotations` makes `__annotations__` store *strings*, not types.
- How `get_type_hints` resolves the strings back to types — and when it cannot (forward refs that are not yet defined).
- PEP 649 (deferred evaluation, default in 3.14) — the future replacement for PEP 563. Version-gated.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.overload — CPython reference** — https://docs.python.org/3/library/typing.html#typing.overload — accessed 2026-10-23 — the canonical API for `@overload`, including the stub-vs-implementation requirement and the disjoint-stubs rule.
- **PEP 484 — Type Hints (the Overloading section)** — https://peps.python.org/pep-0484/#overloading — accessed 2026-10-23 — the original `@overload` PEP, including the rule that the implementation must follow the stubs.
- **mypy — Overloads documentation** — https://mypy.readthedocs.io/en/stable/more_types.html#function-overloading — accessed 2026-10-23 — the production rules mypy applies to overload stubs, including overlap detection and ordering.

## What We Learned

- `@overload` stubs before a function implementation give mypy multiple signatures to check against; the stubs do not run at runtime.
- At runtime, only the implementation exists — the stubs are silently overwritten by Python name binding.
- `@overload` + `Literal[...]` is the "string-in, literal-out" pattern — mypy picks the right stub based on the literal at the call site.
- `@overload` on argument count lets you give per-calling-convention return types and document the conventions in IDE hover.
- The implementation must come *after* the stubs; otherwise the stubs are the runtime function (with `...` body returning `None`).
- Stubs must be disjoint in their input types; list more specific stubs first.
- `get_type_hints(overloaded_fn)` returns the implementation's hints (often `{}` if unannotated), not the stubs'.
