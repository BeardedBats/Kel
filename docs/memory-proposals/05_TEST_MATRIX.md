# Memory proposals — test matrix

All evidence generated on branch `ux/v15-journeys` after the pre-program checkpoint
(`v1.6.0-pre1` / `Kel-V1.6.0-Pre1-Frozen`, artifact source `0fb095f`), from the rebuilt candidate
`dist/package-final13/win-unpacked` (engine `KelEngine.exe` rebuilt 02:16, desktop bundle 06:32).

## Engine (`runtime && python -m pytest tests -q`)

- Full suite: **568 passed + 10 subtests** (was 545; the 23 new below).
- `tests/test_v16_proposals.py` (23 tests):
  - queue: pending listed with current snapshot + proposed value + plain why; duplicate pending returns
    the same id; same-value proposals are `no_change`; newer proposal supersedes older pending.
  - suppression: rejected identical evidence suppressed (`suppressed: true`, nothing created);
    changed evidence asks again; hand-resolved conflicts retire their proposal.
  - acceptance: applies through `record`/`correct` (old superseded, previous value kept in
    `history()` chain, new record user-confirmed trust 2); new knowledge path; accept twice refused;
    accept after the target moved supersedes without touching memory; defer then accept later.
  - triggers: open conflict queues a review proposal and accept picks the newer (old superseded,
    conflict closed); rejection settles as leave-both with memory untouched and no re-ask on
    identical evidence; stale digest queues re-confirmation; accept refreshes the digest; rejection
    leaves the record stale and quiet; vetting decision vs stored rule queues a proposal (kind
    `vetting`, topic `vetting.Q6`, stored rule as `current`); a matching answer queues nothing; a
    rejected vetting proposal does not re-ask for the same answer; the queue is project-scoped.
  - guards: secret-like content refused; history view speaks plain sentences with no internals;
    migration 15 verified additive and versioned.
- Upgrade contract updates (deliberate, alongside the schema change): `test_v13_memory.py` (migration
  lists now `[1, 15]`; backup/receipt guarantees unchanged) and `test_v14_upgrade.py` (version lists
  include 15; the v14 additive/backup guarantees unchanged).

## Desktop

- `bunx tsc --noEmit`: 0 errors.
- `bun run test` (vitest): 76 passed / 5 files.

## Packaged journey (`bash ux-audit/run-memoryprops.sh`, run `ux-audit/runs/mp`)

Scenario `memoryprops` on `package-final13` — all assertions true, `errors: []`, `consoleErrors: []`:

| Step | Result |
| --- | --- |
| Design Vetting start + answer `6: A` | proposal queued (kind `vetting`, current = seeded rule) |
| Conversation page + Review pill | visible (pending only) |
| Card | headline + Current + Why shown, plain words |
| Accept | queue clears; Q6 accepted; old record superseded; new user-confirmed record active; DB probe `q6_value_changed: true`, `side_rule_untouched: true` |
| Reject (`7: A`) | rejected; seeded rule still active; identical re-answer does not re-ask; pill hides |
| Defer (`8: C`) | deferred; hidden from chat; **1 item rendered in Work's Project knowledge queue**; "What changed" section present |
| Restart | `{Q6: accepted, Q7: rejected, Q8: deferred}` kept |
| DB probe (`ux-memoryprops-db.json`) | `passed: true`; proposals only in project `default`; side project's same-topic rule untouched; history has "You accepted…" and "You turned the change down…" |

Screenshots: `memoryprops-01-card.png`, `memoryprops-02-work.png` in the run folder.
