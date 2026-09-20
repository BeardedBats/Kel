# TEST EVIDENCE — `dev/daily-driver`

## Commands used

- Desktop unit (vitest): `cd desktop && bunx vitest run`
- Desktop focused: `cd desktop && bunx vitest run <files>`
- Desktop typecheck: `cd desktop && bunx tsc --noEmit`
- Engine: `cd runtime && python -m unittest discover -s tests` (add `-p "test_x.py"` for one file)

## Baseline (source: final V1.6 re-audit at `6d957ee9…`)

- Desktop tsc PASS; Vitest 15 files / 156 PASS; focused (donor-policy + needs-attention) 17 PASS;
  installed battery 25/25; engine probe healthy; 0 console/page errors.

## Runs (this lane)

| When (local) | Scope | Command | Result | Notes |
| --- | --- | --- | --- | --- |
| 23:03 | desktop baseline | `bunx vitest run` | 15 files / 156 PASS | pre-D0 tree |
| 23:05 | engine identity | `python -m unittest discover -s tests -p "test_v16_r8_identity.py"` | 3 OK | pins desktop version == engine `__version__` == `1.7.0-dev` |
| 23:05 | new job-label suite | `bunx vitest run tests/unit/job-labels.test.ts` | 5 PASS | HVRA-MINOR-001 |
| 23:06 | desktop after D0 edits | `bunx vitest run` | 16 files / 163 PASS | tsc had found TS7011 → fixed with explicit annotation |
| 23:08 | desktop typecheck (final D0 tree) | `bunx tsc --noEmit` | exit 0 | — |
| 23:08 | desktop full (final D0 tree) | `bunx vitest run` | 16 files / 163 PASS | — |
| 23:09 | focused D0 suites | `donor-policy + job-labels + needs-attention` | 3 files / 24 PASS | donor-policy 11 tests (2 new pins) |
| 23:07→23:19 | engine full suite #1 | `python -m unittest discover -s tests -v` | **1019 tests, 1 failure** | failure = `test_v141_claims` (pre-existing, see ENG-001) |
| 23:11 | claims single file (after re-pin) | `python -m unittest tests.test_v141_claims -v` | 2 OK | — |
| 23:14 | D1 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 23:14 | D1 focused | `provider-status + job-labels + donor-policy` | 3 files / 27 PASS | provider-status 11 tests |
| 23:15 | D1 full | `bunx vitest run` | 17 files / 174 PASS | — |
| 23:19 | engine full suite #2 (re-run) | `python -m unittest discover -s tests` | **1019 tests OK (275.5s)** | fully green |
| 23:18 | D2 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 23:18 | D2 full | `bunx vitest run` | 18 files / 177 PASS | includes `update-policy.test.ts` |
| 09:14 | D3 gateway suite (new) | `bunx vitest run packages/web-host/src/gateway-session.unit.test.ts` | 10 PASS | anon 401 incl. reset-password takeover; allowlist passthrough; `/api/auth/user` validation + cache; logout invalidation; WS gating |
| 09:25 | D3 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 09:2x | D3 full | `bunx vitest run` | 19 files / 187 PASS | includes the new gateway suite |
| 09:27 | D3 real stack — raw boundary matrix | `bun run webui --remote --data-dir C:/Users/Nick/KelDailyDriverRuns/d3-remote` (shipped aioncore from `KelVisualFixInstall`) + `node packaging/diagnose-remote-auth.cjs` | anon 401 ×5 (loopback + LAN, incl. reset-password) · login 200 · cookie 200 ×3 · logout 200 · revoked replay 401 | before the fix the same matrix returned 200 for anonymous LAN reads AND an anonymous `POST /api/webui/reset-password` |
| 09:30 | D3 real stack — browser | `node packaging/verify-remote-e2e.cjs` (Playwright/Edge) | entry → /#/login; login ✓ → /#/onboarding; assistants 24 items; refresh 200; logout → 401; relogin ✓; phone 390 overflow 0; LAN anon 401 | screenshots `evidence/d3/01–04*.png`, machine-readable `evidence/d3/remote-e2e.json`; console noise = pre-login boot probes (documented limitation) |
| — | engine suite | not re-run in D3 (no engine changes) | last full run: 1019 OK (275.5s) | — |
| 09:35 | D4 policy pins (new) | `bunx vitest run tests/unit/transcription-policy.test.ts` | 4 PASS | no-spacebar invariant (Escape-only cancel); action wiring to `/api/transcription`; client-side search; affordances |
| 09:36 | D4 full | `bunx vitest run` | 20 files / 191 PASS | includes the policy pins |
| 09:36 | D4 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 09:37 | D4 live engine fixture flow | `python -m kel.service --data <tmp>` + `node packaging/verify-transcription-e2e.cjs` | all steps OK (1.6s) | practice mode: stream 4.6s→text; upload→combine (8.8s, source consumed); exports (485 chars / 403,244-byte wav); folders create/rename/assign/unassign; key set → `muse`, clear → `fixture`; two plain-language errors. Evidence `evidence/d4/transcription-e2e.json` |
| 09:52 | D5 engine shape probe | `python -m kel.service` + `GET /api/state` | fresh-store shapes recorded | `state.providers` = id list; `state.approvals` = `[]` (non-empty shape unverified — not consumed); provider STATUSES come from the providers list API (`not_installed` / `installed_not_authenticated` / `healthy` / …) |
| 09:56 | D5 suites (new + extended) | `bunx vitest run tests/unit/attention-notification-core.test.ts tests/unit/needs-attention.test.ts` | 16 PASS combined | transitions-only core (silent first snapshot, kinds, cooldown, per-tick cap, truncation, finished) + connection-kind derivations (sorting, unbound, action route) |
| 09:58 | D5 typecheck | `bunx tsc --noEmit` | exit 0 | three defects found by the new tests and fixed: kind filter compared ids instead of kinds; cooldown sentinel `?? 0`; `seen` now mirrors the snapshot (resolved-and-returned items can re-notify after cooldown) |
| 09:58 | D5 full | `bunx vitest run` | 21 files / 199 PASS | — |
| 10:04 | D6 suites (new) | `bunx vitest run tests/unit/resumption-brief.test.ts` | 8 PASS | quiet-when-empty; failed-restore first with a Settings action; finished vs needs-you separation; stopped split (paused/waiting, BLOCKED stays needs-you); go-ahead lines with reasons; section caps + "more" line; fresh-restore seconds/ms normalization; no machinery vocabulary |
| 10:06 | D6 typecheck | `bunx tsc --noEmit` | exit 0 | fixed: continuation candidate's partial `job` is not a full job; added the engine's `restore` field to the `kelState` type (it was always returned by the engine) |
| 10:07 | D6 full | `bunx vitest run` | 22 files / 207 PASS | — |
| 10:09 | D6 live restart/resume | `node packaging/verify-continuation-restart.cjs` | verdict all true | fresh pid; engine_version stable; connection restored; `restore` absent before / planted record survives and is surfaced (`{ok:false, detail, at}`); continuation derived (empty on a work-free store); durable counts stable. Evidence `evidence/d6/continuation-restart.json` |
| 10:22 | D7 engine basis verified | read `runtime/kel/core.py` + `runtime/tests/test_v16_r6_liveness.py` + `test_v16_r3_retry_durability.py` | already complete | `recover_expired` fences expired runs (run ORPHANED, milestone UNCERTAIN + reconcile reason, job WAITING_RESOURCE/UNCERTAIN); `wait_for_route`/`retry_route` carry the route reason and auto-resume; liveness pins reconcile-first/never-auto-retry + late-result discard; retry-durability pins budgets, provider counter/circuit, refusal once exhausted |
| 10:26 | D7 suites | `bunx vitest run tests/unit/needs-attention.test.ts tests/unit/resumption-brief.test.ts` | all PASS (3 needs-attention + 5 brief cases new/updated) | orphan → needs-you exactly once with the engine reason; route-blocked never needs-you; no-reason waiting stays quiet; brief: paused-only "stopped" with reasons, no duplicate lines, summary counted from emitted lines |
| 10:28 | D7 typecheck | `bunx tsc --noEmit` | exit 0 | one test-vs-copy mismatch found and fixed (milestone-reason lookup is not restricted to UNCERTAIN) |
| 10:28 | D7 full | `bunx vitest run` | 22 files / 213 PASS | — |
| 10:36 | D8 engine ladder verified | read `runtime/kel/staffing.py` + `team.py` + workforce test list | already complete | TIERS D0–D4 with band ceilings and recorded reasons; hard rules incl. security ⇒ Sentinel/tier ≥ D2, irreversible or externally visible ⇒ approval + independent review/tier ≥ D2, no tier upgrade as a stall remedy; assignments carry dispatch_tier/authority_max/budget_class; 8 workforce test files (d1, d2, parallel, assurance, learning, schemas, assignment, team) |
| 10:40 | D8 staffing-language pins (new) | `bunx vitest run tests/unit/staffing-language.test.ts` | 4 PASS | summary says "Kel is using an independent review."; per-assignment plain sentences; internals ban (tiers, digests, budgets, assignment ids) |
| 10:42 | D8 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 23 files / 218 PASS | Work page internals table replaced by plain language + summary line |
| 11:0x | D8 roster self-seeding (engine, new) | `python -m unittest tests.test_v14_team` | 19 OK | two new cases: a shipped role resolves without explicit seeding (seed-on-first-use), an unknown id still raises PolicyError |
| 11:0x | D8 workforce selection/boundary evidence | `python -m unittest discover -s tests -p "test_workforce_*.py"` | **277 tests OK (148.1s)** | the eight workforce files (d1, d2, parallel, assurance, learning, schemas, assignment, + fixtures-driven) — note: individual `python -m unittest tests.<file>` runs of four of them error on the sibling `workforce_fixtures` import; the discovery form is the canonical one |
| 11:1x | D8 team-surface pins (new) | `bunx vitest run tests/unit/team-surface.test.ts` | 3 PASS | developer-toggle gate; plain-language office lines; exactly one seed label (developer roster view) after the clean office empty state; engine self-seeding comment + guard pinned |
| 11:1x | D8 typecheck + full (closure) | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 24 files / 222 PASS | Team page developer gate + roster self-seeding; no other suite moved |
| 11:2x | D9 pins (new) | `bunx vitest run tests/unit/learning-proposals.test.ts` | 5 PASS | engine always returns the open queue in /api/work; the client type declares it; page quiet-when-empty, user language, the three wired decisions |
| 11:2x | D9 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 25 files / 227 PASS | "Kel suggests" card + proposal actions; record `value` type corrected to match the payload (JSON string) |
| 11:2x | D9 live HTTP journey | `node packaging/verify-learning-proposals.cjs` | **verdict all true** | seed 2 pending proposals → /api/work shows both, nothing applied; defer keeps it queued; accept applies via the trust model (staging-2 active, staging-1 superseded); reject never applies + empties the queue. Evidence `evidence/d9/learning-proposals.json` |
| 11:3x | D10 engine recipe suite (+1 new) | `cd runtime && python -m unittest discover -s tests -p "test_v13_recipes.py"` | 15 OK | new case: a draft from a job with short milestone ids (`m1`/`m2`) now maps to valid step slugs (`step-m1`/`step-m2`) and validates — the fix for a real bug (the primitive had no caller, so nothing had ever exercised it with the engine's own ids) |
| 11:3x | D10 pins (new) | `bunx vitest run tests/unit/recipes-surface.test.ts` | 4 PASS | draft/run/confirmation-gated save on the HTTP surface + client; Recipes Run wired with the follow-up pointer; Work page drafts first and saves once, on confirm |
| 11:3x | D10 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 26 files / 231 PASS | Run button (Recipes) + Save-as-a-recipe flow (Work) |
| 11:3x | D10 live HTTP journey | `node packaging/verify-recipe-loop.cjs` | **verdict all true** | draft from a real job (not stored); save without confirm refused; confirm persists; re-save idempotent; run + run-again accepted as distinct submissions; first run is a real READY job, the second waits in the durable submission queue (no provider here). Evidence `evidence/d10/recipe-loop.json` |
| 11:4x | engine full suite (post-D10 fix) | `cd runtime && python -m unittest discover -s tests` | **1022 tests OK (292.5s)** | includes the new recipe-from-job regression and the D8 team pins; ran with the `recipes.py` slug-mapping fix in place |
| 11:5x | D11 gateway unit tests (new) | `bunx vitest run packages/web-host/src/kel-gateway.unit.test.ts` | 4 PASS | anonymous 401 (engine never contacted); live session forwarded with `Bearer <engine token>` and the browser cookie stripped; missing descriptor 503; dead engine 502; token absent from bodies |
| 11:5x | D11 pins (new) | `bunx vitest run tests/unit/kel-remote-bridge.test.ts` | 3 PASS | renderer fallback (`/kel${route}`, no "bridge unavailable" dead end); gateway gating/fail-closed strings; both launchers wire the engine data root |
| 11:5x | D11 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 28 files / 238 PASS | gateway + fallback + wiring; no other suite moved |
| 11:5x | D11 live real-stack journey | `node packaging/verify-remote-kel.cjs` | **verdict all green** | real stack: Kel engine + `bun run webui` (shipped aioncore from `KelVisualFixInstall` + web-host + built renderer, `KEL_DATA_DIR` at the engine root). Anonymous `/kel/api/state` 401; first-boot admin login; the desktop-seeded job is visible to the remote session (`desktop_job_visible_remotely`, full `/api/work` reachable); engine token never in a body; engine killed → 502 `KEL_ENGINE_UNREACHABLE`. Evidence `evidence/d11/remote-kel.json` |
| 11:5x | D12 engine routing suite (+1 new) | `cd runtime && python -m unittest tests.test_service_routing -v` | 6 OK | new: `state()` exposes the `run.claimed` route for active jobs (provider + selected/policy/excluded intact) |
| 11:5x | D12 pins (new) | `bunx vitest run tests/unit/route-transparency.test.ts` | 5 PASS | engine exposure strings; client type; bodyless reads are GETs over the gateway (the D11 fix); plain-language sentence + reason translations; renders only when a decision exists |
| 11:5x | D12 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 29 files / 243 PASS | route map + Work-page sentence + GET/POST fallback fix; no other suite moved |
| 11:5x | D12 live route journey | `node packaging/verify-route-transparency.cjs` | **verdict all green** | seed a real job + claim with a full route → `GET /api/state` exposes it (selected/policy/fallbacks/excluded intact; unknown cost+quota flagged); after cancel the job enters CANCELLING and the route stays (clears only at terminal). Evidence `evidence/d12/route-transparency.json` |
| 11:5x | D12 engine full suite | `cd runtime && python -m unittest discover -s tests` | **1023 tests OK (289.9s)** | ran after the `state()` route-map change; includes the new routing test |
| 11:5x | D13 pins (new cases) | `bunx vitest run tests/unit/kel-remote-bridge.test.ts` | 5 PASS | gateway codes mapped to sentences; raw code never thrown; browser-level network drop reads as a device problem |
| 11:5x | D13 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 29 files / 245 PASS | failure language for the remote surface; no other suite moved. (The underlying codes were live-verified in the D11 real-stack journey; this layer is source-pinned.) |
| 11:6x | D14 pins (new) | `bunx vitest run tests/unit/activity-surface.test.ts` | 4 PASS | route + nav entry; high-level sections in user language; internals banned (lease/epoch/run/digest tokens); Work + Activity share `workLanguage.ts` |
| 11:6x | D14 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 30 files / 249 PASS | Activity page + shared language module; one D12 pin re-pointed at the shared module (the extraction moved the strings) |
| 11:7x | D15 containment evidence (existing) | autonomy + boundary suites inside the engine full run | green (1023 OK) | ~20 pinned behaviours: reviewed plan required, roots must exist, frozen releases/system locations refused, narrow scopes, outside-lease denial, fail-closed tools, unknown kinds denied, snapshot-gated destructive actions, expired/revoked leases deny all |
| 11:7x | D15 pins (new) | `bunx vitest run tests/unit/emergency-stop.test.ts` | 3 PASS | two-step arm/confirm; single engine call inside the confirmed branch; service keeps actor authority |
| 11:7x | D15 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 31 files / 252 PASS | deliberate emergency stop; no other suite moved |
| 11:7x | D15 live journey | `node packaging/verify-emergency-stop.cjs` | **verdict all green** | real lease issued (reviewed-plan path) → ACTIVE → emergency stop → REVOKED with `reason: emergency stop`; job PAUSED; a caller-supplied `actor` is refused by the engine itself ("Actor identity comes from the authenticated Kel session, not from the request payload"). Evidence `evidence/d15/emergency-stop.json` |
| 11:8x | D16 engine hardening (+2 new) | `cd runtime && python -m unittest tests.test_v14_autonomy` | 32 OK | an unknown boundary scope (e.g. the plural `roots`) is now refused (`Unknown boundary scope`) instead of silently filing a grant that can never match a check; the five matchable kinds are pinned as accepted |
| 11:8x | D16 pins (new) | `bunx vitest run tests/unit/live-revision.test.ts` | 3 PASS | Permissions-page rule in user language; engine enforcement strings; only user input can widen |
| 11:8x | D16 live journey | `node packaging/verify-live-revision.cjs` | **verdict all green (9/9)** | in-scope allowed → out-of-scope denied → pending request does not widen → user grant widens (one use) → one-time grant does not stick → revoke → next check denied (`rule: lease-revoked`). Evidence `evidence/d16/live-revision.json` |
| 11:9x | D17 pins (new) | `bunx vitest run tests/unit/integrations-overview.test.ts` | 3 PASS | overview reads the engine inventory (not a copy); plain connected/needs-setup/unavailable + reason; setup path only on needs-setup rows |
| 11:9x | D17 live journey | `node packaging/verify-integrations-overview.cjs` | **verdict all green** | `/api/capabilities` returns rows with honest states + reasons; ids stable per conversation. Evidence `evidence/d17/integrations-overview.json` |
| 11:9x | D16+D17 typecheck + full | `bunx tsc --noEmit` · `bunx vitest run` | tsc 0 · 33 files / 258 PASS | integrations card + rule copy; no other suite moved |
| 11:9x | D16 engine full suite | `cd runtime && python -m unittest discover -s tests` | **1025 tests OK (299.6s)** | ran with the boundary-scope hardening; includes the two new autonomy pins |
