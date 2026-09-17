# Search and discoverability

| Item | Class | Evidence |
|---|---|---|
| Search conversations | PAG | Sider search popover: partial term, no-result state, clear, keyboard focus (audit) |
| Search transcripts | **Implemented** | engine `/api/search` matches transcript titles and text with snippets |
| Search Vetting sessions | **Implemented** | topic + question matches with plain hints |
| Search chats (engine content) | **Implemented** | titles and message text with snippets |
| One obvious search experience | PAG | the palette (`Ctrl+K`, `/`) shows Actions + Go to + found Chats/Transcripts/Vetting/Jobs/Knowledge/Recipes/Roles |
| Human queries, partial matches | PAG | case-insensitive substring matching; metacharacters escaped |
| Remainder (honest) | Documented | work results, artifacts and the knowledge map keep their own surfaces for this pass; the engine search is the architecture they extend |
| Command palette completeness | **Fixed** | New Chat, Transcription, Settings (+appearance/system) added as Go-to entries; Actions: theme switch, Start design vetting (composer prefill). Only actions that actually run are listed |
| Keyboard shortcuts reference | PBF | the palette footer documents its own keys; a global shortcut sheet stays optional (few global keys today) |
