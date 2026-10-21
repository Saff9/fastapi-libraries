---
title: Curriculum Index
aliases:
 - Index
 - Table of Contents
tags:
 - index
 - start-here
status: complete
---

# Curriculum Index

*The full table of contents — every section, every lesson, one page. Open a lesson in a new pane and keep this index in another.*

## Section 00 — Start Here

- [[00-Start-Here/Welcome]] — what this course is, how to read a lesson, where to start.
- [[00-Start-Here/Complete-Learning-Roadmap]] — the suggested reading order across all 23 sections.
- [[00-Start-Here/How-to-Use-This-Vault]] — how the vault, the companion viewer, and Obsidian fit together.
- [[00-Start-Here/Progress-Tracker]] — a checklist you tick off as you finish each lesson.
- [[00-Start-Here/Glossary]] — the vocabulary, one paragraph per term.
- [[00-Start-Here/Concept-Registry]] — the canonical lessons. Each concept is taught once, here, and reused everywhere.

## Section 01 — `typing` (the module FastAPI introspects on every request)

- [[01-typing/00-typing-MOC]] — section map of content.
- [[01-typing/01-Type-Hints-Basics]] — `list[int]`, `dict[str, X]`, `X | Y`, `Optional`. *Canonical.*
- [[01-typing/02-Annotated-and-Metadata]] — **THE FastAPI primitive** (PEP 593). *Canonical.*
- [[01-typing/03-TypeVar-and-Generics]] — `TypeVar("T")`, bounds, `Generic[T]`. *Canonical.*
- [[01-typing/04-ParamSpec-and-TypeVarTuple]] — typed decorators, variadic generics.
- [[01-typing/05-Protocol-Structural-Typing]] — `Protocol`, `runtime_checkable`. *Canonical.*
- [[01-typing/06-Callable-and-Callable-Annotations]] — `Callable[[int, str], None]`.
- [[01-typing/07-TypedDict]] — `TypedDict`, `Required`/`NotRequired`.
- [[01-typing/08-Literal-and-TypeGuard]] — `Literal[...]`, `TypeGuard`.
- [[01-typing/09-Overload]] — `@overload` for multiple signatures.
- [[01-typing/10-Future-Annotations]] — `from __future__ import annotations`. *Canonical.*
- [[01-typing/11-typing-vs-runtime]] — what evaluates at runtime, `get_type_hints`, `include_extras`. *Canonical.*

## Section 02 — `functools`

- [[02-functools/00-functools-MOC]] — section map of content.
- [[02-functools/01-lru_cache-and-Caching]] — `@lru_cache`, `cache_info`. *Canonical.*
- [[02-functools/02-wraps-and-Decorators]] — `@wraps`, `__wrapped__`. *Canonical.*
- [[02-functools/03-partial]] — `partial`, `partialmethod`.
- [[02-functools/04-singledispatch]] — `@singledispatch`, `@fun.register`.
- [[02-functools/05-reduce]] — `reduce`, and why a loop is usually better.
- [[02-functools/06-cached_property]] — `@cached_property`, the slots gotcha.
- [[02-functools/07-total_ordering]] — `@total_ordering`.

## Section 03 — `contextlib`

- [[03-contextlib/00-contextlib-MOC]] — section map of content.
- [[03-contextlib/01-contextmanager]] — `@contextmanager`. *Canonical.*
- [[03-contextlib/02-asynccontextmanager]] — `@asynccontextmanager`. *Canonical.*
- [[03-contextlib/03-ExitStack-and-AsyncExitStack]] — dynamic context management.
- [[03-contextlib/04-suppress]] — `with suppress(KeyError): ...`.
- [[03-contextlib/05-contextvars]] — **THE FastAPI request-scoped primitive** (PEP 567). *Canonical.*
- [[03-contextlib/06-redirect_stdout-stderr]] — capturing output.
- [[03-contextlib/07-contextmanager-decorator-internals]] — how `@contextmanager` works.

## Section 04 — `collections`

- [[04-collections/00-collections-MOC]] — section map of content.
- [[04-collections/01-Counter]] — `Counter`, `.most_common`. *Canonical.*
- [[04-collections/02-defaultdict]] — `defaultdict`, `__missing__`. *Canonical.*
- [[04-collections/03-deque]] — `deque`, O(1) ring buffer. *Canonical.*
- [[04-collections/04-namedtuple]] — `namedtuple`, `typing.NamedTuple`.
- [[04-collections/05-ChainMap]] — config layering.
- [[04-collections/06-OrderedDict]] — `move_to_end`, and why it still exists. *Canonical.*
- [[04-collections/07-UserDict-UserList-UserString]] — subclassing containers.

## Section 05 — `collections.abc`

- [[05-collections-abc/00-collections-abc-MOC]] — section map of content + the hierarchy diagram.
- [[05-collections-abc/01-The-ABC-Hierarchy]] — `Iterable`→`Iterator`→`Generator`, etc. *Canonical.*
- [[05-collections-abc/02-Sequence-Mapping-Set]] — the mixin methods.
- [[05-collections-abc/03-Hashable-and-Frozen]] — `Hashable`, `__hash__`.
- [[05-collections-abc/04-Iterator-vs-Iterable]] — `__iter__` vs `__next__`.
- [[05-collections-abc/05-Custom-ABCs]] — `ABCMeta`, `register`, `__subclasshook__`.
- [[05-collections-abc/06-abcs-vs-protocols]] — ABC vs `Protocol`. *Canonical.*

## Section 06 — `dataclasses`

- [[06-dataclasses/00-dataclasses-MOC]] — section map of content.
- [[06-dataclasses/01-dataclass-Basics]] — `@dataclass`. *Canonical.*
- [[06-dataclasses/02-field-and-Defaults]] — `field(default_factory=...)`. *Canonical.*
- [[06-dataclasses/03-Frozen-and-Immutability]] — `frozen=True`.
- [[06-dataclasses/04-Slots-and-Performance]] — `slots=True`.
- [[06-dataclasses/05-Inheritance]] — field accumulation, `kw_only`.
- [[06-dataclasses/06-asdict-astuple-replace]] — the helpers.
- [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] — the decision. *Canonical.*
- [[06-dataclasses/08-KW_ONLY-and-InitVar]] — `KW_ONLY`, `InitVar`.

## Section 07 — `itertools`

- [[07-itertools/00-itertools-MOC]] — section map of content.
- [[07-itertools/01-chain-and-islice]] — `chain`, `islice`. *Canonical.*
- [[07-itertools/02-groupby]] — the consecutive-group gotcha.
- [[07-itertools/03-starmap-and-accumulate]] — `starmap`, running aggregate.
- [[07-itertools/04-product-combinations-permutations]] — Cartesian, combinations, permutations.
- [[07-itertools/05-cycle-repeat-count]] — the three infinite iterators.
- [[07-itertools/06-dropwhile-takewhile-filterfalse]] — prefix filter / anti-filter.
- [[07-itertools/07-tee-and-zip_longest]] — fork iterators, zip uneven lengths.

## Section 08 — `pathlib`

- [[08-pathlib/00-pathlib-MOC]] — section map of content.
- [[08-pathlib/01-Path-Basics]] — `Path`, the `/` operator, `.name`/`.stem`/`.suffix`. *Canonical.*
- [[08-pathlib/02-read-write-text-binary]] — `read_text`/`write_text`/`open`.
- [[08-pathlib/03-glob-and-rglob]] — `glob`, `rglob`, the `**` pattern.
- [[08-pathlib/04-mkdir-rmdir-unlink]] — `mkdir(parents=True, exist_ok=True)`, `unlink(missing_ok=True)`.
- [[08-pathlib/05-PurePath-vs-Path]] — path arithmetic vs I/O.
- [[08-pathlib/06-walk-and-iterdir]] — `iterdir`, `walk` (3.12+).
- [[08-pathlib/07-stat-and-permissions]] — `stat()`, `is_file()`/`is_dir()`, `chmod`.

## Section 09 — `enum`

- [[09-enum/00-enum-MOC]] — section map of content.
- [[09-enum/01-Enum-Basics]] — `Enum`, `__members__`. *Canonical.*
- [[09-enum/02-IntEnum-and-StrEnum]] — `IntEnum`, `StrEnum` (3.11+). *Canonical.*
- [[09-enum/03-Flag-and-IntFlag]] — bit flags.
- [[09-enum/04-auto-and-value]] — `auto()`, `_generate_next_value_`.
- [[09-enum/05-Enum-in-APIs]] — **THE FastAPI connection**. *Canonical.*

## Section 10 — `inspect` (the module FastAPI uses to read your signatures)

- [[10-inspect/00-inspect-MOC]] — section map of content.
- [[10-inspect/01-signature-and-Parameter]] — `signature`, `Parameter`. *Canonical.*
- [[10-inspect/02-get_type_hints]] — `get_type_hints`, `include_extras`. *Canonical.*
- [[10-inspect/03-iscoroutinefunction]] — sync vs async detection.
- [[10-inspect/04-Parameter-kinds]] — the 5 kinds deep-dive.
- [[10-inspect/05-BoundArguments-and-bind]] — `bind`, `apply_defaults`.
- [[10-inspect/06-How-FastAPI-uses-inspect]] — the dependency-resolution capstone. *Canonical.*

## Section 11 — `abc`

- [[11-abc/00-abc-MOC]] — section map of content.
- [[11-abc/01-ABC-and-abstractmethod]] — `ABC`, `@abstractmethod`. *Canonical.*
- [[11-abc/02-register-and-Virtual-Subclasses]] — `register`, `__subclasshook__`.
- [[11-abc/03-ABC-vs-Protocol-vs-collections-abc]] — the decision.

## Section 12 — `types`

- [[12-types/00-types-MOC]] — section map of content.
- [[12-types/01-NewType]] — `NewType("UserId", int)`. *Canonical.*
- [[12-types/02-SimpleNamespace]] — mutable attribute bag.
- [[12-types/03-GenericAlias-and-UnionType]] — `list[int]` and `X | Y` at runtime.
- [[12-types/04-ModuleType-and-FunctionType]] — the type of modules and functions.

## Section 13 — `__future__`

- [[13-future/00-future-MOC]] — section map of content.
- [[13-future/01-from-future-import-annotations]] — PEP 563. *Canonical.*
- [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] — the saga. *Canonical.*
- [[13-future/03-When-string-annotations-break]] — the failure modes.

## Section 14 — `importlib`

- [[14-importlib/00-importlib-MOC]] — section map of content.
- [[14-importlib/01-import_module]] — `import_module("a.b")`. *Canonical.*
- [[14-importlib/02-resources]] — `files(pkg) / "data.txt"`, `as_file()`.
- [[14-importlib/03-metadata]] — `version()`, `entry_points()`, `packages_distributions()`.
- [[14-importlib/04-reload]] — `reload(module)` and its gotchas.

## Section 15 — `datetime`

- [[15-datetime/00-datetime-MOC]] — section map of content.
- [[15-datetime/01-datetime-and-timezone]] — `datetime`, `timezone`, `timezone.utc`. *Canonical.*
- [[15-datetime/02-timedelta]] — duration arithmetic.
- [[15-datetime/03-ISO-8601-format]] — `isoformat()` / `fromisoformat()`.
- [[15-datetime/04-timezone-aware-vs-naive]] — the production bug.
- [[15-datetime/05-fromisoformat-and-parsing]] — ISO parsing + `zoneinfo`.

## Section 16 — `uuid`

- [[16-uuid/00-uuid-MOC]] — section map of content.
- [[16-uuid/01-UUID-variants]] — the 8 variants. *Canonical.*
- [[16-uuid/02-uuid4-vs-uuid7]] — DB-index locality; `uuid7` is 3.14+.

## Section 17 — `decimal`

- [[17-decimal/00-decimal-MOC]] — section map of content.
- [[17-decimal/01-Decimal-Basics]] — `Decimal("0.10")`, never float. *Canonical.*
- [[17-decimal/02-Context-and-precision]] — `getcontext()`, `localcontext()`.
- [[17-decimal/03-Decimal-in-APIs]] — Pydantic + FastAPI integration.

## Section 18 — `operator`

- [[18-operator/00-operator-MOC]] — section map of content.
- [[18-operator/01-itemgetter-attrgetter]] — `itemgetter`, `attrgetter`. *Canonical.*
- [[18-operator/02-methodcaller]] — `methodcaller("strip")`.
- [[18-operator/03-functional-composition]] — `operator.add`, `reduce`.

## Section 19 — `weakref`

- [[19-weakref/00-weakref-MOC]] — section map of content.
- [[19-weakref/01-WeakValueDictionary]] — weakly-held values. *Canonical.*
- [[19-weakref/02-WeakSet-and-finalize]] — `WeakSet`, `finalize()`.
- [[19-weakref/03-When-weakrefs-save-memory]] — the cache pattern.

## Section 20 — `warnings`

- [[20-warnings/00-warnings-MOC]] — section map of content.
- [[20-warnings/01-warn-and-filterwarnings]] — `warn(stacklevel=2)`. *Canonical.*
- [[20-warnings/02-DeprecationWarning-vs-FutureWarning]] — the audience rule.
- [[20-warnings/03-deprecated-decorator-PEP-702]] — `typing.deprecated` (3.13+).

## Section 21 — `asyncio` primitives

- [[21-asyncio-primitives/00-asyncio-MOC]] — section map of content.
- [[21-asyncio-primitives/01-Task-gather-wait_for]] — `create_task`, `gather`, `wait_for`. *Canonical.*
- [[21-asyncio-primitives/02-Lock-and-Event]] — `Lock`, `Event`.
- [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] — `Queue`, `shutdown` (3.13+).
- [[21-asyncio-primitives/04-Semaphore-and-Condition]] — bounded concurrency.
- [[21-asyncio-primitives/05-to_thread-and-run-in-executor]] — calling blocking code from async.

## Section 22 — `re`

- [[22-re/00-re-MOC]] — section map of content.
- [[22-re/01-compile-and-match]] — `compile`, `match`, `fullmatch`. *Canonical.*
- [[22-re/02-search-findall-finditer]] — `search`, `findall`, `finditer`.
- [[22-re/03-sub-and-named-groups]] — `sub`, `(?P<name>...)`.
- [[22-re/04-re-in-validation]] — ReDoS + Pydantic validation. *Canonical.*

## Section 23 — `logging`

- [[23-logging/00-logging-MOC]] — section map of content.
- [[23-logging/01-Logger-Handler-Formatter]] — the hierarchy. *Canonical.*
- [[23-logging/02-dictConfig]] — the production config.
- [[23-logging/03-structured-logging]] — JSON for log aggregators.
- [[23-logging/04-Uvicorn-logging-integration]] — **THE FastAPI connection**.

## Section 24 — Templates

- [[24-Templates/Lesson-Template]] — the 13-section spine every lesson follows.

## Section 25 — Reference Library

- [[25-Reference-Library/Source-Register]] — every primary source consulted, with access dates.
- [[25-Reference-Library/Changelog]] — what changed, when, and why.
- [[25-Reference-Library/Engineering-Decision-Log]] — the architectural decisions, with reasoning.

---

**152 lessons across 25 sections — all 23 content sections complete.** Open [[00-Start-Here/Complete-Learning-Roadmap]] for the suggested reading order, or jump straight to [[01-typing/02-Annotated-and-Metadata]] — the lesson that explains the primitive underneath every `Depends()` call you have ever written.
