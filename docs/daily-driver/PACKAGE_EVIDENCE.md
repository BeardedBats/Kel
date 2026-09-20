# PACKAGE EVIDENCE — daily-driver candidate

Historical V1.6 candidate evidence lives in `docs/v1.6/…` and is untouched (not overwritten).

## Bind chain to record for the daily-driver candidate

source HEAD → renderer build → engine build → installer → installed candidate

## Checklist (to verify at package phase)

- [ ] Source HEAD recorded + clean renderer output (no stale package cache; no donor builder config).
- [ ] Engine built from this lane's `runtime/` and bound into the package (`kel-engine`).
- [ ] `desktop/package.json` version = `1.7.0-dev`; artifact name reflects it honestly.
- [ ] Installer metadata re-verified: **FileDescription = Kel** (no donor phrase) — **D0-002 check**.
- [ ] Uninstaller metadata re-verified (same).
- [ ] No donor strings in built output (donor sweep artifact recorded).
- [ ] Installed probe: Permissions Work column shows the work's request (no raw `job_*` ids in the
      primary text; raw ids only behind Advanced) — **D0-001 live replay**.
- [ ] Installed probe: Desktop-Pet enable refusal shows exactly ONE toast (count `.arco-message`
      nodes only — the old probe double-counted `.arco-message-content`) — **D0-004 live replay**.
- [ ] Installed sweep: no donor wiki/help destination reachable (ACP setup link gone) — **D0-003**.
- [ ] Installed probe: Providers page shows human statuses; "Set up → Save + Verify" stores a fixture
      key in the OS store and flips the provider state truthfully — **D1 replay**.
- [ ] Update check fails closed truthfully (no feed; Kel repo has no releases); About shows a closed
      channel rather than a fake "up to date" — **D2 replay**.
- [ ] Upgrade preservation: install the candidate over a disposable prior install; assert
      conversations/projects/settings/credential metadata preserved — **D2/Journey-7**.
- [ ] Install dir: `C:\Users\Nick\KelDailyDriverCandidate`; data root: `C:\Users\Nick\KelDailyDriverRuns\prepared`.
- [ ] Preserved installs untouched (`KelV16ReviewInstall`, `KelVisualFixInstall`, `KelVisualReauditInstall`).

## Records

| Phase | Artifact | SHA-256 | Notes |
| --- | --- | --- | --- |
| — | (not built yet) | — | — |
