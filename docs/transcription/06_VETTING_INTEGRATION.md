# Transcription — Vetting integration

## The boundary

Transcription never parses answers. A transcript is text; the text goes to the **same**
`VettingAnswerIngestion` that serves typed and pasted answers via two `/api/vetting` actions:

- `transcript_preview` — pure extraction: parse the text with `source='transcript'`, return what was
  understood (updates, proposals, unmatched, confidence summary, potential conflicts). It writes
  nothing.
- `transcript_apply` — apply through the normal `Vetting.ingest` (revisions, decisions, conflicts,
  events all behave exactly as typed answers do). `accept_all` also confirms the pending
  low-confidence proposals; `then_process` runs `process answers` for the next batch.

Both actions find the right session without a conversation id: the open conversation's active
session, else the newest active session overall — so the Transcription page works no matter which
chat started the vetting session.

## The review step (rendered on the Transcription page)

"Use as vetting answers" opens the review:

```
I pulled these answers from your transcript:
12 — F, matchup visually dominant        (check this one)   ← anything not EXPLICIT
13 — Progressive density
15 — Wants examples
Suggested matches to confirm: Q16 → C
Possible conflict: Earlier answer leans “a summary/overview…”; this transcript leans “dense…”
────────────────────────────────────────────────────────────
Close · Edit · Accept all · Process batch
```

- **Edit** turns the transcript into a textarea; "check again" re-runs `transcript_preview`.
- **Accept all** applies the explicit answers **and** confirms the suggested matches.
- **Process batch** applies and asks the session for its next batch.
- If no session is open, the action answers with plain copy: *"No vetting session is open. Start one
  in a chat with “start design vetting: …” and speak again."*

## Think out loud

`Think out loud` runs the same preview in `freethink` mode and additionally classifies the raw
sentences into deterministic buckets — **Requirements heard / Concerns heard / Still open** — so
rambling stays useful. Nothing is a separate engine: the buckets classify; the answers still flow
through `VettingAnswerIngestion`, and contradictions are detected by the same opposition scan the
vetting sessions use (read-only in preview, recorded on apply).

## Confidence rules (unchanged from vetting)

- `EXPLICIT` (id + payload) applies directly on Accept.
- `INFERRED_HIGH_CONFIDENCE` applies with a visible "check this one" marker in the review.
- `INFERRED_NEEDS_CONFIRMATION` never applies silently; it stays a proposal until the user accepts.
- `NOT_AN_ANSWER` segments come back as "not mapped" and change nothing.

## The architectural contract (tested)

Same transcript through the review route (`transcript_preview` → `transcript_apply`) and through a
direct `Vetting.ingest(..., source='transcript')` produces an identical snapshot — answers,
revisions, decisions, conflicts, unresolved. `runtime/tests/test_transcription.py`
(`test_transcript_route_matches_direct_ingestion`).
