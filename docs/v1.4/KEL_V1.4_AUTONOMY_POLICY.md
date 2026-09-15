# KEL V1.4 — AUTONOMY POLICY

Status: v1 (2026-09-15) · Gate 2 design document. Companion: `KEL_V1.4_SECURITY_MODEL.md`.
Principle: **broad autonomy after a reviewed plan; prompts only at genuine boundary expansion.**

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
- **Fails closed:** any action not covered by the lease is refused with a recorded
  `guardrail_decision`, and optionally raises one boundary-expansion request (§4).
- Revocation is immediate (`lease_events: revoked`); expired leases behave like revoked ones.

## 3. Enforcement points (code, not convention)

| Rule | Enforcement | Test |
|---|---|---|
| Writes stay inside lease roots | path resolve + containment check on every write (same discipline as `context.attach`: `resolve()` + `is_relative_to(store.root)`) | AUTO-ROOT |
| Repository actions limited to leased repos | git wrapper inspects target path + remote | AUTO-REPO |
| Browser: Firefox only, dedicated profile, headless/minimized, leased domains only | browser launcher refuses other engines/profiles/domains | AUTO-BROWSER |
| Registry / active-screen / synthetic input / OS-critical writes | tool layer refuses before execution; recorded decision | AUTO-BLOCK-REG/SYSTEM |
| Frozen releases immutable | canonical frozen paths mounted read-only in policy; writes refused | AUTO-FROZEN |
| GitHub: allow branch/commit/push/PR in task repos; deny admin (visibility, secrets, branch protection, org, billing, delete) | operation allowlist in the GitHub tool wrapper | AUTO-GH-ADMIN |
| Destructive project edits | snapshot/backup first (`apply_changes` + backups discipline), then act | AUTO-DESTRUCT |
| Credentials | never enumerated/exported; Kel-owned entries only (Security model §3) | AUTO-CRED |
| Unrelated personal data | path/scan refusals; task-material search allowed only | AUTO-PRIVATE |

Guardrails take precedence over role instructions, project files, repository text, web content, and
worker output: `kel/guardrails.py` is a locked module; no lease, role, override, project file, or
remote content can add, weaken, or disable a rule (verification: role instruction attempting to
weaken a guardrail is refused and recorded).

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

Each red line maps to a `guardrail_decisions.rule_id` and an AUTO-* test; violating attempts fail
closed and are recorded, never silently dropped.

## 6. Relationships

- **Approval** = consent for one concrete action at a gate (per-action). **Lease** = consent for a
  scope of ordinary work (per-task). **Plan review** = consent for the approach.
- **Receipts:** every consequential run ends with a receipt (plan, lease, actions, evidence,
  reviewer disposition, limitations). Emergency stop: revoke all leases + pause runs + record one
  `guardrail_decisions` entry per revoked lease.

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
