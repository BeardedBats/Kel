# Navigation and settings

| Item | Class | Evidence |
|---|---|---|
| Back behaviour sensible | PAG | titlebar back/forward buttons (audit inventory) |
| Settings → return restores context | PAG | “Back to Chat” from settings; landing state preserved |
| Work / Projects / Transcription / Vetting don't strand | PAG | every page reachable and returnable (`tour`, `maintext`, battery re-runs) |
| No dead routes | PAG | route matrix probed in `sweep2`; zero console errors |
| No unexpected resets | PAG | drafts + active chat + theme survive navigation and restart |
| Scroll position | Not asserted | classified as a testing gap; layout contract is owned by the shell container |
| Settings save behaviour | PAG | instant-apply with visible feedback (theme, model, appearance all say so in copy); leaving a page keeps changes |
| Settings persist after restart | PAG | theme/model/draft/appearance verified across restart |
| Every settings page scrolls | PAG | appearance/system pages hold the scroll container and reach their last control (matrix + sweep3) |
| No raw localization keys | PAG | sider/maintext scans + hardening jargon scan `[]` |
| No duplicate/conflicting controls | PAG (noted) | theme is reachable from footer toggle, Appearance and the palette action — conveniences, not conflicting sources (one store) |
| Advanced controls secondary | PAG | advanced provider/diagnostics surfaces stay under Settings |
