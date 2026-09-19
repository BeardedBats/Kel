# 04 — REQUIREMENTS COVERAGE (final)

Audit target `08f56673…`. Every ID below was grepped from the RC corpus (`docs/v1.6/**`) and is dispositioned with the audit artifact that evidences it. **Total: 105/105.** No `TBD`.

## Repair/security/feature requirements (23)

| ID | Disposition | Evidence |
|---|---|---|
| APR-01 | PASS — payload `actor` refused on all action families | probe-1 §A; suite |
| APR-02 | **FINDING** — scoping opt-in (enforcement not engine-bound) | AUD-MAJOR-001 |
| APR-03 | deferred by decision (corpus); not re-litigated | corpus record |
| APR-04 | covered — APPROVAL-EXACT battery | probe-1 §B; suite R4 |
| APR-05 | covered — poll-path DDL perf fix; suite re-run | suite; commit `dd34ac2` |
| APR-06 | covered — honest failure surfaces | `594b8b4`; UI review 13 |
| SEC-01 | PASS — vetting session ownership enforced at service layer | probe-4 |
| SEC-02 | folded into P2/P3 sweep; MR-002 verification | corpus; sweep record |
| TR-01 | PASS — lifecycle re-verified independently | probe-4 |
| TR-02 | PASS — backend semantics fine; renderer honest path | `engineFailure.ts`; R10 |
| REL-01 | covered — engine-loss ladder on installed auditor build | auditor r10 PASS |
| REQ-F4 | PASS — evidence-bound close (static + suite) | 08; `test_v16_close_d1` |
| REQ-RK | PASS — resolution-kind breadcrumbs (static+suite) | `a547936` |
| REQ-LOGO-1 | PASS — canonical logo across surfaces + brand check | brand check PASS |
| REQ-APR-1 | **FINDING** via AUD-MAJOR-001 | ledger |
| REQ-OWNERSHIP-PARITY | **FINDING** — approvals diverges from parity rule | AUD-MAJOR-001 |
| REQ-R25-R1 | PARTIAL-FINDING — budget cumulative gap | AUD-MINOR-002 |
| REQ-R25-R4 | PASS — exact/window/duplicate w/ declared callers | probe-1 §B |
| REQ-R25-R7 | PARTIAL-FINDING — native child env | AUD-MINOR-003 |
| REQ-R25-R12 | PASS-with-gaps — installed truth battery; evidence gaps recorded | AUD-MINOR-004 |
| REQ-PKG-ASSERT | PASS (auditor rebuild) + gaps in RC retention | 15; AUD-MINOR-004(e) |
| REQ-WFWIRE | scope decision still open in corpus (recorded) | AUD-MINOR-005 |
| REQ-PKG-ASSERT (ledger reconciliation) | FINDING | AUD-MINOR-001 |

## Change records CHG-001 — CHG-028 (28)

All 28 CHG records were reviewed in the corpus sweep; those with shipped behavior affecting audits were executed or inspected: CHG-001/002 (Work-panel memory action truth — vitest re-run + code), CHG-003 (recommendation wiring — suite), CHG-004 (completion evidence correction — 17), CHG-006 (close binding — 08), CHG-012 (vetting display read — 12), and the remaining CHG rows were dispositioned as documentation/UX records against the delivered tree during Pass 2 (stale rows folded into AUD-MINOR-005). **Status: 28/28 dispositioned** (link targets: 14/17/18 docs; MINOR-005).

## Invariants (42 unique IDs, from corpus grep)

Disposition legend: **A** attacked (probe/stunt executed), **S** suite/static coverage re-verified green, **F** finding recorded.

`INV-APPROVAL-002` A · `INV-APPROVE-001` A(F→MAJOR-001) · `INV-APPROVE-002` A(PASS) · `INV-AUDIT-001` S · `INV-AUTH-001` A(partial→MINOR-002/006) · `INV-AUTH-002` A · `INV-BRAND-001` verified · `INV-CAP-001` A · `INV-CAP-002` A · `INV-CAPREC-001` S · `INV-COMPLETE-001` A+S · `INV-CRED-001` A(F→MINOR-003) · `INV-DATA-001` verified · `INV-EFFECT-001` A · `INV-ERROR-001` S · `INV-FREEZE-001` verified · `INV-GIT-001` verified · `INV-IDEM-001` A · `INV-IPC-001` reviewed(F→MAJOR-002) · `INV-LEASE-001` reviewed · `INV-LINEAGE-001` S · `INV-LIVENESS-001` S · `INV-LIVENESS-002` A(r10) · `INV-MEM-001` A · `INV-MEM-002` A+S · `INV-MEM-003` A · `INV-PACKAGE-001` verified(F-part→MINOR-007) · `INV-PERSIST-001` A · `INV-RECOVERY-001` A(probe-3+r10) · `INV-RECOVERY-002` A(probe-3) · `INV-RETRY-001` A(PASS) · `INV-RK-001` S · `INV-ROUTE-001` verified · `INV-STATE-001` S · `INV-UI-001` verified(0 leaks/errors) · `INV-VISUAL-001` reviewed (human gate PENDING) · `INV-WF-001` S · `INV-WF-002` S · `INV-WF-003` A(PASS) · `INV-WF-004` reviewed(PASS) · `INV-WF-005` reviewed(PASS) · `INV-WF-006` reviewed(PASS). **42/42.**

## Rounds/phases R0–R12 (13)

R0 sweep 27/27 dispositioned (corpus + spot checks; drift → MINOR-005); R1 delegation (attacked); R2 effects/idempotency (negative control executed); R3 retry durability (probe-3 E + suite); R4 approval exact (negative control executed); R5 canonical persistence (probe-1 D); R6 liveness truth (suite + r10); R7 credential containment (probe-1 G → MINOR-003); R8 migration markers (suite + DB receipts); R9 UX truth (installed probe + review); R10 engine-loss (executed on auditor build); R11 package identity (auditor rebuild + install); R12 installed truth (installed probe + lifecycle). **13/13.**

**Grand total: 105/105 requirement items dispositioned with evidence or recorded findings.**
