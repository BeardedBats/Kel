# KEL V2.0 — MARATHON DIRECTIVE (durable instruction set)

**How to use this file.** This is the authoritative instruction set for the V2.0 expansion marathon. It
is durable state: read it before doing anything, follow it exactly, and amend it only with a recorded
decision. Part A is the program directive exactly as Nick issued it (verbatim, section numbers kept).
Part B is the operational summary written at setup: lineage, paths, invariants and the machine-readable
phase state that a resume run needs first.

---

# PART A — PROGRAM DIRECTIVE (verbatim)

## KEL V2.0 — CREATE DEVELOPMENT LINE + DURABLE MARATHON DIRECTIVE

CURRENT AUTHORITATIVE BASELINE

Repository family:
C:\Users\Nick\Desktop\Kel

Current source:
C:\Users\Nick\Desktop\Kel\kel-daily-driver

Current branch:
dev/daily-driver

Authoritative V2.0 base commit:
a471e17ac25590369e74824ebed0dd7b54e4b00b

GitHub:
https://github.com/BeardedBats/Kel

Remote dev/daily-driver:
a471e17ac25590369e74824ebed0dd7b54e4b00b

Current stable dogfood installation:
C:\Users\Nick\KelDogfoodCandidate

Current real dogfood data:
C:\Users\Nick\KelDogfoodRuns\prepared

These dogfood paths are PROTECTED.

### GOAL

Create the clean V2.0 development line and persist the complete V2.0 expansion marathon to durable
repository documents.

Do NOT begin feature implementation in this run.

This run should:

1. create the V2 worktree
2. create the V2 branch from exact base a471e17
3. persist the complete roadmap/directive
4. establish durable resume/state files
5. establish disk/worktree hygiene rules
6. verify the new branch/worktree
7. push dev/v2 safely to GitHub
8. stop

## 1. CREATE THE V2 WORKTREE

Create: `C:\Users\Nick\Desktop\Kel\kel-v2` — Branch: `dev/v2`, based EXACTLY on
`a471e17ac25590369e74824ebed0dd7b54e4b00b`.

Use the existing shared Kel Git object database/worktree architecture.

Do NOT: clone the repository again; copy kel-daily-driver manually; create another independent Git
object database; touch main; rewrite history; force push; move historical refs.

Verify: `dev/v2 HEAD == a471e17` before making any V2 setup commit.

## 2. PROTECT THE STABLE DOGFOOD BUILD

Never modify, uninstall, overwrite, reset, migrate, clean, or use as a V2 test root:
`C:\Users\Nick\KelDogfoodCandidate`.

Never modify or delete: `C:\Users\Nick\KelDogfoodRuns\prepared`.

Nick will actively use that build while V2 development runs. Fix Capture feedback from that build is
real dogfood input. Treat it as an external feedback source, not V2 scratch data.

## 3. V2 DEVELOPMENT PATHS

Source: `C:\Users\Nick\Desktop\Kel\kel-v2` — Branch: `dev/v2`.

Development/test data: `C:\Users\Nick\KelV2Runs\prepared`.

Future installed V2 candidate: `C:\Users\Nick\KelV2Candidate`.

Do not install KelV2Candidate until an implementation checkpoint genuinely benefits from installed-app
verification. Do not create a new permanent install for every phase.

## 4. PRODUCT NORTH STAR

Persist this prominently. Kel should feel like:

> "One capable personal assistant with hidden orchestration."

Nick interacts with Kel. Nick should control: goals; consequential decisions; meaningful model
preferences; capability preferences; meaningful memory changes; approvals.

Nick should NOT need to understand: workers; leases; scopes; staffing graphs; runtime topology; routing
internals; event streams; MCP plumbing; execution packets.

Kel decides how to accomplish the work underneath.

## 5. V2.0 DEFINITION

V2.0 is: "One personal assistant that can talk, work, remember, learn, use Nick's services, continue
autonomously, and stay reachable from his iPhone."

Primary acceptance test: Can Nick spend an entire normal workday inside Kel without repeatedly needing
ChatGPT, Kun, another API client, another workflow tool, or another orchestration/control surface to
coordinate the work?

## 6. CONNECTION MODEL

Use the product term: **Connections**. A Connection means: "Kel has credentials for this service and can
use its API."

Do NOT build: a plugin marketplace; one custom mini-app per service; one database per service; one
worker per service; one workflow system per service.

Conceptual model: Connections give Kel access to services. Tools let Kel do things with them. Recipes
describe repeatable work. Projects provide context/isolation. Memory helps Kel improve. Fix Capture tells
Kel how Kel itself needs improving.

## 7. V2.0 CONNECTIONS

Build support for: Pitcher List / WordPress REST API; Stripe API; Raptive API; Google Drive; GitHub;
ClickUp; Figma; Discord; Generic REST API Connection.

Remove Gmail and Slack from the intended V2 connection list.

- **Pitcher List:** primarily API-key REST access to the WordPress/Pitcher List backend.
- **Stripe:** authenticated API access; writes require existing Kel permission gates.
- **Raptive:** API credential access; no custom dashboard unless usage proves necessary.
- **Google Drive:** account authorization / OAuth as appropriate.
- **GitHub:** repositories, files, branches, commits, issues, PRs, review workflows.
- **ClickUp:** useful task actions only; do not recreate ClickUp.
- **Figma:** retrieve useful design/file/component context; do not recreate Figma.
- **Discord:** start with the least-complex access Nick actually needs: webhook, bot token, or fuller API
  only if required.
- **Generic REST:** fields conceptually include service name; base URL; API key; auth method/header;
  optional documentation URL; optional test endpoint; Test Connection.

## 8. CONNECTION FRAMEWORK

Create a small developer-facing Connection Framework.

Templates:
- **A. API Key** — e.g. Pitcher List, Stripe, Raptive, Generic REST
- **B. OAuth** — e.g. Google Drive, possibly Figma
- **C. Bot / Webhook** — e.g. Discord

The framework should standardize: credentials; authenticated requests; actions/tools; permissions; Test
Connection; errors; retries where appropriate; tests.

Long-term developer goal: "Kel, add Raptive. Here are the API docs." should become a routine
implementation task.

## 9. FIX CAPTURE STATUS

Fix Capture is ALREADY BUILT. Do NOT rebuild it.

Existing stable implementation includes: Ctrl+Shift+F → click problem → record real speech → Muse
transcription → Save Fix → Dogfood Fixes → Prepare Fix Prompt.

The current verified V2 baseline includes the Muse repair at `a471e17`. Fix Capture must remain
functional throughout V2.

Dogfood statuses stay exactly: OPEN, BATCHED, FIXED, DISMISSED. Do not turn it into Jira.

Persistent visual rule: **NEVER use single-side colored borders or accent rails.** No border-left
emphasis; no border-top emphasis; no colored side stripes; no colored edge rails; no stripe + tinted-box
callouts. Use typography; spacing; background tone; subtle full-perimeter neutral borders; restrained
icon/state differences.

## 10. IPHONE KEL V1 — V2.0

V2.0 mobile is intentionally simple. Build a mobile-friendly PWA / WebUI tether. Nick wants to interact
with Kel from his iPhone.

Required: open Kel on iPhone; persistent login; conversation history; create a conversation; continue a
conversation; type text; paste text; voice-record prompt; Muse transcription; send transcript; basic
Project switching; conversational Project routing; create a Project through conversation; add work to an
existing Project/conversation; infer destination when confident; ask when genuinely ambiguous.

When opening mobile Kel, show: running work; recently completed work; failed work; Needs Your Attention.

From phone: answer Kel; approve; deny; grant requested access; review results; resume work; stop work.

NOT V2.0 Mobile V1: file uploads; photos; videos; contacts; camera; share sheet; push notifications;
native Swift app; Android app.

Architecture for V2.0: iPhone PWA → Remote/WebUI → Nick's desktop Kel. Desktop may need to remain on.
Cloud Kel is V2.5, not V2.0.

## 11. NEEDS YOUR ATTENTION 2.0

Improve the current authoritative-state-derived inbox. Add where useful: Project grouping; priority; age;
clear reason Kel needs Nick; related conversation/work; direct action; filtering; sorting; resolved items
disappear. Possible: Snooze; Later — ONLY if those can remain consistent with authoritative work state.
Do not build a second task database.

## 12. RECIPES 2.0

Existing Recipes engine remains authoritative. Add: Recipe library; search; favorites; recent Recipes;
categories; create; edit; duplicate; attach to Project; run; run again; run history; last result;
success/failure; reopen output.

Kel may suggest: "You do this often. Save it as a Recipe?" — only after repeated behavior. Do not
suggest a Recipe after a single occurrence. Recipe sharing is not a V2 priority.

## 13. ACTIVITY 2.0

Activity stays optional/high-level. Add: historical timeline; Project filter; date filter; work-type
filter; failure filter; search; open result; open evidence; retry history; recovery history.

Do NOT expose: raw worker ids; leases; staffing graphs; agent cockpit controls.

## 14. ROUTING INTELLIGENCE

Current routing knows rules. V2 should learn from outcomes. Record useful information such as: response
time; task completion success; provider failure; model failure; task type; tool reliability; approximate
cost; review outcome. Use this to improve Automatic routing: best coding model; best research model; best
review model; recently reliable providers; degraded providers; speed/reliability/cost/task-fit tradeoffs.
Optional action: “Why this model?” — explain on demand; do not clutter normal chat.

## 15. LEARNING 2.0

Kel may learn: output format preference; model preference by task; review depth; autonomy preference;
recurring Project workflows; recurring tasks; file locations; tools; frequently used Connections;
frequently used Recipes.

Build: **What Kel Learned** — allow Nick to inspect; correct; remove; temporarily disable; understand why
something was learned.

Kel must NEVER silently learn: permission grants; spending authority; unrestricted filesystem access;
irreversible authority; sensitive assumptions.

## 16. LONG-RUNNING WORK 2.0

Tune existing autonomy using real use. Improve: continuation; dependency recovery; provider recovery;
stalled-work detection; progress summaries; resume briefs; completion recognition; escalation.

Goal: Kel keeps working until Nick is genuinely required.

## 17. ADAPTIVE STAFFING 2.0

Current workforce principles remain: **LARGE BENCH. SMALL MISSION TEAM. CENTRAL COMMAND. INDEPENDENT
VERIFICATION.**

Kel is Commander. Do not spawn another Commander. Architect is the only retained subordinate manager.
Specialists are: skill packs; variants; lenses; task bindings.

Staffing levels conceptually remain: D0 — Kel alone; D1 — one specialist; D2 — small pod; D3 — parallel
mission teams; D4 — exceptional/high-assurance.

Builders cannot final-certify themselves. Verifier gets fresh context. Sentinel handles serious
security/privacy/data/migration concerns. Oracle should ideally perform fresh read-only review,
preferably via a different provider where practical. Red Team attacks accepted artifacts when justified.
Normal users do not need these labels.

Learn from outcome history: when solo succeeds; when specialists help; when independent review helps;
when parallelism helps; when high assurance is unnecessary.

## 18. LOCAL EXECUTION ISOLATION

Strengthen practical containment. Filesystem: path restrictions; sensitive-folder protection; read-only
execution; temporary writable workspace. Processes: child-process restrictions; full process-tree kill;
restricted environment; disposable sessions.

Do NOT build: a VM platform; a Rust sandbox rewrite; a generalized container orchestration platform.

## 19. NETWORK PERMISSIONS

Introduce explicit network policy. Modes conceptually: **NO INTERNET**; **APPROVED DOMAINS**; **FULL
INTERNET**. Support: per-tool rules; per-Project rules; show contacted domains; block unexpected domains;
ask before a new domain; access history. Keep this practical.

## 20. REAL DOGFOOD FEEDBACK LOOP

Nick will be using `C:\Users\Nick\KelDogfoodCandidate` while V2 development runs. Fix Capture will
generate real product feedback. Do not assume synthetic tests replace that feedback.

When real Fix Capture batches are brought into the V2 thread: 1. reproduce the finding; 2. group related
findings by root cause; 3. implement coherent repair; 4. add regression coverage; 5. verify affected UI
directly; 6. do not mark fixed solely because code changed.

Dogfood feedback can alter V2 priorities when it reveals higher-impact friction. Document meaningful
priority changes.

## 21. PERFORMANCE

Measure what Nick feels: startup; conversation opening; Project switching; first-response latency;
routing delay; Remote load; transcript search; Recipe load; Needs Your Attention; memory retrieval. Fix
real felt delays. Do not waste time chasing meaningless benchmarks.

## 22. MANUAL UPGRADE RELIABILITY

Kel is a personal app. Do NOT build consumer updater infrastructure. No: update server; automatic update
checks; background downloads; “update ready”; release marketing UI; Stable/Beta/Dev channels.

Do preserve: safe manual upgrade; Projects; conversations; memory; credentials; settings; transcripts;
Recipes; Connections; Fix Capture data where appropriate; safe migrations; failure without data loss;
practical developer rollback.

## 23. V2.0 EXPLICIT NON-GOALS

Do NOT build: Profiles; giant workforce dashboard; manual worker rosters; unlimited nested spawning;
second memory system; second workflow system; second auth system; second permission system; second task
database; generic enterprise RBAC; giant vector database; giant knowledge graph; Rust migration; public
A2A; native iPhone app; Android app; phone uploads; phone push notifications; consumer update platform.

## 24. V2.5 BOUNDARY

Do not implement V2.5 during this marathon. V2.5 is: **Always-On Cloud Kel / Mobile V1.1.** Future scope:
cloud Kel engine; cloud conversations; cloud Projects; cloud memory; cloud Recipes; cloud Connections;
cloud models; cloud autonomous work; cloud recovery; iPhone works with desktop off for cloud-capable work.

## 25. V3.0 BOUNDARY

Do not implement V3.0 during this marathon. V3.0 is: **Cloud Kel + secure desktop execution node / Mobile
V1.2.** Future scope: desktop registration; online/offline state; secure cloud-desktop transport; cloud →
desktop task delivery; desktop → cloud results; local files stay local; local credentials stay local;
queued local work when offline; reconnect/resume; Waiting for Desktop state.

## 26. V2 EXECUTION PHASES

Persist the V2 marathon approximately as: **V2-00** baseline / durable state / developer line; **V2-01**
Connections model + central management; **V2-02** Generic REST Connection; **V2-03** personal Connections;
**V2-04** Connection Framework + templates/docs/testing; **V2-05** iPhone Kel PWA V1; **V2-06** Needs Your
Attention 2.0; **V2-07** Recipes 2.0; **V2-08** Activity 2.0; **V2-09** Routing Intelligence; **V2-10**
Learning 2.0; **V2-11** Long-running Work 2.0; **V2-12** Adaptive Staffing 2.0; **V2-13** Local Execution
Isolation; **V2-14** Network Permissions; **V2-15** Real Dogfood Integration Pass; **V2-16** Performance +
UX Polish; **V2-17** Manual Upgrade Reliability / migration validation; **V2-18** Synthetic V2 acceptance
journeys; **V2-19** Full V2 regression; **V2-20** V2 release candidate.

You may refine phase boundaries when implementation evidence supports it. Do not silently remove roadmap
scope. Record any scope movement.

## 27. V2.0 ACCEPTANCE

V2.0 must validate — Conversation: normal discussion, long-running discussion, continuation. Projects:
multiple real contexts, no contamination. Work: real autonomous execution, recovery. Models: routing,
fallback, transparency. Memory: useful recall, controlled learning. Connections: real personal APIs.
Transcription: real Muse recording. Recipes: repeated workflows. Remote: secure browser use. iPhone: chat,
voice, status, approvals, Project routing, resume/stop. Fix Capture: real friction capture. Needs Your
Attention: human interruptions. Recovery: failures without lost work. Security: authority narrowing,
execution boundaries, network restrictions. Upgrade: preserve durable user state.

## 28. DURABLE FILES

Create/update a V2 durable state directory such as `docs/v2/`. Required: `MARATHON_DIRECTIVE.md`,
`MARATHON_STATE.md`, `RESUME.md`, `ROADMAP.md`, `FEATURE_LEDGER.md`, `IMPLEMENTATION_STATUS.md`,
`DECISIONS.md`, `TEST_EVIDENCE.md`, `PACKAGE_EVIDENCE.md`, `KNOWN_LIMITATIONS.md`, `DOGFOOD_FINDINGS.md`.

- MARATHON_DIRECTIVE.md: complete durable instruction set
- MARATHON_STATE.md: machine-readable-ish current program state
- RESUME.md: very short exact continuation instructions
- ROADMAP.md: phase map
- FEATURE_LEDGER.md: feature → state → evidence
- IMPLEMENTATION_STATUS.md: what is actually built
- DECISIONS.md: meaningful product/architecture decisions
- TEST_EVIDENCE.md: cumulative verification
- PACKAGE_EVIDENCE.md: candidate/package/install evidence
- KNOWN_LIMITATIONS.md: honest limitations
- DOGFOOD_FINDINGS.md: real Fix Capture findings incorporated into V2 and their disposition

## 29. AUTONOMOUS MARATHON OPERATING MODEL

Future V2 marathon runs should: read durable state first; reconcile git; resume exact current item;
preserve coherent interrupted work; continue automatically; self-review each coherent increment; test each
coherent increment; commit atomically; update durable state; determine the next dependency; continue.

Do NOT stop merely because: a commit finished; a phase boundary was reached; documentation was updated;
tests initially failed but are fixable; implementation became complex; a clean checkpoint exists.

Legitimate stop reasons: genuine blocker requiring Nick; consequential product decision with no
evidence-backed default; external dependency cannot proceed safely; execution environment itself ends the
turn; final V2 RC is reached.

## 30. DISK / WORKTREE HYGIENE

This is now a mandatory program rule. The previous program accumulated more than 80 GB of disposable
worktrees/build debris. Do not repeat that. Rules: `dev/v2` is the primary long-lived V2 worktree; create
temporary review/audit worktrees only when isolation materially helps; temporary worktrees must NOT
survive indefinitely — once their findings/evidence are safely committed, remove them; do not leave
node_modules/build/dist copies in obsolete trees; do not create independent clones when a Git worktree is
sufficient; do not accumulate historical installed candidates; do not accumulate synthetic data roots; do
not accumulate duplicate installers; generated bulk is reproducible and disposable; committed
source/evidence is durable. Maintain a small disk-hygiene note in durable state if temporary trees are
created.

## 31. VISUAL RULES

Maintain current Kel visual direction. Important: **NEVER use single-side colored borders or accent
rails.** No: colored left border; colored top border; colored right border; colored bottom border;
decorative colored stripe on a box; asymmetric edge highlight.

Prefer: typography; whitespace; hierarchy; restrained background differences; subtle full-perimeter
neutral borders; icons; careful composition.

Also: avoid excessive cards; avoid pills/circles by default; use approximately 8px geometry where
appropriate; no generic AI-dashboard styling; body/conversation floor ~16px; navigation/metadata/settings
floor ~14px; code floor ~14px.

## 32. SETUP COMMIT

Once the durable V2 documents are complete: inspect them; verify they capture this directive faithfully;
commit them atomically as the V2 program initialization. Do not add unrelated implementation.

## 33. PUSH DEV/V2

Push `dev/v2` to `origin/dev/v2`. Normal fast-forward/new-branch push only. No force. Do not touch main.
Verify local and remote HEAD match.

## 34. FINAL REPORT FOR THIS RUN

Return: 1. V2 worktree path; 2. V2 branch; 3. exact base commit; 4. setup commit; 5. remote dev/v2 SHA;
6. durable files created; 7. confirmation DogfoodCandidate untouched; 8. confirmation DogfoodRuns
untouched; 9. confirmation main untouched; 10. worktree list after setup; 11. disk-hygiene state;
12. exact prompt to use for the first V2 implementation run. **STOP AFTER SETUP. Do NOT implement V2-01 in
this run.**

---

# PART B — operational summary written at setup (V2-00)

Read Part A first; this part is the same program expressed as state, so a resume run can act without
re-deriving anything.

## Baseline and paths

| | |
| --- | --- |
| Repository family | `C:\Users\Nick\Desktop\Kel` — one shared Git object database in `Kel-Repo\.git`; every tree is a worktree, never a clone |
| Predecessor line | `dev/daily-driver` @ `a471e17ac25590369e74824ebed0dd7b54e4b00b` (reference only; its records live in `docs/daily-driver/` and `docs/transcription/`) |
| V2 source | `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` |
| V2 test data | `C:\Users\Nick\KelV2Runs\prepared` |
| V2 candidate | `C:\Users\Nick\KelV2Candidate` — created only when a checkpoint genuinely needs installed-app verification |
| Protected (never touch) | `C:\Users\Nick\KelDogfoodCandidate`, `C:\Users\Nick\KelDogfoodRuns\prepared` |
| Remote | `https://github.com/BeardedBats/Kel` (`main` stays at `5e76b21071a28601a7fb4de508cb3cf349c77db8`) |

## Invariants (violating any of these is a bug, not a preference)

- One capable personal assistant with hidden orchestration: Nick controls goals, consequential decisions,
  meaningful model/capability preferences, meaningful memory changes and approvals — never workers,
  leases, scopes, staffing graphs, runtime topology, routing internals, event streams, MCP plumbing or
  execution packets.
- Fix Capture stays exactly as built: `OPEN` / `BATCHED` / `FIXED` / `DISMISSED`, never rebuilt, never Jira.
- No second system of anything (memory, workflow, auth, permissions, task store), no enterprise RBAC, no
  giant vector DB or knowledge graph, no Rust migration, no public A2A, no native mobile apps, no updater
  infrastructure, no cloud Kel (V2.5), no desktop execution node (V3.0).
- Visual rule: never single-side coloured borders or accent rails; typography, whitespace, hierarchy,
  restrained background differences, subtle full-perimeter neutral borders; type floors 16/14/14px.
- Disk hygiene is mandatory: temporary trees are removed once their findings are committed, and none are
  left with `node_modules`/build output. Current state: **no temporary worktrees exist**; record any here.

## How a run proceeds

`MARATHON_DIRECTIVE.md` → `MARATHON_STATE.md` (current item) → `RESUME.md` (exact next action) → work in
`kel-v2` → per-increment loop (understand → design → implement → self-review → test → atomic commit →
update durable state) → next dependency. Stop only for the legitimate reasons in Part A §29.

