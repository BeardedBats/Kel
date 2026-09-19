# MASTER_FINDINGS — Campaign B (canonical ledger)

Audit target: `08f56673ea93ed84568018937bb190e0a5acd71b` (immutable)
Audit branch: `audit/v16-final` — audit records only; no production fixes (Campaign C owns repair).
Severity schema: `AUD-BLOCK` / `AUD-MAJOR` / `AUD-MINOR` / `AUD-SUG`. Suggestions never inflate failure counts.
Auditor-side status: `RECORDED` → `UNDER_VERIFICATION` → `CONFIRMED` / `DISMISSED` (with reason).
Campaign C fields (repair status / repair commit / re-test / final re-audit) start `NOT_STARTED` / blank.

## Findings

### AUD-MINOR-001 — COMMIT_LEDGER does not account for all commits in the declared range; two rows misbound; RC packaging edits unlisted

- **Severity:** AUD-MINOR (integrity/evidence completeness; not release-blocking alone)
- **Status:** RECORDED (mechanical verification complete; evidence attached)
- **Subsystem:** audit/evidence corpus (COMMIT_LEDGER.md)
- **Requirement IDs:** RL-03 (corpus claims match reality); campaign §5 (ledger completeness)
- **Invariant IDs:** —
- **Affected commits:** `022f3ac`, `0aadd42`, `34947f0`, `12f87a7`, `08f5667` (RC), plus malformed rows for `e8bbb05` ("R6 tests+record", no SHA) and `0aadd42` ("HEAD", wrong parent)
- **Affected files:** `docs/v1.6/pre-audit/COMMIT_LEDGER.md`; evidence: `docs/v1.6/audit-final/evidence/ledger-vs-git.txt`, `commit-classification.tsv`
- **Claim challenged:** COMMIT_LEDGER's own maintenance rule — "EVERY production-affecting commit in this range must appear here. Docs-only commits are listed for completeness"; RC claim "ledger rows cross-checked against git log".
- **Expected:** every one of the 73 range commits either carries a ledger row or a documented, intentional omission (only `08f5667` has such an indirection, by design).
- **Actual:** 4 commits have no mention at all (`022f3ac` test, `0aadd42` docs, `34947f0` production feat, `12f87a7` docs); two rows are malformed (`HEAD` placeholder with incorrect parent; `R6 tests+record` without SHA); and the RC commit `08f5667` additionally contains production packaging edits (`desktop/kel-builder.json` output dir; `desktop/package.json` companyName/author) under a `docs(v1.6):` subject, unaccounted in the ledger.
- **Reproduction:** `bash docs/v1.6/audit-final/tools/classify-commits.py`; the scripted reconciliation in `evidence/ledger-vs-git.txt` §A; `git show --stat 34947f0` / `08f56673`.
- **Root-cause hypothesis:** ledger last updated before the R8.B/R10-prep/R11-record tail; placeholder rows survived bookkeeping cleanups.
- **Confidence:** HIGH (mechanical).
- **Adjacent-risk surface:** OTHER ledgers claiming completeness (CHANGE_LEDGER commit lists for CHG-024/028 omit `34947f0`; TEST_EVIDENCE_INDEX rows).
- **Repair acceptance criteria (for Campaign C):** ledger fully reconciles `git rev-list 8a2b25d..08f5667` 1:1; no placeholder SHA cells; production-affecting commits (incl. packaging edits inside the RC commit) carry rows or a documented exception; a reproducible reconciliation check is added.
- **Regression test required:** a scripted ledger↔git reconciliation gate.
- **Campaign C repair status:** NOT_STARTED — repair commit: — — re-test: — — final re-audit: —

_(Further findings accrue below as passes complete. Nothing is repaired in Campaign B.)_
