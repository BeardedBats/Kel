# Cross-feature interactions

## The seam that matters most: voice → vetting

```
composer mic ─┐
page review ──┼─→ text ─→ (chat send) ─→ ACP host ─→ Vetting.ingest ─┐
chat typing ──┘           (transcript_preview → transcript_apply) ───┴─→ VettingAnswerIngestion
```

- The page route (`/api/vetting` `transcript_preview`/`transcript_apply`) and the chat route both
  end in `Vetting.ingest(..., source='transcript'|'chat')`. The engine test compares snapshots
  **plus** answer `source` values and decision events, so a divergent second parser now fails fast.
- `voice-vetting` proves the pair in the packaged app: a dictated answer sent as chat lands in the
  panel (Q1 ANSWERED), and a review-edited multi-answer text applies three answers at once.

## Session resolution without a conversation id

The page's review works from any chat: it uses the open conversation's active session, else the
newest active session (`_active_session_any`). Two chats with two active sessions is the documented
ambiguous case; the review modal names the answers it will apply, and `10_KNOWN_LIMITATIONS.md`
(#9) keeps it honest.

## Composer coexistence

- The composer mic appears in both composers (`/guid` and the conversation `SendBox`); both use
  the same one-shot draft handoff (`kel.transcription.draft`) consumed by `GuidPage`.
- While a live vetting batch is on screen, dictation is just text: answers still only register
  when the user sends or routes them. Nothing in the recording path can answer a question silently.

## Work drawer vs page

- The Vetting tab in the Work drawer and the page's review modal read the same session state
  through `/api/vetting`; actions taken in one are visible in the other on next refresh.
- The drawer auto-selects the newest conversation when `main` is absent; the page's review does not
  need a conversation at all — both were exercised together in `voice-vetting` (restart case:
  review opens after relaunch while the drawer panel shows the same session).

## Failure isolation

- A provider outage affects exactly one thing: new transcriptions. Chats, vetting, folders, and
  previously saved transcripts keep working (practice-mode text is local).
- A missing model provider cannot corrupt vetting: answers are intercepted before submission, and
  a failed planning path still resurfaces open prompts (JR-32).
