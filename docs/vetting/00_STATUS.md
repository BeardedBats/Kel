# Design Vetting Sessions — status

Program: implement the brief "Design Vetting Sessions" as a first-class Kel feature, verified like a
user before resuming the User Journey Auditor program.

## State

| Area | State | Evidence |
|---|---|---|
| Engine model + migration `v15-vetting` | **done** | `runtime/kel/vetting.py`, `test_vetting.py` |
| Ingestion service (source-independent) | **done** — typed chat == direct call | `test_vetting.py::VettingChatPathTests::test_typed_chat_and_direct_paths_produce_identical_state` |
| Chat path: silent ingestion, no assistant turn, resurface after interruptions | **done** | `acp_host` interception + resurface; ACP/vetting tests; live packaged run |
| Batch generation + adaptation (template bank) | **done** (deterministic; LLM hook documented) | `runtime/kel/vetting_bank.py`, `TemplateTests`, `adapt()` rules |
| Conflicts, revisions, decisions, proposals | **done** | `ContradictionTests`, `ProposalsTests`, `test_revision_keeps_history_and_supersedes_decision` |
| Greybox directions + comparison + combine + pending | **done** | `GreyboxTests`, live panel check |
| Spec generation (partial-safe, honest) | **done** | `FinishEarlyTests`, `test_full_spec_after_every_question` |
| Vetting panel (Work drawer tab) | **done** | `KelWorkPanel.tsx` Vetting tab; live packaged run |
| Whole-engine regression suite | **done** | `python -m pytest tests -q` green after every change (25 → 30 vetting tests; see the run records committed with the feature) |
| Live packaged verification (use it like a user) | **done** | `ux-audit.cjs vetting-live` battery run `b2-vetting-live`: panel shows the session (topic, FINISHED, recorded progress, decisions), transcript/DB contain the alternating run, zero console errors; screenshots + `live-databases.txt` in `docs/vetting/evidence/live/` |
| Documentation set | **done** | this directory |
| Independent review | **done** | review relay checkpoint at the program boundary |

## How to run

```
cd runtime && python -m pytest tests/test_vetting.py -q      # 25/25
cd runtime && python -m pytest tests -q                      # full engine suite
NODE_PATH=desktop/node_modules node packaging/ux-audit.cjs <packaged-app> <root> <out> vetting
```

## Key files

- `runtime/kel/vetting.py` — schema + `VettingAnswerIngestion` (the abstraction boundary).
- `runtime/kel/vetting_session.py` — sessions, batches, decisions, conflicts, greyboxes, spec, panel,
  `snapshot()` (the equality surface), chat routing.
- `runtime/kel/vetting_bank.py` — Product/UI template (28 questions, 9 sections) + adaptation.
- `runtime/kel/vetting_spec.py` — spec markdown, option drafts, challenge text, SVG wireframes.
- `runtime/kel/service.py` — `/api/vetting` action family; `runtime/kel/acp_host.py` — chat interception
  and resurface.
- `desktop/.../KelWorkPanel.tsx` — the Vetting tab.
- `packaging/ux-audit.cjs` — `vetting` E2E scenario.
- `docs/product/USER_JOURNEY_STANDARD.md` / `HISTORY.md` — rules JR-31..33 and entries H11..H13.
