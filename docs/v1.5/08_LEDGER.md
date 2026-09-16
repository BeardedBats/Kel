# 08 — Ledger (V1.5)

Status: **working document** — every row below is processed per Workstream 25. Requirement texts
are taken from `docs/v1.4/KEL_V1.4_FEATURE_LEDGER.md` (row IDs) and the post-release triage
(`docs/v1.4-postrelease/03_LEDGER_TRIAGE.md`). A row closes only with implementation **and**
verification evidence; no row closes because related work exists elsewhere.

## Scope summary

| Group | Count | Rule |
|---|---|---|
| VALID_POST_RELEASE_WORK rows | 38 | implement all `V1_5_REQUIRED`; `V1_5_OPTIONAL` only when coherent |
| ARCHITECTURAL_DRIFT rows | 4 (V14-150…153) | close by wiring enforcement or correcting the claim |
| ALREADY_DELIVERED_ELSEWHERE rows | 72 | advance status with the citations from the triage (WS26) |
| INFORMATIONAL rows | 28 | annotate as observations; no work |

## Classification (rows 1–25)

| Row | Requirement (ledger) | Class | Plan / scope |
|---|---|---|---|
| V14-007 | Better-with-access card | V1_5_REQUIRED | Engine opportunity classification exists (`solution.py`); surface in Work context (G7) |
| V14-029 | Per-specialist artifact/evidence grouping | V1_5_OPTIONAL | Drawer polish on top of the existing artifact API (G7 if coherent) |
| V14-043 | Task timeline | V1_5_REQUIRED | Work Center; milestone reports exist engine-side (G7) |
| V14-044 | Current-step emphasis | V1_5_REQUIRED | Work Center (G7) |
| V14-049 | Compact activity feed | V1_5_REQUIRED | Work Center; team_events stream exists (G7) |
| V14-052 | Work search and filters | V1_5_REQUIRED | Work Center (G7) |
| V14-054 | Recovery banner | V1_5_REQUIRED | Recovery engines exist; banner + link (G7) |
| V14-055 | Parent-child work map | V1_5_OPTIONAL | Only if it fits G7 coherently |
| V14-058 | Project/repository scope chip | V1_5_REQUIRED | Ties to leases: show the active execution scope on the work card (G7) |
| V14-059 | Task budget meter | V1_5_REQUIRED | Budget model exists; surface spent/reserved (G8) |
| V14-061 | Retry and escalation history | V1_5_REQUIRED | Retry records exist; history view (G7) |
| V14-062 | Stall detection display | V1_5_REQUIRED | Stall signals exist (heartbeats/deadlines); display (G7) |
| V14-073 | Superseded-history view | V1_5_REQUIRED | `history()` exists engine-side; surface (G7 desktop; engine complete as of G6) |
| V14-074 | Stale-memory warning | V1_5_REQUIRED | `revalidate→stale` exists (MEM-10); surface (G7 desktop; engine complete) |
| V14-075 | Project-isolation indicator | V1_5_REQUIRED | Isolation enforced (MEM-07); indicator (G7 desktop; engine enforced) |
| V14-082 | Context size / source-mix indicator | V1_5_REQUIRED | `context_packets` metrics exist; surface (G7 desktop) |
| V14-087 | Exact provider-session resume display | V1_5_REQUIRED | Session reuse is engine-side (CONT-03); display state (G7 desktop) |
| V14-094 | Continuation history | V1_5_REQUIRED | `job_links` exist; history view (G7 desktop) |
| V14-096 | Recovered-work banner | V1_5_REQUIRED | Recovery exists; banner (G7 desktop) |
| V14-102 | Reviewer-independence indicator | V1_5_REQUIRED | Reviewer diversity records exist; surface (G7 desktop) |
| V14-103 | Evidence-freshness warning | V1_5_REQUIRED | Staleness concepts exist; warning (G7 desktop) |
| V14-105 | Flaky-test indicator | V1_5_REQUIRED | Verify first (triage found none); engine signal or scope-out with evidence, then surface (G7 desktop) |
| V14-107 | Why-uncertain explanation | V1_5_REQUIRED | Uncertainty notes exist; surface (G7 desktop) |
| V14-109 | Verification history | V1_5_REQUIRED | Records exist; view (G7 desktop) |
| V14-111 | Requirements coverage matrix | V1_5_REQUIRED | Claims exist engine-side (`completion_claims`, G5); matrix surface (G7 desktop) |
| V14-113 | Reviewer-rubric viewer | V1_5_OPTIONAL | If it fits G7 coherently |

## Classification (rows 26–42)

| Row | Requirement (ledger) | Class | Plan / scope |
|---|---|---|---|
| V14-120 | Subscription-vs-API explanation | V1_5_REQUIRED | Settings copy (G4) |
| V14-122 | Test connection | V1_5_REQUIRED | Provider probes exist; action + result (G4) |
| V14-132 | Task cost/time/token budget | V1_5_REQUIRED | Budgets exist; surface (G8 with V14-059) |
| V14-135 | Usage history | V1_5_REQUIRED | `provider_usage` exists; page (G4/G8) |
| V14-145 | Plain-language expansion summary | V1_5_REQUIRED | Engine messages now carry plain reasons; UI copy for requests (G7; partial in G1/G2) |
| V14-148 | Outside-project warning | V1_5_REQUIRED | Boundary-request copy for out-of-scope targets (G7; engine rows exist) |
| V14-149 | Destructive-action warning | V1_5_REQUIRED | Approval copy for destructive intents (G7; engine rule exists) |
| V14-150 | Frozen-release lock | V1_5_REQUIRED | **Enforcement wired (G2)**: lease issuance refuses frozen roots; `apply` and every write/repo decision deny frozen paths (`frozen-immutable`); close with the G2 test citations |
| V14-151 | No-screen-takeover enforcement | V1_5_REQUIRED | No action family synthesizes input today; G2 decision: add a gated `machine_input` kind + truthful scope statement |
| V14-152 | Firefox-only browser rule | V1_5_REQUIRED | G2: browser kind is boundary-gated (domain scope); browser driver is not in the runtime — state truthfully or wire |
| V14-153 | Locked-system-red-line status | V1_5_REQUIRED | Correct the copy to what is actually locked (tamper detection + execution-path denials) (G7) |
| V14-178 | Local/private indicator | V1_5_OPTIONAL | Desktop polish (G7 if coherent) |
| V14-182 | Consolidated project switcher | V1_5_OPTIONAL | Desktop polish (G7 if coherent) |
| V14-195 | Context-composition metrics | V1_5_REQUIRED | Packet metrics + `tools/measure_context.py`; surface (G8) |
| V14-196 | Memory-retrieval metrics | V1_5_REQUIRED | Partial engine data exists; surface (G8) |
| V14-197 | Task cost/time metrics | V1_5_REQUIRED | With V14-059/132 (G8) |

## Advancements and annotations (WS26)

- The 72 `ALREADY_DELIVERED_ELSEWHERE` rows are advanced with the per-row citations recorded in
  `docs/v1.4-postrelease/03_LEDGER_TRIAGE.md`. Statuses updated in the ledger file when the V1.5
  increment that touches them lands; citations are copied, never re-invented.
- The 28 `INFORMATIONAL` rows are annotated as verification observations of long-standing behavior.
- No row is marked complete before its V1.5 increment has implementation **and** verification
  evidence in `14_TEST_MATRIX.md`.
