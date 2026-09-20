# KNOWN LIMITATIONS — `dev/daily-driver`

Honest, current list (grows/shrinks as phases complete):

- External provider credentials (Anthropic/DeepSeek etc.) availability on this machine: probed in
  D1; where absent, provider flows are validated with fixtures and clearly marked as such.
- No public DNS / no external notification delivery / no mobile hardware: remote and notification
  work is validated locally (LAN/local browser) with explicit "external validation unavailable" notes.
- D0-002 installer metadata fix is source-level until the next fresh package build; packaged
  Properties re-check is scheduled in the package phase (PACKAGE_EVIDENCE checklist).
- HVRA-SUG-002: the duplicate pet-toast emission path was not fully isolatable from audit evidence
  alone (single toast call site is guarded; audit observed two identical messages). The repair makes
  the refusal toast idempotent at the UI layer so any duplicate emission renders once.
- V1.6 release evidence and frozen tags intentionally not updated (historical record).
