# KEL V1.3 — DONOR AUDIT (Gate 1)

Date: 2026-09-14. Auditor: Kel V1.3 lead engineer session. Status: Gate 1 design deliverable.
Method: each donor was cloned shallowly from GitHub, pinned at an exact revision, license read at the
inspected revision, and implementation code + tests inspected directly (README used for orientation
only). Raw evidence packs are retained in the working thread (artifact ids in
`_kel-work/v13-gate0/EVIDENCE_INDEX.md`); every citation below points into the pinned clones at
`C:\Users\<user>\Desktop\Kel\DeepSeek\_kel-work\v13-donors\<owner>_<repo>` with revisions in
`v13-donors\revisions.txt`.

Classifications: **STEAL** = copy a small, high-quality permissively-licensed implementation;
**ADAPT** = reproduce the pattern inside Kel's architecture; **REFERENCE** = design benchmark only;
**AVOID** = intentionally reject. No donor code has been copied into Kel at Gate 1 — this document is
the pre-copy review record. Any future STEAL must add attribution (MIT notice text; Apache-2.0 NOTICE
check) and tests covering the adopted behavior.

Inspection confidence: donor facts below are CONFIRMED (read from the pinned clones) unless a line is
explicitly marked TENTATIVE or UNCERTAIN. Kel-side equivalents are CONFIRMED against the
Kel-Prototype source tree at `outputs\Kel-Prototype\kel\`.

---

## 1. NousResearch/hermes-agent — memory-provider abstraction

- Repository: `NousResearch/hermes-agent`; revision `40f2702b22a3` (2026-09-14, main).
- License: MIT (root `LICENSE`: "MIT License / Copyright (c) 2025 Nous Research"). No NOTICE;
  no per-file SPDX headers. Vendored/plugin subdirs carry separate MIT copyright holders
  (`plugins/hermes-achievements/LICENSE` etc.); skill bundles under `skills/**`,
  `optional-skills/**` were NOT individually license-read — treat as tainted until checked.
- Source files inspected: `agent/memory_provider.py` (193 lines), `agent/memory_manager.py`
  (837 lines), `tools/memory_tool_store.py` (441 lines), `tools/memory_tool.py`,
  `plugins/memory/__init__.py`, `hermes_constants.py`, `agent/background_review.py`.
- Tests inspected: `tests/agent/test_memory_provider.py` (1527 lines),
  `tests/agent/test_memory_boundary_commit.py`, `tests/agent/test_memory_session_switch.py`,
  `tests/agent/test_background_review_memory_scope.py`, `tests/agent/test_memory_recall_indicator.py`,
  `tests/plugins/memory/test_holographic_store.py`.
- Patterns:
  1. **MemoryProvider lifecycle seam** (`agent/memory_provider.py:73-193`) — required hooks
     (`name`, `is_available`, `initialize`, `get_tool_schemas`) + optional hooks
     (`system_prompt_block`, `prefetch(query, session_id)`, `sync_turn`, `on_memory_write`,
     `on_session_switch`, `on_pre_compress`, `shutdown`). Storage / retrieval / context assembly are
     separated by verb. → **STEAL (interface shape only)**. stdlib-only (abc/dataclasses/re).
  2. **Explicit scope on every call + session rebind** (`:88-95`, `:143-148`; tests:
     `test_memory_session_switch.py`) — retrieval and writes take an explicit scope; `on_session_switch`
     rebinds state; non-primary contexts skip writes. Kel substitutes `project_id` for
     `hermes_home`. → **ADAPT**.
  3. **Context fencing + stream-safe sanitization** (`agent/memory_manager.py:167-177`) — recalled
     memory is injected inside `<memory-context>` fences with a "NOT new user input" note, and
     provider output is scrubbed of those markers so a provider cannot forge provenance
     (`sanitize_context`, `StreamingContextScrubber`). Tests:
     `TestMemoryContextFencing::test_sanitize_context_strips_fence_escapes`. → **STEAL** (~30 lines,
     pure `re`). Directly reusable in Kel's composer for injected memory.
  4. **Write provenance metadata** (`:186-189`) — built-in writes mirrored with
     `action/target/content/metadata{write_origin, session_id, tool_name}`; boundary commits ordered
     on a single serialized worker (`test_memory_boundary_commit.py` pins on_session_end before
     on_session_switch). → **ADAPT**.
  5. **Curated store with refusal-to-lose-data guards** (`tools/memory_tool_store.py:61-66`) —
     refuses to flush when the on-disk file would not round-trip; char budgets; file locking.
     → **REFERENCE** (posture only; the flat-file `\n§\n` format and personal char budgets are out).
- Already in Kel: `kel/context.py` projects/conversations/attachments/handoffs; distinct
  history-vs-work stores; no provider abstraction at all (Kel memory is a store, not a plugin host).
- Remaining gap in Kel: everything durable-knowledge; no typed records; no fencing markers for
  injected memory (composer must add them); no session/project rebind semantics.
- Verdict: STEAL (fencing/sanitize + ABC shape), ADAPT (scope/rebind/provenance), REFERENCE
  (store posture), **AVOID** the plugin ecosystem, provider discovery precedence, and the v1/v2
  duck-typed compatibility shims (`PRE_COMPRESS_CHECKPOINT_API_VERSION`).
- Attribution: MIT notice + copyright line if the fence/sanitizer code is copied.
- Dependency impact: none (stdlib). Risk: ABC is broader than Kel needs — copy shape, not breadth.
- Brief-premise correction: hermes has **no project-scoped memory** by design (scope keys are
  profile/session/user); Kel's project scoping must be built new.

## 2. Untrivial-ai/agent-orchestrator — durable facts → derived status

- Repository: `Untrivial-ai/agent-orchestrator`; revision `768ab5034b98` (2026-09-15, main).
- License: Apache-2.0 (root LICENSE). No per-file SPDX headers; no root NOTICE found — before any
  copy, complete an Apache-2.0 §4(d) NOTICE audit. `.gitmodules` declares `private/ao-cloud`
  (separate repository, own terms) — untouched, not vendored.
- Source files inspected: `backend/pkg/contract/status.go` (267 lines), `backend/internal/domain/
  status.go`, `agent_readiness.go`, `activity.go`, `native_checkpoint.go` (79 lines),
  `backend/internal/ports/terminal_surface.go` (51), `pr_observations.go` (62),
  `backend/internal/service/agent/readiness_coordinator.go` (720), `readiness.go` (264),
  `backend/internal/adapters/agent/activitystate/activitystate.go`, `backend/internal/domain/session.go`.
- Tests inspected: `backend/pkg/contract/status_test.go` (precedence tables),
  `backend/internal/service/agent/readiness_coordinator_test.go` (19 test funcs; invalidation,
  single-flight, purpose TTLs), `session/status_test.go`, `session/stack_test.go`,
  `domain/activity_test.go`, `adapters/chatdriver/claudeacp/checkpoint_test.go`.
- Patterns:
  1. **Pure derived status** (`pkg/contract/status.go:99-131`) — `DeriveStatus(sessionFacts, prs,
     now, grace)`; status is "derived from persisted facts and is never stored". Dependency-light
     package (`time` only). → **ADAPT** (shape + precedence discipline).
  2. **Fail-closed observation types** (`ports/terminal_surface.go:4-9`; `pr_observations.go`) —
     zero value = unknown so a partial input can never become positive evidence; `Fetched` gate:
     "when false the rest is meaningless". → **STEAL (idiom; types only)**.
  3. **Version-counter invalidation + purpose-specific freshness** (`readiness_coordinator.go:537-554`)
     — `installVersion`/`authVersion` counters + bitmask invalidation; in-flight checks are discarded
     if the entry version moved; display vs launch TTLs. → **ADAPT** (Kel: digest-revalidation and
     stale-supersede guards, not a 720-line coordinator).
  4. **Append-only observation accumulation, fail-closed on overflow**
     (`native_checkpoint.go:36-52`) — observations retained verbatim, duplicates dropped, overflow
     marks the evidence `Invalid` rather than evicting; a later older Stop cannot overwrite unknown
     newer state. Tests: `native_checkpoint_test.go`, `claudeacp/checkpoint_test.go`. → **ADAPT**.
  5. **Typed runtime metadata surviving boundaries** (`session.go:72-92`) — typed `SessionMetadata`
     (workspace path, diff base SHA, runtime handle, agent session id + launch-generation pinning).
     → **ADAPT** (generation-pinning idea; not the struct).
- Already in Kel: SQLite `events` (immutable snapshots, jobs as rebuildable projection); leases;
  broker adoption; `providers` health. Kel's job state already derives from events.
- Remaining gap in Kel: no *derived semantic status text* over job facts (candidate/continuation
  ranking needs it); no explicit fail-closed observation idiom at API boundaries; no version-counter
  stale-write guard for map/memory freshness.
- Verdict: ADAPT (derived status, invalidation counters, append-only observations), STEAL (fail-closed
  idiom), **AVOID** the readiness coordinator wholesale, the dozens of per-harness adapters, and any
  import of another orchestration runtime.
- Brief-premise correction: this repo has **no digest-based invalidation** for state (monotonic
  counters + TTLs only) and **no project-state snapshot/rebuild mechanism** located; Kel's
  digest-based revalidation must be designed from scratch.
- Dependency impact: none for the patterns (Go idioms); no code copying for now.

## 3. ephor/warpforge — durable parent/child work, wake semantics

- Repository: `ephor/warpforge`; revision `d8f3148d3adb` (2026-09-13) — unchanged since the V1 audit.
- License: MIT ("Copyright (c) 2026 warpforge contributors").
- Source files inspected: `src/daemon/backlog.rs`, `sessions.rs`, `attachment.rs`, `task.rs`,
  `handoff.rs` (warm/cold handoff documents), `workflow/run.rs`, `workflow/mod.rs`,
  `actor/workflow.rs` (restore/wake-parent), `actor/output.rs`, `Cargo.toml`.
- Tests inspected: `src/daemon/tests/workflow.rs` (21,996 B), `workflow_control.rs`, `sessions.rs`,
  `tasks.rs`, `lifecycle.rs`.
- Patterns:
  1. **Durable workflow run state restored on daemon start** (`workflow/mod.rs`,
     `actor/workflow.rs`) → **ADAPT**; caveat: no dedicated crash/restart test for
     `restore_workflow_runs` — Kel must test its own recovery.
  2. **Wake-parent on child completion** (`actor/workflow.rs`; `handoff.rs`; tests `tasks.rs`,
     `workflow.rs`) — the parent is woken via an inbox rather than polling a turn → **ADAPT**; the
     single most Kel-relevant mechanism.
  3. **Conversation↔session attachment** (`attachment.rs`, `sessions.rs`; tests `sessions.rs`) —
     new conversations attach to persistent sessions; work is not owned by a turn → **ADAPT**.
  4. **In-memory inbox** — spawn creates `HashMap::new()`; wake messages lost at crash → **AVOID
     as-is**; Kel's version must be a durable table (Kel already persists an `inbox` for run results;
     V1.3 adds wake/reminder entries).
  5. **Pause-on-blocked, never replay** (`workflow/run.rs`; `workflow_control.rs`) → **ADAPT**
     (resume-from-frontier discipline).
  6. **Handoff documents** (`handoff.rs`) — compacting a session into a fresh bounded packet rather
     than replaying transcripts → **ADAPT** (matches Kel's continuation packet requirement).
- Already in Kel: durable store + detached brokers + adoption after restart (`runner.py`),
  idempotent inbox, `context.handoff` bounded packets, pause/cancel semantics (`control`,
  `acknowledge_stop`).
- Remaining gap in Kel: no conversation→job attach path; no wake semantics for "parent job resumed
  from a new conversation"; no explicit continuation anchors.
- Verdict: ADAPT (wake/attach/restore semantics), AVOID (transport, PTY model, in-memory inbox).
- Dependency impact: none planned (Kel reimplements over its own store).

## 4. Chuzom/Chuzom — accepted milestones stay accepted

- Repository: `Chuzom/Chuzom`; revision `5041d169d630` (2026-08-29) — unchanged since V1 audit.
- License: MIT ("Copyright (c) 2026 LLM Router Contributors").
- Source files inspected: `src/chuzom/agentic/ledger.py` (freeze/frozen_context, done_ids,
  next_pending), `engine.py` (`_work_milestone` retry→escalate→BLOCK; `_run_and_verify` flaky
  branch; `_refuse_unisolated_irreversible`), `acceptance.py` (`diff_check`, `canary_check`,
  `validator_check`, `reproducible`, `reject_stubs`), `adapters.py` (frozen-context packing).
- Tests inspected: `tests/test_agentic_mgee.py` (S1–S16 incl. bounded-attempts→escalate, DAG sibling
  progress, 40-seed termination fuzz, "replan unreachable"), `tests/test_agentic_acceptance.py`
  (diff_check reads the repo not the claims; scoped to declared files; fails when repo invisible;
  flaky re-run), `tests/agentic/test_verification_soundness.py`,
  `agentic/test_escalation_bounds.py`, `test_agentic_adapters.py` (frozen context carried into
  escalation prompt), `test_agentic_worktree.py` (freeze reversibility rules).
- Patterns:
  1. **Frozen done-frontier** (`ledger.py:130-142`) — `freeze()` marks DONE with artifacts;
     `frozen_context()` gives a read-only view to escalated tiers; accepted milestones are never
     re-executed. → **STEAL** (small, MIT, stdlib; ~40 lines).
  2. **Resume-only-incomplete via DAG frontier** (`ledger.py:105-115`) — `next_pending()` returns
     the earliest READY PENDING milestone; BLOCKED siblings don't stop independent progress.
     → **STEAL**.
  3. **Bounded retry → monotonic escalation → terminal BLOCK** (`engine.py:213-247`) — K attempts
     per tier, then tier+1, then BLOCK; replan deliberately deleted. → **STEAL** (loop is small;
     Kel maps onto its attempts<4 + provider rotation).
  4. **Objective acceptance + flaky≠failure** (`acceptance.py`; tests) — checks run against the real
     repo; non-deterministic failures are re-run once and don't count toward attempts. → **STEAL**
     (result shape + flaky distinction), **ADAPT** (checks are Kel's own).
  5. **Do-nothing-oracle rejection + irreversible gate** (`engine.py:_verify`, `reject_stubs`).
     → **ADAPT** (Kel needs the same "self-supplied acceptance is refused" guard).
- Already in Kel: `revise()` invalidates only dependency-changed milestones and preserves ACCEPTED;
  repair prompts ("Repair only failures; preserve accepted work"); retry switches provider at
  attempts≥2; attempt cap 4. `test_v1.py` revise cases cover it.
- Remaining gap in Kel (critical): **no revalidation/invalidation on dependency or source change**
  once a milestone is accepted. Chuzom has the same hole: `grep 'invalidat|revalidat|stale|digest'`
  over `src/chuzom/agentic` = **zero matches** — a frozen milestone there is permanent regardless of
  upstream change. Kel's "revalidate only affected accepted milestones" + "explicit invalidation
  reasons" must be built new.
- Verdict: STEAL (freeze/frontier/escalation/acceptance-shape), ADAPT (reject-stubs guard).
- Attribution: MIT notice for any copied ledger/engine fragment.
- Dependency impact: stdlib; keep Kel's store as the persistence layer.

## 5. Orkas-AI/Orkas — one owner for coupled reasoning

- Repository: `Orkas-AI/Orkas`; revision `5f1be8f7062c` (2026-09-14).
- License: MIT (root). Vendored dirs: `vendor/whisper` (MIT, ggml/OpenAI), `vendor/whisper/openblas`
  (BSD-style "OpenBLAS Project" — different terms; outside Kel's reuse path).
- Source files inspected: `src/core-agent/src/agent/context-budget.ts` (derived budget),
  `tools/base.ts` (executor-owned timeout), `agent/runner.ts` (delegation + synthesis),
  `package.json`, `vitest.config.ts`.
- Tests inspected: `src/core-agent/test/context-budget.test.ts`, `memory-tool.test.ts`,
  `skill-inline-budget.test.ts`.
- Patterns:
  1. **Derived, model-relative context budget** (`context-budget.ts:1-90`) — message/trigger/retain
     budgets derive from the model window; `MIN_MESSAGE_SHARE` fuse prevents negative budgets; pure
     arithmetic, no I/O. Tests: `context-budget.test.ts`. → **STEAL** (ratios, not constants).
  2. **Executor-owned timeout** (`tools/base.ts`) — one owner for timeout lifecycle → **ADAPT**
     (coupled decisions stay with Kel).
  3. **Commander synthesis as a distinct step** (`runner.ts`) → **REFERENCE** (Kel's
     `combined-result` milestone already implements this).
  4. **Project memory read-only to workers** (memory tool + tests) → **ADAPT**.
- Already in Kel: `combined-result` synthesis milestone with one-voice prompt; worker prompts forbid
  delegation; handoff packets bounded at 32k chars.
- Remaining gap in Kel: no explicit context-budget model for the composer (V1.3 C4 must size
  packets to the consumer); no single named owner for timeout/budget policy per packet.
- Verdict: STEAL (budget arithmetic), ADAPT (timeout-owner, read-only memory to workers),
  REFERENCE (rest). No digest-invalidation in Orkas; no durable continuation (out of its scope).

## 6. microsoft/conductor — schema-validated deterministic workflows

- Repository: `microsoft/conductor`; revision `64b71675432c` (2026-09-11).
- License: MIT ("Copyright (c) Microsoft Corporation.").
- Source files inspected: `src/conductor/config/schema.py` (discriminated step unions; per-type
  forbidden fields; terminate fields at `:1902-1955`), `config/validator.py`
  (`validate_workflow_config`; terminal-node analysis), `engine/workflow.py`
  (terminate handling `:5367`, `_build_terminate_output` `:8165`, resume `:3303`),
  `engine/checkpoint.py:96-120` (versioned, hashed checkpoints), `cli/run.py`, `cli/app.py`,
  `engine/limits.py`, `event_log.py`.
- Tests inspected: `tests/test_config/test_schema.py` (TestTerminateAgent at `:2354`; parametrized
  forbidden-field rejections), `test_validator.py` (TestTerminateValidation at `:2745`),
  `tests/test_cli/test_run.py` (TestRunCommandTerminate at `:1054`; resume parity),
  `test_parallel_validation.py`, `test_workflow_type_schema.py`.
- Patterns:
  1. **Per-type forbidden-field enforcement** (`schema.py:376`, `:2072`, `:2641-2699`) — setting
     another step type's field is a hard error, not ignored. → **ADAPT** (recipe validator
     discipline; Kel's `validate_contract` gains the same explicitness).
  2. **Explicit termination as a first-class step** (`schema.py:1902-1955`; engine `:5367`,`:8165`)
     — `terminate` carries `status` (success|failed) + reason + optional output template; drives CLI
     exit codes and resume parity. Gap for Kel: conductor has **no uncertain terminal state** — Kel's
     recipes must add the third state (VERIFIED / FAILED / UNCERTAIN). → **ADAPT**.
  3. **Versioned checkpoint for resume** (`checkpoint.py:96-120`; `workflow.py:3303`) — version +
     workflow-file SHA-256 + current step + session ids; resume re-enters without resetting counters.
     → **ADAPT** (recipe version pinning analogue).
  4. **Sub-workflow reuse with depth/cycle guards** (`workflow.py:1274-1306`, `:2378`) → **REFERENCE**
     (Kel: recipes compose by compilation, never a nested executor).
- Already in Kel: deterministic compiled pipelines for coding/document/research; `validate_contract`
  (1–5 milestones, unique .md names, trusted check kinds only, cycle rejection); retry/settle
  semantics in `engine.py`/`core.py`.
- Remaining gap in Kel: no user-facing recipe layer; no recipe version pinning; no explicit
  terminate step (jobs end through assess/aggregate).
- Verdict: ADAPT (validation discipline, terminate semantics + Kel's third state, checkpoint
  versioning), REFERENCE (sub-workflows), **AVOID** the recursive runtime / visual DAG direction.
- Notes: `workflow.hooks` was removed upstream as never-effective (schema.py deprecation note) — do
  not resurrect hooks in Kel recipes.

## 7. pioneerdotai/pioneer — evidence, not truth; no self-certification

- Repository: `pioneerdotai/pioneer`; revision `b9afb60df7f6` (2026-09-14).
- License: MIT (root; "Copyright (c) 2026 Alexander Oskin"), **except** vendored
  `crates/sqlite/src/zstd/LICENSE` = LGPL-3.0 (unrelated to audited modules; do not touch/copy).
- Source files inspected: `crates/tasks/src/service.rs` (`validate_review_event_for_candidate`
  `:5363-5366` self-review ban; `:5367-5385` kind↔ref exactness), `tasks/src/review.rs:100-249`
  (resolution state machine), `tasks/src/actor_contract.rs`, `tasks/src/executor.rs`,
  `protocol/src/memory.rs:75-80`, `:142` (`MemoryEvidenceClass`; default `MissingOrWeak` at `:852`),
  `crates/memory/src/candidate_policy.rs:45-65` (contradiction policy), `quality_gate.rs`,
  `crates/crud/src/lib.rs:25411-25584` (blocked-only resume; retry generation; revision bump),
  `cli-agent-runtime/tests/codex_rollout_continuity.rs:121-149` (durable resume path across restart).
- Tests inspected: `tasks/src/tests.rs` (reviewer identity, two-reviewer flows),
  `tasks/src/review.rs:617-693` (five resolution strategies), `memory/src/candidate_policy.rs:953`
  ("contradiction never auto-approves even with high score"), `quality_gate.rs:1343`.
- Patterns:
  1. **Self-review is a hard error** (`service.rs:5363-5385`) — reviewer thread compared to
     candidate source thread; reviewer kind must match an exact ref. → **ADAPT**. (Gap noted: no
     positive test asserting the exact ban error text.)
  2. **Evidence classes with default-weak + contradiction-never-auto-approves**
     (`protocol/memory.rs:142`, `candidate_policy.rs:45-65`; tests) — every candidate carries
     `evidence_class` (DirectUserAssertion / UserCorrection / UserApproval / AssistantInference /
     ToolObservation / TaskRuntimeObservation); admission scores via candidate policy; a
     contradiction can never auto-approve even at high score. → **ADAPT** (the strongest single
     donor contribution to Kel's memory trust model).
  3. **Resumed work is re-driven under a new revision and re-reviewed** (`crud/lib.rs:25411-25584`)
     — only a Blocked run may resume; retry generation advances; occurrence → Recovering; revision
     bumped; actor contract re-derived; a stale/resumed job cannot close a Turn. → **ADAPT**.
  4. **Review resolution policy state machine** (`review.rs:104-130`; `service.rs:5387-5439`)
     → **REFERENCE** (Kel keeps allow/deny + executor≠reviewer).
- Already in Kel: `record_review` executor≠reviewer (run_id check), digest + contract-version
  guards, review prompt "You did not execute this task…". `test_review_recovery.py` covers recovery.
- Remaining gap in Kel: memory records need the evidence-class + default-weak + contradiction policy;
  resumed milestones must bump a revision and re-review (V1.3 continuation spec must make this
  explicit); worker output must never become memory without review.
- Verdict: ADAPT (self-review ban, evidence classes, revision-bumped resume review), REFERENCE
  (resolution machine). Attribution: MIT notice if any fragment is copied.

## 8. Adulari/forge — completion authority (AGPL, IDEAS ONLY)

- Repository: `Adulari/forge`; revision `39a63bb4762b` (2026-09-14).
- License: **AGPL-3.0** (LICENSE read: "GNU AFFERO GENERAL PUBLIC LICENSE / Version 3"). Confirmed.
  **No code copying — ideas and behavioral descriptions only.** (Correction to the V1 donor ledger,
  which used "STEAL (the principle)" language: the principle is reusable; the code is not. This
  audit records that distinction explicitly.)
- Source files inspected: `crates/forge-core/src/completion.rs` (VerificationLedger `:48-110`;
  pipefail/trust `:400-430`; completion gate `:461-530`), `src/lib.rs` (`run_completion_gate`
  `:2440-2508`; continuation guard `:1142-1210`), `stall_guard.rs:20-130`, `completeness.rs:11+`,
  `turn_contract.rs`, `session_lifecycle.rs`, `task_staleness.rs`.
- Tests inspected: `completion.rs:570-880` — `artifact_mutation_stales_old_evidence_until_a_new_check_passes`,
  `failed_typecheck_is_not_cleared_by_a_successful_file_read`,
  `failed_lint_test_and_build_each_require_a_matching_success`,
  `observational_work_never_requires_a_mutating_redrive`, `mutating_claims_are_challenged_then_evaluated_from_evidence`;
  `stall_guard.rs` tests (nudge/halt windows).
- Patterns (behavioral descriptions; ≤3-line anchors; no copying):
  1. **Verification ledger where a mutation stales prior evidence** — unresolved check families
     (typecheck/lint/test/build); a success clears only its own family; completion requires a
     success strictly newer than the last mutation checkpoint. → **ADAPT** (ideas only). The
     strongest match to "process exit is not completion".
  2. **Bounded completion gate** — an all-done claim is challenged up to N times, then accepted as
     explicitly UNVERIFIED rather than pretending success. → **ADAPT** (the third terminal state —
     Kel's UNCERTAIN).
  3. **Continuation guard** — continuation ≠ success: nudge/stop/accept decided from goal-verified,
     progress, budget, continuation count, token delta; stops spirals. → **ADAPT** (Kel's
     escalation/re-drive policy; thresholds are parameters, not constants).
  4. **Narration stall guard** → **REFERENCE** (bounds futile re-driving).
  5. **Self-review prompt** → **REFERENCE ONLY** — it is *self*-review, not independent
     certification; Kel must never count it as review (pioneer's ban applies).
- Already in Kel: `assess()` only produces completion records; evidence-bound checks; UNCERTAIN
  verdict exists; bounded attempts; `verification_summary`.
- Remaining gap in Kel: the *mutable evidence order* discipline (success must be newer than last
  mutation) is not modeled per-check today; Kel's coding checks run once at verify time. V1.3 adds
  digest/timestamped revalidation for resumed work.
- Verdict: ADAPT (ideas), REFERENCE (stall guard, self-review prompt). Attribution: N/A (no code).
- Risk: AGPL — any accidental copy would poison the product license; the audit must stay
  behavioral.

## 9. ryderderder/orchestrator — native session continuity

- Repository: `ryderderder/orchestrator`; revision `5bc35eb1432d` (2026-08-09) — unchanged since V1.
- License: MIT ("Copyright (c) 2026 Ryder Wolf"). Single ~7.2k-line script + tests; no vendored dirs.
- Source files inspected: `orchestrator` (`PROVIDER_SPECS` `:83-120`; `_extract_session_id`;
  `resume_argv` `:823-837`; `provider_auth_state`; `provider_state`; `codex_usage`/`claude_usage`;
  `_live_signal`; `reconcile` `:922-925`).
- Tests inspected: `tests/test_providers_registry.py` (session-id extraction top-level + nested;
  resume exact-UUID; refusal without id; custom `resume_args` validation), `test_orchestrator.py`
  (auth lattice incl. corrupt→unknown; ghost-usage never rendered; route excludes exhausted;
  `_fmt_reset`), `test_adapter_goldens.py` (argv goldens assert session id verbatim),
  `test_lead_config.py`.
- Patterns:
  1. **Declarative provider-spec registry** (`:83-120`) — argv/headless/resume/session_source/
     auth_files/probe as DATA, not if-chains; `session_source` declares how the id is recovered
     (stderr-regex with UUID check, JSON key lookup, fallback glob). → **STEAL/ADAPT** (pattern;
     Kel's `native.py` already carries per-provider argv; the declarative session_source field is
     the new idea).
  2. **Exact-session-only resume** (`:823-837`) — resuming "the most recent session" is banned
     (wrong session under concurrency); refusal when no id captured. → **STEAL** (discipline; Kel
     already passes `session_id` from `runs.native_session` — V1.3 must make the refusal explicit).
  3. **Auth-state lattice with honest "unknown"** — signed-in|signed-out|unknown|unprobed; corrupt
     artifacts are reported as unknown, never guessed; empty JSON is NOT a login. → **STEAL/ADAPT**
     (Kel `telemetry.py` reads Codex quota; extends to auth truthfulness).
  4. **Quota windows auto-expire** (`_live_signal`) — exhausted signal derived from native usage
     windows with `resets_at`; provider with nothing to read stays "quiet", stated not faked.
     → **STEAL/ADAPT** (Kel already reads `rateLimitsByLimitId`; adds the auto-expiry + honest
     quiet state).
  5. **Resurrect honesty** (`reconcile`; `test_resurrect.py`) — never resume interactive sessions;
     records lost teammates instead of maintaining a parallel manifest. → **ADAPT/REFERENCE**.
- Already in Kel: `native.py` codex/claude CLI adapters with session capture; `appserver.py`
  `thread/resume`; `engine._execute` sticky provider + prior session; `telemetry.refresh_codex`.
- Remaining gap in Kel: explicit session-validity check + "recreate bounded context when invalid";
  no quoted/quarantined session-id guards (Kel must validate UUID shape before resuming).
- Verdict: STEAL/ADAPT. Attribution: MIT notice if any fragment is copied.
- Note: no worker iteration/token budgets here (that is xopc's contribution).

## 10. xopcai/xopc — bounded leaf workers

- Repository: `xopcai/xopc`; revision `2c574271d39b` (2026-09-15).
- License: MIT ("Copyright (c) 2026 xopcai").
- Source files inspected: `src/agent/tools/delegate-tool.ts` (allowlist + denylist `:11-34`),
  `src/agent/child-agent-factory.ts` (real budget enforcement), `workflow/subagent-runner.ts`,
  `workflow/structured-output-tool.ts`, `routing/session-key-utils.ts`, `tools/exec-command.ts`.
- Tests inspected: `src/agent/tools/__tests__/delegate-tool.test.ts` (a reviewer cannot be granted
  write/shell tools; blocked names stripped), `workflow/__tests__/tool-restrictions.test.ts`
  (empty toolset preserved, no default fallback), `agent-progress.test.ts` (iteration counting),
  `agent/__tests__/structured-output.test.ts`.
- Patterns:
  1. **Hard budgets enforced in the child factory** — 60 tool calls / 100k tokens / ≤300s per
     child, enforced at authorize-time (`toolIterations >= limit || tokens >= 100_000` blocks with
     terminate). → **STEAL** (idea; Kel's `internal.py` has iteration+timeout; V1.3 adds explicit
     token accounting to packets).
  2. **Default-allowlist + explicit denylist, per mode** — reviewers get inspection tools only; a
     requested set can never include blocked names; empty permitted set throws. → **STEAL**.
  3. **Structured output as a mandatory terminating tool with re-validation** — invalid args return
     an error without terminate (retry allowed); never calling it = failure → null. → **STEAL**
     (shape; Kel uses `submit_result` similarly — add "missing call = failure" test).
  4. **No nested delegation via omitted tool** — `delegate_task` is in the blocked set for children.
     → **REFERENCE** (Kel also omits delegation tooling; goose adds the belt-and-braces check).
- Already in Kel: `internal.py` bounded worker (2 allowlisted tools, max iterations, 90s timeout,
  structured result); native argv hardening; worker prompts forbid delegation.
- Remaining gap in Kel: per-worker token budget; mode-based toolset refusal at the boundary; "empty
  permitted set" hard failure.
- Verdict: STEAL (budgets, allow/deny, structured-output strictness). Caveats: budget is per-child
  not globally capped; the denylist is manual (drift risk); one dead config path noted upstream.

## 11. block/goose — recursion and session discipline (maturity bar)

- Repository: `block/goose`; revision `a23a8cd5b138` (2026-09-14).
- License: Apache-2.0 (root LICENSE; `deny.toml` present for dependency licenses; `vendor/` license
  not fully read).
- Source files inspected: `crates/goose/src/agents/subagent_handler.rs`,
  `subagent_task_config.rs` (`DEFAULT_SUBAGENT_MAX_TURNS = 25`), `platform_extensions/summon.rs`
  (`:2164` conditional delegate tool; recursion refusal), `agents/agent.rs` (`:85`
  `DEFAULT_MAX_TURNS = 1000`; `:435-460` subagent hook isolation),
  `agents/reply_parts.rs` (tool visibility), `permission/permission_store.rs`
  (context-hash + expiry permission records).
- Tests inspected: inline tests in `summon.rs` (zero max_turns rejected; recipe>env>default
  precedence; notification sinks isolate concurrent delegates), `subagent_handler.rs`,
  `acp/server/tool_notifications.rs`.
- Patterns:
  1. **Defense-in-depth refusal of recursive delegation** — the delegate tool is not even listed to
     a `SessionType::SubAgent`, and a call-time check returns "Delegated tasks cannot spawn further
     delegations". → **ADAPT/REFERENCE** (Kel: keep the refusal in worker prompts and add the
     call-time guard test).
  2. **Bounded subagent turns with configuration precedence** (recipe > env > default 25; main
     session default 1000). → **ADAPT**.
  3. **Typed subagent sessions + isolated hooks** (default HookManager; per-child logger
     `subagent:<id>`; parent_session_id). → **REFERENCE**.
  4. **Persisted permission decisions keyed by tool + argument-context hash + expiry** → **ADAPT**
     (Kel's grants are digest-based per project; the argument-context keying is an idea for
     future reuse — not scheduled for V1.3).
- Already in Kel: no agent-spawn tooling; worker prompts forbid delegation; bounded concurrency
  (2 active runs); ACP agent registry locked to single Kel agent.
- Remaining gap in Kel: no *typed* worker session concept beyond runs; no global fan-out ceiling
  beyond concurrency=2 (acceptable); recursion refusal is prompt-level in places — add call-time
  checks where a code path could spawn.
- Verdict: REFERENCE (maturity bar, patterns), ADAPT (recursion refusal, turn bounds).

## 12. agentscope-ai/CoPaw (ex-QwenPaw) — ACP session/permission mechanics (reference)

- Repository: `agentscope-ai/CoPaw`; revision `0b8a12f55180` (2026-09-14). Tier-4 reference — Kel
  already adopted the ACP mechanics in V1; this audit re-checks current practice.
- License: Apache-2.0 (root; sub-packages not exhaustively license-read — UNCERTAIN for
  `packages/qwenpawmail-mcp/`, `plugins/`, `console/`).
- Source files inspected: `src/qwenpaw/agents/acp/service.py` (per-(chat,agent) binding + turn
  lock; `resume_permission`), `agents/acp/permissions.py` (`_is_hard_blocked`);
  `agents/acp/core.py:33` (`SuspendedPermission` dataclass); call sites of client/server/session_mcp.
- Tests inspected: `tests/unit/agents/acp/test_acp_service.py` (process-tree kill; service
  registry; prompt blocks), `test_tool_adapter_rendering.py` (permission-request rendering;
  closed/no-bound-session messages). **No unit tests exist for `permissions.py`** — CONFIRMED.
- Findings relevant to Kel:
  1. Per-`(chat_id, agent)` conversation binding with an explicit `turn_lock`; refuses a new turn
     while one is in flight or while a permission is pending. → REFERENCE/ADAPT (Kel: ACP host
     supersede semantics from V1 drift fix D-02 remain correct for Kel's single-assistant model).
  2. Permission suspension/resume as an explicit resumable state machine
     (`SuspendedPermission` → `resume_prompt` → `resolve_permission(option_id)` with liveness
     checks). → mirrors Kel's existing approvals; REFERENCE.
  3. Fail-closed session-cwd-scoped hard blocks (`is_command_destructive`, `is_path_outside_boundary`)
     with a documented accepted false-positive tradeoff. → REFERENCE (maturity for Kel's approval
     policies).
  4. **Real gap Kel must not copy**: CoPaw keeps sessions + pending permissions **in memory only**;
     a crash loses a suspended permission; and `permissions.py` has no tests. Kel persists approvals
     in SQLite (correct design; V1.3 proves it across restart in the acceptance matrix).
- Verdict: REFERENCE. Do not copy; do not regress Kel's durable approvals to an in-memory model.

## 13. Tier 4 — Aion Donor Shell & KellShell (keep stable; do not deepen)

- `iOfficeAI/AionUi` fork (`work/aion-donor`, origin `https://github.com/iOfficeAI/AionUi.git`,
  HEAD `6744099` + local uncommitted Kel modifications; Apache-2.0). V1.2 rebuilt only
  `out/renderer` and repacked with the dedup/integrity pipeline. V1.3 uses it only for existing
  Work-context UI surfaces (memory/map/continuation/recipe presentation) and app-shell primitives.
  Do not deepen Kel's conceptual dependency on Aion; do not touch donor agent/team UX.
- `iOfficeAI/AionCore` (KellShell): bundled stock `aioncore.exe` v0.2.2 (Apache-2.0) + source
  snapshot `work/aion-core-source`. Keep as conversation transport / ACP host plumbing. V1.3
  project memory and continuation authority must NOT move into KellShell.
- QwenPaw reference: see CoPaw above (ACP session/permission mechanics already adopted in V1.1–V1.2).

## 14. Historical donors carried from V1 (no new inspection)

- `orthogonalhq/nous-core` — AGPL: **ideas only, never code**. Cognitive layering / evidence and
  lifecycle separation concepts already reflected in Kel's layering. Unchanged V1.3 status.
- `eric-cielo/moflo` — learned routing: **AVOID** (V1.3 Out-of-Scope list repeats this).
- `use-agent-os/agent-os` — local classification idea adopted in V1 (`router.classify` now live).
  AVOID recursive delegation (V1.3 repeats).
- `Potarix/agent-hub` — CLI control/preserving native auth: context already reflected in
  `kel/native.py`. No V1.3 change.
- AionUI agent-team paradigm — **AVOIDED** (assistants disabled except Kel); V1.3 preserves.

## 15. Summary table

| # | Donor | Revision | License | Verdict | V1.3 use |
|---|-------|----------|---------|---------|----------|
| 1 | hermes-agent | 40f2702b | MIT | STEAL/ADAPT | memory seam shape; fence+sanitize; scope/rebind; provenance metadata |
| 2 | agent-orchestrator | 768ab503 | Apache-2.0 | ADAPT/STEAL | derived status; fail-closed idiom; version-counter invalidation; append-only observations |
| 3 | warpforge | d8f3148d | MIT | ADAPT | wake/attach/restore semantics; durable (not in-memory) inbox; pause-not-replay |
| 4 | chuzom | 5041d169 | MIT | STEAL | frozen frontier; resume-incomplete; bounded retry + monotonic escalation; acceptance shape |
| 5 | orkas | 5f1be8f7 | MIT | STEAL/ADAPT | derived context budget; timeout owner; read-only worker memory |
| 6 | conductor | 64b71675 | MIT | ADAPT/REF | per-type field validation; terminate step (+Kel's UNCERTAIN); versioned checkpoints |
| 7 | pioneer | b9af60df | MIT* | ADAPT | self-review ban; evidence classes; default-weak; revision-bumped resume review |
| 8 | forge | 39a63bb4 | **AGPL-3.0** | ADAPT (ideas) | mutation-stales-evidence ledger; bounded completion gate; continuation guard |
| 9 | ryderderder | 5bc35eb1 | MIT | STEAL/ADAPT | exact-session-only resume; auth lattice; quota auto-expiry; honest unknown |
| 10 | xopc | 2c574271 | MIT | STEAL | hard worker budgets; allow/deny toolsets; structured-output strictness |
| 11 | goose | a23a8cd5 | Apache-2.0 | REFERENCE/ADAPT | recursion refusal defense-in-depth; turn bounds; subagent session typing |
| 12 | CoPaw | 0b8a12f5 | Apache-2.0 | REFERENCE | ACP semantics; durability gap (do not copy in-memory permissions) |
| 13 | AionUI/AionCore | 6744099 / v0.2.2 | Apache-2.0 | keep stable | UI surfaces + transport only |

\* MIT root; LGPL-3.0 vendored zstd dir excluded from any reuse.

## 16. Cross-cutting conclusions (decision-grade)

1. **The V1.3 memory layer is mostly new construction.** No donor implements project-scoped,
   provenance-typed, supersession-based memory with review-gated admission. The donor value is
   *shape* (hermes interface/fences; pioneer evidence classes; agent-orchestrator fail-closed
   observations) — not transplantable subsystems.
2. **Milestone freeze exists in Kel; invalidation does not.** Chuzom (the freeze donor) also lacks
   digest/dependency revalidation; Kel V1.3 must build invalidation with explicit reasons as new,
   tested behavior.
3. **Continuation needs durable wake/attach semantics.** Warpforge supplies the semantics; its
   storage is in-memory. Kel already has a durable store + broker recovery, so V1.3 adds
   conversation→job links and a wake path, not a second scheduler.
4. **Recipes are a compilation layer, not a runtime.** Conductor teaches validation and termination;
   Kel compiles recipes into existing CompletionContracts and keeps the existing scheduler,
   store, verification, and publication paths. No DAG editor, no second engine.
5. **Trust boundaries from V1 stay intact.** Executor ≠ reviewer, assess-only completion, evidence-
   bound checks, and reviewer-diversity preferences remain; V1.3 strengthens the *memory* side with
   evidence classes and never lets worker output self-certify.
6. **License position is clean for MIT/Apache code with notices; forge is AGPL (ideas only);
   hermes/pioneer vendored subdirs need per-file checks before any copy.**

## 17. Attribution & notice requirements (before any copy)

- Maintain `THIRD_PARTY_NOTICES` (or extend `NOTICE.txt`) listing, per donor: repository URL,
  commit sha, license text inclusion (MIT: copyright line + permission text), and the Kel files
  containing adapted/copied material.
- Apache-2.0 donors (agent-orchestrator, goose, CoPaw): verify NOTICE obligations (§4(d)) and
  include attribution; no trademark use implied.
- AGPL donor (forge): no code, no notice needed; keep behavioral descriptions only.
- Every STEAL/ADAPT item must ship with tests covering the adopted behavior (per the brief).

## 18. Dependency impact

No V1.3 donor item requires a new runtime dependency. All STEAL candidates are stdlib-only Python
hermes fences/regex, chuzom ledger logic, orkas budget arithmetic) or idioms/types in other
languages that will be reimplemented in stdlib Python inside Kel. The engine stays stdlib + sqlite.
