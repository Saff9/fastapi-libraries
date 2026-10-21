---
title: "Welcome"
aliases:
 - Start Here
 - Welcome
tags:
 - welcome
 - start-here
status: complete
---

# Welcome to the Standard Library FastAPI Builds On

*The course that teaches the Python primitives underneath FastAPI, Pydantic, and every modern async backend — `typing`, `dataclasses`, `collections.abc`, `functools`, `contextlib`, `inspect`, and the rest.*

**You're at the very beginning of the course.** Pull up a chair.

If you have ever written `Annotated[int, Depends(get_db)]` in a FastAPI route and not known exactly what `Annotated` does — or what `inspect` call FastAPI makes to read it — this course is for you. If you have ever shipped a `@dataclass` and wondered why `frozen=True` makes it hashable but `slots=True` makes it smaller, this course is for you. If you have ever debugged a `contextvars` value that was None inside an `asyncio.gather` and not known why, this course is for you. You are in good company. Every senior backend engineer was once exactly here.

Take your time. Type every example into a REPL. Read the source of the standard library when a lesson points you to it. **This is how you learn.**

#start-here #welcome

## What this course is

Twenty-three sections, one per standard-library module that FastAPI leans on. Each section is a handful of lessons; each lesson is a complete, runnable Python file followed by a line-by-line deep dive that explains *what* each line does, *why* it is there, and *what Python does internally* when it runs. The lessons are opinionated: they name the decision, give both sides, and commit. The examples all run on Python 3.12 (the vault's runtime); features that require 3.13 or 3.14 are version-gated and clearly marked.

## What this course is not

It is not a FastAPI tutorial. We mention FastAPI constantly — the whole point is to show you what FastAPI is built on — but we do not teach FastAPI itself. We teach the stdlib primitives that, once internalised, make FastAPI read like plain English. We also do not teach third-party libraries (Pydantic, SQLAlchemy, httpx) except as comparison points in the `dataclasses` vs Pydantic vs `TypedDict` lesson and a few others.

## How to read a lesson

Every substantive lesson follows the same spine:

1. **Opening welcome** — one bold line that acknowledges where you are.
2. **Learning Objectives** — the contract. By the end you can do X.
3. **Prerequisites** — the on-ramp, with a wikilink to the canonical lesson that fixes the gap.
4. **The Problem** — the real bug or failure mode this module prevents.
5. **The Code** — one complete, runnable file before any abstraction.
6. **Line-by-Line Deep Dive** — every meaningful block, walked with what/why/internal treatment.
7. **Execution Trace** — the real terminal output when the code runs.
8. **Common Mistakes** — the buggy code, the symptom, the why, the fix.
9. **Engineering Trade-Offs** — the decision, both sides, the commit.
10. **Exercises** — 3–6 of increasing difficulty, each with a `Verify:` command.
11. **Verification** — copy-paste command + expected output.
12. **Previously Learned Here / What's Next** — the connective tissue.
13. **Sources** — the canonical URL and the access date.

## Where to go next

Open [[00-Start-Here/Curriculum-Index]] for the full table of contents, or [[00-Start-Here/Complete-Learning-Roadmap]] for the suggested reading order. If you are not sure where to start, start with [[01-typing/01-Type-Hints-Basics]] — `typing` is the module FastAPI introspects on every request, and it is the prerequisite for half the other sections.

**Welcome. Open the first lesson. We'll see you at the end.**
