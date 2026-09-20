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
| D3 | Remote / WebUI (+security) | §9–10 | QUEUED | — | starts at `desktop/packages/web-host` (see MARATHON_STATE) |
| D4 | Transcription first-class workflow | §11 | QUEUED | — | — |
| D5 | Needs Your Attention + notifications | §12–13 | QUEUED | — | — |
| D6 | Continuation / resumability | §14–15 | QUEUED | — | — |
| D7 | Long-running autonomy | §16–17 | QUEUED | — | — |
| D8 | Adaptive staffing | §18–20 | QUEUED | — | — |
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
