# G10 packaging-acceptance evidence (Kel V1.5)

Provenance: recorded 2026-09-16 against the packaged dir build at
`dist/package/win-unpacked` (electron-builder dir target, `kel-builder.json`; Kel.exe present;
no `app-update.yml`), with a freshly rebuilt renderer (`electron-vite build`) and the V1.5
`KelEngine` rebuilt from source by `scripts/build-runtime.ps1`.

Commands (from the repo root; `NODE_PATH` = `desktop/node_modules`):

```text
node packaging/verify-packaged-ui.cjs <appDir> <fresh dataDir>   # -> packaged-ui.json
node packaging/capture-screens.cjs   <appDir> <fresh dataDir> <outDir> --tag v15 \
     --widths 1440x900,1920x1080                                 # -> 25 screenshots (index below)
node packaging/a11y-probe.cjs        <appDir> <fresh dataDir> <outDir>  # -> a11y.json
```

Results:

- `packaged-ui.json` — every check present and truthy (title `Kel`, Work button, all eight
  drawer tabs, three empty states, recipe preview); `consoleErrors: []`; app exit 0.
- `a11y.json` — `contrastFailureCount: 0` in both measured sections, `errors: []`,
  `emoji: 0`, smallest text 12 px, 30 focus stops, clean close. This file is the
  **post-fix** measurement: the first run found the donor empty-state caption at 2:1
  (rgb(169,174,184) on rgb(242,243,245)); the fix pins `.arco-empty .arco-empty-description`
  to the corrected muted token in `arco-override.css`, and the packaged re-run measures 0.
- `shots-index.txt` — the 25 captured screenshots (boot/chat, work drawer + each tab,
  recipes + preview, map refresh, settings sections) at 1440x900 and 1920x1080. PNGs live in
  the run output directory; they are regenerable with the command above.

Packaging pipeline fixes proven by this run (commit `0fba928`): duplicate inherited
`extraResources` entries removed (was a deterministic EBUSY on `aioncore.exe`), and the
afterPack native rebuild now fetches the official prebuilt for the pinned Electron ABI
(read from `electron.exe` itself) instead of requiring `bun`/`node-abi` — packaged
`better_sqlite3.node` is the Electron-ABI build (1,901,568 bytes).
