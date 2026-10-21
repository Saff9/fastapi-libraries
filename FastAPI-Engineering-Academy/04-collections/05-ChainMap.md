---
title: "Lesson 05: ChainMap"
aliases:
 - collections.ChainMap
 - ChainMap
tags:
 - collections
 - chainmap
 - config
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "20–30 minutes"
prerequisites:
 - "[[04-collections/04-namedtuple]]"
related_lessons:
 - "[[04-collections/06-OrderedDict]]"
 - "[[03-contextlib/05-contextvars]]"
---

# Lesson 05: ChainMap

*`collections.ChainMap` — a view over multiple dicts. Reads fall through layer by layer; writes go to the first layer; `new_child()` pushes a new layer on top. It is the data structure for "defaults + env + user overrides" without copying anything.*

**You're at the very beginning of Section 04 — Lesson 05.**

`ChainMap` is the smallest class in `collections` by line count — under 100 lines of Python — and it solves a problem every backend hits: layered configuration. This lesson walks the read-falls-through protocol, the write-goes-to-first rule, the `new_child` / `parents` API, and the moment when `{**defaults, **env}` is the wrong tool.

Take your time. Type every example. **This is how you learn.**

#collections #chainmap #config

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct a `ChainMap`** with multiple dicts and explain what `__getitem__` does internally on a missing key.
2. **Distinguish reads, writes, and deletes** — what each one does, and why writes/deletes only touch the first layer.
3. **Use `new_child()` and `parents`** to push and pop layers without mutating the underlying dicts.
4. **Choose between `ChainMap` and `{**defaults, **env}`** for a given config-layering problem.

## Prerequisites

Before starting, you need:

- **[[04-collections/04-namedtuple]]** — comfort with the `collections` module's small-class pattern.
- **About 20 minutes of focused time.**

**The most common gap: assuming `ChainMap` copies its inputs.**

It does not. `ChainMap` stores *references* to the input dicts in its `.maps` list. If you mutate one of the underlying dicts after constructing the ChainMap, the ChainMap sees the change. If you wanted a snapshot, copy first. Read this lesson with "view, not copy" front of mind.

## The Problem

Here is the bug. `boardly` has a config object that merges defaults, environment variables, and user overrides:

```python
DEFAULTS = {"db_url": "sqlite:///dev.db", "log_level": "INFO", "max_tickets": 1000}
ENV = {"db_url": "postgres://prod/boardly", "log_level": "DEBUG"}
USER = {"max_tickets": 500}

# The merge-everything pattern
config = {**DEFAULTS, **ENV, **USER}
```

This is correct. It is also wrong in three ways:

1. **It copies.** If `DEFAULTS` has 200 keys and `USER` overrides 3, you have built a fresh 200-key dict. Multiply by every config read in a hot path.
2. **It is one-shot.** If a user toggles a setting at runtime and you want to layer it on top, you have to re-merge the whole thing — losing the layering information.
3. **It loses provenance.** Once merged, you cannot ask "where did `db_url` come from?" — the answer is "the merged dict, somewhere." Debugging a wrong config value becomes a print-and-stare exercise.

`ChainMap(USER, ENV, DEFAULTS)` solves all three. It stores references to the three dicts; reads fall through; the underlying dicts stay intact and addressable.

## The Code

```python
# boardly/config.py
"""Layered configuration with collections.ChainMap."""
from collections import ChainMap
from typing import Any


# Three real config layers. In production these come from defaults.py, env, and
# a per-user DB row. Here we use module-level dicts for clarity.
DEFAULTS: dict[str, Any] = {
    "db_url": "sqlite:///dev.db",
    "log_level": "INFO",
    "max_tickets": 1000,
    "feature_flags": {"export_csv": False},
}

ENV: dict[str, Any] = {
    "db_url": "postgres://prod/boardly",
    "log_level": "DEBUG",
}

USER: dict[str, Any] = {
    "max_tickets": 500,
    "feature_flags": {"export_csv": True},
}


def build_config() -> ChainMap:
    """Layer USER > ENV > DEFAULTS. Reads fall through to lower layers."""
    return ChainMap(USER, ENV, DEFAULTS)


def with_override(base: ChainMap, **overrides: Any) -> ChainMap:
    """Push a temporary override layer; the underlying layers are untouched."""
    return base.new_child(overrides)


def lookup(key: str, config: ChainMap) -> Any:
    """Read through the chain. Raises KeyError if no layer has the key."""
    return config[key]


def provenance(key: str, config: ChainMap) -> str:
    """Return the name of the layer that actually provided the value."""
    for i, layer in enumerate(config.maps):
        if key in layer:
            return f"layer {i}: {layer!r}"
    return "not present"


if __name__ == "__main__":
    cfg = build_config()
    print("db_url ->", lookup("db_url", cfg))
    print("log_level ->", lookup("log_level", cfg))
    print("max_tickets ->", lookup("max_tickets", cfg))
    print("default-only 'feature_flags' ->", cfg["feature_flags"])

    print("\n--- provenance ---")
    print("db_url from:", provenance("db_url", cfg))
    print("max_tickets from:", provenance("max_tickets", cfg))

    print("\n--- write goes to the first layer ---")
    cfg["max_tickets"] = 9999
    print("USER after write:", USER)

    print("\n--- new_child: push a layer ---")
    cfg2 = with_override(cfg, max_tickets=7, log_level="ERROR")
    print("override view -> max_tickets:", cfg2["max_tickets"])
    print("override view -> log_level:", cfg2["log_level"])
    print("base unchanged -> max_tickets:", cfg["max_tickets"])

    print("\n--- parents: pop the top layer ---")
    cfg3 = cfg2.parents
    print("after parents, max_tickets:", cfg3["max_tickets"])

    print("\n--- delete goes to the first layer only ---")
    del cfg["max_tickets"]
    print("USER after delete:", USER)
    print("config now sees:", cfg["max_tickets"])   # falls through to DEFAULTS
```

## Line-by-Line Deep Dive

### Lines 1–4: Imports

```python
# boardly/config.py
"""Layered configuration with collections.ChainMap."""
from collections import ChainMap
from typing import Any
```

`from collections import ChainMap`. The only new import. `typing.Any` is for the value type — config values are heterogeneous (strings, ints, dicts of feature flags), so `Any` is the honest annotation.

### Lines 18–22: The three layers

```python
DEFAULTS: dict[str, Any] = {
    "db_url": "sqlite:///dev.db",
    "log_level": "INFO",
    "max_tickets": 1000,
    "feature_flags": {"export_csv": False},
}
```

Three module-level dicts. In a real codebase these would come from a `defaults.py`, `os.environ`, and a per-user DB row. The point is: they are independent dicts that exist *before* the ChainMap touches them. The ChainMap does not own them; it views them.

### Lines 32–35: Construction — order matters

```python
def build_config() -> ChainMap:
    """Layer USER > ENV > DEFAULTS. Reads fall through to lower layers."""
    return ChainMap(USER, ENV, DEFAULTS)
```

`ChainMap(USER, ENV, DEFAULTS)` — the first positional argument is the *top* layer (highest precedence). The last argument is the *bottom* layer (lowest precedence, the defaults). Reads walk `USER` first, then `ENV`, then `DEFAULTS`.

Internally, `ChainMap.__init__` stores the arguments as `self.maps = list(args)` (or `[args]` if you pass a single iterable). `.maps` is the public attribute — a list of dicts, top-to-bottom. Reading `cfg.maps` is the cheapest way to see the layering.

### Lines 38–41: `new_child` — push without mutation

```python
def with_override(base: ChainMap, **overrides: Any) -> ChainMap:
    """Push a temporary override layer; the underlying layers are untouched."""
    return base.new_child(overrides)
```

`base.new_child(overrides)` returns a *new* `ChainMap` whose first layer is `overrides` and whose remaining layers are `base.maps` (the same dict references). The original `base` is not modified — `new_child` is a pure push.

`new_child()` with no argument pushes an empty dict. That is the canonical "scope a write to a temporary layer" pattern: `with cfg.new_child() as scoped:` ... actually, `ChainMap` is not a context manager, but the pattern is the same shape — call `new_child()`, do writes, drop the reference.

### Lines 44–47: `__getitem__` falls through

```python
def lookup(key: str, config: ChainMap) -> Any:
    """Read through the chain. Raises KeyError if no layer has the key."""
    return config[key]
```

`config[key]` walks `config.maps` in order, returning the value from the first layer that has `key`. If no layer has it, `ChainMap.__getitem__` raises `KeyError` — same as a plain `dict`.

Internally this is roughly:

```python
def __getitem__(self, key):
    for mapping in self.maps:
        if key in mapping:
            return mapping[key]
    raise KeyError(key)
```

The fall-through is linear in the number of layers — for a 3-layer config that is 3 dict lookups worst case. Cheap.

### Lines 49–54: `provenance` — the thing `ChainMap` enables that `{**a, **b}` cannot

```python
def provenance(key: str, config: ChainMap) -> str:
    """Return the name of the layer that actually provided the value."""
    for i, layer in enumerate(config.maps):
        if key in layer:
            return f"layer {i}: {layer!r}"
    return "not present"
```

`config.maps` is the public list of layer dicts. Walking it lets you say "which layer provided this value" — the provenance question that a merged dict cannot answer. This is the `ChainMap` killer feature for debugging: when a config value is wrong, you want to know whether the user, the env, or the defaults supplied it. `ChainMap` keeps that information; `{**a, **b}` throws it away.

### Lines 60–63: Writes go to the first layer

```python
    print("\n--- write goes to the first layer ---")
    cfg["max_tickets"] = 9999
    print("USER after write:", USER)
```

`cfg["max_tickets"] = 9999` writes to `cfg.maps[0]` — that is `USER`. The other layers are not touched. If `USER` did not have `max_tickets` before, it does now. The write does not fall through; it lands on the top layer only.

**Why first-layer-only?** Because the alternative (writing to whatever layer has the key) would silently mutate `ENV` or `DEFAULTS` — a layer the caller may not have intended to modify. The first-layer rule is the conservative choice: writes go to the layer you explicitly chose as the "write target" by putting it first.

### Lines 65–69: `new_child` returns a new ChainMap

```python
    print("\n--- new_child: push a layer ---")
    cfg2 = with_override(cfg, max_tickets=7, log_level="ERROR")
    print("override view -> max_tickets:", cfg2["max_tickets"])
    print("override view -> log_level:", cfg2["log_level"])
    print("base unchanged -> max_tickets:", cfg["max_tickets"])
```

`cfg2 = with_override(cfg, max_tickets=7, log_level="ERROR")` — `cfg2` is a new `ChainMap`. Its first layer is `{"max_tickets": 7, "log_level": "ERROR"}`. Its remaining layers are the same `USER`, `ENV`, `DEFAULTS` references that `cfg` has.

Reads on `cfg2` see the override first: `cfg2["max_tickets"]` is `7`. Reads on the original `cfg` are unaffected: `cfg["max_tickets"]` is still `9999` (from the previous write to `USER`).

**Why this matters:** You can scope a request-level override on top of a process-level config without copying anything. A request handler that wants to "treat this request as if `log_level=ERROR`" calls `cfg.new_child({"log_level": "ERROR"})` and passes the resulting `ChainMap` to the request's dependencies. The underlying process-level config is untouched.

### Lines 71–73: `parents` — pop the top layer

```python
    print("\n--- parents: pop the top layer ---")
    cfg3 = cfg2.parents
    print("after parents, max_tickets:", cfg3["max_tickets"])
```

`cfg2.parents` returns a new `ChainMap` containing all of `cfg2`'s layers *except the first*. That is the pop-the-top operation — the inverse of `new_child`.

`cfg3["max_tickets"]` is `9999` — the value in `USER` after the earlier write, because `cfg3`'s top layer is `USER` (since `cfg2`'s override layer was popped).

### Lines 75–78: Deletes hit the first layer only

```python
    print("\n--- delete goes to the first layer only ---")
    del cfg["max_tickets"]
    print("USER after delete:", USER)
    print("config now sees:", cfg["max_tickets"])   # falls through to DEFAULTS
```

`del cfg["max_tickets"]` deletes from `cfg.maps[0]` — that is `USER`. If `USER` did not have `max_tickets`, this raises `KeyError`. The delete does *not* "shadow" the lower layers — meaning the read on the next line (`cfg["max_tickets"]`) now falls through to `DEFAULTS` and returns `1000`.

**Why this matters:** The delete-and-fall-through pattern is the way you "reset to default" in a layered config. Without `ChainMap`, you would have to remove the override from the merged dict and re-merge — losing the override history. With `ChainMap`, you delete the key from the top layer and the read falls through.

## Execution Trace

```bash
$ uv run python boardly/config.py
db_url -> postgres://prod/boardly
log_level -> DEBUG
max_tickets -> 500
default-only 'feature_flags' -> {'export_csv': True}

--- provenance ---
db_url from: layer 1: {'db_url': 'postgres://prod/boardly', 'log_level': 'DEBUG'}
max_tickets from: layer 0: {'max_tickets': 500, 'feature_flags': {'export_csv': True}}

--- write goes to the first layer ---
USER after write: {'max_tickets': 9999, 'feature_flags': {'export_csv': True}}

--- new_child: push a layer ---
override view -> max_tickets: 7
override view -> log_level: ERROR
base unchanged -> max_tickets: 9999

--- parents: pop the top layer ---
after parents, max_tickets: 9999

--- delete goes to the first layer only ---
USER after delete: {'feature_flags': {'export_csv': True}}
config now sees: 1000
```

Notice the provenance output: `db_url` is reported as provided by `layer 1` (the `ENV` dict), because `USER` (layer 0) does not contain a `db_url` key — the loop walks `config.maps` in order and returns the first layer that has the key. `max_tickets` is reported as `layer 0` (the `USER` dict), because that is where the override lives. This is the `ChainMap` killer feature for debugging: when a config value is wrong, you can ask `provenance(key)` and get the layer that supplied it — a question that a merged `{**a, **b}` dict cannot answer.

## Common Mistakes

### Mistake 1: Assuming `ChainMap` copies its layers

```python
USER["max_tickets"] = 5
cfg = ChainMap(USER, ENV, DEFAULTS)
USER["max_tickets"] = 999
# student expects cfg["max_tickets"] == 5
```

**Symptom:** `cfg["max_tickets"]` is `999`, not `5`.

**Why:** `ChainMap` stores *references* to the input dicts in `.maps`. Mutating `USER` after construction is visible through the ChainMap immediately.

**Fix:** If you want a snapshot, copy the layers first: `ChainMap(dict(USER), dict(ENV), dict(DEFAULTS))`. Or use `{**DEFAULTS, **ENV, **USER}` — which is the merge-and-copy pattern that loses provenance but gives a snapshot.

### Mistake 2: Writing and expecting it to land on the layer that "should" own the value

```python
cfg = ChainMap(USER, ENV, DEFAULTS)
cfg["db_url"] = "new_value"
# student expects ENV["db_url"] to be updated
```

**Symptom:** `ENV["db_url"]` is unchanged; `USER["db_url"]` now has `"new_value"`.

**Why:** Writes go to the first layer (`USER`), not to the layer that had the key before. The ChainMap does not "remember" provenance for writes; the first-layer rule is universal.

**Fix:** If you want to write to a specific layer, write to it directly: `ENV["db_url"] = "new_value"`. The ChainMap will then read the new value via fall-through on the next read.

### Mistake 3: Deleting a key and expecting it to "fall through fully"

```python
cfg = ChainMap(USER, ENV, DEFAULTS)
del cfg["db_url"]   # student expects no more db_url anywhere
cfg["db_url"]        # student expects KeyError
```

**Symptom:** `cfg["db_url"]` still returns `"postgres://prod/boardly"` — the value from `ENV`.

**Why:** `del cfg["db_url"]` only deletes from `cfg.maps[0]`. If `db_url` is in `ENV` (layer 1), the next read falls through to `ENV` and succeeds.

**Fix:** To "shadow" a key from lower layers, set it to a sentinel in the top layer (e.g., `cfg["db_url"] = None`). To remove the key everywhere, iterate `cfg.maps` and delete from each.

## Engineering Trade-Offs

**Decision:** Use `ChainMap` for layered config where you need provenance and runtime mutation; use `{**defaults, **env}` for one-shot merges.

**Both sides:** `{**a, **b, **c}` wins on:

1. Speed — a single dict, no fall-through, O(1) reads with no loop.
2. JSON-friendliness — `json.dumps(merged)` just works; `json.dumps(chainmap)` raises `TypeError` (ChainMap is not a dict).
3. Closure over the layers — once merged, the dict is independent of the source dicts.

`ChainMap` wins on:

1. Layered writes — `new_child` lets you scope overrides per request without copying.
2. Provenance — `.maps` tells you where each value came from.
3. Zero-copy views — for 200-key defaults, the ChainMap is 3 references vs. 200 keys copied.
4. Falling-through deletes — the "reset to default" pattern is one `del` away.

**Commitment:** `boardly/config.py` uses `ChainMap` for the runtime config object because the per-request override pattern is real (e.g., the `?log_level=ERROR` query param). For one-shot merges — e.g., the `pyproject.toml` `[tool.boardly]` table flattened to a dict — `boardly` uses `{**defaults, **file, **env}` because the result is written to a JSON file and the layered history does not matter post-merge.

## Exercises

1. **Exercise 1 — Inspect `.maps`.** Build a `ChainMap` of three layers and print `.maps`. Confirm it is a list of dict references. `Verify: uv run python -c "from collections import ChainMap; a={'x':1}; b={'y':2}; c=ChainMap(a,b); print(c.maps, c.maps[0] is a)"`
2. **Exercise 2 — Read falls through.** Build `ChainMap({'x':1}, {'x':2, 'y':3})` and print `c['x']` and `c['y']`. Confirm the top layer's `x` wins. `Verify: uv run python -c "from collections import ChainMap; c=ChainMap({'x':1},{'x':2,'y':3}); print(c['x'], c['y'])"`
3. **Exercise 3 — `new_child` is a push.** Build a ChainMap, call `new_child({'z':99})`, confirm the new ChainMap has 3 layers and the original has 2. `Verify: uv run python -c "from collections import ChainMap; c=ChainMap({'x':1},{'y':2}); d=c.new_child({'z':99}); print(len(c.maps), len(d.maps), d['z'], d['x'])"`
4. **Exercise 4 — `parents` is a pop.** Confirm `c.parents.maps == c.maps[1:]`. `Verify: uv run python -c "from collections import ChainMap; c=ChainMap({'x':1},{'y':2},{'z':3}); print(c.parents.maps == c.maps[1:])"`
5. **Exercise 5 — Per-request override.** Write a `with_request_override(cfg, **overrides)` context manager (using `contextlib.contextmanager` from Section 03) that yields `cfg.new_child(overrides)` and does nothing on exit. `Verify: uv run python -c "from collections import ChainMap; from contextlib import contextmanager; cfg=ChainMap({'x':1});\n@contextmanager\ndef w(cfg, **o):\n  yield cfg.new_child(o)\nwith w(cfg, x=99) as c:\n  print(c['x'])\nprint(cfg['x'])"`

## Verification

```bash
$ uv run python boardly/config.py
db_url -> postgres://prod/boardly
log_level -> DEBUG
max_tickets -> 500
default-only 'feature_flags' -> {'export_csv': True}

--- provenance ---
db_url from: layer 1: {'db_url': 'postgres://prod/boardly', 'log_level': 'DEBUG'}
max_tickets from: layer 0: {'max_tickets': 500, 'feature_flags': {'export_csv': True}}

--- write goes to the first layer ---
USER after write: {'max_tickets': 9999, 'feature_flags': {'export_csv': True}}

--- new_child: push a layer ---
override view -> max_tickets: 7
override view -> log_level: ERROR
base unchanged -> max_tickets: 9999

--- parents: pop the top layer ---
after parents, max_tickets: 9999

--- delete goes to the first layer only ---
USER after delete: {'feature_flags': {'export_csv': True}}
config now sees: 1000
```

## Previously Learned Here

- [[04-collections/04-namedtuple]] — record types as the static side of `collections`.
- [[04-collections/02-defaultdict]] — `defaultdict`'s `__missing__` was the warm-up for "fall through on missing".

## What's Next

[[04-collections/06-OrderedDict]] — the dict subclass that *still ships* even though `dict` has been ordered since Python 3.7. Why? Because `OrderedDict.move_to_end(key)` and `OrderedDict.popitem(last=True)` are not on `dict`, and because `OrderedDict` equality is order-sensitive while `dict` equality is not. We will see when each matters and why LRU caches are still built on `OrderedDict` today.

## Sources

- **Python `collections.ChainMap` documentation** — https://docs.python.org/3/library/collections.html#collections.ChainMap — accessed 2026-10-23 — the canonical reference for `maps`, `new_child`, `parents`, and the read/write/delete semantics.
- **What's New in Python 3.3 — `ChainMap`** — https://docs.python.org/3/whatsnew/3.3.html#collections — accessed 2026-10-23 — historical context for the `ChainMap` addition (the layered-config pain this lesson opens with; no dedicated PEP).
- **`ChainMap` source in CPython** — https://github.com/python/cpython/blob/3.12/Lib/collections/__init__.py#L1170 — accessed 2026-10-23 — under 100 lines of Python, including the `__getitem__` fall-through and `new_child` push.

## What We Learned

- `ChainMap(*maps)` stores references to the input dicts in `.maps`; reads walk them top-to-bottom.
- Writes (`c[k] = v`) and deletes (`del c[k]`) hit `maps[0]` only — the "first layer" rule.
- `new_child(d)` returns a new ChainMap with `d` pushed on top; the original is untouched.
- `parents` returns a new ChainMap with the top layer popped.
- The "delete and fall through" pattern lets you reset a key to its default without re-merging.
- `{**a, **b}` wins for one-shot merges; `ChainMap` wins for runtime mutation and provenance.
