# 15 — Release Manifest (Kel V1.5)

Status: **released** — tagged `v1.5.0`; frozen at
`C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.5-Frozen` (assembled by `scripts/freeze-release.ps1`,
verified 3/3 by `scripts/verify-release.ps1` at the frozen location).

| Artifact | SHA-256 (first 8) | Notes |
|---|---|---|
| `Kel.exe` | `CF1984AC` | productName Kel; appId `com.kel.desktop`; **no `app-update.yml`** |
| `resources/app.asar` | `51DD5DFE` | renderer + main bundle of the tagged commit |
| `resources/kel-engine/KelEngine.exe` | `AB3024A0` | PyInstaller build; PYZ verify `RESULT: OK` (34 modules structurally identical to source) |
| `resources/bundled-aioncore/win32-x64/aioncore.exe` | `67EB0277` | donor core binary (kept infrastructure; attribution files ship: AionUI/AionCore LICENSE) |

Full hashes: the frozen folder's `SHA256Sums.txt` (path-format, 4 entries) and
`SHA256Sums.txt.txt` (positional — the file `verify-release.ps1` reads). Candidate package and
frozen copy verified **byte-identical** for `Kel.exe`. Prior frozen releases re-verified 3/3 and
byte-untouched.

## Verification evidence (final candidate, commit = the tagged commit)

- Engine suite: **445 passed + 10 subtests**, exit 0 (112.19 s).
- Desktop: `tsc --noEmit` 0 errors; vitest 72/72; electron-vite production build exit 0.
- Packaged probes (final package, fresh data dirs): smoke (`engineStopped`, `appExited`,
  `errors: []`), `verify-packaged-ui` (all checks, `consoleErrors: []`), a11y
  (`contrastFailureCount: 0`, `errors: []`, `emoji: 0`) → `evidence/g13/`.
- Clean clone at the release commit: `git clone --no-hardlinks` → `bun install --frozen-lockfile`
  (1591 packages) → renderer build / tsc / vitest / engine build / electron-builder / PYZ / smoke /
  packaged-UI — all green.
- Migrations: fresh + real V1.3→V1.4→V1.5 upgrade `RESULT: OK` (`13_MIGRATIONS.md`).
- Security + reliability sweeps: all charter cases re-run on this tree (`09`, `10`).
- G12 independent architecture audit: **VERDICT: CONTINUE** after remediation `ed0b35e`.

## Known limitations / deferred scope

- `16_KNOWN_LIMITATIONS.md` — including the explicit **"Surface rows deferred out of V1.5"**
  section (per-row verified reconciliation in `08_LEDGER.md`).
- `17_V2_PLUS_DEFERRED.md` — the V2+ deferred list.
