# Ramble sidebar and header repair

Baseline: `681e005740642e5a0b5ccc022e1c3aa776f7ce88`, existing `ux/v2-shell` worktree.
Authority: the user's Ramble screenshot and explicit layout and inline-folder instructions.

Restore the requested sidebar and page header while keeping Kel typography, palette and transcription behavior.

| Lock | Record |
|---|---|
| Structure | Existing library and transcript panel; user explicitly moves navigation, search and API Key, adds a page title, removes footer |
| Identity | DS v2 Instrument Sans and SF Pro Text; existing glass panels and input tokens |
| Content | Real library and transcripts; new folder defaults to New Folder |
| Behavior | Existing record/upload, search, drag-to-folder, API settings, navigation and persistence handlers |
| Repair scope | Ramble page and CSS; shared titlebar slot limited to Ramble desktop; affected tests |

Baseline captures: `evidence/ramble-sidebar/before-desktop.png` (1440 x 900) and `before-phone.png` (393 x 852), dark theme, isolated local WebUI data.

## Delivered

- Desktop titlebar navigation now renders in the Ramble sidebar beside the Kel logo. Native window buttons stay in the titlebar. Other routes and the existing phone titlebar keep their previous controls.
- Search transcripts moves above Folders, with the previous folder field's control fill, edge, radius and height.
- The right-aligned + creates a persisted New Folder. Its inline name receives focus and full selection. Enter or blur saves; Escape or a blank draft retains the previous name. Failed saves keep the draft.
- Ramble uses the shared 26/32 semibold title style. API Key sits immediately before Upload Audio. The provider footer and its bottom divider are removed.
- Section labels retain DS v2 12/16 typography. This approved product token overrides the general polish skill's label floor.

## Verification

- TypeScript no-emit check and production build passed. Existing chunk-size warnings remain.
- Unit checks: 2/2. Creation, selected input, one Enter save, Escape, blank names, and draft retention after a failed save.
- Browser checks: 3/3. Actual isolated engine folder creation, rename, reload persistence and test-folder deletion; API Key dialog; upload chooser; navigation portal mount/unmount; back/forward; conversation search; transcript-name/body filtering with a labeled fixture; 1440, 1024, 393 and 360px layouts without page overflow.
- Native Electron check: 1/1. Ramble toolbar/header and neighboring native settings remain connected. Window controls stay at the top right.
- The first browser check used an incorrect English search label. The corrected locator uses the existing Search messages text; it passed. The first unit error came from the isolated test's toast renderer; the test now spies on the error notification and verifies draft retention.
- Provider transcription, microphone capture and external credential changes were not exercised. No claim of full-app visual parity or formal accessibility certification.

## Scoped self-review

| Category | Before | After | Evidence |
|---|---|---|---|
| Hierarchy and comprehension | 3 | 5 | Main Ramble title; actions grouped with API Key |
| Typography and readability | 4 | 5 | Shared title style and readable search field |
| Geometry and rhythm | 3 | 5 | Navigation top aligned with logo; search before Folders; + aligned right |
| Component and interaction craft | 3 | 5 | Focused inline creation with saved-name recovery |
| Responsive/accessibility integrity | 4 | 4 | Desktop and phone captures, keyboard editing and labeled controls; existing phone library scroll remains |
| Fidelity to approved direction | 3 | 5 | Requested changes applied without altering palette, fonts or transcript workflow |

Before and after PNGs and runner logs are in `evidence/ramble-sidebar`. Review is local self-review, not an independent review.
