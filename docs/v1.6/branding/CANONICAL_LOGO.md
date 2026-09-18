# Canonical Kel logo — requirement, source, derivatives, surfaces

Requirement: **"The exact Nick-supplied folded-ribbon K is the canonical Kel logo and appears
consistently across all production-reachable Kel branding surfaces."** (REQ-LOGO-1, added to the
pre-audit corpus on 2026-09-18.)

## 1. The canonical source (preserved, never modified)

| Field | Value |
|---|---|
| File as supplied | `C:\Users\Nick\Desktop\Kel Logo.png` |
| sha256 | `7418a42fc06267707c1e1aa4ab0d8822e8d636a687a81f200788a7b3e50ec71f` |
| Bytes / format | 1,854,527 · PNG RGBA |
| Dimensions | 1254 × 1254 (transparent; 48.2% fully transparent, corners `(0,0,0,0)`) |
| Colour family | blues — centre pixel `(17,94,170)`; dominant buckets `(144,192,240)`, `(48,96,192)`, `(0,48,144)` |
| Candidate check | two other Desktop images (`3079a91c-…png`, `…-no-bg.png`, both 12:21–12:22) are the same artwork **with a light-grey background** (opaque / haloed alpha). The 12:25 file literally named "Kel Logo.png" is the clean transparent export → chosen as canonical. |
| In-repo copy | `desktop/resources/branding/kel-logo.png` — **byte-identical** (same sha256), and the original on Nick's Desktop is untouched. |

Nothing regenerates, redraws, recolours, simplifies, distorts or crops the mark. Each derivative
only (a) trims fully transparent margin, (b) scales uniformly preserving aspect ratio, and
(c) recentres on a transparent square canvas with a uniform inset. All resampling is premultiplied
alpha, so the soft edges never gain a dark/black fringe.

## 2. Derivative generation (reproducible)

`scripts/make-brand-assets.py <canonical.png> [--check]` — refuses to run unless the source sha256
matches the recorded constant; writes every output and prints their hashes (`--check` verifies
without writing). Outputs (sha256 recorded at generation time):

| Output | Canvas / frames | Purpose |
|---|---|---|
| `desktop/resources/branding/kel-logo.png` | — (byte copy) | canonical in-repo source |
| `desktop/resources/app.ico` | 16/24/32/48/64/128/256 | exe + installer + shortcuts (Windows) |
| `desktop/resources/app.png` | 1024 | tray, notifications, linux package icon |
| `desktop/resources/app_dev.png` | 1024, padded | dev-mode window/dock icon (Linux/macOS) |
| `desktop/resources/icon.png` | 800 | spare build resource (was donor art) |
| `desktop/resources/app.icns` | ic11/12/07/13/08/14/09/10 | macOS bundle icon |
| `desktop/public/pwa/icon-180.png` | 180 | apple-touch-icon |
| `desktop/public/pwa/icon-192.png` | 192 | favicon + PWA |
| `desktop/public/pwa/icon-512.png` | 512 | PWA |
| `desktop/packages/desktop/src/renderer/assets/logos/brand/app.png` | 1024 | in-app brand mark (login + About) |

## 3. Surfaces wired (all production-reachable branding)

| Surface | Wiring |
|---|---|
| App icon / exe icon / taskbar | `desktop/resources/app.ico`; `kel-builder.json` `win.icon` + **`signAndEditExecutable: true`** (was `false`, so the exe previously kept Electron's default icon — the packaged check below proves the K now lands in `Kel.exe`) |
| Installer / uninstaller / header icon | `kel-builder.json` `nsis.installerIcon/uninstallerIcon/installerHeaderIcon` → `resources/app.ico`; `shortcutName: Kel` |
| Start-menu / desktop shortcuts | derived by NSIS from the app icon; `createDesktopShortcut`/`createStartMenuShortcut` already true |
| Tray + notification icon | `resources/app.png` (`tray.ts`, `notificationBridge.ts`) |
| Dev-mode window icon (win) / dock (mac) | `resources/app.ico` / `resources/app_dev.png` (`src/index.ts`) |
| Linux package icon | `kel-builder.json` `linux.icon` → `resources/app.png` |
| macOS bundle icon | `kel-builder.json` `mac.icon` → `resources/app.icns` |
| Favicon / apple-touch / PWA icons | `desktop/public/pwa/icon-180/192/512.png` (referenced by `renderer/index.html` + `manifest.webmanifest`) |
| Login / onboarding brand mark | `renderer/assets/logos/brand/app.png` (imported by `pages/login/index.tsx`) |
| About screen | **new** brand mark above the "Kel" title (`AboutModalContent.tsx`, `data-testid='kel-about-logo'`) |
| Splash / loading | none exists in this product (verified: no splash surface in the renderer) |

## 4. Explicitly NOT changed (with reasons)

| Item | Why |
|---|---|
| `resources/aionui_*.png/svg`, `homepage.png`, `bannerimage.png`, `assitants.png`, `ai-assistants-experts.png`, `screenshot_*.png`, `webui-remote*.png`, `bug-report-button.png`, `contactus-x.png`, `linuxdo.png`, `llm_newapi.png`, `multi-model.png`, `openclawvia.png`, `packycode.png`, `kimi/*` | Donor **marketing/README** images; none is referenced by production code, and `resources/` ships only what `extraResources`/`files` name (`app.png`, `bundled-aioncore`, `hub`). Not production-reachable. |
| `renderer/assets/logo.svg` | Donor AionUi mark, **no importers** (dead asset). Left for the same dormant-boundary policy as Phase 4; recorded as audit target 47. |
| `desktop/resources/windows/*.nsh` installer text + `$INSTDIR\AionUi.exe` verification | Donor installer messages/identifiers. The Kel build **does** produce an NSIS installer (`win.target` merges `nsis` + `dir`), but these `.nsh` files are **not included** by the builder config (no `include:` key), so the shipped installer uses electron-builder's stock Kel-named template and the donor text is inert. Audit target 48. |
| `desktop/package.json` `description` ("Kel with the AionUI interface") and `author` (AionUi / donor email) | Possible **deliberate attribution** rather than branding; metadata is not a logo surface, and the Apache-2.0 attribution lives in `LICENSE`/`NOTICE`/`THIRD_PARTY_NOTICES` (unchanged). Note: `author` **does** reach the shipped exe (`CompanyName=AionUi`). Recorded as audit target 49. |
| `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES`, license headers | Legal attribution — never removed. |
| Frozen releases / `dist/package-*` (older) | Immutable by policy. |

## 5. Validation

| Check | Result |
|---|---|
| Derivative corners transparent (no unintended opaque/black background) | PASS — all four corners `(0,0,0,0)` at 32/192/1024 |
| Shape preserved across sizes (16→256) | PASS — preview at 32 px keeps the folded-ribbon K, centred, undistorted |
| Determinism | `make-brand-assets.py --check` reproduces the same hashes (see §2) |
| TypeScript | `bunx tsc --noEmit` → 0 errors |
| Unit tests | `bun run test` → 90 passed (7 files) |
| Packaged build | `package-logo` (see PACKAGED_EVIDENCE_INDEX) — exe icon extraction + boot + screenshots recorded there |
| Packaged UI render (Settings → About) | PASS — `python scripts/verify-brand-render.py dist/logo-evidence/ux-audit --sizes 40,48,56,64,72,80` finds the canonical artwork with **0.960** masked NCC in `settings-_settings_about.png`; the other 18 captures stay ≤ 0.51 (baseline). Committed capture: `docs/v1.6/branding/evidence/about-screen-kel-logo.png`. |
| Packaged UI harness | PASS — `packaging/ux-audit.cjs` (`first-run`, `settings`) with an isolated profile: `errors: []` for both; app booted and rendered. |
| Login mark | Not separately captured — the login route requires an authenticated account this environment cannot configure; it renders the *same* asset as the About screen (`renderer/assets/logos/brand/app.png`), whose rendered proof is above. Residual gap (no credentials), never a pass. |
| Human judgment remaining | 16 px legibility of the exe/tray derivative and the About placement/density are a human pixel-gate item (VISUAL_EVIDENCE_INDEX). |
