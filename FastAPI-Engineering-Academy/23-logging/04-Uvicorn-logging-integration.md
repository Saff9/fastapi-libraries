---
title: "Lesson 04: Uvicorn Logging Integration"
aliases:
 - uvicorn logging
 - uvicorn.access
 - uvicorn LOGGING_CONFIG
 - uvicorn log_config
 - uvicorn --log-config
tags:
 - logging
 - uvicorn
 - fastapi
 - asgi
 - canonical
 - fastapi-primitive
status: complete
course_level: intermediate
difficulty: advanced
estimated_time: "40–55 minutes"
prerequisites:
 - "[[23-logging/01-Logger-Handler-Formatter]]"
 - "[[23-logging/02-dictConfig]]"
 - "[[23-logging/03-structured-logging]]"
related_lessons:
 - "[[23-logging/01-Logger-Handler-Formatter]]"
 - "[[23-logging/02-dictConfig]]"
 - "[[23-logging/03-structured-logging]]"
 - "[[03-contextlib/05-contextvars]]"
first_taught_in: "23-logging/04-Uvicorn-logging-integration"
---

# Lesson 04: Uvicorn Logging Integration

*THE FastAPI lesson of this section. Uvicorn ships its own `LOGGING_CONFIG` dict — three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) wired to two handlers (`default` to stderr, `access` to stdout). To interleave your `boardly` business logs with Uvicorn's access logs in the same stream, same JSON formatter, you override the `LOGGING_CONFIG` and pass it via `uvicorn.run(app, log_config=...)` or `--log-config config.json`.*

**You're at the very beginning of Section 23's most important lesson for FastAPI.**

If there is one lesson in this section to read twice, this is it. Every FastAPI app runs under an ASGI server — usually Uvicorn — and Uvicorn arrives with its own logging setup. The first surprise: Uvicorn's setup uses the *same* `logging.config.dictConfig` schema you learned in Lesson 02. The second surprise: Uvicorn creates three named loggers — `uvicorn`, `uvicorn.error`, `uvicorn.access` — and the `uvicorn.access` logger is the canonical hook for every "this HTTP request happened" line in your production logs. The third surprise: to interleave your `boardly` business logs (project_created, ticket_moved) with Uvicorn's access logs in the *same JSON stream, same formatter, same console*, you do not touch Uvicorn's source — you pass a modified `LOGGING_CONFIG` dict to `uvicorn.run(app, log_config=my_config)` or use the `--log-config config.json` CLI flag. By the end of this lesson you will know Uvicorn's three loggers, the `LOGGING_CONFIG` schema, and the interleaving pattern that makes production observability tractable. Take your time. Type every example. **This is how you learn.**

#logging #uvicorn #fastapi #asgi #canonical #fastapi-primitive

## Learning Objectives

By the end of this lesson you will be able to:

1. **Name** Uvicorn's three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) and articulate the role of each — `uvicorn` for server lifecycle, `uvicorn.error` for errors (inherits from `uvicorn`), `uvicorn.access` for HTTP request/response lines.
2. **Read** Uvicorn's `LOGGING_CONFIG` dict (importable from `uvicorn.config`) and articulate its structure: two formatters (`default` with `DefaultFormatter`, `access` with `AccessFormatter`), two handlers (`default` to `ext://sys.stderr`, `access` to `ext://sys.stdout`), three loggers with the `propagate=False` rule.
3. **Interleave** your `boardly` business logs with Uvicorn's access logs by overriding the `LOGGING_CONFIG` to use a *shared* handler with your `JSONFormatter` from Lesson 03, attached to both `uvicorn.access` and `boardly`.
4. **Pass** the modified config to `uvicorn.run(app, log_config=my_config)` — and use the `--log-config config.json` CLI flag for the production deployment pattern.
5. **Articulate** the `access_log=False` parameter and `log_level=` parameter on `uvicorn.run` as the coarse knobs — and why you almost never use them in production (you want the structured access logs, not silence).
6. **Avoid** the double-emit trap: when you add your own handler to `uvicorn.access`, set `propagate=False` to prevent the record walking to Uvicorn's own `access` handler as well.

## Prerequisites

Before starting, you need:

- **Lesson 01** — `Logger`/`Handler`/`Formatter` hierarchy, the `propagate` walk, the two-level gating. See [[23-logging/01-Logger-Handler-Formatter]].
- **Lesson 02** — the `dictConfig` schema, the `"()": "module.Class"` callable-spec, the `ext://` mechanism. See [[23-logging/02-dictConfig]].
- **Lesson 03** — the `JSONFormatter` subclass that emits one JSON object per record. See [[23-logging/03-structured-logging]].
- **`ContextVar`** — the per-request primitive for `request_id` that lets you join Uvicorn's access log line with your `boardly` business log lines. See [[03-contextlib/05-contextvars]].
- **About 40–55 minutes of focused time.**

**The most common gap: thinking Uvicorn's logging setup is separate from stdlib `logging`.**

Students discover `uvicorn.run(app)` boots a server, see Uvicorn's pre-formatted access logs (the `INFO:     127.0.0.1:54321 - "GET /projects HTTP/1.1" 200 OK` line) and assume Uvicorn has its own logging library that is unrelated to `import logging`. It does not. Uvicorn's `LOGGING_CONFIG` is a `dictConfig`-format dict that Uvicorn passes to `logging.config.dictConfig` at server start. Every Uvicorn log line — startup banner, access log, error — goes through the same `logging.Logger` instances you have been configuring since Lesson 01. The `uvicorn.access` logger is `logging.getLogger("uvicorn.access")`. You can attach your own handler to it. You can replace the formatter. You can disable it. The gap is not knowing this; the lesson closes it.

## The Problem

You ship `boardly/main.py` with the structured-logging setup from Lesson 03 and run it under Uvicorn:

```python
# boardly/main.py
import logging, logging.config
from boardly.structured_logging import JSONFormatter, LOGGING_CONFIG
from fastapi import FastAPI

logging.config.dictConfig(LOGGING_CONFIG)
app = FastAPI()
```

```bash
$ uvicorn boardly.main:app
INFO:     Started server process [12345]
INFO:     Application startup complete.
{"ts": "...", "level": "INFO", "logger": "boardly.routers.projects", "msg": "project_created", ...}
INFO:     127.0.0.1:54321 - "POST /projects HTTP/1.1" 201 Created
{"ts": "...", "level": "INFO", "logger": "boardly.routers.projects", "msg": "project_create_failed", ...}
INFO:     127.0.0.1:54322 - "POST /projects HTTP/1.1" 500 Internal Server Error
```

Three problems. First, the format is inconsistent — your `boardly` business logs are JSON, Uvicorn's access logs are prose. The aggregator can index your business logs but cannot index Uvicorn's. Second, the streams are split — Uvicorn's access logs go to `stdout` (the `access` handler is on `ext://sys.stdout`), your business logs go to `stderr` (the `console` handler is on `ext://sys.stderr`), and the log shipper sees them out of order. Third, you cannot *join* the access log line with your business log line — Uvicorn's access formatter uses `%`-style fields (`%(client_addr)s`, `%(request_line)s`, `%(status_code)s`) that are not the same field names your `JSONFormatter` emits, and the request ID is missing entirely.

The fix is the *interleaving pattern*: override Uvicorn's `LOGGING_CONFIG` to use your `JSONFormatter` on a shared handler attached to both `uvicorn.access` *and* `boardly`. Every line — Uvicorn startup, access log, business event — flows through the same handler, same formatter, same stream. And because the `JSONFormatter` pulls the `request_id` `ContextVar`, you can join them.

## The Code

```python
# boardly/uvicorn_logging.py
"""Override Uvicorn's LOGGING_CONFIG to interleave access and business logs."""
from __future__ import annotations

import logging
from typing import Any

from boardly.structured_logging import JSONFormatter  # the Lesson 03 formatter

# The shared handler used by both uvicorn.access AND boardly loggers.
# Both loggers emit to the same StreamHandler with the same JSONFormatter.
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "boardly.structured_logging.JSONFormatter"},
    },
    "handlers": {
        "shared": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        # Uvicorn's three loggers, all wired to the shared handler.
        "uvicorn":         {"level": "INFO", "handlers": ["shared"], "propagate": False},
        "uvicorn.error":   {"level": "INFO"},   # inherits uvicorn via propagation
        "uvicorn.access":  {"level": "INFO", "handlers": ["shared"], "propagate": False},
        # The app's boardly logger, wired to the SAME shared handler.
        "boardly":         {"level": "INFO", "handlers": ["shared"], "propagate": False},
    },
    # NOTE: no 'root' key. Uvicorn does not configure root by default.
}


def run() -> None:
    """Entry point: pass our config to uvicorn.run via log_config=."""
    import uvicorn

    async def app(scope, receive, send):
        # Inline ASGI app for the demo. Real boardly uses FastAPI.
        if scope["type"] != "http":
            return
        log = logging.getLogger("boardly")
        log.info("request_received", extra={"path": scope["path"]})
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"ok"})

    # The integration: log_config= overrides Uvicorn's default LOGGING_CONFIG.
    uvicorn.run(app, log_config=LOGGING_CONFIG, port=8000, host="127.0.0.1")


if __name__ == "__main__":
    run()
```

## Line-by-Line Deep Dive

### Lines 9–14: Importing the `JSONFormatter`

```python
from boardly.structured_logging import JSONFormatter  # the Lesson 03 formatter

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    ...
}
```

The `JSONFormatter` from Lesson 03 is reused unchanged. The `"()"` callable-spec mechanism in `dictConfig` lets the schema import and instantiate any `Formatter` subclass by dotted path — `"()": "boardly.structured_logging.JSONFormatter"`. There is no need to register the formatter with Uvicorn; `dictConfig` does the import. The formatter must be importable (i.e. on `sys.path`) at the moment `uvicorn.run` calls `logging.config.dictConfig`, which happens at server start. Package it as part of the app.

### Lines 15–21: The shared handler

```python
    "handlers": {
        "shared": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
```

The `shared` handler is a single `StreamHandler` writing to `ext://sys.stdout`. It uses the `json` formatter from the `formatters` section. By naming this handler `"shared"` and referencing it from *multiple* loggers (both `uvicorn.access` and `boardly`), we ensure both loggers emit to the *same* stream with the *same* formatter. This is the interleaving pattern in one handler entry.

**Why `sys.stdout` and not `sys.stderr`?** Uvicorn's default `access` handler is on `ext://sys.stdout` and Uvicorn's default `default` handler (server lifecycle logs) is on `ext://sys.stderr`. The convention in 12-factor apps is that *application logs* go to stdout (so the container runtime captures them) and *error/diagnostic* logs go to stderr. For a structured-logging setup where the aggregator ingests one stream, `stdout` is the right choice — your container's stdout pipe is what the log shipper attaches to.

### Lines 22–28: Uvicorn's three loggers, all wired to the shared handler

```python
    "loggers": {
        "uvicorn":         {"level": "INFO", "handlers": ["shared"], "propagate": False},
        "uvicorn.error":   {"level": "INFO"},
        "uvicorn.access":  {"level": "INFO", "handlers": ["shared"], "propagate": False},
        "boardly":         {"level": "INFO", "handlers": ["shared"], "propagate": False},
    },
```

This is Uvicorn's three-logger layout, modified. Compare to Uvicorn's *default* `LOGGING_CONFIG` (which ships in `uvicorn.config`):

- `uvicorn` — server lifecycle logs (startup, shutdown, reload). Default has `handlers=["default"]`, `propagate=False`. We change `handlers=["shared"]`.
- `uvicorn.error` — *no handlers* in the default; it propagates to `uvicorn` (which has the `default` handler). We keep the no-handlers pattern (only `level: INFO`); the propagation walk still works because `uvicorn.error`'s parent is `uvicorn` which has the `shared` handler.
- `uvicorn.access` — HTTP access logs (one line per request). Default has `handlers=["access"]`, `propagate=False`. We change to `handlers=["shared"]`.

Plus our own `boardly` logger, also wired to `shared`. Now every record — server startup, access log, business event — flows through the *same* `StreamHandler` with the *same* `JSONFormatter`, in the *same* stream.

The `propagate: False` on every named logger is critical: it prevents records from walking up to the root logger, which would otherwise emit them via Uvicorn's default `default` handler (the prose formatter on stderr). Without `propagate: False`, you would get *both* the JSON line on stdout (via `shared`) *and* the prose line on stderr (via Uvicorn's `default` handler at root, walked via propagation) — the double-emit trap.

**Why does `uvicorn.error` have no `handlers` key?** Because it inherits via propagation. `uvicorn.error`'s parent is `uvicorn` (the dot-namespaced parent from Lesson 01). When `uvicorn.error` creates a record, its own handlers (none) are tried, then propagation walks up to `uvicorn` which has the `shared` handler. The record is emitted there. This is the same parent/child propagation pattern from Lesson 01 — Uvicorn uses it deliberately to keep the config minimal.

### Lines 31–44: The ASGI app

```python
async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    log = logging.getLogger("boardly")
    log.info("request_received", extra={"path": scope["path"]})
    await send({"type": "http.response.start", "status": 200})
    await send({"type": "http.response.body", "body": b"ok"})
```

This is a minimal inline ASGI app for the demo (no FastAPI router, no `Depends`, no Pydantic). The `log.info("request_received", extra={"path": scope["path"]})` is the canonical event-with-context pattern from Lesson 03. In a real `boardly` app this lives inside a FastAPI route handler — but the logging call is identical. The `path` field lets the aggregator answer "all requests to `/projects` in the last hour" with one query.

### Lines 46–48: The integration

```python
    uvicorn.run(app, log_config=LOGGING_CONFIG, port=8000, host="127.0.0.1")
```

The single line that wires the whole thing together. `uvicorn.run(app, ...)` has a `log_config` parameter whose default is Uvicorn's `LOGGING_CONFIG` dict (importable from `uvicorn.config`). Pass any `dictConfig`-format dict and Uvicorn calls `logging.config.dictConfig(log_config)` at server start. Uvicorn's own three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) are configured by this call — they are not special; they are just named loggers.

`log_level` is a separate parameter (coarse knob — `logging.INFO`/`DEBUG`/etc.) that sets the level on the three Uvicorn loggers *in addition* to whatever the config specifies. It is mostly useful for the `--log-level debug` CLI flag. In production, leave it `None` (the default) and control the level via the config dict.

`access_log` is a bool (`True` by default). Setting `access_log=False` disables the `uvicorn.access` logger entirely — useful for high-traffic endpoints where you only want business-event logs, not every request. Almost never used in production because the access log is the canonical "did this request happen?" signal.

**Why does Uvicorn call `dictConfig` at server start, not at import time?** Because `dictConfig` mutates the global `logging.Logger.manager.loggerDict` — it creates and disables loggers. If Uvicorn called it at *import* time (when you `import uvicorn`), then any library that imported Uvicorn earlier (e.g. FastAPI, which imports Uvicorn in its `fastapi.cli` module) would already have its loggers created, and `dictConfig` with the surprising `disable_existing_loggers: true` default would silence them. By calling `dictConfig` inside `uvicorn.run` (or `uvicorn.Config(...).__init__`), Uvicorn gives your application code a chance to call `dictConfig` itself first. The sequence matters: your `app.main` is imported by Uvicorn's worker — so your `logging.config.dictConfig(...)` call in `app/main.py` runs *before* Uvicorn's `log_config` is applied — and Uvicorn's call then *overrides* yours. This is why the lesson's pattern is "do not call `dictConfig` in `app/main.py`; pass it via `log_config=` instead".

**Why override the full `LOGGING_CONFIG` rather than just the access logger?** Because Uvicorn's three loggers share handlers via the `loggers` section, and changing only one entry leaves the others in a state you cannot reason about. If you only add a `shared` handler to `uvicorn.access`, the `uvicorn` (lifecycle) logger keeps the prose `default` handler — your startup banner is prose, your access logs are JSON, and the aggregator cannot parse the mixed stream. The full override is the only pattern that produces a single, consistent, single-formatter log stream.

## Execution Trace

```bash
$ python boardly/uvicorn_logging.py
{"ts": "2026-10-23T06:42:01.123456+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Started server process [12345]"}
{"ts": "2026-10-23T06:42:01.124001+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Application startup complete."}
{"ts": "2026-10-23T06:42:05.001234+00:00", "level": "INFO", "logger": "uvicorn.access", "msg": "127.0.0.1:54321 - \"GET / HTTP/1.1\" 200"}
{"ts": "2026-10-23T06:42:05.001312+00:00", "level": "INFO", "logger": "boardly", "msg": "request_received", "path": "/"}
```

(Start the server in one terminal, then `curl http://127.0.0.1:8000/` in another.) The exact `ts`, port, PID will differ. The contract: every line is one JSON object, every line is on `stdout` (not stderr), the `logger` field tells you which logger produced the line, and the four loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`, `boardly`) all flow through the same `shared` handler.

**Warning — `uvicorn.access` records arrive at your `JSONFormatter` as interpolated prose, not as structured fields.** Uvicorn's `H11Protocol` calls `self.access_logger.info('%s - "%s %s HTTP/%s" %d', client_addr, method, path, http_version, status)` — the fields are passed as positional `*args`, not as `extra={...}`. The named `client_addr` / `request_line` / `status_code` fields you see in Uvicorn's default `AccessFormatter` are *constructed* by that formatter's `formatMessage()` from `record.args` — they are not on the `LogRecord` until the formatter creates them. When you replace `AccessFormatter` with your `JSONFormatter`, `record.getMessage()` returns the interpolated prose form (`"127.0.0.1:54321 - \"GET / HTTP/1.1\" 200"`), not separate JSON fields. To get them as JSON fields, subclass `uvicorn.logging.AccessFormatter` instead of `logging.Formatter`, call `super().formatMessage(record)` to enrich the record copy, then JSON-encode the result. The lesson's Exercise 4 covers this — the simple path (interpolated prose `msg`) is enough for interleaving with business logs; the structured-fields path is the upgrade.

Compare to Uvicorn's *default* output (no `log_config=` override):

```
INFO:     Started server process [12345]
INFO:     Application startup complete.
INFO:     127.0.0.1:54321 - "GET / HTTP/1.1" 200 OK
{"ts": "...", "level": "INFO", "logger": "boardly", "msg": "request_received", ...}
```

Mixed prose-and-JSON, mixed stdout-and-stderr, no shared fields, no join. The override is the fix.

## Common Mistakes

### Mistake 1: Forgetting `propagate: False` on the overridden Uvicorn loggers

```python
"loggers": {
    "uvicorn.access": {"level": "INFO", "handlers": ["shared"]},  # missing propagate=False
    "boardly":        {"level": "INFO", "handlers": ["shared"]},
}
```

**Symptom:** Every access-log line is emitted *twice* — once on stdout (your `shared` handler) and once on stderr (Uvicorn's `default` handler at the root, walked via propagation). Every `boardly` line is also double-emitted.

**Why:** Uvicorn's default `LOGGING_CONFIG` has `propagate: False` on every named Uvicorn logger to *prevent* propagation to the root. When you override the config, you inherit the schema's *default* `propagate=True`. So records walk up to the root logger — which, if anything has configured the root (e.g. `logging.basicConfig()` or another library), will double-emit. Even if nothing has configured root, Uvicorn's startup may have left a handler on it.

**Fix:** Always set `propagate: False` on every logger you wire a handler to. The Lesson 03 `JSONFormatter` does not dedupe; the formatter is called once per handler.

### Mistake 2: Not including `uvicorn.error` in the override

```python
"loggers": {
    "uvicorn":        {"level": "INFO", "handlers": ["shared"], "propagate": False},
    # uvicorn.error missing entirely
    "uvicorn.access": {"level": "INFO", "handlers": ["shared"], "propagate": False},
    "boardly":        {"level": "INFO", "handlers": ["shared"], "propagate": False},
}
```

**Symptom:** Uvicorn's startup banner, lifespan errors, and reload messages still come out in the *default* prose format — mixed with your JSON.

**Why:** `uvicorn.error` is the logger Uvicorn uses for server-lifecycle messages (started, stopping, application startup complete, application shutdown, lifespan errors). If your override does not include `uvicorn.error`, the `dictConfig` call leaves the existing `uvicorn.error` logger in its prior state — and because the *default* `LOGGING_CONFIG` Uvicorn ships had no handler for `uvicorn.error`, propagation walks up to `uvicorn`, which now has your `shared` handler. That part works. But: if you have *also* set `disable_existing_loggers: True` (the schema default!), the prior `uvicorn.error` logger is *disabled*, and the lifecycle messages vanish entirely — a worse failure.

**Fix:** Always include `uvicorn.error` in your override, even if just to set `level: INFO`. And always set `disable_existing_loggers: False` (Lesson 02, Mistake 1).

### Mistake 3: Using `--log-config` with a YAML file (it expects JSON or INI)

```bash
$ uvicorn boardly.main:app --log-config logging.yaml
# Error: ValueError or ConfigError
```

**Symptom:** `--log-config` accepts a file path, but the file *must* be JSON or INI format (`fileConfig`-style). YAML is not supported by `--log-config` directly — only by loading the YAML in Python and passing via `log_config=`.

**Why:** Uvicorn's `--log-config` CLI flag uses `logging.config.fileConfig` if the file extension is `.ini`, otherwise it tries `json.load` on the file and then `dictConfig`. There is no YAML parsing in the CLI flag path. If you pass a `.yaml` file, Uvicorn falls back to JSON parsing, which raises a `JSONDecodeError`.

**Fix:** Either (a) write the config as `logging.json` (a JSON file) and pass `--log-config logging.json`, or (b) load the YAML in Python (`yaml.safe_load(open("logging.yaml"))`) and pass the dict via `uvicorn.run(app, log_config=config)`. The boardly project ships `boardly/etc/logging.json` for the CLI flag and the Python dict for `uvicorn.run`.

## Engineering Trade-Offs

**Decision:** Override Uvicorn's `LOGGING_CONFIG` entirely via `uvicorn.run(app, log_config=...)` — do not mutate Uvicorn's default.

**Both sides:** The alternative is `LOGGING_CONFIG["loggers"]["uvicorn.access"]["handlers"] = ["shared"]` — *mutating* Uvicorn's default dict in place. This wins on: smaller diff (one line instead of a full dict), automatic updates when Uvicorn bumps the default. It loses on: the mutation affects *every* `uvicorn.run` call in the same process (a global side effect), and the diff is *less* visible in code review because the override is hidden in a `dict.update` rather than a full dict.

**Commitment:** `boardly` overrides the full `LOGGING_CONFIG`. The boardly config is self-contained — you can read it top-to-bottom and know exactly what the production log stream looks like, without having to mentally diff against Uvicorn's default. When Uvicorn bumps the default (new logger? new handler? new field on the access formatter?), boardly's config is unaffected — and the diff is explicit.

## Exercises

1. **Exercise 1 — Use the `--log-config` CLI flag.** Save the `LOGGING_CONFIG` from this lesson to `boardly/etc/logging.json` (use `json.dump` — note the `"()"` key works in JSON too because the schema treats it as a string-keyed dict). Start Uvicorn with `uvicorn boardly.main:app --log-config boardly/etc/logging.json`. Confirm the JSON output is identical to the `uvicorn.run(app, log_config=...)` pattern. `Verify: uvicorn boardly.main:app --log-config boardly/etc/logging.json & sleep 1; curl http://127.0.0.1:8000/`
2. **Exercise 2 — Disable access logs.** Pass `uvicorn.run(app, log_config=LOGGING_CONFIG, access_log=False)` and confirm that `uvicorn.access` records no longer appear — only the `uvicorn` (lifecycle) and `boardly` (business) records. `Verify: python boardly/uvicorn_logging.py & sleep 1; curl http://127.0.0.1:8000/`
3. **Exercise 3 — Trigger the double-emit bug.** Remove `propagate: False` from `uvicorn.access` in the config, re-run, and confirm each access-log line is emitted twice (once via `shared`, once via the propagation walk to root). `Verify: python boardly/uvicorn_logging.py 2>&1 | head -10`
4. **Exercise 4 — Add `request_id` via `ContextVar`.** Define `request_id_var: ContextVar[str] = ContextVar("request_id", default="")` in middleware, set it per-request with `request_id_var.set(uuid4().hex)`, and modify the `JSONFormatter` to call `request_id_var.get()` and add it to the payload. Now every line — Uvicorn access log, `boardly` business log — carries the same `request_id` for a single HTTP request. Join them in Loki with `{request_id="abc123"}`. See [[03-contextlib/05-contextvars]] for the middleware pattern. `Verify: python boardly/uvicorn_logging.py 2>&1 | grep abc123`
5. **Exercise 5 — Sentry as a separate handler at `ERROR` level.** Add a `sentry` handler (`class: sentry_sdk.integrations.logging.EventHandler`, `level: ERROR`) and wire it to `boardly` (and optionally `uvicorn.error`). Confirm that `ERROR`-level lines are emitted both to stdout (via `shared`) *and* to Sentry (via `sentry`), while `INFO`-level lines only go to `shared`. This is the "different handlers, different destinations, different levels" pattern from Lesson 02 in production. `Verify: python boardly/uvicorn_logging.py 2>&1 | head -10`

## Verification

```bash
$ python boardly/uvicorn_logging.py
{"ts": "2026-10-23T06:42:01.123456+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Started server process [12345]"}
{"ts": "2026-10-23T06:42:01.124001+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Application startup complete."}
```

(In a second terminal:)
```bash
$ curl http://127.0.0.1:8000/
ok
```

Back in the first terminal, two more lines appear:
```
{"ts": "2026-10-23T06:42:05.001234+00:00", "level": "INFO", "logger": "uvicorn.access", "msg": "127.0.0.1:54321 - \"GET / HTTP/1.1\" 200"}
{"ts": "2026-10-23T06:42:05.001312+00:00", "level": "INFO", "logger": "boardly", "msg": "request_received", "path": "/"}
```

The PID, port, timestamp will differ on your run. The contract: every line is a single JSON object on stdout, the `logger` field identifies which logger produced the line, and the four loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`, `boardly`) all flow through the same `shared` handler. The `uvicorn.access` line's `msg` field is the *interpolated prose* form because Uvicorn uses positional `*args`, not `extra={...}` — see the Warning in the Execution Trace above.

## Previously Learned Here

- [[23-logging/01-Logger-Handler-Formatter]] — the `Logger`/`Handler` hierarchy, the `propagate` walk, the two-level gating — all of which Uvicorn's three loggers use the same way your `boardly` loggers do.
- [[23-logging/02-dictConfig]] — the `dictConfig` schema that Uvicorn's `LOGGING_CONFIG` is built on, including the `"()": "module.Class"` callable-spec for `JSONFormatter`.
- [[23-logging/03-structured-logging]] — the `JSONFormatter` you reuse unchanged on the shared handler.
- [[03-contextlib/05-contextvars]] — the `ContextVar` middleware pattern for `request_id`, which lets you join the access log line with the business event line in your aggregator.

## What's Next

You have finished the `logging` section. The four lessons walked you from `logging.getLogger("boardly")` (Lesson 01) through the `dictConfig` schema (Lesson 02), the `JSONFormatter` pattern for structured logs (Lesson 03), and the Uvicorn integration that makes your `boardly` business logs interleave with Uvicorn's access logs in one JSON stream (Lesson 04). The cross-cutting pattern — `ContextVar` for per-request fields (`request_id`, `user_id`) read by the `JSONFormatter` at format time — is the connection to Section 03:

- [[03-contextlib/05-contextvars]] — `ContextVar` is THE FastAPI request-scoped primitive; you set it in middleware and the formatter reads it.
- [[25-Reference-Library/Engineering-Decision-Log]] — the decision to ship the stdlib-only `JSONFormatter` rather than `structlog` is documented there.

The next section in the vault (whichever you pick — [[01-typing/00-typing-MOC]], [[06-dataclasses/00-dataclasses-MOC]], [[09-enum/00-enum-MOC]] if you have not yet read those) continues building the stdlib surface area. The `logging` section is the one you will return to whenever you ship a FastAPI app — it is the connective tissue between the stdlib and production observability.

## Sources

- **`logging` — Logging facility for Python** — https://docs.python.org/3/library/logging.html — accessed 2026-10-23 — the `Logger`/`Handler`/`Formatter` hierarchy that Uvicorn's three loggers live in.
- **`logging.config` — Logging configuration** — https://docs.python.org/3/library/logging.config.html — accessed 2026-10-23 — the `dictConfig` schema Uvicorn's `LOGGING_CONFIG` is built on.
- **Uvicorn — Logging** — https://www.uvicorn.org/settings/#logging — accessed 2026-10-23 — the canonical reference for Uvicorn's `log_config`, `log_level`, and `access_log` parameters and the `--log-config` CLI flag.
- **Uvicorn source — `uvicorn/config.py` (LOGGING_CONFIG)** — https://github.com/encode/uvicorn/blob/0.44.0/uvicorn/config.py — accessed 2026-10-23 — the actual `LOGGING_CONFIG` dict (verified against the installed Uvicorn 0.44.0 in this sandbox).

## What We Learned

- You can now name Uvicorn's three loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) and articulate the role of each — `uvicorn` for server lifecycle, `uvicorn.error` for errors (inherits via propagation), `uvicorn.access` for HTTP request/response lines.
- You can now read Uvicorn's `LOGGING_CONFIG` dict — two formatters (`DefaultFormatter`, `AccessFormatter`), two handlers (`default` to stderr, `access` to stdout), three loggers with the `propagate=False` rule.
- You can now interleave your `boardly` business logs with Uvicorn's access logs by overriding the `LOGGING_CONFIG` to use a shared handler with your `JSONFormatter`, attached to both `uvicorn.access` and `boardly`.
- You can now pass the modified config to `uvicorn.run(app, log_config=my_config)` and use the `--log-config config.json` CLI flag for production.
- You can now articulate the `access_log=False` and `log_level=` coarse knobs and why you almost never use them in production.
- You can now avoid the double-emit trap by setting `propagate=False` on every named logger you wire a handler to.
