# V2 AUDIT — candidate r16 (2026-09-22, night)

**Baseline audited**

| | |
| --- | --- |
| Source | `integration/v2` @ **`466c99b`** (pushed; `origin/integration/v2` matches; clean) |
| Candidate | `C:\Users\Nick\KelV2Candidate` — `Kel.exe` `f989e83d2181fbc6…`, `resources/app.asar` `88f343733485e2f4…`, `resources/kel-engine/KelEngine.exe` `00846a7e64fdaa9589a22abc…` |
| Reference set for the dark audit | `docs/v2/evidence/shell/*` (1440, dark: mean luminance ≈ 45) and `docs/v2/evidence/shell-mobile/*` |
| Evidence labels | **[packaged window]**, **[packaged WebUI]**, **[backend API]**, **[source tests]** |

Roots: the **candidate's data was never written**; state-changing checks ran against copies
(`prepared/audit`, `prepared/audit-state` — the latter's copy failed on a busy `controller.lock`, see
F2) and against the V2 test root `prepared/engine`. The stable install, its data root and Astra's
worktree were untouched.

## 1. Packaged application

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1.1 | Archive integrity gate before any copy | **PASS** | manifest parses; renderer bundles present; `out/main/index.js` + `out/renderer/index.html` byte-identical; `VERDICT: ARCHIVE SOUND` |
| 1.2 | Launch via the launcher on isolated data [packaged window] | **PASS** | window "Kel"; own engine `--data …\prepared\candidate`; own aioncore; stable engine untouched |
| 1.3 | Local password recovery on loopback [packaged WebUI] | **PASS** | `POST /api/webui/reset-password` → 200 + a 16-char password (twice today); the remote-refusal boundary is pinned by 30 gateway tests [source tests] |
| 1.4 | Ordinary sign-in [packaged WebUI] | **PASS** | `#/login` → credentials → `#/guid` |
| 1.5 | Deep link → sign-in → destination → refresh [packaged WebUI] | **PASS** | fresh load of `#/conversation/208a29da` → `#/login` with `returnTo=/conversation/208a29da` → after sign-in landed on that conversation |
| 1.6 | Stale session (gated call 401s mid-session) [packaged WebUI] | **PASS** | on a gated surface (`#/guid`) the app flipped to `#/login`, `returnTo=/guid`, sign-in form shown |
| 1.7 | Conversation creation + real model reply [packaged WebUI + backend API] | **PASS** | conversation `208a29da`; the app's own store holds user "Reply with exactly: audit ping." and assistant "audit ping." (`status=finish`) |
| 1.8 | Response delay, one turn [packaged WebUI] | **5.07 s** send → reply visible (condition: `codex` healthy, same host, no other load) |
| 1.9 | History list renders conversations [packaged window, OCR] | **PASS** | the rail lists the real conversations; "Save as a recipe", "+ New Chat", "Settings", "Recent" present |
| 1.10 | Kel surfaces in the packaged WebUI (Work/Projects/Recipes/Activity/Kibble) | **FAIL (high) — BLOCKED** | see F1 |
| 1.11 | Phone-width history / attention / project routing in the packaged WebUI | **PENDING** | blocked by F1; the source-WebUI phone pass (r14) covered Projects/Work/Activity/Kibble rendering |
| 1.12 | Kibble Build Update through human review (UI) | **PENDING** | blocked by F1; the engine side is pinned by `test_v2_build_update` + J-KBU [source tests] |

### F1 — Kel surfaces fail in the packaged WebUI when the app is started with `KEL_DATA_DIR`

- **Repro:** start `Kel.exe --webui` with `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\engine`
  (also reproduced with `…\prepared\audit-state`), sign in, open `#/work`.
- **Expected:** the Work surface renders its rows (or its honest empty state).
- **Actual:** `GET /kel/api/state` and `/kel/api/work?conversation=main` answer **200 with the SPA
  HTML** instead of JSON; the Work page renders **“Kel couldn't complete that / Cannot read
  properties of null (reading 'jobs') / Try again / Copy diagnostics”**
  (`components/kel/…` failure card), and **no `KelEngine.exe` runs for the chosen root** while the
  app is up (only the protected stable engine was alive).
- **Severity:** high — it blocks every Kel surface (Work, Projects, Recipes, Activity, Kibble) in the
  packaged WebUI, i.e. the exact configuration the launcher documents.
- **Evidence:** screenshot OCR of `#/work`
  (`C:\Users\Nick\AppData\Local\Programs\Kun\audit-r16-work-desktop.png`), the gateway HTTP probes
  above, and the process list taken at the same moment.
- **Not established:** why the engine did not come up in these launches. Note the **capture harness**
  (1.10/dark) *did* have a live packaged engine — so the spawn works in some launches. The next
  investigation should compare the two launches' engine-descriptor paths: the gateway reads
  `desktop-session.json` from the data dir it is given, while the desktop resolves its root through
  `KEL_DATA_DIR || appData/kel-desktop/work`.

## 2. Dark mode at desktop and phone widths

Captured with the repo's own harness so the method matches the references:
`node packaging/capture-screens.cjs <candidate> <fresh data root> … --theme dark --widths 1440x900,390x844`
→ **23 shots, 0 errors, 0 blank-suspect frames, clean shutdown** [packaged window],
`docs/v2/evidence/v2-19/audit-r16/dark/` (+ `v13-texts.jsonl`, `v13-manifest.json`).

| View | Reference (dark) | r16 dark capture | Pixels differing >28 |
| --- | --- | --- | --- |
| home | `shell/1440-home.png` lum 45.0 | `v13-13-12-home.png` lum 47.6 | **5.3 %** |
| activity | `shell/1440-activity.png` lum 44.5 | `v13-16-12-activity.png` lum 47.6 | **4.7 %** |
| kibble | `shell/1440-kibble.png` lum 44.8 | `v13-17-12-kibble.png` lum 47.6 | **5.6 %** |
| home @ phone | `shell-mobile/A1-home.png` lum 49.3 | `v13-18-13-home-at-390x844.png` lum 54.3 | 13.0 % |
| work @ phone | `shell-mobile/A2-work.png` lum 50.8 | `v13-19-13-work-at-390x844.png` lum 54.3 | 12.9 % |
| projects @ phone | `shell-mobile/D1-projects.png` lum **246.6** | `v13-20-13-recipes-at-390x844.png` lum 54.3 | excluded — **the reference is a light frame**, not a dark one |

**What matches (dark):** shell chrome — sidebar, titlebar, navigation, type scale and the token
palette. 4.7–5.6 % differing pixels on 1440 is consistent with the same layout carrying different
real content and a slightly lighter dark surface (47.6 vs 44.8–45.0 mean luminance on the shell).

**What does not match, and why — a content finding, not a styling defect:** every capture made from a
**fresh data root** shows Kel's own **setup wizard** covering the route ("Set up Kel / Add Model /
Step 1 of 5 — Welcome … Connect a model …"), in the body of *work*, *recipes* and *kibble* alike
(`v13-texts.jsonl`). The reference frames were captured on a configured install, so the body content
is **different real content**, not a regression. It also means the dark check could not compare the
*surface bodies* on a fresh root; the 4.7–5.6 % figures measure the chrome plus the wizard-vs-surface
difference together and must be read that way.

**Dark-mode verdict:** **PASS for the shell chrome** at 1440 (home/activity/kibble within ~5 %), **PASS
with a wider margin at phone width (12.9–13.0 %, wizard-vs-content again)**, **PENDING for the surface
bodies** (blocked by F1 on a configured root). No prior dark-mode audit existed to compare against —
recorded as a gap in the evidence set, not a defect.

## 3. V2-19 regression, V2-18 re-checks, V2-16 timings

| Group | Result | Evidence |
| --- | --- | --- |
| Engine suites (attention, long-run fencing, build update, recipe library, activity, kibble gate, migrations) | **53 tests OK** | [source tests] |
| Gateway/static suites (session gate, local recovery, remote refusal) | **30 tests passed** | [source tests] |
| Renderer Kel suites (needs-attention, activity surface, recipes surface, shell navigation, shell theme) | **27 tests passed** | [source tests] |
| **Total this pass** | **110 tests passed** | |
| V2-18 journeys | **PENDING (not re-run in this pass)** — no failures known; the engine root is free and the affected journeys are J-WORK, J-RECOV, J-ATTN, J-RECIPE, J-ACTIVITY | |

**V2-16 measurements (conditions: same host, no other load, packaged WebUI, `codex` healthy):**

| Measure | Value |
| --- | --- |
| Sign-in → home ready | 4.13 s (includes the login round trip) |
| One turn: send → reply visible | 5.07 s |
| Navigation timing (home, earlier pass, same build) | TTFB 9 ms / DOMContentLoaded 309 ms / load 387 ms |
| Conversation open, Project switch, remote loading | **PENDING** — blocked by F1 for the packaged WebUI; the source-WebUI numbers (454 ms home ready, 33 ms conversation switch) are recorded in `V2_05_DEEPLINK_RETENTION.md` as a different environment |

## 4. External checks — PENDING with their exact dependency

| Check | Dependency |
| --- | --- |
| Real Google sign-in (V2-04b) | Nick's own OAuth client id + one browser consent |
| Live provider round trips beyond the codex turn measured here | the relevant credentials |
| Muse transcription with real audio | a microphone and a real recording |
| Physical iPhone (V2-05 device pass) | the device |
| Promotion / installation of a candidate | Nick's explicit decision (nothing promoted here) |

Fixtures, phone viewports and earlier runs are **not** counted as live-service or live-device passes.

## 5. Release blockers, non-blocking findings, repair order

**Blockers**

1. **F1** — packaged WebUI Kel surfaces fail when the app is started with `KEL_DATA_DIR` (no engine
   for the chosen root; `/kel/*` serves HTML; every Kel surface shows the failure card).

**Non-blocking findings**

2. **F2** — copying a live Kel data root can produce an incomplete copy (`controller.lock` busy →
   `cp` error) and the engine then refuses to start; the audit worked around it. Impact: setup
   guidance, not the product.
3. **F3** — the packaged app **ignores `AIONUI_DATA_DIR`**; its aioncore store lives in
   `%APPDATA%\kel-aionui\aionui` and is shared by whichever Kel app runs. The audit's conversation
   landed there (the candidate's own root was untouched). Worth an explicit isolation note or an
   honoured override.
4. **F4** — with a fresh data root the setup wizard covers every route, so surface-level checks and
   captures need a configured root; the harness manifest should record that condition.
5. **F5** — `shell-mobile/D1-projects.png` is a light frame; the dark comparison set has a hole there.
6. **F6** — no prior dark-mode audit existed.

**Exact repair order**

1. Fix F1 (find where the desktop's engine spawn and the gateway's descriptor lookup disagree, then
   make the packaged WebUI work with an isolated `KEL_DATA_DIR`); repeat checks 1.10, 1.11, 1.12 and
   the surface-body half of §2 on a configured root.
2. Re-run the V2-18 affected journeys (J-WORK, J-RECOV, J-ATTN, J-RECIPE, J-ACTIVITY).
3. Finish the V2-16 set (conversation open, Project switch, remote loading) in the repaired
   configuration.
4. Then the external checks as their dependencies arrive.
