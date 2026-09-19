# 02 — REPAIR COMMITS (Campaign C)

Branch: `repair/v16-final` · Base: `a3490095889222862ea13b4b696166c0ddc5bf0f`
Rule: production commits carry the finding ID; raw evidence lives under `docs/v1.6/repair-final/evidence/`.

| # | Commit | Finding | Type | Summary |
|---|---|---|---|---|
| 0 | `a349009` (base) | — | — | Campaign B audit head (not a repair commit) |
| 1 | (initialization; see `git log` subject `docs(v1.6-repair): initialize`) | — | docs | Campaign C repair record initialized (binding, dispositions, evidence protocol, status, resume) |
| 2 | `44aee9f` | AUD-MAJOR-001 | fix | Unconditional approval conversation ownership (chat path + both service routes); discriminating tests; raw attack/focused/adjacent evidence |
| 3 | (this commit; see `git log` subject `docs(v1.6-repair): AUD-MAJOR-001 recorded`) | AUD-MAJOR-001 | docs | Disposition detail, commit ledger, regression evidence, status/resume, master-findings Campaign C field |
