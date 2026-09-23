# Kel V2 candidate r26 — recipe and Work regression

**Source:** `integration/v2` @ `c0391b6b5a6db4ea38c88e82e661ee813a2f1522` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r26`, staged only. Its launcher uses `C:\Users\Nick\KelV2Runs\prepared\r26\` for engine and store. No candidate was promoted or renamed.

## Findings and repairs

| Packaged finding | Repair | Evidence |
| --- | --- | --- |
| r23 Run on Audit and Repair claimed a submission, although its dry run needed a project root and no job formed. Required inputs also had no UI. | Recipes now opens the declared input form. Start checks the dry run before submitting. The blocking sentence stays visible in the form. | r24 and r25 packaged clicks: Audit and Repair displays “Coding recipes need the project root and its test command” with no submission; Ship Release with `version=1.2.3` creates a job and history entry. `r25-ui/ship-inputs.png`, `r25-ui/needs-project.png`. |
| r23 Work's Answer request said it was sent but left an injected approval `PENDING`. Its frozen engine omitted the action ID. | Work resolves a missing ID from the pending state and fails visibly when no action exists. The engine was refreshed from current source for r25/r26. | r24 UI click changed its approval to `APPROVED`; r25's refreshed engine supplied the ID in the row. r25 UI click cleared the request, and read-only SQLite showed `APPROVED`. |
| r24's frozen engine offered Try again on a canceled job; Work called it Queued. | The refreshed engine removes that action. The UI guards stopped rows and names running, waiting, stopping, stopped, and finished states. READY milestones say “Waiting to start.” | [r24 failure](r24-ui/work-stopped.png); r25 packaged Work showed **Stopped** and “This work was stopped. Its saved request is kept.” No retry button appeared. [r25 Work](r25-ui/work-stopped.png); recipe Runs reopened the canceled job ([history](r25-ui/recipe-history.png)). |
| The new Dark recipe form's description touched the first input. | The field now uses a column layout with a 6px gap and a bounded input width. | [r24 gap](r24-ui/ship-inputs.png); r26 packaged geometry: desktop 1440px, document 1440px, gap 6px, input x=655–975 inside card x=634–1256. At 390px, document 390px, gap 6px, input x=63–321 inside card x=46–338. [desktop](r26-ui/desktop.png), [narrow](r26-ui/narrow.png). |

The attention job was an **[INJECTED]** isolated test job. The approval itself was completed through the packaged **[UI]** Work button. Ship Release was submitted through the packaged **[UI]** Recipes form, then canceled on the isolated root after its job and history appeared. No real service success is claimed from that run.

## Build and gates

| Check | Result |
| --- | --- |
| `bunx tsc --noEmit -p tsconfig.json` | PASS after the final source edit |
| `npx vitest run tests/unit/recipes-surface.test.ts` | 4 PASS |
| `npx vitest run tests/unit` | 43 files, 294 PASS |
| `python -m unittest -v tests.test_v13_work_context` | 13 PASS |
| `python -m unittest -v tests.test_v2_attention` | 7 PASS |
| `scripts/build-runtime.ps1` | PASS; current source frozen into `KelEngine.exe` |
| `packaging/verify_engine_pyz.py` on r26 | 67 Kel modules match source; no mismatch or missing module |
| `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir` | PASS; Windows directory pack signed |
| `C:\tmp\verify_asar.py` | ARCHIVE SOUND: manifest, renderer bundles, main and index byte equality |
| r26 `app.asar` | one, 300,592,094 B, SHA-256 `5749e1a92cc25837bb7be1bb87335146e42a9fcf4501ec5b6f59ff2b0cde3b5a`; same hash in build and candidate |
| r26 `Kel.exe` | one, SHA-256 `bcffa3f06859c808d11a7f035b31cece585f45c2214034cc7495de3fd99ebf6b` |
| r26 frozen engine | SHA-256 `d168f20a9a272a7a4e39707a67bbebef77829bc525fbaa96fd99ecec417d5f47`; same as r25, 67 modules verified |
| DLL set / stray executable | 58 DLL paths, identical to r25; zero `electron.exe` |

## Bounded V2-19 regression

The r25 packaged functional pass used fresh `...\r25-ui\engine` and `...\r25-ui\store`. r26 changed only recipe form spacing and used another fresh `...\r26-ui\` root. Its packaged form passed desktop and 390px measurements above. Both roots' test process trees were stopped after ownership checks.

The refreshed engine on a separate isolated r25 candidate root passed `J-RECIPE`, `J-ATTN`, `J-ACTIVITY`, `J-RECOV` in [`r25-journeys.json`](r25-journeys.json) and `J-WORK` in [`r25-work.json`](r25-work.json). `J-WORK` settled a real job as `CLOSED` and checked a deliberately stopped row. `J-RECOV` kept the request and guarded retry after `CANCELLED`. These are synthetic requests on a real packaged engine and store. They do not prove live personal services or abandoned-run recovery.

**Review:** no `request_review` tool was available. No independent review occurred.

**Protected state after checks:** r20 remains live at `C:\Users\Nick\KelV2Candidate` (root PID 6356, engine PID 10848, archive `baaab70ae30b6462`). The stable engine remains PID 26544 at `C:\Users\Nick\KelDogfoodCandidate` (archive `4f23c9aecb8288a6`). r23–r26 test processes are stopped. r22 and older candidates, stable data, shortcuts, rollback copies, and Astra's clean `ux/v2-shell` @ `0052075` were untouched.

**Remaining:** Continue V2-19 with bounded packaged Projects/Knowledge/Map, Kibble, Connections, Permissions, and transcription flows. Run V2-16 conversation-open, project-switch, and remote timings. The native color picker has one saved adjustment and an open popup in r23 evidence; a second native adjustment remains unverified. Faint Light-mode labels are outside this Dark pass. Google sign-in and live services need account access; fresh Muse audio needs a recording; physical iPhone checks need the device. The web-host suite was not run while r20 was live because its setup requires all Kel instances stopped.
