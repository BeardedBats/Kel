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
- Transcription (D4): the live provider (Muse, `api.meta.ai`) needs a Meta API key, which is not
  available in this environment — the credential-free "Practice mode" is the verified live path
  (deterministic text; the UI labels it honestly). Key set/clear flips the reported mode truthfully
  (`muse` ↔ `fixture`); the Muse transcription call itself is unverified here. UI-level click-through
  (microphone capture, OS file picker) is deferred to the packaged battery / D18 (no audio hardware
  in this environment); the policy pins + the live HTTP flow cover the shipped logic.
- V1.6 release evidence and frozen tags intentionally not updated (historical record).
- Remote surface (D3): enforcement is gateway-side because aioncore's local mode never gates its own
  business routes. Consequences: (1) pre-login, the SPA's boot probes (client settings/config/cron/
  realtime WS) are refused with 401 — expected noise until login; the login page renders with the
  default theme. (2) Session validity is cached 5s (positives), so a revoked cookie may pass for up
  to 5s unless the logout happened through the gateway (logout invalidates immediately). (3) The
  realtime WS bridge only connects after login; before that, reconnects are refused by the gate.
  (4) aioncore still binds loopback only; the desktop app's own local calls bypass the gateway by
  design (they are not browser traffic). (5) `POST /api/webui/reset-password` is now session-gated
  over the gateway; the desktop settings flow (direct local call) still works.
