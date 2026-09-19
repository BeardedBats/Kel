# 01 — REPOSITORY INTEGRITY (Pass 0)

Campaign B — independent audit of Kel V1.6. Status: **IN PROGRESS** (deep per-commit review continues in `02_COMMIT_COVERAGE.md`).
All statements below were produced by direct git inspection on 2026-09-19 (main worktree `kel-ux-v15`, remote `origin`, and the audit worktree `kel-v16-final-audit`).

## 1. Target identity — VERIFIED

| Item | Observed |
|---|---|
| Target SHA | `08f56673ea93ed84568018937bb190e0a5acd71b` |
| Subject | `docs(v1.6): PRE_AUDIT_V1_6_HEAD — Campaign A complete; pre-audit release candidate ready` |
| Date / parent | 2026-09-18 20:52:11 -0400 / `12f87a7f0da3c9a3a9040182e796aa2193256621` |
| Branch | `ux/v15-journeys` — local == `origin/ux/v15-journeys` == authoritative `git ls-remote` == target |
| Ancestors | `8a2b25d` (last audited) VERIFIED ancestor; `22f4a3e` (first unaudited production) VERIFIED ancestor |
| Worktree state | clean at binding (no staged/unstaged/untracked; no stashes) |
| Remote | `origin` = https://github.com/BeardedBats/Kel.git |

No audit-integrity discrepancy at target identity level.

## 2. Declared range vs git truth

- Declared: `8a2b25d..08f5667`. Observed: **73 commits** (57 first-parent; 2 merges: `3050761` lane re-anchor, `7267630` R11 integration). Production subset from `22f4a3e`: 68 commits.
- Mechanical classification of all 73 commits (`evidence/commit-classification.tsv`, `evidence/commit-file-lists.txt`): **33 DOCS / 37 PROD / 3 TEST**.
- Range-level diff: **189 files changed, +14,424 / −615** (`evidence/git-range-*`).

## 3. Frozen refs — observed vs documented

| Ref | Documented expectation (RC corpus) | Observed | Status |
|---|---|---|---|
| `main` | `5e76b21` | `5e76b21071a28601a7fb4de508cb3cf349c77db8` (local == origin) | MATCH |
| `v1.5.0^{}` | `5e76b21` | tag object `068cd267ff8bdccdffe5f13eb080eafc65f5a0b9` → `5e76b21` | MATCH |
| `v1.6.0-pre1^{}` | `f24d9c2` | tag object `ceac727ef2d04efdf96c4062a3d891825aefa176` → `f24d9c28b09b30d7222691cdb1aafbe21d412672` | MATCH |
| `v1.2.0`/`v1.3.0`/`v1.4.0`/`v1.4.1` | protected, byte-untouched | tags present (`7d69288`/`05b0687`/`ee5b907`/`a6e6d92`); artifact-level re-verification pending (see §7) | RECORDED |
| v1.6.0-pre1 artifact source | `0fb095f` (full: `0fb095fec1d2e8bd640c205c9d6f4f5ab0430fb7`) | existence/ancestry check pending in artifact pass | PENDING |

Weakness noted: the registry uses **abbreviated hashes** in most places (auditability weakness — see findings candidates). The RC never claims `main` moved; `main` still holds v1.5.0, consistent with GITHUB_SYNC_POLICY.

## 4. Ledger coverage — COMMIT_LEDGER vs git (mechanical reconciliation)

Evidence: `evidence/ledger-vs-git.txt` (scripted, reproducible).

- Ledger hex tokens: 69 — all resolve to real commits; 68 in-range; 0 unresolved/phantom rows. No "row with no commit" beyond two malformed placeholder rows (below).
- **Commits in the declared range NOT mentioned anywhere in `COMMIT_LEDGER.md`:**
  1. `022f3ac` — `test(v1.6): engine-version assertion follows the single source (R8.B follow-up)` — test-only (`runtime/tests/test_v141_boundaries.py`).
  2. `0aadd42` — `docs(v1.6): R7–R8 breadcrumbs` (10 docs files). The ledger instead carries a placeholder row labeled **`HEAD`** whose parent cell reads `93b99b5` — the actual commit `0aadd42` has parent `022f3ac`. (Misbound row.)
  3. `34947f0` — `feat(v1.6-visual): R10 prep — [KEL-LINK] transition log beside the engine log` — **production change** (`desktop/.../kel/KelService.ts`, +10 lines). Absent from the ledger entirely; also not listed under CHG-024/CHG-028 commit lists in `CHANGE_LEDGER.md`.
  4. `12f87a7` — `docs(v1.6): R11 records — integration breadcrumb, ledgers, requirements, visual index, status` (7 docs files). Absent.
  5. `08f5667` — the RC commit itself. Expected-absent by the documented hash indirection, **but it is not docs-only**: it also changes `desktop/kel-builder.json` (builder output dir `../dist/package` → `../dist/package-r12`) and `desktop/package.json` (adds `companyName: "Kel"`; `author.name` `AionUi` → `Kel`; author email remains `service@aionui.com`). Production-affecting packaging edits travel under a `docs(v1.6):` subject and are not accounted anywhere in the ledgers.
- Row **`R6 tests+record`** carries no SHA (second cell = `b2ffed1` is the *parent*); the actual commit is `e8bbb05`, which added `runtime/tests/test_v16_r6_liveness.py` alongside docs.
- Ledger's own rule: "EVERY production-affecting commit in this range must appear here." Violations: `34947f0` and the RC commit's packaging edits (production-affecting, unlisted); plus 3 unlisted docs/test commits and 2 malformed rows. → Recorded as **AUD-MINOR-001** in `MASTER_FINDINGS.md`.

## 5. Evidence-snapshot consistency (release integrity)

- `ux-audit/runs/r12-integrity.txt` header says `-- worktree status (expect empty)` but the recorded status shows `M desktop/kel-builder.json` / `M desktop/package.json` — i.e., the RC-head integrity snapshot was captured with uncommitted packaging edits present (they were subsequently committed into the RC head, per its commit message). The script never fails on unexpected status (it only records). See §7 findings candidates (evidence-quality pass).
- Secret scan recorded `actionable_hits=0` over `8a2b25d..HEAD`; independent re-run pending in the security pass.

## 6. Tree hygiene / immutability (continuous)

- RC worktree `kel-ux-v15`: clean; HEAD == target; branch `ux/v15-journeys`; re-checked after every audit operation. `main` untouched at `5e76b21`; no force-push (fetches clean; remote refs exact).
- Audit worktree `kel-v16-final-audit`: branch `audit/v16-final`, advances with audit records only. No production file has been modified anywhere by this audit.

## 7. Open integrity items (continuing)

1. Frozen-folder artifact hash spot-checks (`Kel Releases/Kel-V1.5-Frozen`, `Kel-V1.6.0-Pre1-Frozen`) — in progress.
2. Per-commit deep review — `02_COMMIT_COVERAGE.md` (73/73 table with diffs reviewed).
3. File-level coverage — `03_FILE_COVERAGE.md` (189 files).
4. Independent re-run of engine suite + desktop suites + packaged probes (Campaign A counts are evidence, not truth) — see `18_TEST_QUALITY.md`.
