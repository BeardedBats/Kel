# PRE_AUDIT_RELEASE_CANDIDATE — Kel V1.6, Campaign A

**PRE_AUDIT_V1_6_HEAD**: the commit that finalizes this pre-audit corpus — resolve it exactly with:

```
git log --format=%H -n1 --grep='PRE_AUDIT_V1_6_HEAD' --fixed-strings
```

(The resolving commit's message begins `docs(v1.6): PRE_AUDIT_V1_6_HEAD —`; the same SHA is
recorded in the handoff response. This indirection exists because a commit cannot contain its own
hash; an empty follow-up commit was not used.)

## State at RC

| Item | Value |
|---|---|
| Branch | `ux/v15-journeys` (integration branch; NOT `main`) |
| Last independently audited production | `8a2b25d` |
| First unaudited Campaign A production | `22f4a3e` |
| Unaudited range | `8a2b25d..PRE_AUDIT_V1_6_HEAD` (production starts at `22f4a3e`) |
| Phases | R0–R12 COMPLETE; REL-01 CLOSED (`93b99b5`) |
| Visual lane | integrated at `7267630` (batches 1–8 + R9.D + R10 supervision; lane tip `bc92f7f`) |
| Findings denominator | 26 canonical P2/P3 rows (P2 10, P3 16); the 27-vs-26 question reconciled in `P2_P3_DISPOSITION.md` §Denominator reconciliation (every original finding ID mapped) |

## Batteries at RC (evidence indexes hold the raw lines)

- **Engine**: full suite **998 passed + 10 subtests** (284.53s) on the merged tree
  (`ux-audit/r12-engine-suite.log`); includes fresh DB, upgrade DB, all V1.6 migrations,
  authority, approvals, leases, idempotency, effects, retry-durable, persist-canonical,
  liveness, recovery, memory, continuation, providers, routing, D1–D3, assurance, learning,
  evidence, completion, lineage, vetting, transcription, restore, release identity.
- **Desktop**: `tsc` 0; Vitest **122/122** (12 files) on the merged tree.
- **Packaged (from merged Main)**: `dist/package-r12` —
  `Kel-1.6.0-win-x64.exe` (NSIS, stock template; exit-0 silent install) + `win-unpacked`;
  bundled engine = the frozen 1.6.0 runtime, SHA-256
  `69123AF001B8DF7E98FD092E751437044AFF43CA085B0161E45CA08B62AA3AB1`;
  exe metadata `ProductName=Kel · CompanyName=Kel · FileVersion=1.6.0 · ProductVersion=1.6.0.0`;
  Add/Remove Programs `DisplayName=Kel · Publisher=Kel · DisplayVersion=1.6.0`.
- **Packaged journeys**: R10 engine-loss/recovery (`ux-audit/runs/r10-{f,g}`; link log; 7
  screenshots; DOM leak scan clean; console 0); R12 installed probes — fresh
  (`runs/r12-fresh2`) and upgrade-DB (`runs/r12-upgrade`): healthy, engine 1.6.0, R9.D
  "Needs your attention" present, About canonical K renders, zero raw leaks, zero console
  errors, zero horizontal overflow on five routes; installer lifecycle verified
  (install → use → uninstall → registry/shortcuts cleaned).
- **Failure injection**: R10 packaged kills (loss, repeat loss, restart-impossible, manual
  retry) + the engine suite's named hostile files — `test_v16_r2_idempotency`,
  `test_v16_r4_approval_exact`, `test_v16_r5_persistence`, `test_v16_r6_liveness`,
  `test_v16_r7_credentials`, `test_v16_r8_identity`/`_migrations`, `test_v16_restore_visibility`,
  `test_v16_r1_authority`, `test_v16_approvals`, `test_workforce_d1/d2/…` (see
  TEST_EVIDENCE_INDEX A-29).
- **Release integrity** (`ux-audit/runs/r12-integrity.txt`): branch correct; worktree clean;
  remote exact (`main` `5e76b21`, journey at RC tip); no force push (all pushes fast-forward
  `0aadd42..12f87a7`); secret scan actionable hits **0**; frozen refs unchanged —
  `v1.5.0^{}` `5e76b21`, `v1.6.0-pre1^{}` `f24d9c2`; older freezes untouched.

## Human gate (never claimed)

- **Human Visual: PENDING** — screenshots are produced and indexed; no agent performs pixel
  approval (`r10-g`/`r10-f` captures, `r12-work.png`, `r12-about.png`, `r12-exe-icon.png`).
- Provider reality: validation runs as access allows (`PROVIDER_VALIDATION_MATRIX.md`; LIM-14).

## Out of scope at RC (by directive)

Campaign B (independent audit), Campaign C, final release freeze, moving `main`, the final
V1.6 release tag. `PRE_AUDIT_V1_6_HEAD` is a handoff pointer, not a release.
