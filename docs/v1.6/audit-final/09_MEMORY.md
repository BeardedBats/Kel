# 09 — MEMORY

Audit target `08f56673…`. Source: probe-2 (`evidence/auditor-probe-2-memory.log`) + suite re-run.

## Executed attacks (results)

**Provenance / trust / secret rules (module level, project p1):**
- web-source record with trust 4 → REFUSED ("External content always stays untrusted evidence"); web @ trust 7 accepted. PASS
- preference from inference → REFUSED ("Preferences are stored only from explicit user confirmation"); user-confirmed preference accepted. PASS
- decision from worker evidence (trust 5) → REFUSED ("Decisions come only from explicit user confirmation or accepted work"). PASS
- model inference without confidence → REFUSED; with confidence accepted. PASS
- synthetic secret (`sk-ant-…`) → REFUSED ("the content looks like a secret (pattern: anthropic-key)"); 0 secret-like rows stored; a `refused` audit event recorded. PASS

**Correction / supersession / retraction:**
- correct on an active record → old row `superseded`; confirm on superseded → REFUSED; retract superseded → REFUSED; retract active → ok; second retract → REFUSED. PASS

**Forget / purge / recovery:**
- after forget: query search returns nothing; tombstone row carries empty content; `history()` content blank; `select()` excludes it. PASS
- module-level double-forget of a tombstone returns ok (idempotent, content-free; another audit event); the UI hides the action for purged tombstones (CHG-001 unit tests, re-run). Noted, not a finding.

**Proposals lifecycle + isolation:**
- identical pending dedupe → same id; rejected-identical-evidence suppressed; changed evidence asks again; accept applies + accept-twice refused; p2 list stays empty while p1 holds the proposal. PASS

**Service-layer cross-project battery (real conversations c1@sp1, c2@sp2):**
- confirm / correct / forget / retract a foreign record → all REFUSED ("Memory belongs to another project"). PASS
- foreign proposal fetch + accept → REFUSED ("Proposal belongs to another project"). PASS
- foreign conflict resolution (real conflict row) → REFUSED ("Conflict belongs to another project"); own-project resolution succeeds. PASS
- unknown conversation → "Conversation missing" (fail-closed); omitted conversation defaults to the `main` conversation's project — read/write symmetric and safe. PASS

## Coverage vs the declared battery

All §6 areas attacked: project isolation ✔, provenance ✔, trust levels ✔, preference rules ✔, decision rules ✔, corrections ✔, supersession ✔, conflict handling ✔, retraction ✔, forget/physical purge ✔ (WAL checkpoint + FTS delete in code), proposals ✔, learning integration (INV-MEM-002 path verified statically: `record_learning` → `memory.record` with workforce source types; learning suite re-run green), prompt-context fencing (composer `_pack` behavior covered by `test_v15_memory_packets` in the green suite), stale/revalidate (suite: stale digest queues reconfirm; accept refreshes), UI action truth (CHG-001/002 unit tests, re-run).

**Exit status: PASS — no new findings.**
