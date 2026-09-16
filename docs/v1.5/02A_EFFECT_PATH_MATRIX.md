# 02A — Effect-Path Matrix (G2)

**Claim under test:** every effect-capable path in Kel V1.5 crosses a trusted authorization
boundary before the effect occurs.

Method: source-traced inventory over `runtime/kel/*` (sweeps for `subprocess`/`Popen`, filesystem
mutation primitives, `open(...w)`, network calls, git operations, and Kel's service routes), then
call-graph verification for each hit. Classification is per path, and no row is marked covered just
because a higher-level caller is usually authorized — the check must sit at or near the effect
point, or the path must be explicitly excluded with a reason.

Classes:

| Class | Meaning |
|---|---|
| **GATED** | Crosses `kel.authorize` at/near the effect point, with actor identity bound by trusted code (never payload). Test evidence listed. |
| **KEL-STORE** | Operates only on Kel's own data directory (engine DB, artifacts, logs, attachments). No user-project, filesystem-outside-store, network, or external effect. Reached from the shell only through the authenticated service. |
| **TRUSTED-RUNTIME** | Executes inside a documented trust boundary (provider runtime or the user-authorized native host). Kel controls entry and exit; Kel **cannot** intercept the runtime's internal calls — stated explicitly, never implied otherwise. |
| **CANCELLATION** | Termination paths. Engine-owned; only ever stop processes Kel spawned, by recorded pid + creation-identity handle. |
| **CLOSED** | Found as an unreviewed side door in this G2 pass; now gated or refused. |

## 1. Matrix

| # | Effect path | Entry point | Actor source | Boundary call (near effect) | Effect point | Class | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Apply checked changes into the user's project | `apply_changes.apply_checked` ← `/api/apply` (session) and startup recovery | `user` (session-bound) / `kel` (recovery) | `authorize` kind=`write`, target=project root | `os.replace`/`unlink` into project root | **GATED** | `test_v15_authorize.ApplicationGateTests`, `test_apply_changes.py` (incl. crash-recovery tests) |
| 2 | Coding dispatch (snapshot → external agent turn → tests → evidence) | `CodingAdapter.execute` ← broker ← engine `_execute` | `worker` (live run validated) | `authorize` kind=`repo`, tools `git`+`run_tests`, target=contract root — **before** any copy or process | git clone/copies; native agent process; test `Popen` | **GATED** (entry+exit); inner agent loop TRUSTED | `AdapterEffectPointTests`, `RestartResumeTests` (expired/emergency stop ⇒ BLOCKED, zero workspaces) |
| 3 | Engine claim gate (starting any worker) | `Engine.tick` | `kel` | `ensure_job_lease` + `authorize` kind=`repo`, `consume=False` | `store.claim` run creation / broker launch | **GATED** | `EngineGateTests` (blocked: zero runs claimed; allowed: claim proceeds) |
| 4 | Durable broker launch / relaunch | `runner.DurableAdapter.execute`, `restart_checks_broker`, `recover_pending_checks` | `kel` (engine) then `worker` (broker) | claim gate precedes; the broker re-enters path 2's effect point on execution | `Popen(kel.runner)` | **GATED** at entry; effect-point re-check inside broker | `test_coding_recovery`, `test_broker_recovery` + path 2 tests |
| 5 | Test-command execution inside a coding run | `host_runtime.HostConnection.call('command/exec')` (native-host) / WSL exec | `worker` | included in the dispatch gate (tool `run_tests`); cwd pinned to workspace; provider keys stripped from env | `Popen` | **GATED** (dispatch); TRUSTED-RUNTIME inside (user-authorized model) | dispatch tests; `test_coding_boundaries` |
| 6 | Read-only native agent launch (chat/review/text) | `native.NativeAdapter.execute` ← chat path, Commander review, durable text jobs | `user`/`kel`/`worker` | none — **explicitly lease-free**: no repository/filesystem effects; tools disabled by argv; env sanitized | `Popen(claude/codex)` | **TRUSTED-RUNTIME** (read-only) | `NativeTrustBoundaryTests` (argv pinned `sandbox_mode="read-only"`, `-s read-only`, `--disable`); documented in `16_KNOWN_LIMITATIONS.md` |
| 7 | Internal model call | `internal.InternalAdapter` | `user`/`kel`/`worker` | none — provider boundary; only allowlisted tools (`read_context`, `submit_result`), bounded iterations/tokens | `urllib` → api.anthropic.com | **TRUSTED-RUNTIME** | `test_core.py` internal-worker tests; tool allowlist in source |
| 8 | Web research | `research.ResearchAdapter` ← durable research runs | `worker` | none — provider-side `web_search` (≤3 uses); citations validated against search receipts | provider API | **TRUSTED-RUNTIME**; completion evidence-checked | `check_research_evidence`, `test_research.py` |
| 9 | Native-host coding runtime (full access, contained) | `host_runtime.HostConnection` ← coding transport when contract `runtime=='native-host'` (the current compile default) | `worker` | path 2 gate precedes; Windows job object containment (`windows_job`) | native agent + test process | **GATED** at entry; inner loop TRUSTED (user-authorized model, `docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md`) | path 2 tests; containment in source |
| 10 | WSL isolated coding runtime | `wsl_runtime.WSLCodexConnection` ← coding transport when contract runtime ≠ native-host | `worker` | path 2 gate precedes; isolation check (`/mnt/c` absent); failed runs are *discarded* (`recover_isolated_loss`) | wsl exec/file sync | **GATED** at entry; inner loop TRUSTED (enforced-isolation copy) | `test_isolated_recovery`, `test_wsl_exports` |
| 11 | Project creation (greenfield `Kel Projects` folder, git init, `.gitignore`) | `Service._plan` ← `/api/send` (session) | `user` (session-bound; intent assembled in trusted code) | `authorize` kind=`write`, operation=`create-project` — confined to `<home>/Documents/Kel Projects` | `mkdir`, git init/commit, file write | **CLOSED → GATED** | `ProjectCreationPolicyTests` (allow / outside-root deny / non-user-actor deny / frozen deny), `ServiceIdentityTests.test_greenfield_project_creation_crosses_the_boundary` |
| 12 | Lease issuance | `autonomy.issue` ← `Store.create` (Kel), `ensure_job_lease` (claim gate) | `kel` only | shell route restricted to the user-safe set; `issue` is refused through `/api/autonomy` | Kel DB write (authority object) | **CLOSED → GATED** (`ServiceIdentityTests.test_lease_issuance_is_not_available_through_the_shell`) |
| 13 | Boundary grant resolution | `autonomy.resolve_expansion` ← `/api/autonomy resolve` | `user` only (engine rejects any other actor) | user decision; grant lands as lease scope; `resume_after_grant` wakes the job | Kel DB write | **GATED** (user-only) | `test_v14_autonomy`, resume tests |
| 14 | Emergency stop | `autonomy.emergency_stop` ← `/api/autonomy` | `user` only | revokes active leases, pauses jobs, cancels approvals, signals workers | process signals via runs | **GATED** (user-only) | `test_v141_boundaries`, `RestartResumeTests` |
| 15 | Cancellation kills | `runner.terminate_known_process`, `wsl_runtime.stop_group` | `kel` (control/recovery) | only processes Kel spawned, matched by recorded pid **and** creation-identity | `TerminateProcess`/`SIGTERM`/cgroup stop | **CANCELLATION** | `test_broker_recovery`, `test_isolated_recovery` |
| 16 | Legacy-engine migration | `migration.migrate_idle` (explicit startup step) | `kel`/`user` (explicit) | legacy-hash allowlist, idle checks, identity-bound termination, backup + integrity check | terminate + DB rewrite | **CANCELLATION + KEL-STORE** | `test_v12_upgrade` |
| 17 | Kel store writes (jobs/events/runs/contracts/approvals/effects/messages) | `core.Store.*` ← engine + service | engine-owned / session-authed | n/a — never touches user state | SQLite writes under store root | **KEL-STORE** | core suite |
| 18 | Artifact capture + serving | `core._artifact`, `/api/artifact` | engine | accepted-milestone gate before serving; digest verified | file write under `artifacts/` | **KEL-STORE** | `test_core.py`, artifact tests |
| 19 | Memory / map / recipes / team / briefs / provider-metadata writes | service routes (session) | `user` | recipe `run` creates a job → gated downstream (paths 2/3); nobody here can cause an external effect | Kel DB writes | **KEL-STORE** (no authority increase; role policy can only narrow) | module suites; `test_v14_team`, `test_v13_memory` |
| 20 | Attachment upload | `context.attach` ← `/api/attach` (session) | `user` | size/mime bounded | file write under `attachments/` | **KEL-STORE** | `test_core.py` attach tests |
| 21 | Diagnostics maintenance (retention purge; backup-first compaction; reports) | `/api/diagnostics` (session) | `user` | compaction is backup-first (`_backup` before `VACUUM`); purge bounded by retention settings | Kel DB maintenance | **KEL-STORE** | `test_v14_diagnostics` |
| 22 | Diagnostics export | `/api/diagnostics export` | `user` | secret-shaped values refused (V1.4.1) | read/redact | **KEL-STORE** (leak-checked) | `test_v141_claims`, `CredentialCustodyTests` |
| 23 | Provider quota/telemetry refresh | `telemetry.refresh_codex` ← supervisor | `kel` | read-only app-server query (`account/rateLimits/read`) in a Kel-owned folder; no effects | process launch (read-only query) | **TRUSTED-RUNTIME** (read-only probe) | source; provider state tests |
| 24 | Host/binary probes (`--version`, readiness) | `native.probe`, providers readiness | `kel`/`user` | read-only | process spawn | **TRUSTED-RUNTIME** (read-only probe) | `test_v14_providers` |
| 25 | Project-map git reads | `projectmap` refresh | `kel`/`user` | read-only git queries | `git log/ls-files` | read-only | `test_v13_projectmap` |
| 26 | ACP presentation adapter | `acp_host.py` stdio (launched by the desktop shell) | proxies to the authenticated HTTP service | owns no engine; every request re-enters the service boundary | none (HTTP client) | presentation only | source; used via `--acp` |
| 27 | Codex app-server transport (coding + telemetry) | `appserver.CodexConnection` | `kel`/`worker` | coding transport only reachable inside gated path 2; telemetry read-only | `Popen(codex app-server)`, JSON-RPC | **GATED** (coding) / **TRUSTED** (telemetry read) | paths 2/3 tests |
| 28 | WSL distro/setup utility (`runtime_setup.py`) | explicit setup utility | `user` (out of band) | no callers found in the running product's source; flagged for the G8 packaging/donor audit | downloads/imports distro; writes provider auth into the isolated distro root-only | **TRUSTED-RUNTIME (setup)** — credential aspect revisited at G4 | source; `runtime_setup.py` |

## 2. Side doors found in this pass (and their disposition)

1. **`/api/autonomy action=issue` — authority injection. CLOSED.** A shell payload could previously
   issue a lease with caller-chosen roots for any job; the engine then resolves a job's *latest
   active* lease at the claim gate and effect points, so a widened lease could have carried a job's
   whole effect chain. The shell now refuses every autonomy action outside the user-safe set
   (`leases`, `requests`, `guardrails`, `decisions`, `check`, `revoke`, `resolve`,
   `emergency_stop`); issuance remains Kel-only. Test:
   `test_lease_issuance_is_not_available_through_the_shell`.
2. **Greenfield project creation — ungated filesystem effect. CLOSED → GATED.** The new-project
   flow wrote `~/Documents/Kel Projects/<slug>` (mkdir, git init, file write) without crossing the
   boundary. It now crosses `authorize` under the `user-project-create` policy: user actor only,
   confined to the Kel Projects root, guardrails still applied. Tests: `ProjectCreationPolicyTests`
   plus the service-level integration test.
3. **Identity forgery hardening.** Explicit lease ids are now bound to the job they belong to
   (`lease-mismatch`); a worker's run must match both job and milestone
   (`worker-milestone-mismatch`); a destructive approval must belong to the same job as the intent;
   an unknown role denies (`role-unknown`). Tests: `FailClosedTests`.

## 3. Fail-closed rules (malformed context never means "allowed")

Missing/unknown actor → `INVALID_CONTEXT`; unknown kind → `INVALID_CONTEXT`; unknown job/milestone →
`INVALID_CONTEXT`; dead or mismatched worker → `INVALID_CONTEXT`; missing target for an effect →
`DENY target-required`; unknown role → `DENY role-unknown`. There is no default lease, no
"unknown = allowed" fallback, and no path that silently substitutes `user`, `system`, or full
access. Evidence: `FailClosedTests`.

## 4. Restart / resume / parallel guarantees

- All authorization reads current durable state; no decision is cached in memory. A process restart
  re-evaluates from the database (`RestartResumeTests.test_restarted_engine_reevaluates_against_durable_state`,
  `...requires_current_durable_rules`).
- A resumed worker whose lease expired offline is stopped at the effect point (`EXPIRED_LEASE` ⇒
  `BLOCKED`, zero workspaces). After an emergency stop, resumed work is reissued only through the
  recorded decision path; a targeted revoke is never silently undone.
- Parallel workers are isolated: worker B's denial creates a request on **B's** lease only, does not
  touch A's lease or authority, and A keeps being allowed throughout
  (`ParallelIsolationTests`).

## 5. What Kel can and cannot enforce (explicit)

Kel enforces: dispatch entry, the isolated/contained workspace, test evidence, diff digests, the
apply gate, and every Kel-owned effect point. Kel **cannot** intercept an individual tool call
inside a full external agent (codex/claude) once that agent runs inside its workspace; that inner
loop is the documented trusted runtime, contained (native-host Windows job object or WSL isolation)
and bounded by exit evidence. Provider-side inference and web search run at the provider boundary;
Kel validates their receipts (`research_evidence`, quota observations) but does not see inside them.
This statement is repeated in `16_KNOWN_LIMITATIONS.md` so the product never claims more.

## 6. G2 closure checklist

| Criterion | State | Evidence |
|---|---|---|
| Effect-path inventory complete | ✅ | this document, source-traced |
| All production-reachable effect paths classified | ✅ | §1 (28 rows) |
| All Kel-controlled effect paths authorized at/near effect point | ✅ | §1 GATED rows + §2 |
| Trusted-runtime exceptions explicitly documented | ✅ | §5, `16_KNOWN_LIMITATIONS.md` |
| Restart/resume reauthorization proven | ✅ | `RestartResumeTests` |
| Parallel isolation proven | ✅ | `ParallelIsolationTests` |
| Guardrail decisions durable | ✅ | `guardrail_decisions`; dedupe windows; `DecisionTests` |
| Adversarial tests green | ✅ | `test_v15_authorize.py` (43 tests, run: 43 passed) |
| Full suite green | ✅ | 418 passed + 10 subtests (`00_STATUS.md`) |
| Independent reviewer CONTINUE | ✅ | CONTINUE — 2026-09-16 closure review (recorded in `00_STATUS.md`) |
