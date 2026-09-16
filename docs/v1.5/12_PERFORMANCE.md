# 12 — Performance (Kel V1.5)

Status: **measured** — first recording 2026-09-15 on this working tree (G8). Numbers were produced
by the recorded commands below on the development machine (Windows, Python 3.14.3, desktop Node
toolchain); they are one build's basis, not a promise. Phases not recorded here are simply unknown —
the live view is `kel diagnostics performance` / `/api/diagnostics {action: "performance"}`, which
reports the spans the engine actually recorded.

## Engine (Kel runtime)

| Measure | Result | Basis |
|---|---|---|
| `import kel.service` | ~60 ms | one cold import, this machine |
| `Store` open (fresh data root) | ~46 ms | `Store(root)` constructor |
| `Service` start (store + adapters + engine) | ~650 ms | `Service(root)` constructor; per-boot startup spans are stored in `startup_spans` and surfaced by `diagnostics.performance()` |
| Authorization decision | ~30 ms/decision | 200 sequential `Authorizer.decide()` calls, each with a fresh target and each writing a durable `guardrail_decisions` row (single-writer SQLite with fsync) — the deliberate cost of the audit record |
| Diagnostics snapshot | ~8 ms | 50 sequential `Diagnostics.snapshot()` calls on a small database |

Method: a probe script run from `runtime/` (fixture store + coding job) measuring wall time with
`time.perf_counter()`; the same quantities are visible live through `/api/diagnostics`.

## Desktop shell

| Measure | Result | Basis |
|---|---|---|
| `tsc --noEmit` | ~30 s, 0 errors | full desktop project |
| vitest (web-host lane) | 4 files / 72 tests, ~29 s | `vitest run` |
| `electron-vite build` (production) | ~32–39 s, exit 0 | `npm run package` |
| Renderer bundle | vendor 4.76 MB · index 3.71 MB · largest route chunk 420 KB | minified, uncompressed, from the build output; the build warns above 1500 kB — code-splitting is recorded as a V2+ improvement, not a V1.5 claim |

## Engine suite

Full `python -m pytest tests -q` on this working tree after G8: **441 passed + 10 subtests**,
~85–100 s. V1.4.1 baseline: 375 + 10. The V1.5 additions bought ~15 s of suite time for
authorization, memory, credential, and diagnostics coverage.

## What is deliberately not claimed

- No cross-machine benchmark; every number above is a single dev-machine basis.
- No renderer startup / first-paint timing yet — the desktop lane has no automated renderer-timing
  harness; live startup spans cover the engine side only.
- No memory-query latency series (single measurements exist inside the memory tests).
