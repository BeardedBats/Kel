# Integration line — the Shell baseline on the backend line (2026-09-22)

Branch `integration/v2` @ `fe5e6b7`, worktree `C:\Users\Nick\Desktop\Kel\kel-v2-integration`
(authorized by the marathon session; Astra's own worktree and branch were never touched).

## What was merged

- `dev/v2` @ `7b18618` (this turn's backend work: V2-06/07/08 + the web-host deep-link fix)
- `ux/v2-shell` @ **`0052075`** (Astra's committed Shell baseline at merge time: status text/chips
  replaced with plain coloured text, her web-host socket-listener fix, and the Ramble sidebar header
  with inline folder creation)

**Correction, recorded from evidence rather than assumption:** the merge commit's own message says
`681e005`, which was her tip when the integration worktree was created. She committed `0052075` while
this turn was running, and the merge actually took *that* — verified with
`git log --oneline -1 fe5e6b7^2` → `0052075` and `git merge-base --is-ancestor 0052075 fe5e6b7` → true.
A pushed merge is never rewritten; this file is the accurate record.

**Exactly one conflict**, in `desktop/packages/web-host/src/static-server.unit.test.ts`: Astra's line
added a socket-reset regression pin and kept the older *“SPA fallback: /chat/123 returns index.html”*
expectation; the deep-link fix deliberately supersedes that expectation (a hash-routed SPA cannot serve
that path — that behaviour **was** the defect). Resolution: her socket-reset test kept unchanged, her
copy of the superseded expectation dropped, the deep-link assertions kept, and the reason recorded in
the test itself. Everything else auto-merged, including her `static-server.ts` change (the splice path
keeps its error listener through rejection/close) and the Connections page.

Astra's worktree was **clean** at the end of this turn — her ramble-sidebar work is committed as
`0052075`, which is why the integration line already carries it. Her lane keeps moving; re-merge her
committed baseline before packaging the candidate and record the new tip here.

## Verification

- No conflict markers remain (only binary font/PNG files contain the byte sequence).
- The merged web-host content was executed where the dependencies resolve:
  `bunx vitest run packages/web-host/src/static-server.unit.test.ts` → **15 passed** (Astra's
  socket-reset pin + the deep-link assertions + the rest of the suite).
- **Not verified in the integration worktree itself:** `bun install` was not run there (a Windows
  junction to `dev/v2`'s `node_modules` does not resolve nested packages for bun). The renderer
  suites (`desktop/tests/**`, `tsc`) and the packaged app were **not** run on this line — that is the
  remaining verification work for the integration branch.

## The deep-link defect this line carries the fix for

The renderer is hash-routed (`HashRouter` in `desktop/packages/desktop/src/renderer/components/layout/
Router.tsx`), so a path-style link (`/conversation/<id>`, `/work`, `/connections`) could never reach
its route: the web-host's SPA fallback answered `index.html` for any unmatched path and the router's
catch-all then sent the visitor to `/guid` (or `/login` when unauthenticated) with the path — and the
conversation id — gone. One cause behind both measured symptoms (the blank `/conversation/<id>` load
and the unauthenticated direct-route failure). The fallback now redirects a real deep-link path to its
hash form (`/conversation/abc?from=phone` → `/#/conversation/abc?from=phone`); assets, `/kel/` and the
gated proxy routes are untouched, and no renderer file was edited.
