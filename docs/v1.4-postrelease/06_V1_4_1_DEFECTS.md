# 06 — V1.4.1 Defect Candidates

Patch decision rule applied: **V1.4.1** only for release defects, security issues, data-loss risks,
broken core architecture, serious reliability problems, regressions, or functionality the release
explicitly claims but does not provide. Everything else goes to 07/08. Audit made **no code changes**.

## Recommended for V1.4.1

### D-01 — Capability-lease / guardrail enforcement is not integrated with execution — **P1**
- **Intended:** every delegated action is checked against its lease; locked guardrails (registry /
  active-screen / OS-critical writes, frozen paths, credential boundary, Firefox-only browser, snapshot
  rule for destructive actions) refuse at execution time and record a `guardrail_decisions.rule_id`
  (`KEL_V1.4_AUTONOMY_POLICY.md:24,34-36,57,65`; `KEL_V1.4_ARCHITECTURE.md:39,76`).
- **Actual:** the checker is complete and tested, but **nothing calls it on the execution path** — the
  only import is the `/api/autonomy` endpoint (`service.py:582-583`); no runner/coding/apply/native module
  references autonomy; `guardrail_decisions` exists nowhere in code; AUTO-* tests exercise
  `Autonomy.check()` directly (`test_v14_autonomy.py`). `SECURITY_MODEL.md:69-72` ("enforced by the locked
  guardrail module and verified by tests") is therefore **false as implemented**.
- **Impact:** workers can attempt locked capabilities; only their own CLI flags and the snapshot topology
  limit them (see D-02).
- **Recommended:** V1.4.1 — minimum: correct AUTONOMY_POLICY/SECURITY_MODEL/TEAM_MODEL claims; preferred:
  wire `Autonomy.check` + guardrail evaluation at the runner/coding/apply boundaries and record decisions.

### D-02 — Coding host containment claims vs `danger-full-access` execution — **P1**
- **Intended:** "worker processes contained" (SECURITY_MODEL §6), guardrails verified by tests.
- **Actual:** `host_runtime.py:1` states "This runtime is not a sandbox"; Codex is launched with
  `sandbox_mode="danger-full-access"`, `approval_policy="never"` (`:37,45,49`); every coding contract
  declares `runtime:'native-host'` (`coding.py:33`). Practical containment is an isolated git snapshot +
  Kel-run tests + the evidence-gated apply path — not an OS boundary.
- **Recommended:** V1.4.1 — make the docs state this boundary exactly (user-authorized native host inside
  an isolated snapshot), and/or constrain the host (sandbox policy, allowlist) if containment is claimed.

### D-03 — Emergency stop is partial — **P2**
- `autonomy.py:326-338` revokes active leases only; it does not pause/cancel broker runs or signal
  workers. "Stops everything now" is not what the code does. V1.4.1: implement run control alongside
  revocation, or state the exact scope in the UI and policy doc.

### D-04 — Caller-supplied actor gate + token at rest — **P2**
- `/api/autonomy` defaults `actor='user'` (`service.py` handler); approvals/grants/emergency-stop trust
  the caller string. The engine descriptor token sits in a plaintext JSON readable by same-user
  processes. Local single-user threat model, but the "only the user can approve" claim is weaker than
  stated. V1.4.1 hardening: bind resolutions to an interactive (UI-origin) handle and tighten token-file
  ACLs; document the trust model.

### D-05 — Credential injection documented but unimplemented — **P2**
- `SECURITY_MODEL` §3: "at run time the engine receives the value as an environment variable for that
  single child process". Reality: `getCredential` has **zero call sites**; the engine reads ambient env
  (`service.py:37`); Kel-managed providers are metadata-only. V1.4.1: correct the doc (and optionally
  implement injection — full implementation likely V1.5).

### D-08 — Version labeling mismatch — **P3 (cheap)**
- `ENGINE_VERSION='0.5.0'` (`service.py:24`) and `desktop/package.json` `"version": "0.5.0"` surface in
  Diagnostics/About while the product is V1.4.0. V1.4.1: align or document the convention.

## Reviewed and NOT defects (do not stuff into V1.4.1)

- **Pet-capture variance (candidate 2 vs assembled 0):** byte-identical artifacts; harness timing/click
  sensitivity; harness hardening → V1.5 tooling (05 §5).
- **Close-timeout / bounded kill:** recorded limitation, state-safe (05 §1) → V1.5 polish.
- **142 triage rows:** 0 release defects after classification (03) → ledger advancement is docs hygiene.
- **Donor identity strings (tray tooltip `tray.ts:265`, notification title
  `useBrowserNotification.ts:66`, `[AionUi]` logs, donor ChannelConflictWarning copy, cron/login/
  TestShowcase pages):** visible identity leaks against the "one identity" promise → **D-06, V1.5**
  (optional V1.4.1 if a hotfix train runs; cosmetic, no functional risk).
- **Release-manifest coverage (`debug.log` carried, bare hashes without filenames, unhashed donor
  `aioncore.exe`, docs added post-assembly):** V1.5 tooling → **D-07/D-09**.
- **Ledger statuses stale for 72 delivered rows:** V1.5 docs → **D-11**.

## Net

No P0. Two P1s (D-01, D-02) are one architectural theme: *the autonomy/guardrail layer is a checker, not
an enforcement layer, while the release documents claim enforcement*. Three P2s (D-03…D-05) and three
cheap P3s (D-06…D-11 split between V1.4.1-worthy labeling and V1.5 tooling). A **small V1.4.1 is
recommended** so the shipped documentation, emergency stop, and version labeling match reality; full
enforcement wiring may legitimately slip to V1.5 if the claims are corrected now.
