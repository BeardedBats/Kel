# V2 requirement status (implementation-first checkpoint)

Written to answer, per requirement, **implemented / still missing / dependent on Nick** — and to keep
every deferred check on one list that is *not* run yet.

## Implemented in this checkpoint (source: `integration/v2`, the commit that carries this file)

| Requirement | What was implemented | How it is wired |
| --- | --- | --- |
| An expired session must route to sign-in, not home | `httpBridge` fires `onSessionExpired` when a protected call answers 401 even after the one silent refresh; `AuthProvider` turns that into “signed out”, so `ProtectedLayout` sends the visitor to `/login` **and remembers the destination** (`loginReturnTo`). Desktop runtime is deliberately excluded — its sessions are local | `common/adapter/httpBridge.ts`, `renderer/hooks/context/AuthContext.tsx`, `renderer/components/layout/Router.tsx` |
| An unknown conversation is handled honestly | the route keeps the visitor where they are and says so (Arco `Result` + the id + one action) instead of toasting and replacing the route with home | `renderer/pages/conversation/index.tsx` |
| Run a Recipe and reopen its result | Run already existed; the runs themselves are now readable — `history` + `last_result` through the engine's own job records — with a “Runs” panel and an “Open on Work” link | `renderer/components/kel/kelApi.ts` (`kelRecipeHistory`, `kelRecipeLastResult`), `renderer/pages/kel/projects/index.tsx` |
| Select Kibble findings and start Build Update | checkboxes already selected findings; the panel now starts a development mission from the selection plus the repository folder | `renderer/pages/kel/dogfood/index.tsx`, `kelApi.kelDogfood.buildUpdate.start` |
| Mission progress, failures, candidate evidence | the mission card shows mission/job state, every milestone with its state and attempt count (so a failure is visible), the candidate's review state, `verified`, revision, evidence path, fixed/unresolved findings and limitations | same panel, `buildUpdate.status` + `buildUpdate.candidate` |
| Review the candidate without changing Fix Capture status | Approve / Reject with an optional note, then the reviewed state is shown. `set_status` is never called by this path, the panel says so in words, and installing is deliberately not offered (the engine refuses `promote` by design) | same panel, `buildUpdate.review` |
| Attention actions (V2-06 rows) | `/api/work` rows now carry the id their one action needs (the pending approval, or the saved request a retry resubmits), and the Work page renders that action per row — **answer / resume / stop / retry** — dispatching to `/api/approval`, `/api/send`, `/api/control`, `/api/retry` | `runtime/kel/service.py` (`_work`), `kelApi` (`kelApproval`, `kelSend`, `kelRetry`, `kelWorkRows`), `renderer/pages/kel/work/index.tsx` |
| Project routing, work visibility, activity, Kibble surfaces | already wired and rendering real state; verified at phone width in the r14 checkpoint | `renderer/pages/kel/{projects,work,activity,dogfood}` |

Checks run for this checkpoint: renderer typecheck clean, production renderer build clean, engine
suites `test_v2_attention` + `test_v2_longrun` **18 tests OK** (they cover the row semantics and the
retry/recovery pins).

## Still missing (not deferred checks — real work)

- **Phone conversation history.** The requirement is kept and deliberately **not implemented on this
  line**: Astra owns the phone drawer/history presentation on `ux/v2-shell`, so building it here would
  collide. It stays V2-05-partial, owned by the Shell lane.
- **Multi-utterance dictation** (recorded in `KNOWN_LIMITATIONS.md`): one utterance per press today.

## Dependent on Nick (cannot be finished without him)

| Item | What it needs |
| --- | --- |
| Real Google sign-in | his own OAuth client id + one browser visit (V2-04b is otherwise built) |
| Muse transcription with real audio | a real recording from his microphone |
| V2-15 dogfood batches | his real Kibble feedback from using the build |
| Physical iPhone (V2-05 device pass) | the device itself |
| Promotion / installation of a candidate | his explicit decision; nothing here promotes or installs |

## The audit list (deferred on purpose — **not run**)

1. Browser pass over the **packaged** build (`Kel.exe --webui`): deep link → sign-in → destination →
   refresh; direct Work links; ordinary login; the Kibble Build Update panel end to end; recipe run →
   runs panel; attention action on a live row.
2. V2-19 regression groups, bounded batches, on the integration branch.
3. V2-16 performance numbers on the packaged app (startup, conversation opening, project switching,
   remote loading) — the WebUI numbers in `V2_05_DEEPLINK_RETENTION.md` are a starting point only.
4. Live-service checks (Google, real provider round trips) — needs credentials.
5. Muse recording — needs audio.
6. Physical-iPhone checks — needs the device.
7. Packaging-defect watch: every future pack must pass the minimum archive gate
   (`C:\tmp\verify_asar.py`) before anything is copied.
