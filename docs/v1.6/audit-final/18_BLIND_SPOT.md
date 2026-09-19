# 18 — BLIND-SPOT PASS

Audit target `08f56673…`. Performed after the declared-scope passes, deliberately ignoring the Campaign A roadmap; fresh searches on the questions below.

| Question | Fresh search / result |
|---|---|
| Changed most, least scrutinized? | Desktop renderer + donor packages. Searched donor dirs → found the desktop-pet subsystem wired into production (`createPetWindow`, settings APIs, shipped `pet-states` assets) and the WebUI lifecycle bridge — recorded MINOR-008; aioncore runtime live — MINOR-007; donor builder config as parent — MINOR-009. |
| Architecture assumption everywhere? | "Conversation scoping is supplied by the caller." This single assumption is what MAJOR-001 exploits on `chat_approvals`; the memory/vetting/transcription services enforce it internally (batteries passed), approvals do not. |
| Journey crossing most security/state boundaries? | Approvals → effects → receipts (probe-1 §A/B/C). Findings: MAJOR-001, MINOR-002 (budget), none others. |
| Code path with many exception handlers? | Engine service route dispatch and bridges (`service.py`, webui bridge). Reviewed the webui file-dialog bridge (tokens auto-approved by design; start/stop/status/password as recorded); no new finding. |
| Weak FK/ownership relationships? | `approvals` (conversation nullable → MAJOR-001); memory rows are project-scoped but only via service discipline (batteries held); runs/jobs and proposals/conflicts checked in probes. |
| Packaged files never discussed in the corpus? | Desktop-pet pages/assets, `pet-states`, aioncore trees, WebUI page, donor builder yml — all surfaced and dispositioned in MINOR-007/008/009. |
| Background processes? | Engine child process (audited), native provider children (env audited — MINOR-003), aioncore tree shipped (legality/reachability — MINOR-007), desktop-pet window (MINOR-008). |
| Ports/listeners? | Engine transport audited in the IPC/transport reads (no remote listener opened by the engine surface audited); the WebUI bridge can start a local server when invoked — recorded under MINOR-008’s reachability; no new evidence of a listening socket in the audited boot path (installed probe observed no unexpected connections — 0 console errors; transport inspection was code-level). |
| Executable/script that can mutate user state? | Donor `package.json` scripts + builder config (MINOR-009); enginectl/upsert tooling reviewed as dev-side. |
| Env vars altering security behavior? | `HIDE_DONOR_AGENT_SURFACES` (donor surface hiding — ties to MINOR-008), `KEL_DATA_DIR` (isolation — used by the auditor successfully), provider key envs (MINOR-003). |
| Reachable but undocumented feature? | Desktop-pet start API and the WebUI lifecycle endpoints (MINOR-008); dormant `/api/approval` route (folded into MAJOR-001). |

**Outcome:** three donor-surface findings (MINOR-007/008/009) are the blind-spot pass's net-new yield; no additional BLOCK/MAJOR class emerged. No repairs made.
