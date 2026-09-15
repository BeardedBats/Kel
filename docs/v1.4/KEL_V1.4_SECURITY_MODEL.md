# KEL V1.4 — SECURITY MODEL

Status: v1 (2026-09-15) · Gate 2 design document. Companions: `KEL_V1.4_AUTONOMY_POLICY.md`,
`KEL_V1.4_PROVIDER_SPEC.md`.

Posture: local-first, single-user Windows desktop. Two hard problems: **secrets** and **untrusted
content** (repository text, web pages, worker output). Everything below is enforced in code and
covered by a test id.

## 1. Threat model → mitigation → test

| Threat | Mitigation | Test |
|---|---|---|
| Secret leaks into logs/prompts/Git/screenshots/memory/diagnostics | OS-backed store; values never persisted by the engine; sanitizers on every output path; memory secret-scan (existing patterns in `memory.scan_secret`) extended | SEC-NOLEAK |
| Credential enumeration (Credential Manager, browser stores, SSH keys) | credential API is namespaced `kel:*` and refuses enumeration; only Kel-owned entries are readable/writable | SEC-NOENUM |
| Renderer exposure of keys | keys never cross IPC into the renderer; only state booleans/`credential_ref` metadata | SEC-RENDERER |
| Env leakage to grandchildren | per-run env injection to the specific child; descendants scrubbed (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` removal already implemented) | SEC-ENVSCRUB |
| Prompt injection (repo/web/worker text) | text is data, never authorization; guardrails locked above all instructions; evidence classes + provenance labelling; fence sanitizer on model output | SEC-INJECT |
| Tool abuse by a worker | per-role tool policy checked at claim **and** at effect time; denied tools fail closed | SEC-TOOLPOLICY |
| Path escape (symlink/junction/traversal) | resolve + containment checks on every write (pattern proven in `context.attach`: `resolve()` + `is_relative_to`) | SEC-PATH |
| Lease escalation | leases immutable after issue; grants only via boundary-expansion approval; every action checked | SEC-LEASE |
| Approval bypass | approvals are rows with digests; resolving requires the exact action; no code path executes a gated action without an APPROVED row | SEC-APPROVAL |
| Frozen-release tampering | frozen paths read-only by policy; release hashes re-verified at G10 | SEC-FROZEN |
| Unrelated personal data | task-scoped search only; refusals recorded | SEC-PRIVATE |
| Supply chain (deps/donors) | pinned revisions, licence checks, attribution, AGPL excluded, integrity records in the asar pipeline | SEC-SUPPLY |
| Update integrity | updater unchanged from the donor; diagnostics file is local; no unsigned remote installs | SEC-UPDATE |

## 2. Trust precedence (never inverted)

user decision > **locked guardrails** > reviewed plan + capability lease > role instructions >
project/repository content > external web content > worker output. No scheme, file, page, or model may
treat lower levels as authority; guardrail decisions are recorded with rule ids.

## 3. Credentials (final design)

- **Custody:** the shell main process stores values in the OS-backed store (Windows DPAPI /
  Credential Manager), namespaced `kel:provider:<providerId>:<field>`. The engine stores metadata
  only: `provider`, `fields[]`, `credential_ref`, `updated_at`.
- **Use:** at run time the engine receives the value as an environment variable for that single child
  process; grandchildren are scrubbed; values are never written to disk by the engine, never logged,
  never included in prompts or receipts.
- **Lifecycle:** test · store · replace · delete for Kel-owned entries; deleting a provider removes its
  namespaced entries; rotation guidance shown in Providers settings.
- **Prohibited:** reading unrelated entries, exporting, printing, copying, or including values in
  screenshots/diagnostics/memory/Git — each refused and recorded.

## 4. Data protection

- Store lives in the user data dir (`KEL_DATA_DIR`), SQLite with WAL + `synchronous=FULL`; backups and
  migration receipts before any schema change (existing discipline in `migration.py`).
- Attachments: bounded (≤5 MB), digest-verified on read, non-image content must decode as UTF-8
  (existing `context.attach` behaviour).
- **Retention:** `retention_settings` (conversations, events, diagnostics, provider observations)
  with export-then-purge; purge never touches frozen releases or the active lease/approval rows.
- **Logging:** structured and local; secret-shaped strings are refused at write time; log files are
  deleted with retention.

## 5. Diagnostics sanitizer (export rules)

Include: versions/build, health states, startup spans, provider observations (no keys), process
ownership, job/assignment summaries, counts, sanitized error strings.
Exclude: raw prompts, full transcripts of unrelated conversations, personal files, cookies/auth
files, environment dumps, API keys/tokens, private-key material, screenshots of unrelated windows.
The export is generated from an allowlist, not by filtering a dump; the receipt lists what was
included and excluded.

## 6. Process and OS safety

Single-owner enforcement (`instance_lock` + controller lease); worker processes contained via
`windows_job`; task-owned processes are terminated on completion and checked by the orphan detector
(zero-orphan requirement at G10). No registry writes, no active-screen control, no OS-critical
changes, no covert persistence — enforced by the locked guardrail module and verified by tests.

## 7. Supply chain and release integrity

Donor code: pinned revision + licence verified + attribution in `THIRD_PARTY_NOTICES.md`; AGPL and
unknown-licence code excluded; `packaging/verify_engine_pyz.py` proves module-level structural
equality; `asar-inspect.js` keeps per-file SHA-256 integrity records and explains deltas. Releases are
hash-sealed; frozen folders are immutable; candidate packages are built into isolated directories.

## 8. Incident handling

Revoke leases → pause runs → rotate Kel-owned credentials → export sanitized diagnostics → record a
guardrail decision entry. Issue-report drafts are local Markdown with the sanitizer applied and never
auto-posted unless the task explicitly authorizes it.

## 9. Tests (SEC-*)

SEC-NOLEAK · SEC-NOENUM · SEC-RENDERER · SEC-ENVSCRUB · SEC-INJECT · SEC-TOOLPOLICY · SEC-PATH ·
SEC-LEASE · SEC-APPROVAL · SEC-FROZEN · SEC-PRIVATE · SEC-SUPPLY · SEC-UPDATE · SEC-RETENTION ·
SEC-SANITIZER · SEC-BACKUP-RESTORE.
