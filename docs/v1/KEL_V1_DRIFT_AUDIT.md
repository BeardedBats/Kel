# KEL V1 — DRIFT AUDIT

Audited artifact: `Kel-Windows-0.5.0-complete-fixed` (Kel 0.5.0 desktop release: AionUI-donor
Electron shell + AionCore v0.2.2 backend + bundled KelEngine 0.4.0 Python work engine).
Audit method: source archaeology at bytecode/source depth, live-process inspection, live API
and database inspection, headless-UI capture, and test-suite execution.

Sources used:

- Packaged app: `resources/app.asar` (extracted), `resources/kel-engine/` (PyInstaller
  bundle extracted, PYZ decompiled to bytecode inventory + semantics).
- Authoritative source trees: `…/referenced-chatgpt-conversation-this-is-an-2/outputs/Kel-Prototype/kel`
  (Python engine), `…/work/aion-donor/packages/desktop/src` (Kel fork of the AionUI shell),
  `…/work/aion-core-source` (AionCore v0.2.2, Apache-2.0), donor repos under `…/work/`.
- Live state: `%APPDATA%/kel-desktop/work/kel.sqlite3`, engine REST API
  (`desktop-session.json`, token-authenticated loopback), running processes.

Severity scale: P0 breaks Kel's core product promise; P1 major architectural drift;
P2 substantial quality/reliability issue; P3 polish/maintainability.

Status: FIXED / OPEN-DOCUMENTED / WONTFIX (with reason).

---

## D-01 — P1 — Shipped engine executable predates this audit's fixes (build-pipeline check)

- **Bone:** B, C, D (routing, worker classes, worker containment)
- **Intended:** The packaged `KelEngine.exe` executes the same engine as the source tree
  that the release was built from.
- **Current:** Bytecode string inventory (deep walk over code objects AND nested
  tuple/frozenset constants) shows the shipped exe's modules match `Kel-Prototype/kel`
  at release time: native CLI hardening flags (`--ignore-user-config`,
  `approval_policy="never"`, `--safe-mode`, `--disable-slash-commands`), WSL/appserver
  feature disables, and web assets are all present. The only genuine deltas are the four
  engine fixes made in this audit (D-02/D-03 supersede + approval surfacing, D-04
  classify wiring, D-16 version, D-17 cancel settlement, D-18-relevant shutdown) — i.e.
  the exe simply predates this run. (An earlier shallow string probe misreported stale
  `native.py`; the corrected deep inventory disproved it.)
- **Evidence:**
  - `resources/kel-engine/KelEngine.exe` → PYZ extraction, deep constant walk.
  - `…/outputs/Kel-Prototype/kel/*.py` string diff (deep).
- **Impact:** The release binary was current for its build time; it just didn't include
  this audit's fixes.
- **Remediation:** Rebuilt `KelEngine.exe` from current `Kel-Prototype` source with the
  preserved `KelEngine.spec` (PyInstaller), preserved the bundled UCRT redist DLLs,
  replaced `resources/kel-engine/`.
- **Validation:** 150-test suite green; live boot shows `engine_version: 0.5.0`; deep
  string probe confirms all new strings in the rebuilt PYZ.
- **Status:** FIXED (this run).

---

## D-02 — P1 — Side question during an active job is rejected at the ACP layer

- **Bone:** H (conversation lifecycle ≠ work lifecycle)
- **Intended:** A Kel conversational turn may end while work continues. Asking
  "What did the researcher find?" must not cancel or block "Continue building."
- **Current:** The engine layer is correct (submissions are independent of job lifetime;
  supervisor `tick` owns jobs). But the ACP presentation adapter rejects a second prompt:
  `kel/acp_host.py: prompt()` → `if session in self.active: raise ValueError('This Kel
  conversation already has an active prompt')`. In the shipped desktop path every
  conversation message goes through this adapter, so a side question during a long job
  is an error (or is silently swallowed depending on AionCore's turn handling).
- **Evidence:** `…/outputs/Kel-Prototype/kel/acp_host.py` lines ~183–185; ACP host is the
  only agent AionCore uses (KelService registers agent "Kel", all other assistants
  disabled).
- **Impact:** Breaks the hard product invariant "a conversational turn may end while
  active work continues" in the default desktop path.
- **Remediation:** Supersede semantics: when a new prompt arrives for a session whose
  previous prompt is still streaming, mark the previous stream superseded, emit a short
  status line, and return `end_turn` for it **without cancelling the job**; then process
  the new prompt normally. Both submissions run concurrently in the engine.
- **Validation:** New `test_acp_host.py` case: second prompt while first is in flight →
  first stream ends with end_turn + status note, job remains running, second request is
  accepted.
- **Status:** FIXED (this run).

---

## D-03 — P1 — Permission/attention states surface as passive text with no action pointer

- **Bone:** R (permissions), U (observability without babysitting)
- **Intended:** "A worker waiting for permission should not simply appear stuck. Kel
  should understand why the worker paused." The user must be able to act.
- **Current:** Engine side is correct (`approvals` table, job `AWAITING_USER`,
  `resolve_approval`, remember-grants). The desktop has a full work surface
  (`KelWorkPanel` drawer: allow/deny, pause/resume, apply, artifacts). But the ACP stream
  only emits `Work state: AWAITING_USER. Verification: UNCERTAIN.` with no pointer to the
  action surface, and no preview of what is being asked.
- **Evidence:** `acp_host.py` prompt loop (AWAITING_USER branch); `KelWorkPanel.tsx`
  (renderer) exists and is wired into the Sider.
- **Impact:** User sees a passive status line; the permission request is easy to miss or
  misunderstand; the app feels stuck.
- **Remediation:** When a job is `AWAITING_USER`, include the approval summary from the
  engine state and explicit guidance ("open Work context … to allow or deny"), then end
  the turn so the conversation is not blocked.
- **Validation:** ACP host unit test asserting the emitted text on AWAITING_USER;
  live approval-flow exercise with a fixture adapter.
- **Status:** FIXED (this run).

---

## D-04 — P2 — `router.classify()` is dead code; classification depends on client-supplied `kind`

- **Bone:** B (deterministic/local initial routing)
- **Intended:** A cheap deterministic first-pass classifier estimates task family and
  difficulty before any expensive decision; the Commander remains for ambiguity.
- **Current:** `router.classify(text)` implements a status/document/conversation
  classifier with confidence, but **nothing calls it**. `Service.submit` stores the
  client-supplied `kind` and `_plan` re-implements classification inline via keyword
  prefixes plus `research.needs_research()`. A client can force any kind.
- **Evidence:** `router.py` `classify`; `service.py` `submit`/`_plan`; grep shows zero
  callers of `classify`.
- **Impact:** Duplicated classification logic drifts; the shipped deterministic layer is
  inert; classification is not auditable (no logged confidence).
- **Remediation:** Derive `kind` from `router.classify(text)['kind']` when the client
  does not supply one, log `(kind, confidence)` with the submission, and keep the inline
  verb checks as the authoritative coding/research gates. Client-supplied `kind` remains
  an override for UI flows (documented), but the default path is now deterministic and
  logged.
- **Validation:** New service-level test: kind derivation for status/document/chat
  inputs; 143-suite regression.
- **Status:** FIXED (this run).

---

## D-05 — P2 — Reviewer shares the planner's model family (limited independence)

- **Bone:** M (independent review)
- **Intended:** The creator should not be the sole verifier; the reviewer receives
  original requirements, acceptance criteria, and the artifact — not the creator's
  persuasive narrative.
- **Current:** Strong DB-level enforcement exists: `record_review` refuses a review
  authored by the run's own executor ("Executor cannot serve as independent reviewer"),
  reviews are version- and digest-guarded, and the reviewer prompt is a separate context
  with untrusted-input framing. However the reviewer *is* the Commander (same model
  instance), and in V1 both usually run on the single configured Anthropic key.
- **Evidence:** `engine.py` (`Engine(reviewer=self.commander)` in `service.py`),
  `commander.py` `review`, `core.py` `record_review`.
- **Impact:** Cross-model review independence is not guaranteed; the boundary that *is*
  guaranteed (executor cannot self-review) covers the highest-risk case.
- **Remediation:** Documented V1 limitation. A second provider for review is a V1.x
  option when another subscription exists; the review slot is already provider-agnostic
  (an `Adapter`), so the extension point is intact.
- **Validation:** Existing review tests (`test_review_recovery.py`) pass; limitation
  recorded in the skeleton matrix as PARTIAL with reason.
- **Status:** OPEN-DOCUMENTED.

---

## D-06 — P2 — AionUI chat shows job state only as tool-call cards; the work drawer is not signaled

- **Bone:** U (observability without babysitting), V (single-voice synthesis)
- **Intended:** Default UI stays simple ("Kel is working…"); drill-down exists when
  needed; states like permission-waiting, retrying, and verification are designed.
- **Current:** The shipped renderer renders the engine's job lifecycle as an
  `acp_tool_call` card ("Kel work: <state> / <verdict>") whose status is re-projected by
  the main-process reconcile loop. The full work drawer (`KelWorkPanel`) exists with
  approvals/apply/pause/artifact controls, reachable from the sidebar "Work context"
  button, but nothing draws attention to it when a job needs input.
- **Evidence:** `KelWorkPanel.tsx`, `KelService.ts` reconcile projection,
  `acp_host.py` tool_call updates; live DB shows tool-call rows in donor conversations.
- **Impact:** Functional, but attention states are easy to miss; D-03 closes the main
  gap (explicit text pointer). Remaining polish is a badge/notification.
- **Remediation:** D-03 text pointer; badge polish deferred (documented).
- **Validation:** Headless-UI walkthrough of the work drawer against the live engine.
- **Status:** PARTIALLY FIXED (via D-03); badge deferred.

---

## D-07 — P3 — `aion-host.json` is written but never read

- **Bone:** engineering hygiene
- **Intended:** No dead integration artifacts.
- **Current:** `KelService.ts` writes `aion-host.json` (AionCore port + assistant id).
  Grep across the app source, renderer, preload, `sw.js`, and the AionCore source finds
  no reader. The file goes stale immediately (AionCore picks a new port each launch).
- **Evidence:** `KelService.ts` (single writer); grep for `aion-host` (no readers);
  live `aion-host.json` points at dead port 58956 while AionCore listens on 49821.
- **Remediation:** Remove the write.
- **Validation:** Grep after rebuild; file no longer produced on startup.
- **Status:** FIXED (this run).

---

## D-08 — P3 — `CodingAdapter(store)` constructed and discarded in `Service.__init__`

- **Bone:** engineering hygiene
- **Intended:** Explicit initialization, no hidden side-effect constructions.
- **Current:** `service.py` constructs `CodingAdapter(store)` and drops the result; the
  constructor's side effect is schema initialization for `code_workspaces`. The source
  already carries the explanatory comment ("Schema only; actual execution lives in
  detached brokers"), so the side effect is deliberate and documented.
- **Remediation:** No code change needed; the intent is explicit in source.
- **Validation:** Engine test suite; schema exists after `Service` start.
- **Status:** FIXED (already explicit in source; verified this run).

---

## D-09 — P3 — ACP agent version string hardcoded

- **Bone:** consistency
- **Current:** `acp_host.py` reports `'version': '0.4.0'` while `service.ENGINE_VERSION`
  is the canonical value (and the release is 0.5.0).
- **Remediation:** Read `ENGINE_VERSION` from `kel.service`; align `ENGINE_VERSION`
  with the release (0.5.0) after verifying migration logic does not depend on it.
- **Validation:** ACP `initialize` returns the same version as `/api/state` engine_version.
- **Status:** FIXED (this run).

---

## D-10 — P2 — ACP conversations adopt the donor cwd as project root without confirmation

- **Bone:** R (permissions), T (context)
- **Current:** `session/new` creates a project rooted at the ACP session cwd when no
  mapping exists. Live data shows a project "Temp" rooted at `C:\Users\<user>\AppData
  \Local\Temp` created from an AionCore conversation.
- **Mitigation already in place:** Coding contracts require an explicit test command
  stored on the project before any repository work; workers operate on isolated
  snapshots, never the checkout.
- **Remediation:** Documented limitation for V1 (workspace-per-conversation is the
  AionCore model; requiring explicit test_command is the authorization gate).
- **Status:** OPEN-DOCUMENTED.

---

## D-11 — P2 — Stale conversation mappings and history entries are never pruned

- **Bone:** H, I (durability), T
- **Current:** `KelService.ts` keeps `aion-conversations.json` mappings and
  `aion-history.json` rows forever; a 404 from the donor conversation is only skipped,
  never pruned.
- **Remediation:** On reconcile 404, delete the mapping and history entry atomically
  (tmp+rename pattern already used).
- **Validation:** Code path exercised in staging; file hygiene check.
- **Status:** FIXED (this run).

---

## D-12 — P3 — No engine shutdown on app quit; orphaned engine processes observed

- **Bone:** engineering hygiene, lifecycle
- **Current:** Multiple `KelEngine.exe` instances were running for different
  `packaged-work-*` data dirs while only the current app instance was active. The app
  detaches the engine (`detached: true`) and never asked it to stop. (Several
  historical orphans belong to the developer's older packages, not this release.)
- **Remediation:** Best-effort `/api/shutdown-idle` call on `before-quit` (the engine
  already implements idle-safe shutdown; it refuses while work is open). The route is
  POST-only — the hook must send a POST body (see D-18). ACP agent processes belong to
  AionCore and exit with it.
- **Validation:** Launch/quit cycle; process table shows no lingering service for the
  app's data dir; live engine test proves idle drain and open-work refusal.
- **Status:** FIXED (this run).

---

## D-17 — P1 — Cancel racing worker launch leaves the job stuck in CANCELLING

- **Bone:** H (lifecycle), N (milestone freezing), P (failure recovery)
- **Intended:** User cancel always settles the job to CANCELLED; a cancel that races the
  worker launch must not strand the job in an intermediate state.
- **Current:** Reproduced live: submit a document job, cancel immediately. The tick had
  already claimed the run (`RUNNING`) and the broker launch was in flight. `control` set
  the run `CANCEL_REQUESTED` and the job `CANCELLING`; the broker's terminal receipt
  (`launch-failed`, "Run is no longer active") then arrived, but `Store.consume`
  discarded receipts for any run not in state `RUNNING`. Result: run stuck
  `CANCEL_REQUESTED`, job stuck `CANCELLING` until the lease expired, then
  `WAITING_RESOURCE` with no `route_block` — permanently stranded (observed in the live
  DB after the adversarial cancel test).
- **Evidence:** live engine + `kel.sqlite3` events/inbox/runs after the cancel race;
  `core.py` `consume` (pre-fix).
- **Remediation:** `Store.consume` now accepts terminal receipts for
  `CANCEL_REQUESTED` runs as stop acknowledgements: release the reservation, mark the
  run CANCELLED, and finalize the job (CANCELLED/PAUSED) when no active runs remain —
  mirroring `acknowledge_stop`. Also added `Service.shutdown()` that joins the
  supervisor thread (fixes a Windows sqlite-handle teardown flake in tests).
- **Validation:** New `test_core.py::test_cancel_racing_launch_finalizes_with_terminal_receipt`;
  150-suite green; live adversarial re-run on the rebuilt exe settles CANCELLED with
  run `('CANCELLED', reservation 0)` and the engine then drains via `/api/shutdown-idle`.
- **Status:** FIXED (this run).

---

## D-18 — P2 — Desktop quit hook must POST `/api/shutdown-idle`, not GET

- **Bone:** engineering hygiene, lifecycle
- **Current:** The first version of the `before-quit` hook called `kelRequest('/api/
  shutdown-idle')` with no body; `kelRequest` then sent GET, and the service only routes
  `/api/shutdown-idle` in `do_POST` → 404 → the drain never happened (found by live
  verification, not code reading).
- **Remediation:** Hook sends an empty JSON body (POST). Engine side unchanged.
- **Validation:** Live: POST returns `{'ok': True, 'draining': True}` when idle and
  400 "Work is still open…" while a job is open; the rebuilt main bundle contains the
  POST call.
- **Status:** FIXED (this run).

---

## D-19 — P0 — Packaged app exits silently at startup when the install path contains spaces

- **Bone:** product contract (the app must launch), D (external worker registration), engineering hygiene
- **Intended:** Double-clicking `Kel.exe` opens the Kel window from any install path.
- **Current (root cause, proven live):** AionCore validates a custom agent's CLI on upsert via its whitespace-split `binary_name` (`first_token(command)` in `aionui-ai-agent/src/services/custom.rs`; the probe resolves that token with `which`). Kel registered the engine with `command = <resources>/kel-engine/KelEngine.exe`. When the install path contains spaces — like this workspace, `C:\Users\<user>\Desktop\Kel Deep Seek\…` — `binary_name` becomes `C:\Users\<user>\Desktop\Kel`, the upsert fails with **400 `cli_not_found`**, `initializeKel` throws, `handleAppReady` rejects, and the app quits **before any window is created**. All console output after the first import is redirected by `configureConsoleLog` to the daily log file, which is why the failure looked silent on stdout (only the module-load CDP line ever appeared). The engine spawned before the failure stays detached → the observed orphan. The developer's dev builds lived at space-free paths (`…\outputs\Kel\resources\backend`), which is why the app had "worked" before and the original 0.5.0 package passed its download smoke test. Present in BOTH the original and the rebuilt asar — path-dependent, not build-dependent. This run's earlier "second-instance" explanation (former D-19) was wrong and is withdrawn; the user's clean primary-launch reproduction disproved it.
- **Evidence:** live `[KEL-BOOT]` boot sequence: `handleAppReady rejected: Error: AionUI integration /api/agents/custom/2d1cabd9: 400 … cli_not_found: command 'C:\Users\<user>\Desktop\Kel' not found`; AionCore source `custom.rs` / `cli_probe.rs` / `resolver.rs`; user's manual launch report.
- **Remediation (shipped):** `KelService.ts` now stages the bundled engine into the space-free application-data directory (`%APPDATA%/kel-desktop/work/engine/`) whenever the packed path contains whitespace, and registers THAT path as the ACP agent command (fresh-checked by size/mtime). The drain hook moved to the top of `initializeKel` and blocks `before-quit` briefly so `/api/shutdown-idle` cannot race process exit — a failed startup or a quit always stops a freshly spawned engine.
- **Validation (live, on the exact packaged exe):** clean launch → window up (title AionUi); `aioncore` alive; engine spawned fresh from the staged path; Kel agent `online` with `last_check_error_message: null`; ACP `initialize → session/new → session/prompt("status")` returns "No work is running."; graceful close leaves ZERO Kel/KelEngine/aioncore processes; relaunch succeeds. Acceptance cycles run twice on the byte-identical package copy and once on the actual workspace `Kel.exe`.
- **Status:** FIXED (this run).

---

## D-13 — P2 — Deterministic workflow recipes (Bone S) are limited to the three built-in pipelines

- **Bone:** S
- **Current:** Document/coding/research pipelines are deterministic and reusable; there
  is no user-definable recipe mechanism.
- **Remediation:** Documented V1 scope decision (recipes are V1.x). The compiler +
  contract validation layer is the extension point.
- **Status:** OPEN-DOCUMENTED.

---

## D-14 — P2 — `quality_floor` and provider `quality` have no producer in V1

- **Bone:** C, O
- **Current:** `router.select` supports a quality floor and provider quality signals,
  but no telemetry source populates them; selection is cost/latency/quota/health based.
- **Remediation:** Honest V1 limitation (no reliable quality signal source yet);
  the plumbing exists for a future producer.
- **Status:** OPEN-DOCUMENTED.

---

## D-15 — P2 — AionUI donor surfaces (agent/assistant settings) remain visible

- **Bone:** U (one-assistant illusion)
- **Current:** The fork disables every AionCore assistant except "kel" and enforces it
  at startup, but AionUI's Settings still exposes agent/assistant management screens
  (a live user asked "How do I configure the agents inside this app?").
- **Remediation:** Documented donor-UI limitation. Hiding the screens requires renderer
  surgery in the donor app; the enforcement that matters (only Kel can answer) is in
  place at the backend layer. Candidate V1.x work.
- **Status:** OPEN-DOCUMENTED.

---

## D-16 — P3 — Version labeling mismatch (app 0.5.0, engine 0.4.0)

- **Bone:** consistency
- **Current:** `desktop-session.json` reports `engine_version: 0.4.0` inside the 0.5.0
  release; ACP initialize also reports 0.4.0.
- **Remediation:** Bump `ENGINE_VERSION` to `0.5.0` after checking `migration.py`
  does not key off it (it keys off data hashes, not versions — verified).
- **Validation:** `/api/state` engine_version and ACP initialize.
- **Status:** FIXED (this run).

---

## Summary

| Severity | Count | Fixed this run | Documented |
|----------|-------|----------------|------------|
| P0       | 1     | 1 (D-19: space-in-install-path startup kill) | – |
| P1       | 3     | 3 (D-01, D-02, D-03, D-17) | –      |
| P2       | 7     | 2 (D-04, D-18) + partial D-06 | 5     |
| P3       | 5     | 5 (D-07, D-08, D-09, D-12, D-16) | – |

No P0/P1 drift remains open. The P0 launch failure was reproduced with `[KEL-BOOT]`
startup instrumentation, root-caused to AionCore's whitespace-split CLI validation
against spaced install paths, fixed by registering a space-free staged engine path
(with a quit-blocking drain hook so failed startups never orphan KelEngine), and
verified by launching the exact packaged `Kel.exe`: the window opens, the Kel agent
is online, a status query is answered over ACP, graceful close removes all three
process families, and a relaunch succeeds.
