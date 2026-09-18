# Increment — R8: packaged / migration assertions + REL-01

increment_id: V16-R8-PACKAGE-ASSERTIONS
invariants: **PACKAGE-IDENTITY** (packaged Kel executes the runtime artifact the release evidence
identifies) · **FREEZE-IMMUTABLE** (frozen releases stay byte-untouched)
requirements: `REQ-R25-R8` (= REQ-PKG-ASSERT + REL-01), marathon directive §16
phase: Campaign A — R8 (the minimum marathon return gate)
base_commit: `e8bbb05`
production_commits: `2468b16` (R8.A migrations), `93b99b5` (R8.B/C/D package identity + REL-01)
status: complete

## R8.A — migrations

Exercised the whole module migration set (19 modules, markers 1–21) on a fresh database and on an
existing one:

- **Fresh**: every module's `ensure_schema` runs; `schema_migrations` reaches the intended maximum
  **exactly once**, with unique module markers and the expected names (20 =
  `chat_approval_announcements`, 21 = `v16-budget-reservations`).
- **Idempotent**: a second full run changes nothing.
- **Upgrade**: an existing database keeps its rows; deleting the newest marker and re-running stamps
  it again without touching data (no downgrade, no rewrite).
- **Defect found and fixed**: `workforce` and `assignment` both claimed version **17**. Because
  `version` is the primary key, the row could not say which migration had been applied (diagnostics
  misattributed it, and the number was unusable for a future migration). `assignment` moved to 21;
  the module-constant uniqueness test is the direct guard.
- Tests: `tests/test_v16_r8_migrations.py` (4).

## R8.B — package identity

- **Defect found and fixed**: the engine self-reported `1.5.0` on the V1.6 branch
  (`kel/__init__.py` plus a duplicated `service.ENGINE_VERSION` literal) while the desktop's reuse
  guard compares `app.getVersion()` (the packaged `desktop/package.json` version) to the engine's
  reported version. A V1.6 desktop would have refused its own fresh engine (or the pair would ship
  mislabeled). Now `__version__ = "1.6.0"` is the single source, `ENGINE_VERSION` derives from it,
  and `desktop/package.json` matches (asserted by test, so the two ends can never drift silently).
- Tests: `tests/test_v16_r8_identity.py` (3); desktop `engineVersion.test.ts` (3).

## R8.C — REL-01: the runtime that is hashed is the runtime that loads

The real path chain: `build-runtime.ps1` → `dist/runtime/KelEngine` → electron-builder
`extraResources` → `resources/kel-engine` (the load path; `verify-release.ps1` hashes exactly
`resources/kel-engine/KelEngine.exe`) → `freeze-release.ps1` → sums/manifest.

**REL-01 was live**: the freeze copied the staged runtime with `Copy-Item -Recurse <dir> <existing
dir>`, which nests the fresh build at `resources/kel-engine/KelEngine/…` and leaves the package's own
(possibly stale) engine at the path the app loads — evidence could hash one runtime while the app
loads another. Reproduced while writing the fixture (the half-nested destination even reported
"being used by another process").

Fix: the load-path directory is removed and re-created from the staged runtime, and the freeze now
**refuses** (SHA-256 comparisons) to assemble a release when the staged copy did not land at the load
path or when the package bundles a different engine than the runtime being frozen. The manifest notes
that the load-path hash equals the staged hash by construction.

**Non-release validation fixture** (`scripts/validate-freeze.ps1`, per the directive): builds a
synthetic package carrying the freshly built runtime, freezes into `dist/validation-freeze`, verifies
with `verify-release.ps1` against the freeze's own sums, then tampers the package's bundled engine
and asserts the freeze is refused.

Evidence (this run):

```
-- positive: freeze
Release assembled at .../dist/validation-freeze
-- positive: verify
OK    Kel.exe
OK    resources/app.asar
OK    resources/kel-engine/KelEngine.exe
Release verification passed.
-- negative: a package bundling a different engine must be refused
REL-01 validation passed: load-path hash == staged runtime hash; divergence refused (exit 1).
```

No nested runtime in the frozen tree (grep count 0).

## R8.D — packaged assertions

Executed against the **frozen load-path binary** with a fresh data dir:

- **basic launch**: the frozen `KelEngine.exe` boots, writes its descriptor and serves HTTP;
- **migrations inside the packaged app**: the fresh data dir received `kel.sqlite3`, backups dir,
  controller lock and `desktop-session.json` (the packaged engine ran the full schema itself);
- **runtime identity**: `desktop-session.json` → `{"engine_version":"1.6.0", …}`; authenticated
  `/api/state` → `engine_version 1.6.0`, `connected true`, `guardrails_ok true`;
- **provider discovery**: `/api/state` lists 4 providers;
- **no old donor engine path / no stale runtime nesting**: the frozen tree has no nested
  `resources/kel-engine/KelEngine/`, and the load path is the only engine binary;
- **canonical logo resources**: the desktop package's branding was verified in the branding
  increment (`docs/v1.6/branding/CANONICAL_LOGO.md`, `scripts/make-brand-assets.py` +
  `verify-brand-render.py`); the packaged-icon battery re-runs at R12's full package.
- **REL-01**: closed by the fixture above (positive + negative); the *release freeze itself* remains a
  future release step that Campaign A must not perform.

## Limitations / audit questions / repair hints

- The electron-builder **installer** battery (NSIS run, Start-Menu icon, uninstaller) is scheduled
  with R12's full packaged regression; this increment proves the runtime-carrying artifacts and the
  freeze/verify chain. The R12 run must re-run `validate-freeze.ps1` against the real package.
- `Kel.exe`/`app.asar` in the fixture are synthetic stubs (the freeze only copies and hashes them);
  the real package's asar/executable enter the chain at R12.
- Audit questions: (a) does any prior frozen release directory differ from its recorded sums (spot
  check)? (b) does the electron-builder package step itself copy the runtime *before* or *after*
  `build-runtime.ps1` (ordering assumption documented here)? (c) should `verify-release.ps1` also
  verify the nested-path absence (the negative fixture covers the freeze side)?
- Repair hints: none open from this increment.
