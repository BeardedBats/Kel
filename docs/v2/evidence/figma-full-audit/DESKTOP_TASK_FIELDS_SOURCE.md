# Desktop scheduled-task field rhythm — source evidence

Current Figma reference: `BlpVvZGuc9j9HhxUojIiJI`, `273:1586`. This increment repairs desktop field rhythm and keeps native task validation, callbacks and mobile layout.

The filled Weekdays dialog now measures 600×614px at y70 in both themes and both viewport widths. Body width is 550px; row/column gaps are 14/12px. Labels use Instrument Sans 500, 12px/15px. Name/Assistant/Time/Model fields measure 34px; Instructions measures 72px. Execution options use full borders and 10px radii. Queue copy and Advanced settings use the reference type roles. Required marks disappear visually; required validation remains. A duplicate inner modal border is removed. No colored edge is added.

Dark/Light source probes passed at 1440/800px with zero overflow and renderer errors, aligned Time/Model, 16px modal radius and 24px blur. Light sampled labels pass at least 5.39:1. Unsaved input, skip switch, Cancel/reopen and Escape passed. Dark Weekly stays below Model. Light Advanced open/close, Manual's full-width Model and Custom fields pass without horizontal overflow. No task was saved or executed. Dark was restored and probe apps closed.

The enabled catalog is still open. A real isolated provider fixture with two synthetic names did not give the existing Kel assistant a catalog. A separately created isolated assistant with requested model names also did not expose selectable models. That selection probe timed out; it is not a pass. Both owned records were deleted; assistant removal was explicitly re-read and confirmed. No credential or provider inference was used. Do not fabricate runtime capabilities to close this gap.

TypeScript, source build and 12 focused tests across three files pass. The previous full regression remains 63 files/443 tests at the Model-row increment; it was not repeated for these local styles. The probe initially used the wrong Advanced label (Workspace; native copy is Project), then checked the actual expanded container. A desktop/phone label duplication caused by the new span display rule was repaired with the existing isMobile condition and rechecked.

This closes field rhythm/height, not every task-frame detail. Picker/assistant icons, precise glass image/fill, disabled execution variants and live model catalog acceptance remain open. Package proof joins Chat rhythm/Model at the next larger milestone. Latest disposable package b8c84ae; canonical App 8c67121, Data untouched, mobile paused. request_review unavailable; no independent review claim.

Captures: [Dark 1440](DESKTOP_TASK_FIELDS_DARK_1440.png), [Dark 800](DESKTOP_TASK_FIELDS_DARK_800.png), [Light 1440](DESKTOP_TASK_FIELDS_LIGHT_1440.png), [Light 800](DESKTOP_TASK_FIELDS_LIGHT_800.png).
