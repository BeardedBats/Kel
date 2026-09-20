# KNOWN LIMITATIONS — `dev/daily-driver`

Honest, current list (grows/shrinks as phases complete):

- External provider credentials: none are available for live validation in this environment. D1's
  "Save + Verify" verifies the OS-store write roundtrip + engine credential metadata, not a live
  provider API call; that gap is recorded in PACKAGE_EVIDENCE for the packaged phase.
- No public DNS / no external notification delivery / no mobile hardware: remote and notification
  work will be validated locally (LAN/local browser) with explicit "external validation unavailable"
  notes.
- D0-002 installer metadata fix is source-level until the next fresh package build; packaged
  Properties re-check is scheduled in the package phase (PACKAGE_EVIDENCE checklist).
- HVRA-SUG-002: the audit's "two identical toasts" was a probe double-count artifact (the probe
  matched both `.arco-message` and its inner `.arco-message-content` for a single toast; the campaign
  harness saw a single message). The refusal toast is additionally idempotent (stable message id);
  truthful OFF-state synchronization untouched.
- Update channel: Kel ships with no update CDN (donor feed disabled in D2). The manual check targets
  `BeardedBats/Kel` and fails closed until Kel publishes release assets; until then the update check
  reports a closed-channel failure rather than pretending. Installer-based upgrades preserve user
  data by architecture (data root lives outside the install dir; engine migrations run on open) —
  packaged verification is scheduled in the package phase.
- Internal donor remnants retained deliberately (non-user-visible): license headers, internal NSIS
  symbols, and `HTTP-Referer: https://aionui.com` on two provider API client paths. Recorded for
  future cleanup decisions; not part of the user surface.
- V1.6 release evidence and frozen tags intentionally not updated (historical record).
