# Release hardening — status

Two-phase program on `ux/v15-journeys` (previous head `27215b6`), 2026-09-16.

## Phase A — independent transcription review

Fresh independent review of the committed transcription feature: **round 1 REVISE** (findings and
fixes listed in `10_RELEASE_READINESS.md`), **round 2 verification: all fixes FIXED**, disposition
**CONTINUE**. Fix round also produced rules **JR-38/39/40** and history **H21**.

## Phase B — integrated hardening

- Docs set: this directory (01-09 + AUTO_RESUME).
- Journeys: 20 integrated journeys mapped in `02_REAL_USER_JOURNEYS.md`; battery green (see
  `09_PACKAGED_ACCEPTANCE.md`); evidence archived in `evidence/`.
- Audits: jargon scan `[]` offenders; no donor identity in any new surface; bridge routes verified;
  combine reachable (JR-39); no second voice parser (contract test incl. sources/events).

## Evidence quick map

| Where | What |
|---|---|
| `evidence/transcription/ux-transcription.json` | final transcription scenario (escape, combine, single copy, Check again, send-to-chat, copy/download clicks, restart incl. audio) |
| `evidence/hardening/ux-hardening.json` | narrow window, keyboard, jargon, wrong-key sentence, density, light theme, palette |
| `evidence/voice-vetting/ux-voice-vetting.json` | journeys 4-7 + restart (panel Q1 ANSWERED, multi-preview 3, buckets) |
| `evidence/vetting/ux-vetting.json` | journey 3 via panel outcomes (batch, 10 answers, batch 2, decisions, greyboxes, spec) |
| `evidence/standing/`, `evidence/probes/` | V1.5 battery + a11y probes on the same package |

Every archived run in `evidence/` comes from the final artifact `dist/package-final` (fresh full
build after the last source edit); zero errors, zero console errors and zero timed-out steps
across all archived JSONs.

Commit: branch head of `ux/v15-journeys` after this program (previous head `27215b6`).
