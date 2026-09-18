# KEL_CANONICAL_ROADMAP_R2_5 — the forward authority for V1.6

adopted: 2026-09-18 · status: ACTIVE · supersedes nothing (historical phase docs remain evidence)
owner: autonomous Main / Program Director (single writer; `AUTONOMOUS_OPERATION.md`)
base: Main `ae4c5b0` (docs tip) / `84b5646` (production tip), `ux/v15-journeys`, clean, in sync
source: Round 2.5 ecosystem reconciliation (repo-grounded audit) + the 2026-09-18 sprint directive

**Repository truth beats this document.** If disk/git contradicts a line here, the disk wins and this
file is corrected. This roadmap governs what happens NEXT; it never rewrites what was built.

## 0. Strategy (unchanged, restated once)

> IMPLEMENT EVERYTHING FIRST. BUILD PERFECT BREADCRUMBS. CREATE PRE_AUDIT_V1_6_HEAD. THEN STOP.
> CAMPAIGN B WILL PERFORM THE 100% INDEPENDENT AUDIT. CAMPAIGN C WILL PERFORM THE 100% REPAIR.

- Incremental independent audit cycles stay **PAUSED** (`audit_mode: PAUSED_UNTIL_PRE_AUDIT_RC`).
- Ordinary engineering quality control is **mandatory** (self-review, focused tests, full regression,
  packaged verification, atomic commits, corpus updates in the same arc).
- Nothing in this roadmap may present Campaign A evidence as independently accepted
  (`INV-AUDIT-001`).

## 1. Product North Star

> ONE CAPABLE ASSISTANT WITH HIDDEN ORCHESTRATION.
> LARGE BENCH. SMALL MISSION TEAM. CENTRAL COMMAND. INDEPENDENT VERIFICATION.

Users control goals, meaningful decisions, model/capability preferences, meaningful memory and
approvals. Users never need to understand workers, agents, leases, runtimes, queues, staffing graphs,
orchestration topology, MCP plumbing, or internal event streams. **Round 2.5 must not turn Kel into
an agent cockpit.**

## 2. Round 2.5 verdict

Kel's fundamental architecture is sound. **Do not pivot. Do not rewrite. Do not create duplicate
authority, memory, workflow, recovery, evidence, or orchestration systems.** Round 2.5's value is
converting distributed safety behaviour into explicit constitutional invariants with adversarial
coverage before V1.6 freezes.

Not invalidated: durable work engine · contracts · completion packets · capability leases ·
provider/model routing · Workforce OS · memory architecture · evidence-bound completion · independent
verification · continuation/recovery · worktree isolation · D0–D4 staffing.

### Dispositions (hypotheses, validated against repository truth)

| # | Topic | Disposition | Where |
|---|---|---|---|
| A | Delegation authority ceiling | **ADOPT** — extend the existing authority system; `child_effective ⊆ delegator_effective`; delegation may narrow, never create | R1 |
| B | Logical-work / idempotency | **ADOPT** — one explicit matrix over existing primitives; fill only real gaps; no second queue/event framework | R2 |
| C | Retry budgets survive restart | **ADOPT** — audit every autonomous retry class; persist only where restart could reset a loop | R3 |
| D | Canonical approval binding | **ADOPT + MERGE APR-02** — approval authorizes one exact normalized action; re-prove immediately before execution | R4 |
| E | Persistence integrity | **ADOPT** — system invariant + adversarial/property tests; do not rewrite storage | R5 |
| F | Truthful runtime state | **ADOPT (invariant only)** — `IDLE/WAITING/PROCESS-ALIVE ≠ COMPLETED`; no universal enum | R6 |
| G | Liveness separation | **ADOPT** — `process alive ≠ supervisor healthy ≠ mission progressing` | R6 |
| H | Host-held credentials | **PROVE THE BOUNDARY** — no generic credential-proxy platform in V1.6 (post-V1.6 research) | R7 |
| I | Network-aware sandbox | **REJECT for Campaign A** — record `host_runtime.py` as user-authorized high-authority native execution, not a sandbox | R7 |
| J | Memory provenance | **ALREADY COMPLETE** — verify and keep; no new memory system | R6/R12 |
| K | Resumption briefs | **ALREADY SOLVED** — Continuation/open-work machinery; reuse | — |
| L | Deterministic procedures | **ALREADY SOLVED** — Recipes compile into the existing engine; no second workflow runtime | — |
| M | Execution receipts | **STRENGTHEN TESTS ONLY** — effect ids/digests/receipts exist; no HMAC-everything without a real threat gap | R5/R6 |
| N | Needs Your Attention | **ADOPT FOR V1.6** — derived-only aggregation over existing durable state | R9 |
| O | Trust-tainted execution | **RESEARCH ONLY** (post-V1.6) | — |
| P | Capability revision snapshots | **CLARIFY INVARIANT** — config changes never silently widen running work; user revocation may narrow immediately | R1/R6 |
| Q | Narrow runtime ABI | **RESEARCH ONLY** unless current code shows costly coupling; no elegance rewrite | — |
| R | Public A2A | **REJECT** (no V1.6 need) | — |
| S | Complex memory platform | **REJECT** (knowledge graph / autonomous memory agents / universal vectors) | — |

## 3. Campaign A critical path

```
R0  finish P2/P3 sweep          → every historical row has a final evidence-backed disposition
R1  delegation authority ceiling
R2  logical-work / idempotency invariant
R3  durable retry / recovery budgets
R4  canonical approval binding        (absorbs APR-02)
R5  persistence integrity contract
R6  truthful state + liveness          (absorbs RECOVERY-CLASSIFICATION, LIVE-AUTHORITY proof)
R7  credential / network boundary confirmation
R8  packaged / migration assertions   (REQ-PKG-ASSERT + REL-01 evidence)
R9  Visual batches 6–8 + Needs Your Attention
R10 engine-loss / recovery UX         (absorbs TR-02 where it fits; restore-outcome surface)
R11 Visual → Main integration
R12 final Campaign A regression
    → PRE_AUDIT_V1_6_HEAD  → STOP Campaign A
```

Then: **Campaign B** 100% independent audit → **Campaign C** 100% repair → re-audit → human visual →
final product review → release/freeze.

## 4. Phase contracts

### R0 — finish the P2/P3 sweep
Every row in `P2_P3_DISPOSITION.md` ends with one of: **FIXED · STALE · NOT_APPLICABLE ·
DEFERRED_NON_RELEASE · OPEN_RELEASE_BLOCKER** — evidence inline, no row silently disappears.
At this checkpoint (16/27 done): P2 **APR-02** (resolution scope), **SEC-01** (vetting ownership),
**TR-01** (`_STREAMS` lifecycle review), **TR-02** (renderer UX; coordinate with VIS), plus 7 P3 rows.
**REL-01 stays `OPEN_RELEASE_BLOCKER`** until package/freeze-level evidence exists (R8).
Exit: 27/27 rows decided.

### R1 — delegation authority ceiling
Enforce `effective_child_authority <= delegator_effective_authority` over the EXISTING system
(`AUTHORITY_CLASSES`/`AUTHORITY_RANK`, role `authority_max`, TaskContract `authority` +
`allowed_tools` + `write_boundaries`, capability leases, external-effect lists, assignment grants,
provider/runtime binding, budgets). Child authority = intersection of delegator effective authority,
delegation grant, role ceiling, runtime/profile limits, tool policy, write scope, external-effect
scope, budget envelope. Child may receive LESS, never MORE. No nested spawning is introduced (D1/D2/D3
stay Commander-mediated). Tests: discriminating attempts to widen authority class, tools, write paths,
external effects, authority-relevant runtime class, budget limits (property-style where useful).
Also record the LIVE-AUTHORITY clarification (config never silently widens; user revocation narrows).

### R2 — logical-work / idempotency contract
Build the matrix over existing primitives (unique event ids, dedupe, aggregate revisions,
`job_intakes`, run epochs, unique inbox ids, one-active-milestone, effect operation ids, assessment/
publication/approval-announcement ids, native coding-call identities). For each autonomous event
family record logical-work identity, attempt identity, dedupe identity, authoritative state,
duplicate behaviour, replay behaviour, side-effect behaviour. Families: submission/intake, worker
result, native RPC, native permission reply, approval resolution, boundary grant, effect prepare,
effect observe, continuation, recovery, publication, mission/team events where authoritative.
Invariant: one logical event → at most one authoritative execution unless a NEW attempt identity is
created. Side-effects: reconcile, never blindly replay. Fix only real gaps. Tests inject duplicates
across restart boundaries where practical.

### R3 — durable retry / recovery budgets
Inventory autonomous retry domains (milestone execution, reviewer recovery, provider fallback, route
retry, planning retries, broker restart, coding check recovery, mission/stream recovery, tool
retries, scheduled/repeated work). Distinguish AUTOMATIC from EXPLICIT USER retry; automatic loops
need a durable limit that survives restarting the app/runtime/worker/broker/machine. Prefer local
persistence on authoritative entities — no global retry table unless the schemas genuinely cannot
express the state. Tests: crash/restart between attempts; budget must not reset.

### R4 — canonical approval binding (absorbs APR-02)
An approval authorizes **one exact normalized runtime action** under explicit preconditions:
operation, canonical target/resource, normalized arguments, relevant content digest, job,
run/requester, authority scope, expiration, destructive snapshot/precondition. Immediately before
execution, re-prove the match; a changed material action, a normalization that changes identity, a
changed precondition, or a job/run/scope mismatch **invalidates** the approval. Resolution must be
scoped to the owning conversation/project/job (APR-02's requirement) — as part of this same coherent
path, not a second approval system. No signatures/HMAC without a genuine threat need.

### R5 — persistence integrity contract
Invariant: **only canonical, validated, reconstructable state may be committed durably.** Inventory
externally influenced payloads (job state, events, inbox, worker results, task contracts, completion
packets, memories, proposals, findings, team messages, recovery records, artifact metadata, provider
observations, native receipts) and ensure validation before commit, deterministic serializability,
size limits, enum validation, unknown-field refusal where schemas require it, transaction rollback on
failure, and no half-valid projection/event combinations. Adversarial tests: malformed types, unknown
enums, oversized data, invalid nesting, non-serializable input, malformed JSON, unexpected tool-result
shapes, deep payloads; then verify later startup/rebuild.

### R6 — truthful state + liveness
No giant new enum; preserve layered state machines. Formalize three separate facts:
**PROCESS LIVENESS** (OS process alive and identity-matched) · **EXECUTION/SUPERVISOR LIVENESS**
(broker/controller/lease/heartbeat healthy) · **MISSION PROGRESS** (meaningful work advanced).
Invariants: `process_alive != mission_progressing`; `idle != completed`; `waiting != failed`;
`no recent event != automatically dead`; **completion requires evidence/assessment**. Reuse
Diagnostics, `native_processes`, run expiry, controller lease, mission leases, heartbeat, stale-lease
reclamation, pod stall detection, durable job/milestone state, review recovery. Derived states where
useful (progressing, legitimately waiting, stalled, lost, recovering/reconciling, blocked on user,
blocked on resource) must not become a competing authoritative machine. Interrupted work must resolve
to exactly one of **RECOVERY-CLASSIFICATION**: safely resumable · safely retryable ·
reconcile-first · user-blocked · failed/quarantined. Tests: live process + no progress; dead process
with a durable RUNNING row; legitimate long-running work; stale mission lease; provider outage;
approval wait; interrupted verifier; engine restart.

### R7 — credential / network boundary (prove, do not platform-ize)
Invariant: capability to use a provider must not imply arbitrary access to its raw credential.
Inspect credential metadata, native adapter child environments, native-host, logs, prompts, completion
packets, artifacts, test subprocesses, unrelated provider children. A trusted provider process
receiving the credential it needs is acceptable — that is different from exposing it to arbitrary
worker code, prompt content, unrelated tools, artifacts, tests, or other providers. Document the
distinction; test the containment boundary. Network: **no OS-level egress sandbox in Campaign A**;
record `host_runtime.py` as user-authorized native full-access execution (an authority-class fact),
not a sandbox. Post-V1.6 may research network-aware execution.

### R8 — packaged / migration assertions (REQ-PKG-ASSERT + REL-01)
Verify migrations on a fresh DB, a supported upgrade DB, and the packaged application: schema
versions, runtime engine identity, packaged engine hash, resources, provider discovery, Workforce
tables, resolution-kind migration, any Round 2.5 migration if one was genuinely needed. **REL-01:**
fix and *prove at package/freeze level* that the packaged engine the app loads is the intended runtime
artifact — no source-level fake closure; the blocker stays until that evidence exists. Campaign A may
create a **non-release validation fixture** but must not perform the final immutable freeze unless
release policy explicitly permits it.

### R9 — Visual batches 6–8 + Needs Your Attention
Batch 6 engine loss / error translation / supervision-recovery states · Batch 7 composer, model, tools
· Batch 8 readability, contrast, normalization, settings overlap. Re-read current Main before every
batch; use active file ownership; never race Main. **NEW — Needs Your Attention:** a derived-only
aggregation over EXISTING durable state (approval needed, permission/boundary decision, unrecoverable
failure, verification failure, uncertain completion, blocked work needing input, results genuinely
needing human review). Preferred model: "Needs your attention" / "What needs me?" — never worker
topology, leases, assignment ids, runtimes, graphs and queue internals. Use Kel's established visual
system and prefer existing Work/sidebar surfaces over a new dashboard. The surface owns no authority:
it cannot invent or mutate task state except through the existing action paths behind its buttons.

### R10 — engine-loss / recovery UX
Prove on the packaged app: boot → engine dies → user acts → UI recognizes engine state → reconnect or
restart → durable work reconciled → honest success/failure → no raw infrastructure error, no false
success, state stays understandable. `TypeError: fetch failed` must never be ordinary UX. May absorb
TR-02 and the restore-outcome renderer surface (PER-02's UI half) where appropriate.

### R11 — Visual → Main integration
Only after overlapping runtime/UI work stabilizes. Before: verify exact VIS base/head, branch clean,
Main clean, ownership cleared, overlapping files inventoried, Batches 1–5 behaviour preserved,
Batches 6–8 integrated, canonical logo preserved. After: tsc, vitest, engine regression if affected,
packaged build, probes, screenshot regeneration + index refresh, console/error checks. **Do not mark
the human visual gate passed.**

### R12 — final Campaign A regression
ENGINE: full suite, fresh DB, upgrade DB, migrations, event/idempotency attacks, retry persistence,
approval binding, delegation authority, leases, recovery, Workforce, providers, memory, capabilities,
evidence, lineage, effects, continuation. DESKTOP: tsc, vitest, Settings, Projects, Work, Permissions,
Transcription, Sidebar, Team, Composer, Model/Tools, memory, capability recommendations, Needs Your
Attention, engine-loss states. PACKAGED: build, boot, runtime identity, migration assertions, provider
discovery, routes, failure states, persistence, transcription, Workforce, canonical icon/logo, About
branding, update/restart, recovery. GIT/RELEASE: tree clean, intended branch, remote sync, no
unintended tags, public-history scan, no secrets, frozen refs byte-identical.

## 5. New canonical invariants (added to `INVARIANT_LEDGER.md`)

Stable ids follow the ledger's format; the Round 2.5 short name is in parentheses.

| ID (short name) | Statement | Phase |
|---|---|---|
| INV-AUTH-001 (AUTH-DELEGATION) | Delegated authority is never greater than the delegator's effective authority | R1 |
| INV-IDEM-001 (EVENT-IDEMPOTENCY) | One logical event → at most one authoritative execution unless a new attempt identity exists | R2 |
| INV-EFFECT-001 (EFFECT-REPLAY) | Unresolved external side effects are reconciled, never blindly replayed | R2 |
| INV-RETRY-001 (RETRY-DURABLE) | Automatic retry history survives restart (app/runtime/worker/broker/machine) | R3 |
| INV-APPROVAL-002 (APPROVAL-EXACT) | An approval authorizes one exact canonical runtime action under explicit scope and preconditions, re-proved before execution | R4 |
| INV-PERSIST-001 (PERSIST-CANONICAL) | Only validated, serializable, reconstructable state is durably committed | R5 |
| INV-COMPLETE-001 (COMPLETION-TRUTH) | Waiting/idle/process state never establishes completion; only the completion/evidence path does | R6 |
| INV-LIVENESS-001 (LIVENESS-SEPARATION) | Process liveness, supervisor liveness and mission progress are separate facts | R6 |
| INV-RECOVERY-001 (RECOVERY-CLASSIFICATION) | Interrupted work resolves to exactly one of: safely resumable · safely retryable · reconcile-first · user-blocked · failed/quarantined | R6/R10 |
| INV-MEM-001b (MEMORY-PROVENANCE) | Durable memory stays attributable and project-scoped (existing INV-MEM-001/002/003 remain the operative rows) | verify in R6/R12 |
| INV-CRED-001 (CREDENTIAL-CONTAINMENT) | Raw credentials do not become arbitrary worker/tool/prompt/artifact data | R7 |
| INV-AUTH-002 (LIVE-AUTHORITY) | Runtime/config changes cannot silently widen running work; user revocation may narrow it immediately | R1/R6 |
| INV-WF-002 (VERIFIER-INDEPENDENCE) | Builder cannot final-certify its own artifact (existing row stands) | R1–R12 |
| INV-PACKAGE-001 (PACKAGE-IDENTITY) | Packaged Kel executes the runtime artifact declared by release evidence (existing row; REL-01 is its proof) | R8 |
| INV-FREEZE-001 (FREEZE-IMMUTABLE) | Frozen releases are never modified (existing row stands; re-verified at open + RC) | continuous |

## 6. Do NOT build in V1.6 (rejected / deferred)

arbitrary nested agent spawning · a new RBAC system · a new workflow engine · a second recipe runtime ·
HMAC-everything receipts · a second memory platform · universal vector DB · giant knowledge graph ·
autonomous memory agents · trust-tainted dynamic authority · OS-level Windows network firewall ·
public A2A · a giant unified runtime-state enum · a new Advanced Worker View · adaptive staffing ·
Profiles · speculative Rust migration · generic agent cockpit UI.

## 7. Post-V1.6 (recorded, not implemented)

**Runtime security / resident autonomy:** generic credential mediation where integrations require it ·
network-aware runtime authority · scheduled durable logical-work identity · trust-tainted execution
research · capability/config revision provenance · stronger resident daemon/wake behaviour if needed.
**Workforce:** run the deferred doc-13 evaluation campaign before any adaptive-staffing activation;
5.7 stays shadow/deferred until evidence + Nick sign-off. **Advanced Worker View:** only after a
product decision + usability evidence; Advanced/Details only. **Watchlist:** public A2A · narrow
runtime ABI refactor if coupling becomes costly · richer memory only if product evidence demands it.

## 8. Rules that bind every phase

1. **Breadcrumbs in the same arc** (sprint §25): requirement id, invariant id, base/target commit,
   files, symbols, user-visible + internal change, migration, security/privacy, failure paths,
   self-review, focused/full/packaged tests, known limitation, audit target, repair hints.
   **Campaign B must not need chat history.**
2. **Audit honesty** (§26): incremental audit stays paused; never update AUDIT_STATUS as if Round 2.5
   work were independently accepted; last genuine independent audit remains `8a2b25d`.
3. **Commit truth beats prose**; corpus updated per increment; `git log <last-audited>..HEAD` must
   reconcile with `COMMIT_LEDGER.md`.
4. **Frozen refs and the public-safety scan** gate every push (explicit refspecs; never force).
5. **Speed** (§27): do not stop at phase boundaries, after the roadmap, after R0/R1, after tests, or
   after pushes; perform the next safe action; long records go to disk; chat stays compact.

## 9. Stop conditions and completion format

Campaign A stops only when the §28 checklist is true (Round 2.5 hardening complete, sweep complete,
REL-01 correctly dispositioned, Visual integrated, engine-loss UX complete, packaged regression green,
migrations proven, corpus complete, exact `PRE_AUDIT_V1_6_HEAD` recorded) or a genuine human gate
occurs. On completion, report exactly the §29 format:

```
KEL V1.6 — CAMPAIGN A COMPLETE / PRE-AUDIT RELEASE CANDIDATE READY
PRE_AUDIT_V1_6_HEAD: <sha>
Last independently audited production: 8a2b25d
Unaudited production range: 8a2b25d..<sha>
Round 2.5 V1.6 hardening: COMPLETE
Historical P2/P3 sweep: COMPLETE
Automated regression: PASS    Packaged regression: PASS / documented explicit exception
Visual automated implementation: COMPLETE    Visual integration: COMPLETE
Human Visual: PENDING        100% Audit corpus: READY    100% Repair preparation: READY
Release/freeze: NOT STARTED
NEXT CAMPAIGN: CAMPAIGN B — 100% INDEPENDENT AUDIT    Nick required: YES — START CAMPAIGN B
```
