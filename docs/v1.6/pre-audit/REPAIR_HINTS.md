# REPAIR_HINTS — navigation clues for Campaign C

updated: 2026-09-18T16:05Z
rule: navigation, not prescription. Do not invent fixes; verify against evidence first. Each hint
names where the defect (if confirmed) most likely lives and how to validate a repair.

| Candidate | Likely files | Likely symbols | Related tests | Validation | Expected invariant |
|---|---|---|---|---|---|
| SEC-01 vetting ownership | `runtime/kel/vetting_session.py`, `runtime/kel/acp_host.py` | `Vetting.session()`, the 8 session-addressed entrypoints (`ingest`, `process`, `finish`, `preview`, `help`, `conflict_action`, `greybox`, `apply_pending`) | vetting suite; add cross-scope regression | Route each action through a conversation-scoped lookup OR compare `session['project_id']` vs `_project_of(data['conversation'])` (mirror `_memory_action`); acceptance criteria recorded in audit `16_FINDING_STATUS.md` | INV-MEM-001 |
| APR-01 approvals actor | `runtime/kel/chat_approvals.py`, `runtime/kel/service.py` | `/api/approvals` handler | approvals journey (packaged), add payload-actor rejection test | Assert `'actor' in data` rejection matches sibling endpoints; fix comment-vs-code drift | INV-APPROVE-001 |
| APR-02 resolution scope | `runtime/kel/chat_approvals.py` | resolution lookup | add conversation-scope regression | Make resolution conversation-scoped like the read | INV-APPROVE-001 |
| APR-03 restart queue | `runtime/kel/chat_approvals.py` (~line 95) | `_memory_check_queue` instance state | add restart test | Persist or rebuild the queue on restart; assert no lost checks | INV-MEM-001 |
| APR-04 DDL duplication | `runtime/kel/chat_approvals.py`, `runtime/kel/autonomy.py` (`approval_announcements`) | DDL blocks | schema tests | De-duplicate DDL; decide versioned vs core-schema treatment (like `artifact_lineage`) | INV-DATA-001 (append-only) |
| PER-02 silent restore | `runtime/kel/service.py` (apply_pending_restore call site), `runtime/kel/backup.py` | `apply_pending_restore`, startup try/except | backup-probe.py; add failure injection | Surface failure to the app state; never swallow | INV-ERROR-001 |
| PER-03 snapshot growth | `runtime/kel/backup.py` | `.pre-restore-*` creation | backup probe | Retention/pruning; move snapshot out of the restore try (failure of snapshot must not abort restore silently) | INV-ERROR-001 |
| PER-04 KEL_DATA_DIR creds | `runtime/kel/backup.py`, desktop `kelCredentials.ts`, `KelService.ts` `dataRoot()` | backup root selection | targeted test with KEL_DATA_DIR set | Exclude credentials when data dir is overridden | security |
| A1 engine version reuse | `desktop/.../process/services/kel/KelService.ts:43-52` | descriptor read/reuse path | boot tests | Validate `descriptor.engine_version` before reuse; else respawn | INV-PACKAGE-001 |
| REL-01 freeze staging | `scripts/freeze-release.ps1` | engine staging block | freeze tooling test | Make staging match the load path or remove it; verify manifest hashes cover what loads | INV-FREEZE-001 |
| INT-01 sender frame | `desktop/.../KelService.ts` | `kel:artifact-reveal` handler | enumerate channels | Add the same senderFrame check as sibling channels | INV-IPC-001 |
| COR-03 model control errors | `KelModelControl.tsx` | `setConversation` | renderer unit tests | Add error path (visible failure, no silent keep) | INV-ERROR-001 |
| COR-04 / MDL-01 prefs scope | `runtime/kel/model_prefs.py` | `set_conversation` | model prefs tests | Validate conversation existence + scope | INV-MEM-001 |
| COR-05 search exceptions | `runtime/kel/search.py` | per-section `except` | search tests | Narrow the bare except; report degraded sections | INV-ERROR-001 |
| COR-06 / ERR-01 dispatch leak | `runtime/kel/service.py` | vetting/transcription dispatch | dispatch tests | KeyError → typed error → translated message | INV-ERROR-001 |
| DEAD-05 privates | `runtime/kel/service.py` (`_vetting_route`), `vetting_session.py` | `_questions`, `_format_resurface` | routing tests | Promote to public API or wrap | maintainability |
| DEAD-06 unwired harness | `packaging/ux-audit.cjs` | — | — | Either wire into a package.json/script or relocate to evidence tooling | maintainability |
| THM-01 theme deletion | `applyTheme.ts` | overrides map | theme tests | Prune overrides on theme deletion | INV-UI-clean |
| TR-01 stream lifecycle | `runtime/kel/transcription.py` | `_STREAMS` | add shutdown/cleanup test | Cleanup on shutdown; bounded sessions | lifecycle |
| TR-02 abandoned-stream UX | `renderer/.../kel/transcription/index.tsx` | stream UI state | renderer tests | Honest abandoned state; no silent stale stream | UX truth |
| CAP2-LONGTEXT | `runtime/kel/capabilities.py` | `directive_clauses` (>2000 char early return) | long-paste test | Consider feedback path; keep fail-safe | INV-CAP-001 |
| SEC-01-multipart | `runtime/kel/transcription.py` | `_multipart` header interpolation | add escaping test | Escape/validate filename | security |
| Engine-loss surfaces | renderer error paths, `KelService.ts`, engine supervision | fetch error translation chain | probe b reproduction | User-facing failure + recovery; no raw infra text | INV-UI-001 / RISK-001 |
| Visual integration conflicts | merge between `ux/v16-visual-fix` and `ux/v15-journeys` | `ConversationRow`, settings shell, `KelService.ts`-adjacent | visual probes a/b/c re-run | Record every resolution; re-run automated suite + probes | INV-VISUAL-001 |

## Source pointers

- Findings detail: `kel-v16-code-audit/docs/code-audit/` records `11`, `13`, `16`, `17`, `19`
  and per-increment audits `21`–`37`.
- Acceptance criteria for SEC-01: `16_FINDING_STATUS.md` (quoted above).
- A1/PER-02 overlap analysis: `15_RUST_LEAD_VERIFICATION.md`.
