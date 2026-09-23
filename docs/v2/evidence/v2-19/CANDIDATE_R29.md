# Kel V2 candidate r29 — saved conversation title and local opening time

**Source:** `integration/v2` @ `41b2bf6e738952ebad6a4181ba604874d6373019` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r29`, staged only. **Archive SHA-256:** `6ae8b552e6cf167647957cf566bf7318e1449ddeb8bf51f40e50453f0152032b`. No candidate was promoted or renamed.

## Reproduced gap and repair

In packaged r28, an empty Start using Kel action made a persisted local conversation. Its pane said **Untitled conversation**, but the Recent row had no visible text. The source rendered the raw blank name in the active grouped history and legacy history. Both rows now use the existing translated untitled label for blank names. [Before](../v2-16/r28-blank-recent-row.png) and [packaged r29 after](../v2-16/r29-named-recent-row.png) show the same persisted conversation after opening r29 on the isolated r28 store. No model request was made.

## Checks

| Check | Result |
| --- | --- |
| Desktop typecheck | PASS after source edit |
| Focused desktop tests | 2 files, 8 PASS after source edit |
| `bun run package`, electron-builder directory pack | PASS |
| `C:\tmp\verify_asar.py` | PASS: manifest, renderer bundles, main and index byte equality |
| r29 `app.asar` SHA-256 | `6ae8b552e6cf167647957cf566bf7318e1449ddeb8bf51f40e50453f0152032b` |
| r29 `Kel.exe` SHA-256 | `b42a19307508e52ea08f4a6a09aa5089441adc42e2a70949dfd58f5b9b10b594` |
| r29 `KelEngine.exe` SHA-256 | `d168f20a9a272a7a4e39707a67bbebef77829bc525fbaa96fd99ecec417d5f47` (unchanged frozen engine) |

## V2-16 local timing

The packaged r29 UI opened the persisted conversation from fully loaded Projects Knowledge. The check waited for a visible sendbox and title, then recorded five warm runs: **122.6, 112.4, 106.8, 114.2, 91.9 ms**; median **112.4 ms**. This measures local UI opening only. [Conditions and samples](../v2-16/r29-local-timings.json). The isolated aioncore command line used `C:\Users\Nick\KelV2Runs\prepared\r28-perf\store`; its engine used `...\r28-perf\engine`. This also checked that the local conversation survived the r28 to r29 candidate change.

A Knowledge to Map route change is a panel change, not a project context switch. No second workspace was selected, so project-switch timing remains pending. Remote load and first response timing remain pending without a signed-in session and model request. The setup Change control routes to Projects; the workspace selector opens a native directory dialog. No timing claim uses either as a completed project switch.

## Ownership and remaining checks

Before closing the test, the r29 root was PID 66496, its aioncore PID 640, direct engine PID 41172, and ACP engine PID 43484. All r29 test processes were stopped after executable-path checks. r20 Kel.exe PID 6356 and engine PID 10848 remained in `C:\Users\Nick\KelV2Candidate`; stable engine PID 26544 remained in `C:\Users\Nick\KelDogfoodCandidate`. Stable data, shortcuts, rollback copies, and Astra's `ux/v2-shell` branch were untouched.

No `request_review` tool was available. No independent review occurred. Continue bounded V2-19 on an isolated r29 root. Select two disposable project folders before measuring a real project switch. Test the second native colour-picker adjustment when the native control is available. Google sign-in, live services, fresh Muse audio, and physical iPhone checks remain pending without access or hardware. Keep faint Light-mode labels outside this Dark pass. The web-host suite still needs all Kel instances stopped, which the live r20 session prevents.
