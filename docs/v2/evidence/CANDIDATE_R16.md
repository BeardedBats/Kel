# V2 CANDIDATE r16 — verified (2026-09-22, night)

Supersedes r15 (kept at `C:\Users\Nick\KelV2Candidate.r15`; its record is `CANDIDATE_R15.md`).

## What exists

| | |
| --- | --- |
| Candidate | `C:\Users\Nick\KelV2Candidate` (complete unpacked runtime) |
| Launcher | `Run-Kel-V2-Candidate.cmd` — exports `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate`, then `Start-Process`es `Kel.exe` in that folder |
| Source | `integration/v2` — the commit that carries this file |
| `Kel.exe` | 204,575,232 bytes, sha256 `f989e83d2181fbc6…` |
| `resources\app.asar` | 300,547,544 bytes, sha256 `88f343733485e2f4…` |
| `resources\kel-engine\KelEngine.exe` | 3,524,438 bytes, sha256 `00846a7e64fdaa9589a22abc…` (frozen from this worktree) |

## The packaging gate — it passed before anything was copied

`python C:\tmp\verify_asar.py` (see `ASAR_PACK_DEFECT.md` for why this exists):

| Check | Result |
| --- | --- |
| archive root `package.json` parses | **PASS** — `Kel 1.7.0-dev main=./out/main/index.js` |
| renderer bundles named by `index.html` present | **PASS** — missing: none |
| `out/main/index.js` byte-identical to the build | **PASS** — sha `9ba80282c1812173…` |
| `out/renderer/index.html` byte-identical to the build | **PASS** — sha `66b62a31ca2d1f62…` |
| verdict | **ARCHIVE SOUND** |

## Observed after the copy (both conditions the hand-off required)

| Check | Result |
| --- | --- |
| launcher | starts the app |
| window | titled **Kel** |
| engine | `…\KelV2Candidate\resources\kel-engine\KelEngine.exe --data C:\Users\Nick\KelV2Runs\prepared\candidate` |
| isolation | the protected stable engine stayed exactly as it was |

## What is new in this candidate

- **Phone conversation history** (V2-05 §10): the list re-reads when the phone returns
  (`visibilitychange` / `focus`), an empty history offers “New conversation”, and a conversation that
  no longer exists keeps the honest route state. Decision **D-51**.
- **Recipe library controls** (V2-07): search, category chips, favourites filter + star, “Recently
  used”, and per-recipe Copy — all through `/api/recipes`.
- Corrected requirement-list notes (S15/S28/S34) and **D-52**: multi-utterance dictation is outside
  V2 scope, kept as a documented limitation.

## Honest limits

Checks run for this candidate: renderer typecheck, production renderer build, the archive gate, and
the packaged launch (process/window/engine/root). The deferred audit list in
`REQUIREMENTS_STATUS.md` was deliberately **not** run. Nothing was promoted or installed; the stable
install, its data root and the shortcut were never touched.
