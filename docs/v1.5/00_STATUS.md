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
| G2 execution-path enforcement | **increment 1 landed** — engine claim gate, coding effect point, apply gate, service identity; remaining: V14-151/152 decision, revoked-mid-run runtime drills | `14_TEST_MATRIX.md` |
| G3 roles / leases / boundary | **partial** — leases + expansion end-to-end; roles enforced when assigned; automatic role attachment pending | `08_LEDGER.md` |
| G4 credentials / provider runtime | pending | — |
| G5 routing / completion / review | pending | — |
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

## Current increment (this working tree, committed as b1f9aa5)

- central authorization boundary in the execution path + migration 010 `guardrail_decisions`;
- execution leases issued at job creation (bound to the compiled contract digest), enforced at the
  engine claim gate, at the coding effect point, at change application, and for service identity;
- boundary expansion end-to-end: asked once per target, `once`/`project` grants, denied-sticky,
  automatic resume of the blocked job after a grant;
- tests: `runtime/tests/test_v15_authorize.py` **24/24**; full suite **399 passed + 10 subtests**
  (375 + 10 before the change; zero regressions);
- documents `01`–`17` present; substantive: `02`, `08`; working: this file, `09`, `14`, `16`;
  skeletons: the rest, each marked so.

## Required deliverables (spec checklist)

`00_STATUS` ✅ · `01_ARCHITECTURE` ◻ skeleton · `02_AUTHORIZATION_MODEL` ✅ · `03_PROVIDER_RUNTIME` ◻
· `04_CREDENTIAL_RUNTIME` ◻ · `05_ROUTING` ◻ · `06_COMPLETION_AUTHORITY` ◻ ·
`07_MEMORY_AND_CONTEXT` ◻ · `08_LEDGER` ✅ working · `09_SECURITY_REVIEW` ◻ working ·
`10_RELIABILITY_REVIEW` ◻ · `11_DESIGN_SYSTEM` ◻ · `12_PERFORMANCE` ◻ · `13_MIGRATIONS` ◻ ·
`14_TEST_MATRIX` ◻ working · `15_RELEASE_MANIFEST` ◻ · `16_KNOWN_LIMITATIONS` ✅ working ·
`17_V2_PLUS_DEFERRED` ✅ · `AUTO_RESUME` ✅
