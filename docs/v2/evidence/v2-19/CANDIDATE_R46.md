# V2-19 r46 — populated Dark phone audit

**Source:** `integration/v2` commit `70248659853d71e2b97a07ccc16b165526b6636f`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r46`, staged and not promoted. The full unpacked runtime and `Run-Kel-V2-Candidate-r46.cmd` are present. The launcher points to fresh, separate `C:\Users\Nick\KelV2Runs\prepared\r46\{host,store,engine}` roots. UI checks used the disposable `r43-populated` roots, not the protected stable or r20 data. r44 and r45 remain preserved intermediate candidates.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `1E6ACC2F412CB9776DEB05BE99BEA324D4C3907EBA64065B26A714EC7FDF3510` |
| `Kel.exe` | `F26B8DFABE89DC4762BD6CE5910AF4E57EB12FBAE4B9CCF84943DC212FCADB28` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r46.cmd` | `0F23366B76E1E0DFF7E437F1DCBF5297AB0631ACD8205E3FFCF5BC2A6780790B` |

The staged archive hash equals the `dist\package-r12\win-unpacked` archive hash. The archive gate passed: manifest, renderer bundles, byte-identical main build (`1815dcc992e94cbd`) and renderer index (`2b4d6d307f2c9af5`). `bunx tsc --noEmit -p tsconfig.json` passed. `bunx vitest run tests/unit --reporter=dot` passed 44 files and 295 tests. `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, and `git diff --check` passed. Unit output retained existing React `act(...)` and NaN style warnings without failures.

## Packaged UI evidence

- [The Figma audit](../figma-full-audit/README.md) covers 23 desktop FINAL screens, 28 mobile screens, Foundations, and Components. r45 repaired phone Tools, Scheduled tasks, Ramble list, the chat composer clearance, and Dark dropdown/toast treatment. [r45 measurements](../figma-full-audit/r45-ui-check.json) and [23-route sweep](../figma-full-audit/r45-route-sweep.json) cover its package.
- Three manual scheduled tasks were entered through the isolated package. The mobile list and detail cards and the desktop detail are captured in [phone](../figma-full-audit/key/r45-scheduled-393.png) and [desktop](../figma-full-audit/key/r45-scheduled-1440.png) views. A task with an actual execution history was unavailable.
- The `r43-populated` profile completed setup through **Start using Kel**. A local one-second synthetic 440Hz WAV was uploaded through the packaged UI. The engine saved a one-second transcript with text `A: Yeah`; this is [real local upload evidence](../figma-full-audit/r45-ramble-upload-check.json), not fresh Muse human audio. r45 exposed misplaced actions in its [saved detail](../figma-full-audit/key/r45-ramble-saved-detail.png).
- r46 follows mobile FINAL `222:1628`: selected title and saved state precede the transcript card; Copy, Download, Audio, and More sit below it. [Packaged detail](../figma-full-audit/key/r46-ramble-saved-detail.png) has no horizontal overflow at 393px. [The More menu](../figma-full-audit/key/r46-ramble-more.png) and [checks](../figma-full-audit/r46-ramble-actions.json) show working Rename/Upload/API Key access and correctly disabled unavailable Record More/Combine. Copy raised [a Dark toast](../figma-full-audit/key/r46-ramble-copy-toast.png) at x101/y691, above the tabs; its computed gradient was `#2C3B5C → #1A2846`.
- A [two-turn chat fixture](../figma-full-audit/key/r45-chat-fixture-393.png) tests rendering only. No remote model response was claimed. [r46's 23 phone routes](../figma-full-audit/r46-route-sweep.json) stayed at 393px with no route bounce or horizontal overflow; desktop Model/System remained at 1440px without overflow.

## Ownership and remaining work

The r46 packaged test root was PID 17324, engine PID 70868, and aioncore PID 37296 in the captured process snapshot. Executable paths pointed under `C:\Users\Nick\KelV2Candidate.r46`; the engine used only `r43-populated\engine`. The same snapshot showed protected stable engine PID 26544. The prior r20 PID 6356 and r45 test root were absent when rechecked; this work did not stop either. PIDs can change. Stable data, shortcuts, rollback copies, Astra's clean `ux/v2-shell` branch, and candidate names were untouched.

Exact UI parity is **not established**. [The audit](../figma-full-audit/README.md) lists remaining desktop controls and mobile states. Confirmed gaps include chat feedback actions and spacing versus `216:2`, plus transcript footer icons and saved duration text versus `222:1628`. Enabled WebUI/Pet states, actual task history, generated-image turns, real Muse speech, hover/error/disabled component states, and a physical iPhone need further checks. Faint Light-mode labels remained outside this Dark pass. Google sign-in, live services, and remote model response remain pending for account access. The web-host suite requires all Kel instances stopped and was not run. `request_review` was unavailable; no independent review occurred.

**Next action:** compare populated desktop Scheduled tasks, Transcriptions, Tools, and chat against their FINAL frames. Repair confirmed copy, icon, alignment, and component-state gaps in source. Package a new isolated candidate only after a source change. Keep the stable app and any live r20 session protected.
