# V2 CANDIDATE r14 — verified record (2026-09-22, evening)

Supersedes r13. Everything here was observed on the packaged runtime; limits are stated where the
evidence stops.

## What exists

| | |
| --- | --- |
| Candidate | `C:\Users\Nick\KelV2Candidate` (complete unpacked runtime, 23 entries) |
| Launcher | `C:\Users\Nick\KelV2Candidate\Run-Kel-V2-Candidate.cmd` — exports `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate`, then `Start-Process`es `Kel.exe` in that folder |
| Source | `integration/v2` in `C:\Users\Nick\Desktop\Kel\kel-v2-integration`; the commit that carries this file |
| `Kel.exe` | 204,522,496 bytes, sha256 `689dfd58…` |
| `resources\app.asar` | 300,537,319 bytes, sha256 `c4463f57…` |
| `resources\kel-engine\KelEngine.exe` | 3,524,438 bytes, sha256 `00846a7e64fdaa9589a22abc…` — byte-identical to the engine frozen from this worktree (`scripts/build-runtime.ps1`; `packaging/verify_engine_pyz.py`: 67 modules, `RESULT: OK`) |
| `resources\bundled-aioncore\win32-x64\aioncore.exe` | 99,193,856 bytes, sha256 `67eb0277…` — the donor AionCore v0.2.2 process host |

## Checks that gated this copy (minimum, per `ASAR_PACK_DEFECT.md`)

| Check | Result |
| --- | --- |
| `desktop/package.json` valid before packing | `Kel 1.7.0-dev`, `main ./out/main/index.js` |
| archive root `package.json` parses | `Kel 1.7.0-dev main=./out/main/index.js` |
| every renderer bundle named by `index.html` present | missing = none |
| `out/main/index.js` in the archive vs the build | **byte-identical** (3,977,512 bytes) |
| `out/renderer/index.html` in the archive vs the build | **byte-identical** (2,122 bytes) |

## What was observed on the packaged app

| Check | Result |
| --- | --- |
| launcher | prints the folder and data root, then starts the app |
| window | titled **Kel** |
| engine | `…\KelV2Candidate\resources\kel-engine\KelEngine.exe --data C:\Users\Nick\KelV2Runs\prepared\candidate` |
| donor process | `…\KelV2Candidate\resources\bundled-aioncore\win32-x64\aioncore.exe` |
| data root | the candidate's own `kel.sqlite3`, `desktop-session.json`, `backups\` — the app migrates its own database |
| isolation | the stable engine (`KelDogfoodCandidate`, `--data …KelDogfoodRuns\prepared\engine`) stayed untouched; no process attached to a foreign root |
| shutdown / relaunch | app and engine stop together; relaunch restores window, engine and database |

## Same build verified in the browser (WebUI, signed in)

Deep-link destination retention (link → sign-in → that conversation → refresh), the honest
unknown-conversation state, and the phone-viewport surfaces (Projects, Work, Activity, Kibble) —
details and timings in `V2_05_DEEPLINK_RETENTION.md`.

## Honest limits

- The packaged **window** was verified by process, window title and its own engine; a browser-driven
  pass over the packaged renderer (its own `--webui` surface) is the next check, not done here.
- A physical iPhone, the V2-19 regression groups beyond those recorded, and the remaining V2-16
  numbers are **not** covered here.
- The pack path produced a corrupt archive twice today; the minimum check above is what makes this
  copy trustworthy (`ASAR_PACK_DEFECT.md`).
- This is a *verified, launchable candidate* — not fully accepted V2, and nothing was promoted,
  installed or pointed at the stable data root.
