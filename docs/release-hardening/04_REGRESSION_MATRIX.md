# Regression matrix

| Layer | Command | Result |
|---|---|---|
| Engine suite | `cd runtime && python -m pytest tests -q` | **502 passed, 10 subtests, 0 failed** (log: `evidence/suite-typecheck.txt`) |
| Transcription focus | `python -m pytest tests/test_transcription.py tests/test_vetting.py -q` | **57 passed** (27 + 30) |
| Desktop typecheck | `desktop/node_modules/.bin/tsc --noEmit -p tsconfig.json` | **0 errors** |
| Packaged E2E | `node packaging/ux-audit.cjs <app> <root> <out> <scenario>` | see `09_PACKAGED_ACCEPTANCE.md` |
| A11y probes | `packaging/verify-skip-link.cjs`, `packaging/a11y-probe.cjs` | see `09_PACKAGED_ACCEPTANCE.md` |

## Scenarios re-run for this program

| Scenario | Root | Purpose |
|---|---|---|
| `transcription` | fresh `review-transcription` | full feature incl. new Escape/combine/single-copy/re-check assertions |
| `hardening` | fresh `review-hardening` | narrow window, keyboard, jargon scan, provider error, density, light/dark, palette |
| `voice-vetting` | fresh `review-voice-vetting` | integrated vetting × transcription journeys 4-7 + restart |
| `vetting` | seeded | batch/answer/spec/greybox regression after review fixes |
| `first-run`,`tour`,`settings`,`palette`,`keyboard`,`readability`,`sider`,`maintext` | fresh + seeded | V1.5 acceptance battery re-run on the hardened package |
