# KEL V1.3 — TEST MATRIX

Status: Gate 1 design deliverable. This matrix maps the brief's adversarial acceptance matrix to
concrete, runnable tests. Every test carries an id used by implementation commits and by
`KEL_V1.3_VERIFICATION_REPORT.md`.

## 0. Method and levels

- **U** = unit (pytest, hermetic, fake adapters, temp dirs).
- **I** = integration (real SQLite store on disk, fake providers, real engine tick loop).
- **L** = live (real data dir + real engine process; may use throwaway dirs).
- **P** = packaged (the actual `Kel.exe` / `KelEngine.exe`; Playwright/Electron harness pattern
  proven in V1.2).
- **Retention rule**: the full engine suite must stay ≥ **181 passed + 10 subtests** at every
  gate; no V1.2 test may be deleted or weakened. New tests are additive.
- File convention: `tests/test_v13_memory.py`, `test_v13_projectmap.py`, `test_v13_composer.py`,
  `test_v13_continuation.py`, `test_v13_recipes.py`, `test_v13_migration.py`,
  `test_v13_poisoning.py` (poisoning cases may also live per-module; the ids below are canonical).

## 1. MEMORY (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| MEM-01 | Explicit user decision persists across restart and new conversation | I | Record L2 decision; close/reopen store; new conversation; decision present, `trust=2`, `user_confirmed=1`, visible in select() |
| MEM-02 | Verified repo fact stores correct provenance | I | Deterministic inspection fixture → record; `source_type=repo_inspection`, `source_ref` exact, `source_digest` set, `trust=3` |
| MEM-03 | Model inference remains lower-trust | U | `propose()` → `trust=6`, `confidence` set, `user_confirmed=0`; excluded from decision queries; labeled "inferred" in composer output |
| MEM-04 | New explicit decision supersedes old; history inspectable | U/I | v1 then v2 same topic → v1 `superseded` + `superseded_by=v2`; select returns v2 only; `history()` shows both |
| MEM-05 | User can correct and retract memory | U | correct → new record supersedes; retract → `retracted`, excluded from select; events present |
| MEM-06 | User can forget memory | U | forget → `value`/`summary` purged, `status=retracted`, tombstone event carries no content |
| MEM-07 | Project A memory never appears in Project B | I | Same topic recorded in two projects; selects disjoint; conflicts disjoint; composer project check fails loudly if crossed |
| MEM-08 | Secret-like values are rejected/redacted | U | Fixture set: API-key shapes, `Authorization:` header, token, private-key block → write refused with explanation; events contain no value |
| MEM-09 | Malicious README instructions do not become authoritative | I | External doc with "ignore previous instructions…" stored as L7 evidence only; cannot become a decision; composer output keeps quote labels; fence markers stripped from model output (adopted hermes sanitizer test mirrored) |
| MEM-10 | Stale commands lose authority after config change | I | `command` record with digest; mutate config; `revalidate()` → `stale`; excluded from composer; UI lists as stale |
| MEM-11 | FTS fallback path works | U | Run retrieval suite with FTS5 disabled → same results (bounded LIKE); flag recorded in schema_migrations |
| MEM-12 | Migration is idempotent + backup receipt | I | Open V1.2 fixture DB → tables created once, backup file exists with valid integrity check + receipt; re-open → no-op |

## 2. PROJECT MAP (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| MAP-01 | Map identifies correct commands and entry points | I | Fixture repo (py + js variants) → execution/architecture sections match ground truth; every command/entry has `source_ref` |
| MAP-02 | Map records source references | I | Every section carries refs; inferred prose labeled `inferred`; verified skeleton labeled `verified` |
| MAP-03 | One changed config file refreshes only affected sections | I | Change `package.json` scripts → new version refreshes `execution`; `architecture` copied forward byte-identical with same digests; refresh note lists what changed |
| MAP-04 | Source fingerprint changes mark stale data | I | Fingerprint compare across two versions → changed sections flagged; composer surfaces staleness note |
| MAP-05 | Manual refresh works | L | Refresh from Work context endpoint → new version, updated timestamp, no page errors |
| MAP-06 | Greenfield project gets a valid initial map | I | Empty dir + git init → minimal valid map (identity + execution defaults), no exception; unknown fields null, not guessed |
| MAP-07 | Never rescan entire repo unnecessarily | I | Instrumented fixture counts inspections; second refresh with no changes performs zero subprocess git calls beyond fingerprint |

## 3. CONTEXT (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| CTX-01 | Relevant decisions appear in the packet | I | Matching decision recorded → packet includes it with `sources[].reason` + trust label |
| CTX-02 | Irrelevant memories do not appear | I | Unrelated topics recorded → not selected; `omitted` count recorded |
| CTX-03 | Superseded decisions do not appear | I | Superseded record excluded from packet; current record included |
| CTX-04 | Conflicts are surfaced | I | Open decision conflict → packet `conflicts[]` populated + user notice fired before use |
| CTX-05 | Full transcript is not dumped | I | Long conversation → packet has bounded `recent_turns` only (≤16 msgs / 8k chars); no raw worker transcripts; source-kind assertion |
| CTX-06 | Packet size and selected sources are recorded | I | `context_packets` row exists with sources/omitted/sizes; packet digest stable |
| CTX-07 | Project boundaries are enforced | I | Cross-project memory/map never enters; internal assertion raises if it would |
| CTX-08 (S) | Deterministic composition | U | Identical inputs → identical `packet_id`; stable tie-breaks |
| CTX-09 (S) | Over-budget behavior | U | Forced overflow → drop order respected; omissions recorded; request/decisions/constraints never dropped |

## 4. CONTINUATION (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| CONT-01 | Resume active job after app restart | L | Slow fake worker mid-job → kill engine → restart → job settles once; no double execution; publication correct |
| CONT-02 | Resume from a new conversation | I | Paused job; new conversation "continue…" → linked (`job_links`), resumed; original conversation untouched |
| CONT-03 | Resume valid native provider session | I | Stored valid `native_session` fixture → adapter argv contains the exact session id (reuse path) |
| CONT-04 | Fall back safely when native session is gone | I | Invalid/missing session → bounded packet fallback; explicit message; "most recent" never used |
| CONT-05 | Preserve accepted milestones | I | Accepted milestone + fresh resume → milestone untouched (state + digest); not re-run |
| CONT-06 | Retry only incomplete/failed milestones | I | Mixed milestone states → only non-accepted milestones claimed |
| CONT-07 | Source change invalidates only dependent accepted work | I | Change repo file → resume → affected accepted milestone invalidated with explicit reason; unaffected untouched |
| CONT-08 | Several candidates trigger a choice | I | Two eligible jobs → `kind=choice`; list renders; selecting runs the single flow |
| CONT-09 | Wrong-project continuation is blocked | I | Request referencing another project's job → refusal message; nothing attached |
| CONT-10 | Completed work is not mistakenly resumed | I | VERIFIED job → refusal ("already verified"); no reopen |
| CONT-11 | Approval state survives and remains actionable | I/L | AWAITING_USER → restart → approval pending; resolve path works; badge "1" |

## 5. RECIPES (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| REC-01 | Each initial recipe compiles to a valid CompletionContract | U | All 5 builtin recipes × input fixtures → `validate_contract` passes; recipe provenance `{id, version, digest}` present |
| REC-02 | Interrupted recipe resumes | I | Interrupt mid-recipe (broker kill) → continuation resumes; only incomplete milestone re-runs; accepted ones frozen |
| REC-03 | Accepted steps remain frozen | I | Accepted milestone untouched across resume (state + digest); never re-executed |
| REC-04 | Failed step receives bounded repair | I | Failing fake worker → retries ≤ `max_attempts`; provider switch at 2; terminal block surfaces FAILED/UNCERTAIN per existing paths |
| REC-05 | Recipe cannot escalate undeclared permissions | U | Recipe using `project:write` without declaring → `PolicyError` at compile; engine routing still hard-filters capabilities |
| REC-06 | Recipe terminal verdict remains Kel-controlled | U/I | Recipes cannot inject verdicts; `assess()` remains the only producer; declaring `[VERIFIED]`-only rejected; forged publish attempts rejected |
| REC-07 | Project-local recipe versioning works | I | Save v1.0.1 project-local → shadows builtin in that project; same-version content change rejected; runs pin the digest |
| REC-08 | Saving a successful run as a recipe requires confirmation | I | `propose_from_job` → draft visible; save without confirmation flag refused; with flag → saved + `recipe.saved` event |

## 6. TRUST / COMPLETION (brief matrix → tests)

| Id | Scenario | Level | Setup → Pass criteria |
|---|---|---|---|
| TRUST-01 | Worker output never self-certifies memory or completion | I | Worker attempt to write verdicts/memory directly → no such path; memory only via review gate; completion only via `assess` |
| TRUST-02 | Reviewer receives current requirements + current evidence | I | Reviewer context contains current contract + artifact digest; not the creator's narrative |
| TRUST-03 | Remembered facts used in final output trace to sources | I | Packet sources list for the job; publication/summary path references; spot trace to `source_ref` |
| TRUST-04 | VERIFIED still means actual evidence passed | I | Forced failing evidence → verdict not VERIFIED (V1.2 tests preserved) |
| TRUST-05 | UNCERTAIN clearly states what remains unknown | U | `explain_failure` blocker + summary limitation bullet present |
| TRUST-06 | FAILED clearly states the failure | U | Failed branch of `explain_failure` intact |
| TRUST-07 | V1.2 provenance and verification summaries remain intact | I | Golden assertions from `test_v12_*` unchanged; new fields additive only |

## 7. PACKAGED (brief matrix → tests; run at G7 on the actual Kel.exe)

| Id | Scenario | Level |
|---|---|---|
| PKG-01 | Kel.exe opens | P |
| PKG-02 | KellShell starts | P |
| PKG-03 | Kel Runtime starts; engine version correct | P |
| PKG-04 | Existing V1.2 data loads (approvals, conversations, jobs) | P/L |
| PKG-05 | Project memory survives restart | P |
| PKG-06 | Continuation works through the packaged UI | P |
| PKG-07 | Work-context surfaces render without page errors | P |
| PKG-08 | Normal shutdown leaves zero orphan processes | P |
| PKG-09 | Relaunch succeeds | P |
| PKG-10 | Frozen V1.2 hashes remain unchanged | hash check |

## 8. Baseline retention and measurement

- Every gate re-runs the full engine suite; assertion: ≥ 181 passed + 10 subtests; no V1.2 test
  deleted or weakened.
- Packaging parity checks per ARCHITECTURE §10 at every packaging step.
- C4 measurement: before/after packet metrics on representative tasks (document, fix, research);
  results recorded in `KEL_V1.3_VERIFICATION_REPORT.md` at G7. **No savings claims without
  measurements.**

## 9. Coverage rule

Every acceptance item in the brief maps to ≥ 1 test id above (MEM-01..12, MAP-01..07, CTX-01..09,
CONT-01..11, REC-01..08, TRUST-01..07, PKG-01..10). Any item without a green test at G7 is a gate
failure and is tracked in the verification report — never silently dropped.


