# KNOWN_LIMITATIONS — honest limits of the Campaign A evidence

updated: 2026-09-18T16:05Z
rule: a limitation is never a hidden assumption. If it bounds what an evidence claim can mean, it
must be here.

| # | Limitation | What it bounds | Compensating evidence | Re-check |
|---|---|---|---|---|
| LIM-1 | **No independent audit during Campaign A.** All Campaign A verification is self/parent-executed. | Campaign A "PASS" means internally verified, never independently reviewed. Campaign B is the independence. | Historical audit discipline is preserved and referenced; the sprint directive explicitly pauses audits. | Campaign B |
| LIM-2 | **No real provider credentials validated yet** (dummy-key probes reached the wire once, 401). | PROVIDER_VALIDATION_MATRIX rows marked `mock/static` cannot be read as real validation. | Phase 10 attempts real calls where access allows; unavailable paths recorded as such. | Phase 10 + Campaign B |
| LIM-3 | **Human pixel review not performed** (agents have no image perception). | Visual "packaged acceptance PASS" is automated only; it is NOT visual sign-off. | SCREENSHOT_REVIEW_INDEX prepared for the human reviewer; `human_visual_gate: OPEN` tracked. | Human gate |
| LIM-4 | **Engine-loss behavior currently fails honestly but rawly** (findings 16/17: `TypeError: fetch failed` surfaces). | The RC must not claim graceful engine-loss UX until the fix lands and is evidenced. | Probe b reproduction documented in PACKAGED_EVIDENCE_INDEX. | When batch 6 lands |
| LIM-5 | Packaged migration assertions 15–19 not yet recorded. | Packaged app schema state on upgrade is not yet proven end-to-end. | RC checklist in MIGRATION_LEDGER.md. | At RC |
| LIM-6 | Historical F-finding limitations carried: F20-6 (ignored paths neither integrated nor counted), F20-14 (no conflict-resolution timing), N21-5 (undeclared writes reported not counted), R22-3 (evidence-package nits). | Workforce 5.5 guarantees hold within these recorded bounds. | Recorded in 5.5 record + audits 20–22. | Campaign B |
| LIM-7 | 5.6 learning limitations: lens-evidence mission scoping without a findings→project link; identical-value re-observation multiplicity (24-N2); rate denominator deviations (F23-2/8/9). | Metric reads carry small-sample/denominator caveats; nothing auto-applies. | Recorded in 5.6 record + audit 24 residuals. | Campaign B |
| LIM-8 | Reviewer sessions in this runtime are **static-only** (no execution); execution artifacts are parent-produced and commit-bound. | Historical "independent" verdicts verified artifacts rather than re-running them. Campaign B must re-run critical commands itself where possible. | Artifacts are reproducible from commits; commands documented in TEST_EVIDENCE_INDEX. | Campaign B |
| LIM-9 | Windows-only validation. | macOS/Linux behavior is unverified. | macOS pipeline concerns were treated in v1.5 gates; frozen releases exist for Win. | Release gates |
| LIM-10 | Frozen-release verification is hash-based. | It proves byte identity, not provenance beyond the manifest. | 4-hash manifests + freeze tools. | RC |
| LIM-11 | Conversation transcripts/chat history are NOT authoritative evidence. | This corpus is the evidence layer; chat is control-plane only. | AUTONOMOUS_OPERATION.md disk-backed handoffs. | Always |
| LIM-12 | **New v1.6 surfaces ship Kel-native English copy** (knowledge UI and sibling v1.6 surfaces); the release program's locale pass owns translations (declared in `docs/memory-proposals/04_UI_AND_COPY.md`). | Localized-release claims for the new surfaces. | en-US copy reviewed in packaged journeys. | Release gates (locale pass; DEF-013) |
| LIM-13 | **Memory stale-detection is engine-ready but unwired**: no production caller of `Memory.revalidate()` and no production `source_digest` producers. | "Stale" proposals never appear from real usage; the mechanism is test-covered only. | Stale flow covered by `test_v16_proposals.py`; disposition DEF-012. | When a repo-fact producer lands |
| LIM-14 | **Capability-recommendation card packaged rendering is unproven** (no provider ⇒ no blocked run can be produced here); transcript-inline placement pending (DEF-014). | Packaged evidence for Phase 7's UI surface. | Engine + unit coverage; the Work-panel placement is live for any blocked milestone. | Next packaged battery (RC) |

## PRE-AUDIT RC update (2026-09-19)

- LIM-14 (provider reality) unchanged at RC: provider validation runs as access allows.
- LIM-RC-1: packaged probes exercise first-run by the product's own "Skip setup" path (recorded in
  `r12-installed.json` steps).
- LIM-RC-2: engine-loss variants requiring approvals/effects "in flight" are not constructible in
  the isolated profile; covered at engine level (A-29) and recorded in `19_R10…`.
- LIM-RC-3: no agent performs pixel approval; the human visual gate stays PENDING with screenshots
  indexed (`r10-g`, `r12-work.png`, `r12-about.png`, `r12-exe-icon.png`).
