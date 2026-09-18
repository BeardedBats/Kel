# INVARIANT_LEDGER — cross-cutting invariants for independent challenge

updated: 2026-09-18T16:05Z
rule: every invariant carries definition, owner, code paths, tests, known edge cases, and an audit
target. Campaign B must explicitly attempt every "Audit target" line.

Status legend: DELIVERED (claimed and covered by tests) · PARTIAL (delivered with an open gap) ·
OPEN_GAP (known open finding attacks it).

---

## INV-AUDIT-001 — Builder cannot independently final-certify production output
- Definition: the thread that writes production code never counts as its own independent reviewer;
  independence is produced only by a separate fresh-context reviewer with its own record.
- Owner: program process (AUTONOMOUS_OPERATION.md; review-relay protocol).
- Code paths: `kel-v16-code-audit` worktree (read-only w.r.t. production); review-relay records.
- Tests: n/a (process invariant). Evidence: every audit record states no production writes.
- Edge cases: **Campaign A intentionally suspends independent audit** — all Campaign A
  verification is parent-executed or self-review; independence arrives only in Campaign B. The
  corpus must never present Campaign A evidence as "independent".
- Audit target: verify no acceptance claim in this corpus was minted by the code author alone;
  verify the last independent verdict (`8a2b25d`, increment 24) exists and is authentic.
- Status: DELIVERED (process), suspended-by-design during Campaign A.

## INV-FREEZE-001 — Frozen releases remain byte-identical
- Definition: frozen release artifacts (`Kel-V1.6.0-Pre1-Frozen`, older V1–V1.5 folders, tags
  `v1.6.0-pre1` @ `f24d9c2`, `v1.5.0` @ `5e76b21`) are never modified, moved, re-tagged, or
  force-updated; a correction is a new tag.
- Owner: release process (GITHUB_SYNC_POLICY.md §5).
- Code paths: `scripts/freeze-release.ps1` (4-hash manifest), `ux-audit/verify-prior-frozen.ps1`.
- Tests: re-verification runs (last: 2026-09-17, 4/4 hashes OK).
- Edge cases: freeze tooling nests an inert runtime duplicate
  (`resources/kel-engine/kel-engine/`) — pre1 removed it after assembly; `REL-01` (P2, open):
  freeze engine staging is a no-op for the load path the app + manifest hash.
- Audit target: re-hash the frozen folders + remote tags; confirm `main` and tags byte-equal.
- Status: DELIVERED; REL-01 open on the tooling gap.

## INV-CAP-001 — Ordinary prose never mutates capability state; forwarding stays byte-identical
- Definition: capability state changes only via standalone human-friendly commands or the reserved
  `[kel:<capability>=<state>]` namespace (canonical names/states only). Anything else — quotes,
  code, URLs, nested brackets, malformed tokens, prose — is forwarded byte-identical and mutates
  nothing.
- Owner: capabilities subsystem (`runtime/kel/capabilities.py`, `acp_host.py`, `research.py`).
- Tests: `test_capabilities.py` ORDINARY_PROSE corpus + reserved boundary corpus + a negative
  control executing the pre-fix parser from git; `test_acp_host.py` end-to-end cases A–G.
- Edge cases: messages >2000 chars silently ignore directives (CAP2-LONGTEXT P3, fails safe);
  repeated directives last-write-wins; exact-removal rules (one adjacent separator max).
- Audit target: new prose attacks (mixed quotes/fences/tables), long-paste behavior, unicode
  confusables in the reserved namespace.
- Status: DELIVERED (CAP-01/02/03 + CAP2-CLAUSE + CAP2-RESIDUAL closed through `631881a`).

## INV-CAP-002 — Capability decisions fail closed
- Definition: an unknown/unresolvable tool probe reads unavailable and `resolve()` denies; no
  silent-open fallback.
- Owner: `capabilities.py` (`availability` explicit fail-closed branch).
- Tests: `test_unknown_probe_fails_closed_not_open` (synthetic unknown probe).
- Audit target: enumerate every probe id in production; confirm each resolves closed.
- Status: DELIVERED (DEAD-08 closure).

## INV-APPROVE-001 — Approval resolution only through canonical resolvers
- Definition: chat/UI approval resolution always delegates to `Autonomy.resolve_expansion` /
  `Store.resolve_approval`; expiry, one-shot and scope semantics cannot be bypassed.
- Owner: approvals subsystem (`chat_approvals.py`, `autonomy.py`, `service.py` `/api/approvals`).
- Tests: `test_v14_autonomy.py`; packaged approvals journey (`run-approvals.sh` on final16).
- Edge cases: **APR-01** (P2) payload-actor rejection implicit + comment claims a guard that is
  absent; **APR-02/APR-03** (P2) unscoped resolvers addressed by bare id (shared root cause with
  SEC-01).
- Audit target: attempt resolved-without-announcement, cross-conversation resolution, replay, and
  expired-anchor resolution.
- Status: PARTIAL (open APR-01..03).

## INV-LEASE-001 — Lease release is exact-once on every exit path
- Definition: parallel-mission stream leases release exactly once on success, failure, refusal and
  interruption; a release failure never masks the primary causal error.
- Owner: parallel missions (`runtime/kel/parallel.py`, migration 19).
- Tests: `test_workforce_parallel.py` (incl. ignored-path accounting).
- Edge cases: F20-6 (ignored paths are neither integrated nor counted — recorded limitation);
  F20-14 (no conflict-resolution timing).
- Audit target: kill/interrupt mid-integration; double-release; release after failed integrate.
- Status: DELIVERED (limitations recorded).

## INV-ERROR-001 — Cleanup failure never masks the primary causal error
- Definition: a failure while cleaning up (restore rollback, snapshot, teardown) is reported and
  never replaces the original error; failures are never swallowed silently.
- Owner: service/backup paths (`service.py` startup restore call, `backup.py`).
- Tests: partially covered; **PER-02** (P2, open): failed/partial restore is silent;
  **PER-03** (P2, open): pre-restore snapshots unbounded, snapshot failure aborts restore inside
  the same try.
- Audit target: inject restore failure + snapshot failure; verify the surfaced error is the
  primary one and the failure is visible.
- Status: OPEN_GAP (PER-02/PER-03).

## INV-WF-001 — Commander is never spawned
- Definition: the Commander is an interface concept only; never a spawnable template or worker.
- Owner: workforce (`assignment.py` registry v2, 7 spawnable templates).
- Tests: `test_workforce_assignment.py`.
- Audit target: attempt to template/instantiate a Commander via every registry path.
- Status: DELIVERED.

## INV-WF-002 — Builder ≠ Verifier
- Definition: where independent verification is required, verifier binding is a different agent
  identity and family-diverse with a recorded fallback; verdicts refuse while blockers/criticals
  are open.
- Owner: `pods.py` (`run_d2`).
- Tests: `test_workforce_d2.py`.
- Audit target: same-family fallback path; verifier == builder attempt; VERIFIED-with-open-blocker.
- Status: DELIVERED.

## INV-WF-003 — Flag-off performs zero writes (parity by construction)
- Definition: `workforce.enabled` off and `workforce.learning.shadow` off mean zero writes on every
  path; behavior parity with pre-workforce builds.
- Owner: staffing/delegation/pods/learning modules.
- Tests: flag-off parity tests in every workforce phase (5.1–5.6).
- Edge cases: explicit user corrections are user actions, never gated (5.6).
- Audit target: diff DB before/after a full flag-off mission and a flag-off learning window.
- Status: DELIVERED.

## INV-WF-004 — Nothing auto-applies; never-gate is unwaivable by Kel
- Definition: adaptive gating stays off; promotion queue requires the user; learnings are shadow;
  never-gate findings can be waived only by the user, recorded.
- Owner: `assurance.py` (`gate`, `waive_gate`), `learning.py` (promotion queue).
- Tests: `test_workforce_assurance.py`, `test_workforce_learning.py`.
- Audit target: waive never-gate as Kel (must refuse); promotion without user; adaptive flag on.
- Status: DELIVERED.

## INV-WF-005 — Evidence-bound closes; honest uncertain/failed
- Definition: a completed close is refused on stale, unbound or missing evidence, or missing
  criterion coverage; malformed evidence routes end in a violation; double-close refused.
- Owner: `delegation.py` (`close_d1`), `pods.py`.
- Tests: `test_workforce_d1.py`, `test_workforce_d2.py`.
- Edge cases: F4 (no artifact-ownership/content binding — open, wiring increment); producer-check
  optionality (N1) fixed at wiring.
- Audit target: close with forged/stale evidence; close referencing another task's artifacts.
- Status: PARTIAL (F4 open).

## INV-WF-006 — Ledgers are append-only
- Definition: `findings`, `evidence_records`, `workforce_messages` (and issued task contracts)
  refuse UPDATE/DELETE at the SQLite trigger level.
- Owner: `workforce.py` DDL (migration 16).
- Tests: append-only trigger tests.
- Audit target: direct SQLite UPDATE/DELETE attempts against trigger names; trigger tampering.
- Status: DELIVERED.

## INV-MEM-001 — Project/conversation isolation is preserved
- Definition: memory records, proposals, and conversation-addressed subsystems are scoped to their
  project/conversation; cross-scope reads or writes refuse with a policy error.
- Owner: `memory.py` (`_require_project`), `acp_host.py` (`_memory_action` ownership compare).
- Tests: `test_v16_proposals.py`, `test_v13_memory.py`; isolation regressions in
  `test_v141_boundaries.py`.
- Edge cases: the **bare-id addressing class** — `SEC-01` (vetting sessions) and `APR-02`
  (approval resolvers) look records up by id without the ownership comparison the memory paths
  perform. `MDL-01`/`COR-04` (model prefs accept a non-existent conversation).
- Audit target: cross-project memory retrieval via every entry point; record addressed by foreign
  id; proposals leaked across projects.
- Status: PARTIAL (isolation holds on memory paths; sibling modules have open findings).

## INV-MEM-002 — Learnings ride the memory store (no second system)
- Definition: learnings are memory records with workforce source types
  (`workforce_observed`/`workforce_cross_model`/`workforce_inferred`; user-stated rides
  `user_confirmation`); provenance, trust ladder, supersede chains, conflict queueing and forget
  semantics all apply unchanged; no new storage surface, no migration.
- Owner: `learning.py` + `memory.py` SOURCE_TRUST.
- Tests: `test_workforce_learning.py`.
- Audit target: attempt a learning write bypassing the memory writer; duplicate key fork.
- Status: DELIVERED.

## INV-MEM-003 — Decay/preferences/confidence honesty
- Definition: decay is computed at read time from each record's own creation; preferences only
  from explicit user confirmation; confidence above the auto cap is stored capped and queued —
  nothing promotes automatically; retros/metrics carry small-sample labels.
- Owner: `learning.py`, `memory.py`.
- Tests: `test_workforce_learning.py` (decay, preference-requires-user, promotion queue).
- Edge cases: 24-N2 multiplicity ordering note; F23-2/F23-8/F23-9 rate-denominator deviation.
- Audit target: recompute decay/rates from raw rows; attempt promotion without user.
- Status: DELIVERED (limitations recorded).

## INV-LINEAGE-001 — Every generated artifact can say where it came from
- Definition: artifact lineage chains are recorded and readable (`/api/lineage` →
  `{versions:[...]}`); the workspace panel exposes origin for generated artifacts.
- Owner: artifact lineage (core table `artifact_lineage`, unversioned by design).
- Tests: `test_v15` lineage coverage; packaged lineage probe on final16.
- Audit target: unrecorded artifact generation paths; lineage rows without real artifact binding
  (see F4).
- Status: DELIVERED (F4 binding gap open).

## INV-PACKAGE-001 — Packaged app uses the intended runtime engine
- Definition: the packaged engine is built from the same commit and its identity
  (`ENGINE_VERSION`, hash) matches the fresh `dist/runtime` build; probes assert it.
- Owner: packaging (`scripts/build-runtime.ps1`, `kel-builder.json`, probe scripts).
- Tests: packaged engine hash checks in `run-p1-capabilities.sh` etc.
- Edge cases: REL-01 (freeze staging no-op); bundled `bundled-aioncore` staged from cache (stock
  binary not in git).
- Audit target: rebuild from a clean clone; compare engine hash + version end-to-end.
- Status: DELIVERED (with REL-01 noted for the freeze script).

## INV-GIT-001 — Publication is never verification; no history rewrite
- Definition: pushes are explicit-refspec only, never forced, never tags-all/mirror; a
  pre-publication public-safety scan gates each transmitted range; `main` advances only by FF to a
  frozen release.
- Owner: release process (GITHUB_SYNC_POLICY.md; `ux-audit/github-sync-recon/`).
- Tests: scan records + `ls-remote` verification per publication.
- Audit target: re-scan the published range; verify remote refs match records; no phantom tags.
- Status: DELIVERED.

## INV-IPC-001 — Renderer→main IPC validates sender frames
- Definition: every privileged channel validates `senderFrame` before acting.
- Owner: `desktop/.../KelService.ts`.
- Edge cases: **INT-01** (P3, open): `kel:artifact-reveal` handler lacks the check.
- Audit target: enumerate channels; attempt calls from an unexpected frame.
- Status: OPEN_GAP (INT-01).

## INV-VISUAL-001 — Visual never writes Main; integration preserves lineage
- Definition: the visual worktree writes only its own branch; Main integrates (never force
  updates), preserving visual commit lineage; `active_owned_files` prevents races.
- Owner: program process (AUTONOMOUS_OPERATION.md; VISUAL_STATUS.md).
- Tests: n/a (process). Evidence: commit topology.
- Audit target: integration conflict resolutions (a high-value audit area once integration lands).
- Status: DELIVERED; integration pending in Campaign A.

## INV-ROUTE-001 — Deterministic routing, no silent substitution
- Definition: AUTO/PREFERRED/FIXED resolve deterministically; FIXED never silently substitutes;
  fallback records its basis; grants are fail-closed against the authority ceiling.
- Owner: `router.py`, `assignment.py`.
- Tests: `test_workforce_assignment.py` (cross-mode arguments, fallback_basis).
- Audit target: FIXED with missing model; provider disappears between assignment and execution.
- Status: DELIVERED.

## INV-UI-001 — No raw infrastructure errors in user-facing surfaces
- Definition: engine loss / transport failure surfaces a translated, recoverable user state — never
  a raw `TypeError: fetch failed` class message; recovery is explicit (reconnect/restart) and a
  degraded state must not claim success.
- Owner: renderer error paths + `KelService.ts` + engine-loss supervision.
- Tests: packaged probe b reproduces the raw error today (open findings 16/17 — **engine-loss
  behavior is Campaign A scope, batch 6**).
- Audit target: kill the engine mid-stream, mid-request, at boot, at shutdown; confirm each
  surface; confirm no false success.
- Status: OPEN_GAP (to close in Campaign A).

---

## Maintenance

- New invariants are added when a change introduces cross-cutting behavior; do not delete entries
  during Campaign A — mark superseded if genuinely replaced and explain.
- Every increment record must name which invariants its change touches
  (`INVARIANT_LEDGER` pointers) and any new AUDIT_TARGETS lines.
