# Design Vetting Sessions — data model

Migration: `v15-vetting`, version 11 (`runtime/kel/vetting.py`). All rows are session-scoped; two
sessions in one database never collide (composite `(session_id, id)` keys).

## Entities → tables

| Entity | Table | Notes |
|---|---|---|
| VettingSession | `vetting_sessions` | project, conversation, template, topic, state (`ACTIVE`/`PAUSED`/`FINISHED`), `current_batch` |
| QuestionBatch | `vetting_batches` | ordinal, `question_ids` (JSON), processed timestamp |
| Question | `vetting_questions` | bank id (`Q12`), section, prompt, explain, `visual`, `open`, options (JSON), one row per batch materialization |
| Answer | `vetting_answers` | status, selected codes (JSON), custom text, notes, confidence, source, feedback (JSON) |
| AnswerRevision | `vetting_answer_revisions` | previous/next JSON, reason, source — every change keeps history |
| Decision | `vetting_decisions` | statement + rationale, `CONFIRMED`/`SUPERSEDED`; one live decision per question |
| OpenQuestion | *(derived)* | computed from answers whose status is not recorded; never stored stale |
| VisualDecision | `vetting_greyboxes` + `vetting_greybox_feedback` | directions (traits + SVG), `is_base`, feedback rows (`like`/`dislike`/`combine`), composites keep their sources |
| SpecSnapshot | `vetting_specs` | full markdown + coverage JSON per snapshot |
| (events) | `vetting_events` | append-only audit: session started, ingest, proposals, pauses, conflicts, greybox actions, spec snapshots |

## AnswerState

```
status:      ANSWERED | PARTIALLY_ANSWERED | UNSURE | NEEDS_EXAMPLES | NEEDS_GREYBOX |
             AWAITING_VISUAL_SELECTION | SKIPPED | DEFERRED | CONFLICTING
confidence:  EXPLICIT | INFERRED_HIGH_CONFIDENCE | INFERRED_NEEDS_CONFIRMATION | NOT_AN_ANSWER
source:      chat | pasted | transcript | direct | api
selected:    list of option codes
custom:      free text (None-of-these tails, open answers, composite choices)
notes:       user notes kept with the answer
feedback:    structured extras (greybox choice, greybox request, confirmed proposal, unknown codes)
```

## Decision rules

- A decision is created/updated only for `ANSWERED`/`PARTIALLY_ANSWERED` answers with content.
- Changing an answer marks the previous decision `SUPERSEDED` and writes a revision row — nothing is
  overwritten in place.
- Conflicts never mutate the earlier decision; they flag the newer answer `CONFLICTING` and record the
  pair, until the user resolves it.

## Durability & continuity

- Everything lives in the same SQLite store as the rest of Kel (`schema_migrations` records
  `v15-vetting`); no new service or file format.
- Sessions survive restart and project navigation; `panel(conversation)` rehydrates the whole view
  from the database.
- The canonical comparison surface for tests is `vetting_session.snapshot(store, session_id)` —
  answers, revisions, decisions, conflicts, unresolved ids — which is also the abstraction contract
  surface (Path A typed chat == Path B direct call).
