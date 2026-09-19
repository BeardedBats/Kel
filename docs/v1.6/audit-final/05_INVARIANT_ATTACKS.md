# 05 — INVARIANT ATTACKS (Campaign B)

Every family below receives: ATTACK (what was attempted, with method) + RESULT + EVIDENCE. Families merge the campaign §10 list with the RC invariant ledger. Status filled as attacks execute; nothing removed.

| family | invariants | attack seed | attack executed | result | evidence |
|---|---|---|---|---|---|
| AUTH-DELEGATION | INV-AUTH-DELEGATION / INV-AUTH-001 | construct wider contract on each dimension; D1 unchanged w/o envelope; budget spent/reserved bypass | — | — | — |
| EVENT-IDEMPOTENCY | INV-EVENT-IDEMPOTENCY / INV-IDEM-001 | re-derive matrix; hostile duplicates across families | — | — | — |
| EFFECT-REPLAY | INV-EFFECT-REPLAY / INV-EFFECT-001 | no overwrite of observed receipt; apply-changes contradiction keeps backups; native no redispatch | — | — | — |
| RETRY-DURABLE | INV-RETRY-DURABLE / INV-RETRY-001 | fail an attempt; restart; count continues; only new contract resets | — | — | — |
| APPROVAL-EXACT | INV-APPROVAL-EXACT / INV-APPROVE-002 | cross job/run/project copy; mutate action/workspace; consume after window; unrepeatable reuse | — | — | — |
| PERSIST-CANONICAL | INV-PERSIST-CANONICAL / INV-PERSIST-001 | NaN/Infinity at every ingress; no half-written rows; corrupted row not silently rewritten | — | — | — |
| COMPLETION-TRUTH | INV-STATE-001 | idle != completed; waiting != failed; nothing completes from process state | — | — | — |
| LIVENESS-SEPARATION | INV-LIVENESS-SEPARATION / INV-LIVENESS-002 | alive-but-stalled; dead-but-running; legitimate long work | — | — | — |
| RECOVERY-CLASSIFICATION | INV-RECOVERY-002 | interrupt families; each resolves to one classification | — | — | — |
| MEMORY-PROVENANCE | INV-MEM-001/002/003 | cross-project ids; stale record; forgotten content; provenance widening | — | — | — |
| CREDENTIAL-CONTAINMENT | INV-CRED-001 / INV-CREDENTIAL-CONTAINMENT | sentinel keys through child env/logs/prompts/artifacts/packets/diagnostics | — | — | — |
| LIVE-AUTHORITY | INV-AUTH-002 | change config while work runs; attempt widening; revocation narrows | — | — | — |
| VERIFIER-INDEPENDENCE | INV-WF-002 / INV-AUDIT-001 | self-certification attempts; builder==verifier; open-blocker verdict | — | — | — |
| PACKAGE-IDENTITY | INV-PACKAGE-001 / INV-PACKAGE-IDENTITY | source==staged==packaged==loaded; stale dist; installer resources | — | — | — |
| FREEZE-IMMUTABLE | INV-FREEZE-001 / INV-FREEZE-IMMUTABLE | re-hash frozen folders + tags; no rewrite; new tag only | — | — | — |
| CAPABILITY-GRAMMAR | INV-CAP-001/002 / INV-CAPREC-001 | prose never mutates; reserved namespace; forged recommendation | — | — | — |
| APPROVAL-CANONICAL-RESOLUTION | INV-APPROVE-001 | resolved-without-announcement; cross-conversation; replay; expired anchor | — | — | — |
| ERROR-NON-MASKING | INV-ERROR-001 | inject restore+snapshot failure; primary error surfaces (PER-02/03 attack) | — | — | — |
| LEASE-EXACT | INV-LEASE-001 | kill mid-integration; double-release; release after failed integrate | — | — | — |
| IPC-SENDERFRAME | INV-IPC-001 | enumerate channels; foreign-frame calls; check parity | — | — | — |
| WF-COMMANDER | INV-WF-001 | template/instantiate Commander via every registry path | — | — | — |
| WF-FLAGOFF | INV-WF-003 | flag-off zero writes parity | — | — | — |
| WF-NEVERGATE | INV-WF-004 | Kel waive attempt; promotion without user; adaptive flag on | — | — | — |
| WF-BOUND-EVIDENCE | INV-WF-005 | forged/stale/unbound evidence close; cross-task artifacts | — | — | — |
| WF-APPENDONLY | INV-WF-006 | trigger tampering; direct UPDATE/DELETE | — | — | — |
| LINEAGE | INV-LINEAGE-001 | unrecorded generation paths; unbound lineage rows | — | — | — |
| ROUTING | INV-ROUTE-001 | FIXED missing model; provider disappears between assign and execute | — | — | — |
| UI-RAW-ERRORS | INV-UI-001 | kill engine mid-stream/request/boot/shutdown; no raw infra text; no false success | — | — | — |
| GIT-PUBLICATION | INV-GIT-001 | re-scan published range; remote refs match; no phantom tags | — | — | — |
| VISUAL-ISOLATION | INV-VISUAL-001 | visual lane wrote only its branch; integration preserved lineage | — | — | — |
