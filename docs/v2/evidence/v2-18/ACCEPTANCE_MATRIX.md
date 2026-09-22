# V2-18 — synthetic V2 acceptance matrix

Derived from `MARATHON_DIRECTIVE.md` §27 (V2.0 ACCEPTANCE) and the `ROADMAP.md` V2-18 line
(“Synthetic V2 acceptance journeys”, QUEUED). One row per §27 requirement. The matrix is the
checklist this phase walks; a requirement is **PASSED** only when a journey below it has actually
run on real paths and its evidence is written down — a unit test, a doc or an earlier increment's
green suite is *available evidence*, never a passed journey.

**Rules this phase runs under**

- Synthetic **inputs** (findings, fixture repositories, synthetic turns), real **paths**: the engine
  at `C:\Users\Nick\KelV2Runs\prepared\engine`, its own HTTP surface, its own SQLite store, the real
  coding runtimes installed on this machine (codex 0.142.5 / Claude Code 2.1.215), the real backup
  and migration machinery.
- Where an external service cannot be exercised (Google/Stripe/Pitcher List/Discord credentials,
  Muse audio hardware, a real iPhone), the journey says so **explicitly** and is recorded as a
  **labelled fixture** or **pending**, never as a pass.
- Shell-owned presentation (Astra's `ux/v2-shell` work) is out of scope here: renderer/phone
  journeys are recorded as **pending — Shell integration required** and are never marked passed from
  a backend journey.
- The Kibble Build Update journey keeps four claims **separate** (mission creation + promotion
  refusal · candidate-record creation · an actual built artifact with verified source provenance · a
  complete repair-to-candidate journey). A CLOSED job or a candidate row alone never proves a build.

## 1. Conversation — normal discussion, long-running discussion, continuation

- **Entry point:** `/api/send` (engine) → engine supervisor → a real runtime; `/api/conversation`
  for the thread; `/api/state` for the work view.
- **Expected result:** a turn is accepted, a real model answers, the thread persists, a second turn
  continues the same conversation without re-asking context.
- **Available evidence:** `docs/v2/evidence/v2-05/README.md` (Journey H — real model round trip and a
  second "still here" turn through the gateway); `runtime/tests/test_v13_continuation*.py`,
  `test_v13_composer.py`.
- **Missing journey/assertion:** no engine-level acceptance journey turns `/api/send` twice on the
  real root and asserts persistence + continuation from the store, independently of the phone.
- **Shell required:** no (the engine path is backend-reachable). **Status:** pending — see journey
  J-CONV.

## 2. Projects — multiple real contexts, no contamination

- **Entry point:** `/api/project` (create/switch/infer/ask), `/api/conversation`, project filter on
  `/api/work`.
- **Expected result:** two Projects hold separate work and memory; a turn in Project A never reads
  Project B's artifacts.
- **Available evidence:** `runtime/tests/test_v13_projectmap.py`, `test_v13_work_context.py`;
  the measured project counts in `docs/v2/evidence/v2-17/README.md` (2 real projects in the root).
- **Missing journey/assertion:** no journey creates two synthetic Projects on the real root and
  asserts isolation of work, memory and routing across them.
- **Shell required:** no for the backend assertion. **Status:** pending — see journey J-PROJ.

## 3. Work — real autonomous execution, recovery

- **Entry point:** `/api/send` (work requests), `/api/control` (pause/resume/cancel), `/api/work`,
  `/api/brief`, engine supervisor + `runs` table.
- **Expected result:** real work completes autonomously; a killed/abandoned run is fenced and
  recoverable without silently re-playing it.
- **Available evidence:** `docs/v2/evidence/v2-11/README.md` (long-running work 2.0 — fencing,
  recovers, the Work brief); `test_v2_longrun.py`, `test_coding_recovery.py`,
  `test_isolated_recovery.py`, `test_broker_recovery.py`.
- **Missing journey/assertion:** the acceptance-level journey that runs real work to CLOSED on the
  real root and then abandons a second run and shows the fence + the brief.
- **Shell required:** no. **Status:** pending — see journey J-WORK.

## 4. Models — routing, fallback, transparency

- **Entry point:** `/api/model` (`why`, routing read-back), `runs`/`routing_outcomes` tables,
  `/api/providers`.
- **Expected result:** a route is chosen from evidence, a failure falls back rather than dying, and
  “Why this model?” reads back the stored decision (not a recomputation).
- **Available evidence:** `docs/v2/evidence/v2-09/README.md` (decayed outcome evidence, floor,
  read-back); `test_v2_routing.py`.
- **Missing journey/assertion:** no acceptance journey drives a real turn, reads the stored route
  back through `/api/model {action:'why'}` and asserts the sentence matches the stored decision.
- **Shell required:** no. **Status:** pending — see journey J-MODEL.

## 5. Memory — useful recall, controlled learning

- **Entry point:** `/api/memory` (list/save/recall/forget/disable), `memories` / `memory_proposals`.
- **Expected result:** a saved fact is recalled in a later turn; learning is evidence-thresholded,
  explainable, switchable off, and never silently learns authority.
- **Available evidence:** `docs/v2/evidence/v2-10/README.md`; `test_v2_learning.py`,
  `test_v13_memory.py`.
- **Missing journey/assertion:** recall is not yet exercised as an acceptance journey on the real
  root (save → recall → forget, with the authority fence asserted).
- **Shell required:** no. **Status:** pending — see journey J-MEM.

## 6. Connections — real personal APIs

- **Entry point:** `/api/connections` (list/get/save/set_credential/test/run/actions/events/
  catalogue), `perform_request` as the single choke point; `/oauth/callback` for OAuth.
- **Expected result:** a real personal API call succeeds through the one choke point and lands in the
  access history.
- **Available evidence:** `docs/v2/evidence/v2-04a/README.md` (a live runtime call to
  `github-whoami`, access history with `source: runtime`), `docs/v2/evidence/v2-04b/README.md`
  (OAuth foundation + real-HTTP PKCE lifecycle); `test_v2_connections.py`, `test_v2_oauth.py`,
  `test_v2_connection_bridge.py`.
- **Missing journey/assertion:** end-to-end **real** service calls still depend on Nick's
  credentials; the acceptance journey can only exercise the machinery with a labelled local
  stand-in plus the real choke-point/history path.
- **Shell required:** no for the backend. **Status:** pending (labelled fixture) — see journey
  J-CONN.

## 7. Transcription — real Muse recording

- **Entry point:** `/api/transcription`; the desktop's Muse path; the phone's mic through the gateway.
- **Expected result:** recorded audio becomes a transcript that lands in the composer.
- **Available evidence:** `docs/v2/evidence/v2-05/README.md` (mobile voice: real browser → gateway →
  engine → Muse, transcript in the composer); `test_transcription.py`.
- **Missing journey/assertion:** the acceptance journey cannot produce real speech here; a synthetic
  audio/transcript input on the real transcription path is the honest maximum.
- **Shell required:** yes for the phone surface (Astra). **Status:** pending — labelled fixture +
  Shell-dependent.

## 8. Recipes — repeated workflows

- **Entry point:** `/api/recipes` (list/save/run/history/suggest).
- **Expected result:** a Recipe runs, is recorded, runs again, and shows its last result; a
  suggestion appears only after repeated behaviour.
- **Available evidence:** `test_v13_recipes.py`; `IMPLEMENTATION_STATUS.md` (V2-07 scope is queued,
  recipe machinery exists from V1.5).
- **Missing journey/assertion:** no acceptance journey creates a Recipe on the real root, runs it
  twice and asserts history + last result + failure visibility.
- **Shell required:** no. **Status:** pending — see journey J-RECIPE.

## 9. Remote — secure browser use

- **Entry point:** the web-host gateway (`bun run webui`, session-gated, bearer kept server-side) →
  engine `/kel/` routes.
- **Expected result:** a browser away from the desktop reaches the same renderer, authenticated, with
  no credential in the client.
- **Available evidence:** `docs/v2/evidence/v2-05/README.md` (real browser journeys over the
  gateway); `desktop/tests/unit/kel-remote-bridge.test.ts`.
- **Missing journey/assertion:** an acceptance journey that starts the gateway and asserts the
  session gate (unauthenticated request refused; no bearer in the client).
- **Shell required:** partly (renderer is Astra's). **Status:** pending.

## 10. iPhone — chat, voice, status, approvals, Project routing, resume/stop

- **Entry point:** the PWA over the gateway at a phone viewport; `/api/approvals`, `/api/control`,
  `/api/work`.
- **Expected result:** each phone journey works on real state.
- **Available evidence:** `docs/v2/evidence/v2-05/README.md` (voice, send, real round trip);
  `desktop/tests/e2e/kel-mobile.e2e.ts`.
- **Missing journey/assertion:** job-driven attention actions and history/drawer remain unbuilt
  (V2-05-history deferred for Shell integration); no backend journey can substitute for them.
- **Shell required:** **yes** (Astra owns the phone drawer/history presentation).
  **Status:** pending — Shell-dependent; must not be marked passed here.

## 11. Fix Capture — real friction capture

- **Entry point:** `/api/dogfood` (list/get/save/set_status/prepare_prompt) — four statuses only.
- **Expected result:** a finding is captured with its context and moves only through
  OPEN/BATCHED/FIXED/DISMISSED.
- **Available evidence:** `test_dogfood.py`, `test_v2_kibble_gate.py`; real findings already in the
  root (FIX-0001 from the D-46 live probe).
- **Missing journey/assertion:** no acceptance journey captures on the real root, walks a status,
  and asserts the four-status fence plus context retention.
- **Shell required:** no. **Status:** pending — see journey J-FIX.

## 12. Needs Your Attention — human interruptions

- **Entry point:** `/api/state` + `/api/work` attention rows, `/api/approvals`,
  `/api/approval` (answer).
- **Expected result:** a real interruption appears as an attention row and is resolvable in one
  action, leaving authoritative state consistent.
- **Available evidence:** `test_v2_staffing.py`, `test_failure_surfacing.py`,
  `test_v12_trust_summary.py`.
- **Missing journey/assertion:** no acceptance journey raises a real approval on the real root,
  sees it as an attention row, answers it and asserts the state transition.
- **Shell required:** no (the phone presentation of the same rows is Shell work). **Status:** pending
  — see journey J-ATTN.

## 13. Recovery — failures without lost work

- **Entry point:** `/api/retry`, `/api/control`, `store.recover_expired()`, `/api/backup`.
- **Expected result:** a failed run leaves saved work and a visible reason; recovery resumes or
  retries without duplicating effects.
- **Available evidence:** `docs/v2/evidence/v2-11/README.md`; `test_coding_recovery.py`,
  `test_review_recovery.py`, `test_broker_recovery.py`, `test_failure_surfacing.py`.
- **Missing journey/assertion:** no acceptance journey fails real work on the real root and shows the
  saved result + reason + a bounded retry.
- **Shell required:** no. **Status:** pending — see journey J-RECOV.

## 14. Security — authority narrowing, execution boundaries, network restrictions

- **Entry point:** `containment.assert_usable_root`, `kel/network_policy` behind `perform_request`,
  `authorize`, `/api/autonomy`, `/api/capabilities`, `/api/revoke`.
- **Expected result:** autonomous work is refused at sensitive roots, outbound calls obey the
  configured mode (ask before a new domain; fail closed), and authority narrows on request.
- **Available evidence:** `docs/v2/evidence/v2-13/README.md`, `docs/v2/evidence/v2-14/README.md`;
  `test_v2_isolation.py`, `test_v2_network.py`.
- **Missing journey/assertion:** no acceptance journey sets a network mode on the real root and
  observes a real refusal + a recorded decision, nor refuses a real protected path.
- **Shell required:** no. **Status:** pending — see journey J-SEC.

## 15. Upgrade — preserve durable user state

- **Entry point:** `/api/backup` (`inventory`, `create`, `inspect`), staged restore + marker,
  migration ledger.
- **Expected result:** an inventory before/after shows nothing lost; migrations are additive; the
  ledger is exact.
- **Available evidence:** `docs/v2/evidence/v2-17/README.md` (107 tables, ledger 24, a real
  backup→restore cycle on the root); `test_v2_upgrade.py`.
- **Missing journey/assertion:** the acceptance journey should read the real inventory and assert the
  ledger/table counts are intact *today*, after the Build Update increment added migration 29.
- **Shell required:** no. **Status:** pending — see journey J-UPGRADE.

## 16. Kibble Build Update — selected findings → mission → runtime → repair → tests → verification → candidate → human review

Kept as **four separate claims** (the D-46/D-47 contract):

| Claim | What must be shown | Evidence today |
|---|---|---|
| C1 mission creation + promotion refusal | `start` creates a mission on a verified, clean baseline; `promote` refuses | `docs/v2/evidence/kibble-build-update/README.md`; `test_v2_build_update.py` |
| C2 candidate-record creation | after the mission settles, a candidate record exists under the engine's `candidates/<id>/`, outside the source checkout | `test_v2_build_update.py` |
| C3 an actual built artifact with verified source provenance | a REAL coding runtime repairs the fixture, the bounded test command runs, `code_evidence` is VERIFIED and the candidate carries that revision | not yet shown end-to-end |
| C4 complete repair-to-candidate journey | C1+C2+C3 in one continuous run, ending in a human reviewable candidate and a human-only review state | not yet shown |

Negative assertions the journey must also make:

- failed/unverified tests, a missing artifact and unresolved findings must leave the candidate
  **without a verified build claim** (evidence recorded verbatim, `verified=false`);
- candidate creation and review cannot install or promote anything (`promote` refuses in every
  state; no install path exists);
- the **source checkout is untouched** by the mission (isolated `repositories/<job_id>` copy).

**Entry point:** `/api/dogfood {action:'build_update', op:start|status|candidate|review|promote}`.
**Shell required:** no for the backend contract (a Build Update *surface* is future Shell work).

## Journey runner

Journeys are executable: `runtime/tools/acceptance_journeys.py` drives the real engine over HTTP on
the real root and writes `docs/v2/evidence/v2-18/journeys-<timestamp>.json` (+ a readable summary).
Every journey reports `PASS`, `FAIL`, `PENDING` (Shell/credential dependent) or `FIXTURE`
(labelled stand-in where an external service cannot be exercised) — never a silent pass.
