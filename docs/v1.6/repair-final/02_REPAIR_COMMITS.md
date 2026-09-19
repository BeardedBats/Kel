# 02 — REPAIR COMMITS (Campaign C)

Branch: `repair/v16-final` · Base: `a3490095889222862ea13b4b696166c0ddc5bf0f`
Rule: production commits carry the finding ID; raw evidence lives under `docs/v1.6/repair-final/evidence/`.

| # | Commit | Finding | Type | Summary |
|---|---|---|---|---|
| 0 | `a349009` (base) | — | — | Campaign B audit head (not a repair commit) |
| 1 | (initialization; see `git log` subject `docs(v1.6-repair): initialize`) | — | docs | Campaign C repair record initialized (binding, dispositions, evidence protocol, status, resume) |
| 2 | `44aee9f` | AUD-MAJOR-001 | fix | Unconditional approval conversation ownership (chat path + both service routes); discriminating tests; raw attack/focused/adjacent evidence |
| 3 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MAJOR-001 recorded`) | AUD-MAJOR-001 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 4 | `eaf7bad` | AUD-MAJOR-002 | fix | One shared sender guard on every privileged IPC channel (Kel trio, feedback trio, sendSync + recovery, adapter dispatcher); per-channel refusal tests |
| 5 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MAJOR-002 recorded`) | AUD-MAJOR-002 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 6 | `7e293ba` | AUD-MINOR-002 | fix | Budget reservations aggregate against the job envelope (un-released reservations narrow it); discriminating cumulative tests |
| 7 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-002 recorded`) | AUD-MINOR-002 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 8 | `91bd869` | AUD-MINOR-003 | fix | Native child envs strip every other provider credential via the canonical key set; discriminating tests |
| 9 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-003 recorded`) | AUD-MINOR-003 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 10 | `c056a8a` | AUD-MINOR-006 | fix | Delegation containment resolves `..` lexically (workforce._path_within); traversal table + e2e refusal tests |
| 11 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-006 recorded`) | AUD-MINOR-006 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 12 | `960e023` | AUD-MINOR-001 | fix | COMMIT_LEDGER reconciled 1:1 (rows added, malformed cells fixed) + failing gate script |
| 13 | `89ab6ad` | AUD-MINOR-004 | fix | R12 probe assertion gate (exit non-zero), integrity --fail-on-dirty, R10 wording, 04 checklist, evidence |
| 14 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-001 + AUD-MINOR-004 recorded`) | AUD-MINOR-001 / AUD-MINOR-004 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C fields |
| 15 | `8ca6231` | AUD-MINOR-005 | fix | Corpus reconciliation (6 files) + staleness gate + pre/post evidence |
| 16 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-005 recorded`) | AUD-MINOR-005 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 17 | `197dbff` | AUD-MINOR-007 / 008 / 009 | fix | Donor-cluster dispositions: aioncore provenance binding (KEEP); pet subsystem disabled by policy; Kel build config default + identity assertion; tests + 06 doc |
| 18 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MINOR-007/008/009 recorded`) | AUD-MINOR-007 / 008 / 009 | docs | Disposition rows + details, commit ledger, regression evidence, status/resume, master-findings Campaign C fields |
| 19 | `6d665b2` | AUD-SUG-001 | fix | Directive docstring aligned to parser behavior + conformance table; behavior unchanged |
| 20 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-SUG-001 recorded`) | AUD-SUG-001 | docs | Disposition row + detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
| 21 | `05a076b` | C-DISC-001 | fix | Installer payload check: donor-hardcoded `AionUi.exe` -> single-source `Kel.exe` define; rebuilt v3; installed battery green |
| 22 | (this commit; see `git log` subject `docs(v1.6-repair): completion records`) | completion | docs | 04 package checklist complete; §16/§17/§18/§19 records; C-DISC-001 recorded; MASTER Campaign C discovered section; status/resume |
