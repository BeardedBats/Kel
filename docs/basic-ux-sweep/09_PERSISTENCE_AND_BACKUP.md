# Persistence and backup

## What persists

Chats, projects, work state, Vetting sessions, transcripts + audio, attachments, engine settings,
model choices, theme overrides and composer drafts all survive restart (battery re-runs).

## Backup (new)

- `Backup.create(target)` writes `Kel-Backup-<timestamp>/` containing the engine data tree and a
  `BACKUP-INFO.json` (format, date, item counts, notes).
- **Credentials are excluded**: `transcription_settings.meta_api_key` is deleted from the copied
  database; desktop provider keys live outside the engine data under OS-level encryption and are
  never copied.
- **Runtime state is excluded too**: the engine database is copied through SQLite's own hot-copy API
  (sidecar files are never copied), and the host's Chromium user-data tree (caches, storage and the
  locks the running app holds open) is not part of a backup — only its `config/` (settings, skills,
  assistants) is. Logs, session markers and the controller lock are skipped. Anything that still
  cannot be read is named under `skipped`/`notes` in the backup description instead of failing the
  whole copy, so “Back up now” works while Kel is running.
- `Backup.inspect(folder)` validates a candidate backup and returns the summary the confirm dialog
  shows (no blind overwrites).
- `Backup.stage_restore` copies the backup into `.restore-staging/` and writes a marker;
  **the restore applies at the next engine start before any connection opens**, so an interrupted
  copy can never leave a half-restored database. The previous data is kept beside the data folder
  as `.pre-restore-<timestamp>`.
- Recovery test: the final battery re-runs it — `sweep4` deletes a transcript, restores from the
  backup folder, restarts Kel and checks the rows came back (evidence in `15_FINAL_VERDICT.md`).

## Data location

Settings · System → “Data folder”: shows the path, copies it, and reveals it in the file manager.
Internal database files are never the primary experience.
