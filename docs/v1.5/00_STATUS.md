# 00 — Status (Kel V1.5)

Baseline: `main` @ `6b01e04` (V1.4.1 release record; tags `v1.4.0` and `v1.4.1` present). The
first V1.5 increment is committed as **`b1f9aa5`** (`feat(v1.5): central authorization boundary in
the execution path`); it is not yet released or tagged.

Verified at program start (2026-09-15):

- frozen releases `Kel Releases/Kel-V1.4.1-Frozen` and `Kel Releases/Kel-V1.4-Frozen` both verify
  **3/3** with `scripts/verify-release.ps1`; they remain immutable regression baselines;
- baseline suite before V1.5 changes: **375 passed + 10 subtests** — matches the V1.4.1 release
  record exactly;
- scopes read: `docs/v1.4/`, `docs/v1.4-postrelease/`, `docs/v1.4.1/` (deferral list + 38-row
  triage);
- V1.5 charter: the program spec (32 workstreams, 14 gates, required deliverables), which governs.

## Gate board

| Gate | State | Evidence |
|---|---|---|
| G0 baseline / scope / ledger | **open** — baseline verified; `docs/v1.5` created; ledger classified (`08_LEDGER.md`); remaining: per-row requirement texts are re-read from the ledger when each row is worked | this file, `08_LEDGER.md` |
| G1 authorization architecture | **implemented** — `kel/authorize.py`, migration 010, model doc; review checkpoint run this turn (**CONTINUE**) | `02_AUTHORIZATION_MODEL.md`, `test_v15_authorize.py` |
| G2 execution-path enforcement | **closed** — source-traced effect-path inventory (`02A`, 28 rows), side doors closed (lease-issuance API, greenfield creation, forgery bindings), 25/25 G2 cases evidenced, restart/resume + parallel isolation proven; closure review **CONTINUE** | `02A_EFFECT_PATH_MATRIX.md`, `test_v15_authorize.py` |
| G3 roles / leases / boundary | **closed** — frozen role snapshot per run at claim, enforcement reads the snapshot, coding gate covers `git`/`run_tests`/`write`; leases + expansion end-to-end; closure review **CONTINUE** | `test_v15_roles.py`, `02_AUTHORIZATION_MODEL.md` |
| G4 credentials / provider runtime | **closed** — injection live (secure store → engine spawn env only), engine-side redaction / child-env / test-command hygiene, leak suite 6/6, provider audit (`03`), credential doc (`04`); closure review **CONTINUE**; desktop tsc baseline recorded for G8 | `test_v15_credentials.py`, `03_PROVIDER_RUNTIME.md`, `04_CREDENTIAL_RUNTIME.md` |
| G5 routing / completion / review | **closed** — claims compiler (finalized contracts only; transient drafts stay clean), escalation-aware `routing_outcomes` (`job_kind`/`attempts`/`escalated`), routing + completion + reviewer-independence audits (`05`, `06`); closure review **CONTINUE** | `test_v15_completion.py`, `05_ROUTING.md`, `06_COMPLETION_AUTHORITY.md` |
| G6 memory / continuation / recipes | pending | — |
| G7 donor sunset / chat purity / UX | pending (includes the Autonomy page copy correction) | — |
| G8 diagnostics / performance / packaging | pending | — |
| G9 security + reliability sweeps | pending (a first slice of the security matrix is covered by `test_v15_authorize.py`) | — |
| G10 visual / product acceptance | pending | — |
| G11 migration / clean clone / packaged | pending | — |
| G12 independent architecture audit | pending | — |
| G13 freeze / tag / release | pending | — |

Gate closure rule applies: implementation + tests + runtime evidence + review `CONTINUE`; documents
alone never close a gate.

## Increments

**Increment 1 — committed as `b1f9aa5`:** the central authorization boundary + migration 010
`guardrail_decisions`; execution leases issued at job creation (contract-digest bound), enforced at
the engine claim gate, the coding effect point, change application, and service identity; boundary
expansion end-to-end (ask-once, once/project grants, denied-sticky, automatic resume).

**Increment 2 — G2 completion (this working tree):**

- source-traced effect-path inventory: `02A_EFFECT_PATH_MATRIX.md` (28 classified rows; method and
  classes documented);
- side doors closed: `/api/autonomy` lease issuance refused at the shell; greenfield project
  creation gated under `user-project-create`; lease/job, worker/milestone, and approval/job
  identity bindings enforced; unknown roles deny;
- G2 charter matrix 25/25 evidenced (`09_SECURITY_REVIEW.md`); restart/resume reauthorization and
  parallel-worker isolation proven;
- tests: `runtime/tests/test_v15_authorize.py` **43/43**; full suite **418 passed + 10 subtests**
  (375 + 10 baseline; zero regressions);
- documents `01`–`17` present plus `02A`; substantive: `02`, `02A`, `08`, `09`; working: `14`,
  `16`, this file; skeletons: the rest, each marked so.

**Increment 3 — G3 (this working tree):** frozen role snapshot attached to every run at claim (one
per milestone, reused across retries; coding → Implementation Engineer, research → Research
Specialist, text → Documentation Specialist); enforcement reads the snapshot; the coding dispatcher
gate covers `git` / `run_tests` / `write`; tests `test_v15_roles.py` **5/5**; full suite **423
passed + 10 subtests**; closure review **CONTINUE**.

**Increment 4 — G4 (this working tree):** provider credentials are injected from OS-backed storage
into the engine child environment only (desktop main process decrypts at spawn); engine-side
hygiene (`redact`, `child_env`, `test_command_env`); leak suite `test_v15_credentials.py` **6/6**;
provider audit (`03`) + credential runtime (`04`); Providers copy corrected with the claims test
re-pinned; full suite **429 passed + 10 subtests**; closure review **CONTINUE**. Found: desktop
`tsc --noEmit` has ~25 pre-existing errors (G8 item; none from G4).

**Increment 5 — G5 (this working tree):** explicit CompletionContract claims on finalized
contracts (`completion_claims`; transient drafts stay clean — proven by the scope tests and by a
first-attempt regression they caught), escalation-aware `routing_outcomes` (task class, attempts,
escalated), routing + completion + reviewer-independence audits (`05`, `06`); tests
`test_v15_completion.py` **5/5**; full suite **434 passed + 10 subtests**; closure review
**CONTINUE**.

## Required deliverables (spec checklist)

`00_STATUS` ✅ · `01_ARCHITECTURE` ◻ skeleton · `02_AUTHORIZATION_MODEL` ✅ ·
`02A_EFFECT_PATH_MATRIX` ✅ · `03_PROVIDER_RUNTIME` ✅ · `04_CREDENTIAL_RUNTIME` ✅ · `05_ROUTING` ◻
· `06_COMPLETION_AUTHORITY` ◻ · `07_MEMORY_AND_CONTEXT` ◻ · `08_LEDGER` ✅ working ·
`09_SECURITY_REVIEW` ✅ working (G2 matrix complete) · `10_RELIABILITY_REVIEW` ◻ ·
`11_DESIGN_SYSTEM` ◻ · `12_PERFORMANCE` ◻ · `13_MIGRATIONS` ◻ · `14_TEST_MATRIX` ✅ working ·
`15_RELEASE_MANIFEST` ◻ · `16_KNOWN_LIMITATIONS` ✅ working · `17_V2_PLUS_DEFERRED` ✅ ·
`AUTO_RESUME` ✅
