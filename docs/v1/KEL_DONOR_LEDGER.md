# KEL V1 — DONOR LEDGER

License findings: every donor subsystem Kel actually adopted (AionUI, AionCore) is Apache-2.0; the Kel engine itself is original Python (Kel-Prototype). No AGPL code was transplanted. AGPL donors (Nous/NueOS) were used for architectural ideas only, as the brief requires.

Columns: Repository · License · Subsystem · Exact source area · Pattern worth adopting · Current Kel equivalent · Gap · STEAL/ADAPT/REFERENCE/AVOID · Implementation notes.

---

## 1. iOfficeAI/AionUi (AionUI) — the engineering donor for the desktop shell

- **Repository**: `work/aion-donor` (fork of iOfficeAI/AionUi, commit-level fork used to build the 0.5.0 app; `packages/desktop/`)
- **License**: Apache-2.0 (`AionUI-LICENSE.txt` in the package, `package.json` license field)
- **Subsystem**: entire desktop shell — main process, renderer, pet, WebUI bridge, storage, i18n, settings, tray, auto-updater
- **Exact source area**: `packages/desktop/src/process/{services,pet,bridge,backend,startup}`, `src/renderer/components/{layout/Sider,chat/MessageList,KelWorkPanel}`, `src/common/`
- **Patterns worth adopting (and Kel's status)**:
  1. **Main-process service layering** (`process/services/*`): backend lifecycle, database, tray, auto-updater separated into services with explicit init ordering. **Kel**: keeps this structure; the Kel glue lives in its own `services/kel/KelService.ts` — clean seam. **ADAPT — correctly implemented.**
  2. **Pet state machine** (`process/pet/petManager.ts`, 691 lines): a second always-on-top transparent window whose states are driven by chat stream events; permission bubbles via `petConfirmManager`. **Kel**: shipped as-is (pet present in the Kel package). Gap: pet states are driven only by AionCore stream channels, not by Kel engine job events — a cosmetic gap, documented in the drift audit (D-07/P3). **ADAPT — kept, not expanded.**
  3. **Conversation/history plumbing** (`chatLib`, `MessageList`): message model with `acp_tool_call` row projection. **Kel**: reuses it; the Kel bridge re-projects engine verdicts onto stale tool-call rows (`KelService.reconcile`). **ADAPT — correctly implemented.**
  4. **IPC boundary discipline**: single preload surface with allow-listed channel handlers and sender-frame checks. **Kel**: extends it with `kelAPI` (request/history/conversation/historySearch), each handler validating `senderFrame` + `file:` origin and the request route against a regex allowlist. **ADAPT — correctly implemented, security preserved.**
  5. **What Kel deliberately does NOT adopt**: the visible multi-agent paradigm (agent management UI, team visibility, assistant pickers). Kel disables every assistant except `kel` at startup and keeps the orchestration in the engine. The Settings screens that still show agent concepts remain as donor UI — documented limitation (D-09/P2), not copied paradigm.

- **Current Kel equivalent**: the shipped `app.asar` is this fork built with `kel-runtime-builder.json` (appId `com.kel.desktop`, productName Kel).
- **Gap**: none architectural; see the two documented UI limitations.
- **Verdict**: **ADAPT** (engineering patterns) / **AVOID** (multi-agent presentation paradigm).

## 2. iOfficeAI/AionCore — backend runtime donor (bundled binary v0.2.2)

- **Repository**: `work/aion-core-source` (source snapshot) + `resources/bundled-aioncore/win32-x64/aioncore.exe` (stock download, unmodified)
- **License**: Apache-2.0 (`AionCore-LICENSE.txt`)
- **Subsystem**: conversations, assistant management, agent management (ACP agents), message persistence, WebUI backend
- **Exact source area**: `crates/aionui-conversation/src/{service.rs,runtime_state.rs}`, `crates/aionui-ai-agent/src/factory/acp.rs`, `crates/aionui-assistant/`
- **Patterns worth adopting**:
  1. **ACP as the agent integration boundary**: Kel registers itself as a custom ACP agent (`/api/agents/management`, `--acp --data <root>`); AionCore owns the chat transport and native message store. **Kel**: implemented in `KelService.ts` + `kel/acp_host.py`. **ADAPT — correctly implemented.**
  2. **Per-conversation runtime state** (`runtime_state.rs`, `is_processing`): the shell knows when a conversation turn is in flight. **Kel**: the reconcile loop skips native rows while `is_processing` to avoid racing the stream. **ADAPT — correctly implemented.**
  3. **Assistant enablement as product policy**: all non-Kel assistants are disabled at startup — the one-assistant enforcement point at the backend layer. **ADAPT — correctly implemented.**
- **Current Kel equivalent**: stock AionCore 0.2.2, config-managed by `KelService`.
- **Gap**: AionCore serializes per-conversation turns; the ACP adapter is where Kel must implement side-question concurrency (drift D-02, fixed in this pass).
- **Verdict**: **ADAPT** (runtime as-is) / **AVOID** (none — no AionCore fork is maintained).

## 3. Orkas-AI/Orkas — Commander philosophy donor

- **Repository**: `work/` JSON audit + source review (donor_sources.py archive)
- **License**: audited for pattern use only; no code copied
- **Subsystem**: `src/main/prompts/chat_commander.md`
- **Pattern worth adopting**: "Keep coupled reasoning with one owner. Delegate only cleanly separable work." Kel's Commander compiles bounded document jobs (1–3 milestones + combined-result synthesis milestone) and never decomposes coupled reasoning across workers. **ADAPT — the principle is baked into `kel/commander.py`.**
- **Current Kel equivalent**: `kel/commander.py` (`plan`, `review`, `compile_document`, template fallback).
- **Gap**: Commander scope is document-shaped; coding/research use deterministic compilers instead of the Commander. Documented V1 limitation (Skeleton A: PARTIAL).
- **Verdict**: **ADAPT** (principle).

## 4. Adulari/Forge — Completion Authority donor

- **Repository**: `work/` JSON audit (Adulari_forge.json)
- **Pattern worth adopting**: "A process exiting is not proof that the task is done." Completion is evidence-based, never worker self-reported.
- **Current Kel equivalent**: `kel/core.py` — only `assess()` produces assessment rows; worker results are inbox events; `aggregate()` maps milestone verdicts to VERIFIED/FAILED/UNCERTAIN; `publish()` writes the single Kel-voice reply.
- **Gap**: none material for V1.
- **Verdict**: **STEAL** (the principle, reimplemented in Kel's own store).

## 5. XOPC (xopcai/xopc) — bounded leaf workers donor

- **Pattern worth adopting**: tool allowlists, token/time/iteration budgets, structured child output, persistent hidden worker transcripts, partial/failure semantics.
- **Current Kel equivalent**: `kel/internal.py` (InternalAdapter — two allowlisted tools `read_context`/`submit_result`, max iterations, timeout, structured artifact); `kel/native.py` (hardened CLI argv); `kel/coding.py` (bounded turn with phase machine). Worker transcripts persist in `runs`/`brokers`.
- **Gap**: none material.
- **Verdict**: **STEAL** (pattern, original implementation).

## 6. QwenPaw — ACP external-agent runtime donor

- **Pattern worth adopting**: ACP agent session lifecycle, permission suspension/resume, per-chat worker binding.
- **Current Kel equivalent**: `kel/acp_host.py` (session/new→mapped conversation, session/load replay, prompt loop, session/cancel → job cancel) + `kel/coding_transport.py` (durable native RPC with replay protection) + `kel/appserver.py` CodexConnection (thread/resume, turn/start, approval policy `on-request`).
- **Gap**: engine approvals were surfaced only as passive text in the ACP stream (fixed in this pass: D-03).
- **Verdict**: **STEAL** (pattern).

## 7. AgentOS (use-agent-os) — local initial classification donor

- **Pattern worth adopting**: cheap/local initial classification before expensive routing.
- **Current Kel equivalent**: `kel/router.py` `classify()` (status/document/conversation with confidence) + `research.needs_research()` + inline verb checks in `service._plan`. Drift: `classify()` was dead code (fixed: D-04 wires it into `submit`).
- **Verdict**: **ADAPT** (repaired in this pass). AVOID: AgentOS recursive delegation — not inherited (matches brief).

## 8. ryderderder/orchestrator — vendor CLI + subscription headroom donor

- **Pattern worth adopting**: real vendor CLI usage, exact session capture/resume, subscription headroom, provider readiness/auth state.
- **Current Kel equivalent**: `kel/native.py` (codex/claude CLIs, stream-json parsing, session_id/cost capture), `kel/telemetry.py` (`refresh_codex` — rateLimitsByLimitId, percent_remaining, planType, quota), `kel/router.py` quota filter.
- **Gap**: none material.
- **Verdict**: **STEAL** (pattern).

## 9. Untrivial-ai/agent-orchestrator — durable job lifecycle donor

- **Pattern worth adopting**: observation → durable facts → derived status; worktree isolation; CI/review state; durable chat/runtime metadata.
- **Current Kel equivalent**: `kel/core.py` events table (immutable snapshots, jobs as rebuildable projection), runs/leases, `kel/coding.py` git-snapshot isolation + baseline tests, `kel/runner.py` detached brokers with heartbeats, `kel/context.py` handoff packets.
- **Verdict**: **STEAL** (pattern; strongest donor in the brief, matched well).

## 10. Chuzom — milestone acceptance + freeze donor

- **Pattern worth adopting**: acceptance checks against real repository state, freeze passed milestones, bounded retry, monotonic escalation.
- **Current Kel equivalent**: `kel/core.py` `verify()` (evidence-bound checks, artifact digests), ACCEPTED milestones preserved by `revise()` (only dependency-invalidated milestones revert), repair prompts ("Repair only failures; preserve accepted work"), retry switches provider at attempts≥2 (`engine.tick`), attempt cap 4.
- **Verdict**: **STEAL** (pattern).

## 11. Pioneer (pioneerdotai) — evidence review donor

- **Pattern worth adopting**: "Child results are evidence until the parent reviews and accepts them"; reviewer before adoption.
- **Current Kel equivalent**: `kel/core.py` `record_review` trusted-reviewer boundary ("Executor cannot serve as independent reviewer" enforced by run_id check), reviewer receives source request + fixed rubric + artifact, not the creator's narrative.
- **Gap**: reviewer and planner share one model key in V1 (documented limitation D-05).
- **Verdict**: **STEAL** (pattern).

## 12. Warpforge (ephor) — async parent/child + inbox donor

- **Pattern worth adopting**: parent inbox, worker wake-up event model, persistent work independent of conversation turn.
- **Current Kel equivalent**: `kel/core.py` inbox (idempotent consumption), `kel/engine.py` tick supervision thread, `kel/runner.py` broker adoption after restart.
- **Verdict**: **STEAL** (pattern).

## 13. Goose (block) — maturity reference; anti-recursive-delegation

- **Pattern worth adopting**: provider/session infrastructure maturity; preventing delegated agents from recursively spawning agents.
- **Current Kel equivalent**: worker prompts explicitly forbid delegation ("Do not call tools, create agents…"); CodexConnection developer instructions disable delegation; only `internal` and native CLIs exist — no agent-spawn tooling. Audit block record exists (`block_goose.json`).
- **Verdict**: **REFERENCE** (maturity bar), rule **ADAPTED**.

## 14. Hermes (NousResearch) — memory provider abstraction

- **Pattern worth adopting**: memory provider abstraction, context staging.
- **Current Kel equivalent**: `kel/context.py` — projects/conversations/attachments/handoff packets/grants, provenance-aware and bounded. V1 scope is intentionally narrower than Hermes' plugin architecture.
- **Verdict**: **REFERENCE** (selective for V1).

## 15. Microsoft Conductor — deterministic workflows

- **Pattern worth adopting**: schema validation, parallel execution, explicit success/failure termination — without becoming the Commander.
- **Current Kel equivalent**: `kel/core.py` `validate_contract` (schema + dependency cycles + allowed check kinds), `kel/coding.py` deterministic pipeline (snapshot → turn → baseline+post tests → diff digest → review), `kel/commander.py` deterministic validation of model proposals.
- **Gap**: no user-defined recipe/DAG layer (documented V1 scope decision).
- **Verdict**: **ADAPT** (validation + termination semantics).

## 16. Nous/NueOS (orthogonalhq) — cognitive layering reference

- **License**: AGPL → **no code transplanted**; architectural ideas only.
- **Ideas**: cognitive layering, evidence/witness concepts, escalation and lifecycle separation — already reflected in Kel's Commander/engine/store layering.
- **Verdict**: **REFERENCE** (ideas only; AGPL boundary respected).

## 17. Potarix agent-hub / MoFlo (eric-cielo)

- **Potarix**: controlling real installed CLI agents, preserving native auth — reflected in `kel/native.py` (no shell wrappers, native CLI processes with scrubbed env). **ADAPT.**
- **MoFlo**: outcome-aware learned routing with feedback loops — treated skeptically per brief; Kel V1 uses deterministic outcome tracking (`routing_outcomes`) rather than learned routing. **REFERENCE / AVOID for V1.**

## 18. AionUI → Kel: engineering-pattern summary (what the brief requires be explicit)

| AionUI pattern (source) | Kel status |
|---|---|
| Service-layered main process (`process/services/*`) | ADAPTED — Kel glue in `services/kel/` |
| IPC preload allowlists + sender-frame checks | ADAPTED — `kelAPI` with route regex + frame checks |
| Pet state machine (`pet/petManager.ts`) | ADAPTED as-is (cosmetic gap: not driven by Kel job events) |
| Message model + tool-call row projection | ADAPTED — engine verdicts re-projected over tool-call rows |
| Arco-based drawer work surface | ADAPTED — `KelWorkPanel.tsx` (jobs/approvals/apply/artifact download) |
| Visible agent-team paradigm | **AVOIDED** — assistants disabled except Kel |
| WebUI bridge + PWA | ADAPTED for the engine's own web UI (`kel/web`, served by the engine) |
