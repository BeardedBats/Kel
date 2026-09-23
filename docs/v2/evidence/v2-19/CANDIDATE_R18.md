# Kel V2 candidate r18 — aioncore's store follows `AIONUI_DATA_DIR`

Built from `integration/v2` @ **`74f105a`** (pushed: `origin/integration/v2` matches) after the
follow-up pass recorded in `docs/v2/evidence/v2-19/AUDIT_R16.md` → “Follow-up pass”.
Packed 2026-09-23 03:33Z by **one** packer (`electron-builder --config kel-builder.json --x64 --dir`,
exit 0, “signing with signtool.exe … Kel.exe”), from a working tree with a clean typecheck.

## Archive gate — the preconditions for *keeping* the candidate

| check | r18 | r17 (for comparison) |
| --- | --- | --- |
| `app.asar` | 1 copy, 300,584,526 B, sha256 `b4235af703fec1f7` | 300,584,430 B, `75ef03c0…` |
| `Kel.exe` | 1 copy, 204,575,232 B, sha256 `2ea24332e18c69c8` | 204,575,232 B, `4726f926…` |
| `electron.exe` | **0** | 0 |
| stray `*unpacked*` dirs | none | none |
| frozen engine | `resources/kel-engine/KelEngine.exe` 3,524,438 B `00846a7e64fdaa95` — **byte-identical** | same |
| donor aioncore | `…/bundled-aioncore/win32-x64/aioncore.exe` 99,193,856 B `67eb02774bab3855` — unchanged | same |
| DLL set | exactly the expected 15 (`VCRUNTIME140{,_1}`, chromium ×6, `libcrypto/libssl/libffi/sqlite3/python314`) | same |

## Isolated launch checks (r18, launched from the candidate launcher)

- **Engine ownership** — besides the protected stable engine, the only `KelEngine.exe` running is
  r18's, with `--data C:/Users/Nick/KelV2Runs/prepared/candidate`; the stable engine's
  `--data C:/Users/Nick/KelDogfoodRuns/prepared/engine` was untouched.
- **Gateway** — the packaged WebUI answers `/kel/api/state` with JSON
  (`{"success":false,"error":"Authentication required",…}` without a session), never the SPA HTML.
  F1's fix holds in the new archive.
- **The store fix, both directions** (this candidate's reason to exist):
  - `AIONUI_DATA_DIR` **set** → aioncore's store is created under
    `C:\Users\Nick\KelV2Runs\prepared\candidate\desktop-store` (`aionui-backend.db` 774,144 B plus its
    locks at 23:35), and the shared store's own `aionui` directory is **not** touched (its mtime stayed
    frozen at 23:16:19 across the run).
  - `AIONUI_DATA_DIR` **unset** → the store is written at the default location again
    (`%APPDATA%\kel-aionui\aionui\aionui-backend.db-wal` 23:36:54, `extension-states.json` 23:36:44).
    The default path is unchanged; only the variable redirects it.
  - A *brand-new* store presents the sign-in view (`#/login`) — a fresh isolated store inherits no
    session, which is what “isolated” has to mean.
- **Residual, recorded not fixed** — Electron's own `userData` (Chromium profile: `Preferences`,
  `Local Storage`, `blob_storage`, `logs/…`) still lives in `%APPDATA%\kel-aionui`. Moving *that* would
  move the **stable** app's profile too, because both apps use the path today; it is a decision to take
  deliberately, not a chore to sneak into an audit pass.

## Packaged-session console errors

| error | count | disposition |
| --- | --- | --- |
| `GET /api/state?conversation=main` → **403** | a repeat (≈24–37 per unauthenticated load) | **cause not established** — the bare path has no caller in this source tree; the Kel transport always prefixes `/kel`. Full note in `AUDIT_R16.md` → “Follow-up pass”. Next step is a source-mapped *Initiator* trace, not a blind edit. |
| `GET /favicon.ico` → **404** | 1 | cosmetic; nothing depends on it |

## V2-16 timings

Method: Playwright **conditions only** (wait for the rendered marker the action actually produces);
no fixed-wait estimates anywhere.

Measured on packaged r18 (loopback origin, real navigation-timing entries):

| step | condition | value |
| --- | --- | --- |
| document load | `loadEventEnd` | **627 ms** (TTFB 6 ms, DOMContentLoaded 532 ms; 2.4 KB transferred for the shell) |

**Blocked honestly:** the conversation-open and project-switch numbers need a signed-in session. This
pass's browser had no session, and the sign-in view asks for a username and password — credentials are
not entered by the runner. The r17 attempt earlier in the same pass died with the browser session
before it returned any number, so nothing is being reported from it. Ready method for whoever holds the
session (one script, no waits): home-ready → wait `New Chat`; conversation open → click the newest row
and wait `textarea, [contenteditable=true]`; project switch → hash `#/projects/knowledge`, wait
`Knowledge`, hash `#/projects/map`, wait `Project map`; take `performance.now()` deltas.

## Rollback

- **r17 preserved** at `C:\Users\Nick\KelV2Candidate.r17` (`app.asar` `75ef03c0…`); r16 at
  `C:\Users\Nick\KelV2Candidate.r16`.
- Launcher: `C:\Users\Nick\KelV2Candidate\Run-Kel-V2-Candidate.cmd` — sets
  `KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\candidate` and
  `AIONUI_DATA_DIR=…\prepared\candidate\desktop-store`, then starts `Kel.exe`.
- Never promoted; the stable install, its data and the shortcut were not touched.
