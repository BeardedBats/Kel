# DECISIONS — daily-driver marathon

- **D-001 — Lane.** New implementation lane `kel-daily-driver` / `dev/daily-driver`, based on
  `37b1f27` (the newest verified corpus head whose production tree equals `6d957ee9…`). Protected
  historical refs remain untouched; this is forward development only.
- **D-002 — Identity.** Development identity `1.7.0-dev` applied to `desktop/package.json` and
  `runtime/kel/__init__.py` (the identity test pins both ends together). No release tag, no publish;
  all V1.6 release evidence remains as-is.
- **D-003 — D0 placement.** The four final V1.6 residuals are repaired on the dev lane as forward
  development; source audit IDs are recorded; no new audit campaign is created.
- **D-004 — Disk-first state.** `docs/daily-driver/` holds all durable marathon state;
  `MARATHON_STATE.md` is the canonical resume pointer. Chat history is never relied upon.
- **D-005 — D0-001 approach.** The Permissions page joins `/api/state` jobs (same engine) and shows
  the job's own request as the primary Work label (first line, bounded 120 chars). Unresolvable jobs
  fall back to the neutral label "Work item" — the raw engine id is never primary; it stays in a
  hover tooltip and in an Advanced-only "Work references" table.
- **D-006 — D0-002 approach.** `desktop/package.json` `description` set to `Kel` (the builder derives
  the installer/uninstaller FileDescription from it). No other version-resource strings carry donor
  naming; legal attribution files untouched; packaged re-verification scheduled for the package phase.
- **D-007 — D0-003 approach.** The donor ACP wiki link is removed entirely (not retargeted): no Kel
  help destination exists yet, and the repo home is not a setup guide. The i18n keys remain in
  locale files (unused) to avoid churn in generated i18n typings.
- **D-008 — D0-004 approach.** The audit's duplicate toast was a probe double-count artifact
  (`.arco-message, .arco-message-content` both match one toast; Arco Notice renders both; campaign
  harness saw a single message). Behavior kept truthful; the refusal toast is additionally made
  idempotent with a stable message id so any duplicate emission collapses to one toast.
- (append as work proceeds; every non-obvious choice gets a line)
