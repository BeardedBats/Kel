# Kel V2 candidate r28 — Projects and narrow regression

**Source:** `integration/v2` @ `6b81ffa0241bd7913716c74a6ca4d4bf8d3ebc42` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r28`, staged only. The launcher points at `C:\Users\Nick\KelV2Runs\prepared\r28\` and supplies `KEL_PROTECTED_PATHS` for the stable and live r20 app folders. No candidate was renamed or promoted.

## Reproduced gaps and repairs

| Finding | Source repair | Packaged result |
| --- | --- | --- |
| r26 Project map's empty-state **Refresh map** existed in the DOM but had `display:none` from the source-card rule. | Show action-bearing empty-state rows. | r27/r28 packaged button visible; [hidden before](r26-regression-ui/project-map-action-hidden.png), [visible after](r27-ui/map-empty-action.png). |
| A source card discarded its `actions` prop, so a built map had no visible refresh. | Pass actions through the shared source-card header and place them beside or below the title by width. | r28 built map exposes **Refresh map** at 1440 and 390px; [desktop](r28-ui/desktop-map.png). |
| r26 Connections at 390px narrowed service descriptions to a thin column. | Stack each service description above its controls below 560px. | r28 GitHub description 292px wide; its button starts below the description; document width 390px. [Before](r26-regression-ui/connections-narrow.png), [after](r28-ui/connections-narrow.png). |
| r27 Knowledge and Map tables squeezed topic names and digests at 390px. | Give each table a contained horizontal scroll area and a 560px table width. | r28 viewport and document both 390px; each table has a 292px viewport and 560px scroll width. A packaged click reached **Confirm** after horizontal scroll. [Before](r27-ui/map-narrow.png), [left](r28-ui/narrow-tables-left.png), [right](r28-ui/narrow-tables-right.png). |

The default project had no folder, so an r27 **Refresh map** click correctly returned `Project has no root to inspect`. For the success check, an **[INJECTED]** local fixture folder was assigned to the isolated default project. The packaged UI built map v1, then exposed its refresh action. No real project folder was changed.

## Checks

| Check | Result |
| --- | --- |
| Desktop typecheck | PASS after the last source edit |
| Focused desktop tests | 3 files, 37 PASS after the last source edit |
| `bun run package`, electron-builder directory pack | PASS |
| `C:\tmp\verify_asar.py` | ARCHIVE SOUND: manifest, renderer bundles, main and index byte equality |
| r28 `app.asar` SHA-256 | `f6d8620cdd33c42a7854fcac1dd7dc80f22b5004580128fa7793792743ad6148` |
| r28 `Kel.exe` SHA-256 | `bf7c6d7fc753e2ad7d618a756282418c4d58e42c71bccb71d285a6ff02b5074c` |
| r28 `KelEngine.exe` SHA-256 | `d168f20a9a272a7a4e39707a67bbebef77829bc525fbaa96fd99ecec417d5f47` (same verified frozen engine as r26) |

## Bounded V2-19 evidence

- r26 packaged **[UI]** Knowledge showed an **[INJECTED]** record. **Confirm** changed trust from 4/10 to 2/10 and marked it confirmed. `J-MEM` initially failed on an empty root because it expected an audit entry; it passed after the record was seeded. [Seeded UI](r26-regression-ui/knowledge-seeded.png), [journey](r26-memory-after-seed.json).
- r26 packaged **[UI]** Kibble prepared a fix prompt from an **[INJECTED]** finding and moved it from Open to Batched. It did not start Build Update. [UI](r26-regression-ui/kibble.png).
- r26 packaged **[UI]** Permissions opened Run check and showed the guardrail digest and scope checker. No lease existed to check. [UI](r26-regression-ui/permissions.png).
- r26 packaged **[UI]** Connections opened the Add a service form. No credential or live connection was added. `J-CONN` and `J-NET` remain PENDING for that reason. [Form](r26-regression-ui/connections-form.png), [journeys](r26-service-pending.json).
- r26 packaged **[UI]** Transcriptions showed an empty library. `J-TRANS` passed the engine status and library calls without audio; real Muse capture stays pending. [UI](r26-regression-ui/transcriptions.png).
- r26 engine `J-PROJ` and `J-FIX` passed. `J-SEC` was pending because that ad hoc launcher omitted `KEL_PROTECTED_PATHS`; r28's protected-path launcher passed `J-SEC`. r28 also passed `J-MEM` and `J-TRANS` on its isolated fixture. [r26 journeys](r26-remaining-journeys.json), [r28 journeys](r28-journeys.json).

The brief r27 route timings reached loading shells, so they do **not** satisfy V2-16 conversation-open or project-switch timing. The Workspaces button opened setup; no authenticated remote route was used. These timings remain pending.

**Review:** no `request_review` tool was available. No independent review occurred.

**Protected state after checks:** r20 Kel.exe PID 6356 and engine PID 10848 still run from `C:\Users\Nick\KelV2Candidate`; the stable engine PID 26544 still runs from `C:\Users\Nick\KelDogfoodCandidate`. The isolated r26/r27/r28 test processes were stopped after ownership checks. r28 used only `...\r28-ui\engine`, `store`, and `profile`. Stable data, shortcuts, rollback copies, and Astra's clean `ux/v2-shell` @ `0052075` were untouched.

**Remaining:** Complete V2-16 timings with loaded conversations, project switching, and an accessible remote path. Continue V2-19 on real service and audio paths when available. Test a second native colour-picker adjustment; the first saved adjustment alone is not full proof. Faint Light-mode labels remain outside this Dark pass. Google sign-in, live services, fresh Muse audio, and a physical iPhone remain pending without access or hardware. The web-host suite still needs a window with all Kel instances stopped, which r20 currently prevents.
