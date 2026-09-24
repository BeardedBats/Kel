# Desktop Dark polish — r48–r51

**Authority:** Figma FINAL `189:2628` Scheduled tasks, `189:3098` Providers, `189:3564` Diagnostics; Components `148:229` Input states, `146:52` Dropdown, and `147:162` Lightbox glass. **Source:** `integration/v2` `56df3742ca6d9734f1771230d0dbee05e2874300`. **Profile:** disposable `r43-populated` host, store, and engine roots. All comparisons use packaged Windows candidates at 100% zoom. Phone layouts are outside this pass.

| Lock | Preserve |
| --- | --- |
| Structure | Outer and nested desktop rails, route names, panel order, task and provider data. |
| Identity | Dark canvas, blue glass panels, amber headings, Instrument Sans and SF Pro roles. |
| Behavior | Task selection, New task fields and actions, Diagnostics export, Providers preflight, Tools controls. |
| Repair scope | Desktop row geometry, 768–980px rail widths, task dialog fields, and select popup surface. |

## Matched findings

| Finding | Before | Repair and packaged evidence |
| --- | --- | --- |
| Scheduled detail lacks Figma hairlines; instructions appear as a 14px value on the right. | [r47 baseline](key/r47-scheduled-baseline.png) shows the right-side note and no row dividers. | Instructions now sit under the label in muted 12px/16px. Five real data rows retain their labels and 1px dividers. [r50 detail](key/r50-scheduled-1440.png) and [measurements](r50-desktop-followup.json) show 69px instruction, 63px value, and 45px Queue rows. Figma has no separate Queue row; this real state remains visible. |
| Diagnostics maintenance is short and lacks row dividers. | [r47 baseline](key/r47-diagnostics-baseline.png) has a 165px panel without row dividers. | [r48](key/r48-diagnostics-1440.png) shows hairlines. [r49 measurements](r49-desktop-check.json) show 202px panel and two 64px action rows, matching the FINAL panel height closely. Clear and Restart remain disabled because the runtime operations do not exist. |
| At 800px, the 256px outer rail plus 200px nested rail squeeze action labels and cards. | [r48 Scheduled](key/r48-scheduled-800.png) wraps New task inside its button; [r48 Diagnostics](key/r48-diagnostics-800.png) wraps Export and issue report. | The 768–980px desktop rails now use 180px and 150px, with a 16px pane inset. [r49 Scheduled](key/r49-scheduled-800.png), [Diagnostics](key/r49-diagnostics-800.png), [Providers](key/r49-providers-800.png), [Tools](key/r49-tools-800.png), and [Appearance](key/r49-appearance-800.png) show readable controls. [r49 measurements](r49-desktop-check.json) show no document overflow or clipped header button at 1440, 800, or 768px. |
| New task uses gray square fields instead of the Figma Input component. | [r49 dialog](key/r49-new-task-dialog.png) had a 32px square Name field and gray body. | [r50 dialog](key/r50-new-task-1440.png) uses a 34px, 8px blue glass Name field, Select, and Textarea. [Focus](key/r50-new-task-focus-1440.png) has an accent ring. [r50 measurements](r50-desktop-check.json) show Cancel closes the dialog at 1440 and 800px. |
| Assistant select popup lets the Execution Mode label show through. | [r50 open menu](key/r50-new-task-assistant-open.png) shows the bleed. | r51 uses Components `146:52` opaque Dark gradient for desktop select popups. [1440px](key/r51-new-task-assistant-1440.png) and [800px](key/r51-new-task-assistant-800.png) captures cover the label. [Package measurements](r51-desktop-check.json) show the same gradient and working Cancel at 1440, 800, and 768px. |

The [r50 local preflight](key/r50-providers-preflight-1440.png) chose Claude and reported a DeepSeek key gap. This checks the actual readiness view, not a model response. The [captured text](r50-desktop-followup.json) retains the reason and chain. Figma shows illustrative rows; live provider names, state, and reasons differ by installed configuration.

## Scope and remaining gaps

The Figma Scheduled detail shows editable Assistant, Model, and Execution mode controls. The current detail is read-only; the working New task dialog provides those controls. Figma's sample schedule and history differ from this disposable profile's manual tasks. A populated execution history, a real long transcript, remote response, and service-backed states still need evidence. Exact product-wide parity is not established. Faint Light-mode labels stay outside this Dark pass. No independent review occurred because `request_review` was unavailable.

| Category | Baseline → r51 | Evidence and limit |
| --- | --- | --- |
| Hierarchy and comprehension | 3 → 4 | Instruction text now follows its Figma label; real Queue state remains visible. |
| Typography and readability | 3 → 4 | 12px instruction metadata and usable 768/800px desktop controls. |
| Geometry and rhythm | 2 → 4 | Figma row dividers, 202px Diagnostics maintenance, wider narrow desktop pane. |
| Component and interaction craft | 2 → 4 | Input, focus, select popup, Cancel, task selection, and preflight checked. |
| Responsive and accessibility integrity | 2 → 4 | Checked desktop widths have no document overflow; keyboard and assistive technology need a separate pass. |
| Fidelity to approved direction | 3 → 4 | FINAL panels and Components tokens guide the repairs; live values stay truthful. |
