# V2-19 r39 — Figma UI audit checkpoint

**Source:** `integration/v2` at pushed `61db8d5587d31d192f8d9c31ed51ddcdd38b1e0c`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r39`, staged and not promoted. The full unpacked runtime and `Run-Kel-V2-Candidate-r39.cmd` are present. The launcher uses separate host, store, and engine roots under `C:\Users\Nick\KelV2Runs\prepared\r39`.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `F2C73B0B58B4C1583E144D90F045BE425821E068651822AD3822B65B574332A3` |
| `Kel.exe` | `B7C8F77C4B481F78AE9DDF1859DF8FABE10DE6952D84B3BCBFB42C79F0C18938` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r39.cmd` | `ABFA4093D1EB58D26E7209605B98E9E8D28604E68D659A1CC24E2BBE044C9F35` |

## Checks

- [Full audit](../figma-full-audit/README.md): 23 desktop FINAL frames, 28 mobile frames, Foundations `139:2`, Components `136:2`, Mobile Components `213:3`. Exact parity remains open; the audit lists each screen and component gap.
- Source since r33: mobile About, Archived, and Skills Hub use Figma FINAL text and measured cards. Desktop About keeps Data folder. Mobile About adds Licenses and Third-party notices. r37 exposed a blank-on-first-open notices sheet; r38 rendered it reliably. r39 makes its six-column notice table scroll horizontally at phone width. r34–r38 remain intermediate staged candidates, not promotions.
- `bunx tsc --noEmit -p tsconfig.json` passed. `bunx vitest run tests/unit --reporter=dot` passed 44 files and 295 tests. `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, and `python C:\tmp\verify_asar.py` passed. The archive gate verified the manifest, renderer bundles, main build, and renderer index.
- Fresh packaged root `C:\Users\Nick\KelV2Runs\prepared\r39-figma-final`: [six route and overlay checks](../figma-full-audit/r39-settings-check.json) passed. At 393px, About cards measured 361×214 and 361×109; Archived 361×94; Skills cards 361×114 each. The 79px setup notice explains their y offset from the FINAL samples. First-open notices text was visible, its table viewport was 335px with 931px scroll width, and Escape closed the sheet. At 800 and 1440px, desktop About showed Data folder and no Licenses. No checked width had document overflow. [Package screenshots](../figma-full-audit/key/r39-notices.png) show the final notice treatment.
- Prior r33 packaged checks remain in [r33](CANDIDATE_R33.md): 393px navigation, Add Model Cancel/Escape, Dark Appearance at 393/800/1440, 23-route width sweep, and real PNG image lightbox Copy/Download/scrim/Escape. r29 recorded two native colour-picker adjustments in one popup; r39 did not repeat that check.

## Ownership and remaining work

Before testing, the user's r20 root was `C:\Users\Nick\KelV2Candidate\Kel.exe` PID 6356 with engine PID 10848. The stable engine was PID 26544. The r39 root was PID 21084, engine PID 38960, and aioncore PID 59712 during checks. The r38 and r39 test trees were stopped only after their executable paths matched their isolated candidate folders. The final process list showed only r20 and the stable engine. PIDs may change. Stable data, shortcuts, rollback copies, Astra's clean `ux/v2-shell` branch, and live r20 were untouched. No candidate was renamed or promoted.

Exact UI parity is **not established**. The audit still identifies unmatched desktop controls, compact mobile rows, menus, dropdowns, tooltips, populated chat/task/transcript states, and Components variants. Sample text cannot be compared against empty real data without a matching fixture. Faint Light-mode labels stayed outside this Dark pass. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. The web-host suite requires all Kel instances stopped and was not run while r20 stayed live. `request_review` was unavailable; no independent review occurred.

**Next action:** create a disposable profile with representative populated chat, task, recording, and menu states. Compare each against its paired FINAL frame. Fix only measured copy, control, and spacing gaps. Keep r20 and the stable app protected; do not rename or promote r39 while r20 runs.
