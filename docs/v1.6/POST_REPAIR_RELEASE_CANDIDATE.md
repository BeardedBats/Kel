# KEL V1.6 — POST-REPAIR RELEASE CANDIDATE

**POST_REPAIR_V1_6_HEAD = `05a076b`** (production head: the C-DISC-001 installer fix).
The corpus-records commits (including this file) sit directly on top; nothing after `05a076b`
changes production code.

## Lineage
- Campaign A RC (pre-audit): `08f56673ea93ed84568018937bb190e0a5acd71b`
- Campaign B audit head (repair base): `a3490095889222862ea13b4b696166c0ddc5bf0f`
- Campaign C branch: `repair/v16-final`
- Repair range (production): `a3490095889222862ea13b4b696166c0ddc5bf0f..05a076b`
- Corpus/records tip: see `git log --oneline -1` (this RC record + the final integrity record).

## Findings (Campaign B) — 12/12 dispositioned
| ID | Disposition | Commit |
|---|---|---|
| AUD-MAJOR-001 Chat-approval conversation scoping | REPAIRED | `44aee9f` |
| AUD-MAJOR-002 Privileged IPC sender validation | REPAIRED | `eaf7bad` |
| AUD-MINOR-001 Commit-ledger completeness | REPAIRED | `960e023` |
| AUD-MINOR-002 Budget reservation aggregation | REPAIRED | `7e293ba` |
| AUD-MINOR-003 Native child credential containment | REPAIRED | `91bd869` |
| AUD-MINOR-004 R12 packaged-evidence integrity | REPAIRED | `89ab6ad` |
| AUD-MINOR-005 Corpus state drift | REPAIRED | `8ca6231` |
| AUD-MINOR-006 Path containment (`..`) | REPAIRED | `c056a8a` |
| AUD-MINOR-007 Donor runtime disposition | REPAIRED | `197dbff` |
| AUD-MINOR-008 Desktop-pet subsystem | REPAIRED | `197dbff` |
| AUD-MINOR-009 Builder config | REPAIRED | `197dbff` |
| AUD-SUG-001 Directive docstring vs behavior | REPAIRED | `6d665b2` |

Campaign C discovered: **C-DISC-001** (installer registration E1010) — REPAIRED `05a076b`;
preserved for the final independent re-audit.

## Battery results
- Engine: **1019 passed + 10 subtests** in 353.40s (`repair-final/evidence/final-engine-suite.txt`).
- Desktop TypeScript: `tsc --noEmit` **exit 0**; Desktop Vitest: **152/152** (15 files).
- Campaign B attack replay at the final head: probe-1 to `PROBE-END`; A2 refused; E5 refused;
  **E7 refused** (budget aggregation); **G4 DeepSeek absent** from both native children.
- Package (fresh build from the production head): installer `Kel-1.6.0-win-x64.exe` sha256
  `88a1b4761db5ba2ee6c507e7626e08e969cc5da004036efcbf5d42a87ff5124c`; packaged engine == staged
  (`f525b15b…`); aioncore provenance `67eb0277…` (`04_PACKAGE_EVIDENCE.md`).
- Installed validation (`C:\Users\Nick\KelRepairInstall`): fresh **GATE PASS**; continuity store
  **GATE PASS** (schema 21, conversations preserved); reinstall EXIT=0; uninstall exit 0 with
  data retained; ARP/shortcuts verified (`evidence/installed-*`).
- Migration/persistence: fresh chain + RC-era store continuity verified on the installed build;
  R8 migration suite in the engine battery; `MIGRATION_LEDGER` reconciled (max 21, next free 22).
- Project/conversation isolation: covered by the engine battery suites (projects, conversations,
  leases, idempotency) and the installed continuity probe.
- Credential containment: native children strip all non-own provider keys; probe G4 verified.

## Residual risks
See `repair-final/05_REMAINING_RISKS.md` (re-audit items: `/api/state` read surface,
`/api/autonomy` by-id resolve, guard-semantics scope, run-slot vs planning accounting,
dispatcher retention, system-tool env inheritance, donor exe metadata, inert pet assets, C-DISC
lineage).

## Status
- Repair corpus: `docs/v1.6/repair-final/` (00–06 + status/resume + evidence).
- Campaign B corpus preserved; Campaign C results appended to `audit-final/MASTER_FINDINGS.md`.
- Human Visual: **PENDING** · Final independent re-audit: **NOT STARTED** ·
  Release/freeze: **NOT STARTED** · Frozen refs: **UNCHANGED**.
