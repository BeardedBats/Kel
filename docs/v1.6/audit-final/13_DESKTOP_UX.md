# 13 — DESKTOP / UX TRUTH

Audit target `08f56673…`. Scope discipline: objective checks only; **HUMAN_VISUAL_GATE = PENDING** (no pixel judgment is claimed by this audit).

## Objective checks executed

- **Boot / startup on the auditor-built installed package:** healthy boot, engine 1.6.0, first-run "Skip setup" path, `#/work` attention section present, `#/settings/about` canonical K renders, 0 console errors, 0 raw leaks, 0 horizontal overflow on 5 routes (evidence: `evidence/auditor-installed-probe*`).
- **Packaged identity surfaces:** exe icon/metadata (`Kel`), installer icon config (`kel-builder.json` nsis icons), ARP metadata `Kel · 1.6.0 · Kel` (install test), shortcuts created/removed cleanly.
- **IPC/desktop boundary:** per-channel sender-frame coverage audited → **AUD-MAJOR-002** (credential trio / feedback pair / sendSync / recovery channel / generic adapter dispatcher unguarded; 8 Kel channels guarded).
- **Engine-loss surfaces:** honest states reviewed via R10 evidence + the `engineFailure.ts` classifier (transport text confined to Technical details; unit-pinned) — see 11/14.
- **Donor/desktop feature surfaces reachable in the shipped app:** desktop-pet subsystem wired (`createPetWindow`, settings APIs, `pet-states` shipped) → **AUD-MINOR-008**; WebUI lifecycle bridge (start/stop/status + initial password) exists and is reachable through the donor bridge surface; aioncore runtime is live → **AUD-MINOR-007**.

## Not performed (recorded honestly)

- A systematic dead-control/no-op sweep of every rendered button/route (would require the human/visual harness; the visual track's automated captures + HIDE_DONOR_AGENT_SURFACES guards were reviewed but a control-by-control inventory was not rebuilt this cycle).
- Subjective layout/typography/contrast judgment (human gate, explicitly separate).

## Known items already in the ledger

- `AUD-MINOR-004` (R12 evidence precision), `AUD-MINOR-005` (corpus drift incl. the stale `00_STATUS.md` copy in the RC tree), `AUD-SUG-001` (directive docstring), `AUD-MAJOR-001` (approvals scope).
