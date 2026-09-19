# 14 — Screenshot Review Index

**Location:** `docs/v1.6-visual-ux/screenshots/` (35 PNG files, all captured from
`package-final16` = `ffeef73` + Phase 3 WIP, off-screen 1440×900 unless the filename says otherwise).

**Theme labelling:** the app's default is **light**. `*-light-1440.png` = light theme; `*-dark-1440.png` =
after the in-app theme toggle. Files prefixed `b-` are from the engine/interaction probe, `c-` from the
populated-sidebar probe.

Every row requires a **human or vision-capable reviewer**; this audit did not see the pixels. The
"expected corrected state" column is the acceptance target for the remediation phase — do not check it before
the corresponding batch lands.

| # | File | Finding(s) | Route / surface | What the reviewer must inspect | Expected corrected state |
|---|---|---|---|---|---|
| 1 | `shell-1440-light.png` | 2, 3, 13, 14 | `/guid` (shell) | Nav list and its wording; the **New Chat** button's radius (7px now); sidebar section labels; per-row leading icons; footer entries | Nav uses one vocabulary; New Chat matches the 8px control radius; no leading icon on plain conversations; section labels read as structure |
| 2 | `work-light-1440.png` | 9, 10 | `/work` | How many bordered cards render on an empty account; the 32px title over one sentence; dashed empty boxes nested inside cards; 24px card headings | Only sections with content render; no card-in-card; headings ≤22px; page reads as a short list, not a stack of panels |
| 3 | `work-dark-1440.png` | 9, 10 | `/work` (dark) | Same as above + dark surfaces are slate-navy, not charcoal | Same as above, in the new dark foundation |
| 4 | `work-1280x720.png` | 9, 10 | `/work` small laptop | Whether the four cards force scrolling for no content | Fits comfortably; no scroll for an empty state |
| 5 | `work-1024x768.png` | 9, 10 | `/work` narrow | Card width, gutter, text measure | Gutters hold; content stays left-aligned and readable |
| 6 | `projects-light-1440.png` | 8, 10, 14 | `/projects/knowledge` | The **title says "Projects" but the subtitle says "General · N knowledge records · map — · N recipes"**; the 7-column table; three action buttons per row; raw JSON under Conflicts | Title matches the content; no admin grid; one action + menu; JSON behind a disclosure |
| 7 | `projects-dark-1440.png` | 8, 10, 14 | `/projects/knowledge` (dark) | Same | Same |
| 8 | `permissions-light-1440.png` | 7, 10 | `/autonomy` | **`Emergency stop` sitting next to `Reload`** (and no confirmation); the 3-line explanatory paragraph; `Capability leases` columns (`review_ref`, `kind: value`); the nested card per boundary request; **"Ask the engine about a scope"** panel; `Locked guardrails · digest …` | Pending items lead; one card, no nesting; no policy-checker panel; plain vocabulary; Emergency stop behind an overflow with a confirm |
| 9 | `permissions-dark-1440.png` | 7, 10 | `/autonomy` (dark) | Same | Same |
| 10 | `team-office-light-1440.png` | 15, X1 | `/team/office` | The empty-state button **"Seed the default roster"** (it currently only reloads); the word "Office" | The button seeds or is gone; wording matches what the tab shows |
| 11 | `team-roster-light-1440.png` | 15 | `/team/roster` | "Roster" grouping by department; `Open in Studio` (Studio implies authoring that does not exist) | Plain labels ("Roles", "Role detail"); no invented authoring affordance |
| 12 | `team-dark-1440.png` | 15, X1 | `/team/*` (dark) | Same as above in dark | Same |
| 13 | `transcription-light-1440.png` | 6, 4, 10 | `/transcription` | **No "Transcriptions" title, no API Key entry** (a `Source` text button sits at the bottom); section titles `FOLDERS`/`RECENT TRANSCRIPTIONS`; action row top-**left** in the order `Record · Upload Audio`; 16px `<strong>` title with a `Rename` button; **eight** bottom buttons; two floating bordered panels | Column titled *Transcriptions* + **API Key** text action; actions top-right as `Upload Audio · Record More · Record`; large title + saved state; four primary bottom actions; column + document, not two cards |
| 14 | `transcription-dark-1440.png` | 6, 4, 10 | `/transcription` (dark) | **The `Source` button contrast (measured 2.21:1)** and the donor-blue drop/active tints against Kel's accent | `API Key` readable at ≥4.5:1; no donor-primary tints |
| 15 | `transcription-1280x720.png` | 6, 10 | small laptop | Whether the two panels squeeze the transcript body | Transcript keeps a comfortable measure |
| 16 | `transcription-1024x768.png` | 6, 10 | narrow | The stacked (column-above-workspace) fallback at ≤980px | Still readable and ordered |
| 17 | `settings-system-light-1440.png` | 4, 10 | `/settings/system` | **`Back up now` (white on near-white, 1.23:1)**, `Restore from this backup` (1.5:1), `Clear` (3.25:1); 1,259 characters at 12px | Buttons readable; density reduced |
| 18 | `settings-model-light-1440.png` | 4, 10 | `/settings/model` | **`Needs setup` chip (2.92:1)**; 434 chars at 13px | Chip readable; scale reduced |
| 19 | `appearance-light-1440.png` | 1, 4, 10 | `/settings/appearance` | **Theme-gallery labels `Light`/`Dark`/`Follow System` at 1.06:1**; `Reset` at 1.7:1; the 16px-radius `bg-2` blocks; the colour rows | Labels readable and outside the preview swatch; `Reset` ≥4.5:1; 8px surfaces; stable colour rows |
| 20 | `appearance-dark-1440.png` | 1, 4, 10 | `/settings/appearance` (dark) | `Reset` at 2.13:1; the swatch/hex row layout | `Reset` readable; rows stable across changes |
| 21 | `appearance-after-colour-change-light-1440.png` | 1 | `/settings/appearance` after a colour change | Whether the row the user just changed looks consistent (swatch, hex, "changed" marker) | No visual glitch; control keeps identity |
| 22 | `c-030-appearance-hex.png` | 1, 4 | after typing into the hex field | Whether the typed value survives and the field is still focused | Value kept; focus retained; override applied |
| 23 | `c-010-sidebar-hover.png` | 5, 13 | populated sidebar, row hovered | **Whether the hover menu sits over the title's tail**; which rows show a leading icon | Title ellipsised *before* the button; plain chats show no icon |
| 24 | `c-020-after-newchat.png` | 11, 12, 13 | sidebar after New Chat | Whether a new/empty row appeared; how many rows are real conversations | No phantom row; rows equal conversations with ≥1 message |
| 25 | `b-000-boot.png` | baseline | post-onboarding default | What a first launch actually presents (reference image) | Reference only |
| 26 | `b-020-after-new-chat.png` | 11 | `/guid` after New Chat | The empty composer state — does it read as "a new conversation started"? | An explicit, honest empty state |
| 27 | `b-021-sidebar-after-roundtrip.png` | 11, 12 | after leaving/returning | Whether anything accumulated | Nothing accumulated |
| 28 | `b-010-appearance-after-color.png` | 1 | appearance after a programmatic change | Row integrity after change | Stable |
| 29 | `b-030-engine-lost-work.png` | 16, 17 | `/work` with the engine stopped | **The literal `TypeError: fetch failed` in body copy**, the `Fix:` paragraph, **and the coexisting "Nothing waiting to continue." / "No specialist has been assigned yet." cards** | One human state, one action, raw detail behind a disclosure, no contradictory empty sections |
| 30 | `b-030-engine-lost-projects.png` | 16, 17 | `/projects/knowledge` engine stopped | Same raw leak | Same |
| 31 | `b-030-engine-lost-autonomy.png` | 16, 17 | `/autonomy` engine stopped | Same raw leak | Same |
| 32 | `b-030-engine-lost-team.png` | 16, 17 | `/team/office` engine stopped | Same raw leak | Same |
| 33 | `b-030-engine-lost-transcription.png` | 16, 17 | `/transcription` engine stopped | Same raw leak (note: the page still offers "Upload audio" while the library failed) | Same |
| 34 | `diagnostics-light-1440.png` | 10 | `/diagnostics` | 1,088 chars at 14px + 86 at 24px — the "too large" pattern on an internal surface | Reduced scale |
| 35 | `providers-light-1440.png` | 10 | `/providers` | 878 chars at 16px; provider cards | Reduced scale; card policy applied |

## Not covered by these 35 files (must be captured in the remediation phase)

| Gap | Why it matters | Capture needed |
|---|---|---|
| `#/conversation/<id>` (any platform) | The chat header pills (**finding 2**) render only on a conversation route — Main's own note in `docs/v1.6/AUTO_RESUME.md` records this. The **Phase 3 approval card** also has no screenshot. | `conversation-light/dark-1440.png`, one with an approval pending |
| Dense/populated states | Density claims are stated on empty/small states | A profile with several jobs, a long transcript, several roles |
| `Follow system` theme + third-party theme | Untested | One capture each |
| Widths < 1024px and > 1440px | Only 1024/1280/1440 exist | 900px and 1920px for Work + Transcription |
| `desktop.log` of a failed-engine session | Needed for finding 17 root-cause closure | Copy into the acceptance pack |
