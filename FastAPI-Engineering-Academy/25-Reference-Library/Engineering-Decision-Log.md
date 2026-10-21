---
title: Engineering Decision Log
aliases:
 - Decision Log
 - ADR
tags:
 - reference
 - decisions
status: complete
---

# Engineering Decision Log

Architectural decisions for this vault, with context, decision, and reasoning.

## D-001: Teach the stdlib before the framework

**Context:** The course teaches the Python standard library modules that FastAPI, Pydantic, and SQLAlchemy build on (`typing`, `inspect`, `dataclasses`, `contextvars`, `functools`, etc.) rather than teaching FastAPI itself.

**Decision:** Teach the primitives first. Mention FastAPI constantly (the whole point is "what is FastAPI built on?") but do not teach FastAPI's own API.

**Reasoning:** FastAPI is not magic — it is `inspect.signature` + `typing.get_type_hints(include_extras=True)` + `contextvars.ContextVar` + `functools`. A senior engineer who has internalised the primitives reads `Annotated[int, Depends(get_db)]` as plain English. A junior who skips the primitives memorises incantations. The primitives are stable (the stdlib doesn't break); FastAPI's surface area changes every release. The investment compounds.

## D-002: Target Python 3.12 for runnable examples; version-gate 3.13+/3.14+

**Context:** The sandbox runtime is Python 3.12.15 (Oct 2026). The current stable upstream is Python 3.14.x.

**Decision:** Every runnable code example targets 3.12 so it executes in the vault's playground. Features that require 3.13 or 3.14 (e.g. `typing.deprecated` PEP 702 in 3.13, `uuid7` in 3.14, `Queue.shutdown` in 3.13, PEP 649 deferred-annotations default in 3.14) are version-gated explicitly: `**Python 3.13+:** ...`.

**Reasoning:** 0 errors means the student can copy-paste every `Verify:` command and see the claimed output. If we targeted 3.14 exclusively, the sandbox runs would fail and the verification contract breaks. The version-gating preserves the senior-reader honesty: we tell you exactly when each feature arrived.

## D-003: No Obsidian callouts, no emojis — plain Markdown bold labels

**Context:** The vault renders in Obsidian, GitHub, VS Code, and the companion Next.js viewer. Obsidian callouts (`> [!type]`) are Obsidian-specific syntax that renders as plain blockquotes everywhere else.

**Decision:** Notes, tips, warnings are written as plain Markdown — a bold label (`**Warning — Title**`, `**Tip — Title**`, `**Note — Title**`, `**Danger — Title**`, `**Example — Title**`, `**Title**` for info/success/question) followed by the body as ordinary paragraphs. No emojis.

**Reasoning:** Plain bold labels render identically in every Markdown renderer. The vault is portable. The bold label carries the semantic role that an emoji or a callout icon would have carried. The budgets per lesson (`Warning 3–7`, `Tip 2–5`, etc.) keep the structural signal without the visual noise.

## D-004: `boardly` as the single growing example

**Context:** The original "FastAPI Engineering Academy" vault (now deleted) threaded a `boardly` project-management API through its lessons. The new stdlib course needed a running example.

**Decision:** Keep `boardly` (a project-management API with `Project`, `User`, `Ticket` models) as the running example across the new course's lessons.

**Reasoning:** Continuity. The student who downloaded the previous vault already knows `boardly`. The same models reappear (`boardly/models.py` with `@dataclass` classes, `boardly/deps.py` with `Annotated[..., Depends()]` signatures) so the student sees the stdlib primitives applied to a codebase they already half-know. A new example would force re-learning the domain.

## D-005: Canonical lessons — each concept taught once, linked everywhere

**Context:** A concept like `Annotated` or `get_type_hints` appears in many lessons. Re-explaining it each time bloats the vault and creates drift.

**Decision:** Each concept has one canonical lesson (tagged `canonical` in frontmatter, with a `first_taught_in` field). Other lessons link to the canonical instead of re-explaining. The [[00-Start-Here/Concept-Registry]] lists all canonicals.

**Reasoning:** Single source of truth. If the API changes, one lesson updates and every link still works. The student who needs the prerequisite reads the canonical once; the student who doesn't skips the link. 26 canonicals across 8 sections.

## D-006: 14 sections are MOC stubs — honest "coming soon"

**Context:** The course has 23 content sections. 9 are complete (01, 02, 03, 04, 05, 06, 09, 10, 13); 14 are not yet written (07, 08, 11, 12, 14–23).

**Decision:** Each of the 14 unwritten sections has a `00-*-MOC.md` stub that lists the planned lessons and cross-links to the closest complete section. The stubs are tagged `status: stub` and marked `**Status:** coming soon`.

**Reasoning:** The sidebar tree shows every planned section, so the student sees the full scope and knows where each future lesson will live. The cross-links mean a student who arrives at a stub can still learn the closest-available material. Honesty over false completeness — no stub pretends to be a lesson.

## D-007: All 23 sections complete — spine files are the source of truth

**Context:** As of 2026-10-26, all 23 content sections are complete: 117 lessons, 23 `00-*-MOC.md` files, 57 canonical lessons with `first_taught_in` frontmatter. The D-006 "14 sections are MOC stubs" decision is now superseded — there are no remaining stubs.

**Decision:** The spine files in `00-Start-Here/` (Curriculum-Index, Complete-Learning-Roadmap, Progress-Tracker, Concept-Registry, Glossary) and `25-Reference-Library/` (Changelog, Engineering-Decision-Log, Source-Register) are the canonical source of truth for the vault's structure. When the lesson files change (a new lesson added, a canonical introduced, a section reorganised), the spine files are updated to match. The reverse also holds: if the spine files claim a lesson that doesn't exist, that is a bug to fix — not a forward-looking placeholder.

**Reasoning:** After the 14-section deepening pass and the 15-agent review pass, the spine files were audited and aligned with the actual file tree. The verification commands are stable:

- `find … -name '*.md' … -exec grep -l '^first_taught_in:' {} + | wc -l` returns **57** canonical lessons (one per concept).
- `find … ! -name '00-*' ! -name 'Lesson-Template.md' ! -name 'README.md' ! -path '*/00-Start-Here/*' ! -path '*/25-Reference-Library/*' … | wc -l` returns **117** actual lesson files.
- Total markdown files in the vault: **152** (117 lessons + 23 MOCs + 7 spine + 1 template + 3 reference + 1 README).

The spine-file-as-source-of-truth rule means a senior engineer reading only the spine files can answer "what does this course teach?" without walking the file tree. The 15-agent review pass confirmed the spine files matched reality on 2026-10-25; the final cleanup pass on 2026-10-26 closed the residual mismatches (Curriculum-Index already accurate; Roadmap Phase 7 was a "coming soon" placeholder; Progress-Tracker Phase 7 had MOC-stub checkboxes only; Concept-Registry undercounted canonicals at 26 vs the real 57; Glossary was missing terms from the 14 newly-completed sections; Changelog and Decision-Log had not been updated to record the deepening pass). All six spine files now reflect the full 23-section scope.

The decision commits the project to a maintenance contract: any future lesson addition (a new canonical, a new section, a reorganisation) MUST be reflected in the spine files in the same change set. A lesson file that lacks a corresponding Curriculum-Index entry, Progress-Tracker checkbox, or — for canonicals — Concept-Registry row is a bug.
