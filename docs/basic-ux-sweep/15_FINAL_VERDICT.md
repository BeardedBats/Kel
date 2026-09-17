# Final verdict — basic UX sweep

**Shipped artifact: `dist/package-final6/win-unpacked`** (Kel 1.5.0, win-x64) + installer
`dist/package-final6/Kel-1.5.0-win-x64.exe`.

| File | sha256 |
|---|---|
| `win-unpacked/Kel.exe` | `5150ddc15ddfa91d1ff76e0e33dccf9bf8fad80a5e85f37290953e09b9623872` |
| `win-unpacked/resources/app.asar` | `edfd758f335fe0221e8e191701c7284d3a7c96201f6e701fe7cc9904cc418352` |
| `win-unpacked/resources/kel-engine/KelEngine.exe` | `de973cf63118e73d7480b7a1c6de100abfd2abae2e7d8584bffc54ceede6f7de` |
| `Kel-1.5.0-win-x64.exe` (198,456,102 bytes) | `86290d9cd2e4e26116bf5b58bb8dcd4e23967667cd1b71d131b8aec95267ad1b` |

Build: `scripts/build-runtime.ps1` → `desktop && bun run package` → `electron-builder --config
kel-builder.json --win --x64 --config.directories.output=../dist/package-final6` (all exit 0).
The shell executable and `app.asar` are byte-identical to the previous build; only the engine
changed (the backup/restore fix below). Source: worktree `kel-ux-v15`, branch `ux/v15-journeys`,
committed as `612c325` (the artifact was built from this working tree).

## How it was verified

- Engine: `runtime && python -m pytest tests -q` → **529 passed** (10 subtests).
- Renderer: `desktop && bunx tsc --noEmit` → **0 errors**.
- Packaged battery: `node packaging/ux-audit.cjs <app> <root> <out> <scenario>` on a **fresh copy of
  one seeded root** (`sweep-seed` + `seed-sweep.py`), strictly one app instance at a time and never
  while a build was running. Probes: `a11y-probe.cjs`, `probe-skip-link.cjs`.
  Scratch runner: `C:\Users\Nick\Desktop\Kel\ux-audit\run-f3-battery.sh` (edit `APP`).

## As-built results

| Scenario | Result on `package-final6` |
|---|---|
| `sweep2` — composer, drafts, restart, rename, mention, markdown | 0 errors. `composerFocused` true; drafts survive navigation **and** restart; `renameWorked` true (row menu); mention popup appears; markdown probe inside the shadow root: `textFound` true, **tables 1, pre 1, code 2, links 1**; copy affordance present (`i-icon-copy`). Only `failure-surface`/`retry` timed out — they need a provider (see below). |
| `sweep3` — theme colors, model card/pill, backup, data path, text size, zoom | 0 errors, **no timeouts**. `themeColorsSection` + 10 inputs; `accentOverrideApplied`; `contrastWarningShown`; `restoreAllWorked`; `defaultModelCard` present; `modelPillFound` 1; `dataPathShown` + `copyPathToast`; **`backupCreated`** (`Kel-Backup-20260916-211653`, contains `kel.sqlite3` **and** `host/aionui/aionui-backend.db`, no Chromium caches); `restoreConfirm`; text size `0.95 → 1 → 0.95`; Ctrl+= / Ctrl+0 `0.95 → 1 → 0.95`. |
| `sweep4` — backup, restore, restart recovery, model page | 0 errors, no timeouts. Backup created; confirm dialog names the real backup path; `restoreStaged` true; after restart **`rowsAfterRestore` 2 and `restoreRecovered` true** (the deleted transcript came back); `.pre-restore-20260916-211803` keeps the previous data. |
| `transcription`, `hardening`, `voice-vetting`, `vetting` | 0 errors, no timeouts (recording → row → rename → upload → composer; jargon sweep `jargonOffenders: []`; vetting batches, decisions, spec). |
| Standing set: `first-run`, `tour`, `settings`, `palette`, `keyboard`, `readability`, `sider`, `maintext` | 0 errors, no timeouts. |
| Probes: `v13-a11y.json`, `skip-link-evidence.json` | 0 errors, no timeouts. |

## Defects found by this round and fixed before shipping

| # | Defect | Fix |
|---|---|---|
| F11 | **The whole app could blank** on Settings · Model and on any Kel chat: `action=get` answered without `providers`, `KelModelControl` crashed on `state.providers.map(...)`, React unmounted the page | `get`/`list` answer one payload; the control paints a plain unavailable state |
| F12 | Backup failed while Kel was running (`WinError 32` on `controller.lock` and Chromium's `host/Network/Cookies`) | runtime state excluded (logs, markers, lock, Chromium tree; inside `host` only `config` + the databases), databases hot-copied through SQLite, unreadable files recorded under `skipped`/`notes` |
| F12b | A staged restore was **never applied** at the next start (rollback copy and `rmtree` hit the same live files) — found while verifying F12 | restore merges instead of deleting, writes databases through SQLite, keeps a best-effort `.pre-restore-*`, and clears the marker only when it succeeded |
| F13 | The Theme colors section never learned about its own changes (no contrast warnings, no “Restore all colors”) | rows' `onChanged` wired to the section refresh |
| F14 | Audit probes measured the wrong things (CSS font size for zoom, dark-theme contrast assumption, stale markdown timing, first-match row menus) | probes measure the real zoom factor after a Ctrl+0 reset, drive Ctrl +/−/0 through Electron's input path, force a genuinely low-contrast pair, scroll to the newest message, target the hovered row's menu |
| F15 | The probe was blind to **shadow DOM** (assistant replies render inside a shadow root) | probes walk shadow roots; the app was not changed — the rendering was verified correct inside the shadow root |
| F16 | The seeder corrupted its own rich message (`'\n'.join(rich)` stored it one character per line) | seeder writes the block as-is; the sweep2 run above is the honest re-run |

## What this verdict does **not** claim

- **Provider-dependent paths**: live streaming, stop, retry-after-failure, notifications and work
  cancellation need a connected provider. The UI wiring exists and the plain fallback copy
  (“Kel is waiting for a model to continue.”) is what the battery actually sees; live behaviour is
  classified honestly as unverified, not as passing.
- **Copy feedback**: the copy affordance is present and clickable; the success feedback is an inline
  “copied” state, which this probe does not observe (a toast-based check returns nothing).
- **Rich-message seed**: the markdown probe result above comes from the re-run with the fixed seeder
  (F16); earlier runs in `ux-audit/runs/f3-f3-*` used the character-split seed and are kept only as
  history.
- Screenshots in `evidence/final/` are from the runs named in the table; where a scenario was
  re-run after a fix, the newer JSON is the one stored.

## Evidence map

| Where | What |
|---|---|
| `evidence/audit/ux-sweep-a.json`, `ux-sweep-b.json`, `ux-sweep-seed.json` | pre-fix audit runs |
| `evidence/final/ux-sweep2.json`, `ux-sweep3.json`, `ux-sweep4.json` | the three sweep scenarios on the shipped artifact |
| `evidence/final/ux-*.json` | feature + standing battery on the shipped artifact |
| `evidence/final/*.png` | the screenshots the runs captured |
| `C:\Users\Nick\Desktop\Kel\ux-audit\runs\f3-*` | raw run directories (JSON + screenshots) behind `evidence/` |
