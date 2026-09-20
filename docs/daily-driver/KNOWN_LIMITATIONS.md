# KNOWN LIMITATIONS — `dev/daily-driver`

Honest, current list (grows/shrinks as phases complete):

- External provider credentials (Anthropic/DeepSeek etc.) availability on this machine: probed in
  D1; where absent, provider flows are validated with fixtures and clearly marked as such.
- No public DNS / no external notification delivery / no mobile hardware: remote and notification
  work is validated locally (LAN/local browser) with explicit "external validation unavailable" notes.
- D0-002 installer metadata fix is source-level until the next fresh package build; packaged
  Properties re-check is scheduled in the package phase (PACKAGE_EVIDENCE checklist).
- HVRA-SUG-002: the audit's "two identical toasts" was a probe double-count artifact (the probe
  matched both `.arco-message` and its inner `.arco-message-content` for a single toast; the campaign
  harness saw a single message). The refusal toast was additionally made idempotent (stable message
  id) so duplicate emission is impossible; truthful OFF-state synchronization untouched.
- Full engine suite: verbose run in progress at D0 close; one failure seen in an earlier partial run
  must be identified and resolved (tracked in TEST_EVIDENCE.md) before the D19 regression.
- V1.6 release evidence and frozen tags intentionally not updated (historical record).
