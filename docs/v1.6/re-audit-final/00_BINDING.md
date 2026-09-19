# 00 — BINDING (Final independent post-repair re-audit)

Campaign D (this document set): independent verification of Campaign C, bound to the immutable
production target. NO repairs were made; this branch contains audit docs, probes and evidence only.

## Immutable production target

| Item | Value |
|---|---|
| Campaign A pre-audit RC | `08f56673ea93ed84568018937bb190e0a5acd71b` (unchanged; `ux/v15-journeys` clean) |
| Campaign B final audit head | `a3490095889222862ea13b4b696166c0ddc5bf0f` (unchanged; `audit/v16-final`) |
| **Campaign C production target** | **`05a076b`** (does not move) |
| Campaign C corpus tip | `7cf6030cc4d7bd28c4acf1b862661410ea04fc74` |
| Repair branch | `repair/v16-final` @ `7cf6030` (clean worktree) |
| Stable main | `5e76b21071a28601a7fb4de508cb3cf349c77db8` (= `origin/main`; v1.5.0 -> `5e76b21`) |
| Frozen tags | v1.5.0 obj `068cd267ff8bdccdffe5f13eb080eafc65f5a0b9`; v1.6.0-pre1 obj `ceac727ef2d04efdf96c4062a3d891825aefa176` -> `f24d9c28b09b30d7222691cdb1aafbe21d412672`; v1.2.0–v1.4.1 unchanged |
| Remote (`origin`) | `https://github.com/BeardedBats/Kel.git` — heads: main `5e76b21`, ux/v15-journeys `08f5667`, v1.3-dev, v1.4-dev |

Remote-state observation: `repair/v16-final` and `audit/v16-final` do not exist on `origin`
(local-only so far). No remote mutation was performed by this audit before its own final push.
This is recorded as an observation, not a discrepancy: no campaign claimed a remote push.

## Production-immutability proof (the §0 gate)

`git diff 05a076b..7cf6030` touches **10 paths, all under `docs/`** — repair records and evidence
plus the two RC-tip documentation files. **No production path changed after `05a076b`.**
`05a076b` is an ancestor of `7cf6030` (merge-base check). Evidence: `evidence/ra00-binding.txt`.

Files: `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md` (A),
`docs/v1.6/audit-final/MASTER_FINDINGS.md` (M), 7 × `docs/v1.6/repair-final/*.md` (M),
`docs/v1.6/repair-final/evidence/final-integrity-at-rc-tip.txt` (A).
Classification: documentation / evidence / repair records only — the corpus tip is admissible.

## Dedicated final re-audit worktree

- Path: `C:\Users\Nick\Desktop\Kel\kel-v16-postrepair-audit`
- Branch: `audit/v16-postrepair-final`, based on `7cf6030` (permitted: production tree at
  `7cf6030` == production tree at `05a076b`)
- This worktree contains **no production repairs**; only `docs/v1.6/re-audit-final/**`
  (probes, evidence, findings) plus untracked local build outputs (gitignored).

## Worktree state at binding time

| Worktree | HEAD | Status |
|---|---|---|
| `kel-v16-final-repair` (`repair/v16-final`) | `7cf6030` | clean |
| `Kel-Repo` (`main`) | `5e76b21` | only declared `.agents/`, `Agents.md` untracked |
| `kel-ux-v15` (`ux/v15-journeys`) | `08f5667` | clean |
| `kel-v16-final-audit` (`audit/v16-final`) | `a349009` | only declared `build-output/` untracked |
| `kel-v16-visual-fix` / `kel-v16-visual-audit` | `bc92f7f` / `4199ebb` | clean |

## Constraints honored

- No repair of any finding (this document set records, does not fix).
- Production target `05a076b` was not moved; `main` not moved; no release tag created; no freeze.
- `HUMAN_VISUAL_GATE = PENDING` (Nick's subjective gate remains separate).
- Scratch artifacts used during the audit (two temporary worktrees, two extra PyInstaller
  builds) were removed; the audit worktree carries no production mutation.
