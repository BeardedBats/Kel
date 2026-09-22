# V2 CANDIDATE r15 — verified (2026-09-22, late evening)

Supersedes r14. r14 is preserved at `C:\Users\Nick\KelV2Candidate.r14` (its record is
`CANDIDATE_R14.md`).

## What exists

| | |
| --- | --- |
| Candidate | `C:\Users\Nick\KelV2Candidate` (complete unpacked runtime) |
| Launcher | `Run-Kel-V2-Candidate.cmd` — exports `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate`, then `Start-Process`es `Kel.exe` in that folder |
| Source | `integration/v2` — the commit that carries this file (the implementation increment is `2e60c64`) |
| `Kel.exe` | 204,575,232 bytes, sha256 `fb139e4e7b3c6ff2…` |
| `resources\app.asar` | 300,545,148 bytes, sha256 `b6335e04348f2fc8…` |
| `resources\kel-engine\KelEngine.exe` | 3,524,438 bytes, sha256 `00846a7e64fdaa9589a22abc…` (the engine frozen from this worktree) |
| `resources\bundled-aioncore\win32-x64\aioncore.exe` | 99,193,856 bytes, sha256 `67eb02774bab3855…` (donor AionCore v0.2.2 process host) |

## The packaging gate (it passed before anything was copied)

`ASAR_PACK_DEFECT.md` records that this pack path produced a corrupt archive twice. The gate used
here — and to be used for every future pack — is `python C:\tmp\verify_asar.py`:

| Check | Result |
| --- | --- |
| archive root `package.json` parses | **PASS** — `Kel 1.7.0-dev main=./out/main/index.js` |
| renderer bundles named by `index.html` present | **PASS** — missing: none |
| `out/main/index.js` byte-identical to the build | **PASS** — sha `9ba80282c1812173…` |
| `out/renderer/index.html` byte-identical to the build | **PASS** — sha `4ebdacb0eb07544d…` |
| verdict | **ARCHIVE SOUND** |

## What was observed after the copy

| Check | Result |
| --- | --- |
| launcher | starts the app (`Kel V2 candidate` banner, then the window) |
| window | titled **Kel** |
| engine | `…\KelV2Candidate\resources\kel-engine\KelEngine.exe --data C:\Users\Nick\KelV2Runs\prepared\candidate` |
| donor process | `…\KelV2Candidate\resources\bundled-aioncore\win32-x64\aioncore.exe` |
| isolation | the protected stable engine stayed exactly as it was; nothing attached to a foreign root |

## What is new in this candidate (implementation, not just a rebuild)

1. An expired session routes to sign-in **with the destination remembered** (the bridge signals it,
   the provider flips state, the router's gate takes over) instead of falling back home.
2. The Kibble page has the Build Update panel: findings → mission → milestones/attempts → candidate
   evidence → Approve/Reject with a note. Fix Capture statuses are untouched and installing is not
   offered.
3. A recipe's runs can be reopened (history + last result) with a link to the run on the Work page.
4. `/api/work` rows carry the id their action needs, and the Work page renders that action per row
   (answer / resume / stop / retry) instead of only job-level pause/cancel.

## Honest limits

- The packaged **renderer** flows above were not yet walked in a browser on this build; the checks
  that were run on the packaged app are process/window/engine/root and the archive gate. Everything
  else on the deferred audit list is in `REQUIREMENTS_STATUS.md` and was deliberately not run.
- A physical iPhone, live-service credentials, real Muse audio and the V2-19/V2-16 passes remain
  outstanding, each for the reason recorded there.
- This is a **verified, launchable candidate** for implementation testing — not fully accepted V2,
  and nothing was promoted or installed.
