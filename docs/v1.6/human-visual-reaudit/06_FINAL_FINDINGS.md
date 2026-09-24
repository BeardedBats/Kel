# 06 — FINAL FINDINGS (V1.6 human-visual delta re-audit)

Nothing below was repaired — recorded only, per instruction. IDs: HVRA-BLOCK/MAJOR/MINOR/SUG.

## Counts

- HVRA-BLOCK: **0**
- HVRA-MAJOR: **0**
- HVRA-MINOR: **2** (MINOR-001, MINOR-002)
- HVRA-SUG: **2** (SUG-001, SUG-002)

## HVRA-MINOR-001 — Raw engine job id remains on the primary Permissions surface

- Repro: open Permissions (`#/autonomy`) on a profile with an active lease — the Active-permissions
  table's primary "Work" column renders the raw engine job id (`job_review_summary`).
- Evidence: `evidence/probes-source/own/reaudit-probes.json` → `permissionsLanguage.jobIdMatches`,
  `permissionsRows`; reproduces in `evidence/probes-installed/own/reaudit-probes.json`;
  screenshots `permissions-language-top.png` (source + installed).
- Affected repair: HV-06 — the human finding explicitly cited `job_review_summary` as internal
  vocabulary on the primary surface. Relabeling, advanced gating and expiry fixes landed; this
  value class remains.
- Expected: user-meaningful work reference (e.g., the request/conversation title) in the primary
  column; raw id only in advanced/copy detail.
- Actual: `job_review_summary` rendered as the Work value.
- Release impact: cosmetic/informational only — no security, function, or authorization impact.
- Acceptance criteria: primary column shows a human label (or hides the id behind Advanced
  details); id remains available for support.
- Graded MINOR (not MAJOR): single cosmetic string class; no functional/security impact.

## HVRA-MINOR-002 — Installer & uninstaller FileDescription contains donor name

- Repro: right-click `Kel-1.6.0-win-x64.exe` (or `Uninstall Kel.exe`) → Properties → Details →
  "File description" shows `Kel with the AionUI interface` (also surfaces in some system prompts).
- Evidence: `evidence/installer-metadata.txt` — identical on the campaign installer and the fresh
  re-audit installer, and on the installed uninstaller; the app's own `Kel.exe` shows clean "Kel".
- Affected repair: HV-13 — all dialogs/strings/smokes are Kel-branded; this metadata field was not
  part of the repaired set (pre-existing, sourced from `package.json` description via the builder).
- Expected: File description `Kel` (like the app exe).
- Actual: `Kel with the AionUI interface`.
- Release impact: cosmetic metadata only; no function/security impact.
- Acceptance criteria: set the installer's win.versionInfo/FileDescription to Kel; re-verify
  Properties. (Fixing the `package.json` description fixes both this and the internal-metadata
  observation.)
- Graded MINOR (user-visible donor mention on a shipped artifact; cosmetic).

## HVRA-SUG-001 — ACP setup help link points to the donor wiki

- Repro (code-level): the ACP setup help link constant in the renderer is
  `https://github.com/iOfficeAI/AionUi/wiki/ACP-Setup`; reachable only from ACP-configuration help
  (not on repaired surfaces; not encountered by any battery run).
- Evidence: `evidence/donor-contexts-built.txt` (renderer bundle context).
- Suggestion: retarget to Kel documentation (or drop) when convenient.

## HVRA-SUG-002 — Duplicate identical toast on Desktop-Pet enable refusal

- Repro: Settings → Desktop Pet → toggle Enable while the pet is unavailable → the identical
  message ("The desktop pet is not available in this build, so it stays off.") appears twice.
- Evidence: `evidence/probes-source/own/reaudit-probes.json` → `desktopPet.after.msgs` (2×);
  reproduces installed (2×).
- Affected repair: HV-11 — truthfulness is correct (switch reverts OFF, persists, survives reload);
  only the toast is duplicated (cosmetic).
- Suggestion: collapse to a single error toast.

## Observations (not findings)

- Donor-era migration invite (`AionUi Pro` / `www.aionui.com`) is compile-time gated
  (`IS_DISCONTINUED_BUILD`) and **absent from the built app** (0 occurrences in built output);
  no user risk.
- Internal donor identifiers retained by design (compat/legal), with evidence in
  `donor-sweep-static.txt` + `donor-contexts-*.txt`: `aionui-browser` protocol/CDP ids,
  `bundled-aioncore` binary dir, `aionui-config.*` file names, telemetry tag names,
  `ownership:'aionui'` enum (display value "App"), license headers `Copyright 2025 AionUi`
  (Apache-2.0 attribution), `AionUI-LICENSE.txt` (legal file), hub metadata (upstream third-party
  content from iOfficeAI/AionHub), stale code comments.
- Runtime user-visible text: **0 donor strings** across all 11 screens (source + installed);
  window title "Kel"; installer dialogs Kel (smokes re-run: messagebox 12/12, self-lock, rstrtmgr,
  report — all PASS); page/pane text dumps show Kel branding throughout.
- `BUTLER` token: 0 occurrences anywhere scanned.
- "Scale 95%" persisted zoom in the fixture profile — fixture state, not a defect (overflow checks
  pass at native, 95%, and emulated 125%).
- `package.json` description "Kel with the AionUI interface" is internal metadata (source of
  MINOR-002); not user-visible inside the app UI.

## Technical release gate

No new BLOCK or MAJOR exists. The delta audit found the visual repair coherent, bounded, and
functionally safe; the two MINORs and two SUGs are cosmetic and do not gate the technical release.
No repairs were performed by this audit (per instruction).
