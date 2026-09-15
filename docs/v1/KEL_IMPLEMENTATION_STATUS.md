# KEL V1 — IMPLEMENTATION STATUS

Date: 2026-09-14. Artifact: `Kel-Windows-0.5.0-complete-fixed` (workspace package).
Engine version shipped: **0.5.0** (was 0.4.0).

## 1. What this run changed (concrete)

### Greenfield coding release-blocker — "create me an app" (acceptance run 2, FIXED + live-verified)

0. **Wrong kind routing + missing greenfield path + unreachable reviewer + duplicate work card** — the four root causes behind the "I want to create a little app …" request ending `CLOSED / UNCERTAIN` with two duplicate "View Steps · 1" cards. Fixes, all live-verified through the packaged UI:
   - `kel/router.py`: `GREENFIELD_RE` classifies build/create-verb + deliverable-noun requests as `coding`; `kel/service.py` `_plan` treats `conversation` like `chat`.
   - Greenfield coding flow (`service.py`): creates `Documents/Kel Projects/<slug>-<hex>` (git init + empty HEAD commit + `.gitignore`), stores `['python','smoke_test.py']` as the test command, and instructs the worker to build the app AND a passing smoke test. Greenfield intent wins over a rooted active project.
   - Reviewer fallback (`service.py`): without `ANTHROPIC_API_KEY` the Commander uses an installed native CLI (claude) for plan/review instead of leaving `manual_review` permanently unjudgeable (`KEL_REVIEWER=none` opts out). `commander.py` retries reviews without image kwargs for text-only fallback models.
   - `kel/core.py` `publish()`: UNCERTAIN/FAILED publications append the specific "Blocker: <reason>"; VERIFIED greenfield coding publishes the project location.
   - Renderer dedupe (`aion-donor` `hooks.ts` → shipped `MessageList-cBYU-mto.js`): `getMessageMergeKey` keys `acp_tool_call` rows by the stable `content.update.tool_call_id` instead of row id/msg_id, so the live ACP stream frame and the persisted AionCore row for the same job merge into exactly ONE work card.
   - Result: the exact acceptance request ran live → one submission, one job, `kind=coding`, greenfield repo created with a valid HEAD, real coding worker (claude-code route via Codex ACP transport) created `mic_mute.py` + `requirements.txt` + `smoke_test.py` (14 tests), deterministic verification ran (exit 0, preserved, stable) → `repository_evidence` VERIFIED, native-claude reviewer VERIFIED, job **CLOSED / VERIFIED**, publication names `C:\Users\<user>\Documents\Kel Projects\i-want-to-create-a-little-app-that-a-121b`, apply + re-test + GUI launch exercised, exactly one work card shown, clean shutdown with zero orphan processes. Full evidence in `KEL_VERIFICATION_REPORT.md` §7.

### Release-blocking P0 launch failure (found by the user's clean-launch reproduction)

10. **Space-in-install-path startup kill (D-19, P0 — FIXED).** The packaged app exited silently before creating its window whenever the install path contained whitespace. Root cause (proven with `[KEL-BOOT]` boot instrumentation + the AionCore source): AionCore validates a custom agent's CLI on upsert via its whitespace-split `binary_name` (`first_token`), so a `command` like `C:\…\Kel Deep Seek\…\KelEngine.exe` resolved to the nonexistent `C:\…\Kel` and the agent upsert returned **400 `cli_not_found`**; `initializeKel` threw, `handleAppReady` rejected, and the app quit before window creation — with all later console output already redirected by `configureConsoleLog` to the daily log file, hence the silent-looking exit and the surviving detached engine.
11. **Fix (shipped):** `KelService.ts` stages the bundled engine into the space-free application-data directory (`%APPDATA%/kel-desktop/work/engine/`, freshness-checked by size/mtime) whenever the packed path contains whitespace, and registers that path as the ACP agent command. The engine drain hook moved to the top of `initializeKel` and now blocks `before-quit` briefly so `/api/shutdown-idle` cannot race process exit — a failed startup or a normal quit always stops a freshly spawned engine (no orphans).
12. **[KEL-BOOT] boot instrumentation** added to `index.ts`, `KelService.ts`, and `backend-launcher.ts` (module load, lock, squirrel, whenReady, initializeProcess, backend spawn/exit/error, initializeKel stages, window creation, all quit paths). Retained: low-volume, log-file-only, and it is what pinned this P0 to a single failing HTTP call.

### Engine — `resources/kel-engine/KelEngine.exe` (rebuilt from `Kel-Prototype` source)

1. **Deterministic initial routing wired in** (`kel/service.py`). `Service.submit` now
   derives `kind` from `router.classify(text)` when the client omits it (D-04). The
   previously-dead `classify()` is the live fallback classifier; the status fast-path
   also accepts `kind=='status'`.
2. **Side-question supersede semantics** (`kel/acp_host.py`). A second prompt for a
   conversation whose stream is still polling no longer errors with "already has an
   active prompt". It ends the previous stream with a short note and serves the new
   request; the durable job keeps running untouched (D-02). The `finally` guard only
   clears the session record it owns.
3. **Approval surfacing in the ACP stream** (`kel/acp_host.py` + `kel/service.py`).
   When a job enters `AWAITING_USER`, the ACP stream now emits an actionable message:
   "Kel needs your permission to continue: <action summary>. Open “Work context” in the
   sidebar and allow or deny there." The state API adds `action_summary` per pending
   approval, with a local fallback parser for older engines (D-03).
4. **Cancel-race settlement** (`kel/core.py`). `Store.consume` accepts terminal
   receipts for `CANCEL_REQUESTED` runs and finalizes them as stop acknowledgements —
   a cancel that races the broker launch can no longer strand a job in `CANCELLING`
   → expired → `WAITING_RESOURCE` (D-17, found by live adversarial testing).
5. **Version alignment** (`kel/service.py`, `kel/acp_host.py`). `ENGINE_VERSION`
   = `0.5.0`, and the ACP `initialize` reports it instead of a hardcoded `0.4.0`
   (D-16).
6. **`Service.shutdown()`** added: stops supervision, joins the supervisor thread,
   closes the engine, shuts down the request pool (fixes a Windows sqlite-handle
   teardown flake in tests; used by the new tests).
7. **Telemetry guard** (`KEL_SKIP_TELEMETRY`) for test/CI contexts.

### Desktop shell — `resources/app.asar` (rebuilt from `aion-donor` source)

8. **Engine drain on quit** (`process/services/kel/KelService.ts`). `before-quit`
   sends POST `/api/shutdown-idle`; the engine refuses while work is open and drains
   when idle, bounding orphaned engine processes (D-12, D-18).
9. **Stale mapping cleanup**: a 404 for a donor conversation now drops the
   mapping/history pair instead of re-importing it forever (D-11).
10. **Dead `aion-host.json` write removed** (nothing read it) (D-07).

### Tests

11. `tests/test_service_routing.py` (new, 4 tests): classify mapping, status query
    without a model, deterministic document compile from an untyped request, explicit
    client kind precedence.
12. `tests/test_acp_host.py` (+2): side-question keeps the job running and resumes
    the conversation; `AWAITING_USER` emits the permission guidance with the action
    summary.
13. `tests/test_core.py` (+1): cancel racing launch finalizes with the terminal
    receipt.

Suite: **150 passed** (was 143 at intake).

## 2. What was materially wrong (found by this audit)

- The primary desktop shell had no way to end the engine's life on quit → orphaned
  `KelEngine` services accumulated (multiple historical orphans observed live).
- A cancel during worker launch stranded jobs permanently (live reproduction).
- Side questions were rejected at the ACP layer while a job was active, violating the
  conversation-vs-work lifecycle invariant in the AionCore-driven path.
- Worker permission waits surfaced as passive text with no pointer to the approval
  controls.
- `router.classify` existed but was dead code; request kind was client-supplied.
- Engine version label (0.4.0) disagreed with the release (0.5.0).

## 3. What architecture changed

None of the intended architecture was replaced. The audit confirmed the shipped
package already implements the Kel skeleton at high fidelity:

- **Commander** (plan + independent review contexts), deterministic
  **CompletionContract compilers** for document/coding/research, with literal-check
  validation and template fallback.
- **Durable work engine**: SQLite WAL events → jobs projection; lease-based claims;
  idempotent inbox; **only `assess()` produces completion records**; trusted-reviewer
  boundary; provider health circuits; effect tracking; orphan fencing.
- **Three worker classes**: direct Kel answers; bounded internal loop (2 allowlisted
  tools); external native agents (codex / claude, codex-code / claude-code) with
  durable broker supervision, native session continuity, and deterministic
  snapshot→turn→test→diff evidence.
- **Presentation**: AionUI donor shell + AionCore, Kel registered as the only enabled
  assistant (ACP), renderer `KelWorkPanel` for jobs/approvals/apply, Kel web UI as the
  engine's own surface.

This run tightened the seams between those pieces rather than re-architecting them.

## 4. Donor patterns adopted (summary — see KEL_DONOR_LEDGER.md)

- **AionUI/AionCore** (Apache-2.0): shell, pet, ACP runtime, permission UX; Kel
  enforces single-assistant mode by disabling every other assistant at startup.
- **Chuzom**: milestone acceptance checks + freeze semantics (checks run against real
  repository state; accepted milestones preserved on repair).
- **Forge/Adulari**: process exit ≠ completion; evidence-driven completion authority.
- **XOPC**: bounded leaf workers, allowlisted tools, structured results.
- **QwenPaw**: ACP external-agent runtime and session lifecycle.
- **ryderderder/orchestrator**: real vendor CLI usage, subscription headroom
  telemetry (Codex `rateLimitsByLimitId`), provider readiness.
- **Agent Orchestrator**: observation → durable facts → derived status; durable
  runtime metadata.
- **Orkas**: coupled reasoning stays with one owner; delegation only for cleanly
  separable work.
- **Warpforge**: persistent work independent from the conversational turn (detached
  brokers, durable inbox).
- **Microsoft Conductor**: deterministic pipelines with schema validation and explicit
  termination — adopted as the document/coding/research compilers, not as the
  Commander.

## 5. What was intentionally NOT adopted

- AionUI's visible multi-agent paradigm (agent-team UI stays as settings surface;
  the runtime disables all assistants except Kel).
- AgentOS-style recursive delegation (workers are told not to delegate; no
  agent-spawn tooling is exposed).
- Nous/NueOS AGPL code (ideas only: evidence/witness and lifecycle separation).
- A static DAG engine (Conductor-style) as the Commander.
- MoFlo's learned routing (unsupported by source-level evidence).
- Provider-side "quality" heuristics: the router supports `quality_floor` but no
  producer populates it in V1 (no reliable signal yet).

## 6. Remaining limitations (explicit)

1. **Reviewer independence is bounded by the single configured model.** The planner
   and reviewer are separate contexts with a DB-enforced executor≠reviewer rule, but
   with one API key they can be the same model family. (Documented limitation.)
2. **Escalation is provider-switch, not quality-tier.** Retries rotate to a different
   eligible provider after two attempts; there is no quality ladder because V1 has no
   quality signal producer.
3. **Second-instance behavior** of the packaged shell: a concurrent second launch
   exits silently (pre-existing, identical on the original asar); root cause is in
   the donor shell's backend data-dir conflict handling. Primary instance unaffected.
4. **ACP-rooted project permissions**: ACP sessions create projects rooted at the
   donor cwd (e.g. Temp); coding still requires an explicit test command. Documented.
5. **Orphaned third-party agent processes** from the developer's earlier packages
   were observed on this machine; they belong to older builds, not this package.

## 7. Final skeleton modules (exact files)

- Engine (Python, PyInstaller onedir): `resources/kel-engine/KelEngine.exe`
  - `kel/core.py` — durable store, events, leases, verdicts, approvals, effects
  - `kel/engine.py` — supervision tick, claims, review scheduling, escalation
  - `kel/commander.py` — plan compiler + independent review context
  - `kel/router.py` — deterministic classification + hard-filter routing
  - `kel/coding.py`, `kel/coding_transport.py` — repo snapshots, test evidence, ACP
  - `kel/runner.py` — detached broker lifecycle, fencing, recovery
  - `kel/internal.py` — bounded internal worker
  - `kel/native.py` — codex/claude CLI adapters
  - `kel/research.py` — citation-bound web research
  - `kel/apply_changes.py` — digest-bound change application with backups
  - `kel/context.py` — projects, conversations, handoffs, grants
  - `kel/acp_host.py` — ACP presentation for AionCore
  - `kel/service.py` — authenticated loopback service + web UI
  - `kel/telemetry.py`, `kel/migration.py`, `kel/instance_lock.py`,
    `kel/windows_job.py`, `kel/wsl_runtime.py`, `kel/host_runtime.py`
- Desktop shell: `resources/app.asar`
  - `out/main/index.js` (KelService: engine launch, ACP agent registration,
    conversation mapping, history reconcile, drain-on-quit)
  - `out/renderer/` (KelWorkPanel, kelHistory, kelHistorySearch)
  - `out/preload/` (kelAPI)
- Backend: `resources/bundled-aioncore/win32-x64/aioncore.exe` (stock v0.2.2,
  Apache-2.0)
- Web UI: `resources/kel-engine/_internal/kel/web/` (served by the engine)

## 8. P0/P1 confirmation

- All P0/P1 drift items are resolved (see KEL_V1_DRIFT_AUDIT.md for per-item
  evidence): the only P1-class defect found in the shipped code was D-17 (cancel
  race), fixed with a regression test and live re-verification.
- Nothing is left UNVERIFIED without a stated technical reason (see
  KEL_VERIFICATION_REPORT.md §7).
