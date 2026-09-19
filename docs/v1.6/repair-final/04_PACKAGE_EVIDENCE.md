# 04 — PACKAGE EVIDENCE (Campaign C)

Bound to the post-repair release candidate. Populated at §17/18 (fresh build + installed
battery); this file must name: git SHA, Vite/renderer build, engine build/hash, staged engine,
packaged engine, installer hash.

## R12 evidence-tool repairs (AUD-MINOR-004) — done 2026-09-19

- `ux-audit/r12-installed-probe.cjs` now evaluates `r12-assert-gate.cjs` before exit and fails
  non-zero on: healthyBoot, engineVersion!=1.6.0, attentionVisible, aboutLogoLoaded,
  consoleErrors, rawLeaks, overflow. `out.gate` is recorded in the run JSON.
  Discrimination against the real RC runs: `r12-fresh` → GATE FAIL exit 1;
  `r12-fresh2` → GATE PASS exit 0 (`evidence/mi4-gate-discrimination.txt`).
- `ux-audit/r12-release-integrity.sh` supports `--fail-on-dirty [repo] [outfile]` and exits 1
  on a dirty worktree or secret-scan hits. Re-run at repair head `960e023`:
  `INTEGRITY: PASS dirty=0 actionable_hits=0` (`evidence/mi4-integrity-repair-head.txt`;
  full out file `ux-audit/runs/r12-integrity-repair-c.txt`).
- Script hashes (pre/post) + change summary: `evidence/mi4-script-hashes.txt`.
- `19_R10_ENGINE_LOSS_EVIDENCE.md` wording corrected: unretained per-attempt timings are no
  longer asserted.

## Executions completed at §17/18 (this file updated as they land)

- [ ] repaired-package build: exact command + full log retained under `evidence/`
- [ ] installed battery: `r12-installed-probe.cjs` run through the gate on the repaired install
- [ ] uninstall: run logged + retained
- [ ] `r12-release-integrity.sh --fail-on-dirty` re-run at `POST_REPAIR_V1_6_HEAD`
