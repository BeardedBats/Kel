# DOGFOOD_JOURNEYS — Kel Daily Driver (D18)

The directive's ten journeys, each mapped to the strongest evidence this marathon produced, with the
friction found and where it was fixed. Evidence lives in `docs/daily-driver/evidence/` and
`TEST_EVIDENCE.md`; scripts live in `packaging/`. "Live" means a real engine process (and, where the
journey needs it, the real shipped UI stack) was exercised — not a unit test. Journeys that need a
real model credential are marked PARTIAL with the precise reason; no result is claimed that was not
observed.

| # | Journey | Status | Evidence | Friction found → fixed |
|---|---------|--------|----------|------------------------|
| 1 | Normal conversation | LIVE with a synthetic provider turn (real engine paths; a real model still needs a key) | `packaging/verify_synthetic_journeys.py` J1: a side question answered through the provider path, both turns durable (`evidence/d18/synthetic-journeys.json`); `/api/state`, `/api/work`, `/api/capabilities` exercised live by the D9/D11/D12/D16/D17 journeys | Remote pages failed with a raw code when the engine was down → D13 sentences |
| 2 | Coding task (brief → reviewed plan → lease → changes verified) | LIVE with a synthetic provider turn (engine live; the generation turn is a fixture) | Synthetic journey J2: submit → execute → independent verify → CLOSED/VERIFIED with a publication and an artifact written on disk, all through the real engine paths; D16 journey: hashed reviewed plan issued a real lease (`review_ref` required, pinned), scope checks live | Lease scope sharp edge: plural `roots` silently filed a dead grant → D16 refused loudly |
| 3 | Long-running autonomous goal | LIVE with a synthetic provider turn (the killed run is real) | Synthetic journey J3: a real child process killed mid-run → restart recovery fences the run (ORPHANED, milestone UNCERTAIN, verdict UNCERTAIN, attempts stay 1, no silent replay) → the person's "continue" re-arms it → the same job finishes VERIFIED with a fresh run id (attempts 2); J4 pause/resume holds a run and completes after resume; J5 a failing provider lands terminal + needs-you with the retry ladder bounded at 4. D6 live restart/resume, D7 orphan classification, D15 emergency stop all live | Orphaned work was invisible as "needs you" → D7 surfaced the engine's own reason. Then the promised escape hatch did nothing: "continue" attached a link but left the fenced job waiting forever, and Work claimed that state would "continue automatically" → D19 fixed the engine path and the sentence (see the ledger) |
| 4 | Transcription | LIVE | D4 live fixture flow (practice mode) end-to-end + searchable recents; bounded-failure behaviour pinned | — (recents search came out of this journey) |
| 5 | Remote interaction (desktop → browser) | LIVE | D11 real-stack journey: real engine + real `bun run webui` (shipped aioncore) + login; anonymous refused; desktop-seeded job visible remotely; token never leaves the server; dead engine fails closed | D8 posture: normal UI must not show roster internals; D13: remote failures needed sentences; bodyless reads must be GETs (fixed + pinned) |
| 6 | Provider outage / fallback | LIVE (selection + reasons; provider call itself needs a key) | D12 route journey (chosen route, fallback list, excluded reasons, honest unknowns) + router eligibility/skip pins across the engine suites; D1 truthful provider states (needs-setup/available) | The chosen route was invisible to the person → D12 says it in one plain sentence |
| 7 | Update / upgrade | PINNED (installer phase still ahead) | D2: donor CDN feed severed, fail-closed Kel GitHub check, user-visible update state; packaged re-verify is deferred to the package phase (recorded in PACKAGE_EVIDENCE) | Donor update feed could have silently served another product's build → D2 fail-closed |
| 8 | Recipe create → save → run → re-run | LIVE | D10 journey: draft from a real job (nothing stored), save without confirmation refused, confirm persists, re-save idempotent, run + run-again accepted, first run is a real job | The whole loop was unreachable (dead primitives) and `propose_from_job` crashed on the engine's own short milestone ids → D10 fixed both |
| 9 | Learning promotion / correction | LIVE | D9 journey: two pending proposals; nothing applied before a decision; defer keeps it queued; accept applies through the trust model with superseded history; reject never applies | The proposal queue had no human surface → D9 "Kel suggests"; record `value` contract was mistyped → fixed |
| 10 | Desktop → remote → desktop continuity | LIVE | D11 (as #5) plus D12 `/api/state` `routes` on the remote read; no device-local divergence found: both surfaces read the same engine state | Emergency stop was one click and could end a remote session's work by accident → D15 arm/confirm |

## Friction ledger (what the journeys changed in the product)

Fix work this phase produced, each already committed with its own tests:

1. Raw engine job ids in the Permissions table → plain work labels (`9bdf338`, D0).
2. Donor product phrases in installer metadata and a donor wiki link in agent settings → removed (`777fefe`, `cce55d0`).
3. A duplicated pet-refusal toast → stable message id (`f594282`).
4. Provider setup spoke engine jargon → Set up / Save / Verify in user words (`0279a1d`, D1).
5. A donation CDN could have delivered updates for the wrong product → fail-closed Kel-only check (`7c9df63`, D2).
6. Remote pages failed with raw codes and bodyless reads were POSTed → sentences + bridge-parity GET (`879804e`, D13; D12).
7. The emergency stop fired on a single click → two-step confirm with the effect spelled out (`8b67cdf`, D15).
8. An unknown boundary scope silently filed a dead grant → refused loudly (`8216e48`, D16).
9. The chosen provider/model was invisible → one honest sentence on Work (`879804e`, D12).
10. Roster management was exposed to normal users → Kel manages its own roster; developer-only disclosure (`82ff501`, D8).
11. Two shipped links still pointed at the donor org's GitHub (Office-preview install, agent-hub PR) → removed in the D19 residual fix, pinned by `donor-org-references.test.ts`; the built bundle now has zero donor-org hits (D19 commit).
12. An interrupted run could not actually be continued: the person's "continue" attached a conversation link and left the fenced job waiting forever, while the Work page promised that state would "continue automatically" → `Continuation.execute_resume` now re-arms the fenced milestone at the person's own request (`Store.reopen`), the Work page names the person's next step instead of an automatic continuation it would never get, both pinned (`interrupted-run-promise.test.ts`, `test_v13_continuation.py`) and proven by journey J3 (`3e6b544`, D19).
13. Engine provider ids reached user copy on the installed build: the route sentence said "Running on internal", the provider confirmation read "Saved and verified internal", and the readiness choices were labelled with ids → all three name the provider from the engine's own inventory labels now (`internal` is the legacy id of the Anthropic API entry; renaming the id is recorded as debt, not attempted at the package gate). Pinned by `provider-language.test.ts` (D19).

## Records

- Journey verdicts and timings: `TEST_EVIDENCE.md` rows for D3–D19; raw verdict JSON in
  `docs/daily-driver/evidence/d{9,10,11,12,13,14,15,16,17}/`, plus `evidence/d18/synthetic-journeys.json`
  for journeys 1–3 and `evidence/d19/installed-battery.json` for the installed replays.
- Replay commands: `node packaging/verify-<name>.cjs` (learning-proposals, recipe-loop, remote-kel,
  route-transparency, emergency-stop, live-revision, integrations-overview),
  `node packaging/verify-installed-battery.cjs` (installed candidate),
  `cd runtime && python ../packaging/verify_synthetic_journeys.py` (journeys 1–3).
- Journeys 1–3 carry synthetic-provider evidence (real engine execution paths, fixture text instead of
  a real model turn); a real-provider turn stays listed in `KNOWN_LIMITATIONS.md`, and the installed
  candidate battery (`evidence/d19/`) is the replay that would complete it if a key were present.
