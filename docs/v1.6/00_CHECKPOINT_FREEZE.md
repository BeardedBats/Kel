# 00 — Pre-program checkpoint freeze (Kel v1.6.0-pre1)

Status: **frozen** — checkpoint identity `v1.6.0-pre1`; frozen at
`C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.6.0-Pre1-Frozen` (assembled with
`scripts/freeze-release.ps1`, verified 3/3 by `scripts/verify-release.ps1` at the frozen location).

This is the mandatory pre-program safety freeze of the final pre-release program (memory proposals,
artifact lineage, in-chat approvals, i18n cleanup, agent-to-model assignment, Rust audit, final
release). It is **not** the final release and must never be modified, re-tagged, or reused as one.
The final release is decided separately (Phase 15) and must have a different version, tag, and path.

## Identity

| Field | Value |
|---|---|
| Branch | `ux/v15-journeys` |
| Artifact source commit | `0fb095f` — `0fb095fec1d2e8bd640c205c9d6f4f5ab0430fb7` ("Harden grant spend and refresh evidence on final11") |
| Record commit | the commit this file was finalized in (tagged `v1.6.0-pre1`); docs-only over `0fb095f` |
| Checkpoint tag | `v1.6.0-pre1` (annotated, clearly non-final) |
| Candidate | `dist/package-final11/win-unpacked` (+ installer `Kel-1.5.0-win-x64.exe`) |
| Version identity | engine `ENGINE_VERSION` `1.5.0`; desktop `package.json` `1.5.0` (bump happens at the final release, not here) |
| Frozen path | `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.6.0-Pre1-Frozen` |

## Hashes (frozen folder; full list in its `SHA256Sums.txt` / `SHA256Sums.txt.txt`)

| Artifact | SHA-256 |
|---|---|
| `Kel.exe` | `d573bf0456871df9fe86497586f6996a0e21be7c166adf92fdb6e426136f820b` |
| `resources/app.asar` | `907631cc1694c1cda1e5e7613663f3e82fb665d2e910d546757277ec4f915e1b` |
| `resources/kel-engine/KelEngine.exe` | `e019d002de7eb4b93589fc2c7ce65bc8aa05661e90562f6527bd633ff9dc248c` |
| `resources/bundled-aioncore/win32-x64/aioncore.exe` | `67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892` |
| installer `dist/package-final11/Kel-1.5.0-win-x64.exe` | `8156e1070ef738ca1c87aafd20115ab131f4258bd2cd61a891c882a30ec1bef1` |

## Pre-freeze confirmation (required)

- Working tree clean at freeze; HEAD `0fb095f`; no owned stray processes (no `Kel*`/`electron`).
- Artifact ↔ source: `KelEngine.exe` built 01:01:46 and `app.asar`/`Kel.exe` 01:03:21, both **after**
  the last source edit (`runtime/kel/capabilities.py` 01:01:22); commit `0fb095f` (01:07:38) contains
  exactly those source edits plus docs; an mtime scan found **no** source file newer than its build
  output. The candidate therefore corresponds to the committed source at `0fb095f`.

## Fresh verification (all run for this checkpoint, 2026-09-17 ~01:13–01:55 local)

| Check | Result | Evidence (scratch, not shipped) |
|---|---|---|
| Engine suite | **545 passed + 10 subtests** (137.45 s) | `runtime python -m pytest tests -q` |
| Desktop typecheck | **0 errors** | `desktop bunx tsc --noEmit` |
| Desktop tests | **76 passed** / 5 files | `desktop bun run test` (vitest) |
| Packaged battery on `final11` | 20 result files, **0 errors / 0 console errors everywhere** | `ux-audit/runs/f11-*` |
| · sweep2 composer/drafts/markdown | 0 errors; only the known provider-dependent timeouts (`copy-toast`, `failure-surface`, `retry`) | `f11-a` |
| · sweep3 theme/model/backup | 0 errors, no timeouts; theme colors, accent, contrast warning, model card/pill | `f11-b` |
| · sweep4 backup/restore/restart | 0 errors; backup created, restore confirm, provider form scroll | `f11-c` |
| · transcription | identical to the shipped final6 baseline (27/27 flags) | `f11-t` |
| · hardening (narrow 980px, jargon, keyboard) | identical (18/18 flags) | `f11-h` |
| · voice-vetting | identical flags (one runtime UUID in a truncated preview differs, by design) | `f11-vv` |
| · vetting | identical (16/16 flags) | `f11-vt` |
| · keepawake (donor-derived pass) | full cycle: Off → Active → restart → Active → disable → Off | `f11-kaw` |
| · sessiontools (session-scoped tool controls) | **24/24 keys identical** to the documented run; DB transcript probe `reply_renders_after_user_message: true` | `f11-st` |
| · standing set + first-run | tour / settings / palette / keyboard / readability / sider / maintext / first-run: 0 errors | `f11-std`, `f11-first` |
| a11y + skip-link probes | `contrastFailureCount: 0` (boot + work drawer), `focusIndicatorMissing: 0`, skip link OK | `f11-probes` |
| Packaged smoke | `engineStopped: true`, `appExited: true`, `errors: []` | `f11-smoke/smoke-result.json` |
| Packaged acceptance (PKG-01..09) | all non-vacuous assertions pass; `page_errors` `[]` on both runs | `f11-accept` |
| · PKG-05 note (honest) | On a fresh profile the check is vacuous (its formula needs pre-existing records; the product runtime has no automatic memory-write path — verified with `git grep` at tag `v1.3.0`; the historical 1→1 run used a seeded profile). Positively re-proven: one record seeded through the engine's own Memory API, then two packaged launches read it from the Work payload → `records 1 → 1`, `memory_survived: true`, `page_errors: []` | `f11-accept/memory-survival-probe.json` |
| Packaged UI (Work & context drawer) | five sections render, empty states, recipes, preview, `consoleErrors: []` | `f11-ui` |
| **Frozen copy smoke** (run from the frozen folder itself) | launched, engine 1.5.0, `engineStopped: true`, `appExited: true`, `errors: []` | `f11-frozen-smoke/smoke-result.json` |

Mapping notes for the required list: backup/restore = sweep3+sweep4; scrolling = sweep2 route
matrix + seeded rich chat + sweep4 provider form + hardening narrow windows; model selection =
sweep3 (card/pill/persistence) + engine `model_prefs` tests in the 545; User Journey regression =
standing set + first-run; donor-derived UX = keepawake (+ the final8 findings unchanged);
transcription / vetting / session-tools as above.

## Freeze integrity

- Assembled by `scripts/freeze-release.ps1` from the candidate. The tool's second runtime copy
  normally nests an inert duplicate (`resources/kel-engine/kel-engine/`; the released V1.5 folder
  carries the same artifact as `KelEngine/`). It was removed **before** the frozen copy was made so
  that the frozen tree is exactly the candidate plus the two sums files and the manifest. The four
  hashed targets are untouched; `SHA256Sums.txt`/`SHA256Sums.txt.txt` were generated from the
  candidate itself.
- **Candidate ↔ frozen identity**: full-tree SHA-256 comparison of every file — byte-identical
  (excluding the two sums files and the manifest) → also re-verified at the frozen location.
- Release verifier: **3/3** at the frozen location.
- Prior frozen releases (V1, V1.1, V1.2, V1.3, V1.4, V1.4.1, V1.5): **re-verified 3/3 and
  byte-untouched** (V1.5 independently cross-checked against its documented
  `CF1984AC… / 51DD5DFE… / AB3024A0…`).

## Terminal proof

```
PRE-PROGRAM CHECKPOINT FREEZE VERIFIED
checkpoint version : v1.6.0-pre1
checkpoint tag     : v1.6.0-pre1 (annotated)
artifact source    : 0fb095f (record commit tagged; docs-only over it)
frozen path        : C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.6.0-Pre1-Frozen
hashes             : Kel.exe d573bf04… · app.asar 907631cc… · KelEngine.exe e019d002… · aioncore 67eb0277…
verification       : 3/3 at frozen location; candidate↔frozen full-tree byte-identical
prior frozen       : all seven re-verified 3/3, byte-untouched
```

## Carried limitations (see `docs/session-tools/08_KNOWN_LIMITATIONS.md` for detail)

- No live model provider on this machine: conversation-scoped effects are proven at the
  authorization boundary and by the packaged journeys, not by a live model turn.
- Capability conflict handling answers with a plain refusal + the Tools menu (richer inline card is
  a docket item).
- Drive / Connected apps stay “Needs setup” until a connector owns them.
- PKG-05 note above (acceptance script check is vacuous on fresh profiles; re-proven with a seeded
  record).

## Program position

Phase -1 (this freeze) is complete. The program continues with Phase 0 (session-scoped tool controls
closure check — already re-verified by the fresh 545 + `sessiontools` run above) and then the
docket: memory proposal surface (`docs/basic-ux-sweep/18_DONOR_FEATURE_REMEDIATION.md` §6), artifact
lineage, in-chat approvals, i18n, model assignments, richer memory UX, capability recommendations,
advanced worker view decision, profiles decision, real-provider validation, Rust audit, integrated
regression, independent review, final release.
