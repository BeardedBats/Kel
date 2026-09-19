# 12 — TRANSCRIPTION / VETTING

Audit target `08f56673…`. Sources: probe-4 (`evidence/auditor-probe-4-vetting-transcription.log`), code reads, suite re-run.

## Vetting — executed attacks (service layer)

- Started a session in conversation **c1** (session id captured).
- From conversation **c2** with c1's valid session id: `ingest` / `process` / `finish` → **REFUSED** ("That vetting session belongs to another conversation"). PASS (SEC-01 holds through the service layer).
- Unknown session id → "Vetting session not found" (plain sentence). PASS.
- Missing session field → "Open a design-vetting session first." (plain sentence). PASS.
- Same-conversation `process` works (control). PASS.
- **`panel(session_id=foreign)` returns the foreign session's display data** — this is the corpus-documented "marked cross-conversation display surface" (CHG-012/P2_P3 note; the single load-point `session()` gates every scoped action). Recorded; not a new finding, but flagged for Campaign C’s isolation review.
- Omitted conversation defaults to `main` (fail-safe), consistent with the memory battery.

## Transcription — executed attacks (module + service)

- **TR-01 lifecycle re-verified independently:** a reaped over-age stream is closed exactly once and removed; a fresh stream is untouched; `stream_finish` closes the handle AND removes the entry; unknown session → "That recording session has ended."; declared-conversation mismatch refused for chunk/status/finish while undeclared callers keep the documented additive behavior. PASS.
- Service actions: `library` ok; unknown action plain sentence; `status` reports fixture mode without a key ("Practice mode") and switches with `set_key` (suite: mode/state test).
- Library/record/upload/rename/copy/combine/export paths are covered by the (re-run, green) `test_transcription.py` suite — 31+ tests including plain-copy errors for unreadable/unsupported/long audio and export-without-audio.
- API key workflow: `set_key`/`clear_key` on the store; no getter; engine receives only presence (suite + code).
- TR-02 (abandoned-stream presentation): backend semantics need no correction (documented); the renderer honest-failure path lives in `engineFailure.ts` + R10 evidence (reviewed in 14) — no raw transport text on Kel surfaces (unit-pinned; packaged DOM leak scans clean).

**Exit status: PASS for scoped behavior; one documented display-read surface recorded.**
