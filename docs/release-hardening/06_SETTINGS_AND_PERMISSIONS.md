# Settings and permissions

## Settings surfaces (single registry, JR-30)

Ten tabs, one ordered registry (`BUILTIN_TAB_IDS`): model, agent, skills, tools, appearance, webui,
pet, system, archived, about. `settings`/`b2-settings` visit every tab with zero console errors.

## Transcription settings — one plain status (JR-37)

The page has exactly one settings door: **"Source"** opens "Transcription source", which shows one
human line (`Practice mode` / `Muse (Meta)`), and — only without a key — a single key input plus
"Connect". No provider picker, no model names, no protocol terms anywhere on the surface (jargon
scan over `/transcription` and `/guid`: zero offenders).

## Microphone permission

- The app grants the `media` permission in-session (packaged E2E records with the fake device); a
  denied or unavailable microphone maps to one plain sentence through `friendlyMicError`
  ("Kel needs the microphone… allow access and try again."), never a DOMException string.
- Escape cancels capture in **every** capture state (requesting/working/recording) and a
  late-arriving capture is aborted by the epoch guard — a warm-up race could previously leave a
  recording running (fixed; E2E `escapeCancelled`, `keyboardEscape`).
- Live OS-level denial (blocking the device outside Kel) cannot be produced by the harness; the
  copy path is unit-tested and the handler policy is code-reviewed. Recorded as a limitation.

## Stored credentials

- A Meta API key is stored presence-only (env `META_API_KEY` or the stored key), mirroring
  `kel/providers.py`; the settings modal shows a single "Disconnect the key". A wrong key changes
  nothing else; uploads answer with one plain sentence and practice mode resumes on disconnect.
