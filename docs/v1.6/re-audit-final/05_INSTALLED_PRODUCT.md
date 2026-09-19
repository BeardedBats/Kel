# 05 — INSTALLED PRODUCT (final re-audit)

Independent install of THIS audit's freshly built installer at
`C:\Users\Nick\KelFinalAuditInstall`, with entirely separate data roots under
`C:\Users\Nick\KelFinalAuditRuns\`. Campaign B's and Campaign C's installs were not used as
primary evidence.

## Clean install battery

- Silent install via `ux-audit/r12-install.ps1` (first-party execution): **exit 0**; then a
  **manual reinstall-over** (raw installer `/S /D=…`): **exit 0**.
- Present after install: `Kel.exe`, `Uninstall Kel.exe`, `resources/kel-engine/KelEngine.exe`,
  `resources/app.asar`, bundled aioncore.
- Version identity: Kel · 1.6.0 everywhere checked (see `04_PACKAGE_IDENTITY.md`).
- Shortcuts: Desktop + Start Menu `Kel.lnk` created (`r12-install-result.json`).
- ARP: `Kel` / `1.6.0` / `Uninstall Kel.exe /currentuser` / DisplayIcon extracted
  (`evidence/ra-install-fresh/arp.txt`, `r12-exe-icon.png`).
- Installed engine hash = packaged = staged = built (`df4f0ee9…`).

## Fresh-run battery (installed app, isolated fresh root)

`ux-audit/r12-installed-probe.cjs` executed by this audit (Playwright) against a virgin data
root, gate script `ux-audit/r12-assert-gate.cjs` (hashes verified):

- `healthyBoot=true`, `engineVersion=1.6.0`, conversations present.
- `attentionVisible=true` ("Needs your attention" panel; "Nothing needs you right now."),
  `aboutLogoLoaded=true` (canonical K), `consoleErrors=[]`, `rawLeaks=[]`, all overflow checks 0.
- **GATE: PASS** (`evidence/ra-install-fresh/out/r12-installed.json`, screenshots
  `r12-work.png`, `r12-about.png`; probe log `probe.log`).

## Continuity (existing conversations preserved across reinstall-over)

- A marker message + submission were seeded into a copied fresh data root (offline seed script
  `probes/ra_seed_isolation.py`), then the installer was run **over** the same install while the
  data root stayed in place.
- Post-reinstall: conversations `[2c68da75…, main, …]` preserved; marker message present; engine
  still 1.6.0; 0 page/console errors. **5/5 checks PASS**
  (`evidence/ra-isolation/out/ra-stunt-results.json`, run log entries; bridge): see also
  `evidence/ra-install-fresh/reinstall-over.txt`.

## Isolation stunt (live cross-scope battery on the installed product)

`probes/ra-stunt.cjs isolation` — **12/12 checks PASS**, 0 page/console errors:

- Seeded fixtures: job+run+approval in `main` and in conversation B; marker message + submission
  in B.
- Conversation state: marker + submission visible only in B, absent from `main`; conversation
  list intact.
- **Approvals (live service routes):** foreign omission refused (`another conversation`),
  declared-main on foreign refused, owner settles (`approved`), duplicate refused
  (`does not match`), omission on main-owned reaches resolve — the AUD-MAJOR-001 property
  reproduced end-to-end on the installed product.
- Capability state: `web=off` set in `main` does not affect B (`A=off B=on`).
- Evidence: `evidence/ra-isolation/out/ra-stunt-results.json`, `run2.log`.

## Pet settings dead-control observation (objective, recorded; see RA-MINOR-003)

On `#/settings/pet`, the enable switch reads `false`, becomes `true` after a click and STAYS
true (main process persisted `false` and resolved silently), then re-syncs to `false` after a
route change. Screenshots: `ra-pet-before.png`, `ra-pet-after.png`, `ra-pet-reload.png`.
No pet window can be created; the security property of AUD-MINOR-008 holds.

## Recovery stunt (live installed journey)

`ux-audit/r10-engine-loss-probe.cjs` executed by this audit against the installed product and a
separate root — full journey captured in `evidence/ra-recovery/` (`run.log`,
`out/r10-engine-loss.json`, screenshots):

1. healthy boot (`engine=1.6.0`), durable seed recorded, conversations/projects captured.
2. **real engine kill** (`killed=9368`): link transitions `reconnecting(1) -> recovered(1)`,
   healthy again, NEW engine pid, seed item preserved, conversations preserved, version stable
   (recognition -> recovery verified live).
3. **engine restart made impossible** (binary held, `killed=13924`): link transitions
   `reconnecting(2) -> unrecoverable(2)`; the UI showed the honest failure state —
   "Kel couldn't recover on its own — The engine did not come back after 2 attempts. Close and
   open Kel, or try a restart below. Try to restart Kel's engine" (no fabricated completion).
4. **manual retry** (`manualRetryClicked=true`): `reconnecting(1) -> recovered(1)`;
   "Kel restarted successfully — The engine is back and your work is preserved."
   `engineHealthyAfterManual=true`, `newPidAfterManual=true`.
5. Hygiene: `pendingApprovalsLeft=0`, `jobsLeft=0`, `engineBootMarkers=0` — no blind replay
   residue; work preserved across both losses (`libraryHasSeedAfter=true`).

Result: **PASS** — honest failure + truthful retry + preservation, with screenshots retained.

## Uninstall battery (5-cycle matrix, first-party)

| Cycle | Invocation | Install dir | Shortcuts (desktop + start menu) | ARP | Data roots |
|---|---|---|---|---|---|
| 1 | `Uninstall Kel.exe /S` — **shell cwd inside install dir** | left (empty) | **left (dead)** | removed | retained |
| 2 | `Uninstall Kel.exe /currentuser /S` (the ARP-registered command) | fully removed | removed | removed | retained |
| 3 | bare `/S` from neutral cwd | fully removed | removed | removed | retained |
| 4 | **repeat of cycle 1** (cwd inside install dir) | left (empty) | **left (dead)** | removed | retained |
| 5 | bare `/S` with a held file handle inside the tree (neutral cwd) | fully removed | removed | removed | retained |

Deterministic conclusion: every supported/realistic invocation (including the ARP command and
a locked-file case) cleans everything; ONLY the harness condition of a foreign process
cwd-pinned inside the install directory (reproduced 2/2) leaves an empty dir + the two dead
shortcuts. Recorded as **RA-SUG-004** (robustness note; not a supported-flow defect).
Residual state from cycles 1/4 was cleaned by the audit; data roots (`fresh`, `iso`, `r10`)
retained as intended; ARP references to Kel: 0 after every cycle.


## Objective visual/functional observations (no subjective claims)

- Screenshots retained for: Work surface, About (logo loaded), Pet settings (before/after/reload).
- No raw transport errors, no console errors, no dead clicks observed in the exercised flows
  (pet toggle debounce aside — recorded as RA-MINOR-003).
- `HUMAN_VISUAL_GATE: PENDING` — Nick owns the subjective visual pass; this document only records
  objective conditions (overflow = 0, no console errors, canonical K loaded, no raw leaks).
