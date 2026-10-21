---
title: Source Register
aliases:
 - Sources
 - Source Register
tags:
 - reference
status: complete
last_verified: 2026-10-23
---

# Source Register

Primary sources consulted for this vault. Versions were verified against the live sources on the date accessed (2026-10-23). When a specific version is named in a lesson, it was confirmed against the source at that URL.

| # | Source | URL | Accessed | Used in | Notes |
|---|---|---|---|---|---|
| 1 | Python `typing` module docs | https://docs.python.org/3/library/typing.html | 2026-10-23 | 01-typing/* | `Annotated`, `TypeVar`, `Protocol`, `TypedDict`, `Literal`, `TypeGuard`, `overload`. |
| 2 | PEP 484 — Type Hints | https://peps.python.org/pep-0484/ | 2026-10-23 | 01-typing/01, 11 | The foundational type-hints PEP. |
| 3 | PEP 593 — Flexible function and variable annotations | https://peps.python.org/pep-0593/ | 2026-10-23 | 01-typing/02 | `Annotated`. The FastAPI primitive. |
| 4 | PEP 544 — Protocols | https://peps.python.org/pep-0544/ | 2026-10-23 | 01-typing/05, 05-collections-abc/06 | Structural typing. |
| 5 | PEP 585 — `list[int]` generic syntax | https://peps.python.org/pep-0585/ | 2026-10-23 | 01-typing/01 | The modern lowercase generic syntax. |
| 6 | PEP 586 — `Literal` | https://peps.python.org/pep-0586/ | 2026-10-23 | 01-typing/08 | |
| 7 | PEP 589 — `TypedDict` | https://peps.python.org/pep-0589/ | 2026-10-23 | 01-typing/07 | |
| 8 | PEP 604 — `X | Y` union syntax | https://peps.python.org/pep-0604/ | 2026-10-23 | 01-typing/01 | |
| 9 | PEP 612 — `ParamSpec` | https://peps.python.org/pep-0612/ | 2026-10-23 | 01-typing/04 | Typed decorators. |
| 10 | PEP 646 — `TypeVarTuple` | https://peps.python.org/pep-0646/ | 2026-10-23 | 01-typing/04 | Variadic generics. |
| 11 | PEP 655 — `Required`/`NotRequired` | https://peps.python.org/pep-0655/ | 2026-10-23 | 01-typing/07 | `TypedDict` optional keys. |
| 12 | PEP 563 — Postponed evaluation of annotations | https://peps.python.org/pep-0563/ | 2026-10-23 | 01-typing/10, 13-future/* | `from __future__ import annotations`. |
| 13 | PEP 649 — Deferred annotation evaluation | https://peps.python.org/pep-0649/ | 2026-10-23 | 13-future/02 | Default in Python 3.14 (version-gated). |
| 14 | PEP 749 — Implementation of PEP 649 | https://peps.python.org/pep-0749/ | 2026-10-23 | 13-future/02 | The 3.14 `__annotate__` mechanism. |
| 15 | Python `functools` docs | https://docs.python.org/3/library/functools.html | 2026-10-23 | 02-functools/* | `lru_cache`, `wraps`, `partial`, `singledispatch`, `cached_property`, `total_ordering`. |
| 16 | Python `contextlib` docs | https://docs.python.org/3/library/contextlib.html | 2026-10-23 | 03-contextlib/* | `contextmanager`, `asynccontextmanager`, `ExitStack`, `suppress`, `redirect_stdout`. |
| 17 | Python `contextvars` docs | https://docs.python.org/3/library/contextvars.html | 2026-10-23 | 03-contextlib/05 | `ContextVar`, `Context`, `Token`. |
| 18 | PEP 567 — `contextvars` | https://peps.python.org/pep-0567/ | 2026-10-23 | 03-contextlib/05 | The PEP. |
| 19 | Python `collections` docs | https://docs.python.org/3/library/collections.html | 2026-10-23 | 04-collections/* | `Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`, `OrderedDict`, `UserDict`. |
| 20 | Python `collections.abc` docs | https://docs.python.org/3/library/collections.abc.html | 2026-10-23 | 05-collections-abc/* | The ABC hierarchy. |
| 21 | Python `dataclasses` docs | https://docs.python.org/3/library/dataclasses.html | 2026-10-23 | 06-dataclasses/* | `dataclass`, `field`, `asdict`, `replace`, `KW_ONLY`, `InitVar`. |
| 22 | PEP 557 — `dataclasses` | https://peps.python.org/pep-0557/ | 2026-10-23 | 06-dataclasses/01 | The PEP. |
| 23 | Python `enum` docs | https://docs.python.org/3/library/enum.html | 2026-10-23 | 09-enum/* | `Enum`, `IntEnum`, `StrEnum`, `Flag`, `auto`. |
| 24 | Python `inspect` docs | https://docs.python.org/3/library/inspect.html | 2026-10-23 | 10-inspect/* | `signature`, `Parameter`, `get_type_hints`, `bind`. |
| 25 | PEP 362 — `inspect.signature` | https://peps.python.org/pep-0362/ | 2026-10-23 | 10-inspect/01 | The PEP. |
| 26 | PEP 570 — Positional-only parameters | https://peps.python.org/pep-0570/ | 2026-10-23 | 10-inspect/04 | The `/` marker. |
| 27 | PEP 3102 — Keyword-only arguments | https://peps.python.org/pep-3102/ | 2026-10-23 | 10-inspect/04 | The `*` marker. |
| 28 | FastAPI documentation (Depends, Annotated) | https://fastapi.tiangolo.com/tutorial/dependencies/ | 2026-10-23 | 01-typing/02, 10-inspect/06 | How FastAPI reads `Annotated[T, Depends(...)]`. |
| 29 | CPython source (GitHub) | https://github.com/python/cpython | 2026-10-23 | 03-contextlib/07, 02-functools/01 | Implementation references (`Lib/functools.py`, `Lib/contextlib.py`). |

## Rules used

1. We do not invent future releases. Where a specific version is named, it was confirmed at the URL above on the date accessed.
2. The sandbox runtime is Python 3.12.15 — every runnable example targets 3.12. Features that require 3.13 or 3.14 are version-gated and clearly marked in the lesson.
3. Verified facts and personal engineering judgments are separated: lessons explicitly label "**Engineering judgment:**" for the latter.
