---
title: Progress Tracker
aliases:
 - Tracker
 - Checklist
tags:
 - start-here
 - tracker
status: complete
---

# Progress Tracker

*A checklist. Tick a box when you can do the thing the lesson teaches — not when you've merely read it.*

## Phase 1 — The type system (Section 01)

- [ ] [[01-typing/01-Type-Hints-Basics]] — I can read `list[int]`, `dict[str, X]`, `X | Y` without thinking.
- [ ] [[01-typing/02-Annotated-and-Metadata]] — I can explain why `Annotated[int, Depends(...)]` works and `int` alone does not.
- [ ] [[01-typing/03-TypeVar-and-Generics]] — I can write a generic `class Stack(Generic[T])`.
- [ ] [[01-typing/05-Protocol-Structural-Typing]] — I can pick between `Protocol` and an ABC.
- [ ] [[01-typing/06-Callable-and-Callable-Annotations]] — I can read `Callable[[int, str], None]` and know the 3.12 shorthand.
- [ ] [[01-typing/07-TypedDict]] — I can type a JSON shape with `TypedDict`.
- [ ] [[01-typing/08-Literal-and-TypeGuard]] — I can narrow a type with `TypeGuard`.
- [ ] [[01-typing/09-Overload]] — I can write two `@overload` stubs for one function.
- [ ] [[01-typing/10-Future-Annotations]] — I know what `from __future__ import annotations` does and when it breaks.
- [ ] [[01-typing/11-typing-vs-runtime]] — I can explain the difference between `__annotations__` and `get_type_hints()`.
- [ ] [[01-typing/04-ParamSpec-and-TypeVarTuple]] — I can type a decorator that preserves the wrapped function's signature.

## Phase 2 — How FastAPI reads your signatures (Section 10)

- [ ] [[10-inspect/01-signature-and-Parameter]] — I can walk a function's parameters with `inspect.signature`.
- [ ] [[10-inspect/02-get_type_hints]] — I know why FastAPI passes `include_extras=True`.
- [ ] [[10-inspect/04-Parameter-kinds]] — I can name all 5 `Parameter.kind` values and what produces each.
- [ ] [[10-inspect/05-BoundArguments-and-bind]] — I can `bind` arguments to a signature and `apply_defaults`.
- [ ] [[10-inspect/03-iscoroutinefunction]] — I know how FastAPI decides sync vs async.
- [ ] [[10-inspect/06-How-FastAPI-uses-inspect]] — I have read (or written) a minimal `Depends()` re-implementation.

## Phase 3 — The data containers (Section 06)

- [ ] [[06-dataclasses/01-dataclass-Basics]] — I can write a `@dataclass` and predict its generated methods.
- [ ] [[06-dataclasses/02-field-and-Defaults]] — I know why `field(default_factory=list)` is required and `= []` is forbidden.
- [ ] [[06-dataclasses/03-Frozen-and-Immutability]] — I can explain why `frozen=True` enables hashability.
- [ ] [[06-dataclasses/04-Slots-and-Performance]] — I can measure the memory win from `slots=True`.
- [ ] [[06-dataclasses/05-Inheritance]] — I can resolve the "required field after a defaulted one" error.
- [ ] [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — I can pick between the three for a given field.
- [ ] [[06-dataclasses/06-asdict-astuple-replace]] — I can use `replace()` to make a modified copy.
- [ ] [[06-dataclasses/08-KW_ONLY-and-InitVar]] — I can pass init-only data to `__post_init__`.

## Phase 4 — Collections & ABCs (Sections 04, 05)

- [ ] [[04-collections/01-Counter]] — I can count and rank with `Counter`.
- [ ] [[04-collections/02-defaultdict]] — I can group items with `defaultdict(list)`.
- [ ] [[04-collections/03-deque]] — I can build a bounded ring buffer with `deque(maxlen=N)`.
- [ ] [[04-collections/04-namedtuple]] — I can pick between `namedtuple` and `typing.NamedTuple`.
- [ ] [[04-collections/06-OrderedDict]] — I can explain why `OrderedDict` still exists post-3.7.
- [ ] [[04-collections/05-ChainMap]] — I can layer config with `ChainMap`.
- [ ] [[04-collections/07-UserDict-UserList-UserString]] — I know why subclassing `dict` directly is a trap.
- [ ] [[05-collections-abc/01-The-ABC-Hierarchy]] — I can draw the ABC tree.
- [ ] [[05-collections-abc/04-Iterator-vs-Iterable]] — I can explain why an iterator is exhausted after one pass.
- [ ] [[05-collections-abc/03-Hashable-and-Frozen]] — I can explain the mutable-vs-immutable hash contract.
- [ ] [[05-collections-abc/02-Sequence-Mapping-Set]] — I can subclass `Sequence` and get the mixin methods for free.
- [ ] [[05-collections-abc/05-Custom-ABCs]] — I can `register` a virtual subclass.
- [ ] [[05-collections-abc/06-abcs-vs-protocols]] — I can pick between an ABC and a `Protocol`.

## Phase 5 — Function tools & context (Sections 02, 03)

- [ ] [[02-functools/02-wraps-and-Decorators]] — I never write a decorator without `@wraps`.
- [ ] [[02-functools/01-lru_cache-and-Caching]] — I can memoise and read `cache_info()`.
- [ ] [[02-functools/03-partial]] — I can pre-bind arguments with `partial`.
- [ ] [[02-functools/04-singledispatch]] — I can dispatch by type without `if isinstance`.
- [ ] [[02-functools/06-cached_property]] — I know why `cached_property` breaks on a slotted class.
- [ ] [[02-functools/05-reduce]] — I know when `reduce` is the right answer (rarely).
- [ ] [[02-functools/07-total_ordering]] — I can fill in the comparison methods.
- [ ] [[03-contextlib/01-contextmanager]] — I can write a context manager with one `yield`.
- [ ] [[03-contextlib/02-asynccontextmanager]] — I can write the async version.
- [ ] [[03-contextlib/05-contextvars]] — I can set a request-scoped value in middleware and read it in any handler.
- [ ] [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — I can manage dynamic cleanup with `ExitStack`.
- [ ] [[03-contextlib/04-suppress]] — I can suppress a specific exception cleanly.
- [ ] [[03-contextlib/06-redirect_stdout-stderr]] — I can capture stdout in a test.
- [ ] [[03-contextlib/07-contextmanager-decorator-internals]] — I can explain how `@contextmanager` synthesises `__enter__`/`__exit__`.

## Phase 6 — Enums, the future, and the rest (Sections 09, 13)

- [ ] [[09-enum/01-Enum-Basics]] — I can write an `Enum` and use `Color["RED"]`.
- [ ] [[09-enum/02-IntEnum-and-StrEnum]] — I can pick between `IntEnum` and `StrEnum`.
- [ ] [[09-enum/03-Flag-and-IntFlag]] — I can compose bit flags with `|` and `&`.
- [ ] [[09-enum/04-auto-and-value]] — I can write a custom `_generate_next_value_`.
- [ ] [[09-enum/05-Enum-in-APIs]] — I can make FastAPI serialise an `Enum` field.
- [ ] [[13-future/01-from-future-import-annotations]] — I can explain PEP 563.
- [ ] [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] — I can explain why PEP 649 is better than PEP 563.
- [ ] [[13-future/03-When-string-annotations-break]] — I can debug a `NameError` from `get_type_hints`.

## Phase 7 — The remaining 14 sections (07, 08, 11, 12, 14–23)

All 23 content sections are now complete. Tick a box when you can do the thing the lesson teaches.

### Phase 7a — Iterators & paths (Sections 07, 08)

- [ ] [[07-itertools/01-chain-and-islice]] — I can compose a streaming pipeline with `chain` and `islice`.
- [ ] [[07-itertools/02-groupby]] — I know `groupby` groups CONSECUTIVE same-key elements and I sort first.
- [ ] [[07-itertools/03-starmap-and-accumulate]] — I can write a running aggregate with `accumulate`.
- [ ] [[07-itertools/04-product-combinations-permutations]] — I can name when to use `product` vs `combinations` vs `permutations`.
- [ ] [[07-itertools/05-cycle-repeat-count]] — I can pick between the three infinite iterators.
- [ ] [[07-itertools/06-dropwhile-takewhile-filterfalse]] — I know `takewhile` STOPS at the first miss.
- [ ] [[07-itertools/07-tee-and-zip_longest]] — I can explain the memory cost of `tee`.
- [ ] [[08-pathlib/01-Path-Basics]] — I use `Path` everywhere instead of `os.path.join`.
- [ ] [[08-pathlib/02-read-write-text-binary]] — I can `read_text`/`write_text` in one line.
- [ ] [[08-pathlib/03-glob-and-rglob]] — I can find files recursively with `rglob`.
- [ ] [[08-pathlib/04-mkdir-rmdir-unlink]] — I use `mkdir(parents=True, exist_ok=True)` and `unlink(missing_ok=True)`.
- [ ] [[08-pathlib/05-PurePath-vs-Path]] — I can explain the difference between path arithmetic and I/O.
- [ ] [[08-pathlib/06-walk-and-iterdir]] — I can walk a directory tree lazily with `walk` (3.12+).
- [ ] [[08-pathlib/07-stat-and-permissions]] — I can read file metadata with `stat()` and `chmod`.

### Phase 7b — User-defined ABCs, runtime types, dynamic imports (Sections 11, 12, 14)

- [ ] [[11-abc/01-ABC-and-abstractmethod]] — I can write an `ABC` that refuses instantiation until every `@abstractmethod` is implemented.
- [ ] [[11-abc/02-register-and-Virtual-Subclasses]] — I can register a virtual subclass and explain why `__mro__` does not change.
- [ ] [[11-abc/03-ABC-vs-Protocol-vs-collections-abc]] — I can pick between `abc.ABC`, `typing.Protocol`, and `collections.abc.X` for a new contract.
- [ ] [[12-types/01-NewType]] — I can declare a nominal-distinction id with `NewType("UserId", int)`.
- [ ] [[12-types/02-SimpleNamespace]] — I know when `SimpleNamespace` beats `@dataclass` (and when it loses).
- [ ] [[12-types/03-GenericAlias-and-UnionType]] — I can introspect `list[int]` and `int | str` at runtime via `get_origin`/`get_args`.
- [ ] [[12-types/04-ModuleType-and-FunctionType]] — I can explain why `inspect.signature(f).parameters` is a `MappingProxyType` and read-only.
- [ ] [[14-importlib/01-import_module]] — I can import a module by dotted string name with `import_module`.
- [ ] [[14-importlib/02-resources]] — I can read a data file bundled inside a package with `importlib.resources`.
- [ ] [[14-importlib/03-metadata]] — I can read an installed distribution's version and entry points.
- [ ] [[14-importlib/04-reload]] — I know the `from x import y` gotcha for `reload`.

### Phase 7c — Boundary types: timestamps, identifiers, money (Sections 15, 16, 17)

- [ ] [[15-datetime/01-datetime-and-timezone]] — I know to call `datetime.now(timezone.utc)` (never `datetime.now()` or `datetime.utcnow()`).
- [ ] [[15-datetime/02-timedelta]] — I can do `datetime + timedelta` arithmetic and read `.total_seconds()`.
- [ ] [[15-datetime/03-ISO-8601-format]] — I can serialise a `datetime` with `isoformat(timespec=...)`.
- [ ] [[15-datetime/04-timezone-aware-vs-naive]] — I can explain the `TypeError: can't compare offset-naive and offset-aware datetimes` exception.
- [ ] [[15-datetime/05-fromisoformat-and-parsing]] — I can parse ISO 8601 with `fromisoformat` and use `zoneinfo.ZoneInfo`.
- [ ] [[16-uuid/01-UUID-variants]] — I can name all 8 RFC 9562 variants and pick the right factory function.
- [ ] [[16-uuid/02-uuid4-vs-uuid7]] — I can explain why `uuid4` hurts a B-tree index and why `uuid7` (3.14+) fixes it.
- [ ] [[17-decimal/01-Decimal-Basics]] — I never construct a `Decimal` from a `float` — always from a `str`.
- [ ] [[17-decimal/02-Context-and-precision]] — I can use `localcontext()` to scope a precision override.
- [ ] [[17-decimal/03-Decimal-in-APIs]] — I can write a Pydantic `field_validator` that rejects float input with a 422.

### Phase 7d — Functional glue & resource hygiene (Sections 18, 19)

- [ ] [[18-operator/01-itemgetter-attrgetter]] — I never write `lambda r: r[1]` when `itemgetter(1)` will do.
- [ ] [[18-operator/02-methodcaller]] — I can pre-bind a method call with `methodcaller("strip")`.
- [ ] [[18-operator/03-functional-composition]] — I can articulate why `sum()` beats `reduce(operator.add, ...)`.
- [ ] [[19-weakref/01-WeakValueDictionary]] — I can build a per-id cache that auto-expires with `WeakValueDictionary`.
- [ ] [[19-weakref/02-WeakSet-and-finalize]] — I can replace a `__del__` method with `weakref.finalize`.
- [ ] [[19-weakref/03-When-weakrefs-save-memory]] — I can pick between `weakref`, `lru_cache`, and `cached_property` based on lifetime ownership.

### Phase 7e — Deprecation, concurrency, validation, logging (Sections 20, 21, 22, 23)

- [ ] [[20-warnings/01-warn-and-filterwarnings]] — I always pass `stacklevel=2` to `warnings.warn`.
- [ ] [[20-warnings/02-DeprecationWarning-vs-FutureWarning]] — I can pick between `DeprecationWarning` and `FutureWarning` based on the audience.
- [ ] [[20-warnings/03-deprecated-decorator-PEP-702]] — I can apply `@deprecated("...")` (3.13+) and explain the static check it enables.
- [ ] [[21-asyncio-primitives/01-Task-gather-wait_for]] — I never leave a bare `coro()` — I `create_task` or `await`.
- [ ] [[21-asyncio-primitives/02-Lock-and-Event]] — I can use `async with lock:` for async mutual exclusion.
- [ ] [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] — I can build a bounded producer-consumer pipeline with `asyncio.Queue`.
- [ ] [[21-asyncio-primitives/04-Semaphore-and-Condition]] — I can explain why `Semaphore(1)` is not a substitute for `Lock`.
- [ ] [[21-asyncio-primitives/05-to_thread-and-run-in-executor]] — I know to call `asyncio.to_thread` for blocking sync code (not `requests.get`).
- [ ] [[22-re/01-compile-and-match]] — I can `re.compile` a pattern once and reuse it; I use `fullmatch` (not `match`) for validation.
- [ ] [[22-re/02-search-findall-finditer]] — I can stream `Match` objects lazily with `finditer`.
- [ ] [[22-re/03-sub-and-named-groups]] — I use `\g<name>` backrefs (never `\1`) to avoid the octal-escape trap.
- [ ] [[22-re/04-re-in-validation]] — I can recognise the ReDoS family and apply atomic groups on attacker-controlled input.
- [ ] [[23-logging/01-Logger-Handler-Formatter]] — I can navigate the dot-namespaced logger tree and avoid the root-logger gotcha.
- [ ] [[23-logging/02-dictConfig]] — I can wire a production logging config with `dictConfig`.
- [ ] [[23-logging/03-structured-logging]] — I can build a `JSONFormatter` that emits one JSON object per `LogRecord`.
- [ ] [[23-logging/04-Uvicorn-logging-integration]] — I can interleave Uvicorn access logs with business logs in one JSON stream.
