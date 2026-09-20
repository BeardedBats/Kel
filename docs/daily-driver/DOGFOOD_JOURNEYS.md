# DOGFOOD_JOURNEYS — Kel Daily Driver (D18)

The directive's ten journeys, each mapped to the strongest evidence this marathon produced, with the
friction found and where it was fixed. Evidence lives in `docs/daily-driver/evidence/` and
`TEST_EVIDENCE.md`; scripts live in `packaging/`. "Live" means a real engine process (and, where the
journey needs it, the real shipped UI stack) was exercised — not a unit test. Journeys that need a
real model credential are marked PARTIAL with the precise reason; no result is claimed that was not
observed.

| # | Journey | Status | Evidence | Friction found → fixed |
|---|---------|--------|----------|------------------------|
| 1 | Normal conversation | PARTIAL (engine live; model needed for turn 1) | `/api/state`, `/api/work`, `/api/capabilities` all exercised live by the D9/D11/D12/D16/D17 journeys; a full assistant turn needs a provider key this machine does not have (see KNOWN_LIMITATIONS) | Remote pages failed with a raw code when the engine was down → D13 sentences |
| 2 | Coding task (brief → reviewed plan → lease → changes verified) | PARTIAL (engine live; model needed for the generation step) | D16 journey: hashed reviewed plan issued a real lease (`review_ref` required, pinned), scope checks live; verifier/child-flow pinned across the engine suites. Generation itself needs a provider | Lease scope sharp edge: plural `roots` silently filed a dead grant → D16 refused loudly |
| 3 | Long-running autonomous goal | PARTIAL (engine live; model needed for continuation content) | D6 live restart/resume all-true (kill mid-work → restart → resume without double-running; verdicts recorded); D7 orphan classification live; D15 emergency stop live | Orphaned work was invisible as "needs you" → D7 surfaced the engine's own reason |
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

## Records

- Journey verdicts and timings: `TEST_EVIDENCE.md` rows for D3–D17; raw verdict JSON in
  `docs/daily-driver/evidence/d{9,10,11,12,13,14,15,16,17}/`.
- Replay commands: `node packaging/verify-<name>.cjs` (learning-proposals, recipe-loop, remote-kel,
  route-transparency, emergency-stop, live-revision, integrations-overview).
- PARTIAL journeys stay listed as such in `KNOWN_LIMITATIONS.md`; the package phase (D19) re-runs the
  installed-candidate battery, which is where a real provider key, if present, completes journeys 1–3.
