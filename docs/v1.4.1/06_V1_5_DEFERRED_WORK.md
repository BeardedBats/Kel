# 06 — V1.5 Deferred Work (explicit; nothing hidden)

Everything below is intentionally **not** in V1.4.1. The patch stayed surgical: findings were either
fixed in code, bounded by truthful documentation, or recorded here.

## Enforcement and authorization
1. **Full execution-path capability enforcement** — leases become a runtime gate: issue a lease for a
   job, require it at claim time, and check kind/scope at each effect point (file writes, repo ops,
   browser, tools, external actions). Today the checker is complete but nothing on the execution path
   calls it (`docs/v1.4-postrelease/02_SKELETON_MATRIX.md` Bone 19).
2. **Central authorization middleware** — one choke point that derives actor identity from trusted
   context (session handle bound at the shell), so every engine action family shares the same
   identity rule. V1.4.1 rejects payload-supplied identity at the two current decision points.
3. **Role tool-policy enforcement** — apply `role_versions.tool_policy` allow/deny lists to actual
   worker tool use (adapters), with denial receipts.
4. **`guardrail_decisions` table + receipts** — first-class decision records (rule id, actor, target,
   outcome) for incidents and receipts; today decisions land in `lease_events`/job events.
5. **Native-host containment** — decide between OS-level sandboxing (Windows sandbox/containers/VM)
   and the documented user-authorized model; the V1.4.1 model is documented in
   `02_RUNTIME_TRUST_BOUNDARY.md` §4. *Note: Codex sandbox modes on Windows are the blocker that
   kept D-02 at Option B in this patch.*

## Credentials
6. **Real credential injection** — consume `kelCredentials.getCredential` in the main process, pass
   the value per-run to the specific child (never persisted by the engine, never logged), with tests
   for the native and internal adapters and a packaged end-to-end check on top of
   `packaging/verify-credentials.cjs`.

## Product / identity (audit P3)
7. **Donor identity sunset** — tray tooltip `AionUi` (`tray.ts`), web-notification title `AionUi`
   (`useBrowserNotification.ts`), `[AionUi]` logs, donor copy, and donor pages still in the tree
   (cron/login/TestShowcase; settings tabs model/agent/skills/tools).
8. **Remaining 38 valid backlog rows** from the audit’s ledger triage
   (`docs/v1.4-postrelease/03_LEDGER_TRIAGE.md` VALID_POST_RELEASE_WORK): work-center/verification
   UX, provider/cost surfaces, memory/context surfaces, continuation displays, etc. (grouped in
   `docs/v1.4-postrelease/07_V1_5_BACKLOG.md`).

## Packaging / harness
9. **Release-folder hygiene** — stop carrying `debug.log`; hash manifests with filenames; cover the
   donor `aioncore.exe` in the sums; attest its provenance.
10. **Harness determinism** — deterministic pet-enable step (wait/retry/assert) and a close handshake
    so capture runs stop via the engine instead of the bounded kill.

## Docs / records
11. **Ledger advancement** — advance the 72 already-delivered rows with the citations in
    `docs/v1.4-postrelease/03_LEDGER_TRIAGE.md`.
12. **Historical-record maintenance** — fold V1.4.1’s corrected statements into any future edition of
    the V1.4 design documents instead of the post-release notes used here.
