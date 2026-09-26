# Desktop Setup folder retention and Work return — 2026-09-26

Current Figma references: Setup `189:4492` and Setup still open `273:13646`. This increment completes two behavior gaps behind the existing desktop presentation. Autonomy selection remains open pending Nick's decision about edit permission.

Setup saves the selected folder as the client draft `kel.setupWorkspace_v1`. It restores that draft on a fresh desktop mount without completing setup or changing the global workspace. A current folder choice wins over a late saved read. Canceling the picker preserves the draft. A save failure keeps the current choice usable and shows an explicit retry message.

Desktop `/work` is now available while setup remains open. The existing warm setup banner returns to Setup, where the saved folder remains selected. Chat, new Work/recipe paths and mobile Work remain gated. No engine authority or permission mode changed.

The real isolated client settings endpoint confirmed the draft write and reload. Work and its return banner passed at 1440px and 800px; the banner measured 670×56 and 388×58 respectively. Continue setup, fresh reload, canceled picker, Work→Setup return, unchanged completion flag and Chat redirect passed. The native folder result was intercepted; this was not a physical OS-picker check. No chat/provider/job was started. All renderer errors and document overflow were zero.

TypeScript, source build, seven focused tests across two files, and the full 63-file/443-test desktop suite passed. The suite emitted its existing MaxListenersExceededWarning. Tests include save failure, folder handoff, restored draft and desktop/mobile route boundaries.

Captures: [Work 1440](DESKTOP_SETUP_WORK_RETENTION_1440.png), [800](DESKTOP_SETUP_WORK_RETENTION_800.png); [retained folder 1440](DESKTOP_SETUP_RETAINED_FOLDER_1440.png), [800](DESKTOP_SETUP_RETAINED_FOLDER_800.png).

This source increment is not in the `0b49b56` milestone package. Canonical App remains `8c67121`; durable Data was untouched. The probe restored the prior isolated completion flag, folder draft and workspace history. Its app closed. Autonomy selector semantics, broader populated Chat/Tools/task states and Light Workspace/dialog/icon coverage remain open. Mobile stays paused. `request_review` was unavailable; no independent review is claimed.
