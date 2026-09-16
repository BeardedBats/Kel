# Transcription — status

Feature: **Transcription as a first-class Kel input source**, built on the existing ingestion
architecture (program brief: `pasted-text-20260916-171429.txt`).

## State

| Area | State | Evidence |
|---|---|---|
| Engine module + migration v12 (`v15-transcription`) | **done** | `runtime/kel/transcription.py` |
| Provider abstraction (Muse ported from the donor + deterministic practice mode) | **done** | `MuseProvider`, `FixtureProvider`, `_MuseStream`; `test_mode_is_fixture_without_a_key_and_switches_when_set` |
| Library: folders, recents, rename/delete/assign, append, combine, export | **done** | `tests/test_transcription.py` (26/26) |
| Recording flow (page): permission, live text, stop/save, cancel | **done** | packaged E2E `transcription` run 3 |
| Upload/drop (MP3/MP4 → WebAudio WAV → provider) | **done** | E2E `uploadRow`, `invalid-copy`; unit error matrix |
| Composer mic → editable text, never auto-sent | **done** | E2E `composerRecording/composerText/composerCleared` |
| Vetting integration: preview → review → apply; Think Out Loud | **done** | E2E `reviewModal/reviewApplied/sessionProvenByReview`; contract test |
| Persistence + restart | **done** | E2E `rowsAfterRestart`; DB dump (2 transcripts, 2 audio files) |
| Engine suites | **done** | 26/26 transcription; full engine suite **501 passed**, 10 subtests, 0 failed (2m10s) |
| Packaged verification (use it like a user) | **done** | `ux-audit.cjs transcription`; screenshots + JSON + `databases.txt` in `evidence/live/` |
| Tests / tsc | **done** | tsc 0 errors; suites green |
| Documentation | **done** | this directory |
| Independent review + commit | **done** | review checkpoint CONTINUE; committed on `ux/v15-journeys` |

## How to run

```
cd runtime && python -m pytest tests/test_transcription.py -q     # 26/26
cd runtime && python -m pytest tests -q                           # full engine suite
NODE_PATH=desktop/node_modules node packaging/ux-audit.cjs <app> <root> <out> transcription
```

## Key files

- `runtime/kel/transcription.py` — store, providers, streaming, recordings/uploads, exports.
- `runtime/kel/service.py` — `/api/transcription` action family; `vetting_session.py` —
  `transcript_preview` / `transcript_apply` (the same `VettingAnswerIngestion`).
- `desktop/.../renderer/pages/kel/transcription/` — the page (folders above recents, record/upload,
  transcript view, review modal, Source settings).
- `desktop/.../renderer/pages/guid/components/KelMicButton.tsx` + `utils/transcription/audio.ts` —
  composer mic and audio preparation.
- `packaging/ux-audit.cjs` — `transcription` scenario (fake media device switches included).
- `docs/product/USER_JOURNEY_STANDARD.md` / `HISTORY.md` — JR-35..37, H18..H20.
