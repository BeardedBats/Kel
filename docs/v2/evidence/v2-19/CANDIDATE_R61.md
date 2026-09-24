# V2-19 r61 — desktop Dark System candidate

**Source:** pushed `integration/v2` commit `62f957c1b49500b4f3ce59c3dfb491e973246b1a`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r61`, complete unpacked runtime with `Run-Kel-V2-Candidate-r61.cmd`. The launcher uses isolated `C:\Users\Nick\KelV2Runs\prepared\r61\{host,store,engine}` roots. Packaged UI checks used disposable `r43-populated` roots. r60 is a preserved intermediate; neither candidate was promoted.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `166F9A7E74D2639B52DE8C629A49F090D9BA5ECD68634732A544D330700C3F84` |
| `Kel.exe` | `5E7F8FC3C1D7B594B2BFD8C3EE56A943D1107BA2C7B9397828850E79AEC0AA78` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r61.cmd` | `2E65E81E00D31247AD86F171E33589CCFDACDDBA95C8AFD40226F34243F58E18` |

Typecheck, package build, Windows unpacked builder, archive gate, and diff check passed. The archive's main build SHA prefix was `1815dcc992e94cbd`; renderer index `d6e53ffc9a360d72`. [The desktop comparison](../figma-full-audit/DESKTOP_SYSTEM_R61.md) records FINAL panel geometry, text and control colors, 1440/800px screenshots, and backup/restore dialog closure. No backup or restore was submitted. The last full desktop suite was r47: 44 files, 296 tests; it was not repeated for these renderer changes.

The r59/r60/r61 test roots (PIDs 8684/55940/49176) were stopped only after verifying executable path, debugging port, and child paths. The protected stable engine PID 26544 remained running; the earlier r20 process was absent. Recheck ownership before any later stop. Stable data, shortcuts, rollback copies, and Astra's branch were untouched.

Exact product-wide Figma parity remains open. Google sign-in, live services, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Faint Light-mode labels and phone layout remain outside this Dark pass. `request_review` was unavailable; no independent review occurred.
