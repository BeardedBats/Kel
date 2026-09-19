# 01 — REPAIR REPLAY (final re-audit)

Every Campaign B finding was independently re-attacked on the fixed production tree
(`7cf6030`; production tree == `05a076b`), plus Campaign C's own discovery C-DISC-001.
Campaign C's PASS claims were treated as evidence to verify, never as the authority.

## Campaign B findings — final dispositions

| ID | Severity | Defect (Campaign B) | Repair commit | This audit's replay | Verdict |
|---|---|---|---|---|---|
| AUD-MAJOR-001 | MAJOR | approval resolution scoped only when declared; omission settled any conversation; legacy route unscoped | `44aee9f` | 24/24 first-party attacks incl. omission/declared-foreign/malformed/duplicate/expired/jobless/access-kind + both service routes; pre-fix negative control fails 5 tests (`evidence/ra-attack-major1.txt`, `ra-negctl-engine-prefix.txt`) | **VERIFIED_CLOSED** |
| AUD-MAJOR-002 | MAJOR | non-uniform IPC sender guards; dispatcher/credential trio/feedback/sendSync/recovery unguarded | `eaf7bad` | whole-tree enumeration (29 registrations; all guarded or unreachable) + suite + allow-all mutation replay 19F/11P (`02_SECURITY_AUTHORITY.md`, `ra-negctl-desktop-mutation.txt`) | **VERIFIED_CLOSED** |
| AUD-MINOR-001 | MINOR | COMMIT_LEDGER not 1:1 with git; placeholders | `960e023` (+checker) | ran the gate: `PASS — 73 commits, every row well-formed, 1:1` | **VERIFIED_CLOSED** |
| AUD-MINOR-002 | MINOR | budget reservations did not aggregate; successive reservations passed alone | `7e293ba` | sequential battery C1–C7 green incl. boundary/restart/disjoint; negative control 4 tests fail pre-fix. **New finding RA-MINOR-001** (non-atomic under concurrency; dormant) | **PARTIALLY_CLOSED** — sequential class closed; concurrency defect recorded as new finding |
| AUD-MINOR-003 | MINOR | native children received every provider's key | `91bd869` | sentinel battery D1–D6 incl. real subprocess spawn on the production adapter path; negative control 3 tests fail pre-fix | **VERIFIED_CLOSED** |
| AUD-MINOR-004 | MINOR | R12 evidence gates not discriminating | `89ab6ad` (tools) | re-gated their known-bad run → FAIL exit 1; known-good → PASS; own mutation probe on repaired JSON → FAIL on each mutation | **VERIFIED_CLOSED** |
| AUD-MINOR-005 | MINOR | corpus status cells / migration claims stale | `8ca6231` | corpus lint PASS; fresh-DB migration max = 21 (next free 22) verified from code+DB | **VERIFIED_CLOSED** |
| AUD-MINOR-006 | MINOR | `..` not lexically resolved in delegation containment | `c056a8a` | 26-case concrete-root battery + `authority_within` matrix green; negative control 3 tests fail pre-fix. **New finding RA-SUG-001** (universal-root wording/boundary note) | **VERIFIED_CLOSED** |
| AUD-MINOR-007 | MINOR | aioncore runtime shipped without Kel-side provenance | `197dbff` | fresh build re-exercised the provenance writer; packaged `provenance.json` sha256 `67eb0277…` == reference, bytes match (`04_PACKAGE_IDENTITY.md`) | **VERIFIED_CLOSED** |
| AUD-MINOR-008 | MINOR | donor pet subsystem reachable; settings could enable | `197dbff` | `KEL_PET_SUBSYSTEM_ENABLED=false`; `createPetWindow` refuses; `setPetEnabled` refuses; handlers never register; donor-policy tests + mutation replay catch it | **VERIFIED_CLOSED** |
| AUD-MINOR-009 | MINOR | builder defaulted to donor config; Kel packaging required manual flag | `197dbff` | `KEL_BUILDER_CONFIG='kel-builder.json'` default; this audit's build ran the documented command and produced the NSIS installer with the identity assert `Build identity: Kel -> com.kel.kel.desktop` (`04_PACKAGE_IDENTITY.md`) | **VERIFIED_CLOSED** |
| AUD-SUG-001 | SUG | directive docstring did not match parser behavior | `6d665b2` | 18-case firing matrix + multi-clause order green against the reworded docstring (`ra-attack-major2.txt` F1/F2) | **VERIFIED_CLOSED** |
| C-DISC-001 | (Campaign C discovery) | script-built NSIS registration aborted: payload check expected donor `AionUi.exe` while Kel ships `Kel.exe` (E1010) | `05a076b` | pre/post logic verified from history (`ra-cdisc001.txt`); this audit's fresh package installed with exit 0 (fresh + reinstall-over), engine hash chain identical, E1010 regime gone — see `04`/`05` | **VERIFIED_CLOSED** |

## Summary (final)

- VERIFIED_CLOSED: 11 of the 12 Campaign B findings (all except AUD-MINOR-002)
- PARTIALLY_CLOSED: 1 — AUD-MINOR-002 (the reported sequential defect is closed; a sibling
  concurrency defect is recorded as RA-MINOR-001, dormant in V1.6 as shipped)
- STILL_REPRODUCES / REGRESSION_INTRODUCED / INCONCLUSIVE: 0 (none observed)
- C-DISC-001: VERIFIED_CLOSED
- New final findings: RA-MINOR ×3 (partitioned exactly as listed in `07_FINAL_FINDINGS.md`;
  AUD-MINOR-002's partial closure corresponds to RA-MINOR-001), RA-SUG ×4.
