# Handoff to Opus — Kel V2 line (`integration/v2`), state at r21

Written 2026-09-23 by the previous runner. **No implementation work is in flight**; the working tree is
clean and no builds are running. This document is the only artifact committed by the handoff turn.

Every factual claim below was re-verified against the files and processes at the time of writing.
Evidence class is labelled throughout:

| label | meaning |
| --- | --- |
| **[UI]** | a human/agent actually interacted with the running UI (clicked, typed) |
| **[APP-RUN]** | the real packaged app was launched and its own startup path rendered the UI; measurement was by screenshot pixel analysis (no DOM injection) |
| **[INJECTED]** | values were written directly into a throwaway store DB using the same keys/encoding the app writes, then read back by the app on a normal launch |
| **[BROWSER]** | checked through the app's WebUI origin (curl / Playwright page) |
| **[SOURCE]** | read from the repository, not observed at runtime |

---

## 1. Checkout, branch, HEAD, uncommitted changes

| item | value |
| --- | --- |
| worktree | `C:\Users\Nick\Desktop\Kel\kel-v2-integration` |
| branch | `integration/v2` |
| HEAD | `91d3202a642af48769756ea94ed6000ed9a6a9f3` (`docs(v2): r21 candidate record (dark default verified on the desktop app)`) |
| `origin/integration/v2` | `91d3202a642af48769756ea94ed6000ed9a6a9f3` — **identical**, pushed |
| uncommitted changes | **none** (tree clean; the six dark-default files landed as `219f0ce`, the record as `91d3202`) **[SOURCE]** |

Recent history (newest first): `91d3202` docs(r21) ← `219f0ce` feat: dark default ← `7dceb95` docs(r20)
← `e96df91` fix: Figma canvas under background overrides (PR #4 cherry-pick) ← `3b7b584` fix: web-host
file requests never become deep links ← `74f105a` fix: aioncore store honours `AIONUI_DATA_DIR` ←
`ccde163` candidate r17 ← `6c6775d` ← `28e9e57` ← `fe6edec`…

Sibling worktrees on the same object DB: `Kel-Repo` (`main`, `5e76b21`), `kel-v2` (`dev/v2`, `8842d9e`),
`kel-v2-canvas-fix` (`fix/v2-canvas-background`, `dee7452`), `kel-v2-figma-refresh`
(`ux/v2-figma-refresh`, `ea7de07`), `kel-v2-shell` (**Astra's lane**, `ux/v2-shell`, `0052075`).

## 2. Candidates — live, staged, rollbacks

`app.asar` sha256 (full) — `Kel.exe` / engine / aioncore shortened for readability.

| path | asar sha256 | Kel.exe | launcher |
| --- | --- | --- | --- |
| `C:\Users\Nick\KelV2Candidate` (**r20, live**) | `baaab70ae30b64625344bd8d27dcfc8aa19e933e583d0be88c9f379b1afd0e70` | `98f1b8126207bc36` | `Run-Kel-V2-Candidate.cmd` |
| `C:\Users\Nick\KelV2Candidate.r21` (**r21, staged**) | `84212ebe805e4bb0e7fc8a3086c03954c8128e64c710450242671489e72bac71` | `c17815f60797c090` | `Run-Kel-V2-Candidate.cmd` |
| `…\.r19` | `f9ae0767f798fd84ed262af662ef89e12b88be8f6de27b90ac03ed811c947ca1` | — | yes |
| `…\.r18` | `b4235af703fec1f7ffd59a85772896918506b8eaa44e3e880fa9717b5b197796` | — | yes |
| `…\.r17` | `75ef03c017cb94eb58aa75cb0da0862937142717db615c33fc520428e410c19a` | — | yes |
| `…\.r16` / `.r15` / `.r14` | `88f343733485e2f4…` / `b6335e04348f2fc8…` / `c4463f57dbf38754…` | — | yes |
| `C:\Users\Nick\KelV2CanvasCandidate` (PR #4's verification copy) | `01088642639d804f44b4f9d0576325ab170c1e65c1510191f763471eb342d167` | — | own launcher, differently named |

Both r20 and r21 carry the **same frozen engine** (`resources\kel-engine\KelEngine.exe`
`00846a7e64fdaa95…`) and the **same donor host**
(`resources\bundled-aioncore\win32-x64\aioncore.exe` `67eb02774bab3855…`).

Launcher semantics (identical in both candidate dirs): sets
`KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate` and
`AIONUI_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate\desktop-store`, then `start "" "%~dp0Kel.exe"`.

**Why r21 is staged and not live:** the user's own r20 session was running from
`C:\Users\Nick\KelV2Candidate` for the whole verification pass. Renaming that directory is refused by
Windows while its `Kel.exe` image is mapped (`The process cannot access the file because it is being
used by another process`), and killing a session the runner did not launch is out of bounds. To
promote r21 after the app is closed:

```powershell
Rename-Item C:\Users\Nick\KelV2Candidate     C:\Users\Nick\KelV2Candidate.r20
Rename-Item C:\Users\Nick\KelV2Candidate.r21 C:\Users\Nick\KelV2Candidate
```

## 3. Completed work, with evidence

| # | work | commit | evidence | class |
| --- | --- | --- | --- | --- |
| 1 | **F1** — packaged WebUI Kel surfaces had no engine: `startWebHost` was given the store dir and never `kelDataDir`, so `/kel/*` fell through to the SPA | `8117742` (+ record `28e9e57`) | `docs/v2/evidence/v2-19/audit-r16/AUDIT_R16.md`, `docs/v2/evidence/CANDIDATE_R17.md`, `docs/v2/evidence/v2-18/runs/2026-09-23-r17-f1-repair.json` | **[BROWSER]** gateway JSON vs HTML, **[SOURCE]** root cause |
| 2 | Engine root + **desktop store** isolation: `getDataPath()` now returns `AIONUI_DATA_DIR` when set; aioncore's DB, conversations and `webui.config.json` stop sharing the machine-wide store | `74f105a`, record `e107452` | `docs/v2/evidence/v2-19/CANDIDATE_R18.md` | **[APP-RUN]** both directions (set → isolated dir created, shared store untouched; unset → default path again) |
| 3 | **Manifest fix** — `/manifest.webmanifest` was deep-linked into `/#/manifest.webmanifest`, so the browser parsed HTML as the PWA manifest; `ASSET_FILE` bound `{1,8}` → `{1,12}` | `3b7b584`, record `7dceb95` | `CANDIDATE_R19.md`; regression test in `desktop/packages/web-host/src/static-server.unit.test.ts`; web-host suite **100 passed / 3 todo** | **[BROWSER]** 200 `application/manifest+json`; **[SOURCE]** unit test |
| 4 | **Dark canvas repair (PR #4)** — a saved `App background` no longer replaces the Figma stack; the saved colour becomes base + 20% tint | cherry-pick `e96df91` of PR `6a3df71`; PR closed with the record | `docs/v2/evidence/v2-19/CANVAS_FIX.md` (+ integration section), `CANDIDATE_R20.md` | **[BROWSER]** computed background with saved `#282a34` on r20 |
| 5 | **Dark by default for new profiles** — six renderer files stop assuming Light where nothing is saved | `219f0ce`, record `91d3202` | `CANDIDATE_R21.md`; theme test `tests/unit/kel-shell-theme.dom.test.ts` | **[APP-RUN]** four runs (fresh → dark; saved Light → light; saved dark + custom canvas → tint with artwork; restart → identical) |
| 6 | V2-05 ledger truth-up (history, attention actions, conversational routing landed) | `74f105a` | `docs/v2/FEATURE_LEDGER.md`, `ROADMAP.md` | **[SOURCE]** |

`/api/state?conversation=main → 403` (the console loop from audit r16) was **closed as not-a-defect**:
exhaustive greps find no bare-path caller, and it does not reproduce in r18/r21 on an empty store, a
data store, or the dev build. Evidence: `AUDIT_R16.md` → “Follow-up pass 2”. **[SOURCE] + [BROWSER]**

## 4. Remaining defects, incomplete checks, next recommended task

**Open defects / known gaps**

1. **Theme-card wrapping** visible in the PR #4 comparison screenshot — acknowledged, untouched.
2. **Electron profile/log locations** still shared (`%APPDATA%\kel-aionui`) between apps; moving them
   would move the stable app's profile too. Deliberately unchanged; needs its own decision.
3. **Donor bootstrap noise** on a signed-out page: `/api/settings/client`, `/api/auth/*`,
   `/api/cron/jobs` → 401, plus repeated `ws://…/ws` auth failures. Expected refusals, not defects.
4. **V2-16 timings** for conversation-open and project-switch — never measured. They need a signed-in
   session; the runner does not enter credentials or copy the stable app's session data. Method is
   ready in `AUDIT_R16.md` → “V2-16 instrumentation”. Document-load numbers exist
   (r18: DCL 477 ms / load 570 ms; r19: 532/627 ms) **[BROWSER]**.
5. **Signed-in surfaces never clicked**: Work, Settings, and the command palette have not been driven
   in this line. Work/Settings *bundles* are verified present and served (200), and the sign-in gate
   itself works **[BROWSER]**, but that is not a UI pass.

**Next recommended task (in order)**

1. Promote r21 (two renames above) once the user's app is closed, then re-run the gate + isolated
   launch checks against the promoted path (§5).
2. With a session available: drive **Settings colour rows → canvas colour change** and the **command
   palette theme switch** end-to-end **[UI]**, and take the two V2-16 timings with the documented
   condition-based method. Record numbers, not estimates.
3. Only then start the broad **V2-19 audit** (the earlier directive deliberately deferred it).

## 5. Exact commands (as actually run)

All paths are Git-Bash on Windows; `desktop/` = `C:\Users\Nick\Desktop\Kel\kel-v2-integration\desktop`.
Node `v24.18.0`, Bun `1.4.2` at the time of writing.

```bash
# typecheck (clean)
cd desktop && bunx tsc --noEmit -p tsconfig.json

# theme test (1 passed)
cd desktop && npx vitest run tests/unit/kel-shell-theme.dom.test.ts

# web-host suite (100 passed / 3 todo; stop any running Kel app first — a live instance
# interferes with the gateway tests' port/descriptor fixtures)
cd desktop/packages/web-host && ../../node_modules/.bin/vitest run

# renderer + main build
cd desktop && NODE_OPTIONS="--max-old-space-size=8192" bun run package

# single-packer archive (never run two packers; ~10 min)
cd desktop && rm -rf ../dist/package-r12/win-unpacked && \
  NODE_OPTIONS="--max-old-space-size=8192" ./node_modules/.bin/electron-builder \
    --config kel-builder.json --x64 --dir
# expect: "PACKnn_EXIT=0" and "signing with signtool.exe … Kel.exe"
```

**Packaging gate** (run before installing; aborts if any check fails). Checks: exactly one `app.asar`
and one `Kel.exe`, zero `electron.exe`, no stray `*unpacked*` directories, exactly the expected 15
DLLs, engine `00846a7e…` and aioncore `67eb0277…` unchanged, and the archive marks
(`data-theme="dark"`, `arco-theme="dark"`, `DARK_THEME_ID`, the canvas-repair `color-mix` string, the
r19 manifest fix). The python one-liner used is reproduced in the r20/r21 candidate records; re-derive
it rather than trusting a copy.

**Install / rollback dance** (only when no candidate app is running):

```bash
powershell.exe -NoProfile -Command "
  Rename-Item C:\Users\Nick\KelV2Candidate C:\Users\Nick\KelV2Candidate.rNN ;
  Copy-Item <build>/win-unpacked C:\Users\Nick\KelV2Candidate -Recurse -Force"
# then re-create Run-Kel-V2-Candidate.cmd (content in §2) and hash-verify every preserved dir
```

**Isolated launch — desktop app (the real app, fresh profile/store/engine).** Uses scratch helpers
outside the repo: `C:\tmp\run-r21-verify.cmd`, `C:\tmp\seed.py`, `C:\tmp\kelwin.ps1`.
`AIONUI_MULTI_INSTANCE=1` is required to run beside another instance (the app takes a single-instance
lock otherwise) and `--user-data-dir` keeps the shared Electron profile out of the way:

```cmd
set "AIONUI_MULTI_INSTANCE=1"
set "KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r21-verify\engine"
set "AIONUI_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r21-verify\store"
start "" "C:\Users\Nick\KelV2Candidate.r21\Kel.exe" --user-data-dir="C:\Users\Nick\KelV2Runs\prepared\r21-verify\profile"
```

Capture + pixel analysis of the window (mean luminance, canvas-band colour count, per-channel SD,
fixed sample points) and the theme seeding:

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\tmp\kelwin.ps1 -ProcId <pid> \
  -OutPng C:\Users\Nick\KelV2Runs\prepared\r21-verify\shots\vN.png
python C:/tmp/seed.py <store>/aionui-backend.db '{"theme.activeId": {"json": "light"}}'
```

**Isolated launch — WebUI/gateway checks** (repeat of the r19/r20 checks; needs no session):

```bash
cd /c/Users/Nick/KelV2Candidate && KEL_DATA_DIR=<engine> AIONUI_DATA_DIR=<store> ./Kel.exe --webui
curl -s -D - -o /tmp/m.out http://127.0.0.1:25808/manifest.webmanifest   # 200, 529 B JSON
curl -s http://127.0.0.1:25808/kel/api/state                            # JSON 401 UNAUTHORIZED (never HTML)
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://127.0.0.1:25808/work  # 302 -> /#/work
```

**Stop only what you started** (identity-checked by executable path):

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'Kel.exe' -and $_.ExecutablePath -like '*KelV2Candidate.r21*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## 6. Protected — do not touch

| protected | state verified at handoff |
| --- | --- |
| stable install `C:\Users\Nick\KelDogfoodCandidate` | `app.asar` 299,973,841 B, sha256 `4f23c9aecb8288a6ccbe8cd88076ea79a6b731b45a25a0aec03c729a6a8e9c41` — unchanged |
| stable data `C:\Users\Nick\KelDogfoodRuns\prepared` (+ `\engine`) | present, used only by the stable engine |
| shortcuts | `C:\Users\Nick\Desktop\Kel.lnk`, `C:\Users\Nick\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Kel.lnk` — untouched |
| `main` (`Kel-Repo`) and Astra's lane `ux/v2-shell` @ `0052075` (worktree `C:\Users\Nick\Desktop\Kel\kel-v2-shell`) | clean; never edited |
| never promote V2; never install over the stable app; never point a V2 run at the stable data root | standing rule |

**Processes at handoff** (leave them alone): the stable engine `26544`; the user's own desktop app
stack from `C:\Users\Nick\KelV2Candidate` — `6356`, `65916`, `60804`, `53340` (`Kel.exe`), `43024`
(`aioncore.exe`), `10848` (`KelEngine.exe`). All r21 verification processes were stopped.

**Runtime data paths in play** (confirm before testing — the same exe serves three stores):

- candidate launcher store: `C:\Users\Nick\KelV2Runs\prepared\candidate`
  (+ `\desktop-store\aionui-backend.db`, `client_preferences` holds per-profile settings)
- isolated engine root used by journeys: `C:\Users\Nick\KelV2Runs\prepared\engine`
- r17/r18 audit copies: `…\prepared\audit17-engine`, `…\prepared\audit17-web`
- throwaway verification roots: `…\prepared\r21-verify\{engine,store,profile,shots}`
- the **stable** app's data root (`C:\Users\Nick\KelDogfoodRuns\prepared\engine`) must never be a
  target of a V2 run

**Rollback candidates, hash-verified at handoff**: `KelV2Candidate` (r20), `.r21` (staged r21), `.r19`,
`.r18`, `.r17`, `.r16`, `.r15`, `.r14`, plus `KelV2CanvasCandidate` (PR #4's own copy). Hash table in
§2; any mismatch means the archive was rebuilt, not merely copied.

## 7. Evidence class — what was and was not a UI interaction

- **[UI]** — none by the previous runner. No clicks, no typing, no sign-in. The user themselves
  reached desktop setup without signing in (that is user-reported context, not a runner check).
- **[APP-RUN]** — the four r21 desktop runs: the packaged app was launched through its isolated
  launcher and its own startup path rendered; the runner measured pixels (mean luminance, canvas-band
  colour count/SD, sample points) from a 1816×1189 window capture. Screenshots:
  `C:\Users\Nick\KelV2Runs\prepared\r21-verify\shots\{v1-fresh,v2-saved-light,v3-custom-canvas,v4-restart-same}.png`.
  This is stronger than a source claim and weaker than a click-through: nothing was driven.
- **[INJECTED]** — `theme.activeId` and `theme.overrides` were written into the *throwaway*
  verification store's `client_preferences` (same keys/encoding the app writes); the app then read them
  on a normal launch. The user's store and the shared Electron profile were not written to. A
  *clicked* Settings colour change has **not** been done.
- **[BROWSER]** — WebUI-origin checks (manifest, gateway, deep links) by curl; r20 canvas CSS read and
  console/network traces by Playwright. These exercise the packaged renderer but are not the desktop
  window.
- **[SOURCE]** — the six-file dark-default review, gateway/theme-persistence reading, greps, and the
  `FEATURE_LEDGER`/`ROADMAP` truth-up.
