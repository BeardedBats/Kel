# 12 — Acceptance Criteria per Finding

Four evidence classes are used, and **all four are required** for a finding to close:

* **A — automated/engine**: a repeatable command whose failure is unambiguous (engine tests, tsc, the repo's
  own suites).
* **P — packaged app**: measured in the running packaged build (the `probe-{a,b,c}.cjs` harness in
  `C:\Users\Nick\Desktop\Kel\ux-audit\visual`, which writes JSON + PNG).
* **D — DOM/measurement**: a numeric assertion on the rendered DOM (geometry, computed style, contrast ratio,
  char count, element identity).
* **H — human/pixel**: a person (or a vision-capable reviewer) looking at a specified screenshot and confirming
  the described state. **This class cannot be satisfied by this audit thread** — it is the open gate.

Baseline values to compare against are the ones recorded in `evidence-visual-{a,b,c}.json` and summarised in
`00_STATUS.md`.

## S1 findings

| # | Finding | Observable behaviour (done = ) | A | P | D | H |
|---|---|---|---|---|---|---|
| 3 | Settings nav ejects from Settings | Clicking **every** Settings entry keeps the Settings sidebar and never shows the main nav | n/a (no engine path) | `probe-a` → `settingsNav` disabled/short-circuited | for every settings route: `hasSettingsSider === true && hasMainNavWork === false` | `appearance-light-1440.png` vs the corrected capture: footer still reads "Back to Chat"… and sidebar still lists settings groups |
| 16 | Raw engine error text reaches the user | No screen ever renders an exception string; failures read as sentences | `grep -rn "err.message\|String(err)" renderer/pages/kel` shows no direct render into copy | `probe-b` engine-loss scenario | no alert text matching `/TypeError\|fetch failed\|ECONNREFUSED\|Error invoking/`; a `role=alert` exists with human copy | `b-030-engine-lost-*.png` (5) replaced by corrected captures |
| 17 | No post-launch engine supervision | After the engine stops, the UI recovers (or states the condition and offers one working action) without restarting the app | engine suite green; new supervision unit path tested | `probe-b` kill-engine then revisit all five screens | previously-failing surfaces become non-error **and** a single clear state appears | `b-030-engine-lost-*.png` (5) after the fix |

## S2 findings

| # | Finding | Observable behaviour (done = ) | A | P | D | H |
|---|---|---|---|---|---|---|
| 1 | Colour picker closes mid-interaction | The colour/hex control keeps identity and focus across a change | n/a | `probe-c` → `hexField` | `focused === true` after a change; the queried node is the **same** node (`document.querySelector(sel) === window.__prev`); override still applies | `c-030-appearance-hex.png` / `appearance-after-colour-change-light-1440.png` |
| 5 | Hover actions overlap titles | Hovering a row never covers the title | n/a | `probe-c` → `hover` | `overlapPx <= 0` (baseline **12**) | `c-010-sidebar-hover.png` |
| 7 | Permissions too technical/large | The page leads with what needs the user; no policy-checker panel; no nested cards; vocabulary is plain | n/a | `probe-a` → `autonomy` | visible char count materially below **3615** (target < 1200); no `.kel-card` inside `.kel-card`; zero occurrences of `lease`/`guardrail`/`digest` in body copy | `permissions-light-1440.png` / `permissions-dark-1440.png` |
| 9 | Work oversized/card-heavy | Only sections with content render; no empty-in-card; no 24px headings over empty areas | n/a | `probe-a` → `work` | ≤1 card rendered on an empty account; **0** nested `kel-empty` inside `kel-card`; max heading px ≤ 22 | `work-light-1440.png`, `work-dark-1440.png` |
| 8 | Projects oversized / mis-titled | The surface names what it actually contains; no 7-column admin grid; no raw JSON in body copy | n/a | `probe-a` → `projects` | no `<pre class="kel-code">` in the knowledge/conflicts/recipes bodies; per-row action count ≤ 1 visible + menu | `projects-light-1440.png`, `projects-dark-1440.png` |
| 6 | Transcription diverges from the authoritative IA | Column titled *Transcriptions* with an **API Key** text action; actions top-right as *Upload Audio · Record More · Record*; four bottom actions; Kel tokens only | n/a | `probe-a` → `transcription` | title text present; button order matches; **0** `--color-*` donor vars in `index.module.css`; `Record` is right-most | `transcription-{light,dark}-1440.png` + 1280/1024 |
| 4 | Readability on donor surfaces | Every readable string ≥ 4.5:1 (3:1 large) in both themes | n/a | `probe-a` offenders arrays | **0** offenders on transcription / settings-model / settings-system / appearance, both themes (baseline: 1.06, 1.23, 1.5, 1.7, 2.13, 2.21, 2.92, 3.24, 3.25) | the same four surfaces, both themes |
| 2 | Model/Tools detached from composer | The model pill and tools control render inside the composer, not the header | tsc clean | `probe-a` on `#/guid` + a conversation route | the pill/tools nodes are descendants of the sendbox container; header `headerExtra` contains neither | `shell-1440-light.png` + a conversation capture (see gap note) |

## S3 findings and verified extra defects

| # | Finding | Observable behaviour (done = ) | A | P | D | H |
|---|---|---|---|---|---|---|
| 13 | Redundant row icons | Rows that carry no distinguishing information show no leading icon | n/a | `probe-c` → `sidebar.inventory[].lead` | for single-assistant conversations `lead` is empty/absent; cron/status/fork marks still present | `c-020-after-newchat.png` |
| 14 | Project/folder semantics collide | One word means one thing; the nav entry that opens a knowledge console is not called "Projects" | n/a | `probe-a` → nav labels + `projects.textHead` | nav label and page title agree; the word "Projects" no longer appears on both the group section and the console page | `shell-1440-light.png`, `projects-light-1440.png` |
| 12 | Lingering empty conversations | No sidebar row exists for a conversation with zero messages | n/a | `probe-c` → `sidebar.rowCount` vs store query | rendered rows == conversations with ≥1 message (baseline: 5 rows vs 9 conversations / 6 empty) | `c-020-after-newchat.png` |
| X1 | Team → Office "Seed the default roster" does nothing | The button either seeds or is absent | engine `seed` path covered by tests | `probe-a` → `team` | clicking it changes `roster.roles.length` from 0 to >0, or the button is gone | `team-office-light-1440.png` |
| X2 | `TeamSiderSection.tsx` dead code | Either mounted and reachable, or removed | tsc/lint clean after change | n/a | no unreferenced component remains | n/a |
| 11 | New Chat behaviour (S4/design) | **Requires a coordinator decision** — see `15_SEMANTICS_FLAGS.md` | — | — | — | — |

## Evidence gaps that block full acceptance today

1. **No conversation-route screenshots exist.** My sweep covered `/guid` and the five Kel pages; the chat
   surface with a live conversation (`#/conversation/<id>`, where the header pills actually render — Main's own
   note in `docs/v1.6/AUTO_RESUME.md` records this) was **not** captured. Findings **2, 5 (row actions in
   context) and the Phase 3 approval card** therefore have no packaged screenshot. **Action for the
   implementation phase: capture `conversation-*` screenshots first, before touching the composer.**
2. **Dense/populated states** (many jobs, long transcripts, many roles) were not exercised; the density
   criteria above are stated on empty/small states. Accept them as necessary-but-not-sufficient.
3. **`desktop.log` from a failed-engine session** was not collected; add it to the acceptance pack for #17.
4. Every row above with an **H** cell requires a human or vision-capable reviewer. **This audit cannot close
   the Human Visual UX gate.**
