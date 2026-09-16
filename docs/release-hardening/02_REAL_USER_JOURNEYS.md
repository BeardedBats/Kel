# Real-user journeys (integrated battery)

All journeys run against the packaged app (`dist/package/win-unpacked`) through the journey
harness; fresh roots unless noted. "Results" are written to `evidence/`; the verdict summary lives
in `09_PACKAGED_ACCEPTANCE.md`.

| # | Journey | Scenario (root) | Key assertions |
|---|---|---|---|
| 1 | Fresh launch → onboarding → normal chat | `first-run` (fresh) | onboarding shown/dismissed, `/guid` reachable, composer focus |
| 2 | Normal chat → project work | `tour` (seeded) + `maintext` | every primary page renders, no raw keys, no console errors |
| 3 | Start Design Vetting → answers → greybox → spec | `vetting` (seeded) | batch appears, 10 answers silent, process, spec text, greybox grid |
| 4 | Vetting → interrupt with normal chat → resume | `vetting` + `voice-vetting` | resurface after interruption, session still answerable |
| 5 | Vetting → transcription answers ONE question | `voice-vetting` | composer dictation → edited text → sent; panel shows Q1 ANSWERED |
| 6 | Vetting → transcription answers MANY questions | `voice-vetting` | review Edit → Check again shows ≥3 lines → Accept all applies them |
| 7 | Vetting → Think Out Loud → review decisions | `voice-vetting` | buckets (Requirements/Concerns/Still open) render on a real transcript |
| 8 | Record → save → folder → reopen → send to chat | `transcription` | save with title/audio, drag into folder, send appends to composer |
| 9 | Composer dictation → edit → send | `transcription` + `voice-vetting` | single copy, editable, no auto-send, send works |
| 10 | Upload audio → transcript → send | `transcription` | upload row appears, invalid file gets one plain sentence |
| 11 | Restart → recover chats, sessions, transcripts, folders | `transcription`, `voice-vetting` | rows and audio persist; review modal opens after restart |
| 12 | Permission/error paths | `hardening` + unit copy | mic denial copy, bogus key plain sentence, invalid audio |
| 13 | Provider unavailable paths | `hardening` | wrong key → one plain sentence (no HTTP/status jargon) |
| 14 | Narrow-window behavior | `hardening` | no horizontal overflow on `/transcription` and `/guid` at 980px |
| 15 | Keyboard-only critical paths | `hardening` | focus + Enter starts recording; Escape cancels |
| 16 | Light/dark appearance | `hardening` + `readability` | appearance toggle applies; contrast probe stays clean |
| 17 | Empty states | `hardening` | "Nothing here yet." + KelEmpty on a fresh library |
| 18 | Dense states | `hardening` | 3 folders + 3 transcripts: organised, no layout overflow |
| 19 | Command palette | `hardening` + `palette` | palette reaches Transcription and pages render |
| 20 | Work drawer + Vetting + Transcription together | `vetting` + `voice-vetting` | drawer panel and page review act on the same session |
