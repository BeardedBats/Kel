# Branding evidence — canonical logo (2026-09-18)

Selection of the raw captures produced for REQ-LOGO-1. Full raw sets (more screenshots + JSON) live
outside the repo at `dist/logo-evidence/ux-audit/` (regenerable; see the commands below).

| File | What it shows | How it was produced | Verification |
|---|---|---|---|
| `about-screen-kel-logo.png` |  packaged Settings → **About** page with the new canonical K mark | `packaging/ux-audit.cjs <appDir> <rootDir> <outDir> settings` (isolated profile, offscreen window) | `python scripts/verify-brand-render.py dist/logo-evidence/ux-audit --sizes 40,48,56,64,72,80` → **0.960** masked NCC for this capture (other 18 captures ≤ 0.51 baseline) |
| `packaged-boot.png` | packaged app boot/first paint (launch proof) | same harness, `first-run` scenario | harness reported `errors: []`; `timeToComposerMs` present in `ux-first-run.json` |
| `packaged-landing.png` | post-onboarding landing surface | same harness, `first-run` scenario | `errors: []` |
| `exe-icon-extracted.png` | icon extracted from `dist/package-logo/win-unpacked/Kel.exe` | `[System.Drawing.Icon]::ExtractAssociatedIcon(Kel.exe)` | mean abs diff vs shipped `resources/app.ico` 32 px frame = **0.0** |
| `installer-icon-extracted.png` | icon extracted from the NSIS installer `Kel-1.5.0-win-x64.exe` | same extraction | mean abs diff vs shipped `app.ico` = **0.0** |
| `exe-icon-extracted-previous-package.png` | icon extracted from the previous package (`package-final17`) for contrast | same extraction | **not** the K (mean abs diff 73.2); that build also reported Electron's own identity (`ProductName=Electron`, `CompanyName=GitHub, Inc.`) |

Reproduce:

```bash
python scripts/make-brand-assets.py "C:/Users/Nick/Desktop/Kel Logo.png"     # derivatives (sha256-guarded)
PLAYWRIGHT_MODULE=<node_modules-with-playwright> node packaging/ux-audit.cjs \
  dist/package-logo/win-unpacked dist/logo-evidence/root dist/logo-evidence/ux-audit settings
python scripts/verify-brand-render.py dist/logo-evidence/ux-audit --sizes 40,48,56,64,72,80
```

Note: the packaged **login** screen renders the same asset (`renderer/assets/logos/brand/app.png`)
as the About screen; the About capture is the rendered proof of that asset. The login route requires
an authenticated/webui account, which this environment cannot configure (no credentials), so no
separate login capture exists — recorded as a residual gap, not a pass.
