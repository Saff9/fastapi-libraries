---
title: "Lesson 03: Structured Logging"
aliases:
 - structured logging
 - JSON logging
 - logging extra kwarg
 - structlog
 - log events not prose
tags:
 - logging
 - structured-logging
 - json
 - structlog
 - canonical
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[23-logging/01-Logger-Handler-Formatter]]"
 - "[[23-logging/02-dictConfig]]"
 - "[[03-contextlib/05-contextvars]]"
related_lessons:
 - "[[23-logging/02-dictConfig]]"
 - "[[23-logging/04-Uvicorn-logging-integration]]"
 - "[[03-contextlib/05-contextvars]]"
first_taught_in: "23-logging/03-structured-logging"
---

# Lesson 03: Structured Logging

*JSON records with `request_id` / `user_id` / `trace_id` fields for log aggregators (Loki, Elasticsearch, Datadog) — the `extra={...}` kwarg, a custom JSON `Formatter`, and the "log events not prose" rule that every senior engineer enforces in code review.*

**You're at the very beginning of Section 23's third lesson.**

Every example so far has produced *prose* logs: `"project created: id=... name=..."` is a string meant for a human reading a terminal. That breaks the moment you ship. The aggregator in front of you — Loki, Elasticsearch, Datadog, Sentry, CloudWatch — does not parse prose. It indexes *fields*. A grep-able `request_id` joins the log line for an incoming request with the log line for the DB call it triggered two seconds later. A `user_id` field lets you answer "what did user 42 do in the last hour?" in one query. Prose logs cannot answer that question without a regex on free-text. Structured logs — JSON records with stable field names — answer it in milliseconds. By the end of this lesson you will know the `extra={...}` kwarg, the custom `Formatter` that emits JSON, the bug in `json.dumps(record.msg)` that catches everyone, and the `structlog` library comparison. Take your time. Type every example. **This is how you learn.**

#logging #structured-logging #json #structlog #canonical

## Learning Objectives

By the end of this lesson you will be able to:

1. **Use** the `extra={...}` kwarg on every `Logger` method to attach structured fields to a `LogRecord` — and articulate what happens to those fields at format time.
2. **Subclass** `logging.Formatter` to emit one JSON object per record (the `JSONFormatter` pattern), including the `_RESERVED` set that excludes standard `LogRecord` attributes from the user-extra bucket.
3. **Wire** the custom formatter via `dictConfig` using the `"()": "module.Class"` callable-spec — the schema's way of saying "instantiate this class with no args".
4. **Avoid** the `json.dumps(record.msg)` bug (it captures neither the user fields nor the interpolated message — it captures the *template* string).
5. **Articulate** the "log events not prose" rule: the message is a stable event name (e.g. `"project_create_failed"`); the context lives in `extra`.
6. **Compare** `structlog` to the stdlib-only approach — its benefits (context binding, processor chain, console-renderer for dev) and why teams that adopt it do not go back.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `Logger`/`Handler`/`Formatter` hierarchy, the `Formatter` subclass contract (`format(record) -> str`). See [[23-logging/01-Logger-Handler-Formatter]].
- **Lesson 02** — the `dictConfig` schema, especially the `formatters` section's `"()": "module.Class"` callable-spec. See [[23-logging/02-dictConfig]].
- **`ContextVar`** — the per-request primitive that holds the `request_id` / `user_id` you attach to every log line in a FastAPI middleware. See [[03-contextlib/05-contextvars]].
- **About 40–55 minutes of focused time.**

**The most common gap: free-text log messages with `f-strings`.**

Students reach for `log.info(f"project {name} created for user {user_id}")` because it is the first thing tutorials show. It is also the single biggest footgun in production observability. The aggregator cannot index the user ID out of that string. The grep for "user 42" matches every line where the literal `42` appears. The error-tracking tool groups by message *template* — but every f-string produces a different template, so each occurrence is its own group. The fix is the rule this lesson is built around: **log events, not prose**. The message is a stable event name (`"project_created"`); the context (`name`, `user_id`, `request_id`) is in `extra`, surfaced as JSON fields the aggregator can index.

## The Problem

You ship `boardly/routers/projects.py` with prose logging:

```python
log = logging.getLogger("boardly.routers.projects")
log.info(f"project {name} created for user {user_id} (request {request_id})")
```

A customer reports a 500 on `POST /projects`. You have 12 million log lines in Loki for the last hour. To find this request, you run `grep "request req-abc-123"` — but Loki does not grep, it queries fields. You fall back to a regex match, which scans all 12 million lines and returns 4 results. One of those is the matching line. The other 3 are unrelated requests where the string `req-abc-123` happened to appear in someone else's prose. You cannot filter by `user_id` because the user ID is buried in free text. The 500 takes 90 minutes to diagnose.

The structured alternative:

```python
log.info("project_created",
         extra={"request_id": request_id, "user_id": user_id, "name": name})
```

Loki indexes `request_id="req-abc-123"` directly. The query returns 1 result in 12 ms. The `user_id` field lets you pivot to "all requests for user 42 in the last hour" with one click. The diagnosis takes 30 seconds.

The `logging` module supports this natively — `extra={...}` was added in Python 2.5 — but the default `Formatter` does not emit JSON. You need a one-class subclass to turn the `LogRecord` into a JSON object. That subclass is 12 lines. This lesson walks it.

## The Code

```python
# boardly/structured_logging.py
"""Structured logging: JSON records with request_id / user_id fields."""
from __future__ import annotations

import json
import logging
import logging.config
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record.

    The contract: `format(record) -> str` returns the rendered string.
    We build a dict, JSON-encode it, return the string.
    """

    # Every standard attribute on a LogRecord (CPython 3.12 logging/__init__.py).
    # Excludes taskName (3.12 added) — keep the list current with CPython.
    _RESERVED = frozenset({
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),      # interpolated; not record.msg (template)
        }
        # Pull every user-supplied extra field off the record's __dict__.
        for key, value in record.__dict__.items():
            if not key.startswith("_") and key not in self._RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # The "()" key tells dictConfig: instantiate this class (callable spec).
        "json": {"()": "__main__.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
        },
    },
    "loggers": {
        "boardly": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}


def create_project(name: str, owner_id: UUID, request_id: str, user_id: int) -> None:
    log = logging.getLogger("boardly.routers.projects")
    # The message is a STABLE EVENT NAME. The context is in extra.
    log.info("project_created",
             extra={"request_id": request_id, "user_id": user_id,
                    "project_name": name, "owner_id": str(owner_id)})


if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    create_project(name="auth-rewrite", owner_id=uuid4(),
                   request_id="req-abc-123", user_id=42)

    # An error event: same stable-name discipline, more context in extra.
    log = logging.getLogger("boardly.routers.projects")
    log.error("project_create_failed",
              extra={"request_id": "req-abc-123", "user_id": 42,
                     "reason": "owner_not_found",
                     "owner_id": "00000000-0000-0000-0000-000000000000"})
```

## Line-by-Line Deep Dive

### Lines 9–22: The `JSONFormatter` skeleton

```python
class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    _RESERVED = frozenset({
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        ...
```

`logging.Formatter` is the abstract base for record rendering. The contract is one method: `format(self, record: LogRecord) -> str`. The base class's `format` does `%`-style interpolation, exception formatting, and date formatting; we override it entirely because we want JSON, not `%`-style prose.

`_RESERVED` is the set of standard `LogRecord` attributes (per CPython 3.12's `logging/__init__.py` `LogRecord.__init__` and the level-emission logic). The reason for the set: `record.__dict__` contains *both* the standard attributes (e.g. `record.levelname`, `record.created`, `record.msg`) *and* the user-supplied `extra` keys (e.g. `record.request_id`, `record.user_id`) — they are merged into the same `__dict__` when you call `log.info(..., extra={...})`. To emit *only* the user fields, we filter `record.__dict__` to exclude every standard attribute. The list is current as of CPython 3.12 (which added `taskName`); if you ever see `taskName: null` in your JSON output, your `_RESERVED` set is out of date.

### Lines 23–29: The payload skeleton

```python
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
```

The payload always has four keys: `ts` (ISO-format UTC timestamp from `record.created`, which is a `time.time()` float at record creation), `level` (the string `"INFO"` / `"ERROR"` etc. — `record.levelname`), `logger` (the dotted name like `"boardly.routers.projects"` — `record.name`), and `msg` (the *interpolated* message).

The `record.getMessage()` call is the critical bit. `record.msg` is the *template* — the raw string you passed to `log.info(...)`, before `%`-style formatting with `record.args`. `record.getMessage()` returns the *interpolated* string — `record.msg % record.args` (or, if `record.args` is empty, just `record.msg`). The bug in `json.dumps(record.msg)` is that it captures the template, so `log.info("user %s logged in", user_id)` produces `{"msg": "user %s logged in"}` instead of `{"msg": "user 42 logged in"}`. Always use `record.getMessage()`.

### Lines 30–33: Pull the user-supplied extra fields

```python
        for key, value in record.__dict__.items():
            if not key.startswith("_") and key not in self._RESERVED:
                payload[key] = value
```

The loop walks every attribute on the `LogRecord` instance. The `not key.startswith("_")` guard excludes any internal/dunder attribute. The `key not in self._RESERVED` guard excludes the standard attributes. What is left is exactly the keys the user passed via `extra={...}` — `request_id`, `user_id`, `project_name`, `owner_id`, `reason`, etc. They are added to the payload as-is.

**Why this works:** `logging.Logger.info(msg, *args, extra=None, stack_info=False, **kwargs)` merges `extra` into the `LogRecord`'s `__dict__` at construction time (see CPython `Logger.makeRecord`). The formatter sees them as ordinary attributes. There is no separate `record.extra` field — they are flattened onto `__dict__`. The downside: if a user passes `extra={"name": ...}` and `name` is *also* a standard `LogRecord` attribute (yes, `record.name` is the logger name), `makeRecord` raises `KeyError: 'Attempt to overwrite "name" in LogRecord'`. The fix is to prefix user field names — `logger_name` is safer than `name` — or just accept the rare collision.

### Lines 34–36: Exception handling

```python
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)
```

`record.exc_info` is set when you call `log.exception(...)` or `log.error(..., exc_info=True)`. It is a `(type, value, traceback)` tuple. `self.formatException(record.exc_info)` is the inherited `logging.Formatter.formatException` method that returns the formatted traceback as a multi-line string. We add it under `exc` so the aggregator can index "this record had an exception" with a single field check.

`json.dumps(payload, default=str, ensure_ascii=False)` does the encoding. `default=str` is the fallback for any non-JSON-serialisable value — a `UUID`, a `datetime`, a `dataclass`, a custom class — they all get `str()`'d rather than raising. `ensure_ascii=False` lets UTF-8 through (the default `True` escapes non-ASCII to `\uXXXX` sequences, which makes the JSON unreadable for non-ASCII log content). For real production, you would also handle `stack_info` (similar to `exc_info` but for the call stack).

**Why `default=str` and not a custom JSON encoder class?** Because `default` is the documented hook for the "I do not know how to serialise this object" fallback. A custom `JSONEncoder` subclass overrides *known* types (e.g. `UUID`, `datetime`) with first-class serialisation; `default=str` is the catch-all for everything *else* (custom classes, third-party objects). In practice, the catch-all is what you want for a logging formatter — you do not want one record to break the whole pipeline because someone passed a `sqlalchemy.engine.Engine` object in `extra`. The trade-off: `str(obj)` may produce an ugly `'<sqlalchemy.engine.base.Engine object at 0x7f...>'` for unsupported objects. If that is a problem, write a `default` callable that handles the types you care about and falls back to `str()` for the rest.

### Lines 39–50: The `dictConfig` schema with the callable-spec

```python
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "__main__.JSONFormatter"},
    },
    ...
}
```

The `"()"` key is the `dictConfig` schema's callable-spec mechanism. The value is a dotted path to a callable (class or factory function) that `dictConfig` will import and invoke. The result must be a `Formatter` instance. Any *other* key in the same formatter-spec dict is passed as a kwarg to the callable — so `{"()": "mymod.MyFormatter", "fmt": "..."}` would call `mymod.MyFormatter(fmt="...")`. Here we use no kwargs because `JSONFormatter` takes none.

This is how you wire any custom `Formatter` (including third-party ones like `pythonjsonlogger.json.JsonFormatter`) into a `dictConfig` YAML. In the YAML form (which the production config uses), the line is `json: { (): "boardly.structured_logging.JSONFormatter" }`.

### Lines 53–58: The event-name discipline

```python
def create_project(name: str, owner_id: UUID, request_id: str, user_id: int) -> None:
    log = logging.getLogger("boardly.routers.projects")
    log.info("project_created",
             extra={"request_id": request_id, "user_id": user_id,
                    "project_name": name, "owner_id": str(owner_id)})
```

The "log events not prose" rule, in code. The message is `"project_created"` — a stable, snake_case event name. Every occurrence of this event, from every request, every environment, every day, has the *same* message string. The aggregator can group by `msg` field and produce an accurate count: "1,234 `project_created` events in the last hour, 3 of them with `level=ERROR`". That grouping is impossible with prose because every f-string produces a different message string.

The `extra` dict carries the context. `request_id` joins this event to every other event in the same HTTP request. `user_id` lets the aggregator answer "what did user 42 do?" with one query. `project_name` and `owner_id` are the per-event specifics. Notice the snake_case discipline — `project_name`, not `projectName` — because the aggregator's query language (LogQL, Lucene, Datadog Query Language) is case-sensitive and snake_case is the convention for fields everywhere else in observability.

**Why `extra` and not `json.dumps({...})` as the message?** Because `extra` is the schema-declared mechanism, the `LogRecord` carries the fields as attributes (not as a string), the formatter has full control over how they appear (JSON here, plain key=value in console mode in dev), and downstream code that wants to inspect the record programmatically (e.g. a `QueueListener` that batches to a remote endpoint) gets native attributes, not a deserialise step. Using `json.dumps({...})` as the message string is the half-measure: the message is structured but the aggregator has to parse it back out, and the per-event attributes are not first-class on the record.

## Execution Trace

```bash
$ python boardly/structured_logging.py
{"ts": "2026-10-23T06:40:09.215055+00:00", "level": "INFO", "logger": "boardly.routers.projects", "msg": "project_created", "request_id": "req-abc-123", "user_id": 42, "project_name": "auth-rewrite", "owner_id": "35f280ed-46de-46a1-bc26-fc06b39b1dbb"}
{"ts": "2026-10-23T06:40:09.215172+00:00", "level": "ERROR", "logger": "boardly.routers.projects", "msg": "project_create_failed", "request_id": "req-abc-123", "user_id": 42, "reason": "owner_not_found", "owner_id": "00000000-0000-0000-0000-000000000000"}
```

One JSON object per line. Each line is `json.loads`-able. The `request_id` field lets you join the INFO `project_created` line with the ERROR `project_create_failed` line for the same request. The `user_id` field lets the aggregator pivot to "all events for user 42" with one query.

## Common Mistakes

### Mistake 1: `json.dumps(record.msg)` is wrong

```python
class BuggyJSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"msg": record.msg})  # WRONG
```

**Symptom:** Every log line has `{"msg": "project_created"}` — the user fields (`request_id`, `user_id`) are *missing*. Worse, `log.info("user %s logged in", user_id)` produces `{"msg": "user %s logged in"}` — the template, not the interpolated string.

**Why:** `record.msg` is the raw template string before `%`-style interpolation with `record.args`. The user fields passed via `extra={...}` are stored on the `LogRecord.__dict__`, *not* inside `record.msg`. So `json.dumps(record.msg)` captures neither the args nor the extra fields.

**Fix:** Use the full `JSONFormatter` pattern shown above — call `record.getMessage()` for the interpolated message, walk `record.__dict__` for the extra fields.

### Mistake 2: Overwriting a standard `LogRecord` attribute via `extra`

```python
log.info("project created", extra={"name": "auth-rewrite"})  # WRONG
```

**Symptom:** `KeyError: "Attempt to overwrite 'name' in LogRecord"` at the call site.

**Why:** `record.name` is the logger's dotted name (`"boardly.routers.projects"`). The `makeRecord` call in CPython's `Logger._log` explicitly raises `KeyError` if a user-supplied `extra` key collides with a `LogRecord` attribute. The collision set is the `_RESERVED` set in the `JSONFormatter` above — `name`, `msg`, `args`, `levelname`, `created`, etc. — about 20 names.

**Fix:** Prefix user field names with a domain qualifier. `extra={"project_name": "..."}` is safe; `extra={"name": "..."}` is not. The convention in `boardly` is `entity_field` (e.g. `project_name`, `owner_id`, `ticket_id`).

### Mistake 3: F-string log messages

```python
log.info(f"project {name} created for user {user_id}")  # WRONG
```

**Symptom:** Every log line has a different message string. The aggregator groups each occurrence as its own group. Searches for `user 42` match unrelated lines where the literal `42` appears. The `%`-style short-circuit (where `log.debug` skips the format if the level is too low) is broken — the f-string is evaluated *before* `debug` is called, so the cost is paid even if the record is dropped.

**Why:** `log.info(msg, *args)` was designed for lazy `%`-style formatting — `log.debug("user %s logged in", user_id)` only formats the string if the logger's effective level is `DEBUG` or lower. The f-string `f"user {user_id} logged in"` is evaluated *before* `debug` is called, defeating the short-circuit. Worse, the f-string produces a *new* message string every call, defeating the aggregator's group-by-message-template feature.

**Fix:** Use stable event names with `extra` context: `log.info("project_created", extra={"project_name": name, "user_id": user_id})`. For the rare case where a message *must* be dynamic, use `%`-style: `log.debug("user %s logged in", user_id)`.

## Engineering Trade-Offs

**Decision:** Stdlib-only `JSONFormatter` for the `boardly` project; `structlog` evaluated, not adopted (yet).

**Both sides:** `structlog` (the third-party library) is the popular choice for teams that have used it. It gives you: (a) context binding (`log = log.bind(request_id=rid, user_id=uid)` — every subsequent call from that logger carries those fields, no `extra={...}` repetition), (b) a processor chain (each record passes through a configurable list of processors — add-a-field, redact-a-secret, JSON-render), (c) a console renderer for dev that pretty-prints to ANSI-coloured prose while the prod renderer emits JSON. The downside: it is a dependency (one more package), it has its own configuration layer (which overlaps with `dictConfig`), and the stdlib-only `JSONFormatter` plus a `ContextVar`-bound `extra` covers 90% of what `structlog` gives you.

**Commitment:** `boardly` ships the stdlib-only `JSONFormatter`. The per-request context (`request_id`, `user_id`, `trace_id`) is held in `ContextVar`s (see [[03-contextlib/05-contextvars]]) and read by the `JSONFormatter` at format time — so every call site just writes `log.info("project_created", extra={"project_name": name})` and the `request_id` is added automatically. If the team grows past one service and needs cross-service correlation, the next step is `structlog` with its processor chain — but only after the stdlib pattern is exhausted.

## Exercises

1. **Exercise 1 — Add a `trace_id` field via `extra`.** Modify `create_project` to take a `trace_id: str` parameter and add it to the `extra` dict. Confirm the JSON output now has `"trace_id": "..."`. `Verify: python boardly/structured_logging.py | python3 -c "import json, sys; [print(json.loads(l).get('trace_id')) for l in sys.stdin if l.strip()]"`
2. **Exercise 2 — Demonstrate the `record.msg` vs `record.getMessage()` bug.** Add a `BuggyJSONFormatter` that uses `record.msg` (not `getMessage`). Configure `boardly` to use it. Log `log.info("user %s logged in", 42)` and observe the output `{"msg": "user %s logged in"}` — the template, not the interpolated string. `Verify: python -c "..."`
3. **Exercise 3 — Add a stack-trace field.** Wrap the `create_project` body in `try: ... except Exception: log.exception("project_create_failed", extra={...})` and confirm the JSON output now has an `"exc"` key with the formatted traceback. `Verify: python boardly/structured_logging.py`
4. **Exercise 4 — `ContextVar`-bound `request_id`.** Define `request_id_var: ContextVar[str] = ContextVar("request_id", default="")`. In the `JSONFormatter.format`, read `request_id_var.get()` and add it to the payload (only if non-empty). Now call sites do not need to pass `extra={"request_id": ...}` — every record carries it. `Verify: python boardly/structured_logging.py` (and confirm `request_id` is in every line)
5. **Exercise 5 — Try `structlog`.** `pip install structlog`. Replace `boardly/structured_logging.py` with the `structlog` equivalent: `structlog.configure(processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.add_log_level, structlog.processors.JSONRenderer()])`. Bind `request_id` once via `log = structlog.get_logger().bind(request_id=rid)` and confirm every subsequent `log.info("project_created", user_id=uid)` carries the `request_id` field automatically. Compare the call-site ergonomics to the stdlib `extra={...}` pattern. `Verify: python boardly/structured_structlog.py`

## Verification

```bash
$ python boardly/structured_logging.py
{"ts": "2026-10-23T06:40:09.215055+00:00", "level": "INFO", "logger": "boardly.routers.projects", "msg": "project_created", "request_id": "req-abc-123", "user_id": 42, "project_name": "auth-rewrite", "owner_id": "35f280ed-46de-46a1-bc26-fc06b39b1dbb"}
{"ts": "2026-10-23T06:40:09.215172+00:00", "level": "ERROR", "logger": "boardly.routers.projects", "msg": "project_create_failed", "request_id": "req-abc-123", "user_id": 42, "reason": "owner_not_found", "owner_id": "00000000-0000-0000-0000-000000000000"}
```

The exact `ts`, `owner_id` (UUID) will differ on your run. The contract: each line is a single JSON object, the `msg` field is a stable event name, every context field is a top-level JSON key, and `request_id` lets you join the two lines.

## Previously Learned Here

- [[23-logging/01-Logger-Handler-Formatter]] — the `Formatter` subclass contract (`format(record) -> str`) that `JSONFormatter` implements.
- [[23-logging/02-dictConfig]] — the `"()": "module.Class"` callable-spec that wires `JSONFormatter` into a `dictConfig`.
- [[03-contextlib/05-contextvars]] — `ContextVar` is the canonical mechanism for per-request context (`request_id`, `user_id`) that a `JSONFormatter` reads at format time.

## What's Next

[[23-logging/04-Uvicorn-logging-integration]] — every example so far has been pure stdlib: a `Python` script with a logger, a handler, a formatter. FastAPI runs under Uvicorn, and Uvicorn ships its *own* logging setup — three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) and a `LOGGING_CONFIG` dict that is loaded at server start. To interleave your `boardly` business logs with Uvicorn's access logs in the same console, same file, same JSON formatter, you need to know: (a) the `LOGGING_CONFIG` dict structure, (b) the `uvicorn.access` logger is the canonical hook for structured access logs, (c) the `log_config=` parameter to `uvicorn.run` and the `--log-config` CLI flag. The next lesson is THE FastAPI lesson of this section.

- Uvicorn's three loggers and the `LOGGING_CONFIG` dict.
- The `log_config=` parameter and `--log-config` CLI flag.
- The propagation rule that prevents double-emit when you add your own handler.

## Sources

- **`logging` — Logging facility for Python** — https://docs.python.org/3/library/logging.html — accessed 2026-10-23 — the `extra` kwarg on `Logger.info`/`debug`/`warning`/`error`, the `LogRecord` attribute list, and the `Formatter` subclass contract.
- **`logging.LogRecord` attributes** — https://docs.python.org/3/library/logging.html#logrecord-attributes — accessed 2026-10-23 — the canonical list of standard `LogRecord` attributes (the `_RESERVED` set in `JSONFormatter`).
- **`structlog` documentation** — https://www.structlog.org/en/stable/ — accessed 2026-10-23 — the third-party library comparison: context binding, processor chain, console renderer.
- **PEP 282 — A Logging System** — https://peps.python.org/pep-0282/ — accessed 2026-10-23 — the original PEP that introduced the `logging` module (Python 2.3), including `extra` and the `Logger.makeRecord` merge semantics that `JSONFormatter` relies on.

## What We Learned

- You can now use the `extra={...}` kwarg on `Logger.info` / `debug` / `warning` / `error` to attach structured fields to a `LogRecord` — and articulate that those fields are flattened onto `record.__dict__`, not stored in a separate `extra` slot.
- You can now subclass `logging.Formatter` to emit one JSON object per record, including the `_RESERVED` set that excludes standard `LogRecord` attributes from the user-extra bucket.
- You can now wire the custom formatter via `dictConfig` using the `"()": "module.Class"` callable-spec.
- You can now avoid the `json.dumps(record.msg)` bug — it captures the template, not the interpolated message, and misses the extra fields entirely.
- You can now articulate the "log events not prose" rule: the message is a stable event name; the context lives in `extra`.
- You can now compare `structlog` to the stdlib-only approach and articulate when each wins.
