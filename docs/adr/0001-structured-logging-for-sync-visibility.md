# Structured logging lives in core.py, persisted as rotating JSON-lines under config/

The Scheduler silently never starting (auto_sync off, unnoticed for weeks) was invisible because every diagnostic signal was an unstructured `print()` to stdout, visible only via `docker logs` and lost on restart. To make Sync and Scheduler activity (including a Heartbeat) actually visible on the dashboard, we need durable, structured Log Entries.

We're using Python's stdlib `logging`, writing structured JSON-lines to a size-rotated file under `config/` (already a persisted volume). The logging calls live in `core.py` — the library shared by both the CLI and the web app — not in `app.py`, so CLI invocations (and any future real cron/OS-level scheduling that drives the CLI directly) produce the same Log Entries as the web app's Scheduler.

## Considered Options

- **SQLite table**: more queryable, but adds schema/migration overhead this single-user self-hosted app doesn't need.
- **In-memory ring buffer**: zero disk I/O, but loses exactly the history you'd want after a crash or restart — the failure mode this decision exists to catch.
- **Logging only in `app.py`**: simpler, but the CLI (and any future cron-driven invocation) would produce no Log Entries at all.
