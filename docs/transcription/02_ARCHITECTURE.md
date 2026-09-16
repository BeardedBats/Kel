# Transcription — architecture

## The rule

> Input method is replaceable; answer understanding is not part of any input surface.

```
Microphone / Audio file
        │
        ▼
Renderer capture + decode            renderer/utils/transcription/audio.ts
  (getUserMedia 24 kHz PCM16, WebAudio decode to WAV — no FFmpeg binary)
        │
        ▼
Engine TranscriptionService          runtime/kel/transcription.py  (migration v12)
  ├─ provider abstraction: MuseProvider (Meta) | FixtureProvider (deterministic practice mode)
  ├─ library store: folders + transcripts (+ audio files under <data>/transcription/audio/)
  └─ stream registry: stream_start / stream_chunk / stream_status / stream_finish
        │
        ▼
Transcript (plain text)
        │
        ▼
Input routing
  ├─ chat: composer text (editable; user sends it like anything they typed)
  └─ Vetting: /api/vetting transcript_preview -> transcript_apply
             (the SAME VettingAnswerIngestion that serves typed and pasted answers)
```

## What was reused from the donor (`Transcriptions-Source.zip`, Tauri app)

| Donor piece | Kel adaptation |
|---|---|
| Muse realtime protocol (`wss://api.meta.ai/v1/asr/realtime`, handshake Bearer + PCM_24KHZ + ENDPOINTING/CUMULATIVE, `endStream`, `{transcript, final, turnId, audioProcessedMs}`) | `_MuseStream` in `kel/transcription.py` (websocket-client when importable) |
| Muse file transcription (`POST /v1/asr/transcribe` multipart `request{model,audioEncoding:WAV,mode:DIARIZATION}` + `audio`; same plain-language error mapping: key 401/403, 32 MB, busy 429, 10-minute 400) | `MuseProvider.transcribe_file` (stdlib `urllib`) |
| SQLite library (`folders`, `transcripts` with source_type/status checks) | Kel migration v12 `v15-transcription`, same fields (+ `cancelled` status) |
| Contextual title algorithm (filler stripping, 9 words / 64 chars, title-cased) | `contextual_title()` (unit-tested) |
| Append recording / combine transcripts (FFmpeg concat in the donor) | stdlib `wave` concatenation (both sides are already PCM16 WAV) |
| Sidebar pattern (Folders above, divider, Recents below, drag ghost, drop target, inline create/rename) | `pages/kel/transcription` with the same hierarchy in Kel tokens |
| Recorder shape (AudioContext 24 kHz, ScriptProcessor 4096, linear resample to PCM16, serial send) | `utils/transcription/audio.ts` + stream actions |
| Windows Credential Manager for the API key | engine key resolution: env `META_API_KEY` or a stored key (`set_key`; presence-only, mirroring `kel/providers.py`) |
| Spacebar global shortcut | **not ported** (program hard rule) |

## Deliberate replacements

- **Tauri/Rust IPC → Kel engine HTTP** action family `/api/transcription` (same style as every other
  Kel family), whitelisted in the renderer bridge (`KelService.ts`).
- **FFmpeg sidecar → renderer WebAudio**: MP3/MP4/WAV are decoded to 24 kHz mono PCM16 WAV in the
  renderer (Chromium's decoders), so the package ships no media binary. The engine validates WAV
  with the stdlib `wave` module.
- **Donor CSS/lucide → Kel surfaces**: Arco components + Kel tokens; the page follows the User
  Journey standard (plain copy, visible states, no tiny status text).
- **One understanding module**: `think_out_loud_buckets` lives in `kel/vetting.py`; the
  transcription module knows providers and the library, never answers.
- **One mic control**: both composers (guid and the conversation `SendBox`) mount
  `KelMicButton`; the donor `SpeechInputButton` is not mounted anywhere, so its global
  Ctrl/Cmd+M path is inert.

## Provider modes (plain language surfaced in the UI)

- `muse` — "Muse (Meta)": live + file transcription; needs a Meta API key.
- `fixture` — "Practice mode": deterministic local text derived from the audio's file name and
  duration; the entire feature (recording, upload, folders, review, restart) works with no key.
  This is also what makes the packaged E2E deterministic.

## Architectural contract (tested)

An equivalent transcript fed through (a) the surface every renderer path calls
(`transcript_preview` → `transcript_apply`) and (b) direct `Vetting.ingest(..., source='transcript')`
produces an identical canonical snapshot (answers, revisions, decisions, conflicts, unresolved).
Voice is an input source; the understanding is shared. See `08_TEST_MATRIX.md`.
