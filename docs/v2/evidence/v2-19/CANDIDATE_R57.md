# V2-19 r57 — desktop Dark WebUI candidate

**Source:** `integration/v2` commit `cafe10e32abcf53f4d65ca00fb9814c4f44865c8` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r57`, staged with the complete unpacked runtime and `Run-Kel-V2-Candidate-r57.cmd`. The launcher uses fresh isolated `C:\Users\Nick\KelV2Runs\prepared\r57\{host,store,engine}` roots. Packaged UI checks used the disposable `r43-populated` roots. r55 and r56 remain preserved intermediates; no candidate was renamed or promoted.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `8BFB8503A4433668F13F60649C49CBC7F0B68F2E14BDE0856072D9BC30434CD6` |
| `Kel.exe` | `84C9BBCF830F2741865D05ECE4EE6B5E763233C526D465A7C15A39DD86985E17` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r57.cmd` | `7ED8DB0430093D8DAA5C291474C3E4356B69ABA457E9D0796AB977AB3989F224` |

The r57 `bunx tsc --noEmit`, `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, archive manifest and renderer-bundle gate, and `git diff --check` passed. The archive's main build SHA prefix was `1815dcc992e94cbd`; its renderer index matched the source build at `858898666ff1487e`. The last full desktop suite was r47: 44 files and 296 tests. It was not rerun for this scoped renderer pass. No WebUI component test exists; packaged page, dialog, focus, and close checks covered the changed path.

[The desktop comparison](../figma-full-audit/DESKTOP_WEBUI_R57.md) and [packaged measurements](../figma-full-audit/r57-webui-dialogs.json) record FINAL `188:2240` at 1440 and 800px, the three-segment step strip, exact first-step copy, Figma activity icon, and matching 1440px card bounds. Edit username and Change password opened and closed after their transitions. [The field check](../figma-full-audit/r57-webui-field.json) confirms one border on each password field and an outer focus border and glow. The 800px and 1440px document widths equal their viewports. The switches were left off: this did not test remote activation or later WebUI steps.

The r57 packaged test root was PID 27448 with CDP port 9398. Its direct children were all under `C:\Users\Nick\KelV2Candidate.r57`, including the engine and bundled aioncore. The test tree was stopped after matching the root command line and each direct child path. The final process check showed only protected stable engine PID 26544 under `C:\Users\Nick\KelDogfoodCandidate`. The earlier r20 process was absent; no r20 process was stopped. PIDs can change. Stable data, shortcuts, rollback copies, and Astra's branch were untouched.

Exact product-wide Figma parity remains open. Desktop WebUI enabled and later-step states, populated service data, and some Settings overlays remain to inspect. Faint Light-mode labels and phone layout remain outside this Dark pass. Google sign-in, remote response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. `request_review` was unavailable; no independent review occurred.

**Next action:** compare the next desktop Dark Settings overlay and field state with Components, then run bounded regression on an isolated candidate.
