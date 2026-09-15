# KEL V1.2 — STATUS (Rounds 1–2: shell polish + engine trust)

Date: 2026-09-14. Baseline: Kel-V1.1 frozen (`Kel Releases/Kel-V1.1-Frozen`),
verified byte-identical to this workspace before Round 1 began (`diff -rq`; only
Agents.md and the two freeze-marker files differed).

## Round 1 scope (approved)

A — approval attention badge on the Work-context trigger.
B — hide donor agent/assistant/team/channel surfaces, keep useful settings.
E — window title "Kel".

### A — Approval attention badge — DONE

`KelWorkPanel.tsx`: the Work-context trigger in the Sider is now wrapped in an Arco
`Badge` showing the engine's global PENDING-approval count (from the existing
`/api/state` route, no engine changes). While the drawer is closed a silent 5s poll
updates the count; with the drawer open the existing 1.5s refresh updates it, so the
badge clears immediately after allow/deny. Count 0 renders nothing — no duplicate
indicator, no modals, no notifications.

### B — Donor surface cleanup — DONE

Hidden (routes redirect to the home screen; page bundles stay shipped so capabilities
remain intact):

- /assistants, /settings/assistants, /settings/agent, /settings/agent/:id/repair
- /settings/skills (+ import-history, detail), /settings/tools, /settings/capabilities
- /settings/model, /settings/skills-hub
- /team/:id (TEAM_MODE_ENABLED=false removes team route + titlebar/sider chrome)
- /settings now opens Appearance instead of the agent page
- SettingsModal: Model and Tools tabs removed; default tab is System
- WebUI settings: Channels tab removed (Slack/Discord/Lark/DingTalk integration)

Kept and verified working: Appearance, System (language, start-on-boot, close-to-tray,
hardware acceleration, timeouts), WebUI service settings, About, Pet, Archived,
Scheduled, Guid/onboarding, login, conversations.

Brand strings: About page ("Kel — One desktop. Your AI work engine."), WebUI copy,
start-on-boot and hardware-acceleration copy — "AionUi" replaced with "Kel" across
all 7 shipped locales (en-US, zh-CN, zh-TW, ja-JP, ko-KR, tr-TR, uk-UA).

### E — Window title — DONE

`DocumentTitle.tsx` + `index.html` (application-name, apple-mobile-web-app-title,
`<title>`): AionUi → Kel. Packaged launch shows window title "Kel".

### Round 1 packaging (dedup + integrity pipeline)

- Rebuilt the AionUI donor fork (`electron-vite`, same toolchain as V1.1).
- Deployed tree = fresh extraction of the deployed V1.1 `app.asar`; only `out/renderer`
  overlaid from the fresh build. `out/main` and `out/preload` untouched (V1.2 makes no
  main-process changes).
- Packed with `asar-dedup-pack.js` (V1.1 pipeline).

Parity vs deployed V1.1 asar:

- entries: 10,589 == 10,589 (9,539 files + 1,050 dirs)
- dedup savings: 10,221,384 B == 10,221,384 B (identical groups)
- data size: -1,829 B (renderer-only deltas: title strings, hidden tabs, badge code)
- pack round-trip extraction: lossless (0 diff lines)
- renderer chunk renames: expected cascade from the changed entry chunk (Vite
  content-hashing; ~112 chunks renamed, unchanged-content chunks kept their names)

V1.1 backup preserved at `_kel-work/backups/app.asar.v11-deployed` (hash matches the
frozen release manifest).

### Round 1 packaged verification (exact Kel.exe)

- 3 launch passes via Playwright/Electron: window opens, title "Kel", #/guid home,
  zero pageerrors, engine 0.5.0 boots per launch (desktop.log engine sessions).
- Settings walkthrough + route-redirect checks.
- Badge negative check: with 0 PENDING approvals no badge count renders.

## Round 2 scope (approved): C reviewer diversity + D trust/verification display

### C — reviewer diversity — DONE

- `service.py`: reviewer candidates = the default reviewer (selection unchanged:
  internal key → claude CLI → codex CLI) plus the remaining eligible installed CLI(s)
  as alternates (native alternatives still gated by KEL_REVIEWER != none).
- `commander.py`: per-artifact picker (`_reviewer`) ranks candidates by health
  (existing `provider_states`: open circuit / exhausted quota), then a different model
  family (internal + Claude CLI = anthropic; Codex = openai), then a different
  provider; ties keep the default preference order. Fewer than two candidates keeps
  the current fallback unchanged. Selection never blocks; provenance records the
  reviewer that actually ran; `descriptor(store, job, mid)` resolves the same pick for
  fallback records, and `engine._review_descriptor` uses it (reviewers without a
  descriptor keep the previous None identity; review recovery semantics unchanged).
- executor != reviewer run boundary (record_review: reviewer_id != artifact run_id)
  untouched.

Real two-CLI environment (claude 2.1.215 + codex-cli 0.142.5): telemetry reports the
Codex account at 0% remaining quota, so the health rule kept the healthy Claude
reviewer for a Claude-executed job — the unavailable independent provider fell back
gracefully and provenance records reality (`reviewer_provider=claude` in the
review.recorded event of the live run). Healthy two-provider selection is covered by
targeted tests (7 cases). One-provider / KEL_REVIEWER=none behavior preserved.

### D — trust/verification display — DONE

- `core.verification_summary(job)`: concise block for settled jobs only —
  "Verified / Uncertain / Failed" plus bullets built solely from persisted job state:
  Tests (repository_evidence), Sources (research_evidence), Failed check, Limitation
  (uncertain check reasons / milestone errors, deduped, max 2), Executed by and
  Reviewed by (labels: Claude Code / Codex / Claude <family> for internal models).
  No worker text, prompts, routing internals, or raw transcripts.
- `Store.publish()` appends the summary to the publication for all three verdicts.
  B2 four-part explanations are preserved verbatim; publication semantics
  (assess → single publication → message) unchanged.
- `acp_host.py`: a settled (CLOSED) job no longer prints the duplicate
  "Work state: CLOSED. Verification: X." line — the publication reply and the card
  title carry the result; CANCELLED / PAUSED / WAITING_RESOURCE / AWAITING_USER
  branches unchanged.

### Round 2 tests

- new: `tests/test_v12_reviewer_diversity.py` (7 cases), `tests/test_v12_trust_summary.py` (7 cases)
- full engine suite: **181 passed** (167 V1.1 baseline + 14), 10 subtests.

### Round 2 packaging (engine rebuild)

- PyInstaller 6.19.0 onedir from the same spec (`KelEngine-b3.spec`), same entry
  script; deployed to `resources/kel-engine/`.
- exe: 2,793,875 B (V1.1 2,789,288 B; +4,587 B = the five changed modules in the PYZ).
- `_internal/` parity: 30 files both; only `base_library.zip` differs (same 155
  entries, identical canonical content, entry order only — the documented build-order
  nondeterminism from B2→B6 era).
- PYZ inspection (`_kel-work/v12-engine/inspect_pyz.py`): embedded PYZ sha256
  `64036e36…` identical to the build PYZ; `kel.service`, `kel.commander`,
  `kel.engine`, `kel.core`, `kel.acp_host` are structurally identical to the current
  source and carry the V1.2 markers; vs the V1.1 exe the changed module set is
  exactly those five — nothing added, nothing removed.

### Round 2 packaged verification (exact deployed artifacts)

- Live engine boot (packaged exe): engine_version 0.5.0, providers
  codex / claude / codex-code / claude-code; `/api/state`, submit, settle and
  `/api/shutdown-idle` (exit 0) all exercised across runs.
- Representative success: real document task → CLOSED / VERIFIED; the publication
  carried the new summary ("Verified • Executed by: Claude Code • Reviewed by:
  Claude Code").
- Representative UNCERTAIN: real task with KEL_REVIEWER=none → CLOSED / UNCERTAIN;
  B2 explanation preserved + summary ("Uncertain • Limitation: Independent rubric
  review not recorded • Executed by: Claude Code").
- Packaged ACP presentation harness (`verify_presentation.py`) on the exact exe:
  CLOSED/UNCERTAIN, CLOSED/FAILED, CLOSED/VERIFIED stream the publication without
  the duplicate status line; CANCELLED keeps its one-line status — ALL PASS.
- Approval badge, positive path (exact Kel.exe, throwaway data dir): a real PENDING
  approval created through the store API shows badge count "1" in the packaged UI;
  resolved through the shell's engine API (DENIED) and the badge cleared; settings
  walkthrough (Appearance / System / About) rendered; zero pageerrors; title "Kel".
- Final packaged smoke: fresh data dir, launch OK (#/guid), normal quit → the drain
  stopped the engine (`engineStopped=true`), app exited, zero Kel/KelEngine
  processes and no orphaned children.
- Known behaviors (not regressions): the engine intentionally outlives the shell
  when work is active (durable jobs — drain only stops an idle engine); the badge
  E2E deliberately stopped its throwaway engine because that scenario leaves a
  stuck CANCELLING job.

## V1.2 freeze

- Frozen copy: `Kel Releases/Kel-V1.2-Frozen` (this workspace minus Agents.md, plus
  RELEASE_MANIFEST.md.txt and SHA256Sums.txt.txt, mirroring the V1.1 freeze).
- Key hashes: Kel.exe `E048632E…` (unchanged from V1.1), resources/app.asar
  `B56816B6…` (Round 1), resources/kel-engine/KelEngine.exe `11D9DBC0…` (Round 2).
- V1.1-Frozen confirmed untouched: its three summed artifacts still match
  SHA256Sums.txt.txt (E048632E… / F174432B… / C8DF4AF3…).
