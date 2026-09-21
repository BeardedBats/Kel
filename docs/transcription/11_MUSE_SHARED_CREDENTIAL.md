# 11 — The copied app's Muse credential, shared with Kel's transcription

**Status: shipped and verified in the installed Dogfood candidate (2026-09-21).**

This closes the integration bug where Fix Capture produced Kel's canned local practice transcript
instead of Nick's words.

## What was wrong, exactly

Kel's engine resolved its Meta key from `META_API_KEY` / `MUSE_API_KEY`, then from its own
`meta_api_key` setting — and when none of those existed it **silently returned `FixtureProvider`**,
whose text is the archived practice sentences. The credential the copied Transcriptions app already
had on this machine was never consulted, so a fresh install transcribed "practice" text and Fix
Capture — which calls the same action family — inherited exactly that.

The divergence was two functions and nothing else: `Transcription.api_key()` (env → setting) and
`Transcription.provider()` (`if self.api_key(): Muse else: Fixture`). The microphone path, the audio
contract (24 kHz mono PCM16, WAV for one-shot requests) and the Muse client were already shared by
both features.

## What changed

`runtime/kel/transcription.py`

- **`shared_muse_key()`** reads the credential the copied app already wrote, read-only, via
  `CredReadW('Meta Model API.Muse Transcriptions', CRED_TYPE_GENERIC)` (the target the donor's Rust
  `keyring` entry uses: service `Muse Transcriptions`, account `Meta Model API` — see
  `src-tauri/src/credentials.rs` in the copied app). A defensive second target
  (`Muse Transcriptions:Meta Model API`) is accepted. The value is decoded in memory and never
  logged, returned, or written anywhere.
- **`api_key()`** = env → Kel's own setting → the copied app's stored credential.
- **`provider()`** = explicit practice mode → `FixtureProvider`; otherwise a key → `MuseProvider`;
  otherwise a truthful `PolicyError` ("Kel cannot transcribe this recording right now — the Meta Model
  key is not available on this computer."). Practice text is never a fallback.
- **Practice mode is explicit only**: `KEL_TRANSCRIPTION_PROVIDER=fixture`,
  `KEL_TRANSCRIPTION_MODE=fixture`, or the engine setting `transcription_mode=fixture` (tests, demos).
- **`status()`** is honest about which case you are in: `muse` (with a detail naming the copied app
  when that is where the key came from), `unavailable` (no key at all), or `fixture` (asked for).
- **`key_source()`** answers `environment` / `kel` / `transcriptions-app` — never the key itself.

`runtime/kel/dogfood.py`

- **`_is_practice_text()`** plus a save-time refusal: a fix that is the archived practice copy is
  refused with *"That is Kel's practice text, not your words — record again."* unless practice mode was
  requested by name. A debug build cannot file canned text as a real finding.

## Security

- The credential is **read only**; there is no migration, no second store, no new UI surface, and
  nothing about the key is added to status JSON or logs.
- Verified on the pushed history: the key string appears in **0 commits** and is absent from the tree;
  the only key-shaped literals anywhere are redaction-test fixtures.

## Verification (installed candidate `9a2ffbdf…`, engine `e6444991…`, 2026-09-21)

| Run | What it proves | Result (evidence in `docs/daily-driver/evidence/muse/`) |
| --- | --- | --- |
| `transcriptions` (phrase A) | the normal Transcriptions feature transcribes through real Muse | page reports **Muse**; live text *"Regular transcription muse verification"*; saved transcript *"Regular transcription muse verification orange"* (name: *Regular Transcription Muse Verification Orange*); no practice text |
| `fix-capture` (phrase B) | Fix Capture records, transcribes and saves Nick's words | **FIX-0006** transcript *"Fix capture muse verification, blue baseball 83"*, visible in Dogfood Fixes; no practice text; fixes 4 → 6 |
| `failure` | Muse failure is honest and cannot invent words | panel: *"Couldn't transcribe this recording. The Meta API key was not accepted. Replace it in Settings."*; **Retry Transcription available** and reuses the same recording; Save disabled; **nothing saved**; a direct engine call with the practice sentence is refused (400, *"That is Kel's practice text, not your words — record again."*) |
| `device-check` | the real microphone path | 4 real inputs listed (incl. *Microphone (MiniFuse 1 Start)*); the app opened the default device with no error; peak amplitude ≈ 0.001 (the room is silent) |

Every run: **0 console errors, 0 orphaned KelEngine processes.** The two phrases are deliberately
different and each flow transcribed its own recording.

## Known limitations

- The speech in the automated runs was rendered by Windows TTS to a WAV and injected as the media
  input (`--use-fake-device-for-media-stream` + `--use-file-for-fake-audio-capture`). The capture path,
  the engine, the credential lookup and the network call to Muse are the shipped ones; nobody can speak
  into the microphone during an automated run, so `device-check` documents what the real device does.
- Muse's realtime endpointing returns the utterances it closed before Stop, so a phrase can arrive in
  parts ("…verification orange" vs the full "…blue baseball 83"). That is ASR/stream behaviour, not
  Kel's copy.
- The failure run forced an unusable key through `META_API_KEY` for that one launch. The stored
  credential was never read, moved or modified.
