# Kel v1.6 program — auto-resume (continuation state)

State at this writing: pre-program checkpoint frozen; program Phases 0–2 complete, verified, and
committed on `ux/v15-journeys`. Phase 3 (in-chat approvals) is the next unstarted phase.

## Frozen checkpoints (never touch either)

- Pre-program checkpoint: tag `v1.6.0-pre1` (annotated, commit `f24d9c2`, artifact source `0fb095f`),
  folder `Kel Releases\Kel-V1.6.0-Pre1-Frozen`, verifier 3/3, byte-identical to `package-final11`.
- Older frozen releases V1–V1.5: verified 3/3, byte-untouched.

## Program progress

| Phase | State | Evidence |
| --- | --- | --- |
| -1 Safety freeze | DONE | `docs/v1.6/00_CHECKPOINT_FREEZE.md` |
| 0 Session-tools closure | CLOSED | fresh 545-suite + packaged sessiontools 24/24 identical |
| 1 Memory proposal surface | DONE — commit `a8c3511` | `docs/memory-proposals/` (engine 568 then, packaged `memoryprops` green, review CONTINUE) |
| 2 Artifact lineage | DONE — commit (this one) | `docs/artifact-lineage/` (engine 574, packaged lineage probe green on `package-final15`) |
| 3 In-chat approvals | NEXT | — |
| 4–15 | pending | see the program brief |

Latest verified candidate: `dist/package-final15/win-unpacked` (engine rebuilt with lineage; desktop
with memory + lineage surfaces). `package-final12` is a superseded intermediate (UI bug); never cite
it. `package-final13` is the memory-proposals evidence artifact.

## Verify quickly (any resume)

1. `cd runtime && python -m pytest tests -q` → 574 passed (+10 subtests).
2. `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → 76.
3. Packaged journeys: `bash ux-audit/run-memoryprops.sh` (needs final13) and
   `bash ux-audit/run-lineage-probe.sh` (needs final15) — edit `APPW` inside each to the current
   candidate when a newer package exists.

## Sharp edges learned so far

- Packaged UI probes: the chat header pills (model/tools/review) render only on
  `#/conversation/<id>` pages; the report/detail text lives in an **open shadow root**
  (`.markdown-shadow` → `host.shadowRoot.textContent`).
- `/api/memory` `proposals` returns `{proposals:[...]}`; `/api/lineage` returns `{versions:[...]}`.
- Migration 15 = memory proposals (registered). `artifact_lineage` is deliberately unversioned (core
  schema, like `runs`). Upgrade-test version pins in `test_v13_memory.py` / `test_v14_upgrade.py`
  were updated for 15 by design.
- Freeze tooling nests an inert runtime duplicate (`resources/kel-engine/kel-engine/`); the V1.6.0-pre1
  freeze removed it after assembly for exact candidate↔frozen identity — do the same at the final
  release (or fix `freeze-release.ps1` first).
- `bunx electron-builder --config kel-builder.json --win --x64 --config.directories.output=../dist/package-finalNN`
  is the packaging command used; builds take ~8–10 min (NSIS inside).

## Next phase brief (Phase 3 — in-chat approvals)

Chat gets contextual approval cards (Allow once / Allow for this chat where appropriate / Deny /
Details) for folder access and external actions; Work stays the durable record; ONE approval engine
(the existing approvals/effects tables + `authorize.py` layer order); plain language; consequence
explained; work continues automatically after approval where safe; denial respected; no duplicated
engines; technical details behind Details. Follow the Phase 1/2 playbook: design → relay review →
engine + service + UI + tests → packaged journey → docs (`docs/in-chat-approvals/`) → JR rule +
history → commit → relay review.
