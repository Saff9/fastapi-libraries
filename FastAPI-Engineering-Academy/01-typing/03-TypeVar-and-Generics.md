---
title: "Lesson 03: TypeVar and Generics"
aliases:
 - TypeVar and Generics
 - 03-TypeVar-and-Generics
 - TypeVar
 - Generic
tags:
 - typing
 - typevar
 - generic
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "40–55 minutes"
prerequisites:
 - "[[01-typing/01-Type-Hints-Basics]]"
related_lessons:
 - "[[01-typing/02-Annotated-and-Metadata]]"
 - "[[01-typing/04-ParamSpec-and-TypeVarTuple]]"
 - "[[01-typing/05-Protocol-Structural-Typing]]"
first_taught_in: "01-typing/03-TypeVar-and-Generics"
---

# Lesson 03: TypeVar and Generics

*`TypeVar("T")` — the symbol that lets one function or class work on `int`, `str`, or `Ticket` while still telling the type-checker exactly which one was used at the call site.*

**You're at the very beginning of Section 01's generics vocabulary.**

You can write `list[int]` (lesson 01). You can attach metadata with `Annotated[T, ...]` (lesson 02). But what if you want a `Stack` class that holds *whatever the caller chooses* — sometimes `int`, sometimes `str`, sometimes a `Ticket` — and you want the type-checker to *track* which one? That is what `TypeVar` is for. It is the parameter of a generic. Once you have a `TypeVar`, you can build `Stack[T]`, `Repository[T, ID]`, and `peek_top(stack: Stack[T]) -> T | None` — and mypy knows that if you passed in a `Stack[int]`, the return is `int | None`, not `object | None`. Take your time. Type every example. **This is how you learn.**

#typing #typevar #generic #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Declare** a `TypeVar("T")`, a bounded `TypeVar("T", bound=X)`, and a constrained `TypeVar("T", str, bytes)` — and explain the difference at the call site.
2. **Define** a generic class `class Stack(Generic[T])` and subscript it as `Stack[int]` at the use site.
3. **Write** a generic function `def peek_top(stack: Stack[T]) -> T | None` that mypy narrows correctly based on the argument's concrete type parameter.
4. **Inspect** a `TypeVar` object's `__bound__` and `__constraints__` attributes to know which form was used.
5. **Explain** when to use a `bound` versus `constraints` and why the two are *not* interchangeable.

## Prerequisites

Before starting, you need:

- **[[01-typing/01-Type-Hints-Basics]]** — you must be comfortable with `list[int]` and `get_type_hints`.
- **About 40–55 minutes of focused time.**

**The most common gap: confusing `bound` and `constraints`.**

Students arrive having seen both `TypeVar("T", bound=Shape)` and `TypeVar("T", str, bytes)` and treat them as interchangeable. They are not. `bound=Shape` means "T can be `Shape` *or any subclass* of `Shape`". `TypeVar("T", str, bytes)` means "T can be `str` *or* `bytes` — and nothing else, including no subclasses of `str`". The two are categorically different kinds of restriction, and getting them backwards is the most common `TypeVar` bug.

## The Problem

Here is the bug this lesson prevents. boardly has a generic `Stack` class:

```python
class Stack:
    def __init__(self) -> None:
        self._items: list[object] = []
    def push(self, x: object) -> None:
        self._items.append(x)
    def pop(self) -> object:
        return self._items.pop()
```

The engineer uses `object` because they want the stack to hold "anything". They write `s = Stack(); s.push(1); x = s.pop()` and `x` has type `object`. To use it as an `int`, they have to cast or `isinstance`-check on every pop. Worse: nothing stops someone from pushing a `str` onto a stack that the engineer *thought* held only `ints`. The type system has lost information — it knows only "object", not "int".

`TypeVar` fixes both problems:

```python
T = TypeVar("T")
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, x: T) -> None:
        self._items.append(x)
    def pop(self) -> T:
        return self._items.pop()
```

Now `Stack[int]` declares "this is a stack of ints". `push` only accepts `int`; `pop` returns `int` without a cast. The type-checker tracks the parameter from the call site through every method. That is the entire point of generics: capture the type parameter at the call site and propagate it.

## The Code

```python
# boardly/typevar_generics.py
"""boardly — TypeVar and Generic: parameterised types that stay type-correct."""
from typing import TypeVar, Generic, get_type_hints

# Unbounded TypeVar — any type allowed.
T = TypeVar("T")

# Bounded TypeVar — must be a subtype of the bound.
class Shape:
    area: float = 0.0

class Circle(Shape):
    def __init__(self, r: float) -> None:
        self.area = 3.14 * r * r

class Ticket(Shape):
    def __init__(self, tid: int) -> None:
        self.area = float(tid)

ShapeT = TypeVar("ShapeT", bound=Shape)

# Constrained TypeVar — must be one of exactly these types (no subtypes).
StrOrBytes = TypeVar("StrOrBytes", str, bytes)

# Generic class — a type-parameterised container.
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, x: T) -> None:
        self._items.append(x)
    def pop(self) -> T:
        return self._items.pop()
    def __len__(self) -> int:
        return len(self._items)

# A bounded generic — a stack that only holds Shape subclasses.
class ShapeStack(Generic[ShapeT]):
    def __init__(self) -> None:
        self._items: list[ShapeT] = []
    def push(self, s: ShapeT) -> None:
        self._items.append(s)
    def total_area(self) -> float:
        return sum(s.area for s in self._items)

# A generic function — works on any stack.
def peek_top(stack: Stack[T]) -> T | None:
    return stack._items[-1] if stack._items else None

if __name__ == "__main__":
    # Unbounded: a stack of ints, a stack of strs — both type-check.
    ints: Stack[int] = Stack()
    ints.push(1)
    ints.push(2)
    print("ints pop:", ints.pop())

    strs: Stack[str] = Stack()
    strs.push("a")
    strs.push("b")
    print("strs pop:", strs.pop())

    # peek_top returns int | None when called on Stack[int].
    print("peek ints:", peek_top(ints))
    print("peek strs:", peek_top(strs))

    # Bounded: a ShapeStack that holds Circle and Ticket (both Shape subclasses).
    shapes: ShapeStack[Shape] = ShapeStack()
    shapes.push(Circle(1.0))
    shapes.push(Ticket(42))
    print("total area:", shapes.total_area())

    # The TypeVar object is its own type at runtime.
    print("T is:", T)
    print("ShapeT bound:", ShapeT.__bound__)
    print("StrOrBytes constraints:", StrOrBytes.__constraints__)
```

## Line-by-Line Deep Dive

### Lines 1–6: Module header and the unbounded `TypeVar`

```python
# boardly/typevar_generics.py
"""boardly — TypeVar and Generic: parameterised types that stay type-correct."""
from typing import TypeVar, Generic, get_type_hints

# Unbounded TypeVar — any type allowed.
T = TypeVar("T")
```

`TypeVar("T")` constructs a `TypeVar` object. The string `"T"` is the *name* the type-checker and the repr use — it is *not* a class name, *not* a value, *not* a forward reference. It is purely the display label. (Python's `repr(T)` is `~T` — the tilde is `typing`'s marker for a TypeVar.) Without the name, mypy cannot display meaningful errors. Always name your TypeVar with the same identifier you assign it to — `T = TypeVar("T")`, not `T = TypeVar("U")`. The latter is technically legal but produces errors like `TypeVar "U" cannot be satisfied` which the reader has to mentally translate to "T".

`TypeVar("T")` with no further arguments is *unbounded* — it accepts any type. That is the loosest possible form. Use it when you genuinely have no opinion about what the type parameter should be (e.g., the `Stack` container — it just holds things).

**Why does `TypeVar` need a string name when we already have a variable name?**

Because `TypeVar` constructs an object, and the variable name (`T`) is the Python-side binding. The string `"T"` is what the TypeVar *calls itself* when printed. They are independent. The string is also what mypy uses internally to refer to the TypeVar in error messages. Mismatching them (`X = TypeVar("Y")`) is legal but confusing — and tools that emit error messages (mypy, pyright) will use the string, not the variable, so the error refers to a name the reader cannot find.

### Lines 8–18: The `Shape` hierarchy used as a bound

```python
# Bounded TypeVar — must be a subtype of the bound.
class Shape:
    area: float = 0.0

class Circle(Shape):
    def __init__(self, r: float) -> None:
        self.area = 3.14 * r * r

class Ticket(Shape):
    def __init__(self, tid: int) -> None:
        self.area = float(tid)
```

We need a small class hierarchy to demonstrate a *bound*. `Shape` is the base; `Circle` and `Ticket` are subclasses (yes, a `Ticket` is-a `Shape` in boardly's geometry-themed demo — area is "screen area used"). Both subclasses set `self.area` in `__init__`. The base class declares `area: float = 0.0` as a class-level default, so any subclass that forgets to set it has a sensible fallback rather than an `AttributeError`.

**Why does the bound need a real class hierarchy?**

Because `bound=Shape` means "T must be `Shape` or a subclass". Without `Shape` and at least one subclass, the bound is meaningless. The pattern is: define a base class (or `Protocol`, lesson 05) that captures the *minimum interface* your generic needs, then bound the TypeVar to it. The bound is your contract with the type-checker: "anything you let through this TypeVar has at least the methods and attributes of the bound."

### Line 20: The bounded TypeVar

```python
ShapeT = TypeVar("ShapeT", bound=Shape)
```

`TypeVar("ShapeT", bound=Shape)` is the *bounded* form. `ShapeT` will accept `Shape`, `Circle`, `Ticket`, or any future subclass — but not `int`, `str`, or anything outside the hierarchy. The `bound=` keyword is the only way to express this; `TypeVar("ShapeT", Shape)` (without the keyword) would be *constraints*, not a bound — a categorically different thing.

The `.__bound__` attribute on a bounded TypeVar stores the bound class: `ShapeT.__bound__ is Shape` is `True`. We print this at the bottom of the file to make the introspection visible.

**Why is `bound` strictly more permissive than constraints?**

Because `bound` means "T must be `Shape` *or a subclass*" — including subclasses that did not exist when the bound was written. The bound is *open* — extensible. Constraints, by contrast, are *closed* — `TypeVar("T", str, bytes)` means "T must be exactly `str` or exactly `bytes`", and a future `class MyStr(str): ...` is *not* accepted. This is the most surprising thing about constraints: they exclude subclasses. Choose `bound` when you want extension; choose constraints when you want a closed set.

### Line 23: The constrained TypeVar

```python
# Constrained TypeVar — must be one of exactly these types (no subtypes).
StrOrBytes = TypeVar("StrOrBytes", str, bytes)
```

`TypeVar("StrOrBytes", str, bytes)` is the *constrained* form. The second and onwards positional arguments (here, `str, bytes`) are the *constraints* — the closed set of types `StrOrBytes` will accept. The `.__constraints__` attribute stores them as a tuple: `StrOrBytes.__constraints__ == (str, bytes)`. We print this at the bottom.

When you use a constrained TypeVar in a function body, mypy treats the TypeVar as the *first common supertype* of the constraints — for `str` and `bytes`, that is `str | bytes` semantically, but mypy actually treats it as a special "Union-like" TypeVar that only exposes methods common to all constraints. In practice, a constrained TypeVar's methods are the intersection of the constraints' methods — for `str` and `bytes`, you get the bytes/str-protocol methods (decode, split, join, etc.).

**Why ever use constraints over a plain `Union[str, bytes]`?**

Two reasons. (1) A `Union[str, bytes]` argument accepts both, but the *return type* is also `Union[str, bytes]` — the type-checker loses track of which was passed in. A constrained TypeVar tracks: if the caller passed a `str`, the return is `str`. (2) Constraints let you say "this function works on either `str` or `bytes`, but not a mix" — `Union[str, bytes]` allows `str` for one argument and `bytes` for another. The standard-library `os.PathLike` protocol internally uses a constrained TypeVar for exactly this reason.

### Lines 25–33: The unbounded generic class

```python
# Generic class — a type-parameterised container.
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, x: T) -> None:
        self._items.append(x)
    def pop(self) -> T:
        return self._items.pop()
    def __len__(self) -> int:
        return len(self._items)
```

Three things happen here. (1) `class Stack(Generic[T])` declares `Stack` as a generic class parameterised by `T`. The `Generic[T]` base is the *marker* — it tells the type system that `Stack` has one type parameter, `T`. (2) Inside the class, `T` is usable as a type — `self._items: list[T]` and `def push(self, x: T) -> None` and `def pop(self) -> T`. The type-checker tracks `T` through every method. (3) At the call site, `Stack[int]()` creates an instance of `Stack` "specialised" to `int`. From that point, `push` only accepts `int` and `pop` returns `int`.

`Generic` is itself a class in `typing`. Subclassing it (with a TypeVar in square brackets) is the *only* standard way to declare a generic class in 3.12. (PEP 695's `class Stack[T]:` syntax is 3.12+ — covered in the Trade-Offs section. We do not use it in boardly because we want 3.10-compatible code.)

**Why must I write `Generic[T]` and not just `class Stack:`?**

Because the type-checker needs to know that `Stack` is generic *and* which TypeVars are its parameters. `class Stack:` looks like an ordinary class. `class Stack(Generic[T]):` is the explicit declaration. Without it, mypy treats `Stack` as a non-generic class and `Stack[int]()` is a type error.

### Lines 35–42: The bounded generic class

```python
# A bounded generic — a stack that only holds Shape subclasses.
class ShapeStack(Generic[ShapeT]):
    def __init__(self) -> None:
        self._items: list[ShapeT] = []
    def push(self, s: ShapeT) -> None:
        self._items.append(s)
    def total_area(self) -> float:
        return sum(s.area for s in self._items)
```

`ShapeStack(Generic[ShapeT])` uses the *bounded* TypeVar `ShapeT`. This means at the call site, you can write `ShapeStack[Shape]()` or `ShapeStack[Circle]()` — both are legal — but `ShapeStack[int]()` is a type error. Inside `total_area`, `s.area` is legal because the bound `Shape` declares `area`, so mypy knows every `ShapeT` has it. That is the *point* of a bound: it lets you call methods and access attributes on `T` inside the generic.

**Why is `total_area(self) -> float` not generic in the return?**

Because the return value is `float` regardless of which `ShapeT` was used. The bound says "every `ShapeT` has an `area` of type `float`" — summing them gives a `float`. If `area` had a generic type itself (say, `area: AreaT`), then `total_area` would return `AreaT` and the return type would be generic. The principle: the *bound* declares the contract; the body uses what the contract guarantees; the return type tracks what the body computes.

### Lines 44–46: The generic function

```python
# A generic function — works on any stack.
def peek_top(stack: Stack[T]) -> T | None:
    return stack._items[-1] if stack._items else None
```

A *generic function* does not need `Generic` in the signature — the presence of a free `TypeVar` (`T`) in the signature is enough. mypy infers `T` from the argument: when called with `Stack[int]`, mypy binds `T = int` for that call, and the return type becomes `int | None`. When called with `Stack[str]`, `T = str` and the return is `str | None`. This is *parametric polymorphism* — one function, many concrete types, type-checked correctly at each call.

**Why is `peek_top` not a method on `Stack`?**

It could be — and probably should be. We made it a free function to demonstrate that generic *functions* (not just generic *classes*) work. The pattern is identical: put a free `TypeVar` in the signature, mypy infers it from the call site. Free generic functions are how you write utilities like `def first(xs: list[T]) -> T | None` that work on any list.

### Lines 48–66: The `__main__` block

```python
if __name__ == "__main__":
    # Unbounded: a stack of ints, a stack of strs — both type-check.
    ints: Stack[int] = Stack()
    ints.push(1)
    ints.push(2)
    print("ints pop:", ints.pop())

    strs: Stack[str] = Stack()
    strs.push("a")
    strs.push("b")
    print("strs pop:", strs.pop())

    # peek_top returns int | None when called on Stack[int].
    print("peek ints:", peek_top(ints))
    print("peek strs:", peek_top(strs))

    # Bounded: a ShapeStack that holds Circle and Ticket (both Shape subclasses).
    shapes: ShapeStack[Shape] = ShapeStack()
    shapes.push(Circle(1.0))
    shapes.push(Ticket(42))
    print("total area:", shapes.total_area())

    # The TypeVar object is its own type at runtime.
    print("T is:", T)
    print("ShapeT bound:", ShapeT.__bound__)
    print("StrOrBytes constraints:", StrOrBytes.__constraints__)
```

We exercise three things: (1) the unbounded `Stack` with `int` and `str` — both work; (2) the generic function `peek_top` returns the right concrete type (mypy infers it; at runtime, `peek_top` returns whatever was in the stack, but the type-checker knows it is `int` or `str`); (3) the bounded `ShapeStack` with `Circle` and `Ticket` (both `Shape` subclasses) — both work because the bound is satisfied. The last three `print` lines show the introspection: `T`'s repr is `~T`, `ShapeT.__bound__` is `<class 'Shape'>`, and `StrOrBytes.__constraints__` is `(<class 'str'>, <class 'bytes'>)`. These three attributes are how you programmatically inspect a TypeVar at runtime.

## Execution Trace

```bash
$ python boardly/typevar_generics.py
ints pop: 2
strs pop: b
peek ints: 1
peek strs: a
total area: 45.14
T is: ~T
ShapeT bound: <class '__main__.Shape'>
StrOrBytes constraints: (<class 'str'>, <class 'bytes'>)
```

Three things to verify in this trace. First, `peek ints` returns `1` — the value we pushed first (peek reads the top without popping, but here we have already popped `2`, so the top is `1`). Second, `total area` is `45.14` — `Circle(1.0)` has area `3.14 * 1.0 * 1.0 = 3.14`, and `Ticket(42)` has area `42.0`; sum is `45.14`. Third, the introspection prints confirm the TypeVar forms: unbounded, bounded (`__bound__` set), and constrained (`__constraints__` set).

## Common Mistakes

### Mistake 1: Using `bound=` and constraints together

```python
T = TypeVar("T", bound=Shape, str, bytes)  # ← TypeError at runtime
```

**Symptom:** `TypeError: TypeVar cannot be both bound and constrained` at import time.
**Why:** A TypeVar is *either* unbounded, bounded, or constrained — these are mutually exclusive. The `bound=` keyword and the positional constraints cannot coexist.
**Fix:** Pick one. If you want "T must be a Shape subclass", use `bound=Shape`. If you want "T must be exactly `str` or `bytes`", use the positional form `TypeVar("T", str, bytes)`.

### Mistake 2: Subscripting a non-generic class

```python
class Stack:  # ← no Generic[T]
    ...
s: Stack[int] = Stack()  # ← TypeError at runtime in 3.9+
```

**Symptom:** `TypeError: 'type' object is not subscriptable` (in 3.9) — or, in 3.10+, the subscription may succeed but produce a `types.GenericAlias` that the type-checker rejects.
**Why:** Without `Generic[T]` as a base, the class is not generic and cannot be subscripted at runtime (PEP 585 made builtins subscriptable but user classes still need `Generic`).
**Fix:** Add `Generic[T]` to the bases: `class Stack(Generic[T]):`.

### Mistake 3: Using a constrained TypeVar when you meant a bound

```python
T = TypeVar("T", int, float)  # ← constrained, not bounded
def double(x: T) -> T:
    return x * 2  # ← mypy: T may not have __mul__
```

**Symptom:** mypy complains that `T` does not support `*` even though both `int` and `float` do.
**Why:** Constraints restrict `T` to be *exactly* `int` or `float` — but mypy's inference for constrained TypeVars treats `T` as the *first common supertype* (here, `int` and `float` share `numbers.Real`, but mypy does not traverse the ABCs). The available methods are the intersection of `int` and `float`'s methods, which is small.
**Fix:** Use a bound on a Protocol: `T = TypeVar("T", bound=SupportsMul)` where `SupportsMul` is a `Protocol` with `def __mul__(self, other) -> Self: ...`. Lesson 05 covers `Protocol`.

## Engineering Trade-Offs

**Decision:** Use the *legacy* `TypeVar("T")` constructor and `Generic[T]` base — *not* PEP 695's `class Stack[T]:` syntax — throughout boardly.
**Both sides:** PEP 695 (3.12+) introduces `class Stack[T]:` and `type Alias[T] = ...` — cleaner syntax, no `TypeVar` boilerplate. The legacy form is verbose but works on 3.10+ (and 3.9 with the `TypeVar("T")` call, just without PEP 695's syntactic sugar). The legacy form also lets you write `TypeVar("T", bound=X)` and `TypeVar("T", str, bytes)` — bounds and constraints — which PEP 695's `class Stack[T]:` form *does not* support. PEP 695 has no syntax for bounded or constrained TypeVars.
**Commitment:** boardly uses the legacy form. We support 3.10+ as a minimum and want bounds and constraints, neither of which PEP 695 offers. When PEP 695 grows support for bounds (no PEP exists as of 3.12), we will reconsider.

## Exercises

1. **Exercise 1 — Run the file.** Save the code as `boardly/typevar_generics.py` and run it. Compare output to the Execution Trace. `Verify: python boardly/typevar_generics.py`
2. **Exercise 2 — Add a `clear` method to `Stack`.** Add `def clear(self) -> None: self._items.clear()` and confirm the stack still works. Verify `peek_top` returns `None` after `clear`. `Verify: python -c "from boardly.typevar_generics import Stack, peek_top; s = Stack[int](); s.push(1); s.clear(); print(peek_top(s))"`
3. **Exercise 3 — Use the constrained TypeVar.** Write `def concat(x: StrOrBytes) -> StrOrBytes: return x + x[:1]` and confirm mypy accepts it for both `str` and `bytes` arguments. (mypy will infer the right return type per call.) `Verify: python -c "from boardly.typevar_generics import concat; print(concat('ab'))"`
4. **Exercise 4 — Bound to a Protocol.** Define a `Protocol` `class HasArea(Protocol): area: float` (see lesson 05 for syntax) and rebind `ShapeT` to `bound=HasArea`. Make a non-Shape class with an `area` attribute and confirm `ShapeStack[NonShapeClass]` type-checks. `Verify: python -c "from boardly.typevar_generics import ShapeStack, ShapeT; print(ShapeT.__bound__)"`
5. **Exercise 5 — Build a two-parameter generic.** Add `K = TypeVar("K"); V = TypeVar("V")` and `class Repository(Generic[K, V]):` with `get(self, k: K) -> V | None` and `put(self, k: K, v: V) -> None`. Use it as `Repository[int, Ticket]`. `Verify: python -c "from boardly.typevar_generics import Repository, Ticket; r = Repository[int, Ticket](); r.put(1, Ticket(1)); print(r.get(1))"`

## Verification

```bash
$ python boardly/typevar_generics.py
ints pop: 2
strs pop: b
peek ints: 1
peek strs: a
total area: 45.14
T is: ~T
ShapeT bound: <class '__main__.Shape'>
StrOrBytes constraints: (<class 'str'>, <class 'bytes'>)
```

If `T is: ~T`, `ShapeT bound: <class '__main__.Shape'>`, and `StrOrBytes constraints: (<class 'str'>, <class 'bytes'>)` all appear, you have the three TypeVar forms working and inspectable at runtime.

## Previously Learned Here

- [[01-typing/01-Type-Hints-Basics]] — `list[int]`, `get_type_hints`. Lesson 03 builds on that by letting *your own* classes be parameterised.
- [[01-typing/02-Annotated-and-Metadata]] — `Annotated` attaches metadata to a *concrete* type. `TypeVar` is the way to attach a *parameter* instead of a concrete type.

## What's Next

[[01-typing/04-ParamSpec-and-TypeVarTuple]] — the next tier of generic vocabulary. `TypeVar` parameterises over a *single* type. `ParamSpec` parameterises over a *signature* (a function's parameter list) — which lets you write typed decorators that preserve the wrapped function's signature. `TypeVarTuple` parameterises over a *variable number* of types — which lets you write variadic generics like `tuple[*Ts]`. Three things to look for in lesson 04:

- `ParamSpec("P")` and `def deco(fn: Callable[P, R]) -> Callable[P, R]: ...` — the typed-decorator pattern.
- `Concatenate[int, P]` — how to *prepend* a parameter to a `ParamSpec` (FastAPI uses this to type dependency wrappers).
- `TypeVarTuple("Ts")` and `def first(*xs: *Ts) -> tuple[*Ts]: ...` — variadic generics.

Take your time. Type every example. **This is how you learn.**

## Sources

- **typing.TypeVar — CPython reference** — https://docs.python.org/3/library/typing.html#typing.TypeVar — accessed 2026-10-23 — the canonical API for `TypeVar`, including `bound`, constraints, `__bound__`, and `__constraints__`.
- **typing.Generic — CPython reference** — https://docs.python.org/3/library/typing.html#typing.Generic — accessed 2026-10-23 — the base class used to declare a generic class.
- **PEP 484 — Type Hints (the Generics section)** — https://peps.python.org/pep-0484/#generics — accessed 2026-10-23 — the original generics PEP, where `TypeVar` and `Generic` were introduced.
- **PEP 695 — Type Parameter Syntax** — https://peps.python.org/pep-0695/ — accessed 2026-10-23 — the 3.12 `class Stack[T]:` syntax (which we deliberately do not use in boardly because it lacks bounds and constraints).

## What We Learned

- `TypeVar("T")` (unbounded) accepts any type — for when you have no opinion.
- `TypeVar("T", bound=X)` accepts `X` and any subclass — for an *open* contract.
- `TypeVar("T", str, bytes)` (constraints) accepts *exactly* `str` or `bytes`, no subclasses — for a *closed* set.
- `class Stack(Generic[T])` makes a class generic; subscripting `Stack[int]` specialises it.
- A *free* TypeVar in a function signature (`def f(x: T) -> T`) makes the function generic — `Generic` is only for classes.
- `TypeVar.__bound__` and `TypeVar.__constraints__` let you inspect the form at runtime.
- `bound` and constraints are mutually exclusive — pick one.
