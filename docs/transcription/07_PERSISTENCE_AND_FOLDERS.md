# Transcription — persistence and folders

## Storage

- Migration `v15-transcription` (version 12) in `runtime/kel/transcription.py`:
  - `transcription_folders(id, name, created)`
  - `transcripts(id, name, text, created, updated, folder_id, audio_path, source_type,
    source_filename, duration_ms, status)` — `source_type ∈ {recording, upload}`,
    `status ∈ {processing, recording, complete, failed, cancelled}`
  - `transcription_settings(name, value)` — provider key presence (value never echoed back)
  - indexes on `created DESC` and `folder_id`
- Audio files live under `<KEL_DATA_DIR>/transcription/audio/<id>.<ext>`; deleting a transcript
  removes its audio file. Failed uploads keep their audio on purpose.
- Same SQLite store as the rest of Kel — transcripts survive restarts, updates, and project
  navigation, and they travel with a data-directory copy.

## Library payload (renderer)

`/api/transcription` `library` returns folders (name order) and transcripts (newest first) with
`has_audio`; the renderer never sees filesystem paths.

## Folders

- **Create / rename / delete** are inline in the sidebar ("New folder" + Add; pencil on hover).
  Deleting a folder keeps its transcripts (they move back to Recent Transcriptions) — same rule as
  the donor.
- **Move**: drag a transcript row onto a folder row (the folder highlights as a drop target), or use
  the transcript's "Move to" select. No modal-heavy workflow.
- **Hierarchy**: the sidebar shows **Folders** first, a small divider, then **Recent Transcriptions**
  (all transcripts, filed or not, newest first). Folder rows expand/collapse and show their count.
  A transcript that is filed also stays visible under its folder.

## Transcript actions

- **Rename** (inline), **Copy Transcript**, **Download Transcript** (`.txt`), **Download Audio**
  (original bytes; hidden-when-absent is a disabled button, not a broken one), **Send to chat**,
  **Use as vetting answers**, **Think out loud**, **Delete** (confirm, states what is removed),
  **Record more** (append).

Copy and download sit at the bottom of the transcript content, as the brief requires.

## Restart story (verified live)

Record, upload, rename, file into a folder, restart the app: everything is still there, the audio is
still downloadable, and a `failed` upload still shows with "Needs attention" and its original file
name so it can be retried.
