# PACKAGE EVIDENCE — daily-driver candidate

Historical V1.6 candidate evidence lives in `docs/v1.6/…` and is untouched (not overwritten).

## Bind chain to record for the daily-driver candidate

source HEAD → renderer build → engine build → installer → installed candidate

## Checklist (to verify at package phase)

- [ ] Source HEAD recorded + clean renderer output (no stale package cache; no donor builder config).
- [ ] Engine built from this lane's `runtime/` and bound into the package (`kel-engine`).
- [ ] `desktop/package.json` version = `1.7.0-dev`; artifact name reflects it honestly.
- [ ] Installer metadata re-verified: **FileDescription = Kel** (no donor phrase) — **D0-002 deferred check**.
- [ ] Uninstaller metadata re-verified (same).
- [ ] No donor strings in built output (donor sweep artifact recorded).
- [ ] Install dir: `C:\Users\Nick\KelDailyDriverCandidate`; data root: `C:\Users\Nick\KelDailyDriverRuns\prepared`.
- [ ] Preserved installs untouched (`KelV16ReviewInstall`, `KelVisualFixInstall`, `KelVisualReauditInstall`).

## Records

| Phase | Artifact | SHA-256 | Notes |
| --- | --- | --- | --- |
| — | (not built yet) | — | — |
