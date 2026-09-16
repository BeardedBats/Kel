# Transcription — file upload

## Entry points

- **Upload Audio** button on the Transcription page.
- **Drag and drop** an audio/video file anywhere on the page (a dashed overlay says
  "Drop audio or video to transcribe" while a file hovers).

## Accepted formats

`.mp3`, `.mp4`, `.wav`, plus `.m4a`, `.aac`, `.ogg`, `.flac`, `.webm` when the browser can decode
them. Decoding decides, not a hand-written list: the renderer uses WebAudio `decodeAudioData`, so
any container Chromium understands works, and a file it cannot read gets one plain sentence:
"That file could not be read as audio or video. Choose an MP3 or MP4 file."

## Pipeline

1. detect file → progress label **"Preparing audio…"**
2. renderer decodes to 24 kHz mono PCM16 WAV (no FFmpeg in the package)
3. engine `upload` → transcript row created as `processing` first, **original audio saved
   immediately** (so nothing can be lost), then the provider runs
4. **"Transcribing…"** → on success the row becomes `complete` with text, title (contextual title or
   the file's stem), duration and source filename; on failure the row stays with `failed` status
   **and its audio**, and the plain reason is shown
5. **"Saving transcript…"** → the row appears at the top of Recent Transcriptions and opens

## Error copy (ported from the donor, kept plain)

| Situation | Message |
|---|---|
| empty file | "That audio file is empty." |
| unreadable / damaged | "This audio file could not be read. It may be damaged or in an unsupported format." |
| unsupported extension | "Choose an MP3, MP4, or WAV audio file." |
| longer than the provider limit | "Muse accepts audio up to 10 minutes. Split this file, then try again." |
| larger than 32 MB | "This audio is larger than 32 MB. Split it, then try again." |
| provider rejects the key | "The Meta API key was not accepted. Replace it in Source." (donor wording) |
| provider busy | "Muse is busy for this account. Wait briefly, then try again." |
| mid-process failure | the row stays `failed` with its audio; re-uploading is never required to keep the file |

## Composer dictation vs upload

The composer mic uses the same engine (live stream when available, otherwise a one-shot
`quick_transcribe`) but keeps nothing in the library: dictation is input, not a document. Pressing
Stop drops editable text into the composer; the user sends it or not.

## Restart recovery

`processing`/`failed` rows survive restart with their audio; the page shows them with plain status
copy ("Needs attention") and the original file name, so a retry is obvious and nothing silently
disappears.
