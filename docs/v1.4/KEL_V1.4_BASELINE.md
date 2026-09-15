# KEL V1.4 — BASELINE (Gate 0 verification)

Date: 2026-09-15 (America/New_York) · Session: V1.4 autonomous session #1
Status: **VERIFIED** — repo refs, tag, frozen hashes, and test baseline confirmed this session.

## 1. Repository refs (verified this session)

| Ref | Commit | Note |
|---|---|---|
| `main` / `origin/main` | `b6974cf` | Current tip; 4 commits ahead of the v1.3.0 tag |
| `v1.3.0` (annotated) | `b3c7c24` | PR #1 merge (v1.3-dev → main); matches the brief's "current main commit" |
| `v1.3-dev` / `origin/v1.3-dev` | `dd67ef4` | Matches the brief |
| `v1.4-dev` (new) | branched from `b6974cf`, pushed to origin | V1.4 work branch |
| remote | `https://github.com/BeardedBats/Kel` | push verified this session (`v1.4-dev`) |

**Documented delta vs the brief:** the brief lists `main = b3c7c24`; actual `main` is `b6974cf`,
four commits later (`ab4aef0`, `c2d0c92`, `507220f`, `b6974cf` — Söhne / SF Pro Text font work,
PRs #2/#3, recorded in the frozen manifest as "owner's decision"). Benign, non-destructive,
expected. `v1.4-dev` therefore branches from `b6974cf`.

## 2. Frozen release integrity (3/3 PASS)

`C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.3-Frozen` — read-only check (`sha256sum`):

| File | SHA-256 (prefix) | Result |
|---|---|---|
| `Kel.exe` | `e048632e03fabc96…` | PASS |
| `resources/app.asar` | `cd0d51cb3f4a69af…` | PASS (font amendment hash) |
| `resources/kel-engine/KelEngine.exe` | `8ed30d3d09fb8bbe…` | PASS |

V1, V1.1, V1.2 frozen archives present; nothing under `Kel Releases/` was written.

## 3. Test baseline (green)

- Command: `cd runtime && python -m pytest tests/ -q` (with `PYTHONDONTWRITEBYTECODE=1`, `KEL_SKIP_TELEMETRY=1`)
- Result: **267 passed, 10 subtests passed in 55.58s**, exit 0 — exactly the V1.3 manifest claim.
- Suite is hermetic (temp dirs + fake providers; no network or API keys) per README.
- Environment: Windows 10/11 x64 · Python 3.14.3 · pytest 9.0.3 · Node 24.18.0 · npm 11.16.0 · git 2.53.0 · `gh` present (push verified).

## 4. Dogfood isolation evidence (this session)

- No `Kel.exe` / `KelEngine.exe` / Electron process was running at session start; none was started.
- No user data directories were read or written; no window was launched, so no focus was taken.
- Tests ran hermetic (temp dirs); frozen releases were only hashed (read-only).

## 5. Toolchain gaps to close before build/visual gates

- `bun` not installed (desktop build is bun-based; `desktop/bun.lock` is authoritative).
- Playwright not installed and `desktop/node_modules` absent — needed for the packaged screenshot harness.
- PyInstaller availability for runtime packaging to be confirmed at the build gate.

## 6. UI baseline status

- Screenshot harness: not built yet (next action). No packaged capture yet — no window was opened.
- Source-derived screen inventory: `KEL_V1.4_SCREEN_INVENTORY.md` (v0).
- Preliminary audit notes: `KEL_V1.4_UI_AUDIT.md` (v0).

---
*Method note: every claim in this file was produced by commands run in this session; nothing is
copied from the brief without verification.*
