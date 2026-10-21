---
title: Changelog
aliases:
 - Changes
 - Log
tags:
 - reference
 - changelog
status: complete
---

# Changelog

## [2026-10-23]: New course — The Standard Library FastAPI Builds On

### Added
- **New course identity.** The vault was wiped and rebuilt as "The Standard Library FastAPI Builds On" — a 23-section curriculum for the Python stdlib modules FastAPI, Pydantic, and every modern async backend leans on (`typing`, `functools`, `contextlib`, `collections`, `collections.abc`, `dataclasses`, `enum`, `inspect`, `__future__`, and the rest).
- **9 complete sections, 69 lessons, ~27K lines.**
  - `01-typing` (12 lessons) — `Annotated`, `TypeVar`, `Protocol`, `TypedDict`, `Literal`/`TypeGuard`, `overload`, `from __future__ import annotations`, runtime-vs-string. 5 canonicals.
  - `02-functools` (7 lessons) — `lru_cache`, `wraps`, `partial`, `singledispatch`, `reduce`, `cached_property`, `total_ordering`. 2 canonicals.
  - `03-contextlib` (7 lessons) — `contextmanager`, `asynccontextmanager`, `ExitStack`, `suppress`, `contextvars` (PEP 567), `redirect_stdout`, the `@contextmanager` internals. 3 canonicals.
  - `04-collections` (7 lessons) — `Counter`, `defaultdict`, `deque`, `namedtuple`, `ChainMap`, `OrderedDict`, `UserDict`. 4 canonicals.
  - `05-collections-abc` (6 lessons) — the ABC hierarchy, `Sequence`/`Mapping`/`Set`, `Hashable`, `Iterator` vs `Iterable`, custom ABCs, ABCs vs `Protocol`. 2 canonicals.
  - `06-dataclasses` (8 lessons) — `@dataclass`, `field`, frozen, slots, inheritance, `asdict`/`replace`, vs Pydantic vs `TypedDict`, `KW_ONLY`/`InitVar`. 3 canonicals.
  - `09-enum` (5 lessons) — `Enum`, `IntEnum`/`StrEnum`, `Flag`/`IntFlag`, `auto`, `Enum` in APIs. 3 canonicals.
  - `10-inspect` (6 lessons) — `signature`/`Parameter`, `get_type_hints`, `iscoroutinefunction`, `Parameter` kinds, `BoundArguments`/`bind`, the FastAPI dependency-resolution capstone. 3 canonicals.
  - `13-future` (3 lessons) — `from __future__ import annotations`, the PEP 563/649/749 saga, when string annotations break. 2 canonicals.
- **14 section MOC stubs** for the not-yet-written sections (07, 08, 11, 12, 14–23). Each lists the planned lessons and cross-links to the closest complete section.
- **Spine files** in `00-Start-Here/`: Welcome, Curriculum-Index, Complete-Learning-Roadmap, How-to-Use-This-Vault, Progress-Tracker, Glossary, Concept-Registry.
- **Reference-Library**: Source-Register (29 primary sources, all accessed 2026-10-23), Changelog, Engineering-Decision-Log.
- **Lesson-Template** (`24-Templates/Lesson-Template.md`) documenting the 13-section spine + the bold-label note convention (no Obsidian callouts, no emojis).

### Pedagogy
- Warm mentor tone, real-code-first, line-by-line deep dives that explain *what / why / what-Python-does-internally* for every meaningful code line.
- Inline self-asking Q&A (`**Why X:**` exchanges, 3–7 per lesson).
- `boardly` (a project-management API with `Project`, `User`, `Ticket`) is the single growing example across all sections.
- Notes are plain Markdown bold labels (`**Warning — Title**`, `**Tip — Title**`, `**Note — Title**`, `**Danger — Title**`, `**Example — Title**`, `**Title**` for info/success/question). Renders identically in Obsidian, GitHub, VS Code, and the companion Next.js viewer.

### Verified versions (2026-10-23)
- Python sandbox runtime: **3.12.15** (every runnable example targets 3.12).
- Python current stable upstream: **3.14.x** (features requiring 3.13 or 3.14 are version-gated in the lessons).
- All 29 primary sources in [[25-Reference-Library/Source-Register]] accessed 2026-10-23.

### Known limitations
- 14 sections are MOC stubs only; the lessons are being written.
- The capstone `10-inspect/06-How-FastAPI-uses-inspect` re-implements `Depends()` minimally; the real FastAPI path has more edge cases (sub-dependencies, `yield` cleanup, security scopes) that are noted but not fully implemented.

## [2026-10-24]: 14-section deepening pass — all 23 sections complete

### Added
- **14 new sections, 48 new lessons** — the vault grew from 9 complete sections to all 23 complete. The 14 new sections and their lesson counts:
  - `07-itertools` (7 lessons) — `chain`, `groupby`, `starmap`/`accumulate`, `product`/`combinations`/`permutations`, the three infinite iterators, `dropwhile`/`takewhile`/`filterfalse`, `tee`/`zip_longest`. 1 canonical.
  - `08-pathlib` (7 lessons) — `Path` basics, read/write text & binary, `glob`/`rglob`, `mkdir`/`rmdir`/`unlink`, `PurePath` vs `Path`, `walk` (3.12+) / `iterdir`, `stat` & permissions. 4 canonicals.
  - `11-abc` (3 lessons) — `ABC`/`@abstractmethod`, `register`/`__subclasshook__`, the ABC vs `Protocol` vs `collections.abc` decision. 1 canonical.
  - `12-types` (4 lessons) — `NewType`, `SimpleNamespace`, `GenericAlias`/`UnionType`, `ModuleType`/`FunctionType`/`MappingProxyType`. 1 canonical.
  - `14-importlib` (4 lessons) — `import_module`, `resources`, `metadata`, `reload`. 1 canonical.
  - `15-datetime` (5 lessons) — `datetime`/`timezone`, `timedelta`, ISO 8601, aware vs naive (the production bug), `fromisoformat` + `zoneinfo`. 1 canonical.
  - `16-uuid` (2 lessons) — the 8 RFC 9562 variants, `uuid4` vs `uuid7` (3.14+, version-gated). 1 canonical.
  - `17-decimal` (3 lessons) — `Decimal` basics (never `float`), `Context`/`localcontext`, `Decimal` in Pydantic/FastAPI. 3 canonicals.
  - `18-operator` (3 lessons) — `itemgetter`/`attrgetter`, `methodcaller`, functional composition. 1 canonical.
  - `19-weakref` (3 lessons) — `WeakValueDictionary`, `WeakSet`/`finalize`, when weakrefs save memory. 1 canonical.
  - `20-warnings` (3 lessons) — `warn`/`filterwarnings`, `DeprecationWarning` vs `FutureWarning` (PEP 565), `@deprecated` (PEP 702, 3.13+). 1 canonical.
  - `21-asyncio-primitives` (5 lessons) — `Task`/`gather`/`wait_for`, `Lock`/`Event`, `Queue`/`shutdown` (3.13+), `Semaphore`/`Condition`, `to_thread`/`run_in_executor`. 5 canonicals.
  - `22-re` (4 lessons) — `compile`/`match`/`fullmatch`, `search`/`findall`/`finditer`, `sub`/named groups, `re` in validation + ReDoS defences. 2 canonicals.
  - `23-logging` (4 lessons) — `Logger`/`Handler`/`Formatter`/`Filter`, `dictConfig`, structured logging (JSON), Uvicorn integration. 4 canonicals.
- **Lesson total grew from 69 to 117** (48 new lessons across the 14 new sections). The vault is now 152 files total (117 lessons + 23 MOCs + 7 spine + 1 template + 3 reference + 1 README).
- **Canonical total grew from 26 to 57** (31 new canonicals across 14 sections, all with `first_taught_in` frontmatter).
- **Spine files updated** to reflect the full 23-section scope:
  - `00-Start-Here/Curriculum-Index` — every section now lists its actual lessons (verified against each section's `00-*-MOC.md`).
  - `00-Start-Here/Complete-Learning-Roadmap` — Phase 7 expanded from "coming soon" placeholder to a five-sub-phase reading order covering all 14 newly-complete sections (7a iterators & paths; 7b ABCs, types, importlib; 7c boundary types: datetime/uuid/decimal; 7d operator & weakref; 7e warnings, asyncio, re, logging).
  - `00-Start-Here/Progress-Tracker` — Phase 7 replaced its 14 MOC-only checkboxes with 57 per-lesson checkboxes. Phase 1 gained the previously-missing `06-Callable-and-Callable-Annotations` checkbox (now 117 lesson checkboxes total — one per actual lesson).
  - `00-Start-Here/Concept-Registry` — table expanded from 26 to 57 canonicals (organised by section), with the closing count-by-section breakdown.
  - `00-Start-Here/Glossary` — 23 new terms added covering the new sections (`@asynccontextmanager`, `@cached_property`, `Counter`, `@contextmanager`, `datetime`/`timezone`, `Decimal`, `defaultdict`, `dictConfig`, `Enum`, `from __future__ import annotations`, `import_module`, `itemgetter`/`attrgetter`, `logging.getLogger`, `NewType`, `OrderedDict`, `Path`, `re.compile`/`re.fullmatch`, `@singledispatch`, `asyncio.create_task`/`gather`/`wait_for`, `to_thread`, `UUID`, `warnings.warn`/`stacklevel`, `WeakValueDictionary`). Glossary grew from 20 to 43 terms.
- **`25-Reference-Library/Engineering-Decision-Log`** gained D-007 ("All 23 sections complete") recording the deepening-pass decision and the spine-files-as-source-of-truth rule.

### Changed
- The previous `[Unreleased]`/`Planned` entry ("Lessons for sections 07, 08, 11, 12, 14–23") is now resolved — see the entry above.
- `00-Start-Here/Welcome` and the root `README` continue to describe the course as 23 sections / 152 lessons / 23 content sections complete — no copy change needed (they were already future-tense correct).

### Removed
- The "Known limitations: 14 sections are MOC stubs only" paragraph from the initial launch entry — no longer accurate.

### Pedagogy (carried into the new sections)
- Same warm-mentor tone, real-code-first, line-by-line deep dives (what / why / what-Python-does-internally).
- `boardly` continues as the running example — every new section reuses the same `Project`/`User`/`Ticket` models.
- Version-gating preserved: `StrEnum` (3.11+), `Buffer` ABC (3.12), `walk()` (3.12), `typing.deprecated` (3.13+), `Queue.shutdown` (3.13+), `uuid7` (3.14+), PEP 649 deferred-evaluation default (3.14+) — all marked explicitly in the lessons.
- Plain Markdown bold labels (`**Warning — Title**` etc.) — no emojis, no Obsidian callouts. Identical rendering in Obsidian, GitHub, VS Code, and the Next.js viewer.

### Verified versions (carried forward)
- Python sandbox runtime: **3.12.15** (every runnable example targets 3.12).
- Python current stable upstream: **3.14.x**.
- All 29 primary sources in [[25-Reference-Library/Source-Register]] remain accessed 2026-10-23 — no new sources were consulted for the 14-section deepening pass (the CPython `docs.python.org` references cover every new section).

## [2026-10-25]: 15-agent review pass

### Reviewed
- **15 specialist reviewers** audited the 14 newly-complete sections plus the spine files. Each reviewer was scoped to one concern:
  - Spine-file accuracy (Curriculum-Index, Roadmap, Progress-Tracker, Concept-Registry, Glossary, Changelog, Engineering-Decision-Log)
  - Frontmatter consistency (every lesson has `title`/`aliases`/`tags`/`status`/`prerequisites`/`related_lessons`/`first_taught_in` where canonical; every canonical is in [[00-Start-Here/Concept-Registry]])
  - Wikilink integrity (every `[[folder/Lesson]]` resolves to a real file; no broken cross-links)
  - Mermaid diagram validity (every `mindmap`/`flowchart`/`sequenceDiagram` block parses; no `style` on mindmap blocks)
  - Code-block language tags (every fenced block declares `python`/`bash`/`yaml`/`text`/`mermaid`)
  - Bold-label note convention (no `> [!callout]` syntax, no emojis, no Obsidian-only syntax)
  - Source citations (every lesson's `## Sources` section cites a canonical `docs.python.org` URL with `accessed 2026-10-23`)
  - Version-gating (every 3.13+ or 3.14+ feature is marked explicitly)
  - Lesson-template adherence (the 13-section spine documented in [[24-Templates/Lesson-Template]])
  - Prerequisites & cross-links (every `prerequisites:` wikilink resolves; no orphan cross-links)
  - The `boardly` running example consistency across the 14 new sections
  - Canonical frontmatter (`first_taught_in` value matches the lesson's own path)
  - MOC ↔ Curriculum-Index consistency (every section's `00-*-MOC.md` lesson list matches the Curriculum-Index entry)
  - Concept-Registry ↔ canonical-frontmatter consistency (the registry's table matches the set of files with `first_taught_in:`)
  - Progress-Tracker ↔ Curriculum-Index consistency (every lesson in the index has a checkbox in the tracker)

### Fixed
- Where reviewers found mismatches (e.g. Curriculum-Index lesson titles that drifted from the lesson's own `title:` field; Progress-Tracker checkboxes that missed a lesson; Concept-Registry entries that under-counted canonicals; Glossary terms missing for newly-completed sections; Changelog and Engineering-Decision-Log out of date for the deepening pass) — the spine files were edited directly. The 15-agent review produced no lesson-content changes; all fixes were spine-file accuracy fixes.

## [2026-10-26]: Final cleanup

### Added
- D-007 ("All 23 sections complete") to the [[25-Reference-Library/Engineering-Decision-Log]].
- Phase 7 sub-phase headings (7a–7e) to [[00-Start-Here/Complete-Learning-Roadmap]] and [[00-Start-Here/Progress-Tracker]] so the 14-section reading order is navigable.
- The "Concepts first-taught in this section" pattern was already in 14 of the 23 MOCs; the cleanup pass verified all 23 MOCs surface their canonicals explicitly.

### Changed
- The opening paragraph of `00-Start-Here/Welcome` and the root `README.md` were verified accurate — "23 sections, 152 files, all 23 content sections complete" — and left as-is.
- [[00-Start-Here/Concept-Registry]] restructured from a flat 26-row table to a per-section layout (23 sub-tables) so the canonicals are grouped by the section they live in — easier to scan when a reader is mid-section.
- The closing count line in [[00-Start-Here/Concept-Registry]] now reads "57 canonical lessons across all 23 content sections" with a per-section breakdown.

### Removed
- The stale "Phase 7 — coming-soon sections" placeholder in [[00-Start-Here/Complete-Learning-Roadmap]] (replaced by the five-sub-phase structure above).
- The stale "Phase 7 — Coming soon" MOC-stub checkboxes in [[00-Start-Here/Progress-Tracker]] (replaced by 57 per-lesson checkboxes).

### Verified
- `find … -exec grep -l '^first_taught_in:' … | wc -l` returns **57** (was 26 before the deepening pass).
- `find … ! -name '00-*' ! -name 'Lesson-Template.md' ! -name 'README.md' ! -path '*/00-Start-Here/*' ! -path '*/25-Reference-Library/*' … | wc -l` returns **117** actual lesson files (was 69 before the deepening pass).
- Total markdown files: **152** (117 lessons + 23 MOCs + 7 spine + 1 template + 3 reference + 1 README).
