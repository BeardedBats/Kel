# 17 — TEST QUALITY / NEGATIVE CONTROLS

Audit target `08f56673…`. Method: for campaigns repairs, run the targeted v1.6 tests against **pre-fix module copies** in a scratch package (`build-output/neg/…/kel/`), in place, restoring the frozen tree afterwards.

## Executed negative controls (discriminating evidence)

| Repair | Pre-fix artifact | Test | Result | Reading |
|---|---|---|---|---|
| APR-02 (chat-approval scoping) | pre-APR-02 `chat_approvals.py` | `test_v16_approvals.py` | **6 failed + 1 error** ("conversation aware" tests) | Tests discriminate: they fail on the pre-repair code. |
| R2 (effect idempotency) | pre-R2 `core.py` | `test_v16_r2_idempotency.py` | **1 failed** — `test_a_contradictory_receipt_is_refused_and_the_evidence_is_kept` | Discriminating on the refusal path. |
| R4 (approval exactness) | pre-R4 `authorize.py` | `test_v16_r4_approval_exact.py` | **1 failed** — `test_an_approval_outside_its_window_is_refused` | Discriminating on the window guard. |

All controls then restored; the frozen RC tree stayed byte-clean after every run.

## Static/code-inspection evidence (not dynamic)

- **CHG-004 correction:** the shipped `test_kel_d_e2e.py` content was inspected — it does NOT literally execute builder+verifier completion (it exercises the engine routes/Work view; an earlier note overstated it). Standing E2E-completion evidence = `test_v16_close_d1.py` + `test_workforce_assignment.py` (re-run green). Corrects one training note; no finding.
- **REL-01 / engine-loss:** the honest-failure classifier path is asserted by unit tests (`engineFailure` helper, renderer) and R10 packaged evidence; no pre-fix code artifact was archived for a dynamic control.
- **PERSIST-CANONICAL / SEC-01 / Needs-Your-Attention isolation / credential containment:** covered by suite tests (re-run green) and/or static guards; no pre-fix artifacts retained for those families.

## Limitations

- No exhaustive historical-commit checkout matrix was run; controls were executed where the pre-fix module copies were available (three families above). For the remaining families the discriminating power is asserted from test content plus the green suite, and is flagged here rather than claimed as reproduced.
