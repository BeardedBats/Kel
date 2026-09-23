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

A Knowledge to Map route change is a panel change, not a project context switch. At the first r29 checkpoint, no second workspace was selected. The final isolated round below measured a real local switch. Remote load and first response timing remain pending without a signed-in session and model request. The setup Change control routes to Projects; the workspace selector opens a native directory dialog. No timing claim uses either as a completed project switch.

## Final isolated rounds on the same r29 package

The next packaged run used `KEL_HOST_DATA_DIR`, `AIONUI_DATA_DIR`, and `KEL_DATA_DIR` under `C:\Users\Nick\KelV2Runs\prepared\r29-rounds\`. The aioncore, engine, and Chromium process command lines confirmed those roots. Two disposable folders, `project-a` and `project-b`, were **[INJECTED]** into that isolated host profile's recent-workspaces list. The packaged UI selected each folder and created a real, empty conversation without a model request. Five switches alternated the persisted conversations. Each wait required the target conversation URL, the matching folder visible in Files, and a visible sendbox. Samples: **123.0, 127.5, 107.8, 114.1, 114.9 ms**; median **114.9 ms**. [Conditions and samples](../v2-16/r29-project-switch.json); [loaded project-b](../v2-16/r29-project-b.png). This closes the local project-context timing gap. It does not measure remote load or first response.

The packaged Dark Appearance page was checked again at 1440, 800, and 390px: [desktop](r29-dark-1440.png), [800px](r29-dark-800.png), [390px](r29-dark-390.png). The three theme cards form one row at desktop and stack at narrower widths. At each width the document matched the viewport width, with no horizontal overflow. [Width readings](r29-dark-widths.json). No new token, control, or layout gap was confirmed.

The native Chromium colour popup accepted **two adjustments while it stayed open**: `#0b1732` → `#0c1a36` → `#0c1c36`. The field and popup showed the second value; reload kept `#0c1c36`, and Reset restored the default `#0b1734`. [First of the two adjustments](r29-picker-second-change.png); [second adjustment in the same popup](r29-picker-continuous-second.png). This closes the earlier second-adjustment gap for this packaged Windows run.

After the latest source change, the full desktop unit suite passed: **43 files, 294 tests** (`npx vitest run tests/unit --reporter=dot`). It printed React `act` and `NaN` style warnings but no failures. The source was unchanged during these final rounds, so r29 was not rebuilt.

The staged r29 [launcher](Run-Kel-V2-Candidate-r29.cmd) now sets `KEL_HOST_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r29\host` alongside its existing engine, store, and protected-path settings. Its SHA-256 is `09af1bb5ac96d11af8c8558a1d177532ec04162fc198853b16c1e5f170376476`. A launcher smoke produced root PID 20436; Chromium used `...\r29\host`, aioncore used `...\r29\store`, and the engine used `...\r29\engine`. That test tree was stopped after owner checks. The archive and executable were unchanged. This launcher edit only isolates the staged candidate's host profile; it did not touch r20 or stable.

## Ownership and remaining checks

Before closing the test, the r29 root was PID 66496, its aioncore PID 640, direct engine PID 41172, and ACP engine PID 43484. All r29 test processes were stopped after executable-path checks. r20 Kel.exe PID 6356 and engine PID 10848 remained in `C:\Users\Nick\KelV2Candidate`; stable engine PID 26544 remained in `C:\Users\Nick\KelDogfoodCandidate`. Stable data, shortcuts, rollback copies, and Astra's `ux/v2-shell` branch were untouched.

No `request_review` tool was available. No independent review occurred. The final r29 test tree (root PID 52708, aioncore 43056, direct engine 708, ACP engines 47528 and 37836) was stopped after executable-path and parent checks. The r20 and stable processes remained running. Google sign-in, live services, remote load, first response, fresh Muse audio, and physical iPhone checks remain pending without account access, a model request, fresh audio, or hardware. Keep faint Light-mode labels outside this Dark pass. The web-host suite still needs all Kel instances stopped, which the live r20 session prevents. V2-20 release-candidate promotion remains gated; r29 stays staged.
