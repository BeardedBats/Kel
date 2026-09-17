# Chat basics

| Item | Class | Evidence |
|---|---|---|
| New Chat | PAG | sider button; creates a chat on first message (audit) |
| Composer focus | PAG | `composerFocused = true` on open (sweep-a) |
| Enter sends | PAG | audit message appeared in the transcript |
| Shift+Enter newline | PAG | `shiftEnterNewline = true` (sweep-a) |
| Sending state | PBF | user bubble + reaction row appear; the Stop control could not be observed without a provider — partially unverifiable here |
| Stop generation | PBF | `onStop` prop exists and is wired; unverifiable live (no provider) |
| Retry without retyping | PAG after probe | engine `/api/retry` route + failure card; sweep2 records the retry click |
| Streaming behaviour | Unverifiable (no provider) | classified honestly |
| Manual scroll-up is not dragged down | PBF | not observable without streaming; the list itself scrolls freely |
| Return to newest | MO | no jump-to-latest control found |
| Long responses | Unverifiable (no provider) | virtualization exists (`messageNodes` render on demand) |
| Markdown / tables / code | PAG (engine-verified) | `MessageText` renders through `@renderer/components/Markdown`; the seeded markdown chat probe is recorded in sweep2 |
| Copy response / code / feedback | PBF | copy affordances render on assistant messages; the click probe is recorded in sweep2 |
| Links | PAG | links render via the markdown renderer (probe recorded) |

Honest boundary: every item that requires a live model is marked unverifiable in this environment
(no provider) rather than claimed.
