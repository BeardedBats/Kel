# 04 — REGRESSION (Kel V1.6 human visual repair)

All results recorded on the repair branch `repair/v16-human-visual`.

## Desktop — TypeScript

| Run at | Command | Result |
|--------|---------|--------|
| cluster 1 (`14fc254`) | `bunx tsc --noEmit` (desktop) | **PASS** (exit 0) |
| after installer cluster (`3df2176`) | `bunx tsc --noEmit` | **PASS** (exit 0) |
| after appearance/tools (`d934a60`) | `bunx tsc --noEmit` | **PASS** (exit 0) |

## Desktop — Vitest (full)

| Run at | Command | Result |
|--------|---------|--------|
| after `d934a60` | `bunx vitest run` | **PASS — 15 files / 156 tests** |

Focused runs along the way (all PASS): `tests/unit/donor-policy.test.ts` (now 9 incl. RA-MINOR-003 pins + installer branding gate), `tests/unit/needs-attention.test.ts` (route expectation corrected to `/conversation/…`), `tests/unit/keepAwake.test.ts`.

New discriminating coverage added in this pass:

- `needsAttention` action targets only existing routes (`/conversation/<id>`, `/work`, `/autonomy`) — updated to the real conversation route.
- Desktop Pet truthfulness (RA-MINOR-003): bridge rejects loudly (`throw new Error('The desktop pet is not available in this build…`)) and the settings toggle reverts with a `Message.error`.
- Installer branding (RA-MINOR-002): `installer-messages.nsh` contains no `AionUi`/`AionCore`; report script header/footer use Kel naming.

## Engine (`runtime/`)

This pass touches no engine files (`git diff` from `eb4da52` is desktop + docs + resources/windows only —
verified at packaging time). Engine suites are therefore unaffected; the packaged engine binary is the
audited production binary (see `05_PACKAGE_EVIDENCE.md`).

## Installer smoke replays (disposable, no machine damage)

Pending at recording time — to be replayed after packaging:
`smoke-installer-failure-messagebox.js --all-scenarios --compile-only`, `smoke-installer-self-lock.js`,
`smoke-installer-rstrtmgr-ui.js`, `smoke-installer-report.ps1`.

## Routes / actions checklist (installed battery)

Open the chat · Permissions actions · Work & context · sidebar routes · settings routes · Model controls ·
Tools · Desktop Pet · Remote · Team route (must redirect) — covered by `kelvis-verify.cjs` probe + screenshots.

## Console

Zero unexplained renderer errors — recorded by the probe (`consoleErrors` in `kelvis-verify.json`).
