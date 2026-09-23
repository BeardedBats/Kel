# Kel V2 candidate r20 — one archive with the manifest fix and PR #4's dark canvas repair

Built from `integration/v2` @ **`e96df91`** (+ the record commit that follows it), packed 2026-09-23
13:34Z by **one** packer (`electron-builder --config kel-builder.json --x64 --dir`, exit 0, signed);
typecheck clean before the build.

## What it combines

| source | change | origin |
| --- | --- | --- |
| `web-host/src/static-server.ts` | `ASSET_FILE` bound `{1,8}` → `{1,12}`: file requests (e.g. `/manifest.webmanifest`) are never turned into hash routes | r19 (`3b7b584`) |
| `renderer/styles/kel-shell.css` | the dark shell paints the Figma SVG + gradients in every case; a saved App background color supplies the base and a 20% tint instead of replacing the stack | **PR #4**, cherry-picked as `e96df91` from its `6a3df71` |

The PR branch itself was **not** merged wholesale: it lagged `integration/v2` by the r19 commit and
carried two now-redundant merge commits. Its evidence doc came across with an integration section
that marks what in it is superseded (`docs/v2/evidence/v2-19/CANVAS_FIX.md`).

## Archive gate — the preconditions for *keeping* the candidate

| check | r20 | r19 |
| --- | --- | --- |
| `app.asar` | 1 copy, 300,586,077 B, `baaab70ae30b6462` | 300,585,830 B, `f9ae0767f798fd84` |
| `Kel.exe` | 1 copy, 204,575,232 B, `98f1b8126207bc36` | `460c966d1f917745` |
| `electron.exe` | **0** | 0 |
| stray `*unpacked*` dirs | none | none |
| frozen engine | `00846a7e64fdaa95` — byte-identical | same |
| donor aioncore | `67eb02774bab3855` — unchanged | same |
| DLL set | 15, the expected set | same |
| repaired CSS inside the archive | both markers present (`background-color:var(--kel-shell-custom-canvas, var(--kel-figma-color-canvas-base))`, `color-mix(in srgb,var(--kel-shell-custom-canvas…`) | n/a |

`canvas.svg` is 2,982 B, under Vite's inline limit, so the artwork ships as a `data:image/svg+xml`
URI inside the bundled CSS (two such URIs in `assets/index-*.css`) — there is no loose `canvas.svg`
to find in the archive, and none is needed.

## Isolated launch checks (r20, launched with both data-root variables set)

- **Engine ownership** — the protected stable engine (`--data …/KelDogfoodRuns/prepared/engine`) and
  r20's (`--data …/KelV2Runs/prepared/candidate`); nothing else.
- **Store** — `…\prepared\candidate\desktop-store\aionui-backend.db` (913,408 B + WAL).
- **Manifest** — `GET /manifest.webmanifest` → **200**, `Content-Length: 529`, body parses as JSON
  (`{"name":"Kel", …}`).
- **Gateway** — `/kel/api/state` → JSON (`{"success":false,"error":"Authentication required",…}`).
- **Deep links** — `/work` → `302 /#/work` (the r19 fix kept the real routes working).
- **Auth gate** — an unauthenticated visit still lands on `#/login`; the packaged server serves its
  bundles (`assets/index-*.js`, `vendor-*.js`, `applyTheme-*.js` → 200) including the Settings chunk
  family, and the Work/Map/Kibble routes are present in the built renderer.

## Packaged dark canvas (the repair, exercised in the packaged renderer)

Read from the packaged page against a `.kel-v2-shell` element with `data-theme="dark"`:

| case | computed background | artwork | gradients |
| --- | --- | --- | --- |
| saved color `#282a34` | `background-color: rgb(40, 42, 52)`, tint layer `color(srgb 0.156863 0.164706 0.203922 …)` (the saved color at 20%) | **SVG data URI present** | 3 layers |
| no override | `background-color: rgb(11, 23, 52)` (the Figma base token), tint layer transparent | **SVG data URI present** | 3 layers |

`background-size: 100% 100%` and `background-position: 50% 50%` on every layer. The saved color is
kept and applied as base + tint; clearing it restores the untinted Figma canvas.

## Rollback

- **r19 preserved** at `C:\Users\Nick\KelV2Candidate.r19` (`f9ae0767…`, verified), r18 at `…\.r18`
  (`b4235af7…`), r17 at `…\.r17` (`75ef03c0…`).
- `C:\Users\Nick\KelV2CanvasCandidate` (the PR's own verification copy) is left in place for reference.
- Launcher: `C:\Users\Nick\KelV2Candidate\Run-Kel-V2-Candidate.cmd`.
- Never promoted; the stable install, its data and the shortcut were not touched.

## Unresolved (do not read as verified)

- **Work and Settings as rendered signed-in pages** — this pass could not open them: both are behind
  the sign-in gate and the runner does not enter credentials or copy the stable app's session data.
  What is verified is that the archive ships their bundles and serves them (200) and that the gate
  itself still works.
- **The dark canvas was exercised with the saved color applied to the shell element** — the app's own
  settings path (a saved `App background` in Settings) was verified by PR #4 on its own copy; a
  signed-in Settings run remains the way to re-confirm that path on r20.
- **V2-16 conversation-open / project-switch timings** — still blocked on a signed-in session.
- The theme-card wrapping noted in `CANVAS_FIX.md` is untouched, as the PR itself recorded.
