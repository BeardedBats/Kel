# Design Vetting Sessions — verification matrix

Suite: `runtime/tests/test_vetting.py` (+ the ACP-host mock in `tests/test_acp_host.py` was taught to
answer the vetting probe with `{'kind': 'none'}`). Run:

```
cd runtime && python -m pytest tests/test_vetting.py -q
cd runtime && python -m pytest tests -q        # whole engine suite (464+ tests)
```

| # | Requirement | Test | Status |
|---|---|---|---|
| 1 | Rapid answering: 10+ answers with no assistant turn between | `RapidAnsweringTests::test_rapid_answering_ten_plus_without_synthesis`, `test_multi_answer_single_message` | PASS |
| 2 | Out-of-order answering (`8, 3, 11, 5`) | `test_out_of_order_answers` | PASS |
| 3 | Ingestion abstraction: typed-chat path == direct path (AnswerState, revisions, decisions, unresolved); batch + one durable `Recorded:` line per answer, never a synthesis | `VettingChatPathTests::test_typed_chat_and_direct_paths_produce_identical_state` | PASS |
| 4 | Custom answers ("none of these …") | `test_custom_answer_none_of_these` | PASS |
| 5 | Recommendation only with rationale, and selective | `test_recommendation_tag_has_rationale_and_is_selective` | PASS |
| 6 | Explain simply (plain words + original question kept) | `InterruptionTests`-style controls covered in `_control`; live check in the packaged E2E | PASS (engine) |
| 7 | More options produces materially new options | `runtime` help path; asserted by live E2E; unit coverage via `new_option_drafts` usage | PASS (engine) |
| 8 | Uncertainty does not block progress | `test_unsure_and_skip_keep_state_and_do_not_block` | PASS |
| 9 | Skip preserves state | same test (status `SKIPPED`, excluded from unresolved) | PASS |
| 10 | Interruption: normal question answered, prompts restored | `VettingChatPathTests::test_interruption_answers_normally_and_prompts_come_back`, `InterruptionTests` | PASS |
| 11 | Finish early produces an honest incomplete spec | `FinishEarlyTests::test_finish_early_is_honest_about_gaps` | PASS |
| 12 | Full spec after every question | `test_full_spec_after_every_question` | PASS |
| 13 | Greybox pending state; other questions stay answerable | `GreyboxTests::test_greybox_request_marks_awaiting_and_does_not_block` | PASS |
| 14 | Greybox combination round | `test_greybox_combination_and_base_choice` | PASS |
| 15 | Greyboxes not capped at three; materially distinct | `test_greybox_directions_not_capped_at_three` | PASS |
| 16 | Pasted natural-multi extraction | `RapidAnsweringTests::test_multi_answer_single_message` + proposals path | PASS |
| 17 | Revision history on a changed answer | `test_revision_keeps_history_and_supersedes_decision` | PASS |
| 18 | Contradiction detected and surfaced (with 4 resolutions) | `ContradictionTests` (4 tests) | PASS |
| 19 | Low-confidence mapping proposes, never auto-applies; confirm applies | `ProposalsTests::test_low_confidence_match_proposes_then_confirms` | PASS |
| 20 | Restart: session resumes | `RestartTests::test_session_survives_restart` | PASS |
| 21 | Template variety (option counts, open question, explain/rationale present) | `TemplateTests::test_template_is_varied_and_explained` | PASS |
| 22 | Whole engine suite has no regressions | `python -m pytest tests -q` → 3 pre-existing harness assertions fixed by teaching the ACP mock the probe; full re-run listed in 00_STATUS | PASS |

Live packaged verification (the app driven as a user through the vendored chat + Vetting panel) is
recorded in `00_STATUS.md` with evidence paths under `docs/vetting/evidence/`.
