---
title: "Lesson 01: Logger, Handler, Formatter"
aliases:
 - logging.getLogger
 - Logger
 - Handler
 - Formatter
 - propagate
 - root-logger gotcha
tags:
 - logging
 - logger
 - handler
 - formatter
 - filter
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "35–50 minutes"
prerequisites:
 - "[[06-dataclasses/01-dataclass-Basics]]"
related_lessons:
 - "[[23-logging/02-dictConfig]]"
 - "[[23-logging/03-structured-logging]]"
 - "[[23-logging/04-Uvicorn-logging-integration]]"
first_taught_in: "23-logging/01-Logger-Handler-Formatter"
---

# Lesson 01: `Logger`, `Handler`, `Formatter`

*The four-class hierarchy (`Logger` → `Handler` → `Formatter`, with `Filter` on the side) that every Python log line flows through — and why `logging.getLogger("boardly")` returns the same object every time you call it.*

**You're at the very beginning of Section 23.**

The `logging` module is the part of the standard library that every Python program touches and almost no one reads. You write `import logging; log = logging.getLogger(__name__)` once at the top of a file and forget it. But the moment you ship a FastAPI app and try to interleave your business logs with Uvicorn's access logs, the four-class hierarchy underneath — `Logger` (the entry point), `Handler` (the destination), `Formatter` (the layout), `Filter` (the gate) — stops being optional knowledge. By the end of this lesson you will know why `logging.getLogger("boardly.routers.projects")` returns a logger that inherits from `boardly.routers` that inherits from `boardly`, why the root-logger gotcha (`logging.warning("...")`) silently mutates global state on first call, and what `logger.propagate = False` actually buys you. Take your time. Type every example. **This is how you learn.**

#logging #logger #handler #formatter #filter #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Construct** a named logger with `logging.getLogger("boardly.routers.projects")` and explain the dot-namespaced parent/child hierarchy, the singleton-per-name rule, and the `getEffectiveLevel()` cascade.
2. **Wire** a `Handler` (`StreamHandler`, `FileHandler`, `RotatingFileHandler`) onto a `Logger` and explain the two-level gating: the `Logger` level decides what records are *created*, the `Handler` level decides which of those records it *emits*.
3. **Format** records with `Formatter(fmt, datefmt, style="%"/"{"/"$")` and name all three style back-ends (`PercentStyle`, `StrFormatStyle`, `StringTemplateStyle`).
4. **Filter** by logger-name prefix with `logging.Filter("boardly.routers")` — and articulate why `boardly.routers2` does *not* match (the dot-boundary rule).
5. **Disable** record propagation with `logger.propagate = False` and explain when this is the right move (and when it causes silent log loss).
6. **Avoid** the root-logger gotcha: never call `logging.warning()` / `logging.info()` module-level functions in library code; they trigger `basicConfig()` and pollute the root logger.

## Prerequisites

Before starting, you need:

- **Dataclass basics** — the `boardly` models (`Project`, `Ticket`, `User`) used in examples are `@dataclass` types. See [[06-dataclasses/01-dataclass-Basics]].
- **The `with` block** — used in the file-handler examples. See [[03-contextlib/01-contextmanager]].
- **About 35–50 minutes of focused time.**

**The most common gap: the module-level convenience functions.**

Students reach for `logging.info("...")` (no `getLogger`) because it is the first thing every tutorial shows. It works — exactly once. The second time you call it, the root logger has already been mutated by `basicConfig()`, your `dictConfig` call later in the program has to fight the existing handler, and your library logs leak into every host application that imports you. The fix is one habit: every module begins with `log = logging.getLogger(__name__)`. The rest of this lesson is the *why*.

## The Problem

You ship `boardly/routers/projects.py` and a customer reports that creating a project sometimes takes 6 seconds. You add a print, ship it, and discover that on the staging server your prints go to a container's stdout that the log shipper picks up as unstructured text — no timestamp, no logger name, no level. Worse, your teammate added `logging.info("creating project")` in `boardly/db.py`, and now *both* log streams get mixed into the same root logger handler with different formats, and rotating the file fails because two `FileHandler`s point at the same path.

The `logging` module exists to solve exactly this. It gives you named loggers (so each module owns its own stream), a level cascade (so you can turn `boardly.routers.projects` up to `DEBUG` in staging without touching `boardly.routers.users`), a `Formatter` contract (so the timestamp and request-id are always there), and a `Filter` for the rare case you need a sub-tree gate. But the module is also full of footguns — the root-logger gotcha, the propagation surprise, the dual-level gating — and the only way through it is the four-class hierarchy, one class at a time.

## The Code

```python
# boardly/logging_basics.py
"""Demonstrate the Logger/Handler/Formatter/Filter hierarchy on boardly models."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4


# --- boardly models (subset; see boardly/models.py) ---
@dataclass(frozen=True)
class User:
    id: UUID
    name: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    owner: User


# --- configure the boardly logger by hand (Lesson 02 shows dictConfig) ---
def configure_boardly_logging() -> None:
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # Attach to the top-level boardly logger, NOT the root.
    boardly = logging.getLogger("boardly")
    boardly.setLevel(logging.DEBUG)        # logger-level gate (creates records >= DEBUG)
    boardly.addHandler(console)           # handler-level gate is INFO (above)
    boardly.propagate = False             # do NOT also walk to the root logger

    # A child logger inherits the handler above via propagation.
    child = logging.getLogger("boardly.routers.projects")
    assert child.parent is boardly        # dot-namespaced parent
    assert child.handlers == []           # child has NO handler of its own


def create_project(name: str, owner: User) -> Project:
    log = logging.getLogger("boardly.routers.projects")  # named, singleton per name
    log.debug("create_project entry: name=%s owner=%s", name, owner.id)
    project = Project(id=uuid4(), name=name, owner=owner)
    log.info("project created: id=%s name=%s", project.id, project.name)
    return project


if __name__ == "__main__":
    configure_boardly_logging()
    alice = User(id=uuid4(), name="alice")
    create_project(name="auth-rewrite", owner=alice)

    # Demonstrate the root-logger gotcha (do NOT do this in library code):
    # logging.info("module-level call")   # would trigger basicConfig() on root
    # Instead: always go through a named logger.
    logging.getLogger("boardly").info("done")
```

## Line-by-Line Deep Dive

### Lines 7–22: The boardly models

```python
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class User:
    id: UUID
    name: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    owner: User
```

These are the `boardly` models you have met in earlier sections — frozen dataclasses with UUID primary keys. They appear here only so the demo has real objects to log. The `frozen=True` matters for one reason: a `LogRecord` captures the *value* of the field at log time, so mutable state would be a footgun in any non-trivial program. Frozen dataclasses remove that footgun.

**Why frozen models for loggable state?** Because a `LogRecord` keeps a reference to the objects you pass as args — `log.info("project %s", project)` stores `project` on `record.args` and only interpolates at format time. If `project` is mutable and another thread mutates it between the `log.info` call and the formatter's `getMessage()` call, the logged value is the *post-call* value, not the at-call value. Frozen dataclasses sidestep this entirely. For mutable objects (lists, dicts, mutable dataclasses), pass `repr(obj)` or `str(obj)` instead of the object.

### Lines 25–43: `configure_boardly_logging()`

```python
def configure_boardly_logging() -> None:
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    boardly = logging.getLogger("boardly")
    boardly.setLevel(logging.DEBUG)
    boardly.addHandler(console)
    boardly.propagate = False
```

This is the entire wiring diagram in eight lines. Walk it carefully.

`logging.Formatter(fmt=..., datefmt=...)` constructs a `Formatter` object. The default `style` is `"%"`, so `%(asctime)s` is a `%`-style interpolation field into a `LogRecord`'s attributes. The fields available are documented (`%(asctime)s`, `%(name)s`, `%(levelname)s`, `%(message)s`, `%(process)d`, `%(thread)d`, `%(filename)s`, `%(lineno)d`, and ~20 more); you do not need to memorise them, but you do need to know `%(asctime)s` is the timestamp formatted via `datefmt`, and `%(name)s` is the logger name (the string you passed to `getLogger`).

`logging.StreamHandler()` with no argument writes to `sys.stderr`. `setLevel(logging.INFO)` is the *handler-level* gate — even if the logger hands the handler a `DEBUG` record, this handler will skip it because `INFO` > `DEBUG`. This is the two-level gating rule: the logger decides which records *exist*, the handler decides which it *emits*. Students who set the logger to `DEBUG` and forget to also drop the handler to `DEBUG` will see no extra log lines and assume `logging` is broken. It is not.

`logging.getLogger("boardly")` is the singleton call. The first time you call it with the name `"boardly"`, CPython creates a `Logger` instance and stores it in the global `logging.Logger.manager.loggerDict`. The second time you call `getLogger("boardly")` — from any module, in any thread — you get the *same* object back. That is why `boardly.addHandler(console)` in one module persists for every other module that later calls `getLogger("boardly")`.

`setLevel(logging.DEBUG)` is the *logger-level* gate. The default level for a non-root logger is `NOTSET` (= `0`), which means "defer to my parent" — but here we set the level explicitly so `boardly` *creates* records at `DEBUG` and above.

`propagate = False` is the off-switch for the propagation walk. By default, after a logger's own handlers run, the `LogRecord` walks up the parent chain (root logger included) and is offered to every ancestor's handlers. Setting `propagate = False` stops the walk at this logger. Use it when you have configured a handler on a sub-tree logger and you do not want those records to *also* be emitted by the root logger (which is the default double-emit surprise).

**Why does propagation exist at all?** Because without it you could not configure a handler on the `boardly` logger and have it serve every descendant (`boardly.routers.projects`, `boardly.routers.users`, etc.). The propagation walk is the mechanism that lets one handler on a parent logger fan out to every child. The flip side — the double-emit surprise — happens when *both* a child logger has its own handler *and* the parent has one; both fire because propagation is on. The fix is `propagate = False` on the child, not on the parent.

**Why set the handler level *and* the logger level?** Because they gate at different points. The logger level is checked *first* — when you call `log.debug(...)`, the logger checks `record.levelno >= self.getEffectiveLevel()`. If the logger level is `INFO` and the record is `DEBUG`, the record is never created (no `LogRecord` instance, no `handler.handle()` call). The handler level is checked *second*, in `handler.handle(record)`: even if the record was created, the handler can still skip it. This two-stage gate lets you have one logger feed two handlers at different levels — e.g. a `console` handler at `INFO` (so the terminal is readable) and a `file` handler at `DEBUG` (so the file has everything). One logger, two handlers, two effective levels.

### Lines 45–48: The child logger

```python
    child = logging.getLogger("boardly.routers.projects")
    assert child.parent is boardly
    assert child.handlers == []
```

`child.parent is boardly` is the dot-namespaced hierarchy in one line. When you ask for `getLogger("boardly.routers.projects")`, CPython internally calls `logging.Logger.manager.loggerDict` and splits the name on dots: `boardly` → `boardly.routers` → `boardly.routers.projects`. If any intermediate logger does not exist yet, it is created lazily and linked via `.parent`. So `child.parent.name == "boardly.routers"` and `child.parent.parent.name == "boardly"`. The chain ends at the root logger (`logging.getLogger()` with no args, or `logging.root`).

`child.handlers == []` confirms that the child has no handler of its own. When `child.info("project created")` is called, the record is created at the child's effective level, the child's handlers (none) are tried, and then — because `propagate` is `True` by default on the child — the record walks up to `boardly.routers` (also no handlers), then to `boardly` (the `console` handler we added), and is emitted there. **The handler on `boardly` is shared by every descendant of `boardly`.** This is why we only configure the top-level `boardly` logger: every `boardly.routers.*` logger inherits the console handler via propagation.

### Lines 51–57: `create_project`

```python
def create_project(name: str, owner: User) -> Project:
    log = logging.getLogger("boardly.routers.projects")
    log.debug("create_project entry: name=%s owner=%s", name, owner.id)
    project = Project(id=uuid4(), name=name, owner=owner)
    log.info("project created: id=%s name=%s", project.id, project.name)
    return project
```

The pattern to copy into every module: `log = logging.getLogger(__name__)`. With `__name__ == "boardly.routers.projects"` (the module's dotted name), the logger name *is* the module name — so the `%(name)s` field in your formatter shows exactly which module produced the line. The `log.debug(...)` / `log.info(...)` calls take a `%`-style format string and positional args. This is intentional: the formatting is *lazy*. If the logger's effective level is `INFO`, the `log.debug(...)` call short-circuits *before* the format string is interpolated — saving the cost of building the message string. Never use f-strings inside `log.debug(f"...")` calls; the f-string is evaluated *before* `debug` is called, defeating the short-circuit.

### Lines 60–66: The `__main__` block

```python
if __name__ == "__main__":
    configure_boardly_logging()
    alice = User(id=uuid4(), name="alice")
    create_project(name="auth-rewrite", owner=alice)
    # logging.info("module-level call")   # would trigger basicConfig() on root
    logging.getLogger("boardly").info("done")
```

`configure_boardly_logging()` is the one-time setup call. In a real FastAPI app this lives in `boardly/logging_config.py` and is called from `boardly/main.py` before `app = FastAPI()`. The commented-out `logging.info("module-level call")` is the **root-logger gotcha** — see the section below.

**Why the dot namespace and not flat names?** Because the dot is the parent/child boundary. `boardly.routers.projects` is a *child* of `boardly.routers` which is a *child* of `boardly`. The `logging` module splits the name on `.` to build the tree. A flat name like `boardly-routers-projects` would be a *single* logger with no parent (other than root), so you could not say "set everything under `boardly.routers` to `DEBUG`" in one `dictConfig` line. The dot namespace is the lever that makes `dictConfig` (Lesson 02) tractable.

## Execution Trace

```bash
$ python boardly/logging_basics.py
2026-10-23T06:36:39 INFO     boardly.routers.projects :: project created: id=485a394a-a0c6-4b6e-8bad-7a5c1a7ba795 name=auth-rewrite
2026-10-23T06:36:39 INFO     boardly :: done
```

(The UUID and timestamp will differ on your run — `uuid4()` is random and the timestamp is wall-clock at format time.) The `DEBUG` line for `create_project entry` did *not* print. The `boardly` logger level is `DEBUG`, but the *handler* (`console`) is set to `INFO`, so the handler skips it. This is the two-level gating in action.

## Common Mistakes

### Mistake 1: Calling `logging.info()` / `logging.warning()` in library code

```python
import logging
logging.info("creating project")   # WRONG — this is the root-logger gotcha
```

**Symptom:** Your library's logs leak into every host application's root logger, your `dictConfig` setup later in the program has to fight the handler that `basicConfig()` already added, and rotating-file setups silently fail because two handlers point at the same path.

**Why:** The module-level convenience functions (`logging.debug`, `logging.info`, `logging.warning`, `logging.error`, `logging.critical`) are documented in the `logging` module's source as: *if the root logger has no handlers, call `basicConfig()` first, then dispatch the call to the root logger.* `basicConfig()` adds a `StreamHandler` to `sys.stderr` with the formatter `%(levelname)s:%(name)s:%(message)s`. After that call, the root logger has a handler — permanently, for the rest of the process. Any `dictConfig` later has to either explicitly clear it or rely on `disable_existing_loggers=True` (the default).

**Fix:** Always use named loggers. `log = logging.getLogger(__name__)` at the top of every module, then `log.info(...)`. Never call `logging.info(...)` directly in code that someone else might import.

### Mistake 2: Forgetting the two-level gating

```python
boardly.setLevel(logging.DEBUG)
console = logging.StreamHandler()
console.setFormatter(fmt)
boardly.addHandler(console)
# Later, in boardly/routers/projects.py:
log.debug("entry")   # SILENT — nothing prints
```

**Symptom:** You dropped the logger level to `DEBUG` and your `debug` lines still do not appear.

**Why:** The logger level says "create the `LogRecord` if the level passes." The handler level says "emit the record if the level passes." You set the logger to `DEBUG` but left the handler at its default (`NOTSET`/`0`, which on a `StreamHandler` means "emit anything the logger hands me" — *unless* the handler was given a level at construction). If you did `console.setLevel(logging.INFO)` (as the code above does), the handler will drop `DEBUG` records. This is *intended* — you can have one logger feed two handlers, one for `INFO` (stdout) and one for `DEBUG` (a debug file).

**Fix:** Set *both* levels. `boardly.setLevel(logging.DEBUG)` AND `console.setLevel(logging.DEBUG)`.

### Mistake 3: `propagate = False` on the wrong logger

```python
boardly = logging.getLogger("boardly")
boardly.addHandler(console)
boardly.propagate = False   # WRONG if you actually wanted records to ALSO reach root
```

**Symptom:** Your `boardly` logs show up on the console handler but never reach the root logger's file handler that you configured separately.

**Why:** `propagate = False` stops the record walk at the current logger. The root logger's handlers never see it. This is sometimes what you want (to avoid double-emit) and sometimes a silent log-loss bug. The rule: set `propagate = False` on `boardly` only if you have configured a handler *on* `boardly` and you do not want root's handler to also emit. If you want both, leave `propagate = True` (the default).

**Fix:** Audit whether you have handlers on both `boardly` and root. If yes, set `propagate = False` on the child to avoid double-emit. If no, leave it `True`.

## Engineering Trade-Offs

**Decision:** Use named loggers (`getLogger("boardly.routers.projects")`) and configure only the top-level `boardly` logger, leaving `propagate = True` on descendants.

**Both sides:** The alternative — configuring a separate handler on every module's logger — gives you per-module output streams (e.g. `projects.log` separate from `users.log`). It wins when one subsystem's logs are so noisy they would drown the others. It loses on configuration overhead: each module needs its own handler entry in `dictConfig`, and rotation has to be configured per-handler.

**Commitment:** The `boardly` project configures only `boardly` (and `uvicorn.access` — see Lesson 04) and relies on propagation for every descendant. The `%(name)s` field in the formatter tells you which module produced the line; the file destination is shared. This is the standard FastAPI/Starlette/Uvicorn idiom.

## Exercises

1. **Exercise 1 — Drop the handler level.** Change `console.setLevel(logging.INFO)` to `console.setLevel(logging.DEBUG)` and re-run. The `DEBUG` line for `create_project entry` should now appear. `Verify: python boardly/logging_basics.py | head -5`
2. **Exercise 2 — Add a second handler.** Add a `FileHandler("boardly.log")` at `DEBUG` level to the `boardly` logger, leaving the console handler at `INFO`. Both should fire; the file should also contain the `DEBUG` line. `Verify: tail -5 boardly.log`
3. **Exercise 3 — Verify the singleton.** Add `assert logging.getLogger("boardly") is logging.getLogger("boardly")` to the demo and prove it never fails. Now call `configure_boardly_logging()` twice — the handler is added twice. Add a guard: `if not boardly.handlers: boardly.addHandler(console)`. `Verify: python -c "import boardly.logging_basics as m; m.configure_boardly_logging(); m.configure_boardly_logging(); print(len(__import__('logging').getLogger('boardly').handlers))"`
4. **Exercise 4 — Use a `Filter`.** Create `f = logging.Filter("boardly.routers.projects")` and add it to the console handler with `console.addFilter(f)`. Re-run and observe that *only* `boardly.routers.projects` records (and its descendants) reach the console. The `boardly :: done` line should disappear. `Verify: python boardly/logging_basics.py`
5. **Exercise 5 — Switch to `{`-style format.** Rewrite the formatter as `logging.Formatter("{asctime} {levelname:-8} {name} :: {message}", datefmt="%Y-%m-%dT%H:%M:%S", style="{")`. Confirm the output is identical. The `{`-style uses `str.format` semantics, so `{levelname:-8}` left-justifies in an 8-wide field. `Verify: python boardly/logging_basics.py`

## Verification

```bash
$ python boardly/logging_basics.py
2026-10-23T06:36:39 INFO     boardly.routers.projects :: project created: id=485a394a-a0c6-4b6e-8bad-7a5c1a7ba795 name=auth-rewrite
2026-10-23T06:36:39 INFO     boardly :: done
```

The exact UUID will differ — `uuid4()` is random. The exact timestamp will differ — it is `datetime.now(tz=None)` at format time. The structure (ISO date, level, name, `::`, message) is the contract.

## Previously Learned Here

- [[06-dataclasses/01-dataclass-Basics]] — the frozen dataclass pattern used for the `boardly` models in this lesson.
- [[03-contextlib/01-contextmanager]] — the `with` block used in Lesson 02 for `FileHandler` (which is a context manager).

## What's Next

[[23-logging/02-dictConfig]] — you have now wired the `boardly` logger by hand, calling `addHandler` and `setLevel` in Python. That approach does not scale: the moment you have a console handler, a file handler with rotation, a Sentry handler, and per-subsystem levels, the wiring code becomes its own mess. `logging.config.dictConfig(config)` takes a single dict — usually loaded from YAML at app start — and does the whole wiring declaratively. The next lesson walks the schema (`version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`), shows the production YAML pattern, and explains why `dictConfig` is the only config layer you should ship.

- The schema: `version: 1`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`.
- The `disable_existing_loggers=False` rule (otherwise third-party loggers get disabled).
- The `incremental=True` runtime-reconfig flag.

## Sources

- **`logging` — Logging facility for Python** — https://docs.python.org/3/library/logging.html — accessed 2026-10-23 — the canonical reference for `Logger`, `Handler`, `Formatter`, `Filter`, the level constants, and the `%(name)s`/`%(asctime)s`/`%(levelname)s` `LogRecord` attributes.
- **`logging.handlers` — Logging handlers** — https://docs.python.org/3/library/logging.handlers.html — accessed 2026-10-23 — `StreamHandler`, `FileHandler`, `RotatingFileHandler`, `TimedRotatingFileHandler`, `QueueHandler` (3.7+), `QueueListener`.
- **`logging.LogRecord` attributes** — https://docs.python.org/3/library/logging.html#logrecord-attributes — accessed 2026-10-23 — the full list of `%(name)s`-style format fields.

## What We Learned

- You can now construct a named logger with `logging.getLogger("boardly.routers.projects")` and explain the dot-namespaced parent/child chain that ends at the root logger.
- You can now wire a `StreamHandler` (or `FileHandler`, `RotatingFileHandler`) onto a `Logger` with `addHandler`, and articulate the two-level gating rule: logger level creates records, handler level emits them.
- You can now format records with `Formatter(fmt, datefmt, style="%"/"{"/"$")` and choose the right style back-end (`PercentStyle` default, `StrFormatStyle` for `{}`-format, `StringTemplateStyle` for `$`-Template).
- You can now filter by logger-name prefix with `Filter("boardly.routers")`, including the dot-boundary rule (`boardly.routers2` does not match).
- You can now set `logger.propagate = False` to stop the record walk up the parent chain, and explain when this prevents double-emit and when it causes silent log loss.
- You can now avoid the root-logger gotcha — never calling `logging.warning()` / `logging.info()` in library code, always `getLogger(__name__)` first.
