---
title: "Lesson 02: SimpleNamespace"
aliases:
 - SimpleNamespace
 - types.SimpleNamespace
 - namespace
tags:
 - types
 - simplenamespace
 - configuration
status: complete
course_level: beginner
difficulty: beginner
estimated_time: "15–25 minutes"
prerequisites:
 - "[[12-types/01-NewType]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[12-types/01-NewType]]"
 - "[[12-types/03-GenericAlias-and-UnionType]]"
 - "[[06-dataclasses/01-dataclass-Basics]]"
 - "[[04-collections/04-namedtuple]]"
---

# Lesson 02: SimpleNamespace

*`SimpleNamespace(host="0.0.0.0", port=8000)` — the one-line "I have a dict and I want dot-access" tool, with the `**kwargs` unpacking pattern and the boundary that decides when `@dataclass` should win instead.*

**You're at the very beginning of Section 12 — and `SimpleNamespace` is the simplest tool in the box.**

`types.SimpleNamespace` is what you reach for when you need a *throwaway* object with a handful of attributes — a config prototype, a test fixture, a JSON payload you want to inspect with `cfg.host` rather than `cfg["host"]`. It is mutable. It has no type hints. It has no validation. It has a useful `__repr__` and a value-based `__eq__`. It is the right tool for "this is not a model, it is a bag". By the end of this lesson you will know when to reach for it, when to reach for `@dataclass` instead, and why both have a place. Take your time. Type every example. **This is how you learn.**

#types #simplenamespace #configuration

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct** a `SimpleNamespace` from kwargs — `SimpleNamespace(host="0.0.0.0", port=8000)` — and access its fields as `cfg.host`.
2. **Use** the `**kwargs` unpacking pattern — `SimpleNamespace(**some_dict)` — to turn a dict into a namespace in one call.
3. **Read** the `__repr__` (`namespace(a=1, b=2)`) and the `__eq__` (compares attribute names and values) — and predict what equality comparison produces.
4. **Decide** when `SimpleNamespace` wins (ad-hoc attribute bags, test fixtures, dynamic JSON) versus when `@dataclass` wins (typed models, validation, immutability, IDE completion).
5. **Diagnose** the typo-trap: a typo creates a *new* attribute silently — `cfg.tite = "..."` instead of `cfg.title = "..."` does not raise.

## Prerequisites

Before starting, you need:

- **The `NewType` lesson** — [[12-types/01-NewType]] covers the same "static-only concept" framing from the typing side; `SimpleNamespace` is the runtime-only counterpart that ignores types entirely.
- **The `@dataclass` basics lesson** — [[06-dataclasses/01-dataclass-Basics]] covers the canonical *typed* alternative; this lesson cross-references it constantly.
- **About 15–25 minutes of focused time.**

**The most common gap: reaching for `SimpleNamespace` when you need a model.**

Students arrive having read that `SimpleNamespace` is "a quick alternative to dataclass". They reach for it whenever they want a typed object quickly. That is the wrong use — `SimpleNamespace` is *untyped*, has no validation, no immutability, no IDE completion, and silently accepts typos. If you need *any* of those things, `@dataclass` is the right tool. `SimpleNamespace` wins only when the set of attributes is not known at write-time — when you are loading JSON of unknown shape, when you are building a test fixture where the type system would just get in the way, or when you are sketching a config prototype you will throw away in an hour. The boundary is the whole lesson.

## The Problem

Here is the bug. `boardly` has an environment config that arrives as a `dict`:

```python
# boardly/config.py — the bad old days
env = {
    "DATABASE_URL": "postgres://localhost/boardly",
    "REDIS_URL": "redis://localhost:6379",
    "DEBUG": "true",
}

# Every call site writes this:
def connect(env):
    db_url = env["DATABASE_URL"]
    redis_url = env["REDIS_URL"]
    if env["DEBUG"] == "true":
        ...
```

Three problems. (1) Every access is a string-typed dictionary lookup — `env["DATABASE_URL"]` — which is noisy and slow. (2) A typo (`env["DATABASE_URL "]` with a trailing space) raises `KeyError` at runtime instead of being caught at write-time. (3) The call site has no IDE completion — the editor does not know which keys exist. The temptation is to write a `@dataclass` for `env`, but the data comes from a JSON file or environment variables; you do not know all the keys at write-time, and adding a new env var should not require editing a class definition.

`SimpleNamespace` is the standard-library answer:

```python
from types import SimpleNamespace
env_ns = SimpleNamespace(**env)
print(env_ns.DATABASE_URL)         # 'postgres://localhost/boardly'
print(env_ns.REDIS_URL)            # 'redis://localhost:6379'
print(repr(env_ns))                # namespace(DATABASE_URL='...', REDIS_URL='...', DEBUG='true')
```

The dict becomes a namespace in one call. Attribute access replaces dict access. The `__repr__` shows every attribute. No class definition required, no type annotations required, no `__init__` boilerplate. For "I have data of unknown shape and I want to walk it with dots", this is the right tool.

## The Code

```python
# boardly/runtime/config_ns.py
"""boardly — SimpleNamespace for ad-hoc attribute bags (config prototypes, test fixtures)."""
from types import SimpleNamespace
from dataclasses import dataclass

# 1. Construct from kwargs — instant attribute bag.
cfg = SimpleNamespace(host="0.0.0.0", port=8000, debug=True)
print("cfg:", repr(cfg))
print("cfg.host:", cfg.host, "cfg.port:", cfg.port)

# 2. Mutable — set any attribute after construction.
cfg.tls_cert = "/etc/boardly/tls.pem"  # new attribute
cfg.debug = False                       # overwrite existing
print("after mutation:", repr(cfg))

# 3. The **kwargs unpacking pattern — turn a dict into a namespace.
env = {"DATABASE_URL": "postgres://localhost/boardly", "REDIS_URL": "redis://localhost:6379"}
env_ns = SimpleNamespace(**env)
print("\nenv_ns:", repr(env_ns))
print("env_ns.DATABASE_URL:", env_ns.DATABASE_URL)

# 4. The repr is informative — every attribute listed.
print("\nrepr(cfg):", repr(cfg))

# 5. No validation, no type hints, but value-based equality is defined.
a = SimpleNamespace(x=1)
b = SimpleNamespace(x=1)
print("\na == b:", a == b)  # True — same attrs same values
print("a is b:", a is b)    # False — different objects

# 6. The boundary — when SimpleNamespace loses to @dataclass.
@dataclass
class ProjectConfig:
    host: str
    port: int
    debug: bool = False

cfg2 = ProjectConfig(host="0.0.0.0", port=8000)
print("\ncfg2:", repr(cfg2))

# 7. SimpleNamespace's one great superpower: arbitrary attribute set is the *point*.
import json
raw = json.loads('{"title": "demo", "owner": "ada", "labels": ["bug", "ui"], "estimate": 5}')
ticket_ns = SimpleNamespace(**raw)
print("\nticket_ns.title:", ticket_ns.title)
print("ticket_ns.labels:", ticket_ns.labels)
print("ticket_ns:", repr(ticket_ns))

# 8. Compare attribute access patterns: dict vs SimpleNamespace vs dataclass.
print("\n--- attribute access patterns ---")
print("dict access:   raw['title']    ->", raw["title"])
print("namespace:     ticket_ns.title ->", ticket_ns.title)
print("dataclass:     cfg2.host       ->", cfg2.host)

# 9. The danger: typos silently create new attributes instead of failing.
ticket_ns.tite = "typo!"  # silent
print("\nAfter typo attribute set:", repr(ticket_ns))
```

## Line-by-Line Deep Dive

### Lines 1–6: Module header and the canonical construction

```python
# boardly/runtime/config_ns.py
"""boardly — SimpleNamespace for ad-hoc attribute bags (config prototypes, test fixtures)."""
from types import SimpleNamespace
from dataclasses import dataclass

# 1. Construct from kwargs — instant attribute bag.
cfg = SimpleNamespace(host="0.0.0.0", port=8000, debug=True)
```

`SimpleNamespace(host=..., port=..., debug=...)` accepts arbitrary keyword arguments and stores them as attributes on a new `SimpleNamespace` instance. The implementation is essentially `self.__dict__.update(kwargs)` — every keyword you pass becomes a `self.<keyword>`. There is no class definition, no `__init__` signature, no type checking, no validation. The three arguments `host`, `port`, `debug` become `cfg.host`, `cfg.port`, `cfg.debug`. Access is C-accelerated attribute lookup; the dict that backs it is the instance's `__dict__`.

**Why is `SimpleNamespace` defined in `types` and not in `collections` or `typing`?**

Because it is a *runtime type* — `types` is the standard-library home for the runtime type objects Python itself is built from. `SimpleNamespace` is a *class* you instantiate; the `types` module is where you go to find the classes that back every common Python construct (`ModuleType` for modules, `FunctionType` for functions, `MappingProxyType` for read-only dict views). `collections` is for *data structures* (`Counter`, `defaultdict`, `OrderedDict`) and `typing` is for *static-only constructs* (`TypeVar`, `Annotated`, `NewType` — see lesson 01). `SimpleNamespace` fits in `types` because it is the runtime class behind "an object with arbitrary attributes" — exactly the same category as `ModuleType` (a module *is* a namespace, after all).

### Lines 8–11: Mutability — the whole point

```python
# 2. Mutable — set any attribute after construction.
cfg.tls_cert = "/etc/boardly/tls.pem"  # new attribute
cfg.debug = False                       # overwrite existing
print("after mutation:", repr(cfg))
```

`cfg.tls_cert = ...` *creates* a new attribute; `cfg.debug = False` *overwrites* an existing one. There is no `__setattr__` intercept; there is no validation; there is no "this attribute was not declared" error. `SimpleNamespace` is just a thin wrapper around `object.__dict__`. The mutability is the *point* — if your attributes are not known at write-time (which is the only reason to reach for `SimpleNamespace` over `@dataclass`), you need to be able to add them after construction. The cost is that the type-checker (mypy, pyright) treats a `SimpleNamespace` instance as essentially `Any` for attribute access — there is nothing to check.

### Lines 13–17: The `**kwargs` unpacking pattern

```python
# 3. The **kwargs unpacking pattern — turn a dict into a namespace.
env = {"DATABASE_URL": "postgres://localhost/boardly", "REDIS_URL": "redis://localhost:6379"}
env_ns = SimpleNamespace(**env)
print("\nenv_ns:", repr(env_ns))
print("env_ns.DATABASE_URL:", env_ns.DATABASE_URL)
```

`SimpleNamespace(**env)` is the canonical dict-to-namespace call. The `**env` unpacks the dict's keys and values as keyword arguments — exactly the same mechanism Python uses to forward `**kwargs` to another function. Three things to know. (1) The dict's *keys* must be valid Python identifiers (`DATABASE_URL` is fine; `"database-url"` is not — `SimpleNamespace(**{"database-url": "x"})` raises `TypeError: SimpleNamespace() got an unexpected keyword argument 'database-url'`). (2) The keys become attribute names — case-sensitive, no normalisation. (3) The result is a `SimpleNamespace` whose `__repr__` is `namespace(DATABASE_URL='...', REDIS_URL='...')` — every key visible, in the order they appear in the dict.

**Why does Python reject hyphenated keys in `**kwargs` unpacking?**

Because `**dict` unpacking maps each key to a *keyword argument*, and Python's keyword-argument syntax is `name=value` where `name` is an identifier. `"database-url"` is not a legal identifier (the hyphen is the subtraction operator), so Python rejects it at the syntax layer. The fix is to either rename the dict's keys to valid identifiers (`"database_url"`) before unpacking, or to access the hyphenated key via `getattr(env_ns, "database-url")` after construction (which is legal because attribute *storage* accepts any string, even though attribute *syntax* does not). For environment variables, the standard pattern is to lower-case and replace separators — `os.environ["DATABASE_URL"]` becomes `env_ns.database_url` via a small renaming step.

### Lines 19–20: The `__repr__` lists every attribute

```python
# 4. The repr is informative — every attribute listed.
print("\nrepr(cfg):", repr(cfg))
```

`repr(cfg)` returns `namespace(host='0.0.0.0', port=8000, debug=False, tls_cert='/etc/boardly/tls.pem')`. Every attribute, in insertion order (Python 3.7+ dicts and `__dict__` are ordered), with each value's `repr`. This is one of `SimpleNamespace`'s best features: the default `__repr__` is *useful*. By contrast, a plain `object()` instance has `__repr__ = <object object at 0x...>` — useless for debugging. `SimpleNamespace` gives you a usable debug print for free. This is why it is so common in test fixtures — every assertion failure shows you the entire state of the namespace.

### Lines 22–26: Equality is value-based

```python
# 5. No validation, no type hints, but value-based equality is defined.
a = SimpleNamespace(x=1)
b = SimpleNamespace(x=1)
print("\na == b:", a == b)  # True — same attrs same values
print("a is b:", a is b)    # False — different objects
```

`SimpleNamespace.__eq__` compares the `__dict__` of two namespaces: same attribute names, same values, same order. `a == b` is `True` here. `a is b` is `False` because they are different objects. This is the same shape as `dict.__eq__`, and it is one of the things that makes `SimpleNamespace` *not* the right tool for production models — equality is purely structural, not semantic. Two `SimpleNamespace(x=1)` objects are equal even if one was meant to represent a `Project` and the other a `User`. There is no `__hash__` defined (the class is mutable, so hashing would be unsafe), so you cannot put a `SimpleNamespace` in a set or use it as a dict key. If you need equality *and* hashing, reach for `@dataclass(frozen=True)` instead.

### Lines 28–35: The boundary with `@dataclass`

```python
# 6. The boundary — when SimpleNamespace loses to @dataclass.
@dataclass
class ProjectConfig:
    host: str
    port: int
    debug: bool = False

cfg2 = ProjectConfig(host="0.0.0.0", port=8000)
print("\ncfg2:", repr(cfg2))
```

`ProjectConfig(host=..., port=..., debug=False)` looks similar to `SimpleNamespace(host=..., port=..., debug=...)` from the call site — both produce an object with `.host`, `.port`, `.debug`. But they are categorically different. (1) `ProjectConfig` has *type hints* — `port: int` — which mypy enforces at the call site (`ProjectConfig(port="not-an-int")` is a mypy error; at runtime it is also accepted, but the type-checker catches it). (2) `ProjectConfig` *rejects unknown attributes* — `cfg2.tls_cert = "/etc/..."` works at runtime (Python does not prevent it without `__slots__`), but mypy will flag it as `error: "ProjectConfig" has no attribute "tls_cert"`. Lesson [[06-dataclasses/04-Slots-and-Performance]] covers `slots=True` which makes runtime assignment of an unknown attribute raise `AttributeError`. (3) `ProjectConfig` has a *stable* `__init__` signature — adding a new field is a change to the constructor signature, which is a deliberate decision the type-checker surfaces. `SimpleNamespace` accepts anything.

**Why does `@dataclass` not *enforce* type hints at runtime?**

Because `@dataclass` is a class decorator that runs at import time and generates an `__init__` method; it does not generate validation logic. The `port: int` annotation is *metadata* — it is stored in `__annotations__` and read by mypy, but the generated `__init__` is `def __init__(self, host: str, port: int, debug: bool = False): self.host = host; self.port = port; self.debug = debug`. No `isinstance` check. Runtime validation is a separate concern, addressed by Pydantic (which *does* generate validation) or by a hand-written `__post_init__` (lesson [[06-dataclasses/01-dataclass-Basics]]). The Python type system is static-first by design — same as `NewType`.

### Lines 37–43: The "unknown shape" superpower

```python
# 7. SimpleNamespace's one great superpower: arbitrary attribute set is the *point*.
import json
raw = json.loads('{"title": "demo", "owner": "ada", "labels": ["bug", "ui"], "estimate": 5}')
ticket_ns = SimpleNamespace(**raw)
print("\nticket_ns.title:", ticket_ns.title)
print("ticket_ns.labels:", ticket_ns.labels)
print("ticket_ns:", repr(ticket_ns))
```

This is the case where `SimpleNamespace` wins outright. The JSON has five keys (`title`, `owner`, `labels`, `estimate` and one more) — but you do not know which keys a *different* ticket might have. A ticket from production might have `assignee`, `due_date`, `priority`. A ticket from the legacy API might have `state`, `touched_at`. Writing a `@dataclass` for every variant is impossible; writing one `@dataclass` with all fields is a maintenance nightmare. `SimpleNamespace(**raw)` handles every variant — the keys become attributes, the values are whatever the JSON contained, the `__repr__` shows you what you actually got. The price is no validation (a malformed `labels` value silently passes through) and no IDE completion — but you are *introspecting unknown data*, which is exactly when those costs are acceptable.

### Lines 45–50: The three access patterns side by side

```python
# 8. Compare attribute access patterns: dict vs SimpleNamespace vs dataclass.
print("\n--- attribute access patterns ---")
print("dict access:   raw['title']    ->", raw["title"])
print("namespace:     ticket_ns.title ->", ticket_ns.title)
print("dataclass:     cfg2.host       ->", cfg2.host)
```

Three syntactic styles for the same operation: read a value off an object. `raw["title"]` is dict-access (works for any `Mapping`); `ticket_ns.title` is attribute access on a `SimpleNamespace`; `cfg2.host` is attribute access on a `@dataclass` instance. The dict version is the most flexible (any hashable key works, including non-identifier strings); the dataclass version is the most type-safe (mypy knows `cfg2.host: str`); the namespace version sits in between (any identifier attribute works, no type information). The choice is rarely about *syntax* — all three read fine — but about *what you want to enforce*: nothing (dict), structure (namespace), or structure-plus-types (dataclass).

### Lines 52–54: The typo trap

```python
# 9. The danger: typos silently create new attributes instead of failing.
ticket_ns.tite = "typo!"  # silent
print("\nAfter typo attribute set:", repr(ticket_ns))
```

`ticket_ns.tite = "typo!"` *succeeds*. It creates a new attribute `tite` alongside `title`. There is no error. The `__repr__` afterwards shows both: `namespace(title='demo', owner='ada', labels=['bug', 'ui'], estimate=5, tite='typo!')`. This is the most common `SimpleNamespace` bug — a typo at the assignment site creates a second, never-read attribute, and the intended attribute retains its old value. The fix is `@dataclass(slots=True)` (lesson [[06-dataclasses/04-Slots-and-Performance]]) which raises `AttributeError` on unknown attribute assignment, or a custom `__setattr__` that validates names against a known set. For `SimpleNamespace`, the only defence is discipline and code review.

**Why does CPython not provide a "strict" namespace that rejects unknown attributes?**

Because the standard library's job is to provide primitives, not opinions. `SimpleNamespace` is the *primitive* — a dict-backed attribute bag. `@dataclass(slots=True)` is the *opinionated* layer on top — it generates a class with `__slots__`, which makes attribute storage a fixed tuple instead of a dict, and unknown-attribute assignment a runtime error. The two compose: you can write your own `StrictNamespace` subclass that intercepts `__setattr__` and rejects unknown names, but the standard library does not ship one because the right validation rules differ for every use case (allow-after-init? allow-listed names? type-check values?). The standard library ships the primitive; the framework (Pydantic, attrs, your own dataclass) ships the opinion.

## Execution Trace

```bash
$ python boardly/runtime/config_ns.py
cfg: namespace(host='0.0.0.0', port=8000, debug=True)
cfg.host: 0.0.0.0 cfg.port: 8000
after mutation: namespace(host='0.0.0.0', port=8000, debug=False, tls_cert='/etc/boardly/tls.pem')

env_ns: namespace(DATABASE_URL='postgres://localhost/boardly', REDIS_URL='redis://localhost:6379')
env_ns.DATABASE_URL: postgres://localhost/boardly

repr(cfg): namespace(host='0.0.0.0', port=8000, debug=False, tls_cert='/etc/boardly/tls.pem')

a == b: True
a is b: False

cfg2: ProjectConfig(host='0.0.0.0', port=8000, debug=False)

ticket_ns.title: demo
ticket_ns.labels: ['bug', 'ui']
ticket_ns: namespace(title='demo', owner='ada', labels=['bug', 'ui'], estimate=5)

--- attribute access patterns ---
dict access:   raw['title']    -> demo
namespace:     ticket_ns.title -> demo
dataclass:     cfg2.host       -> 0.0.0.0

After typo attribute set: namespace(title='demo', owner='ada', labels=['bug', 'ui'], estimate=5, tite='typo!')
```

Three things to verify in this trace. First, the `__repr__` after mutation shows the new attribute `tls_cert` appended and `debug` overwritten to `False` — `__dict__` ordering is preserved. Second, `a == b` is `True` for two distinct `SimpleNamespace(x=1)` objects — value-based equality. Third, the typo trap: `tite='typo!'` appears alongside `title='demo'` — the typo did not raise; it silently created a new attribute.

## Common Mistakes

### Mistake 1: Using `SimpleNamespace` where you need a model

```python
# boardly/models/user.py — wrong tool
from types import SimpleNamespace
class User(SimpleNamespace):  # ← inherits SimpleNamespace's mutable, untyped behaviour
    pass

u = User(id=1, name="Ada")
u.id = "oops-a-string"  # silent
u.tite = "typo"          # silent
```

**Symptom:** Production data goes bad silently — a typo creates a new attribute, a type mismatch is not caught, equality is purely structural.
**Why:** `SimpleNamespace` is a runtime-only attribute bag. It has no type hints, no validation, no immutability, no `__slots__`. Inheriting it for a *model* loses every guarantee a model is supposed to provide.
**Fix:** Use `@dataclass` for models (lesson [[06-dataclasses/01-dataclass-Basics]]). Use `SimpleNamespace` for ad-hoc attribute bags (test fixtures, config prototypes, JSON introspection) where the attributes are not known at write-time.

### Mistake 2: Hyphenated keys in the `**dict` unpacking

```python
env = {"database-url": "postgres://..."}
env_ns = SimpleNamespace(**env)  # TypeError
```

**Symptom:** `TypeError: SimpleNamespace() got an unexpected keyword argument 'database-url'` at construction time.
**Why:** `**dict` unpacking maps each key to a keyword argument, and Python's keyword-argument syntax requires the key to be a legal identifier. `"database-url"` is not (hyphen is the subtraction operator).
**Fix:** Rename keys to valid identifiers before unpacking: `env_clean = {k.replace("-", "_"): v for k, v in env.items()}; env_ns = SimpleNamespace(**env_clean)`. Or access the value via `getattr(env_ns, "database-url")` after construction — attribute *storage* accepts any string, even though attribute *syntax* does not.

### Mistake 3: Using `SimpleNamespace` as a dict key or set member

```python
ns = SimpleNamespace(x=1)
d = {ns: "value"}  # TypeError: unhashable type: 'types.SimpleNamespace'
```

**Symptom:** `TypeError: unhashable type: 'types.SimpleNamespace'` at the dict-construction site.
**Why:** `SimpleNamespace` is mutable, so it does not define `__hash__` — Python's rule is "mutable objects are not hashable" because their hash could change after they are inserted into a set or dict, breaking the data structure's invariants. The error string uses the full dotted name `'types.SimpleNamespace'` (not just `'SimpleNamespace'`), so write your test against the full string if you assert on the exception.
**Fix:** Use `@dataclass(frozen=True)` instead — frozen dataclasses are immutable and define `__hash__` (lesson [[06-dataclasses/03-Frozen-and-Immutability]]). If you genuinely need a hashable namespace, write a `namedtuple` (lesson [[04-collections/04-namedtuple]]) — they are immutable and hashable by default.

## Engineering Trade-Offs

**Decision:** Use `SimpleNamespace` only for ad-hoc attribute bags (test fixtures, config prototypes, JSON introspection of unknown shape); use `@dataclass` for every *model* the codebase persists or serialises.
**Both sides:** The alternative is to use `@dataclass` everywhere, including for ad-hoc bags. The cost is boilerplate — every test fixture and every config prototype requires a class definition, type annotations, and a constructor call. The benefit is type safety, IDE completion, and immutability if you opt in. The trade is real: for a test fixture that exists for one test and is then deleted, the type safety buys you nothing because the test itself is the verification; for a model that crosses a serialisation boundary (Pydantic, FastAPI, the database), the type safety is the only thing standing between you and a class of bugs you cannot reproduce locally.
**Commitment:** boardly uses `SimpleNamespace` in three places: (a) test fixtures (`SimpleNamespace(id=1, name="Ada")` for a `User` stand-in that does not need validation), (b) config prototypes during local development (`SimpleNamespace(debug=True, tls_cert="/tmp/test.pem")` to sketch a config), and (c) JSON introspection of unknown-shape webhooks (`SimpleNamespace(**webhook_payload)` so we can walk the payload with attribute access). Every persisted model is a `@dataclass` or a Pydantic model — never a `SimpleNamespace`. The boundary is enforced in code review.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/runtime/config_ns.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/runtime/config_ns.py`
2. **Exercise 2 — Add an attribute after construction.** Add `cfg.feature_flag_x = True` after the mutation block and confirm the new attribute appears in `repr(cfg)`. `Verify: python -c "from boardly.runtime.config_ns import cfg; print(hasattr(cfg, 'feature_flag_x'))"`  (you will need to make `cfg` importable first)
3. **Exercise 3 — Compare equality with different attribute order.** Construct `SimpleNamespace(x=1, y=2)` and `SimpleNamespace(y=2, x=1)`. Print `==`. Confirm the order does not matter for equality (Python dict equality is order-independent). `Verify: python -c "from types import SimpleNamespace; print(SimpleNamespace(x=1, y=2) == SimpleNamespace(y=2, x=1))"`
4. **Exercise 4 — Hyphenated-key fix.** Build a small `normalise_keys(d)` function that replaces hyphens with underscores, then unpacks into a `SimpleNamespace`. Confirm `normalise_keys({"database-url": "x"}).database_url == "x"`. `Verify: python -c "from boardly.runtime.config_ns import normalise_keys; print(normalise_keys({'database-url': 'x'}).database_url)"`
5. **Exercise 5 — The slots-dataclass comparison.** Convert the `ProjectConfig` dataclass above to `@dataclass(slots=True)` (lesson [[06-dataclasses/04-Slots-and-Performance]]) and confirm that `cfg2.tls_cert = "/etc/..."` now raises `AttributeError: 'ProjectConfig' object has no attribute 'tls_cert'` (the `__slots__` rejects the unknown attribute). `Verify: python -c "import dataclasses; print(dataclasses.dataclass.__doc__[:60])"`

## Verification

```bash
$ python boardly/runtime/config_ns.py
cfg: namespace(host='0.0.0.0', port=8000, debug=True)
cfg.host: 0.0.0.0 cfg.port: 8000
after mutation: namespace(host='0.0.0.0', port=8000, debug=False, tls_cert='/etc/boardly/tls.pem')

env_ns: namespace(DATABASE_URL='postgres://localhost/boardly', REDIS_URL='redis://localhost:6379')
env_ns.DATABASE_URL: postgres://localhost/boardly

repr(cfg): namespace(host='0.0.0.0', port=8000, debug=False, tls_cert='/etc/boardly/tls.pem')

a == b: True
a is b: False

cfg2: ProjectConfig(host='0.0.0.0', port=8000, debug=False)

ticket_ns.title: demo
ticket_ns.labels: ['bug', 'ui']
ticket_ns: namespace(title='demo', owner='ada', labels=['bug', 'ui'], estimate=5)

--- attribute access patterns ---
dict access:   raw['title']    -> demo
namespace:     ticket_ns.title -> demo
dataclass:     cfg2.host       -> 0.0.0.0

After typo attribute set: namespace(title='demo', owner='ada', labels=['bug', 'ui'], estimate=5, tite='typo!')
```

If `cfg: namespace(...)` shows every kwarg, `a == b: True` confirms value equality, and `After typo attribute set` shows both `title` and `tite` coexisting, you have the three core `SimpleNamespace` facts working: construction, mutability, and the silent-typo trap.

## Previously Learned Here

- [[12-types/01-NewType]] — `NewType` is the *typed* primitive; `SimpleNamespace` is the *untyped* primitive. The two lessons together are the two ends of the spectrum: zero-runtime-cost-with-types (`NewType`) vs zero-types-with-runtime-bag (`SimpleNamespace`).
- [[06-dataclasses/01-dataclass-Basics]] — `@dataclass` is the canonical *typed* alternative. This lesson cross-references it constantly.
- [[04-collections/04-namedtuple]] — `namedtuple` is the *immutable* alternative. `SimpleNamespace` is mutable; `namedtuple` is frozen. `namedtuple` has fields known at write-time; `SimpleNamespace` does not.

## What's Next

[[12-types/03-GenericAlias-and-UnionType]] — the next stop is the *type of the type*. `list[int]` is a `types.GenericAlias` at runtime; `int | str` is a `types.UnionType`. This lesson shows you what those runtime objects actually *are*, the `typing.get_origin`/`get_args` helpers that abstract over them, and the difference between `list[int]` (the PEP 585 builtin-generic form) and `typing.List[int]` (the older `typing._GenericAlias` form). Three things to look for in lesson 03:

- `type(list[int]).__name__` is `"GenericAlias"`; `type(int | str).__name__` is `"UnionType"` — the runtime types behind the syntax.
- `typing.get_origin(list[int])` returns `list`; `typing.get_args(list[int])` returns `(int,)` — the helpers that work on both the new and old forms.
- `list[int]` and `typing.List[int]` are *different* runtime types (`GenericAlias` vs `_GenericAlias`) — and which you use still matters in 3.12 for some edge cases.

Take your time. Type every example. **This is how you learn.**

## Sources

- **types.SimpleNamespace — CPython reference** — https://docs.python.org/3/library/types.html#types.SimpleNamespace — accessed 2026-10-23 — the canonical API for `SimpleNamespace`, including the explicit statement that it is "a simple object subclass that provides attribute access to its namespace" and "an attribute-equality-based `__repr__` and `__eq__`".
- **types — Dynamic type creation — CPython reference** — https://docs.python.org/3/library/types.html — accessed 2026-10-23 — the section home for `SimpleNamespace` and the rest of the `types` module surface covered in this section.
- **dataclasses — CPython reference** — https://docs.python.org/3/library/dataclasses.html — accessed 2026-10-23 — the canonical reference for `@dataclass`, the typed alternative to `SimpleNamespace` for models.
- **collections.namedtuple — CPython reference** — https://docs.python.org/3/library/collections.html#collections.namedtuple — accessed 2026-10-23 — the immutable, hashable alternative; useful when `SimpleNamespace`'s mutability is a problem.

## What We Learned

- `SimpleNamespace(host="0.0.0.0", port=8000)` constructs a mutable attribute bag from kwargs.
- The `**dict` unpacking pattern (`SimpleNamespace(**some_dict)`) is the canonical dict-to-namespace call — but dict keys must be valid Python identifiers.
- The `__repr__` is `namespace(a=1, b=2)` — every attribute listed in insertion order; the default debug print is *useful* out of the box.
- Equality is value-based — `SimpleNamespace(x=1) == SimpleNamespace(x=1)` is `True`. There is no `__hash__` — namespaces are not hashable.
- Typo trap: `cfg.tite = ...` silently creates a new attribute instead of raising. Use `@dataclass(slots=True)` if you need that to fail.
- The boundary: `SimpleNamespace` for ad-hoc bags (test fixtures, config prototypes, JSON of unknown shape); `@dataclass` for persisted or serialised models. The trade is real and the boundary is enforced in code review.
