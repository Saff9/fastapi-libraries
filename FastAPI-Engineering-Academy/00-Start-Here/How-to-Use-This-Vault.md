---
title: How to Use This Vault
aliases:
 - How to Use
 - Guide
tags:
 - start-here
status: complete
---

# How to Use This Vault

*Three ways to read this course. Pick the one that fits how you work.*

## 1. The companion Next.js viewer (recommended)

At the project root is a Next.js 16 app that reads the markdown in this folder and renders it with a sidebar tree, search, breadcrumbs, and Mermaid diagrams. To start it:

```bash
cd /home/z/my-project
bun install
bun run dev
```

Open `http://localhost:3000`. The sidebar on the left shows every section and lesson in order. `⌘K` (or `Ctrl-K`) opens the search dialog — type any term and jump to the lesson. Wikilinks inside a lesson are clickable; breadcrumbs at the top show where you are.

The viewer is read-only. You can't edit the markdown from the browser — use Obsidian or your editor for that.

## 2. Obsidian

The vault is plain markdown with Obsidian-style wikilinks (`[[folder/Lesson]]`) and Mermaid code-fence diagrams. To open in Obsidian:

1. Open Obsidian → **Open folder as vault**.
2. Select the `FastAPI-Engineering-Academy/` directory.
3. Wikilinks, Mermaid, and `**bold label**` notes render natively. No community plugins are required.

Obsidian is the best choice if you want to take notes alongside the lessons — it lets you create your own backlinks and annotations.

## 3. GitHub / VS Code / any markdown reader

The vault is plain markdown with no Obsidian-only syntax. Every `**Warning — Title**` note renders as a bold paragraph in GitHub, VS Code's preview, or any CommonMark renderer. Mermaid blocks render natively on GitHub. Wikilinks show as plain text in non-Obsidian readers — use the companion viewer or the [[00-Start-Here/Curriculum-Index]] if you need clickable navigation.

## How to read a lesson

Every substantive lesson follows the 13-section spine documented in [[24-Templates/Lesson-Template]]: Learning Objectives → Prerequisites → The Problem → The Code → Line-by-Line Deep Dive → Execution Trace → Common Mistakes → Engineering Trade-Offs → Exercises → Verification → Previously Learned Here → What's Next → Sources → What We Learned.

Read top-to-bottom the first time. On a re-read, the Line-by-Line Deep Dive is where you'll spend most of your time. The Exercises and Verification sections at the end are the proof that you understood — do not skip them.

**Type every code example into a REPL.** Do not copy-paste. Typing is what makes it stick.

## The `boardly` running example

Most lessons use a single growing application — `boardly`, a project-management API with `Project`, `User`, and `Ticket` models. The same models reappear across lessons so you see continuity. When a lesson says "in `boardly/models.py`", it's referring to the same file the previous lesson built.

## Version pins (2026-10-23)

| Component | Version |
|---|---|
| Python (sandbox runtime) | 3.12.15 |
| Python (current stable upstream) | 3.14.x |
| `typing`, `dataclasses`, `enum`, `inspect`, `collections`, `collections.abc`, `functools`, `contextlib`, `contextvars` | stdlib (3.12 stable; 3.13/3.14 features version-gated) |

Every lesson cites the canonical `docs.python.org` URL and the access date in its `## Sources` section.

## Where to start

If you have written any FastAPI code, start with [[01-typing/02-Annotated-and-Metadata]] — the lesson that explains the primitive underneath every `Depends()` call. If you have not, start with [[00-Start-Here/Welcome]] and follow the [[00-Start-Here/Complete-Learning-Roadmap]].
