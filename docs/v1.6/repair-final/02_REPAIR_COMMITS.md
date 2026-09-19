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
