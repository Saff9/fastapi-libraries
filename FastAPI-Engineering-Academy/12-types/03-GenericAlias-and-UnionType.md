---
title: "Lesson 03: GenericAlias and UnionType"
aliases:
 - GenericAlias
 - types.GenericAlias
 - UnionType
 - types.UnionType
 - get_origin
 - get_args
tags:
 - types
 - genericalias
 - uniontype
 - introspection
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[12-types/01-NewType]]"
 - "[[12-types/02-SimpleNamespace]]"
 - "[[01-typing/01-Type-Hints-Basics]]"
 - "[[01-typing/03-TypeVar-and-Generics]]"
related_lessons:
 - "[[12-types/04-ModuleType-and-FunctionType]]"
 - "[[01-typing/03-TypeVar-and-Generics]]"
 - "[[10-inspect/02-get_type_hints]]"
---

# Lesson 03: GenericAlias and UnionType

*`type(list[int]).__name__` is `"GenericAlias"` and `type(int | str).__name__` is `"UnionType"` — the two runtime types behind `list[int]` and `int | str`, and the `typing.get_origin`/`get_args` helpers that let you introspect either form uniformly.*

**You're at the very beginning of Section 12's type-of-the-type layer.**

You have written `list[int]` a thousand times. You have written `int | str` since Python 3.10. You have not asked — at runtime — *what* those expressions evaluate to. The answer is the lesson. `list[int]` evaluates to a `types.GenericAlias` instance (PEP 585, 3.9+). `int | str` evaluates to a `types.UnionType` instance (PEP 604, 3.10+). These are real objects with attributes you can introspect — `.__origin__`, `.__args__` — and there is a uniform helper pair in `typing` (`get_origin`, `get_args`) that abstracts over both the new builtin forms and the older `typing.List`/`typing.Union` forms. By the end of this lesson you will know the four runtime objects, the helper pair, and why the new forms exist at all. Take your time. Type every example. **This is how you learn.**

#types #genericalias #uniontype #introspection

## Learning Objectives

By the end of this lesson you will be able to:

1. **Identify** the runtime type of `list[int]` — `types.GenericAlias` (PEP 585, 3.9+) — and of `int | str` — `types.UnionType` (PEP 604, 3.10+).
2. **Read** the `.__origin__` and `.__args__` attributes of a `GenericAlias` — `list[int].__origin__ is list`, `list[int].__args__ == (int,)`.
3. **Use** `typing.get_origin` and `typing.get_args` to introspect *either* the new builtin forms (`list[int]`, `int | str`) *or* the older `typing` forms (`typing.List[int]`, `typing.Union[int, str]`).
4. **Explain** the difference between `list[int]` (a `types.GenericAlias`) and `typing.List[int]` (a `typing._GenericAlias`) — and why the difference still matters in 3.12.
5. **Write** a small annotation-walker function (`describe(annotation) -> str`) that recursively renders the structure of any annotation, using `get_origin`/`get_args` to handle the union, sequence, and mapping cases.

## Prerequisites

Before starting, you need:

- **Type hints basics** — [[01-typing/01-Type-Hints-Basics]] for `list[int]` and `X | Y`. You must be comfortable writing both forms.
- **TypeVar and Generics** — [[01-typing/03-TypeVar-and-Generics]] for the *generic* form. `list[int]` *is an instance of* `types.GenericAlias`; the lesson on `TypeVar` covers the parameter side, this lesson covers the type-of-the-type side.
- **The two earlier `12-types` lessons** — [[12-types/01-NewType]] and [[12-types/02-SimpleNamespace]] — for the section's tone and the "types is where the runtime types live" framing.
- **About 30–45 minutes of focused time.**

**The most common gap: conflating `list[int]` and `typing.List[int]`.**

Students arrive having seen both forms and assume they are aliases — `list[int]` is just a newer spelling of `typing.List[int]`. They are not. At runtime, `type(list[int]).__name__` is `"GenericAlias"`; `type(typing.List[int]).__name__` is `"_GenericAlias"`. They are different classes, with different internals, in different modules (`types` vs `typing`). For most introspection tasks the two are interchangeable — `typing.get_origin` and `get_args` abstract over both. But for some edge cases (deep metaclass checks, `isinstance(x, types.GenericAlias)` tests, `__class_getitem__` overrides) the difference still matters. Knowing which form you are holding is the lesson.

## The Problem

Here is the bug. `boardly` has a small introspection helper that walks a function's annotations and decides "is this a sequence type?" — used to generate OpenAPI schemas:

```python
# boardly/schema/bad_walker.py — the bad old days
def is_sequence_type(annotation) -> bool:
    # Hardcoded list of every form the engineer remembered
    return annotation in (list, list[int], typing.List, typing.List[int])

# What about list[str]? list[Ticket]? tuple[int, ...]? set[bytes]?
# What about `int | str`? `int | None`? `list[int] | None`?
# The hardcoded list approach misses everything except the exact forms the engineer wrote down.
```

Three problems. (1) The hardcoded list of "every form we remembered" is incomplete — `list[str]` is *not* in that list (it is a different `GenericAlias` instance), so `is_sequence_type(list[str])` returns `False`. (2) Generic sequences (`list[T]` where `T` is a `TypeVar`) are missed entirely. (3) `int | str | None` is a `UnionType` with three args; the function would have to enumerate every possible subset of types, which is impossible. The right tool is not "enumerate the forms", it is "introspect the structure".

`typing.get_origin` and `typing.get_args` are the standard-library answer:

```python
import typing, types

def is_sequence_type(annotation) -> bool:
    origin = typing.get_origin(annotation)
    return origin in (list, tuple, set, frozenset)

# Now all of these work:
is_sequence_type(list[int])        # True
is_sequence_type(list[str])        # True
is_sequence_type(dict[str, int])   # False
is_sequence_type(int | str)        # False
is_sequence_type(str)              # False
```

`get_origin` returns the *origin* of the annotation — the underlying class for a `GenericAlias` (`list` for `list[int]`), the union marker for a `UnionType` (`types.UnionType` for `int | str`), or `None` for a plain class (`str`, `int`). `get_args` returns the parameter tuple. The pair works uniformly on every form — `list[int]`, `typing.List[int]`, `int | str`, `typing.Union[int, str]`. This is the abstraction FastAPI, Pydantic, and every other introspection-heavy library relies on.

## The Code

```python
# boardly/types_introspection.py
"""boardly — types.GenericAlias and types.UnionType: what `list[int]` and `X | Y` actually are."""
import types
import typing
from typing import List, Union

# 1. The runtime type of `list[int]` is types.GenericAlias (PEP 585, 3.9+).
alias = list[int]
print("alias:", alias)
print("type(alias).__name__:", type(alias).__name__)
print("isinstance(alias, types.GenericAlias):", isinstance(alias, types.GenericAlias))
print("alias.__origin__:", alias.__origin__)
print("alias.__args__:", alias.__args__)

# 2. Multi-parameter generic alias.
pair = dict[str, int]
print("\npair:", pair)
print("pair.__origin__:", pair.__origin__)
print("pair.__args__:", pair.__args__)

# 3. typing.List[int] is a different type — typing._GenericAlias.
t_alias = List[int]
print("\nt_alias:", t_alias)
print("type(t_alias).__name__:", type(t_alias).__name__)
print("isinstance(t_alias, types.GenericAlias):", isinstance(t_alias, types.GenericAlias))

# 4. typing.get_origin / get_args — the abstraction over both.
print("\n--- typing.get_origin / get_args (abstraction over both forms) ---")
print("get_origin(list[int]):   ", typing.get_origin(list[int]))
print("get_args(list[int]):     ", typing.get_args(list[int]))
print("get_origin(List[int]):   ", typing.get_origin(List[int]))
print("get_args(List[int]):     ", typing.get_args(List[int]))

# 5. PEP 604 — `int | str` constructs a types.UnionType (3.10+).
u = int | str
print("\nu:", u)
print("type(u).__name__:", type(u).__name__)
print("isinstance(u, types.UnionType):", isinstance(u, types.UnionType))

# 6. typing.Union[int, str] is a *different* type — typing._UnionGenericAlias.
tu = Union[int, str]
print("\ntu:", tu)
print("type(tu).__name__:", type(tu).__name__)
print("isinstance(tu, types.UnionType):", isinstance(tu, types.UnionType))

# 7. get_origin / get_args work on both — but origin DIFFERS.
print("\n--- get_origin / get_args on unions ---")
print("get_origin(int | str):     ", typing.get_origin(int | str))
print("get_args(int | str):       ", typing.get_args(int | str))
print("get_origin(Union[int, str]):", typing.get_origin(Union[int, str]))
print("get_args(Union[int, str]): ", typing.get_args(Union[int, str]))

# 8. Nested aliases — introspection works recursively.
nested = dict[str, list[int]]
print("\nnested:", nested)
print("nested.__args__:", nested.__args__)
inner = nested.__args__[1]
print("inner.__origin__:", inner.__origin__)
print("inner.__args__:", inner.__args__)

# 9. Practical use: a function that prints the structure of any annotation.
def describe(annotation) -> str:
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is None:
        return getattr(annotation, "__name__", repr(annotation))
    if origin is types.UnionType:
        return " | ".join(describe(a) for a in args)
    origin_name = getattr(origin, "__name__", repr(origin))
    return f"{origin_name}[{', '.join(describe(a) for a in args)}]"

print("\n--- describe() outputs ---")
print("describe(list[int]):            ", describe(list[int]))
print("describe(dict[str, list[int]]): ", describe(dict[str, list[int]]))
print("describe(int | str):           ", describe(int | str))
print("describe(int | str | None):    ", describe(int | str | None))
print("describe(Union[int, str]):     ", describe(Union[int, str]))

# 10. The boardly use-case: a function that says "is this annotation a sequence?".
def is_sequence_type(annotation) -> bool:
    origin = typing.get_origin(annotation)
    return origin in (list, tuple, set, frozenset)

print("\n--- is_sequence_type() ---")
print("list[int]:           ", is_sequence_type(list[int]))
print("dict[str, int]:      ", is_sequence_type(dict[str, int]))
print("int | str:           ", is_sequence_type(int | str))
print("str:                 ", is_sequence_type(str))
```

## Line-by-Line Deep Dive

### Lines 1–9: The runtime type of `list[int]`

```python
# boardly/types_introspection.py
"""boardly — types.GenericAlias and types.UnionType: what `list[int]` and `X | Y` actually are."""
import types
import typing
from typing import List, Union

# 1. The runtime type of `list[int]` is types.GenericAlias (PEP 585, 3.9+).
alias = list[int]
print("alias:", alias)
print("type(alias).__name__:", type(alias).__name__)
```

`list[int]` looks like a class with a subscript, but at runtime it is *not* a class. The expression `list[int]` invokes `list.__class_getitem__(int)`, which returns a `types.GenericAlias` instance. That instance is a runtime object that *describes* "list of int" — it is not a list, it is not a class, it is a *type alias object*. Three attributes matter: `type(alias).__name__` is `"GenericAlias"` (the class name); `alias.__origin__` is the `list` class itself (the underlying builtin); `alias.__args__` is `(int,)` (the type parameters). The `GenericAlias` is the runtime form PEP 585 (3.9+) standardised when it made builtins subscriptable — before 3.9, only `typing.List[int]` worked.

**Why did PEP 585 make `list[int]` work — was `typing.List[int]` not enough?**

`typing.List[int]` worked, but it was slow and ugly. The `typing` module's `_GenericAlias` is a Python-level object that has to handle every typing-specific edge case (covariance, contravariance, `TYPE_CHECKING`-only behaviour, `Optional[X]` shortcuts). PEP 585 made the *builtins* (`list`, `dict`, `tuple`, `set`, `frozenset`) subscriptable directly via a C-level `__class_getitem__` that returns a leaner `types.GenericAlias`. The result is faster construction, smaller memory, and the natural syntax we always wanted. In 3.9+, `typing.List` is a deprecated alias for `list` (and `typing.Dict` for `dict`, etc.) — the `typing` forms are kept for backwards compatibility but new code should use the builtin forms.

### Lines 11–13: The `__origin__` and `__args__` attributes

```python
print("isinstance(alias, types.GenericAlias):", isinstance(alias, types.GenericAlias))
print("alias.__origin__:", alias.__origin__)
print("alias.__args__:", alias.__args__)
```

`alias.__origin__ is list` — the origin of `list[int]` is the `list` class. `alias.__args__ == (int,)` — the type parameters are stored as a tuple. These two attributes are the *primary* introspection surface for a `GenericAlias`. They are also what `typing.get_origin` and `typing.get_args` return — the helpers are essentially thin wrappers over `.__origin__` and `.__args__`, with extra logic for the `typing._GenericAlias` and `typing._UnionGenericAlias` cases. The `isinstance(alias, types.GenericAlias)` check is `True` here — `list[int]` *is an instance of* the `GenericAlias` class, the same way `[1, 2]` is an instance of `list`.

### Lines 15–19: Multi-parameter generic alias

```python
# 2. Multi-parameter generic alias.
pair = dict[str, int]
print("\npair:", pair)
print("pair.__origin__:", pair.__origin__)
print("pair.__args__:", pair.__args__)
```

`dict[str, int].__origin__ is dict` and `dict[str, int].__args__ == (str, int)` — the order of the type parameters matches the order in the subscript. For `dict[K, V]`, the first arg is `K`, the second is `V`. For `tuple[int, str, float]`, the args are `(int, str, float)`. For `tuple[int, ...]` (the variadic tuple form, PEP 585), `__args__` is `(int, Ellipsis)` — `...` is the literal `Ellipsis` singleton. When you walk `__args__` programmatically, you need to handle these cases; `typing.get_args` returns them all the same way.

### Lines 21–25: `typing.List[int]` is a *different* runtime type

```python
# 3. typing.List[int] is a different type — typing._GenericAlias.
t_alias = List[int]
print("\nt_alias:", t_alias)
print("type(t_alias).__name__:", type(t_alias).__name__)
print("isinstance(t_alias, types.GenericAlias):", isinstance(t_alias, types.GenericAlias))
```

`typing.List[int]` evaluates to a `typing._GenericAlias` instance — note the leading underscore, signalling "internal to `typing`". `type(t_alias).__name__` is `"_GenericAlias"`, not `"GenericAlias"`. And `isinstance(t_alias, types.GenericAlias)` is `False` — `typing.List[int]` is *not* an instance of the `types.GenericAlias` class. The two are sibling types, both used to describe "list of int", but they are different classes in different modules. `typing.List` exists for backwards compatibility — new code in 3.9+ should write `list[int]`, not `typing.List[int]`. In 3.12, both still work, but the `typing` form is officially deprecated and may be removed in a future version.

**Why do `list[int]` and `typing.List[int]` produce different runtime objects at all?**

Because they have different histories and different responsibilities. `typing.List[int]` was the original form (PEP 484, 3.5+); it lives in `typing`, is implemented in pure Python, and handles typing-specific concerns like `Optional[X]` shortcuts, `TYPE_CHECKING`-only imports, and forward-reference resolution. `list[int]` was added later (PEP 585, 3.9+) as the "native" form, implemented in C, leaner and faster. The two share an interface — `get_origin` and `get_args` work on both — but they have different metaclasses and different `__class__`. The standard library keeps both for backwards compatibility; the deprecation warning on `typing.List` (since 3.9) tells you the future: `typing.List` will eventually be removed, and `list[int]` is the long-term form.

### Lines 27–32: `get_origin`/`get_args` — the uniform abstraction

```python
# 4. typing.get_origin / get_args — the abstraction over both.
print("\n--- typing.get_origin / get_args (abstraction over both forms) ---")
print("get_origin(list[int]):   ", typing.get_origin(list[int]))
print("get_args(list[int]):     ", typing.get_args(list[int]))
print("get_origin(List[int]):   ", typing.get_origin(List[int]))
print("get_args(List[int]):     ", typing.get_args(List[int]))
```

`typing.get_origin(list[int])` returns `list`; `typing.get_origin(List[int])` *also* returns `list`. Same origin for both forms — the helper normalises. `typing.get_args(list[int])` returns `(int,)`; `typing.get_args(List[int])` *also* returns `(int,)`. Same args. This is why the helper exists: it abstracts over the two different runtime classes so your introspection code does not have to. If you write `if isinstance(annotation, types.GenericAlias):` you only handle the builtin form; if you write `origin = typing.get_origin(annotation)` you handle both. The second form is what production code does.

### Lines 34–39: The PEP 604 union type

```python
# 5. PEP 604 — `int | str` constructs a types.UnionType (3.10+).
u = int | str
print("\nu:", u)
print("type(u).__name__:", type(u).__name__)
print("isinstance(u, types.UnionType):", isinstance(u, types.UnionType))
```

`int | str` invokes `int.__or__(str)` — PEP 604 (3.10+) gave the `int` class an `__or__` method that returns a `types.UnionType` instance. The result is `int | str` (the `__repr__` uses the syntax form, not `UnionType[int, str]`), and `type(u).__name__` is `"UnionType"`. The `UnionType` is a *runtime* object — you can construct one explicitly via `types.UnionType(int, str)`, but nobody does; the syntax form is what you always write. PEP 604 was the PEP that finally gave Python a clean union syntax — before 3.10, the only way to write "int or str" was `typing.Union[int, str]` or `typing.Optional[int]` for the `T | None` case.

### Lines 41–46: `typing.Union[int, str]` is a *different* runtime type

```python
# 6. typing.Union[int, str] is a *different* type — typing._UnionGenericAlias.
tu = Union[int, str]
print("\ntu:", tu)
print("type(tu).__name__:", type(tu).__name__)
print("isinstance(tu, types.UnionType):", isinstance(tu, types.UnionType))
```

`typing.Union[int, str]` evaluates to a `typing._UnionGenericAlias` instance — note again the leading underscore. `type(tu).__name__` is `"_UnionGenericAlias"`, not `"UnionType"`. `isinstance(tu, types.UnionType)` is `False`. The parallel with the `list[int]` vs `typing.List[int]` case is exact: the PEP 604 form (`int | str`) lives in `types`, is implemented in C, and is the long-term form; `typing.Union` is the original (PEP 484) form, kept for backwards compatibility, eventually to be removed. New code should write `int | str`, not `Union[int, str]`.

### Lines 48–54: `get_origin`/`get_args` on unions — origin *differs*

```python
# 7. get_origin / get_args work on both — but origin DIFFERS.
print("\n--- get_origin / get_args on unions ---")
print("get_origin(int | str):     ", typing.get_origin(int | str))
print("get_args(int | str):       ", typing.get_args(int | str))
print("get_origin(Union[int, str]):", typing.get_origin(Union[int, str]))
print("get_args(Union[int, str]): ", typing.get_args(Union[int, str]))
```

`typing.get_origin(int | str)` returns `types.UnionType` — *the class itself*, not a sentinel. This is one of the subtler facts: the "origin" of a `UnionType` is the `UnionType` class. The check you write is therefore `typing.get_origin(annotation) is types.UnionType`. By contrast, `typing.get_origin(Union[int, str])` returns `typing.Union` — a *typing-side sentinel*, distinct from `types.UnionType`. The args are the same (`(int, str)` for both). If you are writing code that needs to distinguish the two union forms (rare), you check the origin; if you just need the args, you call `get_args` and forget the origin. Production code does the latter almost always.

**Why does `typing.get_origin(int | str)` return the *class* `types.UnionType` rather than a sentinel?**

Because `types.UnionType` is itself the "origin" — there is no separate `Union` class for builtin unions the way `typing.Union` is a sentinel for typing-side unions. The PEP 604 design made `UnionType` both the runtime *container* and the *marker* for "this is a union of types joined by `|`". The asymmetry with `typing.Union` is a historical artefact: `typing.Union` was a typing-side marker object long before `types.UnionType` existed, and the helper had to keep returning the same marker for backwards compatibility. New code that needs to check "is this a union?" should write `origin is types.UnionType or origin is typing.Union` — or, more commonly, just call `get_args` and check whether the result is non-empty and the input was not a plain class.

### Lines 56–62: Nested aliases — recursive introspection

```python
# 8. Nested aliases — introspection works recursively.
nested = dict[str, list[int]]
print("\nnested:", nested)
print("nested.__args__:", nested.__args__)
inner = nested.__args__[1]
print("inner.__origin__:", inner.__origin__)
print("inner.__args__:", inner.__args__)
```

`dict[str, list[int]].__args__` is `(str, list[int])` — the second arg is itself a `GenericAlias`. You can recurse: `inner.__origin__ is list`, `inner.__args__ == (int,)`. This is the basis of any annotation-walker: read `__args__` (or `get_args`), and for each element that has a non-`None` origin, recurse. The recursion terminates when `get_origin(arg)` returns `None` — meaning the arg is a plain class (`int`, `str`, `Ticket`) and has no further structure to walk. This is exactly what `describe()` in the next block does.

### Lines 64–74: A practical annotation-walker

```python
# 9. Practical use: a function that prints the structure of any annotation.
def describe(annotation) -> str:
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is None:
        return getattr(annotation, "__name__", repr(annotation))
    if origin is types.UnionType:
        return " | ".join(describe(a) for a in args)
    origin_name = getattr(origin, "__name__", repr(origin))
    return f"{origin_name}[{', '.join(describe(a) for a in args)}]"

print("\n--- describe() outputs ---")
print("describe(list[int]):            ", describe(list[int]))
print("describe(dict[str, list[int]]): ", describe(dict[str, list[int]]))
print("describe(int | str):           ", describe(int | str))
print("describe(int | str | None):    ", describe(int | str | None))
print("describe(Union[int, str]):     ", describe(Union[int, str]))
```

`describe(list[int])` returns `"list[int]"`. `describe(dict[str, list[int]])` returns `"dict[str, list[int]]"` — note the recursion: the inner `list[int]` is itself rendered by a recursive call. `describe(int | str)` returns `"int | str"` (the special case for `origin is types.UnionType`). `describe(int | str | None)` returns `"int | str | NoneType"` — note that `None` in a `X | None` is converted at parse time to `types.NoneType` (3.10+), which `describe` renders as `"NoneType"`. This is correct behaviour: `None` *is* `types.NoneType` at the type level since 3.10.

`describe(Union[int, str])` returns `"Union[int, str]"` — the typing-side form is rendered with `typing.Union` as the origin, which `getattr(origin, "__name__")` gives as `"Union"`. The asymmetry between `int | str` (rendered as `"int | str"`) and `Union[int, str]` (rendered as `"Union[int, str]"`) is a side-effect of the two different runtime origins; a more complete `describe` could special-case `origin is typing.Union` to also render with `" | "`.

### Lines 76–83: The boardly `is_sequence_type` helper

```python
# 10. The boardly use-case: a function that says "is this annotation a sequence?".
def is_sequence_type(annotation) -> bool:
    origin = typing.get_origin(annotation)
    return origin in (list, tuple, set, frozenset)

print("\n--- is_sequence_type() ---")
print("list[int]:           ", is_sequence_type(list[int]))
print("dict[str, int]:      ", is_sequence_type(dict[str, int]))
print("int | str:           ", is_sequence_type(int | str))
print("str:                 ", is_sequence_type(str))
```

`is_sequence_type(list[int])` returns `True` because `typing.get_origin(list[int]) is list`. `is_sequence_type(dict[str, int])` returns `False` because the origin is `dict`, not in the sequence tuple. `is_sequence_type(int | str)` returns `False` because the origin is `types.UnionType`, not a sequence type. `is_sequence_type(str)` returns `False` because `typing.get_origin(str)` is `None` — `str` is a plain class, not a `GenericAlias`. This is the canonical pattern: check the origin against a tuple of known origins, and you handle every parameterisation (`list[int]`, `list[str]`, `list[Ticket]`, `list[T]`) with one line.

**Why does `is_sequence_type(str)` return `False` — `str` is a sequence of characters?**

Because at the type-system level, `str` is a plain class — `typing.get_origin(str)` is `None`. The `str` class *is* iterable and subscriptable (`s[0]`, `for c in s`), so by the runtime `Sequence` ABC it qualifies — but the *annotation* `str` is not a parameterised generic. If you want to treat `str` as a sequence for schema purposes, you add it to the tuple explicitly: `return origin in (list, tuple, set, frozenset) or annotation is str`. FastAPI's schema generator handles this case — `str` becomes `{"type": "string"}` in OpenAPI, not `{"type": "array"}`, even though `str` is iterable at runtime. The type-system view and the runtime view diverge here, and the schema generator's job is to honour the type-system view.

## Execution Trace

```bash
$ python boardly/types_introspection.py
alias: list[int]
type(alias).__name__: GenericAlias
isinstance(alias, types.GenericAlias): True
alias.__origin__: <class 'list'>
alias.__args__: (<class 'int'>,)

pair: dict[str, int]
pair.__origin__: <class 'dict'>
pair.__args__: (<class 'str'>, <class 'int'>)

t_alias: typing.List[int]
type(t_alias).__name__: _GenericAlias
isinstance(t_alias, types.GenericAlias): False

--- typing.get_origin / get_args (abstraction over both forms) ---
get_origin(list[int]):    <class 'list'>
get_args(list[int]):      (<class 'int'>,)
get_origin(List[int]):    <class 'list'>
get_args(List[int]):      (<class 'int'>,)

u: int | str
type(u).__name__: UnionType
isinstance(u, types.UnionType): True

tu: typing.Union[int, str]
type(tu).__name__: _UnionGenericAlias
isinstance(tu, types.UnionType): False

--- get_origin / get_args on unions ---
get_origin(int | str):      <class 'types.UnionType'>
get_args(int | str):        (<class 'int'>, <class 'str'>)
get_origin(Union[int, str]): typing.Union
get_args(Union[int, str]):  (<class 'int'>, <class 'str'>)

nested: dict[str, list[int]]
nested.__args__: (<class 'str'>, list[int])
inner.__origin__: <class 'list'>
inner.__args__: (<class 'int'>,)

--- describe() outputs ---
describe(list[int]):             list[int]
describe(dict[str, list[int]]):  dict[str, list[int]]
describe(int | str):            int | str
describe(int | str | None):     int | str | NoneType
describe(Union[int, str]):      Union[int, str]

--- is_sequence_type() ---
list[int]:            True
dict[str, int]:       False
int | str:           False
str:                 False
```

Three things to verify in this trace. First, `type(alias).__name__: GenericAlias` and `type(t_alias).__name__: _GenericAlias` — the two *different* runtime classes for the two forms. Second, `get_origin(int | str): <class 'types.UnionType'>` — the origin of a PEP 604 union is the `UnionType` class itself, not a sentinel. Third, `describe(int | str | None): int | str | NoneType` — `None` becomes `types.NoneType` at parse time, and `describe` renders the class name (the special case for `origin is types.UnionType` handles the join).

## Common Mistakes

### Mistake 1: Using `isinstance(annotation, types.GenericAlias)` and missing the `typing` forms

```python
import types
from typing import List

def is_generic(annotation) -> bool:
    return isinstance(annotation, types.GenericAlias)  # misses typing.List[int]

is_generic(list[int])        # True
is_generic(List[int])       # False — surprising
```

**Symptom:** `is_generic(List[int])` returns `False` even though `List[int]` is clearly a parameterised generic.
**Why:** `typing.List[int]` is an instance of `typing._GenericAlias`, not `types.GenericAlias`. The two are different classes — PEP 585 added `types.GenericAlias` as the leaner, C-level form; `typing._GenericAlias` is the older Python-level form.
**Fix:** Use `typing.get_origin(annotation) is not None` instead — it returns `True` for *both* forms and any other parameterised type. The `isinstance` check only works if you have explicitly opted into the builtin-only world.

### Mistake 2: Treating `int | str` and `Union[int, str]` as the same object

```python
import typing
a = int | str
b = typing.Union[int, str]
print(a is b)             # False
print(type(a) is type(b)) # False — different classes
print(a == b)             # True (they compare equal — both are "int or str")
```

**Symptom:** `a is b` is `False` even though the two look identical; `type(a) is type(b)` is `False`; only `a == b` is `True`.
**Why:** The two are different runtime objects of different classes. They compare equal because both implement `__eq__` to mean "same set of types", but their identities and types differ. This means `is` checks fail across the boundary.
**Fix:** Use `==` for equality, never `is`, when comparing union objects. Or — better — compare the *structure* via `get_origin`/`get_args` rather than the objects themselves: `typing.get_args(a) == typing.get_args(b)` is the structural check.

### Mistake 3: Forgetting that `None` becomes `types.NoneType` in a `X | None`

```python
import types, typing

ann = int | None
args = typing.get_args(ann)
print(args)               # (<class 'int'>, <class 'NoneType'>)
print(args[1] is None)    # False — surprising!
print(args[1] is types.NoneType)  # True
```

**Symptom:** You walk the args of `int | None` and the second element is *not* `None` — it is `types.NoneType`.
**Why:** Since Python 3.10, `None` in a type-annotation context (specifically `X | None`) is converted at parse time to `types.NoneType` (the class of `None`). The `None` *value* is never stored in a `UnionType`'s args — the class is. This mirrors how `True` and `False` are stored as `bool` rather than the literal values in some contexts.
**Fix:** When walking union args, check for `types.NoneType` (the class), not `None` (the value): `if arg is types.NoneType: ...` or `if arg is type(None): ...` (the two are equivalent — `type(None) is types.NoneType`).

## Engineering Trade-Offs

**Decision:** Use the builtin forms (`list[int]`, `int | str`) everywhere in boardly; reserve `typing.List`/`typing.Union` for compatibility shims with old code only. Use `typing.get_origin`/`get_args` for every introspection task; never write `isinstance(x, types.GenericAlias)` in production introspection code.
**Both sides:** The alternative is to keep using `typing.List[int]` and `typing.Union[int, str]` everywhere — they still work, after all, and the difference is invisible to most code. The cost is uglier syntax, slower construction (the Python-level `typing._GenericAlias` is slower than the C-level `types.GenericAlias`), and a future deprecation cliff — `typing.List` has been deprecated since 3.9 and will eventually be removed. For introspection, the alternative to `get_origin`/`get_args` is to walk `.__origin__`/`.__args__` directly, but that misses the `typing` forms entirely (they have different attribute names in some cases).
**Commitment:** boardly uses the builtin forms exclusively. The introspection code in `boardly/schema/introspect.py` uses `typing.get_origin` and `typing.get_args` for every annotation walk — the two helpers handle both the builtin and the `typing` forms uniformly, and the code never needs to know which form was used at the call site. The FastAPI request-schema generator in `boardly/api/schema.py` uses the same pattern; this is the canonical FastAPI approach.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/types_introspection.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/types_introspection.py`
2. **Exercise 2 — Add `tuple[int, str, float]`.** Add a `triple = tuple[int, str, float]` line and print `triple.__args__`. Confirm the args are `(int, str, float)` in order. `Verify: python -c "from boardly.types_introspection import triple" 2>&1; python -c "print(tuple[int, str, float].__args__)"`
3. **Exercise 3 — Handle the variadic tuple.** Add `var_tup = tuple[int, ...]` and print `var_tup.__args__`. Confirm the args are `(int, Ellipsis)` — the literal `Ellipsis` singleton. Extend `describe()` to render this as `"tuple[int, ...]"` rather than `"tuple[int, Ellipsis]"`. `Verify: python -c "print(tuple[int, ...].__args__)"`
4. **Exercise 4 — Special-case `typing.Union` in `describe`.** Extend `describe()` to handle the `typing.Union` origin (rendered with ` | ` instead of `Union[...]`), so that `describe(Union[int, str])` returns `"int | str"` instead of `"Union[int, str]"`. `Verify: python -c "from boardly.types_introspection import describe; from typing import Union; print(describe(Union[int, str]))"`
5. **Exercise 5 — Build an `is_optional` helper.** Write `def is_optional(annotation) -> bool` that returns `True` iff the annotation is a union of exactly two args, one of which is `types.NoneType`. Test it on `int | None` (True), `int | str` (False), `int` (False), `int | str | None` (False — three args). `Verify: python -c "from boardly.types_introspection import is_optional; print(is_optional(int | None), is_optional(int | str), is_optional(int))"`

## Verification

```bash
$ python boardly/types_introspection.py
alias: list[int]
type(alias).__name__: GenericAlias
isinstance(alias, types.GenericAlias): True
alias.__origin__: <class 'list'>
alias.__args__: (<class 'int'>,)

pair: dict[str, int]
pair.__origin__: <class 'dict'>
pair.__args__: (<class 'str'>, <class 'int'>)

t_alias: typing.List[int]
type(t_alias).__name__: _GenericAlias
isinstance(t_alias, types.GenericAlias): False

--- typing.get_origin / get_args (abstraction over both forms) ---
get_origin(list[int]):    <class 'list'>
get_args(list[int]):      (<class 'int'>,)
get_origin(List[int]):    <class 'list'>
get_args(List[int]):      (<class 'int'>,)

u: int | str
type(u).__name__: UnionType
isinstance(u, types.UnionType): True

tu: typing.Union[int, str]
type(tu).__name__: _UnionGenericAlias
isinstance(tu, types.UnionType): False

--- get_origin / get_args on unions ---
get_origin(int | str):      <class 'types.UnionType'>
get_args(int | str):        (<class 'int'>, <class 'str'>)
get_origin(Union[int, str]): typing.Union
get_args(Union[int, str]):  (<class 'int'>, <class 'str'>)

nested: dict[str, list[int]]
nested.__args__: (<class 'str'>, list[int])
inner.__origin__: <class 'list'>
inner.__args__: (<class 'int'>,)

--- describe() outputs ---
describe(list[int]):             list[int]
describe(dict[str, list[int]]):  dict[str, list[int]]
describe(int | str):            int | str
describe(int | str | None):     int | str | NoneType
describe(Union[int, str]):      Union[int, str]

--- is_sequence_type() ---
list[int]:            True
dict[str, int]:       False
int | str:           False
str:                 False
```

If `type(alias).__name__: GenericAlias`, `type(t_alias).__name__: _GenericAlias`, and `get_origin(int | str): <class 'types.UnionType'>` all appear, you have the four runtime objects (`GenericAlias`, `_GenericAlias`, `UnionType`, `_UnionGenericAlias`) distinguished and the helper pair working on all four.

## Previously Learned Here

- [[12-types/01-NewType]] — `NewType` is a static-only construct; this lesson is the runtime-side counterpart. The two together: `NewType` is what you do when you want a *type-checker-facing* nominal alias; `GenericAlias` and `UnionType` are what those type-checker-facing constructs *evaluate to* at runtime when you write `list[UserId]` or `UserId | None`.
- [[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T")` constructs a *parameter*; `list[int]` constructs a `GenericAlias` *instance*. The two are siblings: `TypeVar` is what you put inside the brackets when you do not know the type yet; `GenericAlias` is the runtime object produced when the brackets are filled in.
- [[10-inspect/02-get_type_hints]] — `get_type_hints` returns a dict of annotations whose values are these `GenericAlias` and `UnionType` instances — the introspection surface this lesson walks is what FastAPI receives from `get_type_hints(func, include_extras=True)`.

## What's Next

[[12-types/04-ModuleType-and-FunctionType]] — the final lesson in this section is the runtime types behind the language constructs you use every day. `import math` makes `math` an instance of `types.ModuleType`; `def f(): ...` makes `f` an instance of `types.FunctionType`; `obj.method` is a `types.MethodType`; the `__code__` attribute of a function is a `types.CodeType`; `inspect.signature(f).parameters` is a `types.MappingProxyType` (a read-only dict view). Three things to look for in lesson 04:

- `isinstance(math, types.ModuleType) is True` — modules are *instances* of a class, just like every other object.
- `types.FunctionType` (and its alias `types.LambdaType` — same class) for user-defined functions, `types.BuiltinFunctionType` for `len`/`print`, `types.MethodType` for bound methods on user classes.
- `types.MappingProxyType` is the read-only dict view that `inspect.signature(f).parameters` returns — and the reason no caller can mutate FastAPI's view of your route's signature.

Take your time. Type every example. **This is how you learn.**

## Sources

- **types.GenericAlias — CPython reference** — https://docs.python.org/3/library/types.html#types.GenericAlias — accessed 2026-10-23 — the canonical reference for the runtime type of `list[int]`, including the `__origin__` and `__args__` attributes.
- **types.UnionType — CPython reference** — https://docs.python.org/3/library/types.html#types.UnionType — accessed 2026-10-23 — the canonical reference for the runtime type of `int | str` (PEP 604).
- **typing.get_origin / get_args — CPython reference** — https://docs.python.org/3/library/typing.html#typing.get_origin — accessed 2026-10-23 — the helper pair that abstracts over both the builtin and `typing` forms of generic aliases and unions.
- **PEP 585 — Generics in standard collections** — https://peps.python.org/pep-0585/ — accessed 2026-10-23 — the 3.9 PEP that made `list[int]` work and introduced `types.GenericAlias`.
- **PEP 604 — New Type Union** — https://peps.python.org/pep-0604/ — accessed 2026-10-23 — the 3.10 PEP that introduced `int | str` and `types.UnionType`.
- **types — Dynamic type creation — CPython reference** — https://docs.python.org/3/library/types.html — accessed 2026-10-23 — the section home for all the runtime types this section covers.

## What We Learned

- `list[int]` evaluates to a `types.GenericAlias` instance (PEP 585, 3.9+) — `type(list[int]).__name__ == "GenericAlias"`.
- `int | str` evaluates to a `types.UnionType` instance (PEP 604, 3.10+) — `type(int | str).__name__ == "UnionType"`.
- `typing.List[int]` is a *different* runtime type (`typing._GenericAlias`) from `list[int]` (`types.GenericAlias`); `typing.Union[int, str]` is a *different* runtime type (`typing._UnionGenericAlias`) from `int | str` (`types.UnionType`). New code should use the builtin forms.
- `typing.get_origin(list[int])` returns `list`; `typing.get_args(list[int])` returns `(int,)`. The same helpers work on the `typing` forms and on unions.
- `typing.get_origin(int | str)` returns the `types.UnionType` class itself; `typing.get_origin(Union[int, str])` returns `typing.Union`. The asymmetry is a historical artefact — production code uses `get_args` and checks the args.
- `None` in a `X | None` becomes `types.NoneType` at parse time — when walking union args, check for the class, not the value.
- The canonical annotation-walker pattern is `origin = get_origin(ann); args = get_args(ann); if origin is None: return plain; else: recurse on args`. This is what FastAPI, Pydantic, and every introspection-heavy library use.
