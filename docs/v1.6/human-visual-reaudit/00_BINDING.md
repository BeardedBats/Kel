# 00 — BINDING (V1.6 human-visual delta re-audit)

Independent final re-audit of the Kel V1.6 **HUMAN VISUAL REPAIR delta** only. The full V1.6
product had already passed Campaign B audit, Campaign C repair, and the final Campaign D
post-repair re-audit. This audit verifies ONLY the bounded human-visual repairs made after that
technical release gate.

Rules honored: no repairs, no redesign, no new scope, no release, no freeze.
`HUMAN_VISUAL_GATE = PENDING_NICK` (this audit cannot approve visual taste).

## Immutable targets

| Item | Value |
| --- | --- |
| Production audit target (immutable) | `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda` |
| Corpus head (branch/corpus tip) | `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` = `repair/v16-human-visual` |
| Pre-repair production target | `05a076b3d723ab2c1f3666e6a42193dfc9e502e5` |
| Pre-repair audit head | `eb4da52b40a2500daae12fe8740823d07a6ad1d8` |
| Stable main | `5e76b21071a28601a7fb4de508cb3cf349c77db8` (= `origin/main`) |

## Repository identity (verified at audit start)

- Source worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-fix`
  - branch `repair/v16-human-visual`, HEAD `37b1f27…`, worktree clean
- Remote: `origin` = `https://github.com/BeardedBats/Kel.git`
- Audit worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-reaudit`
  - branch `audit/v16-human-visual-final`, base `37b1f27…`, created at audit start

## Starting-integrity checks (all verified)

1. **Declared refs exist** — `6d957ee9…` ✓, `37b1f27…` ✓, `eb4da52b…` ✓, `05a076b3…` ✓.
2. **Ancestry** — `git merge-base 05a076b 6d957ee9` = `05a076b` and
   `git merge-base eb4da52b 6d957ee9` = `eb4da52b`: the target descends from both the pre-repair
   production commit and the pre-repair audit head. Commit chain in range:
   `05a076b → dbe42aa → ea61003 → 7cf6030 → eb4da52 → 3be6b18 → 14fc254 → 3df2176 → d934a60 →
   393640e → 6b4e40d → 092409b → 9ad8a08 → 250597e → 65bcaa3 → 6d957ee` (+ doc commits to `37b1f27`).
3. **Later-head containment** — `git diff 6d957ee9..37b1f27` contains **only** files under
   `docs/` (53 files, documentation + evidence). No production mutations exist after the target.
   Evidence: `evidence/post-repair-head-files.txt`.
4. **Stable main unchanged** — `main` = `5e76b210…` matches the Campaign D recorded value
   (`origin/main` = same).
5. **Prior audit branches unchanged** — `audit/v16-postrepair-final` = `eb4da52` (Campaign D),
   `audit/v16-final` = `a349009`, `ux/v15-journeys` = `08f5667`, `repair/v16-final` = `7cf6030`,
   `audit/v16-visual-ux` = `4199ebb`, `ux/v16-visual-fix` = `bc92f7f`, `audit/rust-runtime` =
   `9c1e7d0`, `v1.3-dev` = `dd67ef4`, `v1.4-dev` = `3645672`, `v1.4.1-dev` = `790752e` — all match
   Campaign D / prior records.
6. **Protected tags unchanged** — `v1.2.0` `7d69288…`, `v1.3.0` `05b0687…`, `v1.4.0` `ee5b907…`,
   `v1.4.1` `a6e6d92…`, `v1.5.0` `068cd26…`→`5e76b210…`, `v1.6.0-pre1` `ceac727…`→`f24d9c28…` —
   all match records. Evidence: `evidence/refs-audit-start.txt`.
7. **Target selection rule** — production tree at corpus head == production tree at `6d957ee9`
   (diffs are docs-only) ⇒ audit worktree may be based on the corpus head; production bindings
   (builds, installs) remain bound to `6d957ee9`.

## Production delta scope (`05a076b..6d957ee9`)

Production changes are confined to `desktop/`: **47 files (45 modified, 2 deleted)** across
8 fix commits — `14fc254`, `3df2176`, `d934a60`, `6b4e40d`, `9ad8a08`, `250597e`, `65bcaa3`,
`6d957ee`. No engine (`runtime/`) or other production tree is touched; the range's other
commits are documentation/evidence only. Full diff and file list:
`evidence/delta-desktop.diff`, `evidence/delta-desktop-files.txt` (also re-reviewed in
`01_DELTA_REVIEW.md`).

## Pre-existing artifact identities (recorded at audit start; comparison only — NOT primary proof)

- Campaign installer `kem…/dist/package-r12/Kel-1.6.0-win-x64.exe` — measured at audit start
  (see `04_PACKAGE_IDENTITY.md`; campaign-recorded `0dc5dc36…`).
- Staged engine (source worktree `dist/runtime/KelEngine/KelEngine.exe` and
  `kel-v16-final-repair` staged copy): `f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8`.
- Review install `C:\Users\Nick\KelVisualFixInstall`: engine `f525b15b…`, `Kel.exe`
  `28ad709821a3…` (full hash in `04_PACKAGE_IDENTITY.md`).
- Preserved audit install `C:\Users\Nick\KelV16ReviewInstall`: engine
  `df4f0ee991dfd5c0d74e54fffc9510ebf4948dd3d9050088f39561a33ea7e01f`, `Kel.exe` `f65b430a…`.
- Registry (`HKCU`) `InstallLocation` at audit start = `C:\Users\Nick\KelVisualFixInstall`;
  backups taken to `C:\Users\Nick\KelVisualReauditRuns\registry-backup\` before any mutation.

## Method (binding)

1. Replay all 14 human findings (HV-01…HV-14) via: full code review of the delta, the campaign
   harness re-run by this audit, plus independent probes added by this audit — executed first on
   a FRESH package built by this audit from the production target, then on a DEDICATED install
   (`C:\Users\Nick\KelVisualReauditInstall`) with isolated data
   (`C:\Users\Nick\KelVisualReauditRuns`). The campaign's review install is not primary proof.
2. Desktop regression in the audit worktree: TypeScript + full Vitest + focused repair tests.
3. Donor brand sweep (static + runtime) with legal/internal vs user-visible classification.
4. Package identity chain: source SHA → built renderer → staged engine → packaged engine →
   installer → installed files.
5. Findings recorded as `HVRA-BLOCK/MAJOR/MINOR/SUG`; nothing repaired. Final verdict in
   `FINAL_VERDICT.md`.

## Evidence index (this directory)

`evidence/refs-audit-start.txt`, `evidence/post-repair-head-files.txt`,
`evidence/delta-desktop-files.txt`, `evidence/delta-desktop.diff`, plus per-phase evidence added
later (regression logs, package identity, installed battery captures).
