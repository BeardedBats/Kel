# DEFERRED_ITEMS — deliberate deferments with rationale

updated: 2026-09-18T16:05Z
rule: no vague "later". Every item records why, release impact, required future evidence, whether
it blocks V1.6, owner, and the revisit condition.

| ID | Item | Why deferred | Release impact | Required future evidence | Blocks V1.6? | Owner | Revisit condition |
|---|---|---|---|---|---|---|---|
| DEF-001 | Phase 5.7 — adaptive staffing enablement | Entry conditions unmet: no doc-13 full campaign window, no user sign-off; enabling would fabricate readiness | None (shadow learning stays on) | doc-13 campaign (classes 3/5/9 + baseline-B conflict rate) + pre-registered H1–H5 outcomes + explicit user sign-off | NO | user (sign-off) + Main | Campaign results + user sign-off |
| DEF-002 | Phase 5.8 / Phase 8 — Advanced Worker View | **DECISION MADE 2026-09-18: deferred beyond V1.6** (North Star ONE assistant; doc 12 success = 100% zero visits; no product decision or usability review exists; no user-reported need) | None for V1.6 (hidden orchestration stays) | Post-V1.6 product decision + usability review; then a bounded Advanced/Details-only increment behind a setting | NO | product/Nick | Decision recorded: `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md` |
| DEF-003 | Phase 12 — Rust migration | Rust audit verdict NO_MIGRATION_NEEDED_NOW at `9c1e7d0`; **Phase 11 recheck 2026-09-18 upheld the verdict; Phase 12 explicitly CLOSED** | None | Re-entry only via the rust-audit §07 re-open triggers | NO | Main | Closed (2026-09-18) |
| DEF-004 | doc-13 full evaluation campaign | Pilot (classes 2/6/8) succeeded; full matrix is a validation vehicle, not a release behavior | None (nothing reads it to gate) | Campaign run over 10 classes × 3 configs × ≥3 seeds | NO | Main/user | Before any adaptive-enablement re-entry |
| DEF-005 | Optional provider validation (providers without available credentials) | No credentials available in this environment. Phase 10 (2026-09-18): `claude` real call PASS; `codex` blocked by installed CLI version (`gpt-6-astra`); `internal`/`deepseek` no credentials anywhere | Documented limitation, not a blocker | Real call evidence when access exists | NO | Main/user | When credentials/CLI updates become available |
| DEF-006 | Per-project flag storage (workforce flags) | Current single-flag scope is sufficient for shadow behavior | None | Design + migration when per-project control is needed | NO | Main | First real multi-project flag need |
| DEF-007 | Overlay content at calibration | Overlays v1 ship as a graceful no-op registry until real role overlays are authored | None | Authored overlay content + calibration results | NO | Main | When role overlays are content-authored |
| DEF-008 | Provider 'web'/context tokens in evidence | Only evidence-backed tokens allowed; no evidence yet (Phase 10 had no real API-provider runs — remains deferred) | None | Evidence from real provider runs | NO | Main | First real API-provider run |
| DEF-009 | F16-3 — workforce guarantees stay engine-level (no production caller) | Wiring into live product flows is a product decision; guarantees hold engine-level | Documented limitation | A wiring increment decision | NO | Main | Sprint §30 "provider/Workforce real wiring" item — re-decide in Campaign A |
| DEF-010 | Human pixel review | Requires a human; no image perception in agent threads (honest limitation) | Release gate remains open by design | Human review of `packaged-visual5`/later captures via SCREENSHOT_REVIEW_INDEX | YES for release (not for RC) | Nick | At the pre-release human gate |
| DEF-016 | Generic credential mediation platform | Round 2.5 H: no demonstrated gap requires a proxy platform; V1.6 proves the existing containment boundary instead | None | A demonstrated integration that needs mediated credentials | NO | Main | Post-V1.6, only if a real integration demands it |
| DEF-017 | Network-aware runtime authority / OS egress firewall | Round 2.5 I: native-host execution is explicitly a user-authorized full-access runtime, not a sandbox; an OS firewall is a platform project | None (documented authority fact) | A product decision + platform research | NO | Main/product | Post-V1.6 research (recorded in the roadmap) |
| DEF-018 | Trust-tainted execution | Round 2.5 O: research-only; no V1.6 need | None | Research findings + product decision | NO | Main | Post-V1.6 |
| DEF-019 | Narrow runtime ABI refactor | Round 2.5 Q: no demonstrated costly coupling; no elegance rewrite | None | Evidence of real coupling cost | NO | Main | If coupling becomes demonstrably costly |
| DEF-020 | Capability/config revision provenance | Round 2.5 P is satisfied for V1.6 by the LIVE-AUTHORITY invariant (no silent widening; revocation may narrow); full provenance history is post-V1.6 | None | A product need for revision history | NO | Main | Post-V1.6 |

## Rejected for the current roadmap (not deferred — no plan exists)

Round 2.5 §23/§24 items that are **rejected** rather than deferred, recorded so no future reader
mistakes them for missing work: arbitrary nested agent spawning · a new RBAC system · a new workflow
engine · a second recipe runtime · HMAC-everything receipt architecture · a second memory platform ·
a universal vector database · a giant knowledge graph · autonomous memory agents · an OS-level
Windows network firewall · public A2A · one giant unified runtime-state enum · a new Advanced Worker
View · adaptive staffing (see DEF-001) · Profiles · a speculative Rust migration (see DEF-003) ·
generic agent-cockpit UI. Each may only return through a new product decision with evidence.
| DEF-011 | Final freeze/tag/stable release | Campaign A stops BEFORE release by directive | Intentionally not started | Campaign B audit + Campaign C repairs + gates | YES for release | Nick | After audit + repair |
| DEF-012 | Memory stale-detection wiring (`source_digest` producers + a `revalidate` caller) | No producer/caller yet; mechanism is engine-ready and test-covered; staleness never gates anything | None (nothing depends on it) | Producer design (which source facts carry digests) + refresh loop + focused tests | NO | Main | First repo-fact producer needing staleness |
| DEF-013 | Localization of new v1.6 surfaces (knowledge UI + siblings) | Copy intentionally Kel-native English; the release program's locale pass owns translations (declared 2026-09-17) | Non-English users see English on new surfaces | Locale pass across 12 locales + parity checks | NO for RC (decide at release gates) | release program | Pre-release (localization gate) |
| DEF-014 | Transcript-inline capability card placement | Needs a live-run refusal (provider) to design against; the Work-panel placement already delivers the recommendation | None for RC | Provider-backed journey + placement decision | NO | Main | First provider-backed packaged battery |
