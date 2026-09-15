# KEL V1.4 — TEST MATRIX

Status: v0.1 (Gate 0). Planned structure + verified baseline. Fills per gate; no existing test may be deleted or weakened.

## 0. Method and levels (inherited from V1.3, extended)

- **U** unit — pytest, hermetic, fakes, temp dirs.
- **I** integration — real SQLite store on disk, fake providers, real engine tick loop.
- **L** live — real engine process, throwaway data dirs.
- **P** packaged — real `Kel.exe` / `KelEngine.exe`, Playwright, isolated data root.
- **V** visual — packaged screenshots, keyboard, resizing, accessibility checks.

Retention rule: the engine suite must stay ≥ **267 passed + 10 subtests** at every gate. Deletions/weakenings are prohibited; new tests are additive.

## 1. Verified baseline (this session)

| Suite | Command | Result |
|---|---|---|
| Full engine suite | `cd runtime && python -m pytest tests/ -q` | **267 passed + 10 subtests** (55.58s, exit 0) |

## 2. Planned suites (IDs map to the feature ledger `V14-###`)

| Area | ID prefix | Level focus | Status |
|---|---|---|---|
| Solution quality (V14-001…018) | SLN | U/I + reviewer relay | planned |
| Team / Office / Roster / Studio (019…040) | TEAM | I + L | planned |
| Work Center (041…062) | WORK | I/L/P | planned |
| Memory / context (063…082) | MEM | U/I (extend V1.3 MEM-*) | planned |
| Continuation (083…096) | CONT | I/L (extend V1.3 CONT-*) | planned |
| Verification / trust (097…118) | VER | U/I | planned |
| Providers / credentials (119…136) | PROV | U/I + secret scans | planned |
| Autonomy / guardrails (137…153) | AUTO | U/I adversarial — blocked actions must fail closed | planned |
| Recipes (154…166) | REC | I/L (extend V1.3 recipes) | planned |
| Desktop (167…183) | DESK | P/V + keyboard/a11y | planned |
| Diagnostics (184…200) | DIAG | U/I + sanitization checks | planned |

## 3. New-test requirements (from the brief, instantiated per gate)

- Role versioning/rollback/overrides, assignment snapshots, locked-guardrail isolation, no self-certification, no recursive delegation (G3).
- Credential isolation; no secret logging or unrelated enumeration; provider auth-state distinctions; DeepSeek request path; quota-unknown; exhausted fallback (G6).
- Blocked-by-default checks: Registry writes, screen takeover, synthetic input, non-Firefox general browsing, unrelated personal paths, frozen-release writes, GitHub admin actions, force-push main. Allowed: reviewed-plan edit/test/install/commit/push (G6).
- Packaged: boot, V1.3-data migration, zero orphans after shutdown, relaunch, full visual suite (G10).

## 4. Gate 0 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G0-REF | refs/tag/frozen-hash verification | U (to be scripted) | **PASS** (session 1; manual) |
| G0-SUITE | baseline suite green (267 + 10) | U | **PASS** (session 1) |
| G0-HARNESS | packaged screenshot harness (isolated, offscreen, bounded shutdown) | P | **PASS** (`packaging/capture-screens.cjs`) |
| G0-CAPTURES | baseline captures (2 states × 30 views, 5 widths, 0 errors) | P/V | **PASS** (`docs/v1.4/screenshots/baseline/`) |
| G0-FIXTURE | fixture generator for populated states (jobs/approval/memory) | I | **PASS** (`runtime/tools/seed_ui_fixture.py`) |
| G0-PERF | startup/performance baseline | L | pending (G8 tooling) |

## 5. Gate 1 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G1-DIRECTIONS | two materially different directions rendered + audited (contrast, type, emoji, focusables) | V | **PASS** (`packaging/render-directions.cjs`, `screenshots/directions/`) |
| G1-FOCUS | every tab stop shows a focus ring; first stop = skip link | V | **PASS** (0 failures, both directions) |
| G1-A11Y-BASE | packaged V1.3 a11y probe (contrast/focus/type/tab order) | P/V | **PASS** (findings: `KEL_V1.4_UI_AUDIT.md` §5) |
| G1-DOCS | design system + interaction patterns + accessibility standard + visual acceptance matrix | docs | **PASS** (4 documents) |

## 6. Gate 2 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G2-ARCH | architecture + 5 Best Solution Gate decisions grounded in source | docs | **PASS** (`KEL_V1.4_ARCHITECTURE.md`) |
| G2-TEAM | Team model incl. activity contract + no-fake-specialist enforcement | docs | **PASS** (`KEL_V1.4_TEAM_MODEL.md`) |
| G2-AUTONOMY | lease + guardrail enforcement mapped to AUTO-* tests | docs | **PASS** (`KEL_V1.4_AUTONOMY_POLICY.md`) |
| G2-PROVIDERS | state model + DeepSeek first-class + credential custody | docs | **PASS** (`KEL_V1.4_PROVIDER_SPEC.md`) |
| G2-UX | IA + surface specs + old-surface migration + screenshot strategy | docs | **PASS** (`KEL_V1.4_UX_SPEC.md`) |
| G2-SECURITY | threat model + sanitizer + retention + supply chain | docs | **PASS** (`KEL_V1.4_SECURITY_MODEL.md`) |

## 7. Gate 3 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G3-SUITE | full engine suite after V1.4 modules | U/I | **PASS** (296 passed + 10 subtests; retention rule ≥267 + 10 held) |
| G3-SLN | brief/options/comparison/search/opportunity/idea/recommend/review/approve gate | U | **PASS** (12 tests, `tests/test_v14_solution.py`) |
| G3-TEAM | role versioning · rollback · project/task override precedence · locked-section isolation · assignment snapshot immutability · tool policy fails closed · no recursive delegation · activity contract (no hidden reasoning) · staffing reasons · seed idempotency | U/I | **PASS** (17 tests, `tests/test_v14_team.py`) |
| G3-MIGRATION | migrations 005/006 additive, recorded in `schema_migrations`, idempotent | I | **PASS** |
| G3-API | `/api/brief` + `/api/team` wired in `service._action` | I | **PASS** (service envelope test) |

## 8. Gate 4 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G4-BUILD | desktop dependencies + renderer build on this machine | I | **PASS** (`bun install --frozen-lockfile` 1591 pkgs; `bun x electron-vite build` exit 0 → `desktop/out/{main,preload,renderer}`) |
| G4-ALLOWLIST | `/api/brief` + `/api/team` reachable from the renderer | I | **PASS** (`KelService.ts` route allowlist) |
| G4-FIXTURES | team/solution fixtures seed an isolated data root | I | **PASS** (`data/fixture-team`: 9 roles, 2 assignments, activity + artifact, APPROVED brief) |
| G4-UI | Office / Roster / Studio + Work Center surfaces implemented, routed, compiled, and rendered in a packaged candidate | I/V | **PASS** — `030cb61`/`995485c`; rendered from the candidate package |
| G4-PACKAGE | candidate package assembly (asar dedup parity + engine identity) | I | **PASS** — new asar 9,552 files / 1,103 dedup groups / 10,220,315 B saved (frozen baseline 9,548 / 1,103 / 10,220,315; +4 files = the new Kel UI chunks); `verify_engine_pyz.py` → 30 kel modules matched, RESULT: OK |
| G4-CAPTURE | five-width captures of the new surfaces (packaged candidate) | V | **PASS** — 49 shots, 0 renderer errors, 0 blank, app exit 0 (`docs/v1.4/screenshots/g4/`, 20 route views) |
| G4-DEEPLINK | `/team/roster` + `/team/studio` deep links open their own tab | V | **PASS after fix** — distinct rendered content per route (previously all three rendered Office) |
| G4-A11Y-ROUTES | contrast/focus on the new routes | V | **PASS with one note** — table-header contrast fixed (4.35 → ≥6:1); the only remaining failure per route is the donor sidebar label “Projects” (2.92:1) → G7 |
| G4-SHUTDOWN | engine stops when the app closes | I | **NOTE (not a pass)** — `engineStopped: false`, `engineKilled: true` (bounded fallback), `closeOutcome: close-timeout` → G7/G10 item |

## 9. Gate 5 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G5-PROJECTS | Projects workspace (Knowledge · Map · Recipes) implemented, routed at `/projects`, `/projects/knowledge|map|recipes`, Sider entry added | I/V | **PASS** — rendered from the packaged candidate |
| G5-MEMORY | knowledge records (type · trust · status · source · updated) with Confirm · Retract · Forget wired to `/api/memory` | I/V | **PASS (render)** — 3 fixture records at 6/10 and 3/10 trust with actions; live action round-trip still to verify |
| G5-MAP | map sections (trust · freshness · digest · sources) plus Refresh/Build over `/api/map` | V | **PASS (empty state)** — the fixture project has no map; the build action renders and reads honestly |
| G5-RECIPES | recipe library over `/api/work` | V | **PASS** — 5 built-in recipes listed (Audit and Repair, Continue Work, Fix Bug, Research The Implement, Ship Release) |
| G5-CAPTURE | five-width captures of the Projects surfaces | V | **PASS** — 44 shots, 0 renderer errors, 0 blank, app exit 0 (`docs/v1.4/screenshots/g5/`) |
| G5-A11Y | route a11y probe on the new routes | V | **PASS** — contrast failures 0/0/0; 12px floor; 0 emoji |
| G5-VERIFY | Work Center verification panel: worker-reported vs Kel-verified, milestone states/attempts/checks, artifact viewer, Pause · Resume · Cancel over `/api/control` | I/V | **PASS (render)** — “Worker reported: 0 of 1 milestones accepted · Kel verified: UNCERTAIN”, milestone row `UNCERTAIN · 1 attempt · 1 checks · out.md · not verified — checks have not passed`; artifact button correctly hidden for a non-accepted milestone |
| G5-CONTINUATION | continuation candidates from `/api/state.continuation` rendered as a numbered chooser with recorded reasons | V | **PASS (render)** — one candidate listed with its verdict and the honest note “durable state only — no hidden reasoning; continue from chat — Kel never resumes in the background” |
| G5-CAPTURE-2 | five-width captures after the verification/continuation increment | V | **PASS** — 34 shots, 0 renderer errors, 0 blank, app exit 0 (`docs/v1.4/screenshots/g5/`, tag `g5b`) |
| G5-RECEIPT | receipt viewer exercised end-to-end: fixture worker result → checks (`artifact_digest`, `min_chars`) → ACCEPTED → job verdict VERIFIED → publish | I/V | **PASS** — seed reports `{"verify": "VERIFIED", "verdict": "VERIFIED"}`; UI shows “Worker reported: 1 of 1 milestones accepted · Kel verified: VERIFIED”, row `ACCEPTED · 1 attempt · 1 checks · out.md · View artifact`, and the auto-loaded **Receipt — m1** with the artifact text |
| G5-STATE-API | the verified job is visible to the shell (conversation scoping) | I | **PASS after fix** — the verified fixture job is seeded into the `main` conversation the shell renders (“3 jobs in this project · 2 waiting on you”, `2 of 8 steps used`) |
| G5-CAPTURE-3 | capture after the receipt/verified-job fixture | V | **PASS** — tag `g5d`, 0 renderer errors, 0 blank, app exit 0 |
| G5-DRYRUN | recipe preview/dry-run over `/api/recipes` action `preview` | I/V | **PASS** — compiled payload renders with inputs and permission preview; engine state unchanged by design |
| G5-INTERACTIONS | real clicks driven against the packaged candidate with engine before/after reads (`packaging/verify-actions.cjs`) | I/V | **PASS** — `ok: true`, 3/3 steps clicked and rendered; `knowledge-confirm` **changed engine state**, `recipe-preview` and `work-resume` unchanged for recorded reasons; clean close |
| G5-MAP-VOCAB | project map action vocabulary | I | **PASS after fix** — `build` → `refresh` (engine implements `refresh`/`stale`) |

## 11. Gate 6 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G6-REGISTRY | provider definitions: class (native-cli · api), auth mode, base URL, per-model capabilities | U | **PASS** — `claude-code`, `codex`, `internal` (Anthropic API), `deepseek` (`https://api.deepseek.com/v1`) |
| G6-CAPABILITY | capability matrix lookups (`text`, `vision`, `tools`, `edit`, `shell`) | U | **PASS** — `models(provider, capability)`; e.g. `deepseek` → `deepseek-chat`/`deepseek-reasoner`, `internal` → `claude-sonnet-4-6` (vision) |
| G6-STATES | state model: not installed · installed-not-authenticated · healthy · degraded · quota · **quota not reported** · unavailable | U | **PASS** — CLI detection via PATH/auth file, API via credential metadata, `circuit_until` → degraded, quota present/0/absent distinguished |
| G6-READINESS | readiness preflight with recorded reasons + fallback chain | U | **PASS** — honours the preferred provider, records “Fell back to …” with the unusable reasons, and refuses cleanly when nothing is usable |
| G6-CREDENTIALS | engine stores credential **metadata only** (provider · fields · `credential_ref` · timestamps) | U | **PASS** — setting a credential requires a non-empty reference; no value column exists; delete removes metadata only |
| G6-USAGE | append-only provider observations (`provider_usage`) | U | **PASS** — ordered reads with limits; credential set/delete are observed |
| G6-API | `/api/providers` service envelope | I | **PASS** — actions `list`, `status`, `readiness`, `credentials`, `set_credential`, `delete_credential`, `usage` |
| G6-MIGRATION | migration 007 (`provider_credentials`, `provider_usage`) additive + idempotent | I | **PASS** — recorded in `schema_migrations`; suite **316 passed + 10 subtests** (20 new PROV-* tests) |

## 12. Gate 6 autonomy additions

| Id | Check | Level | Status |
|---|---|---|---|
| G6-LEASE-ISSUE | a lease requires a reviewed plan (`review_ref`), ≥1 existing root; frozen releases and system locations cannot be leased | U | **PASS** |
| G6-AUTO-ROOT | writes inside the lease are allowed, outside are denied (`lease-scope`) | U | **PASS** |
| G6-AUTO-REPO | repository actions match only leased repositories | U | **PASS** |
| G6-AUTO-BROWSER | browser targets limited to leased domains (suffix-aware), others denied | U | **PASS** |
| G6-AUTO-TOOL | tool policy fails closed for unleased tools | U | **PASS** |
| G6-AUTO-BLOCK | locked kinds (`registry`, `system`, `credential`, `github_admin`) are never allowed and map to their guardrail rule ids | U | **PASS** |
| G6-AUTO-FROZEN | frozen paths are denied even inside a leased root | U | **PASS** |
| G6-AUTO-DESTRUCT | destructive actions require a snapshot reference **and** stay inside the leased root | U | **PASS** (code fixed in-gate: `destructive` now matches root scope) |
| G6-AUTO-LEASE-EXPIRY | expired, revoked, and unknown leases deny everything | U | **PASS** |
| G6-AUTO-NO-PROMPT | approved-plan writes never create approval rows (no prompting) | U | **PASS** |
| G6-AUTO-ASK-ONCE | boundary requests: deny keeps the target blocked; a one-time grant is used exactly once (`grant-used`); a project grant repeats; only the user can resolve; a request resolves once | U | **PASS** |
| G6-AUTO-GUARDRAIL-IMMUTABLE | the locked block is presented read-only and weakened rules are detected (tamper → `PolicyError`) | U | **PASS** |
| G6-AUTO-EMERGENCY-STOP | emergency stop revokes every active lease (user only) | U | **PASS** |
| G6-LEASE-EVENTS | `issued` / `allowed` / `denied` / `expansion.*` / `emergency_stop` recorded for the receipt | U | **PASS** |
| G6-AUTONOMY-API | `/api/autonomy` service envelope (`issue`, `check`, `revoke`, `leases`, `request`, `resolve`, `requests`, `guardrails`, `emergency_stop`) | I | **PASS** |
| G6-MIGRATION-8 | migration 008 (`capability_leases`, `lease_scope`, `lease_events`, `boundary_expansion_requests`) additive + idempotent | I | **PASS** — suite **346 passed + 10 subtests** (30 AUTO-* tests) |

## 13. Gate 6 UI additions

| Id | Check | Level | Status |
|---|---|---|---|
| G6-PROVIDERS-UI | `/providers` renders one card per provider with the engine's real state, models + capabilities, readiness preflight, credential-metadata section | V | **PASS** — “Claude (Claude Code) · healthy · quota not reported · Native CLI · subscription session”; “DeepSeek API · installed not authenticated · API key · https://api.deepseek.com/v1”; readiness panel with capability + prefer; “Credential metadata (values are never stored here)” |
| G6-AUTONOMY-UI | `/autonomy` renders leases with scope/expiry/revoke, boundary requests with the recorded what/why/benefit/fallback/risk and the three decisions, the locked guardrail block, and the scope probe | V | **PASS** — “1 active lease · 1 boundary request waiting on you”; scope list `domain: docs.python.org`, `repo: …\fixture-project`, `root: …\fixture-project`; request `domain: github.com` with Allow once / Allow for this project / Deny |
| G6-ENGINE-PACKAGING | the candidate's engine must be rebuilt after engine changes | I | **FINDING + FIXED** — the first capture returned “Unknown action” for both pages because the candidate still carried the pre-`providers.py` engine; after `scripts/build-runtime.ps1` + `verify_engine_pyz.py` (`RESULT: OK`) and replacing `resources/kel-engine`, both pages read real data. Packaging step recorded in AUTO_RESUME |
| G6-CAPTURE | captures + route probe for the new surfaces | V | **PASS** — tags `g6`/`g6b` (27 shots each incl. five-width core views), 0 renderer errors, 0 blank, app exit 0; route contrast failures **0/0** on `/providers` and `/autonomy`; 12px floor; 0 emoji |

## 14. Gate 6 credential custody

Evidence: `docs/v1.4/screenshots/audit/v14/credentials/credentials-evidence.json` +
`credentials-{before,after}-store.png`, produced by `packaging/verify-credentials.cjs` (exit 0).

| Check | Result | Verdict |
|---|---|---|
| OS-backed storage available (`safeStorage` / DPAPI) | `storageAvailable: true` | **PASS** |
| Store through the Providers UI (real click, real value) | `rendererStatus {deepseek: ['api_key']}` | **PASS** |
| No value getter on the bridge | `valueGetterAbsent: true` | **PASS** |
| Engine holds metadata only | `credential_ref: kel:provider:deepseek:api_key`, `fields: ['api_key']` | **PASS** |
| On-disk store is ciphertext, not plaintext | `storedKeys ['deepseek:api_key']`, `fileHasPlaintext: false`, `fileBlobLooksEncrypted: true` | **PASS** |
| Value never rendered | `plaintextNotRendered: true` | **PASS** |
| Delete removes both copies | `deleted {removed: 1}`, `fileAfterDeleteHasProvider: false` | **PASS** |

In-gate findings: the candidate engine must be rebuilt after any engine change (recorded as a
packaging rule), and two self-inflicted defects were caught by the evidence loop — a mistyped harness
config path that packed a stale bundle, and an undefined helper (`act is not defined`) in the Providers
page that only surfaced under a real click.

## 15. Gate 7 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G7-REDIRECTS | donor settings routes (`model`, `tools`, `skills`, `agent`, `capabilities`, `skills-hub`) no longer dump the user on `#/guid` | I/V | **PASS** — captures at `/settings/model` → `#/providers`, `/settings/tools` → `#/autonomy`, `/settings/skills` → `#/team/roster`; byte-identical to the direct surfaces (70314 / 93211 / 77456) |
| G7-CONTRAST | muted-text contrast across boot, the work drawer, and every sampled route | V | **PASS** — failures **6 → 0** (boot 0, drawer 0, `work`/`providers`/`autonomy` 0/0/0); smallest text 12px; 0 emoji |
| G7-CONTRAST-SOURCE | the repairs are at the token/source level, not per-instance patches | I | **PASS** — `--bg-6` (#86909c → #5c6470), `.arco-btn-outline`, `.assistantPromptHint`, `.workspaceEmptyBtn`; each measured 2.92–3.1:1 before |
| G7-PROBE-EVIDENCE | the probe names the failing element + classes for future passes | I | **PASS** — `element` field added (`span._assistantPromptHint_…`), which is how the last two defects were located |

Remaining in Gate 7: onboarding for first run, search + command palette, tray/notification/pet tokenization,
and the shell-level keyboard pass (skip link, nav-first order, 30/30 focus rings).

| G7-FOCUS | visible focus ring on every tab stop | P/V | **PASS** — **0/30 → 30/30** stops carry `solid 2px rgb(14, 124, 90)` (the Kel accent); probe resets focus before the pass so the sequence starts like a fresh load |
| G7-SKIP-LINK | the shell's first tab stop is the skip link | I/V | **PASS** — on a fresh load the first stop is `A “Skip to main content”` (`isSkipLink: true`), focused and visible (`rect [8, 10, 162, 39]`) with a ring, targeting the existing `#kel-shell-content`; verified by `packaging/probe-skip-link.cjs` (`firstTabStop.isSkipLink: true`, `targetExists: true`, 0 errors) and by the a11y probe's fresh-load order (`focusOrderBoot[0]`, 15/15 stops ringed). The earlier “not in the tab order” observation was a **probe-ordering artifact** (the pass ran after the drawer had been opened) — fixed by collecting the fresh-load order before any interaction |
| G7-FOCUS-BOOT | fresh-load tab order | V | **PASS** — 15/15 stops ringed, first stop = skip link |
| G7-PALETTE | command palette (`Ctrl+K`, `/` for search) with engine-derived results | I/V | **PASS** — `verify-palette.cjs` exit 0, keyboard-only: closed on load → `Ctrl+K` opens **24 results** (navigation + jobs with verdicts + knowledge with trust + recipes + roles) → typing “providers” filters to one → **Enter navigates to `#/providers`** → `/` reopens in search mode → `Esc` closes; 0 errors |
| G7-PET | pet/confirm surface tokenized and audited | V | **PASS** — muted tone `#86909c` → `#5c6470`, shortcut text 11px → 12px, `prefers-reduced-motion` block added; `render-directions.cjs` on the three pet documents: **0 contrast failures**, 0 emoji, exit 0 (first audit of these surfaces; their bodies are script-rendered, so only CSS/DOM-level checks apply until a live pet-window capture exists) |
| G7-RENDER-SCOPE | renderer focus assertion scoped correctly | I | **PASS** — a document with no focusable controls is exempt from the skip-link requirement, while the directions regression still reports `focusable: 14`, `focusRingFailures: 0`, `firstStopIsSkipLink: true`, exit 0 |
| G7-ONBOARDING-PAGE | first-run onboarding flow renders with real engine reads | V | **PASS** — captured at `#/onboarding`: “Set up Kel · Step 1 of 5 · Welcome”, “Skip setup”, the local-first/private copy, providers from `/api/providers`, project from `/api/state`, and the locked-guardrail block from `/api/autonomy`; completion writes `kel.onboardingCompleted_v1` and routes to `/work` (skip → `/guid`) |
| G7-ONBOARDING-GATE | the automatic first-run trigger fires on a genuinely fresh install | I/V | **PASS** — `verify-onboarding.cjs` exit 0: fresh root timeline `['', '#/onboarding']` → rendered → click-through → `#/work`; the **same root on the second launch stays on `#/guid`** (flag persisted, offered exactly once); 0 errors in all three launches. Root cause of the earlier miss: the freshness test used a conversation count, and the donor keeps a default conversation on a brand-new profile, so the rule was changed to **flag-only** with `configService.initialize()` awaited. Recorded deviation: a profile migrated from an earlier Kel has no flag, so it is offered the flow once and dismisses it with “Skip setup”; a stricter rule needs a renderer-readable “previous install” signal |
| G7-SEMANTICS | donor drawer controls use semantic elements | I | **PASS (false positive, resolved with live DOM evidence)** — the audit flagged “DIVs with `tabindex`”. A dedicated probe (`packaging/probe-drawer-tabs.cjs`) inspected the mounted drawer: the tab titles are `<div class="arco-tabs-header-title" role="tab" tabindex="0" aria-selected="false" aria-controls="arco-tabs-0-panel-N">` and the panes carry `role="tabpanel"` (7 tabs), so they are correct WAI-ARIA tabs wired to their panels, keyboard-operable and now ringed. The earlier `role=None` reading came from my own **sampling artifact** (the post-interaction focus recorder did not capture the role attribute). No refactor needed |
| G7-SIDER | navigation matches the V1.4 information architecture | I | **PASS** — the Sider renders exactly the Kel entries in order (`Work · Team · Projects · Providers · Autonomy` … now also `Diagnostics`) ahead of the donor conversation list and Settings; after fixing the donor group label (`conversation.projectsSection`: `Projects` → `Project conversations`) the rendered text contains **exactly one** “Projects” token (verified by count in `g7/g7sider-texts.jsonl`) |
| G7-NOTIFICATIONS | notification restraint (one OS notification per state change, suppressed when focused, setting respected) | I | **PASS (verified in code)** — `hooks/system/notification/useDesktopTurnNotification.ts` fires on **turn finish** only (a state transition), the renderer merely reports “a turn finished”, the **main process** decides whether to show it, skips while the main window is focused, respects `system.notificationEnabled`, and `useNotificationClick` navigates back to the originating conversation |

## 16. Gate 8 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G8-SNAPSHOT | health observation over real engine sources | U/V | **PASS** — integrity `ok`, main file 850.0 KB, WAL 0 bytes, free pages 0 of 145, job/run counts, runs past their fence, provider states, recorded worker pids with liveness |
| G8-SPAN | startup span is **measured**, not claimed | V | **PASS** — the service records its own construction cost (`engine-start 420.24 ms` in the captured run) and the surface states its basis (“measured from recorded spans; phases not recorded are simply unknown”) |
| G8-EXPORT | sanitized export is allowlist-only with a receipt | U | **PASS** — payload keys ⊆ `EXPORT_ALLOWLIST`; a planted `sk-live-…` marker in a job request and in a worker identity never appears; the receipt lists what is excluded (credentials/tokens/API keys, transcripts, environment dumps) |
| G8-REPORT | local issue report never leaks a pasted secret | U/V | **PASS** — secret-shaped tokens in the user's own note are redacted (`[redacted]`) with a notice in the file; the report is written to `diagnostics/` and nothing is sent anywhere |
| G8-RETENTION | purge removes expired observations and never touches jobs/memories/approvals | U | **PASS** — retention keys validated (setting retention on `jobs` is refused); purge reports per-table removals; job rows survive |
| G8-COMPACT | compaction backs up first, then vacuums, and closes its handles | U | **PASS** — `compact()` returns before/after bytes + integrity + backup note; the leaked-connection bug found by the tests is fixed (a lingering handle kept the DB locked on Windows) |
| G8-ROBUSTNESS | snapshots work on any store state | U | **PASS** — `native_processes` is created lazily by the runner, so the snapshot guards it; `jobs` state is read from the JSON payload (the columnar assumption was wrong) |
| G8-CAPTURE | five-width captures + route probe | V | **PASS** — `screenshots/g8/` (25 shots, 0 renderer errors, 0 blank, app exit 0); route contrast failures **0**; smallest text 12px; 0 emoji |

Remaining in Gate 8: nothing — the gate is closed; its honestly-empty states (no live provider, no
running worker) are carried into Gate 9 as capture gaps rather than defects.

## 17. Gate 9 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G9-COMPARE | scripted before/after comparison pipeline | I | **PASS** — `packaging/make-comparisons.cjs` pairs capture runs that share the harness view ids (handling each generation's run-index prefix) and composes side-by-side sheets with a byte-delta index |
| G9-COMPARE-COVER | comparisons generated for every view the V1.3 baseline and V1.4 share | V | **PASS** — **23 sheets** in `screenshots/comparisons/` (boot/chat, work drawer + its tabs: continue · knowledge · map · recipes · preview · refresh-after, drawer close, all eleven settings pages, 1280-wide repeats); `index.json` records baseline/final sizes and deltas |
| G9-GAPS | views that exist in only one generation are listed rather than faked | I | **PASS** — the index lists only true pairs; V1.4-only surfaces (work/team/projects/providers/autonomy/diagnostics/onboarding) have no baseline counterpart and are covered by their own gate captures |
| G9-DARK-TOKENS | the muted-text token layer is corrected **per theme** | U/V | **PASS** — light `#5c6470` (V1.3 measured 2.92:1 on `#f2f3f5`) and dark `#9aa4b2`; verified by `packaging/probe-tokens.cjs`, which reports the resolved values in both themes (`--bg-6`, `--color-bg-6`, `--kel-text-2`, `--kel-surface-1`) rather than assuming them |
| G9-DARK-SWITCH | the harness renders real dark mode | I | **PASS** — the donor switches with a **pair** (`html[data-theme]` for the CSS-file tokens and `body[arco-theme]` for Arco component styles). Setting only the root left `body.arco-theme: "light"` and kept Arco text buttons on light rules; with the pair applied, dark route failures fell (work 2→1, providers 6→5, autonomy 4→3, diagnostics 4→3) and `paletteBg` measures `rgb(38,38,38)`/`rgb(26,26,26)` |
| G9-MOTION | reduced-motion fallback covers the whole shell | I | **PASS** — the G9 design review flagged donor transitions without a fallback; my rule was scoped to `.kel-scope *` and is now global (`*`), so donor surfaces (toasts, workspace tree) degrade too |
| G9-DENSE | compact density mode is real and engages automatically past ten rows | I/V | **PASS** — the design system defined `[data-density='compact']` tokens but the Work Center never applied them; it now sets `data-density` from the row count (`jobs + assignments > 10`) and compact mode visibly tightens table rows and card padding rather than shrinking type. Verified on a `--dense` fixture: **`density: compact`, 19 rendered rows**, header “16 jobs in this project · 7 waiting on you”, and contrast **0** in the dense capture |
| G9-POPULATED | the G8 capture gaps (empty providers / no workers) are populated from real APIs | I/V | **PASS** — the fixture now calls `set_credential_metadata` for two providers, records two provider observations, and inserts two `native_processes` rows (one with a passed deadline). Rendered evidence: the Providers page shows the DeepSeek card with **2 metadata rows** (`kel:provider:*`), and Diagnostics renders the process table with the labels now distinguishing the cases correctly — `run-orphan · no — orphan candidate · past deadline` versus `run-finished · no — not running` |
| G9-PETS-LIVE | pet windows captured live (the V1.3 baseline had none) | V | **PASS** — the harness gains `--pets`: it enables the desktop pet through its own Settings → Pet switch and captures every non-main window whose URL/title is pet-ish. Result: **2 windows** — `pet.html` at 280×280 and `pet-hit.html` at 168×168 — with 0 renderer errors and 0 blank frames; window identification is by exclusion so the main window is never mis-recorded into the manifest |
| G9-FIXTURE-DENSE | a dense capture state exists and is reproducible | I | **PASS** — `seed_ui_fixture.py --dense` seeds twelve varied jobs (five states, mixed verdicts) plus one long request; the harness now dismisses first-run setup on a freshly seeded root through the product's own “Skip setup”, so any seeded root can be captured (found while running this check — a fresh root otherwise lands on onboarding) |
| G9-NO-GRADIENTS | the design review's donor CSS findings are repaired | I | **PASS** — six toast backgrounds (four gradients, two cream) replaced with flat semantic fills per theme (`#e8f5ef` · `#fef3c7` · `#f2f3f5` · `#fef3f2`, dark `#16281f` · `#2a2113` · `#1c232c` · `#2a1614`), including removing the duplicated success rule the change initially left behind |
| G9-DARK-REMAINDER | remaining dark failures, precisely attributed | V | **PASS (closed)** — with the app-path switch in place, the three labels cleared and the only remaining failures were white text on the dark accent (3.16:1) in primary buttons and selected tabs. Fixed at the token level with per-theme **accent ink** (`#ffffff` light / `#101418` dark) applied to `.kel-btn--primary` and `.kel-tab[aria-selected='true']` (removing a stale `--kel-text-inverse` declaration that had been overriding the new one). Final audits: **0 contrast failures in BOTH themes** — boot 0, drawer 0, and 0 on all eleven routes (`work`, `providers`, `autonomy`, `diagnostics`, `team-office`, `team-roster`, `team-studio`, `projects-knowledge`, `projects-map`, `projects-recipes`) |
