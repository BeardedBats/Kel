# 04 — REGRESSION (Kel V1.6 human visual repair)

## Desktop — TypeScript

| Run at | Result |
|--------|--------|
| cluster 1 (`14fc254`) | PASS (exit 0) |
| installer cluster (`3df2176`) | PASS |
| appearance/tools (`d934a60`) | PASS |
| conversation/work (`6b4e40d`) | PASS |
| pet deadline (`65bcaa3`) | PASS |

## Desktop — Vitest

| Run | Result |
|-----|--------|
| full suite after `d934a60` | **PASS — 15 files / 156 tests** |
| full suite re-run (before pet fix) | PASS (exit 0) |
| focused `donor-policy` + `needs-attention` at `65bcaa3` | **PASS — 17 tests** (donor-policy 9 incl. RA-MINOR-003 pins and the installer-branding gate) |

New discriminating coverage added in this pass:

- attention actions resolve to real routes (`/conversation/<donor-id>` via the host mirror; the old raw-Kel-id
  target 404'd and bounced Home — now covered by the corrected expectation).
- Desktop Pet truthfulness (RA-MINOR-003): bridge rejects loudly; settings toggle re-reads the authoritative
  state, reverts, and explains; deadline reconcile pinned.
- Installer branding (RA-MINOR-002): `installer-messages.nsh` carries no donor names; report header/footer use
  Kel naming.

## Engine (`runtime/`)

`git diff --name-only eb4da52…6d957ee` touches only `docs/` and `desktop/` — **no engine files changed**.
Engine suites are unaffected; the packaged engine binary is the audited production binary
(`f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8`).

## Installer smoke replays (disposable; see `evidence/smokes.log`)

- failure messagebox, all 12 scenarios, compile-only — **PASS**
- self-lock — **PASS** (log: `kel-installer-self-lock-…-log.jsonl`)
- rstrtmgr UI — compile-only **PASS** (the full run opens an interactive harness that waits for a human to click
  Cancel; not automatable, exercised to compile stage)
- report script — **PASS** after the final status-path rename (`status=skipped, code=E1003, copyTextLength=613`)

## Routes / actions (installed battery)

Open the chat · Permissions actions · Work & context · sidebar routes · settings routes · Model controls · Tools ·
Desktop Pet · Remote · Team (must redirect) — all covered by `kelvis-verify.cjs` + `r12-installed-probe.cjs`: PASS.

## Console

Zero unexplained renderer errors in all final runs (source + installed).
