# 04 — PACKAGE EVIDENCE (Campaign C)

Bound to the post-repair release candidate. Production head: `05a076b`.

## R12 evidence-tool repairs (AUD-MINOR-004) — done 2026-09-19

- `ux-audit/r12-installed-probe.cjs` now evaluates `r12-assert-gate.cjs` before exit and fails
  non-zero on: healthyBoot, engineVersion!=1.6.0, attentionVisible, aboutLogoLoaded,
  consoleErrors, rawLeaks, overflow. `out.gate` is recorded in the run JSON.
  Discrimination against the real RC runs: `r12-fresh` → GATE FAIL exit 1;
  `r12-fresh2` → GATE PASS exit 0 (`evidence/mi4-gate-discrimination.txt`).
- `ux-audit/r12-release-integrity.sh` supports `--fail-on-dirty [repo] [outfile]` and exits 1
  on a dirty worktree or secret-scan hits. Re-run at repair head: `INTEGRITY: PASS dirty=0
  actionable_hits=0` (`evidence/mi4-integrity-repair-head.txt`; final re-run at the corpus tip:
  `evidence/final-integrity-at-rc-tip.txt`).
- Script hashes (pre/post) + change summary: `evidence/mi4-script-hashes.txt`.
- `19_R10_ENGINE_LOSS_EVIDENCE.md` wording corrected: unretained per-attempt timings are no
  longer asserted.

## Repaired package (fresh build, §17) — COMPLETE

- Build: `cd desktop && node scripts/build-with-builder.js auto --win` from the production head;
  v3 is the bound build (`evidence/final-package-build-log-v3.txt`). v1/v2 retained as lineage:
  v1 missed `resources/kel-engine` (staging path), v2 lacked the C-DISC-001 installer fix.
- Engine: PyInstaller 6.19.0 (`evidence/final-engine-build-log.txt`); staged (`desktop/dist/
  runtime/KelEngine`) == relocated (`dist/runtime/KelEngine`) == packaged
  `resources/kel-engine/KelEngine.exe`, sha256
  `f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8`.
- Installer `Kel-1.6.0-win-x64.exe` sha256
  `88a1b4761db5ba2ee6c507e7626e08e969cc5da004036efcbf5d42a87ff5124c`;
  `win-unpacked/Kel.exe` sha256
  `392d34b5068c898605976b538dd497a291535ae049e3c101dc5fe7792d5d5257`.
- aioncore provenance in package: `67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892`
  (`resources/bundled-aioncore/win32-x64/provenance.json`).
- Full artifact bindings: `evidence/final-package-artifacts.txt`.

## Installed battery (§18, `C:\Users\Nick\KelRepairInstall`) — COMPLETE

- [x] repaired-package build: exact command + full log retained (`final-package-build-log-v3.txt`)
- [x] installed battery: gated `r12-installed-probe.cjs` — fresh root **GATE PASS** (boot 1.6.0,
  attention visible, About logo loaded, 0 console errors / raw leaks); continuity root (RC-era
  store, schema max 21) **GATE PASS** with conversations preserved
  (`evidence/installed-probe-fresh/`, `installed-probe-upgrade/`)
- [x] installer registration: **EXIT=0** with `Uninstall Kel.exe`, ARP (`Kel · 1.6.0 ·
  /currentuser`), `Kel.lnk` in start menu + desktop — after the C-DISC-001 fix
- [x] reinstall over existing: EXIT=0, app + uninstaller intact
- [x] uninstall: exit 0; install dir + ARP + both shortcuts removed; data roots and
  `%APPDATA%\kel-*` retained (`evidence/installed-battery.txt`)
- [x] release-integrity re-run: PASS (see above)
- [x] C-DISC-001 (discovered + repaired): donor-hardcoded `AionUi.exe` aborted registration
  with E1010 pre-fix (`evidence/cdisc001-installer-e1010-prefix.txt`)
