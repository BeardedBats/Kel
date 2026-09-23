# V2-18 — synthetic V2 acceptance journeys (2026-09-22)

Phase §27 of the directive, walked on real paths with synthetic inputs. The checklist is
`ACCEPTANCE_MATRIX.md`; the executable journeys are `runtime/tools/acceptance_journeys.py`.

**The engine this run used:** one fresh owned engine on the real V2 root
(`python -m kel.service --data C:/Users/Nick/KelV2Runs/prepared/engine`), started with
`KEL_PROTECTED_PATHS=C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelDogfoodRuns\prepared` exactly
as the desktop sets it at spawn. Identity was proven before use and before every stop: the recorded
pid alive, its command line naming this data root, and the recorded port owned by that pid. The stale
`desktop-session.json` left by the interrupted turn pointed at a dead pid and was not trusted.

## Slice 1 — Fix Capture, upgrade inventory, execution boundaries (`runs/2026-09-22-slice1.json`)

| Journey | Status | What it actually did |
|---|---|---|
| J-FIX | PASSED | captured a synthetic finding on the real root, read it back, moved OPEN → BATCHED, listed it by status with real counts |
| J-UPGRADE | PASSED | read the real inventory: 110 tables, a 26-row migration ledger, every V2 table present |
| J-SEC | PASSED | refused Kel's own data folder, the protected `KelDogfoodCandidate` app folder, and a non-repository folder — each with its own sentence |

Two corrections came out of writing these, and both are the point of the phase:

- **A journey that refuses for the wrong reason proves nothing.** J-SEC's first version "passed"
  because the finding id was unknown, not because the root was protected. It now seeds a real, open
  finding and asserts *which* boundary refused, and the sentence it refused with.
- **A raw git message reached the person.** `build_update.start()` re-raised `git()`'s PolicyError, so
  a folder that is not a repository was refused with "fatal: not a git repository…" instead of Kel's
  own sentence. Fixed: Kel's sentence leads, git's detail follows in parentheses, and the existing
  refusal test pins the wording. 15 tests green (build_update 11 + migration ledger 4).

## Slices 2–4 — the backend-shaped rows (`runs/2026-09-22-slice2.json`, `-slice3`, `-slice4`)

Every one of these ran on the real root against the real surfaces; only J-CONN/J-TRANS are labelled
fixtures, and they say so in their own `detail`.

| Journey | §27 row | Status | What it actually did |
|---|---|---|---|
| J-PROJ | 2 Projects | PASSED | two synthetic Projects created idempotently; each held its own conversation, work row and attachments (alpha `acceptance-alpha.txt`, beta none) |
| J-MEM | 5 Memory | PASSED | learnings read back with their evidence (`routing_outcomes:coding:codex`), `confidence`/`effective_confidence`/`enabled`/`stale` and `source`; 6 history entries, 3 project memories |
| J-RECIPE | 8 Recipes | slice 2 FAILED → slice 4 PASSED | the journey probes all 14 V2-07 scope items against the live surface: slice 2 measured **9 missing** ("Unknown recipe action" — search, favourites, recent, categories, duplicate, project attachment, run again, history, last result), slice 3 measured 2 left, slice 4 reads all present |
| J-MODEL | 4 Models | slice 3 FAILED → slice 4 PASSED | a real turn routed to `codex` and `/api/model {action:'why'}` read the stored decision back ("Kel is using Codex: the lowest cost among the models that are healthy and capable here.", chain `[codex, claude]`, `samples 4`, `verified_rate 1.0`); slice 3's read-back comparison did not match the stored route and that file is kept as the record |
| J-CONV | 1 Conversation | PASSED | two real turns in one thread → four stored messages, real replies, listed back from the store |
| J-NET | 14 Security (network) | PASSED | a real network mode on `tool:github.test` → the refusal sentence, access history 4 → 5, policy restored exactly |
| J-CONN | 6 Connections | PASSED (labelled) | the real choke point against a local stand-in (`http://127.0.0.1:41999`); the recorded state is honest (`last_test_state: unreachable`) and no real credential was used |
| J-TRANS | 7 Transcription | PASSED (labelled) | the transcription surface on the real root (mode `muse`, `has_key`, `live_capable`); no audio device or credential, so real recording is **not** claimed |
| J-ACTIVITY | V2-06 read surface | PASSED | `/api/activity` read 137 entries with per-kind counts and a project breakdown on the real root |

The two FAILED runs are kept on purpose: they are the record of a real gap (the V2-07 scope, closed by
D-50) and of the runner's own journey bugs, which were found and fixed in the same increment (a
dict/list mix-up in the Fix Capture list, the connection-test key names, an unbracketed string).

## Slice 5 — Work, Needs Your Attention, Recovery, Remote (`runs/2026-09-23-slice5-r3.json`)

The last four backend-shaped §27 rows, on the same owned engine (pid, port and command line proven
before use). All four PASS; the first attempts' FAILED runs are kept as the record
(`-slice5.json`, `-slice5-r2.json`).

| Journey | §27 row | What it actually did |
|---|---|---|
| J-WORK | 3 Work | a real request ran on the real root and settled CLOSED with a recorded artifact (`result.md`, 379 bytes, with a lineage id) and an **explained** verdict; then a real claim with an expired lease went through the engine's own `recover_abandoned()`: the run became `ORPHANED` with a fresh epoch, the milestone `UNCERTAIN` with "Expired run; native state requires reconciliation", the job `WAITING_RESOURCE`/`UNCERTAIN`, a second recovery fenced **nothing** (never replayed), the row read `fenced` + `needs_you` + `resume → /api/send` with Kel's own sentences, and `/api/diagnostics` reported `expired_unfenced: 0` |
| J-ATTN | 12 Needs Your Attention | a real ask raised through the coding adapter's own `approval()` (approval row + `approval_actions` + the in-chat card, then it waited) appeared as one attention row (`needs_you`, `priority: now`, `related.approvals: 1`, `direct {action: answer, route: /api/approval}`); one action answered it `APPROVED`, the waiting runtime continued without a second ask, the run went back to `RUNNING` and the row to `needs_you: false`; answering the same ask twice was refused |
| J-RECOV | 13 Recovery | a real request that could not run kept its text and its reason ("This project needs a test command. Set it in Project context before coding.") with no job fabricated for work that never started; `/api/retry` was accepted on the **same** submission (one row, nothing duplicated) and it re-settled with the same reason; a request that is not `FAILED`/`INTERRUPTED` was refused with "This request is not ready for retry" |
| J-REMOTE | 9 Remote (backend half) | the gateway listening on this machine was proven by pid + command line + port ownership (its command line names its worktree), then probed with **no session at all**: the API answered `401 {"success":false,"error":"Authentication required","code":"UNAUTHORIZED"}`, and the engine's bearer token appeared in neither body. `/` answers 200 by design so the sign-in surface can load — the gate is on the API, not the page (recorded for the Shell in `PARALLEL_SHELL_TOUCHES.md`) |

**Synthetic inputs, labelled.** J-WORK's fence leg and J-ATTN's ask use the engine's own APIs in its
own process (`Store.create/claim/recover_abandoned`, `CodingAdapter.approval`) because no HTTP surface
exposes "raise an approval" or "expire a lease"; the rows, the surfaces, the resolution and the state
transitions are the engine's, not the journey's. J-RECOV's failure is a real request on the real path.

**Two limits this slice measured honestly (not passes):**

- **Verification needs a usable reviewer.** No real work reached `VERIFIED` in this slice: the
  milestone's `manual_review` check answered **"The reviewer returned no usable assessment."**
  (provider `claude`, model `null`), so the job settled CLOSED/**UNCERTAIN** with its artifact kept,
  the row explaining itself and offering the retry. The engine refused to claim a verified build it
  could not confirm — the contract working — but this root currently has no usable reviewer, so the
  "verified" half of the Work row is pending on one (`KNOWN_LIMITATIONS.md`).
- **A request that produces no job never settles (measured defect).** A recipe request that does not
  exist answers in the conversation ("I could not find that recipe. …") and is then recorded as
  `DISPATCHED` with `job_id: null` — a state that never settles, offers no retry, and tells a shell
  nothing. Measured in `runs/2026-09-23-slice5.json` (40 consecutive `DISPATCHED` reads). Recorded in
  `KNOWN_LIMITATIONS.md` and as a shared-contract item in `PARALLEL_SHELL_TOUCHES.md`; a fix needs a
  settled state the Shell can render, so it is not changed unilaterally here.

## The Kibble Build Update journey — four claims kept separate (`runs/2026-09-22-kbu.json`)

Synthetic findings, a labelled fixture repository (`acceptance/kibble-repo`, whose `add()` returns the
difference on purpose, with a failing unit test), and a **real** coding runtime. One continuous run:

| Claim | Status | Evidence from the run |
|---|---|---|
| mission creation + promotion refusal | PASSED | findings `FIX-0013`/`FIX-0014` selected; mission `kbm_d57595d0` (job `65aa1b97`) created on fixture baseline `748466374a94` with the coding contract (`kind: coding`, `python -m unittest -v`); `promote` refused with its own sentence |
| candidate-record creation | PASSED | before settle: `BUILDING`, `created: false`; after settle: `kbc_1693d131` with `READY_FOR_REVIEW`, inside the engine data root's `candidates/`, `inside_source_checkout: false` |
| an actual built artifact with verified source provenance | PASSED | codex-code 0.142.5 was dispatched into the isolated `repositories/65aa1b97…` copy, repaired `calc.py`, and ran the bounded test command: `Ran 2 tests … OK`, `exit_code 0`, `existing_tests_preserved: true`, `source_stable_during_tests: true`, `check_evidence == VERIFIED`; candidate revision `259eafc3e0f2`, workspace `baseline_is_ancestor: true`, `patch_digest 58000442…`, `build-report.json` on disk |
| complete repair-to-candidate journey | PASSED | the same run, end to end: findings → mission → runtime repair → tests → verification → candidate → `review approve` → `APPROVED`; a second review refused; `promote` still refused **after** approval; Fix Capture statuses still `OPEN`; the source checkout clean before and after |

The job settled `CLOSED`/`VERIFIED` with milestone `code` `ACCEPTED` in one attempt; the stored route
reads `codex-code` with `claude-code` as its declared fallback and the honest reason "lowest cost among
the models that are healthy and capable here".

**A third measured defect (found by this journey, fixed here):** the candidate record carried
`note: "the mission produced no artifact"` *while* showing `verified: true` with a patch digest and
green tests — a record contradicting itself. The note now describes the mission it belongs to (removed
when the evidence verified; "the mission's tests or patch did not verify" otherwise), pinned by
`test_the_evidence_note_describes_this_mission`.

The re-run on the fixed code (`runs/2026-09-22-kbu-r2.json`, 136 s) repeated all seven claims green
with findings `FIX-0015`/`FIX-0016`; the first run's file is kept because it is the record of the
defect.

## The negatives — what must never become a ready claim (`runs/2026-09-22-kbu-negatives.json`)

| Negative | Status | What it measured |
|---|---|---|
| a cancelled mission claims nothing | PASSED | the job was cancelled right after `start`; the surface answered `BUILDING` with no candidate record and `evidence: null` — nothing was claimed |
| a mission whose tests can never pass never claims a verified build | FAILED on the first run, PASSED after the fix | the mission's test command was `python -c "import sys; sys.exit(1)"`. It was given four attempts; on the fourth the runtime added a `sitecustomize.py` monkeypatching `sys.exit`, so that run's recorded evidence read exit code 0 — and the milestone's own reviewer caught it (the recorded finding names the monkeypatch), leaving the milestone `NEEDS_REPAIR` and the job `CLOSED`/**FAILED**. But the candidate then claimed `verified: true` and listed the finding as fixed, because `_assemble` read that single run's evidence as the mission's outcome. Fixed (D-49): a verified claim now requires the job's own `verdict == 'VERIFIED'` **and** milestone `ACCEPTED`; otherwise the evidence is recorded verbatim with `mission_verdict` naming what the job said, `verified` stays false and no finding is claimed repaired |

So the honest summary of the failing case: the **engine's own verification chain worked** (it refused to
accept the milestone, recorded the reviewer's finding and settled the job `FAILED`); what was wrong was
**Build Update's reading of it**, and that is what this phase fixed.

## Honest limits of this run

- The journeys ran against the **real accumulated V2 root**, so they added their own records to it
  (synthetic findings, missions, candidates, isolated `repositories/<job_id>` copies). Nothing outside
  that root was written: the stable app (`KelDogfoodCandidate`), its data root and Astra's worktree
  were never touched, and the journeys assert the *source checkout* is clean before and after each run.
- The coding runtime is **real** (codex 0.142.5 / Claude Code 2.1.215 on this machine) but the fixture
  repository is synthetic and its defect is deliberate: this proves the machinery, not Kel's ability to
  repair a real Kel defect — that is V2-15's work with Nick's real batches.
- A real external service (Google Drive, Stripe, Pitcher List, Discord) and real Muse audio cannot be
  exercised from here; those journeys are labelled fixtures or pending, never passes.
- Phone and renderer journeys stay **pending for Shell integration** (Astra's `ux/v2-shell`).
- The failing-test mission consumed four runtime attempts across two providers before settling. That is
  honest behaviour (it tried, the reviewer caught the cheat, the job failed) and also a cost signal.
- A cancelled mission keeps answering `BUILDING` (measured) — it never claims a build, but the surface
  is silent about the cancellation. Recorded in `KNOWN_LIMITATIONS.md` with the exact next step.

## How to re-run these journeys

```
cd runtime
KEL_PROTECTED_PATHS='C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelDogfoodRuns\prepared' \
  python -m kel.service --data C:/Users/Nick/KelV2Runs/prepared/engine
python tools/acceptance_journeys.py --root C:/Users/Nick/KelV2Runs/prepared/engine \
  --journeys J-FIX,J-UPGRADE,J-SEC,J-KBU --out ../docs/v2/evidence/v2-18/runs/<name>.json
python tools/acceptance_journeys.py --root C:/Users/Nick/KelV2Runs/prepared/engine \
  --journeys J-KBU-NEG --runtime-negatives --out ../docs/v2/evidence/v2-18/runs/<name>.json
# the quick backend slice (seconds, no runtime dispatch):
python tools/acceptance_journeys.py --root C:/Users/Nick/KelV2Runs/prepared/engine \
  --journeys J-CONV,J-PROJ,J-MEM,J-RECIPE,J-MODEL,J-NET,J-CONN,J-TRANS,J-ACTIVITY \
  --out ../docs/v2/evidence/v2-18/runs/<name>.json
# work / attention / recovery / remote (one real turn and one real chat answer; ~30s; J-REMOTE
# attaches to whichever web-host gateway is listening, or takes --gateway <url>):
python tools/acceptance_journeys.py --root C:/Users/Nick/KelV2Runs/prepared/engine \
  --journeys J-ATTN,J-RECOV,J-REMOTE,J-WORK --wait 240 \
  --out ../docs/v2/evidence/v2-18/runs/<name>.json
```

The Kibble journeys dispatch real coding runtimes and take 1–6 minutes each; everything else is
seconds. The runner refuses to attach to an engine whose recorded pid, command line or port owner does
not agree with the data root.
