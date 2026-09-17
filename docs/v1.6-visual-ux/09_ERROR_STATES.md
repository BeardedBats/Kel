# 09 — Error States and Engine Reachability

The user reported that ordinary launch produced, on five screens:

> Work could not be loaded · Projects could not be loaded · Permissions/Autonomy could not be loaded ·
> Transcription could not be loaded · Team could not be loaded — each with `TypeError: fetch failed`

Question asked of this audit: stale build, startup race, engine failure, port/descriptor issue, renderer route,
bridge issue, isolated-environment artefact, or a real current defect?

## Verdict

**A real current defect, in two separable halves.**

1. **The raw string is leaked into user-facing copy by construction.** Every Kel page passes the raw JS error
   text straight into the failure card. That is a product defect regardless of what caused the failure.
2. **There is no engine supervision, readiness gate, or recovery.** The descriptor is read **once** at
   startup; if the engine is unavailable at that moment, or stops later, nothing re-checks, re-connects,
   re-spawns, or tells the user what is actually wrong. Every engine screen simply fails forever until the app
   is restarted.

It is **not** a stale build and **not** a deterministic fresh-launch bug: a clean isolated cold launch was
verified green twice (engine spawned, all surfaces loaded, **0 console errors, 0 error surfaces**).

## Reproduction (performed)

Environment: `package-final16` (ffeef73 + Phase 3 WIP), isolated profile root, off-screen window.

```
boot → engine descriptor: {"url":"http://127.0.0.1:59960/","pid":9704,...}
kill that engine pid  (simulates: engine crashed / was stopped / another instance drained it)
navigate to the five surfaces
```

Observed DOM text (verbatim, `evidence-visual-b.json` → `engineLoss`):

| Surface | Card title rendered to the user | Raw leak | Fix line rendered |
|---|---|---|---|
| `/work` | `Work could not be loaded` | `TypeError: fetch failed` | `Check that the Kel engine is running, then press Reload.` |
| `/projects/knowledge` | `Project context could not be loaded` | `TypeError: fetch failed` | `Check that the Kel engine is running, then press Reload.` |
| `/autonomy` | `Autonomy state could not be loaded` | `TypeError: fetch failed` | `Check that the Kel engine is running, then press Reload.` |
| `/team/office` | `Kel could not read the team state` | `TypeError: fetch failed` | `Check that the engine is running, then retry.` |
| `/transcription` | `Kel could not load the transcript library` | `TypeError: fetch failed` | `Reopen this page or check that Kel is running.` |

This is the user's report, reproduced exactly, on the same five screens. Screenshots:
`screenshots/b-030-engine-lost-*.png`.

## Where each half comes from, with file:line

**The leak.** The engine is reached through the preload bridge → main process → local HTTP:

* `process/services/kel/KelService.ts:12-21` — `kelRequest()` wraps `fetch(new URL(route, descriptor.url), …)`.
  When nothing is listening, undici throws `TypeError: fetch failed`; `String(err)` is exactly
  `"TypeError: fetch failed"`.
* Each page then renders the message verbatim:
  `pages/kel/work/index.tsx:58` (`cause: err instanceof Error ? err.message : …`) rendered at `:146`;
  `pages/kel/projects/index.tsx:50` → `:117`; `pages/kel/autonomy/index.tsx:58` → `:122`;
  `pages/kel/team/index.tsx:81/95/108/121`; `pages/kel/transcription/index.tsx:754`.
* There is **no error classification anywhere** — no distinction between "engine not started", "engine
  stopped", "request timed out", "engine returned a policy refusal", or "bad response". All of them become the
  same card with an engine string in it.

**The lack of supervision.** `KelService.initializeKel(port)` (`:23`):

1. reads `desktop-session.json` and calls `/api/state` once (`:43-49`) → `connected = true` ("reused running
   engine"). **Note: the liveness check is correct and does exist** — a stale descriptor pointing at a dead
   port is handled by spawning a new engine.
2. otherwise spawns `KelEngine.exe --data <root>` detached and polls every 250 ms for up to **45 s**
   (`:99-121`); on timeout it throws `'Kel engine did not start. See desktop.log.'`.
3. after that, nothing watches the engine. There is no health poll, no re-spawn, no `descriptor` refresh, and
   no renderer-side state for "engine down". A `Reload` button re-issues the same fetch and fails identically.

**A plausible trigger the user actually hit.** `KelService.ts:31-40` registers a `before-quit` hook that calls
`/api/shutdown-idle` — i.e. **quitting one Kel window asks the shared engine to stop.** Combined with the
absence of a single-instance guard on the data root, this makes "second launch / previous instance closed"
a realistic path to a live UI with a dead engine. This audit reproduced the *symptom* deterministically by
killing the engine; attributing the user's exact trigger would need a reproduction with two instances and is
listed as an open item below.

## Second problem visible in the same capture

While the error card was shown, Work **still rendered its neutral empty-state cards**:

> `Nothing waiting to continue.` / `No specialist has been assigned yet.`

A user looking at a failure sees "Work could not be loaded" *and* two confident statements that there is
nothing to do. That is worse than either alone. **When a load fails, neutral/empty sections must be suppressed**
and replaced by the single failure card.

## What the user should see instead (design)

Replace the single generic card with a classified, human state:

| Situation | Title | Detail | Action |
|---|---|---|---|
| Engine not started yet (during boot) | `Kel is starting…` | — (a spinner, not an error) | none |
| Engine stopped / unreachable | `Kel's engine isn't running` | `Your work is safe. Kel couldn't reach its local engine on port N.` | **Start Kel's engine** (primary) · `Copy diagnostics` (quiet) |
| Engine reachable, request refused | the engine's own plain-language reason | the refusal, in the user's terms | context action |
| Unexpected request failure | `Something went wrong loading this page` | one sentence | `Try again` · `Copy diagnostics` |

Rules:

* **The raw string never renders as body copy.** `TypeError: fetch failed` belongs behind `Copy diagnostics`,
  together with the port, the engine version, and the last 50 lines of `desktop.log` (`<data>/desktop.log` is
  already written by the spawn).
* **One card, one action.** `Fix: …` as a paragraph is not an affordance.
* **Never render empty-state sections under a failure** (see above).
* **Never say "press Reload" for a condition Reload cannot fix.**

## Reliability fixes (the part that matters more than the copy)

1. **Readiness gate:** do not let engine-dependent screens issue their first request until the bridge reports
   ready; show `Kel is starting…` in the shell. `initializeKel` already knows the exact moment (`:122`).
2. **Supervise:** a light health poll of `/api/state`; on N consecutive failures mark the engine down, show one
   shell-level notice, attempt one re-spawn, and reconnect using the refreshed descriptor.
3. **Single-instance guard per data root** (or make the drain hook *not* stop an engine another live instance
   is using). Today `before-quit` → `/api/shutdown-idle` is a loaded gun in a multi-window world.
4. **Surface engine state** where a user can act on it (Settings → Diagnostics already shows the engine version;
   add liveness).
5. **Classify errors at the bridge** (`engine-unreachable`, `engine-timeout`, `engine-refused`,
   `bridge-unavailable` — the last already exists as `'Kel bridge unavailable — restart Kel and try again'` in
   `components/kel/kelApi.ts:call()`), and let the UI map classes to copy.

## Honest limitations

* The clean-launch result (green, twice) means this defect does **not** fire on every launch. Its severity comes
  from what happens when the engine is unavailable, which is: five screens of engine jargon and no way back.
* The exact 45 s deadline was not exercised end-to-end; the reproduction used a stopped engine rather than one
  that never started.
* `desktop.log` for the failing session was not captured in the probe; a follow-up run should copy it into the
  evidence set so the engine-side cause of any real-world failure is available.
