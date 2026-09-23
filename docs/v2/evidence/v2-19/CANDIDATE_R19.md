# Kel V2 candidate r19 — the packaged manifest is served again

Built from `integration/v2` after the follow-up pass recorded in
`docs/v2/evidence/v2-19/AUDIT_R16.md` → **“Follow-up pass 2”**.
Packed 2026-09-23 04:00Z by **one** packer (`electron-builder --config kel-builder.json --x64 --dir`,
exit 0, “signing with signtool.exe … Kel.exe”); typecheck clean before the build.

## What changed (source)

| file | change |
| --- | --- |
| `desktop/packages/web-host/src/static-server.ts` | `ASSET_FILE` extension bound `{1,8}` → `{1,12}`: a file request never becomes a deep-link redirect. `webmanifest` (11 chars) was being sent to `/#/manifest.webmanifest`, so the browser parsed HTML as the manifest. |
| `desktop/packages/web-host/src/static-server.unit.test.ts` | regression test: “a long-extension asset is served, never redirected into the hash route”. |

No authentication path was touched; the session gate, the `/kel/*` gateway and the donor bootstrap are
unchanged.

## Archive gate — the preconditions for *keeping* the candidate

| check | r19 | r18 |
| --- | --- | --- |
| `app.asar` | 1 copy, 300,585,830 B, `f9ae0767f798fd84` | 300,584,526 B, `b4235af703fec1f7` |
| `Kel.exe` | 1 copy, 204,575,232 B, `460c966d1f917745` | `2ea24332e18c69c8` |
| `electron.exe` | **0** | 0 |
| stray `*unpacked*` dirs | none | none |
| frozen engine | `00846a7e64fdaa95` — byte-identical | same |
| donor aioncore | `67eb02774bab3855` — unchanged | same |
| DLL set | 15, the expected set | same |

## Isolated launch checks (r19, launched with `KEL_DATA_DIR` + `AIONUI_DATA_DIR` set)

- **Engine ownership** — the only engines running are the protected stable one
  (`--data C:/Users/Nick/KelDogfoodRuns/prepared/engine`) and r19's
  (`--data C:/Users/Nick/KelV2Runs/prepared/candidate`).
- **Store** — `…\prepared\candidate\desktop-store\aionui-backend.db` (913,408 B) — the r18 fix holds.
- **Manifest (this candidate's reason to exist)** — `GET /manifest.webmanifest` → **200**,
  `content-type: application/manifest+json`, 529 B of JSON; in the browser the fetch parses to
  `name: "Kel"`. Before the fix the same URL answered `302 → /#/manifest.webmanifest`.
- **Deep links still translate** — `/conversation/abc-123?from=phone` → `302 /#/conversation/abc-123?from=phone`;
  `/work` → `302 /#/work`; an asset-shaped miss (`/assets/does-not-exist.png`) → SPA fallback, unchanged.
- **`/kel/api/state`** → JSON (`{"success":false,"error":"Authentication required",…}`), never HTML.
- **Root** → 200 `text/html` (SPA), and an unauthenticated visit still routes to `#/login`.
- **Document load (loopback, real navigation-timing entries)** — DOMContentLoaded **477 ms**,
  load **570 ms**.

## Rollback

- **r18 preserved** at `C:\Users\Nick\KelV2Candidate.r18` (`app.asar` `b4235af7…`, verified), r17 at
  `…\.r17` (`75ef03c0…`), r16 at `…\.r16` (`88f34373…`).
- Launcher: `C:\Users\Nick\KelV2Candidate\Run-Kel-V2-Candidate.cmd` (sets both data-root variables,
  then starts `Kel.exe`).
- Never promoted; the stable install, its data and the shortcut were not touched.

## Unresolved in this pass (do not read as verified)

- **V2-16 conversation-open and project-switch timings** — still not measured: they need a signed-in
  session, this pass had none, and the sign-in view wants a username and password (the runner does not
  enter credentials and does not copy the stable app's session data). The condition-based method is
  ready in `AUDIT_R16.md` → “V2-16 instrumentation”; the document-load numbers above are the only
  timing results this pass can stand behind.
- **Electron profile/log locations** — deliberately unchanged (documented decision; `%APPDATA%\kel-aionui`
  keeps the Chromium profile and logs because the stable app shares that path).
- **The donor bootstrap's 401s and `ws://…/ws` authentication failures on an unauthenticated load** —
  expected refusals, noisy but not defects; they are what a signed-out page looks like.
