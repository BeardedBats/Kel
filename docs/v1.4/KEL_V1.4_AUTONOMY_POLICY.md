# KEL V1.4 — AUTONOMY POLICY

Status: v1 (2026-09-15) · Gate 2 design document. Companion: `KEL_V1.4_SECURITY_MODEL.md`.
Principle: **broad autonomy after a reviewed plan; prompts only at genuine boundary expansion.**

> **Implementation status (V1.4.1):** the lease/scope checker (`autonomy.py`) and this surface are
> implemented and tested at checker level. Execution-path enforcement (a lease being required to act,
> and red lines blocking worker actions) is **not yet wired** — see
> `docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md` §3 and `06_V1_5_DEFERRED_WORK.md`. The V1.4.1 runtime
> increments are tamper detection (new work refused) and engine-owned write refusal for frozen/system
> paths.

## 1. The gate is the plan, not the action

Once a consequential plan passes the Best Solution Gate and the user approves it (explicitly, or by
the approved-plan rule in the brief), ordinary work inside the resulting lease proceeds without
per-action prompts: reading/creating/editing/moving/deleting files **inside task scope**, running
tests/linters/builds, installing project dependencies, starting/stopping task-owned processes,
additive migrations after backup, and — inside task repos — commit, rebase, fetch/pull, push a branch,
open/update a PR. Every such action is recorded; correctness is carried by leases, snapshots, git
history, and evidence — not by prompts.

## 2. Capability lease (the unit of scope)

`capability_leases(id, job_id, project_id, profile, issued_by, review_ref, expires_at, state)` with
child rows `lease_roots`, `lease_repositories`, `lease_domains`, `lease_tools`,
`lease_external_actions`, and an append-only `lease_events` stream.

- Issued only after a reviewed/approved plan; `review_ref` points at the Solution Brief + reviewer
  disposition. A lease is scoped to one job/project and has an explicit expiry.
- **Fails closed (checker level; not yet called on the execution path):** any action not covered by
  the lease is refused and recorded in `lease_events`, and optionally raises one boundary-expansion
  request (§4). A separate `guardrail_decisions` table is not implemented (V1.5).
- Revocation is immediate (`lease_events: revoked`); expired leases behave like revoked ones.

## 3. Enforcement points (code, not convention)

| Rule | Checker behavior (see status below) | Test |
|---|---|---|
| Writes stay inside lease roots | path resolve + containment check on every write (same discipline as `context.attach`: `resolve()` + `is_relative_to(store.root)`) | AUTO-ROOT |
| Repository actions limited to leased repos | git wrapper inspects target path + remote | AUTO-REPO |
| Browser: Firefox only, dedicated profile, headless/minimized, leased domains only | browser launcher refuses other engines/profiles/domains | AUTO-BROWSER |
| Registry / active-screen / synthetic input / OS-critical writes | the policy checker refuses these action kinds; recorded decision (checker level — see status below) | AUTO-BLOCK-REG/SYSTEM |
| Frozen releases immutable | the checker refuses frozen paths; engine-owned writes refuse frozen/system targets (V1.4.1); canonical read-only mounting is not implemented | AUTO-FROZEN |
| GitHub: allow branch/commit/push/PR in task repos; deny admin (visibility, secrets, branch protection, org, billing, delete) | operation allowlist in the GitHub tool wrapper | AUTO-GH-ADMIN |
| Destructive project edits | checker refuses destructive kinds without a snapshot reference; the apply path is backup-first (`apply_changes` discipline) | AUTO-DESTRUCT |
| Credentials | never enumerated/exported; Kel-owned entries only (Security model §3) | AUTO-CRED |
| Unrelated personal data | path/scan refusals; task-material search allowed only | AUTO-PRIVATE |

Guardrails take precedence over role instructions, project files, repository text, web content, and
worker output: `kel/guardrails.py` is a locked module; no lease, role, override, project file, or
remote content can add, weaken, or disable a rule (verification: role instruction attempting to
weaken a guardrail is refused and recorded).

**V1.4.1 enforcement status:** every row in the table above is implemented inside `Autonomy.check`
and exercised by its AUTO-* test, but **none of them is yet invoked on the execution path**. What the
runtime actually enforces today: (1) runtime modification of the rule set is detected and stops new
work (`guardrails.assert_intact`); (2) engine-owned project writes refuse frozen-release and system
paths (`guardrails.protected_reason`). Everything else in this table is policy plus checker.

## 4. Boundary expansion (ask once)

When work genuinely needs more scope, Kel raises ONE request containing: what is needed, why, the
expected benefit, the fallback if denied, and the risk. Presented in plain language in the Approval
Inbox. Options: **Allow once** · **Allow for this project** (until revoked/expiry) · **Deny**.
A grant becomes a lease event; while it is valid, Kel does not ask again for that scope. Approvals are
independent of runs for continuation (existing `approvals` table). Expiry and revoke are first-class.

## 5. Red lines (never autonomous)

Windows Registry writes · active-screen takeover / synthetic desktop input / focus stealing · changes
to Windows, boot, partitions, firmware, drivers, BitLocker · security weakening (Defender, UAC,
firewall, SmartScreen, TLS validation, VPN/proxy/DNS/hosts) · credential enumeration/exfiltration ·
identity or account-security changes · covert persistence (services, scheduled tasks, startup,
recorders) · destructive machine ops (format, wipe, shutdown/restart/logoff) · modifying frozen
releases · GitHub administrative actions · unrelated personal-data access · purchases, subscriptions,
or external communications not in task scope · self-modification of this policy.

Each red line maps to an AUTO-* test id that exercises its checker rule; violating attempts fail
closed **when checked**, and are recorded in `lease_events`, never silently dropped. Recording to a
distinct `guardrail_decisions` table is not implemented (V1.5).

## 6. Relationships

- **Approval** = consent for one concrete action at a gate (per-action). **Lease** = consent for a
  scope of ordinary work (per-task). **Plan review** = consent for the approach.
- **Receipts:** every consequential run ends with a receipt (plan, lease, actions, evidence,
  reviewer disposition, limitations). **Emergency stop (V1.4.1):** revokes every active lease **and
  pauses all active or queued jobs** (runs are marked CANCEL_REQUESTED so brokers/adapters stop
  workers at the next cancellation check; pending approvals for those jobs are cancelled; pending
  boundary requests remain pending but their leases are revoked). It does not terminate
  uncooperative OS processes and does not undo completed effects. Decisions are recorded in
  `lease_events` and job events (`guardrail_decisions` rows are V1.5).

## 7. What is never prompt-free

Administrator elevation · system-wide installs or PATH/env changes · public releases not in scope ·
history rewriting · deleting branches/tags/releases · sending external messages · creating paid
resources · working outside all declared project roots · irreversible actions without rollback.
These ask once for the capability, not once per command.

## 8. Tests (AUTO-*)

AUTO-ROOT · AUTO-REPO · AUTO-BROWSER · AUTO-BLOCK-REG · AUTO-BLOCK-SYSTEM · AUTO-FROZEN ·
AUTO-GH-ADMIN · AUTO-GH-ALLOW (elevated-verb denial + allowed verbs in-lease) · AUTO-DESTRUCT ·
AUTO-CRED · AUTO-PRIVATE · AUTO-LEASE-EXPIRY · AUTO-ASK-ONCE · AUTO-GUARDRAIL-IMMUTABLE ·
AUTO-EMERGENCY-STOP · AUTO-NO-PROMPT-AFTER-REVIEW (edit/test/install/commit/branch-push succeed
without prompts inside the lease).

Status (V1.4.1): the AUTO-* tests call the checker directly; they are checker-level proofs. The
execution-path integration remains V1.5 work (`docs/v1.4.1/06_V1_5_DEFERRED_WORK.md`).
