# 06 — Completion Authority (Kel V1.5, G5 audit)

Status: **audited + claims compiler shipped** — completion depends on evidence; worker self-report
and process exit remain evidence only. Source citations below (V1.5 G5).

## The compiler (`kel.core.completion_claims`, attached by `validate_contract`)

Every contract now carries an explicit claims projection — computed deterministically from the
trusted acceptance checks, never invented:

| Claim field | Source |
|---|---|
| `id` | `<milestone>.c<n>` (plus `repository.evidence` for coding) |
| `requirement` | the milestone objective (the user's phrasing) |
| `acceptance_criterion` | the exact check (contains literal / min length / rubric text) |
| `verification_method` | builtin check or independent rubric review; repository evidence for coding |
| `objective_or_subjective` | builtin checks objective; rubric review subjective |
| `evidence_required` | artifact digest + check result, or reviewer findings, or code_evidence |
| `failure_condition` | check FAILED, reviewer verdict FAILED, or evidence FAILED/UNCERTAIN |
| `dependencies` | the milestone dependency list, mirrored |

Tested across families in `test_v15_completion.py`: coding, document/writing, research (plus the
multi-step and trivial cases). A trivial request stays at one objective claim — no invented
verification. Executable oracles remain forbidden; only the three trusted builtin checks plus
review exist (`validate_contract`).

## How completion is still governed by evidence

- `Store.verify` aggregates artifact digest + builtin checks (+ repository/research evidence) —
  `aggregate()` returns VERIFIED only when every check verifies.
- `Store.assess` re-reads artifacts and evidence at settle time; missing/uncertain evidence ⇒
  UNCERTAIN, never a pass. `publish` reassesses before publishing.
- `record_review` is the only way a rubric check becomes VERIFIED, and it refuses the executor as
  reviewer (`reviewer_id == artifact run_id` ⇒ PolicyError) and stale subjects.
- Invariant tests retained from the base suite: executor cannot self-accept; process exit alone
  never closes a milestone (worker result ⇒ CHECKING ⇒ checks decide).

## Independent review audit (WS13)

| Property | Mechanism | Evidence |
|---|---|---|
| Reviewer independence | `Commander._reviewer`: health first, then different model **family** (`PROVIDER_FAMILIES`), then different provider; ties keep the default order | `test_v12_reviewer_diversity`, commander source |
| Artifact-first | `Commander.review` reads `store.artifact_text` (+ accepted dependency artifacts) and the rubric; findings recorded with the subject digest | commander source; `test_review_recovery` |
| Original requirement visible | the review prompt carries the source request, exact rubric, and accepted dependency evidence | commander source |
| Creator explanation isolation | review input is the artifact text and requirement only; worker transcripts/prompts are not accessible to the reviewer path | commander source |
| Disagreement resolution | reviewer verdict (VERIFIED/FAILED/UNCERTAIN) combines with the other checks via `aggregate`; UNCERTAIN remains uncertain | `Store.record_review` |
| Reviewer failure | review exceptions record UNCERTAIN with a reason; ≤2 automatic recovery attempts, then an explicit uncertain record — never a silent pass | `Engine._review` / `_schedule_review` |
| No rubber-stamp loops | every review is a distinct attempt recorded in `review_runs`; executor identity can never satisfy the review | `record_review` refusal + recovery tests |
| Confidence | rubric verdicts carry findings; uncertainty is surfaced to the user summary (`verification_summary`) | core source |

## Open items (recorded)

- The reviewer-rubric viewer and requirements-coverage UI surfaces (V14-111/113) remain for the
  product gates (G7); the engine-side data for both now exists (claims + review records).
- Multi-reviewer quorum for subjective work is not implemented; single independent review is the
  shipped V1.5 behavior and the docs say exactly that.
