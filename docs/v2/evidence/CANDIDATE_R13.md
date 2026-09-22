# V2 CANDIDATE r13 — measured record (2026-09-22)

The first V2 candidate that launches. Everything below was observed, not inferred; the limits are
stated where the evidence stops.

## What exists

| | |
| --- | --- |
| Candidate | `C:\Users\Nick\KelV2Candidate` (923 MB, the complete `win-unpacked` runtime, not just `Kel.exe`) |
| Source revision | `integration/v2` — the worktree `C:\Users\Nick\Desktop\Kel\kel-v2-integration` at the commit that contains this file |
| `Kel.exe` | 204,575,232 bytes, sha256 `d628aec2a5068171f1b633dd…` |
| `resources\app.asar` | 300,453,798 bytes, sha256 `7dcec379199200561fb747cb…` |
| `resources\kel-engine\KelEngine.exe` | 3,524,438 bytes, sha256 `00846a7e64fdaa9589a22abc…` — **byte-identical to the engine frozen from this worktree** by `scripts/build-runtime.ps1`, whose packed module set `packaging/verify_engine_pyz.py` confirmed (67 `kel` modules, `MISMATCH: []`, `RESULT: OK`) |
| `resources\bundled-aioncore\win32-x64\aioncore.exe` | 99,193,856 bytes, sha256 `67eb0277…` — the donor AionCore v0.2.2 process host, provenance-checked against its own `provenance.json` |
| Launch | `set KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate` then run `Kel.exe`. Without `KEL_DATA_DIR` the app uses `%APPDATA%\kel-desktop\work` — **never** the stable dogfood root |

## What was measured on the packaged app

| Check | Result |
| --- | --- |
| Launch | window titled **Kel**; `[CDP] Agent browser control enabled` in the app's own log |
| Backend identity | `C:\Users\Nick\KelV2Candidate\resources\kel-engine\KelEngine.exe --data C:/Users/Nick/KelV2Runs/prepared/candidate` — the packaged engine, on the isolated root |
| Donor process | `C:\Users\Nick\KelV2Candidate\resources\bundled-aioncore\win32-x64\aioncore.exe` |
| Isolation | the stable pair (`KelDogfoodCandidate` engine, pid 26544, `--data …KelDogfoodRuns\prepared\engine`) stayed exactly as it was; no process attached to a foreign root |
| Data root | `kel.sqlite3`, `desktop-session.json`, `desktop.log`, `controller.lock`, `backups/pre-v13-20260922-134305.sqlite3` — the app migrated its **own** database |
| Packaged backend surfaces | `/api/state` (engine_version, conversations, approvals …) and `/api/work` (keys `work`, `schema`, `recipes`, `memory`, `project_id`, `map`; 7 rows) answered over the engine's own 127.0.0.1 descriptor with its bearer token |
| Shutdown | app stopped, its engine stopped; stable engine untouched |
| Relaunch | window **Kel** again, candidate engine back on the same isolated root, database still there |

## The packaging defect this run found (and fixed)

The first pack of the day produced an `app.asar` whose root `package.json` held 4,402 bytes of `sw.js`
text. Electron therefore refused the app: *“Error launching app / Unable to parse package.json /
Unexpected token 'ACHE_NAME)' is not valid JSON”*. Root cause: a **previous** session ran
`@electron/asar extract-file … package.json` from `desktop/`, and that command writes its output into
the current directory — it had overwritten the tracked `desktop/package.json`, and the packer faithfully
packed the corrupt input. `git checkout -- desktop/package.json` restored it (10,586 bytes, `name Kel`,
`main ./out/main/index.js`) and the repack produced a valid manifest. Full note: `PACKAGE_EVIDENCE.md`.
The rejected copy is kept at `C:\Users\Nick\KelV2Candidate.rejected-manifest-20260922`.

## Honest limits of this record

- No browser-driven pass through the **packaged** UI was possible (the desktop build keeps its WebUI
  closed); the renderer flows below were measured on the same renderer build served by the WebUI host.
- A physical iPhone, the V2-19 regression groups beyond the ones listed in `MARATHON_STATE.md`, and the
  V2-16 timing numbers are **not** covered here.
- The candidate is a *runnable, verified candidate*; it is **not** fully accepted V2, and nothing was
  promoted, installed, or pointed at the stable data root.

## Continuation steps (next executable actions, in order)

1. `C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` stay untouched; the V2
   engine root for journeys stays `C:\Users\Nick\KelV2Runs\prepared\engine`.
2. Finish the open browser checks on the WebUI host (`desktop/scripts/webui.ts`, port 33100) against the
   **candidate** engine: unauthenticated deep link → login → intended conversation → refresh; direct
   Work links; ordinary login; local password recovery; and a remote-mode request refused at the outer
   boundary (the loopback decision now lives in `static-server.ts::onData`, pinned by
   `static-server.unit.test.ts`).
3. Re-run the corrected journeys (`runtime/tools/acceptance_journeys.py --journeys J-WORK,J-RECOV`) and
   record the new assertions: a stopped job offers **no** action it cannot honour, keeps its request, and
   says so.
4. Diff the packaged `app.asar` renderer against `desktop/out/renderer` for every build (build-filename
   fingerprint) before any future copy to the candidate path.
