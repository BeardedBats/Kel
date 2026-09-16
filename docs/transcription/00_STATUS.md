# Transcription — status

Feature: **Transcription as a first-class Kel input source**, built on the existing ingestion
architecture (program brief: `pasted-text-20260916-171429.txt`).

## State

| Area | State | Evidence |
|---|---|---|
| Engine module + migration v12 (`v15-transcription`) | **done** | `runtime/kel/transcription.py` |
| Provider abstraction (Muse ported from the donor + deterministic practice mode) | **done** | `MuseProvider`, `FixtureProvider`, `_MuseStream`; `test_mode_is_fixture_without_a_key_and_switches_when_set` |
| Library: folders, recents, rename/delete/assign, append, combine, export | **done** | `tests/test_transcription.py` (27/27) |
| Recording flow (page): permission, live text, stop/save, cancel | **done** | packaged E2E `transcription` run 3 |
| Upload/drop (MP3/MP4 → WebAudio WAV → provider) | **done** | E2E `uploadRow`, `invalid-copy`; unit error matrix |
| Composer mic → editable text, never auto-sent | **done** | E2E `composerRecording/composerText/composerCleared` |
| Vetting integration: preview → review → apply; Think Out Loud | **done** | E2E `reviewModal/reviewApplied/sessionProvenByReview`; contract test |
| Persistence + restart | **done** | E2E `rowsAfterRestart`; DB dump (2 transcripts, 2 audio files) |
| Engine suites | **done** | 27/27 transcription; full engine suite **502 passed**, 10 subtests, 0 failed (2m10s) |
| Packaged verification (use it like a user) | **done** | `ux-audit.cjs transcription`; screenshots + JSON + `databases.txt` in `evidence/live/` |
| Tests / tsc | **done** | tsc 0 errors; suites green |
| Documentation | **done** | this directory |
| Independent review round 1 | **REVISE** | delegated code review of `27215b6`; one P1 + P2/P3 findings, all fixed |
| Review fixes re-verified | **done** | rebuilt package; E2E `escapeCancelled`, `combined`, `composerSingleCopy`, `recheckWorked` all true |
| Independent review round 2 | **CONTINUE** | see `evidence/live/` for the post-fix run |

## How to run

```
cd runtime && python -m pytest tests/test_transcription.py -q     # 27/27
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

## Post-review fix round (2026-09-16)

The first independent review of `27215b6` returned REVIEW-FAIL. Fixed in this round:

1. **UX-P1 composer dictation** — `KelMicButton` now sends the terminal `onLiveTranscript(null)`
   before `onTranscript` and on cancel, so a stopped session finalizes exactly once (no duplicated
   or overwritten composer text). E2E asserts a single copy (`composerSingleCopy`).
2. **Combine became reachable** — the transcript view has a “Combine with…” control (choose the
   other transcript; its text and audio merge into this one and it leaves the list).
3. **Provider copy** — the HTTP status left the “could not complete” sentence; the file-type
   sentence dropped “WAV” and the wrong extension list; “Preferences” → “Settings”.
4. **Honest status** — appending a recording says “Recording added to the transcript.”
5. **Escape on the page** — an in-progress page recording cancels with Escape (no row saved).
6. **Check again** — the review's Edit mode now has a real `Check again` button that re-runs
   `transcript_preview` on the edited text; process batch no longer confirms suggested matches.
7. **Error paths** — drag-assign and delete confirmations now surface a plain sentence; the page
   distinguishes microphone errors from engine sentences.
8. **One parser inside** — `think_out_loud_buckets` moved to `kel/vetting.py`; the preview and the
   recorded conflict check now share one opposition scan.
9. **Donor control removed** — the conversation composer mounts `KelMicButton`; the donor
   `SpeechInputButton` (Ctrl/Cmd+M path) is no longer mounted anywhere.
10. **Stronger contract test** — the transcript route/direct-ingest equality test also compares
    answer `source` values and decision events.
