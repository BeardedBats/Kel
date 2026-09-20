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
- **D-005 — Update delivery.** (pending D2 — record chosen mechanism here)
- (append as work proceeds; every non-obvious choice gets a line)
