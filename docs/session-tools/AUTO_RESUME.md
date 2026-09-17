# Session-scoped tool controls — AUTO_RESUME

## Where this workstream stands (2026-09-17)

- Engine: `runtime/kel/capabilities.py` (registry, availability, overrides, one-shot grants, natural
  language), route `/api/capabilities` in `service.py`, authorization layer **3c** in `authorize.py`,
  capability wiring in `coding.py`, inline directives in `acp_host.py`.
- Desktop: `KelToolsControl` beside the model pill; bridge whitelist updated.
- Tests: `runtime/tests/test_capabilities.py` (15 passing); harness scenario `sessiontools`.
- Artifact: `dist/package-final9/win-unpacked` (see `docs/basic-ux-sweep/15_FINAL_VERDICT.md`).

## If work resumes here

1. Worktree `C:\Users\Nick\Desktop\Kel\kel-ux-v15` (branch `ux/v15-journeys`).
2. Build: `powershell -File scripts/build-runtime.ps1`, then `desktop && bun run package`, then
   electron-builder with `--config.directories.output=<fresh dir>` (never while a scenario runs).
3. Verify: `runtime && python -m pytest tests -q`; packaged journey:
   `node packaging/ux-audit.cjs <appDir> <root> <out> sessiontools`.
4. Next increments (in order): the conflict card in the transcript (Enable once / Enable for this
   chat / Keep disabled) → connector-backed availability for Drive/Connected apps → i18n if the
   control graduates out of the Kel-native English set.
5. The workstream after this one, per the release docket, is the **memory proposal surface**
   (`docs/basic-ux-sweep/18_DONOR_FEATURE_REMEDIATION.md` §6).
