# AUDIT_TARGETS — adversarial seed list for Campaign B

updated: 2026-09-18T16:05Z
rule: these are attacks, not accusations. Every attack ends in reproduction evidence or a
recorded "not reproduced". Aim to make the audit smarter than the implementer.

## Engine lifecycle / recovery
1. Kill the engine after the UI successfully mounted, then request — assert no raw infrastructure
   error, no false success, and a real recovery path (currently reproduced: findings 16/17).
2. Kill the engine mid-stream; assert terminal state truthfulness (no "completed" without output).
3. Restart the app while a mission/parallel mission is in flight; assert resume correctness and no
   instance-state loss (APR-03 class: `_memory_check_queue`).
4. Force a lease-release failure while a primary error exists — assert the primary causal error
   surfaces and cleanup failure does not mask it (INV-LEASE/INV-ERROR).
5. Trigger announce-failure after a terminal stream state (approvals flow) — assert no silent
   inconsistency between anchors and chat.

## Capabilities
6. Embed capability tokens in: quoted text, inline code, fenced code, URLs, nested brackets
   (`[[kel:web=off]]`), word-embedded (`prefix[kel:web=off]suffix`), mixed case, punctuation
   adjacency; assert byte-identical forwarding and zero state change.
7. Long-message edge: a reserved directive inside a >2000-char paste (CAP2-LONGTEXT) — assert
   fail-safe (no mutation, no silent text removal) and note the missing feedback.
8. `web: off` in conversation A while a research job is dispatched from conversation B (including
   engine/scheduled jobs with no `submissions` row) — assert the correct conversation's decision.
9. Unknown capability probe — assert fail-closed (unavailable + resolve denies; DEAD-08).

## Memory / isolation / learning
10. Retrieve/correct/forget project A memories from project B context (all endpoints + proposals);
    same for conversation-scoped prefs (MDL-01/COR-04) and vetting sessions (SEC-01).
11. Memory proposals: identical evidence must not re-propose; changed evidence must re-propose;
    supersede chains must not fork a (type, key) identity.
12. Learning decay at read time: re-observation multiplicity (24-N2), rate denominators
   (F23-2/8/9) — recompute from raw rows; challenge small-sample labels.
13. Forget semantics: tombstone + audit event; assert retrieval cannot resurrect; assert
    correction chains keep user-stated trust.

## Workforce
14. Attempt to spawn Commander via any path (INV-WF-001); attempt Builder == Verifier; force
    family-diverse fallback unavailability.
15. Close a task with stale, unbound, or missing evidence; missing criterion coverage; assert
    honest uncertain/failed closes and refusal of completed closes.
16. Attempt to waive a never-gate finding as Kel (must be user-only) and to auto-promote learnings
    above the cap (must queue, not promote).
17. Parallel missions: two streams writing the same file (disjointness), ignored paths (F20-6),
    conflict timing (F20-14), undeclared writes (N21-5).
18. Flag-off parity: every automatic workforce write path with flags off (zero writes).
19. Provider disappears between assignment and execution — assert fallback recorded with basis;
    no silent substitution (AUTO/PREFERRED/FIXED; N1 legacy check).

## Security / privacy / data
20. Approval payload without/with a forged actor (APR-01); resolution from a different
    conversation scope than the read (APR-02); expired/one-shot re-use.
21. Restore failure injection (PER-02): assert user-visible truthful state, no silent swallow;
    snapshot growth/retention (PER-03); `KEL_DATA_DIR` credential inclusion (PER-04).
22. Multipart filename escaping (SEC-01-multipart); transcription stream cleanup on shutdown
    (TR-01); abandoned-stream UX (TR-02).
23. IPC sender-frame validation on every `kel:*` channel (INT-01); dispatch KeyError leaks
    (ERR-01/COR-06); theme overrides surviving deletion (THM-01).
24. Secret scan over the whole published range (not just new commits); assert no credentials in
    corpus evidence files.

## Migrations / packaging / release
25. Migration chain: fresh DB; upgrade from a real prior DB (pins at 14 and 15); interrupted
    migration; duplicate/missing version check; packaged boot `schema_migrations` assertion.
26. Packaged engine identity: hash vs fresh build; detached-engine reuse with wrong-version
    descriptor (A1); update behavior.
27. Freeze tooling: staging no-op (REL-01) and nested inert runtime duplicate; frozen releases
    remain byte-identical (4-hash manifest) at RC; remote refs unchanged.
28. Publication claims vs `ls-remote` (publication is never verification).

## Visual / integration / corpus
29. Every visual merge conflict resolution (§44) — no force updates, no silently dropped behavior;
    lineage preserved.
30. Corpus integrity: `git log 8a2b25d..PRE_AUDIT_V1_6_HEAD` vs COMMIT_LEDGER rows (no gap, no
    unlisted commit); every evidence path exists; every count matches the artifact; hunt for
    "empty but plausible" records.
31. Re-run the critical commands from TEST_EVIDENCE_INDEX on a fresh clone; compare counts.

## Memory reality (Phase 6 additions)

32. Probe cross-project ids on every memory-adjacent endpoint (memory + proposals + conflicts +
    vetting sessions + model prefs) — assert refusal with no leak and no existence oracle in errors.
33. Superseded-chain integrity: correct an active record, then attempt confirm/retract/correct on
    the superseded one via API **and** UI — expect refusals, and the UI must not offer the actions.
34. Forget a record that is the target of an open conflict/proposal — expect `_sync_proposals`
    supersede, no dangling references, tombstone stays readable.
35. Proposal dedupe under rejection: reject with evidence X → suppressed; change evidence → new
    card; accept twice refused; deferred → accept later works.
36. Composer packet: open-conflict records labeled, trust≥6 omitted with reasons, cross-project ref
    boundary asserted (`_pack`); attack the label rendering with unusual values.
37. Guard drift: map every `Memory.confirm/correct/retract/forget` guard to `memoryRecordActions`
    and flag any unmirrored difference (CHG-001 audit question).
38. Knowledge-tab tombstone: forgotten record renders "Content removed.", offers no actions; the
    forget confirmation cannot be bypassed (keyboard/programmatic paths).
39. Packaged Knowledge-tab pass (recorded gap): records list, actions, tombstones, forget confirm.

## Capability recommendations (Phase 7)

40. Forge a recommendation: unknown capability id, fake action (`"deploy"`), or a non-refused
    decision — the card must render nothing / act on nothing, and `/api/capabilities` must refuse
    unknown capabilities/actions plainly.
41. Stale card: leave a card visible, change the policy elsewhere (Tools control), click Allow
    once / Enable — assert the result matches the *current* policy and the confirmation is truthful.
42. Nagging: keep-it-off dismissal persists across panel refreshes; a resolved milestone (success)
    never re-shows a cleared recommendation.
43. Grant semantics via the card: Allow once is spent by the real effect exactly once; Enable is
    conversation-scoped only; both fail closed when the capability is unavailable/removed.
44. Coding-path attachment: produce a BLOCKED coding run (files/terminal/github off) — assert the
    milestone carries the same structured recommendation (currently untested end-to-end).
45. Packaged card rendering (deferred evidence): seed a blocked milestone with a recommendation in a
    packaged app; assert the card renders, actions hit the engine, and dismissal works.

## Profiles / Projects (Phase 9 additions)

46. Donor-dead paths: confirm no Kel conversation can render an `AgentBadge` that navigates to the
    hidden donor assistant editor (`assistantId` path under `HIDE_DONOR_AGENT_SURFACES`); confirm
    no `/profiles` route or Profiles terminology is reachable anywhere.

## Canonical logo (2026-09-18 additions)

47. Dead donor mark: `renderer/assets/logo.svg` (AionUi) — confirm no importer and no bundler
    reachability; decide remove vs keep as a dormant boundary.
48. Installer path: the Kel build produces **both** `win-unpacked` and an NSIS installer (targets
    merge `nsis` + `dir`). The donor `resources/windows/*.nsh` messages are **not included** by the
    builder config, so the shipped installer uses electron-builder's stock Kel-named template —
    confirm that stays true (no `include:`/custom installer script added without rebranding them) and
    that installer/uninstaller/header icons remain the K.
49. Shipped exe metadata: **observed on `package-logo`** — `Kel.exe` reports
    `ProductName=Kel · FileDescription=Kel · CompanyName=AionUi · FileVersion=1.5.0` (before this
    change it reported Electron's own identity). `CompanyName` comes from `package.json` `author`;
    decide whether donor company/author metadata is branding to replace or intended attribution, and
    whether `description` = "Kel with the AionUI interface" should stay.
50. Icon quality: extract the exe icon and the tray icon and confirm legibility at 16/32/48, exact
    transparency (no black/opaque background), and no distortion or letterboxing.
51. Reachability sweep: enumerate every `<img>`/`background-image`/inline svg in the renderer and
    every packaged resource; assert none shows the donor mark on a reachable surface.
52. Derivative integrity: re-run `scripts/make-brand-assets.py --check` and confirm the recorded
    hashes (guards against later asset drift).

## Resolution kinds (2026-09-18 additions)

53. Resolution kinds: confirm every guarded path that writes a resolved status (`resolve_finding`,
    `waive_gate`) also writes `resolution_kind`, that no other path can write `dismissed`/`fixed`
    without one, and that a hand-written `dismissal_reason` cannot change any statistic. Verify the
    v17 `ALTER TABLE` is lossless on a populated pre-v17 store (rows preserved verbatim).
54. Learning-loop semantics: `fp_rate`/`learnable` must be unchanged for pre-v17 rows (derived once)
    and correct for new rows; no review surface silently reads reason text.

## Real-artifact binding (2026-09-18 additions)

55. Real-artifact binding: confirm no path can close a content-bound contract on an artifact that
    `assignment_artifacts` does not record for that assignment; confirm the recorder cannot
    double-write or bind an artifact to the wrong assignment (job+milestone lookup), and that a
    bare store (no team tables) fails safe (refuses rather than invents a binding).
56. On-disk binding coverage: `close_d1(artifact_root=…)` is exercised only where a caller supplies
    a root (tests do; `run_d1` does not yet) — verify the live path supplies one before any release
    claim of on-disk verification, and that a stale/renamed file is refused.

## Restore visibility (2026-09-18 additions)

57. Restore failure surfacing: the engine now records `restore-outcome.json` beside the data and
    exposes `state()['restore']`; verify no restore failure can occur without that record, that a
    failed attempt keeps `restore-pending.json`, and that a renderer surface (REQ-ELOSS) reads the
    existing payload instead of a new endpoint. Also confirm `state()['restore']` cannot report a
    stale outcome after a later clean start (PER-02) and is not confused by PER-03's snapshot path.

## Sweep batch 2 (2026-09-18 additions)

58. Sweep batch 2 verification: (a) the `kel:artifact-reveal` IPC guard has no automated test here
    (no Electron/IPC harness) — challenge it by reading the handler against its four siblings and by
    attempting a call from a non-main frame; (b) confirm no multipart parameter can reach the socket
    unsanitised (`_header_safe` is applied to *every* parameter, not just the filename); (c) confirm
    `NEVER_BACKUP` is consulted on every backup path, including the hot-database copy, and that the
    credentials sidecar is reported as skipped rather than silently absent.

## A1 engine-version binding (2026-09-18 additions)

59. Engine-version binding: the *decision* is unit-tested (`engineVersionAccepted`) but the wiring
    has no Electron harness — challenge it by reading `initializeKel` and confirming **both** trust
    sites check the version (the reuse path and the spawn-wait loop) and that no other path can set
    `connected = true` from an unchecked answer. Also confirm a stale engine that keeps re-writing
    the shared `desktop-session.json` cannot satisfy the check, and that a packaged build's
    `app.getVersion()` really equals the engine's `ENGINE_VERSION` in the RC artifact (a mismatch
    would now block startup instead of silently reusing).

## Snapshot retention and actor guard (2026-09-18 additions)

60. Snapshot retention + actor guard: confirm `_prune_snapshots` cannot delete the snapshot a failed
    restore needs (the current attempt's directory must always be the newest) and that it touches only
    directories matching the `<data-root>.pre-restore-` prefix — a user's own directory must never be
    pruned. Confirm the payload-actor guard is reached on **every** action family that accepts input
    (the generic check plus the per-route repeat), and that adding a new route cannot bypass it.
    APR-02 and SEC-01 remain OPEN: their fixes must add an ownership/scope parameter to the
    session/approval lookups — verify the fix actually refuses a cross-scope id rather than only
    documenting the intent.
