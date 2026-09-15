# Kel V1.4 Release Manifest

> **Post-release note (added in V1.4.1):** the independent post-release audit (docs/v1.4-postrelease/)
> found overstated execution-path enforcement claims; the corrected boundary and patch record are in
> `docs/v1.4.1/`. The V1.4 frozen folder is untouched; this record is otherwise preserved.

Status: **VERIFIED** · Frozen: 2026-09-15 · Branch `v1.4-dev` · Tag `v1.4.0`

Scope: the solution-quality, Team, verification/continuation UX, provider/credential/autonomy,
desktop-productization, diagnostics, and full visual-redesign release — ten gates (G0–G9) executed with
reviewer-relay checkpoints, plus the G10 acceptance and packaging pass.

## Key hashes (see `SHA256Sums.txt.txt`, in order)

| Artifact | SHA-256 (prefix) | vs V1.3 |
|---|---|---|
| `Kel.exe` | `e048632e03fabc96…` | **identical** — same Electron runtime frame |
| `resources/app.asar` | `53a34f627ff9e18c…` | changed — V1.4 shell |
| `resources/kel-engine/KelEngine.exe` | `5c093e321c68e2d9…` | changed — V1.4 engine |

Byte-identical rebuilds are **not** promised (timestamps, ordering, toolchain); verify with
`scripts/verify-release.ps1 -ReleaseDir <this folder> -Manifest <this folder>/SHA256Sums.txt.txt`.

## Verified before freezing

- **Engine suite: 363 passed + 10 subtests** (`runtime`, pytest), including
  5 UPG-* upgrade tests, 30 AUTO-*, 20 PROV-*, 12 DIAG-*, 29 SLN/TEAM, 20 Gate-3 tests.
- **`scripts/verify-release.ps1`**: `OK` on all three artifacts — "Release verification passed."
- **Packaged smoke of this assembled release**: 23 captures, **0 renderer errors, 0 blank frames**,
  packaged launch, `appExitCode 0`, bounded engine shutdown.
- **V1.3 → V1.4 data upgrade**: a real V1.3 store gains all 22 V1.4 tables and migrations 5–9 additively
  with a pre-migration backup; every existing job and memory row is unchanged; reopening is idempotent;
  V1.4 features run on the upgraded data.
- **Accessibility, both themes**: 0 contrast failures (boot · work drawer · all eleven routes), 30/30 tab
  stops with a visible focus ring, skip link as the first tab stop on a fresh load, smallest text 12px,
  0 emoji. The V1.3 baseline measured 6 contrast failures and 0/30 rings.
- **Adversarial acceptance sweep** (`packaging/adversarial-review.py`): **0 blocking findings**;
  do-not-ship list clean (0 emoji, 0 gradients, 0 bounce/overshoot easing, reduced-motion present);
  packaged route allowlist intact; 527 capture files on disk.
- **Frozen V1.3 re-verified unchanged** during this release (`Kel-V1.3-Frozen` 3/3 hashes).

## Carried limitations (stated, not hidden)

- Engine shutdown on app close still requires the bounded kill in the harness.
- A profile migrated from V1.3 sees the first-run flow once and dismisses it with "Skip setup"
  (documented deviation of the flag-only rule).
- Provider live calls remain donor-dependent; no real API keys were exercised.
- 142 of the 200 ledger rows remain at their triage status — per-gate delivered scope and the surface
  column carry the detail (`KEL_V1.4_ADVERSARIAL_REVIEW.md` §3.1).
- Pet-window capture works on the verification candidate (2 windows) but returned 0 on this assembled
  release run; the pet settings switch is the difference under investigation.
- No vision-based aesthetic verdict was possible in this runtime; aesthetics rest on measured contrast,
  type, focus and density evidence plus the independent design review.

Do not modify this folder. All future work must happen in a separate copy.
