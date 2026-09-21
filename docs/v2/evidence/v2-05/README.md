# V2-05 evidence — Kel on a phone

Everything here was produced by driving the **built** app through the **real gateway**, in a real
browser engine, at an iPhone viewport. Nothing is CSS reasoning.

## How to reproduce

```bash
# 1. engine (V2 test data)
cd kel-v2 && KEL_SKIP_TELEMETRY=1 python runtime/kel_backend_entry.py \
  --data "C:/Users/Nick/KelV2Runs/prepared/engine"

# 2. renderer build + gateway (print the dev password on first start)
cd desktop && bun run package
AIONUI_DATA_DIR="C:/Users/Nick/KelV2Runs/prepared/web" \
AIONUI_BACKEND_BUNDLED_DIR="C:/Users/Nick/KelV2Runs/prepared/devtools/bundled-aioncore" \
AIONUI_STATIC_DIR="C:/Users/Nick/Desktop/Kel/kel-v2/desktop/out/renderer" \
KEL_DATA_DIR="C:/Users/Nick/KelV2Runs/prepared/engine" bun run webui

# 3. the phone journeys (real Chromium, 393x852, iPhone UA, fake mic device)
KEL_DEV_PASSWORD=... bunx playwright test tests/e2e/kel-mobile.e2e.ts
```

`desktop/tests/e2e/kel-mobile.e2e.ts` is the journey file; `findings-A|B|C|D|E|F.json` are its raw
observations, and the `*.png` files are what the phone showed at each step.

## What the journeys proved

| Journey | Result |
| --- | --- |
| A — "what is happening with Kel?" | The signed-in phone lands on Kel's home and answers it: **"While you were away — 2 need you"** with two connection items and a truthful hold ("None of your connected models is available right now, so Kel will wait instead of guessing"). Post-sign-in: **zero failed reads, zero console errors, zero dead WebSocket retries.** |
| B — conversation from the thumb | The composer takes **paste-shaped input** intact (3 lines), and the send control has a reachable box (`x=335.5 y=685 32x32`, inside 393px). It is **disabled** while no model is connected — the same gate the home names out loud. |
| C — what needs Nick, answered | Tapping the attention action **"Set it up"** opens **Providers** on the phone with real state: *"4 providers · 2 usable right now"* (Claude Code + Codex CLI available). |
| D — project surface | Reached; the phone's collapsed rail is inert by design (`x=-11`, `pointer-events: none`), so navigation is the drawer's job, not the rail's. |
| E — voice | The mic control starts a real recording ("Recording 0:20", Cancel/Stop) and stops. **No transcription request reaches the backend and no transcript appears** — see the limitation below. |
| F — PWA contract | Manifest is Kel (`name: Kel`, `standalone`, 2 icons, no donor words), service worker registers and controls (`kel-webui-v2`), **0 cached `/api/` entries**, no overflow, clean console. |

Overflow checks: every surface measured `scrollWidth == clientWidth == 393` — **0 horizontal
overflow** on the home, work, providers, project and shell surfaces at 393x852.

## The blocker this increment fixed

`403 /kel/api/providers`, `403 /kel/api/autonomy` — and the shell's honest-but-helpless *"Heads-up: Kel
is not answering right now (403)"*. Kel's engine authorizes a request only when `Host` is its own and
`Origin` is absent or its own; the gateway forwarded the **browser's** `Origin`, which can never be the
engine's. Every mutating Kel route therefore failed from a browser — a phone could read `/api/state`
and nothing else. The gateway now drops `origin`/`referer` the same way it already dropped the session
cookie, so it reaches the engine exactly as the desktop does (pinned in
`desktop/tests/unit/kel-remote-bridge.test.ts`).

## Honest limits recorded for V2-05

1. **Voice → Muse is not wired from the browser.** Recording works on the phone, but stopping it sends
   no `/api/transcription` request (0 in the gateway log) and no transcript appears. Desktop voice was
   repaired and verified in the Daily Driver line; the browser path still has to be connected.
2. **Sending needs a connected model.** With none connected the composer's send stays disabled and Kel
   says why. The phone can reach Providers (C) but this increment did not connect one, so no model turn
   was spent and "send, then continue context" was not exercised end to end.
3. **Attention actions were exercised only for the kind this instance had** (a connection needing
   setup). Approval / deny / grant / resume / stop attach to job state that did not exist here.
4. **Conversation history was not reached from the phone in this run** — the seeded conversation
   (`main`, title "Phone journey seed…") exists in authoritative state and shows through
   `/api/state`, but the automation never opened the drawer that lists it.

## Second pass — mobile voice works, through Muse

Root cause (no speculation left in it): `KelMicButton`'s own `request()` required `window.kelAPI`, the
**desktop preload bridge**, which a phone browser never has. So `start()` threw "Kel is not connected"
before a single request left the page — and the `try/catch` around `stream_start` swallowed it. That is
why the recording UI ran, the gateway saw zero `/api/transcription` traffic and nothing ever appeared.

Fix: transcription now goes through `kelRequest` — the same transport as every other Kel call (preload
on the desktop, the session-gated `/kel` gateway on the phone) — and a failed `stream_start` is said out
loud in plain words (`Live typing is not available right now — Kel will transcribe the recording when you
stop.`), with the reason kept for the moment the user stops. Nothing fake is substituted: the engine's
own practice mode is only entered when it is asked for by name, and `FixtureProvider` signs its work
("Practice transcript for …"), which the journey asserts must never appear.

Journey E, real Chromium at 393x852, real built app, real gateway, real Muse:

- microphone = Chromium's fake capture device playing **real speech** generated on this machine
  (`muse-phrase-24k.wav`, 24 kHz mono PCM16 — the shape Kel's own capture produces; Muse rejects other
  rates with an unmapped status, which is what the earlier 22.05 kHz fixture hit);
- the phone sent `stream_start` + 27 `stream_chunk` + `stream_finish` through the gateway;
- Muse answered, and the composer received **`Calmuse verification green baseball 64`** (Muse's own
  reading of "Mobile Kel Muse verification, green baseball sixty-four." — `Kel Muse` heard as `Calmuse`,
  the leading word not in the final partial);
- gate: `transcriptionCalls.length > 0`, transcript matches `/baseball/` and `/64|sixty/`, and no
  `practice transcript` text.

Engine ground truth, driven directly for comparison: `stream_finish` on the same audio answers
`mobile Calm use verification green baseball 64`.

### Still open in V2-05 (unchanged by this pass)

- **Send with a connected model.** The phone reaches Providers ("4 providers · 2 usable right now",
  Claude Code + Codex CLI "Ready to use") and Connections ("The services Kel can use", Add a service,
  Set up GitHub/Stripe/Figma/Slack), but this pass did not select a model, so the composer stayed
  disabled and no model turn was spent. The positive send path is not claimed.
- **Conversation history / drawer.** Journey B opens the composer and pastes into it; the drawer entry
  that lists conversations is still not reached by the automation.
- **Job-driven attention actions** (approve / deny / grant / resume / stop / review) — no authoritative
  job state existed to exercise them.
- **Conversational project routing** — untouched; not claimed.
- **Multi-utterance dictation:** recording past one utterance can lose the earlier words, because Muse's
  realtime frames for the first utterance were never marked final (measured: replies went
  `Calmuse verification, green baseball 64` → `Mobile` → `Mobile Calmuse`). The engine accumulates
  *finalized* turns correctly; the follow-up needs Muse's end-of-stream frame semantics before changing
  anything.
