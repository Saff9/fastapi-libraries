---
title: "Lesson 02: `dictConfig`"
aliases:
 - logging.config.dictConfig
 - dictConfig
 - incremental reconfig
 - disable_existing_loggers
tags:
 - logging
 - logging-config
 - dictconfig
 - yaml
 - canonical
status: complete
course_level: intermediate
difficulty: intermediate
estimated_time: "30–45 minutes"
prerequisites:
 - "[[23-logging/01-Logger-Handler-Formatter]]"
related_lessons:
 - "[[23-logging/01-Logger-Handler-Formatter]]"
 - "[[23-logging/03-structured-logging]]"
 - "[[23-logging/04-Uvicorn-logging-integration]]"
first_taught_in: "23-logging/02-dictConfig"
---

# Lesson 02: `logging.config.dictConfig`

*The single dict that replaces every `addHandler` / `setLevel` / `addFilter` line of imperative setup — and the schema (`version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`) you read in production YAML.*

**You're at the very beginning of Section 23's second lesson.**

Lesson 01 wired the `boardly` logger by hand: `Formatter(...)`, `StreamHandler()`, `setLevel(...)`, `addHandler(...)`, `propagate = False`. That is six lines for one logger with one handler. Add a file handler with rotation, a Sentry handler, three subsystem loggers, a separate level for staging, and you are looking at thirty lines of imperative setup in `boardly/main.py` that has to be edited for every environment. `logging.config.dictConfig(config)` (added in Python 3.2) takes a single dict — usually loaded from YAML — and does the whole wiring declaratively in one call. The schema has seven top-level keys, only one of which is required (`version`, which must be `1`). By the end of this lesson you will know every key, the production YAML pattern, and why `disable_existing_loggers: false` is the line that prevents your third-party libraries from going silent. Take your time. Type every example. **This is how you learn.**

#logging #logging-config #dictconfig #yaml #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Apply** `logging.config.dictConfig(config)` to a dict — and explain the seven top-level keys: `version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`.
2. **Construct** the `formatters` section (name → `{format, datefmt, style}`) and the `handlers` section (name → `{class, level, formatter, ...}`), including `ext://` references for module attributes like `sys.stderr`.
3. **Wire** the `loggers` section (name → `{level, handlers, propagate}`) and the `root` section, and articulate why `disable_existing_loggers: false` is mandatory in library-bearing code.
4. **Use** `incremental: true` for runtime reconfiguration (level changes only; no new handlers/formatters).
5. **Load** a YAML config file with `yaml.safe_load(open("logging.yaml"))` and pass it to `dictConfig` — the production pattern.
6. **Articulate** why `dictConfig` beats manual `addHandler` setup: declarative, serialisable, diff-able, environment-overridable.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `Logger`/`Handler`/`Formatter`/`Filter` hierarchy, the two-level gating, the propagation walk. See [[23-logging/01-Logger-Handler-Formatter]].
- **About 30–45 minutes of focused time.**

**The most common gap: writing imperative `addHandler` setup in `main.py`.**

Students who have only seen `logging.basicConfig(level=logging.INFO)` in tutorials reach for imperative `addHandler` setup the moment they need two handlers. The result is a `main.py` with 30+ lines of logging setup that has to be copy-pasted into every entry point (`main.py`, `worker.py`, `cli.py`), edited per-environment, and never quite tested. `dictConfig` turns those 30 lines into a YAML file that loads in one line, diffs cleanly in code review, and can be swapped between `logging.dev.yaml` and `logging.prod.yaml` by changing a path. The gap is not knowing the schema.

## The Problem

You ship `boardly/main.py` with this imperative setup:

```python
import logging
from logging.handlers import RotatingFileHandler

fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s :: %(message)s", "%Y-%m-%dT%H:%M:%S")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(fmt)
file = RotatingFileHandler("boardly.log", maxBytes=10_485_760, backupCount=5, encoding="utf-8")
file.setLevel(logging.DEBUG)
file.setFormatter(fmt)

boardly = logging.getLogger("boardly")
boardly.setLevel(logging.DEBUG)
boardly.addHandler(console)
boardly.addHandler(file)
boardly.propagate = False
# ...and the same for boardly.routers.projects, boardly.routers.users, boardly.workers...
```

Four problems. First, the setup is in the wrong place — it should live in `boardly/logging_config.py`, not `main.py`, but copy-pasting it to `worker.py` for the Celery worker is a copy bug waiting to happen. Second, the staging environment needs `DEBUG` and prod needs `INFO`; you cannot toggle this without an `if os.environ["ENV"] == "staging":` branch in the middle of the setup. Third, the team has just decided to add a Sentry handler for `ERROR` and above — a 4-line addition that has to be reviewed as a Python edit, not a config edit. Fourth, the `RotatingFileHandler` config (10 MB max, 5 backups) is now a magic number in source, not a value in YAML that ops can adjust.

`dictConfig` solves all four. One YAML file, loaded with `yaml.safe_load`, passed to `dictConfig`, in one line of Python.

## The Code

```python
# boardly/logging_config.py
"""Declarative logging configuration via logging.config.dictConfig."""
from __future__ import annotations

import logging.config
from pathlib import Path
from typing import Any

import yaml


# --- The boardly dictConfig schema, in Python (the YAML form is below) ---
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,                                   # mandatory; only 1 exists (3.2+)
    "disable_existing_loggers": False,              # DO NOT disable third-party loggers
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
            "style": "%",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": "boardly.log",
            "maxBytes": 10_485_760,                 # 10 MiB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "boardly": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def configure_logging(config_path: Path | None = None) -> None:
    """Apply dictConfig from a YAML file if given, else the in-code default."""
    if config_path is not None:
        with config_path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
    else:
        config = LOGGING_CONFIG
    logging.config.dictConfig(config)


# --- The YAML form (production pattern): ---
LOGGING_YAML = """\
version: 1
disable_existing_loggers: false
formatters:
  standard:
    format: '%(asctime)s %(levelname)-8s %(name)s :: %(message)s'
    datefmt: '%Y-%m-%dT%H:%M:%S'
    style: '%'
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stderr
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: standard
    filename: boardly.log
    maxBytes: 10485760
    backupCount: 5
    encoding: utf-8
loggers:
  boardly:
    level: DEBUG
    handlers: [console, file]
    propagate: false
root:
  level: WARNING
  handlers: [console]
"""


if __name__ == "__main__":
    # Demo: load the in-code config, run a few logs, then re-config at runtime.
    configure_logging()
    log = logging.getLogger("boardly.routers.projects")
    log.debug("debug-1: should reach file but NOT console (handler INFO)")
    log.info("info-1: should reach both console and file")

    # Runtime re-config (incremental): drop console handler to DEBUG
    logging.config.dictConfig({
        "version": 1,
        "incremental": True,
        "handlers": {"console": {"level": "DEBUG"}},
    })
    log.debug("debug-2: should now reach console too")
    log.info("info-2: still both")
```

## Line-by-Line Deep Dive

### Lines 9–16: The schema top-level keys

```python
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {...},
    "handlers": {...},
    "loggers": {...},
    "root": {...},
}
```

`version: 1` is the *only* mandatory key, and the *only* legal value is `1`. It exists because the schema designers wanted a way to introduce a v2 in the future without breaking existing configs. As of Python 3.12, no v2 exists. If you omit `version`, `dictConfig` raises `ValueError: dictionary doesn't specify a version`. If you set `version: 2`, the same error: `ValueError: Unrecognised version`. The other six keys are optional with defaults.

`disable_existing_loggers` defaults to `True` (this is the documented, surprising default). When `True`, every `Logger` instance that existed *before* the `dictConfig` call — including loggers created by third-party libraries you have imported — gets its `disabled` attribute set to `True` and goes silent. This was the right default in 3.2 (when the call site controlled the import order); in 3.12 it is a footgun. **Always set `disable_existing_loggers: false`.** The lesson's "Common Mistakes" section shows what goes wrong.

**Why is `disable_existing_loggers: true` the default?** Because the schema was designed in 3.2 for a world where `dictConfig` was called *before* any library import had created loggers — typically as the first statement in `if __name__ == "__main__":`. In that world, "disable all existing" was empty-set, so the default was harmless. The world changed: libraries now create their loggers at *import time*, and `dictConfig` is called from `app.main:main` after every library is already imported. The 3.2 default became a footgun, but the schema cannot change it without breaking backwards compatibility. The fix is a one-line `disable_existing_loggers: false` in every config you ship.

`formatters`, `handlers`, `loggers`, `root` are covered in the next blocks. `incremental` (not shown in this block — it lives in the runtime re-config call below) is the runtime-reconfig flag.

### Lines 17–24: The `formatters` section

```python
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
            "style": "%",
        },
    },
```

The `formatters` section is a dict of name → formatter-spec. Each spec accepts three keys: `format` (the format string, `%(asctime)s`-style by default), `datefmt` (a `strftime`-style format for `%(asctime)s`; default is ISO-ish), `style` (`"%"` / `"{"` / `"$"` — passed straight to `logging.Formatter(fmt, datefmt, style=...)`). The name `"standard"` here is your own; you reference it from `handlers` entries by string. You can have as many formatters as you like; the YAML pattern usually has `standard`, `verbose`, `json` (Lesson 03).

**Why name formatters?** Because the YAML now says `"formatter": "standard"` instead of repeating the format string in every handler. The handler section is one line per handler; the formatter section is one block per formatter. The indirection makes the YAML diff-able: changing the format string changes one block, not N handler entries.

### Lines 25–43: The `handlers` section

```python
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": "boardly.log",
            "maxBytes": 10_485_760,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
```

The `handlers` section is a dict of name → handler-spec. Each spec's required key is `class` — the dotted path to a `Handler` subclass. `logging.StreamHandler` and `logging.FileHandler` live in the `logging` namespace; the rotating ones (`RotatingFileHandler`, `TimedRotatingFileHandler`) live in `logging.handlers`, so you write `logging.handlers.RotatingFileHandler`. `level` accepts the string `"INFO"` *or* the int `20`; the schema converts. `formatter` is a string name matching a key in `formatters`. Every other key in the spec is passed as a kwarg to the handler's `__init__` — so `filename`, `maxBytes`, `backupCount`, `encoding` are the documented kwargs of `RotatingFileHandler.__init__`.

**Why is the handler `class` a dotted string and not a class object?** Because the config is *serialisable* — you can save it as YAML or JSON, ship it to a different process, load it back, and call `dictConfig` on the result. A class object is not JSON-serialisable; a dotted string is. The `dictConfig` implementation does `import_module(class_path.rsplit(".", 1)[0])` and `getattr(module, ClassName)` at config time, so the class only needs to be importable when `dictConfig` is called. This is the same pattern `pickle` uses for class references.

`"stream": "ext://sys.stderr"` is the schema's `ext://` mechanism: it tells `dictConfig` to resolve the attribute `sys.stderr` by *importing* `sys` and reading `.stderr`. Without the `ext://` prefix, the value would be treated as a literal string. Use `ext://sys.stdout`, `ext://sys.stderr`, `ext://logging.handlers.WATCHED_FILE` etc. for any module-level attribute reference.

### Lines 44–50: The `loggers` section

```python
    "loggers": {
        "boardly": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
```

The `loggers` section is a dict of logger-name → spec. Each spec accepts `level` (string or int), `handlers` (list of handler-name strings, or omitted), `propagate` (bool). The name `"boardly"` here is the *logger name*, not a config name — it is the string you pass to `logging.getLogger("boardly")` in code. Because every descendant (`boardly.routers.projects`, `boardly.routers.users`, etc.) inherits the handler via propagation, you only configure the top-level `boardly` logger in the dict, and `propagate: false` stops records from also reaching the root logger's `console` handler (which would double-emit to stderr).

The `root` section has the same shape (`level`, `handlers`) — except you cannot set `propagate` on root (it has no parent). Everything you do not name in `loggers` falls through to `root`.

### Lines 69–79: The `configure_logging` function

```python
def configure_logging(config_path: Path | None = None) -> None:
    if config_path is not None:
        with config_path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
    else:
        config = LOGGING_CONFIG
    logging.config.dictConfig(config)
```

The production pattern. Default to an in-code config (so the package has a working default if ops does not pass a path). Allow an override via a YAML path (so ops can drop a `logging.prod.yaml` next to the deployment and never touch the source). `yaml.safe_load` is the standard loader — `safe_load` is the one you want; never `yaml.load` (it can construct arbitrary Python objects from the YAML). The `with` block ensures the file is closed even if `dictConfig` raises (e.g. bad class path).

### Lines 116–123: Incremental runtime re-config

```python
    logging.config.dictConfig({
        "version": 1,
        "incremental": True,
        "handlers": {"console": {"level": "DEBUG"}},
    })
    log.debug("debug-2: should now reach console too")
```

`incremental: true` is the runtime-reconfig flag. It changes the schema: with `incremental: true`, you may *only* specify `version`, `incremental`, `loggers`, `handlers`, `root` — and within each, you may only change `level` (and a few other attributes). You *cannot* add new handlers or formatters or change the class of an existing handler. This is intentional: incremental re-config is for "drop the console level to `DEBUG` for this one debug session" — not for "swap the file handler for a Sentry handler". For the latter, you call `dictConfig` again without `incremental` (which is fine — `dictConfig` is idempotent in shape).

**Why `incremental`?** Because the runtime re-config path is hot. A debug session might call it 10 times. `dictConfig` without `incremental` walks every logger in `manager.loggerDict` (potentially hundreds) and re-evaluates every handler/formatter; `incremental` skips the walk and just sets the level attributes. It is the difference between milliseconds and microseconds.

## Execution Trace

```bash
$ python boardly/logging_config.py
2026-10-23T06:37:13 INFO     boardly.routers.projects :: info-1: should reach both console and file
2026-10-23T06:37:13 DEBUG    boardly.routers.projects :: debug-2: should now reach console too
2026-10-23T06:37:13 INFO     boardly.routers.projects :: info-2: still both
```

The `debug-1` line did *not* print to the console — at the time of that call, the `console` handler was at `INFO`. After the incremental re-config dropped it to `DEBUG`, `debug-2` appeared. The file (`boardly.log`) received all four lines (DEBUG and INFO). The `log.debug(...)` short-circuit was on the *logger* level (`DEBUG`), so all four records were created; only the *handler* level determined what reached stderr.

## Common Mistakes

### Mistake 1: `disable_existing_loggers` defaults to `True`

```python
import logging, logging.config
import requests  # this creates a "urllib3" logger on import
logging.config.dictConfig({
    "version": 1,
    # no disable_existing_loggers key -> defaults to True
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"]},
})
logging.getLogger("urllib3").warning("after dictConfig")  # SILENT
```

**Symptom:** After your `dictConfig` call, all loggers created by third-party libraries (everything imported before your `dictConfig` call — `urllib3`, `requests`, `asyncio`, `sqlalchemy`, etc.) go silent.

**Why:** The default `disable_existing_loggers: True` sets the `.disabled` attribute to `True` on every `Logger` instance in `manager.loggerDict` that is *not named* in the `loggers` section of your config. This was the documented behaviour in 3.2 and has been kept for backwards compatibility. The libraries you import at module load time create their loggers *before* your `dictConfig` call, so they get disabled.

**Fix:** Set `disable_existing_loggers: false` in every config you ship. The only time you want `True` is if you are deliberately silencing all third-party loggers — and even then, an explicit `loggers: {urllib3: {level: WARNING}}` block is clearer.

### Mistake 2: Wrong `class` path

```python
"handlers": {
    "file": {"class": "RotatingFileHandler", ...},  # WRONG
    "file2": {"class": "logging.RotatingFileHandler", ...},  # ALSO WRONG
}
```

**Symptom:** `ValueError: Unable to configure handler 'file'` on `dictConfig` call.

**Why:** The `class` value must be a fully-qualified dotted path to a `Handler` subclass that `dictConfig` can import. `RotatingFileHandler` is not in the `logging` namespace (it is in `logging.handlers`). `logging.RotatingFileHandler` does not exist. The correct path is `logging.handlers.RotatingFileHandler`.

**Fix:** Use the full path. The rule of thumb: if `from logging.handlers import X` works in Python, the dictConfig path is `logging.handlers.X`. If `from logging import X` works, the path is `logging.X`.

### Mistake 3: `incremental: true` with new handlers

```python
logging.config.dictConfig({
    "version": 1,
    "incremental": True,
    "handlers": {"sentry": {"class": "sentry_sdk.integrations.logging.SentryHandler"}},
})
```

**Symptom:** Nothing happens. No new handler is added. No error is raised.

**Why:** The `incremental: true` schema *ignores* any handler-spec key it does not recognise — and `class` is one of them in incremental mode. You can only change `level` (and a couple of other attributes documented in the schema) on existing handlers. New handlers require a non-incremental call.

**Fix:** For a one-off new handler at runtime, call `dictConfig` again without `incremental`. The full re-config is what you want — `dictConfig` is idempotent in shape (existing loggers are re-wired to the new config).

## Engineering Trade-Offs

**Decision:** YAML file in `boardly/etc/` loaded by `configure_logging(config_path=Path("..."))`.

**Both sides:** The alternative is the in-code dict (as the demo shows). It wins on: no file I/O at startup, simpler packaging (no `MANIFEST.in` entry for the YAML), no path-resolution pain in a frozen binary. It loses on: ops cannot edit levels without a code release; per-environment configs require `if env == "staging":` branches in Python.

**Commitment:** The `boardly` project ships an in-code default (`LOGGING_CONFIG`) for the single-process demo and an optional YAML path override for production. The pattern is `configure_logging(Path(os.environ.get("BOARDLY_LOGGING_CONFIG", "boardly/etc/logging.yaml")))`. Ops can drop a custom YAML in production without a release; the in-code default is the fallback if the file is missing.

## Exercises

1. **Exercise 1 — Add a second formatter.** Add a `verbose` formatter with format `"%(asctime)s %(levelname)-8s %(name)s %(process)d %(thread)d :: %(message)s"`. Wire the `file` handler to `verbose`. Re-run and inspect `boardly.log` — each line should now include process and thread IDs. `Verify: tail -5 boardly.log`
2. **Exercise 2 — Disable a logger.** Add `"boardly.workers.celery": {"level": "WARNING"}` to the `loggers` section. Confirm that `DEBUG` and `INFO` calls from a `logging.getLogger("boardly.workers.celery")` logger do *not* appear in the console, while `WARNING` and above do. `Verify: python -c "import logging; from boardly.logging_config import configure_logging; configure_logging(); log = logging.getLogger('boardly.workers.celery'); log.info('hi'); log.warning('warning hi')"`
3. **Exercise 3 — Trigger `disable_existing_loggers: true` and prove the bug.** Set `disable_existing_loggers: True`, import `requests` (or `urllib3`) before `configure_logging()`, and confirm that `logging.getLogger("urllib3").warning("hi")` is silent. Then set it back to `False` and confirm the warning prints. `Verify: python boardly/logging_config.py`
4. **Exercise 4 — Load from YAML.** Write `LOGGING_YAML` (the string in the demo) to a file `boardly/etc/logging.yaml`. Modify `configure_logging` to load it via `yaml.safe_load`. Confirm the runtime behaviour is identical to the in-code dict. `Verify: python -c "from boardly.logging_config import configure_logging; from pathlib import Path; configure_logging(Path('boardly/etc/logging.yaml')); import logging; logging.getLogger('boardly').info('from yaml')"`
5. **Exercise 5 — Add a Sentry-style error handler.** Add a `errors` handler with `class: logging.StreamHandler`, `level: ERROR`, `formatter: standard`, and add it to the `boardly` logger alongside `console` and `file`. Confirm that `log.error("...")` is emitted twice on stderr (once via `console`, once via `errors`) and `log.info(...)` only once. This is double-emit on purpose — it shows you why `propagate: false` is rarely the whole story; you also have to be careful not to attach the same stream twice. `Verify: python boardly/logging_config.py`

## Verification

```bash
$ python boardly/logging_config.py
2026-10-23T06:37:13 INFO     boardly.routers.projects :: info-1: should reach both console and file
2026-10-23T06:37:13 DEBUG    boardly.routers.projects :: debug-2: should now reach console too
2026-10-23T06:37:13 INFO     boardly.routers.projects :: info-2: still both
```

The exact timestamp will differ. The structure (ISO date, level, name, `::`, message) is the contract — set by the `standard` formatter in `LOGGING_CONFIG["formatters"]`.

## Previously Learned Here

- [[23-logging/01-Logger-Handler-Formatter]] — the `Logger`/`Handler`/`Formatter` hierarchy that `dictConfig` wires for you declaratively.
- [[06-dataclasses/01-dataclass-Basics]] — the frozen dataclass pattern used in the `boardly` models.

## What's Next

[[23-logging/03-structured-logging]] — every example so far has produced *prose* logs: `"project created: id=... name=..."` is a string meant for a human reading a terminal. Production observability runs on *structured* logs: JSON records with `request_id`, `user_id`, `trace_id` fields that an aggregator (Loki, Elasticsearch, Datadog) can index, filter, and join. The next lesson walks the `extra={...}` pattern, the custom JSON `Formatter` that emits `{"ts": ..., "level": ..., "msg": ..., **extra}`, the `structlog` library comparison, and the "log events not prose" rule that every senior engineer enforces in code review.

- The `extra={"request_id": ..., "user_id": ...}` kwarg and what it actually attaches to a `LogRecord`.
- The custom `Formatter` that emits JSON — including the bug in `json.dumps(record.msg)` that catches everyone.
- The `structlog` comparison — why teams that have used it do not go back.

## Sources

- **`logging.config` — Logging configuration** — https://docs.python.org/3/library/logging.config.html — accessed 2026-10-23 — the canonical reference for `dictConfig`, the schema, `incremental`, `disable_existing_loggers`, and the `ext://` mechanism.
- **`logging.config.configuration` schema (object dict)** — https://docs.python.org/3/library/logging.config.html#dictionary-schema-details — accessed 2026-10-23 — the full schema dictionary documentation.
- **`logging.handlers` — Logging handlers** — https://docs.python.org/3/library/logging.handlers.html — accessed 2026-10-23 — the `RotatingFileHandler` / `TimedRotatingFileHandler` / `QueueHandler` constructor kwargs.

## What We Learned

- You can now apply `logging.config.dictConfig(config)` to a dict, name every schema top-level key (`version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`), and articulate the mandatory-only-`1` rule for `version`.
- You can now construct the `formatters` section (`format`, `datefmt`, `style`) and the `handlers` section (`class`, `level`, `formatter`, plus handler-specific kwargs), including the `ext://sys.stderr` mechanism for module attributes.
- You can now wire the `loggers` section (`level`, `handlers`, `propagate`) and the `root` section, and articulate why `disable_existing_loggers: false` is mandatory in any code that imports third-party libraries.
- You can now use `incremental: true` for runtime re-config of levels (no new handlers or formatters), and articulate why the constraint is intentional.
- You can now load a YAML config file with `yaml.safe_load` and pass it to `dictConfig`, the production pattern.
- You can now articulate why `dictConfig` beats imperative `addHandler` setup: declarative, serialisable, diff-able, environment-overridable, single-line call.
