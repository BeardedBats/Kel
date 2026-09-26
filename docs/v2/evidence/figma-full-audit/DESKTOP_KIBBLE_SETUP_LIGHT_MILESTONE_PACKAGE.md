# Desktop Kibble, Setup, Pet, Skills, and Light milestone — 2026-09-26

Disposable package source: `41a73f57cf3fff035513bc102a6b9016a8c12a9b`. Canonical App remains `8c67121`. The existing engine binary was reused; no engine source changed. All 266 renderer files match the archive, with zero mismatches. Archive SHA-256: `4a58bd05a85dffb396f22fb836689cdfe56c0c0e0feb43047ca0c47856009a4f`.

Six packaged Electron probes passed at 1440px and 800px without a source URL: populated Kibble, build variants, Setup, Pet, populated Skills, and the eight-route Light sweep. Each reported zero renderer errors and document overflow. The archived sign-in renderer also passed both widths in isolated headless Edge, served directly from the archive on loopback. That sign-in check is bundled-renderer proof; it did not run the packaged WebUI server or a real authenticated session.

| Area | Verified behavior | Evidence limits |
| --- | --- | --- |
| Kibble | Real isolated Mark fixed/Reopen/selected prompt→Batched; finding screenshot/detail layout; 279px top panels | No real worker or build execution; owned findings dismissed afterward |
| Kibble build variants | Running step 2 of 4, Cancelled, expandable details, reduced motion, Approve/Reject handoffs | Dogfood mission/status/candidate/review injected/intercepted; no build/review/install mutation |
| Setup | Real isolated Auto-model/config saves; five progress steps; selected folder→composer; setup-return banner on Knowledge | Native folder result intercepted; model/setup preference restored; no sign-in; policy selection/global folder persistence/Work-banner gap remain |
| Pet | Actual Off, disabled dependents, enable refusal→Off, reload Off | No pet window or policy change; enable needs Nick's AUD-MINOR-008 decision |
| Skills | Real isolated custom imports/list/reload; typical 58px rows; long text wraps at both widths | Owned imports deleted; no skill execution/assistant attachment; detail/import-history routes remain open |
| Light labels | Eight routes at both widths, minimum computed enabled-label contrast 4.86:1 | Disabled Pet radios excluded; icons/popups/custom colors and exact Light palette parity remain open; Dark restored |
| Sign-in archive | 420×330/y200, 34px inputs, viewport language control, show/hide, reduced motion, invalid-login handoff | Auth/settings/login intercepted; no real credential or live sign-in; password remained unsaved |

The initial package probe conversion changed the build-source-root test selector; the probe was corrected. Setup's fixture flag needed a renderer reload to refresh cached client preferences. Corrected final probes passed. Neither issue required an app repair.

The Kibble panel still has an extra 2% top sheen from shared card CSS. Current Figma exports for its three panel images are fully transparent 32×32 PNGs, overlaid with 5% pale blue. Exact Kibble panel-material parity remains open; the structural/action checks above are not complete pixel parity. Mission recovery after navigation/reload and real worker acceptance also remain open.

Representative captures: [Kibble 1440](DESKTOP_MILESTONE_KIBBLE_1440.png), [800](DESKTOP_MILESTONE_KIBBLE_800.png); [review 1440](DESKTOP_MILESTONE_KIBBLE_REVIEW_1440.png), [800](DESKTOP_MILESTONE_KIBBLE_REVIEW_800.png); [Setup 1440](DESKTOP_MILESTONE_SETUP_1440.png), [800](DESKTOP_MILESTONE_SETUP_800.png); [Pet 1440](DESKTOP_MILESTONE_PET_1440.png), [800](DESKTOP_MILESTONE_PET_800.png); [Skills 1440](DESKTOP_MILESTONE_SKILLS_1440.png), [800](DESKTOP_MILESTONE_SKILLS_800.png); [archive sign-in 1440](DESKTOP_MILESTONE_SIGNIN_ARCHIVE_1440.png), [800](DESKTOP_MILESTONE_SIGNIN_ARCHIVE_800.png).

Source verification includes the full 63-file/437-test Kibble regression, seven theme tests, TypeScript, final source builds, and measured source checks. The full suite was not repeated for the final CSS-only changes. This package supersedes package-pending statements only for the tested states.

Canonical App and Data were untouched. All test apps/browser contexts closed, synthetic imports were removed through the service, new findings were dismissed, and original model/setup/theme preferences were restored. The archive loopback server stopped. The one bounded comparison stack remains for the next desktop batch. The source preview remains owned and active for ongoing implementation. Previously blocked Workspace/work-appearance/renderer-cache cleanup remains blocked; no removal retry ran. Desktop V2-16/18/19 remain partial; mobile remains paused.
