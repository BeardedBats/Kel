# 06 — MIGRATIONS & DURABLE STATE

Audit target `08f56673…`. Evidence: constants greps, packaged DB queries, engine-suite re-run, probes 1–4.

## Schema chain (verified at RC)

Migration constants found in the tree (module → version/name):
`memory` 1/v13-memory (+v15 memory proposals via `ensure_proposals`), `projectmap` 2, `continuation` 3, `recipes` 4, `solution` 5, `team` 6, `providers` 7, `autonomy` 8, `diagnostics` 9, `authorize` 10, `vetting` 11, `transcription` 12, `model_prefs` 13, `capabilities` 14, `workforce` 16, `delegation` 18 (`v16-workforce-task-link`), `parallel` 19, `chat_approvals` 20 (`chat_approval_announcements`), `assignment` 21 (`v16-budget-reservations`). Assurance v17 rides `findings.resolution_kind` (per increment records). **Max = 21** — consistent across constants, `MIGRATION_LEDGER` RC prose, and actual databases.

- `assignment.py:35` comment records the historical duplicate-17 defect and its fix (assignment claims 21; workforce keeps 17) — matches `2468b16`.
- **Packaged receipts (auditor-queried, read-only):** `ux-audit/runs/r12-fresh2/kelwork/kel.sqlite3` → 14 rows, max `(21,'v16-budget-reservations')`; `ux-audit/runs/r12-upgrade/kelwork/kel.sqlite3` → 15 rows, max 21. Upgrade root with pre-existing conversations boots to the same chain.
- **Fresh + upgrade + idempotence + interrupted-migration checks** exercised via the re-run suite (`test_v16_r8_migrations.py` et al. inside the 998+10 green run) and cross-checked against the receipts above.
- **Backup-before-first-mutation** for the proposals family is implemented (`_backup` in `memory.py`, guarded by `_is_fresh_database`) and covered by the suite; no independent failure-injection of a backup failure was performed (recorded limitation).
- Duplicate/missing-version check: the unique-marker fix + `test_v16_r8_migrations` assert uniqueness; the audit found no duplicate version rows in the packaged DBs.

## Durability semantics attacked (probes 1–3)

- Canonical serialization: `encode` refuses NaN/Infinity (PolicyError, exact sentence); bytes/set refused (TypeError). (Probe-1 D.)
- Effect receipts: identity reuse for a different action refused; identical re-observation is a no-op; contradictory receipt refused and evidence kept. (Probe-1 C; pre-fix negative control fails exactly this test.)
- Restore outcome sidecar: `OUTCOME='restore-outcome.json'` written beside the data; `service.state()['restore']` reads it (`backup.py:23`, `service.py:36`). Renderer surfacing remains the recorded REQ-ELOSS follow-on.
- Memory writes: secret-like content refused before durability (probe-2 A8–A10: 0 rows stored, refused audit event present); tombstone purge leaves content-free rows (probe-2 C).
- Retry/attempt state: milestone `attempts` persisted on the job row survives a new `Store` instance on the same DB (probe-3 E: attempts 1→2 after “restart”, third claim refused once the max-2 budget was spent).

## Open items recorded (not findings)

- No independent interrupted-migration harness was built beyond the suite's checks (the suite covers the paths; recorded as method limitation).
- `MIGRATION_LEDGER.md` table staleness (`next free version: 20`, unchecked RC checklist) is recorded under **AUD-MINOR-005**.
