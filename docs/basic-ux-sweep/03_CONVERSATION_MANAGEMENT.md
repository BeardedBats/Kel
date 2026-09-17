# Conversation management

| Item | Class | Evidence |
|---|---|---|
| Rename conversation | PBF → verify | the row menu opens; the rename item/flow is recorded in `sweep2` |
| Delete + confirmation | PBF → verify | menu opens; confirm modal + cancel-keeps-row recorded in `sweep2` |
| Search conversations | PAG | partial match + no-result state + clear (`searchPartialHit`/`searchNoResult` true) |
| Switch conversations | PAG | audit + drafts isolation |
| Current conversation obvious | PAG | active row highlight; title in the header |
| Survives restart | PAG | `conversationsSurviveRestart` true |
| New conversation does not corrupt others | PAG | three seeded chats stay independent; drafts keyed per chat |
| Unsent drafts not lost | **FIXED** | drafts now persist (`localStorage` mirror in `useSendBoxDraft`); `draftAfterRestart` recorded in `sweep2` |
| Archive / Pin | PAG | `conversations.pinned/archived_at` + Archived settings page (audited, untouched) |
