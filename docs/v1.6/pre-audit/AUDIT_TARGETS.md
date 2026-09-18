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
