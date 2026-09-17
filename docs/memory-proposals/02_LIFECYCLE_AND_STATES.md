# Memory proposals — lifecycle and states

## Storage

Migration 15 (`v16-memory-proposals`, `runtime/kel/memory.py`): table `memory_proposals`
(id, project_id, kind, type, topic, value, summary, why, current_id, current_snapshot, evidence,
dedupe_key, state, source_ref, created, updated, decided_at, decided_by, note) + indexes. Additive and
idempotent; one pre-migration backup before the first proposals write on existing data (skipped when
the v1.3 migration already made the backup in the same open). All proposal transitions write
`memory_events` rows (`proposed`, `proposal_accepted`, `proposal_rejected`, `proposal_deferred`) which
mirror into the shared durable `events` table.

## Proposal identity and suppression

`dedupe_key = sha256(kind | type | topic | normalized value JSON | evidence signature)`.

- pending/deferred/accepted match → the same proposal is returned (no duplicates);
- **rejected match → suppressed**: the call returns the rejected proposal, `suppressed: true`, and
  creates nothing. The question re-opens only when the evidence signature or the value changes;
- superseded match → a fresh proposal may be created (the earlier one lost to newer knowledge).

Evidence signatures are content-based: vetting uses `sha256(question id | decision statement)`, the
conflict trigger uses `sha256(peer value | new value)`, the stale trigger uses the new source digest.

## Applying an accepted change

`accept_proposal` re-checks the world first (sync), so a moved target is superseded instead of applied.
Then, by kind:

- **new knowledge** (no current record): `record(..., source_type='user_confirmation', trust 2,
  user_confirmed=1)` — an explicit user confirmation is the only thing that can create durable
  decisions this way, and secret scanning applies exactly as for any write.
- **change to a record**: `correct(current, value, summary)` — the old row becomes `superseded` with
  `superseded_by` pointing at the new user-confirmed row (previous value preserved; `history()` returns
  the chain).
- **stale re-confirmation** (`kind='stale'`): a refreshed user-confirmed record supersedes the stale
  one with the new source digest; the value is kept.
- **conflict** (`kind='conflict'`): `resolve_conflict(id, 'b')` — the newer statement wins, the older
  is superseded; rejecting instead settles the conflict as "leave both" (memory untouched).
- If the current value already equals the proposal (applied elsewhere meanwhile), the proposal is
  accepted without writing a duplicate.

## Sync rules (when the queue is read)

A pending/deferred proposal is marked **superseded** when: its target record is no longer
active/stale, its snapshot no longer matches the target (summary/value changed), or its wrapping
conflict is no longer open. `accept_proposal` on a superseded proposal returns `{state: 'superseded'}`
and never applies.

## History ("What changed")

`history_view(project_id)` renders `memory_events` + proposal outcomes into plain sentences:
Added / You confirmed / You changed "old" to "new" / Replaced "old" with "new" / Marked as wrong /
Forgotten a record / Out of date / You accepted the change / You turned the change down. No raw event
logs, no ids, bounded (`limit`, default 50).
