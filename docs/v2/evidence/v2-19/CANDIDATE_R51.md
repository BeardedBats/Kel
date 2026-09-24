# V2-19 r51 — desktop Dark candidate

**Source:** `integration/v2` commit `56df3742ca6d9734f1771230d0dbee05e2874300`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r51`, staged with the full unpacked runtime and `Run-Kel-V2-Candidate-r51.cmd`. The launcher points to fresh isolated `C:\Users\Nick\KelV2Runs\prepared\r51\{host,store,engine}` roots. Packaged UI checks used disposable `r43-populated` roots. r47–r50 remain preserved intermediates. No candidate was renamed or promoted.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `F564D5B2C876612B61823E7D0AEEB9A151E9517CB7C98D731FBD02209F2E0BEB` |
| `Kel.exe` | `E7097CAE86403BFC7C7D73993686B8FD9A2CAC91533A933F22B097F8ACED019B` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r51.cmd` | `B00BC12FE6986F1379C076648A5FC7EE975C2E836098EA8D1850E029FA4D4102` |

The staged archive hash matches `dist\package-r12\win-unpacked\resources\app.asar`. Typecheck, `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, archive manifest, renderer-bundle gate, and `git diff --check` passed. The archive's main build SHA prefix was `1815dcc992e94cbd`; its renderer index matched the source build at `b417482e2d3d3ccc`. The last full desktop unit suite was r47: 44 files and 296 tests. It was not rerun for this scoped CSS and modal-class pass. Existing build chunk and dynamic-import warnings remained nonfailing.

## Packaged UI checks

- [The desktop polish record](../figma-full-audit/DESKTOP_POLISH_R51.md) states Figma authority, preservation locks, before/after captures, and remaining gaps. This pass changed only desktop styling and a modal class; it did not inspect or change phone layouts.
- [r50 measurements](../figma-full-audit/r50-desktop-check.json) cover Scheduled tasks, Diagnostics, Providers, and Tools at 1440, 800, and 768px. Every checked document width equals its viewport. The narrow outer rail is 180px; the Scheduled rows have 1px dividers; Diagnostics maintenance rows are 64px. [The r50 follow-up](../figma-full-audit/r50-desktop-followup.json) confirms a selected saved task, its five detail rows, the Assistant menu, and a local Providers preflight.
- [r51 packaged measurements](../figma-full-audit/r51-desktop-check.json) show the Assistant menu's opaque Components gradient at 1440, 800, and 768px. The menu contains Kel; Cancel closes the dialog at all three widths. The [1440px](../figma-full-audit/key/r51-new-task-assistant-1440.png) and [800px](../figma-full-audit/key/r51-new-task-assistant-800.png) screenshots show that the Execution Mode label no longer bleeds through the menu.
- [r50 New task at 1440px](../figma-full-audit/key/r50-new-task-1440.png) and [800px](../figma-full-audit/key/r50-new-task-800.png) show the blue glass input, select, textarea, and buttons. [The focus capture](../figma-full-audit/key/r50-new-task-focus-1440.png) shows the accent ring. r50 and r51 use the same modal source except for the opaque select popup.

## Ownership and limits

The r51 packaged test root was PID 65600 with CDP port 9390; its engine was PID 34172. Their executable paths pointed inside `C:\Users\Nick\KelV2Candidate.r51`; the engine used only `r43-populated\engine`. The test tree was stopped after matching its root command line and child paths. The final process check showed only the protected stable engine PID 26544 in `C:\Users\Nick\KelDogfoodCandidate`. The earlier r20 PID was absent during this pass; no r20 process was stopped. PIDs can change. Stable app data, shortcuts, rollback copies, and Astra's branch were untouched.

Exact product-wide Figma parity remains open. The Scheduled detail still shows read-only values where FINAL illustrates controls; the working New task dialog carries those controls. Real task history, long transcript typography, remote model response, and live service states need matched checks. Faint Light-mode labels and phone layout work remain outside this pass. Google sign-in, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. `request_review` was unavailable; no independent review occurred.

**Next action:** continue a bounded desktop Dark pass on chat, Settings controls, and populated overlay states. Fix a gap only after a matched Figma and packaged capture; run focused checks and stage a new candidate only for a source change.
