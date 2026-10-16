# YouTube Archiver

A self-hosted application that archives YouTube playlists locally: a web dashboard plus a CLI, sharing one core library.

## Language

**Playlist**:
A YouTube playlist the archiver is tracking. Identified by its YouTube playlist ID.

**Video**:
A single downloaded video belonging to a Playlist (or standalone, with no Playlist).

**Sync**:
The operation of checking a Playlist against YouTube and downloading any Videos not yet present in the archive. Triggered either manually (the "Sync All" / per-playlist sync buttons) or automatically by the Scheduler.
_Avoid_: refresh, scan, update, check

**Scheduler**:
The in-process background thread that triggers automatic Syncs on a timer. It is **not** an OS-level cron job — it runs only inside the Flask process, is armed at process startup, and has no existence independent of that process. "Cron" is reserved for a future real OS-level (or equivalent) scheduling mechanism, which does not exist yet.
_Avoid_: cron, cron job, cron task

**Auto Sync**:
The config flag (and Settings-page toggle) controlling whether the Scheduler is armed at process startup. When off, the Scheduler thread never starts and Syncs only happen when triggered manually.
_Avoid_: autosync, scheduling enabled

**Sync Status**:
Ephemeral, in-memory state describing a Sync currently in flight (which task is running, percent progress, when the last one finished). Lives only in process memory — lost on every restart. Exists purely to drive the live UI during an active Sync.
_Avoid_: progress, state

**Log Entry**:
A durable, structured record of something the application did (a Sync starting/finishing, a Video downloading or failing, the Scheduler's Heartbeat), persisted to the rotating log file under `config/`. Unlike Sync Status, a Log Entry is permanent history, not live progress.
_Avoid_: event, log line

**Heartbeat**:
A Log Entry the Scheduler emits on every tick, independent of whether any Sync is running, proving the Scheduler thread is still alive. A missing or stale Heartbeat is the signal that the Scheduler has silently died — distinct from a Sync simply failing.
_Avoid_: ping, keepalive

**Overdue**:
Said of a Playlist whose last Sync is older than its configured sync interval. Drives the dashboard's warning state. Distinct from a stale Heartbeat (the Scheduler itself not running) — a Playlist can be Overdue even while the Scheduler is healthy, e.g. every Sync attempt is failing.
_Avoid_: stale (reserved for Heartbeat staleness)

**Runtime State**:
The three JSON files (`config/config.json`, `config/playlists.json`, `config/downloaded_videos.json`) that the core library reads and rewrites as it runs. Generated application data, not source-controlled configuration — gitignored, not committed.
_Avoid_: config files, settings
