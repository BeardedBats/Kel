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
  route-blocked job waits and resumes by itself, so it deliberately does not interrupt. The orphaned
  journey is now live-verified end to end with a synthetic provider turn
  (`verify_synthetic_journeys.py` J3): a real child process is killed mid-run, recovery fences it
  (ORPHANED run, UNCERTAIN milestone, attempts unchanged, no replay), and the person's own
  continuation completes the same job. What a real-provider orphan would additionally exercise — a
  live model call inside the fenced attempt — stays unverified here because no provider credential
  exists on this machine.
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
- Activity (D14): the page is a composition of current state, so it refreshes on load/visit — it is a
  view, not a live feed (no streaming channel exists yet; D11's limitation applies). It lists at most
  the last five finished items and the first three continuation candidates — depth stays deliberately
  shallow; nothing else is hidden, the rest is one click away on Work.
- Emergency stop (D15): it stops at the next safe check rather than mid-write — a step that is already
  writing a file finishes that write before the stop lands (that is the engine's safe-check semantics,
  unchanged). Finished work is never undone by the stop, and resuming after a stop is a deliberate act
  (new work must be asked for again).
- Live revision (D16): widening always requires a user resolution — there is deliberately no
  "remember this forever" toggle in the free-form path (the engine supports a project-scoped grant,
  but the surface only asks per request). Evidence rounds the target to directories and the grant is
  a one-time use; a second identical action goes back through the request flow.
- Integrations overview (D17): it reports the engine's inventory; per-conversation overrides and
  "enable once" stay in the composer's tools pill, and actual setup happens on the Settings → Tools
  surface. Unavailable entries explain the engine's reason and offer no button — there is nothing to
  click when the machine genuinely cannot run something.
- Donor residual (D19): the Office-preview install link and the agent-hub contribution link (both
  pointing at the donor org's GitHub) were removed; the only tolerated occurrence of the donor org
  name in renderer source is one maintenance comment in `siderTooltip.ts` that records the upstream
  issue being tracked (pinned by `donor-org-references.test.ts`; the shipped bundle contains zero
  occurrences).
- Silent install (D19): NSIS update mode targets the *registered* install directory, not `/D` — the
  documented V1.6 heal behaviour. Fresh installs to a new path require clearing the app's
  registration keys first (`HKCU\Software\9280710d-…` + the Uninstall key); the incident and its
  repair are recorded in `PACKAGE_EVIDENCE.md`.
- Continuing an interrupted run (D19): the engine fences a run that died mid-flight and only an
  explicit person continuation re-arms it (`Store.reopen`, reached through
  `Continuation.execute_resume`). The fresh attempt is bounded by the same retry ceiling as any other
  (`attempts < 4`); when a fenced milestone has already spent its retries, the continuation is
  refused with the engine's own sentence instead of silently re-running. The person gets a *fresh*
  attempt, never a replay of the interrupted one — that attempt stays in the event log for review.
- Update-check wording (D19): with no published Kel release feed, the manual check shows the
  transport-level truth (`Update metadata request failed (404)`) rather than a friendly guess. Honest
  and fail-closed, but technical; a friendlier closed-channel sentence is a candidate for a later
  phase, not invented at the package gate.
- Provider ids (D19): the engine's inventory still carries the legacy id `internal` for the Anthropic
  API entry (`runtime/kel/providers.py`). Stored credential references and the engine's own identity
  for that provider are keyed by it, so renaming it is a migration-class change and was deliberately
  not attempted at the package gate. The user surfaces no longer show it — the Work route sentence,
  the provider save confirmation and the readiness choices all name the provider from the inventory
  label (`provider-language.test.ts` pins it). Any future surface must do the same: the raw id is not
  user copy.
