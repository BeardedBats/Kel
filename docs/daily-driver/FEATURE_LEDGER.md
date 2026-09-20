# FEATURE LEDGER — `dev/daily-driver`

Status legend: **DONE** · **DONE (core)** · **PARTIAL** · **IN PROGRESS** · **QUEUED** · **BLOCKED(external)**

| ID | Feature | Source | Status | Commit(s) | Evidence / notes |
| --- | --- | --- | --- | --- | --- |
| L-000 | Lane open: `dev/daily-driver` from `37b1f27`; durable state; `1.7.0-dev` identity | §1–3 | DONE | `3f83be7` | engine identity test OK |
| ENG-001 | Engine claims re-pin (pre-existing red exposed by full suite run) | D0 regr | DONE | `80c4ba2` | `test_v141_claims` 2 OK; full engine suite 1019 OK after |
| D0-001 | Permissions "Work" column human label; raw id behind support detail | HVRA-MINOR-001 | DONE | `9bdf338` | `jobLabels.ts` + 5 tests; tsc+Vitest green |
| D0-002 | Installer/uninstaller FileDescription Kel-native | HVRA-MINOR-002 | DONE (source) | `777fefe` | desc `Kel`; donor-policy pin; packaged re-verify at package phase |
| D0-003 | Remove donor wiki help destination | HVRA-SUG-001 | DONE | `cce55d0` | `LocalAgents.tsx` constant+button removed |
| D0-004 | Single pet-refusal toast (probe artifact documented) | HVRA-SUG-002 | DONE | `f594282` | idempotent toast id; OFF sync untouched |
| D0-005 | `FINAL_V16_RESIDUAL_CLEANUP` records | §D0 | DONE | `288a53c` | IMPLEMENTATION_STATUS.md table |
| D1 | Provider + model onboarding (human statuses, Set up → Save + Verify) | §6–7 | DONE (core) | `0279a1d` | `providerStatus.ts` + 11 tests; page wiring pins; live key validation unavailable (no external creds) — see KNOWN_LIMITATIONS |
| D2 | Update reliability: donor CDN feed severed; fail-closed Kel GitHub check; installer upgrade path documented | §8 | DONE (core) | `7c9df63` | `updateFeed` returns null; `_feedConfigured` guards; `update-policy.test.ts`; packaged upgrade + Properties re-verify at package phase |
| D3 | Remote / WebUI (+security) | §9–10 | DONE (core) | D3 commit (revert `b13301a`) | gateway session enforcement (`gateway-session.unit.test.ts`, 10 tests); anon allowlist; `/qr-login` proxy; WS gating; logout cache invalidation; real-stack matrix + browser evidence in `evidence/d3/`; see KNOWN_LIMITATIONS for aioncore-side constraints |
| D4 | Transcription first-class workflow | §11 | DONE (core) | D4 commit | engine family + page already complete; + client-side searchable recents; `transcription-policy.test.ts` (4 pins); live fixture flow `packaging/verify-transcription-e2e.cjs` + `evidence/d4/`; live Muse path needs a Meta key (see KNOWN_LIMITATIONS) |
| D5 | Needs Your Attention + notifications | §12–13 | DONE (core) | D5 commit | `connection` kind (provider setup needs) in `needsAttention.ts` + component wiring; transition-only notification core (`attentionNotificationCore.ts`, 8 tests) + `useKelAttentionNotification` in the shell; needs-attention suite extended (16 combined PASS); Snooze/Later omitted by design (see DECISIONS D-015) |
| D6 | Continuation / resumability | §14–15 | DONE (core) | D6 commit | derived-only "While you were away" brief (`resumptionBrief.ts` + `KelResumptionBrief.tsx` on the landing page) with 8 unit pins; live restart/resume verdict all-true (`packaging/verify-continuation-restart.cjs` + `evidence/d6/`); continuation stays human-gated (reply "continue") |
| D7 | Long-running autonomy | §16–17 | DONE (core) | D7 commit | engine basis verified + pinned (orphan fencing never auto-retried, durable attempt budgets, provider circuit, route blocks self-clearing); new: orphaned runs surface as needs-you with the engine's reason, route-blocked jobs explicitly non-interrupting, brief reasons preserved + dedupe; `route_block`/milestone `error` added to client types |
| D8 | Adaptive staffing | §18–20 | DONE (core) | `daafd36` + closure commit | engine ladder verified complete + pinned (TIERS D0–D4, rules R1–R10, ceilings, reasons; 8 workforce files); Work page speaks plain language (`staffingLanguage.ts`); **Kel manages its own roster** (seed-on-first-use in `Team.resolve_role`, unknown ids fail closed, 2 new engine pins); Team page is a developer surface (Office plain by default; Roster/Studio + internals behind "Developer view"; `team-surface.test.ts` 3 pins); D0–D3 evidence: 277 workforce tests OK + 19 team tests OK |
| D9 | Learning promotion | §21–22 | QUEUED | — | — |
| D10 | Recipes | §23–24 | QUEUED | — | — |
| D11 | Cross-device continuity | §25 | QUEUED | — | — |
| D12 | Smarter provider routing (+fallback) | §26–27 | QUEUED | — | — |
| D13 | Failure recovery polish | §28 | QUEUED | — | — |
| D14 | Optional Advanced Activity view | §29 | QUEUED | — | — |
| D15 | Security / sandbox boundary improvements | §30–31 | QUEUED | — | — |
| D16 | Live capability revision | §32 | QUEUED | — | — |
| D17 | Plugin / integration developer surface (+UX) | §33–34 | QUEUED | — | — |
| D18 | Synthetic daily-driver dogfood journeys | §36 | QUEUED | — | — |
| D19 | Full regression + package + installed candidate | §39–42 | QUEUED | — | — |
