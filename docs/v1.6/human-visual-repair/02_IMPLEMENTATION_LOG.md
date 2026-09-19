# 02 — IMPLEMENTATION LOG (Kel V1.6 human visual repair)

Append an entry at every repair commit. Format: SHA · cluster · files · note.

Baseline: branch `repair/v16-human-visual` @ `eb4da52b40a2500daae12fe8740823d07a6ad1d8` (identical production tree to `05a076b`).

| SHA | Cluster | Files | Note |
|-----|---------|-------|------|
| `3be6b18` | durable state docs | `docs/v1.6/human-visual-repair/*` | repair bound to the audited tree; findings enumerated (HV-01…HV-14) |
| `14fc254` | shell + navigation + readability | `needsAttention.ts`, `Layout.tsx` (canonical logo), `Router.tsx` (workforce hidden), `SettingsSider`, `SettingsPageWrapper`, `KelCommandPalette`, `KelWorkPanel` (plain language + state-aware actions + trigger/badge), `kel-tokens.css` (scroll owner, contrast pins, 16/14 floors), `arco-override.css` (root foreground + control inheritance), `autonomy/index.tsx` (language + advanced gating + `formatUntil`), `KelModelControl`, `ModeSettings`, `ModelModalContent`, `en-US/settings.json` | HV-01…HV-07, HV-12 |
| `3df2176` | pet truth + system page + installer branding | `systemSettingsBridge.ts` (loud refusal), `PetSettings.tsx` (revert + reason), `KelKeepAwakeCard`, `KelDataCard` (single card + dividers), `SystemModalContent/*` (folders disclosure, radii), `fontSizes.ts` (16/14 floors), `markdown.css`, installer `*.nsh` message values (47 strings EN+ZH), `installer-observability.nsh`, `installer-repair-heal.nsh`, `installer-process-control.nsh`, `installer-remove-registry.nsh`, `support/query-lockers.ps1`, `support/report-installer-failure.ps1` (title/footer/copyText/URL), `build-with-builder.js` (DetailPrint), 4 smoke scripts, `tests/unit/donor-policy.test.ts` (+RA-MINOR-003 pins, +installer branding gate), `tests/unit/needs-attention.test.ts` (route fix) | HV-08, HV-11, HV-13 |
| `d934a60` | appearance + tools + radius | `theme/builtinThemes.ts` (donor cover removed → generated neutral preview), deleted `themeCovers.ts` + `assets/themes/default-theme.png`, `AppearanceModalContent` (radius 8), `McpServerHeader.tsx` (Kel Browser display name) | HV-09, HV-10 |
| `393640e` | docs | implementation log + status | — |
| `6b4e40d` | conversation resolution + Work states | `useConversationListSync.ts` (Kel id → donor route resolver `resolveConversationRoute`), `KelNeedsAttention.tsx` (click resolves through it), `work/index.tsx` (verdict + milestone phrasing, state-aware Pause/Resume/Cancel) | follow-up found by probe run 3: `/conversation/<kel-id>` 404s; the sidebar opens by donor id (host mirror with `extra.kel_conversation_id`) — deep links now resolve the same way |

Review tooling (outside the repo, `C:\Users\Nick\Desktop\Kel\ux-audit\`): `kelvis-verify.cjs` — launches the packaged build with the isolated review profile, completes onboarding once, walks every surface at 1440×960, runs the Permissions scroll matrix at 5 sizes, contrast scan, donor scan, route checks (Work → Open the chat, Team hidden), pet truthfulness (revert + reload), About logo, console errors, and writes `kelvis-verify.json` + screenshots.
