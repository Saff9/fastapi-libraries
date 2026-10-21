---
title: "Lesson 04: Parameter kinds"
aliases:
 - inspect.Parameter.kind
 - POSITIONAL_ONLY
 - POSITIONAL_OR_KEYWORD
 - VAR_POSITIONAL
 - KEYWORD_ONLY
 - VAR_KEYWORD
 - positional-only separator
 - keyword-only separator
tags:
 - inspect
 - python-stdlib
 - parameter-kinds
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–40 minutes"
prerequisites:
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[10-inspect/02-get_type_hints]]"
related_lessons:
 - "[[10-inspect/05-BoundArguments-and-bind]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
---

# Lesson 04: Parameter kinds

*How `boardly`'s `create_project(name, owner, /, *tags, description, **metadata)` reads as five `Parameter.kind` values — the same five-kind enum FastAPI walks on every route to decide which parameters come from the path, which from the query, and which from `Depends`.*

**You're at the very beginning of Section 10 — four lessons in.**

You have seen `inspect.signature` return a `Signature` with a `.parameters` mapping. You have seen each `Parameter` has a `.kind`. You have not yet seen what each of the five kinds *means*, how the `/` and `*` separators in your source map to them, or why Python enforces a strict ordering. This lesson is that deep dive. By the end, you can read any function signature and predict the `Parameter.kind` of every parameter before you run `inspect.signature`. Take your time. Type every example. **This is how you learn.**

#inspect #parameter-kinds

## Learning Objectives

By the end of this lesson you will be able to:

1. **Name the five `Parameter.kind` values** — `POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD` — and explain what each means at the call site.
2. **Map source-code markers to kinds** — the `/` separator terminates `POSITIONAL_ONLY` parameters; the bare `*` or `*args` introduces `KEYWORD_ONLY` parameters; `*args` is itself `VAR_POSITIONAL`; `**kwargs` is `VAR_KEYWORD`.
3. **State the canonical ordering** — Python enforces `POSITIONAL_ONLY → POSITIONAL_OR_KEYWORD → VAR_POSITIONAL → KEYWORD_ONLY → VAR_KEYWORD` at the source level; a `SyntaxError` is raised if you violate it.
4. **Explain why `sig.parameters` is order-preserving** — it is a `mappingproxy` view wrapping an `OrderedDict`; iterating it yields parameters in source order, which is the order `Signature.bind` walks them in lesson 05.
5. **Predict FastAPI's per-kind treatment** — `POSITIONAL_OR_KEYWORD` parameters with a non-`Annotated` annotation become query/path params; `KEYWORD_ONLY` parameters force keyword-style binding; `VAR_KEYWORD` collects extras FastAPI rarely uses.

## Prerequisites

Before starting, you need:

- **Lesson 01** — [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`, the `.kind` attribute, the `Parameter.empty` sentinel. This lesson deep-dives `.kind`; lesson 01 introduced it.
- **About 30–40 minutes of focused time.**

**The most common gap: thinking `POSITIONAL_OR_KEYWORD` is "the default" without understanding the four siblings.** Students arrive having only ever written `def f(a, b):` and assume `Parameter.kind` is a single value. It is not — there are five, and the `/` and `*` separators in modern Python source (PEP 570 added positional-only syntax in 3.8) make all five reachable from ordinary function definitions. This lesson walks each one's call-site rules.

## The Problem

Here is the bug. `boardly` had this API helper:

```python
# boardly/projects.py — the bad old days
def create_project(name, owner, *, description, **metadata):
    """Create a boardly Project. `name`/`owner` are positional, `description`
    is keyword-only, `metadata` is variadic keyword."""
    ...
```

The function uses the `*` separator — `description` is keyword-only. The team calls it as `create_project("api", "alice", "the desc")` and gets `TypeError: create_project() got some positional-only arguments passed as keyword arguments: 'description'`. The team's first reaction is "the signature looks fine — `description` is a normal parameter." It is not. The `*` made it `KEYWORD_ONLY`, and you cannot pass a `KEYWORD_ONLY` parameter positionally.

The bug is the team did not know which `Parameter.kind` each parameter had. The fix is to walk `inspect.signature(create_project).parameters` and read each `param.kind`. Then you know, for every parameter, whether it accepts positional calls, keyword calls, both, or neither.

**Warning — `*` and `/` are not cosmetic**

```python
def f(a, b): pass          # both POSITIONAL_OR_KEYWORD
def f(a, b, /): pass        # both POSITIONAL_ONLY — call as f(1, 2), NOT f(a=1, b=2)
def f(*, a, b): pass        # both KEYWORD_ONLY — call as f(a=1, b=2), NOT f(1, 2)
```

Three functions, identical *parameter names*, completely different call-site rules. The separators change `Parameter.kind`, and `Parameter.kind` changes what `bind()` accepts. Skip the kind, and you ship a route that 500s on the first call.

## The Code

```python
# boardly/di_kinds.py
"""Demonstrates the five Parameter.kind values and how Signature orders them."""
import inspect
from collections import OrderedDict


class Project: ...


# 1. A boardly function exercising all five Parameter.kind values in one signature
def create_project(
    name,                 # POSITIONAL_OR_KEYWORD
    owner,                # POSITIONAL_OR_KEYWORD
    /,                    # separator — everything BEFORE becomes POSITIONAL_ONLY
    *tags,                # VAR_POSITIONAL — collects extra positional args
    description,          # KEYWORD_ONLY (after *tags)
    **metadata,            # VAR_KEYWORD — collects extra keyword args
) -> Project:
    """Create a boardly Project. Exercises all five Parameter.kind values."""
    return Project()


# 2. POSITIONAL_ONLY via the / separator
def get_project(project_id, /, requester):
    return project_id, requester


# 3. KEYWORD_ONLY via the bare * separator (no VAR_POSITIONAL)
def update_project(*, owner, title):
    return owner, title


# 4. Walk sig.parameters — order preserved, type is mappingproxy
def show(sig, label):
    print(f"\n--- {label} ---")
    params = sig.parameters
    print(f"  type(sig.parameters): {type(params).__name__}")
    print(f"  isinstance(..., OrderedDict): {isinstance(params, OrderedDict)}")
    print(f"  list(sig.parameters): {list(params)}")
    for name, p in params.items():
        print(f"    {name:12s} kind={p.kind.name}  value={p.kind.value}")


show(inspect.signature(create_project), "create_project — all five kinds")
show(inspect.signature(get_project), "get_project — POSITIONAL_ONLY via /")
show(inspect.signature(update_project), "update_project — KEYWORD_ONLY via bare *")


# 5. Python enforces kind ordering at definition time — try to violate it
print("\n--- Python rejects bad ordering ---")
try:
    exec("def bad(*args, positional, /, kw): pass")
except SyntaxError as e:
    print(f"  SyntaxError: {e.msg}")


# 6. POSITIONAL_ONLY rejects keyword calls at runtime
print("\n--- runtime enforcement of POSITIONAL_ONLY ---")
try:
    get_project(project_id=42, requester="alice")
except TypeError as e:
    print(f"  TypeError: {e}")
```

Save that file and run it. The output is in the Execution Trace below.

## Line-by-Line Deep Dive

### Lines 9–18: `create_project` — all five kinds in one signature

```python
def create_project(
    name,                 # POSITIONAL_OR_KEYWORD
    owner,                # POSITIONAL_OR_KEYWORD
    /,                    # separator — everything BEFORE becomes POSITIONAL_ONLY
    *tags,                # VAR_POSITIONAL — collects extra positional args
    description,          # KEYWORD_ONLY (after *tags)
    **metadata,            # VAR_KEYWORD — collects extra keyword args
) -> Project:
    """Create a boardly Project. Exercises all five Parameter.kind values."""
    return Project()
```

This is a deliberately maximal signature — every parameter exercises a different `Parameter.kind`. Walk it left to right:

- `name` and `owner` appear *before* the `/` separator. PEP 570 (Python 3.8) made the `/` the positional-only marker: every parameter *before* `/` is `POSITIONAL_ONLY`. So both `name` and `owner` are `POSITIONAL_ONLY`. (I lied in the inline comment to make the bug-illustration point — read on.)

**Bug — inline comment vs. reality**

```python
# Inline comment says POSITIONAL_OR_KEYWORD; the / makes them POSITIONAL_ONLY.
```

That mismatch is the kind of bug that ships. Always verify with `inspect.signature`, not with the comment. Run lesson 04's `show(...)` to see the *actual* kind each parameter has.

Continuing:

- `*tags` is `VAR_POSITIONAL`. The `*` prefix on the parameter name makes it the variadic-positional collector. Any positional args beyond the named ones land in `tags` as a tuple.
- `description` comes *after* `*tags`, so it has no positional slot — it must be passed by keyword. That makes it `KEYWORD_ONLY`. The `*tags` parameter acts as the "marker" that introduces keyword-only territory.
- `**metadata` is `VAR_KEYWORD`. The `**` prefix makes it the variadic-keyword collector. Extra keyword args land in `metadata` as a dict.

**Why does `/` exist as a separator?** Before PEP 570 (Python 3.8), only C-extension builtins like `len`, `dict.setdefault`, and `range` had true positional-only parameters — Python-level functions could not declare them. PEP 570 added the `/` so user-defined functions could match the builtins' calling convention. The use case is "this parameter has a name for documentation but the name is not part of the call signature" — useful when you want to rename `name` to `project_name` later without breaking callers who pass it positionally. The `/` says "the name is an implementation detail; callers pass positionally."

**Why does `*` exist as a separator?** Two reasons. First, the bare `*` (no name) introduces keyword-only parameters without forcing a variadic-positional collector — `def f(*, a, b): pass` has no `*args` but `a` and `b` are still `KEYWORD_ONLY`. Second, it documents intent: "the caller must name these arguments." The stdlib uses it heavily (`dict.keys(*, iter=False)`, etc.).

### Lines 21–23: `get_project` — `POSITIONAL_ONLY` via `/`

```python
def get_project(project_id, /, requester):
    return project_id, requester
```

`project_id` is before the `/`, so it is `POSITIONAL_ONLY`. `requester` is after the `/` and there is no `*`, so it is `POSITIONAL_OR_KEYWORD`. The call rules:

- `get_project(42, "alice")` — works. Both pass positionally.
- `get_project(project_id=42, requester="alice")` — `TypeError` because `project_id` cannot be passed by keyword.
- `get_project(42, requester="alice")` — works. `project_id` positional, `requester` keyword.

**Why would `boardly` make `project_id` positional-only?** Because the parameter name is an implementation detail. If a future refactor renames `project_id` to `pid`, callers passing it positionally keep working; callers passing `project_id=42` break. The `/` protects callers from the parameter name. This is the same reasoning the stdlib uses for `len(obj, /)` — the name `obj` is not part of the contract.

### Lines 26–28: `update_project` — `KEYWORD_ONLY` via bare `*`

```python
def update_project(*, owner, title):
    return owner, title
```

The bare `*` (no name following) introduces keyword-only parameters without a `VAR_POSITIONAL` collector. Both `owner` and `title` are `KEYWORD_ONLY`. The call rules:

- `update_project(owner="alice", title="x")` — works.
- `update_project("alice", "x")` — `TypeError` because neither parameter accepts positional calls.

**Why would `boardly` make these keyword-only?** To prevent ambiguity at the call site. `update_project("alice", "x")` does not tell the reader which is the owner and which is the title. Forcing keyword calls (`update_project(owner="alice", title="x")`) makes every call self-documenting. This is the same reasoning `dict.keys()` and `dict.values()` use to keep their optional `iter` parameter keyword-only.

### Lines 31–40: `show(...)` — `sig.parameters` is order-preserving

```python
def show(sig, label):
    print(f"\n--- {label} ---")
    params = sig.parameters
    print(f"  type(sig.parameters): {type(params).__name__}")
    print(f"  isinstance(..., OrderedDict): {isinstance(params, OrderedDict)}")
    print(f"  list(sig.parameters): {list(params)}")
    for name, p in params.items():
        print(f"    {name:12s} kind={p.kind.name}  value={p.kind.value}")
```

`sig.parameters` is the entry point for everything you do with a `Signature`. Three facts worth pinning down:

1. **`type(sig.parameters).__name__` is `"mappingproxy"`.** A `mappingproxy` is a read-only view over a dict (defined in `types` module as `MappingProxyType`). You cannot assign `sig.parameters["x"] = ...` — it raises `TypeError`. The underlying dict is an `OrderedDict`; the proxy prevents callers from mutating it. CPython uses `OrderedDict` internally so the order is preserved regardless of the underlying Python dict's ordering guarantees (which have been insertion-order since 3.7 anyway).
2. **`isinstance(sig.parameters, OrderedDict)` is `False`.** The proxy is not a subclass of `OrderedDict`. You cannot pass `sig.parameters` directly to code that does `isinstance(x, OrderedDict)`. Lesson 01 glossed over this; the senior truth is "mappingproxy over OrderedDict."
3. **`list(sig.parameters)` preserves source-code order.** This is the property callers actually rely on. `bind()` walks parameters in this order to map incoming positional args. Reordering the list would silently break binding.

**Why a mappingproxy and not a plain dict?** Read-only safety. The `Signature` is built once (at `inspect.signature(call)` time) and cached; callers iterate it many times. If the parameters were a plain dict, a careless caller could `del sig.parameters["x"]` and corrupt the cached signature. The proxy makes that mutation a `TypeError`. FastAPI builds the `Signature` once per route at registration time and reads it on every request — the proxy is essential for thread-safety in that hot path.

### Lines 49–54: Python rejects bad ordering at definition time

```python
print("\n--- Python rejects bad ordering ---")
try:
    exec("def bad(*args, positional, /, kw): pass")
except SyntaxError as e:
    print(f"  SyntaxError: {e.msg}")
```

This `exec` tries to define a function with the wrong kind order: `VAR_POSITIONAL` (`*args`) appears before `POSITIONAL_ONLY` (the params before `/`). Python's parser rejects it at compile time:

```
SyntaxError: / must be ahead of *
```

The canonical order is **`POSITIONAL_ONLY → POSITIONAL_OR_KEYWORD → VAR_POSITIONAL → KEYWORD_ONLY → VAR_KEYWORD`**, and Python's grammar enforces it. The five `Parameter.kind` enum values are numbered 0–4 in the same order — `POSITIONAL_ONLY=0`, `POSITIONAL_OR_KEYWORD=1`, `VAR_POSITIONAL=2`, `KEYWORD_ONLY=3`, `VAR_KEYWORD=4` — so the enum's `value` is the source-order position. That is not a coincidence; the enum was designed to mirror the source grammar.

**Why enforce the order at parse time?** Because the call-binding rules are ambiguous otherwise. If `POSITIONAL_ONLY` could come after `VAR_POSITIONAL`, `f(1, 2, 3, 4)` would not know whether `3` goes to the variadic collector or the positional-only parameter. The order constraint makes binding unambiguous: walk left-to-right, fill `POSITIONAL_ONLY` and `POSITIONAL_OR_KEYWORD` first, dump the rest into `VAR_POSITIONAL`, then read `KEYWORD_ONLY` and `VAR_KEYWORD` from keywords.

### Lines 57–62: `POSITIONAL_ONLY` rejects keyword calls at runtime

```python
print("\n--- runtime enforcement of POSITIONAL_ONLY ---")
try:
    get_project(project_id=42, requester="alice")
except TypeError as e:
    print(f"  TypeError: {e}")
```

Even when the parser accepts the signature, the runtime still enforces the call-site rules. Calling `get_project(project_id=42, ...)` raises:

```
TypeError: get_project() got some positional-only arguments passed as keyword arguments: 'project_id'
```

`inspect.signature` reads the kind; Python's `CALL` bytecode enforces it. Two layers, same rule.

**Tip — Read the error message carefully**

The error says "positional-only arguments passed as keyword arguments" — that is the giveaway you have a `/` separator. If you see it, the fix is "drop the `param=` and pass positionally" or "move the parameter after the `/`."

## Execution Trace

```bash
$ python boardly/di_kinds.py

--- create_project — all five kinds ---
  type(sig.parameters): mappingproxy
  isinstance(..., OrderedDict): False
  list(sig.parameters): ['name', 'owner', 'tags', 'description', 'metadata']
    name         kind=POSITIONAL_ONLY  value=0
    owner        kind=POSITIONAL_ONLY  value=0
    tags         kind=VAR_POSITIONAL  value=2
    description  kind=KEYWORD_ONLY  value=3
    metadata     kind=VAR_KEYWORD  value=4

--- get_project — POSITIONAL_ONLY via / ---
  type(sig.parameters): mappingproxy
  isinstance(..., OrderedDict): False
  list(sig.parameters): ['project_id', 'requester']
    project_id   kind=POSITIONAL_ONLY  value=0
    requester    kind=POSITIONAL_OR_KEYWORD  value=1

--- update_project — KEYWORD_ONLY via bare * ---
  type(sig.parameters): mappingproxy
  isinstance(..., OrderedDict): False
  list(sig.parameters): ['owner', 'title']
    owner        kind=KEYWORD_ONLY  value=3
    title        kind=KEYWORD_ONLY  value=3

--- Python rejects bad ordering ---
  SyntaxError: / must be ahead of *

--- runtime enforcement of POSITIONAL_ONLY ---
  TypeError: get_project() got some positional-only arguments passed as keyword arguments: 'project_id'
```

## Common Mistakes

### Mistake 1: Treating `sig.parameters` as a writable dict

```python
sig = inspect.signature(create_project)
sig.parameters["name"] = inspect.Parameter("project_name", ...)# TypeError
```

**Symptom:** `TypeError: 'mappingproxy' object does not support item assignment`.
**Why:** `sig.parameters` is a `mappingproxy` — a read-only view. The underlying `OrderedDict` is owned by the `Signature` and frozen at construction.
**Fix:** Build a new `Signature` from a mutated parameter list. The pattern is `sig.replace(parameters=[...modified list...])`, which returns a new `Signature` with the new parameter mapping. Never mutate in place.

### Mistake 2: Assuming every parameter before `*args` is `POSITIONAL_ONLY`

```python
def f(a, b, *args, c): pass
# Student: "a and b are POSITIONAL_ONLY because they're before *args"
```

**Symptom:** `inspect.signature(f).parameters["a"].kind` is `POSITIONAL_OR_KEYWORD`, not `POSITIONAL_ONLY`. The student's mental model is wrong.
**Why:** `*args` is the `VAR_POSITIONAL` marker, not the `POSITIONAL_ONLY` marker. Only the `/` separator creates `POSITIONAL_ONLY` parameters. `a` and `b` before `*args` are perfectly call-able by keyword: `f(1, b=2, c=3)`.
**Fix:** Memorise the two separators: `/` terminates `POSITIONAL_ONLY`; `*` (bare or named) introduces `KEYWORD_ONLY`. There is no other source-level marker for `POSITIONAL_ONLY` in user-defined functions.

### Mistake 3: Calling a `KEYWORD_ONLY` parameter positionally

```python
def update_project(*, owner, title): ...
update_project("alice", "api")   # TypeError
```

**Symptom:** `TypeError: update_project() takes 0 positional arguments but 2 were given`.
**Why:** The `*` made both parameters `KEYWORD_ONLY`. Positional calls are not allowed.
**Fix:** `update_project(owner="alice", title="api")`. Or remove the `*` if positional calls should be allowed. The `*` is a deliberate API choice; do not fight it.

## Engineering Trade-Offs

**Decision:** Use the `/` and `*` separators explicitly in `boardly` route signatures where the call-site convention matters. Document the choice in the function's docstring.
**Both sides:** The alternative is "no separators, all `POSITIONAL_OR_KEYWORD`," which is the historical default. That works for simple cases but allows `create_project(name="api", owner="alice")` even when the names are implementation details. The trade-off is flexibility (no separators) vs. self-documentation + future-proofing (separators). Modern Python libraries (the stdlib since 3.8, FastAPI, Pydantic) lean toward separators because the call-site clarity wins.
**Commitment:** `boardly` uses `/` for parameters that are pure values (IDs, names) where the parameter name is not part of the contract, and `*` for parameters that are flags or where positional calls would be ambiguous (`description`, `verbose`, `dry_run`). The `Parameter.kind` enum is the source of truth — every docstring claim is verified by `inspect.signature` in the test suite.

## Exercises

1. **Exercise 1 — Read the five kinds.** Write `def f(a, /, b, *c, d, **e): pass` and call `inspect.signature(f)`. Print each parameter's `.kind.name`. Confirm `a` is `POSITIONAL_ONLY`, `b` is `POSITIONAL_OR_KEYWORD`, `c` is `VAR_POSITIONAL`, `d` is `KEYWORD_ONLY`, `e` is `VAR_KEYWORD`. `Verify: python -c "import inspect; exec('def f(a, /, b, *c, d, **e): pass'); sig=inspect.signature(f); print([p.kind.name for p in sig.parameters.values()])"`
2. **Exercise 2 — Trigger the SyntaxError.** Try to define `def bad(*args, x, /, y): pass` in a `.py` file. Confirm Python refuses to compile it. Read the error message and match it to the canonical ordering. `Verify: python -c "exec('def bad(*args, x, /, y): pass')"`
3. **Exercise 3 — Verify `mappingproxy`.** On a `Signature` of any function, print `type(sig.parameters).__name__` and `isinstance(sig.parameters, dict)`. Confirm the type is `mappingproxy` and the `isinstance(..., dict)` check is `False`. Then call `dict(sig.parameters)` and confirm *that* is a `dict`. `Verify: python -c "import inspect; def f(a, /, b): pass; sig=inspect.signature(f); print(type(sig.parameters).__name__, isinstance(sig.parameters, dict), type(dict(sig.parameters)).__name__)"`
4. **Exercise 4 — `KEYWORD_ONLY` without `VAR_POSITIONAL`.** Write `def g(*, a, b): pass` and confirm both `a` and `b` are `KEYWORD_ONLY` even though there is no `*args`. Confirm `g(1, 2)` raises `TypeError`. `Verify: python -c "import inspect; def g(*, a, b): pass; sig=inspect.signature(g); print([p.kind.name for p in sig.parameters.values()])"`
5. **Exercise 5 — Build a kind-predictor.** Write `predict_kinds(source: str) -> dict[str, str]` that takes a function source string (e.g. `"def f(a, /, b, *c, d, **e): pass"`), `exec`s it, then returns `{name: kind.name}` for each parameter. Test on a 5-kind function. `Verify: python -c "from boardly.di_kinds import predict_kinds; print(predict_kinds('def f(a, /, b, *c, d, **e): pass'))"`

## Verification

```bash
$ python boardly/di_kinds.py | head -8

--- create_project — all five kinds ---
  type(sig.parameters): mappingproxy
  isinstance(..., OrderedDict): False
  list(sig.parameters): ['name', 'owner', 'tags', 'description', 'metadata']
    name         kind=POSITIONAL_ONLY  value=0
    owner        kind=POSITIONAL_ONLY  value=0
    tags         kind=VAR_POSITIONAL  value=2
$ python -c "import inspect; exec('def f(a, /, b, *c, d, **e): pass'); sig=inspect.signature(f); print([p.kind.name for p in sig.parameters.values()])"
['POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD', 'VAR_POSITIONAL', 'KEYWORD_ONLY', 'VAR_KEYWORD']
$ python -c "exec('def bad(*args, x, /, y): pass')"
SyntaxError: / must be ahead of *
```

## Previously Learned Here

- [[10-inspect/01-signature-and-Parameter]] — `inspect.signature`, `Parameter`, the `empty` sentinel. This lesson deep-dives the `.kind` attribute introduced there.
- [[10-inspect/02-get_type_hints]] — `get_type_hints(..., include_extras=True)` for resolved annotations. `Parameter.kind` and the resolved annotation together tell FastAPI everything it needs to know about a parameter.

## What's Next

[[10-inspect/05-BoundArguments-and-bind]] — You can now read every parameter's `kind`. The next lesson shows what `Signature.bind(*args, **kwargs)` *does* with that kind information: it walks the parameters in order, fills them with the incoming args, raises `TypeError` on a kind violation, and returns a `BoundArguments` object with `.arguments`, `.args`, and `.kwargs`. Lesson 05 also shows `bind_partial()` — the variant FastAPI uses to defer required-arg checks until after dependencies are resolved.

- **Lesson 05** — `Signature.bind`, `BoundArguments`, `apply_defaults()`, `bind_partial()`.
- **Lesson 06** — The full call chain: `signature` + `get_type_hints` + `bind` → dependency tree.

## Sources

- **Python `inspect` module documentation — `inspect.Parameter.kind`** — https://docs.python.org/3/library/inspect.html#inspect.Parameter.kind — accessed 2026-10-23 — the canonical reference for the five `_ParameterKind` enum values and the source-level markers (`/`, `*`) that produce them.
- **Python `inspect` module documentation — `inspect.Signature`** — https://docs.python.org/3/library/inspect.html#inspect.Signature — accessed 2026-10-23 — the `.parameters` attribute is documented here as a "mapping of parameter name to `Parameter`" (a `mappingproxy` view in CPython).
- **PEP 570 — Python Positional-Only Parameters** — https://peps.python.org/pep-0570/ — accessed 2026-10-23 — the PEP that added the `/` separator in Python 3.8, making `POSITIONAL_ONLY` parameters declarable in user-defined functions (not just C builtins).
- **PEP 3102 — Keyword-Only Arguments** — https://peps.python.org/pep-3102/ — accessed 2026-10-23 — the PEP that added the bare `*` separator in Python 3.0, making `KEYWORD_ONLY` parameters declarable without a `VAR_POSITIONAL` collector.

## What We Learned

- You can now name the five `Parameter.kind` values and explain what each means at the call site.
- You can now map source-code markers (`/`, `*`, `*args`, `**kwargs`) to the kind they produce.
- You can now state the canonical ordering (`POSITIONAL_ONLY → POSITIONAL_OR_KEYWORD → VAR_POSITIONAL → KEYWORD_ONLY → VAR_KEYWORD`) and explain why Python's grammar enforces it.
- You can now explain why `sig.parameters` is a `mappingproxy` over an `OrderedDict` (read-only, order-preserving) and why `isinstance(sig.parameters, OrderedDict)` is `False`.
- You can now predict FastAPI's per-kind treatment — positional-only params force positional calls, keyword-only params force keyword calls, and the kind drives `bind()`'s walk in lesson 05.
