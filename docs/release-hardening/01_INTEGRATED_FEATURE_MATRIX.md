# Integrated feature matrix

The four programs that make up the post-V1.5 product, one row per user-facing capability.
Evidence keys refer to `docs/release-hardening/evidence/` (JSON from the packaged harness).

| Program | Capability | Surface | Engine | Evidence | Rules |
|---|---|---|---|---|---|
| V1.5 core | First launch suite, onboarding, normal chat, projects | `/`, `/guid`, `/projects/*` | chat/AI runtime + `KelService` whitelist | `first-run`, `tour`, `maintext` | JR-1..6, JR-17 |
| Journey remediation b1+b2 | Sider/IA naming, plain language, settings registry, locale keys, contrast | sider, settings, `/guid` | renderer only | `sider`, `b2-settings`, `final-sider`, `final3-readability` | JR-20, JR-25, JR-30 |
| Design Vetting Sessions | Session lifecycle, batches, rapid answers, conflicts, spec, greybox, panel | chat + Work drawer (Vetting tab) | `kel/vetting.py`, `kel/vetting_session.py`, migration v11 | `vetting` (b2), live-databases | JR-31..34 |
| Transcription | Dedicated page, record, upload, folders, rename, copy/download, combine, composer mic, vetting review, Think Out Loud | `/transcription`, `/guid` composer, conversation composer | `kel/transcription.py`, migration v12, `MuseProvider`/fixture | `transcription` (review round 2), `voice-vetting`, `hardening` | JR-35..40 |
| Cross-cutting | One ingestion service for every answer source; one mic control; IPC envelope stripped; bridge whitelist | all Kel surfaces | `VettingAnswerIngestion`; `preload/main.ts` | contract tests + `voice-vetting` | JR-34, JR-38, JR-39 |

## Invariants that must hold across programs

1. **One understanding path.** Typed, pasted, dictated, and uploaded transcripts all reach
   `VettingAnswerIngestion`; no surface parses answers. (Contract test compares snapshot plus
   answer sources and decision events.)
2. **One door per capability.** Both composers mount `KelMicButton`; the donor speech control is
   unmounted; `combine` is reachable from the transcript view (JR-39/JR-40).
3. **Provider machinery stays behind one plain status** on every surface (JR-37).
4. **The renderer bridge whitelist matches every engine route a surface calls** (JR-34) — verified
   for `/api/vetting` and `/api/transcription`.
5. **User text is only ever the user's:** dictation finalizes once, cancel restores, nothing
   auto-sends (JR-38, JR-36).
