# Increment — R2: logical-work / idempotency matrix (EVENT-IDEMPOTENCY · EFFECT-REPLAY)

increment_id: V16-R2-IDEMPOTENCY-MATRIX
invariants: **EVENT-IDEMPOTENCY** (one logical event causes at most one authoritative execution
unless a new attempt identity explicitly exists) · **EFFECT-REPLAY** (unresolved external effects are
reconciled rather than blindly replayed)
requirement: `REQ-R25-R2` (roadmap R2.5 §R2; marathon directive §10)
phase: Campaign A — R2
base_commit: `eea6503`
production_commit: (this increment)
status: complete — one real gap found and repaired; every other family proven safe with code anchors

## The matrix (first, before any change)

For each authoritative logical-work family: the identity it carries, its dedupe identity, what a
duplicate does, what restart does, and whether it can cause an external side effect. Verified by
reading the code (anchors are `runtime/kel/…`, line numbers at this commit).

| Family | Logical work | Attempt/dedupe identity | Duplicate behavior | Restart behavior | Effects | Verdict |
|---|---|---|---|---|---|---|
| Submission | one user request | `submissions.id` (client-supplied `data['id']` or `token_hex(16)`) | identical content → the **same sid** is returned and the early return **skips the executor submit** (`service.py:195-199`), so no second planning run; different content on the same id → refused | row + state durable; planner work resumes from `submissions.state` | none | **SAFE** |
| Job intake | one job per intake id | `job_intakes(id, job_id UNIQUE)` (`core.py:176`) | a second intake for the same id hits the UNIQUE row → refused (no second job) | durable | none | **SAFE** |
| Events | one aggregate transition | `events.id UNIQUE` + `dedupe UNIQUE` + `UNIQUE(aggregate_id, revision)` (`core.py:138-141`) | a duplicate (aggregate, revision) is refused by the storage layer; `_save` re-reads the revision and raises `Conflict` on a stale writer (`core.py:229-235`) | ledger is durable and append-only | none | **SAFE** |
| Runs | one milestone attempt | `runs.id` + `epoch` (fresh `uid()` per claim/orphan) + unique index `one_active_milestone(job_id, milestone_id)` (`core.py:148`) | a second active run for the same milestone is refused | durable | none | **SAFE** |
| Run epochs | epoch-scoped receipts | epoch equality | **stale epoch results are refused**: `consume()` marks them handled and skips (`core.py:401-403`); `acknowledge_stop` epoch-checks (`core.py:664-668`); orphaning writes a fresh epoch (`core.py:688`) | durable | none | **SAFE (explicit guard)** |
| Result inbox | one worker receipt | `inbox.id` (event id) + `INSERT OR IGNORE` (`core.py:313-319`) | duplicate delivery = no-op (row kept) | only unhandled rows are re-consumed after restart | none | **SAFE** |
| Inbox reduction | one reduction per receipt | `handled` flag set in the **same transaction** as the state transition (`core.py:392-426`) | a second `consume()` finds nothing unhandled for that id | crash-safe: the transition and the flag commit together | none | **SAFE** |
| Native RPC | one dispatched call | receipt per call; explicit no-replay contract (`coding_transport.py:1, 81, 101`) | a dispatched RPC without a receipt is **not** replayed ('do not replay it') | broker may reconnect; dispatched work never replays | remote effects gated | **SAFE (fail-closed)** |
| Native permission replies | one reply | same transport family (receipts) | same no-replay contract | same | gated | **SAFE (fail-closed)** |
| Approvals | one decision | `approvals.id` + `action_digest` + `status='PENDING'` + run `WAITING_APPROVAL` (`core.py:711-722`) | a second resolve is refused ('Approval does not match this action' / 'Run no longer awaits this approval') | durable | gates effects | **SAFE** |
| Boundary grants | one expansion request | `boundary_expansion_requests.request_id` + `job.state == 'AWAITING_USER'` (`authorize.py:455-478`) | a second `resume_after_grant` after the first is refused (state moved) | durable | gated | **SAFE** |
| External effects | one operation | `effects.id` (operation_id) + `action_digest` + `job_id` (`core.py:735-745`) | re-preparing with the same digest returns the existing state ('PREPARED'); a different digest/job is refused | durable PREPARED/OBSERVED | external | **GAP → FIXED** (see below) |
| Change application | one apply per job | `change_applications.job_id` + destination + state (`apply_changes.py:40-99`) | already APPLIED → `already_applied` (no rewrite); PREPARED → crash-safe resume: staging-file recovery, per-file manifest verification, `actual == after` skip, contradiction → refused with backups preserved | resumable by construction | filesystem | **SAFE (strongest in the set)** |
| Publication | one published assessment | `key = digest([job_id, assessment])` + `INSERT OR IGNORE` + `if cur.rowcount:` (`core.py:639-646`) | a duplicate publish is a no-op; the assistant message is written **only** when the row was actually inserted | durable | user-visible message | **SAFE** |
| Continuation | one resume link | `job_links` via `INSERT OR IGNORE` (`continuation.py:151`) + resume plan state | a repeated link is a no-op | durable | none | **SAFE** |
| Broker recovery | one broker result per run | `brokers` joined to `runs` (`engine.py:50`); adopt-only | recovery adopts an existing result; it never re-dispatches | durable | none | **SAFE** |
| Workforce task/mission events | one message | `workforce_messages.id` PK + append-only triggers (`workforce.py:44-70`) | duplicate id refused by the PK | durable, append-only | none | **SAFE** |
| Parallel stream announcements | one announcement | `stream_announces.announce_id` PK + append-only triggers (`parallel.py:60-68`) | duplicate id refused | durable, append-only | none | **SAFE** |

## The one real gap (and the minimal repair)

**`Store.observe_effect`** overwrote the stored receipt unconditionally: a second observation with a
*different* receipt silently replaced the evidence of what the external effect actually did — the
exact "blindly replaced after uncertain execution" failure `EFFECT-REPLAY` forbids. No production
caller exercises it today (`observe_effect` is only defined in `core.py`), which makes this a latent
correctness hole rather than a live duplicate execution.

Repair (smallest correct): an already-`OBSERVED` effect keeps its receipt. Re-observing the
**identical** receipt is a no-op; a **different** receipt is refused with a plain sentence
('Effect was already observed with a different receipt') so a reconciliation path has to decide,
rather than the storage layer quietly losing the first observation.

## Hostile duplicate tests (this increment)

`tests/test_v16_r2_idempotency.py` — **10 new**:

1. Preparing the same effect operation twice keeps one row and returns `PREPARED`.
2. Reusing an operation identity for a different action is refused.
3. Re-observing the identical receipt is a no-op (state and receipt unchanged).
4. A contradictory receipt is refused and the first observation is kept.
5. A duplicate result delivery lands once (inbox `INSERT OR IGNORE`).
6. A stale run-epoch delivery is consumed but never applied.
7. An approval resolves once (second resolve refused).
8. An event revision cannot be written twice (storage-level UNIQUE).
9. A duplicate identical submission returns the same id and does **not** dispatch the planner twice
   (executor stubbed and counted).
10. A duplicate submission id with different content is refused.

## Limitations / audit questions / repair hints

- The matrix is built from the current tree; Campaign B should re-derive it independently and
  challenge: (a) whether the submission contract requires the *caller* to supply an id (a retry
  without an id creates a new logical submission — documented, not a bug); (b) whether
  `observe_effect`'s new refusal needs a reconciliation entry point when the observation is
  *legitimately* revised (the evidence model prefers a new record — no caller exists yet);
  (c) whether `contact`-style families outside this list exist (the list is the directive's set plus
  what the code actually contains).
- No new framework, queue, or table was added — the repair is one guard in the existing function.
- Repair hints: none open from this increment.
