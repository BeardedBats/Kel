# Transcription — product specification

## One-line goal

Talking to Kel is as natural as typing to it: record, upload, keep, organize, and route spoken
words into chat or a live Design Vetting Session — without ever meeting the provider machinery.

## What the user can do

1. Open a dedicated **Transcription** tool (Kel sider → Transcription).
2. **Record** audio and watch the transcript appear (live text where the runtime provides it).
3. **Upload** or drop an MP3/MP4 (any audio the app can decode) and get a transcript.
4. **Save** transcripts automatically into Recent Transcriptions.
5. **Copy** or **download** a transcript, and **download the original audio** when it exists.
6. **Organize**: create/rename/delete folders, drag a transcript onto a folder, move it back out.
7. **Record more** onto an existing recording (text, duration, and audio are appended).
8. **Invoke transcription from the chat composer** with the mic in the action row.
9. Use a transcript as a **normal chat message** ("Send to chat" lands it in the composer, editable).
10. Use a transcript as **input to an active Vetting Session** with a review step.
11. Use **Think out loud** to speak freely; Kel extracts decisions, requirements, concerns and open
    questions through the same ingestion service.
12. **Resume** everything after an app restart.

## Governing principles (program brief)

> Transcription is an input source, not a separate conversational system.
> The same `VettingAnswerIngestion` pipeline must work whether answers come from typing, pasted
> text, or live voice.
> Reuse the existing transcription implementation where it is already proven; rebuild only what
> Kel integration actually requires.
> Kel should make talking to it feel as natural as typing to it.

## Hard rules honored

- **No spacebar shortcut.** The donor's global spacebar recording key is deliberately not ported —
  no hidden shortcut, no hint, no setting.
- **No auto-send.** A transcript is editable text before it is ever a message; the composer mic
  inserts, never sends.
- **No provider jargon.** The user sees "Practice mode" or "Muse" with plain-language sentences,
  never endpoints, models, or websocket states.

## First release scope

- Recording (microphone), upload/drop (decoded in the app), folders + recents, rename/copy/download,
  audio retention/download, append recording, combine transcripts, composer mic, chat handoff,
  Vetting review (answers + Think out loud), restart persistence.
- Out of scope for this release: live transcription of *uploaded* files (they transcribe on submit),
  multi-speaker UI beyond the provider's own diarized text, and transcription-provider choice beyond
  Muse + practice mode.
