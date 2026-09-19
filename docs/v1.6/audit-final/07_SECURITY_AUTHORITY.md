# 07 — SECURITY / AUTHORITY / ISOLATION

Audit target `08f56673…`. Sources: probes 1–4, code reads, suite re-run (998+10), packaged evidence review.

## Top-level results

- **AUD-MAJOR-001** — chat-approval resolution scoping is opt-in; an undeclared caller settles any conversation's approval (reproduced; engine route passes the field through; dormant `/api/approval` unscoped). Details in `MASTER_FINDINGS.md`.
- **AUD-MAJOR-002** — privileged IPC surface not uniform: credential trio / feedback pair / sendSync handlers / `backend:recover-corrupted-database` / the generic adapter dispatcher lack the sender-frame guard that 8 Kel channels enforce. Details in `MASTER_FINDINGS.md`.
- **AUD-MINOR-003 / 007 / 008 / 009** — credential-env gap, donor runtime shipped, pet subsystem wired, donor builder config is the default build path (+ parent-config inheritance in Kel builds).
- Everything else attacked in this area behaved as declared (below).

## Conversation / project scoping (attacked, results)

- **Memory (probe-2):** cross-conversation confirm/correct/forget/retract via the service route → refused (“Memory belongs to another project”); foreign proposal fetch/accept → refused; foreign conflict resolution → refused (with a real conflict row); unknown conversation → “Conversation missing”; omission defaults to the `main` conversation's project (fail-safe, read/write symmetric). Module-level provenance rules all enforced (web trust-7 ceiling, preference user-only, decision trust ceiling, inference confidence, secret scan).
- **Vetting (probe-4):** foreign-conversation ingest/process/finish with a valid hostile session id → refused (“belongs to another conversation”); unknown id → plain “Vetting session not found”; `panel(session_id=…)` remains a documented cross-conversation **display read** (corpus-disclosed; the single load-point `session()` gates every scoped action).
- **Transcription (probe-4):** declared-conversation mismatch refused for chunk/status/finish; undeclared callers keep the documented additive behavior; unknown stream → “has ended.”; reaped/finished streams release sockets (TR-01 re-verified).
- **Approvals:** declared-foreign refused (probe-1 A1/A5); window expiry, exact-action digest, job binding, duplicate resolution all refused/allowed correctly (probe-1 B + suite; negative control fails pre-fix).

## Authorization / authority

- Actor-identity guard: `service._action` refuses a payload-provided `actor` (APR-01) — present twice (`grep` count 2); covered by tests.
- `AUTH-DELEGATION` containment attacks (probe-1/3 §E): wider class / extra tool / scope escape / nested-without-delegator / cost-over-envelope → refused with exact sentences; path `..` normalization gap recorded (**AUD-MINOR-006**); budget cumulative accounting gap recorded (**AUD-MINOR-002**).
- Emergency stop / guardrails: exercised by the re-run suite (`test_v141_boundaries` family), including “only the user can trigger it” and caller-supplied-actor rejection.
- Engine listens on `127.0.0.1` with a per-run bearer token in `desktop-session.json` (`service.py:1014-1015`) — no LAN bind observed for the engine.

## Credentials

- Sentinel probes (probe-1 §G): `internal.child_env(keep=…)` strips non-keep provider keys; `redact()` masks live-looking secrets; native CLI children strip only the counterpart provider key → `DEEPSEEK_API_KEY` leaks into both `claude` and `codex` children (**AUD-MINOR-003**).
- Engine spawn injects only the Anthropic key into the engine child env (Kel-managed, main-process decrypted); the coding test command clears all three keys (suite).
- No value-returning credential IPC: `preload` exposes `status/set/remove` only; the engine receives metadata (`credential_ref`).

## IPC / desktop boundary

Coverage table (audited channels): `kel:conversation`, `kel:history-search`, `kel:history`, `kel:request` — guarded (senderFrame==mainFrame + URL); `kel:engine-state`, `kel:engine-retry`, `kel:diagnostics` — guarded via `guardKelWindow`; `kel:artifact-reveal` — guarded + path containment; `kel:credential-status/set/delete` — **unguarded**; `feedback:collect-logs`/`feedback:capture-screenshot` — **unguarded**; `get-backend-port`/`get-initial-language`/`get-backend-startup-*` + `backend:recover-corrupted-database` — **unguarded**; `ADAPTER_BRIDGE_EVENT_KEY` generic dispatcher → donor bridge methods (`app.update-cdp-config`, `app.clear-browser-data`, `app.set-start-on-boot`, `update.download`/`auto-update.quit-and-install`, `shell.openExternal`, WebUI lifecycle start/stop via `webuiBridge`, …) — **unguarded**. See AUD-MAJOR-002 for reachability discussion (subframes run the preload; artifact viewers render iframes/webviews).

## Native host / privacy

- `host_runtime.py` is recorded (and verified by reading) as user-authorized full-access native execution — **not** a sandbox; no surface claims otherwise. Network egress filtering remains post-V1.6 (disclosed).

## Secret hygiene of this audit

- All probes used synthetic sentinels (`AUDIT-SENTINEL-…`); no real credentials were read, printed, or stored. Engine evidence artifacts from Campaign A record presence-only.
