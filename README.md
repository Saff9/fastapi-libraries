# The Standard Library FastAPI Builds On

> A complete, opinionated curriculum for the Python standard-library modules that FastAPI, Pydantic, SQLAlchemy, and every modern async backend leans on — `typing`, `dataclasses`, `collections.abc`, `functools`, `contextlib`, `inspect`, `enum`, and the rest. Master the primitives before the framework, and the framework stops feeling like magic.

**As of:** 2026-10-23 · **Target runtime:** Python 3.12 (stable) · **Forward notes:** Python 3.13 & 3.14 features are version-gated where they appear

---

## Why this course exists

FastAPI is not magic. Every `Annotated[int, Depends(get_db)]` you write is a `typing.Annotated` (PEP 593) that FastAPI introspects with `inspect.signature` and `typing.get_type_hints`. Every `@dataclass` you ship is the `dataclasses` module generating `__init__`, `__repr__`, and `__eq__` for you. Every request-scoped database session is a `contextvars.ContextVar` (PEP 567) set in middleware and read in your dependency. Every `@lru_cache`-d lookup, every `@contextmanager`-wrapped resource, every `enum.StrEnum` status field — they are all stdlib, and they are all things you will use incorrectly until you have read their source-of-truth behaviour once.

This course is that once. It teaches the standard library the way a senior engineer explains it to a new hire on day one: real code first, then line-by-line, then the gotcha that has caused a production incident. No framework knowledge is assumed — but by the end, you will understand FastAPI from the inside, because you will understand the primitives it is made of.

## Teaching style

Lessons use a warm mentor tone, real-code-first, line-by-line deep dives that explain *what / why / what-Python-does-internally* for every meaningful code line. Each lesson shows the complete working file once, then walks every block under `### Lines N–M: …` headings. Inline self-asking Q&A (`**Why X:**` exchanges, 3–5 per lesson) force active reading. Mermaid diagrams are color-coded with `style Node fill:#…` or `classDef`. A single growing application — `boardly`, a project-management API — threads through the lessons so the same codebase keeps reappearing.

Notes and warnings are plain Markdown — a bold label (`**Warning — …**`, `**Tip — …**`, `**Note — …**`, `**Danger — …**`, `**Example — …**`, `**Bug — …**`) followed by the body as ordinary paragraphs. No emojis, no Obsidian-only callout syntax. The vault renders identically in Obsidian, GitHub, VS Code, and the companion Next.js viewer.

## The sections

| # | Section | What you learn |
|---|---------|----------------|
| 01 | `typing` | `Annotated`, `TypeVar`, `Protocol`, `Callable`, `TypedDict`, `Literal`, `overload`, and what `from __future__ import annotations` actually does |
| 02 | `functools` | `lru_cache`, `wraps`, `partial`, `singledispatch`, `cached_property`, `reduce` |
| 03 | `contextlib` | `contextmanager`, `asynccontextmanager`, `ExitStack`, `suppress`, `contextvars` |
| 04 | `collections` | `Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`, `OrderedDict` |
| 05 | `collections.abc` | The ABC hierarchy — `Iterable`, `Sequence`, `Mapping`, `Callable`, `Hashable` — and when an ABC beats a `Protocol` |
| 06 | `dataclasses` | `@dataclass`, `field`, `frozen`, `slots`, inheritance, `asdict`/`replace`, and the `dataclass` vs Pydantic vs `TypedDict` decision |
| 07 | `itertools` | `chain`, `groupby`, `islice`, `starmap`, `product`, `combinations` |
| 08 | `pathlib` | `Path`, read/write text & binary, `glob`/`rglob`, `walk`, `stat` |
| 09 | `enum` | `Enum`, `IntEnum`, `StrEnum` (3.11+), `Flag`, `auto`, and FastAPI's `Enum` integration |
| 10 | `inspect` | `signature`, `Parameter`, `get_type_hints`, `iscoroutinefunction` — the module FastAPI uses to read your dependency signatures |
| 11 | `abc` | `ABC`, `abstractmethod`, `register`, virtual subclasses, and `abc` vs `Protocol` vs `collections.abc` |
| 12 | `types` | `NewType`, `SimpleNamespace`, `GenericAlias`, `FunctionType`, `ModuleType` |
| 13 | `__future__` | The `from __future__ import annotations` saga — PEP 563, PEP 649, PEP 749, and when string annotations break |
| 14 | `importlib` | `import_module`, `resources`, `metadata`, `reload` |
| 15 | `datetime` | `datetime`, `timezone`, `timedelta`, ISO-8601, aware vs naive |
| 16 | `uuid` | `UUID` variants (1, 3, 4, 5, 6, 7, 8), `uuid4` vs the 3.14 `uuid7` |
| 17 | `decimal` | `Decimal` for money, `Context`, precision, and why `float` is forbidden in billing |
| 18 | `operator` | `itemgetter`, `attrgetter`, `methodcaller`, functional composition |
| 19 | `weakref` | `WeakValueDictionary`, `WeakSet`, `finalize`, and the memory wins |
| 20 | `warnings` | `warn`, `filterwarnings`, `DeprecationWarning` vs `FutureWarning`, PEP 702 `@deprecated` (3.13+) |
| 21 | `asyncio` primitives | `Task`, `gather`, `wait_for`, `Lock`, `Event`, `Queue` (and 3.13 `shutdown`), `to_thread` |
| 22 | `re` | `compile`, `match`/`search`/`findall`/`finditer`, `sub`, named groups, and validation use |
| 23 | `logging` | `Logger`/`Handler`/`Formatter`, `dictConfig`, structured logging, Uvicorn integration |

## Verified versions (2026-10-23)

| Component | Version | Notes |
|---|---|---|
| Python | 3.12.15 (sandbox runtime) / 3.14.x (current stable upstream) | All runnable examples target 3.12 so they execute in this vault's playground. 3.13+ and 3.14+ features are version-gated where they appear. |
| `typing` | stdlib | `Annotated` (3.9), `TypeAlias` (3.10), `TypeVar` (3.5+), `ParamSpec` (3.10+, PEP 612), `TypeVarTuple` (3.11+, PEP 646), `Self` (3.11), `TypeGuard` (3.10), `deprecated` (3.13, PEP 702) |
| `dataclasses` | stdlib | `slots=True` (3.10), `kw_only=True` (3.10), `InitVar` (3.8+) |
| `enum` | stdlib | `StrEnum` (3.11), `EnumType` improvements (3.12) |
| `uuid` | stdlib | `uuid6`/`uuid7`/`uuid8` added in 3.14 (not in the 3.12 runtime — noted in the lesson) |
| `asyncio` | stdlib | `Queue.shutdown` (3.13, not in 3.12 runtime — noted), `to_thread` (3.9) |

---

## Opening in Obsidian

1. Open Obsidian → **Open folder as vault**.
2. Select the `FastAPI-Engineering-Academy/` directory.
3. Wikilinks and Mermaid diagrams render natively. No community plugins are required.

---

## Opening in the companion viewer

The Next.js app at the project root is a read-only browser for this vault. Run `bun run dev` and open `http://localhost:3000`. The sidebar tree, search (`⌘K`), breadcrumbs, and Mermaid rendering all work against the markdown files in this folder.
