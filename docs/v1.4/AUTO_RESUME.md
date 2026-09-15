# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~20:15 ET · **PROGRAM COMPLETE — Kel V1.4 released**

- **Status: all eleven gates CLOSED (G0–G10), Kel V1.4.0 released and verified from a clean clone.**
  Nothing is pending; this file is now a release record rather than a resume marker.

## Release state

- **Branch / tag / commit**: `main` @ `0a4fd21` (merge of `v1.4-dev`), annotated tag **`v1.4.0`**
  pushed to `origin`. `v1.4-dev` preserved at `3645672`.
- **Frozen release**: `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.4-Frozen` (app frame + resources +
  13 V1.4 documents + `RELEASE_MANIFEST.md.txt` + `SHA256Sums.txt.txt`).
  Hashes: `Kel.exe e048632e…` (identical to V1.3 — same Electron frame) ·
  `resources/app.asar 53a34f62…` · `resources/kel-engine/KelEngine.exe 5c093e32…`.
  `scripts/verify-release.ps1` → **3/3 OK · "Release verification passed."**
- **Frozen V1.3**: re-verified **byte-identical** (`e048632e… / cd0d51cb… / 8ed30d3d…`) and never modified.

## Acceptance evidence

- **Engine suite**: 363 passed + 10 subtests — in the working tree *and* in a clean clone of the tag.
- **Upgrade path**: a real V1.3 store gains all 22 V1.4 tables and migrations 5–9 additively with a
  pre-migration backup; existing rows unchanged; idempotent re-open; V1.4 features run on upgraded data.
- **Packaged smoke of the assembled release**: 23 captures, 0 renderer errors, 0 blank, `appExitCode 0`.
- **Accessibility**: 0 contrast failures in **both themes** (boot, drawer, eleven routes); 30/30 tab stops
  ringed; skip link first on a fresh load; 12px floor; 0 emoji (V1.3 baseline: 6 failures, 0/30 rings).
- **Adversarial sweep** (`packaging/adversarial-review.py`): 0 blocking findings; do-not-ship list clean
  (0 emoji, 0 gradients, 0 bounce easing, reduced-motion present); packaged allowlist intact;
  527 capture files; ledger 200 rows with 58 advanced to `IMPLEMENTED` citing their artifacts.
- **Independent checkpoints**: a Sonnet reviewer relay returned CONTINUE at every gate (G0–G9), plus an
  independent delegated design review at G1 and a DOM-level resolution of the drawer-semantics question.

## Carried limitations (recorded in the release manifest and the adversarial review)

- Engine shutdown on app close still needs the harness's bounded kill.
- A profile migrated from V1.3 sees the first-run flow once (documented deviation of the flag-only rule).
- Provider live calls remain donor-dependent; no real API keys were exercised.
- 142 of the 200 ledger rows remain at triage (per-gate scope and the surface column carry the detail).
- Pet-window capture worked on the verification candidate (2 windows) but returned 0 on the assembled
  release run; the pet settings switch is the difference under investigation.
- No vision-based aesthetic verdict existed in this runtime; aesthetics rest on measured evidence plus the
  independent design review.

## If work resumes

The next program (V1.5) must start from a **copy** of `Kel-V1.4-Frozen`; the frozen folders are read-only.
The verification loop, harness commands, fixture recipes and environment variables used throughout V1.4
are documented in `KEL_V1.4_TEST_MATRIX.md`, `KEL_V1.4_RELEASE_MANIFEST.md` and the individual gate
sections of `KEL_V1.4_STATUS.md`.
