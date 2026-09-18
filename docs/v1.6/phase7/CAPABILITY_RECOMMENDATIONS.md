# Phase 7 — Smart capability recommendations

date: 2026-09-18
increment: PHASE7-CAPABILITY-RECOMMENDATIONS
scope (sprint directive §32): only recommend real capabilities · no no-op UX · preserve capability
safety · verify production effect · record every new recommendation path.
sources: sprint directive §32; docket in `docs/session-tools/` (01 non-goal note; 08 limitation #2
— "no message-level card; next increment per the docket"); `docs/basic-ux-sweep/17_DONOR_FEATURE_
FINDINGS.md` §8 and `18_DONOR_FEATURE_REMEDIATION.md` §4; the CAP2-remediation decision that the
removed connector capabilities (Drive / Connected apps) are never offered as switches.

## What was implemented

1. **Engine — the one recommendation vocabulary.** `capabilities.recommendation(capability,
   decision)` returns a structured suggestion or `None`. A capability the user disabled for this
   conversation refuses with three real next steps: `allow_once`, `enable`, `keep_disabled`.
   Everything else returns `None` — not-available-here, needs-setup-with-no-connector, unknown ids,
   allowed decisions. No heuristics, no detectors, no nagging: a recommendation exists only where a
   real refusal already happened and a real action exists.
2. **Refusal producers attach it.** The real web effect (`kel.research`) and the real repository
   effect (`kel.coding`) now return `capability` + `recommendation` next to their existing plain
   refusal text. The actions themselves are the unchanged session-tools machinery
   (`grant_once` / `set_override`) — no new policy, no widening (INV-CAP-001 preserved).
3. **Durable to the shell.** `kel.core` records the recommendation on the job milestone when a
   blocked result settles (and clears it on success), so `/api/state` carries it to the desktop.
4. **Desktop card.** `KelCapabilityCard` + `capabilityRecommendation.ts` render exactly the
   engine's actions — unknown action ids are dropped (fail-closed rendering) — wired to
   `/api/capabilities` (`allow_once`, `set on`). "Keep it off" changes nothing and dismisses the
   card; dismissed cards stay dismissed (no re-nag). Mounted in the Work panel's job section where
   blocked milestones appear.

## Recommendation paths (the §32 record)

| Path | Trigger | Emits | Consumed by | Discriminating test |
|---|---|---|---|---|
| Research refusal | a research task attempts the web effect while Web is disabled here | `capability: web` + 3-action recommendation | milestone → `/api/state` → Work-panel card | `test_blocked_effect_carries_a_structured_recommendation` |
| Milestone settle | the blocked result is recorded by the engine | milestone carries `recommendation` (cleared on success) | `/api/state` consumers | `test_settled_blocked_effect_exposes_the_recommendation_in_job_state` |
| Coding refusal | a coding run attempts repo effects while Files/Terminal/GitHub is disabled here | same fields (same helper) | same | mapping covered by `RecommendationTests`; dedicated coding-blocked discrimination is an audit target |

## Verification (parent-executed)

- Engine focused (`test_capabilities`, `test_research`, `test_acp_host`, `test_v13_work_context`,
  `test_v15_completion`): **83 passed** — includes the new recommendation matrix (allowed → None,
  unavailable → None, unknown id → None, live grant → None) and the two research-blocked tests.
- Engine full suite: recorded in `TEST_EVIDENCE_INDEX.md` (Campaign A baseline 878).
- Desktop: `bunx tsc --noEmit` → 0 errors; `bun run test` → **90 passed** (was 83; +7 helper tests
  for action mapping, request bodies, and confirmations).

## Production effect — what is proven, what is honestly not

- The card's actions hit the same endpoints the Tools control uses; the one-shot grant being spent
  by the real effect and the per-conversation override persisting are already proven by
  session-tools packaged evidence + engine tests (unchanged by this increment).
- **Bound (honest):** this environment has no model provider, so a blocked *run* cannot be produced
  end-to-end in a packaged app. The card's packaged rendering is deferred to the first packaged
  battery that can seed a blocked milestone (recorded: PACKAGED_EVIDENCE_INDEX + LIM-14). The
  Work-panel placement is the first surface; a transcript-inline placement is DEF-014.

## Safety notes

- Recommendations never change state; only the user's action does. Unknown/removed capabilities are
  never recommended. Unavailable capabilities produce a plain sentence and no action (nothing real
  to offer). The card cannot widen anything: grants remain single-use + TTL-bound, overrides remain
  conversation-scoped, and the lease/approval gates still run after both.
