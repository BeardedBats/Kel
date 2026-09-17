# Memory proposals — where this workstream stands

Status: **implemented, engine-verified, packaged journey in verification** (branch `ux/v15-journeys`).

The user-facing promise: when Kel believes something the project saved changed, the change waits in a
review — Current / Proposed / Why — until the user accepts, rejects or defers it. Nothing is
overwritten until acceptance, the previous value is kept in the record's history, the same unchanged
evidence never asks twice after a rejection, and everything stays scoped to its project.

## Entry points

- Engine: `runtime/kel/memory.py` — migration 15 (`v16-memory-proposals`) + the lifecycle
  (`propose_change`, `proposals`, `proposal`, `accept_proposal`, `reject_proposal`, `defer_proposal`,
  `history_view`); triggers inside `record()` (open conflicts) and `revalidate()` (stale digests);
  `vetting_session.py → flush_memory_checks()` (Design Vetting decisions vs stored rules).
- Service: `/api/memory` actions `proposals | proposal | accept_proposal | reject_proposal |
  defer_proposal | history`; `/api/work` payload gains `memory.proposals`.
- UI: `KelMemoryProposal.tsx` (chat pill + review card + Details), mounted in `ChatConversation`;
  `KelWorkPanel.tsx` Project knowledge tab gains the review queue and a plain-language "What changed".
- Tests: `runtime/tests/test_v16_proposals.py` (23); packaged journey `memoryprops` in
  `packaging/ux-audit.cjs` with `ux-audit/seed-memory-prop.py` + `ux-audit/memoryprops-db-probe.py`.

## Decisions taken (do not relitigate without evidence)

1. Proposals are an additive layer over the approved v1.3 memory engine: memory rows still change only
   through the existing trust model (`record`/`correct`/`resolve_conflict`); a proposal is a queued
   judgment, never a second memory engine.
2. Accepted changes apply as explicit user confirmation (`user_confirmation`, trust 2): new knowledge
   becomes a user-confirmed record; a change to an existing record supersedes it and preserves the
   previous value in the chain.
3. Reject is silent but durable: the proposal keeps its dedupe key, so identical unchanged evidence is
   suppressed; a *different* value (or changed source digest) is a new question. A rejected conflict
   is settled as "leave both" without touching memory.
4. Supersede is automatic: a newer proposal for the same topic replaces older pending ones, and a
   pending proposal whose target record changed (or whose conflict was settled elsewhere) is marked
   superseded when the queue is read — it is never applied against a moved target.
5. Kel-native plain English strings, not donor locale keys (same call as session-tools; Phase 4 of the
   release program owns locale cleanup).

## If work resumes here

1. Verify: `runtime && python -m pytest tests -q`; `desktop && bunx tsc --noEmit`; packaged journey:
   `bash ux-audit/run-memoryprops.sh` (needs `dist/package-finalNN/win-unpacked`).
2. The migration is version 15; upgrade tests in `test_v13_memory.py` / `test_v14_upgrade.py` pin the
   new version lists by design — update only alongside a deliberate schema change.
