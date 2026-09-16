# V1.5 UX remediation-evidence (batch 1)

Provenance: 2026-09-16, branch `ux/v15-journeys` (worktree `kel-ux-v15`), produced by the user-journey audit
of the frozen release `Kel-V1.5-Frozen` (`v1.5.0` / `5e76b21`) and its fixes.

- `baseline/` — harness output against the **frozen** packaged app: fresh first-run (skip path), seeded
  `tour`, `settings`, `palette`, `keyboard`, `readability`, `sider`, `maintext`, `compose` runs
  (compose runs captured the no-usable-provider failure path), plus human-readable dumps.
- `fixed/` — the same harness against the rebuilt packaged app from this branch
  (`kel-ux-v15/dist/package/win-unpacked`): `first-run`, `tour`, `settings`, `palette`, `sider`,
  `readability`, `maintext`, plus `verify-summary*.txt` (extraction of the pass/fail facts) and two
  screenshots (landing + chat notice).

Harness: `packaging/ux-audit.cjs` (scenarios: `first-run | tour | settings | palette | keyboard | readability | sider | maintext | compose`).
Launch pattern matches the V1.5 acceptance probes: packaged `Kel.exe`, isolated root (`APPDATA` + `KEL_DATA_DIR`),
window offscreen, per-run JSON + screenshots. The frozen release was never modified.

**Verified in `fixed/`:** onboarding → `#/guid` with composer; plain-language onboarding steps; provider-unavailable
notice on the chat landing; Work-page human counts/titles; primary sider `New Chat / Work / Projects / Permissions`;
plain palette copy; single "Refresh map"; Permissions title; zero AA offenders on providers/projects/work/settings-appearance.

**Recorded failures/incompleteness in `fixed/` (by design — see the history ledger):** the `settings` run captures
the reverted sider-expansion crash (`TypeError … reading 'id'`, empty sider list — O8); the sider dump shows the raw
i18n key `conversation.workspace.unnamedSpace` (O9); `readability` still lists one 13 px "Kel" at 2.72:1 (O10).
