# Kel V2 candidate r21 — dark is the default appearance for new profiles

Built from `integration/v2` @ **`219f0ce`**, packed 2026-09-23 14:03Z by **one** packer
(`electron-builder --config kel-builder.json --x64 --dir`, exit 0, signed); typecheck clean and the
theme test (`tests/unit/kel-shell-theme.dom.test.ts`) passed before the build.

## What changed (the six reviewed files)

| file | change | what it does NOT touch |
| --- | --- | --- |
| `renderer/index.html` | `<html data-theme="dark">`, `<body arco-theme="dark">` | no pre-hydration flash of Light |
| `hooks/context/ThemeContext.tsx` | `activeTheme?.appearance ?? 'dark'` | a resolved theme's own appearance still wins |
| `hooks/system/useTheme.ts` | persisted-id fallback and the error fallback → `DARK_THEME_ID` | a **saved** id is still returned as-is |
| `utils/theme/applyTheme.ts` | `reapplyIfActive` fallback → `DARK_THEME_ID` | `resolveActiveTheme` unchanged |
| `components/kel/ThemeColorsSection.tsx` | colour section's active theme name/id → `DARK_THEME_ID` | overrides and tokens unchanged |
| `components/kel/KelCommandPalette.tsx` | palette's active theme id → `DARK_THEME_ID` | the switch action itself unchanged |

Every changed expression is the *empty* case (`?? 'light'` / `|| 'light'`). Saved Light, Dark, System
and custom themes travel through `resolveActiveTheme` exactly as before.

## Archive gate — the preconditions for *keeping* the candidate

| check | r21 | r20 |
| --- | --- | --- |
| `app.asar` | 1 copy, 300,586,086 B, `84212ebe805e4bb0` | 300,586,077 B, `baaab70ae30b6462` |
| `Kel.exe` | 1 copy, 204,575,232 B, `c17815f60797c090` | `98f1b8126207bc36` |
| `electron.exe` | **0** | 0 |
| stray `*unpacked*` dirs | none | none |
| frozen engine | `00846a7e64fdaa95` — byte-identical | same |
| donor aioncore | `67eb02774bab3855` — unchanged | same |
| DLL set | 15, the expected set | same |
| archive marks | `data-theme="dark"`, `arco-theme="dark"`, `DARK_THEME_ID`, the canvas repair, the r19 manifest fix — all present | — |

## Desktop verification through the isolated launcher (the actual app, not the browser)

Runs use the staged r21 copy with a **fresh isolated profile, store and engine root**
(`…\KelV2Runs\prepared\r21-verify\`), launched beside the user's own session
(`AIONUI_MULTI_INSTANCE=1`). Each run: launch → window captured at 1816×1189 → pixel analysis
(mean luminance of the window, canvas-band colour count and per-channel SD, fixed sample points).

| run | saved state in the store | measured | verdict |
| --- | --- | --- | --- |
| 1 | nothing (fresh profile) | mean luminance **41.1**; samples (28,41,77) (34,42,72) (33,39,65); **433** distinct canvas colours, SD 15.9/14.0/11.3 | **PASS — opens dark**, Figma artwork and gradients present |
| 2 | `theme.activeId = light` | mean luminance **249.6**; samples (249,250,251) (255,255,255) | **PASS — the saved Light choice wins** over the new default |
| 3 | `theme.activeId = dark`, `theme.overrides = {"dark":{"--bg-base":"#7a1f1f"}}` | mean 42.5; samples red-shifted vs run 1 — (52,40,64) (50,37,58) (40,39,72); **386** distinct canvas colours, SD 15.5/14.1/12.1 | **PASS — custom canvas colour applied, artwork and gradients still painted** (a flat fill would show ~1–3 colours and SD ≈ 0) |
| 4 | same store as run 3, relaunched unchanged | identical to run 3 (42.5 / 386 / SD 15.5/14.1/12.1) | **PASS — saved choices survive restart** |

Screenshots: `C:\Users\Nick\KelV2Runs\prepared\r21-verify\shots\{v1-fresh,v2-saved-light,v3-custom-canvas,v4-restart-same}.png`.
The saved values were written into the *throwaway* verification store's `client_preferences` table
(keys and encoding the app itself uses: `theme.activeId`, `theme.overrides`); the user's store at
`…\prepared\candidate\desktop-store` was not written to, and the shared Electron profile was not used.

## Startup / Settings / command palette agreement

- The three surfaces now share one constant: the Settings colour section and the command palette read
  `DARK_THEME_ID`, `useTheme`/`applyTheme`/`ThemeContext` fall back to it, and `index.html` ships the
  same attribute before any script runs — verified by review of the six diffs and by the packaged
  archive marks.
- The theme test and typecheck pass. The **signed-in Settings colour rows and the palette itself were
  not re-opened in this pass** (they render inside the app shell; the verification runs stopped at the
  fresh/desktop shell screen). Nothing about their rendering code changed, but do not read this as a
  clicked-through Settings check.

## Candidate layout — the swap is parked, not forced

The user's app was running from `C:\Users\Nick\KelV2Candidate` (r20) for the whole pass, so the swap
could not be performed without stopping a session that was not launched for verification. The rename
therefore **fails closed**: r20 is untouched in place, and r21 is staged complete with its own launcher:

| path | asar | note |
| --- | --- | --- |
| `C:\Users\Nick\KelV2Candidate` | `baaab70ae30b6462` | **r20**, live in the user's session |
| `C:\Users\Nick\KelV2Candidate.r21` | `84212ebe805e4bb0` | **r21**, staged, launcher `Run-Kel-V2-Candidate.cmd` inside it |
| `…\.r19` / `.r18` / `.r17` | `f9ae0767…` / `b4235af7…` / `75ef03c0…` | preserved, hash-verified |

To promote r21 once the app is closed (one line, no rebuild):

```powershell
Rename-Item C:\Users\Nick\KelV2Candidate C:\Users\Nick\KelV2Candidate.r20
Rename-Item C:\Users\Nick\KelV2Candidate.r21 C:\Users\Nick\KelV2Candidate
```

## Unresolved / not claimed

- Settings colour rows and command palette as **clicked** surfaces (see above).
- V2-16 conversation-open and project-switch timings (still need a signed-in session).
- Electron profile/log locations unchanged, as instructed; theme-card wrapping untouched.
