# 07 — Kel V1.4.1 Release Manifest

Status: **VERIFIED** (local release; **not pushed** to origin) · Date: 2026-09-15 · Scope: the
post-release-audit correction patch. Small and surgical by design; V1.5 work is separated in
`06_V1_5_DEFERRED_WORK.md`.

## Identity

| Item | Value |
|---|---|
| Patch commit | `790752e` (branch `v1.4.1-dev`, preserved) |
| Merge commit / tagged commit | `725c905` on `main` |
| Tag | `v1.4.1` (annotated) |
| Frozen release folder | `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.4.1-Frozen` |
| Prior releases | V1.4 frozen folder re-verified **3/3 unchanged** (hashes below); V1.3/V1.2/V1.1 also untouched |

## Key hashes (order in `SHA256Sums.txt.txt`: Kel.exe, resources/app.asar, resources/kel-engine/KelEngine.exe)

| Artifact | SHA-256 | vs V1.4 |
|---|---|---|
| `Kel.exe` | `e048632e03fabc96de5e10afbebc0aa31f4e1674155ea3d270597fe7523f9d80` | **identical** (same Electron frame) |
| `resources/app.asar` | `ea1ed44776cc1b1612ea9fe468a1cdc190e7011414bbdcac9b13fe7aa11d5c99` | changed — patched shell (9,556 files; dedup 10,220,315 B, parity held) |
| `resources/kel-engine/KelEngine.exe` | `d107aa8742d99faeaf870cb103ecd6f57bf89af7c8d94c8bc18738e12799dcec` | changed — patched engine (PYZ structural match 33/33 vs source) |

Reference (V1.4 frozen, unchanged): `e048632e…` / `53a34f62…` / `5c093e32…`.

## Verified before freezing

- **Engine suite:** 375 passed + 10 subtests (working tree), including the 12 new V1.4.1 tests
  (`test_v141_boundaries.py`, `test_v141_claims.py`).
- **Adversarial sweep:** `packaging/adversarial-review.py` → 0 blocking findings.
- **Engine bundle:** `verify_engine_pyz.py` → 33/33 modules matched, `RESULT: OK`.
- **Packaged smoke of the assembled release:** 31 shots, **0 renderer errors, 0 blank-suspect
  frames**, `engineStopped: true` (graceful — no bounded kill needed), `appExitCode 0`; captured
  page text proves the patched copy (deferral notice on Autonomy, "Covered by test" column,
  emergency-stop scope note, Providers injection notice, "Engine 1.4.1" on Diagnostics).
- **`scripts/verify-release.ps1`** on the frozen folder → `OK` ×3 — "Release verification passed."
  (independently re-checked by `sha256sum`).
- **V1.4 frozen re-verified untouched** (3/3, same hashes as at V1.4 freeze).

## Folder contents

Frame + `resources/` (new `app.asar`, new `kel-engine/`, `bundled-aioncore/`, `pet-states/`, `pwa/`,
`default_app.asar`, licenses) + the corrected 13 `KEL_V1.4_*.md` documents + this patch's
`01…06_*.md` + `RELEASE_MANIFEST.md.txt` + `SHA256Sums.txt.txt`.

Repo-side only (mirroring the V1.4 convention): this `07_RELEASE_MANIFEST.md` and the
`docs/v1.4-postrelease/` audit set. The frozen folder also still carries the inherited `debug.log`
from the Electron frame — recorded as a V1.5 packaging-hygiene item (`06_V1_5_DEFERRED_WORK.md` #9).

## Notes

- Byte-identical rebuilds are **not** promised (timestamps/ordering/toolchain); verify with
  `scripts/verify-release.ps1 -ReleaseDir <folder> -Manifest <folder>/SHA256Sums.txt.txt`.
- **Not pushed:** `origin/main` still points at `926e346`; local `main` is `725c905` plus the
  release-record commit added immediately after this file. Push is left to the owner.
