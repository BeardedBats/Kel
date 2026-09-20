# DECISIONS — daily-driver marathon

- **D-001 — Lane.** New implementation lane `kel-daily-driver` / `dev/daily-driver`, based on
  `37b1f27` (newest verified corpus head; production tree equals `6d957ee9…`). Protected historical
  refs remain untouched; forward development only.
- **D-002 — Identity.** Development identity `1.7.0-dev` in `desktop/package.json` and
  `runtime/kel/__init__.py` (identity test pins both ends). No release tag; no publish.
- **D-003 — D0 placement.** The four final V1.6 residuals are repaired on the dev lane; audit IDs and
  commits recorded in `IMPLEMENTATION_STATUS.md`; no new audit campaign.
- **D-004 — Disk-first state.** `docs/daily-driver/` holds all durable marathon state;
  `MARATHON_STATE.md` is the canonical resume pointer.
- **D-005 — D0-001 approach.** Permissions joins `/api/state` jobs and shows the job's own request as
  the primary Work label (first line, ≤120 chars; fallback "Work item"); raw ids live only in a hover
  tooltip and an Advanced-only "Work references" table.
- **D-006 — D0-002 approach.** `desktop/package.json` `description` = `Kel` (builder derives the
  installer/uninstaller FileDescription from it); legal attribution untouched; packaged re-verify at
  package phase.
- **D-007 — D0-003 approach.** Donor ACP wiki link removed (not retargeted: no Kel help destination
  exists yet); unused i18n keys left in place to avoid generated-typing churn.
- **D-008 — D0-004 approach.** Duplicate-toast "finding" was a probe double-count artifact (Arco
  renders `.arco-message-content` inside `.arco-message`; the probe matched both). Behavior kept
  truthful; toast made idempotent with a stable message id.
- **D-009 — ENG-001 claims re-pin.** The v1.6 human-visual repair rewrote the permissions copy but the
  engine-side claim pin (`test_v141_claims`) was never updated, leaving the engine suite red since
  then (it had not been run on the repaired tree). The pin now follows the repaired shipped copy —
  same corrected claims, current wording.
- **D-010 — D1 approach.** Engine states are the truth; `providerStatus.ts` maps them to
  Available / Needs setup / Temporarily unavailable / Unavailable + reasons, and never upgrades a
  state. Per-card "Set up → Save + Verify" = OS-store write + engine credential metadata + read-back;
  it is not a live provider API call (no keys in this environment). The manual OS-store section is
  retained because `packaging/verify-credentials.cjs` drives it ("Store credential").
- **D-011 — D2 approach.** Kel ships with no update CDN: `updateFeed.buildCdnFeedOptions()` returns
  null and `autoUpdaterService` skips all electron-updater checks when no feed is configured (no
  donor infrastructure contact, no startup notification). The manual GitHub check
  (`BeardedBats/Kel`) remains the single source of truth and fails closed until Kel publishes release
  assets. Installer-based upgrades preserve user data by architecture; packaged upgrade verification
  is scheduled for the package phase. No cloud update service introduced.
- (append as work proceeds; every non-obvious choice gets a line)
