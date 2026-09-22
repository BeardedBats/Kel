# V2 requirement status (implementation-first checkpoint)

Per requirement: **implemented / still missing / dependent on Nick**. Every deferred check lives on the
single audit list at the bottom and is deliberately **not run yet**.

## Implemented — early checkpoint (`2e60c64`)

| Requirement | What was implemented |
| --- | --- |
| Expired session routes to sign-in | `httpBridge` signals session-expired after the one silent refresh; `AuthProvider` flips to signed-out; the router's sign-in gate takes over **and remembers the destination** |
| Unknown conversation is honest | the conversation route keeps the visitor where they are with an Arco `Result` + the id, instead of a toast and a silent bounce home |
| Build Update surface | Kibble: pick findings → repository folder → mission → milestones with attempts → candidate evidence → Approve/Reject with a note. Fix Capture statuses untouched; installing not offered |
| Recipe runs reopened | `history` + `last_result` through the engine's own job records, with a link to the run on the Work page |
| Attention actions | `/api/work` rows carry the id their one action needs; the Work page renders answer / resume / stop / retry per row |

## Implemented — this checkpoint

| Requirement | What was implemented | Where |
| --- | --- | --- |
| **Phone conversation history** (V2-05 §10: list, open an earlier conversation, continue it) | the Shell's existing conversation list is the phone's history (its sider is the mobile drawer and every row opens `/conversation/<id>` through the same store). Fixes at the cause: the list **re-reads on `visibilitychange`/`focus`** so a conversation deleted elsewhere stops being offered; the **empty history gained its one action** (“New conversation”); a conversation that no longer exists keeps the route with the honest state. Path-style deep links already translate to their hash form (`deepLinkLocation`) | `pages/conversation/GroupedHistory/hooks/useConversationListSync.ts`, `pages/conversation/GroupedHistory/index.tsx`; decision **D-51** |
| **Recipe library controls** (V2-07: search, categories, favourites, recent, duplicate) | search box, category chips, favourites filter and star toggle, “Recently used” line, and a per-recipe Copy — all through the engine's own `/api/recipes` actions, scoped to the project | `components/kel/kelApi.ts`, `pages/kel/projects/index.tsx` |
| Phone attention offers (S14) | the Work surface renders the row's own action at phone width (added in `2e60c64`); the offers are the engine's routes, not new ones | `pages/kel/work/index.tsx` |

## Recorded as out of V2 scope (decision, not a gap)

- **Multi-utterance dictation** — **D-52**: §10 requires “voice-record prompt; Muse transcription; send
  transcript”, which is built and evidenced; accumulating several utterances inside one recording is a
  Muse endpointing behaviour, kept in `KNOWN_LIMITATIONS.md`, to be revisited with the V2.5 realtime
  work. Nothing in V2 acceptance depends on it.

## Corrected in the requirement list (stale notes)

- **S15 “phone Project routing”** — the checklist said `/api/project infer/ask` exists in the engine;
  it does not (no such action anywhere in `kel/`). Project routing is conversational: the conversation
  carries the project, and the engine's own `/api/project` creates or reads one. No engine gap remains
  here; the phone *copy* is Shell presentation, and the routing itself is exercised by J-PROJ.
- **S28 “Activity 2.0”** — was marked missing; `/api/activity` and the timeline exist (`kel/activity.py`,
  built with V2-08) and the Activity page renders real rows (verified at phone width).
- **S34 “deep-link failures”** — the two measured defects are fixed: destination retention through
  sign-in, and the honest state for a conversation that is not there.

## Still missing (real work, not a check)

- Phone drawer/history *presentation* refinements that belong to Astra's Shell lane (nothing in this
  line blocks them).
- Nothing else is outstanding in the requirement list that can be finished without Nick or a device.

## Dependent on Nick / hardware (audit list, **not run**)

1. Browser pass over the **packaged** build (`Kel.exe --webui`): deep link → sign-in → destination →
   refresh; Work links; Kibble Build Update end to end; recipe run → runs panel; a live attention action.
2. V2-19 regression groups (bounded batches) on this branch.
3. V2-16 timings on the packaged app (startup, conversation opening, project switching, remote loading).
4. Live-service checks (Google, real provider round trips) — needs credentials.
5. Muse recording — needs a microphone and audio.
6. Physical-iPhone pass — needs the device.
7. Packaging-defect watch: every future pack must pass `C:\tmp\verify_asar.py` before anything is copied.
