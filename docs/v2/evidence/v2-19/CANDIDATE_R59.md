# V2-19 r59 — desktop Dark Model candidate

**Source:** `integration/v2` commit `96d2b5d55185d5ec0bc112132c82ba7edac4932e` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r59`, staged with the complete unpacked runtime and `Run-Kel-V2-Candidate-r59.cmd`. Its launcher uses fresh isolated `C:\Users\Nick\KelV2Runs\prepared\r59\{host,store,engine}` roots. Packaged UI checks used the disposable `r43-populated` roots. r58 is a preserved intermediate; no candidate was renamed or promoted.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `40CD6EB857BACC1DB3C6B6654DC0E772B8A10A28EBEAC88EA035A2A3D10725A8` |
| `Kel.exe` | `5AF8560BFC566D2C6704B51454FDFAE3B2EBBD4DEA741E8C9456D265C6E645A5` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r59.cmd` | `BF395313A8A3F6C04384FF9784B02DAF508F5339EDE87ECD043068C822F1B98F` |

The r59 `bunx tsc --noEmit`, `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, archive manifest and renderer-bundle gate, and `git diff --check` passed. The archive's main build SHA prefix was `1815dcc992e94cbd`; its renderer index matched the source build at `0355c458e43ca4f7`. The last full desktop suite was r47: 44 files and 296 tests. It was not rerun for this scoped renderer pass. No dedicated Model card or Add Model component test exists; packaged layout and interaction checks covered the changed paths.

[The desktop comparison](../figma-full-audit/DESKTOP_MODEL_R59.md) records the FINAL Model screen `188:1327`, Figma Model panel `188:1563`, Components Input `148:229`, and Modal surface from Lightbox `147:162`. r58 measured the two cards and model rows at 1440px, checked 800px without overflow, switched to Claude and back to Automatic, and opened and closed Add Model. r59 [packaged form checks](../figma-full-audit/r59-add-model-check.json) found 34px default fields, the Figma blue focus border and glow, red error border and glow, clear required messages, Escape closure, and an 800px modal within the viewport. No provider was added and no live model response was claimed.

The r58 page check used root PID 45024 with CDP port 9400. Its second modal baseline used root PID 65504 with port 9401. The r59 form check used root PID 61144 with port 9402. Before stopping each tree, the root path, debugging port, and direct child executable paths matched its own candidate. The final process check showed only protected stable engine PID 26544 under `C:\Users\Nick\KelDogfoodCandidate`. The earlier r20 process was absent; no r20 process was stopped. PIDs can change. Stable data, shortcuts, rollback copies, and Astra's branch were untouched.

Exact product-wide Figma parity remains open. Add Model stays visible on desktop to preserve the working entry point, although FINAL's sample empty Custom models card omits it. Populated custom model rows, provider dropdown states, and live service checks remain unverified. Faint Light-mode labels and phone layout remain outside this Dark pass. Google sign-in, remote response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. `request_review` was unavailable; no independent review occurred.

**Next action:** compare desktop Dark System and Appearance field states with FINAL and Components, then continue bounded regression on an isolated candidate.
