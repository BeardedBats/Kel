# 04 — Security Claim Audit (V1.4.1)

Method: repository-wide sweep for the brief’s term list — `enforced`, `containment`/`contained`,
`red line`/`red-line`, `guardrail`, `capability lease`, `permission`, `sandbox`, `isolation`,
`emergency stop`, `secure credential`, `credential injection`, `provider credentials`, `approval`,
`autonomous safety` — across `docs/v1.4/`, `docs/v1.4.1/`, `docs/v1-postrelease/`, `README.md`,
release notes/manifests, Settings/autonomy/providers/diagnostics UI copy, and packaging scripts; then
each hit was compared against runtime behavior and either corrected, annotated, or recorded as
accurate/historical. The result is also enforced by tests (`test_v141_claims.py`).

## Corrected claims (before → after)

| File | V1.4 claim | V1.4.1 statement |
|---|---|---|
| `SECURITY_MODEL.md` intro | “Everything below is enforced in code and covered by a test id” | “Statements below are marked with what is enforced today… authoritative boundary doc” |
| `SECURITY_MODEL.md` §1 tool-abuse row | “per-role tool policy checked at claim **and** at effect time; denied tools fail closed” | “role tool policy exists as data… not yet implemented (V1.5)” |
| `SECURITY_MODEL.md` §1 lease row | “every action checked” | “not yet called on the execution path; V1.4.1 = tamper detection + protected-path denial” |
| `SECURITY_MODEL.md` §1 approval row | “no code path executes a gated action without an APPROVED row” | exact mechanics: digest-bound user-session approvals; `/api/apply` is user-initiated on VERIFIED evidence + backups |
| `SECURITY_MODEL.md` §1 frozen row | “frozen paths read-only by policy” | engine-owned writes refuse frozen/system (V1.4.1); worker writes not intercepted |
| `SECURITY_MODEL.md` §3 Use | “engine receives the value as an environment variable…” | “status V1.4.1: not implemented”; live calls via CLI sign-in/ambient keys; injection deferred |
| `SECURITY_MODEL.md` §6 | “contained via windows_job… enforced by the locked guardrail module and verified by tests” | lifetime containment only; host = full access, not sandboxed; red lines are policy+checker, not enforced against native workers; V1.4.1 increments named |
| `SECURITY_MODEL.md` §9 | test-id list implies enforcement proofs | status note: checker/custody/sanitizer proofs, not execution-path proofs |
| `AUTONOMY_POLICY.md` header/§2/§3/§5/§6/§8 | draft-closed language (“tool layer refuses before execution”, `guardrail_decisions` rule ids, “fails closed”) | implementation-status banner; checker-level phrasing; `guardrail_decisions` marked not implemented; emergency stop exact scope; AUTO-* marked checker-level |
| `ARCHITECTURE.md` §2 + G6 | invented table names; “lease engine + enforcement” | actual schema names; “policy checker (execution-path enforcement deferred…)” |
| `TEAM_MODEL.md` §4 | “checked at claim and at effect time… fails closed”; recursion “hard engine check” | policy is data, not worker-enforced; recursion ban is structural (tool denial + CLI feature disables + run cap), no separate engine check |
| `TEST_MATRIX.md` | G2-AUTONOMY “enforcement mapped to AUTO-* tests”; G3-TEAM “tool policy fails closed” | V1.4.1 note: checker-level; wording corrected |
| `STATUS.md` / `RELEASE_MANIFEST.md` / `FEATURE_LEDGER.md` | historical records | post-release notes added; content otherwise preserved (no history rewriting) |
| Autonomy page (UI) | “The same check Kel performs before every action”; “engine refuses to run if they change”; “Enforced by” column | checker status + deferral; tamper behavior exact; “Covered by test” column; emergency-stop scope note |
| Providers page (UI) | implied stored credentials feed runs | “Stored values are not yet injected into provider runs…” |
| `kelCredentials.ts` | getCredential “used when a run needs the value injected” | “reserved for the V1.5 injection path; no caller in V1.4.1” |

## Reviewed, intentionally unchanged

- **Screenshot text dumps** (`docs/v1.4/screenshots/**-texts.jsonl`) — immutable evidence of what the UI
  said at capture time; not current claims.
- **`INTERACTION_PATTERNS.md` / `ACCESSIBILITY_STANDARD.md`** — design vocabulary (“Blocked by
  guardrail” state label, lock-glyph semantics for edit-locking); these describe UI states that still
  exist and are not enforcement claims.
- **`FEATURE_LEDGER.md` row statuses** — release-time record; covered by the added note.
- **`README.md`** — swept; contains no security/enforcement claims (only build/verify instructions).
- **Donor copy** (`ChannelConflictWarning.tsx` etc.) — donor-identity issue (V1.5, `06`), not a
  security claim.
- **`PROVIDER_SPEC.md` / `ADVERSARIAL_REVIEW.md` / `UX_SPEC.md`** — swept; no execution-path
  enforcement statements found beyond those already covered.

## Statements that must never return (pinned by `test_v141_claims.py`)

- “Everything below is enforced in code and covered by a test id”
- “no code path executes a gated action without an APPROVED row”
- “enforced by the locked guardrail module and verified by tests”
- “at run time the engine receives the value as an environment variable”
- “per-role tool policy checked at claim **and** at effect time”
- “tool layer refuses before execution”
- “a hard engine check”
- “lease engine + enforcement”

## What is still not claimed anywhere after V1.4.1

- That capability leases are required for, or block, worker execution.
- That role tool policies are enforced against workers.
- That red lines are enforced inside the native coding host.
- That stored credentials drive live provider calls.
- That `guardrail_decisions` rows exist.
- That the coding host is sandboxed.
