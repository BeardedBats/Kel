# Error and recovery

## Error matrix (what the user sees)

| Failure | Surface reply | Rule |
|---|---|---|
| Microphone denied/unavailable | one plain sentence via `friendlyMicError`; nothing recorded | JR-9 |
| Engine not running | KelErrorState: "…fix='Reopen this page or check that Kel is running.'" | JR-9 |
| Audio unreadable/unsupported | one plain sentence ("could not be read; damaged or unsupported") | JR-9 |
| Audio too long for the provider | one plain sentence naming the 10-minute limit | JR-37 |
| Wrong/revoked Meta key | "The Meta API key was not accepted…" — no HTTP codes, no endpoint names | JR-37 |
| Provider unreachable | one plain sentence; practice mode still records/uploads | JR-37 |
| Review with no open session | "No vetting session is open. Start one…" (nothing applied) | JR-8 |
| Unexpected engine fault (new families) | one plain sentence ("Kel could not finish that…") — tracebacks stay in logs | JR-37 |

## Transport hygiene (fixed this round)

Electron wraps handler failures as `Error invoking remote method 'kel:request': Error: <message>`.
The preload bridge now strips that envelope before any surface sees the message, so every Kel page
shows the engine's sentence — verified live by the bogus-key flow (previously the envelope leaked
into the toast; now the toast reads as a sentence).

## Recovery behaviors

- Failed uploads leave no partial transcript; retry works (unit-tested error matrix).
- Cancelling a recording (button or Escape) saves nothing and keeps the library untouched.
- An interrupted vetting flow resurfaces its open prompts after chat replies, including failed
  planning paths (JR-32; re-verified in `voice-vetting` after an interruption).
- Deleting a transcript or folder asks first, and a failed delete reports one sentence instead of
  failing silently (fixed: drag-assign and delete confirmations).
