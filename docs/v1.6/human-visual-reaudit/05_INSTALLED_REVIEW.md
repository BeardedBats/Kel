# 05 — INSTALLED REVIEW (dedicated audit install)

## Dedicated install

- Artifact: fresh re-audit installer `dist/package-r12/Kel-1.6.0-win-x64.exe`
  (sha256 `170df43843e577723918b0a3ee8dbf4f9318c871a9db28cf9126f3ec3b9ced8d`, 213,615,918 bytes).
- Location: `C:\Users\Nick\KelVisualReauditInstall` (fresh path; registration keys cleared first,
  backups at `C:\Users\Nick\KelVisualReauditRuns\registry-backup\`).
- Result: INSTALL_EXIT=0. Installed `Kel.exe` sha256
  `E7AFA62DD74B6F6CA434A6A3FBA557BB20345E0B09A15C1FFE7040A3E0FDDAB5` — byte-identical to the built
  package (`04_PACKAGE_IDENTITY.md`); engine `f525b15b…`; version 1.6.0.0; registry InstallLocation
  → the re-audit install (at install time).
- Data root (isolated): `C:\Users\Nick\KelVisualReauditRuns\prepared` (copy of the review-seeded
  profile; manifest-verified; re-synced from the master before this phase).
- Evidence: `evidence/install-reaudit.txt`, `evidence/installer-metadata.txt`.

## Installed battery — results

| Battery | Result | Evidence |
| --- | --- | --- |
| Campaign matrix re-run (25 gates) | **25/25 PASS, 0 console errors** — badge right 250 ≤ 261; scroll 150/56/56/56/139; pet truthful + reload OFF; team → home; about logo 1024; narrow overflow 0 | `evidence/probes-installed/kelvis/kelvis-verify.json` (+ screenshots) |
| Independent probes (same 16 groups as source phase) | **Full parity**: scroll incl. PageUp/PageDown all sizes; workToChat 3× → `#/conversation/3bdaab68` + back/forward sane; model 2 available / 3 needs-setup; system donor path hidden → shown after expand (by design); theme switching works; pet OFF + message + reload OFF; all 8 hidden routes → `#/guid`; donor window sweep hits **[]**; overflow 0 everywhere incl. 125% emulation; console 0 / page errors 0 | `evidence/probes-installed/own/reaudit-probes.json` (+ summary, screenshots) |
| Installed engine probe (campaign tool, re-run) | `healthy:true engine:1.6.0 attention:true aboutLogo:true leaks:[] errors:0 overflow all 0` | `evidence/probes-installed/r12/r12-installed.json` |

Renderer console — installed: **0 errors** (expected `0 unexplained errors`: met).

## Preservation + restoration (no disturbance left behind)

- Preserved audit install `KelV16ReviewInstall`: re-hashed after all runs — `f65b430a…` / engine
  `df4f0ee9…` (unchanged vs pre-audit). Not touched by any phase.
- Review install `KelVisualFixInstall`: `28ad7098…` / engine `f525b15b…` (unchanged). Registration
  backed up before the audit install and restored after: `InstallLocation` → `KelVisualFixInstall`.
- Desktop + Start-Menu `Kel` shortcuts re-pointed to `C:\Users\Nick\KelVisualFixInstall\Kel.exe`
  (the review install) — the pre-audit target.
- The audit install (`KelVisualReauditInstall`) remains on disk as the audit artifact (files
  untouched; unregistered after the restore — do not run its `Uninstall Kel.exe` post-restore, as
  it would clear the restored review-install registration; delete the folder manually if removal
  is ever wanted).
- Evidence: `evidence/preservation-pre-install.txt`, `evidence/preservation-restore.txt`.

## Operational notes (audit tooling; no product impact)

- The campaign's matrix harness (kelvis) completes all gates + JSON but can hang at teardown,
  leaving an orphan `KelEngine.exe`; this audit killed it after JSON capture (results complete,
  unaffected).
- The re-audit probe needed two audit-tooling fixes during development (donor-map orientation;
  DOM click helpers). Runs 1–2 partial JSONs are kept in
  `evidence/probes-source/own/reaudit-probes-run{1,2}-partial.json`.
- One probe-incident HTTP 404 (from the audit's own invalid `#/conversation/undefined` navigation)
  appeared in run 1 only; run 2/3 (fixed) and both installed runs show 0 console/http errors.
- “Skills”/“Agents” settings entries are intentionally absent post-repair (HV-12); the battery
  item “Skills” is satisfied by: nav removed + `#/settings/skills-hub` → `#/guid`.
