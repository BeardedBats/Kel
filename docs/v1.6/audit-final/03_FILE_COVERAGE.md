# 03 — FILE COVERAGE (8a2b25d..08f56673)

Range net diff: **189 files** (git name-status, 8a2b25d..08f56673). This table lists the **union of per-commit file lists** = **209 paths** (larger because merge-side and later-reverted paths appear per commit even when the net diff no longer shows them). Class: engine / desktop / tooling / test / docs / third_party / meta.
Every file below is mapped to the range commits that touched it (from `evidence/commit-file-lists.txt`); review depth for the corresponding commits is recorded in `02_COMMIT_COVERAGE.md` and the pass docs.

Counts: desktop=51, docs=94, engine=27, meta=1, test=32, tooling=4

| file | class | commits touching |
|---|---|---|
| `desktop/kel-builder.json` | desktop | 71c78f0 3050761 08f5667 |
| `desktop/package.json` | desktop | 93b99b5 3050761 08f5667 |
| `desktop/packages/desktop/src/preload/main.ts` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/process/services/kel/KelService.ts` | desktop | 0596211 101d8c3 3050761 2897207 34947f0 645898a fa66f04 7267630 |
| `desktop/packages/desktop/src/process/services/kel/engineHealth.ts` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/process/services/kel/engineVersion.test.ts` | desktop | 93b99b5 3050761 |
| `desktop/packages/desktop/src/process/services/kel/engineVersion.ts` | desktop | 101d8c3 3050761 |
| `desktop/packages/desktop/src/renderer/assets/logos/brand/app.png` | desktop | 71c78f0 3050761 |
| `desktop/packages/desktop/src/renderer/components/chat/KelWorkPanel.tsx` | desktop | 22f4a3e df87903 8a677d0 3050761 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/KelApprovalCard.tsx` | desktop | 8a677d0 594b8b4 3050761 |
| `desktop/packages/desktop/src/renderer/components/kel/KelCapabilityCard.tsx` | desktop | df87903 3050761 |
| `desktop/packages/desktop/src/renderer/components/kel/KelEngineNotice.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/KelFailureCard.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/KelModelControl.tsx` | desktop | 594b8b4 3050761 |
| `desktop/packages/desktop/src/renderer/components/kel/KelNeedsAttention.tsx` | desktop | 938dc9b 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/KelPrimitives.tsx` | desktop | c911d81 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/capabilityRecommendation.ts` | desktop | df87903 3050761 |
| `desktop/packages/desktop/src/renderer/components/kel/engineFailure.ts` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/kelApi.ts` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/kel/memoryRecordActions.ts` | desktop | 22f4a3e 3050761 |
| `desktop/packages/desktop/src/renderer/components/kel/needsAttention.ts` | desktop | 938dc9b 7267630 |
| `desktop/packages/desktop/src/renderer/components/layout/Layout.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/components/layout/Router.tsx` | desktop | 3d9202c 3050761 7267630 |
| `desktop/packages/desktop/src/renderer/components/layout/Sider/index.tsx` | desktop | 3d9202c 3050761 7267630 |
| `desktop/packages/desktop/src/renderer/components/settings/SettingsModal/contents/AboutModalContent.tsx` | desktop | 71c78f0 3050761 |
| `desktop/packages/desktop/src/renderer/pages/conversation/GroupedHistory/ConversationRow.tsx` | desktop | ac85eb3 3050761 7267630 |
| `desktop/packages/desktop/src/renderer/pages/conversation/components/ChatConversation.tsx` | desktop | 0e7d21a 7267630 |
| `desktop/packages/desktop/src/renderer/pages/conversation/platforms/acp/AcpChat.tsx` | desktop | 0e7d21a 7267630 |
| `desktop/packages/desktop/src/renderer/pages/conversation/platforms/acp/AcpSendBox.tsx` | desktop | 0e7d21a 7267630 |
| `desktop/packages/desktop/src/renderer/pages/conversation/utils/conversationAssistantIdentity.ts` | desktop | ac85eb3 3050761 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/autonomy/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/diagnostics/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/onboarding/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/projects/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/providers/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/team/index.tsx` | desktop | 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/transcription/index.module.css` | desktop | 83af16f 3050761 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/transcription/index.tsx` | desktop | 83af16f 3050761 2897207 7267630 |
| `desktop/packages/desktop/src/renderer/pages/kel/work/index.tsx` | desktop | 2897207 938dc9b 7267630 |
| `desktop/packages/desktop/src/renderer/pages/settings/AppearanceSettings/CssThemeSettings.tsx` | desktop | 594b8b4 3050761 |
| `desktop/packages/desktop/src/renderer/styles/kel-tokens.css` | desktop | 8dd21f9 3050761 2897207 c911d81 938dc9b 7267630 |
| `desktop/packages/desktop/src/renderer/styles/themes/default-color-scheme.css` | desktop | 8dd21f9 3050761 7267630 |
| `desktop/public/pwa/icon-180.png` | desktop | 71c78f0 3050761 |
| `desktop/public/pwa/icon-192.png` | desktop | 71c78f0 3050761 |
| `desktop/public/pwa/icon-512.png` | desktop | 71c78f0 3050761 |
| `desktop/resources/app.icns` | desktop | 71c78f0 3050761 |
| `desktop/resources/app.ico` | desktop | 71c78f0 3050761 |
| `desktop/resources/app.png` | desktop | 71c78f0 3050761 |
| `desktop/resources/app_dev.png` | desktop | 71c78f0 3050761 |
| `desktop/resources/branding/kel-logo.png` | desktop | 71c78f0 3050761 |
| `desktop/resources/icon.png` | desktop | 71c78f0 3050761 |
| `docs/v1.6-visual-ux/00_STATUS.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/01_HUMAN_FINDINGS.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/02_VISUAL_SYSTEM.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/03_CHAT_AND_COMPOSER.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/04_SIDEBAR_AND_NAVIGATION.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/05_WORK_PROJECTS_PERMISSIONS.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/06_TRANSCRIPTION.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/07_TEAM_AND_AGENTS.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/08_DARK_LIGHT_READABILITY.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/09_ERROR_STATES.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/10_IMPLEMENTATION_OWNERSHIP.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/11_CONFLICT_MAP.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/12_ACCEPTANCE_CRITERIA.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/13_IMPLEMENTATION_DEPENDENCIES.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/14_SCREENSHOT_REVIEW_INDEX.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/15_SEMANTICS_FLAGS.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/16_PHASE4_DELTA.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6-visual-ux/17_R9_LANE_RECONCILIATION.md` | docs | 0ff061d 3050761 7267630 |
| `docs/v1.6-visual-ux/18_R9_EVIDENCE.md` | docs | 96979c7 7267630 |
| `docs/v1.6-visual-ux/19_R10_ENGINE_LOSS_EVIDENCE.md` | docs | bc92f7f 7267630 |
| `docs/v1.6-visual-ux/AUTO_RESUME.md` | docs | 04151c8 3050761 7267630 |
| `docs/v1.6/AUTONOMOUS_OPERATION.md` | docs | 3050761 |
| `docs/v1.6/AUTO_RESUME.md` | docs | c4ae724 5127bac 785df71 ac5e2a2 16de55f 006159a 6ea68c2 fed59dd 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 9eab3c6 756218e 4440a90 eea6503 e8bbb05 3050761 08f5667 |
| `docs/v1.6/KEL_CANONICAL_ROADMAP_R2_5.md` | docs | 9eab3c6 3050761 |
| `docs/v1.6/MARATHON_STATE.md` | docs | 4440a90 eea6503 e8bbb05 0aadd42 3050761 1972b68 7267630 12f87a7 08f5667 |
| `docs/v1.6/PRE_AUDIT_RELEASE_CANDIDATE.md` | docs | 08f5667 |
| `docs/v1.6/branding/CANONICAL_LOGO.md` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/README.md` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/about-screen-kel-logo.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/exe-icon-extracted-previous-package.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/exe-icon-extracted.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/installer-icon-extracted.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/packaged-boot.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/branding/evidence/packaged-landing.png` | docs | 1894ef7 3050761 |
| `docs/v1.6/phase10/PROVIDER_VALIDATION.md` | docs | fed59dd 3050761 |
| `docs/v1.6/phase11/RUST_FRESHNESS_RECHECK.md` | docs | fed59dd 3050761 |
| `docs/v1.6/phase5/5.0_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.1_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.2_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.3_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.4_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.5_IMPLEMENTATION_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase5/5.6_IMPLEMENTATION_RECORD.md` | docs | c4ae724 5127bac 3050761 |
| `docs/v1.6/phase5/5.7_DECISION_DEFERRED.md` | docs | 5127bac 3050761 |
| `docs/v1.6/phase5/5.8_DECISION_DEFERRED.md` | docs | 5127bac 3050761 |
| `docs/v1.6/phase5/READING_RECORD.md` | docs | 3050761 |
| `docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md` | docs | ac5e2a2 3050761 |
| `docs/v1.6/phase7/CAPABILITY_RECOMMENDATIONS.md` | docs | 16de55f 3050761 |
| `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md` | docs | 006159a 3050761 |
| `docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md` | docs | 6ea68c2 3050761 |
| `docs/v1.6/pre-audit/AUDIT_HANDOFF.md` | docs | 785df71 05608e6 3050761 08f5667 |
| `docs/v1.6/pre-audit/AUDIT_SCOPE.md` | docs | 785df71 3050761 08f5667 |
| `docs/v1.6/pre-audit/AUDIT_TARGETS.md` | docs | 785df71 ac5e2a2 16de55f 6ea68c2 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 9eab3c6 3050761 93b7074 7267630 |
| `docs/v1.6/pre-audit/CHANGE_LEDGER.md` | docs | 785df71 ac5e2a2 16de55f 006159a 6ea68c2 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 756218e 4440a90 eea6503 e8bbb05 0aadd42 3050761 12f87a7 |
| `docs/v1.6/pre-audit/COMMIT_LEDGER.md` | docs | 785df71 ac5e2a2 16de55f fa31618 24d775b edd50de 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 756218e 4440a90 eea6503 e8bbb05 0aadd42 3050761 12f87a7 |
| `docs/v1.6/pre-audit/DEFERRED_ITEMS.md` | docs | 785df71 ac5e2a2 16de55f 006159a fed59dd 9eab3c6 3050761 08f5667 |
| `docs/v1.6/pre-audit/FINAL_STATE_MATRIX.md` | docs | 785df71 3050761 08f5667 |
| `docs/v1.6/pre-audit/INVARIANT_LEDGER.md` | docs | 785df71 16de55f 9eab3c6 eea6503 e8bbb05 0aadd42 3050761 |
| `docs/v1.6/pre-audit/KNOWN_LIMITATIONS.md` | docs | 785df71 ac5e2a2 16de55f 3050761 08f5667 |
| `docs/v1.6/pre-audit/MIGRATION_LEDGER.md` | docs | 785df71 3050761 08f5667 |
| `docs/v1.6/pre-audit/P2_P3_DISPOSITION.md` | docs | 785df71 ac5e2a2 c1bb980 cbd0430 a3e272d 11e1525 ae4c5b0 756218e 4440a90 0aadd42 05608e6 3050761 |
| `docs/v1.6/pre-audit/PACKAGED_EVIDENCE_INDEX.md` | docs | 785df71 7b32217 1894ef7 3050761 08f5667 |
| `docs/v1.6/pre-audit/PROVIDER_VALIDATION_MATRIX.md` | docs | 785df71 fed59dd 3050761 08f5667 |
| `docs/v1.6/pre-audit/README.md` | docs | 785df71 9eab3c6 3050761 |
| `docs/v1.6/pre-audit/REPAIR_HINTS.md` | docs | 785df71 ac5e2a2 3050761 08f5667 |
| `docs/v1.6/pre-audit/REQUIREMENTS_TRACEABILITY.md` | docs | 785df71 ac5e2a2 16de55f 006159a 6ea68c2 fed59dd 1894ef7 a7c7aa4 820ee3e c1bb980 cbd0430 a3e272d 11e1525 ae4c5b0 9eab3c6 756218e 4440a90 eea6503 e8bbb05 0aadd42 05608e6 3050761 12f87a7 |
| `docs/v1.6/pre-audit/RISK_REGISTER.md` | docs | 785df71 9eab3c6 3050761 08f5667 |
| `docs/v1.6/pre-audit/TEST_EVIDENCE_INDEX.md` | docs | 785df71 ac5e2a2 16de55f fed59dd 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 756218e 4440a90 eea6503 e8bbb05 0aadd42 3050761 08f5667 |
| `docs/v1.6/pre-audit/VISUAL_EVIDENCE_INDEX.md` | docs | 785df71 ac5e2a2 1894ef7 3050761 12f87a7 |
| `docs/v1.6/pre-audit/evidence/campaign-a-baseline/engine-suite-20260918.txt` | docs | 785df71 3050761 |
| `docs/v1.6/pre-audit/evidence/campaign-a-baseline/reconciliation.md` | docs | 785df71 3050761 |
| `docs/v1.6/pre-audit/evidence/campaign-a-baseline/remote-refs.txt` | docs | 785df71 3050761 |
| `docs/v1.6/pre-audit/increments/A1-ENGINE-VERSION-BINDING.md` | docs | 11e1525 3050761 |
| `docs/v1.6/pre-audit/increments/INIT-CAMPAIGN-A.md` | docs | 785df71 3050761 |
| `docs/v1.6/pre-audit/increments/LOGO-CANONICAL.md` | docs | 1894ef7 3050761 |
| `docs/v1.6/pre-audit/increments/P2P3-BATCH2-IPC-HEADER-BACKUP.md` | docs | a3e272d 3050761 |
| `docs/v1.6/pre-audit/increments/P2P3-BATCH3-SNAPSHOTS-SCOPE.md` | docs | ae4c5b0 3050761 |
| `docs/v1.6/pre-audit/increments/PER-02-RESTORE-VISIBILITY.md` | docs | cbd0430 3050761 |
| `docs/v1.6/pre-audit/increments/PHASE6-MEMORY-REALITY.md` | docs | ac5e2a2 3050761 |
| `docs/v1.6/pre-audit/increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | docs | 16de55f 3050761 |
| `docs/v1.6/pre-audit/increments/R0-APR02-APPROVAL-SCOPE.md` | docs | 756218e 3050761 |
| `docs/v1.6/pre-audit/increments/R0-SWEEP.md` | docs | 4440a90 05608e6 3050761 |
| `docs/v1.6/pre-audit/increments/R1-AUTHORITY-CEILING.md` | docs | eea6503 3050761 |
| `docs/v1.6/pre-audit/increments/R11-INTEGRATION.md` | docs | 12f87a7 |
| `docs/v1.6/pre-audit/increments/R2-IDEMPOTENCY-MATRIX.md` | docs | e8bbb05 3050761 |
| `docs/v1.6/pre-audit/increments/R3-RETRY-DURABILITY.md` | docs | 1a9f538 3050761 |
| `docs/v1.6/pre-audit/increments/R4-APPROVAL-EXACT.md` | docs | e8bbb05 3050761 |
| `docs/v1.6/pre-audit/increments/R5-PERSISTENCE-INTEGRITY.md` | docs | e8bbb05 3050761 |
| `docs/v1.6/pre-audit/increments/R6-TRUTHFUL-STATE.md` | docs | e8bbb05 3050761 |
| `docs/v1.6/pre-audit/increments/R7-CREDENTIAL-BOUNDARY.md` | docs | 0aadd42 3050761 |
| `docs/v1.6/pre-audit/increments/R8-PACKAGE-ASSERTIONS.md` | docs | 0aadd42 3050761 |
| `docs/v1.6/pre-audit/increments/REQ-F4-REAL-ARTIFACT-BINDING.md` | docs | 820ee3e 3050761 |
| `docs/v1.6/pre-audit/increments/REQ-RK-RESOLUTION-KIND.md` | docs | a7c7aa4 3050761 |
| `docs/v1.6/status/MAIN_STATUS.md` | docs | c4ae724 5127bac fd98cc4 785df71 ac5e2a2 16de55f 7b32217 006159a 6ea68c2 fed59dd 24d775b 1894ef7 a7c7aa4 820ee3e cbd0430 a3e272d 11e1525 ae4c5b0 9eab3c6 756218e 4440a90 eea6503 e8bbb05 0aadd42 3050761 1972b68 7267630 12f87a7 08f5667 |
| `runtime/kel/__init__.py` | engine | 93b99b5 3050761 |
| `runtime/kel/appserver.py` | engine | b6c4eff 3050761 |
| `runtime/kel/assignment.py` | engine | dc65fbc 2468b16 3050761 |
| `runtime/kel/assurance.py` | engine | a547936 3050761 |
| `runtime/kel/authorize.py` | engine | 8c899c8 3050761 |
| `runtime/kel/backup.py` | engine | df1997a 0596211 84b5646 3050761 |
| `runtime/kel/capabilities.py` | engine | df87903 3050761 |
| `runtime/kel/chat_approvals.py` | engine | 8a677d0 dd34ac2 3050761 |
| `runtime/kel/coding.py` | engine | df87903 b6c4eff 3050761 |
| `runtime/kel/contracts.py` | engine | dc65fbc 3050761 |
| `runtime/kel/core.py` | engine | df87903 081a6ef fde5bbb b2ffed1 3050761 |
| `runtime/kel/delegation.py` | engine | 081a6ef dc65fbc 3050761 |
| `runtime/kel/evaluation.py` | engine | 081a6ef 3050761 |
| `runtime/kel/evidence.py` | engine | 3050761 |
| `runtime/kel/internal.py` | engine | b6c4eff 3050761 |
| `runtime/kel/learning.py` | engine | 3050761 |
| `runtime/kel/memory.py` | engine | 3050761 |
| `runtime/kel/messages.py` | engine | 3050761 |
| `runtime/kel/parallel.py` | engine | 3050761 |
| `runtime/kel/pods.py` | engine | dc65fbc 3050761 |
| `runtime/kel/research.py` | engine | df87903 3050761 |
| `runtime/kel/service.py` | engine | df1997a 8a677d0 49e528e 8ab7699 5950efb b2ffed1 93b99b5 3050761 |
| `runtime/kel/staffing.py` | engine | 3050761 |
| `runtime/kel/team.py` | engine | 3050761 |
| `runtime/kel/transcription.py` | engine | 0596211 8ab7699 3050761 |
| `runtime/kel/vetting_session.py` | engine | 49e528e 3050761 |
| `runtime/kel/workforce.py` | engine | a547936 dc65fbc 3050761 |
| `.gitignore` | meta | 785df71 3050761 |
| `desktop/tests/unit/capability-recommendation.test.ts` | test | df87903 3050761 |
| `desktop/tests/unit/conversation-leading-mark.test.ts` | test | ac85eb3 3050761 7267630 |
| `desktop/tests/unit/engine-failure.test.ts` | test | 2897207 7267630 |
| `desktop/tests/unit/engine-health.test.ts` | test | 2897207 7267630 |
| `desktop/tests/unit/kelEngineVersion.test.ts` | test | 101d8c3 3050761 |
| `desktop/tests/unit/memory-record-actions.test.ts` | test | 22f4a3e 3050761 |
| `desktop/tests/unit/needs-attention.test.ts` | test | 938dc9b 7267630 |
| `runtime/tests/test_capabilities.py` | test | df87903 3050761 |
| `runtime/tests/test_transcription.py` | test | 8ab7699 3050761 |
| `runtime/tests/test_v141_boundaries.py` | test | 022f3ac 3050761 |
| `runtime/tests/test_v16_approvals.py` | test | 8a677d0 3050761 |
| `runtime/tests/test_v16_r1_authority.py` | test | dc65fbc 3050761 |
| `runtime/tests/test_v16_r2_idempotency.py` | test | fde5bbb 3050761 |
| `runtime/tests/test_v16_r3_retry_durability.py` | test | 1a9f538 3050761 |
| `runtime/tests/test_v16_r4_approval_exact.py` | test | 8c899c8 3050761 |
| `runtime/tests/test_v16_r5_persistence.py` | test | b2ffed1 3050761 |
| `runtime/tests/test_v16_r6_liveness.py` | test | e8bbb05 3050761 |
| `runtime/tests/test_v16_r7_credentials.py` | test | b6c4eff 3050761 |
| `runtime/tests/test_v16_r8_identity.py` | test | 93b99b5 3050761 |
| `runtime/tests/test_v16_r8_migrations.py` | test | 2468b16 3050761 |
| `runtime/tests/test_v16_resolution_kind.py` | test | a547936 3050761 |
| `runtime/tests/test_v16_restore_visibility.py` | test | df1997a 3050761 |
| `runtime/tests/test_v16_sweep_fixes.py` | test | 0596211 84b5646 5950efb dd34ac2 3050761 |
| `runtime/tests/test_vetting.py` | test | 49e528e 3050761 |
| `runtime/tests/test_workforce_assignment.py` | test | 3050761 |
| `runtime/tests/test_workforce_assurance.py` | test | 3050761 |
| `runtime/tests/test_workforce_d1.py` | test | 081a6ef 3050761 |
| `runtime/tests/test_workforce_d2.py` | test | 081a6ef 3050761 |
| `runtime/tests/test_workforce_learning.py` | test | 3050761 |
| `runtime/tests/test_workforce_parallel.py` | test | 3050761 |
| `runtime/tests/test_workforce_schemas.py` | test | a547936 3050761 |
| `runtime/tests/workforce_fixtures.py` | test | 3050761 |
| `scripts/freeze-release.ps1` | tooling | 93b99b5 3050761 |
| `scripts/make-brand-assets.py` | tooling | 71c78f0 3050761 |
| `scripts/validate-freeze.ps1` | tooling | 93b99b5 3050761 |
| `scripts/verify-brand-render.py` | tooling | 71c78f0 3050761 |
