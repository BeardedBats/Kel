# KEL V1.3 — CONTINUATION SPEC (C3: First-Class Continuation)

Status: Gate 1 design deliverable. Approved checkpoint: reviewer relay CONTINUE (2026-09-14).
Basis: V1.2 durable store semantics (CONFIRMED: `kel/core.py` events/jobs/runs/leases;
`revise()` preserves ACCEPTED milestones and invalidates only dependency-changed ones; startup
recovery fences ORPHANED runs and adopts brokers); donor audit (warpforge wake/attach semantics,
Chuzom freeze frontier, pioneer revision-bumped resume review, ryder exact-session discipline).

## 1. Purpose and scope

Kel must be able to answer natural requests such as "Continue what we were doing.", "Resume
yesterday's work.", "Pick up the last failed job.", "Continue the dashboard task.", "Finish the
remaining milestones.", "Continue this in a new conversation." — and do it correctly:

- across conversations (attach a new conversation to existing work),
- across application restarts (durable state only),
- without ever resuming the wrong project's work,
- without ever resuming solely from transcript text,
- while preserving already-accepted milestones and the existing completion/reviewer authority.

Out of scope for V1.3: any form of speculative re-planning of accepted work; replaying historical
transcripts; a second job scheduler (Continuation is a resolution/planning layer over the existing
`jobs`/`runs`/`engine.tick` machinery).

## 2. Core rules (non-negotiable)

1. **Durable state is the only source of truth.** Candidates, milestone states, runs, native
   sessions, approvals and artifacts come from the store. Conversation text can *filter* candidates
   (e.g. "the dashboard task") but can never *reconstruct* work.
2. **Exactly one obvious candidate → continue it. Several plausible → ask the user to choose.
   None → say so clearly.** No guessing, no silent best-effort pick.
3. **Never continue work from the wrong project.** Hard project scoping: a continuation request in
   project A can only resolve jobs of project A; cross-project references are refused with a clear
   explanation.
4. **Preserve accepted milestones.** `ACCEPTED` milestones stay accepted; resume opens only
   `READY`/`NEEDS_REPAIR`/`UNCERTAIN`/`INVALIDATED`(retryable) milestones.
5. **Revalidate only affected accepted milestones.** When the project's source state changed since a
   milestone was accepted (digest mismatch), mark it `INVALIDATED` with an explicit reason and let
   the normal pipeline re-run it. Unchanged milestones are never re-executed.
6. **Reuse a valid native session when safe; otherwise build a bounded continuation packet.**
   Stored `runs.native_session` is reused only when its shape is valid and its provider matches;
   otherwise the composer packet is the delivery mechanism (never a transcript replay).
7. **Explain what is being resumed, what remains, and what is already accepted** — every resume
   produces a user-readable statement built from persisted state.
8. **Approval state survives and stays actionable.** `AWAITING_USER` jobs resolve to "waiting for
   your permission" with the existing approval surface; a restart does not drop approvals.
9. **Completion authority and reviewer boundaries are unchanged.** Resumed milestones re-enter
   `verify` → `record_review` → `assess` exactly as V1.2; executor ≠ reviewer is enforced by
   `run_id`; a resumed work item is re-reviewed against current requirements and current evidence.
10. **Continuation is idempotent.** Attaching the same conversation to the same job twice creates
    one link row; two simultaneous resumes of one job are serialized by the engine claim mechanics
    (no double execution; existing one-active-run-per-milestone index applies).

## 3. Candidate model

`Candidate` (derived per request, never stored):

| Field | Source |
|---|---|
| job_id, conversation of origin | jobs / messages |
| title = first 80 chars of contract request | job.contract.request |
| state, verdict | job |
| milestones: accepted / open / failed counts, next open milestone | job.milestones + contract |
| attempts remaining (max 4 per milestone, existing cap) | job.milestones |
| last_event_at (recency) | events / job revisions |
| linked conversations | job_links (new, §6) |
| native session present + provider | runs.native_session, milestones provider |
| source_digest_delta (revalidation need) | contract.source_digest vs current project digest |
| score, why (human words) | computed |

Eligible states (project-scoped):

| State | Eligible | Handling |
|---|---|---|
| READY | yes | resume: normal claim path |
| PAUSED | yes | resume: unpause (`control('resume')`) then claim |
| WAITING_RESOURCE | yes | resume: existing `retry_route` when health permits; else report wait |
| AWAITING_USER | yes | resume = surface approval (badge + Work context + chat line); no execution until resolved |
| RUNNING / CANCELLING | attach-only | report status; do not double-drive |
| CLOSED with verdict FAILED or UNCERTAIN and ≥1 milestone with attempts < 4 | yes ("failed/uncertain follow-up") | resume: reopen non-accepted milestones, revalidate accepted ones only on digest change |
| CLOSED with verdict VERIFIED | **no** | refused as "already verified"; only follow-up work = a NEW request referencing it |
| CANCELLED | explicit only | appears in the choice list / Work context; never auto-selected |
| ORPHANED milestone (post-recovery UNCERTAIN) | yes via revalidation path | normal recovery semantics (native reconciliation first) |

Scoring (deterministic; computed in this order, all ties broken by `last_event_at` then `id`):
1. conversation linkage (request conversation already linked to the job),
2. text match (request text vs title/topic keywords; only when text provided),
3. state priority: AWAITING_USER > PAUSED > WAITING_RESOURCE > READY > CLOSED(failed/uncertain),
4. recency of last event,
5. progress (more accepted milestones = higher).

## 4. Resolution algorithm

```
resolve(project_id, conversation_id, text):
  C = candidates(project_id)                      # state-filtered per §3
  if text: C = rank(C, text)                      # text only filters/ranks; never content
  if not C: return {"kind": "none"}
  top = C[0]
  obvious = (len(C) == 1)
            or (top.link == request_conversation and top.score_margin >= MARGIN)
  if obvious: return {"kind": "single", "candidate": top}
  return {"kind": "choice", "candidates": C[:3]}
```

- `MARGIN` is a fixed constant (documented in code) so behavior is deterministic and testable; the
  first version uses: linked-to-this-conversation + strictly higher than every other candidate.
- **choice** output renders: "I found several unfinished jobs in this project — which should I
  continue? 1) <title> — <state>, <accepted>/<total> milestones accepted, last activity <age>…".
  In the UI, the same three candidates appear under Continue Work with a one-click select.
- **none** output: "I couldn't find unfinished work in this project to continue." with a hint
  (e.g. no jobs / all verified) — never a fabricated resume.
- Wrong-project text reference (user names work that exists in another project): refuse explicitly
  ("That work belongs to project X; switch projects or confirm you want a new task here."), never
  silently retarget.
- Ambiguous project root (no trustworthy project): ask for the project first (existing V1.2
  behavior; unchanged).

## 5. Resume semantics

`execute_resume(job_id, conversation_id)` performs, in order:

1. **Attach** — upsert `job_links(conversation_id, job_id, kind='continuation')`; emit
   `continuation.attached` (event). Idempotent (UNIQUE key).
2. **State routing** (per §3 table): `READY` → nothing to change (claim path takes it);
   `PAUSED` → `Store.control(job_id,'resume')`; `WAITING_RESOURCE` → `Store.retry_route` when
   provider health permits, else report the wait; `AWAITING_USER` → surface approval only;
   `RUNNING`/`CANCELLING` → attach + status report; `CLOSED(FAILED|UNCERTAIN)` → `Store.reopen`.
3. **Revalidation** (only when the contract carries `source_digest` and the current project digest
   differs): for each `ACCEPTED` milestone whose evidence depends on the source state (coding
   milestones; research milestones with source-bound evidence), call
   `Store.invalidate_milestone(job_id, mid, reason='source changed since <old→new digest>')`.
   Milestones whose inputs did not change are left accepted. Legacy jobs without `source_digest`:
   re-check via the existing `coding.check_evidence`; if evidence still verifies, keep accepted;
   otherwise invalidate with reason `evidence no longer reproducible`.
4. **Milestone selection** — the engine's normal claim path picks up `READY`/`NEEDS_REPAIR`/
   `UNCERTAIN`/`INVALIDATED` milestones (existing eligibility rules and attempt cap of 4
   continue; resumed attempts count on the same milestone).
5. **Session continuity** — for each milestone being re-run, reuse the milestone's sticky
   provider and, when the prior run stored a valid `native_session` for that provider
   (shape-validated), pass it through the existing adapter argv / ACP `thread/resume` paths.
   Invalid or missing → no resume; the composer builds the bounded continuation packet
   (purpose `continuation`), and the user sees: "The earlier native session is no longer
   available; continuing with a bounded summary."
6. **Review** — every reopened milestone re-enters `verify` → `record_review` → `assess`
   unchanged: a resumed artifact is evidence until re-verified; executor ≠ reviewer; reviewer
   receives current requirements + current evidence (pioneer rule).
7. **Explain** — the resolution message (§7) is emitted once; the ordinary V1.2 publication
   semantics then apply.

Approval handling: `AWAITING_USER` is never auto-resolved by a continuation; `resolve_approval`
still requires `actor='user'` + digest match; after restart the pending approval is re-surfaced
(badge + Work context + the ACP guidance text fixed in V1.2).

## 6. Data model (migration 003)

```sql
CREATE TABLE IF NOT EXISTS job_links(
  conversation_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  kind TEXT NOT NULL,              -- 'origin' | 'continuation'
  created REAL NOT NULL,
  reason TEXT,
  PRIMARY KEY(conversation_id, job_id));
```

- `origin` links are written when a job is created (V1.3) and backfilled best-effort for existing
  jobs from their intake message conversation when unambiguous (idempotent; never invent links).
- Contract addition: optional `source_digest` (set by `compile_coding` from the snapshot base
  commit/tree; research/document jobs may set a project fingerprint). Old contracts remain valid
  (unknown-field tolerance; missing field = legacy path per §5.3).
- Store helpers added for this spec: `reopen(job_id, reason)`, `invalidate_milestone(job_id, mid,
  reason, expected_revision)` (see ARCHITECTURE §5); both emit events and are covered by tests.

## 7. Explainability (user-facing, from persisted state only)

- **single**: "Continuing “<title>” — <a>/<t> milestones already accepted; resuming <next open>.
  <revalidation note if any>." (<revalidation note> = e.g. "2 accepted milestones will be
  re-checked because the project changed since they were accepted.")
- **choice**: numbered list as in §4 with state + progress + age; selecting one triggers the
  single flow.
- **none**: "I couldn't find unfinished work in this project to continue." + a one-line reason
  (no jobs yet / everything verified / only cancelled work — see Work context to pick explicitly).
- **attached**: "You're continuing in this conversation now." (no state change for RUNNING jobs).
- **approval**: existing V1.2 approval text (unchanged).
No raw event streams, no internal IDs in chat; the Work context shows details on demand.

## 8. Restart and cross-conversation guarantees

| Scenario | Guarantee | Mechanism |
|---|---|---|
| restart while job active | work resumes or is explicitly fenced; no relay of stale state | existing recovery (INTERRUPTED/ORPHANED/brokers) + continuation overlay |
| resume from a new conversation | works; original conversation untouched | `job_links` attach; messages stay in each conversation |
| restart during AWAITING_USER | approval still actionable | approvals table + badge |
| resume twice / concurrently | one link; one execution | UNIQUE link + claim index |
| resume with changed repo state | only affected accepted milestones re-run | `source_digest` compare + explicit reasons |
| completed (VERIFIED) job | never auto-resumed | §3 eligibility (refusal message) |

## 9. Trust and authority in continuation

- **Resumed work is re-reviewed.** A resumed milestone's prior review does not carry over: the
  artifact re-enters `verify` → `record_review` with a fresh run identity, and `record_review`'s
  digest + contract-version guards reject stale subjects. Reviewer receives current requirements +
  current evidence (pioneer rule).
- **Prior output remains evidence, not truth.** Accepted artifacts are referenced by digest;
  re-verification uses the existing evidence checks (`check_evidence`, artifact digests). Worker
  output never self-certifies.
- **Memory interplay.** Continuation reads memories only through the composer (labeled, authority-
  ordered); it never writes memory itself. Reviewed worker output may later become L5 evidence via
  the memory module's own gate. Open conflicts on decisions used in the packet are surfaced before
  use (memory model §8).
- **Approvals are user-only and digest-bound** (`resolve_approval`: actor='user' + action digest
  match); a continuation can never resolve or bypass an approval.
- **Provenance.** `continuation.attached`, `job.reopened`, `milestone.invalidated` events record
  actor, reason and digests; the final publication keeps the standard V1.2 verification summary.

## 10. UI surface ("Continue Work" section)

- Lists eligible candidates (top 3 + "show more"): title, state, progress (`a/t` milestones
  accepted), last activity age, and a one-line "why is this here" (from §3 scoring).
- [Continue] performs attach + resume and switches the conversation to the job's follow-up stream;
  `AWAITING_USER` rows surface the existing allow/deny controls; `WAITING_RESOURCE` rows show the
  wait reason; VERIFIED jobs are not listed as continuable (cancelled work appears only in
  "show more" for explicit selection).
- Chat equivalents: "Continue this in a new conversation." — attaches the current conversation's
  job to a new conversation; "Continue the dashboard task." — resolves by §4.
- Plain language only: no event streams, no internal IDs, no prompts. Failures explain
  what/why/what-next in the V1.2 style.

## 11. Acceptance mapping (brief continuation matrix → test ids)

| Brief item | Test id |
|---|---|
| Resume active job after app restart | CONT-01 |
| Resume from a new conversation | CONT-02 |
| Resume valid native provider session | CONT-03 |
| Fall back safely when native session is gone | CONT-04 |
| Preserve accepted milestones | CONT-05 |
| Retry only incomplete/failed milestones | CONT-06 |
| Source change invalidates only dependent accepted work | CONT-07 |
| Several candidate jobs trigger a choice | CONT-08 |
| Wrong-project continuation is blocked | CONT-09 |
| Completed work is not mistakenly resumed as unfinished | CONT-10 |
| Approval state survives and remains actionable | CONT-11 |

(Test definitions live in `KEL_V1.3_TEST_MATRIX.md`.)

## 12. Explicit non-goals

No transcript-based resume; no new scheduler or job store; no speculative re-planning of accepted
work; no auto-resolution of approvals; no cross-project continuation; no resuming interactive
terminal sessions (only persisted, non-interactive native session ids are candidates, per the
exact-session discipline adapted from ryderderder/orchestrator); no UI outside the Work context
sections defined in §10.


