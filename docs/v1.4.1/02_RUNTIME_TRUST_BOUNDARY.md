# 02 — Runtime Trust Boundary (V1.4.1)

This is the authoritative statement of what the Kel runtime can and cannot enforce after V1.4.1.
It complements, and supersedes where they disagree, the V1.4 design documents
(`docs/v1.4/KEL_V1.4_SECURITY_MODEL.md`, `KEL_V1.4_AUTONOMY_POLICY.md`, `KEL_V1.4_TEAM_MODEL.md`).

## 1. The layered model

```
User (the only principal)
  ↓ authenticated local session (loopback bearer token, per engine boot)
Commander / work engine            — trusted; owns contracts, verdicts, publishing
  ↓ durable brokers (one per run)  — trusted processes; own a run, commit one receipt
Worker adapters
  ├─ internal leaf worker          — untrusted content; 2-tool allowlist; no filesystem access
  ├─ native text slice (codex/claude exec) — untrusted; read-only flags; tools disabled; env scrubbed
  └─ coding native host (app-server/ACP)   — untrusted content with FULL USER OS RIGHTS
  ↓
Filesystem / shell / network       — the real boundary: Windows user privileges + snapshot topology
```

## 2. Layer table — what can actually block what

| Layer | Trust | What Kel can block today | Advisory only | Notes |
|---|---|---|---|---|
| User session (renderer → IPC → service) | Principal | Any request; actor identity is **not accepted from payloads** — `/api/autonomy` and `/api/approval` reject an `actor` field; the service supplies `user` from the authenticated session | — | Same-user local processes can read the loopback token file; that is inside the local trust model and is documented, not hidden |
| Commander / work engine | Trusted | Refuses **new worker runs** if the guardrail rule set was modified at runtime (`guardrails.assert_intact` in `Engine.tick`; surfaced as `guardrails_ok` in `/api/state`); refuses **engine-owned project writes** into frozen-release/system paths (`apply_changes.apply_checked` via `guardrails.protected_reason`); digest/evidence/approval gates unchanged | Budget/escalation policy beyond the above | Engine never hands its token to workers; leases remain a policy record (see §3) |
| Brokers (`runner.py`) | Trusted | Bounded retries, fencing (`ORPHANED`), stop via run state | — | Own exactly one run; no identity of their own |
| Internal leaf worker | Untrusted content | Tool allowlist (unknown tools denied — e.g. `spawn_agent` rejected), token/iteration/time budgets, 40k-char input cap | Prompt-level instructions | No filesystem, no network tools |
| Native text slice (`native.py`) | Untrusted content | `sandbox_mode=read-only`, tools disabled (`--tools ''` / feature disables), cross-provider keys scrubbed, output/time caps | CLI’s own behavior | Resume supported per provider |
| Coding native host (`host_runtime.py`) | Untrusted content, **full user rights** | **Nothing at OS level.** Codex runs with `sandbox_mode="danger-full-access"`, `approval_policy="never"` (the module docstring says “This runtime is not a sandbox”); Kel bounds it *topologically*: an isolated git snapshot per job, Kel-run tests, diff evidence, and a user-gated apply with conflict checks + backups | Worker instructions | This is the documented, deliberate high-privilege path; containment by lease/red-line policy does **not** apply to its own OS actions |
| Filesystem / shell / network | Real boundary | Windows user account limits; frozen/system write refusal only on Kel’s own engine paths | — | OS-level sandboxing is V2+ |

## 3. Minimal-enforcement decision (recorded)

**Question:** can the capability checker be safely inserted into a narrow real execution boundary in
V1.4.1?

**Decision — YES for two points, NO for the full boundary.**

- **Wired (small, fail-closed, test-covered):**
  1. `guardrails.assert_intact()` runs at the top of every `Engine.tick()`; on mismatch the engine
     records `tampered` and claims **no new runs** (recorded results still settle and publish).
     Tests: `test_v141_boundaries.py::GuardrailTamperTests` (including “work resumes after restore”).
  2. `apply_changes.apply_checked()` refuses any project root that resolves into a frozen-release
     marker or a system prefix (`guardrails.protected_reason`). This is the only engine path that
     writes into a user project. Test: `ProtectedPathTests` (denial proven end-to-end to the
     filesystem being untouched); the allow path is proven by the existing `test_apply_changes.py`.
- **Not wired (deferred to V1.5):** requiring a lease for execution, checking scope at effect points,
  enforcing role tool policies, and blocking red-line actions inside the native host. Rationale: this
  needs a lease lifecycle tied to jobs, effect-point enforcement in adapters, and (for the coding
  host) an OS-level sandbox — none of which is “obviously small”, and doing it partially would create
  new false claims. Until then, `capability_leases` is exactly what it says: a policy record + checker
  + UI, not a runtime gate.

## 4. Native host trust model (D-02, Option B)

- The coding host is a **user-authorized high-privilege runtime**. It executes Codex app-server with
  full access on this machine, inside a repository snapshot that Kel creates and never the user's
  checkout. Its OS actions cannot be intercepted by Kel in V1.4.1.
- What protects the user's real project: the snapshot topology (worker edits a copy), Kel-run tests
  and diff evidence (behavior + regression gates), and the explicit user apply, which is
  digest-bound, conflict-checked, backup-first, and now refuses frozen/system targets.
- What protects the machine: the user's own Windows account, the Windows job object (lifetime
  containment only — not a sandbox), and the documented red lines that the worker is instructed to
  follow but that the runtime does not enforce against it.
- This matches `test_host_runtime.py`, which explicitly asserts the full-access policy, and the
  corrected `SECURITY_MODEL` §6.

## 5. What the runtime can and cannot enforce (plain list)

**Can enforce (V1.4.1):** approval rows (digest-bound, user-session-only), completion authority,
evidence/digest gates, agent tamper refusal for new work, frozen/system refusal on engine-owned
project writes, provider auth/health gating, retry/circuit bounds, export sanitization, credential
custody (values never in engine/renderer/export).

**Cannot enforce (V1.4.1, deferred):** a lease being required to act; scope checks on worker actions;
role tool-policy denial against workers; red-line blocking inside the native coding host; OS-level
sandboxing; distinguishing other same-user local processes from the user session.
