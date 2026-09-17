# Kel v1.6 program — auto-resume (continuation state)

State at this writing: pre-program checkpoint frozen; program Phases 0–3 complete, verified, and
committed on `ux/v15-journeys`. Phase 4 (i18n / donor-string cleanup) is the next unstarted phase.

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
| 2 Artifact lineage | DONE — commit `ffeef73` | `docs/artifact-lineage/` (engine 574, packaged lineage probe green on `package-final15`) |
| 3 In-chat approvals | DONE — commit (this one) | `docs/in-chat-approvals/` (engine 592, packaged approvals journey all-green + lineage probe re-run on `package-final16`) |
| 4–15 | pending | see the program brief (Phase 4 next) |

Latest verified candidate: `dist/package-final16/win-unpacked` (engine rebuilt with in-chat approvals;
desktop with memory + lineage + approval surfaces). `package-final12` is a superseded intermediate
(UI bug); never cite it. `package-final13`/`package-final15` are the memory/lineage evidence
artifacts; `package-final16` is the Phase 3 evidence artifact.

## Verify quickly (any resume)

1. `cd runtime && python -m pytest tests -q` → 592 passed (+10 subtests).
2. `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → 76.
3. Packaged journeys: `bash ux-audit/run-approvals.sh` (needs final16), `bash ux-audit/run-lineage-probe.sh` (now final16), `bash ux-audit/run-memoryprops.sh` (needs final13) — edit `APPW`
   inside each to the current candidate when a newer package exists.

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
- In-chat approvals: anchors live in `approval_announcements` (core schema, unversioned); chat
  resolution must always delegate to `Autonomy.resolve_expansion` / `Store.resolve_approval`.
- The repo's `better-sqlite3` binary is Electron-ABI; system Node cannot load it — keep journey DB
  assertions in Python (`ux-audit/verify-approvals.py`), not in Playwright probes.

## Next phase brief (Phase 4 — i18n / donor-string cleanup)

Audit ALL supported locales and every normal user-facing surface: donor identity (AionUI, Butler,
stale names), stale Autonomy wording, runtime/worker/lease/scope jargon, raw localization keys,
missing translations, inconsistent Kel naming, obsolete feature names, stale provider/tool terms.
Do not merely grep English — validate locale catalogs and rendered packaged surfaces; keep donor
attribution required by licenses (legal/about/license surfaces) while removing accidental donor
product identity; no raw keys, no obsolete menu/settings entries. Verify in the packaged app;
commit/review if material. Follow the Phase 1/2 playbook: design → relay review → implement →
packaged verification → docs → JR rule + history → commit → relay review.
