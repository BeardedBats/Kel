# V2 CANDIDATE r17 — verified (2026-09-23)

Supersedes r16 (preserved at `C:\Users\Nick\KelV2Candidate.r16`; its record is `CANDIDATE_R16.md`).
r17 is the first candidate built with the **F1 repair** (`8117742`) and Astra's **Figma refresh**
(`ea7de07`, merged in `fe6edec`).

## What exists

| | |
| --- | --- |
| Candidate | `C:\Users\Nick\KelV2Candidate` |
| Launcher | `C:\Users\Nick\KelV2Candidate\Run-Kel-V2-Candidate.cmd` — exports `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate`, then starts `Kel.exe` in that folder |
| Source | `integration/v2` — the commit that carries this file (parents: `6c6775d`, `8117742`, `fe6edec`) |
| `Kel.exe` | 204,575,232 bytes, sha256 `4726f92685953e249f02e26c308fe6e7` |
| `resources\app.asar` | 300,584,430 bytes, sha256 `75ef03c017cb94eb58aa75cb0da08629` |
| `resources\kel-engine\KelEngine.exe` | 3,524,438 bytes, sha256 `00846a7e64fdaa9589a22abc…` (frozen from this worktree) |
| `resources\bundled-aioncore\win32-x64\aioncore.exe` | 99,193,856 bytes, sha256 `67eb02774bab3855…` (donor AionCore v0.2.2 host) |

## The packaging gate (passed before anything was copied)

| Check | Result |
| --- | --- |
| archive root `package.json` parses | **PASS** — `Kel 1.7.0-dev main=./out/main/index.js` |
| renderer bundles named by `index.html` present | **PASS** — missing: none |
| `out/main/index.js` byte-identical to the build | **PASS** — `eb2775324341c3e9…` |
| `out/renderer/index.html` byte-identical to the build | **PASS** — `3db47abd6bdb0c87…` |
| verdict | **ARCHIVE SOUND** |

## Isolated launch (from the build output, before the candidate was touched)

Roots: `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\audit17-engine` (a copy of the V2 test root:
32 jobs, 23 Kibble findings, 9 missions) and `AIONUI_DATA_DIR=…\prepared\audit17-web`.

| Check | Result |
| --- | --- |
| engine owns that root | **PASS** — `KelEngine.exe` (pid 21528) from the packaged `resources\kel-engine`, descriptor **rewritten in the root** (`http://127.0.0.1:62339/`), `kel.sqlite3` written there during the run |
| `/kel/api/*` through the packaged WebUI | **PASS — JSON, never SPA HTML**: `{"success":false,"error":"Authentication required","code":"UNAUTHORIZED"}` before sign-in (the gateway's own gate, HTTP-level) |
| local recovery (loopback) | **PASS** — `POST /api/webui/reset-password` → 200 + a new password |

## Packaged surfaces (packaged WebUI, engine JSON flowing)

| Surface | Result |
| --- | --- |
| Work | **renders** — "Jobs", "Waiting to continue", "Verification" present with real rows ("Extra help: finished Implementation Engineer · 13h ago"); **no failure card** (this is the surface F1 broke) |
| Projects → Knowledge | **renders** — real memory rows with trust/verification wording and the routing sentence |
| Recipes | **renders** (2,389 chars, no failure card) |
| Activity | **renders** (2,580 chars, no failure card) |
| Kibble | **renders with the Build Update panel** — "Kibble / Build Update / Prepare …", rows `FIX-0004`, `FIX-0002`, `FIX-0001` with states and routes |
| Settings → Assistants | **renders** — "Assistants / My Assistants / Kel — Your assistant for projects and everyday work." (Figma's page, in Settings as Nick confirmed) |
| Settings → Skills | **renders** — "Skills Hub / My Skills / No skills installed / Usage Tip …" |
| Console | **2 errors** for the whole session — no 401 storm, no render failure |

**Dark mode:** the app's own preference was set to dark; `document.documentElement[data-theme]` became
`"dark"` and both Figma settings pages rendered correctly in dark.

**Phone width (390×844):** the Work surface renders (Jobs present, no failure card) and the Figma rail
("Kibble · Ramble · Recipes · Projects · Workspaces · Settings …") is the mobile navigation.

## V2-16 numbers measured in this configuration (conditions stated, no invented targets)

| Measure | Value | Note |
| --- | --- | --- |
| Sign-in → home ready | 4.13 s | measured on r16, same machine, cold load |
| Settings view switch (Assistants → Skills) | **≤ 3.0 s** | upper bound — the sample includes a fixed 3 s wait |
| Phone-width Work load (desktop → 390×844, then `#/work`) | **≤ 4.5 s** | upper bound — includes a fixed 4.5 s wait |
| Conversation open / Project switch / remote loading | still to measure | next pass; the surfaces render, so the instrumented run is a few minutes' work |

## Honest limits of this record

- **AIONUI_DATA_DIR is honoured for the web host's store, but not yet for the desktop's aioncore store**:
  the conversations DB still lands in `%APPDATA%\kel-aionui\aionui` (the backend spawn passes its own
  directory). Recorded as the next repair with the exact seam (the backend spawn in the `--webui` branch).
  Nothing in the candidate's, stable's or Astra's data was written by this audit.
- Attention-action labels ("Answer request" / "Resume" / "Stop" / "Retry") were **not visible** in the
  sampled Work rows because those rows carry no direct action (settled/extra-help); their labels remain
  to be observed on a live row. Not a defect — an unobserved case.
- The deferred broad audit (V2-19 groups beyond those already run, full dark comparison, live services,
  Muse audio, physical iPhone) is untouched by this record.
