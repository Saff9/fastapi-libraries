---
title: "Lesson 04: ModuleType and FunctionType"
aliases:
 - ModuleType
 - FunctionType
 - MethodType
 - CodeType
 - MappingProxyType
 - types.ModuleType
 - types.FunctionType
tags:
 - types
 - moduletype
 - functiontype
 - mappingproxytype
 - introspection
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[12-types/03-GenericAlias-and-UnionType]]"
 - "[[12-types/01-NewType]]"
 - "[[10-inspect/01-signature-and-Parameter]]"
related_lessons:
 - "[[12-types/01-NewType]]"
 - "[[12-types/02-SimpleNamespace]]"
 - "[[12-types/03-GenericAlias-and-UnionType]]"
 - "[[10-inspect/01-signature-and-Parameter]]"
 - "[[10-inspect/06-How-FastAPI-uses-inspect]]"
---

# Lesson 04: ModuleType and FunctionType

*`isinstance(math, types.ModuleType)` is `True`; `isinstance(my_func, types.FunctionType)` is `True`; `inspect.signature(f).parameters` is a `types.MappingProxyType` — the runtime types behind `import`, `def`, and the FastAPI signature walk.*

**You're at the very beginning of Section 12 — and we are at the bottom of the stack.**

This is the lesson that closes the section. Every construct in Python — every `import`, every `def`, every bound method, every `inspect.signature` — has a *runtime type*. That type lives in `types`. `import math` makes `math` an instance of `types.ModuleType`. `def f(): ...` makes `f` an instance of `types.FunctionType`. `obj.method` is a `types.MethodType`. The `__code__` attribute of any function is a `types.CodeType`. The `sig.parameters` you have already seen in lesson [[10-inspect/01-signature-and-Parameter]] is a `types.MappingProxyType` — a read-only view over a dict that nobody can mutate. By the end of this lesson you will know the six runtime types behind the language constructs you write every day. Take your time. Type every example. **This is how you learn.**

#types #moduletype #functiontype #mappingproxytype

## Learning Objectives

By the end of this lesson you will be able to:

1. **Identify** the runtime type of every common construct — `types.ModuleType` for modules, `types.FunctionType` for user-defined functions, `types.BuiltinFunctionType` for C-builtins like `len`, `types.MethodType` for bound methods on user classes.
2. **Read** the `types.CodeType` attributes — `co_argcount`, `co_varnames`, `co_consts`, `co_names` — and explain what they hold.
3. **Construct** a `types.MappingProxyType(some_dict)` and explain why writes raise `TypeError` while reads reflect updates to the underlying dict.
4. **Explain** why `inspect.signature(f).parameters` is a `MappingProxyType` — and why the read-only-ness matters for FastAPI's signature walk.
5. **Distinguish** the four function/method types — `FunctionType` (user `def`/`lambda`), `BuiltinFunctionType` (C-level `len`/`print`/`[].append`), `MethodType` (bound method on a user class), `MethodWrapperType` (dunder wrappers like `[].__init__`).

## Prerequisites

Before starting, you need:

- **The three earlier `12-types` lessons** — [[12-types/01-NewType]], [[12-types/02-SimpleNamespace]], [[12-types/03-GenericAlias-and-UnionType]] — for the section's framing that `types` is the runtime-type home.
- **`inspect.signature` and `Parameter`** — [[10-inspect/01-signature-and-Parameter]] — for the `sig.parameters` object that this lesson reveals is a `MappingProxyType`. Lesson 04 of this section completes the picture lesson 01 of `inspect` started.
- **About 30–45 minutes of focused time.**

**The most common gap: not realising that modules are *instances* of a class.**

Students arrive having written `import math` thousands of times and assume that "module" is a special category — distinct from "object". It is not. A module is an instance of `types.ModuleType`, exactly the way `[1, 2]` is an instance of `list`. `isinstance(math, types.ModuleType)` is `True`. You can construct a module dynamically: `mymod = types.ModuleType("dynamic")`. You can subclass `types.ModuleType` (rare, but legal). The fact that you usually write `import math` rather than `mymod = types.ModuleType("math")` is a syntactic convenience — the runtime sees the same kind of object either way. Once you internalise this, every other "X is an instance of a class" fact in this lesson becomes natural.

## The Problem

Here is the bug. `boardly` has a small plugin system that loads Python files from a `plugins/` directory and registers functions from each:

```python
# boardly/plugins/bad_loader.py — the bad old days
def load_plugin(path):
    # How do we know if `path` points to a module, a function, or something else?
    spec = importlib.util.spec_from_file_location("plugin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Walk every attribute and register callables
    handlers = {}
    for name in dir(module):
        attr = getattr(module, name)
        # ← how do we tell "user function" from "imported stdlib function"?
        # ← how do we skip the dunder wrappers like __name__?
        handlers[name] = attr  # too permissive — registers everything
    return handlers
```

Three problems. (1) The naive `for name in dir(module)` picks up *everything* — imported names, the `__name__` dunder, the `__spec__` object, classes, modules re-exported from imports. The plugin system ends up trying to call `len` as if it were a handler. (2) Without a way to ask "is this a user-defined function?", the loader cannot tell a plugin function (`def handle_create_ticket(...): ...`) from an accidentally-imported builtin (`from os import getenv`). (3) The `inspect.signature(f).parameters` dict, used downstream to figure out what arguments each handler takes, *looks* like a regular dict but rejects writes — `sig.parameters["new"] = ...` raises `TypeError`. If the loader does not know it is dealing with a `MappingProxyType`, it will hit that error at runtime with no idea why.

`types` provides the answer:

```python
import types, inspect, importlib.util

def load_plugin(path):
    spec = importlib.util.spec_from_file_location("plugin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert isinstance(module, types.ModuleType)        # the right kind of object
    handlers = {}
    for name in dir(module):
        attr = getattr(module, name)
        # Only user-defined functions, not imports, not dunders, not builtins.
        if isinstance(attr, types.FunctionType):
            handlers[name] = attr
    return handlers

# Downstream — sig.parameters is a MappingProxyType, so we copy before mutating.
sig = inspect.signature(some_handler)
params = dict(sig.parameters)   # Materialise the read-only view into a regular dict
```

The two `isinstance` checks (against `types.ModuleType` and `types.FunctionType`) and the `dict(sig.parameters)` materialisation are the three things this lesson teaches. They are the runtime-type literacy that any plugin system, framework, or introspection tool needs.

## The Code

```python
# boardly/types_runtime.py
"""boardly — types.ModuleType, FunctionType, MethodType, CodeType, MappingProxyType."""
import math
import types
import inspect

# 1. types.ModuleType — every module IS an instance of this.
print("== ModuleType ==")
print("isinstance(math, types.ModuleType):", isinstance(math, types.ModuleType))
print("type(math).__name__:", type(math).__name__)
print("isinstance(types, types.ModuleType):", isinstance(types, types.ModuleType))

# Construct a module dynamically — same type as `import` produces.
mymod = types.ModuleType("dynamic")
mymod.answer = 42
print("dynamic module:", mymod, "type:", type(mymod).__name__)
print("isinstance(mymod, types.ModuleType):", isinstance(mymod, types.ModuleType))

# 2. types.FunctionType — user-defined def functions and lambdas.
print("\n== FunctionType ==")
def my_function(x):
    return x * 2

print("isinstance(my_function, types.FunctionType):", isinstance(my_function, types.FunctionType))
print("isinstance(lambda x: x, types.FunctionType):", isinstance(lambda x: x, types.FunctionType))
# types.LambdaType is an alias for types.FunctionType — same object.
print("types.LambdaType is types.FunctionType:", types.LambdaType is types.FunctionType)

# 3. types.BuiltinFunctionType — C-builtins like len, print, [].append (bound form).
print("\n== BuiltinFunctionType ==")
print("isinstance(len, types.BuiltinFunctionType):", isinstance(len, types.BuiltinFunctionType))
print("isinstance(print, types.BuiltinFunctionType):", isinstance(print, types.BuiltinFunctionType))
print("isinstance([].append, types.BuiltinFunctionType):", isinstance([].append, types.BuiltinFunctionType))
# types.BuiltinMethodType is an alias — same class.
print("types.BuiltinFunctionType is types.BuiltinMethodType:", types.BuiltinFunctionType is types.BuiltinMethodType)
print("type(len).__name__:", type(len).__name__)

# 4. types.MethodType — a bound method on a user-defined class.
print("\n== MethodType ==")
class Ticket:
    def close(self):
        return "closed"

t = Ticket()
print("isinstance(t.close, types.MethodType):", isinstance(t.close, types.MethodType))
print("type(t.close).__name__:", type(t.close).__name__)
print("t.close.__func__ is Ticket.close:", t.close.__func__ is Ticket.close)
print("t.close.__self__ is t:", t.close.__self__ is t)

# 5. types.MethodWrapperType — wrappers around dunders like [].__init__.
print("\n== MethodWrapperType ==")
print("type([].__init__).__name__:", type([].__init__).__name__)
print("isinstance([].__init__, types.MethodWrapperType):", isinstance([].__init__, types.MethodWrapperType))
print("isinstance(().__contains__, types.MethodWrapperType):", isinstance(().__contains__, types.MethodWrapperType))

# 6. types.CodeType — the __code__ attribute of every function.
print("\n== CodeType ==")
code = my_function.__code__
print("isinstance(code, types.CodeType):", isinstance(code, types.CodeType))
print("type(code).__name__:", type(code).__name__)
print("code.co_argcount:", code.co_argcount)
print("code.co_varnames:", code.co_varnames)
print("code.co_consts:", code.co_consts)

# 7. types.MappingProxyType — a read-only view over a dict.
print("\n== MappingProxyType ==")
d = {"open": 1, "in_progress": 2, "closed": 3}
view = types.MappingProxyType(d)
print("type(view).__name__:", type(view).__name__)
print("view['open']:", view["open"])

# Writes raise TypeError.
try:
    view["cancelled"] = 0
    print("write succeeded (unexpected)")
except TypeError as e:
    print("write raised TypeError:", e)

# Reads reflect updates to the underlying dict.
d["cancelled"] = 0
print("after d['cancelled']=0, view reflects:", dict(view))

# 8. THE key example — inspect.signature.parameters IS a MappingProxyType.
print("\n== signature.parameters is a mappingproxy ==")
def get_ticket(id: int, status: str = "open") -> dict:
    return {"id": id, "status": status}

sig = inspect.signature(get_ticket)
print("type(sig.parameters).__name__:", type(sig.parameters).__name__)
print("isinstance(sig.parameters, types.MappingProxyType):", isinstance(sig.parameters, types.MappingProxyType))
print("sig.parameters keys:", list(sig.parameters.keys()))

try:
    sig.parameters["user"] = None
    print("parameters write succeeded (unexpected)")
except TypeError as e:
    print("parameters write raised TypeError:", e)

# 9. Why FastAPI cares — the parameters object is read-only so nobody can mutate
# FastAPI's view of your signature between the inspect call and the dependency run.
print("\n== The FastAPI connection ==")
print("sig.parameters['id'].name:", sig.parameters["id"].name)
print("sig.parameters['id'].annotation:", sig.parameters["id"].annotation)
print("sig.parameters['id'].kind:", sig.parameters["id"].kind)
print("sig.parameters['status'].default:", sig.parameters["status"].default)
```

## Line-by-Line Deep Dive

### Lines 1–13: `types.ModuleType` — modules are instances

```python
# boardly/types_runtime.py
"""boardly — types.ModuleType, FunctionType, MethodType, CodeType, MappingProxyType."""
import math
import types
import inspect

# 1. types.ModuleType — every module IS an instance of this.
print("== ModuleType ==")
print("isinstance(math, types.ModuleType):", isinstance(math, types.ModuleType))
print("type(math).__name__:", type(math).__name__)
print("isinstance(types, types.ModuleType):", isinstance(types, types.ModuleType))
```

Three facts to verify. (1) `isinstance(math, types.ModuleType)` is `True` — the `math` module is an instance of the `ModuleType` class. (2) `type(math).__name__` is `"module"` — the class is called `ModuleType` at the API level, but its `__name__` attribute (used for the user-facing repr) is `"module"` lowercase, the same word you use in `import`. (3) `isinstance(types, types.ModuleType)` is `True` — the `types` module *itself* is an instance of `types.ModuleType`. The `types` module defines `ModuleType` *and is itself an instance of* it. This is not circular — `types.ModuleType` is a class defined in CPython's C source; the `types` Python module is one of many instances of that class.

**Why is `type(math).__name__` `"module"` and not `"ModuleType"`?**

Because the `ModuleType` class sets its `__name__` to `"module"` (lowercase, the user-facing word) — this is the word that appears in error messages like `AttributeError: 'module' object has no attribute 'X'`. The class's actual Python name (the variable you use to refer to it) is `types.ModuleType`, but its `__name__` attribute is `"module"`. The same pattern appears elsewhere — `type([]).__name__` is `"list"` (the class is `list`, the user-facing word is `"list"`); `type(None).__name__` is `"NoneType"` (the class is `types.NoneType`, the user-facing word is `"NoneType"`). The convention is: the class name and the `__name__` are often the same; when they differ, `__name__` is the user-facing form.

### Lines 15–19: Constructing a module dynamically

```python
# Construct a module dynamically — same type as `import` produces.
mymod = types.ModuleType("dynamic")
mymod.answer = 42
print("dynamic module:", mymod, "type:", type(mymod).__name__)
print("isinstance(mymod, types.ModuleType):", isinstance(mymod, types.ModuleType))
```

`types.ModuleType("dynamic")` constructs a new module object whose `__name__` is `"dynamic"`. The module starts empty — no attributes, no `__dict__` contents. Setting `mymod.answer = 42` adds an attribute exactly the way `import math; math.pi = 3.14` would. The constructed module is *the same kind of object* as `math` — `isinstance(mymod, types.ModuleType)` is `True`. This is the foundation of every dynamic-module pattern: plugin loaders (`importlib.util.module_from_spec` ultimately produces a `ModuleType`), test fixtures (a module constructed in-memory for testing), and metaprogramming utilities. The `import` statement is syntactic sugar over a sequence of `ModuleType` constructions and initialisations; the runtime has no special "module" category.

### Lines 21–29: `types.FunctionType` and the `LambdaType` alias

```python
# 2. types.FunctionType — user-defined def functions and lambdas.
print("\n== FunctionType ==")
def my_function(x):
    return x * 2

print("isinstance(my_function, types.FunctionType):", isinstance(my_function, types.FunctionType))
print("isinstance(lambda x: x, types.FunctionType):", isinstance(lambda x: x, types.FunctionType))
# types.LambdaType is an alias for types.FunctionType — same object.
print("types.LambdaType is types.FunctionType:", types.LambdaType is types.FunctionType)
```

`isinstance(my_function, types.FunctionType)` is `True` — every `def`-defined function is an instance of `types.FunctionType`. `isinstance(lambda x: x, types.FunctionType)` is *also* `True` — lambdas are the *same* class. There is no separate `LambdaFunctionType`; the `types.LambdaType` name is an alias for `types.FunctionType` (the two are literally `is`-identical: `types.LambdaType is types.FunctionType`). The standard library exposes `LambdaType` as a separate name for backwards-compatibility reasons — older code expected "lambdas have their own type" — but the runtime has unified them. This is one of the historical accidents of the `types` module: the names were declared when the language distinguished the two, and the unification kept both names to avoid breaking existing `isinstance` checks.

**Why does Python have one `FunctionType` for both `def` and `lambda` when they look different?**

Because at the bytecode level they *are* the same. A `def my_function(x): return x * 2` and a `lambda x: x * 2` compile to *identical* bytecode — the only difference is the name (`my_function` vs `<lambda>`) and the lack of statements in a lambda body (lambdas are restricted to expressions). The runtime has no reason to distinguish them — both are callable objects with a `__code__`, a `__globals__`, a `__defaults__`, etc. The `FunctionType` class captures everything the two share. The historical `LambdaType` alias exists because early Python documentation suggested lambdas were a different category; the runtime never agreed.

### Lines 31–38: `types.BuiltinFunctionType` for C-builtins

```python
# 3. types.BuiltinFunctionType — C-builtins like len, print, [].append (bound form).
print("\n== BuiltinFunctionType ==")
print("isinstance(len, types.BuiltinFunctionType):", isinstance(len, types.BuiltinFunctionType))
print("isinstance(print, types.BuiltinFunctionType):", isinstance(print, types.BuiltinFunctionType))
print("isinstance([].append, types.BuiltinFunctionType):", isinstance([].append, types.BuiltinFunctionType))
# types.BuiltinMethodType is an alias — same class.
print("types.BuiltinFunctionType is types.BuiltinMethodType:", types.BuiltinFunctionType is types.BuiltinMethodType)
print("type(len).__name__:", type(len).__name__)
```

`isinstance(len, types.BuiltinFunctionType)` is `True` — `len` is a C-level builtin, not a user-defined function. `isinstance([].append, types.BuiltinFunctionType)` is *also* `True` — the bound method `[].append` (the `append` of a specific list instance) is the same class. The class's `__name__` is `"builtin_function_or_method"` — note the unified name, which captures the fact that builtins and bound-builtin-methods are the same runtime kind. The `types.BuiltinMethodType` name is, like `LambdaType`, an alias — `types.BuiltinFunctionType is types.BuiltinMethodType` is `True`. Distinguishing "a top-level builtin like `len`" from "a bound builtin method like `[].append`" requires more work — they are the same class. If you need to distinguish, you check whether `__self__` is set (bound methods have `__self__`; top-level builtins do not) and what type `__self__` is (a module vs a list instance).

**Why does Python treat `len` (a top-level builtin) and `[].append` (a bound method) as the same runtime type?**

Because both are C-level callables that have no Python `__code__` object — they are implemented in C and exposed to Python via a C-level function pointer. The runtime representation is identical: a `PyCFunctionObject` struct. The only difference is whether the struct carries a `self` pointer (`[].append` does; `len` does not). Distinguishing them by class would require two C-level types for what is structurally one kind of object; the standard library chose to expose one class and let users inspect `__self__` if they need to differentiate. This is the same design decision as `LambdaType`/`FunctionType` — unify when the runtime does, expose historical names as aliases.

### Lines 40–48: `types.MethodType` for bound methods on user classes

```python
# 4. types.MethodType — a bound method on a user-defined class.
print("\n== MethodType ==")
class Ticket:
    def close(self):
        return "closed"

t = Ticket()
print("isinstance(t.close, types.MethodType):", isinstance(t.close, types.MethodType))
print("type(t.close).__name__:", type(t.close).__name__)
print("t.close.__func__ is Ticket.close:", t.close.__func__ is Ticket.close)
print("t.close.__self__ is t:", t.close.__self__ is t)
```

`t.close` is a `types.MethodType` instance — a *bound method* on a user class. Three attributes matter. (1) `t.close.__func__` is the underlying function (`Ticket.close` itself) — the unbound function object stored as a class attribute. (2) `t.close.__self__` is the bound instance (`t`) — the `self` argument that will be prepended when the method is called. (3) Calling `t.close()` is equivalent to `Ticket.close(t)`. The `MethodType` is a small wrapper object that Python creates on-the-fly every time you access `t.close` — `Ticket.close` is the function stored on the class; `t.close` is a fresh `MethodType` constructed for that access. This is why `t.close is t.close` is `False` — each access creates a new wrapper.

**Why is `t.close is t.close` False even though `t` is the same instance?**

Because each attribute access `t.close` constructs a *new* `MethodType` wrapper. The wrapper is a small, short-lived object whose only state is `__func__` and `__self__`; creating one per access is cheap (one allocation), but it does mean the wrappers are not identical across accesses. If you call `m = t.close; m(); m()` the same wrapper is used twice — but `t.close is t.close` (two separate accesses) is always `False`. This is the same reason `1 + 1` and `1 + 1` produce `2` (the cached int singleton) but `[].append` and `[].append` (two accesses on the same list) are not identical objects — except in the list case the two are equal-but-not-identical because each is a fresh `builtin_function_or_method`.

### Lines 50–54: `types.MethodWrapperType` for dunder wrappers

```python
# 5. types.MethodWrapperType — wrappers around dunders like [].__init__.
print("\n== MethodWrapperType ==")
print("type([].__init__).__name__:", type([].__init__).__name__)
print("isinstance([].__init__, types.MethodWrapperType):", isinstance([].__init__, types.MethodWrapperType))
print("isinstance(().__contains__, types.MethodWrapperType):", isinstance(().__contains__, types.MethodWrapperType))
```

`[].__init__` is a `types.MethodWrapperType` instance — its `type().__name__` is `"method-wrapper"`. This is a *third* kind of "looks like a method" object: a wrapper around a C-level slot dunder (`__init__`, `__contains__`, `__len__`, etc.). The three method-ish types are: `MethodType` (bound method on a *user* class), `BuiltinFunctionType`/`BuiltinMethodType` (C-level function like `len` or `[].append`), `MethodWrapperType` (C-level slot wrapper like `[].__init__`). The distinction matters in metaprogramming: if you write `for name in dir(some_obj): if callable(getattr(some_obj, name)): ...`, you will pick up all three, but you may want to filter `MethodWrapperType` out (those are dunders you usually do not want to call directly).

### Lines 56–63: `types.CodeType` — the `__code__` attribute

```python
# 6. types.CodeType — the __code__ attribute of every function.
print("\n== CodeType ==")
code = my_function.__code__
print("isinstance(code, types.CodeType):", isinstance(code, types.CodeType))
print("type(code).__name__:", type(code).__name__)
print("code.co_argcount:", code.co_argcount)
print("code.co_varnames:", code.co_varnames)
print("code.co_consts:", code.co_consts)
```

`my_function.__code__` is a `types.CodeType` instance — the bytecode object for the function. Its `__name__` is `"code"`. The attributes you read most often are: `co_argcount` (the number of positional arguments, here `1` for `x`); `co_varnames` (the tuple of local variable names, here `('x',)` — argument names come first, then local variables); `co_consts` (the literal constants used in the function body, here `(None, 2)` — `None` is the implicit return default, `2` is the literal from `x * 2`); `co_names` (global-name references used in the body, here `()` — no globals are referenced). These are the same fields the `dis` module reads to disassemble a function. Most production code does not touch `CodeType` directly — but every debugger, profiler, and bytecode-level optimiser does. The `__code__` attribute is also *replaceable* — `my_function.__code__ = some_other_code` swaps the bytecode, which is how some monkey-patching libraries work.

**Why is the `__code__` object exposed at all — is not the function enough?**

Because the function is the *binding* (the bytecode plus the `__globals__` plus the `__defaults__`), and the bytecode is the *recipe* (the actual instructions the interpreter executes). Separating the two lets you do things that would otherwise be impossible: copy a function's bytecode to another function (which is how `functools.wraps` preserves signatures), inspect a function's locals without running it (which is how `inspect` reports the parameter names), and rewrite bytecode for optimisation (which is what the `cython` and `numba` compilers do). The `CodeType` is also the foundation of CPython's execution model — every function call ultimately pushes a frame whose `f_code` is the `CodeType`. You will not touch it daily, but it is the layer the language is built on.

### Lines 65–77: `types.MappingProxyType` — the read-only dict view

```python
# 7. types.MappingProxyType — a read-only view over a dict.
print("\n== MappingProxyType ==")
d = {"open": 1, "in_progress": 2, "closed": 3}
view = types.MappingProxyType(d)
print("type(view).__name__:", type(view).__name__)
print("view['open']:", view["open"])

# Writes raise TypeError.
try:
    view["cancelled"] = 0
    print("write succeeded (unexpected)")
except TypeError as e:
    print("write raised TypeError:", e)

# Reads reflect updates to the underlying dict.
d["cancelled"] = 0
print("after d['cancelled']=0, view reflects:", dict(view))
```

`types.MappingProxyType(d)` returns a `mappingproxy` object — a *read-only view* over the dict `d`. Three facts. (1) `type(view).__name__` is `"mappingproxy"` (lowercase, the user-facing name; the class itself is `types.MappingProxyType`). (2) Writes raise `TypeError: 'mappingproxy' object does not support item assignment` — you cannot add, modify, or delete keys via the view. (3) Reads reflect updates to the underlying dict — `d["cancelled"] = 0` mutates the dict, and `view["cancelled"]` (or `dict(view)`) immediately sees the new key. The view is not a copy; it is a *window* with `__setitem__`/`__delitem__` disabled.

This is the standard library's primitive for "expose a dict's contents without letting callers mutate them". The two big users are `inspect` (for `sig.parameters`, see below) and the `types` module itself (for `MappingProxyType` instances returned by `types.MappingProxyType`). Frameworks that need to expose internal dicts — Pydantic's `ModelField.metadata`, FastAPI's `Depends.__wrapped__` chain — use `MappingProxyType` to enforce the read-only contract.

### Lines 79–90: `sig.parameters` IS a `MappingProxyType`

```python
# 8. THE key example — inspect.signature.parameters IS a MappingProxyType.
print("\n== signature.parameters is a mappingproxy ==")
def get_ticket(id: int, status: str = "open") -> dict:
    return {"id": id, "status": status}

sig = inspect.signature(get_ticket)
print("type(sig.parameters).__name__:", type(sig.parameters).__name__)
print("isinstance(sig.parameters, types.MappingProxyType):", isinstance(sig.parameters, types.MappingProxyType))
print("sig.parameters keys:", list(sig.parameters.keys()))

try:
    sig.parameters["user"] = None
    print("parameters write succeeded (unexpected)")
except TypeError as e:
    print("parameters write raised TypeError:", e)
```

`type(sig.parameters).__name__` is `"mappingproxy"` — the `parameters` attribute of `inspect.Signature` is a `MappingProxyType` wrapping the internal `dict` of `Parameter` objects. Writing to it (`sig.parameters["user"] = None`) raises `TypeError` exactly the same way as the explicit `MappingProxyType(d)` example above. This is not a coincidence — `inspect.Signature` uses `MappingProxyType` to enforce the contract that *callers cannot mutate the signature's parameter list*.

**Why does FastAPI care that `sig.parameters` is a `MappingProxyType`?**

Because FastAPI walks `sig.parameters` to figure out which parameters are path params, query params, dependencies, and body. The walk happens once per route at import time, then again on every request when FastAPI's dependency-resolution machinery needs to know what to inject. If `sig.parameters` were a plain `dict`, a malicious or buggy dependency could mutate it (`sig.parameters["admin_user"] = some_param`) and FastAPI would inject that dependency on the next request — a security-relevant mutation. By returning a `MappingProxyType`, the `inspect` module gives FastAPI a guarantee: "this is what the signature looked like at import time, and nothing the request handler does can change that". The contract is enforced by the type system itself, not by convention. This is exactly the kind of guarantee a framework needs to be safe in production.

### Lines 92–97: The FastAPI connection — what FastAPI reads off `sig.parameters`

```python
# 9. Why FastAPI cares — the parameters object is read-only so nobody can mutate
# FastAPI's view of your signature between the inspect call and the dependency run.
print("\n== The FastAPI connection ==")
print("sig.parameters['id'].name:", sig.parameters["id"].name)
print("sig.parameters['id'].annotation:", sig.parameters["id"].annotation)
print("sig.parameters['id'].kind:", sig.parameters["id"].kind)
print("sig.parameters['status'].default:", sig.parameters["status"].default)
```

For each `Parameter` object in `sig.parameters`, FastAPI reads four attributes. (1) `.name` — the parameter name (here `"id"` and `"status"`); this is the path/query/body key FastAPI looks for in the request. (2) `.annotation` — the type hint (here `int` and `str`); this is what Pydantic uses to validate the inbound value. (3) `.kind` — one of the five `Parameter.kind` values (`POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD`); this tells FastAPI whether the value comes from the path, the query, or the body. (4) `.default` — the default value (here `Parameter.empty` for `id` and `"open"` for `status`); this tells FastAPI whether the parameter is required. Lesson [[10-inspect/06-How-FastAPI-uses-inspect]] walks the full FastAPI walkthrough; this lesson establishes that the `parameters` object FastAPI is reading is a *read-only* `MappingProxyType`, which is the runtime guarantee that lets FastAPI trust its own walk.

## Execution Trace

```bash
$ python boardly/types_runtime.py
== ModuleType ==
isinstance(math, types.ModuleType): True
type(math).__name__: module
isinstance(types, types.ModuleType): True
dynamic module: <module 'dynamic'> type: module
isinstance(mymod, types.ModuleType): True

== FunctionType ==
isinstance(my_function, types.FunctionType): True
isinstance(lambda x: x, types.FunctionType): True
types.LambdaType is types.FunctionType: True

== BuiltinFunctionType ==
isinstance(len, types.BuiltinFunctionType): True
isinstance(print, types.BuiltinFunctionType): True
isinstance([].append, types.BuiltinFunctionType): True
types.BuiltinFunctionType is types.BuiltinMethodType: True
type(len).__name__: builtin_function_or_method

== MethodType ==
isinstance(t.close, types.MethodType): True
type(t.close).__name__: method
t.close.__func__ is Ticket.close: True
t.close.__self__ is t: True

== MethodWrapperType ==
type([].__init__).__name__: method-wrapper
isinstance([].__init__, types.MethodWrapperType): True
isinstance(().__contains__, types.MethodWrapperType): True

== CodeType ==
isinstance(code, types.CodeType): True
type(code).__name__: code
code.co_argcount: 1
code.co_varnames: ('x',)
code.co_consts: (None, 2)

== MappingProxyType ==
type(view).__name__: mappingproxy
view['open']: 1
write raised TypeError: 'mappingproxy' object does not support item assignment
after d['cancelled']=0, view reflects: {'open': 1, 'in_progress': 2, 'closed': 3, 'cancelled': 0}

== signature.parameters is a mappingproxy ==
type(sig.parameters).__name__: mappingproxy
isinstance(sig.parameters, types.MappingProxyType): True
sig.parameters keys: ['id', 'status']
parameters write raised TypeError: 'mappingproxy' object does not support item assignment

== The FastAPI connection ==
sig.parameters['id'].name: id
sig.parameters['id'].annotation: <class 'int'>
sig.parameters['id'].kind: POSITIONAL_OR_KEYWORD
sig.parameters['status'].default: open
```

Three things to verify in this trace. First, `type(math).__name__: module` (not `"ModuleType"`) — the class's user-facing name is the lowercase word. Second, `types.LambdaType is types.FunctionType: True` and `types.BuiltinFunctionType is types.BuiltinMethodType: True` — the two alias pairs are literally `is`-identical. Third, `sig.parameters write raised TypeError` — the read-only contract on `inspect.signature(f).parameters` is enforced at the type-system level by `MappingProxyType`.

## Common Mistakes

### Mistake 1: Treating `sig.parameters` as a mutable dict

```python
import inspect
def f(x, y): pass
sig = inspect.signature(f)
sig.parameters["z"] = "made-up"   # TypeError
```

**Symptom:** `TypeError: 'mappingproxy' object does not support item assignment` at the assignment site.
**Why:** `sig.parameters` is a `MappingProxyType` — a read-only view over the internal dict. The contract is enforced by `types`; you cannot opt out.
**Fix:** Materialise the view into a plain dict if you need to mutate: `params = dict(sig.parameters); params["z"] = ...`. The new `params` is a regular dict you can mutate freely; the original `sig.parameters` is untouched. If you need a *new* `Signature` with the modified parameters, use `sig.replace(parameters=params)` — `inspect.Signature.replace` is the supported way to construct a derived signature.

### Mistake 2: Using `types.LambdaFunctionType` (which does not exist)

```python
import types
isinstance(lambda x: x, types.LambdaFunctionType)  # AttributeError
```

**Symptom:** `AttributeError: module 'types' has no attribute 'LambdaFunctionType'` at the `isinstance` call.
**Why:** The name is `types.LambdaType` — *not* `types.LambdaFunctionType`. Older documentation and some blog posts reference the longer name; the CPython source exposes only the shorter `LambdaType` (which is an alias for `FunctionType` anyway — they are the same class).
**Fix:** Use `types.LambdaType` (the actual name) or, more honestly, `types.FunctionType` — the two are `is`-identical. There is no reason to write `LambdaType` in new code; the alias exists for backwards compatibility only.

### Mistake 3: Confusing `BuiltinFunctionType` with `MethodDescriptorType`

```python
import types
isinstance(list.append, types.BuiltinFunctionType)   # False — surprising!
isinstance(list.append, types.MethodDescriptorType)  # True
```

**Symptom:** `isinstance(list.append, types.BuiltinFunctionType)` is `False` even though `[].append` *is* a `BuiltinFunctionType`.
**Why:** `list.append` (accessed via the *class*, not an instance) is a `MethodDescriptorType` — a C-level descriptor that, when accessed via an instance (`[].append`), returns a `BuiltinFunctionType`. The unbound form (`list.append`) is the descriptor; the bound form (`[].append`) is the bound builtin function. The two are different runtime types.
**Fix:** Test the *bound* form: `isinstance([].append, types.BuiltinFunctionType)` is `True`. For unbound method-descriptors, use `isinstance(list.append, types.MethodDescriptorType)`. If you do not know whether you have the bound or unbound form, test for both: `isinstance(attr, (types.BuiltinFunctionType, types.MethodDescriptorType))`. The same pattern applies to dunder slots (`list.__contains__` is a `WrapperDescriptorType` when unbound).

## Engineering Trade-Offs

**Decision:** Use `isinstance` checks against `types.*Type` constants when you need to discriminate runtime object categories in `boardly`'s introspection code; use `inspect.signature(f).parameters` as a read-only view and materialise via `dict(sig.parameters)` when you need to mutate.
**Both sides:** The alternative is to use `type(x).__name__` string comparisons (`type(x).__name__ == "function"`), but those are slower, fragile across Python versions (the names have changed historically), and miss subclass relationships. The `isinstance` approach is C-level-fast, version-stable, and respects subclassing. For the `sig.parameters` mutation case, the alternative is to walk `dir(some_obj)` and write a custom signature walker — but `inspect` already does this work correctly and produces a `Signature` whose `parameters` is a guaranteed-read-only view. There is no benefit to reinventing it.
**Commitment:** boardly's plugin loader uses `isinstance(attr, types.FunctionType)` to filter user-defined functions (and `isinstance(attr, types.ModuleType)` to skip nested modules). The schema introspection code uses `inspect.signature` directly and never tries to mutate `sig.parameters` — if it needs a modified signature, it uses `sig.replace(parameters=...)`. The two patterns compose: the plugin loader finds the handlers, the schema introspector walks their signatures, and the `MappingProxyType` guarantee makes the walk safe.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/types_runtime.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/types_runtime.py`
2. **Exercise 2 — Construct a module dynamically.** Add `mymod2 = types.ModuleType("mymod2"); mymod2.value = 100` and confirm `isinstance(mymod2, types.ModuleType) is True` and `mymod2.value == 100`. `Verify: python -c "import types; m = types.ModuleType('test'); m.value = 100; print(isinstance(m, types.ModuleType), m.value)"`
3. **Exercise 3 — Read `co_consts` of a real function.** Define `def add(a, b): return a + b + 1` and print `add.__code__.co_consts`. Confirm the tuple contains `(None, 1)` — `None` for the implicit return, `1` for the literal. `Verify: python -c "def add(a, b): return a + b + 1; print(add.__code__.co_consts)"`
4. **Exercise 4 — Materialise `sig.parameters`.** Take `inspect.signature` of any function and try `dict(sig.parameters)`. Confirm the result is a plain `dict` that you can mutate freely — unlike the original `MappingProxyType`. `Verify: python -c "import inspect; def f(x, y): pass; sig = inspect.signature(f); p = dict(sig.parameters); p['z'] = 1; print(type(p).__name__, list(p.keys()))"`
5. **Exercise 5 — Write a plugin loader.** Write `def load_handlers(module)` that returns `{name: attr for name in dir(module) if isinstance(attr, types.FunctionType)}`. Test it against a small module with one function, one class, and one import. Confirm only the function appears in the result. `Verify: python -c "import types; exec('def f(): pass\\nclass C: pass\\nfrom os import getenv', ns := {}); m = types.ModuleType('m'); m.__dict__.update(ns); print({k: type(v).__name__ for k, v in vars(m).items() if isinstance(v, types.FunctionType)})"`

## Verification

```bash
$ python boardly/types_runtime.py
== ModuleType ==
isinstance(math, types.ModuleType): True
type(math).__name__: module
isinstance(types, types.ModuleType): True
dynamic module: <module 'dynamic'> type: module
isinstance(mymod, types.ModuleType): True

== FunctionType ==
isinstance(my_function, types.FunctionType): True
isinstance(lambda x: x, types.FunctionType): True
types.LambdaType is types.FunctionType: True

== BuiltinFunctionType ==
isinstance(len, types.BuiltinFunctionType): True
isinstance(print, types.BuiltinFunctionType): True
isinstance([].append, types.BuiltinFunctionType): True
types.BuiltinFunctionType is types.BuiltinMethodType: True
type(len).__name__: builtin_function_or_method

== MethodType ==
isinstance(t.close, types.MethodType): True
type(t.close).__name__: method
t.close.__func__ is Ticket.close: True
t.close.__self__ is t: True

== MethodWrapperType ==
type([].__init__).__name__: method-wrapper
isinstance([].__init__, types.MethodWrapperType): True
isinstance(().__contains__, types.MethodWrapperType): True

== CodeType ==
isinstance(code, types.CodeType): True
type(code).__name__: code
code.co_argcount: 1
code.co_varnames: ('x',)
code.co_consts: (None, 2)

== MappingProxyType ==
type(view).__name__: mappingproxy
view['open']: 1
write raised TypeError: 'mappingproxy' object does not support item assignment
after d['cancelled']=0, view reflects: {'open': 1, 'in_progress': 2, 'closed': 3, 'cancelled': 0}

== signature.parameters is a mappingproxy ==
type(sig.parameters).__name__: mappingproxy
isinstance(sig.parameters, types.MappingProxyType): True
sig.parameters keys: ['id', 'status']
parameters write raised TypeError: 'mappingproxy' object does not support item assignment

== The FastAPI connection ==
sig.parameters['id'].name: id
sig.parameters['id'].annotation: <class 'int'>
sig.parameters['id'].kind: POSITIONAL_OR_KEYWORD
sig.parameters['status'].default: open
```

If `type(math).__name__: module`, `types.LambdaType is types.FunctionType: True`, and `sig.parameters write raised TypeError` all appear, you have the three headline facts working: modules are instances of `ModuleType`, lambdas and `def`s are the same `FunctionType`, and `inspect.signature(f).parameters` is a read-only `MappingProxyType`.

## Previously Learned Here

- [[12-types/01-NewType]] — `NewType` is a static-only construct; this lesson is the runtime-side counterpart. The two ends of the section: `NewType` for the type-checker, `ModuleType`/`FunctionType` for the runtime.
- [[12-types/02-SimpleNamespace]] — `SimpleNamespace` is the runtime class behind "an object with arbitrary attributes"; `ModuleType` is the runtime class behind "a module" — and a module *is* a namespace with a few extra attributes (`__name__`, `__spec__`, `__file__`).
- [[12-types/03-GenericAlias-and-UnionType]] — the runtime types behind `list[int]` and `int | str`. This lesson is the same shape: the runtime types behind `import` and `def`.
- [[10-inspect/01-signature-and-Parameter]] — `sig.parameters` is a `MappingProxyType`; this lesson reveals the runtime type that lesson 01 of `inspect` only mentioned in passing.

## What's Next

You have finished Section 12 — `types`. The natural next stop is [[13-future/00-future-MOC]] — the `__future__` and `from __future__ import annotations` lessons that build on the runtime-types layer this section established. The `from __future__ import annotations` switch (PEP 563) stringifies every annotation at module-import time, which means `list[int]` is stored as the *string* `"list[int]"` rather than the `types.GenericAlias` object — and tools that walk annotations have to call `typing.get_type_hints` to evaluate the strings back into runtime objects. Lesson [[13-future/03-When-string-annotations-break]] walks the failure modes that arise when this stringification crosses a runtime-introspection boundary like Pydantic or FastAPI's signature walk. Three things to look for in `13-future`:

- `from __future__ import annotations` (PEP 563) — the one-line switch that changes how every annotation is stored.
- PEP 649 vs PEP 563 — the deferred-evaluation alternative that becomes the default in 3.14.
- The specific failure modes: Pydantic models with forward references, FastAPI routes with `Annotated[...]`, and `TypedDict` total=False fields.

Take your time. Type every example. **This is how you learn.**

## Sources

- **types — Dynamic type creation — CPython reference** — https://docs.python.org/3/library/types.html — accessed 2026-10-23 — the canonical reference for `ModuleType`, `FunctionType`, `MethodType`, `CodeType`, `MappingProxyType`, `BuiltinFunctionType`, `MethodWrapperType` — every type covered in this lesson.
- **types.ModuleType — CPython reference** — https://docs.python.org/3/library/types.html#types.ModuleType — accessed 2026-10-23 — the canonical reference for the type of every module, including the `types.ModuleType(name)` constructor for dynamic module creation.
- **types.FunctionType / LambdaType — CPython reference** — https://docs.python.org/3/library/types.html#types.FunctionType — accessed 2026-10-23 — the canonical reference for the type of user-defined functions; documents the `LambdaType` alias explicitly.
- **types.MappingProxyType — CPython reference** — https://docs.python.org/3/library/types.html#types.MappingProxyType — accessed 2026-10-23 — the canonical reference for the read-only dict view, including the explicit statement that writes raise `TypeError`.
- **inspect.Signature.parameters — CPython reference** — https://docs.python.org/3/library/inspect.html#inspect.Signature.parameters — accessed 2026-10-23 — the canonical reference for the `parameters` attribute; documents that it is an ordered mapping of `Parameter` objects (the underlying type is `MappingProxyType`, established in this lesson).
- **types.CodeType — CPython reference** — https://docs.python.org/3/library/types.html#types.CodeType — accessed 2026-10-23 — the canonical reference for the bytecode object's attributes (`co_argcount`, `co_varnames`, `co_consts`, `co_names`).

## What We Learned

- `isinstance(math, types.ModuleType)` is `True` — a module is an *instance* of `ModuleType`, the same way `[1, 2]` is an instance of `list`. `types.ModuleType("name")` constructs one dynamically.
- `isinstance(my_func, types.FunctionType)` is `True` for both `def` and `lambda` — they are the same class. `types.LambdaType` is an alias for `types.FunctionType` (literally `is`-identical).
- `types.BuiltinFunctionType` covers C-level builtins (`len`, `print`) and bound builtin methods (`[].append`); `types.BuiltinMethodType` is an alias.
- `types.MethodType` is for bound methods on user classes — `t.close` has `__func__` (the underlying function) and `__self__` (the bound instance).
- `types.MethodWrapperType` is for C-level dunder wrappers like `[].__init__` and `().__contains__`.
- `types.CodeType` is the type of `function.__code__` — the bytecode object, with `co_argcount`, `co_varnames`, `co_consts`, `co_names`.
- `types.MappingProxyType(d)` is a read-only view over `d` — writes raise `TypeError`, reads reflect updates to `d`.
- `inspect.signature(f).parameters` is a `MappingProxyType` — the read-only contract that lets FastAPI trust its signature walk across request boundaries.
- The five method-ish types are: `MethodType` (user bound), `BuiltinFunctionType` (C-level `len` or `[].append`), `MethodWrapperType` (C-level dunder wrapper), `MethodDescriptorType` (unbound method-descriptor like `list.append`), `WrapperDescriptorType` (unbound dunder slot like `list.__contains__`).
