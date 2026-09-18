# Increment — REQ-F4 / WF-12: real-artifact binding (evidence binds to real delivered artifacts)

increment_id: V16-F4-REAL-ARTIFACT-BINDING
phase: Campaign A — audit carry-forward `F4` / audit-scope `WF-12`
base_commit: a7c7aa4 (REQ-RK docs)
target_commit: the implementation commit + this docs commit
status: complete

## Objective

Close the carry-forward recorded since phase 5.3: closure verification compared the evidence's
artifact digest against the **packet's own artifact list**, and `assignment_artifacts` — the table
that records what an assignment really delivered — had a writer (`Team.add_artifact`) and **no
reader at all**. A self-asserted digest could therefore satisfy a content-bound contract.

## Requirement Sources

- `pre-audit/AUDIT_SCOPE.md:78` — **WF-12 | Real-artifact binding (`F4`) | evidence binds to real
  delivered artifacts | campaign wiring item | OPEN carry-forward**.
- `phase5/5.3_IMPLEMENTATION_RECORD.md:78` — "on-disk artifact existence/ownership binding remains
  **F4 — deferred** to the real-worker wiring"; `5.4:67` "F4 remains open"; `5.5:153` "F4 … the
  wiring increment".
- `pre-audit/REQUIREMENTS_TRACEABILITY.md` REQ-F4.

## Implementation Summary

1. **Recorder (the missing wiring)** — `kel/core.py: _record_assignment_artifact(...)`: when a
   milestone artifact lands (the same transaction that writes `artifact_lineage`), the artifact is
   bound to the delivering assignment in `assignment_artifacts` (digest `sha256:<hex>`, filename,
   class `artifact`). Guarded: bare stores with no team tables, or no assignment for that
   milestone, are skipped — the close path then refuses the unbound claim instead of inventing a
   binding.
2. **Verifier** — `kel/delegation.py: _artifact_violations(...)`: for every artifact a packet claims,
   (a) the digest must be recorded for this assignment (ownership), and (b) when the caller supplies
   `artifact_root`, the declared path must exist and, for a full-length sha256 claim, hash to the
   claimed digest (on disk). Digests compare as bare lowercase hex, so `sha256:ABC…` and `ABC…` are
   the same artifact.
3. **Wiring** — `_evidence_violations` merges those violations for content-bound contracts (the same
   gate as the pre-existing "not bound to a delivered artifact" check); `close_d1` takes
   `artifact_root=None` and passes it through. A completed close with violations is still refused
   with the same `PolicyError` shape, now naming the real-artifact violation.
4. **Fixture honesty** — three harnesses that closed content-bound contracts on self-asserted
   artifacts now record what they deliver, exactly as the real worker wiring must:
   `tests/test_workforce_d1.py` (success helper), `tests/test_workforce_d2.py` (builder + verifier
   workers), and `kel/evaluation.py` (`_make_builder`/`_make_verifier`, the pilot's deterministic
   specialists). The gate found every remaining unbacked claim itself: the first full run reported
   8 failures + 5 errors in `test_workforce_d2.py` / `test_workforce_parallel.py`, all resolved by
   recording the deliveries.

## Files Changed

- `runtime/kel/core.py` (`_record_assignment_artifact` + its call where the artifact lands)
- `runtime/kel/delegation.py` (`_normalise_digest`, `_artifact_violations`, `_evidence_violations`,
  `close_d1`)
- `runtime/kel/evaluation.py` (pilot specialists record their deliveries)
- `runtime/tests/test_workforce_d1.py` (4 new tests + the success helper records its artifact)
- `runtime/tests/test_workforce_d2.py` (builder/verifier workers record their deliveries)

## Symbols Changed

`Store._record_assignment_artifact`, `_normalise_digest`, `_artifact_violations`,
`_evidence_violations(…, artifact_root)`, `close_d1(…, artifact_root)`.

## Schema/Migrations

None. `assignment_artifacts` already existed (team schema) — this increment gives it a reader.

## User-Facing Behavior

None directly (engine closure semantics). A content-bound task can no longer be closed on an
artifact that nothing delivered.

## Internal Behavior

`close_d1` refuses with messages like
`artifact art_e51 (sha256:77bb) was never recorded as delivered by this assignment`,
`artifact art_e51 is not on disk at src/api/export.py`, or
`artifact art_e51 digest sha256:bbb… does not match sha256:aaa… on disk`.

## Error Paths

Refusal is the same `PolicyError('Evidence-bound close refused: …')` path as before (first five
violations are surfaced); the assignment stays open for a corrected packet.

## Lifecycle Considerations

`_record_assignment_artifact` is idempotent (`INSERT OR IGNORE` on the (assignment_id, digest) key)
and inside the consume transaction, so the binding commits with the artifact.

## Persistence / Isolation

No new files; one existing table gains its first reader.

## Security / Privacy

None. Strictness increases (claims must be backed by delivered artifacts).

## Self-Review Findings

- The on-disk half needs an artifact root, which the engine legitimately does not know at close
  time; it is therefore an explicit parameter and the *ownership* half is always enforced. Recorded
  as a residual: `run_d1` does not yet pass a root, so on-disk verification runs wherever a caller
  supplies one (tests do).
- Digests shorter than a full sha256 (fixtures) skip the hash-equality check but still require the
  ownership binding — recorded in the code comment and here.

## Tests Run

- `cd runtime && python -m pytest tests/test_workforce_d1.py -q` → **35 passed** (31 + 4 new).
- Full engine suite: see TEST_EVIDENCE_INDEX A-14.

## Results

PASS (engine).

## Packaged Verification

Not applicable (engine-internal closure semantics; the RC packaged battery re-runs the engine suite
against the packaged runtime).

## Known Weaknesses

- `run_d1` still calls `close_d1` without `artifact_root`, so a live run's on-disk check depends on
  the caller; wiring a project root through `run_d1` is a follow-up (audit target 56).
- A non-content-bound contract still accepts a claimed artifact list (unchanged scope; F4 is about
  the content-bound promise).

## Deferred Questions

- Should `lens_stats`/the review surface expose artifact-binding failures as a learning signal?

## Audit Targets

AUDIT_TARGETS § 55–56.

## Repair Hints

The recorder is in `kel/core.py` next to `_record_lineage`; the verifier in `kel/delegation.py` next
to `_evidence_violations`. Both are small and separate on purpose.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/REQ-F4-REAL-ARTIFACT-BINDING.md` (this file)
- corpus rows: REQUIREMENTS_TRACEABILITY REQ-F4, CHANGE_LEDGER CHG-006, TEST_EVIDENCE_INDEX A-14,
  COMMIT_LEDGER
