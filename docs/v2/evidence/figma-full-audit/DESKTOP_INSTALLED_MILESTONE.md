# Desktop installed milestone — 2026-09-26

## Result

Canonical App now contains the desktop implementation from source `6b90dbe`. Current main also includes packaging-only commit `9d5a1bf`, which aligns the declared Electron version with the actual `37.10.3` distribution. Renderer and product behavior did not change in that config commit. This is a desktop testing milestone, not full live acceptance or V2-20.

[The frame ledger](DESKTOP_FRAME_DISPOSITIONS.md) covers all 75 current desktop frames. It records implemented presentation, dynamic data, retained-function deviations, missing backend actions and Nick decisions separately. READ is still not accepted pixel parity. Mobile remains paused.

## Package and install proof

The canonical packaging script assembled the required self-contained MCP launch bundles, pinned aioncore v0.2.2 provenance, managed Node runtime and seven offline hub extensions. The first direct package lacked those resources and was not installed. The complete package passed native module rebuilding. Kel executable icon/product metadata were applied before installation. No engine source change or engine rebuild was required.

Archive SHA256: `6bc6b1b06e7e2f9d2030cb2783fe5013fe2ed7f4c16fb99ad438b2fff9326003`. All 265 renderer files match the frozen source build. All 2,655 package files match the installed copy. Existing NSIS uninstaller, icon and elevate helper were preserved. The desktop shortcut still targets `C:\Users\Nick\Desktop\Kel\App\Kel.exe`.

The aioncore binary hash matches its provenance: `67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892`. The packaged Image MCP initialized and listed its real tool through bundled Node; no generation ran. Browser MCP refused to start without the visible bridge port/token, as required. No browser network or credential action ran in that launcher check.

## Checks performed

- TypeScript and production source build passed. Desktop regression: 65 files / 448 tests. The existing listener warning appeared without test failures. Nine focused tests passed earlier.
- Source sidebar working/unread/read/attention/pin variants and confirmed Planning label passed both themes/widths. Supplied catalogs/props are presentation proof, not live runtime discovery.
- Bundled Chat passed stored synthetic turns, preserved six engine-history rows, loaded workspace/footer assets, 30px turn gaps, list/avatar/timestamp geometry, missing usage and wheel access in Dark/Light at 1440/800px. Original records were restored.
- Bundled task passed Dark supplied catalog draft, three exact picker icons, disabled no-target ongoing conversation, 600×614px bounds and Weekly/Skip/Cancel/reopen/Escape. Light passed Advanced/Manual/Custom and readable fields; minimum sampled contrast 5.39:1. No task was saved or run.
- Complete bundled package and installed App passed failed-status detail and enabled Image Model at 1440/800px, Dark/Light. Real isolated selection, MCP enable and reload persistence passed. Provider/settings were journaled, restored and compared. No image request or credential was used.
- Bundled Work/Permissions passed real isolated active/waiting records, Answer request → Running, Allow once → one use, Revoke → Revoked and keyboard scrolling. Fixtures were canceled/acknowledged and requests closed. No worker command ran.
- Installed App passed Light task controls and 32 core route checks: New chat, Work, Permissions, Kibble, Knowledge, Ramble, Skills and Chat in both themes/widths. Each route had no document overflow or renderer errors. This is an installed route smoke check, not a new full frame comparison.

Three test assumptions were corrected without product changes: wait for confirmed settings after reload; reload after installing the supplied assistant catalog interceptor; require the composer bitmap only in Dark. The route helper also uses actual internal `/guid` and `/dogfood` routes. Historical inventory `/home` and `/kibble` names are not current routes.

## Data and cleanup

Canonical Data stayed unchanged: all 2,949 files and 302,844,443 bytes match their pre-install hashes; zero changed files. Root still contains only Kel, App, Data and Tools. Git has one canonical worktree on main. No user data, credentials, migration or Git history rewrite was performed.

All owned apps and the source preview closed. No active restoration journal remains. Durable private proof lives at `C:\Users\Nick\Desktop\Kel\Tools\consolidation\desktop-20260926`; App has `kel-install-provenance.json`.

Automatic approval review rejected the combined temporary cleanup command as blocked by policy. None of that command executed. A separate non-delete action saved proof and stopped the preview. No deletion retry or workaround ran. Residue remains under `C:\Users\Nick\AppData\Local\Temp\kel-figma-audit-1790312139912`: package directories, the App rollback, synthetic data/profile directories and fixture folders. Previously blocked Workspace/work-appearance and repository `packages/` cache also remain. Tracked source is clean; that known untracked cache prevents claiming an entirely clean filesystem.

## Remaining acceptance

Nick must decide Setup Autonomy semantics and whether Pet remains Off under AUD-MINOR-008. Live provider/worker/OAuth/remote/Muse journeys need actual configuration or credentials. Exact Light palette needs a Light reference. Connections retains Advanced/template/secure-storage content, making its card taller than the sample. Supplemental Skills detail/history remains disabled outside the current frame scope. These limits are not marked complete.

V2-16, V2-18 and V2-19 remain partial. V2-20 is not ready. Next exact work: resolve the Autonomy/Pet decisions, implement any authorized desktop change as one batch, then finish the remaining live desktop acceptance. Mobile stays paused. Independent review is unavailable.
