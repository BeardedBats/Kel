# Increment — R0: the P2/P3 sweep reaches 100% final dispositions

increment_id: V16-R0-SWEEP
phase: Campaign A — R0 (roadmap R2.5; marathon directive §8)
base_commit: `756218e` (published docs tip; last production `8a677d0`)
target_commits: `49e528e` (SEC-01) · `8ab7699` (TR-01) · `5950efb` (COR-06/ERR-01) ·
`dd34ac2` (APR-05) · `594b8b4` (COR-03/APR-06/THM-01) + this docs commit
status: complete (full engine regression run at this increment — see TEST_EVIDENCE_INDEX)

## Objective

Finish the historical P2/P3 sweep: every row in `pre-audit/P2_P3_DISPOSITION.md` carries one of the
five final dispositions, with the source audit record read, the current tree verified, a
discriminating test for every behavior change, and an honest disposition where no change is
justified. Method per row: inspect the original claim → inspect current code → reproduce where
meaningful → decide release relevance → fix or disposition.

## Rows closed in this increment

| Row | Sev | Disposition | Commit | Discriminating evidence |
|---|---|---|---|---|
| SEC-01 | P2 | FIXED | `49e528e` | 7 new sweep tests; `test_vetting.py` 36 passed |
| TR-01 | P2 | FIXED | `8ab7699` | 4 new lifecycle tests; `test_transcription.py` 31 passed |
| TR-02 | P2 | DEFERRED_NON_RELEASE (bound to R9.A/R10) | — | tree read: fallback path already honest; residual is transport-failure *presentation* |
| APR-05 | P3 | FIXED | `dd34ac2` | 3 new tests: stamp + no DDL on the poll path + pre-marker upgrade |
| APR-06 | P3 | FIXED | `594b8b4` | tsc 0; vitest 93 (no component harness — §58) |
| COR-03 | P3 | FIXED | `594b8b4` | tsc 0; vitest 93 |
| COR-06 | P3 | FIXED | `5950efb` | 3 new dispatch tests |
| THM-01 | P3 | FIXED | `594b8b4` | tsc 0; vitest 93 |
| ERR-01 | P3 | FIXED (alias note recorded) | `5950efb` | same dispatch tests |

Cross-cutting behavior changes:

1. **Vetting session actions are conversation-scoped** (SEC-01). `Vetting(store, conversation=None)`
   carries the acting scope; `session()` — the single load point used by every by-id action — refuses
   a row whose `conversation_id` differs. `apply_pending` validates scope before its own early
   returns. `panel()` remains a marked display surface (`cross_conversation` preserved), and callers
   that declare no conversation keep the old behavior (additive).
2. **Transcription stream lifecycle releases resources** (TR-01). `_MuseStream.close()` queues the
   reader sentinel best-effort (→ `endStream` → socket close) and is idempotent; `_gc_streams()`
   closes before dropping; `stream_finish` closes after finishing; `_FixtureStream.close()` is a
   symmetric no-op. Optional conversation scope on stream actions.
3. **Dispatch layers never leak raw exception strings** (COR-06/ERR-01). New
   `Service._required(data, key, sentence)`; the vetting family gained the same unexpected-failure
   wrapper the transcription family already had; `/api/retry`, `/api/control`, `/api/apply`,
   `/api/approval` moved to the same contract.
4. **The approvals poll path performs no DDL** (APR-05). `chat_approvals.MIGRATION_VERSION = 20`;
   `ensure_schema` early-returns once stamped; a pre-marker store runs the idempotent body once.
5. **Failure surfaces tell the truth** (COR-03/APR-06/THM-01): the model pill reports instead of
   rejecting silently; the approval card distinguishes "engine unreachable" from a settled decision
   and otherwise shows the engine's own sentence; deleting a theme drops its saved colour overrides
   in the same operation.

## Requirement / invariant mapping

- Requirements: `REQ-P2P3-SWEEP` (this increment completes it), `REQ-OWNERSHIP-PARITY`
  (APR-02 → SEC-01 → TR-01 scope chain), `REQ-POLL-CHEAP` (APR-05), `REQ-TRUTHFUL-SURFACES`
  (COR-03/APR-06), `REQ-ERROR-SENTENCES` (COR-06/ERR-01), `REQ-THEME-HYGIENE` (THM-01).
- Invariants touched: **LIVE-AUTHORITY** adjacency (scope gates never *widen*), **PERSIST-CANONICAL**
  adjacency (the migration marker is additive and idempotent), event-idempotency untouched.
- Round 2.5 notes: APR-02 resolved the approval write/read parity; SEC-01/TR-01 extend the same
  ownership principle to vetting and transcription. R4 (APPROVAL-EXACT) still owns normalization +
  pre-execution revalidation; TR-02's renderer residual is owned by R9.A/R10 by explicit binding.

## Failure modes addressed

- A foreign vetting session id could be mutated from another conversation (SEC-01).
- An abandoned/expired transcription stream held its websocket and reader thread for the life of the
  process (TR-01).
- A missing request field surfaced as `'session'`/`'id'` instead of a sentence (COR-06/ERR-01).
- The approval card polled DDL every 3 seconds; lock churn risk on a competing writer (APR-05).
- The approval card claimed "already settled" for transport failures; the model pill failed silently;
  a deleted theme's overrides outlived it (APR-06/COR-03/THM-01).

## Security / privacy / persistence / migration impact

- Security/privacy: three scope gates (vetting, transcription, service wiring) narrow authority,
  never widen; no new secrets, no new network paths, no new persisted personal data.
- Persistence: one additive migration marker (v20, `chat_approval_announcements`); no table or column
  changes; pre-marker stores are stamped on the next call without rewriting rows.
- Migration: idempotent (`INSERT OR IGNORE`); fresh stores keep the original creation order.

## Tests (evidence-bound)

- Engine focused: `test_vetting.py` 36 · `test_transcription.py` 31 · `test_v16_sweep_fixes.py` 15 ·
  `test_v16_approvals.py` + `test_v16_restore_visibility.py` green.
- Engine full: recorded in TEST_EVIDENCE_INDEX at this commit (see A-20).
- Desktop: `tsc -p tsconfig.json --noEmit` → 0; `vitest run` → 93 passed (8 files).

## Limitations / audit questions / repair hints

- The desktop has **no renderer component-test harness** (§58): COR-03/APR-06/THM-01 are verified by
  tsc + suite + code read; the packaged probes at R8/R12 are the behavioral gate.
- TR-02 is intentionally not implemented here — Campaign B should verify the binding to R9.A/R10 is
  honored by the time the RC is assembled.
- The sprint directive cites 27 P2/P3 rows; the in-repo table carries 26 (P2 10, P3 16).
  **Reconciled 2026-09-18 (R9 bookkeeping):** the 27 = P2 10 + P3 17 worklist arithmetic over the
  increment-1/2 audit material; every original finding ID → canonical row or terminal closed state
  is enumerated in `P2_P3_DISPOSITION.md` §Denominator reconciliation (verified against the tree;
  no closed finding reopened; no real gap found). Campaign B verifies the mapping, not a guess.
- ERR-01 has two source descriptions in the audited corpus (`search.run` bare except = COR-05 vs the
  KeyError family = this fix). Both readings are dispositioned; the alias is recorded in the table.
- Repair hints: none open from this increment (all FIXED rows carry their commit + test).

## Breadcrumb updates in this increment

`P2_P3_DISPOSITION.md` (26/26 final + completion record) · `COMMIT_LEDGER.md` (5 production + docs) ·
`CHANGE_LEDGER.md` (mapping rows) · `REQUIREMENTS_TRACEABILITY.md` (REQ rows) ·
`TEST_EVIDENCE_INDEX.md` (A-20+) · `MAIN_STATUS.md` · `AUTO_RESUME.md` · `MARATHON_STATE.md` ·
this record.
