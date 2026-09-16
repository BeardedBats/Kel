# Packaged acceptance

Artifact under test: `dist/package-final/win-unpacked` (Kel 1.5.0 + post-V1.5 branch work) and its
NSIS installer — a fresh full build produced after the last source edit. (`dist/package` is one
renderer edit older and its `app.asar` is held by a lingering host handle; see AUTO_RESUME.) Engine rebuilt in the same session (the review-fix copy change is inside the
packaged `KelEngine`). All numbers below come from the archived harness JSON in `evidence/`; suite numbers are in
`evidence/suite-typecheck.txt`.

## Headline scenarios (as-built, final runs)

| Flag | transcription | hardening | voice-vetting | vetting |
|---|---|---|---|---|
| dedicated page shows | ✓ | ✓ | — | — |
| empty state ("Nothing here yet.") | ✓ (hardening asserts; page checked in shots) | ✓ | — | — |
| record → save row | ✓ | ✓ (density) | ✓ | — |
| recording state unmistakable (dot + label + timer) | ✓ | ✓ | ✓ | — |
| Escape cancels (no row) | ✓ `escapeCancelled` | ✓ `keyboardEscape` | — | — |
| rename / folder / drag-assign | ✓ | — | — | — |
| upload + invalid-file plain sentence | ✓ `uploadRow`, `invalidMessage` | — | — | — |
| copy + download txt/audio buttons (clicked; no errors) | ✓ `copyAndDownload`, `downloadAudioEnabled` | — | — | — |
| combine (choose → merge → source leaves) | ✓ `combined` | — | — | — |
| composer dictation lands editable, single copy | ✓ `composerSingleCopy` | — | ✓ `dictationText` | — |
| never auto-sent (no auto-send path; harness clears, `sendToChat` proves insertion) | ✓ `composerCleared` | — | ✓ (edited then sent) | — |
| page → chat handoff (Send to chat) | ✓ `sendToChat` | — | — | — |
| review: preview / Edit / Check again ≥1 | ✓ `recheckWorked = 1` | — | ✓ `multiPreview = 3` | — |
| review: Accept all / Process batch | ✓ `reviewApplied` | — | ✓ both | — |
| Think Out Loud buckets | — | — | ✓ `thinkBuckets` | — |
| dictation answers one question (panel: Q1 ANSWERED) | — | — | ✓ `oneAnswerRecorded` | — |
| interrupt with chat then continue | — | — | ✓ `interruptedThen` | — |
| restart: rows + audio (`has_audio` enabled) + session | ✓ `rowsAfterRestart` | — | ✓ both + `audioAfterRestart` | — |
| narrow 980px, no h-scroll | — | ✓ 0/0 px overflow | — | — |
| jargon scan on the two surfaces | — | ✓ `[]` offenders | — | — |
| keyboard: Enter starts, Escape cancels | — | ✓ both | — | — |
| wrong key → one plain sentence, no envelope | — | ✓ "The Meta API key was not accepted. Replace it in Settings." | — | — |
| palette reaches Transcription | — | ✓ | — | — |
| density 3 folders + 3 transcripts, no overflow | — | ✓ | — | — |
| light theme toggle + readable after | — | ✓ `lightThemeToggled` | — | — |
| batch 1 shown in panel | — | — | — | ✓ |
| ten composer answers recorded | — | — | — | ✓ (10) |
| process → batch 2 | — | — | — | ✓ |
| decisions / greyboxes appear | — | — | — | ✓ ✓ |
| spec preview + snapshot | — | — | — | ✓ `spec-preview` |
| console errors | 0 | 0 | 0 | 0 |
| scenario errors / timeouts | none | none | none | none |

## Standing battery (re-run on the final build, seeded root)

`first-run` (fresh): onboarding shown and dismissed, `/guid` reachable with the composer present
(`landingComposer` non-empty; no focus assertion),
sider lists Transcription; 0 console errors. `tour`, `settings`, `palette`, `keyboard`,
`readability`, `sider`, `maintext`, `vetting` panel section: all re-run, 0 console errors each;
readability: `/guid` and three more audited pages show `[]` offenders, and `settings-appearance`
reports two disabled-button hits (2.13 vs 4.5) — WCAG-exempt disabled controls, seen by the
checker as false positives; sider shows "Workspace" and every tool entry, no raw keys.

## Probes

- Skip link: present, first tab stop, target resolves (fresh root, `/guid`).
- a11y probe (light + dark): `contrastFailures: []` on the audited surface; skip-link wiring intact.

## Suites

- Engine: **502 passed, 10 subtests** (transcription 27, vetting 30 among them).
- Desktop typecheck: **0 errors** (post-fix).
- Desktop unit tests: the repo has no desktop test runner configured; typecheck + the packaged
  scenario battery are the desktop gates (honest note, unchanged from V1.5).

## Notes

1. **Chat pane readability**: harness `innerText` cannot read the conversation transcript in the
   packaged shell (pre-existing, verified against the archived V1.5-era run). Vetting journeys
   therefore assert **panel/engine outcomes**; the user actions (typing answers, sending commands,
   editing review text) are still real composer interactions.
2. **One collision, resolved**: an earlier re-run overlapped a rebuild with a live scenario (EBUSY,
   builder aborted, the vetting leg timed out against a half-removed app). Lesson recorded; the
   final runs were executed strictly sequentially on the finished artifact.
3. Every scenario ends with `engineKilled`/clean shutdown checked, so no stray Kel processes.
4. The vetting spec is proven through the engine preview action (markdown + snapshot); the
   drawer's own "Preview spec" button was not separately clicked by the probe (the panel gates
   cover the same session state), noted for honesty.

5. Two runs (`vetting`, `sider`) end with `engineKilled: true` — the engine was force-stopped after
   the scenario overran its close grace period. No stray process remained in either case.
6. The two a11y probes record `errors` and their own checks but not a `consoleErrors` array; the
   "zero console errors" statement is exact for the 13 scenario JSONs that record it.
7. `12: F` in older docs was an unparseable example (Q12 offers A-E); every occurrence now reads
   `12: A`, and the review hint matches (`transcription/index.tsx`, `KelWorkPanel.tsx`).

