---
title: Concept Registry
aliases:
 - Canonicals
 - Concepts
tags:
 - start-here
 - concept-registry
status: complete
---

# Concept Registry

*Every concept is taught once, here, in the canonical lesson — and reused everywhere else. When a later lesson needs the concept, it links back instead of re-explaining.*

The table below lists every lesson in the vault whose frontmatter carries a `first_taught_in` field. Each such lesson is the single source of truth for the concept named in the leftmost column; other lessons that need the concept link to the canonical instead of re-explaining it.

## Section 01 — `typing`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| Type hints basics (`list[int]`, `X \| Y`, PEP 604/585) | [[01-typing/01-Type-Hints-Basics]] | 01-typing/01-Type-Hints-Basics | complete |
| `Annotated` (PEP 593) — the FastAPI primitive | [[01-typing/02-Annotated-and-Metadata]] | 01-typing/02-Annotated-and-Metadata | complete |
| `TypeVar` / generics | [[01-typing/03-TypeVar-and-Generics]] | 01-typing/03-TypeVar-and-Generics | complete |
| `Protocol` (structural typing) | [[01-typing/05-Protocol-Structural-Typing]] | 01-typing/05-Protocol-Structural-Typing | complete |
| `from __future__ import annotations` (PEP 563) | [[01-typing/10-Future-Annotations]] | 01-typing/10-Future-Annotations | complete |
| `typing` runtime vs string annotations | [[01-typing/11-typing-vs-runtime]] | 01-typing/11-typing-vs-runtime | complete |

## Section 02 — `functools`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `lru_cache` / memoisation | [[02-functools/01-lru_cache-and-Caching]] | 02-functools/01-lru_cache-and-Caching | complete |
| `@wraps` / decorator preservation | [[02-functools/02-wraps-and-Decorators]] | 02-functools/02-wraps-and-Decorators | complete |
| `@singledispatch` / type-driven dispatch | [[02-functools/04-singledispatch]] | 02-functools/04-singledispatch | complete |
| `@cached_property` / per-instance lazy attributes | [[02-functools/06-cached_property]] | 02-functools/06-cached_property | complete |

## Section 03 — `contextlib`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `@contextmanager` | [[03-contextlib/01-contextmanager]] | 03-contextlib/01-contextmanager | complete |
| `@asynccontextmanager` | [[03-contextlib/02-asynccontextmanager]] | 03-contextlib/02-asynccontextmanager | complete |
| `contextvars` (PEP 567) — the FastAPI request-scoped primitive | [[03-contextlib/05-contextvars]] | 03-contextlib/05-contextvars | complete |

## Section 04 — `collections`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `Counter` | [[04-collections/01-Counter]] | 04-collections/01-Counter | complete |
| `defaultdict` | [[04-collections/02-defaultdict]] | 04-collections/02-defaultdict | complete |
| `deque` | [[04-collections/03-deque]] | 04-collections/03-deque | complete |
| `OrderedDict` | [[04-collections/06-OrderedDict]] | 04-collections/06-OrderedDict | complete |

## Section 05 — `collections.abc`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `collections.abc` hierarchy | [[05-collections-abc/01-The-ABC-Hierarchy]] | 05-collections-abc/01-The-ABC-Hierarchy | complete |
| ABC vs `Protocol` | [[05-collections-abc/06-abcs-vs-protocols]] | 05-collections-abc/06-abcs-vs-protocols | complete |

## Section 06 — `dataclasses`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `@dataclass` basics | [[06-dataclasses/01-dataclass-Basics]] | 06-dataclasses/01-dataclass-Basics | complete |
| `field()` and defaults | [[06-dataclasses/02-field-and-Defaults]] | 06-dataclasses/02-field-and-Defaults | complete |
| `dataclass` vs Pydantic vs `TypedDict` | [[06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict]] | 06-dataclasses/07-dataclass-vs-pydantic-vs-typeddict | complete |

## Section 07 — `itertools`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| Streaming pipelines (`chain`, `islice`) | [[07-itertools/01-chain-and-islice]] | 07-itertools/01-chain-and-islice | complete |

## Section 08 — `pathlib`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `Path` object-oriented filesystem API | [[08-pathlib/01-Path-Basics]] | 08-pathlib/01-Path-Basics | complete |
| `PurePath` vs `Path` (path arithmetic vs I/O) | [[08-pathlib/05-PurePath-vs-Path]] | 08-pathlib/05-PurePath-vs-Path | complete |
| `walk()` generator (3.12+) and `iterdir()` | [[08-pathlib/06-walk-and-iterdir]] | 08-pathlib/06-walk-and-iterdir | complete |
| `stat()` and permissions | [[08-pathlib/07-stat-and-permissions]] | 08-pathlib/07-stat-and-permissions | complete |

## Section 09 — `enum`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `Enum` basics | [[09-enum/01-Enum-Basics]] | 09-enum/01-Enum-Basics | complete |
| `IntEnum` / `StrEnum` | [[09-enum/02-IntEnum-and-StrEnum]] | 09-enum/02-IntEnum-and-StrEnum | complete |
| `Enum` in FastAPI APIs | [[09-enum/05-Enum-in-APIs]] | 09-enum/05-Enum-in-APIs | complete |

## Section 10 — `inspect`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `inspect.signature` / `Parameter` | [[10-inspect/01-signature-and-Parameter]] | 10-inspect/01-signature-and-Parameter | complete |
| `get_type_hints` / `include_extras` | [[10-inspect/02-get_type_hints]] | 10-inspect/02-get_type_hints | complete |
| How FastAPI uses `inspect` (dependency resolution) | [[10-inspect/06-How-FastAPI-uses-inspect]] | 10-inspect/06-How-FastAPI-uses-inspect | complete |

## Section 11 — `abc`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `abc.ABC` + `@abstractmethod` contract | [[11-abc/01-ABC-and-abstractmethod]] | 11-abc/01-ABC-and-abstractmethod | complete |

## Section 12 — `types`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `typing.NewType` (static-only nominal distinction) | [[12-types/01-NewType]] | 12-types/01-NewType | complete |

## Section 13 — `__future__`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `from __future__ import annotations` (PEP 563 mechanism) | [[13-future/01-from-future-import-annotations]] | 13-future/01-from-future-import-annotations | complete |
| PEP 563 vs PEP 649 vs PEP 749 saga | [[13-future/02-PEP-563-vs-PEP-649-vs-PEP-749]] | 13-future/02-PEP-563-vs-PEP-649-vs-PEP-749 | complete |

## Section 14 — `importlib`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `importlib.import_module` (dotted-path imports) | [[14-importlib/01-import_module]] | 14-importlib/01-import_module | complete |

## Section 15 — `datetime`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `datetime` and the `tzinfo` slot; `timezone.utc` | [[15-datetime/01-datetime-and-timezone]] | 15-datetime/01-datetime-and-timezone | complete |

## Section 16 — `uuid`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `UUID` and the never-`str` rule | [[16-uuid/01-UUID-variants]] | 16-uuid/01-UUID-variants | complete |

## Section 17 — `decimal`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `Decimal` (never `float` for money) | [[17-decimal/01-Decimal-Basics]] | 17-decimal/01-Decimal-Basics | complete |
| `decimal.Context` and `localcontext` | [[17-decimal/02-Context-and-precision]] | 17-decimal/02-Context-and-precision | complete |
| `Decimal` in Pydantic / FastAPI | [[17-decimal/03-Decimal-in-APIs]] | 17-decimal/03-Decimal-in-APIs | complete |

## Section 18 — `operator`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `operator.itemgetter` / `operator.attrgetter` | [[18-operator/01-itemgetter-attrgetter]] | 18-operator/01-itemgetter-attrgetter | complete |

## Section 19 — `weakref`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `weakref.WeakValueDictionary` | [[19-weakref/01-WeakValueDictionary]] | 19-weakref/01-WeakValueDictionary | complete |

## Section 20 — `warnings`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `warnings.warn` + `stacklevel=2` | [[20-warnings/01-warn-and-filterwarnings]] | 20-warnings/01-warn-and-filterwarnings | complete |

## Section 21 — `asyncio` primitives

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `asyncio.create_task` / `gather` / `wait_for` | [[21-asyncio-primitives/01-Task-gather-wait_for]] | 21-asyncio-primitives/01-Task-gather-wait_for | complete |
| `asyncio.Lock` and `asyncio.Event` | [[21-asyncio-primitives/02-Lock-and-Event]] | 21-asyncio-primitives/02-Lock-and-Event | complete |
| `asyncio.Queue` (and 3.13 `shutdown`) | [[21-asyncio-primitives/03-Queue-and-Queue-Shutdown]] | 21-asyncio-primitives/03-Queue-and-Queue-Shutdown | complete |
| `asyncio.Semaphore` and `asyncio.Condition` | [[21-asyncio-primitives/04-Semaphore-and-Condition]] | 21-asyncio-primitives/04-Semaphore-and-Condition | complete |
| `asyncio.to_thread` / `run_in_executor` | [[21-asyncio-primitives/05-to_thread-and-run-in-executor]] | 21-asyncio-primitives/05-to_thread-and-run-in-executor | complete |

## Section 22 — `re`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `re.compile`, `re.Pattern`, `re.Match`, `match`, `fullmatch` | [[22-re/01-compile-and-match]] | 22-re/01-compile-and-match | complete |
| `re` in Pydantic / FastAPI validation; ReDoS defences | [[22-re/04-re-in-validation]] | 22-re/04-re-in-validation | complete |

## Section 23 — `logging`

| Concept | Canonical lesson | First taught in | Status |
|---|---|---|---|
| `logging.getLogger` / `Logger` / `Handler` / `Formatter` / `Filter` | [[23-logging/01-Logger-Handler-Formatter]] | 23-logging/01-Logger-Handler-Formatter | complete |
| `logging.config.dictConfig` | [[23-logging/02-dictConfig]] | 23-logging/02-dictConfig | complete |
| Structured logging (`extra={...}`, custom JSON `Formatter`) | [[23-logging/03-structured-logging]] | 23-logging/03-structured-logging | complete |
| Uvicorn logging integration (`LOGGING_CONFIG`, `log_config=`) | [[23-logging/04-Uvicorn-logging-integration]] | 23-logging/04-Uvicorn-logging-integration | complete |

---

**57 canonical lessons across all 23 content sections.** Each is tagged `canonical` in its frontmatter and carries a `first_taught_in` field so the registry can verify the pointer. The canonical count per section: 01 (6), 02 (4), 03 (3), 04 (4), 05 (2), 06 (3), 07 (1), 08 (4), 09 (3), 10 (3), 11 (1), 12 (1), 13 (2), 14 (1), 15 (1), 16 (1), 17 (3), 18 (1), 19 (1), 20 (1), 21 (5), 22 (2), 23 (4).
