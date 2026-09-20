# 04 — PACKAGE IDENTITY (fresh build from the production target)

Independent package built by this re-audit from the production target `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`
(audit worktree `kel-v16-human-visual-reaudit` @ `37b1f27…`; production tree identical to the target — docs-only diff).
The campaign's own package is used for comparison only, never as primary proof.

## Build

- Command: `node scripts/build-with-builder.js auto --win` (same entry point as the campaign).
- Environment: bun 1.4.2, node v24.18.0, electron-builder 26.15.2, `electronDist=node_modules/electron/dist`
  (electron 44.3.0), compression level 7 (local), signing via signtool (electron-builder managed).
- Fresh worktree ⇒ no `out/`, no Vite cache, no `dist/` ⇒ renderer/main/preload were compiled from source in
  this audit; no output was copied. Full log: `evidence/build-reaudit.log` (BUILD_EXIT=0, "Build completed").

## Chain of identity

| Stage | Artifact | Hash / result |
| --- | --- | --- |
| Source | `6d957ee9…` (= tree of `37b1f27…`) | verified; production-tree equality documented in `00_BINDING.md` |
| Staged engine | `dist/runtime/KelEngine/KelEngine.exe` | `f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8` (31 files, hash-verified before build) |
| Built renderer/main/preload | `out/renderer`, `out/main`, `out/preload` (manifests) | `d84453f7…`, `ea921d34…`, `50c013bd…` — byte-identical to the campaign build (see below) |
| Packaged engine | `win-unpacked/resources/kel-engine/KelEngine.exe` | `f525b15b…` = staged = campaign package engine; directory tree manifest `bf3f8cec…` identical to campaign |
| Packaged app | `win-unpacked/resources/app.asar` + `app.asar.unpacked` | file set identical (35,652 files); app code byte-identical; see diff classification below |
| Installer | `dist/package-r12/Kel-1.6.0-win-x64.exe` | sha256 `170df43843e577723918b0a3ee8dbf4f9318c871a9db28cf9126f3ec3b9ced8d`, 213,615,918 bytes, signed |
| Installed files | `C:\Users\Nick\KelVisualReauditInstall` | recorded in `05_INSTALLED_REVIEW.md` |

Exe metadata: ProductName **Kel**, ProductVersion 1.6.0.0, FileVersion 1.6.0.

## Cross-build comparison vs the campaign package (comparison only)

Evidence: `evidence/pkg-chain-source.txt`, `evidence/asar-compare.txt`, `evidence/asar-compare-extra.txt`.

- File sets identical: 35,652 vs 35,652; zero files only on either side.
- Renderer / main / preload manifests byte-identical; `package.json` identical; `out/**` — zero differing files.
- Different files: exactly 51, all `node_modules/better-sqlite3/build/**` MSVC build intermediates whose bytes
  embed absolute build paths (`.tlog`, `.iobj`, `.ipdb`, `.lib`, `.exp`, `.vcxproj*`, aux `test_extension.*`).
  The runtime native binary `better_sqlite3.node` and all app code are byte-identical.
- Resource trees: `bundled-aioncore` 2189/2189 files, `hub` 9/9, `pet-states` 22/22, `fonts` 9/9 — equal counts;
  engine tree manifest identical (above).
- Installer exe hash differs from the campaign installer (`0dc5dc36…`) — expected across independent builds
  (embedded timestamps/signing); every content-level input we can compare is identical.

**Conclusion:** the fresh package's app payload corresponds exactly to the audited source; no stale renderer, no
stale donor assets (donor theme cover absent — see `02_FINDING_REPLAY.md` HV-09), canonical K present, and the
packaged engine remains the audited engine `f525b15b…`.

## Note B verification (installer rebuilt after support-script naming fix)

- Source delta of the rebuild commit `6d957ee`: **exactly one file**, `support/report-installer-failure.ps1`
  (2 insertions, 2 deletions) — `git diff --name-status 65bcaa3..6d957ee` (evidence: `01_DELTA_REVIEW.md`).
- The support script is NSIS-installer material, not app code (it is not part of `app.asar`); the app payload is
  therefore unaffected by that rename. This is confirmed mechanically by the cross-build comparison above: two
  independent builds of the same tree produce byte-identical app code; the only variance is native build
  intermediates. The campaign additionally re-ran installer smokes after the rename (`evidence/smokes` in the
  repair record: report script PASS `status=skipped code=E1003`).
- The final campaign installer (`0dc5dc36…`) is the artifact recorded at completion; the on-disk file re-hashes
  to `0dc5dc36…` today (no stale artifact substituted). This audit does not use it as primary proof — the
  independent build + install are primary.

## Note A verification (audit-install incident + restoration)

- Preserved audit install `C:\Users\Nick\KelV16ReviewInstall`: engine `df4f0ee991dfd5c0d74e54fffc9510ebf4948dd3d9050088f39561a33ea7e01f`,
  `Kel.exe` `f65b430ad2bd62868f5846d40c3a201b60ff43847e47abf52a857476ecc84a96` — matches the audit build state
  (distinct from the repair build). Re-verified untouched after this audit's install: see `05_INSTALLED_REVIEW.md`.
- Review install `C:\Users\Nick\KelVisualFixInstall`: engine `f525b15b…`, `Kel.exe` `28ad709821a3…`; registry
  (`HKCU\Software\9280710d-…` InstallLocation) pointed at it at audit start → the repair evidence's dedicated
  review install identity is correct; no package identity confusion found.
- Registry backups taken before any mutation: `C:\Users\Nick\KelVisualReauditRuns\registry-backup\`.

## Verdicts (this document's scope)

- Package identity chain: **BOUND** (source → built renderer → staged engine → packaged engine → installer).
- Engine remains the audited engine: **YES** (`f525b15b…`, tree-identical).
- Stale renderer / stale donor assets: **NONE FOUND**.
- Note A: **CONFIRMED SAFE** (identities distinct; preservation re-checked).
- Note B: **CONFIRMED SAFE** (rename limited to installer material; payload unaffected; final installer matches
  the recorded artifact).
