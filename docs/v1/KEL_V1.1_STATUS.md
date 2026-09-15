# KEL V1.1 — STATUS

Scope (approved): B1 second-instance → B2 failure-surfacing → B6 ACP project-root
confirmation → B3 planner/executor/reviewer provenance, plus a kickoff baseline run.

Kickoff: full engine suite = **152 passed, 10 subtests passed** (authoritative baseline).

## B1 — Second-instance focus-or-reject — DONE

Approach (clean, no subprocess/injection): single-instance lock already exists; the
first instance now runs `restore → show → focus → app.focus({steal:true})` on the
`second-instance` event, then — if the window is still unfocused after 250ms (Windows
denied foreground activation under the foreground lock) — calls
`BrowserWindow.flashFrame(true)` and clears the flash on `focus`.

Windows foreground-lock behavior is treated as an OS constraint (documented), not bypassed.

Files changed (AionUI donor shell source, main process only):
- `packages/desktop/src/process/utils/mainWindowLifecycle.ts` (focus + flash fallback)
- `packages/desktop/src/index.ts` (second-instance log line; handler unchanged otherwise)

Packaged verification (exact `Kel.exe` from Kel-V1.1-Dev):
- second launch never spawns another Kel Runtime / KellShell: **4 Kel + 2 backend, unchanged**
- second process exits cleanly (lock-lost path; `backend startup NOT registered (no lock)`)
- first instance receives the event: `[AionUi] second-instance received…` in daily log
- minimized Kel restores and becomes foreground (live)
- no spurious flash when already focused (live)
- clean shutdown leaves **zero** Kel / aioncore / KelEngine processes; relaunch OK (live)

Not directly observable in the automated harness: the taskbar flash on the denial path.
The denial itself is proven (a direct `SetForegroundWindow` returns False when another
GUI app holds the foreground lock), and the flash branch is gated on `!window.isFocused()`;
but reproducing the denial state automatically requires real user input to another app
(automation either moves foreground or releases the lock). Recommend one manual check:
click another app, then double-click `Kel.exe` — expect a taskbar flash, not silence.

### Packaging parity (resolved)

The shipped `app.asar` is content-deduplicated (1103 identical-file groups, 10,220,315 B
saved), which a plain `@electron/asar` 3.4.1 repack does not reproduce (78 MB vs 68 MB).
Rebuilt with a dedup-aware + integrity packer that reproduces the shipped layout:

- new `app.asar` = **68,063,904 B** (shipped 68,063,386 B; +518 B = the one changed file + header)
- entry count 10,589 == 10,589; dedup savings identical (10,220,315 B)
- extract diff vs shipped tree: **only `out/main/index.js` differs**

Frozen release (`Kel Releases/Kel-V1-Frozen`) untouched. Baseline asar backup kept at
`_kel-work/backups/app.asar.v1-baseline`.

## B2 — Failure-surfacing completeness — DONE

Added `kel.core.explain_failure(job)` (+ `explain_approval`) — a pure, read-only
formatter that turns existing job state (`route_block`, milestone `error`, check
reasons, verdict) into a four-part explanation: what happened / why / what Kel
already tried / what you can do next. Wired into:

- `Store.publish()` — the final reply for FAILED/UNCERTAIN now uses the explanation
  instead of the single `Blocker: <reason>` line.
- `acp_host.prompt()` — the `WAITING_RESOURCE` branch (provider failure, no eligible
  worker, worker exit) now emits the explanation instead of the bare
  `Work state: WAITING_RESOURCE. Verification: UNCERTAIN.` line. Approval wait keeps
  its existing D-03 permission text (verified as already complete).

The five target modes reproduce cleanly (`_kel-work/b2_out.txt`):
1. provider failure → "No worker could start this job" + `health circuit open`
2. no eligible worker → `not installed` / `authentication unavailable`
3. approval wait → existing permission guidance (no double-report)
4. environment-limited verification → "Kel could not fully verify the result" + reviewer reason
5. unexpected worker exit → "A worker stopped before this job finished" + preserved-work note

Tests: `tests/test_failure_surfacing.py` (new, 6 cases) + one ACP assertion.
Suite: **158 passed, 10 subtests** (was 152).

Packaging: rebuilt `KelEngine.exe` (PyInstaller 6.19.0, onedir) from the updated
source; `_internal/` unchanged (only `core.py`/`acp_host.py` changed — both live in
the PYZ inside the exe). Frozen exe stays byte-identical (hash `5ca0e632…`, no B2 code).

Packaged verification (exact `resources/kel-engine/KelEngine.exe` from Kel-V1.1-Dev):
- boots, `engine_version: 0.5.0`, providers listed
- live HTTP `status` request → "No work is running." (fast path OK)
- PYZ inspection confirms `kel.core`/`kel.acp_host` carry the B2 code

## B6 — ACP project-root confirmation — DONE

Root cause: `acp_host.session/new` adopted the donor-provided `cwd` (AionCore's
own temp/install working dir) as a project root, creating a `Temp`-rooted project
and binding the conversation to it. Reproduced live before the fix.

Changes (engine, `kel/`):
- `acp_host.py` — `session/new` no longer reads `cwd` or creates/reuses a
  project from it. A new conversation defaults to the unrooted `default`
  project; a root must come from an explicit project choice or greenfield.
  (The old reopen-time "belongs to another workspace" cwd comparison was removed
  with it.)
- `service.py` — added `CODING_VERBS`; `_plan` now routes a coding verb with a
  selected root to existing-project coding (previously it silently fell through
  to chat), and a coding verb with **no** root and no greenfield intent asks the
  user to pick a project instead of guessing.

Four scenarios verified (real `Service._plan` routing):
1. greenfield ("create an app") → still creates a new project (unchanged)
2. plain chat → chat reply, no prompt
3. ambiguous coding, no root → asks to choose a project (no silent Temp adoption)
4. existing-project coding, rooted → coding job using the selected root

Tests: `tests/test_b6_project_root.py` (4 cases) + updated `test_acp_host`
`session/new` case. Suite: **162 passed, 10 subtests** (was 158).

Packaging: rebuilt `KelEngine.exe` (PyInstaller onedir); `_internal/` unchanged.
Packaged verification (live engine): `session/new` with a donor temp cwd binds to
`default` (root=None) and creates **no** `Temp`-rooted project.

## B3 — Planner/executor/reviewer provenance — DONE

Records who planned, executed, and reviewed each job/run, persisted with job/run/review
state. No routing, provider-selection, or quality-heuristic behavior changed.

Engine changes (`kel/`):
- `service.py` — `_plan` sets `contract['planner']` = `{provider, model, compiler}` on
  all four routing branches: coding (`coding-contract-v2`), research (`research-v1`),
  document via commander model proposal (`commander-proposal-v1` + live planner
  provider/model), and template fallback (`document-template-v1`).
- `core.py` — `runs` gains a `model` column (B3 migration for pre-existing data dirs);
  `claim()` persists executor `provider`+`model`; `record_review()` persists
  `reviewer_provider`/`reviewer_model` on the manual_review check and the
  `review.recorded` event.
- `commander.py` — `descriptor()` exposes planner/reviewer identity; `review()` records
  reviewer provenance on the VERIFIED path.
- `engine.py` — review paths record reviewer provenance with a defensive
  `getattr(reviewer,'descriptor',None)` fallback (optional capability; no behavior change).

Tests: `tests/test_b3_provenance.py` (new, 5 cases) covers planner (template, model
proposal, coding), executor+reviewer recording, executor!=reviewer enforcement, and
restart survival. Suite: **167 passed, 10 subtests** (was 162).

Packaging: rebuilt `KelEngine.exe` (PyInstaller 6.19.0, onedir) from the updated source.
`_internal/` differs from B6 only in `base_library.zip` (stdlib bootstrap archive; build
ordering non-determinism already present B2→B6). Verified live: boots engine_version
0.5.0, connected, default project `root: None` (B6 intact); embedded PYZ carries the B3
code in `kel.service` (`planner`), `kel.core`/`kel.commander` (`reviewer_provider`),
`kel.engine` (`descriptor`).

## Status

All four approved items (B1, B2, B6, B3) are complete and packaged. Ready to freeze V1.1.
