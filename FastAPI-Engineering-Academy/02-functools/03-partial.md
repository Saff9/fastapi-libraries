---
title: "Lesson 03: partial and partialmethod"
aliases:
 - functools.partial
 - functools.partialmethod
 - partial
tags:
 - functools
 - partial
 - currying
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[02-functools/02-wraps-and-Decorators]]"
related_lessons:
 - "[[02-functools/04-singledispatch]]"
 - "[[18-operator/01-itemgetter-attrgetter]]"
---

# Lesson 03: `partial` and `partialmethod`

*Currying without a lambda — bind some arguments now, leave the rest free, and let Python's `partial` object carry the binding around as a first-class callable.*

**You're at the very beginning of Section 02.**

`functools.partial` is the function-programming primitive that Python engineers under-use because the lambda is right there. A lambda is shorter to type; a `partial` is richer to introspect. When you `partial` a function, the resulting object exposes `.func`, `.args`, and `.keywords` — three attributes that make the binding visible to debugging tools, signature inspection, and the type checkers. By the end of this lesson you will know when `partial` beats a lambda (almost always, in production code), when `partialmethod` is the right tool for a class, and where the line between `partial` and `operator.itemgetter` falls. Take your time. Type every example. **This is how you learn.**

#functools #partial #currying

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply `functools.partial(fun, *args, **kwargs)`** to curry a function — binding some arguments while leaving others free.
2. **Read `.func`, `.args`, `.keywords`** on a `partial` object and explain what each exposes.
3. **Use `functools.partialmethod`** to bind arguments to a class method at class-definition time.
4. **Choose between `partial` and a lambda** — and articulate why `partial` wins for production code.
5. **Distinguish `partial` from `operator.itemgetter`** — both create callables, but they have different jobs.

## Prerequisites

Before starting, you need:

- **Functions as first-class objects** — `f = print; f("hi")` should feel normal.
- **About 20–30 minutes of focused time.**

**The most common gap: reaching for a lambda when a `partial` is the right tool.**

Lambdas are convenient for one-off inline callables: `sorted(rows, key=lambda r: r["name"])`. They are wrong for reusable, named, introspectable callables: `fetch_with_client = lambda slug: fetch_project(client, slug)` throws away the function's identity, the bound arguments, and the original signature. A `partial` keeps all three.

## The Problem

You have a `fetch_project(client, slug)` function in `boardly/api/projects.py`. In production, every caller has the same `client` (the singleton HTTP client wired up in `lifespan`); only the `slug` changes. You don't want every caller to repeat `client=` — that's noise and it's a refactoring hazard if the client ever needs to be swapped per-test. You want a function that takes just `slug` and uses the right `client` internally.

Three options:

1. **A lambda** — `fetch_with_client = lambda slug: fetch_project(client, slug)`. Short, but `fetch_with_client.__name__` is `"<lambda>"`, `inspect.signature(fetch_with_client)` returns `(slug)`, and there's no way to recover `client` from the closure without inspecting cells.
2. **A nested function** — `def fetch_with_client(slug): return fetch_project(client, slug)`. Same closure problem; the bound `client` is invisible.
3. **A `partial`** — `fetch_with_client = functools.partial(fetch_project, client)`. The bound `client` is exposed as `fetch_with_client.args[0]`; the original function is `fetch_with_client.func`; the signature is recoverable. This is the right tool.

## The Code

```python
# boardly/partial_demo.py
"""Demonstrate functools.partial, partialmethod, and the itemgetter comparison."""
from __future__ import annotations

import functools
import operator
from typing import Any, Callable


# --- The function we want to curry ---
def fetch_project(client: Any, slug: str) -> dict[str, str]:
    """Return project metadata via a client (duck-typed)."""
    return client.get(f"/projects/{slug}")


class FakeClient:
    """Stand-in for an HTTP client — boardly has a real one in production."""
    def __init__(self, projects: dict[str, dict[str, str]]) -> None:
        self.projects = projects
    def get(self, path: str) -> dict[str, str]:
        slug = path.rsplit("/", 1)[-1]
        return self.projects[slug]


client = FakeClient({
    "auth": {"id": "p_001", "name": "Auth Rewrite"},
    "billing": {"id": "p_002", "name": "Billing Migration"},
})


# --- partial: bind the client, leave the slug free ---
fetch_with_client = functools.partial(fetch_project, client)

# The lambda form — semantically identical but introspectively worse
fetch_with_client_lambda: Callable[[str], dict[str, str]] = lambda slug: fetch_project(client, slug)


# --- partialmethod: the same idea, for class methods ---
class ProjectService:
    """Service that wraps a client and exposes per-resource helpers."""
    def __init__(self, client: FakeClient) -> None:
        self.client = client

    def fetch(self, slug: str) -> dict[str, str]:
        return fetch_project(self.client, slug)

    # Bind the slug argument at class-definition time
    fetch_auth = functools.partialmethod(fetch, slug="auth")
    fetch_billing = functools.partialmethod(fetch, slug="billing")


def _get_field(obj: dict[str, str], key: str) -> str:
    """Pure-Python field extractor — used to compare against itemgetter."""
    return obj[key]


def main() -> None:
    print("=== partial: structure ===")
    print(f"partial:           {fetch_with_client}")
    print(f"partial.func:      {fetch_with_client.func}")
    print(f"partial.args:      {fetch_with_client.args}")
    print(f"partial.keywords:  {fetch_with_client.keywords}")

    print()
    print("=== partial vs lambda — same result ===")
    print(f"partial call:  {fetch_with_client('auth')}")
    print(f"lambda  call:  {fetch_with_client_lambda('auth')}")

    print()
    print("=== partialmethod on a class ===")
    svc = ProjectService(client)
    print(f"svc.fetch('billing'):   {svc.fetch('billing')}")
    print(f"svc.fetch_auth():       {svc.fetch_auth()}")
    print(f"svc.fetch_billing():    {svc.fetch_billing()}")

    print()
    print("=== partial vs operator.itemgetter ===")
    projects = [
        {"id": "p_001", "name": "Auth", "owner": "rahul"},
        {"id": "p_002", "name": "Billing", "owner": "maria"},
        {"id": "p_003", "name": "Search", "owner": "ana"},
    ]

    # itemgetter: a C-implemented callable that indexes its argument
    get_owner = operator.itemgetter("owner")
    get_id_and_owner = operator.itemgetter("id", "owner")

    # partial: pure-Python equivalent — slower, but composes with any callable
    get_owner_partial = functools.partial(_get_field, key="owner")

    print(f"itemgetter:  {[get_owner(p) for p in projects]}")
    print(f"partial:     {[get_owner_partial(p) for p in projects]}")
    print(f"multi-key:   {[get_id_and_owner(p) for p in projects]}")


if __name__ == "__main__":
    main()
```

## Line-by-Line Deep Dive

### Lines 1–7: Imports

```python
# boardly/partial_demo.py
"""Demonstrate functools.partial, partialmethod, and the itemgetter comparison."""
from __future__ import annotations

import functools
import operator
from typing import Any, Callable
```

`functools.partial` and `functools.partialmethod` are the stars. `operator.itemgetter` shows up in the comparison section at the bottom — it's the C-implemented sibling of "partial of `__getitem__`." `Any` and `Callable` are typing imports, made lazy by `from __future__ import annotations`.

### Lines 10–22: The function we want to curry, plus a fake client

```python
# --- The function we want to curry ---
def fetch_project(client: Any, slug: str) -> dict[str, str]:
    """Return project metadata via a client (duck-typed)."""
    return client.get(f"/projects/{slug}")


class FakeClient:
    """Stand-in for an HTTP client — boardly has a real one in production."""
    def __init__(self, projects: dict[str, dict[str, str]]) -> None:
        self.projects = projects
    def get(self, path: str) -> dict[str, str]:
        slug = path.rsplit("/", 1)[-1]
        return self.projects[slug]
```

`fetch_project` is a two-argument function — `(client, slug)` — that delegates to `client.get(path)`. The `client: Any` annotation is deliberately loose: in production it's `httpx.AsyncClient`, in tests it's whatever stub you wrote, and duck typing lets the function work with any object that has a `.get(path) -> dict[str, str]` method. This loose typing is what makes `partial` shine — you can bind any compatible client without changing the function's signature.

`FakeClient` is a stand-in for a real HTTP client. `time.sleep(0.08)` would simulate latency in a real demo; here we just return from the in-memory dict, keeping the example offline.

### Lines 27–32: The `partial` and the lambda

```python
# --- partial: bind the client, leave the slug free ---
fetch_with_client = functools.partial(fetch_project, client)

# The lambda form — semantically identical but introspectively worse
fetch_with_client_lambda: Callable[[str], dict[str, str]] = lambda slug: fetch_project(client, slug)
```

`functools.partial(fetch_project, client)` returns a `partial` object. When called with `("auth",)`, it forwards the call as `fetch_project(client, "auth")` — the bound `client` is prepended to the call's positional args. The bound `client` is stored on `fetch_with_client.args` as a tuple `(client,)`, and the original function is stored on `fetch_with_client.func`. The signature, when introspected, reads as the *remaining* parameters of the original function — `(slug: str)` — because `inspect` knows about `partial` and unwraps the bound args (since Python 3.8, `inspect.signature` follows `functools.partial` bindings).

The lambda form is semantically equivalent: it captures `client` in its closure and returns the same result. The difference is *introspectability*: `fetch_with_client_lambda.__name__` is `"<lambda>"`, `inspect.signature(fetch_with_client_lambda)` returns `(slug)` (no annotation, no default, no recoverable binding). You can't ask the lambda "what client are you bound to?" — the answer lives in a closure cell that's not part of the public API.

**Why does `partial` beat a lambda for production code?** Three reasons. First, debugging: a stack trace shows `functools.partial(<function fetch_project>, <FakeClient ...>)` instead of `<lambda>` — you immediately see what the lambda is doing. Second, testing: you can read `fetch_with_client.args[0]` to assert what client is bound, which you cannot do with a lambda. Third, `inspect.signature` follows the `partial` so FastAPI's `Depends` and similar signature-driven tools see the right shape.

### Lines 35–45: `partialmethod` on a class

```python
# --- partialmethod: the same idea, for class methods ---
class ProjectService:
    """Service that wraps a client and exposes per-resource helpers."""
    def __init__(self, client: FakeClient) -> None:
        self.client = client

    def fetch(self, slug: str) -> dict[str, str]:
        return fetch_project(self.client, slug)

    # Bind the slug argument at class-definition time
    fetch_auth = functools.partialmethod(fetch, slug="auth")
    fetch_billing = functools.partialmethod(fetch, slug="billing")
```

`functools.partialmethod` is `partial` for methods. The crucial difference: a regular `partial` would *not* bind `self` — `partial(fetch, slug="auth")` would create a callable that still needs `self`, but it wouldn't be a proper descriptor, so `svc.fetch_auth` would return a `partial` object, not a bound method. `partialmethod` *is* a descriptor: when accessed on an instance (`svc.fetch_auth`), it returns a callable that already has `self` bound, plus the partial-bound `slug="auth"`. The result: `svc.fetch_auth()` calls `svc.fetch(slug="auth")`.

The use case is the classic "named endpoint" pattern — you have a generic `fetch(slug)` and you want convenient named methods like `fetch_auth()`, `fetch_billing()` without writing 50 lines of one-line wrappers. `partialmethod` does it in one line each.

**Why not just write `def fetch_auth(self): return self.fetch("auth")`?** You can, and for two or three endpoints you should — it's clearer. `partialmethod` pays off when you have many endpoints and they're generated programmatically (e.g. from a config file or a list of slugs). Then `partialmethod` lets you build them in a loop: `for slug in slugs: setattr(ProjectService, f"fetch_{slug}", partialmethod(ProjectService.fetch, slug=slug))`.

### Lines 48–51: A helper for the comparison section

```python
def _get_field(obj: dict[str, str], key: str) -> str:
    """Pure-Python field extractor — used to compare against itemgetter."""
    return obj[key]
```

`_get_field` is a two-argument pure-Python function — `obj` and `key`. It exists only so we can `partial` it and compare against `operator.itemgetter`. The leading underscore marks it as private.

### Lines 54–83: The `main` routine

```python
def main() -> None:
    print("=== partial: structure ===")
    print(f"partial:           {fetch_with_client}")
    print(f"partial.func:      {fetch_with_client.func}")
    print(f"partial.args:      {fetch_with_client.args}")
    print(f"partial.keywords:  {fetch_with_client.keywords}")
```

The first block prints the `partial` object itself and its three public attributes. `partial.func` is the original `fetch_project`. `partial.args` is the tuple of bound positional args — `(client,)` here. `partial.keywords` is the dict of bound keyword args — empty here because we bound positionally. If you bound keyword — `partial(fetch_project, client=client)` — then `args` would be `()` and `keywords` would be `{"client": client}`. The repr of the `partial` object shows `func` and the bound args, so a debugger or `print` immediately tells you what's bound.

```python
    print()
    print("=== partial vs lambda — same result ===")
    print(f"partial call:  {fetch_with_client('auth')}")
    print(f"lambda  call:  {fetch_with_client_lambda('auth')}")
```

Both produce the same result. This is the proof that `partial` and the lambda are *behaviourally* equivalent — the difference is purely in introspection and reuse, not in what they compute.

```python
    print()
    print("=== partialmethod on a class ===")
    svc = ProjectService(client)
    print(f"svc.fetch('billing'):   {svc.fetch('billing')}")
    print(f"svc.fetch_auth():       {svc.fetch_auth()}")
    print(f"svc.fetch_billing():    {svc.fetch_billing()}")
```

`svc.fetch("billing")` is the generic call. `svc.fetch_auth()` is the partialmethod call — same result, no `slug` argument needed. This is the value of `partialmethod`: named methods for fixed resources.

```python
    print()
    print("=== partial vs operator.itemgetter ===")
    projects = [
        {"id": "p_001", "name": "Auth", "owner": "rahul"},
        {"id": "p_002", "name": "Billing", "owner": "maria"},
        {"id": "p_003", "name": "Search", "owner": "ana"},
    ]

    # itemgetter: a C-implemented callable that indexes its argument
    get_owner = operator.itemgetter("owner")
    get_id_and_owner = operator.itemgetter("id", "owner")

    # partial: pure-Python equivalent — slower, but composes with any callable
    get_owner_partial = functools.partial(_get_field, key="owner")

    print(f"itemgetter:  {[get_owner(p) for p in projects]}")
    print(f"partial:     {[get_owner_partial(p) for p in projects]}")
    print(f"multi-key:   {[get_id_and_owner(p) for p in projects]}")
```

`operator.itemgetter("owner")` returns a callable that, given any object supporting `["owner"]`, returns `obj["owner"]`. It's implemented in C, so it's about 2× faster than the pure-Python `partial` of `_get_field`. It also supports multi-key access — `itemgetter("id", "owner")` returns a tuple `("p_001", "rahul")` — which a single `partial` cannot do directly.

The line: use `itemgetter` for *field extraction* (one job, optimized for it), and `partial` for *argument binding to any callable* (general-purpose). The two tools are siblings, not competitors.

## Execution Trace

```bash
$ uv run python boardly/partial_demo.py
=== partial: structure ===
partial:           functools.partial(<function fetch_project at 0x...>, <__main__.FakeClient object at 0x...>)
partial.func:      <function fetch_project at 0x...>
partial.args:      (<__main__.FakeClient object at 0x...>,)
partial.keywords:  {}

=== partial vs lambda — same result ===
partial call:  {'id': 'p_001', 'name': 'Auth Rewrite'}
lambda  call:  {'id': 'p_001', 'name': 'Auth Rewrite'}

=== partialmethod on a class ===
svc.fetch('billing'):   {'id': 'p_002', 'name': 'Billing Migration'}
svc.fetch_auth():       {'id': 'p_001', 'name': 'Auth Rewrite'}
svc.fetch_billing():    {'id': 'p_002', 'name': 'Billing Migration'}

=== partial vs operator.itemgetter ===
itemgetter:  ['rahul', 'maria', 'ana']
partial:     ['rahul', 'maria', 'ana']
multi-key:   [('p_001', 'rahul'), ('p_002', 'maria'), ('p_003', 'ana')]
```

The first block shows the `partial` object's three introspection attributes. The second block shows the partial and the lambda return identical results. The third block shows `partialmethod` working on a class — `fetch_auth()` and `fetch_billing()` produce the same results as the generic `fetch(slug)` call. The fourth block shows `itemgetter` and `partial` producing the same single-key result, with `itemgetter` additionally supporting multi-key access via a tuple return.

## Common Mistakes

### Mistake 1: Using `partial` on a method that needs `self`

```python
class Service:
    def fetch(self, slug: str) -> dict: ...
    fetch_auth = functools.partial(fetch, slug="auth")  # ← breaks
```

**Symptom:** `TypeError: fetch_auth() missing 1 required positional argument: 'self'` when you call `svc.fetch_auth()`.

**Why:** A regular `partial` is not a descriptor. When you access `svc.fetch_auth`, Python returns the `partial` object as-is, without binding `self`. Calling `svc.fetch_auth()` then calls `partial(fetch, slug="auth")()` which calls `fetch(slug="auth")` — but `fetch` is an unbound function and needs `self` first.

**Fix:** Use `functools.partialmethod` — it's a descriptor that binds `self` on attribute access.

### Mistake 2: Expecting `partial` to bind keyword arguments positionally

```python
def f(a, b): return (a, b)
p = functools.partial(f, b=2)
p(1)  # → (1, 2)
p(1, 2)  # → TypeError: f() got multiple values for argument 'b'
```

**Symptom:** `TypeError: got multiple values for argument 'b'` when you call the partial with the bound argument again.

**Why:** `partial(f, b=2)` binds `b` as a keyword. When you call `p(1, 2)`, the `2` is positional and goes to `a`, but the `b=2` from the partial is *also* there, so `b` gets two values.

**Fix:** Either bind positionally — `partial(f, 2)` then call `p(1)` to get `(1, 2)` reversed — or restructure so the bound argument is consistently keyword or positional.

### Mistake 3: Confusing `partial` with a closure factory

```python
def make_fetcher(client):
    return functools.partial(fetch_project, client)  # correct
    # vs.
    return lambda slug: fetch_project(client, slug)   # also works, but loses introspection
```

**Symptom:** No bug — both work. But the lambda's stack trace shows `<lambda>`, and the partial's shows `fetch_project`. You'll regret the lambda at 3am debugging.

**Why:** The closure captures `client` in a cell that's invisible to introspection. The partial stores `client` on `.args[0]`, visible to `print`, debugger, and tests.

**Fix:** Use `partial` for any reusable bound callable. Reserve lambdas for one-off inline use (e.g. `sorted(rows, key=lambda r: r["name"])`).

## Engineering Trade-Offs

**Decision:** Use `partial` for argument binding when the bound callable will be referenced by name, stored in a registry, or passed to signature-driven tooling (FastAPI, click, inspect).

**Both sides:** The alternative is a nested function. A nested function is more flexible — you can add logic, default values, or extra arguments — but it loses the `partial`'s introspection properties. For a pure argument binding with no extra logic, `partial` is the right call. For a binding with extra behaviour (e.g. logging, fallback), use the nested function and add `@functools.wraps` to preserve identity.

**Commitment:** `boardly` uses `partial` for every "bound client + free slug" pattern. The `partialmethod` form is used in `ProjectService` and `UserService` to expose per-resource named methods (`fetch_auth`, `fetch_billing`, etc.) without one-line wrapper boilerplate. The project's lint config discourages top-level lambdas (`E731`): top-level lambdas are flagged and converted to `partial` or `def`.

**Why use `partial` when a `def` is two more lines?** Two reasons. First, the `partial` is *transparent* — debugging tools can read its bound args. A nested `def` hides the bound args in a closure. Second, the `partial` is composable — `partial(partial(f, a), b)` works (you can chain them), which is occasionally useful in decorator stacks.

## Exercises

1. **Exercise 1 — Inspect the partial.** Add a `print(fetch_with_client.args)` call after the existing prints. Confirm `args` is a 1-tuple containing the client instance. `Verify: uv run python boardly/partial_demo.py`

2. **Exercise 2 — Bind a keyword argument.** Create `fetch_project_keyword = functools.partial(fetch_project, slug="auth")`. Call it with just `client` as the positional argument. Verify it returns the auth project. `Verify: uv run python boardly/partial_demo.py`

3. **Exercise 3 — Add a `partialmethod`.** Add `fetch_search = functools.partialmethod(fetch, slug="search")` to `ProjectService`. Add the corresponding project (`"search"`) to the `FakeClient`'s projects dict. Call `svc.fetch_search()` and verify the result. `Verify: uv run python boardly/partial_demo.py`

4. **Exercise 4 — Time `partial` vs `itemgetter`.** Use `timeit` to compare `[get_owner(p) for p in projects]` vs `[get_owner_partial(p) for p in projects]` over 100,000 iterations. Confirm `itemgetter` is roughly 2× faster. `Verify: uv run python -c "import timeit; print(timeit.timeit(...))"`

5. **Exercise 5 — Compose two `partial`s.** Write `f = functools.partial(lambda a, b, c: (a, b, c), 1)` and `g = functools.partial(f, 2)`. Call `g(3)` and verify it returns `(1, 2, 3)`. This demonstrates that `partial`s compose — a property you'll use when building decorator stacks. `Verify: uv run python -c "..."`

## Verification

```bash
$ uv run python boardly/partial_demo.py
=== partial: structure ===
partial:           functools.partial(<function fetch_project at 0x...>, <__main__.FakeClient object at 0x...>)
partial.func:      <function fetch_project at 0x...>
partial.args:      (<__main__.FakeClient object at 0x...>,)
partial.keywords:  {}

=== partial vs lambda — same result ===
partial call:  {'id': 'p_001', 'name': 'Auth Rewrite'}
lambda  call:  {'id': 'p_001', 'name': 'Auth Rewrite'}

=== partialmethod on a class ===
svc.fetch('billing'):   {'id': 'p_002', 'name': 'Billing Migration'}
svc.fetch_auth():       {'id': 'p_001', 'name': 'Auth Rewrite'}
svc.fetch_billing():    {'id': 'p_002', 'name': 'Billing Migration'}

=== partial vs operator.itemgetter ===
itemgetter:  ['rahul', 'maria', 'ana']
partial:     ['rahul', 'maria', 'ana']
multi-key:   [('p_001', 'rahul'), ('p_002', 'maria'), ('p_003', 'ana')]
```

## Previously Learned Here

- [[02-functools/02-wraps-and-Decorators]] — `@wraps` preserves identity when wrapping a function; `partial` preserves identity when binding arguments. The two are complementary primitives for the same goal: keeping introspection honest.

## What's Next

[[02-functools/04-singledispatch]] — where `partial` binds arguments, `singledispatch` binds behaviour by argument type. Together they cover the two ways you'll want to specialize a generic function: by value (partial) and by type (singledispatch). The FastAPI `Depends` system is the modern spiritual sibling of `singledispatch`.

- `@singledispatch` + `@fun.register(Type)` — type-keyed dispatch.
- The MRO resolution order.
- `@singledispatchmethod` (3.8+) for class methods.
- The FastAPI `Depends` parallel — type-keyed dependency injection.

## Sources

- **`functools.partial`** — https://docs.python.org/3.12/library/functools.html#functools.partial — accessed 2026-10-23 — the canonical reference for `partial`, `.func`, `.args`, `.keywords`.
- **`functools.partialmethod`** — https://docs.python.org/3.12/library/functools.html#functools.partialmethod — accessed 2026-10-23 — the descriptor-aware sibling for class methods (3.4+).
- **`operator.itemgetter`** — https://docs.python.org/3.12/library/operator.html#operator.itemgetter — accessed 2026-10-23 — the C-implemented sibling of `partial(dict.__getitem__, ...)`.

## What We Learned

- You can apply `functools.partial(fun, *args, **kwargs)` to curry a function.
- You can read `.func`, `.args`, `.keywords` on a `partial` object.
- You can use `functools.partialmethod` to bind arguments to class methods.
- You can choose between `partial` and a lambda — and you know when `partial` wins.
- You can distinguish `partial` from `operator.itemgetter` and reach for each in the right case.
