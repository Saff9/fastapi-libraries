---
title: "logging — Section Map of Content"
aliases:
 - logging MOC
 - 23-logging MOC
tags:
 - logging
 - moc
status: complete
course_level: intermediate
---

# Section 23: `logging`

*The `Logger` / `Handler` / `Formatter` / `Filter` hierarchy, `dictConfig`, structured logging for log aggregators, and the Uvicorn integration that every FastAPI request log flows through.*

**You're at the very beginning of Section 23.**

The `logging` module is the part of the standard library that every Python program touches and almost no one reads. You write `import logging; log = logging.getLogger(__name__)` once at the top of a file and forget it. But the moment you ship a FastAPI app and try to interleave your business logs with Uvicorn's access logs, the four-class hierarchy underneath (`Logger` → `Handler` → `Formatter`, with `Filter` on the side), the `dictConfig` schema, the structured-logging formatter, and the Uvicorn `LOGGING_CONFIG` override all stop being optional knowledge. By the end of this section you will know the dot-namespaced logger tree, the `dictConfig` schema, the JSON formatter pattern, and the Uvicorn integration that lets one log stream serve both server and business events. Take your time. Type every example. **This is how you learn.**

#logging #moc

## Lessons in this section

| # | Lesson | What you learn | Tags |
|---|--------|----------------|------|
| 01 | [[23-logging/01-Logger-Handler-Formatter]] | `logging.getLogger("boardly.routers.projects")` (singleton per name, dot-namespaced parent/child tree), `Logger` / `Handler` / `Formatter` / `Filter` four-class hierarchy, `setLevel(DEBUG/INFO/WARNING/ERROR/CRITICAL)` two-level gating, `propagate=False` rule, the root-logger gotcha (`logging.warning()` mutates the root). | `canonical` |
| 02 | [[23-logging/02-dictConfig]] | `logging.config.dictConfig(config)` schema (`version: 1`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`), the `"()": "module.Class"` callable-spec, the `ext://sys.stderr` mechanism, the production YAML pattern, `incremental=True` runtime re-config. | `canonical` |
| 03 | [[23-logging/03-structured-logging]] | The `extra={...}` kwarg (attaches fields to `LogRecord.__dict__`), the custom `JSONFormatter` subclass, the `_RESERVED` set that excludes standard `LogRecord` attrs, the `json.dumps(record.msg)` bug, the "log events not prose" rule, the `structlog` library comparison. | `canonical` |
| 04 | [[23-logging/04-Uvicorn-logging-integration]] | **THE FastAPI lesson**: Uvicorn's `LOGGING_CONFIG` dict, three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`), overriding via `uvicorn.run(app, log_config=...)` or `--log-config config.json`, the interleaving pattern (shared handler + shared formatter on both `uvicorn.access` and `boardly`), the `propagate=False` double-emit trap. | `canonical` `fastapi-primitive` |

## Suggested reading order

1. [[23-logging/01-Logger-Handler-Formatter]] — the canonical lesson. Every other lesson assumes you have read this. The four-class hierarchy, the dot namespace, the two-level gating, and the root-logger gotcha are the foundation everything else stands on.
2. [[23-logging/02-dictConfig]] — the declarative config layer that replaces imperative `addHandler` setup. Read this second because it depends on Lesson 01's hierarchy for the `loggers` and `root` sections.
3. [[23-logging/03-structured-logging]] — the JSON formatter pattern. Read this third because it depends on Lesson 02's `"()"` callable-spec for wiring the custom formatter, and it introduces the "log events not prose" rule every other lesson's examples use.
4. [[23-logging/04-Uvicorn-logging-integration]] — THE FastAPI lesson. Read this last because it depends on the JSON formatter (Lesson 03) being available on `sys.path` for the `dictConfig` callable-spec, and on the propagation rules (Lesson 01) being internalised before you can reason about the double-emit trap.

## Concepts first-taught in this section

These concepts have their canonical lesson in `23-logging/`:

- **`logging.getLogger` / `Logger` / `Handler` / `Formatter` / `Filter`** → [[23-logging/01-Logger-Handler-Formatter]] — the canonical lesson for the four-class hierarchy, the dot-namespaced logger tree, and the root-logger gotcha.
- **`logging.config.dictConfig`** → [[23-logging/02-dictConfig]] — the canonical lesson for the `dictConfig` schema (`version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`) and the `"()"` callable-spec.
- **Structured logging (`extra={...}` kwarg, custom JSON `Formatter`)** → [[23-logging/03-structured-logging]] — the canonical lesson for the structured-logging pattern in stdlib (no third-party libraries required).
- **Uvicorn logging integration (`LOGGING_CONFIG`, `log_config=`, `--log-config`, `uvicorn.access` logger)** → [[23-logging/04-Uvicorn-logging-integration]] — the canonical lesson for interleaving app logs with Uvicorn's access logs in one JSON stream.

## The cross-cutting connection: `ContextVar` for per-request fields

Every production log line in a FastAPI app needs a `request_id` field so the aggregator can join the access-log line with the business-event line. The `request_id` is set once per HTTP request, in middleware, and read by the `JSONFormatter` at format time. The primitive that makes this work is `contextvars.ContextVar` — the request-scoped state primitive that lives in [[03-contextlib/05-contextvars]]. That lesson is the canonical reference for the `var.set(rid)` in middleware / `var.get()` in handler pattern; this section's Lesson 03 (Exercise 4) and Lesson 04 (Exercise 4) wire the `ContextVar` into the `JSONFormatter`.

**Read [[03-contextlib/05-contextvars]] before reading Lesson 04's Exercise 4.** The `ContextVar` mechanism is what makes per-request logging tractable — without it, you would have to pass `request_id` through every function in the call chain.

## What you will be able to do

After this section, you will be able to:

- Construct named loggers (`logging.getLogger("boardly.routers.projects")`) and explain the dot-namespaced parent/child tree, the singleton-per-name rule, and the `getEffectiveLevel()` cascade.
- Wire a `StreamHandler`, `FileHandler`, or `RotatingFileHandler` onto a `Logger`, and articulate the two-level gating (logger level creates records; handler level emits them).
- Format records with `Formatter(fmt, datefmt, style="%"/"{"/"$")` and choose the right style back-end.
- Filter by logger-name prefix with `logging.Filter("boardly.routers")`, including the dot-boundary rule.
- Avoid the root-logger gotcha — never calling `logging.warning()` / `logging.info()` in library code.
- Apply `logging.config.dictConfig(config)` to a dict, name every schema key, and articulate the `disable_existing_loggers: false` rule.
- Use `incremental: true` for runtime level changes; load YAML configs for production.
- Build a `JSONFormatter` subclass that emits one JSON object per record, including the `_RESERVED` set and the `record.getMessage()` rule.
- Articulate the "log events not prose" rule and apply it: stable event names in the message, context in `extra`.
- Override Uvicorn's `LOGGING_CONFIG` via `uvicorn.run(app, log_config=...)` or `--log-config config.json` to interleave access logs with business logs in one JSON stream.
- Avoid the double-emit trap by setting `propagate=False` on every named logger you wire a handler to.

## What's next

When you finish this section, the natural next stops are:

- [[03-contextlib/05-contextvars]] — if you have not yet read it, this is the canonical lesson for the `ContextVar` middleware pattern that powers per-request logging. Read this *before* Lesson 04's Exercise 4.
- [[01-typing/00-typing-MOC]] — the typing section. The `JSONFormatter` in this section uses `dict[str, Any]` and `frozenset` types throughout; the typing section is where those annotations are first taught canonically.
- [[25-Reference-Library/Engineering-Decision-Log]] — the decision to ship the stdlib-only `JSONFormatter` rather than `structlog` is documented here. Senior engineers consult this log before reaching for a third-party library.

## Sources

- **`logging` — Logging facility for Python** — https://docs.python.org/3/library/logging.html — accessed 2026-10-23 — the canonical reference for `Logger`, `Handler`, `Formatter`, `Filter`, the level constants, and the `LogRecord` attribute list.
- **`logging.config` — Logging configuration** — https://docs.python.org/3/library/logging.config.html — accessed 2026-10-23 — the `dictConfig` schema (`version`, `formatters`, `handlers`, `loggers`, `root`, `incremental`, `disable_existing_loggers`), the `"()"` callable-spec, the `ext://` mechanism.
- **`logging.handlers` — Logging handlers** — https://docs.python.org/3/library/logging.handlers.html — accessed 2026-10-23 — `StreamHandler`, `FileHandler`, `RotatingFileHandler`, `TimedRotatingFileHandler`, `QueueHandler` (3.7+), `QueueListener`.
- **`logging.LogRecord` attributes** — https://docs.python.org/3/library/logging.html#logrecord-attributes — accessed 2026-10-23 — the full list of `%(name)s`-style format fields, used by both the standard `Formatter` and the `_RESERVED` set in the `JSONFormatter`.
- **Uvicorn — Logging** — https://www.uvicorn.org/settings/#logging — accessed 2026-10-23 — the canonical reference for Uvicorn's `log_config`, `log_level`, and `access_log` parameters, and the `--log-config` CLI flag.
- **Uvicorn source — `uvicorn/config.py` (LOGGING_CONFIG)** — https://github.com/encode/uvicorn/blob/0.44.0/uvicorn/config.py — accessed 2026-10-23 — the actual `LOGGING_CONFIG` dict (verified against the installed Uvicorn 0.44.0 in the sandbox).
- **`structlog` documentation** — https://www.structlog.org/en/stable/ — accessed 2026-10-23 — the third-party library comparison in Lesson 03: context binding, processor chain, console renderer.
