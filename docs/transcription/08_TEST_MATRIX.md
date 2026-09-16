# Transcription — test matrix

Suites: `runtime/tests/test_transcription.py` (27 tests, all against the deterministic fixture
provider), plus the whole engine suite (501 passed, 10 subtests, 2m10s) and the packaged E2E
scenario `transcription` in `packaging/ux-audit.cjs`.

## Dedicated tool

| Requirement | Test | Status |
|---|---|---|
| record → save with title, audio and duration | `test_record_save_gives_title_audio_and_duration` | PASS |
| empty recording refused with plain copy | `test_empty_recording_is_refused_with_plain_copy` | PASS |
| restart keeps transcripts and audio | `test_library_survives_restart_and_audio_stays` | PASS |
| rename / delete / folder create / move back | `test_rename_delete_folder_and_move_back` | PASS |
| record more appends text, duration, audio | `test_append_recording_extends_text_duration_and_audio` | PASS |
| combine appends and removes the source | `test_combine_appends_and_removes_source` | PASS |
| Combine is reachable from the page (choose, merge, source leaves) | packaged E2E `combined` | PASS |
| page recording cancelled with Escape saves no row | packaged E2E `escapeCancelled` | PASS |
| review Check again re-runs preview on edited text | packaged E2E `recheckWorked` | PASS |
| export text as a `.txt` payload | `test_export_text_returns_txt_named_payload` | PASS |
| export audio; plain error when the audio is gone | `test_export_audio_without_audio_is_a_plain_error` | PASS |

## Upload

| Requirement | Test | Status |
|---|---|---|
| MP3/MP4 (decoded to WAV in the renderer) | `test_upload_is_deterministic_and_saved` | PASS |
| invalid file (unreadable bytes) | `test_upload_rejects_unreadable_audio_with_plain_copy` | PASS |
| unsupported extension | `test_upload_rejects_unsupported_extension` | PASS |
| over-long audio | `test_upload_rejects_long_audio` | PASS |
| quick dictation keeps nothing in the library | `test_quick_transcribe_keeps_nothing_in_the_library` | PASS |

## Composer

| Requirement | Test | Status |
|---|---|---|
| live stream produces text and duration | `test_stream_lifecycle_produces_text_and_duration` | PASS |
| dead stream session has a plain error | `test_stream_unknown_session_has_plain_error` | PASS |
| quick_transcribe via the service route | `test_status_quick_transcribe_and_stream_routes` | PASS |
| transcript inserted editable, cancel discards | packaged E2E `transcription` (composer section) | PASS |
| dictation lands exactly once (no duplicated live region) | packaged E2E `composerSingleCopy` | PASS |

## Vetting

| Requirement | Test | Status |
|---|---|---|
| preview writes nothing and lists answers | `test_preview_writes_nothing_and_lists_answers` | PASS |
| **architectural contract**: review route == direct ingestion (snapshot **plus** answer sources and decision events) | `test_transcript_route_matches_direct_ingestion` | PASS |
| low-confidence is proposed, confirmed on accept | `test_low_confidence_transcript_is_proposed_not_applied` | PASS |
| Think-Out-Loud buckets + conflict preview | `test_freethink_buckets_and_conflict_preview` | PASS |
| no session → plain error; no conversation → latest active session | `test_no_session_anywhere_…` / `test_transcript_without_a_conversation_…` | PASS |
| service route roundtrip (session panel shows applied state) | `test_vetting_transcript_routes` | PASS |
| Accept all / Edit / Process batch in the packaged UI | packaged E2E `transcription` (review section) | PASS |

## Packaged verification (use it like a user)

`NODE_PATH=desktop/node_modules node packaging/ux-audit.cjs <app> <root> <out> transcription`
(fake media device switches make the packaged app record a synthetic tone; practice mode makes the
text deterministic):

- page visible, mode label honest
- record → live text → stop → transcript saved with audio
- rename, folder create, drag transcript into folder
- upload a valid file (MP3-named WAV) and an unreadable file (plain error)
- composer mic → editable text → cleared without sending
- vetting review opens with an active session; Process batch applies
- relaunch: transcripts still listed
- zero console errors

Evidence: `docs/transcription/evidence/` (JSON + screenshots).
