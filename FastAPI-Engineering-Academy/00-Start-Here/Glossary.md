---
title: Glossary
aliases:
 - Vocabulary
 - Terms
tags:
 - start-here
 - glossary
status: complete
---

# Glossary

*One paragraph per term. If a term has a canonical lesson, it's linked.*

**ABC (Abstract Base Class).** A class that uses `ABCMeta` as its metaclass and defines one or more `@abstractmethod`s. Subclasses must implement the abstracts before they can be instantiated. `collections.abc` ships a hierarchy of ABCs (`Iterable`, `Sequence`, `Mapping`, …) that use `__subclasshook__` to register any class with the right dunder methods as a virtual subclass — `isinstance([1,2], Sequence)` is `True` without `list` inheriting from `Sequence`. See [[05-collections-abc/01-The-ABC-Hierarchy]].

**Annotated.** A type-hint form (`Annotated[T, metadata...]`, PEP 593) that attaches arbitrary metadata to a type without changing the type at runtime. FastAPI reads `Annotated[int, Depends(get_db)]` by calling `typing.get_type_hints(fun, include_extras=True)`, which preserves the metadata instead of stripping it to `int`. The single most important primitive in the course. See [[01-typing/02-Annotated-and-Metadata]].

**`@asynccontextmanager`.** The async sibling of `@contextmanager` (`contextlib.asynccontextmanager`). Decorate an `async def` generator that does `async yield` exactly once and you get an object that implements `__aenter__`/`__aexit__` without writing a class. FastAPI's async-generator dependencies (`async def get_session(): yield session`) use the same shape. See [[03-contextlib/02-asynccontextmanager]].

**BoundArguments.** The object returned by `inspect.Signature.bind(*args, **kwargs)`. It holds the matched arguments as an ordered dict (`.arguments`), exposes `.args` and `.kwargs` for unpacking, and has `.apply_defaults()` to fill in optional parameters that weren't passed. FastAPI uses `bind` to figure out which dependencies to inject. See [[10-inspect/05-BoundArguments-and-bind]].

**`@cached_property`.** A decorator (`functools.cached_property`) that memoises a method's return value per instance — the first access computes and stores the value in `instance.__dict__`; subsequent reads skip the descriptor entirely. The gotcha: on a `@dataclass(slots=True)` class (which has no `__dict__`), `cached_property` raises `TypeError`. See [[02-functools/06-cached_property]].

**`@contextmanager`.** A decorator (`contextlib.contextmanager`) that turns a generator function (one with a single `yield`) into a context manager — `__enter__` runs everything before the `yield`, `__exit__` runs everything after. The escape hatch from writing a class with `__enter__`/`__exit__` for one-off `with` blocks. See [[03-contextlib/01-contextmanager]].

**ContextVar.** A per-context value (PEP 567) that asyncio snapshots on task creation. Set in middleware (`request_id_var.set(uuid4())`), read anywhere in the same request (`request_id_var.get()`). The primitive that makes per-request database sessions, request IDs, and tenant context work without threading them through every function signature. See [[03-contextlib/05-contextvars]].

**Counter.** A `dict` subclass (`collections.Counter`) for counting hashable items. `Counter(iterable)` tallies; `.most_common(n)` returns the top `n` (key, count) pairs; the `+`/`-`/`&`/`|` operators do multiset arithmetic; `.elements()` yields each item count times. The right answer to "how many of each, and what are the top K". See [[04-collections/01-Counter]].

**dataclass.** A class decorator (`@dataclass`, PEP 557) that generates `__init__`, `__repr__`, `__eq__`, and optionally `__hash__`, `__lt__`, etc. from your type-annotated fields. No validation, no parsing — just boilerplate elimination. Compare to Pydantic `BaseModel` (validates) and `TypedDict` (no runtime presence at all). See [[06-dataclasses/01-dataclass-Basics]] and [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]].

**`datetime` / `timezone`.** The `datetime.datetime` type (an instant in time) and the `datetime.timezone` class (a concrete fixed-offset subclass of the abstract `tzinfo`). The cardinal rule: store `datetime.now(timezone.utc)` (aware UTC), never `datetime.now()` (naive local) or `datetime.utcnow()` (deprecated 3.12, still naive). Comparing an aware `datetime` with a naive one raises `TypeError` — the production-saver. See [[15-datetime/01-datetime-and-timezone]].

**Decimal.** A base-10 fixed-point number type (`decimal.Decimal`) — `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` exactly. Constructed from a `str` (never a `float`, which captures the binary approximation); controlled by a thread-local `Context` (precision, rounding mode) and overridden per-scope with `localcontext()`. The right type for money; `float` is forbidden in billing code. See [[17-decimal/01-Decimal-Basics]].

**defaultdict.** A `dict` subclass (`collections.defaultdict`) whose `__missing__` calls a `default_factory` to fill in a missing key instead of raising `KeyError`. `defaultdict(list)` is the canonical grouping pattern — `for k, v in pairs: d[k].append(v)` works without `setdefault` or `if k not in d`. See [[04-collections/02-defaultdict]].

**deque.** A doubly-linked-list-backed double-ended queue (`collections.deque`) with O(1) `appendleft`/`popleft`. With `maxlen=N` it becomes a ring buffer that drops the oldest element on overflow. The queue behind every bounded LRU cache and every producer-consumer pipeline. See [[04-collections/03-deque]].

**dictConfig.** `logging.config.dictConfig(config)` — the declarative way to configure the `logging` hierarchy from a dict (typically loaded from YAML). Schema keys: `version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`; the `"()"` callable-spec instantiates a class by import path; `ext://sys.stderr` references an existing object. Replaces imperative `addHandler` setup. See [[23-logging/02-dictConfig]].

**Enum.** A class (`enum.Enum`) whose members are singleton constants — `Color.RED is Color.RED` is always `True`. Accessed by attribute (`Color.RED`), name (`Color["RED"]`), or value (`Color(1)`); `__members__` is the `dict`-like mapping. The 3.12+ metaclass is `enum.EnumType`. Subclass mixins (`int`, `str`) produce `IntEnum`/`StrEnum`; the 3.11 `StrEnum` fix made `str(StrEnum.X)` return `"X"` not `"StrEnum.X"`. See [[09-enum/01-Enum-Basics]] and [[09-enum/02-IntEnum-and-StrEnum]].

**ForwardRef.** The internal type `typing` uses for an unresolved string annotation. When you write `from __future__ import annotations`, every annotation becomes a string stored as a `ForwardRef` until `get_type_hints()` resolves it. If resolution fails (the name is out of scope), you get a `NameError`. See [[01-typing/11-typing-vs-runtime]] and [[13-future/03-When-string-annotations-break]].

**`from __future__ import annotations`.** The PEP 563 import that stringifies every annotation at module-load time — `__annotations__` stores `{"x": "int"}` instead of `{"x": int}`. Enables forward references and self-references, but breaks `get_type_hints()` when a name is out of scope. PEP 649 (deferred evaluation, 3.14 default) is the proper fix — lazy evaluation, no string storage, no `NameError`. See [[13-future/01-from-future-import-annotations]].

**get_type_hints.** The function (`typing.get_type_hints(obj, globalns=None, localns=None, include_extras=False)`) that resolves string annotations into real type objects. The `include_extras=True` flag keeps `Annotated` metadata — this is the exact call FastAPI and Pydantic make to read your signatures. See [[10-inspect/02-get_type_hints]].

**Generic.** A base class (`typing.Generic[T]`) that makes a class parametric over a `TypeVar`. `list` is implicitly `Generic`; your own classes need to inherit from `Generic[T]` explicitly. See [[01-typing/03-TypeVar-and-Generics]].

**Hashable.** An object with a `__hash__` method whose value never changes over the object's lifetime and that compares equal to another object only when their hashes are equal. Mutable objects (`list`, `dict`, `set`) are unhashable; `frozen=True` dataclasses are hashable. See [[05-collections-abc/03-Hashable-and-Frozen]].

**`import_module`.** `importlib.import_module(name, package=None)` — the runtime-callable form of `import`. Returns the leaf module of a dotted path (`import_module("a.b.c")` returns `c`, not `a` like `__import__` does); `package=` enables relative imports. The public API for plugin loaders and config-driven imports. See [[14-importlib/01-import_module]].

**include_extras.** The keyword argument to `typing.get_type_hints(..., include_extras=True)` that preserves `Annotated[T, metadata]` instead of returning just `T`. If you forget it, FastAPI cannot read your `Depends(...)` metadata. See [[10-inspect/02-get_type_hints]].

**Iterable / Iterator.** `Iterable` is anything with `__iter__` (returns an `Iterator`); `Iterator` is anything with `__next__` (returns the next value or raises `StopIteration`). `for x in obj` calls `iter(obj)` first. An iterator is exhausted after one pass — a common gotcha. See [[05-collections-abc/04-Iterator-vs-Iterable]].

**`itemgetter` / `attrgetter`.** Two factory functions (`operator.itemgetter`, `operator.attrgetter`) that return a callable extracting the named index/attribute from its argument. `itemgetter(1)(row)` is `row[1]`; `attrgetter("owner.name")(obj)` walks a dotted path. The C-accelerated fast path beats a `lambda` at every `key=` call site. See [[18-operator/01-itemgetter-attrgetter]].

**logging.getLogger.** `logging.getLogger(name)` returns the singleton logger for `name`, organised in a dot-namespaced parent/child tree (`"boardly.routers"` is a child of `"boardly"`). Effective level cascades up the tree; the root logger (`getLogger()` with no name) is the gotcha — `logging.warning()` in library code mutates the root. See [[23-logging/01-Logger-Handler-Formatter]].

**lru_cache.** A decorator (`functools.lru_cache(maxsize=N)`) that memoises a function's return values keyed on its arguments, evicting the least-recently-used entry when the cache is full. Thread-safe via an internal lock. `cache()` (3.9+) is the unbounded variant. See [[02-functools/01-lru_cache-and-Caching]].

**namedtuple.** A factory (`collections.namedtuple`) that generates a tuple subclass with named fields, a fixed length, and `__repr__`/`_replace`/`_asdict` helpers. `typing.NamedTuple` (3.6.1+) is the type-hinted form. See [[04-collections/04-namedtuple]].

**NewType.** `UserId = NewType("UserId", int)` creates a nominal-distinction alias — mypy treats `UserId` as distinct from `int`, but at runtime `UserId(5) is 5` is `True` (zero-cost, zero-validation). The static-only concept FastAPI pairs with `Annotated[UserId, Field(ge=0)]` for runtime-validated ids. See [[12-types/01-NewType]].

**OrderedDict.** A `dict` subclass (`collections.OrderedDict`) with explicit `move_to_end(key)` and `popitem(last=True)` methods. Since 3.7 plain `dict` preserves insertion order too — so `OrderedDict` exists today for its *additional* API (the `move_to_end`/`popitem`/equality semantics that ignore order). The right tool for LRU caches and equality-is-order-sensitive tests. See [[04-collections/06-OrderedDict]].

**Parameter.kind.** One of five values (`POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD`) that `inspect.Parameter.kind` reports for each parameter of a function. The `/` and `*` markers in a function signature control which kind each parameter gets. See [[10-inspect/04-Parameter-kinds]].

**Path.** `pathlib.Path` — the object-oriented filesystem path. `Path("a") / "b" / "c"` joins paths (no more `os.path.join`); `.name`/`.stem`/`.suffix`/`.parent`/`.parts` parse components; `.read_text()`/`.write_text()`/`.glob()`/`.mkdir()`/`.stat()` replace 12+ `os.path` functions. `PurePath` is the no-I/O parent; `Path` adds the I/O methods. See [[08-pathlib/01-Path-Basics]].

**Protocol.** A structural type (`typing.Protocol`, PEP 544) — a class whose shape (method names + signatures) any other class can match without inheriting. Duck typing, formalised for static checkers. `@runtime_checkable` enables `isinstance` checks (but only on method names, not signatures). See [[01-typing/05-Protocol-Structural-Typing]] and [[05-collections-abc/06-abcs-vs-protocols]].

**`re.compile` / `re.fullmatch`.** `re.compile(pattern, flags)` returns a `re.Pattern` object (3.7+; `re.Pattern[str]` 3.9+) you bind once at module scope and reuse — the bound methods skip the module-internal cache lookup on every call. `re.fullmatch` (3.4+) anchors the match at *both* ends; `re.match` only anchors at the start (and silently accepts trailing junk). The rule: **use `fullmatch` for validation**. See [[22-re/01-compile-and-match]].

**`@singledispatch`.** A decorator (`functools.singledispatch`) that turns a function into a type-driven dispatch table — register overloads with `@fun.register(Type)`, and the call picks the implementation by the first argument's MRO. The `@singledispatchmethod` (3.8+) variant works on methods. The closest standard-library parallel to FastAPI's `Depends`-style dispatch. See [[02-functools/04-singledispatch]].

**`asyncio.create_task` / `gather` / `wait_for`.** The three primitives for running coroutines concurrently. `create_task(coro())` schedules the coroutine on the running loop and returns a `Task` (a bare `coro()` is never scheduled and emits `RuntimeWarning: coroutine was never awaited`); `gather(*coros)` runs them concurrently and returns results in input order; `wait_for(aw, timeout)` raises `TimeoutError` (== `asyncio.TimeoutError` in 3.12) on timeout. See [[21-asyncio-primitives/01-Task-gather-wait_for]].

**StrEnum.** An `enum` subclass (3.11+) where members are `str` instances and `str(StrEnum.X)` returns `"X"` (not `"StrEnum.X"`, which the pre-3.11 `str`-mixin pattern produced). The canonical choice for string enums in modern Python. See [[09-enum/02-IntEnum-and-StrEnum]].

**`to_thread`.** `asyncio.to_thread(func, *args, **kwargs)` (3.9+) is the canonical way to call blocking sync code from async — runs `func` in a worker thread, returns the result as an awaitable. The default `ThreadPoolExecutor` formula is `min(32, os.cpu_count() + 4)`. For long-term migration, switch to `httpx.AsyncClient` instead of `requests.get` + `to_thread`. See [[21-asyncio-primitives/05-to_thread-and-run-in-executor]].

**TypeVar.** A type variable (`typing.TypeVar("T")`) that stands for an unknown type in a generic. Can be bounded (`bound=Animal`) or constrained (`TypeVar("T", str, bytes)`). `ParamSpec` (3.10+) is for typed decorators; `TypeVarTuple` (3.11+) is for variadic generics. See [[01-typing/03-TypeVar-and-Generics]] and [[01-typing/04-ParamSpec-and-TypeVarTuple]].

**TypedDict.** A type-hint form (`typing.TypedDict`, PEP 589) for dict shapes — `class Point(TypedDict): x: int; y: int` means a dict with exactly the keys `x` and `y` of those types. No runtime presence: a `TypedDict` IS a plain `dict`. `Required`/`NotRequired` (3.11+) mark optional keys. See [[01-typing/07-TypedDict]].

**UUID.** A 128-bit typed identifier (`uuid.UUID`) that validates the layout, exposes the version and variant bits, and rejects malformed input at construction time. Constructed from a hex string, an int, 16 bytes, or a 6-field tuple; rendered as a 36-character dashed string only at the JSON boundary. The eight RFC 9562 variants cover time/MAC, name-hash, random, and time-sortable layouts. The rule: never store an identifier as `str`. See [[16-uuid/01-UUID-variants]].

**`warnings.warn` / `stacklevel`.** `warnings.warn(message, category=DeprecationWarning, stacklevel=2)` emits a warning at the call site. The default `stacklevel=1` points at the `warn()` line itself (wrong for library code); `stacklevel=2` points at the caller (right). The filter stack — `simplefilter`, `filterwarnings`, `catch_warnings(record=True)` — controls what gets shown. Drive it from CI with `-W error::DeprecationWarning` or `PYTHONWARNINGS=...`. See [[20-warnings/01-warn-and-filterwarnings]].

**WeakValueDictionary.** A `dict`-shaped mapping (`weakref.WeakValueDictionary`) that holds its values by weak reference — the entry disappears automatically when the value is garbage-collected elsewhere. The three access paths differ on a dead entry: `.get()` returns `None`, `in` returns `False`, `[]` raises `KeyError`. The per-id cache that auto-expires; the answer to "the worker's cache is leaking memory". See [[19-weakref/01-WeakValueDictionary]].

**wraps.** A decorator (`functools.wraps(fun)`) that copies `__module__`, `__name__`, `__qualname__`, `__annotations__`, and `__doc__` from the wrapped function to the wrapper, and sets `__wrapped__` so `inspect.signature(wrapper)` returns the wrapped function's signature. Every decorator you write needs it. See [[02-functools/02-wraps-and-Decorators]].

---

Add a term by editing this file and linking its canonical lesson. The bar for inclusion: the term appears in at least three lessons and a newcomer would not know it.
