# r21 desktop acceptance — Settings colour rows and command palette, clicked

Run 2026-09-23 against the **staged** r21 copy (`C:\Users\Nick\KelV2Candidate.r21`, `app.asar`
`84212ebe805e4bb0`, hash re-checked before and after — not rebuilt). This closes the gap the r21 record
left open: the Settings save path and the palette were only ever proved by **[INJECTED]** preferences.

## Method — evidence class **[UI]**

- Launcher `C:\tmp\run-r21-ui.cmd`: `AIONUI_MULTI_INSTANCE=1`, fresh
  `KEL_DATA_DIR` / `AIONUI_DATA_DIR` / `--user-data-dir` under `C:\Users\Nick\KelV2Runs\prepared\r21-ui\`,
  plus `--remote-debugging-port=9333` (the packaged app accepts the switch on the command line).
- Driven with Playwright `connectOverCDP`. **All state changes came from input events** — mouse clicks,
  `keyboard.press`/`keyboard.type`, and in one step `fill` (select-all + a single `Input.insertText`, i.e.
  what a paste produces). `page.evaluate` was used **only to read** computed styles and attributes.
- Saved state read **read-only** from `r21-ui\store\aionui-backend.db` → `client_preferences`.
- Restarts: only the r21 process tree was stopped (matched by executable path); the user's r20 session
  (6 processes) and the stable engine `26544` stayed up throughout.
- Screenshots: `C:\Users\Nick\KelV2Runs\prepared\r21-ui\shots\` (names below).

## Results

| # | interaction | observed | store (`theme.*`) | verdict |
| --- | --- | --- | --- | --- |
| 1 | fresh launch | `data-theme=dark`, `arco-theme=dark`, `--bg-base` `rgba(11,23,52,1)` (`u0-fresh`) | no rows | PASS |
| 2 | click **Settings** in the sider before finishing setup | route bounces back to `#/onboarding` (`u1-settings`) | — | by design (flag-only guard in `Layout.tsx`); see observation O1 |
| 3 | click **Start using Kel** → click **Settings** | `#/guid` → `#/settings/appearance`; Dark card checked; rows show `#0b1734` etc. (`u3-settings`) | none yet | PASS |
| 4 | App background hex field: click, Ctrl+A, **type** `#7a1f1f` | field and canvas show **`#77aa11`** (`u4-bg-typed`) | `{"dark":{"--bg-base":"#77aa11"}}` | **FAIL — D1** |
| 5 | click **Reset** on that row | `--bg-base` back to default (`u5-reset`) | `{}` | PASS |
| 6 | **paste** `#7a1f1f` into the same field | `--bg-base` `#7a1f1f`, row "Changed", canvas tinted, artwork still painted (`u6-bg-pasted`) | `{"dark":{"--bg-base":"#7a1f1f"}}` | PASS — the save path works |
| 7 | restart r21, open Settings | row still `#7a1f1f` / Changed; setup stays completed (`u8-restart-settings`) | unchanged | PASS |
| 8 | **Ctrl+K**, type `theme` | palette offers "Switch to Light theme" + "Settings · Appearance" (`p2-typed`) | — | PASS; see **D2** for the surface |
| 9 | **Enter** | `data-theme=light`; the open Settings page follows live (Light card selected, light tokens) (`p3-light`) | `theme.activeId="light"`, dark override kept | PASS |
| 10 | Ctrl+K, `theme`, **Enter** | palette now offers "Switch to Dark theme" (`p4-offer-dark`); Dark + saved override back (`p5-dark`) | `theme.activeId="dark"` | PASS |
| 11 | restart r21 | `dark`, `--bg-base` `#7a1f1f` (`p6-restart-dark`) | unchanged | PASS |

## Defects found

- **D1 — typing a 6-digit hex saves its 3-digit prefix.** `ThemeColorRow`'s hex `Input` calls `apply()`
  on every keystroke that parses; `hex()` accepts `#rgb`, so `#7a1` is saved as `#77aa11`. `onChanged`
  bumps `refresh`, which is part of every row's `key`, so the row remounts, focus is lost and the remaining
  keystrokes (`f1f`) go nowhere. Any typed 6-digit value hits this (every one has a valid 4-char prefix).
  Paste and Reset are unaffected. Source: `components/kel/ThemeColorsSection.tsx` (hex `onChange`, row keys).
- **D2 — the command palette is see-through in Dark.** The palette panel is a `.kel-card`
  (`rgba(15,45,100,0.3)`, no `backdrop-filter`) over a `rgba(20,22,26,0.32)` scrim, so page text bleeds
  through its rows (`p2-typed`, `p7-palette-dark`). Independent of the custom background. Opaque in Light (`p4-offer-dark`).

## Observations (not fixed)

- **O1** — before setup is finished, sider links highlight and push history but land back on
  `#/onboarding` with no explanation.
- **O2** — in Light, several labels are very faint: sider group headers ("Kel", "Application", "Data",
  "Other"), "Restore all colors", the Light card's checkmark, the Fonts "Reset" (`p3-light`).
- Theme-card wrapping ("Follow System" on its own row) is still visible — the known gap.

## Not claimed

- The native `<input type=color>` picker (opens an OS dialog) was not driven.
- V2-16 timings (conversation open, project switch) — still not measured.
- r21 is still **staged**: the user's r20 session is running from `C:\Users\Nick\KelV2Candidate`, so the
  promotion rename was not attempted.
