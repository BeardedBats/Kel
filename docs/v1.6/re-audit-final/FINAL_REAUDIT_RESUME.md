# FINAL RE-AUDIT RESUME (durable state)

If anyone must continue this work, this file + the committed tree is the state. Chat is not the
authority. **Nothing remains to run** except the human gates — the re-audit is complete.

## Where things are

- Audit worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-postrepair-audit`
  (branch `audit/v16-postrepair-final`, based on `7cf6030`).
- Documents: `docs/v1.6/re-audit-final/` — `00_BINDING`, `01_REPAIR_REPLAY`,
  `02_SECURITY_AUTHORITY`, `03_REGRESSION`, `04_PACKAGE_IDENTITY`, `05_INSTALLED_PRODUCT`,
  `06_ADJACENT_RISK`, `07_FINAL_FINDINGS`, `FINAL_REAUDIT_STATUS`, `FINAL_REAUDIT_RESUME`,
  `FINAL_TECHNICAL_VERDICT`.
- Evidence: `docs/v1.6/re-audit-final/evidence/**` (bound runs, probe outputs, screenshots,
  hashes). Probes: `docs/v1.6/re-audit-final/probes/**` (attack batteries, stunts, seed).
- The staged package of this audit: `dist/package-r12/Kel-1.6.0-win-x64.exe`
  (gitignored build output; hashes in `04_PACKAGE_IDENTITY.md`).
- Audit run roots (retained): `C:\Users\Nick\KelFinalAuditRuns\{fresh,iso,r10}`.
- Audit install: removed by the uninstall battery (5-cycle matrix in `05_INSTALLED_PRODUCT.md`);
  B/C installs untouched.

## How the key runs were invoked (reproduction commands)

- Engine suite: `cd runtime && python -m pytest tests -q` (1019 + 10 subtests).
- Engine attacks: `cd runtime && python ../docs/v1.6/re-audit-final/probes/ra_attack_engine.py`
  and `ra_attack_engine2.py`.
- Negative control: scratch worktree at `a349009` + post-fix test files (see `03_REGRESSION.md`).
- Desktop: `cd desktop && npx vitest run`; `./node_modules/.bin/tsc.exe --noEmit -p tsconfig.json`.
- Package: engine `python -m PyInstaller KelEngine.spec --noconfirm`; stage to
  `desktop/dist/runtime/KelEngine` + `dist/runtime/KelEngine`; then
  `node scripts/build-with-builder.js auto --win`.
- Install/probe/stunts: `ux-audit/r12-install.ps1`, `ux-audit/r12-installed-probe.cjs`
  (env `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`),
  `probes/ra-stunt.cjs`, `ux-audit/r10-engine-loss-probe.cjs`.

## Explicit non-actions (stop boundary honored)

No repair of any finding; no Campaign E; `main` not moved; no tag; no freeze; no release;
no claim of human visual approval; production tree `05a076b` (and `7cf6030`) unchanged.

## Remaining work (human-only)

1. Nick: subjective `HUMAN_VISUAL_GATE` pass (screenshots in `evidence/ra-install-fresh/out`,
   `evidence/ra-isolation/out`, `evidence/ra-recovery/out`).
2. Nick: disposition of the 7 recorded findings (`07_FINAL_FINDINGS.md`) — none blocks release.
3. Release/freeze actions are NOT started and are explicitly out of scope here.
