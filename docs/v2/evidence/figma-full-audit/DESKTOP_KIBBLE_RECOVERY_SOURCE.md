# Desktop Kibble mission recovery — source increment

Desktop Kibble stores only its last mission ID in the existing client-settings service. The engine remains authoritative for mission, job, source folder, and candidate review state. Opening Kibble reads status; it never starts work or assembles a candidate. The Start control waits for initial recovery. The mobile flow is unchanged.

Recovery keeps fixes available when the previous update cannot load and offers Refresh. If a mission starts but saving the pointer fails, the mission remains visible and the page explains the persistence failure. An approved candidate remains approved after recovery. This pointer supports one last displayed mission; it is not a mission-history browser or a second work database.

The extra 2% shared-card sheen was removed from desktop Dark Kibble panels. Current Figma's three exported panel images are fully transparent 32×32 PNGs; the specified pale-blue 5% wash now matches the measured computed background. Custom panel colors and desktop Light remain unchanged.

Ten focused tests passed across Kibble DOM and build-summary files. Three new behavioral tests cover approved-state recovery without start/candidate writes, unavailable-status recovery without hiding fixes, and pointer-save failure after a successful start. TypeScript, source build, and the full desktop suite passed: 63 files / 440 tests.

An isolated source-render probe used real client-settings writes and intercepted Dogfood mission/start/status records. Navigation away and back, full renderer reload, source-folder restoration, and approved-review preservation passed at [1440px](DESKTOP_KIBBLE_RECOVERY_SOURCE_1440.png) and [800px](DESKTOP_KIBBLE_RECOVERY_SOURCE_800.png). The call record contained one intercepted start and five status reads; no candidate/review/install operation ran. Both widths had zero renderer errors or overflow and the correct 5% background. No actual worker or mission execution occurred. The original pointer setting was restored. The first probe's injected list handler omitted an optional-body guard; correcting the probe resolved that failure without an app change.

Canonical App/Data were untouched. The latest disposable package remains 41a73f5 and predates this recovery/material increment. Package proof waits for the next larger desktop milestone. Real worker acceptance, legacy missions without a saved pointer, and a full history surface remain open. No mobile work resumed.
