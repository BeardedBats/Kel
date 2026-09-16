# Transcription — recording flow

## States (internal, plain copy to the user)

```
IDLE → REQUESTING_PERMISSION → RECORDING → TRANSCRIBING/FINALIZING → COMPLETE
                                   │                │
                                   ▼                ▼
                                CANCELLED         FAILED
```

The page shows: `idle` = Record button; `requesting` = "…" on the button; `recording` = pulsing
dot + "Recording 0:14" + live text + **Stop and save** + **Cancel**; `working` = "Finishing the
transcript…"; failures surface as plain messages and never discard the captured audio.

## Page recording (dedicated surface)

1. **Record** (always visible) → microphone permission is requested by Chromium; Kel's main process
   grants microphone access to its own windows only.
2. Capture: `getUserMedia(mono, echoCancellation, noiseSuppression, autoGainControl)` →
   `AudioContext(24000)` → `ScriptProcessor(4096)` → linear resample to PCM16;
   - every 4096-sample chunk feeds **live transcription** (engine `stream_chunk`), and
   - the full PCM is kept for the saved `.wav`.
3. **Stop and save** → engine `stream_finish` returns the final text (Muse `endStream`, or the
   practice stream's cumulative sentences) → `save_recording` writes the transcript **and the
   audio** (title from `contextual_title`, e.g. "Dashboard Layout").
4. The new transcript appears at the top of Recent Transcriptions and opens automatically.

**Cancel** (button or Escape while recording) discards the recording — nothing is saved, and a live
session is closed server-side.

## Record more (append)

"Record more" on a recording appends the new text and duration and concatenates the audio
losslessly (both sides are PCM16 WAV; `wave` does the concat — the donor used FFmpeg for this).

## Microphone permission copy

- Denied: "Kel needs microphone access to record audio. Allow the microphone for Kel, then try
  again."
- No device: "No microphone was found on this computer."
- Busy: "The microphone is already in use by another app. Close it, then try again."
- Other: "Kel could not start the microphone. Check your sound settings, then try again."

No raw runtime jargon is ever shown.

## Live transcription honesty

Live text appears when the provider supports it (Muse realtime, or practice mode). When the runtime
cannot stream, the page records normally and says nothing about streaming; the transcript arrives on
stop. The recording state, not the provider, is what the user is asked to trust.

## What must never happen

- Recording that starts without the user asking (no spacebar, no global shortcut).
- A stop control that is hidden or tiny.
- A saved recording that loses its audio because transcription failed.
- Silence: every path either produces a transcript or a plain-language reason it could not.
