# Desktop Light startup and shared dialogs — source repair

This batch repairs Starting, stopped engine, diagnostics export, Update available, and task-delete confirmation in desktop Light. Existing semantic colors replace pale Dark labels and surfaces. Update and Delete now retain the shared desktop Figma position and width in Light. The stopped-engine wrapper no longer adds an inner surface. Light uses neutral full borders, 16px radii, existing shadow/scrim, and solid semantic primary buttons. Desktop Dark and mobile rules remain unchanged.

The before-check found Update at 526.31px wide and y320.5, with title contrast 1.12:1 and secondary contrast 2.38:1. Current Figma specifies a 500px dialog at y220. Current Foundations contains no complete Light palette; this establishes shared geometry and measured readability, not exact Light color parity.

| State | Measured at 1440 and 800 | Interaction proof |
| --- | --- | --- |
| Starting | 440×330, y260 | Injected slow startup; readiness removes view; reduced motion stops spinner |
| Stopped engine | 560×466, y200, expanded details | Injected failure; actual isolated diagnostics read; intercepted clipboard handoff |
| Diagnostics export | 560×406, y120 | Actual isolated receipt read; note entry; Escape |
| Update available | 500×261, y220 | Injected versions/notes; Later and Escape |
| Delete task | 460×146, y300 | Intercepted task record; Keep and Escape |

All five states passed both widths with zero document/internal overflow and zero renderer errors. [Computed measurements](desktop-light-dialog-measurements.json) report a minimum enabled-label ratio of 4.86:1. All primary button labels were measured on solid fills. Measurements use ancestor-composited backgrounds, not pixel-level anti-aliasing. Neutral startup icon tint is applied, without a pixel-level icon contrast claim.

Screenshots: [Starting 1440](DESKTOP_LIGHT_STARTUP_1440.png), [800](DESKTOP_LIGHT_STARTUP_800.png); [Stopped 1440](DESKTOP_LIGHT_STOPPED_ENGINE_1440.png), [800](DESKTOP_LIGHT_STOPPED_ENGINE_800.png); [Export 1440](DESKTOP_LIGHT_DIAGNOSTICS_EXPORT_1440.png), [800](DESKTOP_LIGHT_DIAGNOSTICS_EXPORT_800.png); [Update 1440](DESKTOP_LIGHT_UPDATE_1440.png), [800](DESKTOP_LIGHT_UPDATE_800.png); [Delete 1440](DESKTOP_LIGHT_DELETE_1440.png), [800](DESKTOP_LIGHT_DELETE_800.png).

Ten focused theme/input/update tests passed across three files. The final source build passed. This CSS-only batch did not repeat the previous 63-file/440-test regression. It made no engine restart, diagnostics export, update download/install, or task deletion. Light was selected through the real isolated theme control and Dark restored after each probe. App and durable Data were untouched. Package proof waits for the next larger milestone.
