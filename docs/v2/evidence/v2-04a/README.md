# V2-04a evidence — the assistant bridge, live (2026-09-21)

The engine-level runtime journey is committed as a test (`runtime/tests/test_v2_connection_bridge.py`,
16 tests: helper subprocess → real engine HTTP → stand-in service, capability + one-shot grant,
mutating approval row resolved through `/api/approval`, bounded/scrubbed answers, provenance,
no-leak checks). This file records the **live** journey on `dev/v2` @ `d3bbf65` plus the honest
limits the run measured. Raw material: `live-run.txt` (worker text, events, messages, run rows).

## What ran

- A real work turn was submitted to the running engine (project `bridge-live`, kind `coding`):
  “Update notes.txt … Line two: the login name reported by the connected service — run
  `python -m kel.conn list`, then `python -m kel.conn call github-whoami`, and use the login it
  returns.”
- The connection `github` pointed at a **local stand-in service** on `127.0.0.1:41999` that answers
  `/user` only for the stored credential; the value was pushed into engine custody exactly the way
  the shell does (`supply`), never into the runtime.
- Job `3c35e589…` ran the work. The worker’s own report (raw in `live-run.txt`) shows the path:
  it found the connector, **called the action**, took the login it returned, wrote it as line two of
  `notes.txt`, and ran the project’s smoke command.
- The access history recorded the fact, with the runtime as the caller and no value anywhere:
  `{"action": "github-whoami", "source": "runtime", "state": "ok"}` — migration 27’s `source` fact,
  first live use.
- The run repository shows `notes.txt` = `bridge check` / `kel-bridge-live-account`; the stand-in
  service logged `"GET /user HTTP/1.1" 200` — the login exists only behind the stored credential.

## What the live run measured (limits and findings)

- **Claude Code was quota-blocked**: `claude -p` answers “You’ve hit your session limit · resets
  3:50pm”. Its attempts fail instantly (“Native Claude did not finish”); the engine’s fallback ran
  the work on **codex-code**, which carried the journey. The bridge itself is runtime-agnostic (the
  helper is a plain shell command), but this environment could not exercise the claude path today.
- **The first live attempt found a real defect**: the runtime reached for `python -m kel.conn` and
  failed — “No module named kel” — because the engine never exported its own runtime directory to
  descendants. Fixed in `d3bbf65` (`serve()` prepends the runtime dir to `PYTHONPATH`, idempotent);
  the second run is the one recorded here.
- **The job closed UNCERTAIN**, not verified: after two quota-failed claude attempts the codex
  attempt produced the change and the worker reported the smoke command passing, but the milestone’s
  full verification could not be confirmed (its review path shared the same quota). The honest close
  message is in `live-run.txt`; the bridge evidence stands regardless.
- **The phone line cannot reach a work turn yet**: a phone conversation turn is answered by the
  engine’s conversational path (measured: a 4.8 s “saved context” reply, no job, no runtime), and
  the work route needs a selected project (the Shell’s Work surface — Astra’s territory). Journey J
  is therefore held, not delivered; see `KNOWN_LIMITATIONS.md` and `PARALLEL_SHELL_TOUCHES.md`.

## Suites at this commit

- Engine: `python -m unittest discover -s tests` → **1142 tests, OK** (652 s).
- Desktop: `bunx vitest run` → **43 files / 358 tests, passed**; `bunx tsc --noEmit` clean.
- The bridge journey test alone: **16 tests, all pass**.
