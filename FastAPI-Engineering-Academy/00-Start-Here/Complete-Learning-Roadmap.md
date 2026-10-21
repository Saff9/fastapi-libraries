---
title: Complete Learning Roadmap
aliases:
 - Roadmap
 - Reading Order
tags:
 - start-here
 - roadmap
status: complete
---

# Complete Learning Roadmap

*A suggested reading order across all 23 sections. Tick the boxes in [[00-Start-Here/Progress-Tracker]] as you go.*

The vault is non-linear — you can read any lesson standalone — but there is a sensible order. The principle: **learn the primitive FastAPI introspects, then the primitive that primitive is built on, then the next one down.** By the end you understand FastAPI from the inside.

## Phase 1 — The type system (the foundation)

Everything FastAPI does starts with reading your type hints. Master `typing` first.

1. [[01-typing/01-Type-Hints-Basics]] — the modern syntax (`list[int]`, `X | Y`).
2. [[01-typing/02-Annotated-and-Metadata]] — **the lesson**. `Annotated[int, Depends(...)]` is how FastAPI reads your dependencies.
3. [[01-typing/03-TypeVar-and-Generics]] — `TypeVar`, `Generic[T]`.
4. [[01-typing/05-Protocol-Structural-Typing]] — duck typing, formalised.
5. [[01-typing/07-TypedDict]] — typed dicts (the JSON shape primitive).
6. [[01-typing/08-Literal-and-TypeGuard]] — `Literal["active", "archived"]`.
7. [[01-typing/09-Overload]] — multiple signatures for one function.
8. [[01-typing/10-Future-Annotations]] — `from __future__ import annotations`.
9. [[01-typing/11-typing-vs-runtime]] — what evaluates when. The capstone.
10. [[01-typing/04-ParamSpec-and-TypeVarTuple]] — typed decorators (advanced; read after you've written a decorator).

## Phase 2 — How FastAPI reads your signatures

Now you know `typing`, learn the module FastAPI uses to introspect it.

1. [[10-inspect/01-signature-and-Parameter]] — `inspect.signature(fun)`.
2. [[10-inspect/02-get_type_hints]] — `get_type_hints(..., include_extras=True)` — the call FastAPI makes on every route.
3. [[10-inspect/04-Parameter-kinds]] — positional-only, keyword-only, `*args`, `**kwargs`.
4. [[10-inspect/05-BoundArguments-and-bind]] — `sig.bind(...)`.
5. [[10-inspect/03-iscoroutinefunction]] — how FastAPI decides sync vs async.
6. [[10-inspect/06-How-FastAPI-uses-inspect]] — the capstone. A minimal re-implementation of `Depends()` resolution.

## Phase 3 — The data containers

You have types. Now put data in them.

1. [[06-dataclasses/01-dataclass-Basics]] — `@dataclass`.
2. [[06-dataclasses/02-field-and-Defaults]] — `field(default_factory=list)`.
3. [[06-dataclasses/03-Frozen-and-Immutability]] — `frozen=True`.
4. [[06-dataclasses/04-Slots-and-Performance]] — `slots=True`.
5. [[06-dataclasses/05-Inheritance]] — `kw_only`.
6. [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — the decision.
7. [[06-dataclasses/06-asdict-astuple-replace]] — the helpers.
8. [[06-dataclasses/08-KW_ONLY-and-InitVar]] — `__post_init__`.

## Phase 4 — Collections & ABCs

1. [[04-collections/01-Counter]] — counting.
2. [[04-collections/02-defaultdict]] — grouping.
3. [[04-collections/03-deque]] — queues.
4. [[04-collections/04-namedtuple]] — lightweight records.
5. [[04-collections/06-OrderedDict]] — `move_to_end`.
6. [[04-collections/05-ChainMap]] — config layering.
7. [[04-collections/07-UserDict-UserList-UserString]] — subclassing.
8. [[05-collections-abc/01-The-ABC-Hierarchy]] — the tree.
9. [[05-collections-abc/04-Iterator-vs-Iterable]] — the protocol.
10. [[05-collections-abc/03-Hashable-and-Frozen]] — why frozen matters.
11. [[05-collections-abc/02-Sequence-Mapping-Set]] — the mixins.
12. [[05-collections-abc/05-Custom-ABCs]] — `register`, `__subclasshook__`.
13. [[05-collections-abc/06-abcs-vs-protocols]] — the decision.

## Phase 5 — Function tools & context

1. [[02-functools/02-wraps-and-Decorators]] — every decorator needs `@wraps`.
2. [[02-functools/01-lru_cache-and-Caching]] — memoisation.
3. [[02-functools/03-partial]] — partial application.
4. [[02-functools/04-singledispatch]] — dispatch by type.
5. [[02-functools/06-cached_property]] — the slots gotcha.
6. [[02-functools/05-reduce]] — and why you usually shouldn't.
7. [[02-functools/07-total_ordering]] — filling in the comparison methods.
8. [[03-contextlib/01-contextmanager]] — `@contextmanager`.
9. [[03-contextlib/02-asynccontextmanager]] — the async version.
10. [[03-contextlib/05-contextvars]] — **the request-scoped primitive**. Read this before middleware.
11. [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — dynamic cleanup.
12. [[03-contextlib/04-suppress]] — clean `try/except/pass`.
13. [[03-contextlib/06-redirect_stdout-stderr]] — capturing output.
14. [[03-contextlib/07-contextmanager-decorator-internals]] — how it works.

## Phase 6 — Enums, the future, and the rest

1. [[09-enum/01-Enum-Basics]] — `Enum`.
2. [[09-enum/02-IntEnum-and-StrEnum]] — `StrEnum` (3.11+).
3. [[09-enum/03-Flag-and-IntFlag]] — bit flags.
4. [[09-enum/04-auto-and-value]] — `auto()`.
5. [[09-enum/05-Enum-in-APIs]] — FastAPI + `Enum`.
6. [[13-future/01-from-future-import-annotations]] — PEP 563.
7. [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] — the saga.
8. [[13-future/03-When-string-annotations-break]] — failure modes.

## Phase 7 — The remaining 14 sections

The remaining 14 sections take you through the rest of the standard library FastAPI leans on. They are organised into five thematic sub-phases — iterators & paths, the type-system layer, the boundary types, functional glue & resource hygiene, and the production-critical modules. Pick the sub-phase that matches what you are working on, or read them all in order.

### Phase 7a — Iterators & paths (Sections 07, 08)

1. [[07-itertools/01-chain-and-islice]] — `chain`, `islice` (lazy slice).
2. [[07-itertools/02-groupby]] — the consecutive-group gotcha (sort first).
3. [[07-itertools/03-starmap-and-accumulate]] — `starmap`, running aggregate.
4. [[07-itertools/04-product-combinations-permutations]] — Cartesian, combinations, permutations.
5. [[07-itertools/05-cycle-repeat-count]] — the three infinite iterators.
6. [[07-itertools/06-dropwhile-takewhile-filterfalse]] — prefix / anti-filter.
7. [[07-itertools/07-tee-and-zip_longest]] — fork iterators, zip uneven lengths.
8. [[08-pathlib/01-Path-Basics]] — `Path`, the `/` operator, `.name`/`.stem`/`.suffix`.
9. [[08-pathlib/02-read-write-text-binary]] — `read_text`/`write_text`/`open`.
10. [[08-pathlib/03-glob-and-rglob]] — `glob`, `rglob`, the `**` pattern.
11. [[08-pathlib/04-mkdir-rmdir-unlink]] — `mkdir(parents=True, exist_ok=True)`, `unlink(missing_ok=True)`.
12. [[08-pathlib/05-PurePath-vs-Path]] — path arithmetic vs I/O.
13. [[08-pathlib/06-walk-and-iterdir]] — `iterdir`, `walk` (3.12+).
14. [[08-pathlib/07-stat-and-permissions]] — `stat()`, `is_file()`/`is_dir()`, `chmod`.

### Phase 7b — User-defined ABCs, runtime types, dynamic imports (Sections 11, 12, 14)

1. [[11-abc/01-ABC-and-abstractmethod]] — `ABC`, `@abstractmethod`.
2. [[11-abc/02-register-and-Virtual-Subclasses]] — `register`, `__subclasshook__`.
3. [[11-abc/03-ABC-vs-Protocol-vs-collections-abc]] — the three-way decision.
4. [[12-types/01-NewType]] — `NewType("UserId", int)`.
5. [[12-types/02-SimpleNamespace]] — mutable attribute bag.
6. [[12-types/03-GenericAlias-and-UnionType]] — `list[int]` and `X | Y` at runtime.
7. [[12-types/04-ModuleType-and-FunctionType]] — the type of modules and functions.
8. [[14-importlib/01-import_module]] — `import_module("a.b")`.
9. [[14-importlib/02-resources]] — `files(pkg) / "data.txt"`, `as_file()`.
10. [[14-importlib/03-metadata]] — `version()`, `entry_points()`, `packages_distributions()`.
11. [[14-importlib/04-reload]] — `reload(module)` and its gotchas.

### Phase 7c — Boundary types: timestamps, identifiers, money (Sections 15, 16, 17)

These three sections share one rule: **never use the primitive type for a typed value.** `datetime` instead of `str`, `UUID` instead of `str`, `Decimal` instead of `float`. Read them as a triplet.

1. [[15-datetime/01-datetime-and-timezone]] — `datetime`, `timezone`, `timezone.utc`. Never `datetime.now()`.
2. [[15-datetime/02-timedelta]] — duration arithmetic.
3. [[15-datetime/03-ISO-8601-format]] — `isoformat()` / `fromisoformat()`.
4. [[15-datetime/04-timezone-aware-vs-naive]] — the production bug.
5. [[15-datetime/05-fromisoformat-and-parsing]] — ISO parsing + `zoneinfo`.
6. [[16-uuid/01-UUID-variants]] — the 8 variants.
7. [[16-uuid/02-uuid4-vs-uuid7]] — DB-index locality; `uuid7` is 3.14+.
8. [[17-decimal/01-Decimal-Basics]] — `Decimal("0.10")`, never float.
9. [[17-decimal/02-Context-and-precision]] — `getcontext()`, `localcontext()`.
10. [[17-decimal/03-Decimal-in-APIs]] — Pydantic + FastAPI integration.

### Phase 7d — Functional glue & resource hygiene (Sections 18, 19)

1. [[18-operator/01-itemgetter-attrgetter]] — `itemgetter`, `attrgetter`.
2. [[18-operator/02-methodcaller]] — `methodcaller("strip")`.
3. [[18-operator/03-functional-composition]] — `operator.add`, `reduce`.
4. [[19-weakref/01-WeakValueDictionary]] — weakly-held values.
5. [[19-weakref/02-WeakSet-and-finalize]] — `WeakSet`, `finalize()`.
6. [[19-weakref/03-When-weakrefs-save-memory]] — the cache pattern.

### Phase 7e — Deprecation, concurrency, validation, logging (Sections 20, 21, 22, 23)

The closing four sections cover the production-critical surface — the warnings layer, the asyncio concurrency primitives, the regex engine, and the logging hierarchy that ties a FastAPI app together.

1. [[20-warnings/01-warn-and-filterwarnings]] — `warn(stacklevel=2)`.
2. [[20-warnings/02-DeprecationWarning-vs-FutureWarning]] — the audience rule.
3. [[20-warnings/03-deprecated-decorator-PEP-702]] — `typing.deprecated` (3.13+).
4. [[21-asyncio-primitives/01-Task-gather-wait_for]] — `create_task`, `gather`, `wait_for`.
5. [[21-asyncio-primitives/02-Lock-and-Event]] — `Lock`, `Event`.
6. [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] — `Queue`, `shutdown` (3.13+).
7. [[21-asyncio-primitives/04-Semaphore-and-Condition]] — bounded concurrency.
8. [[21-asyncio-primitives/05-to_thread-and-run-in-executor]] — calling blocking code from async.
9. [[22-re/01-compile-and-match]] — `compile`, `match`, `fullmatch`.
10. [[22-re/02-search-findall-finditer]] — `search`, `findall`, `finditer`.
11. [[22-re/03-sub-and-named-groups]] — `sub`, `(?P<name>...)`.
12. [[22-re/04-re-in-validation]] — ReDoS + Pydantic validation.
13. [[23-logging/01-Logger-Handler-Formatter]] — the hierarchy.
14. [[23-logging/02-dictConfig]] — the production config.
15. [[23-logging/03-structured-logging]] — JSON for log aggregators.
16. [[23-logging/04-Uvicorn-logging-integration]] — **THE FastAPI connection**.

---

**Time estimate:** Phases 1–6 are ~28 hours of focused reading if you type every example. Phase 7 adds ~22 hours across its five sub-phases — totalling ~50 hours for the full 23-section curriculum. Bookmark [[00-Start-Here/Curriculum-Index]] for the full table of contents.
