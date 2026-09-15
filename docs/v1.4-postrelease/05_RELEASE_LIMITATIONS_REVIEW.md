# 05 — Release Limitations Review

Each recorded V1.4 limitation (manifest / `AUTO_RESUME.md`) audited rather than repeated. Severity uses
the audit scale; all six were examined with source + recorded runtime evidence.

## 1. Engine shutdown on app close requires the bounded kill — **P3, not a blocker**

- **Why:** the engine refuses to die while work is open (by design). `KelService` registers a
  `before-quit` drain hook first (`KelService.ts:27-40`): POST `/api/shutdown-idle` → quit proceeds ~50 ms
  later regardless of the answer. `/api/shutdown-idle` only stops the server when no job is open, so a
  fixture with open work always refuses → the harness's bounded kill fires. Evidence: every capture run
  (`g4…g10`, `baseline` fixture run) records `closeOutcome: "close-timeout"`, while an idle probe run
  records `"closed"`.
- **State safety: yes.** WAL + transactional event store; brokers own runs and commit exactly one inbox
  receipt; restart adopts RUNNING/WAITING_APPROVAL runs or fences ORPHANED with no blind replay
  (`runner.py`, `engine.py` `recover_expired`); native effects fenced UNCERTAIN (`fence_uncertain_code`).
- **Process leak: bounded, no path found.** Coding broker descendants are held in a job object
  (`coding_transport.py:131` → `windows_job.py`); non-coding brokers are bounded by run timeouts
  (native cap 180 s, `runner.py:252`) and exit after their receipt; `native_processes` + the diagnostics
  orphan view surface leftovers at next start. Not re-tested live in this audit.
- **Block V1.4.1? No.** No data loss demonstrated. Recommended for V1.4.1 polish: make close
  deterministic (persist a shutdown intent, drain with a deadline message) or document the kill as the
  intended close path — every capture run currently exhibits it.

## 2. Migrated profiles see onboarding once — **P3, acceptable**

- **Mechanic:** the redirect is flag-based (`kel.onboardingCompleted_v1`) and only fires when the flag is
  absent (`Layout.tsx:138-161`; the comment records the fresh-install intent and that installs with
  conversations are never interrupted). A V1.3 profile has no flag → one first-run pass, then the flag is
  written. The release records this as a deliberate deviation of the flag-only rule.
- **Usability impact:** one-time friction only; no destructive migration (onboarding writes only the flag
  and preset settings). No migration risk found; `UPG-*` tests cover additivity and idempotence.
- **Patch-worthy? No.** Optional V1.5 nicety: seed the flag during V1.3→V1.4 upgrade for profiles with
  existing conversations.

## 3. Provider live calls remain donor-dependent — **P2 doc gap; functionality boundary confirmed**

- **Actual boundary:** packaged live calls happen through user-installed native CLIs (`codex`, `claude`)
  with their own auth, or through the internal adapter that reads an ambient `ANTHROPIC_API_KEY`
  (`service.py:37`). The Kel credential vault stores values in the OS store (safeStorage) and the engine
  stores `credential_ref` metadata only (`providers.py:199-213`) — but `getCredential` has **zero call
  sites**, so the documented runtime env injection (`SECURITY_MODEL` §3) is **not implemented** (D-05).
  Kel-managed API keys (e.g., DeepSeek) are registry + metadata today; they cannot yet drive live calls.
- **Failure modes (verified by code):** no key/CLI → no usable provider → `readiness()` raises with
  recorded reasons and the job waits (`WAITING_RESOURCE`), never fake progress. Native probes stay
  conservative (`native.py` probe: `tool_access=False`, `quality=None`).
- **Not re-exercised live** (no keys/CLIs in this audit environment). Recommendation: correct the docs in
  V1.4.1; implement injection in V1.5 **if** the product wants Kel-managed keys to actually work.

## 4. 142/200 ledger rows remain at triage — **benign, but ledger hygiene should catch up**

- Classification complete in `03_LEDGER_TRIAGE.md`: **72 already delivered / 38 valid post-release work /
  28 informational / 4 architectural drift / 0 release defects / 0 unverified**.
- The freeze-time decision to leave rows unadvanced did **not** hide a claimed-but-missing feature; but
  the ledger now understates delivery (72 rows). Advancing statuses with the citations from 03 is a
  documentation task (V1.5, optionally V1.4.1 docs patch).

## 5. Pet capture varied between candidate and assembled release — **not packaging drift**

- **Provenance:** candidate and frozen artifacts are **byte-identical** (`app.asar 53a34f62…`,
  `KelEngine.exe 5c093e32…`), both runs used the same populated data dir and the same harness. Pet assets
  ship in the release (`resources/pet-states`; pet manager in the app bundle).
- **Mechanic:** the harness enables the pet through the settings UI switch with fixed waits (nav → 2.2 s
  → click first `.arco-switch` with a 10 s timeout, errors swallowed → 2.6 s → enumerate non-main
  pet windows; `packaging/capture-screens.cjs` pets block). Candidate captured **2** pet windows; the
  assembled run recorded **0, explicitly** (`petWindowCount: 0` — a visible gap by design).
- **Verdict:** packaging drift is excluded by byte identity; the evidence is most consistent with harness
  timing/click sensitivity on the colder first run of the copied release (feature proven end-to-end on the
  candidate). Recommendation: make the step deterministic (wait for the switch, retry once, assert the
  config write) — harness hardening, V1.5. No functional defect demonstrated; live re-run was not possible
  in this audit (aesthetic/visual re-verification also unavailable — see 6).

## 6. No vision-based aesthetic verdict — **limitation accepted, not papered over**

- This audit performed **no** aesthetic judgment and does not pretend to. What was done instead:
  source/layout checks (token system, `KelPrimitives` as the design-system enforcement point), mechanical
  accessibility evidence (0 contrast failures in both themes, 30/30 tab stops ringed, skip link first),
  the mechanical sweep (0 emoji, 0 gradients, reduced-motion present), and manifest re-reads (0 renderer
  errors across 18 manifests). Taste-level quality remains **outside what this audit can certify**; any
  aesthetic sign-off must come from a vision-capable review or a human.
