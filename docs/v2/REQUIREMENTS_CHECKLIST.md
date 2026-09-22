# KEL V2.0 — REMAINING REQUIREMENT CHECKLIST (working state)

The spine for the rest of the marathon. Every open requirement, its owner, the evidence that exists,
its dependency and the next action. States are the four the session directive names:

- **IV** — implemented and verified (a real run on real paths produced the evidence).
- **IU** — implemented but unverified (the code exists; no current run proves it).
- **MI** — missing implementation.
- **BD** — blocked by a specific external dependency (named).

An earlier unit suite never counts as verification of current integrated behaviour. A narrow backend
journey never closes a broader product phase. Re-established 2026-09-22 against `dev/v2` @ the HEAD
below; corrected whenever a run proves otherwise.

| # | Requirement | Owner | State | Evidence | Dependency / next action |
|---|---|---|---|---|---|
| S1 | §27 Conversation: discussion, long-running, continuation | backend | **IU** | `test_v13_continuation*`; V2-05 Journey H (phone round trip) | J-CONV journey: two real turns on the real root, continuation asserted from the store |
| S2 | §27 Projects: multiple real contexts, no contamination | backend | **IU** | `test_v13_projectmap`; 2 real projects in the root | J-PROJ journey: two synthetic Projects, isolation of work/memory/routing |
| S3 | §27 Work: real autonomous execution | backend | **IV** | J-KBU (C3/C4): real runtime repaired the fixture and the job settled VERIFIED | keep; extend with J-WORK (abandon + fence + brief) |
| S4 | §27 Work: recovery | backend | **IU** | `test_v2_longrun`; V2-11 evidence (broker-backed runs fenced) | J-WORK/J-RECOV journey on the real root |
| S5 | §27 Models: routing + transparency | backend | **IV** | J-KBU route read-back; `docs/v2/evidence/v2-09/README.md` | J-MODEL journey (this session) adds the `/api/model why` read-back assertion |
| S6 | §27 Models: fallback | backend | **IU** | measured in J-KBU-NEG: codex → claude-code after two failures, recorded in the run rows | assert in J-MODEL from the stored chain |
| S7 | §27 Memory: useful recall | backend | **IU** | `test_v2_learning`, `test_v13_memory`; V2-10 live loop | J-MEM journey: save → recall → forget with the authority fence |
| S8 | §27 Memory: controlled learning (off/on, explain) | backend | **IV** | `docs/v2/evidence/v2-10/README.md` (live loop proved) | keep; J-MEM re-checks after integration |
| S9 | §27 Connections: real personal APIs | backend | **BD / IU** | V2-04a live runtime call (`github-whoami`); J-CONN labelled fixture | real calls need Nick's credentials; the fixture exercises the choke point + history |
| S10 | §27 Transcription: real Muse recording | Shell + backend | **BD** | V2-05 mobile voice evidence (real Muse through the gateway) | needs a microphone + the Shell surface; J-TRANS labelled fixture for the engine path |
| S11 | §27 Recipes: repeated workflows | backend | **IU** | `recipes.py` library + `compile_recipe` + `entries/get/preview/save/versions/propose_from_job`; `test_v13_recipes` | J-RECIPE journey; V2-07 gaps below |
| S12 | §27 Remote: secure browser use | backend + Shell | **IU** | V2-05 browser journeys over the gateway | J-REMOTE: session gate refused unauthenticated; renderer is Astra's |
| S13 | §27 iPhone: chat, voice, status | Shell | **BD** | V2-05 evidence (voice + send) | needs the Shell baseline integrated; physical device for the last mile |
| S14 | §27 iPhone: approvals/denials/grants/review/resume/stop on real job state | Shell + backend | **MI** | attention rows exist (`/api/work`); the phone offers are not built | J-ATTN backend journey first; the phone surface is Astra's |
| S15 | §27 iPhone: Project routing | Shell + backend | **MI** | `/api/project infer/ask` exists in the engine | backend journey asserts routing; the phone copy is Astra's |
| S16 | §27 Fix Capture: real friction capture | backend | **IV** | J-FIX (capture → status → list on the real root) | keep |
| S17 | §27 Needs Your Attention: human interruptions | backend | **IU** | `_work()` attention rows + brief; `test_v12_trust_summary` | J-ATTN; V2-06 gaps below |
| S18 | §27 Recovery: failures without lost work | backend | **IU** | `test_failure_surfacing`, `test_coding_recovery`; J-KBU-NEG (failed mission claims nothing) | J-RECOV journey on the real root |
| S19 | §27 Security: authority narrowing | backend | **IU** | `test_v2_isolation`; `/api/autonomy`, `/api/revoke` | J-SEC extension: narrow → observe → restore |
| S20 | §27 Security: execution boundaries | backend | **IV** | J-SEC (own data root, protected app, non-repo refused in plain words) | keep |
| S21 | §27 Security: network restrictions | backend | **IU** | `docs/v2/evidence/v2-14/README.md` (live loop) | J-NET journey: mode set → real refusal + recorded decision |
| S22 | §27 Upgrade: preserve durable user state | backend | **IV** | J-UPGRADE (110 tables, 26-row ledger, all V2 tables) | keep |
| S23 | Kibble C1–C4 + negatives | backend | **IV** | `docs/v2/evidence/v2-18/README.md`; D-49 claim gate | keep; connect to the Kibble interface (V2-Kibble below) |
| S24 | Kibble: connect the backend contract to the intended Kibble interface | backend + Shell | **MI** | the UI contract is recorded in `PARALLEL_SHELL_TOUCHES.md`; no surface reads it yet | backend-side: the ops exist; surface is Shell work — record the dependency |
| S25 | Kibble: selection → progress → failure visibility → candidate evidence → human review | backend | **IU** | ops exist (`start/status/candidate/review/promote`); the journey exercised them by HTTP | the Shell surface is the integration; keep the contract |
| S26 | V2-06 Needs Your Attention 2.0 | backend | **IU** | `_work()` rows: `needs_you`, brief `needs_you`, pending approvals, jobs by state | gaps: Project grouping, priority, age, reason, related work, filtering, sorting, direct action, resolution |
| S27 | V2-07 Recipes 2.0 | backend | **IU** | library + versions + propose_from_job + preview | gaps: search, favourites, recent, categories, duplicate, attach-to-Project, run history, last result, success/failure |
| S28 | V2-08 Activity 2.0 | backend | **MI** | no engine activity surface exists (`grep activity kel/*.py` empty); the renderer has an `/activity` page from the donor line | engine timeline + filters + search + evidence links + retry/recovery history |
| S29 | V2-15 real dogfood integration pass | Nick + backend | **BD** | 3 real findings already in the V2 root (FIX-0001/0003/…) | real batches need Nick using a candidate; process what exists, do not fabricate |
| S30 | V2-16 performance + UX polish | backend + Shell | **IU** | no measurements yet this program | measure startup, conversation open, Project switch, first response, remote load |
| S31 | V2-19 full V2 regression | backend + desktop | **IU** | bounded groups only so far (last: 17 OK on build_update+migrations) | bounded regression across engine, desktop unit, browser, packaged app |
| S32 | V2-20 V2 release candidate | backend | **IU** | packaging scripts exist; no V2 candidate built yet | build at `C:\Users\Nick\KelV2Candidate` (inspect first, rollback ready) |
| S33 | Shell integration (Astra's baseline + backend) | integration | **MI** | Astra @ `681e005` (status-text commit) committed; her worktree has in-progress ramble-sidebar work | integration worktree + branch; integrate committed baseline only |
| S34 | Unauthenticated direct-route + conversation deep-link failures | integration | **MI** | measured in V2-05 (blank `/conversation/<id>` body; home-entry tap timeout) | fix at the cause in the integration worktree; verify in a browser |
| S35 | Dark-mode visual comparison + polish | Shell | **IU** | Astra's status-text evidence (`docs/v2/evidence/status-text/`) | compare against the approved references; do not edit her worktree |

## Owner split

- **backend** = this run (`dev/v2`).
- **Shell** = Astra (`ux/v2-shell`) — integrate her *committed* baseline; never edit her worktree or
  stop her processes.
- **Nick** = the person: credentials for real services, real dogfood batches, physical-phone checks,
  and the promotion decision.

## Blocked, precisely

- **S9** real personal APIs — needs Nick's service credentials (the choke point, history and actions
  are built and provable with a labelled local stand-in).
- **S10/S13** Muse + phone — needs real audio hardware and the Shell baseline; engine-side journeys
  use labelled fixtures.
- **S29** real dogfood batches — needs Nick running a candidate daily; the three findings already in
  the root are processed.
- **S24/S33/S34/S35** the Kibble surface, the integrated Shell and the deep-link repair — depend on
  Astra's committed baseline (available) and, for her unfinished work, on her completing it.
