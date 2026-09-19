# 02 — IMPLEMENTATION LOG (Kel V1.6 human visual repair)

Baseline: branch `repair/v16-human-visual` @ `eb4da52b40a2500daae12fe8740823d07a6ad1d8` (identical production tree to `05a076b`).

| SHA | Cluster | Files | Note |
|-----|---------|-------|------|
| `3be6b18` | durable state docs | `docs/v1.6/human-visual-repair/*` | repair bound to the audited tree; findings enumerated (HV-01…HV-14) |
| `14fc254` | shell + navigation + readability | `needsAttention.ts`, `Layout.tsx` (canonical logo), `Router.tsx` (workforce hidden), `SettingsSider`, `SettingsPageWrapper`, `KelCommandPalette`, `KelWorkPanel` (plain language + state-aware actions + trigger/badge), `kel-tokens.css` (scroll owner, contrast pins, 16/14 floors), `arco-override.css` (root foreground + control inheritance), `autonomy/index.tsx` (language + advanced gating + `formatUntil`), `KelModelControl`, `ModeSettings`, `ModelModalContent`, `en-US/settings.json` | HV-01…HV-07, HV-12 |
| `3df2176` | pet truth + system page + installer branding | `systemSettingsBridge.ts` (loud refusal), `PetSettings.tsx`, `KelKeepAwakeCard`, `KelDataCard` (single card + dividers), `SystemModalContent/*` (folders disclosure, radii), `fontSizes.ts` (16/14 floors), `markdown.css`, installer `*.nsh` message values (47 strings EN+ZH), observability/repair-heal/process-control/remove-registry nsh, `support/query-lockers.ps1`, `support/report-installer-failure.ps1`, `build-with-builder.js`, 4 smoke scripts, `donor-policy.test.ts`, `needs-attention.test.ts` | HV-08, HV-11, HV-13 |
| `d934a60` | appearance + tools + radius | `builtinThemes.ts` (donor cover removed → generated neutral preview), deleted `themeCovers.ts` + `assets/themes/default-theme.png`, `AppearanceModalContent`, `McpServerHeader.tsx` (Kel Browser) | HV-09, HV-10 |
| `393640e` `092409b` | docs checkpoints | this directory | status/log updates through probe v3 |
| `6b4e40d` | conversation resolution + Work states | `useConversationListSync.ts` (`resolveConversationRoute`), `KelNeedsAttention.tsx`, `work/index.tsx` | probe found: `/conversation/<kel-id>` 404s; sidebar opens by donor id (host mirror `extra.kel_conversation_id`) — deep links now resolve the same way |
| `9ad8a08` | pet settle (RA-MINOR-003) | `PetSettings.tsx` | settle on authoritative state after any outcome |
| `250597e` | pet deadline reconcile | `PetSettings.tsx` | the donor dispatcher can swallow a refused handler without settling; reconcile on a 900ms deadline so the toggle can never sit ON |
| `65bcaa3` | pet TS7011 + pins | `PetSettings.tsx`, `donor-policy.test.ts` | explicit-return arrow; pin the deadline settle |
| `6d957ee` | report status/fallback paths | `report-installer-failure.ps1` | completes the Kel naming sweep in the support report script |

**HUMAN_VISUAL_REPAIR_HEAD (production source): `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`**

Review tooling (outside the repo, `C:\Users\Nick\Desktop\Kel\ux-audit\`): `kelvis-verify.cjs` (main battery),
`kelvis-petcheck.cjs` / `kelvis-convcheck*.cjs` (targeted diagnostics), `r12-installed-probe.cjs` (audit battery).
Evidence: `docs/v1.6/human-visual-repair/evidence/` (matrix + installed JSON + probe logs + installer hash + smokes).
