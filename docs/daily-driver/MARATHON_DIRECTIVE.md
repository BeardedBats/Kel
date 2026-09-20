# MARATHON_DIRECTIVE — Kel Daily Driver Expansion Program (D3–D19, package, install)

**Authority:** this file is the complete governing implementation program for the Daily Driver
marathon. It was transcribed verbatim-in-intent from the owner's marathon directive; scope was not
altered. Where the repository or durable state contradicts a line here, **the repository and durable
state win** — record the difference in `DECISIONS.md` / `MARATHON_STATE.md` and continue.

**Restore protocol (fresh context):** read, in order,
1. `docs/daily-driver/MARATHON_DIRECTIVE.md` (this file)
2. `docs/daily-driver/MARATHON_STATE.md`
3. `docs/daily-driver/RESUME.md`

Nothing else is required to resume; every other record under `docs/daily-driver/` is supporting
evidence (`FEATURE_LEDGER.md`, `TEST_EVIDENCE.md`, `IMPLEMENTATION_STATUS.md`, `DECISIONS.md`,
`PACKAGE_EVIDENCE.md`, `KNOWN_LIMITATIONS.md`, `DOGFOOD_JOURNEYS.md`, `ROADMAP.md`).

---

## PRODUCT NORTH STAR

**ONE CAPABLE ASSISTANT WITH HIDDEN ORCHESTRATION.**

Kel is one assistant a person talks to. Every internal orchestration mechanism — staffing,
delegation, leases, epochs, routing, queues, runtimes — stays behind that surface. The user sees
plain language, real actions, and truthful state; never machinery vocabulary.

Development identity: **`1.7.0-dev`**. Lane: branch `dev/daily-driver`, worktree
`C:\Users\Nick\Desktop\Kel\kel-daily-driver`.

---

## EXECUTION RULE

Continue the program phase by phase:

D3 → D4 → D5 → D6 → D7 → D8 → D9 → D10 → D11 → D12 → D13 → D14 → D15 → D16 → D17 → D18 → D19 →
fresh package → installed Daily Driver candidate.

Do NOT return at intermediate checkpoints merely because work advanced. Do NOT stop after: D3,
remote working, transcription working, Needs-Your-Attention working, adaptive staffing, Recipes, one
package, one clean commit, one green suite, a provider limitation, or an unavailable external
credential. Every clean checkpoint launches the next phase.

Do NOT restart the program and do NOT reconstruct it from chat history — resume from durable state.

Do NOT create an audit campaign. Do NOT publish, tag a release, freeze, or rewrite history.

Protected refs (never modify): `main`, `repair/v16-human-visual`, `repair/v16-final`,
`audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`,
`ux/v15-journeys`, and tags `v1.2.0`…`v1.6.0-pre1`.

**Per-phase loop:** understand → narrow design → implement → self-review → test → realistic journey
→ record on disk → commit → continue.

**Durable state is the memory.** Update `docs/daily-driver/MARATHON_STATE.md` and `RESUME.md` at
every checkpoint. Disk is durable state; chat history is not. Before any turn ends unexpectedly:
make the worktree clean where safe, commit completed coherent work, update `MARATHON_STATE.md` and
`RESUME.md` with the exact next item.

---

## D3 — REMOTE / WEBUI

Turn the current Remote/WebUI implementation into a genuinely usable remote Kel surface.

Audit the existing architecture first.

Implement/harden:

- explicit enable/disable
- authentication
- login/session handling
- clear local URL
- LAN access
- truthful security state
- reconnect
- responsive phone/tablet/desktop layouts
- conversation viewing
- sending prompts
- continuing conversations
- Needs Your Attention
- approval/deny
- boundary-access decisions
- completed-work inspection
- work-status inspection

Do not expose runtime plumbing unnecessarily. Do not silently enable remote access. Remote remains
opt-in.

Security review must cover: bind interface, auth/session lifecycle, origin handling, state-changing
requests, secret logging, and basic abuse/throttling where justified.

Use the existing auth/capability architecture. No enterprise IAM.

Run real browser/responsive tests. Record and commit. Then immediately D4.

**Status: DONE (core)** — see Appendix B and `MARATHON_STATE.md` for commits/evidence.

---

## D4 — TRANSCRIPTION

Finish Transcription as a first-class Kel workflow.

Required:

- Record
- Upload Audio
- drag/drop
- folders
- recent transcripts
- transcript detail
- rename
- Copy Transcript
- Download Transcript
- Download Audio
- combine where supported
- API key/setup
- progress
- cancel
- failure/retry

Preserve: **NO spacebar start/stop shortcut.**

Integrate transcripts with Kel where existing architecture supports it: send to conversation,
attach/use in Project, use as context, search recent transcripts.

Do not create a second document database.

Test realistic fixture flow. Commit and continue.

**Status: DONE (core)** — see Appendix B.

---

## D5 — NEEDS YOUR ATTENTION + NOTIFICATIONS

Make Needs Your Attention the canonical human-interruption surface. Derived from authoritative state
only.

Include relevant: approval, file/folder permission, blocking question, provider setup, failed work
requiring choice, uncertain result, completed result requiring review, update/restart requirement.

Improve: project grouping, priority, age, reason, direct action, open conversation, automatic removal
when resolved.

Add Snooze/Later only if semantically safe. No second workflow state.

Add restrained desktop notifications for meaningful events: work finished, approval/access needed,
task failed, provider intervention, transcription finished, genuine stall.

Never notify for internal worker chatter.

Commit and continue.

**Status: DONE (core)** — see Appendix B.

---

## D6 — CONTINUATION / RESUMABILITY

Make reopening Kel feel effortless.

Generate concise resumption briefs from durable truth:

- what completed
- what remains active
- what stopped
- what needs Nick
- what can resume
- provider blockers
- permission blockers

Provide real actions where authoritative paths exist: Resume, Retry, Continue, Review, Approve,
Change provider, Open result, Open conversation.

No fake buttons. No UI-only state.

Test restart/resume. Commit and continue.

---

## D7 — LONG-RUNNING AUTONOMY

Improve pursuit of durable goals. Use the existing execution architecture.

Strengthen: durable objective, current step, checkpoint continuation, retry/recovery, provider
interruption recovery, engine restart recovery, unresolved-effect reconciliation, completion
criteria, human gate classification.

A step completing is not the goal completing. A clean commit is not automatically completion. A
provider turn ending is not completion.

Where Kel already has authority and failure is recoverable, continue automatically. Where Nick is
genuinely required, surface through Needs Your Attention.

No blind infinite retries. No second supervisor.

Commit and continue.

---

## D8 — ADAPTIVE STAFFING

Activate safe automatic staffing with the existing workforce architecture.

Use the smallest sufficient tier: D0 Kel alone · D1 Kel + specialist · D2 builder/reviewer pod ·
D3 parallel mission teams · D4 exceptional/high-assurance only.

Decision inputs may include: complexity, independent workstreams, risk, reversibility, need for
independent verification, expected duration, artifact count, security/data sensitivity.

Preserve: Commander = Kel, never spawned; Architect retained when needed; builder cannot
final-certify; independent verifier; Sentinel where warranted; Oracle read-only/fresh where useful;
Red Team only for high-assurance cases; budget/authority ceilings.

No recursive spawning. No normal-user roster management.

Normal UI should say things like "Kel is using an independent review." — not workforce internals.

Test D0/D1/D2/D3 selection and boundaries. Commit and continue.

---

## D9 — CONTROLLED LEARNING PROMOTION

Promote only high-confidence, low-risk learning into live behavior.

Potential safe classes: response/work style, provider performance by task family, recurring workflow
choice, autonomy preference, review-depth preference, successful Recipe choice, preferred output
destination.

Never silently learn: security permissions, unrestricted filesystem authority, spending authority,
irreversible effects, sensitive personal assumptions.

Preserve: provenance, confidence, correction, supersession, retraction, conflicts, project scope,
user-confirmation rules.

Use the existing memory/learning system. No second memory layer.

Test promotion + correction + retraction. Commit and continue.

---

## D10 — RECIPES

Make reusable workflows practical.

Support where current architecture permits: create, name, description, steps, required capabilities,
model preference, completion condition, retry policy, save, edit, duplicate, run, attach to Project.

Recipes remain declarative. Compile into the existing execution/completion system. No second
workflow runtime.

Allow suggestions such as "You do this often. Save it as a Recipe?" only with enough evidence. Do
not auto-create after one occurrence.

Persist and run a Recipe repeatedly in tests. Commit and continue.

---

## D11 — CROSS-DEVICE CONTINUITY

Build on Remote + durable state.

Desktop → remote browser/mobile-width → desktop must preserve: conversation, Project context,
pending attention, approvals, active work, results.

Avoid device-local divergence. Test realistic round-trip state. Commit and continue.

---

## D12 — SMARTER PROVIDER ROUTING

Improve Automatic routing using the existing Model Router.

Consider: task family, coding vs general reasoning, tool requirements, context size, reliability,
provider health, configured availability, latency, cost where known, independent-review
requirements.

Do not invent fake numerical precision.

Respect: FIXED → no silent fallback; PREFERRED → fallback where safe; AUTO → choose appropriately.

A fallback must not remove required tools/capabilities.

Test provider outage/fallback behavior. Commit and continue.

---

## D13 — FAILURE RECOVERY POLISH

Improve end-to-end recovery for: provider failure, CLI crash, engine restart, network interruption,
remote disconnect, transcription failure, long-running stall, verifier failure, package/update
failure.

Use existing: retry, reconciliation, preserved work, resumability, Needs Your Attention.

No raw infrastructure language in normal UX. Commit and continue.

---

## D14 — OPTIONAL ADVANCED ACTIVITY

Implement an optional high-level power-user Activity surface only if it fits the current architecture
cleanly.

May show: active goals, work in progress, completed work, waiting work, current model/provider,
review status, recovery state, evidence availability.

Do NOT expose ordinary users to: leases, epochs, internal worker IDs, routing packets, database
rows — unless under an additional developer/debug disclosure.

Do not turn Kel into an agent cockpit. Commit and continue.

---

## D15 — EXECUTION / SECURITY BOUNDARY IMPROVEMENTS

Improve existing containment pragmatically: filesystem scope, provider credential isolation,
subprocess environment, effect boundaries, network-use visibility, destructive-command
classification, confirmations.

Make network capability more explicit internally. A task must not silently gain network authority
merely because its execution mechanism can reach the internet.

Use existing authorization/capability semantics. Do NOT build a bespoke hypervisor/firewall
platform. Do NOT derail the marathon into speculative sandbox infrastructure.

Commit and continue.

---

## D16 — LIVE CAPABILITY REVISION

Implement stronger live authority behavior.

Invariant: **running work may NEVER silently gain authority because configuration changes.**
User revocation MAY narrow active work immediately.

Test live revocation of: web, files, terminal, GitHub, Project access, conversation capability.

Active work should become narrowed, blocked, or reconciled. Never silently widened.

Use the existing authorization system. Commit and continue.

---

## D17 — INTEGRATION / PLUGIN DEVELOPER SURFACE

Create a narrow internal developer contract using the current plugin/tool/MCP architecture.

Support future integrations such as: Gmail, Drive, GitHub, Slack, ClickUp, Figma, Pitcher List
tools.

Define enough for: registration/manifest, capability declaration, credential reference, tool schema,
authority requirement, evidence/result contract, configuration, versioning.

Do NOT build a marketplace. Do NOT build a speculative universal ABI.

Normal UX should show: Connected, Needs setup, Unavailable, Reconnect, Remove — not
transport/runtime internals.

Commit and continue.

---

## D18 — SYNTHETIC DAILY-DRIVER DOGFOOD

Run realistic end-to-end journeys. At minimum:

1. normal conversation
2. coding task
3. long-running autonomous goal
4. transcription
5. remote interaction
6. provider outage/fallback
7. update/upgrade
8. Recipe create/run/re-run
9. learning promotion/correction
10. desktop → remote → desktop continuity

Fix objective friction/defects discovered. Do not invent Nick's subjective preferences. Record all
journeys. Commit and continue.

---

## D19 — FULL REGRESSION

Run the complete implementation validation:

- ENGINE: full suite
- DESKTOP: TypeScript + full Vitest
- REMOTE: browser/responsive/auth flows
- TRANSCRIPTION: fixture E2E
- RECIPES: persisted repeated run
- LEARNING: promotion/correction/retraction
- ADAPTIVE STAFFING: D0/D1/D2/D3 + budgets + authority
- CONTINUATION: restart during active work
- CAPABILITIES: live revocation
- PROVIDERS: honest disposition
- UPGRADE: disposable installed upgrade preserving durable state

Investigate every unexplained regression.

---

## PACKAGE + INSTALL

After D19 is green: build a fresh Daily Driver package.

Use clean: renderer output, engine, package cache/config. No donor builder configuration. Use honest
development identity.

Bind the chain: source HEAD → renderer → engine → package → installer.

Install separately at: `C:\Users\Nick\KelDailyDriverCandidate`

Use data root: `C:\Users\Nick\KelDailyDriverRuns\prepared`

Do not overwrite preserved V1.6/audit installations.

Prepare realistic data: Projects, conversations, transcript, Recipe, pending approval, attention
item, provider setup state, resumable work fixture.

Validate the installed app.

---

## FINAL INSTALLED BATTERY

Exercise: startup, conversations, Projects, provider setup, Automatic routing, Tools, Permissions,
Needs Your Attention, Work, Remote/WebUI, Transcription, Recipes, continuation, notifications,
Activity if implemented, Settings, About, upgrade, reinstall/uninstall behavior.

Check: zero unexplained raw errors; no broken routes; no obvious state lies; no donor-brand
regression; no dead controls; no obvious overflow; durable state preserved.

---

## PERFORMANCE / FRICTION

Measure obvious latency where practical: startup, conversation open, Project switch, Settings open,
provider refresh, Needs Your Attention, Remote load, transcript list, Recipe list.

Fix only pathological problems. Do not waste time on microscopic optimization.

---

## DURABLE RECORD

Continuously update: `MARATHON_STATE.md`, `RESUME.md`, `IMPLEMENTATION_STATUS.md`,
`FEATURE_LEDGER.md`, `DECISIONS.md`, `TEST_EVIDENCE.md`, `PACKAGE_EVIDENCE.md`,
`KNOWN_LIMITATIONS.md`, `DOGFOOD_JOURNEYS.md`.

At completion create/finalize `docs/daily-driver/DAILY_DRIVER_CANDIDATE.md` and establish
`DAILY_DRIVER_CANDIDATE_HEAD=<exact sha>`.

---

## SELF-REVIEW / TESTING REQUIREMENTS (all phases)

- Internal self-review per phase; no separate audit campaign.
- Focused tests after every feature cluster; full desktop Vitest + tsc before each commit;
  engine suite when engine code changes.
- Realistic journeys over synthetic ones; fixture/manual validation where external services are
  unavailable, with the limitation recorded honestly.
- Evidence on disk: command, result, and artifact paths in `TEST_EVIDENCE.md`; machine-readable
  JSON + screenshots under `docs/daily-driver/evidence/<phase>/` where a real stack is exercised.
- No fabricated verification; failing checks are reported, not hidden.

---

## OUT OF SCOPE

Still DO NOT build:

- Profiles
- giant workforce dashboard
- normal-user roster management
- unlimited nested spawning
- second memory system
- second workflow engine
- second authorization system
- second task database
- enterprise RBAC
- giant vector DB
- knowledge graph
- Rust migration
- public A2A
- speculative architecture rewrites

---

## RETURN / END-STATE RULES

Do NOT return at another clean implementation checkpoint merely because execution advanced
substantially.

If the execution environment genuinely ends the turn, first:

- make the worktree clean where safe
- commit completed coherent work
- update `MARATHON_STATE.md`
- update `RESUME.md`
- write the exact next item

Otherwise continue.

Return only at:

A. Daily Driver Candidate ready, or
B. genuine execution-capacity termination with durable exact continuation, or
C. genuine owner-only/destructive gate blocking the remaining program.

Preferred endpoint:

```
# KEL — DAILY DRIVER EXPANSION MARATHON COMPLETE
## DAILY DRIVER CANDIDATE READY
```

---

## FINAL RESPONSE FORMAT

When the candidate is ready, the final response states, in this order:

1. `# KEL — DAILY DRIVER EXPANSION MARATHON COMPLETE` / `## DAILY DRIVER CANDIDATE READY`
2. `DAILY_DRIVER_CANDIDATE_HEAD=<exact sha>`
3. The package artifact + SHA-256 and the install path (`C:\Users\Nick\KelDailyDriverCandidate`).
4. The data root used (`C:\Users\Nick\KelDailyDriverRuns\prepared`).
5. Verification summary: engine suite, desktop tsc + Vitest, real-stack remote/browser matrix,
   transcription fixture E2E, installed battery results.
6. Honest remaining limitations (external credentials, services unavailable in this environment).
7. The single next action for Nick (launch the installed app).

For any non-final checkpoint: state the phase just completed, its commit, the evidence path, the
current phase and its exact next action, and continue.

---

## APPENDIX A — REPOSITORY-VERIFIED ENVIRONMENT TRUTHS

These are facts established against the repository during the marathon (they govern implementation;
they do not change scope):

- The desktop app runs **two backends**: the donor `aioncore` binary (the UI/conversation backend;
  bundled at `resources/bundled-aioncore/<plat-arch>/`) and the **Kel engine** (Python,
  `runtime/kel`, reached only by the Electron main process through a per-process bearer token in
  `desktop-session.json`). The web-host proxies to **aioncore** (`globalThis.__backendPort`), not to
  the Kel engine.
- aioncore owns the browser auth surface (`/login`, `/logout`, `/qr-login`, `/api/auth/*`,
  `/api/webui/*`) and runs in local mode: it does **not** gate business routes. Network enforcement
  therefore lives in the **web-host gateway** (D3): session validated against `/api/auth/user`,
  anonymous allowlist only for `/login`, `/logout`, `/qr-login`, `/api/auth/*`.
- The Kel engine's HTTP surface requires `Authorization: Bearer <token>` + `Host`/`Origin` checks and
  binds `127.0.0.1` only; the engine writes `desktop-session.json` (url + token + pid +
  engine_version) into its data root.
- Transcription: engine family `/api/transcription`; credential-free **Practice mode**
  (`FixtureProvider`) is the no-key default and is labelled honestly in UI
  (`status.mode === 'fixture'`); live Muse transcription needs a Meta API key (`api.meta.ai`).
- Provider statuses come from the providers action family (`action: 'list'`); engine states include
  `not_installed`, `installed_not_authenticated`, `healthy`, `quota`, `quota_not_reported`,
  `degraded`, `unavailable`. `not_installed` / `installed_not_authenticated` are the "Needs setup"
  states (used by the D5 `connection` attention kind).
- Notifications: the renderer detects; the Electron main process decides (skips when the window is
  focused, respects `system.notificationEnabled`). D5 reuses `ipcBridge.notification.show`.
- No provider credentials, no public DNS, no mobile hardware in this environment: validate against
  real local stacks (engine + aioncore + built renderer) and record "external validation
  unavailable" honestly. The shipped aioncore can be taken from a preserved install
  (`KelVisualFixInstall/resources/bundled-aioncore`).

## APPENDIX B — PROGRAM STATUS AT TRANSCRIPTION TIME

- Completed and verified: **D0, ENG-001, D1, D2, D3, D4, D5** (commits in `MARATHON_STATE.md`).
- Current phase: **D6 — Continuation / resumability**.
- Remaining queue: D6 → D7 → D8 → D9 → D10 → D11 → D12 → D13 → D14 → D15 → D16 → D17 → D18 → D19 →
  fresh package → installed candidate at `C:\Users\Nick\KelDailyDriverCandidate`.
- Current test state at transcription time: desktop tsc exit 0 · Vitest 21 files / 199 PASS ·
  engine 1019 OK (unchanged) · D3 real-stack matrix green · D4 live transcription fixture E2E green ·
  D5 transition-core + connection derivations green.
