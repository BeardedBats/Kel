# corpus-digest-program-docs.md

Recorded by Campaign B from a delegated read-only digest run (child_mu7tqve1_znpzvr, 2026-09-19).
Content is the child's report, condensed; entries marked [AUDITOR] were independently re-verified by
the auditor (full hashes in `git-tags.txt` / `git-anchors.txt`). Claims here remain evidence to
re-check during the relevant audit passes.

## Frozen refs registry — documented vs observed

Documented "expected" values (per 00_CHECKPOINT_FREEZE.md and RC docs):

| Ref | Documented expected | Source |
|---|---|---|
| `v1.5.0` | `v1.5.0^{}` = `5e76b21` | RC docs / 00_AUDIT_BINDING |
| `v1.6.0-pre1` | `v1.6.0-pre1^{}` = `f24d9c2` | RC docs / pre-audit corpus |
| `main` | `5e76b21` (full: `5e76b21071a28601a7fb4de508cb3cf349c77db8`) | MAIN_STATUS / binding |
| `v1.6.0-pre1` artifact source | commit `0fb095fec1d2e8bd640c205c9d6f4f5ab0430fb7` | 00_CHECKPOINT_FREEZE.md |
| V1.5 frozen artifacts | partial hashes `CF1984AC… / 51DD5DFE… / AB3024A0…` | 00_CHECKPOINT_FREEZE.md |
| Older freezes | V1, V1.1, V1.2, V1.3, V1.4, V1.4.1, V1.5 — "re-verified 3/3 and byte-untouched" | 00_CHECKPOINT_FREEZE.md |

Observed (auditor capture):
- `v1.5.0`: tag object `068cd267ff8bdccdffe5f13eb080eafc65f5a0b9` → commit `5e76b21071a28601a7fb4de508cb3cf349c77db8` [AUDITOR: matches]
- `v1.6.0-pre1`: tag object `ceac727ef2d04efdf96c4062a3d891825aefa176` → commit `f24d9c28b09b30d7222691cdb1aafbe21d412672` [AUDITOR: matches]
- `main` = `origin/main` = `5e76b21071a28601a7fb4de508cb3cf349c77db8` [AUDITOR: matches]
- `ux/v15-journeys` = `origin/ux/v15-journeys` = `08f56673ea93ed84568018937bb190e0a5acd71b` [AUDITOR: matches]
- Tags present: v1.2.0, v1.3.0, v1.4.0, v1.4.1, v1.5.0, v1.6.0-pre1.

Child flags: (1) all other refs documented only with abbreviated hashes (auditability weakness; cannot
independently pin without full hash); (2) no discrepancies found among compared values.

## Roadmap R0–R12 (thresholds as stated) + recorded status

- R0 P2/P3 sweep — every row ends FIXED/STALE/NOT_APPLICABLE/DEFERRED_NON_RELEASE/OPEN_RELEASE_BLOCKER,
  evidence inline; exit "27/27 rows decided" (roadmap text) vs achieved "26 canonical (P2 10, P3 16)"
  reconciled at `05608e6`. [drift noted: roadmap body never updated from 27]
- R1 authority ceiling — `effective_child_authority <= delegator_effective_authority`; "Child may
  receive LESS, never MORE"; no nested spawning. COMPLETE (`dc65fbc`).
- R2 idempotency — one logical event → at most one authoritative execution unless a NEW attempt
  identity; side-effects reconcile, never blindly replay. COMPLETE (`fde5bbb`).
- R3 retry durability — automatic loops need a durable limit surviving app/runtime/worker/broker/
  machine restart; budget must not reset. COMPLETE (`1a9f538`, tests).
- R4 approval binding — authorizes one exact normalized action; re-prove immediately before
  execution; mismatch invalidates; scoped to owning conversation/project/job. COMPLETE (`8c899c8`).
- R5 persistence integrity — only canonical, validated, reconstructable state committed durably;
  adversarial tests for malformed/oversized/non-serializable input. COMPLETE (`b2ffed1`).
- R6 truthful state — `process_alive != mission_progressing`; `idle != completed`; `waiting != failed`;
  no recent event != dead; completion requires evidence/assessment; recovery classification resolves
  to exactly one of five outcomes. COMPLETE (tests; `e8bbb05` breadcrumbs).
- R7 credential boundary — capability ≠ raw credential access; no OS-level egress sandbox in
  Campaign A; `host_runtime.py` recorded as user-authorized native full-access execution, NOT a
  sandbox. COMPLETE (`b6c4eff`).
- R8 packaged/migration assertions — fresh DB, supported upgrade DB, packaged app; REL-01 fix proven
  at package/freeze level; Campaign A may create a non-release validation fixture but must not
  perform the final immutable freeze. COMPLETE; REL-01 CLOSED (`93b99b5`, `022f3ac`, `2468b16`).
- R9 visual batches 6–8 + Needs Your Attention — derived-only aggregation; surface owns no
  authority. COMPLETE (`2897207`, `0e7d21a`, `c911d81`, `938dc9b`).
- R10 engine-loss/recovery UX — honest states; `TypeError: fetch failed` never ordinary UX.
  COMPLETE (packaged `r10-{f,g}`).
- R11 visual→Main integration — zero overlapping files; tsc/vitest/package/probes; "Do not mark the
  human visual gate passed." COMPLETE (`7267630`).
- R12 final regression — engine 998+10, desktop tsc 0 / vitest 122/122, package-r12, engine SHA-256
  `69123AF001B8DF7E98FD092E751437044AFF43CA085B0161E45CA08B62AA3AB1`, frozen refs byte-identical.
  COMPLETE.

## Audit-mode / independence statements

- MAIN_STATUS: `audit_mode: READY_FOR_CAMPAIGN_B` (fresh-context hostile audit; "do not self-audit
  in this thread").
- Roadmap §0: independent audit cycles PAUSED (`PAUSED_UNTIL_PRE_AUDIT_RC`); "Nothing … may present
  Campaign A evidence as independently accepted" (INV-AUDIT-001).
- INV-AUDIT-001: "the thread that writes production code never counts as its own independent
  reviewer"; Campaign A verification is parent-executed or self-review only; independence arrives
  only in Campaign B.
- INV-WF-002 (VERIFIER-INDEPENDENCE): builder cannot final-certify its own artifact.
- Negative constraints: no Campaign B/C work in thread; no release freeze; do not move main/tags; no
  history rewrite ever; do not claim human visual gate passed; no OS network firewall; no Profiles;
  no adaptive staffing; no Advanced Worker View (deferred).

## Open / pending / deferred markers

Child counted ~45 distinct marker items across the eight task files + companion docs (23 in the
eight named files). Key items for Campaign B:

- Human Visual gate: PENDING (release gate; DEF-010, LIM-3, RISK-011) — human judgment only.
- Final release/freeze: NOT STARTED (DEF-011; roadmap §9).
- Localization gate: DEF-013 / LIM-12 (new v1.6 surfaces ship English; locale pass decided at
  release gates).
- Provider reality: LIM-2/LIM-14 (mock/static rows cannot read as real validation; no live model
  provider on this machine per 00_CHECKPOINT_FREEZE).
- Windows-only validation: LIM-9.
- Campaign B must re-run critical commands itself: LIM-8.
- PKG-05 acceptance script "vacuous on fresh profiles; re-proven with a seeded record".
- AUDIT_HANDOFF carries five `TBD` rows (PRE_AUDIT_V1_6_HEAD, range start, production count,
  major subsystems, high-risk commits) — some superseded by RC docs (grep indirection for HEAD).
- AUDIT_SCOPE: everything `PENDING` for Campaign B by design (DS/EN/DB/WF/MEM/UX/SP/FI/PK/RL rows).
- RISK_REGISTER: RISK-001..020, most OPEN/OPEN-by-design; RISK-009/010 CONTROLLED.
- Stale markers left in chronological docs (e.g., AUTO_RESUME quotes of TR-01 OPEN, APR-02 OPEN;
  later fixed) — historical, not current claims; re-check each in Pass 4.
- Roadmap R0 text "27/27" not updated after 26-row reconciliation (documentation drift).

## Release-gate statements

- Human visual gate is the load-bearing open gate (human-only).
- Final freeze/tag/moving `main`: not started; `main` advances only by fast-forward to a verified
  frozen release, after ancestry check; never force.
- Public-safety scan gates every push (`CONFIRMED_SECRET` or new `PRIVATE_ARTIFACT` blocks).
- REL-01 was the only declared release blocker at roadmap adoption; declared CLOSED at `93b99b5`
  (Campaign B must attack this closure).
- Provider rows marked mock/static cannot be read as real validation.

## Child flags (kept verbatim intent; [AUDITOR] notes added)

1. Child had no write tool — digest content is this file (recorded by auditor). [AUDITOR: no impact
   on RC; subagent policy limitation only]
2. "audit-final/tools/ is empty" — [AUDITOR: INCORRECT; `tools/classify-commits.py` exists (child
   likely checked before it was committed / or read a stale view).]
3. "The RC commit itself is classified PROD, not docs-only (desktop:2+docs:15)" — [AUDITOR:
   under independent verification; see 01_REPOSITORY_INTEGRITY.md.]
4. Five commits not mentioned in COMMIT_LEDGER.md — [AUDITOR: confirmed independently; see
   ledger-vs-git.txt and 02_COMMIT_COVERAGE.md.]
5. Roadmap 27/27 text drift — [AUDITOR: confirmed by corpus reading.]
6. Abbreviated frozen hashes — [AUDITOR: noted; refs independently verified above.]
