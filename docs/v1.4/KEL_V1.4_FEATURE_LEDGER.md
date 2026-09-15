# KEL V1.4 — FEATURE LEDGER (200 items)

Status: v0.1 (Gate 0) · Initial triage complete for all 200 items; evidence columns fill as gates run.

**How to read this file**

- Statuses are **initial triage** from (a) verified V1.3 docs (`docs/v1.3/`) and (b) source scans run
  this session (cited as `scan:G0` with a concrete file or grep fact). Statuses are re-verified at
  each gate and progress `ALREADY_PRESENT | EXTEND | NEW → IMPLEMENTED → VERIFIED`.
- Every item carries: ID, feature, source, current-state triage, owning subsystem, visual impact
  (Vis), interaction impact (Int), and evidence/notes. Per-item code files, tests, packaged and
  screenshot evidence are appended as each gate closes them.
- Nothing may silently disappear; deferrals require reason + evidence + follow-up release.
- IDs `V14-001…V14-200` map 1:1 to the brief's numbered features.

**Status legend:** `ALREADY_PRESENT` (working today; V1.4 only needs verification + polish) ·
`EXTEND` (real foundation exists; V1.4 extends it) · `NEW` (not present; build in V1.4) ·
`IMPLEMENTED` / `VERIFIED` (post-implementation states) · `DEFERRED` / `BLOCKED` (require written rationale).

## A. Solution quality, ideation, and autonomous execution (V14-001…018)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-001 | Outcome brief before planning | Orkas + Kel | NEW | runtime:solution | M | H | No solution-brief model in runtime (`scan:G0`); lands with G3 |
| V14-002 | Assumption challenge | Orkas + Pioneer | NEW | runtime:solution | L | M | Part of solution brief; G3 |
| V14-003 | Alternative generation | Orkas | NEW | runtime:solution | L | M | G3 |
| V14-004 | Existing-solution search record | donor-audit method | NEW | runtime:solution | L | M | G3 |
| V14-005 | Donor and library scan record | Kel donor process | NEW | runtime:solution | L | L | Process exists in docs; product record is new |
| V14-006 | Capability opportunity check | user req | NEW | runtime:solution | L | M | G3 |
| V14-007 | Better-with-access card | user req | NEW | shell:solution | M | H | UI for opportunity; G3/G4 |
| V14-008 | Fallback plan | Agent Orchestrator | NEW | runtime:solution | L | M | G3 |
| V14-009 | Decision criteria | Conductor | NEW | runtime:solution | L | M | G3 |
| V14-010 | Tradeoff comparison | Orkas + review | NEW | runtime:solution | M | M | G3 |
| V14-011 | Optimal-enough review | Pioneer + user req | EXTEND | runtime:solution + relay | L | M | Reviewer relay + `KEL_REVIEWER` wiring exist (`scan:G0`); productize solution-review gate in G3 |
| V14-012 | Wrong-layer detector | Kel audit exp | NEW | runtime:solution | L | M | G3 |
| V14-013 | Workaround-vs-root-fix label | Forge ideas + Kel | NEW | runtime:solution | L | M | Ideas-only donor; G3 |
| V14-014 | Rework forecast | Agent Orchestrator | NEW | runtime:solution | L | L | G3 |
| V14-015 | User-idea evaluator | user req | NEW | runtime:solution | L | M | G3 |
| V14-016 | Evidence-to-switch rule | Pioneer | NEW | runtime:solution | L | L | G3 |
| V14-017 | Reviewed-plan autonomy | autonomy model | NEW | runtime:solution | L | H | Policy + enforcement new; G2/G3 |
| V14-018 | Consequential-action receipt | Agent Orchestrator | NEW | runtime:solution | M | M | G3 |

## B. Team, Office, Roster, Studio (V14-019…040)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-019 | Optional Team workspace | Aion, reinterpreted | NEW | shell:team | H | H | Donor has `pages/team/TeamPage.tsx` (Aion team UI) — assess/replace (`scan:G0`) |
| V14-020 | Live Office view | Aion + CEO model | NEW | shell+engine:team | H | H | No office/assignment model (`scan:G0` grep) |
| V14-021 | Specialist Roster | Aion assistants + Kel | NEW | runtime:team | H | M | G3/G4 |
| V14-022 | Agent Studio | Aion agent settings | NEW | shell:team | H | H | G4 |
| V14-023 | Department grouping | Kel synthesis | NEW | runtime:team | M | M | G4 |
| V14-024 | Specialist cards (role/model/state/tools/budget) | Aion + XOPC | NEW | shell:team | H | M | G4 |
| V14-025 | Staffing-plan preview | Orkas + Team | NEW | shell:team | H | H | G4 |
| V14-026 | Why-this-specialist explanation | Orkas | NEW | shell+engine:team | M | M | G4 |
| V14-027 | Current-assignment brief | XOPC | NEW | runtime:team | M | M | G4 |
| V14-028 | Meaningful activity timeline | Agent Orchestrator | NEW | runtime:team | M | H | Assignment activity events new; G4 |
| V14-029 | Artifact/evidence drawer | Aion + Pioneer | EXTEND | shell:work | M | H | Milestone artifact API exists (`/api/artifact`, `scan:G0`); per-specialist view new |
| V14-030 | Foundational-instructions viewer | user req | NEW | shell:team | M | M | G4 |
| V14-031 | Structured role-definition editor | Kel roles | NEW | shell:team | H | H | G4 |
| V14-032 | Global role defaults | Hermes scoping | NEW | runtime:team | L | M | G3 |
| V14-033 | Project role overrides | Hermes | NEW | runtime:team | M | M | G3 |
| V14-034 | Task-specific role overrides | XOPC | NEW | runtime:team | M | M | G3 |
| V14-035 | Role version history | Conductor | NEW | runtime:team | L | M | G3 |
| V14-036 | Instruction diff and rollback | Conductor | NEW | shell:team | M | H | G4 |
| V14-037 | Editable-vs-locked instruction sections | guardrail model | NEW | shell:team | M | M | G3/G4 |
| V14-038 | Model preference per role | Ryder + Kel | NEW | runtime:team | L | M | G3 |
| V14-039 | Tool policy per role | XOPC | NEW | runtime:team | L | M | G3 |
| V14-040 | Budget controls per role | XOPC + Goose | NEW | runtime:team | L | M | G3 |

## C. Work Center, progress, execution visibility (V14-041…062)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-041 | Unified Work Center | Aion + Warpforge | EXTEND | shell:work | H | H | Work drawer + `/api/work` exist (`scan:G0`); unify + redesign |
| V14-042 | Human-readable task states | Agent Orchestrator | EXTEND | runtime:work | M | M | Job states exist; copy/state model review |
| V14-043 | Task timeline | Agent Orchestrator | EXTEND | shell+engine:work | M | M | Milestone reports exist; timeline view new |
| V14-044 | Current-step emphasis | Chuzom | EXTEND | shell:work | M | M | G4 |
| V14-045 | Milestone list | Chuzom + Contracts | ALREADY_PRESENT | runtime:work | M | M | `/api/work` returns milestones; verified UI in V1.3 |
| V14-046 | Frozen accepted steps | Chuzom | EXTEND | runtime:work | M | M | Acceptance exists; freeze semantics verify in G4 |
| V14-047 | Repair-only indicator | Chuzom | EXTEND | runtime:work | M | M | `/api/retry` exists (`scan:G0`); semantics verify |
| V14-048 | One job, one updating card | Aion + Kel dedup | EXTEND | shell:work | M | M | Verify no duplicate cards; G4 |
| V14-049 | Compact activity feed | Agent Orchestrator | EXTEND | shell:work | M | M | G4 |
| V14-050 | Background-work indicator | Warpforge | EXTEND | shell:work | M | M | Engine keeps work alive (README); surface in UI |
| V14-051 | Inline task controls | Aion Work drawer | ALREADY_PRESENT | shell:work | L | M | Pause/resume/cancel/apply buttons in `KelWorkPanel.tsx` (`scan:G0`) |
| V14-052 | Work search and filters | Aion history | NEW | shell:work | M | M | No filters observed (`scan:G0`) |
| V14-053 | Recent / archived / scheduled views | Aion nav | EXTEND | shell:work | M | M | Cron page + archived settings exist (`scan:G0`) |
| V14-054 | Recovery banner | Warpforge + AO | EXTEND | shell:work | M | M | Recovery engines exist; banner UI G4 |
| V14-055 | Parent-child work map | Warpforge + Orkas | NEW | shell:work | M | M | G4 |
| V14-056 | Artifacts drawer | Aion | EXTEND | shell:work | M | M | Artifact endpoint exists; drawer polish G4 |
| V14-057 | Applied-vs-not-applied state | Kel effects + Aion | EXTEND | shell:work | M | M | `/api/apply` + `apply_changes.py` exist (`scan:G0`); state display G4 |
| V14-058 | Project / repository scope chip | capability leases | EXTEND | shell:work | L | M | Project context exists; chip is new UI |
| V14-059 | Task budget meter | XOPC | NEW | shell:work | M | M | No budget model (`scan:G0`); G3/G4 |
| V14-060 | Wait-reason panel | AO + Kel B2 | EXTEND | shell:work | M | M | Verify state payload reasons; G4 |
| V14-061 | Retry and escalation history | Chuzom | EXTEND | shell:work | L | M | Retry exists; history view G4 |
| V14-062 | Stall detection display | Forge ideas only | NEW | shell+engine:work | M | M | G4 |

## D. Project memory, context, understanding (V14-063…082)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-063 | Project Knowledge panel | Hermes | ALREADY_PRESENT | shell:work | M | M | Knowledge tab live in V1.3 (`KelWorkPanel.tsx`) |
| V14-064 | Memory recall indicator | Hermes | EXTEND | shell:work | M | M | Composer reasons exist; surface recall in UI |
| V14-065 | Memory-type badges | Pioneer + V1.3 | EXTEND | shell:work | L | L | Memory kinds exist; badge verify |
| V14-066 | Trust-level badges | Pioneer | EXTEND | shell:work | L | L | Trust levels exist (`docs/v1.3` MEM-*); badge verify |
| V14-067 | Memory source links | Hermes | EXTEND | shell:work | L | L | `source_ref` exists; link UI verify |
| V14-068 | Confirm proposed memory | Pioneer + Hermes | ALREADY_PRESENT | shell:work | L | M | Confirm action in panel (`scan:G0`) |
| V14-069 | Edit memory | Hermes | ALREADY_PRESENT | shell:work | L | M | `correct` action (`scan:G0`) |
| V14-070 | Retract memory | AO | ALREADY_PRESENT | shell:work | L | M | Retract button (`scan:G0`) |
| V14-071 | Forget memory | Hermes | ALREADY_PRESENT | shell:work | L | M | Forget button (`scan:G0`) |
| V14-072 | Conflict resolver | Pioneer | ALREADY_PRESENT | shell:work | M | M | `resolve_conflict` a/b/dismiss UI (`scan:G0`) |
| V14-073 | Superseded-history view | AO | EXTEND | shell:work | L | L | `history()` engine-side; UI verify |
| V14-074 | Stale-memory warning | AO invalidation | EXTEND | shell:work | L | L | `revalidate→stale` exists (MEM-10); UI warning verify |
| V14-075 | Project-isolation indicator | Hermes | EXTEND | shell:work | L | L | Isolation enforced (MEM-07); indicator new |
| V14-076 | Project Map | Hermes + AO | ALREADY_PRESENT | shell:work | M | M | Map tab live in V1.3 |
| V14-077 | Map freshness | AO | EXTEND | shell:work | L | L | Versions/timestamps exist; freshness UI verify |
| V14-078 | Manual map refresh | AO | ALREADY_PRESENT | shell:work | L | L | Refresh button + MAP-05 pass (V1.3) |
| V14-079 | Incremental map refresh | AO | ALREADY_PRESENT | runtime:memory | L | L | MAP-03 incremental copy-forward |
| V14-080 | Context preview | Hermes + Orkas | EXTEND | shell:work | M | M | Composer exists; preview surface G5 |
| V14-081 | Why-included details | Hermes | EXTEND | shell:work | M | M | `sources[].reason` exists; UI surfacing G5 |
| V14-082 | Context size / source-mix indicator | Orkas + XOPC | EXTEND | shell:work | L | L | `context_packets` metrics exist; indicator new |

### E. Continuation and recovery (V14-083 … V14-096)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-083 | Continue last task | Warpforge | ALREADY_PRESENT | runtime:continuation | L | H | "Continue work" tab (V1.3) |
| V14-084 | Continuation chooser | Warpforge + V1.3 | ALREADY_PRESENT | runtime:continuation | L | M | `kind=choice` (CONT-08) |
| V14-085 | Resume summary | Chuzom + Warpforge | EXTEND | shell:work | M | M | Resume info exists; summary UI to verify/polish |
| V14-086 | New-chat continuation | Warpforge | ALREADY_PRESENT | runtime:continuation | L | M | CONT-02 |
| V14-087 | Exact provider-session resume display | Ryder | EXTEND | shell:work | L | M | Session reuse engine-side (CONT-03); display state |
| V14-088 | Bounded fallback handoff | Ryder + Warpforge | ALREADY_PRESENT | runtime:continuation | L | M | CONT-04 |
| V14-089 | Source-changed warning | Forge ideas | ALREADY_PRESENT | runtime:continuation | M | M | CONT-07 |
| V14-090 | Affected-only revalidation | Chuzom + V1.3 | ALREADY_PRESENT | runtime:continuation | M | M | CONT-07 |
| V14-091 | Wrong-project block | Warpforge | ALREADY_PRESENT | runtime:continuation | M | M | CONT-09 |
| V14-092 | Pause instead of replay | Warpforge | ALREADY_PRESENT | runtime:work | L | M | `/api/control` pause; semantics verify |
| V14-093 | Approval survives restart | CoPaw + Kel | ALREADY_PRESENT | runtime:store | M | H | CONT-11 + packaged badge evidence |
| V14-094 | Continuation history | Warpforge + AO | EXTEND | shell:work | L | M | `job_links` exist; history view |
| V14-095 | Idempotent resume | Agent Orchestrator | ALREADY_PRESENT | runtime:engine | L | M | CONT-01 settles once |
| V14-096 | Recovered-work banner | Warpforge | EXTEND | shell:work | M | M | Recovery exists; banner new |

### F. Verification, review, and trust (V14-097 … V14-118)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-097 | What-done-means panel | Conductor + CC | EXTEND | runtime:verify + shell | M | M | Completion/verification engine-side; surface criteria |
| V14-098 | Worker-finished vs Kel-verified distinction | Pioneer + Forge | EXTEND | shell:work | H | H | Engine verifies before reporting (README); make distinct in UI |
| V14-099 | Verification summary card | Forge + Chuzom | EXTEND | shell:work | H | M | Verification records exist; card UI |
| V14-100 | Evidence viewer | Pioneer + Aion | EXTEND | shell:work | M | M | Evidence/artifacts exist (`/api/artifact`); viewer UX |
| V14-101 | Planner/executor/reviewer provenance | Pioneer + Kel | EXTEND | runtime:verify | M | M | B3 provenance (`test_b3_provenance.py`) |
| V14-102 | Reviewer-independence indicator | Pioneer + Kel | EXTEND | runtime:verify | M | M | Reviewer diversity (V1.2 tests); surface result |
| V14-103 | Evidence-freshness warning | Forge | EXTEND | runtime:verify | M | M | Staleness concepts exist; warning verify |
| V14-104 | Failed-check details | Chuzom | EXTEND | shell:work | M | M | Failure surfacing exists (`test_failure_surfacing.py`); UI details |
| V14-105 | Flaky-test indicator | Chuzom | NEW | runtime:verify | L | M | None found (triage; verify) |
| V14-106 | Verified/Uncertain/Failed states | Forge + Kel | EXTEND | runtime + shell | H | H | States exist engine-side; full UI states |
| V14-107 | Why-uncertain explanation | Forge + cap-opp | EXTEND | shell:work | M | M | Uncertainty notes exist; surface |
| V14-108 | Review-disagreement repair loop | Pioneer + Chuzom | EXTEND | runtime:verify | M | H | Review recovery exists; loop UX |
| V14-109 | Verification history | Forge + AO | EXTEND | shell:work | L | M | History records; view |
| V14-110 | Apply-and-backup state | Aion + Kel | EXTEND | runtime:apply | M | M | `apply_changes.py` + backups; state display |
| V14-111 | Requirements coverage matrix | Conductor | NEW | shell:work | M | M | None found (triage; verify) |
| V14-112 | Pre-run verification plan | CC + BSG | EXTEND | runtime:verify | M | M | Plan data partial; formalize |
| V14-113 | Reviewer-rubric viewer | Pioneer | NEW | shell:verify | L | M | None found |
| V14-114 | Solution-quality review | user + Pioneer | NEW | runtime:solution | M | H | Depends on A-block (G3) |
| V14-115 | Self-review-prohibition notice | Pioneer | EXTEND | runtime:verify | L | L | Relay rules exist (dev process); productize |
| V14-116 | Evidence-class labels | Pioneer | EXTEND | shell:work | L | M | Evidence classes engine-side |
| V14-117 | Source-digest/version coverage | Forge + Conductor | EXTEND | runtime:verify | L | M | Digests exist |
| V14-118 | Final completion receipt | AO + user | EXTEND | shell:work | M | M | Completion data exists; receipt UX |

### G. Providers, API keys, models, quota, and readiness (V14-119 … V14-136)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-119 | Provider Setup screen | Aion + Ryder | EXTEND | shell:settings | H | H | Donor provider settings exist; Kel redesign + Kel provider set |
| V14-120 | Subscription-vs-API explanation | Ryder + billing | NEW | shell:settings | M | M | Product copy; lands G6 |
| V14-121 | Secure credential storage | Kel security | EXTEND | runtime:security | L | H | Key storage in shell today; security model + review required (G6) |
| V14-122 | Test connection | Ryder probes | EXTEND | shell:settings | L | M | Protocol detection/probe code exists; surface |
| V14-123 | Installed status | Ryder | EXTEND | runtime:provider | L | M | CLI detection exists; formalize states |
| V14-124 | Authenticated status | Ryder | EXTEND | runtime:provider | L | M | Auth state partial; formalize |
| V14-125 | Health status | AO + Kel circuits | NEW | runtime:provider | L | M | Circuit/health model new |
| V14-126 | Quota and reset | Ryder | NEW | runtime:provider | L | M | None found |
| V14-127 | Unknown/not-reported states | Ryder | NEW | shell:settings | M | L | Define + display |
| V14-128 | Role-based model preferences | Orkas + Kel | NEW | runtime:team | L | M | Depends on Team model (G3) |
| V14-129 | Automatic fallback policy | Ryder + Kel | EXTEND | runtime:router | L | M | Router exists; policy + UI |
| V14-130 | Fallback explanation | Ryder + Kel | NEW | shell:work | M | M | Surface reason copy |
| V14-131 | Exact-session status | Ryder | EXTEND | runtime:provider | L | M | Sessions exist; display |
| V14-132 | Task cost/time/token budget | XOPC | NEW | runtime:work | M | M | Budgets new (G4) |
| V14-133 | Provider readiness preflight | AO | NEW | runtime:provider | M | M | New |
| V14-134 | Capability matrix | Ryder | NEW | shell:settings | M | M | New |
| V14-135 | Usage history | Ryder + Kel | NEW | shell:statistics | L | M | New |
| V14-136 | DeepSeek first-class provider | Ryder → Kel | EXTEND | runtime:provider + shell | M | M | Donor already lists DeepSeek (`modelPlatforms.ts`, `protocolDetector.ts`); needs Kel-grade setup/health/tests |

### H. Broad autonomy, rare approvals, and immutable guardrails (V14-137 … V14-153)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-137 | Autonomy profile | user | NEW | runtime:autonomy | M | H | Lands G6 |
| V14-138 | Task capability lease | user + Goose | NEW | runtime:autonomy | M | H | Broker lease ≠ capability lease; G6 |
| V14-139 | Folder-scope viewer | user | NEW | shell:autonomy | M | M | G6 |
| V14-140 | Repository-scope viewer | user | NEW | shell:autonomy | M | M | G6 |
| V14-141 | Browser-domain scope | user + CoPaw | NEW | shell:autonomy | M | M | G6 |
| V14-142 | Routine execution after review | Best Solution Gate | NEW | runtime:autonomy | L | H | G6 |
| V14-143 | Boundary-expansion approval only | user | NEW | runtime:autonomy | M | H | G6 |
| V14-144 | Approval Inbox | Aion + CoPaw | EXTEND | shell:work | M | H | Approvals exist (badge + CONT-11); inbox view |
| V14-145 | Plain-language expansion summary | CoPaw + BWA | NEW | shell:approval | M | M | Copy layer |
| V14-146 | Allow once / allow for project | Goose | EXTEND | runtime:approval | M | M | Allow exists; scoped grants NEW |
| V14-147 | Permission expiry and revoke | Goose | EXTEND | runtime:approval | L | M | `/api/revoke` exists; expiry NEW |
| V14-148 | Outside-project warning | CoPaw | NEW | shell:approval | M | M | New |
| V14-149 | Destructive-action warning | Chuzom + CoPaw | NEW | shell:approval | M | M | New |
| V14-150 | Frozen-release lock | Kel discipline | NEW | runtime:policy | L | M | Repository discipline exists; technical lock new |
| V14-151 | No-screen-takeover enforcement | user guardrail | NEW | runtime:policy | L | L | Technical enforcement new |
| V14-152 | Firefox-only browser rule | user guardrail | NEW | runtime:policy | L | L | Technical enforcement new |
| V14-153 | Locked-system-red-line status | user + Goose/XOPC | NEW | shell:settings | M | M | New |

### I. Recipes and repeatable workflows (V14-154 … V14-166)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-154 | Recipe Library | Conductor + V1.3 | ALREADY_PRESENT | shell:work | M | M | Recipes tab + 5 builtins (V1.3) |
| V14-155 | Recipe preview | Conductor | EXTEND | shell:work | M | M | Preview UI to verify/polish |
| V14-156 | Required-input checklist | Conductor | EXTEND | shell:work | M | M | Schema inputs exist; checklist UI |
| V14-157 | Permission preview | Conductor + XOPC | NEW | shell:work | M | M | Depends on capability model (G6) |
| V14-158 | Step progress | Chuzom | EXTEND | shell:work | M | M | Run state exists; progress UX |
| V14-159 | Frozen completed steps | Chuzom | EXTEND | runtime:recipes | M | M | Freeze semantics verify; UI |
| V14-160 | Retry/escalation display | Chuzom | EXTEND | shell:work | M | M | Retry exists; display |
| V14-161 | Resume recipe | Warpforge + Conductor | EXTEND | runtime:recipes | M | M | Continuation integration; verify |
| V14-162 | Save successful work as recipe | Kel + Conductor | EXTEND | runtime:recipes | L | M | Verify existence; add confirm flow |
| V14-163 | Recipe versions | Conductor | ALREADY_PRESENT | runtime:recipes | L | L | Append-only versions (V1.3) |
| V14-164 | Explicit terminal states | Conductor + Kel | EXTEND | runtime:recipes | M | M | Verify + UI |
| V14-165 | Dry-run preview | Conductor | NEW | runtime:recipes | L | M | None found (triage; verify) |
| V14-166 | Project-local recipes | V1.3 architecture | ALREADY_PRESENT | runtime:recipes | L | L | Project scoping (V1.3) |

### J. Desktop experience, onboarding, search, and notifications (V14-167 … V14-183)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-167 | First-run setup | Aion + Ryder | EXTEND | shell:desktop | H | H | Donor onboarding/login exists; Kel flow + steps new |
| V14-168 | Global search | Aion | EXTEND | shell:search | M | H | Conversation search exists; global scope new |
| V14-169 | Command palette | Kel + Aion | NEW | shell:desktop | M | H | None found (triage; verify) |
| V14-170 | Tray quick actions | Aion | EXTEND | shell:tray | L | M | `tray.ts` exists; actions verify/polish |
| V14-171 | System notifications | Aion | EXTEND | shell:notify | M | M | Notification plumbing exists; restraint policy |
| V14-172 | Ambient pet status | Aion | ALREADY_PRESENT | shell:pet | M | M | Pet state machine + windows exist |
| V14-173 | Startup Health screen | Aion + AO | EXTEND | shell:desktop | M | M | Startup sequence exists; health screen new |
| V14-174 | Clean Settings organization | Aion | EXTEND | shell:settings | H | H | Regroup per brief §17 |
| V14-175 | Auto-update with release notes | Aion updater | ALREADY_PRESENT | shell:update | M | M | `autoUpdaterService` + update UI; release-notes wiring verify |
| V14-176 | Web companion | Aion WebUI/PWA | ALREADY_PRESENT | shell:web | M | M | `public/pwa` + `web-host`; packaged pwa assets |
| V14-177 | Single-instance behavior | Aion + V1.1 | ALREADY_PRESENT | shell + engine | L | L | `instance_lock.py` |
| V14-178 | Local/private indicator | Kel synthesis | NEW | shell:desktop | M | L | New |
| V14-179 | Excellent empty/loading/error states | Aion + AO | EXTEND | shell:all | H | H | Cross-cutting (G9) |
| V14-180 | Keyboard navigation | product quality | EXTEND | shell:all | L | H | Cross-cutting (G9) |
| V14-181 | Accessibility checks | UX standard | EXTEND | shell:all | M | H | Cross-cutting (G9) |
| V14-182 | Project switcher | Hermes + Aion | EXTEND | shell:desktop | M | H | Project selection exists; consolidated switcher |
| V14-183 | Consistent side-panel details | Aion | EXTEND | shell:layout | M | M | Unify drawer patterns |

### K. Diagnostics, maintenance, performance, and support (V14-184 … V14-200)

| ID | Feature | Source | Status | Subsystem | Vis | Int | Evidence / notes |
|---|---|---|---|---|---|---|---|
| V14-184 | Export Diagnostics | AO + Aion | EXTEND | shell:diag | M | M | Partial diagnostics; systematic export new |
| V14-185 | Health overview | AO | NEW | shell:diag | M | M | None found (triage; verify) |
| V14-186 | Crash-recovery explanation | Warpforge + AO | EXTEND | shell:diag | M | M | Recovery exists; explainer UI |
| V14-187 | Migration and backup receipt | AO + Kel | EXTEND | shell:diag | M | M | Receipts exist engine-side; surface |
| V14-188 | Sanitized logs | XOPC + Kel | EXTEND | runtime:diag | L | M | Logging exists; sanitization requirements |
| V14-189 | Process-ownership view | AO + CoPaw | EXTEND | runtime:diag | M | M | `windows_job.py`/runner own processes; view new |
| V14-190 | Data-retention controls | Hermes | NEW | shell:settings | M | M | New |
| V14-191 | Version and build details | Aion + Ryder | EXTEND | shell:about | L | L | About exists; extend details |
| V14-192 | Performance diagnostics | AO + Orkas | NEW | shell:diag | M | M | New |
| V14-193 | Startup timeline | Aion + AO | NEW | shell:diag | M | M | New (startup spans) |
| V14-194 | Provider-latency history | Ryder | NEW | shell:diag | M | M | New |
| V14-195 | Context-composition metrics | Orkas + V1.3 | EXTEND | runtime:context | L | M | Packet metrics + `tools/measure_context.py` |
| V14-196 | Memory-retrieval metrics | Hermes + V1.3 | EXTEND | runtime:memory | L | M | Partial; surface |
| V14-197 | Task cost/time metrics | Ryder + XOPC | NEW | shell:statistics | M | M | New |
| V14-198 | Orphan detector | AO + Kel | EXTEND | runtime:diag | M | M | Zero-orphan discipline exists; detector new |
| V14-199 | Database health and compaction | AO + Hermes | EXTEND | runtime:db | M | M | DB health basics; compaction tooling verify |
| V14-200 | Issue-report generator | Kel diagnostics | NEW | shell:diag | M | M | New (draft/local unless in scope) |

## Triage summary (initial)

Status counts (from the tables above): **ALREADY_PRESENT = 28 · EXTEND = 91 · NEW = 81** — 200 items total. `IMPLEMENTED` / `VERIFIED` / `DEFERRED` / `BLOCKED` populate as gates run; no item may be dropped (deferral requires the full justification block per brief §14).

Reading: V1.4 mostly **EXTENDS** V1.3 foundations (memory, continuation, recipes, verification, work panel), **ADDS** the Team organization, provider/credential and autonomy systems, diagnostics, and applies the complete visual redesign across all surfaces (brief §11).

