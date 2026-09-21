# V2-10 — Learning 2.0 (2026-09-21)

Increment: the person's side of learning, and the fence. The learning layer already existed
(`kel/learning.py` — learnings as memory records with the V1.3 trust ladder, decay, corrections;
`kel/memory.py` — the proposal queue with accept/reject/defer and evidence-keyed dedupe). Nothing was
rebuilt: this increment added what the roadmap actually asked for and measured the rest.

## What was already true (measured, not assumed)

- Learnings ride the existing memory store: `record_learning` writes a `learning.v1` value through
  `Memory.record` (provenance, secret scan, supersede chains, conflict queue — unchanged).
- The proposal machinery already refuses authoritative types: `Memory.propose` refuses
  `decision`/`preference` outright, and preferences are recordable only from explicit user
  confirmation (`source='user-stated'` + `confirmed_by='user'`).
- A rejected proposal never re-appears from identical evidence: the dedupe key covers the proposed
  change plus an evidence signature.
- The shadow flag (`workforce.learning.shadow`, default off) gates every *automatic* write path.

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| Off/on without deletion | `learning.set_enabled` | A learning is superseded by an equal-trust copy carrying `enabled` — the append-only chain and the trust of the original content are preserved (switching it off is the person's action, not a new belief). Refuses records that are not current learnings, in plain words. |
| Off means out of context | `Memory.select` | A disabled learning never reaches model context; other memory types are untouched. |
| Inspect with buttons | `learning.learnings_view(..., include_disabled=…)` + `/api/memory` actions `learnings` / `disable_learning` / `enable_learning` | Disabled and stale learnings stay inspectable on the person's own surface; only enabled ones reach context. |
| Explain | `learning.explain_learning` + `/api/memory` action `learning` | Source, trust, confidence + decay, evidence references, provenance, the full supersede chain, queued promotions, and a plain `effect` sentence that states the boundary (advisory only — never permission, spending, file access or irreversible authority). |
| Evidence threshold | `learning.suggest_learnings` (`SUGGEST_MIN_EVIDENCE = 3`, 30-day window) | Three bounded sources — decided runs (the V2-09 `routing_outcomes` store: model-by-task), repeated user corrections (≥3), repeated Connection use (≥3, engine-wide) — each needing the threshold before anything is *suggested*. Suggestions are proposals only; nothing is ever applied. |
| Authority fence | `learning.AUTHORITY_RE` + `authority_refusal` in `record_learning` and in the suggestion path | A non-user source that asserts a permission grant, spending authority, filesystem access or irreversible authority is refused outright — not stored, not even proposed — with one plain sentence. A user's own statement is theirs to make and passes. |

## Rules the increment pins

- **Nothing is silent**: suggestions land in the existing review queue (accept / reject / defer); the
  suggestion path never uses `decision` or `preference` memory types.
- **Nothing is authority**: the fence refuses authority-shaped text from every non-user source, and
  `effect` states the boundary on every explain.
- **Off is real and reversible**: disabled learnings leave context and the default view, stay in the
  store, and come back with one call — the chain records every step.
- **Rejection sticks until reality changes**: a rejected suggestion is suppressed for identical
  evidence and can only return when its evidence signature changes.

## Verification (on the final code of this increment)

Bounded groups, one stack at a time — no monolithic run:

- `tests.test_v2_learning` (new, 19 tests) + `test_workforce_learning` + `test_v13_memory` +
  `test_v16_proposals` + `test_v15_memory_packets` + `test_v16_r5_persistence` +
  `test_service_routing` + `test_v14_diagnostics` → **112 OK**.

Live loop (engine restarted on this code with `KEL_WORKFORCE_LEARNING_SHADOW=1`,
`C:\Users\Nick\KelV2Runs\prepared\engine`), driven entirely through `/api/memory`:

```
database=...\KelV2Runs\prepared\engine\kel.sqlite3
suggest (empty evidence) -> minimum=3 suggested=0
suggest (3 decided runs) -> suggested=1 states=['pending']
queue: 1 open
accept -> {"kind": "user_change", "memory": "ab10512d-…", "state": "accepted"}
learnings -> 1: [('model.coding.codex', 'observed')]
explain effect=Advisory only. A learning never grants permission, spending, file access or any
               irreversible authority — those stay your decision every time.
explain evidence=["routing_outcomes:coding:codex"]
after disable -> default=0 include_disabled=1 enabled_flag=False
after enable -> default=1
RESULT live_loop=ok
```

The probe engine was stopped afterwards (pid checked against the listener before killing; nothing of
Astra's was touched). The probe's test rows live only in the V2 test root.
