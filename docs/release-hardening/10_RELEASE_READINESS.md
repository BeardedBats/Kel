# Release readiness

## Phase A — independent transcription review

- **Round 1** (fresh reviewer against `27215b6`): **REVISE** — one UX-P1 (composer dictation
  duplicated/overwrote because the live region was never finalized) and a set of UX-P2/P3 findings
  (combine unreachable, HTTP status in copy, dishonest append status, Escape missing on the page
  bar, "Check again" documented but absent, Process batch confirming suggestions, donor speech
  control still mounted, silent drag/delete failures, duplicated opposition scan, weak equivalence
  test, stale doc claims).
- **Fixes** (all implemented and regression-locked): mic finalizes exactly once (stop/cancel/error),
  combine control on the transcript view, plain provider copy, honest statuses, Escape honored in
  every capture state with an epoch guard aborting late captures, real Check again, Process batch
  applies explicit answers only, both composers mount `KelMicButton` (donor Ctrl/Cmd+M path inert),
  IPC envelope stripped at the bridge, shared `chosen_labels`/`opposition_pairs`, equivalence test
  compares snapshot **plus** answer sources and decision events, hint example corrected to a
  parseable code, error sentences on every catch path.
- **Round 2** (independent verification of every finding): **all 14 fixes verified FIXED**; new
  findings were P3-level (double-cleared live region, stale archived evidence, count in a doc,
  extension wording, error-path clear) — all fixed; the evidence-basis concern is resolved by the
  archived post-fix runs in `evidence/`.
- **Verdict: CONTINUE.** No open P0/P1/P2 finding in transcription.

## Phase B — integrated hardening

| Gate | Result |
|---|---|
| Engine suite (incl. transcription + vetting) | 502 passed / 0 failed |
| Desktop typecheck | 0 errors |
| Packaged battery (headline + standing + probes) | all green; **zero console errors in every run that records them (13/13)** |
| Restart / persistence (transcripts, audio enabled, sessions) | ✓ |
| Clean-state (fresh roots) incl. empty states | ✓ |
| a11y (skip link; contrast light+dark) | ✓ |
| Journey standard gate | findings mapped to JR-38/39/40; history H21 |

## Honest remaining limitations

1. **No usable model provider on this machine** — chat/work/approval happy paths remain
   unverifiable end-to-end (standing O1). Vetting and transcription were designed to work without
   one, and that is exactly what the battery verified.
2. **No Meta API key** — live Muse transcription unverified; practice mode is what every
   packaged run exercises. The wrong-key path is verified (plain sentence).
3. **OS-level microphone denial** cannot be produced by the harness; the copy path is unit-tested
   and the handler policy is code-reviewed.
4. **Chat pane is unreadable to the harness shell** (pre-existing); vetting journeys assert
   panel/engine outcomes. This is a testing-surface limitation, not a product limitation.
5. **Known pre-existing open items** from the journey program (About-page donor links, `acp-temp`
   conversation tab naming, etc.) are unchanged and tracked in `USER_JOURNEY_HISTORY.md` (O2/O4).
6. The donor `SpeechInputButton` file remains in the tree but is unmounted; documented.

## Branch verdict

**Ready to become the next frozen Kel release: YES for everything verifiable on this machine** —
the post-V1.5 work (journey remediation, vetting sessions, transcription) behaves as one product
under the packaged battery, with zero console errors and zero timed-out assertions on the
as-built artifact. Before freezing, a short human smoke with a configured model provider (and,
if available, a Meta key) is recommended to close limitations 1-2. Per instruction, **no tag and
no freeze were created**; the frozen V1.5 release was not modified.
