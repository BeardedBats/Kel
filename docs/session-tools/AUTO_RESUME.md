# Session-scoped tool controls — AUTO_RESUME

## Where this workstream stands (2026-09-17, after the V1.6 P1 remediation)

- Engine: `runtime/kel/capabilities.py` (registry, availability, overrides, one-shot grants, strict
  explicit commands), route `/api/capabilities` in `service.py`, authorization layer **3c** in
  `authorize.py`, capability wiring in `coding.py`, inline commands in `acp_host.py`, and the real
  web effect gated in `research.py` before any external request.
- Desktop: `KelToolsControl` beside the model pill; bridge whitelist updated.
- Tests: `runtime/tests/test_capabilities.py` (25 passing, including the production-path research
  regressions); harness scenario `sessiontools` (updated for the removed-capability contract and the
  ordinary-talk no-mutation step).
- Artifacts: original workstream evidence on `dist/package-final11/win-unpacked`; P1 remediation
  evidence on `dist/package-p1cap/win-unpacked` (`ux-audit/run-p1-capabilities.sh`).

## If work resumes here

1. Worktree `C:\Users\Nick\Desktop\Kel\kel-ux-v15` (branch `ux/v15-journeys`).
2. Build: `powershell -File scripts/build-runtime.ps1`, then `desktop && bun run package`, then
   electron-builder with `--config.directories.output=<fresh dir>` (never while a scenario runs).
3. Verify: `runtime && python -m pytest tests -q`; packaged journey:
   `node packaging/ux-audit.cjs <appDir> <root> <out> sessiontools`.
4. Open docket for this surface: the transcript conflict card (Enable once / Enable for this chat /
   Keep disabled); connector-backed availability is out of V1.6 (Drive/Connected apps removed);
   i18n only if the control graduates out of the Kel-native English set.
5. Note: the V1.6 Phase 4 (i18n / donor-string cleanup) WIP lives in git stash
   `MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` — do not drop it; restore only when the
   program explicitly resumes Phase 4.
