# V2-19 r54 — desktop Dark chat candidate

**Source:** `integration/v2` commit `58a0533a3d66e183775c7d756c00d3cc91eadd88`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r54`, staged with the full unpacked runtime and `Run-Kel-V2-Candidate-r54.cmd`. Its launcher uses fresh isolated `C:\Users\Nick\KelV2Runs\prepared\r54\{host,store,engine}` roots. Packaged UI checks used the disposable `r43-populated` roots. r52 and r53 are preserved intermediates; neither was renamed or promoted.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `817B0DE3D6342942E33B76262EF0660F08FF4ED9858B9BCCF5B78EEDDEC225A6` |
| `Kel.exe` | `5CEA01F7705ADAE3C2744FA47439D6D1010AEB6AAFD01DA3EAD4EE60DD474F87` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r54.cmd` | `6449C0E03C1DB3DF0238B0575C54FBFAAC8495BEFC64CA840FD978053C96B3E2` |

The staged archive hash matches `dist\package-r12\win-unpacked\resources\app.asar`. Typecheck, `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, archive manifest, renderer-bundle gate, and `git diff --check` passed. The archive's main build SHA prefix was `1815dcc992e94cbd`; its renderer index matched the source build at `7593672ae85b9701`. The last full desktop unit suite was r47: 44 files and 296 tests. It was not rerun for this scoped renderer pass. Existing build warnings remained nonfailing.

[The desktop comparison](../figma-full-audit/DESKTOP_CHAT_R54.md) and [r54 package check](../figma-full-audit/r54-chat-check.json) record FINAL `185:1050`, matched fixture text, 1440/800/768px captures, action clicks, local reaction storage, Copy success, and no horizontal overflow. The 393px check confirms the existing phone Copy action and 24-hour time. The response fixture proves rendering only; it does not prove remote model behavior.

The r54 packaged test root was PID 71612 with CDP port 9394. Its direct children ran only under `C:\Users\Nick\KelV2Candidate.r54`; the engine used `r43-populated\store`. The test tree was stopped after matching the root command line and child executable paths. The final process check showed only protected stable engine PID 26544 in `C:\Users\Nick\KelDogfoodCandidate`. The earlier r20 process was absent; no r20 process was stopped. PIDs can change. Stable app data, shortcuts, rollback copies, and Astra's branch were untouched.

Exact product-wide Figma parity remains open. Matched real task history, long model replies, live service states, and some Settings and overlay controls remain to inspect. Faint Light-mode labels and phone layout work remain outside this Dark pass. Google sign-in, remote response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. `request_review` was unavailable; no independent review occurred.

**Next action:** compare desktop Dark WebUI and populated Settings overlays with FINAL and Components. Fix only measured gaps. Continue bounded V2-19 on the isolated candidate.
