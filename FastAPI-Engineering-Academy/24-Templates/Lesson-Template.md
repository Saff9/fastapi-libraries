---
title: Lesson Template
aliases:
 - Lesson Template
tags:
 - template
status: complete
---

# Lesson Template

Use this structure for every substantive lesson in this vault. Adapt only when a topic genuinely needs a different format (reference sheets, glossary entries, MOCs, comparison tables). Every lesson follows this exact 13-section spine.

**Warning — When NOT to use this template**

This 13-section spine is for lessons that teach a *code-first* stdlib module — a single Python file the student will type, run, and modify. Do not use it for:
- **Reference sheets** (method lists, ABC hierarchies) — use a compact table-driven format.
- **Glossary entries** — use the one-paragraph-per-term format in [[00-Start-Here/Glossary]].
- **MOC (map-of-content) files** — use the `00-`-prefixed folder index format with a one-sentence summary per linked lesson (see any `00-*-MOC.md`).
- **Comparison lessons** (e.g. `dataclass` vs Pydantic vs `TypedDict`) — you may still use this spine, but the "Line-by-Line Deep Dive" walks three files side by side.

If you are unsure, open the closest existing lesson in the same folder and match its section list.

## The style (non-negotiable)

1. **Warm mentor tone.** Write it like you are talking to one student, not a class. Use "you", "we", and "let's". End encouragement-heavy lessons with a line like "Take your time. Type every example. **This is how you learn.**"
2. **Real-code-first.** Show one complete, runnable Python file before any abstraction. The file must run on Python 3.12 (the vault runtime). Keep it 20–100 lines; extract boilerplate into `# ... (setup)` comments only when it is truly irrelevant.
3. **Line-by-line deep dive.** Walk every meaningful block under `### Lines N–M: Block name` headings. Repeat the 3–8 lines under each heading (do not reference "the code block above" — the student reads top-to-bottom). For each block, explain **what** it does, **why** it is there, and **what Python does internally** when it runs. The "internal" treatment is what makes this a senior lesson, not a tutorial.
4. **Inline self-asking Q&A.** At least 3 per lesson, aim for 5. Use the `**Why X:**` format: a bold question, then a multi-sentence answer that names the trade-off explicitly.
5. **Plain Markdown notes — no Obsidian callouts.** Use bold labels: `**Warning — Title**`, `**Tip — Title**`, `**Note — Title**`, `**Danger — Title**`, `**Example — Title**`, `**Bug — Title**`, `**Title**` (for info/success), `**Title**` (for questions — the title usually contains the question). The body follows as ordinary paragraphs. No emojis. The labels render identically in Obsidian, GitHub, VS Code, and the Next.js viewer.
6. **0 errors.** Only use verified Python 3.12 API signatures. If a feature requires Python 3.13 or 3.14, version-gate it explicitly: "**Python 3.13+:** `typing.deprecated` (PEP 702) ...". Never invent an API. If unsure, cite the CPython source file and line.
7. **One growing application.** Where a lesson needs a running example, use `boardly` — a project-management API. The same models (`Project`, `User`, `Ticket`) reappear across lessons so the student sees continuity.

## The 13-section spine

````markdown
---
title: "Lesson NN: <Title>"
aliases:
 - <Short alias>
tags:
 - <topic>
 - <topic>
 - canonical        # only when this is the canonical lesson for a registered concept
status: complete
course_level: <beginner|intermediate|advanced>
difficulty: <beginner|intermediate|advanced>
estimated_time: "<N–M minutes>"
prerequisites:
 - "[[<folder>/<Lesson>]]"
related_lessons:
 - "[[<folder>/<Lesson>]]"
first_taught_in: "<folder>/<Lesson>"   # only on canonical lessons
---

# Lesson NN: <Title>

*<One-line italic summary — what boardly feature or real bug this lesson teaches.>*

**You're at the very beginning of Section NN.**

<2–4 sentences of warm welcome. Acknowledge where the student is. Set the tone. End with "Take your time. Type every example. **This is how you learn.**" on lessons that warrant it.>

#<topic> #<topic2> #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **<Verb-led objective>** — <one-sentence clarification>.
2. ...

## Prerequisites

Before starting, you need:

- **<Prerequisite>** — <one sentence + wikilink to the canonical lesson that fixes the gap>.
- **About <N> minutes of focused time.**

**<The most common gap: <topic>.>**

<2–4 sentences explaining the single most common gap that blocks students.>

## The Problem

<Name the real bug or failure mode this module prevents. 2–4 paragraphs. Ground it in a specific symptom the student has hit or will hit.>

## The Code

```python
# <file path>
"""<module docstring>"""
<complete runnable code, 20–100 lines>
```

## Line-by-Line Deep Dive

### Lines 1–8: <Block name>

<Repeat the 3–8 lines here. Then explain what, why, and what-Python-does-internally.>

### Lines 9–15: <Block name>

<...>

## Execution Trace

```bash
$ uv run python boardly/feature.py
<actual terminal output>
```

## Common Mistakes

### Mistake 1: <symptom>

```python
<buggy code>
```

**Symptom:** <what the student sees>
**Why:** <the root cause>
**Fix:** <the corrected code>

## Engineering Trade-Offs

**Decision:** <the choice this lesson commits to>
**Both sides:** <the alternative + when it wins>
**Commitment:** <what the boardly project does and why>

## Exercises

1. **Exercise 1 — <name>.** <instructions>. `Verify: <command>`
2. ...

## Verification

```bash
$ <exact command>
<exact expected output>
```

## Previously Learned Here

- [[<folder>/<Lesson>]] — <one sentence on what was taught>

## What's Next

[[<folder>/<Next-Lesson>]] — <one paragraph + three bullets on what comes next>

## Sources

- **<Source>** — <URL> — accessed 2026-10-23 — <one-sentence "why useful">

## What We Learned

<4–6 past-tense achievement bullets — "you can now do X".>
````

## Conventions

- Filenames: numbered, kebab-case (e.g. `03-Annotated-and-Metadata.md`).
- `00-`-prefixed files are MOCs for a folder.
- Lesson titles use `# Lesson NN: <Title>` (colon).
- Code blocks declare language (`python`, `bash`, `yaml`, `text`).
- Mermaid blocks use `style <Node> fill:#…,stroke:#…` (or `classDef`) ONLY in `flowchart`/`graph` blocks. For `sequenceDiagram`, `erDiagram`, `classDiagram`, `mindmap`, do NOT use `style` (parse error). For `sequenceDiagram` region colouring, use `rect rgb(R, G, B) ... end`.
- Open every lesson with a bold `**You're at the very beginning of Section NN.**` welcome line.
- Frontmatter `first_taught_in` only on canonical lessons (the lesson that first teaches a registered concept).
- Use the inline self-asking Q&A pattern (`**Why X:**` + answer) at least 3 times per lesson; aim for 5.
- Tags line (`#<topic> …`) immediately follows the opening welcome line.
- All versions must match the verified Oct 2026 facts: Python 3.12.15 runtime (sandbox), Python 3.14.x current stable upstream. 3.13+/3.14+ features are version-gated where they appear.
- Sources entries use `**<Title>** — <URL> — accessed 2026-10-23 — <one-sentence "why useful">`.
- Code blocks inside the Line-by-Line Deep Dive *repeat* the lines being explained. The student reads top-to-bottom; making them scroll up breaks the close-reading rhythm.
- `### Lines N-M: <heading>` headings name the *block* (what those lines do as a unit), not the line numbers alone.
- Exercises ramp difficulty: Exercise 1 is "modify one line and re-run"; the final exercise is "extend the artifact with a new feature the lesson didn't cover". Each exercise ends with a `Verify:` command.
- Verification blocks paste the *actual* expected terminal output, not a paraphrase.

## Note & Warning Style Guide

Notes, tips, warnings are written as plain Markdown — a bold label on its own line followed by the body as ordinary paragraphs. No emojis.

| Label | Role | When to use | Budget per lesson |
|------|------|--------------|-------------------|
| `**You're at the very beginning of Section NN.**` | Opening welcome | Open the lesson. | 1 |
| `**Title**` (info) | Reference / "what's actually in X" | Bridge a knowledge gap, point to a canonical lesson. | 3–6 |
| `**Tip — Title**` | Shortcut / FAQ | Answer the question the student is about to ask. | 2–5 |
| `**Note — Title**` | Historical context / recap | What was used before and why it changed. | 1–2 |
| `**Title**` (question) | Self-asking Q&A | Inline quiz the student answers in their head. Minimum 3 per lesson; aim for 5. | 3–5 |
| `**Example — Title**` | "What's actually in X?" enumeration | List the related exports the student will meet later. | 1–3 |
| `**Warning — Title**` | One-line rule that prevents a recurring bug | A rule the student must internalise. | 3–7 |
| `**Danger — Title**` | Production-incident-level trap | A trap that has caused a real incident. | 2–4 |

The budgets are upper bounds, not targets.
