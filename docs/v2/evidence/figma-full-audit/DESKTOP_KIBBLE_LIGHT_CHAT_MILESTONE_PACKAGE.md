# Desktop Kibble recovery, Light menus/dialogs, and Chat milestone — 2026-09-26

Disposable package source: `0b49b56a30bcfae55a20f8f1159db8d124d0c587`. Canonical App remains `8c67121`. The existing engine binary was reused; no engine source changed. All 266 renderer files matched the archive before the next source batch. Archive SHA-256: `3cf32b5e4d4076b243f7a9b0c25e9ae6806974b55de1c45adccf0bc8f2297744`.

Eight grouped packaged Electron probes passed at 1440px and 800px: Light startup, stopped engine, update, diagnostics, delete, menus, Kibble recovery, and Chat tool/plan/reply actions. Four further probes passed Light error and reconnecting at each width. They loaded the normal bundled renderer without a source URL or legacy-history interception. All reported zero renderer errors and document overflow.

| Area | Verified result | Evidence limits |
| --- | --- | --- |
| Light startup/shared dialogs | Starting 440×330, stopped engine 560×466, export 560×406, update 500×261, delete 460×146; full borders, 16px modal radii and 24px blur | Startup/failure/update/task states injected/intercepted; copy intercepted; no restart/export/download/delete executed |
| Light menus | Model, Project, Memory, Permission, Attach and Slash; no clipping; scoped label contrast remains at least 4.81:1 | Memory/catalog/picker calls intercepted; picker canceled; gradient Accept and pixel-level icon contrast excluded |
| Kibble recovery | Real isolated client pointer write survives navigation/reload; candidate/review returns; APPROVED preserved; repaired 5% panel sheen | Mission start/status intercepted; one start and five reads; no worker, approval or installation |
| Chat tool/plan/reply actions | Dark/Light collapsed and expanded; 52px plan, usable narrow current step; one action row below tools; original reply Copy handoff; real reaction write | Synthetic native messages and injected plan; clipboard intercepted; no provider/fork/tool execution |
| Light error/reconnecting | Disclosure/model picker, retry presentation, reduced motion, hidden composer during reconnect, restored composer afterward | Runtime states injected; no actual provider retry or network outage |

The first stopped-engine measurement ran during its opening animation. Waiting for the animation to finish corrected the probe. The final dimensions pass. No source repair or repeated startup check was needed.

The package closes only these scoped pending checks. It does not establish complete frame parity. Populated Chat placement, typography, the narrow right-panel header/native-control overlap, retained task/Tools states, Light Workspace/dialog/icon states, and the exact Light palette remain open. Current Figma Foundations provide Dark tokens only. This package predates the next Setup folder-retention/Work-banner increment.

Representative captures: [Kibble 1440](DESKTOP_RECOVERY_PACKAGE_1440.png), [800](DESKTOP_RECOVERY_PACKAGE_800.png); [Light menus 1440](DESKTOP_LIGHT_MENU_PACKAGE_1440.png), [800](DESKTOP_LIGHT_MENU_PACKAGE_800.png); [Light stopped engine 1440](DESKTOP_LIGHT_STOPPED_PACKAGE_1440.png), [800](DESKTOP_LIGHT_STOPPED_PACKAGE_800.png); [Light replies 1440](DESKTOP_LIGHT_REPLIES_PACKAGE_1440.png), [800](DESKTOP_LIGHT_REPLIES_PACKAGE_800.png).

Source verification includes TypeScript, source builds, focused tests for each functional batch, and the full 63-file/440-test desktop suite after reply-action changes. Package/native SQLite checks passed. The full engine suite was not repeated because no engine source changed.

Canonical App and Data were untouched. All probe apps closed. Original isolated theme, model, mission pointer and reaction state were restored. No provider or worker ran. The one bounded comparison stack remains for ongoing desktop work. Blocked Workspace/work-appearance/generated-renderer-cache removal was not retried. Mobile remains paused; V2-16/18/19 remain partial. `request_review` was unavailable; no independent review is claimed.
