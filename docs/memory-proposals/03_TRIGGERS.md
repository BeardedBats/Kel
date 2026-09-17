# Memory proposals — triggers

Proposals are created only by wired, deterministic triggers. Nothing else writes to the queue.

## 1. Design Vetting decisions vs stored rules (`kind='vetting'`)

Where: `vetting_session._decision_for()` queues every confirmed decision; the service drains the
queue after the vetting request commits (`_vetting_action → flush_memory_checks()`).

Rule: for each confirmed decision, stored active records with topic `vetting.<question id>` are
compared; a record whose value differs queues a proposal (current = the stored rule, proposed = the
vetting statement, why = "Your latest Design Vetting decisions conflict with the stored project
rule."). Re-answering the same option does not re-ask after a rejection (content-based signature).

Scope note (v1): matching is by exact topic key; semantic matching between differently-worded rules
needs a model and is deliberately out of scope (see 06_KNOWN_LIMITATIONS.md).

## 2. Two confirmed choices disagree (`kind='conflict'`)

Where: `Memory.record()` — when the v1.3 conflict matrix produces an OPEN conflict between two
authoritative records (equal trust, both confirmed, different values).

Rule: the open conflict also queues a proposal; current = the older statement, proposed = the newer
statement, why = "Two saved choices disagree — pick the one that should stand." Accept resolves the
conflict in favour of the newer statement; Reject settles it as "leave both" without touching memory.
The pair signature is `sha256(old value | new value)`, so the same disagreement never re-asks.

## 3. A source changed (`kind='stale'`)

Where: `Memory.revalidate()` — when a record's `source_digest` no longer matches the digest map the
caller supplies.

Rule: the record is marked `stale` (v1.3 behaviour, unchanged) and a re-confirmation proposal queues
(why = "The source behind this knowledge changed — confirm it is still true."). Accept replaces the
stale record with a refreshed user-confirmed one (new digest, same value); Reject leaves the record
stale and quiet until the digest changes again. Records without a `source_digest` cannot trigger this.

## Non-triggers (explicitly excluded)

Trivial wording differences (only exact normalized-value differences count), temporary task state,
low-confidence inference, ephemeral conversation content, and minor stylistic variation never create
proposals. User-driven direct edits (`confirm`/`correct`/`retract`/`forget` from the knowledge UI)
remain direct: the user already decided, the history records it, and no card is raised.

## Ordering rules

Triggers run after the surrounding transaction commits (`flush_memory_checks` is called post-commit;
the two in-engine triggers use the same transaction they annotate but write only proposal rows).
Proposal writes are idempotent by dedupe key, so re-running a trigger is always safe.
