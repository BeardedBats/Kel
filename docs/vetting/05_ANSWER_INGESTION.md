# Design Vetting Sessions — answer ingestion

## The architecture rule (non-negotiable)

> Answer understanding is a service, not a composer feature. Input method is replaceable.

```
InputSource                     (typed chat · pasted long text · future transcription · direct/test)
     │
     ▼
VettingAnswerIngestion          runtime/kel/vetting.py — pure parse: no store, no UI, no provider
     ├─ parse (segments, ids, payloads, controls)
     ├─ map to questions (strict match, loose propose)
     ├─ confidence classification
     ├─ proposed AnswerState updates
     └─ revision intents
     ▼
Vetting (kel/vetting_session.py)  applies updates, revisions, decisions, conflicts, events
     ▼
VettingSession state (SQLite, v15-vetting)
```

The composer/chat path (ACP host → `/api/vetting ingest_chat`) and every other source call the same
`Vetting.ingest`. No parsing or state mutation lives in React components, event handlers, or button
handlers: the panel calls the same service through the same API.

The same pipeline will therefore serve a standalone transcription tool, an inline composer action, or
a direct/test harness without rewriting Vetting Sessions.

## What the parser understands

| Input | Result |
|---|---|
| `12: A` / `18: D  12: A  20: skip` | explicit answers, any order |
| `13: D + F` (comma/plus/and lists) | multi-select where the option set allows it |
| `14: change to D` | revision (history preserved) |
| `16: none of these, pickups belong in category rows` | custom answer (ANSWERED + custom text) |
| `15: I'm not sure, show examples` | `NEEDS_EXAMPLES` (or `UNSURE` without examples) |
| `defer` / `decide later` | `DEFERRED` |
| `skip` | `SKIPPED` |
| `17: make greyboxes, I'll decide later` | greybox request → `AWAITING_VISUAL_SELECTION`, directions generated, batch continues |
| `process answers`, `finish spec now`, `preview spec`, `view decisions`, `pause vetting`, `continue this vetting session`, `explain 12`, `more options for 12`, `challenge 12`, `show unanswered only` | batch controls, no assistant turn |
| `start design vetting: <topic>` / `/vetting start <topic>` | starts a session and publishes batch 1 |
| free text with no id | natural mapping — see confidence |
| `Direction 4 → base` style notes | greybox combination (panel/chat) |

## Confidence classes

- `EXPLICIT` — id + payload understood directly.
- `INFERRED_HIGH_CONFIDENCE` — unique keyword mapping (≥ 2 content-word hits, ≥ 0.34 score); applied,
  and the match is recorded in feedback for auditability.
- `INFERRED_NEEDS_CONFIRMATION` — below the apply threshold but still plausible (single strong
  keyword). **Never applied silently**: it becomes a proposal; `yes` confirms, a correction replaces
  it.
- `NOT_AN_ANSWER` — falls through to normal chat; the host re-surfaces open prompts when the reply
  finishes.

Stopwords ("with", "from", "that", …) never count as evidence; a message like "Is this technically
possible with the Yahoo API?" is not mistaken for an answer.

## Extraction review (transcript-ready)

For pasted long-form input the same parser returns `updates` + `proposals` + `unmatched`, which the
future transcription review layer will display as:

```
I pulled these answers from what you wrote:
Q12 — A, matchup dominant
Q13 — Progressive density
…
Accept all · Edit · Process batch
```

Today, pasted answers are ingested in one message (each with its confidence recorded) and anything
uncertain comes back as a proposal line in the chat.

## Revision history

Every changed answer writes a row in `vetting_answer_revisions` (previous, next, reason, source).
The decision ledger shows the current decision as `CONFIRMED` and the replaced one as `SUPERSEDED`.
`keep earlier` on a fresh conflict parks the newer answer as `DEFERRED` — nothing is dropped.

## Recorded source

Each answer stores its `source` (`chat`, `pasted`, `transcript`, `direct`, `api`) so provenance stays
visible as more input methods arrive.
