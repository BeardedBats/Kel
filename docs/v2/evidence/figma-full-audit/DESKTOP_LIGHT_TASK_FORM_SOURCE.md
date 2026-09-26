# Desktop Light scheduled task form — 2026-09-26

Current new-task frame `273:1586` was refreshed directly. This increment repairs the existing desktop Light form. Mobile, task authority, schedule calculation, model resolution, and saving are unchanged. Figma supplies Dark geometry; exact Light palette parity is not claimed.

Before repair, execution labels measured 1.02–1.17:1 and frequency choices 1.51–1.56:1. The modal lacked blur and sat at y73. Both 1440px and 800px now pass centered 600px width, y70, 16px radius, 24px blur, zero internal/document overflow and zero renderer errors. Current Light content measures 610px high. Neutral rounded fields, execution selection, Time label, frequency choices, skip switch and green Create task action use the existing semantic Light palette. Sampled enabled labels pass at least 5.39:1. Field values, pseudo-element Time text and pixel-level icons are not part of the sampled-label contrast claim; their visible surfaces were inspected separately.

The real isolated form selected the existing Kel assistant, accepted unsaved name/instructions, selected Weekdays, and changed the skip switch. Cancel closed the form; reopening cleared the canceled name. Escape closed it. No task was created, saved, or run. No provider request or canonical Data access occurred. The isolated theme returned to Dark and each app closed.

TypeScript, source build and 12 focused theme/job-label tests across three files passed. The latest broader desktop suite remains 63 files / 443 tests from Setup. Package proof waits for the larger desktop milestone. This is Light readability/geometry evidence, not complete task-frame acceptance: field spacing, Time presentation, required marks and the Model control pictured beside Time still need disposition. Current model configuration remains inside Advanced settings when the actual assistant exposes models; no illustrative Automatic state was invented.

Captures: [1440](DESKTOP_LIGHT_TASK_FORM_1440.png), [800](DESKTOP_LIGHT_TASK_FORM_800.png). Canonical App remains `8c67121`; Data untouched. Mobile stays paused. `request_review` was unavailable; no independent review is claimed.
