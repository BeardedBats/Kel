# Desktop source completion milestone package — 2026-09-26

The existing disposable package was rebuilt once at source `b8c84aec00b5f3aee39e658d459b3014e5db3618`. This groups Setup retention, Workspace/Light files, Light Ramble dialogs, populated Chat type, Light Tools dialogs, and the Light task form. No numbered candidate or new test root was created. Canonical App remains `8c67121`; canonical Data was untouched. Mobile stays paused.

Windows directory packaging and native-module rebuilding passed. All 266 renderer files match the archive. Archive SHA256: `19518a8f63d22a95e0eea7e8a3a0136378a7cdcb24731436366896ba82f64b4b`. The final desktop regression passed 63 files / 443 tests. Its existing MaxListenersExceededWarning appeared; no test failed. The package uses its normal bundled renderer, with no Vite URL, CSS injection or legacy-history interception.

Eight sequential grouped probes passed at 1440/800px:

- Setup: real isolated folder-draft write/reload, canceled picker, Work return and Chat gate. Native picker results were intercepted; completion stayed false during the check.
- Legacy Workspace: native titlebar collapse/reopen, 48px header position, 340/260px open widths and zero collapsed width, Dark/Light.
- Light Workspace/File: real synthetic file/SCM reads, Files/Changes/menu, read-only protection, code/split/action menu and sampled readable labels. No file edit/save/attachment/download ran.
- Light Ramble key/Merge: unsaved input, Cancel/reopen/Escape, real synthetic recording choices and keyboard selection. No key save or Merge submission ran; owned recordings were deleted.
- Light Vetting: real preview rechecks, 620px modal at y70, original saved transcript preserved. No Process/Accept ran.
- Populated Chat: three stored synthetic turns, 14px list gaps, 13px/16px timestamps, 24px avatar slot/22×23 mark, Dark/Light and last-turn wheel scrolling. Native engine history remained visible and untouched. Original fixture records were restored in both native databases.
- Light Tools: JSON validity, intercepted five-row CLI catalog/count/disabled auth row, Back/Cancel, unsent report input and Keep. No server add/import/delete/test/report/provider ran.
- Light task: existing assistant selection, unsaved fields, Weekdays, skip switch, Cancel/reopen and Escape. No task was saved, created or run.

Each probe reports zero renderer errors and zero document overflow. Scoped internal-overflow assertions also passed. All apps closed. Isolated client/panel/history preferences and Dark were restored. No active Chat restoration journal remains.

Two initial probe assumptions needed repair, without product changes. Native hash-only Setup navigation retained the pre-write settings cache; a full reload then passed. The first Chat assertion selected an older engine-history assistant; the final assertion targets the three owned fixture IDs and preserves the six history rows. These initial failures are not claimed as product regressions.

Representative bundled captures: Setup [1440](DESKTOP_SOURCE_MILESTONE_SETUP_1440.png), [800](DESKTOP_SOURCE_MILESTONE_SETUP_800.png); files [1440](DESKTOP_SOURCE_MILESTONE_FILES_1440.png), [800](DESKTOP_SOURCE_MILESTONE_FILES_800.png); Vetting [1440](DESKTOP_SOURCE_MILESTONE_VETTING_1440.png), [800](DESKTOP_SOURCE_MILESTONE_VETTING_800.png); Chat [1440](DESKTOP_SOURCE_MILESTONE_CHAT_1440.png), [800](DESKTOP_SOURCE_MILESTONE_CHAT_800.png); Tools CLI [1440](DESKTOP_SOURCE_MILESTONE_TOOLS_1440.png), [800](DESKTOP_SOURCE_MILESTONE_TOOLS_800.png); task [1440](DESKTOP_SOURCE_MILESTONE_TASK_1440.png), [800](DESKTOP_SOURCE_MILESTONE_TASK_800.png).

This closes package proof for these scoped source batches. It does not close full Chat placement/sidebar/footer facts, task field/model presentation, remaining Light/icon parity, Skills detail/history, live worker/provider/remote acceptance, or full V2-18 journeys/V2-19 regression. The historical failed-status popover and enabled Image Model records were not rerun against current Figma. Canonical App promotion still waits for broader desktop acceptance. `request_review` was unavailable; no independent review is claimed.
