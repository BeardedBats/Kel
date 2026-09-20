# ROADMAP — Kel Daily Driver Expansion (lane `dev/daily-driver`)

Guiding principle: **ONE CAPABLE ASSISTANT WITH HIDDEN ORCHESTRATION.**

Out of scope for this tranche (per marathon instruction §35): profiles, visible workforce dashboard,
normal-user roster management, unlimited nested spawning, second memory system, second workflow
engine, second authorization system, second task database, enterprise RBAC, giant vector DB, Rust
migration, public A2A, fashionable rewrites.

| Phase | Scope | Status |
| --- | --- | --- |
| D0 | Close final V1.6 human-visual residuals (HVRA-MINOR-001/002, HVRA-SUG-001/002) | **DONE** |
| D1 | Provider + model onboarding (truthful states, setup flows, Save+Verify, health/failure UX) | **DONE (core)** |
| D2 | Update reliability (safe installer-based upgrade; user-visible update state; no data loss) | **DONE (core)** |
| D3 | Remote / WebUI usable away from the desktop; explicit enable; hardening | **DONE (core)** |
| D4 | Transcription first-class workflow (record/upload/folders/transcript actions/send-to-chat) | **DONE (core)** |
| D5 | Needs Your Attention as the canonical interruption center + restrained notifications | **DONE (core)** |
| D6 | Continuation / resumability ("while you were away" brief; real resume actions) | **DONE (core)** |
| D7 | Long-running autonomy (durable objective/step, completion criteria, human gates) | **DONE (core)** |
| D8 | Adaptive staffing (D0–D4 tiers; guardrails; hidden internally) | **DONE (core)** |
| D9 | Learning promotion (high-confidence, low-risk only; provenance/retraction preserved) | **DONE (core)** |
| D10 | Recipes (declarative; compile into existing execution; evidence-based suggestions) | **DONE (core)** |
| D11 | Cross-device continuity (server-authoritative state) | **DONE (core)** |
| D12 | Smarter provider routing (task fit, health, cost where known; honest fallbacks) | **DONE (core)** |
| D13 | Failure recovery polish (provider/CLI/engine/network/remote/transcription/update) | **DONE (core)** |
| D14 | Optional Advanced Activity view (high-level only; optional + unobtrusive) | **IN PROGRESS** |
| D15 | Security / sandbox boundary improvements (no bespoke hypervisor) | QUEUED |
| D16 | Live capability revision (revocation narrows immediately; no silent widening) | QUEUED |
| D17 | Plugin / integration developer surface (+ connected/needs-setup/unavailable UX) | QUEUED |
| D18 | Synthetic daily-driver dogfood journeys (10 journeys; friction fixes) | QUEUED |
| D19 | Full regression + fresh package + installed candidate + final records | QUEUED |

Cross-cutting (always on): internal self-review per phase; focused tests after every feature cluster;
disk-first durable state; honest development identity; no release, no publish, no new audit campaign.
