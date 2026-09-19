# 19 — SEVERITY REVIEW (FINAL PASS)

Audit target `08f56673…`. Every finding re-evaluated against real reachability, user impact, isolation, and release impact — not inertia.

| ID | As found | Final | Rationale for change / hold |
|---|---|---|---|
| AUD-MAJOR-001 (approvals scope opt-in) | MAJOR | **MAJOR (held)** | Reproduced end-to-end: an undeclared internal caller settled a foreign conversation's approval. Internal reachability is real; no shipped UI path abuses it; dormant route lacks scoping entirely. Security-boundary crossing not proven (no effect executed unreviewed in the probe), so not BLOCK by the observed evidence. |
| AUD-MAJOR-002 (IPC guard coverage) | MAJOR | **MAJOR (held)** | Reproduced statically: credential trio can return a real stored key to any main-world caller (no subframe/sandbox isolation in shipped windows); navigation allowlist blocks only non-http(s) schemes, not origins. Needs a malicious-page control to promote; upgrade criterion recorded. |
| AUD-MINOR-002 (budget reservations) | MINOR | **MINOR (held)** | Real overcommit accepted at reservation time, but execution proceeds only when the milestone is claimed inside the single serialized run path, and probes showed effective limits enforced at grant time for single costs. Release impact: capacity-planning accuracy, not state corruption. Campaign C re-test with runtime claiming. |
| AUD-MINOR-003 (provider env leakage) | MINOR | **MINOR (held)** | Marker present in Claude child env; no exfiltration observed; `fetch`/`network` refusals and tool policy reduce exfiltration reach; only two primary providers spawn children. |
| AUD-MINOR-006 (path traversal containment) | MINOR | **MINOR (held)** | `src/../secrets` misclassified as contained, but actual write primitives resolve paths with native semantics under the worktree; no boundary crossing executed in probes. Hidden coupling cannot be excluded → flagged for Campaign C runtime confirmation. |
| AUD-MINOR-007 (aioncore shipped live) | MINOR | **MINOR (held)** | Presence + viability chain verified; reachability from Kel code not established; legal/licensing exposure independent of runtime compromise. |
| AUD-MINOR-008 (desktop-pet wired) | MINOR | **MINOR (held)** | Settings API reachable; window start requires host-side call; donor assets/behavior shipped. Un-vetted surface, no observed security effect. |
| MINOR-001, 004, 005, 009 | MINOR | **MINOR (held)** | Documentation/evidence/traceability class; no runtime effect. 009 held at MINOR because Kel-producing configs carry Kel identity — no donor identity observed in packaged output. |
| AUD-SUG-001 | SUG | **SUG (held)** | Docstring vs parser precision; behavior arguably by design; zero state effect observed. |

No finding was promoted or demoted by this pass. The two promotion criteria that would change severity (malicious-control IPC probe; runtime budget-claiming probe) are recorded in the ledger as Campaign C follow-ups.
