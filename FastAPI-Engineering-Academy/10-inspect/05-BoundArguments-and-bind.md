---
title: "Lesson 05: BoundArguments and bind"
aliases:
 - inspect.Signature.bind
 - inspect.Signature.bind_partial
 - BoundArguments
 - apply_defaults
 - bound.arguments
tags:
 - inspect
 - python-stdlib
 - binding
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–45 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[10-inspect/02-get_type_hints]]"
 - "[[10-inspect/04-Parameter-kinds]]"
related_lessons:
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
 - "[[10-inspect/04-Parameter-kinds]]"
---

# Lesson 05: BoundArguments and bind

*How `boardly`'s `sig.bind(42, "open", user="alice")` turns an incoming HTTP request into a `BoundArguments` object — `.arguments`, `.args`, `.kwargs`, `apply_defaults()` — and how FastAPI uses the same `bind` call to figure out which dependencies to inject.*

**You're at the very beginning of Section 10 — five lessons in.**

You have walked `Signature.parameters` and you know each `Parameter`'s `kind`. You have not yet seen Python *apply* an incoming argument list to a signature — the step that turns `(42, "open", user="alice")` into a dict `{"id": 42, "status": "open", "user": "alice"}`. That step is `Signature.bind`, and the dict it produces is `BoundArguments`. Today you will see what `bind` does, why `bind_partial` exists, and how FastAPI uses both to mix request data with resolved dependencies before calling your route. Take your time. Type every example. **This is how you learn.**

#inspect #binding

## Learning Objectives

By the end of this lesson you will be able to:

1. **Call `Signature.bind(*args, **kwargs)`** — pass the same args you would pass to the function, get back a `BoundArguments` object that has resolved each arg to its parameter name.
2. **Read `BoundArguments.arguments`** — a `dict` mapping parameter name to bound value, the shape you mutate when injecting dependencies.
3. **Read `BoundArguments.args` and `.kwargs`** — the tuple and dict computed from `.arguments`, ready to splat into `f(*bound.args, **bound.kwargs)`.
4. **Call `apply_defaults()`** — fill in `Parameter.empty`-defaulted parameters that were not supplied by the caller (including `()` for `VAR_POSITIONAL` and `{}` for `VAR_KEYWORD`).
5. **Explain `bind_partial` vs `bind`** — `bind` raises `TypeError` on any missing required parameter; `bind_partial` lets you defer that check (FastAPI uses it to skip dependency params until after they are resolved).
6. **Sketch FastAPI's bind-and-inject flow** — `bind_partial(request_data)` → fill in resolved `Depends()` values via `bound.arguments[name] = value` → `apply_defaults()` → `f(*bound.args, **bound.kwargs)`.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[10-inspect/01-signature-and-Parameter]] — `Signature`, `Parameter`, the `empty` sentinel.
- **Lesson 04** — [[10-inspect/04-Parameter-kinds]] — the five `Parameter.kind` values. `bind` walks parameters in kind-order; you need that mental model to read its output.
- **About 35–45 minutes of focused time.**

**The most common gap: thinking `bind` and calling the function are the same step.** They are not. `bind` is a *pure* operation — it walks the signature, fills a dict, and stops. The function is not called. The point of separating the steps is to let callers mutate the bound arguments (inject dependencies, apply defaults) between binding and calling. That separation is the entire reason `BoundArguments` exists as an object.

## The Problem

Here is the bug. `boardly` had this route:

```python
# boardly/routes/tickets.py — the bad old days
def get_ticket(id: int, status: str = "open", user: str = "alice"):
    return {"id": id, "status": status, "user": user}

# Somewhere else — call it with whatever the HTTP request gives you
def handler(query_params: dict):
    return get_ticket(**query_params)   # if query_params has 'id', fine
                                          # if it has 'status' AND 'user', also fine
                                          # if it has 'extra_param', TypeError
                                          # if it lacks 'id', TypeError
```

The handler blindly splats the query dict into the function call. Three failure modes follow:

1. **Missing required param:** `query_params = {"status": "open"}` → `TypeError: missing a required argument: 'id'`.
2. **Extra param:** `query_params = {"id": 42, "extra": "x"}` → `TypeError: unexpected keyword argument 'extra'`.
3. **Type coercion:** `query_params = {"id": "42"}` → no error, but `id` is now a string, not the int the function expects.

`bind` is the step that catches failures 1 and 2 *before* the function runs. You call `sig.bind(**query_params)`; if it returns, the args are well-formed; if it raises `TypeError`, you return a 422 before touching the function. That is the validation step FastAPI does on every request.

The bug that motivates `bind` is "I want to know if the incoming args fit the function's signature, and I want to know *before* I call the function." The fix is one call.

## The Code

```python
# boardly/di_bind.py
"""Demonstrates Signature.bind, BoundArguments, bind_partial, apply_defaults."""
import inspect


# 1. A boardly function with mixed parameter kinds
def get_ticket(
    id: int,
    status: str = "open",
    *tags,
    user,
    **extra,
) -> dict:
    """Read a boardly ticket."""
    return {"id": id, "status": status, "tags": tags, "user": user, **extra}


sig = inspect.signature(get_ticket)
print(f"sig: {sig}")


# 2. Full bind — supply all required args plus a few extras
bound = sig.bind(42, "open", "api", "bug", user="alice", board="x")
print("\n--- sig.bind(42, 'open', 'api', 'bug', user='alice', board='x') ---")
print(f"  type(bound):           {type(bound).__name__}")
print(f"  bound.arguments:       {dict(bound.arguments)}")
print(f"  bound.args:            {bound.args}")
print(f"  bound.kwargs:          {bound.kwargs}")
result = get_ticket(*bound.args, **bound.kwargs)
print(f"  get_ticket(*a, **k):    {result}")


# 3. Partial bind — skip the defaulted `status`
bound_partial = sig.bind(42, user="alice")
print("\n--- sig.bind(42, user='alice') — defaulted `status` omitted ---")
print(f"  bound.arguments: {dict(bound_partial.arguments)}")
print(f"  bound.args:      {bound_partial.args}")
print(f"  bound.kwargs:    {bound_partial.kwargs}")
# `status` is NOT in arguments — bind does not apply defaults.
# Calling works only because the function has `status = 'open'` as a default.
result = get_ticket(*bound_partial.args, **bound_partial.kwargs)
print(f"  result (no defaults applied): {result}")


# 4. apply_defaults — fill in the missing defaults
bound_partial.apply_defaults()
print("\n--- after apply_defaults() ---")
print(f"  bound.arguments: {dict(bound_partial.arguments)}")
print(f"  bound.args:      {bound_partial.args}")
print(f"  bound.kwargs:    {bound_partial.kwargs}")


# 5. bind() rejects missing required args
print("\n--- sig.bind(42) — missing required `user` ---")
try:
    sig.bind(42)
except TypeError as e:
    print(f"  TypeError: {e}")


# 6. bind_partial() does NOT raise on missing required args
print("\n--- sig.bind_partial(42) — required `user` omitted, no error ---")
bp = sig.bind_partial(42)
print(f"  bp.arguments: {dict(bp.arguments)}")
print(f"  bp.args:      {bp.args}")
print(f"  bp.kwargs:    {bp.kwargs}")
# After apply_defaults, `user` is STILL missing — bind_partial doesn't fill required-missing.
bp.apply_defaults()
print(f"  after apply_defaults: {dict(bp.arguments)}")
# Calling now would fail: `user` is still required-but-absent.
try:
    get_ticket(*bp.args, **bp.kwargs)
except TypeError as e:
    print(f"  get_ticket(*a, **k) raises: {e}")


# 7. Simulated FastAPI flow — bind request data, inject resolved dependencies, call
def call_with_deps(call, request_kwargs, resolved_deps):
    """Bind request data, inject resolved dependency values, apply defaults, call."""
    sig = inspect.signature(call)
    bound = sig.bind_partial(**request_kwargs)
    for name, value in resolved_deps.items():
        if name not in bound.arguments:
            bound.arguments[name] = value   # write into the bound dict
    bound.apply_defaults()
    return call(*bound.args, **bound.kwargs)


# Pretend: `id` comes from the URL query string, `user` is resolved by Depends(get_user)
def get_user():
    return "alice"


result = call_with_deps(get_ticket, {"id": 42}, {"user": get_user()})
print(f"\n--- call_with_deps(get_ticket, {{'id': 42}}, {{'user': 'alice'}}) ---")
print(f"  result: {result}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 5–11: The function under inspection

```python
def get_ticket(
    id: int,
    status: str = "open",
    *tags,
    user,
    **extra,
) -> dict:
    """Read a boardly ticket."""
    return {"id": id, "status": status, "tags": tags, "user": user, **extra}
```

`get_ticket` deliberately mixes all five `Parameter.kind` values (lesson 04) so `bind` has to do real work:

- `id: int` — `POSITIONAL_OR_KEYWORD`. `bind(42)` or `bind(id=42)` both work.
- `status: str = "open"` — `POSITIONAL_OR_KEYWORD` with a default. `bind(42)` *omits* `status` from `.arguments` (no default applied); `bind(42, "open")` *includes* it.
- `*tags` — `VAR_POSITIONAL`. Extra positional args land here as a tuple in `.arguments["tags"]`.
- `user` — `KEYWORD_ONLY`. Must be passed as `user=...`; positional binding is rejected.
- `**extra` — `VAR_KEYWORD`. Extra keyword args land here as a dict in `.arguments["extra"]`.

The return annotation `-> dict` is for documentation; `bind` does not consult it.

**Why mix all five kinds in one example?** Because `bind`'s job is precisely to route incoming args to the correct parameter based on `kind`. If we used only `POSITIONAL_OR_KEYWORD` parameters, `bind` would be trivial (every arg is a positional). Mixing kinds forces `bind` to demonstrate the routing logic — and forces you to see what `args`/`kwargs` look like when the kind varies.

### Lines 14–22: Full bind — every required arg supplied

```python
bound = sig.bind(42, "open", "api", "bug", user="alice", board="x")
print("\n--- sig.bind(42, 'open', 'api', 'bug', user='alice', board='x') ---")
print(f"  type(bound):           {type(bound).__name__}")
print(f"  bound.arguments:       {dict(bound.arguments)}")
print(f"  bound.args:            {bound.args}")
print(f"  bound.kwargs:          {bound.kwargs}")
result = get_ticket(*bound.args, **bound.kwargs)
print(f"  get_ticket(*a, **k):    {result}")
```

`sig.bind(42, "open", "api", "bug", user="alice", board="x")` walks the signature in source order and matches each incoming arg to a parameter:

- `42` → `id` (positional, fills the first `POSITIONAL_OR_KEYWORD` slot).
- `"open"` → `status` (next positional slot).
- `"api"`, `"bug"` → `*tags` (`VAR_POSITIONAL` collects them as `("api", "bug")`).
- `user="alice"` → `user` (`KEYWORD_ONLY` accepts the keyword).
- `board="x"` → `**extra` (`VAR_KEYWORD` collects it as `{"board": "x"}`).

The output:

```
type(bound):           BoundArguments
bound.arguments:       {'id': 42, 'status': 'open', 'tags': ('api', 'bug'), 'user': 'alice', 'extra': {'board': 'x'}}
bound.args:            (42, 'open', 'api', 'bug')
bound.kwargs:          {'user': 'alice', 'board': 'x'}
```

The key insight: `.arguments` is the canonical mapping (parameter name → value). `.args` and `.kwargs` are *computed* from `.arguments` by walking the parameters in order and partitioning them — `POSITIONAL_*` and `VAR_POSITIONAL` go to `.args`; `KEYWORD_ONLY` and `VAR_KEYWORD` go to `.kwargs`. The recomputation is why mutating `.arguments` (which we do in section 7) changes `.args`/`.kwargs` automatically.

**Why are `.args` and `.kwargs` computed properties, not stored fields?** Because the canonical state is `.arguments`. The args/kwargs split is a *view* over that state, optimised for the common call pattern `f(*bound.args, **bound.kwargs)`. If they were stored independently, mutating `.arguments` would require a parallel update to `.args`/`.kwargs` — easy to forget, easy to break. The property pattern makes mutation safe.

### Lines 26–33: Partial bind — defaults omitted from `.arguments`

```python
bound_partial = sig.bind(42, user="alice")
print("\n--- sig.bind(42, user='alice') — defaulted `status` omitted ---")
print(f"  bound.arguments: {dict(bound_partial.arguments)}")
print(f"  bound.args:      {bound_partial.args}")
print(f"  bound.kwargs:    {bound_partial.kwargs}")
result = get_ticket(*bound_partial.args, **bound_partial.kwargs)
print(f"  result (no defaults applied): {result}")
```

`sig.bind(42, user="alice")` binds only what was supplied. `status` is *not* in `.arguments` because the caller did not pass it. The output:

```
bound.arguments: {'id': 42, 'user': 'alice'}
bound.args:      (42,)
bound.kwargs:    {'user': 'alice'}
```

`.arguments` has two entries, not five. `status` is missing — but the function call still works (`result: {'id': 42, 'status': 'open', ...}`), because Python falls back to the function's own `status="open"` default when the argument is absent.

**Why does `bind` not apply defaults?** Because defaults are a property of the *function*, not of the binding. `bind` says "here is what the caller supplied, mapped to parameter names." Whether the function then supplies a default for an absent parameter is the function's business. `apply_defaults()` (next block) is the explicit step that copies the function's defaults into `.arguments`. Separating them lets you inject dependencies *between* binding and default-application — which is exactly FastAPI's pattern (section 7).

### Lines 37–41: `apply_defaults()` fills in the gaps

```python
bound_partial.apply_defaults()
print("\n--- after apply_defaults() ---")
print(f"  bound.arguments: {dict(bound_partial.arguments)}")
print(f"  bound.args:      {bound_partial.args}")
print(f"  bound.kwargs:    {bound_partial.kwargs}")
```

`bound.apply_defaults()` walks the signature and, for any parameter *not in `.arguments`* but with a `default != Parameter.empty`, copies the default into `.arguments`. For our example:

```
after apply_defaults: {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice', 'extra': {}}
```

Three additions:

- `status = "open"` — the explicit default from the function definition.
- `tags = ()` — the implicit empty-tuple default for `VAR_POSITIONAL`.
- `extra = {}` — the implicit empty-dict default for `VAR_KEYWORD`.

`VAR_POSITIONAL` and `VAR_KEYWORD` get *implicit* defaults — `()` and `{}` — even though their `Parameter.default` is `Parameter.empty`. That is a special-case rule `apply_defaults` implements. The reasoning: a variadic collector is never "missing"; it accepts zero values. The default is the empty container.

**Why is `apply_defaults` a separate call, not the default behaviour of `bind`?** Two reasons. First, performance: in the FastAPI hot path, `bind` happens once per request and `apply_defaults` only when needed; collapsing them would force default-copying on every bind. Second, semantics: some callers want to know *what the caller actually supplied* (without defaults) — logging, access control, dependency resolution. `apply_defaults` mutates `.arguments` in place; the caller controls when. The separation is a deliberate API choice, not an oversight.

### Lines 44–49: `bind()` rejects missing required args

```python
print("\n--- sig.bind(42) — missing required `user` ---")
try:
    sig.bind(42)
except TypeError as e:
    print(f"  TypeError: {e}")
```

`sig.bind(42)` raises:

```
TypeError: missing a required argument: 'user'
```

`bind` enforces the function's contract: every parameter without a default *must* be supplied. This is the validation step FastAPI runs against the incoming request — if `bind` raises, FastAPI returns a 422 (Unprocessable Entity) without ever calling the route function. The route function never sees malformed input.

**Why does FastAPI not just call the function and let Python raise `TypeError`?** Two reasons. First, the error message: `bind`'s `TypeError` says "missing a required argument: 'user'" — clear and parameter-specific. The function-call `TypeError` is the same message but happens *inside* the function call, after partial work has been done (e.g., the response model has been built). Second, separation of concerns: validation should happen before the function runs, not during. `bind` is the validation gate.

### Lines 52–62: `bind_partial()` defers the required check

```python
print("\n--- sig.bind_partial(42) — required `user` omitted, no error ---")
bp = sig.bind_partial(42)
print(f"  bp.arguments: {dict(bp.arguments)}")
print(f"  bp.args:      {bp.args}")
print(f"  bp.kwargs:    {bp.kwargs}")
bp.apply_defaults()
print(f"  after apply_defaults: {dict(bp.arguments)}")
try:
    get_ticket(*bp.args, **bp.kwargs)
except TypeError as e:
    print(f"  get_ticket(*a, **k) raises: {e}")
```

`sig.bind_partial(42)` does *not* raise on the missing `user`. The output:

```
bp.arguments: {'id': 42}
bp.args:      (42,)
bp.kwargs:    {}
after apply_defaults: {'id': 42, 'status': 'open', 'tags': (), 'extra': {}}
get_ticket(*a, **k) raises: missing 1 required keyword-only argument: 'user'
```

`bind_partial` skips the "all required args supplied?" check. It binds what you give it and leaves the rest absent. After `apply_defaults`, only the defaulted params are filled — `user` is still absent because it has no default. Calling the function then raises the function's own `TypeError`.

**Why does `bind_partial` exist?** For partial application. If you have a function `def f(a, b, c):` and you want to produce a partial with `a=1` bound, you call `sig.bind_partial(1)` and use the bound arguments to construct a new callable. FastAPI uses `bind_partial` for a different reason: it does not yet know which args the dependency resolver will supply, so it binds the request data *leniently*, fills in the resolved deps by mutating `.arguments`, *then* calls. The lenient bind avoids spurious `TypeError`s on parameters that are about to be injected.

**Tip — `bind_partial` is not `bind` with relaxed rules**

```python
sig.bind_partial(42, unknown_kw="x")  # raises TypeError: too many positional arguments
sig.bind_partial(42, user="alice", unknown_kw="x")  # raises TypeError: unexpected keyword argument
```

`bind_partial` is lenient about *missing* required args, not about *extra* args. Arg-count and arg-name validation still applies. The only relaxation is "you don't have to supply all required params."

### Lines 65–74: Simulated FastAPI flow — bind, inject, call

```python
def call_with_deps(call, request_kwargs, resolved_deps):
    """Bind request data, inject resolved dependency values, apply defaults, call."""
    sig = inspect.signature(call)
    bound = sig.bind_partial(**request_kwargs)
    for name, value in resolved_deps.items():
        if name not in bound.arguments:
            bound.arguments[name] = value   # write into the bound dict
    bound.apply_defaults()
    return call(*bound.args, **bound.kwargs)


# Pretend: `id` comes from the URL query string, `user` is resolved by Depends(get_user)
def get_user():
    return "alice"


result = call_with_deps(get_ticket, {"id": 42}, {"user": get_user()})
print(f"\n--- call_with_deps(get_ticket, {{'id': 42}}, {{'user': 'alice'}}) ---")
print(f"  result: {result}")
```

This is the FastAPI pattern in miniature, with three steps:

1. **`bind_partial(**request_kwargs)`** — bind what the request supplied. In our example, `{"id": 42}` from the URL. `bind_partial` allows `user` to be missing because we are about to fill it in.
2. **Mutate `.arguments`** — for each dependency the resolver produced (`{"user": "alice"}`), write it into `bound.arguments[name]`. The check `if name not in bound.arguments` is important: if the request happened to supply `user` already (e.g., a query param named `user`), we do not overwrite it. This is FastAPI's actual rule — request data wins over dependency resolution for the same parameter name.
3. **`apply_defaults()`** — fill in any remaining defaulted params (`status`, `tags`, `extra`). Then call via `f(*bound.args, **bound.kwargs)`.

The output:

```
result: {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice'}
```

`status` came from the function's default, `tags` and `extra` from `apply_defaults`'s implicit-empty rule, `id` from the request, `user` from the dependency. The function ran with a complete, validated argument set.

**Why mutate `.arguments` instead of passing `user=...` as a separate kwarg?** Because `user` might be `POSITIONAL_ONLY` (no keyword call allowed) or `KEYWORD_ONLY` (no positional call allowed) — passing it as a kwarg would fail for `POSITIONAL_ONLY`, passing it as a positional would fail for `KEYWORD_ONLY`. Mutating `.arguments` lets `bound.args`/`bound.kwargs` recompute the right partition automatically — kind-aware. That is the whole reason `BoundArguments` exists as an object you can mutate.

**Why the `if name not in bound.arguments` guard?** Because FastAPI's rule is "request data wins." If the URL has `?user=bob` AND the dependency produces `"alice"`, the URL value is what gets called. The dependency value is the fallback. This rule prevents ambiguous state — the user-facing data is always the request data, not the resolved dep. Lesson 06 shows the full dependency resolution loop, including this guard.

## Execution Trace

```bash
$ python boardly/di_bind.py
sig: (id: int, status: str = 'open', *tags, user, **extra) -> dict

--- sig.bind(42, 'open', 'api', 'bug', user='alice', board='x') ---
  type(bound):           BoundArguments
  bound.arguments:       {'id': 42, 'status': 'open', 'tags': ('api', 'bug'), 'user': 'alice', 'extra': {'board': 'x'}}
  bound.args:            (42, 'open', 'api', 'bug')
  bound.kwargs:          {'user': 'alice', 'board': 'x'}
  get_ticket(*a, **k):    {'id': 42, 'status': 'open', 'tags': ('api', 'bug'), 'user': 'alice', 'board': 'x'}

--- sig.bind(42, user='alice') — defaulted `status` omitted ---
  bound.arguments: {'id': 42, 'user': 'alice'}
  bound.args:      (42,)
  bound.kwargs:    {'user': 'alice'}
  result (no defaults applied): {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice'}

--- after apply_defaults() ---
  bound.arguments: {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice', 'extra': {}}
  bound.args:      (42, 'open')
  bound.kwargs:    {'user': 'alice'}

--- sig.bind(42) — missing required `user` ---
  TypeError: missing a required argument: 'user'

--- sig.bind_partial(42) — required `user` omitted, no error ---
  bp.arguments: {'id': 42}
  bp.args:      (42,)
  bp.kwargs:    {}
  after apply_defaults: {'id': 42, 'status': 'open', 'tags': (), 'extra': {}}
  get_ticket(*a, **k) raises: get_ticket() missing 1 required keyword-only argument: 'user'

--- call_with_deps(get_ticket, {'id': 42}, {'user': 'alice'}) ---
  result: {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice'}
```

## Common Mistakes

### Mistake 1: Calling `apply_defaults` before injecting dependencies

```python
bound = sig.bind_partial(**request_kwargs)
bound.apply_defaults()           # fills in `status` from default
bound.arguments["user"] = "alice"   # then inject
```

**Symptom:** Defaults are applied *first*, then dependencies overwrite. Seems fine — but if a parameter is *both* defaulted AND a dependency (`status: str = Depends(...)` — possible in FastAPI), the dependency value is correctly preferred. The bug is when the default is mutable: `def f(items: list = Depends(get_items))` — calling `apply_defaults` first would copy the *function's* default (an empty list) into `.arguments["items"]`, then your dependency injection writes over it. That works. The real bug surfaces when a parameter has `Parameter.empty` as default and *is* a dependency — `apply_defaults` does nothing for it (no default to copy), but if you inject *before* `apply_defaults`, you are safe; if you inject *after*, also safe. The ordering only matters when a parameter has *both* a default *and* a dependency override; the safe pattern is `bind → inject → apply_defaults`, which is what section 7 does.

**Why:** `apply_defaults` is idempotent — it never overwrites a value already in `.arguments`. So injecting before `apply_defaults` means your injection survives; injecting after also works because `apply_defaults` skips already-present keys. The danger is calling `apply_defaults` *between* two injects and assuming the second inject wins. That assumption is wrong — `apply_defaults` only fills absent keys.
**Fix:** Use the section-7 order: `bind_partial(request) → inject deps → apply_defaults → call`. That ordering is what FastAPI uses; it is robust to every kind default combination.

### Mistake 2: Treating `.arguments` as read-only

```python
bound = sig.bind_partial(**request_kwargs)
bound.arguments = {"new": "dict"}    # TypeError: cannot set attribute
```

**Symptom:** `AttributeError: 'BoundArguments' object has no attribute 'arguments'` (actually, you can read but not *replace* `.arguments`).
**Why:** `.arguments` is a property whose getter returns the underlying dict. You can mutate the dict (`bound.arguments["x"] = ...` works) but you cannot assign a new dict to `.arguments`. The underlying dict is the source of truth; replacing it would break the `args`/`kwargs` property's reference.
**Fix:** Mutate the dict in place: `bound.arguments["user"] = "alice"`. The `args` and `kwargs` properties recompute from the mutated dict on next access.

### Mistake 3: Forgetting that `apply_defaults` adds `()` and `{}` for variadic params

```python
def f(*args, **kwargs): pass
sig = inspect.signature(f)
bound = sig.bind()      # no args supplied
print(bound.arguments)  # {}
bound.apply_defaults()
print(bound.arguments)  # {'args': (), 'kwargs': {}}
```

**Symptom:** After `apply_defaults`, `*args` and `**kwargs` show up in `.arguments` with empty tuple/dict values, even though the function definition never wrote `= ()` or `= {}`.
**Why:** `apply_defaults` special-cases `VAR_POSITIONAL` and `VAR_KEYWORD` — they always have implicit empty-container defaults. This is the only case where the function's `Parameter.default` is `Parameter.empty` but `apply_defaults` still fills a value.
**Fix:** Expect the empty containers in `.arguments` after `apply_defaults`. Do not write `if name in bound.arguments` checks that assume `*args` will be absent when no positional args were supplied — it will be present as `()` after `apply_defaults`.

## Engineering Trade-Offs

**Decision:** Use `bind_partial` (not `bind`) when injecting dependencies — let `.arguments` mutation fill in the missing pieces, then `apply_defaults`, then call.
**Both sides:** The alternative is `bind` with the full pre-resolved argument set: resolve all dependencies first, then `bind(**request_data, **resolved_deps)`. That works, but it forces dependency resolution to happen *before* validation — you cannot reject a malformed request (e.g., extra kwarg) until after you have spent time resolving deps. `bind_partial` lets you validate the request shape first (rejecting extras), then resolve only the dependencies the request actually needs. The trade-off is two-pass clarity (partial-bind then inject) vs one-pass simplicity (full bind). FastAPI chose two-pass; the performance cost is negligible (one extra dict-merge) and the failure-fast property wins.
**Commitment:** `boardly` uses `bind_partial → inject → apply_defaults → call` exactly as in section 7. Lesson 06 wraps this in a `call_with_dependencies(endpoint)` function and adds the recursive `Depends` resolution that produces `resolved_deps` in the first place.

## Exercises

1. **Exercise 1 — Full bind and call.** Define `def get_ticket(id: int, status: str = "open", *, user, **extra): ...`, call `inspect.signature(get_ticket).bind(42, "open", user="alice", board="x")`, and confirm `bound.args == (42, "open")` and `bound.kwargs == {"user": "alice", "board": "x"}`. `Verify: python -c "import inspect; def f(id: int, status: str='open', *, user, **extra): pass; b=inspect.signature(f).bind(42, 'open', user='alice', board='x'); print(b.args, b.kwargs)"`
2. **Exercise 2 — `apply_defaults` adds empty containers.** On the same function, call `sig.bind_partial(42, user="alice")`, then `apply_defaults()`, and confirm `.arguments` has `'status': 'open'`, `'extra': {}` after the call. `Verify: python -c "import inspect; def f(id: int, status: str='open', *, user, **extra): pass; b=inspect.signature(f).bind_partial(42, user='alice'); b.apply_defaults(); print(sorted(b.arguments.items()))"`
3. **Exercise 3 — `bind` raises on missing required.** On the function from exercise 1, call `sig.bind(42)` and confirm it raises `TypeError: missing a required argument: 'user'`. `Verify: python -c "import inspect; def f(id: int, status: str='open', *, user, **extra): pass; 
try:
    inspect.signature(f).bind(42); print('no error')
except TypeError as e:
    print('TypeError:', e)"`
4. **Exercise 4 — `bind_partial` lets you skip required.** On the same function, call `sig.bind_partial(42)` and confirm it does NOT raise. Then mutate `bound.arguments["user"] = "alice"`, call `apply_defaults()`, and call `f(*bound.args, **bound.kwargs)` — confirm it succeeds. `Verify: python -c "import inspect; def f(id: int, status: str='open', *, user, **extra): return dict(id=id, status=status, user=user, extra=extra); b=inspect.signature(f).bind_partial(42); b.arguments['user']='alice'; b.apply_defaults(); print(f(*b.args, **b.kwargs))"`
5. **Exercise 5 — Implement `call_with_deps`.** Generalise section 7's `call_with_deps` to accept a `request_args` tuple as well as `request_kwargs` (mix positional and keyword request data). Bind via `bind_partial(*request_args, **request_kwargs)`, inject deps, apply defaults, call. Test on `def get_ticket(id, status='open', *tags, user, **extra):` with request data `(42, 'open', 'api')` and deps `{'user': 'alice'}`. `Verify: python -c "from boardly.di_bind import call_with_deps; def f(id, status='open', *tags, user, **extra): return (id, status, tags, user, extra); print(call_with_deps(f, (42, 'open', 'api'), {}, {'user':'alice'}))"`

## Verification

```bash
$ python boardly/di_bind.py | head -5
sig: (id: int, status: str = 'open', *tags, user, **extra) -> dict

--- sig.bind(42, 'open', 'api', 'bug', user='alice', board='x') ---
  type(bound):           BoundArguments
  bound.arguments:       {'id': 42, 'status': 'open', 'tags': ('api', 'bug'), 'user': 'alice', 'extra': {'board': 'x'}}
$ python boardly/di_bind.py | rg 'after apply_defaults'
  after apply_defaults: {'id': 42, 'status': 'open', 'tags': (), 'user': 'alice', 'extra': {}}
$ python -c "import inspect; def f(id: int, status: str='open', *, user, **extra): pass; b=inspect.signature(f).bind_partial(42); b.arguments['user']='alice'; b.apply_defaults(); print(dict(b.arguments))"
{'id': 42, 'status': 'open', 'user': 'alice', 'extra': {}}
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `Signature`, `Parameter`. This lesson is what you do with a `Signature`: `bind` against it.
- [[10-inspect/04-Parameter-kinds]] — the five `kind` values. `bind` routes incoming args to parameters based on their `kind`; without the kind model, you cannot predict `bound.args`/`bound.kwargs`.

## What's Next

[[10-inspect/06-How-FastAPI-uses-inspect]] — You can now `bind`, `bind_partial`, `apply_defaults`, and inject dependencies by mutating `.arguments`. Lesson 06 is the capstone: it combines `inspect.signature`, `typing.get_type_hints(..., include_extras=True)`, the `Annotated[T, Depends(...)]` metadata walk, and the `bind_partial → inject → call` flow into a single ~50-line re-implementation of FastAPI's dependency resolution. After lesson 06, you will know exactly what FastAPI does when it sees `Annotated[Session, Depends(get_session)]` in your route signature.

- **Lesson 06** — `Depends`, `solve_dependencies`, `call_with_dependencies`. The senior deep-dive.

## Sources

- **Python `inspect` module documentation — `inspect.Signature.bind`** — https://docs.python.org/3/library/inspect.html#inspect.Signature.bind — accessed 2026-10-23 — the canonical reference for `bind`, `bind_partial`, and the `TypeError` conditions on missing/extra args.
- **Python `inspect` module documentation — `inspect.BoundArguments`** — https://docs.python.org/3/library/inspect.html#inspect.BoundArguments — accessed 2026-10-23 — the canonical reference for `.arguments`, `.args`, `.kwargs`, and `apply_defaults()`.
- **PEP 362 — Function Signature Object** — https://peps.python.org/pep-0362/ — accessed 2026-10-23 — the PEP that introduced `Signature.bind` and `BoundArguments` in Python 3.3. Read the "BoundArguments" section for the rationale behind the `.arguments`-as-source-of-truth design.

## What We Learned

- You can now call `sig.bind(*args, **kwargs)` and read the resulting `BoundArguments` object.
- You can now explain `.arguments` (the canonical name→value dict), `.args`/`.kwargs` (computed views for `f(*a, **k)`), and `apply_defaults()` (fills absent defaulted params, including `()` and `{}` for variadic).
- You can now distinguish `bind` (raises on missing required) from `bind_partial` (lenient — used for partial application and dependency injection).
- You can now sketch FastAPI's bind-and-inject flow: `bind_partial(request) → mutate .arguments with resolved deps → apply_defaults → f(*bound.args, **bound.kwargs)`.
- You can now explain why `.arguments` is a mutable dict: so dependency resolution can fill in `Depends()`-marked parameters between binding and calling, without re-doing the bind.
