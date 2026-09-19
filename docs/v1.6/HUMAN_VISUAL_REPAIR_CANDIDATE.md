# HUMAN VISUAL REPAIR CANDIDATE — Kel V1.6

- BASE PRODUCTION TARGET: `05a076b` (`05a076b3d723ab2c1f3666e6a42193dfc9e502e5`)
- FINAL PRE-REPAIR AUDIT HEAD: `eb4da52b40a2500daae12fe8740823d07a6ad1d8` (`audit/v16-postrepair-final`)
- REPAIR BRANCH: `repair/v16-human-visual` (worktree `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-fix`)
- HUMAN_VISUAL_REPAIR_HEAD: `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`
- Production commits: `14fc254`, `3df2176`, `d934a60`, `6b4e40d`, `9ad8a08`, `250597e`, `65bcaa3`, `6d957ee`
  (docs checkpoints `3be6b18`, `393640e`, `092409b` and the completion record commits follow)

## Human visual findings — disposition

| Finding | Disposition |
|---------|-------------|
| HV-01 global contrast (dark-on-dark) | Fixed at the theme boundary: `html/body` foreground token + `.kel-card` color pin + control inheritance; contrast scan 0 elements < 2.5:1 |
| HV-02 Permissions cannot scroll | Fixed: `.kel-scope` is the single scroll owner; wheel/PageDown/End/Home verified at 5 sizes |
| HV-03 Work → Open the chat → Home | Fixed: actions resolve the Kel conversation to its donor route id (`#/conversation/e59b9c7f` in the matrix; `#/conversation/3bdaab68` installed) |
| HV-04 sidebar black-square K / clipped badge | Fixed: canonical logo asset (same as About) + badge fully inside the sider (250 ≤ 261) |
| HV-05 drawer internal machinery | Fixed: plain-language statuses, state-appropriate actions, attention-first order, restyled trigger |
| HV-06 Permissions language + `Expires: 0s ago` | Fixed: Active permissions / Access requests language, advanced gating, new `formatUntil` (future-aware) |
| HV-07 Model page contradiction | Fixed: "Available models" (truthful badges) vs "Custom models" + "No custom models configured" |
| HV-08 System page hierarchy + donor path | Fixed: single data card + dividers; work/log folders behind an explicit advanced disclosure |
| HV-09 Appearance donor branding + typography | Fixed: donor cover removed (neutral generated preview); defaults markdown 16 / code 14 |
| HV-10 Tools donor naming | Fixed: built-in browser shows "Kel Browser" (internal id kept) |
| HV-11 Desktop Pet state lie (RA-MINOR-003) | Fixed: bridge refuses loudly; toggle settles to the authoritative state with a reason; reload consistent |
| HV-12 Team/workforce exposure | Hidden from ordinary navigation (routes redirect Home; settings/palette entries removed); Workforce runtime untouched |
| HV-13 installer donor strings (RA-MINOR-002/RA-SUG-002) | Fixed: 47 dialog strings + log/report/copyText/URLs + smokes; compile + report smoke PASS |
| HV-14 polish + responsive/readability | Applied across reviewed surfaces; no horizontal overflow at narrow sizes |

## Evidence

- Screenshot matrix (source): `docs/v1.6/human-visual-repair/evidence/matrix-final/` (all screens at 1440×960; Permissions top/mid/bottom at 5 sizes)
- Installed battery: `evidence/probe-installed.log` + `evidence/installed/` — all gates PASS, 0 console errors
- Audit battery: `KelVisualFixRuns/captures-installed-r12/r12-installed.json` — GATE PASS
- Permissions scroll: wheel/End/Home verified per size (see 03_VISUAL_EVIDENCE.md)
- Work → chat: PASS in both source-level and installed runs
- Desktop Pet: revert + reason + reload truthfulness (probe `petTruthful`, `petReload`)
- Donor brand: visible-text scan clean on all screens; legal attribution (AionUI-LICENSE / license headers) kept
- Console: 0 unexplained renderer errors in final runs
- Package identity: installer sha256 `0dc5dc36…`; engine `f525b15b…`; install at `C:\Users\Nick\KelVisualFixInstall`

## Remaining technical notes

- RA-MINOR-002 and RA-MINOR-003 are repaired in this pass and covered by tests.
- Internal-only donor residues retained deliberately: `kel-engine` / `bundled-aioncore` binary directory names,
  `AionUi` NSIS variable names, license/provenance files, non-visible temp identifiers. No user-visible donor
  naming remains on production-reachable surfaces (verified by scan + smokes).
- Installer behavior note recorded in 05: silent installs update a registered install in place and stop a
  running instance; a fresh dedicated path requires the registration keys to be clear first.

## Gates

- AUTOMATED_VISUAL_REPAIR = PASS (25/25 gates source + installed; audit R12 battery PASS)
- HUMAN_VISUAL_GATE = **PENDING_REVIEW** — Nick inspects the installed repair build; the agent does not self-approve
- Release / freeze = **NOT STARTED** (no tag, no merge, no publish)
