# Desktop Light Ramble dialogs — 2026-09-26

Current references remain API key `273:10383`, Merge `273:10599` and Vetting `273:10837`. Light now retains their desktop positions, widths, padding, full borders, 16px radii and 24px blur. It uses the existing semantic palette for surfaces, fields, labels, selected rows, flags and actions. Dark and mobile remain unchanged. The desktop document menu uses the same Light surface and readable labels.

Both desktop widths passed source-render checks. API key measured 480×212 at y240; Merge measured 520×500 at y200 with seven actual isolated choices; Vetting measured 620×354 at y70 with actual preview content. Merge height follows its available records. No viewport or internal overflow and no renderer errors were reported. Minimum sampled label contrast was 4.76:1, including the selected mark; Vetting metadata measured 4.83:1. Pixel-level icon and unmeasured field-value contrast remain excluded.

API key input, enabled Save control, Cancel, reopening with an empty field and Escape passed. No key was saved, disconnected or verified against a service. Two owned synthetic recordings supplied Merge choices. Radio selection, arrow keys and cancellation passed; Merge was not submitted. Both recordings were removed through the isolated service. Real Vetting preview rechecks passed; the original saved transcript remained unchanged. Process batch and Accept all were not submitted. Dark was restored and both test apps closed.

TypeScript, source build and 14 focused Ramble/transcription/input tests across three files passed. The latest broader desktop suite remains 63 files / 443 tests from the Setup behavior batch. Package proof waits for the next larger milestone. Canonical App remains `8c67121`; durable Data untouched. No microphone, Muse request, credential write or provider execution occurred.

Captures: [API key 1440](DESKTOP_LIGHT_RAMBLE_KEY_SOURCE_1440.png), [800](DESKTOP_LIGHT_RAMBLE_KEY_SOURCE_800.png); [Merge 1440](DESKTOP_LIGHT_RAMBLE_MERGE_SOURCE_1440.png), [800](DESKTOP_LIGHT_RAMBLE_MERGE_SOURCE_800.png); [Vetting 1440](DESKTOP_LIGHT_RAMBLE_VETTING_SOURCE_1440.png), [800](DESKTOP_LIGHT_RAMBLE_VETTING_SOURCE_800.png).

This is scoped Light dialog evidence, not full Ramble frame or Light palette acceptance. Populated Chat placement/typography, retained Tools/task states, broader Light dialog/icon states and live acceptance remain open. Mobile stays paused. `request_review` was unavailable; no independent review is claimed.
