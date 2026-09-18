# CHANGE_LEDGER — product-behavior changes in the unaudited range

updated: 2026-09-18T16:05Z

Organized by PRODUCT BEHAVIOR, not commits. One entry per behavior change that Campaign A (or the
pending visual integration) delivers. Earlier, already-audited V1.6 arcs are traced in
REQUIREMENTS_TRACEABILITY.md instead — this ledger is what Campaign B must read closely.

Template (all fields required; write `none` explicitly rather than leaving blanks):

```
ID:            CHG-###
Title:
Phase:
User-visible impact:
Internal impact:
Previous behavior:
New behavior:
Primary files:
Primary symbols/functions/classes:
Data/schema changes:
Failure paths:
Security/privacy implications:
Persistence implications:
Expected invariants:        (pointer into INVARIANT_LEDGER.md)
Tests:                      (what proves it, incl. discriminating coverage)
Packaged evidence:          (or `-`)
Known concerns:
Audit questions:            (what should Campaign B attack on this change)
Repair hints:               (pointer into REPAIR_HINTS.md, if any)
```

## Entries

*No entries yet.* The ledger opens with the first Campaign A production commit. Increment records
(`increments/`) are written first; the ledger summarizes each increment's behavior changes here.

Planned Phase-to-CHG mapping (kept current as work lands):

| Phase | Expected CHGs | Status |
|---|---|---|
| 6 — memory reality audit + bounded fixes | CHG-001+ (any fixes) | IN PROGRESS |
| 7 — smart capability recommendations | CHG-0xx | PENDING |
| 8 — Advanced Worker View decision | none (decision only; recorded in DEFERRED_ITEMS.md) | PENDING |
| 9 — Profiles vs Projects decision/fixes | CHG-0xx | PENDING |
| 10 — real provider validation | none (evidence only; PROVIDER_VALIDATION_MATRIX.md) | PENDING |
| 11/12 — Rust freshness / migration | none expected (verification only) | PENDING |
| F4 real-artifact binding wiring | CHG-0xx | PENDING |
| resolution-kind semantics | CHG-0xx | PENDING |
| P2/P3 sweep | CHG-0xx per fixed finding | PENDING |
| Visual batches 6–8 + integration | CHG-0xx (per batch; see VISUAL_EVIDENCE_INDEX.md) | PENDING |
| Engine-loss/recovery behavior | CHG-0xx | PENDING |
