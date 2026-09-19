# 06 — DONOR DISPOSITIONS (Campaign C)

Dispositions for the donor-derived subsystem findings (AUD-MINOR-007/008/009). Decisions made
from the final Campaign B evidence; nothing was deleted on donor naming alone; legal attribution
is preserved (`AionUI-LICENSE.txt` is a config-driven packaging input of `kel-builder.json`).

## AUD-MINOR-007 — donor `aioncore` runtime — **KEEP (live backend), bind provenance**

- Reachability: `aioncore` is the app backend — `packages/desktop/src/index.ts` constructs
  `BackendLifecycleManager` (`@aionui/web-host`); the launcher spawns the resolved
  `bundled-aioncore/<platform-arch>/aioncore[.exe]` (dynamic local port; `/health` gated;
  SIGTERM/SIGKILL; crash-restart window; children cleaned up with the backend). It is a live
  runtime dependency, not dead code — removing or renaming it would reshape the architecture
  beyond this finding.
- Provenance binding (repaired): `prepare-aioncore.js` now writes, next to the donor
  `manifest.json`, a Kel-side `provenance.json` — `{binary, sha256, bytes, donorRepository:
  https://github.com/iOfficeAI/AionCore, version, sourceType, source, recordedAt, recordedBy}`;
  `build-with-builder.js` fails the build when `provenance.json` is missing.
  Reference hash (RC staged and packaged copies are byte-identical):
  `aioncore.exe` win32-x64 = `67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892`
  (`docs/v1.6/repair-final/evidence/mi7-aioncore-provenance.txt`).
- Security read: spawn uses `{...process.env}` inheritance (documented; the same containment
  policy as AUD-MINOR-003 applies to provider keys); `AIONUI_BACKEND_BIN` is a developer
  override (resolve order: env → bundled → PATH); the binary binds to a dynamic localhost port;
  and its Windows executable metadata is donor-named (`AionCore`) — packaged under
  `resources/bundled-aioncore/`, not user-visible; About/branding surfaces show Kel.
- Surface-reachability list (sweep refresh): backend spawn (live) · `bundled-aioncore` staged
  resources (shipped, provenance-bound) · `managed-resources/` (donor-managed) · donor settings
  pages that call `systemSettings` (Kel shell) · pet surface (see AUD-MINOR-008).

## AUD-MINOR-008 — desktop-pet subsystem — **DISABLED (hidden); assets inert**

- Decision: retain modules/assets (no risky deletion), disable every reachable activation path.
- Gates (repaired): `petPolicy.KEL_PET_SUBSYSTEM_ENABLED = false`; `petManager.createPetWindow`
  refuses; `systemSettingsBridge.setPetEnabled` refuses enabling (persists `false`); the
  `src/index.ts` startup path requires `pet.enabled === true && KEL_PET_SUBSYSTEM_ENABLED`.
- Reachability list (post-repair): startup init — gated · settings setter — gated · direct
  `createPetWindow()` callers — gated at definition · pet windows/IPC/renderer assets — never
  instantiated; remain shipped inert. Confirmed by `tests/unit/donor-policy.test.ts`.
- Brand/behavior leakage: none reachable (pet window cannot be created; settings toggle is a
  no-op that keeps the stored state disabled).

## AUD-MINOR-009 — builder config — **Kel config is the default**

- Decision: single obvious packaging path; donor `electron-builder.yml` remains only as the
  `extends` base of `kel-builder.json`.
- Repaired: `scripts/build-with-builder.js` uses `KEL_BUILDER_CONFIG = 'kel-builder.json'` for
  BOTH electron-builder invocations (main + mac prepackaged-DMG path) and calls
  `assertKelBuildIdentity()` before the vite build — the build refuses to run unless
  `kel-builder.json` carries `productName: Kel` and `appId: com.kel.desktop`.
- Artifact identity: bound at §17/18 package evidence (exe metadata / installer hash / ARP).
- Reachability list: default config — Kel · donor config — only as `extends` base · scripts
  (`dist`, `dist:win`, …) — all flow through the Kel default.
