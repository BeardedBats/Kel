# 19 — R10 evidence: packaged engine-loss / recovery journey (2026-09-18)

Artifact under test: `kel-v16-visual-fix/dist/package/win-unpacked` built from lane tip **`fa66f04`**
(electron-vite bundles rebuilt at build6; `resources/kel-engine` = the frozen **1.6.0** runtime —
`engine_version` verified in every probe run). Probes: `ux-audit/r10-engine-loss-probe.cjs` (full
journey) and `ux-audit/r10-d-cannot-restart.cjs` (focused segment), engine kills via
`ux-audit/r10-engine-kill.ps1`. All runs use an isolated `KEL_DATA_DIR` + `APPDATA`.

## Summary verdict

**PASS.** The full required sequence ran on real packaged Kel three times over two probes:
healthy → engine killed → truthful "Kel is reconnecting" → supervised restart → "Kel restarted
successfully — your work is preserved" → durable work intact → repeat loss → recovered again →
restart impossible → honest "Kel couldn't recover on its own … after 2 attempts" → manual retry
("Try to restart Kel's engine") → recovered. Zero raw-text leaks in the visible DOM, zero console
errors, screenshots at every state.

## Run index (ux-audit/runs/**)

| Run | Package state | Result |
|---|---|---|
| `r10-c` | first complete package (pre fail-fast follow-ups) | full journey PASS (42s); 5 screenshots |
| `r10-d` / `r10-e` | mid (spawn-failure deadline burn) | honest path PASS but slow: two real 45s attempt waits before could-not-recover |
| `r10-f` | **final `fa66f04`** | focused cannot-restart PASS with fail-fast: kill → reconnecting → attempt 1 fails → attempt 2 fails (per-attempt "2 ms" values were not retained — AUD-MINOR-004 addendum d; the load-bearing timings are retained) → could-not-recover in ~5 s → manual retry → recovered in 0.5 s; 2 screenshots |
| `r10-g` | **final `fa66f04`** | full journey PASS; 5 screenshots; rawLeaks `[]`; consoleErrors `0` |

## r10-g (final full journey) — measured facts

- boot: healthy; `engine_version` **1.6.0**; conversations `[ad5ef32f…, main]`; projects `[default]`
- durable seed: transcription folder `R10 durable folder` created through the engine API → present
  before loss → **present after both losses and after the manual-retry recovery**
- loss 1: killed pid → notice *"Kel is reconnecting. The engine stopped answering. Kel is bringing
  it back — your work is preserved."* → *"Kel restarted successfully. The engine is back and your
  work is preserved. You can continue where you left off."* → engine healthy on a **new pid** →
  conversations preserved → engine version stable
- loss 2 (repeat): recovered again, new pid
- loss 3 + engine binary held: *"Kel couldn't recover on its own. The engine did not come back
  after 2 attempts. Close and open Kel, or try a restart below."* (+ the one working action) →
  binary restored → button clicked → recovered on a new pid
- link log (structured, beside the engine log — the packaged app has no console):

```
[KEL-LINK] 00:09:51 state=connected attempts=0
[KEL-LINK] 00:10:01 state=reconnecting attempts=1
[KEL-LINK] 00:10:01 state=recovered attempts=1
[KEL-LINK] 00:10:11 state=reconnecting attempts=2
[KEL-LINK] 00:10:11 state=recovered attempts=2
[KEL-LINK] 00:10:21 state=unrecoverable attempts=2
[KEL-LINK] 00:10:21 state=reconnecting attempts=1        (manual retry — new incident)
[KEL-LINK] 00:10:21 state=recovered attempts=1
```

- screenshots: `r10-g/r10-00-connected.png`, `-01-reconnecting.png`, `-02-recovered.png`,
  `-03-could-not-recover.png`, `-04-after-manual-retry.png` (+ `r10-f` pair)
- raw-leak scan (visible `innerText` only): **none** (`fetch failed` / `TypeError` / `ECONN` /
  `Traceback` / IPC envelope — all absent); console errors: **0**

## Directive §11 checklist (honest scoping)

| Requirement | Verdict |
|---|---|
| packaged launch → healthy → connected | PASS (r10-g) |
| engine dies after launch | PASS (3 kills across probes) |
| desktop recognizes loss, truthful recovery UI | PASS (~2 health ticks; exact copy above) |
| restart/reconnection occurs | PASS (supervised; new pids recorded) |
| durable work reconciled / existing state remains | PASS (folder + conversations + engine version) |
| unresolved side effects NOT blindly replayed | no effect state existed in this profile; covered by engine suite `EFFECT-REPLAY` (R12 battery) |
| automatic retry budgets NOT reset | PASS in supervision (budget spent honestly across the journey; unit-pinned) — engine-side budgets covered by `RETRY-DURABLE` (R12 battery) |
| authority NOT widened / approvals not fabricated | no authority or approvals existed in this profile; engine suites `AUTH-DELEGATION`, `APPROVAL-EXACT`, R4/R6 invariants cover (R12 battery) |
| recovered or honestly blocked | PASS both branches + working manual retry |
| loss while work is active / awaiting approval | not constructible in the isolated profile (no providers/approvals); engine-level only — recorded for R12 |
| no raw infrastructure stack/errors | PASS (DOM scan + classifier tests) |

Notes: packaged `desktop.log` carries the **engine's** stdio (so a crashed engine's own output is
preserved for support); the `[KEL-BOOT]` markers seen in development are main-process console logs
and by design do not exist in a packaged run — the `[KEL-LINK]` file is the packaged evidence.

Carried to R12: engine-suite battery against the packaged engine (incl. upgrade DB using the
r10-g data root), installer/icon/About checks, failure injection, release integrity.
