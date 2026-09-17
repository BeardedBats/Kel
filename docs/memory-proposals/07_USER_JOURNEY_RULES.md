# Memory proposals — user journey rules

Rule **JR-52** (created by this workstream; recorded in `docs/product/USER_JOURNEY_STANDARD.md` and
ledger entry **H25** in `docs/product/USER_JOURNEY_HISTORY.md`).

## JR-52 — Saved knowledge changes only through the user's judgment

When Kel believes saved project knowledge changed — a Design Vetting decision disagrees with a stored
rule, two confirmed choices conflict, or a source behind a record changed — the change appears as a
review with Current, Proposed and a plain reason plus Accept, Reject, Defer and Details. Nothing is
overwritten until the user accepts; the previous value is preserved in the record's history; the same
unchanged evidence never asks again after a rejection; and the queue is scoped to the project it
belongs to (no cross-project leakage).

Verify: drive a disagreeing Design Vetting answer in the packaged app, accept one proposal (the old
value survives as superseded; the new record is user-confirmed), reject another and repeat the
identical answer (no re-ask), defer a third and restart (state kept), and probe the database to
confirm another project's same-topic rule is untouched.

Implemented by: `memory_proposals` (migration 15) + the lifecycle in `runtime/kel/memory.py`; the
`vetting` / `conflict` / `stale` triggers; `/api/memory` + `/api/work`; the review card in
`KelMemoryProposal.tsx` and the Work-panel queue; packaged scenario `memoryprops`.

## JR-53 — "What changed" answers in plain words, not logs

A project's knowledge history says what changed in Kel's understanding of this project in plain
sentences with previous values (Added / You changed "old" to "new" / You accepted the change / You
turned the change down / Out of date / Forgotten a record). No raw event or database dumps, no
internal ids.

Verify: in the packaged app, accept and reject proposals, then read the Work panel's Project knowledge
tab and confirm the entries are plain sentences; engine test `test_history_view_speaks_plainly` pins
the formatting.

Implemented by: `Memory.history_view()` + the What changed section in `KelWorkPanel.tsx`.

## Rules this workstream leaned on rather than added

- **JR-50** (conversation-scoped preferences state their scope) — the same scope discipline is applied
  to projects: proposals carry their project and never list elsewhere.
- **JR-51** (controls express intent; machinery stays behind Details) — the review card shows Current /
  Proposed / Why in words; ids, topics and kinds live only behind Details or never.
- **JR-47** (unexpected payloads degrade in place) — the pill renders nothing rather than blanking when
  the engine is unreachable; the chat keeps working.
