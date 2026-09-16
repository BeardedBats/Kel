# Persistence and restart

## What must survive a restart

| Data | Where | Proof |
|---|---|---|
| Conversations/chats, projects, autonomy settings | engine sqlite (see `evidence/databases.txt`) | `tour`, `first-run` re-runs |
| Vetting sessions, answers, revisions, decisions, conflicts, spec | migration v11 tables | `vetting` (b2) + `voice-vetting` restart step: review modal opens after relaunch |
| Transcripts (text, duration, folder, status), audio files | migration v12 tables + audio directory | `transcription` `rowsAfterRestart`, `voice-vetting` `rowsAfterRestart` |
| Composer draft handoff | renderer one-shot (`kel.transcription.draft`) | consumed-and-cleared on `/guid`; nothing persists by design |

## Restart behavior verified

- Relaunch keeps transcript rows **and** their audio (`has_audio` still true; export audio works).
- A vetting session answered over voice before restart is still the active session after restart;
  the page's review finds it without a conversation id (`voice-vetting`).
- The engine is stopped with the app (`engineKilled` flag in every scenario: clean shutdown, no
  stray processes).

## Clean state

- Fresh roots (no prior data) run the first-launch suite; an empty transcription library shows the
  KelEmpty state ("Nothing here yet.") instead of a blank pane (`hardening` `emptyState`).
- Migrations are additive and versioned (`v15-vetting` = 11, `v15-transcription` = 12); a database
  created before either migration upgrades in place (engine suite covers both paths).
