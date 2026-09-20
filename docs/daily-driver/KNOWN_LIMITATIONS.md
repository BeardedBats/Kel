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
- Attention + notifications (D5): notifications fire while Kel is running (the driver polls the
  authoritative reads in the shell). A fully quit Kel cannot notify — there is no background service,
  and none is proposed. Snooze/Later is intentionally absent (it would grow a second state store
  beyond the derived-only surface). Update/restart attention items are omitted until an authoritative
  renderer-visible flag exists (update channel closed in D2). The connection item covers engine
  provider setup needs; the Providers page remains the deeper surface.
- Continuation (D6): the landing brief is a point-in-time snapshot (fetched on mount), not a live
  subscription — it reflects durable state at open time; the Work page and conversations update
  normally. There is deliberately no "since you were last here" diff: Kel persists no client-side
  last-seen marker, and the brief reports durable truth rather than inventing recency. Resuming
  remains human-gated: the engine never auto-resumes; the chat reply "continue" (and the Work page)
  is the mechanism, and the brief only points at it.
- Long-running autonomy (D7): the engine never auto-replays an unconfirmed/orphaned run — that is
  deliberate (reconcile first) and now surfaces as needs-you with the engine's reason; a
  route-blocked job waits and resumes by itself, so it deliberately does not interrupt. Live
  verification of an orphaned run in this environment is limited to the engine unit pins
  (`test_v16_r6_liveness`, `test_v16_r3_retry_durability`) plus the desktop-side derivation tests:
  creating a genuinely mid-flight job here would require a live provider credential, which this
  environment does not have.
- Adaptive staffing (D8): tier selection, hard rules and ceilings remain engine-internal — by design;
  normal surfaces speak in plain sentences (`staffingLanguage.ts`). Kel manages its own roster
  (shipped roles seed on first use; `Team.resolve_role`), and roster/studio management, internals
  columns, and the explicit seed action live behind the Team page's "Developer view" toggle. That
  toggle is per-session and not persisted — a deliberate choice (internals disclosure is an explicit
  act, not a stored preference). The tier ladder is not user-configurable and has no user-facing knob
  by design.
- Learning promotion (D9): the engine's pipeline (queue → accept/defer/reject, trust-model
  application, superseded history) is complete; the Knowledge surface shows at most 5 waiting
  suggestions at once (a "N more waiting" line points at the rest) and lives in the projects
  workspace, not a global inbox. Rejected suggestions deliberately do not re-ask until their
  evidence changes (engine behaviour, pinned). Proposals are produced by the engine's own loops
  (vetting/repo-state/corrections) — there is no manual "create proposal" UI, and none is planned.
- Recipes (D10): runs compile into normal jobs (the durable submission queue drains one at a time);
  without a provider credential a submitted run sits READY/WAITING_RESOURCE here — the loop itself is
  verified, provider execution is not. Run sends no inputs from the UI yet: recipes that declare
  required inputs surface the engine's own "needs input" refusal as a plain note rather than a form
  (an input form is a candidate for a later phase, not invented now).
- Cross-device (D11): the remote browser reaches Kel's engine through the desktop web-host's
  session-gated `/kel` gateway, so the engine must be running on the same machine as the web-host
  (the desktop app, or `bun run webui` with `KEL_DATA_DIR` pointed at a running engine). Live Kel
  updates do not stream over the gateway yet — pages show state as of load/refresh (aioncore's own
  `/ws` is untouched); a Kel streaming channel is deliberately not invented in this phase.
- Routing transparency (D12): the Work page shows the route for up to three skipped providers (the
  rest stay available to the engine and in the API payload). "Cost where known" stays literal —
  when cost is unknown the sentence says so instead of guessing. The route map covers active jobs;
  once a job is terminal its route leaves `/api/state`. Provider failover ordering itself is the
  engine's (D7 territory); this surface is informational and offers no manual override beyond the
  existing provider-choice setting.
- Remote failure language (D13): the D13 layer covers what the *gateway* reports. Failures that
  happen before the page's own origin answers (a dead web-host, a wrong address, TLS problems) are
  the browser's own error page and cannot be restyled by Kel — the device-level sentence covers the
  reachable-page case only. Unknown gateway codes deliberately fall back to the engine's own message
  rather than a guessed translation.
