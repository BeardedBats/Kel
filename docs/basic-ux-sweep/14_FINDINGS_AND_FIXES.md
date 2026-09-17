# Findings and fixes

| # | Finding (audit) | Class | Fix |
|---|---|---|---|
| F1 | Substantial unsent drafts were lost on restart (in-memory only) | UX-P1 | drafts mirrored to `localStorage` per conversation; restart keeps them |
| F2 | No explicit “Default Kel model” for normal chat | UX-P1 | engine `model_prefs` + `/api/model` + Settings · Model card (Auto + models, availability chips) |
| F3 | Kel chats had no per-conversation model choice (read-only “Automatic”) | UX-P1 | “Kel model” pill in the chat header: Use global default / Automatic / model list + Details |
| F4 | No way to adjust the selected theme's foundation colors without editing CSS | UX-P1 | semantic Theme colors section with picker/hex/reset/restore, live apply, per-theme scope, contrast warnings |
| F5 | Palette missed core actions (New Chat, Transcription, Settings, theme, Start vetting) | UX-P2 | Go-to entries + verified Actions; only real actions listed |
| F6 | Search covered chats only | UX-P2 | engine `/api/search` (transcripts, vetting, chats) surfaced in the palette; remainder documented |
| F7 | No user-facing data location or backup | UX-P2 | Settings · System “Data folder” + local backup/restore with validation, secret exclusion, staged restore |
| F8 | A polish bug found by the audit probe: review hint example used an unparseable code | UX-P3 | hint now uses a valid example (fixed and re-probed earlier in this thread) |
| F9 | Providers/Long surfaces scroll case (user-reported class) | Regression | proven across surfaces (matrix + DeepSeek provider field case in `sweep4`) |
| F10 | Retry/stop/streaming live behaviour | Unverifiable (no provider) | engine + UI wiring verified; classified honestly, not claimed |
| F11 | **The whole app could blank** (Settings · Model and any Kel chat): `action=get` answered without `providers`, `KelModelControl` crashed on `state.providers.map(...)`, React unmounted the page | UX-P0 (regression, found by the as-built battery) | `get`/`list` answer one payload (stored choice + provider listing) and the control paints a plain unavailable state instead of assuming the list exists |
| F12 | Backup failed while Kel was running: `WinError 32` on `controller.lock` and on Chromium's `host/Network/Cookies`, so “Back up now” answered “could not finish that just now” | UX-P1 | runtime state is no longer copied (logs, session markers, lock; inside `host` only the settings and the chat databases), the databases are hot-copied through SQLite, and a file that still cannot be read is named under `skipped`/`notes` instead of failing the backup |
| F13 | The Theme colors section never learned about its own changes: contrast warnings never appeared and “Restore all colors” was never offered, so a colour change could not be undone from that screen | UX-P2 | the rows' `onChanged` is wired to the section refresh (warnings recompute, restore affordance appears) |
| F14 | Audit probes measured the wrong things: text size/zoom via a CSS font size on a page the control is not on, contrast with a dark-theme assumption, markdown before the newest message was mounted, and row menus via the first match in the DOM | process | probes now read the window's real zoom factor (after a Ctrl+0 reset), drive Ctrl +/−/0 through Electron's input path, force a genuinely low-contrast pair, scroll to the newest message first, and target the hovered row's menu |
| F15 | **The probe was blind to shadow DOM**: assistant replies render through `MarkdownView`, which mounts its body inside a shadow root (`components/Markdown/ShadowView`); light-DOM `innerText`/`querySelectorAll` never see it, so markdown, copy-button and failure-surface checks reported "absent" for content that was on screen | process (instrument) | probes walk shadow roots (`walk`/`deepText`); the app was **not** changed — the rendering itself was verified correct inside the shadow root |
| F16 | **The seeder corrupted its own rich message**: `seed-sweep.py` joined the already-joined markdown block again (`'\n'.join(rich)`), storing the reply **one character per line**, so the markdown probe could never find the text and the "table" was never a table | process (instrument) | the seeder inserts the block as-is; the as-built sweep2 run then finds the message, its table, code and links |

Rules: each fix maps to JR-41..JR-47 (`docs/product/USER_JOURNEY_STANDARD.md`), history H22.
