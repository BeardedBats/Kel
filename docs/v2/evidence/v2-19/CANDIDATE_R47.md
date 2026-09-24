# V2-19 r47 — desktop Dark polish

**Source:** `integration/v2` commit `54ce43fa08295799cddb0101816369e22d872bd2`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r47`, staged and not promoted. Its full unpacked runtime and `Run-Kel-V2-Candidate-r47.cmd` are present. The launcher points to separate fresh `C:\Users\Nick\KelV2Runs\prepared\r47\{host,store,engine}` roots. Packaged checks used disposable `r43-populated` roots. r46 remains preserved.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `B216B4FB082DD3B6D0544437BF274A0013A2CDBF089B0E7E718ECCD9A52D1A50` |
| `Kel.exe` | `9CB6B2634DF9504A39EBBC5BF2B7FF7C1ABE7474A973E447E22F34504DE0B720` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r47.cmd` | `C8F44EA3DCC06AB0CCF02B66D897ADC3CEEABC9270CDC60B968CAD3C0C7EA58C` |

The staged archive hash equals the `dist\package-r12\win-unpacked` archive hash. Typecheck passed. The focused Ramble test passed 3/3, including newest saved selection. The full desktop unit suite passed 44 files and 296 tests. `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, and `git diff --check` passed. The archive gate passed manifest, renderer bundles, and byte-identical main build (`1815dcc992e94cbd`) and renderer index (`e68c13cf4762bdc3`). Existing React `act(...)` and NaN style warnings remained nonfailing.

## Packaged UI checks

- [The desktop polish record](../figma-full-audit/DESKTOP_POLISH_R47.md) states the Figma preservation locks, before/after evidence, and scoped QA. The pass used FINAL Tools `188:1956`, Transcriptions `189:4032`, and Components/Foundations. No phone layout was inspected or changed.
- [Tools measurements](../figma-full-audit/r47-desktop-check.json) show 40px MCP rows and a 158px MCP card at 1440px. At 800px, Add MCP stays inside its card and the Image Model control stacks without document overflow. The no-model sentence and link have 6px separation. [1440px](../figma-full-audit/key/r47-tools-1440.png) and [800px](../figma-full-audit/key/r47-tools-800.png) captures preserve the rendered result.
- [Tool interactions](../figma-full-audit/r47-tools-interactions.json) confirm the Add MCP menu, MCP expand/collapse, and the Go to configure link to Model. The [open menu](../figma-full-audit/key/r47-tools-add-menu.png) and [expanded list](../figma-full-audit/key/r47-tools-expanded.png) were captured. No live MCP service claim follows from these UI checks.
- [Embedded Transcriptions](../figma-full-audit/key/r47-transcriptions-1440.png) now selects the saved local item `Yeah` with text `A: Yeah`. r46 had shown a false empty document in the same disposable library. [Appearance](../figma-full-audit/key/r47-appearance-1440.png) stayed on its route with three theme cards and no horizontal overflow.

## Ownership and remaining work

The r47 packaged test root was PID 27824, engine PID 63716, and aioncore PID 43208. Each executable path pointed inside `C:\Users\Nick\KelV2Candidate.r47`, and its engine used only the disposable `r43-populated\engine` root. The test tree was stopped after matching its root command line and all candidate paths. The final process list showed only the protected stable engine PID 26544. The earlier r20 PID was absent during this pass; this work did not stop it. PIDs can change. Stable data, shortcuts, rollback copies, Astra's branch, and candidate names were untouched.

Exact product-wide Figma parity is **not established**. The [full audit](../figma-full-audit/README.md) lists other desktop screens and component states. The desktop Tools sample lacks Add MCP and live no-model text; those working controls remain. A long real transcript, other MCP states, scheduled execution history, and remote model response need matched checks. Faint Light-mode labels and all phone layout work stayed outside this pass. Google sign-in, live services, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. `request_review` was unavailable; no independent review occurred.

**Next action:** continue desktop Dark comparison on populated Scheduled tasks, chat, Providers, and Diagnostics. Repair measured token, text, alignment, and control gaps, then package only after a source change.
